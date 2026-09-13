"""Regresión de schema 015: proyectos inactivos y contrato nullable de convenios."""

import os
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import AUTH_SETTINGS
from app.database import SessionLocal
from app.main import app


def _catalog(api, name: str) -> dict[str, int]:
    return {
        row["codigo"]: row["id_catalogo_opcion"]
        for row in api("GET", f"/api/catalogos/operativos/{name}").json()
    }


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
    assert csrf
    return client, {"Origin": origin, "X-CSRF-Token": csrf}


def _create_reporting_case(api, target_domain, prefix: str):
    token = uuid.uuid4().hex[:8]
    project = api(
        "POST",
        "/api/proyectos",
        expected=201,
        json={
            "clave_proyecto": f"{prefix}-{token}",
            "nombre_proyecto": f"Proyecto schema 015 {token}",
            "fecha_inicio": "2026-01-01",
        },
    ).json()
    nucleus = api(
        "POST",
        "/api/nucleos",
        expected=201,
        json={
            "id_municipio": target_domain["municipality"]["id_municipio"],
            "nombre_nucleo": f"Núcleo schema 015 {token}",
            "id_tipo_tenencia": _catalog(api, "tipo_tenencia")["ejido"],
            "fuente_datos": "qa-schema-015",
        },
    ).json()
    pn = api(
        "POST",
        f"/api/proyectos/{project['id_proyecto']}/nucleos",
        expected=201,
        json={
            "id_nucleo": nucleus["id_nucleo"],
            "afecta_tuc": False,
            "id_motivo_no_afecta_tuc": _catalog(api, "motivo_no_afecta_tuc")[
                "no_afectacion_colectiva"
            ],
            "tuc_revision_pendiente": False,
        },
    ).json()
    affectation = api(
        "POST",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo"},
    ).json()
    agreement = api(
        "POST",
        f"/api/afectaciones/{affectation['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "monto_100": "45000.25",
            "fecha_firma": "2026-07-01",
            "estado_antecedente": "no_aplica",
        },
    ).json()
    indemnity = api(
        "POST",
        f"/api/afectaciones/{affectation['id_afectacion']}/indemnizacion",
        expected=201,
        json={"estatus": "en_proceso"},
    ).json()
    payment = api(
        "POST",
        f"/api/indemnizaciones/{indemnity['id_indemnizacion']}/pagos",
        expected=201,
        json={
            "fecha_pago": "2026-07-15",
            "monto": "1234.56",
            "beneficiario_nombre": "Beneficiario schema 015",
            "medio_pago": "transferencia",
        },
    ).json()
    return project, pn, agreement, payment


def _view_counts(project_id: int, agreement_id: int, payment_id: int) -> dict[str, int]:
    db = SessionLocal()
    try:
        return {
            "snapshot": db.execute(
                text(
                    "SELECT count(*) FROM vw_reporte_snapshot_actual "
                    "WHERE id_proyecto = :project_id"
                ),
                {"project_id": project_id},
            ).scalar_one(),
            "payment": db.execute(
                text(
                    "SELECT count(*) FROM vw_hito_seguimiento "
                    "WHERE clave_hito = :payment_key"
                ),
                {"payment_key": f"pago:{payment_id}"},
            ).scalar_one(),
            "agreement": db.execute(
                text(
                    "SELECT count(*) FROM vw_convenio_colectivo_destino "
                    "WHERE id_convenio = :agreement_id"
                ),
                {"agreement_id": agreement_id},
            ).scalar_one(),
        }
    finally:
        db.close()


def _reactivate_project(project_id: int) -> None:
    db = SessionLocal()
    try:
        admin_id = db.execute(
            text("SELECT id_usuario FROM usuario WHERE lower(correo) = lower(:email)"),
            {"email": os.environ["TEST_ADMIN_EMAIL"]},
        ).scalar_one()
        db.execute(
            text("SELECT set_config('app.current_user_id', :actor, true)"),
            {"actor": str(admin_id)},
        )
        db.execute(
            text(
                "UPDATE proyecto SET activo = TRUE, fecha_baja = NULL, "
                "id_usuario_baja = NULL, motivo_baja = NULL, actualizado_en = now(), "
                "actualizado_por = :actor WHERE id_proyecto = :project_id"
            ),
            {"actor": admin_id, "project_id": project_id},
        )
        db.commit()
    finally:
        db.close()


