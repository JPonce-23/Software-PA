"""Pruebas de regresión: incorporación de Pago en reporting.

Verifica los criterios mínimos de la regla funcional:
A. Un Pago aparece una sola vez en reporting.
B. Dos pagos de una misma indemnización aparecen como dos hechos distintos.
C. La suma de montos corresponde exactamente a los pagos registrados.
D. fecha_pago determina año, mes y trimestre (independiente de fecha_resolucion de indemnización).
E. Un estatus 'pagado' sin registro Pago no genera un Pago ficticio.
F. Un Pago no se duplica por relaciones N:M (Convenio, UnidadAgraria, FIFONAFE).
G. Pagos de proyectos o entidades diferentes permanecen aislados.
H. Registros inactivos no participan (baja lógica respetada en toda la cadena).
"""

from decimal import Decimal
import uuid
import pytest
from sqlalchemy import text
from app.database import SessionLocal


def _catalog(api, name: str) -> dict[str, int]:
    return {
        row["codigo"]: row["id_catalogo_opcion"]
        for row in api("GET", f"/api/catalogos/operativos/{name}").json()
    }


def _create_isolated_environment(api, target_domain, municipality_id=None, prefix="QA-PAGO"):
    token = uuid.uuid4().hex[:8]
    tenencia = _catalog(api, "tipo_tenencia")["ejido"]
    project = api(
        "POST",
        "/api/proyectos",
        expected=201,
        json={
            "clave_proyecto": f"{prefix}-{token}",
            "nombre_proyecto": f"Proyecto Pago QA {token}",
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
            "fuente_datos": "qa-pago-test",
        },
    ).json()

    pn = api(
        "POST",
        f"/api/proyectos/{project['id_proyecto']}/nucleos",
        expected=201,
        json={"id_nucleo": nucleus["id_nucleo"]},
    ).json()

    return project, pn, nucleus


def _get_periodic(api, project_id, **params):
    query_parts = [f"id_proyecto={project_id}"]
    for key, val in params.items():
        if val is not None:
            query_parts.append(f"{key}={val}")
    qs = "&".join(query_parts)
    return api("GET", f"/api/reportes/avance-periodo?{qs}").json()


def _dashboard(api, project_id):
    return {
        row["indicador"]: row
        for row in api("GET", f"/api/dashboard/kpi?id_proyecto={project_id}").json()
    }


