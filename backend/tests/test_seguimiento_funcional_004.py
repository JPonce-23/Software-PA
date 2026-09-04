"""Functional history and structural audit for migration 004 (seguimiento funcional excel)."""
import uuid
import pytest
from sqlalchemy import text
from app.database import SessionLocal
from .test_excel_closure_002 import _catalog, _isolated_pn


def _event(api, pn, data, expected=201):
    return api("POST", f"/api/proyecto-nucleo/{pn}/seguimiento", expected=expected, json=data)


def test_004_immutability_and_patch_rejection(api, target_domain):
    """Auditoría Sección 2: Un evento histórico NO puede mutarse para simular otra transición."""
    _, pn = _isolated_pn(api, target_domain)
    event = _catalog(api, "tipo_evento_seguimiento")
    reason = _catalog(api, "motivo_seguimiento")
    pn_id = pn["id_proyecto_nucleo"]

    # 1. Crear evento histórico: suspensión por expropiación directa
    created = _event(api, pn_id, {
        "ambito": "colectivo",
        "id_tipo_evento": event["suspension"],
        "id_motivo": reason["expropiacion_directa"],
        "detalle": "Suspensión por expropiación directa decretada",
        "fecha_evento": "2025-10-01",
    }).json()
    event_id = created["id_seguimiento_evento"]

    # 2. Intentar PATCH cambiando tipo_evento / id_tipo_evento -> DEBE RECHAZARSE (422 por schema)
    patch_attempt = api(
        "PATCH", f"/api/seguimiento/{event_id}",
        json={"id_tipo_evento": event["reapertura"]},
        expected=422,
    )
    patch_attempt_named = api(
        "PATCH", f"/api/seguimiento/{event_id}",
        json={"tipo_evento": "reapertura"},
        expected=422,
    )

    # 3. Intentar PATCH cambiando id_proyecto_nucleo, ambito o motivo -> DEBE RECHAZARSE (422)
    api("PATCH", f"/api/seguimiento/{event_id}", json={"id_proyecto_nucleo": 99999}, expected=422)
    api("PATCH", f"/api/seguimiento/{event_id}", json={"ambito": "individual"}, expected=422)
    api("PATCH", f"/api/seguimiento/{event_id}", json={"id_motivo": reason["nueva_informacion"]}, expected=422)
    api("PATCH", f"/api/seguimiento/{event_id}", json={"entidad_tipo": "parcela"}, expected=422)
    api("PATCH", f"/api/seguimiento/{event_id}", json={"entidad_id": 123}, expected=422)

    # 4. PATCH legítimo de metadatos (detalle/fuente) -> ACEPTADO (200)
    updated = api("PATCH", f"/api/seguimiento/{event_id}", json={
        "detalle": "Suspensión por expropiación directa — corregida nota de bitácora",
        "fuente": "Oficio SICT-2025",
    }, expected=200).json()
    assert updated["detalle"] == "Suspensión por expropiación directa — corregida nota de bitácora"
    assert updated["fuente"] == "Oficio SICT-2025"
    assert updated["id_tipo_evento"] == event["suspension"]

    # 5. En base de datos (PostgreSQL trigger): intentar UPDATE directo alterando transición -> RECHAZO
    db = SessionLocal()
    try:
        with pytest.raises(Exception) as excinfo:
            db.execute(
                text("UPDATE seguimiento_evento SET id_tipo_evento = :reap WHERE id_seguimiento_evento = :eid"),
                {"reap": event["reapertura"], "eid": event_id},
            )
            db.commit()
        assert "no se permite reescribir el tipo de evento" in str(excinfo.value).lower()
        db.rollback()

        with pytest.raises(Exception) as excinfo_motivo:
            db.execute(
                text("UPDATE seguimiento_evento SET id_motivo = :mot WHERE id_seguimiento_evento = :eid"),
                {"mot": reason["nueva_informacion"], "eid": event_id},
            )
            db.commit()
        assert "no se permite cambiar el motivo" in str(excinfo_motivo.value).lower()
        db.rollback()
    finally:
        db.close()


