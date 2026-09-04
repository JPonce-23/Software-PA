"""Comprehensive test suite for migration 005 reporting closure (Casos A through V)."""
import uuid
import pytest
from .test_excel_closure_002 import _catalog, _isolated_pn, _dashboard


def _get_periodic(api, project_id, **params):
    query_parts = [f"id_proyecto={project_id}"]
    for key, val in params.items():
        if val is not None:
            query_parts.append(f"{key}={val}")
    qs = "&".join(query_parts)
    return api("GET", f"/api/reportes/avance-periodo?{qs}").json()


def test_caso_a_dedup_sensibilizacion(api, target_domain):
    """CASO A: 3 sensibilizaciones ORIGEN en meses distintos -> 3 ActividadCampo, 1 hito, primera fecha determina periodo."""
    project, pn = _isolated_pn(api, target_domain)
    cop = _catalog(api, "tipo_cop_operativo")
    pn_id = pn["id_proyecto_nucleo"]

    # 3 sensibilizaciones en marzo, abril y mayo
    api("POST", f"/api/proyecto-nucleo/{pn_id}/actividades", expected=201, json={
        "tipo_actividad": "sensibilizacion", "id_tipo_cop_operativo": cop["ORIGEN"],
        "fecha_realizada": "2026-03-10", "responsable": "S-Marzo"
    })
    api("POST", f"/api/proyecto-nucleo/{pn_id}/actividades", expected=201, json={
        "tipo_actividad": "sensibilizacion", "id_tipo_cop_operativo": cop["ORIGEN"],
        "fecha_realizada": "2026-04-15", "responsable": "S-Abril"
    })
    api("POST", f"/api/proyecto-nucleo/{pn_id}/actividades", expected=201, json={
        "tipo_actividad": "sensibilizacion", "id_tipo_cop_operativo": cop["ORIGEN"],
        "fecha_realizada": "2026-05-20", "responsable": "S-Mayo"
    })

    # Persistencia = 3
    activities = api("GET", f"/api/proyecto-nucleo/{pn_id}/actividades").json()
    assert len(activities) == 3

    # Reporte mensual: realizado en marzo = 1; en abril y mayo = 0 para este hito
    rep_mar = _get_periodic(api, project["id_proyecto"], anio=2026, mes=3, indicador="sensibilizacion_ORIGEN")
    rep_abr = _get_periodic(api, project["id_proyecto"], anio=2026, mes=4, indicador="sensibilizacion_ORIGEN")
    rep_may = _get_periodic(api, project["id_proyecto"], anio=2026, mes=5, indicador="sensibilizacion_ORIGEN")

    assert len(rep_mar) == 1 and rep_mar[0]["realizado"] == 1
    assert len(rep_abr) == 0 or rep_abr[0]["realizado"] == 0
    assert len(rep_may) == 0 or rep_may[0]["realizado"] == 0

    # Dashboard anual = 1 realizado, cantidad = 1
    kpis = _dashboard(api, project["id_proyecto"])
    assert kpis["sensibilizacion_ORIGEN"]["realizado"] == 1
    assert kpis["sensibilizacion_ORIGEN"]["cantidad"] == 1


def test_caso_b_dedup_ciclos_independientes(api, target_domain):
    """CASO B: Mismo PN con ciclo ORIGEN y ADICIONAL produce 1 hito independiente por ciclo."""
    project, pn = _isolated_pn(api, target_domain)
    cop = _catalog(api, "tipo_cop_operativo")
    pn_id = pn["id_proyecto_nucleo"]

    api("POST", f"/api/proyecto-nucleo/{pn_id}/actividades", expected=201, json={
        "tipo_actividad": "sensibilizacion", "id_tipo_cop_operativo": cop["ORIGEN"],
        "fecha_realizada": "2026-03-01",
    })
    api("POST", f"/api/proyecto-nucleo/{pn_id}/actividades", expected=201, json={
        "tipo_actividad": "sensibilizacion", "id_tipo_cop_operativo": cop["ADICIONAL"],
        "fecha_realizada": "2026-04-01",
    })

    kpis = _dashboard(api, project["id_proyecto"])
    assert kpis["sensibilizacion_ORIGEN"]["realizado"] == 1
    assert kpis["sensibilizacion_ADICIONAL"]["realizado"] == 1


