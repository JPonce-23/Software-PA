import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app import models
from app.config import AUTH_SETTINGS
from app.database import SessionLocal
from app.main import app
from app.services import franjas


ORIGIN = AUTH_SETTINGS.allowed_origins[0]
TEST_PASSWORD = "PruebaGeo!2026"


def _feature(nombre="Ejido importado", tipo="ejido"):
    return {
        "type": "Feature",
        "properties": {"nombre_nucleo": nombre, "tipo_nucleo": tipo},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        },
    }


def _geojson_file(*features):
    content = json.dumps({"type": "FeatureCollection", "features": list(features)})
    return {"file": ("nucleos.geojson", content, "application/geo+json")}


def _login_geografo(email):
    browser = TestClient(app, raise_server_exceptions=False)
    login = browser.post(
        "/api/auth/sesiones",
        data={"username": email, "password": TEST_PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert login.status_code == 200, login.text
    csrf = browser.cookies.get(AUTH_SETTINGS.csrf_cookie_name)
    return browser, {"Origin": ORIGIN, "X-CSRF-Token": csrf}


def _import_franja_con_sesion(email, password, id_proyecto, fuente):
    browser = TestClient(app, raise_server_exceptions=False)
    headers = None
    try:
        login = browser.post(
            "/api/auth/sesiones",
            data={"username": email, "password": password},
            headers={"Origin": ORIGIN},
        )
        assert login.status_code == 200, login.text
        headers = {
            "Origin": ORIGIN,
            "X-CSRF-Token": browser.cookies.get(AUTH_SETTINGS.csrf_cookie_name),
        }
        return browser.post(
            f"/api/proyectos/{id_proyecto}/franjas/importar",
            headers=headers,
            json={
                "fuente": fuente,
                "fecha_vigencia_inicio": "2026-03-01",
                "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
            },
        )
    finally:
        if headers is not None:
            logout = browser.post("/api/auth/logout", headers=headers)
            assert logout.status_code == 200, logout.text
        browser.close()


def test_franja_versionada_sustituye_sin_sobrescribir(
    client,
    admin_session,
    seed_tramo,
):
    response = client.post(
        f"/api/proyectos/{seed_tramo['id_proyecto']}/franjas/importar",
        headers=admin_session,
        json={
            "fecha_vigencia_inicio": "2026-02-01",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["version"] == 2

    history = client.get(
        f"/api/proyectos/{seed_tramo['id_proyecto']}/franjas",
        headers=admin_session,
    )
    assert history.status_code == 200
    assert [item["version"] for item in history.json()[:2]] == [2, 1]
    assert history.json()[0]["activo"] is True
    assert history.json()[1]["activo"] is False
    assert history.json()[0]["geometria_wkt"].startswith("MULTIPOLYGON")
    seccion = client.post(
        f"/api/tramos/{seed_tramo['id_tramo']}/secciones-derecho-via/importar",
        headers=admin_session,
        json={
            "fuente": "Sección de la nueva versión",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        },
    )
    assert seccion.status_code == 201, seccion.text


def test_seccion_debe_intersectar_el_trazo_activo(
    client,
    admin_session,
    seed_tramo,
):
    response = client.post(
        f"/api/tramos/{seed_tramo['id_tramo']}/secciones-derecho-via/importar",
        headers=admin_session,
        json={
            "fuente": "Sección fuera del trazo",
            "geometria_wkt": "MULTIPOLYGON(((10 10, 11 10, 11 11, 10 11, 10 10)))",
        },
    )
    assert response.status_code == 409


def test_seccion_puede_vincularse_a_un_eje_lineal_confirmado(
    client,
    admin_session,
    cleanup,
):
    suffix = uuid4().hex[:10]
    project = client.post(
        "/api/proyectos",
        headers=admin_session,
        json={"clave_proyecto": f"EJE-{suffix}", "nombre_proyecto": f"Proyecto eje {suffix}"},
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id_proyecto"]
    cleanup.register("/api/proyectos", project_id)

    trace = client.post(
        f"/api/proyectos/{project_id}/franjas/importar",
        headers=admin_session,
        json={
            "fecha_vigencia_inicio": "2026-08-17",
            "geometria_wkt": "MULTILINESTRING((0 0, 1 1))",
        },
    )
    assert trace.status_code == 201, trace.text
    assert trace.json()["geometria_wkt"].startswith("MULTILINESTRING")

    tramo = client.post(
        "/api/tramos",
        headers=admin_session,
        json={
            "id_proyecto": project_id,
            "clave_tramo": f"EJE-{suffix}",
            "nombre_tramo": f"Tramo eje {suffix}",
        },
    )
    assert tramo.status_code == 201, tramo.text
    cleanup.register("/api/tramos", tramo.json()["id_tramo"])

    section = client.post(
        f"/api/tramos/{tramo.json()['id_tramo']}/secciones-derecho-via/importar",
        headers=admin_session,
        json={
            "fuente": "Sección oficial del eje",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        },
    )
    assert section.status_code == 201, section.text


def test_franjas_activas_exponen_geometria(
    client,
    admin_session,
    seed_tramo,
):
    response = client.get("/api/franjas/activas", headers=admin_session)
    assert response.status_code == 200, response.text
    franja = next(
        item for item in response.json()
        if item["id_proyecto"] == seed_tramo["id_proyecto"]
    )
    assert franja["activo"] is True
    assert franja["geometria_wkt"].startswith("MULTIPOLYGON")


def test_nucleos_por_tramo_usan_superficie_de_franja_no_linea(
    client,
    admin_session,
    cleanup,
    seed_tramo,
    seed_municipio_id,
):
    nombre = f"Núcleo franja sin eje {uuid4().hex}"
    created = client.post(
        "/api/nucleos",
        headers=admin_session,
        json={
            "id_municipio": seed_municipio_id,
            "nombre_nucleo": nombre,
            "tipo_nucleo": "ejido",
            "comunidad_indigena": False,
            "geometria_wkt": "MULTIPOLYGON(((0.75 0.05, 0.90 0.05, 0.90 0.20, 0.75 0.20, 0.75 0.05)))",
        },
    )
    assert created.status_code == 201, created.text
    id_nucleo = created.json()["id_nucleo"]
    cleanup.register("/api/nucleos", id_nucleo)

    response = client.get(
        f"/api/nucleos?id_tramo={seed_tramo['id_tramo']}",
        headers=admin_session,
    )
    assert response.status_code == 200, response.text
    item = next(row for row in response.json() if row["id_nucleo"] == id_nucleo)
    assert item["area_afectada_ha"] > 0


def test_postgresql_protege_versiones_y_delete(seed_tramo):
    db = SessionLocal()
    try:
        actor = db.query(models.Usuario.id_usuario).filter(
            models.Usuario.rol == "admin",
            models.Usuario.activo.is_(True),
        ).order_by(models.Usuario.id_usuario).first()
        assert actor is not None
        actor_id = actor[0]
        franja = (
            db.query(models.FranjaDerechoVia)
            .filter(
                models.FranjaDerechoVia.id_proyecto == seed_tramo["id_proyecto"],
                models.FranjaDerechoVia.activo.is_(True),
            )
            .one()
        )
        db.execute(
            text("SELECT set_config('app.current_user_id', :actor, true)"),
            {"actor": str(actor_id)},
        )
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    "UPDATE franja_derecho_via SET fuente = 'Sobrescrita' "
                    "WHERE id_franja = :id_franja"
                ),
                {"id_franja": franja.id_franja},
            )
        db.rollback()

        db.execute(
            text("SELECT set_config('app.current_user_id', :actor, true)"),
            {"actor": str(actor_id)},
        )
        with pytest.raises(DBAPIError):
            db.execute(
                text("DELETE FROM franja_derecho_via WHERE id_franja = :id_franja"),
                {"id_franja": franja.id_franja},
            )

        db.rollback()
        db.execute(
            text("SELECT set_config('app.current_user_id', :actor, true)"),
            {"actor": str(actor_id)},
        )
        db.execute(
            text(
                "UPDATE franja_derecho_via "
                "SET activo = FALSE, fecha_vigencia_fin = fecha_vigencia_inicio, "
                "fecha_baja = now(), id_usuario_baja = :actor, "
                "motivo_baja = 'Sonda de prueba' "
                "WHERE id_franja = :id_franja"
            ),
            {"actor": actor_id, "id_franja": franja.id_franja},
        )
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    "INSERT INTO franja_derecho_via ("
                    "id_proyecto, version, geometria_poligono, fuente, "
                    "fecha_vigencia_inicio, activo"
                    ") SELECT id_proyecto, version + 1, geometria_poligono, fuente, "
                    "fecha_vigencia_inicio - 1, TRUE "
                    "FROM franja_derecho_via WHERE id_franja = :id_franja"
                ),
                {"id_franja": franja.id_franja},
            )
    finally:
        db.rollback()
        db.close()


def test_importaciones_concurrentes_serializan_version(
    client,
    admin_session,
    admin_credentials,
    seed_tramo,
):
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                _import_franja_con_sesion,
                admin_credentials["email"],
                admin_credentials["password"],
                seed_tramo["id_proyecto"],
                f"Fuente concurrente {index}",
            )
            for index in range(2)
        ]
        responses = [future.result() for future in futures]

    assert [response.status_code for response in responses] == [201, 201]
    versions = sorted(response.json()["version"] for response in responses)
    assert versions[1] == versions[0] + 1

    db = SessionLocal()
    try:
        active_count = db.query(models.FranjaDerechoVia).filter(
            models.FranjaDerechoVia.id_proyecto == seed_tramo["id_proyecto"],
            models.FranjaDerechoVia.activo.is_(True),
        ).count()
        assert active_count == 1
    finally:
        db.close()
    seccion = client.post(
        f"/api/tramos/{seed_tramo['id_tramo']}/secciones-derecho-via/importar",
        headers=admin_session,
        json={
            "fuente": "Sección de la versión concurrente",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        },
    )
    assert seccion.status_code == 201, seccion.text


