import uuid


def test_territorial_fixture_contract(api):
    states = api("GET", "/api/catalogos/entidades").json()
    municipalities = api("GET", "/api/catalogos/municipios").json()
    assert len(states) == 32
    assert len(municipalities) == 2478
    assert len({item["clave_inegi"] for item in states}) == 32
    assert len({item["clave_inegi"] for item in municipalities}) == 2478


def test_project_nucleus_unique_and_multiple_references(api, target_domain):
    project = target_domain["project"]
    nucleus = target_domain["nucleus"]
    duplicate = api(
        "POST",
        f"/api/proyectos/{project['id_proyecto']}/nucleos",
        expected=409,
        json={"id_nucleo": nucleus["id_nucleo"]},
    )
    assert "ProyectoNucleo" in duplicate.json()["detail"]
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    added = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/referencias",
        expected=201,
        json={
            "tipo_referencia": "consecutivo",
            "valor": f"CONS-ADICIONAL-{uuid.uuid4().hex[:8]}",
            "es_principal": True,
        },
    ).json()
    references = api(
        "GET", f"/api/proyecto-nucleo/{pn_id}/referencias"
    ).json()
    assert len(references) >= 3
    assert sum(
        item["es_principal"]
        for item in references
        if item["tipo_referencia"] == "consecutivo"
    ) == 1
    assert added["es_principal"] is True


def test_orv_register_holders_and_geometry_optional(api, target_domain):
    project_id = target_domain["project"]["id_proyecto"]
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    person = api(
        "POST",
        f"/api/proyectos/{project_id}/personas",
        expected=201,
        json={
            "nombre": "Persona",
            "apellido_paterno": f"QA-{uuid.uuid4().hex[:8]}",
            "datos_identidad_incompletos": True,
            "origen_registro": "qa",
        },
    ).json()
    orv = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/orv",
        expected=201,
        json={
            "numero_orv": f"ORV-{uuid.uuid4().hex[:8]}",
            "inicio_vigencia": "2026-01-01",
            "fin_vigencia": "2028-12-31",
            "acta_eleccion_inscrita_ran": True,
        },
    ).json()
    member = api(
        "POST",
        f"/api/orv/{orv['id_orv']}/integrantes",
        expected=201,
        json={"id_persona": person["id_persona"], "cargo": "Presidencia"},
    ).json()
    assert member["id_persona"] == person["id_persona"]
    register = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/padrones",
        expected=201,
        json={
            "fecha_padron": "2026-01-15",
            "numero_ejidatarios_comuneros": 42,
        },
    ).json()
    assert register["numero_ejidatarios_comuneros"] == 42
    parcel = target_domain["parcels"][0]
    detail = api("GET", f"/api/parcelas/{parcel['id_parcela']}").json()
    assert detail["geometria_wkt"] is None
    holder = api(
        "POST",
        f"/api/parcelas/{parcel['id_parcela']}/titulares",
        expected=201,
        json={
            "id_persona": person["id_persona"],
            "tipo_derecho": "titular",
            "porcentaje_participacion": "100",
        },
    ).json()
    assert holder["id_persona"] == person["id_persona"]


def test_affectation_scope_rules(api, target_domain):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    parcel_id = target_domain["parcels"][0]["id_parcela"]
    collective_with_parcel = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=422,
        json={"tipo_afectacion": "colectivo", "id_parcela": parcel_id},
    )
    assert collective_with_parcel.status_code == 422
    individual_without_parcel = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=422,
        json={"tipo_afectacion": "individual"},
    )
    assert individual_without_parcel.status_code == 422

    municipality_id = target_domain["municipality"]["id_municipio"]
    other_nucleus = api(
        "POST",
        "/api/nucleos",
        expected=201,
        json={
            "id_municipio": municipality_id,
            "nombre_nucleo": f"OTRO EJIDO QA {uuid.uuid4().hex[:8]}",
            "tipo_nucleo": "ejido",
        },
    ).json()
    other_pn = api(
        "POST",
        f"/api/proyectos/{target_domain['project']['id_proyecto']}/nucleos",
        expected=201,
        json={"id_nucleo": other_nucleus["id_nucleo"]},
    ).json()
    other_parcel = api(
        "POST",
        f"/api/proyecto-nucleo/{other_pn['id_proyecto_nucleo']}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": "CRUZADA-QA"},
    ).json()
    crossed = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=409,
        json={
            "tipo_afectacion": "individual",
            "id_parcela": other_parcel["id_parcela"],
        },
    )
    assert "parcela" in crossed.json()["detail"].lower()


