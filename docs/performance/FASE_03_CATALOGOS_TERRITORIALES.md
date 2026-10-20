# F03 — Catálogos territoriales

> Integración 2026-10-20: alcance vigente y validación conjunta en
> [SSALFER_INTEGRACION_20261020.md](../integration/SSALFER_INTEGRACION_20261020.md).
> Las mediciones y el entorno descritos abajo corresponden a la fase original.

**F03 validada en el entorno local aislado. F01/F02 continúan aprobadas.
La suite global no está en verde: quedan tres incompatibilidades de fixtures,
también reproducibles con la aplicación original, y 27 omisiones preexistentes.**

## Entorno y alcance

Implementación local del 19 de octubre de 2026 sobre
`6e622ffa2daa63f3184722241968516893493c82`, que conserva F01 (`f98586e`) y F02.
Rama: `perf/ssalfer-optimizacion-fase1`.
Worktree independiente y persistente:
`/home/alfredo/proyectos/Software-PA/.worktrees/ssalfer-optimizacion-fase1`.
El estado inicial estaba limpio. El checkout original continúa en
`feature/backend-logica`, separado de este trabajo.

Se comprobó que el equipo y el daemon Docker son locales (`Cooper`), con socket
`unix:///var/run/docker.sock`. El backend persistente monta el checkout original
`/home/alfredo/proyectos/Software-PA/backend`, no el worktree. No se accedió por SSH
ni se utilizó producción para pruebas o mediciones de F03. El estado productivo
descrito por la auditoría es un antecedente documental, no una medición actual.

Solo cambian tres consultas GET de `backend/app/routers/domain.py`:

| Endpoint | Función | Universo conservado |
| --- | --- | --- |
| `/api/catalogos/entidades` | `list_states` | Entidades activas, clave INEGI ascendente |
| `/api/catalogos/municipios` | `list_municipalities` | Municipios activos, filtro opcional de entidad, clave INEGI ascendente |
| `/api/nucleos` | `list_nuclei` | Admin: núcleos activos; visualizador/geógrafo: vinculados a cualquier proyecto activo; operador: proyectos asignados y vínculos activos; filtro municipal y paginación originales |

`/api/catalogos/nucleos` y `services/domain.py:list_ran_nuclei_catalog` ya usan
proyección de columnas con joins explícitos. Se incluyen como control sin
modificar su implementación. Este catálogo nacional filtra fuente RAN y tipo de
tenencia, tiene búsqueda y límite propios, y no se restringe por asignación a
proyectos. No se sustituye por `/api/nucleos`.

No cambian modelos, esquemas, helpers de acceso, autenticación, sesiones, CSRF,
escrituras, migraciones, geometrías, identificadores ni criterios de búsqueda.
No se continúa con dashboard, mapas, reportes, GIS o frontend.

## Causa y solución

Las relaciones `selectin` de entidad → municipios → núcleos activan a su vez
proyectos, ORV, padrones, parcelas y trámites RAN. El lote selectin multiplica las
consultas aunque el DTO solo exponga columnas de la entidad raíz. Los proyectos
y sus relaciones operativas pueden ampliar todavía más ese grafo.

Se añade `.options(raiseload("*"))` a las tres consultas concretas. Esto anula
localmente la carga automática de relaciones y hace fallar un acceso accidental
a ellas, en vez de ejecutar SQL silencioso. Se mantienen todas las columnas
raíz y las mismas expresiones de filtrado, joins, distinct, orden, offset y limit.
No se cambia globalmente ninguna relación ni se introduce caché.

Los DTO actuales solo leen atributos escalares. Las pruebas verifican tanto
la equivalencia contractual como la ausencia de SELECT al serializar y la
prohibición local de acceder a relaciones. Se conserva el valor contractual
predeterminado de `geometria_wkt`; no se añade procesamiento espacial.

## Datos y aislamiento

Proyecto Compose nuevo: `ssalfer-f03-20261019`, usando
`backend/tests/convenio_report_compose.yml`. PostgreSQL 15.4 / PostGIS 3.3.4,
base `software_pa_test`, cluster `convenio-report-disposable`, almacenamiento
tmpfs, red interna sin puertos publicados ni volumen persistente. Worker con
backend del worktree montado en lectura. Usuarios/contraseñas exclusivos de
prueba, sin credenciales productivas. Python 3.11.17, SQLAlchemy 2.0.51,
FastAPI 0.138.2, Pydantic 2.13.4 y pytest 9.1.1.

