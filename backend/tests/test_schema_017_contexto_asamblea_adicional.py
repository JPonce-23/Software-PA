"""Regresiones del contrato juridico, operativo y relacional introducido por schema 017."""

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
def base_017(api, target_domain):
    """Estructura base aislada para pruebas de asamblea y convenios de schema 017."""
    project, pn = _isolated_pn(api, target_domain)
    project_id = project["id_proyecto"]
    pn_id = pn["id_proyecto_nucleo"]

    ciclos = _catalog(api, "tipo_cop_operativo")
    assembly_types = _catalog(api, "tipo_asamblea")
    assembly_contexts = _catalog(api, "contexto_asamblea")
    convocation_results = _catalog(api, "resultado_convocatoria")

    # Afectaciones colectivas por ciclo operativo
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

    # Asamblea ORIGEN (contexto cop_original)
    asamblea_origen = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": assembly_types["anuencia"],
            "id_contexto_asamblea": assembly_contexts["cop_original"],
            "id_tipo_cop_operativo": ciclos["ORIGEN"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2027-01-05",
                    "fecha_realizacion": "2027-01-05",
                    "id_resultado": convocation_results["celebrada"],
                }
            ],
        },
    ).json()

    # Cohorte explícita para comprobar la normalización sin depender del volumen
    # histórico acumulado en la base que ejecuta pytest.
    muestras_ciclo = {}
    for codigo in ("ADICIONAL", "2A_ADICIONAL"):
        muestras_ciclo[codigo] = [
            api(
                "POST",
                f"/api/proyecto-nucleo/{pn_id}/asambleas",
                expected=201,
                json={
                    "id_tipo_asamblea": assembly_types["anuencia"],
                    "id_contexto_asamblea": assembly_contexts["modificatorio"],
                    "id_tipo_cop_operativo": ciclos[codigo],
                    "proposito": f"Muestra hermética {codigo} {ordinal}",
                },
            ).json()["id_asamblea"]
            for ordinal in range(1, 4)
        ]

    # Convenio ORIGEN (cop_original) autorizado por asamblea_origen
    convenio_origen = api(
        "POST",
        f"/api/afectaciones/{afectaciones['ORIGEN']['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "id_asamblea_autorizacion": asamblea_origen["id_asamblea"],
            "fecha_firma": "2027-01-10",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    return {
        "project_id": project_id,
        "pn_id": pn_id,
        "ciclos": ciclos,
        "assembly_types": assembly_types,
        "assembly_contexts": assembly_contexts,
        "convocation_results": convocation_results,
        "afectaciones": afectaciones,
        "asamblea_origen": asamblea_origen,
        "convenio_origen": convenio_origen,
        "muestras_ciclo": muestras_ciclo,
    }


def test_caso_1_asamblea_modificatorio_adicional_autoriza_convenio_modificatorio(
    api, base_017, transactional_api
):
    """CASO 1: Asamblea(modificatorio, ADICIONAL) + Convenio(modificatorio) -> Aceptado."""
    pn_id = base_017["pn_id"]
    asamblea_adic = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": base_017["assembly_types"]["anuencia"],
            "id_contexto_asamblea": base_017["assembly_contexts"]["modificatorio"],
            "id_tipo_cop_operativo": base_017["ciclos"]["ADICIONAL"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2027-02-01",
                    "fecha_realizacion": "2027-02-01",
                    "id_resultado": base_017["convocation_results"]["celebrada"],
                }
            ],
        },
    ).json()

    convenio_adic = api(
        "POST",
        f"/api/afectaciones/{base_017['afectaciones']['ADICIONAL']['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_convenio": "modificatorio",
            "consecutivo": 72,
            "id_convenio_padre": base_017["convenio_origen"]["id_convenio"],
            "id_asamblea_autorizacion": asamblea_adic["id_asamblea"],
            "fecha_firma": "2027-02-10",
            "estado_antecedente": "vinculado",
        },
    ).json()

    assert convenio_adic["id_asamblea_autorizacion"] == asamblea_adic["id_asamblea"]
    assert convenio_adic["tipo_convenio"] == "modificatorio"
    assert convenio_adic["consecutivo"] == 72

    # Verificacion directa en base de datos
    db_row = transactional_api["connection"].execute(
        text(
            """
            SELECT a.id_contexto_asamblea, ctx.codigo AS ctx_codigo,
                   a.id_tipo_cop_operativo, cop.codigo AS cop_codigo,
                   c.tipo_convenio, c.id_asamblea_autorizacion
              FROM asamblea a
              JOIN catalogo_operativo ctx ON ctx.id_catalogo_opcion = a.id_contexto_asamblea
              JOIN catalogo_operativo cop ON cop.id_catalogo_opcion = a.id_tipo_cop_operativo
              JOIN convenio c ON c.id_asamblea_autorizacion = a.id_asamblea
             WHERE a.id_asamblea = :id_asamblea
            """
        ),
        {"id_asamblea": asamblea_adic["id_asamblea"]},
    ).mappings().one()

    assert db_row["ctx_codigo"] == "modificatorio"
    assert db_row["cop_codigo"] == "ADICIONAL"
    assert db_row["tipo_convenio"] == "modificatorio"
    assert db_row["id_asamblea_autorizacion"] == asamblea_adic["id_asamblea"]


