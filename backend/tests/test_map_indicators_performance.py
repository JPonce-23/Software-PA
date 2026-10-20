"""F05: real PostgreSQL comparison against the public map's original traversal.

Uses the F04 shared-convenio fixture, but deliberately reads ALL nuclei, not 100.
Every operational record is inside transactional_api's outer rollback.
"""
from contextlib import ExitStack
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import statistics
import time
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import TypeAdapter
import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session, raiseload

from app import auth, models, schemas
from app.main import app
from app.config import AUTH_SETTINGS
from app.routers import domain, reporting
from app.services import access
from app.services.common import mark_inactive, set_audit_context
from app.services.authentication import hash_password
from tests.test_dashboard_summary_performance import dashboard_env, ROLES


@pytest.fixture(scope="module")
def map_env(dashboard_env):
    env=dict(dashboard_env)
    with env["session_factory"]() as db:
        set_audit_context(db,env["actor"])
        def catalog(kind,code):
            return db.query(models.CatalogoOperativo.id_catalogo_opcion).filter_by(
                tipo_catalogo=kind,codigo=code).scalar()
        celebrated=catalog("resultado_convocatoria","celebrada")
        cancelled=catalog("resultado_convocatoria","cancelada")
        assembly_type=catalog("tipo_asamblea","otra")
        shared=db.query(models.ProyectoNucleo.id_proyecto_nucleo).filter_by(
            id_proyecto=env["projects"][3]).scalar()
        assemblies=[];convocations=[]
        # Including a nucleus with no affectations and nucleus 105 of the large project.
        for pn in (env["pns"][0],env["pns"][1],env["pns"][2],env["pns"][-1],shared):
            a=models.Asamblea(id_proyecto_nucleo=pn,id_tipo_asamblea=assembly_type,
                              resultado=None,creado_por=env["actor"])
            db.add(a);db.flush();assemblies.append(a.id_asamblea)
            for ordinal,result,day in ((1,cancelled,None),(2,celebrated,date(2026,1,2)),(3,None,None)):
                c=models.AsambleaConvocatoria(id_asamblea=a.id_asamblea,ordinal=ordinal,
                    id_resultado=result,fecha_realizacion=day,creado_por=env["actor"])
                db.add(c);db.flush();convocations.append(c.id_convocatoria)
        # Null result and no date are valid, and never count as celebrated.
        blank=models.Asamblea(id_proyecto_nucleo=env["pns"][0],id_tipo_asamblea=assembly_type,
                              creado_por=env["actor"])
        db.add(blank);db.commit()
        env.update(assemblies=assemblies,convocations=convocations,celebrated=celebrated)
    return env


def original(db,user,project):
    """Exact predicates of mapa.js at 0ce1743, using unchanged legacy APIs."""
    nuclei=[];skip=0
    while True:
        page=domain.list_project_nuclei(project,db=db,user=user,skip=skip,limit=200)
        nuclei.extend(page)
        if len(page)<200:break
        skip+=200
    catalog=domain.list_operational_catalog("resultado_convocatoria",False,db=db,_=user)
    celebrated={r.id_catalogo_opcion for r in catalog if r.codigo=="celebrada"}
    assemblies=set();unique={}
    for n in nuclei:
        for a in domain.list_assemblies(n.id_proyecto_nucleo,db=db,user=user):
            if a.activo and any(c.activo and c.fecha_realizacion and c.id_resultado in celebrated for c in a.convocatorias):
                assemblies.add(a.id_asamblea)
        for a in domain.list_affectations(n.id_proyecto_nucleo,db=db,user=user):
            for c in domain.list_agreements(a.id_afectacion,db=db,user=user):
                if c.activo and c.fecha_firma:unique[c.id_convenio]=c
    individual=sum(c.ambito=="individual" for c in unique.values())
    collective=sum(c.ambito=="colectivo" for c in unique.values())
    return dict(asambleas_realizadas=len(assemblies) if celebrated else None,
                convenios_individuales=individual,convenios_colectivos=collective,
                convenios_firmados=individual+collective)


