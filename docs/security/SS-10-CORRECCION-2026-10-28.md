# SS-10 — Diagnósticos seguros de excepciones y parámetros SQL

Fecha: 2026-10-28. Repositorio Software-PA / SSALFER.
Referencia: rama dev, HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff`, más cambios locales SS-01, SS-02, SS-03 y SS-04.

## Dictamen y alcance

**Corrección local implementada y comprobada con pruebas aisladas; validación integrada y operativa pendiente.** El backend deja de incorporar excepciones completas en sus handlers y usa diagnósticos con campos permitidos. SQLAlchemy runtime y owner bootstrap declaran hide_parameters=True. La configuración versionada protege también el formato final de Uvicorn y los logs Python que pasan por los handlers configurados; no se afirma que sanee PostgreSQL servidor, Nginx, stderr nativo ni recolectores externos.

Ejecución final: **105 pruebas descubiertas: 102 aprobadas y 3 omitidas**. Son 81 regresiones previas aprobadas más 24 pruebas nuevas SS-10 (21 aprobadas y 3 nativas omitidas). Las dependencias FastAPI, Starlette, Uvicorn, SQLAlchemy y psycopg2 no están instaladas en el Python local utilizado. No se instalaron paquetes ni se importó app.database/app.main, leyó .env, inició Docker o abrió conexión a PostgreSQL. No se ejecutaron scripts operativos, migraciones, commits/push/merge ni despliegues.

## Inspección y fuentes de exposición

| Fuente | Evidencia de código | Tratamiento |
|---|---|---|
| main.py: database_error_handler y global_exception_handler | Registraban exc_info con excepción/traceback; path crudo podía contener identificadores | Sustituidos por categorías/códigos, correlación interna y plantilla de ruta |
| database.py: create_engine | No declaraba hide_parameters | Se añade True; echo/echo_pool False explícitos |
| Uvicorn / Starlette | El error puede propagarse al servidor aunque el handler ya haya respondido; Uvicorn registra traceback | Formatter permitido para uvicorn.error y root; no se cambia la propagación de excepciones |
| Uvicorn access | Formato habitual incluye request target con query, IP y valores de ruta | --no-access-log elimina esa salida y middleware emite un registro HTTP normalizado |
| SQLAlchemy pool/driver/dependencias Python | Un logger puede incorporar exc.orig, SQL literal o datos en msg/args/exc_text | Formatter final no interpola msg/args ni imprime exc_info/exc_text/stack_info |
| create_admin.py | Engine owner y fallos de bootstrap podían emitir parámetros o traceback no controlado | Hide/echo también en owner; fallos CLI con código y correlación, sin excepción |
| sync/import RAN y conciliador de linaje GIS | print(str(exc)), f-strings de excepción y clase dinámica; errores Unicode incorporaban bytes del archivo | Mensajes controlados; se mantiene código especial de COMMIT incierto |
| GIS y documentos | No se encontraron loggers/prints en sus servicios HTTP; errores controlados con causas encadenadas; GDAL stderr ya descartado por correcciones previas | Se conserva íntegro su código. La causa encadenada nunca se entrega al formatter seguro |
| Nginx SSALFER y React | No hay log_format seguro definido en los archivos server versionados; formato efectivo heredado/externo no inspeccionado | Riesgo residual: request line/query/Referer, errores de proxy y rutas upstream requieren QA/configuración de infraestructura |
| Docker Compose | json-file con max-size/max-file declarados | Conservado. Rotación limita volumen, no sanea contenido ni acredita ACL/retención/exportación reales |
| PostgreSQL servidor, libpq, scripts y artefactos auxiliares | Salidas fuera del logging Python; utilidades de extracción/esquema/reportes pueden producir muestras deliberadas | No se ejecutan. Se documenta la frontera de esta corrección |

Se buscó logging/logger, exc_info, traceback, print de excepciones, str/repr de fallos, create_engine/echo y configuración del driver en backend. Los únicos handlers de logging propios HTTP originales estaban en main.py. El engine usa PostgreSQL con SQLAlchemy/psycopg2 y pool_pre_ping; no hay hook de saneamiento del servidor DB. No se inspeccionaron valores de .env, logs reales, expedientes o credenciales. Las búsquedas se limitaron a código/configuración/documentación versionada y pruebas.

El auxiliar backend/extract.py está excluido explícitamente por backend/.dockerignore y no es el engine runtime: no se amplía esta corrección a sus exportaciones de muestras ni se ejecuta. Tampoco se presentan scripts de benchmark, generación de esquema o datos de QA como una canalización de logging segura. Sus reportes deben tratarse como artefactos con contenido potencialmente sensible.

## Medidas implementadas

### 1. SQLAlchemy: defensa complementaria

Runtime y owner bootstrap usan hide_parameters=True, echo=False y echo_pool=False. Esto reduce la representación habitual de parámetros enlazados; no modifica consultas, pool, transacciones, resultados, permisos o esquema. La [documentación SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/core/engines.html#hiding-parameters) describe el ocultamiento de parámetros del engine.

La opción **no borra** .params, .orig, SQL literal, detalles del driver, causa/contexto de excepción ni datos ya copiados por una biblioteca. No se confía en str(exc) aunque hide_parameters esté activo. No hay extracción de pgerror, DETAIL, statement, params o SQLSTATE para componer logs; la categoría se determina por clases conocidas sin interpolar nombres dinámicos. StatementError mantiene respuesta pública 500; DBAPIError/IntegrityError/InternalError mantienen 409; un error directo del driver mantiene 500.

Las dos comprobaciones nativas SQLAlchemy quedan incluidas como pruebas opcionales: construyen excepciones reales, sin engine ni conexión, para demostrar ocultamiento de parámetros habitual y permanencia de orig/params. Fueron omitidas por dependencia ausente; no se sustituye su resultado por una afirmación basada en mocks. La tercera prueba opcional construye un psycopg2.IntegrityError sin conectar y comprueba el formatter; también omitida.

### 2. Registro con campos permitidos

Nuevo módulo stdlib backend/app/safe_logging.py. Los eventos propios contienen exclusivamente:

- timestamp UTC y nivel de severidad;
- category, code y component definidos por el código;
- correlation_id UUID4 generado dentro del proceso para cada solicitud;
- método HTTP reconocido o OTHER;
- plantilla de ruta registrada o <unmatched>, nunca path/query crudos;
- status y response_complete, sin afirmar éxito de una respuesta incompleta.

No se utiliza X-Request-ID, X-Correlation-ID, cookies, tokens, headers, cuerpo, correo, IP o identificador de expediente para generar correlación. No se añade el ID al body ni a cabeceras públicas: el contrato de respuesta permanece igual. Correlación es del backend, no una cadena distribuida confiada al cliente.

El formatter no llama getMessage/formatException, str/repr de excepción, ni lee sus atributos. Para dependencias no controladas produce runtime_diagnostic con severidad y componente permitido. Algunos templates fijos de Uvicorn y pool tienen códigos específicos (ASGI_APPLICATION_ERROR, SERVER_STARTED, DB_POOL_TERMINATION_ERROR, etc.), sin interpolar args. Templates desconocidos conservan RUNTIME_DIAGNOSTIC y su nivel; no se suprimen errores críticos mediante una expresión regular o filtro general.

Los eventos propios son snapshots inmutables de primitivos. **El LogRecord no recibe el scope, Request, contexto completo ni excepción**: no basta sanear texto si un colector puede serializar extras. El contexto de solicitud usa ContextVar y se restablece en finally. Se comprueba aislamiento entre solicitudes concurrentes y ausencia de secretos en el snapshot.

SafeStreamHandler sustituye el fallback habitual de logging que, si falla el formatter/IO, puede imprimir Message y Arguments. El fallback sólo intenta emitir OBSERVABILITY_FAILURE; si stderr está roto no se puede garantizar persistencia. No se habilitan trazas completas para desarrollo ni producción.

### 3. Observación HTTP sin alterar lógica

SafeDiagnosticsMiddleware es ASGI puro, añadido después de registrar rutas y middleware. Observa mensajes enviados sin consumir cuerpos, reescribir cookies, reemplazar respuestas ni absorber excepciones. Conoce la lista de plantillas registrada al construir el stack; una ruta no reconocida cae a <unmatched>.

Mantiene el comportamiento de errores/background tasks/streaming: un fallo posterior al inicio no sustituye una respuesta ya enviada; se registra el status efectivamente iniciado y si el body terminó. Si todavía no comenzó respuesta, el registro HTTP de un fallo usa el valor de error por defecto 500 y marca incomplete. No es una confirmación de entrega al cliente. El handler global conserva su respuesta genérica; Starlette puede descartar una respuesta de error posterior al envío.

La [documentación de excepciones Starlette](https://starlette.dev/exceptions/) explica la propagación de errores y los fallos de background tasks después de responder. Por ello se protege también Uvicorn en lugar de suponer que eliminar exc_info en main.py es suficiente. No se cambia el orden interno de los controles existentes de CSRF/autenticación; se añade observación externa a los middleware de usuario.

### 4. Configuración de proceso versionada

backend/logging.json configura SafeJSONFormatter/SafeStreamHandler para ssalfer.diagnostics, uvicorn, uvicorn.error, uvicorn.access, sqlalchemy, psycopg2 y root. Conserva ERROR/CRITICAL; el diagnóstico propio y HTTP usa INFO o superior, SQLAlchemy/driver WARNING o superior. No se activa echo ni debug con SQL. disable_existing_loggers=False evita deshabilitar silenciosamente bibliotecas; handlers propios instalados por terceros pueden requerir revisión adicional.

Dockerfile, Compose base y override dev añaden --log-config /app/logging.json y --no-access-log, manteniendo --no-proxy-headers de SS-04 y todos los presupuestos de SS-03. Prod y SSALFER no redefinen el comando backend. COPY y el bind mount dev ya incluyen logging.json; no se modifica el artefacto de frontend. La [configuración Uvicorn](https://uvicorn.dev/settings/) admite formato dictConfig/JSON y control del access log.

El access log se sustituye por eventos HTTP seguros: no se desactiva toda observabilidad. Esto depende de arrancar con el manifiesto/configuración revisados. Un lanzamiento manual sin --log-config o una configuración externa que reinstale handlers no acredita esta protección.

### 5. Diagnósticos CLI

Sólo se modifican salidas de fallo en cuatro scripts; no se ejecutan ni se cambia su lógica de negocio. Los fallos imprimen códigos fijos y UUID de operación; no interpolan excepción o nombre dinámico de clase. RAN conserva las claves/modos de su reporte JSON y sustituye texto de fallo por código fijo. Las entradas Unicode inválidas producen RAN_DECODE_ERROR sin volcar bytes de origen. GIS_COMMIT_UNCERTAIN conserva la advertencia de verificar el resultado en sólo lectura y el exit code de fallo; no se toma ninguna decisión nueva de reparación.

Los reportes operativos de éxito, errores de validación de datos y artefactos exportados pueden seguir conteniendo información deliberada del dataset. No deben enviarse automáticamente a logs centralizados ni considerarse saneados por este formatter. Imports, excepciones de limpieza posteriores y herramientas CLI externas al arranque controlado deben validarse por separado: este módulo no reemplaza sys.excepthook de todo Python ni stderr nativo.

## Ejemplos exclusivamente sintéticos

Antes, el cuerpo real del handler anterior ejecutado con una excepción sintética incluía el marcador en su salida. Ejemplo abreviado de ese mecanismo (sin datos reales):

```text
Database error in POST /api/personas/123
Traceback ...
RuntimeError: SS10_ONLY_SYNTHETIC_BEFORE_73bc1
```

Un error SQL/driver puede añadir parámetros o mensajes a esa representación; no se simuló una conexión SQL real para construir el ejemplo.

Después, ejemplo producido por el formatter implementado con una plantilla y metadatos sintéticos:

```json
{"category":"database_integrity","code":"DB_INTEGRITY_ERROR","component":"database","correlation_id":"424675a6531d44e6b94506c949e8137a","method":"POST","route":"/api/personas/{id_persona}","status":409,"response_complete":false,"level":"ERROR","timestamp":"2026-10-28T18:57:57.017106+00:00"}
```

Una respuesta parcial puede conservar status=200/206 y response_complete=false con categoría de error; no se cambia a un 500 que el cliente nunca recibió. Un evento de driver fuera de solicitud puede tener correlation_id/method/route/status=null: no se inventan datos de una petición inexistente. El logger propio del handler y el registro HTTP comparten correlación, aunque una reemisión exterior de Uvicorn posterior al reset del contexto ya no la tenga.

## Pruebas y evidencia

Se inspeccionaron imports/efectos antes de ejecutar. Las pruebas están fuera de backend/tests y no cargan conftest. Se usa sólo stdlib, configuración de logging versionada y el módulo puro; los cuerpos reales de los handlers/ramas de excepción CLI se extraen por AST con dependencias sintéticas. No se ejecuta el top-level de scripts ni la app/engine. Un conjunto anterior de pruebas falló al detectar interpolación de UnicodeError en el reporte RAN; se corrigió esa vía y se repitió la suite.

Comando final ejecutado:

```sh
python3 -B -m unittest discover -s tests/security -p 'test_*.py' -q
# Ran 105 tests in 0.415s
# OK (skipped=3)
```

| Control | Comprobación ejecutada | Resultado / límite |
|---|---|---|
| Parámetros del engine | AST de ambos create_engine: hide True, echo y echo_pool False | Aprobado sin importar engine |
| StatementError/DBAPIError/IntegrityError/InternalError/driver | Handlers reales con clases sintéticas de jerarquía equivalente; categorías y 409/500 exactos | Aprobado; tipos nativos pendientes |
| Secretos y PII | Sentinelas específicos de contraseña, bcrypt sintético, sesión, CSRF, cookie, SQL, email, nombre, query y detalle driver | Ninguno aparece en salida final formateada |
| Logging de terceros | Registros con msg/args, exc_info real sintético, exc_text cacheado, stack_info y extras no confiables | Proyección segura, incluyendo root/Uvicorn/pool/driver; CRITICAL conservado |
| No inspección de excepción | Excepción cuyo str/repr/orig/params falla si se consulta | No se consulta durante handler/formatting |
| Correlación y rutas | Ocho solicitudes ASGI sintéticas concurrentes; UUID distintos, plantilla constante y reset de contexto | Aprobado sin HTTP real |
| Compatibilidad de respuesta | Mismos mensajes ASGI, cookies/body no reescritos; públicos 409/500 conservados | Aprobado con dobles, sin framework instalado |
| Streaming/background/error reemitido | Estado iniciado y finalización parcial; misma excepción propagada; handler exterior comparte scope/correlación | Aprobado con ASGI simulado |
| Diagnósticos CLI | Catch bodies reales ejecutados con excepción sintética y operaciones ausentes | Códigos/UUID y exit code 1, sin marcador en stdout/stderr |
| Fallo de logging | Fallback no imprime original Message/Arguments | OBSERVABILITY_FAILURE controlado |
| Arranque | JSON dictConfig real cargado en pruebas; YAML de cuatro Compose parseado sin .env; flags preservados | Aprobado estáticamente; sin Docker/Uvicorn real |
| Prueba de regresión negativa | Cuerpo del handler previo con excepción sintética | Confirmó exposición anterior del marcador |
| Regresiones previas | 81 pruebas SS-02/03/04 sin editar | Aprobadas |
| SQLAlchemy/psycopg2 nativos | Tres pruebas opcionales sin conexión preparadas | Omitidas por dependencias ausentes |

Las pruebas capturan stderr tras SafeStreamHandler y el formatter, no sólo argumentos de mocks. También prueban que los extras propios no retienen request/scope/exception. Los dobles no demuestran el comportamiento interno real del framework, driver ni SQLAlchemy; se distinguen explícitamente de las comprobaciones nativas omitidas.

No se ejecutó pytest/collect-only, suites con BD, herramientas operativas ni pruebas contra servicios. Las suites frontend no se reejecutan: no hay cambio de frontend. No se instalaron las dependencias ausentes.

## Riesgos residuales y regresión

1. **Logs PostgreSQL:** hide_parameters actúa en Python, no en el servidor. Las políticas de log_statement, log_min_error_statement, log_parameter_max_length y log_parameter_max_length_on_error, DETAIL/CONTEXT, pgAudit y retención deben verificarse en QA. La [documentación PostgreSQL 15](https://www.postgresql.org/docs/15/runtime-config-logging.html) describe canales/controles propios; no se consultó el servidor ni se cambió su configuración.
2. **Driver/nativo:** libpq/GDAL u otras bibliotecas que escriban directamente a stderr/stdout, notices, volcados del proceso y tracebacks de intérprete no pasan necesariamente por logging. No se promete limpiar .orig/.params en memoria o sanitizar todos los ficheros del host. GDAL stderr ya se descarta y se mantiene sin cambios.
3. **Proxy/ingreso:** los server blocks Nginx no acreditan log_format seguro. Revisar request line, query, Referer, nombres de archivos, upstream errors y cabeceras en acceso/error logs. No se modifica el proxy desconocido ni se asume frontend React activo; no se borran logs históricos.
4. **Recolectores/APM:** si serializan request, LogRecord.args/exc_info de una biblioteca, variables locales, cuerpos o extras antes del formatter, pueden saltar la frontera. No basta un formatter para gobernar un agente con acceso al proceso. Inventariar handlers/canales efectivos, muestreo y captura de excepciones; usar corpus sintético, nunca logs reales sin sanitizar.
5. **Arranque alternativo:** comandos externos sin --log-config, handlers instalados después o sys.excepthook/debuggers no están verificados. Mantener el manifiesto revisado en todas las réplicas; no activar trazas completas para solventar una incidencia en producción.
6. **Diagnóstico reducido deliberadamente:** se pierde texto libre de bibliotecas, SQL, traceback, nombre de constraint y detalles de fichero. Se retienen severidad, códigos, componente, ruta y correlación. Templates no reconocidos son RUNTIME_DIAGNOSTIC; ampliar sólo con códigos/campos aprobados y pruebas sintéticas, no con un fallback a str(exc).
7. **Volumen/disponibilidad:** un registro HTTP por solicitud y fallos repetidos siguen generando carga. La rotación versionada no sustituye cuotas/retención efectivas. No se implementa rate limiting ni se cierra SS-04 como efecto de esta entrega.
8. **Inventario de rutas:** si cambia la forma de registrar rutas/subapps y no se reconoce el template, se registra <unmatched>. Es seguro para confidencialidad pero reduce precisión; verificar inventario real FastAPI en QA.
9. **Operación CLI:** cambia el texto diagnóstico de fallos, no sus modos ni escrituras. Automatizaciones que dependan de frases antiguas deben usar códigos/reportes/exit status. Exportaciones intencionales y fallos fuera de los catch revisados requieren canal protegido.
10. **Retención y acceso:** no se demuestra ACL/cifrado/rotación/exportación/backup de logs, ni se elimina exposición histórica. No se leyó ningún log institucional.

## Validación requerida en QA desechable

- Con dependencias ya instaladas en una imagen QA autorizada, ejecutar las tres pruebas nativas opcionales y las regresiones de autenticación/documentos/GIS correspondientes. Las pruebas de excepción nativa incluidas no necesitan DB; suites integradas que sí escriban requieren autorización y PostgreSQL QA desechable.
- Levantar después, mediante un procedimiento autorizado independiente, el artefacto con Uvicorn/configuración reales. Confirmar carga de logging.json en proceso/reloader/múltiples workers; no activar fallback raw. Esta entrega no ejecuta ese despliegue.
- Inducir errores sintéticos de StatementError, IntegrityError, DBAPIError, psycopg2 y fallo de conexión/rollback en QA. Capturar salida de contenedor/recolector, no sólo logger mocks. Verificar marcadores ausentes y eventos funcionales/cookies/CSRF/respuestas intactos.
- Probar error antes del routing, validación 422, 401/403 de sesión/CSRF, 404 con path sensible, 409, 500, streaming, descarga documental y background task. Acreditar templates y status/correlación reales, incluso reemisión Uvicorn y cambios de task/thread.
- Revisar logs de Nginx/PostgreSQL y recolectores con sentinelas; inspeccionar configuración de sólo lectura selectiva, sin volcar logs o .env. Verificar ausencia de body/headers/query/params/locals en APM. Revisar permisos y retención efectiva, incluida copia de seguridad.
- Revisar reportes/automatización CLI en QA con fallos sintéticos; nunca ejecutar importador/sync/bootstrap/conciliación contra una BD institucional para probar logging.

Estos criterios están pendientes; no equivalen a ensayos ejecutados ni a una certificación de ausencia absoluta de datos sensibles en toda la infraestructura.

## Archivos y preservación

| Archivo | Cambio propio SS-10 |
|---|---|
| backend/app/database.py | Parámetros ocultos y echo desactivado |
| backend/app/main.py | Handlers estructurados y observador HTTP |
| backend/app/safe_logging.py | Nuevo: formatter, handler y middleware puros |
| backend/logging.json | Nuevo: configuración final de logging |
| backend/Dockerfile | Flags logging, conservando SS-04 |
| docker-compose.yml | Sólo flags de arranque; mantiene SS-03/SS-04 |
| docker-compose.override.yml | Mismos flags en desarrollo |
| backend/scripts/create_admin.py | Engine owner y diagnóstico de fallo |
| backend/scripts/import_catalogo_nucleos_ran.py | Fallos controlados y errores de decodificación sin bytes |
| backend/scripts/sync_catalogo_ran.py | Fallos controlados |
| backend/scripts/reconcile_gis_migration_lineage.py | Fallos controlados conservando COMMIT incierto |
| tests/security/test_safe_logging_security.py | Nuevo: 24 pruebas, tres opcionales nativas |
| docs/security/SS-10-CORRECCION-2026-10-28.md | Nuevo: informe |
| docs/security/SS-10-CORRECCION-2026-10-28.patch | Nuevo: diff exclusivo de esta entrega |

Se verificaron hashes antes/después de los archivos previos (sin leer .env). Sólo cambian los nueve archivos preexistentes de esta tabla. Todos los servicios, frontend, pruebas y documentos de SS-01/02/03/04 conservan sus bytes. Los cuerpos CSRF/root/health en main.py son idénticos por AST; sólo cambian los dos handlers y se añade observación externa. No hay modificación de autenticación, sesiones, roles, conciliación, auditoría funcional persistida ni migraciones.

El patch compara contra snapshots del **estado local al inicio de SS-10**, no contra HEAD: excluye los cambios anteriores y conserva sus flags/configuración. Incluye los tres archivos nuevos de código/config/pruebas y este informe; no se incluye a sí mismo. No debe aplicarse como sustituto de las correcciones previas. Se valida con git apply --reverse --check --whitespace=error-all sin aplicar ni revertir nada, y git diff --check.

Hashes finales del material de implementación:

| Archivo | SHA-256 |
|---|---|
| backend/app/database.py | `8735feda6d5a1fc37f3e328e9cf8d5dcb3ea40504ab0e9430640422d436b1eda` |
| backend/app/main.py | `f76afb7fa9003a983ade3092451d6e7cf45ae5ecfa1fadf718d168ab18dc865e` |
| backend/Dockerfile | `b816f56ebff741e408bf0d6a63ce6543b26169c731d585dee8e026882899257e` |
| docker-compose.yml | `337a767b5ee36e60ce68a235a22f6390472553b2b7d8b4b2fe60674988ac9917` |
| docker-compose.override.yml | `f3d0aeaf2c18cea7a085fc6cdd70ee96fdcf0b2db6e24a2797203bd0950645d2` |
| backend/scripts/create_admin.py | `5fb2d76a9aefc40ce957c04c7b64ef1d115b62cbdf0c8000c4e7ad95d51f8e13` |
| backend/scripts/import_catalogo_nucleos_ran.py | `d712812bb8f144b2ccaa626329ac9e165597e74303a60f487fc036ee9d9b34b5` |
| backend/scripts/sync_catalogo_ran.py | `eb8590c40b9e8a65616c22766c6d4bb961592fc852896fbef809c5c740d06adb` |
| backend/scripts/reconcile_gis_migration_lineage.py | `fed52eea17910ffa4c0ca475223b30b259b3e26b8b05033cb60e37d5b91c8457` |
| backend/app/safe_logging.py | `f316d0b6d898314bf9cae546172f980d28b33bb186904e182ac56fe0c1982cd8` |
| backend/logging.json | `46c2cf1b8ca2c89bf446bb85b87469281179c396f4509b4b4a5e98205955221f` |
| tests/security/test_safe_logging_security.py | `6a9a1fb0cf1cdc4167592e421283b416c9a06288ee228653cf571fc190bf1875` |

## Diff principal de handlers y engine

El [patch completo y exclusivo](SS-10-CORRECCION-2026-10-28.patch) incluye todos los archivos enumerados. Este extracto es el diff exacto de main.py/database.py:

```diff
diff --git a/backend/app/database.py b/backend/app/database.py
--- a/backend/app/database.py
+++ b/backend/app/database.py
@@ -42,7 +42,10 @@
     SQLALCHEMY_DATABASE_URL,
     pool_size=20,
     max_overflow=10,
