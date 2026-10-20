"""Synthetic contract tests; run only in convenio_report_compose.yml (tmpfs)."""

from decimal import Decimal
import json
import os
from pathlib import Path
import uuid

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError as JsonSchemaValidationError
from pydantic import ValidationError
from sqlalchemy import event, text

from app import auth, models, schemas
from app.main import app
from app.services import convenio_reports as service
from app.services.common import mark_inactive, set_audit_context


def validate_contract(payload, name, *, openapi=None):
    api = app.openapi() if openapi is None else openapi
    assert api["openapi"].startswith("3.1."), "Select the JSON Schema dialect explicitly"
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": f"#/components/schemas/{name}",
        "components": api["components"],
    }
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)


def contract_documents():
    return Path(os.getenv("REPORT_CONTRACT_DOCS", Path(__file__).resolve().parents[2] / "docs"))


@pytest.mark.parametrize("value,expected", [
    ("0E-7", "0.0000000"), ("0", "0"), (None, None),
    ("12.1234567", "12.1234567"), ("-0.0000001", "-0.0000001"),
    ("1E-35", "0." + "0" * 34 + "1"),
    ("123456789012345678901234567890.1234567", "123456789012345678901234567890.1234567"),
])
def test_decimal_json_real_y_openapi(value, expected):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    model = schemas.ReporteGeneralConveniosResponse.model_validate(json.loads(
        (contract_documents() / "examples/reporte_general_convenios.json").read_text()
    ))
    surface = None if value is None else Decimal(value)
    row = model.individuales[0]
    row.superficie_declarada_m2 = surface
    row.superficie_unidades.superficie_m2 = surface
    row.superficie_unidades.subtotal_conocido_m2 = surface
    row.afectaciones[0].superficie_impacto_m2 = surface
    row.unidades[0].superficie_afectada_m2 = surface
    assert json.loads(model.model_dump_json())["individuales"][0]["superficie_declarada_m2"] == expected
    assert row.superficie_declarada_m2 is None or isinstance(row.superficie_declarada_m2, Decimal)

    api = FastAPI()
    @api.get("/report", response_model=schemas.ReporteGeneralConveniosResponse)
    def report():
        return model
    response = TestClient(api).get("/report")
    assert response.status_code == 200
    payload = response.json()
    item = payload["individuales"][0]
    assert item["superficie_declarada_m2"] == expected
    assert item["superficie_unidades"]["subtotal_conocido_m2"] == expected
    assert item["afectaciones"][0]["superficie_impacto_m2"] == expected
    assert item["unidades"][0]["superficie_afectada_m2"] == expected
    assert expected is None or isinstance(item["superficie_declarada_m2"], str)
    validate_contract(payload, "ReporteGeneralConveniosResponse")


@pytest.mark.parametrize("value,expected", [
    ("0E-7", "0.00"), (None, None), ("12", "12.00"),
    ("-12.30", "-12.30"), ("9999999999999999.99", "9999999999999999.99"),
])
def test_importes_fijos_exactos(value, expected):
    from pydantic import TypeAdapter
    adapter = TypeAdapter(schemas.ImporteConvenioReporte | None)
    money = adapter.validate_python(None if value is None else Decimal(value))
    assert json.loads(adapter.dump_json(money)) == expected
    sample = json.loads((contract_documents() / "examples/reporte_general_convenios.json").read_text())
    sample["individuales"][0]["monto_total_90"] = money
    sample["individuales"][0]["monto_total_100"] = money
    payload = json.loads(schemas.ReporteGeneralConveniosResponse.model_validate(sample).model_dump_json())
    assert payload["individuales"][0]["monto_total_90"] == expected
    assert payload["individuales"][0]["monto_total_100"] == expected
    validate_contract(payload, "ReporteGeneralConveniosResponse")
    # A non-cent amount must fail validation, never round silently.
    with pytest.raises(ValidationError):
        adapter.validate_python(Decimal("12.345"))


