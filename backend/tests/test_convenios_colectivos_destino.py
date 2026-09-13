"""Pruebas de integración y regresión para el desglose por destino de convenios colectivos.

Verifica los criterios obligatorios (Casos A–J):
Caso A: Convenio colectivo monorubro (sólo TUC) -> 1 destino ('tuc'), superficie igual a la unidad, convenio cuenta 1 vez.
Caso B: Convenio colectivo multidestino (TUC + camino + canal) -> 3 renglones de destino, cada uno con su superficie respectiva, suma igual al total afectado, convenio cuenta 1 vez.
Caso C: Convenio con dos afectaciones del mismo destino -> se consolidan por destino sumando sus superficies, no duplica el destino.
Caso D: Convenio colectivo sin unidades agrarias -> destino NULL, superficie física NULL, monto y superficie declarada conservados.
Caso E: Convenio colectivo con unidad agraria sin destino especificado -> destino NULL, conserva superficie afectada.
Caso F: Dos convenios distintos con destinos compartidos -> importes y superficies independientes; no mezcla montos.
Caso G: Integración con Asamblea -> Asamblea vinculada reporta cantidad = 1 sin afectarse por el número de destinos del convenio.
Caso H: Verificación contra productos cartesianos -> N afectaciones, M unidades, P convenios: superficies coinciden exactamente, montos no se multiplican.
Caso I: Baja lógica -> inactivar AfectacionUnidadAgraria o Convenio excluye inmediatamente su superficie del reporte.
Caso J: Aislamiento por proyecto y entidad -> filtros por id_proyecto y geográficos respetan estrictamente el ámbito consultado. Exclusión de individuales.
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


def _create_isolated_environment(api, target_domain, municipality_id=None, prefix="QA-COL-DEST"):
    token = uuid.uuid4().hex[:8]
    tenencia = _catalog(api, "tipo_tenencia")["ejido"]
    project = api(
        "POST",
        "/api/proyectos",
        expected=201,
        json={
            "clave_proyecto": f"{prefix}-{token}",
            "nombre_proyecto": f"Proyecto Colectivo QA {token}",
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
            "fuente_datos": "qa-col-dest",
        },
    ).json()

    pn = api(
        "POST",
        f"/api/proyectos/{project['id_proyecto']}/nucleos",
        expected=201,
        json={"id_nucleo": nucleus["id_nucleo"]},
    ).json()

    return project, pn, nucleus


def _create_unit_and_link(api, pn_id, af_id, destino_id=None, sup="10.0000000"):
    tierra = _catalog(api, "tipo_tierra")["uso_comun"]
    titular = _catalog(api, "tipo_titularidad_unidad")["nucleo_agrario"]

    unit_payload = {
        "id_tipo_tierra": tierra,
        "id_tipo_titularidad": titular,
        "referencia_alfanumerica": f"UA-{uuid.uuid4().hex[:8]}",
    }
    if destino_id is not None:
        unit_payload["id_destino_superficie"] = destino_id

    u = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json=unit_payload,
    ).json()

    au_payload = {"id_unidad_agraria": u["id_unidad_agraria"]}
    if sup is not None:
        au_payload["superficie_afectada_ha"] = sup

    au = api(
        "POST",
        f"/api/afectaciones/{af_id}/unidades-agrarias",
        expected=201,
        json=au_payload,
    ).json()

    return u, au


def test_caso_a_monorubro_tuc(api, target_domain):
    """Caso A: Convenio colectivo monorubro (sólo TUC) -> 1 destino ('tuc'), superficie igual a la unidad, convenio cuenta 1 vez."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="CASO-A")
    pn_id = pn["id_proyecto_nucleo"]
    destinos = _catalog(api, "destino_superficie")
    cop = _catalog(api, "tipo_cop_operativo")

    af = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    _create_unit_and_link(api, pn_id, af["id_afectacion"], destinos["tuc"], sup="10.5000000")

    conv = api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "10.5000000",
            "monto_100": "100000.00",
            "fecha_firma": "2026-05-15",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    rows = api(
        "GET",
        f"/api/reportes/convenios/colectivos-destino?id_proyecto={project['id_proyecto']}",
    ).json()

    assert len(rows) == 1
    row = rows[0]
    assert row["id_convenio"] == conv["id_convenio"]
    assert row["destino_superficie"] == "tuc"
    assert Decimal(str(row["superficie_ha"])) == Decimal("10.5000000")
    assert Decimal(str(row["superficie_declarada_ha"])) == Decimal("10.5000000")
    assert Decimal(str(row["monto_declarado"])) == Decimal("100000.00")
    assert row["ambito"] == "colectivo"
    assert row["anio"] == 2026
    assert row["mes"] == 5
    assert row["trimestre"] == 2

    # El convenio deduplicado cuenta exactamente 1 vez
    unique_convs = {r["id_convenio"] for r in rows}
    assert len(unique_convs) == 1


