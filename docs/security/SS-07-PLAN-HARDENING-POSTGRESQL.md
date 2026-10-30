# SS-07: plan de hardening PostgreSQL, sin ejecución autorizada

Fecha: 2026-10-28. **Diseño y verificador preparados; permisos efectivos sin observar. No aplicar cambios de privilegios en esta etapa.** Referencia `dev`, SHA `683ff75613768de28a7127c7e33a6e2ef4fc40ff` y correcciones locales existentes preservadas.

Consultar [auditoría](SS-07-ETAPA1-AUDITORIA-PRIVILEGIOS-2026-10-28.md) y [matriz](SS-07-MATRIZ-PRIVILEGIOS-2026-10-28.md). SS-05 sigue en diseño; esta propuesta no cambia la política funcional de documentos o de proyectos/personas/GIS.

## Puertas y orden de trabajo futuro

| Paso | Actividad futura | Evidencia y autorización necesarias |
|---|---|---|
| 1 | Confirmar clon QA desechable y responsables del inspector/runtime/migrador/owner | Autorización externa con ID, origen del clon, ausencia de datos institucionales o anonimización aprobada, aislamiento de red, endpoint/identidad y plan de descarte. Nombre `software_pa_test` no basta |
| 2 | Revisar/preparar23 consultas de sólo metadatos y ejecutarlas manualmente en ese clon | Aprobación independiente de conexión/inspección; psql15 autorizado, sin heredar entorno/conexión de la API |
| 3 | Comparar catálogo efectivo, matriz e inventario léxico, registrar objetos extra/faltantes y resultados no observables | Owner real, PUBLIC, defaults por creador, membresías/atributos/columnas, SECURITY DEFINER y dependencias; no interpretar filas ausentes como permisos denegados |
| 4 | Diseñar un diff administrativo de privilegios por objeto y rol | Revisión DBA/backend/AppSec; revisar RAN TEMP, catálogo FOR SHARE, bitácora definer y GIS append-only. No generar REVOKE automáticamente del JSON |
| 5 | Ensayar hardening y recuperación en QA, con identidades reales separadas de prueba | Nueva autorización explícita de cambios QA; tests de operaciones sintéticas y denegaciones, restauración de ACL/owner/defaults comprobada |
| 6 | Preparar migración nueva o script administrativo separado para BD existente y procedimiento de instalaciones nuevas | No editar baseline/históricas ni simular arreglo de una BD editando bootstrap. Elegir número futuro sólo tras revisar cadena vigente |
| 7 | Revisión final y despliegue/permisos efectivos, si posteriormente se autorizan | No incluidos en esta entrega; artefacto exacto, respaldo/recuperación, ventana y comprobaciones posteriores |

## Preparación offline y ejecución opt-in futura

El preparador `ss07/preparar_verificador.py` **nunca conecta**, importa driver, carga dotenv, hereda DB_RUNTIME, ejecuta shell/psql o cambia permisos. Lee sólo el JSON que el operador indique y la plantilla revisada; genera un archivo nuevo0600. No añadir credenciales al JSON. El ejemplo deshabilitado no puede generar una verificación hasta completar aprobación y confirmación de clon.

Procedimiento futuro, no ejecutado en esta fase:

1. Fuera del repositorio público, registrar autorización del clon y comprobar su identidad/aislamiento mediante el procedimiento de operación. Una marca cluster_name es sólo comprobación adicional, no prueba de que sea desechable. No cambiar esa marca desde el verificador.
2. Crear configuración QA propia0600 con los campos exactos de `config-ejemplo.json`: autorización, confirmación de clon, base, IP numérica y puerto del servidor, marca de cluster, inspector y nombres runtime/migrador. Nombres de roles son metadatos, no contraseñas. Mantener flags/identidades reales fuera de informes públicos.
3. Ejecutar únicamente la preparación offline, tras la autorización correspondiente:

```text
python3 -B docs/security/ss07/preparar_verificador.py \
  --config /ruta/qa/config-ss07.json \
  --autorizacion-qa QA-ID-APROBADO \
  --clon-desechable-verificado \
  --salida /ruta/qa/ss07-verificacion-preparada.sql
```

