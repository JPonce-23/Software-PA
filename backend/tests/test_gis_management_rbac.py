"""GIS administration is private; published cartography follows project scope.

Uses real sessions and the disposable PostgreSQL/PostGIS fixtures, including
published imports, raw feature geometry, historical cycles and revision IDs.
"""
from contextlib import contextmanager
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app import auth, models, main as main_module
from app.main import app
from app.routers import geospatial_imports
from app.services.common import mark_inactive, set_audit_context
from tests.test_frontend_read_models import gis_sample
from tests.test_user_administration import _create_user, _login


@pytest.fixture(scope="module")
def gis_rbac_env(transactional_api, gis_sample):
    env = dict(transactional_api)
    api = env["request"]
    pid, iid = gis_sample["project"], gis_sample["import"]
    feature = api("GET", f"/api/importaciones/{iid}/features").json()[0]
    cycle = api("GET", f"/api/importaciones/{iid}/conciliaciones").json()[0]
    revision = api("GET", f"/api/proyectos/{pid}/geoespacial/revisiones").json()[0]
    users = {}
    for name, role in (("admin", "admin"), ("geografo", "geografo"),
                       ("visualizador", "visualizador"), ("operador", "operador"),
                       ("operador_sin_asignacion", "operador")):
        user, password = _create_user(api, role=role)
        users[name] = (user, password)
    api("POST", f"/api/proyectos/{pid}/usuarios", expected=201,
        json={"id_usuario": users["operador"][0]["id_usuario"]})
    env.update(project=pid, import_id=iid, feature=feature["id_importacion_feature"],
               cycle=cycle["id_ciclo"], revision=revision["id_revision"], users=users,
               actor=app.dependency_overrides[auth.get_current_user]().id_usuario,
               map_json=api("GET", f"/api/proyectos/{pid}/mapa").json(),
               indicators=api("GET", f"/api/proyectos/{pid}/mapa/indicadores").json())
    return env


def management_requests(env):
    p, i, f, c, r = (env[k] for k in ("project", "import_id", "feature", "cycle", "revision"))
    prefix = f"/api/importaciones/{i}"
    feature = f"{prefix}/features/{f}"
    return [
        ("GET", f"/api/proyectos/{p}/importaciones", {}),
        *[("POST", f"/api/proyectos/{p}/geoespacial/{kind}/importaciones", {})
          for kind in ("ddv", "nucleos", "parcelas")],
        ("POST", f"/api/proyectos/{p}/importaciones", {}),
        ("GET", prefix, {}),
        ("GET", f"{prefix}/features", {}),
        ("POST", f"{prefix}/baja", {"json": {"motivo": "RBAC sin escritura"}}),
        ("POST", f"{prefix}/confirmar", {"json": {"confirmacion_explicita": True}}),
        ("GET", f"/api/proyectos/{p}/geoespacial/configuracion", {}),
        ("PUT", f"/api/proyectos/{p}/geoespacial/configuracion", {"json": {"srid_trabajo": 4326}}),
        ("GET", f"{prefix}/resumen", {}),
        ("GET", f"{feature}/candidatos", {}),
        ("POST", f"{feature}/decisiones", {"json": {"accion": "ignorar", "motivo": "RBAC"}}),
        ("GET", f"{feature}/decisiones", {}),
        ("GET", f"{feature}/geometria", {}),
        ("POST", f"{prefix}/reconciliar", {"json": {"motivo": "RBAC", "clave_solicitud": str(uuid.uuid4())}}),
        ("GET", f"{prefix}/conciliaciones", {}),
        ("GET", f"{prefix}/conciliaciones/{c}", {}),
        ("GET", f"/api/proyectos/{p}/geoespacial/revisiones", {}),
        ("GET", f"/api/geoespacial/revisiones/{r}", {}),
        ("POST", f"/api/geoespacial/revisiones/{r}/decisiones",
         {"json": {"accion": "revisado", "motivo": "RBAC", "clave_solicitud": str(uuid.uuid4())}}),
    ]


