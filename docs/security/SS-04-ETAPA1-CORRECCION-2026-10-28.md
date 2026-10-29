# SS-04 etapa 1 — Origen de red verificable y diseño de limitación compartida

Fecha: 2026-10-28. Rama `dev`, HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff`, con correcciones locales SS-01, SS-02 etapa 1 y SS-03 etapa 1.

## Dictamen y alcance efectivo

**SS-04 permanece abierto.** Se implementa únicamente el endurecimiento de la atribución de IP: cadena X-Forwarded-For validada desde el extremo confiable y preservación del peer de transporte en los comandos Uvicorn versionados. **No se activa un limitador de solicitudes**, ni se afirma protección global contra fuerza bruta, agotamiento de bcrypt/eventos o bloqueo inducido.

La inspección no encontró un almacén compartido de admisión ni un proxy de entrada cuya topología efectiva esté acreditada. El PostgreSQL de negocio existente no se convierte en contador consultando el histórico por petición: añadiría carga, acoplaría disponibilidad al histórico y requeriría diseño de índices/retención/transacciones y pruebas QA autorizadas. Un diccionario por proceso no controla varias instancias. Conforme a la condición del encargo, se entrega primero el diseño compartido para esos controles; no se introduce un limitador incompleto ni un servicio nuevo.

**81 pruebas aisladas aprobadas:** 32 nuevas SS-04 y 49 existentes SS-02/SS-03. Se ejercitan funciones reales con dependencias sintéticas; no equivalen a pruebas HTTP/ORM de la aplicación integrada. No hay FastAPI, Starlette, Uvicorn ni SQLAlchemy instalados en el intérprete local utilizado. No se instalaron dependencias ni se ejecutaron Docker, PostgreSQL, migraciones, servidores, cargas o fuerza bruta.

## Inspección y preservación

Se revisaron authentication.py (servicio/router), config.py, main.py, auth.py, passwords.py, database.py, Nginx SSALFER, Dockerfile y los cuatro Compose, pruebas auth/RBAC/credenciales, conftest y QA de sesiones frontend; SS-04 de la auditoría y su plan. Las migraciones de credenciales/eventos se inspeccionaron como texto para contrastar la atribución y los motivos permitidos; no se modificaron.

El estado inicial coincide con el SHA de referencia y contiene trabajo sin integrar. Se tomaron hashes de todos los archivos versionados y de los archivos locales no ignorados antes de editar. Sólo cambian cuatro archivos preexistentes de este alcance; todo el material previo SS-01/SS-02/SS-03 conserva sus bytes. En docker-compose.yml se añade únicamente un argumento al comando, conservando íntegramente las variables y presupuestos de SS-03.

Comparación AST antes/después del servicio: la única función modificada es `_request_ip`. create_session, password_matches, eventos, desbloqueo, expiración, cambio de contraseña y revocaciones conservan sus cuerpos. Frontend, Nginx, config, main, auth, router, dependencias, roles, DB y migraciones permanecen intactos. El nuevo helper no mantiene estado, no deniega logins ni vincula sesiones a una IP.

## Modelo de amenazas y controles observados

| Escenario | Evidencia y control actual | Pendiente / efecto de esta entrega |
|---|---|---|
| Muchos intentos a una cuenta | Usuario/estado bloqueados con FOR UPDATE; quinto fallo bloquea por AUTH_LOCK_MINUTES, 15 min predeterminados | El atacante puede inducir el bloqueo. No cambia la política |
| Cuentas inexistentes / enumeración | Dummy bcrypt y 401 «Credenciales incorrectas»; inactivos y bloqueados también devuelven el mensaje genérico | No se prueban tiempos de red ni equivalencia temporal absoluta |
| Ataque repartido por cuentas/orígenes | Cada intento admitido ejecuta bcrypt; alternar identidades evita el contador individual | Requiere presupuesto global compartido antes de bcrypt |
| CPU y eventos | Se verifica contraseña incluso con bloqueo vigente; cada intento crea evento y commit | Sigue pendiente limitar admisiones y agregar rechazos fuera de evento_acceso |
| Prolongación del bloqueo | Durante un bloqueo vigente no se cambia su fecha ni contador | Tras vencer, cinco nuevos fallos pueden iniciar otro bloqueo; no hay garantía frente a ataque sostenido |
| NAT institucional | Muchas personas pueden compartir una dirección; IP no equivale a identidad | No se añade ningún rechazo ni sanción por IP |
| XFF manipulado | Antes se elegía el primer valor si el peer estaba en la lista | Ahora se elige el hop no confiable más cercano, con validación acotada |
| Proxy que reescribe el peer | Uvicorn puede sustituir ASGI client/scheme antes de FastAPI | --no-proxy-headers explícito en los comandos versionados; despliegue efectivo no comprobado |
| Varios procesos / instancias | Los locks del estado de cuenta son DB; no hay contador global de solicitudes | El helper es puro y consistente entre procesos, pero no es rate limiting |
| Origin permitido | main.py exige Origin explícito para login | Un cliente no navegador puede enviarlo: no es una defensa contra automatización |

La guía [OWASP de autenticación](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) trata mensajes genéricos, throttling y riesgo de denegación por bloqueo de cuentas. En SSALFER deben resolverse conjuntamente: bajar el umbral o añadir un cooldown por correo no permite distinguir al dueño de un atacante no autenticado.

## Implementación de origen de red

Nuevo `backend/app/services/request_origin.py`, stdlib exclusivamente:

1. Canonicalizar el peer de socket y las IP exactas configuradas. IPv4-mapped IPv6 se normaliza a IPv4. Peer inválido/ausente produce None; no se inventa identidad usando cabeceras.
2. Sin peer confiable se ignora XFF. No se habilitan CIDR, comodines, nombres DNS ni confianza en toda la red Docker. La configuración existente conserva su validación de IP exactas.
3. Con peer confiable sólo se admite una cabecera XFF, hasta 1024 caracteres y 16 hops. Rechazar como cadena controles/DEL, segmentos vacíos, hostnames, puertos, zonas IPv6 o direcciones no válidas. «Rechazar cadena» significa volver al peer, no bloquear al usuario ni responder 4xx.
4. Validar toda la cadena y recorrerla de derecha a izquierda, saltando exclusivamente proxies configurados; el primer hop no confiable es el origen atribuible. Nunca saltar un intermediario desconocido para confiar en texto a su izquierda.
5. Si todos los hops son confiables, usar el peer conservadoramente. Cabeceras duplicadas, ausentes, demasiado grandes o inválidas también usan el peer. No se consulta Forwarded ni X-Real-IP.

El caso de regresión usa sólo direcciones de documentación: peer confiable 10.0.0.2, XFF `192.0.2.99, 198.51.100.7`. La versión previa atribuía el evento al prefijo 192.0.2.99 controlable por el cliente; la nueva devuelve 198.51.100.7, añadido por el proxy confiable. Se ejecutó el cuerpo previo con datos sintéticos y se confirmó que falla esta expectativa.

| Límite activado | Valor / unidad | Fundamento y alcance |
|---|---|---|
| Longitud XFF | 1024 caracteres | Acota sólo el análisis de esta cabecera; suficiente para la topología propuesta. No limita el cuerpo ni todas las cabeceras HTTP |
| Hops XFF | 16 direcciones | Margen para una cadena pequeña de proxies explícitos. No es una afirmación de topología real |
| Cabeceras XFF | Una | Evita interpretaciones discrepantes de cabeceras duplicadas; fallback a peer, sin lockout |
| Intentos de login nuevos | Ninguno | No se activa presupuesto local/global/por IP sin almacenamiento compartido y pruebas |
| Bloqueo existente | 5 fallos; 15 minutos por defecto, configurable | Se conserva la política vigente, incluidos recuperación/desbloqueo |

Los límites de parsing son constantes deliberadas, no variables de rate limiting. Excederlos degrada la precisión de la traza al peer, sin impedir acceso. No hay mapas por usuario/IP, contadores, temporizadores o logs nuevos que crezcan por solicitud.

## Cadena de confianza exigida antes de desplegar

Cadena propuesta: cliente → proxy HTTPS de entrada administrado → Nginx SSALFER opcional → Uvicorn sin reescritura de headers → FastAPI/helper. Cada proxy confiable debe sobrescribir con una cadena verificada o añadir la IP real de su peer, y no permitir que el cliente elija el sufijo confiable. La selección desde la derecha es coherente con el criterio de último hop no confiable documentado por [Nginx real_ip_recursive](https://nginx.org/en/docs/http/ngx_http_realip_module.html).

El Nginx versionado usa `$proxy_add_x_forwarded_for`, por lo que añade su peer a la cadena. No prueba cómo funciona el proxy externo, ni que existan real_ip/set_real_ip_from seguros o direcciones estables de contenedor. Si el proxy exterior no está en la lista, se atribuirá conservadoramente su dirección; **no resolver añadiendo todos los clientes/NAT o un wildcard como proxies confiables**.

Uvicorn procesa XFF/XFP antes de la aplicación cuando su política lo permite; por eso se desactiva esa segunda interpretación mediante --no-proxy-headers en Dockerfile, Compose base y override dev. Prod y SSALFER no redefinen ese comando. La [configuración Uvicorn](https://uvicorn.dev/settings/) permite controlar proxy headers; su [middleware en la versión fijada 0.49.0](https://raw.githubusercontent.com/Kludex/uvicorn/0.49.0/uvicorn/middleware/proxy_headers.py) modifica client/scheme. No basta definir AUTH_TRUSTED_PROXY_IPS si otro nivel ya sustituyó el peer.

Antes de desplegar, acreditar conexiones y ACL de red: sólo proxies administrados deben alcanzar la entrada del backend; puertos loopback versionados no demuestran firewall o exposición real. Verificar el comando efectivo de cada réplica, incluyendo despliegues externos a estos Compose. Confirmar valores exactos de proxies contra sockets reales, sin volcados de .env ni secretos.

**Regresión a revisar:** --no-proxy-headers también impide interpretar X-Forwarded-Proto. Las cookies Secure y CSRF siguen usando configuración/Origin, no request.scheme; pero redirecciones automáticas de slash y URLs absolutas generadas por framework pueden observar http detrás de TLS. Antes de integrar, probar las rutas canónicas y con slash en QA HTTPS, comprobar Location/esquema/OpenAPI; resolver esquema en un único nivel administrado sin reintroducir confianza arbitraria en XFF. No se modifican ahora main.py ni middleware de esquema para ocultar esa dependencia. No se acredita compatibilidad del proxy de producción.

Un proxy configurado como confiable que sobrescriba XFF con datos del cliente, o un proceso comprometido en esa misma identidad de red, sigue pudiendo falsear trazas. La aplicación sólo puede verificar estructura y peer, no la honestidad de ese proxy. Las cabeceras inválidas no registran su contenido ni un evento adicional.

## Diseño del limitador compartido — no implementado

### Decisión de infraestructura

Se recomienda evaluar **un almacén Redis dedicado de admisión**, sin exposición pública, con identidad/ACL mínima, timeouts y cotas de memoria/conexiones, común a todas las réplicas y procesos. Requiere autorización de servicio/dependencia/configuración y QA desechable: no se añade a Compose ni se instala aquí. Redis permite [scripts atómicos](https://redis.io/docs/latest/develop/programmability/eval-intro/), pero eso no prueba una implementación de rate limiting: deben probarse conjuntamente todos los presupuestos y su recuperación.

Alternativas: PostgreSQL con tabla/operación atómica específica y retención puede coordinar instancias, pero necesita migración nueva, permisos y pruebas de concurrencia/fallos; no usar scans del histórico ni advisory locks con espera como sustituto. Nginx shared zones sirven para procesos de una misma instancia de proxy, no para varias máquinas independientes ni para identidad normalizada de OAuth2 form por sí solas. Un limitador local sólo sería una defensa adicional explícitamente local; no se incorpora ni se presenta como global.

### Punto de admisión y presupuestos

- En la única ruta de login, limitar primero bytes de cuerpo/cabeceras y tiempo de lectura en el proxy y ASGI, antes de parsear form o abrir DB. Rechazar explícitamente un cuerpo excesivo, sin truncarlo. No aplicar esos tamaños a uploads GIS/documentales.
- Tras parseo acotado, normalizar identidad exactamente como create_session (strip/lower); calcular claves mediante HMAC con secreto propio compartido, separado de tokens de sesión. No guardar el correo/IP en claro en claves, logs o etiquetas de métricas. Mantener límite de cardinalidad y TTL; HMAC sigue siendo dato seudonimizado sujeto a acceso/retención.
- Ejecutar una sola operación atómica de admisión que compruebe presupuesto global y combinación identidad/origen confiable. Las cuentas existentes, inexistentes, inactivas y bloqueadas entran por el mismo algoritmo **sin consultar su existencia**. No lanzar DB/bcrypt si no se admite. En Redis Cluster, diseñar claves/script en un slot compatible o elegir topología que garantice la operación conjunta.
- La IP sirve de señal agregada, no de causa única de bloqueo en una NAT compartida. Rotar cuentas desde un origen y rotar orígenes contra una cuenta exige correlación más presupuesto global. Un bucket sólo por identidad también permite denegar al dueño: no activarlo como sanción larga automática ni afirmar que distingue intención.
- Ventanas/recargas finitas, usando reloj del coordinador, sin renovar la penalización/TTL por peticiones rechazadas. No incrementar intentos_fallidos, crear estado de cuenta ni extender bloqueado_hasta por un rechazo del limitador. No resetear todos los presupuestos con un login exitoso ni permitir alternar errores/éxitos para evadir el límite global.
- Separar tasa de admisiones de concurrencia bcrypt. Una cota de peticiones por segundo no limita por sí sola hashes simultáneos o peticiones ya en vuelo. Dimensionar concurrencia total entre réplicas, sin colas ilimitadas ni sleeps mientras se retienen DB locks. Los semáforos locales no equivalen a cota compartida. Si se usan leases, no reutilizar una plaza sólo por vencer TTL mientras un bcrypt anterior siga vivo; diseñar supervisión/terminación o partición explícita de capacidad antes de afirmar garantía global.

No se seleccionan cifras de producción de RPS/burst/concurrencia sin medir coste bcrypt y pico legítimo multiusuario en QA, incluyendo NAT institucional. No hay variables ficticias para aparentar un control activo. Para ensayos funcionales futuros pueden usarse presupuestos artificiales pequeños (por ejemplo dos admisiones por ventana corta), **sólo en QA**, sin inferir capacidad del servidor.

### Respuestas, fallos y trazabilidad

Admisión rechazada por cuota: 429 con cuerpo genérico único «Demasiadas solicitudes; inténtalo más tarde», Retry-After entero acotado y Cache-Control: no-store; sin revelar existencia, motivo de bloqueo, correo o contadores. No borrar cookies de sesiones existentes ni revocarlas por rate limiting. El login ya admitido conserva el 401 genérico o la creación actual de sesión/cookies.

Coordinador indisponible: definir explícitamente 503 genérico y Retry-After acotado antes de DB/bcrypt para login, sin fallback ilimitado local. Esa elección afecta disponibilidad de nuevos accesos y necesita aceptación operativa; las sesiones existentes no deben depender del almacén de admisión. Failover, pérdida/evicción de contadores y reloj/reinicio deben tener comportamiento probado: la atomicidad de un script no garantiza estado durable ni límites bajo todas las fallas. No reclamar cotas exactas con replicación asíncrona sin analizar esa ventana.

Los 429 no insertan evento_acceso ni auth_event de DB por petición. Contadores agregados de admisiones/rechazos por ventana y tipo limitado, alertas y resúmenes acotados conservan trazabilidad operativa sin replicar la carga. Identidades seudonimizadas sólo en una salida protegida, con muestreo/retención y cardinalidad máximos; no incluirlas como labels ilimitados. El propio access log de proxy/API debe revisarse con rotación/cotas: no basta ahorrar eventos DB. Los eventos del login admitido y las transiciones de estado conservan su contrato actual.

### Bloqueo inducido y recuperación

La política actual bloquea al quinto fallo sin prueba de posesión. Un atacante que conoce el correo puede consumir esos cinco fallos, esperar recuperación y repetir; un bucket por cuenta puede producir la misma denegación incluso sin tocar PostgreSQL. Ningún límite previo a verificar la contraseña distingue infaliblemente al dueño de un atacante con los mismos identificadores públicos.

En esta entrega se conserva el desbloqueo administrativo/recuperación y la fecha fija durante un bloqueo vigente. Para resolver la disponibilidad selectiva hay que revisar con el dueño funcional la recuperación acreditada y/o la semántica de bloqueo, sin CAPTCHA ni servicio externo automático. No se cambia esa política sin autorización ni se reduce dummy bcrypt sólo para bloqueados: introduciría una nueva diferencia temporal. El limitador reduce capacidad de abuso; no se promete erradicación de bloqueos sostenidos con el contrato actual.

## Pruebas ejecutadas y alcance de la evidencia

Antes de ejecutar se inspeccionaron conftest, imports y efectos de las suites. El conftest backend exige una base de prueba explícita, importa la app/engine y sus fixtures escriben en PostgreSQL. No se ejecutó pytest ni collect-only. La suite nueva usa stdlib y datos sintéticos: importa directamente el helper puro y extrae por AST cuerpos de funciones seleccionadas de fuentes reales, sin ejecutar imports/top-level, dummy hash bcrypt, routers, DB engine o startup. ORM, bcrypt, Request, Response y middleware HTTP se sustituyen por dobles. La extracción de funciones no acredita integración del framework ni constraints/triggers/atomicidad DB.

```sh
python3 -B -m unittest discover -s tests/security -p 'test_auth_origin_security.py' -v
# Ran 32 tests; OK
python3 -B -m unittest discover -s tests/security -p 'test_*.py' -v
# Ran 81 tests; OK (incluye los 32 anteriores y las 49 regresiones SS-02/SS-03)
```

| Escenario | Evidencia ejecutada | Límite de cobertura |
|---|---|---|
| XFF directo falsificado / prefijo inyectado / hops confiables | Helper y wrapper reales con peers sintéticos | Sin proxy ni Uvicorn nativo |
| Duplicados, IPv4/IPv6, mapped, controles, inválidos, límites | Casos positivos/negativos y fronteras 1024/16 | No mide todo el parser HTTP del servidor |
| NAT compartida | Helper sin estado y logins sintéticos independientes admitidos | No demuestra equidad de un limitador futuro |
| Concurrencia | 32 resoluciones sintéticas en cuatro threads, deterministas | No prueba locks DB ni un contador distribuido |
| Existente/inexistente/inactivo/bloqueado | 401 genérico y un password_matches simulado por intento | No mide timing bcrypt/HTTP |
| Quinto fallo y recuperación | Estado/evento simulado; bloqueo vigente no se extiende; expirado reinicia y permite éxito | Persistencia, triggers y carreras requieren DB QA |
| Eventos y procedencia | Un evento por intento actual, agente saneado y mismo origen en sesión/evento | El crecimiento por abuso sigue sin limitarse |
| Cookies | Función real con Response simulado conserva Secure/HttpOnly/SameSite/__Host/path/max-age | No navegador/HTTPS ni FastAPI nativo |
| CSRF | Cuerpo real del guard: Origin login, ausencia/token válido/inválido y cierre del DB simulado | No prueba criptografía/DB, orden completo ASGI o middleware desplegado |
| Arranques | Flags en Dockerfile/base/override; prod/SSALFER no redefinen comando | Revisión textual/YAML, no Compose efectivo ni contenedores |
| Rechazo por exceso / intentos distribuidos / recuperación de cuotas | **No ejecutado: no hay limitador compartido implementado** | Debe pasar aceptación siguiente antes de activar |

Además: fallo esperado de la función previa ante prefijo XFF sintético; YAML de los cuatro Compose analizado con safe_load ya disponible (sin expansión de .env); AST de autenticación sin cambios salvo _request_ip; hashes de material previo preservados. git diff --check y comprobación inversa --check del patch sin aplicar/revertir. No se imprimieron secretos ni se leyeron archivos .env.

Pruebas omitidas: TestClient/FastAPI/Uvicorn reales por ausencia de esas dependencias; suites backend que necesitan PostgreSQL por falta de BD QA autorizada; navegador/proxy HTTPS/topología real; rate limiting distribuido y carga. No se instalaron herramientas para suplirlos. Las pruebas frontend existentes no se reejecutaron porque no se modifica frontend ni su lógica de sesión.

## Aceptación pendiente para limitador e infraestructura

| Prueba futura en QA desechable | Resultado exigido |
|---|---|
| Umbral pequeño parametrizado con N y N+1 solicitudes sintéticas | N admisiones; siguiente 429 antes de bcrypt/DB/evento, Retry-After finito; mismo tratamiento con cuentas existentes/inexistentes |
| Usuarios distintos detrás de la misma NAT | Acceso legítimo sin sanción general por IP; documentar límite de capacidad global inevitable y tiempos de espera |
| Identidades y orígenes alternados entre dos o más procesos/réplicas | Un único presupuesto global; sin multiplicación por número de procesos |
| Solicitudes concurrentes en borde de cuota | Operación atómica sin sobre-admisión; fallos no consumen/actualizan parcialmente presupuestos ajenos |
| Esperar ventana y enviar rechazos durante ella | Se recupera según plazo fijo; el atacante no prolonga el plazo por solicitudes denegadas; no confundir esto con garantía de disponibilidad frente a nuevas oleadas |
| Coordinador caído/reiniciado/particionado, eviction y failover | Resultado explícito, finito y documentado; no bcrypt/DB ilimitado ni borrado de sesiones existentes |
| Ataque a cuenta bloqueada / desbloqueo administrativo | Rechazos del limitador no cambian estado; verificar recuperación real y riesgo residual de re-bloqueo |
| Cookies, CSRF, roles, expiración/revocación | Suites auth/RBAC/credenciales en BD QA desechable autorizada sin regresión |
| Cadena TLS/proxies/peer real, acceso directo y XFF malicioso | Ningún prefijo del cliente se convierte en origen confiable; comandos/ACL/red/scheme y Location comprobados |
| Volumen de eventos/logs/métricas | Rechazos agregados, storage/cardinalidad acotados, sin secretos ni PII completa |

No se han ejecutado estas pruebas de aceptación de infraestructura; esta tabla no es una evidencia de cierre.

## Archivos, parche y riesgos de revisión

Modificados: backend/app/services/authentication.py, backend/Dockerfile, docker-compose.yml, docker-compose.override.yml. Nuevos: backend/app/services/request_origin.py, tests/security/test_auth_origin_security.py, este informe y SS-04-ETAPA1-CORRECCION-2026-10-28.patch. Ningún otro archivo previo cambia.

El patch se genera contra snapshots locales anteriores a esta intervención, no contra HEAD, e incluye exclusivamente los cuatro cambios anteriores más helper, pruebas e informe (no se incluye a sí mismo). Requiere la base local con las remediaciones previas: no duplicarlas ni reemplazarlas. Los informes/patches previos se conservan sin modificación. Los hashes finales permiten identificar las fuentes revisadas:

| Archivo | SHA-256 final |
|---|---|
| backend/app/services/authentication.py | `c6aa445c565db2c7b536e596ef3dd1a0d0cab8820ee2d6fa3bda904ec0ba1f09` |
| backend/Dockerfile | `94c0dbc2602b52f6a9b88587a82416e0d8ce83788e04b84fb23134e856f773d8` |
| docker-compose.yml | `6122b1bcc1639f36e40de2ee398c4e18dae210dac31d26d38b75fba9d1b97fb6` |
| docker-compose.override.yml | `f590a6396ab5af9556d87bc047abb6ebfcc1736ca839c41bd5dd4ac76705fafe` |
| backend/app/services/request_origin.py | `defab18911b29fd771b2ec7c7b895a2b29e62a16c00b9b98c545e62f7bc95943` |
| tests/security/test_auth_origin_security.py | `62efe433284cf009262d883d8b4d32e8f02fa16a314e331bf61677c043e3c7b8` |

Riesgos de regresión: topologías de proxies no inventariadas producirán una IP de proxy en auditoría; cabeceras duplicadas antes aceptadas ahora caen al peer; IPv4-mapped cambia a representación IPv4; direcciones scope/puerto inválidas no se persisten; esquema/redirects de Uvicorn requiere la QA TLS descrita. No se modifica el comportamiento de autenticación según esa IP, ni se hacen cierres de sesión por cambios de red.

Riesgos residuales: admisiones/bcrypt/eventos aún sin límite complementario, bloqueos inducibles, capacidad global no probada, confianza/ACL del proxy sólo propuesta y no constatada. La entrega es **parcial y pendiente de validación integrada**, lista para revisión de código; no permite declarar SS-04 resuelto ni el despliegue institucional preparado.

## Diff de archivos preexistentes de esta intervención

```diff
diff --git a/backend/app/services/authentication.py b/backend/app/services/authentication.py
--- a/backend/app/services/authentication.py
+++ b/backend/app/services/authentication.py
@@ -2,7 +2,6 @@
 import hmac
 import secrets
 from datetime import datetime, timedelta, timezone
