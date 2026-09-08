"""Regresiones API para la migración 007 y cierre funcional del Bloque 5 de convenios."""

import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import auth, models
from app.database import SessionLocal
from app.main import app
from .test_excel_closure_002 import _catalog, _isolated_pn


@pytest.fixture(scope="module")
def api():
    """Cliente QA autenticado con RBAC de administrador."""
    session = SessionLocal()
    admin = session.query(models.Usuario).filter(
        models.Usuario.rol == "admin", models.Usuario.activo.is_(True)
    ).first()
    assert admin is not None

    for wrapper in app.routes:
        router = getattr(wrapper, "original_router", None)
        if router is None:
            continue
        for route in router.routes:
            for dependency in route.dependant.dependencies:
                if isinstance(dependency.call, auth.RoleChecker):
                    app.dependency_overrides[dependency.call] = lambda admin=admin: admin

    with TestClient(app, raise_server_exceptions=False) as client:
        def request(method: str, path: str, *, expected: int = 200, **kwargs):
            response = client.request(method, path, **kwargs)
            assert response.status_code == expected, f"[{method} {path}] Status {response.status_code}: {response.text}"
            return response

        yield request

    app.dependency_overrides.clear()
    session.close()


@pytest.fixture(scope="module")
def target_domain(api):
    entidad = api("GET", "/api/catalogos/entidades").json()[0]
    municipio = api(
        "GET", f"/api/catalogos/municipios?id_entidad={entidad['id_entidad']}"
    ).json()[0]
    return {"municipality": municipio}


