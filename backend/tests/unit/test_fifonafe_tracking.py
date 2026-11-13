"""Integration checks on the explicitly isolated FIFONAFE QA copy only."""
import os
import unittest
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from app import models as m, auth
from app.database import SessionLocal
from app.routers.fifonafe_tracking import router


class TrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv("DB_NAME") != "db_integracion_mq_local_revision_20261112":
            raise RuntimeError("Use only the isolated FIFONAFE QA database")
        with SessionLocal() as db:
            cls.uid = db.execute(select(m.Usuario.id_usuario).where(m.Usuario.rol == "admin", m.Usuario.activo.is_(True))).scalars().first()
            c = db.execute(select(m.Convenio.id_convenio, m.ProyectoNucleo.id_proyecto)
                    .join(m.ProyectoNucleo, m.ProyectoNucleo.id_proyecto_nucleo == m.Convenio.id_proyecto_nucleo)
                    .where(m.Convenio.activo.is_(True), m.ProyectoNucleo.activo.is_(True), m.Convenio.tipo_instrumento == "convenio")).first()
            cls.cid, cls.pid = c
        cls.app = FastAPI()
        cls.app.include_router(router, prefix="/api")
        cls.client = TestClient(cls.app)

    def setUp(self):
        self.as_role("admin")

    def as_role(self, role):
        self.app.dependency_overrides[auth.get_current_user] = lambda: SimpleNamespace(rol=role, id_usuario=self.uid if role == "admin" else 99999999)

    def get_list(self, **params):
        return self.client.get(f"/api/proyectos/{self.pid}/fifonafe/seguimiento", params=params)

    def test_authentication_required(self):
        self.app.dependency_overrides.clear()
        self.assertEqual(self.get_list().status_code, 401)

    def test_visualizer_read_only(self):
        self.as_role("visualizador")
        self.assertEqual(self.get_list().status_code, 200)
        self.assertEqual(self.client.post(f"/api/convenios/{self.cid}/fifonafe/etiquetas",json={"codigo":"espera_firma","habilitada":True,"motivo":"Prueba de permisos"}).status_code,403)

    def test_geographer_denied(self):
        self.as_role("geografo")
        self.assertEqual(self.get_list().status_code,403)

    def test_unassigned_operator_denied(self):
        self.as_role("operador")
        self.assertEqual(self.get_list().status_code,403)

    def test_page_totals_and_no_duplicates(self):
        first=self.get_list(limit=1).json(); second=self.get_list(limit=1,skip=1).json()
        self.assertEqual(first["total"],first["individuales"]+first["colectivos"])
        self.assertEqual(len(first["items"]),1)
        if second["items"]: self.assertNotEqual(first["items"][0]["id_convenio"],second["items"][0]["id_convenio"])
        self.assertTrue(first["etiquetas_disponibles"])

    def test_filter(self):
        data=self.get_list(ambito="colectivo").json()
        self.assertEqual(data["total"],data["colectivos"])
        self.assertTrue(all(c["ambito"]=="colectivo" for c in data["items"]))

    def test_label_reason_required(self):
        r=self.client.post(f"/api/convenios/{self.cid}/fifonafe/etiquetas",json={"codigo":"espera_firma","habilitada":True,"motivo":"     "})
        self.assertEqual(r.status_code,422)

    def test_label_activation_retirement_and_immutable_history(self):
        ids=[]
        for enabled in (True,False):
            r=self.client.post(f"/api/convenios/{self.cid}/fifonafe/etiquetas",json={"codigo":"espera_firma","habilitada":enabled,"motivo":"Prueba aislada de historial"})
            self.assertEqual(r.status_code,201,r.text); ids.append(r.json()["id_etiqueta"])
        with SessionLocal() as db:
            self.assertEqual(len(db.execute(select(m.EtiquetaSeguimientoFifonafe.id_etiqueta).where(m.EtiquetaSeguimientoFifonafe.id_etiqueta.in_(ids))).all()),2)
            with self.assertRaises(DBAPIError):
                db.execute(text("UPDATE etiqueta_seguimiento_fifonafe SET motivo='alterado' WHERE id_etiqueta=:id"),{"id":ids[0]})
            db.rollback()
