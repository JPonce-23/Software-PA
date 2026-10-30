"""SS-11: stdlib, synthetic rows/cursors/ASGI. No app startup or DB imports."""

import ast
import asyncio
import csv
from dataclasses import replace
from decimal import Decimal
import io
import itertools
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.services import report_limits as limits


def row(i=1, **kwargs):
    values = dict(id_proyecto=1, id_entidad=1, ambito='colectivo', tipo_cop_operativo=None,
        tipo_convenio=None, destino_superficie=None, anio=2026, mes=1, trimestre=1,
        indicador=f'indicador_{i:03}', programado=i, realizado=i, cantidad=i,
        superficie_ha=Decimal('1.123456789'), monto=Decimal('100.25'), activo=True,
        condicion_especial='expropiacion_directa')
    return SimpleNamespace(**(values | kwargs))


class Cursor:
    def __init__(self, rows):
        self.rows = iter(rows); self.closed = False; self.fetch_sizes = []; self.observed = 0
    def fetchmany(self, size):
        assert size > 0
        self.fetch_sizes.append(size)
        result = list(itertools.islice(self.rows, size)); self.observed += len(result)
        return result
    def close(self): self.closed = True


class Field:
    def __init__(self, name): self.name = name
    def __eq__(self, value):
        if isinstance(value, Field): return True
        return lambda row: getattr(row, self.name) == value
    def in_(self, values): return lambda row: getattr(row, self.name) in values
    def is_(self, value): return lambda row: getattr(row, self.name, True) is value
    def label(self, name): return Field(name)
    def nulls_last(self): return self


class Query:
    def __init__(self, rows): self.rows = list(rows); self.bound = None; self.order = (); self.selected = ()
    def filter(self, *predicates):
        for predicate in predicates:
            if callable(predicate): self.rows = list(filter(predicate, self.rows))
        return self
    def with_entities(self, *fields): self.selected = tuple(f.name for f in fields); return self
    def order_by(self, *fields):
        self.order = tuple(f.name for f in fields)
        self.rows.sort(key=lambda row: tuple((getattr(row, f.name) is None, getattr(row, f.name)) for f in fields))
        return self
    def limit(self, count): self.bound = count; return self
    def join(self, *args): return self
    def group_by(self, *args): return self
    @property
    def statement(self): return self


class DB:
    def __init__(self, data, current=()):
        self.data, self.current, self.calls, self.queries = data, current, [], []
        self.closed = False
    def query(self, *fields):
        q = Query(self.data if len(fields) == 1 else self.current)
        self.queries.append(q); return q
    def execute(self, statement, **kwargs):
        assert not self.closed
        result = Cursor(itertools.islice(statement.rows, statement.bound))
        self.calls.append((statement, kwargs, result)); return result
    def close(self): self.closed = True


class HTTPError(Exception):
    def __init__(self, status_code, detail): self.status_code, self.detail = status_code, detail


class StreamingDouble:
    def __init__(self, iterator, *, media_type, headers):
        self.body_iterator, self.media_type, self.headers = iterator, media_type, headers
    async def __call__(self, scope, receive, send):
        await send({'type': 'http.response.start', 'status': 200})
        for chunk in self.body_iterator:
            await send({'type': 'http.response.body', 'body': chunk, 'more_body': True})
        await send({'type': 'http.response.body', 'body': b''})