@contextmanager
def logged_in(env, monkeypatch, name):
    monkeypatch.delitem(app.dependency_overrides, auth.get_current_user)
    # CSRF opens its own SessionLocal outside FastAPI's get_db dependency.
    # Keep the real CSRF check on the same isolated fixture transaction.
    monkeypatch.setattr(main_module, "SessionLocal", env["session_factory"])
    user, password = env["users"][name]
    client, headers = _login(user["correo"], password)
    try:
        yield client, headers
    finally:
        client.close()


@contextmanager
def checkpoint(env):
    transaction = env["connection"].begin_nested()
    try:
        yield
    finally:
        transaction.rollback()


def test_inventory_covers_all_administrative_routes(gis_rbac_env):
    requests = management_requests(gis_rbac_env)
    assert len(requests) == len(geospatial_imports.router.routes) == 22
    for route in geospatial_imports.router.routes:
        for method in route.methods:
            assert any(m == method and route.path_regex.fullmatch(path.removeprefix("/api"))
                       for m, path, _ in requests), (method, route.path)


@pytest.mark.parametrize("name", ["admin", "geografo", "visualizador"])
def test_only_operators_can_receive_new_project_assignments(gis_rbac_env, name):
    env = gis_rbac_env
    env["request"]("POST", f"/api/proyectos/{env['project']}/usuarios", expected=422,
                     json={"id_usuario": env["users"][name][0]["id_usuario"]})
    members = env["request"]("GET", f"/api/proyectos/{env['project']}/usuarios").json()
    assert {u["id_usuario"] for u in members} == {env["users"]["operador"][0]["id_usuario"]}


def test_anonymous_cannot_read_or_write_management(gis_rbac_env, monkeypatch):
    monkeypatch.delitem(app.dependency_overrides, auth.get_current_user)
    with TestClient(app) as client:
        for method, path, options in management_requests(gis_rbac_env):
            response = client.request(method, path, **options)
            assert response.status_code == 401, (method, path, response.text)
        p = gis_rbac_env["project"]
        for suffix in ("mapa", "mapa/indicadores"):
            assert client.get(f"/api/proyectos/{p}/{suffix}").status_code == 401


@pytest.mark.parametrize("name", ["operador", "operador_sin_asignacion", "visualizador"])
def test_non_gis_sessions_cannot_access_any_management_route(gis_rbac_env, monkeypatch, name):
    with logged_in(gis_rbac_env, monkeypatch, name) as (client, headers):
        for method, path, options in management_requests(gis_rbac_env):
            response = client.request(method, path, headers=headers, **options)
            assert response.status_code == 403, (name, method, path, response.text)
            assert response.json() == {"detail": "Operación no permitida para este rol"}
            assert "x-total-count" not in response.headers
        for path in ("/api/importaciones/2147483647", "/api/geoespacial/revisiones/2147483647"):
            assert client.get(path, params={"incluir_inactivas": True}).status_code == 403


@pytest.mark.parametrize("name", ["admin", "geografo"])
def test_gis_sessions_read_lists_details_geometries_and_revisions(gis_rbac_env, monkeypatch, name):
    with logged_in(gis_rbac_env, monkeypatch, name) as (client, _):
        for method, path, _ in management_requests(gis_rbac_env):
            if method == "GET":
                response = client.get(path)
                assert response.status_code == 200, (name, path, response.text)
        geometry = client.get(f"/api/importaciones/{gis_rbac_env['import_id']}/features/{gis_rbac_env['feature']}/geometria").json()
        assert geometry["geometry"] is not None


@pytest.mark.parametrize("name", ["admin", "geografo"])
def test_gis_session_can_record_revision_decision(gis_rbac_env, monkeypatch, name):
    env = gis_rbac_env
    with checkpoint(env), logged_in(env, monkeypatch, name) as (client, headers):
        response = client.post(f"/api/geoespacial/revisiones/{env['revision']}/decisiones", headers=headers,
            json={"accion": "revisado", "motivo": "Validación de rol GIS", "clave_solicitud": str(uuid.uuid4())})
        assert response.status_code == 201, response.text
        assert response.json()["creado_por"] == env["users"][name][0]["id_usuario"]


