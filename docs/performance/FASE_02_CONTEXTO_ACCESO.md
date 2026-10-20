# SSALFER — Fase 1.2 / F02: contexto de acceso

> Integración 2026-10-20: alcance vigente y validación conjunta en
> [SSALFER_INTEGRACION_20261020.md](../integration/SSALFER_INTEGRACION_20261020.md).
> Las mediciones y el entorno descritos abajo corresponden a la fase original.

Fecha: 19 de octubre de 2026. Alcance: contexto mínimo optativo para diez
endpoints de lectura de dominio. No se modifican decisiones RBAC, sesiones,
CSRF, modelos, contratos, cálculos ni flujos de escritura. No se implementa F03.

**Subconjunto F02 validado; certificación global pendiente de cuatro pruebas
preexistentes sin su dataset nacional/histórico.** F01 continúa funcionando.

## Entorno y preparación

- Computadora local: `Cooper`; no es `patrenes` ni `172.16.1.215`.
- Rama: `perf/ssalfer-optimizacion-fase1`.
- Base verificada: `f98586eb4633e07b2481a7a67ee62ee81aa7d938`, con F01 presente.
- Worktree persistente recuperado, limpio antes de comenzar:
  `/home/alfredo/proyectos/Software-PA/.worktrees/ssalfer-optimizacion-fase1`.
- El checkout original conserva `feature/backend-logica` en `2183ab2`.
- Proyecto Compose exclusivo: `ssalfer-f02-20261019`; configuración existente
  `backend/tests/convenio_report_compose.yml`, sin cambios.
- PostgreSQL/PostGIS nuevo, almacenamiento tmpfs, red interna, sin puertos
  publicados, código montado en lectura y credenciales sintéticas de pruebas.
- Base: `software_pa_test`; cluster comprobado: `convenio-report-disposable`.

Se registraron ruta, rama, commit, limpieza y estrategia de pruebas en
`.worktrees/ssalfer-f02-evidence/preparation.json` antes de modificar aplicación.
Se guardó el OpenAPI de F01 antes del cambio. La referencia de autorización y
lecturas se extrajo de Git y se verificó por AST contra `f98586e`.

No se ejecutaron migraciones. Se restauró un dump **solo de esquema** de la base
de pruebas del Docker local y se copiaron su ledger 001–029 y cuatro catálogos
sin usuarios, datos funcionales ni referencias personales de auditoría. Los
checksums locales se verificaron contra los archivos antes de restaurar.
Se crearon usuarios, entidades territoriales y dominio exclusivamente sintéticos.
El rol histórico `pa_app` necesario para restaurar ACL se creó sin login; no se
copiaron credenciales. La fuente local solo recibió lecturas.

La primera ejecución amplia detectó dos defectos de preparación: se habían
eliminado notas canónicas y sustituido por un actor sintético los nulos
históricos del catálogo retirado. Se restauraron esos metadatos desde la fuente
local y se cargó el fixture territorial existente de 32 entidades/2478 municipios.
Los actores no nulos se anonimizan, los nulos conservan su significado. No se
modificaron expectativas ni reglas. Las primeras mediciones usaron dos
entidades/municipios sintéticos; la repetición final usó el catálogo territorial
completo y mantuvo los mismos conteos SQL/objetos de los ocho patrones.

No se accedió al servidor por SSH durante F02. No hubo modificaciones de
producción, cambios de servicios persistentes, push, merge ni deploy.

Versiones: Python 3.11.17, FastAPI 0.138.2, SQLAlchemy 2.0.51, Pydantic 2.13.4,
pytest 9.1.1, PostgreSQL 15.4 y PostGIS 3.3.4.

## Problema y estrategia

Las verificaciones recuperaban entidades con relaciones `selectin` transitivas.
La auditoría midió unos 60 SELECT para un listado de convenios vacío, aunque
solo uno correspondía a la consulta funcional. Esas cifras pertenecen a otro
dataset; la línea base sintética de esta entrega es independiente.

