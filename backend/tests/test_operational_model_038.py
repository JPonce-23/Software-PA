import uuid
import pytest
from fastapi.testclient import TestClient
from app.config import AUTH_SETTINGS
from app.main import app


@pytest.fixture(scope="module")
def catalogs(api):
    tipo_asambleas = api("GET", "/api/catalogos/operativos/tipo_asamblea").json()
    tipo_eventos_ran = api("GET", "/api/catalogos/operativos/tipo_evento_ran").json()
    tipo_eventos_fifonafe = api("GET", "/api/catalogos/operativos/tipo_evento_fifonafe").json()
    estado_registral_orv = api("GET", "/api/catalogos/operativos/estado_registral_orv").json()

    return {
        "tipo_asamblea": tipo_asambleas[0]["id_catalogo_opcion"],
        "ran_ingreso": next(c["id_catalogo_opcion"] for c in tipo_eventos_ran if c["codigo"] == "ingreso"),
        "ran_inscripcion": next(c["id_catalogo_opcion"] for c in tipo_eventos_ran if c["codigo"] == "inscripcion"),
        "fifonafe_oficio1": next(c["id_catalogo_opcion"] for c in tipo_eventos_fifonafe if c["codigo"] == "oficio_fifonafe_dgaopr"),
        "fifonafe_oficio2": next(c["id_catalogo_opcion"] for c in tipo_eventos_fifonafe if c["codigo"] == "oficio_dgaopr_representacion"),
        "fifonafe_oficio3": next(c["id_catalogo_opcion"] for c in tipo_eventos_fifonafe if c["codigo"] == "respuesta_representacion_dgaopr"),
        "fifonafe_oficio4": next(c["id_catalogo_opcion"] for c in tipo_eventos_fifonafe if c["codigo"] == "respuesta_dgaopr_fifonafe"),
        "orv_estado": estado_registral_orv[0]["id_catalogo_opcion"],
    }


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
def setup_domain(api, target_domain, catalogs):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    af_id = target_domain["collective"][0]["id_afectacion"]

    # Create Asamblea
    asamblea = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": catalogs["tipo_asamblea"],
            "proposito": "Asamblea QA 038",
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_expedicion": "2026-09-01",
                    "fecha_programada": "2026-09-10",
                }
            ],
        },
    ).json()

    # Create Convenio
    convenio = api(
        "POST",
        f"/api/afectaciones/{af_id}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "fecha_firma": "2026-09-01",
        },
    ).json()

    # Create ORV
    orv = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/orv",
        expected=201,
        json={
            "numero_orv": f"ORV-038-{uuid.uuid4().hex[:6]}",
            "id_estado_registral": catalogs["orv_estado"],
        },
    ).json()

    return {
        "asamblea": asamblea,
        "convenio": convenio,
        "orv": orv,
        "project_nucleus_id": pn_id,
        "nucleus_id": target_domain["nucleus"]["id_nucleo"],
        "affectation_id": af_id,
    }


def test_01_ran_1_n_asamblea(api, setup_domain, catalogs):
    asamblea_id = setup_domain["asamblea"]["id_asamblea"]

    r1 = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": asamblea_id,
            "fecha_programada_ingreso": "2026-09-01",
            "referencia_expediente": "EXP-ASAMBLEA-1",
        },
    ).json()

    r2 = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": asamblea_id,
            "fecha_programada_ingreso": "2026-09-02",
            "referencia_expediente": "EXP-ASAMBLEA-2",
        },
    ).json()

    assert r1["id_tramite_ran"] != r2["id_tramite_ran"]
    assert r1["id_asamblea"] == asamblea_id
    assert r2["id_asamblea"] == asamblea_id


def test_02_ran_1_n_convenio(api, setup_domain, catalogs):
    convenio_id = setup_domain["convenio"]["id_convenio"]

    r1 = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_convenio": convenio_id,
            "fecha_programada_ingreso": "2026-09-01",
            "referencia_expediente": "EXP-CONVENIO-1",
        },
    ).json()

    r2 = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_convenio": convenio_id,
            "fecha_programada_ingreso": "2026-09-02",
            "referencia_expediente": "EXP-CONVENIO-2",
        },
    ).json()

    assert r1["id_tramite_ran"] != r2["id_tramite_ran"]
    assert r1["id_convenio"] == convenio_id
    assert r2["id_convenio"] == convenio_id


def test_03_ran_1_n_orv(api, setup_domain, catalogs):
    orv_id = setup_domain["orv"]["id_orv"]

    r1 = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_orv": orv_id,
            "referencia_expediente": "EXP-ORV-1",
        },
    ).json()

    r2 = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_orv": orv_id,
            "referencia_expediente": "EXP-ORV-2",
        },
    ).json()

    assert r1["id_tramite_ran"] != r2["id_tramite_ran"]
    assert r1["id_orv"] == orv_id
    assert r2["id_orv"] == orv_id


