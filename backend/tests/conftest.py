"""
conftest.py — Configuración centralizada de fixtures para pytest.

Arquitectura:
  - Se reutiliza la app FastAPI real (sin mocks de BD) para correr tests
    de integración contra PostgreSQL+PostGIS.
  - La suite exige una base aislada y desechable. No intenta convertir la
    eliminación técnica de fixtures en bajas funcionales auditadas.

Convenciones:
  - Fixtures con scope="session" para datos que persisten entre tests.
  - Fixtures con scope="function" para datos efímeros.
  - Toda fixture que crea datos en la BD registra su cleanup automáticamente.
"""

import os
import pytest
import time


def _assert_isolated_test_database() -> None:
    environment = os.getenv("APP_ENV", "").strip().lower()
    database_name = os.getenv("DB_NAME", "").strip().lower()
    isolated_name = (
        database_name.startswith("test_")
        or database_name.endswith("_test")
        or "_test_" in database_name
    )
    if environment != "test" or not isolated_name:
        raise RuntimeError(
            "La suite sólo puede ejecutarse con APP_ENV=test y una DB_NAME "
            "aislada que incluya el marcador '_test'."
        )


_assert_isolated_test_database()

from fastapi.testclient import TestClient
from app.main import app


def _uid() -> str:
    """Genera un sufijo único basado en tiempo para evitar colisiones
    con datos de seed.sql o ejecuciones anteriores de tests."""
    return str(int(time.time() * 1000))[-8:]


# ─────────────────────── Cliente HTTP ─────────────────────── #

@pytest.fixture(scope="session")
def client():
    """Cliente HTTP de FastAPI para toda la sesión de pruebas."""
    return TestClient(app, raise_server_exceptions=False)


# ─────────────────────── Autenticación ─────────────────────── #

@pytest.fixture(scope="session")
def admin_credentials():
    """Credenciales del administrador de pruebas.

    Permite que cada ambiente de pruebas use su propio bootstrap sin codificar
    esas credenciales en los tests.
    """
    email = os.getenv("TEST_ADMIN_EMAIL")
    password = os.getenv("TEST_ADMIN_PASSWORD")
    if not email or not password:
        pytest.fail(
            "TEST_ADMIN_EMAIL y TEST_ADMIN_PASSWORD son obligatorios para "
            "ejecutar la suite contra una base de pruebas aislada."
        )
    return {"email": email, "password": password}


@pytest.fixture(scope="session")
def admin_session(client, admin_credentials):
    """Sesión cookie del admin de pruebas.

    Autentica contra POST /api/auth/sesiones (Corte 4 cookie-based).
    Las cookies de sesión se persisten automáticamente en el TestClient.
    Retorna headers necesarios para escrituras (Origin + CSRF).
    Falla rápido si las credenciales de prueba no existen."""
    from app.config import AUTH_SETTINGS

    origin = AUTH_SETTINGS.allowed_origins[0]
    response = client.post(
        "/api/auth/sesiones",
        data={
            "username": admin_credentials["email"],
            "password": admin_credentials["password"],
        },
        headers={"Origin": origin},
    )
    assert response.status_code == 200, (
        "No se pudo autenticar como admin. "
        "Configura TEST_ADMIN_EMAIL y TEST_ADMIN_PASSWORD para esta BD de pruebas."
    )
    csrf = client.cookies.get(AUTH_SETTINGS.csrf_cookie_name)
    assert csrf, "No se encontró cookie CSRF después del login."
    headers = {"Origin": origin, "X-CSRF-Token": csrf}
    yield headers
    logout = client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 200, "No se pudo revocar la sesión de pruebas."


# ─────────────────────── Pila de limpieza ─────────────────────── #

class CleanupStack:
    """Inventario de recursos creados para diagnósticos de la sesión."""

    def __init__(self):
        self._items: list[tuple[str, int]] = []

    def register(self, endpoint: str, resource_id: int):
        """Registra un recurso para limpieza posterior (LIFO)."""
        self._items.insert(0, (endpoint, resource_id))

    @property
    def items(self) -> list[tuple[str, int]]:
        return self._items