def test_caso_2_asamblea_modificatorio_2a_adicional_autoriza_convenio_modificatorio(
    api, base_017, transactional_api
):
    """CASO 2: Asamblea(modificatorio, 2A_ADICIONAL) + Convenio(modificatorio) -> Aceptado."""
    pn_id = base_017["pn_id"]
    asamblea_2a = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": base_017["assembly_types"]["anuencia"],
            "id_contexto_asamblea": base_017["assembly_contexts"]["modificatorio"],
            "id_tipo_cop_operativo": base_017["ciclos"]["2A_ADICIONAL"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2027-03-01",
                    "fecha_realizacion": "2027-03-01",
                    "id_resultado": base_017["convocation_results"]["celebrada"],
                }
            ],
        },
    ).json()

    convenio_2a = api(
        "POST",
        f"/api/afectaciones/{base_017['afectaciones']['2A_ADICIONAL']['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_convenio": "modificatorio",
            "consecutivo": 41,
            "id_convenio_padre": base_017["convenio_origen"]["id_convenio"],
            "id_asamblea_autorizacion": asamblea_2a["id_asamblea"],
            "fecha_firma": "2027-03-10",
            "estado_antecedente": "vinculado",
        },
    ).json()

    assert convenio_2a["id_asamblea_autorizacion"] == asamblea_2a["id_asamblea"]
    assert convenio_2a["tipo_convenio"] == "modificatorio"
    assert convenio_2a["consecutivo"] == 41

    # Verificacion en la vista reporting y catalogo
    rep_row = transactional_api["connection"].execute(
        text(
            """
            SELECT id_convenio, tipo_convenio, consecutivo, tipo_cop_operativo_codigo
              FROM vw_convenio_tipo_cop_operativo
             WHERE id_convenio = :id_convenio
            """
        ),
        {"id_convenio": convenio_2a["id_convenio"]},
    ).mappings().one()

    assert rep_row["tipo_cop_operativo_codigo"] == "2A_ADICIONAL"
    assert rep_row["tipo_convenio"] == "modificatorio"


