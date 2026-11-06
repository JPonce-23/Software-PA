"""Opt-in read regressions for the marked PR6 disposable deployment lab only.

Temporary shadow view and rolled-back data; no migrations or persistent writes.
"""
import os
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.getenv("PR6_PERFORMANCE_QA_ENABLE") == "1", "Requires explicit PR6 synthetic QA")
class ReadProjections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sqlalchemy import create_engine, text
        from sqlalchemy.engine import URL
        if os.getenv("PR6_DEPLOY_QA") != "SYNTHETIC_DISPOSABLE_ONLY":
            raise RuntimeError("Synthetic PR6 authorization required")
        cls.engine = create_engine(URL.create("postgresql", host="db", database="software_pa_test",
            username=os.environ["POSTGRES_ADMIN_USER"], password=os.environ["POSTGRES_ADMIN_PASSWORD"]),
            hide_parameters=True, pool_size=1, max_overflow=0)
        with cls.engine.connect() as db:
            actual = db.execute(text("SELECT current_database(), current_setting('cluster_name')")).one()
            if tuple(actual) != ("software_pa_test", "pr6-deployment-disposable"):
                raise RuntimeError("Wrong QA database contract")

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def test_dated_facts_match_original_union_distinct_nulls_years_and_scope(self):
        from sqlalchemy import text
        from sqlalchemy.orm import Session
        from app.services import dashboard_csv
        with self.engine.connect() as connection:
            tx = connection.begin()
            try:
                connection.execute(text("""CREATE TEMP VIEW vw_hito_seguimiento AS
                    SELECT * FROM (VALUES
                      (1,'a','h1',DATE '2025-12-31',DATE '2026-01-01',1.25::numeric,10::numeric),
                      (1,'a','h2',DATE '2026-01-01',DATE '2026-01-02',NULL::numeric,NULL::numeric),
                      (1,'a','h2',DATE '2026-01-01',DATE '2026-01-02',NULL::numeric,NULL::numeric),
                      (1,'b','h3',NULL::date,DATE '2026-03-01',2.5::numeric,-2::numeric),
                      (1,'c','h4',DATE '2026-03-01',NULL::date,9::numeric,999::numeric),
                      (1,'d','h5',NULL::date,NULL::date,9::numeric,999::numeric),
                      (2,'a','h6',DATE '2026-01-01',DATE '2026-01-02',3::numeric,15::numeric)
                    ) x(id_proyecto,indicador,clave_hito,fecha_programada,fecha_realizada,superficie_ha,monto)"""))
                reference = """WITH f AS (
                    SELECT id_proyecto,extract(year FROM fecha_programada)::integer anio,indicador,clave_hito,
                    1::bigint programado,0::bigint realizado,NULL::numeric superficie_ha,NULL::numeric monto
                    FROM vw_hito_seguimiento WHERE fecha_programada IS NOT NULL
                    UNION ALL
                    SELECT id_proyecto,extract(year FROM fecha_realizada)::integer,indicador,clave_hito,
                    0::bigint,1::bigint,superficie_ha,monto FROM vw_hito_seguimiento WHERE fecha_realizada IS NOT NULL)
                    SELECT id_proyecto,anio,indicador,sum(programado)::bigint,sum(realizado)::bigint,
                    count(DISTINCT clave_hito)::bigint,sum(superficie_ha)::numeric,sum(monto)::numeric
                    FROM f WHERE id_proyecto=ANY(:ids) AND (:year IS NULL OR anio=:year)
                    GROUP BY id_proyecto,anio,indicador ORDER BY id_proyecto,anio,indicador"""
                with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
                    for ids in ([], [1], [2], [1,2], [999]):
                        for year in (None, 2025, 2026, 2027):
                            with self.subTest(ids=ids, year=year):
                                expected = db.execute(text(reference), {"ids":ids,"year":year}).all()
                                self.assertEqual(dashboard_csv.query(db, ids, year).all(), expected)
            finally:
                tx.rollback()

    def test_real_kpi_view_and_csv_projection_match(self):
        from sqlalchemy import select
        from sqlalchemy.orm import Session
        from app import models
        from app.services import dashboard_csv
        with Session(self.engine) as db:
            scope = select(models.Proyecto.id_proyecto).where(models.Proyecto.activo.is_(True))
            columns = [getattr(models.DashboardKpi,n) for n in
                ('id_proyecto','anio','indicador','programado','realizado','cantidad','superficie_ha','monto')]
            expected = db.query(*columns).filter(models.DashboardKpi.id_proyecto.in_(scope)).order_by(
                models.DashboardKpi.id_proyecto,models.DashboardKpi.anio,models.DashboardKpi.indicador).all()
            self.assertEqual(dashboard_csv.query(db, scope).all(), expected)

    def test_map_keeps_geojson_and_removes_authorization_relationship_loads(self):
        from sqlalchemy import event, text
        from sqlalchemy.orm import Session
        from app import models
        from app.routers import reporting
        from app.services.access import require_project_access
        counts=[];outputs=[]
        with self.engine.connect() as db:
            project=db.execute(text("SELECT (value->>'project')::int FROM pr6_perf_fixture")).scalar_one()
        for details in (True, False):
            queries=[]
            def observed(*args): queries.append(1)
            event.listen(self.engine, 'before_cursor_execute', observed)
            try:
                with Session(self.engine) as db:
                    user=db.query(models.Usuario).filter_by(id_usuario=1).one();queries.clear()
                    with patch.object(reporting, 'require_project_access',
                            side_effect=lambda db,user,p,**kw: require_project_access(db,user,p,load_details=details)):
                        outputs.append(reporting.project_map(project,db,user))
                    counts.append(len(queries))
            finally:
                event.remove(self.engine, 'before_cursor_execute', observed)
        self.assertEqual(outputs[0],outputs[1])
        self.assertEqual(counts[1],5)
        self.assertGreater(counts[0],counts[1])

    def test_complete_app_inspection_failure_keeps_key_and_security_headers(self):
        import uuid
        import io
        from sqlalchemy import text
        from fastapi.testclient import TestClient
        from pypdf import PdfWriter
        from app.main import app
        from app.services import documents
        from app.services.document_validation import DocumentValidationError
        with self.engine.begin() as db:
            db.execute(text("SELECT set_config('app.current_user_id','1',true)"))
            pn=db.execute(text("SELECT id_proyecto_nucleo FROM proyecto_nucleo WHERE activo ORDER BY id_proyecto_nucleo LIMIT 1")).scalar_one()
            doc=db.execute(text("INSERT INTO documento(tipo_documento,estado,titulo,creado_por) VALUES('pr6_qa','disponible','PERF_SYNTHETIC_HTTP_REGRESSION',1) RETURNING id_documento")).scalar_one()
            db.execute(text("INSERT INTO documento_vinculo(id_documento,entidad_tipo,entidad_id,creado_por) VALUES(:d,'proyecto_nucleo',:pn,1)"),{'d':doc,'pn':pn})
        writer=PdfWriter();writer.add_blank_page(width=72,height=72);out=io.BytesIO();writer.write(out);content=out.getvalue()
        key=str(uuid.uuid4());base='https://ssalfer.qa.invalid'
        with TestClient(app, base_url=base, raise_server_exceptions=False) as client:
            login=client.post('/api/auth/sesiones',headers={'Origin':base},data={'username':os.environ['QA_USERNAME'],'password':os.environ['QA_PASSWORD']})
            self.assertEqual(login.status_code,200)
            headers={'Origin':base,'X-CSRF-Token':client.cookies['__Host-pa_csrf'],'Idempotency-Key':key}
            gate = documents._UPLOAD_MEMORY_SLOTS
            gate.acquire(); gate.acquire()
            try:
                with patch.object(documents, 'validate_document', side_effect=AssertionError('must not inspect')):
                    refused=client.post(f'/api/documentos/{doc}/versiones',headers=headers,files={'archivo':('synthetic.pdf',content,'application/pdf')})
                self.assertEqual(refused.status_code,503)
                self.assertEqual(refused.headers['X-Document-Error-Code'],'DOCUMENT_INSPECTION_BUSY')
                with self.engine.connect() as db:
                    self.assertEqual(db.execute(text('SELECT count(*) FROM documento_operacion WHERE id_documento=:d'),{'d':doc}).scalar_one(),0)
            finally:
                gate.release(); gate.release()
            for code,status in [('DOCUMENT_INSPECTION_TIMEOUT',503),('DOCUMENT_INSPECTION_BUSY',503),('DOCUMENT_FORMAT_INVALID',422),('DOCUMENT_PROCESS_LIMIT',422)]:
                with patch.object(documents,'validate_document',side_effect=DocumentValidationError(code,status=status)):
                    r=client.post(f'/api/documentos/{doc}/versiones',headers=headers,files={'archivo':('synthetic.pdf',content,'application/pdf')})
                self.assertEqual(r.status_code,status)
                self.assertEqual(r.headers['X-Document-Error-Code'],code)
                self.assertEqual(r.headers['X-Content-Type-Options'],'nosniff')
                self.assertIn('no-store',r.headers['Cache-Control'])
                with self.engine.connect() as db:
                    self.assertEqual(db.execute(text('SELECT count(*) FROM documento_operacion WHERE id_documento=:d'),{'d':doc}).scalar_one(),0)
            for status in (201,200):
                r=client.post(f'/api/documentos/{doc}/versiones',headers=headers,files={'archivo':('synthetic.pdf',content,'application/pdf')})
                self.assertEqual(r.status_code,status)
            with self.engine.connect() as db:
                self.assertEqual(db.execute(text('SELECT count(*) FROM documento_version WHERE id_documento=:d'),{'d':doc}).scalar_one(),1)


if __name__ == '__main__':
    unittest.main()
