"""Stage 2 closure: real HTTP/worker/POSIX, explicit SQL/journal/auth doubles.

No PostgreSQL, Docker, dotenv, app startup or migrations. PostgreSQL enforcement
is intentionally tested separately by the opt-in native integration methods.
"""
from pathlib import Path
import hashlib,json,sys,unittest,uuid
from types import SimpleNamespace
from unittest.mock import MagicMock,patch

sys.path.insert(0,str(Path(__file__).parent))
import test_document_idempotency as existing
from fastapi import HTTPException
from app.services import document_errors as errors
operations=existing.operations
service=existing.service


class HTTPErrorCodeTests(unittest.TestCase):
    def fixture(self):
        case=existing.HTTPContractTests('test_first_201_repeat_200_same_body_and_key')
        case.setUp();self.addCleanup(case.doCleanups)
        return case
    def code(self,response,expected,status):
        self.assertEqual(response.status_code,status)
        self.assertEqual(response.headers[errors.HEADER],expected)
        self.assertIsInstance(response.json()['detail'],str)
        self.assertFalse(any(name in response.headers for name in ['X-Document-Operation-Id','X-Document-Path','X-Document-Hash']))
    def test_duplicate_first_response_and_rejected_retry_keep_code_without_publishing(self):
        c=self.fixture();first=c.post(c.key);self.assertEqual(first.status_code,201)
        c.query.first.return_value=SimpleNamespace(id_documento_version=1)
        other=uuid.uuid4();response=c.post(other)
        self.code(response,errors.DOCUMENT_DUPLICATE,409)
        self.assertEqual(response.json()['detail'],'Esta versión ya fue cargada')
        record=c.fake.records[(3,7,other)];snapshot=(record.state,record.code,record.status,record.version,record.identity)
        c.query.first.return_value=None  # A retry must not attempt a new INSERT even if SHA lookup would now miss.
        again=c.post(other);self.code(again,errors.DOCUMENT_DUPLICATE,409)
        self.assertEqual((record.state,record.code,record.status,record.version,record.identity),snapshot)
        self.assertEqual(c.tx.flush.call_count,1);self.assertEqual(c.tx.commit.call_count,1)
        self.assertEqual(len(c.files()),1)
    def test_exact_sql_sha_unique_violation_and_retry_are_duplicate(self):
        from sqlalchemy.exc import IntegrityError
        c=self.fixture()
        original=SimpleNamespace(pgcode='23505',diag=SimpleNamespace(constraint_name='uq_documento_hash'))
        c.tx.flush.side_effect=IntegrityError('synthetic',{},original)
        self.code(c.post(c.key),errors.DOCUMENT_DUPLICATE,409)
        c.tx.flush.side_effect=None
        self.code(c.post(c.key),errors.DOCUMENT_DUPLICATE,409)
        self.assertEqual(c.tx.flush.call_count,1);self.assertFalse(c.files())
    def test_other_sql_integrity_conflict_is_not_guessed_as_duplicate(self):
        from sqlalchemy.exc import IntegrityError
        c=self.fixture()
        original=SimpleNamespace(pgcode='23505',diag=SimpleNamespace(constraint_name='uq_documento_version'))
        c.tx.flush.side_effect=IntegrityError('synthetic',{},original)
        self.code(c.post(c.key),errors.DOCUMENT_INTEGRITY_CONFLICT,409)
        c.tx.flush.side_effect=None
        self.code(c.post(c.key),errors.DOCUMENT_INTEGRITY_CONFLICT,409)
        self.assertFalse(c.files())
    def test_key_incompatible_first_and_repeat_preserve_original_intent(self):
        c=self.fixture();self.assertEqual(c.post(c.key).status_code,201)
        record=c.fake.records[(3,7,c.key)]
        snapshot=(record.state,dict(record.metadata),record.fingerprint,record.version.id_documento_version)
        for _ in range(2):self.code(c.post(c.key,existing.minimal_pdf('different')),errors.DOCUMENT_IDEMPOTENCY_CONFLICT,409)
        self.assertEqual((record.state,record.metadata,record.fingerprint,record.version.id_documento_version),snapshot)
        self.assertEqual(len(c.files()),1);self.assertEqual(c.tx.commit.call_count,1)
    def test_postpublication_error_and_retry_have_reconciliation_code_and_keep_evidence(self):
        c=self.fixture();c.tx.commit.side_effect=RuntimeError('synthetic private driver detail')
        for _ in range(2):
            response=c.post(c.key);self.code(response,errors.DOCUMENT_RECONCILIATION_REQUIRED,409)
            self.assertNotIn('private',response.text)
        record=c.fake.records[(3,7,c.key)]
        file=c.files()[0]
        self.assertEqual(record.state,'requiere_reconciliacion')
        self.assertEqual(record.ticket.path,str(file.relative_to(c.root)))
        self.assertEqual(record.metadata['hash_sha256'],hashlib.sha256(file.read_bytes()).hexdigest())
        self.assertEqual(record.metadata['tamano_bytes'],file.stat().st_size)
        self.assertEqual(record.identity,(file.stat().st_dev,file.stat().st_ino))
        self.assertIsNone(record.version);self.assertEqual(c.tx.commit.call_count,1)
    def test_pending_425_is_stable_and_never_stages_on_repeat(self):
        c=self.fixture()
        content=existing.minimal_pdf()
        meta=dict(id_documento=7,id_usuario=3,hash_sha256=hashlib.sha256(content).hexdigest(),
            tamano_bytes=len(content),nombre_original='synthetic.pdf',extension='.pdf',tipo_mime='application/pdf')
        c.fake.begin(None,7,3,c.key,meta,None)
        with patch.object(service,'stage_document') as staging:
            for _ in range(2):
                response=c.post(c.key);self.code(response,errors.DOCUMENT_OPERATION_PENDING,425)
                self.assertEqual(response.headers['Retry-After'],'3')
            staging.assert_not_called()
        self.assertFalse(c.files());self.assertEqual(c.fake.records[(3,7,c.key)].state,'pendiente')
    def test_failed_intent_persistence_uses_fresh_lookup_before_any_staging(self):
        c=self.fixture();factory=existing.SQLRepositoryTests()
        reader=factory.session();writer=factory.session();fresh=factory.session()
        writer.commit.side_effect=RuntimeError('synthetic private intent failure')
        # Run the REAL reserve repository with explicit Session doubles.
        c.fake.reserve.side_effect=lambda sessions,*a,**kw:operations.reserve(MagicMock(side_effect=[reader,writer,fresh]),*a,**kw)
        with patch.object(service,'stage_document') as staging,patch.object(service,'upload_root') as root:
            response=c.post(c.key)
            self.assertEqual(response.status_code,503);self.assertNotIn('private',response.text)
            staging.assert_not_called();root.assert_not_called()
        writer.commit.assert_called_once();fresh.query.assert_called_once()
        self.assertFalse(c.files());self.assertFalse(c.fake.records)
    def test_lost_confirmed_ack_and_subsequent_retry_do_not_create_another_version(self):
        c=self.fixture()
        def commit():c.fake.commit();raise RuntimeError('injected lost acknowledgement')
        c.tx.commit.side_effect=commit
        first=c.post(c.key);second=c.post(c.key)
        self.assertEqual((first.status_code,second.status_code),(200,200))
        self.assertEqual(first.json(),second.json())
        self.assertNotIn(errors.HEADER,first.headers);self.assertNotIn(errors.HEADER,second.headers)
        self.assertEqual(c.tx.commit.call_count,1);self.assertEqual(len(c.files()),1)
    def test_revoked_permission_before_recovery_does_not_expose_old_result(self):
        c=self.fixture();first=c.post(c.key);self.assertEqual(first.status_code,201)
        c.access.side_effect=HTTPException(403,'denied')
        response=c.post(c.key)
        self.assertEqual(response.status_code,403)
        self.assertEqual(response.json(),{'detail':'denied'})
        self.assertNotIn('X-Document-Operation-Id',response.headers)
        self.assertNotIn(first.json()['hash_sha256'],response.text)
        self.assertEqual(c.tx.commit.call_count,1)
    def test_generic_upload_conflict_is_not_misclassified_as_duplicate_or_reconciliation(self):
        c=self.fixture();c.access.side_effect=HTTPException(409,'Documento sin vínculo activo')
        self.code(c.post(c.key),errors.DOCUMENT_REQUEST_CONFLICT,409)
        self.assertFalse(c.files());self.assertFalse(c.fake.records)


