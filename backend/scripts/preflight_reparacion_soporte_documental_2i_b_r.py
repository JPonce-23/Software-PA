#!/usr/bin/env python3
"""Preflight read-only 2I-B-R: seis requisitos CK/CL desbloqueados.

Entrada:
- Excel aprobado (sólo para SHA-256).
- CSV post-2F-R generado por:
  reconciliar_soporte_documental_ck_cl_post_2f_r.py

Estado congelado de la reconciliación post-2F-R:
- 382 claves documentales únicas
- CREATE_CANDIDATE = 6
- REUSE_CANDIDATE = 340
- CONFLICT_REVIEW = 36
- EXISTING_REVIEW = 0
- Deterministas = 346
- pendiente_validacion = 243
- faltante = 103

Persistencia histórica que debe seguir intacta:
- 340 ExpedienteRequisito CK/CL activos
- 240 pendiente_validacion
- 100 faltante
- 0 Documento digital

Este preflight:
1) valida Excel/BD/schema/proyecto;
2) valida cardinalidades de la reconciliación;
3) verifica que los 340 REUSE coinciden exactamente contra PostgreSQL;
4) verifica que los 6 CREATE no existen todavía;
5) revalida pertenencia territorial de sus objetivos con la lógica original;
6) imprime y exporta las seis claves exactas que luego podrán congelarse
   para un importador focalizado 2I-B-R.

NO escribe en PostgreSQL.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402
from app.database import DB_NAME, SessionLocal  # noqa: E402
import importar_soporte_documental_ck_cl as base  # noqa: E402


EXPECTED_DB = "db_carga_excel"
EXPECTED_SCHEMA = "018"
EXPECTED_SHA256 = "bac01c25e9ff963f524fa8a48d69e74d92a0d36578731b1eca91f0e5a3573c3f"
PROJECT_KEY = "MEX-QRO"

EXPECTED_ROWS = 382
EXPECTED_ACTIONS = {
    "CREATE_CANDIDATE": 6,
    "REUSE_CANDIDATE": 340,
    "CONFLICT_REVIEW": 36,
    "EXISTING_REVIEW": 0,
}
EXPECTED_DETERMINISTIC = 346
EXPECTED_STATES = {
    "pendiente_validacion": 243,
    "faltante": 103,
}
EXPECTED_REUSE_STATES = {
    "pendiente_validacion": 240,
    "faltante": 100,
}
EXPECTED_CREATE_STATES = {
    "pendiente_validacion": 3,
    "faltante": 3,
}

EXPECTED_CONFLICTS_BY_REQUIREMENT = {
    "acta_eleccion_orv": 4,
    "acuse_ran": 3,
    "padron": 1,
    "soporte_caminamiento": 16,
    "soporte_sensibilizacion": 12,
}


class PreflightAbort(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def schema_version(db) -> str | None:
    return db.execute(text("SELECT max(version) FROM schema_migrations")).scalar()


def parse_int(value: Any, field: str) -> int:
    try:
        parsed = int(str(value).strip())
    except Exception as exc:
        raise PreflightAbort(f"{field} inválido: {value!r}") from exc
    if parsed <= 0:
        raise PreflightAbort(f"{field} debe ser > 0: {parsed}")
    return parsed


def territorial_label(db, pn_id: int) -> str:
    row = (
        db.query(
            models.EntidadFederativa.nombre,
            models.Municipio.nombre,
            models.NucleoAgrario.nombre_nucleo,
        )
        .join(
            models.Municipio,
            models.Municipio.id_entidad == models.EntidadFederativa.id_entidad,
        )
        .join(
            models.NucleoAgrario,
            models.NucleoAgrario.id_municipio == models.Municipio.id_municipio,
        )
        .join(
            models.ProyectoNucleo,
            models.ProyectoNucleo.id_nucleo == models.NucleoAgrario.id_nucleo,
        )
        .filter(
            models.ProyectoNucleo.id_proyecto_nucleo == pn_id,
            models.ProyectoNucleo.activo.is_(True),
            models.NucleoAgrario.activo.is_(True),
        )
        .one_or_none()
    )
    if row is None:
        return f"PN:{pn_id}"
    return f"{row[0]}|{row[1]}|{row[2]}"


def load_and_validate_reconciliation(path: Path) -> tuple[
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
]:
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))

    if len(rows) != EXPECTED_ROWS:
        raise PreflightAbort(
            f"Claves reconciliadas cambiaron: esperado={EXPECTED_ROWS}, actual={len(rows)}."
        )

    action_counts = Counter(row["action"].strip() for row in rows)
    for action, expected in EXPECTED_ACTIONS.items():
        actual = action_counts[action]
        if actual != expected:
            raise PreflightAbort(
                f"Cambió {action}: esperado={expected}, actual={actual}."
            )

    unexpected_actions = {
        action
        for action, count in action_counts.items()
        if count and action not in EXPECTED_ACTIONS
    }
    if unexpected_actions:
        raise PreflightAbort(
            "Aparecieron acciones inesperadas: "
            + ", ".join(sorted(unexpected_actions))
        )

    creates = [
        row for row in rows if row["action"].strip() == "CREATE_CANDIDATE"
    ]
    reuses = [
        row for row in rows if row["action"].strip() == "REUSE_CANDIDATE"
    ]
    conflicts = [
        row for row in rows if row["action"].strip() == "CONFLICT_REVIEW"
    ]
    existing_review = [
        row for row in rows if row["action"].strip() == "EXISTING_REVIEW"
    ]

    deterministic = creates + reuses
    if len(deterministic) != EXPECTED_DETERMINISTIC:
        raise PreflightAbort(
            "Cambió conjunto determinista: "
            f"esperado={EXPECTED_DETERMINISTIC}, actual={len(deterministic)}."
        )

    state_counts = Counter(row["proposed_state"].strip() for row in deterministic)
    reuse_states = Counter(row["proposed_state"].strip() for row in reuses)
    create_states = Counter(row["proposed_state"].strip() for row in creates)

    for code, expected in EXPECTED_STATES.items():
        if state_counts[code] != expected:
            raise PreflightAbort(
                f"Cambió estado determinista/{code}: "
                f"esperado={expected}, actual={state_counts[code]}."
            )

    for code, expected in EXPECTED_REUSE_STATES.items():
        if reuse_states[code] != expected:
            raise PreflightAbort(
                f"Cambió REUSE/{code}: esperado={expected}, actual={reuse_states[code]}."
            )

    for code, expected in EXPECTED_CREATE_STATES.items():
        if create_states[code] != expected:
            raise PreflightAbort(
                f"Cambió CREATE/{code}: esperado={expected}, actual={create_states[code]}."
            )

    conflict_counts = Counter(row["requirement"].strip() for row in conflicts)
    for requirement, expected in EXPECTED_CONFLICTS_BY_REQUIREMENT.items():
        if conflict_counts[requirement] != expected:
            raise PreflightAbort(
                f"Cambió conflicto/{requirement}: "
                f"esperado={expected}, actual={conflict_counts[requirement]}."
            )

    extra_conflicts = set(conflict_counts) - set(EXPECTED_CONFLICTS_BY_REQUIREMENT)
    if extra_conflicts:
        raise PreflightAbort(
            "Aparecieron conflictos fuera del plan histórico: "
            + ", ".join(sorted(extra_conflicts))
        )

    if existing_review:
        raise PreflightAbort(
            f"EXISTING_REVIEW debe ser 0; actual={len(existing_review)}."
        )

    return rows, creates, reuses, conflicts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("excel", type=Path)
    parser.add_argument(
        "--reconciliation-csv",
        type=Path,
        default=Path(
            "/data/reportes/2i_b_post_2f_r/"
            "reconciliacion_soporte_documental_ck_cl.csv"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/reportes/2i_b_post_2f_r"),
    )
    args = parser.parse_args()

    if DB_NAME != EXPECTED_DB:
        raise PreflightAbort(
            f"Protección: DB_NAME debe ser {EXPECTED_DB!r}; recibido {DB_NAME!r}."
        )
    if not args.excel.exists():
        raise PreflightAbort(f"No existe el Excel: {args.excel}")
    if not args.reconciliation_csv.exists():
        raise PreflightAbort(
            f"No existe reconciliación post-2F-R: {args.reconciliation_csv}"
        )

    digest = sha256_file(args.excel)
    if digest != EXPECTED_SHA256:
        raise PreflightAbort(
            "El SHA-256 no coincide con el Excel aprobado. "
            f"Esperado {EXPECTED_SHA256}; recibido {digest}."
        )

    rows, creates, reuses, conflicts = load_and_validate_reconciliation(
        args.reconciliation_csv
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "preflight_reparacion_soporte_documental_2i_b_r.csv"
    json_path = args.output_dir / "preflight_reparacion_soporte_documental_2i_b_r.json"

    db = SessionLocal()
    try:
        current_db = db.execute(text("SELECT current_database()")).scalar()
        current_schema = schema_version(db)
        if current_db != EXPECTED_DB or current_schema != EXPECTED_SCHEMA:
            raise PreflightAbort(
                f"Destino inesperado: BD={current_db!r}, schema={current_schema!r}."
            )

        project = (
            db.query(models.Proyecto)
            .filter(
                models.Proyecto.clave_proyecto == PROJECT_KEY,
                models.Proyecto.activo.is_(True),
            )
            .one_or_none()
        )
        if project is None:
            raise PreflightAbort(f"No existe proyecto activo {PROJECT_KEY!r}.")

        requirements = (
            db.query(models.RequisitoDocumental)
            .filter(
                models.RequisitoDocumental.codigo.in_(set(base.EXPECTED_BY_REQUIREMENT)),
                models.RequisitoDocumental.activo.is_(True),
            )
            .all()
        )
        requirement_by_code = {row.codigo: row for row in requirements}
        missing_requirements = (
            set(base.EXPECTED_BY_REQUIREMENT) - set(requirement_by_code)
        )
        if missing_requirements:
            raise PreflightAbort(
                "Faltan requisitos documentales activos: "
                + ", ".join(sorted(missing_requirements))
            )

        states = base.catalog_by_code(db, "estado_requisito_documental")
        for code in ("pendiente_validacion", "faltante"):
            if code not in states:
                raise PreflightAbort(
                    f"Falta estado_requisito_documental/{code}."
                )

        # ProyectoNucleo usados por las 346 claves deterministas.
        pn_ids = {
            parse_int(row["id_proyecto_nucleo"], "id_proyecto_nucleo")
            for row in creates + reuses
        }
        pns = (
            db.query(models.ProyectoNucleo)
            .filter(
                models.ProyectoNucleo.id_proyecto_nucleo.in_(pn_ids),
                models.ProyectoNucleo.id_proyecto == project.id_proyecto,
                models.ProyectoNucleo.activo.is_(True),
            )
            .all()
        )
        pn_by_id = {row.id_proyecto_nucleo: row for row in pns}
        missing_pn = pn_ids - set(pn_by_id)
        if missing_pn:
            raise PreflightAbort(
                "Hay ProyectoNucleo fuera de MEX-QRO/inactivos: "
                + ", ".join(map(str, sorted(missing_pn)))
            )

        # Verificar los 340 REUSE directamente contra la BD.
        verified_reuse = 0
        seen_existing_ids: set[int] = set()

        for source in reuses:
            pn_id = parse_int(source["id_proyecto_nucleo"], "id_proyecto_nucleo")
            target_id = parse_int(source["target_id"], "target_id")
            requirement_code = source["requirement"].strip()
            target_type = source["target_type"].strip()
            state_code = source["proposed_state"].strip()
            canonical_detail = source["canonical_detail"]

            target_ok, target_detail = base.validate_target(
                db,
                pn_by_id[pn_id],
                target_type,
                target_id,
            )
            if not target_ok:
                raise PreflightAbort(
                    "REUSE dejó de tener objetivo válido: "
                    f"PN={pn_id}, requisito={requirement_code}, "
                    f"{target_type}/{target_id}. {target_detail}"
                )

            requirement = requirement_by_code[requirement_code]
            state_id = states[state_code].id_catalogo_opcion

            existing = (
                db.query(models.ExpedienteRequisito)
                .filter(
                    models.ExpedienteRequisito.id_proyecto_nucleo == pn_id,
                    models.ExpedienteRequisito.id_requisito
                    == requirement.id_requisito,
                    models.ExpedienteRequisito.entidad_tipo == target_type,
                    models.ExpedienteRequisito.entidad_id == target_id,
                    models.ExpedienteRequisito.activo.is_(True),
                )
                .all()
            )
            if len(existing) != 1:
                raise PreflightAbort(
                    "REUSE no resuelve exactamente un ExpedienteRequisito: "
                    f"PN={pn_id}, requisito={requirement_code}, "
                    f"{target_type}/{target_id}, encontrados={len(existing)}."
                )

            req = existing[0]
            if not (
                req.id_estado == state_id
                and req.id_documento is None
                and req.detalle == canonical_detail
            ):
                raise PreflightAbort(
                    "REUSE dejó de coincidir exactamente con la BD: "
                    f"id_expediente_requisito={req.id_expediente_requisito}."
                )

            if req.id_expediente_requisito in seen_existing_ids:
                raise PreflightAbort(
                    "El mismo ExpedienteRequisito fue resuelto por más de una "
                    f"clave REUSE: {req.id_expediente_requisito}."
                )
            seen_existing_ids.add(req.id_expediente_requisito)
            verified_reuse += 1

        if verified_reuse != 340 or len(seen_existing_ids) != 340:
            raise PreflightAbort(
                "No se verificaron exactamente los 340 REUSE históricos."
            )

        # Verificar y describir las seis claves nuevas.
        create_details = []
        requirement_counts = Counter()
        target_type_counts = Counter()

        for source in creates:
            pn_id = parse_int(source["id_proyecto_nucleo"], "id_proyecto_nucleo")
            target_id = parse_int(source["target_id"], "target_id")
            requirement_code = source["requirement"].strip()
            target_type = source["target_type"].strip()
            state_code = source["proposed_state"].strip()
            canonical_detail = source["canonical_detail"]

            if target_type not in base.ALLOWED_TARGET_TYPES:
                raise PreflightAbort(
                    f"CREATE tiene tipo de objetivo fuera del plan: {target_type}."
                )
            if state_code not in base.ALLOWED_STATES:
                raise PreflightAbort(
                    f"CREATE tiene estado fuera del plan: {state_code}."
                )
            if not canonical_detail.strip():
                raise PreflightAbort("CREATE tiene canonical_detail vacío.")
            if "No se adjuntó Documento digital" not in canonical_detail:
                raise PreflightAbort(
                    "CREATE dejó de preservar la regla de no Documento digital."
                )

            target_ok, target_detail = base.validate_target(
                db,
                pn_by_id[pn_id],
                target_type,
                target_id,
            )
            if not target_ok:
                raise PreflightAbort(
                    "CREATE tiene objetivo inválido: "
                    f"PN={pn_id}, requisito={requirement_code}, "
                    f"{target_type}/{target_id}. {target_detail}"
                )

            requirement = requirement_by_code[requirement_code]
            existing = (
                db.query(models.ExpedienteRequisito)
                .filter(
                    models.ExpedienteRequisito.id_proyecto_nucleo == pn_id,
                    models.ExpedienteRequisito.id_requisito
                    == requirement.id_requisito,
                    models.ExpedienteRequisito.entidad_tipo == target_type,
                    models.ExpedienteRequisito.entidad_id == target_id,
                    models.ExpedienteRequisito.activo.is_(True),
                )
                .all()
            )
            if existing:
                raise PreflightAbort(
                    "CREATE_CANDIDATE ya existe en BD; reconciliación quedó obsoleta: "
                    f"PN={pn_id}, requisito={requirement_code}, "
                    f"{target_type}/{target_id}, existentes={len(existing)}."
                )

            detail = {
                "id_proyecto_nucleo": pn_id,
                "source_key": territorial_label(db, pn_id),
                "requirement": requirement_code,
                "target_type": target_type,
                "target_id": target_id,
                "proposed_state": state_code,
                "evidence_count": parse_int(source["evidence_count"], "evidence_count"),
                "source_rows": source["source_rows"],
                "source_columns": source["source_columns"],
                "source_states": source["source_states"],
                "canonical_detail": canonical_detail,
            }
            create_details.append(detail)
            requirement_counts[requirement_code] += 1
            target_type_counts[target_type] += 1

        if len(create_details) != 6:
            raise PreflightAbort(
                f"CREATE_CANDIDATE válidos != 6: {len(create_details)}."
            )

        create_details.sort(
            key=lambda x: (
                x["source_key"],
                x["requirement"],
                x["target_type"],
                x["target_id"],
            )
        )

        with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "id_proyecto_nucleo",
                    "source_key",
                    "requirement",
                    "target_type",
                    "target_id",
                    "proposed_state",
                    "evidence_count",
                    "source_rows",
                    "source_columns",
                    "source_states",
                    "canonical_detail",
                ],
            )
            writer.writeheader()
            writer.writerows(create_details)

        report = {
            "database": current_db,
            "schema": current_schema,
            "project": PROJECT_KEY,
            "excel": args.excel.name,
            "sha256": digest,
            "reconciliation": {
                "unique_keys": len(rows),
                "CREATE_CANDIDATE": len(creates),
                "REUSE_CANDIDATE": len(reuses),
                "CONFLICT_REVIEW": len(conflicts),
                "EXISTING_REVIEW": 0,
            },
            "states": EXPECTED_STATES,
            "reuse_verified_against_db": verified_reuse,
            "create_candidates": create_details,
            "create_by_requirement": dict(sorted(requirement_counts.items())),
            "create_by_target_type": dict(sorted(target_type_counts.items())),
        }
        json_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print("=== PREFLIGHT REPARACIÓN 2I-B-R — SOPORTE CK/CL ===")
        print(f"BD: {current_db} / schema {current_schema}")
        print(f"Proyecto: {PROJECT_KEY}")
        print(f"SHA-256: {digest}")
        print("Reconciliación congelada:")
        print(f"  Claves únicas:       {len(rows)}")
        print(f"  CREATE_CANDIDATE:    {len(creates)}")
        print(f"  REUSE_CANDIDATE:     {len(reuses)}")
        print(f"  CONFLICT_REVIEW:     {len(conflicts)}")
        print("  EXISTING_REVIEW:     0")
        print("Estados deterministas:")
        print("  pendiente_validacion: 243 (240 REUSE + 3 CREATE)")
        print("  faltante:             103 (100 REUSE + 3 CREATE)")
        print(f"REUSE verificados contra PostgreSQL: {verified_reuse}")
        print("CREATE_CANDIDATE exactos:")
        for item in create_details:
            print(
                f"  {item['source_key']} | "
                f"{item['requirement']} -> "
                f"{item['target_type']}/{item['target_id']} | "
                f"{item['proposed_state']} | "
                f"filas={item['source_rows']} | "
                f"columnas={item['source_columns']}"
            )
        print("CREATE por requisito:")
        for requirement, count in sorted(requirement_counts.items()):
            print(f"  {requirement:<30} {count}")
        print(f"Reporte JSON: {json_path}")
        print(f"Plan CSV:     {csv_path}")
        print("No se realizó ninguna escritura en PostgreSQL.")
        return 0

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PreflightAbort, base.ImportAbort) as exc:
        print("=== PREFLIGHT 2I-B-R ABORTADO ===", file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