`require_project_access` ya admitía `load_details=False`, utilizado por el
reporte general. Se conservó esa función sin cambios. Se extendió el mismo
patrón a:

- `require_project_nucleus_access`: `load_details=True` por defecto; con `False`
  aplica `raiseload("*")` a PN y propaga la opción al proyecto.
- `require_affectation_access`: misma opción; con `False` suprime las relaciones
  de afectación y propaga el contexto mínimo por PN hasta el proyecto.

Se conservan entidades ORM y columnas escalares, incluidos IDs y campos activos.
No se difieren columnas ni se carga ninguna colección para autorizar. No se
introducen cachés, joins nuevos, principal sintético en producción ni reutilización
de permisos entre peticiones. El coste de autorización es constante por nivel:
proyecto, 1 SELECT; PN, 2; afectación, 3.

Se mantienen el orden de las verificaciones y los filtros originales: el hijo
activo o su 404, luego PN activo o su 404, proyecto activo y rol; solo operador
requiere asignación vigente o recibe 403. No se añadieron ni retiraron comprobaciones del núcleo global.
Las pruebas incluyen su baja para asegurar equivalencia con la política existente.

Todos los llamadores que no optan explícitamente conservan `load_details=True`,
incluidos captura, GIS y escrituras. Los handlers de escritura de `domain.py`
permanecen idénticos por AST al commit F01.

## Endpoints optimizados

| GET | Función |
| --- | --- |
| `/api/proyectos/{id_proyecto}` | `get_project` |
| `/api/proyectos/{id_proyecto}/nucleos` | `list_project_nuclei` |
| `/api/proyecto-nucleo/{id_proyecto_nucleo}` | `get_project_nucleus` |
| `/api/proyecto-nucleo/{id_proyecto_nucleo}/referencias` | `list_references` |
| `/api/proyecto-nucleo/{id_proyecto_nucleo}/actividades` | `list_activities` |
| `/api/proyecto-nucleo/{id_proyecto_nucleo}/afectaciones` | `list_affectations` |
| `/api/proyecto-nucleo/{id_proyecto_nucleo}/asambleas` | `list_assemblies` |
| `/api/proyecto-nucleo/{id_proyecto_nucleo}/tramites-ran` | `list_ran_procedures` |
| `/api/afectaciones/{id_afectacion}/convenios` | `list_agreements` |
| `/api/proyecto-nucleo/{id_proyecto_nucleo}/fifonafe` | `list_fifonafe` |

Solo cambió la llamada de contexto en estas funciones. Se conservan consultas
funcionales, filtros, orden, paginación y relaciones necesarias para responder.
Por ejemplo, las convocatorias, eventos RAN y relaciones FIFONAFE siguen presentes.

## Mediciones reproducibles

Antes de modificar aplicación se aprobaron **133 pruebas** y se midieron los
ocho patrones originales con siete muestras cada uno. La comparación posterior
usa siete pares por patrón, alternando original/optimizado y optimizado/original,
con un calentamiento excluido por variante y una Session nueva por muestra.

Los datos son los mismos en ambas variantes: dos proyectos, un núcleo compartido
entre ellos, otro núcleo, tres PN, cuatro afectaciones, una asamblea con
convocatoria, un convenio colectivo con Decimal, un RAN con evento, un FIFONAFE
con evento y tres actividades. Solo operador tiene asignado el primer proyecto;
visualizador y geógrafo conservan el acceso de lectura global a proyectos activos.

