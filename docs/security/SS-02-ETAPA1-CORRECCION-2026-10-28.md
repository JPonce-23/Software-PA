# SS-02 — Etapa 1: entorno explícito de subprocesos GDAL

Fecha: 2026-10-28. Rama dev; HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff`.

## Resultado y límite del dictamen

Se implementó el entorno permitido y se verificó su aplicación en **ogrinfo y ogr2ogr** mediante respuestas sintéticas y mocks. **49 pruebas aisladas aprobadas: 17 nuevas SS-02 y 32 de SS-03.** Se reduce la exposición de variables heredadas; **SS-02 permanece abierto** porque GDAL conserva UID, filesystem y ámbito de procesos del backend.

No se ejecutó GDAL nativo ni se acredita compatibilidad productiva de CRS/formatos. No se instaló nada, no se usó PostgreSQL/servicios institucionales, no se iniciaron ni reconstruyeron contenedores, no hubo migraciones, cambios de frontend/roles/esquema/dependencias, ni commits/push/merge/despliegue. Las lecturas web se limitaron a documentación primaria pública, sin enviar código ni datos del repositorio.

## Estado previo y preservación

El árbol ya contenía SS-01 y SS-03 sin integrar, con fuentes, pruebas y documentos. Se guardaron fingerprints antes de esta intervención. Todos esos archivos conservan su hash, excepto gis_ingestion.py, que necesariamente incorpora el endurecimiento **encima de SS-03**. En ese archivo no se sustituyó ni revirtió el trabajo previo: se cambian sólo el entorno, el shell=False explícito y el rechazo de nombres de capa que podrían interpretarse como opciones CLI.

Se inspeccionaron gis_ingestion, gis_limits, gis_archives, geospatial_imports, gis_reconciliation, Dockerfile, Compose base/prod/override/SSALFER, informes de auditoría y fuentes de pruebas GIS. La imagen backend instala gdal-bin por apt y no fija usuario no privilegiado; sus versiones efectivas no se comprobaron mediante Docker. gis_limits, gis_archives, los consumidores y Compose permanecen iguales al estado inicial de esta intervención.

## Archivos propios de esta entrega

| Archivo | Cambio |
|---|---|
| backend/app/services/gis_ingestion.py | Modificado: entorno explícito, validación de rutas técnicas, shell=False y protección de argumentos de capa |
| tests/security/test_gis_subprocess_environment.py | Nuevo: 17 pruebas aisladas |
| docs/security/SS-02-ETAPA1-CORRECCION-2026-10-28.md | Nuevo: este informe |
| docs/security/SS-02-ETAPA2-DISENO-WORKER.md | Nuevo: diseño, sin implementación |
| docs/security/SS-02-ETAPA1-CORRECCION-2026-10-28.patch | Nuevo: diff completo de esta intervención, excepto el patch mismo |

El patch compara gis_ingestion.py con su contenido local inicial, **no con HEAD**, para excluir SS-03. Incluye los tres archivos nuevos restantes y no incorpora frontend, pruebas previas ni documentos de SS-01/SS-03. Debe revisarse/aplicarse sobre la base local que ya tiene SS-03 etapa 1; no representa un parche independiente contra el commit de auditoría original. La comprobación inversa --check valida que coincide con la entrega sin aplicar ni revertir cambios.

## Política del entorno

Se eliminó os.environ.copy(). Cada hijo recibe un dict nuevo con 15 claves fijas y, si están definidas, un máximo de tres rutas de datos permitidas. No se usan prefijos permisivos tipo GDAL_* o PROJ_*.

| Variables | Política y propósito |
|---|---|
| PATH | Valor fijo /usr/local/bin:/usr/bin:/bin; resuelve binarios del paquete Linux sin heredar directorios del usuario/staging |
| LANG, LC_ALL | C.UTF-8 fijo para texto Unicode y localización determinista |
| TZ | UTC fijo; no se hereda configuración regional de la API |
| HOME, XDG_CONFIG_HOME, XDG_CACHE_HOME | /nonexistent fijo para no dirigir búsquedas implícitas a configuración de la cuenta API; no crea ni aísla directorios |
| TMPDIR, CPL_TMPDIR | /tmp fijo; evita heredar rutas de trabajo arbitrarias; **sigue siendo espacio compartido**, no un tmp privado por trabajo |
| GDAL_CONFIG_FILE | /dev/null fijo; evita cargar gdalrc implícito en versiones compatibles (GDAL >=3.3) |
| PROJ_NETWORK | OFF fijo para rejillas PROJ locales; no es un firewall GDAL |
| GDAL_DISABLE_READDIR_ON_OPEN | EMPTY_DIR, conservado desde SS-03 |
| CPL_VSIL_CURL_ALLOWED_EXTENSIONS, CPL_CURL_VERBOSE | Valores anteriores vacío/NO conservados; no se les atribuye bloqueo universal de red |
| OGR_GEOJSON_MAX_OBJ_SIZE | Derivado de load_limits().geojson_feature_mb; conserva 16 MB por defecto y overrides SS-03 positivos; no hereda la opción GDAL cruda |
| GDAL_DATA (opcional) | Un directorio local absoluto de recursos, sólo si el despliegue lo requiere |
| PROJ_DATA, PROJ_LIB (opcionales) | Directorios locales absolutos, admitiendo listas separadas por os.pathsep; versión moderna y fallback de PROJ |

Las rutas técnicas se leen por nombre exacto, sin volcar el entorno. Se rechazan valores relativos, vacíos en listas, controles/NUL y rutas VSI; un valor inválido produce GDAL_CONFIG_INVALIDA antes de lanzar el proceso, sin incluir su contenido en el mensaje. Una variable vacía/no definida usa los recursos compilados del paquete. No se accede a sus archivos durante estas pruebas ni se verifica su contenido/propiedad: deben ser directorios de confianza, de sólo lectura, preparados por el despliegue. No son parámetros del usuario HTTP.

No se conservan credenciales DB/runtime/owner, SECRET_KEY, contraseñas admin/QA/pgAdmin, cookies/tokens, variables de sesión ni configuración institucional desconocida. También se excluyen proxies, AWS/cloud, LD_PRELOAD/LD_LIBRARY_PATH, PYTHONPATH, rutas de plugins, headers CURL, GDAL_CONFIG_FILE del padre, PROJ_AUX_DB y demás overrides no autorizados. Los límites/timeout IMPORT se consumen en Python y no se copian al hijo; sólo se deriva la opción GeoJSON necesaria. No se leyeron valores reales de .env/credenciales para demostrarlo: se usan sentinelas sintéticos.

## Control de ejecución y rutas

La búsqueda de mecanismos de ejecución en backend/app encontró una sola llamada subprocess de las importaciones: Popen dentro de _process_chunks. _run_json/inspect_dataset (ogrinfo) e iter_features (ogr2ogr) pasan por ella. Ambos reciben env=_gdal_environment(), shell=False, stdin cerrado, stderr descartado y stdout con presupuestos SS-03. Se conservan los argumentos de CRS/precisión/salida y el lector/cierre existentes.

Los comandos se construyen como listas, no texto de shell. Nombres como texto con espacios, comillas, punto y coma o $(...) permanecen un único argumento. En el camino que pasa la capa como argumento posicional se rechazan nombres que comienzan con '-' para impedir que OGR los interprete como opciones. Es una restricción nueva explícita CAPA_NO_SEGURA, no truncamiento ni omisión silenciosa. La rama GPKG con SQL SQLite conserva nombres arbitrarios citados mediante duplicación de comillas; se prueban capa/columna geométrica/FID sin crear argumentos nuevos.

Las rutas de las importaciones HTTP provienen de _store_upload: autorización de proyecto antes de almacenar, raíz UPLOAD_ROOT resuelta, nombre UUID y extensión permitida; el nombre cliente no se concatena como ruta. ZIP retorna el .shp bajo el directorio privado validado. DDV/núcleos/parcelas delegan a esos mismos flujos; los endpoints no reciben una ruta de servidor ni URL para entregar directamente a OGR. **Los helpers internos de ingestión siguen aceptando Path**: la autorización reside en sus consumidores y las llamadas internas futuras deben conservar esa frontera. No se presenta como una prohibición de red o sandbox de rutas universal.

## Drivers y recursos externos

| Necesidad | Tratamiento actual / pendiente |
|---|---|
| GeoJSON | Detección actual y conversión conservadas |
| KML | Mantener compatibilidad con KML o LIBKML según build; no desregistrar uno sin QA |
| GPKG | Conservar SQL SQLite y WKB para dimensiones/procedencia |
| ESRI Shapefile | Conservar auxiliares SHP/SHX/DBF/PRJ y extracción ZIP |
| GeoJSONSeq | Es el driver de **salida**, también necesario al diseñar una lista mínima |

Se evaluaron GDAL_SKIP/OGR_SKIP (listas de exclusión), drivers mínimos compilados y restricción de apertura por GDALOpenEx/CLI -if según versión. No se aplica ahora una lista restrictiva sin inventario del build y pruebas nativas. No basta permitir cuatro extensiones: GDAL puede abrir otros drivers o recursos indirectos antes de la validación posterior. Quitar variables de plugins del padre tampoco deshabilita todos los plugins compilados/configurados en la imagen.

PROJ_NETWORK=OFF evita la intención de descargar rejillas PROJ, y GDAL_CONFIG_FILE evita configuración implícita; ninguno impide que un driver haga otra solicitud o lea ficheros. El valor vacío de la opción CURL previa **no se interpreta como deny-all**. El bloqueo de red, las fronteras del filesystem y un parser comprometido deben resolverse con permisos/namespaces/worker de etapa 2.

## Pruebas y resultados

```sh
python3 -B -m unittest discover -s tests/security -p 'test_gis*.py' -v
```

Resultado final: **Ran 49 tests; OK**. Las pruebas nuevas usan metadata/GeoJSON sintéticos y Popen/select/read simulados; no se ejecutan scripts hostiles ni GDAL nativo. Se importa únicamente la ingestión stdlib y helpers de la suite pura SS-03; no se importa conftest, app.database, app.main ni SQLAlchemy. No hay conexiones ni escrituras fuera de los temporales controlados de la suite SS-03.

| Cobertura | Resultado |
|---|---|
| Secretos sintéticos y claves desconocidas | Excluidos, con igualdad estricta del conjunto permitido |
| Variables técnicas | Preservación de rutas explícitas y constantes; rechazo de rutas no válidas antes de Popen |
| Env de ogrinfo y ogr2ogr | Comprobado para los cuatro formatos con mocks y shell=False |
| Metacaracteres y opciones CLI | Un argumento por nombre; rechazo de nombres genéricos con guion; SQL GPKG citado |
| SS-03 | 32 pruebas previas sin editar, todas aprobadas: unidades/buffers/ZIP/cancelación/conteos/rollback simulado |
| Errores/cierre | Límite de registro, binario ausente y cierre/muerte/recolección del hijo simulado |
| Compatibilidad sintética | Coordenadas/atributos Z, salida GeoJSONSeq, EPSG:4326 y precisión conservados |

Se evaluó la función previa con un SECRET_KEY sintético en memoria: lo copiaba al hijo. La nueva expectativa de exclusión falla en esa versión y pasa en la actual. Durante construcción de las pruebas hubo tres errores de fixture porque os.environ no permite NUL; se corrigió la simulación con un mock de getenv, sin modificar la lógica productiva por ese error. La ejecución final no tiene errores.

Omitidas las suites backend con PostgreSQL/GDAL: no se dispone de GDAL/OGR instalado ni BD QA desechable autorizada. No se usó Docker ni se instalaron dependencias para suplirlos. La compatibilidad nativa y el aislamiento del kernel permanecen pendientes. No se han reproducido SSRF/RCE ni se afirma ausencia universal de esos riesgos.

## Riesgos de regresión y controles residuales

- Instalaciones personalizadas que dependan de PATH/LD_LIBRARY_PATH/plugins/gdalrc o PROJ_AUX_DB heredados deben preparar recursos confiables dentro de la imagen y validar explícitamente el caso. No ampliar la lista permitida por prefijo para restaurar compatibilidad.
- Un CRS que necesite una rejilla ausente localmente puede fallar o usar otra operación disponible al desactivar descarga PROJ. Antes del despliegue, verificar transformación y precisión esperadas con rejillas locales, no sólo que el comando termine. El código de CRS/Z/M y matching no se modificó.
- Localización UTC/C.UTF-8 debe validarse con atributos de fecha/texto del corpus real de QA. No se acredita identidad de resultados nativos sólo mediante mocks.
- Capas genéricas con '-' inicial ahora se rechazan; GPKG por SQL conserva sus identificadores citados. La API devuelve un error controlado, no datos parciales.
- El proceso sigue con el UID de la API, cwd compartido, /tmp y acceso potencial a sus archivos/proc/secretos en disco o memoria de otros procesos según permisos del host. Un parser comprometido puede sobrepasar la protección del entorno.
- No hay deny-all de drivers/red ni límites fuertes de RSS/cgroups por trabajo. La exclusión de secretos del env no garantiza que no puedan recuperarse por otras vías. SS-02 no se marca resuelto.

Aceptación posterior: ejecutar fixtures nativas GeoJSON/KML/GPKG/SHP en sandbox desechable con recursos locales; comprobar versiones y rutas GDAL/PROJ, CRS y dimensiones Z/M y resultados esperados; observar sólo nombres de variables permitidas/sentinelas, sin logs de secretos; contrastar cuotas SS-03. Mantener las regresiones de conciliación/historial/concurrencia en BD QA autorizada. El diseño de etapa 2 define la frontera fuerte pendiente.

## Fuentes técnicas primarias y diseño

- [Configuración GDAL](https://gdal.org/en/stable/user/configoptions.html): archivo de configuración, rutas y selección de drivers.
- [Variables de PROJ](https://proj.org/en/stable/usage/environmentvars.html): recursos locales, nombres PROJ_DATA/PROJ_LIB y red de rejillas.
- [Seguridad GDAL](https://gdal.org/en/stable/user/security.html): abrir datos no confiables requiere permisos y aislamiento; el entorno no basta.
- [ogr2ogr](https://gdal.org/en/stable/programs/ogr2ogr.html): entradas de capas y opciones de driver.
- Diseño adicional: [SS-02 etapa 2](SS-02-ETAPA2-DISENO-WORKER.md). Propuesta sin implementación.

## Diff propio

Hash previo de gis_ingestion.py: `49c150998b8354f337ca5f07fc1b235d99cdc92af7fa64af103cbcd85ab666de`.

Hash final: `dae7019a8e0520cd928779e3565bec4b02c9b012f799075e1d1be32e2bca6339`.

```diff
diff --git a/backend/app/services/gis_ingestion.py b/backend/app/services/gis_ingestion.py
--- a/backend/app/services/gis_ingestion.py
+++ b/backend/app/services/gis_ingestion.py
@@ -61,17 +61,39 @@
 
 
 def _gdal_environment() -> dict[str, str]:
