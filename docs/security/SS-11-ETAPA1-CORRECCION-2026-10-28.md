# SS-11 etapa 1 — Presupuestos de reportes y CSV por lotes

Fecha: 2026-10-28. Rama dev, HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff`, más correcciones locales previas SS-01/02/03/04/10.

## Resultado y alcance

**Corrección local parcial implementada, pendiente de QA integrada. SS-11 continúa abierto** para mapa, otros reportes, presupuesto SQL, concurrencia y cuotas integrales. Se protegen exclusivamente avance-periodo, resumen-actual y dashboard.csv. Los dos JSON mantienen el array completo; si exceden el presupuesto se responde 413, nunca se entrega una página parcial presentada como total. El CSV deja de materializar filas ORM y el documento completo en memoria: se prepara por lotes en un temporal privado acotado antes de responder.

Resultado final Python: **128 pruebas descubiertas, 125 aprobadas y 3 omitidas**. De ellas, 23 pruebas nuevas SS-11 aprobaron; las tres omitidas son comprobaciones nativas de SS-10 que requieren SQLAlchemy/psycopg2 ausentes. El contrato JS de ReportesAPI aprobó con VM local y mocks. También se ejecutó sin errores el archivo previo de regresión SS-01 (el runner Node informó una unidad de archivo aprobada). Ninguna de estas pruebas es una reproducción con navegador/PostgreSQL/PostGIS reales.

No se importó engine/app.database/app.main, leyó .env, instaló software, conectó a PostgreSQL ni se ejecutaron Docker, migraciones, escrituras de expedientes, commits/push/merge o despliegues. No se rediseña el mapa ni el pool/transacciones globales.

## Estado Git y preservación

Al inicio dev/HEAD coinciden con la referencia, con todas las correcciones locales anteriores sin integrar. Se tomaron hashes sin leer archivos .env y snapshot del router; antes de generar el patch se comprobó que únicamente cambiaron reporting.py y docker-compose.yml entre los archivos preexistentes. Las nuevas cuatro variables de reporte se añaden al anchor de entorno sin alterar las variables SS-03, flags SS-04 o configuración SS-10.

Comparación AST: sólo cambian tres funciones previas: reporte_avance_periodo, reporte_resumen_actual y export_dashboard. _dashboard_query y sus permisos quedan idénticos; todos los filtros de ambos reportes se conservan. project_map, las demás rutas y los servicios convenio_reports/dashboard_summary/report_references/map_summary permanecen intactos, al igual que frontend, autenticación, sesiones, auditoría, roles, esquema y migraciones. Se añaden helper de recursos, wrapper de respuesta CSV y pruebas.

## Inventario efectivo de endpoints examinados

Se inspeccionó todo el router reporting, modelos/esquemas/vistas de los reportes prioritarios, convenio_reports y servicios delegados, dependencias get_db y frontend API/consumidores. Los endpoints de esta tabla conservan los roles admin, operador, visualizador y geografo y el alcance existente; la política frontend no sustituye los checks del servidor. Los parámetros se mantienen, incluidas validaciones de fecha, IDs positivos y tamaños de página declarados.

En rutas get_db ordinarias, la sesión depende del ciclo de vida de FastAPI y puede retener transacción/conexión hasta su finalización; cerrar un Result no equivale a cerrar la sesión. El CSV es la excepción nueva explícita: cierra su sesión de lectura antes de devolver la respuesta. El reporte general conserva su dependencia específica con autenticación cerrada primero y snapshot read-only REPEATABLE READ. No se midieron tiempos o consumos reales.

| Endpoint | Autorización y parámetros | Universo, materialización y presupuesto | Consumidor / conexión |
|---|---|---|---|
| GET /api/reportes/referencias | IDs legibles. id_proyecto_nucleo, id_afectacion, id_convenio, incluir_afectaciones | 200 IDs totales; referencias filtradas por alcance. incluir_afectaciones puede cargar hijos de los PN. Sin bytes/deadline global. | api/reportes.js y reportes de seguimiento; get_db |
| GET /api/reportes/referencias-contexto | IDs legibles. id_proyecto_nucleo | 1–100 PN por solicitud; el contrato indica que no limita hijos. Proyección mínima, sin cuota de filas hijas. | api/reportes.js, reportes colectivos; get_db |
| GET /api/proyecto-nucleo/{id_proyecto_nucleo}/reportes/referencias-convenios | PN autorizado. id_proyecto_nucleo | Acceso al PN requerido; vínculos activos de afectación/convenio sin límite de filas. | api/seguimiento.js; get_db |
| GET /api/proyectos/{id_proyecto}/reportes/convenios/general | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, id_entidad, ambito, naturaleza, pagina, tamano_pagina | Snapshot read-only REPEATABLE READ; página 1..1000000, tamaño 1..500 por ámbito; hijos por cabecera sin cota de bytes. | generalConvenios/reporte general; auth cerrada antes de sesión dedicada |
| GET /api/proyectos/{id_proyecto}/reportes/convenios/general/entidades | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, ambito, naturaleza | Mismo alcance/snapshot; agrupa entidades/ámbito autorizados. Resultado territorial pequeño por naturaleza, sin cota de tiempo. | entidadesConvenios; sesión dedicada |
| GET /api/proyectos/{id_proyecto}/reportes/convenios/general/completo | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, id_entidad, ambito, naturaleza | Control existente: máximo 10000 cabeceras totales, 413 sin parcial. Detalles hijos pueden ampliar memoria; no es límite de todas las filas. | generalConvenios(completo); snapshot dedicado |
| GET /api/proyectos/{id_proyecto}/dashboard/convenios | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto | PN paginados a 100 en el bloque existente; otros detalles/convenios precargados no tienen una cota total equivalente. | api/reportes.js y dashboard; get_db |
| GET /api/proyectos/{id_proyecto}/dashboard/resumen | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto | Agregados COP de todos los PN activos; no sustituye detalle por una página. Resultado de totales reducido, SQL puede recorrer todo el proyecto. | dashboard/resumen; get_db |
| GET /api/proyectos/{id_proyecto}/dashboard/exportacion/nucleos | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, despues_de, limit, revision | Keyset después_de + límite 1..200; siguiente_id/revisión y 409 si cambia conjunto. Metadatos/cuenta/revisión comparten snapshot de consulta. | exportación dashboard; get_db |
| GET /api/proyectos/{id_proyecto}/dashboard/exportacion/convenios | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, despues_de, limit, revision | Keyset 1..200, convenios únicos por ID, revisión y total. Control existente efectivo de filas por página, no deadline global. | exportación dashboard; get_db |
| GET /api/proyectos/{id_proyecto}/mapa/indicadores | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto | Un agregado por PN activo de todo el proyecto; no geometría, sin límite de filas/bytes. | mapa Leaflet/resumen; get_db |
| GET /api/dashboard/kpi | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, anio, skip, limit | Control existente: skip >=0, limit 1..1000, default500; orden por PK proyecto/año/indicador. OFFSET profundo puede costar. | obtenerKpiDashboard; get_db |
| GET /api/reportes/avance-periodo | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, id_entidad, anio, mes, trimestre, indicador, ambito, tipo_cop_operativo, tipo_convenio, destino_superficie | Nuevo: proyección escalar, cursor fetchmany y límite+1; máximo10000 completo, 413 sin truncar. Sin presupuesto JSON por bytes o SQL. | reporteAvancePeriodo.js y estadoFinanciero.js; get_db |
| GET /api/reportes/resumen-actual | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, id_entidad, ambito, indicador, tipo_cop_operativo, destino_superficie | Nuevo: máximo10000 compartido entre vista y agregado vigente. Dos SELECT, sin nuevo snapshot transaccional; cursor cerrado al terminar cada uno. | obtenerResumenActual publicado sin filtros en helper; pruebas históricas; get_db |
| GET /api/reportes/convenios/valores-declarados | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, id_entidad, id_proyecto_nucleo, id_convenio, ambito, concepto, firma_acreditada | Vista de valores declarados, all() sin límite. No sumar ingenuamente valores de detalle a cabeceras. | api/reportes.js y reportes/dashboard; get_db |
| GET /api/reportes/convenios/impactos | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, id_entidad, id_proyecto_nucleo, id_convenio, id_afectacion, ambito, concepto, efecto, pendiente, firma_acreditada | Vista de impactos, all() sin cota; multiplicidad de afectaciones/unidades y conceptos. | api/reportes.js; get_db |
| GET /api/reportes/convenios/impactos-periodo | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, id_entidad, anio, mes, trimestre, ambito, tipo_cop_operativo, tipo_convenio, concepto, efecto | Impactos por periodo, all() sin cota; dimensiones temporal/territorial/concepto. | api/reportes.js; get_db |
| GET /api/reportes/convenios/cobertura-impactos | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, id_entidad, ambito, concepto | Cobertura por concepto/convenio, all() sin límite explícito. | api/reportes.js y benchmarks de reportes; get_db |
| GET /api/reportes/convenios/colectivos-destino | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, id_entidad, id_proyecto_nucleo, id_convenio, id_asamblea, tipo_convenio, tipo_cop_operativo, destino_superficie, anio, mes, trimestre | Mismo handler en ruta principal y alias oculto; all() sin cota por destino. No se modifica su desglose jurídico. | obtenerColectivosDestino y reportes; get_db |
| GET /api/reportes/convenios/destinos | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, id_entidad, id_proyecto_nucleo, id_convenio, id_asamblea, tipo_convenio, tipo_cop_operativo, destino_superficie, anio, mes, trimestre | Mismo handler en ruta principal y alias oculto; all() sin cota por destino. No se modifica su desglose jurídico. | obtenerColectivosDestino y reportes; get_db |
| GET /api/reportes/fifonafe/cobertura | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, ambito | Agregados proyecto/ámbito, all() sin límite explícito; cantidad de filas ligada a proyectos autorizados. | reportesFifonafe.js/api/reportes.js; get_db |
| GET /api/reportes/fifonafe/indicador-institucional | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, anio | Agregados proyecto/año, all() sin límite explícito; monto/cobertura no alterados. | reportesFifonafe.js/api/reportes.js; get_db |
| GET /api/exportaciones/dashboard.csv | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto, anio | Nuevo: una SELECT limitada con cursor por lotes; máximo10000 filas y16MiB CSV; archivo temporal antes de200, sesión cerrada antes de descargar. | dashboard, estadoFinanciero y URL pública del helper; archivo sin cursor durante streaming |
| GET /api/proyectos/{id_proyecto}/mapa | Proyecto autorizado o conjunto autorizado; cuatro roles de lectura. id_proyecto | Cuatro consultas .all(), ST_AsGeoJSON, json.loads y FeatureCollection completa. Sin cuotas de features/vértices/bytes/bbox/LOD. Intacto. | mapa.js, pruebas GIS/documentos; get_db |

Las vistas prioritarias agrupan dimensiones, no exponen un listado ilimitado de expedientes individuales por definición, pero el número de proyectos, años, meses y combinaciones puede crecer. El GROUP BY y orden pueden requerir recorrer/intermediar mucho más que las filas devueltas. Las filas de indicadores y cantidades/superficies/montos no se recalculan ni convierten a float. El control previo del reporte general limita **cabeceras**, no todos los hijos ni bytes; dashboard KPI ya estaba paginado y no se presenta como ilimitado.

## Estrategia de compatibilidad de los JSON

Se eligió **límite del conjunto completo**, no paginación nueva. SSALFER espera Array y calcula totales sobre el conjunto; convertir la respuesta en un envelope o devolver limit filas con 200 sería incompatible y podría mostrar montos incompletos. Se mantiene la estructura/campos de schemas.ReporteAvancePeriodoResponse y ReporteSnapshotActualResponse. Los nuevos 413 y el 504 opcional de CSV se documentan en OpenAPI con mensajes controlados.

Las consultas proyectan las columnas escalares de esos schemas en lugar de materializar instancias ORM con identidad/lazy loading. Session.execute recibe yield_per/stream_results/max_row_buffer, SQL LIMIT restante+1 y fetchmany acotado. Se comprueba el conteo **observado** antes de añadir cada fila. El Result se cierra en finally por éxito, exceso, error o cancelación; una excepción impide devolver la lista parcial.

Avance conserva proyecto/año/mes/indicador como orden principal y añade entidad, ámbito, COP, tipo de convenio y destino como desempates, con NULLS LAST en dimensiones opcionales. La identidad agregada de la vista/modelo comprende esas dimensiones; trimestre está determinado por mes. Resumen conserva proyecto/indicador/entidad y añade ámbito/COP/destino. El agregado vigente de expropiación directa mantiene joins, activos, condición y count(distinct PN) originales; usa el **presupuesto restante**, no otro límite independiente, antes de ordenar la unión.

No se introducen páginas externas ni cursors públicos en estos dos endpoints. Por tanto no se promete estabilidad entre páginas frente a mutaciones concurrentes; el ensayo de fronteras comprueba integridad entre lotes del mismo cursor. La segunda consulta de expropiación en resumen conserva el aislamiento previo de get_db: **no se convierte mágicamente en el mismo snapshot de la primera**. Obtener una vista atómica de ambas consultas requiere sesión transaccional de reporte validada en etapa 2.

Transición explícita: resultados dentro del límite siguen siendo arrays completos; el exceso ahora produce 413 y exige acotar filtros. api/reportes.js propaga el error, no devuelve los primeros N elementos. reporteAvancePeriodo/estadoFinanciero ya tratan fallos de API; se debe comprobar la presentación real del 413 en QA. obtenerResumenActual() no pasa filtros desde ese helper aunque el backend sí los admite: si un consumidor supera la cuota, se necesita una transición UI explícita para acotar universo o una API paginada nueva. No se modifica el helper para cambiar su contrato en esta etapa. El enlace directo CSV puede abrir el error JSON del servidor; no se inventa una experiencia de descarga ya validada en navegador.

## CSV: preparación por lotes y propiedad de recursos

1. Reutilizar _dashboard_query con los mismos permisos y filtros proyecto/año. Seleccionar ocho columnas originales y ordenar por la PK (proyecto, año, indicador).
2. Ejecutar **una sola SELECT** con LIMIT máximo+1. Usar cursor/Result en lotes, no repetir SELECT OFFSET para cada bloque. Esto evita que cada lote tome una consulta/snapshot diferente y elimina la lista ORM completa.
3. Preparar tempfile.TemporaryFile binario privado (0600 en la comprobación Linux), sin nombre cliente ni carpeta de importación. csv.writer serializa una fila cada vez en un StringIO reutilizado: getvalue corresponde a **una fila**, no al CSV completo. Cabecera, comillas, CRLF y UTF-8 cuentan en el presupuesto de bytes efectivo. Una cadena que ya exceda el presupuesto en caracteres se rechaza antes de copiarla para escape/CSV; el cálculo final usa bytes UTF-8 reales.
4. Ante filas/bytes/plazo excedidos, error IO o cancelación durante preparación, cerrar el archivo y rechazar antes de crear una respuesta 200. No truncar datos, omitir filas ni producir un CSV parcial con éxito.
5. Cerrar Result y **db.close() antes de construir/devolver la respuesta**. El endpoint sólo ha hecho lectura de negocio; no hay escrituras de exportación por confirmar. El cierre explícito es local a export_dashboard y el finally de get_db puede cerrarla de nuevo. El usuario/roles ya se han evaluado; no se usan objetos ORM en el stream.
6. DashboardCsvResponse mantiene Content-Disposition y tipo CSV; su iterator lee bloques de 64KiB del archivo. finally en __call__ cierra el archivo incluso si ASGI se cancela antes del primer next. El generador también tiene finally de cierre. Si falla la construcción de respuesta, cierre de cursor o cierre de sesión, el propietario anterior cierra el archivo antes de propagar el fallo.

La [documentación SQLAlchemy de streaming](https://docs.sqlalchemy.org/en/20/core/connections.html#streaming-with-a-fixed-buffer-via-yield-per) explica las opciones de buffer y el cierre de Result; aquí se proyectan columnas para evitar restricciones de eager loading/unique. Los [cursores PostgreSQL](https://www.postgresql.org/docs/15/sql-declare.html) permiten recuperar una consulta por bloques. Es el diseño esperado con el driver fijado, **no evidencia de un cursor PostgreSQL nativo ejecutado**: debe comprobarse su consumo/snapshot real en QA.

La [documentación FastAPI de dependencias y StreamingResponse](https://fastapi.tiangolo.com/advanced/advanced-dependencies/#dependencies-with-yield-and-streamingresponse-technical-details) muestra que la vida de dependencias yield tiene matices de versión/alcance. Esta implementación no necesita sesión ni cursor vivos durante el streaming; sólo un archivo propietario, y se prueba el orden de cierre con dobles. No se crea un segundo engine ni se modifica el pool.

Si el cliente abandona mientras la preparación síncrona está bloqueada en DB, el código no garantiza interrupción inmediata del SQL/thread. Los límites se comprueban cuando vuelve el control a Python. Después de preparar el archivo, una descarga lenta ya no retiene conexión; puede retener hasta el presupuesto de disco de esa operación. Cancelación ASGI real y carreras del adaptador sync-thread deben validarse con el framework en QA.

## Fórmulas CSV: alcance real

La columna de texto indicador procede de códigos de vistas SQL de hitos; en la ruta revisada no se confirma un campo libre controlado por usuarios HTTP que se convierta en fórmula. No se presenta CSV injection explotable como un hallazgo nuevo demostrado.

Se aplica defensa en la **representación exportada**: prefijo apóstrofo a strings que comienzan por =, +, -, @ y variantes full-width, o por tab/CR/LF, incluyendo espacios/BOM antes de un iniciador de fórmula. csv.writer mantiene el escape de separador/comillas. Los valores numéricos negativos, Decimal, None, acentos y texto normal mantienen su semántica; no se altera el registro ni el valor almacenado. Se prueba que una cadena fórmula permanece intacta en el objeto origen.

La guía [OWASP CSV Injection](https://community.owasp.org/attacks/CSV_Injection) advierte diferencias entre hojas de cálculo y riesgos al volver a guardar/abrir. El prefijo no es garantía universal para todos los locales, importadores, delimitadores inferidos o ciclos de reexportación. Debe validarse la apertura inicial con aplicaciones institucionales en QA; el CSV no es un formato lossless de reimportación de strings protegidos y esta diferencia se documenta explícitamente.

## Límites nuevos, unidades y fundamento

| Configuración / control | Predeterminado / unidad | Fundamento y alcance |
|---|---|---|
| REPORT_MAX_ROWS | 10000 filas | Política conservadora de conjunto completo, usando como referencia la magnitud del límite existente del reporte general. No es medición de capacidad del host. Compartido por ambos segmentos de resumen y por cada exportación independiente |
| REPORT_EXPORT_MAX_BYTES | 16777216 bytes =16MiB | Cuota administrativa de artefacto CSV por operación, contando cabecera/UTF-8/escape/CRLF. No limita todo JSON, RSS o disco global |
| REPORT_FETCH_BATCH_ROWS | 250 filas, configurable 1..1000 | Buffer moderado y acotado, compatible con el uso de lotes pequeños ya presente en el repositorio. No se atribuye throughput medido |
| Descarga de archivo | 65536 bytes =64KiB por chunk | Memoria de lectura de descarga independiente del tamaño del archivo; constante interna |
| REPORT_EXPORT_BUILD_TIMEOUT_SECONDS | Vacío: no activo. Si se fija, segundos positivos finitos | Control cooperativo antes/después de fetch y durante escritura. Se deja opt-in por falta de mediciones; no es statement_timeout ni cancela SQL bloqueado |
| SQL LIMIT | restante+1 / máximo+1 | Fila testigo para detectar exceso, siempre acompañada por rechazo explícito; jamás éxito truncado |

La configuración rechaza valores no positivos y batch>1000, así como NaN/inf/plazos inválidos. No existe 0=ilimitado. Las cuatro variables se exponen en Compose sin leer valores .env. La selección de filas/bytes es un presupuesto funcional inicial que debe calibrarse antes de integrar; los datasets versionados/fixtures inspeccionados son sintéticos (casos de indicadores y lotes pequeños, páginas 100/200/500) y no acreditan el volumen institucional. No se procesaron datasets de producción ni se inventa capacidad de RAM/CPU/disco.

La cuota por filas impide crecimiento indefinido del número de objetos leídos por estas rutas; **no garantiza una cota estricta de bytes por celda ni del JSON**. El driver ya ha construido cada valor al devolverlo y un campo grande puede ocupar memoria antes del chequeo CSV. Las vistas usan indicadores codificados y escalares, pero los límites de precisión/longitud y resultados intermedios deben verificarse en QA. El RSS incluye buffers de driver, una fila serializada, lote de datos y estructura de validación JSON; no es igual al tamaño del CSV.

## Presupuestos SQL y límites pendientes

| Mecanismo | Qué limita | Estado en esta entrega |
|---|---|---|
| statement_timeout | Duración de un statement en PostgreSQL | No se añade un valor sin medir; revisar por transacción de reporte en QA |
| lock_timeout | Espera por locks, no ejecución total | Pendiente, menor que el presupuesto de statement cuando se dimensione |
| Timeout HTTP/proxy | Espera/vida de transporte según componente | No prueba cancelación real de DB; configuración efectiva no inspeccionada |
| Plazo cooperativo de construcción | Tramos Python y tiempo observado tras fetch | Opt-in; no interrumpe una llamada de driver bloqueada |
| Deadline total de solicitud | Autenticación, SQL, staging, serialización, envío y cierre | Pendiente de diseño global, no equiparar al plazo anterior |
| work_mem/temp_file_limit | Memoria por operación SQL y temporales DB | Pendiente: work_mem se multiplica por nodos y paralelismo, no es cota RSS por petición |
| Concurrencia/cuota de archivos | Operaciones simultáneas por usuario/proyecto y total | Pendiente de coordinación compartida; no se introduce diccionario local como garantía global |
| Cancelación de query | Interrupción efectiva y rollback/recuperación de conexión | Pendiente de ensayo nativo; db.close tras retorno no es cancelación de un execute bloqueado |

Los [parámetros PostgreSQL 15](https://www.postgresql.org/docs/15/runtime-config-client.html) distinguen tiempo de statement y espera de locks. Una futura sesión dedicada de reportes puede aplicar SET LOCAL con valores obtenidos en QA y asegurar rollback/limpieza sin afectar otros módulos. No se modifica database.py, pool_size, overflow, isolation_level global, roles ni transacciones históricas. Los límites LIMIT/fetchmany no evitan sorts, GROUP BY o scans costosos antes del primer resultado.

## Mapa — diseño para SS-11 etapa 2, sin implementación

La implementación actual se conserva literalmente por AST. Entrega FeatureCollection con trazo_proyecto, derecho_via_proyecto vigente, nucleo_agrario y parcela. Cuatro consultas PostGIS materializan filas y ST_AsGeoJSON puede producir texto proporcional a vértices/dimensiones; luego json.loads y la lista final mantienen copias estructurales. Filtros de proyecto/activos/vigencia/fallback/historia son controles de integridad/alcance, no un presupuesto de resultado. SSALFER mapa.js carga la colección, crea capas/índices/tooltips y administra selección; hay dependencias de tipo e ID y previsualizaciones históricas que deben conservarse.

Diseño propuesto para revisar antes de codificar:

1. Conservar el endpoint actual hasta una transición explícita; crear un contrato versionado de **visualización** por bbox/zoom/LOD, con validación finita de coordenadas y extensión, índice espacial comprobado y filtros RBAC idénticos. No paginar silenciosamente la colección existente.
2. Mantener las cuatro categorías e IDs/procedencia/vigencia; indicar si el conjunto por viewport está completo y sus conteos por tipo. Si excede el presupuesto, rechazar o pedir más zoom, sin ocultar features bajo un 200 presentado como completo. Los totales institucionales siguen proviniendo de sus indicadores completos, no del viewport.
3. Separar geometría visual derivada de geometría oficial. Evaluar tolerancias/topología y metadatos de LOD; no escribir la simplificada, no usarla para áreas oficiales, conciliación, decisiones jurídicas o exportación canónica. No decidir una tolerancia sin corpus QA.
4. Coordinar la carga/cancelación de viewport y capa en Leaflet, revisiones del proyecto y selección estable por ID. Si se paginan features de visualización, usar keyset/revisión/snapshot o detectar cambios; acumular hasta completar el viewport y señalizar datos incompletos. No generar mosaicos automáticamente en esta etapa.
5. Para descarga oficial completa, diseñar trabajo/exportación autorizada con cuotas de filas/vértices/bytes/tiempo y recurso privado; conserva CRS/precisión/dimensiones fuente admitidas y metadatos oficiales. Se debe validar con PostGIS y navegador reales en entorno desechable.

El cambio a bbox/LOD requiere pruebas del plan/indexación, comparación geométrica y de superficies, UI/zoom/selección/tooltips e historial/vigencia, no sólo un test unitario de tamaño. No se introduce simplificación destructiva ni API de mosaicos aquí.

## Pruebas ejecutadas y alcance de evidencia

Se inspeccionaron conftest y suites de reportes antes de decidir ejecución. Las suites backend importan engine/aplicación y escriben en PostgreSQL; la de conexiones exige además un cluster QA identificado y ensaya pool real. No se ejecutó pytest ni collect-only; no hay BD QA desechable autorizada ni FastAPI/SQLAlchemy/driver instalados en el intérprete local.

```sh
python3 -B -m unittest discover -s tests/security -p 'test_*.py' -q
# Ran 128 tests; OK (skipped=3): 125 aprobadas
node tests/frontend-ssalfer/report-limits-contract.cjs
# arrays, filters, URLs and explicit failures OK
node --test --test-reporter=spec tests/frontend-ssalfer/map-tooltip-security.cjs
# exit 0; el runner informó 1 unidad de archivo aprobada
```

| Control | Prueba aislada / evidencia | Límite |
|---|---|---|
| Límites y configuración | Vacío/uno/exacto/exceso de filas, bytes UTF-8 exactos y máximo-1, batch inválido, deadline NaN/inf | Sin producción ni medición RSS real |
| Resultados completos | LIMIT+1, conteo observado y rechazo; dos segmentos resumen comparten presupuesto | Cursores/query simulados |
| Orden y lotes | Empates con NULL en dimensiones, orden repetible, 17 registros y batches1/2/7/17/250 sin pérdida/duplicados | No se añade API de páginas; collation nativa pendiente |
| Filtros/permisos | Filtros reales de router sobre dobles, acceso explícito 403 y conjunto autorizado implícito | RBAC real/SQL requieren QA; no se cambia política |
| Cantidad/superficie/monto | Decimals exactos, negativos, Unicode/comillas, overlay actual y totals de fixtures | No reproduce cálculo de vistas PostGIS/SQL reales |
| CSV | Una execute, proyección de columnas, sin all/fetchall del export, cabecera idéntica, header-only vacío y chunks64KiB | Configuración de server cursor declarada; driver real pendiente |
| Fórmulas | Prefijos ASCII/full-width/control/BOM; números negativos y fuente inmutables | Apertura en Excel/LibreOffice no ejecutada |
| Limpieza | Cursor cerrado ante error/cancel, temporal cerrado por filas/bytes/plazo/IO, fallo de cursor.close/db.close/constructor y cancel antes/mientras se envía | ASGI simulado; no carrera real de framework/thread/driver |
| Temporales | Archivo real sintético con modo0600 y cierre tras chunks | Sin cuota global ni fallo de sistema de archivos real |
| Frontend | VM carga api/reportes.js real y simula get: arrays, filtros, URLs y propagación413 | Sin DOM/browser ni pantalla de error real |
| Correcciones anteriores | 102 pruebas Python previas aprobadas, tres nativas previas omitidas; regresión local SS-01 ejecutada | SS-01 no equivale a validación de navegador pendiente |
| Preservación | Hashes y comparación AST: mapa, filtros, helper de permisos y demás funciones intactos | No acredita configuración desplegada |

Las pruebas nuevas extraen funciones/clase de respuesta del router por AST, omitiendo imports/decoradores de startup y usando dobles Query/Result/Session/StreamingResponse. La parte de archivo/CSV/configuración es real stdlib con datos sintéticos. No se presenta ese ensayo como una ejecución de FastAPI, SQLAlchemy ni PostgreSQL. Los errores simulados y resultados esperados no contienen datos institucionales.

Pruebas omitidas: contratos API/Pydantic nativos, compilación/ejecución SQL, repeatable-read, EXPLAIN/estadísticas, pg_stat_activity/cancelación, pool real, PostGIS/mapa, navegador real y hoja de cálculo. Las tres omisiones marcadas por unittest pertenecen a SS-10; las integradas SS-11 no se ejecutaron ni se inventa su resultado. No se instalaron herramientas para suplirlas.

## Criterios de aceptación para QA desechable

- Comparar array/campos/valores y totales con la versión previa en un corpus sintético representativo de proyectos, entidades, periodos, COP, ámbitos, destinos y casos con NULL. Verificar el indicador de expropiación vigente y escenarios positivos/negativos de acceso para cuatro roles.
- Confirmar tipos Row→Pydantic, Decimal/NULL y orden SQL nativo, incluida ausencia de duplicación por cambios ORM→proyección. Usar límites bajos de ensayo y valores exactos/exceso; 413 nunca trae una lista/CSV parcial con 200.
- Instrumentar driver/engine para demostrar un cursor y una SELECT de datos por CSV, batches acotados, conteos íntegros y snapshot consistente bajo escrituras concurrentes. La autorización y los filtros deben ejecutarse antes de exportar.
- Verificar la liberación real de Result/sesión/conexión antes de primer byte de descarga, pool incluso con tamaño de ensayo1, cliente lento, desconexión antes del cuerpo, durante el stream y durante la preparación. Cancelar SQL en QA y comprobar rollback/reutilización sin efectos institucionales.
- Medir RAM/CPU/disco, bytes por fila e intermedios SQL con corpus QA; definir statement_timeout/lock_timeout/work_mem/concurrencia/deadline total a partir de objetivos operativos. No confundir timeout de proxy con cancelación del servidor DB.
- Comprobar UX de 413/504 y enlace de descarga en SSALFER real; ningún panel muestra totales incompletos como definitivos. Si el universo habitual supera límites, diseñar filtros/paginación/exportación asíncrona de transición antes de integrar; no aumentar cuotas a ciegas ni truncar.
- Abrir CSV sintético en versiones/locales institucionales de hojas de cálculo, incluidos prefijos peligrosos, negativos, Unicode y comillas. Reexportación/reapertura fuera de garantía debe quedar documentada para usuarios.
- Comparar mapas/capas/IDs/CRS/áreas oficiales e historial/vigencia con regresiones existentes sin cambio de geometría; sólo después autorizar etapa2 de visualización. Validar presupuestos para los demás endpoints inventariados.

## Riesgos residuales y regresión

La nueva respuesta413 puede impedir cargar universos grandes en pantallas que no ofrecen todos los filtros; es deliberada, documentada y requiere calibración/UX en QA, no una aprobación de despliegue inmediato. El detalle de fórmulas modifica sólo strings peligrosos del CSV exportado y puede afectar reimportadores; nunca modifica datos originales. El resultado estándar y la precisión decimal se mantienen en los casos aislados comprobados.

Quedan sin cota integral: bytes del JSON, memoria por celda antes de llegar a Python, materialización intermedia de SQL, autorización que puede enumerar proyectos, otras rutas de detalle/reportes, geometrías/vértices/bytes del mapa y detalles hijos del reporte general. El spool limita cada archivo, pero varias solicitudes/clientes lentos pueden agotar disco/FD/CPU; hace falta cuota compartida y aislamiento/almacenamiento operativo verificados. Un plazo cooperativo no termina SQL bloqueado y no limita la descarga completa.

La consistencia propuesta para CSV depende del driver/cursor PostgreSQL real; debe contrastarse en QA. Resumen conserva dos consultas sin snapshot nuevo, con la ventana de consistencia previa entre ellas. No hay garantía nueva de estabilidad entre solicitudes paginadas de endpoints existentes. No se afirma que el sistema tenga capacidad institucional suficiente o SS-11 esté resuelto por fijar un límite de filas.

## Archivos y diff de esta intervención

| Archivo | Cambio |
|---|---|
| backend/app/routers/reporting.py | Tres funciones existentes protegidas, helper de lectura y respuesta propietaria CSV; OpenAPI de excesos |
| backend/app/services/report_limits.py | Nuevo: configuración, lectura acotada, orden resumen, CSV y limpieza |
| docker-compose.yml | Cuatro variables de presupuesto, sin otros cambios propios |
| tests/security/test_reporting_resource_limits.py | Nuevo: 23 pruebas aisladas |
| tests/frontend-ssalfer/report-limits-contract.cjs | Nuevo: contrato JS puro |
| docs/security/SS-11-ETAPA1-CORRECCION-2026-10-28.md | Nuevo: informe e inventario/diseño de etapa2 |
| docs/security/SS-11-ETAPA1-CORRECCION-2026-10-28.patch | Nuevo: diff exclusivo SS-11 |

El patch se genera contra el estado local **anterior a SS-11**, con todos los cambios previos conservados. No se usa un diff completo contra HEAD que mezcle SS-01/02/03/04/10. El contenido inicial de Compose se verifica por SHA contra su snapshot antes de generar el diff propio. Incluye los tres archivos nuevos de implementación/pruebas y este informe; excluye únicamente el patch mismo. No debe reemplazar remediaciones anteriores.

Comprobaciones finales: git diff --check, parseo AST/YAML sin .env y git apply --reverse --check --whitespace=error-all del parche, sin aplicarlo o revertirlo.

| Archivo de implementación/pruebas | SHA-256 final |
|---|---|
| backend/app/routers/reporting.py | `9bbb785dced4b4eaf610caf98b53eabe11f5dfba5a7ce5a8abf5117b71cd788e` |
| docker-compose.yml | `9d4959d217ef4993b87c194614257fe96e51bcc1097dc20f9f33603146fd4a6e` |
| backend/app/services/report_limits.py | `94d994a42e40793c6b2396c2615aedbc7406ca32db5f2b85e78d85a4d22d79f7` |
| tests/security/test_reporting_resource_limits.py | `806225b1074fdc61bf2565ca3b57fdcc43d89170b746ad24db09ff67e0d11dfa` |
| tests/frontend-ssalfer/report-limits-contract.cjs | `74eeec2f52ca372445eeed3486499b987e1a11b2f649c16c654e0fb44a93cde1` |

El [diff completo y revisable](SS-11-ETAPA1-CORRECCION-2026-10-28.patch) contiene exactamente esta intervención. El siguiente extracto corresponde a los archivos preexistentes:

```diff
diff --git a/backend/app/routers/reporting.py b/backend/app/routers/reporting.py
--- a/backend/app/routers/reporting.py
+++ b/backend/app/routers/reporting.py
@@ -1,8 +1,7 @@
 """Dashboard, export and project map read models."""
 
