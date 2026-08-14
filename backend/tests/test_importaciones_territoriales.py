import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import models
from app.config import AUTH_SETTINGS
from app.database import SessionLocal
from app.main import app


TEST_PASSWORD = "PruebaGeo!2026"
ORIGIN = AUTH_SETTINGS.allowed_origins[0]


def _feature(properties, geometry):
    return {"type": "Feature", "properties": properties, "geometry": geometry}


def _collection(*features):
    content = json.dumps({"type": "FeatureCollection", "features": list(features)})
    return {"file": ("import.json", content, "application/json")}


def _line(x_offset=0):
    return {
        "type": "LineString",
        "coordinates": [[x_offset, 0], [x_offset + 0.5, 0.5]],
    }


def _polygon(x_offset=0):
    return {
        "type": "Polygon",
        "coordinates": [[
            [x_offset, 0],
            [x_offset + 0.5, 0],
            [x_offset + 0.5, 0.5],
            [x_offset, 0.5],
            [x_offset, 0],
        ]],
    }


def _create_user(client, admin_session, cleanup, role):
    email = f"{role}-imp-{uuid4().hex}@pa.test"
    response = client.post(
        "/api/usuarios",
        headers=admin_session,
        json={
            "nombre": "Prueba",
            "apellido_paterno": "Importacion",
            "correo": email,
            "rol": role,
            "contrasena": TEST_PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    cleanup.register("/api/usuarios", data["id_usuario"])
    return data


def _tamaulipas_context():
    db = SessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT e.id_entidad, m.nombre AS municipio
                  FROM entidad_federativa e
                  JOIN municipio m ON m.id_entidad = e.id_entidad
                 WHERE e.nombre = 'Tamaulipas'
                   AND e.activo = TRUE
                   AND m.activo = TRUE
                 ORDER BY m.nombre
                 LIMIT 1
                """
            )
        ).mappings().first()
        assert row is not None
        return row
    finally:
        db.close()


def _login(email):
    browser = TestClient(app, raise_server_exceptions=False)
    login = browser.post(
        "/api/auth/sesiones",
        data={"username": email, "password": TEST_PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert login.status_code == 200, login.text
    return browser, {"Origin": ORIGIN, "X-CSRF-Token": browser.cookies.get(AUTH_SETTINGS.csrf_cookie_name)}


def test_tramos_preview_no_escribe_y_confirm_geografo_asigna(
    client,
    admin_session,
    cleanup,
    seed_proyecto,
):
    geografo = _create_user(client, admin_session, cleanup, "geografo")
    browser, headers = _login(geografo["correo"])
    clave = f"GEOIMP-{uuid4().hex[:8]}"
    try:
        preview = browser.post(
            "/api/importaciones-territoriales/tramos/previsualizar",
            headers=headers,
            data={"id_proyecto": str(seed_proyecto["id_proyecto"])},
            files=_collection(_feature({"clave_tramo": clave, "nombre_tramo": "Tramo importado"}, _line())),
        )
        assert preview.status_code == 200, preview.text
        assert preview.json()["validos"] == 1
        assert preview.json()["errores"] == 0

        before = client.get(
            f"/api/tramos?id_proyecto={seed_proyecto['id_proyecto']}",
            headers=admin_session,
        )
        assert all(item["clave_tramo"] != clave for item in before.json())

        confirmed = browser.post(
            "/api/importaciones-territoriales/tramos/confirmar",
            headers=headers,
            json={"archivo_sha256": preview.json()["archivo_sha256"], "items": preview.json()["items"]},
        )
        assert confirmed.status_code == 200, confirmed.text
        tramo_id = confirmed.json()["ids_creados"][0]
        cleanup.register("/api/tramos", tramo_id)

        assignments = client.get(
            f"/api/administracion/tramos/{tramo_id}/asignaciones",
            headers=admin_session,
        )
        assert assignments.status_code == 200, assignments.text
        assert [item["id_usuario"] for item in assignments.json()] == [geografo["id_usuario"]]
    finally:
        browser.post("/api/auth/logout", headers=headers)
        browser.close()


def test_confirmacion_revalida_y_revierte_tramos_si_hay_error(
    client,
    admin_session,
    seed_proyecto,
):
    clave_a = f"RBKIMP-{uuid4().hex[:8]}"
    clave_b = f"RBKIMP-{uuid4().hex[:8]}"
    preview = client.post(
        "/api/importaciones-territoriales/tramos/previsualizar",
        headers=admin_session,
        data={"id_proyecto": str(seed_proyecto["id_proyecto"])},
        files=_collection(
            _feature({"clave_tramo": clave_a, "nombre_tramo": "Rollback A"}, _line()),
            _feature({"clave_tramo": clave_b, "nombre_tramo": "Rollback B"}, _line()),
        ),
    )
    assert preview.status_code == 200, preview.text
    payload = preview.json()
    payload["items"][1]["datos"]["properties"]["clave_tramo"] = clave_a
    payload["items"][1]["datos"]["clave_tramo"] = clave_a

    confirmed = client.post(
        "/api/importaciones-territoriales/tramos/confirmar",
        headers=admin_session,
        json={"archivo_sha256": payload["archivo_sha256"], "items": payload["items"]},
    )
    assert confirmed.status_code == 400

    tramos = client.get(
        f"/api/tramos?id_proyecto={seed_proyecto['id_proyecto']}",
        headers=admin_session,
    )
    claves = {item["clave_tramo"] for item in tramos.json()}
    assert clave_a not in claves
    assert clave_b not in claves


def test_operador_no_puede_importar_territorio(client, admin_session, cleanup):
    operador = _create_user(client, admin_session, cleanup, "operador")
    browser, headers = _login(operador["correo"])
    try:
        response = browser.post(
            "/api/importaciones-territoriales/tramos/previsualizar",
            headers=headers,
            data={"id_proyecto": "1"},
            files=_collection(_feature({"clave_tramo": "DEN", "nombre_tramo": "Denegado"}, _line())),
        )
        assert response.status_code == 403
    finally:
        browser.post("/api/auth/logout", headers=headers)
        browser.close()


def test_parcelas_importan_geometria_sin_titular_automatico(
    client,
    admin_session,
    cleanup,
    seed_nucleo,
):
    no_ppt = f"PIMP-{uuid4().hex[:8]}"
    preview = client.post(
        "/api/importaciones-territoriales/parcelas/previsualizar",
        headers=admin_session,
        data={"id_nucleo": str(seed_nucleo["id_nucleo"])},
        files=_collection(_feature({
            "tipo_parcela": "individual",
            "no_parcela_ppt": no_ppt,
            "nombre_titular": "No debe crear persona",
        }, _polygon())),
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["advertencias"] == 1

    confirmed = client.post(
        "/api/importaciones-territoriales/parcelas/confirmar",
        headers=admin_session,
        json={"archivo_sha256": preview.json()["archivo_sha256"], "items": preview.json()["items"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    parcela_id = confirmed.json()["ids_creados"][0]
    cleanup.register("/api/parcelas", parcela_id)

    db = SessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT nombre_titular, ST_AsText(geometria_poligono) AS wkt
                  FROM parcela
                 WHERE id_parcela = :id_parcela
                """
            ),
            {"id_parcela": parcela_id},
        ).mappings().one()
        assert row["nombre_titular"] is None
        assert row["wkt"].startswith("MULTIPOLYGON")
    finally:
        db.close()


