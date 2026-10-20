"""F01 equivalence and query budget on the local disposable PostgreSQL only."""

from contextlib import contextmanager
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import statistics
import time
from types import SimpleNamespace
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, inspect, text
from sqlalchemy.orm import raiseload

from app import auth, models, schemas
from app.config import AUTH_SETTINGS
from app.main import app
from app.routers import domain
from app.services.access import filter_projects_by_user
from app.services.authentication import hash_password
from app.services.common import mark_inactive, set_audit_context


ROLES = ("admin", "operador", "visualizador", "geografo")


def original_list_projects(skip, limit, db, user):
    # Query frozen from 630f7dd: the reference retains every original loader.
    query = db.query(models.Proyecto).filter(models.Proyecto.activo.is_(True))
    query = filter_projects_by_user(query, db, user)
    return query.order_by(models.Proyecto.nombre_proyecto).offset(skip).limit(limit).all()


@contextmanager
def sql_reads(connection):
    queries = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(("SELECT", "WITH")):
            queries.append(statement)

    event.listen(connection, "before_cursor_execute", capture)
    try:
        yield queries
    finally:
        event.remove(connection, "before_cursor_execute", capture)


@pytest.fixture(scope="module")
def projects_env(transactional_api):
    factory = transactional_api["session_factory"]
    with factory() as db:
        assert db.execute(text("SELECT current_database(), current_setting('cluster_name')")).one() == (
            "software_pa_test", "convenio-report-disposable",
        ), "Use el Compose local desechable; nunca una base persistente"
        actor = db.query(models.Usuario.id_usuario).filter_by(rol="admin", activo=True).first()[0]
        set_audit_context(db, actor)
        # Other modules may leave active synthetic projects in a shared run.
        # Hide them only inside this module's outer rollback, keeping the same
        # 205-project expectations and restoring prior state at fixture teardown.
        for project in db.query(models.Proyecto).options(raiseload("*")).filter_by(activo=True).all():
            mark_inactive(project, actor, "Aislamiento transaccional del fixture F01")
        db.flush()
        password = "Qa1!" + uuid.uuid4().hex
        users = {}
        for role in ROLES:
            user = models.Usuario(
                nombre="F01", apellido_paterno="Sintético", rol=role,
                correo=f"f01-{role}-{uuid.uuid4().hex}@local.invalid",
                contrasena_hash=hash_password(password), activo=True,
                fecha_alta=datetime.now(timezone.utc),
            )
            db.add(user)
            db.flush()
            users[role] = SimpleNamespace(id_usuario=user.id_usuario, rol=role, correo=user.correo)
        # Deliberately inserted in reverse name order; >200 accessible projects.
        projects = [models.Proyecto(
            clave_proyecto=f"F01-{uuid.uuid4().hex[:20]}", nombre_proyecto=f"F01 {i:03}",
            descripcion=None if i % 2 else "Descripción áéíóú ñ",
            fecha_inicio=date(2026, 1, 1) if i % 2 else None,
            fecha_fin=date(2026, 12, 31) if i % 2 else None,
            observaciones="Prueba sintética" if i % 2 else None, creado_por=actor,
        ) for i in range(207)]
        db.add_all(reversed(projects))
        db.flush()
        ids = [p.id_proyecto for p in projects]
        for role in ("operador",):
            for index in [*range(203), 205]:
                link = models.UsuarioProyecto(
                    id_usuario=users[role].id_usuario, id_proyecto=ids[index], creado_por=actor,
                    asignado_por=actor,
                )
                db.add(link)
                db.flush()
                if index == 202:
                    mark_inactive(link, actor, "Asignación revocada de prueba")
            # Historical revoked assignment alongside a current one: no duplicates.
            historical = models.UsuarioProyecto(
                id_usuario=users[role].id_usuario, id_proyecto=ids[0], activo=False,
                creado_por=actor, asignado_por=actor, fecha_baja=datetime.now(timezone.utc),
                id_usuario_baja=actor, motivo_baja="Histórico sintético",
            )
            db.add(historical)
        for index in (205, 206):
            mark_inactive(projects[index], actor, "Proyecto inactivo de prueba")
        tenure = db.query(models.CatalogoOperativo.id_catalogo_opcion).filter_by(
            tipo_catalogo="tipo_tenencia", codigo="ejido",
        ).one()[0]
        nucleus = models.NucleoAgrario(
            id_municipio=1, nombre_nucleo="Núcleo compartido F01", id_tipo_tenencia=tenure,
            creado_por=actor,
        )
        db.add(nucleus)
        db.flush()
        # Sharing a nucleus with an unassigned project must not broaden visibility.
        for index in (0, 203):
            pn = models.ProyectoNucleo(id_proyecto=ids[index], id_nucleo=nucleus.id_nucleo,
                                       creado_por=actor)
            db.add(pn)
            db.flush()
            for activity in range(12):
                db.add(models.ActividadCampo(id_proyecto_nucleo=pn.id_proyecto_nucleo,
                                              tipo_actividad="sensibilizacion", creado_por=actor,
                                              resultado=f"Resultado sintético {activity}"))
        db.commit()
    return {**transactional_api, "users": users, "password": password, "ids": ids}


