# F05 — Mapa e indicadores geográficos

F05 implementada localmente sobre `0ce1743aa351b3a69348342a8b15906d23f5b2cd`.
**F05 validada en el entorno aislado; F01–F04 continúan aprobadas, sin
regresiones nuevas.** Cierre local: 20 de octubre de 2026. Quedan pendientes
la comprobación visual en navegador y el defecto Excel anterior con
`tipo_convenio=null`. No se modifica producción ni se inicia F06.

## Entorno y antecedentes verificados

Rama `perf/ssalfer-optimizacion-fase1`, worktree persistente independiente:
`/home/alfredo/proyectos/Software-PA/.worktrees/ssalfer-optimizacion-fase1`.
Equipo local y daemon Docker: `Cooper`, contexto `default`, socket local.
Git estaba limpio al comenzar; `630f7dd`, `f98586e`, `6e622ff` y `cbc78d0`
son ancestros de `0ce1743`, que contiene F01–F04. El checkout original
permanece en `feature/backend-logica`, separado del worktree de rendimiento.
Los montajes del backend persistente apuntan al checkout original, no a este
worktree; se comprobó que ningún contenedor persistente monta el worktree ni
un directorio que lo contenga. No se sobrescribieron modificaciones ajenas.

La auditoría integral del 19-oct-2026 se leyó en la fase anterior y se revisó
el hallazgo F05 y sus límites. Sus 246 peticiones estimadas y sus referencias
a `630f7dd`, `db_integracion_mq_qa` y migraciones 001–029 son antecedentes
históricos; **no se presentan como una nueva verificación del despliegue**.
No se utilizó SSH ni se consultó producción durante F05. La base local de
pruebas verificó las 29 entradas de su propio ledger y sus checksums contra
los archivos del worktree antes de restaurar el esquema.

Proyecto Docker exclusivo `ssalfer-f05-20261020`, con Compose existente
`backend/tests/convenio_report_compose.yml`: PostgreSQL/PostGIS desechable,
`software_pa_test`, cluster `convenio-report-disposable`, almacenamiento tmpfs,
red interna y sin puertos publicados. Worker con `APP_ENV=test`, credenciales
sintéticas exclusivas y código/docs montados en lectura. Se restauró solo DDL
y catálogos sanitizados del entorno local de pruebas, sin usuarios ni datos
operativos copiados y **sin ejecutar migraciones**. No se usaron credenciales
productivas. Los datos operativos de cada módulo están contenidos en rollback.

Versiones verificadas: Python 3.11.17, FastAPI 0.138.2, SQLAlchemy 2.0.51,
Pydantic 2.13.4, pytest 9.1.1, PostgreSQL 15.4 y PostGIS 3.3.4; Node 22.23.2.
No se instalaron dependencias.

Se cargó el fixture versionado público de 32 entidades, 2,478 municipios y
32,278 núcleos RAN, con manifiesto y bytes verificados. SHA-256 del CSV:
`863d31fff0f9b0338a103c7858872d4f531fe2b2593aade514dac2233d2fa6c3`.
Esto permite repetir F03; no reproduce convenios, asambleas ni geometrías de
producción. Los escenarios operativos F05 son sintéticos, con los mismos datos
en ambas versiones. No se afirma validar la escala espacial nacional.

## Dependencias y reglas originales

`mapa.js` obtiene GeoJSON y todos los núcleos mediante páginas de 200; después
consultaba un catálogo y, por núcleo, asambleas y afectaciones; por afectación,
convenios. Estos últimos recorridos solo alimentaban cuatro indicadores.
Las capas y sus detalles usan GeoJSON, núcleos, parcelas, titulares y consultas
puntuales adicionales, conservadas. El resumen administrativo sigue usando
los núcleos para conteos, superficies y controles.

Las reglas del mapa difieren de F04 y se conservan expresamente:

- Universo completo de vínculos activos de `ProyectoNucleoResumen`, sin límite
  de 100 ni 200. No se añade un filtro de actividad del núcleo global o de sus
  padres territoriales que el listado original no aplicaba.