def test_004_derived_state_determinism_scenarios(api, target_domain):
    """Auditoría Sección 3: Determismo del estado derivado en vw_seguimiento_estado_actual."""
    _, pn = _isolated_pn(api, target_domain)
    event = _catalog(api, "tipo_evento_seguimiento")
    reason = _catalog(api, "motivo_seguimiento")
    pn_id = pn["id_proyecto_nucleo"]

    db = SessionLocal()
    try:
        def _get_current_state():
            return db.execute(text(
                "SELECT estado_actual, tipo_ultimo_evento, motivo_actual FROM vw_seguimiento_estado_actual "
                "WHERE id_proyecto_nucleo = :pn AND entidad_tipo IS NULL AND entidad_id IS NULL"
            ), {"pn": pn_id}).fetchone()

        # CASO A: suspension -> reunion -> negociacion => suspendido
        _event(api, pn_id, {
            "ambito": "general", "id_tipo_evento": event["suspension"],
            "id_motivo": reason["cambio_trazo"], "fecha_evento": "2026-01-01",
            "detalle": "Suspensión por análisis de nuevo trazo",
        })
        _event(api, pn_id, {
            "ambito": "general", "id_tipo_evento": event["reunion"],
            "fecha_evento": "2026-01-05", "detalle": "Reunión técnica de gabinete",
        })
        _event(api, pn_id, {
            "ambito": "general", "id_tipo_evento": event["negociacion"],
            "fecha_evento": "2026-01-10", "detalle": "Mesa de negociación",
        })
        row_a = _get_current_state()
        assert row_a is not None
        assert row_a.estado_actual == "suspendido"
        assert row_a.tipo_ultimo_evento == "suspension"
        assert row_a.motivo_actual == "cambio_trazo"

        # CASO B: suspension -> reapertura -> reunion => activo
        _event(api, pn_id, {
            "ambito": "general", "id_tipo_evento": event["reapertura"],
            "id_motivo": reason["nueva_informacion"], "fecha_evento": "2026-01-15",
            "detalle": "Reapertura tras acuerdo preliminar",
        })
        _event(api, pn_id, {
            "ambito": "general", "id_tipo_evento": event["reunion"],
            "fecha_evento": "2026-01-20", "detalle": "Reunión de seguimiento operativo",
        })
        row_b = _get_current_state()
        assert row_b is not None
        assert row_b.estado_actual == "activo"
        assert row_b.tipo_ultimo_evento == "reapertura"

        # CASO C: cierre -> reunion => cerrado
        _event(api, pn_id, {
            "ambito": "general", "id_tipo_evento": event["cierre"],
            "id_motivo": reason["rechazo"], "fecha_evento": "2026-02-01",
            "detalle": "Cierre funcional por rechazo de asamblea",
        })
        _event(api, pn_id, {
            "ambito": "general", "id_tipo_evento": event["reunion"],
            "fecha_evento": "2026-02-05", "detalle": "Reunión informativa posterior",
        })
        row_c = _get_current_state()
        assert row_c is not None
        assert row_c.estado_actual == "cerrado"
        assert row_c.tipo_ultimo_evento == "cierre"

        # CASO D: cierre -> reapertura => activo
        _event(api, pn_id, {
            "ambito": "general", "id_tipo_evento": event["reapertura"],
            "id_motivo": reason["nueva_informacion"], "fecha_evento": "2026-02-10",
            "detalle": "Reapertura por reconsideración del núcleo",
        })
        row_d = _get_current_state()
        assert row_d is not None
        assert row_d.estado_actual == "activo"
        assert row_d.tipo_ultimo_evento == "reapertura"

        # CASO G: Dos eventos de transición con la MISMA fecha_evento -> desempate determinista por id_seguimiento_evento DESC
        # Insertamos suspensión en fecha 2026-03-01
        ev_susp = _event(api, pn_id, {
            "ambito": "general", "id_tipo_evento": event["suspension"],
            "id_motivo": reason["falta_pago"], "fecha_evento": "2026-03-01",
            "detalle": "Suspensión administrativa",
        }).json()
        # Insertamos reapertura el mismo día (id posterior)
        ev_reap = _event(api, pn_id, {
            "ambito": "general", "id_tipo_evento": event["reapertura"],
            "id_motivo": reason["nueva_informacion"], "fecha_evento": "2026-03-01",
            "detalle": "Reapertura el mismo día tras comprobar pago",
        }).json()
        assert ev_reap["id_seguimiento_evento"] > ev_susp["id_seguimiento_evento"]
        row_g = _get_current_state()
        assert row_g.estado_actual == "activo"
        assert row_g.tipo_ultimo_evento == "reapertura"

        # CASO H: fecha_evento NULL -> orden determinista (NULLS LAST, desempate por id)
        _event(api, pn_id, {
            "ambito": "general", "id_tipo_evento": event["suspension"],
            "id_motivo": reason["calificacion_negativa"], "fecha_evento": None,
            "detalle": "Suspensión sin fecha registrada originalmente",
        })
        # Como tiene fecha NULL, va después de fechas explícitas anteriores o se desempata deterministamente
        row_h = _get_current_state()
        assert row_h is not None

    finally:
        db.close()