def test_caso_c_caminamientos_transversales(api, target_domain):
    """CASO C: 4 caminamientos TRANSVERSALES en distintos meses -> total anual = 1."""
    project, pn = _isolated_pn(api, target_domain)
    cop = _catalog(api, "tipo_cop_operativo")
    pn_id = pn["id_proyecto_nucleo"]

    for month in (1, 3, 6, 9):
        api("POST", f"/api/proyecto-nucleo/{pn_id}/actividades", expected=201, json={
            "tipo_actividad": "caminamiento", "id_tipo_cop_operativo": cop["TRANSVERSALES"],
            "fecha_realizada": f"2026-0{month}-15", "responsable": f"C-M{month}",
        })

    kpis = _dashboard(api, project["id_proyecto"])
    assert kpis["caminamiento_TRANSVERSALES"]["realizado"] == 1
    assert kpis["caminamiento_TRANSVERSALES"]["cantidad"] == 1


def test_caso_d_asamblea_convocatorias_separadas(api, target_domain):
    """CASO D: Asamblea con 1a convocatoria marzo (no_verificativo) y 2a abril (celebrada).
    -> programado marzo, realizado abril, cantidad = 1."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    types = _catalog(api, "tipo_asamblea")
    contexts = _catalog(api, "contexto_asamblea")
    results = _catalog(api, "resultado_convocatoria")

    asamblea = api("POST", f"/api/proyecto-nucleo/{pn_id}/asambleas", expected=201, json={
        "id_tipo_asamblea": types["anuencia"],
        "id_contexto_asamblea": contexts["cop_original"],
        "convocatorias": [
            {"ordinal": 1, "fecha_programada": "2026-03-05", "id_resultado": results["no_verificativo"]},
            {"ordinal": 2, "fecha_programada": "2026-04-12", "fecha_realizacion": "2026-04-12", "id_resultado": results["celebrada"]},
        ],
    }).json()

    # Periódico: marzo programado = 1, realizado = 0
    rep_mar = _get_periodic(api, project["id_proyecto"], anio=2026, mes=3, indicador="asambleas")
    assert len(rep_mar) == 1 and rep_mar[0]["programado"] == 1 and rep_mar[0]["realizado"] == 0

    # Periódico: abril programado = 0, realizado = 1
    rep_abr = _get_periodic(api, project["id_proyecto"], anio=2026, mes=4, indicador="asambleas")
    assert len(rep_abr) == 1 and rep_abr[0]["programado"] == 0 and rep_abr[0]["realizado"] == 1

    # Dashboard anual = programado 1, realizado 1, cantidad 1
    kpis = _dashboard(api, project["id_proyecto"])
    assert kpis["asambleas"]["programado"] == 1
    assert kpis["asambleas"]["realizado"] == 1
    assert kpis["asambleas"]["cantidad"] == 1


def test_caso_e_asamblea_permanente_no_duplica(api, target_domain):
    """CASO E: 1 Asamblea + 2 SeguimientoEvento continuacion_asamblea -> sigue 1 Asamblea."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    types = _catalog(api, "tipo_asamblea")
    contexts = _catalog(api, "contexto_asamblea")
    results = _catalog(api, "resultado_convocatoria")
    events = _catalog(api, "tipo_evento_seguimiento")

    asamblea = api("POST", f"/api/proyecto-nucleo/{pn_id}/asambleas", expected=201, json={
        "id_tipo_asamblea": types["anuencia"],
        "id_contexto_asamblea": contexts["cop_original"],
        "convocatorias": [
            {"ordinal": 1, "fecha_programada": "2026-05-01", "fecha_realizacion": "2026-05-01", "id_resultado": results["celebrada"]},
        ],
    }).json()

    # Registrar 2 continuaciones de asamblea
    for i in (1, 2):
        api("POST", f"/api/proyecto-nucleo/{pn_id}/seguimiento", expected=201, json={
            "ambito": "colectivo",
            "entidad_tipo": "asamblea",
            "entidad_id": asamblea["id_asamblea"],
            "id_tipo_evento": events["continuacion_asamblea"],
            "fecha_evento": f"2026-05-1{i}",
            "detalle": f"Continuación de asamblea sesión {i}",
        })

    kpis = _dashboard(api, project["id_proyecto"])
    assert kpis["asambleas"]["realizado"] == 1
    assert kpis["asambleas"]["cantidad"] == 1


