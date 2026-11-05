"""Real store_version, SQL Session doubles and real owned POSIX files.

No PostgreSQL connection, Docker, dotenv, app startup or institution credentials.
PostgreSQL concurrency is covered separately by the explicit disposable QA suite.
"""
import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
import io
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

import anyio

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests"))
from _document_samples import minimal_pdf
from _document_service_support import document_service
from _document_journal_doubles import JournalDouble
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError, OperationalError, TimeoutError as SQLTimeoutError
from sqlalchemy.orm import Session, make_transient_to_detached
from fastapi import HTTPException, UploadFile

service = document_service()


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="ss12-service-unit-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {"UPLOAD_ROOT": str(self.root)}).start()
        self.request = MagicMock(spec=Session)
        self.check = MagicMock(spec=Session)
        self.tx = MagicMock(spec=Session)
        for session in [self.check, self.tx]:
            session.__enter__.return_value = session
            session.__exit__.return_value = False
        self.factory = MagicMock(side_effect=[self.check, self.tx])
        self.session_builder = patch.object(service, "_upload_sessions", return_value=self.factory).start()
        self.actor = service.models.Usuario(id_usuario=3, rol="admin", activo=True)
        make_transient_to_detached(self.actor)
        self.actor_lookup = patch.object(service, "_upload_actor", return_value=self.actor).start()
        self.access = patch.object(service, "require_document_access").start()
        self.validator = patch.object(service, "validate_document", return_value="application/pdf").start()
        self.events = patch.object(service, "storage_event").start()
        self.journal = JournalDouble()
        patch.object(service, "operations", self.journal).start()
        self.tx.connection.return_value.get_isolation_level.return_value = "READ COMMITTED"
        self.tx.execute.return_value.scalar_one_or_none.return_value = 7
        self.query = self.tx.query.return_value
        self.query.filter.return_value = self.query
        self.query.first.return_value = None
        self.query.scalar.return_value = 0
        self.tx.refresh.side_effect = self.populate_response

    def populate_response(self, version):
        version.id_documento_version = 1
        version.fecha_carga = datetime.now(timezone.utc)

    def upload(self):
        return UploadFile(io.BytesIO(minimal_pdf()), filename="../synthetic.pdf")

    def run_upload(self):
        return asyncio.run(service.store_version(self.request, 7, self.upload(), self.actor))

    def files(self):
        return list(self.root.rglob("*.pdf"))

    def test_normal_upload_response_and_owned_sessions(self):
        version = self.run_upload()
        self.assertEqual((version.numero_version, version.nombre_original), (1, "synthetic.pdf"))
        self.assertEqual(self.files()[0].read_bytes(), minimal_pdf())
        response = service.schemas.DocumentoVersionResponse.model_validate(version)
        self.assertEqual(response.id_documento_version, 1)
        self.access.assert_any_call(self.check, self.actor, 7, mode="capture")
        self.access.assert_any_call(self.tx, self.actor, 7, mode="capture")
        self.assertEqual(self.factory.call_count, 2)
        self.request.query.assert_not_called()
        self.tx.commit.assert_called_once()
        self.tx.connection.assert_called_once_with(execution_options={"isolation_level":"READ COMMITTED"})
        self.check.connection.assert_called_once_with(execution_options={"isolation_level":"READ COMMITTED"})
        self.assertFalse(list(self.root.rglob(".pending-*")))

    def test_staging_precedes_lock_flush_precedes_publication(self):
        observed = []
        real_stage = service.stage_document
        @contextmanager
        def stage(*args, **kwargs):
            with real_stage(*args, **kwargs) as staged:
                observed.append("staged")
                real_publish = staged.publish
                def publish(name):
                    observed.append("publish")
                    real_publish(name)
                staged.publish = publish
                yield staged
        def execute(statement, *args, **kwargs):
            if getattr(statement, "_for_update_arg", None) is not None:
                sql = str(statement.compile(dialect=postgresql.dialect()))
                self.assertIn("FOR UPDATE OF documento", sql)
                self.assertNotIn("JOIN", sql)
                observed.append("lock")
            return MagicMock(scalar_one_or_none=lambda: 7)
        self.tx.execute.side_effect = execute
        self.query.first.side_effect = lambda: observed.append("dedup")
        self.query.scalar.side_effect = lambda: (observed.append("max"), 0)[1]
        self.tx.flush.side_effect = lambda: observed.append("flush")
        self.tx.commit.side_effect = lambda: observed.append("commit")
        with patch.object(service, "stage_document", side_effect=stage):
            self.run_upload()
        self.assertEqual(observed, ["staged", "lock", "dedup", "max", "flush", "publish", "commit"])

    def test_all_blocking_work_on_same_worker_not_event_loop(self):
        loop_thread = threading.get_ident()
        observed = []
        self.validator.side_effect = lambda *a, **kw: (observed.append(threading.get_ident()), "application/pdf")[1]
        self.tx.flush.side_effect = lambda: observed.append(threading.get_ident())
        self.tx.commit.side_effect = lambda: observed.append(threading.get_ident())
        real_stage = service.stage_document
        @contextmanager
        def stage(*args, **kwargs):
            observed.append(threading.get_ident())
            with real_stage(*args, **kwargs) as staged: yield staged
        with patch.object(service, "stage_document", side_effect=stage): self.run_upload()
        self.assertEqual(len(set(observed)), 1)
        self.assertNotEqual(observed[0], loop_thread)

    def test_authorization_before_read_and_revalidated_under_lock(self):
        for deny_on in [1, 2]:
            with self.subTest(deny_on=deny_on):
                self.factory.side_effect = [self.check, self.tx]
                self.access.side_effect = [HTTPException(403, "denied")] if deny_on == 1 else [None, HTTPException(403, "revoked")]
                with self.assertRaises(HTTPException) as raised: self.run_upload()
                self.assertEqual(raised.exception.status_code, 403)
                self.assertFalse(self.files())
                self.tx.commit.assert_not_called()

    def test_inactive_or_changed_actor_rechecked(self):
        self.actor_lookup.side_effect = [self.actor, HTTPException(401, "inactive")]
        with self.assertRaises(HTTPException) as raised: self.run_upload()
        self.assertEqual(raised.exception.status_code, 401)
        self.tx.add.assert_not_called()
        self.assertFalse(self.files())

    def test_duplicate_after_lock_never_publishes_or_reads_max(self):
        self.query.first.return_value = service.models.DocumentoVersion(id_documento=7)
        with self.assertRaises(HTTPException) as raised: self.run_upload()
        self.assertEqual(raised.exception.status_code, 409)
        self.query.scalar.assert_not_called()
        self.tx.flush.assert_not_called()
        self.assertFalse(self.files())
        self.tx.rollback.assert_called_once()

    def test_integrity_error_before_publication_has_no_final_file(self):
        self.tx.flush.side_effect = IntegrityError("synthetic", {}, Exception("private driver detail"))
        with self.assertRaises(HTTPException) as raised: self.run_upload()
        self.assertEqual(raised.exception.status_code, 409)
        self.assertNotIn("private", raised.exception.detail)
        self.tx.commit.assert_not_called()
        self.assertFalse(self.files())

    def test_lock_deadlock_and_statement_timeouts_are_bounded_unpublished(self):
        for code in ["55P03", "40P01", "57014"]:
            with self.subTest(code=code):
                self.factory.side_effect = [self.check, self.tx]
                original = Exception("sensitive driver detail"); original.pgcode = code
                self.tx.execute.side_effect = OperationalError("synthetic", {}, original)
                with self.assertRaises(HTTPException) as raised: self.run_upload()
                self.assertEqual(raised.exception.status_code, 503)
                self.assertNotIn("sensitive", raised.exception.detail)
                self.assertFalse(self.files())

    def test_actual_isolation_is_checked_before_parent_lock(self):
        self.tx.connection.return_value.get_isolation_level.return_value = "REPEATABLE READ"
        with self.assertRaises(HTTPException) as raised: self.run_upload()
        self.assertEqual(raised.exception.status_code, 503)
        self.tx.execute.assert_not_called()
        self.assertFalse(self.files())

    def test_connection_pool_timeout_is_transient_without_publication(self):
        self.tx.connection.side_effect = SQLTimeoutError("synthetic private pool detail")
        with self.assertRaises(HTTPException) as raised: self.run_upload()
        self.assertEqual(raised.exception.status_code,503)
        self.assertNotIn('private',raised.exception.detail)
        self.tx.add.assert_not_called()
        self.assertFalse(self.files())

    def test_initial_sql_failure_is_sanitized_before_any_file_read(self):
        self.session_builder.side_effect = SQLTimeoutError("synthetic private connection detail")
        upload=self.upload();upload.file=MagicMock(side_effect=AssertionError('must not read'))
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(service.store_version(self.request,7,upload,self.actor))
        self.assertEqual(raised.exception.status_code,503)
        upload.file.read.assert_not_called()
        self.assertFalse(self.files())

    def test_missing_locked_parent_rejects(self):
        self.tx.execute.return_value.scalar_one_or_none.return_value = None
        with self.assertRaises(HTTPException) as raised: self.run_upload()
        self.assertEqual(raised.exception.status_code, 404)
        self.assertFalse(self.files())

    def test_commit_ack_lost_and_failed_rollback_retain_publication(self):
        self.tx.commit.side_effect = RuntimeError("synthetic lost ack")
        self.tx.rollback.side_effect = RuntimeError("synthetic rollback failure")
        with self.assertRaises(HTTPException) as raised: self.run_upload()
        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("consulte el historial", raised.exception.detail)
        self.assertEqual(len(self.files()), 1)
        self.assertEqual(self.files()[0].read_bytes(), minimal_pdf())
        self.assertEqual({call.args[0] for call in self.events.call_args_list},
            {"DOCUMENT_REGISTRATION_UNCONFIRMED", "DOCUMENT_ROLLBACK_UNCONFIRMED"})

    def test_refresh_is_before_publication_not_after_successful_commit(self):
        self.tx.refresh.side_effect = RuntimeError("synthetic refresh failure")
        with self.assertRaises(RuntimeError): self.run_upload()
        self.assertFalse(self.files())
        self.tx.commit.assert_not_called()

    def test_cancelled_commit_retains_bytes_and_propagates(self):
        self.tx.commit.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError): self.run_upload()
        self.assertEqual(len(self.files()), 1)
        self.tx.rollback.assert_called_once()

    def test_caller_cancellation_waits_for_worker_and_never_compensates(self):
        started = threading.Event(); release = threading.Event()
        def commit():
            started.set()
            if not release.wait(3): raise AssertionError("test gate deadline")
        self.tx.commit.side_effect = commit
        async def exercise():
            task = asyncio.create_task(service.store_version(self.request, 7, self.upload(), self.actor))
            try:
                for _ in range(300):
                    if started.is_set(): break
                    await asyncio.sleep(.005)
                self.assertTrue(started.is_set())
                task.cancel(); await asyncio.sleep(.02)
                task.cancel(); await asyncio.sleep(.02)
                self.assertFalse(task.done())
            finally: release.set()
            with self.assertRaises(asyncio.CancelledError): await task
            self.tx.__exit__.assert_called_once()
        asyncio.run(exercise())
        self.assertEqual(len(self.files()), 1)
        self.tx.rollback.assert_not_called()

    def test_unmapped_user_rejected_without_starting_worker(self):
        actor = service.models.Usuario(id_usuario=999, activo=True, rol="admin")
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(service.store_version(self.request, 7, self.upload(), actor))
        self.assertEqual(raised.exception.status_code, 401)
        self.session_builder.assert_not_called()

    def test_anyio_scope_cancellation_also_drains_the_worker(self):
        started = threading.Event(); release = threading.Event()
        def commit():
            started.set()
            if not release.wait(3): raise AssertionError("test gate deadline")
        self.tx.commit.side_effect = commit
        async def exercise():
            async with anyio.create_task_group() as group:
                holder = {}
                async def cancel_and_release():
                    for _ in range(300):
                        if started.is_set(): break
                        await anyio.sleep(.005)
                    self.assertTrue(started.is_set())
                    holder['scope'].cancel()
                    await anyio.sleep(.02)
                    release.set()
                with anyio.CancelScope() as scope:
                    holder['scope'] = scope
                    group.start_soon(cancel_and_release)
                    await service.store_version(self.request, 7, self.upload(), self.actor)
            self.assertTrue(release.is_set())
        try: anyio.run(exercise)
        finally: release.set()
        self.assertEqual(len(self.files()), 1)
        self.tx.__exit__.assert_called_once()


