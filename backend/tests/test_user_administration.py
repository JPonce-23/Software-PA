"""Integration coverage for secure user administration endpoints."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func

from app.config import AUTH_SETTINGS
from app.database import SessionLocal
from app.main import app
from app import models


def _password() -> str:
    return f"Qa1!{uuid.uuid4().hex}Z"


def _create_user(api, *, role: str = "operador") -> tuple[dict, str]:
    password = _password()
    record = api(
        "POST",
        "/api/usuarios",
        expected=201,
        json={
            "nombre": "Usuario",
            "apellido_paterno": "Prueba",
            "correo": f"usuarios-{uuid.uuid4().hex[:16]}@qa.local",
            "rol": role,
            "contrasena": password,
        },
    ).json()
    return record, password


def _login(email: str, password: str) -> tuple[TestClient, dict[str, str]]:
    client = TestClient(app, raise_server_exceptions=False)
    origin = AUTH_SETTINGS.allowed_origins[0]
    response = client.post(
        "/api/auth/sesiones",
        data={"username": email, "password": password},
        headers={"Origin": origin},
    )
    assert response.status_code == 200, response.text
    return client, {
        "Origin": origin,
        "X-CSRF-Token": client.cookies.get(AUTH_SETTINGS.csrf_cookie_name),
    }


def _block(email: str) -> None:
    origin = AUTH_SETTINGS.allowed_origins[0]
    for _ in range(5):
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/auth/sesiones",
            data={"username": email, "password": "contraseña incorrecta"},
            headers={"Origin": origin},
        )
        assert response.status_code == 401, response.text


def _list_offset(user_id: int, *, activo: bool | None) -> int:
    """Return the endpoint-order offset for a user in a populated QA database."""
    with SessionLocal() as db:
        user = db.get(models.Usuario, user_id)
        query = db.query(func.count(models.Usuario.id_usuario)).filter(
            models.Usuario.correo < user.correo
        )
        if activo is not None:
            query = query.filter(models.Usuario.activo.is_(activo))
        return query.scalar()


def test_user_patch_restricts_fields_and_preserves_secrets(api):
    user, _ = _create_user(api)
    changed = api(
        "PATCH",
        f"/api/usuarios/{user['id_usuario']}",
        json={
            "nombre": "Nuevo",
            "apellido_paterno": "Paterno",
            "apellido_materno": "Materno",
            "rol": "visualizador",
        },
    ).json()
    assert (changed["nombre"], changed["apellido_paterno"], changed["rol"]) == (
        "Nuevo",
        "Paterno",
        "visualizador",
    )
    for forbidden in ("correo", "contrasena"):
        response = api(
            "PATCH",
            f"/api/usuarios/{user['id_usuario']}",
            expected=422,
            json={forbidden: "no-permitido@example.local"},
        )
        assert response.status_code == 422
    assert not ({"contrasena_hash", "token_hash", "csrf_hash"} & changed.keys())


def test_cannot_demote_the_last_active_admin(client, api):
    current = client.get("/api/auth/sesion")
    assert current.status_code == 200, current.text
    current_id = current.json()["user"]["id_usuario"]
    with SessionLocal() as db:
        active_admins = db.query(models.Usuario).filter(
            models.Usuario.rol == "admin", models.Usuario.activo.is_(True)
        ).count()
    if active_admins != 1:
        pytest.skip("La base aislada tiene más de un administrador activo")
    assert api(
        "PATCH",
        f"/api/usuarios/{current_id}",
        expected=409,
        json={"rol": "operador"},
    ).status_code == 409


def test_user_list_filters_exposes_auth_state_and_requires_admin(api):
    active, active_password = _create_user(api)
    inactive, _ = _create_user(api)
    api(
        "DELETE",
        f"/api/usuarios/{inactive['id_usuario']}",
        json={"motivo": "Prueba de listado inactivo"},
    )
    _block(active["correo"])

    # Keep the default active-only contract and target exact rows beyond page 1.
    assert all(row["activo"] for row in api("GET", "/api/usuarios?limit=1").json())
    active_rows = api(
        "GET",
        f"/api/usuarios?estado=activos&skip={_list_offset(active['id_usuario'], activo=True)}&limit=1",
    ).json()
    inactive_rows = api(
        "GET",
        f"/api/usuarios?estado=inactivos&skip={_list_offset(inactive['id_usuario'], activo=False)}&limit=1",
    ).json()
    all_rows = api(
        "GET",
        f"/api/usuarios?estado=todos&skip={_list_offset(active['id_usuario'], activo=None)}&limit=1",
    ).json()
    active_row = active_rows[0]
    assert active_row["bloqueado"] is True
    assert active_row["bloqueado_hasta"] is not None
    assert active["id_usuario"] not in {row["id_usuario"] for row in inactive_rows}
    assert inactive["id_usuario"] == inactive_rows[0]["id_usuario"]
    assert active["id_usuario"] == all_rows[0]["id_usuario"]
    assert api("GET", "/api/usuarios?estado=otro", expected=422).status_code == 422
    assert not ({"contrasena_hash", "token_hash", "csrf_hash"} & active_row.keys())

    # A non-admin session cannot list or administratively alter users.
    blocked_client = TestClient(app, raise_server_exceptions=False)
    assert blocked_client.post(
        "/api/auth/sesiones",
        data={"username": active["correo"], "password": active_password},
        headers={"Origin": AUTH_SETTINGS.allowed_origins[0]},
    ).status_code == 401
    api(
        "POST",
        f"/api/usuarios/{active['id_usuario']}/desbloquear",
        json={"motivo": "Permitir prueba de autorización"},
    )
    client, headers = _login(active["correo"], active_password)
    assert client.get("/api/usuarios", headers=headers).status_code == 403
    assert client.patch(
        f"/api/usuarios/{active['id_usuario']}",
        headers=headers,
        json={"rol": "admin"},
    ).status_code == 403


def test_reactivate_preserves_project_revocation_and_auth_lock(api):
    user, password = _create_user(api)
    project = api(
        "POST",
        "/api/proyectos",
        expected=201,
        json={
            "clave_proyecto": f"REACT-{uuid.uuid4().hex[:10]}",
            "nombre_proyecto": "Proyecto para reactivación QA",
        },
    ).json()
    api(
        "POST",
        f"/api/proyectos/{project['id_proyecto']}/usuarios",
        expected=201,
        json={"id_usuario": user["id_usuario"]},
    )
    _block(user["correo"])
    api(
        "DELETE",
        f"/api/usuarios/{user['id_usuario']}",
        json={"motivo": "Baja para probar reactivación"},
    )
    with SessionLocal() as db:
        state_before = db.get(models.EstadoAutenticacionUsuario, user["id_usuario"])
        auth_state_before = (
            state_before.intentos_fallidos,
            state_before.bloqueado_hasta,
            state_before.ultimo_acceso_en,
        )
        assert db.query(models.SesionUsuario).filter(
            models.SesionUsuario.id_usuario == user["id_usuario"]
        ).count() == 0

    response = api(
        "POST",
        f"/api/usuarios/{user['id_usuario']}/reactivar",
        json={"motivo": "  Reactivar sin restaurar autorizaciones  "},
    )
    assert response.json()["detail"] == "Usuario reactivado"
    assert api(
        "POST",
        f"/api/usuarios/{user['id_usuario']}/reactivar",
        expected=409,
        json={"motivo": "No debe reactivarse dos veces"},
    ).status_code == 409
    assert api(
        "POST",
        "/api/usuarios/999999999/reactivar",
        expected=404,
        json={"motivo": "Usuario inexistente"},
    ).status_code == 404

    with SessionLocal() as db:
        assignment = db.query(models.UsuarioProyecto).filter(
            models.UsuarioProyecto.id_usuario == user["id_usuario"],
            models.UsuarioProyecto.id_proyecto == project["id_proyecto"],
        ).one()
        state = db.get(models.EstadoAutenticacionUsuario, user["id_usuario"])
        target = db.get(models.Usuario, user["id_usuario"])
        assert assignment.activo is False
        assert (
            state.intentos_fallidos,
            state.bloqueado_hasta,
            state.ultimo_acceso_en,
        ) == auth_state_before
        assert db.query(models.SesionUsuario).filter(
            models.SesionUsuario.id_usuario == user["id_usuario"]
        ).count() == 0
        assert target.fecha_baja is not None
        assert target.motivo_baja == "Baja para probar reactivación"
        assert target.fecha_reactivacion is not None
        assert target.motivo_reactivacion == "Reactivar sin restaurar autorizaciones"

    # Reactivation does not create a session or remove the existing lock.
    client = TestClient(app, raise_server_exceptions=False)
    assert client.post(
        "/api/auth/sesiones",
        data={"username": user["correo"], "password": password},
        headers={"Origin": AUTH_SETTINGS.allowed_origins[0]},
    ).status_code == 401
    assert api(
        "POST",
        "/api/usuarios/999999999/reactivar",
        expected=422,
        json={"motivo": "Motivo válido", "campo_extra": True},
    ).status_code == 422


def test_unlock_and_revoke_sessions_record_events(api):
    locked, _ = _create_user(api)
    _block(locked["correo"])
    api(
        "DELETE",
        f"/api/usuarios/{locked['id_usuario']}",
        json={"motivo": "Baja antes de desbloqueo QA"},
    )
    assert api(
        "POST",
        f"/api/usuarios/{locked['id_usuario']}/desbloquear",
        json={"motivo": "Desbloqueo administrativo QA"},
    ).status_code == 200
    assert api(
        "POST",
        f"/api/usuarios/{locked['id_usuario']}/desbloquear",
        expected=409,
        json={"motivo": "No hay bloqueo vigente"},
    ).status_code == 409
    assert api(
        "POST",
        "/api/usuarios/999999999/desbloquear",
        expected=404,
        json={"motivo": "Usuario inexistente"},
    ).status_code == 404
    with SessionLocal() as db:
        assert db.get(models.Usuario, locked["id_usuario"]).activo is False

    target, password = _create_user(api)
    _login(target["correo"], password)
    _login(target["correo"], password)
    revoked = api(
        "POST",
        f"/api/usuarios/{target['id_usuario']}/revocar-sesiones",
        json={"motivo": "Revocación administrativa QA"},
    ).json()
    assert revoked == {"detail": "Sesiones revocadas", "sesiones_revocadas": 2}
    empty, _ = _create_user(api)
    assert api(
        "POST",
        f"/api/usuarios/{empty['id_usuario']}/revocar-sesiones",
        json={"motivo": "Sin sesiones activas QA"},
    ).json()["sesiones_revocadas"] == 0
    assert api(
        "POST",
        "/api/usuarios/999999999/revocar-sesiones",
        expected=404,
        json={"motivo": "Usuario inexistente"},
    ).status_code == 404

    with SessionLocal() as db:
        sessions = db.query(models.SesionUsuario).filter(
            models.SesionUsuario.id_usuario == target["id_usuario"]
        ).all()
        assert len(sessions) == 2
        assert all(session.revocada_en and session.id_usuario_revoca for session in sessions)
        events = db.query(models.EventoAcceso).filter(
            models.EventoAcceso.id_usuario.in_(
                [locked["id_usuario"], target["id_usuario"], empty["id_usuario"]]
            )
        ).all()
        assert any(
            event.tipo_evento == "desbloqueo"
            and event.motivo_codigo == "desbloqueo_admin"
            for event in events
        )
        assert sum(
            event.tipo_evento == "sesion_revocada"
            and event.id_usuario == target["id_usuario"]
            for event in events
        ) == 2
        assert any(
            event.tipo_evento == "sesion_revocada"
            and event.id_usuario == empty["id_usuario"]
            and event.motivo_codigo == "revocacion_admin"
            for event in events
        )
