"""Cobertura del incremento de administración territorial y accesos."""

import time

from fastapi.testclient import TestClient

from app.config import AUTH_SETTINGS
from app.main import app


def _uid() -> str:
    return str(int(time.time() * 1_000_000))[-10:]


def _create_user(client, admin_session, cleanup, role="operador"):
    uid = _uid()
    response = client.post(
        "/api/usuarios",
        headers=admin_session,
        json={
            "nombre": "Usuario",
            "apellido_paterno": "Territorial",
            "correo": f"territorial-{uid}@example.test",
            "rol": role,
            "contrasena": "PruebaSegura#2026",
        },
    )
    assert response.status_code == 201, response.text
    user = response.json()
    cleanup.register("/api/usuarios", user["id_usuario"])
    return user, "PruebaSegura#2026"


def _login(email, password):
    client = TestClient(app, raise_server_exceptions=False)
    origin = AUTH_SETTINGS.allowed_origins[0]
    response = client.post(
        "/api/auth/sesiones",
        data={"username": email, "password": password},
        headers={"Origin": origin},
    )
    assert response.status_code == 200, response.text
    csrf = client.cookies.get(AUTH_SETTINGS.csrf_cookie_name)
    return client, {"Origin": origin, "X-CSRF-Token": csrf}


def _create_empty_tramo(client, admin_session, cleanup, seed_proyecto):
    uid = _uid()
    response = client.post(
        "/api/tramos",
        headers=admin_session,
        json={
            "id_proyecto": seed_proyecto["id_proyecto"],
            "clave_tramo": f"ADM-{uid}",
            "nombre_tramo": f"Tramo administración {uid}",
            "ancho_total_derecho_via_m": "40.00",
            "geometria_wkt": "MULTILINESTRING((0 0, 1 1))",
        },
    )
    assert response.status_code == 201, response.text
    tramo = response.json()
    cleanup.register("/api/tramos", tramo["id_tramo"])
    return tramo


def test_consultas_administrativas_exigen_admin(client, admin_session, cleanup):
    geographer, password = _create_user(client, admin_session, cleanup, "geografo")
    geographer_client, headers = _login(geographer["correo"].upper(), password)

    assert client.get("/api/administracion/proyectos", headers=admin_session).status_code == 200
    assert geographer_client.get("/api/administracion/proyectos", headers=headers).status_code == 403
    assert geographer_client.post(
        "/api/proyectos",
        headers=headers,
        json={"clave_proyecto": f"NO-{_uid()}", "nombre_proyecto": "No permitido"},
    ).status_code == 403
    assert geographer_client.post(
        "/api/geometria/importar-geojson?tipo_entidad=tramo",
        headers=headers,
        files={"file": ("tramo.geojson", b"{}", "application/geo+json")},
    ).status_code == 403


def test_geografo_conserva_geometria_solo_en_tramo_asignado(
    client, admin_session, cleanup, seed_proyecto
):
    geographer, password = _create_user(client, admin_session, cleanup, "geografo")
    assigned = _create_empty_tramo(client, admin_session, cleanup, seed_proyecto)
    unassigned = _create_empty_tramo(client, admin_session, cleanup, seed_proyecto)
    assignment = client.put(
        f"/api/administracion/tramos/{assigned['id_tramo']}/asignaciones",
        headers=admin_session,
        json={"ids_usuario": [geographer["id_usuario"]], "motivo": "Cobertura territorial"},
    )
    assert assignment.status_code == 200, assignment.text

    geographer_client, headers = _login(geographer["correo"], password)
    allowed = geographer_client.put(
        f"/api/tramos/{assigned['id_tramo']}/geometria",
        headers=headers,
        json={"geometria_wkt": "MULTILINESTRING((0 0, 1 1))"},
    )
    denied = geographer_client.put(
        f"/api/tramos/{unassigned['id_tramo']}/geometria",
        headers=headers,
        json={"geometria_wkt": "MULTILINESTRING((0 0, 1 1))"},
    )
    assert allowed.status_code == 200, allowed.text
    assert denied.status_code == 403


