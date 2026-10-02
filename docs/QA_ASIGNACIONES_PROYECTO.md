# QA: ciclo administrativo de asignaciones a proyectos

## Correcciones de auditoría — validación actual, 2026-10-02

Se conserva la implementación anterior y se trabaja exclusivamente en
`task/backend-desasignacion-proyectos`, con HEAD
`750ec71a331a0ce8ac60e9b7268482b2b174c56f`. La referencia local de
`origin/feature/backend-logica` coincide: divergencia `0 0`. Origin:
`git@github.com:JPonce-23/Software-PA.git`. El árbol ya tenía cambios locales
al comenzar; se inspeccionaron también los archivos sin seguimiento.
No hubo commits, push, cambios de rama, merge, rebase, reset ni cherry-pick.

Esta sección es la evidencia de las correcciones. El informe anterior se
conserva abajo como historial; sus resultados y decisiones corresponden a
aquella implementación y no sustituyen las pruebas de esta ejecución.

### Hallazgos, causas y correcciones

| Hallazgo | Causa raíz y cambio | Evidencia y ubicación |
|---|---|---|
| H1 | POST consultaba `activo` sin sincronizar con la baja global. Ahora adquiere `FOR NO KEY UPDATE`, refresca el identity map y valida el estado después de esperar; mantiene el bloqueo hasta commit. | `services/domain.py:1444`; pruebas `test_assignment_concurrency_regressions.py:62` y `:232`: POST primero termina con relación inactiva; baja primero devuelve 404 sin fila nueva; reactivar no recupera permisos. |
| H2 | GET/PATCH de Persona verificaban sólo rol. Se incorpora una autorización común basada en siete caminos reales de relaciones y se validan las referencias antes de vincularlas. | `services/access.py:15` y `:75`, `services/domain.py:413`, `:447`, `:451`, `:1495`; `routers/domain.py:481`. Pruebas `test_person_project_access.py`: revocación, datos persistidos, roles, personas compartidas, creador, otras rutas, PATCH y creación masiva. |
| M1 | `FOR UPDATE` sobre el usuario objetivo impedía los `FOR KEY SHARE` de los FK al actor de auditoría; dos admins cruzados formaban un ciclo. Se usa `FOR NO KEY UPDATE` sin cambiar identificadores. | `services/domain.py:1478`; `routers/users.py:97`, `:157`, `:186`. Dos sesiones y conexiones distintas sincronizadas antes del UPDATE: ambos DELETE 200, una baja y un UPDATE auditado por relación con el actor opuesto. |
| M2 | El observador aceptaba cualquier sesión bloqueada. Ahora captura el PID real de cada trabajador y sigue `pg_blocking_pids` hasta el bloqueador esperado. | `tests/concurrency.py:59` y `:78`; prueba negativa `test_assignment_concurrency_regressions.py:209`. Un bloqueo ajeno no satisface la observación. |
| B1 | La cabecera y el ejemplo de health documentaban esquema 015. Se actualizan ambos a 020 y se compara el OpenAPI completo. | `docs/API.md`; `/health` real devuelve `{"status":"ok","schema":20}`. |

Las ubicaciones de servicios/routers/pruebas son relativas a `backend/app/`
o `backend/tests/`, según corresponda. No se modifica la responsabilidad de
seguimiento ni responsables operativos; la figura funcional sigue en REVIEW.

### Política de Persona confirmada por el usuario

- Admin conserva lectura, edición y vinculación globales.
- Lectura no administrativa: al menos un proyecto autorizado vinculado realmente
  mediante ORV, titularidad de parcela, titularidad de unidad directa/indirecta,
  convenio, FIFONAFE o pago por indemnización.
- Los vínculos y sus padres deben estar activos. La vigencia de negocio de un
  integrante ORV no se confunde con el flag `activo`.
