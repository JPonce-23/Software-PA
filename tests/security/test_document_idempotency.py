"""Stage 2: real service/SQL repository with explicit Session/journal doubles.

No PostgreSQL, Docker or schema execution. State/persistence/concurrency doubles
demonstrate control flow only; native PostgreSQL coverage requires migration 031.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import io
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import MagicMock, patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'backend/tests'))
from _document_samples import minimal_pdf
from _document_service_support import document_service
from _document_journal_doubles import JournalDouble
import test_document_transactions as transactions
from fastapi import HTTPException,UploadFile
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import Insert
from sqlalchemy.orm import Session,make_transient_to_detached

service=document_service()
from app.services import document_operations as operations


class MemoryJournal(JournalDouble):
    """Durability and uniqueness simulator, NOT a PostgreSQL implementation."""
    key=staticmethod(operations.key)
    def __init__(self,shared=None):
        super().__init__();self.records={} if shared is None else shared;self.lock=threading.Lock()
        self.reserve.side_effect=self.begin;self.confirm.side_effect=self.prepare_commit
        self.failed.side_effect=self.fail;self.candidate=None;self.staged.side_effect=self.stage
    def begin(self,sessions,document,actor,key,metadata,authorize,**kw):
        scope=(actor,document,key);fp=operations.fingerprint(metadata)
        with self.lock:
            if scope not in self.records:
                ticket=self.ticket(sessions,document,actor,key,metadata,authorize)
                self.records[scope]=SimpleNamespace(ticket=ticket,fingerprint=fp,state='pendiente',version=None,metadata=dict(metadata),code=None,status=None,identity=None)
                return ticket
            record=self.records[scope]
            op=SimpleNamespace(**record.metadata,id_operacion=record.ticket.id,clave_idempotencia=record.ticket.key,
                huella_solicitud=record.fingerprint,estado=record.state,ruta_prevista=record.ticket.path,
                codigo_error=record.code,http_error=record.status,
                id_documento_version=record.version.id_documento_version if record.version else None)
            db=MagicMock();db.get.return_value=record.version
            return operations._result(db,op,fp)
    def stage(self,sessions,ticket,identity,authorize):
        self.records[(ticket.actor_id,ticket.document_id,ticket.key)].identity=identity
    def prepare_commit(self,db,ticket,version):self.candidate=(ticket,version)
    def commit(self):
        ticket,version=self.candidate
        record=self.records[(ticket.actor_id,ticket.document_id,ticket.key)]
        record.state='confirmada';record.version=version
    def fail(self,sessions,ticket,authorize,**kw):
        record=self.records[(ticket.actor_id,ticket.document_id,ticket.key)]
        if record.state=='confirmada':return self.decorate(record.version,ticket,replayed=True)
        if record.state=='pendiente':
            record.state='requiere_reconciliacion' if kw['uncertain'] else 'rechazada'
            record.code=kw['code'];record.status=kw['status']


class IdempotencyServiceTests(unittest.TestCase):
    populate_response=transactions.TransactionTests.populate_response
    files=transactions.TransactionTests.files
    def setUp(self):
        transactions.TransactionTests.setUp(self)
        self.fake=MemoryJournal();patch.object(service,'operations',self.fake).start()
        self.tx.commit.side_effect=self.fake.commit
        self.key=uuid.uuid4()
    def call(self,label='A',key=None,doc=7,actor=None,name='synthetic.pdf'):
        self.factory.side_effect=[self.check,self.tx]
        return asyncio.run(service.store_version(self.request,doc,
            UploadFile(io.BytesIO(minimal_pdf(label)),filename=name),actor or self.actor,
            idempotency_key=self.key if key is None else key))
    def test_first_and_confirmed_repeat_share_result_without_new_publication(self):
        first=self.call();self.assertFalse(first._idempotency_replayed)
        second=self.call();self.assertTrue(second._idempotency_replayed)
        self.assertEqual(first.id_documento_version,second.id_documento_version)
        self.assertEqual(len(self.files()),1);self.assertEqual(len(self.fake.records),1)
        self.assertEqual(self.tx.commit.call_count,1)
    def test_same_key_changed_bytes_or_name_conflicts(self):
        self.call()
        for params in [dict(label='B'),dict(name='renamed.pdf')]:
            with self.assertRaises(HTTPException) as e:self.call(**params)
            self.assertEqual(e.exception.status_code,409)
        self.assertEqual(len(self.files()),1)
    def test_different_key_same_hash_uses_existing_duplicate_policy(self):
        first=self.call();self.query.first.return_value=first
        with self.assertRaises(HTTPException) as e:self.call(key=uuid.uuid4())
        self.assertEqual(e.exception.status_code,409)
        self.assertEqual(len(self.files()),1)
        self.assertEqual(sorted(r.state for r in self.fake.records.values()),['confirmada','rechazada'])
    def test_two_workers_same_key_one_owner_other_pending(self):
        entered=threading.Event();release=threading.Event();real=service.stage_document
        @contextmanager
        def stage(*a,**kw):
            with real(*a,**kw) as staged:
                entered.set()
                if not release.wait(3):raise AssertionError('test gate timeout')
                yield staged
        with patch.object(service,'stage_document',side_effect=stage),ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(self.call)
            try:
                self.assertTrue(entered.wait(2))
                second=pool.submit(self.call)
                with self.assertRaises(HTTPException) as e:second.result(timeout=2)
                self.assertEqual(e.exception.status_code,425)
            finally:release.set()
            self.assertEqual(first.result(timeout=3).numero_version,1)
        self.assertEqual(len(self.files()),1);self.assertEqual(len(self.fake.records),1)
    def test_prepublication_error_is_terminal_and_creates_no_final(self):
        from sqlalchemy.exc import IntegrityError
        self.tx.flush.side_effect=IntegrityError('synthetic',{},Exception('fixture'))
        with self.assertRaises(HTTPException):self.call()
        self.assertFalse(self.files())
        self.tx.flush.side_effect=None
        with self.assertRaises(HTTPException) as e:self.call()
        self.assertEqual(e.exception.status_code,409);self.assertFalse(self.files())
    def test_after_publication_without_commit_requires_reconciliation(self):
        self.tx.commit.side_effect=RuntimeError('synthetic missing confirmation')
        with self.assertRaises(HTTPException):self.call()
        self.assertEqual(next(iter(self.fake.records.values())).state,'requiere_reconciliacion')
        with self.assertRaises(HTTPException) as e:self.call()
        self.assertEqual(e.exception.status_code,409);self.assertEqual(len(self.files()),1)
    def test_lost_commit_ack_recovers_confirmed_result(self):
        def commit():self.fake.commit();raise RuntimeError('injected lost ack')
        self.tx.commit.side_effect=commit
        recovered=self.call()
        self.assertTrue(recovered._idempotency_replayed)
        self.assertEqual(len(self.files()),1)
        self.assertEqual(next(iter(self.fake.records.values())).state,'confirmada')
    def test_simulated_restart_keeps_result_without_in_memory_owner_state(self):
        first=self.call();replacement=MemoryJournal(self.fake.records)
        with patch.object(service,'operations',replacement):second=self.call()
        self.assertEqual(first.id_documento_version,second.id_documento_version)
        self.assertTrue(second._idempotency_replayed);self.assertEqual(len(self.files()),1)
    def test_scope_includes_document_and_user(self):
        self.call()
        self.call(doc=8)
        other=service.models.Usuario(id_usuario=4,activo=True,rol='admin');make_transient_to_detached(other)
        self.actor_lookup.return_value=other
        self.call(label='other',actor=other)
        self.assertEqual(len(self.fake.records),3);self.assertEqual(len(self.files()),3)
    def test_replay_revalidates_permission_before_read_or_result(self):
        self.call();self.access.side_effect=HTTPException(403,'revoked')
        with self.assertRaises(HTTPException) as e:self.call()
        self.assertEqual(e.exception.status_code,403)
        self.assertEqual(len(self.files()),1)
    def test_cancelled_commit_retains_bytes_and_never_republishes(self):
        self.tx.commit.side_effect=asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):self.call()
        self.assertEqual(len(self.files()),1)
        with self.assertRaises(HTTPException):self.call()
        self.assertEqual(len(self.files()),1)
    def test_staging_checkpoint_ack_failure_never_publishes(self):
        self.fake.staged.side_effect=RuntimeError('synthetic checkpoint ack loss')
        with self.assertRaises(RuntimeError):self.call()
        self.assertFalse(self.files())
        self.assertEqual(next(iter(self.fake.records.values())).state,'requiere_reconciliacion')
        self.assertFalse(list(self.root.rglob('.pending-*')))

    def test_checkpoint_sql_timeout_is_sanitized_and_never_publishes(self):
        from sqlalchemy.exc import TimeoutError as SQLTimeoutError
        self.fake.staged.side_effect=SQLTimeoutError('synthetic private pool detail')
        with self.assertRaises(HTTPException) as e:self.call()
        self.assertEqual(e.exception.status_code,503)
        self.assertNotIn('private',e.exception.detail)
        self.assertEqual(next(iter(self.fake.records.values())).state,'requiere_reconciliacion')
        self.assertFalse(self.files())

    def test_operation_filename_only_accepts_its_own_uuid(self):
        from app.services import document_storage
        import hashlib
        content=minimal_pdf();own=uuid.uuid4();foreign=uuid.uuid4()
        with document_storage.stage_document(self.root,7,content,hashlib.sha256(content).hexdigest(),operation_id=own) as staged:
            with self.assertRaises(document_storage.DocumentStorageError):staged.publish(f'op-{foreign.hex}.pdf')
            staged.publish(f'op-{own.hex}.pdf')
        self.assertEqual((self.root/'7'/f'op-{own.hex}.pdf').read_bytes(),content)


class SQLRepositoryTests(unittest.TestCase):
    """Compiled PostgreSQL statements + Session doubles; NOT SQL execution."""
    def setUp(self):
        self.key=uuid.uuid4();self.opid=uuid.uuid4();self.authorize=MagicMock()
        self.meta=dict(id_documento=7,id_usuario=3,hash_sha256='a'*64,tamano_bytes=10,
            nombre_original='test.pdf',tipo_mime='application/pdf',extension='.pdf')
        self.fp=operations.fingerprint(self.meta)
        self.op=service.models.DocumentoOperacion(id_operacion=self.opid,clave_idempotencia=self.key,
            id_documento=7,id_usuario=3,huella_solicitud=self.fp,hash_sha256='a'*64,tamano_bytes=10,
            nombre_original='test.pdf',tipo_mime='application/pdf',extension='.pdf',estado='pendiente',
            ruta_prevista=f'7/op-{self.opid.hex}.pdf')
    def session(self,operation=None):
        db=MagicMock(spec=Session);db.__enter__.return_value=db;db.__exit__.return_value=False
        db.connection.return_value.get_isolation_level.return_value='READ COMMITTED'
        db.query.return_value.filter.return_value.first.return_value=operation
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value=operation
        return db
    def factory(self,*sessions):return MagicMock(side_effect=sessions)
    def test_upsert_reserves_one_scoped_owner_before_staging(self):
        reader=self.session();writer=self.session()
        writer.execute.return_value.scalar_one_or_none.return_value=self.opid
        with patch.object(operations.uuid,'uuid4',return_value=self.opid):
            ticket=operations.reserve(self.factory(reader,writer),7,3,self.key,self.meta,self.authorize,client_key=True)
        self.assertEqual(ticket.id,self.opid);writer.commit.assert_called_once()
        insert_call=next(c for c in writer.execute.call_args_list if isinstance(c.args[0],Insert))
        sql=str(insert_call.args[0].compile(dialect=postgresql.dialect()))
        self.assertIn('ON CONFLICT ON CONSTRAINT uq_documento_operacion_clave DO NOTHING',sql)
        self.assertIn('RETURNING documento_operacion.id_operacion',sql)
    def test_collision_returns_pending_without_granting_ownership(self):
        reader=self.session();writer=self.session();retry=self.session(self.op)
        writer.execute.return_value.scalar_one_or_none.return_value=None
        with self.assertRaises(HTTPException) as e:
            operations.reserve(self.factory(reader,writer,retry),7,3,self.key,self.meta,self.authorize,client_key=True)
        self.assertEqual(e.exception.status_code,425);self.assertEqual(e.exception.headers['Retry-After'],'3')
    def test_lost_intent_ack_does_not_authorize_publication(self):
        reader=self.session();writer=self.session();retry=self.session(self.op)
        writer.commit.side_effect=RuntimeError('lost intent ack')
        with self.assertRaises(HTTPException) as e:
            operations.reserve(self.factory(reader,writer,retry),7,3,self.key,self.meta,self.authorize,client_key=True)
        self.assertEqual(e.exception.status_code,425)
    def test_confirmed_lookup_is_authorized_and_response_detached(self):
        self.op.estado='confirmada';self.op.id_documento_version=4
        version=service.models.DocumentoVersion(id_documento_version=4,id_documento=7,id_usuario_carga=3,
            hash_sha256='a'*64,tamano_bytes=10,nombre_original='test.pdf',tipo_mime='application/pdf',
            ruta_almacenamiento=self.op.ruta_prevista)
        db=self.session(self.op);db.get.return_value=version
        result=operations.lookup(self.factory(db),7,3,self.key,self.fp,self.authorize)
        self.assertIs(result,version);self.assertTrue(result._idempotency_replayed)
        self.authorize.assert_called_once_with(db);db.expunge.assert_called_once_with(result)
    def test_scope_filters_are_not_a_global_uuid_lookup(self):
        db=self.session();operations.lookup(self.factory(db),7,3,self.key,self.fp,self.authorize)
        conditions=db.query.return_value.filter.call_args.args
        self.assertEqual({c.left.key for c in conditions},{'id_documento','id_usuario','clave_idempotencia'})
        self.assertEqual({c.left.key:c.right.value for c in conditions},
            {'id_documento':7,'id_usuario':3,'clave_idempotencia':self.key})
    def test_incompatible_parameters_and_revoked_permissions_never_replay(self):
        db=self.session(self.op)
        with self.assertRaises(HTTPException) as e:
            operations.lookup(self.factory(db),7,3,self.key,'b'*64,self.authorize)
        self.assertEqual(e.exception.status_code,409)
        self.authorize.side_effect=HTTPException(403,'denied')
        with self.assertRaises(HTTPException):operations.lookup(self.factory(db),7,3,self.key,self.fp,self.authorize)
    def test_confirm_uses_callers_transaction_and_does_not_commit_it(self):
        db=self.session();db.execute.return_value.rowcount=1
        operations.confirm(db,operations._ticket(self.op),SimpleNamespace(id_documento_version=4))
        db.commit.assert_not_called()
        statement=db.execute.call_args.args[0]
        self.assertIn('UPDATE documento_operacion',str(statement.compile(dialect=postgresql.dialect())))
    def test_pending_failure_marks_reconciliation(self):
        db=self.session(self.op)
        operations.failed(self.factory(db),operations._ticket(self.op),self.authorize,
            uncertain=True,status=409,code='PUBLICATION_UNCONFIRMED')
        self.assertEqual(self.op.estado,'requiere_reconciliacion');db.commit.assert_called_once()
    def test_confirmed_failure_resolution_never_downgrades_result(self):
        self.op.estado='confirmada';self.op.id_documento_version=4
        db=self.session(self.op)
        db.get.return_value=service.models.DocumentoVersion(id_documento_version=4,id_documento=7,id_usuario_carga=3,
            hash_sha256='a'*64,tamano_bytes=10,nombre_original='test.pdf',tipo_mime='application/pdf',
            ruta_almacenamiento=self.op.ruta_prevista)
        result=operations.failed(self.factory(db),operations._ticket(self.op),self.authorize,
            uncertain=True,status=409,code='PUBLICATION_UNCONFIRMED')
        self.assertTrue(result._idempotency_replayed)
        self.assertEqual(self.op.estado,'confirmada');db.commit.assert_not_called()
    def test_invalid_uuid_rejected(self):
        with self.assertRaises(HTTPException) as e:operations.key('not-a-uuid')
        self.assertEqual(e.exception.status_code,422)


class HTTPContractTests(unittest.TestCase):
    populate_response=transactions.TransactionTests.populate_response
    files=transactions.TransactionTests.files
    def setUp(self):
        IdempotencyServiceTests.setUp(self)
        import ast
        from fastapi import FastAPI,Depends,File,Header,Response
        from fastapi.testclient import TestClient
        node=next(n for n in ast.parse((ROOT/'backend/app/routers/documents.py').read_text()).body
            if isinstance(n,ast.AsyncFunctionDef) and n.name=='upload_version')
        node.decorator_list=[]
        def get_db():
            self.factory.side_effect=[self.check,self.tx]
            yield self.request
        ns=dict(service=service,UUID=uuid.UUID,Response=Response,UploadFile=UploadFile,
            Session=Session,models=service.models,Depends=Depends,File=File,Header=Header,
            get_db=get_db,CAPTURE_ROLES=['admin','operador'],
            auth=SimpleNamespace(RoleChecker=lambda roles:lambda:self.actor))
        tree=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),node],type_ignores=[])
        exec(compile(ast.fix_missing_locations(tree),'actual_upload_endpoint','exec'),ns)
        app=FastAPI()
        app.post('/documentos/{id_documento}/versiones',response_model=service.schemas.DocumentoVersionResponse,status_code=201)(ns['upload_version'])
        self.client=TestClient(app);self.addCleanup(self.client.close)
    def post(self,key=None,content=None):
        return self.client.post('/documentos/7/versiones',
            headers={} if key is None else {'Idempotency-Key':str(key)},
            files={'archivo':('synthetic.pdf',minimal_pdf() if content is None else content,'application/pdf')})
    def test_first_201_repeat_200_same_body_and_key(self):
        first=self.post(self.key);second=self.post(self.key)
        self.assertEqual((first.status_code,second.status_code),(201,200))
        self.assertEqual(first.json(),second.json())
        self.assertEqual(first.headers['Idempotency-Key'],str(self.key))
        self.assertEqual(second.headers['Idempotency-Replayed'],'true')
        self.assertEqual(len(self.files()),1)

    def test_invalid_header_422_and_legacy_generated_key(self):
        self.assertEqual(self.post('invalid').status_code,422)
        legacy=self.post();self.assertEqual(legacy.status_code,201)
        uuid.UUID(legacy.headers['Idempotency-Key'])
        self.assertFalse(next(iter(self.fake.records.values())).ticket.key is None)
    def test_replay_denied_after_access_revocation(self):
        self.assertEqual(self.post(self.key).status_code,201)
        self.access.side_effect=HTTPException(403,'revoked')
        self.assertEqual(self.post(self.key).status_code,403)
        self.assertEqual(len(self.files()),1)


class CORSContractTests(unittest.TestCase):
    def test_explicit_upload_and_download_headers_preserve_restricted_origins(self):
        import ast
        from starlette.applications import Starlette
        from starlette.middleware.cors import CORSMiddleware
        from starlette.testclient import TestClient
        tree=ast.parse((ROOT/'backend/app/main.py').read_text())
        call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
            and n.func.attr=='add_middleware' and n.args and isinstance(n.args[0],ast.Name) and n.args[0].id=='CORSMiddleware')
        options={k.arg:ast.literal_eval(k.value) for k in call.keywords if k.arg!='allow_origins'}
        self.assertEqual(options['allow_headers'],['Content-Type','X-CSRF-Token','Idempotency-Key','Range','If-Range'])
        self.assertEqual(options['allow_methods'],['GET','HEAD','POST','PUT','PATCH','DELETE','OPTIONS'])
        self.assertTrue(options['allow_credentials'])
        app=CORSMiddleware(Starlette(),allow_origins=['https://qa.invalid'],**options)
        with TestClient(app) as client:
            headers={'Origin':'https://qa.invalid','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Idempotency-Key,X-CSRF-Token'}
            self.assertEqual(client.options('/documentos/7/versiones',headers=headers).status_code,200)
            headers['Origin']='https://outside.invalid'
            self.assertEqual(client.options('/documentos/7/versiones',headers=headers).status_code,400)


if __name__=='__main__':unittest.main()
