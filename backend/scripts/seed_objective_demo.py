"""Instala el seed mínimo canónico de baseline v1."""

import json
import os
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import DB_NAME, engine


SQL_PATH = Path(__file__).resolve().parents[1] / "db" / "seed.sql"


def assert_environment() -> None:
    environment = os.getenv("APP_ENV", "").strip().lower()
    database = DB_NAME.strip().lower()
    if environment not in {"development", "test"}:
        raise RuntimeError("El seed sólo admite APP_ENV=development/test")
    if not any(marker in database for marker in ("test", "prueba", "dev", "local")):
        raise RuntimeError("DB_NAME no identifica una base de desarrollo/prueba")
    if os.getenv("SEED_OBJECTIVE_CONFIRM") != "1":
        raise RuntimeError("Define SEED_OBJECTIVE_CONFIRM=1 para confirmar el seed")


def seed() -> None:
    assert_environment()
    connection = engine.raw_connection()
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(SQL_PATH.read_text(encoding="utf-8"))
    finally:
        connection.close()

    with engine.connect() as connection:
        counts = dict(connection.execute(text("""
            SELECT 'proyectos', COUNT(*) FROM proyecto
            UNION ALL SELECT 'proyecto_nucleo', COUNT(*) FROM proyecto_nucleo
            UNION ALL SELECT 'unidades_agrarias', COUNT(*) FROM unidad_agraria
            UNION ALL SELECT 'afectaciones', COUNT(*) FROM afectacion
            UNION ALL SELECT 'asambleas', COUNT(*) FROM asamblea
            UNION ALL SELECT 'tramites_ran', COUNT(*) FROM tramite_ran
            UNION ALL SELECT 'tramites_fifonafe', COUNT(*) FROM tramite_fifonafe
        """)).all())
    print(json.dumps({"seed": "baseline_v1", "database": DB_NAME, "counts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    seed()
