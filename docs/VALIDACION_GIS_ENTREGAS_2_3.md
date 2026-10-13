# Validación de las entregas GIS 2 y 3

Base: `b79a646d785e119ddbb9f5aff29eaad312e59f7c`.
Worktree aislado: `/tmp/software-pa-gis-entregas-2-3`.

Las pruebas se ejecutan en contenedores temporales con el código del worktree,
`APP_ENV=test`, `DB_NAME=software_pa_test`,
`TEST_ALLOW_DATABASE=software_pa_test` y `PYTHONDONTWRITEBYTECODE=1`.
`conftest.py` rechaza otra base. Se verificó mediante una transacción SQL de
solo lectura que el esquema de pruebas tiene la versión 029 y las referencias
FK utilizadas por la baja. Las fixtures API usan una transacción externa que
revierte sus commits; las pruebas de carrera usan proyectos sintéticos
independientes, conexiones reales y cierre lógico de la fixture.

## Fase A

Comando base (ejecutado desde el checkout que contiene la configuración Docker):

```sh
docker compose run --rm --no-deps \
  -v /tmp/software-pa-gis-entregas-2-3/backend:/app \
  -e APP_ENV=test -e DB_NAME=software_pa_test \
  -e TEST_ALLOW_DATABASE=software_pa_test -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -m pytest -p no:cacheprovider \
  --basetemp=/tmp/gis-baja-tests2 tests/test_gis_baja.py -q
```

Las primeras ejecuciones detectaron un nombre incorrecto de helper y fixtures
sintéticas incompatibles con las restricciones reales de formato/comparabilidad
y revisión. Se corrigieron las fixtures; DDV no crea un ciclo de conciliación
administrativa. Los casos corregidos y añadidos se ejecutaron separadamente,
sin repetir los casos ya aprobados.

Regresiones directamente afectadas: `test_gis_history_026.py` (excepto el caso
administrativo RAN ajeno al alcance), `test_gis_history_regressions.py`,
`test_gis_confirmation_024.py`, `test_gis_concurrency_026.py`, regresión de
trazo legado de `test_geospatial_imports.py`, y lecturas GIS/OpenAPI de
`test_frontend_read_models.py` (excluidas pruebas de documentos).

No se ejecuta la suite completa de GIS 029 ni benchmarks. No se modifican
estructuras o restricciones SQL: no hace falta aplicar migraciones ni repetir
contratos SQL por un cambio de esquema. El checksum de 029 se mantiene:
`284f8a26fc5d1215f21055657a5171431d1df4ee8d0151dc58071e38731e9716`.

Resultado fase A: 38 casos nuevos aprobados en conjunto (33 iniciales,
verificaciones corregidas y 2 protecciones adicionales de pipeline). La última
verificación de dependencias dio 2/2; la verificación previa dio 8 aprobados y
un fallo de fixture posteriormente corregido. No quedan fallos pendientes.
Regresiones: **57 aprobadas, 6 deseleccionadas**, 281,31 s. Advertencia previa
de Starlette/httpx, sin relación con el cambio. OpenAPI generado y exportado;
endpoints y campos obligatorios anteriores conservados. `git diff --check`
sin errores. No se tocaron otros checkouts, frontend ni servidor.

## Fase B

Pruebas nuevas en `test_gis_universe.py`: proyectos sin núcleos, con núcleos y
sin parcelas, vínculos propios/ajenos/inactivos, cambios posteriores al staging,
snapshots nuevos y anteriores, backfills 026 no reconstruibles, importaciones
sin ciclos, reconciliación parcial, reintento idempotente antiguo, permisos,
Pydantic y cantidad acotada de consultas.

La primera ejecución dio 14 aprobadas y un fallo de la expectativa de consultas
(topo de 8 no respaldado por las relaciones ORM existentes). La consulta del
resumen genera **44 SELECT constantes tanto con 1 como con 5 destinos** en
esta fixture, incluyendo autorización y cargas relacionadas existentes. Se
corrigió la prueba para exigir costo constante y una sola consulta de geometría
y de la vista parcelaria, en vez de inventar un presupuesto para toda la API.
Staging carga la vista de parcelas una sola vez con tres features. No se
introducen consultas de universo por feature ni por ciclo en una página.

Se ejecutó el contrato final (`disponibilidad=disponible`, que describe datos
conocidos y no completitud administrativa) junto con regresiones seleccionadas:

```text
python -m pytest -p no:cacheprovider --basetemp=/tmp/gis-universe-final
 tests/test_gis_universe.py
 tests/test_nucleus_gpkg_imports.py::test_three_administrative_nuclei_six_features_partial_reconciliation
 tests/test_nucleus_gpkg_imports.py::test_duplicate_destination_and_rollback_are_atomic
 tests/test_parcel_gpkg_imports.py::test_parcel_number_normalization_is_narrow
 tests/test_parcel_gpkg_imports.py::test_independent_parcel_numbers
 tests/test_parcel_gpkg_imports.py::test_parcel_mixed_import_finishes_without_using_extra_features
 tests/test_gis_history_026.py::test_late_reconciliation_three_cycles_keep_original_no_destination
 tests/test_gis_history_026.py::test_new_delivery_versions_use_topology_and_preserve_domain
 tests/test_gis_baja.py::test_cancel_unconfirmed_and_exact_retry_preserves_audit
 tests/test_gis_baja.py::test_stale_read_cannot_write_after_baja
 tests/test_frontend_read_models.py::test_gis_actor_labels_and_bounded_reads
 tests/test_frontend_read_models.py::test_gis_totals_filters_offsets_and_cors
 tests/test_frontend_read_models.py::test_openapi_only_optional_output_fields_and_new_get -q
```

Resultado: **48 aprobadas**, 208,52 s (15 nuevas + 33 regresiones seleccionadas).
El caso añadido de reintento idempotente de conciliación anterior sin metadatos
nuevos dio **1 aprobada**, 1,12 s, sin reescribir el snapshot. Total fase B:
**16 casos nuevos aprobados**. Se mantiene la advertencia previa Starlette/httpx.

Comprobación estática por AST contra la base: cuerpos de
`normalize_parcel_number`, `nucleus_criteria`, `build_candidates`,
`administrative_universe` y `feature_identity` idénticos. OpenAPI final exportado
sin cambiar campos obligatorios o retirar endpoints anteriores. No se modifica
SQL: las estructuras, restricciones y migraciones históricas quedan intactas.
No se ejecutan contratos SQL de nuevo al no cambiar esquema ni triggers.

Verificación complementaria de fase A: decisiones y candidatos confirmados
protegen la importación aunque contadores/estado de feature no reflejen una
geometría. Los dos casos sintéticos dieron **2 aprobadas**, 7,34 s. Se añadió
el guardado en un commit independiente de la fase A. Total: **40 casos nuevos
A**, **57 regresiones A**, **16 casos nuevos B** y **33 regresiones B**; varias
regresiones se repiten por estar directamente afectadas en ambas fases.
No quedan fallos pendientes. La base de pruebas sigue en 029 y no se aplicaron
migraciones nuevas. El despliegue y cualquier migración productiva corresponden
al encargado del servidor, fuera de esta ejecución.
