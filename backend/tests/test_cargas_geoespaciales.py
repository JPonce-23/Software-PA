"""Pruebas de la carga geoespacial comun para capturas operativas."""

import json
from uuid import uuid4

from app import models
from app.database import SessionLocal


def _feature(geometry, properties=None):
    return {
        "type": "Feature",
        "properties": properties or {},
        "geometry": geometry,
    }


def _geojson(*features):
    return json.dumps({"type": "FeatureCollection", "features": list(features)}).encode()


def _utm14_geojson(*features):
    return json.dumps({
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:32614"}},
        "features": list(features),
    }).encode()


def _polygon():
    return {
        "type": "Polygon",
        "coordinates": [[
            [0, 0], [0.01, 0], [0.01, 0.01], [0, 0.01], [0, 0],
        ]],
    }


def _line():
    return {"type": "LineString", "coordinates": [[0, 0], [0.01, 0.01]]}


def _second_line():
    return {"type": "LineString", "coordinates": [[0.01, 0.01], [0.02, 0.02]]}


def _utm14_line(start_easting, end_easting):
    return {
        "type": "MultiLineString",
        "coordinates": [[
            [start_easting, 2500000, 12],
            [end_easting, 2500000, 14],
        ]],
    }


def _upload(client, headers, target, content):
    return client.post(
        "/api/cargas-geoespaciales",
        headers=headers,
        data={"tipo_objetivo": target, "fuente": "Prueba de staging"},
        files={"file": (f"{target}-{uuid4().hex}.geojson", content, "application/geo+json")},
    )


def test_staging_de_nucleo_no_escribe_y_feature_no_se_reutiliza(
    client, admin_session, seed_municipio_id, cleanup
):
    name = f"Nucleo desde staging {uuid4().hex[:10]}"
    uploaded = _upload(client, admin_session, "nucleo_agrario", _geojson(_feature(_polygon())))
    assert uploaded.status_code == 201, uploaded.text
    record = uploaded.json()
    assert record["estado"] == "listo_revision"
    assert record["features_validos"] == 1
    feature_id = record["features"][0]["id_carga_feature"]

    with SessionLocal() as db:
        assert db.query(models.NucleoAgrario).filter_by(nombre_nucleo=name).count() == 0

    blocked = client.post(
        "/api/nucleos",
        headers=admin_session,
        json={
            "id_municipio": seed_municipio_id,
            "nombre_nucleo": name,
            "tipo_nucleo": "ejido",
            "id_carga_geoespacial_feature": feature_id,
        },
    )
    assert blocked.status_code == 422

    confirmed = client.post(
        f"/api/cargas-geoespaciales/{record['id_carga']}/confirmar",
        headers=admin_session,
        json={"id_carga_feature": feature_id},
    )
    assert confirmed.status_code == 200, confirmed.text

    created = client.post(
        "/api/nucleos",
        headers=admin_session,
        json={
            "id_municipio": seed_municipio_id,
            "nombre_nucleo": name,
            "tipo_nucleo": "ejido",
            "id_carga_geoespacial_feature": feature_id,
        },
    )
    assert created.status_code == 201, created.text
    cleanup.register("/api/nucleos", created.json()["id_nucleo"])

    repeated = client.post(
        "/api/nucleos",
        headers=admin_session,
        json={
            "id_municipio": seed_municipio_id,
            "nombre_nucleo": f"Duplicado {uuid4().hex[:10]}",
            "tipo_nucleo": "ejido",
            "id_carga_geoespacial_feature": feature_id,
        },
    )
    assert repeated.status_code == 409


def test_staging_exige_geometria_del_tipo_del_objetivo(client, admin_session):
    uploaded = _upload(client, admin_session, "seccion_derecho_via", _geojson(_feature(_line())))
    assert uploaded.status_code == 201, uploaded.text
    record = uploaded.json()
    feature = record["features"][0]
    assert record["features_error"] == 1
    assert feature["estado"] == "error"
    assert feature["errores"][0]["codigo"] == "TIPO_GEOMETRIA"