| Patrón | SELECT total antes→después | Objetos cargados antes→después | Mediana ms antes→después |
| --- | ---: | ---: | ---: |
| Contexto proyecto | 32→1 | 22→1 | 25.991→1.101 |
| Contexto PN | 61→2 | 22→2 | 47.034→1.790 |
| Contexto afectación | 66→3 | 22→3 | 53.206→2.919 |
| Convenios vacíos | 67→4 | 22→3 | 62.631→4.578 |
| Actividades | 62→3 | 25→5 | 48.112→2.519 |
| Asambleas | 69→10 | 28→8 | 60.070→9.143 |
| RAN | 63→4 | 24→4 | 56.877→4.264 |
| FIFONAFE | 66→7 | 25→5 | 54.535→6.456 |

Descomposición de los SELECT; se conserva el coste funcional necesario:

| Listado | Autorización antes→después | Funcionales antes→después | Serialización antes→después |
| --- | ---: | ---: | ---: |
| Convenios vacíos | 66→3 | 1→1 | 0→0 |
| Actividades | 61→2 | 1→1 | 0→0 |
| Asambleas | 61→2 | 8→8 | 0→0 |
| RAN | 61→2 | 2→2 | 0→0 |
| FIFONAFE | 61→2 | 5→5 | 0→0 |

Autenticación: excluida de estos patrones internos; se prueba por separado
mediante sesiones HTTP reales sintéticas. No se presenta el conteo como coste
HTTP total. Los tiempos incluyen autorización, consulta y materialización ORM;
excluyen serialización, HTTP y autenticación. Solo se cuentan SELECT/WITH, no
control transaccional/savepoints. No se vaciaron cachés ni se reporta p95.

Objetos cargados significa eventos `loaded_as_persistent`, no memoria pico.
Se registró también `len(Session.identity_map)` al terminar: en convenios vacíos
es 0 en ambas variantes porque el contexto ya salió de alcance; en actividades,
asambleas, RAN y FIFONAFE se retienen respectivamente 3/6/2/3 objetos en ambas.
No se confunde esa retención con el trabajo realizado durante autorización.

Todos los pares devolvieron resultados idénticos. Las pruebas exigen ausencia
de SQL al serializar y 1/2/3 consultas y objetos de autorización según profundidad.
Añadir 60 actividades no cambió ninguno de esos conteos; acceder a una relación
del contexto mínimo dispara `InvalidRequestError` en las pruebas.

Muestras y condiciones completas:
[FASE_02_CONTEXTO_MEDICIONES.json](FASE_02_CONTEXTO_MEDICIONES.json).

La segunda comparación, en otro proceso tras corregir las referencias, repitió
siete pares por patrón. Ejemplos de mediana: proyecto 26.625→1.075 ms, PN
42.050→1.729 ms, afectación 51.121→2.735 ms y convenios vacíos 58.031→4.141 ms.
Las consultas y objetos de la tabla fueron idénticos en ambas comparaciones.

## Validación funcional y de seguridad

La suite específica aprobó **211 pruebas**: 173 de F02 y las 38 de F01.
Se comparan bytes de respuesta y estados HTTP contra las diez funciones
originales congeladas, usando la misma base y los mismos registros.

La matriz incluye los cuatro roles, asignaciones vigentes/revocadas, proyectos
ajenos/inactivos, PN y afectaciones inactivos, recursos inexistentes y el núcleo
compartido. Se comparan 96 combinaciones de contexto/rol/estado, 32 grupos HTTP,
cuatro escenarios de sesiones reales, 36 combinaciones de modo/rol/contexto
con carga por defecto y tres pruebas de guarda y crecimiento de relaciones.

Las sesiones reales cubren ausencia de cookie, token inválido, sesión válida,
usuario posteriormente inactivo y acceso fuera de alcance. Se mantienen 401,
403 y 404 con sus detalles y precedencia. Las pruebas existentes de seguridad
comprueban además CSRF y revocación concurrente.

El OpenAPI completo conserva 140 paths y es idéntico al de F01 en JSON con
claves ordenadas. SHA-256:
`0270fc8f7edacaed68e287b1c44dce96c85fa49140f46287dd5ec3d6b537f72f`.
No cambiaron `models.py`, `schemas.py`, autenticación, reporting ni migraciones.
La comprobación final en lectura confirmó 29 entradas de ledger, todos sus
checksums válidos y el OpenAPI idéntico antes de eliminar la instancia.

