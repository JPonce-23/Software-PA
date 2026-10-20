"""F02: compare the frozen F01 policy and ten reads on disposable PostgreSQL."""
from contextlib import contextmanager
from datetime import date, datetime, timezone
import inspect as python_inspect
import json
import os
from pathlib import Path
import statistics
import time
from types import SimpleNamespace
import uuid

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import TypeAdapter
import pytest
from sqlalchemy import event, inspect, text
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.config import AUTH_SETTINGS
from app.main import app
from app.routers import domain
from app.services import access
from app.services.authentication import hash_password
from app.services.common import mark_inactive, set_audit_context
from tests.fixtures import f02_baseline as baseline


ROLES = ("admin", "operador", "visualizador", "geografo")
READS = ("get_project", "list_project_nuclei", "get_project_nucleus", "list_references",
         "list_activities", "list_affectations", "list_assemblies", "list_ran_procedures",
         "list_agreements", "list_fifonafe")
CONTEXTS = ("require_project_access", "require_project_nucleus_access", "require_affectation_access")


@pytest.fixture(scope="module")
def context_env(transactional_api):
    env = dict(transactional_api)
    api, factory = env["request"], env["session_factory"]
    with factory() as db:
        assert db.execute(text("SELECT current_database(),current_setting('cluster_name')")).one() == (
            "software_pa_test", "convenio-report-disposable",
        ), "Use únicamente el PostgreSQL local desechable"
    def create(path, **body):
        return api("POST", path, expected=201, json=body).json()
    def catalog(kind):
        return {r["codigo"]: r["id_catalogo_opcion"] for r in api("GET", f"/api/catalogos/operativos/{kind}").json()}
    projects = [create("/api/proyectos", clave_proyecto=uuid.uuid4().hex[:25],
                       nombre_proyecto=f"Contexto F02 {i} {uuid.uuid4().hex[:8]}") for i in range(2)]
    nuclei = [create("/api/nucleos", id_municipio=1, nombre_nucleo="F02 " + uuid.uuid4().hex,
                     id_tipo_tenencia=catalog("tipo_tenencia")["ejido"]) for _ in range(2)]
    pns = [create(f"/api/proyectos/{p['id_proyecto']}/nucleos", id_nucleo=nuclei[0]["id_nucleo"],
                  referencias=[{"tipo_referencia":"consecutivo", "valor":uuid.uuid4().hex}])
           for p in projects]
    pns.append(create(f"/api/proyectos/{projects[0]['id_proyecto']}/nucleos", id_nucleo=nuclei[1]["id_nucleo"]))
    affects = [create(f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/afectaciones", tipo_afectacion="colectivo",
                       id_tipo_cop_operativo=catalog("tipo_cop_operativo")["ORIGEN"], superficie_afectada_ha="1.1234567")
               for pn in pns]
    populated = create(f"/api/proyecto-nucleo/{pns[0]['id_proyecto_nucleo']}/afectaciones", tipo_afectacion="colectivo",
                       id_tipo_cop_operativo=catalog("tipo_cop_operativo")["ORIGEN"])
    assembly = create(f"/api/proyecto-nucleo/{pns[0]['id_proyecto_nucleo']}/asambleas",
                      id_tipo_asamblea=catalog("tipo_asamblea")["anuencia"],
                      convocatorias=[{"ordinal":1,"fecha_realizacion":"2026-01-01",
                                      "id_resultado":catalog("resultado_convocatoria")["celebrada"]}])
    agreement = create(f"/api/afectaciones/{populated['id_afectacion']}/convenios", tipo_convenio="cop_original",
                       id_asamblea_autorizacion=assembly["id_asamblea"], fecha_firma="2026-01-02",
                       monto_100="1234.56", superficie_ha="1.1234567")
    create("/api/tramites-ran", id_asamblea=assembly["id_asamblea"], eventos=[
        {"ordinal":1,"id_tipo_evento":catalog("tipo_evento_ran")["ingreso"],"fecha_evento":"2026-01-03"}])
    create(f"/api/proyecto-nucleo/{pns[0]['id_proyecto_nucleo']}/fifonafe",
           ids_afectacion=[populated["id_afectacion"]], eventos=[
               {"ordinal":1,"id_tipo_evento":catalog("tipo_evento_fifonafe")["consulta_conflictos_enviada"],
                "fecha_oficio":"2026-01-04","numero_oficio":"F02-SINTETICO"}])
    for i in range(3):
        create(f"/api/proyecto-nucleo/{pns[0]['id_proyecto_nucleo']}/actividades", tipo_actividad="sensibilizacion",
               fecha_realizada="2026-01-05" if i else None, resultado=f"Actividad sintética {i}")
    with factory() as db:
        actor = app.dependency_overrides[auth.get_current_user]().id_usuario
        set_audit_context(db, actor)
        password = "QaF02!1" + uuid.uuid4().hex
        users = {}
        for role in ROLES:
            user = models.Usuario(nombre="F02", apellido_paterno="Sintético", rol=role,
                                  correo=f"f02-{uuid.uuid4().hex}@local.invalid", contrasena_hash=hash_password(password),
                                  fecha_alta=datetime.now(timezone.utc), activo=True)
            db.add(user); db.flush()
            users[role] = SimpleNamespace(id_usuario=user.id_usuario, rol=role, correo=user.correo)
            if role == "operador":
                db.add(models.UsuarioProyecto(id_usuario=user.id_usuario, id_proyecto=projects[0]["id_proyecto"],
                                               asignado_por=actor, creado_por=actor))
        db.commit()
    env.update(projects=projects, nuclei=nuclei, pns=pns, affects=affects, populated=populated,
               agreement=agreement, users=users, password=password, actor=actor)
    return env


