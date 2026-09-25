"""Contrato HTTP y transaccional de la importación DDV GeoPackage."""

import json
import sqlite3
import subprocess
import uuid
from types import SimpleNamespace

from sqlalchemy import event, text

from app import auth
from app.database import engine
from app.main import app


def _polygon(offset=0):
    return {
        "type": "Polygon",
        "coordinates": [[
            [offset, 0], [offset, 1], [offset + 1, 1],
            [offset + 1, 0], [offset, 0],
        ]],
    }


def _multipolygon(offset=0):
    return {"type": "MultiPolygon", "coordinates": [_polygon(offset)["coordinates"]]}


def _gpkg(tmp_path, label, layers, *, crs="EPSG:4326", unknown_crs=False):
    """Produce capas GPKG pequeñas con GDAL, sin depender de cartografía real."""
    destination = tmp_path / f"{label}.gpkg"
    for layer_name, geometries in layers:
        source = tmp_path / f"{label}-{layer_name}.geojson"
        source.write_text(json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": f"{layer_name}-{index}",
                    "properties": {"etiqueta": f"{label}-{index}"},
                    "geometry": geometry,
                }
                for index, geometry in enumerate(geometries)
            ],
        }, sort_keys=True), encoding="utf-8")
        command = ["ogr2ogr", "-f", "GPKG"]
        if destination.exists():
            command.append("-update")
        command.extend([
            str(destination), str(source), "-nln", layer_name, "-a_srs", crs,
        ])
        subprocess.run(command, check=True, capture_output=True, text=True)
    with sqlite3.connect(destination) as connection:
        connection.execute(
            "UPDATE gpkg_contents SET last_change = '2026-01-01T00:00:00.000Z'"
        )
        if unknown_crs:
            connection.execute("UPDATE gpkg_geometry_columns SET srs_id = 0")
            connection.execute("UPDATE gpkg_contents SET srs_id = 0")
    return destination.read_bytes()


def _project(request):
    return request(
        "POST", "/api/proyectos", expected=201,
        json={
            "clave_proyecto": f"DDV-{uuid.uuid4().hex[:12]}",
            "nombre_proyecto": "Proyecto sintético DDV GPKG",
        },
    ).json()["id_proyecto"]


def _stage(request, project_id, content, *, name="ddv.gpkg", expected=201, extra=None):
    return request(
        "POST", f"/api/proyectos/{project_id}/geoespacial/ddv/importaciones",
        expected=expected,
        data={"fuente": "Fixture DDV QA", "fecha_fuente": "2026-09-25", **(extra or {})},
        files={"archivo": (name, content, "application/geopackage+sqlite3")},
    )


def _confirm(request, import_id, *, accept=False, expected=200):
    return request(
        "POST", f"/api/importaciones/{import_id}/confirmar",
        expected=expected,
        json={"confirmacion_explicita": True, "aceptar_advertencias": accept},
    )


def test_ddv_polygon_and_multipolygon_versions_preserve_history(
    transactional_api, tmp_path
):
    api = transactional_api["request"]
    connection = transactional_api["connection"]
    project_id = _project(api)
    first = _gpkg(tmp_path, "first", [("ddv", [_polygon(0), _polygon(3)])])
    staged = _stage(api, project_id, first).json()
    assert staged["tipo_objetivo"] == "derecho_via_proyecto"
    assert staged["formato_detectado"] == "gpkg"
    assert staged["total_features"] == staged["validos"] == 2
    assert staged["errores"] == staged["advertencias"] == 0
    assert staged["crs_original"] == "EPSG:4326"
    assert connection.execute(text(
        "SELECT count(*) FROM derecho_via_proyecto WHERE id_proyecto=:id"
    ), {"id": project_id}).scalar_one() == 0
    preview = api("GET", f"/api/importaciones/{staged['id_importacion']}/features").json()
    assert len(preview) == 2
    assert preview[0]["atributos_originales"]["etiqueta"] == "first-0"
    assert preview[0]["capa_origen"] == "ddv"
    assert preview[0]["atributos_normalizados"] == {}
    assert {item["codigo"] for item in preview[0]["transformaciones"]} == {
        "POLYGON_A_MULTIPOLYGON"
    }
    first_done = _confirm(api, staged["id_importacion"]).json()
    assert first_done["estado"] == "completo"
    assert first_done["reporte"]["version_ddv"] == 1

    second = _gpkg(tmp_path, "second", [("ddv", [_multipolygon(7)])])
    second_staged = _stage(api, project_id, second).json()
    second_preview = api(
        "GET", f"/api/importaciones/{second_staged['id_importacion']}/features"
    ).json()
    assert second_preview[0]["tipo_geometria"] == "MultiPolygon"
    assert second_preview[0]["transformaciones"] == []
    _confirm(api, second_staged["id_importacion"])
    rows = connection.execute(text("""
        SELECT version, activo, es_vigente, ST_GeometryType(geometria_poligono),
               ST_NumGeometries(geometria_poligono)
          FROM derecho_via_proyecto WHERE id_proyecto=:id ORDER BY version
    """), {"id": project_id}).all()
    assert [(row.version, row.activo, row.es_vigente) for row in rows] == [
        (1, True, False), (2, True, True)
    ]
    assert rows[0][3:] == ("ST_MultiPolygon", 2)
    assert rows[1][3:] == ("ST_MultiPolygon", 1)
    _confirm(api, second_staged["id_importacion"], expected=409)
    assert connection.execute(text(
        "SELECT count(*) FROM derecho_via_proyecto WHERE id_proyecto=:id"
    ), {"id": project_id}).scalar_one() == 2


