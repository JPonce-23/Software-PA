"""Real SQLAlchemy queries on synthetic in-memory SQLite, plus isolated HTTP contracts.

No PostgreSQL connection, production startup, migrations, or existing data are used.
SQLite coverage does not certify PostgreSQL plans, privileges, or native extensions.
"""
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
with patch.dict(os.environ, dict(APP_ENV='test', PYTHON_DOTENV_DISABLED='1',
        DB_HOST='127.0.0.1', DB_PORT='1', DB_NAME='offline_no_database',
        DB_RUNTIME_USER='offline_fixture', DB_RUNTIME_PASSWORD='synthetic-only',
        SECRET_KEY='8f9d7a20b3a652f6c58b3fd27f50df501698fd28ea6cdad295acef489d487ddd')):
    from app import auth, database
    from app.routers import reporting
    from app.services.project_overview import overview_sources
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session


@event.listens_for(database.engine, 'do_connect')
def forbid_postgresql(*args):
    raise AssertionError('Offline regressions must never connect to PostgreSQL')


class SourceQueries(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite+pysqlite:///:memory:')
        self.db = Session(self.engine)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)
        definitions = {
            'proyecto_nucleo': 'id_proyecto_nucleo integer primary key, id_proyecto integer, id_nucleo integer, activo boolean',
            'nucleo_agrario': 'id_nucleo integer primary key, nombre_nucleo text',
            'parcela': 'id_parcela integer primary key, id_nucleo integer, activo boolean',
            'afectacion': 'id_afectacion integer primary key, id_proyecto_nucleo integer, activo boolean',
            'pago': 'id_pago integer primary key, id_indemnizacion integer, activo boolean',
            'indemnizacion': 'id_indemnizacion integer primary key, id_afectacion integer, activo boolean',
            'actividad_campo': 'id_actividad integer primary key, id_proyecto_nucleo integer, activo boolean, tipo_actividad text, fecha_realizada date, fecha_programada date',
            'asamblea': 'id_asamblea integer primary key, id_proyecto_nucleo integer, activo boolean',
            'asamblea_convocatoria': 'id_convocatoria integer primary key, id_asamblea integer, activo boolean, fecha_realizacion date, id_resultado integer',
            'catalogo_operativo': 'id_catalogo_opcion integer primary key, tipo_catalogo text, codigo text, activo boolean',
        }
        for name, fields in definitions.items():
            self.db.execute(text(f'CREATE TABLE {name} ({fields})'))
        for sql in [
            "INSERT INTO nucleo_agrario VALUES(1,'A'),(2,'B'),(3,'Foreign'),(4,'Inactive'),(5,'Empty')",
            'INSERT INTO proyecto_nucleo VALUES(1,10,1,1),(2,10,2,1),(3,20,3,1),(4,10,4,0),(5,10,5,1)',
            'INSERT INTO parcela VALUES(1,1,1),(2,1,0),(3,2,1),(4,3,1),(5,4,1)',
            'INSERT INTO afectacion VALUES(10,1,1),(11,1,0),(20,2,1),(30,3,1),(40,4,1)',
            'INSERT INTO indemnizacion VALUES(1,10,1),(2,10,0),(3,11,1),(4,30,1)',
            'INSERT INTO pago VALUES(1,1,1),(2,1,1),(3,1,0),(4,2,1),(5,3,1),(6,4,1)',
            "INSERT INTO actividad_campo VALUES(1,1,1,'sensibilizacion','2026-01-01',NULL),(2,1,1,'sensibilizacion',NULL,'2026-01-01'),(3,1,1,'sensibilizacion',NULL,NULL),(4,1,0,'sensibilizacion','2026-01-01',NULL),(5,2,1,'caminamiento','2026-01-01',NULL),(6,2,1,'caminamiento',NULL,'2026-01-01'),(7,3,1,'sensibilizacion','2026-01-01',NULL)",
            'INSERT INTO asamblea VALUES(1,1,1),(2,1,1),(3,1,0),(4,3,1)',
            "INSERT INTO catalogo_operativo VALUES(1,'resultado_convocatoria','celebrada',1),(2,'resultado_convocatoria','no_celebrada',1)",
            "INSERT INTO asamblea_convocatoria VALUES(1,1,1,'2026-01-01',1),(2,1,1,'2026-01-02',1),(3,2,1,'2026-01-01',2),(4,2,1,NULL,NULL),(5,3,1,'2026-01-01',1),(6,1,0,'2026-01-01',1),(7,4,1,'2026-01-01',1)",
        ]:
            self.db.execute(text(sql))

    def rows(self, kind, skip=0, limit=200):
        return overview_sources(self.db, 10, kind, skip, limit)

    def test_all_seven_kinds_exclude_other_projects_and_inactive_links(self):
        for kind in ('parcelas', 'afectaciones', 'pagos', 'sensibilizacion', 'caminamiento', 'asambleas', 'convocatorias'):
            with self.subTest(kind=kind):
                self.assertTrue(self.rows(kind))
                self.assertLessEqual({r['id_proyecto_nucleo'] for r in self.rows(kind)}, {1, 2, 5})
        self.assertEqual([(r['id_proyecto_nucleo'], r['total']) for r in self.rows('parcelas')], [(1, 1), (2, 1)])
        self.assertEqual([(r['id_proyecto_nucleo'], r['total']) for r in self.rows('afectaciones')], [(1, 1), (2, 1)])

    def test_payment_counts_keep_nuclei_without_payments_and_filter_inactive_parents(self):
        self.assertEqual([(r['id_proyecto_nucleo'], r['total'], r['realizados'], r['pendientes'])
                          for r in self.rows('pagos')], [(1, 2, 2, 0), (2, 0, 0, 0), (5, 0, 0, 0)])

    def test_activities_distinguish_completed_scheduled_and_without_dates(self):
        self.assertEqual([(r['total'], r['realizados'], r['pendientes'])
                          for r in self.rows('sensibilizacion')], [(3, 1, 1)])
        self.assertEqual([(r['total'], r['realizados'], r['pendientes'])
                          for r in self.rows('caminamiento')], [(2, 1, 1)])

    def test_assemblies_are_deduplicated_and_require_celebrated_result(self):
        self.assertEqual([(r['total'], r['realizados'], r['pendientes'])
                          for r in self.rows('asambleas')], [(2, 1, 1)])
        self.assertEqual([(r['total'], r['realizados'], r['pendientes'])
                          for r in self.rows('convocatorias')], [(4, 3, 1)])

    def test_pagination_beyond_200_is_stable_and_one_query_per_batch(self):
        for i in range(100, 305):
            self.db.execute(text('INSERT INTO nucleo_agrario VALUES(:i,:name)'), {'i': i, 'name': f'QA-{i}'})
            self.db.execute(text('INSERT INTO proyecto_nucleo VALUES(:i,10,:i,1)'), {'i': i})
        statements = []
        def capture(*args): statements.append(1)
        event.listen(self.engine, 'before_cursor_execute', capture)
        try:
            first, second = self.rows('pagos'), self.rows('pagos', 200)
        finally:
            event.remove(self.engine, 'before_cursor_execute', capture)
        self.assertEqual((len(first), len(second), len(statements)), (200, 8, 2))
        self.assertEqual(len({r['id_proyecto_nucleo'] for r in first + second}), 208)


