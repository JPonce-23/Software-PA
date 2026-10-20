"""F04: compare grouped COP with the unchanged dashboard traversal on tmpfs PG."""
from contextlib import ExitStack
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import statistics
import time
from types import SimpleNamespace
import uuid
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import TypeAdapter
import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session, raiseload

from app import auth, models, schemas
from app.main import app
from app.routers import domain, reporting
from app.services import access
from app.services.common import mark_inactive, set_audit_context

ROLES=("admin","operador","visualizador","geografo")
FIELDS=("id_convenio","ambito","tipo_convenio","consecutivo","fecha_firma")


@pytest.fixture(scope="module")
def dashboard_env(transactional_api):
    env=dict(transactional_api)
    with env["session_factory"]() as db:
        assert db.execute(text("SELECT current_database(),current_setting('cluster_name')")).one()==(
            "software_pa_test","convenio-report-disposable")
        actor=app.dependency_overrides[auth.get_current_user]().id_usuario
        set_audit_context(db,actor)
        tenure=db.query(models.CatalogoOperativo.id_catalogo_opcion).filter_by(tipo_catalogo="tipo_tenencia",codigo="ejido").scalar()
        cop=db.query(models.CatalogoOperativo.id_catalogo_opcion).filter_by(tipo_catalogo="tipo_cop_operativo",codigo="ORIGEN").scalar()
        token=uuid.uuid4().hex[:12]
        projects=[models.Proyecto(clave_proyecto=f"F04-{token}-{i}",nombre_proyecto=f"F04 {i}",creado_por=actor) for i in range(4)]
        nuclei=[models.NucleoAgrario(id_municipio=1,nombre_nucleo=f"F04 {token} {i:03}",
                id_tipo_tenencia=tenure,creado_por=actor) for i in range(108)]
        db.add_all(projects+nuclei);db.flush()
        pns=[models.ProyectoNucleo(id_proyecto=projects[0 if i<3 else 1].id_proyecto,
                id_nucleo=n.id_nucleo,creado_por=actor) for i,n in enumerate(nuclei)]
        shared=models.ProyectoNucleo(id_proyecto=projects[3].id_proyecto,id_nucleo=nuclei[0].id_nucleo,creado_por=actor)
        db.add_all(pns+[shared]);db.flush()
        affects=[models.Afectacion(id_proyecto_nucleo=pn.id_proyecto_nucleo,tipo_afectacion="colectivo",
                 id_tipo_cop_operativo=cop,creado_por=actor) for pn in pns if pn!=pns[2]]
        extra=models.Afectacion(id_proyecto_nucleo=pns[0].id_proyecto_nucleo,tipo_afectacion="colectivo",
                 id_tipo_cop_operativo=cop,creado_por=actor)
        individual=models.Afectacion(id_proyecto_nucleo=pns[0].id_proyecto_nucleo,tipo_afectacion="individual",creado_por=actor)
        other=models.Afectacion(id_proyecto_nucleo=shared.id_proyecto_nucleo,tipo_afectacion="colectivo",
                 id_tipo_cop_operativo=cop,creado_por=actor)
        db.add_all(affects+[extra,individual,other]);db.flush()
        agreements=[]; links=[]
        for i,a in enumerate([affects[0],affects[0],individual,affects[-1],other]):
            c=models.Convenio(id_proyecto_nucleo=a.id_proyecto_nucleo,ambito=a.tipo_afectacion,
                tipo_convenio="cop_original",consecutivo=i+1,fecha_firma=date(2026,1,2) if i%2==0 else None,
                monto_90=None if i%2 else "90.12",monto_100="100.13",creado_por=actor)
            db.add(c);db.flush();agreements.append(c)
            link=models.ConvenioAfectacion(id_convenio=c.id_convenio,id_afectacion=a.id_afectacion,creado_por=actor)
            db.add(link);links.append(link)
        duplicate=models.ConvenioAfectacion(id_convenio=agreements[0].id_convenio,id_afectacion=extra.id_afectacion,
                  rol="adicional",creado_por=actor)
        db.add(duplicate)
        users={}
        for role in ROLES:
            u=models.Usuario(nombre="F04",apellido_paterno="QA",correo=f"{uuid.uuid4().hex}@local.invalid",
                rol=role,contrasena_hash="unused-fixture",fecha_alta=datetime.now(timezone.utc))
            db.add(u);db.flush();users[role]=SimpleNamespace(id_usuario=u.id_usuario,rol=role)
            if role=="operador":
                for p in projects[:3]:
                    db.add(models.UsuarioProyecto(id_usuario=u.id_usuario,id_proyecto=p.id_proyecto,asignado_por=actor,creado_por=actor))
        db.commit()
        env.update(actor=actor,projects=[p.id_proyecto for p in projects],pns=[p.id_proyecto_nucleo for p in pns],
            nuclei=[n.id_nucleo for n in nuclei],affects=[a.id_afectacion for a in affects],
            agreements=[c.id_convenio for c in agreements],links=[l.id_convenio_afectacion for l in links],users=users)
    return env


