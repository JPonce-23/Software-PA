# Validación de diagnósticos GIS 029 — entrega 1

Fecha: 13 de octubre de 2026. Base de referencia y remoto, comprobados después
de `git fetch origin`: `cc1888ef7432b09553982e13d911c8701a9e38a0`, rama
`feature/backend-logica`. Checkout original limpio; implementación en worktree
detached `/tmp/software-pa-gis-diagnosticos-20261013`. Sin commits, push,
frontend, despliegues ni migraciones fuera de pruebas.

## Entorno

PostgreSQL 15 / PostGIS existente, base `software_pa_test`; verificación explícita
de `current_database()` y ledger 028 antes de migrar. Los comandos de pytest
fijan `APP_ENV=test`, `DB_NAME=software_pa_test`,
`TEST_ALLOW_DATABASE=software_pa_test`, y conftest comprueba estos valores.
El código se montó en un contenedor temporal cuyo proceso es pytest, sin
iniciar servidor. Las pruebas ordinarias emplean rollback externo; las de
concurrencia/autenticación generan registros sintéticos en esa base aislada.

## Resultados ejecutados

| Ejecución | Aprobadas | Fallidas | Selección / observación |
|---|---:|---:|---|
| Diagnósticos iniciales | 26 | 0 | 33,71 s; posteriormente repetidas dentro de la versión final de 28 casos |
| Regresiones GIS y lecturas | 94 | 0 | 347,58 s; 10 deseleccionadas inicialmente |
| Diagnósticos finales, autenticación, concurrencia y health | 45 | 0 | 104,24 s; cubre 5 de las 10 inicialmente deseleccionadas |
| Contratos SQL 025, 026 y 029 | 3 contratos | 0 | 025/026 forzados a sólo lectura; 029 transaccional con rollback, prueba rechazo de UPDATE/DELETE incluso como owner |

Total final: **139 pruebas pytest únicas aprobadas** (94 + 45); no se suma la
ejecución inicial repetida. Ningún caso falló ni quedó marcado skipped. Las 5
deselecciones restantes corresponden a consolidación documental ajena al GIS.
No se ejecutó la suite completa, el catálogo documental completo ni una
instalación limpia de todas las migraciones en un segundo clúster.

Las ejecuciones pytest emitieron una advertencia de deprecación existente de
Starlette/httpx. No se modificaron dependencias para esta entrega.

Comprobaciones adicionales ejecutadas:

- Runner oficial: 001–028 con checksum intacto, aplicación atómica de 029 y
  segundo recorrido que verificó 001–029 sin aplicar cambios.
- AST idéntico al commit base para `normalize_parcel_number()`,
  `nucleus_criteria()` y `feature_identity()`.
- Comparación byte por byte de todas las migraciones 001–028 contra Git.
- OpenAPI guardado idéntico al generado por la aplicación final; mismos
  endpoints y mismas listas de campos obligatorios de los esquemas anteriores.
- `git diff --check` sin errores y checkout original limpio.

## Comandos pytest ejecutados

Ejecutados desde el checkout original, que conserva su configuración Compose.

```bash
docker compose run --rm --no-deps \
  -v /tmp/software-pa-gis-diagnosticos-20261013/backend:/app \
  -e APP_ENV=test -e DB_NAME=software_pa_test \
  -e TEST_ALLOW_DATABASE=software_pa_test -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -m pytest -p no:cacheprovider \
  --basetemp=/tmp/gis-diag-029-specific tests/test_gis_diagnostics_029.py -q
```

```bash
docker compose run --rm --no-deps \
  -v /tmp/software-pa-gis-diagnosticos-20261013/backend:/app \
  -e APP_ENV=test -e DB_NAME=software_pa_test \
  -e TEST_ALLOW_DATABASE=software_pa_test -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -m pytest -p no:cacheprovider \
  --basetemp=/tmp/gis-diag-029-regression \
  tests/test_parcel_gpkg_imports.py tests/test_nucleus_gpkg_imports.py \
  tests/test_gis_history_026.py tests/test_gis_history_regressions.py \
  tests/test_gis_confirmation_024.py tests/test_gis_preflight_024.py \
  tests/test_geospatial_imports.py tests/test_frontend_read_models.py \
  -k 'not test_parcel_import_preview_confirmation_and_idempotency and not test_import_requires_explicit_target_mapping and not test_two_connections_serialize_confirmation and not test_consolidation' -q
```

