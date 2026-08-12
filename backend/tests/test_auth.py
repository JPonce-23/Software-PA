"""
test_auth.py — Pruebas de autenticación (sesión cookie + RBAC).

Valida:
  - Login con credenciales válidas e inválidas vía sesiones.
  - Protección de rutas sin autenticación.
  - Restricción por rol (RoleChecker).
  - Contracción verificada: endpoint legacy y bearer eliminados.
"""

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.config import AUTH_SETTINGS
from app.main import app
from scripts.create_admin import BootstrapError, validate_admin_config


ORIGIN = AUTH_SETTINGS.allowed_origins[0]


class TestLoginSesion:
    """Flujo de autenticación: POST /api/auth/sesiones"""

    def test_login_exitoso_devuelve_sesion_y_cookies(self, admin_credentials):
        """Un login válido debe setear cookies y devolver datos de usuario."""
        with TestClient(app, raise_server_exceptions=False) as browser:
            res = browser.post(
                "/api/auth/sesiones",
                data={
                    "username": admin_credentials["email"],
                    "password": admin_credentials["password"],
                },
                headers={"Origin": ORIGIN},
            )
            assert res.status_code == 200
            body = res.json()

            assert "access_token" not in body
            assert "user" in body

            user = body["user"]
            assert user["correo"] == admin_credentials["email"]
            assert user["rol"] == "admin"
            assert "id_usuario" in user

            assert browser.cookies.get(AUTH_SETTINGS.session_cookie_name)
            assert browser.cookies.get(AUTH_SETTINGS.csrf_cookie_name)

            set_cookie = res.headers.get("set-cookie", "")
            assert "HttpOnly" in set_cookie

            csrf = browser.cookies.get(AUTH_SETTINGS.csrf_cookie_name)
            logout = browser.post(
                "/api/auth/logout",
                headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            )
            assert logout.status_code == 200

    def test_login_correo_inexistente(self):
        """Correo no registrado debe devolver 401."""
        with TestClient(app, raise_server_exceptions=False) as browser:
            res = browser.post(
                "/api/auth/sesiones",
                data={"username": "noexiste@sistema.com", "password": "abc123"},
                headers={"Origin": ORIGIN},
            )
            assert res.status_code == 401
            assert "Credenciales incorrectas" in res.json()["detail"]

    def test_login_contrasena_incorrecta(self, admin_credentials):
        """Contraseña errónea para un usuario real debe devolver 401."""
        with TestClient(app, raise_server_exceptions=False) as browser:
            res = browser.post(
                "/api/auth/sesiones",
                data={
                    "username": admin_credentials["email"],
                    "password": "ClaveErronea99!x",
                },
                headers={"Origin": ORIGIN},
            )
            assert res.status_code == 401

    def test_login_sin_campos(self):
        """Petición sin campos username/password debe devolver 422."""
        with TestClient(app, raise_server_exceptions=False) as browser:
            res = browser.post(
                "/api/auth/sesiones",
                data={},
                headers={"Origin": ORIGIN},
            )
            assert res.status_code == 422


class TestProteccionRutas:
    """Verificar que todas las rutas protegidas bloquean acceso sin sesión."""

    @pytest.mark.parametrize("ruta", [
        "/api/tramos",
        "/api/proyectos",
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
    def test_get_sin_sesion_devuelve_401(self, client, ruta):
        """Toda ruta protegida debe devolver 401 sin cookie de sesión."""
        with TestClient(app, raise_server_exceptions=False) as browser:
            res = browser.get(ruta)
            assert res.status_code == 401, f"Ruta {ruta} no está protegida"

    def test_cookie_inventada_devuelve_401(self):
        """Una cookie de sesión inventada debe ser rechazada."""
        with TestClient(app, raise_server_exceptions=False) as browser:
            browser.cookies.set(AUTH_SETTINGS.session_cookie_name, "token.falso.inventado")
            res = browser.get("/api/tramos")
            assert res.status_code == 401


class TestContraccionBearer:
    """Verificar que el mecanismo bearer/JWT ha sido retirado."""

    def test_endpoint_login_legacy_no_existe(self):
        """POST /api/auth/login debe retornar 404 o 405 post-contracción."""
        with TestClient(app, raise_server_exceptions=False) as browser:
            res = browser.post(
                "/api/auth/login",
                data={"username": "admin@test.com", "password": "test"},
            )
            assert res.status_code in (404, 405)

    def test_bearer_token_no_autentica(self):
        """Un Authorization: Bearer header no debe conceder acceso."""
        with TestClient(app, raise_server_exceptions=False) as browser:
            headers = {"Authorization": "Bearer token.jwt.inventado"}
            res = browser.get("/api/tramos", headers=headers)
            assert res.status_code == 401


class TestRutasPublicas:
    """Rutas que no requieren autenticación."""

    def test_root_accesible(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert "message" in res.json()

    def test_catalogos_entidades_requiere_autenticacion(self, client, admin_session):
        """Los catálogos geográficos requieren un usuario autenticado."""
        res = client.get("/api/catalogos/entidades", headers=admin_session)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_catalogos_municipios_requiere_autenticacion(self, client, admin_session):
        res = client.get("/api/catalogos/municipios", headers=admin_session)
        assert res.status_code == 200
        assert isinstance(res.json(), list)


class TestHardeningCorte3:
    def test_detecta_secret_key_placeholder(self):
        assert auth._is_insecure_secret_key("change_me_generate_with_openssl_rand_hex_32")
        assert auth._is_insecure_secret_key("short")
        assert not auth._is_insecure_secret_key("a" * 32)

    def test_bootstrap_admin_rechaza_password_debil(self):
        with pytest.raises(BootstrapError):
            validate_admin_config(
                "responsable.seguridad@pa.test",
                "password",
                "Responsable",
                "Seguridad",
            )

    def test_bootstrap_admin_acepta_configuracion_segura(self):
        validate_admin_config(
            "responsable.seguridad@pa.test",
            "ClaveInicial!2026",
            "Responsable",
            "Seguridad",
        )
