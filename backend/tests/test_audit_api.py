"""Integration coverage for administrative audit projections."""

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app import models
from app.config import AUTH_SETTINGS
from app.database import SessionLocal
from app.main import app
from app.services.audit import calculate_changes
from app.services import authentication
from app.services.common import set_audit_context


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
    with SessionLocal() as db:
        session_ids = [row.id_sesion for row in db.query(models.SesionUsuario).filter_by(id_usuario=target["id_usuario"])]
        before = {session_id: _session_audit(db, session_id).count() for session_id in session_ids}
    api("POST", f"/api/usuarios/{target['id_usuario']}/revocar-sesiones", json={"motivo": "Revocación auditada QA"})
    with SessionLocal() as db:
        for session_id in session_ids:
            assert _session_audit(db, session_id).count() == before[session_id] + 1
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


def _session_id(user_id):
    with SessionLocal() as db:
        return db.query(models.SesionUsuario.id_sesion).filter_by(id_usuario=user_id).one()[0]


def _session_audit(db, session_id):
    return db.query(models.Bitacora).filter_by(entidad_tipo="sesion_usuario", entidad_id=session_id)


def test_authenticated_requests_update_activity_without_audit_noise(api):
    target, password = _create_user(api)
    client, _ = _login(target["correo"], password)
    session_id = _session_id(target["id_usuario"])
    with SessionLocal() as db:
        previous = db.get(models.SesionUsuario, session_id).ultima_actividad
        history = [(row.id_bitacora, row.valor_anterior, row.valor_nuevo) for row in _session_audit(db, session_id)]
        total_before = db.query(models.Bitacora).count()
        events_before = db.query(models.EventoAcceso).filter_by(id_sesion=session_id).count()
    for _ in range(5):
        response = client.get("/api/auth/sesion")
        assert response.status_code == 200, response.text
        with SessionLocal() as db:
            current = db.get(models.SesionUsuario, session_id).ultima_actividad
            assert current > previous
            previous = current
            assert [(row.id_bitacora, row.valor_anterior, row.valor_nuevo) for row in _session_audit(db, session_id)] == history
            assert db.query(models.Bitacora).count() == total_before
            assert db.query(models.EventoAcceso).filter_by(id_sesion=session_id).count() == events_before


def test_activity_update_requires_actor(api):
    target, password = _create_user(api)
    _login(target["correo"], password)
    session_id = _session_id(target["id_usuario"])
    with SessionLocal() as db:
        session = db.get(models.SesionUsuario, session_id)
        previous = session.ultima_actividad
        db.execute(text("SELECT set_config('app.current_user_id', '', true)"))
        session.ultima_actividad += timedelta(seconds=1)
        with pytest.raises(DBAPIError, match="app.current_user_id"):
            db.commit()
        db.rollback()
        assert db.get(models.SesionUsuario, session_id).ultima_actividad == previous


@pytest.mark.parametrize("field", ["expira_en", "user_agent_creacion", "token_hash", "csrf_hash", "revocada_en"])
def test_activity_with_simultaneous_changes_is_audited_and_redacted(api, field):
    target, password = _create_user(api)
    _login(target["correo"], password)
    session_id = _session_id(target["id_usuario"])
    with SessionLocal() as db:
        before = _session_audit(db, session_id).count()
        session = db.get(models.SesionUsuario, session_id)
        set_audit_context(db, target["id_usuario"])
        session.ultima_actividad += timedelta(seconds=1)
        value = session.expira_en + timedelta(minutes=1) if field == "expira_en" else uuid.uuid4().hex * 2
        if field == "revocada_en":
            value = datetime.now(timezone.utc)
            session.id_usuario_revoca = target["id_usuario"]
            session.motivo_revocacion = "revocacion_admin"
        setattr(session, field, value)
        db.commit()
        assert _session_audit(db, session_id).count() == before + 1
        row = _session_audit(db, session_id).order_by(models.Bitacora.id_bitacora.desc()).first()
        assert row.accion == "update" and row.id_usuario == target["id_usuario"]
        assert row.valor_anterior["ultima_actividad"] != row.valor_nuevo["ultima_actividad"]
        for payload in (row.valor_anterior, row.valor_nuevo):
            assert not {"token_hash", "csrf_hash", "contrasena_hash"} & payload.keys()
        if field not in {"token_hash", "csrf_hash"}:
            assert row.valor_anterior[field] != row.valor_nuevo[field]


