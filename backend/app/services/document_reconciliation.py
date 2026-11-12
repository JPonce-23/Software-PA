"""Bounded read-only observations, not recovery or an absence/abandonment proof.

Internal API: caller supplies an authenticated actor ID, explicit document scope,
a trusted upload root and a private audit key. No public endpoint is registered.
Two independent primary-DB snapshots surround descriptor-based filesystem reads.
"""
import asyncio
from dataclasses import dataclass, field
import errno
import hashlib
import hmac
import os
from pathlib import Path
import re
import stat
import threading
import time
import uuid
from types import SimpleNamespace

from anyio import CancelScope
from fastapi import HTTPException
from sqlalchemy import event, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, raiseload
from starlette.concurrency import run_in_threadpool

from .. import models
from .access import require_document_access

CONSISTENT = "CONSISTENT"
PENDING = "PENDING"
RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
ORPHAN_FILE = "ORPHAN_FILE"
MISSING_FILE = "MISSING_FILE"
HASH_MISMATCH = "HASH_MISMATCH"
SIZE_MISMATCH = "SIZE_MISMATCH"
INVALID_STORAGE_PATH = "INVALID_STORAGE_PATH"
ACTIVE_OR_UNCERTAIN_OPERATION = "ACTIVE_OR_UNCERTAIN_OPERATION"
REJECTED = "REJECTED"
INCONSISTENT_METADATA = "INCONSISTENT_METADATA"
FILE_IDENTITY_MISMATCH = "FILE_IDENTITY_MISMATCH"
STAGING_INCOMPLETE = "STAGING_INCOMPLETE"
READ_ERROR = "READ_ERROR"
SQL_UNCERTAIN = "SQL_UNCERTAIN"
SCAN_LIMIT_REACHED = "SCAN_LIMIT_REACHED"
SCAN_INTERRUPTED = "SCAN_INTERRUPTED"

FINAL = re.compile(r'(?:op-[0-9a-f]{32}|[0-9]{4,}-[0-9a-f]{32})\.(?:pdf|docx|xlsx|jpe?g|png)\Z')
STAGE = re.compile(r'\.pending-[0-9a-f]{32}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')


@dataclass(frozen=True)
class Limits:
    max_documents: int = 20
    max_operations: int = 200
    max_versions: int = 400
    max_authorization_rows: int = 200
    max_entries: int = 500
    max_directories: int = 60
    max_bytes: int = 64 * 1024 * 1024
    max_file_bytes: int = 20 * 1024 * 1024
    seconds: float = 10.0
    statement_ms: int = 3000
    lock_ms: int = 500

    def __post_init__(self):
        caps = dict(max_documents=100, max_operations=5000, max_versions=10000,
            max_entries=20000, max_directories=1000, max_authorization_rows=2000, max_bytes=1024**3,
            max_file_bytes=100*1024**2, statement_ms=10000, lock_ms=2000)
        for name, cap in caps.items():
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= cap:
                raise ValueError("Invalid reconciliation limit")
        if type(self.seconds) not in (int, float) or not 0 < self.seconds <= 60:
            raise ValueError("Invalid reconciliation deadline")


@dataclass(frozen=True)
class Finding:
    code: str
    document_id: int | None
    operation_id: str | None = None
    version_id: int | None = None
    entry_id: str | None = None
    cause: str = ""
    recommendation: str = "MANUAL_REVIEW_ONLY"
    evidence: tuple = ()


@dataclass(frozen=True)
class Report:
    findings: tuple[Finding, ...]
    complete: bool
    documents: tuple[int, ...]
    entries_examined: int
    bytes_read: int
    sql_samples: int
    read_only: bool = True
    format_version: str = "ss12-observation-v1"


@dataclass(frozen=True)
class _Operation:
    id_operacion: uuid.UUID
    id_documento: int
    id_usuario: int
    estado: str
    ruta_prevista: str = field(repr=False)
    ruta_staging: str = field(repr=False)
    hash_sha256: str = field(repr=False)
    tamano_bytes: int
    nombre_original: str = field(repr=False)
    tipo_mime: str | None = field(repr=False)
    id_documento_version: int | None
    identidad_archivo: tuple | None
    actualizado_en: object


