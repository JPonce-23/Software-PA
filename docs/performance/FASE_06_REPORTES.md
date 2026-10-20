# F06 — Reportes y resolución de referencias

> Integración 2026-10-20: alcance vigente y validación conjunta en
> [SSALFER_INTEGRACION_20261020.md](../integration/SSALFER_INTEGRACION_20261020.md).
> Las mediciones y el entorno descritos abajo corresponden a la fase original.

Implementación local sobre `41d4b68acc04356b3d5fcfcc10a6998251c32abb`.
Commit final de implementación/pruebas: `f16ec94b9ff3d28079e377131fc866251743cf4e`
(más el commit documental de cierre indicado al final).
**Validada localmente para los módulos intervenidos, sin regresiones nuevas.**
Cierre: 20 de octubre de 2026. Incluye referencias a convenios de seguimiento;
los demás tipos polimórficos conservan sus resolvedores y las limitaciones
de certificación indicadas abajo.

## Entorno y alcance

Rama `perf/ssalfer-optimizacion-fase1`, worktree persistente independiente:
`/home/alfredo/proyectos/Software-PA/.worktrees/ssalfer-optimizacion-fase1`.
Equipo local `Cooper`. Estado inicial limpio, sin modificaciones ajenas;
se comprobó que los commits F01–F04 son ancestros de la base F05 indicada.
El checkout original permanece en `feature/backend-logica`, separado del worktree.
No se utilizó SSH ni se consultó producción en F06. El despliegue/commit/base
mencionados en la auditoría del 19-oct-2026 se tratan como antecedentes históricos,
sin atribuirles una verificación actual ni usar sus tiempos como baseline local.
Se revisaron el hallazgo F06, su matriz de pantallas y las fuentes públicas reales.

PostgreSQL/PostGIS aislado: proyecto Compose `ssalfer-f06-20261020`,
`backend/tests/convenio_report_compose.yml`, DB `software_pa_test`, cluster
`convenio-report-disposable`, tmpfs, red interna y sin puertos publicados.
Worker en `APP_ENV=test`, credenciales sintéticas, código/docs en lectura.
Esquema restaurado desde el entorno **local de pruebas**, cuyo ledger 001–029
se verificó contra los checksums del worktree; sin ejecutar migraciones ni
copiar usuarios/datos operativos. Catálogos sanitizados y fixture público:
32 entidades, 2,478 municipios, 32,278 núcleos RAN. CSV SHA-256
`863d31fff0f9b0338a103c7858872d4f531fe2b2593aade514dac2233d2fa6c3`.
Los escenarios operativos se crean dentro del rollback de cada módulo.
No se usan credenciales productivas ni datos operativos de producción.

Se intervienen reportes y referencias de cinco pantallas: reportes colectivos,
el reporte integrado en derechos colectivos, pestañas anteriores de convenios,
estado financiero y las referencias a convenios de seguimiento. El reporte
general de convenios conserva su implementación. Los demás tipos de seguimiento
no utilizan el resolvedor de convenios.

## Mapa de pantallas, dependencias y prioridades

| Pantalla / archivo | Lecturas y problema verificado | Decisión F06 |
| --- | --- | --- |
| `reportesColectivos.html`, `utils/reporteColectivo.js` | Proyectos, primera página de núcleos, reporte base y filtrado; asambleas/afectaciones por núcleo y convenios por afectación para etiquetas | Reemplazar el recorrido de referencias por un lote escalar; conservar ambas consultas de datos y filtros |
| `derechosColectivos.html` | Reutiliza el reporte anterior, aunque abra con un núcleo; detalles de afectación ya diferidos | Optimizar el reporte compartido; conservar detalles, representación, pagos y exportación completa |
| `reportesConvenios.js`, pestañas anteriores | PN y afectaciones por núcleo, convenio por ID; `Promise.allSettled` sin límite | Lotes de referencias con concurrencia máxima 3 y filtros contextuales de un núcleo en una petición |
| `estadoFinanciero.js` | Dos lecturas iniciales de valores declarados y una petición por convenio para etiquetas | Compartir una Promise inicial y resolver referencias por lotes |
| Reporte general de convenios | Proyecciones, lotes, paginación, completo limitado y fechas RAN históricas existentes | Conservar backend, frontend y XLSX sin refactorización |
| Actividades por periodo / FIFONAFE | Reportes planos con pocas solicitudes por consulta; catálogo territorial ya tratado por F03 | Conservar consultas, cálculos y paginación existentes |
| `seguimiento.js` | Memoiza consultas, pero para convenios recorre afectaciones hasta encontrar todos los eventos; una etiqueta compartida depende del punto de parada | Lote específico de vínculos sin deduplicar; mantener padres completos, formato y parada originales. Otros tipos no refactorizados |

