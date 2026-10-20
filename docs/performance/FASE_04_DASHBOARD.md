# F04 — Dashboard HTML/JavaScript

**F04 validada en el entorno aislado; F01–F03 continúan aprobadas. La suite
completa conserva tres fallos previos de fixtures y 27 omisiones. Quedan
pendientes las pruebas de navegador y el caso previo Excel/tipo nulo.**

## Estado y punto de partida

Cierre local de la entrega: **20 de octubre de 2026**. Las muestras conservan
sus fechas originales del 19 de octubre en los archivos de evidencia.

F04 implementada localmente sobre `cbc78d051629e10c52343bbf861737be0fbd8bfd`,
que conserva F01, F02 y F03. Rama `perf/ssalfer-optimizacion-fase1`;
worktree persistente e independiente:
`/home/alfredo/proyectos/Software-PA/.worktrees/ssalfer-optimizacion-fase1`.
Estado inicial limpio, sin cambios ajenos. Equipo/daemon Docker `Cooper`, socket
local `unix:///var/run/docker.sock`; el backend persistente monta el checkout
original, no el worktree. El checkout original permanece separado y sin cambios.

Se leyó la auditoría integral de 851 líneas del 19-oct-2026 y sus límites.
Su commit desplegado/base/métricas son antecedentes históricos, no medidas
actuales del servidor. No hubo acceso SSH ni pruebas en producción en F04.
Se comprobó que `frontend-ssalfer` de `cbc78d0` coincide íntegramente con el
frontend del commit auditado `630f7dd`. Se trabaja en HTML/JS tradicional; no se
toca React. No se reutilizan los tiempos productivos de la auditoría como si
fueran la línea base local.

## Dependencias y decisiones que conservan resultados

El dashboard ejecutaba dos listados de proyectos, KPI, valores declarados y,
por proyecto, el listado de núcleos y el recorrido núcleo → afectaciones →
convenios. `dashboardExcel.js:contarConvenios` deduplica por `id_convenio`,
cuenta ámbitos individuales/colectivos y considera formalizado cualquier
convenio de esos ámbitos con fecha de firma. No usa el criterio del KPI histórico.

Hay dos límites funcionales previos, **conservados**:

- `NucleosAPI.listarPorProyecto` solicita una sola página, por defecto de 100
  vínculos activos, ordenada por entidad, municipio y nombre del núcleo. El
  dashboard y su Excel no incluyen el núcleo 101 en adelante. No se amplía ese
  universo silenciosamente; la ficha de proyecto tiene otro cliente paginado.
- KPI mantiene el límite global original de 500 filas; el reporte de valores
  declarados y sus reglas/coberturas/valores nulos tampoco se modifican.

Excel utiliza los núcleos, KPI y convenios capturados durante la carga del
dashboard, además de metadatos del proyecto y gráficos. Se conserva esa carga
anticipada y **no se añade ninguna lectura al pulsar Excel**. No se difiere la
información ni se convierte la exportación en una actualización. CSV sigue
usando su endpoint existente, que consulta al descargar. No se cambia esa
diferencia temporal previa entre Excel y CSV.

## Backend: endpoint aditivo y consultas por conjuntos

Nuevo `GET /api/proyectos/{id_proyecto}/dashboard/convenios`:

- Autenticación de sesión y `RoleChecker` de los cuatro roles existentes.
- `require_project_access(..., load_details=False)` **antes** de recuperar IDs
  o agregar información. Proyecto activo y asignación activa vigente para no-admin.
- Una consulta proyecta los IDs de los primeros 100 vínculos desde la misma
  `ProyectoNucleoResumen`, con el filtro/orden/página anteriores.
- Otra consulta une afectaciones y vínculos de convenio activos con convenios
  activos; deduplica las columnas raíz por ID en una subconsulta, y cuenta con
  `COUNT FILTER OVER` sobre ese conjunto ya único. Ninguna consulta por fila.
