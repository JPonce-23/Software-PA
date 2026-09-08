"""Regresiones del bloque 2 trazadas a los Excel del cierre V1.

Las fuentes se documentan por archivo, hoja y fila. Cuando una actuación no tiene
fecha completa en el Excel, la prueba conserva ``fecha_evento=None``.
"""

from sqlalchemy import text

from app.database import SessionLocal
from .test_excel_closure_002 import _catalog, _isolated_pn


COLECTIVOS_2708 = (
    "Copia SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS "
    "MQ_COLECTIVOS MEET 27082026.xlsx / INFORME M-Q"
)
COLECTIVOS_REV = (
    "Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx / "
    "INFORME M-Q"
)


def _snapshot(api, project_id, indicator):
    return api(
        "GET",
        f"/api/reportes/resumen-actual?id_proyecto={project_id}&indicador={indicator}",
    ).json()


def _period(api, project_id, indicator):
    return api(
        "GET",
        f"/api/reportes/avance-periodo?id_proyecto={project_id}&indicador={indicator}",
    ).json()


def test_bloque_02_expropiacion_actual_cuenta_nucleos_y_no_infiere_estado(api, target_domain):
    """REV/ASAMBLEAS PENDIENTES filas 8, 23, 49, 52 y 62: marca estructurada SI."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    affects = [
        api(
            "POST",
            f"/api/proyecto-nucleo/{pn_id}/afectaciones",
            expected=201,
            json={
                "tipo_afectacion": "colectivo",
                "condicion_especial": "expropiacion_directa",
            },
        ).json()
        for _ in range(2)
    ]

    rows = _snapshot(api, project["id_proyecto"], "expropiacion_directa_actual")
    assert len(rows) == 1 and rows[0]["cantidad"] == 1
    assert api("GET", f"/api/proyecto-nucleo/{pn_id}").json()["afecta_tuc"] is None
    assert api("GET", f"/api/proyecto-nucleo/{pn_id}/seguimiento").json() == []

    # La vigencia proviene del valor actual de afectaciones activas, no del historial.
    api(
        "PATCH",
        f"/api/afectaciones/{affects[0]['id_afectacion']}",
        json={"condicion_especial": None},
    )
    assert _snapshot(api, project["id_proyecto"], "expropiacion_directa_actual")[0]["cantidad"] == 1
    api(
        "PATCH",
        f"/api/afectaciones/{affects[1]['id_afectacion']}",
        json={"condicion_especial": None},
    )
    assert _snapshot(api, project["id_proyecto"], "expropiacion_directa_actual") == []


def test_bloque_02_orv_especial_usa_otro_detalle_y_documento_sin_fecha(api, target_domain):
    """REV/INFORME M-Q fila 10: AHORCADO, ORV en juicio y expropiación directa."""
    _, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    orv = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/orv",
        expected=201,
        json={"numero_orv": "AHORCADO-REV-F10", "estatus_fuente": "caso especial Excel"},
    ).json()
    document = api(
        "POST",
        f"/api/documentos/objetivos/orv/{orv['id_orv']}",
        expected=201,
        json={
            "tipo_documento": "soporte_caso_especial",
            "estado": "referenciado",
            "titulo": "Soporte ORV - fuente REV fila 10",
        },
    ).json()
    event = _catalog(api, "tipo_evento_seguimiento")
    reason = _catalog(api, "motivo_seguimiento")
    recorded = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "ambito": "colectivo",
            "entidad_tipo": "orv",
            "entidad_id": orv["id_orv"],
            "id_tipo_evento": event["otro"],
            "id_motivo": reason["otro"],
            "detalle": "Caso especial: ORV en juicio agrario; ruta informada de expropiación directa",
            "id_documento": document["id_documento"],
            "fuente": f"{COLECTIVOS_REV}, fila 10",
        },
    ).json()
    assert recorded["fecha_evento"] is None
    assert recorded["entidad_tipo"] == "orv"
    assert recorded["id_documento"] == document["id_documento"]


def test_bloque_02_huecatitla_no_tuc_a_tuc_preserva_identidad_e_historia(api, target_domain):
    """REV fila 27 -> 27/08 fila 33; el cambio está soportado el 24/04/2026."""
    _, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    reason_tuc = _catalog(api, "motivo_no_afecta_tuc")["no_afectacion_colectiva"]
    events = _catalog(api, "tipo_evento_seguimiento")
    reasons = _catalog(api, "motivo_seguimiento")

    before = api(
        "PATCH",
        f"/api/proyecto-nucleo/{pn_id}",
        json={"afecta_tuc": False, "id_motivo_no_afecta_tuc": reason_tuc},
    ).json()
    change = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "ambito": "colectivo",
            "id_tipo_evento": events["cambio_alcance"],
            "id_motivo": reasons["nueva_informacion"],
            "fecha_evento": "2026-04-24",
            "detalle": "La fuente posterior documenta afectación a TUC",
            "fuente": f"{COLECTIVOS_2708}, fila 33",
        },
    ).json()
    after = api(
        "PATCH",
        f"/api/proyecto-nucleo/{pn_id}",
        json={
            "afecta_tuc": True,
            "id_motivo_no_afecta_tuc": None,
            "motivo_no_afecta_tuc_detalle": None,
        },
    ).json()

    assert before["id_proyecto_nucleo"] == after["id_proyecto_nucleo"] == pn_id
    assert after["afecta_tuc"] is True
    history = api("GET", f"/api/proyecto-nucleo/{pn_id}/seguimiento").json()
    assert [row["id_seguimiento_evento"] for row in history] == [change["id_seguimiento_evento"]]


def test_bloque_02_comunidad_no_infiere_consulta_ni_suspension(api, target_domain):
    """27/08 fila 20: CB=SÍ es condición del núcleo, separada de actuaciones."""
    project, pn = _isolated_pn(api, target_domain)
    api("PATCH", f"/api/nucleos/{pn['id_nucleo']}", json={"comunidad_indigena": True})

    assert _snapshot(api, project["id_proyecto"], "comunidad_indigena")[0]["cantidad"] == 1
    assert api("GET", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/seguimiento").json() == []
    with SessionLocal() as db:
        current = db.execute(
            text(
                "SELECT estado_actual FROM vw_seguimiento_estado_actual "
                "WHERE id_proyecto_nucleo=:pn"
            ),
            {"pn": pn["id_proyecto_nucleo"]},
        ).first()
    assert current is None


def test_bloque_02_consulta_sin_anio_no_inventa_fecha_ni_periodo(api, target_domain):
    """27/08 fila 20: consulta 7/14 de septiembre, pero la fila no expresa año."""
    project, pn = _isolated_pn(api, target_domain)
    events = _catalog(api, "tipo_evento_seguimiento")
    reasons = _catalog(api, "motivo_seguimiento")
    recorded = api(
        "POST",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/seguimiento",
        expected=201,
        json={
            "ambito": "colectivo",
            "id_tipo_evento": events["consulta_indigena"],
            "id_motivo": reasons["comunidad_indigena"],
            "detalle": "Presentación de protocolo y reunión de consulta; año no determinado",
            "fuente": f"{COLECTIVOS_2708}, fila 20",
        },
    ).json()
    assert recorded["fecha_evento"] is None
    assert len(api("GET", f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/seguimiento").json()) == 1
    assert _period(api, project["id_proyecto"], "consulta_indigena") == []


def test_bloque_02_reunion_posterior_no_reabre(api, target_domain):
    """Contrato sintético: una reunión posterior nunca equivale a reapertura."""
    _, pn = _isolated_pn(api, target_domain)
    events = _catalog(api, "tipo_evento_seguimiento")
    reasons = _catalog(api, "motivo_seguimiento")
    pn_id = pn["id_proyecto_nucleo"]
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "ambito": "colectivo",
            "id_tipo_evento": events["suspension"],
            "id_motivo": reasons["otro"],
            # Fechas exclusivas del fixture; no se atribuyen a una fila Excel.
            "fecha_evento": "2026-01-25",
            "detalle": "Suspensión previa del fixture de contrato",
        },
    )
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "ambito": "colectivo",
            "id_tipo_evento": events["reunion"],
            "fecha_evento": "2026-01-26",
            "detalle": "Reunión informativa; no equivale a reapertura",
            "fuente": "Fixture sintético de contrato bloque 2",
        },
    )
    with SessionLocal() as db:
        current = db.execute(
            text(
                "SELECT estado_actual, tipo_ultimo_evento FROM vw_seguimiento_estado_actual "
                "WHERE id_proyecto_nucleo=:pn AND entidad_tipo IS NULL"
            ),
            {"pn": pn_id},
        ).one()
    assert current.estado_actual == "suspendido"
    assert current.tipo_ultimo_evento == "suspension"


def test_bloque_02_san_pedrito_necesidad_no_es_caminamiento_realizado(api, target_domain):
    """27/08 fila 80: el 03/02/2026 sólo se expresa necesidad de nuevo caminamiento."""
    project, pn = _isolated_pn(api, target_domain)
    events = _catalog(api, "tipo_evento_seguimiento")
    reasons = _catalog(api, "motivo_seguimiento")
    pn_id = pn["id_proyecto_nucleo"]
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "ambito": "colectivo",
            "id_tipo_evento": events["cambio_alcance"],
            "id_motivo": reasons["nueva_informacion"],
            "fecha_evento": "2026-02-03",
            "detalle": "Se identifica necesidad de nuevo caminamiento para superficie adicional",
            "fuente": f"{COLECTIVOS_2708}, fila 80",
        },
    )
    assert api("GET", f"/api/proyecto-nucleo/{pn_id}/actividades").json() == []
    assert _period(api, project["id_proyecto"], "caminamiento_ADICIONAL") == []
    assert len(_period(api, project["id_proyecto"], "cambio_alcance")) == 1


def test_bloque_02_santa_barbara_conserva_contradiccion_en_revision(api, target_domain):
    """27/08 fila 32: la misma fila afirma no-TUC y afectación TUC con amparo."""
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    updated = api(
        "PATCH",
        f"/api/proyecto-nucleo/{pn_id}",
        json={
            "afecta_tuc": None,
            "tuc_revision_pendiente": True,
            "tuc_revision_detalle": (
                "Fuente contradictoria: declara no afectación y también afectación TUC con amparo"
            ),
        },
    ).json()
    assert updated["afecta_tuc"] is None
    assert updated["tuc_revision_pendiente"] is True
    assert "contradictoria" in updated["tuc_revision_detalle"].lower()
    assert _snapshot(api, project["id_proyecto"], "no_afecta_tuc") == []
