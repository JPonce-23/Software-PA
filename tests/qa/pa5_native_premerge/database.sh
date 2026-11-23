#!/bin/bash
# Historical 001-034 campaign; keep its original fail-closed regressions.
source /qa/database-common.sh
stage migrate-first bash /source/backend/scripts/run_migrations.sh
stage ledger-first /qa-python/bin/python3 /qa/ledger.py "$work/ledger-first.json"
stage migrate-second bash /source/backend/scripts/run_migrations.sh
stage rerun-proof /qa-python/bin/python3 - "$work/migrate-second.log" <<'PY'
from pathlib import Path
import sys,re
s=Path(sys.argv[1]).read_text()
versions=re.findall(r'^Migración ([0-9]{3}) verificada \(checksum sin cambios\)\.$',s,re.M)
assert versions==[f'{n:03}' for n in range(1,35)],versions
assert ' aplicada:' not in s,s
print('PA5_34_VERIFIED_ZERO_REAPPLIED_OK')
PY
stage ledger-second /qa-python/bin/python3 /qa/ledger.py "$work/ledger-second.json"
stage ledger-identical cmp "$work/ledger-first.json" "$work/ledger-second.json"
stage synthetic-seed psql -X -v ON_ERROR_STOP=1 -f /qa/seed.sql
stage runtime-existing env PGUSER=qa_runtime PGPASSWORD="$DB_RUNTIME_PASSWORD" psql -X -v ON_ERROR_STOP=1 --set=expected_runtime_user=qa_runtime --set=expected_owner_user=qa_owner -f /source/backend/db/tests/001_runtime_privileges.sql
stage runtime-negative env PGUSER=qa_runtime PGPASSWORD="$DB_RUNTIME_PASSWORD" psql -X -v ON_ERROR_STOP=1 -f /qa/negative.sql
stage trigger034-runtime env PGUSER=qa_runtime PGPASSWORD="$DB_RUNTIME_PASSWORD" psql -X -v ON_ERROR_STOP=1 -f /qa/034.sql
stage trigger034-owner psql -X -v ON_ERROR_STOP=1 -f /qa/034-owner.sql
stage temp-object-probe env PGUSER=qa_runtime PGPASSWORD="$DB_RUNTIME_PASSWORD" psql -X -v ON_ERROR_STOP=1 -f /qa/temp.sql
stage temp-audit-probe env PGUSER=qa_runtime PGPASSWORD="$DB_RUNTIME_PASSWORD" psql -X -v ON_ERROR_STOP=1 -f /qa/temp-shadow.sql
stage ledger-final /qa-python/bin/python3 /qa/ledger.py "$work/ledger-final.json"
stage ledger-final-identical cmp "$work/ledger-first.json" "$work/ledger-final.json"
printf '%s\n' 'PA5_PRIVATE_DB_ROLES_LEDGER_034_ALL_OK'
