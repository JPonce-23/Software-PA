import uuid


def test_document_version_is_immutable_and_downloadable(
    client, admin_headers, api, target_domain
):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    document = api(
        "POST",
        f"/api/documentos/objetivos/proyecto_nucleo/{pn_id}",
        expected=201,
        json={
            "tipo_documento": "acta_qa",
            "estado": "disponible",
            "titulo": "Soporte de prueba",
        },
    ).json()
    content = b"%PDF-1.4\nSOFTWARE-PA QA\n%%EOF\n"
    first = client.post(
        f"/api/documentos/{document['id_documento']}/versiones",
        headers=admin_headers,
        files={"archivo": ("soporte-qa.pdf", content, "application/pdf")},
    )
    assert first.status_code == 201, first.text
    version = first.json()
    assert len(version["hash_sha256"]) == 64
    duplicate = client.post(
        f"/api/documentos/{document['id_documento']}/versiones",
        headers=admin_headers,
        files={"archivo": ("soporte-qa.pdf", content, "application/pdf")},
    )
    assert duplicate.status_code == 409
    downloaded = client.get(
        f"/api/documentos/versiones/{version['id_documento_version']}/descarga"
    )
    assert downloaded.status_code == 200
    assert downloaded.content == content


def test_dashboard_does_not_multiply_many_to_many(api, target_domain):
    municipality = target_domain["municipality"]
    tenancy = {
        row["codigo"]: row["id_catalogo_opcion"]
        for row in api("GET", "/api/catalogos/operativos/tipo_tenencia").json()
    }
    project = api(
        "POST",
        "/api/proyectos",
        expected=201,
        json={
            "clave_proyecto": f"KPI-{uuid.uuid4().hex[:8]}",
            "nombre_proyecto": "Proyecto KPI N:M QA",
        },
    ).json()
    nucleus = api(
        "POST",
        "/api/nucleos",
        expected=201,
        json={
            "id_municipio": municipality["id_municipio"],
            "nombre_nucleo": f"EJIDO KPI {uuid.uuid4().hex[:8]}",
            "id_tipo_tenencia": tenancy["ejido"],
        },
    ).json()
    pn = api(
        "POST",
        f"/api/proyectos/{project['id_proyecto']}/nucleos",
        expected=201,
        json={"id_nucleo": nucleus["id_nucleo"]},
    ).json()
    affects = []
    for number, surface in enumerate(("1.000000", "2.000000"), start=1):
        affects.append(
            api(
                "POST",
                f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/afectaciones",
                expected=201,
                json={
                    "tipo_afectacion": "colectivo",
                    "superficie_preliminar_ha": surface,
                    "superficie_afectada_ha": surface,
                },
            ).json()
        )
    agreement = api(
        "POST",
        f"/api/afectaciones/{affects[0]['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_convenio": "cop_original",
            "fecha_firma": "2026-07-01",
            "superficie_ha": "3.000000",
        },
    ).json()
    api(
        "POST",
        f"/api/convenios/{agreement['id_convenio']}/afectaciones",
        expected=201,
        json={"id_afectacion": affects[1]["id_afectacion"]},
    )
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/fifonafe",
        expected=201,
        json={
            "ids_afectacion": [item["id_afectacion"] for item in affects],
            "estatus": "pendiente",
        },
    )
    rows = api(
        "GET", f"/api/dashboard/kpi?id_proyecto={project['id_proyecto']}"
    ).json()
    by_indicator = {row["indicador"]: row for row in rows}
    assert by_indicator["nucleos"]["cantidad"] == 1
    assert by_indicator["cop_colectivos"]["cantidad"] == 1
    assert by_indicator["fifonafe"]["cantidad"] == 1
    assert by_indicator["superficie_afectada_administrativa"]["superficie_ha"] == "3.000000"


def test_project_map_is_visual_support(api, target_domain):
    project_id = target_domain["project"]["id_proyecto"]
    traces = api("GET", f"/api/proyectos/{project_id}/trazos").json()
    if not traces:
        api(
            "POST",
            f"/api/proyectos/{project_id}/trazos",
            expected=201,
            json={
                "version": 1,
                "geometria_wkt": "MULTILINESTRING((-100 20,-99.8 20.2))",
                "fuente": "Trazo sintético QA",
                "fecha_vigencia_inicio": "2026-01-01",
            },
        )
    map_data = api("GET", f"/api/proyectos/{project_id}/mapa").json()
    assert map_data["type"] == "FeatureCollection"
    assert any(
        item["properties"]["tipo"] == "trazo_proyecto"
        for item in map_data["features"]
    )
    parcel = target_domain["parcels"][0]
    assert api("GET", f"/api/parcelas/{parcel['id_parcela']}").json()[
        "geometria_wkt"
    ] is None
