"""Opt-in F06 measurements: pytest tests/benchmark_report_screens.py.

Reconstruct the 41d4b68/new frontend API walks using real TestClient responses.
Calls are sequential here; these are NOT browser, TCP, HAR or render timings.
Kept separate from ordinary test discovery so profiling is explicitly requested.
"""
import json
import os
from pathlib import Path
import statistics
import time

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.main import app
from tests.test_report_references_performance import (
    references_env, map_env, dashboard_env, C_FIELDS, A_FIELDS, S_FIELDS, normalized,
)


def subset(row, fields):
    return {key: row[key] for key in fields}


def financial(get, project_id, original):
    result={"project":get(f"/api/proyectos/{project_id}"),"kpi":get("/api/dashboard/kpi")}
    values=f"/api/reportes/convenios/valores-declarados?id_proyecto={project_id}"
    result["values_kpi"]=get(values)
    result["advance"]=get(f"/api/reportes/avance-periodo?id_proyecto={project_id}")
    result["values_table"]=get(values) if original else result["values_kpi"]
    identities=list(dict.fromkeys(row["id_convenio"] for row in result["values_table"]))
    if original:
        refs=[]
        for identity in identities:
            row=get(f"/api/convenios/{identity}",allow_missing=True)
            if row is not None:refs.append(subset(row,C_FIELDS))
    else:
        refs=[]
        for start in range(0,len(identities),100):
            refs.extend(get("/api/reportes/referencias",params=[("id_convenio",i) for i in identities[start:start+100]])["convenios"])
    result["refs"]=normalized({"convenios":refs})
    result["coverage"]=get(f"/api/reportes/convenios/cobertura-impactos?id_proyecto={project_id}")
    result["fifonafe"]=get(f"/api/reportes/fifonafe/cobertura?id_proyecto={project_id}")
    return result


def collective(get, project_id, original, selected_nucleus=None):
    projects=[];skip=0
    while True:
        page=get(f"/api/proyectos?skip={skip}&limit=200");projects.extend(page)
        if len(page)<200:break
        skip+=200
    nuclei=get(f"/api/proyectos/{project_id}/nucleos")  # preserve original first 100
    report=f"/api/reportes/convenios/colectivos-destino?id_proyecto={project_id}"
    result={"projects":projects,"nuclei":nuclei,"filter_source":get(report)}
    refs={"nucleos":[subset(n,("id_proyecto_nucleo","nombre_nucleo")) for n in nuclei],
          "afectaciones":[],"convenios":[],"asambleas":[]}
    if original:
        for n in nuclei:
            pn=n["id_proyecto_nucleo"];affects=get(f"/api/proyecto-nucleo/{pn}/afectaciones")
            unique={}
            for a in affects:
                refs["afectaciones"].append(subset(a,A_FIELDS))
                for c in get(f"/api/afectaciones/{a['id_afectacion']}/convenios"):
                    unique[c["id_convenio"]]={"item":subset(c,C_FIELDS),"id_afectacion":a["id_afectacion"]}
            refs["convenios"].extend(unique.values())
            refs["asambleas"].extend(subset(a,S_FIELDS) for a in get(f"/api/proyecto-nucleo/{pn}/asambleas"))
    elif nuclei:
        refs=get("/api/reportes/referencias-contexto",params=[("id_proyecto_nucleo",n["id_proyecto_nucleo"]) for n in nuclei])
    result["refs"]=normalized(refs)
    result["rows"]=get(report+(f"&id_proyecto_nucleo={selected_nucleus}" if selected_nucleus else ""))
    return result


@pytest.mark.parametrize("screen",["colectivos","derechos_colectivos","estado_financiero"])
def test_screen_flow_comparison(references_env, screen):
    env=references_env;variants={"original":[],"optimized":[]}
    with TestClient(app) as client:
        for i in range(5):
            payloads=[]
            for original in ((True,False) if i%2==0 else (False,True)):
                stats={"requests":0,"sql":0,"objects":0,"response_bytes":0}
                def sql(conn,cursor,statement,params,context,many):
                    if statement.lstrip().upper().startswith(("SELECT","WITH")):stats["sql"]+=1
                def loaded(session,instance):stats["objects"]+=1
                def get(path,allow_missing=False,**kwargs):
                    stats["requests"]+=1;r=client.get(path,**kwargs);stats["response_bytes"]+=len(r.content)
                    if allow_missing and r.status_code in (403,404):return None
                    assert r.status_code==200,(path,r.status_code,r.text)
                    return r.json()
                event.listen(env["connection"],"before_cursor_execute",sql);event.listen(Session,"loaded_as_persistent",loaded)
                try:
                    start=time.perf_counter()
                    if screen=="estado_financiero":data=financial(get,env["projects"][0],original)
                    else:data=collective(get,env["projects"][0],original,env["pns"][0] if screen=="derechos_colectivos" else None)
                    stats["ms"]=(time.perf_counter()-start)*1000
                    variants["original" if original else "optimized"].append(stats);payloads.append(data)
                finally:
                    event.remove(env["connection"],"before_cursor_execute",sql);event.remove(Session,"loaded_as_persistent",loaded)
            assert payloads[0]==payloads[1]
    result={v:{"median_ms":statistics.median(s["ms"] for s in samples),"samples":samples} for v,samples in variants.items()}
    if os.getenv("F06_EVIDENCE_DIR"):
        (Path(os.environ["F06_EVIDENCE_DIR"])/(screen+"-http-flow.json")).write_text(json.dumps(result,indent=2))
