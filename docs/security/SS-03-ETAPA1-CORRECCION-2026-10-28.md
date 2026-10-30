# SS-03 — Etapa 1: corrección de presupuestos de inspección, lectura y ZIP

Fecha de entrega: 2026-10-28. Referencia: `dev`, HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff`.

## Resultado y alcance

Primera etapa implementada y comprobada con **32 pruebas aisladas aprobadas, 0 fallos**. Corrige unidades GDAL y limita la salida de inspección, los registros GeoJSONSeq, bytes totales procesados, capas/features y extracción ZIP. Los excesos se rechazan explícitamente, sin truncar geometrías ni aceptar una importación parcial por un límite de recursos. No se declara cerrado SS-03 completo ni se acredita rendimiento o aislamiento de producción.

Se preservaron íntegros los cambios locales anteriores de SS-01, su prueba, patch e informes mediante comparación SHA-256 antes/después. No se editaron sus documentos para cambiar su estado. El índice y HEAD permanecen intactos. No hubo SSH, acceso a servicios institucionales, conexión a PostgreSQL, Docker, migraciones, instalación, commit/push/merge/checkout ni despliegue.

## Inventario e inspección previa

Se leyeron gis_ingestion.py, geospatial_imports.py, gis_reconciliation.py, el router geospatial_imports, database.py, Compose y las fuentes de pruebas de importaciones DDV/núcleos/parcelas, preflight, conciliación y concurrencia. También los cuatro informes de auditoría solicitados. database.py y el router no se modificaron; las sesiones, autorizaciones y políticas de roles quedan fuera de esta intervención.

| Flujo | Entrada y recorrido | Presupuestos aplicados |
|---|---|---|
| Legacy trazo | GeoJSON/JSON, KML, GPKG o ZIP/Shapefile → stage_import | Almacenamiento existente, ZIP si corresponde, inspección y lectura comunes; error explícito y limpieza del intento fallido |
| Legacy núcleo/parcela con mapping | stage_import delega a reconciliation.stage(strict=False) | Mismos límites comunes y extracción; reglas de matching existentes |
| DDV | stage_ddv_import → stage estricto GPKG | Inspección/lectura comunes, una capa espacial como antes, entrega completa |
| Núcleo/parcela GPKG | stage_nucleus_import/stage_parcel_import → stage estricto | Inspección/lectura comunes, una capa espacial, entrega completa/parcial conservada |

Todos los consumidores de inspect_dataset/iter_features localizados pertenecen a esos flujos y sus pruebas. No hay archivos .gpkg/.geojson/.kml/.zip/.shp versionados en el SHA; las fuentes inspeccionadas generan fixtures sintéticas de pocas features, por ejemplo 1–6, polígonos pequeños y casos multicapas/CRS/dimensiones. No hay evidencia para dimensionar datasets institucionales o capacidad de RAM/disco. Los archivos auxiliares locales ignorados y los datos institucionales no se procesaron.

Compose y .env.example declaraban 100 MiB por archivo y timeout GDAL de 300 s. El extractor tenía 500 MiB expandidos como default Python, sin exponer esa variable en el entorno de Compose. El proceso de auditoría no tenía overrides de las variables IMPORT de recursos consultadas. No se leyó .env ni se inspeccionó configuración efectiva de contenedores/servidor.

## Archivos de esta intervención

| Archivo | Tipo / propósito |
|---|---|
| backend/app/services/gis_ingestion.py | Modificado: unidades, stdout limitado, buffers y conteos |
| backend/app/services/geospatial_imports.py | Modificado: extracción común, cierre explícito del lector y limpieza legacy ante fallos |
| backend/app/services/gis_reconciliation.py | Modificado: cierre del lector y conteos observados cuando GDAL no informa cantidad |
| docker-compose.yml | Modificado: sólo exposición de variables de presupuestos en el anchor del backend |
| backend/app/services/gis_limits.py | Nuevo: configuración positiva, independiente y con valores finitos |
| backend/app/services/gis_archives.py | Nuevo: extracción ZIP aislable mediante stdlib, límites y propiedad del directorio |
| tests/security/test_gis_resource_limits.py | Nuevo: suite unittest fuera de conftest de backend |
| docs/security/SS-03-ETAPA1-CORRECCION-2026-10-28.md | Nuevo: este informe |
| docs/security/SS-03-ETAPA1-CORRECCION-2026-10-28.patch | Nuevo: diff completo de la intervención salvo el patch mismo |

No hay cambios propios en frontend, documentos, autenticación, roles, esquema, migraciones, Dockerfiles ni dependencias. El patch incluye los siete archivos de código/configuración/pruebas y este informe; excluye expresamente todos los cambios previos de SS-01 y no puede incluirse a sí mismo. La mayor parte de la diferencia de indentación de staging se debe a closing/try/finally. Se comprobó por AST que los cuerpos de los bucles de procesamiento de features, incluidas sus cadenas SQL, son idénticos a HEAD; sólo cambia el envoltorio de control de recursos y el cierre de conteos.

## Límites, unidades y justificación

Son **techos iniciales de política por operación**, configurables y sujetos a validación QA con datasets representativos. No son capacidades medidas ni garantías de consumo RSS. Se eligió margen sobre fixtures pequeñas, conservando el techo de archivo/ZIP previo y separando los tamaños de fuente, registro y salida. Ningún valor habilita ilimitado: las nuevas variables deben ser enteros positivos. Una configuración inválida falla cerrada; no se sustituye por cero o ilimitado.

| Variable | Default | Unidad y alcance | Justificación |
|---|---:|---|---|
| IMPORT_MAX_FILE_SIZE_MB | 100 (sin cambio) | MiB por archivo de entrada; conversión a bytes en _store_upload | Techo previo, independiente del driver y de su salida |
| IMPORT_GEOJSON_MAX_FEATURE_MB | 16 | MB según opción nativa GDAL, por feature GeoJSON | Sustituye el valor erróneo; limita un objeto grande sin imponer tamaño de archivo de 16 MB |
| IMPORT_MAX_RECORD_BYTES | 67108864 | 64 MiB por registro de salida GeoJSONSeq | Margen para geometría, atributos, WKB hexadecimal y representaciones duplicadas; no trunca |
| IMPORT_MAX_OUTPUT_BYTES | 536870912 | 512 MiB de stdout de ogr2ogr, acumulado entre capas | Expansión finita para todos los formatos, separada del archivo/registro |
| IMPORT_MAX_INSPECTION_BYTES | 8388608 | 8 MiB de stdout de ogrinfo | Evita capture_output sin límite; metadatos de más capas/columnas se rechazan |
| IMPORT_MAX_LAYERS | 16 | Capas espaciales por operación | Límite para formatos genéricos; GPKG estricto conserva máximo una capa espacial |
| IMPORT_MAX_FEATURES | 100000 | Features globales por operación, declaradas y observadas | Techo finito de crecimiento de staging; no sustituye CPU/RAM/cuotas globales |
| IMPORT_ZIP_MAX_ENTRIES | 2048 | Entradas ZIP, incluidos directorios | Acota cantidad de archivos y evita bypass mediante entradas vacías |
| IMPORT_ZIP_MAX_MEMBER_BYTES | 268435456 | 256 MiB expandidos por miembro | Evita que un único auxiliar consuma todo el presupuesto |
| IMPORT_MAX_UNCOMPRESSED_MB | 500 | MiB expandidos totales | Preserva el techo previo y ahora verifica bytes reales acumulados |
| IMPORT_GDAL_TIMEOUT_SECONDS | 300 (sin cambio) | Segundos por proceso | No es un timeout integral de importación; permanece pendiente etapa 2 |

La [documentación oficial de GeoJSON GDAL](https://gdal.org/en/stable/drivers/vector/geojson.html) expresa OGR_GEOJSON_MAX_OBJ_SIZE en MBytes y permite cero como ilimitado. Ahora recibe el entero positivo 16 por defecto, **sin multiplicarlo por 1048576**. El caso configurable de prueba usa 7 y comprueba que la entrada de 100 MiB no cambia ese valor. La función anterior evaluada aisladamente con defaults producía 104857600: falla la nueva expectativa de unidades. La elección del default 16 es una política explícita adicional a corregir la unidad, no una afirmación de equivalencia con el umbral accidental anterior.

Compose sólo añade las variables al anchor ya utilizado por backend. Esto es necesario para que una variable del archivo de entorno Compose llegue realmente al contenedor; no basta con documentarla en .env. No se alteraron servicios, red, montajes o límites del daemon y no se ejecutó Compose. La configuración efectiva del despliegue queda pendiente de una fase autorizada.

## Comportamiento e integridad

### Inspección y GeoJSONSeq

_run_json usa Popen y lectura binaria acotada de stdout en lugar de capture_output. stderr se descarta sin acumularlo. Se rechaza antes de incorporar al buffer un chunk que exceda el presupuesto. La inspección JSON se valida como objeto y los errores se convierten en IngestionError con mensaje controlado.

iter_features conserva bytes en un bytearray acotado y decodifica JSON sólo cuando hay registro completo. Soporta UTF-8 fragmentado, CRLF, separador RS, múltiples registros por lectura y última línea sin LF. El LF delimitador no cuenta en el máximo del registro; RS/CR sí cuentan si están presentes. La salida total cuenta todos los bytes, incluidos delimitadores y líneas vacías. No se recortan atributos, coordenadas ni geometrías para que quepan.

El helper de proceso conserva stdin cerrado, argumentos como lista sin shell y timeout; en finally mata el hijo GDAL directo si sigue vivo, espera su terminación y cierra stdout. Tanto iter_features como sus consumidores usan closing para propagar el cierre al fallar el parser, el presupuesto o el cuerpo de procesamiento de una feature. GeneratorExit/cancelación y errores de consumo no dependen del garbage collector para limpiar. Las pruebas usan procesos simulados: el comportamiento nativo del sistema operativo y GDAL requiere validación posterior.

Se verifican capas y suma de features declaradas antes de iterar, y features realmente leídas antes de entregarlas al consumidor. Conteos ausentes/negativos se representan internamente como desconocidos, no como archivo vacío. El total inicial para persistencia es la suma no negativa disponible; al terminar se sustituye por el total observado. Cada conteo conocido debe coincidir con su capa; una discrepancia rechaza la operación. El argumento interno limit_per_layer, sin consumidores actuales localizados, ahora es un presupuesto de rechazo; **no añade -limit al comando GDAL**.

Los rechazos pueden ocurrir tras haber entregado features válidas al servicio; no equivalen a una importación aceptada parcialmente. Legacy revierte staging, marca su cabecera existente en error y devuelve 422 con detalle controlado. Conciliación revierte su transacción y devuelve 422; sólo llega a previsualizado al terminar el lector y validar los conteos. No se modifica la semántica funcional de entrega completa/parcial ni decisiones de confirmar/ignorar features. Su atomicidad real contra PostgreSQL permanece pendiente de las suites QA.

### ZIP y almacenamiento

Se validan rutas normalizadas, absolutos, .., symlinks/archivos especiales y pertenencia a raíz; se crean archivos de forma exclusiva y se conserva la exigencia de un único .shp. Antes de extraer se verifican número de entradas y tamaños declarados individual/total. Durante copia se cuentan los bytes efectivamente leídos y escritos por miembro y en toda la extracción; una discrepancia de tamaño se rechaza. Los presupuestos efectivos no dependen sólo del directorio central ZIP.

El directorio privado de extracción se crea sin exist_ok y antes del bloque que podría borrarlo. Si ya existe, se rechaza sin eliminarlo. Ante error, rechazo o cancelación se elimina únicamente el directorio recién creado; el caller elimina el upload fallido. Los callers sólo limpian una extracción después de que _extract_zip haya retornado una ruta, evitando borrar una carpeta ajena cuando falla la creación. Las cancelaciones durante almacenamiento de upload también limpian el archivo parcial.

La política previa de retención de originales legacy exitosos se conserva; conciliación sigue eliminando originales en finally. No se añade borrado global ni tarea de retención. Las cuotas son por operación, no un máximo de uso total del volumen.

### Contratos conservados

No se editaron normalización CRS/4326, SQL de geometría, dimensiones/WKB, identificación/matching, SAFE_FIELDS, SHA-256, versiones, historial, decisiones o autorizaciones. Las funciones de normalización/confirmación y demás funciones de esos módulos no cambiaron por AST; los cuerpos de procesamiento dentro de los dos bucles iteradores son idénticos. La nueva configuración y el rechazo explícito sí pueden impedir importar datos legítimos que superen los techos: esto requiere ajuste deliberado y revisión con datasets representativos.

## Pruebas, resultados y omisiones

Comando seguro ejecutado, sin importar conftest de backend:

```sh
python3 -B -m unittest discover -s tests/security -p 'test_gis_resource_limits.py' -v
```

Resultado final: **Ran 32 tests; OK**. Todos son stdlib, datos sintéticos y directorios temporales; se mockean Popen/select/read para no lanzar GDAL. Los tests de staging ejecutan funciones extraídas por AST con DB/modelos simulados; no importan app.database/app.main/SQLAlchemy ni conectan a BD. La prueba dedicada verifica que esos módulos no fueron cargados. No se crearon usuarios, sesiones, importaciones reales ni servicios.

| Escenario requerido | Evidencia |
|---|---|
| Unidades correctas | Default 16 y override 7; independencia de upload; baseline 104857600 contradice la nueva expectativa |
| Features válidas y excesos | Exactamente en límite, por encima, salida agregada y por capa, límites observados y declarados |
| UTF-8 y ausencia de LF final | Fragmentación de un byte, texto con acentos/emoji y registro final completo |
| ZIP entradas/presupuesto | Conteo máximo, declarado individual/total y bytes reales con metadatos simulados incorrectos |
| Temporales y cancelación | Directorio ajeno intacto, extracción fallida/bad ZIP/symlink/duplicados, cancelación y cierre de lector |
| Conteos inconsistentes | Menos/más que GDAL, desconocidos aceptados sólo bajo control observado |
| Compatibilidad legítima | CRS/columnas por cuatro drivers en metadatos simulados, coordenadas Z/WKB intactas, archivos auxiliares copiados byte a byte |
| Error de servicio | Legacy simulado: rollback, cabecera error, lector cerrado y upload eliminado; conciliación: rollback/limpieza al fallar inspección |

Comprobaciones adicionales: ast.parse de seis archivos Python válidos; git diff --check sin problemas; AST de bucles y funciones comparado con HEAD; hashes de todos los archivos preexistentes SS-01/documentos iguales al inicio; índice Git sin cambios. La comprobación inversa del patch se hace con --check, no aplica ni revierte nada.

Omitidas: suites backend/tests/test_geospatial_imports.py, test_ddv_gpkg_imports.py, test_nucleus_gpkg_imports.py, test_parcel_gpkg_imports.py, test_gis_preflight_024.py, test_gis_confirmation_024.py, test_gis_concurrency_026.py y demás suites GIS con PostgreSQL/GDAL. conftest exige BD test pero también abre conexiones y hace escrituras. No hay autorización ni BD QA desechable verificada. ogrinfo/ogr2ogr no están instalados aquí. No se instaló nada ni se usó Docker para suplirlos. Las pruebas puras de extracción no certifican que el contenido sintético de un .shp sea un dataset nativo válido; prueban el extractor, no el parser GDAL.

## Riesgos de regresión y aceptación posterior

1. Features grandes, WKB hexadecimal, muchas columnas/capas o conversiones expansivas pueden superar presupuestos legítimamente. Medir en QA con muestras autorizadas antes de decidir cambios de límites; no liberar valores ilimitados como solución.
2. Drivers con conteos conocidos pero inexactos ahora rechazan explícitamente; cotejar versiones GDAL y fixtures por formato. Conteos desconocidos se resuelven por observación y deben probarse con triggers reales.
3. Cerrar el lector y limpiar archivos ante fallos modifica la retención de intentos fallidos. No se cambia la procedencia técnica guardada ni se elimina evidencia ajena; revisar recuperación operacional con BD real de QA.
4. El helper de procesos usa pipes/select de Linux, como la implementación existente. No se validó Windows ni comportamiento nativo bajo señales, fallos del disco o procesos no interrumpibles del kernel.
5. Los consumidores que monkeypatcheen iter_features con objetos sin close deben ajustarse al contrato de generador; los consumidores reales utilizan el generador existente. No se aceptan colecciones parciales por presupuesto.

Antes de aprobar para despliegue se requiere ensayo GDAL real en sandbox/QA con fixtures válidas de cada formato, CRS/Z/M y límites justo debajo/encima; suites de conciliación, idempotencia, historial y concurrencia en PostgreSQL desechable; y verificación del entorno efectivo de límites. No se ejecutan en esta intervención.

## Residuales: SS-03 etapa 2 y SS-02

- No hay límite integral de tiempo/CPU/RSS de la importación, ni cuotas agregadas de disco/BD/concurrencia por usuario/proyecto. JSON/Python/ORM pueden ocupar más memoria que los bytes de entrada/salida. Un archivo menor al máximo puede ser costoso para PostGIS.
- ogrinfo/GDAL aún pueden consumir memoria antes de escribir stdout. ZipFile analiza el directorio central antes de poder contar entradas; no es un sandbox del parser. El límite de upload restringe el archivo pero no todo el coste interno de lectura.
- La conversión sigue siendo síncrona dentro de rutas async y las transacciones/bloqueos existentes no fueron rediseñados. Timeout por proceso/capa no equivale a deadline integral ni cancela SQL. Los grandes universos administrativos y queries siguen pendientes.
- El cierre supervisa al hijo directo GDAL, no crea un worker ni una frontera para descendientes/red/filesystem. La terminación y recuperación bajo muerte abrupta del host, falta de espacio/permisos o proceso no interrumpible requiere controles operativos.
- SS-02 debe resolver usuario mínimo, entorno sin secretos, drivers permitidos, filesystem privado, red/egress y límites del contenedor/worker. La herencia de entorno GDAL se conserva y no se presenta como remediada.
- Nuevas cuotas de vértices/complejidad, almacenamiento agregado, colas/worker, statement_timeout/lock_timeout y cancelación integral pertenecen a una etapa posterior revisada, no a cambios improvisados de esta entrega.

Se detiene después de entregar esta etapa. No se inicia SS-02 ni SS-03 etapa 2.

## Identidad de los cambios de código

| Archivo | SHA-256 final |
|---|---|
| `backend/app/services/gis_ingestion.py` | `49c150998b8354f337ca5f07fc1b235d99cdc92af7fa64af103cbcd85ab666de` |
| `backend/app/services/geospatial_imports.py` | `63b6df6caff39f6154f3e2713285800fb10fc8c4158162d5c7ce9581257d66b9` |
| `backend/app/services/gis_reconciliation.py` | `9f8c4bf1b37e3354ed70b33e35e0550bdbd97a51373d722a336ffdd09a1d1977` |
| `docker-compose.yml` | `007ab97b951ee84ea7feba0b06e76c04a2d5b2fbc3434c7e96a2a3c7cad8b5ee` |
| `backend/app/services/gis_limits.py` | `a5063763a87e9e92a3a6376436b9322bda2268e07c700592de505ec6bb294aad` |
| `backend/app/services/gis_archives.py` | `ac2a1adccb60bf82b73568cabcb78dd5eaf2b9fb043d72668008175229e74ba2` |
| `tests/security/test_gis_resource_limits.py` | `435763a2b4bd72ffb646488a13460bc35581a79f5ca8f92b04d27afc35ca3dea` |

Diff completo: [SS-03-ETAPA1-CORRECCION-2026-10-28.patch](SS-03-ETAPA1-CORRECCION-2026-10-28.patch). No incluye la corrección previa de SS-01.