@pytest.fixture(scope="session")
def cleanup():
    """Pila de limpieza global de la sesión."""
    return CleanupStack()


# ────────── Datos semilla (cadena de dependencias) ────────── #

@pytest.fixture(scope="session")
def seed_municipio_id(client, admin_session):
    """Obtiene un id_municipio existente del catálogo.
    No crea nada, solo lee lo que ya existe."""
    res = client.get("/api/catalogos/municipios", headers=admin_session)
    assert res.status_code == 200
    municipios = res.json()
    assert len(municipios) > 0, (
        "La BD debe tener al menos un municipio. Ejecuta el seed.sql primero."
    )
    return municipios[0]["id_municipio"]


@pytest.fixture(scope="session")
def seed_proyecto(client, admin_session, cleanup):
    """Crea un proyecto de prueba para toda la sesión."""
    uid = _uid()
    payload = {
        "clave_proyecto": f"PRY-{uid}",
        "nombre_proyecto": f"Proyecto Pruebas {uid}",
    }
    res = client.post("/api/proyectos", json=payload, headers=admin_session)
    assert res.status_code == 201, f"No se pudo crear proyecto semilla: {res.text}"
    data = res.json()
    cleanup.register("/api/proyectos", data["id_proyecto"])
    return data


@pytest.fixture(scope="session")
def seed_tramo(client, admin_session, cleanup, seed_proyecto):
    """Crea un tramo de prueba para toda la sesión."""
    uid = _uid()
    payload = {
        "id_proyecto": seed_proyecto["id_proyecto"],
        "clave_tramo": f"TST-{uid}",
        "nombre_tramo": f"Tramo Pruebas {uid}",
        "geometria_wkt": "MULTILINESTRING((0 0, 1 1))",
        "ancho_total_derecho_via_m": 40.0,
    }
    res = client.post("/api/tramos", json=payload, headers=admin_session)
    assert res.status_code == 201, f"No se pudo crear tramo semilla: {res.text}"
    data = res.json()
    franja = client.post(
        f"/api/tramos/{data['id_tramo']}/franjas/importar",
        headers=admin_session,
        json={
            "fuente": "Franja oficial para pruebas",
            "fecha_vigencia_inicio": "2026-01-01",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        },
    )
    assert franja.status_code == 201, f"No se pudo crear franja semilla: {franja.text}"
    seccion = client.post(
        f"/api/tramos/{data['id_tramo']}/secciones-derecho-via/importar",
        headers=admin_session,
        json={
            "fuente": "Sección oficial para pruebas",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        },
    )
    assert seccion.status_code == 201, f"No se pudo crear sección semilla: {seccion.text}"
    cleanup.register("/api/tramos", data["id_tramo"])
    return data
@pytest.fixture(scope="session")
def seed_nucleo(client, admin_session, cleanup, seed_municipio_id):
    """Crea un núcleo agrario de prueba."""
    payload = {
        "id_municipio": seed_municipio_id,
        "nombre_nucleo": f"Ejido Pruebas {_uid()}",
        "tipo_nucleo": "ejido",
        "comunidad_indigena": False,
        "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
    }
    res = client.post("/api/nucleos", json=payload, headers=admin_session)
    assert res.status_code == 201, f"No se pudo crear núcleo semilla: {res.text}"
    data = res.json()
    cleanup.register("/api/nucleos", data["id_nucleo"])
    return data


@pytest.fixture(scope="session")
def seed_tramo_nucleo(client, admin_session, cleanup, seed_tramo, seed_nucleo):
    """Crea la relación tramo-núcleo necesaria para afectaciones."""
    payload = {
        "id_tramo": seed_tramo["id_tramo"],
        "id_nucleo": seed_nucleo["id_nucleo"],
        "consecutivo": int(_uid()),
        "geometria_wkt": "MULTILINESTRING((0 0, 1 1))",
    }
    res = client.post("/api/tramos-nucleos", json=payload, headers=admin_session)
    assert res.status_code == 201, f"No se pudo crear tramo-núcleo semilla: {res.text}"
    data = res.json()
    cleanup.register("/api/tramos-nucleos", data["id_tramo_nucleo"])
    for tipo in ("sensibilizacion", "caminamiento"):
        actividad = client.post(
            "/api/actividades-campo",
            json={
                "id_tramo_nucleo": data["id_tramo_nucleo"],
                "tipo_actividad": tipo,
                "contexto_proceso": "cop_original",
                "fecha_realizada": "2026-02-10" if tipo == "sensibilizacion" else "2026-02-11",
            },
            headers=admin_session,
        )
        assert actividad.status_code == 201, actividad.text
        cleanup.register("/api/actividades-campo", actividad.json()["id_actividad"])
    return data