def test_documentos_publicados_validan_con_openapi_generado():
    docs = contract_documents()
    sample = json.loads((docs / "examples/reporte_general_convenios.json").read_text())
    published = json.loads((docs / "openapi.json").read_text())
    generated = app.openapi()
    validate_contract(sample, "ReporteGeneralConveniosResponse")
    validate_contract(sample, "ReporteGeneralConveniosResponse", openapi=published)
    # Both the declared response and every referenced schema must be current.
    for path, operations in generated["paths"].items():
        if "/reportes/convenios/general" in path:
            assert published["paths"][path] == operations
    for name, schema in generated["components"]["schemas"].items():
        if name.endswith(("ConvenioReporte", "ConveniosReporte", "ConveniosResponse", "ConveniosReporteResponse", "GeneralReporte", "BaseReporte", "ReporteDetalle")):
            assert published["components"]["schemas"][name] == schema
    assert "0E-7" not in json.dumps(sample)
    # Do not accidentally "fix" serialization by admitting exponent strings.
    sample["individuales"][0]["superficie_declarada_m2"] = "0E-7"
    with pytest.raises(JsonSchemaValidationError):
        validate_contract(sample, "ReporteGeneralConveniosResponse")


def test_respuesta_real_completa_valida_con_openapi(report_env):
    data = full(report_env)
    validate_contract(data, "ReporteGeneralConveniosResponse")
    zero = next(d for r in data["colectivos"] for d in r["destinos"] if d["codigo"] == "canal")
    assert zero["superficie"]["subtotal_conocido_m2"] == "0.0000000"
    assert all(isinstance(r["monto_total_100"], str) or r["monto_total_100"] is None
               for r in data["individuales"] + data["colectivos"])


def test_access_conserva_carga_anterior_por_defecto(report_env):
    from sqlalchemy import inspect
    from sqlalchemy.exc import InvalidRequestError
    from app.services.access import require_project_access
    with report_env["factory"]() as db:
        project = require_project_access(db, report_env["admin"], report_env["project_id"])
        assert "nucleos" not in inspect(project).unloaded
        assert len(project.nucleos) == 2
    with report_env["factory"]() as db:
        project = require_project_access(db, report_env["admin"], report_env["project_id"], load_details=False)
        with pytest.raises(InvalidRequestError):
            _ = project.nucleos