El preparador verifica host, destino, ledger y checksums; restaura únicamente
el esquema de una base **local de pruebas**, ledger 001–029 y cuatro catálogos
estáticos con actores sanitizados. No copia usuarios ni datos funcionales.
No ejecuta migraciones. Crea un actor sintético y aplica los fixtures existentes
en el destino desechable:

- 32 entidades y 2,478 municipios: `001_catalogo_territorial_inegi.sql`.
- 32,278 núcleos: CSV público versionado `catalogo_nucleos_ran.csv`, 29,852 ejidos
  y 2,426 comunidades de las 32 entidades, cargado con el importador existente.
- Dataset SHA256: `863d31fff0f9b0338a103c7858872d4f531fe2b2593aade514dac2233d2fa6c3`.
- Crosswalk SHA256: `ddadabf417571722b50289724486045037f020c7e6fc2e49db69585d6c6651cb`.

Se validaron manifiesto, bytes, encoding, identidades y crosswalk antes de cargar:
32,278 inserciones, cero errores y cero municipios sin resolver. La procedencia
es el snapshot público aprobado en el repositorio; no se certifica su vigencia
frente al portal RAN actual. Los tests añaden tres núcleos y un pequeño grafo
de proyectos/asignaciones, contenido en rollback externo.

Esto prueba cardinalidad nacional del catálogo público, no toda la historia
operativa ni los aproximadamente 32,352 núcleos de la base auditada. No hay
geometrías nacionales, usuarios reales ni un grafo operativo nacional denso.
No se extrapolan tiempos a producción ni a la latencia de pantalla.

## Mediciones y validación

Se obtuvo una línea base antes de cambiar aplicación: **56 pruebas aprobadas**
en 86.89 s. Después se compararon referencia y cambio con los mismos datos:
una muestra de calentamiento por variante y cinco muestras alternadas, cada
una con Session nueva. Tiempo de la función de consulta, sin HTTP ni
serialización; no son tiempos de EXPLAIN ni de producción. El recolector se
ejecuta antes de cada muestra. No hay aserciones frágiles de umbrales temporales.

| Listado sin filtros, admin | SQL antes → después | ORM cargados antes → después | Mediana ms antes → después |
| --- | ---: | ---: | ---: |
| Entidades, 32 filas | 341 → **1** | 34,794 → **32** | 3124.144 → **1.712** |
| Municipios, 2,478 filas | 340 → **1** | 34,762 → **2,478** | 3068.107 → **13.681** |
| Núcleos, página de 100 | 6 → **1** | 100 → **100** | 20.978 → **14.603** |
| Catálogo RAN, 20 filas, sin cambios | 1 → **1** | 0 → **0** | 57.427 → **59.022** |

En la página inicial de núcleos no hay vínculos operativos precargables: se
eliminan cinco SELECT vacíos, pero no cambia la cantidad de objetos. Las pruebas
de asignaciones sí incluyen un núcleo compartido entre dos proyectos. En RAN
no se atribuye mejora: la diferencia temporal es variación de un control sin
cambio de código.

Consultas de autenticación: excluidas de la medición directa, con pruebas HTTP
separadas. La autorización de `/api/nucleos` sigue en el mismo SELECT mediante
join/subconsulta; no tiene consultas separadas. Los otros catálogos conservan
la comprobación de rol. Los contadores funcionales incluyen todo SELECT
transitivo emitido durante la función, no solo la consulta raíz.

| Listado | Pico Python MiB antes → después | JSON bytes antes = después |
| --- | ---: | ---: |
| Entidades | 193.794 → **0.074** | 2,352 |
| Municipios | 194.091 → **6.200** | 246,251 |
| Núcleos, página de 100 | 0.973 → **0.524** | 50,922 |
| Catálogo RAN | 0.074 → **0.074** | 5,048 |

Memoria: una muestra separada por variante con `tracemalloc`, incluyendo
consulta y serialización. Es pico de asignaciones Python rastreadas, **no RSS**,
memoria de PostgreSQL ni memoria nativa total; no se usa esa muestra para las
medianas temporales. Los objetos se cuentan con `loaded_as_persistent`; también
se registra el tamaño retenido de identity_map. Los bytes son JSON compacto
UTF-8 de los DTO, sin cabeceras/transporte.

Las cinco parejas comparan contenido completo y los tamaños y hashes SHA256
coinciden por endpoint. En todas hay **cero SQL y cero objetos ORM adicionales
durante serialización**, tanto en original como en optimizado. El JSON crudo de
muestras y memoria está en [FASE_03_MEDICIONES.json](FASE_03_MEDICIONES.json).

