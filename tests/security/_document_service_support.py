"""Import the real document service without dotenv, an engine, or app startup.

Only the declarative Base is supplied here. Models, access checks, service,
validation and storage are the production modules. Tests provide their own bind.
"""
import importlib
import sys
import types

from sqlalchemy.orm import declarative_base


def document_service():
    if "app.database" in sys.modules:
        return importlib.import_module("app.services.documents")
    database = types.ModuleType("app.database")
    database.Base = declarative_base()
    sys.modules["app.database"] = database
    try:
        return importlib.import_module("app.services.documents")
    finally:
        # Restore only the supplied module. Removing other newly imported
        # modules would duplicate SQLAlchemy's class/function registrations.
        sys.modules.pop("app.database", None)
