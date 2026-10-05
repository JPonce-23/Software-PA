"""The ledger-writing tests run ONLY in lineage_compose.yml's disposable instance."""
import json
import os
from pathlib import Path
import sys

import psycopg2
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import reconcile_gis_migration_lineage as r
from lineage_inspection import data_signature, ledger, schema_signature


def test_frozen_files_and_functional_gis_bodies():
    r.check_files(r.manifest())

@pytest.mark.parametrize('key,value',[('APP_ENV','development'),('DB_NAME','other'),('TEST_ALLOW_DATABASE','other')])
def test_wrong_environment_is_rejected(monkeypatch,key,value):
    monkeypatch.setenv(key,value)
    with pytest.raises(r.ReconciliationError):r.check_environment(r.DATABASE)

def test_wrong_expected_database_is_rejected():
    with pytest.raises(r.ReconciliationError):r.check_environment('db_pruebas_alfredo')

@pytest.mark.parametrize('mutation',['checksum','incomplete','unexpected','heartbeat','partial','date','name'])
def test_unknown_ledgers_are_rejected(mutation):
    m=r.manifest();rows=[dict(version=x['version'],nombre=x['nombre'],checksum_sha256=x['sha256'],aplicada_en='present') for x in m['common']+m['legacy']]
    if mutation=='checksum':rows[-1]['checksum_sha256']='0'*64
    if mutation=='incomplete':rows.pop()
    if mutation=='unexpected':rows.append(dict(rows[-1],version='026'))
    if mutation=='heartbeat':rows[19].update(nombre=m['canonical'][0]['nombre'],checksum_sha256=m['canonical'][0]['sha256'])
    if mutation=='partial':rows[-1]['version']='025'
    if mutation=='date':rows[-1]['aplicada_en']=None
    if mutation=='name':rows[-1]['nombre']='unexpected'
    assert r.classify(rows,m)=='UNKNOWN'

@pytest.fixture
def disposable():
    if os.getenv('LINEAGE_DISPOSABLE_INSTANCE')!='1':
        pytest.skip('Ledger-writing checks require the isolated disposable instance')
    assert os.environ['DB_HOST']=='db'
    c=r.connect();c.set_session(readonly=True)
    with c.cursor() as cur:
        cur.execute('SHOW cluster_name')
        assert cur.fetchone()[0]=='software-pa-lineage-equivalence', 'Ledger-writing tests require the disposable server marker'
    before=ledger(c);data=data_signature(c);c.rollback();c.set_session(readonly=False)
    assert r.classify(before,r.manifest())=='LEGACY_GIS_024'
    try:yield c,before,data
    finally:
        c.rollback();c.close()
        cleanup=r.connect()
        with cleanup.cursor() as cur:
            cur.execute('TRUNCATE public.schema_migrations')
            cur.executemany('INSERT INTO public.schema_migrations(version,nombre,checksum_sha256,aplicada_en) VALUES (%s,%s,%s,%s)',[tuple(x[k] for k in ('version','nombre','checksum_sha256','aplicada_en')) for x in before])
        cleanup.commit()
        assert ledger(cleanup)==before
        assert data_signature(cleanup)==data
        cleanup.rollback();cleanup.close()

class CursorProxy:
    def __init__(self,cur,statements,wrong_database=False):self.cur,self.statements,self.wrong_database=cur,statements,wrong_database
    def __enter__(self):self.cur.__enter__();return self
    def __exit__(self,*args):return self.cur.__exit__(*args)
    def execute(self,query,*args):
        self.statements.append(str(query));self.last=str(query)
        return self.cur.execute(query,*args)
    def fetchone(self):
        result=self.cur.fetchone()
        return ('wrong_database',) if self.wrong_database and self.last=='SELECT current_database()' else result
    def __getattr__(self,name):return getattr(self.cur,name)