@dataclass(frozen=True)
class _Version:
    id_documento_version: int
    id_documento: int
    id_usuario_carga: int
    ruta_almacenamiento: str = field(repr=False)
    hash_sha256: str = field(repr=False)
    tamano_bytes: int
    nombre_original: str = field(repr=False)
    tipo_mime: str | None = field(repr=False)


@dataclass(frozen=True)
class _Snapshot:
    operations: tuple[_Operation, ...]
    versions: tuple[_Version, ...]


@dataclass
class _File:
    found: bool | None
    code: str | None = None
    size: int | None = None
    identity: tuple | None = None
    digest: str | None = field(default=None, repr=False)
    changed: bool = False
    error_number: int | None = None


@dataclass
class _Tree:
    files: dict = field(default_factory=dict, repr=False)
    stages: dict = field(default_factory=dict, repr=False)
    entries: list = field(default_factory=list, repr=False)
    changed_documents: set = field(default_factory=set)


class _Stop(Exception):
    def __init__(self, code): self.code = code


class _Budget:
    def __init__(self, limits, cancel):
        self.limits, self.cancel = limits, cancel
        self.deadline = time.monotonic() + limits.seconds
        self.entries = self.bytes = self.directories = self.authorization_rows = 0

    def check(self):
        if self.cancel.is_set(): raise _Stop(SCAN_INTERRUPTED)
        if time.monotonic() >= self.deadline: raise _Stop(SCAN_LIMIT_REACHED)

    def entry(self):
        self.check()
        if self.entries >= self.limits.max_entries: raise _Stop(SCAN_LIMIT_REACHED)
        self.entries += 1

    def directory(self):
        self.check()
        if self.directories >= self.limits.max_directories: raise _Stop(SCAN_LIMIT_REACHED)
        self.directories += 1


def _authorize(db, actor_id, documents, budget):
    # Retain canonical RBAC/scope semantics, but cap all authorization results
    # and disable implicit eager/lazy relationship loads during those queries.
    def bounded(state):
        budget.check()
        if not state.is_select: raise _Stop(SQL_UNCERTAIN)
        if getattr(state.statement, "_for_update_arg", None) is not None: raise _Stop(SQL_UNCERTAIN)
        remaining = budget.limits.max_authorization_rows - budget.authorization_rows
        if remaining <= 0: raise _Stop(SCAN_LIMIT_REACHED)
        statement = state.statement.limit(remaining + 1)
        if any(d.get("entity") is not None and d.get("expr") is d.get("entity")
               for d in getattr(statement, "column_descriptions", ())):
            statement = statement.options(raiseload("*"))
        frozen = state.invoke_statement(statement).freeze()
        count = sum(1 for _ in frozen())
        if count > remaining: raise _Stop(SCAN_LIMIT_REACHED)
        budget.authorization_rows += count
        return frozen()
    event.listen(db, "do_orm_execute", bounded, retval=True)
    try:
        row = db.execute(select(models.Usuario.id_usuario, models.Usuario.rol).where(
            models.Usuario.id_usuario == actor_id, models.Usuario.activo.is_(True)).limit(1)).first()
        if row is None: raise HTTPException(401, "No se pudieron validar las credenciales")
        actor = SimpleNamespace(id_usuario=row.id_usuario, rol=row.rol)
        if actor.rol not in {"admin", "operador", "visualizador", "geografo"}:
            raise HTTPException(403, "Operación no permitida para este rol")
        for document_id in documents:
            budget.check()
            require_document_access(db, actor, document_id, mode="read")
    finally:
        event.remove(db, "do_orm_execute", bounded)