def test_caso_f_ran_acta_hitos_separados(api, target_domain):
    """CASO F: RAN acta programado feb, ingreso mar, prevencion abr, reingreso may, inscripcion jun.
    -> ingreso programado feb = 1, ingreso realizado mar = 1, inscripcion jun = 1, anual ingreso = 1 (nunca 2), anual inscripcion = 1."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    types = _catalog(api, "tipo_asamblea")
    contexts = _catalog(api, "contexto_asamblea")
    results = _catalog(api, "resultado_convocatoria")
    events = _catalog(api, "tipo_evento_ran")

    asamblea = api("POST", f"/api/proyecto-nucleo/{pn_id}/asambleas", expected=201, json={
        "id_tipo_asamblea": types["anuencia"],
        "id_contexto_asamblea": contexts["cop_original"],
        "convocatorias": [
            {"ordinal": 1, "fecha_programada": "2026-01-20", "fecha_realizacion": "2026-01-20", "id_resultado": results["celebrada"]},
        ],
    }).json()

    ran = api("POST", "/api/tramites-ran", expected=201, json={
        "id_asamblea": asamblea["id_asamblea"],
        "fecha_programada_ingreso": "2026-02-15",
        "eventos": [
            {"ordinal": 1, "id_tipo_evento": events["ingreso"], "fecha_evento": "2026-03-10", "numero_solicitud": "ACTA-ING"},
            {"ordinal": 2, "id_tipo_evento": events["prevencion"], "fecha_evento": "2026-04-05"},
            {"ordinal": 3, "id_tipo_evento": events["reingreso"], "fecha_evento": "2026-05-12", "numero_solicitud": "ACTA-REING"},
            {"ordinal": 4, "id_tipo_evento": events["inscripcion"], "fecha_evento": "2026-06-20"},
        ],
    }).json()

    # Periódico: febrero programado ingreso = 1
    rep_feb = _get_periodic(api, project["id_proyecto"], anio=2026, mes=2, indicador="ingreso_ran_acta")
    assert len(rep_feb) == 1 and rep_feb[0]["programado"] == 1 and rep_feb[0]["realizado"] == 0

    # Periódico: marzo realizado ingreso = 1
    rep_mar = _get_periodic(api, project["id_proyecto"], anio=2026, mes=3, indicador="ingreso_ran_acta")
    assert len(rep_mar) == 1 and rep_mar[0]["realizado"] == 1

    # Periódico: mayo NO debe volver a sumar realizado en ingreso
    rep_may = _get_periodic(api, project["id_proyecto"], anio=2026, mes=5, indicador="ingreso_ran_acta")
    assert len(rep_may) == 0 or rep_may[0]["realizado"] == 0

    # Periódico: junio realizado inscripcion = 1
    rep_jun = _get_periodic(api, project["id_proyecto"], anio=2026, mes=6, indicador="inscripcion_ran_acta")
    assert len(rep_jun) == 1 and rep_jun[0]["realizado"] == 1

    # Anual: ingreso realizado = 1 (nunca 2), inscripcion = 1
    kpis = _dashboard(api, project["id_proyecto"])
    assert kpis["ingreso_ran_acta"]["programado"] == 1
    assert kpis["ingreso_ran_acta"]["realizado"] == 1
    assert kpis["ingreso_ran_acta"]["cantidad"] == 1
    assert kpis["inscripcion_ran_acta"]["realizado"] == 1
    assert kpis["inscripcion_ran_acta"]["cantidad"] == 1


def test_caso_g_ran_convenio_hitos_separados(api, target_domain):
    """CASO G: RAN convenio con mismo patrón ingreso/reingreso/inscripción."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")
    events = _catalog(api, "tipo_evento_ran")

    affect = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201, json={
        "tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]
    }).json()
    convenio = api("POST", f"/api/afectaciones/{affect['id_afectacion']}/convenios", expected=201, json={
        "tipo_convenio": "cop_original", "fecha_firma": "2026-02-01"
    }).json()

    api("POST", "/api/tramites-ran", expected=201, json={
        "id_convenio": convenio["id_convenio"],
        "fecha_programada_ingreso": "2026-02-10",
        "eventos": [
            {"ordinal": 1, "id_tipo_evento": events["ingreso"], "fecha_evento": "2026-03-01", "numero_solicitud": "CONV-ING"},
            {"ordinal": 2, "id_tipo_evento": events["reingreso"], "fecha_evento": "2026-04-10", "numero_solicitud": "CONV-REING"},
            {"ordinal": 3, "id_tipo_evento": events["inscripcion"], "fecha_evento": "2026-06-15"},
        ],
    })

    kpis = _dashboard(api, project["id_proyecto"])
    assert kpis["ingreso_ran_convenio"]["realizado"] == 1
    assert kpis["ingreso_ran_convenio"]["cantidad"] == 1
    assert kpis["inscripcion_ran_convenio"]["realizado"] == 1


