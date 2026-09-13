"""Integration fixtures for the target model on an isolated PostgreSQL database."""

import os
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, text


TEST_DATABASE = "software_pa_test"
TEST_ADMIN_MARKER = "Cuenta administrada exclusivamente por pytest"


def _assert_isolated_database() -> None:
    environment = os.getenv("APP_ENV", "").strip().lower()
    database = os.getenv("DB_NAME", "").strip().lower()
    explicitly_authorized = os.getenv("TEST_ALLOW_DATABASE", "").strip().lower()
    if (
        environment != "test"
        or database != TEST_DATABASE
        or explicitly_authorized != TEST_DATABASE
    ):
        raise RuntimeError(
            "pytest requires APP_ENV=test, DB_NAME=software_pa_test and "
            "TEST_ALLOW_DATABASE=software_pa_test"
        )


_assert_isolated_database()

from app import models, schemas
from app.config import AUTH_SETTINGS
from app.database import SessionLocal
from app.main import app
from app.services.authentication import hash_password, password_matches
from app.services.common import set_audit_context


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="session")
def test_admin_credentials() -> tuple[str, str]:
    email = os.getenv("TEST_ADMIN_EMAIL")
    password = os.getenv("TEST_ADMIN_PASSWORD")
    if not email or not password:
        pytest.fail("TEST_ADMIN_EMAIL y TEST_ADMIN_PASSWORD son obligatorios")
    contract = schemas.UsuarioCreate(
        nombre="Pytest",
        apellido_paterno="QA",
        correo=email,
        rol="admin",
        contrasena=password,
    )

    with SessionLocal() as db:
        current_database = db.execute(text("SELECT current_database()")).scalar_one()
        if current_database != TEST_DATABASE:
            pytest.fail("La conexión de pytest no apunta a software_pa_test")
        user = (
            db.query(models.Usuario)
            .filter(func.lower(func.btrim(models.Usuario.correo)) == contract.correo)
            .one_or_none()
        )
        if user is None:
            actor = (
                db.query(models.Usuario)
                .filter(
                    models.Usuario.rol == "admin",
                    models.Usuario.activo.is_(True),
                )
                .order_by(models.Usuario.id_usuario)
                .first()
            )
            if actor is None:
                pytest.fail(
                    "software_pa_test requiere un administrador bootstrap para auditar "
                    "la creación de la cuenta pytest"
                )
            set_audit_context(db, actor.id_usuario)
            user = models.Usuario(
                nombre=contract.nombre,
                apellido_paterno=contract.apellido_paterno,
                correo=contract.correo,
                contrasena_hash=hash_password(contract.contrasena),
                rol="admin",
                activo=True,
                fecha_alta=datetime.now(timezone.utc),
                observaciones=TEST_ADMIN_MARKER,
            )
            db.add(user)
            db.commit()
        elif user.observaciones != TEST_ADMIN_MARKER:
            pytest.fail(
                "TEST_ADMIN_EMAIL pertenece a una cuenta no administrada por pytest"
            )
        elif not user.activo or user.rol != "admin":
            pytest.fail("La cuenta administrada por pytest no es un admin activo")
        elif not password_matches(contract.contrasena, user.contrasena_hash):
            pytest.fail(
                "TEST_ADMIN_PASSWORD no coincide con la cuenta administrada por pytest"
            )

    return contract.correo, contract.contrasena


@pytest.fixture(scope="session")
def admin_headers(
    client: TestClient, test_admin_credentials: tuple[str, str]
) -> dict[str, str]:
    email, password = test_admin_credentials
    origin = AUTH_SETTINGS.allowed_origins[0]
    response = client.post(
        "/api/auth/sesiones",
        data={"username": email, "password": password},
        headers={"Origin": origin},
    )
    assert response.status_code == 200, response.text
    csrf = client.cookies.get(AUTH_SETTINGS.csrf_cookie_name)
    assert csrf
    return {"Origin": origin, "X-CSRF-Token": csrf}


@pytest.fixture(scope="session")
def api(client: TestClient, admin_headers: dict[str, str]):
    created_projects: set[int] = set()

    def request(method: str, path: str, *, expected: int = 200, **kwargs):
        headers = {**admin_headers, **kwargs.pop("headers", {})}
        response = client.request(method, path, headers=headers, **kwargs)
        assert response.status_code == expected, response.text
        if method.upper() == "POST" and path == "/api/proyectos" and expected == 201:
            created_projects.add(response.json()["id_proyecto"])
        return response

    yield request

    for project_id in sorted(created_projects, reverse=True):
        response = client.request(
            "DELETE",
            f"/api/proyectos/{project_id}",
            headers=admin_headers,
            json={"motivo": "Cierre lógico de fixture sintética QA"},
        )
        assert response.status_code in (200, 404), response.text