Prioridad: recorridos confirmados por registro, sin modificar modelos, vistas,
migraciones, políticas de seguridad ni criterios de reportes. No se reescriben
KPI ni se sustituye el reporte general por agregados con otros significados.

## Backend: tres contratos aditivos

`GET /api/reportes/referencias` acepta listas repetidas `id_proyecto_nucleo`,
`id_afectacion`, `id_convenio`, IDs positivos y **máximo 200 IDs totales** por lote.
`incluir_afectaciones=true` obtiene las afectaciones activas de los núcleos
pedidos, como el listado original, sin enviar un ID por cada afectación.

Devuelve tres listas, también vacías: `nucleos`, `afectaciones`, `convenios`.
Cada familia solicitada usa una consulta escalar, con autorización incorporada
en SQL: registro activo, PN activo y proyecto activo. Solo operador requiere
asignación activa; visualizador y geógrafo consultan todo proyecto activo.
Los IDs ajenos, inactivos o inexistentes se omiten sin distinguir sus motivos.
No se consultan directorios territoriales globales para completar nombres.

`GET /api/reportes/referencias-contexto` acepta de 1 a 100 IDs PN positivos.
Devuelve núcleos legibles, afectaciones, convenios y asambleas activos mediante
**4 consultas**: raíces autorizadas, afectaciones, convenios y asambleas.
Sin raíces legibles: una consulta y listas vacías. Se reutilizan las raíces
únicamente durante esa petición. No hay una consulta por núcleo o convenio;
no se pagina ni trunca la colección de hijos.

`GET /api/proyecto-nucleo/{id}/reportes/referencias-convenios` usa primero
`require_project_nucleus_access(load_details=False)` y después una consulta
escalar de vínculos A→C activos, ordenados por afectación y convenio. No deduplica:
seguimiento necesita conservar todos los pares para reproducir su parada.
Incluye `fecha_programada_firma`, usada cuando falta la firma. La membresía
sigue el vínculo de afectación, exactamente como el listado anterior.
Total admin: **2 SQL de autorización + 1 funcional, 2 objetos de contexto**;
la proyección funcional carga 0 objetos ORM. No se sustituye la lectura completa
de padres usada también por formularios. PN inexistente/inactivo responde 404;
proyecto inactivo/ajeno o permiso revocado conserva la decisión 403 del helper.

Las proyecciones contienen solo entradas usadas por las etiquetas/modal:

| Familia | Campos |
| --- | --- |
| Núcleo en proyecto | ID PN y nombre |
| Afectación | ID, PN, tipo, situación y superficie afectada Decimal/null |
| Convenio | ID, PN, tipo nullable, consecutivo, ámbito, descripción de instrumento y fecha de firma nullable |
| Asamblea | ID, PN y propósito nullable |
| Convenio contextual | `item` anterior e ID de su afectación de referencia |

El contexto reproduce un detalle significativo de `contexto.js`: al recorrer
las afectaciones en orden ascendente, su Map conserva la primera posición del
convenio, pero la etiqueta de la **última** afectación activa que lo contiene.
SQL usa `ROW_NUMBER` descendente por afectación y `MIN(id_afectacion)` para
preservar esa posición inicial. No se elige silenciosamente el vínculo principal.
Se comprueban la relación N:M activa y las bajas; no se duplican convenios.

Los cuatro roles usan el mismo `RoleChecker` existente. La autorización escalar
es equivalente a los getters/listados anteriores. Se conserva incluso la
lectura de un PN activo cuyo núcleo global esté inactivo, cuando el getter
anterior la permite; no se incorpora una regla de actividad nueva.

Los contratos nuevos responden `401` ante sesión inválida/usuario inactivo,
`403` ante rol no autorizado y `422` ante parámetros/límites inválidos.
Un lote autenticado puede responder `200` parcial: omite referencias no legibles.
Los endpoints individuales conservan sus `403`/`404` y JSON originales.
El consumidor colectivo exige que estén disponibles todas las raíces pedidas;
si falta alguna, conserva el error y deshabilita exportación. En referencias
opcionales se mantienen las etiquetas de respaldo y los datos del reporte.

