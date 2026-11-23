#!/bin/bash
set -euo pipefail
export PATH=/usr/lib/postgresql/15/bin:$PATH
export PYTHONHOME=/qa-python PYTHONDONTWRITEBYTECODE=1
work=$(mktemp -d /tmp/pa5-pr8-db.XXXXXX)
started=no
cleanup() {
 code=$?
 trap - EXIT
 if [[ "$started" == yes ]]; then pg_ctl -D "$work/data" -m fast -w stop >/dev/null 2>&1 || true; fi
 for f in "$work"/*.log "$work"/ledger*.json "$work"/function-*.json; do
  [[ -f "$f" && "${f##*/}" != server-private.log ]] || continue
  printf '\nEVIDENCE_FILE %s\n' "${f##*/}"; cat "$f"
 done
 exit "$code"
}
trap cleanup EXIT
stage() {
 local label=$1;shift
 local status=0
 "$@" > "$work/$label.log" 2>&1 || status=$?
 printf 'STAGE %s EXIT %s\n' "$label" "$status"
 [[ "$status" == 0 ]] || exit "$status"
}
mkdir "$work/socket"
owner_password=$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')
export DB_RUNTIME_PASSWORD=$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')
printf '%s\n' "$owner_password" > "$work/owner-password"
chmod 600 "$work/owner-password"
stage initdb initdb -D "$work/data" -U qa_owner --auth-local=scram-sha-256 --auth-host=reject --pwfile="$work/owner-password" --no-locale
stage start pg_ctl -D "$work/data" -l "$work/server-private.log" -o "-F -h '' -k $work/socket -c listen_addresses='' -c cluster_name=${PA5_QA_CLUSTER:-pa5-pr8-f715b55} -c shared_buffers=64MB -c max_connections=15" -w start
started=yes
export PGHOST="$work/socket" PGUSER=qa_owner PGPASSWORD="$owner_password"
unset owner_password
export PGOPTIONS='-c statement_timeout=120000 -c lock_timeout=5000'
stage createdb createdb software_pa_test
export PGDATABASE=software_pa_test POSTGRES_USER=qa_owner POSTGRES_DB=software_pa_test DB_RUNTIME_USER=qa_runtime MIGRATIONS_DIR=/source/backend/db/migrations
stage versions psql -X -At -v ON_ERROR_STOP=1 -c "SELECT current_database(),current_setting('server_version'),current_setting('cluster_name');"
stage bootstrap bash /source/backend/db/init/001_bootstrap_roles.sh
