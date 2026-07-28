from fastapi import FastAPI, Depends, HTTPException, status, Query, UploadFile, File
import os
import json
import shutil
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import InternalError, IntegrityError, DatabaseError
from typing import List, Type, Any
from datetime import datetime, timezone, timedelta
import pandas as pd
import io

from .database import engine, Base, get_db
from . import models, schemas
from fastapi.security import OAuth2PasswordRequestForm
from . import auth


app = FastAPI(
    title="API - Sistema de Seguimiento de Liberación de Derechos",
    description="Backend con lógica de negocio geoespacial y administrativa",
    version="1.3.1"
)


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
    raw_msg = str(exc.orig)
    clean_msg = sanitize_pg_error(raw_msg)
    return JSONResponse(status_code=400, content={"detail": clean_msg})

@app.exception_handler(IntegrityError)
def sqlalchemy_integrity_error_handler(request, exc: IntegrityError):
    raw_msg = str(exc.orig)
    clean_msg = sanitize_pg_error(raw_msg)
    return JSONResponse(status_code=422, content={"detail": f"Violación de regla de negocio: {clean_msg}"})

@app.exception_handler(Exception)
def global_exception_handler(request, exc: Exception):
    import traceback
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": str(exc)})

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


os.makedirs("uploads", exist_ok=True)

