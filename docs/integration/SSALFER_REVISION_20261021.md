# Correcciones de revisión colaborativa del PR #2

Rama local `integration/ssalfer-mq-f01-f06-20261020`, sobre
`58875d3845e45fd744a822a2a11867f69e6ce279`. Trabajo exclusivo en el worktree
de integración. No se publica esta revisión, se fusiona el PR ni se despliega.

El compañero comunicó equivalencia general en navegador usando una copia de su
base. Esa comprobación corresponde a la versión anterior. Esta revisión ejecutó
pruebas Node VM/DOM y API/PostgreSQL; no ejecutó navegación real ni Windows.

## Defectos y correcciones

| Hallazgo | Origen comprobado | Corrección |
| --- | --- | --- |
| Inicialización administrativa con acceso denegado | Ambos scripts GIS son idénticos entre `d73615f` y `58875d3`; el problema precede a la integración F01–F06 | Esperar `SSALFER_SESION_LISTA` y comprobar admin/geógrafo antes de leer DOM, registrar controles o construir componentes |
| Excel falla con `tipo_convenio=null` | Preexistente en el escritor de `cbc78d0`, conservado y registrado en `58875d3` | Mostrar `Tipo no informado` en la celda, conservando el nulo en los datos originales |
| Pruebas sensibles a LF/CRLF | Los lectores comparaban checkout y `git show` o buscaban delimitadores con LF literal | Normalizar exclusivamente el texto fuente leído por los tests; conservar las expectativas de datos, filas y resultados |
| Orden de convenios | El recorrido anterior dependía de tres workers; F04 ya responde por `id_convenio` ascendente | Ordenar una copia del arreglo al exportar, siguiendo ese mismo criterio, sin modificar el arreglo recibido ni perder filas |

Los diez casos de arranque GIS cubren sesión pendiente/resuelta, admin/geógrafo,
operador, visualizador y ausencia de sesión, con DOM presente o retirado por la
pantalla de denegación. No hay trabajo administrativo, solicitudes ni errores
de consola en los casos denegados. La conciliación conserva el orden de carga
respecto al gestor y solo se publica su helper después de autorizar la sesión.

El Excel se genera con el bundle ExcelJS real y sus bytes se reabren para
comparar celdas. Las pruebas recorren los cuatro roles, congelan el payload,
conservan contadores/CSV y verifican que el orden de entrada no se muta. Se
comparan conjuntos de filas y valores antes/después, además del orden por ID,
incluyendo fechas nulas y consecutivos distintos al orden de identificadores.
No se introduce una categoría ni se modifica un cálculo.

## Permisos efectivos conservados

| Operación sobre proyecto activo | Admin | Geógrafo | Operador | Visualizador |
| --- | --- | --- | --- | --- |
| Dashboard, mapa publicado e indicadores | Permitido | Permitido | Solo con asignación activa | Permitido |
| Administración GIS y previsualizaciones internas/históricas | Permitido | Permitido | 403 | 403 |

Sin autenticación se conserva 401; los recursos GIS inexistentes mantienen 404
para roles autorizados, y los proyectos inactivos siguen rechazados según la
política existente. El backend continúa protegiendo las 22 operaciones
administrativas mediante `require_gis_management`. No cambia `READ_ROLES`, la
asignación exclusiva a operadores, la API cartográfica ni la migración 030.
Las pruebas focalizadas ejercitan identificadores directos, revocaciones,
proyectos inactivos, bajas e historia, además de lecturas y decisiones GIS.

## Auditoría del límite de 100 núcleos

El límite **no es exclusivamente visual**: `dashboard_summary.project_agreements`
selecciona los primeros 100 vínculos activos ordenados por entidad, municipio y
nombre. Sus COP individuales/colectivos/formalizados y el detalle de convenios
del Excel se calculan sobre ese subconjunto; el listado/exportación de núcleos
también usa la primera página. Así funcionaba antes de F01–F06 y así se conserva.

El KPI histórico del dashboard utiliza otra consulta, `/dashboard/kpi`, con
paginación predeterminada de 500 filas; no comparte el límite de 100 núcleos.
Los valores declarados tampoco usan ese recorte de núcleos. Ninguno de estos
límites o contratos se modifica en esta corrección.

El mapa pagina sus lecturas administrativas y su agregado de indicadores abarca
todos los núcleos activos del proyecto. Se comprobó con los cuatro roles que un
convenio firmado únicamente en el núcleo 105 **sí cuenta en el mapa**, mientras
el resumen COP del dashboard conserva su exclusión histórica. Los módulos
calculan indicadores con criterios distintos; no deben compararse como si todos
representaran el mismo universo. Ampliar la cobertura del dashboard queda para
una decisión y cambio posteriores.

## Validación ejecutada

| Pruebas | Aprobadas | Fallos | Omisiones |
| --- | ---: | ---: | ---: |
| Backend: RBAC GIS (35), dashboard F04 (56), mapa seleccionado (12) | 103 | 0 | 0 |
| JavaScript con LF | 49 | 0 | 0 |
| Mismas JavaScript con CRLF simulado en memoria | 49 | 0 | 0 |