class RepositoryNegativeTests(unittest.TestCase):
    def fixture(self):
        case=existing.SQLRepositoryTests();case.setUp();return case
    def test_rejected_operation_failure_handling_is_read_only_and_terminal(self):
        c=self.fixture();c.op.estado='rechazada';c.op.codigo_error=errors.DOCUMENT_DUPLICATE;c.op.http_error=409
        before=dict(c.op.__dict__);db=c.session(c.op)
        result=operations.failed(c.factory(db),operations._ticket(c.op),c.authorize,
            uncertain=True,status=409,code='PUBLICATION_UNCONFIRMED')
        self.assertIsNone(result);self.assertEqual(c.op.__dict__,before)
        db.commit.assert_not_called();db.get.assert_not_called()
    def test_legacy_rejection_diagnostic_is_not_guessed_or_exposed(self):
        c=self.fixture();c.op.estado='rechazada';c.op.codigo_error='PREPUBLICATION_REJECTED';c.op.http_error=409
        before=dict(c.op.__dict__);db=c.session(c.op)
        with self.assertRaises(HTTPException) as caught:operations._result(db,c.op,c.fp)
        self.assertEqual(caught.exception.headers[errors.HEADER],errors.DOCUMENT_OPERATION_REJECTED)
        self.assertNotIn('PREPUBLICATION_REJECTED',str(caught.exception.detail))
        self.assertEqual(c.op.__dict__,before);db.get.assert_not_called();db.commit.assert_not_called()
    def test_other_actor_or_document_scope_cannot_return_another_operations_result(self):
        c=self.fixture();db=c.session()  # Scoped SQL query yields no row.
        self.assertIsNone(operations.lookup(c.factory(db),8,4,c.key,c.fp,c.authorize))
        filters=db.query.return_value.filter.call_args.args
        self.assertEqual({x.left.key:x.right.value for x in filters},
            {'id_documento':8,'id_usuario':4,'clave_idempotencia':c.key})
        db.get.assert_not_called();db.commit.assert_not_called()
    def test_recovery_authorization_failure_precedes_operation_query(self):
        c=self.fixture();db=c.session(c.op);c.authorize.side_effect=HTTPException(403,'denied')
        with self.assertRaises(HTTPException) as caught:operations.lookup(c.factory(db),7,3,c.key,c.fp,c.authorize)
        self.assertEqual(caught.exception.status_code,403);db.query.assert_not_called();db.get.assert_not_called()
    def test_confirmed_record_with_wrong_version_metadata_is_not_returned(self):
        c=self.fixture();c.op.estado='confirmada';c.op.id_documento_version=1;db=c.session(c.op)
        db.get.return_value=None
        with self.assertRaises(HTTPException) as caught:operations._result(db,c.op,c.fp)
        self.assertEqual(caught.exception.headers[errors.HEADER],errors.DOCUMENT_RECONCILIATION_REQUIRED)
        db.commit.assert_not_called()