def legacy(db,user,project):
    nuclei=domain.list_project_nuclei(project,db=db,user=user,skip=0,limit=100)
    unique={}
    for n in nuclei:
        for a in domain.list_affectations(n.id_proyecto_nucleo,db=db,user=user):
            for c in domain.list_agreements(a.id_afectacion,db=db,user=user):
                unique[c.id_convenio]=c
    rows=list(unique.values())
    return {"individuales":sum(c.ambito=="individual" for c in rows),
            "colectivos":sum(c.ambito=="colectivo" for c in rows),
            "formalizados":sum(c.ambito in ("individual","colectivo") and c.fecha_firma is not None for c in rows),
            "convenios":[{f:(getattr(c,f).isoformat() if f=="fecha_firma" and c.fecha_firma else getattr(c,f)) for f in FIELDS} for c in rows]}


def normalized(value):
    return {**value,"convenios":sorted(value["convenios"],key=lambda c:c["id_convenio"])}


def measure(env,project,original,user=None):
    phase=["query"];stats={"authorization":0,"functional":0,"serialization":0,"objects":0}
    def sql(conn,cursor,statement,params,context,many):
        if statement.lstrip().upper().startswith("SELECT"):
            stats["serialization" if phase[0]=="serialization" else "authorization" if phase[0]=="authorization" else "functional"]+=1
    def loaded(session,instance):stats["objects"]+=1
    event.listen(env["connection"],"before_cursor_execute",sql);event.listen(Session,"loaded_as_persistent",loaded)
    try:
        with ExitStack() as stack, env["session_factory"]() as db:
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
            if original:
                payload=legacy(db,user or env["users"]["admin"],project)
            else:
                payload=reporting.dashboard_convenios(project,db=db,user=user or env["users"]["admin"])
            elapsed=(time.perf_counter()-start)*1000
            phase[0]="serialization"
            if not original:
                payload=TypeAdapter(schemas.DashboardConveniosResponse).dump_python(
                    TypeAdapter(schemas.DashboardConveniosResponse).validate_python(payload),mode="json")
            return {"ms":elapsed,**stats},normalized(payload)
    finally:
        event.remove(env["connection"],"before_cursor_execute",sql);event.remove(Session,"loaded_as_persistent",loaded)


def save(name,data):
    if os.getenv("F04_EVIDENCE_DIR"):
        (Path(os.environ["F04_EVIDENCE_DIR"])/name).write_text(json.dumps(data,indent=2))


def test_baseline_before_changes(dashboard_env):
    result={str(i):measure(dashboard_env,p,True)[0] for i,p in enumerate(dashboard_env["projects"])}
    save("backend-baseline.json",result)
    if os.getenv("F04_EVIDENCE_DIR"):
        path=Path(os.environ["F04_EVIDENCE_DIR"])/"openapi-before.json"
        if not path.exists():path.write_text(json.dumps(app.openapi(),indent=2))


@pytest.mark.parametrize("role",ROLES)
@pytest.mark.parametrize("project_index",range(4))
def test_equivalent_counts_details_and_scope(dashboard_env,role,project_index):
    env=dashboard_env;u=env["users"][role];p=env["projects"][project_index]
    if role=="operador" and project_index==3:
        for original in (True,False):
            with pytest.raises(HTTPException) as denied:measure(env,p,original,u)
            assert denied.value.status_code==403
        return
    _,expected=measure(env,p,True,u)
    stats,actual=measure(env,p,False,u)
    assert actual==expected
    assert (stats["authorization"],stats["functional"],stats["objects"])==(1,2,1)
    assert stats["serialization"]==0
    if project_index==0:
        assert (actual["individuales"],actual["colectivos"],actual["formalizados"])==(1,2,2)
    if project_index==1:
        assert actual["convenios"]==[]  # agreement only on nucleus 105; preserve first 100


@pytest.mark.parametrize("state",["project","pn","nucleus","affectation","agreement","link","revoked","null_type"])
@pytest.mark.parametrize("role",ROLES)
def test_active_records_and_revocation(dashboard_env,state,role):
    env=dashboard_env;u=env["users"][role];p=env["projects"][0]
    tx=env["connection"].begin_nested()
    try:
        with env["session_factory"]() as db:
            set_audit_context(db,env["actor"])
            if state=="null_type":
                row=db.query(models.Convenio).options(raiseload("*")).filter_by(id_convenio=env["agreements"][0]).one()
                row.tipo_instrumento="otro";row.tipo_convenio=None;row.descripcion_instrumento="Instrumento F04"
                db.commit();row=None
            elif state=="revoked" and role=="operador":
                row=db.query(models.UsuarioProyecto).filter_by(id_proyecto=p,id_usuario=u.id_usuario).one()
            elif state!="revoked":
                model,identity={"project":(models.Proyecto,p),"pn":(models.ProyectoNucleo,env["pns"][0]),
                    "nucleus":(models.NucleoAgrario,env["nuclei"][0]),"affectation":(models.Afectacion,env["affects"][0]),
                    "agreement":(models.Convenio,env["agreements"][0]),"link":(models.ConvenioAfectacion,env["links"][0])}[state]
                row=db.query(model).options(raiseload("*")).filter(model.__mapper__.primary_key[0]==identity).one()
            else:row=None
            if row is not None:mark_inactive(row,env["actor"],"F04 sintético");db.commit()
        outcomes=[]
        for original in (True,False):
            try:outcomes.append((200,measure(env,p,original,u)[1]))
            except HTTPException as error:outcomes.append((error.status_code,error.detail))
        assert outcomes[0]==outcomes[1]
    finally:tx.rollback()


