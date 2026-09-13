"""Pruebas de regresión: semántica triestado TUC en vw_reporte_snapshot_actual.

Verifica que el reporting/snapshot no confunda:
- Caso A: afecta_tuc = true, revisión no pendiente -> NO cuenta en no_afecta_tuc
- Caso B: afecta_tuc = false, revisión no pendiente -> SÍ cuenta en no_afecta_tuc (confirmado)
- Caso C: afecta_tuc = NULL, revisión no pendiente -> NO cuenta en no_afecta_tuc (desconocido)
- Caso D: afecta_tuc = NULL, revisión pendiente -> NO cuenta en no_afecta_tuc (pendiente de conciliar)
- Caso E: afecta_tuc = false, revisión pendiente -> NO cuenta en no_afecta_tuc (no confirmado)
"""

import uuid
import pytest
from sqlalchemy import text
from app.database import SessionLocal


def _catalog(api, name: str) -> dict[str, int]:
    return {
        row["codigo"]: row["id_catalogo_opcion"]
        for row in api("GET", f"/api/catalogos/operativos/{name}").json()
    }


def _create_project(api, prefix="QA-TUC"):
    token = uuid.uuid4().hex[:8]
    return api(
        "POST",
        "/api/proyectos",
        expected=201,
        json={
            "clave_proyecto": f"{prefix}-{token}",
            "nombre_proyecto": f"Proyecto TUC QA {token}",
            "fecha_inicio": "2026-09-10",
        },
    ).json()


def _create_nucleus(api, municipality_id, prefix="NUC-TUC"):
    token = uuid.uuid4().hex[:8]
    tenencia = _catalog(api, "tipo_tenencia")["ejido"]
    return api(
        "POST",
        "/api/nucleos",
        expected=201,
        json={
            "id_municipio": municipality_id,
            "nombre_nucleo": f"{prefix} {token}",
            "id_tipo_tenencia": tenencia,
            "fuente_datos": "qa-tuc-test",
        },
    ).json()


def _snapshot(api, project_id: int, indicator: str | None = None, id_entidad: int | None = None):
    url = f"/api/reportes/resumen-actual?id_proyecto={project_id}"
    if indicator:
        url += f"&indicador={indicator}"
    if id_entidad:
        url += f"&id_entidad={id_entidad}"
    return api("GET", url).json()


def test_snapshot_tuc_triestado_casos_individuales(api, target_domain):
    """Evalúa los casos A, B, C, D y E de manera aislada."""
    reason_tuc = _catalog(api, "motivo_no_afecta_tuc")["no_afectacion_colectiva"]
    municipality_id = target_domain["municipality"]["id_municipio"]

    cases = [
        # (case_name, afecta_tuc, id_motivo, detalle_motivo, rev_pendiente, rev_detalle, expected_count)
        ("Caso_A_afecta_true", True, None, None, False, None, 0),
        ("Caso_B_afecta_false_confirmado", False, reason_tuc, None, False, None, 1),
        ("Caso_C_afecta_null_sin_revision", None, None, None, False, None, 0),
        ("Caso_D_afecta_null_con_revision", None, None, None, True, "Revisión pendiente caso D", 0),
        ("Caso_E_afecta_false_con_revision", False, reason_tuc, None, True, "Revisión pendiente caso E", 0),
    ]

    for case_name, afecta, motivo, det_motivo, rev_pend, rev_det, expected_count in cases:
        project = _create_project(api, prefix=case_name[:8])
        nucleus = _create_nucleus(api, municipality_id, prefix=case_name[:8])

        payload = {
            "id_nucleo": nucleus["id_nucleo"],
            "afecta_tuc": afecta,
            "tuc_revision_pendiente": rev_pend,
        }
        if motivo is not None:
            payload["id_motivo_no_afecta_tuc"] = motivo
        if det_motivo is not None:
            payload["motivo_no_afecta_tuc_detalle"] = det_motivo
        if rev_det is not None:
            payload["tuc_revision_detalle"] = rev_det

        pn = api(
            "POST",
            f"/api/proyectos/{project['id_proyecto']}/nucleos",
            expected=201,
            json=payload,
        ).json()

        assert pn["afecta_tuc"] == afecta
        assert pn["tuc_revision_pendiente"] is rev_pend

        # Snapshot para total_nucleos debe ser siempre 1
        snap_total = _snapshot(api, project["id_proyecto"], "total_nucleos")
        assert len(snap_total) == 1, f"Fallo en total_nucleos para {case_name}"
        assert snap_total[0]["cantidad"] == 1

        # Snapshot para no_afecta_tuc
        snap_no_tuc = _snapshot(api, project["id_proyecto"], "no_afecta_tuc")
        if expected_count == 0:
            assert snap_no_tuc == [], (
                f"{case_name}: se esperaba lista vacía para no_afecta_tuc, pero se obtuvo {snap_no_tuc}"
            )
        else:
            assert len(snap_no_tuc) == 1, (
                f"{case_name}: se esperaba exactamente 1 fila para no_afecta_tuc, pero se obtuvo {snap_no_tuc}"
            )
            assert snap_no_tuc[0]["cantidad"] == expected_count
            assert snap_no_tuc[0]["indicador"] == "no_afecta_tuc"
            assert snap_no_tuc[0]["ambito"] == "colectivo"