4. Revisar el SQL generado y sus guardas. El preparador no ejecuta ese archivo. Usar psql15 con `-X`, host/IP, puerto, base e inspector **explícitos**, con `-v SS07_QA_AUTORIZADA=1` y archivo preparado; este documento no proporciona un comando de conexión listo con destino institucional ni autoriza ejecutarlo.
5. Lanzar desde un entorno limpio y aprobado: sin DATABASE_URL/DB_*/PGSERVICE/PGOPTIONS/PGHOST heredados de la app; autenticación QA protegida por mecanismo aprobado fuera de argv, reportes y consola. No cargar .env, no confiar en un servicio/libpq o archivo de contraseñas habitual implícito. Si se usa un fichero de autenticación QA, debe ser exclusivo y0600; no crearlo ni mostrar su contenido en esta fase.
6. El script exige opt-in psql y compara destino/inspector antes de Q00. Requiere conexión TCP cuya IP de servidor/puerto observado coincida; socket Unix, NAT de puerto diferente o marca no coincidente fallan la guarda. No relajarla automáticamente para “hacer pasar” QA.
7. Exigir Q00 con identidades existentes/separación revisada,23 secciones completas y marcador final `SS07_INSPECCION_COMPLETA_REVISAR_OMISIONES_Y_RESULTADOS`. Un rechazo puede usar `\quit` y no dar por sí solo un exitcode fallido: no evaluar el éxito únicamente por exitcode.
8. Guardar la salida protegida, con sesión/fecha/artefacto/rol inspector y omisiones registradas. Si falta privilegio de inspección o hay timeout, esa sección y posteriores quedan no observadas; no resumir como “sin privilegios excesivos”. No escalar o volver a ejecutar automáticamente.

La transacción es READ ONLY/REPEATABLE READ y termina ROLLBACK; SET LOCAL sólo ajusta la sesión del verificador.15s por sentencia/1s de locks son límites QA del inspector; no cambian runtime o PostgreSQL institucional ni representan un deadline global. Se consulta pg_catalog y funciones de privilegios, no filas funcionales, parámetros SQL, archivos del servidor ni cuerpos desplegados. No se usa SET ROLE: las comprobaciones se refieren a OIDs de roles y no prueban autenticación/SET ROLE real por esos usuarios.

## Catálogo de consultas y criterio de interpretación

| ID | Cobertura | Qué no demuestra |
|---|---|---|
| Q00 | Inspector actual/sesión, versión, roles objetivo existentes y comparación runtime/migrador | Coincidencia no prueba clon ni login efectivo usado por la API desplegada |
| Q01–Q03 | Atributos, aristas/grantor/ADMIN OPTION, MEMBER y USAGE transitivos | No confundir membresía con herencia inmediata ni atributos especiales con permisos ordinarios heredados; acceso administrativo efectivo debe revisarse |
| Q04–Q05 | ACL/owner de BD, CONNECT/CREATE/TEMP; USAGE/CREATE schemas | CONNECT en otra BD no inventaría sus objetos; no se abre esa conexión |
| Q06–Q08 | Relaciones, propietarios, ACL, RLS, permisos efectivos y de columnas | ACL no expresa todos los efectos del ownership; permisos efectivos se cruzan con schema y políticas, y no prueban operaciones de negocio |
| Q09–Q10 | Privilegios y pertenencia de secuencias | No avanza ni lee valores; probar generación de IDs es otra actividad de QA |
| Q11–Q13 | Rutinas por OID/tipos, definer/search_path/EXECUTE, ACL expandidas y defaults | No imprime cuerpo SQL ni acredita que su implementación desplegada coincida con Git. Default ACL vacío no equivale a deny y cada creador importa |
| Q14 | Triggers habilitados/internos/diferidos y función/owner | Un trigger habilitado puede ser modificable por owner/superuser; no prueba inmutabilidad frente a ese actor |
| Q15–Q16 | Extensiones/miembros, dependencias/flags de vistas | No ejecuta PostGIS ni garantiza equivalencia de definiciones o rendimiento |
| Q17–Q18 | search_path rol-BD y metadatos de RLS | No muestra otros parámetros, expresiones de políticas o sesiones/datos; no introduce RLS |
| Q19–Q20 | USAGE de tipos y lenguajes | USAGE de lenguaje no otorga por sí solo CREATE en schema; no implica necesidad de crear funciones para runtime |
| Q21–Q22 | EXECUTE de rutinas administrativas pg_catalog y ACL de parámetrosPG15 | No invoca rutinas, lee archivos o cambia parámetros. No cubre todas las posibilidades administrativas de extensiones ajenas: inventariar las detectadas |

