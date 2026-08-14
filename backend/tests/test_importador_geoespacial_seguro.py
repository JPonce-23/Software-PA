import json
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app import models
from app.config import AUTH_SETTINGS
from app.database import SessionLocal
from app.main import app
from app.services import importador_geoespacial as service
from app.services.gis_ingestion import IngestionError, LayerInfo, inspect_dataset


ORIGIN = AUTH_SETTINGS.allowed_origins[0]


def _territory():
    with SessionLocal() as db:
        municipality = (
            db.query(models.Municipio)
            .join(models.EntidadFederativa)
            .filter(models.Municipio.activo.is_(True), models.EntidadFederativa.activo.is_(True))
            .order_by(models.Municipio.id_municipio)
            .first()
        )
        entity = db.get(models.EntidadFederativa, municipality.id_entidad)
        return {
            "id_municipio": municipality.id_municipio,
            "municipio": municipality.nombre,
            "id_entidad": entity.id_entidad,
            "entidad": entity.nombre,
            "clave_municipio": municipality.clave_inegi,
            "clave_entidad": entity.clave_inegi,
        }


def _polygon(offset=0, z=False):
    points = [
        [offset, 0], [offset + 0.01, 0], [offset + 0.01, 0.01],
        [offset, 0.01], [offset, 0],
    ]
    if z:
        points = [[x, y, 10] for x, y in points]
    return {"type": "Polygon", "coordinates": [points]}


def _feature(name=None, nucleus_id=None, geometry=None, type_value="EJIDO", **extra):
    territory = _territory()
    properties = {
        "NombreNucleoAgrario": name or f"NUCLEO {uuid4().hex[:10]}",
        "TipoNucleoAgrario": type_value,
        "NombreMunicipio": territory["municipio"],
        "NombreEntidadFederativa": territory["entidad"],
        "IdMunicipio": str(territory["id_municipio"] + 100000),
        "IdEntidadFederativa": territory["clave_entidad"],
        "IdNucleoAgrario": nucleus_id or uuid4().hex,
        **extra,
    }
    return {"type": "Feature", "properties": properties, "geometry": geometry or _polygon()}


def _geojson(*features, crs=None):
    payload = {"type": "FeatureCollection", "features": list(features)}
    if crs:
        payload["crs"] = {"type": "name", "properties": {"name": crs}}
    return json.dumps(payload).encode()


def _upload(client, headers, content, filename=None, source=None):
    return client.post(
        "/api/importaciones-geoespaciales",
        headers=headers,
        data={"fuente": source or f"RAN-TEST-{uuid4().hex}"},
        files={"file": (filename or f"nucleos-{uuid4().hex}.geojson", content, "application/octet-stream")},
    )


def _process(client, headers, record, mapping=None, options=None):
    payload = {
        "mapeo": mapping or record["mapeo"],
        "opciones": options or {},
    }
    mapped = client.put(
        f"/api/importaciones-geoespaciales/{record['id_importacion']}/mapeo",
        headers=headers,
        json=payload,
    )
    assert mapped.status_code == 200, mapped.text
    started = client.post(
        f"/api/importaciones-geoespaciales/{record['id_importacion']}/procesar",
        headers=headers,
    )
    assert started.status_code == 202, started.text
    detail = client.get(
        f"/api/importaciones-geoespaciales/{record['id_importacion']}",
        headers=headers,
    )
    assert detail.status_code == 200
    return detail.json()