def test_caso_h_convenio_multiples_afectaciones_no_multiplica(api, target_domain):
    """CASO H: 1 Convenio ligado a 3 Afectaciones -> firma realizada = 1."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    affects = [
        api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201, json={
            "tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]
        }).json() for _ in range(3)
    ]
    convenio = api("POST", f"/api/afectaciones/{affects[0]['id_afectacion']}/convenios", expected=201, json={
        "tipo_convenio": "cop_original", "fecha_firma": "2026-07-20", "superficie_ha": 5.5, "monto_100": 500000.00
    }).json()
    for aff in affects[1:]:
        api("POST", f"/api/convenios/{convenio['id_convenio']}/afectaciones", expected=201, json={
            "id_afectacion": aff["id_afectacion"]
        })

    kpis = _dashboard(api, project["id_proyecto"])
    assert kpis["cop_colectivos"]["realizado"] == 1
    assert kpis["cop_colectivos"]["cantidad"] == 1
    assert float(kpis["cop_colectivos"]["superficie_ha"]) == 5.5
    assert float(kpis["cop_colectivos"]["monto"]) == 500000.00


def test_caso_i_parcela_multiples_afectaciones_no_inventa_periodo(api, target_domain):
    """CASO I: una parcela ligada a varias afectaciones es snapshot; alta técnica no crea avance periódico."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    titularidad = _catalog(api, "tipo_titularidad_unidad")["persona"]

    parcel = api("POST", f"/api/proyecto-nucleo/{pn_id}/parcelas", expected=201, json={
        "tipo_parcela": "individual", "no_parcela": "P-CASO-I"
    }).json()
    unit = api("POST", f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias", expected=201, json={
        "id_tipo_tierra": tierra, "id_tipo_titularidad": titularidad, "id_parcela": parcel["id_parcela"]
    }).json()

    for _ in range(3):
        aff = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201, json={
            "tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]
        }).json()
        api("POST", f"/api/afectaciones/{aff['id_afectacion']}/unidades-agrarias", expected=201, json={
            "id_unidad_agraria": unit["id_unidad_agraria"]
        })

    rep = _get_periodic(api, project["id_proyecto"], indicador="parcelas_afectadas")
    assert rep == []


def test_caso_j_actividad_periodos_separados(api, target_domain):
    """CASO J: Actividad programada 2025-12-20, realizada 2026-01-10 -> dic 2025 prog 1, ene 2026 real 1."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    api("POST", f"/api/proyecto-nucleo/{pn_id}/actividades", expected=201, json={
        "tipo_actividad": "sensibilizacion", "id_tipo_cop_operativo": cop["ORIGEN"],
        "fecha_programada": "2025-12-20", "fecha_realizada": "2026-01-10",
    })

    dec = _get_periodic(api, project["id_proyecto"], anio=2025, mes=12, indicador="sensibilizacion_ORIGEN")
    jan = _get_periodic(api, project["id_proyecto"], anio=2026, mes=1, indicador="sensibilizacion_ORIGEN")

    assert len(dec) == 1 and dec[0]["programado"] == 1 and dec[0]["realizado"] == 0
    assert len(jan) == 1 and jan[0]["realizado"] == 1 and jan[0]["programado"] == 0 and jan[0]["trimestre"] == 1


def test_caso_k_convenio_periodos_separados(api, target_domain):
    """CASO K: Convenio programado Q1, firmado Q2 -> periodos separados."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    aff = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201, json={
        "tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]
    }).json()
    api("POST", f"/api/afectaciones/{aff['id_afectacion']}/convenios", expected=201, json={
        "tipo_convenio": "cop_original", "fecha_programada_firma": "2026-02-15", "fecha_firma": "2026-05-10"
    })

    q1 = _get_periodic(api, project["id_proyecto"], anio=2026, mes=2, indicador="cop_colectivos")
    q2 = _get_periodic(api, project["id_proyecto"], anio=2026, mes=5, indicador="cop_colectivos")

    assert len(q1) == 1 and q1[0]["programado"] == 1 and q1[0]["realizado"] == 0 and q1[0]["trimestre"] == 1
    assert len(q2) == 1 and q2[0]["realizado"] == 1 and q2[0]["programado"] == 0 and q2[0]["trimestre"] == 2