def test_04_orv_devuelve_id_nucleo_e_id_pn_null(api, setup_domain):
    orv_id = setup_domain["orv"]["id_orv"]
    nuc_id = setup_domain["nucleus_id"]

    ran = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_orv": orv_id,
            "referencia_expediente": "EXP-ORV-CHECK",
        },
    ).json()

    assert ran["id_orv"] == orv_id
    assert ran["id_nucleo"] == nuc_id
    assert ran["id_proyecto_nucleo"] is None


def test_05_asamblea_devuelve_id_pn_e_id_nucleo_null(api, setup_domain):
    asamblea_id = setup_domain["asamblea"]["id_asamblea"]
    pn_id = setup_domain["project_nucleus_id"]

    ran = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": asamblea_id,
            "referencia_expediente": "EXP-ASAMBLEA-CHECK",
        },
    ).json()

    assert ran["id_asamblea"] == asamblea_id
    assert ran["id_proyecto_nucleo"] == pn_id
    assert ran["id_nucleo"] is None


def test_06_convenio_devuelve_id_pn_e_id_nucleo_null(api, setup_domain):
    convenio_id = setup_domain["convenio"]["id_convenio"]
    pn_id = setup_domain["project_nucleus_id"]

    ran = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_convenio": convenio_id,
            "referencia_expediente": "EXP-CONVENIO-CHECK",
        },
    ).json()

    assert ran["id_convenio"] == convenio_id
    assert ran["id_proyecto_nucleo"] == pn_id
    assert ran["id_nucleo"] is None


def test_07_intento_contexto_ran_incorrecto_rechazado(api, setup_domain):
    # Sin objetivo
    api(
        "POST",
        "/api/tramites-ran",
        expected=422,
        json={"referencia_expediente": "NO-TARGET"},
    )

    # Múltiples objetivos
    api(
        "POST",
        "/api/tramites-ran",
        expected=422,
        json={
            "id_asamblea": setup_domain["asamblea"]["id_asamblea"],
            "id_convenio": setup_domain["convenio"]["id_convenio"],
            "referencia_expediente": "MULTI-TARGET",
        },
    )

    # Objetivo no existente
    api(
        "POST",
        "/api/tramites-ran",
        expected=404,
        json={
            "id_asamblea": 99999999,
            "referencia_expediente": "NON-EXISTENT",
        },
    )


def test_08_rbac_visualizador_read_only(api, target_domain, setup_domain):
    project_id = target_domain["project"]["id_proyecto"]
    asamblea_id = setup_domain["asamblea"]["id_asamblea"]

    password = f"Qa1!{uuid.uuid4().hex}Z"
    email = f"visualizador-{uuid.uuid4().hex[:10]}@qa.local"
    user = api(
        "POST",
        "/api/usuarios",
        expected=201,
        json={
            "nombre": "Visualizador",
            "apellido_paterno": "QA",
            "correo": email,
            "rol": "visualizador",
            "contrasena": password,
        },
    ).json()

    api(
        "POST",
        f"/api/proyectos/{project_id}/usuarios",
        expected=201,
        json={"id_usuario": user["id_usuario"]},
    )

    viewer, viewer_headers = _login(email, password)

    # Read authorized
    resp_list = viewer.get(f"/api/asambleas/{asamblea_id}/tramites-ran", headers=viewer_headers)
    assert resp_list.status_code == 200

    # Write forbidden
    resp_create = viewer.post(
        "/api/tramites-ran",
        headers=viewer_headers,
        json={"id_asamblea": asamblea_id, "referencia_expediente": "VIEWER-NO"},
    )
    assert resp_create.status_code == 403


def test_09_rbac_operador_crea(api, target_domain, setup_domain):
    project_id = target_domain["project"]["id_proyecto"]
    asamblea_id = setup_domain["asamblea"]["id_asamblea"]

    password = f"Qa1!{uuid.uuid4().hex}Z"
    email = f"operador-{uuid.uuid4().hex[:10]}@qa.local"
    user = api(
        "POST",
        "/api/usuarios",
        expected=201,
        json={
            "nombre": "Operador",
            "apellido_paterno": "QA",
            "correo": email,
            "rol": "operador",
            "contrasena": password,
        },
    ).json()

    api(
        "POST",
        f"/api/proyectos/{project_id}/usuarios",
        expected=201,
        json={"id_usuario": user["id_usuario"]},
    )

    op, op_headers = _login(email, password)

    resp = op.post(
        "/api/tramites-ran",
        headers=op_headers,
        json={"id_asamblea": asamblea_id, "referencia_expediente": "OPERADOR-OK"},
    )
    assert resp.status_code == 201


def test_10_asamblea_create_no_acepta_ran_legacy(api, setup_domain, catalogs):
    pn_id = setup_domain["project_nucleus_id"]

    # Crear asamblea canónica con convocatoria
    asamblea = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": catalogs["tipo_asamblea"],
            "proposito": "Asamblea sin RAN legacy",
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_expedicion": "2026-09-01",
                    "fecha_programada": "2026-09-05",
                }
            ],
        },
    ).json()

    # Verificar que no se creó trámite RAN automático
    rans = api("GET", f"/api/asambleas/{asamblea['id_asamblea']}/tramites-ran").json()
    assert len(rans) == 0