def test_004_non_transition_events_do_not_alter_state(api, target_domain):
    """Auditoría Sección 3 E y F: cambio_alcance y consulta_indigena no cierran ni suspenden solos."""
    _, pn = _isolated_pn(api, target_domain)
    event = _catalog(api, "tipo_evento_seguimiento")
    reason = _catalog(api, "motivo_seguimiento")
    pn_id = pn["id_proyecto_nucleo"]

    db = SessionLocal()
    try:
        # CASO E: cambio_alcance solamente no debe producir suspensión ni cierre
        _event(api, pn_id, {
            "ambito": "general", "id_tipo_evento": event["cambio_alcance"],
            "id_motivo": reason["cambio_trazo"], "detalle": "Ajuste de trazo preliminar",
            "fecha_evento": "2026-01-01",
        })
        row_e = db.execute(text(
            "SELECT estado_actual FROM vw_seguimiento_estado_actual WHERE id_proyecto_nucleo = :pn"
        ), {"pn": pn_id}).fetchone()
        # No genera estado de suspensión ni cierre en el read-model de transiciones
        assert row_e is None or row_e.estado_actual == "activo"

        # CASO F: consulta_indigena solamente no debe cerrar automáticamente
        _event(api, pn_id, {
            "ambito": "general", "id_tipo_evento": event["consulta_indigena"],
            "id_motivo": reason["comunidad_indigena"], "detalle": "Proceso de consulta en curso",
            "fecha_evento": "2026-01-05",
        })
        row_f = db.execute(text(
            "SELECT estado_actual FROM vw_seguimiento_estado_actual WHERE id_proyecto_nucleo = :pn"
        ), {"pn": pn_id}).fetchone()
        assert row_f is None or row_f.estado_actual not in ("suspendido", "cerrado")
    finally:
        db.close()


