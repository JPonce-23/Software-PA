"""Integration tests for document target access on all 22 supported entity types in 039."""
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
        "calidad_compareciente": next(iter(get_cat("calidad_compareciente_convenio").values())),
        "tipo_acreditacion": next(iter(get_cat("tipo_acreditacion_derecho_individual").values())),
        "tipo_evento_ran": next(iter(get_cat("tipo_evento_ran").values())),
        "tipo_evento_fifonafe": next(iter(get_cat("tipo_evento_fifonafe").values())),
        "tipo_asamblea": next(iter(get_cat("tipo_asamblea").values())),
        "estado_requisito": next(iter(get_cat("estado_requisito_documental").values())),
    }


@pytest.fixture(scope="module")
def domain_fixture(api, target_domain, catalogs):
    token = uuid.uuid4().hex[:8]
    project_id = target_domain["project"]["id_proyecto"]
    pn = target_domain["project_nucleus"]
    pn_id = pn["id_proyecto_nucleo"]
    nucleo_id = target_domain["nucleus"]["id_nucleo"]

    # 1. Parcela and ParcelaTitular
    parcela = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": f"DOC-P-{token}"},
    ).json()
    persona = api(
        "POST",
        f"/api/proyectos/{project_id}/personas",
        expected=201,
        json={"nombre": "Persona", "apellido_paterno": token, "origen_registro": "qa"},
    ).json()
    parcela_titular = api(
        "POST",
        f"/api/parcelas/{parcela['id_parcela']}/titulares",
        expected=201,
        json={"id_persona": persona["id_persona"], "tipo_derecho": "parcelario"},
    ).json()

    # 2. UnidadAgraria and UnidadAgrariaTitular
    unidad_agraria = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": catalogs["tipo_tierra"],
            "id_tipo_titularidad": catalogs["tipo_titularidad"],
            "id_parcela": parcela["id_parcela"],
            "referencia_alfanumerica": f"UA-DOC-{token}",
        },
    ).json()
    unidad_titular = api(
        "POST",
        f"/api/unidades-agrarias/{unidad_agraria['id_unidad_agraria']}/titulares",
        expected=201,
        json={"id_parcela_titular": parcela_titular["id_parcela_titular"], "es_principal": True},
    ).json()

    # 3. Afectacion, AfectacionUnidadAgraria, and BienAfectado
    afectacion = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_parcela": parcela["id_parcela"]},
    ).json()
    afectacion_unidad = api(
        "POST",
        f"/api/afectaciones/{afectacion['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={"id_unidad_agraria": unidad_agraria["id_unidad_agraria"]},
    ).json()
    bien_afectado = api(
        "POST",
        f"/api/afectaciones/{afectacion['id_afectacion']}/bienes",
        expected=201,
        json={"tipo_tierra": "parcelada", "referencia_alfanumerica": f"BIEN-DOC-{token}"},
    ).json()

    # 4. Asamblea and AsambleaConvocatoria
    asamblea = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": catalogs["tipo_asamblea"],
            "proposito": f"Asamblea Doc {token}",
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_expedicion": "2026-09-01",
                    "fecha_programada": "2026-09-10",
                }
            ],
        },
    ).json()
    asamblea_convocatoria = asamblea["convocatorias"][0]

    # 5. Convenio and ConvenioCompareciente
    convenio = api(
        "POST",
        f"/api/afectaciones/{afectacion['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "fecha_firma": "2026-09-01",
            "comparecientes": [
                {
                    "id_persona": persona["id_persona"],
                    "id_parcela_titular": parcela_titular["id_parcela_titular"],
                    "id_tipo_calidad": catalogs["calidad_compareciente"],
                    "id_tipo_acreditacion": catalogs["tipo_acreditacion"],
                    "referencia_acreditacion": f"ACR-{token}",
                    "nombre_en_instrumento": "Compareciente QA",
                    "es_firmante": True,
                }
            ],
        },
    ).json()
    compareciente = api("GET", f"/api/convenios/{convenio['id_convenio']}/comparecientes").json()[0]

    # 6. TramiteRan (PN context via Convenio) & Evento
    ran_pn = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_convenio": convenio["id_convenio"],
            "referencia_expediente": f"RAN-PN-{token}",
            "eventos": [
                {
                    "ordinal": 1,
                    "id_tipo_evento": catalogs["tipo_evento_ran"],
                    "fecha_evento": "2026-09-02",
                }
            ],
        },
    ).json()
    ran_pn_evento = ran_pn["eventos"][0]

    # 7. ORV & TramiteRan (ORV context with id_nucleo) & Evento
    orv = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/orv",
        expected=201,
        json={"numero_orv": f"ORV-DOC-{token}", "inicio_vigencia": "2026-01-01"},
    ).json()
    ran_orv = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_orv": orv["id_orv"],
            "referencia_expediente": f"RAN-ORV-{token}",
            "eventos": [
                {
                    "ordinal": 1,
                    "id_tipo_evento": catalogs["tipo_evento_ran"],
                    "fecha_evento": "2026-09-02",
                }
            ],
        },
    ).json()
    assert ran_orv["id_proyecto_nucleo"] is None
    assert ran_orv["id_nucleo"] == nucleo_id
    ran_orv_evento = ran_orv["eventos"][0]

    # 8. TramiteFifonafe & Evento
    fifonafe = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/fifonafe",
        expected=201,
        json={"ids_afectacion": [afectacion["id_afectacion"]], "estatus": "pendiente"},
    ).json()
    fifonafe_evento = api(
        "POST",
        f"/api/fifonafe/{fifonafe['id_tramite_fifonafe']}/eventos",
        expected=201,
        json={
            "ordinal": 1,
            "id_tipo_evento": catalogs["tipo_evento_fifonafe"],
            "numero_oficio": f"OF-DOC-{token}",
            "fecha_oficio": "2026-09-01",
        },
    ).json()

    # 9. ExpedienteRequisito
    reqs = api("GET", "/api/catalogos/requisitos-documentales").json()
    expediente_req = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/requisitos-documentales",
        expected=201,
        json={
            "id_requisito": reqs[0]["id_requisito"],
            "id_estado": catalogs["estado_requisito"],
            "entidad_tipo": "parcela",
            "entidad_id": parcela["id_parcela"],
        },
    ).json()

    return {
        "project": target_domain["project"],
        "project_nucleus": pn,
        "parcela_titular": parcela_titular,
        "bien_afectado": bien_afectado,
        "unidad_agraria": unidad_agraria,
        "unidad_agraria_titular": unidad_titular,
        "afectacion_unidad_agraria": afectacion_unidad,
        "asamblea_convocatoria": asamblea_convocatoria,
        "convenio_compareciente": compareciente,
        "tramite_ran_pn": ran_pn,
        "tramite_ran_pn_evento": ran_pn_evento,
        "tramite_ran_orv": ran_orv,
        "tramite_ran_orv_evento": ran_orv_evento,
        "tramite_fifonafe_evento": fifonafe_evento,
        "expediente_requisito": expediente_req,
    }


