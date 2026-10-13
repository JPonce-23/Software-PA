"""Diagnósticos informativos, snapshots históricos y contratos aditivos GIS."""

from contextlib import contextmanager
from types import SimpleNamespace as N
import json
import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

from app import auth, models, schemas
from app.database import engine
from app.main import app
from app.services.common import set_audit_context
from app.services import gis_diagnostics, gis_reconciliation
from app.services.gis_diagnostics import matching_diagnostic, unavailable_diagnostic
from tests.test_gis_history_026 import reconcile
from tests.test_nucleus_gpkg_imports import (
    candidates, confirm, decision, gpkg, nucleus, polygon, preview, project,
    rename_nucleus, stage,
)
from tests.test_parcel_gpkg_imports import attrs, link_parcel, parcel, stage as stage_parcels


@contextmanager
def captured_reads(connection):
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(("SELECT", "WITH")):
            statements.append(statement)
    event.listen(connection, "before_cursor_execute", capture)
    try:
        yield statements
    finally:
        event.remove(connection, "before_cursor_execute", capture)


def diagnostic_context(*numbers):
    n = N(nombre_nucleo="San José", fuente_datos="RAN_PHINA_CATALOGO_NUCLEOS",
          id_nucleo_fuente="RAN-1", municipio=N(nombre="M1", entidad=N(nombre="E1")),
          tipo_tenencia=N(nombre="Ejido"))
    pn = N(id_proyecto_nucleo=1)
    nuclei = [(pn, n, None)]
    return nuclei, [(pn, n, N(id_parcela=i + 1, no_parcela=number)) for i, number in enumerate(numbers)]


@pytest.mark.parametrize("properties,expected,fields", [
    ({}, ["IDENTIDAD_NUCLEO_INSUFICIENTE"], []),
    ({"cve_unica": "OTRA", "NombreNucl": "San José", "municipio": "M2"},
     ["CLAVE_SIN_COINCIDENCIA_EN_UNIVERSO"], ["cve_unica"]),
    ({"NombreNucl": "Otro"}, ["NOMBRE_SIN_COINCIDENCIA_EN_UNIVERSO"], ["NombreNucl"]),
    ({"NombreNucl": "San Jose", "municipio": "M2", "entidad": "E2"},
     ["MUNICIPIO_INCOMPATIBLE"], ["NombreNucl", "municipio"]),
    ({"NombreNucl": "San Jose", "municipio": "M1", "entidad": "E2"},
     ["ENTIDAD_INCOMPATIBLE"], ["NombreNucl", "municipio", "entidad"]),
    ({"NombreNucl": "San Jose", "tipo_nucleo": "Comunidad"},
     ["TIPO_NUCLEO_INCOMPATIBLE"], ["NombreNucl", "tipo_nucleo"]),
])
def test_nucleus_diagnostic_predicates_and_precedence(properties, expected, fields):
    nuclei, _ = diagnostic_context()
    value = matching_diagnostic(properties, nuclei, nuclei, [], parcel=False)
    assert value["codigos"] == expected
    assert value["campos_evaluados"] == fields
    schemas.DiagnosticoConciliacionGisResponse.model_validate(value)


@pytest.mark.parametrize("source,destination,variant", [
    ("016", "16", True), ("0016", "16", True), ("P-016", "P-16", True),
    ("P.-016", "P-16", True), ("P-585B", "P-585A", False),
    ("P/16", "P-16", False), ("16", "P-16", False), ("016A", "16A", False),
])
def test_format_observation_never_changes_matching(source, destination, variant):
    nuclei, universe = diagnostic_context(destination)
    value = matching_diagnostic(attrs("RAN-1", source), universe, nuclei, [], parcel=True)
    assert value["codigos"] == ["PARCELA_SIN_COINCIDENCIA_EN_UNIVERSO"] + (
        ["VARIANTE_FORMATO_PENDIENTE_REVISION"] if variant else [])
    assert value["evidencia"]["candidatos"] == 0
    assert bool(value["evidencia"]["variantes_formato"]) == variant


