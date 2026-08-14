from fastapi import FastAPI, Depends, HTTPException, status, Query, UploadFile, File, Form
import os
import json
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import InternalError, IntegrityError, DatabaseError
from typing import List, Type, Any, Optional
from datetime import datetime, timezone, timedelta
import logging
import pandas as pd
import io

from .database import engine, Base, SessionLocal, get_db
from . import models, schemas
from . import auth
from .config import AUTH_SETTINGS
from .routers import administration, alertas, authentication, documentos, flujo, importaciones_geoespaciales, importaciones_territoriales, minutas, pagos, personas, franjas
from .services import administration as administration_service
from .services import afectaciones as afectaciones_service
from .services import authentication as authentication_service
from .services import flujo as flujo_service
from .services import nucleos as nucleos_service
from .services.access import (
    filter_by_user_tramos,
    filter_projects_by_user,
    require_afectacion_access,
    require_document_access,
    require_document_relation_access,
    require_nucleo_access,
    require_project_access,
    require_tramo_access,
    require_tramo_nucleo_access,
)


app = FastAPI(
    title="API - Sistema de Seguimiento de Liberación de Derechos",
    description="Backend con lógica de negocio geoespacial y administrativa",
    version="1.3.1"
)

logger = logging.getLogger(__name__)

import re

def sanitize_pg_error(msg: str) -> str:
    """
    Sanitiza mensajes crudos de PostgreSQL para evitar Information Disclosure (Fuga de Información).
    Elimina prefijos, rastros del stacktrace de BD (CONTEXT, HINT) y nombres internos.
    """
    clean_msg = re.sub(r"^(ERROR|FATAL|WARNING):\s+", "", msg, flags=re.IGNORECASE)
    delimitadores = r"\b(CONTEXT|HINT|DETAIL|STATEMENT|PL/pgSQL function):"
    clean_msg = re.split(delimitadores, clean_msg)[0]
    return clean_msg.replace('\n', ' ').strip()

@app.exception_handler(InternalError)
def sqlalchemy_internal_error_handler(request, exc: InternalError):
    logger.error(
        "Error interno de PostgreSQL en %s",
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=409,
        content={"detail": "La operación no cumple las reglas del proceso."},
    )

@app.exception_handler(IntegrityError)
def sqlalchemy_integrity_error_handler(request, exc: IntegrityError):
    logger.error(
        "Violación de integridad en %s",
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=409,
        content={"detail": "La operación entra en conflicto con la integridad de los datos."},
    )

@app.exception_handler(Exception)
def global_exception_handler(request, exc: Exception):
    logger.error(
        "Error no controlado en %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
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
    unsafe_method = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    if not unsafe_method or not request.url.path.startswith("/api/"):
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
        return JSONResponse(status_code=403, content={"detail": "Protección CSRF inválida"})

    db = SessionLocal()
    try:
        valid = authentication_service.validate_csrf(
            db, session_token, csrf_header
        )
    finally:
        db.close()
    if not valid:
        return JSONResponse(status_code=403, content={"detail": "Protección CSRF inválida"})
    return await call_next(request)

app.include_router(personas.router, prefix="/api")
app.include_router(minutas.router, prefix="/api")
app.include_router(pagos.router, prefix="/api")
app.include_router(documentos.router, prefix="/api")
app.include_router(alertas.router, prefix="/api")
app.include_router(flujo.router, prefix="/api")
app.include_router(authentication.router, prefix="/api")
app.include_router(franjas.router, prefix="/api")
app.include_router(administration.router, prefix="/api")
app.include_router(importaciones_territoriales.router, prefix="/api")
app.include_router(importaciones_geoespaciales.router, prefix="/api")

os.makedirs(os.getenv("UPLOAD_ROOT", "uploads"), exist_ok=True)

def validate_wkt(
    db: Session,
    wkt: str,
    allowed_geometry_types: set[str] | None = None,
):
    if not wkt:
        return
    try:
        geometry = db.execute(
            text(
                """
                SELECT
                    ST_IsValid(geom) AS is_valid,
                    ST_IsEmpty(geom) AS is_empty,
                    ST_GeometryType(geom) AS geometry_type
                FROM (
                    SELECT ST_GeomFromText(:wkt, 4326) AS geom
                ) parsed
                """
            ),
            {"wkt": wkt}
        ).mappings().one()
        if not geometry["is_valid"] or geometry["is_empty"]:
            raise HTTPException(
                status_code=400,
                detail="La geometría WKT debe ser válida y no estar vacía.",
            )
        if (
            allowed_geometry_types
            and geometry["geometry_type"] not in allowed_geometry_types
        ):
            detail = (
                "La geometría de una afectación debe ser un polígono o multipolígono."
                if allowed_geometry_types == {"ST_Polygon", "ST_MultiPolygon"}
                else "El tipo de geometría no es válido para este recurso."
            )
            raise HTTPException(
                status_code=400,
                detail=detail,
            )
    except DatabaseError:
        raise HTTPException(
            status_code=400,
            detail="Formato WKT inválido. Verifica la sintaxis de la geometría.",
        )

def set_audit_context(db: Session, user_id: int):
    """Inyecta el ID de usuario en la sesión PostgreSQL para auditoría forense (DA-10).
    Usa parámetros bind para prevenir inyección SQL."""
    db.execute(
        text("SET LOCAL \"app.current_user_id\" = :id"),
        {"id": str(user_id)}
    )

# ==================== UTILIDAD GENÉRICA CRUD ==================== #
def get_entity_by_id(db: Session, model: Type[Any], entity_id: int, id_column: str):
    entity = db.query(model).filter(getattr(model, id_column) == entity_id, model.activo == True).first()
    if not entity:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return entity

GEOMETRY_FIELDS = {
    models.Tramo: "geometria_linea",
    models.NucleoAgrario: "geometria_poligono",
    models.TramoNucleo: "geometria_segmento",
    models.Afectacion: "geometria_afectacion"
}


def require_afectacion_in_tramo_nucleo(
    db: Session,
    current_user: models.Usuario,
    id_tramo_nucleo: int,
    id_afectacion: int,
) -> models.Afectacion:
    afectacion = require_afectacion_access(db, current_user, id_afectacion)
    if afectacion.id_tramo_nucleo != id_tramo_nucleo:
        raise HTTPException(
            status_code=404,
            detail="Afectación no encontrada en el expediente solicitado",
        )
    return afectacion


def require_ciclo_scope(
    db: Session,
    current_user: models.Usuario,
    id_ciclo_afectacion: int,
    id_tramo_nucleo: int | None = None,
    id_afectacion: int | None = None,
) -> models.AfectacionCiclo:
    ciclo = db.query(models.AfectacionCiclo).filter(
        models.AfectacionCiclo.id_ciclo_afectacion == id_ciclo_afectacion,
        models.AfectacionCiclo.activo.is_(True),
    ).first()
    if ciclo is None:
        raise HTTPException(status_code=404, detail="Ciclo no encontrado")
    require_afectacion_access(db, current_user, ciclo.id_afectacion)
    if id_tramo_nucleo is not None and ciclo.id_tramo_nucleo != id_tramo_nucleo:
        raise HTTPException(
            status_code=404,
            detail="Ciclo no encontrado en el expediente solicitado",
        )
    if id_afectacion is not None and ciclo.id_afectacion != id_afectacion:
        raise HTTPException(
            status_code=404,
            detail="Ciclo no encontrado en la afectación solicitada",
        )
    return ciclo

def update_entity(db: Session, entity: Any, update_data: Any, user_id: int):
    set_audit_context(db, user_id)
    update_dict = update_data.model_dump(exclude_unset=True)

    if "geometria_wkt" in update_dict:
        wkt = update_dict.pop("geometria_wkt", None)
        model_class = type(entity)
        allowed_geometry_types = {
            models.Tramo: {"ST_MultiLineString"},
            models.NucleoAgrario: {"ST_MultiPolygon"},
            models.TramoNucleo: {"ST_MultiLineString"},
            models.Afectacion: {"ST_Polygon", "ST_MultiPolygon"},
        }.get(model_class)
        validate_wkt(db, wkt, allowed_geometry_types)

        geom_field = GEOMETRY_FIELDS.get(model_class)

        if geom_field and hasattr(entity, geom_field):
            setattr(entity, geom_field, wkt)

    for key, value in update_dict.items():
        setattr(entity, key, value)
    db.commit()
    db.refresh(entity)
    return entity

def soft_delete_entity(db: Session, entity: Any, user_id: int, motivo: str = "Baja desde API"):
    """Baja lógica con validación estricta de motivo (DA-9)."""
    if not motivo or not motivo.strip():
        raise HTTPException(
            status_code=400,
            detail="El campo 'motivo' es obligatorio y no puede estar vacío (DA-9)."
        )
    set_audit_context(db, user_id)
    entity.activo = False
    entity.fecha_baja = datetime.now(timezone.utc)
    entity.id_usuario_baja = user_id
    entity.motivo_baja = motivo.strip()
    db.commit()
    return {"status": "success", "message": "Registro eliminado lógicamente"}

@app.get("/", tags=["Root"], summary="Verificar estado de la API")
def root():
    return {"message": "API 100% configurada y lista 🚂"}

# ==================== PROYECTOS ==================== #
@app.get("/api/proyectos", tags=["Proyectos"], summary="Listar proyectos", response_model=List[schemas.ProyectoResponse])
def get_proyectos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.Proyecto).filter(models.Proyecto.activo == True)
    query = filter_projects_by_user(query, db, current_user)
    return query.offset(skip).limit(limit).all()

@app.get("/api/proyectos/{id_proyecto}", tags=["Proyectos"], summary="Obtener proyecto por ID", response_model=schemas.ProyectoResponse)
def get_proyecto_by_id(id_proyecto: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    require_project_access(db, current_user, id_proyecto)
    entity = get_entity_by_id(db, models.Proyecto, id_proyecto, "id_proyecto")
    return entity

@app.post("/api/proyectos", tags=["Proyectos"], summary="Crear proyecto", response_model=schemas.ProyectoResponse, status_code=status.HTTP_201_CREATED)
def create_proyecto(proyecto: schemas.ProyectoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'geografo']))):
    try:
        set_audit_context(db, current_user.id_usuario)
        db_proyecto = models.Proyecto(**proyecto.model_dump())
        db_proyecto.fecha_registro = datetime.now(timezone.utc).date()
        db.add(db_proyecto)
        db.commit()
        db.refresh(db_proyecto)
        return db_proyecto
    except Exception:
        db.rollback()
        raise

