#!/usr/bin/env python3
"""Preflight read-only 2J: SeguimientoEvento post-reparaciones.

Entrada contractual:
- Excel aprobado.
- CSV generado por resolver_seguimiento_post_reparaciones_2j.py.

Este paso NO reinterpreta texto libre. Valida que el resultado del resolver
cumpla exactamente el plan congelado y que cada uno de los 17 eventos
deterministas pueda escribirse contra el backend real.

Plan esperado:
- 42 filas en resolución: 38 CG/CJ + 4 continuaciones AI/AJ de 2B-R.
- 17 deterministas.
- 25 REVIEW_DATE preservados.
- CREATE=17 / REUSE=0 antes de importar 2J.
- 0 BLOCKED_TARGET / REVIEW_TARGET / REVIEW_EXISTING / SKIP_SOURCE.
- deterministas:
    reunion                              8
    cambio_alcance/nueva_informacion    2
    medicion_bdt                        1
    continuacion_asamblea               6
- objetivos permitidos:
    proyecto_nucleo
    asamblea
- las seis continuaciones deben apuntar a Asamblea.
- no se crea Documento.

El preflight:
1) valida BD/schema/proyecto/SHA del Excel;
2) calcula y reporta SHA-256 del CSV de resolución para congelarlo después;
3) valida cardinalidades y firmas semánticas;
4) valida catálogos;
5) valida pertenencia de cada objetivo al ProyectoNucleo;
6) valida que el modelo SeguimientoEvento no tenga columnas NOT NULL sin regla;
7) recalcula existencia exacta en PostgreSQL;
8) imprime las 17 filas deterministas para congelar el importador.

NO realiza escrituras.
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

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402
from app.database import DB_NAME, SessionLocal  # noqa: E402
import resolver_seguimiento_post_reparaciones_2j as resolver  # noqa: E402


EXPECTED_DB = "db_carga_excel"
EXPECTED_SCHEMA = "018"
EXPECTED_EXCEL_SHA256 = "bac01c25e9ff963f524fa8a48d69e74d92a0d36578731b1eca91f0e5a3573c3f"
PROJECT_KEY = "MEX-QRO"

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

EXPECTED_CONTINUATION_SOURCE = {
    ("MEXICO|COYOTEPEC|COYOTEPEC", "CJ", 45, "2025-10-18"),
    ("HIDALGO|TULA DE ALLENDE|TULA DE ALLENDE", "CJ", 92, "2025-08-17"),
    ("HIDALGO|CHAPANTONGO|JUCHITLAN", "AJ", 103, "2025-09-09"),
    ("HIDALGO|CHAPANTONGO|SAN JOSE EL MARQUEZ", "AJ", 105, "2025-09-09"),
    ("MEXICO|JILOTEPEC|SANTIAGO OXTHOC", "AJ", 117, "2025-09-07"),
    ("QUERETARO|SAN JUAN DEL RIO|PASO DE MATA", "AI", 136, "2025-08-31"),
}

ALLOWED_TARGET_TYPES = {"proyecto_nucleo", "asamblea"}


class PreflightAbort(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def schema_version(db) -> str | None:
    return db.execute(text("SELECT max(version) FROM schema_migrations")).scalar()


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
    supplied = {
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
    missing = required_unhandled_columns(models.SeguimientoEvento, supplied)
    if missing:
        raise PreflightAbort(
            "SeguimientoEvento tiene columnas NOT NULL sin regla 2J: "
            + ", ".join(missing)
        )


def parse_int(value: Any, field: str) -> int:
    raw = str(value or "").strip()
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise PreflightAbort(f"{field} inválido: {value!r}") from exc
    if parsed <= 0:
        raise PreflightAbort(f"{field} debe ser >0: {parsed}")
    return parsed


def parse_date(value: Any, field: str) -> date:
    raw = str(value or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise PreflightAbort(f"{field} inválida: {value!r}") from exc


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
        query = query.filter(models.SeguimientoEvento.id_motivo.is_(None))
    else:
        query = query.filter(models.SeguimientoEvento.id_motivo == motive_id)

    return query.order_by(models.SeguimientoEvento.id_seguimiento_evento).all()


def validate_target(db, *, pn_id: int, target_type: str, target_id: int) -> str:
    if target_type == "proyecto_nucleo":
        if target_id != pn_id:
            raise PreflightAbort(
                "Evento proyecto_nucleo debe apuntar a su propio PN: "
                f"pn={pn_id}, target={target_id}."
            )
        pn = db.get(models.ProyectoNucleo, pn_id)
        if pn is None or not pn.activo:
            raise PreflightAbort(f"ProyectoNucleo inactivo/inexistente: {pn_id}.")
        return f"ProyectoNucleo/{pn_id}"

    if target_type == "asamblea":
        assembly = db.get(models.Asamblea, target_id)
        if assembly is None or not assembly.activo:
            raise PreflightAbort(f"Asamblea inactiva/inexistente: {target_id}.")
        if assembly.id_proyecto_nucleo != pn_id:
            raise PreflightAbort(
                f"Asamblea {target_id} no pertenece a PN {pn_id}."
            )
        return f"Asamblea/{target_id}"

    raise PreflightAbort(f"Tipo de objetivo no permitido: {target_type!r}.")


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
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/reportes/2j_post_reparaciones"),
    )
    args = parser.parse_args()

    if DB_NAME != EXPECTED_DB:
        raise PreflightAbort(
            f"Protección: DB_NAME debe ser {EXPECTED_DB!r}; recibido {DB_NAME!r}."
        )
    if not args.excel.exists():
        raise PreflightAbort(f"No existe Excel: {args.excel}")
    if not args.resolution_csv.exists():
        raise PreflightAbort(
            f"No existe resolución 2J: {args.resolution_csv}"
        )

    excel_sha = sha256_file(args.excel)
    if excel_sha != EXPECTED_EXCEL_SHA256:
        raise PreflightAbort(
            "SHA-256 del Excel no coincide: "
            f"esperado={EXPECTED_EXCEL_SHA256}, actual={excel_sha}."
        )

    resolution_sha = sha256_file(args.resolution_csv)

    with args.resolution_csv.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as stream:
        rows = list(csv.DictReader(stream))

    if len(rows) != EXPECTED_RESOLUTION_ROWS:
        raise PreflightAbort(
            "Cambió cardinalidad del CSV de resolución: "
            f"esperado={EXPECTED_RESOLUTION_ROWS}, actual={len(rows)}."
        )

    origin_counts = Counter(row["origin"].strip() for row in rows)
    for origin, expected in EXPECTED_ORIGINS.items():
        if origin_counts[origin] != expected:
            raise PreflightAbort(
                f"Cambió origin/{origin}: "
                f"esperado={expected}, actual={origin_counts[origin]}."
            )
    if set(origin_counts) != set(EXPECTED_ORIGINS):
        raise PreflightAbort(
            "Aparecieron orígenes fuera del plan 2J: "
            + ", ".join(sorted(set(origin_counts) - set(EXPECTED_ORIGINS)))
        )

    deterministic = [
        row
        for row in rows
        if row["resolution"].strip()
        in {"CREATE_CANDIDATE", "REUSE_CANDIDATE"}
    ]
    review_date = [
        row for row in rows if row["resolution"].strip() == "REVIEW_DATE"
    ]

    other_resolution_counts = Counter(row["resolution"].strip() for row in rows)

    if len(deterministic) != EXPECTED_DETERMINISTIC:
        raise PreflightAbort(
            f"Deterministas != {EXPECTED_DETERMINISTIC}: {len(deterministic)}."
        )
    if len(review_date) != EXPECTED_REVIEW_DATE:
        raise PreflightAbort(
            f"REVIEW_DATE != {EXPECTED_REVIEW_DATE}: {len(review_date)}."
        )

    for code in (
        "BLOCKED_TARGET",
        "REVIEW_TARGET",
        "REVIEW_EXISTING",
        "SKIP_SOURCE",
    ):
        if other_resolution_counts[code] != 0:
            raise PreflightAbort(
                f"Resolución inesperada {code}={other_resolution_counts[code]}."
            )

    event_counts = Counter(
        (row["event_type"].strip(), row["motive"].strip())
        for row in deterministic
    )
    if event_counts != Counter(EXPECTED_BY_EVENT):
        raise PreflightAbort(
            f"Cambió desglose determinista: {dict(event_counts)!r}."
        )

    continuation_source = {
        (
            row["source_key"].strip(),
            row["column"].strip(),
            parse_int(row["row"], "row"),
            row["fecha_evento"].strip(),
        )
        for row in deterministic
        if row["event_type"].strip() == "continuacion_asamblea"
    }
    if continuation_source != EXPECTED_CONTINUATION_SOURCE:
        raise PreflightAbort(
            "Cambió conjunto fuente de las seis continuaciones."
        )

    # REVIEW_DATE debe seguir siendo sólo material CG/CJ no determinista.
    if any(row["origin"].strip() != "CG_CJ" for row in review_date):
        raise PreflightAbort(
            "Apareció REVIEW_DATE fuera del análisis CG/CJ original."
        )

    validate_model_shape()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "preflight_seguimiento_2j.json"
    csv_path = args.output_dir / "preflight_seguimiento_2j.csv"

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

        event_catalog = resolver.catalog_by_code(
            db, "tipo_evento_seguimiento"
        )
        motive_catalog = resolver.catalog_by_code(
            db, "motivo_seguimiento"
        )

        required_event_codes = {
            event_type for event_type, _motive in EXPECTED_BY_EVENT
        }
        missing_events = required_event_codes - set(event_catalog)
        if missing_events:
            raise PreflightAbort(
                "Faltan tipo_evento_seguimiento: "
                + ", ".join(sorted(missing_events))
            )

        if "nueva_informacion" not in motive_catalog:
            raise PreflightAbort(
                "Falta motivo_seguimiento/nueva_informacion."
            )

        actions = Counter()
        verified = []
        exact_signatures = set()

        for row in deterministic:
            pn_id = parse_int(
                row["id_proyecto_nucleo"], "id_proyecto_nucleo"
            )
            target_type = row["target_type"].strip()
            target_id = parse_int(row["target_id"], "target_id")
            event_type = row["event_type"].strip()
            motive = row["motive"].strip()
            event_date = parse_date(row["fecha_evento"], "fecha_evento")
            detail = row["clause"]
            source = row["fuente"]

            if target_type not in ALLOWED_TARGET_TYPES:
                raise PreflightAbort(
                    f"target_type fuera del plan: {target_type!r}."
                )
            if not detail.strip():
                raise PreflightAbort("Evento determinista con detalle vacío.")
            if not source.strip():
                raise PreflightAbort("Evento determinista con fuente vacía.")

            if event_type == "continuacion_asamblea":
                if target_type != "asamblea":
                    raise PreflightAbort(
                        "continuacion_asamblea debe apuntar a Asamblea."
                    )
                if motive:
                    raise PreflightAbort(
                        "continuacion_asamblea no debe tener motivo."
                    )
            else:
                if target_type != "proyecto_nucleo":
                    raise PreflightAbort(
                        f"{event_type} debe apuntar a ProyectoNucleo."
                    )

            if event_type == "cambio_alcance":
                if motive != "nueva_informacion":
                    raise PreflightAbort(
                        "cambio_alcance determinista debe usar "
                        "motivo nueva_informacion."
                    )
            elif motive:
                raise PreflightAbort(
                    f"{event_type} no debe llevar motivo {motive!r}."
                )

            validate_target(
                db,
                pn_id=pn_id,
                target_type=target_type,
                target_id=target_id,
            )

            event_type_id = event_catalog[event_type].id_catalogo_opcion
            motive_id = (
                motive_catalog[motive].id_catalogo_opcion
                if motive
                else None
            )

            signature = (
                pn_id,
                target_type,
                target_id,
                event_type_id,
                motive_id,
                event_date,
                detail,
                source,
            )
            if signature in exact_signatures:
                raise PreflightAbort(
                    "Dos filas deterministas producen la misma firma exacta."
                )
            exact_signatures.add(signature)

            existing = exact_existing(
                db,
                pn_id=pn_id,
                target_type=target_type,
                target_id=target_id,
                event_type_id=event_type_id,
                motive_id=motive_id,
                event_date=event_date,
                detail=detail,
                source=source,
            )

            if len(existing) == 0:
                action = "CREATE"
                existing_id = None
            elif len(existing) == 1:
                action = "REUSE"
                existing_id = existing[0].id_seguimiento_evento
            else:
                raise PreflightAbort(
                    "Hay múltiples SeguimientoEvento con firma exacta: "
                    f"fila={row['row']} columna={row['column']}."
                )

            actions[action] += 1
            verified.append({
                "action": action,
                "existing_id": existing_id,
                "row": parse_int(row["row"], "row"),
                "column": row["column"].strip(),
                "origin": row["origin"].strip(),
                "source_key": row["source_key"].strip(),
                "event_type": event_type,
                "motive": motive,
                "fecha_evento": event_date.isoformat(),
                "id_proyecto_nucleo": pn_id,
                "target_type": target_type,
                "target_id": target_id,
                "fuente": source,
                "clause": detail,
            })

        # Preflight previo a importación: los 17 deben ser nuevos.
        if actions["CREATE"] != EXPECTED_DETERMINISTIC or actions["REUSE"] != 0:
            raise PreflightAbort(
                "Estado previo 2J inesperado: "
                f"CREATE={actions['CREATE']} REUSE={actions['REUSE']}; "
                "se esperaba 17/0."
            )

        verified.sort(
            key=lambda item: (
                item["row"],
                item["column"],
                item["event_type"],
                item["source_key"],
            )
        )

        with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "action",
                    "existing_id",
                    "row",
                    "column",
                    "origin",
                    "source_key",
                    "event_type",
                    "motive",
                    "fecha_evento",
                    "id_proyecto_nucleo",
                    "target_type",
                    "target_id",
                    "fuente",
                    "clause",
                ],
            )
            writer.writeheader()
            writer.writerows(verified)

        report = {
            "database": current_db,
            "schema": current_schema,
            "project": PROJECT_KEY,
            "excel": args.excel.name,
            "excel_sha256": excel_sha,
            "resolution_csv": str(args.resolution_csv),
            "resolution_csv_sha256": resolution_sha,
            "resolution_rows": len(rows),
            "origins": dict(origin_counts),
            "deterministic": len(deterministic),
            "review_date": len(review_date),
            "actions": {
                "CREATE": actions["CREATE"],
                "REUSE": actions["REUSE"],
            },
            "by_event": [
                {
                    "event_type": event_type,
                    "motive": motive,
                    "count": count,
                }
                for (event_type, motive), count
                in sorted(event_counts.items())
            ],
            "verified": verified,
        }
        json_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print("=== PREFLIGHT 2J — SEGUIMIENTO ===")
        print(f"BD: {current_db} / schema {current_schema}")
        print(f"Proyecto: {PROJECT_KEY}")
        print(f"SHA-256 Excel:      {excel_sha}")
        print(f"SHA-256 resolución: {resolution_sha}")
        print("Resolución preservada:")
        print(f"  filas totales:       {len(rows)}")
        print(f"  CG_CJ:               {origin_counts['CG_CJ']}")
        print(f"  2B_R_AI_AJ:          {origin_counts['2B_R_AI_AJ']}")
        print(f"  deterministas:       {len(deterministic)}")
        print(f"  REVIEW_DATE:         {len(review_date)}")
        print("Estado PostgreSQL:")
        print(f"  CREATE:              {actions['CREATE']}")
        print(f"  REUSE:               {actions['REUSE']}")
        print("Deterministas por tipo:")
        for (event_type, motive), count in sorted(event_counts.items()):
            label = event_type + (f"/{motive}" if motive else "")
            print(f"  {label:<42} {count}")
        print("Plan exacto 2J:")
        for item in verified:
            motive_label = f"/{item['motive']}" if item["motive"] else ""
            print(
                f"  fila={item['row']} col={item['column']} | "
                f"{item['source_key']} | "
                f"{item['event_type']}{motive_label} | "
                f"{item['fecha_evento']} | "
                f"{item['target_type']}/{item['target_id']} | "
                f"{item['action']}"
            )
        print("Documento: 0 (id_documento=NULL en todos los eventos).")
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
    except (
        PreflightAbort,
        resolver.ResolveAbort,
    ) as exc:
        print("=== PREFLIGHT 2J ABORTADO ===", file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