-import csv
-import io
 import json
+import time
 
 from fastapi import APIRouter, Depends, HTTPException, Path, Query
 from fastapi.responses import StreamingResponse
@@ -15,10 +14,33 @@
 from ..services.access import authorized_project_ids, require_project_access, require_project_nucleus_access
 from ..services import convenio_reports, dashboard_summary, map_summary
 from ..services import report_references as report_references_service
+from ..services import report_limits
 
 
 router = APIRouter(tags=["Dashboard y mapa"])
 READ_ROLES = ["admin", "operador", "visualizador", "geografo"]
+
+
+class DashboardCsvResponse(StreamingResponse):
+    """Own the file even if ASGI is cancelled before iteration starts."""
+    def __init__(self, output):
+        self.output = output
+        super().__init__(report_limits.file_chunks(output),
+            media_type="text/csv; charset=utf-8",
+            headers={"Content-Disposition": "attachment; filename=dashboard.csv"})
+
+    async def __call__(self, scope, receive, send):
+        try:
+            await super().__call__(scope, receive, send)
+        finally:
+            self.output.close()
+
+
+def _complete_report_rows(db, query, limits, *, already_read=0):
+    try:
+        return report_limits.read_complete_rows(db, query, limits, already_read=already_read)
+    except report_limits.ReportLimitError as exc:
+        raise HTTPException(exc.status, detail=exc.detail) from exc
 
 
 @router.get(
@@ -264,7 +286,8 @@
     ).offset(skip).limit(limit).all()
 
 
