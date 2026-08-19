from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db
from ..services import franjas as franjas_service
from ..services.access import filter_projects_by_user, require_project_access, require_tramo_access

router = APIRouter(tags=["Franjas de Derecho de Vía"])

@router.get(
    "/proyectos/{id_proyecto}/franjas",
    summary="Listar historial del trazo oficial de un proyecto",
    response_model=List[schemas.FranjaDerechoViaResponse]
)
def list_franjas(
    id_proyecto: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))
):
    require_project_access(db, current_user, id_proyecto)
    return db.query(
        models.FranjaDerechoVia.id_franja,
        models.FranjaDerechoVia.id_proyecto,
        models.FranjaDerechoVia.version,
        models.FranjaDerechoVia.fecha_vigencia_inicio,
        models.FranjaDerechoVia.fecha_vigencia_fin,
        models.FranjaDerechoVia.activo,
        func.ST_AsText(func.coalesce(
            models.FranjaDerechoVia.geometria_linea,
            models.FranjaDerechoVia.geometria_poligono,
        )).label("geometria_wkt"),
    ).filter(
        models.FranjaDerechoVia.id_proyecto == id_proyecto
    ).order_by(models.FranjaDerechoVia.version.desc()).all()


@router.get(
    "/franjas/activas",
    summary="Listar franjas activas accesibles",
    response_model=List[schemas.FranjaDerechoViaResponse],
)
def list_franjas_activas(
    id_proyecto: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(
        auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo'])
    ),
):
    if id_proyecto is not None:
        require_project_access(db, current_user, id_proyecto)

    query = db.query(
        models.FranjaDerechoVia.id_franja,
        models.FranjaDerechoVia.id_proyecto,
        models.FranjaDerechoVia.version,
        models.FranjaDerechoVia.fecha_vigencia_inicio,
        models.FranjaDerechoVia.fecha_vigencia_fin,
        models.FranjaDerechoVia.activo,
        func.ST_AsText(func.coalesce(
            models.FranjaDerechoVia.geometria_linea,
            models.FranjaDerechoVia.geometria_poligono,
        )).label("geometria_wkt"),
    ).join(
        models.Proyecto,
        models.Proyecto.id_proyecto == models.FranjaDerechoVia.id_proyecto,
    ).filter(
        models.FranjaDerechoVia.activo.is_(True),
        models.Proyecto.activo.is_(True),
    )
    if id_proyecto is not None:
        query = query.filter(models.FranjaDerechoVia.id_proyecto == id_proyecto)
    query = filter_projects_by_user(query, db, current_user)
    return query.order_by(models.FranjaDerechoVia.id_proyecto).distinct().all()


@router.post(
    "/proyectos/{id_proyecto}/franjas/importar",
    summary="Importar nueva versión del trazo oficial",
    response_model=schemas.FranjaDerechoViaResponse,
    status_code=status.HTTP_201_CREATED
)
def importar_franja(
    id_proyecto: int,
    data: schemas.FranjaDerechoViaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'geografo']))
):
    require_project_access(db, current_user, id_proyecto)
    return franjas_service.importar_franja(db, id_proyecto, data, current_user.id_usuario)


@router.get("/tramos/{id_tramo}/secciones-derecho-via", response_model=List[schemas.SeccionDerechoViaResponse])
def list_secciones(id_tramo: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    require_tramo_access(db, current_user, id_tramo)
    return db.query(
        models.SeccionDerechoVia.id_seccion,
        models.SeccionDerechoVia.id_franja,
        models.SeccionDerechoVia.id_tramo,
        models.SeccionDerechoVia.fuente,
        models.SeccionDerechoVia.activo,
        func.ST_AsText(models.SeccionDerechoVia.geometria_poligono).label("geometria_wkt"),
    ).filter(models.SeccionDerechoVia.id_tramo == id_tramo).order_by(models.SeccionDerechoVia.id_seccion.desc()).all()


@router.post("/tramos/{id_tramo}/secciones-derecho-via/importar", response_model=schemas.SeccionDerechoViaResponse, status_code=status.HTTP_201_CREATED)
def importar_seccion(id_tramo: int, data: schemas.SeccionDerechoViaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'geografo']))):
    require_tramo_access(db, current_user, id_tramo)
    return franjas_service.importar_seccion(db, id_tramo, data, current_user.id_usuario)


# Compatibilidad temporal: resuelve el proyecto del tramo, sin volver a hacer
# de la franja una hija espacial del tramo.
@router.post("/tramos/{id_tramo}/franjas/importar", response_model=schemas.FranjaDerechoViaResponse, status_code=status.HTTP_201_CREATED, deprecated=True)
def importar_franja_legacy(id_tramo: int, data: schemas.FranjaDerechoViaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'geografo']))):
    require_tramo_access(db, current_user, id_tramo)
    tramo = db.query(models.Tramo).filter(
        models.Tramo.id_tramo == id_tramo,
        models.Tramo.activo.is_(True),
    ).one_or_none()
    if tramo is None:
        raise HTTPException(status_code=404, detail="Tramo no encontrado")
    return franjas_service.importar_franja(db, tramo.id_proyecto, data, current_user.id_usuario)


@router.get("/tramos/{id_tramo}/franjas", response_model=List[schemas.FranjaDerechoViaResponse], deprecated=True)
def list_franjas_legacy(id_tramo: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    require_tramo_access(db, current_user, id_tramo)
    tramo = db.query(models.Tramo).filter(
        models.Tramo.id_tramo == id_tramo,
        models.Tramo.activo.is_(True),
    ).one_or_none()
    if tramo is None:
        raise HTTPException(status_code=404, detail="Tramo no encontrado")
    return list_franjas(tramo.id_proyecto, db, current_user)
