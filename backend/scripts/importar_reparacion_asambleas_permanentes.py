#!/usr/bin/env python3
"""Importación transaccional de reparación 2B-R: asambleas permanentes.

Repara exclusivamente los 6 grupos auditados que la capa 2B original dejó en
REVIEW por mezclar la asamblea base con texto de "ASAMBLEA PERMANENTE" /
"CONTINUACIÓN".

Plan congelado:
- 6 grupos fuente
- 8 Asambleas
- 13 AsambleaConvocatoria
- 7 Asambleas celebradas
- 1 Asamblea sólo programada
- 6 continuaciones separadas, que NO se escriben aquí

La continuación no se modela como otra Asamblea. El reporte conserva el
id_asamblea base resultante para que la capa 2J pueda crear después
SeguimientoEvento.continuacion_asamblea.

Seguridad:
- sólo DB_NAME=db_carga_excel
- schema 018
- SHA-256 exacto del Excel aprobado
- actor activo
- plan de firmas congelado
- no pisa Asambleas no reconocidas del mismo ProyectoNucleo+COP
- idempotencia por firma exacta de convocatorias
- una sola transacción
- SET CONSTRAINTS ALL IMMEDIATE
- --dry-run => ROLLBACK
- --confirmar => COMMIT
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402
from app.database import DB_NAME, SessionLocal  # noqa: E402


EXPECTED_DB = "db_carga_excel"
EXPECTED_SCHEMA = "018"
EXPECTED_SHA256 = "bac01c25e9ff963f524fa8a48d69e74d92a0d36578731b1eca91f0e5a3573c3f"

PROJECT_KEY = "MEX-QRO"

COP_CONTEXT = {
    "ORIGEN": "cop_original",
    "ADICIONAL": "modificatorio",
    "2A_ADICIONAL": "modificatorio",
    "COMPLEMENTARIAS": "obras_complementarias",
}

EXPECTED_GROUPS = 6
EXPECTED_ASSEMBLIES = 8
EXPECTED_CONVOCATIONS = 13
EXPECTED_CELEBRATED = 7
EXPECTED_PROGRAMMED_ONLY = 1
EXPECTED_CONTINUATIONS = 6


class ImportAbort(RuntimeError):
    pass


def d(value: str) -> date:
    return date.fromisoformat(value)


# ordinal, fecha_programada, fecha_realizacion, resultado
PLAN = [
    {
        "source_key": "MEXICO|COYOTEPEC|COYOTEPEC",
        "cop": "ORIGEN",
        "source_rows": [45, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59],
        "assemblies": [
            {
                "label": "COYOTEPEC_A",
                "rule": "ciclo_previo_programado",
                "convocations": [
                    (1, d("2025-06-25"), None, None),
                    (2, d("2025-07-05"), None, None),
                ],
            },
            {
                "label": "COYOTEPEC_B",
                "rule": "base_permanente_segunda_convocatoria",
                "convocations": [
                    (1, d("2025-09-30"), None, None),
                    (2, d("2025-10-11"), d("2025-10-11"), "celebrada"),
                ],
            },
        ],
        "continuation": {
            "assembly_label": "COYOTEPEC_B",
            "date": d("2025-10-18"),
            "source_column": "CJ",
            "source_row": 45,
        },
    },
    {
        "source_key": "HIDALGO|TULA DE ALLENDE|TULA DE ALLENDE",
        "cop": "ORIGEN",
        "source_rows": [92, 93],
        "assemblies": [
            {
                "label": "TULA_A",
                "rule": "base_permanente_primera_convocatoria",
                "convocations": [
                    (1, d("2025-08-03"), d("2025-08-03"), "celebrada"),
                ],
            },
        ],
        "continuation": {
            "assembly_label": "TULA_A",
            "date": d("2025-08-17"),
            "source_column": "CJ",
            "source_row": 92,
        },
    },
    {
        "source_key": "HIDALGO|CHAPANTONGO|JUCHITLAN",
        "cop": "ORIGEN",
        "source_rows": [103],
        "assemblies": [
            {
                "label": "JUCHITLAN_A",
                "rule": "base_permanente_segunda_convocatoria",
                "convocations": [
                    (1, d("2025-07-08"), None, None),
                    (2, d("2025-07-20"), d("2025-07-20"), "celebrada"),
                ],
            },
        ],
        "continuation": {
            "assembly_label": "JUCHITLAN_A",
            "date": d("2025-09-09"),
            "source_column": "AJ",
            "source_row": 103,
        },
    },
    {
        "source_key": "HIDALGO|CHAPANTONGO|SAN JOSE EL MARQUEZ",
        "cop": "ORIGEN",
        "source_rows": [105, 106],
        "assemblies": [
            {
                "label": "SAN_JOSE_A",
                "rule": "base_permanente_segunda_convocatoria",
                "convocations": [
                    (1, d("2025-07-11"), None, None),
                    (2, d("2025-07-20"), d("2025-07-20"), "celebrada"),
                ],
            },
        ],
        "continuation": {
            "assembly_label": "SAN_JOSE_A",
            "date": d("2025-09-09"),
            "source_column": "AJ",
            "source_row": 105,
        },
    },
    {
        "source_key": "MEXICO|JILOTEPEC|SANTIAGO OXTHOC",
        "cop": "ORIGEN",
        "source_rows": [117],
        "assemblies": [
            {
                "label": "SANTIAGO_A",
                "rule": "base_permanente_segunda_convocatoria_textual",
                "convocations": [
                    (1, d("2025-06-29"), None, None),
                    (2, d("2025-07-08"), d("2025-07-08"), "celebrada"),
                ],
            },
            {
                "label": "SANTIAGO_B",
                "rule": "asamblea_posterior_primera_convocatoria",
                "convocations": [
                    (1, d("2025-11-18"), d("2025-11-18"), "celebrada"),
                ],
            },
        ],
        "continuation": {
            "assembly_label": "SANTIAGO_A",
            "date": d("2025-09-07"),
            "source_column": "AJ",
            "source_row": 117,
        },
    },
    {
        "source_key": "QUERETARO|SAN JUAN DEL RIO|PASO DE MATA",
        "cop": "ORIGEN",
        "source_rows": [136, 138, 139],
        "assemblies": [
            {
                "label": "PASO_MATA_A",
                "rule": "base_permanente_primera_convocatoria_textual",
                "convocations": [
                    (1, d("2025-08-24"), d("2025-08-24"), "celebrada"),
                ],
            },
        ],
        "continuation": {
            "assembly_label": "PASO_MATA_A",
            "date": d("2025-08-31"),
            "source_column": "AI",
            "source_row": 136,
        },
    },
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\u00a0", " ")).strip()


def norm(value: Any) -> str:
    raw = clean_text(value).upper()
    normalized = unicodedata.normalize("NFKD", raw)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", " ", ascii_text).strip()


def make_nucleus_key(entity: Any, municipality: Any, nucleus: Any) -> str | None:
    parts = (norm(entity), norm(municipality), norm(nucleus))
    return "|".join(parts) if all(parts) else None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def schema_version(db) -> str | None:
    return db.execute(text("SELECT max(version) FROM schema_migrations")).scalar()


def catalog_by_code(db, catalog_type: str) -> dict[str, Any]:
    rows = (
        db.query(models.CatalogoOperativo)
        .filter(
            models.CatalogoOperativo.tipo_catalogo == catalog_type,
            models.CatalogoOperativo.activo.is_(True),
        )
        .all()
    )
    return {row.codigo: row for row in rows}


def build_project_nucleus_index(db, project):
    rows = (
        db.query(
            models.ProyectoNucleo,
            models.NucleoAgrario,
            models.Municipio,
            models.EntidadFederativa,
        )
        .join(
            models.NucleoAgrario,
            models.NucleoAgrario.id_nucleo == models.ProyectoNucleo.id_nucleo,
        )
        .join(
            models.Municipio,
            models.Municipio.id_municipio == models.NucleoAgrario.id_municipio,
        )
        .join(
            models.EntidadFederativa,
            models.EntidadFederativa.id_entidad == models.Municipio.id_entidad,
        )
        .filter(
            models.ProyectoNucleo.id_proyecto == project.id_proyecto,
            models.ProyectoNucleo.activo.is_(True),
            models.NucleoAgrario.activo.is_(True),
        )
        .all()
    )

    index = {}
    for pn, nucleus, municipality, entity in rows:
        key = make_nucleus_key(
            entity.nombre,
            municipality.nombre,
            nucleus.nombre_nucleo,
        )
        if key in index:
            raise ImportAbort(f"ProyectoNucleo duplicado para clave {key}")
        index[key] = pn

    return index


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
        # Columnas de auditoría pueden poblarse por trigger del esquema.
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


def filtered_kwargs(model, data: dict[str, Any]) -> dict[str, Any]:
    columns = model_column_names(model)
    return {key: value for key, value in data.items() if key in columns}


def validate_model_shape() -> None:
    assembly_supplied = {
        "id_proyecto_nucleo",
        "id_tipo_asamblea",
        "id_contexto_asamblea",
        "id_tipo_cop_operativo",
        "id_padron",
        "proposito",
        "activo",
        "creado_por",
        "observaciones",
    }
    conv_supplied = {
        "id_asamblea",
        "ordinal",
        "fecha_expedicion",
        "fecha_programada",
        "fecha_realizacion",
        "id_resultado",
        "activo",
        "creado_por",
        "observaciones",
    }

    missing_a = required_unhandled_columns(models.Asamblea, assembly_supplied)
    missing_c = required_unhandled_columns(
        models.AsambleaConvocatoria,
        conv_supplied,
    )

    if missing_a:
        raise ImportAbort(
            "El modelo Asamblea tiene columnas NOT NULL sin regla de 2B-R: "
            + ", ".join(missing_a)
        )

    if missing_c:
        raise ImportAbort(
            "El modelo AsambleaConvocatoria tiene columnas NOT NULL "
            "sin regla de 2B-R: "
            + ", ".join(missing_c)
        )


def candidate_signature(candidate: dict[str, Any]) -> tuple:
    return tuple(candidate["convocations"])


def active_group_assemblies(
    db,
    pn_id: int,
    type_id: int,
    context_id: int,
    cop_id: int,
    result_by_id: dict[int, str],
):
    assemblies = (
        db.query(models.Asamblea)
        .filter(
            models.Asamblea.id_proyecto_nucleo == pn_id,
            models.Asamblea.id_tipo_asamblea == type_id,
            models.Asamblea.id_contexto_asamblea == context_id,
            models.Asamblea.id_tipo_cop_operativo == cop_id,
            models.Asamblea.activo.is_(True),
        )
        .order_by(models.Asamblea.id_asamblea)
        .all()
    )

    output = []

    for assembly in assemblies:
        convs = (
            db.query(models.AsambleaConvocatoria)
            .filter(
                models.AsambleaConvocatoria.id_asamblea
                == assembly.id_asamblea,
                models.AsambleaConvocatoria.activo.is_(True),
            )
            .order_by(models.AsambleaConvocatoria.ordinal)
            .all()
        )

        signature = tuple(
            (
                conv.ordinal,
                conv.fecha_programada,
                conv.fecha_realizacion,
                (
                    result_by_id.get(conv.id_resultado)
                    if conv.id_resultado is not None
                    else None
                ),
            )
            for conv in convs
        )

        output.append((assembly, signature))

    return output


def validate_plan_shape() -> None:
    if len(PLAN) != EXPECTED_GROUPS:
        raise ImportAbort("Cambió número de grupos del plan 2B-R.")

    assembly_count = sum(len(group["assemblies"]) for group in PLAN)
    conv_count = sum(
        len(candidate["convocations"])
        for group in PLAN
        for candidate in group["assemblies"]
    )
    celebrated_count = sum(
        1
        for group in PLAN
        for candidate in group["assemblies"]
        if any(
            result == "celebrada"
            for _, _, _, result in candidate["convocations"]
        )
    )
    programmed_only = assembly_count - celebrated_count

    if assembly_count != EXPECTED_ASSEMBLIES:
        raise ImportAbort("Cambió número de Asambleas del plan 2B-R.")
    if conv_count != EXPECTED_CONVOCATIONS:
        raise ImportAbort("Cambió número de convocatorias del plan 2B-R.")
    if celebrated_count != EXPECTED_CELEBRATED:
        raise ImportAbort("Cambió número de Asambleas celebradas 2B-R.")
    if programmed_only != EXPECTED_PROGRAMMED_ONLY:
        raise ImportAbort("Cambió número de Asambleas programadas 2B-R.")


def create_assembly(
    db,
    *,
    pn_id: int,
    type_id: int,
    context_id: int,
    cop_id: int,
    actor_id: int,
    group: dict[str, Any],
    candidate: dict[str, Any],
):
    assembly_data = {
        "id_proyecto_nucleo": pn_id,
        "id_tipo_asamblea": type_id,
        "id_contexto_asamblea": context_id,
        "id_tipo_cop_operativo": cop_id,
        "id_padron": None,
        "proposito": None,
        "activo": True,
        "creado_por": actor_id,
        "observaciones": (
            "Reparación migratoria 2B-R desde Excel INFORME M-Q; "
            f"grupo={group['source_key']}; COP={group['cop']}; "
            f"etiqueta={candidate['label']}; regla={candidate['rule']}; "
            f"filas={','.join(map(str, group['source_rows']))}."
        ),
    }

    assembly = models.Asamblea(
        **filtered_kwargs(models.Asamblea, assembly_data)
    )
    db.add(assembly)
    db.flush()

    return assembly


def create_convocation(
    db,
    *,
    assembly_id: int,
    ordinal: int,
    programmed: date,
    realized: date | None,
    result_code: str | None,
    result_catalog: dict[str, Any],
    actor_id: int,
    group: dict[str, Any],
    candidate: dict[str, Any],
):
    result_id = (
        result_catalog[result_code].id_catalogo_opcion
        if result_code
        else None
    )

    conv_data = {
        "id_asamblea": assembly_id,
        "ordinal": ordinal,
        "fecha_expedicion": None,
        "fecha_programada": programmed,
        "fecha_realizacion": realized,
        "id_resultado": result_id,
        "activo": True,
        "creado_por": actor_id,
        "observaciones": (
            "Reparación migratoria 2B-R; "
            f"grupo={group['source_key']}; "
            f"etiqueta={candidate['label']}; ordinal={ordinal}."
        ),
    }

    conv = models.AsambleaConvocatoria(
        **filtered_kwargs(models.AsambleaConvocatoria, conv_data)
    )
    db.add(conv)
    db.flush()

    return conv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("excel", type=Path)

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--confirmar", action="store_true")

    parser.add_argument("--actor-id", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("."))

    args = parser.parse_args()

    validate_plan_shape()
    validate_model_shape()

    if DB_NAME != EXPECTED_DB:
        raise ImportAbort(
            f"Protección: DB_NAME debe ser {EXPECTED_DB!r}; recibido {DB_NAME!r}."
        )

    if not args.excel.exists():
        raise ImportAbort(f"No existe el Excel: {args.excel}")

    digest = sha256_file(args.excel)
    if digest != EXPECTED_SHA256:
        raise ImportAbort(
            "El SHA-256 no coincide con el Excel aprobado. "
            f"Esperado {EXPECTED_SHA256}; recibido {digest}."
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    mode_name = "confirmar" if args.confirmar else "dry-run"
    report_path = (
        args.output_dir
        / f"importacion_reparacion_asambleas_permanentes_{mode_name}.json"
    )

    db = SessionLocal()

    try:
        current_db = db.execute(text("SELECT current_database()")).scalar()
        current_schema = schema_version(db)

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

        pn_index = build_project_nucleus_index(db, project)
        cop_catalog = catalog_by_code(db, "tipo_cop_operativo")
        type_catalog = catalog_by_code(db, "tipo_asamblea")
        context_catalog = catalog_by_code(db, "contexto_asamblea")
        result_catalog = catalog_by_code(db, "resultado_convocatoria")

        if "anuencia" not in type_catalog:
            raise ImportAbort("Falta tipo_asamblea/anuencia.")
        if "celebrada" not in result_catalog:
            raise ImportAbort("Falta resultado_convocatoria/celebrada.")

        db.execute(
            text("SELECT set_config('app.current_user_id', :id, true)"),
            {"id": str(args.actor_id)},
        )

        result_by_id = {
            item.id_catalogo_opcion: item.codigo
            for item in result_catalog.values()
        }

        assembly_actions = Counter()
        conv_actions = Counter()
        imported = []
        continuation_targets = []

        for group in PLAN:
            pn = pn_index.get(group["source_key"])
            if pn is None:
                raise ImportAbort(
                    "ProyectoNucleo faltante para grupo reparable: "
                    f"{group['source_key']}"
                )

            cop = cop_catalog.get(group["cop"])
            if cop is None:
                raise ImportAbort(
                    f"Falta tipo_cop_operativo/{group['cop']}."
                )

            context_code = COP_CONTEXT[group["cop"]]
            context = context_catalog.get(context_code)
            if context is None:
                raise ImportAbort(
                    f"Falta contexto_asamblea/{context_code}."
                )

            existing = active_group_assemblies(
                db,
                pn.id_proyecto_nucleo,
                type_catalog["anuencia"].id_catalogo_opcion,
                context.id_catalogo_opcion,
                cop.id_catalogo_opcion,
                result_by_id,
            )

            expected_signatures = {
                candidate_signature(candidate)
                for candidate in group["assemblies"]
            }

            extras = [
                (assembly, signature)
                for assembly, signature in existing
                if signature not in expected_signatures
            ]

            if extras:
                raise ImportAbort(
                    "Hay Asambleas activas no reconocidas por 2B-R para "
                    f"{group['source_key']} / {group['cop']}: "
                    + ", ".join(
                        f"id={assembly.id_asamblea}"
                        for assembly, _ in extras
                    )
                )

            label_to_assembly = {}
            used_existing_ids = set()

            for candidate in group["assemblies"]:
                signature = candidate_signature(candidate)

                exact = [
                    assembly
                    for assembly, actual_signature in existing
                    if actual_signature == signature
                    and assembly.id_asamblea not in used_existing_ids
                ]

                if len(exact) > 1:
                    raise ImportAbort(
                        "Hay múltiples Asambleas exactas para "
                        f"{group['source_key']} / {candidate['label']}."
                    )

                if len(exact) == 1:
                    assembly = exact[0]
                    used_existing_ids.add(assembly.id_asamblea)
                    assembly_actions["REUSE"] += 1
                    conv_actions["REUSE"] += len(
                        candidate["convocations"]
                    )
                    action = "REUSE"

                else:
                    assembly = create_assembly(
                        db,
                        pn_id=pn.id_proyecto_nucleo,
                        type_id=type_catalog["anuencia"].id_catalogo_opcion,
                        context_id=context.id_catalogo_opcion,
                        cop_id=cop.id_catalogo_opcion,
                        actor_id=args.actor_id,
                        group=group,
                        candidate=candidate,
                    )

                    for ordinal, programmed, realized, result_code in (
                        candidate["convocations"]
                    ):
                        create_convocation(
                            db,
                            assembly_id=assembly.id_asamblea,
                            ordinal=ordinal,
                            programmed=programmed,
                            realized=realized,
                            result_code=result_code,
                            result_catalog=result_catalog,
                            actor_id=args.actor_id,
                            group=group,
                            candidate=candidate,
                        )

                    assembly_actions["CREATE"] += 1
                    conv_actions["CREATE"] += len(
                        candidate["convocations"]
                    )
                    action = "CREATE"

                label_to_assembly[candidate["label"]] = assembly

                imported.append({
                    "action": action,
                    "source_key": group["source_key"],
                    "cop": group["cop"],
                    "label": candidate["label"],
                    "rule": candidate["rule"],
                    "id_proyecto_nucleo": pn.id_proyecto_nucleo,
                    "id_asamblea": assembly.id_asamblea,
                    "convocations": [
                        {
                            "ordinal": ordinal,
                            "fecha_programada": programmed.isoformat(),
                            "fecha_realizacion": (
                                realized.isoformat()
                                if realized
                                else None
                            ),
                            "resultado": result_code,
                        }
                        for (
                            ordinal,
                            programmed,
                            realized,
                            result_code,
                        ) in candidate["convocations"]
                    ],
                })

            continuation = group["continuation"]
            base = label_to_assembly.get(
                continuation["assembly_label"]
            )
            if base is None:
                raise ImportAbort(
                    "No se resolvió la Asamblea base para continuación "
                    f"{group['source_key']} / "
                    f"{continuation['assembly_label']}."
                )

            continuation_targets.append({
                "source_key": group["source_key"],
                "id_proyecto_nucleo": pn.id_proyecto_nucleo,
                "cop": group["cop"],
                "id_asamblea": base.id_asamblea,
                "assembly_label": continuation["assembly_label"],
                "continuation_date": continuation["date"].isoformat(),
                "source_column": continuation["source_column"],
                "source_row": continuation["source_row"],
            })

        if (
            assembly_actions["CREATE"]
            + assembly_actions["REUSE"]
            != EXPECTED_ASSEMBLIES
        ):
            raise ImportAbort(
                "CREATE+REUSE de Asambleas no coincide con 8."
            )

        if (
            conv_actions["CREATE"]
            + conv_actions["REUSE"]
            != EXPECTED_CONVOCATIONS
        ):
            raise ImportAbort(
                "CREATE+REUSE de convocatorias no coincide con 13."
            )

        if len(continuation_targets) != EXPECTED_CONTINUATIONS:
            raise ImportAbort(
                "No se resolvieron las 6 continuaciones esperadas."
            )

        # Validación final por firma exacta después de CREATE/REUSE.
        verified_assemblies = 0
        verified_convs = 0
        verified_celebrated = 0
        verified_programmed_only = 0

        for group in PLAN:
            pn = pn_index[group["source_key"]]
            cop = cop_catalog[group["cop"]]
            context = context_catalog[COP_CONTEXT[group["cop"]]]

            actual = active_group_assemblies(
                db,
                pn.id_proyecto_nucleo,
                type_catalog["anuencia"].id_catalogo_opcion,
                context.id_catalogo_opcion,
                cop.id_catalogo_opcion,
                result_by_id,
            )

            actual_signatures = [signature for _, signature in actual]

            for candidate in group["assemblies"]:
                signature = candidate_signature(candidate)
                if actual_signatures.count(signature) != 1:
                    raise ImportAbort(
                        "Validación post-import falló para "
                        f"{group['source_key']} / {candidate['label']}."
                    )

                verified_assemblies += 1
                verified_convs += len(candidate["convocations"])

                if any(
                    result == "celebrada"
                    for _, _, _, result in candidate["convocations"]
                ):
                    verified_celebrated += 1
                else:
                    verified_programmed_only += 1

        if verified_assemblies != EXPECTED_ASSEMBLIES:
            raise ImportAbort("Postcheck: Asambleas != 8.")
        if verified_convs != EXPECTED_CONVOCATIONS:
            raise ImportAbort("Postcheck: convocatorias != 13.")
        if verified_celebrated != EXPECTED_CELEBRATED:
            raise ImportAbort("Postcheck: celebradas != 7.")
        if verified_programmed_only != EXPECTED_PROGRAMMED_ONLY:
            raise ImportAbort("Postcheck: programadas-only != 1.")

        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

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
            "actions": {
                "assemblies": {
                    "CREATE": assembly_actions["CREATE"],
                    "REUSE": assembly_actions["REUSE"],
                },
                "convocations": {
                    "CREATE": conv_actions["CREATE"],
                    "REUSE": conv_actions["REUSE"],
                },
            },
            "verified": {
                "assemblies": verified_assemblies,
                "convocations": verified_convs,
                "celebrated": verified_celebrated,
                "programmed_only": verified_programmed_only,
                "continuations_ready": len(continuation_targets),
            },
            "assemblies": imported,
            "continuation_targets": continuation_targets,
        }

        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(
            "=== IMPORTACIÓN REPARACIÓN 2B-R — "
            "ASAMBLEAS PERMANENTES ==="
        )
        print(f"Modo: {mode_name}")
        print(f"BD: {current_db} / schema {current_schema}")
        print(f"Actor: {actor.id_usuario} / {actor.correo}")
        print(f"Proyecto: {PROJECT_KEY}")
        print(f"SHA-256: {digest}")
        print("Asambleas:")
        print(f"  CREATE   {assembly_actions['CREATE']}")
        print(f"  REUSE    {assembly_actions['REUSE']}")
        print("Convocatorias:")
        print(f"  CREATE   {conv_actions['CREATE']}")
        print(f"  REUSE    {conv_actions['REUSE']}")
        print("Validación:")
        print(f"  Asambleas base:             {verified_assemblies}")
        print(f"  Convocatorias:              {verified_convs}")
        print(f"  Asambleas celebradas:       {verified_celebrated}")
        print(f"  Asambleas sólo programadas: {verified_programmed_only}")
        print(f"  Continuaciones listas 2J:   {len(continuation_targets)}")
        print("Continuaciones resueltas a Asamblea base:")
        for item in continuation_targets:
            print(
                f"  {item['source_key']} | "
                f"{item['continuation_date']} | "
                f"id_asamblea={item['id_asamblea']}"
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
        print("=== IMPORTACIÓN ABORTADA ===", file=sys.stderr)
        print(f"IntegrityError: {exc}", file=sys.stderr)
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
    try:
        raise SystemExit(main())
    except ImportAbort as exc:
        print("=== IMPORTACIÓN ABORTADA ===", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        print(
            "ROLLBACK realizado; no se confirmó ningún cambio.",
            file=sys.stderr,
        )
        raise SystemExit(2)