Los **142 paths y todos los esquemas anteriores** de OpenAPI permanecen iguales;
solo se agregan tres paths y nueve DTO. Los 18 métodos previos de reporting y
las 203 definiciones previas de esquemas conservan su AST. `models.py`,
`services/access.py` y `services/convenio_reports.py` conservan sus bytes.
Los dos lotes generales cargan **0 objetos ORM**; el contexto de seguimiento
carga los dos objetos de autorización indicados. Serializar los DTO no ejecuta SQL.
No se crea caché de autorización ni de referencias entre peticiones en backend.

## Frontend: lotes, reutilización y respuestas tardías

`ReportesAPI.obtenerReferenciasReporte` deduplica IDs por familia y divide en
lotes de 100, con hasta tres peticiones simultáneas. Si un lote falla, conserva
las referencias disponibles de los demás y marca `incompletas`. No conserva
resultados entre invocaciones. `obtenerReferenciasContexto` sirve al reporte
colectivo y a los filtros contextuales de un núcleo.

El reporte colectivo mantiene la primera página original de **100 PN** de
`NucleosAPI.listarPorProyecto`; no amplía su universo ni sus opciones.
Construye índices por PN y afectación una sola vez, en lugar de volver a
filtrar toda la respuesta para cada núcleo. Las etiquetas usan exactamente los
formatters y reglas anteriores, incluidos superficie, propósito, consecutivo,
firma y prefijo de núcleo. El modal conserva los campos que mostraba.
Aunque derechos colectivos abra con un PN seleccionado, se conserva el
universo del selector de proyecto; se elimina su fanout, sin retirar opciones.
Los registros del reporte base fuera de esa primera página mantienen los
respaldos de referencia anteriores; no se corrige silenciosamente ese límite.

Las pestañas antiguas de convenios mantienen su caché de etiquetas del documento
ya existente. Las referencias nuevas se publican juntas solo si la consulta
sigue vigente. Cambiar filtros durante una consulta invalida la respuesta
pendiente y permite consultar de nuevo, sin que el resultado viejo sobrescriba
el nuevo. No se consulta automáticamente por cambiar un filtro ni se modifica
el controlador independiente del reporte general.

Estado financiero comparte **una Promise de valores declarados durante la carga
inicial**, consumida por KPI y tabla. Sus cálculos y formato quedan intactos.
El KPI sigue pidiéndose globalmente y filtrándose en cliente: imponer el filtro
servidor cambiaría el universo original de las primeras 500 filas.
La exportación CSV conserva su URL y consulta al descargar; no usa la Promise
inicial ni cambia a una instantánea almacenada. Los fallos de referencias
mantienen `Convenio · Referencia no disponible`, con los importes presentes.

Seguimiento conserva la lectura completa y memoizada de afectaciones. Para
etiquetas de convenios solicita los pares una vez, los indexa por afectación y
recorre los padres en el mismo orden **hasta encontrar todos los IDs de eventos**.
Un convenio compartido puede mantener la primera etiqueta o la última visitada,
según dónde se complete esa búsqueda; no se reutiliza la deduplicación global
del contexto colectivo. Solo memoiza hijos efectivamente visitados, como antes.
Se reutilizan sin cambios los formateadores: superficie afectada o preliminar,
redondeo original, tipo nullable y fecha de firma o programada.
Si falla el lote, se ejecuta el recorrido anterior y conserva resultados parciales
y aviso de error. Una generación anterior no publica etiquetas ni borra la
Promise de una generación nueva al fallar. Las otras 40 funciones de seguimiento,
incluidos formularios y escritura, conservan sus bytes.

## Equivalencia funcional y exportaciones

No se agregan importes en el resolvedor. Los datos financieros provienen de los
mismos endpoints; se conservan Decimal, nulos, fechas, superficies y orden.
El reporte colectivo mantiene `montoVisible` una sola vez por convenio entre
sus destinos. No se multiplica un monto por afectaciones o unidades agrarias.

