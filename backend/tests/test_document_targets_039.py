"""Integration tests for canonical document target access."""
import uuid
import pytest
from sqlalchemy import text
from app import auth, models
from app.main import app
from app.services.access import project_ids_for_document_target
from app.services.common import mark_inactive, set_audit_context
from .test_excel_closure_002 import _isolated_pn


@pytest.fixture(scope="module")
def api(transactional_api):
    """Reuse the canonical rollback fixture, without login credentials or rows left behind."""
    return transactional_api["request"]


@pytest.fixture(scope="module")
def target_domain(api, transactional_target_domain):
    project, pn = _isolated_pn(api, transactional_target_domain)
    return {
        "project": project,
        "project_nucleus": pn,
        "nucleus": {"id_nucleo": pn["id_nucleo"]},
    }


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

    # 3. Afectacion and its canonical agricultural-unit association
    afectacion = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual"},
    ).json()
    afectacion_unidad = api(
        "POST",
        f"/api/afectaciones/{afectacion['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={"id_unidad_agraria": unidad_agraria["id_unidad_agraria"]},
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
    existing_orv = api("GET", f"/api/proyecto-nucleo/{pn_id}/orv").json()
    orv = existing_orv[0] if existing_orv else api(
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


def test_target_403_unauthorized_project(api, domain_fixture, monkeypatch):
    # Authentication identity is injected; project authorization remains real.
    outsider = models.Usuario(id_usuario=-1, rol="operador", activo=True)
    monkeypatch.setitem(app.dependency_overrides, auth.get_current_user, lambda: outsider)
    target_id = domain_fixture["parcela_titular"]["id_parcela_titular"]
    api(
        "POST",
        f"/api/documentos/objetivos/parcela_titular/{target_id}",
        expected=403,
        json={"tipo_documento": "soporte_qa", "estado": "disponible", "titulo": "Denegado"},
    )
    api("GET", f"/api/documentos/objetivos/parcela_titular/{target_id}", expected=403)


@pytest.fixture
def activity_target(api, target_domain):
    activity = api(
        "POST",
        f"/api/proyecto-nucleo/{target_domain['project_nucleus']['id_proyecto_nucleo']}/actividades",
        expected=201,
        json={"tipo_actividad": "caminamiento", "responsable": f"DOC-{uuid.uuid4().hex}"},
    ).json()
    assert activity["id_afectacion"] is None
    return activity


@pytest.fixture(scope="module")
def document_user(transactional_api, target_domain):
    """An assigned operator contained in the outer rollback, with no login/password changes."""
    with transactional_api["session_factory"]() as db:
        admin = app.dependency_overrides[auth.get_current_user]()
        set_audit_context(db, admin.id_usuario)
        user = db.query(models.Usuario).filter(
            models.Usuario.rol == "operador", models.Usuario.activo.is_(True),
        ).order_by(models.Usuario.id_usuario).first()
        assert user is not None, "software_pa_test requiere un operador activo de prueba"
        db.add(models.UsuarioProyecto(
            id_usuario=user.id_usuario,
            id_proyecto=target_domain["project"]["id_proyecto"],
            asignado_por=admin.id_usuario, creado_por=admin.id_usuario,
        ))
        db.commit()
        db.refresh(user)
        db.expunge(user)
        return user


def test_target_activity_authorized_round_trip(
    api, transactional_api, target_domain, activity_target, document_user, monkeypatch
):
    monkeypatch.setitem(app.dependency_overrides, auth.get_current_user, lambda: document_user)
    activity_id = activity_target["id_actividad"]
    assert api("GET", f"/api/documentos/objetivos/actividad_campo/{activity_id}").json() == []
    doc = _upload_and_verify_doc(api, "actividad_campo", activity_id)
    with transactional_api["session_factory"]() as db:
        assert project_ids_for_document_target(db, "actividad_campo", activity_id) == [
            target_domain["project"]["id_proyecto"]
        ]
        link = db.query(models.DocumentoVinculo).filter_by(id_documento=doc["id_documento"]).one()
        assert (link.entidad_tipo, link.entidad_id, link.activo, link.creado_por) == (
            "actividad_campo", activity_id, True, document_user.id_usuario
        )
        assert db.execute(text(
            "SELECT EXISTS (SELECT 1 FROM bitacora WHERE entidad_tipo='documento_vinculo' "
            "AND entidad_id=:id AND id_usuario=:actor AND accion='insert')"
        ), {"id": link.id_documento_vinculo, "actor": document_user.id_usuario}).scalar_one()
    api("PATCH", f"/api/documentos/{doc['id_documento']}", json={"titulo": "Actualizado"})
    api("DELETE", f"/api/documentos/{doc['id_documento']}", json={"motivo": "Cierre de prueba"})
    assert api("GET", f"/api/documentos/objetivos/actividad_campo/{activity_id}").json() == []


def test_target_activity_unauthorized(api, activity_target, monkeypatch):
    outsider = models.Usuario(id_usuario=-1, rol="operador", activo=True)
    monkeypatch.setitem(app.dependency_overrides, auth.get_current_user, lambda: outsider)
    _assert_activity_denied(api, activity_target["id_actividad"], 403)


@pytest.mark.parametrize("role", ["visualizador", "geografo"])
def test_target_activity_read_roles(api, activity_target, document_user, monkeypatch, role):
    monkeypatch.setattr(document_user, "rol", role)
    monkeypatch.setitem(app.dependency_overrides, auth.get_current_user, lambda: document_user)
    path = f"/api/documentos/objetivos/actividad_campo/{activity_target['id_actividad']}"
    api("GET", path)
    response = api("POST", path, expected=403,
                   json={"tipo_documento": "soporte_qa", "estado": "disponible"})
    assert response.json()["detail"] == "Operación no permitida para este rol"


def _assert_activity_denied(api, activity_id, status):
    path = f"/api/documentos/objetivos/actividad_campo/{activity_id}"
    expected_detail = ("Objetivo documental no encontrado" if status == 404
                       else "Proyecto fuera del alcance autorizado")
    assert api("GET", path, expected=status).json()["detail"] == expected_detail
    assert api("POST", path, expected=status, json={
        "tipo_documento": "soporte_qa", "estado": "disponible",
    }).json()["detail"] == expected_detail


def test_target_activity_missing(api):
    _assert_activity_denied(api, 2147483647, 404)


@pytest.mark.parametrize("parent,status", [("activity", 404), ("pn", 404), ("project", 403)])
def test_target_activity_inactive(api, transactional_api, transactional_target_domain, parent, status):
    project, pn = _isolated_pn(api, transactional_target_domain)
    activity = api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/actividades",
                   expected=201, json={"tipo_actividad": "sensibilizacion"}).json()
    model, pk = {
        "activity": (models.ActividadCampo, activity["id_actividad"]),
        "pn": (models.ProyectoNucleo, pn["id_proyecto_nucleo"]),
        "project": (models.Proyecto, project["id_proyecto"]),
    }[parent]
    with transactional_api["session_factory"]() as db:
        admin = app.dependency_overrides[auth.get_current_user]()
        set_audit_context(db, admin.id_usuario)
        mark_inactive(db.get(model, pk), admin.id_usuario, "Baja de fixture documental")
        db.commit()
    _assert_activity_denied(api, activity["id_actividad"], status)


def test_target_activity_existing_link_and_versions(api, target_domain, activity_target):
    doc = _upload_and_verify_doc(
        api, "proyecto_nucleo", target_domain["project_nucleus"]["id_proyecto_nucleo"]
    )
    activity_id = activity_target["id_actividad"]
    path = f"/api/documentos/{doc['id_documento']}/vinculos/actividad_campo/{activity_id}"
    link = api("POST", path, expected=201).json()
    assert (link["entidad_tipo"], link["entidad_id"]) == ("actividad_campo", activity_id)
    assert any(row["id_documento"] == doc["id_documento"] for row in
               api("GET", f"/api/documentos/objetivos/actividad_campo/{activity_id}").json())
    api("POST", path, expected=409)
    content = b"%PDF-1.4\nContrato B-04\n%%EOF\n"
    version = api("POST", f"/api/documentos/{doc['id_documento']}/versiones", expected=201,
                  files={"archivo": ("actividad.pdf", content, "application/pdf")}).json()
    api("POST", f"/api/documentos/{doc['id_documento']}/versiones", expected=409,
        files={"archivo": ("actividad.pdf", content, "application/pdf")})
    assert api("GET", f"/api/documentos/versiones/{version['id_documento_version']}/descarga").content == content


def test_target_activity_requirement_unchanged(api, target_domain, activity_target, catalogs):
    doc = _upload_and_verify_doc(api, "actividad_campo", activity_target["id_actividad"])
    requirement_id = api("GET", "/api/catalogos/requisitos-documentales").json()[0]["id_requisito"]
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    requirement = api("POST", f"/api/proyecto-nucleo/{pn_id}/requisitos-documentales", expected=201,
                      json={"id_requisito": requirement_id, "id_estado": catalogs["estado_requisito"],
                            "id_documento": doc["id_documento"], "entidad_tipo": "actividad_campo",
                            "entidad_id": activity_target["id_actividad"]}).json()
    assert requirement["id_documento"] == doc["id_documento"]
    assert any(row["id_expediente_requisito"] == requirement["id_expediente_requisito"] for row in
               api("GET", f"/api/proyecto-nucleo/{pn_id}/requisitos-documentales").json())