@pytest.mark.parametrize("name", ["admin", "geografo", "operador", "visualizador", "operador_sin_asignacion"])
def test_published_map_and_indicators_keep_project_read_scope(gis_rbac_env, monkeypatch, name):
    env = gis_rbac_env
    with logged_in(env, monkeypatch, name) as (client, _):
        for suffix, expected in (("mapa", env["map_json"]), ("mapa/indicadores", env["indicators"])):
            response = client.get(f"/api/proyectos/{env['project']}/{suffix}")
            assert response.status_code == (403 if name == "operador_sin_asignacion" else 200)
            if response.status_code == 200:
                assert response.json() == expected


@pytest.mark.parametrize("name", ["admin", "geografo", "operador", "visualizador"])
def test_inactive_project_blocks_management_and_public_map(gis_rbac_env, monkeypatch, name):
    env = gis_rbac_env
    with checkpoint(env):
        with env["session_factory"]() as db:
            set_audit_context(db, env["actor"])
            mark_inactive(db.get(models.Proyecto, env["project"]), env["actor"], "RBAC proyecto inactivo")
            db.commit()
        with logged_in(env, monkeypatch, name) as (client, headers):
            for method, path, _ in management_requests(env):
                if method == "GET":
                    assert client.get(path, params={"incluir_inactivas": True}).status_code == 403, (name, path)
            response = client.post(f"/api/geoespacial/revisiones/{env['revision']}/decisiones",
                headers=headers, json={"accion": "revisado", "motivo": "Proyecto inactivo",
                                       "clave_solicitud": str(uuid.uuid4())})
            assert response.status_code == 403, (name, response.text)
            for suffix in ("mapa", "mapa/indicadores"):
                assert client.get(f"/api/proyectos/{env['project']}/{suffix}").status_code == 403
            assert env["project"] not in {p["id_proyecto"] for p in client.get("/api/proyectos?limit=200").json()}


@pytest.mark.parametrize("name", ["admin", "geografo", "operador", "visualizador"])
def test_assignment_revocation_only_removes_operator_map_access(gis_rbac_env, monkeypatch, name):
    env = gis_rbac_env
    with checkpoint(env):
        with env["session_factory"]() as db:
            set_audit_context(db, env["actor"])
            link = db.query(models.UsuarioProyecto).filter_by(id_proyecto=env["project"],
                id_usuario=env["users"]["operador"][0]["id_usuario"], activo=True).one()
            mark_inactive(link, env["actor"], "RBAC revocación")
            db.commit()
        with logged_in(env, monkeypatch, name) as (client, _):
            for suffix in ("mapa", "mapa/indicadores"):
                assert client.get(f"/api/proyectos/{env['project']}/{suffix}").status_code == (403 if name == "operador" else 200)


@pytest.mark.parametrize("name", ["admin", "geografo"])
def test_direct_missing_or_foreign_identifiers_preserve_not_found(gis_rbac_env, monkeypatch, name):
    env = gis_rbac_env
    with logged_in(env, monkeypatch, name) as (client, _):
        for path in ("/api/importaciones/2147483647", "/api/importaciones/2147483647/features",
                     f"/api/importaciones/{env['import_id']}/features/2147483647/geometria",
                     f"/api/importaciones/{env['import_id']}/features/2147483647/decisiones",
                     f"/api/importaciones/{env['import_id']}/conciliaciones/2147483647",
                     "/api/geoespacial/revisiones/2147483647"):
            assert client.get(path).status_code == 404, (name, path)
        other = client.get(f"/api/proyectos/{env['project']}/importaciones").json()
        old_import = next(i["id_importacion"] for i in other if i["id_importacion"] != env["import_id"])
        assert client.get(f"/api/importaciones/{old_import}/features/{env['feature']}/geometria").status_code == 404
        assert client.get(f"/api/importaciones/{old_import}/conciliaciones/{env['cycle']}").status_code == 404
        assert client.get("/api/proyectos/2147483647/importaciones").status_code == 403