def test_pago_a_aparece_una_sola_vez(api, target_domain):
    """Criterio A: Un Pago aparece una sola vez en reporting y base de datos."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="PAGO-A")
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    aff = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    ind = api(
        "POST",
        f"/api/afectaciones/{aff['id_afectacion']}/indemnizacion",
        expected=201,
        json={"estatus": "en_proceso"},
    ).json()

    pago = api(
        "POST",
        f"/api/indemnizaciones/{ind['id_indemnizacion']}/pagos",
        expected=201,
        json={
            "fecha_pago": "2026-04-10",
            "monto": "15500.50",
            "beneficiario_nombre": "Beneficiario A",
            "medio_pago": "transferencia",
            "referencia": "PAGO-REF-A",
        },
    ).json()

    pago_id = pago["id_pago"]

    # 1. Verificación directa en vw_hito_seguimiento
    db = SessionLocal()
    try:
        hitos = db.execute(
            text(
                "SELECT clave_hito, indicador, fecha_programada, fecha_realizada, cantidad, superficie_ha, monto "
                "FROM vw_hito_seguimiento WHERE clave_hito = :clave"
            ),
            {"clave": f"pago:{pago_id}"},
        ).mappings().all()

        assert len(hitos) == 1
        h = hitos[0]
        assert h["clave_hito"] == f"pago:{pago_id}"
        assert h["indicador"] == "pagos"
        assert h["fecha_programada"] is None
        assert str(h["fecha_realizada"]) == "2026-04-10"
        assert h["cantidad"] == 1
        assert h["superficie_ha"] is None
        assert Decimal(str(h["monto"])) == Decimal("15500.50")
    finally:
        db.close()

    # 2. Verificación en reporte de avance periódico
    rep = _get_periodic(api, project["id_proyecto"], indicador="pagos")
    assert len(rep) == 1
    r = rep[0]
    assert r["anio"] == 2026
    assert r["mes"] == 4
    assert r["trimestre"] == 2
    assert r["indicador"] == "pagos"
    assert r["programado"] == 0
    assert r["realizado"] == 1
    assert r["cantidad"] == 1
    assert r["superficie_ha"] is None
    assert Decimal(str(r["monto"])) == Decimal("15500.50")

    # 3. Verificación en dashboard KPI
    kpis = _dashboard(api, project["id_proyecto"])
    assert "pagos" in kpis
    kp = kpis["pagos"]
    assert kp["programado"] == 0
    assert kp["realizado"] == 1
    assert kp["cantidad"] == 1
    assert kp["superficie_ha"] is None
    assert Decimal(str(kp["monto"])) == Decimal("15500.50")


def test_pago_b_dos_pagos_misma_indemnizacion_hechos_distintos(api, target_domain):
    """Criterio B: Dos pagos de una misma indemnización aparecen como dos hechos distintos."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="PAGO-B")
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    aff = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    ind = api(
        "POST",
        f"/api/afectaciones/{aff['id_afectacion']}/indemnizacion",
        expected=201,
        json={"estatus": "en_proceso"},
    ).json()

    pago1 = api(
        "POST",
        f"/api/indemnizaciones/{ind['id_indemnizacion']}/pagos",
        expected=201,
        json={
            "fecha_pago": "2026-03-15",
            "monto": "10000.00",
            "beneficiario_nombre": "Beneficiario 1",
        },
    ).json()

    pago2 = api(
        "POST",
        f"/api/indemnizaciones/{ind['id_indemnizacion']}/pagos",
        expected=201,
        json={
            "fecha_pago": "2026-07-20",
            "monto": "25000.00",
            "beneficiario_nombre": "Beneficiario 2",
        },
    ).json()

    # Directo en vista de hitos: deben existir 2 hitos distintos
    db = SessionLocal()
    try:
        hitos = db.execute(
            text(
                "SELECT clave_hito, fecha_realizada, monto FROM vw_hito_seguimiento "
                "WHERE clave_hito IN (:c1, :c2) ORDER BY fecha_realizada"
            ),
            {"c1": f"pago:{pago1['id_pago']}", "c2": f"pago:{pago2['id_pago']}"},
        ).mappings().all()

        assert len(hitos) == 2
        assert hitos[0]["clave_hito"] == f"pago:{pago1['id_pago']}"
        assert str(hitos[0]["fecha_realizada"]) == "2026-03-15"
        assert Decimal(str(hitos[0]["monto"])) == Decimal("10000.00")
        assert hitos[1]["clave_hito"] == f"pago:{pago2['id_pago']}"
        assert str(hitos[1]["fecha_realizada"]) == "2026-07-20"
        assert Decimal(str(hitos[1]["monto"])) == Decimal("25000.00")
    finally:
        db.close()

    # Avance periódico: dos registros en meses separados (mes 3 y mes 7)
    rep = _get_periodic(api, project["id_proyecto"], indicador="pagos")
    assert len(rep) == 2

    marzo = next(r for r in rep if r["mes"] == 3)
    assert marzo["trimestre"] == 1
    assert marzo["realizado"] == 1
    assert marzo["cantidad"] == 1
    assert Decimal(str(marzo["monto"])) == Decimal("10000.00")

    julio = next(r for r in rep if r["mes"] == 7)
    assert julio["trimestre"] == 3
    assert julio["realizado"] == 1
    assert julio["cantidad"] == 1
    assert Decimal(str(julio["monto"])) == Decimal("25000.00")

    # Dashboard anual 2026: suma ambos hechos
    kpis = _dashboard(api, project["id_proyecto"])
    assert kpis["pagos"]["realizado"] == 2
    assert kpis["pagos"]["cantidad"] == 2
    assert Decimal(str(kpis["pagos"]["monto"])) == Decimal("35000.00")


