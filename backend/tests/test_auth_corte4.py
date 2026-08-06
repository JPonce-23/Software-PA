from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app import models
from app.config import AUTH_SETTINGS
from app.database import SessionLocal
from app.main import app
from app.services import authentication as auth_service


ORIGIN = AUTH_SETTINGS.allowed_origins[0]
TEST_PASSWORD = "PruebaAuth!2026"


@pytest.fixture
def auth_user(client, admin_session):
    email = f"auth-corte4-{uuid4().hex}@pa.test"
    response = client.post(
        "/api/usuarios",
        headers=admin_session,
        json={
            "nombre": "Prueba",
            "apellido_paterno": "Autenticacion",
            "correo": email,
            "rol": "visualizador",
            "contrasena": TEST_PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    user = response.json()
    yield {"id_usuario": user["id_usuario"], "email": email}
    client.delete(
        f"/api/usuarios/{user['id_usuario']}?motivo=Limpieza de prueba Corte 4",
        headers=admin_session,
    )


def _session_login(browser: TestClient, email: str, password: str):
    return browser.post(
        "/api/auth/sesiones",
        data={"username": email, "password": password},
        headers={"Origin": ORIGIN},
    )


def _csrf_headers(browser: TestClient) -> dict[str, str]:
    csrf = browser.cookies.get(AUTH_SETTINGS.csrf_cookie_name)
    assert csrf
    return {"Origin": ORIGIN, "X-CSRF-Token": csrf}


def test_cookie_session_csrf_logout_and_redaction(auth_user):
    with TestClient(app, raise_server_exceptions=False) as browser:
        login = _session_login(browser, auth_user["email"], TEST_PASSWORD)
        assert login.status_code == 200, login.text
        assert "access_token" not in login.json()
        assert login.json()["user"]["id_usuario"] == auth_user["id_usuario"]
        set_cookie = login.headers.get("set-cookie", "")
        assert "HttpOnly" in set_cookie
        assert "SameSite=lax" in set_cookie
        assert browser.cookies.get(AUTH_SETTINGS.session_cookie_name)

        current = browser.get("/api/auth/sesion")
        assert current.status_code == 200
        assert current.json()["user"]["correo"] == auth_user["email"]

        rejected = browser.post("/api/auth/logout", headers={"Origin": ORIGIN})
        assert rejected.status_code == 403

        logout = browser.post("/api/auth/logout", headers=_csrf_headers(browser))
        assert logout.status_code == 200
        assert browser.get("/api/auth/sesion").status_code == 401

    db = SessionLocal()
    try:
        leaked = db.execute(
            text(
                """
                SELECT COUNT(*)
                  FROM bitacora
                 WHERE entidad_tipo = 'sesion_usuario'
                   AND (
                       COALESCE(valor_anterior, '{}'::jsonb)
                           ?| ARRAY['token_hash', 'csrf_hash']
                       OR COALESCE(valor_nuevo, '{}'::jsonb)
                           ?| ARRAY['token_hash', 'csrf_hash']
                   )
                """
            )
        ).scalar_one()
        assert leaked == 0
    finally:
        db.close()


def test_quinto_fallo_concurrente_bloquea_y_admin_desbloquea(
    auth_user,
    client,
    admin_session,
):
    def fail_login(_):
        with TestClient(app, raise_server_exceptions=False) as browser:
            return _session_login(
                browser, auth_user["email"], "ClaveIncorrecta!2026"
            ).status_code

    with ThreadPoolExecutor(max_workers=5) as executor:
        statuses = list(executor.map(fail_login, range(5)))
    assert statuses == [401] * 5

    db = SessionLocal()
    try:
        state = db.get(models.EstadoAutenticacionUsuario, auth_user["id_usuario"])
        assert state.intentos_fallidos == 5
        assert state.bloqueado_hasta is not None
        blocked_events = (
            db.query(models.EventoAcceso)
            .filter(
                models.EventoAcceso.id_usuario == auth_user["id_usuario"],
                models.EventoAcceso.tipo_evento == "cuenta_bloqueada",
                models.EventoAcceso.motivo_codigo == "quinto_fallo",
            )
            .count()
        )
        assert blocked_events == 1
    finally:
        db.close()

    with TestClient(app, raise_server_exceptions=False) as browser:
        assert _session_login(browser, auth_user["email"], TEST_PASSWORD).status_code == 401

    unlocked = client.post(
        f"/api/usuarios/{auth_user['id_usuario']}/desbloquear",
        headers=admin_session,
        json={"motivo": "Recuperación controlada en prueba"},
    )
    assert unlocked.status_code == 200, unlocked.text

    with TestClient(app, raise_server_exceptions=False) as browser:
        login = _session_login(browser, auth_user["email"], TEST_PASSWORD)
        assert login.status_code == 200, login.text
        browser.post("/api/auth/logout", headers=_csrf_headers(browser))


def test_postgresql_rechaza_estado_sin_evento(auth_user):
    db = SessionLocal()
    try:
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    """
                    UPDATE estado_autenticacion_usuario
                       SET intentos_fallidos = 1,
                           bloqueado_hasta = NULL,
                           actualizado_en = NOW()
                     WHERE id_usuario = :id_usuario
                    """
                ),
                {"id_usuario": auth_user["id_usuario"]},
            )
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_postgresql_rechaza_cambios_colaterales_en_expiracion(auth_user):
    with TestClient(app, raise_server_exceptions=False) as browser:
        login = _session_login(browser, auth_user["email"], TEST_PASSWORD)
        assert login.status_code == 200, login.text

    db = SessionLocal()
    try:
        session = (
            db.query(models.SesionUsuario)
            .filter(
                models.SesionUsuario.id_usuario == auth_user["id_usuario"],
                models.SesionUsuario.revocada_en.is_(None),
            )
            .order_by(models.SesionUsuario.id_sesion.desc())
            .first()
        )
        event_id = db.execute(
            text(
                """
                INSERT INTO evento_acceso (
                    id_usuario, id_sesion, tipo_evento, motivo_codigo
                ) VALUES (
                    :id_usuario, :id_sesion,
                    'sesion_expirada', 'expiracion_inactividad'
                )
                RETURNING id_evento
                """
            ),
            {
                "id_usuario": auth_user["id_usuario"],
                "id_sesion": session.id_sesion,
            },
        ).scalar_one()
        db.execute(
            text("SELECT set_config('app.auth_system_event_id', :event_id, true)"),
            {"event_id": str(event_id)},
        )
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    """
                    UPDATE sesion_usuario
                       SET revocada_en = NOW(),
                           motivo_revocacion = 'expiracion_inactividad',
                           token_hash = :token_hash
                     WHERE id_sesion = :id_sesion
                    """
                ),
                {
                    "id_sesion": session.id_sesion,
                    "token_hash": "a" * 64,
                },
            )
            db.commit()
    finally:
        db.rollback()
        db.close()