No había credenciales de pytest configuradas. Para la última ejecución se
generó un correo sintético único y una contraseña aleatoria en memoria; la
fixture existente crea la cuenta marcada como exclusiva de pytest. No se
imprimieron credenciales ni se modificaron cuentas preexistentes.

```bash
docker compose run --rm --no-deps \
  -v /tmp/software-pa-gis-diagnosticos-20261013/backend:/app \
  -e APP_ENV=test -e DB_NAME=software_pa_test \
  -e TEST_ALLOW_DATABASE=software_pa_test -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -c 'import os,secrets,sys; os.environ["TEST_ADMIN_EMAIL"]="diag029-"+secrets.token_hex(8)+"@example.invalid"; os.environ["TEST_ADMIN_PASSWORD"]="Qa1!"+secrets.token_hex(24); import pytest; raise SystemExit(pytest.main(sys.argv[1:]))' \
  -p no:cacheprovider --basetemp=/tmp/gis-diag-029-final \
  tests/test_gis_diagnostics_029.py \
  tests/test_geospatial_imports.py::test_parcel_import_preview_confirmation_and_idempotency \
  tests/test_geospatial_imports.py::test_import_requires_explicit_target_mapping \
  tests/test_gis_confirmation_024.py::test_two_connections_serialize_confirmation \
  tests/test_gis_concurrency_026.py tests/test_auth_rbac.py \
  tests/test_document_type_catalog.py::test_health_029 -q
```

## SQL y aplicación de la migración