-from ipaddress import ip_address
 
 import bcrypt
 from fastapi import HTTPException, Request, status
@@ -13,6 +12,7 @@
 from ..config import AUTH_SETTINGS
 from ..passwords import is_within_bcrypt_limit
 from .common import commit_or_conflict, set_audit_context
+from .request_origin import resolve_client_ip
 
 
 _DUMMY_PASSWORD_HASH = bcrypt.hashpw(
@@ -51,17 +51,11 @@
 
 def _request_ip(request: Request) -> str | None:
     peer = request.client.host if request.client else None
-    candidate = peer
-    if peer in AUTH_SETTINGS.trusted_proxy_ips:
-        forwarded = request.headers.get("x-forwarded-for", "")
-        if forwarded:
-            candidate = forwarded.split(",", 1)[0].strip()
-    if not candidate:
-        return None
-    try:
-        return str(ip_address(candidate))
-    except ValueError:
-        return None
+    return resolve_client_ip(
+        peer,
+        request.headers.getlist("x-forwarded-for"),
+        AUTH_SETTINGS.trusted_proxy_ips,
+    )
 
 
 def _event(
diff --git a/backend/Dockerfile b/backend/Dockerfile
--- a/backend/Dockerfile
+++ b/backend/Dockerfile
@@ -15,4 +15,4 @@
 
 EXPOSE 8000
 
-CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
+CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers", "--reload"]
diff --git a/docker-compose.yml b/docker-compose.yml
--- a/docker-compose.yml
+++ b/docker-compose.yml
@@ -88,7 +88,7 @@
     image: software-pa-backend
     build:
       context: ./backend
-    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
+    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
     restart: always
     environment:
       <<: *backend-environment
diff --git a/docker-compose.override.yml b/docker-compose.override.yml
--- a/docker-compose.override.yml
+++ b/docker-compose.override.yml
@@ -9,6 +9,7 @@
       - 0.0.0.0
       - --port
       - "8000"
+      - --no-proxy-headers
       - --reload
     volumes:
       - ./backend:/app
```

El [parche completo](SS-04-ETAPA1-CORRECCION-2026-10-28.patch) añade también helper, pruebas y este documento. **Se detiene la intervención para revisión.** No se instala el coordinador propuesto, no se despliega, no hay commits/push/merge y no se continúa con otros hallazgos.
