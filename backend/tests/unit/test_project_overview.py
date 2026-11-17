"""Synthetic temporary tables; never modify administrative records."""
import os
import unittest
from decimal import Decimal
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text, event
from app import auth
from app.database import SessionLocal
from app.routers.reporting import router
from app.services.project_overview import project_overview


class OverviewTests(unittest.TestCase):
    def setUp(self):
        if os.getenv("DB_NAME") != "db_integracion_mq_local_revision_20261112":
            raise RuntimeError("Use the isolated QA database")
        self.db = SessionLocal()
        for table in ("proyecto_nucleo", "parcela", "afectacion", "actividad_campo", "asamblea",
                      "asamblea_convocatoria", "catalogo_operativo", "convenio", "convenio_afectacion",
                      "tramite_fifonafe_afectacion", "tramite_fifonafe", "pago", "indemnizacion",
                      "afectacion_unidad_agraria", "unidad_agraria"):
            self.db.execute(text(f"CREATE TEMP TABLE {table} ON COMMIT DROP AS SELECT * FROM public.{table} WITH NO DATA"))

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def sql(self, query):
        self.db.execute(text(query))

    def seed(self):
        self.sql("INSERT INTO proyecto_nucleo(id_proyecto_nucleo,id_proyecto,id_nucleo,activo) VALUES(1,1,1,true),(2,2,2,true),(3,1,3,false)")
        self.sql("INSERT INTO afectacion(id_afectacion,id_proyecto_nucleo,activo,superficie_afectada_ha) VALUES(1,1,true,2),(2,1,true,NULL),(3,2,true,100)")
        self.sql("INSERT INTO convenio(id_convenio,id_proyecto_nucleo,ambito,tipo_instrumento,activo,monto_90,monto_100) VALUES(1,1,'colectivo','convenio',true,90,100),(2,1,'colectivo','convenio',true,NULL,NULL),(3,1,'individual','convenio',true,0,0),(4,2,'colectivo','convenio',true,900,1000),(5,1,'colectivo','otro',true,900,1000)")
        self.sql("INSERT INTO convenio_afectacion(id_convenio,id_afectacion,activo) VALUES(1,1,true),(1,2,true),(2,2,true)")
        self.sql("INSERT INTO tramite_fifonafe(id_tramite_fifonafe,id_proyecto_nucleo,estatus,hay_conflictos,activo) VALUES(1,1,'completo',true,true),(2,1,'pendiente',NULL,true)")
        self.sql("INSERT INTO tramite_fifonafe_afectacion(id_tramite_fifonafe,id_afectacion,activo) VALUES(1,1,true),(1,2,true)")

    def test_empty_project_unknown_is_not_zero(self):
        d = project_overview(self.db, 1)
        self.assertEqual(d['nucleos'], 0)
        self.assertIsNone(d['colectivo_monto_100'])
        self.assertIsNone(d['asambleas_realizadas'])
        self.assertEqual(d['sin_superficie'], 0)

    def test_complete_conflict_independent_and_deduplicated(self):
        self.seed()
        d = project_overview(self.db, 1)
        self.assertEqual((d['colectivo_total'], d['colectivo_completos'], d['colectivo_conflicto']), (2,2,2))
        self.assertEqual(d['colectivo_monto_100'], Decimal('100'))
        self.assertEqual(d['individual_sin_tramite'],1)
        self.assertEqual(d['individual_completos'],0)
        self.assertEqual(d['individual_monto_100'],0)
        self.sql("INSERT INTO tramite_fifonafe_afectacion(id_tramite_fifonafe,id_afectacion,activo) VALUES(2,1,true)")
        self.assertEqual(project_overview(self.db, 1)['colectivo_completos'],1)

    def test_counts_no_100_nucleus_limit_one_statement(self):
        self.sql("INSERT INTO proyecto_nucleo(id_proyecto_nucleo,id_proyecto,id_nucleo,activo) SELECT i,1,i,true FROM generate_series(1,1000) i")
        calls=[]
        connection=self.db.connection()
        def count(*args): calls.append(1)
        event.listen(connection,'before_cursor_execute',count)
        try:
            self.assertEqual(project_overview(self.db,1)['nucleos'],1000)
            self.assertEqual(len(calls),1)
        finally:
            event.remove(connection,'before_cursor_execute',count)

    def test_surface_precedence_payments_not_multiplied(self):
        self.seed()
        self.sql("INSERT INTO unidad_agraria(id_unidad_agraria,activo) VALUES(1,true),(2,true)")
        self.sql("INSERT INTO afectacion_unidad_agraria(id_afectacion_unidad,id_afectacion,id_unidad_agraria,superficie_afectada_ha,activo) VALUES(1,1,1,99,true),(2,2,2,3,true)")
        self.sql("INSERT INTO indemnizacion(id_indemnizacion,id_afectacion,activo) VALUES(1,2,true)")
        self.sql("INSERT INTO pago(id_pago,id_indemnizacion,monto,activo) VALUES(1,1,50,true)")
        d=project_overview(self.db,1)
        self.assertEqual(d['superficie_ha'],5)
        self.assertEqual(d['sin_superficie'],0)
        self.assertEqual(d['pagos_registros'],1)
        self.assertEqual(d['pagos_total'],50)

    def test_assemblies_deduplicated_activities_completed_by_date(self):
        self.seed()
        self.sql("INSERT INTO catalogo_operativo(id_catalogo_opcion,tipo_catalogo,codigo,activo) VALUES(1,'resultado_convocatoria','celebrada',true)")
        self.sql("INSERT INTO asamblea(id_asamblea,id_proyecto_nucleo,activo) VALUES(1,1,true)")
        self.sql("INSERT INTO asamblea_convocatoria(id_asamblea,fecha_realizacion,id_resultado,activo) VALUES(1,'2026-01-01',1,true),(1,'2026-01-02',1,true),(1,NULL,NULL,true)")
        self.sql("INSERT INTO actividad_campo(id_proyecto_nucleo,tipo_actividad,fecha_realizada,activo) VALUES(1,'caminamiento','2026-01-01',true),(1,'caminamiento',NULL,true),(2,'caminamiento','2026-01-01',true)")
        d=project_overview(self.db,1)
        self.assertEqual((d['asambleas_total'],d['asambleas_realizadas']), (1,1))
        self.assertEqual((d['convocatorias_total'],d['convocatorias_realizadas']), (3,2))
        self.assertEqual((d['caminamiento_total'],d['caminamiento_realizadas']), (2,1))


class OverviewPermissions(unittest.TestCase):
    def test_auth_roles_and_project_scope(self):
        app=FastAPI(); app.include_router(router,prefix='/api')
        client=TestClient(app)
        url='/api/proyectos/3/resumen-ampliado'
        self.assertEqual(client.get(url).status_code,401)
        for role, expected in [('geografo',403),('operador',403),('visualizador',200)]:
            app.dependency_overrides[auth.get_current_user]=lambda r=role: SimpleNamespace(rol=r,id_usuario=99999999)
            self.assertEqual(client.get(url).status_code,expected)


if __name__ == '__main__':
    unittest.main()
