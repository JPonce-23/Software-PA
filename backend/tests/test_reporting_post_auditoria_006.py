"""Evidencia semántica ejecutable de los ajustes post-auditoría 006."""
from datetime import date

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import text

from app.database import SessionLocal
from .test_excel_closure_002 import _catalog, _isolated_pn


def _periodo(api, project_id, **params):
    qs = "&".join([f"id_proyecto={project_id}", *(f"{k}={v}" for k, v in params.items())])
    return api("GET", f"/api/reportes/avance-periodo?{qs}").json()


def test_006_snapshot_endpoint_is_published_without_period_dimensions():
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    # Protegido por RBAC, pero publicado: 401 prueba que no se ignora la ruta.
    assert client.get("/api/reportes/resumen-actual").status_code == 401


def test_006_openapi_exposes_snapshot_filters():
    from app.main import app
    operation = app.openapi()["paths"]["/api/reportes/resumen-actual"]["get"]
    names = {parameter["name"] for parameter in operation["parameters"]}
    assert {"id_proyecto", "id_entidad", "ambito", "indicador", "tipo_cop_operativo", "destino_superficie"} <= names
    assert not {"anio", "mes", "trimestre"} & names


@pytest.mark.parametrize("codigo", ["ORIGEN", "ADICIONAL", "2A_ADICIONAL", "COMPLEMENTARIAS", "TRANSVERSALES"])
def test_006_asamblea_preserva_cada_cop(api, target_domain, codigo):
    project, pn = _isolated_pn(api, target_domain)
    cop, tipos, contextos, resultados = (_catalog(api, x) for x in ("tipo_cop_operativo", "tipo_asamblea", "contexto_asamblea", "resultado_convocatoria"))
    api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/asambleas", expected=201, json={"id_tipo_asamblea": tipos["anuencia"], "id_contexto_asamblea": contextos["cop_original"], "id_tipo_cop_operativo": cop[codigo], "convocatorias": [{"ordinal": 1, "fecha_programada": "2026-03-10", "fecha_realizacion": "2026-03-10", "id_resultado": resultados["celebrada"]}]})
    rows = _periodo(api, project["id_proyecto"], anio=2026, mes=3, indicador="asambleas", tipo_cop_operativo=codigo)
    assert len(rows) == 1 and rows[0]["programado"] == rows[0]["realizado"] == rows[0]["cantidad"] == 1


