"""B-07: confirmed project geometry, administrative scope and legacy fallback."""

from decimal import Decimal
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app import auth, models
from app.main import app
from app.services.common import mark_inactive, set_audit_context
from tests.test_ddv_gpkg_imports import _confirm as confirm_ddv, _stage as stage_ddv
from tests.test_gis_history_regressions import ADMINISTRATIVE_TABLES
from tests.test_nucleus_gpkg_imports import (
    candidates, confirm, decision, gpkg, nucleus, polygon, preview, project,
    stage as stage_nuclei,
)
from tests.test_parcel_gpkg_imports import attrs, link_parcel, parcel, stage as stage_parcels


LEGACY_WKT = "MULTIPOLYGON(((20 0,20 1,21 1,21 0,20 0)))"
FEATURE_KINDS = {"nucleo": "nucleo_agrario", "parcela": "parcela", "ddv": "derecho_via_proyecto"}


def map_features(api, project_id, kind):
    result = api("GET", f"/api/proyectos/{project_id}/mapa").json()
    assert result["type"] == "FeatureCollection"
    return [f for f in result["features"] if f["properties"]["tipo"] == FEATURE_KINDS[kind]]


def multipolygon(offset):
    return {"type": "MultiPolygon", "coordinates": [polygon(offset)["coordinates"]]}


def assert_geometry(connection, actual, offset):
    # GPKG normalization can change ring orientation without changing geometry.
    assert actual["type"] == "MultiPolygon"
    assert connection.execute(text("""
        SELECT ST_Equals(ST_GeomFromGeoJSON(:actual), ST_GeomFromGeoJSON(:expected))
    """), {"actual": json.dumps(actual), "expected": json.dumps(multipolygon(offset))}).scalar_one()


def stage_geometry(api, tmp_path, project_id, kind, key, offset):
    properties = {"cve_unica": key} if kind == "nucleo" else attrs(key, "P-100") if kind == "parcela" else {}
    content = gpkg(tmp_path, f"map-{kind}-{project_id}-{offset}", [("geometria", [(polygon(offset), properties)])])
    stage = {"nucleo": stage_nuclei, "parcela": stage_parcels, "ddv": stage_ddv}[kind]
    return stage(api, project_id, content).json()["id_importacion"]


def confirm_geometry(api, import_id, kind, *, accept=False):
    if kind == "ddv":
        return confirm_ddv(api, import_id, accept=accept).json()
    feature = preview(api, import_id)[0]
    decision(api, import_id, feature, "confirmar", candidates(api, import_id, feature)[0], accept=accept)
    return confirm(api, import_id).json()


def administrative_snapshot(connection):
    # Include every administrative surface, all row fields and financial records.
    return {
        name: connection.execute(text(f"""
            SELECT md5(COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)::text, '[]'))
            FROM {name} t
        """)).scalar_one()
        for name in (*ADMINISTRATIVE_TABLES, "convenio_afectacion", "indemnizacion", "pago")
    }


@pytest.mark.parametrize("kind", ["nucleo", "parcela", "ddv"])
def test_confirmed_geometry_appears_without_changing_administrative_surfaces(transactional_api, tmp_path, kind):
    api = transactional_api["request"]
    project_id = project(api)
    nucleus_id, key = nucleus(transactional_api, project_id)
    parcel_id = parcel(transactional_api, nucleus_id, "P-100")
    link_parcel(transactional_api, project_id, nucleus_id, parcel_id)
    with transactional_api["session_factory"]() as db:
        actor = db.query(models.Usuario).filter_by(rol="admin", activo=True).first()
        set_audit_context(db, actor.id_usuario)
        pn = db.query(models.ProyectoNucleo).filter_by(id_proyecto=project_id).one()
        affectation = db.query(models.Afectacion).filter_by(id_proyecto_nucleo=pn.id_proyecto_nucleo).one()
        unit_link = db.query(models.AfectacionUnidadAgraria).filter_by(id_afectacion=affectation.id_afectacion).one()
        for row in (affectation, unit_link):
            row.superficie_preliminar_ha = Decimal("13.7654321")
            row.superficie_afectada_ha = Decimal("12.3456789")
            row.actualizado_por = actor.id_usuario
        db.commit()
    before = administrative_snapshot(transactional_api["connection"])
    import_id = stage_geometry(api, tmp_path, project_id, kind, key, 0)
    assert map_features(api, project_id, kind) == []  # Staging is not publication.
    confirmed = confirm_geometry(api, import_id, kind)
    features = map_features(api, project_id, kind)
    assert len(features) == 1
    assert_geometry(transactional_api["connection"], features[0]["geometry"], 0)
    expected_id = nucleus_id if kind == "nucleo" else parcel_id if kind == "parcela" else confirmed["reporte"]["id_derecho_via"]
    assert features[0]["id"] == f"{FEATURE_KINDS[kind]}:{expected_id}"
    assert features[0]["properties"]["id"] == expected_id
    assert administrative_snapshot(transactional_api["connection"]) == before