def test_pago_c_suma_montos_exacta_sin_mezcla(api, target_domain):
    """Criterio C: La suma de montos corresponde exactamente a los pagos registrados y no se mezcla con avalúo ni convenios."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="PAGO-C")
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    aff = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "individual",
            "id_tipo_cop_operativo": cop["ORIGEN"],
            "avaluo_monto": "999999.99",
            "superficie_afectada_ha": "2.5",
        },
    ).json()

    ind = api(
        "POST",
        f"/api/afectaciones/{aff['id_afectacion']}/indemnizacion",
        expected=201,
        json={"estatus": "en_proceso", "fecha_programada": "2026-01-01"},
    ).json()

    # Tres pagos en el mismo mes con centavos exactos
    montos = [Decimal("1234.56"), Decimal("2345.67"), Decimal("3456.78")]
    for i, m in enumerate(montos):
        api(
            "POST",
            f"/api/indemnizaciones/{ind['id_indemnizacion']}/pagos",
            expected=201,
            json={
                "fecha_pago": "2026-05-15",
                "monto": str(m),
                "beneficiario_nombre": f"Beneficiario C{i}",
            },
        )

    suma_esperada = sum(montos)  # 7037.01

    rep = _get_periodic(api, project["id_proyecto"], indicador="pagos", anio=2026, mes=5)
    assert len(rep) == 1
    assert Decimal(str(rep[0]["monto"])) == suma_esperada
    assert rep[0]["realizado"] == 3
    assert rep[0]["cantidad"] == 3
    # No se confunde con avalúo ni superficies
    assert rep[0]["superficie_ha"] is None

    # Dashboard anual
    kpis = _dashboard(api, project["id_proyecto"])
    assert Decimal(str(kpis["pagos"]["monto"])) == suma_esperada
    assert kpis["pagos"]["cantidad"] == 3


def test_pago_d_fecha_pago_determina_periodo(api, target_domain):
    """Criterio D: fecha_pago determina año, mes y trimestre; no fecha_resolucion de Indemnizacion."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="PAGO-D")
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    aff = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    # Indemnización resuelta en DICIEMBRE (mes 12, Q4)
    ind = api(
        "POST",
        f"/api/afectaciones/{aff['id_afectacion']}/indemnizacion",
        expected=201,
        json={
            "estatus": "completo",
            "fecha_programada": "2026-02-01",
            "fecha_resolucion": "2026-12-15",
        },
    ).json()

    # Pago realizado en MAYO (mes 5, Q2)
    api(
        "POST",
        f"/api/indemnizaciones/{ind['id_indemnizacion']}/pagos",
        expected=201,
        json={
            "fecha_pago": "2026-05-20",
            "monto": "8000.00",
            "beneficiario_nombre": "Beneficiario D",
        },
    )

    # Filtrar por mes de mayo: Pago DEBE aparecer
    rep_mayo = _get_periodic(api, project["id_proyecto"], anio=2026, mes=5, indicador="pagos")
    assert len(rep_mayo) == 1
    assert rep_mayo[0]["trimestre"] == 2
    assert rep_mayo[0]["realizado"] == 1
    assert Decimal(str(rep_mayo[0]["monto"])) == Decimal("8000.00")

    # Filtrar por mes de diciembre: Pago NO debe aparecer
    rep_dic = _get_periodic(api, project["id_proyecto"], anio=2026, mes=12, indicador="pagos")
    assert len(rep_dic) == 0

    # En cambio, la indemnización resuelta SÍ está en diciembre y NO en mayo
    rep_ind_dic = _get_periodic(api, project["id_proyecto"], anio=2026, mes=12, indicador="indemnizaciones")
    assert len(rep_ind_dic) == 1 and rep_ind_dic[0]["realizado"] == 1

    rep_ind_mayo = _get_periodic(api, project["id_proyecto"], anio=2026, mes=5, indicador="indemnizaciones")
    assert len(rep_ind_mayo) == 0


