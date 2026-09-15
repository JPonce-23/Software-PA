"""Regresiones del contrato juridico y operativo introducido por schema 016."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from .test_excel_closure_002 import _catalog, _isolated_pn


@pytest.fixture(scope="module")
def api(transactional_api):
    return transactional_api["request"]


@pytest.fixture(scope="module")
def target_domain(transactional_target_domain):
    return transactional_target_domain


@pytest.fixture(scope="module")
def caso_016(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    project_id = project["id_proyecto"]
    pn_id = pn["id_proyecto_nucleo"]
    ciclos = _catalog(api, "tipo_cop_operativo")

    afectaciones = {}
    for codigo in ("ORIGEN", "ADICIONAL", "2A_ADICIONAL", "COMPLEMENTARIAS"):
        afectaciones[codigo] = api(
            "POST",
            f"/api/proyecto-nucleo/{pn_id}/afectaciones",
            expected=201,
            json={
                "tipo_afectacion": "colectivo",
                "id_tipo_cop_operativo": ciclos[codigo],
            },
        ).json()

    original = api(
        "POST",
        f"/api/afectaciones/{afectaciones['ORIGEN']['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "fecha_firma": "2027-01-10",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    modificatorios = {}
    for codigo, consecutivo, fecha in (
        ("ADICIONAL", 72, "2027-02-10"),
        ("2A_ADICIONAL", 41, "2027-03-10"),
    ):
        modificatorios[codigo] = api(
            "POST",
            f"/api/afectaciones/{afectaciones[codigo]['id_afectacion']}/convenios",
            expected=201,
            json={
                "tipo_convenio": "modificatorio",
                "consecutivo": consecutivo,
                "id_convenio_padre": original["id_convenio"],
                "fecha_firma": fecha,
                "estado_antecedente": "vinculado",
            },
        ).json()

    complementarias = api(
        "POST",
        f"/api/afectaciones/{afectaciones['COMPLEMENTARIAS']['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_convenio": "obras_complementarias",
            "consecutivo": 3,
            "id_convenio_padre": original["id_convenio"],
            "fecha_firma": "2027-04-10",
            "estado_antecedente": "vinculado",
        },
    ).json()

    afectacion_individual = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "individual",
            "id_tipo_cop_operativo": ciclos["ORIGEN"],
        },
    ).json()
    parcela = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={
            "tipo_parcela": "individual",
            "no_parcela": f"SCHEMA-016-{uuid.uuid4().hex[:8]}",
        },
    ).json()
    unidad = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_parcela": parcela["id_parcela"],
            "id_tipo_tierra": _catalog(api, "tipo_tierra")["parcelada"],
            "id_tipo_titularidad": _catalog(api, "tipo_titularidad_unidad")["persona"],
        },
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{afectacion_individual['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={"id_unidad_agraria": unidad["id_unidad_agraria"]},
    )

    original_individual = api(
        "POST",
        f"/api/afectaciones/{afectacion_individual['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "estado_antecedente": "no_aplica",
        },
    ).json()
    derivados_individuales = {}
    for tipo, consecutivo in (("ampliacion", 8), ("ampliacion_remanente", 9)):
        derivados_individuales[tipo] = api(
            "POST",
            f"/api/afectaciones/{afectacion_individual['id_afectacion']}/convenios",
            expected=201,
            json={
                "tipo_convenio": tipo,
                "consecutivo": consecutivo,
                "id_convenio_padre": original_individual["id_convenio"],
                "estado_antecedente": "vinculado",
            },
        ).json()

    return {
        "project_id": project_id,
        "pn_id": pn_id,
        "afectaciones": afectaciones,
        "original": original,
        "modificatorios": modificatorios,
        "complementarias": complementarias,
        "original_individual": original_individual,
        "derivados_individuales": derivados_individuales,
    }


def test_api_rechaza_tipo_juridico_retirado(api, caso_016):
    adicional = caso_016["afectaciones"]["ADICIONAL"]
    api(
        "POST",
        f"/api/afectaciones/{adicional['id_afectacion']}/convenios",
        expected=422,
        json={
            "tipo_convenio": "superficie_adicional",
            "consecutivo": 90,
        },
    )

    modificatorio = caso_016["modificatorios"]["ADICIONAL"]
    api(
        "PATCH",
        f"/api/convenios/{modificatorio['id_convenio']}",
        expected=422,
        json={"tipo_convenio": "superficie_adicional"},
    )
    vigente = api("GET", f"/api/convenios/{modificatorio['id_convenio']}").json()
    assert vigente["tipo_convenio"] == "modificatorio"


def test_db_rechaza_insert_y_update_directos(transactional_api, caso_016):
    connection = transactional_api["connection"]

    insert_savepoint = connection.begin_nested()
    try:
        with pytest.raises(DBAPIError) as insert_error:
            connection.execute(
                text(
                    """
                    INSERT INTO convenio (
                        id_proyecto_nucleo, ambito, tipo_instrumento,
                        tipo_convenio, consecutivo, estado_antecedente
                    ) VALUES (
                        :pn, 'colectivo', 'convenio',
                        'superficie_adicional', 9016, 'no_aplica'
                    )
                    """
                ),
                {"pn": caso_016["pn_id"]},
            )
        assert (
            getattr(insert_error.value.orig, "sqlstate", None)
            or getattr(insert_error.value.orig, "pgcode", None)
        ) == "23514"
    finally:
        insert_savepoint.rollback()

    update_savepoint = connection.begin_nested()
    try:
        with pytest.raises(DBAPIError) as update_error:
            connection.execute(
                text(
                    """
                    UPDATE convenio
                       SET tipo_convenio = 'superficie_adicional'
                     WHERE id_convenio = :id_convenio
                    """
                ),
                {"id_convenio": caso_016["original"]["id_convenio"]},
            )
        assert (
            getattr(update_error.value.orig, "sqlstate", None)
            or getattr(update_error.value.orig, "pgcode", None)
        ) == "23514"
    finally:
        update_savepoint.rollback()


def test_ciclos_adicionales_conservan_dimension_juridica(
    transactional_api, caso_016
):
    modificatorios = caso_016["modificatorios"]
    rows = transactional_api["connection"].execute(
        text(
            """
            SELECT id_convenio, tipo_convenio, consecutivo,
                   id_convenio_padre, tipo_cop_operativo_codigo
            FROM vw_convenio_tipo_cop_operativo
            WHERE id_convenio IN (:adicional, :segundo_adicional)
            """
        ),
        {
            "adicional": modificatorios["ADICIONAL"]["id_convenio"],
            "segundo_adicional": modificatorios["2A_ADICIONAL"]["id_convenio"],
        },
    ).mappings().all()

    por_ciclo = {row["tipo_cop_operativo_codigo"]: row for row in rows}
    assert set(por_ciclo) == {"ADICIONAL", "2A_ADICIONAL"}
    assert {row["tipo_convenio"] for row in rows} == {"modificatorio"}
    assert por_ciclo["ADICIONAL"]["consecutivo"] == 72
    assert por_ciclo["2A_ADICIONAL"]["consecutivo"] == 41
    assert {row["id_convenio_padre"] for row in rows} == {
        caso_016["original"]["id_convenio"]
    }


@pytest.mark.parametrize("codigo", ["ADICIONAL", "2A_ADICIONAL"])
def test_reporting_y_filtros_canonicos(api, caso_016, codigo):
    project_id = caso_016["project_id"]
    esperado = caso_016["modificatorios"][codigo]["id_convenio"]

    periodo = api(
        "GET",
        "/api/reportes/avance-periodo"
        f"?id_proyecto={project_id}&tipo_convenio=modificatorio"
        f"&tipo_cop_operativo={codigo}",
    ).json()
    assert periodo
    assert {row["tipo_convenio"] for row in periodo} == {"modificatorio"}
    assert {row["tipo_cop_operativo"] for row in periodo} == {codigo}
    assert {row["indicador"] for row in periodo} == {"superficie_adicional"}

    destino = api(
        "GET",
        "/api/reportes/convenios/colectivos-destino"
        f"?id_proyecto={project_id}&tipo_convenio=modificatorio"
        f"&tipo_cop_operativo={codigo}",
    ).json()
    assert {row["id_convenio"] for row in destino} == {esperado}
    assert {row["tipo_convenio"] for row in destino} == {"modificatorio"}
    assert {row["tipo_cop_operativo"] for row in destino} == {codigo}


def test_obras_complementarias_permanece_sin_cambio(api, caso_016):
    convenio = caso_016["complementarias"]
    vigente = api("GET", f"/api/convenios/{convenio['id_convenio']}").json()
    assert vigente["tipo_convenio"] == "obras_complementarias"
    assert vigente["id_convenio_padre"] == caso_016["original"]["id_convenio"]

    periodo = api(
        "GET",
        "/api/reportes/avance-periodo"
        f"?id_proyecto={caso_016['project_id']}"
        "&tipo_convenio=obras_complementarias"
        "&tipo_cop_operativo=COMPLEMENTARIAS",
    ).json()
    assert periodo
    assert {row["indicador"] for row in periodo} == {"obras_complementarias"}


def test_ampliaciones_y_linaje_individual_permanecen_sin_cambio(api, caso_016):
    padre = caso_016["original_individual"]
    derivados = caso_016["derivados_individuales"]

    assert derivados["ampliacion"]["tipo_convenio"] == "ampliacion"
    assert derivados["ampliacion_remanente"]["tipo_convenio"] == "ampliacion_remanente"
    assert derivados["ampliacion"]["consecutivo"] == 8
    assert derivados["ampliacion_remanente"]["consecutivo"] == 9
    assert {
        derivados["ampliacion"]["id_convenio_padre"],
        derivados["ampliacion_remanente"]["id_convenio_padre"],
    } == {padre["id_convenio"]}