- Editar los campos globales exige rol operador y captura en todos los proyectos
  relacionados. Un proyecto inactivo con referencias activas permanece en ese
  conjunto; no se considera captura autorizada ni permite fallback al creador.
- Sin referencias activas: sólo admin o el creador operador con alguna asignación
  vigente puede leer, editar y realizar la primera vinculación. No se crea una
  relación implícita por utilizar el POST bajo un proyecto.
- Vincular exige lectura legítima de Persona y captura en el recurso destino.
  No equivale a editar los campos globales; no permite importar un id fuera del
  alcance para obtener acceso indirecto.
- Las referencias a Persona en altas de convenio (incluidas las masivas), ORV,
  parcela, unidad, FIFONAFE y pago, y en PATCH que cambian referencias, reutilizan
  la validación. `update_entity` tampoco permite eludir el control de Persona.

Se usa el mismo advisory lock de relaciones de Persona de la migración 018
antes de comprobar el alcance de una edición. Las referencias de un lote se
bloquean en orden de id. Una prueba mantiene una nueva vinculación pendiente en
otro proyecto; PATCH espera su PID y, tras commit, responde 403 sin modificar
campos ni auditoría de Persona. Las decisiones funcionales solicitadas quedaron
confirmadas; H2 no queda pendiente de esa decisión.

### Transacciones, proyectos e historial

POST/DELETE de asignaciones adquieren `FOR SHARE` en proyecto, seguido de
`FOR NO KEY UPDATE` en usuario. DELETE bloquea después la relación activa.
La baja global de cuenta bloquea primero ese mismo usuario. Los FK al actor
pueden usar `FOR KEY SHARE` sin el deadlock reproducido. Se comprueba el SQL
emitido, no sólo el nombre del argumento de SQLAlchemy.

Dos asignaciones a usuarios distintos pueden avanzar simultáneamente en el
mismo proyecto. Para baja de proyecto: si POST obtiene primero el bloqueo,
confirma 201 y luego el proyecto queda inactivo; si la baja confirma primero,
POST responde 403 y no crea la relación. Se conserva la política existente:
la baja de proyecto no hace cascada de asignaciones; el proyecto inactivo
impide acceso. No se introduce reactivación de proyecto ni nueva autorización.

Las pruebas comparan snapshots persistidos, fechas, actor y bitácora.
Desasignar no modifica cuenta, rol, sesiones u otras parejas; repetir devuelve
404 sin cambios. Reasignar crea otro id, conserva histórico y mantiene una
única relación activa. Se prueban también ambas ordenaciones entre baja
individual y global. Un error PostgreSQL real (`SELECT 1 / 0`) después del
UPDATE y su trigger verifica rollback de relación y bitácora juntas.

### QA y comandos ejecutados

Base en ambos entornos: `software_pa_test`, PostgreSQL **15.4**, PostGIS 3.3.4,
veinte migraciones aplicadas hasta **020**. El backend usa `qa_runtime`, sin
superusuario, creación de roles ni creación de bases. No se escribe en bases
existentes o compartidas. El backend se monta sólo lectura y los uploads/cache
de pytest quedan en directorios temporales.

El primer entorno nuevo fue `software-pa-assignment-fixes-db-20261002`, red
`software-pa-assignment-fixes-20261002`. Se utilizó para desarrollo focalizado
y experimentos de regresión sólo en memoria del runner. La validación final usa
otra copia: `software-pa-assignment-fixes-full-db-20261002`, red
`software-pa-assignment-fixes-full-20261002`, sin puertos ni volúmenes compartidos.
Ambas copias proceden de lectura de la QA original 020, no de producción:

```sh
docker exec software-pa-assignments-qa-db-20261002 pg_dump -U qa_owner -d software_pa_test --no-owner | docker exec -i software-pa-assignment-fixes-full-db-20261002 psql -U qa_owner -d software_pa_test -X -q -v ON_ERROR_STOP=1
```

