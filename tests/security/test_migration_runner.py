"""Offline tests of proposed read-only guard ONLY. No original/full runner or DB."""
import hashlib,json,os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUNNER=ROOT/'backend/scripts/run_migrations.sh'
def history_guard_source():
 source=RUNNER.read_text()
 return source[source.index('# BEGIN HISTORY GUARD'):source.index('# END HISTORY GUARD')]

FAKE='''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
args=sys.argv[1:]
if '-f' in args or '-c' not in args: raise SystemExit(97)
query=args[args.index('-c')+1]
if not query.startswith('SELECT '):raise SystemExit(98)
key=('exists' if "to_regclass('public.schema_migrations')" in query else 'objects' if 'user_objects' in query else 'lookup' if 'count(*),coalesce(min(nombre)' in query else 'rows' if 'ORDER BY version' in query else 'unknown')
with open(os.environ['FAKE_CALLS'],'a') as f:f.write(key+'\\n')
state=json.loads(Path(os.environ['FAKE_STATE']).read_text());r=state.get(key,{'out':'UNEXPECTED_QUERY','rc':99})
if r.get('err'):print(r['err'],file=sys.stderr)
if r.get('out'):print(r['out'])
raise SystemExit(r.get('rc',0))
'''
class HistoryGuardTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='pa-pr6-runner-proposal-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.files=self.root/'migrations';self.files.mkdir();self.rows=[]
  for i in range(1,4):
   name=f'{i:03d}_case_{i}.sql';data=f'-- synthetic canonical {i}\n'.encode();(self.files/name).write_bytes(data)
   self.rows.append(f'{i:03d}|case_{i}|'+hashlib.sha256(data).hexdigest())
  self.fake=self.root/'fake_psql';self.fake.write_text(FAKE);self.fake.chmod(0o700)
  self.state={'exists':{'out':'present'},'rows':{'out':'\n'.join(self.rows)},'lookup':{'out':'1|'+self.rows[0].split('|',1)[1]}}
 def run_guard(self,*,lookup=True):
  state=self.root/'state.json';state.write_text(json.dumps(self.state));calls=self.root/'calls'
  script='set -euo pipefail\nshopt -s nullglob\nconnection=()\n'+history_guard_source()+'\nvalidate_migration_history\n'
  if lookup:script+='read_applied_checksum 001 case_1\n'
  env={'PATH':os.environ['PATH'],'PSQL_BIN':str(self.fake),'MIGRATIONS_DIR':str(self.files),'FAKE_STATE':str(state),'FAKE_CALLS':str(calls)}
  p=subprocess.run(['bash','-c',script],env=env,text=True,capture_output=True)
  self.calls=calls.read_text().splitlines() if calls.exists() else []
  return p
 def assert_reject(self,stage=None):
  p=self.run_guard();self.assertNotEqual(p.returncode,0,p.stdout);self.assertNotIn('unknown',self.calls)
  if stage:self.assertEqual(self.calls[-1],stage)
  return p
 def test_valid_existing_history(self):
  p=self.run_guard();self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout.strip(),self.rows[0].split('|')[2])
 def test_valid_new_empty_database_skips_relation_lookup(self):
  self.state={'exists':{'out':'missing'},'objects':{'out':'0'}};p=self.run_guard();self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(self.calls,['exists','objects']);self.assertEqual(p.stdout,'')
 def test_missing_history_with_application_objects_rejected(self):
  self.state={'exists':{'out':'missing'},'objects':{'out':'4'}};self.assert_reject('objects')
 def test_connection_failure_fails_closed_with_diagnostic(self):
  self.state['exists']={'rc':2,'err':'SYNTHETIC_CONNECTION_FAILURE'};p=self.assert_reject('exists');self.assertIn('SYNTHETIC_CONNECTION_FAILURE',p.stderr)
 def test_history_permission_error_fails_closed(self):
  self.state['rows']={'rc':1,'err':'SYNTHETIC_PERMISSION_DENIED'};p=self.assert_reject('rows');self.assertIn('SYNTHETIC_PERMISSION_DENIED',p.stderr)
 def test_history_query_error_fails_closed(self):
  self.state['rows']={'rc':1,'err':'SYNTHETIC_UNDEFINED_COLUMN'};self.assert_reject('rows')
 def test_new_database_inventory_error_fails_closed(self):
  self.state={'exists':{'out':'missing'},'objects':{'rc':1,'err':'SYNTHETIC_INVENTORY_ERROR'}};self.assert_reject('objects')
 def test_existing_empty_history_rejected(self):
  self.state['rows']={'out':''};self.assert_reject('rows')
 def test_duplicate_version_rejected(self):
  self.state['rows']={'out':self.rows[0]+'\n'+self.rows[0]};self.assert_reject('rows')
 def test_gap_rejected(self):
  self.state['rows']={'out':self.rows[0]+'\n'+self.rows[2]};self.assert_reject('rows')
 def test_unexpected_version_rejected(self):
  self.state['rows']={'out':'\n'.join(self.rows)+f'\n004|unknown|'+('a'*64)};self.assert_reject('rows')
 def test_null_checksum_rejected(self):
  self.state['rows']={'out':'001|case_1|<NULL>'};self.assert_reject('rows')
 def test_mismatched_checksum_rejected(self):
  self.state['rows']={'out':'001|case_1|'+('a'*64)};self.assert_reject('rows')
 def test_mismatched_name_rejected(self):
  self.state['rows']={'out':self.rows[0].replace('case_1','wrong')};self.assert_reject('rows')
 def test_duplicate_canonical_files_rejected(self):
  (self.files/'001_other.sql').write_text('-- duplicate version');self.assert_reject('rows')
 def test_lookup_connection_or_permission_failure_is_not_unapplied(self):
  self.state['lookup']={'rc':2,'err':'SYNTHETIC_LOOKUP_FAILURE'};p=self.assert_reject('lookup');self.assertIn('SYNTHETIC_LOOKUP_FAILURE',p.stderr)
 def test_lookup_duplicate_rows_rejected(self):
  self.state['lookup']={'out':'2|'+self.rows[0].split('|',1)[1]};self.assert_reject('lookup')
 def test_lookup_null_or_malformed_checksum_rejected(self):
  self.state['lookup']={'out':'1|case_1|'};self.assert_reject('lookup')
 def test_missing_later_version_is_unapplied(self):
  self.state['lookup']={'out':'0||'};p=self.run_guard();self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout,'')
 def test_unknown_catalog_response_rejected(self):
  self.state['exists']={'out':'ambiguous'};self.assert_reject('exists')

