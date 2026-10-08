"""ORV administrative history through real authorization and rollback fixtures."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app import auth, models, schemas
from app.main import app
from app.services.access import person_project_ids
from app.services.common import mark_inactive, set_audit_context
from .conftest import unique
from .test_excel_closure_002 import _isolated_pn
from .test_project_user_assignments import _assign, _remove
from .test_user_administration import _create_user


COMBINATIONS = [(False, False), (True, False), (False, True), (True, True)]
SLOTS = [
    ("comisariado", "presidente", "propietario"),
    ("comisariado", "secretario", "propietario"),
    ("comisariado", "tesorero", "propietario"),
    ("consejo_vigilancia", "presidente", "propietario"),
    ("consejo_vigilancia", "secretario_1", "propietario"),
    ("consejo_vigilancia", "secretario_2", "propietario"),
    ("comisariado", "presidente", "suplente"),
    ("comisariado", "secretario", "suplente"),
    ("comisariado", "tesorero", "suplente"),
]


@pytest.fixture(scope="module")
def history_resources(transactional_api):
    api = transactional_api["request"]
    catalogs = {
        kind: {row["codigo"]: row["id_catalogo_opcion"]
               for row in api("GET", f"/api/catalogos/operativos/{kind}").json()}
        for kind in ("organo_orv", "cargo_orv", "calidad_integrante_orv",
                     "tipo_fin_orv_integrante")
    }
    users = {}
    for role in ("operador", "visualizador", "geografo"):
        record, _ = _create_user(api, role=role)
        with transactional_api["session_factory"]() as db:
            user = db.get(models.Usuario, record["id_usuario"])
            db.expunge(user)
            users[role] = user
    return catalogs, users


@pytest.fixture
def history(transactional_api, transactional_target_domain, history_resources):
    # Every API commit is a savepoint inside the existing outer transaction.
    # This savepoint also isolates cases from one another, including 409 rollback.
    savepoint = transactional_api["connection"].begin_nested()
    try:
        api = transactional_api["request"]
        project, pn = _isolated_pn(api, transactional_target_domain)
        catalogs, users = history_resources
        for user in users.values():
            _assign(api, project["id_proyecto"], user.id_usuario)
        marker = unique("ORV-B02")
        orv = api("POST", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/orv",
                  expected=201, json={"numero_orv": marker}).json()
        today = date.today()
        assert transactional_api["connection"].execute(
            text("SELECT CURRENT_DATE")
        ).scalar_one() == today
        yield SimpleNamespace(
            api=api, project=project, pn=pn, orv=orv, catalogs=catalogs, users=users,
            admin=app.dependency_overrides[auth.get_current_user](),
            factory=transactional_api["session_factory"], marker=marker,
            today=today, next_slot=0,
        )
    finally:
        savepoint.rollback()


def _as(history, user, method, path, **kwargs):
    previous = app.dependency_overrides[auth.get_current_user]
    app.dependency_overrides[auth.get_current_user] = lambda: user
    try:
        return history.api(method, path, **kwargs)
    finally:
        app.dependency_overrides[auth.get_current_user] = previous


def _list(history, *, user=None, **params):
    return _as(history, user or history.admin, "GET",
               f"/api/orv/{history.orv['id_orv']}/integrantes", params=params).json()


def _add(history, key, *, start=None, end=None, inactive=False, slot=None):
    if slot is None:
        slot = history.next_slot
        history.next_slot += 1
    organ, position, quality = SLOTS[slot]
    person = history.api(
        "POST", f"/api/proyectos/{history.project['id_proyecto']}/personas",
        expected=201, json={"nombre": f"{history.marker} {key}"},
    ).json()
    member = history.api(
        "POST", f"/api/orv/{history.orv['id_orv']}/integrantes", expected=201,
        json={"id_persona": person["id_persona"],
              "id_organo": history.catalogs["organo_orv"][organ],
              "id_cargo": history.catalogs["cargo_orv"][position],
              "id_calidad": history.catalogs["calidad_integrante_orv"][quality],
              "fecha_inicio": start.isoformat() if start else None},
    ).json()
    if end is not None:
        member = history.api(
            "POST", f"/api/orv-integrantes/{member['id_orv_integrante']}/finalizar",
            json={"fecha_fin": end.isoformat(),
                  "id_tipo_fin": history.catalogs["tipo_fin_orv_integrante"]["termino_periodo"],
                  "detalle_fin": f"Cierre {key}"},
        ).json()
    if inactive:
        history.api("DELETE", f"/api/orv-integrantes/{member['id_orv_integrante']}",
                    json={"motivo": f"Baja {key}"})
    return {**member, "nombre": person["nombre"]}


@pytest.fixture
def population(history):
    today = history.today
    periods = {
        "current": (today - timedelta(days=30), None, False),
        "future_start": (today + timedelta(days=30), None, False),
        "past_end": (today - timedelta(days=90), today - timedelta(days=1), False),
        "future_end": (today - timedelta(days=30), today + timedelta(days=30), False),
        "today_end": (today - timedelta(days=30), today, False),
        "baja_open": (today + timedelta(days=30), None, True),
        "baja_past": (today - timedelta(days=90), today - timedelta(days=1), True),
        "baja_future": (today + timedelta(days=30), today + timedelta(days=60), True),
        "inactive_person": (today - timedelta(days=90), today - timedelta(days=1), True),
    }
    rows = {key: _add(history, key, start=start, end=end, inactive=inactive)
            for key, (start, end, inactive) in periods.items()}
    history.api("DELETE", f"/api/personas/{rows['inactive_person']['id_persona']}",
                json={"motivo": "Persona dada de baja para B-02"})
    return rows


def _ids(rows):
    return {row["id_orv_integrante"] for row in rows}


def _expected(population, include_history, include_deactivated):
    keys = {"current", "future_end", "today_end"}
    if include_history:
        keys |= {"future_start", "past_end"}
    if include_deactivated:
        keys |= {"baja_open", "baja_past", "baja_future"}
    return {population[key]["id_orv_integrante"] for key in keys}


@pytest.mark.parametrize("include_history,include_deactivated", COMBINATIONS)
def test_four_combinations_exact_ids_order_and_validity(history, population, include_history, include_deactivated):
    rows = _list(history, incluir_historico=include_history, incluir_bajas=include_deactivated)
    assert _ids(rows) == _expected(population, include_history, include_deactivated)
    assert len(rows) == len(_ids(rows))
    assert rows == sorted(rows, key=lambda row: (row["id_organo"], row["id_cargo"], row["nombre"]))
    by_id = {row["id_orv_integrante"]: row for row in rows}
    for key, member in population.items():
        if member["id_orv_integrante"] in by_id:
            assert by_id[member["id_orv_integrante"]]["vigente"] == (
                key in {"current", "future_end", "today_end"}
            )


@pytest.mark.parametrize("params,include_history", [({}, False),
                         ({"incluir_historico": False}, False),
                         ({"incluir_historico": True}, True)])
def test_old_calls_and_explicit_false_keep_same_results(history, population, params, include_history):
    original_call = _list(history, **params)
    assert _ids(original_call) == _expected(population, include_history, False)
    assert original_call == _list(history, **params, incluir_bajas=False)


@pytest.mark.parametrize("key", ["baja_open", "baja_past", "baja_future"])
def test_deactivated_response_preserves_period_and_existing_schema(history, population, key):
    row = next(row for row in _list(history, incluir_bajas=True)
               if row["id_orv_integrante"] == population[key]["id_orv_integrante"])
    assert set(row) == set(schemas.OrvIntegranteDetailResponse.model_fields)
    assert row["activo"] is False and row["vigente"] is False
    assert row["fecha_baja"] is not None
    assert row["motivo_baja"] == f"Baja {key}"
    assert row["id_usuario_baja"] == history.admin.id_usuario
    for field in ("id_persona", "fecha_inicio", "fecha_fin", "id_tipo_fin", "detalle_fin"):
        assert row[field] == population[key][field]


@pytest.mark.parametrize("role", ["admin", "operador", "visualizador", "geografo"])
def test_all_read_roles_see_bajas_but_not_inactive_people(history, population, role):
    user = history.admin if role == "admin" else history.users[role]
    for include_history, include_deactivated in COMBINATIONS:
        rows = _list(history, user=user, incluir_historico=include_history,
                     incluir_bajas=include_deactivated)
        assert _ids(rows) == _expected(population, include_history, include_deactivated)
        assert population["inactive_person"]["id_orv_integrante"] not in _ids(rows)
    if role != "admin":
        member_id = population["baja_past"]["id_orv_integrante"]
        _as(history, user, "POST", f"/api/orv-integrantes/{member_id}/reactivar", expected=403)
        _as(history, user, "DELETE", f"/api/orv-integrantes/{member_id}",
            expected=403, json={"motivo": "Lectura no concede baja"})


@pytest.mark.parametrize("role", ["operador", "visualizador", "geografo"])
def test_revoked_or_unrelated_project_has_no_historical_access(history, role):
    member = _add(history, "hidden", inactive=True)
    user = history.users[role]
    assert _ids(_list(history, user=user, incluir_bajas=True)) == {member["id_orv_integrante"]}
    _remove(history.api, history.project["id_proyecto"], user.id_usuario)
    unrelated = history.api("POST", "/api/proyectos", expected=201,
                            json={"clave_proyecto": unique("B02-OTRO"),
                                  "nombre_proyecto": unique("Proyecto ajeno")}).json()
    _assign(history.api, unrelated["id_proyecto"], user.id_usuario)
    for include_history, include_deactivated in COMBINATIONS:
        response = _as(history, user, "GET", f"/api/orv/{history.orv['id_orv']}/integrantes",
                       expected=403, params={"incluir_historico": include_history,
                                             "incluir_bajas": include_deactivated})
        assert response.json() == {"detail": "Proyecto fuera del alcance autorizado"}


@pytest.mark.parametrize("parent,expected", [("orv", 404), ("nucleus", 404),
                                             ("pn", 403), ("project", 403)])
def test_inactive_parents_keep_existing_access_rules(history, parent, expected):
    member = _add(history, "parent", inactive=True)
    model, record_id = {
        "orv": (models.Orv, history.orv["id_orv"]),
        "nucleus": (models.NucleoAgrario, history.pn["id_nucleo"]),
        "pn": (models.ProyectoNucleo, history.pn["id_proyecto_nucleo"]),
        "project": (models.Proyecto, history.project["id_proyecto"]),
    }[parent]
    with history.factory() as db:
        set_audit_context(db, history.admin.id_usuario)
        mark_inactive(db.get(model, record_id), history.admin.id_usuario, "Padre inactivo B-02")
        db.commit()
    for user in history.users.values():
        _as(history, user, "GET", f"/api/orv/{history.orv['id_orv']}/integrantes",
            expected=expected, params={"incluir_historico": True, "incluir_bajas": True})
    if parent in {"orv", "nucleus"}:
        history.api("GET", f"/api/orv/{history.orv['id_orv']}/integrantes", expected=404,
                    params={"incluir_bajas": True})
    else:
        assert _ids(_list(history, incluir_bajas=True)) == {member["id_orv_integrante"]}


def test_locate_and_reactivate_keeps_functional_finish(history):
    member = _add(history, "restore", start=history.today - timedelta(days=90),
                  end=history.today - timedelta(days=1), inactive=True)
    located, = _list(history, incluir_bajas=True)
    assert located["id_orv_integrante"] == member["id_orv_integrante"]
    restored = history.api("POST", f"/api/orv-integrantes/{located['id_orv_integrante']}/reactivar").json()
    assert restored["activo"] is True and restored["vigente"] is False
    assert all(restored[field] is None for field in ("fecha_baja", "motivo_baja", "id_usuario_baja"))
    for field in ("fecha_inicio", "fecha_fin", "id_tipo_fin", "detalle_fin"):
        assert restored[field] == located[field]
    assert _list(history) == _list(history, incluir_bajas=True) == []
    assert _ids(_list(history, incluir_historico=True)) == {member["id_orv_integrante"]}
    assert _list(history, incluir_historico=True) == _list(history, incluir_historico=True, incluir_bajas=True)


def test_reactivation_overlap_rolls_back_and_preserves_baja(history):
    old = _add(history, "conflict", start=history.today - timedelta(days=90),
               end=history.today - timedelta(days=1), inactive=True, slot=0)
    _add(history, "replacement", start=history.today - timedelta(days=30), slot=0)
    before = next(row for row in _list(history, incluir_bajas=True)
                  if row["id_orv_integrante"] == old["id_orv_integrante"])
    response = history.api("POST", f"/api/orv-integrantes/{old['id_orv_integrante']}/reactivar", expected=409)
    assert "traslapa" in response.json()["detail"]
    after = next(row for row in _list(history, incluir_bajas=True)
                 if row["id_orv_integrante"] == old["id_orv_integrante"])
    assert after == before
    with history.factory() as db:
        persisted = db.get(models.OrvIntegrante, old["id_orv_integrante"])
        assert persisted.activo is False
        assert persisted.fecha_baja is not None
        assert persisted.motivo_baja == before["motivo_baja"]
        assert persisted.id_usuario_baja == before["id_usuario_baja"]


@pytest.mark.parametrize("end_offset", [None, -1, 30])
def test_already_active_reactivation_keeps_conflict_contract(history, end_offset):
    member = _add(history, "active", start=history.today - timedelta(days=90),
                  end=history.today + timedelta(days=end_offset) if end_offset is not None else None)
    before = _list(history, incluir_historico=True)
    response = history.api("POST", f"/api/orv-integrantes/{member['id_orv_integrante']}/reactivar", expected=409)
    assert response.json() == {"detail": "El integrante ORV ya está activo"}
    assert _list(history, incluir_historico=True) == before


def test_finished_active_member_still_grants_person_relationship(history):
    member = _add(history, "person-scope", start=history.today - timedelta(days=90),
                  end=history.today - timedelta(days=1))
    with history.factory() as db:
        assert person_project_ids(db, member["id_persona"]) == {history.project["id_proyecto"]}
        assert db.execute(text("SELECT fn_persona_tiene_relaciones_activas(:id)"),
                          {"id": member["id_persona"]}).scalar_one() is True
    rows = _as(history, history.users["operador"], "GET", "/api/personas",
               params={"q": member["nombre"]}).json()
    assert [row["id_persona"] for row in rows] == [member["id_persona"]]
    assert _list(history) == []
    assert _ids(_list(history, incluir_historico=True)) == {member["id_orv_integrante"]}


def test_parent_functional_expiration_does_not_change_member_validity(history):
    member = _add(history, "current", start=history.today - timedelta(days=30))
    parent = history.api("PATCH", f"/api/orv/{history.orv['id_orv']}", json={
        "inicio_vigencia": (history.today - timedelta(days=100)).isoformat(),
        "fin_vigencia": (history.today - timedelta(days=1)).isoformat(),
    }).json()
    assert parent["activo"] is True and parent["vigente"] is False
    row, = _list(history)
    assert row["id_orv_integrante"] == member["id_orv_integrante"]
    assert row["vigente"] is True


@pytest.mark.parametrize("include_history,include_deactivated", COMBINATIONS)
def test_empty_list(history, include_history, include_deactivated):
    assert _list(history, incluir_historico=include_history, incluir_bajas=include_deactivated) == []


@pytest.mark.parametrize("parameter", ["incluir_historico", "incluir_bajas"])
def test_invalid_boolean(history, parameter):
    history.api("GET", f"/api/orv/{history.orv['id_orv']}/integrantes", expected=422,
                params={parameter: "no-es-un-booleano"})


def test_authentication_and_missing_orv_contract(history):
    history.api("GET", "/api/orv/999999999/integrantes", expected=404,
                params={"incluir_bajas": True})
    previous = app.dependency_overrides.pop(auth.get_current_user)
    try:
        history.api("GET", f"/api/orv/{history.orv['id_orv']}/integrantes", expected=401,
                    params={"incluir_bajas": True})
    finally:
        app.dependency_overrides[auth.get_current_user] = previous
