"""Opt-in end-to-end deployment checks using ONLY the named disposable lab.

Requires PR6_DEPLOY_QA=SYNTHETIC_DISPOSABLE_ONLY and the matching PostgreSQL
cluster marker. Never provisions infrastructure or applies migrations. Supply explicit lab settings.
Fixtures contain no real data. Run with the candidate image and UID 10001.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import ssl
import stat
import sys
import time
import uuid
from unittest.mock import patch

import httpx
from sqlalchemy import text
from fastapi import HTTPException, UploadFile

assert os.environ.get('PR6_DEPLOY_QA')=='SYNTHETIC_DISPOSABLE_ONLY'
assert os.geteuid()==10001
from app.database import engine, SessionLocal
from app import models
from app.services import documents, document_recovery_execution
from app.services.document_coordination import WriterLease
if len(Path(__file__).resolve().parents)>2:
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend/tests'))
from _document_samples import minimal_pdf

BASE='https://ssalfer.qa.invalid'
CONTEXT=ssl.create_default_context(cafile='/qa/fullchain.pem')
results=[]
def passed(name):
    results.append(name);print('PASS',name,flush=True)
def status(response, expected):
    assert response.status_code==expected, (response.request.method,response.request.url.path,response.status_code,response.text[:180])
    return response
def client():return httpx.Client(base_url=BASE,verify=CONTEXT,trust_env=False,timeout=90)
def login(c,username=None):
    response=c.post('/api/auth/sesiones',headers={'Origin':BASE,'X-Forwarded-For':'192.0.2.77'},data={'username':username or os.environ['QA_USERNAME'],'password':os.environ['QA_PASSWORD']})
    status(response,200)
    c.headers.update({'Origin':BASE,'X-CSRF-Token':c.cookies['__Host-pa_csrf']})
    return response
def upload(c,doc,data,key=None):
    return c.post(f'/api/documentos/{doc}/versiones',headers={'Idempotency-Key':str(key or uuid.uuid4())},files={'archivo':('synthetic.pdf',data,'application/pdf')})
def sized_pdf(size):
    def build(pad):
        objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] >>',
            b'<< /Length '+str(pad).encode()+b' >>\nstream\n'+b'x'*pad+b'\nendstream']
        out=bytearray(b'%PDF-1.4\n');offsets=[]
        for i,obj in enumerate(objects,1):
            offsets.append(len(out));out.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
        start=len(out);out.extend(b'xref\n0 5\n0000000000 65535 f \n')
        for off in offsets:out.extend(f'{off:010} 00000 n \n'.encode())
        out.extend(f'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode())
        return bytes(out)
    pad=size-len(build(0))
    for _ in range(5):
        data=build(pad)
        if len(data)==size:return data
        pad+=size-len(data)
    raise AssertionError('size fixture')


def exercise_polygon(c,pid):
    # The browser intentionally hides legacy traces; confirm an actual DDV layer.
    with tempfile.TemporaryDirectory(prefix='pr6-gpkg-')as tmp:
        source=Path(tmp)/'synthetic.geojson';output=Path(tmp)/'synthetic.gpkg'
        source.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'etiqueta':'PR6_SYNTHETIC_DDV'},'geometry':{'type':'Polygon','coordinates':[[[-100,20],[-100,20.01],[-99.99,20.01],[-99.99,20],[-100,20]]]}}]}))
        subprocess.run(['ogr2ogr','-f','GPKG',str(output),str(source),'-nln','ddv','-a_srs','EPSG:4326'],check=True,capture_output=True)
        r=status(c.post(f'/api/proyectos/{pid}/geoespacial/ddv/importaciones',data={'fuente':'PR6_SYNTHETIC_DDV'},files={'archivo':('synthetic.gpkg',output.read_bytes(),'application/geopackage+sqlite3')}),201)
        record=r.json();assert record['validos']==1,record
        status(c.post(f"/api/importaciones/{record['id_importacion']}/confirmar",json={'confirmacion_explicita':True,'aceptar_advertencias':True}),200)
        mapa=status(c.get(f'/api/proyectos/{pid}/mapa'),200).json()
        assert any(f['geometry']['type']=='MultiPolygon'and f['properties']['tipo']=='derecho_via_proyecto'for f in mapa['features'])


def main():
    with engine.connect() as db:
        assert tuple(db.execute(text("SELECT current_database(),current_setting('cluster_name'),current_user")).one())==('software_pa_test','pr6-deployment-disposable','ss12_runner')
        fixture=db.execute(text('SELECT value FROM pr6_synthetic_fixture')).scalar_one()
        assert db.execute(text('SELECT max(version::int) FROM schema_migrations')).scalar_one()==32
        assert not db.execute(text("SELECT rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole FROM pg_roles WHERE rolname=current_user")).scalar_one()
    # Fresh documents make repeated lab runs independent; the historical file
    # is deliberately retained as a migration/access fixture.
    docs=[fixture['docs'][0]];pid=fixture['project']
    with SessionLocal()as db:
        from app.services.common import set_audit_context
        set_audit_context(db,1)
        target=db.query(models.DocumentoVinculo).filter_by(id_documento=docs[0],activo=True).one()
        for _ in range(6):
            doc=models.Documento(tipo_documento='pr6_qa',estado='disponible',titulo='PR6_SYNTHETIC',creado_por=1)
            db.add(doc);db.flush();docs.append(doc.id_documento)
            db.add(models.DocumentoVinculo(id_documento=doc.id_documento,entidad_tipo=target.entidad_tipo,entidad_id=target.entidad_id,creado_por=1))
        db.commit()
    passed('isolated_database_runtime_role_and_migrations_031_032')

    with client() as c:
        r=c.get('http://ssalfer.qa.invalid/dashboard.html?qa=synthetic')
        status(r,308);assert r.headers['location']==BASE+'/dashboard.html?qa=synthetic'
        for path,code in [('/Index.html',200),('/api/auth/sesion',401),('/not-found',404),('/docs',404),('/redoc',404),('/openapi.json',404),('/api/docs',404),('/deploy/tls/README.md',404),('/.env',404),('/js/vendor/leaflet-1.9.4/leaflet.js',200)]:
            r=status(c.get(path),code)
            for header,value in [('x-content-type-options','nosniff'),('cache-control','private, no-store'),('referrer-policy','no-referrer'),('x-frame-options','SAMEORIGIN')]:
                assert r.headers.get_list(header)==[value],(path,header,r.headers.get_list(header))
            assert 'max-age=31536000'==r.headers['strict-transport-security']
            assert len(r.headers.get_list('content-security-policy-report-only'))==1
            assert 'content-security-policy' not in r.headers
        status(c.get('/Index.html',headers={'Host':'hostile.invalid'}),421)
        passed('tls_trusted_lab_certificate_redirect_headers_errors_and_private_assets')

        # Preflight against FastAPI directly as well as the public boundary.
        for path in ('/docs','/redoc','/openapi.json'):
            status(c.get('http://backend:8000'+path),404)
        r=c.options('/api/documentos/1/versiones',headers={'Origin':BASE,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'X-CSRF-Token,Idempotency-Key'})
        status(r,200);assert r.headers['access-control-allow-origin']==BASE
        r=c.options('/api/documentos/1/versiones',headers={'Origin':'https://evil.invalid','Access-Control-Request-Method':'POST'})
        status(r,400);assert 'access-control-allow-origin'not in r.headers
        status(c.post('/api/auth/sesiones',headers={'Origin':'https://evil.invalid'},data={'username':'synthetic','password':'synthetic'}),403)
        response=login(c)
        cookies=response.headers.get_list('set-cookie');assert len(cookies)==2
        session=next(v for v in cookies if v.startswith('__Host-pa_session='))
        csrf=next(v for v in cookies if v.startswith('__Host-pa_csrf='))
        assert 'HttpOnly'in session and 'HttpOnly'not in csrf
        for cookie in cookies:
            assert 'Secure'in cookie and 'Path=/'in cookie and 'SameSite=lax'in cookie and 'Domain='not in cookie
        with socket.create_connection(('ssalfer.qa.invalid',443))as sock:source=sock.getsockname()[0]
        with engine.connect()as db:
            actual=str(db.execute(text("SELECT ip_origen FROM evento_acceso WHERE id_usuario=1 AND tipo_evento='login_exitoso' ORDER BY fecha_hora DESC LIMIT 1")).scalar_one())
            assert actual==source,(actual,source)
        r=c.post('/api/proyectos',headers={'X-CSRF-Token':'wrong'},json={});status(r,403)
        status(c.post('/api/proyectos',headers={'Origin':'https://evil.invalid'},json={}),403)
        r=c.post('/api/proyectos',json={'clave_proyecto':'PR6_CSRF_'+uuid.uuid4().hex[:8],'nombre_proyecto':'Synthetic CSRF check'});status(r,201)
        r=c.get(f'/api/documentos/{docs[0]}/versiones/')
        status(r,307);assert r.headers['location'].startswith(BASE+'/')
        passed('login_host_cookies_csrf_cors_forwarding_spoof_and_https_slash_redirect')

        path=f"/api/documentos/versiones/{fixture['legacy_version']}/descarga"
        r=status(c.get(path),200);assert hashlib.sha256(r.content).hexdigest()==fixture['legacy_sha']
        assert r.headers['content-type']=='application/octet-stream'and r.headers['content-disposition'].startswith('attachment;')
        status(c.get(path,headers={'Range':'bytes=0-7'}),206)
        r=status(c.head(path),200);assert not r.content
        with client()as other:
            login(other,'unassigned@example.invalid')
            status(other.get(path),403)
            status(upload(other,docs[0],minimal_pdf('forbidden synthetic')),403)
        passed('historical_download_head_range_and_unassigned_operator_denial')

        if os.getenv('PR6_QA_SKIP_VERIFIED_SIZES') != '1':
            # Effective size enforcement: Content-Length and chunked, across edge AND
            # inner SSALFER proxy. Unauthenticated body probes never write data.
            for origin in (BASE,'http://frontend_ssalfer:80'):
                for route in ('/api/proyectos','/Index.html'):
                    r=c.post(origin+route,content=b'x'*(1024**2),headers={'Content-Type':'application/json'})
                    assert r.status_code in (200,405,422),r.status_code
                    r=c.post(origin+route,content=b'x'*(1024**2+1));status(r,413)
                for suffix in ('','/'):
                    docroute=f'/api/documentos/{docs[1]}/versiones'+suffix
                    with httpx.Client(verify=CONTEXT,trust_env=False,timeout=90)as anonymous:
                        status(anonymous.post(origin+docroute,content=b'x'*(26*1024**2)),307 if suffix else 401)
                    status(c.post(origin+docroute,content=b'x'*(26*1024**2+1)),413)
                    for family in ('','geoespacial/ddv/','geoespacial/nucleos/','geoespacial/parcelas/'):
                        route=f'/api/proyectos/{pid}/{family}importaciones'+suffix
                        # Exactly at outer quota reaches the application; +1 is 413.
                        with httpx.Client(verify=CONTEXT,trust_env=False,timeout=90)as anonymous:
                            r=anonymous.post(origin+route,headers={'Content-Type':'application/octet-stream'},content=b'x'*(101*1024**2))
                            status(r,307 if suffix else 401)
                            status(anonymous.post(origin+route,content=b'x'*(101*1024**2+1)),413)
                def chunks():
                    for _ in range(17):yield b'x'*65536
                status(c.post(origin+'/api/proyectos',content=chunks()),413)
            passed('outer_limits_all_proxy_routes_slashes_chunked_and_101_mib_boundaries')

            # A real valid file at 25 MiB succeeds; max+1 reaches API and fails there.
            data=sized_pdf(25*1024**2)
            r=status(upload(c,docs[1],data),201);version=r.json()['id_documento_version']
            downloaded=status(c.get(f'/api/documentos/versiones/{version}/descarga'),200)
            assert downloaded.content==data
            r=status(upload(c,docs[2],sized_pdf(25*1024**2+1)),413)
            assert '26214400 bytes (25 MiB)'in r.json()['detail']
            # Both proxies accept a normal multipart file above the old 20 MiB fallback.
            with httpx.Client(base_url='http://frontend_ssalfer:80',trust_env=False,timeout=90)as inner:
                # Cookies deliberately supplied only to the isolated synthetic origin.
                inner.headers.update({'Origin':BASE,'X-CSRF-Token':c.cookies['__Host-pa_csrf'],'Cookie':f"__Host-pa_session={c.cookies['__Host-pa_session']}; __Host-pa_csrf={c.cookies['__Host-pa_csrf']}"})
                status(upload(inner,docs[2],data),201)
            passed('25_mib_valid_multipart_upload_download_and_file_limit_plus_one')

        # Distinct keys/version ordering plus repeated key across actual workers.
        distinct_keys={i:uuid.uuid4()for i in range(4)}
        def concurrent_upload(index,key=None):
            with client()as worker:
                worker.cookies.update(c.cookies);worker.headers.update(dict(c.headers))
                return upload(worker,docs[3],minimal_pdf('concurrent '+str(index)),key or distinct_keys[index])
        with ThreadPoolExecutor(max_workers=4)as pool:
            records=list(pool.map(concurrent_upload,range(4)))
        for index,response in enumerate(records):
            assert response.status_code in (201,503),response.status_code
            if response.status_code==503:records[index]=concurrent_upload(index)
        assert [r.status_code for r in records]==[201]*4,[r.status_code for r in records]
        assert sorted(r.json()['numero_version']for r in records)==[1,2,3,4]
        key=uuid.uuid4()
        with ThreadPoolExecutor(max_workers=8)as pool:
            repeated=list(pool.map(lambda _:concurrent_upload(99,key),range(8)))
        # SS-06 intentionally fails closed with 503 when parser slots are full.
        # That response must create no extra version; same-key retry succeeds.
        for r in repeated:assert r.status_code in (200,201,425,503),(r.status_code,r.text[:100])
        final=concurrent_upload(99,key);status(final,200)
        assert len({r.json()['id_documento_version']for r in repeated if r.status_code in (200,201)}|{final.json()['id_documento_version']})==1
        versions=status(c.get(f'/api/documentos/{docs[3]}/versiones'),200).json()
        assert len(versions)==5
        passed('two_worker_http_concurrency_unique_versions_and_shared_idempotency')

        # Inject a loss after publication but before SQL commit in this isolated
        # runner only. Recover using the unchanged real SS-12 service under 10001.
        request_key=uuid.uuid4();content=minimal_pdf('synthetic publication interruption')
        with SessionLocal()as db:
            user=db.get(models.Usuario,1)
            with patch.object(documents.operations,'confirm',side_effect=RuntimeError('synthetic commit loss')):
                try:asyncio.run(documents.store_version(db,docs[4],UploadFile(io.BytesIO(content),filename='synthetic.pdf'),user,idempotency_key=request_key))
                except HTTPException as e:assert e.status_code==409
                else:raise AssertionError('expected isolated publication loss')
        with engine.connect()as db:
            op=db.execute(text('SELECT id_operacion,ruta_prevista,estado FROM documento_operacion WHERE clave_idempotencia=:key'),{'key':request_key}).one()
            identity=db.execute(text('SELECT identidad FROM documento_coordinacion WHERE id_operacion=:op'),{'op':op[0]}).scalar_one()
        assert (Path('/app/uploads')/op[1]).read_bytes()==content
        attempt=uuid.uuid4()
        with WriterLease('/app/uploads',docs[4],op[0])as lease:
            assert lease.identity==identity
            r=document_recovery_execution.recover_document_operation(engine,1,docs[4],op[0],attempt_id=attempt,root='/app/uploads',reason='OPERATOR_REVIEW')
            assert (r.status,r.code)==('PENDING','ACTIVE_WRITER')
        r=document_recovery_execution.recover_document_operation(engine,1,docs[4],op[0],attempt_id=attempt,root='/app/uploads',reason='OPERATOR_REVIEW')
        assert r.status=='VERIFIED',(r.status,r.code)
        again=document_recovery_execution.recover_document_operation(engine,1,docs[4],op[0],attempt_id=attempt,root='/app/uploads',reason='OPERATOR_REVIEW')
        assert again.status=='VERIFIED'and r.version_id==again.version_id
        recovered=status(c.get(f'/api/documentos/{docs[4]}/versiones'),200).json();assert len(recovered)==1
        assert status(c.get(f"/api/documentos/versiones/{recovered[0]['id_documento_version']}/descarga"),200).content==content
        lock=Path('/app/uploads/.ss12-writers')/f'{docs[4]}-{op[0].hex}.lock'
        info=lock.stat();assert info.st_uid==10001 and stat.S_IMODE(info.st_mode)==0o600 and info.st_nlink==1
        passed('uid10001_ss12_lock_identity_active_writer_recovery_and_replay')

        # Real native GDAL -> PostGIS staging, confirmation, map and CSV export.
        geo=json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':{'type':'LineString','coordinates':[[-100,20],[-99.9,20.1]]}}]}).encode()
        r=status(c.post(f'/api/proyectos/{pid}/importaciones',data={'tipo_objetivo':'trazo_proyecto','fuente':'PR6_SYNTHETIC_ONLY'},files={'archivo':('synthetic.geojson',geo,'application/geo+json')}),201)
        record=r.json();assert record['validos']==1,record
        status(c.post(f"/api/importaciones/{record['id_importacion']}/confirmar",json={'confirmacion_explicita':True}),200)
        mapa=status(c.get(f'/api/proyectos/{pid}/mapa'),200).json()
        assert any(f['geometry']['type']=='MultiLineString'for f in mapa['features']),mapa
        r=status(c.get(f'/api/exportaciones/dashboard.csv?id_proyecto={pid}'),200)
        assert 'text/csv'in r.headers['content-type']and 'attachment'in r.headers['content-disposition']
        exercise_polygon(c,pid)
        passed('native_gdal_postgis_import_confirmation_map_and_csv_export')

        from scripts.check_upload_access import check
        assert check('/app/uploads')>0
        testdir=Path('/app/uploads')/'pr6-private-permission-probe';testdir.mkdir(mode=0o700)
        sentinel=testdir/'private';sentinel.write_bytes(b'synthetic');sentinel.chmod(0o600)
        before=(sentinel.stat().st_dev,sentinel.stat().st_ino)
        sentinel.chmod(0o622)
        try:check('/app/uploads')
        except ValueError as e:assert str(e)=='FILE_ACCESS_REQUIRED'
        else:raise AssertionError('preflight accepted public write')
        sentinel.chmod(0o600);assert (sentinel.stat().st_dev,sentinel.stat().st_ino)==before
        assert check('/app/uploads')>0
        passed('read_only_storage_preflight_rejects_unsafe_permissions_without_replacing_inodes')

        status(c.post('/api/auth/logout'),200)
        status(c.get('/api/auth/sesion'),401)
        # Exhaust login budget with a separate lab peer after successful flows.
        statuses=[]
        for _ in range(10):
            statuses.append(c.post('/api/auth/sesiones',data={'username':'absent@example.invalid','password':'synthetic'}).status_code)
        assert 429 in statuses and set(statuses)<={401,429},statuses
        passed('logout_invalidates_session_and_nginx_login_budget_returns_429')
    print('LIVE_CHECK_GROUPS',len(results),'ALL_PASS',flush=True)


if __name__=='__main__':main()