@pytest.fixture(scope="module")
def report_env(transactional_api):
    factory = transactional_api["session_factory"]
    with factory() as db:
        assert db.execute(text("SELECT current_database(),current_setting('cluster_name')")).one() == (
            "software_pa_test", "convenio-report-disposable",
        ), "Se requiere la instancia local desechable de convenio_report_compose.yml"
        admin = db.query(models.Usuario).filter_by(rol="admin", activo=True).first()
        db.expunge(admin)

    def report_db():
        with factory() as db:
            yield db

    previous = app.dependency_overrides.get(service.get_report_db)
    app.dependency_overrides[service.get_report_db] = report_db
    api = transactional_api["request"]
    catalogs = {}
    for kind in ("tipo_tenencia", "tipo_tierra", "destino_superficie", "tipo_titularidad_unidad",
                 "tipo_cop_operativo", "tipo_asamblea", "resultado_convocatoria", "tipo_evento_ran"):
        catalogs[kind] = {r["codigo"]: r["id_catalogo_opcion"] for r in api("GET", f"/api/catalogos/operativos/{kind}").json()}

    def create(path, **data):
        return api("POST", path, expected=201, json=data).json()

    project = create("/api/proyectos", clave_proyecto="REP-" + uuid.uuid4().hex[:10], nombre_proyecto="Reporte sintético")
    pid = project["id_proyecto"]
    pns = []
    for municipality in (1, 2):
        n = create("/api/nucleos", id_municipio=municipality, nombre_nucleo="Núcleo " + uuid.uuid4().hex,
                   id_tipo_tenencia=catalogs["tipo_tenencia"]["ejido"])
        pns.append(create(f"/api/proyectos/{pid}/nucleos", id_nucleo=n["id_nucleo"])["id_proyecto_nucleo"])

    def affect(pn, scope, cop="ORIGEN", surface=None):
        return create(f"/api/proyecto-nucleo/{pn}/afectaciones", tipo_afectacion=scope,
                      id_tipo_cop_operativo=catalogs["tipo_cop_operativo"][cop] if cop else None,
                      superficie_afectada_ha=surface)["id_afectacion"]

    def unit(pn, aid, scope, surface, dest, parcel=None):
        u = create(f"/api/proyecto-nucleo/{pn}/unidades-agrarias",
                   id_tipo_tierra=catalogs["tipo_tierra"]["parcelada" if scope == "individual" else "uso_comun"],
                   id_tipo_titularidad=catalogs["tipo_titularidad_unidad"]["persona" if parcel else "nucleo_agrario"],
                   id_destino_superficie=catalogs["destino_superficie"][dest] if dest else None,
                   id_parcela=parcel, referencia_alfanumerica=uuid.uuid4().hex)
        link = create(f"/api/afectaciones/{aid}/unidades-agrarias", id_unidad_agraria=u["id_unidad_agraria"], superficie_afectada_ha=surface)
        return u, link

    def agreement(aid, **data):
        return create(f"/api/afectaciones/{aid}/convenios", tipo_convenio=data.pop("tipo_convenio", "cop_original"), **data)

    parcels = [create(f"/api/proyecto-nucleo/{pns[0]}/parcelas", tipo_parcela="individual", no_parcela=p)
               for p in ("0007", "P-02")]
    ia = affect(pns[0], "individual", surface="0.0000001")
    iu, _ = unit(pns[0], ia, "individual", "0.0000001", "parcela_ejidal", parcels[0]["id_parcela"])
    unit(pns[0], ia, "individual", "0", "parcela_ejidal", parcels[1]["id_parcela"])
    individual = agreement(ia, monto_90="90.01", monto_100="100.02", superficie_ha="0.1234567", fecha_firma="2026-01-01")
    extra = affect(pns[0], "individual", cop=None)
    create(f"/api/afectaciones/{extra}/unidades-agrarias", id_unidad_agraria=iu["id_unidad_agraria"], superficie_afectada_ha=None)
    create(f"/api/convenios/{individual['id_convenio']}/afectaciones", id_afectacion=extra,
           efecto_superficie="sustitucion", superficie_impacto_ha="-0.0000001")
    modification = agreement(ia, tipo_convenio="modificatorio", id_convenio_padre=individual["id_convenio"], estado_antecedente="vinculado")
    empty_individual = agreement(affect(pns[1], "individual"), monto_100="0", consecutivo=7)
    agreement(affect(pns[1], "individual"), monto_90="0", monto_100=None)
    ca = affect(pns[0], "colectivo", surface="0")
    for surface, dest in (("1.0000001", "tuc"), (None, "tuc"), ("0", "canal"), ("0.5", None)):
        unit(pns[0], ca, "colectivo", surface, dest)
    assembly = create(f"/api/proyecto-nucleo/{pns[0]}/asambleas",
                      id_tipo_asamblea=catalogs["tipo_asamblea"]["anuencia"],
                      convocatorias=[{"ordinal": 1, "id_resultado": catalogs["resultado_convocatoria"]["celebrada"], "fecha_realizacion": "2026-01-02"}])
    collective = agreement(ca, monto_100="500000", superficie_ha="2.5", id_asamblea_autorizacion=assembly["id_asamblea"], fecha_firma="2026-01-03")
    empty_collective = agreement(affect(pns[1], "colectivo"))

    def ran(target, identifier, events):
        return create("/api/tramites-ran", **{target: identifier}, eventos=[
            {"ordinal": i, "id_tipo_evento": catalogs["tipo_evento_ran"][kind], "fecha_evento": date}
            for i, (kind, date) in enumerate(events, 1)
        ])

    ra = ran("id_asamblea", assembly["id_asamblea"], [("ingreso", "2026-01-03"), ("inscripcion", "2026-01-04")])
    ran("id_asamblea", assembly["id_asamblea"], [])
    first = ran("id_convenio", collective["id_convenio"], [("ingreso", "2026-02-03"), ("inscripcion", "2026-02-10"), ("calificacion", None)])
    second = ran("id_convenio", collective["id_convenio"], [("ingreso", "2026-01-05"), ("reingreso", "2026-01-07"), ("inscripcion", "2026-03-03")])
    ran("id_convenio", individual["id_convenio"], [("ingreso", None), ("inscripcion", None)])
    env = dict(api=api, create=create, project_id=pid, pns=pns, individual=individual["id_convenio"],
               modification=modification["id_convenio"], empty_individual=empty_individual["id_convenio"],
               collective=collective["id_convenio"], empty_collective=empty_collective["id_convenio"],
               factory=factory, admin=admin, first=first, second=second, ra=ra,
               path=f"/api/proyectos/{pid}/reportes/convenios/general")
    try:
        yield env
    finally:
        if previous is None:
            app.dependency_overrides.pop(service.get_report_db, None)
        else:
            app.dependency_overrides[service.get_report_db] = previous


