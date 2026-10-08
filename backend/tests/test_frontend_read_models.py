"""Additive read contracts, authorization, provenance and bounded SQL queries."""

from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy import event

from app import auth, models
from app.config import AUTH_SETTINGS
from app.main import app
from app.services.access import project_ids_for_document_target
from app.services.common import mark_inactive, set_audit_context

from tests.test_document_targets_039 import api, catalogs, domain_fixture, target_domain
from tests.test_excel_closure_002 import _isolated_pn
from tests.test_gis_history_026 import finish, reconcile
from tests.test_nucleus_gpkg_imports import gpkg, nucleus, polygon, preview, project, stage
from tests.test_parcel_gpkg_imports import attrs, link_parcel, parcel, stage as stage_parcels
from tests.test_user_administration import _create_user


@contextmanager
def sql_reads(connection):
    queries = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(("SELECT", "WITH")):
            queries.append(statement)

    event.listen(connection, "before_cursor_execute", capture)
    try:
        yield queries
    finally:
        event.remove(connection, "before_cursor_execute", capture)


def new_document(api, kind, identity):
    return api("POST", f"/api/documentos/objetivos/{kind}/{identity}", expected=201,
               json={"tipo_documento": "soporte_qa", "estado": "disponible",
                     "titulo": f"Soporte {uuid.uuid4().hex}"}).json()


def test_consolidation_all_provenances_versions_and_constant_queries(
    api, transactional_api, target_domain, domain_fixture, catalogs,
):
    pn = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    path = f"/api/proyecto-nucleo/{pn}/documentos"
    document = new_document(api, "proyecto_nucleo", pn)
    with sql_reads(transactional_api["connection"]) as few_queries:
        initial = api("GET", path).json()
    assert len(initial) == 1 and initial[0]["version_vigente"] is None
    identities = {
        "proyecto_nucleo": pn,
        "nucleo_agrario": target_domain["nucleus"]["id_nucleo"],
        "parcela_titular": domain_fixture["parcela_titular"]["id_parcela_titular"],
        "unidad_agraria": domain_fixture["unidad_agraria"]["id_unidad_agraria"],
        "unidad_agraria_titular": domain_fixture["unidad_agraria_titular"]["id_unidad_titular"],
        "afectacion_unidad_agraria": domain_fixture["afectacion_unidad_agraria"]["id_afectacion_unidad"],
        "asamblea_convocatoria": domain_fixture["asamblea_convocatoria"]["id_convocatoria"],
        "convenio_compareciente": domain_fixture["convenio_compareciente"]["id_compareciente"],
        "tramite_ran": domain_fixture["tramite_ran_pn"]["id_tramite_ran"],
        "tramite_ran_evento": domain_fixture["tramite_ran_orv_evento"]["id_evento_ran"],
        "tramite_fifonafe_evento": domain_fixture["tramite_fifonafe_evento"]["id_evento_fifonafe"],
        "expediente_requisito": domain_fixture["expediente_requisito"]["id_expediente_requisito"],
    }
    for kind, identity in identities.items():
        if kind != "proyecto_nucleo":
            api("POST", f"/api/documentos/{document['id_documento']}/vinculos/{kind}/{identity}", expected=201)
        with transactional_api["session_factory"]() as db:
            assert target_domain["project"]["id_proyecto"] in project_ids_for_document_target(db, kind, identity)
    activity = api("POST", f"/api/proyecto-nucleo/{pn}/actividades", expected=201,
                   json={"tipo_actividad": "sensibilizacion"}).json()
    identities["actividad_campo"] = activity["id_actividad"]
    api("POST", f"/api/documentos/{document['id_documento']}/vinculos/actividad_campo/{activity['id_actividad']}", expected=201)
    requirement = api("PATCH", f"/api/requisitos-documentales/{identities['expediente_requisito']}",
                      json={"id_documento": document["id_documento"]}).json()
    versions = [api("POST", f"/api/documentos/{document['id_documento']}/versiones", expected=201,
                    files={"archivo": ("soporte.pdf", f"%PDF-{i}".encode(), "application/pdf")}).json()
                for i in (1, 2)]
    with sql_reads(transactional_api["connection"]) as many_queries:
        rows = api("GET", path).json()
    # Existing project authorization eagerly loads the administrative graph;
    # the new projection still costs exactly one SQL query at any document count.
    assert len(many_queries) == len(few_queries)
    assert sum(q.startswith("WITH document_targets") for q in many_queries) == 1
    linked = [row for row in rows if row["fuente_relacion"] == "vinculo"]
    assert {(row["entidad_tipo"], row["entidad_id"]) for row in linked} == set(identities.items())
    for row in rows:
        assert row["documento"] == document
        assert row["version_vigente"] == versions[-1]
        assert row["origen"]
        assert "ruta_almacenamiento" not in row["version_vigente"]
    req_rows = [row for row in rows if row["fuente_relacion"] == "expediente_requisito"]
    assert len(req_rows) == 1
    assert req_rows[0]["entidad_tipo"] == "expediente_requisito"
    assert req_rows[0]["entidad_id"] == requirement["id_expediente_requisito"]
    assert req_rows[0]["id_documento_vinculo"] is None
    assert api("GET", f"/api/documentos/objetivos/proyecto_nucleo/{pn}").json() == [document]