Fixture operativo: cuatro proyectos, 108 núcleos más un vínculo compartido,
un proyecto de 105 PN, asambleas/convocatorias, 65 convenios, vínculos N:M,
dos destinos físicos y valores monetarios de precisión fija. El fixture adicional
de seguimiento agrega 50 afectaciones y 50 convenios con fecha programada,
sin modificar el dataset de los otros perfiles. Se comparan
versiones con los mismos datos en la misma transacción. Las pruebas verifican:

- Cuatro roles, proyectos asignados/no asignados, raíces compartidas, bajas de
  proyecto/PN/núcleo/afectación/convenio/vínculo y asignación revocada.
- Referencias inexistentes, tipo nulo, firma nula, orden contextual y última
  afectación de un convenio compartido; sesiones reales/inválidas y usuario inactivo.
- JSON de reportes colectivos, valores declarados, cobertura y general paginado/
  completo, y CSV financiero byte a byte antes/después de resolver referencias.
- Dos filas de destino con el mismo monto contractual `100.13`, sin sumarlo;
  general con más de una página y sin cambios de filtros o cálculos.
- HTML, opciones, estados y CSV colectivo **idénticos** entre JavaScript original
  y optimizado, con 0/3/74/105 núcleos, selección de PN, nulos y convenios compartidos.
- Celdas financieras y enlace CSV idénticos; 205 referencias, lotes con latencia,
  concurrencia máxima 3, fallos parciales, reintento y cambios rápidos de filtros.
- Seguimiento: pares y decisiones de acceso de los cuatro roles, proyecto ajeno,
  inactividad y revocación; en JavaScript hasta 150 afectaciones, referencias
  inexistentes, parada temprana/tardía, fallos parciales y generaciones solapadas.
- XLSX general real con SheetJS 0.20.3: generación y reapertura de ambas hojas,
  celdas, formato, fechas RAN históricas, nulos y decimales largos como texto exacto.
  El frontend general y sus exportadores conservan sus bytes.

El defecto anterior de **dashboard Excel con `tipo_convenio=null`** se conserva
y vuelve a identificarse en la regresión F04. No impide validar el CSV colectivo
ni el XLSX general, que tienen otros exportadores y sí admiten ese escenario.
No se cambian los resultados esperados de pruebas existentes.

## Mediciones

Se registró la línea base antes de modificar código de aplicación; fuentes
originales y OpenAPI de `41d4b68` conservados en la evidencia. Cinco muestras
alternadas por variante, mismos datos, sesión nueva por muestra y calentamiento
para el perfil directo. Se cuentan SELECT/WITH y objetos materializados;
se excluyen control de transacción, autenticación de sesión y recursos estáticos.
La autorización está incorporada en las consultas de las proyecciones nuevas;
los getters anteriores sí ejecutan sus contextos adicionales.

| Perfil directo (Python) | SQL consulta antes → después | ORM antes → después | SQL serialización antes → después | Bytes equivalentes | Mediana ms antes → después |
| --- | ---: | ---: | ---: | ---: | ---: |
| 65 convenios | 3,307 → 1 | 9,994 → 0 | 0 → 0 | 10,968 = 10,968 | 2590.932 → 1.575 |
| 3 PN | 62 → 4 | 169 → 0 | 0 → 0 | 13,410 = 13,410 | 41.512 → 8.134 |
| 105 PN, servicio directo | 1,476 → 4 | 741 → 0 | 0 → 0 | 20,433 = 20,433 | 951.268 → 10.691 |
| ID inexistente | 1 → 1 | 0 → 0 | 0 → 0 | 47 = 47 | 0.964 → 1.326 |

El caso de 105 PN invoca el servicio directamente en Python para comprobar
escalamiento; no representa una petición HTTP que exceda el límite de 100
raíces del contrato nuevo. Un cliente que necesitara 105 raíces usaría dos lotes.
El cliente colectivo actual conserva su página original de 100.

| Referencias HTTP reales (TestClient) | Peticiones | SQL | ORM | Bytes de respuesta acumulados | Mediana ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| 65 convenios | 65 → 1 | 3,307 → 1 | 9,994 → 0 | 73,789 → 10,966 | 5241.836 → 10.796 |
| ID inexistente | 1 → 1 | 1 → 1 | 0 → 0 | 35 → 47 | 7.852 → 8.560 |

Los bytes del perfil directo representan proyecciones equivalentes; los bytes
HTTP acumulan los cuerpos reales de los endpoints completos frente al lote.
Las referencias inexistentes no aceleran: ambas variantes requieren una consulta;
el nuevo contrato tiene una respuesta distinta documentada (listas vacías).