def test_reemplazo_asignaciones_es_atomico_y_valida_usuarios(
    client, admin_session, cleanup, seed_proyecto
):
    operator, _ = _create_user(client, admin_session, cleanup)
    tramo = _create_empty_tramo(client, admin_session, cleanup, seed_proyecto)
    endpoint = f"/api/administracion/tramos/{tramo['id_tramo']}/asignaciones"

    created = client.put(
        endpoint,
        headers=admin_session,
        json={"ids_usuario": [operator["id_usuario"]], "motivo": "Asignación inicial"},
    )
    assert created.status_code == 200, created.text
    assert created.json()["altas"] == 1

    rejected = client.put(
        endpoint,
        headers=admin_session,
        json={"ids_usuario": [operator["id_usuario"], 99999999], "motivo": "Cambio inválido"},
    )
    assert rejected.status_code == 409
    current = client.get(endpoint, headers=admin_session)
    assert [item["id_usuario"] for item in current.json()] == [operator["id_usuario"]]


def test_baja_usuario_desactiva_asignaciones_en_misma_operacion(
    client, admin_session, cleanup, seed_proyecto
):
    operator, _ = _create_user(client, admin_session, cleanup)
    tramo = _create_empty_tramo(client, admin_session, cleanup, seed_proyecto)
    endpoint = f"/api/administracion/tramos/{tramo['id_tramo']}/asignaciones"
    assert client.put(
        endpoint,
        headers=admin_session,
        json={"ids_usuario": [operator["id_usuario"]], "motivo": "Asignación inicial"},
    ).status_code == 200

    deleted = client.delete(
        f"/api/usuarios/{operator['id_usuario']}?motivo=Baja%20de%20prueba",
        headers=admin_session,
    )
    assert deleted.status_code == 200, deleted.text
    assert client.get(endpoint, headers=admin_session).json() == []

    restored = client.post(
        f"/api/administracion/usuarios/{operator['id_usuario']}/reactivar",
        headers=admin_session,
        json={"motivo": "Reingreso de prueba"},
    )
    assert restored.status_code == 200, restored.text


def test_correo_se_normaliza_y_no_admite_equivalentes(client, admin_session, cleanup):
    user, _ = _create_user(client, admin_session, cleanup)
    duplicate = client.post(
        "/api/usuarios",
        headers=admin_session,
        json={
            "nombre": "Duplicado",
            "apellido_paterno": "Correo",
            "correo": f"  {user['correo'].upper()}  ",
            "rol": "operador",
            "contrasena": "PruebaSegura#2026",
        },
    )
    assert duplicate.status_code in {400, 409}


def test_reactivar_tramo_exige_proyecto_activo(client, admin_session, cleanup):
    uid = _uid()
    project_response = client.post(
        "/api/proyectos",
        headers=admin_session,
        json={"clave_proyecto": f"REA-{uid}", "nombre_proyecto": "Proyecto reactivación"},
    )
    assert project_response.status_code == 201, project_response.text
    project = project_response.json()
    cleanup.register("/api/proyectos", project["id_proyecto"])

    tramo = _create_empty_tramo(client, admin_session, cleanup, project)
    assert client.delete(
        f"/api/tramos/{tramo['id_tramo']}?motivo=Preparar%20reactivación",
        headers=admin_session,
    ).status_code == 200
    assert client.delete(
        f"/api/proyectos/{project['id_proyecto']}?motivo=Preparar%20reactivación",
        headers=admin_session,
    ).status_code == 200

    response = client.post(
        f"/api/administracion/tramos/{tramo['id_tramo']}/reactivar",
        headers=admin_session,
        json={"motivo": "Intento controlado"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "El proyecto del tramo debe estar activo antes de reactivarlo"
    )
