#!/usr/bin/env bash
set -euo pipefail

MIGRATIONS_DIR="${MIGRATIONS_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../db/migrations" && pwd)}"
PSQL_BIN="${PSQL_BIN:-psql}"

if [[ ! -d "$MIGRATIONS_DIR" ]]; then
    echo "Directorio de migraciones inexistente: $MIGRATIONS_DIR" >&2
    exit 1
fi

connection=()
if [[ -n "${DATABASE_URL:-}" ]]; then
    connection+=("$DATABASE_URL")
else
    : "${POSTGRES_DB:=${DB_NAME:-}}"
    : "${POSTGRES_USER:=${POSTGRES_ADMIN_USER:-}}"
    : "${POSTGRES_DB:?POSTGRES_DB o DB_NAME es obligatorio}"
    : "${POSTGRES_USER:?POSTGRES_USER o POSTGRES_ADMIN_USER es obligatorio}"
    connection+=(--username "$POSTGRES_USER" --dbname "$POSTGRES_DB")
    [[ -n "${DB_HOST:-}" ]] && connection+=(--host "$DB_HOST")
    [[ -n "${DB_PORT:-}" ]] && connection+=(--port "$DB_PORT")
fi

shopt -s nullglob
files=("$MIGRATIONS_DIR"/[0-9][0-9][0-9]_*.sql)
if ((${#files[@]} == 0)); then
    echo "No hay migraciones NNN_*.sql en $MIGRATIONS_DIR" >&2
    exit 1
fi

for file in "${files[@]}"; do
    filename="$(basename "$file")"
    if [[ ! "$filename" =~ ^([0-9]{3})_([a-z0-9_]+)\.sql$ ]]; then
        echo "Nombre de migración inválido: $filename" >&2
        exit 1
    fi
    version="${BASH_REMATCH[1]}"
    name="${BASH_REMATCH[2]}"
    checksum="$(sha256sum "$file" | awk '{print $1}')"

    applied_checksum="$($PSQL_BIN "${connection[@]}" -X -Atq -v ON_ERROR_STOP=1 \
        -c "SELECT CASE WHEN to_regclass('public.schema_migrations') IS NULL THEN NULL ELSE (SELECT checksum_sha256 FROM public.schema_migrations WHERE version='$version') END" \
        2>/dev/null || true)"

    if [[ -n "$applied_checksum" ]]; then
        if [[ "$applied_checksum" != "$checksum" ]]; then
            echo "Migración $version modificada después de aplicarse: $filename" >&2
            echo "registrado=$applied_checksum actual=$checksum" >&2
            exit 1
        fi
        echo "Migración $version verificada (checksum sin cambios)."
        continue
    fi

    "$PSQL_BIN" "${connection[@]}" -X -v ON_ERROR_STOP=1 --single-transaction \
        -f "$file" \
        -c "INSERT INTO public.schema_migrations(version,nombre,checksum_sha256) VALUES ('$version','$name','$checksum')"
    echo "Migración $version aplicada: $filename"
done
