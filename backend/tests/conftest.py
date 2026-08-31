"""Integration fixtures for the target model on an isolated PostgreSQL database."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient


def _assert_isolated_database() -> None:
    environment = os.getenv("APP_ENV", "").strip().lower()
    database = os.getenv("DB_NAME", "").strip().lower()
    explicitly_authorized = os.getenv("TEST_ALLOW_DATABASE", "").strip().lower()
    database_is_authorized = "_test" in database or (
        explicitly_authorized and database == explicitly_authorized
    )
    if environment != "test" or not database_is_authorized:
        raise RuntimeError(
            "pytest requires APP_ENV=test and either an isolated DB_NAME containing "
            "'_test' or an exact TEST_ALLOW_DATABASE opt-in"
        )


_assert_isolated_database()

from app.config import AUTH_SETTINGS
from app.main import app


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="session")
def admin_headers(client: TestClient) -> dict[str, str]:
    email = os.getenv("TEST_ADMIN_EMAIL")
    password = os.getenv("TEST_ADMIN_PASSWORD")
    if not email or not password:
        pytest.fail("TEST_ADMIN_EMAIL y TEST_ADMIN_PASSWORD son obligatorios")
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
    def request(method: str, path: str, *, expected: int = 200, **kwargs):
        headers = {**admin_headers, **kwargs.pop("headers", {})}
        response = client.request(method, path, headers=headers, **kwargs)
        assert response.status_code == expected, response.text
        return response

    return request


@pytest.fixture(scope="session")
def target_domain(api):
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
            "tipo_nucleo": "ejido",
            "fuente_datos": "qa",
        },
    ).json()
    project_nucleus = api(
        "POST",
        f"/api/proyectos/{project['id_proyecto']}/nucleos",
        expected=201,
        json={
            "id_nucleo": nucleus["id_nucleo"],
            "residencia": "Residencia QA",
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
            "destino_superficie": "tierras_uso_comun",
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
            "destino_superficie": "parcela_escolar",
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
            "id_parcela": parcel_one["id_parcela"],
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
            "id_parcela": parcel_two["id_parcela"],
            "superficie_preliminar_ha": "0.750000",
            "superficie_afectada_ha": "0.700000",
        },
    ).json()
    return {
        "state": state,
        "municipality": municipality,
        "project": project,
        "nucleus": nucleus,
        "project_nucleus": project_nucleus,
        "parcels": [parcel_one, parcel_two],
        "collective": [collective_one, collective_two],
        "individual": [individual_one, individual_two],
    }
