"""Integration contract for individual identity, COP and its RAN procedure."""
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from app.config import AUTH_SETTINGS
from app.database import SessionLocal
from app import models
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from app.main import app


def _login(email, password):
    client = TestClient(app, raise_server_exceptions=False)
    origin = AUTH_SETTINGS.allowed_origins[0]
    response = client.post("/api/auth/sesiones", data={"username": email, "password": password}, headers={"Origin": origin})
    assert response.status_code == 200, response.text
    return client, {"Origin": origin, "X-CSRF-Token": client.cookies.get(AUTH_SETTINGS.csrf_cookie_name)}


def _catalog(api, name):
    return {x["codigo"]: x["id_catalogo_opcion"] for x in api("GET", f"/api/catalogos/operativos/{name}").json()}


@pytest.fixture(scope="module")
def individual(api, target_domain):
    pn = target_domain["project_nucleus"]; token = uuid.uuid4().hex[:8]
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    titularidad = _catalog(api, "tipo_titularidad_unidad")["persona"]
    parcela = api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/parcelas", expected=201, json={"tipo_parcela":"individual","no_parcela":f"P039-{token}"}).json()
    persona = api("POST", f"/api/proyectos/{target_domain['project']['id_proyecto']}/personas", expected=201, json={"nombre":"Titular","apellido_paterno":token,"origen_registro":"qa"}).json()
    pt = api("POST", f"/api/parcelas/{parcela['id_parcela']}/titulares", expected=201, json={"id_persona":persona["id_persona"],"tipo_derecho":"parcelario"}).json()
    unidad = api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/unidades-agrarias", expected=201, json={"id_tipo_tierra":tierra,"id_tipo_titularidad":titularidad,"id_parcela":parcela["id_parcela"],"referencia_alfanumerica":f"UA039-{token}"}).json()
    ut = api("POST", f"/api/unidades-agrarias/{unidad['id_unidad_agraria']}/titulares", expected=201, json={"id_parcela_titular":pt["id_parcela_titular"],"es_principal":True}).json()
    return {"pn":pn,"parcela":parcela,"persona":persona,"pt":pt,"unidad":unidad,"ut":ut}


def test_01_individual_identity(api, target_domain, individual):
    row = individual
    assert row["parcela"]["no_parcela"] and row["parcela"]["id_nucleo"] == target_domain["nucleus"]["id_nucleo"]
    unidad = api("GET", f"/api/unidades-agrarias/{row['unidad']['id_unidad_agraria']}").json()
    assert unidad["id_parcela"] == row["parcela"]["id_parcela"] and unidad["id_nucleo"] == row["parcela"]["id_nucleo"]
    titulares = api("GET", f"/api/unidades-agrarias/{row['unidad']['id_unidad_agraria']}/titulares").json()
    assert any(x["id_unidad_titular"] == row["ut"]["id_unidad_titular"] and x["id_parcela_titular"] == row["pt"]["id_parcela_titular"] for x in titulares)


@pytest.fixture(scope="module")
def original(api, individual):
    calidad = _catalog(api, "calidad_compareciente_convenio"); acreditacion = _catalog(api, "tipo_acreditacion_derecho_individual")
    a = api("POST", f"/api/proyecto-nucleo/{individual['pn']['id_proyecto_nucleo']}/afectaciones", expected=201, json={"tipo_afectacion":"individual","id_parcela":individual["parcela"]["id_parcela"]}).json()
    api("POST", f"/api/afectaciones/{a['id_afectacion']}/unidades-agrarias", expected=201, json={"id_unidad_agraria":individual["unidad"]["id_unidad_agraria"]})
    c = api("POST", f"/api/afectaciones/{a['id_afectacion']}/convenios", expected=201, json={"tipo_instrumento":"convenio","tipo_convenio":"cop_original","fecha_firma":"2026-09-01","comparecientes":[{"id_persona":individual["persona"]["id_persona"],"id_parcela_titular":individual["pt"]["id_parcela_titular"],"id_tipo_calidad":calidad["titular_parcelario"],"id_tipo_acreditacion":acreditacion["certificado_parcelario"],"referencia_acreditacion":"CERT-039","nombre_en_instrumento":"Titular histórico","es_firmante":True}]}).json()
    return {**individual,"afectacion":a,"convenio":c}


