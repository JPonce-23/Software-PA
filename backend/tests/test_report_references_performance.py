"""F06: compare scalar references with the unchanged individual read APIs."""
from datetime import date, datetime, timezone
from contextvars import ContextVar
from decimal import Decimal
import json
import os
from pathlib import Path
import statistics
import time

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
from app.services import convenio_reports
from app.services.common import mark_inactive, set_audit_context
from app.services.authentication import hash_password
from tests.test_map_indicators_performance import map_env, dashboard_env, ROLES
from tests.test_convenios_colectivos_destino import _catalog, _create_unit_and_link

C_FIELDS=("id_convenio","id_proyecto_nucleo","tipo_convenio","consecutivo","ambito","descripcion_instrumento","fecha_firma")
A_FIELDS=("id_afectacion","id_proyecto_nucleo","tipo_afectacion","situacion","superficie_afectada_ha")
N_FIELDS=("id_proyecto_nucleo","nombre_nucleo")
S_FIELDS=("id_asamblea","id_proyecto_nucleo","proposito")
MEASUREMENT_PHASE=ContextVar("f06_measurement_phase",default=None)


@pytest.fixture(scope="module")
def references_env(map_env):
    env=dict(map_env);api=env["request"]
    destinations=_catalog(api,"destino_superficie")
    for code,surface in (("tuc","1.1234567"),("camino","2.2345678")):
        _create_unit_and_link(api,env["pns"][0],env["affects"][0],destinations[code],surface)
    with env["session_factory"]() as db:
        set_audit_context(db,env["actor"])
        for i in range(60):
            c=models.Convenio(id_proyecto_nucleo=env["pns"][0],ambito="colectivo",
                tipo_convenio="cop_original",consecutivo=i+10,creado_por=env["actor"],
                fecha_firma=date(2026,2,3) if i%2 else None,monto_100=Decimal("123456.78"),
                descripcion_instrumento=None)
            db.add(c);db.flush()
            db.add(models.ConvenioAfectacion(id_convenio=c.id_convenio,id_afectacion=env["affects"][0],creado_por=env["actor"]))
        db.commit()
        all_nuclei=db.query(models.ProyectoNucleoResumen).filter(models.ProyectoNucleoResumen.id_proyecto.in_(env["projects"])).all()
        env["names"]={n.id_proyecto_nucleo:n.nombre_nucleo for n in all_nuclei}
        env["all_pns"]=list(env["names"])
        env["all_c"]=[r[0] for r in db.query(models.Convenio.id_convenio).filter(models.Convenio.id_proyecto_nucleo.in_(env["all_pns"])).all()]
    return env


def project(record,fields,schema):
    phase=MEASUREMENT_PHASE.get();previous=phase[0] if phase else None
    if phase is not None:phase[0]="serialization"
    try:
        adapter=TypeAdapter(schema)
        data=adapter.dump_python(adapter.validate_python(record),mode="json")
        return {key:data[key] for key in fields}
    finally:
        if phase is not None:phase[0]=previous


def legacy_generic(db,user,ids):
    result={"nucleos":[],"afectaciones":[],"convenios":[]}
    for name,fn,fields,schema in (
        ("nucleos",domain.get_project_nucleus,N_FIELDS,schemas.ProyectoNucleoResponse),
        ("afectaciones",domain.get_affectation,A_FIELDS,schemas.AfectacionResponse),
        ("convenios",domain.get_agreement,C_FIELDS,schemas.ConvenioResponse),
    ):
        for identity in dict.fromkeys(ids.get(name,[])):
            try:result[name].append(project(fn(identity,db=db,user=user),fields,schema))
            except HTTPException as e:
                assert e.status_code in (403,404)
    return result


def legacy_context(db,user,ids,names):
    result={"nucleos":[],"afectaciones":[],"convenios":[],"asambleas":[]}
    for pn in dict.fromkeys(ids):
        affects=domain.list_affectations(pn,db=db,user=user)
        result["nucleos"].append({"id_proyecto_nucleo":pn,"nombre_nucleo":names[pn]})
        unique={}
        for a in affects:
            result["afectaciones"].append(project(a,A_FIELDS,schemas.AfectacionResponse))
            for c in domain.list_agreements(a.id_afectacion,db=db,user=user):
                unique[c.id_convenio]={"item":project(c,C_FIELDS,schemas.ConvenioResponse),"id_afectacion":a.id_afectacion}
        result["convenios"].extend(unique.values())
        result["asambleas"].extend(project(a,S_FIELDS,schemas.AsambleaResponse) for a in domain.list_assemblies(pn,db=db,user=user))
    return result