def arguments(env, side=0):
    return {"id_proyecto":env["projects"][side]["id_proyecto"],
            "id_proyecto_nucleo":env["pns"][side]["id_proyecto_nucleo"],
            "id_afectacion":env["affects"][side]["id_afectacion"]}


def kwargs_for(function, env, user, side=0):
    available = {**arguments(env, side), "skip":0, "limit":100, "id_entidad":None,
                 "id_municipio":None, "tipo":None, "user":user}
    return {key:value for key,value in available.items() if key in python_inspect.signature(function).parameters}


@contextmanager
def checkpoint(env):
    transaction = env["connection"].begin_nested()
    try:
        yield
    finally:
        transaction.rollback()


def mutate(env, state, user):
    if state in ("normal", "unassigned", "missing"):
        return
    with env["session_factory"]() as db:
        set_audit_context(db, env["actor"])
        if state == "revoked":
            if user.rol != "operador":
                return
            obj = db.query(models.UsuarioProyecto).filter_by(id_usuario=user.id_usuario, activo=True).one()
        else:
            model, identity = {
                "project_inactive":(models.Proyecto, env["projects"][0]["id_proyecto"]),
                "pn_inactive":(models.ProyectoNucleo, env["pns"][0]["id_proyecto_nucleo"]),
                "aff_inactive":(models.Afectacion, env["affects"][0]["id_afectacion"]),
                "nucleus_inactive":(models.NucleoAgrario, env["nuclei"][0]["id_nucleo"]),
            }[state]
            obj = db.get(model, identity)
        mark_inactive(obj, env["actor"], "Estado sintético F02")
        db.commit()


def context_result(env, name, user, *, original, state="normal"):
    module = baseline if original else access
    fn = getattr(module, name)
    index = CONTEXTS.index(name)
    identity = list(arguments(env).values())[index]
    if state == "missing":
        identity = 2147483647
    if state == "unassigned":
        identity = list(arguments(env, 1).values())[index]
    options = {"load_details":False} if not original and "load_details" in python_inspect.signature(fn).parameters else {}
    with env["session_factory"]() as db:
        try:
            row = fn(db, user, identity, **options)
            return (200, {c.key:getattr(row,c.key) for c in inspect(row).mapper.column_attrs})
        except HTTPException as exc:
            return exc.status_code, exc.detail


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("name", CONTEXTS)
@pytest.mark.parametrize("state", ["normal","unassigned","revoked","project_inactive","pn_inactive",
                                   "aff_inactive","nucleus_inactive","missing"])