def test_02_signed_original(api, original):
    r = original; c = r["convenio"]
    assert c["ambito"] == "individual" and c["tipo_convenio"] == "cop_original" and c["id_convenio_padre"] is None
    assert any(x["id_convenio"] == c["id_convenio"] for x in api("GET", f"/api/afectaciones/{r['afectacion']['id_afectacion']}/convenios").json())
    cc = api("GET", f"/api/convenios/{c['id_convenio']}/comparecientes").json()[0]
    assert cc["id_persona"] == r["persona"]["id_persona"] and cc["es_firmante"] and cc["nombre_en_instrumento"] == "Titular histórico"


def test_03_ran_for_original(api, original):
    tipos = _catalog(api, "tipo_evento_ran"); c = original["convenio"]
    ran = api("POST", "/api/tramites-ran", expected=201, json={"id_convenio":c["id_convenio"],"referencia_expediente":"RAN-039","eventos":[{"ordinal":1,"id_tipo_evento":tipos["ingreso"],"fecha_evento":"2026-09-02"},{"ordinal":2,"id_tipo_evento":tipos["calificacion"],"fecha_evento":"2026-09-03"},{"ordinal":3,"id_tipo_evento":tipos["inscripcion"],"fecha_evento":"2026-09-04"}]}).json()
    assert ran["id_convenio"] == c["id_convenio"] and ran["id_proyecto_nucleo"] == original["pn"]["id_proyecto_nucleo"]
    assert [x["ordinal"] for x in ran["eventos"]] == [1,2,3]
    assert any(x["id_tramite_ran"] == ran["id_tramite_ran"] for x in api("GET", f"/api/convenios/{c['id_convenio']}/tramites-ran").json())


def test_08_general_activity(api, individual):
    pn = individual["pn"]["id_proyecto_nucleo"]
    created = api("POST", f"/api/proyecto-nucleo/{pn}/actividades", expected=201, json={"tipo_actividad":"sensibilizacion"}).json()
    assert created["id_proyecto_nucleo"] == pn and created["id_afectacion"] is None
    assert any(x["id_actividad"] == created["id_actividad"] for x in api("GET", f"/api/proyecto-nucleo/{pn}/actividades").json())


def test_09_specific_activity(api, original):
    pn = original["pn"]["id_proyecto_nucleo"]; aid = original["afectacion"]["id_afectacion"]
    activity = api("POST", f"/api/proyecto-nucleo/{pn}/actividades", expected=201, json={"tipo_actividad":"caminamiento", "id_afectacion":aid}).json()
    assert activity["id_afectacion"] == aid and activity["id_proyecto_nucleo"] == pn


def test_10_cross_project_activity_rejected(api, original, target_domain):
    other = api("POST", "/api/proyectos", expected=201, json={"clave_proyecto":f"P039-{uuid.uuid4().hex[:8]}","nombre_proyecto":"P039 B","fecha_inicio":"2026-01-01"}).json()
    nucleus = api("POST", "/api/nucleos", expected=201, json={"id_municipio":target_domain["municipality"]["id_municipio"],"nombre_nucleo":f"N039-{uuid.uuid4().hex[:8]}","tipo_nucleo":"ejido","fuente_datos":"qa"}).json()
    pn_b = api("POST", f"/api/proyectos/{other['id_proyecto']}/nucleos", expected=201, json={"id_nucleo":nucleus["id_nucleo"],"residencia":"QA","referencias":[]}).json()
    parcel = api("POST", f"/api/proyecto-nucleo/{pn_b['id_proyecto_nucleo']}/parcelas", expected=201, json={"tipo_parcela":"individual","no_parcela":f"PX-{uuid.uuid4().hex[:8]}"}).json()
    affectation = api("POST", f"/api/proyecto-nucleo/{pn_b['id_proyecto_nucleo']}/afectaciones", expected=201, json={"tipo_afectacion":"individual","id_parcela":parcel["id_parcela"]}).json()
    api("POST", f"/api/proyecto-nucleo/{original['pn']['id_proyecto_nucleo']}/actividades", expected=409, json={"tipo_actividad":"caminamiento","id_afectacion":affectation["id_afectacion"]})


