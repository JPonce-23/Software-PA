"""
test_auth.py — Pruebas de autenticación y autorización (JWT + RBAC).

Valida:
  - Login con credenciales válidas e inválidas.
  - Protección de rutas sin token.
  - Restricción por rol (RoleChecker).
  - Estructura del token devuelto.
"""

import pytest


class TestLogin:
    """Flujo de autenticación: /api/auth/login"""

    def test_login_exitoso_devuelve_token_y_datos_usuario(self, client):
        """Un login válido debe devolver access_token, token_type y datos del usuario."""
        res = client.post(
            "/api/auth/login",
            data={"username": "admin@sistema.com", "password": "Admin123!"},
        )
        assert res.status_code == 200
        body = res.json()

        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert "user" in body

        user = body["user"]
        assert user["correo"] == "admin@sistema.com"
        assert user["rol"] == "admin"
        assert "id_usuario" in user

    def test_login_correo_inexistente(self, client):
        """Correo no registrado debe devolver 401."""
        res = client.post(
            "/api/auth/login",
            data={"username": "noexiste@sistema.com", "password": "abc123"},
        )
        assert res.status_code == 401
        assert "Credenciales incorrectas" in res.json()["detail"]

    def test_login_contrasena_incorrecta(self, client):
        """Contraseña errónea para un usuario real debe devolver 401."""
        res = client.post(
            "/api/auth/login",
            data={"username": "admin@sistema.com", "password": "ClaveErronea99"},
        )
        assert res.status_code == 401

    def test_login_sin_campos(self, client):
        """Petición sin campos username/password debe devolver 422."""
        res = client.post("/api/auth/login", data={})
        assert res.status_code == 422


class TestProteccionRutas:
    """Verificar que todas las rutas protegidas bloquean acceso sin JWT."""

    @pytest.mark.parametrize("ruta", [
        "/api/tramos",
        "/api/frentes",
        "/api/tramos-nucleos",
        "/api/parcelas",
        "/api/afectaciones",
        "/api/asambleas",
        "/api/convenios",
        "/api/orvs",
        "/api/padrones",
        "/api/actividades-campo",
        "/api/fifonafe",
        "/api/documentacion",
        "/api/alertas",
        "/api/usuarios",
        "/api/bitacora",
        "/api/dashboard",
        "/api/reportes/resumen",
    ])
    def test_get_sin_token_devuelve_401(self, client, ruta):
        """Toda ruta protegida debe devolver 401 sin token."""
        res = client.get(ruta)
        assert res.status_code == 401, f"Ruta {ruta} no está protegida"

    def test_token_invalido_devuelve_401(self, client):
        """Un Bearer token inventado debe ser rechazado."""
        headers = {"Authorization": "Bearer token.falso.inventado"}
        res = client.get("/api/tramos", headers=headers)
        assert res.status_code == 401


class TestRutasPublicas:
    """Rutas que no requieren autenticación."""

    def test_root_accesible(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert "message" in res.json()

    def test_catalogos_entidades_accesible(self, client):
        """Los catálogos geográficos son públicos."""
        res = client.get("/api/catalogos/entidades")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_catalogos_municipios_accesible(self, client):
        res = client.get("/api/catalogos/municipios")
        assert res.status_code == 200
        assert isinstance(res.json(), list)
