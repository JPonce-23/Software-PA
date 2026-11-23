"""Read the ledger only from the private Unix socket inherited from database.sh."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
assert os.environ['PGDATABASE']=='software_pa_test'
assert os.environ['PGHOST'].startswith('/tmp/pa5-pr8-db.')
cluster=subprocess.check_output(['psql','-X','-At','-v','ON_ERROR_STOP=1','-c',"SELECT current_setting('cluster_name')"],text=True).strip()
assert cluster in {'pa5-pr8-f715b55','pa5-pr8-035-upgrade','pa5-pr8-035-fresh'}
maximum=int(os.environ.get('PA5_LEDGER_MAX_VERSION','34'));assert maximum in {34,35}
files=sorted(p for p in Path('/source/backend/db/migrations').glob('[0-9][0-9][0-9]_*.sql') if int(p.name[:3])<=maximum)
expected=[[p.name[:3],p.stem[4:],hashlib.sha256(p.read_bytes()).hexdigest()] for p in files]
assert [r[0] for r in expected]==[f'{n:03}' for n in range(1,maximum+1)]
raw=subprocess.check_output(['psql','-X','-At','-F','|','-v','ON_ERROR_STOP=1','-c','SELECT version,nombre,checksum_sha256 FROM public.schema_migrations ORDER BY version'],text=True)
actual=[line.split('|') for line in raw.splitlines()]
assert actual==expected,'LEDGER_EXACT_CANONICAL_MISMATCH'
Path(sys.argv[1]).write_text(json.dumps(actual,indent=2)+'\n')
print(f'PA5_{maximum}_NAMES_AND_CANONICAL_CHECKSUMS_OK')
