#!/usr/bin/env python3
"""Reconciliación read-only 2I-B-R posterior a 2B-R / 2F-R.

Este wrapper reutiliza exactamente la lógica de reconciliación ya cerrada en
reconciliar_soporte_documental_ck_cl.py, pero actualiza únicamente las guardas
de cardinalidad del resolvedor para el estado posterior a las reparaciones:

Histórico 2I-B:
- 436 cláusulas RESOLVED
- 442 instancias objetivo RESOLVED
- 376 claves documentales únicas
- 340 claves deterministas importadas
- 36 CONFLICT_REVIEW
- 240 pendiente_validacion
- 100 faltante

Estado actual del resolvedor después de 2B-R / 2F-R:
- 442 cláusulas RESOLVED
- 448 instancias objetivo RESOLVED

Antes de reconciliar se exige que la persistencia histórica CK/CL siga intacta:
- exactamente 340 ExpedienteRequisito activos para los 10 requisitos CK/CL;
- 240 en pendiente_validacion;
- 100 en faltante;
- 0 con Documento digital.

El script NO escribe en PostgreSQL. Su propósito es descubrir si las seis
instancias nuevas son:
- claves nuevas CREATE_CANDIDATE,
- evidencia adicional sobre claves existentes (EXISTING_REVIEW),
- nuevas contradicciones CONFLICT_REVIEW,
- o claves que siguen coincidiendo exactamente REUSE_CANDIDATE.

No se modifican las reglas semánticas del reconciliador original.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402
from app.database import DB_NAME, SessionLocal  # noqa: E402
import reconciliar_soporte_documental_ck_cl as base  # noqa: E402


EXPECTED_DB = "db_carga_excel"
EXPECTED_SCHEMA = "018"
PROJECT_KEY = "MEX-QRO"

EXPECTED_EXISTING_CKCL = 340
EXPECTED_EXISTING_STATES = {
    "pendiente_validacion": 240,
    "faltante": 100,
}
EXPECTED_EXISTING_WITH_DOCUMENT = 0

EXPECTED_RESOLVED_CLAUSES_POST_REPAIR = 442
EXPECTED_RESOLVED_TARGET_INSTANCES_POST_REPAIR = 448


class PreflightAbort(RuntimeError):
    pass


def validate_existing_ckcl() -> None:
    if DB_NAME != EXPECTED_DB:
        raise PreflightAbort(
            f"Protección: DB_NAME debe ser {EXPECTED_DB!r}; recibido {DB_NAME!r}."
        )

    db = SessionLocal()
    try:
        current_db = db.execute(text("SELECT current_database()")).scalar()
        current_schema = base.schema_version(db)

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

        rows = (
            db.query(
                models.ExpedienteRequisito,
                models.RequisitoDocumental,
                models.CatalogoOperativo,
            )
            .join(
                models.RequisitoDocumental,
                models.RequisitoDocumental.id_requisito
                == models.ExpedienteRequisito.id_requisito,
            )
            .join(
                models.CatalogoOperativo,
                models.CatalogoOperativo.id_catalogo_opcion
                == models.ExpedienteRequisito.id_estado,
            )
            .join(
                models.ProyectoNucleo,
                models.ProyectoNucleo.id_proyecto_nucleo
                == models.ExpedienteRequisito.id_proyecto_nucleo,
            )
            .filter(
                models.ProyectoNucleo.id_proyecto == project.id_proyecto,
                models.ProyectoNucleo.activo.is_(True),
                models.ExpedienteRequisito.activo.is_(True),
                models.RequisitoDocumental.activo.is_(True),
                models.RequisitoDocumental.codigo.in_(
                    sorted(base.TARGET_TYPE_BY_REQUIREMENT)
                ),
                models.CatalogoOperativo.tipo_catalogo
                == "estado_requisito_documental",
            )
            .order_by(models.ExpedienteRequisito.id_expediente_requisito)
            .all()
        )

        if len(rows) != EXPECTED_EXISTING_CKCL:
            raise PreflightAbort(
                "Cambió la persistencia histórica CK/CL: "
                f"esperado={EXPECTED_EXISTING_CKCL}, actual={len(rows)}."
            )

        states = Counter(
            state.codigo for _req, _requirement, state in rows
        )
        for code, expected in EXPECTED_EXISTING_STATES.items():
            actual = states[code]
            if actual != expected:
                raise PreflightAbort(
                    f"Cambió estado CK/CL/{code}: "
                    f"esperado={expected}, actual={actual}."
                )

        unexpected_states = (
            set(states) - set(EXPECTED_EXISTING_STATES)
        )
        if unexpected_states:
            raise PreflightAbort(
                "Aparecieron estados inesperados en requisitos CK/CL: "
                + ", ".join(sorted(unexpected_states))
            )

        with_document = sum(
            1
            for req, _requirement, _state in rows
            if req.id_documento is not None
        )
        if with_document != EXPECTED_EXISTING_WITH_DOCUMENT:
            raise PreflightAbort(
                "Cambió la regla documental CK/CL: "
                f"requisitos con id_documento esperado=0, actual={with_document}."
            )

        print("=== GUARDA PREVIA 2I-B-R — PERSISTENCIA CK/CL ===")
        print(f"BD: {current_db} / schema {current_schema}")
        print(f"Proyecto: {PROJECT_KEY}")
        print(f"ExpedienteRequisito CK/CL activos: {len(rows)}")
        print(
            "  pendiente_validacion: "
            f"{states['pendiente_validacion']}"
        )
        print(f"  faltante:             {states['faltante']}")
        print(f"  con Documento:        {with_document}")
        print("Persistencia histórica CK/CL intacta.")
        print()

    finally:
        db.rollback()
        db.close()


def main() -> int:
    # Parseamos sólo para validar que el usuario está pasando el CSV nuevo; el
    # reconciliador original volverá a parsear exactamente los mismos argumentos.
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("excel", type=Path)
    parser.add_argument(
        "--resolution-csv",
        type=Path,
        default=Path(
            "/data/reportes/2i_b_post_2f_r/"
            "resolucion_soporte_documental_ck_cl.csv"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/reportes/2i_b_post_2f_r"),
    )
    args, _unknown = parser.parse_known_args()

    if not args.resolution_csv.exists():
        raise PreflightAbort(
            "No existe el CSV post-2F-R: "
            f"{args.resolution_csv}."
        )

    validate_existing_ckcl()

    # Sólo se actualizan las guardas cardinales del resolvedor. Toda la lógica
    # de agrupación, conflicto, estado propuesto y comparación contra la BD es
    # exactamente la del reconciliador original.
    base.EXPECTED_RESOLVED_CLAUSES = (
        EXPECTED_RESOLVED_CLAUSES_POST_REPAIR
    )
    base.EXPECTED_RESOLVED_TARGET_INSTANCES = (
        EXPECTED_RESOLVED_TARGET_INSTANCES_POST_REPAIR
    )

    print(
        "Reconciliando estado post-2F-R con guardas "
        f"{base.EXPECTED_RESOLVED_CLAUSES} cláusulas / "
        f"{base.EXPECTED_RESOLVED_TARGET_INSTANCES} instancias..."
    )
    print()

    return base.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PreflightAbort, base.ReconcileAbort) as exc:
        print("=== RECONCILIACIÓN 2I-B-R ABORTADA ===", file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
