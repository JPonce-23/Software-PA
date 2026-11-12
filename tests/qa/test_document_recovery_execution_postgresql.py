"""Opt-in real PostgreSQL recovery, ONLY the verified disposable SS12 lab.

Faults target owned synthetic uploads/child processes. Never applies migrations,
starts/stops Docker or connects to an ordinary application database.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import multiprocessing
import os
from pathlib import Path
import signal
import sys
import threading
import unittest
import uuid
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'tests/security'),str(ROOT/'tests/qa')]
import test_document_service_postgresql as publication


def interrupted_upload(document,key,root,phase,ready):
    if not(os.getenv('SS12_QA_ENABLE')=='1'and os.getenv('SS12_QA_RECOVERY_EXECUTION')=='1'):
        raise RuntimeError('Explicit recovery lab opt-in required')
    from sqlalchemy import create_engine,text
    from sqlalchemy.engine import URL
    from sqlalchemy.orm import Session
    from fastapi import UploadFile
    from _document_service_support import document_service
    from _document_samples import minimal_pdf
    service=document_service()
    engine=create_engine(URL.create('postgresql+psycopg2',host=os.environ['SS12_QA_SOCKET_DIR'],
        port=5432,database='software_pa_test',username='ss12_runner',password=os.environ['SS12_QA_PASSWORD']),
        hide_parameters=True,connect_args={'connect_timeout':3})
    with engine.connect()as c:
        assert tuple(c.execute(text("SELECT current_database(),current_setting('cluster_name')")).one())==('software_pa_test','ss12-document-disposable')
    os.environ['UPLOAD_ROOT']=root
    def wait():
        ready.send('fault-point-reached')
        threading.Event().wait(30)
        raise RuntimeError('Parent did not terminate its synthetic worker')
    original=service._confirm_version
    def after(*a,**kw):
        result=original(*a,**kw);wait();return result
    target=patch.object(service.operations,'confirm',side_effect=lambda *a:wait())if phase=='before'else patch.object(service,'_confirm_version',side_effect=after)
    with target,Session(engine)as db:
        actor=db.get(service.models.Usuario,1)
        asyncio.run(service.store_version(db,document,UploadFile(io.BytesIO(minimal_pdf('crash')),
            filename='synthetic.pdf'),actor,idempotency_key=key))


def interrupted_recovery(document,operation,attempt,root,phase,ready):
    if not(os.getenv('SS12_QA_ENABLE')=='1'and os.getenv('SS12_QA_RECOVERY_EXECUTION')=='1'):
        raise RuntimeError('Explicit recovery lab opt-in required')
    from sqlalchemy import create_engine,text
    from sqlalchemy.engine import URL
    from sqlalchemy.orm import Session,sessionmaker
    from _document_service_support import document_service
    document_service()
    from app.services import document_recovery_execution as executor
    engine=create_engine(URL.create('postgresql+psycopg2',host=os.environ['SS12_QA_SOCKET_DIR'],port=5432,
        database='software_pa_test',username='ss12_runner',password=os.environ['SS12_QA_PASSWORD']),hide_parameters=True)
    with engine.connect()as c:
        assert tuple(c.execute(text("SELECT current_database(),current_setting('cluster_name')")).one())==('software_pa_test','ss12-document-disposable')
    calls=[]
    def wait():
        ready.send('fault-point-reached');threading.Event().wait(30)
        raise RuntimeError('Parent did not terminate its recovery worker')
    class Interrupted(Session):
        def commit(db):
            calls.append(1)
            if len(calls)==2 and phase=='before':wait()
            super().commit()
            if len(calls)==2 and phase=='after':wait()
    with patch.object(executor,'sessionmaker',side_effect=lambda **kw:sessionmaker(class_=Interrupted,**kw)):
        executor.recover_document_operation(engine,1,document,operation,attempt_id=attempt,root=root,reason='OPERATOR_REVIEW')


@unittest.skipUnless(os.getenv('SS12_QA_ENABLE')=='1'and os.getenv('SS12_QA_RECOVERY_EXECUTION')=='1',
                     'Explicit disposable recovery execution lab authorization required')
class RecoveryExecutionPostgreSQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        publication.DocumentServicePostgreSQL.setUpClass.__func__(cls)
        from app.services import document_recovery_execution as executor
        from app.services.document_coordination import WriterLease
        cls.executor=executor;cls.WriterLease=WriterLease
        # Keep a second synthetic administrator: native RBAC forbids revoking
        # the last active admin. Never weaken that production trigger for QA.
        with cls.engine.begin()as c:
            c.execute(cls.text("SELECT set_config('app.current_user_id','1',true)"))
            c.execute(cls.text("INSERT INTO usuario(nombre,apellido_paterno,correo,contrasena_hash,rol,activo,fecha_alta,observaciones) "
                "VALUES ('SS12 recovery guard','QA','ss12-recovery-guard@example.invalid','SS12_SYNTHETIC_DISABLED_HASH','admin',true,now(),'SS12_SYNTHETIC_DISPOSABLE_ONLY') ON CONFLICT(correo) DO NOTHING"))
        with cls.engine.connect()as c:
            value=c.execute(cls.text("SELECT checksum_sha256 FROM schema_migrations WHERE version='032'")).scalar()
            assert value==hashlib.sha256((ROOT/'backend/db/migrations/032_recuperacion_documental_controlada.sql').read_bytes()).hexdigest()

    setUp=publication.DocumentServicePostgreSQL.setUp
    upload=publication.DocumentServicePostgreSQL.upload
    rows=publication.DocumentServicePostgreSQL.rows
    _operation_record=publication.DocumentServicePostgreSQL._operation_record

    def pending(self):
        key=uuid.uuid4();content=self.pdf('SS12_RECOVERY_SYNTHETIC')
        with patch.object(self.service.operations,'confirm',side_effect=RuntimeError('synthetic pre-commit loss')):
            status,_=self.upload(self.documents[0],content,key)
        self.assertEqual(status,409)
        record=self._operation_record(key)
        self.assertEqual(record['estado'],'requiere_reconciliacion')
        self.assertEqual(len(self.rows(self.documents[0])),0)
        path=self.root/record['ruta_prevista'];self.assertEqual(path.read_bytes(),content)
        self.assertEqual(path.stat().st_nlink,1)
        return key,record,content

    def recover(self,record,attempt=None,actor=1):
        return self.executor.recover_document_operation(self.engine,actor,self.documents[0],record['id_operacion'],
            attempt_id=attempt or uuid.uuid4(),root=self.root,reason='OPERATOR_REVIEW')

    def journal(self,attempt):
        with self.engine.connect()as c:
            return c.execute(self.text('SELECT to_jsonb(r) FROM documento_recuperacion r WHERE id_intento=:id'),{'id':str(attempt)}).scalar_one()

    def test_recovers_published_file_and_repeats_without_duplicate_or_file_change(self):
        key,record,content=self.pending();path=self.root/record['ruta_prevista'];before=path.stat()
        attempt=uuid.uuid4();first=self.recover(record,attempt)
        self.assertEqual((first.status,first.code),('VERIFIED','RECOVERED'))
        self.assertEqual(self.recover(record,attempt),first)
        existing=self.recover(record)
        self.assertEqual((existing.status,existing.code,existing.version_id),('VERIFIED','EXISTING_RESULT',first.version_id))
        self.assertEqual(self.upload(self.documents[0],content,key)[0],200)
        self.assertEqual(len(self.rows(self.documents[0])),1)
        self.assertEqual((path.stat().st_dev,path.stat().st_ino),(before.st_dev,before.st_ino))
        self.assertEqual(path.read_bytes(),content)
        self.assertEqual(self.journal(attempt)['id_usuario'],1)

    def test_confirmed_upload_lost_http_result_is_only_verified(self):
        key=uuid.uuid4();self.assertEqual(self.upload(self.documents[0],self.pdf('ack'),key)[0],201)
        record=self._operation_record(key);before=self.rows(self.documents[0])
        result=self.recover(record)
        self.assertEqual((result.status,result.code),('VERIFIED','EXISTING_RESULT'))
        self.assertEqual(self.rows(self.documents[0]),before)

    def test_active_writer_lock_blocks_without_terminalizing_same_attempt(self):
        _,record,content=self.pending();attempt=uuid.uuid4()
        with self.WriterLease(self.root,self.documents[0],uuid.UUID(record['id_operacion'])):
            result=self.recover(record,attempt)
            self.assertEqual((result.status,result.code),('PENDING','ACTIVE_WRITER'))
            self.assertEqual(self.journal(attempt)['estado'],'pendiente')
            self.assertEqual(self.rows(self.documents[0]),[])
        self.assertEqual(self.recover(record,attempt).status,'VERIFIED')

    def test_two_recovery_process_requests_same_attempt_have_one_result(self):
        _,record,_=self.pending();attempt=uuid.uuid4()
        with ThreadPoolExecutor(max_workers=2)as pool:
            results=list(pool.map(lambda _:self.recover(record,attempt),range(2)))
        self.assertTrue(any(r.status=='VERIFIED'for r in results))
        self.assertEqual(self.recover(record,attempt).status,'VERIFIED')
        self.assertEqual(len(self.rows(self.documents[0])),1)

    def test_different_concurrent_attempts_never_duplicate_version(self):
        _,record,_=self.pending();attempts=[uuid.uuid4(),uuid.uuid4()]
        with ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(lambda x:self.recover(record,x),attempts))
        self.assertTrue(any(r.status=='VERIFIED'for r in results))
        for attempt in attempts:self.assertEqual(self.recover(record,attempt).status,'VERIFIED')
        self.assertEqual(len(self.rows(self.documents[0])),1)

    def test_missing_file_is_blocked_and_does_not_change_operation(self):
        _,record,_=self.pending();path=self.root/record['ruta_prevista'];retained=self.root/'retained'
        path.rename(retained);attempt=uuid.uuid4()
        self.assertEqual(self.recover(record,attempt).status,'BLOCKED')
        self.assertTrue(retained.is_file());self.assertEqual(self.rows(self.documents[0]),[])
        self.assertEqual(self.journal(attempt)['estado'],'bloqueada')

    def test_corruption_blocks_and_preserves_bytes(self):
        _,record,_=self.pending();path=self.root/record['ruta_prevista'];path.write_bytes(b'CORRUPT_SYNTHETIC')
        self.assertEqual(self.recover(record).status,'BLOCKED')
        self.assertEqual(path.read_bytes(),b'CORRUPT_SYNTHETIC');self.assertEqual(self.rows(self.documents[0]),[])

    def test_substitution_with_identical_bytes_still_blocks(self):
        _,record,content=self.pending();path=self.root/record['ruta_prevista'];old=self.root/'retained'
        path.rename(old);path.write_bytes(content);path.chmod(0o600)
        self.assertEqual(self.recover(record).status,'BLOCKED')
        self.assertEqual(old.read_bytes(),content);self.assertEqual(path.read_bytes(),content)
        self.assertEqual(self.rows(self.documents[0]),[])

    def test_substitution_after_descriptor_verification_rolls_back_before_commit(self):
        _,record,content=self.pending();original=self.executor._physical
        def substitute(*a):
            verified=original(*a);path=self.root/record['ruta_prevista']
            path.rename(self.root/'retained');path.write_bytes(content);path.chmod(0o600)
            return verified
        with patch.object(self.executor,'_physical',side_effect=substitute):result=self.recover(record)
        self.assertEqual(result.status,'BLOCKED');self.assertEqual(self.rows(self.documents[0]),[])
        self.assertEqual((self.root/'retained').read_bytes(),content)
        self.assertEqual((self.root/record['ruta_prevista']).read_bytes(),content)

    def test_symlink_and_extra_hardlink_are_not_adopted(self):
        _,record,content=self.pending();path=self.root/record['ruta_prevista'];old=self.root/'retained'
        path.rename(old);path.symlink_to(old)
        self.assertEqual(self.recover(record).status,'BLOCKED');path.unlink();os.link(old,path)
        self.assertEqual(self.recover(record).status,'BLOCKED');self.assertEqual(old.read_bytes(),content)

    def test_replaced_coordination_lock_blocks_even_if_unlocked(self):
        _,record,_=self.pending();op=uuid.UUID(record['id_operacion'])
        path=self.root/'.ss12-writers'/f'{self.documents[0]}-{op.hex}.lock'
        path.rename(path.with_suffix('.retained'));path.touch(mode=0o600)
        result=self.recover(record)
        self.assertEqual((result.status,result.code),('BLOCKED','WRITER_PROTOCOL_UNPROVEN'))

    def test_foreign_actor_cannot_recover_even_with_a_real_operation_uuid(self):
        _,record,_=self.pending()
        with self.assertRaises(self.HTTPException):self.recover(record,actor=999999)
        self.assertEqual(self.rows(self.documents[0]),[])

    def change_role(self,role):
        with self.engine.begin()as c:
            c.execute(self.text("SELECT set_config('app.current_user_id','1',true)"))
            c.execute(self.text('UPDATE usuario SET rol=:role WHERE id_usuario=1'),{'role':role})

    def test_revoked_role_prevents_recovery(self):
        _,record,_=self.pending();self.change_role('visualizador')
        try:
            with self.assertRaises(self.HTTPException):self.recover(record)
            self.assertEqual(self.rows(self.documents[0]),[])
        finally:self.change_role('admin')

    def test_revocation_after_durable_intent_is_rechecked(self):
        _,record,_=self.pending();original=self.executor._intent
        def revoke(*a):
            result=original(*a);self.change_role('visualizador');return result
        try:
            with patch.object(self.executor,'_intent',side_effect=revoke):result=self.recover(record)
            self.assertEqual((result.status,result.code),('BLOCKED','AUTHORIZATION_REVOKED'))
            self.assertEqual(self.rows(self.documents[0]),[])
        finally:self.change_role('admin')

    def test_authorization_fence_prevents_concurrent_link_revocation(self):
        _,record,_=self.pending();original=self.executor._physical;observed=[]
        def verify(*a):
            try:
                with self.engine.begin()as c:
                    c.execute(self.text("SET LOCAL lock_timeout='100ms'"))
                    c.execute(self.text("SELECT set_config('app.current_user_id','1',true)"))
                    c.execute(self.text('UPDATE documento_vinculo SET activo=false WHERE id_documento=:doc'),{'doc':self.documents[0]})
            except Exception as error:observed.append(getattr(getattr(error,'orig',None),'pgcode',None))
            return original(*a)
        with patch.object(self.executor,'_physical',side_effect=verify):result=self.recover(record)
        self.assertEqual(result.status,'VERIFIED');self.assertTrue(observed);self.assertEqual(set(observed),{'55P03'})

    def test_upload_authorization_fence_prevents_revocation_before_commit(self):
        from app.services.document_storage import StagedDocument
        original=StagedDocument.publish;observed=[]
        def publish(staged,name):
            try:
                with self.engine.begin()as c:
                    c.execute(self.text("SET LOCAL lock_timeout='100ms'"))
                    c.execute(self.text("SELECT set_config('app.current_user_id','1',true)"))
                    c.execute(self.text("UPDATE usuario SET rol='visualizador' WHERE id_usuario=1"))
                observed.append('REVOCATION_COMMITTED')
            except Exception as error:
                observed.append(getattr(getattr(error,'orig',None),'pgcode',None))
            return original(staged,name)
        try:
            with patch.object(StagedDocument,'publish',publish):
                status,_=self.upload(self.documents[0],self.pdf('SS12_AUTH_RACE_SYNTHETIC'))
            self.assertEqual(observed,['55P03'])
            self.assertEqual(status,201)
            # The barrier ends at COMMIT: revocation must then work, and a new
            # recovery attempt must honor it even for the confirmed operation.
            self.change_role('visualizador')
            with self.engine.connect()as c:
                operation=c.execute(self.text('SELECT id_operacion FROM documento_operacion WHERE id_documento=:doc'),
                                    {'doc':self.documents[0]}).scalar_one()
            with self.assertRaises(self.HTTPException):
                self.recover({'id_operacion':operation})
        finally:self.change_role('admin')

    def lost_ack(self,after):
        _,record,_=self.pending();attempt=uuid.uuid4()
        from sqlalchemy.orm import Session,sessionmaker
        calls=[]
        class Interrupted(Session):
            def commit(db):
                calls.append(1)
                if len(calls)==2 and not after:raise RuntimeError('synthetic before COMMIT')
                super().commit()
                if len(calls)==2:raise RuntimeError('synthetic lost COMMIT acknowledgement')
        with patch.object(self.executor,'sessionmaker',side_effect=lambda **kw:sessionmaker(class_=Interrupted,**kw)):
            result=self.recover(record,attempt)
        return record,attempt,result

    def test_commit_acknowledgement_lost_after_server_commit_is_independently_verified(self):
        record,attempt,result=self.lost_ack(True)
        self.assertEqual(result.status,'VERIFIED');self.assertEqual(self.journal(attempt)['estado'],'confirmada')
        self.assertEqual(len(self.rows(self.documents[0])),1)

    def test_failure_before_commit_is_not_reported_success_and_same_attempt_can_retry(self):
        record,attempt,result=self.lost_ack(False)
        self.assertEqual(result.status,'PENDING');self.assertEqual(self.journal(attempt)['estado'],'pendiente')
        self.assertEqual(self.rows(self.documents[0]),[])
        self.assertEqual(self.recover(record,attempt).status,'VERIFIED')
        self.assertEqual(len(self.rows(self.documents[0])),1)

    def test_independent_verification_unavailable_never_claims_success(self):
        _,record,_=self.pending();attempt=uuid.uuid4()
        with patch.object(self.executor,'_verify',side_effect=RuntimeError('synthetic unavailable verification')):
            result=self.recover(record,attempt)
        self.assertEqual((result.status,result.code),('PENDING','INDEPENDENT_VERIFICATION_UNAVAILABLE'))
        self.assertEqual(self.journal(attempt)['estado'],'confirmada')
        self.assertEqual(self.recover(record,attempt).status,'VERIFIED')
        self.assertEqual(len(self.rows(self.documents[0])),1)

    def test_uncoordinated_legacy_operation_is_not_retroactively_trusted(self):
        import json
        def legacy(sessions,ticket,identity,authorize,**kwargs):
            with sessions()as db:
                self.service.operations._connection(db);authorize(db)
                self.service.set_audit_context(db,ticket.actor_id)
                db.execute(self.text('UPDATE documento_operacion SET identidad_archivo=CAST(:value AS jsonb),'
                    'staging_preparado_en=clock_timestamp() WHERE id_operacion=:id'),
                    {'value':json.dumps({'device':identity[0],'inode':identity[1]}),'id':ticket.id})
                db.commit()
        with patch.object(self.service.operations,'staged',side_effect=legacy):_,record,content=self.pending()
        result=self.recover(record)
        self.assertEqual((result.status,result.code),('BLOCKED','WRITER_PROTOCOL_UNPROVEN'))
        self.assertEqual((self.root/record['ruta_prevista']).read_bytes(),content)
        self.assertEqual(self.rows(self.documents[0]),[])

    def test_recovery_journal_and_coordination_are_immutable_and_not_deletable(self):
        _,record,_=self.pending();attempt=uuid.uuid4();self.assertEqual(self.recover(record,attempt).status,'VERIFIED')
        before=self.journal(attempt)
        for statement in [
            "UPDATE documento_recuperacion SET codigo='EXISTING_RESULT' WHERE id_intento=:id",
            'DELETE FROM documento_recuperacion WHERE id_intento=:id',
            'TRUNCATE documento_recuperacion',
            'UPDATE documento_coordinacion SET protocolo=1 WHERE id_operacion=:operation',
            'DELETE FROM documento_coordinacion WHERE id_operacion=:operation',
        ]:
            with self.subTest(statement=statement),self.assertRaises(Exception):
                with self.engine.begin()as c:
                    c.execute(self.text("SELECT set_config('app.current_user_id','1',true)"))
                    c.execute(self.text(statement),{'id':str(attempt),'operation':record['id_operacion']})
        self.assertEqual(self.journal(attempt),before)

    def recovery_interruption(self,phase):
        _,record,content=self.pending();attempt=uuid.uuid4()
        ctx=multiprocessing.get_context('spawn');reader,writer=ctx.Pipe(False)
        process=ctx.Process(target=interrupted_recovery,args=(self.documents[0],record['id_operacion'],attempt,str(self.root),phase,writer))
        process.start()
        try:
            self.assertTrue(reader.poll(15));self.assertEqual(reader.recv(),'fault-point-reached')
            os.kill(process.pid,signal.SIGKILL);process.join(10);self.assertEqual(process.exitcode,-signal.SIGKILL)
        finally:
            if process.is_alive():process.terminate();process.join(5)
            reader.close();writer.close()
        self.assertEqual(self.journal(attempt)['estado'],'pendiente'if phase=='before'else'confirmada')
        self.assertEqual(self.recover(record,attempt).status,'VERIFIED')
        self.assertEqual(len(self.rows(self.documents[0])),1)
        self.assertEqual((self.root/record['ruta_prevista']).read_bytes(),content)

    def test_sigkill_recovery_before_commit_retries_the_durable_attempt(self):
        self.recovery_interruption('before')

    def test_sigkill_recovery_after_commit_verifies_the_existing_attempt(self):
        self.recovery_interruption('after')

    def interrupt(self,phase):
        ctx=multiprocessing.get_context('spawn');reader,writer=ctx.Pipe(False);key=uuid.uuid4()
        process=ctx.Process(target=interrupted_upload,args=(self.documents[0],key,str(self.root),phase,writer))
        process.start()
        try:
            self.assertTrue(reader.poll(15),'Synthetic worker did not reach the named fault point')
            self.assertEqual(reader.recv(),'fault-point-reached')
            if phase=='before':
                record=self._operation_record(key);attempt=uuid.uuid4()
                result=self.recover(record,attempt)
                self.assertEqual((result.status,result.code),('PENDING','ACTIVE_WRITER'))
                self.assertEqual(self.journal(attempt)['estado'],'pendiente')
            os.kill(process.pid,signal.SIGKILL);process.join(10);self.assertEqual(process.exitcode,-signal.SIGKILL)
        finally:
            if process.is_alive():process.terminate();process.join(5)
            reader.close();writer.close()
        return self._operation_record(key)

    def test_sigkill_after_publication_before_commit_can_recover_after_worker_restart(self):
        record=self.interrupt('before');self.assertEqual(record['estado'],'pendiente')
        self.assertEqual(self.rows(self.documents[0]),[])
        result=self.recover(record);self.assertEqual((result.status,result.code),('VERIFIED','RECOVERED'))
        self.assertEqual(len(self.rows(self.documents[0])),1)

    def test_sigkill_after_commit_returns_existing_result_without_duplicate(self):
        record=self.interrupt('after');self.assertEqual(record['estado'],'confirmada')
        result=self.recover(record);self.assertEqual((result.status,result.code),('VERIFIED','EXISTING_RESULT'))
        self.assertEqual(len(self.rows(self.documents[0])),1)


if __name__=='__main__':unittest.main(verbosity=2)