Las regresiones cubren las 32 entidades, municipios de diferentes entidades,
filtros combinados e inexistentes, búsqueda literal `%`, `_` y `\\`, paginación,
parámetros inválidos, cuatro roles, proyecto no asignado, revocación, vínculos
compartidos e inactivos y registros territoriales inactivos. Se compara además
HTTP/JSON byte a byte con la referencia y `401` sin sesión; los parámetros
inválidos siguen dando `422`. El listado fuera de asignación sigue devolviendo
`[]`, sin introducir un `403` nuevo. No se modifica ningún contrato `404`.

Se preserva expresamente la semántica anterior: municipios y RAN no incorporan
un filtro nuevo sobre la actividad de la entidad padre; RAN tampoco filtra la
actividad del municipio padre. Eso se prueba sin corregir esas reglas en F03.

La comparación del OpenAPI completo usa el archivo capturado antes del cambio,
no una expectativa regenerada. La revisión AST confirma que solo cambian
`list_states`, `list_municipalities` y `list_nuclei`; todas las demás funciones
del router son idénticas. Modelos, esquemas, autenticación, access.py,
services/domain.py y pruebas F01/F02 son idénticos byte a byte a `6e622ff`.

| Ejecución | Resultado |
| --- | --- |
| Línea base antes del cambio de aplicación | 56 aprobadas, 4 pruebas de presupuesto/guardas excluidas; 86.89 s |
| F03 específica y OpenAPI completo | **60 aprobadas**, cero fallidas/omitidas; 125.28 s |
| F01/F02 específicas | **211 aprobadas**, cero fallidas/omitidas; 42.37 s |
| Suite completa final | **1,238 casos: 1,208 aprobadas, 3 fallidas, 27 omitidas**; 617.39 s |
| Control con router original `6e622ff` | Los tres fallos se reproducen sin F03; ver detalle abajo |

Los 60 casos F03 y las regresiones F01/F02 pasan también en la ejecución
completa. F01 mantiene su presupuesto de una consulta funcional; los
presupuestos y decisiones de F02 se siguen cumpliendo. Se verifica equivalencia
de JSON, visibilidad y OpenAPI, no solo reducción de SQL. El OpenAPI previo
archivado tiene SHA256
`c0179cf0b1066aebb177d29d19f781eea1577b8cdbee5ec9884234277b822cc0`.

| Rol | `/api/nucleos` | Catálogos territoriales/nacional |
| --- | --- | --- |
| Administrador | Núcleos activos, sin restricción por asignación | Mismo universo territorial/RAN de la referencia |
| Operador | Solo proyectos/asignaciones/vínculos activos autorizados | Mismo universo territorial/RAN de la referencia |
| Visualizador | Núcleos activos vinculados a cualquier proyecto activo | Mismo universo territorial/RAN de la referencia |
| Geógrafo | Núcleos activos vinculados a cualquier proyecto activo | Mismo universo territorial/RAN de la referencia |

La revocación se refleja en una sesión SQLAlchemy nueva, sin caché entre
peticiones. La suite F02 vuelve a comprobar sesiones reales, usuarios inactivos,
sesiones inválidas y decisiones `403`/`404` de los contextos; F01 vuelve a
comprobar autenticación. Las pruebas de autenticación y asignaciones de la
suite completa también comprueban CSRF y pasan. No se cambia seguridad para
reducir consultas.

### Seguimiento de los cuatro fallos documentados en F02

| Prueba | Estado en la suite F03 |
| --- | --- |
| `test_without_filters_is_bounded_stable_and_only_returns_ran` | **Aprobada**, ahora hay al menos 20 filas RAN públicas reales |
| `test_valid_limit_and_maximum_are_enforced` | **Aprobada**, ahora hay al menos 100 filas RAN públicas reales |
| `test_dataset_excludes_actual_additional_ran_identities` | Sigue fallando: espera exactamente 51 identidades históricas adicionales; hay 19 identidades sintéticas ajenas al CSV creadas por otros tests |
| `test_018_backfill_specific_record_from_017_transition` | Sigue fallando: espera históricos 017→018 con causa `sin_clasificar`; los registros válidos creados por tests tienen `termino_periodo` |

Además, `tests/test_convenio_general_report.py::test_facetas_respetan_naturaleza_sin_depender_de_pagina`
espera literalmente `Entidad sintética A` para id 1. El fixture territorial
versionado conserva el nombre real `Aguascalientes`. Es una incompatibilidad
previa del test con el catálogo nacional, ajena a la carga ORM; no se cambió el
reporte, el nombre real ni la expectativa. Se reprodujo **el mismo fallo** en
3.01 s montando en lectura el router original de `6e622ff`, con todos los demás
archivos de aplicación idénticos a esa revisión y la misma base aislada.
Los dos fallos históricos también se repitieron con esa aplicación original.