@pytest.mark.parametrize("kind", ["nucleo", "parcela"])
def test_project_geometry_overrides_legacy_and_only_current_version_is_published(transactional_api, tmp_path, kind):
    api = transactional_api["request"]
    project_id = project(api)
    nucleus_id, key = nucleus(transactional_api, project_id, geometry=LEGACY_WKT if kind == "nucleo" else None)
    if kind == "parcela":
        parcel_id = parcel(transactional_api, nucleus_id, "P-100", geometry=LEGACY_WKT)
        link_parcel(transactional_api, project_id, nucleus_id, parcel_id)
    assert_geometry(transactional_api["connection"], map_features(api, project_id, kind)[0]["geometry"], 20)
    for index, offset in enumerate((0, 4)):
        import_id = stage_geometry(api, tmp_path, project_id, kind, key, offset)
        confirm_geometry(api, import_id, kind, accept=index > 0)
        features = map_features(api, project_id, kind)
        assert len(features) == 1
        assert_geometry(transactional_api["connection"], features[0]["geometry"], offset)
    table_name = "proyecto_nucleo_geometria" if kind == "nucleo" else "proyecto_parcela_geometria"
    assert transactional_api["connection"].execute(text(f"""
        SELECT g.version, g.activo, g.es_vigente FROM {table_name} g
        JOIN proyecto_nucleo pn USING(id_proyecto_nucleo)
        WHERE pn.id_proyecto=:project ORDER BY g.version
    """), {"project": project_id}).all() == [(1, True, False), (2, True, True)]


@pytest.mark.parametrize("kind", ["nucleo", "parcela", "ddv"])
def test_shared_administrative_records_do_not_mix_project_geometries(transactional_api, tmp_path, kind):
    api = transactional_api["request"]
    left, right = project(api), project(api)
    nucleus_id, key = nucleus(transactional_api, left)
    api("POST", f"/api/proyectos/{right}/nucleos", expected=201, json={"id_nucleo": nucleus_id})
    if kind == "parcela":
        parcel_id = parcel(transactional_api, nucleus_id, "P-100")
        for project_id in (left, right):
            link_parcel(transactional_api, project_id, nucleus_id, parcel_id)
    confirm_geometry(api, stage_geometry(api, tmp_path, left, kind, key, 0), kind)
    assert map_features(api, right, kind) == []
    confirm_geometry(api, stage_geometry(api, tmp_path, right, kind, key, 4), kind)
    for project_id, offset in ((left, 0), (right, 4)):
        features = map_features(api, project_id, kind)
        assert len(features) == 1
        assert_geometry(transactional_api["connection"], features[0]["geometry"], offset)


def test_legacy_parcel_requires_administrative_membership_not_just_shared_nucleus(transactional_api):
    api = transactional_api["request"]
    left, right = project(api), project(api)
    nucleus_id, _ = nucleus(transactional_api, left, geometry=LEGACY_WKT)
    api("POST", f"/api/proyectos/{right}/nucleos", expected=201, json={"id_nucleo": nucleus_id})
    parcel_id = parcel(transactional_api, nucleus_id, "P-100", geometry=LEGACY_WKT)
    parcel(transactional_api, nucleus_id, "P-UNLINKED", geometry=LEGACY_WKT)
    link_parcel(transactional_api, left, nucleus_id, parcel_id)
    features = map_features(api, left, "parcela")
    assert len(features) == 1
    assert features[0]["properties"]["id"] == parcel_id
    assert_geometry(transactional_api["connection"], features[0]["geometry"], 20)
    assert map_features(api, right, "parcela") == []
    assert_geometry(transactional_api["connection"], map_features(api, right, "nucleo")[0]["geometry"], 20)


