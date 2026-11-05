"""Durable scoped upload reservations. Never resumes publication on a retry."""
from dataclasses import dataclass
import hashlib
import json
import uuid

from fastapi import HTTPException
from sqlalchemy import func, text, update
from sqlalchemy.dialects.postgresql import insert

from .. import models
from .common import set_audit_context
from .document_storage import storage_event
from .document_errors import (document_error, REJECTED_CODES,
    DOCUMENT_IDEMPOTENCY_CONFLICT, DOCUMENT_RECONCILIATION_REQUIRED,
    DOCUMENT_OPERATION_PENDING, DOCUMENT_OPERATION_REJECTED)


# Coarse, bounded authorization fence. SHARE conflicts with every INSERT/UPDATE/
# DELETE, including revocation paths that do not know this recovery protocol.
# NOWAIT avoids lock cycles with business writers; contention blocks recovery.
# This exact set covers all model relations read by canonical access.py.
AUTHORIZATION_TABLES = (
    'actividad_campo', 'afectacion', 'afectacion_unidad_agraria', 'asamblea',
    'asamblea_convocatoria', 'convenio', 'convenio_compareciente', 'documento',
    'documento_vinculo', 'expediente_requisito', 'indemnizacion', 'nucleo_agrario',
    'orv', 'orv_integrante', 'padron_historial', 'pago', 'parcela', 'parcela_titular',
    'persona', 'proyecto', 'proyecto_nucleo', 'tramite_fifonafe',
    'tramite_fifonafe_evento', 'tramite_fifonafe_interviniente', 'tramite_ran',
    'tramite_ran_evento', 'unidad_agraria', 'unidad_agraria_titular', 'usuario',
    'usuario_proyecto',
)

def authorization_fence(db):
    # Constants only; fail immediately rather than wait in a business lock cycle.
    db.execute(text('LOCK TABLE ' + ','.join('public.' + n for n in AUTHORIZATION_TABLES) + ' IN SHARE MODE NOWAIT'))


@dataclass(frozen=True)
class Ticket:
    id: uuid.UUID
    key: uuid.UUID
    document_id: int
    actor_id: int
    fingerprint: str
    path: str


def key(value):
    try:
        return uuid.uuid4() if value is None else uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(422, "Idempotency-Key debe ser un UUID válido") from None


def fingerprint(metadata):
    return hashlib.sha256(json.dumps(metadata, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True).encode()).hexdigest()


def _connection(db):
    connection = db.connection(execution_options={"isolation_level": "READ COMMITTED"})
    if connection.get_isolation_level().upper() != "READ COMMITTED":
        raise HTTPException(503, "La bitácora requiere READ COMMITTED")
    db.execute(text("SELECT set_config('lock_timeout','5000ms',true), "
                    "set_config('statement_timeout','15000ms',true)"))


def _query(db, document_id, actor_id, request_key):
    return db.query(models.DocumentoOperacion).filter(
        models.DocumentoOperacion.id_documento == document_id,
        models.DocumentoOperacion.id_usuario == actor_id,
        models.DocumentoOperacion.clave_idempotencia == request_key,
    ).first()


def decorate(version, ticket, *, replayed):
    version._idempotency_key = str(ticket.key)
    version._upload_operation_id = str(ticket.id)
    version._idempotency_replayed = replayed
    return version


def _ticket(operation):
    return Ticket(operation.id_operacion, operation.clave_idempotencia,
        operation.id_documento, operation.id_usuario, operation.huella_solicitud,
        operation.ruta_prevista)


def _result(db, operation, expected):
    headers = {"Idempotency-Key": str(operation.clave_idempotencia),
        "X-Document-Operation-State": operation.estado}
    if operation.huella_solicitud != expected:
        raise document_error(409, "La clave ya identifica otra carga o metadatos incompatibles",
            DOCUMENT_IDEMPOTENCY_CONFLICT, headers=headers)
    if operation.estado == "confirmada":
        version = db.get(models.DocumentoVersion, operation.id_documento_version)
        if version is None or any(getattr(version, name) != getattr(operation, name)
            for name in ["id_documento", "hash_sha256", "tamano_bytes", "nombre_original", "tipo_mime"]) \
            or version.id_usuario_carga != operation.id_usuario \
            or version.ruta_almacenamiento != operation.ruta_prevista:
            raise document_error(409, "El resultado registrado requiere revisión",
                DOCUMENT_RECONCILIATION_REQUIRED, headers=headers)
        return decorate(version, _ticket(operation), replayed=True)
    if operation.estado == "pendiente":
        headers["Retry-After"] = "3"
        raise document_error(425, "La carga sigue pendiente o sin confirmación; conserve la clave y consulte el historial",
            DOCUMENT_OPERATION_PENDING, headers=headers)
    if operation.estado == "rechazada":
        # Older rejected rows have generic diagnostic codes: never infer SHA
        # duplication from PREPUBLICATION_REJECTED or expose raw diagnostics.
        code = operation.codigo_error if operation.codigo_error in REJECTED_CODES else DOCUMENT_OPERATION_REJECTED
        raise document_error(operation.http_error or 409,
            "La operación fue rechazada; para una nueva carga lógica seleccione nuevamente el archivo", code, headers=headers)
    raise document_error(409, "La carga requiere reconciliación; no se volverá a publicar automáticamente",
        DOCUMENT_RECONCILIATION_REQUIRED, headers=headers)