-@router.get("/reportes/avance-periodo", response_model=list[schemas.ReporteAvancePeriodoResponse])
+@router.get("/reportes/avance-periodo", response_model=list[schemas.ReporteAvancePeriodoResponse],
+    responses={413: {"description": "El conjunto completo excede el límite; acote los filtros. No se devuelve una página parcial."}})
 def reporte_avance_periodo(
     id_proyecto: int | None = None,
     id_entidad: int | None = Query(default=None, gt=0),
@@ -303,15 +326,23 @@
         query = query.filter(models.ReporteAvancePeriodo.tipo_convenio == tipo_convenio)
     if destino_superficie is not None:
         query = query.filter(models.ReporteAvancePeriodo.destino_superficie == destino_superficie)
-    return query.order_by(
+    query = query.with_entities(*(getattr(models.ReporteAvancePeriodo, name)
+        for name in report_limits.ADVANCE_COLUMNS)).order_by(
         models.ReporteAvancePeriodo.id_proyecto,
         models.ReporteAvancePeriodo.anio,
         models.ReporteAvancePeriodo.mes,
         models.ReporteAvancePeriodo.indicador,
-    ).all()
-
-
-@router.get("/reportes/resumen-actual", response_model=list[schemas.ReporteSnapshotActualResponse])
+        models.ReporteAvancePeriodo.id_entidad,
+        models.ReporteAvancePeriodo.ambito.nulls_last(),
+        models.ReporteAvancePeriodo.tipo_cop_operativo.nulls_last(),
+        models.ReporteAvancePeriodo.tipo_convenio.nulls_last(),
+        models.ReporteAvancePeriodo.destino_superficie.nulls_last(),
+    )
+    return _complete_report_rows(db, query, report_limits.load_limits())
+
+
+@router.get("/reportes/resumen-actual", response_model=list[schemas.ReporteSnapshotActualResponse],
+    responses={413: {"description": "El conjunto completo excede el límite; acote los filtros. No se devuelve una página parcial."}})
 def reporte_resumen_actual(
     id_proyecto: int | None = None,
     id_entidad: int | None = Query(default=None, gt=0),
@@ -331,10 +362,17 @@
     for field, value in ((models.ReporteSnapshotActual.id_entidad, id_entidad), (models.ReporteSnapshotActual.ambito, ambito), (models.ReporteSnapshotActual.indicador, indicador), (models.ReporteSnapshotActual.tipo_cop_operativo, tipo_cop_operativo), (models.ReporteSnapshotActual.destino_superficie, destino_superficie)):
         if value is not None:
             query = query.filter(field == value)
-    rows = query.order_by(
+    limits = report_limits.load_limits()
+    query = query.with_entities(*(getattr(models.ReporteSnapshotActual, name)
+        for name in report_limits.SNAPSHOT_COLUMNS)).order_by(
         models.ReporteSnapshotActual.id_proyecto,
         models.ReporteSnapshotActual.indicador,
-    ).all()
+        models.ReporteSnapshotActual.id_entidad,
+        models.ReporteSnapshotActual.ambito.nulls_last(),
+        models.ReporteSnapshotActual.tipo_cop_operativo.nulls_last(),
+        models.ReporteSnapshotActual.destino_superficie.nulls_last(),
+    )
+    rows = _complete_report_rows(db, query, limits)
 
     # 006 no publicó un snapshot de esta condición. Se calcula en la capa de
     # lectura desde el valor vigente de afectaciones activas y se deduplica por
@@ -392,11 +430,12 @@
             models.ProyectoNucleo.id_proyecto,
             models.Municipio.id_entidad,
         )
-        rows.extend(current.all())
+        current = current.order_by(models.ProyectoNucleo.id_proyecto, models.Municipio.id_entidad)
+        rows.extend(_complete_report_rows(db, current, limits, already_read=len(rows)))
 
     return sorted(
         rows,
-        key=lambda row: (row.id_proyecto, row.indicador, row.id_entidad),
+        key=report_limits.snapshot_key,
     )
 
 
@@ -683,51 +722,44 @@
     ).all()
 
 