def _snapshot(engine, actor_id, documents, limits, budget):
    if not isinstance(engine, Engine) or engine.dialect.name != "postgresql":
        raise _Stop(SQL_UNCERTAIN)
    with Session(bind=engine, autoflush=False, expire_on_commit=False) as db:
        # Per-connection options; no shared/request Session or engine mutation.
        db.connection(execution_options={"isolation_level": "REPEATABLE READ", "postgresql_readonly": True})
        budget.check()
        db.execute(text("SELECT set_config('lock_timeout',:lock,true), "
            "set_config('statement_timeout',:statement,true)"),
            {"lock": f"{limits.lock_ms}ms", "statement": f"{limits.statement_ms}ms"})
        mode = db.execute(text("SELECT current_setting('transaction_read_only'), "
            "current_setting('transaction_isolation'), pg_is_in_recovery()" )).one()
        if tuple(mode) != ("on", "repeatable read", False): raise _Stop(SQL_UNCERTAIN)
        _authorize(db, actor_id, documents, budget)
        budget.check()
        op = models.DocumentoOperacion
        # Other actors' rows are private protective references; never returned.
        op_rows = db.execute(select(*[getattr(op, name) for name in _Operation.__dataclass_fields__])
            .where(op.id_documento.in_(documents)).order_by(op.id_documento, op.id_operacion)
            .limit(limits.max_operations + 1)).mappings().all()
        if len(op_rows) > limits.max_operations: raise _Stop(SCAN_LIMIT_REACHED)
        budget.check()
        version = models.DocumentoVersion
        version_rows = db.execute(select(*[getattr(version, name) for name in _Version.__dataclass_fields__])
            .where(version.id_documento.in_(documents)).order_by(version.id_documento, version.id_documento_version)
            .limit(limits.max_versions + 1)).mappings().all()
        if len(op_rows) > limits.max_operations or len(version_rows) > limits.max_versions:
            raise _Stop(SCAN_LIMIT_REACHED)
        operations = []
        for row in op_rows:
            values = dict(row)
            identity = values["identidad_archivo"]
            values["identidad_archivo"] = None if identity is None else (identity["device"], identity["inode"])
            operations.append(_Operation(**values))
        return _Snapshot(tuple(operations), tuple(_Version(**dict(row)) for row in version_rows))
        # Session close rolls back its read-only TX. Never flush/commit/add/lock.


def _stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
        info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)


def _flags(directory=False, noatime=False):
    names = ["O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK"] + (["O_DIRECTORY"] if directory else [])
    if noatime: names.append("O_NOATIME")
    if not all(hasattr(os, name) for name in names): raise _Stop(READ_ERROR)
    return os.O_RDONLY | sum(getattr(os, name) for name in names)


def _open_root(root):
    # No resolve(), mkdir(), symlink traversal or root-wide enumeration.
    try: path = Path(root)
    except (ValueError, TypeError): raise _Stop(INVALID_STORAGE_PATH) from None
    if "\x00" in str(path): raise _Stop(INVALID_STORAGE_PATH)
    if not path.is_absolute() or len(path.parts) < 2 or ".." in path.parts or len(path.parts) > 64:
        raise _Stop(INVALID_STORAGE_PATH)
    fd = os.open("/", _flags(directory=True))
    try:
        for i, part in enumerate(path.parts[1:], 1):
            child = os.open(part, _flags(directory=True, noatime=i == len(path.parts)-1), dir_fd=fd)
            os.close(fd); fd = child
        if os.fstat(fd).st_mode & stat.S_IWOTH: raise _Stop(INVALID_STORAGE_PATH)
        return fd
    except BaseException:
        os.close(fd); raise


def _valid_name(name):
    return FINAL.fullmatch(name) is not None and (name.startswith("op-") or bool(name.split("-")[0].strip("0")))


def _valid_path(path, document_id):
    return isinstance(path, str) and "\\" not in path and "\x00" not in path \
        and path.startswith(str(document_id) + "/") and path.count("/") == 1 \
        and _valid_name(path.split("/")[1])


def _valid_operation_paths(op):
    try: identity = uuid.UUID(str(op.id_operacion)).hex
    except (TypeError, ValueError, AttributeError): return False
    return _valid_path(op.ruta_prevista, op.id_documento) \
        and op.ruta_prevista.split("/")[1].startswith("op-" + identity + ".") \
        and op.ruta_staging == f"{op.id_documento}/.pending-{identity}/payload"