def router_functions():
    tree = ast.parse((ROOT / 'backend/app/routers/reporting.py').read_text())
    names = {'_dashboard_query', '_complete_report_rows', 'reporte_avance_periodo',
        'reporte_resumen_actual', 'export_dashboard', 'DashboardCsvResponse'}
    definitions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    assert {n.name for n in definitions} == names
    for n in definitions: n.decorator_list = []
    models = SimpleNamespace()
    fields = set(limits.ADVANCE_COLUMNS + limits.SNAPSHOT_COLUMNS + limits.CSV_COLUMNS) | {
        'activo', 'condicion_especial', 'id_nucleo', 'id_municipio', 'id_proyecto_nucleo'}
    for model in ['DashboardKpi', 'ReporteAvancePeriodo', 'ReporteSnapshotActual',
                  'ProyectoNucleo', 'NucleoAgrario', 'Municipio', 'Afectacion']:
        setattr(models, model, SimpleNamespace(**{name: Field(name) for name in fields}))
    def require(db, user, project):
        if project not in user.projects: raise HTTPError(403, 'Proyecto fuera de alcance')
    func = SimpleNamespace(count=lambda *args: Field('cantidad'), distinct=lambda f: f)
    ns = dict(report_limits=limits, models=models, func=func, literal=lambda v: Field('literal'),
        time=__import__('time'), Query=lambda *args, **kwargs: kwargs.get('default', args[0] if args else None),
        Depends=lambda *args: None, get_db=None, auth=SimpleNamespace(RoleChecker=lambda roles: None),
        READ_ROLES=['admin', 'operador', 'visualizador', 'geografo'],
        require_project_access=require, authorized_project_ids=lambda db, user: user.projects,
        HTTPException=HTTPError, StreamingResponse=StreamingDouble)
    future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, *definitions], type_ignores=[])),
        'isolated_reporting', 'exec'), ns)
    return ns


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True); self.env.start(); self.addCleanup(self.env.stop)
        self.limits = limits.load_limits()

    def test_defaults_and_positive_configuration_bounds(self):
        self.assertEqual((self.limits.rows, self.limits.csv_bytes, self.limits.batch_rows,
            self.limits.build_seconds), (10000, 16777216, 250, None))
        for key in ['REPORT_MAX_ROWS', 'REPORT_EXPORT_MAX_BYTES', 'REPORT_FETCH_BATCH_ROWS']:
            for value in ['0', '-1', 'invalid']:
                with self.subTest(key=key, value=value), patch.dict(os.environ, {key: value}):
                    with self.assertRaises(RuntimeError): limits.load_limits()
        for value in ['0', '-1', 'inf', 'nan', 'invalid']:
            with patch.dict(os.environ, {'REPORT_EXPORT_BUILD_TIMEOUT_SECONDS': value}):
                with self.assertRaises(RuntimeError): limits.load_limits()
        with patch.dict(os.environ, {'REPORT_FETCH_BATCH_ROWS': '1001'}):
            with self.assertRaises(RuntimeError): limits.load_limits()
        with patch.dict(os.environ, {'REPORT_EXPORT_BUILD_TIMEOUT_SECONDS': '2.5'}):
            self.assertEqual(limits.load_limits().build_seconds, 2.5)

    def test_complete_read_boundaries_never_return_silent_partial_result(self):
        budget = replace(self.limits, rows=3, batch_rows=2)
        for count in [0, 1, 3, 4]:
            db, query = DB([]), Query(row(i) for i in range(count))
            if count <= 3:
                self.assertEqual(len(limits.read_complete_rows(db, query, budget)), count)
            else:
                with self.assertRaises(limits.ReportLimitError): limits.read_complete_rows(db, query, budget)
            statement, options, cursor = db.calls[0]
            self.assertEqual(statement.bound, 4)
            self.assertEqual(options['execution_options']['yield_per'], 2)
            self.assertTrue(cursor.closed)
            self.assertLessEqual(cursor.observed, 4)

    def test_two_snapshot_segments_share_one_row_budget(self):
        budget = replace(self.limits, rows=3)
        db = DB([])
        self.assertEqual(len(limits.read_complete_rows(db, Query([row()]), budget, already_read=2)), 1)
        with self.assertRaises(limits.ReportLimitError):
            limits.read_complete_rows(db, Query([row(), row(2)]), budget, already_read=2)
        self.assertTrue(all(cursor.closed for _, _, cursor in db.calls))

    def test_cursor_error_and_cancellation_are_closed(self):
        for error in [RuntimeError('synthetic'), asyncio.CancelledError()]:
            cursor = Cursor([]); cursor.fetchmany = MagicMock(side_effect=error)
            db = SimpleNamespace(execute=lambda *a, **kw: cursor)
            with self.assertRaises(type(error)):
                limits.read_complete_rows(db, Query([]), self.limits)
            self.assertTrue(cursor.closed)

    def test_batch_boundaries_no_row_loss_or_duplication(self):
        rows = [row(i) for i in range(17)]
        for batch in [1, 2, 7, 17, 250]:
            cursor = Cursor(rows)
            self.assertEqual(list(limits.iter_result_rows(cursor, replace(self.limits, batch_rows=batch))), rows)
            self.assertTrue(all(size <= batch for size in cursor.fetch_sizes))

    def test_csv_header_order_utf8_and_decimal_totals_are_preserved(self):
        rows = [row(1, indicador='José ñ <inert>, "texto"'), row(2, monto=Decimal('-0.25'))]
        cursor = Cursor(rows)
        with limits.build_csv(cursor, self.limits) as output:
            parsed = list(csv.reader(io.StringIO(output.read().decode('utf-8'))))
        self.assertEqual(parsed[0], list(limits.CSV_COLUMNS))
        self.assertEqual(parsed[1][2], rows[0].indicador)
        self.assertEqual(sum(Decimal(r[7]) for r in parsed[1:]), Decimal('100.00'))
        self.assertEqual(sum(Decimal(r[6]) for r in parsed[1:]), Decimal('2.246913578'))
        self.assertFalse(cursor.closed)  # Explicitly the route's responsibility.

    def test_empty_csv_is_a_complete_header_only_export(self):
        with limits.build_csv(Cursor([]), self.limits) as output:
            parsed = list(csv.reader(io.StringIO(output.read().decode('utf-8'))))
        self.assertEqual(parsed, [list(limits.CSV_COLUMNS)])

    def test_formula_mitigation_is_export_only_and_does_not_change_numeric_negatives(self):
        for value in ['=1+1', '+cmd', '-cmd', '@SUM(A1)', '  =1', '\ufeff=1', '\ttext', '\rtext', '\ntext',
                      '＝1+1', '＋cmd', '－cmd', '＠SUM(A1)']:
            self.assertEqual(limits.csv_cell(value), "'" + value)
        for value in ['normal', 'áéí & <texto>', '', None, -5, Decimal('-1.2500')]:
            self.assertEqual(limits.csv_cell(value), value)
        source = row(indicador='=synthetic')
        with limits.build_csv(Cursor([source]), self.limits) as output:
            parsed = list(csv.reader(io.StringIO(output.read().decode())))
        self.assertEqual(parsed[1][2], "'=synthetic")
        self.assertEqual(source.indicador, '=synthetic')

    def test_csv_bytes_count_utf8_header_quotes_and_crlf(self):
        source = [row(indicador='ñ,"a"')]
        with limits.build_csv(Cursor(source), self.limits) as output: expected = output.read()
        with limits.build_csv(Cursor(source), replace(self.limits, csv_bytes=len(expected))) as output:
            self.assertEqual(output.read(), expected)
        with self.assertRaises(limits.ReportLimitError) as error:
            limits.build_csv(Cursor(source), replace(self.limits, csv_bytes=len(expected) - 1))
        self.assertEqual(error.exception.code, 'REPORT_CSV_BYTE_LIMIT')

    def test_files_close_on_rows_bytes_deadline_io_and_cancellation_errors(self):
        for kind in ['rows', 'bytes', 'deadline', 'io', 'cancel']:
            output = io.BytesIO()
            cursor = Cursor([row(), row(2)])
            budget = replace(self.limits, rows=1) if kind == 'rows' else self.limits
            if kind == 'bytes': budget = replace(budget, csv_bytes=1)
            if kind in ['io', 'cancel']:
                cursor.fetchmany = MagicMock(side_effect=OSError('synthetic') if kind == 'io' else asyncio.CancelledError())
            with self.subTest(kind=kind), self.assertRaises(BaseException):
                limits.build_csv(cursor, budget, deadline=1 if kind == 'deadline' else None,
                    clock=lambda: 1, file_factory=lambda **kwargs: output)
            self.assertTrue(output.closed)

    def test_oversized_string_rejected_before_formula_copy_and_csv_serialization(self):
        output = io.BytesIO()
        with patch.object(limits, 'csv_cell', side_effect=AssertionError('should not copy large cell')):
            with self.assertRaises(limits.ReportLimitError):
                limits.build_csv(Cursor([row(indicador='=' * 501)]),
                    replace(self.limits, csv_bytes=500), file_factory=lambda **kwargs: output)
        self.assertTrue(output.closed)

    def test_deadline_checks_before_and_after_fetch(self):
        cursor = Cursor([row()])
        ticks = iter([0, 2])
        with self.assertRaises(limits.ReportLimitError) as caught:
            list(limits.iter_result_rows(cursor, self.limits, deadline=1, clock=lambda: next(ticks)))
        self.assertEqual(caught.exception.status, 504)
        self.assertEqual(cursor.observed, 1)

    def test_private_temporary_file_and_fixed_download_chunks(self):
        rows = [row(i, indicador='x' * 1000) for i in range(200)]
        output = limits.build_csv(Cursor(rows), self.limits)
        self.assertEqual(os.fstat(output.fileno()).st_mode & 0o777, 0o600)
        chunks = list(limits.file_chunks(output))
        self.assertGreater(len(chunks), 1)
        self.assertLessEqual(max(map(len, chunks)), limits.CSV_CHUNK_BYTES)
        self.assertTrue(output.closed)


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True); self.env.start(); self.addCleanup(self.env.stop)
        self.ns = router_functions(); self.user = SimpleNamespace(projects=[1])

    def test_advance_all_filters_and_access_are_preserved(self):
        target = row(tipo_cop_operativo='ORIGEN', tipo_convenio='principal', destino_superficie='tuc')
        others = [row(id_proyecto=2), row(id_entidad=2), row(anio=2025), row(mes=2), row(trimestre=2),
                  row(indicador='other'), row(ambito='individual'), row(tipo_cop_operativo='ADICIONAL'),
                  row(tipo_convenio='otro'), row(destino_superficie='otro')]
        db = DB([target, *others])
        result = self.ns['reporte_avance_periodo'](id_proyecto=1, id_entidad=1, anio=2026, mes=1,
            trimestre=1, indicador=target.indicador, ambito=target.ambito, tipo_cop_operativo='ORIGEN',
            tipo_convenio='principal', destino_superficie='tuc', db=db, user=self.user)
        self.assertEqual(result, [target])
        self.assertEqual(db.queries[0].selected, limits.ADVANCE_COLUMNS)
        with self.assertRaises(HTTPError) as caught:
            self.ns['reporte_avance_periodo'](id_proyecto=2, db=DB([]), user=self.user)
        self.assertEqual(caught.exception.status_code, 403)

    def test_implicit_project_scope_and_complete_array_no_pagination(self):
        db = DB([row(), row(id_proyecto=2)])
        result = self.ns['reporte_avance_periodo'](db=db, user=self.user)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result, list)
        with patch.dict(os.environ, {'REPORT_MAX_ROWS': '1'}):
            with self.assertRaises(HTTPError) as caught:
                self.ns['reporte_avance_periodo'](db=DB([row(), row(2)]), user=self.user)
        self.assertEqual(caught.exception.status_code, 413)

    def test_all_tie_dimensions_have_stable_order_with_nulls(self):
        rows = [row(id_entidad=2), row(tipo_cop_operativo='ORIGEN'), row(ambito='individual'), row()]
        first = self.ns['reporte_avance_periodo'](db=DB(rows), user=self.user)
        second = self.ns['reporte_avance_periodo'](db=DB(reversed(rows)), user=self.user)
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(rows))
        self.assertEqual(sum(r.monto for r in first), Decimal('401.00'))

    def test_snapshot_filters_special_overlay_and_shared_limit(self):
        base = row(indicador='total_nucleos')
        current = row(indicador='expropiacion_directa_actual', cantidad=3, superficie_ha=None, monto=None)
        result = self.ns['reporte_resumen_actual'](db=DB([base, row(id_proyecto=2)], [current]), user=self.user)
        self.assertEqual({r.indicador for r in result}, {'total_nucleos', 'expropiacion_directa_actual'})
        self.assertEqual(next(r.cantidad for r in result if r.indicador == current.indicador), 3)
        with patch.dict(os.environ, {'REPORT_MAX_ROWS': '1'}):
            db = DB([base], [current])
            with self.assertRaises(HTTPError) as caught:
                self.ns['reporte_resumen_actual'](db=db, user=self.user)
            self.assertEqual(caught.exception.status_code, 413)
            self.assertTrue(all(cursor.closed for _, _, cursor in db.calls))
        db = DB([base], [current])
        self.ns['reporte_resumen_actual'](indicador='total_nucleos', db=db, user=self.user)
        self.assertEqual(len(db.calls), 1)

    def test_csv_single_select_filters_sorted_and_db_closed_before_response(self):
        db = DB([row(2), row(1), row(id_proyecto=2), row(anio=2025)])
        response = self.ns['export_dashboard'](id_proyecto=1, anio=2026, db=db, user=self.user)
        self.assertTrue(db.closed)
        self.assertEqual(len(db.calls), 1)
        query, options, cursor = db.calls[0]
        self.assertTrue(cursor.closed)
        self.assertEqual(query.order, ('id_proyecto', 'anio', 'indicador'))
        self.assertEqual(query.selected, limits.CSV_COLUMNS)
        self.assertEqual(query.bound, 10001)
        parsed = list(csv.reader(io.StringIO(response.output.read().decode())))
        self.assertEqual([r[2] for r in parsed[1:]], ['indicador_001', 'indicador_002'])
        self.assertEqual(response.headers['Content-Disposition'], 'attachment; filename=dashboard.csv')
        response.output.close()

    def test_csv_denial_and_limit_failure_close_db_without_response(self):
        for project, data in [(2, []), (1, [row(), row(2)])]:
            db = DB(data)
            with patch.dict(os.environ, {'REPORT_MAX_ROWS': '1'}), self.assertRaises(HTTPError):
                self.ns['export_dashboard'](id_proyecto=project, db=db, user=self.user)
            self.assertTrue(db.closed)
            self.assertTrue(all(cursor.closed for _, _, cursor in db.calls))

    def test_csv_execute_failure_and_response_constructor_failure_release_resources(self):
        db = DB([]); db.execute = MagicMock(side_effect=RuntimeError('synthetic'))
        with self.assertRaises(RuntimeError): self.ns['export_dashboard'](db=db, user=self.user)
        self.assertTrue(db.closed)
        output = io.BytesIO()
        self.ns['DashboardCsvResponse'] = MagicMock(side_effect=RuntimeError('synthetic response'))
        with patch.object(limits, 'build_csv', return_value=output), self.assertRaises(RuntimeError):
            self.ns['export_dashboard'](db=DB([]), user=self.user)
        self.assertTrue(output.closed)

    def test_csv_fetch_cancel_cursor_close_or_db_close_error_cleans_owned_file(self):
        for kind in ['cancel', 'cursor_close', 'db_close']:
            db = DB([]); cursor = Cursor([]); output = io.BytesIO()
            db.execute = MagicMock(return_value=cursor)
            if kind == 'cancel': cursor.fetchmany = MagicMock(side_effect=asyncio.CancelledError())
            if kind == 'cursor_close': cursor.close = MagicMock(side_effect=RuntimeError('synthetic close'))
            if kind == 'db_close': db.close = MagicMock(side_effect=RuntimeError('synthetic db close'))
            build = limits.build_csv if kind == 'cancel' else lambda *args, **kwargs: output
            with patch.object(limits, 'build_csv', side_effect=build):
                with self.assertRaises(BaseException): self.ns['export_dashboard'](db=db, user=self.user)
            if kind != 'cancel': self.assertTrue(output.closed)
            if kind != 'db_close': self.assertTrue(db.closed)

    def test_response_cancellation_before_iteration_and_midstream_closes_file(self):
        response_type = self.ns['DashboardCsvResponse']
        for cancel_on in [1, 2]:
            output = io.BytesIO(b'x' * (limits.CSV_CHUNK_BYTES + 1))
            response = response_type(output); calls = []
            async def send(message):
                calls.append(message)
                if len(calls) == cancel_on: raise asyncio.CancelledError()
            with self.assertRaises(asyncio.CancelledError):
                asyncio.run(response({}, MagicMock(), send))
            self.assertTrue(output.closed)

    def test_public_models_still_arrays_and_roles_unchanged(self):
        tree = ast.parse((ROOT / 'backend/app/routers/reporting.py').read_text())
        for name in ['reporte_avance_periodo', 'reporte_resumen_actual']:
            fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
            response_model = next(k.value for k in fn.decorator_list[0].keywords if k.arg == 'response_model')
            self.assertTrue(ast.unparse(response_model).startswith('list[schemas.'))
        self.assertNotIn('app.database', sys.modules)
        self.assertNotIn('app.main', sys.modules)


if __name__ == '__main__': unittest.main()
