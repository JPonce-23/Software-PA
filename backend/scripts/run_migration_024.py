import os
import sys
from dotenv import load_dotenv

load_dotenv()

import sqlalchemy

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME")

if not DB_USER or not DB_PASSWORD or not DB_NAME:
    print("DB_USER, DB_PASSWORD y DB_NAME son obligatorios.")
    sys.exit(1)

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = sqlalchemy.create_engine(SQLALCHEMY_DATABASE_URL)

try:
    with engine.connect() as conn:
        with open("backend/db/migrations/024_archivo_importacion_archivado.sql", "r") as f:
            sql = f.read()
        conn.execute(sqlalchemy.text(sql))
        conn.commit()
    print("Migration applied successfully.")
except Exception as e:
    print(f"Error applying migration: {e}")
    sys.exit(1)