| Recorrido lógico de APIs por módulo, datos sintéticos | Peticiones | SQL | ORM | Bytes acumulados | Mediana ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reporte colectivo | 14 → 5 | 117 → 59 | 806 → 567 | 176,018 → 106,830 | 176.514 → 107.052 |
| Reporte integrado en derechos | 14 → 5 | 117 → 59 | 806 → 567 | 176,018 → 106,830 | 194.044 → 115.166 |
| Estado financiero, 63 convenios | 70 → 7 | 3,345 → 107 | 10,687 → 702 | 114,055 → 33,535 | 3754.469 → 728.050 |
| Referencias de convenios en seguimiento, 53 afectaciones | 54 → 2 | 380 → 12 | 562 → 175 | 164,435 → 60,990 | 536.699 → 24.878 |

El perfil de seguimiento fuerza el recorrido completo (un evento inexistente
mantiene pendientes), y mide solo las referencias de convenios, no la página
completa. La nueva ruta aislada tiene SQL de serialización **0**; los 175 objetos
del flujo incluyen las afectaciones completas y contextos que se conservan.
Con parada muy temprana el lote puede transferir más pares que el recorrido
anterior; es el coste de una solicitud constante por núcleo y se mantiene
acotado al PN autorizado. Los pares de padres no visitados no se renderizan ni se memoizan.
En fallo del lote el fallback conserva el fanout anterior, solo en ese caso.

Los recorridos de pantalla anteriores se reconstruyen desde el código original
y ejecutan peticiones **reales de TestClient en secuencia**, sin red TCP ni DOM.
No reproducen el paralelismo del navegador ni su tiempo de carga visual.
Incluyen los endpoints de datos y metadatos conservados, excluyendo sesión y
Aside. En derechos se mide el reporte integrado; representación, detalles y
pagos del contenedor no forman parte de ese perfil. Sus respuestas y
referencias necesarias se comparan completas antes/después. Se ejecutan como
benchmark explícito adicional, no como un HAR ni como estimación estática.

**Peticiones de funciones JavaScript reales con API/DOM simulados**, excluyendo
sesión, Aside, contenedor de derechos, estáticos y navegación; estos datasets
son distintos del perfil SQL:

| Módulo / fixture JS | Antes | Después |
| --- | ---: | ---: |
| Colectivo / derechos: 74 PN, 92 afectaciones | 244 | 5 |
| Colectivo / derechos: 105 PN, primera página 100 | 322 | 5 |
| Colectivo vacío | 4 | 4 |
| Estado financiero: 74 convenios | 81 | 7 |
| Estado financiero: 205 convenios | 212 | 9 |
| Estado financiero vacío | 7 | 6 |
| Referencias de pestañas antiguas: 205 PN/205 convenios + ID inexistente | 616 | 5 |
| Filtros de un PN con dos afectaciones | 3 | 1 |
| Referencias convenio de seguimiento: 53 afectaciones, parada al final | 54 | 2 |
| Seguimiento: 150 afectaciones, referencia inexistente | 151 | 2 |

No se eliminan las dos consultas de datos del reporte colectivo: una construye
opciones y otra consulta con los filtros finales. Tampoco se deduplica el Aside
con los módulos de contenido. No se presentan sus costes como eliminados.
No se midió RAM del proceso; los objetos ORM no equivalen a bytes de memoria.
Muestras completas en [FASE_06_MEDICIONES.json](FASE_06_MEDICIONES.json).

## Validación y regresiones

- **99 pruebas específicas F06 aprobadas**: 61 referencias/reportes y 38 seguimiento.
- **407 regresiones F01–F05 aprobadas** en la misma ejecución: F01 38,
  F02 173, F03 60, F04 56 y F05 80. También pasan las 43 pruebas existentes
  de mapa GIS/historia 026.
- **34 pruebas JavaScript aprobadas**: 16 F06 y 18 F04/F05, en 3.69 s.
- Suite completa final: **1,443 aprobadas, 3 fallidas preexistentes y 27
  omitidas**, 1,473 casos, 705.11 s de pytest (709.46 s del ejecutor), exit code `1`
  por esas tres aserciones, **cero errores pytest**. IDs de fallo y motivos de
  omisión coinciden automáticamente con F05 (`preexisting-comparison.json`).