@pytest.fixture(scope="session")
def target_domain(api):
    def catalog(name: str) -> dict[str, int]:
        return {
            row["codigo"]: row["id_catalogo_opcion"]
            for row in api("GET", f"/api/catalogos/operativos/{name}").json()
        }

    tenencia = catalog("tipo_tenencia")
    residencia = catalog("residencia")
    tipo_tierra = catalog("tipo_tierra")
    tipo_gestion = catalog("tipo_gestion")
    destino = catalog("destino_superficie")
    titularidad = catalog("tipo_titularidad_unidad")
    state = api("GET", "/api/catalogos/entidades").json()[0]
    municipality = api(
        "GET", f"/api/catalogos/municipios?id_entidad={state['id_entidad']}"
    ).json()[0]
    project = api(
        "POST",
        "/api/proyectos",
        expected=201,
        json={
            "clave_proyecto": unique("QA-PROY"),
            "nombre_proyecto": unique("Proyecto objetivo"),
            "fecha_inicio": "2026-01-01",
        },
    ).json()
    nucleus = api(
        "POST",
        "/api/nucleos",
        expected=201,
        json={
            "id_municipio": municipality["id_municipio"],
            "nombre_nucleo": unique("EJIDO QA"),
            "id_tipo_tenencia": tenencia["ejido"],
            "fuente_datos": "qa",
        },
    ).json()
    project_nucleus = api(
        "POST",
        f"/api/proyectos/{project['id_proyecto']}/nucleos",
        expected=201,
        json={
            "id_nucleo": nucleus["id_nucleo"],
            "id_residencia": residencia["queretaro"],
            "referencias": [
                {
                    "tipo_referencia": "consecutivo",
                    "valor": unique("CONS"),
                    "es_principal": True,
                },
                {
                    "tipo_referencia": "clave_tramo",
                    "valor": "REFERENCIA-HISTORICA-QA",
                },
            ],
        },
    ).json()
    pn_id = project_nucleus["id_proyecto_nucleo"]
    parcel_one = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": unique("P-1")},
    ).json()
    parcel_two = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": unique("P-2")},
    ).json()
    collective_one = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "colectivo",
            "superficie_preliminar_ha": "3.500000",
            "superficie_afectada_ha": "3.250000",
        },
    ).json()
    collective_two = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "colectivo",
            "superficie_preliminar_ha": "1.000000",
            "superficie_afectada_ha": "0.900000",
        },
    ).json()
    individual_one = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "individual",
            "superficie_preliminar_ha": "0.500000",
            "superficie_afectada_ha": "0.450000",
        },
    ).json()
    individual_two = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "individual",
            "superficie_preliminar_ha": "0.750000",
            "superficie_afectada_ha": "0.700000",
        },
    ).json()
    unit_specs = [
        (collective_one, None, tipo_tierra["uso_comun"], tipo_gestion["TUC"], destino["tuc"], titularidad["nucleo_agrario"]),
        (collective_two, None, tipo_tierra["uso_comun"], tipo_gestion["PARCELA"], destino["parcela_escolar"], titularidad["nucleo_agrario"]),
        (individual_one, parcel_one["id_parcela"], tipo_tierra["parcelada"], tipo_gestion["PARCELA"], destino["parcela_ejidal"], titularidad["persona"]),
        (individual_two, parcel_two["id_parcela"], tipo_tierra["parcelada"], tipo_gestion["PARCELA"], destino["parcela_ejidal"], titularidad["persona"]),
    ]
    units = []
    links = []
    for affectation, parcel_id, land_type, management, destination, ownership in unit_specs:
        unit = api(
            "POST",
            f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
            expected=201,
            json={
                "id_tipo_tierra": land_type,
                "id_tipo_gestion": management,
                "id_destino_superficie": destination,
                "id_tipo_titularidad": ownership,
                "id_parcela": parcel_id,
                "referencia_alfanumerica": unique("UA"),
            },
        ).json()
        link = api(
            "POST",
            f"/api/afectaciones/{affectation['id_afectacion']}/unidades-agrarias",
            expected=201,
            json={
                "id_unidad_agraria": unit["id_unidad_agraria"],
                "superficie_preliminar_ha": affectation["superficie_preliminar_ha"],
                "superficie_afectada_ha": affectation["superficie_afectada_ha"],
            },
        ).json()
        units.append(unit)
        links.append(link)

    return {
        "state": state,
        "municipality": municipality,
        "project": project,
        "nucleus": nucleus,
        "project_nucleus": project_nucleus,
        "parcels": [parcel_one, parcel_two],
        "collective": [collective_one, collective_two],
        "individual": [individual_one, individual_two],
        "units": units,
        "affectation_units": links,
    }
