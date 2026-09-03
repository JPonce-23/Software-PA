"""Integration tests for AfectacionUnidadAgraria PATCH, DELETE, and access constraints."""
import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from app.config import AUTH_SETTINGS
from app.main import app


def _login(email: str, password: str) -> tuple[TestClient, dict[str, str]]:
    client = TestClient(app, raise_server_exceptions=False)
    origin = AUTH_SETTINGS.allowed_origins[0]
    response = client.post(
        "/api/auth/sesiones",
        data={"username": email, "password": password},
        headers={"Origin": origin},
    )
    assert response.status_code == 200, response.text
    csrf = client.cookies.get(AUTH_SETTINGS.csrf_cookie_name)
    return client, {"Origin": origin, "X-CSRF-Token": csrf}


@pytest.fixture(scope="module")
def catalogs(api):
    def get_cat(name):
        return {x["codigo"]: x["id_catalogo_opcion"] for x in api("GET", f"/api/catalogos/operativos/{name}").json()}

    return {
        "tipo_tierra": next(iter(get_cat("tipo_tierra").values())),
        "tipo_titularidad": get_cat("tipo_titularidad_unidad")["persona"],
    }


def test_afectacion_unidad_agraria_lifecycle_and_patch(api, target_domain, catalogs):
    pn = target_domain["project_nucleus"]
    pn_id = pn["id_proyecto_nucleo"]
    token = uuid.uuid4().hex[:8]

    # 1. Create parcel, agricultural unit, and affectation
    parcela = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": f"UA-TEST-{token}"},
    ).json()

    unidad = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": catalogs["tipo_tierra"],
            "id_tipo_titularidad": catalogs["tipo_titularidad"],
            "id_parcela": parcela["id_parcela"],
            "referencia_alfanumerica": f"REF-UA-{token}",
        },
    ).json()

    afectacion = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "individual",
            "superficie_preliminar_ha": "1.000000",
            "superficie_afectada_ha": "1.000000",
        },
    ).json()

    af_id = afectacion["id_afectacion"]
    ua_id = unidad["id_unidad_agraria"]

    # 2. Associate UnidadAgraria to Afectacion
    assoc = api(
        "POST",
        f"/api/afectaciones/{af_id}/unidades-agrarias",
        expected=201,
        json={
            "id_unidad_agraria": ua_id,
            "superficie_preliminar_ha": "2.500000",
            "superficie_afectada_ha": "2.000000",
            "superficie_valor_original": "2-00-00",
            "superficie_formato_origen": "ha-a-ca",
            "fuente": "Fuente inicial QA",
            "observaciones": "Obs iniciales",
        },
    ).json()
    assoc_id = assoc["id_afectacion_unidad"]
    assert assoc_id > 0
    assert assoc["id_afectacion"] == af_id
    assert assoc["id_unidad_agraria"] == ua_id

    # 3. Query via GET
    units = api("GET", f"/api/afectaciones/{af_id}/unidades-agrarias").json()
    assert any(u["id_afectacion_unidad"] == assoc_id for u in units)

    # 4. PATCH all editable fields
    updated = api(
        "PATCH",
        f"/api/afectacion-unidades-agrarias/{assoc_id}",
        expected=200,
        json={
            "superficie_preliminar_ha": "3.500000",
            "superficie_afectada_ha": "3.250000",
            "superficie_valor_original": "3-25-00.00",
            "superficie_formato_origen": "ha-a-ca",
            "fuente": "Levantamiento topográfico 2026",
            "observaciones": "Ajuste de superficie verificado",
        },
    ).json()
    assert Decimal(str(updated["superficie_preliminar_ha"])) == Decimal("3.500000")
    assert Decimal(str(updated["superficie_afectada_ha"])) == Decimal("3.250000")
    assert updated["superficie_valor_original"] == "3-25-00.00"
    assert updated["superficie_formato_origen"] == "ha-a-ca"
    assert updated["fuente"] == "Levantamiento topográfico 2026"
    assert updated["observaciones"] == "Ajuste de superficie verificado"

    # 5. Confirm GET returns the updated values
    units_after = api("GET", f"/api/afectaciones/{af_id}/unidades-agrarias").json()
    matched = next(u for u in units_after if u["id_afectacion_unidad"] == assoc_id)
    assert Decimal(str(matched["superficie_preliminar_ha"])) == Decimal("3.500000")
    assert Decimal(str(matched["superficie_afectada_ha"])) == Decimal("3.250000")
    assert matched["fuente"] == "Levantamiento topográfico 2026"

    # 6. Identity fields are rejected by the canonical PATCH contract.
    api(
        "PATCH",
        f"/api/afectacion-unidades-agrarias/{assoc_id}",
        expected=422,
        json={
            "id_afectacion": 99999,
            "id_unidad_agraria": 99999,
            "fuente": "Intento de cambio de identidad",
        },
    )

    # 7. Logical delete
    del_res = api(
        "DELETE",
        f"/api/afectacion-unidades-agrarias/{assoc_id}",
        expected=200,
        json={"motivo": "Baja de prueba QA de unidad afectada"},
    ).json()
    assert "dada de baja" in del_res["detail"]

    # 8. Confirm GET no longer returns the inactive association
    units_after_del = api("GET", f"/api/afectaciones/{af_id}/unidades-agrarias").json()
    assert not any(u["id_afectacion_unidad"] == assoc_id for u in units_after_del)