def test_geojson_staging_no_escribe_y_confirmacion_es_explicita(
    client, admin_session, cleanup
):
    name = f"STAGING {uuid4().hex[:12]}"
    content = _geojson(_feature(name=name))
    with SessionLocal() as db:
        before = db.query(models.NucleoAgrario).filter(models.NucleoAgrario.nombre_nucleo == name).count()
    uploaded = _upload(client, admin_session, content)
    assert uploaded.status_code == 201, uploaded.text
    record = uploaded.json()
    assert record["sha256"]
    assert record["formato_detectado"] == "geojson"
    assert record["mapeo"]["id_municipio_fuente"] == "IdMunicipio"
    assert record["mapeo"]["id_nucleo_fuente"] == "IdNucleoAgrario"

    ready = _process(client, admin_session, record)
    assert ready["estado"] == "listo_revision"
    assert ready["validos"] == 1
    with SessionLocal() as db:
        assert db.query(models.NucleoAgrario).filter(models.NucleoAgrario.nombre_nucleo == name).count() == before

    confirmed = client.post(
        f"/api/importaciones-geoespaciales/{record['id_importacion']}/confirmar",
        headers=admin_session,
        json={"aceptar_advertencias": False},
    )
    assert confirmed.status_code == 202, confirmed.text
    completed = client.get(
        f"/api/importaciones-geoespaciales/{record['id_importacion']}",
        headers=admin_session,
    ).json()
    assert completed["estado"] == "completado"
    assert completed["importados"] == 1
    page = client.get(
        f"/api/importaciones-geoespaciales/{record['id_importacion']}/features",
        headers=admin_session,
    ).json()
    nucleus_id = page["items"][0]["id_nucleo_operativo"]
    cleanup.register("/api/nucleos", nucleus_id)

    repeated = client.post(
        f"/api/importaciones-geoespaciales/{record['id_importacion']}/confirmar",
        headers=admin_session,
        json={"aceptar_advertencias": False},
    )
    assert repeated.status_code == 409
    duplicate_file = _upload(client, admin_session, content)
    assert duplicate_file.status_code == 409
    report = client.get(
        f"/api/importaciones-geoespaciales/{record['id_importacion']}/reporte.csv",
        headers=admin_session,
    )
    assert report.status_code == 200
    assert record["sha256"] in report.text


def test_id_municipio_externo_no_se_interpreta_como_pk(client, admin_session):
    territory = _territory()
    external_id = str(territory["id_municipio"] + 100000)
    uploaded = _upload(client, admin_session, _geojson(_feature()))
    assert uploaded.status_code == 201
    ready = _process(client, admin_session, uploaded.json())
    assert ready["validos"] == 1
    feature = client.get(
        f"/api/importaciones-geoespaciales/{ready['id_importacion']}/features",
        headers=admin_session,
    ).json()["items"][0]
    assert feature["id_municipio_resuelto"] == territory["id_municipio"]
    with SessionLocal() as db:
        staged = db.get(models.ImportacionFeature, feature["id_importacion_feature"])
        assert staged.id_municipio_fuente == external_id


def test_tipo_desconocido_y_municipio_inexistente_quedan_en_staging(client, admin_session):
    feature = _feature(type_value="PROPIEDAD PRIVADA")
    feature["properties"]["NombreMunicipio"] = f"INEXISTENTE {uuid4().hex}"
    uploaded = _upload(client, admin_session, _geojson(feature))
    ready = _process(client, admin_session, uploaded.json())
    assert ready["errores"] == 1
    item = client.get(
        f"/api/importaciones-geoespaciales/{ready['id_importacion']}/features?estado=error",
        headers=admin_session,
    ).json()["items"][0]
    codes = {problem["codigo"] for problem in item["errores"]}
    assert "TIPO_NUCLEO_DESCONOCIDO" in codes
    assert "MUNICIPIO_NO_ENCONTRADO" in codes
    blocked = client.post(
        f"/api/importaciones-geoespaciales/{ready['id_importacion']}/confirmar",
        headers=admin_session,
        json={"aceptar_advertencias": False},
    )
    assert blocked.status_code == 409