class SourceEndpoint(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(reporting.router, prefix='/api')
        self.db = object()
        app.dependency_overrides[database.get_db] = lambda: self.db
        self.app = app
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.url = '/api/proyectos/10/resumen-ampliado/origenes?tipo=parcelas'

    def role(self, role):
        self.app.dependency_overrides[auth.get_current_user] = lambda: SimpleNamespace(rol=role, id_usuario=987654)

    def test_anonymous_and_geographer_are_rejected_before_query(self):
        with patch.object(reporting, 'require_project_access') as access:
            self.assertEqual(self.client.get(self.url).status_code, 401)
            self.role('geografo')
            self.assertEqual(self.client.get(self.url).status_code, 403)
            access.assert_not_called()

    def test_project_authorization_is_mandatory_before_source_query(self):
        for role in ('admin', 'operador', 'visualizador'):
            self.role(role)
            with patch.object(reporting, 'require_project_access', side_effect=HTTPException(403)) as access, \
                    patch('app.services.project_overview.overview_sources') as query:
                self.assertEqual(self.client.get(self.url).status_code, 403)
                access.assert_called_once_with(self.db, unittest.mock.ANY, 10, load_details=False)
                query.assert_not_called()

    def test_valid_pagination_and_invalid_filters_do_not_change_api_contract(self):
        self.role('visualizador')
        with patch.object(reporting, 'require_project_access'), \
                patch('app.services.project_overview.overview_sources', return_value=[]) as query:
            self.assertEqual(self.client.get(self.url + '&skip=200&limit=200').status_code, 200)
            query.assert_called_once_with(self.db, 10, 'parcelas', 200, 200)
            query.reset_mock()
            for params in ('tipo=unknown', 'tipo=pagos&limit=201', 'tipo=pagos&limit=0', 'tipo=pagos&skip=-1'):
                with self.subTest(params=params):
                    self.assertEqual(self.client.get(self.url.split('?')[0] + '?' + params).status_code, 422)
            query.assert_not_called()


if __name__ == '__main__':
    unittest.main()