def test_multiple_proven_territorial_rejections_and_official_precedence():
    nuclei, _ = diagnostic_context()
    pn, n, _ = nuclei[0]
    second = N(**vars(n))
    second.municipio = N(nombre="M2", entidad=N(nombre="E2"))
    context = nuclei + [(N(id_proyecto_nucleo=2), second, None)]
    value = matching_diagnostic({"NombreNucl": "San José", "municipio": "M1", "entidad": "E2"},
                                context, context, [], parcel=False)
    assert value["codigos"] == ["MUNICIPIO_INCOMPATIBLE", "ENTIDAD_INCOMPATIBLE"]
    assert value["evidencia"]["descartes_territoriales"] == {"municipio": 1, "entidad": 1, "tipo_nucleo": 0}
    value = matching_diagnostic({"cve_unica": "RAN-1", "municipio": "M2"}, nuclei, nuclei,
                                [N(id_proyecto_nucleo=pn.id_proyecto_nucleo)], parcel=False)
    assert value["codigos"] == [] and value["campos_evaluados"] == ["cve_unica"]
    n.fuente_datos = "FUENTE_NO_OFICIAL"
    value = matching_diagnostic({"cve_unica": "RAN-1"}, nuclei, nuclei, [], parcel=False)
    assert value["codigos"] == ["CLAVE_SIN_COINCIDENCIA_EN_UNIVERSO"]


def test_unavailable_contract_has_no_inferred_evidence():
    value = unavailable_diagnostic()
    assert schemas.DiagnosticoConciliacionGisResponse.model_validate(value).origen == "no_disponible"
    assert all(value["evidencia"][key] is None for key in ("destinos_evaluados", "nucleos_compatibles", "candidatos"))
    value["evidencia"]["candidatos"] = 0
    with pytest.raises(ValidationError):
        schemas.DiagnosticoConciliacionGisResponse.model_validate(value)
    value = unavailable_diagnostic()
    value["evidencia"]["titular"] = "NO AUTORIZADO"
    with pytest.raises(ValidationError):
        schemas.DiagnosticoConciliacionGisResponse.model_validate(value)


def test_legacy_technical_mapping_has_no_invented_nucleus_cause():
    nuclei, universe = diagnostic_context("16")
    value = matching_diagnostic({}, universe, nuclei, [], parcel=True, direct_id=-1, direct_id_field="id_destino")
    assert value["codigos"] == ["ID_ADMINISTRATIVO_SIN_COINCIDENCIA_EN_UNIVERSO"]
    assert value["campos_evaluados"] == ["id_destino"]
    assert value["evidencia"]["nucleos_evaluados"] == 0
    assert value["evidencia"]["parcelas_evaluadas"] == 1


@pytest.mark.parametrize("field", ["record_id", "id_destino", "id_parcela", "id_nucleo"])
@pytest.mark.parametrize("target", ["nucleo_agrario", "parcela"])
def test_technical_source_field_in_staging_reconciliation_and_history(transactional_api, field, target):
    api = transactional_api["request"]
    pid = project(api)
    nid, _ = nucleus(transactional_api, pid)
    destination = nid
    if target == "parcela":
        destination = parcel(transactional_api, nid, "16")
        link_parcel(transactional_api, pid, nid, destination)
    content = json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {field: value}, "geometry": polygon(i * 3)}
        for i, value in enumerate((destination, -1))
    ]}).encode()
    record = api("POST", f"/api/proyectos/{pid}/importaciones", expected=201,
        data={"tipo_objetivo": target, "fuente": "QA campo técnico",
              "mapeo": json.dumps({"id_destino": field})},
        files={"archivo": ("technical.geojson", content, "application/geo+json")}).json()
    iid = record["id_importacion"]
    rows = preview(api, iid)
    assert all(f["diagnostico"]["campos_evaluados"] == [field] for f in rows)
    assert rows[1]["diagnostico"]["codigos"] == ["ID_ADMINISTRATIVO_SIN_COINCIDENCIA_EN_UNIVERSO"]
    cs = candidates(api, iid, rows[0])
    assert len(cs) == 1 and cs[0]["clasificacion"] == ("revision" if target == "parcela" else "exacta")
    assert cs[0]["coincidencias"] == ["id_administrativo_legacy"]
    cid = rows[0]["id_ciclo_conciliacion"]
    first = api("GET", f"/api/importaciones/{iid}/conciliaciones/{cid}").json()
    second = reconcile(api, iid).json()
    current = preview(api, iid)
    assert current[0]["id_ciclo_conciliacion"] == cid
    assert current[1]["id_ciclo_conciliacion"] == second["id_ciclo"]
    assert current[1]["diagnostico"]["campos_evaluados"] == [field]
    historical = api("GET", f"/api/importaciones/{iid}/conciliaciones/{cid}").json()
    assert historical["estado"] == "finalizado" and historical["fecha_fin"] is not None
    assert {key: value for key, value in historical.items() if key not in {"estado", "fecha_fin"}} == {
        key: value for key, value in first.items() if key not in {"estado", "fecha_fin"}}
    assert candidates(api, iid, current[0]) == cs


