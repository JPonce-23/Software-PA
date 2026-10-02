"""Project authorization lifecycle against isolated PostgreSQL and real sessions."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import models
from app.config import AUTH_SETTINGS
from app.database import SessionLocal, engine
from app.main import app
from app.services.common import mark_inactive, set_audit_context
from .test_user_administration import _create_user, _login
from .conftest import unique
from .test_excel_closure_002 import _isolated_pn
from .concurrency import PostgreSQLWorkers, wait_for_blocked_workers


REASON = "Reasignación administrativa de personal"


def _project(api):
    return api(
        "POST", "/api/proyectos", expected=201,
        json={"clave_proyecto": unique("ASIG"), "nombre_proyecto": unique("Asignaciones QA")},
    ).json()["id_proyecto"]


def _assign(api, project_id, user_id, *, expected=201):
    return api(
        "POST", f"/api/proyectos/{project_id}/usuarios", expected=expected,
        json={"id_usuario": user_id},
    )


def _remove(api, project_id, user_id, *, expected=200, reason=REASON):
    return api(
        "DELETE", f"/api/proyectos/{project_id}/usuarios/{user_id}", expected=expected,
        json={"motivo": reason},
    )


def _snapshot(assignment_id):
    with SessionLocal() as db:
        assignment = db.get(models.UsuarioProyecto, assignment_id)
        return {column.name: getattr(assignment, column.name)
                for column in models.UsuarioProyecto.__table__.columns}


def _audit(assignment_id):
    with SessionLocal() as db:
        return [
            {column.name: getattr(row, column.name) for column in models.Bitacora.__table__.columns}
            for row in db.query(models.Bitacora).filter(
                models.Bitacora.entidad_tipo == "usuario_proyecto",
                models.Bitacora.entidad_id == assignment_id,
            ).order_by(models.Bitacora.id_bitacora).all()
        ]


def test_lifecycle_preserves_history_audit_other_assignments_and_sessions(api, client):
    user, password = _create_user(api)
    other_user, _ = _create_user(api)
    user_id = user["id_usuario"]
    project_id, other_project = _project(api), _project(api)
    original = _assign(api, project_id, user_id).json()
    assignment_id = original["id_usuario_proyecto"]
    other = _assign(api, other_project, user_id).json()["id_usuario_proyecto"]
    neighbor = _assign(api, project_id, other_user["id_usuario"]).json()["id_usuario_proyecto"]
    other_before, neighbor_before = _snapshot(other), _snapshot(neighbor)
    before = _snapshot(assignment_id)
    actor = client.get("/api/auth/sesion").json()["user"]["id_usuario"]
    session, _ = _login(user["correo"], password)
    try:
        listed = api("GET", f"/api/proyectos/{project_id}/usuarios").json()
        assert {row["id_usuario"] for row in listed} == {user_id, other_user["id_usuario"]}
        _assign(api, project_id, user_id, expected=409)
        with SessionLocal() as db:
            sessions_before = db.query(models.SesionUsuario).filter(
                models.SesionUsuario.id_usuario == user_id,
            ).all()
            session_state = [(s.id_sesion, s.revocada_en, s.id_usuario_revoca) for s in sessions_before]

        assert _remove(api, project_id, user_id, reason=f"  {REASON}  ").json() == {
            "detail": "Asignación desactivada"
        }
        after = _snapshot(assignment_id)
        assert after["activo"] is False
        assert after["motivo_baja"] == REASON
        assert after["id_usuario_baja"] == after["actualizado_por"] == actor
        assert after["fecha_baja"] == after["actualizado_en"] is not None
        assert after["fecha_asignacion"] == before["fecha_asignacion"]
        assert after["creado_en"] == before["creado_en"]
        assert user_id not in {row["id_usuario"] for row in api(
            "GET", f"/api/proyectos/{project_id}/usuarios"
        ).json()}
        assert _snapshot(other) == other_before
        assert _snapshot(neighbor) == neighbor_before
        assert session.get(f"/api/proyectos/{project_id}").status_code == 403
        assert session.get(f"/api/proyectos/{other_project}").status_code == 200
        assert session.get("/api/auth/sesion").status_code == 200
        with SessionLocal() as db:
            target = db.get(models.Usuario, user_id)
            assert target.activo and target.rol == "operador"
            assert [(s.id_sesion, s.revocada_en, s.id_usuario_revoca) for s in db.query(
                models.SesionUsuario
            ).filter(models.SesionUsuario.id_usuario == user_id).all()] == session_state

        audit = _audit(assignment_id)
        assert [row["accion"] for row in audit] == ["insert", "update"]
        update = audit[-1]
        assert update["id_usuario"] == actor
        assert update["id_proyecto"] == project_id
        assert update["valor_anterior"]["activo"] is True
        assert update["valor_anterior"]["fecha_baja"] is None
        assert update["valor_nuevo"]["activo"] is False
        assert update["valor_nuevo"]["motivo_baja"] == REASON
        assert update["valor_nuevo"]["actualizado_por"] == actor
        assert update["valor_nuevo"]["id_usuario_baja"] == actor
        assert update["valor_nuevo"]["fecha_baja"] is not None

        with SessionLocal() as db:
            audit_count = db.query(models.Bitacora).count()
        _remove(api, project_id, user_id, expected=404, reason="Segundo intento administrativo")
        assert _snapshot(assignment_id) == after
        assert _audit(assignment_id) == audit
        with SessionLocal() as db:
            assert db.query(models.Bitacora).count() == audit_count
        new = _assign(api, project_id, user_id).json()
        assert new["id_usuario_proyecto"] != assignment_id
        assert new["activo"] is True and new["fecha_baja"] is None
        assert _snapshot(assignment_id) == after
        assert _audit(assignment_id) == audit
        _assign(api, project_id, user_id, expected=409)
        with SessionLocal() as db:
            rows = db.query(models.UsuarioProyecto).filter(
                models.UsuarioProyecto.id_usuario == user_id,
                models.UsuarioProyecto.id_proyecto == project_id,
            ).all()
            assert len(rows) == 2 and sum(row.activo for row in rows) == 1
        assert session.get(f"/api/proyectos/{project_id}").status_code == 200
    finally:
        session.close()


@pytest.mark.parametrize("role", ["operador", "visualizador", "geografo"])
def test_backend_revokes_project_and_nucleus_access_and_preserves_role(api, target_domain, role):
    user, password = _create_user(api, role=role)
    project, pn = _isolated_pn(api, target_domain)
    project_id = project["id_proyecto"]
    pn_id = pn["id_proyecto_nucleo"]
    user_id = user["id_usuario"]
    _assign(api, project_id, user_id)
    session, headers = _login(user["correo"], password)
    reads = [f"/api/proyectos/{project_id}", f"/api/proyectos/{project_id}/nucleos",
             f"/api/proyecto-nucleo/{pn_id}", f"/api/proyecto-nucleo/{pn_id}/actividades"]
    capture_path = f"/api/proyecto-nucleo/{pn_id}/actividades"
    capture_payload = {"tipo_actividad": "caminamiento", "contexto_actividad": "general",
                       "fecha_realizada": "2026-04-01", "resultado": unique("Captura QA")}
    gis_path = f"/api/nucleos/{pn['id_nucleo']}/geometria"
    gis_payload = {"geometria_wkt": "MULTIPOLYGON(((-100 20,-99.9 20,-99.9 20.1,-100 20.1,-100 20)))",
                   "fuente_geometria": "QA asignaciones", "fecha_fuente_geometria": "2026-01-01"}
    try:
        for path in reads:
            assert session.get(path).status_code == 200, path
        assert [row["id_proyecto"] for row in session.get("/api/proyectos?limit=1").json()] == [project_id]
        for method, path, payload in [
            ("GET", f"/api/proyectos/{project_id}/usuarios", None),
            ("POST", f"/api/proyectos/{project_id}/usuarios", {"id_usuario": user_id}),
            ("DELETE", f"/api/proyectos/{project_id}/usuarios/{user_id}", {"motivo": REASON}),
        ]:
            kwargs = {"headers": headers}
            if payload is not None:
                kwargs["json"] = payload
            assert session.request(method, path, **kwargs).status_code == 403
        assert session.post(capture_path, headers=headers, json=capture_payload).status_code == (
            201 if role == "operador" else 403
        )
        assert session.patch(gis_path, headers=headers, json=gis_payload).status_code == (
            200 if role == "geografo" else 403
        )
        _remove(api, project_id, user_id)
        assert session.get("/api/proyectos?limit=1").json() == []
        for path in reads:
            assert session.get(path).status_code == 403, path
        assert session.post(capture_path, headers=headers, json=capture_payload).status_code == 403
        assert session.patch(gis_path, headers=headers, json=gis_payload).status_code == 403
        _assign(api, project_id, user_id)
        for path in reads:
            assert session.get(path).status_code == 200, path
        capture_payload["resultado"] = unique("Captura tras reasignación QA")
        assert session.post(capture_path, headers=headers, json=capture_payload).status_code == (
            201 if role == "operador" else 403
        )
        assert session.patch(gis_path, headers=headers, json=gis_payload).status_code == (
            200 if role == "geografo" else 403
        )
    finally:
        session.close()


@pytest.mark.parametrize("payload", [{}, {"motivo": ""}, {"motivo": "   "},
                                    {"motivo": "ab"}, {"motivo": " a "}, {"motivo": "x" * 501}, None])
def test_invalid_reason_does_not_change_assignment(api, payload):
    user, _ = _create_user(api)
    project_id = _project(api)
    assignment_id = _assign(api, project_id, user["id_usuario"]).json()["id_usuario_proyecto"]
    before, audit = _snapshot(assignment_id), _audit(assignment_id)
    api("DELETE", f"/api/proyectos/{project_id}/usuarios/{user['id_usuario']}",
        expected=422, json=payload)
    assert _snapshot(assignment_id) == before
    assert _audit(assignment_id) == audit


def test_authentication_csrf_and_missing_resources(api, client, admin_headers):
    user, _ = _create_user(api)
    project_id = _project(api)
    user_id = user["id_usuario"]
    assignment_id = _assign(api, project_id, user_id).json()["id_usuario_proyecto"]
    before, audit = _snapshot(assignment_id), _audit(assignment_id)
    path = f"/api/proyectos/{project_id}/usuarios/{user_id}"
    with TestClient(app, raise_server_exceptions=False) as anonymous:
        for method, url, payload in [
            ("GET", f"/api/proyectos/{project_id}/usuarios", None),
            ("POST", f"/api/proyectos/{project_id}/usuarios", {"id_usuario": user_id}),
            ("DELETE", path, {"motivo": REASON}),
        ]:
            kwargs = {"headers": {"Origin": AUTH_SETTINGS.allowed_origins[0]}}
            if payload is not None:
                kwargs["json"] = payload
            assert anonymous.request(method, url, **kwargs).status_code == 401
    assert client.request("DELETE", path, headers={**admin_headers, "X-CSRF-Token": "invalid"},
                          json={"motivo": REASON}).status_code == 403
    assert client.request("DELETE", path, headers={"Origin": admin_headers["Origin"]},
                          json={"motivo": REASON}).status_code == 403
    assert _snapshot(assignment_id) == before and _audit(assignment_id) == audit
    assert _remove(api, project_id, 999999999, expected=404).json()["detail"] == "Usuario no encontrado"
    assert _remove(api, 999999999, user_id, expected=403).json()["detail"] == "Proyecto fuera del alcance autorizado"
    other_project = _project(api)
    assert _remove(api, other_project, user_id, expected=404).json()["detail"] == "Asignación activa no encontrada"
    with SessionLocal() as db:
        actor = db.query(models.Usuario.id_usuario).filter(
            models.Usuario.rol == "admin", models.Usuario.activo.is_(True)
        ).first()[0]
        set_audit_context(db, actor)
        inactive_project = models.Proyecto(clave_proyecto=unique("INACTIVO"),
                                           nombre_proyecto="Proyecto inactivo QA", creado_por=actor)
        mark_inactive(inactive_project, actor, REASON)
        db.add(inactive_project)
        db.commit()
        inactive_id = inactive_project.id_proyecto
    _remove(api, inactive_id, user_id, expected=403)


def test_inactive_account_can_be_unassigned_and_reactivation_restores_no_access(api):
    user, password = _create_user(api)
    project_id = _project(api)
    user_id = user["id_usuario"]
    assignment_id = _assign(api, project_id, user_id).json()["id_usuario_proyecto"]
    # Simulate an existing inactive principal with an independently active relation.
    # Account DELETE ordinarily deactivates relations, so prepare this edge case in QA.
    with SessionLocal() as db:
        actor = db.query(models.Usuario.id_usuario).filter(
            models.Usuario.rol == "admin", models.Usuario.activo.is_(True)
        ).first()[0]
        set_audit_context(db, actor)
        mark_inactive(db.get(models.Usuario, user_id), actor, "Cuenta inactiva sintética QA")
        db.commit()
    _remove(api, project_id, user_id)
    after, audit = _snapshot(assignment_id), _audit(assignment_id)
    with SessionLocal() as db:
        assert db.get(models.Usuario, user_id).activo is False
    _remove(api, project_id, user_id, expected=404)
    api("POST", f"/api/usuarios/{user_id}/reactivar", json={"motivo": "Reactivar cuenta sin permisos"})
    session, _ = _login(user["correo"], password)
    try:
        assert session.get("/api/proyectos").json() == []
        assert session.get(f"/api/proyectos/{project_id}").status_code == 403
        assert _snapshot(assignment_id) == after and _audit(assignment_id) == audit
    finally:
        session.close()


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_concurrent_requests_use_database_locks_and_preserve_one_winner(api, client, admin_headers, method):
    user, _ = _create_user(api)
    user_id, project_id = user["id_usuario"], _project(api)
    assignment_id = None
    if method == "DELETE":
        assignment_id = _assign(api, project_id, user_id).json()["id_usuario_proyecto"]
    barrier = threading.Barrier(3)

    # Different authenticated sessions avoid serializing workers on a heartbeat.
    sessions = [
        _login(os.environ["TEST_ADMIN_EMAIL"], os.environ["TEST_ADMIN_PASSWORD"])
        for _ in range(2)
    ]

    def request(index):
        concurrent_client, headers = sessions[index]
        try:
            barrier.wait(timeout=10)
            path = f"/api/proyectos/{project_id}/usuarios"
            payload = {"id_usuario": user_id}
            if method == "DELETE":
                path += f"/{user_id}"
                payload = {"motivo": REASON}
            return concurrent_client.request(method, path, headers=headers, json=payload)
        finally:
            concurrent_client.close()

    # Hold the referenced user row so both independent API transactions overlap.
    with engine.connect() as blocker, PostgreSQLWorkers() as workers:
        transaction = blocker.begin()
        blocker_pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        blocker.execute(text("SELECT id_usuario FROM usuario WHERE id_usuario=:id FOR UPDATE"), {"id": user_id})
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(workers.run, str(index), request, index) for index in range(2)]
            try:
                barrier.wait(timeout=10)
                wait_for_blocked_workers(workers.wait_pids(["0", "1"]), [blocker_pid])
            finally:
                transaction.rollback()
            responses = [future.result(timeout=15) for future in futures]
    assert sorted(response.status_code for response in responses) == (
        [201, 409] if method == "POST" else [200, 404]
    ), [response.text for response in responses]
    with SessionLocal() as db:
        assignments = db.query(models.UsuarioProyecto).filter(
            models.UsuarioProyecto.id_usuario == user_id,
            models.UsuarioProyecto.id_proyecto == project_id,
        ).all()
        assert len(assignments) == 1
        assert assignments[0].activo is (method == "POST")
        assignment_id = assignments[0].id_usuario_proyecto
    assert [row["accion"] for row in _audit(assignment_id)] == (
        ["insert"] if method == "POST" else ["insert", "update"]
    )


def test_post_waits_for_uncommitted_deactivation_and_creates_new_history(api, client, admin_headers):
    user, _ = _create_user(api)
    user_id, project_id = user["id_usuario"], _project(api)
    assignment_id = _assign(api, project_id, user_id).json()["id_usuario_proyecto"]
    actor = client.get("/api/auth/sesion").json()["user"]["id_usuario"]
    with SessionLocal() as writer, PostgreSQLWorkers() as workers:
        writer_pid = writer.execute(text("SELECT pg_backend_pid()")).scalar_one()
        set_audit_context(writer, actor)
        assignment = writer.query(models.UsuarioProyecto).filter(
            models.UsuarioProyecto.id_usuario_proyecto == assignment_id
        ).with_for_update().one()
        mark_inactive(assignment, actor, REASON)
        assignment.actualizado_en = assignment.fecha_baja
        assignment.actualizado_por = actor
        writer.flush()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(workers.run, "post", _assign, api, project_id, user_id)
            try:
                wait_for_blocked_workers(workers.wait_pids(["post"]), [writer_pid])
                writer.commit()
            finally:
                writer.rollback()
            response = future.result(timeout=15)
    assert response.json()["id_usuario_proyecto"] != assignment_id
    assert _snapshot(assignment_id)["activo"] is False
    assert _snapshot(assignment_id)["motivo_baja"] == REASON
    assert [row["accion"] for row in _audit(assignment_id)] == ["insert", "update"]
    _assign(api, project_id, user_id, expected=409)
