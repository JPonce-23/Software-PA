"""Regresiones para la actualización de programación del trámite RAN padre.

Casos cubiertos:
A. Crear trámite con fecha programada y corregirla.
B. Crear trámite con fecha NULL y asignar una fecha (y limpiar a NULL).
C. Actualizar fecha sin modificar objetivo ni eventos.
D. Usuario sin acceso al proyecto -> rechazado (403).
E. Rol sin permiso de captura -> rechazado (403).
F. Trámite inexistente -> 404.
G. Body con campos no permitidos (id_asamblea, id_convenio, id_orv, eventos, etc.) -> 422.
H. La modificación genera la auditoría correspondiente (actualizado_por, bitacora).
I. Los eventos RAN anteriores permanecen idénticos.
J. El reporting programado refleja la nueva fecha sin modificar los hitos realizados.
"""

import uuid
from datetime import date
import pytest
from fastapi.testclient import TestClient

from app.config import AUTH_SETTINGS
from app.database import SessionLocal
from app.main import app
from app import models


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


def _catalog(api, name: str) -> dict[str, int]:
    return {
        row["codigo"]: row["id_catalogo_opcion"]
        for row in api("GET", f"/api/catalogos/operativos/{name}").json()
    }


def _create_isolated_environment(api, target_domain):
    token = uuid.uuid4().hex[:8]
    tenencia = _catalog(api, "tipo_tenencia")["ejido"]
    state = target_domain["state"]
    municipality = target_domain["municipality"]

    project = api(
        "POST",
        "/api/proyectos",
        expected=201,
        json={
            "clave_proyecto": f"PRJ-RAN-{token}",
            "nombre_proyecto": f"Proyecto RAN Prog {token}",
            "fecha_inicio": "2026-01-01",
        },
    ).json()

    nucleus = api(
        "POST",
        "/api/nucleos",
        expected=201,
        json={
            "id_municipio": municipality["id_municipio"],
            "nombre_nucleo": f"EJIDO RAN {token}",
            "id_tipo_tenencia": tenencia,
            "fuente_datos": "qa",
        },
    ).json()

    residencia = _catalog(api, "residencia")["queretaro"]
    project_nucleus = api(
        "POST",
        f"/api/proyectos/{project['id_proyecto']}/nucleos",
        expected=201,
        json={
            "id_nucleo": nucleus["id_nucleo"],
            "id_residencia": residencia,
            "referencias": [
                {
                    "tipo_referencia": "consecutivo",
                    "valor": f"RAN-PN-{token}",
                    "es_principal": True,
                }
            ],
        },
    ).json()

    # Create an assembly
    types = _catalog(api, "tipo_asamblea")
    contexts = _catalog(api, "contexto_asamblea")
    results = _catalog(api, "resultado_convocatoria")
    cops = _catalog(api, "tipo_cop_operativo")
    assembly = api(
        "POST",
        f"/api/proyecto-nucleo/{project_nucleus['id_proyecto_nucleo']}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": types["anuencia"],
            "id_contexto_asamblea": contexts["cop_original"],
            "id_tipo_cop_operativo": cops["ORIGEN"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2026-01-15",
                    "fecha_realizacion": "2026-01-15",
                    "id_resultado": results["celebrada"],
                }
            ],
        },
    ).json()

    return {
        "project": project,
        "nucleus": nucleus,
        "project_nucleus": project_nucleus,
        "assembly": assembly,
    }


def test_caso_a_crear_con_fecha_y_corregirla(api, target_domain):
    env = _create_isolated_environment(api, target_domain)
    procedure = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": env["assembly"]["id_asamblea"],
            "referencia_expediente": f"EXP-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2026-01-25",
        },
    ).json()
    ran_id = procedure["id_tramite_ran"]
    assert procedure["fecha_programada_ingreso"] == "2026-01-25"

    # PATCH to correct date
    res = api(
        "PATCH",
        f"/api/tramites-ran/{ran_id}",
        expected=200,
        json={"fecha_programada_ingreso": "2026-02-15"},
    ).json()
    assert res["id_tramite_ran"] == ran_id
    assert res["fecha_programada_ingreso"] == "2026-02-15"

    # Verify with GET
    fetched = api("GET", f"/api/tramites-ran/{ran_id}").json()
    assert fetched["fecha_programada_ingreso"] == "2026-02-15"