class CORSResponseTests(unittest.TestCase):
    def test_real_error_response_exposes_code_for_allowed_origin_only(self):
        import ast
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from starlette.middleware.cors import CORSMiddleware
        tree=ast.parse((existing.ROOT/'backend/app/main.py').read_text())
        call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='add_middleware' and n.args and getattr(n.args[0],'id',None)=='CORSMiddleware')
        options={k.arg:ast.literal_eval(k.value) for k in call.keywords if k.arg!='allow_origins'}
        self.assertIn(errors.HEADER,options['expose_headers'])
        app=FastAPI();app.add_middleware(CORSMiddleware,allow_origins=['https://qa.invalid'],**options)
        @app.get('/error')
        def endpoint():raise errors.document_error(409,'Mensaje compatible',errors.DOCUMENT_DUPLICATE)
        with TestClient(app) as client:
            allowed=client.get('/error',headers={'Origin':'https://qa.invalid'})
            self.assertEqual(allowed.json(),{'detail':'Mensaje compatible'})
            self.assertEqual(allowed.headers[errors.HEADER],errors.DOCUMENT_DUPLICATE)
            self.assertIn(errors.HEADER,allowed.headers['Access-Control-Expose-Headers'])
            self.assertEqual(allowed.headers['Access-Control-Allow-Origin'],'https://qa.invalid')
            denied=client.get('/error',headers={'Origin':'https://outside.invalid'})
            self.assertNotIn('Access-Control-Allow-Origin',denied.headers)