class SessionBoundaryTests(unittest.TestCase):
    def test_request_session_read_transaction_released_and_isolation_scoped(self):
        db = MagicMock(spec=Session); db.new=set(); db.dirty=set(); db.deleted=set()
        engine = db.get_bind.return_value; engine.dialect.name="postgresql"
        with patch.object(service, "sessionmaker") as factory:
            service._upload_sessions(db)
        db.rollback.assert_called_once()
        engine.execution_options.assert_not_called()
        factory.assert_called_once_with(bind=engine, autoflush=False, expire_on_commit=False)

    def test_pending_changes_and_external_connection_rejected(self):
        db = MagicMock(spec=Session); db.new={object()}; db.dirty=set(); db.deleted=set()
        with self.assertRaises(HTTPException): service._upload_sessions(db)
        db.rollback.assert_not_called()
        db.new=set(); db.get_bind.return_value=MagicMock(spec=Connection)
        with self.assertRaises(HTTPException): service._upload_sessions(db)
        db.rollback.assert_not_called()

    def test_role_and_active_account_are_enforced_in_worker(self):
        db=MagicMock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value=None
        with self.assertRaises(HTTPException) as raised: service._upload_actor(db,3)
        self.assertEqual(raised.exception.status_code,401)
        for role in ["visualizador","geografo"]:
            db.query.return_value.filter.return_value.first.return_value=service.models.Usuario(id_usuario=3,rol=role,activo=True)
            with self.assertRaises(HTTPException) as raised: service._upload_actor(db,3)
            self.assertEqual(raised.exception.status_code,403)


if __name__=="__main__":unittest.main()