def test_benchmark(dashboard_env):
    results={}
    for name,p in zip(("small","over_100","empty"),dashboard_env["projects"]):
        variants={"original":[],"optimized":[]}
        for original in (True,False):measure(dashboard_env,p,original)
        for i in range(5):
            payloads=[]
            for original in ((True,False) if i%2==0 else (False,True)):
                sample,payload=measure(dashboard_env,p,original);payloads.append(payload)
                variants["original" if original else "optimized"].append(sample)
            assert payloads[0]==payloads[1]
        results[name]={v:{"median_ms":statistics.median(s["ms"] for s in samples),"samples":samples} for v,samples in variants.items()}
    save("backend-comparison.json",results)
    print("F04="+json.dumps(results))


def test_http_auth_validation_and_additive_openapi(dashboard_env,monkeypatch):
    env=dashboard_env;path=f"/api/proyectos/{env['projects'][0]}/dashboard/convenios"
    with TestClient(app) as client:
        response=client.get(path);assert response.status_code==200
        assert normalized(response.json())==measure(env,env["projects"][0],True)[1]
        assert client.get("/api/proyectos/2147483647/dashboard/convenios").status_code==403
        assert client.get("/api/proyectos/0/dashboard/convenios").status_code==422
        monkeypatch.delitem(app.dependency_overrides,auth.get_current_user)
        assert client.get(path).status_code==401
    if os.getenv("F04_BASELINE_OPENAPI"):
        before=json.loads(Path(os.environ["F04_BASELINE_OPENAPI"]).read_text());after=app.openapi()
        for path,contract in before["paths"].items():assert after["paths"][path]==contract,path
        for name,contract in before["components"]["schemas"].items():assert after["components"]["schemas"][name]==contract,name
        assert set(after["paths"])-set(before["paths"])=={"/api/proyectos/{id_proyecto}/dashboard/convenios"}


@pytest.mark.parametrize("role",ROLES)
def test_http_roles(dashboard_env,monkeypatch,role):
    env=dashboard_env
    monkeypatch.setitem(app.dependency_overrides,auth.get_current_user,lambda:env["users"][role])
    with TestClient(app) as client:
        for index,p in enumerate(env["projects"]):
            response=client.get(f"/api/proyectos/{p}/dashboard/convenios")
            assert response.status_code==(403 if index==3 and role=="operador" else 200)


def test_http_measurements(dashboard_env):
    """Local TestClient round trips, not TCP/browser or session-auth timings."""
    env=dashboard_env;results={}
    with TestClient(app) as client:
        for name,p in zip(("small","over_100"),env["projects"]):
            variants={"original":[],"optimized":[]}
            for i in range(5):
                payloads=[]
                for original in ((True,False) if i%2==0 else (False,True)):
                    stats={"sql":0,"requests":0}
                    def count(conn,cursor,statement,params,context,many):
                        if statement.lstrip().upper().startswith("SELECT"):stats["sql"]+=1
                    def get(path):
                        stats["requests"]+=1;r=client.get(path);assert r.status_code==200,r.text
                        return r.json()
                    event.listen(env["connection"],"before_cursor_execute",count)
                    try:
                        start=time.perf_counter()
                        nuclei=get(f"/api/proyectos/{p}/nucleos")
                        if original:
                            unique={}
                            for n in nuclei:
                                for a in get(f"/api/proyecto-nucleo/{n['id_proyecto_nucleo']}/afectaciones"):
                                    for c in get(f"/api/afectaciones/{a['id_afectacion']}/convenios"):unique[c['id_convenio']]=c
                            rows=list(unique.values())
                            payload={"individuales":sum(c['ambito']=='individual' for c in rows),
                                "colectivos":sum(c['ambito']=='colectivo' for c in rows),
                                "formalizados":sum(c['fecha_firma'] is not None for c in rows),
                                "convenios":[{f:c[f] for f in FIELDS} for c in rows]}
                        else:payload=get(f"/api/proyectos/{p}/dashboard/convenios")
                        stats["ms"]=(time.perf_counter()-start)*1000
                        variants["original" if original else "optimized"].append(stats)
                        payloads.append(normalized(payload))
                    finally:event.remove(env["connection"],"before_cursor_execute",count)
                assert payloads[0]==payloads[1]
            results[name]={v:{"median_ms":statistics.median(s["ms"] for s in samples),"samples":samples} for v,samples in variants.items()}
    save("http-comparison.json",results)