def full(env, **params):
    return env["api"]("GET", env["path"] + "/completo", params=params).json()


def by_id(rows, cid):
    return next(r for r in rows if r["id_convenio"] == cid)


def test_individual_multi_parcela_montos_y_candidatos(report_env):
    data = full(report_env)
    assert len(data["individuales"]) == 4
    item = by_id(data["individuales"], report_env["individual"])
    assert [p["no_parcela"] for p in item["parcelas"]] == ["0007", "P-02"]
    assert len(item["parcelas"][0]["ids_afectacion_unidad"]) == 2
    assert len(item["afectaciones"]) == 2
    assert Decimal(item["monto_total_90"]) == Decimal("90.01")
    assert Decimal(item["monto_total_100"]) == Decimal("100.02")
    assert all("monto_total_100" not in p for p in item["parcelas"])
    assert Decimal(item["superficie_declarada_m2"]) == Decimal("1234.567")
    assert item["superficie_excel_m2"] is None
    assert item["superficie_geometrica_m2"] is None
    assert item["superficie_administrativa_afectada"]["superficie_m2"] is None
    assert Decimal(item["superficie_administrativa_afectada"]["subtotal_conocido_m2"]) == Decimal("0.001")
    assert item["superficie_unidades"]["registros_sin_superficie"] == 1
    assert Decimal(item["afectaciones"][1]["superficie_impacto_m2"]) == Decimal("-0.001")
    assert item["tipo_cop_operativo"] == "ORIGEN"
    assert item["clasificacion_cop_incompleta"] is True


def test_colectivo_destinos_sin_producto_cartesiano(report_env):
    item = by_id(full(report_env)["colectivos"], report_env["collective"])
    assert len(item["destinos"]) == 3
    assert len(item["unidades"]) == 4
    assert Decimal(item["monto_total_100"]) == Decimal("500000")
    assert Decimal(item["superficie_declarada_m2"]) == Decimal("25000")
    tuc = next(d for d in item["destinos"] if d["codigo"] == "tuc")
    assert tuc["superficie"]["superficie_m2"] is None
    assert Decimal(tuc["superficie"]["subtotal_conocido_m2"]) == Decimal("10000.001")
    assert tuc["superficie"]["registros_sin_superficie"] == 1
    canal = next(d for d in item["destinos"] if d["codigo"] == "canal")
    assert Decimal(canal["superficie"]["superficie_m2"]) == 0
    assert any(d["id_destino_superficie"] is None for d in item["destinos"])
    assert all("monto_declarado" not in d and "superficie_declarada_m2" not in d for d in item["destinos"])


