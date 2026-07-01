import pytest
from fastapi.testclient import TestClient
from app.main import app
import random

client = TestClient(app, raise_server_exceptions=True)

@pytest.fixture(scope="session")
def auth_token():
    response = client.post(
        "/api/auth/login",
        data={"username": "admin@sistema.com", "password": "Admin123!"}
    )
    assert response.status_code == 200, "Error: No se pudo iniciar sesión"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

@pytest.fixture(scope="session")
def ctx(auth_token):
    # Diccionario compartido para guardar IDs y limpiarlos al final
    return {"auth": auth_token, "cleanup_stack": []}

def register_cleanup(ctx, endpoint, item_id):
    # Agrega al inicio para borrar en orden inverso (LIFO) y no romper FKs
    ctx["cleanup_stack"].insert(0, (endpoint, item_id))

def test_00_preparar_catalogos(ctx):
    res = client.get("/api/catalogos/municipios", headers=ctx["auth"])
    assert res.status_code == 200
    municipios = res.json()
    assert len(municipios) > 0, "Debe existir al menos un municipio en la BD"
    ctx["id_municipio"] = municipios[0]["id_municipio"]

def test_01_tramo(ctx):
    data = {
        "clave_tramo": f"TR-{random.randint(100,999)}",
        "nombre_tramo": "Tramo Prueba Prof",
        "geometria_wkt": "MULTILINESTRING((0 0, 1 1))",
        "ancho_total_derecho_via_m": 40.0
    }
    res = client.post("/api/tramos", json=data, headers=ctx["auth"])
    assert res.status_code == 201, res.text
    ctx["id_tramo"] = res.json()["id_tramo"]
    register_cleanup(ctx, "/api/tramos", ctx["id_tramo"])

def test_02_frente(ctx):
    data = {
        "id_tramo": ctx["id_tramo"],
        "clave_frente": f"FR-{random.randint(100,999)}",
        "nombre_frente": "Frente Prueba Prof",
        "geometria_wkt": "MULTILINESTRING((0 0, 1 1))"
    }
    res = client.post("/api/frentes", json=data, headers=ctx["auth"])
    assert res.status_code == 201, res.text
    ctx["id_frente"] = res.json()["id_frente"]
    register_cleanup(ctx, "/api/frentes", ctx["id_frente"])

def test_03_nucleo(ctx):
    data = {
        "id_municipio": ctx["id_municipio"],
        "nombre_nucleo": "Ejido Prueba Prof",
        "tipo_nucleo": "ejido",
        "comunidad_indigena": False,
        "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))"
    }
    res = client.post("/api/nucleos", json=data, headers=ctx["auth"])
    assert res.status_code == 201, res.text
    ctx["id_nucleo"] = res.json()["id_nucleo"]
    register_cleanup(ctx, "/api/nucleos", ctx["id_nucleo"])

def test_04_tramo_nucleo(ctx):
    data = {
        "id_tramo": ctx["id_tramo"],
        "id_frente": ctx["id_frente"],
        "id_nucleo": ctx["id_nucleo"],
        "consecutivo": random.randint(1, 1000),
        "geometria_wkt": "MULTILINESTRING((0 0, 1 1))"
    }
    res = client.post("/api/tramos-nucleos", json=data, headers=ctx["auth"])
    assert res.status_code == 201, res.text
    ctx["id_tramo_nucleo"] = res.json()["id_tramo_nucleo"]
    register_cleanup(ctx, "/api/tramos-nucleos", ctx["id_tramo_nucleo"])

def test_05_parcela(ctx):
    data = {
        "id_nucleo": ctx["id_nucleo"],
        "tipo_parcela": "individual",
        "no_parcela_ppt": "PPT-PROF-1",
        "nombre_titular": "Sujeto Agrario Automatizado",
        "documentacion_faltante": "En trámite ante el RAN"
    }
    res = client.post("/api/parcelas", json=data, headers=ctx["auth"])
    assert res.status_code == 201, res.text
    ctx["id_parcela"] = res.json()["id_parcela"]
    register_cleanup(ctx, "/api/parcelas", ctx["id_parcela"])