def measure(env,project,legacy,user=None):
    phase=["functional"];stats={"authorization":0,"functional":0,"serialization":0,"objects":0}
    def sql(conn,cursor,statement,params,context,many):
        if statement.lstrip().upper().startswith(("SELECT","WITH")):stats[phase[0]]+=1
    def loaded(session,instance):stats["objects"]+=1
    event.listen(env["connection"],"before_cursor_execute",sql)
    event.listen(Session,"loaded_as_persistent",loaded)
    try:
        with ExitStack() as stack,env["session_factory"]() as db:
            def guard(fn):
                def wrapped(*args,**kwargs):
                    previous=phase[0];phase[0]="authorization"
                    try:return fn(*args,**kwargs)
                    finally:phase[0]=previous
                return wrapped
            for module in (domain,reporting,access):
                for name in ("require_project_access","require_project_nucleus_access","require_affectation_access"):
                    if hasattr(module,name):stack.enter_context(patch.object(module,name,guard(getattr(module,name))))
            start=time.perf_counter()
            payload=(original if legacy else reporting.map_indicators)(
                db=db,user=user or env["users"]["admin"],**({"project":project} if legacy else {"id_proyecto":project}))
            phase[0]="serialization"
            if not legacy:
                adapter=TypeAdapter(schemas.MapaIndicadoresResponse)
                payload=adapter.dump_python(adapter.validate_python(payload),mode="json")
            stats["ms"]=(time.perf_counter()-start)*1000
            stats["bytes"]=len(json.dumps(payload,separators=(",",":"),ensure_ascii=False).encode())
            return stats,payload
    finally:
        event.remove(env["connection"],"before_cursor_execute",sql)
        event.remove(Session,"loaded_as_persistent",loaded)


def save(name,value):
    if os.getenv("F05_EVIDENCE_DIR"):
        (Path(os.environ["F05_EVIDENCE_DIR"])/name).write_text(json.dumps(value,indent=2))


def test_baseline_before_changes(map_env):
    if not os.getenv("F05_EVIDENCE_DIR") or not (Path(os.environ["F05_EVIDENCE_DIR"])/"backend-baseline.json").exists():
        save("backend-baseline.json",{str(i):measure(map_env,p,True) for i,p in enumerate(map_env["projects"])})
    if os.getenv("F05_EVIDENCE_DIR"):
        path=Path(os.environ["F05_EVIDENCE_DIR"])/"openapi-before.json"
        if not path.exists():path.write_text(json.dumps(app.openapi(),indent=2))


@pytest.mark.parametrize("role",ROLES)
@pytest.mark.parametrize("project_index",range(4))
def test_equivalent_indicators_and_scope(map_env,role,project_index):
    env=map_env;p=env["projects"][project_index];user=env["users"][role]
    if role=="operador" and project_index==3:
        for legacy in (True,False):
            with pytest.raises(HTTPException) as denied:measure(env,p,legacy,user)
            assert denied.value.status_code==403
        return
    _,expected=measure(env,p,True,user)
    stats,actual=measure(env,p,False,user)
    assert actual==expected
    assert (stats["authorization"],stats["functional"],stats["serialization"],stats["objects"])==(1,1,0,1)
    if project_index==0:assert actual==dict(asambleas_realizadas=3,convenios_individuales=1,convenios_colectivos=1,convenios_firmados=2)
    if project_index==1:assert actual["asambleas_realizadas"]==1  # nucleus 105 must be included


@pytest.mark.parametrize("role",ROLES)
@pytest.mark.parametrize("state",["project","pn","nucleus","affectation","agreement","link","revoked",
                                 "assembly","convocation","catalog","null_type","unsigned"])
def test_active_records_nulls_and_revocation(map_env,state,role):
    env=map_env;p=env["projects"][0];user=env["users"][role]
    tx=env["connection"].begin_nested()
    try:
        with env["session_factory"]() as db:
            set_audit_context(db,env["actor"])
            if state=="revoked":
                row=db.query(models.UsuarioProyecto).filter_by(id_proyecto=p,id_usuario=user.id_usuario).first()
            else:
                model,identity={"project":(models.Proyecto,p),"pn":(models.ProyectoNucleo,env["pns"][0]),
                    "nucleus":(models.NucleoAgrario,env["nuclei"][0]),"affectation":(models.Afectacion,env["affects"][0]),
                    "agreement":(models.Convenio,env["agreements"][0]),"link":(models.ConvenioAfectacion,env["links"][0]),
                    "assembly":(models.Asamblea,env["assemblies"][0]),
                    "convocation":(models.AsambleaConvocatoria,env["convocations"][1]),
                    "catalog":(models.CatalogoOperativo,env["celebrated"]),
                    "null_type":(models.Convenio,env["agreements"][0]),
                    "unsigned":(models.Convenio,env["agreements"][0])}[state]
                row=db.query(model).options(raiseload("*")).filter(model.__mapper__.primary_key[0]==identity).one()
            if state=="null_type":
                row.tipo_instrumento="otro";row.tipo_convenio=None;row.descripcion_instrumento="F05"
            elif state=="unsigned":row.fecha_firma=None
            elif row is not None:mark_inactive(row,env["actor"],"F05 sintético")
            db.commit()
        results=[]
        for legacy in (True,False):
            try:results.append((200,measure(env,p,legacy,user)[1]))
            except HTTPException as error:results.append((error.status_code,error.detail))
        assert results[0]==results[1]
        if state=="catalog":assert results[1][1]["asambleas_realizadas"] is None
    finally:tx.rollback()