def normalized(data):
    return {name:sorted(rows,key=lambda row:json.dumps(row,sort_keys=True)) for name,rows in data.items()}


def measure(env,kind,ids,original,user=None):
    stats={"sql":0,"objects":0,"serialization_sql":0};phase=["query"]
    phase_token=MEASUREMENT_PHASE.set(phase)
    def sql(conn,cursor,statement,params,context,many):
        if statement.lstrip().upper().startswith(("SELECT","WITH")):
            stats["serialization_sql" if phase[0]=="serialization" else "sql"]+=1
    def loaded(session,instance):stats["objects"]+=1
    event.listen(env["connection"],"before_cursor_execute",sql);event.listen(Session,"loaded_as_persistent",loaded)
    try:
        with env["session_factory"]() as db:
            u=user or env["users"]["admin"];start=time.perf_counter()
            if original:
                data=legacy_generic(db,u,ids) if kind=="generic" else legacy_context(db,u,ids,env["names"])
            elif kind=="generic":
                data=reporting.report_references(id_proyecto_nucleo=ids.get("nucleos",[]),id_afectacion=ids.get("afectaciones",[]),id_convenio=ids.get("convenios",[]),db=db,user=u)
            else:data=reporting.report_context_references(id_proyecto_nucleo=ids,db=db,user=u)
            phase[0]="serialization"
            if not original:
                adapter=TypeAdapter(schemas.ReporteReferenciasResponse if kind=="generic" else schemas.ReporteContextoReferenciasResponse)
                data=adapter.dump_python(adapter.validate_python(data),mode="json")
            stats["ms"]=(time.perf_counter()-start)*1000
            stats["bytes"]=len(json.dumps(data,separators=(",",":"),ensure_ascii=False).encode())
            return stats,normalized(data)
    finally:
        event.remove(env["connection"],"before_cursor_execute",sql);event.remove(Session,"loaded_as_persistent",loaded)
        MEASUREMENT_PHASE.reset(phase_token)


def save(name,data):
    if os.getenv("F06_EVIDENCE_DIR"):(Path(os.environ["F06_EVIDENCE_DIR"])/name).write_text(json.dumps(data,indent=2))


def patterns(env):
    return {"convenios_65":("generic",{"convenios":env["all_c"]}),
        "contexto_3":("context",env["pns"][:3]),"contexto_105":("context",env["pns"][3:]),
        "sin_resultados":("generic",{"convenios":[2147483647]})}


def test_baseline_before_changes(references_env):
    p=Path(os.environ["F06_EVIDENCE_DIR"]) if os.getenv("F06_EVIDENCE_DIR") else None
    if p and not (p/'backend-baseline.json').exists():
        save("backend-baseline.json",{k:measure(references_env,kind,ids,True)[0] for k,(kind,ids) in patterns(references_env).items()})
        save("openapi-before.json",app.openapi())


@pytest.mark.parametrize("role",ROLES)
@pytest.mark.parametrize("kind",["generic","context"])
def test_equivalent_references_and_visibility(references_env,role,kind):
    env=references_env;user=env["users"][role]
    ids={"nucleos":env["all_pns"],"afectaciones":env["affects"],"convenios":env["all_c"]} if kind=="generic" else env["pns"][:3]
    # Keep generic direct calls below the documented total limit.
    if kind=="generic":ids["nucleos"]=ids["nucleos"][:3];ids["afectaciones"]=ids["afectaciones"][:4]
    expected=measure(env,kind,ids,True,user)[1];stats,actual=measure(env,kind,ids,False,user)
    assert actual==expected
    assert stats["objects"]==stats["serialization_sql"]==0
    assert stats["sql"]==(3 if kind=="generic" else 4)


