import uuid

from fastapi.testclient import TestClient

from app.config import AUTH_SETTINGS
from app.main import app


def _new_password() -> str:
    return f"Qa1!{uuid.uuid4().hex}Z"


def _login(email: str, password: str) -> tuple[TestClient, dict[str, str]]:
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


def test_auth_health_and_csrf(client, admin_headers):
    assert client.get("/health").json()["schema"] == 1
    anonymous = TestClient(app, raise_server_exceptions=False)
    assert anonymous.get("/api/proyectos").status_code == 401
    response = client.post(
        "/api/proyectos",
        json={"clave_proyecto": "CSRF-NO-DEBE-CREARSE", "nombre_proyecto": "CSRF"},
    )
    assert response.status_code == 403


def test_project_rbac_filters_before_pagination(api, target_domain):
    project_id = target_domain["project"]["id_proyecto"]
    role_sessions = {}
    for role in ("operador", "visualizador", "geografo"):
        password = _new_password()
        email = f"{role}-{uuid.uuid4().hex[:10]}@qa.local"
        user = api(
            "POST",
            "/api/usuarios",
            expected=201,
            json={
                "nombre": role.title(),
                "apellido_paterno": "QA",
                "correo": email,
                "rol": role,
                "contrasena": password,
            },
        ).json()
        api(
            "POST",
            f"/api/proyectos/{project_id}/usuarios",
            expected=201,
            json={"id_usuario": user["id_usuario"]},
        )
        role_sessions[role] = _login(email, password)

    unassigned = api(
        "POST",
        "/api/proyectos",
        expected=201,
        json={
            "clave_proyecto": f"NO-ASIGNADO-{uuid.uuid4().hex[:8]}",
            "nombre_proyecto": "Proyecto no asignado QA",
        },
    ).json()
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]

    operator, operator_headers = role_sessions["operador"]
    visible = operator.get("/api/proyectos?limit=1").json()
    assert len(visible) == 1
    assert visible[0]["id_proyecto"] == project_id
    assert operator.get(f"/api/proyectos/{unassigned['id_proyecto']}").status_code == 403
    assert operator.post(
        f"/api/proyecto-nucleo/{pn_id}/actividades",
        headers=operator_headers,
        json={
            "tipo_actividad": "caminamiento",
            "contexto_actividad": "general",
            "fecha_realizada": "2026-04-01",
        },
    ).status_code == 201

    viewer, viewer_headers = role_sessions["visualizador"]
    assert viewer.get(f"/api/proyecto-nucleo/{pn_id}").status_code == 200
    assert viewer.post(
        f"/api/proyecto-nucleo/{pn_id}/actividades",
        headers=viewer_headers,
        json={"tipo_actividad": "sensibilizacion"},
    ).status_code == 403

    geographer, geographer_headers = role_sessions["geografo"]
    assert geographer.get(f"/api/proyecto-nucleo/{pn_id}").status_code == 200
    assert geographer.post(
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        headers=geographer_headers,
        json={"tipo_afectacion": "colectivo"},
    ).status_code == 403
    trace = geographer.post(
        f"/api/proyectos/{project_id}/trazos",
        headers=geographer_headers,
        json={
            "version": 1,
            "geometria_wkt": "MULTILINESTRING((-100 20,-99.9 20.1))",
            "fuente": "Geometría sintética QA",
            "fecha_vigencia_inicio": "2026-01-01",
        },
    )
    assert trace.status_code == 201, trace.text