def test_consolidation_never_leaks_other_pn_shared_nucleus_or_inactive_links(
    api, transactional_api, transactional_target_domain, catalogs,
):
    left, left_pn = _isolated_pn(api, transactional_target_domain)
    right = project(api)
    right_pn = api("POST", f"/api/proyectos/{right}/nucleos", expected=201,
                   json={"id_nucleo": left_pn["id_nucleo"]}).json()
    foreign = new_document(api, "proyecto_nucleo", right_pn["id_proyecto_nucleo"])
    own = new_document(api, "proyecto_nucleo", left_pn["id_proyecto_nucleo"])
    shared = new_document(api, "nucleo_agrario", left_pn["id_nucleo"])
    # A requirement in the requested PN cannot turn a foreign document into support.
    requirement_id = api("GET", "/api/catalogos/requisitos-documentales").json()[0]["id_requisito"]
    api("POST", f"/api/proyecto-nucleo/{left_pn['id_proyecto_nucleo']}/requisitos-documentales", expected=201,
        json={"entidad_tipo": "proyecto_nucleo", "entidad_id": left_pn["id_proyecto_nucleo"],
              "id_requisito": requirement_id, "id_estado": catalogs["estado_requisito"],
              "id_documento": foreign["id_documento"]})
    foreign_link = api("POST", f"/api/documentos/{own['id_documento']}/vinculos/proyecto_nucleo/{right_pn['id_proyecto_nucleo']}", expected=201).json()
    path = f"/api/proyecto-nucleo/{left_pn['id_proyecto_nucleo']}/documentos"
    rows = api("GET", path).json()
    assert {r["documento"]["id_documento"] for r in rows} == {own["id_documento"], shared["id_documento"]}
    assert all(r["id_documento_vinculo"] != foreign_link["id_documento_vinculo"] for r in rows)
    with transactional_api["session_factory"]() as db:
        admin = app.dependency_overrides[auth.get_current_user]()
        set_audit_context(db, admin.id_usuario)
        link = db.query(models.DocumentoVinculo).filter_by(id_documento=own["id_documento"],
                                                          entidad_id=left_pn["id_proyecto_nucleo"]).one()
        mark_inactive(link, admin.id_usuario, "Prueba de vínculo inactivo")
        db.commit()
    assert {r["documento"]["id_documento"] for r in api("GET", path).json()} == {shared["id_documento"]}
    api("DELETE", f"/api/documentos/{shared['id_documento']}", json={"motivo": "Prueba documental"})
    assert api("GET", path).json() == []


@pytest.mark.parametrize("role", ["operador", "visualizador", "geografo"])
def test_consolidation_preserves_roles_project_scope_and_missing_target(
    api, target_domain, monkeypatch, role,
):
    pn = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    pid = target_domain["project"]["id_proyecto"]
    admin = app.dependency_overrides[auth.get_current_user]()
    api("POST", f"/api/proyectos/{pid}/usuarios", expected=201 if role == "operador" else 409,
        json={"id_usuario": admin.id_usuario})
    monkeypatch.setitem(app.dependency_overrides, auth.get_current_user,
                        lambda: SimpleNamespace(id_usuario=admin.id_usuario, rol=role))
    api("GET", f"/api/proyecto-nucleo/{pn}/documentos")
    api("GET", "/api/proyecto-nucleo/2147483647/documentos", expected=404)
    monkeypatch.setitem(app.dependency_overrides, auth.get_current_user,
                        lambda: SimpleNamespace(id_usuario=-1, rol=role))
    api("GET", f"/api/proyecto-nucleo/{pn}/documentos", expected=403)


