# Migraciones y credenciales PostgreSQL

> Flujo vigente: Baseline V1, versión `001`. Las migraciones futuras comienzan en `002`.

## Identidades PostgreSQL

- `POSTGRES_ADMIN_USER`/`POSTGRES_ADMIN_PASSWORD`: owner usado sólo para bootstrap, migraciones y tareas administrativas.
- `software_pa_app`: rol `NOLOGIN` con el contrato DML de la aplicación.
- `DB_RUNTIME_USER`/`DB_RUNTIME_PASSWORD`: LOGIN de FastAPI; por defecto `pa_runtime`, miembro únicamente de `software_pa_app`.

Las contraseñas llegan por variables de entorno y no se incluyen en SQL. El baseline crea objetos funcionales y ACL para roles ya provisionados; `backend/db/init/001_bootstrap_roles.sh` administra los roles por separado.

## Instalación limpia

Con un PGDATA vacío:

```bash
cp .env.example .env
# Sustituir localmente todos los placeholders y cargar el entorno.
set -a; source .env; set +a
docker compose up -d db
```

El entrypoint ejecuta, en orden:

1. `backend/db/init/001_bootstrap_roles.sh`;
2. `backend/db/init/002_apply_migrations.sh`;
3. `backend/scripts/run_migrations.sh` sobre `backend/db/migrations/001_baseline_v1.sql`.

Después se carga el catálogo territorial y se crea el administrador inicial:

```bash
docker compose exec -T db sh -lc \
  'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f -' \
  < backend/db/fixtures/001_catalogo_territorial_inegi.sql

docker compose run --rm --no-deps \
  -e ADMIN_DATABASE_MODE=owner \
  -e POSTGRES_ADMIN_USER \
  -e POSTGRES_ADMIN_PASSWORD \
  -e ADMIN_EMAIL \
  -e ADMIN_NOMBRE \
  -e ADMIN_APELLIDO_PATERNO \
  -e ADMIN_APELLIDO_MATERNO \
  backend python scripts/create_admin.py
```

El seed funcional es opcional y exige un administrador activo:

```bash
SEED_OBJECTIVE_CONFIRM=1 docker compose run --rm --no-deps \
  -e SEED_OBJECTIVE_CONFIRM backend python scripts/seed_objective_demo.py
```

## Runner y checksums

`backend/scripts/run_migrations.sh`:

1. selecciona archivos `NNN_nombre.sql`;
2. calcula SHA-256;
3. aplica cada archivo con `psql --single-transaction`;
4. registra `version`, `nombre`, `checksum_sha256` y `aplicada_en`;
5. rechaza un archivo ya aplicado cuyo checksum haya cambiado.

La tabla de control es:

```text
schema_migrations(
  version varchar(3) primary key,
  nombre varchar(200) not null,
  checksum_sha256 char(64) not null,
  aplicada_en timestamptz not null default now()
)
```

No se modifica una migración aplicada. El siguiente cambio de esquema debe ser `002_nombre.sql`.

Ejecución manual como owner:

```bash
set -a; source .env; set +a
POSTGRES_DB="$DB_NAME" POSTGRES_USER="$POSTGRES_ADMIN_USER" \
  DB_HOST=127.0.0.1 DB_PORT="${DB_HOST_PORT:-5433}" \
  PGPASSWORD="$POSTGRES_ADMIN_PASSWORD" \
  backend/scripts/run_migrations.sh
```

## Base existente y credenciales runtime

El entrypoint de PostgreSQL sólo corre sobre PGDATA vacío. Para una base que ya contiene Baseline V1:

```bash
set -a; source .env; set +a
docker compose up -d --force-recreate db
backend/scripts/utils/set_runtime_credentials.sh
```

El script exige `schema_migrations.version='001'`, fuerza atributos no administrativos, elimina membresías y privilegios directos del LOGIN, concede únicamente `software_pa_app` y comprueba autenticación TCP sin imprimir la contraseña.

## Validación

Usar siempre una base aislada y explícita, nunca una base con datos que deban preservarse:

```bash
docker compose exec -T db sh -lc \
  'psql -U "$POSTGRES_USER" -d software_pa_baseline_test -X -v ON_ERROR_STOP=1' \
  < backend/db/tests/001_baseline_v1_contract.sql

DB_NAME=software_pa_baseline_test backend/db/tests/001_runtime_privileges.sh

docker compose run --rm --no-deps \
  -e APP_ENV=test \
  -e DB_NAME=software_pa_baseline_test \
  -e TEST_ALLOW_DATABASE=software_pa_baseline_test \
  -e TEST_ADMIN_EMAIL \
  -e TEST_ADMIN_PASSWORD \
  backend pytest -q
```

El contrato runtime exige `SELECT/INSERT/UPDATE`, prohíbe owner, DDL, `DELETE`, `TRUNCATE` y escritura en `schema_migrations`.

## Historia anterior

Las migraciones incrementales 001–039 dejaron de ser el mecanismo de instalación al adoptar Baseline V1. Git conserva esa historia; no se reaplica ni se concatena sobre una base nueva. Los documentos bajo `docs/historico/`, `docs/propuestas/` y `docs/evaluaciones/` son evidencia histórica, no instrucciones operativas.