def test_006_retiro_y_ran_no_se_mezclan(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    tipos, contextos, resultados, events = (_catalog(api, x) for x in ("tipo_asamblea", "contexto_asamblea", "resultado_convocatoria", "tipo_evento_ran"))
    a = api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/asambleas", expected=201, json={"id_tipo_asamblea": tipos["retiro_fondos"], "id_contexto_asamblea": contextos["retiro_fondos"], "convocatorias": [{"ordinal": 1,"fecha_programada":"2026-03-01","id_resultado":resultados["no_verificativo"]},{"ordinal":2,"fecha_programada":"2026-03-10","fecha_realizacion":"2026-03-10","id_resultado":resultados["celebrada"]}]}).json()
    api("POST", "/api/tramites-ran", expected=201, json={"id_asamblea":a["id_asamblea"],"eventos":[{"ordinal":1,"id_tipo_evento":events["ingreso"],"fecha_evento":"2026-03-11"},{"ordinal":2,"id_tipo_evento":events["reingreso"],"fecha_evento":"2026-04-01"},{"ordinal":3,"id_tipo_evento":events["inscripcion"],"fecha_evento":"2026-05-01"}]})
    assert len(_periodo(api, project["id_proyecto"], indicador="retiro_fondos")) == 1
    assert not _periodo(api, project["id_proyecto"], indicador="asambleas")
    assert len(_periodo(api, project["id_proyecto"], indicador="ingreso_ran_retiro_fondos")) == 1
    assert not _periodo(api, project["id_proyecto"], indicador="ingreso_ran_acta")


@pytest.mark.parametrize("codigo", ["ORIGEN", "ADICIONAL"])
def test_006_ran_acta_cop_ingreso_reingreso_e_inscripcion(api, target_domain, codigo):
    project, pn = _isolated_pn(api, target_domain)
    cop, tipos, contextos, resultados, events = (_catalog(api, x) for x in ("tipo_cop_operativo", "tipo_asamblea", "contexto_asamblea", "resultado_convocatoria", "tipo_evento_ran"))
    a = api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/asambleas", expected=201, json={"id_tipo_asamblea":tipos["anuencia"],"id_contexto_asamblea":contextos["cop_original"],"id_tipo_cop_operativo":cop[codigo],"convocatorias":[{"ordinal":1,"fecha_programada":"2026-02-01","fecha_realizacion":"2026-02-01","id_resultado":resultados["celebrada"]}]}).json()
    api("POST", "/api/tramites-ran", expected=201, json={"id_asamblea":a["id_asamblea"],"fecha_programada_ingreso":"2026-02-10","eventos":[{"ordinal":1,"id_tipo_evento":events["ingreso"],"fecha_evento":"2026-03-01"},{"ordinal":2,"id_tipo_evento":events["reingreso"],"fecha_evento":"2026-05-01"},{"ordinal":3,"id_tipo_evento":events["inscripcion"],"fecha_evento":"2026-06-01"}]})
    ingreso = _periodo(api, project["id_proyecto"], indicador="ingreso_ran_acta", tipo_cop_operativo=codigo)
    ins = _periodo(api, project["id_proyecto"], indicador="inscripcion_ran_acta", tipo_cop_operativo=codigo)
    assert len(ingreso) == 2 and len(ins) == 1
    assert sum(r["programado"] for r in ingreso) == sum(r["realizado"] for r in ingreso) == 1
    assert ingreso[0]["cantidad"] == ingreso[1]["cantidad"] == ins[0]["cantidad"] == 1
    assert not _periodo(api, project["id_proyecto"], anio=2026, mes=5, indicador="ingreso_ran_acta", tipo_cop_operativo=codigo)


def test_006_snapshot_nucleos_no_temporal(api, target_domain):
    project, _ = _isolated_pn(api, target_domain)
    rows = api("GET", f"/api/reportes/resumen-actual?id_proyecto={project['id_proyecto']}&indicador=total_nucleos").json()
    assert len(rows) == 1 and rows[0]["cantidad"] >= 1 and "anio" not in rows[0] and "mes" not in rows[0]


def test_006_fifonafe_colectivo_exige_numero_y_fecha(api, target_domain):
    project, pn = _isolated_pn(api, target_domain); pnid = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo"); eventos = _catalog(api, "tipo_evento_fifonafe")
    aff = api("POST", f"/api/proyecto-nucleo/{pnid}/afectaciones", expected=201, json={"tipo_afectacion":"colectivo","id_tipo_cop_operativo":cop["ORIGEN"]}).json()
    codigos = ["oficio_fifonafe_dgaopr","oficio_dgaopr_representacion","respuesta_representacion_dgaopr","respuesta_dgaopr_fifonafe"]
    bad = api("POST", f"/api/proyecto-nucleo/{pnid}/fifonafe", expected=201, json={"ids_afectacion":[aff["id_afectacion"]],"eventos":[{"ordinal":i+1,"id_tipo_evento":eventos[c],"fecha_oficio":f"2026-0{i+1}-01",**({"numero_oficio":str(i)} if i<3 else {})} for i,c in enumerate(codigos)]}).json()
    assert not _periodo(api, project["id_proyecto"], indicador="fifonafe")
    good = api("POST", f"/api/proyecto-nucleo/{pnid}/fifonafe", expected=201, json={"ids_afectacion":[aff["id_afectacion"]],"eventos":[{"ordinal":i+1,"id_tipo_evento":eventos[c],"fecha_oficio":f"2026-0{i+1}-01","numero_oficio":str(i)} for i,c in enumerate(codigos)]}).json()
    rows = _periodo(api, project["id_proyecto"], indicador="fifonafe")
    assert len(rows) == 1 and rows[0]["mes"] == 4


def test_006_fifonafe_individual_no_exige_cadena_colectiva(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    pnid = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")
    afectacion = api(
        "POST",
        f"/api/proyecto-nucleo/{pnid}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "individual",
            "id_tipo_cop_operativo": cop["ORIGEN"],
        },
    ).json()

    tramite = api(
        "POST",
        f"/api/proyecto-nucleo/{pnid}/fifonafe",
        expected=201,
        json={
            "ids_afectacion": [afectacion["id_afectacion"]],
            "estatus": "completo",
            "eventos": [],
        },
    ).json()

    assert tramite["ambito"] == "individual"
    assert tramite["estatus"] == "completo"
    assert tramite["eventos"] == []
    assert not _periodo(
        api,
        project["id_proyecto"],
        indicador="fifonafe",
        ambito="individual",
    )


def test_006_fifonafe_colectivo_tres_de_cuatro_no_completa(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    pnid = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")
    tipos_evento = _catalog(api, "tipo_evento_fifonafe")
    afectacion = api(
        "POST",
        f"/api/proyecto-nucleo/{pnid}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "colectivo",
            "id_tipo_cop_operativo": cop["ORIGEN"],
        },
    ).json()
    codigos = (
        "oficio_fifonafe_dgaopr",
        "oficio_dgaopr_representacion",
        "respuesta_representacion_dgaopr",
    )
    tramite = api(
        "POST",
        f"/api/proyecto-nucleo/{pnid}/fifonafe",
        expected=201,
        json={
            "ids_afectacion": [afectacion["id_afectacion"]],
            "eventos": [
                {
                    "ordinal": ordinal,
                    "id_tipo_evento": tipos_evento[codigo],
                    "numero_oficio": f"FIF-3-4-{ordinal}",
                    "fecha_oficio": f"2026-0{ordinal}-15",
                }
                for ordinal, codigo in enumerate(codigos, start=1)
            ],
        },
    ).json()

    clave_hito = f"fifonafe:{tramite['id_tramite_fifonafe']}"
    with SessionLocal() as db:
        hito = db.execute(
            text(
                "SELECT count(*) FROM vw_hito_seguimiento "
                "WHERE clave_hito = :clave_hito AND indicador = 'fifonafe'"
            ),
            {"clave_hito": clave_hito},
        ).scalar_one()
    assert hito == 0
    assert not _periodo(
        api,
        project["id_proyecto"],
        indicador="fifonafe",
        ambito="colectivo",
    )
    api(
        "PATCH",
        f"/api/fifonafe/{tramite['id_tramite_fifonafe']}",
        expected=409,
        json={"estatus": "completo"},
    )


def test_006_fifonafe_max_fecha_filtrado_a_cuatro_oficios(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    pnid = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")
    tipos_evento = _catalog(api, "tipo_evento_fifonafe")
    afectacion = api(
        "POST",
        f"/api/proyecto-nucleo/{pnid}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "colectivo",
            "id_tipo_cop_operativo": cop["ORIGEN"],
        },
    ).json()
    codigos = (
        "oficio_fifonafe_dgaopr",
        "oficio_dgaopr_representacion",
        "respuesta_representacion_dgaopr",
        "respuesta_dgaopr_fifonafe",
    )
    eventos = [
        {
            "ordinal": ordinal,
            "id_tipo_evento": tipos_evento[codigo],
            "numero_oficio": f"FIF-4-4-{ordinal}",
            "fecha_oficio": f"2026-0{ordinal}-15",
        }
        for ordinal, codigo in enumerate(codigos, start=1)
    ]
    eventos.append(
        {
            "ordinal": 5,
            "id_tipo_evento": tipos_evento["otro"],
            "numero_oficio": "FIF-EXTRA-AGOSTO",
            "fecha_oficio": "2026-08-20",
        }
    )
    tramite = api(
        "POST",
        f"/api/proyecto-nucleo/{pnid}/fifonafe",
        expected=201,
        json={
            "ids_afectacion": [afectacion["id_afectacion"]],
            "eventos": eventos,
        },
    ).json()

    clave_hito = f"fifonafe:{tramite['id_tramite_fifonafe']}"
    with SessionLocal() as db:
        fechas = db.execute(
            text(
                "SELECT fecha_realizada FROM vw_hito_seguimiento "
                "WHERE clave_hito = :clave_hito AND indicador = 'fifonafe'"
            ),
            {"clave_hito": clave_hito},
        ).scalars().all()
    assert fechas == [date(2026, 4, 15)]

    abril = _periodo(
        api,
        project["id_proyecto"],
        anio=2026,
        mes=4,
        indicador="fifonafe",
        ambito="colectivo",
    )
    agosto = _periodo(
        api,
        project["id_proyecto"],
        anio=2026,
        mes=8,
        indicador="fifonafe",
        ambito="colectivo",
    )
    assert len(abril) == 1
    assert abril[0]["realizado"] == abril[0]["cantidad"] == 1
    assert agosto == []


@pytest.mark.parametrize("evento,motivo,detalle", [
    ("inicio", None, None), ("suspension", "expropiacion_directa", None),
    ("reapertura", "nueva_informacion", "reabre"), ("cierre", "otro", "cierra"),
    ("cambio_alcance", "nueva_informacion", "cambia"),
])
def test_006_transiciones_rechazan_fecha_ausente_y_aceptan_fecha(api, target_domain, evento, motivo, detalle):
    _, pn = _isolated_pn(api, target_domain); cats = _catalog(api, "tipo_evento_seguimiento"); reasons = _catalog(api, "motivo_seguimiento")
    body = {"ambito":"colectivo", "id_tipo_evento":cats[evento], "detalle":detalle}
    if motivo: body["id_motivo"] = reasons[motivo]
    api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/seguimiento", expected=409, json=body)
    body["fecha_evento"] = "2026-06-01"
    api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/seguimiento", expected=201, json=body)


def test_006_snapshot_parcela_nm_no_duplica(api, target_domain):
    project, pn = _isolated_pn(api, target_domain); pid=pn["id_proyecto_nucleo"]
    tierra=next(iter(_catalog(api,"tipo_tierra").values())); titular=_catalog(api,"tipo_titularidad_unidad")["persona"]; cop=_catalog(api,"tipo_cop_operativo")["ORIGEN"]
    p=api("POST",f"/api/proyecto-nucleo/{pid}/parcelas",expected=201,json={"tipo_parcela":"individual","no_parcela":"N-M-006"}).json(); u=api("POST",f"/api/proyecto-nucleo/{pid}/unidades-agrarias",expected=201,json={"id_parcela":p["id_parcela"],"id_tipo_tierra":tierra,"id_tipo_titularidad":titular}).json()
    for _ in range(3):
        a=api("POST",f"/api/proyecto-nucleo/{pid}/afectaciones",expected=201,json={"tipo_afectacion":"individual","id_tipo_cop_operativo":cop}).json(); api("POST",f"/api/afectaciones/{a['id_afectacion']}/unidades-agrarias",expected=201,json={"id_unidad_agraria":u["id_unidad_agraria"]})
    rows=api("GET",f"/api/reportes/resumen-actual?id_proyecto={project['id_proyecto']}&indicador=total_parcelas_afectadas").json(); assert len(rows)==1 and rows[0]["cantidad"]==1


def test_006_snapshot_superficie_destino_no_multiplica(api, target_domain):
    project,pn=_isolated_pn(api,target_domain); pid=pn["id_proyecto_nucleo"]; cop=_catalog(api,"tipo_cop_operativo")["ORIGEN"]; tierra=next(iter(_catalog(api,"tipo_tierra").values())); titular=_catalog(api,"tipo_titularidad_unidad")["nucleo_agrario"]; destinos=_catalog(api,"destino_superficie")
    a=api("POST",f"/api/proyecto-nucleo/{pid}/afectaciones",expected=201,json={"tipo_afectacion":"colectivo","id_tipo_cop_operativo":cop,"superficie_afectada_ha":8}).json()
    for destino,sup in (("tuc",5),("camino",2),("canal",1)):
        u=api("POST",f"/api/proyecto-nucleo/{pid}/unidades-agrarias",expected=201,json={"id_tipo_tierra":tierra,"id_tipo_titularidad":titular,"id_destino_superficie":destinos[destino]}).json(); api("POST",f"/api/afectaciones/{a['id_afectacion']}/unidades-agrarias",expected=201,json={"id_unidad_agraria":u["id_unidad_agraria"],"superficie_afectada_ha":sup})
    rows=api("GET",f"/api/reportes/resumen-actual?id_proyecto={project['id_proyecto']}&indicador=superficie_por_destino").json(); values={r["destino_superficie"]:float(r["superficie_ha"]) for r in rows}; assert {k:values[k] for k in ("tuc","camino","canal")} == {"tuc":5,"camino":2,"canal":1} and sum(values[k] for k in ("tuc","camino","canal"))==8


def test_006_total_cops_planeados_no_multiplica(api, target_domain):
    project,pn=_isolated_pn(api,target_domain); api("PATCH",f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}",json={"total_cops_planeados":3})
    ten=_catalog(api,"tipo_tenencia")["ejido"]; nuc=api("POST","/api/nucleos",expected=201,json={"id_municipio":target_domain["municipality"]["id_municipio"],"nombre_nucleo":f"COP PLANEADOS 006 {project['id_proyecto']}","id_tipo_tenencia":ten}).json(); pn2=api("POST",f"/api/proyectos/{project['id_proyecto']}/nucleos",expected=201,json={"id_nucleo":nuc["id_nucleo"],"total_cops_planeados":5}).json()
    cop=_catalog(api,"tipo_cop_operativo")["ORIGEN"]
    for target in (pn,pn2):
        for _ in range(2): api("POST",f"/api/proyecto-nucleo/{target['id_proyecto_nucleo']}/afectaciones",expected=201,json={"tipo_afectacion":"colectivo","id_tipo_cop_operativo":cop})
    rows=api("GET",f"/api/reportes/resumen-actual?id_proyecto={project['id_proyecto']}&indicador=total_cops_planeados").json(); assert len(rows)==1 and rows[0]["cantidad"]==8


def test_006_documento_cruzado_rechazado(api, target_domain):
    _, pn_a = _isolated_pn(api, target_domain)
    _, pn_b = _isolated_pn(api, target_domain)
    pn_a_id = pn_a["id_proyecto_nucleo"]
    pn_b_id = pn_b["id_proyecto_nucleo"]
    tipo_evento = _catalog(api, "tipo_evento_seguimiento")["reunion"]

    documento_b = api(
        "POST",
        f"/api/documentos/objetivos/proyecto_nucleo/{pn_b_id}",
        expected=201,
        json={
            "tipo_documento": "soporte_seguimiento_006",
            "estado": "disponible",
            "titulo": "Documento exclusivo de PN B",
        },
    ).json()
    evento = {
        "ambito": "colectivo",
        "id_tipo_evento": tipo_evento,
        "detalle": "Reunión respaldada documentalmente",
    }
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_a_id}/seguimiento",
        expected=409,
        json={**evento, "id_documento": documento_b["id_documento"]},
    )

    documento_a = api(
        "POST",
        f"/api/documentos/objetivos/proyecto_nucleo/{pn_a_id}",
        expected=201,
        json={
            "tipo_documento": "soporte_seguimiento_006",
            "estado": "disponible",
            "titulo": "Documento compatible con PN A",
        },
    ).json()
    creado = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_a_id}/seguimiento",
        expected=201,
        json={**evento, "id_documento": documento_a["id_documento"]},
    ).json()
    assert creado["id_proyecto_nucleo"] == pn_a_id
    assert creado["id_documento"] == documento_a["id_documento"]

    with SessionLocal() as db:
        actor = db.execute(
            text(
                "SELECT min(id_usuario) FROM usuario "
                "WHERE activo AND rol = 'admin'"
            )
        ).scalar_one()
        db.execute(
            text("SELECT set_config('app.current_user_id', :actor, true)"),
            {"actor": str(actor)},
        )
        with pytest.raises(Exception, match="ajeno al ProyectoNucleo"):
            db.execute(
                text(
                    "INSERT INTO seguimiento_evento "
                    "(id_proyecto_nucleo, ambito, id_tipo_evento, detalle, "
                    " id_documento, creado_por) "
                    "VALUES (:pn, 'colectivo', :tipo, 'Inserción cruzada directa', "
                    " :documento, :actor)"
                ),
                {
                    "pn": pn_a_id,
                    "tipo": tipo_evento,
                    "documento": documento_b["id_documento"],
                    "actor": actor,
                },
            )