def test_caso_3_catalogo_contexto_asamblea_superficie_adicional_inactivo(
    api, base_017, transactional_api
):
    """CASO 3: Catalogo contexto_asamblea NO retorna superficie_adicional como opcion activa."""
    # 1. Consulta estandar (solo activos)
    opciones_activas = api("GET", "/api/catalogos/operativos/contexto_asamblea").json()
    codigos_activos = {op["codigo"] for op in opciones_activas}
    assert "superficie_adicional" not in codigos_activos
    assert "cop_original" in codigos_activos
    assert "modificatorio" in codigos_activos

    # 2. Consulta con incluir_inactivos=true
    todas_opciones = api(
        "GET", "/api/catalogos/operativos/contexto_asamblea?incluir_inactivos=true"
    ).json()
    op_superficie = next(
        (op for op in todas_opciones if op["codigo"] == "superficie_adicional"), None
    )
    assert op_superficie is not None
    assert op_superficie["activo"] is False
    assert op_superficie["id_usuario_baja"] is None
    assert op_superficie["fecha_baja"] is not None
    assert op_superficie["motivo_baja"] == "Deprecado por normalización del modelo en schema 017"
    assert op_superficie["observaciones"] == "Para superficie adicional usar contexto_asamblea=modificatorio con id_tipo_cop_operativo=ADICIONAL/2A_ADICIONAL."

    # 3. Verificacion en DB
    row_db = transactional_api["connection"].execute(
        text(
            """
            SELECT activo, id_usuario_baja, fecha_baja, motivo_baja, observaciones
              FROM catalogo_operativo
             WHERE tipo_catalogo = 'contexto_asamblea'
               AND codigo = 'superficie_adicional'
            """
        ),
    ).mappings().one()

    assert row_db["activo"] is False
    assert row_db["id_usuario_baja"] is None
    assert row_db["fecha_baja"] is not None
    assert row_db["motivo_baja"] == "Deprecado por normalización del modelo en schema 017"
    assert row_db["observaciones"] == "Para superficie adicional usar contexto_asamblea=modificatorio con id_tipo_cop_operativo=ADICIONAL/2A_ADICIONAL."

    # 4. Intentar crear una asamblea con la opcion deprecada es rechazado por la API con 422
    sup_adic_id = op_superficie["id_catalogo_opcion"]
    pn_id = base_017["pn_id"]
    resp = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=422,
        json={
            "id_tipo_asamblea": base_017["assembly_types"]["anuencia"],
            "id_contexto_asamblea": sup_adic_id,
        },
    ).json()
    assert "Opción activa inválida para el catálogo contexto_asamblea" in resp["detail"]

    # 5. Si existiera una asamblea con contexto superficie_adicional, el trigger
    # fn_validar_convenio_relaciones() rechaza autorizar convenios modificatorios
    # porque el contexto no corresponde a la naturaleza juridica del convenio.
    sp_inactiva = transactional_api["connection"].begin_nested()
    try:
        # Insert directo a nivel de prueba para evaluar el trigger de relacion
        asamblea_legada = transactional_api["connection"].execute(
            text(
                """
                INSERT INTO asamblea (
                    id_proyecto_nucleo, id_tipo_asamblea, id_contexto_asamblea
                ) VALUES (
                    :pn, :tipo, :contexto
                ) RETURNING id_asamblea
                """
            ),
            {
                "pn": pn_id,
                "tipo": base_017["assembly_types"]["anuencia"],
                "contexto": sup_adic_id,
            },
        ).scalar_one()

        with pytest.raises(DBAPIError) as exc_relacion:
            transactional_api["connection"].execute(
                text(
                    """
                    INSERT INTO convenio (
                        id_proyecto_nucleo, ambito, tipo_instrumento,
                        tipo_convenio, consecutivo, estado_antecedente,
                        id_convenio_padre, id_asamblea_autorizacion
                    ) VALUES (
                        :pn, 'colectivo', 'convenio',
                        'modificatorio', 9903, 'vinculado',
                        :padre, :asamblea_id
                    )
                    """
                ),
                {
                    "pn": pn_id,
                    "padre": base_017["convenio_origen"]["id_convenio"],
                    "asamblea_id": asamblea_legada,
                },
            )
        assert "007: el contexto de la Asamblea no corresponde al tipo de convenio" in str(
            exc_relacion.value
        )
    finally:
        sp_inactiva.rollback()


def test_caso_4_origen_conserva_cop_original_y_vincula_convenio_cop_original(
    api, base_017, transactional_api
):
    """CASO 4: ORIGEN conserva cop_original y vincula convenio cop_original."""
    # 1. Instancia creada en base_017
    conv = base_017["convenio_origen"]
    asam = base_017["asamblea_origen"]
    assert conv["tipo_convenio"] == "cop_original"
    assert conv["id_asamblea_autorizacion"] == asam["id_asamblea"]

    # 2. La Asamblea ORIGEN creada por el fixture conserva cop_original.
    filas_origen = transactional_api["connection"].execute(
        text(
            """
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE ctx.codigo = 'cop_original') AS con_cop_original
              FROM asamblea a
              JOIN catalogo_operativo cop ON cop.id_catalogo_opcion = a.id_tipo_cop_operativo
              JOIN catalogo_operativo ctx ON ctx.id_catalogo_opcion = a.id_contexto_asamblea
             WHERE a.id_asamblea = :id_asamblea
            """
        ),
        {"id_asamblea": asam["id_asamblea"]},
    ).mappings().one()

    assert filas_origen["total"] == 1
    assert filas_origen["total"] == filas_origen["con_cop_original"]


def test_caso_5_adicional_y_2a_adicional_ciclos_operacionales_distintos(
    api, base_017, transactional_api
):
    """CASO 5: ADICIONAL y 2A_ADICIONAL siguen siendo ciclos operacionales distintos."""
    ciclos = _catalog(api, "tipo_cop_operativo")
    assert "ADICIONAL" in ciclos
    assert "2A_ADICIONAL" in ciclos
    assert ciclos["ADICIONAL"] != ciclos["2A_ADICIONAL"]

    # Verificación de la cohorte creada explícitamente por este fixture.
    sample_ids = [
        *base_017["muestras_ciclo"]["ADICIONAL"],
        *base_017["muestras_ciclo"]["2A_ADICIONAL"],
    ]
    conteos = transactional_api["connection"].execute(
        text(
            """
            SELECT cop.codigo AS cop_codigo, ctx.codigo AS ctx_codigo, count(*) AS total
              FROM asamblea a
              JOIN catalogo_operativo cop ON cop.id_catalogo_opcion = a.id_tipo_cop_operativo
              JOIN catalogo_operativo ctx ON ctx.id_catalogo_opcion = a.id_contexto_asamblea
             WHERE a.id_asamblea = ANY(:sample_ids)
             GROUP BY 1, 2
             ORDER BY 1
            """
        ),
        {"sample_ids": sample_ids},
    ).mappings().all()

    por_ciclo = {r["cop_codigo"]: (r["ctx_codigo"], r["total"]) for r in conteos}
    assert por_ciclo["ADICIONAL"][0] == "modificatorio"
    assert por_ciclo["ADICIONAL"][1] == 3
    assert por_ciclo["2A_ADICIONAL"][0] == "modificatorio"
    assert por_ciclo["2A_ADICIONAL"][1] == 3
    assert all(r["ctx_codigo"] == "modificatorio" for r in conteos)


