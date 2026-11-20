#!/bin/bash
set -euo pipefail
case "${PA5_QA_MODE:-}" in upgrade|fresh) ;; *) exit 2 ;; esac
export PA5_QA_CLUSTER="pa5-pr8-035-$PA5_QA_MODE"
source /qa/database-common.sh
# Used after the existing shared init/bootstrap, only on a fresh private cluster.
if [[ "$PA5_QA_MODE" == upgrade ]]; then
 mkdir "$work/migrations34"
 cp /source/backend/db/migrations/0[0-2][0-9]_*.sql /source/backend/db/migrations/03[0-4]_*.sql "$work/migrations34/"
 export MIGRATIONS_DIR="$work/migrations34"
 stage migrate-034 bash /source/backend/scripts/run_migrations.sh
 stage ledger-034 env PA5_LEDGER_MAX_VERSION=34 /qa-python/bin/python3 /qa/ledger.py "$work/ledger-034.json"
 stage seed-existing psql -X -v ON_ERROR_STOP=1 -f /qa/seed.sql
 # Exactly the same strict regressions will be used after applying 035.
 for case in audit-persistence audit-origin; do
  status=0
  env PGUSER=qa_runtime PGPASSWORD="$DB_RUNTIME_PASSWORD" psql -X -v ON_ERROR_STOP=1 -f "/qa/$case.sql" > "$work/red-$case.log" 2>&1 || status=$?
  printf 'EXPECTED_RED %s EXIT %s\n' "$case" "$status"
  [[ "$status" == 3 ]] || exit 91
 done
 grep -F 'AUDIT_035_PERSISTENCE_MISMATCH public=0 temp=2' "$work/red-audit-persistence.log" >/dev/null
 grep -F 'AUDIT_035_FORGED_TRIGGER_ACCEPTED' "$work/red-audit-origin.log" >/dev/null
 stage metadata-before /qa-python/bin/python3 /qa/metadata035.py "$work/function-before.json"
 export MIGRATIONS_DIR=/source/backend/db/migrations
 stage upgrade-035 bash /source/backend/scripts/run_migrations.sh
 stage upgrade-proof /qa-python/bin/python3 - "$work/upgrade-035.log" <<'PY'
from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text()
assert re.findall(r'^Migración (\d{3}) verificada',s,re.M)==[f'{n:03}' for n in range(1,35)]
assert re.findall(r'^Migración (\d{3}) aplicada:',s,re.M)==['035']
print('AUDIT_035_UPGRADE_34_VERIFIED_ONLY_035_APPLIED_OK')
PY
 stage metadata-preserved /qa-python/bin/python3 /qa/metadata035.py "$work/function-after.json" "$work/function-before.json"
elif [[ "$PA5_QA_MODE" == fresh ]]; then
 stage install-035 bash /source/backend/scripts/run_migrations.sh
 stage seed-new psql -X -v ON_ERROR_STOP=1 -f /qa/seed.sql
 stage metadata-new /qa-python/bin/python3 /qa/metadata035.py "$work/function-after.json"
else
 echo 'Invalid 035 scenario' >&2;exit 2
fi
export PA5_LEDGER_MAX_VERSION=35
stage ledger-035 /qa-python/bin/python3 /qa/ledger.py "$work/ledger-035.json"
stage repeat-035 bash /source/backend/scripts/run_migrations.sh
stage repeat-proof-035 /qa-python/bin/python3 - "$work/repeat-035.log" <<'PY'
from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text()
assert re.findall(r'^Migración (\d{3}) verificada \(checksum sin cambios\)\.$',s,re.M)==[f'{n:03}' for n in range(1,36)]
assert ' aplicada:' not in s
print('AUDIT_035_35_VERIFIED_ZERO_REAPPLIED_OK')
PY
for case in audit-persistence audit-origin audit-auth; do
 stage "green-$case" env PGUSER=qa_runtime PGPASSWORD="$DB_RUNTIME_PASSWORD" psql -X -v ON_ERROR_STOP=1 -f "/qa/$case.sql"
done
stage runtime-existing env PGUSER=qa_runtime PGPASSWORD="$DB_RUNTIME_PASSWORD" psql -X -v ON_ERROR_STOP=1 --set=expected_runtime_user=qa_runtime --set=expected_owner_user=qa_owner -f /source/backend/db/tests/001_runtime_privileges.sql
stage runtime-negative env PGUSER=qa_runtime PGPASSWORD="$DB_RUNTIME_PASSWORD" psql -X -v ON_ERROR_STOP=1 -f /qa/negative.sql
stage trigger034-runtime env PGUSER=qa_runtime PGPASSWORD="$DB_RUNTIME_PASSWORD" psql -X -v ON_ERROR_STOP=1 -f /qa/034.sql
stage trigger034-owner psql -X -v ON_ERROR_STOP=1 -f /qa/034-owner.sql
stage ledger-final /qa-python/bin/python3 /qa/ledger.py "$work/ledger-final.json"
stage ledger-unchanged cmp "$work/ledger-035.json" "$work/ledger-final.json"
printf '%s\n' 'AUDIT_035_ALL_REGRESSIONS_OK' 'PA5_PRIVATE_DB_ROLES_LEDGER_034_ALL_OK'