- El detalle mínimo para Excel se obtiene en esa misma consulta, sin recuperar
  relaciones ORM. Solo se carga un objeto ORM: el contexto de proyecto autorizado.

Coste del endpoint: **1 SELECT de autorización + 2 funcionales**, independiente
del número de núcleos/afectaciones. No incluye las consultas legítimas de sesión.
Serializar su respuesta no ejecuta SQL adicional.

Contrato nuevo, también declarado en OpenAPI:

| Campo | Tipo / regla |
| --- | --- |
| `individuales` | entero, convenios únicos activos de ámbito individual |
| `colectivos` | entero, convenios únicos activos de ámbito colectivo |
| `formalizados` | entero, ámbitos anteriores con `fecha_firma IS NOT NULL` |
| `convenios` | lista de detalle mínimo, ordenada por ID |
| `convenios[].id_convenio` | entero |
| `convenios[].ambito` | ámbito existente individual/colectivo |
| `convenios[].tipo_convenio` | string o **null**, sin sustituirlo |
| `convenios[].consecutivo` | entero |
| `convenios[].fecha_firma` | fecha ISO o **null** |

Sin convenios: conteos cero y lista vacía. Sesión inválida/inactiva: `401`;
proyecto inexistente, inactivo o ajeno: `403`, igual que el contexto anterior;
ID inválido/no positivo: `422`. No se añaden criterios de estado, tipo de
instrumento, fecha actual o firma acreditada que el recorrido no aplicaba.
Un instrumento `otro` con tipo nulo sigue formando parte de su ámbito.
No se exige actividad del núcleo global ni de sus padres territoriales cuando
la consulta previa no la exigía. Las pruebas comprueban esa semántica.

No se agregan montos: permanecen en el endpoint de valores declarados. Por tanto
la relación N:M no multiplica importes en el resumen nuevo ni cambia los tipos
Decimal de APIs anteriores. Todos los endpoints, esquemas y funciones de
reporting previos permanecen iguales; no se editan vistas ni migraciones.

## Frontend: peticiones y concurrencia

`dashboard.js` comparte una única Promise de proyectos entre sus dos consumidores
iniciales. Vive únicamente en el closure del documento: no hay caché de permisos
ni información sensible en almacenamiento persistente o entre peticiones API.
Una nueva página/usuario vuelve a consultar la información.

Proyectos, KPI y valores declarados comienzan en paralelo. Por proyecto se
consultan el listado de núcleos existente (necesario para Excel) y el nuevo
resumen COP. Como máximo tres proyectos se procesan simultáneamente: seis GET
de detalle, sin una tormenta de solicitudes proporcional a las afectaciones.
Las tarjetas tienen posición y estado de carga propios; una tarjeta lenta no
impide completar las otras. El DOM y el Excel conservan el orden de proyectos,
incluyendo cuando las respuestas llegan en distinto orden.

Si falla KPI/valores se conservan los estados previos. Un fallo COP muestra
`Sin dato`, nunca un cero inventado. Si el listado de núcleos falla o está vacío,
se conserva el comportamiento anterior: lista vacía y contador cero. Un proyecto
no bloquea la exportación de los demás. Los datos quedan asociados al proyecto
de cada tarea; no se reutilizan contextos de otro documento/usuario.

Para `P` proyectos, `N` vínculos de la página y `A` afectaciones activas:

| Camino inicial del dashboard | Antes | Después |
| --- | ---: | ---: |
| Sesión memoizada | 1 | 1 |
| Listado de proyectos, sin llegar a 200 | 2 | 1 |
| KPI y valores | 2 | 2 |
| Listado de núcleos | P | P |
| Afectaciones y convenios individuales | N + A | 0 |
| Resumen COP | 0 | P |
| Total | 5 + P + N + A | **4 + 2P** |