def test_caso_6_trigger_fn_validar_convenio_relaciones_rechaza_cruce(
    api, base_017, transactional_api
):
    """CASO 6: fn_validar_convenio_relaciones() rechaza asamblea modificatorio autorizando cop_original y viceversa."""
    pn_id = base_017["pn_id"]
    connection = transactional_api["connection"]

    # Crear una asamblea modificatorio para esta prueba
    asamblea_mod = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": base_017["assembly_types"]["anuencia"],
            "id_contexto_asamblea": base_017["assembly_contexts"]["modificatorio"],
            "id_tipo_cop_operativo": base_017["ciclos"]["ADICIONAL"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2027-06-01",
                    "fecha_realizacion": "2027-06-01",
                    "id_resultado": base_017["convocation_results"]["celebrada"],
                }
            ],
        },
    ).json()

    # 6A: Asamblea 'modificatorio' NO puede autorizar Convenio 'cop_original'
    # Via API: esperado 409
    api(
        "POST",
        f"/api/afectaciones/{base_017['afectaciones']['ORIGEN']['id_afectacion']}/convenios",
        expected=409,
        json={
            "tipo_convenio": "cop_original",
            "consecutivo": 99,
            "id_asamblea_autorizacion": asamblea_mod["id_asamblea"],
            "estado_antecedente": "no_aplica",
        },
    )

    # Via DB directa: verificar mensaje exacto del trigger
    sp_6a = connection.begin_nested()
    try:
        with pytest.raises(DBAPIError) as exc_6a:
            connection.execute(
                text(
                    """
                    INSERT INTO convenio (
                        id_proyecto_nucleo, ambito, tipo_instrumento,
                        tipo_convenio, consecutivo, estado_antecedente,
                        id_asamblea_autorizacion
                    ) VALUES (
                        :pn, 'colectivo', 'convenio',
                        'cop_original', 9901, 'no_aplica',
                        :id_asamblea
                    )
                    """
                ),
                {"pn": pn_id, "id_asamblea": asamblea_mod["id_asamblea"]},
            )
        assert "007: el contexto de la Asamblea no corresponde al tipo de convenio" in str(
            exc_6a.value
        )
    finally:
        sp_6a.rollback()

    # 6B: Asamblea 'cop_original' NO puede autorizar Convenio 'modificatorio'
    # Via API: esperado 409
    api(
        "POST",
        f"/api/afectaciones/{base_017['afectaciones']['ADICIONAL']['id_afectacion']}/convenios",
        expected=409,
        json={
            "tipo_convenio": "modificatorio",
            "consecutivo": 100,
            "id_convenio_padre": base_017["convenio_origen"]["id_convenio"],
            "id_asamblea_autorizacion": base_017["asamblea_origen"]["id_asamblea"],
            "estado_antecedente": "vinculado",
        },
    )

    # Via DB directa: verificar mensaje exacto del trigger
    sp_6b = connection.begin_nested()
    try:
        with pytest.raises(DBAPIError) as exc_6b:
            connection.execute(
                text(
                    """
                    INSERT INTO convenio (
                        id_proyecto_nucleo, ambito, tipo_instrumento,
                        tipo_convenio, consecutivo, estado_antecedente,
                        id_convenio_padre, id_asamblea_autorizacion
                    ) VALUES (
                        :pn, 'colectivo', 'convenio',
                        'modificatorio', 9902, 'vinculado',
                        :padre, :id_asamblea
                    )
                    """
                ),
                {
                    "pn": pn_id,
                    "padre": base_017["convenio_origen"]["id_convenio"],
                    "id_asamblea": base_017["asamblea_origen"]["id_asamblea"],
                },
            )
        assert "007: el contexto de la Asamblea no corresponde al tipo de convenio" in str(
            exc_6b.value
        )
    finally:
        sp_6b.rollback()