def test_007_precision_superficie_siete_decimales(api, target_domain):
    """Verifica que la precisión NUMERIC(15,7) se preserva sin redondeo ni truncamiento."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]

    # 1. Crear afectación con 7 decimales exactos
    sup_preliminar = "1.1234567"
    sup_afectada = "2.7654321"
    afectacion1 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "individual",
            "superficie_preliminar_ha": sup_preliminar,
            "superficie_afectada_ha": sup_afectada,
        },
    ).json()

    assert Decimal(str(afectacion1["superficie_preliminar_ha"])) == Decimal(sup_preliminar)
    assert Decimal(str(afectacion1["superficie_afectada_ha"])) == Decimal(sup_afectada)

    # 2. Crear convenio sobre esa afectación con superficie_ha de 7 decimales
    sup_convenio = "3.9876543"
    convenio = api(
        "POST",
        f"/api/afectaciones/{afectacion1['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "superficie_ha": sup_convenio,
            "efecto_monto": "pendiente",
            "estado_antecedente": "no_aplica",
        },
    ).json()

    assert Decimal(str(convenio["superficie_ha"])) == Decimal(sup_convenio)
    conv_id = convenio["id_convenio"]

    # 3. Consultar GET /convenios/{id}/afectaciones y verificar relación principal
    afectaciones_conv = api("GET", f"/api/convenios/{conv_id}/afectaciones").json()
    assert len(afectaciones_conv) == 1
    assert afectaciones_conv[0]["rol"] == "principal"
    assert afectaciones_conv[0]["efecto_superficie"] == "pendiente"
    assert afectaciones_conv[0]["superficie_impacto_ha"] is None

    # 4. Crear afectación 2 y asociarla con efecto y superficie de 7 decimales
    afectacion2 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "superficie_afectada_ha": "0.5555555"},
    ).json()

    ca_adicional = api(
        "POST",
        f"/api/convenios/{conv_id}/afectaciones",
        expected=201,
        json={
            "id_afectacion": afectacion2["id_afectacion"],
            "efecto_superficie": "adicion",
            "superficie_impacto_ha": "0.5555555",
        },
    ).json()
    assert ca_adicional["rol"] == "adicional"
    assert ca_adicional["efecto_superficie"] == "adicion"
    assert Decimal(str(ca_adicional["superficie_impacto_ha"])) == Decimal("0.5555555")

    # 5. Modificar vía PATCH /convenio-afectaciones/{id} con 7 decimales
    ca_id = ca_adicional["id_convenio_afectacion"]
    ca_actualizado = api(
        "PATCH",
        f"/api/convenio-afectaciones/{ca_id}",
        expected=200,
        json={
            "efecto_superficie": "sustitucion",
            "superficie_impacto_ha": "0.8888888",
        },
    ).json()
    assert ca_actualizado["efecto_superficie"] == "sustitucion"
    assert Decimal(str(ca_actualizado["superficie_impacto_ha"])) == Decimal("0.8888888")

    # Re-consultar lista completa de afectaciones
    afectaciones_conv2 = api("GET", f"/api/convenios/{conv_id}/afectaciones").json()
    assert len(afectaciones_conv2) == 2


def test_007_efectos_economicos_y_validaciones(api, target_domain):
    """Verifica reglas de consistencia para efecto_monto e impactos económicos."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]

    afectacion = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual"},
    ).json()
    af_id = afectacion["id_afectacion"]

    # 1. Rechazo: pendiente con impacto no nulo
    api(
        "POST",
        f"/api/afectaciones/{af_id}/convenios",
        expected=422,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "monto_90": "50000.00",
            "efecto_monto": "pendiente",
            "monto_90_impacto": "50000.00",
            "estado_antecedente": "no_aplica",
        },
    )

    # 2. Rechazo: adicion con impacto negativo o cero
    api(
        "POST",
        f"/api/afectaciones/{af_id}/convenios",
        expected=422,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 2,
            "efecto_monto": "adicion",
            "monto_90_impacto": "0.00",
            "estado_antecedente": "no_aplica",
        },
    )

    # 3. Rechazo: sin_cambio con impacto distinto de 0
    api(
        "POST",
        f"/api/afectaciones/{af_id}/convenios",
        expected=422,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 3,
            "efecto_monto": "sin_cambio",
            "monto_90_impacto": "100.00",
            "estado_antecedente": "no_aplica",
        },
    )

    # 4. Creación válida con sin_cambio (impacto == 0)
    conv = api(
        "POST",
        f"/api/afectaciones/{af_id}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "monto_90": "50000.00",
            "monto_100": "60000.00",
            "efecto_monto": "sin_cambio",
            "monto_90_impacto": "0.00",
            "monto_100_impacto": "0.00",
            "estado_antecedente": "no_aplica",
        },
    ).json()
    assert conv["efecto_monto"] == "sin_cambio"
    assert Decimal(str(conv["monto_90_impacto"])) == Decimal("0.00")

    # 5. Actualización vía PATCH a adicion con impacto positivo
    conv_updated = api(
        "PATCH",
        f"/api/convenios/{conv['id_convenio']}",
        expected=200,
        json={
            "efecto_monto": "adicion",
            "monto_90_impacto": "15000.00",
            "monto_100_impacto": "20000.00",
        },
    ).json()
    assert conv_updated["efecto_monto"] == "adicion"
    assert Decimal(str(conv_updated["monto_90_impacto"])) == Decimal("15000.00")
    assert Decimal(str(conv_updated["monto_100_impacto"])) == Decimal("20000.00")


