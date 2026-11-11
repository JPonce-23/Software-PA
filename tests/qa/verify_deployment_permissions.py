import hashlib,json,os,stat,subprocess,sys
from pathlib import Path
from sqlalchemy import text
from app.database import engine
assert os.environ.get('PR6_DEPLOY_QA')=='SYNTHETIC_DISPOSABLE_ONLY'and os.geteuid()==0
with engine.connect()as db:
    assert db.execute(text("SELECT current_setting('cluster_name')")).scalar_one()=='pr6-deployment-disposable'
    f=db.execute(text('SELECT value FROM pr6_synthetic_fixture')).scalar_one()
    version=db.execute(text('SELECT id_documento,ruta_almacenamiento,tamano_bytes,hash_sha256 FROM documento_version WHERE id_documento_version=:v'),{'v':f['legacy_version']}).one()
    op=db.execute(text('SELECT c.id_operacion,o.id_documento,c.identidad FROM documento_coordinacion c JOIN documento_operacion o USING(id_operacion) LIMIT 1')).one()
root=Path('/app/uploads');file=root/version[1];directory=file.parent
lock=root/'.ss12-writers'/f'{op[1]}-{op[0].hex}.lock'
assert file.resolve().is_relative_to(root)and file.is_file()and lock.is_file()
entries=[directory,file,lock]
identity=lambda p:(p.stat().st_dev,p.stat().st_ino)
before=[identity(p)for p in entries];digest=hashlib.sha256(file.read_bytes()).hexdigest()
def uid10001():os.setgid(10001);os.setuid(10001)
# Reproduce a private historical file and lock from the former runtime UID.
for p in entries:os.chown(p,0,0)
file.chmod(0o600)
preflight=[sys.executable,'/app/scripts/check_upload_access.py']
r=subprocess.run(preflight,preexec_fn=uid10001,capture_output=True,text=True)
assert r.returncode==1 and 'UPLOAD_PREFLIGHT_FAIL'in r.stdout
# Exact allow-list only; no recursive chmod/chown, inode replacement or DB edit.
for p in entries:os.chown(p,10001,10001)
assert [identity(p)for p in entries]==before
assert hashlib.sha256(file.read_bytes()).hexdigest()==digest
subprocess.run(preflight,preexec_fn=uid10001,check=True)
code='''import hashlib,threading,uuid
from app.services.document_download import open_verified
from app.services.document_coordination import WriterLease
from pathlib import Path
meta=__META__
owned=open_verified('/app/uploads',meta['path'],meta['document'],meta['size'],meta['sha'],threading.Event())
try:assert hashlib.sha256(owned.read_at(0,meta['size'])).hexdigest()==meta['sha']
finally:owned.close()
with WriterLease('/app/uploads',meta['lock_document'],uuid.UUID(meta['operation']))as lease:
 assert lease.identity==meta['identity']
'''.replace('__META__',repr({'path':version[1],'document':version[0],'size':version[2],'sha':version[3],
    'lock_document':op[1],'operation':str(op[0]),'identity':op[2]}))
subprocess.run([sys.executable,'-c',code],preexec_fn=uid10001,check=True)
print('PASS private_historical_file_and_coordination_owner_transition_exact_entries_same_inodes_and_bytes')
