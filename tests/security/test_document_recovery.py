"""Offline 3B: real POSIX and async coordinator, explicit SQL snapshot doubles.

No PostgreSQL/Docker/credentials/dotenv or production engine is accessed.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import asdict, replace
import errno
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'tests/security'))
from _document_service_support import document_service
document_service()
from app.services import document_recovery as recovery
from fastapi import HTTPException
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import TextClause

scan = recovery.observation
KEY = b'SS12_SYNTHETIC_RECOVERY_AUDIT_KEY_32'


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='ss12-recovery-offline-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / '7').mkdir(mode=0o700)
        self.content = b'SS12 synthetic recovery bytes'
        self.operation_id = uuid.UUID('12345678-1234-4234-8234-123456789abc')
        path = f'7/op-{self.operation_id.hex}.pdf'
        self.path = self.root / path
        self.path.write_bytes(self.content)
        info = self.path.stat()
        self.operation = scan._Operation(self.operation_id, 7, 3, 'confirmada', path,
            f'7/.pending-{self.operation_id.hex}/payload', hashlib.sha256(self.content).hexdigest(),
            len(self.content), 'private-original.pdf', 'application/pdf', 11,
            (info.st_dev, info.st_ino), '2000-01-01T00:00:00Z')
        self.version = scan._Version(11, 7, 3, path, self.operation.hash_sha256,
            len(self.content), 'private-original.pdf', 'application/pdf')
        self.snapshot = scan._Snapshot((self.operation,), (self.version,))
        self.engine = MagicMock(spec=Engine)
        self.engine.dialect = SimpleNamespace(name='postgresql')

    def run_plan(self, first=None, last=None, **kwargs):
        first = self.snapshot if first is None else first
        last = first if last is None else last
        with patch.object(scan, '_snapshot', side_effect=[first, last]):
            return asyncio.run(recovery.evaluate_recovery(self.engine, 3, 7,
                self.operation_id, self.root, audit_key=KEY, **kwargs))

    def state(self, name):
        op = replace(self.operation, estado=name, id_documento_version=None)
        return scan._Snapshot((op,), ())

    def test_existing_confirmation_returns_reference_without_new_version(self):
        plan = self.run_plan()
        self.assertEqual(plan.diagnostics, (recovery.EXISTING_CONFIRMATION,))
        self.assertEqual(plan.existing_result, recovery.ExistingResult(7, 11))
        self.assertEqual(plan.proposed_action, 'RETURN_EXISTING_RESULT')
        self.assertTrue(plan.complete)
        self.assertTrue(plan.dry_run)
        self.assertFalse(plan.transition_enabled)

    def test_retry_is_idempotent_including_observation_token(self):
        self.assertEqual(self.run_plan(), self.run_plan())

    def test_two_concurrent_recoverers_have_independent_evaluations(self):
        barrier = threading.Barrier(2)
        local = threading.local()
        def snapshot(*args):
            local.calls = getattr(local, 'calls', 0) + 1
            if local.calls == 1:
                barrier.wait(timeout=3)
            return self.snapshot
        with patch.object(scan, '_snapshot', side_effect=snapshot), ThreadPoolExecutor(max_workers=2) as pool:
            def evaluate():
                return asyncio.run(recovery.evaluate_recovery(self.engine, 3, 7,
                    self.operation_id, self.root, audit_key=KEY))
            jobs = [pool.submit(evaluate) for _ in range(2)]
            plans = [job.result(timeout=5) for job in jobs]
        self.assertEqual(plans[0], plans[1])
        self.assertEqual(plans[0].existing_result.version_id, 11)

    def test_pending_with_potential_writer_never_resumes_or_proves_abandonment(self):
        plan = self.run_plan(self.state('pendiente'))
        self.assertIn(scan.PENDING, plan.diagnostics)
        self.assertIn(scan.ACTIVE_OR_UNCERTAIN_OPERATION, plan.diagnostics)
        self.assertEqual(plan.proposed_action, 'WAIT_AND_REVIEW')
        self.assertIn(('abandonment_proven', False), plan.evidence)
        self.assertIsNone(plan.existing_result)
        self.assertTrue(self.path.exists())

    def test_pending_without_file_keeps_state_even_if_very_old(self):
        self.path.unlink()
        plan = self.run_plan(self.state('pendiente'))
        self.assertIn(scan.PENDING, plan.diagnostics)
        self.assertIn(scan.MISSING_FILE, plan.diagnostics)
        self.assertEqual(plan.durable_state, 'pendiente')
        self.assertEqual(plan.blocked_reason, 'NO_WRITER_QUIESCENCE_OR_COMMIT_PROOF')

    def test_published_without_version_is_only_candidate_not_adopted(self):
        plan = self.run_plan(self.state('pendiente'))
        self.assertIn(recovery.PUBLISHED_WITHOUT_CONFIRMATION, plan.diagnostics)
        self.assertIn('LEGAL_031_TRANSITION_AND_ORIGINAL_ACTOR_CONTEXT', plan.pending_preconditions)
        self.assertIsNone(plan.version_id)
        self.assertEqual(self.path.read_bytes(), self.content)

    def test_reconciliation_required_is_not_automatically_resolved(self):
        plan = self.run_plan(self.state('requiere_reconciliacion'))
        self.assertIn(scan.RECONCILIATION_REQUIRED, plan.diagnostics)
        self.assertEqual(plan.durable_state, 'requiere_reconciliacion')
        self.assertFalse(plan.transition_enabled)

    def test_missing_confirmed_file_requires_intervention_not_result_replay(self):
        self.path.unlink()
        plan = self.run_plan()
        self.assertIn(scan.MISSING_FILE, plan.diagnostics)
        self.assertIsNone(plan.existing_result)
        self.assertEqual(plan.proposed_action, 'MANUAL_REVIEW_ONLY')

    def test_wrong_hash_at_same_size_does_not_return_confirmation(self):
        self.path.write_bytes(b'x' * len(self.content))
        plan = self.run_plan()
        self.assertEqual(plan.diagnostics, (scan.HASH_MISMATCH,))
        self.assertIsNone(plan.existing_result)

    def test_wrong_size_and_hash_are_both_reported(self):
        self.path.write_bytes(b'wrong')
        plan = self.run_plan()
        self.assertEqual(set(plan.diagnostics), {scan.SIZE_MISMATCH, scan.HASH_MISMATCH})

    def test_wrong_durable_identity_is_not_consistent(self):
        snap = replace(self.snapshot, operations=(replace(self.operation, identidad_archivo=(1, 1)),))
        self.assertIn(scan.FILE_IDENTITY_MISMATCH, self.run_plan(snap).diagnostics)

    def test_missing_durable_identity_blocks_physical_adoption(self):
        snap = self.state('pendiente')
        snap = replace(snap, operations=(replace(snap.operations[0], identidad_archivo=None),))
        plan = self.run_plan(snap)
        self.assertIn(scan.INCONSISTENT_METADATA, plan.diagnostics)
        self.assertIsNone(plan.existing_result)

    def test_invalid_operation_paths_rejected_before_open(self):
        for value in ('../secret', '/etc/passwd', '8/op-' + self.operation_id.hex + '.pdf', '7/a\\secret'):
            snap = replace(self.snapshot, operations=(replace(self.operation, ruta_prevista=value),))
            with self.subTest(value=value), patch.object(recovery, '_physical') as physical:
                self.assertEqual(self.run_plan(snap).diagnostics, (scan.INVALID_STORAGE_PATH,))
                physical.assert_not_called()

    def test_symlink_file_is_not_followed(self):
        outside = self.root / 'private-synthetic'
        outside.write_bytes(b'private bytes')
        self.path.unlink()
        self.path.symlink_to(outside)
        with patch.object(scan.os, 'read', wraps=os.read) as read:
            plan = self.run_plan()
            read.assert_not_called()
        self.assertIn(scan.INVALID_STORAGE_PATH, plan.diagnostics)
        self.assertNotIn(recovery.PUBLISHED_WITHOUT_CONFIRMATION, plan.diagnostics)

    def test_symlink_document_and_root_ancestor_are_not_followed(self):
        self.path.unlink()
        (self.root / '7').rmdir()
        (self.root / '7').symlink_to(self.root, target_is_directory=True)
        self.assertIn(scan.INVALID_STORAGE_PATH, self.run_plan().diagnostics)
        alias = self.root / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        with patch.object(scan, '_snapshot', return_value=self.snapshot):
            result = asyncio.run(recovery.evaluate_recovery(self.engine, 3, 7,
                self.operation_id, alias, audit_key=KEY))
        self.assertIn(scan.INVALID_STORAGE_PATH, result.diagnostics)

    def test_hard_link_is_never_read(self):
        os.link(self.path, self.root / 'other')
        with patch.object(scan.os, 'read', wraps=os.read) as read:
            plan = self.run_plan()
            read.assert_not_called()
        self.assertIn(scan.INVALID_STORAGE_PATH, plan.diagnostics)

    def test_file_substitution_during_read_is_uncertain(self):
        real_read = os.read
        done = False
        def read(fd, size):
            nonlocal done
            value = real_read(fd, size)
            if not done:
                done = True
                replacement = self.root / 'replacement'
                replacement.write_bytes(self.content)
                os.replace(replacement, self.path)
            return value
        with patch.object(scan.os, 'read', side_effect=read):
            plan = self.run_plan()
        self.assertEqual(plan.diagnostics, (scan.ACTIVE_OR_UNCERTAIN_OPERATION,))
        self.assertIsNone(plan.existing_result)

    def test_same_inode_modification_during_read_is_uncertain(self):
        real_read = os.read
        def read(fd, size):
            value = real_read(fd, size)
            self.path.write_bytes(b'x' * len(self.content))
            return value
        with patch.object(scan.os, 'read', side_effect=read):
            self.assertEqual(self.run_plan().diagnostics, (scan.ACTIVE_OR_UNCERTAIN_OPERATION,))

    def test_file_substitution_between_physical_checks_is_uncertain(self):
        real = recovery._physical
        count = 0
        def physical(*args):
            nonlocal count
            count += 1
            if count == 2:
                replacement = self.root / 'replacement'
                replacement.write_bytes(self.content)
                os.replace(replacement, self.path)
            return real(*args)
        with patch.object(recovery, '_physical', side_effect=physical):
            self.assertEqual(self.run_plan().diagnostics, (scan.ACTIVE_OR_UNCERTAIN_OPERATION,))

    def test_disappearing_parent_is_uncertain(self):
        real = recovery._physical
        def physical(*args):
            value = real(*args)
            if self.path.exists():
                (self.root / '7').rename(self.root / 'moved')
            return value
        with patch.object(recovery, '_physical', side_effect=physical):
            self.assertEqual(self.run_plan().diagnostics, (scan.ACTIVE_OR_UNCERTAIN_OPERATION,))

    def test_io_error_does_not_become_consistent_or_expose_exception(self):
        with patch.object(scan.os, 'read', side_effect=OSError(errno.EIO, 'private credential /path')):
            plan = self.run_plan()
        self.assertEqual(plan.diagnostics, (scan.READ_ERROR,))
        self.assertFalse(plan.complete)
        self.assertNotIn('credential', repr(plan))

    def test_lost_sql_connection_before_or_after_first_sample_is_redacted(self):
        for effects in ([RuntimeError('private password')], [self.snapshot, RuntimeError('private password')]):
            with self.subTest(samples=len(effects)), patch.object(scan, '_snapshot', side_effect=effects):
                plan = asyncio.run(recovery.evaluate_recovery(self.engine, 3, 7,
                    self.operation_id, self.root, audit_key=KEY))
            self.assertEqual(plan.diagnostics, (scan.SQL_UNCERTAIN,))
            self.assertIsNone(plan.operation_id)
            self.assertIsNone(plan.durable_state)
            self.assertNotIn('password', repr(plan))

    def test_postgresql_lock_and_statement_timeout_have_specific_diagnostics(self):
        for sqlstate, expected in [('55P03', recovery.LOCK_TIMEOUT), ('57014', recovery.SQL_TIMEOUT)]:
            original = RuntimeError('private SQL/path')
            original.pgcode = sqlstate
            with patch.object(scan, '_snapshot', side_effect=OperationalError('private SQL', {}, original)):
                plan = asyncio.run(recovery.evaluate_recovery(self.engine, 3, 7,
                    self.operation_id, self.root, audit_key=KEY))
            self.assertEqual(plan.diagnostics, (expected,))
            self.assertIsNone(plan.operation_id)

    def test_rejected_terminal_never_changes_or_resumes(self):
        plan = self.run_plan(self.state('rechazada'))
        self.assertIn(scan.REJECTED, plan.diagnostics)
        self.assertEqual(plan.proposed_action, 'KEEP_TERMINAL_RESULT')
        self.assertEqual(plan.durable_state, 'rechazada')

    def test_permission_revoked_on_either_sample_returns_no_plan(self):
        for effects in ([HTTPException(403, 'denied')], [self.snapshot, HTTPException(403, 'denied')]):
            with self.subTest(sample=len(effects)), patch.object(scan, '_snapshot', side_effect=effects):
                with self.assertRaises(HTTPException) as error:
                    asyncio.run(recovery.evaluate_recovery(self.engine, 3, 7,
                        self.operation_id, self.root, audit_key=KEY))
                self.assertEqual(error.exception.status_code, 403)

    def test_foreign_and_absent_operations_have_identical_denials_before_filesystem(self):
        foreign = replace(self.snapshot, operations=(replace(self.operation, id_usuario=4),))
        messages = []
        for snap in (foreign, scan._Snapshot((), ())):
            with patch.object(recovery, '_physical') as physical, self.assertRaises(HTTPException) as error:
                self.run_plan(snap)
            messages.append((error.exception.status_code, error.exception.detail))
            physical.assert_not_called()
        self.assertEqual(messages[0], messages[1])

    def test_operation_disappearance_state_or_identity_change_is_not_replayed(self):
        for last in (scan._Snapshot((), ()), self.state('requiere_reconciliacion'),
                     replace(self.snapshot, operations=(replace(self.operation, identidad_archivo=(1, 1)),))):
            with self.subTest(last=last):
                plan = self.run_plan(last=last)
                self.assertEqual(plan.diagnostics, (scan.ACTIVE_OR_UNCERTAIN_OPERATION,))
                self.assertIsNone(plan.existing_result)

    def test_version_change_between_samples_is_uncertain(self):
        last = replace(self.snapshot, versions=(replace(self.version, hash_sha256='f' * 64),))
        self.assertEqual(self.run_plan(last=last).diagnostics, (scan.ACTIVE_OR_UNCERTAIN_OPERATION,))

    def test_incompatible_version_or_nonterminal_reference_blocks_before_read(self):
        snapshots = [replace(self.snapshot, versions=()),
            replace(self.snapshot, versions=(replace(self.version, id_usuario_carga=4),)),
            replace(self.snapshot, operations=self.state('pendiente').operations)]
        for snap in snapshots:
            with self.subTest(snap=snap), patch.object(recovery, '_physical') as physical:
                self.assertEqual(self.run_plan(snap).diagnostics, (scan.INCONSISTENT_METADATA,))
                physical.assert_not_called()

    def test_budgets_bound_both_physical_checks(self):
        for limits in (scan.Limits(max_file_bytes=1), scan.Limits(max_bytes=1),
                       scan.Limits(max_entries=1), scan.Limits(max_directories=1)):
            with self.subTest(limits=limits):
                self.assertEqual(self.run_plan(limits=limits).diagnostics, (scan.SCAN_LIMIT_REACHED,))

    def test_sql_row_limit_and_authorization_overflow_remain_conservative(self):
        with patch.object(scan, '_snapshot', side_effect=scan._Stop(scan.SCAN_LIMIT_REACHED)):
            plan = asyncio.run(recovery.evaluate_recovery(self.engine, 3, 7,
                self.operation_id, self.root, audit_key=KEY))
        self.assertEqual(plan.diagnostics, (scan.SCAN_LIMIT_REACHED,))
        self.assertIsNone(plan.operation_id)

    def test_interrupt_and_deadline_before_first_query(self):
        event = threading.Event()
        event.set()
        with patch.object(scan, '_snapshot') as snapshot:
            result = recovery._evaluate(self.engine, 3, 7, self.operation_id, self.root,
                KEY, scan.Limits(), event)
            snapshot.assert_not_called()
        self.assertEqual(result.diagnostics, (scan.SCAN_INTERRUPTED,))
        with patch.object(scan.time, 'monotonic', side_effect=[1, 20]):
            result = recovery._evaluate(self.engine, 3, 7, self.operation_id, self.root,
                KEY, scan.Limits(seconds=1), threading.Event())
        self.assertEqual(result.diagnostics, (scan.SCAN_LIMIT_REACHED,))

    def test_async_cancellation_drains_worker_without_repair(self):
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()
        def snapshot(*args):
            entered.set()
            try:
                if not release.wait(3):
                    raise AssertionError('offline gate timeout')
                return self.snapshot
            finally:
                finished.set()
        async def exercise():
            task = asyncio.create_task(recovery.evaluate_recovery(self.engine, 3, 7,
                self.operation_id, self.root, audit_key=KEY))
            try:
                for _ in range(400):
                    if entered.is_set():
                        break
                    await asyncio.sleep(.005)
                self.assertTrue(entered.is_set())
                task.cancel()
                await asyncio.sleep(.02)
                self.assertFalse(task.done())
            finally:
                release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(finished.is_set())
        with patch.object(scan, '_snapshot', side_effect=snapshot):
            asyncio.run(exercise())
        self.assertEqual(self.path.read_bytes(), self.content)

    def test_dry_run_has_no_posix_mutations_and_preserves_metadata(self):
        paths = [self.root, self.root / '7', self.path]
        def stamps():
            return [tuple(getattr(p.stat(), n) for n in ('st_dev', 'st_ino', 'st_mode',
                'st_size', 'st_atime_ns', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')) for p in paths]
        before = stamps()
        real_open = os.open
        def readonly(path, flags, *args, **kwargs):
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)
            self.assertFalse(flags & (os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            return real_open(path, flags, *args, **kwargs)
        with ExitStack() as stack:
            for name in ('unlink', 'rmdir', 'rename', 'replace', 'mkdir', 'chmod', 'truncate',
                         'link', 'symlink', 'write', 'fsync'):
                stack.enter_context(patch.object(scan.os, name, side_effect=AssertionError('mutation forbidden')))
            stack.enter_context(patch.object(scan.os, 'open', side_effect=readonly))
            self.assertEqual(self.run_plan().existing_result.version_id, 11)
        self.assertEqual(stamps(), before)

    def test_output_never_leaks_storage_names_hashes_or_exception_details(self):
        plan = self.run_plan()
        payload = json.dumps(asdict(plan))
        for private in (str(self.root), self.operation.ruta_prevista, self.operation.ruta_staging,
                        self.operation.nombre_original, self.operation.hash_sha256):
            self.assertNotIn(private, payload)
        self.assertEqual(plan.operation_id, str(self.operation_id))
        self.assertEqual(len(plan.observation_token), 64)

    def test_no_apply_mode_or_invalid_input_can_reach_sql(self):
        cases = [dict(dry_run=False), dict(dry_run=1), dict(actor_id=True),
                 dict(document_id=0), dict(operation_id='invalid'), dict(audit_key=b'short')]
        with patch.object(scan, '_snapshot') as snapshot:
            for changes in cases:
                args = dict(engine=self.engine, actor_id=3, document_id=7,
                            operation_id=self.operation_id, root=self.root, audit_key=KEY)
                args.update(changes)
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    asyncio.run(recovery.evaluate_recovery(**args))
            snapshot.assert_not_called()

    def sql_context(self, operations=None, versions=None):
        """Exercise the REAL 3A SQL boundary; DB results are explicit doubles."""
        dbs = [MagicMock(spec=Session), MagicMock(spec=Session)]
        values = asdict(self.operation)
        values['identidad_archivo'] = {'device': self.operation.identidad_archivo[0],
                                      'inode': self.operation.identidad_archivo[1]}
        operations = [values] if operations is None else operations
        versions = [asdict(self.version)] if versions is None else versions
        def execute(statement, *args, **kwargs):
            result = MagicMock()
            if isinstance(statement, TextClause):
                self.assertTrue(statement.text.lstrip().startswith('SELECT'))
                result.one.return_value = ('on', 'repeatable read', False)
            else:
                self.assertTrue(statement.is_select)
                self.assertIsNone(statement._for_update_arg)
                self.assertNotIn('contrasena_hash', str(statement))
                name = list(statement.selected_columns)[0].key
                if name == 'id_usuario':
                    result.first.return_value = SimpleNamespace(id_usuario=3, rol='admin')
                else:
                    result.mappings.return_value.all.return_value = operations if name == 'id_operacion' else versions
            return result
        for db in dbs:
            db.__enter__.return_value = db
            db.execute.side_effect = execute
        stack = ExitStack()
        self.addCleanup(stack.close)
        constructor = stack.enter_context(patch.object(scan, 'Session', side_effect=dbs))
        stack.enter_context(patch.object(scan.event, 'listen'))
        stack.enter_context(patch.object(scan.event, 'remove'))
        access = stack.enter_context(patch.object(scan, 'require_document_access'))
        return dbs, constructor, access

    def test_real_snapshot_boundary_uses_two_owned_readonly_sessions_no_dml_or_rowlocks(self):
        dbs, constructor, access = self.sql_context()
        plan = asyncio.run(recovery.evaluate_recovery(self.engine, 3, 7,
            self.operation_id, self.root, audit_key=KEY))
        self.assertEqual(plan.existing_result.version_id, 11)
        self.assertEqual(constructor.call_count, 2)
        self.assertEqual(access.call_count, 2)
        for db in dbs:
            db.connection.assert_called_once_with(execution_options={
                'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': True})
            for name in ('commit', 'flush', 'add', 'add_all', 'delete', 'merge'):
                getattr(db, name).assert_not_called()

    def test_real_snapshot_operation_overflow_prevents_physical_inspection(self):
        self.sql_context(operations=[{}, {}])
        with patch.object(recovery, '_physical') as physical:
            plan = asyncio.run(recovery.evaluate_recovery(self.engine, 3, 7,
                self.operation_id, self.root, audit_key=KEY, limits=scan.Limits(max_operations=1)))
        self.assertEqual(plan.diagnostics, (scan.SCAN_LIMIT_REACHED,))
        physical.assert_not_called()

    def test_real_snapshot_version_overflow_prevents_physical_inspection(self):
        self.sql_context(versions=[{}, {}])
        with patch.object(recovery, '_physical') as physical:
            plan = asyncio.run(recovery.evaluate_recovery(self.engine, 3, 7,
                self.operation_id, self.root, audit_key=KEY, limits=scan.Limits(max_versions=1)))
        self.assertEqual(plan.diagnostics, (scan.SCAN_LIMIT_REACHED,))
        physical.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
