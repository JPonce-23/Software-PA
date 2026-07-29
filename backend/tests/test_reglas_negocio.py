"""
test_reglas_negocio.py — Validaciones de reglas de negocio del dominio.

Verifica que la API rechace correctamente operaciones que violan
las restricciones documentadas en design.md:
  - Convenios: compatibilidad tipo_convenio vs tipo_afectacion.
  - Convenios: asamblea requerida para colectivos.
  - Convenios: obras complementarias sin BDT.
  - Afectaciones: individual requiere parcela.
  - Afectaciones: inconsistencia núcleo-tramo_nucleo.
  - Baja lógica: motivo obligatorio y no vacío.
"""

import pytest


class TestValidacionConvenios:
    """Reglas de negocio para la creación de convenios."""

    def test_convenio_colectivo_sin_asamblea_rechazado(
        self, client, admin_headers, seed_tramo_nucleo, seed_afectacion_colectiva
    ):
        """RN: Convenios colectivos requieren id_asamblea_autorizacion."""
        payload = {
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": seed_afectacion_colectiva["id_afectacion"],
            "tipo_afectacion": "colectivo",
            "tipo_convenio": "cop_original",
            # Sin id_asamblea_autorizacion
            "superficie_real_afectada_ha": 5.0,
        }
        res = client.post("/api/convenios", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert "asamblea" in res.json()["detail"].lower()

    def test_convenio_individual_con_asamblea_rechazado(
        self, client, admin_headers, seed_tramo_nucleo,
        seed_afectacion_individual, seed_asamblea_anuencia,
    ):
        """RN: Convenios individuales no deben tener asamblea."""
        payload = {
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": seed_afectacion_individual["id_afectacion"],
            "tipo_afectacion": "individual",
            "tipo_convenio": "cop_original",
            "id_asamblea_autorizacion": seed_asamblea_anuencia["id_asamblea"],
            "superficie_total_ha": 2.0,
        }
        res = client.post("/api/convenios", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert "individual" in res.json()["detail"].lower()

    def test_tipo_convenio_incompatible_con_afectacion_colectiva(
        self, client, admin_headers, seed_tramo_nucleo,
        seed_afectacion_colectiva, seed_asamblea_anuencia,
    ):
        """RN-1: tipo_convenio 'ampliacion' no permitido para afectación colectiva."""
        payload = {
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": seed_afectacion_colectiva["id_afectacion"],
            "tipo_afectacion": "colectivo",
            "tipo_convenio": "ampliacion",
            "id_asamblea_autorizacion": seed_asamblea_anuencia["id_asamblea"],
        }
        res = client.post("/api/convenios", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert "no permitido" in res.json()["detail"].lower()

    def test_tipo_convenio_incompatible_con_afectacion_individual(
        self, client, admin_headers, seed_tramo_nucleo, seed_afectacion_individual,
    ):
        """RN-1: tipo_convenio 'obras_complementarias' no permitido para individual."""
        payload = {
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": seed_afectacion_individual["id_afectacion"],
            "tipo_afectacion": "individual",
            "tipo_convenio": "obras_complementarias",
        }
        res = client.post("/api/convenios", json=payload, headers=admin_headers)
        assert res.status_code == 400

    def test_obras_complementarias_con_bdt_rechazado(
        self, client, admin_headers, seed_tramo_nucleo,
        seed_afectacion_colectiva, seed_asamblea_anuencia,
    ):
        """RN-2: Obras complementarias no deben tener monto_bdt."""
        payload = {
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": seed_afectacion_colectiva["id_afectacion"],
            "tipo_afectacion": "colectivo",
            "tipo_convenio": "obras_complementarias",
            "id_asamblea_autorizacion": seed_asamblea_anuencia["id_asamblea"],
            "monto_bdt": 100000.00,
        }
        res = client.post("/api/convenios", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert "bdt" in res.json()["detail"].lower()

    def test_modificatorio_sin_padre_rechazado(
        self, client, admin_headers, seed_tramo_nucleo,
        seed_afectacion_colectiva, seed_asamblea_anuencia,
    ):
        """RN: Modificatorio requiere id_convenio_padre."""
        payload = {
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": seed_afectacion_colectiva["id_afectacion"],
            "tipo_afectacion": "colectivo",
            "tipo_convenio": "modificatorio",
            "id_asamblea_autorizacion": seed_asamblea_anuencia["id_asamblea"],
            # Sin id_convenio_padre
        }
        res = client.post("/api/convenios", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert "padre" in res.json()["detail"].lower()

    def test_convenio_afectacion_inexistente(
        self, client, admin_headers, seed_tramo_nucleo,
    ):
        """La afectación referenciada debe existir."""
        payload = {
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": 999999,
            "tipo_afectacion": "colectivo",
            "tipo_convenio": "cop_original",
        }
        res = client.post("/api/convenios", json=payload, headers=admin_headers)
        assert res.status_code == 404

    def test_superficie_exclusiva_colectivo_rechaza_total(
        self, client, admin_headers, seed_tramo_nucleo,
        seed_afectacion_colectiva, seed_asamblea_anuencia,
    ):
        """RN-5: Colectivo debe usar superficie_real_afectada_ha, no superficie_total_ha."""
        payload = {
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": seed_afectacion_colectiva["id_afectacion"],
            "tipo_afectacion": "colectivo",
            "tipo_convenio": "cop_original",
            "id_asamblea_autorizacion": seed_asamblea_anuencia["id_asamblea"],
            "superficie_total_ha": 5.0,
        }
        res = client.post("/api/convenios", json=payload, headers=admin_headers)
        assert res.status_code == 400


class TestValidacionAfectaciones:
    """Reglas de negocio para afectaciones."""

    def test_individual_sin_parcela_rechazada(
        self, client, admin_headers, seed_nucleo, seed_tramo_nucleo,
    ):
        """Una afectación individual debe tener id_parcela."""
        payload = {
            "id_nucleo": seed_nucleo["id_nucleo"],
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "tipo_afectacion": "individual",
            "tipo_tenencia": "Parcelaria",
            "origen_registro": "migracion_excel",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
            # Sin id_parcela
        }
        res = client.post("/api/afectaciones", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert "parcela" in res.json()["detail"].lower()

    def test_tramo_nucleo_inconsistente_con_nucleo(
        self, client, admin_headers, seed_tramo_nucleo,
    ):
        """El tramo-núcleo debe pertenecer al núcleo indicado."""
        payload = {
            "id_nucleo": 999999,
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "tipo_afectacion": "colectivo",
            "tipo_tenencia": "Uso Común",
            "origen_registro": "migracion_excel",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        }
        res = client.post("/api/afectaciones", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert "inconsistencia" in res.json()["detail"].lower()

    def test_tramo_nucleo_inexistente(
        self, client, admin_headers, seed_nucleo,
    ):
        """El tramo-núcleo referenciado debe existir."""
        payload = {
            "id_nucleo": seed_nucleo["id_nucleo"],
            "id_tramo_nucleo": 999999,
            "tipo_afectacion": "colectivo",
            "tipo_tenencia": "Uso Común",
            "origen_registro": "migracion_excel",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        }
        res = client.post("/api/afectaciones", json=payload, headers=admin_headers)
        assert res.status_code == 404

    def test_geometria_confirmada_es_obligatoria(
        self, client, admin_headers, seed_nucleo, seed_tramo_nucleo,
    ):
        payload = {
            "id_nucleo": seed_nucleo["id_nucleo"],
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "tipo_afectacion": "colectivo",
            "tipo_tenencia": "Uso Común",
        }
        res = client.post("/api/afectaciones", json=payload, headers=admin_headers)
        assert res.status_code == 422

    def test_geometria_de_afectacion_debe_ser_poligonal(
        self, client, admin_headers, seed_nucleo, seed_tramo_nucleo,
    ):
        payload = {
            "id_nucleo": seed_nucleo["id_nucleo"],
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "tipo_afectacion": "colectivo",
            "tipo_tenencia": "Uso Común",
            "geometria_wkt": "LINESTRING(0 0, 1 1)",
        }
        res = client.post("/api/afectaciones", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert "polígono" in res.json()["detail"].lower()


class TestValidacionAsambleas:
    """Reglas de negocio para asambleas."""

    def test_asamblea_tramo_nucleo_inconsistente(
        self, client, admin_headers, seed_tramo_nucleo,
    ):
        """El tramo-núcleo debe pertenecer al núcleo indicado."""
        payload = {
            "id_nucleo": 999999,
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "tipo_asamblea": "informacion",
        }
        res = client.post("/api/asambleas", json=payload, headers=admin_headers)
        assert res.status_code == 400


class TestBajaLogica:
    """Validación de la baja lógica (soft delete) con motivo obligatorio (DA-9)."""

    def test_baja_sin_motivo_rechazada(self, client, admin_headers, seed_tramo):
        """DELETE sin parámetro 'motivo' debe devolver error."""
        res = client.delete(
            f"/api/tramos/{seed_tramo['id_tramo']}",
            headers=admin_headers,
        )
        # FastAPI devuelve 422 si falta un Query requerido
        assert res.status_code == 422

    def test_baja_con_motivo_vacio_rechazada(
        self, client, admin_headers, cleanup, seed_nucleo
    ):
        """Motivo vacío o solo espacios debe ser rechazado (DA-9)."""
        # Crear un recurso temporal para probar la baja
        payload = {
            "id_nucleo": seed_nucleo["id_nucleo"],
            "fecha_padron": "2020-01-01",
            "numero_ejidatarios_comuneros": 50,
        }
        res_create = client.post("/api/padrones", json=payload, headers=admin_headers)
        assert res_create.status_code == 201
        padron_id = res_create.json()["id_padron"]
        cleanup.register("/api/padrones", padron_id)

        # Intentar eliminar con motivo vacío
        res = client.delete(
            f"/api/padrones/{padron_id}?motivo=   ",
            headers=admin_headers,
        )
        assert res.status_code == 400
        assert "motivo" in res.json()["detail"].lower()
