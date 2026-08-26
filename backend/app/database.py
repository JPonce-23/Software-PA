import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DB_RUNTIME_USER = os.getenv("DB_RUNTIME_USER")
DB_RUNTIME_PASSWORD = os.getenv("DB_RUNTIME_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

missing_database_vars = [
    name
    for name, value in (
        ("DB_RUNTIME_USER", DB_RUNTIME_USER),
        ("DB_RUNTIME_PASSWORD", DB_RUNTIME_PASSWORD),
        ("DB_HOST", DB_HOST),
        ("DB_PORT", DB_PORT),
        ("DB_NAME", DB_NAME),
    )
    if not value
]
if missing_database_vars:
    raise RuntimeError(
        "Configuración PostgreSQL runtime incompleta. Variables obligatorias faltantes: "
        + ", ".join(missing_database_vars)
    )

SQLALCHEMY_DATABASE_URL = URL.create(
    drivername="postgresql",
    username=DB_RUNTIME_USER,
    password=DB_RUNTIME_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