def test_caso_l_asamblea_periodos_separados(api, target_domain):
    """CASO L: Asamblea programada Q2, celebrada Q3 -> periodos separados."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    types = _catalog(api, "tipo_asamblea")
    contexts = _catalog(api, "contexto_asamblea")
    results = _catalog(api, "resultado_convocatoria")

    api("POST", f"/api/proyecto-nucleo/{pn_id}/asambleas", expected=201, json={
        "id_tipo_asamblea": types["anuencia"],
        "id_contexto_asamblea": contexts["cop_original"],
        "convocatorias": [
            {"ordinal": 1, "fecha_programada": "2026-05-10", "fecha_realizacion": "2026-08-15", "id_resultado": results["celebrada"]},
        ],
    })

    may = _get_periodic(api, project["id_proyecto"], anio=2026, mes=5, indicador="asambleas")
    aug = _get_periodic(api, project["id_proyecto"], anio=2026, mes=8, indicador="asambleas")

    assert len(may) == 1 and may[0]["programado"] == 1 and may[0]["realizado"] == 0 and may[0]["trimestre"] == 2
    assert len(aug) == 1 and aug[0]["realizado"] == 1 and aug[0]["programado"] == 0 and aug[0]["trimestre"] == 3


def test_caso_m_ran_tres_periodos(api, target_domain):
    """CASO M: RAN programado Q1, ingreso Q2, inscripción Q4 -> tres periodos correctos."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    types = _catalog(api, "tipo_asamblea")
    contexts = _catalog(api, "contexto_asamblea")
    results = _catalog(api, "resultado_convocatoria")
    events = _catalog(api, "tipo_evento_ran")

    asamblea = api("POST", f"/api/proyecto-nucleo/{pn_id}/asambleas", expected=201, json={
        "id_tipo_asamblea": types["anuencia"],
        "id_contexto_asamblea": contexts["cop_original"],
        "convocatorias": [
            {"ordinal": 1, "fecha_programada": "2026-01-05", "fecha_realizacion": "2026-01-05", "id_resultado": results["celebrada"]},
        ],
    }).json()

    api("POST", "/api/tramites-ran", expected=201, json={
        "id_asamblea": asamblea["id_asamblea"],
        "fecha_programada_ingreso": "2026-01-15",
        "eventos": [
            {"ordinal": 1, "id_tipo_evento": events["ingreso"], "fecha_evento": "2026-04-10"},
            {"ordinal": 2, "id_tipo_evento": events["inscripcion"], "fecha_evento": "2026-10-20"},
        ],
    })

    # Q1 prog ingreso
    p_q1 = _get_periodic(api, project["id_proyecto"], anio=2026, mes=1, indicador="ingreso_ran_acta")
    assert len(p_q1) == 1 and p_q1[0]["programado"] == 1 and p_q1[0]["trimestre"] == 1

    # Q2 real ingreso
    p_q2 = _get_periodic(api, project["id_proyecto"], anio=2026, mes=4, indicador="ingreso_ran_acta")
    assert len(p_q2) == 1 and p_q2[0]["realizado"] == 1 and p_q2[0]["trimestre"] == 2

    # Q4 real inscripción
    p_q4 = _get_periodic(api, project["id_proyecto"], anio=2026, mes=10, indicador="inscripcion_ran_acta")
    assert len(p_q4) == 1 and p_q4[0]["realizado"] == 1 and p_q4[0]["trimestre"] == 4


