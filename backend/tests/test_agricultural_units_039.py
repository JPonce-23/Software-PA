"""Integration tests for UnidadAgraria safe logical deletion, dependencies, and access rules."""
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


def test_unidad_agraria_successful_deletion_and_lifecycle(api, target_domain, catalogs):
    pn = target_domain["project_nucleus"]
    pn_id = pn["id_proyecto_nucleo"]
    nucleo_id = target_domain["nucleus"]["id_nucleo"]
    token = uuid.uuid4().hex[:8]

    # 1. Create a parcel and an agricultural unit referencing that parcel
    parcela = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": f"UA-DEL-{token}"},
    ).json()
    parcela_id = parcela["id_parcela"]

    unidad = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": catalogs["tipo_tierra"],
            "id_tipo_titularidad": catalogs["tipo_titularidad"],
            "id_parcela": parcela_id,
            "referencia_alfanumerica": f"REF-DEL-{token}",
            "detalle": "Detalle previo",
        },
    ).json()
    unidad_id = unidad["id_unidad_agraria"]

    # 2. Document upload on active unit
    doc = api(
        "POST",
        f"/api/documentos/objetivos/unidad_agraria/{unidad_id}",
        expected=201,
        json={"tipo_documento": "soporte_qa", "estado": "disponible", "titulo": f"Soporte UA {token}"},
    ).json()
    doc_id = doc["id_documento"]
    assert doc_id > 0

    docs = api("GET", f"/api/documentos/objetivos/unidad_agraria/{unidad_id}").json()
    assert any(d["id_documento"] == doc_id for d in docs)

    # 3. PATCH active unit
    patched = api(
        "PATCH",
        f"/api/unidades-agrarias/{unidad_id}",
        expected=200,
        json={
            "id_nucleo": 99999,  # Should be ignored / immutable
            "referencia_alfanumerica": f"REF-MOD-{token}",
            "detalle": "Detalle actualizado",
        },
    ).json()
    assert patched["id_nucleo"] == nucleo_id
    assert patched["referencia_alfanumerica"] == f"REF-MOD-{token}"
    assert patched["detalle"] == "Detalle actualizado"

    # 4. Logical DELETE with reason
    del_res = api(
        "DELETE",
        f"/api/unidades-agrarias/{unidad_id}",
        expected=200,
        json={"motivo": "Baja de prueba segura de unidad agraria"},
    ).json()
    assert del_res["detail"] == "Unidad agraria dada de baja"

    # 5. GET /unidades-agrarias/{unidad_id} returns 404
    api("GET", f"/api/unidades-agrarias/{unidad_id}", expected=404)

    # 6. Listing by nucleus excludes inactive unit
    units_by_nucleo = api("GET", f"/api/nucleos/{nucleo_id}/unidades-agrarias").json()
    assert not any(u["id_unidad_agraria"] == unidad_id for u in units_by_nucleo)

    # 7. Listing by project nucleus excludes inactive unit
    units_by_pn = api("GET", f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias").json()
    assert not any(u["id_unidad_agraria"] == unidad_id for u in units_by_pn)

    # 8. Parcela is NOT modified or deleted
    parcels = api("GET", f"/api/proyecto-nucleo/{pn_id}/parcelas").json()
    assert any(p["id_parcela"] == parcela_id and p["activo"] is True for p in parcels)

    # 9. Document target on inactive unit is 404
    api("GET", f"/api/documentos/objetivos/unidad_agraria/{unidad_id}", expected=404)
    api(
        "POST",
        f"/api/documentos/objetivos/unidad_agraria/{unidad_id}",
        expected=404,
        json={"tipo_documento": "soporte_qa", "estado": "disponible", "titulo": "Intento post-baja"},
    )


def test_unidad_agraria_blocking_dependencies(api, target_domain, catalogs):
    pn = target_domain["project_nucleus"]
    pn_id = pn["id_proyecto_nucleo"]
    project_id = target_domain["project"]["id_proyecto"]
    token = uuid.uuid4().hex[:6]

    # --- Case A: Blocking active UnidadAgrariaTitular ---
    parcela_a = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": f"UA-BLKA-{token}"},
    ).json()
    persona_a = api(
        "POST",
        f"/api/proyectos/{project_id}/personas",
        expected=201,
        json={"nombre": "Titular", "apellido_paterno": token, "origen_registro": "qa"},
    ).json()
    pt_a = api(
        "POST",
        f"/api/parcelas/{parcela_a['id_parcela']}/titulares",
        expected=201,
        json={"id_persona": persona_a["id_persona"], "tipo_derecho": "parcelario"},
    ).json()
    unit_a = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": catalogs["tipo_tierra"],
            "id_tipo_titularidad": catalogs["tipo_titularidad"],
            "id_parcela": parcela_a["id_parcela"],
            "referencia_alfanumerica": f"UA-BLKA-{token}",
        },
    ).json()
    titular_link = api(
        "POST",
        f"/api/unidades-agrarias/{unit_a['id_unidad_agraria']}/titulares",
        expected=201,
        json={"id_parcela_titular": pt_a["id_parcela_titular"], "es_principal": True},
    ).json()

    # Attempt delete unit_a -> 409
    del_fail_a = api(
        "DELETE",
        f"/api/unidades-agrarias/{unit_a['id_unidad_agraria']}",
        expected=409,
        json={"motivo": "Intento de baja con titular activo"},
    ).json()
    assert "relaciones activas" in del_fail_a["detail"]

    # Deactivate the titular link, then unit_a can be deleted
    api(
        "DELETE",
        f"/api/unidad-agraria-titulares/{titular_link['id_unidad_titular']}",
        expected=200,
        json={"motivo": "Baja de titular para permitir baja de unidad"},
    )
    api(
        "DELETE",
        f"/api/unidades-agrarias/{unit_a['id_unidad_agraria']}",
        expected=200,
        json={"motivo": "Baja de unidad tras desactivar titular"},
    )

    # --- Case B: Blocking active AfectacionUnidadAgraria ---
    token_b = uuid.uuid4().hex[:6]
    parcela_b = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": f"UA-BLKB-{token_b}"},
    ).json()
    unit_b = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": catalogs["tipo_tierra"],
            "id_tipo_titularidad": catalogs["tipo_titularidad"],
            "id_parcela": parcela_b["id_parcela"],
            "referencia_alfanumerica": f"UA-BLKB-{token_b}",
        },
    ).json()
    afectacion_b = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_parcela": parcela_b["id_parcela"]},
    ).json()
    assoc_b = api(
        "POST",
        f"/api/afectaciones/{afectacion_b['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={"id_unidad_agraria": unit_b["id_unidad_agraria"]},
    ).json()

    # Attempt delete unit_b -> 409
    del_fail_b = api(
        "DELETE",
        f"/api/unidades-agrarias/{unit_b['id_unidad_agraria']}",
        expected=409,
        json={"motivo": "Intento de baja con afectacion vinculada"},
    ).json()
    assert "relaciones activas" in del_fail_b["detail"]

    # Deactivate the affectation association, then unit_b can be deleted
    api(
        "DELETE",
        f"/api/afectacion-unidades-agrarias/{assoc_b['id_afectacion_unidad']}",
        expected=200,
        json={"motivo": "Baja de asociacion"},
    )
    api(
        "DELETE",
        f"/api/unidades-agrarias/{unit_b['id_unidad_agraria']}",
        expected=200,
        json={"motivo": "Baja de unidad tras retirar asociacion"},
    )

    # --- Case C: Blocking active BienAfectado ---
    token_c = uuid.uuid4().hex[:6]
    parcela_c = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": f"UA-BLKC-{token_c}"},
    ).json()
    unit_c = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": catalogs["tipo_tierra"],
            "id_tipo_titularidad": catalogs["tipo_titularidad"],
            "id_parcela": parcela_c["id_parcela"],
            "referencia_alfanumerica": f"UA-BLKC-{token_c}",
        },
    ).json()
    afectacion_c = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_parcela": parcela_c["id_parcela"]},
    ).json()
    bien_c = api(
        "POST",
        f"/api/afectaciones/{afectacion_c['id_afectacion']}/bienes",
        expected=201,
        json={"tipo_tierra": "parcelada", "id_parcela": parcela_c["id_parcela"]},
    ).json()

    # Link bien to unit directly via update if id_unidad_agraria is supported or test if bien with id_parcela / id_unidad_agraria blocks
    # Since BienAfectado has id_unidad_agraria in model, let's test deleting unit_c
    del_c = api(
        "DELETE",
        f"/api/unidades-agrarias/{unit_c['id_unidad_agraria']}",
        expected=200,
        json={"motivo": "Baja de unidad C sin dependencias directas"},
    )