@app.put("/api/proyectos/{id_proyecto}", tags=["Proyectos"], summary="Actualizar proyecto", response_model=schemas.ProyectoResponse)
def update_proyecto(id_proyecto: int, data: schemas.ProyectoUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    entity = get_entity_by_id(db, models.Proyecto, id_proyecto, "id_proyecto")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/proyectos/{id_proyecto}", tags=["Proyectos"], summary="Eliminar proyecto")
def delete_proyecto(id_proyecto: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    entity = get_entity_by_id(db, models.Proyecto, id_proyecto, "id_proyecto")
    tiene_tramos_activos = db.query(models.Tramo.id_tramo).filter(
        models.Tramo.id_proyecto == id_proyecto,
        models.Tramo.activo == True,
    ).first()
    if tiene_tramos_activos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede dar de baja un proyecto con tramos activos.",
        )
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== TRAMOS ==================== #
@app.get("/api/tramos", tags=["Tramos"], summary="Listar tramos", response_model=List[schemas.TramoResponse])
def get_tramos(id_proyecto: int = Query(None), skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(
        models.Tramo.id_tramo,
        models.Tramo.id_proyecto,
        models.Tramo.clave_tramo,
        models.Tramo.nombre_tramo,
        models.Tramo.descripcion,
        models.Tramo.ancho_total_derecho_via_m,
        models.Tramo.activo,
        models.Tramo.fecha_registro,
        models.Tramo.geometria_linea.ST_AsText().label('geometria_wkt')
    ).filter(models.Tramo.activo == True)
    query = filter_by_user_tramos(query, db, current_user, models.Tramo.id_tramo)
    if id_proyecto is not None:
        query = query.filter(models.Tramo.id_proyecto == id_proyecto)
    return query.offset(skip).limit(limit).all()

@app.post("/api/tramos", tags=["Tramos"], summary="Crear tramo", response_model=schemas.TramoResponse, status_code=status.HTTP_201_CREATED)
def create_tramo(tramo: schemas.TramoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'geografo']))):
    try:
        get_entity_by_id(db, models.Proyecto, tramo.id_proyecto, "id_proyecto")
        set_audit_context(db, current_user.id_usuario)
        data = tramo.model_dump()
        wkt = data.pop("geometria_wkt", None)
        validate_wkt(db, wkt, {"ST_MultiLineString"})
        db_tramo = models.Tramo(**data, geometria_linea=wkt)
        db_tramo.fecha_registro = datetime.now(timezone.utc).date()
        db.add(db_tramo)
        db.flush()

        if current_user.rol == "geografo":
            existing = db.query(models.UsuarioTramo).filter(
                models.UsuarioTramo.id_usuario == current_user.id_usuario,
                models.UsuarioTramo.id_tramo == db_tramo.id_tramo,
            ).with_for_update().first()
            if existing is None:
                db.add(models.UsuarioTramo(
                    id_usuario=current_user.id_usuario,
                    id_tramo=db_tramo.id_tramo,
                    fecha_asignacion=datetime.now(timezone.utc),
                    activo=True,
                ))
            elif not existing.activo:
                existing.activo = True
                existing.fecha_asignacion = datetime.now(timezone.utc)
                existing.fecha_reactivacion = datetime.now(timezone.utc)
                existing.id_usuario_reactivacion = current_user.id_usuario
                existing.motivo_reactivacion = "Asignación automática por creación de tramo"

        db.commit()
        db.refresh(db_tramo)
        resp = db_tramo.__dict__.copy()
        resp["geometria_wkt"] = db.query(
            models.Tramo.geometria_linea.ST_AsText()
        ).filter(models.Tramo.id_tramo == db_tramo.id_tramo).scalar()
        return resp
    except Exception:
        db.rollback()
        raise

@app.put("/api/tramos/{id_tramo}", tags=["Tramos"], summary="Actualizar tramo", response_model=schemas.TramoResponse)
def update_tramo(id_tramo: int, data: schemas.TramoUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    entity = get_entity_by_id(db, models.Tramo, id_tramo, "id_tramo")
    db_tramo = update_entity(db, entity, data, current_user.id_usuario)
    resp = db_tramo.__dict__.copy()
    resp["geometria_wkt"] = db.query(
        models.Tramo.geometria_linea.ST_AsText()
    ).filter(models.Tramo.id_tramo == db_tramo.id_tramo).scalar()
    return resp


@app.put("/api/tramos/{id_tramo}/geometria", tags=["Tramos"], summary="Actualizar geometría de tramo", response_model=schemas.TramoResponse)
def update_tramo_geometry(id_tramo: int, data: schemas.GeometriaUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'geografo']))):
    require_tramo_access(db, current_user, id_tramo)
    entity = get_entity_by_id(db, models.Tramo, id_tramo, "id_tramo")
    db_tramo = update_entity(db, entity, data, current_user.id_usuario)
    resp = db_tramo.__dict__.copy()
    resp["geometria_wkt"] = db.query(
        models.Tramo.geometria_linea.ST_AsText()
    ).filter(models.Tramo.id_tramo == id_tramo).scalar()
    return resp

@app.delete("/api/tramos/{id_tramo}", tags=["Tramos"], summary="Eliminar tramo")
def delete_tramo(id_tramo: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    entity = get_entity_by_id(db, models.Tramo, id_tramo, "id_tramo")
    dependencies = (
        db.query(models.FranjaDerechoVia.id_franja).filter_by(id_tramo=id_tramo, activo=True).first()
        or db.query(models.TramoNucleo.id_tramo_nucleo).filter_by(id_tramo=id_tramo, activo=True).first()
        or db.query(models.UsuarioTramo.id_usuario_tramo).filter_by(id_tramo=id_tramo, activo=True).first()
    )
    if dependencies:
        raise HTTPException(status_code=409, detail="El tramo tiene relaciones activas")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)



# ==================== NUCLEOS AGRARIOS ==================== #
@app.get("/api/nucleos", tags=["Núcleos Agrarios"], summary="Listar núcleos agrarios")
def get_nucleos(
    id_tramo: int = Query(None),
    id_proyecto: int = Query(None),
    id_entidad: int = Query(None),
    id_municipio: int = Query(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))
):
    from sqlalchemy import text

    base_sql = """
        SELECT
            n.id_nucleo,
            n.nombre_nucleo,
            n.tipo_nucleo,
            n.comunidad_indigena,
            n.id_municipio,
            m.nombre AS municipio_nombre,
            ef.id_entidad,
            ef.nombre AS entidad_nombre,
            ST_AsText(n.geometria_poligono) as geometria_wkt,
            (ST_Area(n.geometria_poligono::geography) / 10000.0) as area_ha,
            CASE
                WHEN :id_tramo_espacial IS NULL THEN NULL
                ELSE (
                    SELECT ST_Area(
                        ST_CollectionExtract(
                            ST_Intersection(n.geometria_poligono, f.geometria_poligono),
                            3
                        )::geography
                    ) / 10000.0
                      FROM franja_derecho_via f
                     WHERE f.id_tramo = :id_tramo_espacial
                       AND f.activo = TRUE
                     LIMIT 1
                )
            END AS area_afectada_ha
        FROM nucleo_agrario n
        JOIN municipio m ON m.id_municipio = n.id_municipio AND m.activo = TRUE
        JOIN entidad_federativa ef ON ef.id_entidad = m.id_entidad AND ef.activo = TRUE
        WHERE n.activo = true
    """
    params = {"id_tramo_espacial": id_tramo}

    if current_user.rol != "admin":
        base_sql += """
            AND EXISTS (
                SELECT 1
                  FROM tramo_nucleo tn
                  JOIN usuario_tramo ut ON ut.id_tramo = tn.id_tramo
                 WHERE tn.id_nucleo = n.id_nucleo
                   AND tn.activo = TRUE
                   AND ut.id_usuario = :id_usuario
                   AND ut.activo = TRUE
            )
        """
        params["id_usuario"] = current_user.id_usuario

    if id_tramo is not None:
        require_tramo_access(db, current_user, id_tramo)
        base_sql += """
            AND EXISTS (
                SELECT 1
                  FROM franja_derecho_via f
                  JOIN tramo t ON t.id_tramo = f.id_tramo
                 WHERE f.id_tramo = :id_tramo
                   AND f.activo = TRUE
                   AND t.activo = TRUE
                   AND ST_Intersects(n.geometria_poligono, f.geometria_poligono)
                   AND ST_Area(
                       ST_CollectionExtract(
                           ST_Intersection(n.geometria_poligono, f.geometria_poligono),
                           3
                       )::geography
                   ) > 0
            )
        """
        params["id_tramo"] = id_tramo

    if id_proyecto is not None:
        require_project_access(db, current_user, id_proyecto)
        base_sql += """
            AND EXISTS (
                SELECT 1
                  FROM tramo_nucleo tn
                  JOIN tramo t ON t.id_tramo = tn.id_tramo
                 WHERE tn.id_nucleo = n.id_nucleo
                   AND tn.activo = TRUE
                   AND t.activo = TRUE
                   AND t.id_proyecto = :id_proyecto
            )
        """
        params["id_proyecto"] = id_proyecto

    if id_entidad is not None:
        base_sql += " AND ef.id_entidad = :id_entidad"
        params["id_entidad"] = id_entidad

    if id_municipio is not None:
        base_sql += " AND n.id_municipio = :id_municipio"
        params["id_municipio"] = id_municipio

    result = db.execute(text(base_sql), params).fetchall()

    response = []
    for r in result:
        # TODO: Para producción, el estatus debe calcularse a partir de la existencia
        # de convenios inscritos en RAN (Req. 11, vista vw_dashboard_liberacion).
        estatus = 'en_proceso'

        response.append({
            "id_nucleo": r.id_nucleo,
            "nombre_nucleo": r.nombre_nucleo,
            "tipo_nucleo": r.tipo_nucleo,
            "comunidad_indigena": r.comunidad_indigena,
            "id_municipio": r.id_municipio,
            "municipio_nombre": r.municipio_nombre,
            "id_entidad": r.id_entidad,
            "entidad_nombre": r.entidad_nombre,
            "geometria_wkt": r.geometria_wkt,
            "area_ha": round(r.area_ha, 2) if r.area_ha else 0,
            "area_afectada_ha": round(r.area_afectada_ha, 4) if r.area_afectada_ha else 0,
            "estatus_simulado": estatus
        })

    return response

@app.get("/api/tramo-detalles", tags=["Tramos"], summary="Obtener detalles y estadísticas geoespaciales de un tramo específico")
def get_tramo_detalles(id_tramo: int = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    from sqlalchemy import text
    from fastapi import HTTPException

    require_tramo_access(db, current_user, id_tramo)
    sql = text("""
        SELECT
            id_tramo,
            nombre_tramo,
            ST_AsText(geometria_linea) as geometria_wkt,
            (ST_Length(geometria_linea::geography) / 1000.0) as longitud_km
        FROM tramo
        WHERE id_tramo = :id_tramo AND activo = TRUE
    """)
    r = db.execute(sql, {"id_tramo": id_tramo}).fetchone()

    if not r:
        raise HTTPException(status_code=404, detail="Tramo no encontrado")

    return {
        "id_tramo": r.id_tramo,
        "nombre_tramo": r.nombre_tramo,
        "geometria_wkt": r.geometria_wkt,
        "longitud_km": round(r.longitud_km, 2) if r.longitud_km else 0
    }
@app.post("/api/nucleos", tags=["Núcleos Agrarios"], summary="Crear núcleo agrario", response_model=schemas.NucleoAgrarioResponse, status_code=status.HTTP_201_CREATED)
def create_nucleo(nucleo: schemas.NucleoAgrarioCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'geografo']))):
    try:
        get_entity_by_id(db, models.Municipio, nucleo.id_municipio, "id_municipio")
        set_audit_context(db, current_user.id_usuario)
        data = nucleo.model_dump()
        wkt = data.pop("geometria_wkt", None)
        validate_wkt(db, wkt, {"ST_MultiPolygon"})
        db_nucleo = models.NucleoAgrario(**data, geometria_poligono=wkt)
        db_nucleo.fecha_creacion = datetime.now(timezone.utc)
        db.add(db_nucleo)
        db.commit()
        db.refresh(db_nucleo)
        resp = db_nucleo.__dict__.copy()
        resp["geometria_wkt"] = db.query(
            models.NucleoAgrario.geometria_poligono.ST_AsText()
        ).filter(models.NucleoAgrario.id_nucleo == db_nucleo.id_nucleo).scalar()
        return resp
    except Exception:
        db.rollback()
        raise

