from typing import List

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .. import auth, models, schemas
from ..database import get_db
from ..services import documentos as service
from ..services.common import get_active, mark_inactive, set_audit_context


router = APIRouter()
READ_ROLES = ["admin", "operador", "visualizador", "geografo"]
WRITE_ROLES = ["admin", "operador"]


@router.get(
    "/documentacion/{id_documento}/versiones",
    response_model=List[schemas.DocumentoVersionResponse],
    tags=["Documentación"],
)
def listar_versiones(
    id_documento: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    get_active(
        db,
        models.DocumentacionSoporte,
        id_documento,
        "id_documento",
        "Documento no encontrado",
    )
    return (
        db.query(models.DocumentoVersion)
        .filter_by(id_documento=id_documento, activo=True)
        .order_by(models.DocumentoVersion.numero_version.desc())
        .all()
    )


@router.get(
    "/documentacion/{id_documento}/versiones/{numero_version}/archivo",
    tags=["Documentación"],
)
def descargar_version(
    id_documento: int,
    numero_version: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    get_active(
        db,
        models.DocumentacionSoporte,
        id_documento,
        "id_documento",
        "Documento no encontrado",
    )
    version = (
        db.query(models.DocumentoVersion)
        .filter_by(
            id_documento=id_documento,
            numero_version=numero_version,
            activo=True,
        )
        .first()
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Versión no encontrada")
    path = service.safe_storage_path(version)
    return FileResponse(
        path,
        filename=version.nombre_archivo_original,
        media_type=version.tipo_mime,
    )


@router.post(
    "/documentacion/{id_documento}/archivo",
    response_model=schemas.DocumentoVersionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Documentación"],
)
async def subir_archivo(
    id_documento: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    documento = await run_in_threadpool(
        service.get_documento_for_update,
        db,
        id_documento,
    )
    return await service.save_version(
        db,
        documento,
        file,
        current_user.id_usuario,
    )


@router.get(
    "/documentacion/{id_documento}/archivo",
    tags=["Documentación"],
)
def descargar_ultima_version(
    id_documento: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    get_active(
        db,
        models.DocumentacionSoporte,
        id_documento,
        "id_documento",
        "Documento no encontrado",
    )
    version = service.latest_version(db, id_documento)
    path = service.safe_storage_path(version)
    return FileResponse(
        path,
        filename=version.nombre_archivo_original,
        media_type=version.tipo_mime,
    )


@router.delete(
    "/documentacion/{id_documento}",
    tags=["Documentación"],
)
def eliminar_documento(
    id_documento: int,
    motivo: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(
        auth.RoleChecker(["admin", "operador", "geografo"])
    ),
):
    documento = get_active(
        db,
        models.DocumentacionSoporte,
        id_documento,
        "id_documento",
        "Documento no encontrado",
    )
    set_audit_context(db, current_user.id_usuario)
    versiones = (
        db.query(models.DocumentoVersion)
        .filter_by(id_documento=id_documento, activo=True)
        .all()
    )
    for version in versiones:
        mark_inactive(version, current_user.id_usuario, motivo)
    mark_inactive(documento, current_user.id_usuario, motivo)
    db.commit()
    return {"status": "success", "message": "Documento dado de baja"}