Si proyectos requiere varias páginas, se mantiene su paginación y cada página
se comparte entre consumidores; la fórmula anterior solo supone un lote de
proyectos. No se fuerza un total constante respecto de proyectos autorizados.

Con el volumen de auditoría (2 proyectos, 75 vínculos, 92 afectaciones), son
**174 → 8**. Antes era estimación estática de la auditoría. Aquí también se
reprodujeron ambos conteos ejecutando los scripts reales con dobles HTTP/DOM en
Node VM; **no son 174/8 solicitudes capturadas en HAR ni tiempos de navegador**.
Los cuatro roles producen tarjetas/celdas equivalentes bajo sus respectivos
universos autorizados: admin 174→8; otros roles del fixture, 171→6.

## Línea base y mediciones reproducibles

Se establecieron las referencias antes de modificar cada implementación:
baseline backend aprobada en 3.61 s antes del cambio backend, OpenAPI completo
capturado, y ejecución original JS/XLSX aprobada antes de modificar frontend.
Los recorridos de referencia backend siguen utilizando las funciones existentes
sin cambios; el frontend original se obtiene del commit inmutable `cbc78d0`.

Datos sintéticos operativos, contenidos en rollback externo: cuatro proyectos,
108 núcleos propios, un núcleo compartido con otro proyecto, proyecto vacío,
vínculos sin afectaciones, afectaciones sin convenios, convenios multiafectación,
firmados/sin firma y uno solo visible fuera de la primera página de 100.
Se prueban inactivos, revocaciones, ámbitos, nulos y restricciones de los roles.
No es una copia de la historia agraria/financiera de producción.

Mediciones directas del recorrido COP frente al endpoint nuevo, cinco parejas
alternadas, Session nueva por muestra y calentamiento por variante. Tiempo
incluye autorización de proyecto/consulta/fetch; autenticación de sesión no se
simula como coste cero productivo, se excluye expresamente de esta medición.
La columna objetos cuenta eventos `loaded_as_persistent`:

| Escenario | SQL autorización antes→después | SQL funcional antes→después | ORM antes→después | Mediana ms antes→después |
| --- | ---: | ---: | ---: | ---: |
| Pequeño, 3 núcleos | 19→1 | 25→2 | 29→1 | 34.725→4.124 |
| 105 núcleos, página de 100 | 501→1 | 601→2 | 601→1 | 883.243→5.930 |
| Proyecto vacío | 1→1 | 1→2 | 1→1 | 4.388→4.750 |

La referencia directa incluye obtener la lista de núcleos para recorrerla; el
nuevo endpoint no reemplaza el listado que conserva el frontend. Por ello la
comparación completa por proyecto, **incluyendo ese listado conservado**, se
midió adicionalmente con TestClient y sesiones SQL separadas por petición:

| Escenario | Peticiones API antes→después | SELECT antes→después | Mediana total TestClient ms antes→después |
| --- | ---: | ---: | ---: |
| Pequeño | 8→2 | 44→5 | 80.417→20.143 |
| 105 núcleos, página de 100 | 201→2 | 1,102→5 | 2132.245→34.258 |

Estos tiempos son rondas locales TestClient, con autorización real de alcance
y principal de prueba inyectado; excluyen TCP, TLS, navegador y coste de sesión.
No son tiempos de render ni navegación. La respuesta COP nueva da cero SQL al
serializar. Los cinco SELECT finales son dos autorizaciones y tres consultas
funcionales (listado existente más dos del resumen). No se impone una consulta
por endpoint a costa de seguridad. El proyecto vacío tiene un pequeño coste
adicional al pedir preventivamente un resumen en paralelo: no se declara mejora
en ese caso. No hay p95 ni ensayo de carga productiva.
El número de consultas es acotado, pero bytes y memoria del detalle siguen
creciendo con los convenios exportables. Se conservan esos datos anticipados
para no cambiar la política de Excel; no se afirma tiempo/memoria constantes.

Muestras originales: [FASE_04_MEDICIONES.json](FASE_04_MEDICIONES.json).

