"""SS-10: formatted logging + ASGI doubles, never imports app database/startup.

Native SQLAlchemy exception-only checks are optional; no PostgreSQL connection.
Run: python3 -B -m unittest discover -s tests/security -p 'test_safe_logging_security.py' -v
"""

import ast
import asyncio
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
import importlib.util
import io
import json
import logging
import logging.config
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app import safe_logging as safe


SENTINELS = (
    'SS10_SYNTH_PASSWORD_173bc48fe', '$2b$12$SS10_SYNTH_BCRYPT_HASH_8f3d7',
    'SS10_SYNTH_SESSION_TOKEN_483fe7', 'SS10_SYNTH_CSRF_TOKEN_18df47',
    '__Host-pa_session=SS10_SYNTH_COOKIE_531d7',
    'SS10_SYNTH_SQL_PARAMETER_e8a14', 'ss10.person.73b1@qa.invalid',
    'SS10_SYNTH_PERSON_ÑÁ_37df1', 'SS10_SYNTH_QUERY_a13d8',
    'SS10_SYNTH_DRIVER_DETAIL_71cf2',
)
ROUTE = SimpleNamespace(path='/api/personas/{id_persona}')


def scope():
    return {'type': 'http', 'method': 'POST', 'path': '/api/personas/' + SENTINELS[7],
            'raw_path': ('/api/personas/' + SENTINELS[7]).encode(),
            'query_string': ('password=' + SENTINELS[0] + '&token=' + SENTINELS[8]).encode(),
            'headers': [(b'cookie', SENTINELS[4].encode()), (b'x-request-id', SENTINELS[2].encode())],
            'client': ('192.0.2.8', 12345)}


class SensitiveError(Exception):
    def __init__(self):
        super().__init__(' '.join(SENTINELS))
        self.orig = RuntimeError(SENTINELS[-1])
        self.params = {'password': SENTINELS[0], 'email': SENTINELS[6]}
        self.statement = 'SELECT ' + SENTINELS[5]


class StatementError(SensitiveError): pass
class DBAPIError(StatementError): pass
class IntegrityError(DBAPIError): pass
class InternalError(DBAPIError): pass
class PostgreSQLError(SensitiveError): pass


def handlers():
    """Only extract handler functions; imports/decorators/engine never execute."""
    tree = ast.parse((ROOT / 'backend/app/main.py').read_text())
    definitions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
        and n.name in ('database_error_handler', 'global_exception_handler')]
    assert len(definitions) == 2
    for node in definitions: node.decorator_list = []
    ns = dict(StatementError=StatementError, DBAPIError=DBAPIError,
        IntegrityError=IntegrityError, InternalError=InternalError, PostgreSQLError=PostgreSQLError,
        log_request_error=safe.log_request_error,
        JSONResponse=lambda **kwargs: SimpleNamespace(**kwargs))
    exec(compile(ast.fix_missing_locations(ast.Module(body=definitions, type_ignores=[])),
        'isolated_main_handlers', 'exec'), ns)
    return ns