def test_06_afectaciones_completas(ctx):
    # Afectacion Colectiva (Uso Común)
    data_col = {
        "id_nucleo": ctx["id_nucleo"],
        "id_tramo_nucleo": ctx["id_tramo_nucleo"],
        "tipo_afectacion": "colectivo",
        "tipo_tenencia": "Uso Común",
        "destino_superficie": "Vías férreas",
        "superficie_afectada_ha": 10.5,
        "origen_registro": "captura_sistema",
        "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))"
    }
    res_col = client.post("/api/afectaciones", json=data_col, headers=ctx["auth"])
    assert res_col.status_code == 201, res_col.text
    ctx["id_afec_col"] = res_col.json()["id_afectacion"]
    register_cleanup(ctx, "/api/afectaciones", ctx["id_afec_col"])

    # Afectacion Individual (Parcelaria)
    data_ind = {
        "id_nucleo": ctx["id_nucleo"],
        "id_tramo_nucleo": ctx["id_tramo_nucleo"],
        "id_parcela": ctx["id_parcela"],
        "tipo_afectacion": "individual",
        "tipo_tenencia": "Parcelaria",
        "superficie_afectada_ha": 2.1,
        "origen_registro": "captura_sistema",
        "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))"
    }
    res_ind = client.post("/api/afectaciones", json=data_ind, headers=ctx["auth"])
    assert res_ind.status_code == 201, res_ind.text
    ctx["id_afec_ind"] = res_ind.json()["id_afectacion"]
    register_cleanup(ctx, "/api/afectaciones", ctx["id_afec_ind"])

def test_07_asambleas_multiples(ctx):
    # Asamblea de Información
    data_info = {
        "id_nucleo": ctx["id_nucleo"],
        "id_tramo_nucleo": ctx["id_tramo_nucleo"],
        "contexto_proceso": "cop_original",
        "tipo_asamblea": "informacion",
        "estatus_asamblea": "completo",
        "fecha_realizada": "2026-01-15"
    }
    res_info = client.post("/api/asambleas", json=data_info, headers=ctx["auth"])
    assert res_info.status_code == 201, res_info.text
    register_cleanup(ctx, "/api/asambleas", res_info.json()["id_asamblea"])

    # Asamblea de Anuencia (Aprobatoria)
    data_anu = {
        "id_nucleo": ctx["id_nucleo"],
        "id_tramo_nucleo": ctx["id_tramo_nucleo"],
        "contexto_proceso": "cop_original",
        "tipo_asamblea": "anuencia",
        "resultado_anuencia": "otorgada",
        "estatus_asamblea": "completo",
        "fecha_realizada": "2026-02-20"
    }
    res_anu = client.post("/api/asambleas", json=data_anu, headers=ctx["auth"])
    assert res_anu.status_code == 201, res_anu.text
    ctx["id_asamblea_anuencia"] = res_anu.json()["id_asamblea"]
    register_cleanup(ctx, "/api/asambleas", ctx["id_asamblea_anuencia"])

def test_08_convenios_variados(ctx):
    # Convenio Ocupación Previa (Colectivo)
    data_cop = {
        "id_tramo_nucleo": ctx["id_tramo_nucleo"],
        "id_afectacion": ctx["id_afec_col"],
        "tipo_afectacion": "colectivo",
        "tipo_convenio": "cop_original",
        "id_asamblea_autorizacion": ctx["id_asamblea_anuencia"],
        "superficie_real_afectada_ha": 10.5,
        "monto_100": 5000000.00
    }
    res_cop = client.post("/api/convenios", json=data_cop, headers=ctx["auth"])
    assert res_cop.status_code == 201, res_cop.text
    register_cleanup(ctx, "/api/convenios", res_cop.json()["id_convenio"])

    # Convenio Ampliacion (Individual)
    data_obra = {
        "id_tramo_nucleo": ctx["id_tramo_nucleo"],
        "id_afectacion": ctx["id_afec_ind"],
        "tipo_afectacion": "individual",
        "tipo_convenio": "ampliacion",
        "superficie_ampliacion_ha": 0.5,
        "monto_100": 150000.00
    }
    res_obra = client.post("/api/convenios", json=data_obra, headers=ctx["auth"])
    assert res_obra.status_code == 201, res_obra.text
    register_cleanup(ctx, "/api/convenios", res_obra.json()["id_convenio"])