def test_ran_cuatro_fechas_historial_y_procedencia(report_env):
    item = by_id(full(report_env)["colectivos"], report_env["collective"])
    assert item["fecha_asamblea_realizada"] == "2026-01-02"
    assert item["fecha_ingreso_ran_asamblea"] == "2026-01-03"
    assert item["fecha_inscripcion_ran_asamblea"] == "2026-01-04"
    assert item["fecha_ingreso_ran_convenio"] == "2026-01-05"
    assert item["fecha_inscripcion_ran_convenio"] == "2026-02-10"
    ran = item["ran_convenio"]
    assert ran["ingreso"]["id_tramite_ran"] == report_env["second"]["id_tramite_ran"]
    assert ran["inscripcion"]["id_evento_ran"] == report_env["first"]["eventos"][1]["id_evento_ran"]
    assert ran["criterio"] == "primera_fecha_historica_por_tipo"
    assert ran["tramite_vigente_determinado"] is False
    assert ran["multiples_tramites"] and ran["fechas_de_distintos_tramites"]
    assert ran["eventos_sin_fecha"] == 1
    assert ran["cantidad_reingresos"] == 1
    assert len(ran["tramites"]) == 2
    assert len(item["ran_asamblea"]["tramites"]) == 2
    individual = by_id(full(report_env)["individuales"], report_env["individual"])
    assert individual["fecha_ingreso_ran_convenio"] is None
    assert individual["fecha_inscripcion_ran_convenio"] is None
    assert individual["ran_convenio"]["eventos_sin_fecha"] == 2


def test_nulos_y_ceros_sin_inferencias(report_env):
    data = full(report_env)
    individual = by_id(data["individuales"], report_env["empty_individual"])
    assert individual["monto_total_90"] is None
    assert Decimal(individual["monto_total_100"]) == 0
    assert individual["superficie_declarada_m2"] is None
    assert individual["parcelas"] == []
    assert individual["tipo_cop_operativo"] == "ORIGEN"  # consecutivo 7 is irrelevant
    collective = by_id(data["colectivos"], report_env["empty_collective"])
    assert collective["destinos"] == []
    assert collective["fecha_asamblea_realizada"] is None
    assert collective["fecha_ingreso_ran_asamblea"] is None
    assert collective["superficie_unidades"]["superficie_m2"] is None


def test_paginacion_completa_estable_y_entidades(report_env):
    expected = full(report_env)
    collected = {"individuales": [], "colectivos": []}
    for page in range(1, 5):
        response = report_env["api"]("GET", report_env["path"], params={"pagina": page, "tamano_pagina": 1}).json()
        for scope in collected:
            collected[scope].extend(response[scope])
            assert response["paginacion_" + scope]["total"] == len(expected[scope])
            assert response["paginacion_" + scope]["hay_mas"] == (page < len(expected[scope]))
    assert collected == {key: expected[key] for key in collected}
    assert [r["no"] for r in collected["individuales"]] == [1, 2, 3, 4]
    entities = report_env["api"]("GET", report_env["path"] + "/entidades").json()["entidades"]
    assert [e["id_entidad"] for e in entities] == [1, 2]
    assert sum(e["individuales"] for e in entities) == 4
    assert sum(e["colectivos"] for e in entities) == 2
    assert full(report_env) == expected


@pytest.mark.parametrize("params", [{"ambito": "individual"}, {"id_entidad": 2}, {"naturaleza": "modificatorio"}])
def test_filtros_antes_de_paginacion(report_env, params):
    data = full(report_env, **params)
    rows = data["individuales"] + data["colectivos"]
    assert rows
    for row in rows:
        for key, value in params.items():
            assert row["tipo_convenio" if key == "naturaleza" else key] == value
    if "ambito" in params:
        assert data["colectivos"] == []
    if "naturaleza" in params:
        assert [r["id_convenio"] for r in rows] == [report_env["modification"]]
        assert report_env["individual"] in [r["id_convenio"] for r in full(report_env)["individuales"]]


def test_sin_categoria_y_sin_resultados(report_env):
    assert full(report_env, ambito="colectivo")["individuales"] == []
    empty = full(report_env, id_entidad=999999)
    assert empty["individuales"] == empty["colectivos"] == []
    assert empty["completo"] is True
    page = report_env["api"]("GET", report_env["path"], params={"pagina": 100}).json()
    assert page["individuales"] == page["colectivos"] == []