def test_ddv_rejects_other_formats_multiple_layers_and_mapping(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = _project(api)
    polygon = _polygon()
    _stage(api, project_id, b"not a gpkg", name="ddv.kmz", expected=415)
    _stage(api, project_id, b"not a gpkg", name="ddv.geojson", expected=415)
    _stage(api, project_id, json.dumps(polygon).encode(), expected=415)
    multiple = _gpkg(tmp_path, "multiple", [
        ("ddv", [polygon]), ("extra", [_polygon(3)]),
    ])
    _stage(api, project_id, multiple, expected=422)
    single = _gpkg(tmp_path, "strict", [("ddv", [polygon])])
    _stage(api, project_id, single, expected=422, extra={"mapeo": "{}"})
    _stage(api, project_id, single, expected=422, extra={"tipo_objetivo": "parcela"})


def test_ddv_reprojects_known_crs_and_rejects_unknown(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = _project(api)
    mercator = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0, 1000], [1000, 1000], [1000, 0], [0, 0]]],
    }
    content = _gpkg(tmp_path, "mercator", [("ddv", [mercator])], crs="EPSG:3857")
    staged = _stage(api, project_id, content).json()
    assert staged["crs_original"] == "EPSG:3857"
    preview = api("GET", f"/api/importaciones/{staged['id_importacion']}/features").json()
    assert preview[0]["transformaciones"][0] == {
        "codigo": "CRS_REPROYECTADO",
        "origen": "EPSG:3857",
        "destino": "EPSG:4326",
    }
    _confirm(api, staged["id_importacion"])
    maximum = transactional_api["connection"].execute(text("""
        SELECT ST_XMax(geometria_poligono)
          FROM derecho_via_proyecto WHERE id_proyecto=:id
    """), {"id": project_id}).scalar_one()
    assert 0 < maximum < 0.01

    unknown = _gpkg(tmp_path, "unknown", [("ddv", [_polygon()])], unknown_crs=True)
    _stage(api, project_id, unknown, expected=422)


def test_ddv_repairs_invalid_polygon_only_with_explicit_warning_acceptance(
    transactional_api, tmp_path
):
    api = transactional_api["request"]
    project_id = _project(api)
    bowtie = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]],
    }
    staged = _stage(api, project_id, _gpkg(tmp_path, "bowtie", [("ddv", [bowtie])])).json()
    assert staged["advertencias"] == 1
    assert staged["errores"] == 0
    preview = api("GET", f"/api/importaciones/{staged['id_importacion']}/features").json()
    assert preview[0]["estado"] == "advertencia"
    assert preview[0]["advertencias"][0]["codigo"] == "GEOMETRIA_REPARADA"
    assert "Self-intersection" in preview[0]["advertencias"][0]["razon"]
    assert "GEOMETRIA_REPARADA" in {
        item["codigo"] for item in preview[0]["transformaciones"]
    }
    _confirm(api, staged["id_importacion"], expected=409)
    assert transactional_api["connection"].execute(text(
        "SELECT count(*) FROM derecho_via_proyecto WHERE id_proyecto=:id"
    ), {"id": project_id}).scalar_one() == 0
    _confirm(api, staged["id_importacion"], accept=True)
    confirmed = api("GET", f"/api/importaciones/{staged['id_importacion']}/features").json()
    assert confirmed[0]["advertencias_aceptadas"] is True