@pytest.fixture(scope="session")
def seed_parcela(client, admin_session, cleanup, seed_nucleo):
    """Crea una parcela de prueba vinculada al núcleo semilla."""
    payload = {
        "id_nucleo": seed_nucleo["id_nucleo"],
        "tipo_parcela": "individual",
        "no_parcela_ppt": f"PPT-{_uid()}",
        "nombre_titular": f"Titular Pruebas {_uid()}",
        "documentacion_faltante": "En trámite ante el RAN",
    }
    res = client.post("/api/parcelas", json=payload, headers=admin_session)
    assert res.status_code == 201, f"No se pudo crear parcela semilla: {res.text}"
    data = res.json()
    cleanup.register("/api/parcelas", data["id_parcela"])
    return data


@pytest.fixture(scope="session")
def seed_afectacion_colectiva(client, admin_session, cleanup, seed_nucleo, seed_tramo_nucleo):
    """Crea una afectación colectiva de prueba."""
    payload = {
        "id_nucleo": seed_nucleo["id_nucleo"],
        "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
        "tipo_afectacion": "colectivo",
        "tipo_tenencia": "Uso Común",
        "destino_superficie": "Vías férreas",
        "superficie_afectada_ha": 10.5,
        "origen_registro": "captura_sistema",
        "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
    }
    res = client.post("/api/afectaciones", json=payload, headers=admin_session)
    assert res.status_code == 201, f"No se pudo crear afectación colectiva: {res.text}"
    data = res.json()
    cleanup.register("/api/afectaciones", data["id_afectacion"])
    return data


@pytest.fixture(scope="session")
def seed_afectacion_individual(client, admin_session, cleanup, seed_nucleo, seed_tramo_nucleo, seed_parcela):
    """Crea una afectación individual de prueba."""
    payload = {
        "id_nucleo": seed_nucleo["id_nucleo"],
        "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
        "id_parcela": seed_parcela["id_parcela"],
        "tipo_afectacion": "individual",
        "tipo_tenencia": "Parcelaria",
        "superficie_afectada_ha": 2.1,
        "origen_registro": "captura_sistema",
        "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
    }
    res = client.post("/api/afectaciones", json=payload, headers=admin_session)
    assert res.status_code == 201, f"No se pudo crear afectación individual: {res.text}"
    data = res.json()
    cleanup.register("/api/afectaciones", data["id_afectacion"])
    return data


@pytest.fixture(scope="session")
def seed_asamblea_anuencia(client, admin_session, cleanup, seed_nucleo, seed_tramo_nucleo, seed_afectacion_colectiva):
    """Crea una asamblea de anuencia otorgada (requerida para convenios colectivos)."""
    ciclos = client.get(
        f"/api/afectaciones/{seed_afectacion_colectiva['id_afectacion']}/ciclos",
        headers=admin_session,
    ).json()
    original = next(c for c in ciclos if c["tipo_ciclo"] == "cop_original")
    payload = {
        "id_nucleo": seed_nucleo["id_nucleo"],
        "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
        "id_afectacion": seed_afectacion_colectiva["id_afectacion"],
        "id_ciclo_afectacion": original["id_ciclo_afectacion"],
        "contexto_proceso": "cop_original",
        "tipo_asamblea": "anuencia",
        "resultado_anuencia": "otorgada",
        "estatus_asamblea": "completo",
        "fecha_realizada": "2026-02-20",
    }
    res = client.post("/api/asambleas", json=payload, headers=admin_session)
    assert res.status_code == 201, f"No se pudo crear asamblea anuencia: {res.text}"
    data = res.json()
    cleanup.register("/api/asambleas", data["id_asamblea"])
    return data