@pytest.mark.parametrize("name", ["admin", "geografo"])
def test_withdrawn_import_keeps_private_history_and_never_revives_published_geometry(gis_rbac_env, monkeypatch, name):
    env = gis_rbac_env
    with checkpoint(env):
        env["request"]("POST", f"/api/importaciones/{env['import_id']}/baja",
                         json={"motivo": "Validación de historial GIS privado"})
        with logged_in(env, monkeypatch, name) as (client, _):
            base = f"/api/importaciones/{env['import_id']}"
            assert client.get(base).status_code == 404
            history = {"incluir_inactivas": True}
            assert client.get(base, params=history).json()["activo"] is False
            assert client.get(f"{base}/features/{env['feature']}/geometria", params=history).json()["geometry"]
            assert client.get(f"{base}/conciliaciones/{env['cycle']}", params=history).status_code == 200
            assert client.get(f"/api/proyectos/{env['project']}/mapa").json()["features"] == []


def insert_decision(db, env, actor):
    return db.execute(text("""INSERT INTO revision_cambio_gis_decision
        (id_revision,accion,motivo,clave_solicitud,creado_por)
        VALUES (:revision,'revisado','RBAC directo',:key,:actor) RETURNING id_decision"""),
        {"revision": env["revision"], "key": str(uuid.uuid4()), "actor": actor}).scalar_one()


@pytest.mark.parametrize("name", ["admin", "geografo", "operador", "visualizador"])
def test_database_also_enforces_gis_roles_without_geographer_assignments(gis_rbac_env, name):
    env = gis_rbac_env
    with checkpoint(env), env["session_factory"]() as db:
        actor = env["users"][name][0]["id_usuario"]
        set_audit_context(db, actor)
        if name in {"admin", "geografo"}:
            assert insert_decision(db, env, actor) > 0
        else:
            with pytest.raises(DBAPIError, match="Decisión GIS requiere admin o geografo"):
                insert_decision(db, env, actor)
        db.rollback()


def test_database_still_rejects_forged_actor_and_inactive_project(gis_rbac_env):
    env = gis_rbac_env
    with checkpoint(env):
        with env["session_factory"]() as db:
            set_audit_context(db, env["actor"])
            with pytest.raises(DBAPIError, match="Decisión GIS requiere admin o geografo"):
                insert_decision(db, env, env["users"]["geografo"][0]["id_usuario"])
            db.rollback()
        with env["session_factory"]() as db:
            set_audit_context(db, env["actor"])
            mark_inactive(db.get(models.Proyecto, env["project"]), env["actor"], "DB RBAC inactivo")
            db.commit()
        with env["session_factory"]() as db:
            actor = env["users"]["geografo"][0]["id_usuario"]
            set_audit_context(db, actor)
            with pytest.raises(DBAPIError, match="Proyecto fuera del alcance autorizado"):
                insert_decision(db, env, actor)
            db.rollback()


def test_inactive_gis_user_cannot_reuse_session(gis_rbac_env, monkeypatch):
    env = gis_rbac_env
    with checkpoint(env), logged_in(env, monkeypatch, "geografo") as (client, _):
        with env["session_factory"]() as db:
            set_audit_context(db, env["actor"])
            user = db.get(models.Usuario, env["users"]["geografo"][0]["id_usuario"])
            mark_inactive(user, env["actor"], "RBAC usuario inactivo")
            db.commit()
        with env["session_factory"]() as db:
            actor = env["users"]["geografo"][0]["id_usuario"]
            set_audit_context(db, actor)
            with pytest.raises(DBAPIError, match="Decisión GIS requiere admin o geografo"):
                insert_decision(db, env, actor)
            db.rollback()
        for path in (f"/api/importaciones/{env['import_id']}",
                     f"/api/proyectos/{env['project']}/mapa", f"/api/proyectos/{env['project']}/mapa/indicadores"):
            assert client.get(path).status_code == 401, path