def test_004_typed_target_rules_and_validations(api, target_domain):
    """Auditoría Sección 4: Reglas de objetivo tipado y restricciones de compatibilidad."""
    _, pn = _isolated_pn(api, target_domain)
    event = _catalog(api, "tipo_evento_seguimiento")
    reason = _catalog(api, "motivo_seguimiento")
    pn_id = pn["id_proyecto_nucleo"]
    token = uuid.uuid4().hex[:6]

    # 1. Asimetría de objetivo tipado:
    # entidad_tipo NULL + entidad_id no NULL -> 422
    api("POST", f"/api/proyecto-nucleo/{pn_id}/seguimiento", expected=422, json={
        "ambito": "general", "id_tipo_evento": event["reunion"],
        "entidad_tipo": None, "entidad_id": 100, "detalle": "Asimetría 1",
    })
    # entidad_tipo no NULL + entidad_id NULL -> 422
    api("POST", f"/api/proyecto-nucleo/{pn_id}/seguimiento", expected=422, json={
        "ambito": "general", "id_tipo_evento": event["reunion"],
        "entidad_tipo": "parcela", "entidad_id": None, "detalle": "Asimetría 2",
    })

    # 2. Objetivo inexistente -> rechazo 409
    _event(api, pn_id, {
        "ambito": "individual", "entidad_tipo": "parcela", "entidad_id": 9999999,
        "id_tipo_evento": event["reunion"], "detalle": "Parcela inexistente",
    }, expected=409)

    # 3. Objetivo de otro ProyectoNucleo (cruzado) -> rechazo 409
    other_parcel = target_domain["parcels"][0]
    _event(api, pn_id, {
        "ambito": "individual", "entidad_tipo": "parcela", "entidad_id": other_parcel["id_parcela"],
        "id_tipo_evento": event["reunion"], "detalle": "Parcela de otro PN",
    }, expected=409)

    # 4. Crear recursos propios para pruebas de compatibilidad
    my_parcel = api("POST", f"/api/proyecto-nucleo/{pn_id}/parcelas", expected=201, json={
        "tipo_parcela": "individual", "no_parcela": f"AUDIT-P-{token}",
    }).json()
    my_affectation = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201, json={
        "tipo_afectacion": "individual", "superficie_preliminar_ha": "1.000000",
        "superficie_afectada_ha": "1.000000",
    }).json()
    assembly_type = _catalog(api, "tipo_asamblea")["anuencia"]
    context = _catalog(api, "contexto_asamblea")["cop_original"]
    my_assembly = api("POST", f"/api/proyecto-nucleo/{pn_id}/asambleas", expected=201, json={
        "id_tipo_asamblea": assembly_type, "id_contexto_asamblea": context,
    }).json()

    # 5. continuacion_asamblea:
    # - Objetivo asamblea propio -> ACEPTA (201)
    _event(api, pn_id, {
        "ambito": "colectivo", "entidad_tipo": "asamblea", "entidad_id": my_assembly["id_asamblea"],
        "id_tipo_evento": event["continuacion_asamblea"], "fecha_evento": "2026-03-10",
        "detalle": "Continuación legítima de asamblea",
    }, expected=201)
    # - Apuntando a parcela -> RECHAZO (409)
    _event(api, pn_id, {
        "ambito": "colectivo", "entidad_tipo": "parcela", "entidad_id": my_parcel["id_parcela"],
        "id_tipo_evento": event["continuacion_asamblea"], "detalle": "Continuación sobre parcela",
    }, expected=409)

    # 6. dominio_pleno:
    # - Individual + parcela -> ACEPTA (201)
    _event(api, pn_id, {
        "ambito": "individual", "entidad_tipo": "parcela", "entidad_id": my_parcel["id_parcela"],
        "id_tipo_evento": event["cierre"], "id_motivo": reason["dominio_pleno"],
        "detalle": "Salida por adopción de dominio pleno",
    }, expected=201)
    # - Individual + afectación individual -> ACEPTA (201)
    _event(api, pn_id, {
        "ambito": "individual", "entidad_tipo": "afectacion", "entidad_id": my_affectation["id_afectacion"],
        "id_tipo_evento": event["cierre"], "id_motivo": reason["dominio_pleno"],
        "detalle": "Dominio pleno en afectación individual",
    }, expected=201)
    # - Colectivo -> RECHAZO (409)
    _event(api, pn_id, {
        "ambito": "colectivo", "entidad_tipo": "parcela", "entidad_id": my_parcel["id_parcela"],
        "id_tipo_evento": event["cierre"], "id_motivo": reason["dominio_pleno"],
        "detalle": "Intento de dominio pleno colectivo",
    }, expected=409)
    # - Objetivo incompatible (asamblea) -> RECHAZO (409)
    _event(api, pn_id, {
        "ambito": "individual", "entidad_tipo": "asamblea", "entidad_id": my_assembly["id_asamblea"],
        "id_tipo_evento": event["cierre"], "id_motivo": reason["dominio_pleno"],
        "detalle": "Dominio pleno sobre asamblea",
    }, expected=409)