def test_pago_e_estatus_pagado_sin_pago_no_genera_pago_ficticio(api, target_domain):
    """Criterio E: Un estatus 'pagado' sin registro Pago no genera un Pago ficticio."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="PAGO-E")
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    aff = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    # Indemnización con estatus 'pagado' pero SIN ningún registro en tabla pago
    api(
        "POST",
        f"/api/afectaciones/{aff['id_afectacion']}/indemnizacion",
        expected=201,
        json={
            "estatus": "pagado",
            "fecha_programada": "2026-03-01",
            "fecha_resolucion": "2026-08-15",
        },
    )

    # Avance periódico para indicador 'pagos' debe estar completamente vacío
    rep_pagos = _get_periodic(api, project["id_proyecto"], indicador="pagos")
    assert rep_pagos == []

    # Dashboard para indicador 'pagos' no debe existir
    kpis = _dashboard(api, project["id_proyecto"])
    assert "pagos" not in kpis

    # Consulta directa a vw_hito_seguimiento para este proyecto con indicador 'pagos'
    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                "SELECT * FROM vw_hito_seguimiento WHERE id_proyecto = :pid AND indicador = 'pagos'"
            ),
            {"pid": project["id_proyecto"]},
        ).mappings().all()
        assert len(rows) == 0
    finally:
        db.close()


def test_pago_f_no_duplicacion_por_relaciones_nm(api, target_domain):
    """Criterio F: Un Pago no se duplica por relaciones N:M (Convenios, Unidades Agrarias, FIFONAFE)."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="PAGO-F")
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    titularidad = _catalog(api, "tipo_titularidad_unidad")["persona"]

    aff = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    ind = api(
        "POST",
        f"/api/afectaciones/{aff['id_afectacion']}/indemnizacion",
        expected=201,
        json={"estatus": "en_proceso"},
    ).json()

    # Registrar EXACTAMENTE un Pago
    pago = api(
        "POST",
        f"/api/indemnizaciones/{ind['id_indemnizacion']}/pagos",
        expected=201,
        json={
            "fecha_pago": "2026-06-10",
            "monto": "50000.00",
            "beneficiario_nombre": "Beneficiario NM",
        },
    ).json()

    # Agregar múltiples Unidades Agrarias vinculadas a la afectación (relación N:M)
    for i in range(3):
        parcel = api(
            "POST",
            f"/api/proyecto-nucleo/{pn_id}/parcelas",
            expected=201,
            json={"tipo_parcela": "individual", "no_parcela": f"P-NM-{i}"},
        ).json()
        unit = api(
            "POST",
            f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
            expected=201,
            json={
                "id_tipo_tierra": tierra,
                "id_tipo_titularidad": titularidad,
                "id_parcela": parcel["id_parcela"],
            },
        ).json()
        api(
            "POST",
            f"/api/afectaciones/{aff['id_afectacion']}/unidades-agrarias",
            expected=201,
            json={"id_unidad_agraria": unit["id_unidad_agraria"]},
        )

    # Agregar Convenio con afectación asociada (relación N:M)
    api(
        "POST",
        f"/api/afectaciones/{aff['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "superficie_ha": 3.0,
            "monto_100": 300000.00,
        },
    )

    # Agregar Trámite FIFONAFE vinculado a la afectación (relación N:M)
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/fifonafe",
        expected=201,
        json={"ids_afectacion": [aff["id_afectacion"]]},
    )

    # Verificación en vista de hitos
    db = SessionLocal()
    try:
        hitos = db.execute(
            text(
                "SELECT * FROM vw_hito_seguimiento WHERE id_proyecto = :pid AND indicador = 'pagos'"
            ),
            {"pid": project["id_proyecto"]},
        ).mappings().all()
        assert len(hitos) == 1
        assert hitos[0]["clave_hito"] == f"pago:{pago['id_pago']}"
        assert Decimal(str(hitos[0]["monto"])) == Decimal("50000.00")
    finally:
        db.close()

    # Verificación en reporte de avance periódico
    rep = _get_periodic(api, project["id_proyecto"], indicador="pagos")
    assert len(rep) == 1
    assert rep[0]["realizado"] == 1
    assert rep[0]["cantidad"] == 1
    assert Decimal(str(rep[0]["monto"])) == Decimal("50000.00")

    # Verificación en dashboard KPI
    kpis = _dashboard(api, project["id_proyecto"])
    assert kpis["pagos"]["realizado"] == 1
    assert kpis["pagos"]["cantidad"] == 1
    assert Decimal(str(kpis["pagos"]["monto"])) == Decimal("50000.00")


