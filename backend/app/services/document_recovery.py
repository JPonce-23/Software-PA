"""Internal 3B evaluation only: no executor, mutation, endpoint or repair mode.

An observation token is a correlation fingerprint, NEVER a capability to apply
a transition. Two new read-only SQL snapshots and two descriptor-based physical
checks are required for every call. Even a stable observation proves no lease,
abandonment, or atomicity between PostgreSQL and the filesystem.
"""
import asyncio
from dataclasses import dataclass, field
import errno
import hashlib
import hmac
import os
import stat
import threading
import uuid

from anyio import CancelScope
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

from . import document_reconciliation as observation

EXISTING_CONFIRMATION = "EXISTING_CONFIRMATION"
PUBLISHED_WITHOUT_CONFIRMATION = "PUBLICATION_CANDIDATE_WITHOUT_CONFIRMATION"
LOCK_TIMEOUT = "LOCK_TIMEOUT"
SQL_TIMEOUT = "SQL_TIMEOUT"

# Specifications for a FUTURE executor, not implemented or satisfied by dry-run.
# Matching the uploader's parent-first ordering is mandatory. Authorization rows
# also need a shared locking protocol with revocation before enabling writes.
FUTURE_LOCK_ORDER = ("documento:id_documento", "documento_operacion:id_operacion",
                     "documento_version:id_documento_version")
FUTURE_PRECONDITIONS = (
    "EXPLICIT_TRANSITION_AUTHORIZATION", "NEW_READ_COMMITTED_TRANSACTION",
    "BOUNDED_POSTGRESQL_LOCKS_IN_DOCUMENT_OPERATION_VERSION_ORDER",
    "LIVE_CAPTURE_AUTHORIZATION_AND_REVOCATION_FENCING",
    "RECHECK_OPERATION_VERSION_DOCUMENT_UNDER_LOCKS",
    "WRITER_QUIESCENCE_OR_FENCING_PROOF", "FRESH_DESCRIPTOR_EVIDENCE",
    "LEGAL_031_TRANSITION_AND_ORIGINAL_ACTOR_CONTEXT",
    "DURABLE_RECOVERY_ATTEMPT_AND_UNCERTAIN_COMMIT_PROTOCOL",
    "VERIFY_RESULT_IN_INDEPENDENT_AUTHORIZED_SESSION",
)


@dataclass(frozen=True)
class ExistingResult:
    document_id: int
    version_id: int


@dataclass(frozen=True)
class RecoveryPlan:
    operation_id: str | None
    document_id: int | None
    durable_state: str | None
    version_id: int | None
    diagnostics: tuple[str, ...]
    proposed_action: str
    evidence: tuple
    pending_preconditions: tuple[str, ...] = FUTURE_PRECONDITIONS
    blocked_reason: str | None = None
    existing_result: ExistingResult | None = None
    observation_token: str | None = None
    complete: bool = False
    dry_run: bool = True
    transition_enabled: bool = False
    format_version: str = "ss12-recovery-plan-v1"


@dataclass(frozen=True)
class _Physical:
    file: observation._File = field(repr=False)
    stamps: tuple = field(default=(), repr=False)


def _physical(root, operation, budget):
    """Reuse 3A's no-follow, no-atime, bounded regular-file descriptor reader.

    Read only the durable final name, including for nonterminal operations (3A
    inventories those names but does not hash their content). Never touch staging.
    Parent/root names are rebound and compared before returning the observation.
    """
    budget.check()
    root_fd = document_fd = check_fd = None
    try:
        root_fd = observation._open_root(root)
        root_before = observation._stamp(os.fstat(root_fd))
        budget.directory()
        name = str(operation.id_documento)
        try:
            document_fd = os.open(name, observation._flags(directory=True, noatime=True), dir_fd=root_fd)
        except FileNotFoundError:
            check_fd = observation._open_root(root)
            changed = root_before != observation._stamp(os.fstat(check_fd))
            return _Physical(observation._File(False, changed=changed), (root_before, None, None))
        document_before = observation._stamp(os.fstat(document_fd))
        if os.fstat(document_fd).st_mode & stat.S_IWOTH:
            raise observation._Stop(observation.INVALID_STORAGE_PATH)
        leaf = operation.ruta_prevista.split('/')[1]
        budget.entry()
        try:
            before = observation._stamp(os.stat(leaf, dir_fd=document_fd, follow_symlinks=False))
        except FileNotFoundError:
            before = None
        observed = observation._file(document_fd, leaf, budget, read_content=True)
        budget.check()
        try:
            after = observation._stamp(os.stat(leaf, dir_fd=document_fd, follow_symlinks=False))
        except FileNotFoundError:
            after = None
        document_after = observation._stamp(os.stat(name, dir_fd=root_fd, follow_symlinks=False))
        check_fd = observation._open_root(root)
        if before != after or document_before != document_after \
                or document_before != observation._stamp(os.fstat(document_fd)) \
                or root_before != observation._stamp(os.fstat(root_fd)) \
                or root_before != observation._stamp(os.fstat(check_fd)):
            observed.changed = True
        return _Physical(observed, (root_before, document_before, after))
    except FileNotFoundError:
        # Root/parent vanished after opening: absence cannot be trusted.
        return _Physical(observation._File(None, changed=True))
    except OSError as error:
        code = observation.INVALID_STORAGE_PATH if error.errno in (errno.ELOOP, errno.ENOTDIR) else observation.READ_ERROR
        return _Physical(observation._File(None, code))
    finally:
        for fd in (check_fd, document_fd, root_fd):
            if fd is not None:
                os.close(fd)


