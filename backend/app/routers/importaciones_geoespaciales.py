from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import auth, models
from ..database import get_db
from ..schemas_importaciones import (
    AliasTerritorialCreate,
    ConfirmacionImportacionRequest,
    FeaturePageResponse,
    FeatureRevisionRequest,
    ImportacionArchivoResponse,
    ImportacionFeatureResponse,
    MapeoImportacionRequest,
    OperacionImportacionResponse,
    PerfilMapeoCreate,
    PerfilMapeoResponse,
)
from ..services import importador_geoespacial as service


router = APIRouter(
    prefix="/importaciones-geoespaciales",
    tags=["Importaciones geoespaciales"],
)
allowed = auth.RoleChecker(["admin", "geografo"])


@router.post("", response_model=ImportacionArchivoResponse, status_code=201)
async def upload_import(
    file: UploadFile = File(...),
    fuente: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    return await service.stage_upload(db, file, fuente, current_user.id_usuario)


@router.get("", response_model=list[ImportacionArchivoResponse])
def list_imports(
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    query = db.query(models.ImportacionArchivo)
    if current_user.rol != "admin":
        query = query.filter(models.ImportacionArchivo.id_usuario_carga == current_user.id_usuario)
    return query.order_by(models.ImportacionArchivo.fecha_carga.desc()).limit(limit).all()


@router.get("/perfiles", response_model=list[PerfilMapeoResponse])
def list_profiles(
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(allowed),
):
    return (
        db.query(models.PerfilMapeoImportacion)
        .filter(models.PerfilMapeoImportacion.activo.is_(True))
        .order_by(models.PerfilMapeoImportacion.nombre)
        .all()
    )


@router.post("/perfiles", response_model=PerfilMapeoResponse, status_code=201)
def create_profile(
    payload: PerfilMapeoCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    return service.create_profile(db, payload, current_user.id_usuario)


@router.post("/alias-territoriales", status_code=201)
def create_territorial_alias(
    payload: AliasTerritorialCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    alias = service.create_alias(db, payload, current_user.id_usuario)
    return {
        "id_alias": alias.id_alias,
        "id_entidad": alias.id_entidad,
        "alias_nombre": alias.alias_nombre,
        "alias_clave": alias.alias_clave,
        "id_municipio_destino": alias.id_municipio_destino,
        "fuente": alias.fuente,
        "activo": alias.activo,
    }


@router.get("/{import_id}", response_model=ImportacionArchivoResponse)
def get_import(
    import_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    return service.get_import_or_404(db, import_id, current_user)


@router.put("/{import_id}/mapeo", response_model=ImportacionArchivoResponse)
def set_mapping(
    import_id: int,
    payload: MapeoImportacionRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    record = service.get_import_or_404(db, import_id, current_user)
    return service.update_mapping(db, record, payload, current_user.id_usuario)


@router.post("/{import_id}/procesar", response_model=OperacionImportacionResponse, status_code=202)
def process_import(
    import_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    record = service.get_import_or_404(db, import_id, current_user)
    if record.estado in service.RUNNING_STATES:
        raise HTTPException(status_code=409, detail="La importacion ya se esta procesando.")
    if record.estado == "completado" or (
        record.estado == "fallido" and record.error_codigo == "CONFIRMACION_FALLIDA"
    ):
        raise HTTPException(status_code=409, detail="La importacion ya entro a la fase de confirmacion.")
    service.validate_mapping(record.mapeo or {}, record.columnas_detectadas or [])
    background_tasks.add_task(service.process_import, record.id_importacion, current_user.id_usuario)
    return OperacionImportacionResponse(
        id_importacion=record.id_importacion,
        estado="analizando",
        detalle="La prevalidacion fue programada.",
    )


@router.get("/{import_id}/features", response_model=FeaturePageResponse)
def list_features(
    import_id: int,
    estado: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    record = service.get_import_or_404(db, import_id, current_user)
    query = db.query(models.ImportacionFeature).filter(
        models.ImportacionFeature.id_importacion == record.id_importacion
    )
    if estado:
        if estado not in {"valido", "advertencia", "error", "importado", "pendiente_revision", "descartado"}:
            raise HTTPException(status_code=422, detail="Estado de feature no valido.")
        query = query.filter(models.ImportacionFeature.estado == estado)
    total = query.count()
    items = query.order_by(models.ImportacionFeature.indice_feature).offset(offset).limit(limit).all()
    return FeaturePageResponse(total=total, items=items)


@router.patch("/{import_id}/features/{feature_id}", response_model=ImportacionFeatureResponse)
def revise_feature(
    import_id: int,
    feature_id: int,
    payload: FeatureRevisionRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    record = service.get_import_or_404(db, import_id, current_user)
    return service.revise_feature(db, record, feature_id, payload, current_user.id_usuario)


@router.post("/{import_id}/confirmar", response_model=OperacionImportacionResponse, status_code=202)
def confirm_import(
    import_id: int,
    payload: ConfirmacionImportacionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    record = service.get_import_or_404(db, import_id, current_user)
    retryable = record.estado == "fallido" and record.error_codigo == "CONFIRMACION_FALLIDA"
    if record.estado != "listo_revision" and not retryable:
        raise HTTPException(status_code=409, detail="La importacion no esta lista para confirmarse.")
    eligible = db.query(models.ImportacionFeature.id_importacion_feature).filter(
        models.ImportacionFeature.id_importacion == import_id,
        (
            (models.ImportacionFeature.estado == "valido")
            | (
                (models.ImportacionFeature.estado == "advertencia")
                & (
                    models.ImportacionFeature.advertencias_aceptadas.is_(True)
                    | payload.aceptar_advertencias
                )
            )
        ),
    ).first()
    if not eligible:
        raise HTTPException(status_code=409, detail="No hay registros validados y autorizados para importar.")
    background_tasks.add_task(
        service.confirm_import,
        record.id_importacion,
        current_user.id_usuario,
        payload.aceptar_advertencias,
    )
    return OperacionImportacionResponse(
        id_importacion=record.id_importacion,
        estado="confirmando",
        detalle="La confirmacion explicita fue registrada.",
    )


@router.get("/{import_id}/reporte.csv")
def download_report(
    import_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(allowed),
):
    record = service.get_import_or_404(db, import_id, current_user)
    filename = f"importacion-{record.id_importacion}-reporte.csv"
    return StreamingResponse(
        service.csv_report(db, record),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
