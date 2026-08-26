"""Document metadata, controlled links and immutable versions."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services import documents as service
from ..services.access import (
    require_document_access,
    require_document_target_access,
)


router = APIRouter(tags=["Documentos"])
READ_ROLES = ["admin", "operador", "visualizador", "geografo"]
CAPTURE_ROLES = ["admin", "operador"]


@router.get(
    "/documentos/objetivos/{entidad_tipo}/{entidad_id}",
    response_model=list[schemas.DocumentoResponse],
)
def list_documents(
    entidad_tipo: str,
    entidad_id: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_document_target_access(db, user, entidad_tipo, entidad_id)
    return db.query(models.Documento).join(models.DocumentoVinculo).filter(
        models.DocumentoVinculo.entidad_tipo == entidad_tipo,
        models.DocumentoVinculo.entidad_id == entidad_id,
        models.DocumentoVinculo.activo.is_(True),
        models.Documento.activo.is_(True),
    ).order_by(models.Documento.tipo_documento, models.Documento.id_documento).all()


@router.post(
    "/documentos/objetivos/{entidad_tipo}/{entidad_id}",
    response_model=schemas.DocumentoResponse,
    status_code=201,
)
def create_document(
    entidad_tipo: str,
    entidad_id: int,
    data: schemas.DocumentoCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_document(db, entidad_tipo, entidad_id, data, user)


@router.post(
    "/documentos/{id_documento}/vinculos/{entidad_tipo}/{entidad_id}",
    response_model=schemas.DocumentoVinculoResponse,
    status_code=201,
)
def add_document_link(
    id_documento: int,
    entidad_tipo: str,
    entidad_id: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.add_link(
        db, id_documento, entidad_tipo, entidad_id, user
    )


@router.get(
    "/documentos/{id_documento}/versiones",
    response_model=list[schemas.DocumentoVersionResponse],
)
def list_versions(
    id_documento: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_document_access(db, user, id_documento)
    return db.query(models.DocumentoVersion).filter(
        models.DocumentoVersion.id_documento == id_documento
    ).order_by(models.DocumentoVersion.numero_version.desc()).all()


@router.post(
    "/documentos/{id_documento}/versiones",
    response_model=schemas.DocumentoVersionResponse,
    status_code=201,
)
async def upload_version(
    id_documento: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return await service.store_version(db, id_documento, archivo, user)


@router.get("/documentos/versiones/{id_version}/descarga")
def download_version(
    id_version: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    version = db.get(models.DocumentoVersion, id_version)
    if version is None:
        raise HTTPException(status_code=404, detail="Versión no encontrada")
    require_document_access(db, user, version.id_documento)
    return FileResponse(
        service.safe_version_path(version),
        filename=version.nombre_original,
        media_type=version.tipo_mime or "application/octet-stream",
    )


@router.delete(
    "/documentos/{id_documento}",
    response_model=schemas.AuthOperationResponse,
)
def delete_document(
    id_documento: int,
    data: schemas.BajaRequest,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    service.delete_document(db, id_documento, data.motivo, user)
    return {"detail": "Documento dado de baja"}