def test_shared_assembly_agreement_many_to_many_and_permuta(api, target_domain):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    assembly = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "tipo_asamblea": "anuencia",
            "fecha_realizada": "2026-05-10",
            "fecha_ingreso_ran": "2026-05-12",
            "numero_solicitud_ran": f"RAN-ACTA-{uuid.uuid4().hex[:8]}",
            "fecha_inscripcion_ran": "2026-06-01",
        },
    ).json()
    first, second = target_domain["collective"]
    agreement = api(
        "POST",
        f"/api/afectaciones/{first['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_convenio": "cop_original",
            "id_asamblea_autorizacion": assembly["id_asamblea"],
            "fecha_firma": "2026-06-02",
            "superficie_ha": "4.150000",
        },
    ).json()
    additional = api(
        "POST",
        f"/api/convenios/{agreement['id_convenio']}/afectaciones",
        expected=201,
        json={"id_afectacion": second["id_afectacion"]},
    ).json()
    assert additional["rol"] == "adicional"
    second_agreement = api(
        "POST",
        f"/api/afectaciones/{second['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_convenio": "modificatorio",
            "id_asamblea_autorizacion": assembly["id_asamblea"],
        },
    ).json()
    assert second_agreement["id_asamblea_autorizacion"] == assembly["id_asamblea"]

    individual = target_domain["individual"][0]
    permuta = api(
        "POST",
        f"/api/afectaciones/{individual['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_convenio": "cop_original",
            "modalidad_especial": "permuta",
            "descripcion_modalidad": "Caso sintético QA",
        },
    ).json()
    assert permuta["modalidad_especial"] == "permuta"
    api(
        "POST",
        f"/api/afectaciones/{individual['id_afectacion']}/convenios",
        expected=422,
        json={
            "tipo_convenio": "ampliacion",
            "modalidad_especial": "permuta",
        },
    )


def test_shared_fifonafe_indemnity_and_multiple_payments(api, target_domain):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    individuals = target_domain["individual"]
    procedure = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/fifonafe",
        expected=201,
        json={
            "ids_afectacion": [item["id_afectacion"] for item in individuals],
            "estatus": "completo",
            "no_oficio_fifonafe_a_dgaopr": "QA-OF-1",
            "fecha_oficio_fifonafe_a_dgaopr": "2026-01-01",
            "no_oficio_dgaopr_a_representacion": "QA-OF-2",
            "fecha_oficio_dgaopr_a_representacion": "2026-01-02",
            "no_oficio_respuesta_representacion_a_dgaopr": "QA-OF-3",
            "fecha_oficio_respuesta_representacion_a_dgaopr": "2026-01-03",
            "no_oficio_respuesta_dgaopr_a_fifonafe": "QA-OF-4",
            "fecha_oficio_respuesta_dgaopr_a_fifonafe": "2026-01-04",
            "hay_conflictos": False,
            "resultado_no_conflictos": "Sin conflictos QA",
        },
    ).json()
    assert len(procedure["afectaciones"]) == 2
    cross = api(
        "POST",
        f"/api/fifonafe/{procedure['id_tramite_fifonafe']}/afectaciones",
        expected=409,
        json={"id_afectacion": target_domain["collective"][0]["id_afectacion"]},
    )
    assert "ámbito" in cross.json()["detail"]

    affectation_id = individuals[0]["id_afectacion"]
    indemnity = api(
        "POST",
        f"/api/afectaciones/{affectation_id}/indemnizacion",
        expected=201,
        json={
            "estatus": "completo",
            "fecha_programada": "2026-02-01",
            "fecha_resolucion": "2026-02-05",
        },
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{affectation_id}/indemnizacion",
        expected=409,
        json={"estatus": "pendiente"},
    )
    for number, amount in enumerate(("1000.00", "250.50"), start=1):
        api(
            "POST",
            f"/api/indemnizaciones/{indemnity['id_indemnizacion']}/pagos",
            expected=201,
            json={
                "fecha_pago": f"2026-02-0{5 + number}",
                "monto": amount,
                "beneficiario_nombre": "Titular QA",
                "referencia": f"PAGO-QA-{uuid.uuid4().hex[:8]}",
                "medio_pago": "transferencia",
            },
        )
    payments = api(
        "GET", f"/api/indemnizaciones/{indemnity['id_indemnizacion']}/pagos"
    ).json()
    assert len(payments) == 2


def test_logical_deletion(api, target_domain):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    affectation = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "destino_superficie": "solar_qa"},
    ).json()
    api(
        "DELETE",
        f"/api/afectaciones/{affectation['id_afectacion']}",
        json={"motivo": "Baja lógica de prueba"},
    )
    api(
        "GET",
        f"/api/afectaciones/{affectation['id_afectacion']}",
        expected=404,
    )