Las credenciales sintéticas permanecen en
`/tmp/software-pa-assignments-qa/qa.env`, fuera del repositorio. La fixture
comprueba `APP_ENV=test`, `DB_NAME=software_pa_test` y
`TEST_ALLOW_DATABASE=software_pa_test`. La limpieza de proyectos consulta su
estado persistido para omitir los que la prueba ya desactivó; no acepta errores
403 arbitrarios como éxito de limpieza.

Focalizadas finales, comando exacto:

```sh
docker run --rm --name software-pa-assignment-fixes-focused-complete-20261002 --network software-pa-assignment-fixes-full-20261002 --env-file /tmp/software-pa-assignments-qa/qa.env --mount type=bind,src=/home/alfredo/proyectos/Software-PA/backend,dst=/app,readonly -e PYTHONDONTWRITEBYTECODE=1 software-pa-backend python -m pytest tests/test_person_project_access.py tests/test_project_user_assignments.py tests/test_assignment_concurrency_regressions.py tests/test_user_administration.py tests/test_auth_rbac.py tests/test_orv_persona_ciclo_vida.py tests/test_fifonafe_intervinientes.py tests/test_audit_api.py -o cache_dir=/tmp/pytest-cache -q
```

Resultado: **101 aprobadas, 0 fallidas, 0 omitidas**, una advertencia de
deprecación Starlette/httpx; 67.98 s. No se reutilizó el resultado anterior de 370.

Suite general, comando exacto:

```sh
docker run --name software-pa-assignment-fixes-full-suite-20261002 --network software-pa-assignment-fixes-full-20261002 --env-file /tmp/software-pa-assignments-qa/qa.env --mount type=bind,src=/home/alfredo/proyectos/Software-PA/backend,dst=/app,readonly -e PYTHONDONTWRITEBYTECODE=1 software-pa-backend python -m pytest -o cache_dir=/tmp/pytest-cache -q
```

Resultado general: **407 aprobadas, 0 fallidas, 0 omitidas**, una advertencia
de deprecación Starlette/httpx; **207.91 s**. Ejecutada después de las focalizadas,
con todos los cambios finales de backend y pruebas.

Intentos previos de esta ejecución: 29 aprobadas y 1 error de teardown por volver
a desactivar un proyecto; corregido en `conftest.py`. Otro intento dio 84 aprobadas
y 5 fallos de nuevas fixtures por nombre de catálogo/rutas inexistentes; corregidos
contra el contrato real. Las ejecuciones posteriores dieron 90, 96 y 98 aprobadas
antes de añadir las tres últimas regresiones.

### Comprobación de que las pruebas detectan las regresiones

En runners temporales se restablecieron los defectos sólo en memoria mediante
`/tmp/software-pa-assignment-fixes-mutations.py`; no se cambiaron los archivos
del checkout. Los seis casos seleccionados fallaron al introducir sus defectos:

| Defecto restablecido | Resultado esperado y observado |
|---|---|
| H1: retirar NO KEY UPDATE sólo al trabajador POST | 2 fallos: ninguno de los PID esperó al bloqueador esperado. |
| M1: sustituir NO KEY UPDATE por UPDATE | 1 fallo: respuestas 200/409. PostgreSQL registró `deadlock detected`, ciclo entre PID 242/243 y comprobación FK `FOR KEY SHARE` en `usuario`. |
| M2: volver al conteo global | 1 fallo: el observador aceptó un PID ajeno que no esperaba. |
| H2: restaurar GET/PATCH sólo por rol | 2 fallos: GET tras revocación y PATCH compartido devolvieron 200 en vez de 403. |

Son fallos intencionales de los experimentos, separados de las pruebas de la
implementación final. Su base no se usa como fuente de la validación general.

### Esquema, OpenAPI y alcance final

