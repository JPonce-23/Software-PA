"""Recovery coordination contracts: owned POSIX files, no SQL/network/Docker."""
import ast
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'tests/security')]
from _document_service_support import document_service
document_service()
from app.services.document_coordination import WriterLease,CoordinationError
from app.services.document_storage import stage_document,DocumentStorageError
from app.services import document_recovery_execution as recovery


class CoordinationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='ss12-execution-unit-')
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.op=uuid.uuid4()

    def test_same_operation_cannot_hold_two_leases(self):
        with WriterLease(self.root,7,self.op,create=True):
            with self.assertRaises(CoordinationError)as error:
                with WriterLease(self.root,7,self.op):pass
            self.assertEqual(error.exception.code,'ACTIVE_WRITER')

    def test_different_operations_coexist_and_identity_survives_close(self):
        with WriterLease(self.root,7,self.op,create=True)as first:
            identity=first.identity
            with WriterLease(self.root,7,uuid.uuid4(),create=True):first.check()
        with WriterLease(self.root,7,self.op)as retry:self.assertEqual(retry.identity,identity)

    def test_close_error_still_releases_every_owned_descriptor(self):
        lease=WriterLease(self.root,7,self.op,create=True).__enter__()
        descriptors=[lease.fd,lease.directory_fd,lease.root_fd]
        real_close=os.close
        def close_with_reported_error(fd):
            real_close(fd)
            if fd==descriptors[0]:raise OSError('synthetic close error after release')
        try:
            with patch('app.services.document_coordination.os.close',side_effect=close_with_reported_error):
                with self.assertRaises(OSError):lease.close()
            for fd in descriptors:
                with self.subTest(fd=fd),self.assertRaises(OSError):os.fstat(fd)
            self.assertEqual((lease.fd,lease.directory_fd,lease.root_fd),(None,None,None))
            lease.close()
            with WriterLease(self.root,7,self.op):pass
        finally:
            lease.close()

    def test_check_close_error_releases_both_temporary_descriptors(self):
        with WriterLease(self.root,7,self.op,create=True)as lease:
            real_close=os.close
            def close_with_reported_error(fd):
                # _open_root also closes traversed directories. Target only the
                # completed check's coordination directory, not path traversal.
                target=Path('/proc/self/fd/'+str(fd)).readlink().name=='.ss12-writers'
                real_close(fd)
                if target:raise OSError('synthetic temporary descriptor close error')
            before=set(os.listdir('/proc/self/fd'))
            with patch('app.services.document_coordination.os.close',side_effect=close_with_reported_error):
                with self.assertRaises(OSError):lease.check()
            self.assertEqual(set(os.listdir('/proc/self/fd')),before)
            lease.check()

    def test_path_walk_close_error_releases_the_already_open_child(self):
        real_close=os.close;calls=[]
        def descriptors():
            result=set()
            for name in os.listdir('/proc/self/fd'):
                try:os.fstat(int(name));result.add(int(name))
                except OSError:pass
            return result
        def close_with_reported_error(fd):
            real_close(fd);calls.append(fd)
            if len(calls)==1:raise OSError('synthetic path traversal close error')
        before=descriptors()
        try:
            with patch('app.services.document_coordination.os.close',side_effect=close_with_reported_error):
                with self.assertRaises(OSError):
                    with WriterLease(self.root,7,self.op,create=True):pass
            self.assertEqual(descriptors(),before)
        finally:
            for fd in descriptors()-before:real_close(fd)

    def test_upload_cleanup_close_error_preserves_processing_error_and_published_file(self):
        data=b'SS12 synthetic cleanup';digest=hashlib.sha256(data).hexdigest()
        staged=stage_document(self.root,7,data,digest,operation_id=self.op).__enter__()
        name='op-'+self.op.hex+'.pdf';staged.publish(name)
        descriptors=[staged.coordination.fd,staged.coordination.directory_fd,staged.coordination.root_fd]
        real_close=os.close
        def close_with_reported_error(fd):
            real_close(fd)
            if fd==descriptors[0]:raise OSError('synthetic close error after release')
        try:
            with patch('app.services.document_coordination.os.close',side_effect=close_with_reported_error),\
                 patch('app.services.document_storage.storage_event')as event:
                with self.assertRaisesRegex(RuntimeError,'synthetic processing error'):
                    try:raise RuntimeError('synthetic processing error')
                    finally:staged.close()
                event.assert_any_call('DOCUMENT_STAGING_CLEANUP_INCOMPLETE',self.op.hex)
            for fd in descriptors:
                with self.subTest(fd=fd),self.assertRaises(OSError):os.fstat(fd)
            self.assertEqual((self.root/'7'/name).read_bytes(),data)
            with WriterLease(self.root,7,self.op):pass
        finally:
            staged.close()

    def test_recovery_never_creates_coordination_artifacts(self):
        before=list(self.root.iterdir())
        with self.assertRaises(OSError):
            with WriterLease(self.root,7,self.op):pass
        self.assertEqual(list(self.root.iterdir()),before)

    def test_replaced_lock_does_not_fake_exclusion(self):
        with WriterLease(self.root,7,self.op,create=True)as original:
            path=self.root/'.ss12-writers'/original.name
            path.rename(path.with_suffix('.retained'));path.touch(mode=0o600)
            with self.assertRaises(CoordinationError):original.check()
            with WriterLease(self.root,7,self.op)as substituted:
                self.assertNotEqual(original.identity,substituted.identity)

    def test_symlink_and_hardlink_coordination_rejected(self):
        with WriterLease(self.root,7,self.op,create=True)as first:name=first.name
        path=self.root/'.ss12-writers'/name;path.unlink()
        target=self.root/'foreign';target.touch(mode=0o600);path.symlink_to(target)
        with self.assertRaises(OSError):
            with WriterLease(self.root,7,self.op):pass
        path.unlink();os.link(target,path)
        with self.assertRaises(CoordinationError):
            with WriterLease(self.root,7,self.op):pass

    def test_world_writable_root_is_not_trusted(self):
        self.root.chmod(0o777)
        with self.assertRaises(CoordinationError):
            with WriterLease(self.root,7,self.op,create=True):pass

    def test_permission_change_while_holding_lease_is_detected(self):
        with WriterLease(self.root,7,self.op,create=True)as lease:
            (self.root/'.ss12-writers').chmod(0o777)
            with self.assertRaises(CoordinationError):lease.check()

    def test_upload_coordination_conflict_keeps_controlled_http_status(self):
        data=b'SS12 synthetic conflict';digest=hashlib.sha256(data).hexdigest()
        with stage_document(self.root,7,data,digest,operation_id=self.op)as staged:
            (self.root/'.ss12-writers').chmod(0o777)
            with self.assertRaises(DocumentStorageError)as error:
                staged.publish('op-'+self.op.hex+'.pdf')
            self.assertEqual(error.exception.status,409)
            self.assertFalse((self.root/'7'/('op-'+self.op.hex+'.pdf')).exists())

    def test_publish_is_single_link_before_sql_commit_and_keeps_writer_lock(self):
        data=b'SS12 synthetic publication';digest=hashlib.sha256(data).hexdigest()
        with stage_document(self.root,7,data,digest,operation_id=self.op)as staged:
            staged.publish('op-'+self.op.hex+'.pdf')
            final=self.root/'7'/('op-'+self.op.hex+'.pdf')
            self.assertEqual(final.stat().st_nlink,1)
            self.assertEqual(final.read_bytes(),data)
            with self.assertRaises(CoordinationError):
                with WriterLease(self.root,7,self.op):pass
        self.assertEqual(final.read_bytes(),data)
        with WriterLease(self.root,7,self.op):pass

    def test_authorization_fence_covers_all_canonical_access_relations(self):
        tree=ast.parse((ROOT/'backend/app/services/access.py').read_text())
        classes={n.attr for n in ast.walk(tree)if isinstance(n,ast.Attribute)
                 and isinstance(n.value,ast.Name)and n.value.id=='models'}
        self.assertEqual(set(recovery.AUTHORIZATION_TABLES),
                         {getattr(recovery.models,name).__tablename__ for name in classes})

    def test_observation_plan_or_nonoperator_reason_is_not_authority(self):
        with self.assertRaises(ValueError):
            recovery.recover_document_operation(None,1,7,self.op,
                attempt_id=uuid.uuid4(),root=self.root,reason='observation-token')
        with self.assertRaises(ValueError):
            recovery.recover_document_operation(None,False,7,self.op,
                attempt_id=uuid.uuid4(),root=self.root,reason='OPERATOR_REVIEW')


if __name__=='__main__':unittest.main()
