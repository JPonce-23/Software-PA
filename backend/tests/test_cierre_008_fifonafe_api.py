"""Regresiones API post-008; todos los hechos son escenarios sintéticos QA."""

import uuid


def _catalog(api, name: str) -> dict[str, int]:
    return {
        row["codigo"]: row["id_catalogo_opcion"]
        for row in api("GET", f"/api/catalogos/operativos/{name}").json()
    }


def _document(api, entity_type: str, entity_id: int, title: str):
    return api(
        "POST", f"/api/documentos/objetivos/{entity_type}/{entity_id}",
        expected=201,
        json={"tipo_documento": "fifonafe_prueba_008", "estado": "disponible",
              "titulo": title},
    ).json()


def _event(api, procedure_id: int, event_type: int, ordinal: int, **extra):
    return api(
        "POST", f"/api/fifonafe/{procedure_id}/eventos", expected=201,
        json={"ordinal": ordinal, "id_tipo_evento": event_type, **extra},
    ).json()


def test_fifonafe_v2_rondas_triestado_y_reporting_sin_nm(api, target_domain):
    pn = target_domain["project_nucleus"]
    afectaciones = target_domain["collective"]
    tipos = _catalog(api, "tipo_evento_fifonafe")
    tramite = api(
        "POST",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/fifonafe",
        expected=201,
        json={
            "ids_afectacion": [a["id_afectacion"] for a in afectaciones],
            "referencia_expediente": "SINTETICO-008-NO-FOLIO-REAL",
            "hay_conflictos": False,
        },
    ).json()
    assert tramite["version_flujo"] == 2

    # Un evento sin ciclo se conserva, pero no concluye ninguna ronda.
    api(
        "POST", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/eventos",
        expected=201,
        json={"ordinal": 1, "id_tipo_evento": tipos["consulta_conflictos_enviada"],
              "fecha_oficio": "2026-02-01", "numero_oficio": "SINT-SIN-CICLO"},
    )
    api(
        "POST", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/eventos",
        expected=201,
        json={"ordinal": 2, "id_tipo_evento": tipos["consulta_conflictos_enviada"],
              "ciclo_consulta": 2, "fecha_oficio": "2026-02-02",
              "numero_oficio": "SINT-CICLO-2"},
    )
    documento = api(
        "POST",
        f"/api/documentos/objetivos/tramite_fifonafe/{tramite['id_tramite_fifonafe']}",
        expected=201,
        json={"tipo_documento": "fif_respuesta_conflictos", "estado": "disponible",
              "titulo": "Escenario sintético respuesta 008"},
    ).json()
    api(
        "POST", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/eventos",
        expected=201,
        json={"ordinal": 3, "id_tipo_evento": tipos["respuesta_conflictos_acreditada"],
              "ciclo_consulta": 2, "fecha_evento": "2026-02-03",
              "conflicto_impide_retiro": False,
              "id_documento": documento["id_documento"]},
    )
    cobertura = api(
        "GET",
        f"/api/reportes/fifonafe/cobertura?id_proyecto={target_domain['project']['id_proyecto']}",
    ).json()
    fila = next(x for x in cobertura if x["ambito"] == "colectivo")
    assert fila["universo_solicitudes"] >= 1
    assert fila["eventos_consulta_sin_ciclo"] >= 1
    avance = api(
        "GET",
        f"/api/reportes/avance-periodo?id_proyecto={target_domain['project']['id_proyecto']}"
        "&indicador=informe_no_conflictos",
    ).json()
    assert sum(x["realizado"] for x in avance) == 1  # no se multiplica por 2 afectaciones


def test_fifonafe_interviniente_no_crea_pago_y_evento_es_atomico(api, target_domain):
    pn = target_domain["project_nucleus"]
    afectacion = target_domain["individual"][0]
    tipos = _catalog(api, "tipo_evento_fifonafe")
    tramite = api(
        "POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/fifonafe",
        expected=201, json={"ids_afectacion": [afectacion["id_afectacion"]]},
    ).json()
    persona = api(
        "POST", f"/api/proyectos/{target_domain['project']['id_proyecto']}/personas",
        expected=201,
        json={"nombre": f"SINTETICO-{uuid.uuid4().hex[:8]}",
              "datos_identidad_incompletos": True, "origen_registro": "qa"},
    ).json()
    interviniente = api(
        "POST", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes",
        expected=201, json={"id_persona": persona["id_persona"], "rol": "receptor_designado"},
    ).json()
    assert interviniente["rol"] == "receptor_designado"

    evento = api(
        "POST", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/eventos",
        expected=201,
        json={"ordinal": 1, "id_tipo_evento": tipos["diferimiento_retiro"],
              "fecha_evento": "2026-03-01"},
    ).json()
    api(
        "PATCH", f"/api/eventos-fifonafe/{evento['id_evento_fifonafe']}",
        expected=422, json={"fecha_evento": "2026-03-02", "ordinal": 99},
    )
    actual = api(
        "GET", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/eventos"
    ).json()[0]
    assert actual["ordinal"] == 1 and actual["fecha_evento"] == "2026-03-01"
    api(
        "DELETE", f"/api/eventos-fifonafe/{evento['id_evento_fifonafe']}",
        json={"motivo": "Baja lógica de escenario sintético 008"},
    )
    # La API no expone ninguna creación de Pago por interviniente.
    assert "id_pago" not in interviniente


