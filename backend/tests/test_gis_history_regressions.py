"""Regresiones ejecutables sobre 024; no requieren ampliar el esquema GIS."""

import pytest
from sqlalchemy import text

from tests.test_ddv_gpkg_imports import _confirm as confirm_ddv
from tests.test_ddv_gpkg_imports import _stage as stage_ddv
from tests.test_excel_closure_002 import _catalog, _isolated_pn
from tests.test_nucleus_gpkg_imports import (
    candidates, confirm, decision, gpkg, nucleus, polygon, preview, project,
    stage as stage_nuclei,
)
from tests.test_parcel_gpkg_imports import (
    attrs, link_parcel, parcel, stage as stage_parcels,
)


ADMINISTRATIVE_TABLES = (
    "proyecto", "proyecto_nucleo", "nucleo_agrario", "parcela", "afectacion",
    "convenio", "tramite_ran", "tramite_ran_evento", "seguimiento_evento",
    "unidad_agraria", "afectacion_unidad_agraria", "expediente_requisito",
)


def domain_counts(connection):
    return {
        table: connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
        for table in ADMINISTRATIVE_TABLES
    }


def project_domain_rows(connection, project_id):
    """Compara también campos/auditoría, no sólo la cantidad de registros."""
    return connection.execute(text("""
        SELECT to_jsonb(pr), to_jsonb(pn), to_jsonb(n), to_jsonb(a), to_jsonb(p)
        FROM proyecto pr
        JOIN proyecto_nucleo pn USING (id_proyecto)
        JOIN nucleo_agrario n USING (id_nucleo)
        LEFT JOIN afectacion a USING (id_proyecto_nucleo)
        LEFT JOIN afectacion_unidad_agraria au USING (id_afectacion)
        LEFT JOIN unidad_agraria u USING (id_unidad_agraria)
        LEFT JOIN parcela p ON p.id_parcela = u.id_parcela
        WHERE pr.id_proyecto = :project
        ORDER BY pn.id_proyecto_nucleo, a.id_afectacion, p.id_parcela
    """), {"project": project_id}).all()


@pytest.mark.parametrize("kind", ["nucleo", "parcela"])
def test_three_geometry_versions_preserve_provenance_and_administrative_domain(
    transactional_api, tmp_path, kind,
):
    api = transactional_api["request"]
    connection = transactional_api["connection"]
    project_id = project(api)
    nucleus_id, key = nucleus(transactional_api, project_id)
    if kind == "parcela":
        parcel_id = parcel(transactional_api, nucleus_id, "P-100")
        link_parcel(transactional_api, project_id, nucleus_id, parcel_id)
        stage, properties = stage_parcels, attrs(key, "P-100")
        table = "proyecto_parcela_geometria"
    else:
        stage, properties = stage_nuclei, {"cve_unica": key}
        table = "proyecto_nucleo_geometria"
    before_counts = domain_counts(connection)
    before_rows = project_domain_rows(connection, project_id)
    imports, feature_ids, historical_geometry = [], [], []
    for version in (1, 2, 3):
        staged = stage(api, project_id, gpkg(tmp_path, f"{kind}-v{version}", [
            ("geometrias", [(polygon(version * 3), properties)]),
        ])).json()
        import_id = staged["id_importacion"]
        imports.append(import_id)
        feature = preview(api, import_id)[0]
        feature_ids.append(feature["id_importacion_feature"])
        candidate = candidates(api, import_id, feature)[0]
        rows_before_confirmation = connection.execute(text(f"""
            SELECT g.version, ST_AsEWKB(g.geometria_poligono),
                   ST_AsEWKB(g.geometria_trabajo)
            FROM {table} g JOIN proyecto_nucleo pn USING (id_proyecto_nucleo)
            WHERE pn.id_proyecto = :project ORDER BY g.version
        """), {"project": project_id}).all()
        assert rows_before_confirmation == historical_geometry
        if version > 1:
            decision(api, import_id, feature, "confirmar", candidate, expected=409)
            assert api("GET", f"/api/importaciones/{import_id}/features/"
                       f"{feature['id_importacion_feature']}/decisiones").json() == []
        decision(api, import_id, feature, "confirmar", candidate, accept=version > 1)
        confirm(api, import_id)
        versions = connection.execute(text(f"""
            SELECT g.version, g.activo, g.es_vigente, g.id_importacion_feature,
                   i.id_importacion, g.srid_trabajo, i.srid_trabajo AS import_srid,
                   g.fuente = i.fuente AS source_matches,
                   g.fecha_fuente = i.fecha_fuente AS date_matches,
                   g.creado_por IS NOT NULL AND g.creado_en IS NOT NULL AS audited,
                   g.geometria_poligono = f.geometria_normalizada AS web_matches,
                   g.geometria_trabajo = f.geometria_trabajo AS work_matches
            FROM {table} g JOIN proyecto_nucleo pn USING (id_proyecto_nucleo)
            JOIN importacion_feature f USING (id_importacion_feature)
            JOIN importacion_archivo i USING (id_importacion)
            WHERE pn.id_proyecto = :project ORDER BY g.version
        """), {"project": project_id}).mappings().all()
        assert [row["version"] for row in versions] == list(range(1, version + 1))
        assert all(row["activo"] for row in versions)
        assert [row["es_vigente"] for row in versions] == [False] * (version - 1) + [True]
        assert [row["id_importacion"] for row in versions] == imports
        assert [row["id_importacion_feature"] for row in versions] == feature_ids
        assert all(row["srid_trabajo"] == row["import_srid"] for row in versions)
        assert all(all(row[field] for field in (
            "source_matches", "date_matches", "audited", "web_matches", "work_matches",
        )) for row in versions)
        historical_geometry = connection.execute(text(f"""
            SELECT g.version, ST_AsEWKB(g.geometria_poligono),
                   ST_AsEWKB(g.geometria_trabajo)
            FROM {table} g JOIN proyecto_nucleo pn USING (id_proyecto_nucleo)
            WHERE pn.id_proyecto = :project ORDER BY g.version
        """), {"project": project_id}).all()
        assert historical_geometry[:-1] == rows_before_confirmation
        assert domain_counts(connection) == before_counts
        assert project_domain_rows(connection, project_id) == before_rows


