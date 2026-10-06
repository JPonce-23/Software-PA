#!/usr/bin/env python3
"""Manual, exceptional adoption of the exact pre-canonical GIS lineage.

Dry-run is read-only and is the default. This script never applies heartbeat,
replays GIS DDL, or writes business rows. Unknown/partial states are rejected.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import psycopg2
from psycopg2 import sql

from lineage_inspection import DATA_TABLES, data_signature, digest, ledger, schema_signature

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_FILE = ROOT / 'db/lineage/gis_lineage_manifest.json'
SCHEMA_FILE = ROOT / 'db/lineage/gis_legacy_schema_signature.json'
MANIFEST_SHA = '7c4f524adf823a162c38e54f0bbfc10e0ba93affd0f552e1d128f8fba427feba'
SCHEMA_SHA = '12e605a56d258f4363950745968cb5db6012fd9401ca5736cc01f02913312827'
DATABASE = 'software_pa_test'
LOCK_NAME = 'software-pa:reconcile-gis-lineage:v1'

class ReconciliationError(RuntimeError):
    pass

class CommitUncertain(ReconciliationError):
    pass

def approved_json(path, expected):
    contents=path.read_bytes()
    if hashlib.sha256(contents).hexdigest()!=expected:
        raise ReconciliationError(f'Manifiesto aprobado alterado: {path.name}')
    return json.loads(contents)

def manifest():
    return approved_json(MANIFEST_FILE,MANIFEST_SHA)

def check_environment(expected_database):
    if expected_database != DATABASE or any(os.getenv(k)!=v for k,v in {
        'APP_ENV':'test','DB_NAME':DATABASE,'TEST_ALLOW_DATABASE':DATABASE}.items()):
        raise ReconciliationError('Se requiere --expected-database software_pa_test, APP_ENV=test, DB_NAME=software_pa_test y TEST_ALLOW_DATABASE=software_pa_test')

def connect():
    # Never fall back to runtime credentials or a different database.
    params={'dbname':DATABASE,'host':os.getenv('PGHOST') or os.getenv('DB_HOST'),
            'port':os.getenv('PGPORT') or os.getenv('DB_PORT') or '5432',
            'user':os.getenv('PGUSER') or os.getenv('POSTGRES_ADMIN_USER'),
            'password':os.getenv('PGPASSWORD') or os.getenv('POSTGRES_ADMIN_PASSWORD'),
            'connect_timeout':10,'options':'-c statement_timeout=30000 -c lock_timeout=5000','application_name':'software-pa-gis-lineage-reconciler'}
    if not params['host'] or not params['user'] or not params['password']:
        raise ReconciliationError('Faltan credenciales administrativas explícitas y host')
    return psycopg2.connect(**params)

def compact(rows):
    return [{'version':r['version'],'nombre':r['nombre'],'sha256':r.get('checksum_sha256',r.get('sha256'))} for r in rows]

def classify(rows,m):
    values=compact(rows)
    if any(r.get('aplicada_en') is None for r in rows):return 'UNKNOWN'
    if values==compact(m['common']+m['legacy']):return 'LEGACY_GIS_024'
    if values==compact(m['common']+m['canonical'][1:]):return 'RECONCILED_PENDING_HEARTBEAT'
    if values==compact(m['common']+m['canonical']):return 'CANONICAL_025'
    return 'UNKNOWN'

def check_files(m):
    expected=m['common']+m['canonical']
    files=sorted(p.name for p in (ROOT/'db/migrations').glob('*.sql') if p.is_file())
    if files!=sorted(x['file'] for x in expected):
        raise ReconciliationError('Inventario ejecutable distinto de 001–025 canónico')
    for item in expected:
        contents=(ROOT/'db/migrations'/item['file']).read_bytes()
        if hashlib.sha256(contents).hexdigest()!=item['sha256']:
            raise ReconciliationError('SHA canónico incorrecto: '+item['file'])
    for old,new in zip(m['legacy'],m['canonical'][1:]):
        original=(ROOT/'db/lineage/gis_precanonical'/old['file']).read_bytes()
        canonical=(ROOT/'db/migrations'/new['file']).read_bytes()
        if hashlib.sha256(original).hexdigest()!=old['sha256']:
            raise ReconciliationError('Archivo GIS histórico alterado: '+old['file'])
        def body(data):return data[re.search(rb'(?m)^(?:CREATE|ALTER) ',data).start():]
        if body(original)!=body(canonical) or hashlib.sha256(body(canonical)).hexdigest()!=new['functional_sha256']:
            raise ReconciliationError('Cambio funcional GIS detectado: '+new['file'])

def validate(connection,m):
    check_files(m)
    with connection.cursor() as cur:
        cur.execute('SELECT current_database()')
        if cur.fetchone()[0]!=DATABASE:raise ReconciliationError('Base real incorrecta')
        cur.execute("SELECT count(*) FROM pg_constraint WHERE contype='f' AND confrelid='public.schema_migrations'::regclass")
        if cur.fetchone()[0]:raise ReconciliationError('Ledger tiene FK entrante inesperada')
        cur.execute("SELECT count(*) FROM pg_trigger WHERE tgrelid='public.schema_migrations'::regclass AND NOT tgisinternal")
        if cur.fetchone()[0]:raise ReconciliationError('Ledger tiene trigger inesperado')
    rows=ledger(connection)
    state=classify(rows,m)
    if state!='LEGACY_GIS_024':
        raise ReconciliationError('Estado no aplicable; no se modifica: '+state)
    actual=schema_signature(connection)
    expected=approved_json(SCHEMA_FILE,SCHEMA_SHA)
    if actual!=expected:
        changed=[k for k in expected if actual.get(k)!=expected[k]]
        raise ReconciliationError('Firma estructural incompatible: '+','.join(changed))
    return rows,actual,data_signature(connection)

def execute(connection,*,apply=False,expected_database=DATABASE,after_step=None):
    check_environment(expected_database)
    m=manifest()
    connection.set_session(readonly=not apply)
    committing=False
    try:
        if apply:
            with connection.cursor() as cur:
                cur.execute("SET LOCAL lock_timeout='5s'")
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",(LOCK_NAME,))
                cur.execute('LOCK TABLE public.schema_migrations IN ACCESS EXCLUSIVE MODE')
                # Protect the preservation comparison from concurrent application writers.
                cur.execute(sql.SQL('LOCK TABLE {} IN SHARE MODE').format(sql.SQL(',').join(sql.Identifier('public',t) for t in DATA_TABLES)))
        before,structure,data=validate(connection,m)
        report={'database':DATABASE,'mode':'apply' if apply else 'dry-run','state':'LEGACY_GIS_024',
                'ledger_before':before,'legacy_manifest':m['common']+m['legacy'],
                'canonical_manifest':m['common']+m['canonical'],
                'structural_validation':'exact_match','schema_sha256':digest(structure),
                'data_before':data,'preserve_aplicada_en':True,
                'transformations':[{'from':a['version'],'to':b['version'],'nombre':b['nombre'],'sha256':b['sha256']} for a,b in reversed(list(zip(m['legacy'],m['canonical'][1:])))]}
        if not apply:
            connection.rollback()
            report['writes']=0
            return report
        original={r['version']:r for r in before}
        with connection.cursor() as cur:
            for old,new in reversed(list(zip(m['legacy'],m['canonical'][1:]))):
                cur.execute('UPDATE public.schema_migrations SET version=%s,nombre=%s,checksum_sha256=%s WHERE version=%s AND nombre=%s AND checksum_sha256=%s AND aplicada_en=%s',
                    (new['version'],new['nombre'],new['sha256'],old['version'],old['nombre'],old['sha256'],original[old['version']]['aplicada_en']))
                if cur.rowcount!=1:raise ReconciliationError('Actualización no unitaria: '+old['version'])
                if after_step:after_step(old['version'])
        after=ledger(connection)
        if classify(after,m)!='RECONCILED_PENDING_HEARTBEAT':raise ReconciliationError('Postcondición del ledger incorrecta')
        expected_dates={r['version']:r['aplicada_en'] for r in before if int(r['version'])<20}
        expected_dates.update({new['version']:original[old['version']]['aplicada_en'] for old,new in zip(m['legacy'],m['canonical'][1:])})
        if any(r['aplicada_en']!=expected_dates[r['version']] for r in after):raise ReconciliationError('Fecha histórica alterada')
        if schema_signature(connection)!=structure or data_signature(connection)!=data:
            raise ReconciliationError('Cambió el esquema o datos administrativos/GIS')
        report.update(ledger_after=after,data_after=data,state_after='RECONCILED_PENDING_HEARTBEAT',business_rows_changed=0)
        committing=True
        connection.commit()
        return report
    except Exception as exc:
        if committing:
            # Never guess whether a lost COMMIT response means success or rollback.
            try:
                probe=connect();probe.set_session(readonly=True)
                state=classify(ledger(probe),m)
                probe.rollback();probe.close()
            except Exception:
                state='UNVERIFIED'
            raise CommitUncertain('Resultado de COMMIT incierto; estado observado='+state+'; verificar en sólo lectura, sin reparar automáticamente') from exc
        connection.rollback()
        raise

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run',action='store_true')
    mode.add_argument('--apply',action='store_true')
    parser.add_argument('--expected-database',required=True,choices=[DATABASE])
    args=parser.parse_args()
    connection=None
    try:
        check_environment(args.expected_database)
        connection=connect()
        print(json.dumps(execute(connection,apply=args.apply,expected_database=args.expected_database),indent=2,default=str))
        return 0
    except Exception as exc:
        print('ABORTADO: '+str(exc),file=sys.stderr)
        return 1
    finally:
        if connection:connection.close()

if __name__=='__main__':sys.exit(main())