@pytest.fixture(scope="module")
def gis_sample(transactional_api, tmp_path_factory):
    api = transactional_api["request"]
    tmp = tmp_path_factory.mktemp("read-gis")
    pid = project(api)
    nid, key = nucleus(transactional_api, pid)
    ids = [parcel(transactional_api, nid, f"P-{i}") for i in range(3)]
    for identity in ids:
        link_parcel(transactional_api, pid, nid, identity)
    imports = []
    for version in (1, 2):
        iid = stage_parcels(api, pid, gpkg(tmp, f"read-{version}", [("p", [
            (polygon(i * 4 + version), attrs(key, f"P-{i}")) for i in range(3)
        ])])).json()["id_importacion"]
        finish(api, iid, accept=version == 2)
        imports.append(iid)
    return {"project": pid, "import": imports[-1], "parcels": ids, "key": key}


def test_gis_actor_labels_and_bounded_reads(transactional_api, gis_sample):
    api = transactional_api["request"]
    iid, pid = gis_sample["import"], gis_sample["project"]
    actor = app.dependency_overrides[auth.get_current_user]()
    name = " ".join(p.strip() for p in (actor.nombre, actor.apellido_paterno, actor.apellido_materno) if p and p.strip())
    cycle = api("GET", f"/api/importaciones/{iid}/conciliaciones").json()[0]
    assert cycle["usuario_nombre"] == name and cycle["id_usuario"] == actor.id_usuario
    detail_path = f"/api/importaciones/{iid}/conciliaciones/{cycle['id_ciclo']}"
    with sql_reads(transactional_api["connection"]) as cycle_queries:
        detail = api("GET", detail_path).json()
    assert sum("FROM importacion_feature_candidato" in q for q in cycle_queries) == 1
    assert sum("FROM importacion_feature_decision" in q for q in cycle_queries) == 1
    assert len(detail["features"]) == 3
    destinations = {(d["id_proyecto_nucleo"], d["id_parcela"]): d for d in detail["universo_destinos"]}
    for feature in detail["features"]:
        for candidate in feature["candidatos"]:
            dest = destinations[(candidate["id_proyecto_nucleo"], candidate["id_parcela"])]
            assert all(dest[field] for field in ["nombre_nucleo", "municipio", "entidad", "numero_parcela"])
            assert candidate["usuario_revision_nombre"] == name
        assert all(d["creado_por_nombre"] == name for d in feature["decisiones"])
        feature_id = feature["id_importacion_feature"]
        assert api("GET", f"/api/importaciones/{iid}/features/{feature_id}/decisiones").json() == feature["decisiones"]
        assert api("GET", f"/api/importaciones/{iid}/features/{feature_id}/candidatos").json() == feature["candidatos"]
    with sql_reads(transactional_api["connection"]) as revision_queries:
        rows = api("GET", f"/api/proyectos/{pid}/geoespacial/revisiones").json()
    assert len(rows) == 3
    with sql_reads(transactional_api["connection"]) as page_queries:
        api("GET", f"/api/proyectos/{pid}/geoespacial/revisiones", params={"limit": 1})
    assert len(revision_queries) == len(page_queries)
    for row in rows:
        assert row["creado_por_nombre"] == name
        assert row["destino"]["numero_parcela"] in {"P-0", "P-1", "P-2"}
        assert all(row["destino"][f] for f in ("nombre_nucleo", "municipio", "entidad"))
        record = api("GET", f"/api/geoespacial/revisiones/{row['id_revision']}").json()
        assert all(record[k] == v for k, v in row.items())
    decision = api("POST", f"/api/geoespacial/revisiones/{rows[0]['id_revision']}/decisiones", expected=201,
                   json={"accion": "revisado", "motivo": "Comprobar actor",
                         "clave_solicitud": str(uuid.uuid4())}).json()
    assert decision["creado_por_nombre"] == name
    assert api("GET", f"/api/geoespacial/revisiones/{rows[0]['id_revision']}").json()["decisiones"] == [decision]
    name_queries = [q for q in cycle_queries + revision_queries if "usuario.nombre" in q]
    assert name_queries and all("usuario.correo" not in q and "usuario.rol" not in q for q in name_queries)
    assert all("usuario.activo" not in q for q in name_queries)  # Inactive historical actors remain readable.
    for schema_name in ["CandidatoGisResponse", "DecisionGisResponse", "CicloGisResponse",
                        "RevisionGisResponse", "RevisionGisDecisionResponse"]:
        properties = app.openapi()["components"]["schemas"][schema_name]["properties"]
        assert not {"correo", "rol", "numero_empleado", "actor"} & properties.keys()


