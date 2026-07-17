"""
test_reportes_y_endpoints_especiales.py — Tests para endpoints especiales.

Cubre:
  - Dashboard y reportes de resumen.
  - Exportación CSV de tramos.
  - Bitácora de auditoría.
  - Asignación/remoción de usuarios a frentes.
"""

import pytest


class TestDashboard:
    """Endpoints de Dashboard y métricas."""

    def test_dashboard_devuelve_lista(self, client, admin_headers):
        res = client.get("/api/dashboard", headers=admin_headers)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_reporte_resumen_estructura(self, client, admin_headers):
        """El reporte resumen debe contener conteos de entidades."""
        res = client.get("/api/reportes/resumen", headers=admin_headers)
        assert res.status_code == 200
        body = res.json()
        assert "total_convenios" in body
        assert "total_nucleos" in body
        assert "total_afectaciones" in body
        assert "generado_el" in body


class TestExportacionCSV:
    """Exportación de datos a formato CSV."""

    def test_exportar_tramos_csv(self, client, admin_headers):
        """Debe devolver un archivo CSV válido."""
        res = client.get("/api/reportes/exportar/tramos", headers=admin_headers)
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

    def test_listar_bitacora_como_admin(self, client, admin_headers):
        res = client.get("/api/bitacora", headers=admin_headers)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_bitacora_tiene_estructura_correcta(self, client, admin_headers):
        """Cada entrada de bitácora debe tener los campos de auditoría."""
        res = client.get("/api/bitacora?limit=5", headers=admin_headers)
        assert res.status_code == 200
        entries = res.json()
        if len(entries) > 0:
            entry = entries[0]
            assert "id_bitacora" in entry
            assert "entidad_tipo" in entry
            assert "accion" in entry
            assert "fecha_hora" in entry


class TestAsignacionUsuarioFrente:
    """Asignación y remoción de usuarios a frentes."""

    def test_asignar_usuario_a_frente(
        self, client, admin_headers, seed_frente
    ):
        """Debe poder asignar un usuario a un frente."""
        # Obtener el id del usuario admin
        login_res = client.post(
            "/api/auth/login",
            data={"username": "admin@sistema.com", "password": "Admin123!"},
        )
        user_id = login_res.json()["user"]["id_usuario"]

        res = client.post(
            f"/api/frentes/{seed_frente['id_frente']}/asignar-usuario",
            json={"id_usuario": user_id},
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["activo"] is True

    def test_remover_usuario_de_frente(
        self, client, admin_headers, seed_frente
    ):
        """Debe poder remover al usuario del frente."""
        login_res = client.post(
            "/api/auth/login",
            data={"username": "admin@sistema.com", "password": "Admin123!"},
        )
        user_id = login_res.json()["user"]["id_usuario"]

        res = client.delete(
            f"/api/frentes/{seed_frente['id_frente']}/remover-usuario/{user_id}?motivo=Prueba",
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "success"

    def test_remover_asignacion_inexistente(self, client, admin_headers, seed_frente):
        """Remover un usuario no asignado devuelve 404."""
        res = client.delete(
            f"/api/frentes/{seed_frente['id_frente']}/remover-usuario/999999?motivo=Prueba",
            headers=admin_headers,
        )
        assert res.status_code == 404


class TestTramoDetalles:
    """Endpoint de detalles geoespaciales de tramo."""

    def test_tramo_detalles_existente(self, client, admin_headers, seed_tramo):
        nombre = seed_tramo["nombre_tramo"]
        res = client.get(
            f"/api/tramo-detalles?tramo={nombre}",
            headers=admin_headers,
        )
        assert res.status_code == 200
        body = res.json()
        assert "nombre_tramo" in body
        assert "longitud_km" in body

    def test_tramo_detalles_inexistente(self, client, admin_headers):
        res = client.get(
            "/api/tramo-detalles?tramo=Tramo Que No Existe",
            headers=admin_headers,
        )
        assert res.status_code == 404
