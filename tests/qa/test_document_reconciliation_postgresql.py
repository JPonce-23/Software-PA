"""Prepared 3A QA. NOT authorized by the implementation task.

Reuses disposable identity/031/actor guards and synthetic fixture construction.
Setup/upload/race simulation WRITE synthetic SQL; the reconciler itself must not.
Never auto-migrates, resets a database, or inspects old QA fixtures as abandoned.
"""
import asyncio
from dataclasses import asdict
import hashlib,json,os
from pathlib import Path
import sys,unittest,uuid
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/qa'))
import test_document_service_postgresql as publication


@unittest.skipUnless(os.getenv('SS12_QA_ENABLE')=='1','Separate disposable PostgreSQL 3A authorization required')
class DocumentReconciliationPostgreSQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        publication.DocumentServicePostgreSQL.setUpClass.__func__(cls)
        from app.services import document_reconciliation
        cls.reconciliation=document_reconciliation
        cls.audit_key=b'SS12_SYNTHETIC_RECONCILIATION_KEY_32'

    def setUp(self):publication.DocumentServicePostgreSQL.setUp(self)
    upload=publication.DocumentServicePostgreSQL.upload
    rows=publication.DocumentServicePostgreSQL.rows
    _operation_record=publication.DocumentServicePostgreSQL._operation_record

    def inspect(self,actor=None):
        return asyncio.run(self.reconciliation.reconcile_documents(self.engine,actor or self.actor,
            [self.documents[0]],self.root,audit_key=self.audit_key))
    def codes(self,report):return {finding.code for finding in report.findings}
    def records(self):
        with self.engine.connect() as connection:
            return connection.execute(self.text('SELECT to_jsonb(o) FROM documento_operacion o WHERE '
                'id_documento=:doc ORDER BY id_operacion'),{'doc':self.documents[0]}).scalars().all()
    def confirmed(self,label='3A confirmed'):
        key=uuid.uuid4();code,result=self.upload(self.documents[0],self.pdf(label),key)
        self.assertEqual(code,201);return key,result

    def test_consistent_scan_has_readonly_sessions_no_dml_and_no_engine_profile_leak(self):
        self.confirmed();before=self.records();modes=[];statements=[]
        def inspect_sql(connection,cursor,statement,parameters,context,many):
            verb=statement.lstrip().split(None,1)[0].upper();statements.append(verb)
            self.assertIn(verb,['SELECT','SHOW','SET'])
            self.assertNotIn('contrasena_hash',statement)
            check=connection.connection.cursor()
            try:check.execute('SHOW transaction_read_only');modes.append(check.fetchone()[0])
            finally:check.close()
        self.event.listen(self.engine,'before_cursor_execute',inspect_sql)
        try:report=self.inspect()
        finally:self.event.remove(self.engine,'before_cursor_execute',inspect_sql)
        self.assertEqual(self.codes(report),{'CONSISTENT'});self.assertTrue(report.complete)
        self.assertTrue(modes);self.assertEqual(set(modes),{'on'});self.assertTrue(statements)
        self.assertEqual(self.records(),before)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(self.text('SHOW transaction_read_only')).scalar_one(),'off')

    def test_confirmed_missing_file_is_observed_without_mutating_sql(self):
        key,_=self.confirmed();before=self.records();record=self._operation_record(key)
        # Fixture-only loss simulation, before invoking the read-only service.
        (self.root/record['ruta_prevista']).unlink()
        report=self.inspect();self.assertIn('MISSING_FILE',self.codes(report));self.assertEqual(self.records(),before)

    def test_corrupted_synthetic_file_reports_size_hash_and_keeps_terminal_result(self):
        key,_=self.confirmed();before=self.records();record=self._operation_record(key)
        (self.root/record['ruta_prevista']).write_bytes(b'SS12 synthetic corruption')
        report=self.inspect();self.assertTrue({'SIZE_MISMATCH','HASH_MISMATCH'}<=self.codes(report))
        self.assertEqual(self.records(),before);self.assertEqual(self._operation_record(key)['estado'],'confirmada')

    def test_unreferenced_file_is_only_a_candidate_and_is_retained(self):
        directory=self.root/str(self.documents[0]);directory.mkdir(mode=0o700)
        file=directory/('0001-'+uuid.uuid4().hex+'.pdf');file.write_bytes(self.pdf('orphan candidate'))
        before=self.records();report=self.inspect()
        self.assertIn('ORPHAN_FILE',self.codes(report));self.assertTrue(file.exists());self.assertEqual(self.records(),before)
        finding=next(f for f in report.findings if f.code=='ORPHAN_FILE')
        self.assertIn(('candidate',True),finding.evidence);self.assertEqual(finding.recommendation,'MANUAL_REVIEW_ONLY')

    def test_pending_reservation_is_not_abandoned_or_resumed(self):
        data=self.pdf('3A pending');key=uuid.uuid4()
        metadata=dict(id_documento=self.documents[0],id_usuario=self.actor,hash_sha256=hashlib.sha256(data).hexdigest(),
            tamano_bytes=len(data),nombre_original='synthetic.pdf',extension='.pdf',tipo_mime='application/pdf')
        with self.Session(self.engine) as request:sessions=self.service._upload_sessions(request)
        self.service.operations.reserve(sessions,self.documents[0],self.actor,key,metadata,
            lambda db:self.service._authorize_upload(db,self.documents[0],self.actor),client_key=True)
        before=self.records();report=self.inspect()
        self.assertTrue({'PENDING','ACTIVE_OR_UNCERTAIN_OPERATION'}<=self.codes(report))
        self.assertNotIn('ORPHAN_FILE',self.codes(report));self.assertEqual(self.records(),before)
        self.assertFalse(list(self.root.rglob('*.pdf')))

    def test_other_authorized_actor_never_receives_owners_operation_id(self):
        key,_=self.confirmed();owner=self._operation_record(key);before=self.records()
        with self.engine.begin() as connection:
            connection.execute(self.text("SELECT set_config('app.current_user_id','1',true)"))
            actor=connection.execute(self.text("INSERT INTO usuario(nombre,apellido_paterno,correo,contrasena_hash,rol,activo,observaciones) "
                "VALUES('SS12','QA',:email,'SS12_DISABLED_SYNTHETIC_HASH','admin',true,'SS12_STAGE2_SYNTHETIC_ONLY') RETURNING id_usuario"),
                {'email':'ss12-stage2-'+uuid.uuid4().hex+'@example.invalid'}).scalar_one()
        report=self.inspect(actor)
        self.assertTrue(all(f.operation_id is None for f in report.findings))
        self.assertNotIn(owner['id_operacion'],json.dumps(asdict(report)));self.assertEqual(self.records(),before)

    def test_permission_revocation_denies_scan_before_filesystem(self):
        self.confirmed();before=self.records()
        with self.engine.begin() as connection:
            connection.execute(self.text("SELECT set_config('app.current_user_id','1',true)"))
            connection.execute(self.text("UPDATE documento_vinculo SET activo=false,fecha_baja=now(),id_usuario_baja=1,"
                "motivo_baja='SS12 synthetic 3A revocation' WHERE id_documento=:doc"),{'doc':self.documents[0]})
        with patch.object(self.reconciliation,'_tree') as tree:
            with self.assertRaises(self.HTTPException) as caught:self.inspect()
            self.assertEqual(caught.exception.status_code,409);tree.assert_not_called()
        self.assertEqual(self.records(),before)

    def test_concurrent_new_upload_is_uncertain_not_missing_or_orphan(self):
        self.confirmed();real=self.reconciliation._tree
        def concurrent(*args,**kwargs):
            observed=real(*args,**kwargs)
            self.assertEqual(self.upload(self.documents[0],self.pdf('3A concurrent writer'),uuid.uuid4())[0],201)
            return observed
        with patch.object(self.reconciliation,'_tree',side_effect=concurrent):report=self.inspect()
        self.assertIn('ACTIVE_OR_UNCERTAIN_OPERATION',self.codes(report));self.assertFalse(report.complete)
        self.assertFalse(self.codes(report)&{'MISSING_FILE','ORPHAN_FILE','HASH_MISMATCH','SIZE_MISMATCH','CONSISTENT'})
        self.assertEqual(len(self.rows(self.documents[0])),2)


if __name__=='__main__':unittest.main(verbosity=2)
