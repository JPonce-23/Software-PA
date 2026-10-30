"""PREPARED ONLY: disposable PostgreSQL contract tests, never run implicitly.

Standalone unittest file outside backend/tests/conftest.py. Requires explicit
SS12_QA_ENABLE=1 and dedicated QA_* connection fields; never loads .env or app's
engine. Checks cluster identity BEFORE creating synthetic document rows. Leaves
committed QA rows; discard the disposable cluster after the authorized run.

These are SQL/publication protocol tests, not native FastAPI/RBAC tests.
"""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
ENABLED = os.getenv('SS12_QA_ENABLE') == '1'
DATABASE = 'software_pa_test'
CLUSTER = 'ss12-document-disposable'


@unittest.skipUnless(ENABLED, 'Requires explicit disposable SS12 PostgreSQL QA authorization')
class PostgreSQLContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (os.getenv('APP_ENV') != 'test' or os.getenv('SS12_QA_DATABASE') != DATABASE
                or os.getenv('SS12_QA_ALLOW_DATABASE') != DATABASE):
            raise RuntimeError('Explicit disposable QA database authorization required')
        host = os.getenv('SS12_QA_HOST')
        if host not in ('127.0.0.1', 'localhost', 'db'):
            raise RuntimeError('Only explicitly authorized local/lab QA hosts allowed')
        for key in ['SS12_QA_PORT', 'SS12_QA_USER', 'SS12_QA_PASSWORD', 'SS12_QA_ACTOR_ID']:
            if not os.getenv(key): raise RuntimeError(key + ' is required')
        port, cls.actor = int(os.environ['SS12_QA_PORT']), int(os.environ['SS12_QA_ACTOR_ID'])
        if not 0 < port < 65536 or cls.actor <= 0: raise RuntimeError('Invalid QA port/actor')
        # Imports happen after opt-in/validation. No app.database or dotenv.
        from sqlalchemy import create_engine, text
        from sqlalchemy.engine import URL
        from sqlalchemy.exc import IntegrityError, OperationalError
        from sqlalchemy.orm import Session
        from app.services import document_storage, document_validation
        cls.text, cls.Session = staticmethod(text), Session
        cls.IntegrityError, cls.OperationalError = IntegrityError, OperationalError
        cls.storage, cls.validation = document_storage, document_validation
        spec = importlib.util.spec_from_file_location('ss12_synthetic_samples', ROOT / 'backend/tests/_document_samples.py')
        samples = importlib.util.module_from_spec(spec); spec.loader.exec_module(samples)
        cls.pdf = staticmethod(samples.minimal_pdf)
        cls.engine = create_engine(URL.create('postgresql+psycopg2', host=host, port=port,
            database=DATABASE, username=os.environ['SS12_QA_USER'], password=os.environ['SS12_QA_PASSWORD']),
            hide_parameters=True, echo=False, echo_pool=False, pool_size=4, max_overflow=0,
            pool_timeout=3, isolation_level='READ COMMITTED',
            connect_args={'connect_timeout': 3, 'options': '-c statement_timeout=3000 -c lock_timeout=1000'})
        cls.addClassCleanup(cls.engine.dispose)
        with cls.engine.connect() as connection:
            actual = connection.execute(text("SELECT current_database(), current_setting('cluster_name')")).one()
            if tuple(actual) != (DATABASE, CLUSTER):
                raise RuntimeError('Refusing unverified/non-disposable QA cluster')
            actor = connection.execute(text("SELECT 1 FROM usuario WHERE id_usuario=:actor AND activo AND rol='admin'"),
                {'actor': cls.actor}).scalar()
            if actor != 1: raise RuntimeError('Explicit active synthetic QA admin required')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.documents = []
        with self.engine.begin() as connection:
            connection.execute(self.text("SELECT set_config('app.current_user_id', :actor, true)"), {'actor': str(self.actor)})
            for _ in range(2):
                self.documents.append(connection.execute(self.text(
                    "INSERT INTO documento(tipo_documento,estado,titulo,creado_por) "
                    "VALUES ('ss12_qa','disponible',:marker,:actor) RETURNING id_documento"),
                    {'marker': 'SS12_SYNTHETIC_' + uuid.uuid4().hex, 'actor': self.actor}).scalar_one())

    def protocol(self, document_id, content, *, proposed=False, barrier=None):
        """Reference SQL protocol: current order vs proposed parent-lock order.

        It does not import/replace the actual service. Native API acceptance must
        separately exercise store_version against the same disposable cluster.
        """
        checksum = hashlib.sha256(content).hexdigest()
        mime = self.validation.validate_document(content, '.pdf', None, max_file_bytes=1048576)
        with self.storage.stage_document(self.root, document_id, content, checksum) as staged:
            with self.Session(bind=self.engine) as session:
                session.execute(self.text("SELECT set_config('app.current_user_id', :actor, true)"), {'actor': str(self.actor)})
                if proposed:
                    if barrier: barrier.wait(timeout=5)
                    session.execute(self.text("SELECT id_documento FROM documento WHERE id_documento=:doc FOR UPDATE"), {'doc': document_id}).one()
                found = session.execute(self.text("SELECT 1 FROM documento_version WHERE id_documento=:doc AND hash_sha256=:hash"),
                    {'doc': document_id, 'hash': checksum}).scalar()
                if found: return 409, None
                number = session.execute(self.text("SELECT coalesce(max(numero_version),0)+1 FROM documento_version WHERE id_documento=:doc"),
                    {'doc': document_id}).scalar_one()
                if barrier and not proposed: barrier.wait(timeout=5)  # Force same stale max.
                name = f'{number:04d}-{uuid.uuid4().hex}.pdf'
                values = dict(doc=document_id, number=number, hash=checksum, size=len(content),
                    path=f'{document_id}/{name}', mime=mime, actor=self.actor)
                try:
                    if not proposed: staged.publish(name)
                    session.execute(self.text(
                        "INSERT INTO documento_version(id_documento,numero_version,hash_sha256,tamano_bytes,nombre_original,ruta_almacenamiento,tipo_mime,id_usuario_carga) "
                        "VALUES (:doc,:number,:hash,:size,'ss12-qa.pdf',:path,:mime,:actor)"), values)
                    if proposed: staged.publish(name)  # Constraints tested before publication.
                    session.commit()
                    return 201, number
                except self.IntegrityError as error:
                    code = error.orig.pgcode
                    session.rollback()
                    if code != '23505': raise
                    return 409, None

    def test_actual_unique_constraints_exist_and_are_immediate(self):
        with self.engine.connect() as connection:
            rows = connection.execute(self.text("SELECT conname, condeferrable FROM pg_constraint WHERE conrelid='public.documento_version'::regclass AND contype='u'"))
            constraints = dict(rows)
        for name in ['uq_documento_version', 'uq_documento_hash', 'uq_documento_ruta']:
            self.assertIn(name, constraints); self.assertIs(constraints[name], False)

    def test_row_lock_is_per_document_released_on_commit_and_rollback(self):
        for finish in ['commit', 'rollback']:
            with self.Session(bind=self.engine) as first, self.Session(bind=self.engine) as second:
                first.execute(self.text("SELECT id_documento FROM documento WHERE id_documento=:doc FOR UPDATE"), {'doc': self.documents[0]}).one()
                second.execute(self.text("SELECT id_documento FROM documento WHERE id_documento=:doc FOR UPDATE NOWAIT"), {'doc': self.documents[1]}).one()
                second.rollback()
                with self.assertRaises(self.OperationalError) as caught:
                    second.execute(self.text("SELECT id_documento FROM documento WHERE id_documento=:doc FOR UPDATE NOWAIT"), {'doc': self.documents[0]}).one()
                self.assertEqual(caught.exception.orig.pgcode, '55P03')
                second.rollback(); getattr(first, finish)()
                second.execute(self.text("SELECT id_documento FROM documento WHERE id_documento=:doc FOR UPDATE NOWAIT"), {'doc': self.documents[0]}).one()
                second.rollback()  # One explicit retry; never an unbounded retry loop.

    def test_current_order_concurrent_distinct_bytes_relies_on_unique_constraint(self):
        barrier = threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(self.protocol, self.documents[0], self.pdf(label), barrier=barrier) for label in ['A', 'B']]
            results = [job.result(timeout=10) for job in jobs]
        self.assertEqual(sorted(code for code, _ in results), [201, 409])
        self.assertEqual(len(list(self.root.rglob('*.pdf'))), 2)  # Conservative retained orphan.

    def test_current_order_concurrent_identical_bytes_has_one_confirmed_hash(self):
        barrier = threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(self.protocol, self.documents[0], self.pdf('same'), barrier=barrier) for _ in range(2)]
            results = [job.result(timeout=10) for job in jobs]
        self.assertEqual(sorted(code for code, _ in results), [201, 409])
        with self.engine.connect() as connection:
            count = connection.execute(self.text("SELECT count(*) FROM documento_version WHERE id_documento=:doc"), {'doc': self.documents[0]}).scalar_one()
        self.assertEqual(count, 1)

    def test_proposed_read_committed_parent_lock_contract(self):
        for document, labels in [(self.documents[0], ['A', 'B']), (self.documents[1], ['same', 'same'])]:
            barrier = threading.Barrier(2)
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs = [pool.submit(self.protocol, document, self.pdf(label), proposed=True, barrier=barrier) for label in labels]
                results = [job.result(timeout=10) for job in jobs]
            if labels[0] != labels[1]: self.assertEqual(sorted(results), [(201, 1), (201, 2)])
            else: self.assertEqual(sorted(code for code, _ in results), [201, 409])

    def test_rollback_after_publication_retains_file_without_confirmed_row(self):
        content = self.pdf('rollback'); checksum = hashlib.sha256(content).hexdigest()
        name = '0001-' + uuid.uuid4().hex + '.pdf'
        with self.storage.stage_document(self.root, self.documents[0], content, checksum) as staged:
            with self.Session(bind=self.engine) as session:
                session.execute(self.text("SELECT id_documento FROM documento WHERE id_documento=:doc FOR UPDATE"), {'doc': self.documents[0]}).one()
                staged.publish(name); session.rollback()
        self.assertEqual((self.root / str(self.documents[0]) / name).read_bytes(), content)
        with self.engine.connect() as connection:
            count = connection.execute(self.text("SELECT count(*) FROM documento_version WHERE id_documento=:doc"), {'doc': self.documents[0]}).scalar_one()
        self.assertEqual(count, 0)


if __name__ == '__main__': unittest.main()