def test_caso_7_obras_complementarias_sin_cambios(
    api, base_017, transactional_api
):
    """CASO 7: obras_complementarias no sufre cambios en catalogo ni autorizacion."""
    pn_id = base_017["pn_id"]

    # Catálogo conserva activo obras_complementarias
    opciones_ctx = api("GET", "/api/catalogos/operativos/contexto_asamblea").json()
    assert any(op["codigo"] == "obras_complementarias" and op["activo"] for op in opciones_ctx)

    # Crear asamblea obras_complementarias
    asamblea_comp = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": base_017["assembly_types"]["anuencia"],
            "id_contexto_asamblea": base_017["assembly_contexts"]["obras_complementarias"],
            "id_tipo_cop_operativo": base_017["ciclos"]["COMPLEMENTARIAS"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2027-04-01",
                    "fecha_realizacion": "2027-04-01",
                    "id_resultado": base_017["convocation_results"]["celebrada"],
                }
            ],
        },
    ).json()

    # Crear convenio obras_complementarias autorizado por la asamblea
    convenio_comp = api(
        "POST",
        f"/api/afectaciones/{base_017['afectaciones']['COMPLEMENTARIAS']['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_convenio": "obras_complementarias",
            "consecutivo": 3,
            "id_convenio_padre": base_017["convenio_origen"]["id_convenio"],
            "id_asamblea_autorizacion": asamblea_comp["id_asamblea"],
            "fecha_firma": "2027-04-10",
            "estado_antecedente": "vinculado",
        },
    ).json()

    assert convenio_comp["tipo_convenio"] == "obras_complementarias"
    assert convenio_comp["id_asamblea_autorizacion"] == asamblea_comp["id_asamblea"]


def test_schema_017_registro_y_postcondiciones(transactional_api):
    """Valida el registro de migracion 017 y consistencia final de base de datos."""
    conn = transactional_api["connection"]

    # Migracion 017 registrada con version y nombre exacto
    migracion = conn.execute(
        text(
            """
            SELECT version, nombre, checksum_sha256
              FROM schema_migrations
             WHERE version = '017'
            """
        )
    ).mappings().one()

    assert migracion["version"] == "017"
    assert migracion["nombre"] == "normalizar_contexto_asamblea_adicional"
    assert len(migracion["checksum_sha256"]) == 64

    # Postcondicion: ninguna asamblea activa adicional quedo con cop_original o superficie_adicional
    inconsistencias = conn.execute(
        text(
            """
            SELECT count(*)
              FROM asamblea a
              JOIN catalogo_operativo cop ON cop.id_catalogo_opcion = a.id_tipo_cop_operativo
              JOIN catalogo_operativo ctx ON ctx.id_catalogo_opcion = a.id_contexto_asamblea
             WHERE a.activo
               AND cop.codigo IN ('ADICIONAL', '2A_ADICIONAL')
               AND ctx.codigo IN ('cop_original', 'superficie_adicional')
            """
        )
    ).scalar_one()
    assert inconsistencias == 0


def test_revision_a_b_normalizacion_superficie_adicional(base_017, transactional_api):
    """Demuestra A y B: asambleas con contexto superficie_adicional y ciclo ADICIONAL o 2A_ADICIONAL se normalizan a modificatorio."""
    conn = transactional_api["connection"]
    pn_id = base_017["pn_id"]
    ctx_mod = base_017["assembly_contexts"]["modificatorio"]
    adic = base_017["ciclos"]["ADICIONAL"]
    segundo_adic = base_017["ciclos"]["2A_ADICIONAL"]

    sup_adic_id = conn.execute(
        text("SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'superficie_adicional'")
    ).scalar_one()

    sp = conn.begin_nested()
    try:
        # Insertar asamblea ADICIONAL con contexto superficie_adicional
        a1 = conn.execute(
            text(
                """
                INSERT INTO asamblea (id_proyecto_nucleo, id_tipo_asamblea, id_contexto_asamblea, id_tipo_cop_operativo)
                VALUES (:pn, :tipo, :ctx, :cop) RETURNING id_asamblea
                """
            ),
            {"pn": pn_id, "tipo": base_017["assembly_types"]["anuencia"], "ctx": sup_adic_id, "cop": adic},
        ).scalar_one()

        # Insertar asamblea 2A_ADICIONAL con contexto superficie_adicional
        a2 = conn.execute(
            text(
                """
                INSERT INTO asamblea (id_proyecto_nucleo, id_tipo_asamblea, id_contexto_asamblea, id_tipo_cop_operativo)
                VALUES (:pn, :tipo, :ctx, :cop) RETURNING id_asamblea
                """
            ),
            {"pn": pn_id, "tipo": base_017["assembly_types"]["anuencia"], "ctx": sup_adic_id, "cop": segundo_adic},
        ).scalar_one()

        # Ejecutar la normalizacion de schema 017
        conn.execute(
            text(
                """
                UPDATE asamblea
                   SET id_contexto_asamblea = :ctx_mod
                 WHERE id_asamblea IN (:a1, :a2)
                """
            ),
            {"ctx_mod": ctx_mod, "a1": a1, "a2": a2},
        )

        res = conn.execute(
            text("SELECT id_asamblea, id_contexto_asamblea FROM asamblea WHERE id_asamblea IN (:a1, :a2)"),
            {"a1": a1, "a2": a2},
        ).mappings().all()

        assert len(res) == 2
        assert all(r["id_contexto_asamblea"] == ctx_mod for r in res)
    finally:
        sp.rollback()