def test_empty_universe_staging_retains_count_and_nonblocking_diagnostics(transactional_api, tmp_path):
    api = transactional_api["request"]
    pid = project(api)
    content = gpkg(tmp_path, "empty-diag", [("n", [(polygon(), {}), (polygon(3), {"cve_unica": "NO-DESTINO"})])])
    record = stage(api, pid, content).json()
    assert record["reporte"]["registros_administrativos"] == 0
    rows = preview(api, record["id_importacion"])
    assert rows[0]["diagnostico"]["codigos"] == ["UNIVERSO_DESTINOS_VACIO", "IDENTIDAD_NUCLEO_INSUFICIENTE"]
    assert rows[1]["diagnostico"]["codigos"] == ["UNIVERSO_DESTINOS_VACIO"]
    assert all(f["estado_conciliacion"] == "sin_coincidencia" and f["errores"] == [] for f in rows)
    assert stage(api, pid, content).json()["id_importacion"] == record["id_importacion"]
    assert confirm(api, record["id_importacion"]).json()["importados"] == 0


def test_nucleus_codes_persist_without_changing_candidates(transactional_api, tmp_path):
    api = transactional_api["request"]
    pid = project(api)
    nid, key = nucleus(transactional_api, pid)
    rename_nucleus(transactional_api, nid, "Núcleo diagnóstico")
    pairs = [
        ({"cve_unica": "FUERA", "NombreNucl": "Núcleo diagnóstico", "municipio": "NO"}, "CLAVE_SIN_COINCIDENCIA_EN_UNIVERSO"),
        ({"NombreNucl": "INEXISTENTE"}, "NOMBRE_SIN_COINCIDENCIA_EN_UNIVERSO"),
        ({"NombreNucl": "Núcleo diagnóstico", "municipio": "NO"}, "MUNICIPIO_INCOMPATIBLE"),
        ({"NombreNucl": "Núcleo diagnóstico", "entidad": "NO"}, "ENTIDAD_INCOMPATIBLE"),
        ({"NombreNucl": "Núcleo diagnóstico", "tipo_nucleo": "NO"}, "TIPO_NUCLEO_INCOMPATIBLE"),
        ({}, "IDENTIDAD_NUCLEO_INSUFICIENTE"),
    ]
    iid = stage(api, pid, gpkg(tmp_path, "nucleus-diag", [("n", [
        (polygon(i * 3), props) for i, (props, _) in enumerate(pairs)
    ])])).json()["id_importacion"]
    for feature, (_, code) in zip(preview(api, iid), pairs):
        assert feature["diagnostico"]["codigos"] == [code]
        assert feature["estado_conciliacion"] == "sin_coincidencia"
        assert candidates(api, iid, feature) == []
    assert confirm(api, iid).json()["importados"] == 0