def test_snapshot_tuc_proyecto_combinado_y_aislamiento_entidades(api, target_domain):
    """Verifica un proyecto con múltiples núcleos y entidades:
    - Entidad 1: Casos A, B, C, D, E (5 núcleos). Sólo B debe sumar en no_afecta_tuc.
    - Entidad 2: 1 Caso B (confirmado) y 1 Caso E (revisión pendiente). Sólo B debe sumar.
    - Total proyecto: 7 núcleos, 2 no_afecta_tuc (1 por entidad).
    - Sin duplicados ni contaminación cruzada entre entidades.
    """
    reason_tuc = _catalog(api, "motivo_no_afecta_tuc")["no_afectacion_colectiva"]
    project = _create_project(api, prefix="COMB")
    project_id = project["id_proyecto"]

    # Entidad 1 (de target_domain)
    entidad_1_id = target_domain["state"]["id_entidad"]
    muni_1_id = target_domain["municipality"]["id_municipio"]

    # Obtenemos un municipio de una segunda entidad distinta
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT id_municipio, id_entidad FROM municipio WHERE id_entidad != :e1 LIMIT 1"),
            {"e1": entidad_1_id},
        ).mappings().first()
        muni_2_id = row["id_municipio"]
        entidad_2_id = row["id_entidad"]
    finally:
        db.close()

    assert entidad_1_id != entidad_2_id

    # Casos en Entidad 1: A, B, C, D, E
    configs_entidad_1 = [
        (True, None, False, None),                                  # A
        (False, reason_tuc, False, None),                           # B (único que cuenta)
        (None, None, False, None),                                  # C
        (None, None, True, "Rev D"),                                # D
        (False, reason_tuc, True, "Rev E"),                         # E
    ]
    for afecta, motivo, rev_p, rev_d in configs_entidad_1:
        nuc = _create_nucleus(api, muni_1_id, prefix="N1")
        payload = {"id_nucleo": nuc["id_nucleo"], "afecta_tuc": afecta, "tuc_revision_pendiente": rev_p}
        if motivo: payload["id_motivo_no_afecta_tuc"] = motivo
        if rev_d: payload["tuc_revision_detalle"] = rev_d
        api("POST", f"/api/proyectos/{project_id}/nucleos", expected=201, json=payload)

    # Casos en Entidad 2: B y E
    configs_entidad_2 = [
        (False, reason_tuc, False, None),                           # B (único que cuenta)
        (False, reason_tuc, True, "Rev E2"),                        # E
    ]
    for afecta, motivo, rev_p, rev_d in configs_entidad_2:
        nuc = _create_nucleus(api, muni_2_id, prefix="N2")
        payload = {"id_nucleo": nuc["id_nucleo"], "afecta_tuc": afecta, "tuc_revision_pendiente": rev_p}
        if motivo: payload["id_motivo_no_afecta_tuc"] = motivo
        if rev_d: payload["tuc_revision_detalle"] = rev_d
        api("POST", f"/api/proyectos/{project_id}/nucleos", expected=201, json=payload)

    # Verificación total_nucleos por entidad
    snap_tot_e1 = _snapshot(api, project_id, "total_nucleos", id_entidad=entidad_1_id)
    assert len(snap_tot_e1) == 1
    assert snap_tot_e1[0]["cantidad"] == 5

    snap_tot_e2 = _snapshot(api, project_id, "total_nucleos", id_entidad=entidad_2_id)
    assert len(snap_tot_e2) == 1
    assert snap_tot_e2[0]["cantidad"] == 2

    # Verificación no_afecta_tuc por entidad
    snap_no_tuc_e1 = _snapshot(api, project_id, "no_afecta_tuc", id_entidad=entidad_1_id)
    assert len(snap_no_tuc_e1) == 1
    assert snap_no_tuc_e1[0]["cantidad"] == 1
    assert snap_no_tuc_e1[0]["id_entidad"] == entidad_1_id

    snap_no_tuc_e2 = _snapshot(api, project_id, "no_afecta_tuc", id_entidad=entidad_2_id)
    assert len(snap_no_tuc_e2) == 1
    assert snap_no_tuc_e2[0]["cantidad"] == 1
    assert snap_no_tuc_e2[0]["id_entidad"] == entidad_2_id

    # Verificación global de no_afecta_tuc en el proyecto (sin filtro de entidad)
    snap_no_tuc_all = _snapshot(api, project_id, "no_afecta_tuc")
    assert len(snap_no_tuc_all) == 2
    entidades_presentes = {r["id_entidad"]: r["cantidad"] for r in snap_no_tuc_all}
    assert entidades_presentes == {entidad_1_id: 1, entidad_2_id: 1}