@contextmanager
def endpoint_version(monkeypatch, original=False):
    routes = [candidate for route in app.routes for candidate in (
        route.effective_route_contexts() if hasattr(route, "effective_route_contexts") else [route]
    )]
    route = next(r for r in routes if getattr(r, "path", None) == "/api/proyectos"
                 and "GET" in getattr(r, "methods", set()))
    calls = []

    def original_call(**kwargs):
        calls.append(True)
        return original_list_projects(**kwargs)

    with monkeypatch.context() as patch:
        if original:
            patch.setattr(route.dependant, "call", original_call)
        yield
    if original:
        assert calls, "La comparación HTTP debe ejecutar la consulta original"


def payload_for(env, user, *, original=False, skip=0, limit=100):
    with env["session_factory"]() as db:
        function = original_list_projects if original else domain.list_projects
        rows = function(skip=skip, limit=limit, db=db, user=user)
        return [schemas.ProyectoResponse.model_validate(row).model_dump(mode="json") for row in rows]


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("skip,limit", [(0, 1), (0, 100), (0, 200), (199, 200), (205, 200), (999, 1)])
def test_roles_json_order_and_pagination(projects_env, monkeypatch, role, skip, limit):
    user = projects_env["users"][role]
    monkeypatch.setitem(app.dependency_overrides, auth.get_current_user, lambda: user)
    expected = payload_for(projects_env, user, original=True, skip=skip, limit=limit)
    response = projects_env["request"]("GET", "/api/proyectos", params={"skip": skip, "limit": limit})
    assert response.json() == expected
    accessible = projects_env["ids"][:202] if role == "operador" else projects_env["ids"][:205]
    assert [row["id_proyecto"] for row in response.json()] == accessible[skip:skip + limit]
    assert all(row["activo"] for row in response.json())


@pytest.mark.parametrize("role", ROLES)
def test_bounded_loading_and_serialization(projects_env, role):
    user = projects_env["users"][role]
    with projects_env["session_factory"]() as db:
        with sql_reads(projects_env["connection"]) as queries:
            rows = domain.list_projects(skip=0, limit=200, db=db, user=user)
            query_count = len(queries)
            assert query_count == 1
            assert len(db.identity_map) == len(rows) == 200
            for row in rows:
                assert {"nucleos", "trazos", "asignaciones", "derechos_via"} <= inspect(row).unloaded
            payload = [schemas.ProyectoResponse.model_validate(r).model_dump(mode="json") for r in rows]
            assert len(queries) == query_count  # Serialization must issue zero SQL.
    assert payload == payload_for(projects_env, user, original=True, limit=200)


@pytest.mark.parametrize("role", ROLES[1:])
def test_empty_scope_and_revocation(projects_env, monkeypatch, role):
    user = projects_env["users"][role]
    unassigned = SimpleNamespace(id_usuario=-1, rol=role)
    expected_scope = [] if role == "operador" else projects_env["ids"][:100]
    assert [r["id_proyecto"] for r in payload_for(projects_env, unassigned)] == expected_scope
    assert [r["id_proyecto"] for r in payload_for(projects_env, unassigned, original=True)] == expected_scope
    if role == "operador":
        with projects_env["session_factory"]() as db:
            set_audit_context(db, projects_env["users"]["admin"].id_usuario)
            link = db.query(models.UsuarioProyecto).filter_by(
                id_usuario=user.id_usuario, id_proyecto=projects_env["ids"][0], activo=True,
            ).one()
            mark_inactive(link, projects_env["users"]["admin"].id_usuario, "Revocación F01")
            db.flush()
            for original in (False, True):
                fn = original_list_projects if original else domain.list_projects
                rows = fn(skip=0, limit=200, db=db, user=user)
                assert projects_env["ids"][0] not in {r.id_proyecto for r in rows}
            db.rollback()


