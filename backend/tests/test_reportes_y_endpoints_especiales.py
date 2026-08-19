"""
test_reportes_y_endpoints_especiales.py — Tests para endpoints especiales.

Cubre:
  - Dashboard y reportes de resumen.
  - Exportación CSV de tramos.
  - Bitácora de auditoría.
  - Asignación/remoción de usuarios a tramos.
"""

import pytest


class TestDashboard:
    """Endpoints de Dashboard y métricas."""

    def test_dashboard_devuelve_lista(self, client, admin_session):
        res = client.get("/api/dashboard", headers=admin_session)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_reporte_resumen_estructura(self, client, admin_session):
        """El reporte resumen debe contener conteos de entidades."""
        res = client.get("/api/reportes/resumen", headers=admin_session)
        assert res.status_code == 200
        body = res.json()
        assert "total_convenios" in body
        assert "total_nucleos" in body
        assert "total_afectaciones" in body
        assert "generado_el" in body


class TestExportacionCSV:
    """Exportación de datos a formato CSV."""

    def test_exportar_tramos_csv(self, client, admin_session):
        """Debe devolver un archivo CSV válido."""
        res = client.get("/api/reportes/exportar/tramos", headers=admin_session)
        assert res.status_code == 200
        assert "text/csv" in res.headers.get("content-type", "")
        assert "Content-Disposition" in res.headers

        # Verificar que el CSV tiene headers válidos
        contenido = res.text
        primera_linea = contenido.split("\n")[0]
        assert "ID Tramo" in primera_linea
        assert "Nombre" in primera_linea


class TestBitacora:
    """Consulta de bitácora de auditoría."""

    def test_listar_bitacora_como_admin(self, client, admin_session):
        res = client.get("/api/bitacora", headers=admin_session)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_bitacora_tiene_estructura_correcta(self, client, admin_session):
        """Cada entrada de bitácora debe tener los campos de auditoría."""
        res = client.get("/api/bitacora?limit=5", headers=admin_session)
        assert res.status_code == 200
        entries = res.json()
        if len(entries) > 0:
            entry = entries[0]
            assert "id_bitacora" in entry
            assert "entidad_tipo" in entry
            assert "accion" in entry
            assert "fecha_hora" in entry


class TestAsignacionUsuarioTramo:
    """Asignación y remoción de usuarios a tramos."""

    def test_asignar_usuario_a_tramo(
        self, client, admin_session, admin_credentials, seed_tramo
    ):
        """Debe poder asignar un usuario a un tramo."""
        # Obtener el id del usuario admin
        sesion_res = client.get("/api/auth/sesion")
        user_id = sesion_res.json()["user"]["id_usuario"]

        res = client.post(
            f"/api/tramos/{seed_tramo['id_tramo']}/asignar-usuario",
            json={"id_usuario": user_id},
            headers=admin_session,
        )
        assert res.status_code == 200
        assert res.json()["activo"] is True

    def test_remover_usuario_de_tramo(
        self, client, admin_session, admin_credentials, seed_tramo
    ):
        """Debe poder remover al usuario del tramo."""
        sesion_res = client.get("/api/auth/sesion")
        user_id = sesion_res.json()["user"]["id_usuario"]

        res = client.delete(
            f"/api/tramos/{seed_tramo['id_tramo']}/remover-usuario/{user_id}?motivo=Prueba",
            headers=admin_session,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "success"

    def test_remover_asignacion_inexistente(self, client, admin_session, seed_tramo):
        """Remover un usuario no asignado devuelve 404."""
        res = client.delete(
            f"/api/tramos/{seed_tramo['id_tramo']}/remover-usuario/999999?motivo=Prueba",
            headers=admin_session,
        )
        assert res.status_code == 404

    def test_reactivar_asignacion_exige_motivo_y_registra_reactivacion(
        self, client, admin_session, admin_credentials, seed_tramo
    ):
        sesion_res = client.get("/api/auth/sesion")
        user_id = sesion_res.json()["user"]["id_usuario"]
        endpoint = f"/api/tramos/{seed_tramo['id_tramo']}/asignar-usuario"

        sin_motivo = client.post(endpoint, json={"id_usuario": user_id}, headers=admin_session)
        assert sin_motivo.status_code == 400

        reactivada = client.post(
            endpoint,
            json={
                "id_usuario": user_id,
                "motivo_reactivacion": "Se reasigna al responsable territorial.",
            },
            headers=admin_session,
        )
        assert reactivada.status_code == 200
        assert reactivada.json()["activo"] is True

        limpieza = client.delete(
            f"/api/tramos/{seed_tramo['id_tramo']}/remover-usuario/{user_id}?motivo=Limpieza",
            headers=admin_session,
        )
        assert limpieza.status_code == 200


class TestTramoDetalles:
    """Endpoint de detalles geoespaciales de tramo."""

    def test_tramo_detalles_existente(self, client, admin_session, seed_tramo):
        res = client.get(
            f"/api/tramo-detalles?id_tramo={seed_tramo['id_tramo']}",
            headers=admin_session,
        )
        assert res.status_code == 200
        body = res.json()
        assert "nombre_tramo" in body
        assert "longitud_km" in body

    def test_franjas_activas_filtra_por_proyecto(
        self, client, admin_session, seed_proyecto, seed_tramo
    ):
        response = client.get(
            f"/api/franjas/activas?id_proyecto={seed_proyecto['id_proyecto']}",
            headers=admin_session,
        )
        assert response.status_code == 200, response.text
        assert response.json()
        assert {item["id_proyecto"] for item in response.json()} == {seed_proyecto["id_proyecto"]}

    def test_tramo_detalles_inexistente(self, client, admin_session):
        res = client.get(
            "/api/tramo-detalles?id_tramo=999999",
            headers=admin_session,
        )
        assert res.status_code == 404