def test_004_afecta_tuc_expropriation_and_community(api, target_domain):
    """Auditoría Secciones 5 y 6: Afecta_TUC, Expropiación Directa y Comunidad Indígena."""
    _, pn = _isolated_pn(api, target_domain)
    event = _catalog(api, "tipo_evento_seguimiento")
    reason = _catalog(api, "motivo_seguimiento")
    pn_id = pn["id_proyecto_nucleo"]
    nucleus_id = pn["id_nucleo"]

    # Iniciar con afecta_tuc = True y comunidad_indigena = True
    api("PATCH", f"/api/proyecto-nucleo/{pn_id}", json={
        "afecta_tuc": True, "id_motivo_no_afecta_tuc": None, "motivo_no_afecta_tuc_detalle": None
    })
    api("PATCH", f"/api/nucleos/{nucleus_id}", json={"comunidad_indigena": True})

    pn_before = api("GET", f"/api/proyecto-nucleo/{pn_id}").json()
    nuc_before = api("GET", f"/api/nucleos/{nucleus_id}").json()
    assert pn_before["afecta_tuc"] is True
    assert nuc_before["comunidad_indigena"] is True

    # 1. Registrar suspensión con motivo expropiacion_directa
    _event(api, pn_id, {
        "ambito": "colectivo", "id_tipo_evento": event["suspension"],
        "id_motivo": reason["expropiacion_directa"], "detalle": "Suspensión por expropiación directa",
        "fecha_evento": "2026-01-10",
    })
    # afecta_tuc DEBE SEGUIR SIENDO True
    pn_mid1 = api("GET", f"/api/proyecto-nucleo/{pn_id}").json()
    assert pn_mid1["afecta_tuc"] is True

    # 2. Registrar reapertura con motivo nueva_informacion
    _event(api, pn_id, {
        "ambito": "colectivo", "id_tipo_evento": event["reapertura"],
        "id_motivo": reason["nueva_informacion"], "detalle": "Representación retoma diálogo",
        "fecha_evento": "2026-02-15",
    })
    # afecta_tuc DEBE SEGUIR SIENDO True
    pn_mid2 = api("GET", f"/api/proyecto-nucleo/{pn_id}").json()
    assert pn_mid2["afecta_tuc"] is True

    # 3. Registrar eventos de consulta indígena y suspensión por comunidad indígena
    _event(api, pn_id, {
        "ambito": "general", "id_tipo_evento": event["consulta_indigena"],
        "id_motivo": reason["comunidad_indigena"], "detalle": "Consulta indígena previa informada",
        "fecha_evento": "2026-03-01",
    })
    _event(api, pn_id, {
        "ambito": "general", "id_tipo_evento": event["suspension"],
        "id_motivo": reason["comunidad_indigena"], "detalle": "Suspensión por asamblea de consulta",
        "fecha_evento": "2026-03-10",
    })
    # comunidad_indigena y afecta_tuc NO deben haber mutado
    nuc_after = api("GET", f"/api/nucleos/{nucleus_id}").json()
    pn_after = api("GET", f"/api/proyecto-nucleo/{pn_id}").json()
    assert nuc_after["comunidad_indigena"] is True
    assert pn_after["afecta_tuc"] is True

    # Reapertura final
    _event(api, pn_id, {
        "ambito": "general", "id_tipo_evento": event["reapertura"],
        "id_motivo": reason["nueva_informacion"], "detalle": "Consulta concluida protocolizada",
        "fecha_evento": "2026-04-01",
    })
    history = api("GET", f"/api/proyecto-nucleo/{pn_id}/seguimiento").json()
    assert len(history) == 5