def test_caso_n_trimestres_calendario(api, target_domain):
    """CASO N: Trimestres: ene-mar=1, abr-jun=2, jul-sep=3, oct-dic=4."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    cycles = [
        (2, 1, "ORIGEN"),
        (5, 2, "ADICIONAL"),
        (8, 3, "COMPLEMENTARIAS"),
        (11, 4, "TRANSVERSALES"),
    ]
    for m, q, cycle in cycles:
        api("POST", f"/api/proyecto-nucleo/{pn_id}/actividades", expected=201, json={
            "tipo_actividad": "caminamiento", "id_tipo_cop_operativo": cop[cycle],
            "fecha_realizada": f"2026-{m:02d}-15", "responsable": f"Q{q}",
        })
        rep = _get_periodic(api, project["id_proyecto"], anio=2026, mes=m, indicador=f"caminamiento_{cycle}")
        assert len(rep) >= 1
        assert rep[0]["trimestre"] == q


def test_caso_o_colectivo_vs_individual(api, target_domain):
    """CASO O: Mismo proyecto: 1 COP colectivo original, 2 COP individuales originales.
    Filtro ambito=colectivo -> 1, ambito=individual -> 2; sin filtro -> diferenciables por dimensión."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    # 1 colectivo programado
    aff_col = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201, json={
        "tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]
    }).json()
    api("POST", f"/api/afectaciones/{aff_col['id_afectacion']}/convenios", expected=201, json={
        "tipo_convenio": "cop_original", "fecha_programada_firma": "2026-06-01"
    })

    # 2 individuales programados
    for _ in (1, 2):
        aff_ind = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201, json={
            "tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]
        }).json()
        api("POST", f"/api/afectaciones/{aff_ind['id_afectacion']}/convenios", expected=201, json={
            "tipo_convenio": "cop_original", "fecha_programada_firma": "2026-06-02"
        })

    # Filtro colectivo
    rep_col = _get_periodic(api, project["id_proyecto"], ambito="colectivo", anio=2026, mes=6)
    col_convenios = [r for r in rep_col if r["tipo_convenio"] == "cop_original"]
    assert len(col_convenios) == 1 and col_convenios[0]["programado"] == 1

    # Filtro individual
    rep_ind = _get_periodic(api, project["id_proyecto"], ambito="individual", anio=2026, mes=6)
    ind_convenios = [r for r in rep_ind if r["tipo_convenio"] == "cop_original"]
    assert len(ind_convenios) == 1 and ind_convenios[0]["programado"] == 2

    # Sin filtro: diferenciables por ámbito
    all_rep = _get_periodic(api, project["id_proyecto"], anio=2026, mes=6)
    ambitos = {r["ambito"] for r in all_rep if r["tipo_convenio"] == "cop_original"}
    assert "colectivo" in ambitos and "individual" in ambitos


