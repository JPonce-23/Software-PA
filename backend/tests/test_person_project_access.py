"""Real RBAC, project scopes, shared identity writes and safe first linking."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException

from app import models, schemas
from app.database import SessionLocal
from app.services import domain
from app.services.access import person_project_ids
from .conftest import unique
from .test_excel_closure_002 import _catalog, _isolated_pn
from .test_project_user_assignments import _assign, _remove
from .test_user_administration import _create_user, _login
from .test_assignment_concurrency_regressions import _admin_session, _pause_flush
from .concurrency import PostgreSQLWorkers, wait_for_blocked_workers


def _person(api, project_id):
    return api("POST", f"/api/proyectos/{project_id}/personas", expected=201,
               json={"nombre": unique("Persona alcance")}).json()["id_persona"]


def _snapshot(person_id):
    with SessionLocal() as db:
        row = db.get(models.Persona, person_id)
        state = {c.name: getattr(row, c.name) for c in models.Persona.__table__.columns}
        audit = [(a.id_bitacora, a.accion, a.id_usuario, a.valor_anterior, a.valor_nuevo)
                 for a in db.query(models.Bitacora).filter_by(
                     entidad_tipo="persona", entidad_id=person_id
                 ).order_by(models.Bitacora.id_bitacora)]
        return state, audit


def _link_request(api, pn, person_id, kind):
    """Build actual target resources; return a POST and its persisted model."""
    pn_id = pn["id_proyecto_nucleo"]
    if kind == "orv":
        orv = api("POST", f"/api/proyecto-nucleo/{pn_id}/orv", expected=201, json={}).json()
        payload = {"id_persona": person_id, **{
            field: next(iter(_catalog(api, catalog).values())) for field, catalog in (
                ("id_organo", "organo_orv"), ("id_cargo", "cargo_orv"),
                ("id_calidad", "calidad_integrante_orv"))}}
        return f"/api/orv/{orv['id_orv']}/integrantes", payload, models.OrvIntegrante
    if kind in {"parcel", "unit_indirect"}:
        parcel = api("POST", f"/api/proyecto-nucleo/{pn_id}/parcelas", expected=201,
                     json={"tipo_parcela": "individual", "no_parcela": unique("PER")}).json()
        if kind == "parcel":
            return f"/api/parcelas/{parcel['id_parcela']}/titulares", {
                "id_persona": person_id, "tipo_derecho": "posesion"}, models.ParcelaTitular
        holder = api("POST", f"/api/parcelas/{parcel['id_parcela']}/titulares", expected=201,
                     json={"id_persona": person_id, "tipo_derecho": "posesion"}).json()
    if kind in {"unit", "unit_indirect"}:
        payload = {"id_tipo_tierra": next(iter(_catalog(api, "tipo_tierra").values())),
                   "id_tipo_titularidad": _catalog(api, "tipo_titularidad_unidad")["persona"],
                   "referencia_alfanumerica": unique("PER-UA")}
        if kind == "unit_indirect":
            payload["id_parcela"] = parcel["id_parcela"]
        unit = api("POST", f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias", expected=201,
                   json=payload).json()
        identity = {"id_persona": person_id} if kind == "unit" else {
            "id_parcela_titular": holder["id_parcela_titular"]}
        return f"/api/unidades-agrarias/{unit['id_unidad_agraria']}/titulares", identity, models.UnidadAgrariaTitular
    affectation = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201,
                      json={"tipo_afectacion": "colectivo"}).json()
    if kind == "agreement":
        agreement = api("POST", f"/api/afectaciones/{affectation['id_afectacion']}/convenios",
                        expected=201, json={"tipo_convenio": "cop_original"}).json()
        return f"/api/convenios/{agreement['id_convenio']}/comparecientes", {
            "id_persona": person_id, "nombre_en_instrumento": unique("Compareciente"),
            "id_tipo_calidad": _catalog(api, "calidad_compareciente_convenio")["beneficiario"],
            "es_firmante": False,
        }, models.ConvenioCompareciente
    if kind == "fifonafe":
        procedure = api("POST", f"/api/proyecto-nucleo/{pn_id}/fifonafe", expected=201,
                        json={"ids_afectacion": [affectation["id_afectacion"]]}).json()
        return f"/api/fifonafe/{procedure['id_tramite_fifonafe']}/intervinientes", {
            "id_persona": person_id, "rol": "beneficiario"}, models.TramiteFifonafeInterviniente
    indemnity = api("POST", f"/api/afectaciones/{affectation['id_afectacion']}/indemnizacion",
                    expected=201, json={}).json()
    return f"/api/indemnizaciones/{indemnity['id_indemnizacion']}/pagos", {
        "id_persona_beneficiaria": person_id, "fecha_pago": "2026-10-01", "monto": "1",
        "beneficiario_nombre": unique("Beneficiario")}, models.Pago


@pytest.mark.parametrize("kind", ["parcel", "orv", "unit", "unit_indirect", "agreement", "fifonafe", "payment"])
def test_person_scope_follows_every_actual_relationship_and_revocation(api, target_domain, kind):
    project, pn = _isolated_pn(api, target_domain)
    project_id = project["id_proyecto"]
    person_id = _person(api, project_id)
    path, payload, model = _link_request(api, pn, person_id, kind)
    api("POST", path, expected=201, json=payload)
    user, password = _create_user(api)
    _assign(api, project_id, user["id_usuario"])
    session, headers = _login(user["correo"], password)
    try:
        with SessionLocal() as db:
            assert person_project_ids(db, person_id) == {project_id}
        assert session.get(f"/api/personas/{person_id}").status_code == 200
        updated = session.patch(f"/api/personas/{person_id}", headers=headers,
                                json={"nombre": unique("Edición autorizada")})
        assert updated.status_code == 200, updated.text
        before = _snapshot(person_id)
        assert before[0]["nombre"] == updated.json()["nombre"]
        assert before[0]["actualizado_por"] == user["id_usuario"]
        assert before[1][-1][2] == user["id_usuario"]
        _remove(api, project_id, user["id_usuario"])
        assert session.get(f"/api/proyectos/{project_id}").status_code == 403
        assert session.get(f"/api/personas/{person_id}").status_code == 403
        assert session.patch(f"/api/personas/{person_id}", headers=headers,
                             json={"nombre": "Intento fuera del alcance"}).status_code == 403
        assert _snapshot(person_id) == before
        assert session.get(path).status_code == 403
        assert api("GET", f"/api/personas/{person_id}").status_code == 200
        api("PATCH", f"/api/personas/{person_id}", json={"nombre": unique("Admin global")})
    finally:
        session.close()


@pytest.mark.parametrize("role", ["operador", "visualizador", "geografo"])
def test_shared_person_requires_all_projects_for_global_edit_and_preserves_read_scope(api, target_domain, role):
    project, pn = _isolated_pn(api, target_domain)
    other, other_pn = _isolated_pn(api, target_domain)
    person_id = _person(api, project["id_proyecto"])
    for scope in (pn, other_pn):
        path, payload, _ = _link_request(api, scope, person_id, "parcel")
        api("POST", path, expected=201, json=payload)
    user, password = _create_user(api, role=role)
    _assign(api, project["id_proyecto"], user["id_usuario"])
    session, headers = _login(user["correo"], password)
    try:
        before = _snapshot(person_id)
        assert session.get(f"/api/personas/{person_id}").status_code == 200
        assert session.get(f"/api/proyecto-nucleo/{other_pn['id_proyecto_nucleo']}").status_code == 403
        assert session.patch(f"/api/personas/{person_id}", headers=headers,
                             json={"nombre": "Cambio global prohibido"}).status_code == 403
        assert _snapshot(person_id) == before
        _assign(api, other["id_proyecto"], user["id_usuario"])
        response = session.patch(f"/api/personas/{person_id}", headers=headers,
                                 json={"nombre": unique("Ambos proyectos")})
        assert response.status_code == (200 if role == "operador" else 403), response.text
        if role != "operador":
            assert _snapshot(person_id) == before
        _remove(api, project["id_proyecto"], user["id_usuario"])
        assert session.get(f"/api/personas/{person_id}").status_code == 200
        assert session.patch(f"/api/personas/{person_id}", headers=headers,
                             json={"nombre": "Un permiso no basta"}).status_code == 403
        _remove(api, other["id_proyecto"], user["id_usuario"])
        assert session.get(f"/api/personas/{person_id}").status_code == 403
    finally:
        session.close()


@pytest.mark.parametrize("kind", ["parcel", "orv", "unit", "unit_indirect", "agreement", "fifonafe", "payment"])
def test_other_authorized_project_cannot_link_an_out_of_scope_person(api, target_domain, kind):
    project, pn = _isolated_pn(api, target_domain)
    other, other_pn = _isolated_pn(api, target_domain)
    person_id = _person(api, project["id_proyecto"])
    path, payload, _ = _link_request(api, pn, person_id, "parcel")
    holder = api("POST", path, expected=201, json=payload).json()
    if kind == "unit_indirect":
        target_path, _, model = _link_request(api, other_pn, person_id, "unit")
        target_payload = {"id_parcela_titular": holder["id_parcela_titular"]}
        # A holder from another nucleus already violates the unit's canonical
        # scope. Preserve its existing 409; do not create a preparatory link.
    else:
        target_path, target_payload, model = _link_request(api, other_pn, person_id, kind)
    user, password = _create_user(api)
    _assign(api, other["id_proyecto"], user["id_usuario"])
    session, headers = _login(user["correo"], password)
    try:
        assert session.get(f"/api/personas/{person_id}").status_code == 403
        before = _snapshot(person_id)
        with SessionLocal() as db:
            count = db.query(model).count()
        response = session.post(target_path, headers=headers, json=target_payload)
        assert response.status_code == (409 if kind == "unit_indirect" else 403), response.text
        with SessionLocal() as db:
            assert db.query(model).count() == count
        assert _snapshot(person_id) == before
    finally:
        session.close()


def test_orphan_person_creator_policy_and_first_link_without_implicit_project(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    user, password = _create_user(api)
    _assign(api, project["id_proyecto"], user["id_usuario"])
    stranger, stranger_password = _create_user(api)
    _assign(api, project["id_proyecto"], stranger["id_usuario"])
    session, headers = _login(user["correo"], password)
    stranger_session, stranger_headers = _login(stranger["correo"], stranger_password)
    try:
        response = session.post(f"/api/proyectos/{project['id_proyecto']}/personas", headers=headers,
                                json={"nombre": unique("Persona nueva")})
        assert response.status_code == 201, response.text
        person_id = response.json()["id_persona"]
        with SessionLocal() as db:
            assert person_project_ids(db, person_id) == set()
        assert api("GET", f"/api/personas/{person_id}").status_code == 200
        api("PATCH", f"/api/personas/{person_id}", json={"telefono": "555000QA"})
        assert session.get(f"/api/personas/{person_id}").status_code == 200
        assert session.patch(f"/api/personas/{person_id}", headers=headers,
                             json={"nombre": unique("Creador captura")}).status_code == 200
        assert stranger_session.get(f"/api/personas/{person_id}").status_code == 403
        assert stranger_session.patch(f"/api/personas/{person_id}", headers=stranger_headers,
                                      json={"nombre": "No es mi persona"}).status_code == 403
        _remove(api, project["id_proyecto"], user["id_usuario"])
        assert session.get(f"/api/personas/{person_id}").status_code == 403
        assert session.patch(f"/api/personas/{person_id}", headers=headers,
                             json={"nombre": "Creador sin asignaciones"}).status_code == 403
        _assign(api, project["id_proyecto"], user["id_usuario"])
        path, payload, _ = _link_request(api, pn, person_id, "parcel")
        assert stranger_session.post(path, headers=stranger_headers, json=payload).status_code == 403
        assert session.post(path, headers=headers, json=payload).status_code == 201
        with SessionLocal() as db:
            assert person_project_ids(db, person_id) == {project["id_proyecto"]}
        _remove(api, project["id_proyecto"], user["id_usuario"])
        assert session.get(f"/api/personas/{person_id}").status_code == 403
    finally:
        session.close()
        stranger_session.close()


def test_service_update_entity_cannot_bypass_person_authorization(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    person_id = _person(api, project["id_proyecto"])
    path, payload, _ = _link_request(api, pn, person_id, "parcel")
    api("POST", path, expected=201, json=payload)
    user, _ = _create_user(api)
    before = _snapshot(person_id)
    with SessionLocal() as db:
        with pytest.raises(HTTPException) as exc:
            domain.update_entity(db, db.get(models.Persona, person_id),
                                 schemas.PersonaUpdate(nombre="Bypass prohibido"),
                                 db.get(models.Usuario, user["id_usuario"]))
        assert exc.value.status_code == 403
        db.rollback()
    assert _snapshot(person_id) == before


def test_shared_person_edit_rechecks_scope_after_concurrent_link_commits(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    other, other_pn = _isolated_pn(api, target_domain)
    person_id = _person(api, project["id_proyecto"])
    path, payload, _ = _link_request(api, pn, person_id, "parcel")
    api("POST", path, expected=201, json=payload)
    other_path, other_payload, _ = _link_request(api, other_pn, person_id, "parcel")
    user, password = _create_user(api)
    _assign(api, project["id_proyecto"], user["id_usuario"])
    operator, operator_headers = _login(user["correo"], password)
    admin, admin_headers = _admin_session()
    before = _snapshot(person_id)
    try:
        with PostgreSQLWorkers() as workers, _pause_flush(
            lambda row: isinstance(row, models.ParcelaTitular) and row.id_persona == person_id
        ) as (reached, release), ThreadPoolExecutor(max_workers=2) as pool:
            link = pool.submit(workers.run, "link", admin.post, other_path,
                               headers=admin_headers, json=other_payload)
            try:
                assert reached.wait(10)
                update = pool.submit(workers.run, "update", operator.patch,
                                     f"/api/personas/{person_id}", headers=operator_headers,
                                     json={"nombre": "Edición sin captura en el nuevo proyecto"})
                wait_for_blocked_workers(workers.wait_pids(["update"]), workers.wait_pids(["link"]))
            finally:
                release.set()
            assert link.result(15).status_code == 201
            assert update.result(15).status_code == 403
        assert _snapshot(person_id) == before
        with SessionLocal() as db:
            assert person_project_ids(db, person_id) == {project["id_proyecto"], other["id_proyecto"]}
    finally:
        operator.close()
        admin.close()


def test_inactive_project_reference_does_not_allow_shared_edit_or_creator_fallback(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    other, other_pn = _isolated_pn(api, target_domain)
    user, password = _create_user(api)
    _assign(api, project["id_proyecto"], user["id_usuario"])
    _assign(api, other["id_proyecto"], user["id_usuario"])
    session, headers = _login(user["correo"], password)
    try:
        created = session.post(f"/api/proyectos/{project['id_proyecto']}/personas", headers=headers,
                               json={"nombre": unique("Creador compartida")})
        assert created.status_code == 201
        person_id = created.json()["id_persona"]
        for scope in (pn, other_pn):
            path, payload, _ = _link_request(api, scope, person_id, "parcel")
            api("POST", path, expected=201, json=payload)
        api("DELETE", f"/api/proyectos/{other['id_proyecto']}", json={"motivo": "Proyecto inactivo QA"})
        before = _snapshot(person_id)
        assert session.get(f"/api/personas/{person_id}").status_code == 200
        assert session.patch(f"/api/personas/{person_id}", headers=headers,
                             json={"nombre": "Proyecto inactivo no equivale a captura"}).status_code == 403
        _remove(api, project["id_proyecto"], user["id_usuario"])
        assert session.get(f"/api/personas/{person_id}").status_code == 403
        assert _snapshot(person_id) == before
    finally:
        session.close()


@pytest.mark.parametrize("kind", ["agreement", "payment"])
def test_admin_invalid_person_reference_preserves_existing_conflict_contract(api, target_domain, kind):
    project, pn = _isolated_pn(api, target_domain)
    path, payload, model = _link_request(api, pn, 999999999, kind)
    with SessionLocal() as db:
        count = db.query(model).count()
        audit_count = db.query(models.Bitacora).count()
    api("POST", path, expected=409, json=payload)
    with SessionLocal() as db:
        assert db.query(model).count() == count
        assert db.query(models.Bitacora).count() == audit_count


@pytest.mark.parametrize("kind", ["unit", "payment"])
def test_reference_patch_cannot_import_an_out_of_scope_person(api, target_domain, kind):
    revoked, revoked_pn = _isolated_pn(api, target_domain)
    authorized, authorized_pn = _isolated_pn(api, target_domain)
    hidden = _person(api, revoked["id_proyecto"])
    path, payload, _ = _link_request(api, revoked_pn, hidden, "parcel")
    api("POST", path, expected=201, json=payload)
    visible = _person(api, authorized["id_proyecto"])
    path, payload, model = _link_request(api, authorized_pn, visible, kind)
    record = api("POST", path, expected=201, json=payload).json()
    if kind == "unit":
        record_id, column, patch_path = record["id_unidad_titular"], "id_persona", "/api/unidad-agraria-titulares/"
    else:
        record_id, column, patch_path = record["id_pago"], "id_persona_beneficiaria", "/api/pagos/"
    user, password = _create_user(api)
    _assign(api, authorized["id_proyecto"], user["id_usuario"])
    session, headers = _login(user["correo"], password)
    try:
        before = _snapshot(hidden)
        with SessionLocal() as db:
            audit_count = db.query(models.Bitacora).count()
        response = session.patch(patch_path + str(record_id), headers=headers, json={column: hidden})
        assert response.status_code == 403, response.text
        with SessionLocal() as db:
            assert getattr(db.get(model, record_id), column) == visible
            assert db.query(models.Bitacora).count() == audit_count
        assert _snapshot(hidden) == before
    finally:
        session.close()


def test_bulk_agreement_creation_rejects_hidden_person_without_partial_rows(api, target_domain):
    hidden_project, hidden_pn = _isolated_pn(api, target_domain)
    authorized, pn = _isolated_pn(api, target_domain)
    person_id = _person(api, hidden_project["id_proyecto"])
    path, payload, _ = _link_request(api, hidden_pn, person_id, "parcel")
    api("POST", path, expected=201, json=payload)
    affectation = api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/afectaciones",
                      expected=201, json={"tipo_afectacion": "colectivo"}).json()
    user, password = _create_user(api)
    _assign(api, authorized["id_proyecto"], user["id_usuario"])
    session, headers = _login(user["correo"], password)
    try:
        with SessionLocal() as db:
            before = [db.query(model).count() for model in (
                models.Convenio, models.ConvenioAfectacion, models.ConvenioCompareciente, models.Bitacora)]
        response = session.post(f"/api/afectaciones/{affectation['id_afectacion']}/convenios", headers=headers,
                                json={"tipo_convenio": "cop_original", "comparecientes": [{
                                    "id_persona": person_id, "nombre_en_instrumento": "Persona oculta",
                                    "id_tipo_calidad": _catalog(api, "calidad_compareciente_convenio")["beneficiario"],
                                    "es_firmante": False}]})
        assert response.status_code == 403, response.text
        with SessionLocal() as db:
            assert [db.query(model).count() for model in (
                models.Convenio, models.ConvenioAfectacion, models.ConvenioCompareciente, models.Bitacora)] == before
    finally:
        session.close()