@pytest.mark.parametrize("reason", ["expiracion_inactividad", "expiracion_absoluta"])
def test_expiration_keeps_correlated_system_event_without_session_audit(api, monkeypatch, reason):
    target, password = _create_user(api)
    client, _ = _login(target["correo"], password)
    session_id = _session_id(target["id_usuario"])
    with SessionLocal() as db:
        session = db.get(models.SesionUsuario, session_id)
        future = (session.expira_en + timedelta(seconds=1) if reason == "expiracion_absoluta"
                  else session.ultima_actividad + timedelta(minutes=AUTH_SETTINGS.inactivity_minutes, seconds=1))
        before = _session_audit(db, session_id).count()
    monkeypatch.setattr(authentication, "_utcnow", lambda: future)
    assert client.get("/api/auth/sesion").status_code == 401
    assert client.get("/api/auth/sesion").status_code == 401
    with SessionLocal() as db:
        session = db.get(models.SesionUsuario, session_id)
        assert session.revocada_en == future and session.id_usuario_revoca is None
        assert session.motivo_revocacion == reason
        assert _session_audit(db, session_id).count() == before
        event = db.query(models.EventoAcceso).filter_by(id_sesion=session_id, tipo_evento="sesion_expirada").one()
        assert event.motivo_codigo == reason and event.id_usuario_actor is None


def test_logout_keeps_session_audit_and_access_event(api):
    target, password = _create_user(api)
    client, headers = _login(target["correo"], password)
    session_id = _session_id(target["id_usuario"])
    with SessionLocal() as db:
        before = _session_audit(db, session_id).count()
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/sesion").status_code == 401
    with SessionLocal() as db:
        assert _session_audit(db, session_id).count() == before + 1
        assert db.get(models.SesionUsuario, session_id).revocada_en is not None
        event = db.query(models.EventoAcceso).filter_by(id_sesion=session_id, tipo_evento="logout").one()
        assert event.id_usuario_actor == target["id_usuario"]


@pytest.mark.parametrize("invalid", ["previous_transaction", "session", "actor", "event_type", "reason", "activity", "secret", "heartbeat_only"])
def test_system_expiration_validation_cannot_bypass_audit(api, invalid):
    target, password = _create_user(api)
    _login(target["correo"], password)
    session_id = _session_id(target["id_usuario"])
    with SessionLocal() as db:
        session = db.get(models.SesionUsuario, session_id)
        activity = session.ultima_actividad
        before = _session_audit(db, session_id).count()
        event = models.EventoAcceso(
            id_usuario=target["id_usuario"],
            id_sesion=None if invalid == "session" else session_id,
            id_usuario_actor=target["id_usuario"] if invalid == "actor" else None,
            tipo_evento="login_exitoso" if invalid == "event_type" else "sesion_expirada",
            motivo_codigo="expiracion_absoluta" if invalid == "reason" else "expiracion_inactividad",
        )
        db.add(event)
        db.flush()
        event_id = event.id_evento
        if invalid == "previous_transaction":
            db.commit()
        db.execute(text("SELECT set_config('app.auth_system_event_id', :event, true)"), {"event": str(event_id)})
        # Even a valid actor must not bypass the dedicated system-event checks.
        set_audit_context(db, target["id_usuario"])
        if invalid == "heartbeat_only":
            session.ultima_actividad += timedelta(seconds=1)
        else:
            session.revocada_en = datetime.now(timezone.utc)
            session.motivo_revocacion = "expiracion_inactividad"
            if invalid == "activity":
                session.ultima_actividad += timedelta(seconds=1)
            if invalid == "secret":
                session.csrf_hash = uuid.uuid4().hex * 2
        with pytest.raises(DBAPIError, match="Expiración de sesión sin evento de sistema"):
            db.commit()
        db.rollback()
        session = db.get(models.SesionUsuario, session_id)
        assert session.revocada_en is None and session.ultima_actividad == activity
        assert _session_audit(db, session_id).count() == before