def test_caso_b_multidestino(api, target_domain):
    """Caso B: Convenio colectivo multidestino (TUC + camino + canal) -> 3 renglones de destino,

    cada uno con su superficie respectiva, suma igual al total afectado, convenio cuenta 1 vez.
    """
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="CASO-B")
    pn_id = pn["id_proyecto_nucleo"]
    destinos = _catalog(api, "destino_superficie")
    cop = _catalog(api, "tipo_cop_operativo")

    af = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    _create_unit_and_link(api, pn_id, af["id_afectacion"], destinos["tuc"], sup="12.0000000")
    _create_unit_and_link(api, pn_id, af["id_afectacion"], destinos["camino"], sup="3.5000000")
    _create_unit_and_link(api, pn_id, af["id_afectacion"], destinos["canal"], sup="1.5000000")

    conv = api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "18.0000000",
            "monto_100": "500000.00",
            "fecha_firma": "2026-06-20",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    rows = api(
        "GET",
        f"/api/reportes/convenios/colectivos-destino?id_proyecto={project['id_proyecto']}",
    ).json()

    assert len(rows) == 3
    dest_map = {r["destino_superficie"]: Decimal(str(r["superficie_ha"])) for r in rows}
    assert dest_map["tuc"] == Decimal("12.0000000")
    assert dest_map["camino"] == Decimal("3.5000000")
    assert dest_map["canal"] == Decimal("1.5000000")

    # Suma de superficies físicas por destino es exactamente 17.0 ha
    total_fisica = sum(Decimal(str(r["superficie_ha"])) for r in rows)
    assert total_fisica == Decimal("17.0000000")

    # Cada fila preserva la superficie declarada e importe del instrumento sin multiplicar
    for r in rows:
        assert r["id_convenio"] == conv["id_convenio"]
        assert Decimal(str(r["superficie_declarada_ha"])) == Decimal("18.0000000")
        assert Decimal(str(r["monto_declarado"])) == Decimal("500000.00")

    # Convenio cuenta 1 vez
    assert len({r["id_convenio"] for r in rows}) == 1


def test_caso_c_dos_afectaciones_mismo_destino(api, target_domain):
    """Caso C: Convenio con dos afectaciones del mismo destino -> se consolidan por destino sumando sus superficies, no duplica el destino."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="CASO-C")
    pn_id = pn["id_proyecto_nucleo"]
    destinos = _catalog(api, "destino_superficie")
    cop = _catalog(api, "tipo_cop_operativo")

    af1 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()
    af2 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    _create_unit_and_link(api, pn_id, af1["id_afectacion"], destinos["tuc"], sup="8.0000000")
    _create_unit_and_link(api, pn_id, af2["id_afectacion"], destinos["tuc"], sup="6.0000000")

    conv = api(
        "POST",
        f"/api/afectaciones/{af1['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "14.0000000",
            "monto_100": "300000.00",
            "fecha_firma": "2026-07-10",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    # Asociar segunda afectación al mismo convenio
    api(
        "POST",
        f"/api/convenios/{conv['id_convenio']}/afectaciones",
        expected=201,
        json={"id_afectacion": af2["id_afectacion"], "rol": "adicional"},
    )

    rows = api(
        "GET",
        f"/api/reportes/convenios/colectivos-destino?id_convenio={conv['id_convenio']}",
    ).json()

    # Se consolida en exactamente 1 renglón para el destino 'tuc', sumando 8.0 + 6.0 = 14.0
    assert len(rows) == 1
    row = rows[0]
    assert row["destino_superficie"] == "tuc"
    assert Decimal(str(row["superficie_ha"])) == Decimal("14.0000000")
    assert Decimal(str(row["superficie_declarada_ha"])) == Decimal("14.0000000")
    assert Decimal(str(row["monto_declarado"])) == Decimal("300000.00")


def test_caso_d_sin_unidades_agrarias(api, target_domain):
    """Caso D: Convenio colectivo sin unidades agrarias -> destino NULL, superficie física NULL, monto y superficie declarada conservados."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="CASO-D")
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    af = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    conv = api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "20.0000000",
            "monto_100": "250000.00",
            "fecha_firma": "2026-08-01",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    rows = api(
        "GET",
        f"/api/reportes/convenios/colectivos-destino?id_convenio={conv['id_convenio']}",
    ).json()

    assert len(rows) == 1
    row = rows[0]
    assert row["destino_superficie"] is None
    assert row["superficie_ha"] is None  # NULL no es 0.00
    assert Decimal(str(row["superficie_declarada_ha"])) == Decimal("20.0000000")
    assert Decimal(str(row["monto_declarado"])) == Decimal("250000.00")