@pytest.mark.parametrize("role",ROLES)
@pytest.mark.parametrize("state",["project","pn","nucleus","affectation","agreement","link","revoked","null_type"])
def test_inactive_records_missing_references_and_revocation(references_env,role,state):
    env=references_env;tx=env["connection"].begin_nested();user=env["users"][role]
    try:
        with env["session_factory"]() as db:
            set_audit_context(db,env["actor"])
            if state=="revoked":row=db.query(models.UsuarioProyecto).filter_by(id_proyecto=env["projects"][0],id_usuario=user.id_usuario).first()
            else:
                model,identity={"project":(models.Proyecto,env["projects"][0]),"pn":(models.ProyectoNucleo,env["pns"][0]),"nucleus":(models.NucleoAgrario,env["nuclei"][0]),"affectation":(models.Afectacion,env["affects"][0]),"agreement":(models.Convenio,env["agreements"][0]),"link":(models.ConvenioAfectacion,env["links"][0]),"null_type":(models.Convenio,env["agreements"][0])}[state]
                row=db.query(model).options(raiseload("*")).filter(model.__mapper__.primary_key[0]==identity).one()
            if state=="null_type":row.tipo_instrumento="otro";row.tipo_convenio=None;row.descripcion_instrumento="F06 <sin tipo>"
            elif row is not None:mark_inactive(row,env["actor"],"F06 sintético")
            db.commit()
        ids={"nucleos":env["all_pns"][-3:]+[env["pns"][0],2147483647],"convenios":env["agreements"]+[2147483647],"afectaciones":env["affects"][:2]+[2147483647]}
        assert measure(env,"generic",ids,True,user)[1]==measure(env,"generic",ids,False,user)[1]
        # Context batches omit denied/inactive roots, just as the client cannot read them.
        try:expected=measure(env,"context",env["pns"][:3],True,user)[1]
        except HTTPException as e:
            assert e.status_code in (403,404)
            actual=measure(env,"context",env["pns"][:3],False,user)[1]
            assert env["pns"][0] not in {n["id_proyecto_nucleo"] for n in actual["nucleos"]}
        else:assert measure(env,"context",env["pns"][:3],False,user)[1]==expected
    finally:tx.rollback()


def test_benchmarks(references_env):
    result={}
    for name,(kind,ids) in patterns(references_env).items():
        variants={"original":[],"optimized":[]}
        for original in (True,False):measure(references_env,kind,ids,original)
        for i in range(5):
            payloads=[]
            for original in ((True,False) if i%2==0 else (False,True)):
                stats,payload=measure(references_env,kind,ids,original);payloads.append(payload)
                variants["original" if original else "optimized"].append(stats)
            assert payloads[0]==payloads[1]
        result[name]={v:{"median_ms":statistics.median(s["ms"] for s in samples),"samples":samples} for v,samples in variants.items()}
    save("backend-comparison.json",result)


@pytest.mark.parametrize("role",ROLES)
def test_http_roles_limits_and_contract(references_env,monkeypatch,role):
    env=references_env;monkeypatch.setitem(app.dependency_overrides,auth.get_current_user,lambda:env["users"][role])
    with TestClient(app) as client:
        generic="/api/reportes/referencias";context="/api/reportes/referencias-contexto"
        ids={"nucleos":env["all_pns"][-2:],"afectaciones":env["affects"][:2],"convenios":env["agreements"]}
        params=[(key,i) for name,key in (("nucleos","id_proyecto_nucleo"),("afectaciones","id_afectacion"),("convenios","id_convenio")) for i in ids[name]]
        assert normalized(client.get(generic,params=params).json())==measure(env,"generic",ids,True,env["users"][role])[1]
        assert client.get(generic,params=[("id_convenio",1)]*201).status_code==422
        assert client.get(generic,params={"id_convenio":0}).status_code==422
        assert client.get(context).status_code==422
        assert client.get(context,params=[("id_proyecto_nucleo",i) for i in env["pns"][:3]]).status_code==200
        monkeypatch.delitem(app.dependency_overrides,auth.get_current_user)
        assert client.get(generic).status_code==401
        assert client.get(context,params={"id_proyecto_nucleo":1}).status_code==401