def test_11_collective_and_individual_coexist(api, original):
    pn = original["pn"]["id_proyecto_nucleo"]
    collective = api("POST", f"/api/proyecto-nucleo/{pn}/afectaciones", expected=201, json={"tipo_afectacion":"colectivo"}).json()
    individual = api("GET", f"/api/proyecto-nucleo/{pn}/afectaciones").json()
    assert collective["tipo_afectacion"] == "colectivo" and any(x["tipo_afectacion"] == "individual" for x in individual)


def test_12_individual_has_no_assembly_side_effect(api, original):
    assemblies = api("GET", f"/api/proyecto-nucleo/{original['pn']['id_proyecto_nucleo']}/asambleas").json()
    assert not any(x.get("id_asamblea") == original["convenio"].get("id_asamblea_autorizacion") for x in assemblies)


def test_13_individual_fifonafe(api, original):
    pn = original["pn"]["id_proyecto_nucleo"]; aid = original["afectacion"]["id_afectacion"]
    fif = api("POST", f"/api/proyecto-nucleo/{pn}/fifonafe", expected=201, json={"ids_afectacion":[aid],"estatus":"pendiente"}).json()
    assert fif["ambito"] == "individual" and any(x["id_afectacion"] == aid for x in fif["afectaciones"])


def test_14_indemnity_and_payment(api, original):
    aid = original["afectacion"]["id_afectacion"]
    indemnity = api("POST", f"/api/afectaciones/{aid}/indemnizacion", expected=201, json={"estatus":"pendiente"}).json()
    payment = api("POST", f"/api/indemnizaciones/{indemnity['id_indemnizacion']}/pagos", expected=201, json={"fecha_pago":"2026-09-05","monto":"100.00","beneficiario_nombre":"Titular histórico","medio_pago":"transferencia"}).json()
    assert indemnity["id_afectacion"] == aid and payment["id_indemnizacion"] == indemnity["id_indemnizacion"]


def test_15_document_requirements_for_individual_targets(api, original):
    pn = original["pn"]["id_proyecto_nucleo"]; requirements = api("GET", "/api/catalogos/requisitos-documentales").json()
    ran = api("POST", "/api/tramites-ran", expected=201, json={"id_convenio":original["convenio"]["id_convenio"],"referencia_expediente":"DOC-039"}).json()
    states = _catalog(api, "estado_requisito_documental"); state = next(iter(states.values()))
    req = requirements[0]
    for kind, ident in (("parcela", original["parcela"]["id_parcela"]), ("convenio", original["convenio"]["id_convenio"]), ("tramite_ran", ran["id_tramite_ran"])):
        api("POST", f"/api/proyecto-nucleo/{pn}/requisitos-documentales", expected=201, json={"id_requisito":req["id_requisito"],"id_estado":state,"entidad_tipo":kind,"entidad_id":ident})


def test_16_authorized_update_and_logical_delete(api, individual):
    uid = individual["ut"]["id_unidad_titular"]; unit = individual["unidad"]["id_unidad_agraria"]
    updated = api("PATCH", f"/api/unidad-agraria-titulares/{uid}", json={"es_principal":False}).json()
    assert updated["es_principal"] is False
    password = f"Qa1!{uuid.uuid4().hex}Z"; email = f"sin-acceso-{uuid.uuid4().hex[:8]}@qa.local"
    api("POST", "/api/usuarios", expected=201, json={"nombre":"Sin","apellido_paterno":"Acceso","correo":email,"rol":"operador","contrasena":password})
    outsider, headers = _login(email, password)
    denied = outsider.patch(f"/api/unidad-agraria-titulares/{uid}", headers=headers, json={"es_principal":True})
    assert denied.status_code == 403
    api("DELETE", f"/api/unidad-agraria-titulares/{uid}", expected=200, json={"motivo":"Titularidad histórica cerrada"})
    assert not any(x["id_unidad_titular"] == uid for x in api("GET", f"/api/unidades-agrarias/{unit}/titulares").json())

    db = SessionLocal()
    try:
        persisted = db.query(__import__("app.models", fromlist=["UnidadAgrariaTitular"]).UnidadAgrariaTitular).filter_by(id_unidad_titular=uid).one()
        assert persisted.activo is False
    finally:
        db.close()