- Perfil explícito adicional: **4 aprobadas en 50.47 s**: tres recorridos de
  pantalla y repetición del perfil directo para aislar la serialización.
  Estos perfiles preceden al agregado independiente de seguimiento; sus fuentes
  no se modificaron después de medirlos. Seguimiento agrega cinco muestras y
  **43 pruebas focalizadas aprobadas en 17.97 s** antes de la suite final.
  Los 15 archivos de aplicación, contratos y pruebas mantienen el hash registrado
  al iniciar esa suite; solo se completa documentación después de ejecutarla.

| Fallo previo conservado | Causa reproducida |
| --- | --- |
| `test_facetas_respetan_naturaleza_sin_depender_de_pagina` | Espera nombre sintético; el fixture INEGI contiene `Aguascalientes`. |
| `test_018_backfill_specific_record_from_017_transition` | Espera `sin_clasificar` de una transición histórica; las filas actuales contienen `termino_periodo`. |
| `test_dataset_excludes_actual_additional_ran_identities` | Espera 51 identidades históricas adicionales; la suite genera 19. |

Omisiones: 23 comprobaciones de linaje con escritura de ledger, 2 backfills DDL
GIS, 1 reproducción RAN completa y 1 prerrequisito de administrador único.
No se habilitaron guardas de migración ni se fabricaron historiales para aprobarlas.
La advertencia Starlette/httpx es preexistente.

Durante el desarrollo, una comparación Node requería normalizar los prototipos
de arreglos procedentes de dos VM; se mantuvieron IDs y textos. Cuatro pruebas
nuevas de equivalencia general necesitaban conectar el fixture transaccional
con la sesión de lectura separada del reporte general, siguiendo sus propias
pruebas existentes. Se corrigió únicamente el harness y sus expectativas `200`,
montos y datos quedaron intactas. Los XML/TAP iniciales y corregidos se conservan.

No hay navegador instalado/disponible. Quedan pendientes pruebas visuales reales,
HAR, navegación inicial/enlace/Atrás/caché caliente, interacción de controles,
exportaciones desde navegador y tiempos visuales. La equivalencia JS/API/XLSX
no se presenta como certificación visual.

## Reproducción y evidencia local

La evidencia está en el directorio persistente hermano
`/home/alfredo/proyectos/Software-PA/.worktrees/ssalfer-f06-evidence`.
`prepare_database.py` restaura únicamente esquema/catalogos del entorno local
marcado de pruebas en el proyecto tmpfs dedicado y comprueba el ledger;
`run_full_suite.py` reconstruye solo ese proyecto y ejecuta pytest. Ninguno
se conecta por SSH. Son herramientas locales de preparación, no dependencias
de ejecución de la aplicación. No se deben apuntar a una base operativa.

Con esa base aislada preparada, desde el worktree se ejecutaron:

```sh
docker compose -p ssalfer-f06-20261020 -f backend/tests/convenio_report_compose.yml run --rm -T --no-deps worker python -m pytest -p no:cacheprovider tests/test_report_references_performance.py tests/test_tracking_report_references.py -q --tb=short
node --test tests/frontend-ssalfer/reports-performance.cjs tests/frontend-ssalfer/tracking-references-performance.cjs tests/frontend-ssalfer/map-performance.cjs tests/frontend-ssalfer/dashboard-performance.cjs
```

El perfil adicional opt-in es
`python -m pytest tests/benchmark_report_screens.py -q` dentro del mismo worker.
Para guardar métricas se monta el directorio de evidencia como `/evidence` y se
pasa `F06_EVIDENCE_DIR=/evidence`; pytest usa `--junitxml=/evidence/<nombre>.xml`.
La suite completa utiliza además los paquetes jsonschema/attrs locales montados
en lectura, como registra `run_full_suite.py`, sin instalar dependencias.
Evidencias principales: `full-suite.xml`, `full-suite-summary.json`,
`preexisting-comparison.json`, `frontend-final.tap`, `tracking-focused.xml`,
perfiles `*-comparison.json`/`*-http-flow.json`, `static-review.json`,
`docker-isolation.json` y `versions.json`. Las mediciones que acompañan este
informe son un resumen versionado de esos resultados; las trazas de desarrollo
no sustituyen la ejecución final.