def test_004_permanent_assembly_kpi_invariance(api, target_domain):
    """Auditoría Sección 7: Continuaciones de asamblea permanente no alteran conteo ni KPI."""
    _, pn = _isolated_pn(api, target_domain)
    event = _catalog(api, "tipo_evento_seguimiento")
    pn_id = pn["id_proyecto_nucleo"]

    # Crear una única asamblea
    assembly_type = _catalog(api, "tipo_asamblea")["anuencia"]
    context = _catalog(api, "contexto_asamblea")["cop_original"]
    assembly = api("POST", f"/api/proyecto-nucleo/{pn_id}/asambleas", expected=201, json={
        "id_tipo_asamblea": assembly_type, "id_contexto_asamblea": context,
    }).json()
    assembly_id = assembly["id_asamblea"]

    # Registrar 2 eventos de continuación de asamblea permanente en fechas posteriores
    _event(api, pn_id, {
        "ambito": "colectivo", "entidad_tipo": "asamblea", "entidad_id": assembly_id,
        "id_tipo_evento": event["continuacion_asamblea"], "fecha_evento": "2026-05-02",
        "detalle": "Sesión permanente: pase de lista y discusión de propuesta",
    })
    _event(api, pn_id, {
        "ambito": "colectivo", "entidad_tipo": "asamblea", "entidad_id": assembly_id,
        "id_tipo_evento": event["continuacion_asamblea"], "fecha_evento": "2026-05-10",
        "detalle": "Sesión permanente: formalización de acuerdos",
    })

    # Total de Asambleas realizadas DEBE seguir siendo exactamente 1
    asambleas = api("GET", f"/api/proyecto-nucleo/{pn_id}/asambleas").json()
    assert len(asambleas) == 1
    assert asambleas[0]["id_asamblea"] == assembly_id


def test_004_parcel_scope_change_cycle(api, target_domain):
    """Auditoría Sección 9: Parcela sale y vuelve sin duplicarse."""
    _, pn = _isolated_pn(api, target_domain)
    event = _catalog(api, "tipo_evento_seguimiento")
    reason = _catalog(api, "motivo_seguimiento")
    pn_id = pn["id_proyecto_nucleo"]
    token = uuid.uuid4().hex[:6]

    # Crear parcela P
    parcel = api("POST", f"/api/proyecto-nucleo/{pn_id}/parcelas", expected=201, json={
        "tipo_parcela": "individual", "no_parcela": f"CYCLE-P-{token}",
    }).json()
    parcel_id = parcel["id_parcela"]

    # 1. cambio_alcance / no_afectacion
    _event(api, pn_id, {
        "ambito": "individual", "entidad_tipo": "parcela", "entidad_id": parcel_id,
        "id_tipo_evento": event["cambio_alcance"], "id_motivo": reason["no_afectacion"],
        "detalle": "El proyecto ferroviario no afecta parcelas en presentación preliminar",
        "fecha_evento": "2026-01-10",
    })

    # 2. cambio_alcance / nueva_informacion
    _event(api, pn_id, {
        "ambito": "individual", "entidad_tipo": "parcela", "entidad_id": parcel_id,
        "id_tipo_evento": event["cambio_alcance"], "id_motivo": reason["nueva_informacion"],
        "detalle": "En la nueva presentación del trazo sí aparecen parcelas afectadas",
        "fecha_evento": "2026-02-15",
    })

    # La parcela sigue siendo exactamente la misma (id, datos) y no se duplicó
    parcels_list = api("GET", f"/api/proyecto-nucleo/{pn_id}/parcelas").json()
    matching = [p for p in parcels_list if p["id_parcela"] == parcel_id]
    assert len(matching) == 1
    assert matching[0]["no_parcela"] == f"CYCLE-P-{token}"