def test_ambiguous_nuclei_have_diagnostic_and_no_automatic_selection(transactional_api, tmp_path):
    api = transactional_api["request"]
    pid = project(api)
    for _ in range(2):
        nid, _ = nucleus(transactional_api, pid)
        rename_nucleus(transactional_api, nid, "Ambiguo diagnóstico")
    iid = stage(api, pid, gpkg(tmp_path, "ambiguous-diag", [("n", [(polygon(), {"NombreNucl": "Ambiguo diagnóstico"})])])).json()["id_importacion"]
    f = preview(api, iid)[0]
    assert f["estado_conciliacion"] == "ambiguo"
    assert f["diagnostico"]["codigos"] == ["MULTIPLES_DESTINOS_COMPATIBLES"]
    assert f["diagnostico"]["evidencia"]["candidatos"] == 2
    assert all(c["clasificacion"] == "revision" and c["estado"] == "propuesto" for c in candidates(api, iid, f))


def test_identified_nucleus_without_eligible_parcels_and_other_project_scope(transactional_api, tmp_path):
    api = transactional_api["request"]
    pid, other = project(api), project(api)
    nid, key = nucleus(transactional_api, pid)
    api("POST", f"/api/proyectos/{other}/nucleos", expected=201, json={"id_nucleo": nid})
    p = parcel(transactional_api, nid, "16")
    link_parcel(transactional_api, other, nid, p)
    record = stage_parcels(api, pid, gpkg(tmp_path, "no-links-diag", [("p", [
        (polygon(), attrs(key, "16")), (polygon(3), {"cve_unica_nucleo": key}),
    ])])).json()
    rows = preview(api, record["id_importacion"])
    assert record["reporte"]["registros_administrativos"] == 0
    assert rows[0]["diagnostico"]["codigos"] == ["UNIVERSO_DESTINOS_VACIO", "PARCELA_SIN_COINCIDENCIA_EN_UNIVERSO"]
    assert rows[1]["diagnostico"]["codigos"] == ["UNIVERSO_DESTINOS_VACIO", "NUMERO_PARCELA_AUSENTE"]
    assert rows[0]["diagnostico"]["evidencia"]["nucleos_compatibles"] == 1
    assert rows[0]["diagnostico"]["evidencia"]["parcelas_evaluadas"] == 0
    assert all(candidates(api, record["id_importacion"], f) == [] for f in rows)
    assert str(p) not in str(rows[0]["diagnostico"]["evidencia"].get("variantes_formato"))


