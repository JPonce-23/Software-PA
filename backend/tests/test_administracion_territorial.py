"""Cobertura del incremento de administración territorial y accesos."""

import time

from fastapi.testclient import TestClient

from app.config import AUTH_SETTINGS
from app import main as main_module
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


def test_consultas_administrativas_separan_configuracion_y_admin(client, admin_session, cleanup):
    geographer, password = _create_user(client, admin_session, cleanup, "geografo")
    geographer_client, headers = _login(geographer["correo"].upper(), password)

    assert client.get("/api/administracion/proyectos", headers=admin_session).status_code == 200
    assert geographer_client.get("/api/administracion/proyectos", headers=headers).status_code == 200
    assert geographer_client.get("/api/administracion/usuarios", headers=headers).status_code == 403
    created = geographer_client.post(
        "/api/proyectos",
        headers=headers,
        json={"clave_proyecto": f"GEO-{_uid()}", "nombre_proyecto": "Proyecto geógrafo"},
    )
    assert created.status_code == 201, created.text
    cleanup.register("/api/proyectos", created.json()["id_proyecto"])
    assert geographer_client.post(
        "/api/geometria/importar-geojson?tipo_entidad=tramo",
        headers=headers,
        files={"file": ("tramo.geojson", b"{}", "application/geo+json")},
    ).status_code == 403


def test_geografo_puede_crear_tramo_y_queda_asignado(
    client, admin_session, cleanup, seed_proyecto
):
    geographer, password = _create_user(client, admin_session, cleanup, "geografo")
    geographer_client, headers = _login(geographer["correo"], password)
    response = geographer_client.post(
        "/api/tramos",
        headers=headers,
        json={
            "id_proyecto": seed_proyecto["id_proyecto"],
            "clave_tramo": f"GTR-{_uid()}",
            "nombre_tramo": "Tramo creado por geógrafo",
            "ancho_total_derecho_via_m": "40.00",
            "geometria_wkt": "MULTILINESTRING((0 0, 1 1))",
        },
    )
    assert response.status_code == 201, response.text
    tramo = response.json()
    cleanup.register("/api/tramos", tramo["id_tramo"])

    assignments = client.get(
        f"/api/administracion/tramos/{tramo['id_tramo']}/asignaciones",
        headers=admin_session,
    )
    assert assignments.status_code == 200, assignments.text
    assert [item["id_usuario"] for item in assignments.json()] == [geographer["id_usuario"]]


def test_geografo_no_puede_falsificar_usuario_en_asignacion_automatica(
    client, admin_session, cleanup, seed_proyecto
):
    geographer, password = _create_user(client, admin_session, cleanup, "geografo")
    admin_identity = client.get("/api/auth/sesion", headers=admin_session).json()["user"]
    geographer_client, headers = _login(geographer["correo"], password)
    response = geographer_client.post(
        "/api/tramos",
        headers=headers,
        json={
            "id_proyecto": seed_proyecto["id_proyecto"],
            "clave_tramo": f"FAL-{_uid()}",
            "nombre_tramo": "Tramo sin usuario falsificado",
            "ancho_total_derecho_via_m": "40.00",
            "geometria_wkt": "MULTILINESTRING((0 0, 1 1))",
            "id_usuario": admin_identity["id_usuario"],
        },
    )
    assert response.status_code == 201, response.text
    tramo = response.json()
    cleanup.register("/api/tramos", tramo["id_tramo"])

    assignments = client.get(
        f"/api/administracion/tramos/{tramo['id_tramo']}/asignaciones",
        headers=admin_session,
    )
    assigned_ids = [item["id_usuario"] for item in assignments.json()]
    assert assigned_ids == [geographer["id_usuario"]]
    assert admin_identity["id_usuario"] not in assigned_ids


def test_geografo_puede_crear_nucleo(client, admin_session, cleanup, seed_municipio_id):
    geographer, password = _create_user(client, admin_session, cleanup, "geografo")
    geographer_client, headers = _login(geographer["correo"], password)
    response = geographer_client.post(
        "/api/nucleos",
        headers=headers,
        json={
            "id_municipio": seed_municipio_id,
            "nombre_nucleo": f"Núcleo geógrafo {_uid()}",
            "tipo_nucleo": "ejido",
            "comunidad_indigena": False,
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        },
    )
    assert response.status_code == 201, response.text
    cleanup.register("/api/nucleos", response.json()["id_nucleo"])


def test_operador_no_puede_crear_configuracion_territorial(
    client, admin_session, cleanup, seed_proyecto, seed_municipio_id
):
    operator, password = _create_user(client, admin_session, cleanup, "operador")
    operator_client, headers = _login(operator["correo"], password)
    assert operator_client.post(
        "/api/proyectos",
        headers=headers,
        json={"clave_proyecto": f"OPR-{_uid()}", "nombre_proyecto": "Rechazado"},
    ).status_code == 403
    assert operator_client.post(
        "/api/tramos",
        headers=headers,
        json={
            "id_proyecto": seed_proyecto["id_proyecto"],
            "clave_tramo": f"OPR-{_uid()}",
            "nombre_tramo": "Rechazado",
        },
    ).status_code == 403
    assert operator_client.post(
        "/api/nucleos",
        headers=headers,
        json={
            "id_municipio": seed_municipio_id,
            "nombre_nucleo": "Rechazado",
            "tipo_nucleo": "ejido",
        },
    ).status_code == 403


def test_creacion_tramo_revierte_si_falla_asignacion_geografo(
    client, admin_session, cleanup, seed_proyecto, monkeypatch
):
    geographer, password = _create_user(client, admin_session, cleanup, "geografo")
    geographer_client, headers = _login(geographer["correo"], password)
    clave = f"RBK-{_uid()}"

    class BrokenUsuarioTramo:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("fallo controlado de asignación")

    monkeypatch.setattr(main_module.models, "UsuarioTramo", BrokenUsuarioTramo)
    response = geographer_client.post(
        "/api/tramos",
        headers=headers,
        json={
            "id_proyecto": seed_proyecto["id_proyecto"],
            "clave_tramo": clave,
            "nombre_tramo": "Tramo con rollback",
            "ancho_total_derecho_via_m": "40.00",
            "geometria_wkt": "MULTILINESTRING((0 0, 1 1))",
        },
    )
    assert response.status_code == 500
    monkeypatch.undo()

    tramos = client.get(
        f"/api/tramos?id_proyecto={seed_proyecto['id_proyecto']}",
        headers=admin_session,
    )
    assert tramos.status_code == 200, tramos.text
    assert all(item["clave_tramo"] != clave for item in tramos.json())


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
