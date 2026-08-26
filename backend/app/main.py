"""FastAPI application for the ProyectoNucleo target architecture."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, InternalError

from .config import AUTH_SETTINGS
from .database import SessionLocal
from .routers import (
    authentication,
    documents,
    domain,
    geospatial_imports,
    reporting,
    users,
)
from .services import authentication as authentication_service


logger = logging.getLogger(__name__)

app = FastAPI(
    title="SOFTWARE-PA",
    description="Seguimiento administrativo por ProyectoNucleo",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(AUTH_SETTINGS.allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)


@app.middleware("http")
async def csrf_cookie_guard(request, call_next):
    unsafe = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    if not unsafe or not request.url.path.startswith("/api/"):
        return await call_next(request)
    origin = request.headers.get("origin")
    if request.url.path == "/api/auth/sesiones":
        if origin not in AUTH_SETTINGS.allowed_origins:
            return JSONResponse(status_code=403, content={"detail": "Origen no permitido"})
        return await call_next(request)
    session_token = request.cookies.get(AUTH_SETTINGS.session_cookie_name)
    if not session_token:
        return await call_next(request)
    csrf_cookie = request.cookies.get(AUTH_SETTINGS.csrf_cookie_name)
    csrf_header = request.headers.get("x-csrf-token")
    if (
        origin not in AUTH_SETTINGS.allowed_origins
        or not csrf_cookie
        or not csrf_header
        or csrf_cookie != csrf_header
    ):
        return JSONResponse(
            status_code=403, content={"detail": "Protección CSRF inválida"}
        )
    db = SessionLocal()
    try:
        valid = authentication_service.validate_csrf(db, session_token, csrf_header)
    finally:
        db.close()
    if not valid:
        return JSONResponse(
            status_code=403, content={"detail": "Protección CSRF inválida"}
        )
    return await call_next(request)


@app.exception_handler(IntegrityError)
@app.exception_handler(InternalError)
@app.exception_handler(DBAPIError)
def database_error_handler(request, exc):
    logger.error(
        "Database error in %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=409,
        content={"detail": "La operación entra en conflicto con la integridad de los datos."},
    )


@app.exception_handler(Exception)
def global_exception_handler(request, exc):
    logger.error(
        "Unhandled error in %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


app.include_router(authentication.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(domain.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(geospatial_imports.router, prefix="/api")
app.include_router(reporting.router, prefix="/api")


@app.get("/", tags=["Sistema"])
def root():
    return {"service": "SOFTWARE-PA", "model": "ProyectoNucleo", "version": "2.0.0"}


@app.get("/health", tags=["Sistema"])
def health():
    db = SessionLocal()
    try:
        version = db.execute(
            text("SELECT max(version::integer) FROM schema_migrations")
        ).scalar_one()
    finally:
        db.close()
    return {"status": "ok", "schema": version}