def test_caso_e_unidad_sin_destino_especificado(api, target_domain):
    """Caso E: Convenio colectivo con unidad agraria sin destino especificado -> destino NULL, conserva superficie afectada."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="CASO-E")
    pn_id = pn["id_proyecto_nucleo"]
    cop = _catalog(api, "tipo_cop_operativo")

    af = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    # Unidad sin destino_superficie
    _create_unit_and_link(api, pn_id, af["id_afectacion"], destino_id=None, sup="9.2500000")

    conv = api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "9.2500000",
            "monto_100": "120000.00",
            "fecha_firma": "2026-08-15",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    rows = api(
        "GET",
        f"/api/reportes/convenios/colectivos-destino?id_convenio={conv['id_convenio']}",
    ).json()

    assert len(rows) == 1
    row = rows[0]
    assert row["destino_superficie"] is None
    assert Decimal(str(row["superficie_ha"])) == Decimal("9.2500000")
    assert Decimal(str(row["superficie_declarada_ha"])) == Decimal("9.2500000")
    assert Decimal(str(row["monto_declarado"])) == Decimal("120000.00")


def test_caso_f_dos_convenios_destinos_compartidos(api, target_domain):
    """Caso F: Dos convenios distintos con destinos compartidos -> importes y superficies independientes; no mezcla montos."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="CASO-F")
    pn_id = pn["id_proyecto_nucleo"]
    destinos = _catalog(api, "destino_superficie")
    cop = _catalog(api, "tipo_cop_operativo")

    af1 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()
    af2 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    _create_unit_and_link(api, pn_id, af1["id_afectacion"], destinos["tuc"], sup="5.0000000")
    _create_unit_and_link(api, pn_id, af2["id_afectacion"], destinos["tuc"], sup="7.0000000")

    conv1 = api(
        "POST",
        f"/api/afectaciones/{af1['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "5.0000000",
            "monto_100": "100000.00",
            "fecha_firma": "2026-03-10",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    conv2 = api(
        "POST",
        f"/api/afectaciones/{af2['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "7.0000000",
            "monto_100": "200000.00",
            "fecha_firma": "2026-04-10",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    rows = api(
        "GET",
        f"/api/reportes/convenios/colectivos-destino?id_proyecto={project['id_proyecto']}",
    ).json()

    assert len(rows) == 2
    row_conv1 = next(r for r in rows if r["id_convenio"] == conv1["id_convenio"])
    row_conv2 = next(r for r in rows if r["id_convenio"] == conv2["id_convenio"])

    assert row_conv1["destino_superficie"] == "tuc"
    assert Decimal(str(row_conv1["superficie_ha"])) == Decimal("5.0000000")
    assert Decimal(str(row_conv1["monto_declarado"])) == Decimal("100000.00")

    assert row_conv2["destino_superficie"] == "tuc"
    assert Decimal(str(row_conv2["superficie_ha"])) == Decimal("7.0000000")
    assert Decimal(str(row_conv2["monto_declarado"])) == Decimal("200000.00")

    # Conteo deduplicado de convenios y suma de montos sin multiplicación
    unique_convs = {r["id_convenio"]: Decimal(str(r["monto_declarado"])) for r in rows}
    assert len(unique_convs) == 2
    assert sum(unique_convs.values()) == Decimal("300000.00")


def test_caso_g_integracion_asamblea(api, target_domain):
    """Caso G: Integración con Asamblea -> Asamblea vinculada reporta cantidad = 1 sin afectarse por el número de destinos del convenio."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="CASO-G")
    pn_id = pn["id_proyecto_nucleo"]
    destinos = _catalog(api, "destino_superficie")
    cop = _catalog(api, "tipo_cop_operativo")
    tipo_asamblea = _catalog(api, "tipo_asamblea")["anuencia"]

    # Crear asamblea
    asamblea = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": tipo_asamblea,
            "proposito": "Asamblea de anuencia y autorización de convenio",
        },
    ).json()
    asamblea_id = asamblea["id_asamblea"]

    af = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    _create_unit_and_link(api, pn_id, af["id_afectacion"], destinos["tuc"], sup="10.0000000")
    _create_unit_and_link(api, pn_id, af["id_afectacion"], destinos["camino"], sup="2.0000000")

    conv = api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "12.0000000",
            "monto_100": "450000.00",
            "fecha_firma": "2026-09-05",
            "id_asamblea_autorizacion": asamblea_id,
            "estado_antecedente": "no_aplica",
        },
    ).json()

    rows = api(
        "GET",
        f"/api/reportes/convenios/colectivos-destino?id_asamblea={asamblea_id}",
    ).json()

    assert len(rows) == 2
    for r in rows:
        assert r["id_asamblea"] == asamblea_id
        assert r["id_convenio"] == conv["id_convenio"]

    # Deduplicación: exactamente 1 asamblea asociada a pesar de múltiples destinos
    unique_asambleas = {r["id_asamblea"] for r in rows if r["id_asamblea"] is not None}
    assert len(unique_asambleas) == 1


def test_caso_h_anti_producto_cartesiano(api, target_domain):
    """Caso H: Verificación contra productos cartesianos -> N afectaciones, M unidades, P convenios.

    Totales de superficie física por destino coinciden exactamente con afectacion_unidad_agraria, y montos de convenio no se multiplican.
    """
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="CASO-H")
    pn_id = pn["id_proyecto_nucleo"]
    destinos = _catalog(api, "destino_superficie")
    cop = _catalog(api, "tipo_cop_operativo")

    # Afectacion 1: 2 unidades ('tuc': 3.0, 'camino': 2.0)
    af1 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()
    _create_unit_and_link(api, pn_id, af1["id_afectacion"], destinos["tuc"], sup="3.0000000")
    _create_unit_and_link(api, pn_id, af1["id_afectacion"], destinos["camino"], sup="2.0000000")

    # Afectacion 2: 2 unidades ('canal': 4.0, 'derecho_paso': 1.5)
    af2 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()
    _create_unit_and_link(api, pn_id, af2["id_afectacion"], destinos["canal"], sup="4.0000000")
    _create_unit_and_link(api, pn_id, af2["id_afectacion"], destinos["derecho_paso"], sup="1.5000000")

    # Convenio 1 sobre af1
    conv1 = api(
        "POST",
        f"/api/afectaciones/{af1['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "5.0000000",
            "monto_100": "50000.00",
            "fecha_firma": "2026-05-01",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    # Convenio 2 sobre af2
    conv2 = api(
        "POST",
        f"/api/afectaciones/{af2['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "5.5000000",
            "monto_100": "75000.00",
            "fecha_firma": "2026-05-10",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    rows = api(
        "GET",
        f"/api/reportes/convenios/colectivos-destino?id_proyecto={project['id_proyecto']}",
    ).json()

    # Debe haber exactamente 4 filas (2 destinos por convenio)
    assert len(rows) == 4

    # Verificar superficies físicas por destino sumadas en el proyecto
    superficies_por_destino = {}
    for r in rows:
        d = r["destino_superficie"]
        superficies_por_destino[d] = superficies_por_destino.get(d, Decimal("0")) + Decimal(str(r["superficie_ha"]))

    assert superficies_por_destino["tuc"] == Decimal("3.0000000")
    assert superficies_por_destino["camino"] == Decimal("2.0000000")
    assert superficies_por_destino["canal"] == Decimal("4.0000000")
    assert superficies_por_destino["derecho_paso"] == Decimal("1.5000000")
    assert sum(superficies_por_destino.values()) == Decimal("10.5000000")

    # Conteo de convenios deduplicados
    unique_conv_ids = {r["id_convenio"] for r in rows}
    assert len(unique_conv_ids) == 2

    # Montos totales deduplicados
    unique_montos = {r["id_convenio"]: Decimal(str(r["monto_declarado"])) for r in rows}
    assert sum(unique_montos.values()) == Decimal("125000.00")


def test_caso_i_baja_logica(api, target_domain):
    """Caso I: Baja lógica -> inactivar una AfectacionUnidadAgraria o un Convenio excluye inmediatamente su superficie del reporte del destino."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="CASO-I")
    pn_id = pn["id_proyecto_nucleo"]
    destinos = _catalog(api, "destino_superficie")
    cop = _catalog(api, "tipo_cop_operativo")

    af = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    u_tuc, au_tuc = _create_unit_and_link(api, pn_id, af["id_afectacion"], destinos["tuc"], sup="5.0000000")
    u_cam, au_cam = _create_unit_and_link(api, pn_id, af["id_afectacion"], destinos["camino"], sup="3.0000000")

    conv = api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "8.0000000",
            "monto_100": "150000.00",
            "fecha_firma": "2026-06-01",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    # 1. Antes de la baja lógica: 2 destinos presentes
    rows_pre = api(
        "GET",
        f"/api/reportes/convenios/colectivos-destino?id_convenio={conv['id_convenio']}",
    ).json()
    assert len(rows_pre) == 2
    assert {r["destino_superficie"] for r in rows_pre} == {"tuc", "camino"}

    # 2. Inactivar el vínculo afectacion_unidad_agraria de camino
    api(
        "DELETE",
        f"/api/afectacion-unidades-agrarias/{au_cam['id_afectacion_unidad']}",
        expected=200,
        json={"motivo": "Baja de unidad camino por ajuste de trazo"},
    )

    # 3. Después de la baja de au: sólo 'tuc' permanece con 5.0 ha
    rows_post = api(
        "GET",
        f"/api/reportes/convenios/colectivos-destino?id_convenio={conv['id_convenio']}",
    ).json()
    assert len(rows_post) == 1
    assert rows_post[0]["destino_superficie"] == "tuc"
    assert Decimal(str(rows_post[0]["superficie_ha"])) == Decimal("5.0000000")

    # 4. Inactivar el convenio completo en base de datos
    db = SessionLocal()
    try:
        db.execute(text("SELECT set_config('app.current_user_id', '1', true)"))
        db.execute(
            text("UPDATE convenio SET activo = false, fecha_baja = now(), id_usuario_baja = 1, motivo_baja = 'Baja de prueba' WHERE id_convenio = :cid"),
            {"cid": conv["id_convenio"]},
        )
        db.commit()
    finally:
        db.close()

    rows_inactivo = api(
        "GET",
        f"/api/reportes/convenios/colectivos-destino?id_convenio={conv['id_convenio']}",
    ).json()
    assert len(rows_inactivo) == 0


def test_caso_j_aislamiento_proyecto_y_entidad_y_exclusion_individual(api, target_domain):
    """Caso J: Aislamiento por proyecto y entidad -> filtros por id_proyecto y geográficos respetan estrictamente el ámbito consultado.

    Además verifica que los convenios individuales no se mezclan con los colectivos.
    """
    destinos = _catalog(api, "destino_superficie")
    cop = _catalog(api, "tipo_cop_operativo")

    # Proyecto A
    proj_a, pn_a, _ = _create_isolated_environment(api, target_domain, prefix="PROY-A")
    af_a = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_a['id_proyecto_nucleo']}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()
    _create_unit_and_link(api, pn_a["id_proyecto_nucleo"], af_a["id_afectacion"], destinos["tuc"], sup="10.0000000")
    conv_a = api(
        "POST",
        f"/api/afectaciones/{af_a['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "10.0000000",
            "monto_100": "100000.00",
            "fecha_firma": "2026-07-01",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    # Proyecto B
    proj_b, pn_b, _ = _create_isolated_environment(api, target_domain, prefix="PROY-B")
    af_b = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_b['id_proyecto_nucleo']}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()
    _create_unit_and_link(api, pn_b["id_proyecto_nucleo"], af_b["id_afectacion"], destinos["camino"], sup="4.0000000")
    conv_b = api(
        "POST",
        f"/api/afectaciones/{af_b['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "4.0000000",
            "monto_100": "40000.00",
            "fecha_firma": "2026-07-05",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    # Convenio individual en Proyecto A (NO debe aparecer en este endpoint colectivo)
    af_ind = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_a['id_proyecto_nucleo']}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()
    conv_ind = api(
        "POST",
        f"/api/afectaciones/{af_ind['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "1.0000000",
            "monto_100": "10000.00",
            "efecto_monto": "pendiente",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    # 1. Filtro por Proyecto A: sólo conv_a
    rows_a = api(
        "GET",
        f"/api/reportes/convenios/colectivos-destino?id_proyecto={proj_a['id_proyecto']}",
    ).json()
    assert len(rows_a) == 1
    assert rows_a[0]["id_convenio"] == conv_a["id_convenio"]
    assert rows_a[0]["destino_superficie"] == "tuc"

    # Verificar que el individual no aparece
    assert not any(r["id_convenio"] == conv_ind["id_convenio"] for r in rows_a)

    # 2. Filtro por Proyecto B: sólo conv_b
    rows_b = api(
        "GET",
        f"/api/reportes/convenios/colectivos-destino?id_proyecto={proj_b['id_proyecto']}",
    ).json()
    assert len(rows_b) == 1
    assert rows_b[0]["id_convenio"] == conv_b["id_convenio"]
    assert rows_b[0]["destino_superficie"] == "camino"

    # 3. Alias /destinos retorna exactamente lo mismo
    rows_alias = api(
        "GET",
        f"/api/reportes/convenios/destinos?id_proyecto={proj_a['id_proyecto']}",
    ).json()
    assert rows_alias == rows_a


def test_filtros_temporales_y_clasificacion(api, target_domain):
    """Verifica filtros por anio, mes, trimestre, tipo_convenio, tipo_cop_operativo y destino_superficie."""
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="FILTROS")
    pn_id = pn["id_proyecto_nucleo"]
    destinos = _catalog(api, "destino_superficie")
    cop = _catalog(api, "tipo_cop_operativo")

    af = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    _create_unit_and_link(api, pn_id, af["id_afectacion"], destinos["tuc"], sup="5.0000000")
    _create_unit_and_link(api, pn_id, af["id_afectacion"], destinos["camino"], sup="2.0000000")

    conv = api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "7.0000000",
            "monto_100": "70000.00",
            "fecha_firma": "2026-11-20",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    base_url = f"/api/reportes/convenios/colectivos-destino?id_proyecto={project['id_proyecto']}"

    # Filtro año y mes
    assert len(api("GET", f"{base_url}&anio=2026&mes=11").json()) == 2
    assert len(api("GET", f"{base_url}&anio=2026&mes=10").json()) == 0

    # Filtro trimestre
    assert len(api("GET", f"{base_url}&trimestre=4").json()) == 2
    assert len(api("GET", f"{base_url}&trimestre=1").json()) == 0

    # Filtro destino
    rows_tuc = api("GET", f"{base_url}&destino_superficie=tuc").json()
    assert len(rows_tuc) == 1
    assert rows_tuc[0]["destino_superficie"] == "tuc"

    # Filtro tipo_convenio
    assert len(api("GET", f"{base_url}&tipo_convenio=cop_original").json()) == 2
    assert len(api("GET", f"{base_url}&tipo_convenio=modificatorio").json()) == 0

    # Filtro tipo_cop_operativo
    assert len(api("GET", f"{base_url}&tipo_cop_operativo=ORIGEN").json()) == 2


def test_monto_declarado_no_aditivo_multidestino_total_oficial_500k(api, target_domain):
    """Verifica que un convenio con 3 destinos y monto_100 = 500000 produce monto total oficial = 500000, nunca 1500000.

    1. En vw_convenio_colectivo_destino (GET /api/reportes/convenios/colectivos-destino):
       - Se retornan 3 filas (una por cada destino: tuc, camino, canal).
       - Cada fila repite monto_declarado = 500000.00 como atributo descriptivo del instrumento completo.
       - La agregación oficial deduplicada por id_convenio suma exactamente 500000.00, NUNCA 1500000.00.
    2. En los reportes económicos oficiales agregados (GET /api/reportes/convenios/valores-declarados,
       GET /api/reportes/convenios/impactos):
       - El monto oficial reportado es exactamente 500000.00, nunca 1500000.00.
       - La presencia de 3 destinos físicos en el convenio no triplica el valor declarado ni los impactos.
    """
    project, pn, _ = _create_isolated_environment(api, target_domain, prefix="NO-ADIT")
    pn_id = pn["id_proyecto_nucleo"]
    destinos = _catalog(api, "destino_superficie")
    cop = _catalog(api, "tipo_cop_operativo")

    af = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo", "id_tipo_cop_operativo": cop["ORIGEN"]},
    ).json()

    # 3 destinos físicos asociados a la misma afectación
    _create_unit_and_link(api, pn_id, af["id_afectacion"], destinos["tuc"], sup="10.0000000")
    _create_unit_and_link(api, pn_id, af["id_afectacion"], destinos["camino"], sup="3.0000000")
    _create_unit_and_link(api, pn_id, af["id_afectacion"], destinos["canal"], sup="2.0000000")

    # Convenio colectivo con monto_100 = 500000.00
    conv = api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": "15.0000000",
            "monto_100": "500000.00",
            "efecto_monto": "adicion",
            "monto_100_impacto": "500000.00",
            "fecha_firma": "2026-06-15",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    # A. Consulta del endpoint de desglose por destino
    rows_destinos = api(
        "GET",
        f"/api/reportes/convenios/colectivos-destino?id_proyecto={project['id_proyecto']}",
    ).json()

    assert len(rows_destinos) == 3
    # Cada fila expone el monto descriptivo del instrumento
    for r in rows_destinos:
        assert Decimal(str(r["monto_declarado"])) == Decimal("500000.00")

    # Si alguien sumara ingenuamente la columna monto_declarado sin deduplicar, obtendría erróneamente 1,500,000.00
    suma_ingenua_erronea = sum(Decimal(str(r["monto_declarado"])) for r in rows_destinos)
    assert suma_ingenua_erronea == Decimal("1500000.00")

    # El monto total oficial deduplicando por id_convenio es estrictamente 500,000.00, NUNCA 1,500,000.00
    monto_oficial_colectivo = sum(
        {r["id_convenio"]: Decimal(str(r["monto_declarado"])) for r in rows_destinos}.values()
    )
    assert monto_oficial_colectivo == Decimal("500000.00")
    assert monto_oficial_colectivo != Decimal("1500000.00")

    # B. Consulta de los reportes oficiales agregados de convenios
    # 1. valores-declarados: 1 fila de monto_100 con 500,000.00
    vd_rows = api(
        "GET",
        f"/api/reportes/convenios/valores-declarados?id_proyecto={project['id_proyecto']}&concepto=monto_100_declarado",
    ).json()
    assert len(vd_rows) == 1
    assert Decimal(str(vd_rows[0]["valor_declarado"])) == Decimal("500000.00")

    # 2. impactos: 1 fila de monto_100 con 500,000.00 (cero multiplicación por las 3 unidades)
    imp_rows = api(
        "GET",
        f"/api/reportes/convenios/impactos?id_proyecto={project['id_proyecto']}&concepto=monto_100",
    ).json()
    assert len(imp_rows) == 1
    assert Decimal(str(imp_rows[0]["valor_impacto"])) == Decimal("500000.00")

    # Suma total económica del proyecto en impactos oficiales
    total_economico_oficial = sum(
        Decimal(str(r["valor_impacto"])) for r in imp_rows if r["valor_impacto"] is not None
    )
    assert total_economico_oficial == Decimal("500000.00")
    assert total_economico_oficial != Decimal("1500000.00")
