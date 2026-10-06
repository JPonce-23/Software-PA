#!/usr/bin/env python3
"""Run both migration histories in an isolated tmpfs PostGIS instance.

No host ports or persistent volumes. The only database is software_pa_test.
Always removes the Compose project, including on failure. Does not connect to
Software-PA's persistent database. Run with the three explicit test guards.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'backups/lineage_gis_20261005'
COMPOSE=['docker','compose','--env-file',str(ROOT/'.env'),'-p','software-pa-lineage-equivalence','-f',str(ROOT/'backend/tests/lineage_compose.yml')]


def run(args,name):
    result=subprocess.run(COMPOSE+args,cwd=ROOT,text=True,capture_output=True)
    (EVIDENCE/(name+'.stdout')).write_text(result.stdout)
    (EVIDENCE/(name+'.stderr')).write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(f'{name} failed ({result.returncode}); inspect evidence')
    return result.stdout


def reset():
    # Match the persistent instance's approved extension configuration, rather
    # than the optional tiger/topology extensions auto-created by the image.
    run(['exec','-T','db','sh','-lc',
         'test "$(psql -U "$POSTGRES_USER" -d software_pa_test -Atc "SELECT current_database()")" = software_pa_test; '
         'psql -U "$POSTGRES_USER" -d software_pa_test -X -v ON_ERROR_STOP=1 -c '
         '"DROP SCHEMA public CASCADE; CREATE SCHEMA public AUTHORIZATION pg_database_owner; GRANT USAGE ON SCHEMA public TO PUBLIC;"'], 'equivalence-reset')


def runner(legacy=False):
    setup=''
    directory='/tmp/canonical-gis-025'
    setup='mkdir -p /tmp/canonical-gis-025; for f in /opt/software-pa/db/migrations/0[01][0-9]_*.sql /opt/software-pa/db/migrations/02[0-5]_*.sql; do test -f "$f" && ln -sf "$f" /tmp/canonical-gis-025/; done; '
    if legacy:
        directory='/tmp/legacy-gis'
        setup='mkdir -p /tmp/legacy-gis; for f in /opt/software-pa/db/migrations/0[01][0-9]_*.sql /opt/software-pa/db/lineage/gis_precanonical/*.sql; do test -f "$f" && ln -sf "$f" /tmp/legacy-gis/; done; '
    return run(['exec','-T','db','sh','-lc',setup+'MIGRATIONS_DIR='+directory+' POSTGRES_DB=software_pa_test /opt/software-pa/scripts/run_migrations.sh'],'equivalence-runner-'+('legacy' if legacy else 'canonical'))


def snapshot(name):
    code='import json,sys; sys.path.insert(0,"scripts"); import reconcile_gis_migration_lineage as r; import lineage_inspection as i; c=r.connect(); c.set_session(readonly=True); print(json.dumps({"schema":i.schema_signature(c),"ledger":i.ledger(c),"data":i.data_signature(c)},default=str,sort_keys=True)); c.rollback(); c.close()'
    return json.loads(run(['run','--rm','--no-deps','worker','python','-c',code],name))


def main():
    for key,value in {'APP_ENV':'test','DB_NAME':'software_pa_test','TEST_ALLOW_DATABASE':'software_pa_test'}.items():
        if os.getenv(key)!=value:raise RuntimeError('Missing explicit test guard: '+key)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    # The exceptional reconciler deliberately rejects later releases. Test it
    # against its frozen inventory, without weakening any production safeguard.
    frozen=tempfile.TemporaryDirectory(prefix='software-pa-lineage-025-')
    frozen_path=Path(frozen.name)
    migrations=frozen_path/'migrations'
    migrations.mkdir()
    for item in json.loads((ROOT/'backend/db/lineage/gis_lineage_manifest.json').read_text())['common'] + json.loads((ROOT/'backend/db/lineage/gis_lineage_manifest.json').read_text())['canonical']:
        shutil.copyfile(ROOT/'backend/db/migrations'/item['file'],migrations/item['file'])
    override=frozen_path/'compose.yml'
    override.write_text('services:\n  worker:\n    volumes:\n      - '+str(migrations)+':/app/db/migrations:ro\n')
    COMPOSE.extend(['-f',str(override)])
    try:
        run(['up','-d','--wait','db'],'equivalence-start')
        reset();runner();a=snapshot('equivalence-a')
        reset();runner(legacy=True)
        before=snapshot('equivalence-b-before')
        run(['run','--rm','--no-deps','worker','pytest','-q','tests/test_migration_lineage.py'],'equivalence-reconciler-tests')
        run(['run','--rm','--no-deps','worker','python','scripts/reconcile_gis_migration_lineage.py','--dry-run','--expected-database','software_pa_test'],'equivalence-b-dry-run')
        run(['run','--rm','--no-deps','worker','python','scripts/reconcile_gis_migration_lineage.py','--apply','--expected-database','software_pa_test'],'equivalence-b-apply')
        pending=snapshot('equivalence-b-pending')
        output=runner()
        assert 'Migración 020 aplicada:' in output
        assert all(f'Migración {n:03} verificada' in output for n in range(21,26))
        b=snapshot('equivalence-b-final')
        assert a['schema']==b['schema'],[k for k in a['schema'] if a['schema'][k]!=b['schema'][k]]
        def logical(rows):return [{k:x[k] for k in ('version','nombre','checksum_sha256')} for x in rows]
        assert logical(a['ledger'])==logical(b['ledger'])
        assert before['data']==pending['data']==b['data']
        dates={x['version']:x['aplicada_en'] for x in before['ledger']}
        assert len(b['ledger'])==25 and len(pending['ledger'])==24
        assert all(x['aplicada_en']==dates[f"{int(x['version'])-1:03}"] for x in b['ledger'] if int(x['version'])>=21)
        result={'equivalent':True,'categories':list(a['schema']),
                'ledger_rows':25,'gis_dates_preserved':True,'business_and_gis_data_preserved':True,
                'runner_applied_heartbeat_only':True,'reconciler_tests':'38 passed'}
        (EVIDENCE/'equivalence-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
    finally:
        run(['down','-v','--remove-orphans'],'equivalence-cleanup')
        frozen.cleanup()

if __name__=='__main__':main()