class ConnectionProxy:
    def __init__(self,c,*,wrong_database=False,commit_failure=None):self.c=c;self.statements=[];self.wrong_database=wrong_database;self.commit_failure=commit_failure
    def cursor(self):return CursorProxy(self.c.cursor(),self.statements,self.wrong_database)
    def commit(self):
        if self.commit_failure=='after':self.c.commit()
        elif self.commit_failure=='before':self.c.rollback()
        else:return self.c.commit()
        raise psycopg2.OperationalError('Injected lost COMMIT response')
    def __getattr__(self,name):return getattr(self.c,name)


def test_real_database_name_guard(disposable):
    c,before,_=disposable
    with pytest.raises(r.ReconciliationError,match='Base real incorrecta'):
        r.execute(ConnectionProxy(c,wrong_database=True))
    assert ledger(c)==before


def test_read_only_dry_run_without_updates(disposable):
    c,before,_=disposable;proxy=ConnectionProxy(c)
    report=r.execute(proxy)
    assert report['writes']==0 and report['structural_validation']=='exact_match'
    assert c.readonly is True
    assert not any(s.startswith(('UPDATE','INSERT','DELETE','LOCK')) for s in proxy.statements)
    assert ledger(c)==before

@pytest.mark.parametrize('mutation',['checksum','incomplete','unexpected','heartbeat','partial'])
def test_invalid_actual_ledger_aborts(disposable,mutation):
    c,_,_=disposable
    with c.cursor() as cur:
        if mutation=='checksum':cur.execute("UPDATE schema_migrations SET checksum_sha256=%s WHERE version='024'",('0'*64,))
        if mutation=='incomplete':cur.execute("DELETE FROM schema_migrations WHERE version='024'")
        if mutation=='unexpected':cur.execute("INSERT INTO schema_migrations SELECT '026',nombre,checksum_sha256,aplicada_en FROM schema_migrations WHERE version='024'")
        if mutation=='heartbeat':
            h=r.manifest()['canonical'][0];cur.execute("UPDATE schema_migrations SET nombre=%s,checksum_sha256=%s WHERE version='020'",(h['nombre'],h['sha256']))
        if mutation=='partial':cur.execute("UPDATE schema_migrations SET version='025' WHERE version='024'")
    c.commit()
    with pytest.raises(r.ReconciliationError,match='UNKNOWN'):r.execute(c,apply=True)


@pytest.mark.parametrize('part',['column','constraint','index','trigger','function'])
def test_missing_structural_signature_aborts(disposable,part):
    c,_,_=disposable
    changes={
      'column':('ALTER TABLE importacion_feature RENAME COLUMN estado_conciliacion TO unexpected_column','ALTER TABLE importacion_feature RENAME COLUMN unexpected_column TO estado_conciliacion'),
      'constraint':('ALTER TABLE importacion_feature RENAME CONSTRAINT chk_feature_conciliacion TO unexpected_constraint','ALTER TABLE importacion_feature RENAME CONSTRAINT unexpected_constraint TO chk_feature_conciliacion'),
      'index':('ALTER INDEX idx_feature_conciliacion RENAME TO unexpected_index','ALTER INDEX unexpected_index RENAME TO idx_feature_conciliacion'),
      'trigger':('ALTER TABLE importacion_feature_decision DISABLE TRIGGER trg_gis_decision_inmutable','ALTER TABLE importacion_feature_decision ENABLE TRIGGER trg_gis_decision_inmutable'),
      'function':('ALTER FUNCTION fn_audit_log() RENAME TO unexpected_audit_function','ALTER FUNCTION unexpected_audit_function() RENAME TO fn_audit_log'),
    }
    change,restore=changes[part]
    with c.cursor() as cur:cur.execute(change)
    c.commit()
    try:
        with pytest.raises(r.ReconciliationError,match='Firma estructural'):r.execute(c,apply=True)
    finally:
        with c.cursor() as cur:cur.execute(restore)
        c.commit()