def _upload_and_verify_doc(api, entity_type: str, entity_id: int):
    token = uuid.uuid4().hex[:6]
    doc = api(
        "POST",
        f"/api/documentos/objetivos/{entity_type}/{entity_id}",
        expected=201,
        json={
            "tipo_documento": "soporte_qa",
            "estado": "disponible",
            "titulo": f"Doc {entity_type} {token}",
        },
    ).json()
    assert doc["id_documento"] > 0

    docs = api("GET", f"/api/documentos/objetivos/{entity_type}/{entity_id}").json()
    assert any(d["id_documento"] == doc["id_documento"] for d in docs)
    return doc


def test_target_parcela_titular(api, domain_fixture):
    _upload_and_verify_doc(api, "parcela_titular", domain_fixture["parcela_titular"]["id_parcela_titular"])


def test_target_bien_afectado(api, domain_fixture):
    _upload_and_verify_doc(api, "bien_afectado", domain_fixture["bien_afectado"]["id_bien_afectado"])


def test_target_unidad_agraria(api, domain_fixture):
    _upload_and_verify_doc(api, "unidad_agraria", domain_fixture["unidad_agraria"]["id_unidad_agraria"])


def test_target_unidad_agraria_titular(api, domain_fixture):
    _upload_and_verify_doc(api, "unidad_agraria_titular", domain_fixture["unidad_agraria_titular"]["id_unidad_titular"])


