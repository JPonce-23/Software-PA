"""Controlled document links and immutable file versions."""

import asyncio
import hashlib
import os
import re
from pathlib import Path

from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from anyio import CancelScope
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError, IntegrityError, TimeoutError as SQLTimeoutError
from sqlalchemy.orm import Session, sessionmaker

from .. import models, schemas
from .access import require_document_access, require_document_target_access
from .common import apply_update, commit_or_conflict, mark_inactive, set_audit_context
from .document_validation import DocumentValidationError, validate_document
from .document_storage import DocumentStorageError, stage_document, storage_event
from . import document_operations as operations
from .document_operations import authorization_fence
from .document_errors import (document_error, error_code, DOCUMENT_DUPLICATE,
    DOCUMENT_RECONCILIATION_REQUIRED, DOCUMENT_OPERATION_PENDING,
    DOCUMENT_INTEGRITY_CONFLICT, DOCUMENT_REQUEST_CONFLICT)


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
    values = data.model_dump(exclude={"observaciones"})
    if data.id_tipo_documento is not None:
        option = require_document_type(db, data.id_tipo_documento)
        validate_other_description(option, data.descripcion)
        if len(option.nombre) > 80:
            raise HTTPException(status_code=422, detail="El nombre del tipo excede el texto legado")
        values["tipo_documento"] = option.nombre
    set_audit_context(db, user.id_usuario)
    document = models.Documento(
        **values,
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


def list_document_types(db: Session, *, include_inactive: bool = False):
    query = db.query(models.CatalogoTipoDocumento)
    if not include_inactive:
        query = query.filter(models.CatalogoTipoDocumento.activo.is_(True))
    return query.order_by(
        models.CatalogoTipoDocumento.activo.desc(),
        models.CatalogoTipoDocumento.orden,
        models.CatalogoTipoDocumento.nombre,
        models.CatalogoTipoDocumento.codigo,
        models.CatalogoTipoDocumento.id_tipo_documento,
    ).all()


def require_document_type(db: Session, option_id: int) -> models.CatalogoTipoDocumento:
    # FOR SHARE also serializes against administrative deactivation.
    option = db.query(models.CatalogoTipoDocumento).filter(
        models.CatalogoTipoDocumento.id_tipo_documento == option_id,
        models.CatalogoTipoDocumento.activo.is_(True),
    ).with_for_update(read=True).first()
    if option is None:
        raise HTTPException(status_code=422, detail="Tipo documental activo inválido")
    return option


def validate_other_description(option: models.CatalogoTipoDocumento, description: str | None):
    if option.codigo == "OTRO" and (description is None or not description.strip(" ")):
        raise HTTPException(status_code=422, detail="OTRO requiere descripción no vacía")


def update_document(
    db: Session, document: models.Documento, data: schemas.DocumentoUpdate,
    user: models.Usuario,
) -> models.Documento:
    fields = data.model_fields_set
    if "tipo_documento" in fields and document.id_tipo_documento is not None:
        raise HTTPException(status_code=422, detail="Reclasifique mediante id_tipo_documento")
    option = document.clasificacion
    if "id_tipo_documento" in fields:
        option = require_document_type(db, data.id_tipo_documento)
    if option is not None:
        description = data.descripcion if "descripcion" in fields else document.descripcion
        validate_other_description(option, description)
    set_audit_context(db, user.id_usuario)
    apply_update(document, data, user.id_usuario)
    commit_or_conflict(db)
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


def _upload_actor(db: Session, actor_id: int) -> models.Usuario:
    actor = db.query(models.Usuario).filter(
        models.Usuario.id_usuario == actor_id,
        models.Usuario.activo.is_(True),
    ).first()
    if actor is None:
        raise HTTPException(status_code=401, detail="No se pudieron validar las credenciales")
    if actor.rol not in {"admin", "operador"}:
        raise HTTPException(status_code=403, detail="Operación no permitida para este rol")
    return actor


def _upload_sessions(db: Session):
    """Release authentication reads; never transfer its connection to our UoW.

    Called only in the worker, before opening either owned Session. Callers must
    not use the request Session concurrently. An external transaction/savepoint
    cannot provide the short, independently committed transaction required here.
    """
    if db.new or db.dirty or db.deleted:
        raise HTTPException(status_code=409, detail="La sesión contiene cambios pendientes")
    bind = db.get_bind(mapper=models.Documento)
    if isinstance(bind, Connection):
        raise HTTPException(status_code=409, detail="La carga requiere una sesión independiente")
    if bind.dialect.name != "postgresql":
        raise HTTPException(status_code=503, detail="La carga requiere PostgreSQL READ COMMITTED")
    db.rollback()  # Authentication may have autobegun a read transaction.
    return sessionmaker(
        bind=bind, autoflush=False, expire_on_commit=False,
    )


def _rollback_upload(db: Session, operation_id: str) -> None:
    try:
        db.rollback()
    except Exception:
        # Rollback is cleanup, never evidence that COMMIT did not reach the DB.
        storage_event("DOCUMENT_ROLLBACK_UNCONFIRMED", operation_id)


def _confirm_version(sessions, document_id, actor_id, staged, values, ticket):
    publication_attempted = False
    authorize = lambda session: _authorize_upload(session, document_id, actor_id)
    with sessions() as db:
        try:
            db.begin()
            connection = db.connection(execution_options={"isolation_level": "READ COMMITTED"})
            if connection.get_isolation_level().upper() != "READ COMMITTED":
                raise HTTPException(status_code=503, detail="La carga requiere READ COMMITTED")
            # Local to this short transaction; no global engine/session changes.
            db.execute(text("SELECT set_config('lock_timeout', '5000ms', true), "
                            "set_config('statement_timeout', '15000ms', true)"))
            # Select only the key: Documento's joined relationships must not turn
            # FOR UPDATE into a lock on the nullable side of an outer join.
            parent = db.execute(select(models.Documento.id_documento).where(
                models.Documento.id_documento == document_id,
            ).with_for_update(of=models.Documento)).scalar_one_or_none()
            if parent is None:
                raise HTTPException(status_code=404, detail="Documento no encontrado")
            authorization_fence(db)
            actor = _upload_actor(db, actor_id)
            # Fresh Session, after the lock: recheck active document, links,
            # project scope and current role. Keep existing estado semantics.
            require_document_access(db, actor, document_id, mode="capture")
            previous = db.query(models.DocumentoVersion).filter(
                models.DocumentoVersion.id_documento == document_id,
                models.DocumentoVersion.hash_sha256 == values["hash_sha256"],
            ).first()
            if previous is not None:
                raise document_error(409, "Esta versión ya fue cargada", DOCUMENT_DUPLICATE)
            number = db.query(func.coalesce(func.max(models.DocumentoVersion.numero_version), 0)).filter(
                models.DocumentoVersion.id_documento == document_id,
            ).scalar() + 1
            relative = Path(ticket.path)
            values.pop('extension')
            version = models.DocumentoVersion(**values, numero_version=number,
                ruta_almacenamiento=str(relative))
            set_audit_context(db, actor_id)
            db.add(version)
            db.flush()  # Immediate UNIQUE/FK/check/trigger errors precede publication.
            db.refresh(version)  # Load response scalars before publication/commit.
            publication_attempted = True
            staged.publish(relative.name)  # Existing no-replace, identity and fsync rules.
            operations.confirm(db, ticket, version)
            db.commit()
            return operations.decorate(version, ticket, replayed=False)
        except BaseException as exc:
            published = staged.published_name is not None
            if published:
                storage_event("DOCUMENT_REGISTRATION_UNCONFIRMED", staged.operation_id)
            _rollback_upload(db, staged.operation_id)
            status = (exc.status_code if isinstance(exc, HTTPException) else
                exc.status if isinstance(exc, DocumentStorageError) else
                409 if isinstance(exc, IntegrityError) or publication_attempted else 503)
            recovered = operations.failed(sessions, ticket, authorize,
                uncertain=publication_attempted, status=status,
                code="PUBLICATION_UNCONFIRMED" if publication_attempted else
                    error_code(exc) or (DOCUMENT_INTEGRITY_CONFLICT if isinstance(exc, IntegrityError) else "PREPUBLICATION_REJECTED"))
            if not isinstance(exc, Exception):
                raise
            if recovered is not None:
                return recovered
            if isinstance(exc, (HTTPException, DocumentStorageError)):
                if publication_attempted:
                    # A response classification is not a claim that the
                    # diagnostic UPDATE committed. The pending intent survives.
                    raise document_error(status, exc.detail,
                        DOCUMENT_RECONCILIATION_REQUIRED,
                        headers=exc.headers if isinstance(exc, HTTPException) else None) from exc
                raise
            if published:
                raise document_error(409,
                    "No fue posible confirmar el registro de la versión; consulte el historial antes de reintentar.",
                    DOCUMENT_RECONCILIATION_REQUIRED) from exc
            if isinstance(exc, IntegrityError):
                raise document_error(409, "Conflicto de integridad de la versión", error_code(exc) or DOCUMENT_INTEGRITY_CONFLICT) from exc
            if isinstance(exc, (DBAPIError, SQLTimeoutError)):
                code = getattr(getattr(exc, "orig", None), "pgcode", None)
                detail = ("La carga está ocupada; vuelva a intentarlo más tarde"
                    if code in {"55P03", "40P01", "57014"}
                    else "No fue posible registrar la versión en este momento")
                raise HTTPException(status_code=503, detail=detail) from exc
            raise


def _authorize_upload(db, document_id, actor_id):
    actor = _upload_actor(db, actor_id)
    require_document_access(db, actor, document_id, mode="capture")
    return actor


def _store_version_worker(db, document_id, upload, actor_id, request_key, client_key):
    """All blocking SQL, read/validation, hashing and POSIX work stays here."""
    try:
        sessions = _upload_sessions(db)
        # No transaction survives the initial authorization check or input read.
        with sessions() as check:
            check.connection(execution_options={"isolation_level": "READ COMMITTED"})
            actor = _upload_actor(check, actor_id)
            require_document_access(check, actor, document_id, mode="capture")
    except (DBAPIError, SQLTimeoutError) as exc:
        raise HTTPException(status_code=503,
            detail="No fue posible comprobar el acceso documental en este momento") from exc
    original = _safe_original_name(upload.filename)
    extension = Path(original).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail="Tipo de archivo no permitido")
    content = upload.file.read(MAX_UPLOAD_BYTES + 1)
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Archivo vacío o demasiado grande")
    try:
        canonical_mime = validate_document(content, extension, upload.content_type,
            max_file_bytes=MAX_UPLOAD_BYTES)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
    digest = hashlib.sha256(content).hexdigest()
    metadata = dict(id_documento=document_id, id_usuario=actor_id, hash_sha256=digest,
        tamano_bytes=len(content), nombre_original=original, tipo_mime=canonical_mime, extension=extension)
    authorize = lambda session: _authorize_upload(session, document_id, actor_id)
    try:
        reservation = operations.reserve(sessions, document_id, actor_id, request_key,
            metadata, authorize, client_key=client_key)
    except (DBAPIError, SQLTimeoutError) as exc:
        raise HTTPException(503, "La bitácora de cargas no está disponible; no se inició una publicación") from exc
    if isinstance(reservation, models.DocumentoVersion):
        return reservation
    ticket = reservation
    checkpoint_uncertain = False
    confirmation_started = False
    try:
        root = upload_root()
        with stage_document(root, document_id, content, digest, operation_id=ticket.id) as staged:
            checkpoint_uncertain = True
            operations.staged(sessions, ticket, staged.file_identity, authorize,
                coordination_identity=staged.coordination.identity)
            checkpoint_uncertain = False
            # _confirm_version owns failure recording after the parent lock.
            confirmation_started = True
            return _confirm_version(sessions, document_id, actor_id, staged, dict(
                id_documento=document_id, hash_sha256=digest, tamano_bytes=len(content),
                nombre_original=original, tipo_mime=canonical_mime,
                id_usuario_carga=actor_id, extension=extension,
            ), ticket)
    except BaseException as exc:
        # A second recording is conditional and cannot downgrade a committed or
        # rejected result. No state transition ever republishes a pending intent.
        status = (exc.status_code if isinstance(exc, HTTPException) else exc.status
            if isinstance(exc, DocumentStorageError) else 507 if isinstance(exc, OSError) else 503)
        recovered = operations.failed(sessions, ticket, authorize,
            uncertain=checkpoint_uncertain or confirmation_started, status=status,
            code="CONFIRMATION_UNCONFIRMED" if confirmation_started else "STAGING_UNCONFIRMED" if checkpoint_uncertain else "STAGING_REJECTED")
        if not isinstance(exc, Exception):
            raise
        if recovered is not None:
            return recovered
        if isinstance(exc, DocumentStorageError):
            raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
        if isinstance(exc, OSError):
            raise HTTPException(507, "No fue posible completar el almacenamiento documental") from exc
        if isinstance(exc, (DBAPIError, SQLTimeoutError)):
            raise HTTPException(503, "No fue posible confirmar la preparación de la carga; conserve la clave") from exc
        raise


