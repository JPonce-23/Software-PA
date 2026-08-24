"""Reglas críticas de secuencia, cierre y terminalidad del Subcorte 2B."""

from concurrent.futures import ThreadPoolExecutor
import time
from fastapi.testclient import TestClient
from app.config import AUTH_SETTINGS
from app.main import app

ORIGIN = AUTH_SETTINGS.allowed_origins[0]

OFICIOS = {
    "no_oficio_fifonafe_a_dgaopr": "FIF-001",
    "no_oficio_dgaopr_a_repr": "DGA-001",
    "no_oficio_rpta_repr_a_dgaopr": "REP-001",
    "no_oficio_rpta_dgaopr_a_fifonafe": "RFI-001",
    "fecha_oficio_fifonafe_a_dgaopr": "2026-08-01",
    "fecha_oficio_dgaopr_a_repr": "2026-08-01",
    "fecha_oficio_rpta_repr_a_dgaopr": "2026-08-02",
    "fecha_oficio_rpta_dgaopr_a_fifonafe": "2026-08-02",
}


def _crear_afectacion(client, headers, cleanup, nucleo, tramo_nucleo, tipo, parcela=None):
    payload = {
        "id_nucleo": nucleo["id_nucleo"],
        "id_tramo_nucleo": tramo_nucleo["id_tramo_nucleo"],
        "tipo_afectacion": tipo,
        "tipo_tenencia": "Parcelaria" if tipo == "individual" else "Uso Común",
        "superficie_afectada_ha": "1.2500",
        "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
    }
    if parcela:
        payload["id_parcela"] = parcela["id_parcela"]
    response = client.post("/api/afectaciones", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    afectacion = response.json()
    cleanup.register("/api/afectaciones", afectacion["id_afectacion"])
    ciclos = client.get(
        f"/api/afectaciones/{afectacion['id_afectacion']}/ciclos", headers=headers
    ).json()
    return afectacion, next(c for c in ciclos if c["tipo_ciclo"] == "cop_original")


def _crear_tramo_nucleo_local(client, headers, cleanup, tramo, nucleo):
    payload = {
        "id_tramo": tramo["id_tramo"],
        "id_nucleo": nucleo["id_nucleo"],
        "consecutivo": int(time.time() * 1000) % 100000000,
        "geometria_wkt": "MULTILINESTRING((0 0, 1 1))",
    }
    response = client.post("/api/tramos-nucleos", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    data = response.json()
    cleanup.register("/api/tramos-nucleos", data["id_tramo_nucleo"])
    return data


def _crear_convenio_individual(client, headers, cleanup, tramo_nucleo, afectacion, ciclo):
    response = client.post(
        "/api/convenios",
        json={
            "id_tramo_nucleo": tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "tipo_afectacion": "individual",
            "tipo_convenio": "cop_original",
            "fecha_firma": "2026-07-28",
            "monto_90": "90.00",
            "monto_100": "100.00",
            "monto_bdt": "10.00",
            "superficie_total_ha": "1.2500",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    convenio = response.json()
    cleanup.register("/api/convenios", convenio["id_convenio"])
    registered = client.put(
        f"/api/convenios/{convenio['id_convenio']}",
        json={
            "ingreso_ran_fecha": "2026-07-29",
            "numero_solicitud_ingreso": "RAN-001",
            "convenio_inscrito_fecha_ran": "2026-07-30",
        },
        headers=headers,
    )
    assert registered.status_code == 200, registered.text
    return registered.json()


def _crear_fifonafe_completo(client, headers, cleanup, tramo_nucleo, afectacion, ciclo, convenio):
    informe_response = client.post(
        "/api/fifonafe",
        json={
            "id_tramo_nucleo": tramo_nucleo["id_tramo_nucleo"],
            "id_convenio": convenio["id_convenio"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "tipo_afectacion": afectacion["tipo_afectacion"],
            "tipo_tramite": "informe_no_conflictos",
            "estatus": "completo",
            "hay_conflictos": False,
            **OFICIOS,
        },
        headers=headers,
    )
    assert informe_response.status_code == 201, informe_response.text
    informe = informe_response.json()
    cleanup.register("/api/fifonafe", informe["id_tramite_fifonafe"])

    indemnizacion_response = client.post(
        "/api/fifonafe",
        json={
            "id_tramo_nucleo": tramo_nucleo["id_tramo_nucleo"],
            "id_convenio": convenio["id_convenio"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "id_tramite_no_conflictos": informe["id_tramite_fifonafe"],
            "tipo_afectacion": afectacion["tipo_afectacion"],
            "tipo_tramite": "indemnizacion",
            "estatus": "pendiente",
        },
        headers=headers,
    )
    assert indemnizacion_response.status_code == 201, indemnizacion_response.text
    indemnizacion = indemnizacion_response.json()
    cleanup.register("/api/fifonafe", indemnizacion["id_tramite_fifonafe"])

    limite = float(convenio.get("monto_100") or 0)
    if afectacion["tipo_afectacion"] == "colectivo" or convenio.get("tipo_convenio") != "modificatorio":
        limite += float(convenio.get("monto_bdt") or 0)

    if limite > 0:
        payment = client.post(
            "/api/pagos-indemnizacion",
            json={
                "id_tramite_fifonafe": indemnizacion["id_tramite_fifonafe"],
                "monto_pagado": str(limite),
                "fecha_pago": "2026-08-01",
                "tipo_pago": "total",
                "beneficiario_externo": "Beneficiario de prueba",
            },
            headers=headers,
        )
        assert payment.status_code == 201, payment.text
        cleanup.register("/api/pagos-indemnizacion", payment.json()["id_pago"])

    completed = client.post(
        f"/api/fifonafe/{indemnizacion['id_tramite_fifonafe']}/completar-indemnizacion",
        json={"confirmar": True},
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["no_oficio_fifonafe_a_dgaopr"] is None
    return completed.json()


def test_ciclo_original_y_estado_derivado(
    client, admin_session, seed_afectacion_colectiva,
):
    cycles = client.get(
        f"/api/afectaciones/{seed_afectacion_colectiva['id_afectacion']}/ciclos",
        headers=admin_session,
    )
    assert cycles.status_code == 200
    assert [item["tipo_ciclo"] for item in cycles.json()].count("cop_original") == 1
    state = client.get(
        f"/api/afectaciones/{seed_afectacion_colectiva['id_afectacion']}/estado",
        headers=admin_session,
    )
    assert state.status_code == 200
    assert state.json()["estado_liberacion"] != "liberada"


def test_ciclo_incompatible_se_rechaza(
    client, admin_session, seed_afectacion_colectiva,
):
    response = client.post(
        f"/api/afectaciones/{seed_afectacion_colectiva['id_afectacion']}/ciclos",
        json={"tipo_ciclo": "ampliacion"},
        headers=admin_session,
    )
    assert response.status_code == 409


def test_caminamiento_posterior_exige_sensibilizacion_del_mismo_ciclo(
    client, admin_session, cleanup, seed_afectacion_colectiva, seed_tramo_nucleo,
):
    cycle_response = client.post(
        f"/api/afectaciones/{seed_afectacion_colectiva['id_afectacion']}/ciclos",
        json={"tipo_ciclo": "superficie_adicional"}, headers=admin_session,
    )
    assert cycle_response.status_code == 201, cycle_response.text
    cycle = cycle_response.json()
    walking = {
        "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
        "id_ciclo_afectacion": cycle["id_ciclo_afectacion"],
        "tipo_actividad": "caminamiento",
        "contexto_proceso": "superficie_adicional",
        "fecha_realizada": "2026-08-03",
    }
    blocked = client.post("/api/actividades-campo", json=walking, headers=admin_session)
    assert blocked.status_code == 409
    sensitization = client.post(
        "/api/actividades-campo",
        json={**walking, "tipo_actividad": "sensibilizacion"},
        headers=admin_session,
    )
    assert sensitization.status_code == 201, sensitization.text
    cleanup.register("/api/actividades-campo", sensitization.json()["id_actividad"])
    allowed = client.post("/api/actividades-campo", json=walking, headers=admin_session)
    assert allowed.status_code == 201, allowed.text
    cleanup.register("/api/actividades-campo", allowed.json()["id_actividad"])


def test_individual_se_libera_por_indemnizacion_completa(
    client, admin_session, cleanup, seed_nucleo, seed_tramo_nucleo, seed_parcela,
):
    afectacion, ciclo = _crear_afectacion(
        client, admin_session, cleanup, seed_nucleo, seed_tramo_nucleo,
        "individual", seed_parcela,
    )
    convenio = _crear_convenio_individual(
        client, admin_session, cleanup, seed_tramo_nucleo, afectacion, ciclo,
    )
    _crear_fifonafe_completo(
        client, admin_session, cleanup, seed_tramo_nucleo, afectacion, ciclo, convenio,
    )
    state = client.get(
        f"/api/afectaciones/{afectacion['id_afectacion']}/estado",
        headers=admin_session,
    )
    assert state.status_code == 200
    assert state.json()["estado_financiero"] == "concluido"
    assert state.json()["estado_liberacion"] == "liberada"


def test_salida_terminal_detiene_nuevos_ciclos(
    client, admin_session, cleanup, seed_nucleo, seed_tramo_nucleo,
):
    afectacion, _ = _crear_afectacion(
        client, admin_session, cleanup, seed_nucleo, seed_tramo_nucleo, "colectivo"
    )
    terminal = client.put(
        f"/api/afectaciones/{afectacion['id_afectacion']}/salida-terminal",
        json={
            "tipo_salida_terminal": "fuera_seguimiento_expropiacion",
            "motivo": "Derivación confirmada por el expediente de prueba",
            "confirmar": True,
        },
        headers=admin_session,
    )
    assert terminal.status_code == 200, terminal.text
    blocked = client.post(
        f"/api/afectaciones/{afectacion['id_afectacion']}/ciclos",
        json={"tipo_ciclo": "superficie_adicional"},
        headers=admin_session,
    )
    assert blocked.status_code == 409
    state = client.get(
        f"/api/afectaciones/{afectacion['id_afectacion']}/estado",
        headers=admin_session,
    ).json()
    assert state["estado_liberacion"] == "no_aplica_terminal"


def test_no_afecta_uso_comun_detiene_nuevas_afectaciones(
    client, admin_session, cleanup, seed_tramo, seed_nucleo, seed_parcela,
):
    tramo_nucleo = _crear_tramo_nucleo_local(
        client, admin_session, cleanup, seed_tramo, seed_nucleo
    )
    marked = client.put(
        f"/api/tramos-nucleos/{tramo_nucleo['id_tramo_nucleo']}",
        json={"proyecto_no_afecta_uso_comun": True},
        headers=admin_session,
    )
    assert marked.status_code == 200, marked.text

    blocked = client.post(
        "/api/afectaciones",
        json={
            "id_nucleo": seed_nucleo["id_nucleo"],
            "id_tramo_nucleo": tramo_nucleo["id_tramo_nucleo"],
            "id_parcela": seed_parcela["id_parcela"],
            "tipo_afectacion": "individual",
            "tipo_tenencia": "Parcelaria",
            "superficie_afectada_ha": "1.2500",
            "geometria_wkt": "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))",
        },
        headers=admin_session,
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"]["code"] == "PA_SIN_SEGUIMIENTO_ORDINARIO"


def test_modificatorio_individual_sustituye_sin_sumar_y_respeta_pagado(
    client, admin_session, cleanup, seed_nucleo, seed_tramo_nucleo, seed_parcela,
):
    afectacion, ciclo = _crear_afectacion(
        client, admin_session, cleanup, seed_nucleo, seed_tramo_nucleo,
        "individual", seed_parcela,
    )
    convenio = _crear_convenio_individual(
        client, admin_session, cleanup, seed_tramo_nucleo, afectacion, ciclo,
    )
    informe = client.post(
        "/api/fifonafe",
        json={
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_convenio": convenio["id_convenio"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "tipo_afectacion": "individual",
            "tipo_tramite": "informe_no_conflictos",
            "estatus": "completo",
            "hay_conflictos": False,
            **OFICIOS,
        },
        headers=admin_session,
    )
    assert informe.status_code == 201, informe.text
    cleanup.register("/api/fifonafe", informe.json()["id_tramite_fifonafe"])
    indemnizacion = client.post(
        "/api/fifonafe",
        json={
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_convenio": convenio["id_convenio"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "id_tramite_no_conflictos": informe.json()["id_tramite_fifonafe"],
            "tipo_afectacion": "individual",
            "tipo_tramite": "indemnizacion",
        },
        headers=admin_session,
    )
    assert indemnizacion.status_code == 201, indemnizacion.text
    cleanup.register("/api/fifonafe", indemnizacion.json()["id_tramite_fifonafe"])
    payment = client.post(
        "/api/pagos-indemnizacion",
        json={
            "id_tramite_fifonafe": indemnizacion.json()["id_tramite_fifonafe"],
            "monto_pagado": "50.00",
            "fecha_pago": "2026-08-02",
            "tipo_pago": "parcial",
            "beneficiario_externo": "Titular de prueba",
        },
        headers=admin_session,
    )
    assert payment.status_code == 201, payment.text
    cleanup.register("/api/pagos-indemnizacion", payment.json()["id_pago"])

    modifier = client.post(
        "/api/convenios",
        json={
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "id_convenio_padre": convenio["id_convenio"],
            "tipo_afectacion": "individual",
            "tipo_convenio": "modificatorio",
            "fecha_firma": "2026-08-02",
            "monto_90": "70.00",
            "monto_100": "80.00",
        },
        headers=admin_session,
    )
    assert modifier.status_code == 201, modifier.text
    cleanup.register("/api/convenios", modifier.json()["id_convenio"])
    activated = client.post(
        f"/api/convenios/{modifier.json()['id_convenio']}/activar-modificatorio",
        json={"confirmar": True}, headers=admin_session,
    )
    assert activated.status_code == 200, activated.text
    state = client.get(
        f"/api/afectaciones/{afectacion['id_afectacion']}/estado",
        headers=admin_session,
    ).json()
    assert state["ciclos"][0]["limite_pagable"] == "80.00"
    assert state["ciclos"][0]["total_pagado"] == "50.00"

    def concurrent_payment(reference):
        return client.post(
            "/api/pagos-indemnizacion",
            json={
                "id_tramite_fifonafe": indemnizacion.json()["id_tramite_fifonafe"],
                "monto_pagado": "20.00",
                "fecha_pago": "2026-08-03",
                "tipo_pago": "parcial",
                "beneficiario_externo": "Titular de prueba",
                "banco_emisor": "Banco de prueba",
                "referencia_bancaria": reference,
            },
            headers=admin_session,
        )

    reference_suffix = time.time_ns()
    with ThreadPoolExecutor(max_workers=2) as executor:
        concurrent = list(executor.map(
            concurrent_payment,
            (f"CON-1-{reference_suffix}", f"CON-2-{reference_suffix}"),
        ))
    assert sorted(response.status_code for response in concurrent) == [201, 409]
    for response in concurrent:
        if response.status_code == 201:
            cleanup.register("/api/pagos-indemnizacion", response.json()["id_pago"])

    invalid = client.post(
        "/api/convenios",
        json={
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "id_convenio_padre": convenio["id_convenio"],
            "tipo_afectacion": "individual",
            "tipo_convenio": "modificatorio",
            "fecha_firma": "2026-08-03",
            "monto_90": "35.00",
            "monto_100": "40.00",
        },
        headers=admin_session,
    )
    assert invalid.status_code == 201, invalid.text
    cleanup.register("/api/convenios", invalid.json()["id_convenio"])
    rejected = client.post(
        f"/api/convenios/{invalid.json()['id_convenio']}/activar-modificatorio",
        json={"confirmar": True}, headers=admin_session,
    )
    assert rejected.status_code == 409


def test_colectivo_exige_indemnizacion_y_retiro_de_fondos_completos(
    client, admin_session, cleanup, seed_nucleo, seed_tramo_nucleo,
):
    afectacion, ciclo = _crear_afectacion(
        client, admin_session, cleanup, seed_nucleo, seed_tramo_nucleo, "colectivo"
    )
    assembly = client.post(
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
    assert assembly.status_code == 201, assembly.text
    cleanup.register("/api/asambleas", assembly.json()["id_asamblea"])
    agreement = client.post(
        "/api/convenios",
        json={
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "id_asamblea_autorizacion": assembly.json()["id_asamblea"],
            "tipo_afectacion": "colectivo",
            "tipo_convenio": "cop_original",
            "fecha_firma": "2026-07-23",
            "monto_90": "90.00",
            "monto_100": "100.00",
            "monto_bdt": "10.00",
            "superficie_real_afectada_ha": "1.2500",
        },
        headers=admin_session,
    )
    assert agreement.status_code == 201, agreement.text
    cleanup.register("/api/convenios", agreement.json()["id_convenio"])
    registered = client.put(
        f"/api/convenios/{agreement.json()['id_convenio']}",
        json={
            "ingreso_ran_fecha": "2026-07-24",
            "numero_solicitud_ingreso": "RAN-COL",
            "convenio_inscrito_fecha_ran": "2026-07-25",
        }, headers=admin_session,
    )
    assert registered.status_code == 200, registered.text
    _crear_fifonafe_completo(
        client, admin_session, cleanup, seed_tramo_nucleo,
        afectacion, ciclo, registered.json(),
    )
    pending = client.get(
        f"/api/afectaciones/{afectacion['id_afectacion']}/estado",
        headers=admin_session,
    ).json()
    assert pending["estado_liberacion"] != "liberada"
    assert pending["ciclos"][0]["estado_financiero"] == "retiro_fondos_pendiente"

    withdrawal = client.post(
        "/api/asambleas",
        json={
            "id_nucleo": seed_nucleo["id_nucleo"],
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "id_afectacion": afectacion["id_afectacion"],
            "id_ciclo_afectacion": ciclo["id_ciclo_afectacion"],
            "tipo_asamblea": "retiro_fondos",
            "contexto_proceso": "cop_original",
            "resultado_anuencia": "no_aplica",
            "estatus_asamblea": "pendiente",
            "fecha_realizada": "2026-08-03",
        }, headers=admin_session,
    )
    assert withdrawal.status_code == 201, withdrawal.text
    cleanup.register("/api/asambleas", withdrawal.json()["id_asamblea"])
    completed = client.post(
        f"/api/asambleas/{withdrawal.json()['id_asamblea']}/completar-retiro-fondos",
        json={"confirmar": True}, headers=admin_session,
    )
    assert completed.status_code == 200, completed.text
    final_state = client.get(
        f"/api/afectaciones/{afectacion['id_afectacion']}/estado",
        headers=admin_session,
    ).json()
    assert final_state["estado_liberacion"] == "liberada"


def test_salida_terminal_heredada_detiene_ciclo_y_agrega_expediente(
    client,
    admin_session,
    seed_tramo_nucleo,
    seed_afectacion_colectiva,
):
    tramo_nucleo_id = seed_tramo_nucleo["id_tramo_nucleo"]
    marked = client.put(
        f"/api/tramos-nucleos/{tramo_nucleo_id}",
        json={"es_expropiacion": True},
        headers=admin_session,
    )
    assert marked.status_code == 200, marked.text
    try:
        state = client.get(
            f"/api/tramos-nucleos/{tramo_nucleo_id}/estado",
            headers=admin_session,
        )
        assert state.status_code == 200, state.text
        assert state.json()["estado_legal"] == "fuera_seguimiento"
        blocked = client.post(
            f"/api/afectaciones/{seed_afectacion_colectiva['id_afectacion']}/ciclos",
            json={"tipo_ciclo": "superficie_adicional"},
            headers=admin_session,
        )
        assert blocked.status_code == 409
    finally:
        restored = client.put(
            f"/api/tramos-nucleos/{tramo_nucleo_id}",
            json={"es_expropiacion": False},
            headers=admin_session,
        )
        assert restored.status_code == 200, restored.text


def test_flujo_respeta_pertenencia_territorial(
    client,
    admin_session,
    cleanup,
    seed_tramo,
    seed_nucleo,
    seed_afectacion_colectiva,
):
    correo = f"operador.2b.{time.time_ns()}@pruebas.local"
    created = client.post(
        "/api/usuarios",
        json={
            "nombre": "Operador",
            "apellido_paterno": "Territorial",
            "correo": correo,
            "rol": "operador",
            "contrasena": "Prueba2B!2026",
        },
        headers=admin_session,
    )
    assert created.status_code == 201, created.text
    user = created.json()
    cleanup.register("/api/usuarios", user["id_usuario"])

    with TestClient(app, raise_server_exceptions=False) as op_browser:
        login = op_browser.post(
            "/api/auth/sesiones",
            data={"username": correo, "password": "Prueba2B!2026"},
            headers={"Origin": ORIGIN},
        )
        assert login.status_code == 200, login.text

        affected_id = seed_afectacion_colectiva["id_afectacion"]

        denied = op_browser.get(
            f"/api/afectaciones/{affected_id}/estado",
        )
        assert denied.status_code == 403
        denied_direct = op_browser.get(
            f"/api/afectaciones/{affected_id}"
        )
        assert denied_direct.status_code == 403
        assert op_browser.get("/api/tramos").json() == []
        assert op_browser.get("/api/tramos-nucleos").json() == []
        assert op_browser.get("/api/dashboard").json() == []
        assert op_browser.get("/api/padrones").json() == []
        assert op_browser.get("/api/orvs").json() == []
        assert op_browser.get(
            "/api/padrones", params={"id_nucleo": seed_nucleo["id_nucleo"]}
        ).status_code == 403
        assert op_browser.get(
            "/api/orvs", params={"id_nucleo": seed_nucleo["id_nucleo"]}
        ).status_code == 403

        assigned = client.post(
            f"/api/tramos/{seed_tramo['id_tramo']}/asignar-usuario",
            json={"id_usuario": user["id_usuario"]},
            headers=admin_session,
        )
        assert assigned.status_code == 200, assigned.text

        allowed = op_browser.get(
            f"/api/afectaciones/{affected_id}/estado",
        )
        assert allowed.status_code == 200, allowed.text
        listed = op_browser.get("/api/afectaciones")
        assert listed.status_code == 200
        assert affected_id in {item["id_afectacion"] for item in listed.json()}
        visible_tramos = op_browser.get("/api/tramos")
        assert seed_tramo["id_tramo"] in {
            item["id_tramo"] for item in visible_tramos.json()
        }
        assert op_browser.get(
            "/api/padrones", params={"id_nucleo": seed_nucleo["id_nucleo"]}
        ).status_code == 200
        assert op_browser.get(
            "/api/orvs", params={"id_nucleo": seed_nucleo["id_nucleo"]}
        ).status_code == 200

        removed = client.delete(
            f"/api/tramos/{seed_tramo['id_tramo']}/remover-usuario/{user['id_usuario']}",
            params={"motivo": "Fin de prueba territorial 2B"},
            headers=admin_session,
        )
        assert removed.status_code == 200, removed.text