def test_parcel_numbers_diagnosed_without_changing_normalization_or_classification(transactional_api, tmp_path):
    api = transactional_api["request"]
    pid = project(api)
    nid, key = nucleus(transactional_api, pid)
    for number in ("16", "P-585A", "P-666", "P.-666"):
        link_parcel(transactional_api, pid, nid, parcel(transactional_api, nid, number))
    properties = [attrs(key, "016"), attrs(key, "P-585B"), attrs(key, "EXTRA"),
                  {"cve_unica_nucleo": key}, attrs(key, "P-666"),
                  {"cve_unica_nucleo": key, "PARCELA": "16", "Num_parcela": "16"}]
    record = stage_parcels(api, pid, gpkg(tmp_path, "parcel-diag", [("p", [
        (polygon(i * 3), {**props, "titular": "NO CONSERVAR", "CURP": "NO CONSERVAR"})
        for i, props in enumerate(properties)
    ])])).json()
    assert record["reporte"]["registros_administrativos"] == 4
    rows = preview(api, record["id_importacion"])
    assert [f["estado_conciliacion"] for f in rows] == ["sin_coincidencia"] * 4 + ["ambiguo", "candidato"]
    assert rows[0]["diagnostico"]["codigos"] == ["PARCELA_SIN_COINCIDENCIA_EN_UNIVERSO", "VARIANTE_FORMATO_PENDIENTE_REVISION"]
    assert rows[0]["atributos_originales"]["no_parcela"] == "016"
    assert rows[0]["diagnostico"]["evidencia"]["variantes_formato"][0]["destinos_observados"] == 1
    assert rows[1]["diagnostico"]["codigos"] == ["PARCELA_SIN_COINCIDENCIA_EN_UNIVERSO"]
    assert rows[2]["diagnostico"]["codigos"] == ["PARCELA_SIN_COINCIDENCIA_EN_UNIVERSO"]
    assert rows[3]["diagnostico"]["codigos"] == ["NUMERO_PARCELA_AUSENTE"]
    assert rows[4]["diagnostico"]["codigos"] == ["MULTIPLES_DESTINOS_COMPATIBLES"]
    assert candidates(api, record["id_importacion"], rows[5])[0]["clasificacion"] == "fuerte"
    assert all("NO CONSERVAR" not in str(f) and f["errores"] == [] for f in rows)
    with captured_reads(transactional_api["connection"]) as one:
        page = api("GET", f"/api/importaciones/{record['id_importacion']}/features", params={"limit": 1})
    with captured_reads(transactional_api["connection"]) as many:
        whole = api("GET", f"/api/importaciones/{record['id_importacion']}/features", params={"limit": 6})
    assert len(one) == len(many)
    assert sum("importacion_conciliacion_resultado" in sql for sql in many) == 1
    assert page.headers["X-Total-Count"] == whole.headers["X-Total-Count"] == "6"
    offset = api("GET", f"/api/importaciones/{record['id_importacion']}/features",
                 params={"skip": 1, "limit": 1, "estado_conciliacion": "sin_coincidencia"})
    assert offset.headers["X-Total-Count"] == "4" and offset.json()[0] == rows[1]
    legacy = dict(rows[0])
    legacy.pop("diagnostico"); legacy.pop("id_ciclo_conciliacion")
    assert schemas.ImportacionFeatureResponse.model_validate(legacy).diagnostico is None


def test_partial_reconciliation_keeps_each_feature_cycle_and_historical_diagnostics(transactional_api, tmp_path):
    api = transactional_api["request"]
    pid = project(api)
    _, key_a = nucleus(transactional_api, pid)
    nid_b, key_b = nucleus(transactional_api, pid, linked=False)
    iid = stage(api, pid, gpkg(tmp_path, "history-diag", [("n", [
        (polygon(), {"cve_unica": key_a}), (polygon(3), {"cve_unica": key_b}),
    ])])).json()["id_importacion"]
    first = preview(api, iid)
    decision(api, iid, first[0], "confirmar", candidates(api, iid, first[0])[0])
    confirm(api, iid)
    initial = api("GET", f"/api/importaciones/{iid}/conciliaciones/{first[0]['id_ciclo_conciliacion']}").json()
    api("POST", f"/api/proyectos/{pid}/nucleos", expected=201, json={"id_nucleo": nid_b})
    request_key = str(uuid.uuid4())
    second = reconcile(api, iid, key=request_key).json()
    assert reconcile(api, iid, key=request_key).json() == second
    current = preview(api, iid)
    assert current[0]["id_ciclo_conciliacion"] == first[0]["id_ciclo_conciliacion"]
    assert current[0]["diagnostico"] == first[0]["diagnostico"]
    assert current[1]["id_ciclo_conciliacion"] == second["id_ciclo"]
    assert current[1]["diagnostico"]["codigos"] == []
    assert first[1]["diagnostico"]["codigos"] == ["CLAVE_SIN_COINCIDENCIA_EN_UNIVERSO"]
    assert api("GET", f"/api/importaciones/{iid}/conciliaciones/{initial['id_ciclo']}").json() == initial
    assert len(candidates(api, iid, current[0])) == len(candidates(api, iid, current[1])) == 1
    old_candidate = candidates(api, iid, current[0])[0]
    assert old_candidate["estado"] == "confirmado"
    with transactional_api["session_factory"]() as db:
        for change in ("diagnostico=NULL", "estado_matching='ambiguo'"):
            with pytest.raises(DBAPIError):
                with db.begin_nested():
                    db.execute(text(f"UPDATE importacion_conciliacion_resultado SET {change} WHERE id_ciclo=:c"), {"c": initial["id_ciclo"]})