El segundo pase JavaScript comprueba las mismas 49 pruebas; no son 49 casos
adicionales. Incluye regresiones de mapa, reportes colectivos/financieros/general,
reapertura XLSX del reporte general y seguimiento F06. El backend emitió una
advertencia preexistente de deprecación Starlette/httpx.

Como control negativo se ejecutaron ocho casos nuevos contra los tres scripts
de `58875d3`, sustituyendo las fuentes solo en memoria: los ocho detectaron los
defectos esperados (seis arranques denegados, nulo XLSX y orden). No se alteró el
checkout para esa comprobación.

PostgreSQL/PostGIS se ejecutó en el proyecto desechable
`ssalfer-review-20261021`, base `software_pa_test`, cluster
`convenio-report-disposable`, almacenamiento tmpfs, red interna y sin puertos
publicados. Se restauró el esquema 029 de prueba previamente saneado, catálogos
de prueba y datos públicos RAN; se aplicó la 030 únicamente allí. No se conectó
a la base del compañero ni a producción. El contenedor y su red se retiraron
al terminar; los logs locales se conservan. Hubo un reintento de preparación tras
el reinicio normal de PostgreSQL durante su primera inicialización; ocurrió
antes de cargar el esquema y no fue un fallo de producto.

Se cotejaron los hashes de 145 archivos de backend, migraciones y pruebas con
la [evidencia completa anterior](SSALFER_VALIDACION_20261020.json): todos se
conservan. No se repite la suite completa; se reutiliza su registro histórico
de **1,488 aprobadas, tres fallos preexistentes y 27 omitidas**. No se afirma
haber vuelto a ejecutar ni corregido esos casos en esta revisión.

Los tres fallos pendientes son:

- `test_facetas_respetan_naturaleza_sin_depender_de_pagina`: Aguascalientes frente
  a la entidad sintética esperada.
- `test_018_backfill_specific_record_from_017_transition`: `termino_periodo`
  frente a `sin_clasificar`.
- `test_dataset_excludes_actual_additional_ran_identities`: 19 frente a 51.

Las 27 omisiones históricas conservan su desglose: 23 de escritura del ledger,
dos de backfill DDL GIS, una de reproducción RAN y una de último administrador.
El defecto Excel nulo pasa a **corregido**, con regresión positiva; el informe
del 20 de octubre se conserva como evidencia histórica, no como estado actual
de ese defecto. No se observaron regresiones nuevas en las pruebas ejecutadas.

Los comandos JavaScript, la selección pytest, los hashes de fuentes y de los
logs locales están en [SSALFER_REVISION_20261021.json](SSALFER_REVISION_20261021.json).
Evidencia temporal: `/tmp/ssalfer-review-20261021/`. Las mediciones históricas
[F04](../performance/FASE_04_DASHBOARD.md),
[F05](../performance/FASE_05_MAPA_INDICADORES.md) y
[F06](../performance/FASE_06_REPORTES.md) conservan sus valores; esta revisión
no presenta nuevos tiempos de navegador ni una nueva campaña de rendimiento.

## Revalidación del compañero

Después de autorizar y realizar una publicación posterior, obtener la rama en
un worktree de pruebas independiente y comprobar que su HEAD incluye ambos
commits de esta revisión. Consultar el
[informe de integración y migración 030](SSALFER_INTEGRACION_20261020.md) y utilizar
una copia aislada, manteniendo su base original y rama de desarrollo intactas.
No hay migraciones nuevas por
estas correcciones; verificar la 030 ya prevista en la copia de pruebas.

1. Con operador y visualizador, abrir directamente Gestión geoespacial, recargar
   y repetir con sesión ausente. Debe mostrarse la denegación o el inicio de
   sesión existente, según corresponda, sin
   excepciones ni peticiones administrativas iniciadas por los módulos.
   Una petición API administrativa directa debe seguir devolviendo 403 para
   ambos roles y 401 sin sesión.
2. Con admin y geógrafo, verificar carga normal de Gestión, selección de proyecto,
   conciliación e historia. Comprobar que el mapa publicado siga disponible
   para los cuatro roles dentro de su alcance y que un operador sin asignación
   o un proyecto inactivo sigan bloqueados.
3. Con un registro ya nulo en la copia local, exportar el Excel del dashboard y
   abrirlo en Excel/LibreOffice: etiqueta `Tipo no informado`, mismas filas,
   valores y totales, orden por ID ascendente (no por consecutivo o fecha).
   Comparar dos exportaciones con la misma información.
4. Repetir dashboard, mapa, reporte general, reportes de convenios y exportaciones;
   registrar rol/proyecto, pasos, consola/red y diferencias. En proyectos de más
   de 100 núcleos distinguir la cobertura histórica del dashboard de la del mapa.
5. En el checkout Windows ejecutar `node --test tests/frontend-ssalfer/*.cjs`.
   Para repetir la simulación sin cambiar el checkout:
   `node --require ./tests/frontend-ssalfer/helpers/crlf-checkout.cjs --test tests/frontend-ssalfer/*.cjs`.

Se recomienda publicar estos commits para esa revalidación una vez autorizado.
La aprobación de navegación de la versión anterior no sustituye esa prueba.