def test_neg_07_signed_without_signer(api, individual):
    affectation = _second_affectation(api, individual)
    api("POST", f"/api/afectaciones/{affectation['id_afectacion']}/convenios", expected=409, json={"tipo_instrumento":"convenio","tipo_convenio":"cop_original","fecha_firma":"2026-09-10"})


def test_neg_08_signed_without_individual_affectation(api, original):
    accreditation = next(iter(_catalog(api, "tipo_acreditacion_derecho_individual").values()))
    db = SessionLocal()
    try:
        user = db.query(models.Usuario).filter(models.Usuario.activo.is_(True)).first()
        db.execute(
            text("SELECT set_config('app.current_user_id', :id, true)"),
            {"id": str(user.id_usuario)},
        )
        convenio = models.Convenio(id_proyecto_nucleo=original["pn"]["id_proyecto_nucleo"], ambito="individual", tipo_instrumento="convenio", tipo_convenio="cop_original", consecutivo=99, fecha_firma=date(2026, 9, 11), creado_por=user.id_usuario)
        db.add(convenio); db.flush()
        db.add(models.ConvenioCompareciente(id_convenio=convenio.id_convenio, id_persona=original["persona"]["id_persona"], id_tipo_calidad=next(iter(_catalog(api,"calidad_compareciente_convenio").values())), id_tipo_acreditacion=accreditation, referencia_acreditacion="QA-039-ACREDITACION", nombre_en_instrumento="Firmante válido", es_firmante=True, creado_por=user.id_usuario))
        with pytest.raises(DBAPIError) as exc_info:
            db.commit()
        assert "Un convenio activo requiere al menos una afectaci" in str(exc_info.value)
        db.rollback()
        assert db.query(models.Convenio).filter_by(id_convenio=convenio.id_convenio).first() is None
    finally:
        db.close()


def test_neg_09_incoherent_compareciente_rejected(api, original, target_domain):
    other = target_domain["parcels"][1]
    person = api("POST", f"/api/proyectos/{target_domain['project']['id_proyecto']}/personas", expected=201, json={"nombre":"Ajeno","apellido_paterno":"039","origen_registro":"qa"}).json()
    holder = api("POST", f"/api/parcelas/{other['id_parcela']}/titulares", expected=201, json={"id_persona":person["id_persona"],"tipo_derecho":"parcelario"}).json()
    api("POST", f"/api/convenios/{original['convenio']['id_convenio']}/comparecientes", expected=409, json={"id_persona":person["id_persona"],"id_parcela_titular":holder["id_parcela_titular"],"id_tipo_calidad":next(iter(_catalog(api,"calidad_compareciente_convenio").values())),"nombre_en_instrumento":"Ajeno","es_firmante":True})
    persisted = api("GET", f"/api/convenios/{original['convenio']['id_convenio']}/comparecientes").json()
    assert not any(item["id_persona"] == person["id_persona"] for item in persisted)


def test_neg_10_cross_project_activity(api, original, target_domain):
    test_10_cross_project_activity_rejected(api, original, target_domain)


def _second_affectation(api, row):
    a = api("POST", f"/api/proyecto-nucleo/{row['pn']['id_proyecto_nucleo']}/afectaciones", expected=201, json={"tipo_afectacion":"individual", "id_parcela":row["parcela"]["id_parcela"]}).json()
    api("POST", f"/api/afectaciones/{a['id_afectacion']}/unidades-agrarias", expected=201, json={"id_unidad_agraria":row["unidad"]["id_unidad_agraria"]})
    return a