def test_benchmark(map_env):
    results={}
    for name,p in zip(("small","over_100","empty"),map_env["projects"]):
        variants={"original":[],"optimized":[]}
        for legacy in (True,False):measure(map_env,p,legacy)
        for i in range(5):
            payloads=[]
            for legacy in ((True,False) if i%2==0 else (False,True)):
                stats,payload=measure(map_env,p,legacy);payloads.append(payload)
                variants["original" if legacy else "optimized"].append(stats)
            assert payloads[0]==payloads[1]
        results[name]={name:{"median_ms":statistics.median(s["ms"] for s in samples),"samples":samples} for name,samples in variants.items()}
    save("backend-comparison.json",results)


@pytest.mark.parametrize("role",ROLES)
def test_http_roles_contract_and_validation(map_env,monkeypatch,role):
    env=map_env
    monkeypatch.setitem(app.dependency_overrides,auth.get_current_user,lambda:env["users"][role])
    with TestClient(app) as client:
        for i,p in enumerate(env["projects"]):
            response=client.get(f"/api/proyectos/{p}/mapa/indicadores")
            assert response.status_code==(403 if i==3 and role=="operador" else 200)
            if response.status_code==200:assert response.json()==measure(env,p,True,env["users"][role])[1]
        assert client.get("/api/proyectos/2147483647/mapa/indicadores").status_code==403
        assert client.get("/api/proyectos/0/mapa/indicadores").status_code==422
        monkeypatch.delitem(app.dependency_overrides,auth.get_current_user)
        assert client.get(f"/api/proyectos/{env['projects'][0]}/mapa/indicadores").status_code==401
        client.cookies.set("ssalfer_session","invalid")
        assert client.get(f"/api/proyectos/{env['projects'][0]}/mapa/indicadores").status_code==401


def test_additive_openapi(map_env):
    after=app.openapi()
    docs=Path(os.getenv("REPORT_CONTRACT_DOCS",str(Path(__file__).resolve().parents[2]/"docs")))
    published=json.loads((docs/"openapi.json").read_text())
    route="/api/proyectos/{id_proyecto}/mapa/indicadores"
    assert published["paths"][route]==after["paths"][route]
    assert published["components"]["schemas"]["MapaIndicadoresResponse"]==after["components"]["schemas"]["MapaIndicadoresResponse"]
    if not os.getenv("F05_EVIDENCE_DIR"):return
    before=json.loads((Path(os.environ["F05_EVIDENCE_DIR"])/"openapi-before.json").read_text())
    for path,contract in before["paths"].items():assert after["paths"][path]==contract,path
    for name,contract in before["components"]["schemas"].items():assert after["components"]["schemas"][name]==contract,name
    assert set(after["paths"])-set(before["paths"])=={"/api/proyectos/{id_proyecto}/mapa/indicadores"}
    save("openapi-after.json",after)


@pytest.mark.parametrize("role",ROLES)
def test_signed_agreement_on_nucleus_105_is_included(map_env,role):
    env=map_env;tx=env["connection"].begin_nested()
    try:
        with env["session_factory"]() as db:
            set_audit_context(db,env["actor"])
            c=db.query(models.Convenio).options(raiseload("*")).filter_by(id_convenio=env["agreements"][3]).one()
            c.fecha_firma=date(2026,1,2);db.commit()
        p=env["projects"][1];u=env["users"][role]
        assert measure(env,p,True,u)[1]==measure(env,p,False,u)[1]
        assert measure(env,p,False,u)[1]["convenios_colectivos"]==1
    finally:tx.rollback()


