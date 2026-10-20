"""F06 event convenio labels: retain every ordered active pair, authorize before projection."""
from datetime import date
import json
import statistics
import time

from fastapi.testclient import TestClient
from pydantic import TypeAdapter
import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session, raiseload

from app import auth, models, schemas
from app.main import app
from app.routers import domain, reporting
from app.services.common import mark_inactive, set_audit_context
from tests.test_report_references_performance import (
    map_env, dashboard_env, references_env, ROLES, C_FIELDS, project, save, MEASUREMENT_PHASE,
)
FIELDS=(*C_FIELDS,"fecha_programada_firma")
ADAPTER=TypeAdapter(list[schemas.ReporteConvenioEventoVinculoReferencia])


@pytest.fixture(scope="module")
def tracking_env(references_env):
    env=dict(references_env)
    with env["session_factory"]() as db:
        set_audit_context(db,env["actor"])
        cop=db.query(models.CatalogoOperativo.id_catalogo_opcion).filter_by(tipo_catalogo="tipo_cop_operativo",codigo="ORIGEN").scalar()
        for i in range(50):
            a=models.Afectacion(id_proyecto_nucleo=env["pns"][0],tipo_afectacion="colectivo",id_tipo_cop_operativo=cop,creado_por=env["actor"])
            db.add(a);db.flush()
            c=models.Convenio(id_proyecto_nucleo=env["pns"][0],ambito="colectivo",tipo_convenio="cop_original",consecutivo=1000+i,fecha_programada_firma=date(2026,3,4),creado_por=env["actor"])
            db.add(c);db.flush();db.add(models.ConvenioAfectacion(id_convenio=c.id_convenio,id_afectacion=a.id_afectacion,creado_por=env["actor"]))
        db.commit()
        env["shared_pn"]=db.query(models.ProyectoNucleo.id_proyecto_nucleo).filter_by(id_proyecto=env["projects"][3]).scalar()
    return env


def legacy(db,user,pn):
    return [{"item":project(c,FIELDS,schemas.ConvenioResponse),"id_afectacion":a.id_afectacion}
            for a in domain.list_affectations(pn,db=db,user=user)
            for c in domain.list_agreements(a.id_afectacion,db=db,user=user)]


@pytest.mark.parametrize("role",ROLES)
@pytest.mark.parametrize("state",["active","project","pn","nucleus","affectation","agreement","link","revoked","null_type"])
def test_same_authorization_and_ordered_pairs(tracking_env,monkeypatch,role,state):
    env=tracking_env;tx=env["connection"].begin_nested();user=env["users"][role]
    try:
        with env["session_factory"]() as db:
            set_audit_context(db,env["actor"])
            if state=="revoked":row=db.query(models.UsuarioProyecto).filter_by(id_proyecto=env["projects"][0],id_usuario=user.id_usuario).first()
            elif state=="active":row=None
            else:
                model,identity={"project":(models.Proyecto,env["projects"][0]),"pn":(models.ProyectoNucleo,env["pns"][0]),"nucleus":(models.NucleoAgrario,env["nuclei"][0]),"affectation":(models.Afectacion,env["affects"][0]),"agreement":(models.Convenio,env["agreements"][0]),"link":(models.ConvenioAfectacion,env["links"][0]),"null_type":(models.Convenio,env["agreements"][0])}[state]
                row=db.query(model).options(raiseload("*")).filter(model.__mapper__.primary_key[0]==identity).one()
            if state=="null_type":row.tipo_instrumento="otro";row.tipo_convenio=None;row.descripcion_instrumento="F06 sin tipo"
            elif row is not None:mark_inactive(row,env["actor"],"F06 sintético")
            db.commit()
        with TestClient(app) as client:
            monkeypatch.setitem(app.dependency_overrides,auth.get_current_user,lambda:user)
            for pn in [env["pns"][0],env["pns"][2],env["pns"][-1],env["shared_pn"],2147483647]:
                before=client.get(f"/api/proyecto-nucleo/{pn}/afectaciones")
                after=client.get(f"/api/proyecto-nucleo/{pn}/reportes/referencias-convenios")
                assert after.status_code==before.status_code
                if before.status_code==200:
                    with env["session_factory"]() as db:assert after.json()==legacy(db,user,pn)
    finally:
        tx.rollback()


def test_scalar_serialization_and_published_contract(tracking_env):
    env=tracking_env;stats={"sql":0,"objects":0,"serialization_sql":0};phase=["query"]
    def sql(conn,cursor,statement,params,context,many):
        if statement.lstrip().upper().startswith(("SELECT","WITH")):stats["serialization_sql" if phase[0]=="serialization" else "sql"]+=1
    def loaded(session,obj):stats["objects"]+=1
    event.listen(env["connection"],"before_cursor_execute",sql);event.listen(Session,"loaded_as_persistent",loaded)
    try:
        with env["session_factory"]() as db:
            rows=reporting.report_event_agreement_references(env["pns"][0],db=db,user=env["users"]["admin"])
            phase[0]="serialization";payload=ADAPTER.dump_python(ADAPTER.validate_python(rows),mode="json")
        assert payload;assert stats=={"sql":3,"objects":2,"serialization_sql":0}
    finally:
        event.remove(env["connection"],"before_cursor_execute",sql);event.remove(Session,"loaded_as_persistent",loaded)
    save("tracking-scalar.json",stats)


def test_tracking_http_flow_benchmark(tracking_env):
    env=tracking_env;variants={"original":[],"optimized":[]}
    with TestClient(app) as client:
        for i in range(5):
            payloads=[]
            for original in ((True,False) if i%2==0 else (False,True)):
                stats={"requests":0,"sql":0,"objects":0,"response_bytes":0}
                def sql(conn,cursor,statement,params,context,many):
                    if statement.lstrip().upper().startswith(("SELECT","WITH")):stats["sql"]+=1
                def loaded(session,obj):stats["objects"]+=1
                def get(path):
                    stats["requests"]+=1;r=client.get(path);assert r.status_code==200,r.text;stats["response_bytes"]+=len(r.content);return r.json()
                event.listen(env["connection"],"before_cursor_execute",sql);event.listen(Session,"loaded_as_persistent",loaded)
                try:
                    start=time.perf_counter();pn=env["pns"][0];parents=get(f"/api/proyecto-nucleo/{pn}/afectaciones")
                    if original:rows=[{"item":{k:c[k] for k in FIELDS},"id_afectacion":a["id_afectacion"]} for a in parents for c in get(f"/api/afectaciones/{a['id_afectacion']}/convenios")]
                    else:rows=get(f"/api/proyecto-nucleo/{pn}/reportes/referencias-convenios")
                    stats["ms"]=(time.perf_counter()-start)*1000;payloads.append(rows);variants["original" if original else "optimized"].append(stats)
                finally:
                    event.remove(env["connection"],"before_cursor_execute",sql);event.remove(Session,"loaded_as_persistent",loaded)
            assert payloads[0]==payloads[1]
    save("tracking-http-flow.json",{v:{"median_ms":statistics.median(s["ms"] for s in samples),"samples":samples} for v,samples in variants.items()})
