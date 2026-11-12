"""Real route body/decorator + ASGI, explicit caller-supplied DB/auth fixtures.

Never imports app.main/auth/database or dotenv. Full JWT/cookie integration is
separate QA; the injected authorization is identified by each test suite.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from app.services.document_download import DescriptorDownloadResponse

ROOT = Path(__file__).resolve().parents[2]


def download_app(models, database, actor, access):
    tree = ast.parse((ROOT/'backend/app/routers/documents.py').read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'download_version')
    namespace = dict(router=APIRouter(), Depends=Depends, HTTPException=HTTPException,
        Session=Session, models=models, get_db=database, READ_ROLES=['admin','operador','visualizador','geografo'],
        auth=SimpleNamespace(RoleChecker=lambda roles:actor), require_document_access=access,
        DescriptorDownloadResponse=DescriptorDownloadResponse)
    future = ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future,node],type_ignores=[])),
                 'actual_download_route','exec'),namespace)
    app=FastAPI();app.include_router(namespace['router'])
    return app