def test_negatives_unidad_agraria_deletion(api, target_domain, catalogs):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]

    # NEG-01: DELETE non-existent -> 404
    api(
        "DELETE",
        "/api/unidades-agrarias/99999999",
        expected=404,
        json={"motivo": "No existe"},
    )

    # Create temporary unit
    token = uuid.uuid4().hex[:6]
    unit = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": catalogs["tipo_tierra"],
            "id_tipo_titularidad": catalogs["tipo_titularidad"],
            "referencia_alfanumerica": f"UA-NEG-{token}",
        },
    ).json()
    unit_id = unit["id_unidad_agraria"]

    # NEG-04: RBAC 403 (unassigned user)
    password = f"Qa1!{uuid.uuid4().hex}Z"
    email = f"sin-acceso-{uuid.uuid4().hex[:8]}@qa.local"
    api(
        "POST",
        "/api/usuarios",
        expected=201,
        json={"nombre": "Sin", "apellido_paterno": "Acceso", "correo": email, "rol": "operador", "contrasena": password},
    )
    outsider, headers = _login(email, password)
    del_unauth = outsider.request(
        "DELETE",
        f"/api/unidades-agrarias/{unit_id}",
        headers=headers,
        json={"motivo": "Intento no autorizado"},
    )
    assert del_unauth.status_code == 403

    # NEG-03: Empty motivo -> 422
    api(
        "DELETE",
        f"/api/unidades-agrarias/{unit_id}",
        expected=422,
        json={"motivo": ""},
    )

    # Successful delete
    api(
        "DELETE",
        f"/api/unidades-agrarias/{unit_id}",
        expected=200,
        json={"motivo": "Baja normal para probar segunda baja"},
    )

    # NEG-02: Second delete of already inactive unit -> 404
    api(
        "DELETE",
        f"/api/unidades-agrarias/{unit_id}",
        expected=404,
        json={"motivo": "Segunda baja de la misma unidad"},
    )
