#!/usr/bin/env python3
"""Wrapper read-only para ejecutar la auditoría global sobre una BD restaurada.

No cambia reglas ni conteos del auditor principal. Sólo permite que
auditoria_global_migracion_mq.py acepte el nombre efímero indicado en
RESTORECHECK_DB_NAME.

Protecciones:
- DB_NAME debe coincidir exactamente con RESTORECHECK_DB_NAME.
- Nunca acepta db_carga_excel ni db_pruebas_alfredo.
- El nombre debe iniciar con db_carga_excel_restorecheck_.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parent))

from app.database import DB_NAME  # noqa: E402
import auditoria_global_migracion_mq as audit  # noqa: E402


def main() -> int:
    expected = os.getenv("RESTORECHECK_DB_NAME", "").strip()

    if not expected:
        print(
            "ERROR: falta RESTORECHECK_DB_NAME.",
            file=sys.stderr,
        )
        return 2

    if expected in {"db_carga_excel", "db_pruebas_alfredo"}:
        print(
            f"ERROR: base protegida no permitida en restore-check: {expected}.",
            file=sys.stderr,
        )
        return 2

    if not re.fullmatch(
        r"db_carga_excel_restorecheck_[0-9]{8}_[0-9]{6}",
        expected,
    ):
        print(
            "ERROR: nombre de restore-check fuera del patrón permitido.",
            file=sys.stderr,
        )
        return 2

    if DB_NAME != expected:
        print(
            f"ERROR: DB_NAME={DB_NAME!r} no coincide con "
            f"RESTORECHECK_DB_NAME={expected!r}.",
            file=sys.stderr,
        )
        return 2

    # Única diferencia respecto al auditor principal:
    # aceptar el nombre efímero de la BD restaurada.
    audit.EXPECTED_DB = expected

    try:
        return audit.main()
    except audit.AuditAbort as exc:
        print("=== AUDITORÍA RESTORE-CHECK ABORTADA ===", file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