@pytest.mark.parametrize("inactive_model", [
    models.ProyectoNucleo, models.NucleoAgrario, models.Parcela,
    models.Afectacion, models.AfectacionUnidadAgraria, models.UnidadAgraria,
])
def test_confirmed_parcel_is_hidden_when_administrative_membership_becomes_inactive(transactional_api, tmp_path, inactive_model):
    api = transactional_api["request"]
    project_id = project(api)
    nucleus_id, key = nucleus(transactional_api, project_id)
    parcel_id = parcel(transactional_api, nucleus_id, "P-100", geometry=LEGACY_WKT)
    link_parcel(transactional_api, project_id, nucleus_id, parcel_id)
    confirm_geometry(api, stage_geometry(api, tmp_path, project_id, "parcela", key, 0), "parcela")
    assert len(map_features(api, project_id, "parcela")) == 1
    with transactional_api["session_factory"]() as db:
        actor = db.query(models.Usuario).filter_by(rol="admin", activo=True).first()
        set_audit_context(db, actor.id_usuario)
        pn = db.query(models.ProyectoNucleo).filter_by(id_proyecto=project_id).one()
        affectation = db.query(models.Afectacion).filter_by(id_proyecto_nucleo=pn.id_proyecto_nucleo).one()
        unit_link = db.query(models.AfectacionUnidadAgraria).filter_by(id_afectacion=affectation.id_afectacion).one()
        row = {
            models.ProyectoNucleo: pn,
            models.NucleoAgrario: db.get(models.NucleoAgrario, nucleus_id),
            models.Parcela: db.get(models.Parcela, parcel_id),
            models.Afectacion: affectation,
            models.AfectacionUnidadAgraria: unit_link,
            models.UnidadAgraria: db.get(models.UnidadAgraria, unit_link.id_unidad_agraria),
        }[inactive_model]
        mark_inactive(row, actor.id_usuario, "Baja sintética para comprobar el universo del mapa")
        db.commit()
    assert map_features(api, project_id, "parcela") == []


def test_current_ddv_and_legacy_trace_are_independent_layers(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    trace = api("POST", f"/api/proyectos/{project_id}/trazos", expected=201, json={
        "version": 1, "geometria_wkt": "MULTILINESTRING((0 0,1 1))",
        "fuente": "Trazo sintético", "fecha_vigencia_inicio": "2026-01-01",
    }).json()
    for offset in (0, 4):
        current = confirm_geometry(api, stage_geometry(api, tmp_path, project_id, "ddv", None, offset), "ddv")
    result = api("GET", f"/api/proyectos/{project_id}/mapa").json()
    assert {f["id"] for f in result["features"]} == {
        f"trazo_proyecto:{trace['id_trazo']}",
        f"derecho_via_proyecto:{current['reporte']['id_derecho_via']}",
    }
    assert_geometry(transactional_api["connection"], map_features(api, project_id, "ddv")[0]["geometry"], 4)
    assert next(f for f in result["features"] if f["properties"]["tipo"] == "trazo_proyecto")["geometry"]["type"] == "MultiLineString"


def test_map_preserves_project_authorization(transactional_api):
    api = transactional_api["request"]
    allowed, forbidden = project(api), project(api)
    original = app.dependency_overrides[auth.get_current_user]
    admin = original()
    api("POST", f"/api/proyectos/{allowed}/usuarios", expected=201, json={"id_usuario": admin.id_usuario})
    try:
        app.dependency_overrides[auth.get_current_user] = lambda: SimpleNamespace(
            id_usuario=admin.id_usuario, rol="geografo", activo=True,
        )
        assert api("GET", f"/api/proyectos/{allowed}/mapa").json()["type"] == "FeatureCollection"
        api("GET", f"/api/proyectos/{forbidden}/mapa", expected=403)
    finally:
        app.dependency_overrides[auth.get_current_user] = original