@pytest.mark.parametrize("suffix", ["", "/entidades", "/completo"])
@pytest.mark.parametrize("role", ["admin", "operador", "visualizador", "geografo"])
def test_acceso_proyecto(report_env, suffix, role):
    original = app.dependency_overrides[auth.get_current_user]
    app.dependency_overrides[auth.get_current_user] = lambda: models.Usuario(id_usuario=9999999, rol=role)
    try:
        report_env["api"]("GET", report_env["path"] + suffix, expected=403 if role == "operador" else 200)
    finally:
        app.dependency_overrides[auth.get_current_user] = original


def test_limite_completo_explicito(report_env, monkeypatch):
    monkeypatch.setattr(service, "MAX_COMPLETE_CONVENIOS", 2)
    result = report_env["api"]("GET", report_env["path"] + "/completo", expected=413).json()
    assert result["detail"]["total_convenios"] == 6
    assert result["detail"]["codigo"] == "REPORTE_EXCEDE_LIMITE"
    assert result["detail"]["limite_convenios"] == 2
    assert result["detail"]["mensaje"] == "Acote los filtros; no se devolvieron datos parciales."
    validate_contract(result, "LimiteConveniosReporteResponse")
    response_schema = app.openapi()["paths"][report_env["path"].replace(str(report_env["project_id"]), "{id_proyecto}") + "/completo"]["get"]["responses"]["413"]["content"]["application/json"]["schema"]
    assert response_schema == {"$ref": "#/components/schemas/LimiteConveniosReporteResponse"}
    assert "individuales" not in result
    assert len(full(report_env, naturaleza="modificatorio")["individuales"]) == 1
    # Exactly six headers, even though some have several parcels/destinations.
    monkeypatch.setattr(service, "MAX_COMPLETE_CONVENIOS", 6)
    assert len(full(report_env)["colectivos"]) == 2


@pytest.mark.parametrize("params", [{"ambito": "invalido"}, {"naturaleza": "ORIGEN"}, {"pagina": 0}, {"tamano_pagina": 501}, {"id_entidad": 0}])
def test_filtros_invalidos(report_env, params):
    report_env["api"]("GET", report_env["path"], params=params, expected=422)


def test_sin_n_mas_uno(report_env):
    counts = []
    for size in (1, 500):
        statements = []
        def capture(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)
        with report_env["factory"]() as db:
            event.listen(db.connection(), "before_cursor_execute", capture)
            try:
                result = service.general_report(db, report_env["admin"], report_env["project_id"], tamano_pagina=size)
                schemas.ReporteGeneralConveniosResponse.model_validate(result)
            finally:
                event.remove(db.connection(), "before_cursor_execute", capture)
        counts.append(len(statements))
    assert counts == [7, 7]


def test_contratos_anteriores(report_env):
    pid = report_env["project_id"]
    old = report_env["api"]("GET", "/api/reportes/convenios/colectivos-destino", params={"id_proyecto": pid}).json()
    assert isinstance(old, list)
    assert any(r["id_convenio"] == report_env["collective"] and "monto_declarado" in r for r in old)
    declared = report_env["api"]("GET", "/api/reportes/convenios/valores-declarados", params={"id_proyecto": pid}).json()
    assert any(r["concepto"] == "monto_90_declarado" for r in declared)


def test_conexion_real_de_reporte_solo_lectura():
    # Exercise the production dependency against the disposable instance,
    # without replacing it with the transactional fixture.
    iterator = service.get_report_db()
    db = next(iterator)
    try:
        assert db.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
        assert db.execute(text("SHOW transaction_isolation")).scalar_one() == "repeatable read"
        assert db.execute(text("SHOW cluster_name")).scalar_one() == "convenio-report-disposable"
    finally:
        iterator.close()


