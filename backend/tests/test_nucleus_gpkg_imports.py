"""Contrato GPKG estricto para geometrías de núcleos RAN ya existentes."""

import json
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from geoalchemy2.elements import WKTElement
from sqlalchemy import event, text

from app import auth, models
from app.database import engine
from app.main import app
from app.services.common import set_audit_context


def polygon(offset=0):
    return {"type": "Polygon", "coordinates": [[
        [offset, 0], [offset, 1], [offset + 1, 1], [offset + 1, 0], [offset, 0],
    ]]}


def gpkg(tmp_path, label, layers, *, crs="EPSG:4326", unknown_crs=False):
    destination = tmp_path / f"{label}.gpkg"
    for layer_name, features in layers:
        source = tmp_path / f"{label}-{layer_name}.geojson"
        source.write_text(json.dumps({
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "id": str(index), "geometry": geometry,
                 "properties": properties}
                for index, (geometry, properties) in enumerate(features)
            ],
        }, sort_keys=True), encoding="utf-8")
        command = ["ogr2ogr", "-f", "GPKG"]
        if destination.exists():
            command.append("-update")
        command.extend([str(destination), str(source), "-nln", layer_name, "-a_srs", crs])
        subprocess.run(command, check=True, capture_output=True, text=True)
    with sqlite3.connect(destination) as connection:
        connection.execute("UPDATE gpkg_contents SET last_change = '2026-01-01T00:00:00.000Z'")
        if unknown_crs:
            connection.execute("UPDATE gpkg_geometry_columns SET srs_id = 0")
            connection.execute("UPDATE gpkg_contents SET srs_id = 0")
    return destination.read_bytes()


def project(api):
    return api("POST", "/api/proyectos", expected=201, json={
        "clave_proyecto": f"NG-{uuid.uuid4().hex[:12]}",
        "nombre_proyecto": "Proyecto sintético núcleos GPKG",
    }).json()["id_proyecto"]


def nucleus(transactional_api, project_id, *, active=True, linked=True, geometry=None):
    with transactional_api["session_factory"]() as db:
        admin = db.query(models.Usuario).filter(models.Usuario.rol == "admin").first()
        municipality = db.query(models.Municipio).filter(models.Municipio.activo.is_(True)).first()
        tenure = db.query(models.CatalogoOperativo).filter(
            models.CatalogoOperativo.tipo_catalogo == "tipo_tenencia",
            models.CatalogoOperativo.codigo == "ejido",
        ).first()
        key = f"QA-{uuid.uuid4().hex}"
        set_audit_context(db, admin.id_usuario)
        item = models.NucleoAgrario(
            id_municipio=municipality.id_municipio,
            nombre_nucleo=f"Núcleo QA {key}",
            id_tipo_tenencia=tenure.id_catalogo_opcion,
            fuente_datos="RAN_PHINA_CATALOGO_NUCLEOS",
            id_entidad_fuente=str(municipality.id_entidad),
            id_municipio_fuente=str(municipality.id_municipio),
            id_nucleo_fuente=key,
            alcance_identidad_fuente="nacional",
            geometria_poligono=WKTElement(geometry, srid=4326) if geometry else None,
            fuente_geometria="Fuente anterior" if geometry else None,
            activo=active,
            creado_por=admin.id_usuario,
            fecha_baja=datetime.now(timezone.utc) if not active else None,
            id_usuario_baja=admin.id_usuario if not active else None,
            motivo_baja="QA" if not active else None,
        )
        db.add(item)
        db.flush()
        if linked:
            db.add(models.ProyectoNucleo(
                id_proyecto=project_id, id_nucleo=item.id_nucleo,
                activo=True, creado_por=admin.id_usuario,
            ))
        result = item.id_nucleo, key
        db.commit()
        return result


def stage(api, project_id, content, *, name="nucleos.gpkg", expected=201, extra=None):
    return api(
        "POST", f"/api/proyectos/{project_id}/geoespacial/nucleos/importaciones",
        expected=expected,
        data={"fuente": "Cartografía QA", "fecha_fuente": "2026-09-25", **(extra or {})},
        files={"archivo": (name, content, "application/geopackage+sqlite3")},
    )


def confirm(api, import_id, *, accept=False, expected=200):
    return api(
        "POST", f"/api/importaciones/{import_id}/confirmar", expected=expected,
        json={"confirmacion_explicita": True, "aceptar_advertencias": accept},
    )


def preview(api, import_id):
    return api("GET", f"/api/importaciones/{import_id}/features").json()