def test_ddv_spatial_changes_preserve_administrative_records_and_nucleus_versions(
    transactional_api, tmp_path,
):
    """El diagnóstico A/B/C no implica decisiones ni eventos administrativos."""
    api = transactional_api["request"]
    connection = transactional_api["connection"]
    project_id = project(api)
    nuclei = [nucleus(transactional_api, project_id) for _ in range(3)]
    staged = stage_nuclei(api, project_id, gpkg(tmp_path, "nuclei-abc", [
        ("nucleos", [(polygon(offset), {"cve_unica": key})
                     for offset, (_, key) in zip((0, 4, 8), nuclei)]),
    ])).json()
    for feature in preview(api, staged["id_importacion"]):
        decision(api, staged["id_importacion"], feature, "confirmar",
                 candidates(api, staged["id_importacion"], feature)[0])
    confirm(api, staged["id_importacion"])
    before_counts = domain_counts(connection)
    before_rows = project_domain_rows(connection, project_id)
    for version, offsets in ((1, (0, 4)), (2, (0, 8))):
        ddv = stage_ddv(api, project_id, gpkg(tmp_path, f"ddv-abc-v{version}", [
            ("ddv", [(polygon(offset), {}) for offset in offsets]),
        ])).json()
        confirm_ddv(api, ddv["id_importacion"])
        assert domain_counts(connection) == before_counts
        assert project_domain_rows(connection, project_id) == before_rows
    relations = connection.execute(text("""
        SELECT pn.id_nucleo,
               ST_Intersects(g.geometria_poligono, old.geometria_poligono) AS before,
               ST_Intersects(g.geometria_poligono, new.geometria_poligono) AS after
        FROM proyecto_nucleo pn
        JOIN proyecto_nucleo_geometria g USING (id_proyecto_nucleo)
        JOIN derecho_via_proyecto old ON old.id_proyecto = pn.id_proyecto AND old.version = 1
        JOIN derecho_via_proyecto new ON new.id_proyecto = pn.id_proyecto AND new.version = 2
        WHERE pn.id_proyecto = :project AND g.es_vigente
        ORDER BY pn.id_nucleo
    """), {"project": project_id}).all()
    assert relations == [(nuclei[0][0], True, True), (nuclei[1][0], True, False),
                         (nuclei[2][0], False, True)]
    assert connection.execute(text("""
        SELECT g.version, g.activo, g.es_vigente FROM proyecto_nucleo_geometria g
        JOIN proyecto_nucleo pn USING (id_proyecto_nucleo)
        WHERE pn.id_proyecto = :project
    """), {"project": project_id}).all() == [(1, True, True)] * 3


def test_full_non_linear_history_keeps_every_event_and_derives_last_transition(
    transactional_api, transactional_target_domain,
):
    api = transactional_api["request"]
    connection = transactional_api["connection"]
    project_row, pn = _isolated_pn(api, transactional_target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    event_types = _catalog(api, "tipo_evento_seguimiento")
    reasons = _catalog(api, "motivo_seguimiento")
    before_rows = project_domain_rows(connection, project_row["id_proyecto"])
    sequence = [
        ("inicio", "activo", "inicio"),
        ("suspension", "suspendido", "suspension"),
        ("reapertura", "activo", "reapertura"),
        ("cambio_alcance", "activo", "reapertura"),
        ("cierre", "cerrado", "cierre"),
        ("reapertura", "activo", "reapertura"),
    ]
    created = []
    for day, (code, expected_state, expected_transition) in enumerate(sequence, 1):
        created.append(api("POST", f"/api/proyecto-nucleo/{pn_id}/seguimiento",
                           expected=201, json={
            "ambito": "general", "id_tipo_evento": event_types[code],
            "id_motivo": reasons["nueva_informacion"],
            "fecha_evento": f"2026-01-{day:02d}",
            "detalle": f"Decisión humana sintética: {code}",
        }).json())
        assert connection.execute(text("""
            SELECT estado_actual, tipo_ultimo_evento FROM vw_seguimiento_estado_actual
            WHERE id_proyecto_nucleo = :pn
        """), {"pn": pn_id}).one() == (expected_state, expected_transition)
        assert api("GET", f"/api/proyecto-nucleo/{pn_id}/seguimiento").json() == created
        assert project_domain_rows(connection, project_row["id_proyecto"]) == before_rows
    assert len({row["id_seguimiento_evento"] for row in created}) == len(sequence)
