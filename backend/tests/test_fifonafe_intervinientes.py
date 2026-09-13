"""Pruebas de integridad API/BD para intervinientes FIFONAFE.

Cubre exhaustivamente los casos A-J requeridos:
A. Interviniente sin ORV (id_orv_integrante = NULL).
B. id_orv_integrante con id_evento_fifonafe = NULL (rechazado con 422).
C. Evento perteneciente a otro trámite (rechazado con 409).
D. Evento sin fecha_evento ni fecha_oficio para ORV (rechazado con 409).
E. id_orv_integrante perteneciente a otra persona (rechazado con 409).
F. ORV perteneciente a otro núcleo (rechazado con 409).
G. Integrante ORV fuera de vigencia respecto a fecha del evento (rechazado con 409).
H. Caso completamente válido (creado con 201).
I. Verificación de que un rechazo de API no deja filas parciales.
J. Verificación de que la BD sigue rechazando inserción inválida directa.
"""

import uuid
from datetime import date
import pytest
from sqlalchemy import text

from app.database import SessionLocal


def _catalog(api, name: str) -> dict[str, int]:
    return {
        row["codigo"]: row["id_catalogo_opcion"]
        for row in api("GET", f"/api/catalogos/operativos/{name}").json()
    }


def _create_isolated_env(api, target_domain, prefix="FIF-INT", municipality_id=None):
    token = uuid.uuid4().hex[:8]
    tenencia = _catalog(api, "tipo_tenencia")["ejido"]

    project = api(
        "POST",
        "/api/proyectos",
        expected=201,
        json={
            "clave_proyecto": f"PRJ-{prefix}-{token}",
            "nombre_proyecto": f"Proyecto {prefix} {token}",
            "fecha_inicio": "2026-01-01",
        },
    ).json()

    mun_id = municipality_id or target_domain["municipality"]["id_municipio"]
    nucleus = api(
        "POST",
        "/api/nucleos",
        expected=201,
        json={
            "id_municipio": mun_id,
            "nombre_nucleo": f"Núcleo {prefix} {token}",
            "id_tipo_tenencia": tenencia,
            "fuente_datos": "qa-fifonafe-test",
        },
    ).json()

    pn = api(
        "POST",
        f"/api/proyectos/{project['id_proyecto']}/nucleos",
        expected=201,
        json={"id_nucleo": nucleus["id_nucleo"]},
    ).json()

    cop = _catalog(api, "tipo_cop_operativo")
    aff = api(
        "POST",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    tramite = api(
        "POST",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/fifonafe",
        expected=201,
        json={"ids_afectacion": [aff["id_afectacion"]]},
    ).json()

    return project, pn, nucleus, aff, tramite


def _create_person(api, project_id, name="Persona QA"):
    token = uuid.uuid4().hex[:8]
    return api(
        "POST",
        f"/api/proyectos/{project_id}/personas",
        expected=201,
        json={
            "nombre": f"{name}-{token}",
            "datos_identidad_incompletos": True,
            "origen_registro": "qa",
        },
    ).json()


def _create_orv(api, pn_id, start="2026-01-01", end="2026-12-31"):
    token = uuid.uuid4().hex[:8]
    states = _catalog(api, "estado_registral_orv")
    return api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/orv",
        expected=201,
        json={
            "numero_orv": f"ORV-{token}",
            "inicio_vigencia": start,
            "fin_vigencia": end,
            "id_estado_registral": states["inscrita"],
        },
    ).json()


def _create_member(api, orv_id, person_id, start="2026-01-01", end="2026-12-31"):
    organs = _catalog(api, "organo_orv")
    positions = _catalog(api, "cargo_orv")
    qualities = _catalog(api, "calidad_integrante_orv")
    return api(
        "POST",
        f"/api/orv/{orv_id}/integrantes",
        expected=201,
        json={
            "id_persona": person_id,
            "id_organo": organs["comisariado"],
            "id_cargo": positions["presidente"],
            "id_calidad": qualities["propietario"],
            "fecha_inicio": start,
            "fecha_fin": end,
        },
    ).json()