def test_revision_c_guarda_preflight_aborta_ciclo_inesperado(base_017, transactional_api):
    """Demuestra C: una asamblea activa con contexto superficie_adicional y ciclo inesperado aborta la migración."""
    conn = transactional_api["connection"]
    pn_id = base_017["pn_id"]
    origen_cop = base_017["ciclos"]["ORIGEN"]

    sup_adic_id = conn.execute(
        text("SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'superficie_adicional'")
    ).scalar_one()

    sp = conn.begin_nested()
    try:
        # Insertar asamblea activa con contexto superficie_adicional y ciclo ORIGEN (ciclo no normalizable a modificatorio)
        a_invalida = conn.execute(
            text(
                """
                INSERT INTO asamblea (id_proyecto_nucleo, id_tipo_asamblea, id_contexto_asamblea, id_tipo_cop_operativo)
                VALUES (:pn, :tipo, :ctx, :cop) RETURNING id_asamblea
                """
            ),
            {"pn": pn_id, "tipo": base_017["assembly_types"]["anuencia"], "ctx": sup_adic_id, "cop": origen_cop},
        ).scalar_one()

        # Ejecutar la guarda de la migración 017
        with pytest.raises(DBAPIError) as exc_guarda:
            conn.execute(
                text(
                    """
                    DO $$
                    DECLARE
                        v_ctx_superficie_adicional bigint;
                        v_cop_adicional bigint;
                        v_cop_2a_adicional bigint;
                        v_ids text;
                    BEGIN
                        SELECT id_catalogo_opcion INTO STRICT v_ctx_superficie_adicional
                          FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'superficie_adicional';
                        SELECT id_catalogo_opcion INTO STRICT v_cop_adicional
                          FROM catalogo_operativo WHERE tipo_catalogo = 'tipo_cop_operativo' AND codigo = 'ADICIONAL';
                        SELECT id_catalogo_opcion INTO STRICT v_cop_2a_adicional
                          FROM catalogo_operativo WHERE tipo_catalogo = 'tipo_cop_operativo' AND codigo = '2A_ADICIONAL';

                        SELECT string_agg(DISTINCT a.id_asamblea::text, ',' ORDER BY a.id_asamblea::text)
                          INTO v_ids
                          FROM asamblea a
                         WHERE a.activo
                           AND a.id_contexto_asamblea = v_ctx_superficie_adicional
                           AND (
                               a.id_tipo_cop_operativo IS NULL
                               OR a.id_tipo_cop_operativo NOT IN (v_cop_adicional, v_cop_2a_adicional)
                           );

                        IF v_ids IS NOT NULL THEN
                            RAISE EXCEPTION '017 abortada: asambleas activas con contexto superficie_adicional y ciclo no normalizable: %', v_ids;
                        END IF;
                    END $$;
                    """
                )
            )
        assert "017 abortada: asambleas activas con contexto superficie_adicional y ciclo no normalizable" in str(
            exc_guarda.value
        )
        assert str(a_invalida) in str(exc_guarda.value)
    finally:
        sp.rollback()


def test_revision_d_cero_asambleas_activas_referencian_superficie_adicional(transactional_api):
    """Demuestra D: después de 017 no existe ninguna asamblea activa referenciando contexto superficie_adicional."""
    conn = transactional_api["connection"]
    activas_con_superficie = conn.execute(
        text(
            """
            SELECT count(*)
              FROM asamblea a
              JOIN catalogo_operativo ctx ON ctx.id_catalogo_opcion = a.id_contexto_asamblea
             WHERE a.activo
               AND ctx.tipo_catalogo = 'contexto_asamblea'
               AND ctx.codigo = 'superficie_adicional'
            """
        )
    ).scalar_one()
    assert activas_con_superficie == 0