## Pendientes e ideas no implementadas

- Otros tipos de seguimiento: personas/titulares, indemnizaciones y eventos
  RAN/FIFONAFE tienen resolvedores y permisos propios. Se conservan su memoización
  y los hijos embebidos; la proyección de convenios no debe sustituirlos.
- Límites previos de 100 PN y 500 KPI, universos de filtros y frescura de las dos
  lecturas colectivas: no se amplían ni unifican como una optimización técnica.
- Consultas de datos de reportes y sus contextos ORM constantes, vistas/KPI,
  paginación de reportes planos y listados comunes del Aside: no reescritos.
  Exigen baseline y equivalencia por operación antes de extender los cambios.
- Sin cambios de GIS, índices, infraestructura, importaciones ni fases nuevas.

Para certificación integral F01–F06 faltan: navegador real con los cuatro roles
y navegación/exportaciones; resolver con autorización el defecto Excel de tipo
nulo; preparar los antecedentes correctos para los tres fallos de fixtures y
los escenarios aislados para las 27 omisiones; y validar volumen operativo y
latencia con datos representativos autorizados. El catálogo público nacional
no sustituye historiales y convenios productivos. Los otros tipos
polimórficos de seguimiento quedan identificados como trabajo adicional;
esta fase sí optimiza sus referencias de convenios, sin atribuir cobertura
a los demás tipos.

## Archivos, commits y reversión

- `backend/app/services/report_references.py`: proyecciones y autorización por lote.
- `backend/app/routers/reporting.py`: tres rutas nuevas, sin editar métodos anteriores.
- `backend/app/schemas.py`, `docs/openapi.json`: contratos aditivos.
- `frontend-ssalfer/js/api/reportes.js`: clientes y concurrencia acotada.
- `utils/reporteColectivo.js`: etiquetas por lote y guardas de selección.
- `reportesConvenios.js`: referencias, filtros contextuales e invalidación de consultas.
- `estadoFinanciero.js`: Promise inicial compartida y referencias mínimas.
- `seguimiento.js`, `api/seguimiento.js`: pares por lote y generaciones de etiquetas.
- `backend/tests/test_report_references_performance.py`,
  `backend/tests/benchmark_report_screens.py`,
  `backend/tests/test_tracking_report_references.py`,
  `tests/frontend-ssalfer/reports-performance.cjs`,
  `tests/frontend-ssalfer/tracking-references-performance.cjs`: equivalencia y mediciones.
- Este informe y `FASE_06_MEDICIONES.json`.

Commits de aplicación: `d5b863d` (backend/contrato), `d3bd66d` (frontend).
Pruebas iniciales: `3f8fc86`. Seguimiento: `18d3b66` (backend),
`087217a` (frontend) y `f16ec94` (pruebas).
Commit final documental: `docs: registra validacion y limites de F06`.
Su hash se informa al cierre y se obtiene con `git log -1` en la rama;
el último código de aplicación es `087217a`; la suite final se ejecuta
sobre `f16ec94`, que añade sus pruebas sin modificar la aplicación.

Reversión: retirar documentación y los commits de pruebas; revertir `087217a`
y `18d3b66` para retirar seguimiento. Después `d3bd66d` para que el
frontend vuelva a los endpoints conservados y finalmente `d5b863d` para retirar
los contratos/servicio nuevos. F01–F05 permanecen. No requiere migraciones,
reversión de datos ni invalidar una caché nueva. Una futura integración deberá
incorporar backend antes del frontend; no se hizo push, merge ni deploy.

Al cierre se retiraron únicamente el contenedor DB, tmpfs y red de
`ssalfer-f06-20261020` mediante `docker compose ... down -v`. No quedan
contenedores, redes ni volúmenes etiquetados con ese proyecto. Los seis
contenedores persistentes que estaban en ejecución conservan sus IDs y siguen
en ejecución; el checkout original sigue limpio en `feature/backend-logica`,
HEAD `2183ab20091f977208912f101748d5ff10c3f735`. No se detuvieron ni reiniciaron
servicios persistentes. Evidencia: `cleanup.json` y `final-state.json` en el
directorio persistente indicado.

Producción permanece intacta: sin SSH, escrituras productivas, reinicios,
migraciones productivas, push, merge ni despliegue. Esta ejecución se detiene
tras la entrega F06 descrita y requiere autorización para continuar.