def test_007_linaje_y_estados_antecedente(api, target_domain):
    """Verifica que instrumentos derivados admitan estados de antecedente sin padre forzado."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]

    afectacion = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "colectivo"},
    ).json()
    af_id = afectacion["id_afectacion"]

    # 1. COP original: estado_antecedente sólo puede ser no_aplica
    api(
        "POST",
        f"/api/afectaciones/{af_id}/convenios",
        expected=422,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "efecto_monto": "pendiente",
            "estado_antecedente": "pendiente_identificar",
        },
    )

    cop = api(
        "POST",
        f"/api/afectaciones/{af_id}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "efecto_monto": "pendiente",
            "estado_antecedente": "no_aplica",
        },
    ).json()
    cop_id = cop["id_convenio"]
    assert cop["estado_antecedente"] == "no_aplica"

    # 2. Derivado sin padre: pendiente_identificar aceptado con 201 (no inventa padre ficticio)
    mod_pendiente = api(
        "POST",
        f"/api/afectaciones/{af_id}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "modificatorio",
            "consecutivo": 2,
            "efecto_monto": "pendiente",
            "estado_antecedente": "pendiente_identificar",
        },
    ).json()
    assert mod_pendiente["id_convenio_padre"] is None
    assert mod_pendiente["estado_antecedente"] == "pendiente_identificar"

    # 3. Derivado sin padre: referido_sin_soporte aceptado con 201
    mod_referido = api(
        "POST",
        f"/api/afectaciones/{af_id}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "superficie_adicional",
            "consecutivo": 3,
            "efecto_monto": "pendiente",
            "estado_antecedente": "referido_sin_soporte",
        },
    ).json()
    assert mod_referido["id_convenio_padre"] is None
    assert mod_referido["estado_antecedente"] == "referido_sin_soporte"

    # 4. Derivado sin padre pero con antecedente vinculado -> rechazo 422
    api(
        "POST",
        f"/api/afectaciones/{af_id}/convenios",
        expected=422,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "modificatorio",
            "consecutivo": 4,
            "efecto_monto": "pendiente",
            "estado_antecedente": "vinculado",
        },
    )

    # 5. Derivado con padre real y vinculado -> aceptado con 201
    mod_vinculado = api(
        "POST",
        f"/api/afectaciones/{af_id}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "modificatorio",
            "consecutivo": 5,
            "id_convenio_padre": cop_id,
            "efecto_monto": "pendiente",
            "estado_antecedente": "vinculado",
        },
    ).json()
    assert mod_vinculado["id_convenio_padre"] == cop_id
    assert mod_vinculado["estado_antecedente"] == "vinculado"

    # 6. Derivado con padre pero antecedente no_aplica -> rechazo 422
    api(
        "POST",
        f"/api/afectaciones/{af_id}/convenios",
        expected=422,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "modificatorio",
            "consecutivo": 6,
            "id_convenio_padre": cop_id,
            "efecto_monto": "pendiente",
            "estado_antecedente": "no_aplica",
        },
    )


def test_007_validaciones_efecto_superficie(api, target_domain):
    """Verifica validaciones de consistencia para efecto_superficie en convenio-afectación."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]

    af1 = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201,
              json={"tipo_afectacion": "individual"}).json()
    af2 = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201,
              json={"tipo_afectacion": "individual"}).json()

    conv = api("POST", f"/api/afectaciones/{af1['id_afectacion']}/convenios", expected=201,
               json={"tipo_instrumento": "convenio", "tipo_convenio": "cop_original",
                     "consecutivo": 1, "efecto_monto": "pendiente", "estado_antecedente": "no_aplica"}).json()
    conv_id = conv["id_convenio"]

    # Rechazo: pendiente con superficie definida
    api("POST", f"/api/convenios/{conv_id}/afectaciones", expected=422,
        json={"id_afectacion": af2["id_afectacion"], "efecto_superficie": "pendiente",
              "superficie_impacto_ha": "1.0000000"})

    # Rechazo: sin_cambio con superficie distinta de 0
    api("POST", f"/api/convenios/{conv_id}/afectaciones", expected=422,
        json={"id_afectacion": af2["id_afectacion"], "efecto_superficie": "sin_cambio",
              "superficie_impacto_ha": "0.5000000"})

    # Rechazo: adicion con superficie <= 0 o None
    api("POST", f"/api/convenios/{conv_id}/afectaciones", expected=422,
        json={"id_afectacion": af2["id_afectacion"], "efecto_superficie": "adicion",
              "superficie_impacto_ha": "0.0000000"})

    # Creación válida adicion
    ca2 = api("POST", f"/api/convenios/{conv_id}/afectaciones", expected=201,
              json={"id_afectacion": af2["id_afectacion"], "efecto_superficie": "adicion",
                    "superficie_impacto_ha": "0.7500000"}).json()
    assert Decimal(str(ca2["superficie_impacto_ha"])) == Decimal("0.7500000")

    # PATCH a sin_cambio
    ca2_patch = api("PATCH", f"/api/convenio-afectaciones/{ca2['id_convenio_afectacion']}", expected=200,
                    json={"efecto_superficie": "sin_cambio", "superficie_impacto_ha": "0.0000000"}).json()
    assert ca2_patch["efecto_superficie"] == "sin_cambio"
    assert Decimal(str(ca2_patch["superficie_impacto_ha"])) == Decimal("0.0000000")


