# SSALFER — Fase 0 y Fase 1.1 / F01

> Integración 2026-10-20: alcance vigente y validación conjunta en
> [SSALFER_INTEGRACION_20261020.md](../integration/SSALFER_INTEGRACION_20261020.md).
> Las mediciones y el entorno descritos abajo corresponden a la fase original.

Fecha: 19 de octubre de 2026. **Validado en entorno local aislado.** Se optimizó
únicamente `GET /api/proyectos`. No se modificaron producción, bases persistentes,
migraciones, modelos, esquemas, políticas de acceso ni cálculos. Sin push, merge
ni deploy. La ejecución se detiene aquí; F02 y fases posteriores quedan pendientes
de autorización.

## Preparación y antecedentes verificados antes de modificar el endpoint

| Dato | Valor registrado |
| --- | --- |
| Computadora de Codex | `Cooper`, distinta de `patrenes` |
| Checkout original | `/home/alfredo/proyectos/Software-PA`, `feature/backend-logica`, `2183ab20091f977208912f101748d5ff10c3f735`, limpio |
| Worktree independiente | `/tmp/software-pa-ssalfer-optimizacion-fase1` |
| Rama nueva | `perf/ssalfer-optimizacion-fase1` |
| Commit base | `630f7dd66c494a1f2a4b4375184ff49a3a5b540b`, limpio al crear el worktree |
| Proyecto Compose exclusivo de pruebas | `ssalfer-f01-20261019` |
| Configuración existente reutilizada | `backend/tests/convenio_report_compose.yml` |
| Base de pruebas | `software_pa_test`, cluster `convenio-report-disposable` |
| Aislamiento | PostgreSQL nuevo en tmpfs, red Docker interna, sin puertos publicados ni volúmenes persistentes; código montado en lectura |
| Datos y credenciales | Exclusivamente sintéticos del Compose de pruebas; sin `.env`, cookies, cuentas ni datos productivos |

Se leyó la auditoría completa:
`/tmp/ssalfer-auditoria-20261019-hguiqw/INFORME_AUDITORIA_SSALFER_2026-10-19.md`,
incluidas sus condiciones y limitaciones. El commit se recuperó mediante fetch
local y se cotejó nuevamente por SSH, sin modificar referencias en el servidor.

La consulta SSH del **19-oct-2026 18:42:20 UTC** volvió a confirmar:

- `patrenes` en `630f7dd66c494a1f2a4b4375184ff49a3a5b540b`.
- Conexión efectiva del engine del backend a `db_integracion_mq_qa`.
- Migraciones `001–029`, todas con checksum correcto respecto del backend activo.
- Los 33 módulos Python desplegados coinciden byte a byte con el commit base.
- Modificaciones preexistentes en `docker-compose.ssalfer.yml` y el auxiliar
  `docker-compose.ssalfer.yml.git`, sin intervención.

La inspección de base usó una transacción `REPEATABLE READ READ ONLY`, con
`statement_timeout=1500ms` y `lock_timeout=200ms`, terminada con rollback.
No se iniciaron sesiones HTTP ni se ejecutaron pruebas en el servidor.

El preparador existente `tests/setup_convenio_report_db.py` instaló las
migraciones **sin alterarlas** únicamente en el PostgreSQL desechable vacío,
con catálogo territorial mínimo y administrador sintético. Rechaza otra
identidad de instancia o un esquema previamente instalado. Las fixtures F01
quedan contenidas en rollback externo; las regresiones existentes de sesiones
y concurrencia escriben únicamente en este contenedor desechable.

Versiones: Python 3.11.17, FastAPI 0.138.2, SQLAlchemy 2.0.51, Pydantic 2.13.4,
psycopg2 2.9.12, pytest 9.1.1, PostgreSQL 15.4 y PostGIS 3.3.4.

El registro previo a cambios y el OpenAPI original se guardaron en
`/tmp/ssalfer-f01-evidence/preparation.json` y `openapi-original.json`.
La metadata y las muestras se conservan también en
[FASE_01_PROYECTOS_MEDICIONES.json](FASE_01_PROYECTOS_MEDICIONES.json).

## Cambio técnico

`ProyectoResponse` utiliza columnas de `Proyecto`. El modelo configura
relaciones `selectin` que recorren núcleos, actividades, asignaciones y otras
colecciones aunque el JSON del listado no las incluya.