async def store_version(
    db: Session,
    document_id: int,
    upload: UploadFile,
    user: models.Usuario,
    *,
    idempotency_key=None,
) -> models.DocumentoVersion:
    # inspect(identity) does not refresh an authentication-expired ORM instance.
    identity = inspect(user).identity
    if identity is None:
        raise HTTPException(status_code=401, detail="No se pudieron validar las credenciales")
    request_key = operations.key(idempotency_key)
    worker = asyncio.create_task(run_in_threadpool(
        _store_version_worker, db, document_id, upload, identity[0], request_key, idempotency_key is not None,
    ))
    try:
        return await asyncio.shield(worker)
    except HTTPException as exc:
        # Other upload conflicts (e.g. unlinked document/request Session) keep
        # their status/detail without being mislabeled as duplicate or uncertain.
        if exc.status_code in (409, 425) and error_code(exc) is None:
            raise document_error(exc.status_code, exc.detail,
                DOCUMENT_OPERATION_PENDING if exc.status_code == 425 else DOCUMENT_REQUEST_CONFLICT,
                headers=exc.headers) from exc
        raise
    except asyncio.CancelledError:
        # A Python thread cannot be cancelled safely. Finish/reap it before the
        # request dependency closes db or UploadFile. Never compensate a published
        # file, even if the caller receives no confirmation. Also handle repeated
        # asyncio cancellation; AnyIO scopes are shielded during this drain.
        with CancelScope(shield=True):
            while not worker.done():
                try:
                    await asyncio.shield(worker)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
        if not worker.cancelled():
            worker.exception()  # Consume an unobserved worker failure.
        raise


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