def test_caso_b_crear_con_fecha_null_y_asignar_y_limpiar(api, target_domain):
    env = _create_isolated_environment(api, target_domain)
    procedure = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": env["assembly"]["id_asamblea"],
            "referencia_expediente": f"EXP-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": None,
        },
    ).json()
    ran_id = procedure["id_tramite_ran"]
    assert procedure["fecha_programada_ingreso"] is None

    # Assign a date
    updated = api(
        "PATCH",
        f"/api/tramites-ran/{ran_id}",
        expected=200,
        json={"fecha_programada_ingreso": "2026-03-01"},
    ).json()
    assert updated["fecha_programada_ingreso"] == "2026-03-01"

    # Clear it back to None
    cleared = api(
        "PATCH",
        f"/api/tramites-ran/{ran_id}",
        expected=200,
        json={"fecha_programada_ingreso": None},
    ).json()
    assert cleared["fecha_programada_ingreso"] is None

    # Verify with GET
    fetched = api("GET", f"/api/tramites-ran/{ran_id}").json()
    assert fetched["fecha_programada_ingreso"] is None


def test_caso_c_actualizar_fecha_sin_modificar_objetivo_ni_eventos(api, target_domain):
    env = _create_isolated_environment(api, target_domain)
    codes = _catalog(api, "tipo_evento_ran")
    ref = f"EXP-OBJ-{uuid.uuid4().hex[:6]}"
    procedure = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": env["assembly"]["id_asamblea"],
            "referencia_expediente": ref,
            "fecha_programada_ingreso": "2026-01-20",
        },
    ).json()
    ran_id = procedure["id_tramite_ran"]

    # Add an event
    event = api(
        "POST",
        f"/api/tramites-ran/{ran_id}/eventos",
        expected=201,
        json={
            "ordinal": 1,
            "id_tipo_evento": codes["ingreso"],
            "fecha_evento": "2026-01-28",
            "numero_solicitud": "SOL-100",
        },
    ).json()

    # Update fecha_programada_ingreso
    updated = api(
        "PATCH",
        f"/api/tramites-ran/{ran_id}",
        expected=200,
        json={"fecha_programada_ingreso": "2026-02-28"},
    ).json()

    # Inmutable properties
    assert updated["id_tramite_ran"] == ran_id
    assert updated["id_asamblea"] == env["assembly"]["id_asamblea"]
    assert updated["id_convenio"] is None
    assert updated["id_orv"] is None
    assert updated["id_proyecto_nucleo"] == env["project_nucleus"]["id_proyecto_nucleo"]
    assert updated["id_nucleo"] is None
    assert updated["referencia_expediente"] == ref
    assert updated["fecha_programada_ingreso"] == "2026-02-28"

    # Events untouched
    assert len(updated["eventos"]) == 1
    assert updated["eventos"][0]["id_evento_ran"] == event["id_evento_ran"]
    assert updated["eventos"][0]["ordinal"] == 1
    assert updated["eventos"][0]["fecha_evento"] == "2026-01-28"


def test_caso_d_usuario_sin_acceso_al_proyecto_rechazado(api, target_domain):
    env = _create_isolated_environment(api, target_domain)
    procedure = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": env["assembly"]["id_asamblea"],
            "referencia_expediente": f"EXP-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2026-01-25",
        },
    ).json()
    ran_id = procedure["id_tramite_ran"]

    # Create operator user NOT assigned to this project
    password = _new_password()
    email = f"operador-{uuid.uuid4().hex[:8]}@qa.local"
    api(
        "POST",
        "/api/usuarios",
        expected=201,
        json={
            "nombre": "Operador",
            "apellido_paterno": "NoAsignado",
            "correo": email,
            "rol": "operador",
            "contrasena": password,
        },
    )

    client, headers = _login(email, password)
    res = client.patch(
        f"/api/tramites-ran/{ran_id}",
        headers=headers,
        json={"fecha_programada_ingreso": "2026-05-15"},
    )
    assert res.status_code == 403


