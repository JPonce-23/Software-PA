"""Executable closure cases: real events are retained while KPIs deduplicate."""
import uuid


def _catalog(api, name):
    return {row["codigo"]: row["id_catalogo_opcion"] for row in api("GET", f"/api/catalogos/operativos/{name}").json()}


def _isolated_pn(api, target_domain):
    token = uuid.uuid4().hex[:10]
    tenencia = _catalog(api, "tipo_tenencia")["ejido"]
    project = api("POST", "/api/proyectos", expected=201, json={
        "clave_proyecto": f"XLS-{token}", "nombre_proyecto": "Cierre Excel QA",
    }).json()
    nucleus = api("POST", "/api/nucleos", expected=201, json={
        "id_municipio": target_domain["municipality"]["id_municipio"],
        "nombre_nucleo": f"Nucleo XLS {token}", "id_tipo_tenencia": tenencia,
    }).json()
    pn = api("POST", f"/api/proyectos/{project['id_proyecto']}/nucleos", expected=201,
             json={"id_nucleo": nucleus["id_nucleo"]}).json()
    return project, pn


def _dashboard(api, project_id):
    return {row["indicador"]: row for row in api("GET", f"/api/dashboard/kpi?id_proyecto={project_id}").json()}


def test_002_activity_kpis_deduplicate_by_cycle(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    cop = _catalog(api, "tipo_cop_operativo")
    for index in range(3):
        api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/actividades", expected=201,
            json={"tipo_actividad": "sensibilizacion", "id_tipo_cop_operativo": cop["ORIGEN"], "fecha_realizada": "2026-09-01", "responsable": f"S{index}"})
    for index in range(4):
        api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/actividades", expected=201,
            json={"tipo_actividad": "caminamiento", "id_tipo_cop_operativo": cop["TRANSVERSALES"], "fecha_realizada": "2026-09-02", "responsable": f"C{index}"})
    api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/actividades", expected=201,
        json={"tipo_actividad": "sensibilizacion", "id_tipo_cop_operativo": cop["ADICIONAL"], "fecha_realizada": "2026-09-03"})

    activities = api("GET", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/actividades").json()
    assert len(activities) == 8
    kpi = _dashboard(api, project["id_proyecto"])
    assert kpi["sensibilizacion_ORIGEN"]["realizado"] == 1
    assert kpi["sensibilizacion_ADICIONAL"]["realizado"] == 1
    assert kpi["caminamiento_TRANSVERSALES"]["realizado"] == 1


def test_002_all_operational_cop_codes_are_available(api):
    codes = _catalog(api, "tipo_cop_operativo")
    assert {"ORIGEN", "ADICIONAL", "2A_ADICIONAL", "COMPLEMENTARIAS", "TRANSVERSALES"} <= set(codes)


def test_003_periodic_reporting_separates_canonical_dates(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    cop = _catalog(api, "tipo_cop_operativo")
    api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/actividades", expected=201, json={
        "tipo_actividad": "sensibilizacion", "id_tipo_cop_operativo": cop["ORIGEN"],
        "fecha_programada": "2025-12-20", "fecha_realizada": "2026-01-10",
    })
    dec = api("GET", f"/api/reportes/avance-periodo?id_proyecto={project['id_proyecto']}&anio=2025&mes=12").json()
    jan = api("GET", f"/api/reportes/avance-periodo?id_proyecto={project['id_proyecto']}&anio=2026&mes=1&trimestre=1").json()
    assert dec[0]["indicador"] == "sensibilizacion_ORIGEN" and dec[0]["programado"] == 1 and dec[0]["realizado"] == 0
    assert jan[0]["indicador"] == "sensibilizacion_ORIGEN" and jan[0]["realizado"] == 1 and jan[0]["programado"] == 0 and jan[0]["trimestre"] == 1


