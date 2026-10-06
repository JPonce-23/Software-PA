"""Person discovery with real project permissions and rollback-contained writes."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import event, func, text

from app import auth, models
from app.main import app
from app.services.access import person_project_ids, require_person_access
from app.services.common import mark_inactive, set_audit_context
from .conftest import unique
from .test_excel_closure_002 import _isolated_pn
from .test_person_project_access import _link_request
from .test_project_user_assignments import _assign, _remove
from .test_user_administration import _create_user


@pytest.fixture(scope="module")
def search_users(transactional_api):
    # Synthetic users stay inside the existing outer rollback. No admin login
    # credentials are invented, and authentication alone is dependency-injected.
    api = transactional_api["request"]
    records = {name: _create_user(api, role=role)[0] for name, role in (
        ("operator", "operador"), ("other", "operador"),
        ("viewer", "visualizador"), ("geographer", "geografo"),
    )}
    users = {}
    with transactional_api["session_factory"]() as db:
        for name, record in records.items():
            user = db.get(models.Usuario, record["id_usuario"])
            db.expunge(user)
            users[name] = user
    return users


@pytest.fixture
def search(transactional_api, transactional_target_domain, search_users):
    savepoint = transactional_api["connection"].begin_nested()
    api = transactional_api["request"]
    project, pn = _isolated_pn(api, transactional_target_domain)
    for user in search_users.values():
        _assign(api, project["id_proyecto"], user.id_usuario)
    context = SimpleNamespace(
        api=api, users=search_users, project=project, pn=pn,
        admin=app.dependency_overrides[auth.get_current_user](),
        factory=transactional_api["session_factory"],
        connection=transactional_api["connection"],
        domain=transactional_target_domain, marker=unique("PS"),
    )
    try:
        yield context
    finally:
        savepoint.rollback()


def _request_as(search, user, method, path, **kwargs):
    previous = app.dependency_overrides[auth.get_current_user]
    app.dependency_overrides[auth.get_current_user] = lambda: user
    try:
        return search.api(method, path, **kwargs)
    finally:
        app.dependency_overrides[auth.get_current_user] = previous


def _person(search, *, owner=None, project=None, **values):
    return _request_as(
        search, owner or search.admin, "POST",
        f"/api/proyectos/{(project or search.project)['id_proyecto']}/personas",
        expected=201, json={"nombre": search.marker, **values},
    ).json()


def _link(search, person, *, pn=None, kind="parcel"):
    path, payload, model = _link_request(search.api, pn or search.pn,
                                         person["id_persona"], kind)
    return path, payload, model, search.api("POST", path, expected=201, json=payload).json()


def _find(search, *, user=None, **params):
    if not any(key in params for key in ("q", "curp", "rfc")):
        params["q"] = search.marker
    return _request_as(search, user or search.admin, "GET", "/api/personas", params=params).json()


def _inactive(search, model, record_id):
    with search.factory() as db:
        set_audit_context(db, search.admin.id_usuario)
        mark_inactive(db.get(model, record_id), search.admin.id_usuario, "Baja temporal B-01")
        db.commit()


def _ids(rows):
    return [row["id_persona"] for row in rows]


@pytest.mark.parametrize("params", [
    {}, {"q": ""}, {"q": "  "}, {"q": "\t\t"}, {"q": " x "},
    {"q": "x" * 301}, {"curp": ""}, {"curp": "  "}, {"curp": "x" * 19},
    {"rfc": ""}, {"rfc": "  "}, {"rfc": "x" * 14},
    {"q": "Ana", "curp": "CURP"}, {"q": "Ana", "rfc": "RFC"},
    {"curp": "CURP", "rfc": "RFC"}, {"q": "Ana", "curp": "CURP", "rfc": "RFC"},
    {"q": "Ana", "limit": 0}, {"q": "Ana", "limit": 101},
    {"q": "Ana", "skip": -1},
])
def test_validation(search, params):
    search.api("GET", "/api/personas", expected=422, params=params)


def test_admin_scope_and_minimal_projection(search):
    related = _person(search, telefono="555123", correo_electronico="persona@qa.local")
    _link(search, related)
    orphan = _person(search)
    inactive_project = _person(search)
    other_project, other_pn = _isolated_pn(search.api, search.domain)
    _link(search, inactive_project, pn=other_pn)
    _inactive(search, models.Proyecto, other_project["id_proyecto"])
    inactive_person = _person(search)
    _inactive(search, models.Persona, inactive_person["id_persona"])
    rows = _find(search)
    assert set(_ids(rows)) == {related["id_persona"], orphan["id_persona"],
                               inactive_project["id_persona"]}
    assert all(set(row) == {"id_persona", "nombre", "apellido_paterno",
                           "apellido_materno", "curp", "rfc"} for row in rows)
    assert _find(search, user=search.users["operator"], curp="NOEXISTE") == []


@pytest.mark.parametrize("kind", ["parcel", "orv", "unit", "unit_indirect", "agreement", "fifonafe", "payment"])
def test_all_relationship_paths_and_read_access_equivalence(search, kind):
    person = _person(search)
    _link(search, person, kind=kind)
    for user in (search.admin, *search.users.values()):
        rows = _find(search, user=user)
        assert _ids(rows) == [person["id_persona"]]
        with search.factory() as db:
            assert search.project["id_proyecto"] in person_project_ids(db, person["id_persona"])
            assert require_person_access(db, user, person["id_persona"]).id_persona == person["id_persona"]
    for user in search.users.values():
        _remove(search.api, search.project["id_proyecto"], user.id_usuario)
        assert _find(search, user=user) == []
        with search.factory() as db:
            with pytest.raises(HTTPException) as denied:
                require_person_access(db, user, person["id_persona"])
            assert denied.value.status_code == 403


def test_hidden_person_exact_identifiers_do_not_reveal_existence(search):
    other_project, other_pn = _isolated_pn(search.api, search.domain)
    hidden = _person(search, project=other_project, curp=search.marker, rfc=search.marker)
    _link(search, hidden, pn=other_pn)
    for user in search.users.values():
        for criterion in ({"q": search.marker}, {"curp": search.marker}, {"rfc": search.marker}):
            response = _request_as(search, user, "GET", "/api/personas", params=criterion)
            assert response.status_code == 200
            assert response.text == "[]"
    response = _request_as(search, search.users["operator"], "POST",
                           f"/api/proyectos/{search.project['id_proyecto']}/personas",
                           expected=409, json={"nombre": "Otro nombre", "curp": search.marker.lower()})
    assert response.json() == {"detail": "La persona ya existe"}


def test_multi_project_duplicates_and_authorization_before_limit(search):
    hidden = _person(search, apellido_paterno="A")
    other_project, other_pn = _isolated_pn(search.api, search.domain)
    _link(search, hidden, pn=other_pn)
    visible = _person(search, apellido_paterno="Z")
    _link(search, visible)
    _link(search, visible, kind="orv")
    _link(search, visible, pn=other_pn)
    user = search.users["operator"]
    assert _ids(_find(search, user=user, limit=1)) == [visible["id_persona"]]
    _assign(search.api, other_project["id_proyecto"], user.id_usuario)
    assert _ids(_find(search, user=user)) == [hidden["id_persona"], visible["id_persona"]]
    _request_as(search, user, "PATCH", f"/api/personas/{visible['id_persona']}",
                json={"telefono": "Actualización autorizada"})
    _remove(search.api, other_project["id_proyecto"], user.id_usuario)
    _request_as(search, user, "PATCH", f"/api/personas/{visible['id_persona']}",
                expected=403, json={"nombre": "Edición compartida no permitida"})


def test_shared_nucleus_derives_all_active_project_nucleus_links(search):
    other_project, _ = _isolated_pn(search.api, search.domain)
    search.api("POST", f"/api/proyectos/{other_project['id_proyecto']}/nucleos",
               expected=201, json={"id_nucleo": search.pn["id_nucleo"]})
    person = _person(search)
    _link(search, person)
    user = search.users["operator"]
    _remove(search.api, search.project["id_proyecto"], user.id_usuario)
    _assign(search.api, other_project["id_proyecto"], user.id_usuario)
    assert _ids(_find(search, user=user)) == [person["id_persona"]]


def test_true_orphan_creator_policy_and_no_implicit_project(search):
    user = search.users["operator"]
    own = _person(search, owner=user)
    other = _person(search, owner=search.users["other"])
    admin_orphan = _person(search)
    with search.factory() as db:
        assert person_project_ids(db, own["id_persona"]) == set()
    assert _ids(_find(search, user=user)) == [own["id_persona"]]
    assert _ids(_find(search, user=search.users["other"])) == [other["id_persona"]]
    assert set(_ids(_find(search))) == {own["id_persona"], other["id_persona"], admin_orphan["id_persona"]}
    _remove(search.api, search.project["id_proyecto"], user.id_usuario)
    assert _find(search, user=user) == []
    with search.factory() as db:
        with pytest.raises(HTTPException) as denied:
            require_person_access(db, user, own["id_persona"])
        assert denied.value.status_code == 403


def test_inactive_project_keeps_shared_edit_scope_and_does_not_grant_creator_access(search):
    user = search.users["operator"]
    other_project, other_pn = _isolated_pn(search.api, search.domain)
    _assign(search.api, other_project["id_proyecto"], user.id_usuario)
    only_inactive = _person(search, owner=user)
    _link(search, only_inactive)
    shared = _person(search, owner=user)
    _link(search, shared)
    _link(search, shared, pn=other_pn)
    orphan = _person(search, owner=user)
    _inactive(search, models.Proyecto, search.project["id_proyecto"])
    assert _ids(_find(search, user=user)) == [shared["id_persona"], orphan["id_persona"]]
    with search.factory() as db:
        assert person_project_ids(db, only_inactive["id_persona"]) == {search.project["id_proyecto"]}
        with pytest.raises(HTTPException) as denied:
            require_person_access(db, user, only_inactive["id_persona"])
        assert denied.value.status_code == 403
    _request_as(search, user, "PATCH", f"/api/personas/{shared['id_persona']}",
                expected=403, json={"nombre": "Proyecto inactivo no habilita edición"})
    # A real orphan is still available through any current authorized project,
    # without a persistent link to the original POST's project.
    _request_as(search, user, "PATCH", f"/api/personas/{orphan['id_persona']}",
                json={"telefono": "555001"})
    _remove(search.api, other_project["id_proyecto"], user.id_usuario)
    assert _find(search, user=user) == []


@pytest.mark.parametrize("parent", ["project", "pn", "nucleus", "parcel", "relation"])
def test_inactive_parent_and_relation_preserve_creator_policy(search, parent):
    user = search.users["operator"]
    person = _person(search, owner=user)
    _, _, _, holder = _link(search, person)
    model, record_id = {
        "project": (models.Proyecto, search.project["id_proyecto"]),
        "pn": (models.ProyectoNucleo, search.pn["id_proyecto_nucleo"]),
        "nucleus": (models.NucleoAgrario, search.pn["id_nucleo"]),
        "parcel": (models.Parcela, holder["id_parcela"]),
        "relation": (models.ParcelaTitular, holder["id_parcela_titular"]),
    }[parent]
    _inactive(search, model, record_id)
    with search.factory() as db:
        has_relations = db.execute(text("SELECT fn_persona_tiene_relaciones_activas(:id)"),
                                   {"id": person["id_persona"]}).scalar_one()
        assert has_relations == (parent != "relation")
    # Only deactivating the actual business reference produces a true orphan.
    assert _ids(_find(search, user=user)) == ([person["id_persona"]] if parent == "relation" else [])
    assert _ids(_find(search)) == [person["id_persona"]]


@pytest.mark.parametrize("role", ["viewer", "geographer"])
def test_read_roles_cannot_search_orphans_or_capture(search, role):
    user = search.users[role]
    related = _person(search)
    _link(search, related)
    own_orphan = _person(search)
    with search.factory() as db:
        set_audit_context(db, search.admin.id_usuario)
        db.get(models.Persona, own_orphan["id_persona"]).creado_por = user.id_usuario
        db.commit()
    _person(search, owner=search.users["operator"])
    assert _ids(_find(search, user=user)) == [related["id_persona"]]
    _request_as(search, user, "POST", f"/api/proyectos/{search.project['id_proyecto']}/personas",
                expected=403, json={"nombre": "Captura prohibida"})
    _request_as(search, user, "PATCH", f"/api/personas/{related['id_persona']}",
                expected=403, json={"nombre": "Edición prohibida"})
    path, payload, _ = _link_request(search.api, search.pn, related["id_persona"], "parcel")
    _request_as(search, user, "POST", path, expected=403, json=payload)


def test_inactive_person_is_hidden_for_every_role(search):
    person = _person(search, owner=search.users["operator"], curp=search.marker, rfc=search.marker)
    _inactive(search, models.Persona, person["id_persona"])
    for user in (search.admin, *search.users.values()):
        for params in ({"q": search.marker}, {"curp": search.marker}, {"rfc": search.marker}):
            assert _find(search, user=user, **params) == []


@pytest.mark.parametrize("field,max_length", [("curp", 18), ("rfc", 13)])
def test_exact_normalized_identifiers_without_normalizing_writes(search, field, max_length):
    value = (search.marker + "ABCDE")[:max_length]
    person = _person(search, **{field: value.lower()})
    _link(search, person)
    user = search.users["operator"]
    assert _ids(_find(search, user=user, **{field: f"  {value.upper()}  "})) == [person["id_persona"]]
    assert _find(search, user=user, **{field: value[:-1]}) == []
    assert _find(search, **{field: "NOEXISTE"}) == []
    assert _person(search)[field] is None
    with search.factory() as db:
        assert getattr(db.get(models.Persona, person["id_persona"]), field) == value.lower()
    _request_as(search, user, "PATCH", f"/api/personas/{person['id_persona']}",
                json={field: value.lower()})
    with search.factory() as db:
        assert getattr(db.get(models.Persona, person["id_persona"]), field) == value.lower()


@pytest.mark.parametrize("field", ["curp", "rfc"])
def test_multiple_normalized_identifier_matches(search, field):
    value = search.marker[:10]
    first = _person(search, **{field: value.lower()})
    second = _person(search, **{field: f" {value.upper()} "})
    for person in (first, second):
        _link(search, person)
    assert _ids(_find(search, user=search.users["operator"], **{field: value})) == [first["id_persona"], second["id_persona"]]
    if field == "rfc":
        third = _person(search, rfc=value.lower())
        _link(search, third)
        assert _ids(_find(search, rfc=value)) == [first["id_persona"], second["id_persona"], third["id_persona"]]


@pytest.mark.parametrize("term", ["jUaN", "pÉrEz", "LÓPEZ", "juan pérez", "López JUAN", "Pérez López Juan"])
def test_name_words_case_order_and_accents(search, term):
    person = _person(search, nombre=f"{search.marker} Juan", apellido_paterno="Pérez", apellido_materno="López")
    assert _ids(_find(search, q=f"  {search.marker} {term}  ")) == [person["id_persona"]]
    assert _find(search, q=f"{search.marker} PEREZ") == []


def test_name_with_null_surnames(search):
    person = _person(search)
    assert _ids(_find(search, q=search.marker)) == [person["id_persona"]]


@pytest.mark.parametrize("literal", ["%", "_", "\\", "%_\\"])
def test_like_metacharacters_are_literals(search, literal):
    person = _person(search, nombre=f"{search.marker}{literal}Fin")
    _person(search, nombre=f"{search.marker}XFin")
    assert _ids(_find(search, q=f"{search.marker}{literal}")) == [person["id_persona"]]


def test_sql_looking_name_input_remains_a_bound_search_value(search):
    _person(search)
    assert _find(search, q=f"{search.marker}' OR 1=1 --") == []
    assert len(_find(search)) == 1


def test_pagination_defaults_maximum_stable_order_and_single_query(search):
    people = [_person(search, nombre=f"{search.marker} {index:02}",
                      apellido_paterno=("alfa" if index < 2 else "Beta" if index < 23 else None),
                      apellido_materno=("uno" if index % 2 else None)) for index in range(25)]
    # Tie all display fields of the first two; id_persona must break the tie.
    for person in people[:2]:
        search.api("PATCH", f"/api/personas/{person['id_persona']}", json={
            "nombre": search.marker, "apellido_materno": "uno"})
    all_rows = _find(search, limit=100)
    assert len(all_rows) == 25
    assert _ids(all_rows[:2]) == _ids(people[:2])
    assert all_rows[-1]["apellido_paterno"] is None
    assert len(_find(search)) == 20
    assert _find(search, limit=3, skip=2) == all_rows[2:5]
    assert _find(search, skip=25) == []
    for person in people:
        _link(search, person)
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(search.connection, "before_cursor_execute", record)
    try:
        assert _find(search, user=search.users["operator"], limit=100) == all_rows
    finally:
        event.remove(search.connection, "before_cursor_execute", record)
    selects = [statement for statement in statements if statement.lstrip().upper().startswith("SELECT")]
    assert len(selects) == 1


def test_reuse_existing_person_in_actual_authorized_relation(search):
    user = search.users["operator"]
    other_project, other_pn = _isolated_pn(search.api, search.domain)
    _assign(search.api, other_project["id_proyecto"], user.id_usuario)
    person = _person(search, project=other_project)
    _link(search, person, pn=other_pn)
    row, = _find(search, user=user)
    with search.factory() as db:
        count_before = db.query(func.count(models.Persona.id_persona)).scalar()
    path, payload, model = _link_request(search.api, search.pn, row["id_persona"], "parcel")
    result = _request_as(search, user, "POST", path, expected=201, json=payload).json()
    with search.factory() as db:
        assert db.query(func.count(models.Persona.id_persona)).scalar() == count_before
        assert db.get(model, result["id_parcela_titular"]).id_persona == person["id_persona"]
        assert person_project_ids(db, person["id_persona"]) == {
            search.project["id_proyecto"], other_project["id_proyecto"]}
    assert _ids(_find(search, user=user)) == [person["id_persona"]]


def test_revocation_after_search_prevents_reuse(search):
    person = _person(search)
    _link(search, person)
    user = search.users["operator"]
    assert _ids(_find(search, user=user)) == [person["id_persona"]]
    other_project, other_pn = _isolated_pn(search.api, search.domain)
    _assign(search.api, other_project["id_proyecto"], user.id_usuario)
    _remove(search.api, search.project["id_proyecto"], user.id_usuario)
    path, payload, model = _link_request(search.api, other_pn, person["id_persona"], "parcel")
    with search.factory() as db:
        before = db.query(model).count()
    _request_as(search, user, "POST", path, expected=403, json=payload)
    with search.factory() as db:
        assert db.query(model).count() == before


def test_search_authentication_required(search):
    previous = app.dependency_overrides.pop(auth.get_current_user)
    try:
        search.api("GET", "/api/personas", expected=401, params={"q": search.marker})
    finally:
        app.dependency_overrides[auth.get_current_user] = previous