-@router.get("/exportaciones/dashboard.csv")
+@router.get("/exportaciones/dashboard.csv", responses={
+    413: {"description": "La exportación excede filas o bytes; acote los filtros. No se entrega un CSV parcial."},
+    504: {"description": "Se excedió el plazo cooperativo de preparación configurado."},
+})
 def export_dashboard(
     id_proyecto: int | None = None,
     anio: int | None = Query(default=None, ge=2000, le=2200),
     db: Session = Depends(get_db),
     user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
 ):
-    rows = _dashboard_query(db, user, id_proyecto, anio).order_by(
-        models.DashboardKpi.id_proyecto,
-        models.DashboardKpi.anio,
-        models.DashboardKpi.indicador,
-    ).all()
-    output = io.StringIO()
-    writer = csv.writer(output)
-    writer.writerow(
-        [
-            "id_proyecto",
-            "anio",
-            "indicador",
-            "programado",
-            "realizado",
-            "cantidad",
-            "superficie_ha",
-            "monto",
-        ]
-    )
-    for row in rows:
-        writer.writerow(
-            [
-                row.id_proyecto,
-                row.anio,
-                row.indicador,
-                row.programado,
-                row.realizado,
-                row.cantidad,
-                row.superficie_ha,
-                row.monto,
-            ]
-        )
-    output.seek(0)
-    return StreamingResponse(
-        iter([output.getvalue()]),
-        media_type="text/csv; charset=utf-8",
-        headers={"Content-Disposition": "attachment; filename=dashboard.csv"},
-    )
+    output = None
+    try:
+        try:
+            limits = report_limits.load_limits()
+            deadline = time.monotonic() + limits.build_seconds if limits.build_seconds is not None else None
+            query = _dashboard_query(db, user, id_proyecto, anio).with_entities(
+                *(getattr(models.DashboardKpi, name) for name in report_limits.CSV_COLUMNS)
+            ).order_by(models.DashboardKpi.id_proyecto, models.DashboardKpi.anio,
+                       models.DashboardKpi.indicador).limit(limits.rows + 1)
+            result = db.execute(query.statement, execution_options={"yield_per": limits.batch_rows,
+                "stream_results": True, "max_row_buffer": limits.batch_rows})
+            try:
+                output = report_limits.build_csv(result, limits, deadline=deadline)
+            finally:
+                result.close()
+        finally:
+            # This read-only endpoint has completed all DB work. Slow clients
+            # retain only the private file, never a dependency-owned cursor.
+            db.close()
+        return DashboardCsvResponse(output)
+    except report_limits.ReportLimitError as exc:
+        if output is not None:
+            output.close()
+        raise HTTPException(exc.status, detail=exc.detail) from exc
+    except BaseException:
+        if output is not None:
+            output.close()
+        raise
 
 
 @router.get("/proyectos/{id_proyecto}/mapa")
