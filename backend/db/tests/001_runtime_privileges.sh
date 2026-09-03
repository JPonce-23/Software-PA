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

docker compose exec -T \
    -e RUNTIME_TEST_DB="$DB_NAME" \
    -e EXPECTED_OWNER_USER="$POSTGRES_ADMIN_USER" \
    db sh -eu -c '
        PGPASSWORD="$DB_RUNTIME_PASSWORD" exec psql -X -v ON_ERROR_STOP=1 \
            -h 127.0.0.1 -U "$DB_RUNTIME_USER" -d "$RUNTIME_TEST_DB" \
            --set=expected_runtime_user="$DB_RUNTIME_USER" \
            --set=expected_owner_user="$EXPECTED_OWNER_USER" -f -
    ' < backend/db/tests/001_runtime_privileges.sql

echo "CONTRATO ACL/RUNTIME BASELINE V1: OK"
