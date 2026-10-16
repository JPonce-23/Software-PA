"""Real FastAPI authentication and PostgreSQL pool; no dependency overrides.

Only the identified tmpfs cluster may run these synthetic write tests.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app import database
from app.config import AUTH_SETTINGS
from app.main import app
from app.services import authentication, convenio_reports


def login(email, password):
    client = TestClient(app, raise_server_exceptions=False)
    result = client.post("/api/auth/sesiones", data={"username": email, "password": password},
                         headers={"Origin": AUTH_SETTINGS.allowed_origins[0]})
    assert result.status_code == 200, result.text
    return client


@pytest.fixture(scope="module")
def real_report_env(api, test_admin_credentials):
    assert not app.dependency_overrides
    with database.engine.connect() as conn:
        assert conn.execute(text("SELECT current_database(),current_setting('cluster_name')")).one() == (
            "software_pa_test", "convenio-report-disposable",
        )
        assert database.engine.url.host == "db"
    project = api("POST", "/api/proyectos", expected=201, json={
        "clave_proyecto": "POOL-" + uuid.uuid4().hex[:12], "nombre_proyecto": "Pool sintético",
    }).json()
    password = "QaPool1!" + uuid.uuid4().hex
    email = uuid.uuid4().hex + "@pool.local"
    user = api("POST", "/api/usuarios", expected=201, json={
        "nombre": "Pool", "apellido_paterno": "QA", "correo": email,
        "rol": "visualizador", "contrasena": password,
    }).json()
    admin = login(*test_admin_credentials)
    denied = login(email, password)
    yield {"admin": admin, "denied": denied, "project_id": project["id_proyecto"],
           "user_id": user["id_usuario"], "api": api,
           "path": f"/api/proyectos/{project['id_proyecto']}/reportes/convenios/general"}
    admin.close()
    denied.close()


@pytest.fixture
def pool(real_report_env, monkeypatch):
    # Deliberately one connection, zero overflow: old report-first checkout
    # would starve authentication. Actual SQL and actual dependencies run.
    engine = create_engine(database.engine.url, pool_size=1, max_overflow=0,
                           pool_timeout=2, pool_pre_ping=True)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    yield engine
    assert engine.pool.checkedout() == 0
    engine.dispose()


@pytest.mark.parametrize("suffix", ["", "/entidades", "/completo"])
def test_auth_y_autorizacion_antes_de_checkout_del_reporte(real_report_env, pool, monkeypatch, suffix):
    stages = []
    authenticate = authentication.authenticate_session
    authorize = convenio_reports.require_project_access

    def auth_spy(*args, **kwargs):
        # No report transaction has checked out a connection at auth entry.
        assert pool.pool.checkedout() == 0
        stages.append("autenticacion")
        return authenticate(*args, **kwargs)

    def access_spy(db, *args, **kwargs):
        readonly = db.get_bind().get_execution_options().get("postgresql_readonly", False)
        if readonly:
            # Authorization session has already returned its physical connection.
            assert pool.pool.checkedout() == 0
            assert stages == ["autenticacion", "autorizado"]
            stages.append("reporte")
        result = authorize(db, *args, **kwargs)
        if not readonly:
            stages.append("autorizado")
        return result

    monkeypatch.setattr(authentication, "authenticate_session", auth_spy)
    monkeypatch.setattr(convenio_reports, "require_project_access", access_spy)
    response = real_report_env["admin"].get(real_report_env["path"] + suffix)
    assert response.status_code == 200, response.text
    assert stages == ["autenticacion", "autorizado", "reporte"]
    assert pool.pool.checkedout() == 0


@pytest.mark.parametrize("suffix", ["", "/entidades", "/completo"])
@pytest.mark.parametrize("kind,status", [("anonimo", 401), ("invalido", 401), ("sin_acceso", 403)])
def test_rechazos_sin_transaccion_de_reporte(real_report_env, pool, suffix, kind, status):
    report_sql = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        if conn.get_execution_options().get("postgresql_readonly"):
            report_sql.append(statement)
    event.listen(pool, "before_cursor_execute", capture)
    with TestClient(app, raise_server_exceptions=False) as client:
        if kind == "invalido":
            client.cookies.set(AUTH_SETTINGS.session_cookie_name, "invalid-synthetic-session")
        elif kind == "sin_acceso":
            client.cookies.update(real_report_env["denied"].cookies)
        response = client.get(real_report_env["path"] + suffix)
    assert response.status_code == status, response.text
    assert "individuales" not in response.json() and "entidades" not in response.json()
    assert not report_sql
    assert pool.pool.checkedout() == 0


def test_liberacion_ante_error_real_de_consulta(real_report_env, pool):
    def fail(conn, cursor, statement, parameters, context, executemany):
        if conn.get_execution_options().get("postgresql_readonly"):
            # A real SQL failure aborts the transaction after physical checkout.
            cursor.execute("SELECT 1/0")
    event.listen(pool, "before_cursor_execute", fail)
    try:
        response = real_report_env["admin"].get(real_report_env["path"] + "/completo")
        assert response.status_code == 500
        assert pool.pool.checkedout() == 0
    finally:
        event.remove(pool, "before_cursor_execute", fail)
    assert real_report_env["admin"].get(real_report_env["path"]).status_code == 200
    assert pool.pool.checkedout() == 0


def test_solicitudes_simultaneas_con_pool_de_una_conexion(real_report_env, pool):
    barrier, lock = Barrier(6), Lock()
    checkouts = []
    def checkout(*args):
        with lock:
            checkouts.append(1)
    event.listen(pool, "checkout", checkout)
    def request(index):
        with TestClient(app, raise_server_exceptions=False) as client:
            client.cookies.update(real_report_env["admin"].cookies)
            barrier.wait(timeout=10)
            return client.get(real_report_env["path"] + ("", "/entidades", "/completo")[index % 3])
    with ThreadPoolExecutor(max_workers=6) as executor:
        responses = list(executor.map(request, range(6)))
    assert [r.status_code for r in responses] == [200] * 6, [r.text for r in responses]
    assert len(checkouts) >= 12  # Actual authentication and report transactions.
    assert pool.pool.checkedout() == 0


def test_snapshot_completo_real_por_http(real_report_env):
    # Update a project between the totals and the ranked SELECT with a real
    # concurrent API writer. Read inside the report's actual transaction to
    # verify its old snapshot, and outside afterwards to verify the new value.
    assert not app.dependency_overrides
    writer_api = real_report_env["api"]
    changed = []
    def concurrent_write(conn, cursor, statement, parameters, context, executemany):
        if conn.get_execution_options().get("postgresql_readonly") and "row_number()" in statement and not changed:
            changed.append(True)
            result = writer_api("PATCH", f"/api/proyectos/{real_report_env['project_id']}",
                                json={"nombre_proyecto": "Cambio concurrente sintético"})
            assert result.status_code == 200
            assert conn.exec_driver_sql("SHOW transaction_isolation").scalar_one() == "repeatable read"
            assert conn.exec_driver_sql("SHOW transaction_read_only").scalar_one() == "on"
            value = conn.execute(text("SELECT nombre_proyecto FROM proyecto WHERE id_proyecto=:id"),
                                 {"id": real_report_env["project_id"]}).scalar_one()
            assert value == "Pool sintético"
    event.listen(database.engine, "before_cursor_execute", concurrent_write)
    try:
        result = real_report_env["admin"].get(real_report_env["path"] + "/completo")
        assert result.status_code == 200, result.text
        assert result.json()["completo"] is True
        assert result.json()["paginacion_individuales"]["total"] == 0
        assert changed
    finally:
        event.remove(database.engine, "before_cursor_execute", concurrent_write)
    with database.engine.connect() as conn:
        assert conn.execute(text("SELECT nombre_proyecto FROM proyecto WHERE id_proyecto=:id"),
                            {"id": real_report_env["project_id"]}).scalar_one() == "Cambio concurrente sintético"


def test_usuario_asignado_con_autenticacion_real(real_report_env, pool):
    real_report_env["api"]("POST", f"/api/proyectos/{real_report_env['project_id']}/usuarios",
                           expected=201, json={"id_usuario": real_report_env["user_id"]})
    for suffix in ("", "/entidades", "/completo"):
        response = real_report_env["denied"].get(real_report_env["path"] + suffix)
        assert response.status_code == 200, response.text
        assert response.json()["id_proyecto"] == real_report_env["project_id"]
        assert pool.pool.checkedout() == 0
