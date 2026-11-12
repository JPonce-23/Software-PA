"""Full app HTTP boundary offline, isolated from other suites' service doubles.

Run with unittest; no conftest, database, Docker, auth overrides or real login.
Controlled routes model failures; real auth/CSRF/validation reject before SQL.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
CASES = (
    'cors_head', 'cors_range', 'cors_if_range', 'cors_combined_credentials',
    'cors_foreign_origin', 'cors_forbidden_method', 'cors_forbidden_header',
    'cors_exposed_download_headers', 'error_401', 'error_403_csrf', 'error_404',
    'error_409', 'error_422', 'error_425', 'error_503', 'error_416',
    'error_500_allowed_origin', 'error_500_foreign_origin', 'error_500_no_origin',
    'document_codes_and_details', 'cache_more_restrictive', 'cache_public_removed',
    'cache_multiple_lines', 'get_head_ranges_multipart', 'success_headers_unchanged',
    'pool_timeout_allowed', 'pool_timeout_foreign', 'pool_timeout_no_origin',
    'pool_timeout_post_not_replayed', 'pool_timeout_csrf_middleware',
    'builtin_timeout_stays_500', 'integrity_error_stays_409',
    'session_cookie_flags', 'stream_error_not_replaced', 'non_http_passthrough',
)


def worker():
    import asyncio
    import hashlib
    import logging
    import secrets
    import tempfile
    # All values here are synthetic. Never load an institutional .env/config.
    os.environ.update(APP_ENV='test', PYTHON_DOTENV_DISABLED='1',
        DB_RUNTIME_USER='ss12_offline', DB_RUNTIME_PASSWORD=secrets.token_hex(32),
        DB_HOST='/tmp/ss12-offline-no-server', DB_PORT='5432', DB_NAME='software_pa_test',
        SECRET_KEY=secrets.token_hex(48), CORS_ORIGINS='https://qa.invalid',
        AUTH_COOKIE_SECURE='true', AUTH_COOKIE_SAMESITE='lax', AUTH_TRUSTED_PROXY_IPS='')
    attempts = []

    def audit(kind, args):
        if kind == 'socket.connect':
            attempts.append('socket.connect')
            raise AssertionError('Offline QA forbids network/database connections')
        if kind == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            if Path(os.fsdecode(args[0])).name.startswith('.env'):
                raise AssertionError('Offline QA forbids .env reads')

    sys.addaudithook(audit)
    logging.disable(logging.CRITICAL)
    sys.path.insert(0, str(ROOT / 'backend'))
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from starlette.responses import JSONResponse, Response
    from app.main import app
    from app import database
    from sqlalchemy import event
    from sqlalchemy.exc import TimeoutError as SQLTimeoutError, IntegrityError
    from unittest.mock import patch
    from types import SimpleNamespace

    @event.listens_for(database.engine, 'do_connect')
    def deny_database(*args):
        # libpq uses C sockets, which do not emit Python socket.connect audits.
        attempts.append('database_connect')
        raise AssertionError('Offline QA forbids libpq connections')

    from app.config import AUTH_SETTINGS
    from app.http_security import ErrorHeadersMiddleware
    from app.routers.authentication import _set_auth_cookies
    from app.services.document_download import DescriptorDownloadResponse
    from app.services.document_errors import document_error
    assert not app.dependency_overrides
    origin = {'Origin': 'https://qa.invalid'}
    detail = 'SS12 synthetic compatible detail'
    sentinel = 'SS12_PRIVATE_EXCEPTION_SENTINEL'
    directory = tempfile.TemporaryDirectory(prefix='ss12-http-boundary-')
    root = Path(directory.name); (root / '17').mkdir(mode=0o700)
    content = b'SS12_SYNTHETIC_BINARY\x00\xff0123456789'
    (root / '17/owned.bin').write_bytes(content)

    @app.get('/__ss12/errors/{status}')
    def controlled(status: int):
        if status == 500:
            raise RuntimeError('/private/' + sentinel)
        if status in (409, 425):
            raise document_error(status, detail,
                'DOCUMENT_DUPLICATE' if status == 409 else 'DOCUMENT_OPERATION_PENDING',
                headers={'Retry-After': '3'} if status == 425 else None)
        raise HTTPException(status, detail, headers={'Retry-After': '5'} if status == 503 else None)

    @app.api_route('/__ss12/download', methods=['GET', 'HEAD'])
    def download():
        return DescriptorDownloadResponse(root=root, relative='17/owned.bin',
            document_id=17, size=len(content), sha256=hashlib.sha256(content).hexdigest(),
            filename='synthetic.bin')

    @app.get('/__ss12/cache/{mode}')
    def cache(mode: str):
        value = {'strict': 'private, no-store, no-cache="Set-Cookie, Authorization", max-age=0, must-revalidate',
                 'public': 'public, max-age=0', 'success': 'private, max-age=0'}[mode]
        return JSONResponse({'detail': detail}, status_code=200 if mode == 'success' else 409,
                            headers={'Cache-Control': value, 'X-Preserved': 'yes'})

    @app.get('/__ss12/cookies')
    def cookies():
        response = Response()
        _set_auth_cookies(response, session_token='SS12_SYNTHETIC_SESSION', csrf_token='SS12_SYNTHETIC_CSRF')
        return response

    pool_calls=[]

    @app.api_route('/__ss12/pool-timeout', methods=['GET','POST'])
    def pool_timeout():
        pool_calls.append(1)
        raise SQLTimeoutError(sentinel+' SELECT synthetic secret')

    @app.get('/__ss12/builtin-timeout')
    def builtin_timeout():raise TimeoutError(sentinel)

    @app.get('/__ss12/integrity')
    def integrity():raise IntegrityError('SELECT '+sentinel,{'secret':sentinel},RuntimeError(sentinel))

    client = TestClient(app, base_url='https://qa.invalid', raise_server_exceptions=False)
    results = {}

    def check(name, fn):
        try:
            fn()
            results[name] = {'status': 'PASS'}
        except Exception as error:
            results[name] = {'status': 'FAIL', 'reason': type(error).__name__ + ': ' + str(error)}

    def security(response, status):
        assert response.status_code == status, (response.status_code, status)
        assert response.headers.get('x-content-type-options') == 'nosniff'
        assert response.headers.get('cache-control') == 'private, no-store'
        assert response.headers.get('access-control-allow-origin') == 'https://qa.invalid'
        assert response.headers.get('access-control-allow-credentials') == 'true'
        assert 'origin' in response.headers.get('vary', '').lower()
        assert sentinel not in response.text and '/private/' not in response.text

    def preflight(method='GET', headers='Idempotency-Key,X-CSRF-Token', allowed=True, foreign=False):
        response = client.options('/__ss12/download', headers={
            'Origin': 'https://foreign.invalid' if foreign else 'https://qa.invalid',
            'Access-Control-Request-Method': method, 'Access-Control-Request-Headers': headers})
        assert response.status_code == (200 if allowed else 400)
        if foreign:
            assert 'access-control-allow-origin' not in response.headers
        else:
            assert response.headers['access-control-allow-origin'] == 'https://qa.invalid'
            assert response.headers['access-control-allow-credentials'] == 'true'
            assert '*' not in response.headers['access-control-allow-origin']
        if not allowed:
            security(response, 400) if not foreign else None

    check('cors_head', lambda: preflight('HEAD'))
    check('cors_range', lambda: preflight(headers='Range'))
    check('cors_if_range', lambda: preflight(headers='If-Range'))
    check('cors_combined_credentials', lambda: preflight(headers='Range,If-Range,Idempotency-Key,X-CSRF-Token,Content-Type'))
    check('cors_foreign_origin', lambda: preflight(allowed=False, foreign=True))
    check('cors_forbidden_method', lambda: preflight('TRACE', allowed=False))
    check('cors_forbidden_header', lambda: preflight(headers='X-SS12-Forbidden', allowed=False))

    def exposed():
        r = client.get('/__ss12/errors/409', headers=origin)
        security(r, 409)
        values = {v.strip().lower() for v in r.headers['access-control-expose-headers'].split(',')}
        assert {'x-document-error-code', 'content-disposition', 'content-range', 'accept-ranges',
                'etag', 'last-modified', 'idempotency-key', 'idempotency-replayed',
                'x-document-operation-id', 'x-document-operation-state', 'retry-after'} <= values

    check('cors_exposed_download_headers', exposed)
    check('error_401', lambda: security(client.get('/api/documentos/99999999/versiones', headers=origin), 401))

    def csrf():
        r = client.post('/api/auth/sesiones')
        assert r.status_code == 403 and r.json() == {'detail': 'Origen no permitido'}
        assert 'access-control-allow-origin' not in r.headers
        client.cookies.set(AUTH_SETTINGS.session_cookie_name, 'SS12_SYNTHETIC_UNKNOWN')
        try:
            r = client.post('/api/documentos/99999999/versiones', headers=origin)
            security(r, 403)
            assert r.json() == {'detail': 'Protección CSRF inválida'}
        finally:
            client.cookies.clear()

    check('error_403_csrf', csrf)
    check('error_404', lambda: security(client.get('/api/__ss12_missing', headers=origin), 404))
    check('error_409', lambda: security(client.get('/__ss12/errors/409', headers=origin), 409))
    check('error_422', lambda: security(client.post('/api/auth/sesiones', headers=origin, data={}), 422))
    check('error_425', lambda: security(client.get('/__ss12/errors/425', headers=origin), 425))
    check('error_503', lambda: security(client.get('/__ss12/errors/503', headers=origin), 503))
    check('error_416', lambda: security(client.get('/__ss12/download', headers={**origin, 'Range': 'bytes=999999-'}), 416))

    def internal_error(headers):
        r = client.get('/__ss12/errors/500', headers=headers)
        assert r.status_code == 500 and r.json() == {'detail': 'Error interno del servidor'}
        assert sentinel not in r.text and '/private/' not in r.text
        assert r.headers['x-content-type-options'] == 'nosniff'
        assert r.headers['cache-control'] == 'private, no-store'
        if headers == origin:
            security(r, 500)
        else:
            assert 'access-control-allow-origin' not in r.headers

    check('error_500_allowed_origin', lambda: internal_error(origin))
    check('error_500_foreign_origin', lambda: internal_error({'Origin': 'https://foreign.invalid'}))
    check('error_500_no_origin', lambda: internal_error({}))

    def pool_error(headers,method='GET'):
        before=len(pool_calls)
        r=client.request(method,'/__ss12/pool-timeout',headers=headers)
        assert len(pool_calls)==before+1
        assert r.status_code==503 and r.json()=={'detail':'Servicio temporalmente no disponible'}
        assert sentinel not in r.text and 'SELECT' not in r.text
        assert r.headers['x-content-type-options']=='nosniff'
        assert r.headers['cache-control']=='private, no-store'
        if headers==origin:security(r,503)
        else:assert 'access-control-allow-origin' not in r.headers

    check('pool_timeout_allowed',lambda:pool_error(origin))
    check('pool_timeout_foreign',lambda:pool_error({'Origin':'https://foreign.invalid'}))
    check('pool_timeout_no_origin',lambda:pool_error({}))
    check('pool_timeout_post_not_replayed',lambda:pool_error(origin,'POST'))

    def middleware_timeout():
        import app.main as main
        closed=[]
        with patch.object(main,'SessionLocal',return_value=SimpleNamespace(close=lambda:closed.append(1))), \
             patch.object(main.authentication_service,'validate_csrf',side_effect=SQLTimeoutError(sentinel)):
            r=client.post('/api/proyectos',headers={**origin,'X-CSRF-Token':'SYNTHETIC',
                'Cookie':f'{AUTH_SETTINGS.session_cookie_name}=SYNTHETIC; {AUTH_SETTINGS.csrf_cookie_name}=SYNTHETIC'},json={})
        security(r,503)
        assert r.json()=={'detail':'Servicio temporalmente no disponible'} and closed==[1]

    check('pool_timeout_csrf_middleware',middleware_timeout)
    check('builtin_timeout_stays_500',lambda:security(client.get('/__ss12/builtin-timeout',headers=origin),500))
    check('integrity_error_stays_409',lambda:security(client.get('/__ss12/integrity',headers=origin),409))

    def details():
        for status, code in [(409, 'DOCUMENT_DUPLICATE'), (425, 'DOCUMENT_OPERATION_PENDING')]:
            r = client.get(f'/__ss12/errors/{status}', headers=origin)
            assert r.json() == {'detail': detail} and r.headers['x-document-error-code'] == code
        assert client.get('/__ss12/errors/425').headers['retry-after'] == '3'
        assert client.get('/__ss12/errors/503').headers['retry-after'] == '5'

    check('document_codes_and_details', details)

    def strict_cache():
        r = client.get('/__ss12/cache/strict')
        assert r.headers['cache-control'] == 'private, no-store, no-cache="Set-Cookie, Authorization", max-age=0, must-revalidate'
        assert r.headers['x-preserved'] == 'yes'

    check('cache_more_restrictive', strict_cache)
    check('cache_public_removed', lambda: unittest.TestCase().assertEqual(
        client.get('/__ss12/cache/public').headers['cache-control'], 'max-age=0, private, no-store'))

    def multiple():
        async def inner(scope, receive, send):
            await send({'type': 'http.response.start', 'status': 409, 'headers': [
                (b'cache-control', b'no-cache'), (b'cache-control', b'must-revalidate')]})
        messages = []
        async def send(message): messages.append(message)
        asyncio.run(ErrorHeadersMiddleware(inner)({'type': 'http'}, None, send))
        values = [v for k, v in messages[0]['headers'] if k == b'cache-control']
        assert values == [b'no-cache, must-revalidate, private, no-store']

    check('cache_multiple_lines', multiple)

    def downloads():
        r = client.get('/__ss12/download', headers=origin)
        assert r.status_code == 200 and r.content == content
        assert r.headers['content-type'] == 'application/octet-stream'
        assert r.headers['cache-control'] == 'private, no-store'
        assert r.headers['x-content-type-options'] == 'nosniff'
        assert int(r.headers['content-length']) == len(content)
        h = client.head('/__ss12/download', headers=origin)
        assert h.status_code == 200 and not h.content and h.headers['content-length'] == r.headers['content-length']
        p = client.get('/__ss12/download', headers={**origin, 'Range': 'bytes=1-4', 'If-Range': r.headers['etag']})
        assert p.status_code == 206 and p.content == content[1:5]
        p = client.get('/__ss12/download', headers={**origin, 'Range': 'bytes=1-4', 'If-Range': '"stale"'})
        assert p.status_code == 200 and p.content == content
        p = client.get('/__ss12/download', headers={**origin, 'Range': 'bytes=0-2,7-9'})
        assert p.status_code == 206 and p.headers['content-type'].startswith('multipart/byteranges;')
        assert int(p.headers['content-length']) == len(p.content)

    check('get_head_ranges_multipart', downloads)
    check('success_headers_unchanged', lambda: unittest.TestCase().assertEqual(
        client.get('/__ss12/cache/success').headers['cache-control'], 'private, max-age=0'))

    def cookies_check():
        values = client.get('/__ss12/cookies').headers.get_list('set-cookie')
        assert len(values) == 2 and all('Secure' in v and 'SameSite=lax' in v and 'Path=/' in v for v in values)
        assert sum('HttpOnly' in v for v in values) == 1
        client.cookies.clear()

    check('session_cookie_flags', cookies_check)

    def streamed_error():
        async def inner(scope, receive, send):
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': content, 'more_body': True})
            raise RuntimeError('SS12 controlled already-started stream')
        messages = []
        async def send(message): messages.append(message)
        with unittest.TestCase().assertRaisesRegex(RuntimeError, 'already-started'):
            asyncio.run(ErrorHeadersMiddleware(inner)({'type': 'http'}, None, send))
        assert len(messages) == 2 and messages[0]['status'] == 200 and messages[1]['body'] is content

    check('stream_error_not_replaced', streamed_error)

    def non_http():
        seen = []
        async def inner(scope, receive, send): seen.append(scope['type'])
        asyncio.run(ErrorHeadersMiddleware(inner)({'type': 'lifespan'}, None, None))
        assert seen == ['lifespan']

    check('non_http_passthrough', non_http)
    assert not attempts and not app.dependency_overrides
    client.close(); database.engine.dispose(); directory.cleanup()
    print(json.dumps({'cases': results, 'database_or_network_attempts': attempts,
                      'dependency_overrides': 0, 'authentication_positive_native': 'PENDING_AUTHORIZATION'}))


class HTTPBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--worker'],
            cwd=ROOT, env={'PATH': os.defpath, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'},
            capture_output=True, text=True, timeout=60)
        if run.returncode:
            raise AssertionError('Offline full-app worker failed: ' + run.stderr[-3000:])
        cls.report = json.loads(run.stdout)
        if cls.report['database_or_network_attempts'] or cls.report['dependency_overrides']:
            raise AssertionError('Offline boundary guard lost coverage')


def method(name):
    def check_case(self):
        result = self.report['cases'][name]
        self.assertEqual(result['status'], 'PASS', result.get('reason', name))
    return check_case


for name in CASES:
    setattr(HTTPBoundaryTests, 'test_' + name, method(name))

if __name__ == '__main__':
    if '--worker' in sys.argv:
        worker()
    else:
        unittest.main(verbosity=2)