def _target(snapshot, actor_id, document_id, operation_id):
    if any(row.id_documento != document_id for row in (*snapshot.operations, *snapshot.versions)):
        raise observation._Stop(observation.SQL_UNCERTAIN)
    rows = [row for row in snapshot.operations
            if row.id_operacion == operation_id and row.id_usuario == actor_id]
    # Same denial for absent and foreign operations, even for business admins.
    if not rows:
        raise HTTPException(404, "Operación documental no disponible")
    if len(rows) != 1:
        raise observation._Stop(observation.INCONSISTENT_METADATA)
    return rows[0]


def _version(snapshot, operation):
    rows = [v for v in snapshot.versions if v.id_documento_version == operation.id_documento_version]
    if operation.estado != "confirmada":
        # A version at a nonterminal final name is inconsistent, not adoptable.
        return None, operation.id_documento_version is None and not any(
            v.ruta_almacenamiento == operation.ruta_prevista for v in snapshot.versions)
    if len(rows) != 1:
        return None, False
    version = rows[0]
    valid = all(getattr(version, name) == getattr(operation, name)
                for name in ("id_documento", "hash_sha256", "tamano_bytes", "nombre_original", "tipo_mime")) \
        and version.id_usuario_carga == operation.id_usuario \
        and version.ruta_almacenamiento == operation.ruta_prevista \
        and operation.identidad_archivo is not None
    return version, valid


def _incomplete(code, samples=0):
    # No stale authorization or partially observed operation details escape.
    return RecoveryPlan(None, None, None, None, (code,), "RETRY_AUTHORIZED_EVALUATION",
                        (("sql_samples", samples), ("read_only", True)), blocked_reason=code)


def _plan(operation, version, first, last, physical, key):
    file = physical.file
    diagnostics = []
    if file.code:
        diagnostics.append(file.code)
    elif file.found is False:
        diagnostics.append(observation.MISSING_FILE)
    elif file.found is not True:
        diagnostics.append(observation.ACTIVE_OR_UNCERTAIN_OPERATION)
    else:
        if file.size != operation.tamano_bytes:
            diagnostics.append(observation.SIZE_MISMATCH)
        if file.digest is None:
            diagnostics.append(observation.ACTIVE_OR_UNCERTAIN_OPERATION)
        elif not hmac.compare_digest(file.digest, operation.hash_sha256):
            diagnostics.append(observation.HASH_MISMATCH)
        if operation.identidad_archivo is None:
            diagnostics.append(observation.INCONSISTENT_METADATA)
        elif file.identity != operation.identidad_archivo:
            diagnostics.append(observation.FILE_IDENTITY_MISMATCH)
    result = None
    action, blocked = "MANUAL_REVIEW_ONLY", None
    if operation.estado == "confirmada" and not diagnostics:
        diagnostics.append(EXISTING_CONFIRMATION)
        action = "RETURN_EXISTING_RESULT"
        result = ExistingResult(operation.id_documento, version.id_documento_version)
    elif operation.estado == "rechazada":
        diagnostics.append(observation.REJECTED)
        action, blocked = "KEEP_TERMINAL_RESULT", "IMMUTABLE_TERMINAL_RESULT"
    elif operation.estado in ("pendiente", "requiere_reconciliacion"):
        diagnostics.append(observation.PENDING if operation.estado == "pendiente" else observation.RECONCILIATION_REQUIRED)
        if file.found is True and file.code is None:
            diagnostics.append(PUBLISHED_WITHOUT_CONFIRMATION)
        diagnostics.append(observation.ACTIVE_OR_UNCERTAIN_OPERATION)
        action, blocked = "WAIT_AND_REVIEW", "NO_WRITER_QUIESCENCE_OR_COMMIT_PROOF"
    else:
        blocked = "PHYSICAL_INCIDENCE_REQUIRES_INTERVENTION"
    token_input = repr((first, last, physical.stamps, file.identity, file.digest,
                        operation.hash_sha256, operation.ruta_prevista)).encode()
    token = hmac.new(key, token_input, hashlib.sha256).hexdigest()
    evidence = (("sql_samples", 2), ("physical_checks", 2), ("read_only", True),
                ("file_observed", file.found is True), ("stable_observation", True),
                ("abandonment_proven", False))
    return RecoveryPlan(str(operation.id_operacion), operation.id_documento, operation.estado,
                        operation.id_documento_version, tuple(sorted(set(diagnostics))), action,
                        evidence, blocked_reason=blocked, existing_result=result,
                        observation_token=token, complete=True)


