"""Prepared 3B QA only; NEVER run without separate execution authorization.

Reuses native service fixtures and disposable identity/031 guards. Fixture SQL
writes are synthetic; the actual coordinator must use read-only transactions.
No schema change, Docker lifecycle, real recovery, migration or database reset.
"""
import asyncio
from dataclasses import asdict
import hashlib
import multiprocessing
import os
from pathlib import Path
import sys
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/qa'))
import test_document_service_postgresql as publication

KEY = b'SS12_SYNTHETIC_RECOVERY_AUDIT_KEY_32'
AUTHORIZED = os.getenv('SS12_QA_ENABLE') == '1' and os.getenv('SS12_QA_RECOVERY_DRY_RUN_ENABLE') == '1'


def _process_evaluate(document, operation, root, queue):
    """Spawned process: new real engine, identity verification, no fixture writes."""
    engine = None
    try:
        if not (os.getenv('SS12_QA_ENABLE') == '1' and os.getenv('SS12_QA_RECOVERY_DRY_RUN_ENABLE') == '1'
                and os.getenv('APP_ENV') == 'test' and os.getenv('SS12_QA_DATABASE') == 'software_pa_test'
                and os.getenv('SS12_QA_ALLOW_DATABASE') == 'software_pa_test'
                and os.getenv('SS12_QA_USER') == 'ss12_runner' and os.getenv('SS12_QA_ACTOR_ID') == '1'):
            raise RuntimeError('Explicit 3B disposable authorization required')
        from sqlalchemy import create_engine, text
        from sqlalchemy.engine import URL
        from _document_service_support import document_service
        document_service()
        from app.services.document_recovery import evaluate_recovery
        host = os.getenv('SS12_QA_SOCKET_DIR')
        if host:
            import stat
            socket = Path(host)
            if not (socket.is_absolute() and socket.resolve() == socket and str(socket).startswith('/tmp/')
                    and socket.stat().st_uid == os.getuid() and stat.S_IMODE(socket.stat().st_mode) == 0o700):
                raise RuntimeError('Unsafe private QA socket')
        else:
            host = os.environ['SS12_QA_HOST']
            if host not in ('127.0.0.1', 'localhost'):
                raise RuntimeError('Only explicit local QA connection permitted')
        engine = create_engine(URL.create('postgresql+psycopg2', host=host,
            port=int(os.environ['SS12_QA_PORT']), database='software_pa_test', username='ss12_runner',
            password=os.environ['SS12_QA_PASSWORD']), hide_parameters=True,
            connect_args={'connect_timeout': 5})
        with engine.connect() as connection:
            identity = connection.execute(text("SELECT current_database(),current_setting('cluster_name'),"
                "current_setting('server_version_num'),current_user")).one()
            if tuple(identity) != ('software_pa_test', 'ss12-document-disposable', '150004', 'ss12_runner'):
                raise RuntimeError('Disposable child database identity mismatch')
            lineage = connection.execute(text("SELECT checksum_sha256 FROM schema_migrations WHERE version='031'")).scalar_one()
            if lineage != hashlib.sha256((ROOT / 'backend/db/migrations/031_operaciones_documentales.sql').read_bytes()).hexdigest():
                raise RuntimeError('031 mismatch; never auto-apply')
            actor = connection.execute(text("SELECT count(*) FROM usuario WHERE id_usuario=1 AND activo AND rol='admin' "
                "AND correo='ss12-qa@example.invalid' AND observaciones='SS12_SYNTHETIC_DISPOSABLE_ONLY'")).scalar_one()
            if actor != 1:
                raise RuntimeError('Synthetic actor mismatch')
        result = asyncio.run(evaluate_recovery(engine, 1, document, operation, root, audit_key=KEY))
        queue.put(('OK', asdict(result)))
    except Exception as error:
        # Never send DSNs, SQL parameters, original driver errors or file paths.
        queue.put(('BLOCKED', type(error).__name__))
    finally:
        if engine is not None:
            engine.dispose()


