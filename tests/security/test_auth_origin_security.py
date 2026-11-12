"""SS-04: pure origin tests and extracted auth branches with synthetic doubles.

No app startup, DB, HTTP server, bcrypt work, conftest or dependency installs.
These tests do NOT validate a distributed rate limiter (none is activated).
Run: python3 -B -m unittest discover -s tests/security -p 'test_auth_origin_security.py' -v
"""

import ast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock


ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / 'backend/app/services/authentication.py'
ROUTER = ROOT / 'backend/app/routers/authentication.py'
spec = importlib.util.spec_from_file_location('ss04_request_origin',
    ROOT / 'backend/app/services/request_origin.py')
origin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(origin)
PROXIES = ('10.0.0.2', '10.0.0.3', '2001:db8::2')
NOW = datetime(2026, 10, 28, tzinfo=timezone.utc)


def functions(path, names, namespace):
    """Execute only named source definitions, never module imports/startup."""
    tree = ast.parse(path.read_text())
    definitions = [node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    assert {node.name for node in definitions} == set(names)
    for node in definitions:
        node.decorator_list = []
    future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future, *definitions], type_ignores=[]))
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace


class Headers:
    def __init__(self, values=()):
        self.values = list(values)

    def getlist(self, name):
        return [v for k, v in self.values if k.lower() == name.lower()]

    def get(self, name, default=None):
        values = self.getlist(name)
        return values[0] if values else default


def request(peer='10.0.0.2', forwarded=('192.0.2.8',), *, headers=(), cookies=None,
            path='/api/auth/sesiones'):
    return SimpleNamespace(client=SimpleNamespace(host=peer) if peer else None,
        headers=Headers([*(('x-forwarded-for', v) for v in forwarded), *headers]),
        cookies=cookies or {}, method='POST', url=SimpleNamespace(path=path))