- Asamblea activa con **alguna** convocatoria activa, fecha de realización no
  nula y resultado perteneciente al catálogo activo `resultado_convocatoria`,
  código exacto `celebrada`. Se cuenta una vez por ID, sin depender del texto
  `asamblea.resultado`, del ordinal más reciente ni de la fecha actual.
- Si no existe esa opción activa del catálogo, el indicador muestra
  `No disponible`, incluso en un proyecto vacío; los convenios siguen disponibles.
- Solo convenios activos con fecha de firma no nula, accesibles por afectaciones
  activas y relaciones N:M activas del universo anterior. Deduplicación por
  `id_convenio` antes de contar ámbitos individuales/colectivos. Firmados es la
  suma de esos dos ámbitos, sin filtros nuevos de tipo de instrumento o de COP.
- No se suman montos ni superficies, no se sustituyen nulos y no se reutilizan
  KPI ni el servicio F04 con su página de 100. Un instrumento `otro` con tipo
  nulo y firma mantiene su ámbito y cuenta como antes.

El fixture respeta los triggers: un convenio puede vincularse a varias
afectaciones del mismo ProyectoNucleo/ámbito; no se deshabilitaron restricciones
para fabricar relaciones entre proyectos. Los núcleos compartidos entre
proyectos tienen contextos y datos operativos separados.

## Backend y contrato aditivo

Nuevo `GET /api/proyectos/{id_proyecto}/mapa/indicadores`:

1. Autenticación de sesión y `RoleChecker` con los cuatro roles existentes.
2. `require_project_access(..., load_details=False)` comprueba proyecto y
   asignación activos **antes de agregar datos**.
3. Una sentencia SQL con CTE de núcleos y resultado celebrado, conteo distinto
   de asambleas y subconsulta distinta de convenios firmados; `COUNT FILTER`
   sobre el conjunto deduplicado. No hay bucles de consultas ni entidades ORM
   funcionales. El único objeto ORM cargado es el contexto autorizado de proyecto.

Coste: **1 consulta de autorización + 1 funcional**, sin contar autenticación.
La cantidad de sentencias es constante; el trabajo de PostgreSQL depende del
número real de filas. No hay caché de permisos ni de indicadores entre peticiones.
No se editan modelos, relaciones, vistas, migraciones ni políticas de sesión.

| Campo | Tipo / significado |
| --- | --- |
| `asambleas_realizadas` | entero >= 0; null si falta el resultado activo celebrado |
| `convenios_individuales` | entero >= 0; convenios únicos activos firmados individuales |
| `convenios_colectivos` | entero >= 0; convenios únicos activos firmados colectivos |
| `convenios_firmados` | entero >= 0; suma de los dos ámbitos |

Sin filas: ceros, salvo la ausencia de catálogo indicada. Sesión inválida o
usuario inactivo: `401`; proyecto inexistente, inactivo, no asignado o asignación
revocada: `403`, según el contexto existente; ID no positivo/inválido: `422`.
Los `404` de recursos puntuales y todos los endpoints anteriores permanecen
intactos. El path y `MapaIndicadoresResponse` se publican en `docs/openapi.json`.
Las definiciones OpenAPI y JSON anteriores se comparan sin modificaciones.

## Frontend, concurrencia y errores

Solo se modifica `frontend-ssalfer/js/mapa.js`. `metricasProyecto` usa una petición
al resumen en lugar del recorrido. Valida enteros y nulos contractuales antes
de pintar; respuesta inválida o fallo de esa petición: `No disponible`, nunca
cero inventado. El nulo de asambleas mantiene disponibles los otros indicadores.
El resumen completo viaja en una respuesta; un fallo de transporte de esa
respuesta deja los cuatro indicadores no disponibles.

La petición comienza al seleccionar el proyecto, en paralelo con GeoJSON y
núcleos. No se espera para mostrar capas y tampoco espera al GeoJSON, al resumen
administrativo o a previsualizaciones GIS. Se reutiliza el token de selección
para descartar éxitos y errores tardíos. Un fallo geográfico o administrativo
no impide obtener los indicadores; un fallo del resumen no impide las capas.
Los estados `Consultando…` y `No disponible` se conservan.