def _metadata_valid(version):
    return type(version.tamano_bytes) is int and version.tamano_bytes > 0 \
        and isinstance(version.hash_sha256, str) and SHA.fullmatch(version.hash_sha256) is not None


def _names(fd, budget):
    values = []
    with os.scandir(fd) as entries:
        for entry in entries:
            budget.entry(); values.append(entry.name)
    return sorted(values)


def _file(parent, name, budget, read_content=False):
    fd = None
    seen = False
    try:
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        seen = True
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            return _File(True, INVALID_STORAGE_PATH)
        observed = _File(True, size=before.st_size, identity=(before.st_dev, before.st_ino))
        fd = os.open(name, _flags(noatime=True), dir_fd=parent)
        opened = os.fstat(fd)
        if _stamp(before) != _stamp(opened): observed.changed = True; return observed
        if read_content:
            if before.st_size > budget.limits.max_file_bytes: raise _Stop(SCAN_LIMIT_REACHED)
            checksum, remaining = hashlib.sha256(), before.st_size
            while remaining:
                budget.check()
                allowed = min(65536, remaining, budget.limits.max_bytes - budget.bytes)
                if allowed <= 0: raise _Stop(SCAN_LIMIT_REACHED)
                block = os.read(fd, allowed)
                if not block: observed.changed = True; return observed
                budget.bytes += len(block); remaining -= len(block); checksum.update(block)
            observed.digest = checksum.hexdigest()
        after = os.fstat(fd)
        entry = os.stat(name, dir_fd=parent, follow_symlinks=False)
        observed.changed = _stamp(before) != _stamp(after) or _stamp(after) != _stamp(entry)
        return observed
    except FileNotFoundError:
        return _File(None, changed=True) if seen else _File(False)
    except OSError as error:
        return _File(None, INVALID_STORAGE_PATH if error.errno in (errno.ELOOP, errno.ENOTDIR) else READ_ERROR,
            error_number=error.errno)
    finally:
        if fd is not None: os.close(fd)


def _stage(parent, name, budget):
    fd = None
    try:
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISDIR(before.st_mode): return (INVALID_STORAGE_PATH, False, False)
        budget.directory()
        fd = os.open(name, _flags(directory=True, noatime=True), dir_fd=parent)
        if _stamp(before) != _stamp(os.fstat(fd)): return (ACTIVE_OR_UNCERTAIN_OPERATION, False, True)
        names = _names(fd, budget)
        payload = _file(fd, "payload", budget) if "payload" in names else _File(False)
        changed = _stamp(before) != _stamp(os.fstat(fd)) or _stamp(before) != _stamp(os.stat(name, dir_fd=parent, follow_symlinks=False))
        code = payload.code or (INVALID_STORAGE_PATH if any(n != "payload" for n in names) else
            STAGING_INCOMPLETE if not payload.found else ACTIVE_OR_UNCERTAIN_OPERATION)
        return code, bool(payload.found), changed or payload.changed
    except FileNotFoundError: return (ACTIVE_OR_UNCERTAIN_OPERATION, False, True)
    except OSError as error: return (INVALID_STORAGE_PATH if error.errno in (errno.ELOOP, errno.ENOTDIR) else READ_ERROR, False, False)
    finally:
        if fd is not None: os.close(fd)