def test_002_assemblies_and_ran_are_counted_by_entity(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    types = _catalog(api, "tipo_asamblea"); contexts = _catalog(api, "contexto_asamblea")
    results = _catalog(api, "resultado_convocatoria"); events = _catalog(api, "tipo_evento_ran")
    assemblies = []
    for ordinal in (1, 2):
        assemblies.append(api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/asambleas", expected=201, json={
            "id_tipo_asamblea": types["anuencia"], "id_contexto_asamblea": contexts["cop_original"],
            "convocatorias": [{"ordinal": 1, "fecha_programada": f"2026-09-0{ordinal}", "fecha_realizacion": f"2026-09-0{ordinal}", "id_resultado": results["celebrada"]}],
        }).json())
    ran = api("POST", "/api/tramites-ran", expected=201, json={
        "id_asamblea": assemblies[0]["id_asamblea"], "fecha_programada_ingreso": "2026-09-10",
        "eventos": [
            {"ordinal": 1, "id_tipo_evento": events["ingreso"], "fecha_evento": "2026-09-11", "numero_solicitud": "ING-1"},
            {"ordinal": 2, "id_tipo_evento": events["prevencion"], "fecha_evento": "2026-09-12"},
            {"ordinal": 3, "id_tipo_evento": events["reingreso"], "fecha_evento": "2026-09-13", "numero_solicitud": "REING-2"},
            {"ordinal": 4, "id_tipo_evento": events["calificacion"], "calificacion": "procedente"},
            {"ordinal": 5, "id_tipo_evento": events["inscripcion"], "fecha_evento": "2026-09-14"},
        ],
    }).json()
    assert ran["fecha_programada_ingreso"] == "2026-09-10" and len(ran["eventos"]) == 5
    assert {e["numero_solicitud"] for e in ran["eventos"] if e["numero_solicitud"]} == {"ING-1", "REING-2"}
    assert any(e["calificacion"] == "procedente" for e in ran["eventos"])
    kpi = _dashboard(api, project["id_proyecto"])
    assert kpi["asambleas"]["realizado"] == 2
    assert kpi["ingreso_ran_acta"]["realizado"] == 1


def test_002_convenio_ran_parcela_and_paid_indemnity(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    cop = _catalog(api, "tipo_cop_operativo"); events = _catalog(api, "tipo_evento_ran")
    tierra = next(iter(_catalog(api, "tipo_tierra").values())); titularidad = _catalog(api, "tipo_titularidad_unidad")["persona"]
    parcel = api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/parcelas", expected=201, json={"tipo_parcela": "individual", "no_parcela": "UNICA-002"}).json()
    unit = api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/unidades-agrarias", expected=201, json={"id_tipo_tierra": tierra, "id_tipo_titularidad": titularidad, "id_parcela": parcel["id_parcela"]}).json()
    affects = []
    for _ in range(2):
        affect = api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/afectaciones", expected=201, json={"tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]}).json()
        api("POST", f"/api/afectaciones/{affect['id_afectacion']}/unidades-agrarias", expected=201, json={"id_unidad_agraria": unit["id_unidad_agraria"]})
        affects.append(affect)
    collective = [api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/afectaciones", expected=201, json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]}).json() for _ in range(2)]
    agreement = api("POST", f"/api/afectaciones/{collective[0]['id_afectacion']}/convenios", expected=201, json={"tipo_convenio": "cop_original", "fecha_firma": "2026-09-20"}).json()
    api("POST", f"/api/convenios/{agreement['id_convenio']}/afectaciones", expected=201, json={"id_afectacion": collective[1]["id_afectacion"]})
    ran = api("POST", "/api/tramites-ran", expected=201, json={"id_convenio": agreement["id_convenio"], "fecha_programada_ingreso": "2026-09-21", "eventos": [
        {"ordinal": 1, "id_tipo_evento": events["ingreso"], "fecha_evento": "2026-09-22", "numero_solicitud": "C-1"},
        {"ordinal": 2, "id_tipo_evento": events["reingreso"], "fecha_evento": "2026-09-23", "numero_solicitud": "C-2"},
        {"ordinal": 3, "id_tipo_evento": events["inscripcion"], "fecha_evento": "2026-09-24"},
    ]}).json()
    indemnity = api("POST", f"/api/afectaciones/{affects[0]['id_afectacion']}/indemnizacion", expected=201, json={"estatus": "pagado"}).json()
    assert indemnity["estatus"] == "pagado" and ran["fecha_programada_ingreso"] == "2026-09-21"
    assert "no_parcela_ppt" not in parcel and "numero_parcela_ppt" not in parcel
    kpi = _dashboard(api, project["id_proyecto"])
    assert kpi["cop_colectivos"]["realizado"] == 1
    assert kpi["ingreso_ran_convenio"]["realizado"] == 1
    assert "parcelas_afectadas" not in kpi
