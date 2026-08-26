"""Staging, preview and explicit confirmation for all GIS targets."""

import json
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services import geospatial_imports as service
from ..services.access import require_project_access


router = APIRouter(tags=["Importaciones geoespaciales"])
READ_ROLES = ["admin", "operador", "visualizador", "geografo"]
GIS_ROLES = ["admin", "geografo"]


@router.get(
    "/proyectos/{id_proyecto}/importaciones",
    response_model=list[schemas.ImportacionArchivoResponse],
)
def list_imports(
    id_proyecto: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_project_access(db, user, id_proyecto)
    return db.query(models.ImportacionArchivo).filter(
        models.ImportacionArchivo.id_proyecto == id_proyecto,
        models.ImportacionArchivo.activo.is_(True),
    ).order_by(models.ImportacionArchivo.fecha_carga.desc()).offset(skip).limit(limit).all()


@router.post(
    "/proyectos/{id_proyecto}/importaciones",
    response_model=schemas.ImportacionArchivoResponse,
    status_code=201,
)
async def stage_import(
    id_proyecto: int,
    tipo_objetivo: str = Form(...),
    fuente: str = Form(...),
    fecha_fuente: date | None = Form(default=None),
    mapeo: str = Form(default="{}"),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(GIS_ROLES)),
):
    try:
        mapping = json.loads(mapeo)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="El mapeo no es JSON válido") from exc
    if not isinstance(mapping, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in mapping.items()
    ):
        raise HTTPException(status_code=422, detail="El mapeo debe ser objeto texto:texto")
    return await service.stage_import(
        db,
        id_proyecto,
        tipo_objetivo,
        fuente,
        fecha_fuente,
        mapping,
        archivo,
        user,
    )


@router.get(
    "/importaciones/{id_importacion}",
    response_model=schemas.ImportacionArchivoResponse,
)
def get_import(
    id_importacion: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return service.require_import_access(db, id_importacion, user)


@router.get(
    "/importaciones/{id_importacion}/features",
    response_model=list[schemas.ImportacionFeatureResponse],
)
def preview_features(
    id_importacion: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    service.require_import_access(db, id_importacion, user)
    return db.query(models.ImportacionFeature).filter(
        models.ImportacionFeature.id_importacion == id_importacion
    ).order_by(models.ImportacionFeature.indice_feature).offset(skip).limit(limit).all()


@router.post(
    "/importaciones/{id_importacion}/confirmar",
    response_model=schemas.ImportacionArchivoResponse,
)
def confirm_import(
    id_importacion: int,
    data: schemas.ImportacionConfirmarRequest,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(GIS_ROLES)),
):
    return service.confirm_import(db, id_importacion, data, user)