Los archivos 001–020 se compararon byte a byte con `750ec71`; los veinte
checksums de `schema_migrations` coinciden con los archivos. El SHA256 de 020 es
`cfa4dadb2e8b5bb9b8cddddf617c34132380ad49a660de9037de43850263f4c8`.
Existen `chk_usuario_proyecto_baja`, el índice único parcial
`uq_usuario_proyecto_activo ... WHERE activo` y
`trg_audit_usuario_proyecto AFTER INSERT OR UPDATE ... fn_audit_log`.
Se conserva el heartbeat y no existe necesidad estructural de migración 021.

`docs/openapi.json` es idéntico a `app.openapi()` real. Se reconstruyó una app
FastAPI con el router original de `750ec71`: todas sus operaciones y componentes
coinciden; sólo se añade DELETE de asignaciones. GET/POST mantienen su esquema.
Los cambios preexistentes del documento son sincronización, no funcionalidades
de esta tarea: rutas de Persona, finalizar/reactivar ORV, contrato de integrantes
ORV y enums de `ConvenioCreate/Response/Update`. La restricción de autorización
de Persona sí es el cambio semántico de seguridad H2, documentado expresamente;
no cambia sus cuerpos ni response models.

Archivos runtime: `routers/domain.py`, `routers/users.py`, `services/domain.py`
y `services/access.py`. Pruebas: `conftest.py`, `concurrency.py`,
`test_project_user_assignments.py`, `test_assignment_concurrency_regressions.py`
y `test_person_project_access.py`. Documentación: `docs/API.md`,
`docs/openapi.json` y este informe. Los archivos nuevos sin seguimiento forman
parte de la entrega; `git diff --stat` por sí solo no los incluye.

`git status -sb` final:

```text
## task/backend-desasignacion-proyectos
 M backend/app/routers/domain.py
 M backend/app/routers/users.py
 M backend/app/services/access.py
 M backend/app/services/domain.py
 M backend/tests/conftest.py
 M docs/API.md
 M docs/openapi.json
?? backend/tests/concurrency.py
?? backend/tests/test_assignment_concurrency_regressions.py
?? backend/tests/test_person_project_access.py
?? backend/tests/test_project_user_assignments.py
?? docs/QA_ASIGNACIONES_PROYECTO.md
```

`git diff --stat` final (archivos con seguimiento):

```text
 backend/app/routers/domain.py  |  23 +-
 backend/app/routers/users.py   |   6 +-
 backend/app/services/access.py | 105 +++++-
 backend/app/services/domain.py | 108 ++++--
 backend/tests/conftest.py      |   6 +
 docs/API.md                    |  74 +++-
 docs/openapi.json              | 793 ++++++++++++++++++++++++++++++++++-------
 7 files changed, 959 insertions(+), 156 deletions(-)
```

Adicionalmente, sin seguimiento: `concurrency.py` (+85 líneas),
`test_assignment_concurrency_regressions.py` (+352),
`test_person_project_access.py` (+375),
`test_project_user_assignments.py` (+371) y este informe (+433). Son doce archivos
en total. `git diff --check` final no informa errores. No aparece ningún archivo
frontend ni ninguna migración; se conserva el HEAD y el arreglo heartbeat.

Límites: las pruebas cubren las carreras descritas y las nuevas peticiones;
no son una prueba de ausencia de todo deadlock posible bajo cualquier carga.
No se cancela retroactivamente una operación que ya pasó su autorización.
La excepción del creador y edición compartida quedan documentadas y aprobadas.
El historial inactivo no concede alcance. Advertencia residual de dependencia:
Starlette anuncia deprecación del TestClient basado en httpx; queda fuera de esta
corrección. No se modifican frontend, modelos/esquemas, migraciones, checksums,
`docs/MIGRACIONES.md` ni responsables funcionales.

Mensaje de commit propuesto (no ejecutado):
`fix(backend): serializar asignaciones y restringir Persona por proyecto`.

## Informe anterior — historial de la implementación original

Fecha: 2026-10-02. Rama local: `task/backend-desasignacion-proyectos`.
Base: `750ec71a331a0ce8ac60e9b7268482b2b174c56f`.

