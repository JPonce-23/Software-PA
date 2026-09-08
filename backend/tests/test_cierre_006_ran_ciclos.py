"""Regresiones de ciclos RAN para el cierre funcional 006.

Ejecutar sólo contra una base QA aislada, con el guard de conftest.py.
No modifica el esquema ni presupone una migración 007.
"""

import uuid

import pytest

from .test_excel_closure_002 import _catalog, _isolated_pn


def _period(api, project_id, indicator, month):
    return api(
        "GET",
        "/api/reportes/avance-periodo",
        params={
            "id_proyecto": project_id,
            "anio": 2026,
            "mes": month,
            "indicador": indicator,
        },
    ).json()


def _total(rows, field):
    return sum(row[field] for row in rows)


def _assembly(api, pn_id):
    types = _catalog(api, "tipo_asamblea")
    contexts = _catalog(api, "contexto_asamblea")
    results = _catalog(api, "resultado_convocatoria")
    return api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": types["anuencia"],
            "id_contexto_asamblea": contexts["cop_original"],
            "id_tipo_cop_operativo": _catalog(api, "tipo_cop_operativo")["ORIGEN"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2026-01-15",
                    "fecha_realizacion": "2026-01-15",
                    "id_resultado": results["celebrada"],
                }
            ],
        },
    ).json()


def _target(api, pn_id, kind):
    if kind == "acta":
        assembly = _assembly(api, pn_id)
        return {"id_asamblea": assembly["id_asamblea"]}, assembly["id_asamblea"]
    affectation = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "colectivo",
            "id_tipo_cop_operativo": _catalog(api, "tipo_cop_operativo")["ORIGEN"],
        },
    ).json()
    agreement = api(
        "POST",
        f"/api/afectaciones/{affectation['id_afectacion']}/convenios",
        expected=201,
        json={"tipo_convenio": "cop_original", "fecha_firma": "2026-01-20"},
    ).json()
    return {"id_convenio": agreement["id_convenio"]}, agreement["id_convenio"]


@pytest.mark.parametrize("kind", ["acta", "convenio"])
def test_ran_dos_prevenciones_y_reingresos_conservan_identidad(
    api, target_domain, kind
):
    project, pn = _isolated_pn(api, target_domain)
    target, target_id = _target(api, pn["id_proyecto_nucleo"], kind)
    codes = _catalog(api, "tipo_evento_ran")
    reference = f"QA-RAN-{uuid.uuid4().hex[:8]}"
    procedure = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            **target,
            "referencia_expediente": reference,
            "fecha_programada_ingreso": "2026-01-25",
        },
    ).json()
    ran_id = procedure["id_tramite_ran"]
    sequence = [
        ("ingreso", "2026-02-02", "SOL-001", None),
        ("prevencion", "2026-02-05", "SOL-001", "Documentación incompleta"),
        ("subsanacion", "2026-02-10", "SOL-001", "Se presenta documentación"),
        ("reingreso", "2026-03-02", "SOL-002", None),
        ("prevencion", "2026-03-05", "SOL-002", "Segunda prevención"),
        ("subsanacion", "2026-03-10", "SOL-002", "Segunda subsanación"),
        ("reingreso", "2026-04-02", "SOL-003", None),
        ("calificacion", "2026-04-10", "SOL-003", "procedente"),
        ("inscripcion", "2026-05-02", "SOL-003", None),
    ]
    for ordinal, (code, date, number, result) in enumerate(sequence, 1):
        payload = {
            "ordinal": ordinal,
            "id_tipo_evento": codes[code],
            "fecha_evento": date,
            "numero_solicitud": number,
        }
        if result is not None:
            if code == "calificacion":
                payload["calificacion"] = result
            else:
                payload["resultado"] = result
        event = api(
            "POST",
            f"/api/tramites-ran/{ran_id}/eventos",
            expected=201,
            json=payload,
        ).json()
        assert event["id_tramite_ran"] == ran_id
        if code == "calificacion":
            assert (
                _total(
                    _period(
                        api,
                        project["id_proyecto"],
                        f"inscripcion_ran_{kind}",
                        4,
                    ),
                    "realizado",
                )
                == 0
            )

    stored = api("GET", f"/api/tramites-ran/{ran_id}").json()
    events = api("GET", f"/api/tramites-ran/{ran_id}/eventos").json()
    assert stored["referencia_expediente"] == reference
    assert stored[next(iter(target))] == target_id
    assert len(events) == len(sequence)
    assert [e["ordinal"] for e in events] == list(range(1, 10))
    assert [e["fecha_evento"] for e in events] == [row[1] for row in sequence]
    assert [e["numero_solicitud"] for e in events] == [row[2] for row in sequence]
    assert [e["id_tipo_evento"] for e in events] == [codes[row[0]] for row in sequence]
    endpoint = "asambleas" if kind == "acta" else "convenios"
    assert len(api("GET", f"/api/{endpoint}/{target_id}/tramites-ran").json()) == 1

    project_id = project["id_proyecto"]
    ingress = f"ingreso_ran_{kind}"
    inscription = f"inscripcion_ran_{kind}"
    assert _total(_period(api, project_id, ingress, 1), "programado") == 1
    assert _total(_period(api, project_id, ingress, 2), "realizado") == 1
    assert _total(_period(api, project_id, ingress, 3), "realizado") == 0
    assert _total(_period(api, project_id, ingress, 4), "realizado") == 0
    assert _total(_period(api, project_id, inscription, 4), "realizado") == 0
    assert _total(_period(api, project_id, inscription, 5), "realizado") == 1
    annual = api(
        "GET",
        "/api/reportes/avance-periodo",
        params={"id_proyecto": project_id, "anio": 2026, "indicador": ingress},
    ).json()
    assert _total(annual, "realizado") == 1
    assert _total(annual, "programado") == 1


