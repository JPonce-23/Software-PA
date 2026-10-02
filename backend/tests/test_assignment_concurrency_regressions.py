"""Reproduce audit races with independent HTTP sessions and exact PostgreSQL PID waits."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest
from fastapi import HTTPException
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app import models
from app import schemas
from app.database import SessionLocal, engine
from app.services import domain
from .concurrency import PostgreSQLWorkers, wait_for_blocked_workers, workers_are_blocked
from .test_project_user_assignments import REASON, _assign, _audit, _project, _snapshot
from .test_user_administration import _create_user, _login


def _admin_session():
    return _login(os.environ["TEST_ADMIN_EMAIL"], os.environ["TEST_ADMIN_PASSWORD"])


@contextmanager
def _pause_flush(predicate):
    """Stop the winning transaction after validation/locks, before its first write."""
    reached, release = threading.Event(), threading.Event()

    def pause(session, context, instances):
        if any(predicate(row) for row in list(session.new) + list(session.dirty)):
            reached.set()
            assert release.wait(15), "La transacción ganadora no fue liberada"

    event.listen(Session, "before_flush", pause)
    try:
        yield reached, release
    finally:
        release.set()
        event.remove(Session, "before_flush", pause)


@contextmanager
def _pause_project_update():
    reached, release = threading.Event(), threading.Event()

    def pause(connection, cursor, statement, parameters, context, many):
        if statement.startswith("UPDATE proyecto "):
            reached.set()
            assert release.wait(15)

    event.listen(engine, "after_cursor_execute", pause)
    try:
        yield reached, release
    finally:
        release.set()
        event.remove(engine, "after_cursor_execute", pause)


@pytest.mark.parametrize("first", ["post", "user_delete"])
def test_assignment_serializes_with_global_user_deactivation(api, first):
    user, password = _create_user(api)
    user_id, project_id = user["id_usuario"], _project(api)
    clients = {name: _admin_session() for name in ("post", "user_delete")}

    def request(name):
        client, headers = clients[name]
        if name == "post":
            return client.post(f"/api/proyectos/{project_id}/usuarios", headers=headers,
                               json={"id_usuario": user_id})
        return client.request("DELETE", f"/api/usuarios/{user_id}", headers=headers,
                              json={"motivo": REASON})

    def winning_row(row):
        if first == "post":
            return isinstance(row, models.UsuarioProyecto) and row.id_usuario == user_id
        return isinstance(row, models.Usuario) and row.id_usuario == user_id and not row.activo

    try:
        with PostgreSQLWorkers() as workers, _pause_flush(winning_row) as (reached, release):
            with ThreadPoolExecutor(max_workers=2) as pool:
                winner = pool.submit(workers.run, first, request, first)
                try:
                    assert reached.wait(10), "La operación no adquirió sus bloqueos"
                    second = "user_delete" if first == "post" else "post"
                    loser = pool.submit(workers.run, second, request, second)
                    wait_for_blocked_workers(workers.wait_pids([second]), workers.wait_pids([first]))
                finally:
                    release.set()
                responses = {first: winner.result(15), second: loser.result(15)}
            assert any("FOR NO KEY UPDATE" in sql for sql in workers.statements["post"])
        assert responses["user_delete"].status_code == 200, responses["user_delete"].text
        assert responses["post"].status_code == (201 if first == "post" else 404), responses["post"].text
        with SessionLocal() as db:
            assert not db.get(models.Usuario, user_id).activo
            rows = db.query(models.UsuarioProyecto).filter_by(id_usuario=user_id, id_proyecto=project_id).all()
            assert len(rows) == (1 if first == "post" else 0)
            assert not any(row.activo for row in rows)
            historical = _snapshot(rows[0].id_usuario_proyecto) if rows else None
            if rows:
                assert rows[0].fecha_baja is not None and rows[0].motivo_baja == REASON
                assert [a["accion"] for a in _audit(rows[0].id_usuario_proyecto)] == ["insert", "update"]
        api("POST", f"/api/usuarios/{user_id}/reactivar", json={"motivo": "Reactivación QA sin permisos"})
        session, _ = _login(user["correo"], password)
        try:
            assert session.get("/api/proyectos").json() == []
            assert session.get(f"/api/proyectos/{project_id}").status_code == 403
        finally:
            session.close()
        if historical:
            assert _snapshot(historical["id_usuario_proyecto"]) == historical
    finally:
        for client, _ in clients.values():
            client.close()


@pytest.mark.parametrize("first", ["post", "project_delete"])
def test_assignment_serializes_with_project_deactivation(api, first):
    user, _ = _create_user(api)
    user_id, project_id = user["id_usuario"], _project(api)
    clients = {name: _admin_session() for name in ("post", "project_delete")}

    def request(name):
        client, headers = clients[name]
        if name == "post":
            return client.post(f"/api/proyectos/{project_id}/usuarios", headers=headers,
                               json={"id_usuario": user_id})
        return client.request("DELETE", f"/api/proyectos/{project_id}", headers=headers,
                              json={"motivo": REASON})

    def winning_row(row):
        if first == "post":
            return isinstance(row, models.UsuarioProyecto) and row.id_usuario == user_id
        return isinstance(row, models.Proyecto) and row.id_proyecto == project_id and not row.activo

    try:
        pause = _pause_flush(winning_row) if first == "post" else _pause_project_update()
        with PostgreSQLWorkers() as workers, pause as (reached, release):
            with ThreadPoolExecutor(max_workers=2) as pool:
                winner = pool.submit(workers.run, first, request, first)
                try:
                    assert reached.wait(10)
                    second = "project_delete" if first == "post" else "post"
                    loser = pool.submit(workers.run, second, request, second)
                    wait_for_blocked_workers(workers.wait_pids([second]), workers.wait_pids([first]))
                finally:
                    release.set()
                winner_response, loser_response = winner.result(15), loser.result(15)
                responses = {first: winner_response, second: loser_response}
        assert responses["project_delete"].status_code == 200, responses["project_delete"].text
        assert responses["post"].status_code == (201 if first == "post" else 403), responses["post"].text
        with SessionLocal() as db:
            assert not db.get(models.Proyecto, project_id).activo
            rows = db.query(models.UsuarioProyecto).filter_by(id_usuario=user_id, id_proyecto=project_id).all()
            assert len(rows) == (1 if first == "post" else 0)
            # Existing project deletion has no assignment cascade. Its active flag
            # denies access; changing that policy is outside this correction.
            assert all(row.activo for row in rows)
    finally:
        for client, _ in clients.values():
            client.close()


def test_cross_admin_unassignments_do_not_deadlock_and_audit_each_actor(api):
    admins = [_create_user(api, role="admin") for _ in range(2)]
    project_id = _project(api)
    ids = [admin["id_usuario"] for admin, _ in admins]
    assignment_ids = [_assign(api, project_id, user_id).json()["id_usuario_proyecto"] for user_id in ids]
    clients = [_login(admin["correo"], password) for admin, password in admins]
    barrier = threading.Barrier(2)

    def synchronize(session, context, instances):
        if any(isinstance(row, models.UsuarioProyecto) and row.id_usuario_proyecto in assignment_ids
               and not row.activo for row in session.dirty):
            barrier.wait(10)

    def request(index):
        client, headers = clients[index]
        return client.request("DELETE", f"/api/proyectos/{project_id}/usuarios/{ids[1-index]}",
                              headers=headers, json={"motivo": REASON})

    try:
        event.listen(Session, "before_flush", synchronize)
        with PostgreSQLWorkers() as workers, ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(workers.run, str(index), request, index) for index in range(2)]
            responses = [future.result(20) for future in futures]
            assert [response.status_code for response in responses] == [200, 200], [r.text for r in responses]
            assert len(set(workers.wait_pids(["0", "1"]))) == 2
            for name in ("0", "1"):
                assert any("FOR NO KEY UPDATE" in sql for sql in workers.statements[name])
        for index, assignment_id in enumerate(assignment_ids):
            row = _snapshot(assignment_id)
            assert not row["activo"] and row["motivo_baja"] == REASON
            assert row["id_usuario_baja"] == row["actualizado_por"] == ids[1-index]
            assert row["fecha_baja"] == row["actualizado_en"] is not None
            audit = _audit(assignment_id)
            assert [a["accion"] for a in audit] == ["insert", "update"]
            assert audit[-1]["id_usuario"] == ids[1-index]
            assert audit[-1]["valor_anterior"]["activo"] and not audit[-1]["valor_nuevo"]["activo"]
    finally:
        event.remove(Session, "before_flush", synchronize)
        for client, _ in clients:
            client.close()
        for user_id in ids:
            api("DELETE", f"/api/usuarios/{user_id}", json={"motivo": "Limpieza administradores QA"})


def test_unrelated_lock_cannot_satisfy_worker_observer(api):
    project_id = _project(api)
    with engine.connect() as blocker, engine.connect() as worker, engine.connect().execution_options(
        isolation_level="AUTOCOMMIT"
    ) as observer:
        blocker_pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        worker_pid = worker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        observer_pid = observer.execute(text("SELECT pg_backend_pid()")).scalar_one()
        blocker.execute(text("SELECT id_proyecto FROM proyecto WHERE id_proyecto=:id FOR UPDATE"), {"id": project_id})
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(worker.execute, text(
                "SELECT id_proyecto FROM proyecto WHERE id_proyecto=:id FOR UPDATE"
            ), {"id": project_id})
            try:
                wait_for_blocked_workers([worker_pid], [blocker_pid])
                assert not workers_are_blocked(observer, [observer_pid], [blocker_pid])
                assert not workers_are_blocked(observer, [worker_pid], [observer_pid])
            finally:
                blocker.rollback()
            future.result(15)
        worker.rollback()


def test_assignment_revalidates_a_preloaded_user_after_global_deactivation(api):
    user, _ = _create_user(api)
    user_id, project_id = user["id_usuario"], _project(api)
    actor = api("GET", "/api/auth/sesion").json()["user"]["id_usuario"]
    with SessionLocal() as db:
        cached = db.get(models.Usuario, user_id)
        assert cached.activo
        api("DELETE", f"/api/usuarios/{user_id}", json={"motivo": REASON})
        assert cached.activo  # Identity map has the old state until locked refresh.
        with pytest.raises(HTTPException) as exc:
            domain.assign_user_to_project(db, project_id, schemas.UsuarioProyectoCreate(id_usuario=user_id),
                                          db.get(models.Usuario, actor))
        assert exc.value.status_code == 404
        assert not cached.activo
        db.rollback()
    with SessionLocal() as db:
        assert not db.query(models.UsuarioProyecto).filter_by(id_usuario=user_id, id_proyecto=project_id).count()


def test_different_users_can_be_assigned_concurrently_to_the_same_project(api):
    ids = [_create_user(api)[0]["id_usuario"] for _ in range(2)]
    project_id = _project(api)
    clients = [_admin_session() for _ in ids]
    barrier = threading.Barrier(2)

    def synchronize(session, context, instances):
        if any(isinstance(row, models.UsuarioProyecto) and row.id_usuario in ids for row in session.new):
            barrier.wait(10)

    def request(index):
        client, headers = clients[index]
        return client.post(f"/api/proyectos/{project_id}/usuarios", headers=headers,
                           json={"id_usuario": ids[index]})

    event.listen(Session, "before_flush", synchronize)
    try:
        with PostgreSQLWorkers() as workers, ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(workers.run, str(index), request, index) for index in range(2)]
            responses = [future.result(20) for future in futures]
            assert len(set(workers.wait_pids(["0", "1"]))) == 2
            assert all(any("FOR SHARE" in sql for sql in workers.statements[name]) for name in ("0", "1"))
        assert [r.status_code for r in responses] == [201, 201], [r.text for r in responses]
        with SessionLocal() as db:
            assert db.query(models.UsuarioProyecto).filter(
                models.UsuarioProyecto.id_usuario.in_(ids),
                models.UsuarioProyecto.id_proyecto == project_id,
                models.UsuarioProyecto.activo.is_(True),
            ).count() == 2
    finally:
        event.remove(Session, "before_flush", synchronize)
        for client, _ in clients:
            client.close()


@pytest.mark.parametrize("first", ["individual", "global"])
def test_individual_and_global_deactivation_serialize_without_changing_history(api, first):
    user, _ = _create_user(api)
    user_id = user["id_usuario"]
    project_id, other_project = _project(api), _project(api)
    assignment_id = _assign(api, project_id, user_id).json()["id_usuario_proyecto"]
    other_id = _assign(api, other_project, user_id).json()["id_usuario_proyecto"]
    clients = {name: _admin_session() for name in ("individual", "global")}

    def request(name):
        client, headers = clients[name]
        path = f"/api/proyectos/{project_id}/usuarios/{user_id}" if name == "individual" else f"/api/usuarios/{user_id}"
        return client.request("DELETE", path, headers=headers,
                              json={"motivo": REASON if name == "individual" else "Baja global QA"})

    def winning_row(row):
        return ((first == "individual" and isinstance(row, models.UsuarioProyecto)
                 and row.id_usuario_proyecto == assignment_id and not row.activo)
                or (first == "global" and isinstance(row, models.Usuario)
                    and row.id_usuario == user_id and not row.activo))

    try:
        with PostgreSQLWorkers() as workers, _pause_flush(winning_row) as (reached, release), ThreadPoolExecutor(max_workers=2) as pool:
            winner = pool.submit(workers.run, first, request, first)
            try:
                assert reached.wait(10)
                second = "global" if first == "individual" else "individual"
                loser = pool.submit(workers.run, second, request, second)
                wait_for_blocked_workers(workers.wait_pids([second]), workers.wait_pids([first]))
            finally:
                release.set()
            responses = {first: winner.result(15), second: loser.result(15)}
        assert responses["global"].status_code == 200
        assert responses["individual"].status_code == (200 if first == "individual" else 404)
        for row_id in (assignment_id, other_id):
            assert not _snapshot(row_id)["activo"]
            assert [a["accion"] for a in _audit(row_id)] == ["insert", "update"]
        assert _snapshot(assignment_id)["motivo_baja"] == (REASON if first == "individual" else "Baja global QA")
        assert _snapshot(other_id)["motivo_baja"] == "Baja global QA"
    finally:
        for client, _ in clients.values():
            client.close()


def test_failed_assignment_update_rolls_back_its_trigger_audit(api):
    user, _ = _create_user(api)
    user_id, project_id = user["id_usuario"], _project(api)
    assignment_id = _assign(api, project_id, user_id).json()["id_usuario_proyecto"]
    before, audit = _snapshot(assignment_id), _audit(assignment_id)
    executed = []

    def fail_after_update(connection, cursor, statement, parameters, context, many):
        if statement.startswith("UPDATE usuario_proyecto "):
            executed.append(statement)
            # The real UPDATE and bitacora trigger have executed in this same
            # PostgreSQL transaction. A real DB failure must roll both back.
            connection.exec_driver_sql("SELECT 1 / 0")

    event.listen(engine, "after_cursor_execute", fail_after_update)
    try:
        api("DELETE", f"/api/proyectos/{project_id}/usuarios/{user_id}", expected=409,
            json={"motivo": REASON})
    finally:
        event.remove(engine, "after_cursor_execute", fail_after_update)
    assert len(executed) == 1
    assert _snapshot(assignment_id) == before
    assert _audit(assignment_id) == audit