## Git y alcance

Antes de modificar código, el árbol estaba limpio en `feature/backend-logica`.
`git fetch origin` terminó correctamente; HEAD y
`origin/feature/backend-logica` coincidían en `750ec71`, con divergencia `0 0`.
La rama de tarea se creó desde esa referencia. Se conserva el arreglo heartbeat;
no se hicieron commits, push, merge, rebase, reset ni cherry-pick.

Sólo cambian backend, pruebas backend y documentación técnica. No se modifican
frontend, migraciones 001–020, checksums, `docs/MIGRACIONES.md`, autorización,
responsables operativos ni flujos agrarios. No se necesita migración 021.

## Diagnóstico confirmado

| Evidencia | Ubicación |
|---|---|
| GET administrativo lista sólo relaciones activas | `backend/app/routers/domain.py:1832` |
| POST administrativo mantiene entrada `id_usuario` y respuesta 201 | `backend/app/routers/domain.py:1848` |
| POST valida usuario activo y construye una fila nueva; conflicto 409 | `backend/app/services/domain.py:1417` |
| `UsuarioProyecto` hereda `AuditableMixin` | `backend/app/models.py:1091` |
| Campos de actualización y baja lógica del mixin | `backend/app/models.py:40` |
| Columnas y check obligatorio de baja | `backend/db/migrations/001_baseline_v1.sql:3748` |
| Índice único parcial por usuario/proyecto WHERE activo | `backend/db/migrations/001_baseline_v1.sql:5206` |
| Trigger de INSERT/UPDATE de la relación | `backend/db/migrations/001_baseline_v1.sql:5815` |
| Autorización depende de asignaciones y proyectos activos | `backend/app/services/access.py:19` y `:46` |
| Baja de cuenta también desactiva asignaciones y sesiones | `backend/app/routers/users.py:177` |
| Contexto de actor y helper de baja; éste no actualiza timestamps de edición | `backend/app/services/common.py:12` y `:46` |
| Motivo recortado, mínimo 3 y máximo 500; respuesta `detail` | `backend/app/schemas.py:41` y `:78` |
| CSRF de operaciones con cookie de sesión | `backend/app/main.py:43` |
| UPDATE de asignaciones conserva auditoría; heartbeat de sesión se omite | `backend/db/migrations/020_auditoria_heartbeat_sesion.sql:75` |

## Implementación y contrato

El router incorpora únicamente
`DELETE /api/proyectos/{id_proyecto}/usuarios/{id_usuario}`, con
`RoleChecker(["admin"])`, `BajaRequest` obligatorio y `AuthOperationResponse`.

```json
{"motivo":"Reasignación administrativa de personal"}
```

Respuesta HTTP 200:

```json
{"detail":"Asignación desactivada"}
```

El servicio valida el proyecto con `require_project_access`. Un proyecto
inexistente/inactivo devuelve 403 según la convención vigente. Bloquea la cuenta
con `with_for_update()` sin filtrar `activo`, para serializar con administración
de cuentas; un usuario inexistente devuelve 404. Después bloquea exclusivamente
la relación activa de la pareja. Su ausencia devuelve 404 sin tocar histórico.

Reutiliza `set_audit_context` y `mark_inactive`; establece además
`actualizado_en=fecha_baja` y `actualizado_por=actor`. `commit_or_conflict` realiza
un único commit y rollback ante conflicto de integridad (409). La auditoría se
produce mediante el trigger existente en esa misma transacción.

El POST queda intacto: una reasignación crea otra fila activa; el índice parcial
garantiza unicidad sin impedir conservar filas inactivas. No se modifican cuenta,
rol ni sesiones globales. Los administradores conservan acceso global por rol.
La asignación es autorización por proyecto; la figura funcional de responsable
del seguimiento continúa en REVIEW.

## Archivos

