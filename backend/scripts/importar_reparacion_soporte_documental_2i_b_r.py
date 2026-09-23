#!/usr/bin/env python3
"""Importación transaccional 2I-B-R: seis requisitos CK/CL desbloqueados.

Contexto
========
La capa 2I-B original quedó cerrada con:
- 340 ExpedienteRequisito deterministas
- 240 pendiente_validacion
- 100 faltante
- 36 CONFLICT_REVIEW no escritos
- 0 Documento digital

Después de 2B-R y 2F-R, el resolvedor/reconciliador produjo:
- 382 claves documentales únicas
- 346 deterministas
- 6 CREATE_CANDIDATE nuevos
- 340 REUSE_CANDIDATE históricos
- 36 CONFLICT_REVIEW
- 0 EXISTING_REVIEW
- 243 pendiente_validacion
- 103 faltante

Las seis claves nuevas congeladas son:
- fila 45 CK: acta_asamblea -> asamblea / pendiente_validacion
- fila 45 CK: acuse_ran -> tramite_ran_evento / pendiente_validacion
- fila 92 CK: convocatoria_asamblea -> asamblea_convocatoria /
  pendiente_validacion
- fila 103 CL: acuse_ran -> tramite_ran_evento / faltante
- fila 105 CL: acuse_ran -> tramite_ran_evento / faltante
- fila 117 CL: acuse_ran -> tramite_ran_evento / faltante

Este importador:
- NO reescribe los 340 requisitos históricos;
- NO escribe las 36 contradicciones;
- NO crea Documento;
- sólo puede crear/reutilizar las seis claves nuevas;
- revalida las 340 claves históricas una por una;
- revalida que las 36 contradicciones sigan sin ExpedienteRequisito activo;
- revalida pertenencia territorial del objetivo antes de escribir;
- fuerza constraints antes del commit/rollback;
- exige idempotencia.

Estado final esperado:
- 346 ExpedienteRequisito CK/CL activos
- 243 pendiente_validacion
- 103 faltante
- 0 Documento
- por requisito:
    acta_asamblea                 20
    acta_eleccion_orv            39
    acta_no_verificativo          0
    acuse_ran                    65
    col_convenio_firmado         62
    constancia_orv_ran           24
    convocatoria_asamblea        16
    padron                       33
    soporte_caminamiento         43
    soporte_sensibilizacion      44

Seguridad:
- sólo DB_NAME=db_carga_excel
- schema 018
- SHA-256 exacto del Excel
- actor activo
- proyecto MEX-QRO
- CSV de reconciliación post-2F-R con cardinalidades exactas
- una sola transacción
- SET CONSTRAINTS ALL IMMEDIATE
- --dry-run => INSERT real + validaciones + ROLLBACK
- --confirmar => COMMIT
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402
from app.database import DB_NAME, SessionLocal  # noqa: E402
import importar_soporte_documental_ck_cl as base  # noqa: E402


EXPECTED_DB = "db_carga_excel"
EXPECTED_SCHEMA = "018"
EXPECTED_SHA256 = "bac01c25e9ff963f524fa8a48d69e74d92a0d36578731b1eca91f0e5a3573c3f"
PROJECT_KEY = "MEX-QRO"

EXPECTED_RECONCILED_KEYS = 382
EXPECTED_CREATE = 6
EXPECTED_REUSE_HISTORICAL = 340
EXPECTED_CONFLICTS = 36
EXPECTED_EXISTING_REVIEW = 0
EXPECTED_FINAL_DETERMINISTIC = 346

EXPECTED_FINAL_STATES = {
    "pendiente_validacion": 243,
    "faltante": 103,
}

EXPECTED_HISTORICAL_STATES = {
    "pendiente_validacion": 240,
    "faltante": 100,
}

EXPECTED_NEW_STATES = {
    "pendiente_validacion": 3,
    "faltante": 3,
}

EXPECTED_FINAL_BY_REQUIREMENT = {
    "acta_asamblea": 20,
    "acta_eleccion_orv": 39,
    "acta_no_verificativo": 0,
    "acuse_ran": 65,
    "col_convenio_firmado": 62,
    "constancia_orv_ran": 24,
    "convocatoria_asamblea": 16,
    "padron": 33,
    "soporte_caminamiento": 43,
    "soporte_sensibilizacion": 44,
}

EXPECTED_CONFLICTS_BY_REQUIREMENT = {
    "acta_eleccion_orv": 4,
    "acuse_ran": 3,
    "padron": 1,
    "soporte_caminamiento": 16,
    "soporte_sensibilizacion": 12,
}

# No se congelan target_id ni id_proyecto_nucleo. La identidad fuente se fija
# por requisito + tipo objetivo + estado + fila(s) + columna(s).
EXPECTED_CREATE_SIGNATURES = {
    (
        "acta_asamblea",
        "asamblea",
        "pendiente_validacion",
        (45,),
        ("CK",),
    ),
    (
        "acuse_ran",
        "tramite_ran_evento",
        "pendiente_validacion",
        (45,),
        ("CK",),
    ),
    (
        "convocatoria_asamblea",
        "asamblea_convocatoria",
        "pendiente_validacion",
        (92,),
        ("CK",),
    ),
    (
        "acuse_ran",
        "tramite_ran_evento",
        "faltante",
        (103,),
        ("CL",),
    ),
    (
        "acuse_ran",
        "tramite_ran_evento",
        "faltante",
        (105,),
        ("CL",),
    ),
    (
        "acuse_ran",
        "tramite_ran_evento",
        "faltante",
        (117,),
        ("CL",),
    ),
}


class ImportAbort(RuntimeError):
    pass


def parse_list_int(value: Any, field: str) -> tuple[int, ...]:
    raw = str(value or "").strip()
    if not raw:
        raise ImportAbort(f"{field} vacío.")
    try:
        values = tuple(sorted({int(part) for part in raw.split(";") if part.strip()}))
    except ValueError as exc:
        raise ImportAbort(f"{field} inválido: {value!r}") from exc
    if not values or any(item <= 0 for item in values):
        raise ImportAbort(f"{field} inválido: {value!r}")
    return values


def parse_list_text(value: Any) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                part.strip()
                for part in str(value or "").split(";")
                if part.strip()
            }
        )
    )


def row_signature(row: dict[str, str]) -> tuple:
    return (
        row["requirement"].strip(),
        row["target_type"].strip(),
        row["proposed_state"].strip(),
        parse_list_int(row["source_rows"], "source_rows"),
        parse_list_text(row["source_columns"]),
    )


def load_plan(path: Path) -> tuple[
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
]:
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))

    if len(rows) != EXPECTED_RECONCILED_KEYS:
        raise ImportAbort(
            "Cambió reconciliación post-2F-R: "
            f"esperado={EXPECTED_RECONCILED_KEYS}, actual={len(rows)}."
        )

    actions = Counter(row["action"].strip() for row in rows)
    expected_actions = {
        "CREATE_CANDIDATE": EXPECTED_CREATE,
        "REUSE_CANDIDATE": EXPECTED_REUSE_HISTORICAL,
        "CONFLICT_REVIEW": EXPECTED_CONFLICTS,
        "EXISTING_REVIEW": EXPECTED_EXISTING_REVIEW,
    }
    for action, expected in expected_actions.items():
        if actions[action] != expected:
            raise ImportAbort(
                f"Cambió {action}: esperado={expected}, actual={actions[action]}."
            )

    unexpected = {
        action
        for action, count in actions.items()
        if count and action not in expected_actions
    }
    if unexpected:
        raise ImportAbort(
            "Acciones inesperadas en reconciliación: "
            + ", ".join(sorted(unexpected))
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

    observed_signatures = {row_signature(row) for row in creates}
    if observed_signatures != EXPECTED_CREATE_SIGNATURES:
        raise ImportAbort(
            "Cambió el conjunto exacto de las seis claves nuevas 2I-B-R."
        )

    if len(observed_signatures) != EXPECTED_CREATE:
        raise ImportAbort("Las seis claves CREATE no son únicas.")

    deterministic = creates + reuses
    if len(deterministic) != EXPECTED_FINAL_DETERMINISTIC:
        raise ImportAbort(
            "Cambió conjunto determinista post-2F-R: "
            f"esperado={EXPECTED_FINAL_DETERMINISTIC}, "
            f"actual={len(deterministic)}."
        )

    seen_keys = set()
    state_counts = Counter()
    req_counts = Counter()
    create_states = Counter()
    reuse_states = Counter()

    for row in deterministic:
        pn_id = base.parse_int(row["id_proyecto_nucleo"], "id_proyecto_nucleo")
        target_id = base.parse_int(row["target_id"], "target_id")
        requirement = row["requirement"].strip()
        entity_type = row["target_type"].strip()
        state = row["proposed_state"].strip()
        canonical_detail = row["canonical_detail"]

        if entity_type not in base.ALLOWED_TARGET_TYPES:
            raise ImportAbort(f"Tipo objetivo no permitido: {entity_type!r}.")
        if state not in base.ALLOWED_STATES:
            raise ImportAbort(f"Estado no permitido: {state!r}.")
        if requirement not in EXPECTED_FINAL_BY_REQUIREMENT:
            raise ImportAbort(f"Requisito fuera del plan: {requirement!r}.")
        if not canonical_detail.strip():
            raise ImportAbort("canonical_detail vacío.")
        if "No se adjuntó Documento digital" not in canonical_detail:
            raise ImportAbort(
                "canonical_detail dejó de preservar la regla de no Documento."
            )

        key = (pn_id, requirement, entity_type, target_id)
        if key in seen_keys:
            raise ImportAbort(f"Clave determinista duplicada: {key!r}.")
        seen_keys.add(key)

        state_counts[state] += 1
        req_counts[requirement] += 1

        if row["action"].strip() == "CREATE_CANDIDATE":
            create_states[state] += 1
        else:
            reuse_states[state] += 1

    for state, expected in EXPECTED_FINAL_STATES.items():
        if state_counts[state] != expected:
            raise ImportAbort(
                f"Cambió estado final/{state}: "
                f"esperado={expected}, actual={state_counts[state]}."
            )

    for state, expected in EXPECTED_NEW_STATES.items():
        if create_states[state] != expected:
            raise ImportAbort(
                f"Cambió CREATE/{state}: "
                f"esperado={expected}, actual={create_states[state]}."
            )

    for state, expected in EXPECTED_HISTORICAL_STATES.items():
        if reuse_states[state] != expected:
            raise ImportAbort(
                f"Cambió REUSE histórico/{state}: "
                f"esperado={expected}, actual={reuse_states[state]}."
            )

    for requirement, expected in EXPECTED_FINAL_BY_REQUIREMENT.items():
        if req_counts[requirement] != expected:
            raise ImportAbort(
                f"Cambió total determinista/{requirement}: "
                f"esperado={expected}, actual={req_counts[requirement]}."
            )

    conflict_counts = Counter(
        row["requirement"].strip() for row in conflicts
    )
    for requirement, expected in EXPECTED_CONFLICTS_BY_REQUIREMENT.items():
        if conflict_counts[requirement] != expected:
            raise ImportAbort(
                f"Cambió conflicto/{requirement}: "
                f"esperado={expected}, actual={conflict_counts[requirement]}."
            )

    extra_conflicts = (
        set(conflict_counts) - set(EXPECTED_CONFLICTS_BY_REQUIREMENT)
    )
    if extra_conflicts:
        raise ImportAbort(
            "Conflictos fuera del plan histórico: "
            + ", ".join(sorted(extra_conflicts))
        )

    return creates, reuses, conflicts


def exact_existing(
    db,
    *,
    pn_id: int,
    requirement_id: int,
    entity_type: str,
    target_id: int,
):
    return (
        db.query(models.ExpedienteRequisito)
        .filter(
            models.ExpedienteRequisito.id_proyecto_nucleo == pn_id,
            models.ExpedienteRequisito.id_requisito == requirement_id,
            models.ExpedienteRequisito.entidad_tipo == entity_type,
            models.ExpedienteRequisito.entidad_id == target_id,
            models.ExpedienteRequisito.activo.is_(True),
        )
        .order_by(models.ExpedienteRequisito.id_expediente_requisito)
        .all()
    )


def validate_exact_req(
    req,
    *,
    state_id: int,
    canonical_detail: str,
) -> bool:
    return (
        req.id_estado == state_id
        and req.id_documento is None
        and req.detalle == canonical_detail
    )


def project_ckcl_rows(db, project_id: int, requirement_ids: set[int]):
    return (
        db.query(models.ExpedienteRequisito)
        .join(
            models.ProyectoNucleo,
            models.ProyectoNucleo.id_proyecto_nucleo
            == models.ExpedienteRequisito.id_proyecto_nucleo,
        )
        .filter(
            models.ProyectoNucleo.id_proyecto == project_id,
            models.ProyectoNucleo.activo.is_(True),
            models.ExpedienteRequisito.id_requisito.in_(requirement_ids),
            models.ExpedienteRequisito.activo.is_(True),
        )
        .all()
    )


def validate_historical_reuses(
    db,
    rows: list[dict[str, str]],
    *,
    pn_by_id,
    requirement_by_code,
    states,
) -> set[int]:
    ids = set()

    for row in rows:
        pn_id = base.parse_int(row["id_proyecto_nucleo"], "id_proyecto_nucleo")
        target_id = base.parse_int(row["target_id"], "target_id")
        requirement_code = row["requirement"].strip()
        entity_type = row["target_type"].strip()
        state_code = row["proposed_state"].strip()

        target_ok, target_detail = base.validate_target(
            db,
            pn_by_id[pn_id],
            entity_type,
            target_id,
        )
        if not target_ok:
            raise ImportAbort(
                "REUSE histórico dejó de tener objetivo válido: "
                f"{pn_id}/{requirement_code}/{entity_type}/{target_id}. "
                f"{target_detail}"
            )

        requirement = requirement_by_code[requirement_code]
        existing = exact_existing(
            db,
            pn_id=pn_id,
            requirement_id=requirement.id_requisito,
            entity_type=entity_type,
            target_id=target_id,
        )
        if len(existing) != 1:
            raise ImportAbort(
                "REUSE histórico ya no resuelve exactamente una fila: "
                f"{pn_id}/{requirement_code}/{entity_type}/{target_id}; "
                f"encontrados={len(existing)}."
            )

        req = existing[0]
        state_id = states[state_code].id_catalogo_opcion
        if not validate_exact_req(
            req,
            state_id=state_id,
            canonical_detail=row["canonical_detail"],
        ):
            raise ImportAbort(
                "REUSE histórico dejó de coincidir exactamente: "
                f"id_expediente_requisito={req.id_expediente_requisito}."
            )

        if req.id_expediente_requisito in ids:
            raise ImportAbort(
                "Un ExpedienteRequisito histórico resolvió a dos claves."
            )
        ids.add(req.id_expediente_requisito)

    if len(ids) != EXPECTED_REUSE_HISTORICAL:
        raise ImportAbort(
            f"REUSE históricos verificados != {EXPECTED_REUSE_HISTORICAL}."
        )
    return ids


def validate_conflicts_absent(
    db,
    rows: list[dict[str, str]],
    *,
    requirement_by_code,
) -> None:
    for row in rows:
        pn_id = base.parse_int(row["id_proyecto_nucleo"], "id_proyecto_nucleo")
        target_id = base.parse_int(row["target_id"], "target_id")
        requirement = requirement_by_code[row["requirement"].strip()]
        entity_type = row["target_type"].strip()

        existing = exact_existing(
            db,
            pn_id=pn_id,
            requirement_id=requirement.id_requisito,
            entity_type=entity_type,
            target_id=target_id,
        )
        if existing:
            raise ImportAbort(
                "Una clave CONFLICT_REVIEW tiene ExpedienteRequisito activo; "
                "2I-B-R no puede continuar: "
                f"{pn_id}/{row['requirement']}/{entity_type}/{target_id}."
            )


def validate_final_state(
    db,
    *,
    project_id: int,
    requirement_by_code,
    states,
    deterministic_rows: list[dict[str, str]],
    pn_by_id,
) -> list[int]:
    requirement_ids = {
        req.id_requisito for req in requirement_by_code.values()
    }
    rows = project_ckcl_rows(db, project_id, requirement_ids)

    if len(rows) != EXPECTED_FINAL_DETERMINISTIC:
        raise ImportAbort(
            "Postcheck CK/CL total falló: "
            f"esperado={EXPECTED_FINAL_DETERMINISTIC}, actual={len(rows)}."
        )

    state_by_id = {
        option.id_catalogo_opcion: option.codigo for option in states.values()
    }
    req_code_by_id = {
        req.id_requisito: code for code, req in requirement_by_code.items()
    }

    state_counts = Counter()
    req_counts = Counter()
    with_document = 0

    for req in rows:
        state_counts[state_by_id.get(req.id_estado, f"ID:{req.id_estado}")] += 1
        req_counts[req_code_by_id.get(req.id_requisito, f"ID:{req.id_requisito}")] += 1
        if req.id_documento is not None:
            with_document += 1

    for state, expected in EXPECTED_FINAL_STATES.items():
        if state_counts[state] != expected:
            raise ImportAbort(
                f"Postcheck estado/{state}: "
                f"esperado={expected}, actual={state_counts[state]}."
            )

    if with_document != 0:
        raise ImportAbort(
            f"Postcheck: hay {with_document} requisitos CK/CL con Documento."
        )

    for requirement, expected in EXPECTED_FINAL_BY_REQUIREMENT.items():
        if req_counts[requirement] != expected:
            raise ImportAbort(
                f"Postcheck requisito/{requirement}: "
                f"esperado={expected}, actual={req_counts[requirement]}."
            )

    deterministic_ids = set()
    for source in deterministic_rows:
        pn_id = base.parse_int(
            source["id_proyecto_nucleo"], "id_proyecto_nucleo"
        )
        target_id = base.parse_int(source["target_id"], "target_id")
        requirement_code = source["requirement"].strip()
        entity_type = source["target_type"].strip()
        state_code = source["proposed_state"].strip()

        target_ok, target_detail = base.validate_target(
            db,
            pn_by_id[pn_id],
            entity_type,
            target_id,
        )
        if not target_ok:
            raise ImportAbort(
                "Postcheck objetivo inválido: "
                f"{pn_id}/{requirement_code}/{entity_type}/{target_id}. "
                f"{target_detail}"
            )

        requirement = requirement_by_code[requirement_code]
        existing = exact_existing(
            db,
            pn_id=pn_id,
            requirement_id=requirement.id_requisito,
            entity_type=entity_type,
            target_id=target_id,
        )
        if len(existing) != 1:
            raise ImportAbort(
                "Postcheck clave determinista no resuelve exactamente una fila: "
                f"{pn_id}/{requirement_code}/{entity_type}/{target_id}."
            )

        req = existing[0]
        if not validate_exact_req(
            req,
            state_id=states[state_code].id_catalogo_opcion,
            canonical_detail=source["canonical_detail"],
        ):
            raise ImportAbort(
                "Postcheck clave determinista no coincide exactamente: "
                f"id_expediente_requisito={req.id_expediente_requisito}."
            )
        deterministic_ids.add(req.id_expediente_requisito)

    if len(deterministic_ids) != EXPECTED_FINAL_DETERMINISTIC:
        raise ImportAbort(
            "Postcheck: las 346 claves no resolvieron a 346 requisitos distintos."
        )

    return sorted(deterministic_ids)


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

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--confirmar", action="store_true")

    parser.add_argument("--actor-id", type=int, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/reportes/2i_b_post_2f_r"),
    )
    args = parser.parse_args()

    if DB_NAME != EXPECTED_DB:
        raise ImportAbort(
            f"Protección: DB_NAME debe ser {EXPECTED_DB!r}; recibido {DB_NAME!r}."
        )
    if not args.excel.exists():
        raise ImportAbort(f"No existe el Excel: {args.excel}")
    if not args.reconciliation_csv.exists():
        raise ImportAbort(
            f"No existe reconciliación: {args.reconciliation_csv}"
        )

    digest = base.sha256_file(args.excel)
    if digest != EXPECTED_SHA256:
        raise ImportAbort(
            "El SHA-256 no coincide con el Excel aprobado. "
            f"Esperado {EXPECTED_SHA256}; recibido {digest}."
        )

    creates, reuses, conflicts = load_plan(args.reconciliation_csv)
    deterministic = creates + reuses

    args.output_dir.mkdir(parents=True, exist_ok=True)
    mode_name = "confirmar" if args.confirmar else "dry-run"
    report_path = (
        args.output_dir
        / f"importacion_reparacion_soporte_documental_2i_b_r_{mode_name}.json"
    )

    db = SessionLocal()
    try:
        current_db = db.execute(text("SELECT current_database()")).scalar()
        current_schema = base.schema_version(db)

        if current_db != EXPECTED_DB or current_schema != EXPECTED_SCHEMA:
            raise ImportAbort(
                f"Destino inesperado: BD={current_db!r}, "
                f"schema={current_schema!r}."
            )

        actor = (
            db.query(models.Usuario)
            .filter(
                models.Usuario.id_usuario == args.actor_id,
                models.Usuario.activo.is_(True),
            )
            .one_or_none()
        )
        if actor is None:
            raise ImportAbort(
                f"Actor {args.actor_id} no existe o no está activo."
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
            raise ImportAbort(f"No existe proyecto activo {PROJECT_KEY!r}.")

        requirements = (
            db.query(models.RequisitoDocumental)
            .filter(
                models.RequisitoDocumental.codigo.in_(
                    set(EXPECTED_FINAL_BY_REQUIREMENT)
                ),
                models.RequisitoDocumental.activo.is_(True),
            )
            .all()
        )
        requirement_by_code = {row.codigo: row for row in requirements}
        missing_requirements = (
            set(EXPECTED_FINAL_BY_REQUIREMENT) - set(requirement_by_code)
        )
        if missing_requirements:
            raise ImportAbort(
                "Faltan requisitos documentales activos: "
                + ", ".join(sorted(missing_requirements))
            )

        states = base.catalog_by_code(db, "estado_requisito_documental")
        missing_states = base.ALLOWED_STATES - set(states)
        if missing_states:
            raise ImportAbort(
                "Faltan estados documentales: "
                + ", ".join(sorted(missing_states))
            )

        pn_ids = {
            base.parse_int(row["id_proyecto_nucleo"], "id_proyecto_nucleo")
            for row in deterministic
        }
        project_nuclei = (
            db.query(models.ProyectoNucleo)
            .filter(
                models.ProyectoNucleo.id_proyecto_nucleo.in_(pn_ids),
                models.ProyectoNucleo.id_proyecto == project.id_proyecto,
                models.ProyectoNucleo.activo.is_(True),
            )
            .all()
        )
        pn_by_id = {
            row.id_proyecto_nucleo: row for row in project_nuclei
        }
        missing_pn = pn_ids - set(pn_by_id)
        if missing_pn:
            raise ImportAbort(
                "ProyectoNucleo fuera de MEX-QRO/inactivo: "
                + ", ".join(map(str, sorted(missing_pn)))
            )

        historical_ids = validate_historical_reuses(
            db,
            reuses,
            pn_by_id=pn_by_id,
            requirement_by_code=requirement_by_code,
            states=states,
        )
        validate_conflicts_absent(
            db,
            conflicts,
            requirement_by_code=requirement_by_code,
        )

        requirement_ids = {
            req.id_requisito for req in requirement_by_code.values()
        }
        before_rows = project_ckcl_rows(
            db, project.id_proyecto, requirement_ids
        )
        before_count = len(before_rows)
        if before_count not in {340, 346}:
            raise ImportAbort(
                "Estado CK/CL previo inesperado: "
                f"esperado 340 o 346, actual={before_count}."
            )

        db.execute(
            text("SELECT set_config('app.current_user_id', :id, true)"),
            {"id": str(args.actor_id)},
        )

        runtime = Counter()
        runtime_by_state = Counter()
        runtime_by_requirement = Counter()
        touched = []

        for source in sorted(
            creates,
            key=lambda row: (
                min(parse_list_int(row["source_rows"], "source_rows")),
                row["requirement"],
                row["target_type"],
            ),
        ):
            pn_id = base.parse_int(
                source["id_proyecto_nucleo"], "id_proyecto_nucleo"
            )
            target_id = base.parse_int(source["target_id"], "target_id")
            requirement_code = source["requirement"].strip()
            entity_type = source["target_type"].strip()
            state_code = source["proposed_state"].strip()
            canonical_detail = source["canonical_detail"]

            pn = pn_by_id[pn_id]
            target_ok, target_detail = base.validate_target(
                db,
                pn,
                entity_type,
                target_id,
            )
            if not target_ok:
                raise ImportAbort(
                    "Objetivo 2I-B-R dejó de ser válido: "
                    f"PN={pn_id}, requisito={requirement_code}, "
                    f"{entity_type}/{target_id}. {target_detail}"
                )

            requirement = requirement_by_code[requirement_code]
            state_id = states[state_code].id_catalogo_opcion

            existing = exact_existing(
                db,
                pn_id=pn_id,
                requirement_id=requirement.id_requisito,
                entity_type=entity_type,
                target_id=target_id,
            )

            if not existing:
                req = models.ExpedienteRequisito(
                    id_proyecto_nucleo=pn_id,
                    entidad_tipo=entity_type,
                    entidad_id=target_id,
                    id_requisito=requirement.id_requisito,
                    id_estado=state_id,
                    id_documento=None,
                    detalle=canonical_detail,
                    creado_por=args.actor_id,
                    observaciones=(
                        f"Reparación migratoria 2I-B-R desde {args.excel.name}; "
                        "hoja INFORME M-Q; "
                        f"filas fuente={source['source_rows']}; "
                        f"columnas={source['source_columns']}; "
                        f"estado_fuente={source['source_states']}."
                    ),
                )
                db.add(req)
                db.flush()
                action = "CREATE"

            elif len(existing) == 1:
                req = existing[0]
                if not validate_exact_req(
                    req,
                    state_id=state_id,
                    canonical_detail=canonical_detail,
                ):
                    raise ImportAbort(
                        "La clave 2I-B-R ya existe pero no coincide; "
                        "no se sobrescribe: "
                        f"id_expediente_requisito="
                        f"{req.id_expediente_requisito}."
                    )
                action = "REUSE"

            else:
                raise ImportAbort(
                    "Hay múltiples ExpedienteRequisito para una clave 2I-B-R: "
                    f"{pn_id}/{requirement_code}/{entity_type}/{target_id}."
                )

            runtime[action] += 1
            runtime_by_state[(state_code, action)] += 1
            runtime_by_requirement[(requirement_code, action)] += 1

            touched.append({
                "action": action,
                "id_expediente_requisito": req.id_expediente_requisito,
                "id_proyecto_nucleo": pn_id,
                "requirement": requirement_code,
                "target_type": entity_type,
                "target_id": target_id,
                "state": state_code,
                "source_rows": source["source_rows"],
                "source_columns": source["source_columns"],
            })

        if runtime["CREATE"] + runtime["REUSE"] != EXPECTED_CREATE:
            raise ImportAbort("2I-B-R no procesó exactamente seis claves.")

        # No aceptamos estados parciales. Antes del primer commit debe ser 6/0;
        # después del commit debe ser 0/6.
        if (runtime["CREATE"], runtime["REUSE"]) not in {(6, 0), (0, 6)}:
            raise ImportAbort(
                "Estado parcial 2I-B-R no permitido: "
                f"CREATE={runtime['CREATE']} REUSE={runtime['REUSE']}."
            )

        for state, expected in EXPECTED_NEW_STATES.items():
            actual = (
                runtime_by_state[(state, "CREATE")]
                + runtime_by_state[(state, "REUSE")]
            )
            if actual != expected:
                raise ImportAbort(
                    f"Runtime nuevas/{state}: "
                    f"esperado={expected}, actual={actual}."
                )

        expected_new_by_req = {
            "acta_asamblea": 1,
            "acuse_ran": 4,
            "convocatoria_asamblea": 1,
        }
        for requirement, expected in expected_new_by_req.items():
            actual = (
                runtime_by_requirement[(requirement, "CREATE")]
                + runtime_by_requirement[(requirement, "REUSE")]
            )
            if actual != expected:
                raise ImportAbort(
                    f"Runtime nuevas/{requirement}: "
                    f"esperado={expected}, actual={actual}."
                )

        # Forzar constraints diferidos antes de validar el estado final.
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

        deterministic_ids = validate_final_state(
            db,
            project_id=project.id_proyecto,
            requirement_by_code=requirement_by_code,
            states=states,
            deterministic_rows=deterministic,
            pn_by_id=pn_by_id,
        )
        validate_conflicts_absent(
            db,
            conflicts,
            requirement_by_code=requirement_by_code,
        )

        if not historical_ids.issubset(set(deterministic_ids)):
            raise ImportAbort(
                "Los 340 requisitos históricos dejaron de estar contenidos "
                "en el estado final."
            )

        # Revalidar las seis como REUSE dentro de la misma transacción.
        intra_reuse = 0
        for source in creates:
            pn_id = base.parse_int(
                source["id_proyecto_nucleo"], "id_proyecto_nucleo"
            )
            target_id = base.parse_int(source["target_id"], "target_id")
            requirement = requirement_by_code[source["requirement"].strip()]
            existing = exact_existing(
                db,
                pn_id=pn_id,
                requirement_id=requirement.id_requisito,
                entity_type=source["target_type"].strip(),
                target_id=target_id,
            )
            if len(existing) != 1:
                raise ImportAbort(
                    "Idempotencia intratransacción: clave nueva no resuelve única."
                )
            req = existing[0]
            if not validate_exact_req(
                req,
                state_id=states[
                    source["proposed_state"].strip()
                ].id_catalogo_opcion,
                canonical_detail=source["canonical_detail"],
            ):
                raise ImportAbort(
                    "Idempotencia intratransacción: clave nueva no coincide."
                )
            intra_reuse += 1

        if intra_reuse != 6:
            raise ImportAbort(
                f"Idempotencia intratransacción REUSE != 6: {intra_reuse}."
            )

        report = {
            "mode": mode_name,
            "database": current_db,
            "schema": current_schema,
            "actor": {
                "id_usuario": actor.id_usuario,
                "correo": actor.correo,
            },
            "project": PROJECT_KEY,
            "excel": args.excel.name,
            "sha256": digest,
            "reconciliation_csv": str(args.reconciliation_csv),
            "plan": {
                "reconciled_keys": EXPECTED_RECONCILED_KEYS,
                "historical_reuse": EXPECTED_REUSE_HISTORICAL,
                "new_keys": EXPECTED_CREATE,
                "conflict_review": EXPECTED_CONFLICTS,
                "final_deterministic": EXPECTED_FINAL_DETERMINISTIC,
                "pendiente_validacion": 243,
                "faltante": 103,
            },
            "before_ckcl_active": before_count,
            "runtime": {
                "CREATE": runtime["CREATE"],
                "REUSE": runtime["REUSE"],
            },
            "intra_transaction": {
                "ckcl_active": EXPECTED_FINAL_DETERMINISTIC,
                "new_keys_reuse": intra_reuse,
                "documents": 0,
            },
            "touched": touched,
        }

        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        print("=== IMPORTACIÓN REPARACIÓN 2I-B-R — SOPORTE CK/CL ===")
        print(f"Modo: {mode_name}")
        print(f"BD: {current_db} / schema {current_schema}")
        print(f"Actor: {actor.id_usuario} / {actor.correo}")
        print(f"Proyecto: {PROJECT_KEY}")
        print(f"SHA-256: {digest}")
        print("Persistencia CK/CL al inicio:")
        print(f"  ExpedienteRequisito activos: {before_count}")
        print("Guardas históricas:")
        print("  REUSE históricos verificados: 340")
        print("  CONFLICT_REVIEW preservados:   36")
        print("Objetivos 2I-B-R:")
        print(f"  CREATE   {runtime['CREATE']}")
        print(f"  REUSE    {runtime['REUSE']}")
        print("Estado final intratransacción:")
        print("  ExpedienteRequisito CK/CL: 346")
        print("  pendiente_validacion:       243")
        print("  faltante:                   103")
        print("  con Documento:                0")
        print("  nuevas claves REUSE:           6")
        print("Claves 2I-B-R verificadas:")
        for item in touched:
            print(
                f"  {item['requirement']} -> "
                f"{item['target_type']}/{item['target_id']} | "
                f"{item['state']} | filas={item['source_rows']} | "
                f"columnas={item['source_columns']} | "
                f"id_expediente_requisito="
                f"{item['id_expediente_requisito']}"
            )

        if args.confirmar:
            db.commit()
            print("COMMIT realizado")
        else:
            db.rollback()
            print("ROLLBACK realizado (dry-run)")

        print(f"Reporte: {report_path}")
        return 0

    except IntegrityError as exc:
        db.rollback()
        print("=== IMPORTACIÓN 2I-B-R ABORTADA ===", file=sys.stderr)
        print(f"IntegrityError: {exc}", file=sys.stderr)
        return 2
    except (ImportAbort, base.ImportAbort) as exc:
        db.rollback()
        print("=== IMPORTACIÓN 2I-B-R ABORTADA ===", file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