Se añadió `.options(raiseload("*"))` exclusivamente a la consulta de
`list_projects`, más su importación. Esto sustituye los cargadores de relaciones
para esta lectura e impide una carga accidental al serializar. Se conservan
`filter_projects_by_user`, `activo IS TRUE`, `nombre_proyecto`, offset, límites,
`RoleChecker`, autenticación y `ProyectoResponse` sin modificaciones.

No se cambió `models.py` ni `services/access.py`. Las fichas y demás consultas
conservan sus estrategias de carga. No hay caché, nuevas dependencias, servicios,
contratos ni migraciones.

## Línea base y comparación

La consulta de referencia en las pruebas reproduce exactamente el cuerpo de
`list_projects` de `630f7dd`; se cotejó por AST contra el archivo original
extraído de Git. Antes de cambiar código de aplicación pasaron **33 pruebas**
de equivalencia, acceso, sesiones y paginación. La línea base de 15 muestras
dio **13 SELECT, 24 objetos y mediana 8.319 ms** para dos proyectos sintéticos.

Fixture: 207 proyectos insertados en orden inverso al nombre; 205 activos y dos
inactivos. Operador tiene 202 proyectos activos asignados, una asignación
revocada y un proyecto asignado inactivo; visualizador y geógrafo consultan los
205 proyectos activos sin asignaciones. Hay un núcleo compartido entre dos
proyectos, dos PN y 24 actividades.

La comparación final usa **15 pares por proceso**, alternando original/optimizado
y optimizado/original, después de un calentamiento excluido por variante.
Cada muestra usa una Session nueva y devuelve los mismos dos proyectos.

| Medición | Original | Optimizado |
| --- | ---: | ---: |
| SELECT funcionales por muestra, ambas ejecuciones | 13 | **1** |
| Objetos ORM retenidos por muestra, ambas ejecuciones | 24 | **2** |
| SQL adicional al serializar, ambas ejecuciones | 0 | **0** |
| Mediana primera comparación, 15 muestras por variante | 10.268 ms | **1.270 ms** |
| Mediana repetición en otro proceso, 15 muestras por variante | 8.327 ms | **0.901 ms** |
| JSON por cada par | Idéntico | Idéntico |

También se verificó **1 SELECT y exactamente 200 objetos** al devolver 200
proyectos, para cada uno de los cuatro roles, sin cargar relaciones ni emitir
SQL al serializar.

Los tiempos corresponden a consulta y materialización ORM. Excluyen
autenticación, HTTP y serialización; los conteos SQL excluyen control de
transacciones/savepoints. Los objetos son `len(Session.identity_map)` al
terminar la lectura, no memoria pico. No se limpiaron cachés ni se calculó p95.
No se impone un umbral de milisegundos al test para evitar fallos por ruido del
equipo; los presupuestos SQL, objetos y equivalencia sí son obligatorios.

Las cifras auditadas **37→1 SQL, 1580→2 objetos y 71.073→0.831 ms** pertenecen a
otro dataset y hardware. Se conservan como antecedente; no se presentan como
una medición nueva ni como mejora prometida del dashboard.

## Pruebas y resultados

| Ejecución | Resultado |
| --- | --- |
| Baseline antes de cambiar el endpoint | 33 aprobadas; 5 pruebas de optimización excluidas deliberadamente |
| Suite F01 completa | **38 aprobadas**, 0 fallidas, 0 omitidas; 4.35 s |
| Autenticación/RBAC, asignaciones y concurrencia existentes | **29 aprobadas**, 0 fallidas, 0 omitidas; 18.80 s |
| Repetición del benchmark en proceso independiente | 1 aprobada; 1.63 s |
| OpenAPI generado frente a captura original | Idéntico byte a byte en JSON con claves ordenadas; 140 paths |
| AST del resto de funciones de `domain.py` | Idéntico al commit base |
| Modelos, esquemas, autenticación, autorización y migraciones | Sin cambios respecto del commit base |
| `git diff --check` | Sin errores |

**67 pruebas únicas aprobadas** entre la suite F01 y las regresiones existentes;
no se suman las repeticiones del baseline o benchmark como cobertura adicional.

