"""
conftest.py — Configuración centralizada de fixtures para pytest.

Arquitectura:
  - Se reutiliza la app FastAPI real (sin mocks de BD) para correr tests
    de integración contra el contenedor PostgreSQL+PostGIS existente.
  - Cada sesión de tests crea su propio conjunto de datos semilla y los
    limpia al final en orden inverso (LIFO) para respetar foreign keys.

Convenciones:
  - Fixtures con scope="session" para datos que persisten entre tests.
  - Fixtures con scope="function" para datos efímeros.
  - Toda fixture que crea datos en la BD registra su cleanup automáticamente.
"""

import pytest
import time
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
def admin_headers(client):
    """Headers de autorización para el usuario admin.
    Falla rápido si las credenciales de prueba no existen."""
    response = client.post(
        "/api/auth/login",
        data={"username": "admin@sistema.com", "password": "Admin123!"},
    )
    assert response.status_code == 200, (
        "No se pudo autenticar como admin. "
        "Asegúrate de que el usuario admin@sistema.com existe en la BD de pruebas."
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────── Pila de limpieza ─────────────────────── #

class CleanupStack:
    """Pila LIFO para registrar recursos creados durante los tests.
    Al finalizar la sesión, se eliminan en orden inverso para
    respetar las dependencias de foreign keys."""

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
def seed_municipio_id(client, admin_headers):
    """Obtiene un id_municipio existente del catálogo.
    No crea nada, solo lee lo que ya existe."""
    res = client.get("/api/catalogos/municipios", headers=admin_headers)
    assert res.status_code == 200
    municipios = res.json()
    assert len(municipios) > 0, (
        "La BD debe tener al menos un municipio. Ejecuta el seed.sql primero."
    )
    return municipios[0]["id_municipio"]


@pytest.fixture(scope="session")
def seed_proyecto(client, admin_headers, cleanup):
    """Crea un proyecto de prueba para toda la sesión."""
    uid = _uid()
    payload = {
        "clave_proyecto": f"PRY-{uid}",
        "nombre_proyecto": f"Proyecto Pruebas {uid}",
    }
    res = client.post("/api/proyectos", json=payload, headers=admin_headers)
    assert res.status_code == 201, f"No se pudo crear proyecto semilla: {res.text}"
    data = res.json()
    cleanup.register("/api/proyectos", data["id_proyecto"])
    return data


@pytest.fixture(scope="session")
def seed_tramo(client, admin_headers, cleanup, seed_proyecto):
    """Crea un tramo de prueba para toda la sesión."""
    uid = _uid()
    payload = {
        "id_proyecto": seed_proyecto["id_proyecto"],
        "clave_tramo": f"TST-{uid}",
        "nombre_tramo": f"Tramo Pruebas {uid}",
        "geometria_wkt": "MULTILINESTRING((0 0, 1 1))",
        "ancho_total_derecho_via_m": 40.0,
    }
    res = client.post("/api/tramos", json=payload, headers=admin_headers)
    assert res.status_code == 201, f"No se pudo crear tramo semilla: {res.text}"
    data = res.json()
    cleanup.register("/api/tramos", data["id_tramo"])
    return data
@pytest.fixture(scope="session")
def seed_nucleo(client, admin_headers, cleanup, seed_municipio_id):
    """Crea un núcleo agrario de prueba."""
    payload = {
        "id_municipio": seed_municipio_id,
        "nombre_nucleo": f"Ejido Pruebas {_uid()}",
        "tipo_nucleo": "ejido",
        "comunidad_indigena": False,
        "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
    }
    res = client.post("/api/nucleos", json=payload, headers=admin_headers)
    assert res.status_code == 201, f"No se pudo crear núcleo semilla: {res.text}"
    data = res.json()
    cleanup.register("/api/nucleos", data["id_nucleo"])
    return data


@pytest.fixture(scope="session")
def seed_tramo_nucleo(client, admin_headers, cleanup, seed_tramo, seed_nucleo):
    """Crea la relación tramo-núcleo necesaria para afectaciones."""
    payload = {
        "id_tramo": seed_tramo["id_tramo"],
        "id_nucleo": seed_nucleo["id_nucleo"],
        "consecutivo": int(_uid()),
        "geometria_wkt": "MULTILINESTRING((0 0, 1 1))",
    }
    res = client.post("/api/tramos-nucleos", json=payload, headers=admin_headers)
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
            headers=admin_headers,
        )
        assert actividad.status_code == 201, actividad.text
        cleanup.register("/api/actividades-campo", actividad.json()["id_actividad"])
    return data


@pytest.fixture(scope="session")
def seed_parcela(client, admin_headers, cleanup, seed_nucleo):
    """Crea una parcela de prueba vinculada al núcleo semilla."""
    payload = {
        "id_nucleo": seed_nucleo["id_nucleo"],
        "tipo_parcela": "individual",
        "no_parcela_ppt": f"PPT-{_uid()}",
        "nombre_titular": f"Titular Pruebas {_uid()}",
        "documentacion_faltante": "En trámite ante el RAN",
    }
    res = client.post("/api/parcelas", json=payload, headers=admin_headers)
    assert res.status_code == 201, f"No se pudo crear parcela semilla: {res.text}"
    data = res.json()
    cleanup.register("/api/parcelas", data["id_parcela"])
    return data


@pytest.fixture(scope="session")
def seed_afectacion_colectiva(client, admin_headers, cleanup, seed_nucleo, seed_tramo_nucleo):
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
    res = client.post("/api/afectaciones", json=payload, headers=admin_headers)
    assert res.status_code == 201, f"No se pudo crear afectación colectiva: {res.text}"
    data = res.json()
    cleanup.register("/api/afectaciones", data["id_afectacion"])
    return data


@pytest.fixture(scope="session")
def seed_afectacion_individual(client, admin_headers, cleanup, seed_nucleo, seed_tramo_nucleo, seed_parcela):
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
    res = client.post("/api/afectaciones", json=payload, headers=admin_headers)
    assert res.status_code == 201, f"No se pudo crear afectación individual: {res.text}"
    data = res.json()
    cleanup.register("/api/afectaciones", data["id_afectacion"])
    return data


@pytest.fixture(scope="session")
def seed_asamblea_anuencia(client, admin_headers, cleanup, seed_nucleo, seed_tramo_nucleo, seed_afectacion_colectiva):
    """Crea una asamblea de anuencia otorgada (requerida para convenios colectivos)."""
    ciclos = client.get(
        f"/api/afectaciones/{seed_afectacion_colectiva['id_afectacion']}/ciclos",
        headers=admin_headers,
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
    res = client.post("/api/asambleas", json=payload, headers=admin_headers)
    assert res.status_code == 201, f"No se pudo crear asamblea anuencia: {res.text}"
    data = res.json()
    cleanup.register("/api/asambleas", data["id_asamblea"])
    return data
