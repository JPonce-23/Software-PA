"""F03 contract and loading regression against the frozen F02 implementation.

Run only on the dedicated tmpfs PostgreSQL with the versioned national fixture.
Authentication is excluded from direct measurements; HTTP tests retain RBAC.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
import statistics
import time
import tracemalloc
from types import SimpleNamespace
import uuid

from fastapi.testclient import TestClient
from pydantic import TypeAdapter
import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session, raiseload

from app import auth, models, schemas
from app.main import app
from app.routers import domain
from app.services.common import mark_inactive, set_audit_context
from tests.fixtures import f03_baseline as baseline

ROLES = ("admin", "operador", "visualizador", "geografo")
READS = ("list_states", "list_municipalities", "list_nuclei", "list_ran_nuclei_catalog")
SCHEMAS = dict(zip(READS, (schemas.EntidadFederativaResponse, schemas.MunicipioResponse,
                         schemas.NucleoAgrarioResponse, schemas.NucleoRanCatalogoResponse)))


@pytest.fixture(scope="module")
def territory_env(transactional_api):
    env = dict(transactional_api)
    with env["session_factory"]() as db:
        assert db.execute(text("SELECT current_database(),current_setting('cluster_name')")).one() == (
            "software_pa_test", "convenio-report-disposable")
        assert db.query(models.EntidadFederativa.id_entidad).count() == 32
        assert db.query(models.Municipio.id_municipio).count() == 2478
        assert db.query(models.NucleoAgrario.id_nucleo).filter_by(
            fuente_datos="RAN_PHINA_CATALOGO_NUCLEOS").count() >= 32278
        actor = app.dependency_overrides[auth.get_current_user]().id_usuario
        municipalities = db.query(models.Municipio.id_municipio, models.Municipio.id_entidad).order_by(
            models.Municipio.id_municipio).all()
        a = municipalities[0]
        b = next(m for m in municipalities if m.id_entidad != a.id_entidad)
        tenure = db.query(models.CatalogoOperativo.id_catalogo_opcion).filter_by(
            tipo_catalogo="tipo_tenencia", codigo="ejido").scalar()
        set_audit_context(db, actor)
        token = "F03" + uuid.uuid4().hex
        nuclei = [models.NucleoAgrario(id_municipio=(a if i < 2 else b).id_municipio,
                    nombre_nucleo=token + suffix, id_tipo_tenencia=tenure, creado_por=actor,
                    fuente_datos="RAN_PHINA_CATALOGO_NUCLEOS" if i != 1 else "QA_MANUAL",
                    id_entidad_fuente=str((a if i < 2 else b).id_entidad),
                    id_municipio_fuente=str((a if i < 2 else b).id_municipio),
                    id_nucleo_fuente=token + str(i), alcance_identidad_fuente="nacional")
                  for i, suffix in enumerate((" A %_\\", " B manual", " C otro"))]
        projects = [models.Proyecto(clave_proyecto=uuid.uuid4().hex[:25],
                    nombre_proyecto=token + str(i), creado_por=actor) for i in range(2)]
        db.add_all(nuclei + projects); db.flush()
        pns = [models.ProyectoNucleo(id_proyecto=projects[p].id_proyecto,
               id_nucleo=nuclei[n].id_nucleo, creado_por=actor) for p, n in ((0, 0), (1, 0), (1, 2))]
        db.add_all(pns)
        users = {}
        for role in ROLES:
            user = models.Usuario(nombre="F03", apellido_paterno="QA", rol=role,
                    correo=uuid.uuid4().hex + "@local.invalid", contrasena_hash="unused-fixture",
                    fecha_alta=datetime.now(timezone.utc))
            db.add(user); db.flush()
            users[role] = SimpleNamespace(id_usuario=user.id_usuario, rol=role)
            if role != "admin":
                db.add(models.UsuarioProyecto(id_usuario=user.id_usuario, id_proyecto=projects[0].id_proyecto,
                       asignado_por=actor, creado_por=actor))
        db.commit()
        env.update(actor=actor, token=token, municipalities=(a, b), users=users,
                   nuclei=[n.id_nucleo for n in nuclei], projects=[p.id_proyecto for p in projects],
                   pns=[p.id_proyecto_nucleo for p in pns])
    return env


def arguments(env, name, **overrides):
    result = {"list_states": {}, "list_municipalities": {"id_entidad":None},
              "list_nuclei": {"id_municipio":None, "skip":0, "limit":100},
              "list_ran_nuclei_catalog": {"id_entidad":None, "id_municipio":None, "q":None, "limit":20}}[name]
    result["user" if name == "list_nuclei" else "_"] = env["users"]["admin"]
    result.update(overrides)
    return result


def measure(env, name, original, *, memory=False, **overrides):
    phase = ["functional"]
    stats = {key:{"sql":0,"objects":0} for key in ("functional", "serialization")}
    def sql(conn, cursor, statement, params, context, many):
        if statement.lstrip().upper().startswith(("SELECT", "WITH")):
            stats[phase[0]]["sql"] += 1
    def loaded(session, instance):
        stats[phase[0]]["objects"] += 1
    adapter = TypeAdapter(list[SCHEMAS[name]])
    gc.collect()
    if memory:
        tracemalloc.start()
    event.listen(env["connection"], "before_cursor_execute", sql)
    event.listen(Session, "loaded_as_persistent", loaded)
    try:
        with env["session_factory"]() as db:
            start = time.perf_counter()
            rows = getattr(baseline if original else domain, name)(db=db, **arguments(env,name,**overrides))
            elapsed = (time.perf_counter()-start)*1000
            retained = len(db.identity_map)
            phase[0] = "serialization"
            payload = adapter.dump_json(adapter.validate_python(rows))
            sample = {"ms":elapsed, "phases":stats, "retained":retained,
                      "rows":len(rows), "bytes":len(payload), "sha256":hashlib.sha256(payload).hexdigest()}
            if memory:
                sample["peak_python_bytes"] = tracemalloc.get_traced_memory()[1]
            return sample, json.loads(payload)
    finally:
        event.remove(env["connection"], "before_cursor_execute", sql)
        event.remove(Session, "loaded_as_persistent", loaded)
        if memory:
            tracemalloc.stop()


def save(name, value, *, overwrite=True):
    if os.getenv("F03_EVIDENCE_DIR"):
        path=Path(os.environ["F03_EVIDENCE_DIR"])/name
        if overwrite or not path.exists():
            path.write_text(json.dumps(value,indent=2))


def test_baseline_before_changes(territory_env):
    results = {name:measure(territory_env,name,True)[0] for name in READS}
    save("baseline.json", results, overwrite=False)
    save("openapi-before.json", app.openapi(), overwrite=False)


def test_national_benchmark(territory_env):
    results = {}
    for name in READS:
        samples = {"original":[], "optimized":[]}
        for original in (True,False):
            measure(territory_env,name,original)
        for i in range(5):
            payloads = []
            for original in ((True,False) if i%2 == 0 else (False,True)):
                sample, payload = measure(territory_env,name,original)
                samples["original" if original else "optimized"].append(sample)
                payloads.append(payload)
                assert sample["phases"]["serialization"] == {"sql":0,"objects":0}
                if not original:
                    assert sample["phases"]["functional"]["sql"] == 1
                    assert sample["phases"]["functional"]["objects"] == (0 if name == READS[-1] else sample["rows"])
            assert payloads[0] == payloads[1]
        results[name] = {key:{"median_ms":statistics.median(s["ms"] for s in values), "samples":values,
                             "memory_sample":measure(territory_env,name,key=="original",memory=True)[0]}
                         for key,values in samples.items()}
    save("comparison.json", results)
    print("F03_MEDIANS=" + json.dumps({k:{v:x["median_ms"] for v,x in row.items()} for k,row in results.items()}))


@contextmanager
def original_reads(monkeypatch):
    calls = []
    def wrap(fn):
        def call(**kwargs):
            calls.append(fn.__name__)
            return fn(**kwargs)
        return call
    with monkeypatch.context() as patch:
        for route in app.routes:
            candidates = route.effective_route_contexts() if hasattr(route,"effective_route_contexts") else [route]
            for candidate in candidates:
                dep = getattr(candidate,"dependant",None)
                name = getattr(getattr(dep,"call",None),"__name__",None)
                if name in READS:
                    patch.setattr(dep,"call",wrap(getattr(baseline,name)))
        yield calls


@pytest.mark.parametrize("role", ROLES)
def test_http_json_and_roles(territory_env, monkeypatch, role):
    env=territory_env
    monkeypatch.setitem(app.dependency_overrides,auth.get_current_user,lambda:env["users"][role])
    paths = ["/api/catalogos/entidades", "/api/catalogos/municipios?id_entidad=2",
             "/api/nucleos?limit=200", "/api/nucleos?skip=1&limit=1",
             "/api/catalogos/nucleos?q=" + env["token"]]
    with TestClient(app) as client:
        with original_reads(monkeypatch) as calls:
            before = [(r.status_code,r.content) for path in paths for r in [client.get(path)]]
        after = [(r.status_code,r.content) for path in paths for r in [client.get(path)]]
        assert len(calls) == len(paths)
        assert after == before
        assert {code for code,_ in after} == {200}
        assert len(json.loads(after[0][1])) == 32
        assert len(json.loads(after[-1][1])) == 2  # national RAN includes unassigned nucleus
        visible={r["id_nucleo"] for r in json.loads(after[2][1])}
        if role != "admin":
            assert visible == {env["nuclei"][0]}


@pytest.mark.parametrize("state", ["normal","revoked","project_inactive","pn_inactive", "nucleus_inactive",
                                    "municipality_inactive","state_inactive"])
@pytest.mark.parametrize("role", ROLES)
def test_visibility_and_inactive_semantics(territory_env, state, role):
    env=territory_env
    transaction=env["connection"].begin_nested()
    try:
        with env["session_factory"]() as db:
            set_audit_context(db,env["actor"])
            if state == "revoked" and role != "admin":
                obj=db.query(models.UsuarioProyecto).filter_by(id_usuario=env["users"][role].id_usuario).one()
            elif state not in ("normal","revoked"):
                model, identity={"project_inactive":(models.Proyecto,env["projects"][0]),
                    "pn_inactive":(models.ProyectoNucleo,env["pns"][0]),
                    "nucleus_inactive":(models.NucleoAgrario,env["nuclei"][0]),
                    "municipality_inactive":(models.Municipio,env["municipalities"][0].id_municipio),
                    "state_inactive":(models.EntidadFederativa,env["municipalities"][0].id_entidad)}[state]
                obj=db.query(model).options(raiseload("*")).filter(model.__mapper__.primary_key[0]==identity).one()
            else:
                obj=None
            if obj is not None:
                mark_inactive(obj,env["actor"],"Estado F03 sintético")
                db.commit()
        options={"user":env["users"][role],"limit":200}
        _, expected=measure(env,"list_nuclei",True,**options)
        after, actual=measure(env,"list_nuclei",False,**options)
        assert actual == expected
        assert after["phases"]["functional"] == {"sql":1,"objects":len(actual)}
        assert after["phases"]["serialization"]["sql"] == 0
        if role != "admin":
            visible = state not in ("revoked","project_inactive","pn_inactive","nucleus_inactive")
            assert {r["id_nucleo"] for r in actual} == ({env["nuclei"][0]} if visible else set())
        for name,options in (("list_municipalities",{"id_entidad":env["municipalities"][0].id_entidad}),
                             ("list_ran_nuclei_catalog",{"q":env["token"]})):
            expected=measure(env,name,True,**options)[1]
            actual=measure(env,name,False,**options)[1]
            assert actual == expected
            if name == "list_ran_nuclei_catalog":
                assert len(actual) == (1 if state == "nucleus_inactive" else 2)
            if name == "list_municipalities" and state == "municipality_inactive":
                assert env["municipalities"][0].id_municipio not in {r["id_municipio"] for r in actual}
        if state == "state_inactive":
            expected=measure(env,"list_states",True)[1]
            assert measure(env,"list_states",False)[1] == expected
            assert len(expected) == 31
    finally:
        transaction.rollback()


@pytest.mark.parametrize("name,options", [
    ("list_municipalities",{"id_entidad":2147483647}),
    ("list_municipalities",{"id_entidad":-1}),
    ("list_nuclei",{"id_municipio":2147483647}),
    ("list_nuclei",{"skip":50000}),
    ("list_nuclei",{"skip":2,"limit":3}),
    ("list_ran_nuclei_catalog",{"id_entidad":1,"id_municipio":2}),
    ("list_ran_nuclei_catalog",{"id_entidad":2147483647}),
    ("list_ran_nuclei_catalog",{"q":"   "}),
    ("list_ran_nuclei_catalog",{"q":"%_\\"}),
    ("list_ran_nuclei_catalog",{"id_entidad":2,"limit":100}),
])
def test_filters_order_and_pagination(territory_env,name,options):
    assert measure(territory_env,name,True,**options)[1] == measure(territory_env,name,False,**options)[1]


@pytest.mark.parametrize("path", ["/api/nucleos?skip=-1", "/api/nucleos?limit=201", "/api/nucleos?limit=0",
    "/api/nucleos?id_municipio=abc", "/api/catalogos/municipios?id_entidad=abc",
    "/api/catalogos/nucleos?id_entidad=0", "/api/catalogos/nucleos?limit=101", "/api/catalogos/nucleos?q="])
def test_invalid_parameters(territory_env,monkeypatch,path):
    with TestClient(app) as client:
        with original_reads(monkeypatch):
            before=client.get(path)
        after=client.get(path)
        assert after.status_code == before.status_code == 422
        assert after.json() == before.json()


@pytest.mark.parametrize("path", ["/api/catalogos/entidades", "/api/catalogos/municipios",
                                  "/api/nucleos", "/api/catalogos/nucleos"])
def test_real_auth_required(territory_env,monkeypatch,path):
    monkeypatch.delitem(app.dependency_overrides,auth.get_current_user)
    with TestClient(app) as client:
        with original_reads(monkeypatch):
            before=client.get(path)
        after=client.get(path)
        assert after.status_code == before.status_code == 401
        assert after.json() == before.json()


@pytest.mark.parametrize("name,relation", [("list_states","municipios"),
                                         ("list_municipalities","nucleos"), ("list_nuclei","proyectos")])
def test_relationships_are_guarded_locally(territory_env,name,relation):
    with territory_env["session_factory"]() as db:
        rows=getattr(domain,name)(db=db,**arguments(territory_env,name))
        with pytest.raises(InvalidRequestError):
            getattr(rows[0],relation)


def test_openapi_unchanged(territory_env):
    evidence=os.getenv("F03_BASELINE_OPENAPI")
    if evidence:
        assert app.openapi() == json.loads(Path(evidence).read_text())
    assert schemas.NucleoAgrarioResponse.model_fields["geometria_wkt"].default is None