@pytest.mark.parametrize("role",ROLES)
def test_affectations_expanded_by_nucleus_match_original_lists(references_env,role):
    env=references_env;u=env["users"][role]
    with env["session_factory"]() as db:
        actual=reporting.report_references(id_proyecto_nucleo=env["all_pns"],id_afectacion=[],id_convenio=[],incluir_afectaciones=True,db=db,user=u)
        actual=TypeAdapter(schemas.ReporteReferenciasResponse).dump_python(TypeAdapter(schemas.ReporteReferenciasResponse).validate_python(actual),mode="json")
        expected=[]
        for identity in env["all_pns"]:
            try:expected.extend(project(a,A_FIELDS,schemas.AfectacionResponse) for a in domain.list_affectations(identity,db=db,user=u))
            except HTTPException as e:assert e.status_code in (403,404)
        assert normalized({"afectaciones":actual["afectaciones"]})==normalized({"afectaciones":expected})


def test_context_preserves_duplicate_parent_label_and_per_nucleus_order(references_env):
    env=references_env
    with env["session_factory"]() as db:
        expected=legacy_context(db,env["users"]["admin"],env["pns"][:3],env["names"])
        actual=reporting.report_context_references(env["pns"][:3],db=db,user=env["users"]["admin"])
        adapter=TypeAdapter(schemas.ReporteContextoReferenciasResponse);actual=adapter.dump_python(adapter.validate_python(actual),mode="json")
        for pn in env["pns"][:3]:
            for name in ("afectaciones","asambleas","convenios"):
                def in_pn(row):return (row.get("item") or row)["id_proyecto_nucleo"]==pn
                assert [r for r in actual[name] if in_pn(r)]==[r for r in expected[name] if in_pn(r)]


@pytest.mark.parametrize("role",ROLES)
def test_real_sessions_and_inactive_accounts(references_env,monkeypatch,role):
    env=references_env;tx=env["connection"].begin_nested();password="ReportesLocal2026!QA"
    try:
        with env["session_factory"]() as db:
            set_audit_context(db,env["actor"]);u=db.get(models.Usuario,env["users"][role].id_usuario)
            u.contrasena_hash=hash_password(password);email=u.correo;db.commit()
        monkeypatch.delitem(app.dependency_overrides,auth.get_current_user)
        with TestClient(app) as client:
            paths=[f"/api/proyecto-nucleo/{env['pns'][0]}/reportes/referencias-convenios",f"/api/reportes/referencias?id_convenio={env['agreements'][0]}",f"/api/reportes/referencias-contexto?id_proyecto_nucleo={env['pns'][0]}"]
            for path in paths:assert client.get(path).status_code==401
            client.cookies.set(AUTH_SETTINGS.session_cookie_name,"f06-invalid-session")
            for path in paths:assert client.get(path).status_code==401
            client.cookies.clear()
            assert client.post("/api/auth/sesiones",data={"username":email,"password":password},headers={"Origin":AUTH_SETTINGS.allowed_origins[0]}).status_code==200
            for path in paths:assert client.get(path).status_code==200
            with env["session_factory"]() as db:
                set_audit_context(db,env["actor"]);u=db.get(models.Usuario,env["users"][role].id_usuario)
                u.activo=False;u.fecha_baja=datetime.now(timezone.utc);u.id_usuario_baja=env["actor"];u.motivo_baja="F06 inactivo";db.commit()
            for path in paths:assert client.get(path).status_code==401
    finally:tx.rollback()


def test_additive_and_published_openapi(references_env):
    current=app.openapi();docs=Path(os.getenv("REPORT_CONTRACT_DOCS",str(Path(__file__).resolve().parents[2]/"docs")))
    published=json.loads((docs/"openapi.json").read_text())
    paths={"/api/reportes/referencias","/api/reportes/referencias-contexto","/api/proyecto-nucleo/{id_proyecto_nucleo}/reportes/referencias-convenios"}
    for path in paths:assert current["paths"][path]==published["paths"][path]
    for name,value in current["components"]["schemas"].items():
        if name.startswith("Reporte") and "Referencia" in name:assert published["components"]["schemas"][name]==value
    if os.getenv("F06_EVIDENCE_DIR"):
        before=json.loads((Path(os.environ["F06_EVIDENCE_DIR"])/"openapi-before.json").read_text())
        for path,contract in before["paths"].items():assert current["paths"][path]==contract
        for name,contract in before["components"]["schemas"].items():assert current["components"]["schemas"][name]==contract
        assert set(current["paths"])-set(before["paths"])==paths


