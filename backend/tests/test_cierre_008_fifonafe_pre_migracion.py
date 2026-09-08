"""Regresiones FIFONAFE compatibles con el esquema 007.

Los escenarios de este archivo son sintéticos y no representan hechos de los
expedientes Excel auditados.
"""


def _catalog(api, name: str) -> dict[str, int]:
    return {
        row["codigo"]: row["id_catalogo_opcion"]
        for row in api("GET", f"/api/catalogos/operativos/{name}").json()
    }


def test_fifonafe_asociacion_y_eventos_rechazan_campos_ajenos_atomicamente(
    api, target_domain
):
    pn = target_domain["project_nucleus"]
    colectivo = target_domain["collective"]
    tipos = _catalog(api, "tipo_evento_fifonafe")

    tramite = api(
        "POST",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/fifonafe",
        expected=201,
        json={"ids_afectacion": [colectivo[0]["id_afectacion"]]},
    ).json()

    api(
        "POST",
        f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/afectaciones",
        expected=422,
        json={
            "id_afectacion": colectivo[1]["id_afectacion"],
            "efecto_superficie": "adicion",
            "superficie_impacto_ha": "1.0000000",
        },
    )
    vigente = api(
        "GET",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/fifonafe",
    ).json()
    actual = next(
        item
        for item in vigente
        if item["id_tramite_fifonafe"] == tramite["id_tramite_fifonafe"]
    )
    assert [a["id_afectacion"] for a in actual["afectaciones"]] == [
        colectivo[0]["id_afectacion"]
    ]

    evento = api(
        "POST",
        f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/eventos",
        expected=201,
        json={
            "ordinal": 1,
            "id_tipo_evento": tipos["oficio_fifonafe_dgaopr"],
            "numero_oficio": "SINTETICO-PRE-008-1",
            "fecha_oficio": "2026-09-07",
        },
    ).json()
    actualizado = api(
        "PATCH",
        f"/api/eventos-fifonafe/{evento['id_evento_fifonafe']}",
        json={"numero_oficio": "SINTETICO-PRE-008-CORREGIDO"},
    ).json()
    assert actualizado["numero_oficio"] == "SINTETICO-PRE-008-CORREGIDO"

    api(
        "PATCH",
        f"/api/eventos-fifonafe/{evento['id_evento_fifonafe']}",
        expected=422,
        json={"numero_oficio": "NO-DEBE-PERSISTIR", "ordinal": 2},
    )
    eventos = api(
        "GET", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/eventos"
    ).json()
    assert eventos[0]["ordinal"] == 1
    assert eventos[0]["numero_oficio"] == "SINTETICO-PRE-008-CORREGIDO"

    api(
        "DELETE",
        f"/api/eventos-fifonafe/{evento['id_evento_fifonafe']}",
        json={"motivo": "Escenario sintético: baja lógica pre-008"},
    )
    assert api(
        "GET", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/eventos"
    ).json() == []
