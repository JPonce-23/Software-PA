# Fixtures de base de datos

`001_catalogo_territorial_inegi.sql` es el catálogo territorial reproducible
de SOFTWARE-PA. Usa claves naturales INEGI, no conserva IDs internos y aplica
UPSERT idempotente. Su metadata y checksum están en el archivo JSON homónimo.

El fixture debe cargarse después de las migraciones y de crear un administrador
activo mediante el bootstrap seguro, y antes del dominio demo.
La carga aborta si el catálogo activo final no contiene exactamente 32
entidades federativas y 2,478 municipios/alcaldías con claves únicas.

Los Excel de `fuentes_locales/` no forman parte de este fixture ni se copian al
repositorio.

## Catálogo nacional RAN/PHINA

`catalogo_nucleos_ran.csv` conserva exactamente los bytes CP1252 del archivo
fuente aprobado. `catalogo_nucleos_ran.metadata.json` es la fuente de verdad para
checksum, tamaño, filas, claves, columnas y conteos por tipo/entidad. También fija
el checksum de `ran_municipio_inegi_crosswalk.csv`.

La fuente institucional es el **Registro Agrario Nacional (RAN)**, a través de
su [portal oficial de Datos Abiertos](https://datos.ran.gob.mx/). El conjunto es
**Catálogo de Núcleos Agrarios** y el recurso **Listado del total de los Núcleos
Agrarios que conforman la Propiedad Social**, publicados en la
[página oficial de conjuntos](https://datos.ran.gob.mx/conjuntoDatosPublico.php).
El portal describe sus Datos Abiertos como información pública disponible para
uso, reutilización y redistribución para cualquier fin legal; no se atribuye una
licencia específica adicional.

`source` conserva la clave técnica `RAN_PHINA_CATALOGO_NUCLEOS` utilizada por el
importador; `source_name` identifica la fuente institucional. El SHA-256 del
manifiesto identifica exactamente el **snapshot local aprobado por Software-PA**.
No se afirma que coincida byte por byte con la descarga actualmente publicada en
el portal RAN: esa descarga no se ha obtenido y comparado en esta fase.

V1 contiene 32,278 claves: 29,852 ejidos y 2,426 comunidades en 32 entidades.
Los 51 registros sintéticos QA/GIS adicionales de `software_pa_test` no pertenecen
al artefacto ni al objetivo productivo. No copiar datos de esa DB a un servidor.

La carga exige estructura RAN de 019 o posterior (release actual 028), catálogos
territoriales y de tenencia activos, y un administrador activo para autorizar
apply. No ejecutar `seed_objective_demo.py` para obtener el catálogo productivo.

Desde cualquier directorio, con conexión y Python configurados:

```bash
/ruta/Software-PA/backend/scripts/sync_catalogo_ran.sh \
  --expected-database nombre_real_de_la_base
/ruta/Software-PA/backend/scripts/sync_catalogo_ran.sh \
  --expected-database nombre_real_de_la_base \
  --actor-email administrador_del_destino@example.org --apply
```

El script localiza artefactos junto al manifiesto, comprueba integridad antes de
conectar y rechaza conexión contradictoria, actor inexistente/inactivo/no admin,
errores de datos y municipios sin correspondencia. `--metadata /ruta/manifest.json`
permite seleccionar otro artefacto aprobado; CSV y crosswalk deben estar junto
al manifiesto. `PYTHON_BIN` puede seleccionar un intérprete con `psycopg2`.

El importador conserva su salida humana y añade `--report-json`: un objeto con
`database`, `dataset_sha256`, `rows`, `insertions`, `updates`, `unchanged`, `errors`,
`error_details`, `unresolved_crosswalk`, `success` y `mode`. El script usa esa
salida, no interpreta logs humanos. Un dry-run con cambios termina sin escribir;
apply sólo se ejecuta con `--apply`, después de dry-run exitoso. Una importación
fallida revierte su transacción; un fallo de la comprobación posterior se reporta
como error y no revierte una importación que ya fue confirmada.

La identidad es fuente RAN + clave externa normalizada por el importador, no el
ID interno, ni la coincidencia de nombre/municipio. Las actualizaciones conservan
IDs; no se borran ausentes ni se reactivan registros inactivos. La verificación
final exige cobertura del dataset, informa activos y extras y no fuerza un total
global. En instalación limpia: 32,278 claves cubiertas y activas, cero extras.

Para actualizar: aprobar CSV y crosswalk, sustituirlos y actualizar el manifiesto
en el mismo cambio, revisar dry-run, autorizar apply y exigir segundo dry-run sin
cambios. No modificar saltos de línea/codificación ni actualizar checksums para
silenciar una corrupción. Los tests fijan el hash del artefacto V1 aprobado;
una nueva versión requiere revisar también esas expectativas.

### Prueba completa aislada

`tests/test_sync_catalogo_ran.py::test_full_dataset_reproduces_in_explicit_empty_database`
requiere `RAN_REPRO_DATABASE` con prefijo `software_pa_ran_repro_`, preparada
exclusivamente para esta prueba: migraciones canónicas 001–028, un administrador
activo, fixture territorial y cero núcleos RAN. Ejecutar pytest con las guardas
habituales `APP_ENV=test`, `DB_NAME=software_pa_test`,
`TEST_ALLOW_DATABASE=software_pa_test`. Sólo ese test cambia su conexión de forma
temporal a la base desechable indicada; el resto usa rollback/mocks/lectura.
La prueba completa realiza commits **sólo en esa DB desechable**, verifica carga
de todas las claves y reejecución sin duplicados ni cambios de IDs. El responsable
del entorno debe eliminar esa base al terminar; sin la variable se omite el caso.