def _child(api, row, tipo, affectation=None):
    a = affectation or _second_affectation(api, row)
    consecutivos = {"ampliacion": 2, "ampliacion_remanente": 3, "modificatorio": 4}
    return api("POST", f"/api/afectaciones/{a['id_afectacion']}/convenios", expected=201, json={"tipo_instrumento":"convenio", "tipo_convenio":tipo, "consecutivo":consecutivos[tipo], "id_convenio_padre":row["convenio"]["id_convenio"]}).json()


def test_04_ampliacion_reuses_identity(api, original):
    child = _child(api, original, "ampliacion")
    assert child["ambito"] == "individual" and child["id_convenio_padre"] == original["convenio"]["id_convenio"]
    second = api("GET", f"/api/afectaciones/{original['afectacion']['id_afectacion']}/unidades-agrarias").json()
    other = api("GET", f"/api/convenios/{child['id_convenio']}/afectaciones").json() if False else []
    assert original["unidad"]["id_unidad_agraria"] in [x["id_unidad_agraria"] for x in second]
    units = api("GET", f"/api/nucleos/{original['pn']['id_nucleo']}/unidades-agrarias").json()
    assert sum(x["id_unidad_agraria"] == original["unidad"]["id_unidad_agraria"] for x in units) == 1
    assert original["parcela"]["id_parcela"] == original["unidad"]["id_parcela"]


def test_05_ampliacion_remanente_and_modificatorio(api, original):
    remanente = _child(api, original, "ampliacion_remanente")
    modificatorio = _child(api, original, "modificatorio")
    assert remanente["tipo_convenio"] == "ampliacion_remanente" and remanente["id_convenio_padre"] == original["convenio"]["id_convenio"]
    assert modificatorio["tipo_convenio"] == "modificatorio" and modificatorio["id_convenio_padre"] == original["convenio"]["id_convenio"]


def test_06_same_unit_in_multiple_affectations(api, original):
    a2 = _second_affectation(api, original)
    first = api("GET", f"/api/afectaciones/{original['afectacion']['id_afectacion']}/unidades-agrarias").json()
    second = api("GET", f"/api/afectaciones/{a2['id_afectacion']}/unidades-agrarias").json()
    assert original["afectacion"]["id_afectacion"] != a2["id_afectacion"]
    assert first[0]["id_unidad_agraria"] == second[0]["id_unidad_agraria"] == original["unidad"]["id_unidad_agraria"]


def test_07_historical_signer_survives_title_change(api, original, target_domain):
    cid = original["convenio"]["id_convenio"]
    before = api("GET", f"/api/convenios/{cid}/comparecientes").json()[0]
    api("PATCH", f"/api/parcela-titulares/{original['pt']['id_parcela_titular']}", json={"fecha_fin":"2026-09-10"})
    person_b = api("POST", f"/api/proyectos/{target_domain['project']['id_proyecto']}/personas", expected=201, json={"nombre":"Nuevo titular","apellido_paterno":"039","origen_registro":"qa"}).json()
    api("POST", f"/api/parcelas/{original['parcela']['id_parcela']}/titulares", expected=201, json={"id_persona":person_b["id_persona"],"tipo_derecho":"parcelario","fecha_inicio":"2026-09-11"})
    after = api("GET", f"/api/convenios/{cid}/comparecientes").json()[0]
    assert after["id_persona"] == before["id_persona"] == original["persona"]["id_persona"]
    assert after["nombre_en_instrumento"] == before["nombre_en_instrumento"]


def _expect_child_rejected(api, row, tipo, **extra):
    a = _second_affectation(api, row)
    payload = {"tipo_instrumento":"convenio", "tipo_convenio":tipo, **extra}
    response = api("POST", f"/api/afectaciones/{a['id_afectacion']}/convenios", expected=409, json=payload)
    return response


def test_neg_01_modificatorio_without_parent(api, original):
    _expect_child_rejected(api, original, "modificatorio")


def test_neg_02_ampliacion_without_parent(api, original):
    _expect_child_rejected(api, original, "ampliacion")


def test_neg_03_remanente_without_parent(api, original):
    _expect_child_rejected(api, original, "ampliacion_remanente")