def _create_event(api, tramite_id, ordinal=1, event_date="2026-06-15", oficio_date=None, **kwargs):
    tipos = _catalog(api, "tipo_evento_fifonafe")
    payload = {
        "ordinal": ordinal,
        "id_tipo_evento": tipos["diferimiento_retiro"],
        **kwargs,
    }
    if event_date is not None:
        payload["fecha_evento"] = event_date
    if oficio_date is not None:
        payload["fecha_oficio"] = oficio_date
    return api("POST", f"/api/fifonafe/{tramite_id}/eventos", expected=201, json=payload).json()


# =========================================================================
# CASO A: Interviniente sin ORV (id_orv_integrante = NULL)
# =========================================================================
def test_caso_a_interviniente_sin_orv(api, target_domain):
    project, pn, _, _, tramite = _create_isolated_env(api, target_domain, prefix="CASO-A")
    person = _create_person(api, project["id_proyecto"], "Persona Sin ORV")

    # A1: Sin evento y sin ORV
    res1 = api(
        "POST",
        f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes",
        expected=201,
        json={
            "id_persona": person["id_persona"],
            "rol": "solicitante",
            "id_evento_fifonafe": None,
            "id_orv_integrante": None,
        },
    ).json()
    assert res1["id_interviniente_fifonafe"] > 0
    assert res1["rol"] == "solicitante"
    assert res1["id_orv_integrante"] is None

    # A2: Con evento válido y sin ORV
    event = _create_event(api, tramite["id_tramite_fifonafe"], ordinal=1, event_date="2026-06-01")
    person2 = _create_person(api, project["id_proyecto"], "Persona Con Evento Sin ORV")
    res2 = api(
        "POST",
        f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes",
        expected=201,
        json={
            "id_persona": person2["id_persona"],
            "rol": "titular",
            "id_evento_fifonafe": event["id_evento_fifonafe"],
            "id_orv_integrante": None,
        },
    ).json()
    assert res2["id_interviniente_fifonafe"] > 0
    assert res2["rol"] == "titular"
    assert res2["id_evento_fifonafe"] == event["id_evento_fifonafe"]
    assert res2["id_orv_integrante"] is None


# =========================================================================
# CASO B: id_orv_integrante con id_evento_fifonafe = NULL (rechazado con 422)
# =========================================================================
def test_caso_b_orv_sin_evento_rechazado_422(api, target_domain):
    project, pn, _, _, tramite = _create_isolated_env(api, target_domain, prefix="CASO-B")
    person = _create_person(api, project["id_proyecto"], "Persona Caso B")
    orv = _create_orv(api, pn["id_proyecto_nucleo"])
    member = _create_member(api, orv["id_orv"], person["id_persona"])

    # Intentar registrar interviniente con ORV pero sin id_evento_fifonafe (omitido)
    resp1 = api(
        "POST",
        f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes",
        expected=422,
        json={
            "id_persona": person["id_persona"],
            "rol": "representante",
            "id_orv_integrante": member["id_orv_integrante"],
        },
    )
    assert "id_evento_fifonafe" in resp1.text

    # Intentar registrar interviniente con ORV pero con id_evento_fifonafe = null explícito
    resp2 = api(
        "POST",
        f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes",
        expected=422,
        json={
            "id_persona": person["id_persona"],
            "rol": "representante",
            "id_evento_fifonafe": None,
            "id_orv_integrante": member["id_orv_integrante"],
        },
    )
    assert "id_evento_fifonafe" in resp2.text


# =========================================================================
# CASO C: Evento perteneciente a otro trámite (rechazado con 409)
# =========================================================================
def test_caso_c_evento_perteneciente_a_otro_tramite(api, target_domain):
    project, pn, _, _, tramite1 = _create_isolated_env(api, target_domain, prefix="CASO-C1")
    cop = _catalog(api, "tipo_cop_operativo")
    aff2 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ADICIONAL"]},
    ).json()
    tramite2 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/fifonafe",
        expected=201,
        json={"ids_afectacion": [aff2["id_afectacion"]]},
    ).json()

    event_tramite2 = _create_event(api, tramite2["id_tramite_fifonafe"], ordinal=1, event_date="2026-06-10")
    person = _create_person(api, project["id_proyecto"], "Persona Caso C")

    # Intentar asociar evento de tramite2 en interviniente de tramite1
    resp = api(
        "POST",
        f"/api/fifonafe/{tramite1['id_tramite_fifonafe']}/intervinientes",
        expected=409,
        json={
            "id_persona": person["id_persona"],
            "rol": "representante",
            "id_evento_fifonafe": event_tramite2["id_evento_fifonafe"],
        },
    )
    assert resp.status_code == 409


