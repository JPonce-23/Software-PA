"""Regresiones acotadas post-release para contratos schema 008."""

import uuid


def _catalog(api, name: str) -> dict[str, int]:
    return {
        row["codigo"]: row["id_catalogo_opcion"]
        for row in api("GET", f"/api/catalogos/operativos/{name}").json()
    }


def _new_project_nucleus(api, target_domain):
    tenencia = _catalog(api, "tipo_tenencia")
    residencia = _catalog(api, "residencia")
    project = api(
        "POST",
        "/api/proyectos",
        expected=201,
        json={
            "clave_proyecto": f"QA-POSTREL-{uuid.uuid4().hex[:8]}",
            "nombre_proyecto": "QA post release schema 008",
            "fecha_inicio": "2026-09-08",
        },
    ).json()
    nucleus = api(
        "POST",
        "/api/nucleos",
        expected=201,
        json={
            "id_municipio": target_domain["municipality"]["id_municipio"],
            "nombre_nucleo": f"QA POST RELEASE {uuid.uuid4().hex[:8]}",
            "id_tipo_tenencia": tenencia["ejido"],
            "fuente_datos": "qa-post-release",
        },
    ).json()
    return project, nucleus, residencia


def test_project_nucleus_create_get_patch_get_persiste_tuc(api, target_domain):
    project, nucleus, residencia = _new_project_nucleus(api, target_domain)
    motivo = _catalog(api, "motivo_no_afecta_tuc")["no_afectacion_colectiva"]

    created = api(
        "POST",
        f"/api/proyectos/{project['id_proyecto']}/nucleos",
        expected=201,
        json={
            "id_nucleo": nucleus["id_nucleo"],
            "id_residencia": residencia["queretaro"],
            "total_cops_planeados": 2,
            "afecta_tuc": False,
            "id_motivo_no_afecta_tuc": motivo,
            "motivo_no_afecta_tuc_detalle": "Escenario sintético post-release",
            "tuc_revision_pendiente": True,
            "tuc_revision_detalle": "Pendiente de conciliación sintética",
        },
    ).json()

    fetched = api(
        "GET", f"/api/proyecto-nucleo/{created['id_proyecto_nucleo']}"
    ).json()
    assert fetched["afecta_tuc"] is False
    assert fetched["id_motivo_no_afecta_tuc"] == motivo
    assert fetched["motivo_no_afecta_tuc_detalle"] == "Escenario sintético post-release"
    assert fetched["tuc_revision_pendiente"] is True
    assert fetched["tuc_revision_detalle"] == "Pendiente de conciliación sintética"

    rejected = api(
        "PATCH",
        f"/api/proyecto-nucleo/{created['id_proyecto_nucleo']}",
        expected=422,
        json={"total_cops_planeados": 9, "referencias": []},
    )
    assert "referencias" in rejected.text
    unchanged = api(
        "GET", f"/api/proyecto-nucleo/{created['id_proyecto_nucleo']}"
    ).json()
    assert unchanged["total_cops_planeados"] == 2

    updated = api(
        "PATCH",
        f"/api/proyecto-nucleo/{created['id_proyecto_nucleo']}",
        expected=200,
        json={
            "afecta_tuc": True,
            "id_motivo_no_afecta_tuc": None,
            "motivo_no_afecta_tuc_detalle": None,
            "tuc_revision_pendiente": False,
            "tuc_revision_detalle": None,
        },
    ).json()
    assert updated["afecta_tuc"] is True
    assert updated["id_motivo_no_afecta_tuc"] is None
    assert updated["motivo_no_afecta_tuc_detalle"] is None
    assert updated["tuc_revision_pendiente"] is False
    assert updated["tuc_revision_detalle"] is None


def test_asamblea_patch_rechaza_convocatorias_y_endpoints_hijos_funcionan(
    api, target_domain
):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    tipos = _catalog(api, "tipo_asamblea")
    contextos = _catalog(api, "contexto_asamblea")
    resultados = _catalog(api, "resultado_convocatoria")

    asamblea = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": tipos["anuencia"],
            "id_contexto_asamblea": contextos["cop_original"],
            "proposito": "Asamblea sintética original",
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2026-09-08",
                    "fecha_realizacion": "2026-09-08",
                    "id_resultado": resultados["celebrada"],
                }
            ],
        },
    ).json()
    assert len(asamblea["convocatorias"]) == 1

    rejected = api(
        "PATCH",
        f"/api/asambleas/{asamblea['id_asamblea']}",
        expected=422,
        json={
            "proposito": "Mutación parcial no permitida",
            "convocatorias": [{"ordinal": 2, "fecha_programada": "2026-09-09"}],
        },
    )
    assert "convocatorias" in rejected.text
    current = next(
        row
        for row in api(
            "GET", f"/api/proyecto-nucleo/{pn_id}/asambleas", expected=200
        ).json()
        if row["id_asamblea"] == asamblea["id_asamblea"]
    )
    assert current["proposito"] == "Asamblea sintética original"
    assert len(current["convocatorias"]) == 1

    updated = api(
        "PATCH",
        f"/api/asambleas/{asamblea['id_asamblea']}",
        expected=200,
        json={"proposito": "Asamblea sintética actualizada"},
    ).json()
    assert updated["proposito"] == "Asamblea sintética actualizada"

    child = api(
        "POST",
        f"/api/asambleas/{asamblea['id_asamblea']}/convocatorias",
        expected=201,
        json={"ordinal": 2, "fecha_programada": "2026-09-09"},
    ).json()
    patched_child = api(
        "PATCH",
        f"/api/convocatorias/{child['id_convocatoria']}",
        expected=200,
        json={"observaciones_resultado": "Convocatoria hija actualizada"},
    ).json()
    assert patched_child["ordinal"] == 2
    assert patched_child["observaciones_resultado"] == "Convocatoria hija actualizada"
