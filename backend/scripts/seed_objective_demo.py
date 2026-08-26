"""Instala el dominio demo objetivo y su único archivo documental de QA."""

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import DB_NAME, engine
from app.services.documents import upload_root


ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "db" / "seed.sql"
ASSET_PATH = ROOT / "db" / "seeds" / "assets" / "qa_soporte_demo.txt"
EXPECTED_SHA256 = "dee42d98c899eb2dc8dba9f95326ded525de0b4ce752a82208880da79e679717"


def assert_environment() -> str:
    environment = os.getenv("APP_ENV", "").strip().lower()
    database = DB_NAME.strip().lower()
    if environment not in {"development", "test"}:
        raise RuntimeError("El seed objetivo sólo admite APP_ENV=development/test")
    if not any(marker in database for marker in ("test", "prueba", "dev", "local")):
        raise RuntimeError("DB_NAME no identifica una base local de desarrollo/prueba")
    if os.getenv("SEED_OBJECTIVE_CONFIRM") != "1":
        raise RuntimeError("Define SEED_OBJECTIVE_CONFIRM=1 para confirmar el dominio demo")
    return environment


def validate_asset() -> bytes:
    content = ASSET_PATH.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != EXPECTED_SHA256 or len(content) != 161:
        raise RuntimeError("El asset documental QA no coincide con checksum/tamaño esperados")
    return content


def seed() -> None:
    environment = assert_environment()
    validate_asset()
    destination = upload_root() / "seed" / ASSET_PATH.name
    existed = destination.exists()
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ASSET_PATH, destination)

    connection = engine.raw_connection()
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute("SET app.environment = %s", (environment,))
            cursor.execute(SQL_PATH.read_text(encoding="utf-8"))
    except Exception:
        if not existed:
            destination.unlink(missing_ok=True)
        raise
    finally:
        connection.close()

    with engine.connect() as connection:
        counts = dict(connection.execute(text("""
            SELECT 'proyectos', COUNT(*) FROM proyecto
            UNION ALL SELECT 'proyecto_nucleo', COUNT(*) FROM proyecto_nucleo
            UNION ALL SELECT 'parcelas', COUNT(*) FROM parcela
            UNION ALL SELECT 'afectaciones', COUNT(*) FROM afectacion
            UNION ALL SELECT 'convenios', COUNT(*) FROM convenio
            UNION ALL SELECT 'fifonafe', COUNT(*) FROM tramite_fifonafe
            UNION ALL SELECT 'pagos', COUNT(*) FROM pago
        """)).all())
    if hashlib.sha256(destination.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError("El archivo documental instalado no conserva su checksum")
    print(json.dumps({"seed": "dominio_objetivo", "database": DB_NAME, "counts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    seed()