## Navegación, frescura y exportaciones

La aplicación conserva href y documentos HTML independientes. Regresar por
enlace inicia nuevas lecturas acotadas, sin el recorrido N+A. La protección de
sesión existente (`proteccion.js`) fuerza `location.reload()` cuando `pageshow`
indica restauración BFCache: **se conserva**, sin ampliar una ventana de acceso
ni servir datos anteriores como actuales. No se añade caché de retorno, SPA,
interceptores de enlaces ni cambios a logout/CSRF.

No se encontró navegador ejecutable ni instalación Playwright utilizable.
Se ejecutó Node VM con dobles DOM/HTTP y el bundle ExcelJS real del repositorio,
generando bytes XLSX y reabriéndolos con ExcelJS para comparar las celdas.
`html2canvas` se sustituye por una imagen de prueba: cifras/celdas y contenido
de tarjetas sí se comparan; captura visual, canvas real, accesibilidad visual,
HAR, BFCache efectivo, navegación inicial/regreso/Atrás y caché HTTP caliente
**quedan pendientes de navegador de staging**. No se inventan tiempos de carga,
render ni navegación. Se comprobaron documentos nuevos y cambios rápidos en
contextos VM independientes, con datos de diferentes roles y respuestas lentas.

El escritor Excel completo es idéntico byte a byte al original; solo se ordena
su registro de proyectos antes de habilitar el botón, porque las tareas ahora
terminan en paralelo. Se conservan fórmulas defensivas contra inyección de
celdas, nombres de hojas, metadatos, importes, nulos, KPI y filas de núcleos y
convenios. Se comparan celdas, no bytes ZIP/timestamps de generación.
Antes, la inserción de convenios dependía del orden de finalización de tres
workers; no tenía un orden de red contractual. El resumen nuevo ordena por ID,
sin perder ni duplicar miembros/valores. No se cambia el orden de proyectos.

**Problema previo, documentado sin corregir:** un instrumento `otro` puede tener
`tipo_convenio=null`; el exportador original invoca `.replaceAll` sobre ese campo
y falla. Se reproduce el mismo error con los scripts originales de `cbc78d0` y
los nuevos. Las tarjetas siguen siendo iguales, la API conserva null y las
pruebas no sustituyen ese dato para conseguir una exportación artificialmente
correcta. El XLSX de ese caso queda pendiente de una corrección funcional
autorizada; no se declara validado. Los casos normales y fallos parciales
descritos sí generan XLSX con celdas equivalentes. CSV y APIs previas no cambian.

## Validación

| Ejecución | Resultado |
| --- | --- |
| Backend específico F04 | **56 aprobadas**, cero fallidas/omitidas; 26.30 s |
| JavaScript/Excel F04, ubicación definitiva | **7 aprobadas**, cero fallidas/omitidas; 3.75 s |
| Regresiones F01/F02/F03 | **271 aprobadas**, cero fallidas/omitidas; 185.96 s |
| Suite completa inicial | 1,263 aprobadas, 4 fallidas, 27 omitidas; 682.80 s |
| Control del OpenAPI publicado después de corregirlo | 1 aprobada; 1.27 s |
| Suite completa final en base reconstruida | **1,294 casos: 1,264 aprobadas, 3 fallidas preexistentes, 27 omitidas**; 671.30 s |
| Control con la aplicación original `cbc78d0` | Los mismos **3 fallos** reproducidos; 3.40 s |

Los siete casos JS comprueban las cuatro cuentas, tarjetas HTML exactas,
XLSX generado/leído, CSV, >100 núcleos, fallos parciales de KPI/valores/núcleos/COP,
respuestas fuera de orden, nuevas páginas/usuarios y el error nulo preexistente.
Los 56 de backend comparan conteos y conjuntos completos de convenios, no solo
totales. `401`, `403`, `422`, registros activos/inactivos, ámbito compartido y
revocaciones se comprueban explícitamente. F01/F02 vuelven a probar sesiones
reales; las pruebas de autenticación y asignaciones de la suite completa
comprueban CSRF. Se conserva la protección de sesión sin cambios.