@app.put("/api/nucleos/{id_nucleo}", tags=["Núcleos Agrarios"], summary="Actualizar núcleo agrario", response_model=schemas.NucleoAgrarioResponse)
def update_nucleo(id_nucleo: int, data: schemas.NucleoAgrarioUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    entity = get_entity_by_id(db, models.NucleoAgrario, id_nucleo, "id_nucleo")
    db_nucleo = update_entity(db, entity, data, current_user.id_usuario)
    resp = db_nucleo.__dict__.copy()
    resp["geometria_wkt"] = db.query(
        models.NucleoAgrario.geometria_poligono.ST_AsText()
    ).filter(models.NucleoAgrario.id_nucleo == db_nucleo.id_nucleo).scalar()
    return resp


@app.put("/api/nucleos/{id_nucleo}/geometria", tags=["Núcleos Agrarios"], summary="Actualizar geometría de núcleo", response_model=schemas.NucleoAgrarioResponse)
def update_nucleo_geometry(id_nucleo: int, data: schemas.GeometriaUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'geografo']))):
    require_nucleo_access(db, current_user, id_nucleo)
    entity = get_entity_by_id(db, models.NucleoAgrario, id_nucleo, "id_nucleo")
    db_nucleo = update_entity(db, entity, data, current_user.id_usuario)
    resp = db_nucleo.__dict__.copy()
    resp["geometria_wkt"] = db.query(
        models.NucleoAgrario.geometria_poligono.ST_AsText()
    ).filter(models.NucleoAgrario.id_nucleo == id_nucleo).scalar()
    return resp

@app.delete("/api/nucleos/{id_nucleo}", tags=["Núcleos Agrarios"], summary="Eliminar núcleo agrario")
def delete_nucleo(id_nucleo: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    entity = get_entity_by_id(db, models.NucleoAgrario, id_nucleo, "id_nucleo")
    if db.query(models.TramoNucleo.id_tramo_nucleo).filter_by(id_nucleo=id_nucleo, activo=True).first():
        raise HTTPException(status_code=409, detail="El núcleo tiene relaciones tramo-núcleo activas")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

@app.post("/api/nucleos/importacion-masiva", tags=["Núcleos Agrarios"], summary="Importación masiva GeoJSON")
async def importacion_masiva_nucleos(
    file: UploadFile = File(...),
    id_municipio_fallback: int = Form(None),
    id_entidad_fallback: int = Form(None),
    ids_tramo_contexto: Optional[List[int]] = Form(None),
    tipo_nucleo_fallback: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'geografo']))
):
    raise HTTPException(
        status_code=410,
        detail="La importacion directa fue retirada. Use el flujo geoespacial con staging.",
    )


# ==================== TRAMOS-NUCLEOS ==================== #
@app.get("/api/tramos-nucleos", tags=["Tramos-Nucleos"], summary="Listar tramos-nucleos", response_model=List[schemas.TramoNucleoResponse])
def list_tramos_nucleos(
    id_tramo: int = Query(None),
    id_nucleo: int = Query(None),
    db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))
):
    query = db.query(
        models.TramoNucleo.id_tramo_nucleo,
        models.TramoNucleo.id_tramo,
        models.TramoNucleo.id_nucleo,
        models.Proyecto.id_proyecto,
        models.Proyecto.clave_proyecto,
        models.Proyecto.nombre_proyecto,
        models.Tramo.nombre_tramo,
        models.NucleoAgrario.nombre_nucleo,
        models.Municipio.id_municipio,
        models.Municipio.nombre.label("municipio_nombre"),
        models.EntidadFederativa.id_entidad,
        models.EntidadFederativa.nombre.label("entidad_nombre"),
        models.TramoNucleo.consecutivo,
        models.TramoNucleo.numero_tramo,
        models.TramoNucleo.geometria_segmento.ST_AsText().label('geometria_wkt'),
        models.TramoNucleo.longitud_m,
        models.TramoNucleo.es_expropiacion,
        models.TramoNucleo.causa_problema,
        models.TramoNucleo.proyecto_no_afecta_uso_comun,
        models.TramoNucleo.activo,
        models.TramoNucleo.observaciones,
    ).join(
        models.Tramo,
        models.Tramo.id_tramo == models.TramoNucleo.id_tramo,
    ).join(
        models.Proyecto,
        models.Proyecto.id_proyecto == models.Tramo.id_proyecto,
    ).join(
        models.NucleoAgrario,
        models.NucleoAgrario.id_nucleo == models.TramoNucleo.id_nucleo,
    ).join(
        models.Municipio,
        models.Municipio.id_municipio == models.NucleoAgrario.id_municipio,
    ).join(
        models.EntidadFederativa,
        models.EntidadFederativa.id_entidad == models.Municipio.id_entidad,
    ).filter(models.TramoNucleo.activo == True)
    query = filter_by_user_tramos(
        query, db, current_user, models.TramoNucleo.id_tramo
    )
    if id_tramo:
        query = query.filter(models.TramoNucleo.id_tramo == id_tramo)
    if id_nucleo:
        query = query.filter(models.TramoNucleo.id_nucleo == id_nucleo)
    return query.all()

@app.get("/api/tramos-nucleos/{id_tramo_nucleo}", tags=["Tramos-Nucleos"], summary="Obtener tramo-nucleo", response_model=schemas.TramoNucleoResponse)
def get_tramo_nucleo(id_tramo_nucleo: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    require_tramo_nucleo_access(db, current_user, id_tramo_nucleo)
    row = db.query(
        models.TramoNucleo.id_tramo_nucleo,
        models.TramoNucleo.id_tramo,
        models.TramoNucleo.id_nucleo,
        models.Proyecto.id_proyecto,
        models.Proyecto.clave_proyecto,
        models.Proyecto.nombre_proyecto,
        models.Tramo.nombre_tramo,
        models.NucleoAgrario.nombre_nucleo,
        models.Municipio.id_municipio,
        models.Municipio.nombre.label("municipio_nombre"),
        models.EntidadFederativa.id_entidad,
        models.EntidadFederativa.nombre.label("entidad_nombre"),
        models.TramoNucleo.consecutivo,
        models.TramoNucleo.numero_tramo,
        models.TramoNucleo.geometria_segmento.ST_AsText().label('geometria_wkt'),
        models.TramoNucleo.longitud_m,
        models.TramoNucleo.es_expropiacion,
        models.TramoNucleo.causa_problema,
        models.TramoNucleo.proyecto_no_afecta_uso_comun,
        models.TramoNucleo.activo,
        models.TramoNucleo.observaciones,
    ).join(
        models.Tramo,
        models.Tramo.id_tramo == models.TramoNucleo.id_tramo,
    ).join(
        models.Proyecto,
        models.Proyecto.id_proyecto == models.Tramo.id_proyecto,
    ).join(
        models.NucleoAgrario,
        models.NucleoAgrario.id_nucleo == models.TramoNucleo.id_nucleo,
    ).join(
        models.Municipio,
        models.Municipio.id_municipio == models.NucleoAgrario.id_municipio,
    ).join(
        models.EntidadFederativa,
        models.EntidadFederativa.id_entidad == models.Municipio.id_entidad,
    ).filter(
        models.TramoNucleo.id_tramo_nucleo == id_tramo_nucleo,
        models.TramoNucleo.activo == True
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="TramoNucleo not found")
    return row

@app.post("/api/tramos-nucleos", tags=["Tramos-Nucleos"], summary="Crear tramo-nucleo", response_model=schemas.TramoNucleoResponse, status_code=status.HTTP_201_CREATED)
def create_tramo_nucleo(tramo_nucleo: schemas.TramoNucleoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    set_audit_context(db, current_user.id_usuario)
    data = tramo_nucleo.model_dump()
    wkt = data.pop("geometria_wkt", None)
    if wkt:
        validate_wkt(db, wkt, {"ST_MultiLineString"})
    db_tn = models.TramoNucleo(**data)
    if wkt:
        db_tn.geometria_segmento = wkt
    db.add(db_tn)
    db.commit()
    db.refresh(db_tn)
    resp = db_tn.__dict__.copy()
    resp["geometria_wkt"] = db.query(
        models.TramoNucleo.geometria_segmento.ST_AsText()
    ).filter(
        models.TramoNucleo.id_tramo_nucleo == db_tn.id_tramo_nucleo
    ).scalar()
    return resp

@app.put("/api/tramos-nucleos/{id_tramo_nucleo}", tags=["Tramos-Nucleos"], summary="Actualizar tramo-nucleo", response_model=schemas.TramoNucleoResponse)
def update_tramo_nucleo(id_tramo_nucleo: int, data: schemas.TramoNucleoUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    entity = get_entity_by_id(db, models.TramoNucleo, id_tramo_nucleo, "id_tramo_nucleo")
    require_tramo_access(db, current_user, entity.id_tramo)
    updated = update_entity(db, entity, data, current_user.id_usuario)
    resp = updated.__dict__.copy()
    resp["geometria_wkt"] = db.query(
        models.TramoNucleo.geometria_segmento.ST_AsText()
    ).filter(
        models.TramoNucleo.id_tramo_nucleo == updated.id_tramo_nucleo
    ).scalar()
    return resp


@app.put("/api/tramos-nucleos/{id_tramo_nucleo}/geometria", tags=["Tramos-Nucleos"], summary="Actualizar geometría de relación tramo-núcleo", response_model=schemas.TramoNucleoResponse)
def update_tramo_nucleo_geometry(id_tramo_nucleo: int, data: schemas.GeometriaUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'geografo']))):
    entity = get_entity_by_id(db, models.TramoNucleo, id_tramo_nucleo, "id_tramo_nucleo")
    require_tramo_access(db, current_user, entity.id_tramo)
    updated = update_entity(db, entity, data, current_user.id_usuario)
    resp = updated.__dict__.copy()
    resp["geometria_wkt"] = db.query(
        models.TramoNucleo.geometria_segmento.ST_AsText()
    ).filter(models.TramoNucleo.id_tramo_nucleo == id_tramo_nucleo).scalar()
    return resp