def test_validacion_falla_cerrado_sin_franja(
    client,
    admin_session,
    seed_proyecto,
):
    response = client.post(
        "/api/tramos",
        headers=admin_session,
        json={
            "id_proyecto": seed_proyecto["id_proyecto"],
            "clave_tramo": f"SIN-FR-{uuid4().hex[:8]}",
            "nombre_tramo": "Tramo temporal sin franja",
        },
    )
    assert response.status_code == 201, response.text
    tramo = response.json()
    try:
        db = SessionLocal()
        try:
            with pytest.raises(HTTPException) as exc_info:
                franjas.validar_interseccion_afectacion(
                    db,
                    tramo["id_tramo"],
                    "MULTIPOLYGON(((10 10, 11 10, 11 11, 10 11, 10 10)))",
                )
            assert exc_info.value.status_code == 409
        finally:
            db.close()
    finally:
        client.delete(
            f"/api/tramos/{tramo['id_tramo']}?motivo=Limpieza Corte 5",
            headers=admin_session,
        )


@pytest.mark.skip(reason="El endpoint legacy de nucleos fue retirado por el staging 020")
def test_importacion_admin_global_es_atomica_y_estricta(
    client,
    admin_session,
    seed_municipio_id,
):
    nombre = f"Ejido global {uuid4().hex}"
    response = client.post(
        "/api/nucleos/importacion-masiva",
        headers=admin_session,
        data={"id_municipio_fallback": str(seed_municipio_id)},
        files=_geojson_file(_feature(nombre)),
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    for id_nucleo in response.json()["ids_nucleo"]:
        client.delete(
            f"/api/nucleos/{id_nucleo}?motivo=Limpieza Corte 5",
            headers=admin_session,
        )

    invalida = client.post(
        "/api/nucleos/importacion-masiva",
        headers=admin_session,
        data={"id_municipio_fallback": str(seed_municipio_id)},
        files=_geojson_file(
            _feature(f"Ejido válido {uuid4().hex}"),
            _feature(f"Ejido inválido {uuid4().hex}", "tipo_desconocido"),
        ),
    )
    assert invalida.status_code == 400
    assert invalida.json()["detail"]["errores"][0]["index"] == 1

    raiz_invalida = client.post(
        "/api/nucleos/importacion-masiva",
        headers=admin_session,
        data={"id_municipio_fallback": str(seed_municipio_id)},
        files={"file": ("raiz.geojson", "[]", "application/geo+json")},
    )
    assert raiz_invalida.status_code == 400
    assert raiz_invalida.json()["detail"] == "El archivo debe ser un FeatureCollection."

    db = SessionLocal()
    try:
        actor = db.query(models.Usuario.id_usuario).filter(
            models.Usuario.rol == "admin",
            models.Usuario.activo.is_(True),
        ).order_by(models.Usuario.id_usuario).first()
        assert actor is not None
        db.execute(
            text("SELECT set_config('app.current_user_id', :actor, true)"),
            {"actor": str(actor[0])},
        )
        with pytest.raises(DBAPIError):
            db.execute(
                text(
                    "INSERT INTO nucleo_agrario ("
                    "id_municipio, nombre_nucleo, tipo_nucleo, comunidad_indigena, "
                    "geometria_poligono, fecha_creacion, activo"
                    ") VALUES ("
                    ":municipio, :nombre, 'ejido', FALSE, "
                    "ST_GeomFromText("
                    "'MULTIPOLYGON(((0 0,1 1,1 0,0 1,0 0)))', 4326"
                    "), now(), TRUE)"
                ),
                {
                    "municipio": seed_municipio_id,
                    "nombre": f"Núcleo inválido {uuid4().hex}",
                },
            )
    finally:
        db.rollback()
        db.close()


@pytest.mark.skip(reason="El endpoint legacy de nucleos fue retirado por el staging 020")
def test_geografo_puede_elegir_varios_tramos_asignados(
    client,
    admin_session,
    seed_tramo,
    seed_tramo_nucleo,
    seed_municipio_id,
):
    email = f"geografo-c5-{uuid4().hex}@pa.test"
    created = client.post(
        "/api/usuarios",
        headers=admin_session,
        json={
            "nombre": "Prueba",
            "apellido_paterno": "Geografía",
            "correo": email,
            "rol": "geografo",
            "contrasena": TEST_PASSWORD,
        },
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id_usuario"]
    tramos = client.get("/api/tramos", headers=admin_session).json()
    second = next(item for item in tramos if item["id_tramo"] != seed_tramo["id_tramo"])
    assigned_ids = [seed_tramo["id_tramo"], second["id_tramo"]]
    for id_tramo in assigned_ids:
        assigned = client.post(
            f"/api/tramos/{id_tramo}/asignar-usuario",
            headers=admin_session,
            json={"id_usuario": user_id},
        )
        assert assigned.status_code == 200, assigned.text

    browser, headers = _login_geografo(email)
    try:
        multipart = [
            ("id_municipio_fallback", (None, str(seed_municipio_id))),
            ("ids_tramo_contexto", (None, str(assigned_ids[0]))),
            ("ids_tramo_contexto", (None, str(assigned_ids[1]))),
            *list(_geojson_file(_feature(f"Ejido territorial {uuid4().hex}")).items()),
        ]
        imported = browser.post(
            "/api/nucleos/importacion-masiva",
            headers=headers,
            files=multipart,
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["total"] == 1
        imported_ids = imported.json()["ids_nucleo"]

        forbidden_update = browser.put(
            f"/api/nucleos/{imported_ids[0]}",
            headers=headers,
            json={"nombre_nucleo": "Cambio fuera de territorio"},
        )
        assert forbidden_update.status_code == 403
        forbidden_delete = browser.delete(
            f"/api/nucleos/{imported_ids[0]}?motivo=Intento fuera de territorio",
            headers=headers,
        )
        assert forbidden_delete.status_code == 403

        territorial_report = browser.get("/api/reportes/resumen")
        admin_report = client.get("/api/reportes/resumen", headers=admin_session)
        assert territorial_report.status_code == 200
        assert admin_report.status_code == 200
        assert admin_report.json()["total_nucleos"] > territorial_report.json()["total_nucleos"]

        db = SessionLocal()
        try:
            auto_relations = db.query(models.TramoNucleo).filter(
                models.TramoNucleo.id_nucleo.in_(imported_ids),
            ).count()
            assert auto_relations == 0
        finally:
            db.close()

        for id_nucleo in imported_ids:
            client.delete(
                f"/api/nucleos/{id_nucleo}?motivo=Limpieza Corte 5",
                headers=admin_session,
            )

        unassigned = next(
            item for item in tramos if item["id_tramo"] not in assigned_ids
        )
        rejected = browser.post(
            "/api/nucleos/importacion-masiva",
            headers=headers,
            data={
                "id_municipio_fallback": str(seed_municipio_id),
                "ids_tramo_contexto": str(unassigned["id_tramo"]),
            },
            files=_geojson_file(_feature(f"Ejido rechazado {uuid4().hex}")),
        )
        assert rejected.status_code == 403
    finally:
        logout = browser.post("/api/auth/logout", headers=headers)
        assert logout.status_code == 200, logout.text
        browser.close()
        for id_tramo in assigned_ids:
            client.delete(
                f"/api/tramos/{id_tramo}/remover-usuario/{user_id}?motivo=Limpieza Corte 5",
                headers=admin_session,
            )
        client.delete(
            f"/api/usuarios/{user_id}?motivo=Limpieza Corte 5",
            headers=admin_session,
        )
