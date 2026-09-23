#!/usr/bin/env python3
"""Importación transaccional final 2J: SeguimientoEvento.

Contrato congelado
==================
Fuente primaria:
- Excel aprobado:
  SHA-256 bac01c25e9ff963f524fa8a48d69e74d92a0d36578731b1eca91f0e5a3573c3f

Fuente derivada auditada:
- resolucion_seguimiento_post_reparaciones.csv
- SHA-256:
  912d05e031a3edd08652fb7adb4a716ec1588137822cf2b998ca51f26e1361ee

Plan:
- 42 filas de resolución:
    38 CG/CJ
    4 continuaciones AI/AJ auditadas por 2B-R
- 17 eventos deterministas
- 25 REVIEW_DATE que NO se escriben
- desglose determinista:
    reunion                               8
    cambio_alcance/nueva_informacion     2
    medicion_bdt                         1
    continuacion_asamblea                6
- id_documento=NULL en los 17
- ámbito=colectivo
- continuacion_asamblea -> Asamblea base
- resto de eventos deterministas -> ProyectoNucleo

Seguridad
=========
- sólo DB_NAME=db_carga_excel
- schema 018
- proyecto MEX-QRO
- actor activo
- SHA-256 exacto de Excel y CSV de resolución
- cardinalidades y firmas semánticas congeladas
- validación de objetivo antes de escribir
- idempotencia por firma exacta:
    PN + entidad_tipo/id + ámbito + tipo + motivo + fecha + detalle + fuente
- no admite estado parcial: antes del primer commit 17/0; después 0/17
- SET CONSTRAINTS ALL IMMEDIATE
- --dry-run: INSERT real + revalidación intratransacción + ROLLBACK
- --confirmar: COMMIT

Este script NO crea Documento ni modifica eventos existentes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402
from app.database import DB_NAME, SessionLocal  # noqa: E402

import resolver_seguimiento_post_reparaciones_2j as resolver  # noqa: E402


EXPECTED_DB = "db_carga_excel"
EXPECTED_SCHEMA = "018"
EXPECTED_PROJECT = "MEX-QRO"

EXPECTED_EXCEL_SHA256 = (
    "bac01c25e9ff963f524fa8a48d69e74d92a0d36578731b1eca91f0e5a3573c3f"
)
EXPECTED_RESOLUTION_SHA256 = (
    "912d05e031a3edd08652fb7adb4a716ec1588137822cf2b998ca51f26e1361ee"
)

EXPECTED_RESOLUTION_ROWS = 42
EXPECTED_ORIGINS = {
    "CG_CJ": 38,
    "2B_R_AI_AJ": 4,
}
EXPECTED_DETERMINISTIC = 17
EXPECTED_REVIEW_DATE = 25

EXPECTED_BY_EVENT = {
    ("cambio_alcance", "nueva_informacion"): 2,
    ("continuacion_asamblea", ""): 6,
    ("medicion_bdt", ""): 1,
    ("reunion", ""): 8,
}

EXPECTED_CONTINUATIONS = {
    ("MEXICO|COYOTEPEC|COYOTEPEC", "CJ", 45, "2025-10-18"),
    ("HIDALGO|TULA DE ALLENDE|TULA DE ALLENDE", "CJ", 92, "2025-08-17"),
    ("HIDALGO|CHAPANTONGO|JUCHITLAN", "AJ", 103, "2025-09-09"),
    ("HIDALGO|CHAPANTONGO|SAN JOSE EL MARQUEZ", "AJ", 105, "2025-09-09"),
    ("MEXICO|JILOTEPEC|SANTIAGO OXTHOC", "AJ", 117, "2025-09-07"),
    ("QUERETARO|SAN JUAN DEL RIO|PASO DE MATA", "AI", 136, "2025-08-31"),
}

ALLOWED_TARGET_TYPES = {"proyecto_nucleo", "asamblea"}

SUPPLIED_MODEL_FIELDS = {
    "id_proyecto_nucleo",
    "entidad_tipo",
    "entidad_id",
    "ambito",
    "id_tipo_evento",
    "id_motivo",
    "fecha_evento",
    "detalle",
    "id_documento",
    "fuente",
    "activo",
    "creado_por",
}


class ImportAbort(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def schema_version(db) -> str | None:
    return db.execute(
        text("SELECT max(version) FROM schema_migrations")
    ).scalar()


def parse_int(value: Any, field: str) -> int:
    raw = str(value or "").strip()
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ImportAbort(f"{field} inválido: {value!r}") from exc
    if parsed <= 0:
        raise ImportAbort(f"{field} debe ser > 0: {parsed}")
    return parsed


def parse_date(value: Any, field: str) -> date:
    raw = str(value or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ImportAbort(f"{field} inválida: {value!r}") from exc


def model_column_names(model) -> set[str]:
    return {column.name for column in model.__table__.columns}


def required_unhandled_columns(model, supplied: set[str]) -> list[str]:
    unhandled = []
    for column in model.__table__.columns:
        if column.primary_key:
            continue
        if column.name in supplied:
            continue
        if column.nullable:
            continue
        if column.default is not None or column.server_default is not None:
            continue
        if column.name in {
            "creado_en",
            "actualizado_en",
            "creado_por",
            "actualizado_por",
            "activo",
        }:
            continue
        unhandled.append(column.name)
    return unhandled


def validate_model_shape() -> None:
    missing = required_unhandled_columns(
        models.SeguimientoEvento,
        SUPPLIED_MODEL_FIELDS,
    )
    if missing:
        raise ImportAbort(
            "SeguimientoEvento tiene columnas NOT NULL sin regla 2J: "
            + ", ".join(missing)
        )


def load_resolution(path: Path) -> tuple[
    list[dict[str, str]],
    list[dict[str, str]],
]:
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))

    if len(rows) != EXPECTED_RESOLUTION_ROWS:
        raise ImportAbort(
            "Cambió cardinalidad de resolución 2J: "
            f"esperado={EXPECTED_RESOLUTION_ROWS}, actual={len(rows)}."
        )

    origins = Counter(row["origin"].strip() for row in rows)
    if origins != Counter(EXPECTED_ORIGINS):
        raise ImportAbort(
            f"Cambió desglose origin 2J: {dict(origins)!r}."
        )

    resolutions = Counter(row["resolution"].strip() for row in rows)

    deterministic = [
        row
        for row in rows
        if row["resolution"].strip()
        in {"CREATE_CANDIDATE", "REUSE_CANDIDATE"}
    ]
    review_date = [
        row
        for row in rows
        if row["resolution"].strip() == "REVIEW_DATE"
    ]

    if len(deterministic) != EXPECTED_DETERMINISTIC:
        raise ImportAbort(
            "Cambió conjunto determinista 2J: "
            f"esperado={EXPECTED_DETERMINISTIC}, actual={len(deterministic)}."
        )

    if len(review_date) != EXPECTED_REVIEW_DATE:
        raise ImportAbort(
            "Cambió REVIEW_DATE 2J: "
            f"esperado={EXPECTED_REVIEW_DATE}, actual={len(review_date)}."
        )

    for code in (
        "BLOCKED_TARGET",
        "REVIEW_TARGET",
        "REVIEW_EXISTING",
        "SKIP_SOURCE",
    ):
        if resolutions[code] != 0:
            raise ImportAbort(
                f"Resolución inesperada {code}={resolutions[code]}."
            )

    if any(row["origin"].strip() != "CG_CJ" for row in review_date):
        raise ImportAbort(
            "Apareció REVIEW_DATE fuera de CG/CJ."
        )

    event_counts = Counter(
        (row["event_type"].strip(), row["motive"].strip())
        for row in deterministic
    )
    if event_counts != Counter(EXPECTED_BY_EVENT):
        raise ImportAbort(
            f"Cambió desglose determinista: {dict(event_counts)!r}."
        )

    continuation_sources = {
        (
            row["source_key"].strip(),
            row["column"].strip(),
            parse_int(row["row"], "row"),
            row["fecha_evento"].strip(),
        )
        for row in deterministic
        if row["event_type"].strip() == "continuacion_asamblea"
    }
    if continuation_sources != EXPECTED_CONTINUATIONS:
        raise ImportAbort(
            "Cambió el conjunto fuente de las seis continuaciones."
        )

    return rows, deterministic


def validate_target(
    db,
    *,
    pn_id: int,
    target_type: str,
    target_id: int,
) -> None:
    if target_type == "proyecto_nucleo":
        if target_id != pn_id:
            raise ImportAbort(
                "Evento ProyectoNucleo apunta a PN distinto: "
                f"pn={pn_id}, target={target_id}."
            )
        pn = db.get(models.ProyectoNucleo, pn_id)
        if pn is None or not pn.activo:
            raise ImportAbort(
                f"ProyectoNucleo inexistente/inactivo: {pn_id}."
            )
        return

    if target_type == "asamblea":
        assembly = db.get(models.Asamblea, target_id)
        if assembly is None or not assembly.activo:
            raise ImportAbort(
                f"Asamblea inexistente/inactiva: {target_id}."
            )
        if assembly.id_proyecto_nucleo != pn_id:
            raise ImportAbort(
                f"Asamblea {target_id} no pertenece a PN {pn_id}."
            )
        return

    raise ImportAbort(
        f"Tipo de objetivo no permitido: {target_type!r}."
    )


def exact_existing(
    db,
    *,
    pn_id: int,
    target_type: str,
    target_id: int,
    event_type_id: int,
    motive_id: int | None,
    event_date: date,
    detail: str,
    source: str,
):
    query = db.query(models.SeguimientoEvento).filter(
        models.SeguimientoEvento.id_proyecto_nucleo == pn_id,
        models.SeguimientoEvento.entidad_tipo == target_type,
        models.SeguimientoEvento.entidad_id == target_id,
        models.SeguimientoEvento.ambito == "colectivo",
        models.SeguimientoEvento.id_tipo_evento == event_type_id,
        models.SeguimientoEvento.fecha_evento == event_date,
        models.SeguimientoEvento.detalle == detail,
        models.SeguimientoEvento.id_documento.is_(None),
        models.SeguimientoEvento.fuente == source,
        models.SeguimientoEvento.activo.is_(True),
    )
    if motive_id is None:
        query = query.filter(
            models.SeguimientoEvento.id_motivo.is_(None)
        )
    else:
        query = query.filter(
            models.SeguimientoEvento.id_motivo == motive_id
        )

    return query.order_by(
        models.SeguimientoEvento.id_seguimiento_evento
    ).all()


def normalize_candidate(
    row: dict[str, str],
    *,
    event_catalog,
    motive_catalog,
) -> dict[str, Any]:
    pn_id = parse_int(
        row["id_proyecto_nucleo"],
        "id_proyecto_nucleo",
    )
    target_type = row["target_type"].strip()
    target_id = parse_int(row["target_id"], "target_id")
    event_type = row["event_type"].strip()
    motive = row["motive"].strip()
    event_date = parse_date(row["fecha_evento"], "fecha_evento")
    detail = row["clause"]
    source = row["fuente"]

    if target_type not in ALLOWED_TARGET_TYPES:
        raise ImportAbort(
            f"target_type fuera del plan: {target_type!r}."
        )

    if event_type not in event_catalog:
        raise ImportAbort(
            f"Falta tipo_evento_seguimiento/{event_type}."
        )

    if not detail.strip():
        raise ImportAbort(
            f"Detalle vacío en fila {row['row']} col {row['column']}."
        )
    if not source.strip():
        raise ImportAbort(
            f"Fuente vacía en fila {row['row']} col {row['column']}."
        )

    if event_type == "continuacion_asamblea":
        if target_type != "asamblea":
            raise ImportAbort(
                "continuacion_asamblea debe apuntar a Asamblea."
            )
        if motive:
            raise ImportAbort(
                "continuacion_asamblea no debe tener motivo."
            )
    else:
        if target_type != "proyecto_nucleo":
            raise ImportAbort(
                f"{event_type} debe apuntar a ProyectoNucleo."
            )

    if event_type == "cambio_alcance":
        if motive != "nueva_informacion":
            raise ImportAbort(
                "cambio_alcance determinista debe usar "
                "motivo nueva_informacion."
            )
    elif motive:
        raise ImportAbort(
            f"{event_type} no debe llevar motivo {motive!r}."
        )

    motive_id = None
    if motive:
        if motive not in motive_catalog:
            raise ImportAbort(
                f"Falta motivo_seguimiento/{motive}."
            )
        motive_id = motive_catalog[motive].id_catalogo_opcion

    return {
        "row": parse_int(row["row"], "row"),
        "column": row["column"].strip(),
        "origin": row["origin"].strip(),
        "source_key": row["source_key"].strip(),
        "pn_id": pn_id,
        "target_type": target_type,
        "target_id": target_id,
        "event_type": event_type,
        "event_type_id": event_catalog[event_type].id_catalogo_opcion,
        "motive": motive,
        "motive_id": motive_id,
        "event_date": event_date,
        "detail": detail,
        "source": source,
    }


def create_event(
    db,
    *,
    item: dict[str, Any],
    actor_id: int,
) -> models.SeguimientoEvento:
    data = {
        "id_proyecto_nucleo": item["pn_id"],
        "entidad_tipo": item["target_type"],
        "entidad_id": item["target_id"],
        "ambito": "colectivo",
        "id_tipo_evento": item["event_type_id"],
        "id_motivo": item["motive_id"],
        "fecha_evento": item["event_date"],
        "detalle": item["detail"],
        "id_documento": None,
        "fuente": item["source"],
        "activo": True,
        "creado_por": actor_id,
    }

    columns = model_column_names(models.SeguimientoEvento)
    event = models.SeguimientoEvento(
        **{key: value for key, value in data.items() if key in columns}
    )
    db.add(event)
    db.flush()
    return event


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("excel", type=Path)
    parser.add_argument(
        "--resolution-csv",
        type=Path,
        default=Path(
            "/data/reportes/2j_post_reparaciones/"
            "resolucion_seguimiento_post_reparaciones.csv"
        ),
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--confirmar", action="store_true")

    parser.add_argument("--actor-id", type=int, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/reportes/2j_post_reparaciones"),
    )
    args = parser.parse_args()

    if DB_NAME != EXPECTED_DB:
        raise ImportAbort(
            f"Protección: DB_NAME debe ser {EXPECTED_DB!r}; "
            f"recibido={DB_NAME!r}."
        )
    if not args.excel.exists():
        raise ImportAbort(f"No existe Excel: {args.excel}.")
    if not args.resolution_csv.exists():
        raise ImportAbort(
            f"No existe resolución 2J: {args.resolution_csv}."
        )

    excel_sha = sha256_file(args.excel)
    if excel_sha != EXPECTED_EXCEL_SHA256:
        raise ImportAbort(
            "SHA-256 del Excel no coincide: "
            f"esperado={EXPECTED_EXCEL_SHA256}, actual={excel_sha}."
        )

    resolution_sha = sha256_file(args.resolution_csv)
    if resolution_sha != EXPECTED_RESOLUTION_SHA256:
        raise ImportAbort(
            "SHA-256 del CSV de resolución 2J no coincide: "
            f"esperado={EXPECTED_RESOLUTION_SHA256}, "
            f"actual={resolution_sha}."
        )

    _rows, deterministic_rows = load_resolution(
        args.resolution_csv
    )
    validate_model_shape()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    mode_name = "confirmar" if args.confirmar else "dry-run"
    report_path = (
        args.output_dir
        / f"importacion_seguimiento_2j_{mode_name}.json"
    )

    db = SessionLocal()
    try:
        current_db = db.execute(
            text("SELECT current_database()")
        ).scalar()
        current_schema = schema_version(db)

        if (
            current_db != EXPECTED_DB
            or current_schema != EXPECTED_SCHEMA
        ):
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
                models.Proyecto.clave_proyecto == EXPECTED_PROJECT,
                models.Proyecto.activo.is_(True),
            )
            .one_or_none()
        )
        if project is None:
            raise ImportAbort(
                f"No existe proyecto activo {EXPECTED_PROJECT!r}."
            )

        event_catalog = resolver.catalog_by_code(
            db,
            "tipo_evento_seguimiento",
        )
        motive_catalog = resolver.catalog_by_code(
            db,
            "motivo_seguimiento",
        )

        missing_events = {
            event_type
            for event_type, _motive in EXPECTED_BY_EVENT
        } - set(event_catalog)
        if missing_events:
            raise ImportAbort(
                "Faltan tipos de seguimiento: "
                + ", ".join(sorted(missing_events))
            )

        if "nueva_informacion" not in motive_catalog:
            raise ImportAbort(
                "Falta motivo_seguimiento/nueva_informacion."
            )

        candidates = [
            normalize_candidate(
                row,
                event_catalog=event_catalog,
                motive_catalog=motive_catalog,
            )
            for row in deterministic_rows
        ]

        # Evita duplicados internos en el plan.
        signatures = set()
        for item in candidates:
            validate_target(
                db,
                pn_id=item["pn_id"],
                target_type=item["target_type"],
                target_id=item["target_id"],
            )
            signature = (
                item["pn_id"],
                item["target_type"],
                item["target_id"],
                item["event_type_id"],
                item["motive_id"],
                item["event_date"],
                item["detail"],
                item["source"],
            )
            if signature in signatures:
                raise ImportAbort(
                    "Dos candidatos 2J tienen la misma firma exacta."
                )
            signatures.add(signature)

        # Estado inicial: sólo aceptamos completamente nuevo o completamente
        # importado. Un estado parcial obliga a investigar.
        initial = Counter()
        initial_existing_ids: dict[tuple, int] = {}

        for item in candidates:
            existing = exact_existing(
                db,
                pn_id=item["pn_id"],
                target_type=item["target_type"],
                target_id=item["target_id"],
                event_type_id=item["event_type_id"],
                motive_id=item["motive_id"],
                event_date=item["event_date"],
                detail=item["detail"],
                source=item["source"],
            )
            if len(existing) == 0:
                initial["CREATE"] += 1
            elif len(existing) == 1:
                initial["REUSE"] += 1
                key = (
                    item["row"],
                    item["column"],
                    item["source_key"],
                    item["event_type"],
                    item["event_date"].isoformat(),
                )
                initial_existing_ids[key] = (
                    existing[0].id_seguimiento_evento
                )
            else:
                raise ImportAbort(
                    "Múltiples SeguimientoEvento exactos antes de importar: "
                    f"fila={item['row']} col={item['column']}."
                )

        if (
            initial["CREATE"],
            initial["REUSE"],
        ) not in {
            (EXPECTED_DETERMINISTIC, 0),
            (0, EXPECTED_DETERMINISTIC),
        }:
            raise ImportAbort(
                "Estado parcial 2J no permitido al inicio: "
                f"CREATE={initial['CREATE']} "
                f"REUSE={initial['REUSE']}."
            )

        db.execute(
            text(
                "SELECT set_config('app.current_user_id', :id, true)"
            ),
            {"id": str(args.actor_id)},
        )

        runtime = Counter()
        touched = []

        for item in sorted(
            candidates,
            key=lambda x: (
                x["row"],
                x["column"],
                x["event_type"],
                x["source_key"],
            ),
        ):
            validate_target(
                db,
                pn_id=item["pn_id"],
                target_type=item["target_type"],
                target_id=item["target_id"],
            )

            existing = exact_existing(
                db,
                pn_id=item["pn_id"],
                target_type=item["target_type"],
                target_id=item["target_id"],
                event_type_id=item["event_type_id"],
                motive_id=item["motive_id"],
                event_date=item["event_date"],
                detail=item["detail"],
                source=item["source"],
            )

            if len(existing) == 0:
                event = create_event(
                    db,
                    item=item,
                    actor_id=args.actor_id,
                )
                action = "CREATE"

            elif len(existing) == 1:
                event = existing[0]
                action = "REUSE"

                # No se reutiliza una fila "parecida": exact_existing ya
                # exige id_documento NULL y todos los campos canónicos.
                if event.creado_por is None:
                    # No es requisito de idempotencia que el actor histórico
                    # sea el mismo; únicamente no aceptamos una fila inválida
                    # sin auditoría si el modelo la permite.
                    pass

            else:
                raise ImportAbort(
                    "Múltiples SeguimientoEvento exactos durante importación: "
                    f"fila={item['row']} col={item['column']}."
                )

            runtime[action] += 1
            touched.append({
                "action": action,
                "id_seguimiento_evento": event.id_seguimiento_evento,
                "row": item["row"],
                "column": item["column"],
                "origin": item["origin"],
                "source_key": item["source_key"],
                "event_type": item["event_type"],
                "motive": item["motive"],
                "fecha_evento": item["event_date"].isoformat(),
                "id_proyecto_nucleo": item["pn_id"],
                "target_type": item["target_type"],
                "target_id": item["target_id"],
                "fuente": item["source"],
            })

        if (
            runtime["CREATE"],
            runtime["REUSE"],
        ) not in {
            (EXPECTED_DETERMINISTIC, 0),
            (0, EXPECTED_DETERMINISTIC),
        }:
            raise ImportAbort(
                "Estado parcial 2J no permitido en runtime: "
                f"CREATE={runtime['CREATE']} "
                f"REUSE={runtime['REUSE']}."
            )

        # No permite que el estado cambie entre precheck y runtime.
        if (
            runtime["CREATE"] != initial["CREATE"]
            or runtime["REUSE"] != initial["REUSE"]
        ):
            raise ImportAbort(
                "El estado 2J cambió dentro de la ejecución antes del "
                "postcheck."
            )

        # Fuerza constraints diferidos antes de considerar válido el lote.
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

        # Postcheck intratransacción: los 17 deben resolver ahora exactamente
        # a una fila y, por tanto, comportarse como REUSE.
        verified = []
        intra_event_counts = Counter()

        for item in candidates:
            validate_target(
                db,
                pn_id=item["pn_id"],
                target_type=item["target_type"],
                target_id=item["target_id"],
            )
            existing = exact_existing(
                db,
                pn_id=item["pn_id"],
                target_type=item["target_type"],
                target_id=item["target_id"],
                event_type_id=item["event_type_id"],
                motive_id=item["motive_id"],
                event_date=item["event_date"],
                detail=item["detail"],
                source=item["source"],
            )
            if len(existing) != 1:
                raise ImportAbort(
                    "Postcheck intratransacción no resolvió exactamente una "
                    "fila para: "
                    f"fila={item['row']} col={item['column']}."
                )

            event = existing[0]
            if event.id_documento is not None:
                raise ImportAbort(
                    "Postcheck: un evento 2J tiene id_documento no NULL."
                )
            if event.ambito != "colectivo":
                raise ImportAbort(
                    "Postcheck: un evento 2J dejó ámbito colectivo."
                )

            intra_event_counts[
                (item["event_type"], item["motive"])
            ] += 1

            verified.append({
                "id_seguimiento_evento": event.id_seguimiento_evento,
                "row": item["row"],
                "column": item["column"],
                "source_key": item["source_key"],
                "event_type": item["event_type"],
                "motive": item["motive"],
                "fecha_evento": item["event_date"].isoformat(),
                "target_type": item["target_type"],
                "target_id": item["target_id"],
            })

        if len(verified) != EXPECTED_DETERMINISTIC:
            raise ImportAbort(
                "Postcheck intratransacción no verificó 17 eventos."
            )

        if intra_event_counts != Counter(EXPECTED_BY_EVENT):
            raise ImportAbort(
                "Postcheck intratransacción cambió desglose por evento: "
                f"{dict(intra_event_counts)!r}."
            )

        # Verificación adicional: no hay dos IDs distintos para la misma
        # firma y tampoco un mismo ID cubriendo dos firmas.
        verified_ids = {
            item["id_seguimiento_evento"]
            for item in verified
        }
        if len(verified_ids) != EXPECTED_DETERMINISTIC:
            raise ImportAbort(
                "Los 17 candidatos no resolvieron a 17 IDs distintos."
            )

        report = {
            "mode": mode_name,
            "database": current_db,
            "schema": current_schema,
            "actor": {
                "id_usuario": actor.id_usuario,
                "correo": actor.correo,
            },
            "project": EXPECTED_PROJECT,
            "excel": args.excel.name,
            "excel_sha256": excel_sha,
            "resolution_csv": str(args.resolution_csv),
            "resolution_sha256": resolution_sha,
            "plan": {
                "resolution_rows": EXPECTED_RESOLUTION_ROWS,
                "deterministic": EXPECTED_DETERMINISTIC,
                "review_date_preserved": EXPECTED_REVIEW_DATE,
                "documents": 0,
            },
            "initial": {
                "CREATE": initial["CREATE"],
                "REUSE": initial["REUSE"],
            },
            "runtime": {
                "CREATE": runtime["CREATE"],
                "REUSE": runtime["REUSE"],
            },
            "intra_transaction": {
                "exact_reuse": len(verified),
                "distinct_ids": len(verified_ids),
                "by_event": [
                    {
                        "event_type": event_type,
                        "motive": motive,
                        "count": count,
                    }
                    for (event_type, motive), count
                    in sorted(intra_event_counts.items())
                ],
            },
            "touched": touched,
            "verified": verified,
        }

        report_path.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        print("=== IMPORTACIÓN 2J — SEGUIMIENTO ===")
        print(f"Modo: {mode_name}")
        print(f"BD: {current_db} / schema {current_schema}")
        print(f"Actor: {actor.id_usuario} / {actor.correo}")
        print(f"Proyecto: {EXPECTED_PROJECT}")
        print(f"SHA-256 Excel:      {excel_sha}")
        print(f"SHA-256 resolución: {resolution_sha}")
        print("Plan preservado:")
        print("  deterministas:       17")
        print("  REVIEW_DATE:         25")
        print("  Documento:            0")
        print("Estado al inicio:")
        print(f"  CREATE:              {initial['CREATE']}")
        print(f"  REUSE:               {initial['REUSE']}")
        print("Runtime:")
        print(f"  CREATE:              {runtime['CREATE']}")
        print(f"  REUSE:               {runtime['REUSE']}")
        print("Validación intratransacción:")
        print(f"  REUSE exactos:       {len(verified)}")
        print(f"  IDs distintos:       {len(verified_ids)}")
        print("  por tipo:")
        for (event_type, motive), count in sorted(
            intra_event_counts.items()
        ):
            label = (
                event_type
                + (f"/{motive}" if motive else "")
            )
            print(f"    {label:<40} {count}")

        print("Eventos 2J verificados:")
        for item in sorted(
            verified,
            key=lambda x: (
                x["row"],
                x["column"],
                x["event_type"],
            ),
        ):
            motive_label = (
                f"/{item['motive']}"
                if item["motive"]
                else ""
            )
            print(
                f"  fila={item['row']} col={item['column']} | "
                f"{item['source_key']} | "
                f"{item['event_type']}{motive_label} | "
                f"{item['fecha_evento']} | "
                f"{item['target_type']}/{item['target_id']} | "
                f"id_seguimiento_evento="
                f"{item['id_seguimiento_evento']}"
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
        print("=== IMPORTACIÓN 2J ABORTADA ===", file=sys.stderr)
        print(f"IntegrityError: {exc}", file=sys.stderr)
        print(
            "ROLLBACK realizado; no se confirmó ningún cambio.",
            file=sys.stderr,
        )
        return 2

    except (ImportAbort, resolver.ResolveAbort) as exc:
        db.rollback()
        print("=== IMPORTACIÓN 2J ABORTADA ===", file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        print(
            "ROLLBACK realizado; no se confirmó ningún cambio.",
            file=sys.stderr,
        )
        return 2

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