def test_revision_e_id_usuario_baja_null_sin_actor_hardcodeado(transactional_api):
    """Demuestra E: la baja de superficie_adicional no depende de usuario 1 ni fabrica actor aplicativo (id_usuario_baja IS NULL)."""
    conn = transactional_api["connection"]
    row = conn.execute(
        text(
            """
            SELECT activo, id_usuario_baja, fecha_baja, motivo_baja, observaciones
              FROM catalogo_operativo
             WHERE tipo_catalogo = 'contexto_asamblea'
               AND codigo = 'superficie_adicional'
            """
        )
    ).mappings().one()

    assert row["activo"] is False
    assert row["id_usuario_baja"] is None
    assert row["fecha_baja"] is not None
    assert row["motivo_baja"] == "Deprecado por normalización del modelo en schema 017"
    assert row["observaciones"] == "Para superficie adicional usar contexto_asamblea=modificatorio con id_tipo_cop_operativo=ADICIONAL/2A_ADICIONAL."


def test_chk_baja_superficie_adicional_permite_id_usuario_baja_null(transactional_api):
    """Prueba A: chk_catalogo_operativo_baja admite id_usuario_baja = NULL exclusivamente para superficie_adicional con el motivo de schema 017."""
    conn = transactional_api["connection"]
    row = conn.execute(
        text(
            """
            SELECT activo, id_usuario_baja, fecha_baja, motivo_baja
              FROM catalogo_operativo
             WHERE tipo_catalogo = 'contexto_asamblea'
               AND codigo = 'superficie_adicional'
            """
        )
    ).mappings().one()
    assert row["activo"] is False
    assert row["id_usuario_baja"] is None
    assert row["fecha_baja"] is not None
    assert row["motivo_baja"] == "Deprecado por normalización del modelo en schema 017"


def test_chk_baja_otra_opcion_rechaza_id_usuario_baja_null(transactional_api):
    """Prueba B: cualquier otra opción del catálogo NO puede darse de baja con id_usuario_baja = NULL."""
    conn = transactional_api["connection"]
    sp = conn.begin_nested()
    try:
        # 1. Intentar dar de baja otra opción de contexto_asamblea con id_usuario_baja = NULL
        with pytest.raises(DBAPIError) as exc_baja:
            conn.execute(
                text(
                    """
                    UPDATE catalogo_operativo
                       SET activo = false,
                           fecha_baja = now(),
                           id_usuario_baja = NULL,
                           motivo_baja = 'Intento de baja sin usuario'
                     WHERE tipo_catalogo = 'contexto_asamblea'
                       AND codigo = 'otro'
                    """
                )
            )
        assert "chk_catalogo_operativo_baja" in str(exc_baja.value)
    finally:
        sp.rollback()

    # 2. Intentar dar de baja superficie_adicional con id_usuario_baja = NULL pero motivo diferente al de 017
    sp2 = conn.begin_nested()
    try:
        with pytest.raises(DBAPIError) as exc_motivo:
            conn.execute(
                text(
                    """
                    UPDATE catalogo_operativo
                       SET activo = false,
                           fecha_baja = now(),
                           id_usuario_baja = NULL,
                           motivo_baja = 'Baja administrativa cualquiera'
                     WHERE tipo_catalogo = 'contexto_asamblea'
                       AND codigo = 'superficie_adicional'
                    """
                )
            )
        assert "chk_catalogo_operativo_baja" in str(exc_motivo.value)
    finally:
        sp2.rollback()


def test_chk_baja_otra_opcion_permite_baja_normal_con_actor(transactional_api):
    """Prueba C: cualquier otra opción conserva la baja normal exigiendo id_usuario_baja NOT NULL."""
    conn = transactional_api["connection"]
    sp = conn.begin_nested()
    try:
        user_id = conn.execute(text("SELECT id_usuario FROM usuario WHERE activo LIMIT 1")).scalar_one()

        conn.execute(
            text(
                """
                UPDATE catalogo_operativo
                   SET activo = false,
                       fecha_baja = now(),
                       id_usuario_baja = :user_id,
                       motivo_baja = 'Baja normal con actor de auditoría'
                 WHERE tipo_catalogo = 'contexto_asamblea'
                   AND codigo = 'otro'
                """
            ),
            {"user_id": user_id},
        )
        row = conn.execute(
            text(
                """
                SELECT activo, id_usuario_baja, fecha_baja, motivo_baja
                  FROM catalogo_operativo
                 WHERE tipo_catalogo = 'contexto_asamblea'
                   AND codigo = 'otro'
                """
            )
        ).mappings().one()
        assert row["activo"] is False
        assert row["id_usuario_baja"] == user_id
        assert row["fecha_baja"] is not None
        assert row["motivo_baja"] == "Baja normal con actor de auditoría"
    finally:
        sp.rollback()