def test_004_document_states_and_logical_delete(api, target_domain):
    """Auditoría Sección 9: Validación de detalle/motivo, estados documentales y baja lógica."""
    _, pn = _isolated_pn(api, target_domain)
    event = _catalog(api, "tipo_evento_seguimiento")
    reason = _catalog(api, "motivo_seguimiento")
    pn_id = pn["id_proyecto_nucleo"]

    # Reapertura sin detalle -> 409
    _event(api, pn_id, {"ambito": "general", "id_tipo_evento": event["reapertura"]}, expected=409)

    # Motivo "otro" sin detalle -> 409; con detalle -> 201
    _event(api, pn_id, {
        "ambito": "general", "id_tipo_evento": event["suspension"], "id_motivo": reason["otro"],
    }, expected=409)
    _event(api, pn_id, {
        "ambito": "general", "id_tipo_evento": event["suspension"], "id_motivo": reason["otro"],
        "detalle": "Causa justificada detallada",
    }, expected=201)

    # Suspensión sin motivo -> 409
    _event(api, pn_id, {"ambito": "general", "id_tipo_evento": event["suspension"]}, expected=409)

    # Estados documentales: parcial, pendiente_validacion
    states = _catalog(api, "estado_requisito_documental")
    requirements = api("GET", "/api/catalogos/requisitos-documentales").json()
    codes = {row["codigo"]: row["id_requisito"] for row in requirements}

    assert "parcial" in states
    assert "pendiente_validacion" in states
    assert {"validacion_pa_sict", "oficio_ran_parcelas_afectacion", "acta_complementaria"} <= set(codes)

    # Vincular 3 nuevos requisitos
    api("POST", f"/api/proyecto-nucleo/{pn_id}/requisitos-documentales", expected=201, json={
        "entidad_tipo": "proyecto_nucleo", "entidad_id": pn_id,
        "id_requisito": codes["validacion_pa_sict"], "id_estado": states["parcial"],
        "detalle": "Documentación parcial PA/SICT",
    })
    api("POST", f"/api/proyecto-nucleo/{pn_id}/requisitos-documentales", expected=201, json={
        "entidad_tipo": "proyecto_nucleo", "entidad_id": pn_id,
        "id_requisito": codes["oficio_ran_parcelas_afectacion"], "id_estado": states["pendiente_validacion"],
        "detalle": "Oficio RAN con revisión de parcelas",
    })
    api("POST", f"/api/proyecto-nucleo/{pn_id}/requisitos-documentales", expected=201, json={
        "entidad_tipo": "proyecto_nucleo", "entidad_id": pn_id,
        "id_requisito": codes["acta_complementaria"], "id_estado": states["disponible"],
        "detalle": "Acta complementaria disponible",
    })

    # Baja lógica: DELETE lógico y prevención de DELETE físico
    ev_to_delete = _event(api, pn_id, {
        "ambito": "general", "id_tipo_evento": event["reunion"],
        "detalle": "Reunión por cancelar", "fecha_evento": "2026-06-01",
    }).json()
    del_id = ev_to_delete["id_seguimiento_evento"]

    api("DELETE", f"/api/seguimiento/{del_id}", json={"motivo": "Cancelada por fuerza mayor"})
    active = api("GET", f"/api/proyecto-nucleo/{pn_id}/seguimiento").json()
    assert not any(e["id_seguimiento_evento"] == del_id for e in active)

    db = SessionLocal()
    try:
        row = db.execute(text(
            "SELECT activo, fecha_baja, motivo_baja FROM seguimiento_evento WHERE id_seguimiento_evento = :eid"
        ), {"eid": del_id}).fetchone()
        assert row.activo is False
        assert row.fecha_baja is not None
        assert row.motivo_baja == "Cancelada por fuerza mayor"

        with pytest.raises(Exception) as excinfo:
            db.execute(text("DELETE FROM seguimiento_evento WHERE id_seguimiento_evento = :eid"), {"eid": del_id})
            db.commit()
        err = str(excinfo.value).lower()
        assert "eliminación física" in err or "trg_prevent_delete" in err or "permission denied" in err
        db.rollback()
    finally:
        db.close()