def test_context_decisions_and_columns(context_env, role, name, state):
    user = context_env["users"][role]
    with checkpoint(context_env):
        mutate(context_env, state, user)
        expected = context_result(context_env,name,user,original=True,state=state)
        actual = context_result(context_env,name,user,original=False,state=state)
        assert actual == expected
        if state == "normal":
            assert actual[0] == 200
        if state in ("unassigned","revoked") and role == "operador":
            assert actual[0] == 403
        elif state in ("unassigned","revoked") and role in {"visualizador","geografo"}:
            assert actual[0] == 200
        if state == "missing":
            assert actual[0] == (403 if name == CONTEXTS[0] else 404)


@contextmanager
def original_reads(monkeypatch):
    calls = []
    def wrapped(function):
        def call(**kwargs):
            calls.append(function.__name__)
            return function(**kwargs)
        return call
    with monkeypatch.context() as patch:
        for route in app.routes:
            candidates = route.effective_route_contexts() if hasattr(route,"effective_route_contexts") else [route]
            for candidate in candidates:
                dependant = getattr(candidate,"dependant",None)
                if dependant is not None and getattr(dependant.call,"__name__",None) in READS:
                    patch.setattr(dependant,"call",wrapped(getattr(baseline,dependant.call.__name__)))
        yield calls


def paths(env, *, side=0, missing=False):
    ids = arguments(env,side)
    if missing:
        ids = dict.fromkeys(ids,2147483647)
    p,n,a = ids.values()
    return [f"/api/proyectos/{p}", f"/api/proyectos/{p}/nucleos", f"/api/proyecto-nucleo/{n}",
            f"/api/proyecto-nucleo/{n}/referencias", f"/api/proyecto-nucleo/{n}/actividades",
            f"/api/proyecto-nucleo/{n}/afectaciones", f"/api/proyecto-nucleo/{n}/asambleas",
            f"/api/proyecto-nucleo/{n}/tramites-ran", f"/api/afectaciones/{a}/convenios",
            f"/api/proyecto-nucleo/{n}/fifonafe"]


def responses(client, urls):
    return [(r.status_code,r.content) for r in (client.get(url) for url in urls)]


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("state", ["normal","unassigned","revoked","project_inactive","pn_inactive",
                                   "aff_inactive","nucleus_inactive","missing"])
def test_http_bytes_and_status(context_env,monkeypatch,role,state):
    user = context_env["users"][role]
    monkeypatch.setitem(app.dependency_overrides,auth.get_current_user,lambda:user)
    with checkpoint(context_env), TestClient(app,raise_server_exceptions=True) as client:
        mutate(context_env,state,user)
        urls = paths(context_env,side=int(state=="unassigned"),missing=state=="missing")
        urls += [f"/api/afectaciones/{context_env['populated']['id_afectacion']}/convenios",
                 paths(context_env)[4]+"?tipo=caminamiento", paths(context_env)[1]+"?limit=1&skip=1"]
        with original_reads(monkeypatch) as called:
            expected = responses(client,urls)
        assert called
        assert responses(client,urls) == expected