def test_caso_p_tipos_convenio_distinguibles(api, target_domain):
    """CASO P: Verificar que cop_original, modificatorio, superficie_adicional, obras_complementarias,
    ampliacion y ampliacion_remanente son distinguibles y no aparecen todos como otros_instrumentos."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    # Colectivo: cop_original, modificatorio, superficie_adicional, obras_complementarias
    aff_col = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201, json={
        "tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]
    }).json()
    cop_col = api("POST", f"/api/afectaciones/{aff_col['id_afectacion']}/convenios", expected=201, json={
        "tipo_convenio": "cop_original", "fecha_firma": "2026-07-01", "consecutivo": 1
    }).json()
    for idx, t in enumerate(["modificatorio", "superficie_adicional", "obras_complementarias"]):
        api("POST", f"/api/afectaciones/{aff_col['id_afectacion']}/convenios", expected=201, json={
            "tipo_convenio": t, "fecha_firma": f"2026-07-{idx+2:02d}",
            "id_convenio_padre": cop_col["id_convenio"], "consecutivo": idx + 2
        })

    # Individual: cop_original, ampliacion, ampliacion_remanente
    aff_ind = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201, json={
        "tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]
    }).json()
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    titularidad = _catalog(api, "tipo_titularidad_unidad")["persona"]
    token = uuid.uuid4().hex[:6]
    parcel = api("POST", f"/api/proyecto-nucleo/{pn_id}/parcelas", expected=201, json={
        "tipo_parcela": "individual", "no_parcela": f"P-{token}"
    }).json()
    unit = api("POST", f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias", expected=201, json={
        "id_parcela": parcel["id_parcela"], "id_tipo_tierra": tierra, "id_tipo_titularidad": titularidad
    }).json()
    api("POST", f"/api/afectaciones/{aff_ind['id_afectacion']}/unidades-agrarias", expected=201, json={
        "id_unidad_agraria": unit["id_unidad_agraria"]
    })
    cop_ind = api("POST", f"/api/afectaciones/{aff_ind['id_afectacion']}/convenios", expected=201, json={
        "tipo_convenio": "cop_original", "fecha_programada_firma": "2026-07-10", "consecutivo": 1
    }).json()
    for idx, t in enumerate(["ampliacion", "ampliacion_remanente"]):
        api("POST", f"/api/afectaciones/{aff_ind['id_afectacion']}/convenios", expected=201, json={
            "tipo_convenio": t, "fecha_programada_firma": f"2026-07-{idx+11:02d}",
            "id_convenio_padre": cop_ind["id_convenio"], "consecutivo": idx + 2
        })

    rep = _get_periodic(api, project["id_proyecto"], anio=2026, mes=7)
    tipos_encontrados = {r["tipo_convenio"] for r in rep if r["tipo_convenio"]}
    expected_types = {
        "cop_original", "modificatorio", "superficie_adicional",
        "obras_complementarias", "ampliacion", "ampliacion_remanente"
    }
    assert expected_types <= tipos_encontrados

    # Ninguno debe reportar indicador 'otros_instrumentos'
    indicadores = {r["indicador"] for r in rep}
    assert "otros_instrumentos" not in indicadores


def test_caso_q_tipos_cop_distinguibles(api, target_domain):
    """CASO Q: Tipos COP ORIGEN, ADICIONAL, 2A_ADICIONAL, COMPLEMENTARIAS, TRANSVERSALES son distinguibles."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    for idx, codigo in enumerate(["ORIGEN", "ADICIONAL", "2A_ADICIONAL", "COMPLEMENTARIAS", "TRANSVERSALES"]):
        api("POST", f"/api/proyecto-nucleo/{pn_id}/actividades", expected=201, json={
            "tipo_actividad": "sensibilizacion", "id_tipo_cop_operativo": cop[codigo],
            "fecha_realizada": "2026-08-01", "responsable": f"Resp {codigo}",
        })

    rep = _get_periodic(api, project["id_proyecto"], anio=2026, mes=8)
    cop_encontrados = {r["tipo_cop_operativo"] for r in rep if r["tipo_cop_operativo"]}
    for codigo in ("ORIGEN", "ADICIONAL", "2A_ADICIONAL", "COMPLEMENTARIAS", "TRANSVERSALES"):
        assert codigo in cop_encontrados


def test_caso_r_destino_superficie_no_inventa_periodo(api, target_domain):
    """CASO R: Una Afectación con varias unidades: TUC, camino, canal con superficies específicas.
    Las superficies específicas son el snapshot canónico; su alta no inventa un periodo."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    titularidad = _catalog(api, "tipo_titularidad_unidad")["nucleo_agrario"]
    destinos = _catalog(api, "destino_superficie")

    aff = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201, json={
        "tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"], "superficie_afectada_ha": 10.0
    }).json()

    units_data = [
        ("tuc", 4.0),
        ("camino", 3.0),
        ("canal", 3.0),
    ]
    for dest_code, sup in units_data:
        unit = api("POST", f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias", expected=201, json={
            "id_tipo_tierra": tierra, "id_tipo_titularidad": titularidad, "id_destino_superficie": destinos[dest_code]
        }).json()
        api("POST", f"/api/afectaciones/{aff['id_afectacion']}/unidades-agrarias", expected=201, json={
            "id_unidad_agraria": unit["id_unidad_agraria"], "superficie_afectada_ha": sup
        })

    assert _get_periodic(api, project["id_proyecto"], destino_superficie="tuc") == []
    assert _get_periodic(api, project["id_proyecto"], destino_superficie="camino") == []
    assert _get_periodic(api, project["id_proyecto"], destino_superficie="canal") == []


def test_caso_s_indemnizacion_fecha_resolucion(api, target_domain):
    """CASO S: Indemnización con estatus pagado y fecha_resolucion válida -> realizada en fecha_resolucion."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    aff = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201, json={
        "tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]
    }).json()
    api("POST", f"/api/afectaciones/{aff['id_afectacion']}/indemnizacion", expected=201, json={
        "estatus": "pagado", "fecha_resolucion": "2026-09-15"
    })

    rep = _get_periodic(api, project["id_proyecto"], anio=2026, mes=9, indicador="indemnizaciones")
    assert len(rep) == 1 and rep[0]["realizado"] == 1