def test_gis_totals_filters_offsets_and_cors(transactional_api, gis_sample):
    api = transactional_api["request"]
    iid, pid = gis_sample["import"], gis_sample["project"]
    for path in [f"/api/importaciones/{iid}/features", f"/api/importaciones/{iid}/conciliaciones",
                 f"/api/proyectos/{pid}/importaciones", f"/api/proyectos/{pid}/geoespacial/revisiones"]:
        full = api("GET", path)
        rows = full.json()
        assert int(full.headers["x-total-count"]) == len(rows)
        for skip in (0, 1, 99):
            page = api("GET", path, params={"skip": skip, "limit": 1},
                       headers={"Origin": AUTH_SETTINGS.allowed_origins[0]})
            assert page.json() == rows[skip:skip + 1]
            assert int(page.headers["x-total-count"]) == len(rows)
            assert "X-Total-Count" in page.headers["access-control-expose-headers"]
    assert api("GET", f"/api/importaciones/{iid}/features", params={"estado_conciliacion": "sin_coincidencia"}).headers["x-total-count"] == "0"
    filtered = api("GET", f"/api/importaciones/{iid}/features", params={"estado_conciliacion": "confirmado", "limit": 1})
    assert filtered.headers["x-total-count"] == "3" and len(filtered.json()) == 1
    path = f"/api/proyectos/{pid}/geoespacial/revisiones"
    rows = api("GET", path).json()
    first = rows[0]
    for params in [
        {"estado": "pendiente"}, {"estado": "revisado"}, {"tipo_cambio": first["tipo_cambio"]},
        {"tipo_cambio": "inexistente"}, {"objetivo": "parcela"}, {"objetivo": "ddv"},
        {"id_proyecto_nucleo": first["id_proyecto_nucleo"]}, {"id_proyecto_nucleo": 2147483647},
        {"desde": first["creado_en"]}, {"hasta": first["creado_en"]},
        {"estado": "pendiente", "objetivo": "parcela", "tipo_cambio": first["tipo_cambio"],
         "desde": rows[-1]["creado_en"], "hasta": first["creado_en"]},
    ]:
        def included(row):
            equal_fields = {"estado": "estado_revision", "tipo_cambio": "tipo_cambio",
                            "objetivo": "objetivo", "id_proyecto_nucleo": "id_proyecto_nucleo"}
            if any(row[field] != params[p] for p, field in equal_fields.items() if p in params):
                return False
            created = datetime.fromisoformat(row["creado_en"].replace("Z", "+00:00"))
            return ("desde" not in params or created >= datetime.fromisoformat(params["desde"].replace("Z", "+00:00"))) and (
                "hasta" not in params or created <= datetime.fromisoformat(params["hasta"].replace("Z", "+00:00")))

        expected = [row for row in rows if included(row)]
        full = api("GET", path, params=params)
        page = api("GET", path, params={**params, "skip": 1, "limit": 1})
        assert int(full.headers["x-total-count"]) == len(full.json())
        assert full.json() == expected
        assert page.headers["x-total-count"] == full.headers["x-total-count"]
        assert page.json() == full.json()[1:2]