@pytest.mark.parametrize("role", ROLES)
def test_real_auth_invalid_sessions_and_inactive_users(context_env,monkeypatch,role):
    monkeypatch.delitem(app.dependency_overrides,auth.get_current_user)
    user = context_env["users"][role]
    with checkpoint(context_env), TestClient(app,raise_server_exceptions=True) as client:
        urls = paths(context_env)
        for token in (None,"f02-invalid-session-token"):
            if token:
                client.cookies.set(AUTH_SETTINGS.session_cookie_name,token)
            with original_reads(monkeypatch):
                expected = responses(client,urls)
            assert responses(client,urls) == expected
            assert {status for status,body in expected} == {401}
        client.cookies.clear()
        login = client.post("/api/auth/sesiones",data={"username":user.correo,"password":context_env["password"]},
                            headers={"Origin":AUTH_SETTINGS.allowed_origins[0]})
        assert login.status_code == 200, login.text
        with original_reads(monkeypatch):
            expected = responses(client,urls+paths(context_env,side=1))
        assert responses(client,urls+paths(context_env,side=1)) == expected
        with context_env["session_factory"]() as db:
            set_audit_context(db,context_env["actor"])
            account = db.get(models.Usuario,user.id_usuario)
            account.activo=False
            account.fecha_baja=datetime.now(timezone.utc)
            account.id_usuario_baja=context_env["actor"]
            account.motivo_baja="Usuario inactivo F02"
            db.commit()
        with original_reads(monkeypatch):
            expected = responses(client,urls)
        assert responses(client,urls) == expected
        assert {status for status,body in expected} == {401}


@contextmanager
def instrumentation(env,monkeypatch,original):
    module = baseline if original else access
    phase = ["functional"]
    stats = {}
    def counter(key):
        return stats.setdefault(phase[0],{"sql":0,"objects_loaded":0})
    def sql(conn,cursor,statement,params,context,many):
        if statement.lstrip().upper().startswith(("SELECT","WITH")):
            counter("sql")["sql"] += 1
    def loaded(session,instance):
        counter("objects_loaded")["objects_loaded"] += 1
    def wrap(fn,name):
        def call(*args,**kwargs):
            previous=phase[0]; phase[0]="authorization."+name
            try:
                return fn(*args,**kwargs)
            finally:
                phase[0]=previous
        return call
    with monkeypatch.context() as patch:
        for name in CONTEXTS:
            replacement=wrap(getattr(module,name),name)
            patch.setattr(module,name,replacement)
            if not original:
                patch.setattr(domain,name,replacement)
        event.listen(env["connection"],"before_cursor_execute",sql)
        event.listen(Session,"loaded_as_persistent",loaded)
        try:
            yield stats,phase
        finally:
            event.remove(env["connection"],"before_cursor_execute",sql)
            event.remove(Session,"loaded_as_persistent",loaded)


def measure(env,monkeypatch,name,original):
    user=env["users"]["admin"]
    fn=getattr(baseline if original else domain,name,None)
    context=name in CONTEXTS
    if context:
        fn=getattr(baseline if original else access,name)
    with env["session_factory"]() as db, instrumentation(env,monkeypatch,original) as (stats,phase):
        start=time.perf_counter()
        if context:
            phase[0]="authorization."+name
            index=CONTEXTS.index(name)
            options={"load_details":False} if not original and "load_details" in python_inspect.signature(fn).parameters else {}
            result=fn(db,user,list(arguments(env).values())[index],**options)
        else:
            result=fn(db=db,**kwargs_for(fn,env,user))
        wall_ms=(time.perf_counter()-start)*1000
        retained=len(db.identity_map)
        phase[0]="serialization"
        if context:
            payload={c.key:getattr(result,c.key) for c in inspect(result).mapper.column_attrs}
        else:
            schema={"list_agreements":schemas.ConvenioResponse,"list_activities":schemas.ActividadCampoResponse,
                    "list_assemblies":schemas.AsambleaResponse,"list_ran_procedures":schemas.TramiteRanResponse,
                    "list_fifonafe":schemas.TramiteFifonafeResponse}[name]
            payload=TypeAdapter(list[schema]).dump_python(TypeAdapter(list[schema]).validate_python(result),mode="json")
        return {"wall_ms":wall_ms,"objects_retained":retained,"phases":stats},payload


PATTERNS=(*CONTEXTS,"list_agreements","list_activities","list_assemblies","list_ran_procedures","list_fifonafe")


