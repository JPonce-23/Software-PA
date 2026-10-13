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