def test_007_reporting_vistas_convenios_api(api, target_domain):
    """Verifica que los endpoints de reporting consulten las vistas 007 con precisión y aislamiento."""
    project, pn = _isolated_pn(api, target_domain)
    project_id = project["id_proyecto"]
    pn_id = pn["id_proyecto_nucleo"]

    afectacion = api("POST", f"/api/proyecto-nucleo/{pn_id}/afectaciones", expected=201,
                     json={"tipo_afectacion": "individual"}).json()
    af_id = afectacion["id_afectacion"]

    # Convenio con valores declarados explícitos
    conv = api("POST", f"/api/afectaciones/{af_id}/convenios", expected=201,
               json={
                   "tipo_instrumento": "convenio",
                   "tipo_convenio": "cop_original",
                   "consecutivo": 1,
                   "monto_90": "125000.00",
                   "monto_100": "150000.00",
                   "monto_bdt": "10000.00",
                   "superficie_ha": "4.5678901",
                   "efecto_monto": "adicion",
                   "monto_90_impacto": "125000.00",
                   "monto_100_impacto": "150000.00",
                   "monto_bdt_impacto": "10000.00",
                   "estado_antecedente": "no_aplica",
               }).json()
    conv_id = conv["id_convenio"]

    # 1. Endpoint /reportes/convenios/valores-declarados
    vd_rows = api("GET", f"/api/reportes/convenios/valores-declarados?id_proyecto={project_id}").json()
    assert len(vd_rows) >= 4  # superficie_declarada, monto_90, monto_100, monto_bdt
    vd_by_concept = {row["concepto"]: row for row in vd_rows if row["id_convenio"] == conv_id}
    assert "superficie_declarada" in vd_by_concept
    assert Decimal(str(vd_by_concept["superficie_declarada"]["valor_declarado"])) == Decimal("4.5678901")
    assert vd_by_concept["superficie_declarada"]["unidad"] == "ha"
    assert Decimal(str(vd_by_concept["monto_90_declarado"]["valor_declarado"])) == Decimal("125000.00")
    assert vd_by_concept["monto_90_declarado"]["unidad"] == "MXN"

    # 2. Endpoint /reportes/convenios/impactos
    imp_rows = api("GET", f"/api/reportes/convenios/impactos?id_proyecto={project_id}").json()
    assert len(imp_rows) >= 4
    imp_by_key = {row["clave_impacto"]: row for row in imp_rows if row["id_convenio"] == conv_id}
    # Rama de superficie: clave empieza con superficie:
    sup_impact = next(r for r in imp_by_key.values() if r["concepto"] == "superficie")
    assert sup_impact["unidad"] == "ha"
    assert sup_impact["efecto"] == "pendiente"
    assert sup_impact["pendiente"] is True
    # NULL pendiente nunca se fabrica como cero:
    assert sup_impact["valor_impacto"] is None

    # Rama económica: montos discriminados sin unirse en N:M
    m90_impact = imp_by_key.get(f"monto:{conv_id}:monto_90")
    assert m90_impact is not None
    assert Decimal(str(m90_impact["valor_impacto"])) == Decimal("125000.00")
    assert m90_impact["pendiente"] is False

    # 3. Endpoint /reportes/convenios/cobertura-impactos
    cob_rows = api("GET", f"/api/reportes/convenios/cobertura-impactos?id_proyecto={project_id}").json()
    assert len(cob_rows) > 0
    conceptos_cob = {r["concepto"]: r for r in cob_rows}
    assert "superficie" in conceptos_cob
    assert conceptos_cob["superficie"]["universo"] >= 1
    assert conceptos_cob["superficie"]["pendientes"] >= 1

    # 4. Endpoint /reportes/convenios/impactos-periodo
    # Como el instrumento no tiene firma acreditada por documento, impactos-periodo no lo incluye (excluye pendientes y sin firma)
    periodo_rows = api("GET", f"/api/reportes/convenios/impactos-periodo?id_proyecto={project_id}").json()
    assert isinstance(periodo_rows, list)