def test_11_convenio_create_no_genera_ran_automatico(api, setup_domain):
    af_id = setup_domain["affectation_id"]

    convenio = api(
        "POST",
        f"/api/afectaciones/{af_id}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 2,
            "fecha_firma": "2026-09-02",
        },
    ).json()

    rans = api("GET", f"/api/convenios/{convenio['id_convenio']}/tramites-ran").json()
    assert len(rans) == 0


def test_12_fifonafe_create_no_genera_eventos_desde_legacy(api, setup_domain):
    pn_id = setup_domain["project_nucleus_id"]
    af_id = setup_domain["affectation_id"]

    fifonafe = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/fifonafe",
        expected=201,
        json={
            "ids_afectacion": [af_id],
            "estatus": "pendiente",
        },
    ).json()

    events = api("GET", f"/api/fifonafe/{fifonafe['id_tramite_fifonafe']}/eventos").json()
    assert len(events) == 0


def test_13_eventos_ran_anadidos_correctamente(api, setup_domain, catalogs):
    asamblea_id = setup_domain["asamblea"]["id_asamblea"]

    ran = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": asamblea_id,
            "referencia_expediente": "EXP-EVENTOS-RAN",
        },
    ).json()

    event = api(
        "POST",
        f"/api/tramites-ran/{ran['id_tramite_ran']}/eventos",
        expected=201,
        json={
            "ordinal": 1,
            "id_tipo_evento": catalogs["ran_ingreso"],
            "fecha_evento": "2026-09-01",
            "numero_solicitud": "SOL-038-1",
        },
    ).json()

    assert event["id_tramite_ran"] == ran["id_tramite_ran"]
    assert event["numero_solicitud"] == "SOL-038-1"

    events_list = api("GET", f"/api/tramites-ran/{ran['id_tramite_ran']}/eventos").json()
    assert len(events_list) == 1
    assert events_list[0]["id_evento_ran"] == event["id_evento_ran"]


def test_14_eventos_fifonafe_anadidos_correctamente(api, setup_domain, catalogs):
    pn_id = setup_domain["project_nucleus_id"]
    af_id = setup_domain["affectation_id"]

    fifonafe = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/fifonafe",
        expected=201,
        json={
            "ids_afectacion": [af_id],
            "estatus": "pendiente",
        },
    ).json()

    event = api(
        "POST",
        f"/api/fifonafe/{fifonafe['id_tramite_fifonafe']}/eventos",
        expected=201,
        json={
            "ordinal": 1,
            "id_tipo_evento": catalogs["fifonafe_oficio1"],
            "numero_oficio": "OF-038-1",
            "fecha_oficio": "2026-09-01",
        },
    ).json()

    assert event["id_tramite_fifonafe"] == fifonafe["id_tramite_fifonafe"]
    assert event["numero_oficio"] == "OF-038-1"

    events_list = api("GET", f"/api/fifonafe/{fifonafe['id_tramite_fifonafe']}/eventos").json()
    assert len(events_list) == 1
    assert events_list[0]["id_evento_fifonafe"] == event["id_evento_fifonafe"]


def test_15_ran_orv_no_selecciona_arbitrariamente_proyecto_nucleo(api, setup_domain):
    orv_id = setup_domain["orv"]["id_orv"]
    nuc_id = setup_domain["nucleus_id"]

    ran = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_orv": orv_id,
            "referencia_expediente": "EXP-ORV-STRICT",
        },
    ).json()

    assert ran["id_nucleo"] == nuc_id
    assert ran["id_proyecto_nucleo"] is None

    # List by ORV
    orv_rans = api("GET", f"/api/orv/{orv_id}/tramites-ran").json()
    assert any(r["id_tramite_ran"] == ran["id_tramite_ran"] for r in orv_rans)


def test_16_ran_post_canonico_y_post_legacy_retirado(api, setup_domain):
    asamblea_id = setup_domain["asamblea"]["id_asamblea"]
    project_nucleus_id = setup_domain["project_nucleus_id"]

    ran = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": asamblea_id,
            "referencia_expediente": "CANONICO-POST-038",
        },
    ).json()
    assert ran["id_asamblea"] == asamblea_id

    api(
        "POST",
        f"/api/proyecto-nucleo/{project_nucleus_id}/tramites-ran",
        expected=405,
        json={"id_asamblea": asamblea_id, "referencia_expediente": "LEGACY-POST-038"},
    )

    compatibles = api(
        "GET", f"/api/proyecto-nucleo/{project_nucleus_id}/tramites-ran"
    ).json()
    assert any(item["id_tramite_ran"] == ran["id_tramite_ran"] for item in compatibles)
