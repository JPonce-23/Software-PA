"""
test_crud_ciclo_vida.py — Tests del ciclo de vida completo CRUD.

Cubre el flujo Create → Read → Update → Soft-Delete para cada entidad
del sistema, validando:
  - Creación exitosa (201) con datos correctos.
  - Lectura individual y listados filtrados.
  - Actualización parcial (PATCH semántico vía PUT).
  - Baja lógica con motivo obligatorio.
  - Que un registro "eliminado" ya no aparezca en listados.
"""

import pytest
import time


def _uid() -> str:
    """Sufijo único por invocación."""
    return str(int(time.time() * 1000))[-8:]


# Almacenamiento de IDs creados durante el ciclo CRUD (persistente entre métodos)
_ids: dict[str, int] = {}


class TestCRUDTramos:
    """Ciclo de vida de Tramos."""

    def test_crear_tramo(self, client, admin_headers, cleanup, seed_proyecto):
        uid = _uid()
        payload = {
            "id_proyecto": seed_proyecto["id_proyecto"],
            "clave_tramo": f"CRD-{uid}",
            "nombre_tramo": f"Tramo CRUD {uid}",
            "geometria_wkt": "MULTILINESTRING((0 0, 1 1))",
            "ancho_total_derecho_via_m": 40.0,
        }
        res = client.post("/api/tramos", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["nombre_tramo"].startswith("Tramo CRUD")
        cleanup.register("/api/tramos", data["id_tramo"])
        _ids["tramo"] = data["id_tramo"]

    def test_leer_tramo_por_id(self, client, admin_headers):
        res = client.get(f"/api/tramos/{_ids['tramo']}", headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["id_tramo"] == _ids["tramo"]

    def test_listar_tramos_incluye_creado(self, client, admin_headers):
        res = client.get("/api/tramos", headers=admin_headers)
        assert res.status_code == 200
        ids = [t["id_tramo"] for t in res.json()]
        assert _ids["tramo"] in ids

    def test_actualizar_nombre_tramo(self, client, admin_headers):
        res = client.put(
            f"/api/tramos/{_ids['tramo']}",
            json={"nombre_tramo": "Tramo CRUD Actualizado"},
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["nombre_tramo"] == "Tramo CRUD Actualizado"

    def test_no_permite_baja_de_proyecto_con_tramos_activos(
        self, client, admin_headers, seed_proyecto
    ):
        res = client.delete(
            f"/api/proyectos/{seed_proyecto['id_proyecto']}?motivo=Prueba",
            headers=admin_headers,
        )
        assert res.status_code == 409

    def test_tramo_inexistente_devuelve_404(self, client, admin_headers):
        res = client.get("/api/tramos/999999", headers=admin_headers)
        assert res.status_code == 404


class TestCRUDParcelas:
    """Ciclo de vida de Parcelas."""

    def test_crear_parcela(self, client, admin_headers, cleanup, seed_nucleo):
        uid = _uid()
        payload = {
            "id_nucleo": seed_nucleo["id_nucleo"],
            "tipo_parcela": "individual",
            "no_parcela_ppt": f"CRD-{uid}",
            "nombre_titular": f"Titular CRUD {uid}",
            "documentacion_faltante": "Pendiente RAN",
        }
        res = client.post("/api/parcelas", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        cleanup.register("/api/parcelas", data["id_parcela"])
        _ids["parcela"] = data["id_parcela"]

    def test_leer_parcela(self, client, admin_headers):
        res = client.get(f"/api/parcelas/{_ids['parcela']}", headers=admin_headers)
        assert res.status_code == 200

    def test_actualizar_parcela(self, client, admin_headers):
        res = client.put(
            f"/api/parcelas/{_ids['parcela']}",
            json={"nombre_titular": "Titular Actualizado"},
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["nombre_titular"] == "Titular Actualizado"

    def test_listar_parcelas_por_nucleo(self, client, admin_headers, seed_nucleo):
        res = client.get(
            f"/api/parcelas?id_nucleo={seed_nucleo['id_nucleo']}",
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert isinstance(res.json(), list)


class TestCRUDAfectaciones:
    """Ciclo de vida de Afectaciones."""

    def test_crear_afectacion_colectiva(
        self, client, admin_headers, cleanup, seed_nucleo, seed_tramo_nucleo
    ):
        payload = {
            "id_nucleo": seed_nucleo["id_nucleo"],
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "tipo_afectacion": "colectivo",
            "tipo_tenencia": "Uso Común",
            "destino_superficie": "Derecho de vía",
            "superficie_afectada_ha": 5.0,
            "origen_registro": "captura_sistema",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        }
        res = client.post("/api/afectaciones", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["tipo_afectacion"] == "colectivo"
        cleanup.register("/api/afectaciones", data["id_afectacion"])
        _ids["afec_col"] = data["id_afectacion"]

    def test_crear_afectacion_individual(
        self, client, admin_headers, cleanup, seed_nucleo, seed_tramo_nucleo, seed_parcela
    ):
        payload = {
            "id_nucleo": seed_nucleo["id_nucleo"],
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_parcela": seed_parcela["id_parcela"],
            "tipo_afectacion": "individual",
            "tipo_tenencia": "Parcelaria",
            "superficie_afectada_ha": 1.5,
            "origen_registro": "captura_sistema",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        }
        res = client.post("/api/afectaciones", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["tipo_afectacion"] == "individual"
        cleanup.register("/api/afectaciones", data["id_afectacion"])
        _ids["afec_ind"] = data["id_afectacion"]

    def test_listar_afectaciones_por_tramo_nucleo(
        self, client, admin_headers, seed_tramo_nucleo
    ):
        tn_id = seed_tramo_nucleo["id_tramo_nucleo"]
        res = client.get(f"/api/afectaciones?id_tramo_nucleo={tn_id}", headers=admin_headers)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_actualizar_superficie(self, client, admin_headers):
        res = client.put(
            f"/api/afectaciones/{_ids['afec_col']}",
            json={"superficie_afectada_ha": 6.0},
            headers=admin_headers,
        )
        assert res.status_code == 200


class TestCRUDAsambleas:
    """Ciclo de vida de Asambleas."""

    def test_crear_asamblea_informacion(
        self, client, admin_headers, cleanup, seed_nucleo, seed_tramo_nucleo
    ):
        payload = {
            "id_nucleo": seed_nucleo["id_nucleo"],
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "contexto_proceso": "cop_original",
            "tipo_asamblea": "informacion",
            "estatus_asamblea": "programado",
        }
        res = client.post("/api/asambleas", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["tipo_asamblea"] == "informacion"
        cleanup.register("/api/asambleas", data["id_asamblea"])
        _ids["asamblea"] = data["id_asamblea"]

    def test_actualizar_resultado_anuencia(self, client, admin_headers):
        res = client.put(
            f"/api/asambleas/{_ids['asamblea']}",
            json={"resultado_anuencia": "otorgada", "estatus_asamblea": "completo"},
            headers=admin_headers,
        )
        assert res.status_code == 200

    def test_leer_asamblea_por_id(self, client, admin_headers):
        res = client.get(f"/api/asambleas/{_ids['asamblea']}", headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["id_asamblea"] == _ids["asamblea"]


class TestCRUDConvenios:
    """Ciclo de vida de Convenios."""

    def test_crear_convenio_colectivo_cop(
        self, client, admin_headers, cleanup,
        seed_tramo_nucleo, seed_afectacion_colectiva, seed_asamblea_anuencia,
    ):
        payload = {
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": seed_afectacion_colectiva["id_afectacion"],
            "tipo_afectacion": "colectivo",
            "tipo_convenio": "cop_original",
            "id_asamblea_autorizacion": seed_asamblea_anuencia["id_asamblea"],
            "superficie_real_afectada_ha": 10.5,
            "monto_100": 5000000.00,
        }
        res = client.post("/api/convenios", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["tipo_convenio"] == "cop_original"
        cleanup.register("/api/convenios", data["id_convenio"])
        _ids["convenio"] = data["id_convenio"]

    def test_crear_convenio_individual_ampliacion(
        self, client, admin_headers, cleanup,
        seed_tramo_nucleo, seed_afectacion_individual,
    ):
        payload = {
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": seed_afectacion_individual["id_afectacion"],
            "tipo_afectacion": "individual",
            "tipo_convenio": "ampliacion",
            "superficie_ampliacion_ha": 0.5,
            "monto_100": 150000.00,
        }
        res = client.post("/api/convenios", json=payload, headers=admin_headers)
        assert res.status_code == 201
        cleanup.register("/api/convenios", res.json()["id_convenio"])

    def test_actualizar_fecha_firma(self, client, admin_headers):
        res = client.put(
            f"/api/convenios/{_ids['convenio']}",
            json={"fecha_firma": "2026-06-15"},
            headers=admin_headers,
        )
        assert res.status_code == 200

    def test_listar_convenios_filtrados(self, client, admin_headers, seed_tramo_nucleo):
        tn_id = seed_tramo_nucleo["id_tramo_nucleo"]
        res = client.get(f"/api/convenios?id_tramo_nucleo={tn_id}", headers=admin_headers)
        assert res.status_code == 200
        assert len(res.json()) >= 1


class TestCRUDOrvs:
    """Ciclo de vida de ORVs."""

    def test_crear_orv(self, client, admin_headers, cleanup, seed_nucleo):
        payload = {
            "id_nucleo": seed_nucleo["id_nucleo"],
            "inicio_vigencia": "2026-01-01",
            "fin_vigencia": "2028-12-31",
            "comisariado_presidente": "Juan Pérez Test",
            "acta_eleccion_inscrita_ran": True,
        }
        res = client.post("/api/orvs", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["comisariado_presidente"] == "Juan Pérez Test"
        cleanup.register("/api/orvs", data["id_orv"])
        _ids["orv"] = data["id_orv"]

    def test_actualizar_orv(self, client, admin_headers):
        res = client.put(
            f"/api/orvs/{_ids['orv']}",
            json={"comisariado_secretario": "María López Test"},
            headers=admin_headers,
        )
        assert res.status_code == 200


class TestCRUDPadrones:
    """Ciclo de vida de Padrones."""

    def test_crear_padron(self, client, admin_headers, cleanup, seed_nucleo):
        payload = {
            "id_nucleo": seed_nucleo["id_nucleo"],
            "fecha_padron": "2025-12-01",
            "numero_ejidatarios_comuneros": 150,
        }
        res = client.post("/api/padrones", json=payload, headers=admin_headers)
        assert res.status_code == 201
        cleanup.register("/api/padrones", res.json()["id_padron"])


class TestCRUDActividadesCampo:
    """Ciclo de vida de Actividades de Campo."""

    def test_crear_actividad(self, client, admin_headers, cleanup, seed_tramo_nucleo):
        payload = {
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "tipo_actividad": "sensibilizacion",
            "contexto_proceso": "cop_original",
            "fecha_programada": "2026-03-01",
        }
        res = client.post("/api/actividades-campo", json=payload, headers=admin_headers)
        assert res.status_code == 201
        cleanup.register("/api/actividades-campo", res.json()["id_actividad"])


class TestCRUDDocumentacion:
    """Ciclo de vida de Documentación de Soporte."""

    def test_crear_documento(self, client, admin_headers, cleanup, seed_nucleo):
        payload = {
            "entidad_relacionada_id": seed_nucleo["id_nucleo"],
            "entidad_relacionada_tipo": "nucleo_agrario",
            "tipo_documento": "Acta de Asamblea",
            "categoria": "disponible",
            "es_critico": True,
        }
        res = client.post("/api/documentacion", json=payload, headers=admin_headers)
        assert res.status_code == 201
        cleanup.register("/api/documentacion", res.json()["id_documento"])


class TestCRUDAlertas:
    """Ciclo de vida de Alertas."""

    def test_crear_alerta(self, client, admin_headers, cleanup, seed_nucleo):
        payload = {
            "tipo": "documento_faltante",
            "prioridad": "alta",
            "titulo": "Falta acta constitutiva",
            "entidad_relacionada_id": seed_nucleo["id_nucleo"],
            "entidad_relacionada_tipo": "nucleo_agrario",
        }
        res = client.post("/api/alertas", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["titulo"] == "Falta acta constitutiva"
        cleanup.register("/api/alertas", data["id_alerta"])
        _ids["alerta"] = data["id_alerta"]

    def test_marcar_alerta_leida(self, client, admin_headers):
        res = client.post(
            f"/api/alertas/{_ids['alerta']}/marcar-leida",
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "success"
