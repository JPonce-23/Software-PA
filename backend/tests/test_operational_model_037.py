import pytest
import datetime

@pytest.fixture(scope="module")
def catalogs(api):
    tipo_tierras = api("GET", "/api/catalogos/operativos/tipo_tierra").json()
    tipo_gestiones = api("GET", "/api/catalogos/operativos/tipo_gestion").json()
    destinos = api("GET", "/api/catalogos/operativos/destino_superficie").json()
    titularidades = api("GET", "/api/catalogos/operativos/tipo_titularidad_unidad").json()
    motivos_tuc = api("GET", "/api/catalogos/operativos/motivo_no_afecta_tuc").json()
    tipos_cop = api("GET", "/api/catalogos/operativos/tipo_cop_operativo").json()
    
    return {
        "tipo_tierra": tipo_tierras[0]["id_catalogo_opcion"],
        "tipo_gestion_parcela": next((c["id_catalogo_opcion"] for c in tipo_gestiones if c["codigo"] == "PARCELA"), tipo_gestiones[0]["id_catalogo_opcion"]),
        "destino_parcela_escolar": next((c["id_catalogo_opcion"] for c in destinos if c["codigo"] == "parcela_escolar"), destinos[0]["id_catalogo_opcion"]),
        "titularidad": titularidades[0]["id_catalogo_opcion"],
        "motivo_tuc": motivos_tuc[0]["id_catalogo_opcion"] if motivos_tuc else None,
        "tipo_cop_origen": next((c["id_catalogo_opcion"] for c in tipos_cop if c["codigo"] == "ORIGEN"), tipos_cop[0]["id_catalogo_opcion"] if tipos_cop else None)
    }

def test_01_crear_unidad_agraria(api, target_domain, catalogs):
    pn = target_domain["project_nucleus"]
    nucleo_id = target_domain["nucleus"]["id_nucleo"]
    
    payload = {
        "id_tipo_tierra": catalogs["tipo_tierra"],
        "id_tipo_titularidad": catalogs["titularidad"], "referencia_alfanumerica": "UA-TEST-05",
        "referencia_alfanumerica": "UA-TEST-01",
        "fuente": "pytest"
    }
    
    resp = api("POST", f"/api/nucleos/{nucleo_id}/unidades-agrarias", json=payload, expected=201)
    data = resp.json()
    assert data["id_nucleo"] == nucleo_id
    assert data["referencia_alfanumerica"] == "UA-TEST-01"
    assert "id_unidad_agraria" in data

def test_02_listar_unidades_por_nucleo(api, target_domain):
    nucleo_id = target_domain["nucleus"]["id_nucleo"]
    resp = api("GET", f"/api/nucleos/{nucleo_id}/unidades-agrarias")
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(u["referencia_alfanumerica"] == "UA-TEST-01" for u in data)

def test_03_actualizar_unidad_agraria(api, target_domain):
    nucleo_id = target_domain["nucleus"]["id_nucleo"]
    units = api("GET", f"/api/nucleos/{nucleo_id}/unidades-agrarias").json()
    ua_id = next(u["id_unidad_agraria"] for u in units if u["referencia_alfanumerica"] == "UA-TEST-01")
    
    resp = api("PATCH", f"/api/unidades-agrarias/{ua_id}", json={"detalle": "Updated by pytest"})
    data = resp.json()
    assert data["detalle"] == "Updated by pytest"

def test_04_asociar_afectacion_unidad_agraria(api, target_domain):
    nucleo_id = target_domain["nucleus"]["id_nucleo"]
    units = api("GET", f"/api/nucleos/{nucleo_id}/unidades-agrarias").json()
    ua_id = next(u["id_unidad_agraria"] for u in units if u["referencia_alfanumerica"] == "UA-TEST-01")
    
    afectacion_id = target_domain["collective"][0]["id_afectacion"]
    
    payload = {
        "id_unidad_agraria": ua_id,
        "superficie_preliminar_ha": "1.500000",
        "fuente": "pytest"
    }
    resp = api("POST", f"/api/afectaciones/{afectacion_id}/unidades-agrarias", json=payload, expected=201)
    data = resp.json()
    assert data["id_afectacion"] == afectacion_id
    assert data["id_unidad_agraria"] == ua_id
    assert "id_afectacion_unidad" in data

def test_05_rechazar_asociacion_otro_nucleo(api, target_domain, catalogs):
    proj_id = target_domain["project"]["id_proyecto"]
    mun_id = target_domain["municipality"]["id_municipio"]
    
    import uuid
    uid = uuid.uuid4().hex[:6]
    nuc2 = api("POST", "/api/nucleos", json={
        "id_municipio": mun_id, "nombre_nucleo": f"NUC-2-{uid}", "tipo_nucleo": "ejido", "fuente_datos": "qa"
    }, expected=201).json()
    
    api("POST", f"/api/proyectos/{proj_id}/nucleos", json={
        "id_nucleo": nuc2["id_nucleo"], "residencia": "RES2", "referencias": []
    }, expected=201)
    
    ua2 = api("POST", f"/api/nucleos/{nuc2['id_nucleo']}/unidades-agrarias", json={
        "id_tipo_tierra": catalogs["tipo_tierra"],
        "id_tipo_titularidad": catalogs["titularidad"], "referencia_alfanumerica": "UA-TEST-05"
    }, expected=201).json()
    
    afectacion_id = target_domain["collective"][0]["id_afectacion"]
    
    api("POST", f"/api/afectaciones/{afectacion_id}/unidades-agrarias", json={
        "id_unidad_agraria": ua2["id_unidad_agraria"]
    }, expected=409)