def test_subsanacion_no_genera_reingreso_automatico(api, target_domain):
    _, pn = _isolated_pn(api, target_domain)
    target, _ = _target(api, pn["id_proyecto_nucleo"], "acta")
    codes = _catalog(api, "tipo_evento_ran")
    ran = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            **target,
            "eventos": [
                {
                    "ordinal": 1,
                    "id_tipo_evento": codes["ingreso"],
                    "fecha_evento": "2026-02-02",
                },
                {
                    "ordinal": 2,
                    "id_tipo_evento": codes["prevencion"],
                    "fecha_evento": "2026-02-05",
                },
            ],
        },
    ).json()
    ran_id = ran["id_tramite_ran"]
    api(
        "POST",
        f"/api/tramites-ran/{ran_id}/eventos",
        expected=201,
        json={
            "ordinal": 3,
            "id_tipo_evento": codes["subsanacion"],
            "fecha_evento": "2026-02-10",
            "resultado": "Documentos recibidos",
        },
    )
    events = api("GET", f"/api/tramites-ran/{ran_id}/eventos").json()
    assert len(events) == 3
    assert [e["id_tipo_evento"] for e in events] == [
        codes[c] for c in ("ingreso", "prevencion", "subsanacion")
    ]


def test_ran_desistimiento_y_correccion_no_duplican_asamblea(api, target_domain):
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    target, assembly_id = _target(api, pn_id, "acta")
    codes = _catalog(api, "tipo_evento_ran")
    sequence = ["ingreso", "desistimiento", "subsanacion", "reingreso", "inscripcion"]
    ran = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            **target,
            "eventos": [
                {
                    "ordinal": i,
                    "id_tipo_evento": codes[code],
                    "fecha_evento": f"2026-0{i + 1}-05",
                    "resultado": "Corrección de la misma acta",
                }
                for i, code in enumerate(sequence, 1)
            ],
        },
    ).json()
    assert len(ran["eventos"]) == 5
    assert len(api("GET", f"/api/asambleas/{assembly_id}/tramites-ran").json()) == 1
    assert len(api("GET", f"/api/proyecto-nucleo/{pn_id}/asambleas").json()) == 1
    assert (
        _total(_period(api, project["id_proyecto"], "ingreso_ran_acta", 2), "realizado")
        == 1
    )
    assert (
        _total(_period(api, project["id_proyecto"], "ingreso_ran_acta", 5), "realizado")
        == 0
    )
    assert (
        _total(
            _period(api, project["id_proyecto"], "inscripcion_ran_acta", 6),
            "realizado",
        )
        == 1
    )


