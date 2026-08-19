# Importador geoespacial seguro

El importador procesa `KML` y `GeoJSON` mediante un único pipeline GDAL/OGR:

```text
archivo privado -> inspección -> staging -> normalización -> resolución
territorial -> revisión -> confirmación explícita -> núcleo agrario -> CSV
```

La inspección y la prevalidación nunca escriben en `nucleo_agrario`,
`tramo_nucleo`, `afectacion` ni en otras tablas operativas. La relación con el
derecho de vía permanece como una operación independiente.

## Migraciones

Se aplican en orden:

1. `020_importador_geoespacial_seguro.sql`
2. `021_alcance_identidad_externa.sql`
3. `022_identidad_externa_territorio_resuelto.sql`
4. `023_procedencia_conversion_geoespacial.sql`
5. `024_archivo_importacion_archivado.sql`
6. `025_cargas_geoespaciales_genericas.sql`
7. `026_trazo_proyecto_secciones_tramo.sql`
8. `027_trazo_lineal_a_franja.sql`

La segunda migración registra el alcance real de las identidades externas. El
KML RAN de Campeche demostró que `IdNucleoAgrario` se reutiliza en municipios
distintos, por lo que su alcance predeterminado es territorial. Sólo debe
seleccionarse alcance global cuando la fuente documente esa garantía.
La identidad territorial se materializa con el municipio interno que ya fue
resuelto de forma estricta; las claves externas continúan intactas como datos de
procedencia.

La cuarta migración permite declarar si un GeoJSON es original o proviene de
un KML ya registrado. En una conversión, la prevalidación compara el conteo de
features de ambos archivos y se bloquea con `PERDIDA_CONVERSION` cuando existe
cualquier diferencia. El operador puede reabrir la configuración desde el
estado `listo_revision`, cambiar esta procedencia o la política de unión de
partes y ejecutar otra prevalidación sin escribir en tablas operativas.

La quinta migración agrega baja lógica para ocultar importaciones antiguas de
la vista activa sin eliminar su historial ni sus reportes.

La sexta migración agrega una capa de staging para capturas individuales de
`franja_derecho_via`, `seccion_derecho_via`, `nucleo_agrario` y `parcela`,
además de candidatos revisables de `tramo_nucleo`. Una feature confirmada se
consume en la misma transacción que crea o actualiza el registro operativo y
no puede reutilizarse. Detectar una intersección nunca crea un expediente por
sí solo.

La séptima migración establece que el trazo oficial pertenece al proyecto y
que cada tramo es una división administrativa con una sección poligonal del
trazo. No se puede cargar una línea directamente sobre un tramo.

La octava migración admite archivos de eje ferroviario segmentado. Si todas las
features son lineales y válidas, la interfaz permite confirmarlas como un único
trazo `MULTILINESTRING`. No infiere una superficie ni solicita anchos: la
superficie operativa se carga después como sección del tramo.

## Configuración

| Variable | Predeterminado | Uso |
|---|---:|---|
| `IMPORT_MAX_FILE_SIZE_MB` | `100` | Tamaño máximo recibido por streaming |
| `IMPORT_STAGING_BATCH_SIZE` | `250` | Features persistidos por lote de prevalidación |
| `IMPORT_CONFIRM_BATCH_SIZE` | `100` | Registros operativos por transacción |
| `IMPORT_GDAL_TIMEOUT_SECONDS` | `300` | Tiempo máximo por operación GDAL |
| `IMPORT_STAGING_RETENTION_DAYS` | `30` | Retención de archivos temporales |
| `IMPORT_MAKE_VALID_MAX_AREA_DELTA` | vacío | Tolerancia relativa de reparación |

La tolerancia de área es una fracción entre `0` y `1`. Mientras permanezca
vacía, cualquier geometría que necesite `ST_MakeValid` se bloquea. Debe ser
aprobada antes de habilitar reparaciones en producción. Las áreas se comparan
en `EPSG:6933`, no directamente en `EPSG:4326`.

## Reglas de resolución

La resolución municipal sigue este orden: clave INEGI completa, clave municipal
externa con entidad, nombre normalizado con entidad y alias aprobado. Cero o
múltiples coincidencias bloquean el feature. Un identificador externo se
conserva como procedencia y nunca se interpreta como PK interna.

Los tipos de núcleo admitidos son `ejido` y `comunidad`, con equivalencias
explícitas. No existe valor predeterminado. Un CRS ausente o no transformable
bloquea el archivo completo.

## Mapeo guiado

La selección inicial muestra únicamente nombre del núcleo, tipo, entidad y
municipio. Cada columna detectada incluye hasta tres valores de muestra leídos
del archivo temporal mediante GDAL, sin ejecutar la prevalidación ni escribir
en staging. Claves INEGI, identificadores externos, perfiles y políticas de
unión permanecen disponibles en `Configuración avanzada`.

## Geometría

GDAL detecta el formato y CRS reales. PostGIS aplica `Force2D`, extracción de
polígonos, conversión a `MultiPolygon`, transformación a `EPSG:4326` y, cuando
es necesario, reparación controlada. Cada transformación y cambio relativo de
área queda en `importacion_feature`.

## Procesamiento y seguridad

La carga usa bloques de 1 MiB, nombre aleatorio, permisos `0600`, SHA-256 y una
ruta no pública. Se verifica el contenido con GDAL, no el MIME del navegador.
El scheduler elimina archivos que superan la retención configurada.

Los trabajos se ejecutan con `BackgroundTasks` y guardan estado y progreso en
PostgreSQL. No existe una cola durable: un reinicio del backend puede dejar un
trabajo en ejecución sin reanudarlo automáticamente. La operación es observable
y reintentable, pero no debe anunciarse como reanudación real hasta incorporar
un ejecutor durable aprobado.

## Captura individual y candidatos

La carga individual acepta `KML`, `GeoJSON` y `Shapefile (.zip)`. El ZIP debe
contener exactamente un dataset y sus archivos `.shp`, `.shx`, `.dbf` y `.prj`.
La selección no escribe geometrías operativas: primero muestra formato, CRS,
conteo, errores y previsualización. Para un formulario con múltiples features,
la persona operadora debe elegir una y confirmarla explícitamente.

El trazo oficial es un polígono versionado del proyecto. Cada tramo recibe una
sección poligonal explícita de ese trazo. Con una sección activa, el sistema
puede detectar núcleos que se intersectan con área positiva. La detección queda
en `candidato_tramo_nucleo`; únicamente un administrador puede aceptar el
candidato y crear el expediente maestro `tramo_nucleo`.