- `backend/app/routers/domain.py`: nuevo endpoint administrativo.
- `backend/app/services/domain.py`: validación, bloqueo y baja transaccional.
- `backend/tests/test_project_user_assignments.py`: 16 casos de integración, con sesiones reales.
- `docs/API.md`: contrato, errores, autorización, baja y reasignación con historial.
- `docs/openapi.json`: exportación completa desde `app.openapi()` de FastAPI.
- Este informe: diagnóstico, decisiones, entorno y resultados reproducibles.

El OpenAPI versionado estaba desactualizado respecto del código de HEAD: faltaban
rutas de Persona, finalización/reactivación ORV y sus esquemas. La regeneración
completa corrige ese desfase preexistente. Se exportó también el OpenAPI usando
el router original de HEAD y se comparó estructuralmente: todas las operaciones
anteriores y componentes son idénticos; la única nueva ruta runtime es DELETE de
asignación. GET/POST de asignaciones permanecen idénticos.

## QA aislada y comandos

Contenedor PostgreSQL: `software-pa-assignments-qa-db-20261002`.
Red independiente: `software-pa-assignments-qa-20261002`.
Base: `software_pa_test`; PostgreSQL 15.4 / PostGIS 3.3.4; esquema **020**.
Sin puertos publicados ni volúmenes compartidos con bases existentes. El checkout
se monta sólo lectura; credenciales sintéticas están fuera del repositorio.
El backend utiliza `qa_runtime`, sin ownership ni privilegios administrativos.
`APP_ENV=test`, `DB_NAME=software_pa_test` y
`TEST_ALLOW_DATABASE=software_pa_test` satisfacen las protecciones de pytest.

Se aplicaron 001–017 con el runner oficial, se prepararon cinco integrantes ORV
históricos sintéticos y se aplicaron 018–020 con el mismo runner. Se cargó la
fixture territorial oficial y cien núcleos RAN sintéticos completos. Un único
administrador administrado por pytest permite comprobar la protección del último
admin. El runner verificó los checksums existentes; 020 conserva
`cfa4dadb2e8b5bb9b8cddddf617c34132380ad49a660de9037de43850263f4c8`.

Pruebas focalizadas, en el runner Docker aislado:

```sh
python -m pytest tests/test_project_user_assignments.py tests/test_auth_rbac.py tests/test_user_administration.py -o cache_dir=/tmp/pytest-cache -q
```

Suite general, en el mismo entorno:

```sh
docker run --name software-pa-assignments-qa-full-20261002 \
  --network software-pa-assignments-qa-20261002 \
  --env-file /tmp/software-pa-assignments-qa/qa.env \
  --mount type=bind,src=/home/alfredo/proyectos/Software-PA/backend,dst=/app,readonly \
  -e PYTHONDONTWRITEBYTECODE=1 software-pa-backend \
  python -m pytest -o cache_dir=/tmp/pytest-cache -q
```

OpenAPI se exportó en un runner equivalente con:

```sh
python -c 'import json; from app.main import app; print(json.dumps(app.openapi(),ensure_ascii=False,indent=2))'
```

La salida se guardó íntegra en `docs/openapi.json`, sin editar contratos a mano.

## Resultados y cobertura

- Focalizadas: **23 aprobadas, 0 fallidas, 0 omitidas**, en 17.47 segundos.
- Suite general completa: **370 aprobadas, 0 fallidas, 0 omitidas**, en 160.55 segundos; salida del runner `0`.
- Una advertencia preexistente de deprecación Starlette/httpx.
- `git diff --check` sin errores; sintaxis Python verificada sin generar bytecode.
- Checksums 001–020 verificados nuevamente al terminar; ningún archivo de migración cambió.