def test_null_historical_diagnostic_is_not_rebuilt_from_current_universe(transactional_api, tmp_path):
    api = transactional_api["request"]
    pid = project(api)
    nid, _ = nucleus(transactional_api, pid)
    iid = stage(api, pid, gpkg(tmp_path, "legacy-diag", [("n", [(polygon(), {})])])).json()["id_importacion"]
    cid = preview(api, iid)[0]["id_ciclo_conciliacion"]
    with transactional_api["session_factory"]() as db:
        actor = db.query(models.Usuario).filter_by(rol="admin", activo=True).first()
        set_audit_context(db, actor.id_usuario)
        f = models.ImportacionFeature(id_importacion=iid, indice_feature=100,
            atributos_originales={"NombreNucl": "Histórico"}, atributos_normalizados={},
            estado="valido", estado_conciliacion="sin_coincidencia")
        db.add(f); db.flush()
        fid = f.id_importacion_feature
        db.add(models.ImportacionConciliacionResultado(id_ciclo=cid, id_importacion_feature=fid, estado_matching="sin_coincidencia", diagnostico=None))
        db.commit()
    rename_nucleus(transactional_api, nid, "Histórico")
    f = next(row for row in preview(api, iid) if row["id_importacion_feature"] == fid)
    assert f["diagnostico"] == unavailable_diagnostic()
    detail = api("GET", f"/api/importaciones/{iid}/conciliaciones/{cid}").json()
    assert detail["features"][-1]["diagnostico"] == unavailable_diagnostic()
    with transactional_api["session_factory"]() as db:
        assert db.get(models.ImportacionConciliacionResultado, (cid, fid)).diagnostico is None


def test_diagnostic_failure_rolls_back_staging_and_reconciliation(transactional_api, tmp_path):
    api = transactional_api["request"]
    con = transactional_api["connection"]
    pid = project(api)
    before = con.execute(text("SELECT count(*) FROM importacion_archivo WHERE id_proyecto=:p"), {"p": pid}).scalar_one()
    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith("INSERT INTO importacion_conciliacion_resultado"):
            raise RuntimeError("Fallo sintético al persistir diagnóstico")
    content = gpkg(tmp_path, "rollback-diag", [("n", [(polygon(), {})])])
    event.listen(engine, "before_cursor_execute", fail)
    try:
        stage(api, pid, content, expected=422)
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    assert con.execute(text("SELECT count(*) FROM importacion_archivo WHERE id_proyecto=:p"), {"p": pid}).scalar_one() == before
    iid = stage(api, pid, content).json()["id_importacion"]
    first = preview(api, iid)
    initial = api("GET", f"/api/importaciones/{iid}/conciliaciones").json()
    event.listen(engine, "before_cursor_execute", fail)
    try:
        reconcile(api, iid, expected=409)
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    assert preview(api, iid) == first
    assert api("GET", f"/api/importaciones/{iid}/conciliaciones").json() == initial


def test_diagnostic_reads_preserve_project_access(transactional_api, tmp_path, monkeypatch):
    api = transactional_api["request"]
    pid = project(api)
    iid = stage(api, pid, gpkg(tmp_path, "access-diag", [("n", [(polygon(), {})])])).json()["id_importacion"]
    cid = preview(api, iid)[0]["id_ciclo_conciliacion"]
    monkeypatch.setitem(app.dependency_overrides, auth.get_current_user,
                        lambda: N(id_usuario=-1, rol="geografo", activo=True))
    api("GET", f"/api/importaciones/{iid}/features", expected=403)
    api("GET", f"/api/importaciones/{iid}/conciliaciones/{cid}", expected=403)


