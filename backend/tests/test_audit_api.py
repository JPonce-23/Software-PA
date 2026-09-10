"""Integration coverage for administrative audit projections."""

from datetime import datetime, timezone
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text

from app import models
from app.config import AUTH_SETTINGS
from app.database import SessionLocal
from app.main import app
from app.services.audit import calculate_changes


def _password() -> str:
    return f"Qa1!{uuid.uuid4().hex}Z"


def _create_user(api, *, role: str = "operador") -> tuple[dict, str]:
    password = _password()
    user = api(
        "POST",
        "/api/usuarios",
        expected=201,
        json={
            "nombre": "Auditoria",
            "apellido_paterno": "QA",
            "correo": f"audit-{uuid.uuid4().hex[:16]}@qa.local",
            "rol": role,
            "contrasena": password,
        },
    ).json()
    return user, password


def _login(email: str, password: str) -> tuple[TestClient, dict[str, str]]:
    client = TestClient(app, raise_server_exceptions=False)
    origin = AUTH_SETTINGS.allowed_origins[0]
    response = client.post(
        "/api/auth/sesiones",
        data={"username": email, "password": password},
        headers={"Origin": origin},
    )
    assert response.status_code == 200, response.text
    return client, {"Origin": origin, "X-CSRF-Token": client.cookies.get(AUTH_SETTINGS.csrf_cookie_name)}


def _block(email: str) -> None:
    for _ in range(5):
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/auth/sesiones",
            data={"username": email, "password": "contraseña incorrecta"},
            headers={"Origin": AUTH_SETTINGS.allowed_origins[0]},
        )
        assert response.status_code == 401, response.text


def test_changes_require_admin_and_return_sanitized_differences(api):
    assert TestClient(app, raise_server_exceptions=False).get("/api/auditoria/cambios").status_code == 401
    user, password = _create_user(api)
    client, headers = _login(user["correo"], password)
    assert client.get("/api/auditoria/cambios", headers=headers).status_code == 403

    project = api(
        "POST",
        "/api/proyectos",
        expected=201,
        json={"clave_proyecto": f"AUD-{uuid.uuid4().hex[:10]}", "nombre_proyecto": "Alta auditoría QA"},
    ).json()
    api("PATCH", f"/api/proyectos/{project['id_proyecto']}", json={"nombre_proyecto": "Cambio auditoría QA"})
    result = api(
        "GET",
        f"/api/auditoria/cambios?entidad_tipo=proyecto&id_proyecto={project['id_proyecto']}&limit=20",
    ).json()
    assert result["total"] >= 2
    update = next(item for item in result["items"] if item["accion"] == "update")
    assert update["accion_descripcion"] == "Modificación"
    fields = {change["campo"] for change in update["cambios"]}
    assert "nombre_proyecto" in fields
    assert "clave_proyecto" not in fields
    assert update["usuario"]["id_usuario"] == api("GET", "/api/auth/sesion").json()["user"]["id_usuario"]
    assert all("valor_anterior" not in item and "valor_nuevo" not in item for item in result["items"])

    redacted = calculate_changes(
        {"password": "anterior", "geometria_wkt": "POINT(0 0)", "igual": "x"},
        {"password": "nuevo", "geometria_wkt": "POINT(1 1)", "igual": "x"},
    )
    assert {item["campo"] for item in redacted} == {"geometria_wkt"}
    assert redacted[0]["anterior"] == redacted[0]["nuevo"] == "[geometría]"


def test_change_filters_pagination_and_reactivation(api):
    target, _ = _create_user(api)
    api("DELETE", f"/api/usuarios/{target['id_usuario']}", json={"motivo": "Baja para auditoría QA"})
    api("POST", f"/api/usuarios/{target['id_usuario']}/reactivar", json={"motivo": "Reactivación para auditoría QA"})
    user_changes = api(
        "GET",
        f"/api/auditoria/cambios?entidad_tipo=usuario&entidad_id={target['id_usuario']}&desde=2000-01-01T00:00:00Z&hasta=2100-01-01T00:00:00Z&limit=20",
    ).json()
    assert user_changes["total"] >= 3
    assert any(item["accion_descripcion"] == "Baja" for item in user_changes["items"])
    assert any(item["accion_descripcion"] == "Reactivación" for item in user_changes["items"])
    page_one = api(
        "GET",
        f"/api/auditoria/cambios?entidad_tipo=usuario&entidad_id={target['id_usuario']}&limit=1",
    ).json()
    page_two = api(
        "GET",
        f"/api/auditoria/cambios?entidad_tipo=usuario&entidad_id={target['id_usuario']}&skip=1&limit=1",
    ).json()
    assert page_one["total"] >= 2
    assert page_one["items"][0]["id_bitacora"] > page_two["items"][0]["id_bitacora"] or page_one["items"][0]["fecha_hora"] > page_two["items"][0]["fecha_hora"]


def test_access_events_and_append_only_privileges(api):
    target, password = _create_user(api)
    _block(target["correo"])
    api("POST", f"/api/usuarios/{target['id_usuario']}/desbloquear", json={"motivo": "Desbloqueo auditado QA"})
    _login(target["correo"], password)
    _login(target["correo"], password)
    api("POST", f"/api/usuarios/{target['id_usuario']}/revocar-sesiones", json={"motivo": "Revocación auditada QA"})
    events = api(
        "GET",
        f"/api/auditoria/accesos?id_usuario={target['id_usuario']}&motivo_codigo=desbloqueo_admin&limit=20",
    ).json()
    unlock = next(item for item in events["items"] if item["tipo_evento"] == "desbloqueo")
    assert unlock["usuario"]["id_usuario"] == target["id_usuario"]
    assert unlock["usuario_actor"]["id_usuario"] != target["id_usuario"]
    revoked = api(
        "GET",
        f"/api/auditoria/accesos?id_usuario={target['id_usuario']}&motivo_codigo=revocacion_admin&limit=20",
    ).json()
    assert len([item for item in revoked["items"] if item["tipo_evento"] == "sesion_revocada"]) == 2
    assert all("token_hash" not in str(item) and "csrf_hash" not in str(item) for item in revoked["items"])

    with SessionLocal() as db:
        privileges = db.execute(text("SELECT has_table_privilege(current_user, 'public.bitacora', 'INSERT'), has_table_privilege(current_user, 'public.bitacora', 'UPDATE'), has_table_privilege(current_user, 'public.bitacora', 'DELETE'), has_table_privilege(current_user, 'public.bitacora', 'TRUNCATE')")).one()
        assert privileges == (False, False, False, False)
        assert db.query(models.Bitacora).filter(models.Bitacora.entidad_tipo == "usuario", models.Bitacora.entidad_id == target["id_usuario"]).count() > 0