def test_http_reference_benchmark(references_env):
    env=references_env;results={}
    with TestClient(app) as client:
        for name,identities in (("convenios_65",env["all_c"]),("sin_resultados",[2147483647])):
            variants={"original":[],"optimized":[]}
            for i in range(5):
                payloads=[]
                for original in ((True,False) if i%2==0 else (False,True)):
                    stats={"sql":0,"objects":0,"requests":0,"response_bytes":0}
                    def sql(conn,cursor,statement,params,context,many):
                        if statement.lstrip().upper().startswith(("SELECT","WITH")):stats["sql"]+=1
                    def loaded(session,instance):stats["objects"]+=1
                    def get(path,**kwargs):
                        stats["requests"]+=1;r=client.get(path,**kwargs);stats["response_bytes"]+=len(r.content);return r
                    event.listen(env["connection"],"before_cursor_execute",sql);event.listen(Session,"loaded_as_persistent",loaded)
                    try:
                        start=time.perf_counter();rows=[]
                        if original:
                            for identity in identities:
                                r=get(f"/api/convenios/{identity}")
                                if r.status_code==200:rows.append({key:r.json()[key] for key in C_FIELDS})
                                else:assert r.status_code in (403,404)
                        else:
                            r=get("/api/reportes/referencias",params=[("id_convenio",identity) for identity in identities]);assert r.status_code==200
                            rows=r.json()["convenios"]
                        stats["ms"]=(time.perf_counter()-start)*1000
                        variants["original" if original else "optimized"].append(stats);payloads.append(normalized({"convenios":rows}))
                    finally:
                        event.remove(env["connection"],"before_cursor_execute",sql);event.remove(Session,"loaded_as_persistent",loaded)
                assert payloads[0]==payloads[1]
            results[name]={v:{"median_ms":statistics.median(s["ms"] for s in samples),"samples":samples} for v,samples in variants.items()}
    save("http-comparison.json",results)


@pytest.mark.parametrize("role",ROLES)
def test_report_json_financial_values_pagination_and_csv_are_unchanged(references_env,monkeypatch,role):
    env=references_env;p=env["projects"][0]
    monkeypatch.setitem(app.dependency_overrides,auth.get_current_user,lambda:env["users"][role])
    # The general report intentionally has a separate read-only connection in
    # production. Route it into this fixture's outer rollback, as its own tests do.
    def report_db():
        with env["session_factory"]() as db:yield db
    monkeypatch.setitem(app.dependency_overrides,convenio_reports.get_report_db,report_db)
    paths=[f"/api/reportes/convenios/colectivos-destino?id_proyecto={p}",
           f"/api/reportes/convenios/valores-declarados?id_proyecto={p}",
           f"/api/reportes/convenios/cobertura-impactos?id_proyecto={p}",
           f"/api/proyectos/{p}/reportes/convenios/general?tamano_pagina=1",
           f"/api/proyectos/{p}/reportes/convenios/general/completo",
           f"/api/exportaciones/dashboard.csv?id_proyecto={p}"]
    with TestClient(app) as client:
        before=[client.get(path) for path in paths]
        assert all(r.status_code==200 for r in before),[(p,r.status_code,r.text[:250]) for p,r in zip(paths,before)]
        assert client.get("/api/reportes/referencias",params=[("id_convenio",i) for i in env["all_c"]]).status_code==200
        assert client.get("/api/reportes/referencias-contexto",params=[("id_proyecto_nucleo",i) for i in env["pns"][:3]]).status_code==200
        after=[client.get(path) for path in paths]
        assert [r.content for r in after]==[r.content for r in before]
        rows=[r for r in before[0].json() if r["id_convenio"]==env["agreements"][0]]
        assert len(rows)==2
        assert {Decimal(r["monto_declarado"]) for r in rows}=={Decimal("100.13")}
        assert before[3].json()["paginacion_colectivos"]["hay_mas"] is True
