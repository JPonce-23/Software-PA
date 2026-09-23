"""Regresión aislada del contrato PATCH de Convenio previo a la migración 007."""

import pytest

from .test_excel_closure_002 import _catalog, _isolated_pn


@pytest.fixture(scope="module")
def api(transactional_api):
    return transactional_api["request"]


@pytest.fixture(scope="module")
def target_domain(transactional_target_domain):
    return transactional_target_domain


def test_patch_convenio_rechaza_comparecientes_y_endpoints_hijos_funcionan(
    api, target_domain
):
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    project_id = project["id_proyecto"]
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    titularidad = _catalog(api, "tipo_titularidad_unidad")["persona"]
    calidad = _catalog(api, "calidad_compareciente_convenio")["titular_parcelario"]
    acreditacion = _catalog(api, "tipo_acreditacion_derecho_individual")[
        "certificado_parcelario"
    ]

    persona = api(
        "POST",
        f"/api/proyectos/{project_id}/personas",
        expected=201,
        json={"nombre": "Sonda", "apellido_paterno": "PATCH", "origen_registro": "qa"},
    ).json()
    parcela = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": "QA-PATCH-007"},
    ).json()
    titular = api(
        "POST",
        f"/api/parcelas/{parcela['id_parcela']}/titulares",
        expected=201,
        json={"id_persona": persona["id_persona"], "tipo_derecho": "parcelario"},
    ).json()
    unidad = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": tierra,
            "id_tipo_titularidad": titularidad,
            "id_parcela": parcela["id_parcela"],
            "referencia_alfanumerica": "UA-QA-PATCH-007",
        },
    ).json()
    afectacion = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual"},
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{afectacion['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={"id_unidad_agraria": unidad["id_unidad_agraria"]},
    )
    convenio = api(
        "POST",
        f"/api/afectaciones/{afectacion['id_afectacion']}/convenios",
        expected=201,
        json={"tipo_instrumento": "convenio", "tipo_convenio": "cop_original"},
    ).json()

    # El tipo juridico legado tampoco puede reintroducirse mediante PATCH.
    api(
        "PATCH",
        f"/api/convenios/{convenio['id_convenio']}",
        expected=422,
        json={"tipo_convenio": "superficie_adicional"},
    )
    assert api("GET", f"/api/convenios/{convenio['id_convenio']}").json()[
        "tipo_convenio"
    ] == "cop_original"

    compareciente_payload = {
        "id_persona": persona["id_persona"],
        "id_parcela_titular": titular["id_parcela_titular"],
        "id_tipo_calidad": calidad,
        "id_tipo_acreditacion": acreditacion,
        "referencia_acreditacion": "CERT-QA-PATCH-007",
        "nombre_en_instrumento": "Sonda PATCH",
        "es_firmante": True,
    }

    # La colección no forma parte de PATCH y tampoco se aplica el campo escalar vecino.
    api(
        "PATCH",
        f"/api/convenios/{convenio['id_convenio']}",
        expected=422,
        json={
            "descripcion_instrumento": "NO DEBE PERSISTIR",
            "comparecientes": [compareciente_payload],
        },
    )
    sin_cambio = api("GET", f"/api/convenios/{convenio['id_convenio']}").json()
    assert sin_cambio["descripcion_instrumento"] is None
    assert sin_cambio["comparecientes"] == []

    # Alta, modificación y baja siguen pasando por los endpoints hijos dedicados.
    compareciente = api(
        "POST",
        f"/api/convenios/{convenio['id_convenio']}/comparecientes",
        expected=201,
        json=compareciente_payload,
    ).json()
    actualizado = api(
        "PATCH",
        f"/api/convenio-comparecientes/{compareciente['id_compareciente']}",
        json={"nombre_en_instrumento": "Sonda PATCH actualizada"},
    ).json()
    assert actualizado["nombre_en_instrumento"] == "Sonda PATCH actualizada"
    assert len(
        api("GET", f"/api/convenios/{convenio['id_convenio']}/comparecientes").json()
    ) == 1
    api(
        "DELETE",
        f"/api/convenio-comparecientes/{compareciente['id_compareciente']}",
        json={"motivo": "Cierre de regresión aislada"},
    )
    assert (
        api("GET", f"/api/convenios/{convenio['id_convenio']}/comparecientes").json()
        == []
    )