def validate_wkt(db: Session, wkt: str):
    if not wkt: return
    try:
        is_valid = db.execute(
            text("SELECT ST_IsValid(ST_GeomFromText(:wkt, 4326))"), 
            {"wkt": wkt}
        ).scalar()
        if is_valid is False:
            raise HTTPException(
                status_code=400, 
                detail="Geometría WKT inválida topológicamente (ej. cruces, puntos duplicados)."
            )
    except DatabaseError:
        raise HTTPException(
            status_code=400, 
            detail="Formato WKT inválido. Verifica la sintaxis de la geometría."
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

def update_entity(db: Session, entity: Any, update_data: Any, user_id: int):
    set_audit_context(db, user_id)
    update_dict = update_data.model_dump(exclude_unset=True)
    
    if "geometria_wkt" in update_dict:
        wkt = update_dict.pop("geometria_wkt", None)
        validate_wkt(db, wkt)
        
        model_class = type(entity)
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
    return db.query(models.Proyecto).filter(models.Proyecto.activo == True).offset(skip).limit(limit).all()

@app.get("/api/proyectos/{id_proyecto}", tags=["Proyectos"], summary="Obtener proyecto por ID", response_model=schemas.ProyectoResponse)
def get_proyecto_by_id(id_proyecto: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    entity = get_entity_by_id(db, models.Proyecto, id_proyecto, "id_proyecto")
    return entity

@app.post("/api/proyectos", tags=["Proyectos"], summary="Crear proyecto", response_model=schemas.ProyectoResponse, status_code=status.HTTP_201_CREATED)
def create_proyecto(proyecto: schemas.ProyectoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    db_proyecto = models.Proyecto(**proyecto.model_dump())
    db_proyecto.fecha_registro = datetime.now(timezone.utc).date()
    db.add(db_proyecto)
    db.commit()
    db.refresh(db_proyecto)
    return db_proyecto

@app.put("/api/proyectos/{id_proyecto}", tags=["Proyectos"], summary="Actualizar proyecto", response_model=schemas.ProyectoResponse)
def update_proyecto(id_proyecto: int, data: schemas.ProyectoUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Proyecto, id_proyecto, "id_proyecto")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/proyectos/{id_proyecto}", tags=["Proyectos"], summary="Eliminar proyecto")
def delete_proyecto(id_proyecto: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
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
    if id_proyecto is not None:
        query = query.filter(models.Tramo.id_proyecto == id_proyecto)
    return query.offset(skip).limit(limit).all()

@app.post("/api/tramos", tags=["Tramos"], summary="Crear tramo", response_model=schemas.TramoResponse, status_code=status.HTTP_201_CREATED)
def create_tramo(tramo: schemas.TramoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    # Validar que el proyecto exista
    get_entity_by_id(db, models.Proyecto, tramo.id_proyecto, "id_proyecto")
    set_audit_context(db, current_user.id_usuario)
    data = tramo.model_dump()
    wkt = data.pop("geometria_wkt", None)
    validate_wkt(db, wkt)
    db_tramo = models.Tramo(**data, geometria_linea=wkt)
    db_tramo.fecha_registro = datetime.now(timezone.utc).date()
    db.add(db_tramo)
    db.commit()
    db.refresh(db_tramo)
    resp = db_tramo.__dict__.copy()
    resp["geometria_wkt"] = db.scalar(
        db.query(models.Tramo.geometria_linea.ST_AsText()).filter(models.Tramo.id_tramo == db_tramo.id_tramo)
    )
    return resp

@app.put("/api/tramos/{id_tramo}", tags=["Tramos"], summary="Actualizar tramo", response_model=schemas.TramoResponse)
def update_tramo(id_tramo: int, data: schemas.TramoUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Tramo, id_tramo, "id_tramo")
    db_tramo = update_entity(db, entity, data, current_user.id_usuario)
    resp = db_tramo.__dict__.copy()
    resp["geometria_wkt"] = db.scalar(
        db.query(models.Tramo.geometria_linea.ST_AsText()).filter(models.Tramo.id_tramo == db_tramo.id_tramo)
    )
    return resp

@app.delete("/api/tramos/{id_tramo}", tags=["Tramos"], summary="Eliminar tramo")
def delete_tramo(id_tramo: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Tramo, id_tramo, "id_tramo")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)



# ==================== NUCLEOS AGRARIOS ==================== #
@app.get("/api/nucleos", tags=["Núcleos Agrarios"], summary="Listar núcleos agrarios")
def get_nucleos(id_tramo: int = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    from sqlalchemy import text
    
    base_sql = """
        SELECT 
            n.id_nucleo, 
            n.nombre_nucleo, 
            n.tipo_nucleo, 
            n.comunidad_indigena, 
            ST_AsText(n.geometria_poligono) as geometria_wkt,
            (ST_Area(n.geometria_poligono::geography) / 10000.0) as area_ha
        FROM nucleo_agrario n
        WHERE n.activo = true
    """
    params = {}
    
    if id_tramo is not None:
        base_sql += """
            AND ST_Intersects(n.geometria_poligono, (
                SELECT ST_Union(t.geometria_linea) 
                FROM tramo t 
                WHERE t.id_tramo = :id_tramo AND t.activo = TRUE
            ))
        """
        params["id_tramo"] = id_tramo
        
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
            "geometria_wkt": r.geometria_wkt,
            "area_ha": round(r.area_ha, 2) if r.area_ha else 0,
            "estatus_simulado": estatus
        })
        
    return response

@app.get("/api/tramo-detalles", tags=["Tramos"], summary="Obtener detalles y estadísticas geoespaciales de un tramo específico")
def get_tramo_detalles(id_tramo: int = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    from sqlalchemy import text
    from fastapi import HTTPException
    
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
def create_nucleo(nucleo: schemas.NucleoAgrarioCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    data = nucleo.model_dump()
    wkt = data.pop("geometria_wkt", None)
    validate_wkt(db, wkt)
    db_nucleo = models.NucleoAgrario(**data, geometria_poligono=wkt)
    db_nucleo.fecha_creacion = datetime.now(timezone.utc)
    db.add(db_nucleo)
    db.commit()
    db.refresh(db_nucleo)
    resp = db_nucleo.__dict__.copy()
    resp["geometria_wkt"] = db.scalar(
        db.query(models.NucleoAgrario.geometria_poligono.ST_AsText()).filter(models.NucleoAgrario.id_nucleo == db_nucleo.id_nucleo)
    )
    return resp

@app.put("/api/nucleos/{id_nucleo}", tags=["Núcleos Agrarios"], summary="Actualizar núcleo agrario", response_model=schemas.NucleoAgrarioResponse)
def update_nucleo(id_nucleo: int, data: schemas.NucleoAgrarioUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.NucleoAgrario, id_nucleo, "id_nucleo")
    db_nucleo = update_entity(db, entity, data, current_user.id_usuario)
    resp = db_nucleo.__dict__.copy()
    resp["geometria_wkt"] = db.scalar(
        db.query(models.NucleoAgrario.geometria_poligono.ST_AsText()).filter(models.NucleoAgrario.id_nucleo == db_nucleo.id_nucleo)
    )
    return resp

@app.delete("/api/nucleos/{id_nucleo}", tags=["Núcleos Agrarios"], summary="Eliminar núcleo agrario")
def delete_nucleo(id_nucleo: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.NucleoAgrario, id_nucleo, "id_nucleo")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

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
        models.TramoNucleo.consecutivo,
        models.TramoNucleo.numero_tramo,
        models.TramoNucleo.geometria_segmento.ST_AsText().label('geometria_wkt'),
        models.TramoNucleo.longitud_m,
        models.TramoNucleo.es_expropiacion,
        models.TramoNucleo.causa_problema,
        models.TramoNucleo.proyecto_no_afecta_uso_comun,
        models.TramoNucleo.activo,
        models.TramoNucleo.observaciones,
    ).filter(models.TramoNucleo.activo == True)
    if id_tramo:
        query = query.filter(models.TramoNucleo.id_tramo == id_tramo)
    if id_nucleo:
        query = query.filter(models.TramoNucleo.id_nucleo == id_nucleo)
    return query.all()

@app.get("/api/tramos-nucleos/{id_tramo_nucleo}", tags=["Tramos-Nucleos"], summary="Obtener tramo-nucleo", response_model=schemas.TramoNucleoResponse)
def get_tramo_nucleo(id_tramo_nucleo: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    row = db.query(
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
        models.TramoNucleo.activo == True
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="TramoNucleo not found")
    return row

@app.post("/api/tramos-nucleos", tags=["Tramos-Nucleos"], summary="Crear tramo-nucleo", response_model=schemas.TramoNucleoResponse, status_code=status.HTTP_201_CREATED)
def create_tramo_nucleo(tramo_nucleo: schemas.TramoNucleoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    data = tramo_nucleo.model_dump()
    wkt = data.pop("geometria_wkt", None)
    if wkt:
        validate_wkt(db, wkt)
    db_tn = models.TramoNucleo(**data)
    if wkt:
        db_tn.geometria_segmento = wkt
    db.add(db_tn)
    db.commit()
    db.refresh(db_tn)
    resp = db_tn.__dict__.copy()
    resp["geometria_wkt"] = db.scalar(
        db.query(models.TramoNucleo.geometria_segmento.ST_AsText()).filter(models.TramoNucleo.id_tramo_nucleo == db_tn.id_tramo_nucleo)
    )
    return resp

@app.put("/api/tramos-nucleos/{id_tramo_nucleo}", tags=["Tramos-Nucleos"], summary="Actualizar tramo-nucleo", response_model=schemas.TramoNucleoResponse)
def update_tramo_nucleo(id_tramo_nucleo: int, data: schemas.TramoNucleoUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.TramoNucleo, id_tramo_nucleo, "id_tramo_nucleo")
    updated = update_entity(db, entity, data, current_user.id_usuario)
    resp = updated.__dict__.copy()
    resp["geometria_wkt"] = db.scalar(
        db.query(models.TramoNucleo.geometria_segmento.ST_AsText()).filter(models.TramoNucleo.id_tramo_nucleo == updated.id_tramo_nucleo)
    )
    return resp

@app.delete("/api/tramos-nucleos/{id_tramo_nucleo}", tags=["Tramos-Nucleos"], summary="Eliminar tramo-nucleo")
def delete_tramo_nucleo(id_tramo_nucleo: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.TramoNucleo, id_tramo_nucleo, "id_tramo_nucleo")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== PARCELAS ==================== #
@app.get("/api/parcelas", tags=["Parcelas"], summary="Listar parcelas", response_model=List[schemas.ParcelaResponse])
def list_parcelas(
    id_nucleo: int = Query(None),
    tipo_parcela: str = Query(None),
    db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))
):
    query = db.query(models.Parcela).filter(models.Parcela.activo == True)
    if id_nucleo:
        query = query.filter(models.Parcela.id_nucleo == id_nucleo)
    if tipo_parcela:
        query = query.filter(models.Parcela.tipo_parcela == tipo_parcela)
    return query.all()

@app.get("/api/parcelas/{id_parcela}", tags=["Parcelas"], summary="Obtener parcela", response_model=schemas.ParcelaResponse)
def get_parcela(id_parcela: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    return get_entity_by_id(db, models.Parcela, id_parcela, "id_parcela")

@app.post("/api/parcelas", tags=["Parcelas"], summary="Crear parcela", response_model=schemas.ParcelaResponse, status_code=status.HTTP_201_CREATED)
def create_parcela(parcela: schemas.ParcelaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    db_parcela = models.Parcela(**parcela.model_dump())
    db.add(db_parcela)
    db.commit()
    db.refresh(db_parcela)
    return db_parcela

@app.put("/api/parcelas/{id_parcela}", tags=["Parcelas"], summary="Actualizar parcela", response_model=schemas.ParcelaResponse)
def update_parcela(id_parcela: int, data: schemas.ParcelaUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Parcela, id_parcela, "id_parcela")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/parcelas/{id_parcela}", tags=["Parcelas"], summary="Eliminar parcela")
def delete_parcela(id_parcela: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Parcela, id_parcela, "id_parcela")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== DASHBOARD & REPORTES ==================== #
@app.get("/api/dashboard", tags=["Dashboard"], summary="Consultar convenios y superficie", response_model=List[schemas.DashboardMetrics])
def get_dashboard_metrics(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = text("SELECT * FROM vw_dashboard_liberacion LIMIT 100;")
    return db.execute(query).mappings().all()

@app.get("/api/reportes/resumen", tags=["Reportes"], summary="Generar reporte resumen")
def generar_reporte_resumen(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    return {
        "generado_el": datetime.now(timezone.utc),
        "total_convenios": db.query(models.Convenio).filter(models.Convenio.activo == True).count(),
        "total_nucleos": db.query(models.NucleoAgrario).filter(models.NucleoAgrario.activo == True).count(),
        "total_afectaciones": db.query(models.Afectacion).filter(models.Afectacion.activo == True).count()
    }

# ==================== AFECTACIONES ==================== #
@app.get("/api/afectaciones", tags=["Afectaciones"], summary="Listar afectaciones", response_model=List[schemas.AfectacionResponse])
def list_afectaciones(skip: int = 0, limit: int = 100, id_tramo_nucleo: int = Query(None), tipo_afectacion: str = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(
        models.Afectacion,
        models.Afectacion.geometria_afectacion.ST_AsText().label('geometria_wkt')
    ).filter(models.Afectacion.activo == True)
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

@app.post("/api/afectaciones", tags=["Afectaciones"], summary="Crear afectación", response_model=schemas.AfectacionResponse, status_code=status.HTTP_201_CREATED)
def create_afectacion(afectacion: schemas.AfectacionCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    
    # Validación de integridad: TramoNucleo debe existir y pertenecer al NucleoAgrario indicado
    tramo_nucleo_db = db.query(models.TramoNucleo).filter(
        models.TramoNucleo.id_tramo_nucleo == afectacion.id_tramo_nucleo,
        models.TramoNucleo.activo == True
    ).first()
    if not tramo_nucleo_db:
        raise HTTPException(status_code=404, detail="El TramoNucleo especificado no existe.")
    if tramo_nucleo_db.id_nucleo != afectacion.id_nucleo:
        raise HTTPException(status_code=400, detail="Inconsistencia: El TramoNucleo no pertenece al NucleoAgrario especificado.")
    
    # Validación: Individual requiere parcela y la parcela debe pertenecer al mismo núcleo
    if afectacion.tipo_afectacion == 'individual':
        if not afectacion.id_parcela:
            raise HTTPException(status_code=400, detail="Una afectación individual requiere id_parcela")
        parcela_db = db.query(models.Parcela).filter(
            models.Parcela.id_parcela == afectacion.id_parcela,
            models.Parcela.activo == True
        ).first()
        if not parcela_db:
            raise HTTPException(status_code=404, detail="La Parcela especificada no existe.")
        if parcela_db.id_nucleo != afectacion.id_nucleo:
            raise HTTPException(status_code=400, detail="Inconsistencia: La Parcela no pertenece al NucleoAgrario especificado.")
        
    data = afectacion.model_dump()
    wkt = data.pop("geometria_wkt", None)
    
    if wkt:
        validate_wkt(db, wkt)
        
    db_afectacion = models.Afectacion(**data)
    if wkt:
        db_afectacion.geometria_afectacion = wkt
        
    db.add(db_afectacion)
    db.commit()
    db.refresh(db_afectacion)
    resp = db_afectacion.__dict__.copy()
    resp["geometria_wkt"] = db.scalar(
        db.query(models.Afectacion.geometria_afectacion.ST_AsText()).filter(models.Afectacion.id_afectacion == db_afectacion.id_afectacion)
    )
    return resp

@app.put("/api/afectaciones/{id_afectacion}", tags=["Afectaciones"], summary="Actualizar afectación", response_model=schemas.AfectacionResponse)
def update_afectacion_route(id_afectacion: int, data: schemas.AfectacionUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Afectacion, id_afectacion, "id_afectacion")
    db_afectacion = update_entity(db, entity, data, current_user.id_usuario)
    resp = db_afectacion.__dict__.copy()
    resp["geometria_wkt"] = db.scalar(
        db.query(models.Afectacion.geometria_afectacion.ST_AsText()).filter(models.Afectacion.id_afectacion == db_afectacion.id_afectacion)
    )
    return resp

@app.delete("/api/afectaciones/{id_afectacion}", tags=["Afectaciones"], summary="Eliminar afectación")
def delete_afectacion(id_afectacion: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Afectacion, id_afectacion, "id_afectacion")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== ASAMBLEAS ==================== #
@app.get("/api/asambleas", tags=["Asambleas"], summary="Listar asambleas", response_model=List[schemas.AsambleaResponse])
def list_asambleas(id_tramo_nucleo: int = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.Asamblea).filter(models.Asamblea.activo == True)
    if id_tramo_nucleo:
        query = query.filter(models.Asamblea.id_tramo_nucleo == id_tramo_nucleo)
    return query.all()

@app.post("/api/asambleas", tags=["Asambleas"], summary="Crear asamblea", response_model=schemas.AsambleaResponse, status_code=status.HTTP_201_CREATED)
def create_asamblea(asamblea: schemas.AsambleaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    
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
    
    db_asamblea = models.Asamblea(**asamblea.model_dump())
    db_asamblea.id_usuario_registro = current_user.id_usuario
    db.add(db_asamblea)
    db.commit()
    db.refresh(db_asamblea)
    return db_asamblea

@app.put("/api/asambleas/{id_asamblea}", tags=["Asambleas"], summary="Actualizar asamblea", response_model=schemas.AsambleaResponse)
def update_asamblea_route(id_asamblea: int, data: schemas.AsambleaUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Asamblea, id_asamblea, "id_asamblea")
    if data.id_padron is not None:
        padron_db = db.query(models.PadronHistorial).filter_by(id_padron=data.id_padron, activo=True).first()
        if not padron_db or padron_db.id_nucleo != entity.id_nucleo:
            raise HTTPException(status_code=400, detail="Inconsistencia: El Padrón no existe o no pertenece al NucleoAgrario de la asamblea.")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/asambleas/{id_asamblea}", tags=["Asambleas"], summary="Eliminar asamblea")
def delete_asamblea(id_asamblea: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Asamblea, id_asamblea, "id_asamblea")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== CONVENIOS ==================== #
@app.get("/api/convenios", tags=["Convenios"], summary="Listar convenios", response_model=List[schemas.ConvenioResponse])
def list_convenios(
    id_tramo_nucleo: int = Query(None),
    tipo_convenio: str = Query(None),
    inscrito: bool = Query(None),
    db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))
):
    query = db.query(models.Convenio).filter(models.Convenio.activo == True)
    if id_tramo_nucleo:
        query = query.filter(models.Convenio.id_tramo_nucleo == id_tramo_nucleo)
    if tipo_convenio:
        query = query.filter(models.Convenio.tipo_convenio == tipo_convenio)
    if inscrito is True:
        query = query.filter(models.Convenio.convenio_inscrito_fecha_ran != None)
    return query.all()

@app.post("/api/convenios", tags=["Convenios"], summary="Crear convenio", response_model=schemas.ConvenioResponse, status_code=status.HTTP_201_CREATED)
def create_convenio(convenio: schemas.ConvenioCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    
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
        
    if convenio.id_convenio_padre:
        padre_db = db.query(models.Convenio).filter_by(id_convenio=convenio.id_convenio_padre, activo=True).first()
        if not padre_db or padre_db.id_afectacion != convenio.id_afectacion:
            raise HTTPException(status_code=400, detail="Inconsistencia: El Convenio Padre no existe o no pertenece a la misma Afectación.")
            
    if convenio.id_asamblea_autorizacion:
        asamblea_db = db.query(models.Asamblea).filter_by(id_asamblea=convenio.id_asamblea_autorizacion, activo=True).first()
        if not asamblea_db or asamblea_db.id_tramo_nucleo != convenio.id_tramo_nucleo:
            raise HTTPException(status_code=400, detail="Inconsistencia: La Asamblea no existe o no pertenece al mismo TramoNucleo.")
    
    # B6 / B7: Asamblea constraint
    if convenio.tipo_afectacion == 'colectivo' and not convenio.id_asamblea_autorizacion:
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

    db_convenio = models.Convenio(**convenio.model_dump())
    db_convenio.id_usuario_registro = current_user.id_usuario
    db.add(db_convenio)
    db.commit()
    db.refresh(db_convenio)
    return db_convenio

@app.put("/api/convenios/{id_convenio}", tags=["Convenios"], summary="Actualizar convenio", response_model=schemas.ConvenioResponse)
def update_convenio_route(id_convenio: int, data: schemas.ConvenioUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Convenio, id_convenio, "id_convenio")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/convenios/{id_convenio}", tags=["Convenios"], summary="Eliminar convenio")
def delete_convenio(id_convenio: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Convenio, id_convenio, "id_convenio")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== ORV ==================== #
@app.get("/api/orvs", tags=["ORVs"], summary="Listar ORVs", response_model=List[schemas.OrvResponse])
def list_orvs(id_nucleo: int = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.Orv).filter(models.Orv.activo == True)
    if id_nucleo:
        query = query.filter(models.Orv.id_nucleo == id_nucleo)
    return query.all()

@app.post("/api/orvs", tags=["ORVs"], summary="Crear ORV", response_model=schemas.OrvResponse, status_code=status.HTTP_201_CREATED)
def create_orv(orv: schemas.OrvCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    db_orv = models.Orv(**orv.model_dump())
    db.add(db_orv)
    db.commit()
    db.refresh(db_orv)
    return db_orv

@app.put("/api/orvs/{id_orv}", tags=["ORVs"], summary="Actualizar ORV", response_model=schemas.OrvResponse)
def update_orv_route(id_orv: int, data: schemas.OrvUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Orv, id_orv, "id_orv")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/orvs/{id_orv}", tags=["ORVs"], summary="Eliminar ORV")
def delete_orv(id_orv: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Orv, id_orv, "id_orv")
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
def list_actividades(id_tramo_nucleo: int = Query(None), tipo_actividad: str = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.ActividadCampo).filter(models.ActividadCampo.activo == True)
    if id_tramo_nucleo:
        query = query.filter(models.ActividadCampo.id_tramo_nucleo == id_tramo_nucleo)
    if tipo_actividad:
        query = query.filter(models.ActividadCampo.tipo_actividad == tipo_actividad)
    return query.all()

@app.post("/api/actividades-campo", tags=["Actividades de Campo"], summary="Crear actividad de campo", response_model=schemas.ActividadCampoResponse, status_code=status.HTTP_201_CREATED)
def create_actividad(act: schemas.ActividadCampoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    
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
def update_actividad_route(id_actividad: int, data: schemas.ActividadCampoUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.ActividadCampo, id_actividad, "id_actividad")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/actividades-campo/{id_actividad}", tags=["Actividades de Campo"], summary="Eliminar actividad de campo")
def delete_actividad(id_actividad: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.ActividadCampo, id_actividad, "id_actividad")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== TRAMITE FIFONAFE ==================== #
@app.get("/api/fifonafe", tags=["Fifonafe"], summary="Listar trámites fifonafe", response_model=List[schemas.TramiteFifonafeResponse])
def list_fifonafe(id_tramo_nucleo: int = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.TramiteFifonafe).filter(models.TramiteFifonafe.activo == True)
    if id_tramo_nucleo:
        query = query.filter(models.TramiteFifonafe.id_tramo_nucleo == id_tramo_nucleo)
    return query.all()

@app.post("/api/fifonafe", tags=["Fifonafe"], summary="Crear trámite fifonafe", response_model=schemas.TramiteFifonafeResponse, status_code=status.HTTP_201_CREATED)
def create_fifonafe(tramite: schemas.TramiteFifonafeCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    
    # Validaciones de coherencia jerárquica
    tn_db = db.query(models.TramoNucleo).filter_by(id_tramo_nucleo=tramite.id_tramo_nucleo, activo=True).first()
    if not tn_db:
        raise HTTPException(status_code=404, detail="El TramoNucleo no existe.")
        
    if tramite.id_afectacion:
        afectacion_db = db.query(models.Afectacion).filter_by(id_afectacion=tramite.id_afectacion, activo=True).first()
        if not afectacion_db or afectacion_db.id_tramo_nucleo != tramite.id_tramo_nucleo:
            raise HTTPException(status_code=400, detail="Inconsistencia: La Afectación no existe o no pertenece al TramoNucleo especificado.")
            
    if tramite.id_convenio:
        convenio_db = db.query(models.Convenio).filter_by(id_convenio=tramite.id_convenio, activo=True).first()
        if not convenio_db or convenio_db.id_tramo_nucleo != tramite.id_tramo_nucleo:
            raise HTTPException(status_code=400, detail="Inconsistencia: El Convenio no existe o no pertenece al TramoNucleo especificado.")
            
    db_tram = models.TramiteFifonafe(**tramite.model_dump())
    db.add(db_tram)
    db.commit()
    db.refresh(db_tram)
    return db_tram

@app.put("/api/fifonafe/{id_tramite}", tags=["Fifonafe"], summary="Actualizar trámite fifonafe", response_model=schemas.TramiteFifonafeResponse)
def update_fifonafe_route(id_tramite: int, data: schemas.TramiteFifonafeUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.TramiteFifonafe, id_tramite, "id_tramite_fifonafe")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/fifonafe/{id_tramite}", tags=["Fifonafe"], summary="Eliminar trámite fifonafe")
def delete_fifonafe(id_tramite: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.TramiteFifonafe, id_tramite, "id_tramite_fifonafe")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== DOCUMENTACION ==================== #
@app.get("/api/documentacion", tags=["Documentación"], summary="Listar documentación de soporte", response_model=List[schemas.DocumentacionSoporteResponse])
def list_documentacion(entidad_tipo: str = Query(None), entidad_id: int = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.DocumentacionSoporte).filter(models.DocumentacionSoporte.activo == True)
    if entidad_tipo:
        query = query.filter(models.DocumentacionSoporte.entidad_relacionada_tipo == entidad_tipo)
    if entidad_id:
        query = query.filter(models.DocumentacionSoporte.entidad_relacionada_id == entidad_id)
    return query.all()

@app.post("/api/documentacion", tags=["Documentación"], summary="Crear documentación de soporte", response_model=schemas.DocumentacionSoporteResponse, status_code=status.HTTP_201_CREATED)
def create_documentacion(doc: schemas.DocumentacionSoporteCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    db_doc = models.DocumentacionSoporte(**doc.model_dump())
    db_doc.fecha_carga = datetime.now(timezone.utc)
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

@app.put("/api/documentacion/{id_documento}", tags=["Documentación"], summary="Actualizar documentación de soporte", response_model=schemas.DocumentacionSoporteResponse)
def update_documentacion_route(id_documento: int, data: schemas.DocumentacionSoporteUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.DocumentacionSoporte, id_documento, "id_documento")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/documentacion/{id_documento}", tags=["Documentación"], summary="Eliminar documentación de soporte")
def delete_documentacion(id_documento: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.DocumentacionSoporte, id_documento, "id_documento")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

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

# ==================== AUTH ==================== #
@app.post("/api/auth/login", tags=["Autenticación"], summary="Iniciar sesión", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.correo == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.contrasena_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.activo:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.correo, "rol": user.rol}, expires_delta=access_token_expires
    )
    # Return user data explicitly for the frontend AuthContext
    user_data = {
        "id_usuario": user.id_usuario,
        "nombre": user.nombre,
        "apellido_paterno": user.apellido_paterno,
        "correo": user.correo,
        "rol": user.rol
    }
    return {"access_token": access_token, "token_type": "bearer", "user": user_data}

# ==================== USUARIOS ==================== #
@app.post("/api/usuarios", tags=["Usuarios"], summary="Crear usuario", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def create_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    set_audit_context(db, current_user.id_usuario)
    db_user = db.query(models.Usuario).filter(models.Usuario.correo == usuario.correo).first()
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
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/usuarios/{id_usuario}", tags=["Usuarios"], summary="Eliminar usuario")
def delete_usuario(id_usuario: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    entity = get_entity_by_id(db, models.Usuario, id_usuario, "id_usuario")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

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

@app.post("/api/documentacion/{id_documento}/archivo", tags=["Documentación"], summary="Subir archivo")
def upload_archivo(id_documento: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    doc = get_entity_by_id(db, models.DocumentacionSoporte, id_documento, "id_documento")
    
    EXTENSIONES_PERMITIDAS = {".pdf", ".jpg", ".jpeg", ".png", ".docx"}
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Solo se aceptan: {', '.join(sorted(EXTENSIONES_PERMITIDAS))}"
        )
    
    safe_filename = f"doc_{id_documento}{file_extension}"
    file_path = os.path.join("uploads", safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    set_audit_context(db, current_user.id_usuario)
    doc.url_archivo = file_path
    db.commit()
    return {"status": "success", "url": file_path}

@app.get("/api/documentacion/{id_documento}/archivo", tags=["Documentación"], summary="Descargar archivo")
def download_archivo(id_documento: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    doc = get_entity_by_id(db, models.DocumentacionSoporte, id_documento, "id_documento")
    if not doc.url_archivo or not os.path.exists(doc.url_archivo):
        raise HTTPException(status_code=404, detail="Archivo físico no encontrado.")
    return FileResponse(doc.url_archivo, filename=os.path.basename(doc.url_archivo))

# ==================== GEOJSON IMPORTER ==================== #
@app.post("/api/geometria/importar-geojson", tags=["Geometría"], summary="Importar GeoJSON")
def importar_geojson(
    tipo_entidad: str = Query(..., description="Opciones: tramo, nucleo_agrario, tramo_nucleo, afectacion"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'geografo']))
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
                datos_limpios["fecha_creacion"] = datetime.now()

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

# ==================== ALERTAS VISTAS ==================== #
@app.post("/api/alertas/{id_alerta}/marcar-leida", tags=["Alertas"], summary="Marcar alerta como leída")
def marcar_alerta_leida(id_alerta: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    alerta = get_entity_by_id(db, models.Alertas, id_alerta, "id_alerta")
    vista = db.query(models.AlertasVistas).filter_by(id_alerta=id_alerta, id_usuario=current_user.id_usuario).first()
    if not vista:
        nueva_vista = models.AlertasVistas(
            id_alerta=id_alerta, 
            id_usuario=current_user.id_usuario,
            fecha_vista=datetime.now(timezone.utc)
        )
        db.add(nueva_vista)
        db.commit()
    return {"status": "success", "detail": "Alerta marcada como leída."}

# ==================== GET BY ID (Líneas Individuales) ==================== #
@app.get("/api/tramos/{id_tramo}", tags=["Tramos"], summary="Obtener tramo por ID", response_model=schemas.TramoResponse)
def get_tramo_by_id(id_tramo: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
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
        models.Afectacion.observaciones
    ).filter(models.Afectacion.id_afectacion == id_afectacion, models.Afectacion.activo == True).first()
    if not row:
        raise HTTPException(status_code=404, detail="Afectacion not found")
    return row

@app.get("/api/asambleas/{id_asamblea}", tags=["Asambleas"], summary="Obtener asamblea por ID", response_model=schemas.AsambleaResponse)
def get_asamblea_by_id(id_asamblea: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    return get_entity_by_id(db, models.Asamblea, id_asamblea, "id_asamblea")

@app.get("/api/convenios/{id_convenio}", tags=["Convenios"], summary="Obtener convenio por ID", response_model=schemas.ConvenioResponse)
def get_convenio_by_id(id_convenio: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    return get_entity_by_id(db, models.Convenio, id_convenio, "id_convenio")
