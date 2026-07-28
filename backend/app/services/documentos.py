import hashlib
import os
import zipfile
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from .common import set_audit_context


ALLOWED_FILE_TYPES = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".jpg": {"image/jpeg", "application/octet-stream"},
    ".jpeg": {"image/jpeg", "application/octet-stream"},
    ".png": {"image/png", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
}
DEFAULT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def upload_root() -> Path:
    return Path(os.getenv("UPLOAD_ROOT", "uploads")).resolve()


def max_upload_bytes() -> int:
    raw_value = os.getenv("MAX_UPLOAD_BYTES")
    if raw_value is None:
        return DEFAULT_MAX_UPLOAD_BYTES
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError("MAX_UPLOAD_BYTES debe ser un entero") from exc
    if value <= 0:
        raise RuntimeError("MAX_UPLOAD_BYTES debe ser mayor que cero")
    return value


def _validar_tipo_archivo(
    filename: str | None,
    content_type: str | None,
) -> tuple[str, str]:
    nombre = Path(filename or "").name
    extension = Path(nombre).suffix.lower()
    if not nombre or extension not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Solo se aceptan archivos PDF, JPG, JPEG, PNG y DOCX",
        )
    mime = (content_type or "application/octet-stream").lower()
    if mime not in ALLOWED_FILE_TYPES[extension]:
        raise HTTPException(
            status_code=400,
            detail="El tipo MIME no corresponde con la extensión del archivo",
        )
    return nombre, extension


def _validar_firma(extension: str, encabezado: bytes) -> None:
    firmas_validas = {
        ".pdf": encabezado.startswith(b"%PDF-"),
        ".jpg": encabezado.startswith(b"\xff\xd8\xff"),
        ".jpeg": encabezado.startswith(b"\xff\xd8\xff"),
        ".png": encabezado.startswith(b"\x89PNG\r\n\x1a\n"),
        ".docx": encabezado.startswith(b"PK\x03\x04"),
    }
    if not firmas_validas[extension]:
        raise HTTPException(
            status_code=400,
            detail="El contenido del archivo no coincide con su extensión",
        )


def _validar_docx(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            entries = set(archive.namelist())
    except (OSError, zipfile.BadZipFile) as exc:
        raise HTTPException(status_code=400, detail="El archivo DOCX no es válido") from exc
    required = {"[Content_Types].xml", "word/document.xml"}
    if not required.issubset(entries):
        raise HTTPException(status_code=400, detail="El archivo DOCX no es válido")


def get_documento_for_update(
    db: Session,
    id_documento: int,
) -> models.DocumentacionSoporte:
    documento = (
        db.query(models.DocumentacionSoporte)
        .filter(
            models.DocumentacionSoporte.id_documento == id_documento,
            models.DocumentacionSoporte.activo.is_(True),
        )
        .with_for_update()
        .first()
    )
    if documento is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return documento


async def save_version(
    db: Session,
    documento: models.DocumentacionSoporte,
    file: UploadFile,
    user_id: int,
) -> models.DocumentoVersion:
    nombre_original, extension = _validar_tipo_archivo(
        file.filename,
        file.content_type,
    )
    root = upload_root()
    directory = root / f"documento_{documento.id_documento}"
    directory.mkdir(parents=True, exist_ok=True)
    token = uuid4().hex
    temp_path = directory / f".{token}.tmp"
    digest = hashlib.sha256()
    size = 0
    header = b""

    try:
        async with aiofiles.open(temp_path, "wb") as output:
            while chunk := await file.read(1024 * 1024):
                if not header:
                    header = chunk[:16]
                    _validar_firma(extension, header)
                size += len(chunk)
                if size > max_upload_bytes():
                    raise HTTPException(
                        status_code=413,
                        detail="El archivo excede el tamaño máximo permitido",
                    )
                digest.update(chunk)
                await output.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="El archivo está vacío")
        if extension == ".docx":
            _validar_docx(temp_path)

        numero_version = (
            db.query(func.coalesce(func.max(models.DocumentoVersion.numero_version), 0))
            .filter(models.DocumentoVersion.id_documento == documento.id_documento)
            .scalar()
            + 1
        )
        final_path = directory / f"v{numero_version}_{token}{extension}"
        os.replace(temp_path, final_path)

        set_audit_context(db, user_id)
        version = models.DocumentoVersion(
            id_documento=documento.id_documento,
            numero_version=numero_version,
            hash_sha256=digest.hexdigest(),
            tamano_bytes=size,
            nombre_archivo_original=nombre_original,
            ruta_almacenamiento=str(final_path),
            tipo_mime=file.content_type,
            id_usuario_carga=user_id,
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version
    except Exception:
        db.rollback()
        if temp_path.exists():
            temp_path.unlink()
        if "final_path" in locals() and final_path.exists():
            final_path.unlink()
        raise
    finally:
        await file.close()


def latest_version(
    db: Session,
    id_documento: int,
) -> models.DocumentoVersion:
    version = (
        db.query(models.DocumentoVersion)
        .filter_by(id_documento=id_documento, activo=True)
        .order_by(models.DocumentoVersion.numero_version.desc())
        .first()
    )
    if version is None:
        raise HTTPException(
            status_code=404,
            detail="El documento todavía no tiene versiones",
        )
    return version


def safe_storage_path(version: models.DocumentoVersion) -> Path:
    path = Path(version.ruta_almacenamiento).resolve()
    if not path.is_relative_to(upload_root()):
        raise HTTPException(status_code=500, detail="Ruta de archivo inválida")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Archivo físico no encontrado")
    return path