### Suite completa, control original y correcciones de preparación

| Ejecución | Resultado |
| --- | --- |
| Baseline previo a implementación | 133 aprobadas; 45.58 s |
| F02 y F01 específicas | 211 aprobadas, 0 fallidas; 43.55 s |
| Suite completa inicial | 1178 casos: 1134 aprobadas, 17 fallidas, 27 omitidas; 496.26 s |
| Control con aplicación y tests originales de `f98586e` | Los mismos 17 casos fallan; 18 regresiones de autenticación/asignaciones pasan; 18.71 s |
| Repetición final tras corregir preparación y aislamiento | 241 casos: **237 aprobadas, 4 fallidas**, 0 omitidas; 60.07 s |

Las 237 aprobadas finales incluyen **las 173 de F02 y las 38 de F01**, las 18
regresiones de autenticación/asignaciones y ocho casos antes bloqueados por
metadatos/territorio. Estos números se solapan con la suite inicial; no se suman
como cobertura única adicional. No se volvió a ejecutar toda la suite después
de ajustar el fixture; se repitieron todos los casos fallidos y las suites F01/F02
junto con módulos que dejan proyectos sintéticos activos.

Los cinco fallos administrativos de F01 procedían de proyectos activos de otros
módulos presentes antes de su fixture. Se corrigió exclusivamente su aislamiento:
la fixture desactiva esos proyectos dentro de su rollback externo y restaura
íntegramente el estado al salir. Se conservan todas las aserciones, orden y
expectativas de 205 proyectos activos. La consulta de aplicación de F01 mantiene
el AST exacto de `f98586e`.

Los cuatro fallos restantes, también reproducidos con F01 original, son:

| Prueba | Limitación de datos; pendiente |
| --- | --- |
| `test_without_filters_is_bounded_stable_and_only_returns_ran` | Espera 20 filas nacionales precargadas; el entorno dispone de 19 identidades sintéticas creadas por otros tests |
| `test_valid_limit_and_maximum_are_enforced` | Espera al menos 100 filas RAN precargadas |
| `test_dataset_excludes_actual_additional_ran_identities` | Depende del catálogo nacional completo y exactamente 51 identidades históricas adicionales de otra base |
| `test_018_backfill_specific_record_from_017_transition` | Presupone que los cinco primeros ORV históricos provienen de una migración 017→018 y tienen causa `sin_clasificar`; los creados por tests tienen una causa funcional válida, `termino_periodo` |

No se inventaron históricos, se reclasificaron causas, se importaron datos
funcionales ajenos ni se cambiaron esas aserciones para aprobarlas. Requieren
fixtures nacionales/históricos independientes. No afectan los diez lectores
optimizados y quedan pendientes de una validación global, fuera de este
subconjunto. No se declara la suite completa en verde.

Las 27 omisiones de la ejecución completa corresponden a guardas/prerrequisitos
preexistentes, incluidos los ensayos de actualización/linaje que requieren otra
instancia y permisos explícitos. No se habilitaron para ejecutar migraciones.
Las ejecuciones ordinarias emitieron la advertencia preexistente de
Starlette/httpx; el arranque de baseline desde Python también emitió una
advertencia de reescritura de asserts de pytest/anyio.

### Evidencia y reproducción sin migraciones

El directorio persistente local `.worktrees/ssalfer-f02-evidence` conserva el
dump de esquema local, el código original archivado de F01, los catálogos
saneados, preparación, OpenAPI y JUnit de todas las ejecuciones. No contiene
usuarios, contraseñas, cookies ni datos funcionales copiados de otra base.
Los tests sí generan registros sintéticos en su instancia desechable.

