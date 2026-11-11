"""Internal, explicitly requested recovery. No endpoint or background scanner.

The trusted caller authenticates actor_id and supplies a stable attempt UUID and
OPERATOR_REVIEW reason. Neither dry-run plans nor observation tokens are accepted.
Only the original currently authorized uploader can recover its operation. SQL
intent/result are durable; every successful return is independently verified.
"""
from dataclasses import dataclass
import os
import stat
import threading
import uuid

from fastapi import HTTPException
from sqlalchemy import select, func, text, or_
from sqlalchemy.orm import sessionmaker

from .. import models
from . import documents as uploads, document_operations as operations
from .document_coordination import WriterLease, CoordinationError
from .document_download import open_verified, DownloadError, _stamp
from .document_storage import _directory_flags
from .common import set_audit_context
from .document_validation import MIME_BY_EXTENSION

# Shared with the uploader: authorization cannot change before confirmation.
AUTHORIZATION_TABLES = operations.AUTHORIZATION_TABLES


@dataclass(frozen=True)
class RecoveryOutcome:
    attempt_id: str
    status: str
    code: str
    version_id: int | None = None


class CommitUncertain(Exception):
    pass


class Blocked(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _transaction(db):
    connection = db.connection(execution_options={'isolation_level': 'READ COMMITTED'})
    if connection.get_isolation_level() != 'READ COMMITTED':
        raise Blocked('UNSUPPORTED_ISOLATION')
    db.execute(text("SELECT set_config('lock_timeout','1000ms',true), "
                    "set_config('statement_timeout','15000ms',true), "
                    "set_config('synchronous_commit','on',true)"))


def _locked_operation(db, actor_id, document_id, operation_id):
    # Same parent-first order as _confirm_version. No joined outer relationships.
    parent = db.execute(select(models.Documento.id_documento).where(
        models.Documento.id_documento == document_id).with_for_update(of=models.Documento)).scalar_one_or_none()
    if parent is None:
        raise HTTPException(404, 'Operación documental no disponible')
    op = db.query(models.DocumentoOperacion).filter(
        models.DocumentoOperacion.id_operacion == operation_id,
        models.DocumentoOperacion.id_documento == document_id,
        models.DocumentoOperacion.id_usuario == actor_id,
    ).with_for_update(of=models.DocumentoOperacion).first()
    if op is None:
        raise HTTPException(404, 'Operación documental no disponible')
    # No interpolated input: every identifier is a reviewed constant.
    operations.authorization_fence(db)
    uploads._authorize_upload(db, document_id, actor_id)
    set_audit_context(db, actor_id)
    return op


def _attempt(db, attempt_id, actor_id, document_id, operation_id):
    row = db.execute(text('SELECT * FROM documento_recuperacion WHERE id_intento=:attempt'),
                     {'attempt': attempt_id}).mappings().first()
    if row is None or (row['id_usuario'], row['id_documento'], row['id_operacion']) != (actor_id, document_id, operation_id):
        raise HTTPException(404, 'Intento de recuperación no disponible')
    return row


def _intent(sessions, actor_id, document_id, operation_id, attempt_id):
    with sessions() as db:
        _transaction(db)
        # Intent logging takes no business row locks/FK on documento: an active
        # uploader may hold that row. The action below still locks parent first.
        operations.authorization_fence(db)
        op = db.get(models.DocumentoOperacion, operation_id)
        if op is None or (op.id_documento, op.id_usuario) != (document_id, actor_id):
            raise HTTPException(404, 'Operación documental no disponible')
        uploads._authorize_upload(db, document_id, actor_id)
        set_audit_context(db, actor_id)
        db.execute(text("INSERT INTO documento_recuperacion(id_intento,id_operacion,id_documento,id_usuario,motivo) "
                        "VALUES (:attempt,:operation,:document,:actor,'OPERATOR_REVIEW') "
                        "ON CONFLICT(id_intento) DO NOTHING"),
                   {'attempt': attempt_id, 'operation': operation_id, 'document': document_id, 'actor': actor_id})
        row = dict(_attempt(db, attempt_id, actor_id, document_id, operation_id))
        db.commit()  # Acknowledged durable intent before physical inspection/action.
        return row


def _finish(db, attempt_id, code, version_id=None):
    count = db.execute(text("UPDATE documento_recuperacion SET estado=:state,codigo=:code, "
        "id_documento_version=:version,terminado_en=clock_timestamp() "
        "WHERE id_intento=:attempt AND estado='pendiente'"),
        {'attempt': attempt_id, 'state': 'confirmada' if version_id is not None else 'bloqueada',
         'code': code, 'version': version_id}).rowcount
    if count != 1:
        raise Blocked('ATTEMPT_CHANGED')


def _blocked(sessions, actor_id, document_id, operation_id, attempt_id, code):
    try:
        with sessions() as db:
            _transaction(db)
            row = _attempt(db, attempt_id, actor_id, document_id, operation_id)
            if row['estado'] == 'pendiente':
                set_audit_context(db, actor_id)
                _finish(db, attempt_id, code)
                db.commit()
            elif row['estado'] == 'bloqueada':
                return RecoveryOutcome(str(attempt_id), 'BLOCKED', row['codigo'])
            elif row['estado'] == 'confirmada':
                return RecoveryOutcome(str(attempt_id), 'PENDING', 'INDEPENDENT_VERIFICATION_REQUIRED')
        return RecoveryOutcome(str(attempt_id), 'BLOCKED', code)
    except Exception:
        return RecoveryOutcome(str(attempt_id), 'PENDING', 'JOURNAL_RESULT_UNCONFIRMED')


def _metadata(op):
    if (op.extension not in MIME_BY_EXTENSION or op.tipo_mime != MIME_BY_EXTENSION[op.extension]
            or type(op.tamano_bytes) is not int or not 0 < op.tamano_bytes <= uploads.MAX_UPLOAD_BYTES
            or op.ruta_prevista != f'{op.id_documento}/op-{op.id_operacion.hex}{op.extension}'
            or op.ruta_staging != f'{op.id_documento}/.pending-{op.id_operacion.hex}/payload'
            or not isinstance(op.identidad_archivo, dict)
            or set(op.identidad_archivo) != {'device', 'inode'}):
        raise Blocked('INCOMPLETE_OPERATION_EVIDENCE')
    meta = {n: getattr(op, n) for n in ('id_documento', 'id_usuario', 'hash_sha256', 'tamano_bytes',
            'nombre_original', 'tipo_mime', 'extension')}
    if operations.fingerprint(meta) != op.huella_solicitud:
        raise Blocked('INCONSISTENT_OPERATION_METADATA')


def _physical(op, lease):
    _metadata(op); lease.check()
    verified = open_verified(lease.root, op.ruta_prevista, op.id_documento,
                             op.tamano_bytes, op.hash_sha256, threading.Event())
    try:
        info = verified.info
        if (op.identidad_archivo != {'device': info.st_dev, 'inode': info.st_ino}
                or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600):
            raise Blocked('FILE_IDENTITY_MISMATCH')
        _check_binding(op, lease, verified)
        return verified
    except BaseException:
        verified.close()
        raise



def _check_binding(op, lease, verified):
    verified.check(); lease.check()
    info = os.fstat(verified.fd)
    if info.st_nlink != 1:
        raise Blocked('PUBLISHED_NAME_CHANGED')
    document_fd = os.open(str(op.id_documento), _directory_flags(), dir_fd=lease.root_fd)
    try:
        current = os.stat(op.ruta_prevista.split('/')[1], dir_fd=document_fd, follow_symlinks=False)
        if _stamp(current) != _stamp(info) or current.st_nlink != 1:
            raise Blocked('PUBLISHED_NAME_CHANGED')
    finally:
        os.close(document_fd)
    lease.check()


def _version(db, op):
    # Called after the document/operation locks: version is the final row lock.
    version = db.query(models.DocumentoVersion).filter(
        models.DocumentoVersion.id_documento_version == op.id_documento_version,
    ).with_for_update(of=models.DocumentoVersion).first()
    if version is None or any(getattr(version, n) != getattr(op, n) for n in
        ('id_documento', 'hash_sha256', 'tamano_bytes', 'nombre_original', 'tipo_mime')) \
        or version.id_usuario_carga != op.id_usuario or version.ruta_almacenamiento != op.ruta_prevista:
        raise Blocked('CONFIRMED_RESULT_INCONSISTENT')
    return version


def _apply(sessions, actor_id, document_id, operation_id, attempt_id, lease):
    with sessions() as db:
        _transaction(db)
        op = _locked_operation(db, actor_id, document_id, operation_id)
        row = _attempt(db, attempt_id, actor_id, document_id, operation_id)
        if row['estado'] == 'bloqueada':
            raise Blocked(row['codigo'])
        if op.estado not in ('pendiente', 'requiere_reconciliacion', 'confirmada'):
            raise Blocked('TERMINAL_OPERATION_REJECTED')
        marker = db.execute(text('SELECT identidad FROM documento_coordinacion WHERE id_operacion=:id AND protocolo=1'),
                            {'id': operation_id}).scalar_one_or_none()
        if marker != lease.identity:
            raise Blocked('WRITER_PROTOCOL_UNPROVEN')
        verified = _physical(op, lease)
        try:
            if op.estado == 'confirmada':
                version = _version(db, op); code = 'EXISTING_RESULT'
            else:
                if row['estado'] != 'pendiente':
                    raise Blocked('ATTEMPT_CHANGED')
                duplicate = db.query(models.DocumentoVersion.id_documento_version).filter(
                    models.DocumentoVersion.id_documento == document_id,
                    or_(models.DocumentoVersion.hash_sha256 == op.hash_sha256,
                        models.DocumentoVersion.ruta_almacenamiento == op.ruta_prevista)).first()
                if duplicate is not None:
                    raise Blocked('EXISTING_VERSION_REQUIRES_REVIEW')
                number = db.query(func.coalesce(func.max(models.DocumentoVersion.numero_version), 0)).filter(
                    models.DocumentoVersion.id_documento == document_id).scalar() + 1
                version = models.DocumentoVersion(id_documento=document_id, numero_version=number,
                    hash_sha256=op.hash_sha256, tamano_bytes=op.tamano_bytes, nombre_original=op.nombre_original,
                    ruta_almacenamiento=op.ruta_prevista, tipo_mime=op.tipo_mime, id_usuario_carga=actor_id)
                db.add(version); db.flush(); db.refresh(version)
                # Existing 031 trigger validates original actor, metadata and link.
                op.estado = 'confirmada'; op.id_documento_version = version.id_documento_version
                op.confirmado_en = func.clock_timestamp(); op.codigo_error = None; op.http_error = None
                db.flush(); code = 'RECOVERED'
            _check_binding(op, lease, verified)
            if row['estado'] == 'pendiente':
                _finish(db, attempt_id, code, version.id_documento_version)
            try:
                db.commit()  # Operation + version + attempt result, one SQL transaction.
            except Exception as error:
                raise CommitUncertain() from error
        finally:
            verified.close()


def _verify(sessions, actor_id, document_id, operation_id, attempt_id, lease):
    with sessions() as db:
        _transaction(db)
        op = _locked_operation(db, actor_id, document_id, operation_id)
        row = _attempt(db, attempt_id, actor_id, document_id, operation_id)
        if op.estado != 'confirmada' or row['estado'] != 'confirmada':
            return RecoveryOutcome(str(attempt_id), 'PENDING', 'RESULT_NOT_CONFIRMED')
        version = _version(db, op)
        if row['id_documento_version'] != version.id_documento_version:
            raise Blocked('CONFIRMED_RESULT_INCONSISTENT')
        verified = _physical(op, lease)
        try:
            return RecoveryOutcome(str(attempt_id), 'VERIFIED', row['codigo'], version.id_documento_version)
        finally:
            verified.close()


def recover_document_operation(engine, actor_id, document_id, operation_id, *, attempt_id, root, reason):
    """Explicit internal operation, owner-only. No token/plan grants write access.

    SQL unavailability after a possible commit returns PENDING, never a claim of
    rollback or permission to delete/re-publish. Retry the SAME attempt UUID.
    Blocked terminal attempts need a new reviewed attempt after intervention.
    """
    if type(actor_id) is not int or actor_id <= 0 or type(document_id) is not int or document_id <= 0:
        raise ValueError('Invalid authenticated scope')
    operation_id, attempt_id = uuid.UUID(str(operation_id)), uuid.UUID(str(attempt_id))
    if reason != 'OPERATOR_REVIEW':
        raise ValueError('Explicit operator review required')
    if engine.dialect.name != 'postgresql':
        raise ValueError('PostgreSQL required')
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        intent = _intent(sessions, actor_id, document_id, operation_id, attempt_id)
    except HTTPException:
        raise
    except Exception:
        return RecoveryOutcome(str(attempt_id), 'PENDING', 'JOURNAL_INTENT_UNCONFIRMED')
    if intent['estado'] == 'bloqueada':
        return RecoveryOutcome(str(attempt_id), 'BLOCKED', intent['codigo'])
    try:
        with WriterLease(root, document_id, operation_id) as lease:
            try:
                _apply(sessions, actor_id, document_id, operation_id, attempt_id, lease)
            except (Blocked, CoordinationError, DownloadError) as error:
                return _blocked(sessions, actor_id, document_id, operation_id, attempt_id, error.code)
            except HTTPException:
                return _blocked(sessions, actor_id, document_id, operation_id, attempt_id, 'AUTHORIZATION_REVOKED')
            except CommitUncertain:
                # COMMIT may have reached PostgreSQL: fresh verification only.
                pass
            except Exception:
                return _blocked(sessions, actor_id, document_id, operation_id, attempt_id, 'SQL_PRECONDITION_FAILED')
            try:
                return _verify(sessions, actor_id, document_id, operation_id, attempt_id, lease)
            except HTTPException:
                return RecoveryOutcome(str(attempt_id), 'BLOCKED', 'AUTHORIZATION_REVOKED')
            except (Blocked, CoordinationError, DownloadError) as error:
                return RecoveryOutcome(str(attempt_id), 'BLOCKED', error.code)
            except Exception:
                return RecoveryOutcome(str(attempt_id), 'PENDING', 'INDEPENDENT_VERIFICATION_UNAVAILABLE')
    except CoordinationError as error:
        if error.code == 'ACTIVE_WRITER':
            # Another recovery may own this SAME attempt. Never terminalize its
            # journal row; the durable intent stays retryable under the same UUID.
            return RecoveryOutcome(str(attempt_id), 'PENDING', 'ACTIVE_WRITER')
        return _blocked(sessions, actor_id, document_id, operation_id, attempt_id, error.code)
    except OSError:
        return _blocked(sessions, actor_id, document_id, operation_id, attempt_id, 'COORDINATION_UNAVAILABLE')