Procedimiento y reversión: [MIGRACIONES.md](MIGRACIONES.md#diagnósticos-gis-029--aplicación-y-reversión-segura).
Se ejecutaron los siguientes contratos existentes/nuevo, sin aplicar
migraciones históricas de nuevo:

```bash
docker compose exec -T db sh -lc \
  'PGOPTIONS="-c default_transaction_read_only=on" psql -U "$POSTGRES_USER" -d software_pa_test -X -v ON_ERROR_STOP=1' \
  < /tmp/software-pa-gis-diagnosticos-20261013/backend/db/tests/025_conciliacion_gis_proyecto_contract.sql
docker compose exec -T db sh -lc \
  'PGOPTIONS="-c default_transaction_read_only=on" psql -U "$POSTGRES_USER" -d software_pa_test -X -v ON_ERROR_STOP=1' \
  < /tmp/software-pa-gis-diagnosticos-20261013/backend/db/tests/026_historia_cambios_gis_contract.sql
docker compose exec -T db sh -lc \
  'psql -U "$POSTGRES_USER" -d software_pa_test -X -v ON_ERROR_STOP=1' \
  < /tmp/software-pa-gis-diagnosticos-20261013/backend/db/tests/029_diagnosticos_conciliacion_gis_contract.sql
```

## Compatibilidad y límites

La migración se probó sobre una base existente con 028 y datos; no hace backfill
ni altera candidatos, decisiones o geometrías. Sólo añade diagnóstico nullable,
check e índice. La aplicación de producción queda pendiente de autorización y
revisión de volumen/bloqueo DDL. Ningún entorno de producción fue modificado.

La observación de ceros iniciales no genera candidatos ni equivalencias.
Diagnósticos antiguos no se reconstruyen; el mismo SHA conserva su identidad
y puede devolver staging anterior sin diagnóstico. La nueva versión se
registra sólo al producir resultados nuevos. El SQL valida el sobre JSON;
Pydantic aplica el contrato completo tipado. La validación inicial no incluyó
benchmark de GPKG grandes; el test de páginas comprueba consultas constantes.
La revisión final posterior incorpora un benchmark sintético de CPU, descrito
en la siguiente sección, que no equivale a medir staging completo de GPKG.

La cuenta y las entidades sintéticas de pruebas con commits entre conexiones
permanecen sujetas a la limpieza lógica de las fixtures. No se realizaron
resets, bajas de importaciones ni borrados físicos.

Contrato para frontend: [CONTRATO_DIAGNOSTICOS_GIS_SSALFER.md](CONTRATO_DIAGNOSTICOS_GIS_SSALFER.md).

## Revisión final y correcciones puntuales

Se conserva la migración 029 byte por byte y su SHA-256 original
`284f8a26fc5d1215f21055657a5171431d1df4ee8d0151dc58071e38731e9716`.
No se ejecutaron migraciones durante esta revisión.

Correcciones: campo técnico de origen tomado de `record.mapeo.id_destino`,
lookup de columnas construido una vez por diagnóstico y normalización de
destinos compartida entre columnas exclusivamente para observar variantes.
Los cuatro mapeos permitidos se prueban en staging y reconciliación de núcleos
y parcelas; sus candidatos y clasificaciones se conservan.

El contrato SQL 029 ahora crea siempre proyecto, importación, feature, ciclo y
resultado sintéticos. No selecciona resultados históricos ni omite la prueba
si no hay ninguno: sólo requiere el administrador bootstrap de pruebas.
Comprueba que UPDATE que intenta cambiar el mensaje y DELETE son rechazados
por el trigger como owner, y que el diagnóstico original sigue intacto.
Toda la fixture se revierte. El contrato reforzado se ejecutó satisfactoriamente
en `software_pa_test`, junto con los contratos 025/026 en sólo lectura.

Resultado final: **148 pruebas aprobadas, 0 fallidas, 5 deseleccionadas**,
504,88 segundos. Las deselecciones son consolidación documental fuera del GIS.
La suite diagnóstica incluye 37 casos; sus pruebas nuevas verifican también
cero SQL durante cada diagnóstico, reutilización del universo y conteo constante
de consultas en páginas de 1/20 features. Se mantienen las mismas advertencias
de deprecación de Starlette/httpx, sin cambio de dependencias.

Incidencias corregidas antes de esta corrida final:

- Ocho aserciones nuevas comparaban también estado/fecha de cierre del ciclo;
  se ajustaron para verificar el cierre permitido y preservar los demás datos.
- Una aserción de carga esperaba dos consultas, pero la relación `selectin`
  existente añade una tercera en bloque. Se conservó ese comportamiento y se
  verificó separadamente ausencia de carga nuclear duplicada y SQL por feature.
- El primer arranque del benchmark necesitó incluir el directorio backend en
  la ruta de importación. La ejecución completa posterior terminó correctamente.

Verificaciones finales ejecutadas: AST idéntico para normalización,
`nucleus_criteria`, `feature_identity`, decisiones y confirmación; prefijo de
`build_candidates` anterior al diagnóstico idéntico a Entrega 1; migraciones
001–028 intactas; mismo checksum 029 en archivo y ledger; OpenAPI idéntico al
código final y sin cambios adicionales frente a Entrega 1. Comparado con el
commit auditado, conserva endpoints, propiedades previas y campos obligatorios.
Checkout original limpio, sin commits/push ni cambios de frontend.

[Benchmark, límites y muestras](BENCHMARK_DIAGNOSTICOS_GIS_029.md).
Los diagnósticos ya registrados con la etiqueta técnica anterior no se
reescriben. Las mediciones de CPU son orientativas y no incluyen GDAL/SQL.

Comando de la ejecución final:

```bash
docker compose run --rm --no-deps \
  -v /tmp/software-pa-gis-diagnosticos-20261013/backend:/app \
  -e APP_ENV=test -e DB_NAME=software_pa_test \
  -e TEST_ALLOW_DATABASE=software_pa_test -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -c 'import os,secrets,sys; os.environ["TEST_ADMIN_EMAIL"]="gis029-review-"+secrets.token_hex(8)+"@example.invalid"; os.environ["TEST_ADMIN_PASSWORD"]="Qa1!"+secrets.token_hex(24); import pytest; raise SystemExit(pytest.main(sys.argv[1:]))' \
  -p no:cacheprovider --basetemp=/tmp/gis029-final-review-regression \
  tests/test_gis_diagnostics_029.py tests/test_parcel_gpkg_imports.py \
  tests/test_nucleus_gpkg_imports.py tests/test_gis_history_026.py \
  tests/test_gis_history_regressions.py tests/test_gis_confirmation_024.py \
  tests/test_gis_preflight_024.py tests/test_geospatial_imports.py \
  tests/test_frontend_read_models.py tests/test_gis_concurrency_026.py \
  tests/test_auth_rbac.py tests/test_document_type_catalog.py::test_health_029 \
  -k 'not test_consolidation' -q
```