def test_pago_g_aislamiento_proyecto_y_entidad(api, target_domain):
    """Criterio G: Pagos de proyectos o entidades diferentes permanecen aislados."""
    # Obtener dos entidades federativas distintas con sus municipios
    states = api("GET", "/api/catalogos/entidades").json()
    assert len(states) >= 2
    state_a = states[0]
    state_b = states[1]

    mun_a = api("GET", f"/api/catalogos/municipios?id_entidad={state_a['id_entidad']}").json()[0]
    mun_b = api("GET", f"/api/catalogos/municipios?id_entidad={state_b['id_entidad']}").json()[0]

    cop = _catalog(api, "tipo_cop_operativo")

    # Proyecto A en Entidad A con pago de $11,111.00
    proj_a, pn_a, _ = _create_isolated_environment(
        api, target_domain, municipality_id=mun_a["id_municipio"], prefix="ISO-A"
    )
    aff_a = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_a['id_proyecto_nucleo']}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()
    ind_a = api(
        "POST",
        f"/api/afectaciones/{aff_a['id_afectacion']}/indemnizacion",
        expected=201,
        json={"estatus": "en_proceso"},
    ).json()
    api(
        "POST",
        f"/api/indemnizaciones/{ind_a['id_indemnizacion']}/pagos",
        expected=201,
        json={
            "fecha_pago": "2026-05-10",
            "monto": "11111.00",
            "beneficiario_nombre": "Beneficiario Entidad A",
        },
    )

    # Proyecto B en Entidad B con pago de $22,222.00
    proj_b, pn_b, _ = _create_isolated_environment(
        api, target_domain, municipality_id=mun_b["id_municipio"], prefix="ISO-B"
    )
    aff_b = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_b['id_proyecto_nucleo']}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()
    ind_b = api(
        "POST",
        f"/api/afectaciones/{aff_b['id_afectacion']}/indemnizacion",
        expected=201,
        json={"estatus": "en_proceso"},
    ).json()
    api(
        "POST",
        f"/api/indemnizaciones/{ind_b['id_indemnizacion']}/pagos",
        expected=201,
        json={
            "fecha_pago": "2026-05-10",
            "monto": "22222.00",
            "beneficiario_nombre": "Beneficiario Entidad B",
        },
    )

    # Aislamiento por proyecto
    rep_a = _get_periodic(api, proj_a["id_proyecto"], indicador="pagos")
    assert len(rep_a) == 1
    assert rep_a[0]["id_proyecto"] == proj_a["id_proyecto"]
    assert rep_a[0]["id_entidad"] == state_a["id_entidad"]
    assert Decimal(str(rep_a[0]["monto"])) == Decimal("11111.00")

    rep_b = _get_periodic(api, proj_b["id_proyecto"], indicador="pagos")
    assert len(rep_b) == 1
    assert rep_b[0]["id_proyecto"] == proj_b["id_proyecto"]
    assert rep_b[0]["id_entidad"] == state_b["id_entidad"]
    assert Decimal(str(rep_b[0]["monto"])) == Decimal("22222.00")

    # Aislamiento por entidad
    rep_ent_a = _get_periodic(
        api, proj_a["id_proyecto"], id_entidad=state_a["id_entidad"], indicador="pagos"
    )
    assert len(rep_ent_a) == 1
    assert Decimal(str(rep_ent_a[0]["monto"])) == Decimal("11111.00")

    rep_ent_b_en_a = _get_periodic(
        api, proj_a["id_proyecto"], id_entidad=state_b["id_entidad"], indicador="pagos"
    )
    assert rep_ent_b_en_a == []