def test_06_evitar_asociacion_duplicada(api, target_domain):
    nucleo_id = target_domain["nucleus"]["id_nucleo"]
    units = api("GET", f"/api/nucleos/{nucleo_id}/unidades-agrarias").json()
    ua_id = next(u["id_unidad_agraria"] for u in units if u["referencia_alfanumerica"] == "UA-TEST-01")
    
    afectacion_id = target_domain["collective"][0]["id_afectacion"]
    
    api("POST", f"/api/afectaciones/{afectacion_id}/unidades-agrarias", json={
        "id_unidad_agraria": ua_id
    }, expected=409)

def test_07_colectivo_gestion_parcela_escolar_valido(api, target_domain, catalogs):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    
    resp = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", json={
        "tipo_afectacion": "colectivo",
        "id_tipo_cop_operativo": catalogs["tipo_cop_origen"],
        "superficie_preliminar_ha": "2.0"
    }, expected=201)
    
    af_id = resp.json()["id_afectacion"]
    
    ua = api("POST", f"/api/nucleos/{target_domain['nucleus']['id_nucleo']}/unidades-agrarias", json={
        "id_tipo_tierra": catalogs["tipo_tierra"],
        "id_tipo_titularidad": catalogs["titularidad"], "referencia_alfanumerica": "UA-TEST-05",
        "id_tipo_gestion": catalogs["tipo_gestion_parcela"],
        "id_destino_superficie": catalogs["destino_parcela_escolar"],
        "referencia_alfanumerica": "UA-PARCELA-ESCOLAR"
    }, expected=201).json()
    
    api("POST", f"/api/afectaciones/{af_id}/unidades-agrarias", json={
        "id_unidad_agraria": ua["id_unidad_agraria"]
    }, expected=201)

def test_08_individual_con_parcela_valido(api, target_domain, catalogs):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    import uuid
    parcel = api("POST", f"/api/proyecto-nucleo/{pn_id}/parcelas", json={
        "tipo_parcela": "individual", "no_parcela": f"P-TEST-IND-{uuid.uuid4().hex[:6]}"
    }, expected=201).json()
    
    af = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", json={
        "tipo_afectacion": "individual",
        "id_parcela": parcel["id_parcela"]
    }, expected=201).json()
    
    ua = api("POST", f"/api/nucleos/{target_domain['nucleus']['id_nucleo']}/unidades-agrarias", json={
        "id_tipo_tierra": catalogs["tipo_tierra"],
        "id_tipo_titularidad": catalogs["titularidad"], "referencia_alfanumerica": "UA-TEST-05",
        "id_parcela": parcel["id_parcela"]
    }, expected=201).json()
    
    api("POST", f"/api/afectaciones/{af['id_afectacion']}/unidades-agrarias", json={
        "id_unidad_agraria": ua["id_unidad_agraria"]
    }, expected=201)

def test_09_reutilizar_misma_unidad(api, target_domain):
    nucleo_id = target_domain["nucleus"]["id_nucleo"]
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    
    units = api("GET", f"/api/nucleos/{nucleo_id}/unidades-agrarias").json()
    ua_id = next(u["id_unidad_agraria"] for u in units if u["referencia_alfanumerica"] == "UA-TEST-01")
    
    af_2 = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", json={
        "tipo_afectacion": "colectivo",
        "superficie_preliminar_ha": "1.0"
    }, expected=201).json()
    
    api("POST", f"/api/afectaciones/{af_2['id_afectacion']}/unidades-agrarias", json={
        "id_unidad_agraria": ua_id
    }, expected=201)

def test_10_tipo_cop_en_afectacion(api, target_domain, catalogs):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    af = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", json={
        "tipo_afectacion": "colectivo",
        "id_tipo_cop_operativo": catalogs["tipo_cop_origen"]
    }, expected=201).json()
    
    assert af["id_tipo_cop_operativo"] == catalogs["tipo_cop_origen"]
    
    af_upd = api("PATCH", f"/api/afectaciones/{af['id_afectacion']}", json={
        "tipo_cop_revision_pendiente": True, "tipo_cop_revision_detalle": "Por revisar"
    }, expected=200).json()
    assert af_upd["tipo_cop_revision_pendiente"] is True


def test_11_afecta_tuc_false(api, target_domain, catalogs):
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    motivo = catalogs["motivo_tuc"]
    
    resp = api("PATCH", f"/api/proyecto-nucleo/{pn_id}", json={
        "afecta_tuc": False,
        "id_motivo_no_afecta_tuc": motivo
    }, expected=200).json()
    
    # Verify in DB directly because view doesn't return afecta_tuc
    import os
    import psycopg2
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_RUNTIME_USER", "pa_runtime"),
        password=os.environ.get("DB_RUNTIME_PASSWORD", "suzuka+sp4")
    )
    cur = conn.cursor()
    cur.execute("SELECT afecta_tuc, id_motivo_no_afecta_tuc FROM proyecto_nucleo WHERE id_proyecto_nucleo = %s", (pn_id,))
    row = cur.fetchone()
    conn.close()
    
    assert row[0] is False
    if motivo:
        assert row[1] == motivo

def test_12_rbac_escritura(client, target_domain, catalogs):
    nucleo_id = target_domain["nucleus"]["id_nucleo"]
    resp = client.post(f"/api/nucleos/{nucleo_id}/unidades-agrarias", json={
        "id_tipo_tierra": catalogs["tipo_tierra"],
        "id_tipo_titularidad": catalogs["titularidad"], "referencia_alfanumerica": "UA-TEST-05"
    })
    assert resp.status_code in (401, 403)