La primera ejecución focalizada produjo 17 aprobadas, 6 fallidas y un error de
teardown. Se corrigieron fixtures nuevas que reutilizaban hechos operativos con
unicidad, el borrado anticipado de un proyecto seguido por limpieza repetida
(403 según la convención vigente), y la consulta estadística de bloqueos que
reutilizaba su snapshot. No fue necesario cambiar implementación del servicio
ni contratos existentes. En preparación de QA se corrigieron también el uso de
TCP durante el arranque temporal y campos de identidad RAN sintéticos incompletos.

Logs conservados fuera del repositorio:
`/tmp/software-pa-assignments-qa/focused-initial.log`, `focused-fixed.log` y
`full.log`. En ese directorio también están las entradas de preparación sintética
y ambas exportaciones OpenAPI para comprobar la comparación contra HEAD.

| Requisitos | Evidencia de integración |
|---|---|
| A–E, G–K, Q, T | Ciclo completo: GET/POST, duplicado, baja, repetición sin cambios, nueva fila, historial y bitácora; otras parejas intactas. |
| F, L, S | Tres roles con sesión real: listado paginado, detalle, listado/detalle ProyectoNucleo y actividades; captura y edición GIS permitidas según rol antes de la baja y rechazadas después. Reasignación conserva límites del rol. |
| M–O | Anónimos 401, CSRF ausente/incorrecto 403, usuario inexistente 404, proyecto inexistente/inactivo 403 y pareja sin asignación activa 404. |
| P | Siete entradas inválidas: ausencia de cuerpo/motivo, vacío, espacios, motivos insuficientes y longitud excesiva; 422 sin cambios. |
| R | Cuenta inactiva con relación activa puede desasignarse; reactivar la cuenta no restaura acceso ni cambia histórico. La suite previa cubre también la baja completa de cuenta. |
| U | Dos POST concurrentes dan 201/409; dos DELETE dan 200/404 y un solo UPDATE auditado. POST espera una baja no confirmada y crea otra fila al confirmarse. |

La repetición de DELETE preserva todos los campos de la relación y su bitácora;
también se comprueba que no aumenta el total global de bitácora. Se verifican
motivo, actor, fechas originales, timestamps de baja/actualización y snapshots
anteriores/nuevos. La sesión del usuario permanece válida y otra asignación
conserva acceso, mientras el proyecto revocado responde 403.

En concurrencia se usan conexiones independientes, bloqueos reales y
`pg_blocking_pids`; la consulta de observación usa autocommit para renovar las
estadísticas. No se omiten las comprobaciones de carreras. El caso de inserción
durante una baja pendiente prepara directamente el UPDATE transaccional con los
helpers reales; los otros dos casos ejercen los endpoints HTTP concurrentes.

## Estado final de Git

Rama: `task/backend-desasignacion-proyectos`; HEAD se conserva en `750ec71`.
`git status --short`:

```text
 M backend/app/routers/domain.py
 M backend/app/services/domain.py
 M docs/API.md
 M docs/openapi.json
?? backend/tests/test_project_user_assignments.py
?? docs/QA_ASIGNACIONES_PROYECTO.md
```

`git diff --stat` de los archivos seguidos:

```text
 backend/app/routers/domain.py  |  15 +
 backend/app/services/domain.py |  28 ++
 docs/API.md                    |  38 +-
 docs/openapi.json              | 793 ++++++++++++++++++++++++++++++++++-------
 4 files changed, 753 insertions(+), 121 deletions(-)
```

Además, hay dos archivos nuevos sin staging: 376 líneas de pruebas y este
informe. `git diff --quiet -- backend/db/migrations docs/MIGRACIONES.md frontend
frontend-ssalfer` confirmó que esas rutas no tienen cambios.

## Pendientes y propuesta de commit

La integración queda pendiente de revisión humana; no se hizo commit ni push.
La exportación OpenAPI incluye la corrección del desfase documental previo.
La desasignación de un admin no limita el acceso global que le concede su rol.
No se implementa reactivación de asignaciones ni asignación de responsabilidades.

Mensaje propuesto:

```text
feat(backend): completar desasignación administrativa de usuarios por proyecto
```
