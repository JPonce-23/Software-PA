# SS-07 etapa 1: auditoría estática y verificación futura de privilegios

Fecha: 2026-10-28. Repositorio Software-PA, rama `dev`, HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff` más las correcciones locales anteriores. **No se abrió ninguna conexión PostgreSQL, incluida QA.**

## Dictamen

**Los privilegios efectivos de runtime y migrador continúan sin acreditar. SS-07 permanece abierto, como riesgo de configuración.** El repositorio declara identidades separadas y restricciones útiles, pero el baseline otorga SELECT/INSERT/UPDATE por esquema, EXECUTE sobre todas las funciones y defaults igualmente amplios. Los permisos reales pueden además proceder de PUBLIC, roles heredados, propiedad o cambios administrativos no versionados. No se afirma que runtime sea superusuario, propietario o pueda desactivar triggers en el servidor.

Se entregan una matriz de necesidades candidatas, inventario trazable de30 migraciones,23 consultas de metadatos y un preparador **offline** con controles opt-in. Resultado:21 pruebas descubiertas,20 aprobadas y1 omitida por ausencia de parser PostgreSQL. Sintaxis y semántica nativas siguen pendientes. No se introdujo ni ejecutó GRANT/REVOKE correctivo, RLS, migración o cambio de política documental SS-05.

## Alcance y preservación

Se revisaron como texto `backend/app/database.py`, los dos scripts de init, `backend/scripts/run_migrations.sh`, las30 migraciones SQL canónicas001–030, modelos, consultas de routers/services, triggers/funciones/vistas/secuencias, scripts administrativos/importación, Compose y auditoría SS-07/matriz. Se detectó `backend/db/migrations/001_init_schema.sql` como directorio, no como migración ejecutable; el inventario no lo trata como un fichero SQL.

Snapshot inicial:722 archivos preexistentes, excluidos `.env` y variantes. Se comprueba su igualdad por SHA-256 al terminar. SS-01/02/03/04/06/10/11/12 y el diseño SS-05 permanecen intactos. No se importó `app.database`: ese módulo carga dotenv y prepara el engine. No se leyó `.env`, instalaron dependencias, ejecutaron psql/Docker/bootstrap/migraciones o hicieron cambios Git.

El inventario es **léxico y de referencias**, no un catálogo efectivo ni un simulador exhaustivo de DDL/ACL. Registra cada sitio CREATE/reemplazo y referencias; las migraciones con SQL dinámico, recreación de vistas o identidad implícita requieren comparación con QA. No se recopilan filas, definiciones de funciones desplegadas, contraseñas, hashes de autenticación ni cadenas de conexión.

## Identidades y responsabilidades

| Identidad | Evidencia del repositorio | Capacidad esperada / desconocido efectivo |
|---|---|---|
| Login runtime FastAPI | `database.py:8–55`: DB_RUNTIME_USER/PASSWORD y URL SQLAlchemy; hide_parameters de SS-10 | CONNECT + USAGE esquema + DML/EXECUTE mínimos de matriz; sin DDL/roles/extensiones/ownership. Nombre real, membresías, ACL y atributos efectivos no leídos |
| `software_pa_app` | `001_bootstrap_roles.sh`: NOLOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION, NOBYPASSRLS; se concede al login runtime | Rol contractual colectivo PostgreSQL, distinto de los cuatro roles funcionales. No se prueba ownership, otras membresías, INHERIT efectivo ni permisos PUBLIC |
| Propietario/administrador | Compose entrega POSTGRES_ADMIN_USER/PASSWORD al contenedor db como POSTGRES_USER/PASSWORD | Administra bootstrap, ownership y extensiones según instalación; la imagen y un PGDATA existente no acreditan atributos/propietarios reales |
| Migrador | `002_apply_migrations.sh` invoca runner; runner usa DATABASE_URL si existe, o POSTGRES_USER/POSTGRES_ADMIN_USER y POSTGRES_DB/DB_NAME | DDL/funciones/índices/triggers y S/I sobre schema_migrations; baseline necesita PostGIS y018 btree_gist. No hay una identidad migrador distinta obligatoria en el código: suele derivar del administrador, pero el destino real se desconoce |
| Bootstrap primer admin funcional | `create_admin.py`: runtime por defecto, owner sólo con ADMIN_DATABASE_MODE=owner; primer usuario desactiva temporalmente trg_audit_usuario | Esa tarea inicial necesita identidad administrativa controlada, no elevar runtime para que funcione. Un admin de la aplicación no es un rol PostgreSQL SUPERUSER |
| Provisionamiento runtime de BD existente | `scripts/utils/set_runtime_credentials.sh` | Script administrativo de escritura, NO ejecutado. Rechaza ownership de BD/esquemas/relaciones del login y limpia membresías/direct grants de esquema/tablas/secuencias; no demuestra su ejecución ni cubre por sí solo todas las funciones, derechos de BD, PUBLIC o propiedad heredada |
| Importador RAN/sincronización | `import_catalogo_nucleos_ran.py:330–347,574`; `sync_catalogo_ran.py` | DATABASE_URL puede seleccionar otra identidad; por defecto DB_RUNTIME_*. Usa CREATE TEMP TABLE, carga temporal y DML de catálogo. TEMP no puede retirarse sin separar/revalidar este flujo |
| unlock_admin, seeds y auxiliares | Scripts que importan SessionLocal y modelos; herramientas de lineage pueden usar identidad administrativa explícita | DML/locks específicos; seeds y reparación de lineage son operaciones operativas, no necesidades del servicio HTTP ordinario. No se ejecutaron |
| pgAdmin | Compose define credenciales de la interfaz pgAdmin | No son la identidad PostgreSQL de una conexión guardada; no se inspeccionó ninguna configuración efectiva |
| GDAL/OGR | SS-02 restringe entorno de los subprocesos y procesa staging de archivos | No justificar credenciales o privilegios PostgreSQL adicionales para GDAL. PostGIS lo invoca la API por runtime, no un login GDAL acreditado |

Cambiar INHERIT de un login existente no está forzado explícitamente en el bootstrap. Un rol preexistente puede conservar estado adicional. La mera presencia de CREATE ROLE o NOSUPERUSER en scripts no acredita el destino ni excluye derechos por membresía/propiedad.

## Necesidades de alto nivel

| Capacidad runtime | ¿Necesaria por la API inspeccionada? | ¿Se posee efectivamente? |
|---|---|---|
| Crear/alterar/borrar esquemas/tablas | No para HTTP ordinario. TEMP sí en importador auxiliar con credenciales runtime | Desconocido; Q04/Q05/Q06/Q07 |
| Alterar funciones/triggers/controles | No; exclusivamente administración/migración | Desconocido: flags y ownership, no sólo grants; Q01/Q03/Q06/Q11/Q14 |
| Ejecutar migraciones | No; sólo lectura de schema_migrations para health | Desconocido; Q07 y roles/ownership |
| Administrar roles/privilegios | No | Desconocido; Q01/Q02/Q03/Q12/Q13/Q22 |
| Crear/actualizar extensiones | No; tarea administrativa controlada | Desconocido; CREATE en BD/ownership/atributos y Q15 |
| Acceder a otros objetos/BD | No justificado por la API, salvo pg_catalog/tipos/funciones de plataforma y dependencias necesarias | Q04 cubre CONNECT/CREATE/TEMP por BD; sólo objetos de la BD conectada se inventarían. No abrir otras BD |
| Leer schema_migrations | Sí: `/health` hace SELECT max(version::integer) | Declarado S en baseline; efectivo pendiente |
| Modificar schema_migrations | No en runtime; runner migrador necesita INSERT y comprobar checksum | Revocación declarada001; efectivo pendiente por otras rutas de privilegio |

## Evidencias relevantes de migraciones

| Migración/sitio | Control declarado o riesgo a verificar |
|---|---|
| 001:8092–8105 | USAGE public; S/I/U en todas las relaciones; USAGE/SELECT de secuencias; EXECUTE en todas las funciones. Revoca D/TRUNCATE/REFERENCES/TRIGGER y escrituras de schema_migrations al rol contractual |
| 001 defaults | Defaults por rol creador que ejecuta ALTER DEFAULT PRIVILEGES, no automáticamente por cualquier migrador futuro. Pueden conceder UPDATE a una nueva tabla append-only hasta revocación explícita |
| 009 | Revoca I/U/D/TRUNCATE en bitacora al contrato y mantiene S; exige fn_audit_log SECURITY DEFINER con capacidad de INSERT del propietario |
| 010/011/020 | Reemplazos de fn_audit_log; filtran hashes sensibles y validan actor/evento/heartbeat. SECURITY DEFINER con SET search_path public y referencias sin schema en el cuerpo |
| 025 | Revoca UPDATE de importacion_feature_decision; permisos necesarios de candidato/geometrías y secuencias |
| 026 | Revoca U/D/TRUNCATE de decisiones/revisiones/resultados append-only y D/TRUNCATE de ciclo; preserva INSERT/SELECT e historia |
| 028 | Catálogo tipo documental tiene SELECT explícito; defaults del creador podrían aportar UPDATE. El servicio actual usa FOR SHARE al seleccionarlo; quitar UPDATE puede romper clasificación/cargas |
| 030 | Ajusta RBAC funcional GIS por contexto de actor; no altera GRANT SQL. Sustituye lock de revisión append-only por advisory lock para no necesitar UPDATE de esa tabla |
| 007 | Guarda/recrea vistas y ACL/owners con tablas temporales y SQL dinámico administrativo; no extrapolar permisos del migrador a runtime |

Las revocaciones al contrato no eliminan permisos de PUBLIC, otro rol o propietario. Un trigger inmutable/auditable no prueba que un propietario o superusuario no pueda alterarlo o deshabilitarlo. Los privilegios de DDL dependen de propiedad y membresías; `has_table_privilege` no responde por sí solo si un actor puede modificar una función o desactivar un trigger.

## Riesgos y prioridades de inspección

No son nuevos exploits confirmados ni se asigna CVSS sin evidencia efectiva. Todos siguen dentro de SS-07.

| ID | Prioridad | Evidencia estática | Verificación/impacto pendiente |
|---|---|---|---|
| P01 | Alta | Separación declarada, sin inspección de login/owners/membresías aplicados | Si runtime es owner, hereda owner, SUPERUSER/CREATEROLE/CREATEDB/BYPASSRLS o roles de archivos/programas, puede exceder el contrato. No se afirma que ocurra |
| P02 | Alta | fn_audit_log SECURITY DEFINER SET search_path public; nombres no calificados | Evaluar CREATE public, TEMP y owner de función/objetos. Posible resolución a objetos no confiables; no se ejecutó una explotación o prueba de shadowing |
| P03 | Media | S/I/U/EXECUTE por esquema y defaults; UPDATE de documento_version/evento_acceso queda principalmente ante triggers, salvo grants de otras migraciones | Ampliación futura de superficie o mutación si controles/owners cambian; comparar por objeto y operación, no revocar en masa |
| P04 | Media | Defaults dependientes del creador y revocaciones selectivas 009/025/026 | Un despliegue por otra identidad puede omitir permisos necesarios o conservar otros; verificar creators, defaults globales y por esquema |
| P05 | Media | Actor app.current_user_id se establece desde runtime por set_config/SET LOCAL | El login compartido es frontera de confianza; SQL concedido a runtime puede elegir actor. Atributo de sesión no autentica al humano por sí solo; no se introduce RLS ni se cambia RBAC |
| P06 | Media | TEMP usado por importador; helpers invoker y locks sobre catálogos/dominio | Una revocación apresurada provoca regresiones o no elimina shadowing si otra vía concede TEMP/CREATE. Separar auxiliares y preservar dependencias verificadas |
| P07 | Media | Provisionamiento de BD existente no comprueba ownership de pg_proc y no limpia explícitamente derechos de BD/funciones/PUBLIC | Propiedad de funciones/otro rol puede permitir alterar validación/auditoría pese a limpieza de grants directos. Procedimiento aplicado desconocido |

SQL dinámico: los validadores de objetivos controlados eligen tablas/PK por listas y usan `%I`/parámetros; scripts de migración construyen DDL/ACL desde catálogos. Esto no equivale a SQL injection confirmada. Revisar el namespace/owner y las firmas de cada rutina desplegada antes de estrechar permisos. EXECUTE sobre una función RETURNS trigger no significa que sea invocable útilmente como una función ordinaria; tampoco sustituye el análisis de sus privilegios al dispararse.

No se infiere PUBLIC CREATE seguro por usar PostgreSQL15: bases actualizadas o ACL modificadas pueden diferir. Tampoco una ACL NULL significa “sin permisos”; hay defaults implícitos, propiedad y PUBLIC. [Privilegios y propiedad PostgreSQL15](https://www.postgresql.org/docs/15/ddl-priv.html), [schemas](https://www.postgresql.org/docs/15/ddl-schemas.html).

## Artefactos y cobertura

- [Matriz de necesidades](SS-07-MATRIZ-PRIVILEGIOS-2026-10-28.md).
- [Plan de hardening y QA](SS-07-PLAN-HARDENING-POSTGRESQL.md).
- [Inventario estructurado](ss07/inventario-estatico.json):30 ficheros con SHA;76 modelos;67 nombres de tabla declarados, incluidos2 temporales de migración;21 nombres de vista;78 nombres de función;59 nombres de secuencia explícitos o referidos en GRANT; dos columnas identity adicionales sin nombre de secuencia explícito en fuente. Se añaden155 declaraciones literales de triggers,2 extensiones declaradas (postgis/btree_gist) y15 sitios EXECUTE format, sin expandir las construcciones dinámicas. No hay CREATE MATERIALIZED VIEW detectado.
- [Consultas](ss07/consultas-privilegios.sql.in):23 SELECT/WITH de pg_catalog, incluyendo roles, ACL/ownership, columnas, secuencias, rutinas, defaults, triggers, extensiones, vistas, RLS y parámetros PG15. No llaman funciones de aplicación o PostGIS ni consultan tablas de negocio.
- [Preparador offline](ss07/preparar_verificador.py) y [ejemplo deshabilitado](ss07/config-ejemplo.json): no contienen connector, subprocess, shell, dotenv ni ejecución SQL.
- [Pruebas nuevas](../../tests/security/test_postgresql_privilege_audit.py): aislamiento, opt-in, datos de configuración, no impresión de sentinelas, consultas permitidas, cobertura y SHA de migraciones.

El inventario no enumera todas las rutinas/objetos instalados por PostGIS y btree_gist a partir de su nombre: los descubre Q15/Q11 en QA. Tampoco trata las46 coincidencias de nombres en expresiones Python/SQL como46 funciones almacenadas distintas: incluye construcciones como coalesce/distinct. No crea GRANT automáticamente desde esos datos.

## Verificador: controles y límites

La preparación requiere configuración sin credenciales, identificador de autorización externa QA y confirmación explícita de clon desechable. El ejemplo tiene `clon_verificado=false` y autorización pendiente, por lo que se rechaza. El preparador sólo crea un archivo nuevo0600, sin sobrescribir existentes o seguir un symlink de salida. Los errores no imprimen paths, valores de configuración, argumentos desconocidos, DSN o tracebacks.

El SQL generado exige además opt-in de psql `SS07_QA_AUTORIZADA`, y antes de inventariar compara BD, IP/puerto del servidor, cluster_name, PostgreSQL15, session_user e inspector sin SET ROLE. Esas coincidencias son comprobaciones de consistencia, **no acreditan por sí mismas que sea un clon ni sustituyen la aprobación externa**. No hay conexión automática ni reutilización de DB_RUNTIME/DATABASE_URL, .env o credenciales de la aplicación.

Se ejecutaría en transacción READ ONLY, REPEATABLE READ, search_path pg_catalog/pg_temp, límites de15s por sentencia y1s de lock, finalizando ROLLBACK. Son presupuestos del verificador, no del runtime ni garantía de deadline total (23 consultas pueden acumular tiempo). No se usan locks de negocio, CREATE TEMP, nextval, setval, SECURITY DEFINER de aplicación ni llamadas a extensiones. Los límites pueden omitir resultados en un catálogo grande: registrar el caso como pendiente, no como ausencia de permisos.

Si el inspector no puede leer un catálogo o usar una función de inspección, ON_ERROR_STOP detiene la transacción; esa consulta y las posteriores quedan **no observadas**. No ampliar automáticamente al inspector. Repetir bajo identidad autorizada o recortar explícitamente la cobertura en una revisión. Un rol objetivo inexistente aparece en Q00; no interpretar su ausencia en Q07 como denegación satisfactoria. Una pareja runtime=migrador se muestra como separación falsa, no se oculta ni se cambia de rol.

La salida de metadatos puede contener nombres de cuentas/esquemas institucionales: conservarla protegida en QA, sin copiarla íntegra a informes públicos o logs. Se excluyen pg_authid/pg_shadow, query de pg_stat_activity, cuerpos de rutinas/vistas, opciones de conexiones FDW y configuración amplia que pueda contener secretos. Sólo search_path de proconfig/configuración rol-BD se muestra; no otros valores.

Una salida de rechazo `SS07_RECHAZADO_*` o un error no es un informe completo. Las guardas de psql usan `\quit`; no suponer que el código de salida de psql por sí solo acredita éxito: exigir marcador de inspección completa, Q00 correcto y las23 secciones revisadas. La plantilla `.sql.in` no es un script para ejecutar directamente y contiene marcadores pendientes.

## Pruebas ejecutadas y pendientes

Comando local, inspeccionado previamente y sin conftest de backend:

```text
python3 -B -m unittest discover -s tests/security -p 'test_postgresql_privilege_audit.py' -q
Ran 21 tests
OK (skipped=1)
```

20 aprobadas;1 omitida: parser PostgreSQL pglast no instalado. No hay pglast/sqlparse/sqlglot/SQLAlchemy/psycopg2 disponibles en este Python; no se instalaron. Se comprueban tokens permitidos, balance de comentarios/literales/paréntesis, fin de sentencias y estructura de la plantilla fija; **no es validación de gramática PostgreSQL ni un sandbox para SQL arbitrario**. Los tokens de privilegios INSERT/UPDATE/CREATE aparecen como literales de comprobación, no como instrucciones de cambio.

No se ejecutaron psql, SQL, EXPLAIN/PREPARE contra servidor, bootstrap, suites backend, collect-only o QA. No se reejecutó la suite completa de remediaciones anteriores porque sólo se agregan artefactos de inspección; se verifica su preservación por hash. Los puntos de aceptación requieren catálogo y operaciones sintéticas reales en QA autorizada en una fase posterior, especialmente triggers, PostGIS, locks, secuencias y separación de owner.

**Etapa1 terminada con privilegios efectivos pendientes. Detenerse para revisión antes de cualquier conexión o cambio de permisos.**