class OriginTests(unittest.TestCase):
    def resolve(self, peer='10.0.0.2', headers=('192.0.2.8',), trusted=PROXIES):
        return origin.resolve_client_ip(peer, headers, trusted)

    def test_untrusted_direct_peer_ignores_forged_headers(self):
        for spoof in ['192.0.2.99', '10.0.0.2', 'invalid', 'x' * 2048]:
            self.assertEqual(self.resolve('198.51.100.7', (spoof,)), '198.51.100.7')

    def test_empty_trust_does_not_accept_forwarded_or_wildcard(self):
        for trusted in [(), ('*',), ('10.0.0.0/8',)]:
            self.assertEqual(self.resolve(trusted=trusted), '10.0.0.2')

    def test_single_verified_proxy(self):
        self.assertEqual(self.resolve(), '192.0.2.8')

    def test_forged_leftmost_address_cannot_override_actual_appended_peer(self):
        self.assertEqual(self.resolve(headers=('192.0.2.99, 198.51.100.7',)), '198.51.100.7')

    def test_multiple_trusted_proxies_walk_from_right_to_left(self):
        self.assertEqual(self.resolve(headers=('192.0.2.99, 198.51.100.7, 10.0.0.3',)),
            '198.51.100.7')

    def test_untrusted_intermediary_stops_chain(self):
        self.assertEqual(self.resolve(headers=('192.0.2.8, 198.51.100.7, 10.0.0.3',)),
            '198.51.100.7')

    def test_all_trusted_hops_conservatively_fall_back_to_socket_peer(self):
        self.assertEqual(self.resolve(headers=('10.0.0.3, 2001:db8::2',)), '10.0.0.2')

    def test_duplicate_headers_are_ambiguous_even_when_equal(self):
        for values in [('192.0.2.8', '198.51.100.7'), ('192.0.2.8', '192.0.2.8')]:
            self.assertEqual(self.resolve(headers=values), '10.0.0.2')

    def test_missing_empty_or_malformed_chain_uses_peer(self):
        for values in [(), ('',), (' , ',), (',192.0.2.8',), ('192.0.2.8,',),
                       ('garbage, 192.0.2.8',), ('unknown',), ('[2001:db8::8]',),
                       ('192.0.2.8:443',), ('host.example',), ('fe80::1%eth0',)]:
            with self.subTest(values=values):
                self.assertEqual(self.resolve(headers=values), '10.0.0.2')

    def test_no_valid_peer_never_uses_header(self):
        for peer in [None, '', 'host.example', 'fe80::1%eth0', '192.0.2.8:80']:
            self.assertIsNone(self.resolve(peer=peer))

    def test_whitespace_and_ipv6_canonicalization(self):
        self.assertEqual(self.resolve('2001:0db8:0:0:0:0:0:2', (' 2001:0db8::9 , 10.0.0.3 ',)),
            '2001:db8::9')

    def test_ipv4_mapped_ipv6_peers_and_hops_use_exact_ipv4_trust(self):
        self.assertEqual(self.resolve('::ffff:10.0.0.2', ('::ffff:192.0.2.8',)), '192.0.2.8')

    def test_control_characters_are_rejected(self):
        for char in ['\x00', '\n', '\r', '\t', '\x7f']:
            self.assertEqual(self.resolve(headers=('192.0.2.8' + char,)), '10.0.0.2')

    def test_chain_length_and_hop_budgets(self):
        self.assertEqual(self.resolve(headers=('192.0.2.8' + ' ' * 1015,)), '192.0.2.8')
        self.assertEqual(self.resolve(headers=('192.0.2.8' + ' ' * 1016,)), '10.0.0.2')
        self.assertEqual(self.resolve(headers=(','.join(['192.0.2.8'] * 16),)), '192.0.2.8')
        self.assertEqual(self.resolve(headers=(','.join(['192.0.2.8'] * 17),)), '10.0.0.2')

    def test_other_forwarding_headers_do_not_change_auth_ip(self):
        namespace = functions(AUTH, ['_request_ip'], {
            'resolve_client_ip': origin.resolve_client_ip,
            'AUTH_SETTINGS': SimpleNamespace(trusted_proxy_ips=PROXIES)})
        req = request(forwarded=(), headers=[('Forwarded', 'for=192.0.2.99'),
            ('X-Real-IP', '192.0.2.99')])
        self.assertEqual(namespace['_request_ip'](req), '10.0.0.2')

    def test_auth_wrapper_retains_duplicates_for_ambiguity_check(self):
        namespace = functions(AUTH, ['_request_ip'], {
            'resolve_client_ip': origin.resolve_client_ip,
            'AUTH_SETTINGS': SimpleNamespace(trusted_proxy_ips=PROXIES)})
        self.assertEqual(namespace['_request_ip'](request(forwarded=('192.0.2.8', '192.0.2.99'))),
            '10.0.0.2')

    def test_shared_nat_resolution_is_stateless_and_does_not_reject_users(self):
        for _ in range(20):
            self.assertEqual(self.resolve(headers=('198.51.100.7',)), '198.51.100.7')

    def test_concurrent_resolution_has_no_shared_mutable_request_state(self):
        values = [f'192.0.2.{i}' for i in range(1, 33)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            result = list(pool.map(lambda v: self.resolve(headers=(v + ', 10.0.0.3',)), values))
        self.assertEqual(result, values)


class SyntheticHTTPError(Exception):
    def __init__(self, status_code, detail):
        self.status_code, self.detail = status_code, detail


class ExistingAuthenticationTests(unittest.TestCase):
    """Test actual unchanged auth bodies with fake ORM/bcrypt, not DB guarantees."""
    def harness(self, *, exists=True, active=True, valid=True, failures=0, blocked=None):
        user = SimpleNamespace(id_usuario=7, contrasena_hash='synthetic-hash', activo=active)
        state = SimpleNamespace(intentos_fallidos=failures, bloqueado_hasta=blocked)
        models = SimpleNamespace(Usuario=MagicMock(), EstadoAutenticacionUsuario=MagicMock(),
            SesionUsuario=lambda **kw: SimpleNamespace(id_sesion=11, **kw),
            EventoAcceso=lambda **kw: SimpleNamespace(id_evento=13, **kw))
        db = MagicMock()
        def query(model):
            q = MagicMock()
            q.filter.return_value = q
            q.with_for_update.return_value = q
            q.first.return_value = user if exists else None
            q.one_or_none.return_value = state
            return q
        db.query.side_effect = query
        ns = functions(AUTH, ['_request_ip', '_safe_user_agent', '_event', '_hash_secret',
            '_credentials_error', 'create_session'], {
            'models': models, 'func': MagicMock(), 'hashlib': hashlib,
            'timedelta': timedelta, '_utcnow': lambda: NOW,
            'AUTH_SETTINGS': SimpleNamespace(trusted_proxy_ips=PROXIES, lock_minutes=15,
                absolute_minutes=480),
            'resolve_client_ip': origin.resolve_client_ip,
            'password_matches': MagicMock(return_value=valid),
            '_DUMMY_PASSWORD_HASH': 'synthetic-dummy',
            'HTTPException': SyntheticHTTPError,
            'status': SimpleNamespace(HTTP_401_UNAUTHORIZED=401),
            '_link_state_event': MagicMock(), 'set_audit_context': MagicMock(),
            'secrets': SimpleNamespace(token_urlsafe=MagicMock(side_effect=['synthetic-session', 'synthetic-csrf']))})
        return ns, db, user, state

    def failure(self, ns, db):
        with self.assertRaises(SyntheticHTTPError) as caught:
            ns['create_session'](db, request(), ' User@qa.invalid ', 'synthetic-password')
        self.assertEqual((caught.exception.status_code, caught.exception.detail),
            (401, 'Credenciales incorrectas'))

    def test_existing_missing_inactive_and_blocked_keep_generic_error(self):
        for options in [dict(valid=False), dict(exists=False), dict(active=False),
                        dict(blocked=NOW + timedelta(minutes=5))]:
            ns, db, _, _ = self.harness(**options)
            self.failure(ns, db)
            ns['password_matches'].assert_called_once()
            db.commit.assert_called_once()

    def test_unknown_account_keeps_dummy_bcrypt_and_single_event(self):
        ns, db, _, _ = self.harness(exists=False)
        self.failure(ns, db)
        self.assertEqual(ns['password_matches'].call_args.args[1], 'synthetic-dummy')
        self.assertEqual(db.add.call_count, 1)
        self.assertIsNone(db.add.call_args.args[0].id_usuario)

    def test_fifth_failure_sets_existing_fifteen_minute_lock(self):
        ns, db, _, state = self.harness(valid=False, failures=4)
        self.failure(ns, db)
        self.assertEqual((state.intentos_fallidos, state.bloqueado_hasta),
            (5, NOW + timedelta(minutes=15)))
        self.assertEqual(db.add.call_args.args[0].motivo_codigo, 'quinto_fallo')
        ns['_link_state_event'].assert_called_once_with(db, 13)

    def test_requests_during_lock_do_not_extend_it_or_mutate_failure_count(self):
        deadline = NOW + timedelta(minutes=5)
        ns, db, _, state = self.harness(failures=5, blocked=deadline)
        for _ in range(3): self.failure(ns, db)
        self.assertEqual((state.intentos_fallidos, state.bloqueado_hasta), (5, deadline))
        self.assertEqual(db.add.call_count, 3)  # Existing residual: one DB event per rejected login.

    def test_expired_lock_with_bad_password_restarts_failure_count(self):
        ns, db, _, state = self.harness(valid=False, failures=5, blocked=NOW)
        self.failure(ns, db)
        self.assertEqual((state.intentos_fallidos, state.bloqueado_hasta), (1, None))

    def test_success_after_expired_lock_keeps_tokens_hashes_and_audit_origin(self):
        ns, db, user, state = self.harness(failures=5, blocked=NOW - timedelta(seconds=1))
        result = ns['create_session'](db, request(forwarded=('192.0.2.99, 198.51.100.7',)),
            'user@qa.invalid', 'synthetic-password')
        self.assertIs(result[0], user)
        session = result[1]
        self.assertEqual(result[2:], ('synthetic-session', 'synthetic-csrf'))
        self.assertEqual(session.token_hash, hashlib.sha256(b'synthetic-session').hexdigest())
        self.assertEqual(session.csrf_hash, hashlib.sha256(b'synthetic-csrf').hexdigest())
        self.assertEqual(session.expira_en, NOW + timedelta(minutes=480))
        self.assertEqual((state.intentos_fallidos, state.bloqueado_hasta), (0, None))
        event = db.add.call_args.args[0]
        self.assertEqual(event.motivo_codigo, 'inicio_sesion')
        self.assertEqual((session.ip_creacion, event.ip_origen), ('198.51.100.7', '198.51.100.7'))
        db.commit.assert_called_once()

    def test_synthetic_users_sharing_nat_keep_independent_authentication_state(self):
        for _ in range(6):
            ns, db, _, state = self.harness()
            ns['create_session'](db, request(), 'user@qa.invalid', 'synthetic-password')
            self.assertEqual(state.intentos_fallidos, 0)

    def test_event_sanitizes_agent_and_uses_nearest_untrusted_hop(self):
        ns, db, _, _ = self.harness(valid=False)
        req = request(forwarded=('192.0.2.99, 198.51.100.7, 10.0.0.3',),
            headers=[('user-agent', 'synthetic\nagent' + 'x' * 600)])
        with self.assertRaises(SyntheticHTTPError):
            ns['create_session'](db, req, 'user@qa.invalid', 'synthetic-password')
        event = db.add.call_args.args[0]
        self.assertEqual(event.ip_origen, '198.51.100.7')
        self.assertEqual(len(event.user_agent), 512)
        self.assertNotIn('\n', event.user_agent)


class CookieAndCSRFTests(unittest.TestCase):
    def test_existing_secure_cookie_flags_and_clearing(self):
        settings = SimpleNamespace(absolute_minutes=480, cookie_secure=True,
            cookie_samesite='lax', session_cookie_name='__Host-pa_session',
            csrf_cookie_name='__Host-pa_csrf')
        ns = functions(ROUTER, ['_set_auth_cookies', '_clear_auth_cookies'], {'AUTH_SETTINGS': settings})
        response = MagicMock()
        ns['_set_auth_cookies'](response, session_token='synthetic-session', csrf_token='synthetic-csrf')
        calls = response.set_cookie.call_args_list
        self.assertEqual([c.args[0] for c in calls], ['__Host-pa_session', '__Host-pa_csrf'])
        self.assertEqual([c.kwargs['httponly'] for c in calls], [True, False])
        for call in calls:
            self.assertEqual({k: call.kwargs[k] for k in ['secure', 'samesite', 'path', 'max_age']},
                dict(secure=True, samesite='lax', path='/', max_age=28800))
            self.assertNotIn('domain', call.kwargs)
        ns['_clear_auth_cookies'](response)
        self.assertEqual(response.delete_cookie.call_count, 2)

    def guard(self):
        self.db = MagicMock()
        self.validate = MagicMock(return_value=True)
        self.next = AsyncMock(return_value='accepted')
        self.settings = SimpleNamespace(allowed_origins=('https://qa.invalid',),
            session_cookie_name='session', csrf_cookie_name='csrf')
        ns = functions(ROOT / 'backend/app/main.py', ['csrf_cookie_guard'], {
            'AUTH_SETTINGS': self.settings, 'SessionLocal': lambda: self.db,
            'authentication_service': SimpleNamespace(validate_csrf=self.validate),
            'JSONResponse': lambda **kw: SimpleNamespace(**kw)})
        return lambda req: asyncio.run(ns['csrf_cookie_guard'](req, self.next))

    def test_login_origin_is_still_required(self):
        guard = self.guard()
        rejected = guard(request(headers=[('Origin', 'https://forged.invalid')]))
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(guard(request(headers=[('Origin', 'https://qa.invalid')])), 'accepted')
        self.validate.assert_not_called()

    def test_mutation_with_session_without_csrf_is_rejected_before_db(self):
        guard = self.guard()
        rejected = guard(request(cookies={'session': 'synthetic'}, path='/api/auth/logout'))
        self.assertEqual(rejected.status_code, 403)
        self.validate.assert_not_called()
        self.next.assert_not_awaited()

    def test_valid_csrf_still_checks_session_secret_and_closes_db_double(self):
        guard = self.guard()
        req = request(headers=[('Origin', 'https://qa.invalid'), ('X-CSRF-Token', 'synthetic-csrf')],
            cookies={'session': 'synthetic-session', 'csrf': 'synthetic-csrf'}, path='/api/auth/logout')
        self.assertEqual(guard(req), 'accepted')
        self.validate.assert_called_once_with(self.db, 'synthetic-session', 'synthetic-csrf')
        self.db.close.assert_called_once()

    def test_invalid_csrf_hash_is_rejected_and_db_double_closed(self):
        guard = self.guard()
        self.validate.return_value = False
        req = request(headers=[('Origin', 'https://qa.invalid'), ('X-CSRF-Token', 'synthetic-csrf')],
            cookies={'session': 'synthetic-session', 'csrf': 'synthetic-csrf'}, path='/api/auth/logout')
        self.assertEqual(guard(req).status_code, 403)
        self.db.close.assert_called_once()
        self.next.assert_not_awaited()


class StartupPolicyTests(unittest.TestCase):
    def test_image_and_both_compose_commands_disable_peer_rewriting(self):
        dockerfile = (ROOT / 'backend/Dockerfile').read_text()
        image_command = json.loads(next(line[4:] for line in dockerfile.splitlines() if line.startswith('CMD ')))
        base = (ROOT / 'docker-compose.yml').read_text()
        base_command = json.loads(next(line.strip()[9:] for line in base.splitlines()
            if line.strip().startswith('command: ["uvicorn"')))
        override = (ROOT / 'docker-compose.override.yml').read_text().split('    volumes:', 1)[0]
        override_command = [line.strip()[2:] for line in override.splitlines() if line.strip().startswith('- ')]
        for command in [image_command, base_command, override_command]:
            self.assertIn('--no-proxy-headers', command)
            self.assertNotIn('--proxy-headers', command)
            self.assertNotIn('--forwarded-allow-ips', command)


if __name__ == '__main__':
    unittest.main()