def test_caso_e_rol_sin_permiso_de_captura_rechazado(api, target_domain):
    env = _create_isolated_environment(api, target_domain)
    procedure = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": env["assembly"]["id_asamblea"],
            "referencia_expediente": f"EXP-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2026-01-25",
        },
    ).json()
    ran_id = procedure["id_tramite_ran"]

    # Create visualizador assigned to this project
    password = _new_password()
    email = f"visualizador-{uuid.uuid4().hex[:8]}@qa.local"
    viewer = api(
        "POST",
        "/api/usuarios",
        expected=201,
        json={
            "nombre": "Viewer",
            "apellido_paterno": "SoloLectura",
            "correo": email,
            "rol": "visualizador",
            "contrasena": password,
        },
    ).json()

    api(
        "POST",
        f"/api/proyectos/{env['project']['id_proyecto']}/usuarios",
        expected=201,
        json={"id_usuario": viewer["id_usuario"]},
    )

    client, headers = _login(email, password)
    res = client.patch(
        f"/api/tramites-ran/{ran_id}",
        headers=headers,
        json={"fecha_programada_ingreso": "2026-05-15"},
    )
    assert res.status_code == 403


def test_caso_f_tramite_inexistente_retorna_404(api):
    res = api(
        "PATCH",
        "/api/tramites-ran/999999999",
        expected=404,
        json={"fecha_programada_ingreso": "2026-06-01"},
    )
    assert "Trámite RAN no encontrado" in res.json()["detail"]


def test_caso_g_body_con_campos_no_permitidos_rechazado_422(api, target_domain):
    env = _create_isolated_environment(api, target_domain)
    procedure = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": env["assembly"]["id_asamblea"],
            "referencia_expediente": f"EXP-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2026-01-25",
        },
    ).json()
    ran_id = procedure["id_tramite_ran"]

    forbidden_payloads = [
        {"id_asamblea": env["assembly"]["id_asamblea"]},
        {"id_convenio": 123},
        {"id_orv": 456},
        {"eventos": []},
        {"referencia_expediente": "NEW-REF"},
        {"id_tramite_ran": ran_id},
        {"id_proyecto_nucleo": env["project_nucleus"]["id_proyecto_nucleo"]},
        {"id_nucleo": env["nucleus"]["id_nucleo"]},
        {"activo": False},
        {"observaciones": "Cambio no permitido"},
    ]

    for payload in forbidden_payloads:
        res = api(
            "PATCH",
            f"/api/tramites-ran/{ran_id}",
            expected=422,
            json=payload,
        )
        assert res.status_code == 422


def test_caso_h_modificacion_genera_auditoria(api, target_domain):
    env = _create_isolated_environment(api, target_domain)
    # Create operator user assigned to this project to verify user ID in audit
    password = _new_password()
    email = f"operador-audit-{uuid.uuid4().hex[:8]}@qa.local"
    operator = api(
        "POST",
        "/api/usuarios",
        expected=201,
        json={
            "nombre": "Operador",
            "apellido_paterno": "Audit",
            "correo": email,
            "rol": "operador",
            "contrasena": password,
        },
    ).json()

    api(
        "POST",
        f"/api/proyectos/{env['project']['id_proyecto']}/usuarios",
        expected=201,
        json={"id_usuario": operator["id_usuario"]},
    )

    procedure = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": env["assembly"]["id_asamblea"],
            "referencia_expediente": f"EXP-AUDIT-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2026-01-20",
        },
    ).json()
    ran_id = procedure["id_tramite_ran"]

    client, headers = _login(email, password)
    patch_res = client.patch(
        f"/api/tramites-ran/{ran_id}",
        headers=headers,
        json={"fecha_programada_ingreso": "2026-04-15"},
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["actualizado_por"] == operator["id_usuario"]
    assert data["actualizado_en"] is not None

    # Check bitacora in DB
    db = SessionLocal()
    try:
        audit_rows = (
            db.query(models.Bitacora)
            .filter(
                models.Bitacora.entidad_tipo == "tramite_ran",
                models.Bitacora.entidad_id == ran_id,
                models.Bitacora.accion == "update",
            )
            .order_by(models.Bitacora.id_bitacora.desc())
            .all()
        )
        assert len(audit_rows) >= 1
        latest = audit_rows[0]
        assert latest.id_usuario == operator["id_usuario"]
        assert latest.valor_nuevo["fecha_programada_ingreso"] == "2026-04-15"
        assert latest.valor_anterior["fecha_programada_ingreso"] == "2026-01-20"
    finally:
        db.close()


def test_caso_i_eventos_anteriores_permanecen_identicos(api, target_domain):
    env = _create_isolated_environment(api, target_domain)
    codes = _catalog(api, "tipo_evento_ran")
    procedure = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": env["assembly"]["id_asamblea"],
            "referencia_expediente": f"EXP-EVT-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2026-01-10",
        },
    ).json()
    ran_id = procedure["id_tramite_ran"]

    evt1 = api(
        "POST",
        f"/api/tramites-ran/{ran_id}/eventos",
        expected=201,
        json={
            "ordinal": 1,
            "id_tipo_evento": codes["ingreso"],
            "fecha_evento": "2026-01-15",
            "numero_solicitud": "SOL-EVT-1",
        },
    ).json()

    evt2 = api(
        "POST",
        f"/api/tramites-ran/{ran_id}/eventos",
        expected=201,
        json={
            "ordinal": 2,
            "id_tipo_evento": codes["prevencion"],
            "fecha_evento": "2026-01-22",
            "numero_solicitud": "SOL-EVT-1",
            "resultado": "Faltan documentos",
        },
    ).json()

    # PATCH the procedure date
    api(
        "PATCH",
        f"/api/tramites-ran/{ran_id}",
        expected=200,
        json={"fecha_programada_ingreso": "2026-03-25"},
    )

    # Fetch events via GET
    events = api("GET", f"/api/tramites-ran/{ran_id}/eventos").json()
    assert len(events) == 2
    assert events[0]["id_evento_ran"] == evt1["id_evento_ran"]
    assert events[0]["ordinal"] == 1
    assert events[0]["fecha_evento"] == "2026-01-15"
    assert events[0]["numero_solicitud"] == "SOL-EVT-1"

    assert events[1]["id_evento_ran"] == evt2["id_evento_ran"]
    assert events[1]["ordinal"] == 2
    assert events[1]["fecha_evento"] == "2026-01-22"
    assert events[1]["resultado"] == "Faltan documentos"