def test_document_target_lifecycle_with_affectation_unit(api, target_domain, catalogs):
    pn = target_domain["project_nucleus"]
    pn_id = pn["id_proyecto_nucleo"]
    token = uuid.uuid4().hex[:6]

    # Create dedicated unit and affectation
    parcela = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": f"DOC-UA-{token}"},
    ).json()
    unidad = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": catalogs["tipo_tierra"],
            "id_tipo_titularidad": catalogs["tipo_titularidad"],
            "id_parcela": parcela["id_parcela"],
        },
    ).json()
    afectacion = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual"},
    ).json()
    assoc = api(
        "POST",
        f"/api/afectaciones/{afectacion['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={"id_unidad_agraria": unidad["id_unidad_agraria"]},
    ).json()
    assoc_id = assoc["id_afectacion_unidad"]

    # Document upload on active association
    doc = api(
        "POST",
        f"/api/documentos/objetivos/afectacion_unidad_agraria/{assoc_id}",
        expected=201,
        json={"tipo_documento": "soporte_qa", "estado": "disponible", "titulo": f"Soporte {token}"},
    ).json()
    assert doc["id_documento"] > 0

    docs = api("GET", f"/api/documentos/objetivos/afectacion_unidad_agraria/{assoc_id}").json()
    assert any(d["id_documento"] == doc["id_documento"] for d in docs)

    # Perform logical delete
    api(
        "DELETE",
        f"/api/afectacion-unidades-agrarias/{assoc_id}",
        expected=200,
        json={"motivo": "Baja para probar no-autorizacion documental posterior"},
    )

    # After logical delete, document target should no longer be active (404)
    api("GET", f"/api/documentos/objetivos/afectacion_unidad_agraria/{assoc_id}", expected=404)
    api(
        "POST",
        f"/api/documentos/objetivos/afectacion_unidad_agraria/{assoc_id}",
        expected=404,
        json={"tipo_documento": "soporte_qa", "estado": "disponible", "titulo": "Intento tras baja"},
    )