def test_apply_descending_dates_and_zero_business_changes(disposable):
    c,before,data=disposable;proxy=ConnectionProxy(c)
    report=r.execute(proxy,apply=True)
    assert [s['from'] for s in report['transformations']]==['024','023','022','021','020']
    after=ledger(c)
    assert r.classify(after,r.manifest())=='RECONCILED_PENDING_HEARTBEAT'
    assert data_signature(c)==data
    assert report['business_rows_changed']==0
    dates={x['version']:x['aplicada_en'] for x in before}
    for row in after:
        prior=row['version'] if int(row['version'])<20 else f"{int(row['version'])-1:03}"
        assert row['aplicada_en']==dates[prior]
    c.rollback()
    with pytest.raises(r.ReconciliationError,match='RECONCILED_PENDING_HEARTBEAT'):r.execute(c,apply=True)

@pytest.mark.parametrize('step',['024','023','022','021','020'])
def test_every_step_rolls_back_completely(disposable,step):
    c,before,data=disposable
    def fail(version):
        if version==step:raise RuntimeError('Injected failure '+version)
    with pytest.raises(RuntimeError,match='Injected failure'):r.execute(c,apply=True,after_step=fail)
    assert ledger(c)==before and data_signature(c)==data


def test_concurrent_advisory_lock_aborts_without_updates(disposable):
    c,before,_=disposable;blocker=r.connect()
    try:
        with blocker.cursor() as cur:cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(r.LOCK_NAME,))
        with pytest.raises(psycopg2.errors.LockNotAvailable):r.execute(c,apply=True)
        assert ledger(c)==before
    finally:blocker.rollback();blocker.close()

@pytest.mark.parametrize('when,state',[('before','LEGACY_GIS_024'),('after','RECONCILED_PENDING_HEARTBEAT')])
def test_uncertain_commit_classifies_without_repair(disposable,when,state):
    c,_,_=disposable
    with pytest.raises(r.CommitUncertain,match=state):r.execute(ConnectionProxy(c,commit_failure=when),apply=True)
    assert r.classify(ledger(c),r.manifest())==state


@pytest.mark.parametrize('file',[r.MANIFEST_FILE,r.SCHEMA_FILE])
def test_changed_approved_manifest_is_rejected(tmp_path,file):
    target=tmp_path/file.name;target.write_bytes(file.read_bytes()+b' ')
    expected=r.MANIFEST_SHA if file==r.MANIFEST_FILE else r.SCHEMA_SHA
    with pytest.raises(r.ReconciliationError,match='alterado'):r.approved_json(target,expected)


def test_known_canonical_ledger_is_classified():
    m=r.manifest();rows=[dict(version=x['version'],nombre=x['nombre'],checksum_sha256=x['sha256'],aplicada_en='present') for x in m['common']+m['canonical']]
    assert r.classify(rows,m)=='CANONICAL_025'


def test_canonical_ledger_reexecution_is_rejected(disposable):
    c,_,_=disposable;r.execute(c,apply=True)
    hb=r.manifest()['canonical'][0]
    with c.cursor() as cur:cur.execute('INSERT INTO schema_migrations(version,nombre,checksum_sha256) VALUES (%s,%s,%s)',(hb['version'],hb['nombre'],hb['sha256']))
    c.commit()
    with pytest.raises(r.ReconciliationError,match='CANONICAL_025'):r.execute(c,apply=True)


def test_concurrent_ledger_lock_aborts_without_updates(disposable):
    c,before,_=disposable;blocker=r.connect()
    try:
        with blocker.cursor() as cur:cur.execute('LOCK TABLE schema_migrations IN ACCESS EXCLUSIVE MODE')
        with pytest.raises(psycopg2.errors.LockNotAvailable):r.execute(c,apply=True)
        blocker.rollback()
        assert ledger(c)==before
    finally:blocker.rollback();blocker.close()
