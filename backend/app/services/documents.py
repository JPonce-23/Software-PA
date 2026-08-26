"""Controlled document links and immutable file versions."""

import hashlib
import os
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from .access import require_document_access, require_document_target_access
from .common import commit_or_conflict, mark_inactive, set_audit_context


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".jpg", ".jpeg", ".png"}
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))


def upload_root() -> Path:
    root = Path(os.getenv("UPLOAD_ROOT", "uploads")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_original_name(value: str | None) -> str:
    name = Path(value or "archivo").name
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    return (name or "archivo")[:255]


def create_document(
    db: Session,
    entity_type: str,
    entity_id: int,
    data: schemas.DocumentoCreate,
    user: models.Usuario,
) -> models.Documento:
    require_document_target_access(
        db, user, entity_type, entity_id, mode="capture"
    )
    set_audit_context(db, user.id_usuario)
    document = models.Documento(
        **data.model_dump(exclude={"observaciones"}),
        observaciones=data.observaciones,
        creado_por=user.id_usuario,
    )
    db.add(document)
    try:
        db.flush()
        db.add(
            models.DocumentoVinculo(
                id_documento=document.id_documento,
                entidad_tipo=entity_type,
                entidad_id=entity_id,
                creado_por=user.id_usuario,
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="No fue posible crear el documento y su vínculo"
        ) from exc
    db.refresh(document)
    return document


def add_link(
    db: Session,
    document_id: int,
    entity_type: str,
    entity_id: int,
    user: models.Usuario,
) -> models.DocumentoVinculo:
    require_document_access(db, user, document_id, mode="capture")
    require_document_target_access(
        db, user, entity_type, entity_id, mode="capture"
    )
    set_audit_context(db, user.id_usuario)
    link = models.DocumentoVinculo(
        id_documento=document_id,
        entidad_tipo=entity_type,
        entidad_id=entity_id,
        creado_por=user.id_usuario,
    )
    db.add(link)
    commit_or_conflict(db, "El vínculo documental ya existe o no es válido")
    db.refresh(link)
    return link


async def store_version(
    db: Session,
    document_id: int,
    upload: UploadFile,
    user: models.Usuario,
) -> models.DocumentoVersion:
    require_document_access(db, user, document_id, mode="capture")
    original = _safe_original_name(upload.filename)
    extension = Path(original).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail="Tipo de archivo no permitido")
    content = await upload.read(MAX_UPLOAD_BYTES + 1)
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Archivo vacío o demasiado grande")
    digest = hashlib.sha256(content).hexdigest()
    previous = db.query(models.DocumentoVersion).filter(
        models.DocumentoVersion.id_documento == document_id,
        models.DocumentoVersion.hash_sha256 == digest,
    ).first()
    if previous is not None:
        raise HTTPException(status_code=409, detail="Esta versión ya fue cargada")
    next_version = (
        db.query(func.coalesce(func.max(models.DocumentoVersion.numero_version), 0))
        .filter(models.DocumentoVersion.id_documento == document_id)
        .scalar()
        + 1
    )
    relative = Path(str(document_id)) / f"{next_version:04d}-{uuid.uuid4().hex}{extension}"
    destination = (upload_root() / relative).resolve()
    if upload_root() not in destination.parents:
        raise HTTPException(status_code=422, detail="Ruta documental no válida")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    set_audit_context(db, user.id_usuario)
    version = models.DocumentoVersion(
        id_documento=document_id,
        numero_version=next_version,
        hash_sha256=digest,
        tamano_bytes=len(content),
        nombre_original=original,
        ruta_almacenamiento=str(relative),
        tipo_mime=upload.content_type,
        id_usuario_carga=user.id_usuario,
    )
    db.add(version)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=409, detail="No fue posible registrar la versión"
        ) from exc
    db.refresh(version)
    return version


def safe_version_path(version: models.DocumentoVersion) -> Path:
    root = upload_root()
    path = (root / version.ruta_almacenamiento).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return path


def delete_document(
    db: Session,
    document_id: int,
    reason: str,
    user: models.Usuario,
) -> None:
    document = require_document_access(db, user, document_id, mode="capture")
    set_audit_context(db, user.id_usuario)
    mark_inactive(document, user.id_usuario, reason)
    for link in db.query(models.DocumentoVinculo).filter(
        models.DocumentoVinculo.id_documento == document_id,
        models.DocumentoVinculo.activo.is_(True),
    ).all():
        mark_inactive(link, user.id_usuario, reason)
    commit_or_conflict(db, "No fue posible dar de baja el documento")