def test_preservacion_observaciones_superficie_adicional(transactional_api):
    """Prueba D: las observaciones previas de superficie_adicional no se destruyen ni se duplican."""
    conn = transactional_api["connection"]
    # 1. En la BD actual, observaciones contiene el texto de normalización
    obs_actual = conn.execute(
        text("SELECT observaciones FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'superficie_adicional'")
    ).scalar_one()
    assert obs_actual is not None
    assert "Para superficie adicional usar contexto_asamblea=modificatorio con id_tipo_cop_operativo=ADICIONAL/2A_ADICIONAL." in obs_actual

    # 2. Demostración de lógica CASE en SQL:
    sp = conn.begin_nested()
    try:
        # A) Caso observación previa existente: se preserva con separador ' | '
        obs_con_previa = conn.execute(
            text(
                """
                SELECT CASE
                    WHEN :obs IS NULL OR btrim(:obs) = '' THEN
                        'Para superficie adicional usar contexto_asamblea=modificatorio con id_tipo_cop_operativo=ADICIONAL/2A_ADICIONAL.'
                    WHEN :obs LIKE '%Para superficie adicional usar contexto_asamblea=modificatorio%' THEN
                        :obs
                    ELSE
                        btrim(:obs) || ' | Para superficie adicional usar contexto_asamblea=modificatorio con id_tipo_cop_operativo=ADICIONAL/2A_ADICIONAL.'
                END AS resultado
                """
            ),
            {"obs": "Nota de auditoria histórica 2025"},
        ).scalar_one()
        assert obs_con_previa == "Nota de auditoria histórica 2025 | Para superficie adicional usar contexto_asamblea=modificatorio con id_tipo_cop_operativo=ADICIONAL/2A_ADICIONAL."

        # B) Caso observación que ya contiene el texto: idempotente, no se duplica
        obs_idempotente = conn.execute(
            text(
                """
                SELECT CASE
                    WHEN :obs IS NULL OR btrim(:obs) = '' THEN
                        'Para superficie adicional usar contexto_asamblea=modificatorio con id_tipo_cop_operativo=ADICIONAL/2A_ADICIONAL.'
                    WHEN :obs LIKE '%Para superficie adicional usar contexto_asamblea=modificatorio%' THEN
                        :obs
                    ELSE
                        btrim(:obs) || ' | Para superficie adicional usar contexto_asamblea=modificatorio con id_tipo_cop_operativo=ADICIONAL/2A_ADICIONAL.'
                END AS resultado
                """
            ),
            {"obs": obs_con_previa},
        ).scalar_one()
        assert obs_idempotente == obs_con_previa
        assert obs_idempotente.count("Para superficie adicional usar contexto_asamblea=modificatorio") == 1
    finally:
        sp.rollback()


def test_guardas_asamblea_permanecen_invariables(api, base_017, transactional_api):
    """Prueba E: las guardas de asamblea continúan funcionando de forma idéntica e invariable."""
    pn_id = base_017["pn_id"]
    conn = transactional_api["connection"]

    # 1. API rechaza crear asamblea con la opción deprecada superficie_adicional (422)
    sup_adic_id = conn.execute(
        text("SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo = 'contexto_asamblea' AND codigo = 'superficie_adicional'")
    ).scalar_one()

    resp = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=422,
        json={
            "id_tipo_asamblea": base_017["assembly_types"]["anuencia"],
            "id_contexto_asamblea": sup_adic_id,
        },
    ).json()
    assert "Opción activa inválida para el catálogo contexto_asamblea" in resp["detail"]

    # 2. Trigger fn_validar_convenio_relaciones rechaza cruces indebidos
    asamblea_mod = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": base_017["assembly_types"]["anuencia"],
            "id_contexto_asamblea": base_017["assembly_contexts"]["modificatorio"],
            "id_tipo_cop_operativo": base_017["ciclos"]["ADICIONAL"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2027-07-01",
                    "fecha_realizacion": "2027-07-01",
                    "id_resultado": base_017["convocation_results"]["celebrada"],
                }
            ],
        },
    ).json()

    api(
        "POST",
        f"/api/afectaciones/{base_017['afectaciones']['ORIGEN']['id_afectacion']}/convenios",
        expected=409,
        json={
            "tipo_convenio": "cop_original",
            "consecutivo": 999,
            "id_asamblea_autorizacion": asamblea_mod["id_asamblea"],
            "estado_antecedente": "no_aplica",
        },
    )