def test_caso_j_reporting_programado_refleja_nueva_fecha_sin_afectar_realizados(
    api, target_domain
):
    env = _create_isolated_environment(api, target_domain)
    project_id = env["project"]["id_proyecto"]
    codes = _catalog(api, "tipo_evento_ran")

    # Create procedure with programmed date in Month 1 (Jan 2026)
    procedure = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": env["assembly"]["id_asamblea"],
            "referencia_expediente": f"EXP-REP-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2026-01-20",
        },
    ).json()
    ran_id = procedure["id_tramite_ran"]

    # Register realized event 'ingreso' in Month 2 (Feb 2026)
    api(
        "POST",
        f"/api/tramites-ran/{ran_id}/eventos",
        expected=201,
        json={
            "ordinal": 1,
            "id_tipo_evento": codes["ingreso"],
            "fecha_evento": "2026-02-10",
            "numero_solicitud": "SOL-REP-1",
        },
    )

    def _get_period(month):
        rows = api(
            "GET",
            "/api/reportes/avance-periodo",
            params={
                "id_proyecto": project_id,
                "anio": 2026,
                "mes": month,
                "indicador": "ingreso_ran_acta",
            },
        ).json()
        prog = sum(r["programado"] for r in rows)
        real = sum(r["realizado"] for r in rows)
        return prog, real

    # Before PATCH:
    # Month 1: programado = 1, realizado = 0
    # Month 2: programado = 0, realizado = 1
    # Month 3: programado = 0, realizado = 0
    p1, r1 = _get_period(1)
    p2, r2 = _get_period(2)
    p3, r3 = _get_period(3)
    assert p1 == 1 and r1 == 0
    assert p2 == 0 and r2 == 1
    assert p3 == 0 and r3 == 0

    # PATCH: Reprogram to Month 3 (Mar 2026)
    api(
        "PATCH",
        f"/api/tramites-ran/{ran_id}",
        expected=200,
        json={"fecha_programada_ingreso": "2026-03-25"},
    )

    # After PATCH:
    # Month 1: programado = 0, realizado = 0 (programado moved!)
    # Month 2: programado = 0, realizado = 1 (realizado unchanged!)
    # Month 3: programado = 1, realizado = 0 (programado is now in month 3!)
    p1_post, r1_post = _get_period(1)
    p2_post, r2_post = _get_period(2)
    p3_post, r3_post = _get_period(3)

    assert p1_post == 0 and r1_post == 0
    assert p2_post == 0 and r2_post == 1
    assert p3_post == 1 and r3_post == 0