@pytest.mark.skip(reason="El endpoint legacy de nucleos fue retirado por el staging 020")
def test_nucleos_territorio_acepta_alias_name_y_tipo_predeterminado(
    client,
    admin_session,
    cleanup,
    seed_municipio_id,
):
    nombre = f"Nucleo alias {uuid4().hex[:8]}"
    preview = client.post(
        "/api/importaciones-territoriales/nucleos/previsualizar",
        headers=admin_session,
        data={
            "id_municipio_fallback": str(seed_municipio_id),
            "tipo_nucleo_fallback": "ejido",
        },
        files=_collection(_feature({"Name": nombre}, _polygon())),
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["validos"] == 1
    assert preview.json()["errores"] == 0

    confirmed = client.post(
        "/api/importaciones-territoriales/nucleos/confirmar",
        headers=admin_session,
        json={"archivo_sha256": preview.json()["archivo_sha256"], "items": preview.json()["items"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    cleanup.register("/api/nucleos", confirmed.json()["ids_creados"][0])


@pytest.mark.skip(reason="El endpoint legacy de nucleos fue retirado por el staging 020")
def test_nucleos_contexto_usa_franja_aunque_no_cruce_linea(
    client,
    admin_session,
    cleanup,
    seed_tramo,
    seed_municipio_id,
):
    nombre = f"Nucleo borde franja {uuid4().hex[:8]}"
    geometry = {
        "type": "Polygon",
        "coordinates": [[
            [0.75, 0.05],
            [0.90, 0.05],
            [0.90, 0.20],
            [0.75, 0.20],
            [0.75, 0.05],
        ]],
    }
    preview = client.post(
        "/api/importaciones-territoriales/nucleos/previsualizar",
        headers=admin_session,
        data={
            "id_municipio_fallback": str(seed_municipio_id),
            "tipo_nucleo_fallback": "ejido",
            "ids_tramo_contexto": str(seed_tramo["id_tramo"]),
        },
        files=_collection(_feature({"nombre_nucleo": nombre}, geometry)),
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["validos"] == 1

    confirmed = client.post(
        "/api/importaciones-territoriales/nucleos/confirmar",
        headers=admin_session,
        json={
            "archivo_sha256": preview.json()["archivo_sha256"],
            "items": preview.json()["items"],
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    cleanup.register("/api/nucleos", confirmed.json()["ids_creados"][0])


@pytest.mark.skip(reason="El endpoint legacy de nucleos fue retirado por el staging 020")
def test_nucleos_territorio_resuelve_tamaulipas_por_entidad_y_municipio(
    client,
    admin_session,
    cleanup,
):
    tamaulipas = _tamaulipas_context()
    preview = client.post(
        "/api/importaciones-territoriales/nucleos/previsualizar",
        headers=admin_session,
        data={
            "id_entidad_fallback": str(tamaulipas["id_entidad"]),
            "tipo_nucleo_fallback": "ejido",
        },
        files=_collection(_feature({
            "Name": f"Nucleo Tamps {uuid4().hex[:8]}",
            "MUNICIPIO": tamaulipas["municipio"],
        }, _polygon())),
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["validos"] == 1

    confirmed = client.post(
        "/api/importaciones-territoriales/nucleos/confirmar",
        headers=admin_session,
        json={"archivo_sha256": preview.json()["archivo_sha256"], "items": preview.json()["items"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    cleanup.register("/api/nucleos", confirmed.json()["ids_creados"][0])


@pytest.mark.skip(reason="El endpoint legacy de nucleos fue retirado por el staging 020")
def test_nucleos_territorio_fusiona_features_del_mismo_nucleo(
    client,
    admin_session,
    cleanup,
):
    tamaulipas = _tamaulipas_context()
    nombre = f"Nucleo multipart {uuid4().hex[:8]}"
    preview = client.post(
        "/api/importaciones-territoriales/nucleos/previsualizar",
        headers=admin_session,
        data={
            "id_entidad_fallback": str(tamaulipas["id_entidad"]),
            "tipo_nucleo_fallback": "ejido",
        },
        files=_collection(
            _feature({"Name": nombre, "MUNICIPIO": tamaulipas["municipio"]}, _polygon(0)),
            _feature({"Name": nombre, "MUNICIPIO": tamaulipas["municipio"]}, _polygon(2)),
            _feature({"Name": f"{nombre} distinto", "MUNICIPIO": tamaulipas["municipio"]}, _polygon(4)),
        ),
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["validos"] == 2
    assert body["errores"] == 0
    grouped = next(item for item in body["items"] if item["resumen"] == nombre)
    assert grouped["estado"] == "advertencia"
    assert grouped["datos"]["features_agrupadas"] == 2
    assert grouped["datos"]["indices_origen"] == [0, 1]

    confirmed = client.post(
        "/api/importaciones-territoriales/nucleos/confirmar",
        headers=admin_session,
        json={"archivo_sha256": body["archivo_sha256"], "items": body["items"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    ids = confirmed.json()["ids_creados"]
    assert len(ids) == 2
    for id_nucleo in ids:
        cleanup.register("/api/nucleos", id_nucleo)

    db = SessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT ST_GeometryType(geometria_poligono) AS geometry_type,
                       ST_NumGeometries(geometria_poligono) AS parts
                  FROM nucleo_agrario
                 WHERE id_nucleo = :id_nucleo
                """
            ),
            {"id_nucleo": ids[0]},
        ).mappings().one()
        assert row["geometry_type"] == "ST_MultiPolygon"
        assert row["parts"] == 2
    finally:
        db.close()


@pytest.mark.skip(reason="El endpoint legacy de nucleos fue retirado por el staging 020")
def test_nucleos_territorio_rechaza_nombre_existente_en_mismo_municipio(
    client,
    admin_session,
    cleanup,
    seed_municipio_id,
):
    nombre = f"Nucleo duplicado {uuid4().hex[:8]}"
    first = client.post(
        "/api/importaciones-territoriales/nucleos/previsualizar",
        headers=admin_session,
        data={
            "id_municipio_fallback": str(seed_municipio_id),
            "tipo_nucleo_fallback": "ejido",
        },
        files=_collection(_feature({"Name": nombre}, _polygon(0))),
    )
    assert first.status_code == 200, first.text
    confirmed = client.post(
        "/api/importaciones-territoriales/nucleos/confirmar",
        headers=admin_session,
        json={"archivo_sha256": first.json()["archivo_sha256"], "items": first.json()["items"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    cleanup.register("/api/nucleos", confirmed.json()["ids_creados"][0])

    second = client.post(
        "/api/importaciones-territoriales/nucleos/previsualizar",
        headers=admin_session,
        data={
            "id_municipio_fallback": str(seed_municipio_id),
            "tipo_nucleo_fallback": "ejido",
        },
        files=_collection(_feature({"Name": nombre.upper()}, _polygon(2))),
    )
    assert second.status_code == 409


@pytest.mark.skip(reason="El endpoint legacy de nucleos fue retirado por el staging 020")
def test_nucleos_territorio_ignora_id_municipio_externo_si_resuelve_nombre(
    client,
    admin_session,
    cleanup,
):
    tamaulipas = _tamaulipas_context()
    preview = client.post(
        "/api/importaciones-territoriales/nucleos/previsualizar",
        headers=admin_session,
        data={
            "id_entidad_fallback": str(tamaulipas["id_entidad"]),
            "tipo_nucleo_fallback": "ejido",
        },
        files=_collection(_feature({
            "Name": f"Nucleo Tamps externo {uuid4().hex[:8]}",
            "id_municipio": "999999",
            "MUNICIPIO": tamaulipas["municipio"],
        }, _polygon())),
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["validos"] == 1

    confirmed = client.post(
        "/api/importaciones-territoriales/nucleos/confirmar",
        headers=admin_session,
        json={"archivo_sha256": preview.json()["archivo_sha256"], "items": preview.json()["items"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    cleanup.register("/api/nucleos", confirmed.json()["ids_creados"][0])


@pytest.mark.skip(reason="El endpoint legacy de nucleos fue retirado por el staging 020")
def test_nucleos_territorio_sin_municipio_muestra_error_de_resolucion(
    client,
    admin_session,
):
    preview = client.post(
        "/api/importaciones-territoriales/nucleos/previsualizar",
        headers=admin_session,
        data={"tipo_nucleo_fallback": "ejido"},
        files=_collection(_feature({
            "Name": f"Nucleo sin municipio {uuid4().hex[:8]}",
        }, _polygon())),
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["errores"] == 1
    detalle = "\n".join(body["items"][0]["errores"])
    assert "No se pudo resolver el municipio" in detalle
    assert "id_municipio_fallback es obligatorio" not in detalle


@pytest.mark.skip(reason="El endpoint legacy de nucleos fue retirado por el staging 020")
def test_nucleos_mapa_acepta_alias_name_y_tipo_predeterminado(
    client,
    admin_session,
    cleanup,
    seed_municipio_id,
):
    nombre = f"Nucleo mapa alias {uuid4().hex[:8]}"
    imported = client.post(
        "/api/nucleos/importacion-masiva",
        headers=admin_session,
        data={
            "id_municipio_fallback": str(seed_municipio_id),
            "tipo_nucleo_fallback": "ejido",
        },
        files=_collection(_feature({"Name": nombre}, _polygon())),
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["total"] == 1
    cleanup.register("/api/nucleos", imported.json()["ids_nucleo"][0])


@pytest.mark.skip(reason="El endpoint legacy de nucleos fue retirado por el staging 020")
def test_nucleos_mapa_resuelve_tamaulipas_por_entidad_y_municipio(
    client,
    admin_session,
    cleanup,
):
    tamaulipas = _tamaulipas_context()
    imported = client.post(
        "/api/nucleos/importacion-masiva",
        headers=admin_session,
        data={
            "id_entidad_fallback": str(tamaulipas["id_entidad"]),
            "tipo_nucleo_fallback": "ejido",
        },
        files=_collection(_feature({
            "Name": f"Nucleo mapa Tamps {uuid4().hex[:8]}",
            "MUNICIPIO": tamaulipas["municipio"],
        }, _polygon())),
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["total"] == 1
    cleanup.register("/api/nucleos", imported.json()["ids_nucleo"][0])


@pytest.mark.skip(reason="El endpoint legacy de nucleos fue retirado por el staging 020")
def test_nucleos_mapa_fusiona_features_del_mismo_nucleo(
    client,
    admin_session,
    cleanup,
    seed_municipio_id,
):
    nombre = f"Nucleo mapa multipart {uuid4().hex[:8]}"
    imported = client.post(
        "/api/nucleos/importacion-masiva",
        headers=admin_session,
        data={
            "id_municipio_fallback": str(seed_municipio_id),
            "tipo_nucleo_fallback": "ejido",
        },
        files=_collection(
            _feature({"Name": nombre}, _polygon(0)),
            _feature({"Name": nombre}, _polygon(2)),
        ),
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["total"] == 1
    id_nucleo = imported.json()["ids_nucleo"][0]
    cleanup.register("/api/nucleos", id_nucleo)

    db = SessionLocal()
    try:
        parts = db.execute(
            text(
                """
                SELECT ST_NumGeometries(geometria_poligono)
                  FROM nucleo_agrario
                 WHERE id_nucleo = :id_nucleo
                """
            ),
            {"id_nucleo": id_nucleo},
        ).scalar_one()
        assert parts == 2
    finally:
        db.close()


@pytest.mark.skip(reason="El endpoint legacy de nucleos fue retirado por el staging 020")
def test_nucleos_mapa_ignora_id_municipio_externo_si_resuelve_nombre(
    client,
    admin_session,
    cleanup,
):
    tamaulipas = _tamaulipas_context()
    imported = client.post(
        "/api/nucleos/importacion-masiva",
        headers=admin_session,
        data={
            "id_entidad_fallback": str(tamaulipas["id_entidad"]),
            "tipo_nucleo_fallback": "ejido",
        },
        files=_collection(_feature({
            "Name": f"Nucleo mapa externo {uuid4().hex[:8]}",
            "id_municipio": "999999",
            "MUNICIPIO": tamaulipas["municipio"],
        }, _polygon())),
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["total"] == 1
    cleanup.register("/api/nucleos", imported.json()["ids_nucleo"][0])


def test_cruces_operativos_admin_only_y_confirmacion_explicitamente_crea(
    client,
    admin_session,
    cleanup,
    seed_tramo,
    seed_municipio_id,
):
    geografo = _create_user(client, admin_session, cleanup, "geografo")
    browser, headers = _login(geografo["correo"])
    try:
        denied = browser.post(
            "/api/importaciones-territoriales/cruces_operativos/previsualizar",
            headers=headers,
            data={"id_tramo": str(seed_tramo["id_tramo"]), "id_nucleo": "1"},
            files=_collection(_feature({"consecutivo": 99999}, _line())),
        )
        assert denied.status_code == 403
    finally:
        browser.post("/api/auth/logout", headers=headers)
        browser.close()

    nucleo = client.post(
        "/api/nucleos",
        headers=admin_session,
        json={
            "id_municipio": seed_municipio_id,
            "nombre_nucleo": f"Nucleo cruce {uuid4().hex[:8]}",
            "tipo_nucleo": "ejido",
            "comunidad_indigena": False,
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        },
    )
    assert nucleo.status_code == 201, nucleo.text
    id_nucleo = nucleo.json()["id_nucleo"]
    cleanup.register("/api/nucleos", id_nucleo)
    consecutivo = int(str(uuid4().int)[-7:])

    preview = client.post(
        "/api/importaciones-territoriales/cruces_operativos/previsualizar",
        headers=admin_session,
        data={"id_tramo": str(seed_tramo["id_tramo"]), "id_nucleo": str(id_nucleo)},
        files=_collection(_feature({"consecutivo": consecutivo}, _line())),
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["validos"] == 1

    confirmed = client.post(
        "/api/importaciones-territoriales/cruces_operativos/confirmar",
        headers=admin_session,
        json={"archivo_sha256": preview.json()["archivo_sha256"], "items": preview.json()["items"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    cleanup.register("/api/tramos-nucleos", confirmed.json()["ids_creados"][0])

    db = SessionLocal()
    try:
        auto_afectaciones = db.query(models.Afectacion).filter(
            models.Afectacion.id_tramo_nucleo == confirmed.json()["ids_creados"][0],
        ).count()
        assert auto_afectaciones == 0
    finally:
        db.close()