def test_proyecto_inactivo_se_excluye_y_reactivado_vuelve_a_ser_elegible(
    api, target_domain
):
    project, _, agreement, payment = _create_reporting_case(
        api, target_domain, "INACTIVO-015"
    )
    project_id = project["id_proyecto"]

    password = f"Qa1!{uuid.uuid4().hex}Z"
    email = f"operador-schema015-{uuid.uuid4().hex[:8]}@qa.local"
    operator = api(
        "POST",
        "/api/usuarios",
        expected=201,
        json={
            "nombre": "Operador",
            "apellido_paterno": "Schema015",
            "correo": email,
            "rol": "operador",
            "contrasena": password,
        },
    ).json()
    api(
        "POST",
        f"/api/proyectos/{project_id}/usuarios",
        expected=201,
        json={"id_usuario": operator["id_usuario"]},
    )
    operator_client, _ = _login(email, password)

    active_counts = _view_counts(
        project_id, agreement["id_convenio"], payment["id_pago"]
    )
    assert active_counts["snapshot"] > 0
    assert active_counts["payment"] == 1
    assert active_counts["agreement"] == 1
    assert any(
        row["id_proyecto"] == project_id
        for row in operator_client.get("/api/proyectos").json()
    )

    api(
        "DELETE",
        f"/api/proyectos/{project_id}",
        json={"motivo": "Validación de exclusión schema 015"},
    )

    assert _view_counts(project_id, agreement["id_convenio"], payment["id_pago"]) == {
        "snapshot": 0,
        "payment": 0,
        "agreement": 0,
    }
    assert operator_client.get(f"/api/proyectos/{project_id}").status_code == 403
    assert all(
        row["id_proyecto"] != project_id
        for row in operator_client.get("/api/proyectos").json()
    )
    assert all(
        row["id_proyecto"] != project_id
        for row in operator_client.get("/api/reportes/resumen-actual").json()
    )
    assert all(
        row["id_proyecto"] != project_id
        for row in operator_client.get(
            "/api/reportes/avance-periodo?indicador=pagos"
        ).json()
    )
    assert all(
        row["id_proyecto"] != project_id
        for row in operator_client.get(
            "/api/reportes/convenios/colectivos-destino"
        ).json()
    )

    _reactivate_project(project_id)

    reactivated_counts = _view_counts(
        project_id, agreement["id_convenio"], payment["id_pago"]
    )
    assert reactivated_counts["snapshot"] == active_counts["snapshot"]
    assert reactivated_counts["payment"] == 1
    assert reactivated_counts["agreement"] == 1
    assert any(
        row["id_proyecto"] == project_id
        for row in operator_client.get("/api/proyectos").json()
    )

    api(
        "DELETE",
        f"/api/usuarios/{operator['id_usuario']}",
        json={"motivo": "Cierre de usuario sintético schema 015"},
    )


def test_tipo_convenio_null_es_respuesta_api_valida(api, target_domain):
    project, pn, _, _ = _create_reporting_case(api, target_domain, "NULL-015-BASE")
    affectation = api(
        "POST",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo"},
    ).json()
    agreement = api(
        "POST",
        f"/api/afectaciones/{affectation['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "otro",
            "descripcion_instrumento": "Instrumento colectivo distinto de convenio",
            "consecutivo": 2,
            "monto_100": "9876.54",
            "fecha_firma": "2026-08-01",
        },
    ).json()
    assert agreement["tipo_convenio"] is None

    response = api(
        "GET",
        "/api/reportes/convenios/colectivos-destino"
        f"?id_convenio={agreement['id_convenio']}",
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["tipo_convenio"] is None
    assert rows[0]["id_proyecto"] == project["id_proyecto"]