class FormattedLoggingTests(unittest.TestCase):
    def setUp(self):
        self.stream = io.StringIO()
        self.redirect = redirect_stderr(self.stream)
        self.redirect.__enter__()
        config = json.loads((ROOT / 'backend/logging.json').read_text())
        loggers = [logging.getLogger(), *[logging.getLogger(name) for name in config['loggers']]]
        self.previous = [(logger, list(logger.handlers), logger.level, logger.propagate, logger.disabled)
                         for logger in loggers]
        logging.config.dictConfig(config)
        self.handlers = handlers()

    def tearDown(self):
        for logger, old_handlers, level, propagate, disabled in self.previous:
            logger.handlers = old_handlers
            logger.setLevel(level)
            logger.propagate = propagate
            logger.disabled = disabled
        self.redirect.__exit__(None, None, None)

    def records(self):
        text = self.stream.getvalue()
        for sentinel in SENTINELS: self.assertNotIn(sentinel, text)
        records = [json.loads(line) for line in text.splitlines()]
        self.assertTrue(records)
        for record in records:
            self.assertIn('code', record)
            self.assertIn('category', record)
            self.assertIn('component', record)
            self.assertIn('level', record)
        return records

    def test_database_handler_preserves_409_and_categorizes_without_exception_text(self):
        for cls, code in [(IntegrityError, 'DB_INTEGRITY_ERROR'), (InternalError, 'DB_INTERNAL_ERROR'),
                          (DBAPIError, 'DB_API_ERROR')]:
            result = self.handlers['database_error_handler'](SimpleNamespace(scope=scope()), cls())
            self.assertEqual(result.status_code, 409)
            self.assertEqual(result.content, {'detail': 'La operación entra en conflicto con la integridad de los datos.'})
            record = self.records()[-1]
            self.assertEqual((record['code'], record['component'], record['status']), (code, 'database', 409))
            self.assertEqual(record['route'], '<unmatched>')
            self.assertRegex(record['correlation_id'], r'^[0-9a-f]{32}$')

    def test_statement_driver_and_third_party_errors_preserve_generic_500(self):
        for cls, code in [(StatementError, 'DB_STATEMENT_ERROR'), (PostgreSQLError, 'DB_DRIVER_ERROR'),
                          (SensitiveError, 'API_INTERNAL_ERROR')]:
            result = self.handlers['global_exception_handler'](SimpleNamespace(scope=scope()), cls())
            self.assertEqual((result.status_code, result.content), (500, {'detail': 'Error interno del servidor'}))
            self.assertEqual(self.records()[-1]['code'], code)

    def test_handler_and_formatter_never_access_str_repr_orig_or_params(self):
        class Explosive(Exception):
            def __str__(self): raise AssertionError('must not stringify')
            def __repr__(self): raise AssertionError('must not repr')
            @property
            def orig(self): raise AssertionError('must not read orig')
            @property
            def params(self): raise AssertionError('must not read params')
        self.handlers['global_exception_handler'](SimpleNamespace(scope=scope()), Explosive())
        logging.getLogger('uvicorn.error').error(Explosive(), exc_info=(Explosive, Explosive(), None))
        self.assertEqual(self.records()[-1]['component'], 'server')

    def test_final_formatter_excludes_cached_tracebacks_messages_args_and_extras(self):
        record = logging.LogRecord('sqlalchemy.engine.Engine', logging.ERROR, SENTINELS[7], 8,
            'unsafe SQL %s', (SENTINELS,), (SensitiveError, SensitiveError(), None))
        record.exc_text = 'cached traceback ' + ' '.join(SENTINELS)
        record.stack_info = 'stack ' + ' '.join(SENTINELS)
        record.safe_event = {'password': SENTINELS[0]}  # Not a trusted typed event.
        for handler in logging.getLogger('sqlalchemy').handlers: handler.handle(record)
        result = self.records()[-1]
        self.assertEqual((result['component'], result['level']), ('database', 'ERROR'))
        self.assertNotIn('filename', result)

    def test_server_sqlalchemy_driver_and_other_loggers_all_use_safe_output(self):
        for name, component in [('uvicorn.error', 'server'), ('uvicorn.access', 'server'),
                ('sqlalchemy.engine.Engine', 'database'), ('sqlalchemy.pool.impl.QueuePool', 'database'),
                ('psycopg2', 'database_driver'), ('third.party.' + SENTINELS[6], 'dependency')]:
            try:
                raise SensitiveError()
            except SensitiveError:
                logging.getLogger(name).critical(' '.join(SENTINELS), exc_info=True, stack_info=True)
            self.assertEqual(self.records()[-1]['component'], component)
            self.assertEqual(self.records()[-1]['level'], 'CRITICAL')

    def test_known_runtime_failures_retain_codes_without_interpolating_parameters(self):
        for name, template, code in [
                ('uvicorn.error', 'Exception in ASGI application\n', 'ASGI_APPLICATION_ERROR'),
                ('sqlalchemy.pool.impl.QueuePool', 'Exception terminating connection %r', 'DB_POOL_TERMINATION_ERROR'),
                ('uvicorn.error', 'Application startup complete.', 'SERVER_STARTED')]:
            logging.getLogger(name).error(template, SENTINELS[0], exc_info=(SensitiveError, SensitiveError(), None))
            self.assertEqual(self.records()[-1]['code'], code)

    def test_request_access_is_normalized_and_response_messages_unchanged(self):
        req = scope()
        messages = [{'type': 'http.response.start', 'status': 201,
                     'headers': [(b'set-cookie', SENTINELS[4].encode())]},
                    {'type': 'http.response.body', 'body': SENTINELS[2].encode()}]
        output = []
        async def app(s, receive, send):
            s['route'] = ROUTE
            logging.getLogger('sqlalchemy.pool').warning('unsafe ' + SENTINELS[-1])
            for message in messages: await send(message)
        async def send(message): output.append(message)
        asyncio.run(safe.SafeDiagnosticsMiddleware(app, [ROUTE])(req, MagicMock(), send))
        self.assertEqual(output, messages)
        record = self.records()[-1]
        self.assertEqual((record['route'], record['method'], record['status'], record['response_complete']),
            (ROUTE.path, 'POST', 201, True))
        self.assertNotEqual(record['correlation_id'], SENTINELS[2])
        self.assertEqual(len({r['correlation_id'] for r in self.records()}), 1)
        self.assertIsNone(safe._CURRENT.get())

    def test_unmatched_route_and_unrecognized_method_never_log_raw_values(self):
        req = scope(); req['method'] = SENTINELS[0]
        async def app(s, receive, send):
            s['route'] = SimpleNamespace(path='/' + SENTINELS[7])
            await send({'type': 'http.response.start', 'status': 404})
            await send({'type': 'http.response.body', 'body': b''})
        async def send(message): pass
        asyncio.run(safe.SafeDiagnosticsMiddleware(app, [ROUTE])(req, MagicMock(), send))
        self.assertEqual((self.records()[-1]['route'], self.records()[-1]['method']), ('<unmatched>', 'OTHER'))

    def test_unhandled_exception_rethrow_and_outer_handler_share_correlation(self):
        req = scope(); error = SensitiveError()
        async def app(s, receive, send):
            s['route'] = ROUTE
            raise error
        async def send(message): pass
        try:
            asyncio.run(safe.SafeDiagnosticsMiddleware(app, [ROUTE])(req, MagicMock(), send))
        except SensitiveError as caught:
            self.assertIs(caught, error)
            self.handlers['global_exception_handler'](SimpleNamespace(scope=req), caught)
            logging.getLogger('uvicorn.error').error('Exception in ASGI application', exc_info=True)
        records = self.records()
        own = [r for r in records if r['code'] != 'RUNTIME_DIAGNOSTIC']
        self.assertEqual(len(own), 2)
        self.assertEqual(len({r['correlation_id'] for r in own}), 1)
        self.assertEqual({r['route'] for r in own}, {ROUTE.path})
        self.assertIsNone(safe._CURRENT.get())

    def test_background_failure_records_actual_status_without_replacing_stream(self):
        req = scope(); output = []
        async def app(s, receive, send):
            s['route'] = ROUTE
            await send({'type': 'http.response.start', 'status': 200})
            await send({'type': 'http.response.body', 'body': b'done'})
            raise SensitiveError()
        async def send(message): output.append(message)
        with self.assertRaises(SensitiveError):
            asyncio.run(safe.SafeDiagnosticsMiddleware(app, [ROUTE])(req, MagicMock(), send))
        self.handlers['global_exception_handler'](SimpleNamespace(scope=req), SensitiveError())
        self.assertEqual(len(output), 2)
        record = self.records()[-1]
        self.assertEqual((record['code'], record['status'], record['response_complete']),
            ('API_INTERNAL_ERROR', 200, True))

    def test_partial_stream_failure_is_incomplete_and_keeps_actual_status(self):
        req = scope()
        async def app(s, receive, send):
            await send({'type': 'http.response.start', 'status': 206})
            await send({'type': 'http.response.body', 'body': b'partial', 'more_body': True})
            raise SensitiveError()
        async def send(message): pass
        with self.assertRaises(SensitiveError):
            asyncio.run(safe.SafeDiagnosticsMiddleware(app, [ROUTE])(req, MagicMock(), send))
        self.assertEqual((self.records()[-1]['status'], self.records()[-1]['response_complete']), (206, False))

    def test_concurrent_requests_have_distinct_server_generated_ids(self):
        async def app(s, receive, send):
            s['route'] = ROUTE
            await asyncio.sleep(0)
            logging.getLogger('sqlalchemy.pool').warning(SENTINELS[-1])
            await send({'type': 'http.response.start', 'status': 200})
            await send({'type': 'http.response.body', 'body': b''})
        async def send(message): pass
        async def run():
            middleware = safe.SafeDiagnosticsMiddleware(app, [ROUTE])
            await asyncio.gather(*(middleware(scope(), MagicMock(), send) for _ in range(8)))
        asyncio.run(run())
        ids = {r['correlation_id'] for r in self.records()}
        self.assertEqual(len(ids), 8)
        for correlation in ids: self.assertRegex(correlation, r'^[0-9a-f]{32}$')
        self.assertIsNone(safe._CURRENT.get())

    def test_logrecord_snapshot_does_not_retain_scope_request_or_exception(self):
        req = scope()
        context = safe.RequestDiagnostics('a' * 32, req, frozenset([ROUTE.path]))
        event = safe._event('internal_error', 'API_INTERNAL_ERROR', 'api', context)
        serialized = json.dumps(asdict(event))
        for sentinel in SENTINELS: self.assertNotIn(sentinel, serialized)
        self.assertNotIn('scope', asdict(event))
        self.assertNotIn('context', asdict(event))

    def test_unknown_error_category_is_replaced_by_fixed_code(self):
        safe.log_request_error(scope(), SENTINELS[0], 500)
        self.assertEqual(self.records()[-1]['code'], 'API_INTERNAL_ERROR')

    def test_non_http_scope_passes_through_without_request_diagnostics(self):
        req = {'type': 'lifespan'}
        async def app(s, receive, send): self.assertIs(s, req)
        asyncio.run(safe.SafeDiagnosticsMiddleware(app, [ROUTE])(req, MagicMock(), MagicMock()))
        self.assertEqual(self.stream.getvalue(), '')

    def test_handler_failure_fallback_never_prints_original_logrecord(self):
        handler = safe.SafeStreamHandler()
        record = logging.LogRecord('unsafe', logging.ERROR, '', 0, SENTINELS[0], (), None)
        handler.handleError(record)
        self.assertEqual(self.records()[-1]['code'], 'OBSERVABILITY_FAILURE')

    def test_cli_failure_branches_emit_codes_and_correlation_without_exception_text(self):
        from uuid import uuid4
        for name in ['create_admin.py', 'sync_catalogo_ran.py', 'import_catalogo_nucleos_ran.py',
                     'reconcile_gis_migration_lineage.py']:
            source = ast.parse((ROOT / 'backend/scripts' / name).read_text())
            if name == 'create_admin.py':
                outer = next(n for n in source.body if isinstance(n, ast.If))
                guarded = next(n for n in outer.body if isinstance(n, ast.Try))
            else:
                main = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
                guarded = [n for n in main.body if isinstance(n, ast.Try)][-1]
            # Exercise only the real catch bodies, no script imports, DB or operations.
            attempt = ast.Try(body=[ast.Raise(exc=ast.Name(id='injected', ctx=ast.Load()))],
                handlers=guarded.handlers, orelse=[], finalbody=[])
            wrapper = ast.FunctionDef(name='exercise', args=ast.arguments(posonlyargs=[], args=[],
                kwonlyargs=[], kw_defaults=[], defaults=[]), body=[attempt], decorator_list=[])
            ns = dict(injected=SensitiveError(), sys=sys, uuid4=uuid4, connection=None,
                args=SimpleNamespace(report_json=False), BootstrapError=ValueError, CommitUncertain=ValueError)
            exec(compile(ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[])), name, 'exec'), ns)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                try:
                    result = ns['exercise']()
                    self.assertEqual(result, 1)
                except SystemExit as error:
                    self.assertEqual(error.code, 1)
            for sentinel in SENTINELS: self.assertNotIn(sentinel, stdout.getvalue())
            self.assertIn('correlacion=', self.stream.getvalue())
            self.assertNotIn('SS10_SYNTH', self.stream.getvalue())