La ejecución completa inicial añadió un fallo documental a los tres previos:
`test_documentos_publicados_validan_con_openapi_generado` detectó que faltaba
publicar `DashboardConveniosResponse` en `docs/openapi.json`. Se corrigió el
artefacto añadiendo únicamente un path y dos esquemas, sin cambiar la prueba ni
los contratos existentes. Su control pasó; se reconstruyó la base desechable
con los mismos fixtures para repetir toda la suite. La evidencia inicial se
conserva en `full-suite-initial.xml`.

Los tres casos globales previos a F04 siguen registrados:

| Caso | Prerrequisito / diferencia de fixture |
| --- | --- |
| `test_facetas_respetan_naturaleza_sin_depender_de_pagina` | Espera `Entidad sintética A`; el catálogo real conserva `Aguascalientes` |
| `test_018_backfill_specific_record_from_017_transition` | Requiere históricos 017→018 con `sin_clasificar`; los tests crean causas válidas `termino_periodo` |
| `test_dataset_excludes_actual_additional_ran_identities` | Espera exactamente 51 identidades históricas adicionales; la base pública más los tests tiene 19 sintéticas |

No se renombraron entidades reales ni se inventaron históricos para aprobarlos.
Las 27 omisiones de referencia son 23 guardas de linaje/ledger, dos backfills
DDL, una sincronización RAN y una condición de administrador único. No se
habilitan esas guardas. Los dos antiguos fallos de tamaño del catálogo RAN que
ya pasaban en F03 siguen pasando con el catálogo público nacional.
Se repitieron los tres casos fallidos montando en lectura reporting.py y
schemas.py originales de `cbc78d0` en un worker desechable, con el resto de la
aplicación previa intacto. Fallan los mismos casos por los mismos motivos.
No hay regresiones funcionales nuevas observadas; **la suite global sigue sin
estar en verde** por esos prerrequisitos históricos/nombres de fixture.

Todos los paths/métodos previos y sus esquemas en OpenAPI son iguales al archivo
capturado antes de F04. Solo se añade un path y dos DTO. Las funciones previas
de reporting, modelos, access.py, domain.py, APIs de núcleos, HTML, auth.js y
proteccion.js permanecen idénticas a `cbc78d0`. No hay cambios a F01–F03.

## Entorno, reproducción y evidencias

Instancia nueva `ssalfer-f04-20261019`, Compose de pruebas existente
`backend/tests/convenio_report_compose.yml`, PostgreSQL 15.4 / PostGIS 3.3.4,
`software_pa_test`, cluster `convenio-report-disposable`, tmpfs, red interna
sin puertos publicados ni volumen de datos persistente. Credenciales/usuarios
exclusivamente sintéticos; worker con backend montado en lectura.

Preparación desde esquema **local de pruebas** y ledger 001–029 verificando
checksums, sin ejecutar migraciones ni copiar usuarios/datos funcionales;
catálogos estáticos sanitizados y fixtures versionados de 32 entidades,
2,478 municipios y 32,278 núcleos públicos RAN para repetir F03. Se validó el
manifiesto RAN y sus bytes, con las mismas huellas y limitaciones que F03.
El escenario operativo F04 se crea aparte dentro del rollback de tests.

Evidencia persistente local:
`/home/alfredo/proyectos/Software-PA/.worktrees/ssalfer-f04-evidence`.
Incluye preparador con guardas, baseline, OpenAPI anterior, fuente JS anterior,
mediciones, matrices de celdas, revisión estática y XML JUnit. No contiene
credenciales/cookies productivas. Versiones de backend iguales a F03; Node
22.23.2 y ExcelJS 4.4.0 ya estaban disponibles, sin instalar dependencias.

