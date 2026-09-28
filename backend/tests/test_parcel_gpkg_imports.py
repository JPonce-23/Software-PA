"""Contrato GPKG estricto de geometrías para parcelas existentes."""

import uuid
from types import SimpleNamespace

from geoalchemy2.elements import WKTElement
from sqlalchemy import event, text

from app import auth, models
from app.database import engine
from app.main import app
from app.services.common import set_audit_context
from app.services.geospatial_imports import normalize_parcel_number
from tests.test_nucleus_gpkg_imports import (
    confirm, gpkg, nucleus, polygon, preview, project,
)


def parcel(transactional_api, nucleus_id, number, *, active=True, geometry=None):
    with transactional_api["session_factory"]() as db:
        admin = db.query(models.Usuario).filter(models.Usuario.rol == "admin").first()
        set_audit_context(db, admin.id_usuario)
        item = models.Parcela(
            id_nucleo=nucleus_id,
            tipo_parcela="individual",
            no_parcela=number,
            geometria_poligono=WKTElement(geometry, srid=4326) if geometry else None,
            fuente_geometria="Fuente anterior" if geometry else None,
            activo=active,
            creado_por=admin.id_usuario,
        )
        if not active:
            from datetime import datetime, timezone
            item.fecha_baja = datetime.now(timezone.utc)
            item.id_usuario_baja = admin.id_usuario
            item.motivo_baja = "QA"
        db.add(item)
        db.commit()
        return item.id_parcela


def stage(api, project_id, content, *, name="parcelas.gpkg", expected=201, extra=None):
    return api(
        "POST", f"/api/proyectos/{project_id}/geoespacial/parcelas/importaciones",
        expected=expected,
        data={"fuente": "Cartografía parcelaria QA", "fecha_fuente": "2026-09-25", **(extra or {})},
        files={"archivo": (name, content, "application/geopackage+sqlite3")},
    )


def attrs(key, number, **extra):
    return {"cve_unica_nucleo": key, "no_parcela": number, **extra}


def test_parcel_number_normalization_is_narrow():
    assert normalize_parcel_number(" P.-666 ") == normalize_parcel_number("P-666") == "p-666"
    assert {normalize_parcel_number(f"P-585{letter}") for letter in "ABCD"} == {
        "p-585a", "p-585b", "p-585c", "p-585d",
    }
    assert normalize_parcel_number("P.-585A") != normalize_parcel_number("P-585A")
    assert normalize_parcel_number("P/666") != normalize_parcel_number("P-666")
    assert normalize_parcel_number(" P  -  666 ") == "p - 666"