def _tree(root, documents, first, budget):
    result = _Tree()
    expected = {v.ruta_almacenamiento for v in first.versions if _valid_path(v.ruta_almacenamiento, v.id_documento)}
    root_fd = _open_root(root)
    try:
        root_before = _stamp(os.fstat(root_fd))
        for document_id in documents:
            budget.directory(); fd = None
            try:
                fd = os.open(str(document_id), _flags(directory=True, noatime=True), dir_fd=root_fd)
                before = _stamp(os.fstat(fd))
                if os.fstat(fd).st_mode & stat.S_IWOTH: raise _Stop(INVALID_STORAGE_PATH)
                for name in _names(fd, budget):
                    budget.check(); relative = f"{document_id}/{name}"
                    if _valid_name(name):
                        result.files[relative] = _file(fd, name, budget, read_content=relative in expected)
                    elif STAGE.fullmatch(name):
                        result.stages[relative + "/payload"] = _stage(fd, name, budget)
                    else:
                        result.entries.append((document_id, relative, INVALID_STORAGE_PATH))
                # Probe SQL references not in enumeration: missing vs unknown.
                for relative in sorted(expected):
                    if relative.startswith(str(document_id) + "/") and relative not in result.files:
                        budget.entry(); result.files[relative] = _file(fd, relative.split("/")[1], budget, read_content=True)
                current = os.stat(str(document_id), dir_fd=root_fd, follow_symlinks=False)
                if before != _stamp(os.fstat(fd)) or before != _stamp(current): result.changed_documents.add(document_id)
            except FileNotFoundError:
                if fd is not None: result.changed_documents.add(document_id)
                else:
                    for relative in expected:
                        if relative.startswith(str(document_id) + "/"): result.files[relative] = _File(False)
            except OSError as error:
                result.entries.append((document_id, str(document_id), INVALID_STORAGE_PATH if error.errno in (errno.ELOOP, errno.ENOTDIR) else READ_ERROR))
                result.changed_documents.add(document_id)
            finally:
                if fd is not None: os.close(fd)
        # Check the named root through the same no-follow component walk again.
        check = _open_root(root)
        try:
            if root_before != _stamp(os.fstat(root_fd)) or root_before != _stamp(os.fstat(check)):
                result.changed_documents.update(documents)
        finally: os.close(check)
        return result
    finally: os.close(root_fd)