class StaticConfigurationTests(unittest.TestCase):
    def test_runtime_and_owner_engines_hide_parameters_and_disable_echo(self):
        for name in ['backend/app/database.py', 'backend/scripts/create_admin.py']:
            tree = ast.parse((ROOT / name).read_text())
            calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name) and n.func.id == 'create_engine']
            self.assertEqual(len(calls), 1)
            kwargs = {k.arg: ast.literal_eval(k.value) for k in calls[0].keywords}
            self.assertIs(kwargs['hide_parameters'], True)
            self.assertIs(kwargs['echo'], False)
            self.assertIs(kwargs['echo_pool'], False)

    def test_versioned_commands_keep_ip_policy_and_use_safe_server_config(self):
        for name in ['backend/Dockerfile', 'docker-compose.yml', 'docker-compose.override.yml']:
            text = (ROOT / name).read_text()
            for argument in ['--no-proxy-headers', '--log-config', '/app/logging.json', '--no-access-log']:
                self.assertIn(argument, text)
        config = json.loads((ROOT / 'backend/logging.json').read_text())
        self.assertEqual(config['root']['handlers'], ['safe'])
        for name in ['ssalfer.diagnostics', 'uvicorn.error', 'sqlalchemy', 'psycopg2']:
            self.assertEqual(config['loggers'][name]['handlers'], ['safe'])
            self.assertIs(config['loggers'][name]['propagate'], False)

    def test_only_diagnostics_middleware_is_added_without_changing_csrf(self):
        tree = ast.parse((ROOT / 'backend/app/main.py').read_text())
        last = tree.body[-1]
        self.assertIsInstance(last, ast.Expr)
        self.assertEqual(ast.unparse(last.value.func), 'app.add_middleware')
        self.assertEqual(ast.unparse(last.value.args[0]), 'SafeDiagnosticsMiddleware')
        self.assertNotIn('app.database', sys.modules)

    def test_cli_exception_handlers_do_not_format_caught_exception_values(self):
        for name in ['create_admin.py', 'sync_catalogo_ran.py', 'import_catalogo_nucleos_ran.py',
                     'reconcile_gis_migration_lineage.py']:
            tree = ast.parse((ROOT / 'backend/scripts' / name).read_text())
            for handler in [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler) and n.name]:
                for node in ast.walk(handler):
                    if isinstance(node, ast.JoinedStr):
                        self.assertNotIn(handler.name, {n.id for n in ast.walk(node) if isinstance(n, ast.Name)})
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('str', 'repr'):
                        self.assertNotIn(handler.name, {n.id for n in node.args if isinstance(n, ast.Name)})