def test_parcel_matches_documented_variant_and_stages_before_commit(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    nucleus_id, key = nucleus(transactional_api, project_id)
    parcel_id = parcel(transactional_api, nucleus_id, "P-666")
    content = gpkg(tmp_path, "match", [("parcelas", [
        (polygon(), attrs(key, "P.-666", titular="No se usa para identificar")),
    ])])
    staged = stage(api, project_id, content).json()
    assert staged["tipo_objetivo"] == "parcela_gpkg"
    assert (staged["validos"], staged["errores"], staged["advertencias"]) == (1, 0, 0)
    feature = preview(api, staged["id_importacion"])[0]
    assert feature["registro_destino_id"] == parcel_id
    assert feature["atributos_originales"]["no_parcela"] == "P.-666"
    assert feature["atributos_normalizados"]["no_parcela"] == "p-666"
    assert feature["atributos_normalizados"]["id_nucleo"] == nucleus_id
    assert transactional_api["connection"].execute(text(
        "SELECT geometria_poligono IS NULL FROM parcela WHERE id_parcela=:id"
    ), {"id": parcel_id}).scalar_one() is True
    confirm(api, staged["id_importacion"])
    row = transactional_api["connection"].execute(text("""
        SELECT ST_GeometryType(geometria_poligono), fuente_geometria,
               fecha_fuente_geometria FROM parcela WHERE id_parcela=:id
    """), {"id": parcel_id}).one()
    assert row[0] == "ST_MultiPolygon"
    assert row[1] == "Cartografía parcelaria QA" and str(row[2]) == "2026-09-25"
    confirm(api, staged["id_importacion"], expected=409)


def test_parcel_letter_suffixes_remain_distinct(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    nucleus_id, key = nucleus(transactional_api, project_id)
    ids = {letter: parcel(transactional_api, nucleus_id, f"P-585{letter}") for letter in "ABCD"}
    content = gpkg(tmp_path, "suffixes", [("parcelas", [
        (polygon(index * 3), attrs(key, f"P-585{letter}"))
        for index, letter in enumerate("ABCD")
    ])])
    staged = stage(api, project_id, content).json()
    assert staged["validos"] == 4
    assert [item["registro_destino_id"] for item in preview(api, staged["id_importacion"])] == list(ids.values())
    confirm(api, staged["id_importacion"])


def test_parcel_identity_errors_block_all_destinations(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    nucleus_id, key = nucleus(transactional_api, project_id)
    parcel_id = parcel(transactional_api, nucleus_id, "P-777")
    _, outside_key = nucleus(transactional_api, project_id, linked=False)
    inactive_id = parcel(transactional_api, nucleus_id, "P-778", active=False)
    cases = [
        ("empty-key", attrs("", "P-777"), "CVE_UNICA_NUCLEO_VACIA"),
        ("empty-number", attrs(key, ""), "NO_PARCELA_VACIO"),
        ("unknown-key", attrs("SIN-CVE", "P-777"), "CVE_UNICA_INEXISTENTE"),
        ("outside", attrs(outside_key, "P-777"), "NUCLEO_FUERA_DEL_PROYECTO"),
        ("missing", attrs(key, "P-999"), "PARCELA_INEXISTENTE"),
        ("inactive", attrs(key, "P-778"), "PARCELA_INACTIVA"),
    ]
    for label, properties, code in cases:
        staged = stage(api, project_id, gpkg(tmp_path, label, [("parcelas", [
            (polygon(), properties),
        ])])).json()
        assert staged["errores"] == 1
        assert any(item["codigo"] == code for item in preview(api, staged["id_importacion"])[0]["errores"])
        confirm(api, staged["id_importacion"], accept=True, expected=409)
    assert transactional_api["connection"].execute(text(
        "SELECT geometria_poligono IS NULL FROM parcela WHERE id_parcela IN (:first, :second)"
    ), {"first": parcel_id, "second": inactive_id}).scalars().all() == [True, True]


def test_parcel_ambiguous_variant_and_duplicate_destination(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    nucleus_id, key = nucleus(transactional_api, project_id)
    parcel(transactional_api, nucleus_id, "P-666")
    parcel(transactional_api, nucleus_id, "P.-666")
    ambiguous = stage(api, project_id, gpkg(tmp_path, "ambiguous", [("parcelas", [
        (polygon(), attrs(key, "P-666")),
    ])])).json()
    assert preview(api, ambiguous["id_importacion"])[0]["errores"][0]["codigo"] == "PARCELA_AMBIGUA"
    confirm(api, ambiguous["id_importacion"], expected=409)

    unique_id = parcel(transactional_api, nucleus_id, "P-667")
    duplicate = stage(api, project_id, gpkg(tmp_path, "duplicate", [("parcelas", [
        (polygon(), attrs(key, "P-667")),
        (polygon(3), attrs(key, "P.-667")),
    ])])).json()
    assert duplicate["errores"] == 1
    assert preview(api, duplicate["id_importacion"])[1]["errores"][0]["codigo"] == "PARCELA_DUPLICADA_EN_IMPORTACION"
    confirm(api, duplicate["id_importacion"], expected=409)
    assert transactional_api["connection"].execute(text(
        "SELECT geometria_poligono IS NULL FROM parcela WHERE id_parcela=:id"
    ), {"id": unique_id}).scalar_one() is True


def test_parcel_replacement_and_repair_require_acceptance(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    nucleus_id, key = nucleus(transactional_api, project_id)
    old_wkt = "MULTIPOLYGON(((0 0,0 1,1 1,1 0,0 0)))"
    parcel_id = parcel(transactional_api, nucleus_id, "P-100", geometry=old_wkt)
    replacement = stage(api, project_id, gpkg(tmp_path, "replacement", [("parcelas", [
        (polygon(3), attrs(key, "P-100")),
    ])])).json()
    assert replacement["advertencias"] == 1
    assert preview(api, replacement["id_importacion"])[0]["advertencias"][0]["codigo"] == "GEOMETRIA_EXISTENTE_DISTINTA"
    confirm(api, replacement["id_importacion"], expected=409)
    assert transactional_api["connection"].execute(text(
        "SELECT ST_AsText(geometria_poligono) FROM parcela WHERE id_parcela=:id"
    ), {"id": parcel_id}).scalar_one() == old_wkt
    confirm(api, replacement["id_importacion"], accept=True)

    parcel(transactional_api, nucleus_id, "P-101")
    bowtie = {"type": "Polygon", "coordinates": [[
        [0, 0], [2, 2], [0, 2], [2, 0], [0, 0],
    ]]}
    repaired = stage(api, project_id, gpkg(tmp_path, "repair", [("parcelas", [
        (bowtie, attrs(key, "P-101")),
    ])])).json()
    assert repaired["advertencias"] == 1
    assert preview(api, repaired["id_importacion"])[0]["advertencias"][0]["codigo"] == "GEOMETRIA_REPARADA"
    confirm(api, repaired["id_importacion"], expected=409)
    confirm(api, repaired["id_importacion"], accept=True)


def test_parcel_rollback_and_stale_preview(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    nucleus_id, key = nucleus(transactional_api, project_id)
    first_id = parcel(transactional_api, nucleus_id, "P-200")
    second_id = parcel(transactional_api, nucleus_id, "P-201")
    staged = stage(api, project_id, gpkg(tmp_path, "rollback", [("parcelas", [
        (polygon(), attrs(key, "P-200")),
        (polygon(3), attrs(key, "P-201")),
    ])])).json()

    def fail_update(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith("UPDATE parcela"):
            raise RuntimeError("Fallo sintético de parcela")

    event.listen(engine, "before_cursor_execute", fail_update)
    try:
        confirm(api, staged["id_importacion"], expected=409)
    finally:
        event.remove(engine, "before_cursor_execute", fail_update)
    assert transactional_api["connection"].execute(text(
        "SELECT geometria_poligono IS NULL FROM parcela WHERE id_parcela IN (:first, :second)"
    ), {"first": first_id, "second": second_id}).scalars().all() == [True, True]
    assert api("GET", f"/api/importaciones/{staged['id_importacion']}").json()["estado"] == "previsualizado"
    with transactional_api["session_factory"]() as db:
        admin = db.query(models.Usuario).filter(models.Usuario.rol == "admin").first()
        set_audit_context(db, admin.id_usuario)
        db.query(models.Parcela).filter(models.Parcela.id_parcela == first_id).update({
            models.Parcela.geometria_poligono: WKTElement(
                "MULTIPOLYGON(((10 0,10 1,11 1,11 0,10 0)))", srid=4326
            )
        })
        db.commit()
    confirm(api, staged["id_importacion"], expected=409)
    assert transactional_api["connection"].execute(text(
        "SELECT geometria_poligono IS NULL FROM parcela WHERE id_parcela=:id"
    ), {"id": second_id}).scalar_one() is True


def test_parcel_strict_input_crs_and_permissions(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    other_project = project(api)
    nucleus_id, key = nucleus(transactional_api, project_id)
    parcel(transactional_api, nucleus_id, "P-300")
    stage(api, project_id, b"bad", name="parcelas.kmz", expected=415)
    stage(api, project_id, gpkg(tmp_path, "forbidden", [("parcelas", [
        (polygon(), attrs(key, "P-300", id_parcela=5)),
    ])]), expected=422)
    stage(api, project_id, gpkg(tmp_path, "multi", [
        ("parcelas", [(polygon(), attrs(key, "P-300"))]),
        ("otra", [(polygon(3), attrs(key, "P-300"))]),
    ]), expected=422)
    stage(api, project_id, gpkg(tmp_path, "unknown", [("parcelas", [
        (polygon(), attrs(key, "P-300")),
    ])], unknown_crs=True), expected=422)
    content = gpkg(tmp_path, "roles", [("parcelas", [
        (polygon(), attrs(key, "P-300")),
    ])])
    original = app.dependency_overrides[auth.get_current_user]
    try:
        for role, expected in (("operador", 403), ("geografo", 201)):
            user = api("POST", "/api/usuarios", expected=201, json={
                "nombre": role.title(), "apellido_paterno": "Parcelas QA",
                "correo": f"{role}-{uuid.uuid4().hex}@example.invalid",
                "rol": role, "contrasena": f"Qa1!{uuid.uuid4().hex}Z",
            }).json()
            api("POST", f"/api/proyectos/{project_id}/usuarios", expected=201,
                json={"id_usuario": user["id_usuario"]})
            app.dependency_overrides[auth.get_current_user] = (
                lambda user_id=user["id_usuario"], user_role=role:
                SimpleNamespace(id_usuario=user_id, rol=user_role, activo=True)
            )
            result = stage(api, project_id, content, expected=expected)
            if role == "geografo":
                stage(api, other_project, content, expected=403)
                confirm(api, result.json()["id_importacion"])
            app.dependency_overrides[auth.get_current_user] = original
    finally:
        app.dependency_overrides[auth.get_current_user] = original


def test_parcel_known_crs_and_irrecoverable_geometry(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    nucleus_id, key = nucleus(transactional_api, project_id)
    parcel_id = parcel(transactional_api, nucleus_id, "P-400")
    mercator = {"type": "MultiPolygon", "coordinates": [[[
        [0, 0], [0, 1000], [1000, 1000], [1000, 0], [0, 0],
    ]]]}
    projected = stage(api, project_id, gpkg(tmp_path, "mercator", [("parcelas", [
        (mercator, attrs(key, "P-400")),
    ])], crs="EPSG:3857")).json()
    assert projected["crs_original"] == "EPSG:3857"
    assert preview(api, projected["id_importacion"])[0]["transformaciones"] == [{
        "codigo": "CRS_REPROYECTADO", "origen": "EPSG:3857", "destino": "EPSG:4326",
    }]
    confirm(api, projected["id_importacion"])
    maximum = transactional_api["connection"].execute(text(
        "SELECT ST_XMax(geometria_poligono) FROM parcela WHERE id_parcela=:id"
    ), {"id": parcel_id}).scalar_one()
    assert 0 < maximum < 0.01

    collapsed = {"type": "Polygon", "coordinates": [[
        [0, 0], [1, 1], [2, 2], [0, 0],
    ]]}
    failed = stage(api, project_id, gpkg(tmp_path, "collapsed", [("parcelas", [
        (collapsed, attrs(key, "P-400")),
    ])])).json()
    assert failed["errores"] == 1
    assert preview(api, failed["id_importacion"])[0]["errores"][0]["codigo"] == "GEOMETRIA_IRRECUPERABLE"
    confirm(api, failed["id_importacion"], accept=True, expected=409)


def test_parcel_staging_schema_contract(transactional_api):
    assert transactional_api["connection"].execute(text("""
        SELECT checksum_sha256 FROM schema_migrations WHERE version='023'
    """)).scalar_one() == "6491328bf6da3f22af31e1ae93e4569ba3836493043748d40cbc23fe26d3a7dd"
    assert transactional_api["connection"].execute(text("""
        SELECT count(*) FROM pg_constraint
         WHERE conrelid='public.importacion_archivo'::regclass
           AND conname='chk_importacion_parcela_gpkg'
    """)).scalar_one() == 1