# Full-runner offline model: the fake executable never invokes PostgreSQL.
# These tests validate control flow/argv, not real PostgreSQL transactionality.
LOOP_FAKE=r'''#!/usr/bin/env python3
import hashlib,json,os,re,sys
from pathlib import Path
path=Path(os.environ['MODEL_STATE']);state=json.loads(path.read_text());args=sys.argv[1:]
query=args[args.index('-c')+1] if '-c' in args else ''
if '-f' in args:
 file=Path(args[args.index('-f')+1]);version=file.name[:3];kind='apply:'+version
else:
 kind=('exists' if "to_regclass('public.schema_migrations')" in query else 'objects' if 'user_objects' in query else 'rows' if 'ORDER BY version' in query else 'lookup:'+re.search("WHERE version='([0-9]{3})'",query).group(1) if 'count(*),coalesce(min(nombre)' in query else 'UNKNOWN')
state['calls'].append({'kind':kind,'argv':args});path.write_text(json.dumps(state))
if state.get('fail')==kind:
 print(state.get('error','SYNTHETIC_PSQL_FAILURE'),file=sys.stderr);raise SystemExit(state.get('rc',1))
if kind.startswith('apply:'):
 assert '--single-transaction' in args and 'ON_ERROR_STOP=1' in args
 version=kind.split(':')[1];name=file.name[4:-4];checksum=hashlib.sha256(file.read_bytes()).hexdigest()
 assert "INSERT INTO public.schema_migrations" in query
 assert "VALUES ('%s','%s','%s')"%(version,name,checksum) in query
 assert version not in state['rows']
 state['history']=True;state['objects']=1;state['rows'][version]=[name,checksum];state['applied'].append(version)
 path.write_text(json.dumps(state));print('SYNTHETIC_TRANSACTION_COMMITTED')
elif kind=='exists':print('present' if state['history'] else 'missing')
elif kind=='objects':print(state['objects'])
elif kind=='rows':
 for version,(name,checksum) in sorted(state['rows'].items()):print('|'.join([version,name,checksum]))
elif kind.startswith('lookup:'):
 row=state['rows'].get(kind.split(':')[1]);print('1|'+'|'.join(row) if row else '0||')
else:raise SystemExit(97)
'''

class RunnerControlFlowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='pa-runner-loop-offline-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.files=self.root/'migrations';self.files.mkdir()
  for i in range(1,4):(self.files/f'{i:03d}_fixture_{i}.sql').write_text(f'-- offline fixture {i}; never sent to PostgreSQL\n')
  self.fake=self.root/'fake_psql';self.fake.write_text(LOOP_FAKE);self.fake.chmod(0o700)
  self.state=self.root/'state.json';self.state.write_text(json.dumps({'history':False,'objects':0,'rows':{},'calls':[],'applied':[]}))
 def model(self):return json.loads(self.state.read_text())
 def change(self,**fields):
  d=self.model();d.update(fields);self.state.write_text(json.dumps(d))
 def invoke(self,**extra):
  env={'PATH':os.environ['PATH'],'PSQL_BIN':str(self.fake),'MIGRATIONS_DIR':str(self.files),'POSTGRES_DB':'synthetic_model_db','POSTGRES_USER':'synthetic_model_owner','MODEL_STATE':str(self.state)}
  env.update(extra)
  return subprocess.run(['bash',str(RUNNER)],env=env,text=True,capture_output=True)
 def initialize(self):
  p=self.invoke();self.assertEqual(p.returncode,0,p.stderr)
  self.assertEqual(self.model()['applied'],['001','002','003'])
 def test_first_run_executes_each_file_with_atomic_ledger_insert(self):
  self.initialize();calls=self.model()['calls']
  self.assertEqual([c['kind'] for c in calls[:3]],['exists','objects','apply:001'])
  self.assertEqual([c['kind'] for c in calls if c['kind'].startswith('apply:')],['apply:001','apply:002','apply:003'])
  for c in calls:
   if c['kind'].startswith('apply:'):self.assertIn('--single-transaction',c['argv'])
 def test_second_run_is_idempotent_and_never_reapplies(self):
  self.initialize();before=self.model();p=self.invoke();self.assertEqual(p.returncode,0,p.stderr)
  after=self.model();self.assertEqual(after['rows'],before['rows']);self.assertEqual(after['applied'],before['applied'])
  self.assertFalse(any(c['kind'].startswith('apply:') for c in after['calls'][len(before['calls']):]))
  self.assertEqual(p.stdout.count('checksum sin cambios'),3)
 def test_altered_registered_file_stops_before_any_reapplication(self):
  self.initialize();before=self.model();file=self.files/'001_fixture_1.sql';file.write_text(file.read_text()+'-- altered\n')
  p=self.invoke();self.assertNotEqual(p.returncode,0);after=self.model();self.assertEqual(after['rows'],before['rows'])
  self.assertFalse(any(c['kind'].startswith('apply:') for c in after['calls'][len(before['calls']):]))
 def test_connection_error_stops_before_any_file(self):
  self.change(fail='exists',rc=2);p=self.invoke();self.assertNotEqual(p.returncode,0)
  self.assertEqual(self.model()['applied'],[]);self.assertEqual([c['kind'] for c in self.model()['calls']],['exists'])
 def test_permission_error_stops_before_any_file(self):
  self.initialize();before=self.model();self.change(fail='rows',error='SYNTHETIC_PERMISSION_DENIED')
  p=self.invoke();self.assertNotEqual(p.returncode,0);self.assertEqual(self.model()['applied'],before['applied'])
  self.assertEqual([c['kind'] for c in self.model()['calls'][len(before['calls']):]],['exists','rows'])
 def test_lookup_query_failure_does_not_apply_following_files(self):
  self.change(fail='lookup:002',error='SYNTHETIC_QUERY_FAILURE');p=self.invoke();self.assertNotEqual(p.returncode,0)
  self.assertEqual(self.model()['applied'],['001']);self.assertEqual(self.model()['calls'][-1]['kind'],'lookup:002')
  self.assertNotIn('Migración 002 aplicada',p.stdout)
 def test_apply_failure_preserves_failure_and_stops_following_files(self):
  self.change(fail='apply:002',error='SYNTHETIC_APPLY_FAILURE');p=self.invoke();self.assertNotEqual(p.returncode,0)
  self.assertEqual(self.model()['applied'],['001']);self.assertNotIn('002',self.model()['rows'])
  self.assertEqual(self.model()['calls'][-1]['kind'],'apply:002');self.assertNotIn('Migración 003 aplicada',p.stdout)
 def test_connection_failure_diagnostics_do_not_leak_password_or_url(self):
  secret='SYNTHETIC_SENTINEL_PASSWORD';uri='postgresql://synthetic:'+secret+'@example.invalid/qa'
  self.change(fail='exists',rc=2,error='connection failed '+uri+' password='+secret)
  p=self.invoke(PGPASSWORD=secret,DATABASE_URL=uri)
  self.assertNotEqual(p.returncode,0);self.assertIn('PSQL_ERROR exit=2',p.stderr)
  self.assertNotIn(secret,p.stdout+p.stderr);self.assertNotIn(uri,p.stdout+p.stderr)
  self.assertEqual(self.model()['applied'],[])
 def test_apply_failure_diagnostics_do_not_leak_credentials(self):
  secret='SYNTHETIC_APPLY_SECRET';self.change(fail='apply:002',error='failed with '+secret)
  p=self.invoke(POSTGRES_ADMIN_PASSWORD=secret);self.assertNotEqual(p.returncode,0)
  self.assertNotIn(secret,p.stdout+p.stderr);self.assertIn('PSQL_ERROR exit=1',p.stderr)
  self.assertEqual(self.model()['applied'],['001'])
 def test_url_and_discrete_connection_contracts_are_preserved(self):
  uri='postgresql://synthetic:synthetic_only@example.invalid/qa'
  p=self.invoke(DATABASE_URL=uri,DB_HOST='ignored.invalid');self.assertEqual(p.returncode,0,p.stderr)
  argv=self.model()['calls'][0]['argv'];self.assertEqual(argv[0],uri);self.assertNotIn('--host',argv)
  self.change(calls=[]);p=self.invoke(POSTGRES_DB='',POSTGRES_USER='',DB_NAME='fallback_db',POSTGRES_ADMIN_USER='fallback_owner',DB_HOST='127.0.0.1',DB_PORT='55432')
  self.assertEqual(p.returncode,0,p.stderr);argv=self.model()['calls'][0]['argv']
  self.assertEqual(argv[:8],['--username','fallback_owner','--dbname','fallback_db','--host','127.0.0.1','--port','55432'])

if __name__=='__main__':unittest.main(verbosity=2)