def test_nucleus_new_geometry_resolves_key_and_stages_before_commit(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    nucleus_id, key = nucleus(transactional_api, project_id)
    content = gpkg(tmp_path, "new", [("nucleos", [(polygon(), {"cve_unica": key})])])
    staged = stage(api, project_id, content).json()
    assert staged["tipo_objetivo"] == "nucleo_agrario_gpkg"
    assert (staged["validos"], staged["errores"], staged["advertencias"]) == (1, 0, 0)
    feature = preview(api, staged["id_importacion"])[0]
    assert feature["registro_destino_id"] == nucleus_id
    assert feature["atributos_normalizados"]["cve_unica"] == key
    assert feature["atributos_originales"]["cve_unica"] == key
    assert feature["transformaciones"] == [{"codigo": "POLYGON_A_MULTIPOLYGON"}]
    row = transactional_api["connection"].execute(text(
        "SELECT geometria_poligono IS NULL FROM nucleo_agrario WHERE id_nucleo=:id"
    ), {"id": nucleus_id}).scalar_one()
    assert row is True
    confirm(api, staged["id_importacion"])
    row = transactional_api["connection"].execute(text("""
        SELECT ST_GeometryType(geometria_poligono), ST_IsValid(geometria_poligono),
               fuente_geometria, fecha_fuente_geometria
          FROM nucleo_agrario WHERE id_nucleo=:id
    """), {"id": nucleus_id}).one()
    assert row[0] == "ST_MultiPolygon" and row[1] is True
    assert row[2] == "Cartografía QA" and str(row[3]) == "2026-09-25"
    assert preview(api, staged["id_importacion"])[0]["estado"] == "confirmado"
    confirm(api, staged["id_importacion"], expected=409)


def test_nucleus_rejects_missing_empty_unknown_inactive_and_outside_project(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    _, valid_key = nucleus(transactional_api, project_id)
    _, inactive_key = nucleus(transactional_api, project_id, active=False)
    _, outside_key = nucleus(transactional_api, project_id, linked=False)
    items = [
        ("empty", "", "CVE_UNICA_VACIA"),
        ("unknown", "NO-EXISTE", "CVE_UNICA_INEXISTENTE"),
        ("inactive", inactive_key, "NUCLEO_INACTIVO"),
        ("outside", outside_key, "NUCLEO_FUERA_DEL_PROYECTO"),
    ]
    for label, key, code in items:
        staged = stage(api, project_id, gpkg(
            tmp_path, label, [("nucleos", [(polygon(), {"cve_unica": key})])]
        )).json()
        assert staged["errores"] == 1
        assert preview(api, staged["id_importacion"])[0]["errores"][0]["codigo"] == code
        confirm(api, staged["id_importacion"], accept=True, expected=409)
    missing = gpkg(tmp_path, "missing", [("nucleos", [(polygon(), {"otra": valid_key})])])
    stage(api, project_id, missing, expected=422)
    assert transactional_api["connection"].execute(text(
        "SELECT count(*) FROM nucleo_agrario WHERE geometria_poligono IS NOT NULL AND id_nucleo_fuente=:key"
    ), {"key": valid_key}).scalar_one() == 0


def test_nucleus_duplicate_key_blocks_entire_import(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    nucleus_id, key = nucleus(transactional_api, project_id)
    staged = stage(api, project_id, gpkg(tmp_path, "duplicate", [("nucleos", [
        (polygon(), {"cve_unica": key}), (polygon(3), {"cve_unica": key}),
    ])])).json()
    assert staged["errores"] == 1
    assert preview(api, staged["id_importacion"])[1]["errores"][0]["codigo"] == "NUCLEO_DUPLICADO_EN_IMPORTACION"
    confirm(api, staged["id_importacion"], expected=409)
    assert transactional_api["connection"].execute(text(
        "SELECT geometria_poligono IS NULL FROM nucleo_agrario WHERE id_nucleo=:id"
    ), {"id": nucleus_id}).scalar_one() is True


def test_nucleus_replacement_warns_and_preserves_provenance(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    old_wkt = "MULTIPOLYGON(((0 0,0 1,1 1,1 0,0 0)))"
    nucleus_id, key = nucleus(transactional_api, project_id, geometry=old_wkt)
    staged = stage(api, project_id, gpkg(tmp_path, "replacement", [("nucleos", [
        (polygon(3), {"cve_unica": key}),
    ])])).json()
    assert staged["advertencias"] == 1
    feature = preview(api, staged["id_importacion"])[0]
    assert feature["advertencias"][0]["codigo"] == "GEOMETRIA_EXISTENTE_DISTINTA"
    confirm(api, staged["id_importacion"], expected=409)
    assert transactional_api["connection"].execute(text(
        "SELECT ST_AsText(geometria_poligono) FROM nucleo_agrario WHERE id_nucleo=:id"
    ), {"id": nucleus_id}).scalar_one() == old_wkt
    confirm(api, staged["id_importacion"], accept=True)
    assert preview(api, staged["id_importacion"])[0]["advertencias_aceptadas"] is True
    row = transactional_api["connection"].execute(text("""
        SELECT ST_XMin(geometria_poligono), fuente_geometria,
               fecha_fuente_geometria FROM nucleo_agrario WHERE id_nucleo=:id
    """), {"id": nucleus_id}).one()
    assert row[0] == 3 and row[1] == "Cartografía QA" and str(row[2]) == "2026-09-25"


def test_nucleus_same_geometry_does_not_warn(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    _, key = nucleus(
        transactional_api, project_id,
        geometry="MULTIPOLYGON(((0 0,0 1,1 1,1 0,0 0)))",
    )
    staged = stage(api, project_id, gpkg(tmp_path, "same", [("nucleos", [
        (polygon(), {"cve_unica": key}),
    ])])).json()
    assert staged["advertencias"] == 0
    confirm(api, staged["id_importacion"])


def test_nucleus_strict_format_columns_layers_crs_and_multipolygon(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    _, key = nucleus(transactional_api, project_id)
    stage(api, project_id, b"not gpkg", name="nucleo.kmz", expected=415)
    stage(api, project_id, b"not gpkg", name="nucleo.gpkg", expected=422)
    stage(api, project_id, gpkg(tmp_path, "layers", [
        ("nucleos", [(polygon(), {"cve_unica": key})]),
        ("otra", [(polygon(2), {"cve_unica": key})]),
    ]), expected=422)
    stage(api, project_id, gpkg(tmp_path, "forbidden", [("nucleos", [
        (polygon(), {"cve_unica": key, "id_destino": 17}),
    ])]), expected=422)
    stage(api, project_id, gpkg(tmp_path, "forbidden-internal", [("nucleos", [
        (polygon(), {"cve_unica": key, "id_nucleo": 17}),
    ])]), expected=422)
    stage(api, project_id, gpkg(tmp_path, "unknown-crs", [("nucleos", [
        (polygon(), {"cve_unica": key}),
    ])], unknown_crs=True), expected=422)
    mercator = {"type": "MultiPolygon", "coordinates": [[[[
        0, 0], [0, 1000], [1000, 1000], [1000, 0], [0, 0],
    ]]]}
    staged = stage(api, project_id, gpkg(tmp_path, "mercator", [("nucleos", [
        (mercator, {"cve_unica": key}),
    ])], crs="EPSG:3857")).json()
    feature = preview(api, staged["id_importacion"])[0]
    assert feature["tipo_geometria"] == "MultiPolygon"
    assert feature["transformaciones"] == [{
        "codigo": "CRS_REPROYECTADO", "origen": "EPSG:3857", "destino": "EPSG:4326",
    }]
    confirm(api, staged["id_importacion"])


def test_nucleus_repair_requires_acceptance_and_irrecoverable_blocks(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    _, key = nucleus(transactional_api, project_id)
    bowtie = {"type": "Polygon", "coordinates": [[
        [0, 0], [2, 2], [0, 2], [2, 0], [0, 0],
    ]]}
    staged = stage(api, project_id, gpkg(tmp_path, "repair", [("nucleos", [
        (bowtie, {"cve_unica": key}),
    ])])).json()
    assert preview(api, staged["id_importacion"])[0]["advertencias"][0]["codigo"] == "GEOMETRIA_REPARADA"
    confirm(api, staged["id_importacion"], expected=409)
    confirm(api, staged["id_importacion"], accept=True)
    collapsed = {"type": "Polygon", "coordinates": [[
        [0, 0], [1, 1], [2, 2], [0, 0],
    ]]}
    failed = stage(api, project_id, gpkg(tmp_path, "collapsed", [("nucleos", [
        (collapsed, {"cve_unica": key}),
    ])])).json()
    assert failed["errores"] == 1
    assert preview(api, failed["id_importacion"])[0]["errores"][0]["codigo"] == "GEOMETRIA_IRRECUPERABLE"
    confirm(api, failed["id_importacion"], accept=True, expected=409)


def test_nucleus_rollback_and_stale_preview_protection(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    first_id, first_key = nucleus(transactional_api, project_id)
    second_id, second_key = nucleus(transactional_api, project_id)
    staged = stage(api, project_id, gpkg(tmp_path, "rollback", [("nucleos", [
        (polygon(), {"cve_unica": first_key}),
        (polygon(3), {"cve_unica": second_key}),
    ])])).json()

    def fail_update(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith("UPDATE nucleo_agrario"):
            raise RuntimeError("Fallo sintético de actualización")

    event.listen(engine, "before_cursor_execute", fail_update)
    try:
        confirm(api, staged["id_importacion"], expected=409)
    finally:
        event.remove(engine, "before_cursor_execute", fail_update)
    rows = transactional_api["connection"].execute(text("""
        SELECT id_nucleo, geometria_poligono IS NULL FROM nucleo_agrario
         WHERE id_nucleo IN (:first, :second) ORDER BY id_nucleo
    """), {"first": first_id, "second": second_id}).all()
    assert all(row[1] is True for row in rows)
    assert api("GET", f"/api/importaciones/{staged['id_importacion']}").json()["estado"] == "previsualizado"
    with transactional_api["session_factory"]() as db:
        admin = db.query(models.Usuario).filter(models.Usuario.rol == "admin").first()
        set_audit_context(db, admin.id_usuario)
        db.query(models.NucleoAgrario).filter(models.NucleoAgrario.id_nucleo == first_id).update({
            models.NucleoAgrario.geometria_poligono: WKTElement(
                "MULTIPOLYGON(((10 0,10 1,11 1,11 0,10 0)))", srid=4326
            )
        })
        db.commit()
    confirm(api, staged["id_importacion"], expected=409)
    assert transactional_api["connection"].execute(text(
        "SELECT geometria_poligono IS NULL FROM nucleo_agrario WHERE id_nucleo=:id"
    ), {"id": second_id}).scalar_one() is True


def test_nucleus_permissions_admin_and_geographer(transactional_api, tmp_path):
    api = transactional_api["request"]
    project_id = project(api)
    other_project = project(api)
    _, key = nucleus(transactional_api, project_id)
    content = gpkg(tmp_path, "roles-nuclei", [("nucleos", [(polygon(), {"cve_unica": key})])])
    original = app.dependency_overrides[auth.get_current_user]
    try:
        for role, expected in (("operador", 403), ("geografo", 201)):
            user = api("POST", "/api/usuarios", expected=201, json={
                "nombre": role.title(), "apellido_paterno": "Núcleos QA",
                "correo": f"{role}-{uuid.uuid4().hex}@example.invalid",
                "rol": role, "contrasena": f"Qa1!{uuid.uuid4().hex}Z",
            }).json()
            api("POST", f"/api/proyectos/{project_id}/usuarios", expected=201,
                json={"id_usuario": user["id_usuario"]})
            app.dependency_overrides[auth.get_current_user] = (
                lambda user_id=user["id_usuario"], user_role=role:
                SimpleNamespace(id_usuario=user_id, rol=user_role, activo=True)
            )
            response = stage(api, project_id, content, expected=expected)
            if role == "geografo":
                stage(api, other_project, content, expected=403)
                confirm(api, response.json()["id_importacion"])
            app.dependency_overrides[auth.get_current_user] = original
    finally:
        app.dependency_overrides[auth.get_current_user] = original


def test_nucleus_external_identity_uniqueness_prevents_ambiguity(transactional_api):
    assert transactional_api["connection"].execute(text("""
        SELECT indisunique FROM pg_index
         WHERE indexrelid = 'public.uq_nucleo_identidad_fuente'::regclass
    """)).scalar_one() is True


def test_nucleus_staging_database_contract(transactional_api):
    constraints = set(transactional_api["connection"].execute(text("""
        SELECT conname FROM pg_constraint
         WHERE conrelid = 'public.importacion_archivo'::regclass
           AND conname IN ('chk_importacion_objetivo', 'chk_importacion_nucleo_gpkg')
    """)).scalars())
    assert constraints == {"chk_importacion_objetivo", "chk_importacion_nucleo_gpkg"}
    assert transactional_api["connection"].execute(text("""
        SELECT checksum_sha256 FROM schema_migrations WHERE version = '022'
    """)).scalar_one() == "a244ed434176feff02ceacbb0e5204bebe0bb16d582dbb4efdea9a13a41ebf0b"
