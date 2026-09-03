#!/usr/bin/env bash
set -euo pipefail

# PostgreSQL ejecuta este bootstrap sólo al inicializar un PGDATA vacío.
# Las credenciales siempre llegan por variables de entorno.
: "${POSTGRES_USER:?POSTGRES_USER es obligatorio}"
: "${POSTGRES_DB:?POSTGRES_DB es obligatorio}"
: "${DB_RUNTIME_USER:?DB_RUNTIME_USER es obligatorio}"
: "${DB_RUNTIME_PASSWORD:?DB_RUNTIME_PASSWORD es obligatorio}"

if [[ ! "$DB_RUNTIME_USER" =~ ^[a-z_][a-z0-9_]{0,62}$ ]]; then
    echo "DB_RUNTIME_USER no es un identificador PostgreSQL válido" >&2
    exit 1
fi

psql -X -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'EOSQL'
\set QUIET on
\getenv runtime_user DB_RUNTIME_USER
\getenv runtime_password DB_RUNTIME_PASSWORD

DO $role$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'software_pa_app') THEN
        CREATE ROLE software_pa_app;
    END IF;
END
$role$;

ALTER ROLE software_pa_app
    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

SELECT format('CREATE ROLE %I', :'runtime_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'runtime_user')
\gexec

SELECT format(
    'ALTER ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L',
    :'runtime_user', :'runtime_password'
)
\gexec

SELECT format('GRANT software_pa_app TO %I', :'runtime_user')
\gexec
\unset runtime_password
EOSQL

echo "Roles de SOFTWARE-PA provisionados sin versionar contraseñas."
