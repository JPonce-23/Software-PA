"""Document metadata, controlled links and immutable versions."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services import documents as service
from ..services.document_read_models import consolidated_documents
from ..services.access import (
    require_document_access,
    require_document_target_access,
)


router = APIRouter(tags=["Documentos"])
READ_ROLES = ["admin", "operador", "visualizador", "geografo"]
CAPTURE_ROLES = ["admin", "operador"]


@router.get(
    "/proyecto-nucleo/{id_proyecto_nucleo}/documentos",
    response_model=list[schemas.DocumentoConsolidadoResponse],
    description="Soporte documental consolidado de sólo lectura por procedencia. Incluye vínculos activos y referencias de requisitos con vínculo autorizado dentro del alcance; versión vigente = mayor numero_version existente.",
)
def list_consolidated_documents(
    id_proyecto_nucleo: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return consolidated_documents(db, id_proyecto_nucleo, user)


@router.get(
    "/catalogos/tipos-documento", response_model=list[schemas.TipoDocumentoResponse],
    description="Catálogo documental sin paginación. Sólo activos por defecto; lectura para los cuatro roles.",
)
def list_document_types(
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return service.list_document_types(db, include_inactive=incluir_inactivos)


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
    description="Exactamente uno de id_tipo_documento activo o tipo_documento legado. OTRO exige descripcion; selecciones inválidas producen 422.",
)
def create_document(
    entidad_tipo: str,
    entidad_id: int,
    data: schemas.DocumentoCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_document(db, entidad_tipo, entidad_id, data, user)


@router.patch(
    "/documentos/{id_documento}", response_model=schemas.DocumentoResponse,
    description="Omitir selectores conserva la clasificación. No permite NULL, ambos selectores ni texto legado con FK. Reclasificar exige ID activo; OTRO exige descripción final válida.",
)
def update_document(
    id_documento: int,
    data: schemas.DocumentoUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    document = require_document_access(db, user, id_documento, mode="capture")
    return service.update_document(db, document, data, user)


@router.get(
    "/trazabilidad/objetivos/{entidad_tipo}/{entidad_id}",
    response_model=list[schemas.TrazabilidadFuenteResponse],
)
def list_source_traceability(
    entidad_tipo: str,
    entidad_id: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_document_target_access(db, user, entidad_tipo, entidad_id)
    return db.query(models.TrazabilidadFuente).filter(
        models.TrazabilidadFuente.entidad_tipo == entidad_tipo,
        models.TrazabilidadFuente.entidad_id == entidad_id,
    ).order_by(models.TrazabilidadFuente.registrado_en.desc()).all()


@router.post(
    "/trazabilidad/objetivos/{entidad_tipo}/{entidad_id}",
    response_model=schemas.TrazabilidadFuenteResponse,
    status_code=201,
)
def create_source_traceability(
    entidad_tipo: str,
    entidad_id: int,
    data: schemas.TrazabilidadFuenteCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    require_document_target_access(db, user, entidad_tipo, entidad_id, mode="capture")
    entity = models.TrazabilidadFuente(
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        id_usuario_registro=user.id_usuario,
        **data.model_dump(),
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


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