def test_ran_orv_conserva_objetivo_del_nucleo(api, target_domain):
    nucleus_id = target_domain["nucleus"]["id_nucleo"]
    pn_id = target_domain["project_nucleus"]["id_proyecto_nucleo"]
    orv = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/orv",
        expected=201,
        json={
            "numero_orv": f"QA-{uuid.uuid4().hex[:8]}",
            "inicio_vigencia": "2026-01-01",
            "fin_vigencia": "2028-12-31",
        },
    ).json()
    codes = _catalog(api, "tipo_evento_ran")
    ran = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_orv": orv["id_orv"],
            "eventos": [
                {
                    "ordinal": 1,
                    "id_tipo_evento": codes["ingreso"],
                    "fecha_evento": "2026-02-01",
                },
                {
                    "ordinal": 2,
                    "id_tipo_evento": codes["prevencion"],
                    "fecha_evento": "2026-02-05",
                },
                {
                    "ordinal": 3,
                    "id_tipo_evento": codes["subsanacion"],
                    "fecha_evento": "2026-02-10",
                },
                {
                    "ordinal": 4,
                    "id_tipo_evento": codes["reingreso"],
                    "fecha_evento": "2026-03-01",
                },
                {
                    "ordinal": 5,
                    "id_tipo_evento": codes["inscripcion"],
                    "fecha_evento": "2026-04-01",
                },
            ],
        },
    ).json()
    stored = api("GET", f"/api/tramites-ran/{ran['id_tramite_ran']}").json()
    assert stored["id_orv"] == orv["id_orv"]
    assert stored["id_nucleo"] == nucleus_id
    assert stored["id_proyecto_nucleo"] is None
    assert stored["id_asamblea"] is None and stored["id_convenio"] is None
    assert len(api("GET", f"/api/orv/{orv['id_orv']}/tramites-ran").json()) == 1
    assert (
        len(api("GET", f"/api/tramites-ran/{ran['id_tramite_ran']}/eventos").json())
        == 5
    )


def test_ran_objetivos_exclusivos_y_ordinal_repetido(api, target_domain):
    _, pn = _isolated_pn(api, target_domain)
    target, assembly_id = _target(api, pn["id_proyecto_nucleo"], "acta")
    codes = _catalog(api, "tipo_evento_ran")
    api("POST", "/api/tramites-ran", expected=422, json={})
    api(
        "POST",
        "/api/tramites-ran",
        expected=422,
        json={"id_asamblea": assembly_id, "id_convenio": 1},
    )
    api(
        "POST",
        "/api/tramites-ran",
        expected=422,
        json={
            **target,
            "eventos": [
                {"ordinal": 1, "id_tipo_evento": codes["ingreso"]},
                {"ordinal": 1, "id_tipo_evento": codes["prevencion"]},
            ],
        },
    )
    ran = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            **target,
            "eventos": [
                {
                    "ordinal": 1,
                    "id_tipo_evento": codes["ingreso"],
                    "fecha_evento": "2026-02-01",
                }
            ],
        },
    ).json()
    api(
        "POST",
        f"/api/tramites-ran/{ran['id_tramite_ran']}/eventos",
        expected=409,
        json={
            "ordinal": 1,
            "id_tipo_evento": codes["prevencion"],
            "fecha_evento": "2026-02-05",
        },
    )
    assert (
        len(api("GET", f"/api/tramites-ran/{ran['id_tramite_ran']}/eventos").json())
        == 1
    )