# =========================================================================
# CASO D: Evento sin fecha_evento ni fecha_oficio (rechazado con 409)
# =========================================================================
def test_caso_d_evento_sin_fecha_rechazado_para_orv(api, target_domain):
    project, pn, _, _, tramite = _create_isolated_env(api, target_domain, prefix="CASO-D")
    person = _create_person(api, project["id_proyecto"], "Persona Caso D")
    orv = _create_orv(api, pn["id_proyecto_nucleo"])
    member = _create_member(api, orv["id_orv"], person["id_persona"])

    # Evento sin fecha_evento y sin fecha_oficio
    undated_event = _create_event(
        api,
        tramite["id_tramite_fifonafe"],
        ordinal=1,
        event_date=None,
        oficio_date=None,
        observaciones="Evento sin fecha de negocio",
    )

    resp = api(
        "POST",
        f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes",
        expected=409,
        json={
            "id_persona": person["id_persona"],
            "rol": "representante",
            "id_evento_fifonafe": undated_event["id_evento_fifonafe"],
            "id_orv_integrante": member["id_orv_integrante"],
        },
    )
    assert resp.status_code == 409
    assert "fecha de negocio" in resp.text


# =========================================================================
# CASO E: id_orv_integrante perteneciente a otra persona (rechazado con 409)
# =========================================================================
def test_caso_e_orv_integrante_otra_persona(api, target_domain):
    project, pn, _, _, tramite = _create_isolated_env(api, target_domain, prefix="CASO-E")
    person_titular = _create_person(api, project["id_proyecto"], "Persona Titular")
    person_ajena = _create_person(api, project["id_proyecto"], "Persona Ajena")

    orv = _create_orv(api, pn["id_proyecto_nucleo"])
    member_ajena = _create_member(api, orv["id_orv"], person_ajena["id_persona"])

    event = _create_event(api, tramite["id_tramite_fifonafe"], ordinal=1, event_date="2026-06-15")

    # Intentar registrar interviniente de person_titular usando el integrante de person_ajena
    resp = api(
        "POST",
        f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes",
        expected=409,
        json={
            "id_persona": person_titular["id_persona"],
            "rol": "representante",
            "id_evento_fifonafe": event["id_evento_fifonafe"],
            "id_orv_integrante": member_ajena["id_orv_integrante"],
        },
    )
    assert resp.status_code == 409
    assert "no coincide" in resp.text or "no acredita" in resp.text


# =========================================================================
# CASO F: ORV perteneciente a otro núcleo (rechazado con 409)
# =========================================================================
def test_caso_f_orv_otro_nucleo(api, target_domain):
    project, pn1, nucleus1, _, tramite1 = _create_isolated_env(api, target_domain, prefix="CASO-F1")

    # Crear segundo núcleo y proyecto_nucleo distinto
    tenencia = _catalog(api, "tipo_tenencia")["ejido"]
    mun_id = target_domain["municipality"]["id_municipio"]
    nucleus2 = api(
        "POST",
        "/api/nucleos",
        expected=201,
        json={
            "id_municipio": mun_id,
            "nombre_nucleo": f"Núcleo Ajeno {uuid.uuid4().hex[:6]}",
            "id_tipo_tenencia": tenencia,
            "fuente_datos": "qa-fifonafe-test",
        },
    ).json()
    pn2 = api(
        "POST",
        f"/api/proyectos/{project['id_proyecto']}/nucleos",
        expected=201,
        json={"id_nucleo": nucleus2["id_nucleo"]},
    ).json()

    person = _create_person(api, project["id_proyecto"], "Persona Caso F")

    # Crear ORV e integrante en el núcleo 2
    orv_nucleo2 = _create_orv(api, pn2["id_proyecto_nucleo"])
    member_nucleo2 = _create_member(api, orv_nucleo2["id_orv"], person["id_persona"])

    event = _create_event(api, tramite1["id_tramite_fifonafe"], ordinal=1, event_date="2026-06-15")

    # Intentar acreditar en tramite1 (núcleo 1) un integrante del ORV de núcleo 2
    resp = api(
        "POST",
        f"/api/fifonafe/{tramite1['id_tramite_fifonafe']}/intervinientes",
        expected=409,
        json={
            "id_persona": person["id_persona"],
            "rol": "representante",
            "id_evento_fifonafe": event["id_evento_fifonafe"],
            "id_orv_integrante": member_nucleo2["id_orv_integrante"],
        },
    )
    assert resp.status_code == 409
    assert "incompatible" in resp.text or "no acredita" in resp.text