def _findings(actor_id, documents, first, last, tree, audit_key):
    findings = []
    def add(code, doc, op=None, version=None, path=None, cause="", action="MANUAL_REVIEW_ONLY", **evidence):
        entry = hmac.new(audit_key, os.fsencode(path), hashlib.sha256).hexdigest() if path is not None else None
        findings.append(Finding(code, doc, str(op.id_operacion) if op is not None and op.id_usuario == actor_id else None,
            version.id_documento_version if version is not None else None, entry, cause, action, tuple(sorted(evidence.items()))))
    busy = set(tree.changed_documents)
    for doc in documents:
        if tuple(o for o in first.operations if o.id_documento == doc) != tuple(o for o in last.operations if o.id_documento == doc) \
                or tuple(v for v in first.versions if v.id_documento == doc) != tuple(v for v in last.versions if v.id_documento == doc): busy.add(doc)
    versions = {v.id_documento_version: v for v in last.versions}
    protected = {p for op in last.operations for p in (op.ruta_prevista, op.ruta_staging)}
    foreign = {p for op in last.operations if op.id_usuario != actor_id for p in (op.ruta_prevista, op.ruta_staging)}
    associated = {o.id_documento_version: o for o in last.operations if o.estado == "confirmada"}
    bad_versions = set()
    for op in last.operations:
        if op.id_usuario != actor_id: continue
        doc = op.id_documento
        if not _valid_operation_paths(op):
            add(INVALID_STORAGE_PATH, doc, op, cause="invalid_durable_paths")
            if op.id_documento_version in versions: bad_versions.add(op.id_documento_version)
            continue
        observed = tree.files.get(op.ruta_prevista)
        stage = tree.stages.get(op.ruta_staging)
        if op.estado in ("pendiente", "requiere_reconciliacion"):
            add(PENDING if op.estado == "pendiente" else RECONCILIATION_REQUIRED, doc, op,
                cause="durable_nonterminal_state", action="WAIT_AND_REVIEW", final_observed=bool(observed and observed.found), staging_observed=stage is not None)
            add(ACTIVE_OR_UNCERTAIN_OPERATION, doc, op, cause="no_lease_or_quiescence_proof", action="DO_NOT_RESUME_OR_DELETE")
            if observed and observed.found and observed.identity is not None and op.identidad_archivo is not None \
                    and observed.identity != op.identidad_archivo and not observed.changed and doc not in busy:
                add(FILE_IDENTITY_MISMATCH, doc, op, path=op.ruta_prevista,
                    cause="nonterminal_identity_observation_differs", action="DO_NOT_RESUME_OR_DELETE", uncertain=True)
        elif op.estado == "rechazada":
            add(REJECTED, doc, op, cause="immutable_rejection", action="KEEP_TERMINAL_RESULT")
            if observed and observed.found and doc not in busy and op.ruta_prevista not in {v.ruta_almacenamiento for v in last.versions}:
                add(ORPHAN_FILE, doc, op, path=op.ruta_prevista, cause="unreferenced_terminal_candidate", candidate=True)
        elif op.estado == "confirmada":
            version = versions.get(op.id_documento_version)
            consistent = version is not None and all(getattr(op, n) == getattr(version, n) for n in
                ("id_documento", "hash_sha256", "tamano_bytes", "nombre_original", "tipo_mime")) \
                and op.id_usuario == version.id_usuario_carga and op.ruta_prevista == version.ruta_almacenamiento
            if not consistent or op.identidad_archivo is None:
                add(INCONSISTENT_METADATA, doc, op, cause="confirmed_result_reference_mismatch")
                if version is not None: bad_versions.add(version.id_documento_version)
        else: add(INCONSISTENT_METADATA, doc, op, cause="unknown_durable_state")
    for doc in sorted(busy): add(ACTIVE_OR_UNCERTAIN_OPERATION, doc, cause="sql_or_directory_changed", action="REPEAT_OBSERVATION")
    for version in last.versions:
        doc, path = version.id_documento, version.ruta_almacenamiento
        op = associated.get(version.id_documento_version)
        if not _valid_path(path, doc): add(INVALID_STORAGE_PATH, doc, op, version, cause="invalid_version_path"); continue
        if not _metadata_valid(version): add(INCONSISTENT_METADATA, doc, op, version, cause="invalid_version_metadata"); continue
        if doc in busy: continue
        observed = tree.files.get(path)
        if observed is None or observed.changed:
            add(ACTIVE_OR_UNCERTAIN_OPERATION, doc, op, version, path, cause="entry_unstable_or_not_observed", action="REPEAT_OBSERVATION"); continue
        if observed.code: add(observed.code, doc, op, version, path, cause="entry_not_safely_readable", error_number=observed.error_number); continue
        if observed.found is False: add(MISSING_FILE, doc, op, version, path, cause="absent_in_bounded_observation", action="VERIFY_BACKUP_AND_REPEAT"); continue
        failed = version.id_documento_version in bad_versions
        if path.split("/")[1].startswith("op-") and op is None:
            add(INCONSISTENT_METADATA, doc, version=version, path=path, cause="operation_link_missing"); failed = True
        if observed.size != version.tamano_bytes:
            add(SIZE_MISMATCH, doc, op, version, path, cause="stored_size_differs", actual_size=observed.size); failed = True
        if observed.digest is None:
            add(ACTIVE_OR_UNCERTAIN_OPERATION, doc, op, version, path, cause="hash_not_observed", action="REPEAT_OBSERVATION"); failed = True
        elif not hmac.compare_digest(observed.digest, version.hash_sha256):
            add(HASH_MISMATCH, doc, op, version, path, cause="stored_hash_differs"); failed = True
        if op is not None and op.id_usuario == actor_id and op.identidad_archivo != observed.identity:
            add(FILE_IDENTITY_MISMATCH, doc, op, version, path, cause="durable_physical_identity_differs"); failed = True
        if not failed:
            add(CONSISTENT, doc, op, version, path, cause="stable_version_and_file", action="NONE",
                operation_scope_checked=bool(op is not None and op.id_usuario == actor_id))
    referenced = {v.ruta_almacenamiento for v in last.versions}
    for path, observed in sorted(tree.files.items()):
        doc = int(path.split("/")[0])
        if path in protected or path in referenced or doc in busy: continue
        if observed.changed: add(ACTIVE_OR_UNCERTAIN_OPERATION, doc, path=path, cause="unreferenced_entry_changed", action="REPEAT_OBSERVATION")
        elif observed.code: add(observed.code, doc, path=path, cause="unreferenced_entry_unsafe")
        elif observed.found: add(ORPHAN_FILE, doc, path=path, cause="no_reference_in_two_primary_samples", candidate=True, samples=2)
    for path, (code, payload, changed) in sorted(tree.stages.items()):
        if path in foreign: continue
        doc = int(path.split("/")[0])
        owner = next((o for o in last.operations if o.ruta_staging == path and o.id_usuario == actor_id), None)
        add(ACTIVE_OR_UNCERTAIN_OPERATION if changed else code, doc, owner, path=path,
            cause="staging_is_not_abandonment_proof", action="DO_NOT_RESUME_OR_DELETE", payload_observed=payload)
    for doc, path, code in tree.entries:
        if path not in foreign: add(code, doc, path=path, cause="unexpected_or_unreadable_entry")
    key = lambda f: (f.document_id or 0, f.operation_id or "", f.version_id or 0, f.entry_id or "", f.code, f.cause)
    return tuple(sorted(set(findings), key=key)), not busy


