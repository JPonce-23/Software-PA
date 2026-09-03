#!/bin/bash
set -euo pipefail

# Uso para una base existente, después de aplicar el baseline 001:
#   set -a; source .env; set +a
#   docker compose up -d --force-recreate db
#   backend/scripts/utils/set_runtime_credentials.sh
# El contenedor recreado recibe DB_RUNTIME_* sin reinicializar PGDATA.

: "${POSTGRES_ADMIN_USER:?POSTGRES_ADMIN_USER es obligatorio}"
: "${DB_NAME:?DB_NAME es obligatorio}"
: "${DB_RUNTIME_USER:?DB_RUNTIME_USER es obligatorio}"
: "${DB_RUNTIME_PASSWORD:?DB_RUNTIME_PASSWORD es obligatorio}"

if [[ ! "$POSTGRES_ADMIN_USER" =~ ^[a-z_][a-z0-9_]{0,62}$ ]]; then
    echo "POSTGRES_ADMIN_USER no es un identificador PostgreSQL válido" >&2
    exit 1
fi
if [[ ! "$DB_RUNTIME_USER" =~ ^[a-z_][a-z0-9_]{0,62}$ ]]; then
    echo "DB_RUNTIME_USER no es un identificador PostgreSQL válido" >&2
    exit 1
fi

# En volúmenes existentes, cambiar .env no actualiza el entorno del contenedor.
# Fallar aquí evita provisionar silenciosamente credenciales anteriores.
container_owner_user=$(docker compose exec -T db sh -eu -c 'printf %s "$POSTGRES_USER"')
container_runtime_user=$(docker compose exec -T db sh -eu -c 'printf %s "$DB_RUNTIME_USER"')
container_runtime_password_hash=$(
    docker compose exec -T db sh -eu -c \
        'printf %s "$DB_RUNTIME_PASSWORD" | sha256sum | cut -d" " -f1'
)
host_runtime_password_hash=$(printf %s "$DB_RUNTIME_PASSWORD" | sha256sum | cut -d" " -f1)
if [[ "$container_owner_user" != "$POSTGRES_ADMIN_USER"
      || "$container_runtime_user" != "$DB_RUNTIME_USER"
      || "$container_runtime_password_hash" != "$host_runtime_password_hash" ]]; then
    echo "El contenedor db no contiene las credenciales actuales; ejecute docker compose up -d --force-recreate db" >&2
    exit 1
fi

docker compose exec -T db psql -X -v ON_ERROR_STOP=1 \
    --username "$POSTGRES_ADMIN_USER" --dbname "$DB_NAME" <<'EOSQL'
\set QUIET on
\getenv runtime_user DB_RUNTIME_USER
\getenv runtime_password DB_RUNTIME_PASSWORD

DO $preflight$
BEGIN
    IF to_regclass('public.schema_migrations') IS NULL
       OR NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '001') THEN
        RAISE EXCEPTION 'La provisión runtime requiere el baseline 001';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'software_pa_app') THEN
        RAISE EXCEPTION 'Falta el rol NOLOGIN software_pa_app creado por bootstrap';
    END IF;
END
$preflight$;

SELECT format('CREATE ROLE %I', :'runtime_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'runtime_user')
\gexec

SELECT set_config('app.provision_runtime_user', :'runtime_user', false) AS provisioned_runtime
\gset

DO $ownership$
DECLARE
    v_runtime name := current_setting('app.provision_runtime_user')::name;
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_database d JOIN pg_roles r ON r.oid = d.datdba
        WHERE r.rolname = v_runtime
    ) OR EXISTS (
        SELECT 1 FROM pg_namespace n JOIN pg_roles r ON r.oid = n.nspowner
        WHERE r.rolname = v_runtime
    ) OR EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_roles r ON r.oid = c.relowner
        WHERE r.rolname = v_runtime
    ) THEN
        RAISE EXCEPTION 'El LOGIN runtime % posee objetos; reasigne ownership antes de provisionar', v_runtime;
    END IF;
END
$ownership$;

SELECT format(
    'ALTER ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L',
    :'runtime_user', :'runtime_password'
)
\gexec

-- El LOGIN hereda sólo el rol contractual. Se eliminan membresías anteriores.
SELECT format('REVOKE %I FROM %I', parent.rolname, :'runtime_user')
FROM pg_auth_members membership
JOIN pg_roles parent ON parent.oid = membership.roleid
JOIN pg_roles member ON member.oid = membership.member
WHERE member.rolname = :'runtime_user'
  AND parent.rolname <> 'software_pa_app'
\gexec

SELECT format('GRANT software_pa_app TO %I', :'runtime_user')
\gexec

-- Elimina privilegios directos: todo DML permitido debe heredarse del NOLOGIN.
SELECT format('REVOKE ALL PRIVILEGES ON SCHEMA public FROM %I', :'runtime_user')
\gexec
SELECT format('REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM %I', :'runtime_user')
\gexec
SELECT format('REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM %I', :'runtime_user')
\gexec

\unset runtime_password
EOSQL

# Fuerza autenticación TCP con la misma identidad que utilizará FastAPI.
docker compose exec -T -e RUNTIME_TARGET_DB="$DB_NAME" db sh -eu -c '
    PGPASSWORD="$DB_RUNTIME_PASSWORD" psql -X -v ON_ERROR_STOP=1 \
        -h 127.0.0.1 -U "$DB_RUNTIME_USER" -d "$RUNTIME_TARGET_DB" \
        -At -c "SELECT current_user" >/dev/null
'

echo "Credenciales runtime provisionadas y conexión TCP validada (contraseña no mostrada)."