Cobertura F01: admin, operador, visualizador y geógrafo; respuestas JSON
completas; nulos, fechas, Unicode y auditoría; alcance antes de paginar;
activos/inactivos; asignaciones vigentes/revocadas/históricas; ausencia de fuga
por núcleo compartido; usuario sin asignaciones; límites 1/100/200; offsets
0/199/205/999 y páginas vacías. En HTTP se compararon bytes y estados usando
sesiones reales sintéticas: 200, 401, 403 y 422, recursos ajenos/inactivos y
ausentes, parámetros inválidos y consulta de sesión. Se conservó el 403 que la
ficha devuelve actualmente para un proyecto ausente.

Las regresiones existentes cubrieron además CSRF, revocación de acceso sin
revocar otras asignaciones/sesiones, reactivación, auditoría y bloqueos de
asignación/baja concurrentes. No se alteraron expectativas para aprobarlas.
Durante la preparación se corrigieron defectos del fixture nuevo: actor de
asignación obligatorio, unicidad de actividades y localización de rutas
incluidas en FastAPI 0.138.2. El baseline válido se ejecutó después de esas
correcciones y antes de modificar el endpoint.

Las ejecuciones emitieron únicamente la advertencia de deprecación preexistente
de Starlette/httpx. No se cambiaron dependencias.

### Reproducción local

Desde la raíz del worktree, usando un nombre de proyecto Docker nuevo o después
de eliminar **solo** el proyecto desechable anterior:

```bash
docker compose -p ssalfer-f01-20261019 -f backend/tests/convenio_report_compose.yml up -d --wait db
docker compose -p ssalfer-f01-20261019 -f backend/tests/convenio_report_compose.yml run --rm -T --no-deps worker python tests/setup_convenio_report_db.py
docker compose -p ssalfer-f01-20261019 -f backend/tests/convenio_report_compose.yml run --rm -T --no-deps worker python -m pytest -p no:cacheprovider tests/test_projects_read_performance.py -q -s
docker compose -p ssalfer-f01-20261019 -f backend/tests/convenio_report_compose.yml run --rm -T --no-deps worker python -m pytest -p no:cacheprovider tests/test_auth_rbac.py tests/test_project_user_assignments.py tests/test_assignment_concurrency_regressions.py -q
docker compose -p ssalfer-f01-20261019 -f backend/tests/convenio_report_compose.yml run --rm -T --no-deps worker python -m pytest -p no:cacheprovider tests/test_projects_read_performance.py::test_benchmark_original_vs_optimized -q -s
docker compose -p ssalfer-f01-20261019 -f backend/tests/convenio_report_compose.yml down -v
```

Los JUnit XML, OpenAPI original, comprobaciones estáticas y muestras completas
de esta ejecución quedan en `/tmp/ssalfer-f01-evidence`. Ese directorio es temporal;
las métricas y condiciones relevantes se incluyen en el JSON versionado citado.
La instancia desechable se eliminó al terminar.

## Diff, commit y reversión

Archivos de la entrega:

- `backend/app/routers/domain.py`: importación y opción local de carga;
  cinco líneas añadidas y dos retiradas.
- `backend/tests/test_projects_read_performance.py`: regresiones F01, consulta
  original congelada y medición reproducible.
- `docs/performance/FASE_01_PROYECTOS.md`: este informe.
- `docs/performance/FASE_01_PROYECTOS_MEDICIONES.json`: condiciones y muestras.

Entrega preparada como un único commit local con mensaje
`perf: limita la carga ORM de GET /api/proyectos (F01)`; su identificador se
obtiene con `git log -1 --format='%H %s'` en la rama indicada y se informa al
cierre. Sin integración con otras ramas ni cambios en el checkout original.

Reversión: revertir ese commit local, o retirar la opción `raiseload("*")` y su
importación para restaurar la consulta original. No hay datos ni migraciones
que revertir. Cualquier despliegue o reversión en servidor requiere una
autorización posterior y queda fuera de esta entrega.

## Límites y pendientes

No quedan pruebas obligatorias pendientes para F01 en este entorno aislado.
No se ejecutó la suite completa del repositorio, navegación de navegador, HAR,
carga concurrente de producción ni una copia de datos reales. No se promete
una reducción equivalente del tiempo de pantalla. Un futuro campo relacional
en `ProyectoResponse` deberá declarar su carga y revisar el presupuesto SQL;
la guarda hará visible ese cambio en las pruebas.

F02, F03, dashboard, mapas, reportes y demás optimizaciones no se implementaron.