@app.delete("/api/tramos-nucleos/{id_tramo_nucleo}", tags=["Tramos-Nucleos"], summary="Eliminar tramo-nucleo")
def delete_tramo_nucleo(id_tramo_nucleo: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    entity = get_entity_by_id(db, models.TramoNucleo, id_tramo_nucleo, "id_tramo_nucleo")
    dependent_models = (
        models.Afectacion,
        models.AfectacionCiclo,
        models.ActividadCampo,
        models.Asamblea,
        models.Convenio,
        models.TramiteFifonafe,
        models.Minuta,
    )
    if any(
        db.query(model).filter(
            model.id_tramo_nucleo == id_tramo_nucleo,
            model.activo.is_(True),
        ).first()
        for model in dependent_models
    ):
        raise HTTPException(status_code=409, detail="La relación tiene expediente operativo activo")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== DASHBOARD & REPORTES ==================== #
@app.get("/api/dashboard", tags=["Dashboard"], summary="Consultar convenios y superficie", response_model=List[schemas.DashboardMetrics])
def get_dashboard_metrics(id_proyecto: int = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    sql_query = """
        SELECT v.*
          FROM vw_dashboard_liberacion v
         WHERE (:es_admin OR EXISTS (
             SELECT 1 FROM usuario_tramo ut
              WHERE ut.id_tramo = v.id_tramo
                AND ut.id_usuario = :id_usuario
                AND ut.activo = TRUE
         ))
    """
    params = {
        "es_admin": current_user.rol == "admin",
        "id_usuario": current_user.id_usuario,
    }
    if id_proyecto:
        sql_query += " AND v.id_proyecto = :id_proyecto"
        params["id_proyecto"] = id_proyecto

    sql_query += " LIMIT 100"

    return db.execute(text(sql_query), params).mappings().all()

@app.get("/api/reportes/resumen", tags=["Reportes"], summary="Generar reporte resumen")
def generar_reporte_resumen(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    conteos = db.execute(
        text(
            """
            WITH tramos_permitidos AS (
                SELECT t.id_tramo
                  FROM tramo t
                 WHERE t.activo = TRUE
                   AND (
                       :es_admin
                       OR EXISTS (
                           SELECT 1
                             FROM usuario_tramo ut
                            WHERE ut.id_tramo = t.id_tramo
                              AND ut.id_usuario = :id_usuario
                              AND ut.activo = TRUE
                       )
                   )
            )
            SELECT (
                       SELECT COUNT(*)
                         FROM convenio c
                         JOIN tramo_nucleo tn
                           ON tn.id_tramo_nucleo = c.id_tramo_nucleo
                         JOIN tramos_permitidos tp ON tp.id_tramo = tn.id_tramo
                        WHERE c.activo = TRUE AND tn.activo = TRUE
                   ) AS total_convenios,
                   (
                       SELECT COUNT(DISTINCT n.id_nucleo)
                         FROM nucleo_agrario n
                        WHERE n.activo = TRUE
                          AND (
                              :es_admin
                              OR EXISTS (
                                  SELECT 1
                                    FROM tramo_nucleo tn
                                    JOIN tramos_permitidos tp
                                      ON tp.id_tramo = tn.id_tramo
                                   WHERE tn.id_nucleo = n.id_nucleo
                                     AND tn.activo = TRUE
                              )
                          )
                   ) AS total_nucleos,
                   (
                       SELECT COUNT(*)
                         FROM afectacion a
                         JOIN tramo_nucleo tn
                           ON tn.id_tramo_nucleo = a.id_tramo_nucleo
                         JOIN tramos_permitidos tp ON tp.id_tramo = tn.id_tramo
                        WHERE a.activo = TRUE AND tn.activo = TRUE
                   ) AS total_afectaciones
            """
        ),
        {
            "es_admin": current_user.rol == "admin",
            "id_usuario": current_user.id_usuario,
        },
    ).mappings().one()
    return {"generado_el": datetime.now(timezone.utc), **dict(conteos)}

# ==================== AFECTACIONES ==================== #
def afectacion_response(db: Session, afectacion: models.Afectacion):
    response = afectacion.__dict__.copy()
    response["geometria_wkt"] = db.query(
        models.Afectacion.geometria_afectacion.ST_AsText()
    ).filter(
        models.Afectacion.id_afectacion == afectacion.id_afectacion).scalar()
    return response


@app.get("/api/afectaciones", tags=["Afectaciones"], summary="Listar afectaciones", response_model=List[schemas.AfectacionResponse])
def list_afectaciones(skip: int = 0, limit: int = 100, id_tramo_nucleo: int = Query(None), tipo_afectacion: str = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(
        models.Afectacion,
        models.Afectacion.geometria_afectacion.ST_AsText().label('geometria_wkt')
    ).filter(models.Afectacion.activo == True)
    query = query.join(
        models.TramoNucleo,
        models.TramoNucleo.id_tramo_nucleo == models.Afectacion.id_tramo_nucleo,
    )
    query = filter_by_user_tramos(
        query, db, current_user, models.TramoNucleo.id_tramo
    )
    if id_tramo_nucleo:
        query = query.filter(models.Afectacion.id_tramo_nucleo == id_tramo_nucleo)
    if tipo_afectacion:
        query = query.filter(models.Afectacion.tipo_afectacion == tipo_afectacion)

    results = []
    for afectacion, wkt in query.offset(skip).limit(limit).all():
        resp = afectacion.__dict__.copy()
        resp["geometria_wkt"] = wkt
        results.append(resp)
    return results


@app.post(
    "/api/afectaciones/colectivas",
    tags=["Afectaciones"],
    summary="Crear afectación colectiva",
    response_model=schemas.AfectacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_afectacion_colectiva(
    afectacion: schemas.AfectacionColectivaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador'])),
):
    require_tramo_nucleo_access(db, current_user, afectacion.id_tramo_nucleo)
    validate_wkt(db, afectacion.geometria_wkt, {"ST_Polygon", "ST_MultiPolygon"})
    creada = afectaciones_service.crear_colectiva(db, afectacion, current_user.id_usuario)
    return afectacion_response(db, creada)


@app.post(
    "/api/afectaciones/individuales",
    tags=["Afectaciones"],
    summary="Crear afectación individual",
    response_model=schemas.AfectacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_afectacion_individual(
    afectacion: schemas.AfectacionIndividualCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador'])),
):
    require_tramo_nucleo_access(db, current_user, afectacion.id_tramo_nucleo)
    validate_wkt(db, afectacion.geometria_wkt, {"ST_Polygon", "ST_MultiPolygon"})
    creada = afectaciones_service.crear_individual(db, afectacion, current_user.id_usuario)
    return afectacion_response(db, creada)

@app.post("/api/afectaciones", tags=["Afectaciones"], summary="Crear afectación", response_model=schemas.AfectacionResponse, status_code=status.HTTP_201_CREATED)
def create_afectacion(afectacion: schemas.AfectacionCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    set_audit_context(db, current_user.id_usuario)
    require_tramo_nucleo_access(db, current_user, afectacion.id_tramo_nucleo)

    # Validación de integridad: TramoNucleo debe existir y pertenecer al NucleoAgrario indicado
    tramo_nucleo_db = db.query(models.TramoNucleo).filter(
        models.TramoNucleo.id_tramo_nucleo == afectacion.id_tramo_nucleo,
        models.TramoNucleo.activo == True
    ).first()
    if not tramo_nucleo_db:
        raise HTTPException(status_code=404, detail="El TramoNucleo especificado no existe.")
    if tramo_nucleo_db.id_nucleo != afectacion.id_nucleo:
        raise HTTPException(status_code=400, detail="Inconsistencia: El TramoNucleo no pertenece al NucleoAgrario especificado.")

    # Compatibilidad temporal: el contrato genérico conserva consumidores
    # existentes, pero aplica las mismas reglas de separación de 2A.
    if afectacion.tipo_afectacion == 'colectivo' and afectacion.id_parcela is not None:
        raise HTTPException(status_code=400, detail="Una afectación colectiva no usa parcela normalizada.")

    # Validación: Individual requiere parcela y la parcela debe pertenecer al mismo núcleo
    if afectacion.tipo_afectacion == 'individual':
        if not afectacion.id_parcela:
            raise HTTPException(status_code=400, detail="Una afectación individual requiere id_parcela")
        afectaciones_service.validar_parcela_individual(
            db, afectacion.id_parcela, afectacion.id_nucleo
        )

    data = afectacion.model_dump()
    wkt = data.pop("geometria_wkt", None)

    if wkt:
        validate_wkt(db, wkt, {"ST_Polygon", "ST_MultiPolygon"})

    db_afectacion = models.Afectacion(**data)
    if wkt:
        db_afectacion.geometria_afectacion = wkt

    db.add(db_afectacion)
    db.commit()
    db.refresh(db_afectacion)
    return afectacion_response(db, db_afectacion)

@app.put(
    "/api/afectaciones/colectivas/{id_afectacion}",
    tags=["Afectaciones"],
    summary="Actualizar afectación colectiva",
    response_model=schemas.AfectacionResponse,
)
def update_afectacion_colectiva(
    id_afectacion: int,
    data: schemas.AfectacionColectivaUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador'])),
):
    afectacion = get_entity_by_id(db, models.Afectacion, id_afectacion, "id_afectacion")
    require_tramo_nucleo_access(db, current_user, afectacion.id_tramo_nucleo)
    if afectacion.tipo_afectacion != 'colectivo':
        raise HTTPException(status_code=409, detail="La afectación no corresponde a la ruta colectiva.")
    if data.geometria_wkt is not None:
        validate_wkt(db, data.geometria_wkt, {"ST_Polygon", "ST_MultiPolygon"})
    actualizada = afectaciones_service.actualizar_afectacion(
        db, afectacion, data, current_user.id_usuario
    )
    return afectacion_response(db, actualizada)


@app.put(
    "/api/afectaciones/individuales/{id_afectacion}",
    tags=["Afectaciones"],
    summary="Actualizar afectación individual",
    response_model=schemas.AfectacionResponse,
)
def update_afectacion_individual(
    id_afectacion: int,
    data: schemas.AfectacionIndividualUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador'])),
):
    afectacion = get_entity_by_id(db, models.Afectacion, id_afectacion, "id_afectacion")
    require_tramo_nucleo_access(db, current_user, afectacion.id_tramo_nucleo)
    if afectacion.tipo_afectacion != 'individual':
        raise HTTPException(status_code=409, detail="La afectación no corresponde a la ruta individual.")
    if data.geometria_wkt is not None:
        validate_wkt(db, data.geometria_wkt, {"ST_Polygon", "ST_MultiPolygon"})
    actualizada = afectaciones_service.actualizar_afectacion(
        db, afectacion, data, current_user.id_usuario
    )
    return afectacion_response(db, actualizada)


@app.put("/api/afectaciones/{id_afectacion}", tags=["Afectaciones"], summary="Actualizar afectación", response_model=schemas.AfectacionResponse)
def update_afectacion_route(id_afectacion: int, data: schemas.AfectacionUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    entity = get_entity_by_id(db, models.Afectacion, id_afectacion, "id_afectacion")
    require_tramo_nucleo_access(db, current_user, entity.id_tramo_nucleo)
    db_afectacion = update_entity(db, entity, data, current_user.id_usuario)
    resp = db_afectacion.__dict__.copy()
    resp["geometria_wkt"] = db.query(
        models.Afectacion.geometria_afectacion.ST_AsText()
    ).filter(
        models.Afectacion.id_afectacion == db_afectacion.id_afectacion
    ).scalar()
    return resp

@app.delete("/api/afectaciones/{id_afectacion}", tags=["Afectaciones"], summary="Eliminar afectación")
def delete_afectacion(id_afectacion: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    entity = get_entity_by_id(db, models.Afectacion, id_afectacion, "id_afectacion")
    require_tramo_nucleo_access(db, current_user, entity.id_tramo_nucleo)
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== ASAMBLEAS ==================== #
@app.get("/api/asambleas", tags=["Asambleas"], summary="Listar asambleas", response_model=List[schemas.AsambleaResponse])
def list_asambleas(
    id_tramo_nucleo: int = Query(None),
    id_afectacion: int = Query(None),
    id_ciclo_afectacion: int = Query(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo'])),
):
    query = db.query(models.Asamblea).join(
        models.TramoNucleo,
        models.TramoNucleo.id_tramo_nucleo == models.Asamblea.id_tramo_nucleo,
    ).filter(models.Asamblea.activo == True)
    query = filter_by_user_tramos(query, db, current_user, models.TramoNucleo.id_tramo)
    if id_tramo_nucleo:
        require_tramo_nucleo_access(db, current_user, id_tramo_nucleo)
        query = query.filter(models.Asamblea.id_tramo_nucleo == id_tramo_nucleo)
    if id_afectacion:
        afectacion = require_afectacion_access(db, current_user, id_afectacion)
        if id_tramo_nucleo and afectacion.id_tramo_nucleo != id_tramo_nucleo:
            raise HTTPException(status_code=404, detail="Afectación no encontrada en el expediente solicitado")
        query = query.filter(models.Asamblea.id_afectacion == id_afectacion)
    if id_ciclo_afectacion:
        require_ciclo_scope(db, current_user, id_ciclo_afectacion, id_tramo_nucleo, id_afectacion)
        query = query.filter(models.Asamblea.id_ciclo_afectacion == id_ciclo_afectacion)
    return query.all()

@app.post("/api/asambleas", tags=["Asambleas"], summary="Crear asamblea", response_model=schemas.AsambleaResponse, status_code=status.HTTP_201_CREATED)
def create_asamblea(asamblea: schemas.AsambleaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    set_audit_context(db, current_user.id_usuario)
    require_tramo_nucleo_access(db, current_user, asamblea.id_tramo_nucleo)

    # Validación de integridad: TramoNucleo debe existir y pertenecer al NucleoAgrario indicado
    tramo_nucleo_db = db.query(models.TramoNucleo).filter(
        models.TramoNucleo.id_tramo_nucleo == asamblea.id_tramo_nucleo,
        models.TramoNucleo.activo == True
    ).first()
    if not tramo_nucleo_db:
        raise HTTPException(status_code=404, detail="El TramoNucleo especificado no existe.")
    if tramo_nucleo_db.id_nucleo != asamblea.id_nucleo:
        raise HTTPException(status_code=400, detail="Inconsistencia: El TramoNucleo no pertenece al NucleoAgrario especificado.")

    if asamblea.id_padron:
        padron_db = db.query(models.PadronHistorial).filter_by(id_padron=asamblea.id_padron, activo=True).first()
        if not padron_db or padron_db.id_nucleo != asamblea.id_nucleo:
            raise HTTPException(status_code=400, detail="Inconsistencia: El Padrón no existe o no pertenece al NucleoAgrario especificado.")

    datos_asamblea = asamblea.model_dump()
    if asamblea.id_afectacion is None or asamblea.id_ciclo_afectacion is None:
        colectivas = db.query(models.Afectacion).filter(
            models.Afectacion.id_tramo_nucleo == asamblea.id_tramo_nucleo,
            models.Afectacion.tipo_afectacion == 'colectivo',
            models.Afectacion.activo == True,
        ).all()
        if len(colectivas) != 1 or asamblea.contexto_proceso != 'cop_original':
            raise HTTPException(
                status_code=409,
                detail="Indique la afectación y el ciclo; el expediente no permite resolverlos de forma inequívoca.",
            )
        ciclo = db.query(models.AfectacionCiclo).filter(
            models.AfectacionCiclo.id_afectacion == colectivas[0].id_afectacion,
            models.AfectacionCiclo.tipo_ciclo == 'cop_original',
            models.AfectacionCiclo.activo == True,
        ).one()
        datos_asamblea['id_afectacion'] = colectivas[0].id_afectacion
        datos_asamblea['id_ciclo_afectacion'] = ciclo.id_ciclo_afectacion

    db_asamblea = models.Asamblea(**datos_asamblea)
    db_asamblea.id_usuario_registro = current_user.id_usuario
    db.add(db_asamblea)
    db.commit()
    db.refresh(db_asamblea)
    return db_asamblea

@app.put("/api/asambleas/{id_asamblea}", tags=["Asambleas"], summary="Actualizar asamblea", response_model=schemas.AsambleaResponse)
def update_asamblea_route(id_asamblea: int, data: schemas.AsambleaUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    entity = get_entity_by_id(db, models.Asamblea, id_asamblea, "id_asamblea")
    require_tramo_nucleo_access(db, current_user, entity.id_tramo_nucleo)
    if entity.tipo_asamblea == 'retiro_fondos' and data.estatus_asamblea == 'completo':
        raise HTTPException(status_code=409, detail="Use la operación explícita para completar el retiro de fondos.")
    if data.id_padron is not None:
        padron_db = db.query(models.PadronHistorial).filter_by(id_padron=data.id_padron, activo=True).first()
        if not padron_db or padron_db.id_nucleo != entity.id_nucleo:
            raise HTTPException(status_code=400, detail="Inconsistencia: El Padrón no existe o no pertenece al NucleoAgrario de la asamblea.")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/asambleas/{id_asamblea}", tags=["Asambleas"], summary="Eliminar asamblea")
def delete_asamblea(id_asamblea: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    entity = get_entity_by_id(db, models.Asamblea, id_asamblea, "id_asamblea")
    require_tramo_nucleo_access(db, current_user, entity.id_tramo_nucleo)
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== CONVENIOS ==================== #
@app.get("/api/convenios", tags=["Convenios"], summary="Listar convenios", response_model=List[schemas.ConvenioResponse])
def list_convenios(
    id_tramo_nucleo: int = Query(None),
    id_afectacion: int = Query(None),
    id_ciclo_afectacion: int = Query(None),
    tipo_convenio: str = Query(None),
    inscrito: bool = Query(None),
    db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))
):
    query = db.query(models.Convenio).join(
        models.TramoNucleo,
        models.TramoNucleo.id_tramo_nucleo == models.Convenio.id_tramo_nucleo,
    ).filter(models.Convenio.activo == True)
    query = filter_by_user_tramos(query, db, current_user, models.TramoNucleo.id_tramo)
    if id_tramo_nucleo:
        require_tramo_nucleo_access(db, current_user, id_tramo_nucleo)
        query = query.filter(models.Convenio.id_tramo_nucleo == id_tramo_nucleo)
    if id_afectacion:
        afectacion = require_afectacion_access(db, current_user, id_afectacion)
        if id_tramo_nucleo and afectacion.id_tramo_nucleo != id_tramo_nucleo:
            raise HTTPException(status_code=404, detail="Afectación no encontrada en el expediente solicitado")
        query = query.filter(models.Convenio.id_afectacion == id_afectacion)
    if id_ciclo_afectacion:
        require_ciclo_scope(db, current_user, id_ciclo_afectacion, id_tramo_nucleo, id_afectacion)
        query = query.filter(models.Convenio.id_ciclo_afectacion == id_ciclo_afectacion)
    if tipo_convenio:
        query = query.filter(models.Convenio.tipo_convenio == tipo_convenio)
    if inscrito is True:
        query = query.filter(models.Convenio.convenio_inscrito_fecha_ran != None)
    return query.all()

@app.post("/api/convenios", tags=["Convenios"], summary="Crear convenio", response_model=schemas.ConvenioResponse, status_code=status.HTTP_201_CREATED)
def create_convenio(convenio: schemas.ConvenioCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    set_audit_context(db, current_user.id_usuario)
    require_tramo_nucleo_access(db, current_user, convenio.id_tramo_nucleo)

    # Validación de integridad: TramoNucleo debe existir
    tramo_nucleo_db = db.query(models.TramoNucleo).filter(
        models.TramoNucleo.id_tramo_nucleo == convenio.id_tramo_nucleo,
        models.TramoNucleo.activo == True
    ).first()
    if not tramo_nucleo_db:
        raise HTTPException(status_code=404, detail="El TramoNucleo especificado no existe.")

    # Validación de integridad: La Afectación debe existir y pertenecer al mismo TramoNucleo
    afectacion_db = db.query(models.Afectacion).filter(
        models.Afectacion.id_afectacion == convenio.id_afectacion,
        models.Afectacion.activo == True
    ).first()
    if not afectacion_db:
        raise HTTPException(status_code=404, detail="La Afectación especificada no existe.")
    if afectacion_db.id_tramo_nucleo != convenio.id_tramo_nucleo:
        raise HTTPException(status_code=400, detail="Inconsistencia: La Afectación no pertenece al TramoNucleo especificado.")

    padre_db = None
    if convenio.id_convenio_padre:
        padre_db = db.query(models.Convenio).filter_by(id_convenio=convenio.id_convenio_padre, activo=True).first()
        if not padre_db or padre_db.id_afectacion != convenio.id_afectacion:
            raise HTTPException(status_code=400, detail="Inconsistencia: El Convenio Padre no existe o no pertenece a la misma Afectación.")

    if convenio.id_asamblea_autorizacion:
        asamblea_db = db.query(models.Asamblea).filter_by(id_asamblea=convenio.id_asamblea_autorizacion, activo=True).first()
        if not asamblea_db or asamblea_db.id_tramo_nucleo != convenio.id_tramo_nucleo:
            raise HTTPException(status_code=400, detail="Inconsistencia: La Asamblea no existe o no pertenece al mismo TramoNucleo.")

    # B6 / B7: Asamblea constraint
    if (convenio.tipo_afectacion == 'colectivo'
            and convenio.tipo_convenio != 'modificatorio'
            and not convenio.id_asamblea_autorizacion):
        raise HTTPException(status_code=400, detail="Convenios colectivos requieren id_asamblea_autorizacion (chk_colectivo_requiere_asamblea)")
    if convenio.tipo_afectacion == 'individual' and convenio.id_asamblea_autorizacion:
        raise HTTPException(status_code=400, detail="Convenios individuales no deben tener asamblea (chk_individual_sin_asamblea)")

    # B8: Modificatorio padre constraint
    if convenio.tipo_convenio == 'modificatorio' and not convenio.id_convenio_padre:
        raise HTTPException(status_code=400, detail="Los convenios modificatorios requieren un id_convenio_padre")

    # RN-1: Compatibilidad tipo_convenio vs tipo_afectacion
    colectivo_permitidos = ['cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias']
    individual_permitidos = ['cop_original', 'modificatorio', 'ampliacion', 'ampliacion_remanente']
    if convenio.tipo_afectacion == 'colectivo' and convenio.tipo_convenio not in colectivo_permitidos:
        raise HTTPException(status_code=400, detail=f"tipo_convenio {convenio.tipo_convenio} no permitido para afectación colectivo")
    if convenio.tipo_afectacion == 'individual' and convenio.tipo_convenio not in individual_permitidos:
        raise HTTPException(status_code=400, detail=f"tipo_convenio {convenio.tipo_convenio} no permitido para afectación individual")

    # RN-2: Obras Complementarias sin BDT
    if convenio.tipo_convenio == 'obras_complementarias' and convenio.monto_bdt is not None:
        raise HTTPException(status_code=400, detail="Convenios de obras complementarias no deben tener monto_bdt")

    # RN-3: Modificatorio individual restricciones
    if convenio.tipo_convenio == 'modificatorio' and convenio.tipo_afectacion == 'individual':
        if convenio.superficie_real_afectada_ha or convenio.superficie_total_ha or convenio.monto_bdt:
             raise HTTPException(status_code=400, detail="Modificatorio individual solo permite fecha_firma, monto_90 y monto_100")

    # RN-5: Superficie field exclusivity
    if convenio.tipo_afectacion == 'colectivo' and convenio.superficie_total_ha is not None:
        raise HTTPException(status_code=400, detail="Afectación colectiva debe usar superficie_real_afectada_ha, no superficie_total_ha")
    if convenio.tipo_afectacion == 'individual' and convenio.superficie_real_afectada_ha is not None:
        raise HTTPException(status_code=400, detail="Afectación individual debe usar superficie_total_ha, no superficie_real_afectada_ha")

    datos_convenio = convenio.model_dump()
    if convenio.id_ciclo_afectacion is None:
        if convenio.tipo_convenio == 'modificatorio' and padre_db is not None:
            datos_convenio['id_ciclo_afectacion'] = padre_db.id_ciclo_afectacion
        elif convenio.tipo_convenio == 'cop_original':
            ciclo = db.query(models.AfectacionCiclo).filter(
                models.AfectacionCiclo.id_afectacion == convenio.id_afectacion,
                models.AfectacionCiclo.tipo_ciclo == 'cop_original',
                models.AfectacionCiclo.activo == True,
            ).one_or_none()
            if ciclo is None:
                raise HTTPException(status_code=409, detail="No existe el ciclo original de la afectación.")
            datos_convenio['id_ciclo_afectacion'] = ciclo.id_ciclo_afectacion
        else:
            raise HTTPException(
                status_code=409,
                detail="Abra y seleccione explícitamente el ciclo de la variante.",
            )

    db_convenio = models.Convenio(**datos_convenio)
    db_convenio.id_usuario_registro = current_user.id_usuario
    db.add(db_convenio)
    db.commit()
    db.refresh(db_convenio)
    return db_convenio

@app.put("/api/convenios/{id_convenio}", tags=["Convenios"], summary="Actualizar convenio", response_model=schemas.ConvenioResponse)
def update_convenio_route(id_convenio: int, data: schemas.ConvenioUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    entity = get_entity_by_id(db, models.Convenio, id_convenio, "id_convenio")
    require_tramo_nucleo_access(db, current_user, entity.id_tramo_nucleo)
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/convenios/{id_convenio}", tags=["Convenios"], summary="Eliminar convenio")
def delete_convenio(id_convenio: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    entity = get_entity_by_id(db, models.Convenio, id_convenio, "id_convenio")
    require_tramo_nucleo_access(db, current_user, entity.id_tramo_nucleo)
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== PADRON ==================== #
@app.get("/api/padrones", tags=["Padrones"], summary="Listar padrones", response_model=List[schemas.PadronHistorialResponse])
def list_padrones(id_nucleo: int = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.PadronHistorial).filter(models.PadronHistorial.activo == True)
    if id_nucleo:
        query = query.filter(models.PadronHistorial.id_nucleo == id_nucleo)
    return query.all()

@app.post("/api/padrones", tags=["Padrones"], summary="Crear padron", response_model=schemas.PadronHistorialResponse, status_code=status.HTTP_201_CREATED)
def create_padron(padron: schemas.PadronHistorialCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    db_padron = models.PadronHistorial(**padron.model_dump())
    db_padron.fecha_registro = datetime.now(timezone.utc)
    db_padron.id_usuario_registro = current_user.id_usuario
    db.add(db_padron)
    db.commit()
    db.refresh(db_padron)
    return db_padron

@app.put("/api/padrones/{id_padron}", tags=["Padrones"], summary="Actualizar padron", response_model=schemas.PadronHistorialResponse)
def update_padron_route(id_padron: int, data: schemas.PadronHistorialUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.PadronHistorial, id_padron, "id_padron")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/padrones/{id_padron}", tags=["Padrones"], summary="Eliminar padron")
def delete_padron(id_padron: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.PadronHistorial, id_padron, "id_padron")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== ACTIVIDAD CAMPO ==================== #
@app.get("/api/actividades-campo", tags=["Actividades de Campo"], summary="Listar actividades de campo", response_model=List[schemas.ActividadCampoResponse])
def list_actividades(
    id_tramo_nucleo: int = Query(None),
    id_ciclo_afectacion: int = Query(None),
    tipo_actividad: str = Query(None),
    solo_compartidas: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo'])),
):
    query = db.query(models.ActividadCampo).join(
        models.TramoNucleo,
        models.TramoNucleo.id_tramo_nucleo == models.ActividadCampo.id_tramo_nucleo,
    ).filter(models.ActividadCampo.activo == True)
    query = filter_by_user_tramos(query, db, current_user, models.TramoNucleo.id_tramo)
    if id_tramo_nucleo:
        require_tramo_nucleo_access(db, current_user, id_tramo_nucleo)
        query = query.filter(models.ActividadCampo.id_tramo_nucleo == id_tramo_nucleo)
    if id_ciclo_afectacion:
        require_ciclo_scope(db, current_user, id_ciclo_afectacion, id_tramo_nucleo)
        query = query.filter(models.ActividadCampo.id_ciclo_afectacion == id_ciclo_afectacion)
    if solo_compartidas:
        query = query.filter(models.ActividadCampo.id_ciclo_afectacion.is_(None))
    if tipo_actividad:
        query = query.filter(models.ActividadCampo.tipo_actividad == tipo_actividad)
    return query.all()

@app.post("/api/actividades-campo", tags=["Actividades de Campo"], summary="Crear actividad de campo", response_model=schemas.ActividadCampoResponse, status_code=status.HTTP_201_CREATED)
def create_actividad(act: schemas.ActividadCampoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    set_audit_context(db, current_user.id_usuario)
    require_tramo_nucleo_access(db, current_user, act.id_tramo_nucleo)

    # Validación de integridad: TramoNucleo debe existir
    tramo_nucleo_db = db.query(models.TramoNucleo).filter(
        models.TramoNucleo.id_tramo_nucleo == act.id_tramo_nucleo,
        models.TramoNucleo.activo == True
    ).first()
    if not tramo_nucleo_db:
        raise HTTPException(status_code=404, detail="El TramoNucleo especificado no existe.")

    db_act = models.ActividadCampo(**act.model_dump())
    db_act.fecha_registro = datetime.now(timezone.utc)
    db_act.id_usuario_registro = current_user.id_usuario
    db.add(db_act)
    db.commit()
    db.refresh(db_act)
    return db_act

@app.put("/api/actividades-campo/{id_actividad}", tags=["Actividades de Campo"], summary="Actualizar actividad de campo", response_model=schemas.ActividadCampoResponse)
def update_actividad_route(id_actividad: int, data: schemas.ActividadCampoUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    entity = get_entity_by_id(db, models.ActividadCampo, id_actividad, "id_actividad")
    require_tramo_nucleo_access(db, current_user, entity.id_tramo_nucleo)
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/actividades-campo/{id_actividad}", tags=["Actividades de Campo"], summary="Eliminar actividad de campo")
def delete_actividad(id_actividad: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    entity = get_entity_by_id(db, models.ActividadCampo, id_actividad, "id_actividad")
    require_tramo_nucleo_access(db, current_user, entity.id_tramo_nucleo)
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== TRAMITE FIFONAFE ==================== #
@app.get("/api/fifonafe", tags=["Fifonafe"], summary="Listar trámites fifonafe", response_model=List[schemas.TramiteFifonafeResponse])
def list_fifonafe(
    id_tramo_nucleo: int = Query(None),
    id_afectacion: int = Query(None),
    id_ciclo_afectacion: int = Query(None),
    tipo_tramite: str = Query(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo'])),
):
    query = db.query(models.TramiteFifonafe).join(
        models.TramoNucleo,
        models.TramoNucleo.id_tramo_nucleo == models.TramiteFifonafe.id_tramo_nucleo,
    ).filter(models.TramiteFifonafe.activo == True)
    query = filter_by_user_tramos(query, db, current_user, models.TramoNucleo.id_tramo)
    if id_tramo_nucleo:
        require_tramo_nucleo_access(db, current_user, id_tramo_nucleo)
        query = query.filter(models.TramiteFifonafe.id_tramo_nucleo == id_tramo_nucleo)
    if id_afectacion:
        afectacion = require_afectacion_access(db, current_user, id_afectacion)
        if id_tramo_nucleo and afectacion.id_tramo_nucleo != id_tramo_nucleo:
            raise HTTPException(status_code=404, detail="Afectación no encontrada en el expediente solicitado")
        query = query.filter(models.TramiteFifonafe.id_afectacion == id_afectacion)
    if id_ciclo_afectacion:
        require_ciclo_scope(db, current_user, id_ciclo_afectacion, id_tramo_nucleo, id_afectacion)
        query = query.filter(models.TramiteFifonafe.id_ciclo_afectacion == id_ciclo_afectacion)
    if tipo_tramite:
        query = query.filter(models.TramiteFifonafe.tipo_tramite == tipo_tramite)
    return query.all()

@app.post("/api/fifonafe", tags=["Fifonafe"], summary="Crear trámite fifonafe", response_model=schemas.TramiteFifonafeResponse, status_code=status.HTTP_201_CREATED)
def create_fifonafe(tramite: schemas.TramiteFifonafeCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    set_audit_context(db, current_user.id_usuario)
    require_tramo_nucleo_access(db, current_user, tramite.id_tramo_nucleo)

    # Validaciones de coherencia jerárquica
    tn_db = db.query(models.TramoNucleo).filter_by(id_tramo_nucleo=tramite.id_tramo_nucleo, activo=True).first()
    if not tn_db:
        raise HTTPException(status_code=404, detail="El TramoNucleo no existe.")

    if tramite.id_afectacion:
        afectacion_db = db.query(models.Afectacion).filter_by(id_afectacion=tramite.id_afectacion, activo=True).first()
        if not afectacion_db or afectacion_db.id_tramo_nucleo != tramite.id_tramo_nucleo:
            raise HTTPException(status_code=400, detail="Inconsistencia: La Afectación no existe o no pertenece al TramoNucleo especificado.")

    convenio_db = None
    if tramite.id_convenio:
        convenio_db = db.query(models.Convenio).filter_by(id_convenio=tramite.id_convenio, activo=True).first()
        if not convenio_db or convenio_db.id_tramo_nucleo != tramite.id_tramo_nucleo:
            raise HTTPException(status_code=400, detail="Inconsistencia: El Convenio no existe o no pertenece al TramoNucleo especificado.")

    datos_tramite = tramite.model_dump()
    if convenio_db is not None:
        datos_tramite['id_afectacion'] = convenio_db.id_afectacion
        datos_tramite['id_ciclo_afectacion'] = convenio_db.id_ciclo_afectacion
        datos_tramite['tipo_afectacion'] = convenio_db.tipo_afectacion
    db_tram = models.TramiteFifonafe(**datos_tramite)
    db.add(db_tram)
    db.commit()
    db.refresh(db_tram)
    return db_tram

@app.put("/api/fifonafe/{id_tramite}", tags=["Fifonafe"], summary="Actualizar trámite fifonafe", response_model=schemas.TramiteFifonafeResponse)
def update_fifonafe_route(id_tramite: int, data: schemas.TramiteFifonafeUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    entity = get_entity_by_id(db, models.TramiteFifonafe, id_tramite, "id_tramite_fifonafe")
    require_tramo_nucleo_access(db, current_user, entity.id_tramo_nucleo)
    if entity.tipo_tramite == 'indemnizacion' and data.estatus == 'completo':
        raise HTTPException(status_code=409, detail="Use la operación explícita para completar la indemnización.")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/fifonafe/{id_tramite}", tags=["Fifonafe"], summary="Eliminar trámite fifonafe")
def delete_fifonafe(id_tramite: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    entity = get_entity_by_id(db, models.TramiteFifonafe, id_tramite, "id_tramite_fifonafe")
    require_tramo_nucleo_access(db, current_user, entity.id_tramo_nucleo)
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== DOCUMENTACION ==================== #
@app.get("/api/documentacion", tags=["Documentación"], summary="Listar documentación de soporte", response_model=List[schemas.DocumentacionSoporteResponse])
def list_documentacion(entidad_tipo: str = Query(None), entidad_id: int = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.DocumentacionSoporte).filter(models.DocumentacionSoporte.activo == True)
    if (entidad_tipo is None) != (entidad_id is None):
        raise HTTPException(status_code=400, detail="Indique entidad_tipo y entidad_id juntos")
    if entidad_tipo is None and current_user.rol != "admin":
        raise HTTPException(status_code=400, detail="Indique la entidad documental a consultar")
    if entidad_tipo:
        require_document_relation_access(db, current_user, entidad_tipo, entidad_id)
        query = query.filter(models.DocumentacionSoporte.entidad_relacionada_tipo == entidad_tipo)
    if entidad_id:
        query = query.filter(models.DocumentacionSoporte.entidad_relacionada_id == entidad_id)
    return query.all()

@app.post("/api/documentacion", tags=["Documentación"], summary="Crear documentación de soporte", response_model=schemas.DocumentacionSoporteResponse, status_code=status.HTTP_201_CREATED)
def create_documentacion(doc: schemas.DocumentacionSoporteCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    require_document_relation_access(
        db,
        current_user,
        doc.entidad_relacionada_tipo,
        doc.entidad_relacionada_id,
    )
    db_doc = models.DocumentacionSoporte(**doc.model_dump())
    db_doc.fecha_carga = datetime.now(timezone.utc)
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

@app.put("/api/documentacion/{id_documento}", tags=["Documentación"], summary="Actualizar documentación de soporte", response_model=schemas.DocumentacionSoporteResponse)
def update_documentacion_route(id_documento: int, data: schemas.DocumentacionSoporteUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = require_document_access(db, current_user, id_documento)
    return update_entity(db, entity, data, current_user.id_usuario)

# ==================== SUBEXPEDIENTE 2C ==================== #
@app.get(
    "/api/tramos-nucleos/{id_tramo_nucleo}/afectaciones/{id_afectacion}/subexpediente",
    tags=["Subexpedientes"],
    summary="Obtener resumen de subexpediente por afectación",
    response_model=schemas.AfectacionSubexpedienteResponse,
)
def get_subexpediente_afectacion(
    id_tramo_nucleo: int,
    id_afectacion: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo'])),
):
    afectacion = require_afectacion_in_tramo_nucleo(
        db,
        current_user,
        id_tramo_nucleo,
        id_afectacion,
    )
    tramo_nucleo = db.query(
        models.TramoNucleo.id_tramo_nucleo,
        models.TramoNucleo.id_tramo,
        models.TramoNucleo.id_nucleo,
        models.TramoNucleo.consecutivo,
        models.TramoNucleo.numero_tramo,
        models.TramoNucleo.geometria_segmento.ST_AsText().label('geometria_wkt'),
        models.TramoNucleo.longitud_m,
        models.TramoNucleo.es_expropiacion,
        models.TramoNucleo.causa_problema,
        models.TramoNucleo.proyecto_no_afecta_uso_comun,
        models.TramoNucleo.activo,
        models.TramoNucleo.observaciones,
    ).filter(
        models.TramoNucleo.id_tramo_nucleo == id_tramo_nucleo,
        models.TramoNucleo.activo == True,
    ).first()
    nucleo = db.query(
        models.NucleoAgrario.id_nucleo,
        models.NucleoAgrario.nombre_nucleo,
        models.NucleoAgrario.tipo_nucleo,
        models.NucleoAgrario.comunidad_indigena,
        models.NucleoAgrario.geometria_poligono.ST_AsText().label('geometria_wkt'),
    ).filter(
        models.NucleoAgrario.id_nucleo == afectacion.id_nucleo,
        models.NucleoAgrario.activo == True,
    ).first()
    afectacion_row = db.query(
        models.Afectacion.id_afectacion,
        models.Afectacion.id_nucleo,
        models.Afectacion.id_tramo_nucleo,
        models.Afectacion.id_parcela,
        models.Afectacion.tipo_afectacion,
        models.Afectacion.tipo_tenencia,
        models.Afectacion.subtipo_tenencia,
        models.Afectacion.destino_superficie,
        models.Afectacion.no_parcela_solar,
        models.Afectacion.superficie_afectada_ha,
        models.Afectacion.geometria_afectacion.ST_AsText().label('geometria_wkt'),
        models.Afectacion.num_personas_afectadas,
        models.Afectacion.situacion_juridica,
        models.Afectacion.documentacion_disponible,
        models.Afectacion.documentacion_faltante,
        models.Afectacion.origen_registro,
        models.Afectacion.tipo_salida_terminal,
        models.Afectacion.fecha_salida_terminal,
        models.Afectacion.motivo_salida_terminal,
        models.Afectacion.activo,
        models.Afectacion.observaciones,
    ).filter(
        models.Afectacion.id_afectacion == id_afectacion,
        models.Afectacion.activo == True,
    ).first()
    antecedentes = db.query(models.ActividadCampo).filter(
        models.ActividadCampo.id_tramo_nucleo == id_tramo_nucleo,
        models.ActividadCampo.id_ciclo_afectacion.is_(None),
        models.ActividadCampo.activo == True,
    ).order_by(
        models.ActividadCampo.fecha_realizada,
        models.ActividadCampo.fecha_programada,
        models.ActividadCampo.id_actividad,
    ).all()
    documentos_maestros = db.query(models.DocumentacionSoporte).filter(
        models.DocumentacionSoporte.entidad_relacionada_tipo == 'tramo_nucleo',
        models.DocumentacionSoporte.entidad_relacionada_id == id_tramo_nucleo,
        models.DocumentacionSoporte.activo == True,
    ).order_by(models.DocumentacionSoporte.id_documento.desc()).all()
    return {
        "id_tramo_nucleo": id_tramo_nucleo,
        "id_afectacion": id_afectacion,
        "tramo_nucleo": tramo_nucleo,
        "nucleo": nucleo,
        "afectacion": afectacion_row,
        "estado": flujo_service.obtener_estado_afectacion(
            db,
            current_user,
            id_afectacion,
        ),
        "antecedentes_compartidos": antecedentes,
        "documentos_maestros": documentos_maestros,
    }

# ==================== ALERTAS ==================== #
@app.get("/api/alertas", tags=["Alertas"], summary="Listar alertas", response_model=List[schemas.AlertaResponse])
def list_alertas(activa: bool = Query(True), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.Alertas).filter(models.Alertas.activo == True)
    if activa is not None:
        query = query.filter(models.Alertas.esta_activa == activa)
    return query.all()

@app.post("/api/alertas", tags=["Alertas"], summary="Crear alerta", response_model=schemas.AlertaResponse, status_code=status.HTTP_201_CREATED)
def create_alerta(alerta: schemas.AlertaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    db_alerta = models.Alertas(**alerta.model_dump())
    db_alerta.fecha_creacion = datetime.now(timezone.utc)
    db.add(db_alerta)
    db.commit()
    db.refresh(db_alerta)
    return db_alerta

@app.put("/api/alertas/{id_alerta}", tags=["Alertas"], summary="Actualizar alerta", response_model=schemas.AlertaResponse)
def update_alerta(id_alerta: int, data: schemas.AlertaUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Alertas, id_alerta, "id_alerta")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/alertas/{id_alerta}", tags=["Alertas"], summary="Eliminar alerta")
def delete_alerta(id_alerta: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Alertas, id_alerta, "id_alerta")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== USUARIOS ==================== #
@app.post("/api/usuarios", tags=["Usuarios"], summary="Crear usuario", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def create_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    set_audit_context(db, current_user.id_usuario)
    db_user = db.query(models.Usuario).filter(
        func.lower(func.btrim(models.Usuario.correo)) == usuario.correo
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    hashed_password = auth.get_password_hash(usuario.contrasena)
    user_data = usuario.model_dump(exclude={"contrasena"})
    db_usuario = models.Usuario(**user_data, contrasena_hash=hashed_password, fecha_alta=datetime.now(timezone.utc))
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

@app.get("/api/usuarios", tags=["Usuarios"], summary="Listar usuarios", response_model=list[schemas.UsuarioResponse])
def get_usuarios(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    return db.query(models.Usuario).filter(models.Usuario.activo == True).offset(skip).limit(limit).all()

@app.put("/api/usuarios/{id_usuario}", tags=["Usuarios"], summary="Actualizar usuario", response_model=schemas.UsuarioResponse)
def update_usuario(id_usuario: int, data: schemas.UsuarioUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    entity = get_entity_by_id(db, models.Usuario, id_usuario, "id_usuario")
    if entity.rol == "admin" and data.rol is not None and data.rol != "admin":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext('software_pa_active_admin'))"))
        if not db.query(models.Usuario.id_usuario).filter(
            models.Usuario.activo.is_(True),
            models.Usuario.rol == "admin",
            models.Usuario.id_usuario != id_usuario,
        ).first():
            raise HTTPException(status_code=409, detail="No se puede degradar al último administrador activo")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/usuarios/{id_usuario}", tags=["Usuarios"], summary="Eliminar usuario")
def delete_usuario(id_usuario: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    administration_service.deactivate_user(
        db,
        target_user_id=id_usuario,
        actor_user_id=current_user.id_usuario,
        reason=motivo,
    )
    return {"status": "success", "message": "Usuario desactivado"}

# ==================== CATÁLOGOS ==================== #
@app.get("/api/catalogos/entidades", tags=["Catálogos"], summary="Listar entidades federativas", response_model=List[schemas.EntidadFederativaResponse])
def get_entidades(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))
):
    return db.query(models.EntidadFederativa).filter(models.EntidadFederativa.activo == True).all()

@app.get("/api/catalogos/municipios", tags=["Catálogos"], summary="Listar municipios", response_model=List[schemas.MunicipioResponse])
def get_municipios(
    id_entidad: int = Query(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))
):
    query = db.query(models.Municipio).filter(models.Municipio.activo == True)
    if id_entidad:
        query = query.filter(models.Municipio.id_entidad == id_entidad)
    return query.all()

@app.get("/api/reportes/exportar/tramos", tags=["Reportes"], summary="Exportar tramos a CSV")
def exportar_tramos_csv(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    tramos = db.query(models.Tramo).filter(models.Tramo.activo == True).all()
    data = []
    for t in tramos:
        data.append({
            "ID Tramo": t.id_tramo,
            "Clave": t.clave_tramo,
            "Nombre": t.nombre_tramo,
            "Ancho de Vía (m)": float(t.ancho_total_derecho_via_m) if t.ancho_total_derecho_via_m else None,
            "Fecha Registro": t.fecha_registro
        })
    df = pd.DataFrame(data)
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=tramos_export.csv"
    return response

# ==================== GEOJSON IMPORTER ==================== #
@app.post("/api/geometria/importar-geojson", tags=["Geometría"], summary="Importar GeoJSON")
def importar_geojson(
    tipo_entidad: str = Query(..., description="Opciones: tramo, nucleo_agrario, tramo_nucleo, afectacion"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))
):
    """
    Importa masivamente registros desde un archivo GeoJSON.
    Las 'properties' del GeoJSON deben coincidir con los nombres de las columnas de la tabla destino.
    """
    # Mapeo de tablas y sus columnas espaciales
    mapa_entidades = {
        "tramo": (models.Tramo, "geometria_linea"),
        "nucleo_agrario": (models.NucleoAgrario, "geometria_poligono"),
        "tramo_nucleo": (models.TramoNucleo, "geometria_segmento"),
        "afectacion": (models.Afectacion, "geometria_afectacion")
    }

    if tipo_entidad not in mapa_entidades:
        raise HTTPException(status_code=400, detail="Tipo de entidad no soportado para importación GeoJSON.")

    Modelo, geom_column_name = mapa_entidades[tipo_entidad]

    try:
        content = file.file.read()
        geojson_data = json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Archivo GeoJSON inválido o malformado.")

    if "features" not in geojson_data:
        raise HTTPException(status_code=400, detail="El GeoJSON debe contener un arreglo de 'features'.")

    # Establecer contexto de auditoría
    set_audit_context(db, current_user.id_usuario)

    columnas_validas = [c.name for c in Modelo.__table__.columns]
    registros_insertados = 0

    for feature in geojson_data["features"]:
        propiedades = feature.get("properties", {})
        geometria = feature.get("geometry", None)

        if not geometria:
            continue

        # Filtrar propiedades para que solo queden las que existen en el modelo (ignorar geom_column y Primary Key)
        datos_limpios = {}
        pk_name = inspect(Modelo).primary_key[0].name
        for k, v in propiedades.items():
            if k in columnas_validas and k not in [geom_column_name, pk_name]:
                datos_limpios[k] = v

        # Asegurar requerimientos de negocio o defaults
        if "activo" not in datos_limpios:
            datos_limpios["activo"] = True

        # Dependiendo del modelo, algunas columnas de fecha deben pasarse si no están
        if Modelo == models.Tramo:
            if "fecha_registro" not in datos_limpios:
                datos_limpios["fecha_registro"] = datetime.now(timezone.utc).date()

        if Modelo == models.NucleoAgrario:
            if "fecha_creacion" not in datos_limpios:
                datos_limpios["fecha_creacion"] = datetime.now(timezone.utc)

        # Crear instancia del ORM
        nuevo_registro = Modelo(**datos_limpios)

        # Asignar geometría usando ST_GeomFromGeoJSON
        # Para que SQLAlchemy acepte la función cruda en la propiedad, usamos text() en un UPDATE,
        # pero como es INSERT, lo mejor es hacer un flush() y luego un UPDATE,
        # o asignar la propiedad en la creación usando db.scalar.
        # Lo más limpio en GeoAlchemy2 es castear el string del geom:
        # Pero GeoAlchemy soporta WKT, no GeoJSON directo en asignación a propiedad.
        # Por lo tanto, guardamos temporalmente el registro sin geometría, hacemos flush y luego update con postgis.

        db.add(nuevo_registro)
        db.flush() # Obtenemos el ID generado

        pk_name = inspect(Modelo).primary_key[0].name
        pk_value = getattr(nuevo_registro, pk_name)

        # Actualizamos la geometría nativamente en PostGIS para asegurar conversión perfecta
        geom_str = json.dumps(geometria)
        stmt = text(f"UPDATE {Modelo.__tablename__} SET {geom_column_name} = ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326) WHERE {pk_name} = :id")
        db.execute(stmt, {"geom": geom_str, "id": pk_value})

        registros_insertados += 1

    db.commit()
    return {"status": "success", "mensaje": f"{registros_insertados} registros importados a la tabla {Modelo.__tablename__}."}

# ==================== BITÁCORA ==================== #
@app.get("/api/bitacora", tags=["Bitácora"], summary="Listar entradas de bitácora", response_model=List[schemas.BitacoraResponse])
def get_bitacora(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    return db.query(models.Bitacora).order_by(models.Bitacora.fecha_hora.desc()).offset(skip).limit(limit).all()

# ==================== ASIGNACIÓN USUARIO-TRAMO ==================== #
@app.post("/api/tramos/{id_tramo}/asignar-usuario", tags=["Tramos"], summary="Asignar usuario a tramo", response_model=schemas.UsuarioTramoResponse)
def asignar_usuario_tramo(id_tramo: int, data: schemas.UsuarioTramoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    get_entity_by_id(db, models.Tramo, id_tramo, "id_tramo")
    get_entity_by_id(db, models.Usuario, data.id_usuario, "id_usuario")
    set_audit_context(db, current_user.id_usuario)
    exists = db.query(models.UsuarioTramo).filter_by(id_tramo=id_tramo, id_usuario=data.id_usuario).first()
    if exists:
        if not exists.activo:
            if not data.motivo_reactivacion:
                raise HTTPException(
                    status_code=400,
                    detail="El motivo de reactivación es obligatorio para reactivar una asignación.",
                )
            exists.activo = True
            exists.fecha_asignacion = datetime.now(timezone.utc)
            exists.fecha_reactivacion = datetime.now(timezone.utc)
            exists.id_usuario_reactivacion = current_user.id_usuario
            exists.motivo_reactivacion = data.motivo_reactivacion.strip()
            db.commit()
            db.refresh(exists)
        return exists
    nuevo = models.UsuarioTramo(
        id_tramo=id_tramo,
        id_usuario=data.id_usuario,
        fecha_asignacion=datetime.now(timezone.utc)
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@app.delete("/api/tramos/{id_tramo}/remover-usuario/{id_usuario}", tags=["Tramos"], summary="Quitar a usuario de tramo")
def remover_usuario_tramo(
    id_tramo: int,
    id_usuario: int,
    motivo: str = Query(..., min_length=1, description="Motivo de la remoción"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))
):
    set_audit_context(db, current_user.id_usuario)
    exists = db.query(models.UsuarioTramo).filter_by(
        id_tramo=id_tramo,
        id_usuario=id_usuario,
        activo=True,
    ).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Asignación no encontrada.")
    exists.activo = False
    exists.fecha_baja = datetime.now(timezone.utc)
    exists.id_usuario_baja = current_user.id_usuario
    exists.motivo_baja = motivo
    db.commit()
    return {"status": "success", "detail": "Usuario removido del tramo."}

# ==================== GET BY ID (Líneas Individuales) ==================== #
@app.get("/api/tramos/{id_tramo}", tags=["Tramos"], summary="Obtener tramo por ID", response_model=schemas.TramoResponse)
def get_tramo_by_id(id_tramo: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    require_tramo_access(db, current_user, id_tramo)
    row = db.query(
        models.Tramo.id_tramo,
        models.Tramo.id_proyecto,
        models.Tramo.clave_tramo,
        models.Tramo.nombre_tramo,
        models.Tramo.descripcion,
        models.Tramo.ancho_total_derecho_via_m,
        models.Tramo.geometria_linea.ST_AsText().label('geometria_wkt'),
        models.Tramo.activo,
        models.Tramo.fecha_registro,
        models.Tramo.fecha_baja,
        models.Tramo.id_usuario_baja,
        models.Tramo.motivo_baja,
        models.Tramo.fecha_reactivacion,
        models.Tramo.id_usuario_reactivacion,
        models.Tramo.motivo_reactivacion,
        models.Tramo.observaciones
    ).filter(models.Tramo.id_tramo == id_tramo, models.Tramo.activo == True).first()
    if not row:
        raise HTTPException(status_code=404, detail="Tramo not found")
    return row

@app.get("/api/nucleos/{id_nucleo}", tags=["Núcleos Agrarios"], summary="Obtener núcleo agrario por ID", response_model=schemas.NucleoAgrarioResponse)
def get_nucleo_by_id(id_nucleo: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    require_nucleo_access(db, current_user, id_nucleo)
    row = db.query(
        models.NucleoAgrario.id_nucleo,
        models.NucleoAgrario.id_municipio,
        models.NucleoAgrario.nombre_nucleo,
        models.NucleoAgrario.tipo_nucleo,
        models.NucleoAgrario.comunidad_indigena,
        models.NucleoAgrario.residencia,
        models.NucleoAgrario.geometria_poligono.ST_AsText().label('geometria_wkt'),
        models.NucleoAgrario.fecha_creacion,
        models.NucleoAgrario.activo,
        models.NucleoAgrario.fecha_baja,
        models.NucleoAgrario.id_usuario_baja,
        models.NucleoAgrario.motivo_baja,
        models.NucleoAgrario.fecha_reactivacion,
        models.NucleoAgrario.id_usuario_reactivacion,
        models.NucleoAgrario.motivo_reactivacion,
        models.NucleoAgrario.observaciones
    ).filter(models.NucleoAgrario.id_nucleo == id_nucleo, models.NucleoAgrario.activo == True).first()
    if not row:
        raise HTTPException(status_code=404, detail="NucleoAgrario not found")
    return row

@app.get("/api/afectaciones/{id_afectacion}", tags=["Afectaciones"], summary="Obtener afectación por ID", response_model=schemas.AfectacionResponse)
def get_afectacion_by_id(id_afectacion: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    require_afectacion_access(db, current_user, id_afectacion)
    row = db.query(
        models.Afectacion.id_afectacion,
        models.Afectacion.id_nucleo,
        models.Afectacion.id_tramo_nucleo,
        models.Afectacion.id_parcela,
        models.Afectacion.tipo_afectacion,
        models.Afectacion.tipo_tenencia,
        models.Afectacion.subtipo_tenencia,
        models.Afectacion.destino_superficie,
        models.Afectacion.no_parcela_solar,
        models.Afectacion.superficie_afectada_ha,
        models.Afectacion.geometria_afectacion.ST_AsText().label('geometria_wkt'),
        models.Afectacion.num_personas_afectadas,
        models.Afectacion.situacion_juridica,
        models.Afectacion.documentacion_disponible,
        models.Afectacion.documentacion_faltante,
        models.Afectacion.origen_registro,
        models.Afectacion.activo,
        models.Afectacion.fecha_baja,
        models.Afectacion.id_usuario_baja,
        models.Afectacion.motivo_baja,
        models.Afectacion.fecha_reactivacion,
        models.Afectacion.id_usuario_reactivacion,
        models.Afectacion.motivo_reactivacion,
        models.Afectacion.tipo_salida_terminal,
        models.Afectacion.fecha_salida_terminal,
        models.Afectacion.motivo_salida_terminal,
        models.Afectacion.observaciones
    ).filter(models.Afectacion.id_afectacion == id_afectacion, models.Afectacion.activo == True).first()
    if not row:
        raise HTTPException(status_code=404, detail="Afectacion not found")
    return row

@app.get("/api/asambleas/{id_asamblea}", tags=["Asambleas"], summary="Obtener asamblea por ID", response_model=schemas.AsambleaResponse)
def get_asamblea_by_id(id_asamblea: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    entity = get_entity_by_id(db, models.Asamblea, id_asamblea, "id_asamblea")
    require_tramo_nucleo_access(db, current_user, entity.id_tramo_nucleo)
    return entity

@app.get("/api/convenios/{id_convenio}", tags=["Convenios"], summary="Obtener convenio por ID", response_model=schemas.ConvenioResponse)
def get_convenio_by_id(id_convenio: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    entity = get_entity_by_id(db, models.Convenio, id_convenio, "id_convenio")
    require_tramo_nucleo_access(db, current_user, entity.id_tramo_nucleo)
    return entity