def test_006_no_conflictos_sin_fecha_no_inventa_periodo(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    pnid = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")
    tipos_evento = _catalog(api, "tipo_evento_fifonafe")
    afectacion = api(
        "POST",
        f"/api/proyecto-nucleo/{pnid}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "colectivo",
            "id_tipo_cop_operativo": cop["ORIGEN"],
        },
    ).json()
    tramite = api(
        "POST",
        f"/api/proyecto-nucleo/{pnid}/fifonafe",
        expected=201,
        json={
            "ids_afectacion": [afectacion["id_afectacion"]],
            "hay_conflictos": False,
            "resultado_no_conflictos": "Sin conflictos; fecha exacta no disponible",
            "acuse_fifonafe_fecha": "2026-03-20",
            "eventos": [
                {
                    "ordinal": 1,
                    "id_tipo_evento": tipos_evento["otro"],
                    "numero_oficio": "FIF-NC-OTRO",
                    "fecha_oficio": "2026-08-25",
                }
            ],
        },
    ).json()
    assert tramite["hay_conflictos"] is False
    assert tramite["acuse_fifonafe_fecha"] == "2026-03-20"

    with SessionLocal() as db:
        hitos_temporales = db.execute(
            text(
                "SELECT count(*) FROM vw_hito_seguimiento "
                "WHERE id_proyecto = :proyecto "
                "AND indicador = 'informe_no_conflictos'"
            ),
            {"proyecto": project["id_proyecto"]},
        ).scalar_one()
    assert hitos_temporales == 0
    assert not _periodo(
        api,
        project["id_proyecto"],
        indicador="informe_no_conflictos",
    )
    assert not _periodo(
        api,
        project["id_proyecto"],
        anio=2026,
        mes=3,
        indicador="informe_no_conflictos",
    )
    assert not _periodo(
        api,
        project["id_proyecto"],
        anio=2026,
        mes=8,
        indicador="informe_no_conflictos",
    )