-    env = os.environ.copy()
-    env.update(
-        {
-            "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
-            "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": "",
-            "CPL_CURL_VERBOSE": "NO",
-            "OGR_GEOJSON_MAX_OBJ_SIZE": str(
-                load_limits().geojson_feature_mb
-            ),
-        }
-    )
+    """Linux GDAL child environment: fixed policy plus local data directories only.
+
+    Never forward API credentials, loader/plugin settings, proxies or user config.
+    This reduces ambient configuration; it is not a network/filesystem sandbox.
+    """
+    env = {
+        "PATH": "/usr/local/bin:/usr/bin:/bin",
+        "LANG": "C.UTF-8",
+        "LC_ALL": "C.UTF-8",
+        "TZ": "UTC",
+        "HOME": "/nonexistent",
+        "XDG_CONFIG_HOME": "/nonexistent",
+        "XDG_CACHE_HOME": "/nonexistent",
+        "TMPDIR": "/tmp",
+        "CPL_TMPDIR": "/tmp",
+        "GDAL_CONFIG_FILE": "/dev/null",
+        "PROJ_NETWORK": "OFF",
+        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
+        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": "",
+        "CPL_CURL_VERBOSE": "NO",
+        "OGR_GEOJSON_MAX_OBJ_SIZE": str(load_limits().geojson_feature_mb),
+    }
+    # Resource directories may differ between packaged GDAL/PROJ builds.
+    # PROJ_DATA (>=9.1) and its older PROJ_LIB fallback support search lists.
+    for name in ("GDAL_DATA", "PROJ_DATA", "PROJ_LIB"):
+        value = os.getenv(name)
+        if not value:
+            continue
+        paths = [value] if name == "GDAL_DATA" else value.split(os.pathsep)
+        if (any(ord(char) < 32 for char in value)
+                or any(not Path(part).is_absolute() or part.startswith("/vsi") for part in paths)):
+            raise IngestionError("GDAL_CONFIG_INVALIDA", f"{name} requiere directorios locales absolutos.")
+        env[name] = value
     return env
 
 
@@ -80,7 +102,7 @@
     timeout = int(os.getenv("IMPORT_GDAL_TIMEOUT_SECONDS", "300"))
     try:
         process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
-            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=_gdal_environment())
+            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=_gdal_environment(), shell=False)
     except FileNotFoundError as exc:
         raise IngestionError("GDAL_NO_DISPONIBLE", "El servicio geoespacial no esta disponible.") from exc
     stdout = process.stdout
@@ -271,6 +293,9 @@
             command.extend(["-dialect", "SQLite", "-sql",
                 f'SELECT *{select_fid}, hex(ST_AsBinary("{quoted_geom}")) AS "__pa_source_wkb" FROM "{quoted_layer}"'])
         else:
+            # argv prevents shell commands, but a leading '-' could be an OGR option.
+            if layer.name.startswith("-"):
+                raise IngestionError("CAPA_NO_SEGURA", "El nombre de capa no puede comenzar con un guion.")
             command.append(layer.name)
         command.extend([
             "-t_srs",
```

El [patch completo](SS-02-ETAPA1-CORRECCION-2026-10-28.patch) añade la prueba y ambos documentos. Sólo se redacta el diseño de etapa 2; no se ejecuta su despliegue. Se detiene la intervención para revisión.