def test_09_orv(ctx):
    data = {
        "id_nucleo": ctx["id_nucleo"],
        "inicio_vigencia": "2026-01-01",
        "fin_vigencia": "2028-12-31",
        "comisariado_presidente": "Juan Perez",
        "acta_eleccion_inscrita_ran": True
    }
    res = client.post("/api/orvs", json=data, headers=ctx["auth"])
    assert res.status_code == 201, res.text
    register_cleanup(ctx, "/api/orvs", res.json()["id_orv"])

def test_10_padron(ctx):
    data = {
        "id_nucleo": ctx["id_nucleo"],
        "fecha_padron": "2025-12-01",
        "numero_ejidatarios_comuneros": 150
    }
    res = client.post("/api/padrones", json=data, headers=ctx["auth"])
    assert res.status_code == 201, res.text
    register_cleanup(ctx, "/api/padrones", res.json()["id_padron"])

def test_11_actividades_campo(ctx):
    data = {
        "id_tramo_nucleo": ctx["id_tramo_nucleo"],
        "tipo_actividad": "sensibilizacion",
        "contexto_proceso": "cop_original",
        "fecha_programada": "2026-02-01",
        "fecha_realizada": "2026-02-05"
    }
    res = client.post("/api/actividades-campo", json=data, headers=ctx["auth"])
    assert res.status_code == 201, res.text
    register_cleanup(ctx, "/api/actividades-campo", res.json()["id_actividad"])

def test_12_tramites_fifonafe(ctx):
    data = {
        "id_tramo_nucleo": ctx["id_tramo_nucleo"],
        "id_afectacion": ctx["id_afec_col"],
        "tipo_afectacion": "colectivo",
        "tipo_tramite": "indemnizacion",
        "estatus": "programado"
    }
    res = client.post("/api/fifonafe", json=data, headers=ctx["auth"])
    assert res.status_code == 201, res.text
    register_cleanup(ctx, "/api/fifonafe", res.json()["id_tramite_fifonafe"])

def test_13_documentacion(ctx):
    data = {
        "entidad_relacionada_id": ctx["id_nucleo"],
        "entidad_relacionada_tipo": "nucleo_agrario",
        "tipo_documento": "Acta de Asamblea",
        "categoria": "disponible",
        "es_critico": True
    }
    res = client.post("/api/documentacion", json=data, headers=ctx["auth"])
    assert res.status_code == 201, res.text
    register_cleanup(ctx, "/api/documentacion", res.json()["id_documento"])

def test_14_alertas(ctx):
    res = client.get("/api/alertas", headers=ctx["auth"])
    assert res.status_code == 200, res.text
    assert isinstance(res.json(), list)

def test_15_dashboard(ctx):
    res = client.get("/api/dashboard", headers=ctx["auth"])
    assert res.status_code == 200, res.text
    assert isinstance(res.json(), list)

def test_16_reportes(ctx):
    res = client.get("/api/reportes/resumen", headers=ctx["auth"])
    assert res.status_code == 200, res.text
    assert isinstance(res.json(), dict)

def test_99_limpieza_ordenada(ctx):
    # Borra los registros generados asegurando que no queden datos basura (LIFO)
    auth = ctx["auth"]
    for endpoint, item_id in ctx["cleanup_stack"]:
        res = client.delete(f"{endpoint}/{item_id}?motivo=Limpieza pytest profesional", headers=auth)
        assert res.status_code == 200, f"No se pudo limpiar {endpoint}/{item_id}: {res.text}"