diff --git a/docker-compose.yml b/docker-compose.yml
--- a/docker-compose.yml
+++ b/docker-compose.yml
@@ -13,6 +13,10 @@
   AUTH_ABSOLUTE_MINUTES: ${AUTH_ABSOLUTE_MINUTES:-480}
   AUTH_LOCK_MINUTES: ${AUTH_LOCK_MINUTES:-15}
   AUTH_TRUSTED_PROXY_IPS: ${AUTH_TRUSTED_PROXY_IPS:-}
+  REPORT_MAX_ROWS: ${REPORT_MAX_ROWS:-10000}
+  REPORT_EXPORT_MAX_BYTES: ${REPORT_EXPORT_MAX_BYTES:-16777216}
+  REPORT_FETCH_BATCH_ROWS: ${REPORT_FETCH_BATCH_ROWS:-250}
+  REPORT_EXPORT_BUILD_TIMEOUT_SECONDS: ${REPORT_EXPORT_BUILD_TIMEOUT_SECONDS:-}
   IMPORT_MAX_FILE_SIZE_MB: ${IMPORT_MAX_FILE_SIZE_MB:-100}
   IMPORT_GEOJSON_MAX_FEATURE_MB: ${IMPORT_GEOJSON_MAX_FEATURE_MB:-16}
   IMPORT_MAX_RECORD_BYTES: ${IMPORT_MAX_RECORD_BYTES:-67108864}
```

**Intervención detenida para revisión.** No se inicia etapa2, no se cambia el mapa o SQL global, no hay integración ni despliegue.