def test_historical_inactive_actor_and_multiple_cycle_totals(transactional_api, gis_sample, tmp_path, monkeypatch):
    api = transactional_api["request"]
    actor, _ = _create_user(api, role="geografo")
    pid = gis_sample["project"]
    api("POST", f"/api/proyectos/{pid}/usuarios", expected=201, json={"id_usuario": actor["id_usuario"]})
    iid = stage_parcels(api, pid, gpkg(tmp_path, "inactive-actor", [("p", [
        (polygon(), attrs(gis_sample["key"], "P-0")),
        (polygon(4), attrs(gis_sample["key"], "INEXISTENTE")),
    ])])).json()["id_importacion"]
    admin_override = app.dependency_overrides[auth.get_current_user]
    monkeypatch.setitem(app.dependency_overrides, auth.get_current_user,
                        lambda: SimpleNamespace(id_usuario=actor["id_usuario"], rol="geografo"))
    cycle = reconcile(api, iid).json()
    name = f"{actor['nombre']} {actor['apellido_paterno']}"
    assert cycle["usuario_nombre"] == name
    feature = preview(api, iid)[1]
    api("POST", f"/api/importaciones/{iid}/features/{feature['id_importacion_feature']}/decisiones",
        json={"accion": "ignorar", "motivo": "Operación sintética"})
    monkeypatch.setitem(app.dependency_overrides, auth.get_current_user, admin_override)
    api("DELETE", f"/api/usuarios/{actor['id_usuario']}", json={"motivo": "Actor histórico de prueba"})
    decisions = api("GET", f"/api/importaciones/{iid}/features/{feature['id_importacion_feature']}/decisiones").json()
    assert decisions[0]["creado_por_nombre"] == name
    assert decisions[0]["creado_por"] == actor["id_usuario"]
    page = api("GET", f"/api/importaciones/{iid}/conciliaciones", params={"skip": 1, "limit": 1})
    assert page.headers["x-total-count"] == "2"
    assert page.json()[0]["id_ciclo"] == cycle["id_ciclo"]
    assert page.json()[0]["usuario_nombre"] == name
    detail = api("GET", f"/api/importaciones/{iid}/conciliaciones/{cycle['id_ciclo']}").json()
    assert detail["usuario_nombre"] == name and detail["features"][0]["decisiones"] == decisions


@pytest.mark.parametrize("role", ["operador", "visualizador", "geografo"])
def test_gis_read_permissions_and_write_roles_unchanged(transactional_api, gis_sample, monkeypatch, role):
    api = transactional_api["request"]
    iid, pid = gis_sample["import"], gis_sample["project"]
    monkeypatch.setitem(app.dependency_overrides, auth.get_current_user,
                        lambda: SimpleNamespace(id_usuario=-1, rol=role))
    for path in [f"/api/importaciones/{iid}/features", f"/api/importaciones/{iid}/conciliaciones",
                 f"/api/proyectos/{pid}/geoespacial/revisiones"]:
        assert "x-total-count" not in api("GET", path, expected=403).headers
    api("POST", f"/api/importaciones/{iid}/reconciliar", expected=403,
        json={"motivo": "Fuera de alcance", "clave_solicitud": str(uuid.uuid4())})


def test_openapi_only_optional_output_fields_and_new_get():
    contract = app.openapi()
    schemas = contract["components"]["schemas"]
    for name, fields in {
        "CandidatoGisResponse": ["usuario_revision_nombre"], "CicloGisResponse": ["usuario_nombre"],
        "DecisionGisResponse": ["creado_por_nombre"], "RevisionGisDecisionResponse": ["creado_por_nombre"],
        "RevisionGisResponse": ["creado_por_nombre", "destino"],
    }.items():
        assert all(f in schemas[name]["properties"] and f not in schemas[name]["required"] for f in fields)
    assert set(contract["paths"]["/api/proyecto-nucleo/{id_proyecto_nucleo}/documentos"]) == {"get"}
    for path in ["/api/importaciones/{id_importacion}/features", "/api/importaciones/{id_importacion}/conciliaciones",
                 "/api/proyectos/{id_proyecto}/importaciones", "/api/proyectos/{id_proyecto}/geoespacial/revisiones"]:
        response = contract["paths"][path]["get"]["responses"]["200"]
        assert response["content"]["application/json"]["schema"]["type"] == "array"
        assert response["headers"]["X-Total-Count"]["schema"]["type"] == "integer"