def lookup(sessions, document_id, actor_id, request_key, expected, authorize):
    with sessions() as db:
        _connection(db)
        authorize(db)  # Every result lookup revalidates live credentials/scope.
        operation = _query(db, document_id, actor_id, request_key)
        if operation is None:
            return None
        result = _result(db, operation, expected)
        db.expunge(result)  # Read-session rollback must not expire the response.
        return result


def reserve(sessions, document_id, actor_id, request_key, metadata, authorize, *, client_key):
    expected = fingerprint(metadata)
    # Fast path for retries: no filesystem work and no new intent.
    result = lookup(sessions, document_id, actor_id, request_key, expected, authorize)
    if result is not None:
        return result
    operation_id = uuid.uuid4()
    path = f"{document_id}/op-{operation_id.hex}{metadata['extension']}"
    values = dict(id_operacion=operation_id, clave_idempotencia=request_key,
        cliente_con_clave=client_key, id_documento=document_id, id_usuario=actor_id,
        huella_solicitud=expected, estado="pendiente", ruta_prevista=path,
        ruta_staging=f"{document_id}/.pending-{operation_id.hex}/payload",
        **{name: metadata[name] for name in ["hash_sha256", "tamano_bytes", "nombre_original", "extension", "tipo_mime"]})
    try:
        with sessions() as db:
            _connection(db); authorize(db); set_audit_context(db, actor_id)
            inserted = db.execute(insert(models.DocumentoOperacion).values(**values)
                .on_conflict_do_nothing(constraint="uq_documento_operacion_clave")
                .returning(models.DocumentoOperacion.id_operacion)).scalar_one_or_none()
            db.commit()  # Durable intent MUST be acknowledged before any staging/publication.
    except Exception:
        # A lost intent acknowledgement never authorizes publication or adoption.
        result = lookup(sessions, document_id, actor_id, request_key, expected, authorize)
        if result is not None:
            return result
        raise HTTPException(503, "No fue posible confirmar la intención de carga; conserve la clave") from None
    if inserted is None:
        result = lookup(sessions, document_id, actor_id, request_key, expected, authorize)
        if result is None:
            raise document_error(409, "La reserva requiere revisión; no se iniciará otra publicación", DOCUMENT_RECONCILIATION_REQUIRED)
        return result
    if inserted != operation_id:
        raise document_error(409, "Identidad de reserva inesperada; no se publicará el archivo", DOCUMENT_RECONCILIATION_REQUIRED)
    return Ticket(operation_id, request_key, document_id, actor_id, expected, path)


def staged(sessions, ticket, identity, authorize, *, coordination_identity=None):
    if coordination_identity is None:
        raise HTTPException(503, "La carga requiere coordinación verificable")
    with sessions() as db:
        _connection(db); authorize(db); set_audit_context(db, ticket.actor_id)
        db.execute(text("INSERT INTO documento_coordinacion(id_operacion,protocolo,identidad) "
                        "VALUES (:operation,1,CAST(:identity AS jsonb))"),
            {"operation": ticket.id, "identity": json.dumps(coordination_identity)})
        count = db.execute(update(models.DocumentoOperacion).where(
            models.DocumentoOperacion.id_operacion == ticket.id,
            models.DocumentoOperacion.estado == "pendiente",
            models.DocumentoOperacion.identidad_archivo.is_(None),
        ).values(identidad_archivo={"device": identity[0], "inode": identity[1]},
            staging_preparado_en=func.clock_timestamp())).rowcount
        if count != 1:
            raise document_error(409, "La intención de carga cambió; no se publicará el archivo", DOCUMENT_RECONCILIATION_REQUIRED)
        db.commit()  # Separate short TX, before acquiring the parent row lock.


def confirm(db, ticket, version):
    # Same SQL transaction as version INSERT; the migration verifies the link.
    count = db.execute(update(models.DocumentoOperacion).where(
        models.DocumentoOperacion.id_operacion == ticket.id,
        models.DocumentoOperacion.estado == "pendiente",
        models.DocumentoOperacion.huella_solicitud == ticket.fingerprint,
    ).values(estado="confirmada", id_documento_version=version.id_documento_version,
        confirmado_en=func.clock_timestamp())).rowcount
    if count != 1:
        raise document_error(409, "La operación no pudo confirmar su resultado", DOCUMENT_RECONCILIATION_REQUIRED)


def failed(sessions, ticket, authorize, *, uncertain, status, code):
    """Fresh-session recovery is read-only for a confirmed result; no file I/O."""
    try:
        with sessions() as db:
            _connection(db)
            db.execute(text("SELECT set_config('lock_timeout','1000ms',true)"))
            authorize(db)
            operation = db.query(models.DocumentoOperacion).filter(
                models.DocumentoOperacion.id_operacion == ticket.id,
                models.DocumentoOperacion.id_usuario == ticket.actor_id,
                models.DocumentoOperacion.id_documento == ticket.document_id,
            ).with_for_update().first()
            if operation is None:
                return None
            if operation.estado == "confirmada":
                result = _result(db, operation, ticket.fingerprint)
                db.expunge(result)
                return result
            if operation.estado != "pendiente":
                return None
            set_audit_context(db, ticket.actor_id)
            operation.estado = "requiere_reconciliacion" if uncertain else "rechazada"
            operation.codigo_error = code
            operation.http_error = status
            db.commit()
    except Exception:
        # Original pending intent/path remain durable even if this diagnostic
        # update cannot be acknowledged. No retry is allowed to publish it.
        storage_event("DOCUMENT_OPERATION_STATE_UNCONFIRMED", ticket.id.hex)
    return None