def test_ddv_irrecoverable_geometry_blocks_confirmation(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = _project(api)
    collapsed = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 1], [2, 2], [0, 0]]],
    }
    staged = _stage(api, project_id, _gpkg(tmp_path, "collapsed", [("ddv", [collapsed])])).json()
    assert staged["errores"] == 1
    preview = api("GET", f"/api/importaciones/{staged['id_importacion']}/features").json()
    assert preview[0]["estado"] == "error"
    assert preview[0]["errores"][0]["codigo"] == "GEOMETRIA_IRRECUPERABLE"
    _confirm(api, staged["id_importacion"], accept=True, expected=409)
    assert transactional_api["connection"].execute(text(
        "SELECT count(*) FROM derecho_via_proyecto WHERE id_proyecto=:id"
    ), {"id": project_id}).scalar_one() == 0

    line = {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}
    line_record = _stage(
        api, project_id, _gpkg(tmp_path, "line", [("ddv", [line])])
    ).json()
    assert line_record["errores"] == 1
    line_preview = api(
        "GET", f"/api/importaciones/{line_record['id_importacion']}/features"
    ).json()
    assert line_preview[0]["errores"][0]["codigo"] == "TIPO_GEOMETRIA_NO_PERMITIDO"


def test_ddv_confirmation_rolls_back_previous_version_on_insert_failure(
    transactional_api, tmp_path
):
    api = transactional_api["request"]
    project_id = _project(api)
    first = _stage(api, project_id, _gpkg(tmp_path, "rollback-first", [("ddv", [_polygon()])])).json()
    _confirm(api, first["id_importacion"])
    second = _stage(api, project_id, _gpkg(tmp_path, "rollback-second", [("ddv", [_polygon(4)])])).json()

    def fail_ddv_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith("INSERT INTO derecho_via_proyecto"):
            raise RuntimeError("Fallo sintético después de desmarcar versión previa")

    event.listen(engine, "before_cursor_execute", fail_ddv_insert)
    try:
        _confirm(api, second["id_importacion"], expected=409)
    finally:
        event.remove(engine, "before_cursor_execute", fail_ddv_insert)
    rows = transactional_api["connection"].execute(text("""
        SELECT version, activo, es_vigente
          FROM derecho_via_proyecto WHERE id_proyecto=:id ORDER BY version
    """), {"id": project_id}).all()
    assert rows == [(1, True, True)]
    retry = api("GET", f"/api/importaciones/{second['id_importacion']}").json()
    assert retry["estado"] == "previsualizado"
    assert retry["confirmacion_explicita"] is False
    _confirm(api, second["id_importacion"])


def test_ddv_upload_allows_admin_and_assigned_geographer_only(
    transactional_api, tmp_path
):
    api = transactional_api["request"]
    project_id = _project(api)
    other_project_id = _project(api)
    content = _gpkg(tmp_path, "roles", [("ddv", [_polygon()])])
    original = app.dependency_overrides[auth.get_current_user]
    try:
        for role, expected in (("operador", 403), ("geografo", 201)):
            user = api("POST", "/api/usuarios", expected=201, json={
                "nombre": role.title(),
                "apellido_paterno": "DDV QA",
                "correo": f"{role}-{uuid.uuid4().hex}@example.invalid",
                "rol": role,
                "contrasena": f"Qa1!{uuid.uuid4().hex}Z",
            }).json()
            api("POST", f"/api/proyectos/{project_id}/usuarios", expected=201,
                json={"id_usuario": user["id_usuario"]})
            app.dependency_overrides[auth.get_current_user] = (
                lambda user_id=user["id_usuario"], user_role=role:
                SimpleNamespace(id_usuario=user_id, rol=user_role, activo=True)
            )
            response = _stage(api, project_id, content, expected=expected)
            if role == "geografo":
                _stage(api, other_project_id, content, expected=403)
                _confirm(api, response.json()["id_importacion"])
            app.dependency_overrides[auth.get_current_user] = original
    finally:
        app.dependency_overrides[auth.get_current_user] = original