def test_target_afectacion_unidad_agraria(api, domain_fixture):
    _upload_and_verify_doc(api, "afectacion_unidad_agraria", domain_fixture["afectacion_unidad_agraria"]["id_afectacion_unidad"])


def test_target_asamblea_convocatoria(api, domain_fixture):
    _upload_and_verify_doc(api, "asamblea_convocatoria", domain_fixture["asamblea_convocatoria"]["id_convocatoria"])


def test_target_convenio_compareciente(api, domain_fixture):
    _upload_and_verify_doc(api, "convenio_compareciente", domain_fixture["convenio_compareciente"]["id_compareciente"])


def test_target_tramite_ran_pn(api, domain_fixture):
    _upload_and_verify_doc(api, "tramite_ran", domain_fixture["tramite_ran_pn"]["id_tramite_ran"])


def test_target_tramite_ran_orv(api, domain_fixture):
    _upload_and_verify_doc(api, "tramite_ran", domain_fixture["tramite_ran_orv"]["id_tramite_ran"])


def test_target_tramite_ran_evento_pn(api, domain_fixture):
    _upload_and_verify_doc(api, "tramite_ran_evento", domain_fixture["tramite_ran_pn_evento"]["id_evento_ran"])


def test_target_tramite_ran_evento_orv(api, domain_fixture):
    _upload_and_verify_doc(api, "tramite_ran_evento", domain_fixture["tramite_ran_orv_evento"]["id_evento_ran"])


def test_target_tramite_fifonafe_evento(api, domain_fixture):
    _upload_and_verify_doc(api, "tramite_fifonafe_evento", domain_fixture["tramite_fifonafe_evento"]["id_evento_fifonafe"])


def test_target_expediente_requisito(api, domain_fixture):
    _upload_and_verify_doc(api, "expediente_requisito", domain_fixture["expediente_requisito"]["id_expediente_requisito"])


def test_target_404_not_found(api):
    api(
        "POST",
        "/api/documentos/objetivos/parcela_titular/99999999",
        expected=404,
        json={"tipo_documento": "soporte_qa", "estado": "disponible", "titulo": "No existe"},
    )
    api("GET", "/api/documentos/objetivos/parcela_titular/99999999", expected=404)
    api(
        "POST",
        "/api/documentos/objetivos/tramite_ran/99999999",
        expected=404,
        json={"tipo_documento": "soporte_qa", "estado": "disponible", "titulo": "No existe"},
    )
    api("GET", "/api/documentos/objetivos/tramite_ran/99999999", expected=404)


def test_target_422_invalid_type(api, domain_fixture):
    api(
        "POST",
        "/api/documentos/objetivos/tipo_no_permitido/1",
        expected=422,
        json={"tipo_documento": "soporte_qa", "estado": "disponible", "titulo": "Invalido"},
    )
    api("GET", "/api/documentos/objetivos/tipo_no_permitido/1", expected=422)


def test_target_403_unauthorized_project(api, domain_fixture):
    password = f"Qa1!{uuid.uuid4().hex}Z"
    email = f"sin-acceso-{uuid.uuid4().hex[:8]}@qa.local"
    api(
        "POST",
        "/api/usuarios",
        expected=201,
        json={"nombre": "Sin", "apellido_paterno": "Acceso", "correo": email, "rol": "operador", "contrasena": password},
    )
    outsider, headers = _login(email, password)

    # Try to access a target in a project the outsider is not assigned to
    target_id = domain_fixture["parcela_titular"]["id_parcela_titular"]
    res_post = outsider.post(
        f"/api/documentos/objetivos/parcela_titular/{target_id}",
        headers=headers,
        json={"tipo_documento": "soporte_qa", "estado": "disponible", "titulo": "Denegado"},
    )
    assert res_post.status_code == 403

    res_get = outsider.get(f"/api/documentos/objetivos/parcela_titular/{target_id}", headers=headers)
    assert res_get.status_code == 403