@pytest.mark.parametrize("role", ["operador", "visualizador", "geografo"])
def test_roles_lectores_respetan_alcance_actual(report_env, role):
    user = report_env["create"]("/api/usuarios", nombre="Reporte", apellido_paterno="Sintético", rol=role,
                                correo=uuid.uuid4().hex + "@local.invalid", contrasena="Convenios2026!Aislado")
    report_env["api"]("POST", f"/api/proyectos/{report_env['project_id']}/usuarios", expected=201 if role == "operador" else 422,
                      json={"id_usuario":user["id_usuario"]})
    original = app.dependency_overrides[auth.get_current_user]
    app.dependency_overrides[auth.get_current_user] = lambda: models.Usuario(id_usuario=user["id_usuario"], rol=role)
    try:
        assert len(full(report_env)["individuales"]) == 4
        assert len(report_env["api"]("GET", report_env["path"] + "/entidades").json()["entidades"]) == 2
        report_env["api"]("GET", "/api/proyectos/9999999/reportes/convenios/general/completo", expected=403)
    finally:
        app.dependency_overrides[auth.get_current_user] = original


def test_bajas_sin_descartar_instrumentos_originales(report_env):
    with report_env["factory"]() as db:
        # Only synthetic records, inside a savepoint additionally rolled back.
        with db.begin_nested() as savepoint:
            set_audit_context(db, report_env["admin"].id_usuario)
            record = db.get(models.Convenio, report_env["empty_collective"])
            mark_inactive(record, report_env["admin"].id_usuario, "Baja sintética para reporte")
            db.flush()
            data = service.general_report(db, report_env["admin"], report_env["project_id"], completo=True)
            assert [r["id_convenio"] for r in data["colectivos"]] == [report_env["collective"]]
            assert report_env["individual"] in [r["id_convenio"] for r in data["individuales"]]
            savepoint.rollback()


def test_facetas_respetan_naturaleza_sin_depender_de_pagina(report_env):
    data = report_env["api"]("GET", report_env["path"] + "/entidades", params={"naturaleza": "modificatorio"}).json()
    assert data["entidades"] == [{"id_entidad": 1, "estado": "Entidad sintética A", "individuales": 1, "colectivos": 0}]


@pytest.mark.parametrize("suffix", ["", "/entidades", "/completo"])
def test_sin_sesion(report_env, suffix):
    original = app.dependency_overrides.pop(auth.get_current_user)
    try:
        report_env["api"]("GET", report_env["path"] + suffix, expected=401)
    finally:
        app.dependency_overrides[auth.get_current_user] = original


def test_proyecto_vacio_no_filtra_datos_de_otro_proyecto(report_env):
    project = report_env["create"]("/api/proyectos", clave_proyecto=uuid.uuid4().hex[:20], nombre_proyecto="Vacío sintético")
    path = f"/api/proyectos/{project['id_proyecto']}/reportes/convenios/general"
    data = report_env["api"]("GET", path + "/completo").json()
    assert data["individuales"] == data["colectivos"] == []
    assert report_env["api"]("GET", path + "/entidades").json()["entidades"] == []


def test_snapshot_consistente_entre_consultas():
    from app.database import SessionLocal
    name = "Snapshot " + uuid.uuid4().hex
    with SessionLocal() as writer:
        assert writer.execute(text("SHOW cluster_name")).scalar_one() == "convenio-report-disposable"
        set_audit_context(writer, 1)
        project = models.Proyecto(clave_proyecto=uuid.uuid4().hex[:20], nombre_proyecto=name, creado_por=1)
        writer.add(project)
        writer.flush()
        project_id = project.id_proyecto
        writer.commit()
    iterator = service.get_report_db()
    reader = next(iterator)
    statement = text("SELECT nombre_proyecto FROM proyecto WHERE id_proyecto=:id")
    try:
        assert reader.execute(statement, {"id": project_id}).scalar_one() == name
        with SessionLocal() as writer:
            set_audit_context(writer, 1)
            writer.execute(text("UPDATE proyecto SET nombre_proyecto=:name WHERE id_proyecto=:id"), {"name": name + " modificado", "id": project_id})
            writer.commit()
        assert reader.execute(statement, {"id": project_id}).scalar_one() == name
    finally:
        iterator.close()
    with SessionLocal() as reader:
        assert reader.execute(statement, {"id": project_id}).scalar_one() == name + " modificado"
