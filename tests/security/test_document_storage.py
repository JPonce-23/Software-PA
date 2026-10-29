"""SS-12: real POSIX operations on owned temporary files; synthetic DB doubles.

No PostgreSQL, server, Docker, migrations or institutional files. Child Python
processes below run only this pure storage module on tiny synthetic payloads.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import errno
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.services import document_storage as storage
from app.safe_logging import SafeJSONFormatter
from test_document_validation import service_functions, minimal_pdf


def digest(data): return hashlib.sha256(data).hexdigest()
NAME = '0001-' + 'a' * 32 + '.pdf'


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.real_event = storage.storage_event
        self.events = patch.object(storage, 'storage_event'); self.event = self.events.start(); self.addCleanup(self.events.stop)

    def stage(self, data=b'SS12 tiny synthetic complete bytes', doc=7):
        return storage.stage_document(self.root, doc, data, digest(data))

    def assert_clean(self): self.assertEqual(list(self.root.rglob('.pending-*')), [])

    def test_private_complete_file_hash_fsync_publication_and_cleanup(self):
        data = b'SS12 original\x00\xff bytes'
        with self.stage(data) as staged:
            owned_fds = [staged.root_fd, staged.document_fd, staged.stage_fd, staged.file_fd]
            self.assertFalse((self.root / '7' / NAME).exists())
            self.assertEqual(os.fstat(staged.file_fd).st_mode & 0o777, 0o600)
            self.assertEqual(os.fstat(staged.stage_fd).st_mode & 0o777, 0o700)
            staged.publish(NAME)
            self.assertEqual((self.root / '7' / NAME).read_bytes(), data)
            self.assertEqual(os.stat(self.root / '7' / NAME).st_ino, os.fstat(staged.file_fd).st_ino)
        final = self.root / '7' / NAME
        self.assertEqual(digest(final.read_bytes()), digest(data)); self.assertEqual(final.stat().st_nlink, 1)
        self.assert_clean(); self.assertIsNone(staged.root_fd); self.assertIsNone(staged.file_fd)
        for fd in owned_fds:
            with self.assertRaises(OSError): os.fstat(fd)

    def test_existing_file_and_symlink_never_overwritten_or_deleted(self):
        document = self.root / '7'; document.mkdir()
        foreign = self.root / 'foreign'; foreign.write_bytes(b'foreign')
        for symlink in [False, True]:
            target = document / NAME
            if target.exists() or target.is_symlink(): target.unlink()
            if symlink: target.symlink_to(foreign)
            else: target.write_bytes(b'existing')
            with self.stage() as staged:
                with self.assertRaises(storage.DocumentStorageError) as error: staged.publish(NAME)
                self.assertEqual(error.exception.code, 'DOCUMENT_STORAGE_COLLISION')
            self.assertEqual(foreign.read_bytes(), b'foreign')
            self.assertEqual(target.read_bytes(), b'foreign' if symlink else b'existing')
            self.assert_clean()

    def test_partial_os_writes_are_completed_and_zero_write_is_rejected(self):
        real_write = os.write
        def partial_write(fd, data):
            self.assertFalse((self.root / '7' / NAME).exists())
            return real_write(fd, data[:3])
        with patch.object(storage.os, 'write', side_effect=partial_write):
            with self.stage(b'1234567890') as staged: staged.publish(NAME)
        self.assertEqual((self.root / '7' / NAME).read_bytes(), b'1234567890')
        with patch.object(storage.os, 'write', return_value=0):
            with self.assertRaises(storage.DocumentStorageError):
                with self.stage(doc=8): pass
        self.assert_clean()

    def test_failure_or_cancel_during_write_flush_and_hash_removes_only_private_stage(self):
        foreign = self.root / 'foreign'; foreign.write_bytes(b'preserved')
        for function, error in [('write', OSError(errno.ENOSPC, 'synthetic full disk')),
                ('write', PermissionError('synthetic')), ('write', asyncio.CancelledError()),
                ('fsync', OSError(errno.EIO, 'synthetic')), ('fsync', asyncio.CancelledError()),
                ('read', OSError(errno.EIO, 'synthetic'))]:
            with self.subTest(function=function, kind=type(error).__name__), patch.object(storage.os, function, side_effect=error):
                with self.assertRaises((storage.DocumentStorageError, asyncio.CancelledError)):
                    with self.stage(): pass
            self.assert_clean(); self.assertEqual(list((self.root / '7').glob('*.pdf')), [])
            self.assertEqual(foreign.read_bytes(), b'preserved')

    def test_readback_hash_mismatch_rejects_before_publication(self):
        with self.assertRaises(storage.DocumentStorageError) as error:
            with storage.stage_document(self.root, 7, b'abc', '0' * 64): pass
        self.assertEqual(error.exception.code, 'DOCUMENT_STORAGE_HASH_MISMATCH')
        self.assert_clean(); self.assertEqual(list((self.root / '7').glob('*.pdf')), [])

    def test_root_document_symlinks_escape_and_world_write_are_rejected(self):
        real = self.root / 'real'; real.mkdir()
        link = self.root / 'link'; link.symlink_to(real, target_is_directory=True)
        with self.assertRaises(storage.DocumentStorageError):
            with storage.stage_document(link, 7, b'a', digest(b'a')): pass
        (self.root / '7').symlink_to(real, target_is_directory=True)
        with self.assertRaises(storage.DocumentStorageError):
            with self.stage(): pass
        self.assertEqual(list(real.iterdir()), [])
        with self.assertRaises(storage.DocumentStorageError):
            with storage.stage_document('/', 7, b'a', digest(b'a')): pass
        for doc in [-1, True, '../x']:
            with self.assertRaises(storage.DocumentStorageError): self.stage(doc=doc)
        (self.root / '7').unlink(); self.root.chmod(0o777)
        try:
            with self.assertRaises(storage.DocumentStorageError):
                with self.stage(): pass
        finally: self.root.chmod(0o700)

    def test_stage_collision_does_not_adopt_or_clean_existing_directory(self):
        doc = self.root / '7'; doc.mkdir()
        stage = doc / ('.pending-' + 'b' * 32); stage.mkdir(); (stage / 'foreign').write_bytes(b'foreign')
        with patch.object(storage.uuid, 'uuid4', return_value=type('Token', (), {'hex': 'b' * 32})()):
            with self.assertRaises(storage.DocumentStorageError):
                with self.stage(): pass
        self.assertEqual((stage / 'foreign').read_bytes(), b'foreign')

    def test_invalid_publication_names_and_double_publication_rejected(self):
        with self.stage() as staged:
            for name in ['../outside.pdf', '/absolute.pdf', '0000-' + 'a' * 32 + '.pdf', 'client.pdf']:
                with self.assertRaises(storage.DocumentStorageError): staged.publish(name)
            staged.publish(NAME)
            with self.assertRaises(storage.DocumentStorageError): staged.publish(NAME)
        self.assert_clean()

    def test_source_substitution_is_detected_and_foreign_entry_is_not_deleted(self):
        foreign = self.root / 'foreign'; foreign.write_bytes(b'foreign')
        with self.stage() as staged:
            original = self.root / '7' / staged.stage_name / 'payload'
            original.unlink(); original.symlink_to(foreign)
            with self.assertRaises(storage.DocumentStorageError): staged.publish(NAME)
        self.assertTrue(original.is_symlink()); self.assertEqual(foreign.read_bytes(), b'foreign')
        self.event.assert_called_with('DOCUMENT_STAGING_CLEANUP_INCOMPLETE', staged.operation_id)

    def test_document_directory_substitution_does_not_redirect_publication_or_cleanup(self):
        with self.stage() as staged:
            (self.root / '7').rename(self.root / 'old-document')
            (self.root / '7').mkdir()
            foreign = self.root / '7' / NAME; foreign.write_bytes(b'foreign')
            with self.assertRaises(storage.DocumentStorageError) as error: staged.publish(NAME)
            self.assertEqual(error.exception.code, 'DOCUMENT_STORAGE_DIRECTORY_CHANGED')
        self.assertEqual(foreign.read_bytes(), b'foreign'); self.assert_clean()

    def test_cleanup_permission_error_keeps_publication_and_reports_incomplete_cleanup(self):
        staged = self.stage().__enter__(); staged.publish(NAME)
        with patch.object(storage.os, 'unlink', side_effect=PermissionError('synthetic cleanup denial')):
            staged.close()
        self.assertTrue((self.root / '7' / NAME).is_file())
        self.assertIsNone(staged.root_fd); self.assertIsNone(staged.file_fd)
        self.event.assert_called_with('DOCUMENT_STAGING_CLEANUP_INCOMPLETE', staged.operation_id)

    def test_abrupt_child_exit_documents_partial_stage_and_published_orphan_windows(self):
        script = '''import hashlib, os, pathlib, sys
from app.services.document_storage import stage_document
root=pathlib.Path(sys.argv[1]); phase=sys.argv[2]; name=sys.argv[3]; data=b'SS12 tiny crash fixture'
if phase=='partial':
 original=os.write
 def partial(fd, content):
  original(fd,content[:3]); os._exit(17)
 os.write=partial
with stage_document(root,7,data,hashlib.sha256(data).hexdigest()) as staged:
 if phase=='published': staged.publish(name)
 os._exit(17)
'''
        env = {'PATH': '/usr/bin:/bin', 'PYTHONPATH': str(ROOT / 'backend'), 'LC_ALL': 'C.UTF-8'}
        for phase in ['partial', 'staged', 'published']:
            root = self.root / phase; root.mkdir()
            result = subprocess.run([sys.executable, '-B', '-c', script, str(root), phase, NAME],
                env=env, capture_output=True, timeout=5)
            self.assertEqual((result.returncode, result.stderr), (17, b''))
            payloads = list(root.rglob('payload')); self.assertEqual(len(payloads), 1)
            self.assertEqual(payloads[0].read_bytes(), b'SS1' if phase == 'partial' else b'SS12 tiny crash fixture')
            final = root / '7' / NAME
            self.assertEqual(final.exists(), phase == 'published')
            if final.exists(): self.assertEqual(final.read_bytes(), b'SS12 tiny crash fixture')

    def test_unexpected_foreign_stage_content_is_never_recursively_removed(self):
        with self.stage() as staged:
            foreign = self.root / '7' / staged.stage_name / 'foreign'
            foreign.write_bytes(b'foreign')
        self.assertEqual(foreign.read_bytes(), b'foreign')
        self.event.assert_called_with('DOCUMENT_STAGING_CLEANUP_INCOMPLETE', staged.operation_id)

    def test_failed_hardlink_has_no_copy_or_replace_fallback(self):
        with self.stage() as staged, patch.object(storage.os, 'link', side_effect=OSError(errno.EXDEV, 'synthetic')):
            with self.assertRaises(storage.DocumentStorageError): staged.publish(NAME)
        self.assert_clean(); self.assertFalse((self.root / '7' / NAME).exists())

    def test_directory_fsync_failure_after_link_retains_published_entry(self):
        with self.stage() as staged:
            with patch.object(storage.os, 'fsync', side_effect=OSError(errno.EIO, 'synthetic')):
                with self.assertRaises(storage.DocumentStorageError): staged.publish(NAME)
        self.assertTrue((self.root / '7' / NAME).is_file()); self.assert_clean()

    def test_exception_after_publication_retains_final_and_closes_staging(self):
        with self.assertRaises(RuntimeError):
            with self.stage() as staged:
                staged.publish(NAME)
                raise RuntimeError('synthetic after publication')
        self.assertTrue((self.root / '7' / NAME).is_file()); self.assert_clean()

    def test_storage_diagnostics_use_final_safe_format_without_paths_or_exception_text(self):
        stream = io.StringIO(); handler = logging.StreamHandler(stream); handler.setFormatter(SafeJSONFormatter())
        logger = logging.getLogger('ssalfer.diagnostics')
        old = (logger.handlers, logger.level, logger.propagate, logger.disabled)
        try:
            logger.handlers = [handler]; logger.setLevel(logging.ERROR); logger.propagate = False; logger.disabled = False
            failure = OSError(errno.ENOSPC, 'SS12_SECRET_SYNTHETIC', str(self.root / 'private-client-name'))
            self.real_event(storage._io_code(failure), 'a' * 32)
        finally:
            logger.handlers, level, logger.propagate, logger.disabled = old; logger.setLevel(level)
        output = stream.getvalue(); event = json.loads(output)
        self.assertEqual((event['code'], event['component'], event['correlation_id']),
            ('DOCUMENT_STORAGE_FULL', 'documents', 'a' * 32))
        self.assertNotIn('SS12_SECRET_SYNTHETIC', output); self.assertNotIn(str(self.root), output)

    def test_simultaneous_threads_use_exclusive_publication_without_mutex(self):
        barrier = threading.Barrier(2)
        def worker(value):
            with self.stage(value) as staged:
                barrier.wait(timeout=5)
                try: staged.publish(NAME); return 'ok'
                except storage.DocumentStorageError as error: return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, [b'complete-A', b'complete-B']))
        self.assertEqual(sorted(results), ['DOCUMENT_STORAGE_COLLISION', 'ok'])
        self.assertIn((self.root / '7' / NAME).read_bytes(), [b'complete-A', b'complete-B'])
        self.assert_clean()

    def test_independent_documents_do_not_share_a_process_lock(self):
        barrier = threading.Barrier(2)
        def worker(doc):
            with self.stage(str(doc).encode(), doc) as staged:
                barrier.wait(timeout=5); staged.publish(NAME)
        with ThreadPoolExecutor(max_workers=2) as pool: list(pool.map(worker, [7, 8]))
        self.assertEqual((self.root / '7' / NAME).read_bytes(), b'7')
        self.assertEqual((self.root / '8' / NAME).read_bytes(), b'8'); self.assert_clean()

    def test_separate_python_processes_share_the_same_exclusive_filesystem_rule(self):
        script = '''import hashlib, pathlib, sys, time
from app.services.document_storage import stage_document, DocumentStorageError
root=pathlib.Path(sys.argv[1]); tag=sys.argv[2]; data=('complete-'+tag).encode()
with stage_document(root,7,data,hashlib.sha256(data).hexdigest()) as staged:
 (root/('ready-'+tag)).write_text('ready')
 deadline=time.monotonic()+5
 while not (root/'go').exists():
  if time.monotonic()>deadline: raise RuntimeError('synthetic barrier timeout')
  time.sleep(.005)
 try: staged.publish(sys.argv[3]); print('ok')
 except DocumentStorageError as error: print(error.code)
'''
        env = {'PATH': '/usr/bin:/bin', 'PYTHONPATH': str(ROOT / 'backend'), 'LC_ALL': 'C.UTF-8'}
        children = []
        try:
            for tag in ['A', 'B']:
                children.append(subprocess.Popen([sys.executable, '-B', '-c', script, str(self.root), tag, NAME],
                    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
            deadline = time.monotonic() + 5
            while not all((self.root / ('ready-' + tag)).exists() for tag in ['A', 'B']):
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.005)
            (self.root / 'go').write_text('go')
            results = []
            for child in children:
                output, errors = child.communicate(timeout=5)
                self.assertEqual((child.returncode, errors), (0, '')); results.append(output.strip())
            self.assertEqual(sorted(results), ['DOCUMENT_STORAGE_COLLISION', 'ok'])
            self.assertIn((self.root / '7' / NAME).read_bytes(), [b'complete-A', b'complete-B'])
            self.assert_clean()
        finally:
            for child in children:
                if child.poll() is None: child.kill(); child.communicate(timeout=5)


class ServiceFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'UPLOAD_ROOT': str(self.root)}, clear=True)
        self.env.start(); self.addCleanup(self.env.stop)
        self.ns = service_functions(); self.user = type('User', (), {'id_usuario': 3})()
        self.db = MagicMock(); query = self.db.query.return_value
        query.filter.return_value = query; query.first.return_value = None; query.scalar.return_value = 0

    def upload(self):
        async def read(size): return minimal_pdf()
        upload = type('Upload', (), {'filename': 'synthetic.pdf', 'content_type': 'application/pdf'})()
        upload.read = read
        return asyncio.run(self.ns['store_version'](self.db, 7, upload, self.user))

    def test_lost_commit_ack_never_deletes_potentially_committed_bytes(self):
        committed = []
        def commit():
            committed.append(self.db.add.call_args.args[0])
            raise RuntimeError('SS12 synthetic lost COMMIT response')
        self.db.commit.side_effect = commit
        with self.assertRaises(Exception) as caught: self.upload()
        self.assertEqual(caught.exception.status_code, 409)
        self.assertIn('consulte el historial', caught.exception.detail)
        self.assertEqual(len(committed), 1)
        path = self.root / committed[0].ruta_almacenamiento
        self.assertEqual(path.read_bytes(), minimal_pdf())
        self.assertEqual(digest(path.read_bytes()), committed[0].hash_sha256)
        self.assertEqual(list(self.root.rglob('.pending-*')), [])
        self.db.rollback.assert_called_once()

    def test_cancel_during_commit_retains_file_rolls_back_and_propagates(self):
        self.db.commit.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError): self.upload()
        self.assertEqual(len(list(self.root.rglob('*.pdf'))), 1)
        self.assertEqual(list(self.root.rglob('.pending-*')), []); self.db.rollback.assert_called_once()

    def test_refresh_failure_after_commit_and_rollback_failure_do_not_delete_file(self):
        self.db.refresh.side_effect = RuntimeError('synthetic HTTP failure after commit')
        with self.assertRaises(RuntimeError): self.upload()
        self.assertEqual(len(list(self.root.rglob('*.pdf'))), 1)
        self.assertEqual(list(self.root.rglob('.pending-*')), [])
        self.db.refresh.side_effect = None
        self.db.commit.side_effect = RuntimeError('synthetic commit')
        self.db.rollback.side_effect = RuntimeError('synthetic rollback')
        with self.assertRaises(RuntimeError): self.upload()
        self.assertEqual(len(list(self.root.rglob('*.pdf'))), 2)
        self.assertEqual(list(self.root.rglob('.pending-*')), [])

    def test_storage_error_rejects_before_record_commit(self):
        with patch.object(storage.os, 'write', side_effect=OSError(errno.ENOSPC, 'synthetic')):
            with self.assertRaises(Exception) as caught: self.upload()
        self.assertEqual(caught.exception.status_code, 507)
        self.db.add.assert_not_called(); self.db.commit.assert_not_called()
        self.assertEqual(list(self.root.rglob('*.pdf')), [])
        self.assertEqual(list(self.root.rglob('.pending-*')), [])


if __name__ == '__main__': unittest.main()