def test_revision_manual_corrige_territorio_solo_con_relacion_valida(client, admin_session):
    territory = _territory()
    feature = _feature()
    feature["properties"]["NombreMunicipio"] = f"INEXISTENTE {uuid4().hex}"
    uploaded = _upload(client, admin_session, _geojson(feature))
    ready = _process(client, admin_session, uploaded.json())
    item = client.get(
        f"/api/importaciones-geoespaciales/{ready['id_importacion']}/features?estado=error",
        headers=admin_session,
    ).json()["items"][0]

    partial = client.patch(
        f"/api/importaciones-geoespaciales/{ready['id_importacion']}/features/{item['id_importacion_feature']}",
        headers=admin_session,
        json={"id_entidad": territory["id_entidad"]},
    )
    assert partial.status_code == 422

    corrected = client.patch(
        f"/api/importaciones-geoespaciales/{ready['id_importacion']}/features/{item['id_importacion_feature']}",
        headers=admin_session,
        json={
            "id_entidad": territory["id_entidad"],
            "id_municipio": territory["id_municipio"],
        },
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["estado"] == "valido"
    assert corrected.json()["id_municipio_resuelto"] == territory["id_municipio"]


def test_columnas_desconocidas_requieren_mapeo_manual(client, admin_session):
    territory = _territory()
    properties = {
        "col_a": f"MANUAL {uuid4().hex[:10]}",
        "col_b": "COMUNIDAD",
        "col_c": territory["entidad"],
        "col_d": territory["municipio"],
        "col_e": uuid4().hex,
    }
    uploaded = _upload(client, admin_session, _geojson({"type": "Feature", "properties": properties, "geometry": _polygon()}))
    assert uploaded.status_code == 201
    record = uploaded.json()
    assert "nombre_nucleo" not in record["mapeo"]
    mapping = {
        "nombre_nucleo": "col_a", "tipo_nucleo": "col_b", "entidad": "col_c",
        "municipio": "col_d", "id_nucleo_fuente": "col_e",
    }
    ready = _process(client, admin_session, record, mapping=mapping)
    assert ready["validos"] == 1


def test_kml_valido_es_detectado_por_ogr(client, admin_session):
    territory = _territory()
    name = f"KML {uuid4().hex[:8]}"
    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark>
      <name>{name}</name><ExtendedData>
        <Data name="TipoNucleoAgrario"><value>EJIDO</value></Data>
        <Data name="NombreMunicipio"><value>{territory['municipio']}</value></Data>
        <Data name="NombreEntidadFederativa"><value>{territory['entidad']}</value></Data>
        <Data name="IdNucleoAgrario"><value>{uuid4().hex}</value></Data>
      </ExtendedData><Polygon><outerBoundaryIs><LinearRing><coordinates>
        0,0 0.01,0 0.01,0.01 0,0.01 0,0
      </coordinates></LinearRing></outerBoundaryIs></Polygon>
    </Placemark></Document></kml>'''.encode()
    uploaded = _upload(client, admin_session, b"\xef\xbb\xbf" + kml, filename=f"{uuid4().hex}.kml")
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["formato_detectado"] == "kml"
    assert "4326" in uploaded.json()["crs_original"]


def test_crs_transformable_se_registra_y_normaliza(client, admin_session):
    feature = _feature(geometry={
        "type": "Polygon",
        "coordinates": [[[0, 0], [1000, 0], [1000, 1000], [0, 1000], [0, 0]]],
    })
    uploaded = _upload(client, admin_session, _geojson(feature, crs="EPSG:3857"))
    assert uploaded.status_code == 201, uploaded.text
    assert "3857" in uploaded.json()["crs_original"]
    ready = _process(client, admin_session, uploaded.json())
    item = client.get(
        f"/api/importaciones-geoespaciales/{ready['id_importacion']}/features",
        headers=admin_session,
    ).json()["items"][0]
    assert any(step["codigo"] == "CRS_TRANSFORMADO" for step in item["transformaciones"])


def test_duplicado_y_contradiccion_de_id_externo_bloquean(client, admin_session):
    external_id = uuid4().hex
    first = _feature(name=f"DUP A {uuid4().hex[:8]}", nucleus_id=external_id)
    second = _feature(name=f"DUP B {uuid4().hex[:8]}", nucleus_id=external_id, geometry=_polygon(0.02))
    uploaded = _upload(client, admin_session, _geojson(first, second))
    ready = _process(client, admin_session, uploaded.json())
    assert ready["errores"] == 2
    items = client.get(
        f"/api/importaciones-geoespaciales/{ready['id_importacion']}/features?estado=error",
        headers=admin_session,
    ).json()["items"]
    assert all(any(problem["codigo"] == "ID_EXTERNO_CONTRADICTORIO" for problem in item["errores"]) for item in items)


def test_union_de_partes_requiere_opcion_advertencia_y_aceptacion(client, admin_session, cleanup):
    external_id = uuid4().hex
    name = f"MULTIPARTE {uuid4().hex[:8]}"
    uploaded = _upload(
        client,
        admin_session,
        _geojson(
            _feature(name=name, nucleus_id=external_id),
            _feature(name=name, nucleus_id=external_id, geometry=_polygon(0.02)),
        ),
    )
    ready = _process(
        client,
        admin_session,
        uploaded.json(),
        options={"unir_partes_mismo_id": True},
    )
    assert ready["advertencias"] == 2
    assert ready["errores"] == 0
    blocked = client.post(
        f"/api/importaciones-geoespaciales/{ready['id_importacion']}/confirmar",
        headers=admin_session,
        json={"aceptar_advertencias": False},
    )
    assert blocked.status_code == 409
    accepted = client.post(
        f"/api/importaciones-geoespaciales/{ready['id_importacion']}/confirmar",
        headers=admin_session,
        json={"aceptar_advertencias": True},
    )
    assert accepted.status_code == 202
    page = client.get(
        f"/api/importaciones-geoespaciales/{ready['id_importacion']}/features",
        headers=admin_session,
    ).json()
    nucleus_ids = {item["id_nucleo_operativo"] for item in page["items"]}
    assert len(nucleus_ids) == 1
    cleanup.register("/api/nucleos", nucleus_ids.pop())


def test_seguridad_archivo_extension_nombre_tamano_y_autorizacion(
    client, admin_session, monkeypatch
):
    content = _geojson(_feature())
    fake = _upload(client, admin_session, content, filename="falso.kml")
    assert fake.status_code == 415
    unsupported = _upload(client, admin_session, content, filename="datos.txt")
    assert unsupported.status_code == 415
    invalid = _upload(client, admin_session, b"{contenido invalido", filename="datos.geojson")
    assert invalid.status_code == 422
    malicious = _upload(client, admin_session, content, filename="../datos.geojson")
    assert malicious.status_code == 400
    monkeypatch.setenv("IMPORT_MAX_FILE_SIZE_MB", "0")
    too_large = _upload(client, admin_session, content)
    assert too_large.status_code == 413
    monkeypatch.delenv("IMPORT_MAX_FILE_SIZE_MB")
    with TestClient(app, raise_server_exceptions=False) as anonymous:
        denied = _upload(anonymous, {}, content)
        assert denied.status_code == 401


def test_perfil_y_alias_aprobado_producen_trazabilidad(client, admin_session):
    profile_name = f"Perfil {uuid4().hex}"
    profile = client.post(
        "/api/importaciones-geoespaciales/perfiles",
        headers=admin_session,
        json={
            "nombre": profile_name,
            "fuente": "RAN",
            "mapeo": {"nombre_nucleo": "Name"},
            "opciones": {},
        },
    )
    assert profile.status_code == 201, profile.text
    assert any(item["nombre"] == profile_name for item in client.get(
        "/api/importaciones-geoespaciales/perfiles", headers=admin_session
    ).json())

    territory = _territory()
    alias_name = f"ALIAS {uuid4().hex[:10]}"
    alias = client.post(
        "/api/importaciones-geoespaciales/alias-territoriales",
        headers=admin_session,
        json={
            "id_entidad": territory["id_entidad"],
            "alias_nombre": alias_name,
            "id_municipio_destino": territory["id_municipio"],
            "fuente": "Acta de aprobacion de prueba",
        },
    )
    assert alias.status_code == 201, alias.text
    feature = _feature()
    feature["properties"]["NombreMunicipio"] = alias_name
    uploaded = _upload(client, admin_session, _geojson(feature))
    ready = _process(client, admin_session, uploaded.json())
    assert ready["advertencias"] == 1
    item = client.get(
        f"/api/importaciones-geoespaciales/{ready['id_importacion']}/features",
        headers=admin_session,
    ).json()["items"][0]
    assert item["advertencias"][0]["codigo"] == "ALIAS_TERRITORIAL_APLICADO"


def test_geometrias_polygon_multi_collection_3d_y_reparacion_controlada():
    layer = LayerInfo("test", 1, (), "EPSG:4326", True)
    with SessionLocal() as db:
        polygon = service._normalize_geometry(db, _polygon(), layer, None)
        assert not polygon[4]
        multi = service._normalize_geometry(
            db, {"type": "MultiPolygon", "coordinates": [_polygon()["coordinates"]]}, layer, None
        )
        assert not multi[4]
        collection = service._normalize_geometry(
            db, {"type": "GeometryCollection", "geometries": [_polygon()]}, layer, None
        )
        assert not collection[4]
        three_d = service._normalize_geometry(db, _polygon(z=True), layer, None)
        assert any(step["codigo"] == "FORCE_2D" for step in three_d[6])
        bowtie = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]],
        }
        repaired_without_policy = service._normalize_geometry(db, bowtie, layer, None)
        assert any(problem["codigo"] == "TOLERANCIA_AREA_NO_CONFIGURADA" for problem in repaired_without_policy[4])
        repaired_strict = service._normalize_geometry(db, bowtie, layer, Decimal("0"))
        assert any(problem["codigo"] == "REPARACION_SUPERA_TOLERANCIA" for problem in repaired_strict[4])
        repair_without_area_change = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [2, 0], [1, 1], [2, 2], [0, 2], [1, 1], [0, 0]]],
        }
        repaired_allowed = service._normalize_geometry(
            db, repair_without_area_change, layer, Decimal("0")
        )
        assert not repaired_allowed[4]
        assert any(problem["codigo"] == "GEOMETRIA_REPARADA" for problem in repaired_allowed[5])
        non_polygon = service._normalize_geometry(
            db, {"type": "Point", "coordinates": [0, 0]}, layer, None
        )
        assert non_polygon[4][0]["codigo"] == "TIPO_GEOMETRIA_NO_PERMITIDO"


def test_crs_desconocido_bloquea(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.services.gis_ingestion._run_json",
        lambda _: {
            "driverShortName": "GeoJSON",
            "layers": [{"name": "sin_crs", "featureCount": 1, "fields": [], "geometryFields": [{}]}],
        },
    )
    source = tmp_path / "sin-crs.geojson"
    source.write_text("{}")
    with pytest.raises(IngestionError) as error:
        inspect_dataset(source)
    assert error.value.code == "CRS_DESCONOCIDO"


def test_resolucion_territorial_prioriza_claves_y_detecta_ambiguedad():
    entity_a = SimpleNamespace(id_entidad=1, clave_inegi="01", nombre="Entidad A")
    entity_b = SimpleNamespace(id_entidad=2, clave_inegi="02", nombre="Entidad B")
    municipality_a = SimpleNamespace(id_municipio=10, id_entidad=1, clave_inegi="01001", nombre="Centro")
    municipality_a_duplicate = SimpleNamespace(id_municipio=11, id_entidad=1, clave_inegi="01002", nombre="Centro")
    municipality_b = SimpleNamespace(id_municipio=20, id_entidad=2, clave_inegi="02001", nombre="Centro")
    catalogs = {
        "entities_by_code": {"01": entity_a, "02": entity_b},
        "entities_by_name": {"entidad a": [entity_a], "entidad b": [entity_b]},
        "municipalities_by_code": {
            "01001": municipality_a,
            "01002": municipality_a_duplicate,
            "02001": municipality_b,
        },
        "municipalities_by_id": {10: municipality_a, 11: municipality_a_duplicate, 20: municipality_b},
        "municipalities_by_entity_name": {
            (1, "centro"): [municipality_a, municipality_a_duplicate],
            (2, "centro"): [municipality_b],
        },
        "aliases": {},
    }
    _, by_full_code, errors, _ = service._resolve_territory(
        {"clave_entidad_inegi": "01", "clave_municipio_inegi": "01001"}, {}, catalogs
    )
    assert by_full_code.id_municipio == 10
    assert not errors
    _, by_external_code, errors, _ = service._resolve_territory(
        {"entidad": "Entidad B", "id_municipio_fuente": "1"},
        {"id_municipio_fuente_semantica": "clave_municipal_inegi"},
        catalogs,
    )
    assert by_external_code.id_municipio == 20
    assert not errors
    _, by_name_other_entity, errors, _ = service._resolve_territory(
        {"entidad": "Entidad B", "municipio": "Centro"}, {}, catalogs
    )
    assert by_name_other_entity.id_municipio == 20
    assert not errors
    _, ambiguous, errors, _ = service._resolve_territory(
        {"entidad": "Entidad A", "municipio": "Centro"}, {}, catalogs
    )
    assert ambiguous is None
    assert errors[0]["codigo"] == "MUNICIPIO_AMBIGUO"


def test_identidad_externa_territorial_usa_municipio_resuelto():
    record = SimpleNamespace(
        fuente="RAN",
        opciones_mapeo={"alcance_id_nucleo_fuente": "territorial"},
    )
    first = SimpleNamespace(id_nucleo_fuente="7", id_municipio_resuelto=10)
    same_municipality = SimpleNamespace(id_nucleo_fuente="7", id_municipio_resuelto=10)
    other_municipality = SimpleNamespace(id_nucleo_fuente="7", id_municipio_resuelto=20)

    assert service._external_identity(record, first) == service._external_identity(record, same_municipality)
    assert service._external_identity(record, first) != service._external_identity(record, other_municipality)

    record.opciones_mapeo = {"alcance_id_nucleo_fuente": "global"}
    assert service._external_identity(record, first) == service._external_identity(record, other_municipality)


def test_dos_confirmaciones_de_servicio_no_duplican(client, admin_session, cleanup):
    name = f"CONCURRENCIA {uuid4().hex[:10]}"
    uploaded = _upload(client, admin_session, _geojson(_feature(name=name)))
    ready = _process(client, admin_session, uploaded.json())
    with SessionLocal() as db:
        user_id = db.query(models.Usuario.id_usuario).filter(models.Usuario.rol == "admin", models.Usuario.activo.is_(True)).order_by(models.Usuario.id_usuario).first()[0]
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: service.confirm_import(ready["id_importacion"], user_id, False), range(2)))
    with SessionLocal() as db:
        rows = db.query(models.NucleoAgrario).filter(models.NucleoAgrario.nombre_nucleo == name, models.NucleoAgrario.activo.is_(True)).all()
        assert len(rows) == 1
        cleanup.register("/api/nucleos", rows[0].id_nucleo)


def test_falla_operativa_revierte_el_registro_y_conserva_error_en_staging(
    client, admin_session, monkeypatch
):
    name = f"ROLLBACK {uuid4().hex[:10]}"
    uploaded = _upload(client, admin_session, _geojson(_feature(name=name)))
    ready = _process(client, admin_session, uploaded.json())
    original_import_group = service._import_group

    def fail_after_flush(db, record, group, user_id):
        original_import_group(db, record, group, user_id)
        raise IntegrityError("forced", {}, RuntimeError("forced"))

    monkeypatch.setattr(service, "_import_group", fail_after_flush)
    response = client.post(
        f"/api/importaciones-geoespaciales/{ready['id_importacion']}/confirmar",
        headers=admin_session,
        json={"aceptar_advertencias": False},
    )
    assert response.status_code == 202
    with SessionLocal() as db:
        assert db.query(models.NucleoAgrario).filter(
            models.NucleoAgrario.nombre_nucleo == name,
            models.NucleoAgrario.activo.is_(True),
        ).count() == 0
        feature = db.query(models.ImportacionFeature).filter_by(
            id_importacion=ready["id_importacion"]
        ).one()
        assert feature.estado == "error"
        assert any(item["codigo"] == "FALLO_IMPORTACION_OPERATIVA" for item in feature.errores)


def test_rutas_legacy_de_nucleos_no_escriben(client, admin_session):
    content = _geojson(_feature())
    old_direct = client.post(
        "/api/nucleos/importacion-masiva",
        headers=admin_session,
        files={"file": ("old.geojson", content, "application/json")},
    )
    old_preview = client.post(
        "/api/importaciones-territoriales/nucleos/previsualizar",
        headers=admin_session,
        files={"file": ("old.geojson", content, "application/json")},
    )
    assert old_direct.status_code == 410
    assert old_preview.status_code == 410


def test_no_existen_rutas_duplicadas():
    signatures = [
        (tuple(sorted(route.methods or [])), route.path)
        for route in app.routes
        if hasattr(route, "methods")
    ]
    assert len(signatures) == len(set(signatures))
