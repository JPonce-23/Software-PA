"""Aislamiento por subexpediente y documentación del Subcorte 2C."""

import time


OFICIOS = {
    "no_oficio_fifonafe_a_dgaopr": "FIF-2C",
    "no_oficio_dgaopr_a_repr": "DGA-2C",
    "no_oficio_rpta_repr_a_dgaopr": "REP-2C",
    "no_oficio_rpta_dgaopr_a_fifonafe": "RFI-2C",
    "fecha_oficio_fifonafe_a_dgaopr": "2026-08-04",
    "fecha_oficio_dgaopr_a_repr": "2026-08-04",
    "fecha_oficio_rpta_repr_a_dgaopr": "2026-08-04",
    "fecha_oficio_rpta_dgaopr_a_fifonafe": "2026-08-04",
}


def _ciclo_original(client, headers, id_afectacion):
    response = client.get(f"/api/afectaciones/{id_afectacion}/ciclos", headers=headers)
    assert response.status_code == 200, response.text
    return next(item for item in response.json() if item["tipo_ciclo"] == "cop_original")


def _crear_afectacion_colectiva(client, headers, cleanup, nucleo, tramo_nucleo, suffix):
    response = client.post(
        "/api/afectaciones",
        json={
            "id_nucleo": nucleo["id_nucleo"],
            "id_tramo_nucleo": tramo_nucleo["id_tramo_nucleo"],
            "tipo_afectacion": "colectivo",
            "tipo_tenencia": f"Uso Común {suffix}",
            "destino_superficie": "Vías férreas",
            "superficie_afectada_ha": "1.0000",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    afectacion = response.json()
    cleanup.register("/api/afectaciones", afectacion["id_afectacion"])
    return afectacion, _ciclo_original(client, headers, afectacion["id_afectacion"])


def _crear_asamblea(client, headers, cleanup, nucleo, tramo_nucleo, afectacion, ciclo):
    response = client.post(
        "/api/asambleas",
        json={
            "id_nucleo": nucleo["id_nucleo"],
            "id_tramo_nucleo": tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "tipo_asamblea": "anuencia",
            "contexto_proceso": "cop_original",
            "resultado_anuencia": "otorgada",
            "estatus_asamblea": "completo",
            "fecha_realizada": "2026-08-04",
            "ingreso_ran_fecha": "2026-08-04",
            "acta_inscripcion_fecha_ran": "2026-08-04",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    asamblea = response.json()
    cleanup.register("/api/asambleas", asamblea["id_asamblea"])
    return asamblea


def _crear_convenio(client, headers, cleanup, tramo_nucleo, afectacion, ciclo, asamblea):
    response = client.post(
        "/api/convenios",
        json={
            "id_tramo_nucleo": tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "id_asamblea_autorizacion": asamblea["id_asamblea"],
            "tipo_afectacion": "colectivo",
            "tipo_convenio": "cop_original",
            "fecha_firma": "2026-08-04",
            "monto_90": "90.00",
            "monto_100": "100.00",
            "monto_bdt": "10.00",
            "superficie_real_afectada_ha": "1.0000",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    convenio = response.json()
    cleanup.register("/api/convenios", convenio["id_convenio"])
    updated = client.put(
        f"/api/convenios/{convenio['id_convenio']}",
        json={
            "ingreso_ran_fecha": "2026-08-04",
            "numero_solicitud_ingreso": f"RAN-2C-{convenio['id_convenio']}",
            "convenio_inscrito_fecha_ran": "2026-08-04",
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    return updated.json()


def _crear_fifonafe_y_pago(client, headers, cleanup, tramo_nucleo, afectacion, ciclo, convenio):
    informe = client.post(
        "/api/fifonafe",
        json={
            "id_tramo_nucleo": tramo_nucleo["id_tramo_nucleo"],
            "id_convenio": convenio["id_convenio"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "tipo_afectacion": "colectivo",
            "tipo_tramite": "informe_no_conflictos",
            "estatus": "completo",
            "hay_conflictos": False,
            **OFICIOS,
        },
        headers=headers,
    )
    assert informe.status_code == 201, informe.text
    cleanup.register("/api/fifonafe", informe.json()["id_tramite_fifonafe"])
    indemnizacion = client.post(
        "/api/fifonafe",
        json={
            "id_tramo_nucleo": tramo_nucleo["id_tramo_nucleo"],
            "id_convenio": convenio["id_convenio"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "id_tramite_no_conflictos": informe.json()["id_tramite_fifonafe"],
            "tipo_afectacion": "colectivo",
            "tipo_tramite": "indemnizacion",
        },
        headers=headers,
    )
    assert indemnizacion.status_code == 201, indemnizacion.text
    tramite = indemnizacion.json()
    cleanup.register("/api/fifonafe", tramite["id_tramite_fifonafe"])
    pago = client.post(
        "/api/pagos-indemnizacion",
        json={
            "id_tramite_fifonafe": tramite["id_tramite_fifonafe"],
            "monto_pagado": "10.00",
            "fecha_pago": "2026-08-04",
            "tipo_pago": "parcial",
            "beneficiario_externo": f"Beneficiario 2C {afectacion['id_afectacion']}",
        },
        headers=headers,
    )
    assert pago.status_code == 201, pago.text
    cleanup.register("/api/pagos-indemnizacion", pago.json()["id_pago"])
    return tramite, pago.json()


def test_documentos_y_subexpediente_aislan_afectaciones(
    client, admin_headers, cleanup, seed_nucleo, seed_tramo_nucleo,
):
    afectacion_a, ciclo_a = _crear_afectacion_colectiva(
        client, admin_headers, cleanup, seed_nucleo, seed_tramo_nucleo, "A"
    )
    afectacion_b, _ = _crear_afectacion_colectiva(
        client, admin_headers, cleanup, seed_nucleo, seed_tramo_nucleo, "B"
    )
    documentos = []
    for entidad_tipo, entidad_id, nombre in (
        ("tramo_nucleo", seed_tramo_nucleo["id_tramo_nucleo"], "Maestro 2C"),
        ("afectacion", afectacion_a["id_afectacion"], "Afectacion A"),
        ("afectacion", afectacion_b["id_afectacion"], "Afectacion B"),
    ):
        response = client.post(
            "/api/documentacion",
            json={
                "entidad_relacionada_tipo": entidad_tipo,
                "entidad_relacionada_id": entidad_id,
                "tipo_documento": nombre,
                "categoria": "disponible",
                "es_critico": False,
            },
            headers=admin_headers,
        )
        assert response.status_code == 201, response.text
        documento = response.json()
        cleanup.register("/api/documentacion", documento["id_documento"])
        documentos.append(documento)

    docs_a = client.get(
        "/api/documentacion",
        params={
            "entidad_tipo": "afectacion",
            "entidad_id": afectacion_a["id_afectacion"],
        },
        headers=admin_headers,
    )
    assert docs_a.status_code == 200, docs_a.text
    assert {item["tipo_documento"] for item in docs_a.json()} == {"Afectacion A"}

    subexpediente = client.get(
        "/api/tramos-nucleos/"
        f"{seed_tramo_nucleo['id_tramo_nucleo']}/afectaciones/"
        f"{afectacion_a['id_afectacion']}/subexpediente",
        headers=admin_headers,
    )
    assert subexpediente.status_code == 200, subexpediente.text
    body = subexpediente.json()
    assert body["id_afectacion"] == afectacion_a["id_afectacion"]
    assert body["estado"]["id_afectacion"] == afectacion_a["id_afectacion"]
    assert {doc["tipo_documento"] for doc in body["documentos_maestros"]} == {
        "Maestro 2C"
    }
    assert all(
        item["id_ciclo_afectacion"] is None
        for item in body["antecedentes_compartidos"]
    )

    propia = client.post(
        "/api/minutas",
        json={
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": afectacion_a["id_afectacion"],
            "id_ciclo_afectacion": ciclo_a["id_ciclo_afectacion"],
            "fecha_reunion": "2026-08-04",
            "asunto": "Minuta propia A",
        },
        headers=admin_headers,
    )
    assert propia.status_code == 201, propia.text
    cleanup.register("/api/minutas", propia.json()["id_minuta"])
    compartida = client.post(
        "/api/minutas",
        json={
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "fecha_reunion": "2026-08-04",
            "asunto": "Minuta compartida",
        },
        headers=admin_headers,
    )
    assert compartida.status_code == 201, compartida.text
    cleanup.register("/api/minutas", compartida.json()["id_minuta"])

    minutas_a = client.get(
        "/api/minutas",
        params={
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": afectacion_a["id_afectacion"],
        },
        headers=admin_headers,
    )
    assert minutas_a.status_code == 200, minutas_a.text
    assert {item["asunto"] for item in minutas_a.json()} == {"Minuta propia A"}

    minutas_compartidas = client.get(
        "/api/minutas",
        params={
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "solo_compartidas": True,
        },
        headers=admin_headers,
    )
    assert minutas_compartidas.status_code == 200, minutas_compartidas.text
    assert "Minuta compartida" in {
        item["asunto"] for item in minutas_compartidas.json()
    }


def test_listados_operativos_filtran_por_afectacion(
    client, admin_headers, cleanup, seed_nucleo, seed_tramo_nucleo,
):
    afectacion_a, ciclo_a = _crear_afectacion_colectiva(
        client, admin_headers, cleanup, seed_nucleo, seed_tramo_nucleo, "Filtro A"
    )
    afectacion_b, ciclo_b = _crear_afectacion_colectiva(
        client, admin_headers, cleanup, seed_nucleo, seed_tramo_nucleo, "Filtro B"
    )
    asamblea_a = _crear_asamblea(
        client, admin_headers, cleanup, seed_nucleo, seed_tramo_nucleo,
        afectacion_a, ciclo_a,
    )
    asamblea_b = _crear_asamblea(
        client, admin_headers, cleanup, seed_nucleo, seed_tramo_nucleo,
        afectacion_b, ciclo_b,
    )
    convenio_a = _crear_convenio(
        client, admin_headers, cleanup, seed_tramo_nucleo,
        afectacion_a, ciclo_a, asamblea_a,
    )
    convenio_b = _crear_convenio(
        client, admin_headers, cleanup, seed_tramo_nucleo,
        afectacion_b, ciclo_b, asamblea_b,
    )
    tramite_a, pago_a = _crear_fifonafe_y_pago(
        client, admin_headers, cleanup, seed_tramo_nucleo,
        afectacion_a, ciclo_a, convenio_a,
    )
    tramite_b, _ = _crear_fifonafe_y_pago(
        client, admin_headers, cleanup, seed_tramo_nucleo,
        afectacion_b, ciclo_b, convenio_b,
    )

    asambleas = client.get(
        "/api/asambleas",
        params={"id_afectacion": afectacion_a["id_afectacion"]},
        headers=admin_headers,
    )
    assert {item["id_asamblea"] for item in asambleas.json()} == {
        asamblea_a["id_asamblea"]
    }
    convenios = client.get(
        "/api/convenios",
        params={"id_afectacion": afectacion_a["id_afectacion"]},
        headers=admin_headers,
    )
    assert {item["id_convenio"] for item in convenios.json()} == {
        convenio_a["id_convenio"]
    }
    tramites = client.get(
        "/api/fifonafe",
        params={"id_afectacion": afectacion_a["id_afectacion"]},
        headers=admin_headers,
    )
    assert tramite_a["id_tramite_fifonafe"] in {
        item["id_tramite_fifonafe"] for item in tramites.json()
    }
    assert {item["id_afectacion"] for item in tramites.json()} == {
        afectacion_a["id_afectacion"]
    }
    assert tramite_b["id_tramite_fifonafe"] not in {
        item["id_tramite_fifonafe"] for item in tramites.json()
    }
    pagos = client.get(
        "/api/pagos-indemnizacion",
        params={"id_afectacion": afectacion_a["id_afectacion"]},
        headers=admin_headers,
    )
    assert {item["id_pago"] for item in pagos.json()} == {pago_a["id_pago"]}


def test_documentacion_respeta_pertenencia_territorial(
    client, admin_headers, cleanup, seed_afectacion_colectiva,
):
    documento = client.post(
        "/api/documentacion",
        json={
            "entidad_relacionada_tipo": "afectacion",
            "entidad_relacionada_id": seed_afectacion_colectiva["id_afectacion"],
            "tipo_documento": "Territorial 2C",
            "categoria": "disponible",
            "es_critico": False,
        },
        headers=admin_headers,
    )
    assert documento.status_code == 201, documento.text
    cleanup.register("/api/documentacion", documento.json()["id_documento"])

    correo = f"operador.2c.{time.time_ns()}@pruebas.local"
    created = client.post(
        "/api/usuarios",
        json={
            "nombre": "Operador",
            "apellido_paterno": "SinTramo",
            "correo": correo,
            "rol": "operador",
            "contrasena": "Prueba2C!2026",
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    cleanup.register("/api/usuarios", created.json()["id_usuario"])
    login = client.post(
        "/api/auth/login",
        data={"username": correo, "password": "Prueba2C!2026"},
    )
    assert login.status_code == 200, login.text
    operator_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    denied = client.get(
        "/api/documentacion",
        params={
            "entidad_tipo": "afectacion",
            "entidad_id": seed_afectacion_colectiva["id_afectacion"],
        },
        headers=operator_headers,
    )
    assert denied.status_code == 403
    denied_versions = client.get(
        f"/api/documentacion/{documento.json()['id_documento']}/versiones",
        headers=operator_headers,
    )
    assert denied_versions.status_code == 403
