import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_login_invalid_credentials():
    # Debería rechazar credenciales falsas con 401
    response = client.post(
        "/api/auth/login",
        data={"username": "fake@sistema.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_protected_route_without_token():
    # Debería bloquear el acceso a recursos protegidos sin JWT
    response = client.get("/api/tramos")
    assert response.status_code == 401

def test_catalog_routes_without_token():
    # Debería permitir leer catálogos sin autenticación (o con ella, dependiendo de la configuración actual)
    # En nuestro main.py actual, get_entidades tiene Dependencia?
    # Revisando main.py, get_entidades tiene Dependencia de get_db, pero no de RoleChecker (no lo inyectamos).
    response = client.get("/api/catalogos/entidades")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
