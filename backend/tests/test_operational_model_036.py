"""API contract for the normalized collective operational model."""

import uuid


def _catalog(api, catalog_type: str) -> dict[str, dict]:
    rows = api("GET", f"/api/catalogos/operativos/{catalog_type}").json()
    return {row["codigo"]: row for row in rows}


def test_catalogs_are_administered_without_migration(api):
    code = f"qa_{uuid.uuid4().hex[:10]}"
    created = api(
        "POST", "/api/catalogos/operativos", expected=201,
        json={
            "tipo_catalogo": "destino_superficie",
            "codigo": code,
            "nombre": "Destino sintético QA",
            "fuente": "pytest",
        },
    ).json()
    updated = api(
        "PATCH",
        f"/api/catalogos/operativos/opciones/{created['id_catalogo_opcion']}",
        json={"nombre": "Destino QA editado"},
    ).json()
    assert updated["nombre"] == "Destino QA editado"
    inactive = api(
        "PATCH",
        f"/api/catalogos/operativos/opciones/{created['id_catalogo_opcion']}",
        json={"activo": False, "motivo_baja": "Prueba de histórico"},
    ).json()
    assert inactive["activo"] is False
    history = api(
        "GET", "/api/catalogos/operativos/destino_superficie?incluir_inactivos=true"
    ).json()
    assert any(item["codigo"] == code and not item["activo"] for item in history)


def test_collective_parcel_asset_and_individual_holder_coexist(api, target_domain):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    parcel_id = target_domain["parcels"][0]["id_parcela"]
    management = _catalog(api, "tipo_gestion")
    destinations = _catalog(api, "destino_superficie")
    cop_types = _catalog(api, "tipo_cop_operativo")
    affectation = api(
        "POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201,
        json={"tipo_afectacion": "colectivo", "id_parcela": parcel_id},
    ).json()
    asset = api(
        "POST", f"/api/afectaciones/{affectation['id_afectacion']}/bienes",
        expected=201,
        json={
            "id_tipo_gestion": management["PARCELA"]["id_catalogo_opcion"],
            "id_destino_superficie": destinations["parcela_escolar"]["id_catalogo_opcion"],
            "id_tipo_cop_operativo": cop_types["ORIGEN"]["id_catalogo_opcion"],
            "id_parcela": parcel_id,
            "referencia_alfanumerica": "P-60",
            "superficie_valor_original": "00-20-16.941",
            "superficie_formato_origen": "H-M2-CM2",
            "superficie_afectada_ha": "0.201694",
        },
    ).json()
    assert asset["referencia_alfanumerica"] == "P-60"
    assert affectation["tipo_afectacion"] == "colectivo"
    assert target_domain["individual"][0]["id_parcela"] == parcel_id


def test_assembly_three_convocations_and_full_ran_history(api, target_domain):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    assembly_types = _catalog(api, "tipo_asamblea")
    contexts = _catalog(api, "contexto_asamblea")
    results = _catalog(api, "resultado_convocatoria")
    ran_types = _catalog(api, "tipo_evento_ran")
    assembly = api(
        "POST", f"/api/proyecto-nucleo/{pn_id}/asambleas", expected=201,
        json={
            "id_tipo_asamblea": assembly_types["anuencia"]["id_catalogo_opcion"],
            "id_contexto_asamblea": contexts["cop_original"]["id_catalogo_opcion"],
            "convocatorias": [
                {"ordinal": 1, "fecha_programada": "2026-07-01", "id_resultado": results["no_verificativo"]["id_catalogo_opcion"]},
                {"ordinal": 2, "fecha_programada": "2026-07-15", "id_resultado": results["reprogramada"]["id_catalogo_opcion"]},
                {"ordinal": 3, "fecha_programada": "2026-07-30", "fecha_realizacion": "2026-07-30", "id_resultado": results["celebrada"]["id_catalogo_opcion"]},
            ],
        },
    ).json()
    assert len(assembly["convocatorias"]) == 3
    events = [
        ("ingreso", "2026-08-01", "A-1", None),
        ("prevencion", "2026-08-03", "A-1", None),
        ("subsanacion", "2026-08-05", "A-1", None),
        ("reingreso", "2026-08-06", "A-2", None),
        ("inscripcion", "2026-08-20", "A-2", None),
    ]
    procedure = api(
        "POST", "/api/tramites-ran", expected=201,
        json={
            "id_asamblea": assembly["id_asamblea"],
            "eventos": [
                {
                    "ordinal": ordinal,
                    "id_tipo_evento": ran_types[event_type]["id_catalogo_opcion"],
                    "fecha_evento": event_date,
                    "numero_solicitud": request,
                    "calificacion": qualification,
                }
                for ordinal, (event_type, event_date, request, qualification)
                in enumerate(events, 1)
            ],
        },
    ).json()
    assert [item["ordinal"] for item in procedure["eventos"]] == [1, 2, 3, 4, 5]
    listed = api("GET", f"/api/proyecto-nucleo/{pn_id}/tramites-ran").json()
    saved = next(item for item in listed if item["id_tramite_ran"] == procedure["id_tramite_ran"])
    assert len(saved["eventos"]) == 5
    assert saved["eventos"][0]["numero_solicitud"] == "A-1"
    assert saved["eventos"][3]["numero_solicitud"] == "A-2"


def test_structured_document_checklist(api, target_domain):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    requirements = api("GET", "/api/catalogos/requisitos-documentales").json()
    states = _catalog(api, "estado_requisito_documental")
    requirement = next(item for item in requirements if item["codigo"] == "acta_no_verificativo")
    item = api(
        "POST", f"/api/proyecto-nucleo/{pn_id}/requisitos-documentales", expected=201,
        json={
            "id_requisito": requirement["id_requisito"],
            "id_estado": states["faltante"]["id_catalogo_opcion"],
            "detalle": "Evidencia sintética pendiente",
        },
    ).json()
    assert item["detalle"] == "Evidencia sintética pendiente"