Se eliminan las peticiones repetidas de convenios compartidos y el catálogo por
cada selección. La paginación administrativa, la caché en memoria de núcleos
ya existente y las consultas de detalle no se cambian. La carga común del Aside
y su listado de proyectos siguen separados del listado paginado del selector
del mapa; no se refactoriza `dashboard.js` ni se introduce caché persistente.

## Geometrías, capas y compatibilidad

`project_map` conserva íntegramente su AST, al igual que los otros 16 métodos
existentes de reporting y las 202 definiciones anteriores de esquemas. No se
cambia ninguna sentencia geográfica: ST_AsGeoJSON, CRS, coordenadas, precisión,
prioridad de geometría de proyecto sobre legado, vigencia, historial, trazos y
DDV conservan su código. Tampoco cambian superficies administrativas.

La función real `cargarMapaDeProyecto`, la paginación de núcleos y el resumen
administrativo conservan sus bytes. Las pruebas JS ejecutan el cargador real
con coordenadas de precisión alta y verifican que entrega el mismo objeto de
feature a la capa y descarta respuestas de otro proyecto. No se editan filtros,
simbología, popups, controles, Leaflet ni las previsualizaciones GIS.
Las pruebas API existentes verifican proyectos sin geometría publicada,
geometrías actuales/históricas, fallback, retirada, núcleos compartidos,
parcelas, DDV, trazos y ausencia de cambios en superficies administrativas.

## Mediciones reproducibles

Línea base registrada antes de modificar código de aplicación. Referencia JS
inmutable `0ce1743`; backend compara los endpoints originales conservados con
el nuevo resumen. Cinco muestras alternadas por variante tras calentamiento,
sesión SQLAlchemy nueva por muestra, mismo dataset y transacción. Eventos de
SQLAlchemy contabilizan sentencias SELECT/WITH y objetos materializados; se
excluyen instrucciones de control de transacción y autenticación. Los tiempos no
son garantías productivas ni tiempos de renderizado.

**Peticiones de indicadores: funciones reales ejecutadas en VM Node con API/DOM
simulados**, excluyendo sesión, listado de proyectos/núcleos, GeoJSON, teselas,
estáticos y clics de detalle:

| Núcleos / escenario JS | Antes | Después | Resultado exacto |
| --- | ---: | ---: | --- |
| 0 | 1 | 1 | 0 / 0 / 0 / 0 |
| 74 y 92 afectaciones | 241 | 1 | 37 / 0 / 1 / 1 |
| 105 | 334 | 1 | 53 / 0 / 1 / 1 |
| 205 | 634 | 1 | 103 / 0 / 1 / 1 |

Orden: asambleas / individuales / colectivos / firmados. La auditoría estimó
246 API totales con otros datos y código histórico: 241 de indicadores más 5
llamadas base. Sustituir solo ese componente daría **6 estimadas**, manteniendo
las demás llamadas de aquella hipótesis. No es una medición del navegador ni
un nuevo conteo total de la página actual; faltan HAR y navegación real.
Las peticiones administrativas todavía dependen de las páginas de núcleos.

**Backend directo: recorrido original y resumen**, sin autenticación. Antes
incluye recuperar el universo de núcleos para el recorrido; después la CTE lo
resuelve dentro del resumen. Objetos incluyen contexto de autorización.

| Dataset | SQL autorización antes → después | SQL funcional antes → después | ORM antes → después | Mediana ms antes → después |
| --- | ---: | ---: | ---: | ---: |
| 3 núcleos | 25 → 1 | 39 → 1 | 53 → 1 | 54.238 → 5.558 |
| 105 núcleos | 736 → 1 | 744 → 1 | 852 → 1 | 927.967 → 4.150 |
| Vacío | 1 → 1 | 3 → 1 | 6 → 1 | 9.337 → 5.721 |

