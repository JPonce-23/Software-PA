"""3A offline: real POSIX/async scanner, explicit SQL snapshots/session doubles.

No PostgreSQL, Docker, dotenv, production engine or schema execution.
"""
import asyncio
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

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'tests/security'))
from _document_service_support import document_service
document_service()
from app.services import document_reconciliation as scan
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.engine.result import IteratorResult,SimpleResultMetaData
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import TextClause

KEY=b'synthetic-audit-key-only-32-bytes!'


class FilesystemTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='ss12-reconciliation-')
        self.addCleanup(self.directory.cleanup);self.root=Path(self.directory.name)
        (self.root/'7').mkdir(mode=0o700)
        self.content=b'original-synthetic'
        self.path='7/0001-'+('a'*32)+'.pdf';(self.root/self.path).write_bytes(self.content)
        self.version=scan._Version(1,7,3,self.path,hashlib.sha256(self.content).hexdigest(),len(self.content),'private-original.pdf','application/pdf')
        self.snapshot=scan._Snapshot((),(self.version,))
        self.engine=MagicMock(spec=Engine);self.engine.dialect=SimpleNamespace(name='postgresql')
    def inspect(self,first=None,last=None,**kwargs):
        first=self.snapshot if first is None else first;last=first if last is None else last
        with patch.object(scan,'_snapshot',side_effect=[first,last]) as snapshot:
            result=asyncio.run(scan.reconcile_documents(self.engine,3,[7],self.root,audit_key=KEY,**kwargs))
            self.assertEqual(snapshot.call_count,2)
            return result
    def codes(self,result):return {f.code for f in result.findings}
    def operation(self,state='pendiente',actor=3):
        opid=uuid.UUID('12345678-1234-4234-8234-123456789abc')
        return scan._Operation(opid,7,actor,state,f'7/op-{opid.hex}.pdf',f'7/.pending-{opid.hex}/payload',
            hashlib.sha256(self.content).hexdigest(),len(self.content),'private-original.pdf','application/pdf',
            1 if state=='confirmada' else None,None,'1900-01-01T00:00:00Z')
    def confirmed(self):
        op=self.operation('confirmada');target=self.root/op.ruta_prevista
        (self.root/self.path).rename(target)
        op=replace(op,identidad_archivo=(target.stat().st_dev,target.stat().st_ino))
        version=replace(self.version,ruta_almacenamiento=op.ruta_prevista)
        return scan._Snapshot((op,),(version,))
    def test_consistent_legacy_version_and_reproducible_opaque_report(self):
        a=self.inspect();b=self.inspect()
        self.assertEqual(a,b);self.assertEqual(self.codes(a),{scan.CONSISTENT});self.assertTrue(a.complete)
        text=json.dumps(asdict(a))
        for sensitive in [str(self.root),self.path,'private-original.pdf',self.version.hash_sha256]:self.assertNotIn(sensitive,text)
    def test_confirmed_operation_identity_and_file_are_consistent(self):
        snap=self.confirmed();result=self.inspect(snap)
        self.assertEqual(self.codes(result),{scan.CONSISTENT})
        self.assertEqual(result.findings[0].operation_id,str(snap.operations[0].id_operacion))
    def test_missing_file_is_observation_not_commit_failure(self):
        (self.root/self.path).unlink();result=self.inspect()
        self.assertEqual(self.codes(result),{scan.MISSING_FILE})
        self.assertEqual(result.findings[0].recommendation,'VERIFY_BACKUP_AND_REPEAT')
    def test_same_size_wrong_hash(self):
        (self.root/self.path).write_bytes(b'x'*len(self.content));result=self.inspect()
        self.assertEqual(self.codes(result),{scan.HASH_MISMATCH})
    def test_wrong_size_and_hash(self):
        (self.root/self.path).write_bytes(b'tampered');result=self.inspect()
        self.assertEqual(self.codes(result),{scan.HASH_MISMATCH,scan.SIZE_MISMATCH})
    def test_orphan_is_candidate_never_a_delete_recommendation(self):
        orphan='7/0002-'+('b'*32)+'.pdf';(self.root/orphan).write_bytes(b'synthetic orphan')
        result=self.inspect();finding=next(f for f in result.findings if f.code==scan.ORPHAN_FILE)
        self.assertIn(('candidate',True),finding.evidence);self.assertEqual(finding.recommendation,'MANUAL_REVIEW_ONLY')
        self.assertTrue((self.root/orphan).exists())
    def test_old_pending_with_final_file_is_uncertain_not_abandoned_or_orphan(self):
        (self.root/self.path).unlink()
        op=self.operation();(self.root/op.ruta_prevista).write_bytes(self.content)
        result=self.inspect(scan._Snapshot((op,),()))
        self.assertIn(scan.PENDING,self.codes(result));self.assertIn(scan.ACTIVE_OR_UNCERTAIN_OPERATION,self.codes(result))
        self.assertNotIn(scan.ORPHAN_FILE,self.codes(result));self.assertFalse(result.complete)
        self.assertFalse(any('abandon' in f.cause for f in result.findings))
    def test_reconciliation_state_is_never_completed(self):
        (self.root/self.path).unlink()
        op=self.operation('requiere_reconciliacion');snap=scan._Snapshot((op,),())
        result=self.inspect(snap);self.assertIn(scan.RECONCILIATION_REQUIRED,self.codes(result))
        self.assertEqual(snap.operations[0],op)
    def test_rejected_terminal_is_observed_without_mutation(self):
        (self.root/self.path).unlink()
        op=self.operation('rechazada');result=self.inspect(scan._Snapshot((op,),()))
        self.assertIn(scan.REJECTED,self.codes(result));self.assertEqual(op.estado,'rechazada')
    def test_confirmed_metadata_reference_mismatch_is_not_consistent(self):
        snap=self.confirmed();snap=replace(snap,operations=(replace(snap.operations[0],hash_sha256='f'*64),))
        result=self.inspect(snap);self.assertIn(scan.INCONSISTENT_METADATA,self.codes(result));self.assertNotIn(scan.CONSISTENT,self.codes(result))
    def test_invalid_confirmed_operation_path_never_reports_consistent_version(self):
        snap=self.confirmed();snap=replace(snap,operations=(replace(snap.operations[0],ruta_prevista='../outside'),))
        result=self.inspect(snap)
        self.assertIn(scan.INVALID_STORAGE_PATH,self.codes(result));self.assertNotIn(scan.CONSISTENT,self.codes(result))
    def test_confirmed_physical_identity_mismatch(self):
        snap=self.confirmed();snap=replace(snap,operations=(replace(snap.operations[0],identidad_archivo=(1,1)),))
        self.assertIn(scan.FILE_IDENTITY_MISMATCH,self.codes(self.inspect(snap)))
    def test_path_traversal_absolute_backslash_and_wrong_document_never_opened(self):
        for path in ['../outside.pdf','/etc/passwd','8/'+self.path.split('/')[1],'7/../secret','7/hidden\\name.pdf']:
            with self.subTest(path=path),patch.object(scan,'_file',wraps=scan._file) as reader:
                result=self.inspect(scan._Snapshot((),(replace(self.version,ruta_almacenamiento=path),)))
                self.assertIn(scan.INVALID_STORAGE_PATH,self.codes(result))
                # The real in-scope file may be inventoried, never any supplied path.
                self.assertTrue(all('/' not in call.args[1] for call in reader.call_args_list))
    def test_symlink_file_is_not_followed(self):
        target=self.root/'private-outside';target.write_bytes(b'secret synthetic')
        (self.root/self.path).unlink();(self.root/self.path).symlink_to(target)
        with patch.object(scan.os,'read',wraps=os.read) as read:
            result=self.inspect();self.assertIn(scan.INVALID_STORAGE_PATH,self.codes(result));read.assert_not_called()
    def test_symlink_in_root_ancestor_and_document_directory(self):
        alias=self.root/'alias';alias.symlink_to(self.root,target_is_directory=True)
        with patch.object(scan,'_snapshot',return_value=self.snapshot):
            result=asyncio.run(scan.reconcile_documents(self.engine,3,[7],alias,audit_key=KEY))
        self.assertIn(scan.INVALID_STORAGE_PATH,self.codes(result))
        (self.root/self.path).unlink();(self.root/'7').rmdir();(self.root/'7').symlink_to(self.root,target_is_directory=True)
        self.assertIn(scan.INVALID_STORAGE_PATH,self.codes(self.inspect()))
    def test_hard_link_is_not_read(self):
        alias=self.root/'other';os.link(self.root/self.path,alias)
        with patch.object(scan.os,'read',wraps=os.read) as read:
            result=self.inspect();self.assertIn(scan.INVALID_STORAGE_PATH,self.codes(result));read.assert_not_called()
    def test_empty_staging_is_incomplete_and_uncertain_even_when_old(self):
        (self.root/self.path).unlink()
        op=self.operation();(self.root/Path(op.ruta_staging).parent).mkdir(mode=0o700)
        result=self.inspect(scan._Snapshot((op,),()))
        self.assertIn(scan.STAGING_INCOMPLETE,self.codes(result));self.assertIn(scan.ACTIVE_OR_UNCERTAIN_OPERATION,self.codes(result))
    def test_staging_payload_symlink_is_unsafe_and_never_read(self):
        (self.root/self.path).unlink()
        op=self.operation();stage=self.root/Path(op.ruta_staging).parent;stage.mkdir(mode=0o700)
        secret=self.root/'outside';secret.write_bytes(b'synthetic private')
        (stage/'payload').symlink_to(secret)
        with patch.object(scan.os,'read',wraps=os.read) as read:
            result=self.inspect(scan._Snapshot((op,),()));read.assert_not_called()
        self.assertIn(scan.INVALID_STORAGE_PATH,self.codes(result))
    def test_nonterminal_identity_difference_stays_uncertain(self):
        (self.root/self.path).unlink()
        op=replace(self.operation(),identidad_archivo=(1,1));(self.root/op.ruta_prevista).write_bytes(self.content)
        result=self.inspect(scan._Snapshot((op,),()))
        self.assertIn(scan.FILE_IDENTITY_MISMATCH,self.codes(result));self.assertIn(scan.PENDING,self.codes(result))
        self.assertIn(scan.ACTIVE_OR_UNCERTAIN_OPERATION,self.codes(result))
    def test_foreign_operations_are_protective_references_not_disclosed(self):
        (self.root/self.path).unlink()
        op=self.operation(actor=4);(self.root/op.ruta_prevista).write_bytes(self.content)
        (self.root/Path(op.ruta_staging).parent).mkdir(mode=0o700)
        result=self.inspect(scan._Snapshot((op,),()))
        self.assertEqual(result.findings,());self.assertNotIn(str(op.id_operacion),json.dumps(asdict(result)))
    def test_sql_change_between_samples_suppresses_integrity_and_orphan_inferences(self):
        first=scan._Snapshot((self.operation(),),())
        last=self.confirmed()
        result=self.inspect(first,last)
        self.assertIn(scan.ACTIVE_OR_UNCERTAIN_OPERATION,self.codes(result))
        self.assertFalse(self.codes(result)&{scan.MISSING_FILE,scan.HASH_MISMATCH,scan.ORPHAN_FILE,scan.CONSISTENT})
    def test_file_modified_while_hashing_is_uncertain_not_corrupt(self):
        real=os.read;done=False;inode=(self.root/self.path).stat().st_ino
        def racing(fd,amount):
            nonlocal done
            data=real(fd,amount)
            if not done and os.fstat(fd).st_ino==inode:
                done=True;(self.root/self.path).write_bytes(b'x'*len(self.content))
            return data
        with patch.object(scan.os,'read',side_effect=racing):result=self.inspect()
        self.assertIn(scan.ACTIVE_OR_UNCERTAIN_OPERATION,self.codes(result));self.assertNotIn(scan.HASH_MISMATCH,self.codes(result))
    def test_entry_substitution_during_read_does_not_read_replacement(self):
        secret=self.root/'outside-synthetic';secret.write_bytes(b'private synthetic')
        real=os.read;done=False;secret_inode=secret.stat().st_ino;read_secret=False
        def racing(fd,amount):
            nonlocal done,read_secret
            read_secret |= os.fstat(fd).st_ino==secret_inode
            data=real(fd,amount)
            if not done:
                done=True;(self.root/self.path).unlink();(self.root/self.path).symlink_to(secret)
            return data
        with patch.object(scan.os,'read',side_effect=racing):result=self.inspect()
        self.assertFalse(read_secret);self.assertIn(scan.ACTIVE_OR_UNCERTAIN_OPERATION,self.codes(result))
        self.assertNotIn(scan.HASH_MISMATCH,self.codes(result))
    def test_read_failure_is_sanitized(self):
        with patch.object(scan.os,'read',side_effect=OSError(errno.EIO,'private path/credential')):
            result=self.inspect()
        self.assertIn(scan.READ_ERROR,self.codes(result));self.assertNotIn('credential',repr(result));self.assertFalse(result.complete)
    def test_sql_failure_before_or_after_scan_never_proves_orphan(self):
        for effects in [[RuntimeError('private db secret')],[self.snapshot,RuntimeError('private db secret')]]:
            with self.subTest(effects=len(effects)),patch.object(scan,'_snapshot',side_effect=effects):
                result=asyncio.run(scan.reconcile_documents(self.engine,3,[7],self.root,audit_key=KEY))
                self.assertEqual(self.codes(result),{scan.SQL_UNCERTAIN});self.assertEqual(result.documents,())
                self.assertNotIn('secret',repr(result))
    def test_authorization_denied_on_first_or_second_sample_returns_no_report(self):
        for effects in [[HTTPException(403,'denied')],[self.snapshot,HTTPException(403,'revoked')]]:
            with self.subTest(phase=len(effects)),patch.object(scan,'_snapshot',side_effect=effects):
                with self.assertRaises(HTTPException) as caught:
                    asyncio.run(scan.reconcile_documents(self.engine,3,[7],self.root,audit_key=KEY))
                self.assertEqual(caught.exception.status_code,403)
    def test_entry_byte_and_directory_limits_return_only_incomplete_summary(self):
        cases=[scan.Limits(max_bytes=1),scan.Limits(max_file_bytes=1),scan.Limits(max_directories=1)]
        (self.root/'7'/('.pending-'+'c'*32)).mkdir(mode=0o700)
        (self.root/'7'/('0002-'+'b'*32+'.pdf')).write_bytes(b'other')
        cases.append(scan.Limits(max_entries=1))
        for limits in cases:
            with self.subTest(limits=limits),patch.object(scan,'_snapshot',return_value=self.snapshot):
                result=asyncio.run(scan.reconcile_documents(self.engine,3,[7],self.root,audit_key=KEY,limits=limits))
                self.assertEqual(self.codes(result),{scan.SCAN_LIMIT_REACHED});self.assertFalse(result.complete)
                self.assertLessEqual(result.bytes_read,limits.max_bytes)
    def test_interrupt_and_deadline_before_scan_read_nothing(self):
        event=threading.Event();event.set()
        report=scan._inspect(self.engine,3,(7,),self.root,KEY,scan.Limits(),event)
        self.assertEqual(self.codes(report),{scan.SCAN_INTERRUPTED});self.assertEqual(report.bytes_read,0)
        with patch.object(scan.time,'monotonic',side_effect=[1,20]):
            report=scan._inspect(self.engine,3,(7,),self.root,KEY,scan.Limits(seconds=1),threading.Event())
        self.assertEqual(self.codes(report),{scan.SCAN_LIMIT_REACHED})
    def test_no_destructive_calls_content_or_metadata_mutations_and_readonly_open_flags(self):
        paths=[self.root,self.root/'7',self.root/self.path]
        attrs=lambda p:tuple(getattr(p.stat(),n) for n in ['st_dev','st_ino','st_mode','st_size','st_atime_ns','st_mtime_ns','st_ctime_ns','st_nlink'])
        before=[attrs(p) for p in paths];real_open=os.open
        def readonly(path,flags,*a,**kw):
            self.assertEqual(flags&os.O_ACCMODE,os.O_RDONLY)
            self.assertFalse(flags&(os.O_CREAT|os.O_TRUNC|os.O_APPEND));return real_open(path,flags,*a,**kw)
        from contextlib import ExitStack
        with ExitStack() as stack:
            for name in ['unlink','rmdir','rename','replace','mkdir','chmod','truncate','link','symlink','write','fsync']:
                stack.enter_context(patch.object(scan.os,name,side_effect=AssertionError('filesystem mutation forbidden')))
            stack.enter_context(patch.object(scan.os,'open',side_effect=readonly))
            self.assertIn(scan.CONSISTENT,self.codes(self.inspect()))
        self.assertEqual([attrs(p) for p in paths],before)
    def test_invalid_scope_and_limits_are_bounded_before_any_sql(self):
        with patch.object(scan,'_snapshot') as snapshot:
            for docs in [[],[0],[True],range(1,102)]:
                with self.subTest(docs=str(docs)),self.assertRaises(ValueError):
                    asyncio.run(scan.reconcile_documents(self.engine,3,docs,self.root,audit_key=KEY))
            snapshot.assert_not_called()
        with self.assertRaises(ValueError):scan.Limits(max_operations=0)
    def test_interrupt_during_hash_discards_partial_digest_and_closes_descriptors(self):
        content=b'x'*70000;(self.root/self.path).write_bytes(content)
        version=replace(self.version,hash_sha256=hashlib.sha256(content).hexdigest(),tamano_bytes=len(content))
        snap=scan._Snapshot((),(version,));cancel=threading.Event();real=os.read
        def interrupt(fd,amount):
            block=real(fd,amount);cancel.set();return block
        before=len(os.listdir('/proc/self/fd'))
        with patch.object(scan,'_snapshot',return_value=snap),patch.object(scan.os,'read',side_effect=interrupt):
            result=scan._inspect(self.engine,3,(7,),self.root,KEY,scan.Limits(),cancel)
        self.assertEqual(self.codes(result),{scan.SCAN_INTERRUPTED});self.assertEqual(result.bytes_read,65536)
        self.assertFalse(result.complete);self.assertEqual(result.documents,())
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)
    def test_disappearance_between_stat_and_open_is_uncertain_not_missing(self):
        real=os.open;name=self.path.split('/')[1]
        def disappear(path,*args,**kwargs):
            if path==name:raise FileNotFoundError(errno.ENOENT,'synthetic entry race')
            return real(path,*args,**kwargs)
        with patch.object(scan.os,'open',side_effect=disappear):result=self.inspect()
        self.assertIn(scan.ACTIVE_OR_UNCERTAIN_OPERATION,self.codes(result));self.assertNotIn(scan.MISSING_FILE,self.codes(result))
    def test_no_descriptor_leak_after_read_failure(self):
        before=len(os.listdir('/proc/self/fd'))
        with patch.object(scan,'_snapshot',return_value=self.snapshot),patch.object(scan.os,'read',side_effect=OSError(errno.EIO,'synthetic')):
            result=scan._inspect(self.engine,3,(7,),self.root,KEY,scan.Limits(),threading.Event())
        self.assertIn(scan.READ_ERROR,self.codes(result));self.assertEqual(len(os.listdir('/proc/self/fd')),before)
    def test_out_of_scope_sql_rows_fail_closed_before_filesystem(self):
        foreign=replace(self.version,id_documento=8)
        with patch.object(scan,'_snapshot',return_value=scan._Snapshot((),(foreign,))),patch.object(scan,'_tree') as tree:
            result=asyncio.run(scan.reconcile_documents(self.engine,3,[7],self.root,audit_key=KEY))
        tree.assert_not_called();self.assertEqual(self.codes(result),{scan.SQL_UNCERTAIN});self.assertEqual(result.documents,())
    def test_other_document_directory_is_never_opened(self):
        (self.root/'8').mkdir();(self.root/'8'/'sensitive-name.pdf').write_bytes(b'synthetic private')
        real=os.open
        def guarded(path,*args,**kwargs):
            self.assertNotEqual(str(path),'8');return real(path,*args,**kwargs)
        with patch.object(scan.os,'open',side_effect=guarded):result=self.inspect()
        self.assertEqual(self.codes(result),{scan.CONSISTENT})
    def test_blocking_work_runs_off_loop_and_cancellation_drains_worker(self):
        entered=threading.Event();release=threading.Event();finished=threading.Event();ids=[]
        def snapshot(*a):
            ids.append(threading.get_ident());entered.set()
            try:
                if not release.wait(3):raise AssertionError('test gate timeout')
                return self.snapshot
            finally:finished.set()
        async def exercise():
            loop_thread=threading.get_ident()
            task=asyncio.create_task(scan.reconcile_documents(self.engine,3,[7],self.root,audit_key=KEY))
            try:
                for _ in range(400):
                    if entered.is_set():break
                    await asyncio.sleep(.005)
                self.assertTrue(entered.is_set());self.assertNotEqual(ids[0],loop_thread)
                task.cancel();await asyncio.sleep(.02);self.assertFalse(task.done())
            finally:release.set()
            with self.assertRaises(asyncio.CancelledError):await task
            self.assertTrue(finished.is_set())
        with patch.object(scan,'_snapshot',side_effect=snapshot):asyncio.run(exercise())


class SQLReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.engine=MagicMock(spec=Engine);self.engine.dialect=SimpleNamespace(name='postgresql')
        self.db=MagicMock(spec=Session);self.db.__enter__.return_value=self.db
        self.actor=SimpleNamespace(id_usuario=3,rol='admin')
        self.db.query.return_value.filter.return_value.first.return_value=self.actor
        self.op_rows=[];self.version_rows=[];self.mode=('on','repeatable read',False)
        def execute(statement,*a,**kw):
            result=MagicMock()
            if isinstance(statement,TextClause):
                self.assertTrue(statement.text.lstrip().upper().startswith('SELECT'))
                result.one.return_value=self.mode
            else:
                self.assertTrue(statement.is_select);self.assertIsNone(statement._for_update_arg)
                cols=list(statement.selected_columns)
                if cols[0].key=='id_usuario':result.first.return_value=self.actor
                else:result.mappings.return_value.all.return_value=self.op_rows if cols[0].key=='id_operacion' else self.version_rows
            return result
        self.db.execute.side_effect=execute
    def snapshot(self,limits=None):
        limits=limits or scan.Limits();budget=scan._Budget(limits,threading.Event())
        return scan._snapshot(self.engine,3,(7,),limits,budget)
    def context(self):
        from contextlib import ExitStack
        stack=ExitStack();self.addCleanup(stack.close)
        self.constructor=stack.enter_context(patch.object(scan,'Session',return_value=self.db))
        self.listen=stack.enter_context(patch.object(scan.event,'listen'))
        self.remove=stack.enter_context(patch.object(scan.event,'remove'))
        self.authorize=stack.enter_context(patch.object(scan,'require_document_access'))
        return stack
    def test_own_sessions_readonly_repeatable_read_primary_scope_and_bounded_selects(self):
        self.context();self.snapshot();self.snapshot()
        self.assertEqual(self.constructor.call_count,2)
        for call in self.db.connection.call_args_list:self.assertEqual(call.kwargs['execution_options'],{'isolation_level':'REPEATABLE READ','postgresql_readonly':True})
        self.constructor.assert_called_with(bind=self.engine,autoflush=False,expire_on_commit=False)
        statements=[c.args[0] for c in self.db.execute.call_args_list if not isinstance(c.args[0],TextClause)]
        self.assertEqual(len(statements),6)
        for stmt in statements:
            self.assertNotIn('contrasena_hash',str(stmt))
            if list(stmt.selected_columns)[0].key=='id_usuario':continue
            self.assertIn('id_documento',str(stmt.whereclause));self.assertIn(7,list(stmt.whereclause.right.value))
            self.assertIn(stmt._limit_clause.value,[201,401])
        for name in ['commit','flush','add','delete','merge']:getattr(self.db,name).assert_not_called()
        self.assertEqual(self.listen.call_count,self.remove.call_count)
    def test_actor_or_document_denial_never_loads_operations(self):
        self.context();self.authorize.side_effect=HTTPException(403,'denied')
        with self.assertRaises(HTTPException):self.snapshot()
        self.assertEqual(len(self.db.execute.call_args_list),3)
        self.db.commit.assert_not_called()
    def test_nonprimary_or_nonreadonly_mode_is_uncertain(self):
        self.context()
        for mode in [('off','repeatable read',False),('on','read committed',False),('on','repeatable read',True)]:
            self.mode=mode
            with self.subTest(mode=mode),self.assertRaises(scan._Stop) as caught:self.snapshot()
            self.assertEqual(caught.exception.code,scan.SQL_UNCERTAIN)
        self.db.query.assert_not_called()
    def test_sql_record_limit_refuses_truncated_reference_inventory(self):
        self.context();self.op_rows=[{},{}]
        with self.assertRaises(scan._Stop) as caught:self.snapshot(scan.Limits(max_operations=1))
        self.assertEqual(caught.exception.code,scan.SCAN_LIMIT_REACHED)
    def test_canonical_authorization_query_cap_and_no_rowlocks_or_dml(self):
        self.context();self.snapshot();bounded=self.listen.call_args.args[2]
        # Actual SQLAlchemy in-memory Result.freeze; no database.
        def result(statement):return IteratorResult(SimpleResultMetaData(['id']),iter([(1,)]))
        state=SimpleNamespace(is_select=True,statement=select(scan.models.Usuario.id_usuario),invoke_statement=MagicMock(side_effect=result))
        self.assertEqual(list(bounded(state)),[(1,)])
        self.assertLessEqual(state.invoke_statement.call_args.args[0]._limit_clause.value,201)
        for statement,is_select in [(select(scan.models.Usuario.id_usuario).with_for_update(),True),(update(scan.models.Usuario).values(activo=False),False)]:
            state.statement=statement;state.is_select=is_select
            with self.assertRaises(scan._Stop):bounded(state)
    def test_authorization_overflow_fails_closed(self):
        self.context();self.snapshot(scan.Limits(max_authorization_rows=1));bounded=self.listen.call_args.args[2]
        state=SimpleNamespace(is_select=True,statement=select(scan.models.Usuario.id_usuario),invoke_statement=lambda stmt:IteratorResult(SimpleResultMetaData(['id']),iter([(1,),(2,)])))
        with self.assertRaises(scan._Stop) as caught:bounded(state)
        self.assertEqual(caught.exception.code,scan.SCAN_LIMIT_REACHED)