Con la instancia desechable preparada y el catálogo público cargado:

```bash
docker compose -p ssalfer-f04-20261019 -f backend/tests/convenio_report_compose.yml run --rm -T --no-deps worker python -m pytest -p no:cacheprovider tests/test_dashboard_summary_performance.py -q
node --test tests/frontend-ssalfer/dashboard-performance.cjs
docker compose -p ssalfer-f04-20261019 -f backend/tests/convenio_report_compose.yml run --rm -T --no-deps worker python -m pytest -p no:cacheprovider tests/test_projects_read_performance.py tests/test_access_context_performance.py tests/test_territorial_catalog_performance.py -q
```

`F04_EVIDENCE_DIR` opcional escribe muestras en un directorio escribible montado;
`F04_BASELINE_OPENAPI` activa la comparación con el OpenAPI anterior. Para la
suite completa se montan los paquetes locales JSON Schema en lectura como en
F03, sin habilitar guardas de migración/linaje. La referencia JS lee `cbc78d0`
con Git; en un sandbox que no permita subprocesos Node requiere la aprobación
de ejecución local que se usó durante estas pruebas.

## Archivos, commits, límites y reversión

- `backend/app/services/dashboard_summary.py`: selección acotada, deduplicación y conteos por conjunto.
- `backend/app/routers/reporting.py`: únicamente el endpoint aditivo y su import.
- `backend/app/schemas.py`: dos esquemas nuevos, sin alterar los previos.
- `docs/openapi.json`: publica únicamente el path y los dos esquemas nuevos.
- `frontend-ssalfer/js/dashboard.js`: Promise inicial compartida, paralelo acotado y consumo del resumen.
- `frontend-ssalfer/js/api/reportes.js`: método nuevo compatible.
- `frontend-ssalfer/js/utils/dashboardExcel.js`: conserva orden de proyectos antes de habilitar exportación.
- `backend/tests/test_dashboard_summary_performance.py` y `tests/frontend-ssalfer/dashboard-performance.cjs`: regresiones/referencias y mediciones.
- Este informe y `FASE_04_MEDICIONES.json`.

Commits independientes posteriores a F03:

- `b3d992b`: backend y contrato nuevo.
- `912a967`: integración frontend.
- Commit final de pruebas/documentación: `test: valida F04 y documenta resultados y limites`.
  Su hash se informa al cierre y se consulta con `git log -1` en esta rama.
  El último commit de código de aplicación validado es `912a967`; no se cambió
  código después de las pruebas. Este cierre incluye también `docs/openapi.json`.

Reversión completa: revertir el commit de pruebas/documentación, después la
integración frontend `912a967`, que vuelve a los endpoints anteriores conservados,
y finalmente `b3d992b` para retirar el path/DTO/servicio nuevo. F01–F03
se conservan; no hay migración ni datos persistentes que revertir. Una eventual
integración autorizada debe incorporar backend antes del frontend; no se ha
publicado ningún cambio. No hay caché sensible que invalidar.

Límites: persiste el truncamiento original a 100 núcleos/500 KPI y el defecto
previo Excel/tipo nulo; permanecen el coste de vistas KPI/valores y las librerías
de exportación cargadas al inicio. No se optimizan esos criterios ni F05/mapas,
F06/reportes, GIS, infraestructura o frontend React. Ampliar el universo,
eliminar la protección BFCache o cambiar la frescura requiere decisión aparte.

Producción permanece intacta: sin modificaciones de servidor/contenedores/base,
reinicios, migraciones, push, merge o deploy. La ejecución se detiene después
de F04; F05 queda pendiente de autorización.

Al cierre se retiraron únicamente el contenedor, tmpfs y red de
`ssalfer-f04-20261019` mediante `docker compose ... down -v`. La evidencia
permanece en el directorio persistente indicado; ningún servicio persistente
fue detenido o reiniciado.