**Flujo HTTP real en TestClient**, incluyendo el listado administrativo de
núcleos en **ambas** variantes, porque el mapa sigue necesitándolo. Se serializan
las respuestas completas originales y se calculan exactamente los mismos cuatro
valores. Excluye GeoJSON, sesión, red TCP, teselas y renderizado. La autenticación
se sustituye para medir; sesiones reales se prueban aparte.

| Dataset | Solicitudes antes → después | SQL total antes → después | ORM antes → después | Bytes JSON acumulados antes → después | Mediana ms antes → después |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3 núcleos | 12 → 2 | 64 → 4 | 64 → 5 | 18,155 → 3,390 | 102.587 → 19.656 |
| 105 núcleos | 317 → 2 | 1,480 → 4 | 958 → 107 | 185,262 → 115,287 | 2,740.966 → 30.888 |
| Vacío | 2 → 2 | 4 → 4 | 6 → 2 | 2,078 → 103 | 18.929 → 24.185 |

El caso vacío no reduce solicitudes/SQL en ese flujo y su mediana local aumenta;
no se afirma acelerar todos los escenarios. Las grandes respuestas de núcleos
permanecen. El resumen de cuatro valores ocupa 101 bytes en estos fixtures
no vacíos; no incluye cabeceras ni compresión. El JSON agregado derivado es
idéntico antes/después. Serializar el nuevo DTO ejecuta **0 consultas extra**.
No se midió memoria del proceso; los objetos ORM son un indicador independiente,
no una medida de bytes de RAM.

Muestras completas: [FASE_05_MEDICIONES.json](FASE_05_MEDICIONES.json).
Evidencia persistente adicional:
`/home/alfredo/proyectos/Software-PA/.worktrees/ssalfer-f05-evidence`, con
preparador, esquema, manifiesto, fuentes originales, OpenAPI antes/después,
mediciones, revisión AST y XML/TAP. No contiene datos ni secretos productivos.

## Pruebas y estado acumulado

- F05 backend: **80 aprobadas** en 43.72 s en la ejecución específica.
  Cuatro roles; asignados/no asignados, proyecto/vínculo/núcleo/afectación/
  convenio/relación activos e inactivos; revocación; recursos inexistentes;
  convocatorias múltiples, resultado y fecha nulos, catálogo inactivo;
  convenios firmados/no firmados/compartidos, tipo nulo; núcleo 105 con convenio
  firmado; sesiones reales, inválidas y usuario inactivo; JSON y contrato aditivo.
- JavaScript: **18 aprobadas**: 11 F05 y 7 F04. Incluye 0/74/105/205 núcleos,
  respuestas inválidas, fallos parciales, indicadores lentos, cambios rápidos
  de proyecto, descarte de errores tardíos y cargador geográfico real. F04 vuelve
  a verificar exportaciones y conserva explícitamente el defecto previo de tipo nulo.
- Regresiones F01–F04 y geometrías: **370 aprobadas** en 267.20 s.
  F01: 38; F02: 173; F03: 60; F04: 56; mapa GIS: 17; historia GIS 026: 26.
  F01–F04 conservan su comportamiento, incluidos permisos y exportaciones.
- Suite completa: **1,344 aprobadas, 3 fallidas preexistentes y 27 omitidas**,
  1,374 casos, 945.89 s. Exit code pytest `1`, sin errores de colección/ejecución.
  Son exactamente las tres identidades de fallo y los mismos motivos de omisión
  del XML de F04; comparación automática en `preexisting-comparison.json`.

Fallos previos conservados, sin cambiar esperados:

| Prueba | Diferencia del entorno aislado |
| --- | --- |
| `test_convenio_general_report::test_facetas_respetan_naturaleza_sin_depender_de_pagina` | Espera `Entidad sintética A`; el fixture INEGI contiene `Aguascalientes`. |
| `test_schema_018_orv_persona_ciclo_vida::test_018_backfill_specific_record_from_017_transition` | Espera historia de transición 017→018 con `sin_clasificar`; las filas de prueba actuales contienen `termino_periodo`. |
| `test_sync_catalogo_ran::test_dataset_excludes_actual_additional_ran_identities` | Espera 51 identidades históricas adicionales; la suite sobre el fixture público genera 19. |