def test_trazo_segmentado_se_guarda_despues_de_confirmar_sin_fuente_ni_anchos(
    client, admin_session, cleanup
):
    suffix = uuid4().hex[:10]
    project = client.post(
        "/api/proyectos",
        headers=admin_session,
        json={
            "clave_proyecto": f"TRZ-{suffix}",
            "nombre_proyecto": f"Proyecto trazo segmentado {suffix}",
        },
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id_proyecto"]
    cleanup.register("/api/proyectos", project_id)

    uploaded = _upload(
        client,
        admin_session,
        "franja_derecho_via",
        _utm14_geojson(
            _feature(_utm14_line(400000, 400100)),
            _feature(_utm14_line(400100, 400200)),
        ),
    )
    assert uploaded.status_code == 201, uploaded.text
    record = uploaded.json()
    assert record["tipo_geometria_esperado"] == "trazo"
    assert record["features_validos"] == 2
    assert record["features_error"] == 0
    assert {feature["tipo_geometria"] for feature in record["features"]} == {"MultiLineString"}
    feature_id = record["features"][0]["id_carga_feature"]

    confirmed = client.post(
        f"/api/cargas-geoespaciales/{record['id_carga']}/confirmar",
        headers=admin_session,
        json={"id_carga_feature": feature_id},
    )
    assert confirmed.status_code == 200, confirmed.text

    imported = client.post(
        f"/api/proyectos/{project_id}/franjas/importar",
        headers=admin_session,
        json={
            "fecha_vigencia_inicio": "2026-08-17",
            "id_carga_geoespacial_feature": feature_id,
        },
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["geometria_wkt"].startswith("MULTILINESTRING")

    with SessionLocal() as db:
        feature = db.get(models.CargaGeoespacialFeature, feature_id)
        franja = db.get(models.FranjaDerechoVia, imported.json()["id_franja"])
        assert feature.id_registro_operativo == imported.json()["id_franja"]
        assert franja.ancho_izquierdo_m is None
        assert franja.ancho_derecho_m is None
        assert franja.geometria_linea is not None
        assert {item["codigo"] for item in feature.transformaciones} >= {"UNION_SEGMENTOS_TRAZO"}


def test_candidatos_requieren_revision_antes_de_crear_expediente(
    client, admin_session, cleanup, seed_municipio_id
):
    suffix = uuid4().hex[:10]
    project = client.post(
        "/api/proyectos",
        headers=admin_session,
        json={"clave_proyecto": f"CG-{suffix}", "nombre_proyecto": f"Proyecto candidatos {suffix}"},
    )
    assert project.status_code == 201, project.text
    cleanup.register("/api/proyectos", project.json()["id_proyecto"])
    tramo = client.post(
        "/api/tramos",
        headers=admin_session,
        json={
            "id_proyecto": project.json()["id_proyecto"],
            "clave_tramo": f"CG-{suffix}",
            "nombre_tramo": f"Tramo candidatos {suffix}",
            "geometria_wkt": "MULTILINESTRING((0 0, 1 1))",
        },
    )
    assert tramo.status_code == 201, tramo.text
    cleanup.register("/api/tramos", tramo.json()["id_tramo"])
    franja = client.post(
        f"/api/tramos/{tramo.json()['id_tramo']}/franjas/importar",
        headers=admin_session,
        json={
            "fuente": "Franja de prueba de candidatos",
            "fecha_vigencia_inicio": "2026-01-01",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        },
    )
    assert franja.status_code == 201, franja.text
    seccion = client.post(
        f"/api/tramos/{tramo.json()['id_tramo']}/secciones-derecho-via/importar",
        headers=admin_session,
        json={
            "fuente": "Sección de prueba de candidatos",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        },
    )
    assert seccion.status_code == 201, seccion.text
    nucleo = client.post(
        "/api/nucleos",
        headers=admin_session,
        json={
            "id_municipio": seed_municipio_id,
            "nombre_nucleo": f"Nucleo candidatos {suffix}",
            "tipo_nucleo": "ejido",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        },
    )
    assert nucleo.status_code == 201, nucleo.text
    cleanup.register("/api/nucleos", nucleo.json()["id_nucleo"])

    detected = client.post(
        f"/api/cargas-geoespaciales/tramos/{tramo.json()['id_tramo']}/candidatos/detectar",
        headers=admin_session,
    )
    assert detected.status_code == 200, detected.text
    candidates = client.get(
        f"/api/cargas-geoespaciales/tramos/{tramo.json()['id_tramo']}/candidatos",
        headers=admin_session,
    )
    assert candidates.status_code == 200, candidates.text
    candidate = next(item for item in candidates.json() if item["id_nucleo"] == nucleo.json()["id_nucleo"])

    with SessionLocal() as db:
        assert not db.query(models.TramoNucleo).filter_by(
            id_tramo=tramo.json()["id_tramo"], id_nucleo=nucleo.json()["id_nucleo"], activo=True
        ).first()

    accepted = client.post(
        f"/api/cargas-geoespaciales/candidatos/{candidate['id_candidato']}/confirmar",
        headers=admin_session,
        json={"consecutivo": int(uuid4().int % 100000000) + 1},
    )
    assert accepted.status_code == 200, accepted.text
    cleanup.register("/api/tramos-nucleos", accepted.json()["id_tramo_nucleo"])


def test_importador_directo_esta_retirado(client, admin_session):
    response = client.post(
        "/api/geometria/importar-geojson?tipo_entidad=tramo",
        headers=admin_session,
        files={"file": ("tramo.geojson", _geojson(_feature(_line())), "application/geo+json")},
    )
    assert response.status_code == 410