@pytest.mark.parametrize(
    ("elapsed", "reason"),
    [
        (timedelta(minutes=31), "expiracion_inactividad"),
        (timedelta(minutes=481), "expiracion_absoluta"),
    ],
)
def test_expiracion_servidor(auth_user, monkeypatch, elapsed, reason):
    with TestClient(app, raise_server_exceptions=False) as browser:
        login = _session_login(browser, auth_user["email"], TEST_PASSWORD)
        assert login.status_code == 200, login.text

        db = SessionLocal()
        try:
            session = (
                db.query(models.SesionUsuario)
                .filter(
                    models.SesionUsuario.id_usuario == auth_user["id_usuario"],
                    models.SesionUsuario.revocada_en.is_(None),
                )
                .order_by(models.SesionUsuario.id_sesion.desc())
                .first()
            )
            session_id = session.id_sesion
            audit_count_before = db.execute(
                text(
                    """
                    SELECT COUNT(*)
                      FROM bitacora
                     WHERE entidad_tipo = 'sesion_usuario'
                       AND entidad_id = :session_id
                    """
                ),
                {"session_id": session_id},
            ).scalar_one()
            future = session.fecha_creacion + elapsed
        finally:
            db.close()

        monkeypatch.setattr(auth_service, "_utcnow", lambda: future)
        assert browser.get("/api/auth/sesion").status_code == 401

    db = SessionLocal()
    try:
        event = (
            db.query(models.EventoAcceso)
            .filter(
                models.EventoAcceso.id_usuario == auth_user["id_usuario"],
                models.EventoAcceso.motivo_codigo == reason,
            )
            .order_by(models.EventoAcceso.id_evento.desc())
            .first()
        )
        assert event is not None
        assert event.id_sesion == session_id
        assert event.id_usuario_actor is None
        audit_count_after = db.execute(
            text(
                """
                SELECT COUNT(*)
                  FROM bitacora
                 WHERE entidad_tipo = 'sesion_usuario'
                   AND entidad_id = :session_id
                """
            ),
            {"session_id": session_id},
        ).scalar_one()
        assert audit_count_after == audit_count_before
    finally:
        db.close()


def test_login_identidad_inexistente_no_guarda_identificador():
    with TestClient(app, raise_server_exceptions=False) as browser:
        response = _session_login(
            browser,
            f"inexistente-{uuid4().hex}@pa.test",
            "ClaveIncorrecta!2026",
        )
        assert response.status_code == 401

    db = SessionLocal()
    try:
        event = (
            db.query(models.EventoAcceso)
            .filter(
                models.EventoAcceso.tipo_evento == "login_fallido",
                models.EventoAcceso.id_usuario.is_(None),
            )
            .order_by(models.EventoAcceso.id_evento.desc())
            .first()
        )
        assert event is not None
        columns = {
            row[0]
            for row in db.execute(
                text(
                    """
                    SELECT column_name
                      FROM information_schema.columns
                     WHERE table_schema = 'public'
                       AND table_name = 'evento_acceso'
                    """
                )
            )
        }
        assert "identificador_hash" not in columns
        assert "correo" not in columns
    finally:
        db.close()