def test_caso_t_indemnizacion_sin_fecha_no_inventa_periodo(api, target_domain):
    """CASO T: Indemnización con estatus pagado y fecha_resolucion=NULL -> NO inventar periodo realizado."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    aff = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201, json={
        "tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]
    }).json()
    ind = api("POST", f"/api/afectaciones/{aff['id_afectacion']}/indemnizacion", expected=201, json={
        "estatus": "pagado"
    }).json()
    assert ind["estatus"] == "pagado" and ind["fecha_resolucion"] is None

    rep = _get_periodic(api, project["id_proyecto"], indicador="indemnizaciones")
    # No debe haber filas con realizado > 0 para esta indemnización
    for r in rep:
        assert r["realizado"] == 0 or r["anio"] is None


def test_caso_u_seguimiento_funcional_no_muta_afecta_tuc(api, target_domain):
    """CASO U: Suspensión por expropiación directa en marzo, reapertura por nueva información en mayo
    se consultan como eventos sin alterar afecta_tuc."""
    token = uuid.uuid4().hex[:10]
    tenencia = _catalog(api, "tipo_tenencia")["ejido"]
    project = api("POST", "/api/proyectos", expected=201, json={
        "clave_proyecto": f"XLS-U-{token}", "nombre_proyecto": "Caso U QA",
    }).json()
    nucleus = api("POST", "/api/nucleos", expected=201, json={
        "id_municipio": target_domain["municipality"]["id_municipio"],
        "nombre_nucleo": f"Nucleo XLS U {token}", "id_tipo_tenencia": tenencia,
    }).json()
    pn = api("POST", f"/api/proyectos/{project['id_proyecto']}/nucleos", expected=201,
             json={"id_nucleo": nucleus["id_nucleo"]}).json()
    pn_id = pn["id_proyecto_nucleo"]
    api("PATCH", f"/api/proyecto-nucleo/{pn_id}", json={"afecta_tuc": True})
    pn = api("GET", f"/api/proyecto-nucleo/{pn_id}").json()
    event = _catalog(api, "tipo_evento_seguimiento")
    reason = _catalog(api, "motivo_seguimiento")

    assert pn["afecta_tuc"] is True

    # Suspensión en marzo
    api("POST", f"/api/proyecto-nucleo/{pn_id}/seguimiento", expected=201, json={
        "ambito": "colectivo", "id_tipo_evento": event["suspension"],
        "id_motivo": reason["expropiacion_directa"], "detalle": "Suspensión por decreto",
        "fecha_evento": "2026-03-01",
    })

    # Reapertura en mayo
    api("POST", f"/api/proyecto-nucleo/{pn_id}/seguimiento", expected=201, json={
        "ambito": "colectivo", "id_tipo_evento": event["reapertura"],
        "id_motivo": reason["nueva_informacion"], "detalle": "Reanudación con nueva información",
        "fecha_evento": "2026-05-01",
    })

    # afecta_tuc sigue intacto
    pn_current = api("GET", f"/api/proyecto-nucleo/{pn_id}").json()
    assert pn_current["afecta_tuc"] is True

    # Los eventos aparecen en sus fechas respectivas
    rep_mar = _get_periodic(api, project["id_proyecto"], anio=2026, mes=3, indicador="suspension")
    rep_may = _get_periodic(api, project["id_proyecto"], anio=2026, mes=5, indicador="reapertura")
    assert len(rep_mar) >= 1 and rep_mar[0]["realizado"] >= 1
    assert len(rep_may) >= 1 and rep_may[0]["realizado"] >= 1


def test_caso_v_consulta_indigena_evento_real(api, target_domain):
    """CASO V: consulta_indigena es un evento real y no produce cierre implícito."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    event = _catalog(api, "tipo_evento_seguimiento")

    api("POST", f"/api/proyecto-nucleo/{pn_id}/seguimiento", expected=201, json={
        "ambito": "colectivo", "id_tipo_evento": event["consulta_indigena"],
        "detalle": "Asamblea consultiva comunitaria", "fecha_evento": "2026-06-15",
    })

    rep = _get_periodic(api, project["id_proyecto"], anio=2026, mes=6, indicador="consulta_indigena")
    assert len(rep) == 1 and rep[0]["realizado"] == 1