# =========================================================================
# CASO G: Integrante ORV fuera de vigencia respecto al evento (rechazado con 409)
# =========================================================================
def test_caso_g_orv_fuera_de_vigencia(api, target_domain):
    project, pn, _, _, tramite = _create_isolated_env(api, target_domain, prefix="CASO-G")
    person = _create_person(api, project["id_proyecto"], "Persona Caso G")

    # Integrante con vigencia en 2025
    orv = _create_orv(api, pn["id_proyecto_nucleo"], start="2025-01-01", end="2025-12-31")
    member_vencido = _create_member(api, orv["id_orv"], person["id_persona"], start="2025-01-01", end="2025-12-31")

    # Evento en junio 2026 (fuera de vigencia)
    event_2026 = _create_event(api, tramite["id_tramite_fifonafe"], ordinal=1, event_date="2026-06-15")

    resp = api(
        "POST",
        f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes",
        expected=409,
        json={
            "id_persona": person["id_persona"],
            "rol": "representante",
            "id_evento_fifonafe": event_2026["id_evento_fifonafe"],
            "id_orv_integrante": member_vencido["id_orv_integrante"],
        },
    )
    assert resp.status_code == 409
    assert "vigencia" in resp.text or "no acredita" in resp.text


# =========================================================================
# CASO H: Caso completamente válido (creado con 201)
# =========================================================================
def test_caso_h_interviniente_valido(api, target_domain):
    project, pn, _, _, tramite = _create_isolated_env(api, target_domain, prefix="CASO-H")
    person = _create_person(api, project["id_proyecto"], "Persona Caso H")

    orv = _create_orv(api, pn["id_proyecto_nucleo"], start="2026-01-01", end="2026-12-31")
    member = _create_member(api, orv["id_orv"], person["id_persona"], start="2026-01-01", end="2026-12-31")

    event = _create_event(api, tramite["id_tramite_fifonafe"], ordinal=1, event_date="2026-06-20")

    res = api(
        "POST",
        f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes",
        expected=201,
        json={
            "id_persona": person["id_persona"],
            "rol": "representante",
            "id_evento_fifonafe": event["id_evento_fifonafe"],
            "id_orv_integrante": member["id_orv_integrante"],
        },
    ).json()

    assert res["id_interviniente_fifonafe"] > 0
    assert res["id_tramite_fifonafe"] == tramite["id_tramite_fifonafe"]
    assert res["id_persona"] == person["id_persona"]
    assert res["rol"] == "representante"
    assert res["id_evento_fifonafe"] == event["id_evento_fifonafe"]
    assert res["id_orv_integrante"] == member["id_orv_integrante"]

    # Verificar que aparece en la lista de intervinientes del trámite
    listed = api("GET", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes").json()
    assert any(x["id_interviniente_fifonafe"] == res["id_interviniente_fifonafe"] for x in listed)


# =========================================================================
# CASO I: Verificación de que un rechazo de API no deja filas parciales
# =========================================================================
def test_caso_i_rechazos_no_dejan_filas_parciales(api, target_domain):
    project, pn, _, _, tramite = _create_isolated_env(api, target_domain, prefix="CASO-I")
    person = _create_person(api, project["id_proyecto"], "Persona Caso I")
    orv = _create_orv(api, pn["id_proyecto_nucleo"], start="2026-01-01", end="2026-12-31")
    member = _create_member(api, orv["id_orv"], person["id_persona"], start="2026-01-01", end="2026-12-31")

    # 1. Fallo 422: ORV sin evento
    api(
        "POST",
        f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes",
        expected=422,
        json={
            "id_persona": person["id_persona"],
            "rol": "representante",
            "id_orv_integrante": member["id_orv_integrante"],
        },
    )

    # 2. Fallo 409: Persona inexistente
    api(
        "POST",
        f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes",
        expected=409,
        json={
            "id_persona": 99999999,
            "rol": "solicitante",
        },
    )

    # 3. Fallo 409: Evento sin fecha para ORV
    undated = _create_event(
        api,
        tramite["id_tramite_fifonafe"],
        ordinal=1,
        event_date=None,
        oficio_date=None,
        observaciones="Evento sin fecha de negocio",
    )
    api(
        "POST",
        f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes",
        expected=409,
        json={
            "id_persona": person["id_persona"],
            "rol": "representante",
            "id_evento_fifonafe": undated["id_evento_fifonafe"],
            "id_orv_integrante": member["id_orv_integrante"],
        },
    )

    # Verificar que el endpoint retorna 0 intervinientes
    intervinientes = api("GET", f"/api/fifonafe/{tramite['id_tramite_fifonafe']}/intervinientes").json()
    assert len(intervinientes) == 0

    # Verificar en base de datos directamente que no existen filas parciales
    db = SessionLocal()
    try:
        count = db.execute(
            text(
                "SELECT count(*) FROM tramite_fifonafe_interviniente WHERE id_tramite_fifonafe = :tid"
            ),
            {"tid": tramite["id_tramite_fifonafe"]},
        ).scalar()
        assert count == 0
    finally:
        db.close()


# =========================================================================
# CASO J: Verificación de que la BD sigue rechazando inserción inválida directa
# =========================================================================
def test_caso_j_bd_rechaza_insercion_directa_invalida(api, target_domain):
    project, pn, _, _, tramite = _create_isolated_env(api, target_domain, prefix="CASO-J")
    person = _create_person(api, project["id_proyecto"], "Persona Caso J")
    orv = _create_orv(api, pn["id_proyecto_nucleo"], start="2026-01-01", end="2026-12-31")
    member = _create_member(api, orv["id_orv"], person["id_persona"], start="2026-01-01", end="2026-12-31")

    db = SessionLocal()
    try:
        # Configurar contexto de auditoría para el trigger fn_audit_log
        db.execute(text("SELECT set_config('app.current_user_id', '1', true)"))

        # J1: Intento de insertar directamente id_orv_integrante sin id_evento_fifonafe
        # Debe fallar por el trigger fn_validar_fifonafe_interviniente_008
        with pytest.raises(Exception) as exc_info1:
            db.execute(
                text("""
                    INSERT INTO tramite_fifonafe_interviniente (
                        id_tramite_fifonafe, id_persona, rol, id_orv_integrante, creado_por
                    ) VALUES (
                        :tid, :pid, 'representante', :mid, 1
                    )
                """),
                {
                    "tid": tramite["id_tramite_fifonafe"],
                    "pid": person["id_persona"],
                    "mid": member["id_orv_integrante"],
                },
            )
            db.flush()
        db.rollback()
        assert "La representación ORV histórica requiere un acto FIFONAFE con fecha de negocio" in str(exc_info1.value)

        # J2: Intento de insertar directamente id_orv_integrante de otra persona
        other_person = _create_person(api, project["id_proyecto"], "Otra Persona J")
        event = _create_event(api, tramite["id_tramite_fifonafe"], ordinal=1, event_date="2026-06-15")

        db.execute(text("SELECT set_config('app.current_user_id', '1', true)"))
        with pytest.raises(Exception) as exc_info2:
            db.execute(
                text("""
                    INSERT INTO tramite_fifonafe_interviniente (
                        id_tramite_fifonafe, id_persona, rol, id_evento_fifonafe, id_orv_integrante, creado_por
                    ) VALUES (
                        :tid, :pid, 'representante', :eid, :mid, 1
                    )
                """),
                {
                    "tid": tramite["id_tramite_fifonafe"],
                    "pid": other_person["id_persona"],
                    "eid": event["id_evento_fifonafe"],
                    "mid": member["id_orv_integrante"],
                },
            )
            db.flush()
        db.rollback()
        assert "Integrante ORV no acredita persona, nucleo o vigencia a la fecha del acto" in str(exc_info2.value)

    finally:
        db.close()
