"""Integration tests for independent, atomic credential operations."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError

from app import models
from app.config import AUTH_SETTINGS
from app.database import SessionLocal
from app.main import app
from app.services.authentication import hash_password
from app.services.common import set_audit_context


def _password() -> str:
    return f"Qa1!{uuid.uuid4().hex}Z"


def _create_user(api, *, role="operador"):
    password = _password()
    user = api(
        "POST", "/api/usuarios", expected=201,
        json={"nombre": "Credencial", "apellido_paterno": "QA", "correo": f"cred-{uuid.uuid4().hex[:16]}@qa.local", "rol": role, "contrasena": password},
    ).json()
    return user, password


def _login(email, password):
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/api/auth/sesiones", data={"username": email, "password": password}, headers={"Origin": AUTH_SETTINGS.allowed_origins[0]})
    assert response.status_code == 200, response.text
    return client, {"Origin": AUTH_SETTINGS.allowed_origins[0], "X-CSRF-Token": client.cookies.get(AUTH_SETTINGS.csrf_cookie_name)}


def _block(email):
    for _ in range(5):
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/auth/sesiones", data={"username": email, "password": "Contraseña incorrecta"}, headers={"Origin": AUTH_SETTINGS.allowed_origins[0]},
        )
        assert response.status_code == 401, response.text


@pytest.mark.parametrize(
    ("password", "expected"),
    [
        ("abc1234", 422),
        ("abcd1234", 201),
        ("12345678", 422),
        ("abcdefgh", 422),
        ("a1" + "ñ" * 36, 422),
    ],
)
def test_user_create_password_policy(api, password, expected):
    response = api(
        "POST", "/api/usuarios", expected=expected,
        json={
            "nombre": "Política",
            "apellido_paterno": "QA",
            "correo": f"policy-{uuid.uuid4().hex[:16]}@qa.local",
            "rol": "operador",
            "contrasena": password,
        },
    )
    assert response.status_code == expected


def test_password_policy_applies_to_own_change_and_admin_reset(api):
    target, old_password = _create_user(api)
    client, headers = _login(target["correo"], old_password)
    assert client.post(
        "/api/auth/cambiar-contrasena", headers=headers,
        json={"contrasena_actual": old_password, "contrasena_nueva": "abcd1234"},
    ).status_code == 200
    reset_target, _ = _create_user(api)
    assert api(
        "POST", f"/api/usuarios/{reset_target['id_usuario']}/restablecer-contrasena",
        json={"contrasena_nueva": "abcd1234", "motivo": "Validación de política QA"},
    ).status_code == 200


def test_current_password_over_72_utf8_bytes_is_422(api):
    target, password = _create_user(api)
    client, headers = _login(target["correo"], password)
    response = client.post(
        "/api/auth/cambiar-contrasena", headers=headers,
        json={"contrasena_actual": "ñ" * 37, "contrasena_nueva": _password()},
    )
    assert response.status_code == 422


def test_password_hash_update_requires_actor_and_creates_no_empty_audit(api):
    target, _ = _create_user(api)
    with SessionLocal() as db:
        user = db.get(models.Usuario, target["id_usuario"])
        user.contrasena_hash = hash_password("actorless123")
        with pytest.raises(DBAPIError, match="app.current_user_id"):
            db.commit()
        db.rollback()

    actor_id = api("GET", "/api/auth/sesion").json()["user"]["id_usuario"]
    with SessionLocal() as db:
        before = db.query(models.Bitacora).filter(
            models.Bitacora.entidad_tipo == "usuario",
            models.Bitacora.entidad_id == target["id_usuario"],
        ).count()
        user = db.get(models.Usuario, target["id_usuario"])
        set_audit_context(db, actor_id)
        user.contrasena_hash = hash_password("actorpresent123")
        db.commit()
        after = db.query(models.Bitacora).filter(
            models.Bitacora.entidad_tipo == "usuario",
            models.Bitacora.entidad_id == target["id_usuario"],
        ).count()
        assert after == before


def test_admin_changes_email_atomically_and_keeps_account_state(api):
    target, password = _create_user(api)
    _login(target["correo"], password)
    _login(target["correo"], password)
    with SessionLocal() as db:
        state = db.get(models.EstadoAutenticacionUsuario, target["id_usuario"])
        state_before = (state.intentos_fallidos, state.bloqueado_hasta, state.ultimo_acceso_en)
    new_email = f"nuevo.correo-{uuid.uuid4().hex[:12]}@qa.local"
    changed = api(
        "PATCH", f"/api/usuarios/{target['id_usuario']}/correo",
        json={"correo": f"  {new_email.upper()} ", "motivo": "Actualización institucional QA"},
    ).json()
    assert changed["sesiones_revocadas"] == 2
    with SessionLocal() as db:
        user = db.get(models.Usuario, target["id_usuario"])
        state = db.get(models.EstadoAutenticacionUsuario, target["id_usuario"])
        assert user.correo == new_email and user.activo is True
        assert (state.intentos_fallidos, state.bloqueado_hasta, state.ultimo_acceso_en) == state_before
        assert db.query(models.SesionUsuario).filter(models.SesionUsuario.id_usuario == target["id_usuario"], models.SesionUsuario.revocada_en.is_(None)).count() == 0
    audit = api("GET", f"/api/auditoria/cambios?entidad_tipo=usuario&entidad_id={target['id_usuario']}&limit=20").json()["items"]
    correo = next(change for item in audit for change in item["cambios"] if change["campo"] == "correo")
    assert correo["anterior"] == target["correo"] and correo["nuevo"] == new_email
    events = api("GET", f"/api/auditoria/accesos?id_usuario={target['id_usuario']}&motivo_codigo=cambio_correo_admin").json()["items"]
    event = next(item for item in events if item["tipo_evento"] == "cambio_correo")
    assert event["usuario_actor"]["id_usuario"] != target["id_usuario"]
    assert api("PATCH", f"/api/usuarios/{target['id_usuario']}/correo", expected=409, json={"correo": new_email, "motivo": "Sin cambio"}).status_code == 409
    duplicate, _ = _create_user(api)
    assert api("PATCH", f"/api/usuarios/{target['id_usuario']}/correo", expected=409, json={"correo": duplicate["correo"], "motivo": "Duplicado QA"}).status_code == 409
    assert api("PATCH", f"/api/usuarios/{target['id_usuario']}/correo", expected=422, json={"correo": "otro@qa.local", "motivo": "Extra QA", "rol": "admin"}).status_code == 422


def test_email_permissions_and_inactive_target(api):
    target, _ = _create_user(api)
    assert TestClient(app, raise_server_exceptions=False).patch(f"/api/usuarios/{target['id_usuario']}/correo", json={"correo": "x@qa.local", "motivo": "No autenticado"}).status_code == 401
    operator, password = _create_user(api)
    client, headers = _login(operator["correo"], password)
    assert client.patch(f"/api/usuarios/{target['id_usuario']}/correo", headers=headers, json={"correo": "x@qa.local", "motivo": "No autorizado"}).status_code == 403
    assert api("PATCH", "/api/usuarios/999999999/correo", expected=404, json={"correo": "x@qa.local", "motivo": "Inexistente"}).status_code == 404
    api("DELETE", f"/api/usuarios/{target['id_usuario']}", json={"motivo": "Baja antes de correo QA"})
    api("PATCH", f"/api/usuarios/{target['id_usuario']}/correo", json={"correo": f"inactivo-{uuid.uuid4().hex[:12]}@qa.local", "motivo": "Correo inactivo QA"})
    with SessionLocal() as db:
        assert db.get(models.Usuario, target["id_usuario"]).activo is False


def test_own_password_change_revokes_sessions_without_empty_audit(api):
    target, old_password = _create_user(api)
    client, headers = _login(target["correo"], old_password)
    _login(target["correo"], old_password)
    with SessionLocal() as db:
        before = db.query(models.Bitacora).filter(models.Bitacora.entidad_tipo == "usuario", models.Bitacora.entidad_id == target["id_usuario"]).count()
    new_password = _password()
    result = client.post("/api/auth/cambiar-contrasena", headers=headers, json={"contrasena_actual": old_password, "contrasena_nueva": new_password})
    assert result.status_code == 200 and result.json()["sesiones_revocadas"] == 2
    assert client.get("/api/auth/sesion").status_code == 401
    assert TestClient(app, raise_server_exceptions=False).post("/api/auth/sesiones", data={"username": target["correo"], "password": old_password}, headers={"Origin": AUTH_SETTINGS.allowed_origins[0]}).status_code == 401
    _login(target["correo"], new_password)
    with SessionLocal() as db:
        after = db.query(models.Bitacora).filter(models.Bitacora.entidad_tipo == "usuario", models.Bitacora.entidad_id == target["id_usuario"]).count()
        assert after == before
    assert client.post("/api/auth/cambiar-contrasena", headers=headers, json={"contrasena_actual": old_password, "contrasena_nueva": _password()}).status_code == 401
    fresh, fresh_headers = _login(target["correo"], new_password)
    assert fresh.post("/api/auth/cambiar-contrasena", headers=fresh_headers, json={"contrasena_actual": new_password, "contrasena_nueva": new_password}).status_code == 409
    assert fresh.post("/api/auth/cambiar-contrasena", headers=fresh_headers, json={"contrasena_actual": new_password, "contrasena_nueva": "débil", "extra": True}).status_code == 422
    events = api("GET", f"/api/auditoria/accesos?id_usuario={target['id_usuario']}&motivo_codigo=cambio_contrasena_usuario").json()["items"]
    assert any(item["tipo_evento"] == "cambio_contrasena" for item in events)
    assert "contrasena_hash" not in str(events)


def test_admin_password_reset_keeps_inactive_blocked_and_rejects_self(api):
    target, old_password = _create_user(api)
    _login(target["correo"], old_password)
    _block(target["correo"])
    api("DELETE", f"/api/usuarios/{target['id_usuario']}", json={"motivo": "Baja antes de reset QA"})
    with SessionLocal() as db:
        state = db.get(models.EstadoAutenticacionUsuario, target["id_usuario"])
        state_before = (state.intentos_fallidos, state.bloqueado_hasta)
    new_password = _password()
    reset = api("POST", f"/api/usuarios/{target['id_usuario']}/restablecer-contrasena", json={"contrasena_nueva": new_password, "motivo": "Restablecimiento administrativo QA"}).json()
    assert reset["sesiones_revocadas"] == 0
    with SessionLocal() as db:
        user = db.get(models.Usuario, target["id_usuario"])
        state = db.get(models.EstadoAutenticacionUsuario, target["id_usuario"])
        assert user.activo is False and (state.intentos_fallidos, state.bloqueado_hasta) == state_before
    assert api("POST", f"/api/usuarios/{target['id_usuario']}/restablecer-contrasena", expected=409, json={"contrasena_nueva": new_password, "motivo": "No repetir"}).status_code == 409
    assert api("POST", "/api/usuarios/999999999/restablecer-contrasena", expected=404, json={"contrasena_nueva": _password(), "motivo": "Inexistente"}).status_code == 404
    assert api("POST", f"/api/usuarios/{target['id_usuario']}/restablecer-contrasena", expected=422, json={"contrasena_nueva": "débil", "motivo": "Débil QA"}).status_code == 422
    assert api("POST", f"/api/usuarios/{target['id_usuario']}/restablecer-contrasena", expected=422, json={"contrasena_nueva": _password(), "motivo": "Extra QA", "extra": True}).status_code == 422
    admin_id = api("GET", "/api/auth/sesion").json()["user"]["id_usuario"]
    assert api("POST", f"/api/usuarios/{admin_id}/restablecer-contrasena", expected=409, json={"contrasena_nueva": _password(), "motivo": "No sobre sí mismo"}).status_code == 409
    events = api("GET", f"/api/auditoria/accesos?id_usuario={target['id_usuario']}&motivo_codigo=restablecimiento_contrasena_admin").json()["items"]
    event = next(item for item in events if item["tipo_evento"] == "restablecimiento_contrasena")
    assert event["usuario_actor"]["id_usuario"] != target["id_usuario"]