Pendientes globales: preparar fixtures de históricos 017→018, las identidades
adicionales reales pertinentes y desacoplar la expectativa de reporte de un
nombre sintético, en un trabajo autorizado separado. No se inventaron
históricos, no se alteraron causas ni se modificaron resultados esperados.
No hay fallos nuevos atribuibles a las tres consultas optimizadas, pero **no se
declara validada toda la suite**.

Las **27 omisiones** se mantienen y se registran sin ocultarlas:

- 23 controles de escritura de ledger/linaje requieren instancia explícitamente autorizada.
- 2 backfills DDL requieren su guarda de instancia desechable.
- 1 sincronización completa requiere `RAN_REPRO_DATABASE` preparada.
- 1 prueba administrativa requiere un único administrador activo.

No se habilitaron esas guardas ni se ejecutaron migraciones para aprobarlas.
Permanece la advertencia preexistente de Starlette/httpx; no es un fallo F03.

## Reproducción y evidencias

Evidencia persistente local, fuera del código versionado:
`/home/alfredo/proyectos/Software-PA/.worktrees/ssalfer-f03-evidence`.
Contiene preparación verificable, manifiesto, esquema local, línea base,
OpenAPI previo, mediciones pareadas y reportes JUnit. El preparador es
`prepare_database.py`; rechaza un esquema destino existente.

La referencia de cuatro funciones en `backend/tests/fixtures/f03_baseline.py`
se extrajo de `6e622ff`; se verificaron sus AST antes de modificar aplicación.
No se ajusta la referencia a los resultados optimizados.

Desde la raíz del worktree, con la base desechable preparada y el catálogo
público precargado:

```bash
docker compose -p ssalfer-f03-20261019 -f backend/tests/convenio_report_compose.yml run --rm -T --no-deps worker python -m pytest -p no:cacheprovider tests/test_territorial_catalog_performance.py -q
docker compose -p ssalfer-f03-20261019 -f backend/tests/convenio_report_compose.yml run --rm -T --no-deps worker python -m pytest -p no:cacheprovider tests/test_projects_read_performance.py tests/test_access_context_performance.py -q
```

Las mediciones JSON se escriben solo al definir `F03_EVIDENCE_DIR` apuntando a
un volumen escribible. La comparación OpenAPI usa `F03_BASELINE_OPENAPI` con el
archivo previo a la implementación. El backend permanece montado en lectura.
Para la suite completa se montan en lectura los paquetes locales de pruebas
`jsonschema`, `attr`, `attrs` y `pyrsistent` bajo `/test-libs`, usando
`PYTHONPATH=/app:/test-libs`. No se instalan dependencias ni se habilitan guardas
de linaje o migraciones.

## Cambios y reversión

Archivos: router (tres opciones de carga), referencia F03, pruebas F03, este
informe y el JSON de mediciones. F01 y F02 permanecen sin cambios. Resumen del
diff de aplicación: tres líneas añadidas y tres eliminadas, en tres consultas.
Las pruebas y documentos son archivos nuevos, sin otros cambios ajenos.

Commit final de código:
`97fc45875c1d7d765d798dd591e920e747f506e3`
(`perf: limita carga ORM de catalogos territoriales F03`). Incluye las tres
opciones de carga y sus pruebas/referencia. El commit documental de entrega es
`docs: registra validacion y limites de F03`; su hash final se informa al cierre
y se obtiene con `git log -1` en esta rama. Ambos son posteriores e independientes
de F01/F02, sin push ni merge.

Reversión: revertir el commit de código de F03 conserva F01/F02; no requiere
migraciones ni cambios de datos. Una ampliación futura del DTO que necesite
relaciones debe declarar su carga explícita y volver a validar el presupuesto
SQL. No se aplicó ninguna reversión ni despliegue.

El proyecto desechable se eliminó al cerrar la entrega con
`docker compose -p ssalfer-f03-20261019 -f backend/tests/convenio_report_compose.yml down -v`.
La evidencia permanece en disco. Ningún servicio persistente ni servidor fue
modificado o reiniciado. Producción, contenedores productivos y
`db_integracion_mq_qa` permanecen intactos; no hay migraciones nuevas.

Esta ejecución termina en F03. La siguiente fase del plan es F04 (dashboard),
pendiente de autorización; no se ha comenzado.
