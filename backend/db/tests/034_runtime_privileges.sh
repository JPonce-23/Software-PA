#!/bin/bash
set -euo pipefail

: "${POSTGRES_ADMIN_USER:?POSTGRES_ADMIN_USER es obligatorio}"
: "${DB_NAME:?DB_NAME es obligatorio}"
: "${DB_RUNTIME_USER:?DB_RUNTIME_USER es obligatorio}"
: "${DB_RUNTIME_PASSWORD:?DB_RUNTIME_PASSWORD es obligatorio}"

for role_name in "$POSTGRES_ADMIN_USER" "$DB_RUNTIME_USER"; do
    if [[ ! "$role_name" =~ ^[a-z_][a-z0-9_]{0,62}$ ]]; then
        echo "Nombre de rol PostgreSQL inválido" >&2
        exit 1
    fi
done

probe_table="runtime_privilege_probe_034_$$"

cleanup() {
    docker compose exec -T db psql -X -v ON_ERROR_STOP=1 \
        -U "$POSTGRES_ADMIN_USER" -d "$DB_NAME" \
        --set=probe_table="$probe_table" <<'EOSQL' >/dev/null 2>&1 || true
DROP TABLE IF EXISTS public.:"probe_table";
EOSQL
}
trap cleanup EXIT

# El owner real crea una tabla futura después de 034. No hay GRANT explícito:
# los permisos deben provenir de ALTER DEFAULT PRIVILEGES.
docker compose exec -T db psql -X -v ON_ERROR_STOP=1 \
    -U "$POSTGRES_ADMIN_USER" -d "$DB_NAME" \
    --set=probe_table="$probe_table" <<'EOSQL'
CREATE TABLE public.:"probe_table" (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    valor text NOT NULL
);
EOSQL

# Contrato desde una conexión TCP autenticada realmente como el LOGIN runtime.
docker compose exec -T \
    -e RUNTIME_TEST_DB="$DB_NAME" \
    -e RUNTIME_PROBE_TABLE="$probe_table" \
    -e EXPECTED_OWNER_USER="$POSTGRES_ADMIN_USER" \
    db sh -eu -c '
        PGPASSWORD="$DB_RUNTIME_PASSWORD" exec psql -X -v ON_ERROR_STOP=1 \
            -h 127.0.0.1 -U "$DB_RUNTIME_USER" -d "$RUNTIME_TEST_DB" \
            --set=expected_runtime_user="$DB_RUNTIME_USER" \
            --set=expected_owner_user="$EXPECTED_OWNER_USER" \
            --set=probe_table="$RUNTIME_PROBE_TABLE" -f -
    ' < backend/db/tests/034_runtime_privileges.sql

# Evidencia automatizada de owner y defaults del usuario de migraciones.
docker compose exec -T db psql -X -v ON_ERROR_STOP=1 \
    -U "$POSTGRES_ADMIN_USER" -d "$DB_NAME" \
    --set=runtime_user="$DB_RUNTIME_USER" \
    --set=probe_table="$probe_table" \
    -f - < backend/db/tests/034_default_privileges.sql

echo "CONTRATO AUTOMATIZADO 034 OWNER/RUNTIME: OK"