HAS_SQLALCHEMY = importlib.util.find_spec('sqlalchemy') is not None


@unittest.skipUnless(HAS_SQLALCHEMY, 'SQLAlchemy not installed; native exception checks pending QA')
class NativeExceptionTests(unittest.TestCase):
    def test_hide_parameters_does_not_remove_orig_or_params(self):
        from sqlalchemy.exc import StatementError, DBAPIError, IntegrityError
        for cls in [StatementError, DBAPIError, IntegrityError]:
            kwargs = dict(statement='INSERT INTO synthetic VALUES (:v)', params={'v': SENTINELS[5]},
                          orig=RuntimeError(SENTINELS[-1]), hide_parameters=True)
            if cls is StatementError: kwargs['message'] = 'synthetic statement failure'
            error = cls(**kwargs)
            self.assertNotIn(SENTINELS[5], str(error))
            self.assertIn(SENTINELS[-1], str(error.orig))
            self.assertEqual(error.params['v'], SENTINELS[5])

    def test_real_sqlalchemy_exception_formatting_is_projected_safely(self):
        from sqlalchemy.exc import StatementError, DBAPIError, IntegrityError
        for cls in [StatementError, DBAPIError, IntegrityError]:
            kwargs = dict(statement='SELECT ' + SENTINELS[5], params={'v': SENTINELS[0]},
                          orig=RuntimeError(SENTINELS[-1]), hide_parameters=True)
            if cls is StatementError: kwargs['message'] = SENTINELS[6]
            error = cls(**kwargs)
            record = logging.LogRecord('sqlalchemy.engine.Engine', logging.ERROR, '', 1,
                SENTINELS[0], (), (type(error), error, None))
            result = safe.SafeJSONFormatter().format(record)
            for sentinel in SENTINELS: self.assertNotIn(sentinel, result)


@unittest.skipUnless(importlib.util.find_spec('psycopg2') is not None,
    'psycopg2 not installed; native PostgreSQL driver exception check pending QA')
class NativeDriverTests(unittest.TestCase):
    def test_driver_exception_object_does_not_reach_formatted_output(self):
        import psycopg2
        error = psycopg2.IntegrityError(' '.join(SENTINELS))
        record = logging.LogRecord('psycopg2', logging.ERROR, '', 1, SENTINELS[0], (),
                                  (type(error), error, None))
        result = safe.SafeJSONFormatter().format(record)
        for sentinel in SENTINELS: self.assertNotIn(sentinel, result)
        self.assertEqual(json.loads(result)['component'], 'database_driver')


if __name__ == '__main__':
    unittest.main()