def test_fifonafe_v2_ruta_judicial_no_fabrica_ruta_ordinaria(api, target_domain):
    pn = target_domain["project_nucleus"]
    tipos = _catalog(api, "tipo_evento_fifonafe")
    tramite = api(
        "POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/fifonafe",
        expected=201,
        json={"ids_afectacion": [target_domain["individual"][0]["id_afectacion"]]},
    ).json()
    doc = _document(api, "tramite_fifonafe", tramite["id_tramite_fifonafe"],
                    "SINTETICO 008 vía judicial")
    _event(api, tramite["id_tramite_fifonafe"], tipos["requerimiento_judicial"], 1,
           fecha_evento="2026-04-01", id_documento=doc["id_documento"])
    api("PATCH", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}",
        expected=409, json={"estatus": "completo"})
    _event(api, tramite["id_tramite_fifonafe"], tipos["cumplimiento_judicial"], 2,
           fecha_evento="2026-04-15", id_documento=doc["id_documento"])
    completo = api("PATCH", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}",
                   json={"estatus": "completo"}).json()
    assert completo["estatus"] == "completo"
    codigos = {e["id_tipo_evento"] for e in completo["eventos"]}
    assert tipos["consulta_conflictos_enviada"] not in codigos
    assert tipos["resolucion_retiro_autorizada"] not in codigos


def test_fifonafe_v2_administrativo_no_completa_por_hitos_parciales(api, target_domain):
    pn = target_domain["project_nucleus"]
    tipos = _catalog(api, "tipo_evento_fifonafe")
    tramite = api(
        "POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/fifonafe",
        expected=201,
        json={"ids_afectacion": [target_domain["individual"][1]["id_afectacion"]],
              "hay_conflictos": True},
    ).json()
    tid = tramite["id_tramite_fifonafe"]
    doc = _document(api, "tramite_fifonafe", tid, "SINTETICO 008 ruta administrativa")
    common = {"fecha_evento": "2026-05-01", "id_documento": doc["id_documento"]}
    _event(api, tid, tipos["solicitud_retiro_individual"], 1, **common)
    _event(api, tid, tipos["consulta_conflictos_enviada"], 2, ciclo_consulta=1,
           fecha_oficio="2026-05-02", numero_oficio="SINT-008-CONSULTA")
    _event(api, tid, tipos["respuesta_conflictos_acreditada"], 3,
           ciclo_consulta=1, conflicto_impide_retiro=False, **common)
    api("PATCH", f"/api/fifonafe/{tid}", expected=409, json={"estatus": "completo"})
    _event(api, tid, tipos["resolucion_retiro_autorizada"], 4, **common)
    api("PATCH", f"/api/fifonafe/{tid}", expected=409, json={"estatus": "completo"})
    _event(api, tid, tipos["entrega_recursos"], 5, **common)
    api("PATCH", f"/api/fifonafe/{tid}", expected=409, json={"estatus": "completo"})
    _event(api, tid, tipos["comprobacion_entrega"], 6, **common)
    assert api("PATCH", f"/api/fifonafe/{tid}", json={"estatus": "completo"}).json()["estatus"] == "completo"
    rows = api(
        "GET", f"/api/reportes/avance-periodo?id_proyecto={target_domain['project']['id_proyecto']}"
               "&indicador=informe_no_conflictos&anio=2026&mes=5",
    ).json()
    assert sum(row["realizado"] for row in rows) == 0