def test_database_rejects_malformed_diagnostic_envelopes(transactional_api, tmp_path):
    api = transactional_api["request"]
    pid = project(api)
    iid = stage(api, pid, gpkg(tmp_path, "envelope-diag", [("n", [(polygon(), {})])])).json()["id_importacion"]
    row = preview(api, iid)[0]
    cid = row["id_ciclo_conciliacion"]
    with transactional_api["session_factory"]() as db:
        actor = db.query(models.Usuario).filter_by(rol="admin", activo=True).first()
        set_audit_context(db, actor.id_usuario)
        f = models.ImportacionFeature(id_importacion=iid, indice_feature=101,
            atributos_originales={}, atributos_normalizados={}, estado="valido", estado_conciliacion="sin_coincidencia")
        db.add(f); db.flush()
        for invalid in ([], {}, {**row["diagnostico"], "version": "2"},
                        {**row["diagnostico"], "origen": "no_disponible"},
                        {**row["diagnostico"], "evidencia": None}):
            with pytest.raises(DBAPIError):
                with db.begin_nested():
                    db.add(models.ImportacionConciliacionResultado(id_ciclo=cid,
                        id_importacion_feature=f.id_importacion_feature, estado_matching="sin_coincidencia", diagnostico=invalid))
                    db.flush()
        assert db.get(models.ImportacionConciliacionResultado, (cid, f.id_importacion_feature)) is None


def test_diagnostic_generation_reuses_universe_without_feature_queries(transactional_api, tmp_path, monkeypatch):
    api = transactional_api["request"]
    pid = project(api)
    keys = []
    for index in range(2):
        nid, key = nucleus(transactional_api, pid)
        keys.append(key)
        rename_nucleus(transactional_api, nid, f"Núcleo rendimiento {index}")
        for number in ("16", "17", "P-585A"):
            link_parcel(transactional_api, pid, nid, parcel(transactional_api, nid, number))
    with transactional_api["session_factory"]() as db:
        nuclei = gis_reconciliation.administrative_universe(db, pid)
        with captured_reads(transactional_api["connection"]) as sql:
            universe = gis_reconciliation.administrative_universe(db, pid, parcels=True, nuclei=nuclei)
        # Links, parcels and their existing selectin relationship load in batches.
        assert len(universe) == 6 and len(sql) == 3
        assert not any("FROM proyecto_nucleo" in query for query in sql)
    original = gis_diagnostics.matching_diagnostic
    contexts, calls = set(), []
    def inspect(*args, **kwargs):
        contexts.add((id(args[1]), id(args[2])))
        with captured_reads(transactional_api["connection"]) as sql:
            diagnostic = original(*args, **kwargs)
        assert sql == []
        calls.append(diagnostic)
        return diagnostic
    monkeypatch.setattr(gis_diagnostics, "matching_diagnostic", inspect)
    props = [attrs(keys[0], "16"), attrs(keys[1], "016"),
             {"N__CLEO_AG": "Núcleo rendimiento 0", "municipio": "INCOMPATIBLE", "no_parcela": "17"},
             {"N__CLEO_AG": "Núcleo rendimiento 1", "no_parcela": "P-585B"}, {}] * 4
    content = gpkg(tmp_path, "bounded-diagnostic", [("p", [
        (polygon(index * 3), properties) for index, properties in enumerate(props)
    ])])
    iid = stage_parcels(api, pid, content).json()["id_importacion"]
    assert len(calls) == 20 and len(contexts) == 1
    with captured_reads(transactional_api["connection"]) as one:
        api("GET", f"/api/importaciones/{iid}/features", params={"limit": 1})
    with captured_reads(transactional_api["connection"]) as many:
        api("GET", f"/api/importaciones/{iid}/features", params={"limit": 20})
    assert len(one) == len(many)
    assert sum("importacion_conciliacion_resultado" in query for query in many) == 1


def test_openapi_diagnostic_fields_are_optional_and_no_new_endpoint():
    spec = app.openapi()
    feature = spec["components"]["schemas"]["ImportacionFeatureResponse"]
    result = spec["components"]["schemas"]["ResultadoCicloGisResponse"]
    assert "diagnostico" in feature["properties"] and "diagnostico" not in feature["required"]
    assert "id_ciclo_conciliacion" not in feature["required"]
    assert "diagnostico" in result["properties"] and "diagnostico" not in result["required"]
    assert not any(path.endswith("/diagnostico") for path in spec["paths"])