def test_007_firma_acreditada_y_periodo_reporting(api, target_domain):
    """Acredita firma colectiva conforme a fn_convenio_firma_acreditada_007 y valida que fluya al reporte por periodo."""
    project, pn = _isolated_pn(api, target_domain)
    project_id = project["id_proyecto"]
    pn_id = pn["id_proyecto_nucleo"]

    session = SessionLocal()
    try:
        pn_db = session.query(models.ProyectoNucleo).filter_by(id_proyecto_nucleo=pn_id).first()
        nucleo_id = pn_db.id_nucleo

        # 1. Crear persona para ORV
        persona = api(
            "POST",
            f"/api/proyectos/{project_id}/personas",
            expected=201,
            json={"nombre": "Comisariado", "apellido_paterno": "Firmante", "origen_registro": "qa"},
        ).json()
        persona_id = persona["id_persona"]

        # 2. Crear ORV con integrante vigente
        cargo_orv = next(iter(_catalog(api, "cargo_orv").values()))
        organo_orv = next(iter(_catalog(api, "organo_orv").values()))
        calidad_integrante = next(iter(_catalog(api, "calidad_integrante_orv").values()))
        orv = api(
            "POST",
            f"/api/proyecto-nucleo/{pn_id}/orv",
            expected=201,
            json={
                "inicio_vigencia": "2026-01-01",
                "fin_vigencia": "2028-12-31",
            },
        ).json()
        orv_id = orv["id_orv"]

        api(
            "POST",
            f"/api/orv/{orv_id}/integrantes",
            expected=201,
            json={
                "id_persona": persona_id,
                "id_organo": organo_orv,
                "id_cargo": cargo_orv,
                "id_calidad": calidad_integrante,
                "fecha_inicio": "2026-01-01",
                "fecha_fin": "2028-12-31",
            },
        )

        # 3. Afectación colectiva y Convenio con fecha de firma
        afectacion = api(
            "POST",
            f"/api/proyecto-nucleo/{pn_id}/afectaciones",
            expected=201,
            json={"tipo_afectacion": "colectivo"},
        ).json()

        conv = api(
            "POST",
            f"/api/afectaciones/{afectacion['id_afectacion']}/convenios",
            expected=201,
            json={
                "tipo_instrumento": "convenio",
                "tipo_convenio": "cop_original",
                "consecutivo": 1,
                "fecha_firma": "2026-09-01",
                "monto_100": "250000.00",
                "efecto_monto": "adicion",
                "monto_100_impacto": "250000.00",
                "estado_antecedente": "no_aplica",
            },
        ).json()
        conv_id = conv["id_convenio"]

        # 4. Compareciente firmante
        calidad = next(iter(_catalog(api, "calidad_compareciente_convenio").values()))
        comp = api(
            "POST",
            f"/api/convenios/{conv_id}/comparecientes",
            expected=201,
            json={
                "id_persona": persona_id,
                "nombre_en_instrumento": "Comisariado Firmante",
                "id_tipo_calidad": calidad,
                "es_firmante": True,
                "requiere_revision": False,
            },
        ).json()

        # 5. Crear documento y requisito documental 'col_convenio_firmado' en estado 'disponible'
        session.execute(text("SELECT set_config('app.current_user_id', '1', true)"))
        doc = models.Documento(
            tipo_documento="convenio",
            estado="disponible",
            titulo="convenio_col_firmado.pdf",
            creado_por=1,
        )
        session.add(doc)
        session.flush()

        req_def = session.query(models.RequisitoDocumental).filter_by(codigo="col_convenio_firmado", activo=True).first()
        estado_disp = session.query(models.CatalogoOperativo).filter_by(
            tipo_catalogo="estado_requisito_documental", codigo="disponible", activo=True
        ).first()

        exp_req = session.query(models.ExpedienteRequisito).filter_by(entidad_tipo="convenio", entidad_id=conv_id).first()
        if exp_req is None:
            exp_req = models.ExpedienteRequisito(
                id_proyecto_nucleo=pn_id,
                id_requisito=req_def.id_requisito,
                id_estado=estado_disp.id_catalogo_opcion,
                id_documento=doc.id_documento,
                entidad_tipo="convenio",
                entidad_id=conv_id,
                activo=True,
                creado_por=1,
            )
            session.add(exp_req)
        else:
            exp_req.id_estado = estado_disp.id_catalogo_opcion
            exp_req.id_documento = doc.id_documento
            exp_req.activo = True
        session.commit()

        # 6. Consultar /reportes/convenios/valores-declarados y verificar firma_acreditada
        v_rows = api("GET", f"/api/reportes/convenios/valores-declarados?id_convenio={conv_id}").json()
        assert len(v_rows) > 0
        assert all(r["firma_acreditada"] is True for r in v_rows)

        # 7. Consultar /reportes/convenios/impactos y verificar firma_acreditada y fecha_efecto
        imp_rows = api("GET", f"/api/reportes/convenios/impactos?id_convenio={conv_id}").json()
        monto_imp = next(r for r in imp_rows if r["clave_impacto"] == f"monto:{conv_id}:monto_100")
        assert monto_imp["firma_acreditada"] is True
        assert monto_imp["fecha_efecto"] == "2026-09-01"

        # 8. Consultar /reportes/convenios/impactos-periodo
        per_rows = api("GET", f"/api/reportes/convenios/impactos-periodo?id_proyecto={project_id}&anio=2026&mes=9").json()
        assert len(per_rows) >= 1
        p_m100 = next(r for r in per_rows if r["concepto"] == "monto_100")
        assert Decimal(str(p_m100["valor_impacto"])) == Decimal("250000.00")
        assert p_m100["cantidad"] == 1
    finally:
        session.close()