def test_baseline_measurements(context_env,monkeypatch):
    result={}
    for name in PATTERNS:
        measure(context_env,monkeypatch,name,True)
        samples=[measure(context_env,monkeypatch,name,True)[0] for _ in range(7)]
        result[name]={"median_ms":statistics.median(s["wall_ms"] for s in samples),"samples":samples}
    if os.getenv("F02_EVIDENCE_DIR"):
        (Path(os.environ["F02_EVIDENCE_DIR"])/"baseline.json").write_text(json.dumps(result,indent=2))
    print("F02_BASELINE="+json.dumps({k:v["median_ms"] for k,v in result.items()}))


def test_benchmark_and_minimal_loading(context_env,monkeypatch):
    result={}
    for name in PATTERNS:
        variants={"original":[],"optimized":[]}
        for original in (True,False):
            measure(context_env,monkeypatch,name,original)
        for i in range(7):
            payloads=[]
            for original in ((True,False) if i%2==0 else (False,True)):
                sample,payload=measure(context_env,monkeypatch,name,original)
                variants["original" if original else "optimized"].append(sample)
                payloads.append(payload)
            assert payloads[0]==payloads[1]
        for variant,samples in variants.items():
            for sample in samples:
                assert sample["phases"].get("serialization",{}).get("sql",0)==0
                if variant=="optimized":
                    authz=[v for k,v in sample["phases"].items() if k.startswith("authorization.")]
                    depth=3 if name in (CONTEXTS[2],"list_agreements") else 1 if name==CONTEXTS[0] else 2
                    assert sum(s["sql"] for s in authz)==depth
                    assert sum(s["objects_loaded"] for s in authz)==depth
        result[name]={k:{"median_ms":statistics.median(s["wall_ms"] for s in samples),"samples":samples}
                      for k,samples in variants.items()}
    if os.getenv("F02_EVIDENCE_DIR"):
        (Path(os.environ["F02_EVIDENCE_DIR"])/"comparison.json").write_text(json.dumps(result,indent=2))
    print("F02_COMPARISON="+json.dumps({k:{v:x["median_ms"] for v,x in value.items()} for k,value in result.items()}))


@pytest.mark.parametrize("name",CONTEXTS)
def test_minimal_guards_and_cost_independent_of_children(context_env,monkeypatch,name):
    user=context_env["users"]["admin"]
    with checkpoint(context_env):
        before,_=measure(context_env,monkeypatch,name,False)
        with context_env["session_factory"]() as db:
            set_audit_context(db,context_env["actor"])
            db.add_all([models.ActividadCampo(id_proyecto_nucleo=context_env["pns"][0]["id_proyecto_nucleo"],
                        tipo_actividad="sensibilizacion",resultado=f"Crecimiento F02 {i}",creado_por=context_env["actor"])
                        for i in range(60)])
            db.commit()
        after,payload=measure(context_env,monkeypatch,name,False)
        old,expected=measure(context_env,monkeypatch,name,True)
        assert payload==expected
        assert before["phases"]==after["phases"]
        assert sum(v["objects_loaded"] for v in old["phases"].values())>sum(v["objects_loaded"] for v in after["phases"].values())
        with context_env["session_factory"]() as db:
            row=getattr(access,name)(db,user,list(arguments(context_env).values())[CONTEXTS.index(name)],load_details=False)
            relation=("nucleos","actividades","unidades_agrarias")[CONTEXTS.index(name)]
            with pytest.raises(InvalidRequestError):
                getattr(row,relation)


@pytest.mark.parametrize("name",CONTEXTS)
@pytest.mark.parametrize("role",ROLES)
@pytest.mark.parametrize("mode",["read","capture","gis"])
def test_default_loading_and_write_modes_unchanged(context_env,name,role,mode):
    user=context_env["users"][role]
    identity=list(arguments(context_env).values())[CONTEXTS.index(name)]
    outcomes=[]
    for module in (baseline,access):
        with context_env["session_factory"]() as db:
            try:
                row=getattr(module,name)(db,user,identity,mode=mode)
                outcomes.append((200,{c.key:getattr(row,c.key) for c in inspect(row).mapper.column_attrs},inspect(row).unloaded))
            except HTTPException as exc:
                outcomes.append((exc.status_code,exc.detail))
    assert outcomes[0]==outcomes[1]