def test_negatives_afectacion_unidad_agraria(api, target_domain, catalogs):
    pn = target_domain["project_nucleus"]
    pn_id = pn["id_proyecto_nucleo"]

    # NEG-01: PATCH non-existent
    api(
        "PATCH",
        "/api/afectacion-unidades-agrarias/99999999",
        expected=404,
        json={"fuente": "No existe"},
    )

    # NEG-02: DELETE non-existent
    api(
        "DELETE",
        "/api/afectacion-unidades-agrarias/99999999",
        expected=404,
        json={"motivo": "No existe"},
    )

    # Create dedicated parcel, unit, and affectation for negative testing
    token = uuid.uuid4().hex[:6]
    parcela = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": f"NEG-P-{token}"},
    ).json()
    unidad = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": catalogs["tipo_tierra"],
            "id_tipo_titularidad": catalogs["tipo_titularidad"],
            "id_parcela": parcela["id_parcela"],
        },
    ).json()
    afectacion = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual"},
    ).json()
    assoc = api(
        "POST",
        f"/api/afectaciones/{afectacion['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={"id_unidad_agraria": unidad["id_unidad_agraria"]},
    ).json()
    assoc_id = assoc["id_afectacion_unidad"]

    # NEG-03: RBAC 403 (unassigned user)
    password = f"Qa1!{uuid.uuid4().hex}Z"
    email = f"sin-acceso-{uuid.uuid4().hex[:8]}@qa.local"
    api(
        "POST",
        "/api/usuarios",
        expected=201,
        json={"nombre": "Sin", "apellido_paterno": "Acceso", "correo": email, "rol": "operador", "contrasena": password},
    )
    outsider, headers = _login(email, password)
    patch_res = outsider.patch(
        f"/api/afectacion-unidades-agrarias/{assoc_id}",
        headers=headers,
        json={"fuente": "Intento no autorizado"},
    )
    assert patch_res.status_code == 403

    del_res = outsider.request(
        "DELETE",
        f"/api/afectacion-unidades-agrarias/{assoc_id}",
        headers=headers,
        json={"motivo": "Intento no autorizado"},
    )
    assert del_res.status_code == 403

    # NEG-04: Cross-nucleus association rejected (409)
    # Create another nucleus in the same state
    state = api("GET", "/api/catalogos/entidades").json()[0]
    municipality = api("GET", f"/api/catalogos/municipios?id_entidad={state['id_entidad']}").json()[0]
    other_nucleus = api(
        "POST",
        "/api/nucleos",
        expected=201,
        json={
            "id_municipio": municipality["id_municipio"],
            "nombre_nucleo": f"OTRO NUCLEO {uuid.uuid4().hex[:8]}",
            "id_tipo_tenencia": {
                x["codigo"]: x["id_catalogo_opcion"]
                for x in api("GET", "/api/catalogos/operativos/tipo_tenencia").json()
            }["ejido"],
        },
    ).json()
    other_unit = api(
        "POST",
        f"/api/nucleos/{other_nucleus['id_nucleo']}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": catalogs["tipo_tierra"],
            "id_tipo_titularidad": catalogs["tipo_titularidad"],
            "referencia_alfanumerica": f"REF-OTHER-{uuid.uuid4().hex[:6]}",
        },
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{afectacion['id_afectacion']}/unidades-agrarias",
        expected=409,
        json={"id_unidad_agraria": other_unit["id_unidad_agraria"]},
    )

    # NEG-05: Negative surface rejected (422)
    api(
        "PATCH",
        f"/api/afectacion-unidades-agrarias/{assoc_id}",
        expected=422,
        json={"superficie_afectada_ha": -1.5},
    )

    # NEG-06: Delete without reason rejected (422 by Pydantic min_length=3)
    api(
        "DELETE",
        f"/api/afectacion-unidades-agrarias/{assoc_id}",
        expected=422,
        json={"motivo": ""},
    )

    # Successfully delete
    api(
        "DELETE",
        f"/api/afectacion-unidades-agrarias/{assoc_id}",
        expected=200,
        json={"motivo": "Baja normal para probar segunda baja"},
    )

    # NEG-07: Second delete of already inactive association returns 404
    api(
        "DELETE",
        f"/api/afectacion-unidades-agrarias/{assoc_id}",
        expected=404,
        json={"motivo": "Intento de segunda baja"},
    )
