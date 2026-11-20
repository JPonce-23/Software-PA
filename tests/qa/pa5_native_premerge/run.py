"""Local disposable-Engine QA; no pull/build/network/daemon changes. Review before running."""
import argparse,hashlib,json,os,shutil,subprocess,sys,uuid
from pathlib import Path

REFERENCE='software-pa-libgdal36-candidate:20261117-pa5@sha256:d413671654deef3c43367ea3fd0be56a32a36d75b9d971970e33ec56a76b7c3c'
APPROVED='9efbaf92-7703-4fa0-9192-31b975794366'
SOCKET='unix:///var/run/docker.sock'

def assessment(log):
 if 'PA5_AUDIT_TEMP_SHADOW_REPRODUCED' in log:return 'FAIL'
 if 'PA5_TEMP_CREATION_ALLOWED' in log:return 'PARTIAL'
 return 'PASS'

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--source',type=Path,required=True)
 parser.add_argument('--assets',type=Path,required=True)
 parser.add_argument('--evidence',type=Path,required=True)
 parser.add_argument('--approved-engine-id',required=True)
 parser.add_argument('--database-only',action='store_true',help='Do not repeat the already verified original smoke')
 parser.add_argument('--source-manifest',default='source-sha256.json')
 parser.add_argument('--database-script',choices=['database.sh','database-035.sh'],default='database.sh')
 parser.add_argument('--scenario',choices=['baseline34','upgrade','fresh'],default='baseline34')
 args=parser.parse_args()
 if (args.database_script=='database-035.sh') != (args.scenario in {'upgrade','fresh'}):parser.error('035 requires scenario upgrade or fresh')
 if args.approved_engine_id!=APPROVED:raise RuntimeError('Engine not authorized for this campaign')
 docker_binary=shutil.which('docker')
 env={k:v for k,v in os.environ.items() if k not in {'DOCKER_CONTEXT','DOCKER_HOST'}}
 docker=[docker_binary,'--host',SOCKET]
 def guard():
  p=subprocess.run(docker+['info','--format','{{.ID}}'],env=env,capture_output=True,text=True,timeout=15)
  if p.returncode or p.stdout.strip()!=APPROVED:raise RuntimeError('ENGINE_ID_MISMATCH: no mutation or cleanup permitted')
 guard()
 args.evidence.mkdir(mode=0o700,parents=True,exist_ok=False)
 rows=[];names=[]
 def save(name,value):(args.evidence/name).write_text(json.dumps(value,indent=2)+'\n')
 def stage(name,command,timeout=600,extra_env=None):
  result=subprocess.run(command,env=extra_env or env,capture_output=True,text=True,timeout=timeout)
  (args.evidence/(name+'.log')).write_text(result.stdout+result.stderr)
  rows.append(dict(stage=name,exit=result.returncode));save('stages.json',rows)
  if result.returncode:raise RuntimeError(f'{name} exit={result.returncode}; see evidence')
  return result.stdout
 def dkr(name,arguments):
  guard()
  return stage(name,docker+arguments)
 try:
  expected=json.loads((args.assets/args.source_manifest).read_text())
  for path,wanted in expected.items():
   assert hashlib.sha256((args.source/path).read_bytes()).hexdigest()==wanted,path
  save('source-check.json',dict(state='PASS',base_candidate='f715b55b964517aa4f859e9d20cbdcdee51a36ea',source_manifest=args.source_manifest,manifest_sha256=hashlib.sha256((args.assets/args.source_manifest).read_bytes()).hexdigest(),files=len(expected)))
  raw=dkr('image-inspect',['image','inspect',REFERENCE]);row=json.loads(raw)[0]
  # Avoid retaining even frozen image environment/history in the report.
  (args.evidence/'image-inspect.log').unlink()
  catalog=json.loads((args.source/'deploy/ci/pa5-supply-catalog.json').read_text())
  assert row['Id']==catalog['local_index_digest'] and row['Descriptor']['digest']==catalog['local_index_digest']
  assert row['Os']=='linux' and row['Architecture']=='amd64'
  assert 'software-pa-libgdal36-candidate@'+catalog['local_index_digest'] in row['RepoDigests']
  save('image-identity.json',{k:row[k] for k in ['Id','Descriptor','RepoDigests','RootFS','Os','Architecture']})
  binary=Path('/usr/bin/python3.12');stdlib=Path('/usr/lib/python3.12')
  assert binary.is_file() and stdlib.is_dir()
  helper={'binary':str(binary),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'version':subprocess.check_output([str(binary),'--version'],text=True).strip(),'stdlib_sha256':{str(p.relative_to(stdlib)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(stdlib.rglob('*')) if p.is_file()}}
  save('python-helper.json',helper)
  # Original host verifier uses this guarded Docker shim, never ambient contexts.
  bindir=args.evidence/'bin';bindir.mkdir()
  shim=bindir/'docker'
  shim.write_text('#!/bin/sh\nset -eu\nunset DOCKER_CONTEXT DOCKER_HOST\ntest "$("'+docker_binary+'" --host '+SOCKET+' info --format "{{.ID}}")" = '+APPROVED+'\nexec "'+docker_binary+'" --host '+SOCKET+' "$@"\n')
  shim.chmod(0o700)
  venv=dict(env,PATH=str(bindir)+os.pathsep+env.get('PATH',''))
  if not args.database_only:stage('original-engine-verifier',['sh',str(args.source/'deploy/ci/verificar-pa5-engine.sh'),REFERENCE],extra_env=venv)
  common=['--rm','--pull','never','--network','none','--read-only','--user','postgres','--cap-drop','ALL','--security-opt','no-new-privileges:true','--memory','2g','--cpus','2','--pids-limit','256','--tmpfs','/tmp:rw,nosuid,nodev,size=1536m,mode=1777','--tmpfs','/var/lib/postgresql/data:rw,nosuid,nodev,size=16m,mode=0700',
   '--mount',f'type=bind,src={binary},dst=/qa-python/bin/python3,readonly','--mount',f'type=bind,src={stdlib},dst=/qa-python/lib/python3.12,readonly','-e','PYTHONHOME=/qa-python','-e','PYTHONDONTWRITEBYTECODE=1','-e','PATH=/qa-python/bin:/usr/lib/postgresql/15/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin']
  tag=uuid.uuid4().hex[:12]
  if not args.database_only:
   name='pa5-pr8-smoke-'+tag;names.append(name)
   dkr('original-smoke-readonly-helper',['run','--name',name,*common,'--mount',f'type=bind,src={args.source}/deploy/ci,dst=/qa,readonly','--entrypoint','sh',REFERENCE,'/qa/pa5-native-smoke.sh'])
  name='pa5-pr8-database-'+tag;names.append(name)
  log=dkr('private-database',['run','--name',name,*common,'--mount',f'type=bind,src={args.source},dst=/source,readonly','--mount',f'type=bind,src={args.assets},dst=/qa,readonly','-e','PA5_QA_MODE='+args.scenario,'--entrypoint','bash',REFERENCE,'/qa/'+args.database_script])
  assert 'PA5_PRIVATE_DB_ROLES_LEDGER_034_ALL_OK' in log
  names=[]
  save('result.json',dict(state=assessment(log),scope='private PostgreSQL roles/ledger/034; original smoke skipped this invocation' if args.database_only else 'original smoke plus private PostgreSQL roles/ledger/034; backend ABI39 not run',scenario=args.scenario,temporary_objects_allowed=('PA5_TEMP_CREATION_ALLOWED' in log or 'AUDIT_035_ALL_REGRESSIONS_OK' in log),audit_temp_shadow_reproduced='PA5_AUDIT_TEMP_SHADOW_REPRODUCED' in log,engine_id=APPROVED))
  if assessment(log)=='FAIL':raise RuntimeError('AUDIT_TEMP_SHADOW_REPRODUCED: security gate failed')
 finally:
  for name in names:
   guard()
   p=subprocess.run(docker+['container','inspect','--format','{{.Name}}',name],env=env,capture_output=True,text=True)
   if p.returncode==0:
    guard();subprocess.run(docker+['rm','-f','-v',name],env=env,capture_output=True,check=True)
  save('stages.json',rows)

if __name__=='__main__':main()