-    pool_pre_ping=True
+    pool_pre_ping=True,
+    hide_parameters=True,
+    echo=False,
+    echo_pool=False,
 )
 SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
 
diff --git a/backend/app/main.py b/backend/app/main.py
--- a/backend/app/main.py
+++ b/backend/app/main.py
@@ -1,12 +1,11 @@
 """FastAPI application for the ProyectoNucleo target architecture."""
-
-import logging
 
 from fastapi import FastAPI
 from fastapi.middleware.cors import CORSMiddleware
 from fastapi.responses import JSONResponse
 from sqlalchemy import text
-from sqlalchemy.exc import DBAPIError, IntegrityError, InternalError
+from sqlalchemy.exc import DBAPIError, IntegrityError, InternalError, StatementError
+from psycopg2 import Error as PostgreSQLError
 
 from .config import AUTH_SETTINGS
 from .database import SessionLocal
@@ -20,9 +19,7 @@
     users,
 )
 from .services import authentication as authentication_service
-
-
-logger = logging.getLogger(__name__)
+from .safe_logging import SafeDiagnosticsMiddleware, log_request_error
 
 app = FastAPI(
     title="SOFTWARE-PA",
@@ -80,12 +77,9 @@
 @app.exception_handler(InternalError)
 @app.exception_handler(DBAPIError)
 def database_error_handler(request, exc):
-    logger.error(
-        "Database error in %s %s",
-        request.method,
-        request.url.path,
-        exc_info=(type(exc), exc, exc.__traceback__),
-    )
+    category = ("database_integrity" if isinstance(exc, IntegrityError) else
+                "database_internal" if isinstance(exc, InternalError) else "database_error")
+    log_request_error(request.scope, category, 409)
     return JSONResponse(
         status_code=409,
         content={"detail": "La operación entra en conflicto con la integridad de los datos."},
@@ -94,12 +88,9 @@
 
 @app.exception_handler(Exception)
 def global_exception_handler(request, exc):
-    logger.error(
-        "Unhandled error in %s %s",
-        request.method,
-        request.url.path,
-        exc_info=(type(exc), exc, exc.__traceback__),
-    )
+    category = ("database_statement" if isinstance(exc, StatementError) else
+                "database_driver" if isinstance(exc, PostgreSQLError) else "internal_error")
+    log_request_error(request.scope, category, 500)
     return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})
 
 
@@ -127,3 +118,7 @@
     finally:
         db.close()
     return {"status": "ok", "schema": version}
+
+
+# Registered last: observe CSRF/CORS and routing, retaining route templates only.
+app.add_middleware(SafeDiagnosticsMiddleware, routes=app.routes)
```

**Entrega detenida para revisión técnica.** No se continúa con otro hallazgo ni se integra/despliega esta corrección.