def test_fifonafe_asamblea_retiro_compartida_y_cop_rechazada(api, target_domain):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    tipos = _catalog(api, "tipo_asamblea")
    contextos = _catalog(api, "contexto_asamblea")
    resultados = _catalog(api, "resultado_convocatoria")
    cop = api(
        "POST", f"/api/proyecto-nucleo/{pn_id}/asambleas", expected=201,
        json={"id_tipo_asamblea": tipos["anuencia"],
              "id_contexto_asamblea": contextos["cop_original"],
              "convocatorias": [{"ordinal": 1, "fecha_realizacion": "2026-06-01",
                                  "id_resultado": resultados["celebrada"]}]},
    ).json()
    api("POST", f"/api/proyecto-nucleo/{pn_id}/fifonafe", expected=409,
        json={"ids_afectacion": [target_domain["collective"][0]["id_afectacion"]],
              "id_asamblea_retiro": cop["id_asamblea"]})
    retiro = api(
        "POST", f"/api/proyecto-nucleo/{pn_id}/asambleas", expected=201,
        json={"id_tipo_asamblea": tipos["retiro_fondos"],
              "id_contexto_asamblea": contextos["retiro_fondos"],
              "convocatorias": [{"ordinal": 1, "fecha_realizacion": "2026-06-02",
                                  "id_resultado": resultados["celebrada"]}]},
    ).json()
    _document(api, "asamblea", retiro["id_asamblea"], "SINTETICO 008 Asamblea retiro")
    ids = []
    for affectation in target_domain["collective"]:
        row = api(
            "POST", f"/api/proyecto-nucleo/{pn_id}/fifonafe", expected=201,
            json={"ids_afectacion": [affectation["id_afectacion"]],
                  "id_asamblea_retiro": retiro["id_asamblea"]},
        ).json()
        ids.append(row["id_tramite_fifonafe"])
    assert len(set(ids)) == 2


def test_fifonafe_representacion_orv_historica_y_externa(api, target_domain):
    project_id = target_domain["project"]["id_proyecto"]
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    tipos_evento = _catalog(api, "tipo_evento_fifonafe")
    states = _catalog(api, "estado_registral_orv")
    organs = _catalog(api, "organo_orv")
    positions = _catalog(api, "cargo_orv")
    qualities = _catalog(api, "calidad_integrante_orv")
    person = api("POST", f"/api/proyectos/{project_id}/personas", expected=201,
                 json={"nombre": f"SINTETICO-{uuid.uuid4().hex[:8]}",
                       "datos_identidad_incompletos": True, "origen_registro": "qa"}).json()
    existing_orv = api("GET", f"/api/proyecto-nucleo/{pn_id}/orv").json()
    orv = existing_orv[0] if existing_orv else api(
        "POST", f"/api/proyecto-nucleo/{pn_id}/orv", expected=201,
        json={"numero_orv": f"ORV-008-{uuid.uuid4().hex[:8]}",
              "inicio_vigencia": "2026-01-01", "fin_vigencia": "2026-12-31",
              "id_estado_registral": states["inscrita"]},
    ).json()
    member = api("POST", f"/api/orv/{orv['id_orv']}/integrantes", expected=201,
                 json={"id_persona": person["id_persona"], "id_organo": organs["comisariado"],
                       "id_cargo": positions["presidente"], "id_calidad": qualities["propietario"],
                       "fecha_inicio": "2026-01-01", "fecha_fin": "2026-12-31"}).json()
    tramite = api("POST", f"/api/proyecto-nucleo/{pn_id}/fifonafe", expected=201,
                  json={"ids_afectacion": [target_domain["individual"][0]["id_afectacion"]]}).json()
    event = _event(api, tramite["id_tramite_fifonafe"], tipos_evento["diferimiento_retiro"], 1,
                   fecha_evento="2026-07-01")
    api("POST", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes", expected=201,
        json={"id_persona": person["id_persona"], "rol": "representante",
              "id_evento_fifonafe": event["id_evento_fifonafe"],
              "id_orv_integrante": member["id_orv_integrante"]})
    undated = _event(api, tramite["id_tramite_fifonafe"], tipos_evento["diferimiento_retiro"], 2,
                     observaciones="SINTETICO sin fecha verificable")
    api("POST", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes", expected=409,
        json={"id_persona": person["id_persona"], "rol": "representante",
              "id_evento_fifonafe": undated["id_evento_fifonafe"],
              "id_orv_integrante": member["id_orv_integrante"]})
    external = api("POST", f"/api/proyectos/{project_id}/personas", expected=201,
                   json={"nombre": f"EXTERNO-{uuid.uuid4().hex[:8]}",
                         "datos_identidad_incompletos": True, "origen_registro": "qa"}).json()
    intervention = api(
        "POST", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes", expected=201,
        json={"id_persona": external["id_persona"], "rol": "representante",
              "id_evento_fifonafe": event["id_evento_fifonafe"]},
    ).json()
    _document(api, "tramite_fifonafe_interviniente", intervention["id_interviniente_fifonafe"],
              "SINTETICO 008 acreditación representante externo")