def test_pago_h_baja_logica_excluye_inactivos(api, target_domain):
    """Criterio H: Registros inactivos no participan si el modelo aplica baja lógica (pago, indemnizacion, afectacion, proyecto_nucleo)."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="PAGO-H")
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    aff = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    ind = api(
        "POST",
        f"/api/afectaciones/{aff['id_afectacion']}/indemnizacion",
        expected=201,
        json={"estatus": "en_proceso"},
    ).json()

    pago = api(
        "POST",
        f"/api/indemnizaciones/{ind['id_indemnizacion']}/pagos",
        expected=201,
        json={
            "fecha_pago": "2026-09-10",
            "monto": "45000.00",
            "beneficiario_nombre": "Beneficiario Baja",
        },
    ).json()
    pago_id = pago["id_pago"]

    # Inicialmente activo -> visible
    assert len(_get_periodic(api, project["id_proyecto"], indicador="pagos")) == 1

    # H1: Baja lógica del pago
    db = SessionLocal()
    try:
        db.execute(text("SELECT set_config('app.current_user_id', '1', true)"))
        db.execute(
            text(
                "UPDATE pago SET activo = false, fecha_baja = now(), id_usuario_baja = 1, motivo_baja = 'Baja de prueba' "
                "WHERE id_pago = :id"
            ),
            {"id": pago_id},
        )
        db.commit()
    finally:
        db.close()

    # Ya no debe aparecer
    assert _get_periodic(api, project["id_proyecto"], indicador="pagos") == []
    assert "pagos" not in _dashboard(api, project["id_proyecto"])

    # Reactivar pago para probar baja de indemnización
    db = SessionLocal()
    try:
        db.execute(text("SELECT set_config('app.current_user_id', '1', true)"))
        db.execute(
            text(
                "UPDATE pago SET activo = true, fecha_baja = null, id_usuario_baja = null, motivo_baja = null "
                "WHERE id_pago = :id"
            ),
            {"id": pago_id},
        )
        db.commit()
    finally:
        db.close()

    # Vuelve a ser visible
    assert len(_get_periodic(api, project["id_proyecto"], indicador="pagos")) == 1

    # H2: Baja lógica de la indemnización
    db = SessionLocal()
    try:
        db.execute(text("SELECT set_config('app.current_user_id', '1', true)"))
        db.execute(
            text(
                "UPDATE indemnizacion SET activo = false, fecha_baja = now(), id_usuario_baja = 1, motivo_baja = 'Baja indemnización' "
                "WHERE id_indemnizacion = :id"
            ),
            {"id": ind["id_indemnizacion"]},
        )
        db.commit()
    finally:
        db.close()

    # Debe desaparecer
    assert _get_periodic(api, project["id_proyecto"], indicador="pagos") == []

    # Reactivar indemnización para probar baja de afectación
    db = SessionLocal()
    try:
        db.execute(text("SELECT set_config('app.current_user_id', '1', true)"))
        db.execute(
            text(
                "UPDATE indemnizacion SET activo = true, fecha_baja = null, id_usuario_baja = null, motivo_baja = null "
                "WHERE id_indemnizacion = :id"
            ),
            {"id": ind["id_indemnizacion"]},
        )
        db.commit()
    finally:
        db.close()

    # Vuelve a ser visible
    assert len(_get_periodic(api, project["id_proyecto"], indicador="pagos")) == 1

    # H3: Baja lógica de la afectación
    db = SessionLocal()
    try:
        db.execute(text("SELECT set_config('app.current_user_id', '1', true)"))
        db.execute(
            text(
                "UPDATE afectacion SET activo = false, fecha_baja = now(), id_usuario_baja = 1, motivo_baja = 'Baja afectación' "
                "WHERE id_afectacion = :id"
            ),
            {"id": aff["id_afectacion"]},
        )
        db.commit()
    finally:
        db.close()

    # Debe desaparecer
    assert _get_periodic(api, project["id_proyecto"], indicador="pagos") == []
