#!/usr/bin/env python3
"""Auditoría global read-only del laboratorio de migración MEX-QRO.

Objetivo
========
Comprobar el estado final de db_carga_excel después del cierre de las capas
1, 2A–2J y de las reparaciones 2B-R / 2D-R / 2F-R / 2I-B-R.

Este script NO importa ni modifica datos. Ejecuta la transacción en modo
READ ONLY, genera un reporte JSON/CSV y termina con ROLLBACK.

Los checks se dividen en:
- PASS/FAIL: invariantes congeladas y relaciones que deben cumplirse.
- INFO: métricas útiles que no tienen un valor canónico congelado.

Guardas:
- DB_NAME=db_carga_excel
- schema=018
- proyecto MEX-QRO
- SHA-256 exacto del Excel aprobado
- SHA-256 exacto de la resolución final de 2J

Conteos finales congelados
==========================
Capa 1:
- ProyectoNucleo: 74
- ProyectoNucleoReferencia: 74
- ProyectoNucleoResponsable: 51
- PadronHistorial: 63
- ORV: 74
- OrvIntegrante: 417
- PUERTA DE PALMILLAS: 0 ProyectoNucleo

2A:
- ActividadCampo: 155

2B + 2B-R + 2E:
- Asamblea anuencia: 83
- Convocatorias anuencia: 138
- anuencia celebradas: 70
- anuencia sólo programadas: 13
- Asamblea retiro_fondos: 8
- Convocatorias retiro_fondos: 11
- retiro celebradas: 6
- retiro sólo programadas: 2
- total Asambleas: 91
- total Convocatorias: 149

2C:
- Afectacion: 92
- UnidadAgraria activas del proyecto: 96
- UnidadAgraria distintas enlazadas a afectación: 94
- UnidadAgraria independientes sin COP: 2
- AfectacionUnidadAgraria: 123
- enlaces con superficie real: 111
- sin superficie real: 12
- con superficie preliminar: 11
- unidades con requiere_revision=true: 6

2D + 2D-R:
- Convenio: 66
- ConvenioAfectacion: 66
- Convenios con Asamblea autorizante: 46
- Convenios sin Asamblea autorizante: 20

2F + 2F-R:
- TramiteRan: 131
- TramiteRanEvento: 223
- ingreso: 131
- calificacion: 9
- inscripcion: 83
- objetivo Asamblea: 58
- objetivo Convenio: 73

2G:
- TramiteFifonafe: 31
- TramiteFifonafeAfectacion: 31
- TramiteFifonafeEvento: 102
- completo: 16
- pendiente: 15
- eventos: 29/21/27/25 por flujo histórico

2H:
- Indemnizacion pagada: 3
- Pago: 0
- ProyectoNucleo afecta_tuc=false: 2
- NucleoAgrario comunidad_indigena=true: 7

2I-A + 2I-B-R:
- ExpedienteRequisito: 384
- pendiente_validacion: 281
- faltante: 103
- id_documento no NULL: 0
- desglose por requisito:
    oficio_ran_parcelas_afectacion 38
    acta_asamblea                  20
    acta_eleccion_orv              39
    acuse_ran                      65
    col_convenio_firmado           62
    constancia_orv_ran             24
    convocatoria_asamblea          16
    padron                         33
    soporte_caminamiento           43
    soporte_sensibilizacion        44

2J:
- SeguimientoEvento: 17
- reunion: 8
- continuacion_asamblea: 6
- cambio_alcance/nueva_informacion: 2
- medicion_bdt: 1
- ProyectoNucleo targets: 11
- Asamblea targets: 6
- id_documento no NULL: 0

Además se validan duplicados lógicos y pertenencia territorial de relaciones
polimórficas/documentales.

Uso:
  python /app/scripts/auditoria_global_migracion_mq.py \
    /data/mq_colectivos.xlsx \
    --resolution-2j /data/reportes/2j_post_reparaciones/resolucion_seguimiento_post_reparaciones.csv \
    --output-dir /data/reportes/cierre_global

Exit codes:
- 0: auditoría sin FAIL
- 2: uno o más FAIL
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import DB_NAME, SessionLocal  # noqa: E402


EXPECTED_DB = "db_carga_excel"
EXPECTED_SCHEMA = "018"
PROJECT_KEY = "MEX-QRO"

EXPECTED_EXCEL_SHA256 = (
    "bac01c25e9ff963f524fa8a48d69e74d92a0d36578731b1eca91f0e5a3573c3f"
)
EXPECTED_RESOLUTION_2J_SHA256 = (
    "912d05e031a3edd08652fb7adb4a716ec1588137822cf2b998ca51f26e1361ee"
)

EXPECTED_REQUIREMENTS = {
    "oficio_ran_parcelas_afectacion": 38,
    "acta_asamblea": 20,
    "acta_eleccion_orv": 39,
    "acuse_ran": 65,
    "col_convenio_firmado": 62,
    "constancia_orv_ran": 24,
    "convocatoria_asamblea": 16,
    "padron": 33,
    "soporte_caminamiento": 43,
    "soporte_sensibilizacion": 44,
}

EXPECTED_RAN_EVENTS = {
    "ingreso": 131,
    "calificacion": 9,
    "inscripcion": 83,
}

EXPECTED_FIFONAFE_EVENTS = {
    "oficio_fifonafe_dgaopr": 29,
    "oficio_dgaopr_representacion": 21,
    "respuesta_representacion_dgaopr": 27,
    "respuesta_dgaopr_fifonafe": 25,
}

EXPECTED_2J_EVENTS = {
    ("cambio_alcance", "nueva_informacion"): 2,
    ("continuacion_asamblea", ""): 6,
    ("medicion_bdt", ""): 1,
    ("reunion", ""): 8,
}


class AuditAbort(RuntimeError):
    pass


@dataclass
class Check:
    layer: str
    code: str
    status: str
    expected: Any
    actual: Any
    detail: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scalar(db, sql: str, params: dict[str, Any] | None = None) -> Any:
    return db.execute(text(sql), params or {}).scalar()


def rows(db, sql: str, params: dict[str, Any] | None = None):
    return db.execute(text(sql), params or {}).mappings().all()


def add_exact(
    checks: list[Check],
    layer: str,
    code: str,
    actual: Any,
    expected: Any,
    detail: str,
) -> None:
    checks.append(
        Check(
            layer=layer,
            code=code,
            status="PASS" if actual == expected else "FAIL",
            expected=expected,
            actual=actual,
            detail=detail,
        )
    )


def add_zero(
    checks: list[Check],
    layer: str,
    code: str,
    actual: Any,
    detail: str,
) -> None:
    add_exact(checks, layer, code, actual, 0, detail)


def add_info(
    checks: list[Check],
    layer: str,
    code: str,
    actual: Any,
    detail: str,
) -> None:
    checks.append(
        Check(
            layer=layer,
            code=code,
            status="INFO",
            expected=None,
            actual=actual,
            detail=detail,
        )
    )


def project_params(project_id: int) -> dict[str, Any]:
    return {"project_id": project_id}


def validate_expediente_targets(db, project_id: int) -> tuple[int, dict[str, int]]:
    """Valida entidad_tipo/entidad_id contra el mismo ProyectoNucleo.

    Devuelve:
    - número de objetivos inválidos;
    - distribución observada por entidad_tipo.
    """
    reqs = rows(
        db,
        """
        SELECT
            er.id_expediente_requisito,
            er.id_proyecto_nucleo,
            pn.id_nucleo,
            er.entidad_tipo,
            er.entidad_id
        FROM expediente_requisito er
        JOIN proyecto_nucleo pn
          ON pn.id_proyecto_nucleo = er.id_proyecto_nucleo
        WHERE er.activo IS TRUE
          AND pn.activo IS TRUE
          AND pn.id_proyecto = :project_id
        ORDER BY er.id_expediente_requisito
        """,
        project_params(project_id),
    )

    pn_by_id = {
        row["id_proyecto_nucleo"]: row["id_nucleo"]
        for row in rows(
            db,
            """
            SELECT id_proyecto_nucleo, id_nucleo
            FROM proyecto_nucleo
            WHERE activo IS TRUE
              AND id_proyecto = :project_id
            """,
            project_params(project_id),
        )
    }

    affectation = {
        row["id_afectacion"]: row["id_proyecto_nucleo"]
        for row in rows(
            db,
            """
            SELECT id_afectacion, id_proyecto_nucleo
            FROM afectacion
            WHERE activo IS TRUE
              AND id_proyecto_nucleo IN (
                    SELECT id_proyecto_nucleo
                    FROM proyecto_nucleo
                    WHERE activo IS TRUE
                      AND id_proyecto = :project_id
              )
            """,
            project_params(project_id),
        )
    }
    activity = {
        row["id_actividad"]: row["id_proyecto_nucleo"]
        for row in rows(
            db,
            """
            SELECT id_actividad, id_proyecto_nucleo
            FROM actividad_campo
            WHERE activo IS TRUE
              AND id_proyecto_nucleo IN (
                    SELECT id_proyecto_nucleo
                    FROM proyecto_nucleo
                    WHERE activo IS TRUE
                      AND id_proyecto = :project_id
              )
            """,
            project_params(project_id),
        )
    }
    assembly = {
        row["id_asamblea"]: row["id_proyecto_nucleo"]
        for row in rows(
            db,
            """
            SELECT id_asamblea, id_proyecto_nucleo
            FROM asamblea
            WHERE activo IS TRUE
              AND id_proyecto_nucleo IN (
                    SELECT id_proyecto_nucleo
                    FROM proyecto_nucleo
                    WHERE activo IS TRUE
                      AND id_proyecto = :project_id
              )
            """,
            project_params(project_id),
        )
    }
    convocation = {
        row["id_convocatoria"]: row["id_proyecto_nucleo"]
        for row in rows(
            db,
            """
            SELECT ac.id_convocatoria, a.id_proyecto_nucleo
            FROM asamblea_convocatoria ac
            JOIN asamblea a ON a.id_asamblea = ac.id_asamblea
            WHERE ac.activo IS TRUE
              AND a.activo IS TRUE
              AND a.id_proyecto_nucleo IN (
                    SELECT id_proyecto_nucleo
                    FROM proyecto_nucleo
                    WHERE activo IS TRUE
                      AND id_proyecto = :project_id
              )
            """,
            project_params(project_id),
        )
    }
    convenio = {
        row["id_convenio"]: row["id_proyecto_nucleo"]
        for row in rows(
            db,
            """
            SELECT id_convenio, id_proyecto_nucleo
            FROM convenio
            WHERE activo IS TRUE
              AND id_proyecto_nucleo IN (
                    SELECT id_proyecto_nucleo
                    FROM proyecto_nucleo
                    WHERE activo IS TRUE
                      AND id_proyecto = :project_id
              )
            """,
            project_params(project_id),
        )
    }
    orv = {
        row["id_orv"]: row["id_nucleo"]
        for row in rows(
            db,
            """
            SELECT o.id_orv, o.id_nucleo
            FROM orv o
            WHERE o.activo IS TRUE
              AND o.id_nucleo IN (
                    SELECT id_nucleo
                    FROM proyecto_nucleo
                    WHERE activo IS TRUE
                      AND id_proyecto = :project_id
              )
            """,
            project_params(project_id),
        )
    }
    padron = {
        row["id_padron"]: row["id_nucleo"]
        for row in rows(
            db,
            """
            SELECT ph.id_padron, ph.id_nucleo
            FROM padron_historial ph
            WHERE ph.activo IS TRUE
              AND ph.id_nucleo IN (
                    SELECT id_nucleo
                    FROM proyecto_nucleo
                    WHERE activo IS TRUE
                      AND id_proyecto = :project_id
              )
            """,
            project_params(project_id),
        )
    }
    ran_event = {
        row["id_evento_ran"]: (
            row["id_proyecto_nucleo"],
            row["id_nucleo"],
        )
        for row in rows(
            db,
            """
            SELECT tre.id_evento_ran,
                   tr.id_proyecto_nucleo,
                   tr.id_nucleo
            FROM tramite_ran_evento tre
            JOIN tramite_ran tr
              ON tr.id_tramite_ran = tre.id_tramite_ran
            WHERE tre.activo IS TRUE
              AND tr.activo IS TRUE
              AND tr.id_proyecto_nucleo IN (
                    SELECT id_proyecto_nucleo
                    FROM proyecto_nucleo
                    WHERE activo IS TRUE
                      AND id_proyecto = :project_id
              )
            """,
            project_params(project_id),
        )
    }

    invalid = 0
    distribution: dict[str, int] = {}

    for req in reqs:
        entity_type = req["entidad_tipo"]
        entity_id = req["entidad_id"]
        pn_id = req["id_proyecto_nucleo"]
        nucleus_id = req["id_nucleo"]

        distribution[entity_type] = distribution.get(entity_type, 0) + 1
        valid = False

        if entity_type == "afectacion":
            valid = affectation.get(entity_id) == pn_id
        elif entity_type == "actividad_campo":
            valid = activity.get(entity_id) == pn_id
        elif entity_type == "asamblea":
            valid = assembly.get(entity_id) == pn_id
        elif entity_type == "asamblea_convocatoria":
            valid = convocation.get(entity_id) == pn_id
        elif entity_type == "convenio":
            valid = convenio.get(entity_id) == pn_id
        elif entity_type == "orv":
            valid = orv.get(entity_id) == nucleus_id
        elif entity_type == "padron_historial":
            valid = padron.get(entity_id) == nucleus_id
        elif entity_type == "tramite_ran_evento":
            target = ran_event.get(entity_id)
            if target is not None:
                target_pn, target_nucleus = target
                valid = (
                    target_pn == pn_id
                    if target_pn is not None
                    else target_nucleus == nucleus_id
                )

        if not valid:
            invalid += 1

    return invalid, dict(sorted(distribution.items()))


def validate_seguimiento_targets(db, project_id: int) -> int:
    invalid = scalar(
        db,
        """
        SELECT COUNT(*)
        FROM seguimiento_evento se
        JOIN proyecto_nucleo pn
          ON pn.id_proyecto_nucleo = se.id_proyecto_nucleo
        LEFT JOIN asamblea a
          ON se.entidad_tipo = 'asamblea'
         AND a.id_asamblea = se.entidad_id
         AND a.activo IS TRUE
        WHERE se.activo IS TRUE
          AND pn.activo IS TRUE
          AND pn.id_proyecto = :project_id
          AND (
                (se.entidad_tipo = 'proyecto_nucleo'
                 AND se.entidad_id <> se.id_proyecto_nucleo)
             OR (se.entidad_tipo = 'asamblea'
                 AND (
                        a.id_asamblea IS NULL
                     OR a.id_proyecto_nucleo <> se.id_proyecto_nucleo
                 ))
             OR se.entidad_tipo NOT IN ('proyecto_nucleo', 'asamblea')
          )
        """,
        project_params(project_id),
    )
    return int(invalid or 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("excel", type=Path)
    parser.add_argument(
        "--resolution-2j",
        type=Path,
        default=Path(
            "/data/reportes/2j_post_reparaciones/"
            "resolucion_seguimiento_post_reparaciones.csv"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/reportes/cierre_global"),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Imprime todos los checks, no sólo resumen y FAIL/INFO.",
    )
    args = parser.parse_args()

    if DB_NAME != EXPECTED_DB:
        raise AuditAbort(
            f"Protección: DB_NAME debe ser {EXPECTED_DB!r}; recibido={DB_NAME!r}."
        )
    if not args.excel.exists():
        raise AuditAbort(f"No existe el Excel: {args.excel}.")
    if not args.resolution_2j.exists():
        raise AuditAbort(
            f"No existe la resolución final 2J: {args.resolution_2j}."
        )

    excel_sha = sha256_file(args.excel)
    resolution_sha = sha256_file(args.resolution_2j)

    if excel_sha != EXPECTED_EXCEL_SHA256:
        raise AuditAbort(
            "SHA-256 del Excel no coincide. "
            f"Esperado={EXPECTED_EXCEL_SHA256}, actual={excel_sha}."
        )
    if resolution_sha != EXPECTED_RESOLUTION_2J_SHA256:
        raise AuditAbort(
            "SHA-256 de resolución 2J no coincide. "
            f"Esperado={EXPECTED_RESOLUTION_2J_SHA256}, actual={resolution_sha}."
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "auditoria_global_migracion_mq.json"
    csv_path = args.output_dir / "auditoria_global_migracion_mq.csv"

    db = SessionLocal()
    checks: list[Check] = []

    try:
        # La primera sentencia de la transacción la vuelve explícitamente READ ONLY.
        db.execute(text("SET TRANSACTION READ ONLY"))

        current_db = scalar(db, "SELECT current_database()")
        schema = scalar(db, "SELECT max(version) FROM schema_migrations")

        if current_db != EXPECTED_DB or str(schema) != EXPECTED_SCHEMA:
            raise AuditAbort(
                f"Destino inesperado: BD={current_db!r}, schema={schema!r}."
            )

        project_rows = rows(
            db,
            """
            SELECT id_proyecto
            FROM proyecto
            WHERE clave_proyecto = :project_key
              AND activo IS TRUE
            """,
            {"project_key": PROJECT_KEY},
        )
        if len(project_rows) != 1:
            raise AuditAbort(
                f"Se esperaba un proyecto activo {PROJECT_KEY}; hay {len(project_rows)}."
            )
        project_id = project_rows[0]["id_proyecto"]
        p = project_params(project_id)

        # ------------------------------------------------------------------
        # ENTORNO / ARTEFACTOS
        # ------------------------------------------------------------------
        add_exact(checks, "00_ENTORNO", "database", current_db, EXPECTED_DB,
                  "Base exclusiva del laboratorio.")
        add_exact(checks, "00_ENTORNO", "schema", str(schema), EXPECTED_SCHEMA,
                  "Versión de esquema congelada.")
        add_exact(checks, "00_ENTORNO", "excel_sha256", excel_sha,
                  EXPECTED_EXCEL_SHA256, "Excel aprobado.")
        add_exact(checks, "00_ENTORNO", "resolution_2j_sha256", resolution_sha,
                  EXPECTED_RESOLUTION_2J_SHA256,
                  "Resolución final 2J congelada.")

        # ------------------------------------------------------------------
        # CAPA 1
        # ------------------------------------------------------------------
        pn_count = scalar(db, """
            SELECT COUNT(*) FROM proyecto_nucleo
            WHERE activo IS TRUE AND id_proyecto=:project_id
        """, p)
        add_exact(checks, "01_BASE", "proyecto_nucleo", pn_count, 74,
                  "Núcleos del proyecto importados.")

        nuclei_count = scalar(db, """
            SELECT COUNT(DISTINCT id_nucleo) FROM proyecto_nucleo
            WHERE activo IS TRUE AND id_proyecto=:project_id
        """, p)
        add_exact(checks, "01_BASE", "nucleos_distintos", nuclei_count, 74,
                  "Un núcleo agrario por ProyectoNucleo.")

        duplicate_pn = scalar(db, """
            SELECT COUNT(*) FROM (
                SELECT id_nucleo
                FROM proyecto_nucleo
                WHERE activo IS TRUE AND id_proyecto=:project_id
                GROUP BY id_nucleo
                HAVING COUNT(*) > 1
            ) q
        """, p)
        add_zero(checks, "01_BASE", "duplicados_proyecto_nucleo", duplicate_pn,
                 "No debe repetirse un núcleo dentro de MEX-QRO.")

        references = scalar(db, """
            SELECT COUNT(*)
            FROM proyecto_nucleo_referencia r
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=r.id_proyecto_nucleo
            WHERE r.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "01_BASE", "referencias", references, 74,
                  "ProyectoNucleoReferencia.")

        responsibles = scalar(db, """
            SELECT COUNT(*)
            FROM proyecto_nucleo_responsable r
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=r.id_proyecto_nucleo
            WHERE r.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "01_BASE", "responsables", responsibles, 51,
                  "Responsables importados.")

        padrones = scalar(db, """
            SELECT COUNT(*)
            FROM padron_historial ph
            WHERE ph.activo IS TRUE
              AND ph.id_nucleo IN (
                  SELECT id_nucleo FROM proyecto_nucleo
                  WHERE activo IS TRUE AND id_proyecto=:project_id
              )
        """, p)
        add_exact(checks, "01_BASE", "padrones", padrones, 63,
                  "Padrones de hoja ORV.")

        orvs = scalar(db, """
            SELECT COUNT(*)
            FROM orv o
            WHERE o.activo IS TRUE
              AND o.id_nucleo IN (
                  SELECT id_nucleo FROM proyecto_nucleo
                  WHERE activo IS TRUE AND id_proyecto=:project_id
              )
        """, p)
        add_exact(checks, "01_BASE", "orv", orvs, 74,
                  "Un ORV activo por núcleo importado.")

        # Orv.activo es el borrado lógico del registro, no equivale a
        # "vigente hoy". La capa base preserva inicio_vigencia/fin_vigencia
        # directamente desde L/M de la hoja ORV. En el Excel aprobado hay
        # 71 filas con fin_vigencia; PUERTA DE PALMILLAS es una de ellas y
        # se omite por tenencia, por lo que quedan 70 ORV importados con fin.
        orv_with_end = scalar(db, """
            SELECT COUNT(*)
            FROM orv o
            WHERE o.activo IS TRUE
              AND o.fin_vigencia IS NOT NULL
              AND o.id_nucleo IN (
                  SELECT id_nucleo FROM proyecto_nucleo
                  WHERE activo IS TRUE AND id_proyecto=:project_id
              )
        """, p)
        add_exact(checks, "01_BASE", "orv_con_fin_vigencia",
                  orv_with_end, 70,
                  "fin_vigencia se preserva desde la columna M de ORV.")

        orv_without_end = scalar(db, """
            SELECT COUNT(*)
            FROM orv o
            WHERE o.activo IS TRUE
              AND o.fin_vigencia IS NULL
              AND o.id_nucleo IN (
                  SELECT id_nucleo FROM proyecto_nucleo
                  WHERE activo IS TRUE AND id_proyecto=:project_id
              )
        """, p)
        add_exact(checks, "01_BASE", "orv_sin_fin_vigencia",
                  orv_without_end, 4,
                  "Cuatro filas ORV importadas no traen fin de vigencia.")

        orv_bad_period = scalar(db, """
            SELECT COUNT(*)
            FROM orv o
            WHERE o.activo IS TRUE
              AND o.inicio_vigencia IS NOT NULL
              AND o.fin_vigencia IS NOT NULL
              AND o.fin_vigencia < o.inicio_vigencia
              AND o.id_nucleo IN (
                  SELECT id_nucleo FROM proyecto_nucleo
                  WHERE activo IS TRUE AND id_proyecto=:project_id
              )
        """, p)
        add_zero(checks, "01_BASE", "orv_periodo_invertido",
                 orv_bad_period,
                 "fin_vigencia no puede ser anterior a inicio_vigencia.")

        duplicate_orv = scalar(db, """
            SELECT COUNT(*) FROM (
                SELECT o.id_nucleo
                FROM orv o
                WHERE o.activo IS TRUE
                  AND o.id_nucleo IN (
                      SELECT id_nucleo FROM proyecto_nucleo
                      WHERE activo IS TRUE AND id_proyecto=:project_id
                  )
                GROUP BY o.id_nucleo
                HAVING COUNT(*) > 1
            ) q
        """, p)
        add_zero(checks, "01_BASE", "nucleos_con_multiples_orv_activos",
                 duplicate_orv, "No debe haber ORV activo duplicado por núcleo.")

        members = scalar(db, """
            SELECT COUNT(*)
            FROM orv_integrante oi
            JOIN orv o ON o.id_orv=oi.id_orv
            WHERE oi.activo IS TRUE AND o.activo IS TRUE
              AND o.id_nucleo IN (
                  SELECT id_nucleo FROM proyecto_nucleo
                  WHERE activo IS TRUE AND id_proyecto=:project_id
              )
        """, p)
        add_exact(checks, "01_BASE", "orv_integrantes", members, 417,
                  "Slots ORV deterministas; persona ambigua fue omitida.")

        member_end = scalar(db, """
            SELECT COUNT(*)
            FROM orv_integrante oi
            JOIN orv o ON o.id_orv=oi.id_orv
            WHERE oi.activo IS TRUE AND o.activo IS TRUE
              AND oi.fecha_fin IS NOT NULL
              AND o.id_nucleo IN (
                  SELECT id_nucleo FROM proyecto_nucleo
                  WHERE activo IS TRUE AND id_proyecto=:project_id
              )
        """, p)
        add_zero(checks, "01_BASE", "orv_integrantes_activos_con_fecha_fin",
                 member_end, "Integrantes activos importados no tienen fecha_fin.")

        palmillas = scalar(db, """
            SELECT COUNT(*)
            FROM proyecto_nucleo pn
            JOIN nucleo_agrario na ON na.id_nucleo=pn.id_nucleo
            WHERE pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND UPPER(na.nombre_nucleo)='PUERTA DE PALMILLAS'
        """, p)
        add_zero(checks, "01_BASE", "puerta_de_palmillas_proyecto_nucleo",
                 palmillas,
                 "Omisión deliberada por tenencia vacía.")

        people = scalar(db, """
            SELECT COUNT(DISTINCT oi.id_persona)
            FROM orv_integrante oi
            JOIN orv o ON o.id_orv=oi.id_orv
            WHERE oi.activo IS TRUE AND o.activo IS TRUE
              AND o.id_nucleo IN (
                  SELECT id_nucleo FROM proyecto_nucleo
                  WHERE activo IS TRUE AND id_proyecto=:project_id
              )
        """, p)
        add_info(checks, "01_BASE", "personas_distintas_en_orv", people,
                 "Métrica informativa; no se congeló conteo global de Persona.")

        # ------------------------------------------------------------------
        # 2A
        # ------------------------------------------------------------------
        activities = scalar(db, """
            SELECT COUNT(*)
            FROM actividad_campo ac
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=ac.id_proyecto_nucleo
            WHERE ac.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "02A_ACTIVIDADES", "actividad_campo", activities, 155,
                  "Sensibilización + caminamiento.")

        invalid_activity_type = scalar(db, """
            SELECT COUNT(*)
            FROM actividad_campo ac
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=ac.id_proyecto_nucleo
            WHERE ac.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND ac.tipo_actividad NOT IN ('sensibilizacion','caminamiento')
        """, p)
        add_zero(checks, "02A_ACTIVIDADES", "tipos_fuera_plan",
                 invalid_activity_type,
                 "Sólo se migraron sensibilización y caminamiento.")

        # ------------------------------------------------------------------
        # 2C
        # ------------------------------------------------------------------
        affectations = scalar(db, """
            SELECT COUNT(*)
            FROM afectacion a
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            WHERE a.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "02C_AFECTACIONES", "afectaciones", affectations, 92,
                  "Afectaciones colectivas.")

        # La capa 2C crea 96 UnidadAgraria. Dos son deliberadamente
        # independientes porque su fuente tiene J/K/L pero M (COP) vacío:
        # LA ESTANCIA, filas 63 (P-2) y 64 (P-216). Sin COP no se crea
        # Afectacion ni AfectacionUnidadAgraria para esas unidades.
        total_units = scalar(db, """
            SELECT COUNT(*)
            FROM unidad_agraria ua
            WHERE ua.activo IS TRUE
              AND ua.id_nucleo IN (
                  SELECT id_nucleo FROM proyecto_nucleo
                  WHERE activo IS TRUE AND id_proyecto=:project_id
              )
        """, p)
        add_exact(checks, "02C_AFECTACIONES", "unidades_agrarias_total",
                  total_units, 96,
                  "Total de UnidadAgraria creadas/reutilizadas por el plan 2C.")

        linked_units = scalar(db, """
            SELECT COUNT(DISTINCT aua.id_unidad_agraria)
            FROM afectacion_unidad_agraria aua
            JOIN afectacion a ON a.id_afectacion=aua.id_afectacion
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            WHERE aua.activo IS TRUE AND a.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "02C_AFECTACIONES", "unidades_agrarias_enlazadas",
                  linked_units, 94,
                  "Dos de las 96 unidades son independientes por COP vacío.")

        independent_units = scalar(db, """
            SELECT COUNT(*)
            FROM unidad_agraria ua
            WHERE ua.activo IS TRUE
              AND ua.id_nucleo IN (
                  SELECT id_nucleo FROM proyecto_nucleo
                  WHERE activo IS TRUE AND id_proyecto=:project_id
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM afectacion_unidad_agraria aua
                  JOIN afectacion a
                    ON a.id_afectacion=aua.id_afectacion
                  JOIN proyecto_nucleo pn
                    ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
                  WHERE aua.activo IS TRUE
                    AND a.activo IS TRUE
                    AND pn.activo IS TRUE
                    AND pn.id_proyecto=:project_id
                    AND aua.id_unidad_agraria=ua.id_unidad_agraria
              )
        """, p)
        add_exact(checks, "02C_AFECTACIONES", "unidades_independientes",
                  independent_units, 2,
                  "M vacío permite UnidadAgraria, pero no Afectacion ni enlace.")

        independent_expected = scalar(db, """
            SELECT COUNT(*)
            FROM unidad_agraria ua
            JOIN nucleo_agrario na ON na.id_nucleo=ua.id_nucleo
            JOIN proyecto_nucleo pn ON pn.id_nucleo=na.id_nucleo
            WHERE ua.activo IS TRUE
              AND na.activo IS TRUE
              AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND UPPER(na.nombre_nucleo)='LA ESTANCIA'
              AND ua.referencia_alfanumerica IN ('P-2','P-216')
              AND NOT EXISTS (
                  SELECT 1
                  FROM afectacion_unidad_agraria aua
                  JOIN afectacion a
                    ON a.id_afectacion=aua.id_afectacion
                  JOIN proyecto_nucleo pn2
                    ON pn2.id_proyecto_nucleo=a.id_proyecto_nucleo
                  WHERE aua.activo IS TRUE
                    AND a.activo IS TRUE
                    AND pn2.activo IS TRUE
                    AND pn2.id_proyecto=:project_id
                    AND aua.id_unidad_agraria=ua.id_unidad_agraria
              )
        """, p)
        add_exact(checks, "02C_AFECTACIONES",
                  "unidades_independientes_la_estancia",
                  independent_expected, 2,
                  "Trazabilidad fuente: filas 63/P-2 y 64/P-216.")

        affectation_links = scalar(db, """
            SELECT COUNT(*)
            FROM afectacion_unidad_agraria aua
            JOIN afectacion a ON a.id_afectacion=aua.id_afectacion
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            WHERE aua.activo IS TRUE AND a.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "02C_AFECTACIONES", "afectacion_unidad_agraria",
                  affectation_links, 123, "Relaciones Afectacion-Unidad.")

        parent_surfaces = scalar(db, """
            SELECT COUNT(*)
            FROM afectacion a
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            WHERE a.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND (
                   a.superficie_preliminar_ha IS NOT NULL
                OR a.superficie_afectada_ha IS NOT NULL
              )
        """, p)
        add_zero(checks, "02C_AFECTACIONES", "superficie_en_padre",
                 parent_surfaces,
                 "La superficie física vive en AfectacionUnidadAgraria.")

        real_surface = scalar(db, """
            SELECT COUNT(*)
            FROM afectacion_unidad_agraria aua
            JOIN afectacion a ON a.id_afectacion=aua.id_afectacion
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            WHERE aua.activo IS TRUE AND a.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
              AND aua.superficie_afectada_ha IS NOT NULL
        """, p)
        add_exact(checks, "02C_AFECTACIONES", "links_superficie_real",
                  real_surface, 111, "BO canónica.")

        no_real_surface = affectation_links - real_surface
        add_exact(checks, "02C_AFECTACIONES", "links_sin_superficie_real",
                  no_real_surface, 12,
                  "Ausencias preservadas; no se inventó superficie.")

        prelim_surface = scalar(db, """
            SELECT COUNT(*)
            FROM afectacion_unidad_agraria aua
            JOIN afectacion a ON a.id_afectacion=aua.id_afectacion
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            WHERE aua.activo IS TRUE AND a.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
              AND aua.superficie_preliminar_ha IS NOT NULL
        """, p)
        add_exact(checks, "02C_AFECTACIONES", "links_superficie_preliminar",
                  prelim_surface, 11, "BL preliminar.")

        review_units = scalar(db, """
            SELECT COUNT(DISTINCT ua.id_unidad_agraria)
            FROM unidad_agraria ua
            JOIN afectacion_unidad_agraria aua
              ON aua.id_unidad_agraria=ua.id_unidad_agraria
            JOIN afectacion a ON a.id_afectacion=aua.id_afectacion
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            WHERE ua.activo IS TRUE AND aua.activo IS TRUE
              AND a.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND ua.requiere_revision IS TRUE
        """, p)
        add_exact(checks, "02C_AFECTACIONES", "unidades_revision",
                  review_units, 6, "Revisión explícita preservada.")

        bad_unit_nucleus = scalar(db, """
            SELECT COUNT(*)
            FROM afectacion_unidad_agraria aua
            JOIN afectacion a ON a.id_afectacion=aua.id_afectacion
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            JOIN unidad_agraria ua
              ON ua.id_unidad_agraria=aua.id_unidad_agraria
            WHERE aua.activo IS TRUE AND a.activo IS TRUE
              AND pn.activo IS TRUE AND ua.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND ua.id_nucleo <> pn.id_nucleo
        """, p)
        add_zero(checks, "02C_AFECTACIONES", "unidad_otro_nucleo",
                 bad_unit_nucleus,
                 "UnidadAgraria debe pertenecer al núcleo de la afectación.")

        duplicate_aff_unit = scalar(db, """
            SELECT COUNT(*) FROM (
                SELECT aua.id_afectacion, aua.id_unidad_agraria
                FROM afectacion_unidad_agraria aua
                JOIN afectacion a ON a.id_afectacion=aua.id_afectacion
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
                WHERE aua.activo IS TRUE AND a.activo IS TRUE
                  AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
                GROUP BY aua.id_afectacion, aua.id_unidad_agraria
                HAVING COUNT(*) > 1
            ) q
        """, p)
        add_zero(checks, "02C_AFECTACIONES", "duplicados_afectacion_unidad",
                 duplicate_aff_unit, "No debe repetirse el mismo enlace activo.")

        # ------------------------------------------------------------------
        # 2B / 2B-R / 2E
        # ------------------------------------------------------------------
        assembly_counts = rows(db, """
            SELECT co.codigo, COUNT(*) AS total
            FROM asamblea a
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            JOIN catalogo_operativo co
              ON co.id_catalogo_opcion=a.id_tipo_asamblea
            WHERE a.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND co.tipo_catalogo='tipo_asamblea'
            GROUP BY co.codigo
        """, p)
        assembly_by_type = {r["codigo"]: r["total"] for r in assembly_counts}
        add_exact(checks, "02B_02E_ASAMBLEAS", "anuencia",
                  assembly_by_type.get("anuencia", 0), 83,
                  "75 originales + 8 de 2B-R.")
        add_exact(checks, "02B_02E_ASAMBLEAS", "retiro_fondos",
                  assembly_by_type.get("retiro_fondos", 0), 8,
                  "Asambleas de retiro de fondos.")
        add_exact(checks, "02B_02E_ASAMBLEAS", "asambleas_total",
                  sum(assembly_by_type.values()), 91,
                  "Sólo tipos importados por estas capas.")

        conv_counts = rows(db, """
            SELECT co.codigo, COUNT(*) AS total
            FROM asamblea_convocatoria ac
            JOIN asamblea a ON a.id_asamblea=ac.id_asamblea
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            JOIN catalogo_operativo co
              ON co.id_catalogo_opcion=a.id_tipo_asamblea
            WHERE ac.activo IS TRUE AND a.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
              AND co.tipo_catalogo='tipo_asamblea'
            GROUP BY co.codigo
        """, p)
        conv_by_type = {r["codigo"]: r["total"] for r in conv_counts}
        add_exact(checks, "02B_02E_ASAMBLEAS", "convocatorias_anuencia",
                  conv_by_type.get("anuencia", 0), 138,
                  "125 originales + 13 de 2B-R.")
        add_exact(checks, "02B_02E_ASAMBLEAS", "convocatorias_retiro",
                  conv_by_type.get("retiro_fondos", 0), 11,
                  "Convocatorias de retiro.")
        add_exact(checks, "02B_02E_ASAMBLEAS", "convocatorias_total",
                  sum(conv_by_type.values()), 149, "Total activo.")

        realized = rows(db, """
            SELECT co.codigo, COUNT(DISTINCT a.id_asamblea) AS total
            FROM asamblea a
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            JOIN catalogo_operativo co
              ON co.id_catalogo_opcion=a.id_tipo_asamblea
            JOIN asamblea_convocatoria ac
              ON ac.id_asamblea=a.id_asamblea
            WHERE a.activo IS TRUE AND ac.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
              AND ac.fecha_realizacion IS NOT NULL
            GROUP BY co.codigo
        """, p)
        realized_by_type = {r["codigo"]: r["total"] for r in realized}
        add_exact(checks, "02B_02E_ASAMBLEAS", "anuencia_realizada",
                  realized_by_type.get("anuencia", 0), 70,
                  "63 originales + 7 de 2B-R.")
        add_exact(checks, "02B_02E_ASAMBLEAS", "retiro_realizada",
                  realized_by_type.get("retiro_fondos", 0), 6,
                  "Asambleas retiro celebradas.")

        programmed_only_anuencia = (
            assembly_by_type.get("anuencia", 0)
            - realized_by_type.get("anuencia", 0)
        )
        programmed_only_retiro = (
            assembly_by_type.get("retiro_fondos", 0)
            - realized_by_type.get("retiro_fondos", 0)
        )
        add_exact(checks, "02B_02E_ASAMBLEAS", "anuencia_solo_programada",
                  programmed_only_anuencia, 13, "12 originales + 1 de 2B-R.")
        add_exact(checks, "02B_02E_ASAMBLEAS", "retiro_solo_programada",
                  programmed_only_retiro, 2, "Capa 2E.")

        duplicate_conv = scalar(db, """
            SELECT COUNT(*) FROM (
                SELECT ac.id_asamblea, ac.ordinal
                FROM asamblea_convocatoria ac
                JOIN asamblea a ON a.id_asamblea=ac.id_asamblea
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
                WHERE ac.activo IS TRUE AND a.activo IS TRUE
                  AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
                GROUP BY ac.id_asamblea, ac.ordinal
                HAVING COUNT(*) > 1
            ) q
        """, p)
        add_zero(checks, "02B_02E_ASAMBLEAS", "convocatoria_ordinal_duplicado",
                 duplicate_conv,
                 "No debe haber dos convocatorias activas con mismo ordinal.")

        conv_docs = scalar(db, """
            SELECT COUNT(*)
            FROM asamblea_convocatoria ac
            JOIN asamblea a ON a.id_asamblea=ac.id_asamblea
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            WHERE ac.activo IS TRUE AND a.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
              AND ac.id_documento IS NOT NULL
        """, p)
        add_zero(checks, "02B_02E_ASAMBLEAS", "documentos_convocatoria",
                 conv_docs, "No se inventaron archivos digitales.")

        retiro_cop = scalar(db, """
            SELECT COUNT(*)
            FROM asamblea a
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            JOIN catalogo_operativo co
              ON co.id_catalogo_opcion=a.id_tipo_asamblea
            WHERE a.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND co.tipo_catalogo='tipo_asamblea'
              AND co.codigo='retiro_fondos'
              AND a.id_tipo_cop_operativo IS NOT NULL
        """, p)
        add_zero(checks, "02B_02E_ASAMBLEAS", "retiro_con_tipo_cop",
                 retiro_cop, "Retiro de fondos debe tener id_tipo_cop_operativo NULL.")

        repair_assemblies = scalar(db, """
            SELECT COUNT(*)
            FROM asamblea a
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            WHERE a.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND a.observaciones LIKE 'Reparación migratoria 2B-R%'
        """, p)
        add_exact(checks, "02B_02E_ASAMBLEAS", "asambleas_2b_r",
                  repair_assemblies, 8, "Reparación focal 2B-R.")

        # ------------------------------------------------------------------
        # 2D / 2D-R
        # ------------------------------------------------------------------
        convenios = scalar(db, """
            SELECT COUNT(*)
            FROM convenio c
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=c.id_proyecto_nucleo
            WHERE c.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "02D_CONVENIOS", "convenios", convenios, 66,
                  "Convenios colectivos deterministas.")

        convenio_links = scalar(db, """
            SELECT COUNT(*)
            FROM convenio_afectacion ca
            JOIN convenio c ON c.id_convenio=ca.id_convenio
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=c.id_proyecto_nucleo
            WHERE ca.activo IS TRUE AND c.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "02D_CONVENIOS", "convenio_afectacion",
                  convenio_links, 66, "Un enlace principal por convenio.")

        convenio_with_assembly = scalar(db, """
            SELECT COUNT(*)
            FROM convenio c
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=c.id_proyecto_nucleo
            WHERE c.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND c.id_asamblea_autorizacion IS NOT NULL
        """, p)
        add_exact(checks, "02D_CONVENIOS", "con_asamblea",
                  convenio_with_assembly, 46, "42 originales + 4 de 2D-R.")
        add_exact(checks, "02D_CONVENIOS", "sin_asamblea",
                  convenios - convenio_with_assembly, 20,
                  "Casos que siguen sin correspondencia única.")

        bad_convenio_assembly = scalar(db, """
            SELECT COUNT(*)
            FROM convenio c
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=c.id_proyecto_nucleo
            JOIN asamblea a ON a.id_asamblea=c.id_asamblea_autorizacion
            WHERE c.activo IS TRUE AND pn.activo IS TRUE
              AND a.activo IS TRUE AND pn.id_proyecto=:project_id
              AND c.id_asamblea_autorizacion IS NOT NULL
              AND a.id_proyecto_nucleo <> c.id_proyecto_nucleo
        """, p)
        add_zero(checks, "02D_CONVENIOS", "asamblea_otro_proyecto_nucleo",
                 bad_convenio_assembly,
                 "Convenio y Asamblea autorizante deben pertenecer al mismo PN.")

        bad_convenio_affect = scalar(db, """
            SELECT COUNT(*)
            FROM convenio_afectacion ca
            JOIN convenio c ON c.id_convenio=ca.id_convenio
            JOIN afectacion a ON a.id_afectacion=ca.id_afectacion
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=c.id_proyecto_nucleo
            WHERE ca.activo IS TRUE AND c.activo IS TRUE AND a.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
              AND a.id_proyecto_nucleo <> c.id_proyecto_nucleo
        """, p)
        add_zero(checks, "02D_CONVENIOS", "afectacion_otro_proyecto_nucleo",
                 bad_convenio_affect,
                 "ConvenioAfectacion no puede cruzar ProyectoNucleo.")

        bad_link_cardinality = scalar(db, """
            SELECT COUNT(*) FROM (
                SELECT c.id_convenio, COUNT(ca.id_convenio_afectacion) AS n
                FROM convenio c
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=c.id_proyecto_nucleo
                LEFT JOIN convenio_afectacion ca
                  ON ca.id_convenio=c.id_convenio AND ca.activo IS TRUE
                WHERE c.activo IS TRUE AND pn.activo IS TRUE
                  AND pn.id_proyecto=:project_id
                GROUP BY c.id_convenio
                HAVING COUNT(ca.id_convenio_afectacion) <> 1
            ) q
        """, p)
        add_zero(checks, "02D_CONVENIOS", "cardinalidad_afectacion",
                 bad_link_cardinality,
                 "Cada convenio importado tiene exactamente una afectación.")

        convenio_effect = scalar(db, """
            SELECT COUNT(*)
            FROM convenio c
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=c.id_proyecto_nucleo
            WHERE c.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND c.efecto_monto <> 'pendiente'
        """, p)
        add_zero(checks, "02D_CONVENIOS", "efecto_monto_no_pendiente",
                 convenio_effect, "No se inventó efecto monetario.")

        surface_effect = scalar(db, """
            SELECT COUNT(*)
            FROM convenio_afectacion ca
            JOIN convenio c ON c.id_convenio=ca.id_convenio
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=c.id_proyecto_nucleo
            WHERE ca.activo IS TRUE AND c.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
              AND ca.efecto_superficie <> 'pendiente'
        """, p)
        add_zero(checks, "02D_CONVENIOS", "efecto_superficie_no_pendiente",
                 surface_effect, "No se inventó efecto de superficie.")

        # ------------------------------------------------------------------
        # 2F / 2F-R
        # ------------------------------------------------------------------
        ran_total = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_ran tr
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tr.id_proyecto_nucleo
            WHERE tr.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "02F_RAN", "tramite_ran", ran_total, 131,
                  "123 originales + 8 de 2F-R.")

        ran_events = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_ran_evento tre
            JOIN tramite_ran tr ON tr.id_tramite_ran=tre.id_tramite_ran
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tr.id_proyecto_nucleo
            WHERE tre.activo IS TRUE AND tr.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "02F_RAN", "tramite_ran_evento", ran_events, 223,
                  "208 originales + 15 de 2F-R.")

        ran_by_type = {
            r["codigo"]: r["total"]
            for r in rows(db, """
                SELECT co.codigo, COUNT(*) AS total
                FROM tramite_ran_evento tre
                JOIN tramite_ran tr ON tr.id_tramite_ran=tre.id_tramite_ran
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=tr.id_proyecto_nucleo
                JOIN catalogo_operativo co
                  ON co.id_catalogo_opcion=tre.id_tipo_evento
                WHERE tre.activo IS TRUE AND tr.activo IS TRUE
                  AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
                  AND co.tipo_catalogo='tipo_evento_ran'
                GROUP BY co.codigo
            """, p)
        }
        for code, expected in EXPECTED_RAN_EVENTS.items():
            add_exact(checks, "02F_RAN", f"evento_{code}",
                      ran_by_type.get(code, 0), expected,
                      "Distribución final de eventos RAN.")

        ran_assembly = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_ran tr
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tr.id_proyecto_nucleo
            WHERE tr.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND tr.id_asamblea IS NOT NULL
        """, p)
        add_exact(checks, "02F_RAN", "objetivo_asamblea", ran_assembly, 58,
                  "55 anuencia + 3 retiro.")

        ran_convenio = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_ran tr
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tr.id_proyecto_nucleo
            WHERE tr.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND tr.id_convenio IS NOT NULL
        """, p)
        add_exact(checks, "02F_RAN", "objetivo_convenio", ran_convenio, 73,
                  "Trámites asociados a Convenio.")

        ran_other_targets = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_ran tr
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tr.id_proyecto_nucleo
            WHERE tr.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND (tr.id_nucleo IS NOT NULL OR tr.id_orv IS NOT NULL)
        """, p)
        add_zero(checks, "02F_RAN", "objetivo_nucleo_orv",
                 ran_other_targets,
                 "Importador colectivo final usa PN + Asamblea/Convenio.")

        bad_ran_target = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_ran tr
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tr.id_proyecto_nucleo
            LEFT JOIN asamblea a ON a.id_asamblea=tr.id_asamblea
            LEFT JOIN convenio c ON c.id_convenio=tr.id_convenio
            LEFT JOIN orv o ON o.id_orv=tr.id_orv
            WHERE tr.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND (
                    (tr.id_asamblea IS NOT NULL
                     AND (a.id_asamblea IS NULL OR a.activo IS NOT TRUE
                          OR a.id_proyecto_nucleo <> tr.id_proyecto_nucleo))
                 OR (tr.id_convenio IS NOT NULL
                     AND (c.id_convenio IS NULL OR c.activo IS NOT TRUE
                          OR c.id_proyecto_nucleo <> tr.id_proyecto_nucleo))
                 OR (tr.id_orv IS NOT NULL
                     AND (o.id_orv IS NULL OR o.activo IS NOT TRUE
                          OR o.id_nucleo <> pn.id_nucleo))
                 OR (tr.id_nucleo IS NOT NULL
                     AND tr.id_nucleo <> pn.id_nucleo)
              )
        """, p)
        add_zero(checks, "02F_RAN", "objetivo_territorial_invalido",
                 bad_ran_target, "Objetivo RAN debe pertenecer al mismo contexto.")

        ran_docs = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_ran_evento tre
            JOIN tramite_ran tr ON tr.id_tramite_ran=tre.id_tramite_ran
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tr.id_proyecto_nucleo
            WHERE tre.activo IS TRUE AND tr.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
              AND tre.id_documento IS NOT NULL
        """, p)
        add_zero(checks, "02F_RAN", "documentos_evento_ran", ran_docs,
                 "No se inventaron documentos RAN.")

        duplicate_ran_ordinal = scalar(db, """
            SELECT COUNT(*) FROM (
                SELECT tre.id_tramite_ran, tre.ordinal
                FROM tramite_ran_evento tre
                JOIN tramite_ran tr ON tr.id_tramite_ran=tre.id_tramite_ran
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=tr.id_proyecto_nucleo
                WHERE tre.activo IS TRUE AND tr.activo IS TRUE
                  AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
                GROUP BY tre.id_tramite_ran, tre.ordinal
                HAVING COUNT(*) > 1
            ) q
        """, p)
        add_zero(checks, "02F_RAN", "ordinal_evento_duplicado",
                 duplicate_ran_ordinal, "Secuencia RAN no debe duplicar ordinal.")

        ran_bad_ingreso = scalar(db, """
            SELECT COUNT(*) FROM (
                SELECT tr.id_tramite_ran,
                       COUNT(*) FILTER (WHERE co.codigo='ingreso') AS n
                FROM tramite_ran tr
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=tr.id_proyecto_nucleo
                LEFT JOIN tramite_ran_evento tre
                  ON tre.id_tramite_ran=tr.id_tramite_ran
                 AND tre.activo IS TRUE
                LEFT JOIN catalogo_operativo co
                  ON co.id_catalogo_opcion=tre.id_tipo_evento
                 AND co.tipo_catalogo='tipo_evento_ran'
                WHERE tr.activo IS TRUE AND pn.activo IS TRUE
                  AND pn.id_proyecto=:project_id
                GROUP BY tr.id_tramite_ran
                HAVING COUNT(*) FILTER (WHERE co.codigo='ingreso') <> 1
            ) q
        """, p)
        add_zero(checks, "02F_RAN", "tramite_sin_ingreso_unico",
                 ran_bad_ingreso, "Cada trámite determinista tiene un ingreso.")

        # ------------------------------------------------------------------
        # 2G
        # ------------------------------------------------------------------
        fif_total = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_fifonafe tf
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tf.id_proyecto_nucleo
            WHERE tf.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "02G_FIFONAFE", "tramite_fifonafe", fif_total, 31,
                  "Trámites deterministas.")

        fif_links = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_fifonafe_afectacion tfa
            JOIN tramite_fifonafe tf
              ON tf.id_tramite_fifonafe=tfa.id_tramite_fifonafe
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tf.id_proyecto_nucleo
            WHERE tfa.activo IS TRUE AND tf.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "02G_FIFONAFE", "tramite_afectacion", fif_links, 31,
                  "Exactamente una afectación por trámite.")

        fif_events = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_fifonafe_evento tfe
            JOIN tramite_fifonafe tf
              ON tf.id_tramite_fifonafe=tfe.id_tramite_fifonafe
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tf.id_proyecto_nucleo
            WHERE tfe.activo IS TRUE AND tf.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "02G_FIFONAFE", "eventos", fif_events, 102,
                  "Flujo histórico de cuatro oficios.")

        fif_status = {
            r["estatus"]: r["total"]
            for r in rows(db, """
                SELECT tf.estatus, COUNT(*) AS total
                FROM tramite_fifonafe tf
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=tf.id_proyecto_nucleo
                WHERE tf.activo IS TRUE AND pn.activo IS TRUE
                  AND pn.id_proyecto=:project_id
                GROUP BY tf.estatus
            """, p)
        }
        add_exact(checks, "02G_FIFONAFE", "completo",
                  fif_status.get("completo", 0), 16, "Estatus final.")
        add_exact(checks, "02G_FIFONAFE", "pendiente",
                  fif_status.get("pendiente", 0), 15, "Estatus final.")

        bad_flow = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_fifonafe tf
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tf.id_proyecto_nucleo
            WHERE tf.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND tf.version_flujo <> 1
        """, p)
        add_zero(checks, "02G_FIFONAFE", "version_flujo_distinta_1",
                 bad_flow, "CC:CF usa flujo histórico versión 1.")

        bad_fif_fields = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_fifonafe tf
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tf.id_proyecto_nucleo
            WHERE tf.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND (
                   tf.acuse_fifonafe_fecha IS NOT NULL
                OR tf.hay_conflictos IS NOT NULL
                OR tf.resultado_no_conflictos IS NOT NULL
                OR tf.referencia_expediente IS NOT NULL
                OR tf.id_asamblea_retiro IS NOT NULL
              )
        """, p)
        add_zero(checks, "02G_FIFONAFE", "campos_no_fuente_rellenados",
                 bad_fif_fields,
                 "No se inventaron acuses/conflictos/expediente/asamblea retiro.")

        bad_fif_event_fields = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_fifonafe_evento tfe
            JOIN tramite_fifonafe tf
              ON tf.id_tramite_fifonafe=tfe.id_tramite_fifonafe
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tf.id_proyecto_nucleo
            WHERE tfe.activo IS TRUE AND tf.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
              AND (
                   tfe.origen IS NOT NULL
                OR tfe.destino IS NOT NULL
                OR tfe.id_documento IS NOT NULL
                OR tfe.ciclo_consulta IS NOT NULL
                OR tfe.fecha_evento IS NOT NULL
                OR tfe.conflicto_impide_retiro IS NOT NULL
              )
        """, p)
        add_zero(checks, "02G_FIFONAFE", "campos_evento_no_fuente",
                 bad_fif_event_fields,
                 "Sólo oficio/fecha_oficio y tipo canónico se preservan.")

        fif_by_type = {
            r["codigo"]: r["total"]
            for r in rows(db, """
                SELECT co.codigo, COUNT(*) AS total
                FROM tramite_fifonafe_evento tfe
                JOIN tramite_fifonafe tf
                  ON tf.id_tramite_fifonafe=tfe.id_tramite_fifonafe
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=tf.id_proyecto_nucleo
                JOIN catalogo_operativo co
                  ON co.id_catalogo_opcion=tfe.id_tipo_evento
                WHERE tfe.activo IS TRUE AND tf.activo IS TRUE
                  AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
                  AND co.tipo_catalogo='tipo_evento_fifonafe'
                GROUP BY co.codigo
            """, p)
        }
        for code, expected in EXPECTED_FIFONAFE_EVENTS.items():
            add_exact(checks, "02G_FIFONAFE", f"evento_{code}",
                      fif_by_type.get(code, 0), expected,
                      "Distribución del flujo histórico.")

        bad_fif_cardinality = scalar(db, """
            SELECT COUNT(*) FROM (
                SELECT tf.id_tramite_fifonafe,
                       COUNT(tfa.id_tramite_fifonafe_afectacion) AS n
                FROM tramite_fifonafe tf
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=tf.id_proyecto_nucleo
                LEFT JOIN tramite_fifonafe_afectacion tfa
                  ON tfa.id_tramite_fifonafe=tf.id_tramite_fifonafe
                 AND tfa.activo IS TRUE
                WHERE tf.activo IS TRUE AND pn.activo IS TRUE
                  AND pn.id_proyecto=:project_id
                GROUP BY tf.id_tramite_fifonafe
                HAVING COUNT(tfa.id_tramite_fifonafe_afectacion) <> 1
            ) q
        """, p)
        add_zero(checks, "02G_FIFONAFE", "cardinalidad_afectacion",
                 bad_fif_cardinality,
                 "Cada TramiteFifonafe tiene exactamente una afectación.")

        bad_fif_cross = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_fifonafe_afectacion tfa
            JOIN tramite_fifonafe tf
              ON tf.id_tramite_fifonafe=tfa.id_tramite_fifonafe
            JOIN afectacion a ON a.id_afectacion=tfa.id_afectacion
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tf.id_proyecto_nucleo
            WHERE tfa.activo IS TRUE AND tf.activo IS TRUE
              AND a.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND a.id_proyecto_nucleo <> tf.id_proyecto_nucleo
        """, p)
        add_zero(checks, "02G_FIFONAFE", "afectacion_otro_proyecto_nucleo",
                 bad_fif_cross, "Trámite y afectación deben pertenecer al mismo PN.")

        fif_interveners = scalar(db, """
            SELECT COUNT(*)
            FROM tramite_fifonafe_interviniente tfi
            JOIN tramite_fifonafe tf
              ON tf.id_tramite_fifonafe=tfi.id_tramite_fifonafe
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=tf.id_proyecto_nucleo
            WHERE tfi.activo IS TRUE AND tf.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
        """, p)
        add_zero(checks, "02G_FIFONAFE", "intervinientes",
                 fif_interveners, "No se inventaron intervinientes.")

        # ------------------------------------------------------------------
        # 2H
        # ------------------------------------------------------------------
        indemnities = scalar(db, """
            SELECT COUNT(*)
            FROM indemnizacion i
            JOIN afectacion a ON a.id_afectacion=i.id_afectacion
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            WHERE i.activo IS TRUE AND a.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "02H_ESTADOS", "indemnizaciones", indemnities, 3,
                  "BX=PAGADO determinista.")

        paid = scalar(db, """
            SELECT COUNT(*)
            FROM indemnizacion i
            JOIN afectacion a ON a.id_afectacion=i.id_afectacion
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            WHERE i.activo IS TRUE AND a.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
              AND i.estatus='pagado'
        """, p)
        add_exact(checks, "02H_ESTADOS", "indemnizaciones_pagadas", paid, 3,
                  "Se conserva el estado, no un Pago.")

        indemnity_dates = scalar(db, """
            SELECT COUNT(*)
            FROM indemnizacion i
            JOIN afectacion a ON a.id_afectacion=i.id_afectacion
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            WHERE i.activo IS TRUE AND a.activo IS TRUE
              AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
              AND (
                   i.fecha_programada IS NOT NULL
                OR i.fecha_resolucion IS NOT NULL
                OR i.fecha_entrega_expediente_pa IS NOT NULL
              )
        """, p)
        add_zero(checks, "02H_ESTADOS", "fechas_indemnizacion_inventadas",
                 indemnity_dates, "La fuente no aportó fechas deterministas.")

        payments = scalar(db, """
            SELECT COUNT(*)
            FROM pago pg
            JOIN indemnizacion i ON i.id_indemnizacion=pg.id_indemnizacion
            JOIN afectacion a ON a.id_afectacion=i.id_afectacion
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
            WHERE pg.activo IS TRUE AND i.activo IS TRUE
              AND a.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
        """, p)
        add_zero(checks, "02H_ESTADOS", "pagos", payments,
                 "BX='PAGADO' no crea Pago.")

        tuc_false = scalar(db, """
            SELECT COUNT(*)
            FROM proyecto_nucleo
            WHERE activo IS TRUE AND id_proyecto=:project_id
              AND afecta_tuc IS FALSE
        """, p)
        add_exact(checks, "02H_ESTADOS", "afecta_tuc_false", tuc_false, 2,
                  "No afectación TUC determinista.")

        tuc_reason_ok = scalar(db, """
            SELECT COUNT(*)
            FROM proyecto_nucleo pn
            JOIN catalogo_operativo co
              ON co.id_catalogo_opcion=pn.id_motivo_no_afecta_tuc
            WHERE pn.activo IS TRUE AND pn.id_proyecto=:project_id
              AND pn.afecta_tuc IS FALSE
              AND co.tipo_catalogo='motivo_no_afecta_tuc'
              AND co.codigo='no_afectacion_colectiva'
        """, p)
        add_exact(checks, "02H_ESTADOS", "motivo_no_afecta_tuc",
                  tuc_reason_ok, 2, "Motivo canónico de los dos casos.")

        communities = scalar(db, """
            SELECT COUNT(DISTINCT na.id_nucleo)
            FROM nucleo_agrario na
            JOIN proyecto_nucleo pn ON pn.id_nucleo=na.id_nucleo
            WHERE na.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND na.comunidad_indigena IS TRUE
        """, p)
        add_exact(checks, "02H_ESTADOS", "comunidad_indigena_true",
                  communities, 7, "CB='SÍ' determinista.")

        # ------------------------------------------------------------------
        # 2I
        # ------------------------------------------------------------------
        requirement_total = scalar(db, """
            SELECT COUNT(*)
            FROM expediente_requisito er
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=er.id_proyecto_nucleo
            WHERE er.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
        """, p)
        add_exact(checks, "02I_DOCUMENTAL", "expediente_requisito",
                  requirement_total, 384,
                  "38 de 2I-A + 346 CK/CL post 2I-B-R.")

        req_by_code = {
            r["codigo"]: r["total"]
            for r in rows(db, """
                SELECT rd.codigo, COUNT(*) AS total
                FROM expediente_requisito er
                JOIN requisito_documental rd
                  ON rd.id_requisito=er.id_requisito
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=er.id_proyecto_nucleo
                WHERE er.activo IS TRUE AND rd.activo IS TRUE
                  AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
                GROUP BY rd.codigo
            """, p)
        }
        for code, expected in EXPECTED_REQUIREMENTS.items():
            add_exact(checks, "02I_DOCUMENTAL", f"requisito_{code}",
                      req_by_code.get(code, 0), expected,
                      "Desglose documental final.")

        extra_req_codes = sorted(set(req_by_code) - set(EXPECTED_REQUIREMENTS))
        add_exact(checks, "02I_DOCUMENTAL", "requisitos_fuera_plan",
                  len(extra_req_codes), 0,
                  "No deben aparecer requisitos importados fuera del plan final.")

        req_states = {
            r["codigo"]: r["total"]
            for r in rows(db, """
                SELECT co.codigo, COUNT(*) AS total
                FROM expediente_requisito er
                JOIN catalogo_operativo co
                  ON co.id_catalogo_opcion=er.id_estado
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=er.id_proyecto_nucleo
                WHERE er.activo IS TRUE AND pn.activo IS TRUE
                  AND pn.id_proyecto=:project_id
                  AND co.tipo_catalogo='estado_requisito_documental'
                GROUP BY co.codigo
            """, p)
        }
        add_exact(checks, "02I_DOCUMENTAL", "pendiente_validacion",
                  req_states.get("pendiente_validacion", 0), 281,
                  "38 CI + 243 CK/CL.")
        add_exact(checks, "02I_DOCUMENTAL", "faltante",
                  req_states.get("faltante", 0), 103,
                  "CK/CL faltante.")

        req_docs = scalar(db, """
            SELECT COUNT(*)
            FROM expediente_requisito er
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=er.id_proyecto_nucleo
            WHERE er.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND er.id_documento IS NOT NULL
        """, p)
        add_zero(checks, "02I_DOCUMENTAL", "documentos",
                 req_docs, "Texto de soporte no equivale a archivo digital.")

        duplicate_req = scalar(db, """
            SELECT COUNT(*) FROM (
                SELECT er.id_proyecto_nucleo, er.id_requisito,
                       er.entidad_tipo, er.entidad_id
                FROM expediente_requisito er
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=er.id_proyecto_nucleo
                WHERE er.activo IS TRUE AND pn.activo IS TRUE
                  AND pn.id_proyecto=:project_id
                GROUP BY er.id_proyecto_nucleo, er.id_requisito,
                         er.entidad_tipo, er.entidad_id
                HAVING COUNT(*) > 1
            ) q
        """, p)
        add_zero(checks, "02I_DOCUMENTAL", "claves_duplicadas",
                 duplicate_req, "Clave documental canónica debe ser única.")

        invalid_req_targets, req_target_distribution = validate_expediente_targets(
            db, project_id
        )
        add_zero(checks, "02I_DOCUMENTAL", "objetivos_invalidos",
                 invalid_req_targets,
                 "Cada objetivo documental debe existir y pertenecer al mismo PN/núcleo.")
        add_info(checks, "02I_DOCUMENTAL", "distribucion_entidad_tipo",
                 req_target_distribution, "Distribución de objetivos documentales.")

        # ------------------------------------------------------------------
        # 2J
        # ------------------------------------------------------------------
        follow_total = scalar(db, """
            SELECT COUNT(*)
            FROM seguimiento_evento se
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=se.id_proyecto_nucleo
            WHERE se.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND se.ambito='colectivo'
        """, p)
        add_exact(checks, "02J_SEGUIMIENTO", "seguimiento_evento",
                  follow_total, 17, "Eventos deterministas finales.")

        follow_docs = scalar(db, """
            SELECT COUNT(*)
            FROM seguimiento_evento se
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=se.id_proyecto_nucleo
            WHERE se.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND se.ambito='colectivo'
              AND se.id_documento IS NOT NULL
        """, p)
        add_zero(checks, "02J_SEGUIMIENTO", "documentos",
                 follow_docs, "No se inventaron documentos.")

        follow_pn = scalar(db, """
            SELECT COUNT(*)
            FROM seguimiento_evento se
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=se.id_proyecto_nucleo
            WHERE se.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND se.ambito='colectivo'
              AND se.entidad_tipo='proyecto_nucleo'
        """, p)
        add_exact(checks, "02J_SEGUIMIENTO", "sobre_proyecto_nucleo",
                  follow_pn, 11, "Eventos funcionales generales.")

        follow_assembly = scalar(db, """
            SELECT COUNT(*)
            FROM seguimiento_evento se
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=se.id_proyecto_nucleo
            WHERE se.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND se.ambito='colectivo'
              AND se.entidad_tipo='asamblea'
        """, p)
        add_exact(checks, "02J_SEGUIMIENTO", "sobre_asamblea",
                  follow_assembly, 6, "Continuaciones de Asamblea permanente.")

        follow_by_type = {
            (r["tipo_evento"], r["motivo"] or ""): r["total"]
            for r in rows(db, """
                SELECT te.codigo AS tipo_evento,
                       ms.codigo AS motivo,
                       COUNT(*) AS total
                FROM seguimiento_evento se
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=se.id_proyecto_nucleo
                JOIN catalogo_operativo te
                  ON te.id_catalogo_opcion=se.id_tipo_evento
                LEFT JOIN catalogo_operativo ms
                  ON ms.id_catalogo_opcion=se.id_motivo
                WHERE se.activo IS TRUE AND pn.activo IS TRUE
                  AND pn.id_proyecto=:project_id
                  AND se.ambito='colectivo'
                  AND te.tipo_catalogo='tipo_evento_seguimiento'
                GROUP BY te.codigo, ms.codigo
            """, p)
        }
        for key, expected in EXPECTED_2J_EVENTS.items():
            label = key[0] + (f"_{key[1]}" if key[1] else "")
            add_exact(checks, "02J_SEGUIMIENTO", f"evento_{label}",
                      follow_by_type.get(key, 0), expected,
                      "Desglose determinista 2J.")

        invalid_follow_targets = validate_seguimiento_targets(db, project_id)
        add_zero(checks, "02J_SEGUIMIENTO", "objetivos_invalidos",
                 invalid_follow_targets,
                 "Continuación -> Asamblea; otros eventos -> mismo ProyectoNucleo.")

        duplicate_follow = scalar(db, """
            SELECT COUNT(*) FROM (
                SELECT se.id_proyecto_nucleo, se.entidad_tipo, se.entidad_id,
                       se.ambito, se.id_tipo_evento, se.id_motivo,
                       se.fecha_evento, se.detalle, se.fuente
                FROM seguimiento_evento se
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=se.id_proyecto_nucleo
                WHERE se.activo IS TRUE AND pn.activo IS TRUE
                  AND pn.id_proyecto=:project_id
                  AND se.ambito='colectivo'
                GROUP BY se.id_proyecto_nucleo, se.entidad_tipo, se.entidad_id,
                         se.ambito, se.id_tipo_evento, se.id_motivo,
                         se.fecha_evento, se.detalle, se.fuente
                HAVING COUNT(*) > 1
            ) q
        """, p)
        add_zero(checks, "02J_SEGUIMIENTO", "firmas_duplicadas",
                 duplicate_follow, "Idempotencia por firma exacta.")

        follow_null_date = scalar(db, """
            SELECT COUNT(*)
            FROM seguimiento_evento se
            JOIN proyecto_nucleo pn
              ON pn.id_proyecto_nucleo=se.id_proyecto_nucleo
            WHERE se.activo IS TRUE AND pn.activo IS TRUE
              AND pn.id_proyecto=:project_id
              AND se.ambito='colectivo'
              AND se.fecha_evento IS NULL
        """, p)
        add_zero(checks, "02J_SEGUIMIENTO", "fecha_evento_null",
                 follow_null_date,
                 "Sólo se escribieron los 17 eventos con fecha determinista.")

        # ------------------------------------------------------------------
        # CONTROLES TRANSVERSALES
        # ------------------------------------------------------------------
        relevant_doc_refs = (
            req_docs + follow_docs + conv_docs + ran_docs
            + scalar(db, """
                SELECT COUNT(*)
                FROM padron_historial ph
                WHERE ph.activo IS TRUE
                  AND ph.id_documento IS NOT NULL
                  AND ph.id_nucleo IN (
                      SELECT id_nucleo FROM proyecto_nucleo
                      WHERE activo IS TRUE AND id_proyecto=:project_id
                  )
            """, p)
            + scalar(db, """
                SELECT COUNT(*)
                FROM tramite_fifonafe_evento tfe
                JOIN tramite_fifonafe tf
                  ON tf.id_tramite_fifonafe=tfe.id_tramite_fifonafe
                JOIN proyecto_nucleo pn
                  ON pn.id_proyecto_nucleo=tf.id_proyecto_nucleo
                WHERE tfe.activo IS TRUE AND tf.activo IS TRUE
                  AND pn.activo IS TRUE AND pn.id_proyecto=:project_id
                  AND tfe.id_documento IS NOT NULL
            """, p)
        )
        add_zero(checks, "99_TRANSVERSAL", "referencias_documento_no_inventadas",
                 relevant_doc_refs,
                 "Capas migradas desde texto Excel no deben fingir archivo digital.")

        active_documents_total = scalar(
            db,
            "SELECT COUNT(*) FROM documento WHERE activo IS TRUE"
        )
        add_info(checks, "99_TRANSVERSAL", "documentos_activos_base",
                 active_documents_total,
                 "INFO global: Documento no tiene FK directa al proyecto.")

        # ------------------------------------------------------------------
        # REPORTES
        # ------------------------------------------------------------------
        fail_count = sum(1 for check in checks if check.status == "FAIL")
        pass_count = sum(1 for check in checks if check.status == "PASS")
        info_count = sum(1 for check in checks if check.status == "INFO")

        layer_summary: dict[str, dict[str, int]] = {}
        for check in checks:
            bucket = layer_summary.setdefault(
                check.layer, {"PASS": 0, "FAIL": 0, "INFO": 0}
            )
            bucket[check.status] += 1

        report = {
            "database": current_db,
            "schema": str(schema),
            "project": PROJECT_KEY,
            "project_id": project_id,
            "excel": str(args.excel),
            "excel_sha256": excel_sha,
            "resolution_2j": str(args.resolution_2j),
            "resolution_2j_sha256": resolution_sha,
            "transaction": "READ ONLY / ROLLBACK",
            "summary": {
                "PASS": pass_count,
                "FAIL": fail_count,
                "INFO": info_count,
                "result": "PASS" if fail_count == 0 else "FAIL",
            },
            "layers": layer_summary,
            "checks": [asdict(check) for check in checks],
        }

        json_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "layer", "code", "status",
                    "expected", "actual", "detail",
                ],
            )
            writer.writeheader()
            for check in checks:
                row = asdict(check)
                if isinstance(row["expected"], (dict, list, tuple)):
                    row["expected"] = json.dumps(
                        row["expected"], ensure_ascii=False, sort_keys=True
                    )
                if isinstance(row["actual"], (dict, list, tuple)):
                    row["actual"] = json.dumps(
                        row["actual"], ensure_ascii=False, sort_keys=True
                    )
                writer.writerow(row)

        print("=== AUDITORÍA GLOBAL MIGRACIÓN MEX-QRO ===")
        print(f"BD: {current_db} / schema {schema}")
        print(f"Proyecto: {PROJECT_KEY} / id_proyecto={project_id}")
        print(f"SHA-256 Excel:      {excel_sha}")
        print(f"SHA-256 resolución: {resolution_sha}")
        print("Transacción: READ ONLY")
        print()
        print("Resumen por capa:")
        for layer in sorted(layer_summary):
            bucket = layer_summary[layer]
            print(
                f"  {layer:<22} "
                f"PASS={bucket['PASS']:>2} "
                f"FAIL={bucket['FAIL']:>2} "
                f"INFO={bucket['INFO']:>2}"
            )

        print()
        print(
            f"TOTAL: PASS={pass_count} FAIL={fail_count} INFO={info_count}"
        )

        failures = [check for check in checks if check.status == "FAIL"]
        infos = [check for check in checks if check.status == "INFO"]

        if failures:
            print()
            print("FAILURES:")
            for check in failures:
                print(
                    f"  [{check.layer}] {check.code}: "
                    f"esperado={check.expected!r} actual={check.actual!r} | "
                    f"{check.detail}"
                )

        if infos:
            print()
            print("INFO:")
            for check in infos:
                print(
                    f"  [{check.layer}] {check.code}: "
                    f"{check.actual!r} | {check.detail}"
                )

        if args.verbose:
            print()
            print("TODOS LOS CHECKS:")
            for check in checks:
                print(
                    f"  {check.status:<4} [{check.layer}] {check.code}: "
                    f"esperado={check.expected!r} actual={check.actual!r}"
                )

        print()
        print(f"Reporte JSON: {json_path}")
        print(f"Reporte CSV:  {csv_path}")

        if fail_count == 0:
            print(
                "RESULTADO GLOBAL: PASS — no se detectaron desviaciones "
                "contra el estado final congelado."
            )
        else:
            print(
                "RESULTADO GLOBAL: FAIL — no promover la base hasta "
                "diagnosticar los checks fallidos."
            )

        return 0 if fail_count == 0 else 2

    finally:
        # Incluso siendo READ ONLY, cerramos explícitamente con rollback.
        db.rollback()
        db.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditAbort as exc:
        print("=== AUDITORÍA GLOBAL ABORTADA ===", file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
