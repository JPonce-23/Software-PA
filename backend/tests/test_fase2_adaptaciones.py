"""Pruebas de integración para los contratos incorporados en la Fase 2."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4


def test_parcela_legacy_crea_titular_normalizado(
    client,
    admin_session,
    seed_parcela,
):
    response = client.get(
        f"/api/parcelas/{seed_parcela['id_parcela']}/titulares",
        headers=admin_session,
    )
    assert response.status_code == 200
    titulares = response.json()
    assert len(titulares) == 1
    assert titulares[0]["persona"]["nombre"] == seed_parcela["nombre_titular"]


def test_orv_legacy_crea_integrante_normalizado(
    client,
    admin_session,
    cleanup,
    seed_nucleo,
):
    payload = {
        "id_nucleo": seed_nucleo["id_nucleo"],
        "inicio_vigencia": "2026-01-01",
        "fin_vigencia": "2028-12-31",
        "comisariado_presidente": "Representante de prueba",
    }
    created = client.post("/api/orvs", json=payload, headers=admin_session)
    assert created.status_code == 201, created.text
    id_orv = created.json()["id_orv"]
    cleanup.register("/api/orvs", id_orv)

    response = client.get(
        f"/api/orvs/{id_orv}/integrantes",
        headers=admin_session,
    )
    assert response.status_code == 200
    integrantes = response.json()
    assert len(integrantes) == 1
    assert integrantes[0]["cargo"] == "comisariado_presidente"
    assert integrantes[0]["persona"]["nombre"] == "Representante de prueba"


def test_parcela_normalizada_es_atomica_y_filtrable_por_persona(
    client,
    admin_session,
    cleanup,
    seed_nucleo,
):
    created_person = client.post(
        "/api/personas",
        json={"nombre": "Titular normalizado"},
        headers=admin_session,
    )
    assert created_person.status_code == 201, created_person.text
    persona = created_person.json()
    cleanup.register("/api/personas", persona["id_persona"])

    created_parcel = client.post(
        "/api/parcelas/con-titular",
        json={
            "parcela": {
                "id_nucleo": seed_nucleo["id_nucleo"],
                "tipo_parcela": "individual",
                "no_parcela_ppt": "NORMALIZADA-1",
            },
            "titular": {
                "id_persona": persona["id_persona"],
                "tipo_derecho": "titular",
            },
        },
        headers=admin_session,
    )
    assert created_parcel.status_code == 201, created_parcel.text
    parcela = created_parcel.json()
    cleanup.register("/api/parcelas", parcela["id_parcela"])
    assert parcela["nombre_titular"] is None

    filtered = client.get(
        "/api/parcelas",
        params={
            "id_nucleo": seed_nucleo["id_nucleo"],
            "id_persona": persona["id_persona"],
        },
        headers=admin_session,
    )
    assert filtered.status_code == 200
    assert [item["id_parcela"] for item in filtered.json()] == [
        parcela["id_parcela"]
    ]


def test_persona_normaliza_identidad_y_rechaza_curp_duplicada(
    client,
    admin_session,
    cleanup,
):
    token = uuid4().hex
    iniciales = "".join(chr(ord("A") + int(char, 16)) for char in token[:4])
    curp = f"{iniciales}800101HDFPPS{token[4].upper()}{int(token[5], 16) % 10}"
    payload = {
        "nombre": "  María  ",
        "curp": curp.lower(),
        "rfc": "",
    }
    created = client.post("/api/personas", json=payload, headers=admin_session)
    assert created.status_code == 201, created.text
    persona = created.json()
    cleanup.register("/api/personas", persona["id_persona"])
    assert persona["nombre"] == "María"
    assert persona["curp"] == curp
    assert persona["rfc"] is None

    duplicate = client.post(
        "/api/personas",
        json={"nombre": "Homónima", "curp": curp},
        headers=admin_session,
    )
    assert duplicate.status_code == 409


def test_minuta_y_acuerdo_validan_expediente_y_responsable(
    client,
    admin_session,
    cleanup,
    seed_tramo_nucleo,
):
    minuta_response = client.post(
        "/api/minutas",
        json={
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "fecha_reunion": "2026-07-28",
            "asunto": "Seguimiento de liberación",
        },
        headers=admin_session,
    )
    assert minuta_response.status_code == 201, minuta_response.text
    minuta = minuta_response.json()
    cleanup.register("/api/minutas", minuta["id_minuta"])

    acuerdo_response = client.post(
        f"/api/minutas/{minuta['id_minuta']}/acuerdos",
        json={
            "descripcion": "Entregar expediente conciliado",
            "responsable_externo": "Enlace institucional",
            "fecha_limite": "2026-08-15",
        },
        headers=admin_session,
    )
    assert acuerdo_response.status_code == 201, acuerdo_response.text
    acuerdo = acuerdo_response.json()
    cleanup.register("/api/acuerdos", acuerdo["id_acuerdo"])
    assert acuerdo["estatus"] == "pendiente"

    invalid = client.put(
        f"/api/acuerdos/{acuerdo['id_acuerdo']}",
        json={"estatus": "cumplido"},
        headers=admin_session,
    )
    assert invalid.status_code == 400


def test_documento_genera_version_inmutable(
    client,
    admin_session,
    cleanup,
    seed_nucleo,
):
    created = client.post(
        "/api/documentacion",
        json={
            "entidad_relacionada_id": seed_nucleo["id_nucleo"],
            "entidad_relacionada_tipo": "nucleo_agrario",
            "tipo_documento": "Acta",
            "categoria": "disponible",
        },
        headers=admin_session,
    )
    assert created.status_code == 201, created.text
    id_documento = created.json()["id_documento"]
    cleanup.register("/api/documentacion", id_documento)

    uploaded = client.post(
        f"/api/documentacion/{id_documento}/archivo",
        files={"file": ("acta.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf")},
        headers=admin_session,
    )
    assert uploaded.status_code == 201, uploaded.text
    version = uploaded.json()
    assert version["numero_version"] == 1
    assert version["tamano_bytes"] == 15
    assert len(version["hash_sha256"]) == 64

    versions = client.get(
        f"/api/documentacion/{id_documento}/versiones",
        headers=admin_session,
    )
    assert versions.status_code == 200
    assert [item["numero_version"] for item in versions.json()] == [1]

    def upload_concurrent(name: str):
        return client.post(
            f"/api/documentacion/{id_documento}/archivo",
            files={
                "file": (
                    name,
                    f"%PDF-1.4\n{name}\n%%EOF\n".encode(),
                    "application/pdf",
                )
            },
            headers=admin_session,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(upload_concurrent, ("segunda.pdf", "tercera.pdf"))
        )
    assert [response.status_code for response in responses] == [201, 201]
    assert sorted(response.json()["numero_version"] for response in responses) == [
        2,
        3,
    ]

    downloaded = client.get(
        f"/api/documentacion/{id_documento}/versiones/1/archivo",
        headers=admin_session,
    )
    assert downloaded.status_code == 200
    assert downloaded.content == b"%PDF-1.4\n%%EOF\n"


def test_pago_respeta_monto_tierra_mas_bdt(
    client,
    admin_session,
    cleanup,
    seed_nucleo,
    seed_tramo_nucleo,
):
    afectacion_response = client.post(
        "/api/afectaciones",
        json={
            "id_nucleo": seed_nucleo["id_nucleo"],
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "tipo_afectacion": "colectivo",
            "tipo_tenencia": "Uso Común",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        },
        headers=admin_session,
    )
    assert afectacion_response.status_code == 201, afectacion_response.text
    afectacion = afectacion_response.json()
    cleanup.register("/api/afectaciones", afectacion["id_afectacion"])
    ciclo = client.get(
        f"/api/afectaciones/{afectacion['id_afectacion']}/ciclos",
        headers=admin_session,
    ).json()[0]
    asamblea_response = client.post(
        "/api/asambleas",
        json={
            "id_nucleo": seed_nucleo["id_nucleo"],
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "tipo_asamblea": "anuencia",
            "contexto_proceso": "cop_original",
            "resultado_anuencia": "otorgada",
            "estatus_asamblea": "completo",
            "fecha_realizada": "2026-07-20",
            "ingreso_ran_fecha": "2026-07-21",
            "acta_inscripcion_fecha_ran": "2026-07-22",
        },
        headers=admin_session,
    )
    assert asamblea_response.status_code == 201, asamblea_response.text
    asamblea = asamblea_response.json()
    cleanup.register("/api/asambleas", asamblea["id_asamblea"])
    convenio_response = client.post(
        "/api/convenios",
        json={
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "id_asamblea_autorizacion": asamblea["id_asamblea"],
            "tipo_afectacion": "colectivo",
            "tipo_convenio": "cop_original",
            "fecha_firma": "2026-07-23",
            "monto_100": "100.00",
            "monto_bdt": "10.00",
            "superficie_real_afectada_ha": "10.5",
        },
        headers=admin_session,
    )
    assert convenio_response.status_code == 201, convenio_response.text
    convenio = convenio_response.json()
    cleanup.register("/api/convenios", convenio["id_convenio"])
    ran = client.put(
        f"/api/convenios/{convenio['id_convenio']}",
        json={
            "ingreso_ran_fecha": "2026-07-24",
            "numero_solicitud_ingreso": "RAN-PAGO",
            "convenio_inscrito_fecha_ran": "2026-07-25",
        },
        headers=admin_session,
    )
    assert ran.status_code == 200, ran.text

    oficios = {
        "no_oficio_fifonafe_a_dgaopr": "F-1",
        "no_oficio_dgaopr_a_repr": "D-1",
        "no_oficio_rpta_repr_a_dgaopr": "R-1",
        "no_oficio_rpta_dgaopr_a_fifonafe": "RF-1",
        "fecha_oficio_fifonafe_a_dgaopr": "2026-07-25",
        "fecha_oficio_dgaopr_a_repr": "2026-07-25",
        "fecha_oficio_rpta_repr_a_dgaopr": "2026-07-26",
        "fecha_oficio_rpta_dgaopr_a_fifonafe": "2026-07-26",
    }
    informe_response = client.post(
        "/api/fifonafe",
        json={
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_convenio": convenio["id_convenio"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "tipo_afectacion": "colectivo",
            "tipo_tramite": "informe_no_conflictos",
            "estatus": "completo",
            "hay_conflictos": False,
            **oficios,
        },
        headers=admin_session,
    )
    assert informe_response.status_code == 201, informe_response.text
    informe = informe_response.json()
    cleanup.register("/api/fifonafe", informe["id_tramite_fifonafe"])

    tramite_response = client.post(
        "/api/fifonafe",
        json={
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_convenio": convenio["id_convenio"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "id_tramite_no_conflictos": informe["id_tramite_fifonafe"],
            "tipo_afectacion": "colectivo",
            "tipo_tramite": "indemnizacion",
        },
        headers=admin_session,
    )
    assert tramite_response.status_code == 201, tramite_response.text
    tramite = tramite_response.json()
    cleanup.register("/api/fifonafe", tramite["id_tramite_fifonafe"])

    base_payload = {
        "id_tramite_fifonafe": tramite["id_tramite_fifonafe"],
        "fecha_pago": "2026-07-28",
        "tipo_pago": "parcial",
        "beneficiario_externo": "Núcleo agrario de prueba",
    }
    excessive = client.post(
        "/api/pagos-indemnizacion",
        json={**base_payload, "monto_pagado": "110.01"},
        headers=admin_session,
    )
    assert excessive.status_code == 409

    valid = client.post(
        "/api/pagos-indemnizacion",
        json={**base_payload, "monto_pagado": "110.00"},
        headers=admin_session,
    )
    assert valid.status_code == 201, valid.text
    cleanup.register("/api/pagos-indemnizacion", valid.json()["id_pago"])
    assert Decimal(valid.json()["monto_pagado"]) == Decimal("110.00")


def test_contador_alertas_disminuye_al_marcar_como_leida(
    client,
    admin_session,
    cleanup,
    seed_nucleo,
):
    before = client.get("/api/alertas/no-vistas/count", headers=admin_session)
    assert before.status_code == 200

    created = client.post(
        "/api/alertas",
        json={
            "tipo": "documento_faltante",
            "prioridad": "alta",
            "titulo": "Documento de prueba pendiente",
            "entidad_relacionada_id": seed_nucleo["id_nucleo"],
            "entidad_relacionada_tipo": "nucleo_agrario",
        },
        headers=admin_session,
    )
    assert created.status_code == 201, created.text
    id_alerta = created.json()["id_alerta"]
    cleanup.register("/api/alertas", id_alerta)

    unread = client.get("/api/alertas/no-vistas/count", headers=admin_session)
    assert unread.json()["total"] == before.json()["total"] + 1

    marked = client.post(
        f"/api/alertas/{id_alerta}/marcar-leida",
        headers=admin_session,
    )
    assert marked.status_code == 200
    after = client.get("/api/alertas/no-vistas/count", headers=admin_session)
    assert after.json()["total"] == before.json()["total"]