@pytest.mark.parametrize("role", ROLES)
def test_real_sessions_status_json_and_neighbor_endpoints(projects_env, monkeypatch, role):
    # Keep database isolation, restore the real authentication dependency.
    monkeypatch.delitem(app.dependency_overrides, auth.get_current_user)
    user = projects_env["users"][role]
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.get("/api/proyectos").status_code == 401
        login = client.post("/api/auth/sesiones", data={"username": user.correo,
                            "password": projects_env["password"]},
                            headers={"Origin": AUTH_SETTINGS.allowed_origins[0]})
        assert login.status_code == 200, login.text
        responses = []
        for original in (True, False):
            with endpoint_version(monkeypatch, original):
                responses.append([(r.status_code, r.content) for r in (
                    client.get("/api/proyectos?limit=200"),
                    client.get("/api/proyectos?skip=-1"),
                    client.get("/api/proyectos?limit=0"),
                    client.get("/api/proyectos?limit=201"),
                    client.get("/api/proyectos?skip=999"),
                    client.get(f"/api/proyectos/{projects_env['ids'][203]}"),
                    client.get(f"/api/proyectos/{projects_env['ids'][205]}"),
                    client.get("/api/proyectos/2147483647"),
                )])
        assert responses[0] == responses[1]
        assert [r[0] for r in responses[1]] == [200, 422, 422, 422, 200,
                                                               403 if role == "operador" else 200, 403, 403]
        assert json.loads(responses[1][4][1]) == []
        session = client.get("/api/auth/sesion")
        assert session.status_code == 200


def test_disallowed_role_still_forbidden(projects_env, monkeypatch):
    monkeypatch.setitem(app.dependency_overrides, auth.get_current_user,
                        lambda: SimpleNamespace(id_usuario=-1, rol="invalid"))
    projects_env["request"]("GET", "/api/proyectos", expected=403)


def measure(env, function, user):
    with env["session_factory"]() as db:
        with sql_reads(env["connection"]) as queries:
            start = time.perf_counter()
            rows = function(skip=0, limit=2, db=db, user=user)
            wall_ms = (time.perf_counter() - start) * 1000
            sql_count = len(queries)
            objects = len(db.identity_map)
            payload = [schemas.ProyectoResponse.model_validate(row).model_dump(mode="json") for row in rows]
            return {"ms": wall_ms, "sql": sql_count, "objects": objects,
                    "serialization_sql": len(queries) - sql_count, "rows": len(rows)}, payload


def save_measurements(name, result):
    print(name + "=" + json.dumps(result, sort_keys=True))
    if os.getenv("F01_EVIDENCE_DIR"):
        (Path(os.environ["F01_EVIDENCE_DIR"]) / (name + ".json")).write_text(json.dumps(result, indent=2))


def test_original_baseline(projects_env):
    user = projects_env["users"]["admin"]
    measure(projects_env, original_list_projects, user)  # Mapper/process warm-up excluded.
    samples = [measure(projects_env, original_list_projects, user)[0] for _ in range(15)]
    save_measurements("original_baseline", {"samples": samples,
                      "median_ms": statistics.median(s["ms"] for s in samples)})
    assert all(s["rows"] == 2 and s["sql"] > 1 and s["serialization_sql"] == 0 for s in samples)


def test_benchmark_original_vs_optimized(projects_env):
    user = projects_env["users"]["admin"]
    variants = (original_list_projects, domain.list_projects)
    for fn in variants:
        measure(projects_env, fn, user)
    results = {"original": [], "optimized": []}
    for i in range(15):
        pair = []
        for index in ((0, 1) if i % 2 == 0 else (1, 0)):
            sample, payload = measure(projects_env, variants[index], user)
            results[("original", "optimized")[index]].append(sample)
            pair.append(payload)
        assert pair[0] == pair[1]
    for samples in results.values():
        assert all(s["serialization_sql"] == 0 for s in samples)
    assert {s["sql"] for s in results["optimized"]} == {1}
    assert {s["objects"] for s in results["optimized"]} == {2}
    assert min(s["sql"] for s in results["original"]) > 1
    assert min(s["objects"] for s in results["original"]) > 2
    save_measurements("comparison", {key: {"samples": samples,
                      "median_ms": statistics.median(s["ms"] for s in samples)}
                      for key, samples in results.items()})