## Propuesta de hardening posterior

### Identidades y propiedad

Objetivo: login runtime sólo miembro del contrato necesario, sin propiedad directa o heredable de BD/esquemas/tablas/vistas/secuencias/funciones/extensiones; sin SUPERUSER/CREATEDB/CREATEROLE/REPLICATION/BYPASSRLS, ADMIN OPTION ni roles predefinidos de lectura/escritura global, archivos/programas o señales salvo necesidad expresamente justificada. No asumir que NOBYPASSRLS importa si no existe RLS; evita un exceso potencial, pero no implementa el aislamiento por proyecto.

Separar owner de objetos de aplicación de login operativo; owner NOLOGIN confiable y migrador con acceso controlado a ese owner para DDL aprobado. La API no debe poder adoptar ese rol. Los derechos de propietario son inherentes: un REVOKE DML no quita la capacidad de ALTER/DROP de quien puede actuar como owner. [Privilegios PostgreSQL15](https://www.postgresql.org/docs/15/ddl-priv.html).

Provisionar primer admin funcional mediante identidad administrativa acotada y temporal según el script revisado, sin elevar el runtime para permitir DISABLE TRIGGER. Separar importador RAN/operaciones de mantenimiento si se desea retirar TEMP al login API; hasta probar esa separación, documentar la necesidad y riesgo existente. No modificar herramientas previas SS-10 o SS-02 en esta intervención.

### Objetos existentes

Preparar una allowlist por objeto/operación después de Q00–Q22. Mantener SELECT de schema_migrations por health y negar I/U/D/TRUNCATE al runtime; no impedir al runner migrador registrar sus cambios. Conservar las restricciones de009/025/026 y no recrear grants amplios después.

Reducir UPDATE de tablas realmente append-only y escrituras sobre vistas cuando QA demuestre que no son necesarias. Conservar UPDATE de estados, cierres lógicos, usuarios/sesiones, candidatos y flags GIS válidos. Mantener SELECT requerido por WHERE/RETURNING/relaciones y triggers invoker. Si se desea UPDATE por columnas, definir columnas exactas y probar ORM/locks; no sustituir la política RBAC de API por permisos de tabla más amplios o más estrechos sin análisis.

Resolver específicamente catálogo tipo documental FOR SHARE: no aplicar S-only porque el SQL de bloqueo puede requerir UPDATE. Las revisiones GIS tienen un diseño append-only con advisory lock en030; no “arreglar” un error concediendo UPDATE otra vez. Las secuencias se evalúan por uso serial/identity y ownership: USAGE puede bastar para nextval, UPDATE permite setval y no se justifica por generar IDs. No resetear secuencias para comprobar permisos.

Revisar PUBLIC y grants directos/indirectos antes y después; revocar sólo al contrato no elimina otro grant. Antes de restringir un objeto de extensión, distinguir miembros y dependencias, mantener upgrades soportados y probar PostGIS; no alterar ownership internamente de una extensión ni revocar todas sus rutinas a ciegas.

### SECURITY DEFINER, namespace y actor

Revisar fn_audit_log y cualquier definer adicional descubierto. Propietario dedicado con permisos mínimos; schema(s) confiables y referencias calificadas. El `search_path` seguro debe excluir namespaces escribibles por runtime/PUBLIC y colocar pg_temp explícitamente al final cuando corresponda, en lugar de depender de resolución implícita. Validar todas las relaciones/funciones/operadores/tipos empleados por la auditoría; no basta cambiar un SET sin probar el cuerpo. [Seguridad de funciones SECURITY DEFINER](https://www.postgresql.org/docs/15/sql-createfunction.html).

Revisar EXECUTE de PUBLIC y ACL de cada firma, incluidas rutinas no necesarias. [Crear un trigger](https://www.postgresql.org/docs/15/sql-createtrigger.html) requiere permisos propios; ni quitar TRIGGER ni observar un trigger habilitado elimina la capacidad inherente del propietario para cambiar controles. Probar creación/mantenimiento y disparo de triggers después del hardening, sin asumir que retirar EXECUTE de una función instalada impide por sí solo su ejecución por trigger.

TEMP y CREATE public deben evaluarse por permisos efectivos/owner/membresías y por el contexto definer, no por versión PostgreSQL nominal. La solución futura debe preservar el actor transaccional y los eventos funcionales. `app.current_user_id` es un dato suministrado por la identidad compartida: cambiar ACL no crea autenticación humana independiente. Si se quiere reducir esa confianza, requiere un diseño de identidades/RLS/procedimientos completo fuera de esta etapa.

### Objetos futuros y default privileges

Cambiar defaults **para cada rol creador real**, globales y por esquema, de acuerdo con la allowlist; no sólo para el login migrador nominal si ejecuta DDL como owner. Un default nuevo no revoca ACL de objetos existentes y un REVOKE de objetos existentes no modifica los futuros. Las concesiones por schema se combinan con las globales; deben analizarse conjuntamente. [ALTER DEFAULT PRIVILEGES PostgreSQL15](https://www.postgresql.org/docs/15/sql-alterdefaultprivileges.html).

Evitar defaults S/I/U/EXECUTE indiscriminados que vuelvan a conceder UPDATE a historia o acceso a nuevas funciones privilegiadas. La migración futura debe conceder explícitamente lo necesario en cada nuevo objeto, con prueba de instalación limpia y de actualización. No editar001 para aparentar corrección de un PGDATA ya inicializado: usar un artefacto administrativo nuevo o migración forward-only revisada.

## Contrato de artefacto correctivo futuro

Propuesta: una nueva migración `NNN_hardening_privilegios_runtime.sql` para ACL/defaults de objetos de aplicación y un script administrativo separado de provisionamiento/ownership cuando se necesiten facultades de cluster. `NNN` es un marcador de diseño, no un archivo creado ni un número reservado. Los dos artefactos necesitan nueva aprobación, revisión y ejecución QA antes de definir instrucciones concretas.

Entradas esperadas: OIDs/nombres verificados de login runtime, contrato, owner y migrador; catálogo autorizado de objetos y firmas; defaults de cada creador; precondiciones de las migraciones aplicadas; ACL de recuperación custodiadas. Salidas: cambios de privilegios específicos y comprobaciones efectivas antes/después, sin contraseñas en SQL. No aceptar una lista de roles/objetos suministrada sin contrastar con el catálogo.

La migración no debe tocar filas funcionales, RBAC, hashes, geometrías o esquema de expedientes; mantiene las revocaciones append-only y la auditoría. El script administrativo no debe tomar credenciales runtime como administrador ni hacer cambios en todos los objetos de un cluster por patrón. Hasta conocer Q00–Q22 y las dependencias de QA, escribir GRANT/REVOKE exactos sería dar por demostrados permisos y necesidades todavía desconocidos; por ello aquí se entrega su especificación y orden, no SQL correctivo ejecutable.

## Orden del script correctivo futuro, no generado como ejecutable

1. Preflight con catálogo/roles/owners/defaults y fingerprint del estado QA esperado; comprobar no confundir runtime/migrador, y que exista acceso administrativo de recuperación independiente.
2. Respaldar metadatos ACL/ownership/defaults y procedimiento de restauración bajo custodia protegida, sin secretos o expedientes en reporte. No usar un rollback que active permisos amplios indiscriminadamente.
3. Preparar roles/owners/migrador/importador autorizados y sus dependencias antes de retirar acceso anterior. Si se necesita reasignar propiedad, determinar alcance exacto; no ejecutar REASSIGN OWNED global por reflejo.
4. Asegurar capacidad de auditoría/validación bajo su owner, tipos/funciones/secuencias y permisos mínimos del contrato. Ensayar sesiones nuevas y existentes.
5. Revocar sólo excesos demostrados de objetos existentes/PUBLIC/membresías, manteniendo salud/auth/GIS/documentos/reportes y los flujos auxiliares acordados.
6. Ajustar defaults por creador real para futuros objetos y ensayar una migración sintética; no hacer grants generales después de las revocaciones selectivas.
7. Verificar Q00–Q22 y pruebas de aceptación. Aplicar un conjunto transaccional donde PostgreSQL lo permita; separar operaciones de extensión u otras tareas que requieran procedimiento propio.
8. Si falla, rollback transaccional antes de confirmar o restauración de ACL/owners/defaults exactos respaldados mediante admin independiente, con nueva verificación. No elevar runtime a SUPERUSER ni deshabilitar auditoría para recuperar servicio. Cambios de ownership/credenciales, conexiones abiertas y despliegue tienen planes separados; no se promete reversión universal con un único BEGIN.

## Pruebas QA futuras de mínimo privilegio

No se ejecutan aquí. Los ensayos de DML/DDL negativo escriben o intentan escribir sobre objetos sintéticos propios en un clon autorizado; no forman parte del verificador de sólo metadatos.

| Caso | Evidencia esperada |
|---|---|
| Conexiones runtime/migrador/inspector | Identidades diferentes cuando el diseño lo requiere, owner no alcanzable por runtime, sin atributos peligrosos; no probar con SET ROLE del admin como sustituto de autenticar el login real |
| Prohibiciones runtime | No puede crear/alterar/borrar objetos, modificar funciones/triggers, otorgar privilegios/roles, instalar extensiones o escribir schema_migrations; verificar con recursos sintéticos, sin tocar controles institucionales |
| Login y sesiones | Bcrypt, bloqueo/rate limit previo, eventos, CSRF, creación/expiración/heartbeat/revocación, estado de usuario y locks siguen funcionando; no se cambian roles funcionales |
| Auditoría | DML válido genera bitácora con actor; runtime directo no altera auditoría. Owner definer conserva privilegios; probar ausencia de shadowing sólo en QA aislada |
| Documentos | Alta, clasificación FOR SHARE, carga SS-06/SS-12, listado, descarga y bajas actuales preservadas. No implementar SS-05 ni borrar versiones/archivos para ensayar permisos |
| GIS | Staging/conciliación/confirmación/revisiones y decisiones con locks; catálogos, geometrías Z/M/SRID y PostGIS funcionan. No devolver UPDATE a append-only por conveniencia |
| Reportes/health | SELECT schema_migrations y vistas/reportes SS-11 válidos; no se requieren escrituras en vistas para leer |
| Secuencias/defaults | INSERT/RETURNING serial/identity sin grant excesivo; owner de auditoría y objetos futuros bajo cada creador tienen permisos correctos. No usar nextval/setval en el verificador |
| Auxiliares | Importación RAN TEMP con identidad segregada o excepción aprobada, mantenimiento y bootstrap fuera del runtime HTTP; no compartir secretos con GDAL |
| Recuperación | Demostrar rollback/restauración de ACL/defaults/owners en clon, sesiones/pool y acceso admin de emergencia; registrar resultado y límites |

## Pruebas estáticas de esta etapa

21 pruebas descubiertas:20 aprobadas y1 omitida. El test pglast se omite porque no hay parser instalado. Las pruebas efectivas cubren controles opt-in y destino, no ejecución/conexión en el preparador, lista de fuentes/funciones de metadatos, rechazo de DML/DDL/COPY/escapes, balance léxico, identificación runtime/migrador, salida privada exclusiva, sentinelas no impresas y preservación SHA de30 migraciones y cobertura de76 modelos.

La sintaxis SQL completa, resolución de firmas/catálogos PostgreSQL15, permisos del inspector, comportamientos serial/identity/locks, grants aplicados y PostGIS quedan pendientes QA. No se inventa una validación nativa con un parser artesanal: los checks léxicos limitan cambios accidentales en una plantilla fija, no certifican SQL arbitrario.

## Aceptación antes de cambiar privilegios o desplegar

- Autorización separada de conexión QA y de cambios de permisos; clon identificado y aislamiento comprobado por operación.
- Catálogo efectivo y omisiones documentados, sin datos de negocio/credenciales; runtime y migrador observados por login real y no inferidos de archivos.
- Matriz reconciliada con triggers/funciones/owners/PUBLIC/defaults/secuencias/PostGIS y auxiliares; resolver catálogo FOR SHARE y RAN TEMP.
- Diff administrativo específico aprobado, rollback probado y defaults por cada creador ensayados; históricos y correcciones anteriores intactos.
- Casos positivos y negativos de QA aprobados sin elevar runtime o debilitar auditoría/RBAC para superar fallos.
- SS-07 sólo puede reevaluarse con evidencia efectiva posterior; esta entrega no autoriza ejecución ni acredita despliegue institucional seguro.

**Detenerse tras la revisión de estos artefactos. No ejecutar el verificador ni el hardening sin nueva autorización.**