El preparador local revisable está en
`/home/alfredo/proyectos/Software-PA/.worktrees/ssalfer-f02-evidence/prepare_database.py`.
Comprueba `Cooper`, la identidad de la fuente local y el ledger, y restaura solo
en el proyecto desechable identificado; rechaza un esquema destino existente.
Con Docker local disponible y ese proyecto limpio se puede volver a ejecutar
para reconstruir el entorno. No utilizar `tests/setup_convenio_report_db.py`
en esta fase porque ejecuta migraciones.

Desde la raíz del worktree, después de preparar esa base:

```bash
docker compose -p ssalfer-f02-20261019 -f backend/tests/convenio_report_compose.yml run --rm -T --no-deps worker python -m pytest -p no:cacheprovider tests/test_access_context_performance.py tests/test_projects_read_performance.py -q -s
docker compose -p ssalfer-f02-20261019 -f backend/tests/convenio_report_compose.yml run --rm -T --no-deps worker python -m pytest -p no:cacheprovider tests/test_auth_rbac.py tests/test_project_user_assignments.py tests/test_assignment_concurrency_regressions.py -q
docker compose -p ssalfer-f02-20261019 -f backend/tests/convenio_report_compose.yml down -v
```

Para la suite completa se montaron en lectura los paquetes de pruebas JSON
Schema ya instalados localmente (`jsonschema`, `attr`, `attrs`, `pyrsistent`)
bajo `/test-libs`, con `PYTHONPATH=/app:/test-libs`. No se instalaron dependencias.
Las mediciones se guardan estableciendo `F02_EVIDENCE_DIR` a un directorio
escribible montado; sin esa variable se imprimen resúmenes y no se escribe en
el repositorio montado en lectura.

La instancia desechable se eliminó al cerrar la entrega.

## Archivos, commits y reversión

- `backend/app/services/access.py`: dos opciones de carga y propagación del contexto.
- `backend/app/routers/domain.py`: diez opt-in de lectura; F01 intacto.
- `backend/tests/fixtures/f02_baseline.py`: referencia extraída de F01, sin adaptar expectativas.
- `backend/tests/test_access_context_performance.py`: comparación RBAC, HTTP y medición por fase.
- `backend/tests/test_projects_read_performance.py`: aislamiento transaccional de su fixture, sin cambiar expectativas ni implementación F01.
- Este informe y el JSON de mediciones.

Commits locales, todos posteriores a F01:

- `197b3de`: contexto mínimo optativo para PN y afectación.
- `7553112`: aislamiento del fixture F01 entre módulos, mismas expectativas.
- `ec0cd62`: diez lecturas con opt-in y referencia/regresiones F02.
- Commit documental final: `docs: registra resultados y limites de F02`; el hash
  final se informa al cierre y se consulta con `git log -1` en la rama indicada.

No hay merge ni push.

Reversión: revertir los commits de F02, primero los consumidores y después los
helpers. F01 se conserva. No hay migración ni datos persistentes que revertir.
No aplicar esa reversión ni desplegar sin autorización posterior.

## Subconjunto pendiente y límites

F02 se entrega como subconjunto seguro. Quedan pendientes, en cambios separados,
los demás lectores de `require_nucleus_access`, los contextos tipados de asamblea,
convenio, FIFONAFE/RAN, documentos y otros consumidores. No se cambiaron sus
políticas ni su carga por defecto. Tampoco se tocaron reporting, KPI, mapas,
frontend, GIS ni catálogos F03. Los cambios futuros deben declarar qué relaciones
necesita cada DTO, especialmente los recursos compartidos.

Estas mediciones sintéticas no certifican tiempos del servidor, navegador ni
un dashboard completo. No hay benchmark de carga productiva ni promesa de una
mejora equivalente en pantalla. No se utilizaron cuentas o credenciales reales.

La siguiente optimización recomendada por el plan es F03: cargas explícitas de
catálogos territoriales, tras autorización. Esta ejecución se detiene en F02.