Omisiones: 23 comprobaciones de linaje con escritura de ledger; 2 backfills DDL
GIS; 1 reproducción RAN completa; 1 prerrequisito de administrador único. No se
activaron guardas ni se fabricaron antecedentes históricos para aprobarlas.
La advertencia de Starlette/httpx es preexistente.

Repetición en la instancia desechable preparada, con el catálogo público cargado:

```bash
docker compose -p ssalfer-f05-20261020 -f backend/tests/convenio_report_compose.yml run --rm -T --no-deps worker python -m pytest -p no:cacheprovider tests/test_map_indicators_performance.py -q
node --test tests/frontend-ssalfer/map-performance.cjs tests/frontend-ssalfer/dashboard-performance.cjs
```

`F05_EVIDENCE_DIR` opcional conserva muestras y activa comparación con el OpenAPI
generado anterior; requiere montar un directorio escribible con el baseline
antes de implementar. La prueba JS lee `0ce1743` mediante Git. El preparador y
el ejecutor de suite completa en el directorio de evidencia registran las
guardas, restauración sin migraciones y montajes locales JSON Schema en lectura.
No se habilitaron las guardas de pruebas de DDL/linaje/importación completa.

No hay navegador instalado ni MCP de navegador disponible: Chromium/Chrome/
Firefox ausentes y caché Playwright vacía. Quedan pendientes Leaflet visual,
controles, popups y navegación real inicial/enlace/Atrás/caché caliente, HAR y
tiempos de visualización. No se inventan resultados de esos controles.
El error Excel anterior `tipo_convenio=null` permanece registrado, sin corregir.

## Archivos, commits y reversión

- `backend/app/services/map_summary.py`: consultas escalares agrupadas.
- `backend/app/routers/reporting.py`: import y nuevo endpoint autorizado.
- `backend/app/schemas.py`: DTO aditivo del mapa.
- `docs/openapi.json`: únicamente path y esquema nuevos.
- `frontend-ssalfer/js/mapa.js`: consumo del resumen y arranque independiente.
- `backend/tests/test_map_indicators_performance.py` y
  `tests/frontend-ssalfer/map-performance.cjs`: referencias, regresiones y mediciones.
- Este informe y `FASE_05_MEDICIONES.json`.

Commits locales posteriores a F04:

1. `4f505df`: backend y OpenAPI, `perf: agrega indicadores agrupados y autorizados del mapa F05`.
2. `b265f21`: frontend, `perf: sustituye recorridos del mapa por resumen paralelo F05`.
3. `0d25fb3`: pruebas, `test: verifica equivalencia y rendimiento de indicadores del mapa F05`.
4. Commit final documental: `docs: registra validacion y limites de F05`.
   Su hash final se entrega al cierre y se obtiene con `git log -1` en esta rama;
   el último commit de aplicación probado es `b265f21`.

Para revertir: retirar primero el commit documental, después `0d25fb3` y
`b265f21` (el frontend recupera los endpoints anteriores conservados), y finalmente
`4f505df` (retira el resumen/DTO/contrato nuevos). F01–F04 permanecen. No hay
migración ni datos a revertir. Una futura integración autorizada debe disponer
del backend antes del frontend. No se realizó publicación alguna.

F05 no optimiza GeoJSON, las consultas puntuales de detalle, proyectos del Aside,
los procesos GIS, reportes generales ni infraestructura. No se añaden índices,
simplificación geométrica, caché de permisos o almacenamiento persistente sensible.
Sin cambios de producción, base `db_integracion_mq_qa`, servidor, contenedores
productivos, reinicios, migraciones, push, merge o deploy.

Al cierre se retiraron únicamente el contenedor, tmpfs y red de
`ssalfer-f05-20261020` mediante `docker compose ... down -v`. No se detuvo ni
reinició ningún servicio persistente. La evidencia queda en disco.
La ejecución se detiene en F05; F06 requiere autorización nueva.