def _evaluate(engine, actor_id, document_id, operation_id, root, key, limits, cancel):
    budget = observation._Budget(limits, cancel)
    samples = 0
    try:
        budget.check()
        first = observation._snapshot(engine, actor_id, (document_id,), limits, budget)
        samples = 1
        operation = _target(first, actor_id, document_id, operation_id)
        if operation.estado not in ("pendiente", "confirmada", "rechazada", "requiere_reconciliacion") \
                or not observation._metadata_valid(operation):
            raise observation._Stop(observation.INCONSISTENT_METADATA)
        if not observation._valid_operation_paths(operation):
            raise observation._Stop(observation.INVALID_STORAGE_PATH)
        _, valid = _version(first, operation)
        if not valid:
            raise observation._Stop(observation.INCONSISTENT_METADATA)
        before = _physical(root, operation, budget)
        budget.check()
        last = observation._snapshot(engine, actor_id, (document_id,), limits, budget)
        samples = 2
        # Reauthorize even after a failed physical read. Never emit stale scope.
        try:
            current = _target(last, actor_id, document_id, operation_id)
        except HTTPException:
            # Scope was reauthorized, but the owned row vanished or changed
            # ownership. Return no previous IDs/state as a recoverable result.
            return _incomplete(observation.ACTIVE_OR_UNCERTAIN_OPERATION, samples)
        if first != last or operation != current or before.file.changed:
            return _incomplete(observation.ACTIVE_OR_UNCERTAIN_OPERATION, samples)
        version, valid = _version(last, current)
        if not valid:
            raise observation._Stop(observation.INCONSISTENT_METADATA)
        after = _physical(root, current, budget)
        budget.check()
        if after.file.changed or before != after:
            return _incomplete(observation.ACTIVE_OR_UNCERTAIN_OPERATION, samples)
        if after.file.code == observation.READ_ERROR or after.file.found is None:
            return _incomplete(after.file.code or observation.ACTIVE_OR_UNCERTAIN_OPERATION, samples)
        return _plan(current, version, first, last, after, key)
    except HTTPException:
        raise
    except observation._Stop as stop:
        return _incomplete(stop.code, samples)
    except Exception as error:
        sqlstate = getattr(getattr(error, "orig", None), "pgcode", None)
        code = LOCK_TIMEOUT if sqlstate == "55P03" else SQL_TIMEOUT if sqlstate == "57014" else observation.SQL_UNCERTAIN
        return _incomplete(code, samples)


async def evaluate_recovery(engine, actor_id, document_id, operation_id, root, *,
                            audit_key, limits=observation.Limits(), dry_run=True):
    """Return a fresh, private plan or an existing result reference. Never apply.

    Caller must authenticate actor_id; both snapshots recheck active credentials,
    canonical read authorization and operation ownership. No Session crosses a
    thread. Cancellation drains the worker; deadlines are cooperative, not hard
    kernel/pool time bounds. complete means inspection completed, NOT repair-safe.
    """
    if dry_run is not True:
        raise ValueError("Only dry-run recovery evaluation is available")
    if type(actor_id) is not int or actor_id <= 0 or type(document_id) is not int or document_id <= 0:
        raise ValueError("Invalid authorized scope")
    if not isinstance(audit_key, bytes) or len(audit_key) < 32:
        raise ValueError("Private audit key required")
    if not isinstance(limits, observation.Limits):
        raise ValueError("Invalid recovery limits")
    try:
        operation_id = uuid.UUID(str(operation_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid operation identifier") from None
    cancel = threading.Event()
    worker = asyncio.create_task(run_in_threadpool(_evaluate, engine, actor_id,
        document_id, operation_id, root, audit_key, limits, cancel))
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        cancel.set()
        with CancelScope(shield=True):
            while not worker.done():
                try:
                    await asyncio.shield(worker)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
        if not worker.cancelled():
            worker.exception()
        raise
