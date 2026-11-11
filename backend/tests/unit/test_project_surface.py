"""Run with python -m unittest discover -s tests/unit -p test_project_surface.py."""
import unittest
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.services.project_surface import summarize_surfaces


class SurfaceSummaryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        self.db = Session(self.engine)
        for sql in (
            "CREATE TABLE afectacion (id_afectacion INTEGER, id_proyecto_nucleo INTEGER, superficie_afectada_ha NUMERIC, activo BOOLEAN)",
            "CREATE TABLE unidad_agraria (id_unidad_agraria INTEGER, activo BOOLEAN)",
            "CREATE TABLE afectacion_unidad_agraria (id_afectacion_unidad INTEGER, id_afectacion INTEGER, id_unidad_agraria INTEGER, superficie_afectada_ha NUMERIC, activo BOOLEAN)",
            "INSERT INTO unidad_agraria VALUES (1,1),(2,1),(3,0)",
            "INSERT INTO afectacion VALUES (1,10,10,1),(2,10,NULL,1),(3,20,NULL,1),(4,30,0,1),(5,40,99,0),(6,50,NULL,1)",
            "INSERT INTO afectacion_unidad_agraria VALUES (1,1,1,10,1),(2,2,1,2,1),(3,2,2,3,1),(4,2,3,99,1),(5,2,1,99,0),(6,3,1,NULL,1),(7,4,1,20,1),(8,6,1,2,1),(9,6,2,NULL,1)",
        ):
            self.db.execute(text(sql))

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_parent_and_destinations_not_added_twice(self):
        result = summarize_surfaces(self.db, [10])[10]
        self.assertEqual(result["superficie_resumen_ha"], Decimal("15"))
        self.assertEqual(result["afectaciones_superficie_incompleta"], 0)

    def test_missing_is_not_zero(self):
        result = summarize_surfaces(self.db, [20])[20]
        self.assertIsNone(result["superficie_resumen_ha"])
        self.assertEqual(result["afectaciones_superficie_incompleta"], 1)

    def test_explicit_zero_takes_precedence(self):
        self.assertEqual(summarize_surfaces(self.db, [30])[30]["superficie_resumen_ha"], 0)

    def test_partial_destination_total_is_identified(self):
        result = summarize_surfaces(self.db, [50])[50]
        self.assertEqual(result["superficie_resumen_ha"], 2)
        self.assertEqual(result["afectaciones_superficie_incompleta"], 1)

    def test_inactive_and_unrequested_nuclei_excluded(self):
        self.assertEqual(summarize_surfaces(self.db, [40,999]), {})

    def test_empty_page(self):
        self.assertEqual(summarize_surfaces(self.db, []), {})