@pytest.mark.parametrize("role",ROLES)
def test_real_sessions_and_inactive_users(map_env,monkeypatch,role):
    env=map_env;tx=env["connection"].begin_nested();password="MapaLocal2026!QA"
    try:
        with env["session_factory"]() as db:
            set_audit_context(db,env["actor"])
            u=db.get(models.Usuario,env["users"][role].id_usuario)
            u.contrasena_hash=hash_password(password);email=u.correo;db.commit()
        monkeypatch.delitem(app.dependency_overrides,auth.get_current_user)
        with TestClient(app) as client:
            path=f"/api/proyectos/{env['projects'][0]}/mapa/indicadores"
            assert client.get(path).status_code==401
            client.cookies.set(AUTH_SETTINGS.session_cookie_name,"f05-invalid-session")
            assert client.get(path).status_code==401
            client.cookies.clear()
            login=client.post("/api/auth/sesiones",data={"username":email,"password":password},
                headers={"Origin":AUTH_SETTINGS.allowed_origins[0]})
            assert login.status_code==200,login.text
            assert client.get(path).json()==measure(env,env["projects"][0],True,env["users"][role])[1]
            forbidden=f"/api/proyectos/{env['projects'][3]}/mapa/indicadores"
            assert client.get(forbidden).status_code==(403 if role=="operador" else 200)
            with env["session_factory"]() as db:
                set_audit_context(db,env["actor"])
                u=db.get(models.Usuario,env["users"][role].id_usuario)
                u.activo=False;u.fecha_baja=datetime.now(timezone.utc)
                u.id_usuario_baja=env["actor"];u.motivo_baja="F05 usuario inactivo";db.commit()
            assert client.get(path).status_code==401
    finally:tx.rollback()


def test_http_benchmark_and_serialized_results(map_env):
    """Real API serialization in TestClient, not network/browser timings.

    Keep the administrative nucleus request on both sides, since the map still
    needs it for surfaces, counts and detail controls. Authentication is overridden.
    """
    env=map_env;results={}
    with TestClient(app) as client:
        for name,p in zip(("small","over_100","empty"),env["projects"]):
            variants={"original":[],"optimized":[]}
            for i in range(5):
                payloads=[]
                for legacy in ((True,False) if i%2==0 else (False,True)):
                    stats={"sql":0,"requests":0,"objects":0,"response_bytes":0}
                    def count(conn,cursor,statement,params,context,many):
                        if statement.lstrip().upper().startswith(("SELECT","WITH")):stats["sql"]+=1
                    def loaded(session,instance):stats["objects"]+=1
                    def get(path):
                        stats["requests"]+=1;r=client.get(path);assert r.status_code==200,r.text
                        stats["response_bytes"]+=len(r.content)
                        return r.json()
                    event.listen(env["connection"],"before_cursor_execute",count)
                    event.listen(Session,"loaded_as_persistent",loaded)
                    try:
                        start=time.perf_counter();nuclei=[];skip=0
                        while True:
                            page=get(f"/api/proyectos/{p}/nucleos?skip={skip}&limit=200")
                            nuclei.extend(page)
                            if len(page)<200:break
                            skip+=200
                        if legacy:
                            catalog=get("/api/catalogos/operativos/resultado_convocatoria")
                            celebrated={r["id_catalogo_opcion"] for r in catalog if r["codigo"]=="celebrada"}
                            assemblies=set();unique={}
                            for n in nuclei:
                                for a in get(f"/api/proyecto-nucleo/{n['id_proyecto_nucleo']}/asambleas"):
                                    if a["activo"] and any(c["activo"] and c["fecha_realizacion"] and c["id_resultado"] in celebrated for c in a["convocatorias"]):
                                        assemblies.add(a["id_asamblea"])
                                for a in get(f"/api/proyecto-nucleo/{n['id_proyecto_nucleo']}/afectaciones"):
                                    for c in get(f"/api/afectaciones/{a['id_afectacion']}/convenios"):
                                        if c["activo"] and c["fecha_firma"]:unique[c["id_convenio"]]=c
                            individual=sum(c["ambito"]=="individual" for c in unique.values())
                            collective=sum(c["ambito"]=="colectivo" for c in unique.values())
                            payload=dict(asambleas_realizadas=len(assemblies) if celebrated else None,
                                convenios_individuales=individual,convenios_colectivos=collective,
                                convenios_firmados=individual+collective)
                        else:payload=get(f"/api/proyectos/{p}/mapa/indicadores")
                        stats["ms"]=(time.perf_counter()-start)*1000
                        variants["original" if legacy else "optimized"].append(stats)
                        payloads.append(payload)
                        if not legacy:assert stats["sql"]==4
                    finally:
                        event.remove(env["connection"],"before_cursor_execute",count)
                        event.remove(Session,"loaded_as_persistent",loaded)
                assert payloads[0]==payloads[1]
            results[name]={v:{"median_ms":statistics.median(s["ms"] for s in samples),"samples":samples} for v,samples in variants.items()}
    save("http-comparison.json",results)
