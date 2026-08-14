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

La segunda migración registra el alcance real de las identidades externas. El
KML RAN de Campeche demostró que `IdNucleoAgrario` se reutiliza en municipios
distintos, por lo que su alcance predeterminado es territorial. Sólo debe
seleccionarse alcance global cuando la fuente documente esa garantía.
La identidad territorial se materializa con el municipio interno que ya fue
resuelto de forma estricta; las claves externas continúan intactas como datos de
procedencia.

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
