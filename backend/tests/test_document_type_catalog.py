"""Catálogo B-03 y coexistencia documental, aislados por rollback."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app import auth, models
from app.main import app
from app.database import engine
from app.services.common import mark_inactive, set_audit_context
from .conftest import unique, target_domain as full_target_domain
from .test_excel_closure_002 import _isolated_pn
from .test_project_user_assignments import _assign
from .test_user_administration import _create_user

CODES = [
    "MINUTA", "FOTOGRAFIA", "ACTA_ASAMBLEA", "PADRON", "ACTA_ELECCION_ORV",
    "ACTA_REMOCION_ORV", "ACTA_NO_VERIFICATIVO", "ACTA_COMPLEMENTARIA",
    "ACTA_DELIMITACION_DESTINO_ASIGNACION", "CONVOCATORIA_PRIMERA",
    "CONVOCATORIA_SEGUNDA", "CONVENIO", "ACUSE_RAN", "SOLICITUD_RAN",
    "AVISO_INSCRIPCION_RAN", "CONSTANCIA_INSCRIPCION_RAN", "FOLIO_EJIDOS_COMUNIDADES",
    "CREDENCIAL_INE", "CREDENCIAL_RAN", "CERTIFICADO_PARCELARIO",
    "CERTIFICADO_DERECHOS_AGRARIOS", "CONSTANCIA_VIGENCIA_DERECHOS", "OFICIO",
    "RESPUESTA", "VALIDACION", "AVALUO", "OTRO",
]


@pytest.fixture(scope="module")
def document_resources(transactional_api, transactional_target_domain):
    api = transactional_api["request"]
    project, pn = _isolated_pn(api, transactional_target_domain)
    _, foreign = _isolated_pn(api, transactional_target_domain)
    users = {}
    for role in ("operador", "visualizador", "geografo"):
        record, _ = _create_user(api, role=role)
        _assign(api, project["id_proyecto"], record["id_usuario"])
        with transactional_api["session_factory"]() as db:
            user = db.get(models.Usuario, record["id_usuario"])
            db.expunge(user)
            users[role] = user
    return project, pn, foreign, users


@pytest.fixture
def docs(transactional_api, document_resources):
    savepoint = transactional_api["connection"].begin_nested()
    project, pn, foreign, users = document_resources
    api = transactional_api["request"]
    try:
        yield SimpleNamespace(
            api=api, project=project, pn=pn, foreign=foreign, users=users,
            factory=transactional_api["session_factory"],
            admin=app.dependency_overrides[auth.get_current_user](),
            types={row["codigo"]: row for row in api("GET", "/api/catalogos/tipos-documento").json()},
            path=f"/api/documentos/objetivos/proyecto_nucleo/{pn['id_proyecto_nucleo']}",
            marker=unique("DOC-B03"),
        )
    finally:
        savepoint.rollback()


def _as(docs, role, method, path, **kwargs):
    user = docs.admin if role == "admin" else docs.users[role]
    previous = app.dependency_overrides[auth.get_current_user]
    app.dependency_overrides[auth.get_current_user] = lambda: user
    try:
        return docs.api(method, path, **kwargs)
    finally:
        app.dependency_overrides[auth.get_current_user] = previous


def _create(docs, *, code="ACTA_ASAMBLEA", **extra):
    payload = {"id_tipo_documento": docs.types[code]["id_tipo_documento"],
               "estado": "disponible", "titulo": docs.marker, **extra}
    return docs.api("POST", docs.path, expected=201, json=payload).json()


def _legacy(docs, value="  Acta LEGADA  "):
    return docs.api("POST", docs.path, expected=201, json={
        "tipo_documento": value, "estado": "disponible", "titulo": docs.marker,
    }).json()


def _read(docs, document_id, role="admin"):
    return next(row for row in _as(docs, role, "GET", docs.path).json()
                if row["id_documento"] == document_id)


def _deactivate(docs, code):
    with docs.factory() as db:
        set_audit_context(db, docs.admin.id_usuario)
        option = db.get(models.CatalogoTipoDocumento, docs.types[code]["id_tipo_documento"])
        mark_inactive(option, docs.admin.id_usuario, "Baja transaccional B-03")
        db.commit()


@pytest.mark.parametrize("role", ["admin", "operador", "visualizador", "geografo"])
def test_catalog_roles_and_projection(docs, role):
    rows = _as(docs, role, "GET", "/api/catalogos/tipos-documento").json()
    assert [row["codigo"] for row in rows] == CODES
    assert all(row["activo"] for row in rows)
    assert all(set(row) == {"id_tipo_documento", "codigo", "nombre",
                           "descripcion", "orden", "activo"} for row in rows)
    assert [row["orden"] for row in rows] == [*range(10, 270, 10), 999]


def test_catalog_inactive_default_and_order(docs):
    _deactivate(docs, "MINUTA")
    rows = docs.api("GET", "/api/catalogos/tipos-documento").json()
    assert "MINUTA" not in {row["codigo"] for row in rows}
    rows = docs.api("GET", "/api/catalogos/tipos-documento",
                    params={"incluir_inactivos": True}).json()
    assert len(rows) == 27 and rows[-1]["codigo"] == "MINUTA" and not rows[-1]["activo"]
    assert rows == sorted(rows, key=lambda row: (
        not row["activo"], row["orden"], row["nombre"], row["codigo"], row["id_tipo_documento"]
    ))


def test_catalog_invalid_boolean(docs):
    docs.api("GET", "/api/catalogos/tipos-documento",
             params={"incluir_inactivos": "invalido"}, expected=422)


@pytest.mark.parametrize("role", ["admin", "operador"])
def test_create_classified_persisted_and_read(docs, role):
    result = _as(docs, role, "POST", docs.path, expected=201, json={
        "id_tipo_documento": docs.types["ACTA_ASAMBLEA"]["id_tipo_documento"],
        "estado": "disponible", "titulo": docs.marker,
    }).json()
    assert result["tipo_documento"] == "Acta de asamblea"
    assert result["clasificacion"] == {
        "id_tipo_documento": result["id_tipo_documento"], "codigo": "ACTA_ASAMBLEA",
        "nombre": "Acta de asamblea", "activo": True,
    }
    assert _read(docs, result["id_documento"]) == result
    with docs.factory() as db:
        saved = db.get(models.Documento, result["id_documento"])
        assert saved.id_tipo_documento == result["id_tipo_documento"]
        assert saved.tipo_documento == "Acta de asamblea"
        link = db.query(models.DocumentoVinculo).filter_by(id_documento=saved.id_documento).one()
        assert (link.entidad_tipo, link.entidad_id) == ("proyecto_nucleo", docs.pn["id_proyecto_nucleo"])


@pytest.mark.parametrize("selector", [
    {}, {"id_tipo_documento": None}, {"id_tipo_documento": -1},
    {"id_tipo_documento": 999999999},
    {"tipo_documento": None}, {"tipo_documento": ""}, {"tipo_documento": " "},
    {"tipo_documento": "   "}, {"tipo_documento": "x" * 81},
    {"tipo_documento": "legado", "id_tipo_documento": 1},
])
def test_create_invalid_selectors_do_not_write(docs, selector):
    with docs.factory() as db:
        before = db.query(models.Documento).count()
    docs.api("POST", docs.path, expected=422,
             json={"estado": "disponible", "titulo": docs.marker, **selector})
    with docs.factory() as db:
        assert db.query(models.Documento).count() == before


@pytest.mark.parametrize("value", [" acta ", "soporte_qa", "x" * 80, "Acta áéí"])
def test_legacy_preserved_without_inference(docs, value):
    result = _legacy(docs, value)
    assert result["tipo_documento"] == value
    assert result["id_tipo_documento"] is None and result["clasificacion"] is None
    assert _read(docs, result["id_documento"]) == result


def test_create_inactive_type(docs):
    _deactivate(docs, "MINUTA")
    docs.api("POST", docs.path, expected=422, json={
        "id_tipo_documento": docs.types["MINUTA"]["id_tipo_documento"], "estado": "disponible",
    })


@pytest.mark.parametrize("description", [None, "", " ", "   "])
def test_other_invalid_description_before_persist(docs, description):
    with docs.factory() as db:
        before = db.query(models.Documento).count()
    docs.api("POST", docs.path, expected=422, json={
        "id_tipo_documento": docs.types["OTRO"]["id_tipo_documento"],
        "estado": "disponible", "descripcion": description,
    })
    with docs.factory() as db:
        assert db.query(models.Documento).count() == before


def test_other_valid_description(docs):
    result = _create(docs, code="OTRO", descripcion="  Documento excepcional  ")
    assert result["descripcion"] == "  Documento excepcional  "
    assert result["tipo_documento"] == "Otro documento"
    assert result["clasificacion"]["codigo"] == "OTRO"


def test_patch_omission_preserves(docs):
    doc = _create(docs)
    result = docs.api("PATCH", f"/api/documentos/{doc['id_documento']}",
                      json={"titulo": "Nuevo título"}).json()
    assert result["id_tipo_documento"] == doc["id_tipo_documento"]
    assert result["tipo_documento"] == doc["tipo_documento"]
    assert result["titulo"] == "Nuevo título"


def test_classify_legacy_and_reclassify_preserve_text(docs):
    doc = _legacy(docs)
    path = f"/api/documentos/{doc['id_documento']}"
    for code in ("ACTA_ASAMBLEA", "MINUTA"):
        result = docs.api("PATCH", path, json={
            "id_tipo_documento": docs.types[code]["id_tipo_documento"],
        }).json()
        assert result["tipo_documento"] == doc["tipo_documento"]
        assert result["clasificacion"]["codigo"] == code
        assert _read(docs, doc["id_documento"])["clasificacion"]["codigo"] == code


@pytest.mark.parametrize("classified", [False, True])
@pytest.mark.parametrize("payload", [
    {"id_tipo_documento": None}, {"id_tipo_documento": 999999999},
    {"tipo_documento": None}, {"tipo_documento": ""},
    {"tipo_documento": " "}, {"tipo_documento": "   "},
    {"tipo_documento": "x" * 81},
    {"tipo_documento": "legado", "id_tipo_documento": 1},
])
def test_patch_invalid_preserves_row(docs, classified, payload):
    doc = _create(docs) if classified else _legacy(docs)
    docs.api("PATCH", f"/api/documentos/{doc['id_documento']}", expected=422, json=payload)
    assert _read(docs, doc["id_documento"]) == doc


def test_patch_legacy_allowed_but_classified_text_protected(docs):
    doc = _legacy(docs)
    path = f"/api/documentos/{doc['id_documento']}"
    updated = docs.api("PATCH", path, json={"tipo_documento": "  Otro texto libre  "}).json()
    assert updated["tipo_documento"] == "  Otro texto libre  "
    docs.api("PATCH", path, json={"id_tipo_documento": docs.types["MINUTA"]["id_tipo_documento"]})
    docs.api("PATCH", path, expected=422, json={"tipo_documento": "simula cambio"})
    assert _read(docs, doc["id_documento"])["tipo_documento"] == updated["tipo_documento"]


def test_existing_inactive_type_read_and_metadata_update(docs):
    doc = _create(docs, code="MINUTA")
    _deactivate(docs, "MINUTA")
    result = docs.api("PATCH", f"/api/documentos/{doc['id_documento']}",
                      json={"titulo": "Metadato permitido"}).json()
    assert result["clasificacion"]["activo"] is False
    docs.api("PATCH", f"/api/documentos/{doc['id_documento']}", expected=422,
             json={"id_tipo_documento": doc["id_tipo_documento"]})
    assert _read(docs, doc["id_documento"])["titulo"] == "Metadato permitido"


def test_patch_inactive_different_type_rejected(docs):
    doc = _create(docs)
    _deactivate(docs, "MINUTA")
    docs.api("PATCH", f"/api/documentos/{doc['id_documento']}", expected=422,
             json={"id_tipo_documento": docs.types["MINUTA"]["id_tipo_documento"]})
    assert _read(docs, doc["id_documento"]) == doc


@pytest.mark.parametrize("description", [None, "", " ", "   "])
def test_patch_other_requires_final_description(docs, description):
    doc = _create(docs, code="OTRO", descripcion="Documento especial")
    docs.api("PATCH", f"/api/documentos/{doc['id_documento']}", expected=422,
             json={"descripcion": description})
    assert _read(docs, doc["id_documento"]) == doc


def test_patch_to_other_and_away(docs):
    doc = _create(docs)
    path = f"/api/documentos/{doc['id_documento']}"
    other_id = docs.types["OTRO"]["id_tipo_documento"]
    docs.api("PATCH", path, expected=422, json={"id_tipo_documento": other_id})
    result = docs.api("PATCH", path, json={
        "id_tipo_documento": other_id, "descripcion": "Validación excepcional",
    }).json()
    assert result["clasificacion"]["codigo"] == "OTRO"
    result = docs.api("PATCH", path, json={
        "id_tipo_documento": docs.types["VALIDACION"]["id_tipo_documento"], "descripcion": None,
    }).json()
    assert result["clasificacion"]["codigo"] == "VALIDACION" and result["descripcion"] is None
    assert result["tipo_documento"] == doc["tipo_documento"]


@pytest.mark.parametrize("role", ["visualizador", "geografo"])
def test_read_roles_cannot_capture_or_patch(docs, role):
    doc = _create(docs)
    assert _read(docs, doc["id_documento"], role)["clasificacion"]["codigo"] == "ACTA_ASAMBLEA"
    _as(docs, role, "POST", docs.path, expected=403, json={
        "id_tipo_documento": doc["id_tipo_documento"], "estado": "disponible",
    })
    _as(docs, role, "PATCH", f"/api/documentos/{doc['id_documento']}",
        expected=403, json={"titulo": "No autorizado"})


@pytest.mark.parametrize("role", ["operador", "visualizador", "geografo"])
def test_foreign_target_not_visible(docs, role):
    path = f"/api/documentos/objetivos/proyecto_nucleo/{docs.foreign['id_proyecto_nucleo']}"
    foreign_doc = docs.api("POST", path, expected=201, json={
        "id_tipo_documento": docs.types["MINUTA"]["id_tipo_documento"],
        "estado": "disponible", "titulo": docs.marker,
    }).json()
    _as(docs, role, "GET", path, expected=403)
    _as(docs, role, "POST", path, expected=403, json={
        "id_tipo_documento": foreign_doc["id_tipo_documento"], "estado": "disponible",
    })
    _as(docs, role, "PATCH", f"/api/documentos/{foreign_doc['id_documento']}",
        expected=403, json={"titulo": "Ajeno"})


def test_health_028(docs):
    assert docs.api("GET", "/health").json() == {"status": "ok", "schema": 28}


def test_existing_document_version_regression_isolated(docs):
    from .test_documents_dashboard import test_document_version_is_immutable_and_downloadable
    with TestClient(app, raise_server_exceptions=False) as client:
        test_document_version_is_immutable_and_downloadable(
            client, {}, docs.api, {"project_nucleus": docs.pn},
        )


@pytest.mark.parametrize("name", [
    # Regresiones documentales aisladas. Las pruebas de cierre judicial y administrativo
    # tienen fallos reproducidos también en HEAD base y se reportan fuera de B-03.
    "test_fifonafe_v2_rondas_triestado_y_reporting_sin_nm",
    "test_fifonafe_interviniente_no_crea_pago_y_evento_es_atomico",
    "test_fifonafe_asamblea_retiro_compartida_y_cop_rechazada",
    "test_fifonafe_representacion_orv_historica_y_externa",
])
def test_existing_fifonafe_regression_isolated(docs, name):
    from . import test_cierre_008_fifonafe_api as regression
    target = full_target_domain.__wrapped__(docs.api)
    getattr(regression, name)(docs.api, target)


def test_requirement_remains_separate_with_classified_support(docs):
    catalog = docs.api("GET", "/api/catalogos/requisitos-documentales").json()
    req = next(row for row in catalog if row["codigo"] == "validacion_pa_sict")
    state = next(row for row in docs.api(
        "GET", "/api/catalogos/operativos/estado_requisito_documental"
    ).json() if row["codigo"] == "pendiente_validacion")
    doc = _create(docs, code="OFICIO")
    result = docs.api("POST", f"/api/proyecto-nucleo/{docs.pn['id_proyecto_nucleo']}/requisitos-documentales",
        expected=201, json={
            "id_requisito": req["id_requisito"], "id_estado": state["id_catalogo_opcion"],
            "entidad_tipo": "proyecto_nucleo", "entidad_id": docs.pn["id_proyecto_nucleo"],
            "id_documento": doc["id_documento"],
        }).json()
    assert result["id_documento"] == doc["id_documento"]
    assert result["id_requisito"] == req["id_requisito"]
    assert _read(docs, doc["id_documento"])["clasificacion"]["codigo"] == "OFICIO"


def test_direct_sql_selection_serializes_with_deactivation(docs):
    # Dos conexiones reales; ambas transacciones se revierten incluso si falla la aserción.
    with engine.connect() as first, engine.connect() as second:
        first_tx = first.begin()
        second_tx = second.begin()
        try:
            first.execute(text("SELECT set_config('app.current_user_id', :actor, true)"),
                          {"actor": str(docs.admin.id_usuario)})
            first.execute(text("""
                INSERT INTO documento(tipo_documento,estado,id_tipo_documento,titulo)
                SELECT nombre,'disponible',id_tipo_documento,:marker
                FROM catalogo_tipo_documento WHERE codigo='MINUTA'
            """), {"marker": docs.marker})
            second.execute(text("SET LOCAL lock_timeout='100ms'"))
            second.execute(text("SELECT set_config('app.current_user_id', :actor, true)"),
                           {"actor": str(docs.admin.id_usuario)})
            with pytest.raises(DBAPIError) as raised:
                second.execute(text("""
                    UPDATE catalogo_tipo_documento SET activo=false,fecha_baja=now(),
                        id_usuario_baja=:actor,motivo_baja='B03 concurrencia revertida'
                    WHERE codigo='MINUTA'
                """), {"actor": docs.admin.id_usuario})
            assert raised.value.orig.pgcode == "55P03"
        finally:
            second_tx.rollback()
            first_tx.rollback()