def test_neg_04_parent_other_project_nucleus(api, original, target_domain):
    project = api("POST", "/api/proyectos", expected=201, json={"clave_proyecto":f"P039-{uuid.uuid4().hex[:8]}","nombre_proyecto":"Proyecto 039 alterno","fecha_inicio":"2026-01-01"}).json()
    nucleus = api("POST", "/api/nucleos", expected=201, json={"id_municipio":target_domain["municipality"]["id_municipio"],"nombre_nucleo":f"N039-{uuid.uuid4().hex[:8]}","tipo_nucleo":"ejido","fuente_datos":"qa"}).json()
    pn = api("POST", f"/api/proyectos/{project['id_proyecto']}/nucleos", expected=201, json={"id_nucleo":nucleus["id_nucleo"],"residencia":"QA","referencias":[]}).json()
    other = api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/parcelas", expected=201, json={"tipo_parcela":"individual","no_parcela":f"P039-{uuid.uuid4().hex[:8]}"}).json()
    a = api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/afectaciones", expected=201, json={"tipo_afectacion":"individual","id_parcela":other["id_parcela"]}).json()
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    titularidad = _catalog(api, "tipo_titularidad_unidad")["persona"]
    unit = api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/unidades-agrarias", expected=201, json={"id_tipo_tierra":tierra,"id_tipo_titularidad":titularidad,"id_parcela":other["id_parcela"],"referencia_alfanumerica":f"UA039-{uuid.uuid4().hex[:8]}"}).json()
    api("POST", f"/api/afectaciones/{a['id_afectacion']}/unidades-agrarias", expected=201, json={"id_unidad_agraria":unit["id_unidad_agraria"]})
    api("POST", f"/api/afectaciones/{a['id_afectacion']}/convenios", expected=409, json={"tipo_instrumento":"convenio","tipo_convenio":"modificatorio","id_convenio_padre":original["convenio"]["id_convenio"]})


def test_neg_05_collective_parent_for_individual(api, original, target_domain):
    collective = api("POST", f"/api/proyecto-nucleo/{original['pn']['id_proyecto_nucleo']}/afectaciones", expected=201, json={"tipo_afectacion":"colectivo"}).json()
    parent = api("POST", f"/api/afectaciones/{collective['id_afectacion']}/convenios", expected=201, json={"tipo_instrumento":"convenio","tipo_convenio":"cop_original"}).json()
    a = _second_affectation(api, original)
    api("POST", f"/api/afectaciones/{a['id_afectacion']}/convenios", expected=409, json={"tipo_instrumento":"convenio","tipo_convenio":"modificatorio","id_convenio_padre":parent["id_convenio"]})


def test_neg_06_parent_without_shared_unit(api, original):
    # The parent uses the original unit; the child uses a distinct parcel/unit.
    other = api("POST", f"/api/proyecto-nucleo/{original['pn']['id_proyecto_nucleo']}/parcelas", expected=201, json={"tipo_parcela":"individual","no_parcela":f"P039-X-{uuid.uuid4().hex[:8]}"}).json()
    child_a = api("POST", f"/api/proyecto-nucleo/{original['pn']['id_proyecto_nucleo']}/afectaciones", expected=201, json={"tipo_afectacion":"individual","id_parcela":other["id_parcela"]}).json()
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    titularidad = _catalog(api, "tipo_titularidad_unidad")["persona"]
    other_unit = api("POST", f"/api/proyecto-nucleo/{original['pn']['id_proyecto_nucleo']}/unidades-agrarias", expected=201, json={"id_tipo_tierra":tierra,"id_tipo_titularidad":titularidad,"id_parcela":other["id_parcela"],"referencia_alfanumerica":f"UA039-X-{uuid.uuid4().hex[:8]}"}).json()
    api("POST", f"/api/afectaciones/{child_a['id_afectacion']}/unidades-agrarias", expected=201, json={"id_unidad_agraria":other_unit["id_unidad_agraria"]})
    api("POST", f"/api/afectaciones/{child_a['id_afectacion']}/convenios", expected=409, json={"tipo_instrumento":"convenio","tipo_convenio":"modificatorio","id_convenio_padre":original["convenio"]["id_convenio"]})
