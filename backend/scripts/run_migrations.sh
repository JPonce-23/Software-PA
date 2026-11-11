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

# BEGIN HISTORY GUARD: exercised directly by the offline tests.
# psql failures remain fatal. Never print raw diagnostics when credentials may
# be present; preserve the exit code and the caller's fixed phase diagnostic.
psql_checked() {
    local output status key sensitive=0
    if output="$("$PSQL_BIN" "$@" 2>&1)"; then
        printf '%s\n' "$output"
        return 0
    else
        status=$?
    fi
    while IFS= read -r key; do
        case "$key" in
            *PASSWORD*|*SECRET*|*TOKEN*|DATABASE_URL|PGPASSFILE|PGSERVICE|PGSERVICEFILE)
                [[ -z "${!key:-}" ]] || sensitive=1 ;;
        esac
    done < <(compgen -e)
    printf 'PSQL_ERROR exit=%s\n' "$status" >&2
    if [[ "$sensitive" == 0 ]]; then
        printf '%s\n' "$output" >&2
    fi
    return "$status"
}
validate_migration_history() {
    local exists objects rows v n h extra expected_file expected_name expected_hash
    local seen=0
    if ! exists="$(psql_checked "${connection[@]}" -X -Atq -v ON_ERROR_STOP=1 -c "SELECT CASE WHEN to_regclass('public.schema_migrations') IS NULL THEN 'missing' ELSE 'present' END")"; then
        echo 'HISTORIAL_NO_VERIFICADO: conexión, permisos o consulta fallida' >&2; return 1
    fi
    case "$exists" in
    missing)
        if ! objects="$(psql_checked "${connection[@]}" -X -Atq -v ON_ERROR_STOP=1 -c "SELECT count(*) FROM (SELECT c.oid FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S','f','c') AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_class'::regclass AND d.objid=c.oid AND d.deptype='e') UNION ALL SELECT p.oid FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_proc'::regclass AND d.objid=p.oid AND d.deptype='e') UNION ALL SELECT t.oid FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='public' AND t.typtype IN ('e','d') AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_type'::regclass AND d.objid=t.oid AND d.deptype='e')) user_objects")"; then
            echo 'BASE_NUEVA_NO_VERIFICADA' >&2; return 1
        fi
        [[ "$objects" == 0 ]] || { echo 'HISTORIAL_AUSENTE_CON_OBJETOS: requiere revisión' >&2; return 1; }
        HISTORY_READY=0
        ;;
    present)
        if ! rows="$(psql_checked "${connection[@]}" -X -Atq -v ON_ERROR_STOP=1 -c "SELECT coalesce(version::text,'<NULL>') || '|' || coalesce(nombre,'<NULL>') || '|' || coalesce(checksum_sha256,'<NULL>') FROM public.schema_migrations ORDER BY version")"; then
            echo 'HISTORIAL_ILEGIBLE: permisos, estructura o consulta fallida' >&2; return 1
        fi
        [[ -n "$rows" ]] || { echo 'HISTORIAL_VACIO_REQUIERE_REVISION' >&2; return 1; }
        while IFS='|' read -r v n h extra; do
            ((seen+=1))
            [[ "$v" =~ ^[0-9]{3}$ && "$v" == "$(printf '%03d' "$seen")" && -z "$extra" && "$h" =~ ^[0-9a-f]{64}$ ]] || { echo 'HISTORIAL_INCONSISTENTE: hueco, duplicado, versión o checksum inválido' >&2; return 1; }
            local matches=("$MIGRATIONS_DIR"/"$v"_*.sql)
            [[ ${#matches[@]} == 1 && -f "${matches[0]}" ]] || { echo 'VERSION_SIN_ARCHIVO_CANONICO_UNICO' >&2; return 1; }
            expected_file="${matches[0]}"; expected_name="${expected_file##*/}"; expected_name="${expected_name:4:-4}"
            if ! expected_hash="$(sha256sum "$expected_file")"; then echo 'CHECKSUM_LOCAL_NO_VERIFICADO' >&2; return 1; fi
            expected_hash="${expected_hash%% *}"
            [[ "$n" == "$expected_name" && "$h" == "$expected_hash" ]] || { echo 'HISTORIAL_NO_COINCIDE_CON_CANONICOS' >&2; return 1; }
        done <<< "$rows"
        HISTORY_READY=1
        ;;
    *) echo 'RESPUESTA_HISTORIAL_INVALIDA' >&2; return 1 ;;
    esac
}
read_applied_checksum() {
    local version="$1" expected_name="$2" row count stored_name stored_hash extra
    [[ "$HISTORY_READY" == 1 ]] || { [[ "$version" == 001 ]] || return 1; return 0; }
    if ! row="$(psql_checked "${connection[@]}" -X -Atq -F '|' -v ON_ERROR_STOP=1 -c "SELECT count(*),coalesce(min(nombre),''),coalesce(min(checksum_sha256),'') FROM public.schema_migrations WHERE version='$version'")"; then
        echo 'CHECKSUM_NO_VERIFICADO: conexión, permisos o consulta fallida' >&2; return 1
    fi
    IFS='|' read -r count stored_name stored_hash extra <<< "$row"
    [[ -z "$extra" && "$row" != *$'\n'* ]] || { echo 'RESPUESTA_CHECKSUM_INVALIDA' >&2; return 1; }
    case "$count" in
    0) [[ -z "$stored_name$stored_hash" ]] || return 1 ;;
    1) [[ "$stored_name" == "$expected_name" && "$stored_hash" =~ ^[0-9a-f]{64}$ ]] || { echo 'REGISTRO_CHECKSUM_INVALIDO' >&2; return 1; }; printf '%s\n' "$stored_hash" ;;
    *) echo 'HISTORIAL_DUPLICADO_O_CONTEO_INVALIDO' >&2; return 1 ;;
    esac
}

# END HISTORY GUARD
validate_migration_history

for file in "${files[@]}"; do
    [[ -f "$file" ]] || continue
    filename="$(basename "$file")"
    if [[ ! "$filename" =~ ^([0-9]{3})_([a-z0-9_]+)\.sql$ ]]; then
        echo "Nombre de migración inválido: $filename" >&2
        exit 1
    fi
    version="${BASH_REMATCH[1]}"
    name="${BASH_REMATCH[2]}"
    checksum="$(sha256sum "$file" | awk '{print $1}')"

    if ! applied_checksum="$(read_applied_checksum "$version" "$name")"; then
        echo "No se ejecuta la migración $version: historial no verificado" >&2
        exit 1
    fi

    if [[ -n "$applied_checksum" ]]; then
        if [[ "$applied_checksum" != "$checksum" ]]; then
            echo "Migración $version modificada después de aplicarse: $filename" >&2
            echo "registrado=$applied_checksum actual=$checksum" >&2
            exit 1
        fi
        echo "Migración $version verificada (checksum sin cambios)."
        continue
    fi

    psql_checked "${connection[@]}" -X -v ON_ERROR_STOP=1 --single-transaction \
        -f "$file" \
        -c "INSERT INTO public.schema_migrations(version,nombre,checksum_sha256) VALUES ('$version','$name','$checksum')"
    HISTORY_READY=1
    echo "Migración $version aplicada: $filename"
done