def test_007_reporting_rbac_aislamiento(api, target_domain):
    """Verifica que los endpoints de reporting filtren y protejan proyectos no autorizados."""
    from datetime import datetime, timezone
    project_a, pn_a = _isolated_pn(api, target_domain)
    project_b, pn_b = _isolated_pn(api, target_domain)
    id_a = project_a["id_proyecto"]
    id_b = project_b["id_proyecto"]

    session = SessionLocal()
    try:
        session.execute(text("SELECT set_config('app.current_user_id', '1', true)"))
        user_vis = models.Usuario(
            nombre="Visualizador",
            apellido_paterno="Aislado",
            correo=f"vis-{uuid.uuid4().hex[:8]}@qa.test",
            contrasena_hash="fake",
            rol="visualizador",
            activo=True,
            fecha_alta=datetime.now(timezone.utc),
        )
        session.add(user_vis)
        session.flush()

        up = models.UsuarioProyecto(
            id_usuario=user_vis.id_usuario,
            id_proyecto=id_a,
            asignado_por=1,
            activo=True,
            creado_por=1,
        )
        session.add(up)
        session.commit()
        session.refresh(user_vis)
        session.expunge(user_vis)

        for wrapper in app.routes:
            router = getattr(wrapper, "original_router", None)
            if router:
                for route in router.routes:
                    for dependency in route.dependant.dependencies:
                        if isinstance(dependency.call, auth.RoleChecker):
                            app.dependency_overrides[dependency.call] = lambda u=user_vis: u

        with TestClient(app, raise_server_exceptions=False) as client:
            # Acceso a proyecto B no autorizado -> 403
            res = client.get(f"/api/reportes/convenios/impactos?id_proyecto={id_b}")
            assert res.status_code == 403

            # Acceso a proyecto A autorizado -> 200
            res_a = client.get(f"/api/reportes/convenios/impactos?id_proyecto={id_a}")
            assert res_a.status_code == 200

            # Consulta sin id_proyecto: no debe incluir datos del proyecto B
            res_all = client.get("/api/reportes/convenios/impactos")
            assert res_all.status_code == 200
            for item in res_all.json():
                assert item["id_proyecto"] != id_b
    finally:
        app.dependency_overrides.clear()
        session.close()