def test_snapshot_tuc_patch_transicion_triestado(api, target_domain):
    """Verifica transiciones dinámicas entre estados en el mismo ProyectoNucleo."""
    reason_tuc = _catalog(api, "motivo_no_afecta_tuc")["no_afectacion_colectiva"]
    project = _create_project(api, prefix="TRANS")
    project_id = project["id_proyecto"]
    nucleus = _create_nucleus(api, target_domain["municipality"]["id_municipio"], prefix="TRN")

    # 1. Inicia en Caso C: afecta_tuc = NULL, tuc_revision_pendiente = False
    pn = api(
        "POST",
        f"/api/proyectos/{project_id}/nucleos",
        expected=201,
        json={"id_nucleo": nucleus["id_nucleo"], "afecta_tuc": None, "tuc_revision_pendiente": False},
    ).json()
    pn_id = pn["id_proyecto_nucleo"]
    assert _snapshot(api, project_id, "no_afecta_tuc") == []

    # 2. Transición a Caso E: afecta_tuc = False, tuc_revision_pendiente = True
    api(
        "PATCH",
        f"/api/proyecto-nucleo/{pn_id}",
        json={
            "afecta_tuc": False,
            "id_motivo_no_afecta_tuc": reason_tuc,
            "tuc_revision_pendiente": True,
            "tuc_revision_detalle": "Contradicción documental en revisión",
        },
    )
    # Aún no confirmado: no debe aparecer en no_afecta_tuc
    assert _snapshot(api, project_id, "no_afecta_tuc") == []

    # 3. Transición a Caso B: Se resuelve la revisión (tuc_revision_pendiente = False)
    api(
        "PATCH",
        f"/api/proyecto-nucleo/{pn_id}",
        json={
            "tuc_revision_pendiente": False,
            "tuc_revision_detalle": None,
        },
    )
    # Ahora sí confirmado: debe aparecer con cantidad = 1
    snap_b = _snapshot(api, project_id, "no_afecta_tuc")
    assert len(snap_b) == 1
    assert snap_b[0]["cantidad"] == 1

    # 4. Transición a Caso A: Cambia a afecta_tuc = True
    api(
        "PATCH",
        f"/api/proyecto-nucleo/{pn_id}",
        json={
            "afecta_tuc": True,
            "id_motivo_no_afecta_tuc": None,
            "motivo_no_afecta_tuc_detalle": None,
            "tuc_revision_pendiente": False,
        },
    )
    # Ya no es no_afecta_tuc
    assert _snapshot(api, project_id, "no_afecta_tuc") == []


def test_snapshot_directo_vista_sql(api, target_domain):
    """Consulta directa a la vista PostgreSQL vw_reporte_snapshot_actual."""
    reason_tuc = _catalog(api, "motivo_no_afecta_tuc")["no_afectacion_colectiva"]
    project = _create_project(api, prefix="SQL")
    project_id = project["id_proyecto"]
    nucleus = _create_nucleus(api, target_domain["municipality"]["id_municipio"], prefix="SQLN")

    # Crear núcleo con Caso B (confirmado no afecta TUC)
    api(
        "POST",
        f"/api/proyectos/{project_id}/nucleos",
        expected=201,
        json={
            "id_nucleo": nucleus["id_nucleo"],
            "afecta_tuc": False,
            "id_motivo_no_afecta_tuc": reason_tuc,
            "tuc_revision_pendiente": False,
        },
    )

    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                "SELECT id_proyecto, id_entidad, ambito, indicador, cantidad, superficie_ha, monto "
                "FROM vw_reporte_snapshot_actual "
                "WHERE id_proyecto = :pid AND indicador = 'no_afecta_tuc'"
            ),
            {"pid": project_id},
        ).mappings().all()

        assert len(rows) == 1
        r = rows[0]
        assert r["id_proyecto"] == project_id
        assert r["ambito"] == "colectivo"
        assert r["indicador"] == "no_afecta_tuc"
        assert r["cantidad"] == 1
        assert r["superficie_ha"] is None
        assert r["monto"] is None
    finally:
        db.close()
