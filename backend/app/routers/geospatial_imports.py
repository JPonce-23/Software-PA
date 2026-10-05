"""Staging, preview and explicit confirmation for all GIS targets."""

import json
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services import geospatial_imports as service
from ..services import gis_reconciliation as reconciliation
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
    "/proyectos/{id_proyecto}/geoespacial/ddv/importaciones",
    response_model=schemas.ImportacionArchivoResponse,
    status_code=201,
)
async def stage_ddv_import(
    id_proyecto: int,
    request: Request,
    fuente: str = Form(...),
    fecha_fuente: date | None = Form(default=None),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(GIS_ROLES)),
):
    fields = [key for key, _ in (await request.form()).multi_items()]
    if sorted(fields) != sorted(set(fields)) or set(fields) - {
        "fuente", "fecha_fuente", "archivo"
    }:
        raise HTTPException(
            status_code=422,
            detail="El DDV solo admite archivo, fuente y fecha_fuente",
        )
    return await service.stage_ddv_import(
        db, id_proyecto, fuente, fecha_fuente, archivo, user
    )


@router.post(
    "/proyectos/{id_proyecto}/geoespacial/nucleos/importaciones",
    response_model=schemas.ImportacionArchivoResponse,
    status_code=201,
)
async def stage_nucleus_import(
    id_proyecto: int,
    request: Request,
    fuente: str = Form(...),
    fecha_fuente: date | None = Form(default=None),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(GIS_ROLES)),
):
    fields = [key for key, _ in (await request.form()).multi_items()]
    if sorted(fields) != sorted(set(fields)) or set(fields) - {
        "fuente", "fecha_fuente", "archivo"
    }:
        raise HTTPException(
            status_code=422,
            detail="Los núcleos solo admiten archivo, fuente y fecha_fuente",
        )
    return await service.stage_nucleus_import(
        db, id_proyecto, fuente, fecha_fuente, archivo, user
    )


@router.post(
    "/proyectos/{id_proyecto}/geoespacial/parcelas/importaciones",
    response_model=schemas.ImportacionArchivoResponse,
    status_code=201,
)
async def stage_parcel_import(
    id_proyecto: int,
    request: Request,
    fuente: str = Form(...),
    fecha_fuente: date | None = Form(default=None),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(GIS_ROLES)),
):
    fields = [key for key, _ in (await request.form()).multi_items()]
    if sorted(fields) != sorted(set(fields)) or set(fields) - {
        "fuente", "fecha_fuente", "archivo"
    }:
        raise HTTPException(
            status_code=422,
            detail="Las parcelas solo admiten archivo, fuente y fecha_fuente",
        )
    return await service.stage_parcel_import(
        db, id_proyecto, fuente, fecha_fuente, archivo, user
    )


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
    estado_conciliacion: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    service.require_import_access(db, id_importacion, user)
    query = db.query(models.ImportacionFeature).filter(
        models.ImportacionFeature.id_importacion == id_importacion
    )
    if estado_conciliacion is not None:
        query = query.filter(models.ImportacionFeature.estado_conciliacion == estado_conciliacion)
    return query.order_by(models.ImportacionFeature.indice_feature).offset(skip).limit(limit).all()


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


@router.get("/proyectos/{id_proyecto}/geoespacial/configuracion", response_model=schemas.ConfiguracionGisResponse)
def get_gis_configuration(id_proyecto: int, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    require_project_access(db,user,id_proyecto)
    return {"id_proyecto":id_proyecto,"srid_trabajo":reconciliation.working_srid(db,id_proyecto)}


@router.put("/proyectos/{id_proyecto}/geoespacial/configuracion", response_model=schemas.ConfiguracionGisResponse)
def configure_gis(id_proyecto: int, data: schemas.ConfiguracionGisRequest, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(GIS_ROLES))):
    return reconciliation.configure_project(db,id_proyecto,data.srid_trabajo,user)


@router.get("/importaciones/{id_importacion}/resumen")
def get_reconciliation_summary(id_importacion: int, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    record=service.require_import_access(db,id_importacion,user)
    if record.tipo_objetivo not in reconciliation.RECONCILIATION_TARGETS:
        return record.reporte
    return reconciliation.reconciliation_summary(db,record)


@router.get("/importaciones/{id_importacion}/features/{id_feature}/candidatos", response_model=list[schemas.CandidatoGisResponse])
def get_feature_candidates(id_importacion: int, id_feature: int, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    service.require_import_access(db,id_importacion,user)
    return db.query(models.ImportacionFeatureCandidato).filter_by(id_importacion=id_importacion,id_importacion_feature=id_feature).order_by(models.ImportacionFeatureCandidato.id_candidato).all()


@router.post("/importaciones/{id_importacion}/features/{id_feature}/decisiones", response_model=schemas.ImportacionFeatureResponse)
def decide_feature(id_importacion: int, id_feature: int, data: schemas.DecisionGisRequest, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(GIS_ROLES))):
    return reconciliation.decide(db,id_importacion,id_feature,data,user)


@router.get("/importaciones/{id_importacion}/features/{id_feature}/decisiones", response_model=list[schemas.DecisionGisResponse])
def get_feature_decisions(id_importacion: int, id_feature: int, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    service.require_import_access(db,id_importacion,user)
    feature=db.query(models.ImportacionFeature).filter_by(id_importacion=id_importacion,id_importacion_feature=id_feature).first()
    if feature is None: raise HTTPException(404,"Feature no encontrada")
    return db.query(models.ImportacionFeatureDecision).filter_by(id_importacion_feature=id_feature).order_by(models.ImportacionFeatureDecision.id_decision).all()


@router.get('/importaciones/{id_importacion}/features/{id_feature}/geometria')
def get_feature_geometry(id_importacion: int,id_feature: int,db: Session=Depends(get_db),user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    from sqlalchemy import func
    service.require_import_access(db,id_importacion,user)
    row=db.query(models.ImportacionFeature.id_importacion_feature,
        func.ST_AsGeoJSON(models.ImportacionFeature.geometria_normalizada,15)).filter_by(
            id_importacion=id_importacion,id_importacion_feature=id_feature).one_or_none()
    if row is None: raise HTTPException(404,'Feature no encontrada')
    return {'type':'Feature','id':row[0],'properties':{},'geometry':json.loads(row[1]) if row[1] else None}
