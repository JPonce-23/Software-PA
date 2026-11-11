import os,ssl
import httpx
from sqlalchemy import text
from app.database import engine
assert os.getenv('PR6_DEPLOY_QA')=='SYNTHETIC_DISPOSABLE_ONLY'
with engine.connect()as db:
    assert db.execute(text("SELECT current_setting('cluster_name')")).scalar_one()=='pr6-deployment-disposable'
with httpx.Client(base_url='https://ssalfer.qa.invalid',verify=ssl.create_default_context(cafile='/qa/fullchain.pem'),trust_env=False,headers={'Origin':'https://ssalfer.qa.invalid'})as c:
    for _ in range(5):
        r=c.post('/api/auth/sesiones',data={'username':'locked@example.invalid','password':'synthetic-wrong'});assert r.status_code==401,r.status_code
    r=c.post('/api/auth/sesiones',data={'username':'locked@example.invalid','password':os.environ['QA_PASSWORD']});assert r.status_code==401,r.status_code
    with engine.connect()as db:
        row=db.execute(text('SELECT intentos_fallidos,bloqueado_hasta>now() FROM estado_autenticacion_usuario WHERE id_usuario=3')).one()
        assert tuple(row)==(5,True),row
    # Body ceiling is enforced before the login rate limit, including slash alias.
    for suffix in ('','/'):
        r=c.post('/api/auth/sesiones'+suffix,content=b'x'*(16*1024+1));assert r.status_code==413,r.status_code
print('PASS postgres_shared_fifth_failure_lock_and_correct_credentials_blocked')
print('PASS edge_login_16_kib_plus_one_body_ceiling_both_slash_forms')