def _inspect(engine, actor_id, documents, root, audit_key, limits, cancel):
    budget = _Budget(limits, cancel)
    samples = 0
    try:
        budget.check()
        first = _snapshot(engine, actor_id, documents, limits, budget); samples = 1
        if any(row.id_documento not in documents for row in (*first.operations, *first.versions)): raise _Stop(SQL_UNCERTAIN)
        budget.check()
        observed = _tree(root, documents, first, budget)
        budget.check()
        # New TX reauthorizes and observes commits that may have raced the scan.
        last = _snapshot(engine, actor_id, documents, limits, budget); samples = 2
        if any(row.id_documento not in documents for row in (*last.operations, *last.versions)): raise _Stop(SQL_UNCERTAIN)
        budget.check()
        findings, stable = _findings(actor_id, documents, first, last, observed, audit_key)
        complete = stable and not any(f.code in (READ_ERROR, ACTIVE_OR_UNCERTAIN_OPERATION) for f in findings)
        return Report(findings, complete, documents, budget.entries, budget.bytes, samples)
    except HTTPException: raise  # No filesystem/results returned after a denial.
    except _Stop as stop: code = stop.code
    except OSError as error: code = INVALID_STORAGE_PATH if error.errno in (errno.ELOOP, errno.ENOTDIR) else READ_ERROR
    except Exception: code = SQL_UNCERTAIN  # Never expose DB/driver/path diagnostics.
    # A failed/partial observation cannot prove missing rows or safe orphans.
    return Report((Finding(code, None, cause="observation_incomplete", recommendation="REPEAT_AUTHORIZED_OBSERVATION"),),
        False, (), budget.entries, budget.bytes, samples)


async def reconcile_documents(engine, actor_id, document_ids, root, *, audit_key, limits=Limits()):
    """Observe only the explicit authorized documents. No repair/apply option.

    audit_key is caller-managed private material (>=32 bytes); findings contain
    opaque reproducible entry IDs, never root/path/name/content hashes. Deadline
    checks are cooperative: a stalled kernel filesystem call may exceed them.
    """
    if type(actor_id) is not int or actor_id <= 0: raise ValueError("Invalid actor")
    if not isinstance(audit_key, bytes) or len(audit_key) < 32: raise ValueError("Private audit key required")
    # Consume at most max_documents+1; do not exhaust an unbounded iterable.
    values = []
    for value in document_ids:
        if type(value) is not int or value <= 0: raise ValueError("Invalid document scope")
        values.append(value)
        if len(values) > limits.max_documents: raise ValueError("Document scope limit exceeded")
    documents = tuple(sorted(set(values)))
    if not documents: raise ValueError("Explicit document scope required")
    cancel = threading.Event()
    worker = asyncio.create_task(run_in_threadpool(_inspect, engine, actor_id, documents, root, audit_key, limits, cancel))
    try: return await asyncio.shield(worker)
    except asyncio.CancelledError:
        cancel.set()
        with CancelScope(shield=True):
            while not worker.done():
                try: await asyncio.shield(worker)
                except asyncio.CancelledError: continue
                except Exception: break
        if not worker.cancelled(): worker.exception()
        raise