@unittest.skipUnless(AUTHORIZED, 'Separate SS12_QA_RECOVERY_DRY_RUN_ENABLE=1 authorization required')
class DocumentRecoveryPostgreSQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        publication.DocumentServicePostgreSQL.setUpClass.__func__(cls)
        from app.services import document_recovery
        cls.recovery = document_recovery
        with cls.engine.connect() as connection:
            if connection.execute(cls.text("SHOW server_version_num")).scalar_one() != '150004':
                raise RuntimeError('3B QA requires verified PostgreSQL 15.4')

    def setUp(self):
        publication.DocumentServicePostgreSQL.setUp(self)

    upload = publication.DocumentServicePostgreSQL.upload
    rows = publication.DocumentServicePostgreSQL.rows
    _operation_record = publication.DocumentServicePostgreSQL._operation_record

    def confirmed(self, label='3B confirmed'):
        key = uuid.uuid4()
        status, result = self.upload(self.documents[0], self.pdf(label), key)
        self.assertEqual(status, 201)
        return key, result, self._operation_record(key)

    def evaluate(self, record, actor=None, **kwargs):
        return asyncio.run(self.recovery.evaluate_recovery(self.engine, actor or self.actor,
            self.documents[0], record['id_operacion'], self.root, audit_key=KEY, **kwargs))

    def records(self):
        with self.engine.connect() as connection:
            return connection.execute(self.text("SELECT jsonb_build_object('operations',"
                "(SELECT coalesce(jsonb_agg(to_jsonb(o) ORDER BY id_operacion),'[]'::jsonb) FROM documento_operacion o WHERE id_documento=:doc),"
                "'versions',(SELECT coalesce(jsonb_agg(to_jsonb(v) ORDER BY id_documento_version),'[]'::jsonb) "
                "FROM documento_version v WHERE id_documento=:doc))"), {'doc': self.documents[0]}).scalar_one()

    def reserve(self, label='3B pending'):
        data, key = self.pdf(label), uuid.uuid4()
        metadata = dict(id_documento=self.documents[0], id_usuario=self.actor,
            hash_sha256=hashlib.sha256(data).hexdigest(), tamano_bytes=len(data), nombre_original='synthetic.pdf',
            extension='.pdf', tipo_mime='application/pdf')
        with self.Session(self.engine) as request:
            sessions = self.service._upload_sessions(request)
        self.service.operations.reserve(sessions, self.documents[0], self.actor, key, metadata,
            lambda db: self.service._authorize_upload(db, self.documents[0], self.actor), client_key=True)
        return self._operation_record(key)

    def test_confirmed_result_readonly_no_dml_and_idempotent(self):
        key, result, record = self.confirmed()
        before = self.records()
        modes = []
        def observe(connection, cursor, statement, parameters, context, many):
            self.assertEqual(statement.lstrip().split(None, 1)[0].upper(), 'SELECT')
            self.assertNotIn('FOR UPDATE', statement.upper())
            check = connection.connection.cursor()
            try:
                check.execute('SHOW transaction_read_only')
                modes.append(check.fetchone()[0])
            finally:
                check.close()
        self.event.listen(self.engine, 'before_cursor_execute', observe)
        try:
            first, second = self.evaluate(record), self.evaluate(record)
        finally:
            self.event.remove(self.engine, 'before_cursor_execute', observe)
        self.assertEqual(first, second)
        self.assertEqual(first.existing_result.version_id, result.id_documento_version)
        self.assertTrue(modes)
        self.assertEqual(set(modes), {'on'})
        self.assertEqual(self.records(), before)

    def test_two_spawned_processes_return_same_existing_result_without_writes(self):
        _, _, record = self.confirmed()
        before = self.records()
        context = multiprocessing.get_context('spawn')
        queue = context.Queue()
        jobs = [context.Process(target=_process_evaluate, args=(self.documents[0], record['id_operacion'], str(self.root), queue)) for _ in range(2)]
        try:
            for job in jobs:
                job.start()
            for job in jobs:
                job.join(timeout=30)
                self.assertFalse(job.is_alive(), 'Unexpected child retained; no automatic termination')
                self.assertEqual(job.exitcode, 0)
            results = [queue.get(timeout=3) for _ in jobs]
            self.assertTrue(all(status == 'OK' for status, _ in results))
            self.assertEqual(results[0][1], results[1][1])
            self.assertEqual(self.records(), before)
        finally:
            queue.close()

    def test_pending_writer_row_lock_does_not_prove_abandonment(self):
        record = self.reserve()
        before = self.records()
        with self.engine.connect() as writer:
            writer.execute(self.text('SELECT id_documento FROM documento WHERE id_documento=:doc FOR UPDATE'), {'doc': self.documents[0]})
            writer.execute(self.text('SELECT id_operacion FROM documento_operacion WHERE id_operacion=:id FOR UPDATE'), {'id': record['id_operacion']})
            plan = self.evaluate(record)
            self.assertIn('ACTIVE_OR_UNCERTAIN_OPERATION', plan.diagnostics)
            self.assertEqual(plan.proposed_action, 'WAIT_AND_REVIEW')
            self.assertFalse(plan.transition_enabled)
        self.assertEqual(self.records(), before)

    def test_relation_lock_timeout_returns_specific_incomplete_diagnostic(self):
        _, _, record = self.confirmed()
        before = self.records()
        with self.engine.connect() as blocker:
            blocker.execute(self.text("SET LOCAL lock_timeout='500ms'"))
            blocker.execute(self.text('LOCK TABLE documento_operacion IN ACCESS EXCLUSIVE MODE'))
            plan = self.evaluate(record, limits=self.recovery.observation.Limits(lock_ms=100, statement_ms=1000))
        self.assertEqual(plan.diagnostics, ('LOCK_TIMEOUT',))
        self.assertFalse(plan.complete)
        self.assertIsNone(plan.operation_id)
        self.assertEqual(self.records(), before)

    def test_revoked_link_denies_before_physical_inspection(self):
        _, _, record = self.confirmed()
        with self.engine.begin() as connection:
            connection.execute(self.text("SELECT set_config('app.current_user_id','1',true)"))
            connection.execute(self.text("UPDATE documento_vinculo SET activo=false,fecha_baja=now(),id_usuario_baja=1,"
                "motivo_baja='SS12 synthetic 3B revocation' WHERE id_documento=:doc"), {'doc': self.documents[0]})
        before = self.records()
        with patch.object(self.recovery, '_physical') as physical:
            with self.assertRaises(self.HTTPException):
                self.evaluate(record)
            physical.assert_not_called()
        self.assertEqual(self.records(), before)

    def test_foreign_operation_is_denied_even_for_authorized_business_admin(self):
        _, _, record = self.confirmed()
        before = self.records()
        with self.engine.begin() as connection:
            connection.execute(self.text("SELECT set_config('app.current_user_id','1',true)"))
            actor = connection.execute(self.text("INSERT INTO usuario(nombre,apellido_paterno,correo,contrasena_hash,rol,activo,observaciones) "
                "VALUES('SS12','QA',:email,'SS12_DISABLED_SYNTHETIC_HASH','admin',true,'SS12_STAGE2_SYNTHETIC_ONLY') RETURNING id_usuario"),
                {'email': 'ss12-stage2-' + uuid.uuid4().hex + '@example.invalid'}).scalar_one()
        with patch.object(self.recovery, '_physical') as physical:
            with self.assertRaises(self.HTTPException) as error:
                self.evaluate(record, actor=actor)
            self.assertEqual(error.exception.status_code, 404)
            physical.assert_not_called()
        self.assertEqual(self.records(), before)

    def test_postpublication_unconfirmed_transaction_is_retained_not_adopted(self):
        fixture = self
        base = self.Session
        class BeforeCommitFailure(base):
            def commit(session):
                if any(isinstance(v, fixture.service.models.DocumentoVersion) for v in session.identity_map.values()):
                    raise RuntimeError('SS12 3B injected precommit failure after publication')
                super().commit()
        original, key = self.service.sessionmaker, uuid.uuid4()
        with patch.object(self.service, 'sessionmaker', side_effect=lambda **kw: original(class_=BeforeCommitFailure, **kw)):
            status, _ = self.upload(self.documents[0], self.pdf('3B uncertain commit'), key)
        self.assertEqual(status, 409)
        record = self._operation_record(key)
        self.assertEqual(record['estado'], 'requiere_reconciliacion')
        before = self.records()
        file = self.root / record['ruta_prevista']
        data = file.read_bytes()
        plan = self.evaluate(record)
        self.assertIn('RECONCILIATION_REQUIRED', plan.diagnostics)
        self.assertIn(self.recovery.PUBLISHED_WITHOUT_CONFIRMATION, plan.diagnostics)
        self.assertIsNone(plan.existing_result)
        self.assertEqual(self.records(), before)
        self.assertEqual(file.read_bytes(), data)

    def test_concurrent_new_upload_between_samples_is_incomplete(self):
        _, _, record = self.confirmed()
        real = self.recovery._physical
        calls = 0
        def physical(*args):
            nonlocal calls
            value = real(*args)
            calls += 1
            if calls == 1:
                self.assertEqual(self.upload(self.documents[0], self.pdf('3B concurrent writer'), uuid.uuid4())[0], 201)
            return value
        with patch.object(self.recovery, '_physical', side_effect=physical):
            plan = self.evaluate(record)
        self.assertEqual(plan.diagnostics, ('ACTIVE_OR_UNCERTAIN_OPERATION',))
        self.assertIsNone(plan.existing_result)
        self.assertEqual(len(self.rows(self.documents[0])), 2)

    def test_pending_without_file_does_not_create_staging_or_version(self):
        record = self.reserve()
        before = self.records()
        plan = self.evaluate(record)
        self.assertIn('PENDING', plan.diagnostics)
        self.assertIn('MISSING_FILE', plan.diagnostics)
        self.assertEqual(self.records(), before)
        self.assertFalse(list(self.root.rglob('*')))

    def test_confirmed_missing_or_corrupt_file_does_not_modify_terminal_result(self):
        _, _, record = self.confirmed()
        before = self.records()
        file = self.root / record['ruta_prevista']
        file.write_bytes(b'SS12 synthetic corruption')
        plan = self.evaluate(record)
        self.assertIn('HASH_MISMATCH', plan.diagnostics)
        self.assertIn('SIZE_MISMATCH', plan.diagnostics)
        self.assertIsNone(plan.existing_result)
        file.unlink()  # Fixture-only simulation; coordinator must never do this.
        self.assertIn('MISSING_FILE', self.evaluate(record).diagnostics)
        self.assertEqual(self.records(), before)

    def test_lost_commit_ack_recovers_existing_result_without_second_publication(self):
        fixture, base = self, self.Session
        class LostAck(base):
            def commit(session):
                is_version = any(isinstance(v, fixture.service.models.DocumentoVersion) for v in session.identity_map.values())
                super().commit()
                if is_version:
                    raise RuntimeError('SS12 3B injected lost acknowledgement AFTER real COMMIT')
        original, key = self.service.sessionmaker, uuid.uuid4()
        with patch.object(self.service, 'sessionmaker', side_effect=lambda **kw: original(class_=LostAck, **kw)):
            self.assertIn(self.upload(self.documents[0], self.pdf('3B lost ack'), key)[0], (200, 201))
        record = self._operation_record(key)
        before = self.records()
        self.assertEqual(record['estado'], 'confirmada')
        first, second = self.evaluate(record), self.evaluate(record)
        self.assertEqual(first, second)
        self.assertEqual(first.existing_result.version_id, record['id_documento_version'])
        self.assertEqual(self.records(), before)
        self.assertEqual(len(list(self.root.rglob('*.pdf'))), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
