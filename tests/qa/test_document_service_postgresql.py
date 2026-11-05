"""Opt-in PostgreSQL integration of the REAL store_version implementation.

Only software_pa_test / ss12-document-disposable and the synthetic actor are
accepted. No dotenv, app engine/startup, migrations or resets. Committed rows
are synthetic SS12_STAGE1_* fixtures; discard them with the authorized QA volume.
Fault-injection cases still use real SQL/commit, with the injected event named.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import io
import os
from pathlib import Path
import stat
import sys
import tempfile
import threading
import time
import unittest
import uuid
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
sys.path.insert(0,str(ROOT/'backend/tests'))
sys.path.insert(0,str(ROOT/'tests/security'))


def _process_upload(document,content,request_key,upload_root,queue,barrier=None):
    """Fresh process, fresh engine and real service; used only after QA opt-in."""
    if not (os.getenv('SS12_QA_ENABLE')=='1' and os.getenv('APP_ENV')=='test'
        and os.getenv('SS12_QA_ALLOW_DATABASE')=='software_pa_test'):
        raise RuntimeError('Explicit QA authorization required in child process')
    from sqlalchemy import create_engine,text
    from sqlalchemy.engine import URL
    from sqlalchemy.orm import Session
    from fastapi import UploadFile,HTTPException
    from _document_service_support import document_service
    service=document_service()
    host=os.getenv('SS12_QA_SOCKET_DIR') or os.environ['SS12_QA_HOST']
    engine=create_engine(URL.create('postgresql+psycopg2',host=host,port=int(os.environ['SS12_QA_PORT']),
        database='software_pa_test',username='ss12_runner',password=os.environ['SS12_QA_PASSWORD']),hide_parameters=True,
        connect_args={'connect_timeout':5})
    os.environ['UPLOAD_ROOT']=upload_root
    try:
        with engine.connect() as c:
            if tuple(c.execute(text("SELECT current_database(),current_setting('cluster_name')")).one())!=('software_pa_test','ss12-document-disposable'):
                raise RuntimeError('Child refusing unverified QA database')
        with Session(engine) as request:
            actor=request.get(service.models.Usuario,1)
            if barrier is not None:barrier.wait(timeout=10)
            try:
                result=asyncio.run(service.store_version(request,document,
                    UploadFile(io.BytesIO(content),filename='synthetic.pdf'),actor,idempotency_key=request_key))
                queue.put((200 if result._idempotency_replayed else 201,result.id_documento_version))
            except HTTPException as error:queue.put((error.status_code,None))
    finally:engine.dispose()


@unittest.skipUnless(os.getenv('SS12_QA_ENABLE')=='1','Explicit disposable PostgreSQL authorization required')
class DocumentServicePostgreSQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (os.getenv('APP_ENV')=='test' and os.getenv('SS12_QA_DATABASE')=='software_pa_test'
            and os.getenv('SS12_QA_ALLOW_DATABASE')=='software_pa_test'
            and os.getenv('SS12_QA_USER')=='ss12_runner' and os.getenv('SS12_QA_ACTOR_ID')=='1'):
            raise RuntimeError('Explicit synthetic QA identity required')
        host=os.environ.get('SS12_QA_HOST')
        socket_dir=os.environ.get('SS12_QA_SOCKET_DIR')
        if socket_dir:
            path=Path(socket_dir)
            if not (path.is_absolute() and path.resolve()==path and str(path).startswith('/tmp/')
                and path.stat().st_uid==os.getuid() and stat.S_IMODE(path.stat().st_mode)==0o700):
                raise RuntimeError('Unsafe explicitly supplied private QA socket directory')
            host=socket_dir
        elif host not in ['127.0.0.1','localhost']:
            raise RuntimeError('Only explicit local QA connections permitted')
        from sqlalchemy import create_engine,text,event
        import hashlib
        from sqlalchemy.engine import URL
        from sqlalchemy.orm import Session
        from fastapi import HTTPException,UploadFile
        from _document_service_support import document_service
        from _document_samples import minimal_pdf
        cls.service=document_service();cls.text=staticmethod(text);cls.Session=Session
        cls.event=event;cls.HTTPException=HTTPException;cls.UploadFile=UploadFile
        cls.pdf=staticmethod(minimal_pdf)
        cls.engine=create_engine(URL.create('postgresql+psycopg2',host=host,
            port=int(os.environ['SS12_QA_PORT']),database='software_pa_test',username='ss12_runner',
            password=os.environ['SS12_QA_PASSWORD']),hide_parameters=True,echo=False,
            pool_size=6,max_overflow=0,pool_timeout=3,
            connect_args={'connect_timeout':5,'options':'-c statement_timeout=10000 -c lock_timeout=5000'})
        cls.addClassCleanup(cls.engine.dispose)
        with cls.engine.connect() as c:
            identity=c.execute(text("SELECT current_database(),current_setting('cluster_name'),current_user")).one()
            if tuple(identity)!=('software_pa_test','ss12-document-disposable','ss12_runner'):
                raise RuntimeError('Refusing a database outside the authorized disposable QA cluster')
            lineage=c.execute(text("SELECT checksum_sha256 FROM schema_migrations WHERE version='031'")).scalar()
            expected=hashlib.sha256((ROOT/'backend/db/migrations/031_operaciones_documentales.sql').read_bytes()).hexdigest()
            if lineage!=expected:raise RuntimeError('QA requires explicitly authorized migration 031; tests never apply it')
            actor=c.execute(text("SELECT id_usuario FROM usuario WHERE id_usuario=1 AND activo AND rol='admin' "
                "AND correo='ss12-qa@example.invalid' AND observaciones='SS12_SYNTHETIC_DISPOSABLE_ONLY'")).all()
            if actor!=[(1,)]:raise RuntimeError('Synthetic actor mismatch')
        cls.actor=1
        # Minimal canonical project scope, without changing the existing actor.
        marker='SS12_STAGE1_'+uuid.uuid4().hex[:12]
        with cls.Session(cls.engine) as db:
            cls.service.set_audit_context(db,cls.actor)
            m=cls.service.models
            entity=db.query(m.EntidadFederativa).first()
            if entity is None:
                entity=m.EntidadFederativa(id_entidad=99,clave_inegi='99',nombre='SS12 synthetic entity',activo=True)
                db.add(entity);db.flush()
            municipality=db.query(m.Municipio).filter(m.Municipio.id_entidad==entity.id_entidad).first()
            if municipality is None:
                municipality=m.Municipio(id_municipio=99001,id_entidad=entity.id_entidad,
                    clave_inegi='99001',nombre='SS12 synthetic municipality',activo=True)
                db.add(municipality);db.flush()
            tenure=db.query(m.CatalogoOperativo).filter(m.CatalogoOperativo.tipo_catalogo=='tipo_tenencia',
                m.CatalogoOperativo.activo.is_(True)).first()
            if tenure is None:raise RuntimeError('Canonical tenure catalog unavailable')
            nucleus=m.NucleoAgrario(id_municipio=municipality.id_municipio,nombre_nucleo=marker,
                id_tipo_tenencia=tenure.id_catalogo_opcion,creado_por=cls.actor)
            project=m.Proyecto(clave_proyecto=marker,nombre_proyecto=marker,creado_por=cls.actor)
            db.add_all([nucleus,project]);db.flush()
            pn=m.ProyectoNucleo(id_proyecto=project.id_proyecto,id_nucleo=nucleus.id_nucleo,creado_por=cls.actor)
            db.add(pn);db.flush();cls.project_nucleus=pn.id_proyecto_nucleo;db.commit()

    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='ss12-real-service-')
        self.addCleanup(self.directory.cleanup);self.root=Path(self.directory.name)
        env=patch.dict(os.environ,{'UPLOAD_ROOT':str(self.root)});env.start();self.addCleanup(env.stop)
        self.documents=[]
        with self.Session(self.engine) as db:
            self.service.set_audit_context(db,self.actor)
            for _ in range(2):
                document=self.service.models.Documento(tipo_documento='ss12_qa',estado='disponible',
                    titulo='SS12_STAGE1_'+uuid.uuid4().hex,creado_por=self.actor)
                db.add(document);db.flush()
                db.add(self.service.models.DocumentoVinculo(id_documento=document.id_documento,
                    entidad_tipo='proyecto_nucleo',entidad_id=self.project_nucleus,creado_por=self.actor))
                self.documents.append(document.id_documento)
            db.commit()

    def upload(self,document,content,request_key=None,actor_id=None):
        with self.Session(self.engine) as request:
            user=request.get(self.service.models.Usuario,actor_id or self.actor)
            upload=self.UploadFile(io.BytesIO(content),filename='synthetic.pdf')
            try:
                version=asyncio.run(self.service.store_version(request,document,upload,user,idempotency_key=request_key))
                # The real unchanged response contract works after owned Session close.
                return (200 if version._idempotency_replayed else 201),self.service.schemas.DocumentoVersionResponse.model_validate(version)
            except self.HTTPException as error:return error.status_code,error.detail

    def rows(self,document):
        with self.engine.connect() as c:
            return c.execute(self.text('SELECT numero_version,hash_sha256,ruta_almacenamiento FROM documento_version '
                'WHERE id_documento=:doc ORDER BY numero_version'),{'doc':document}).all()

    def synchronized_uploads(self,contents):
        barrier=threading.Barrier(2);real=self.service.stage_document
        @contextmanager
        def stage(*args, **kwargs):
            with real(*args, **kwargs) as staged:
                barrier.wait(timeout=5)
                yield staged
        with patch.object(self.service,'stage_document',side_effect=stage),ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(self.upload,self.documents[0],data) for data in contents]
            return [job.result(timeout=15) for job in jobs]

    def test_distinct_concurrent_uploads_have_consecutive_versions_and_no_orphans(self):
        results=self.synchronized_uploads([self.pdf('A'),self.pdf('B')])
        self.assertEqual([code for code,_ in results],[201,201])
        self.assertEqual([r[0] for r in self.rows(self.documents[0])],[1,2])
        self.assertEqual(len(list(self.root.rglob('*.pdf'))),2)
        self.assertFalse(list(self.root.rglob('.pending-*')))

    def test_identical_concurrent_uploads_confirm_one_row_and_one_file(self):
        results=self.synchronized_uploads([self.pdf('same')]*2)
        self.assertEqual(sorted(code for code,_ in results),[201,409])
        self.assertEqual(len(self.rows(self.documents[0])),1)
        self.assertEqual(len(list(self.root.rglob('*.pdf'))),1)

    def test_other_document_progresses_while_first_waits_for_parent_lock(self):
        with self.engine.connect() as blocker,ThreadPoolExecutor(max_workers=2) as pool:
            blocker.execute(self.text('SELECT id_documento FROM documento WHERE id_documento=:doc FOR UPDATE'),{'doc':self.documents[0]})
            first=pool.submit(self.upload,self.documents[0],self.pdf('wait'))
            try:
                waiting=False;deadline=time.monotonic()+3
                while time.monotonic()<deadline:
                    with self.engine.connect() as observer:
                        waiting=observer.execute(self.text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                            "AND usename=current_user AND wait_event_type='Lock'")).scalar_one()>0
                    if waiting:break
                    time.sleep(.01)
                self.assertTrue(waiting,'service must reach its real parent row lock')
                second=pool.submit(self.upload,self.documents[1],self.pdf('independent'))
                self.assertEqual(second.result(timeout=3)[0],201)
                self.assertFalse(first.done())
            finally:blocker.rollback()
            self.assertEqual(first.result(timeout=8)[0],201)

    def test_flush_unique_error_does_not_publish_and_rollback_releases_parent(self):
        self.assertEqual(self.upload(self.documents[0],self.pdf('existing'))[0],201)
        existing=self.rows(self.documents[0])[0][1]
        def collide(session,*args):
            for value in session.new:
                if isinstance(value,self.service.models.DocumentoVersion):value.hash_sha256=existing
        self.event.listen(self.Session,'before_flush',collide)
        try:
            from app.services.document_errors import HEADER,DOCUMENT_DUPLICATE
            error=self._attempt_native(self.documents[0],self.pdf('new bytes'),None)
            self.assertEqual((error.status_code,error.headers[HEADER]),(409,DOCUMENT_DUPLICATE))
        finally:self.event.remove(self.Session,'before_flush',collide)
        self.assertEqual(len(list(self.root.rglob('*.pdf'))),1)
        with self.engine.connect() as c:
            c.execute(self.text('SELECT id_documento FROM documento WHERE id_documento=:doc FOR UPDATE NOWAIT'),{'doc':self.documents[0]})
        self.assertEqual(self.upload(self.documents[0],self.pdf('retry distinct'))[0],201)
        self.assertEqual([r[0] for r in self.rows(self.documents[0])],[1,2])

    def test_commit_releases_parent_and_real_constraints_remain_enabled(self):
        self.assertEqual(self.upload(self.documents[0],self.pdf('normal'))[0],201)
        with self.engine.connect() as c:
            c.execute(self.text('SELECT id_documento FROM documento WHERE id_documento=:doc FOR UPDATE NOWAIT'),{'doc':self.documents[0]})
            constraints={row.conname:row.condeferrable for row in c.execute(self.text(
                "SELECT conname,condeferrable FROM pg_constraint WHERE conrelid='documento_version'::regclass AND contype='u'"))}
            for name in ['uq_documento_version','uq_documento_hash','uq_documento_ruta']:
                self.assertIn(name,constraints);self.assertIs(constraints[name],False)
            self.assertEqual(c.execute(self.text("SELECT tgenabled FROM pg_trigger WHERE tgrelid='documento_version'::regclass "
                "AND tgname='trg_documento_version_inmutable'")).scalar_one(),'O')

    def test_read_committed_is_scoped_without_changing_callers_engine_profile(self):
        profile=self.engine.execution_options(isolation_level='REPEATABLE READ')
        with self.Session(profile) as request:
            user=request.get(self.service.models.Usuario,self.actor)
            version=asyncio.run(self.service.store_version(request,self.documents[0],
                self.UploadFile(io.BytesIO(self.pdf('engine profile')),filename='synthetic.pdf'),user))
            self.assertEqual(version.numero_version,1)
        with profile.connect() as connection:
            self.assertEqual(connection.get_isolation_level(),'REPEATABLE READ')

    def test_inactive_document_rechecked_after_staging_before_publication(self):
        real=self.service.stage_document
        @contextmanager
        def stage(*args, **kwargs):
            with real(*args, **kwargs) as staged:
                with self.engine.begin() as c:
                    c.execute(self.text("SELECT set_config('app.current_user_id','1',true)"))
                    c.execute(self.text("UPDATE documento SET activo=false,fecha_baja=now(),id_usuario_baja=1,"
                        "motivo_baja='SS12 synthetic concurrent deactivation' WHERE id_documento=:doc"),{'doc':self.documents[0]})
                yield staged
        with patch.object(self.service,'stage_document',side_effect=stage):
            self.assertEqual(self.upload(self.documents[0],self.pdf('revoked'))[0],404)
        self.assertEqual(self.rows(self.documents[0]),[])
        self.assertFalse(list(self.root.rglob('*.pdf')))

    def test_active_link_revoked_after_staging_is_not_bypassed(self):
        real=self.service.stage_document
        @contextmanager
        def stage(*args, **kwargs):
            with real(*args, **kwargs) as staged:
                with self.engine.begin() as c:
                    c.execute(self.text("SELECT set_config('app.current_user_id','1',true)"))
                    c.execute(self.text("UPDATE documento_vinculo SET activo=false,fecha_baja=now(),id_usuario_baja=1,"
                        "motivo_baja='SS12 synthetic link revocation' WHERE id_documento=:doc"),{'doc':self.documents[0]})
                yield staged
        with patch.object(self.service,'stage_document',side_effect=stage):
            self.assertEqual(self.upload(self.documents[0],self.pdf('revoked link'))[0],409)
        self.assertFalse(list(self.root.rglob('*.pdf')))

    def test_real_commit_lost_ack_retains_confirmed_row_and_file(self):
        base=self.Session
        class LostAck(base):
            def commit(session):
                confirming=any(isinstance(value,self.service.models.DocumentoVersion) for value in session.identity_map.values())
                super().commit()
                if confirming:raise RuntimeError('SS12 injected lost COMMIT acknowledgement')
        original=self.service.sessionmaker
        def factory(**kwargs):return original(class_=LostAck,**kwargs)
        with patch.object(self.service,'sessionmaker',side_effect=factory):
            code,detail=self.upload(self.documents[0],self.pdf('lost ack'))
        # Stage 2 recovers the acknowledged durable result from a fresh Session.
        self.assertEqual(code,200)
        rows=self.rows(self.documents[0]);self.assertEqual(len(rows),1)
        self.assertEqual((self.root/rows[0][2]).read_bytes(),self.pdf('lost ack'))

    def test_cancelled_caller_waits_for_real_commit_without_deleting_file(self):
        gate=threading.Event();release=threading.Event();base=self.Session
        class GatedCommit(base):
            def commit(session):
                confirming=any(isinstance(value,self.service.models.DocumentoVersion) for value in session.identity_map.values())
                if confirming:
                    gate.set()
                    if not release.wait(5):raise RuntimeError('SS12 synthetic commit gate deadline')
                super().commit()
        original=self.service.sessionmaker
        async def exercise():
            with self.Session(self.engine) as request:
                user=request.get(self.service.models.Usuario,self.actor)
                task=asyncio.create_task(self.service.store_version(request,self.documents[0],
                    self.UploadFile(io.BytesIO(self.pdf('cancelled caller')),filename='synthetic.pdf'),user))
                try:
                    for _ in range(600):
                        if gate.is_set():break
                        await asyncio.sleep(.005)
                    self.assertTrue(gate.is_set())
                    task.cancel();await asyncio.sleep(.02);self.assertFalse(task.done())
                finally:release.set()
                with self.assertRaises(asyncio.CancelledError):await task
        with patch.object(self.service,'sessionmaker',side_effect=lambda **kw:original(class_=GatedCommit,**kw)):
            asyncio.run(exercise())
        rows=self.rows(self.documents[0]);self.assertEqual(len(rows),1)
        self.assertEqual((self.root/rows[0][2]).read_bytes(),self.pdf('cancelled caller'))

    def operation(self,key,document=None,actor=None):
        with self.engine.connect() as c:
            return c.execute(self.text('SELECT estado,id_documento_version FROM documento_operacion WHERE '
                'id_documento=:doc AND id_usuario=:actor AND clave_idempotencia=:key'),
                {'doc':document or self.documents[0],'actor':actor or self.actor,'key':str(key)}).one()

    def test_key_first_and_replay_return_same_immutable_result(self):
        key=uuid.uuid4();data=self.pdf('replay')
        a=self.upload(self.documents[0],data,key);b=self.upload(self.documents[0],data,key)
        self.assertEqual((a[0],b[0]),(201,200));self.assertEqual(a[1].model_dump(),b[1].model_dump())
        self.assertEqual(len(self.rows(self.documents[0])),1);self.assertEqual(len(list(self.root.rglob('*.pdf'))),1)

    def test_key_changed_content_and_different_keys_same_content_are_conflicts(self):
        key=uuid.uuid4();data=self.pdf('first')
        self.assertEqual(self.upload(self.documents[0],data,key)[0],201)
        self.assertEqual(self.upload(self.documents[0],self.pdf('other'),key)[0],409)
        other=uuid.uuid4();self.assertEqual(self.upload(self.documents[0],data,other)[0],409)
        self.assertEqual(self.operation(other)[0],'rechazada')
        self.assertEqual(len(self.rows(self.documents[0])),1)

    def test_legacy_without_key_keeps_duplicate_policy_not_replay(self):
        self.assertEqual(self.upload(self.documents[0],self.pdf('legacy'))[0],201)
        self.assertEqual(self.upload(self.documents[0],self.pdf('legacy'))[0],409)

    def test_same_key_in_two_processes_has_only_one_intent_and_publication(self):
        import multiprocessing
        ctx=multiprocessing.get_context('spawn');queue=ctx.Queue();barrier=ctx.Barrier(2);key=uuid.uuid4()
        processes=[ctx.Process(target=_process_upload,args=(self.documents[0],self.pdf('workers'),key,str(self.root),queue,barrier)) for _ in range(2)]
        try:
            for p in processes:p.start()
            results=[queue.get(timeout=20) for _ in processes]
            for p in processes:p.join(timeout=10);self.assertEqual(p.exitcode,0)
        finally:
            for p in processes:
                if p.is_alive():p.terminate();p.join(timeout=5)
            queue.close()
        self.assertIn(201,[code for code,_ in results])
        self.assertTrue(all(code in [200,201,425] for code,_ in results))
        self.assertEqual(self.upload(self.documents[0],self.pdf('workers'),key)[0],200)
        self.assertEqual(len(self.rows(self.documents[0])),1);self.assertEqual(len(list(self.root.rglob('*.pdf'))),1)

    def test_confirmed_result_is_recovered_in_fresh_application_process(self):
        import multiprocessing
        key=uuid.uuid4();first=self.upload(self.documents[0],self.pdf('restart'),key)
        ctx=multiprocessing.get_context('spawn');queue=ctx.Queue()
        child=ctx.Process(target=_process_upload,args=(self.documents[0],self.pdf('restart'),key,str(self.root),queue))
        try:
            child.start();status,version=queue.get(timeout=15);child.join(timeout=10)
            self.assertEqual(child.exitcode,0);self.assertEqual(status,200)
            self.assertEqual(version,first[1].id_documento_version)
        finally:
            if child.is_alive():child.terminate();child.join(timeout=5)
            queue.close()

    def test_pending_without_version_does_not_resume_or_publish(self):
        import hashlib
        key=uuid.uuid4();data=self.pdf('reserved')
        metadata=dict(id_documento=self.documents[0],id_usuario=self.actor,hash_sha256=hashlib.sha256(data).hexdigest(),
            tamano_bytes=len(data),nombre_original='synthetic.pdf',extension='.pdf',tipo_mime='application/pdf')
        with self.Session(self.engine) as request:
            sessions=self.service._upload_sessions(request)
        self.service.operations.reserve(sessions,self.documents[0],self.actor,key,metadata,
            lambda db:self.service._authorize_upload(db,self.documents[0],self.actor),client_key=True)
        self.assertEqual(self.upload(self.documents[0],data,key)[0],425)
        self.assertEqual(self.operation(key),('pendiente',None))
        self.assertFalse(list(self.root.rglob('*.pdf')))

    def test_error_after_publication_before_commit_never_republishes(self):
        base=self.Session;key=uuid.uuid4()
        class BeforeCommitFailure(base):
            def commit(session):
                if any(isinstance(v,self.service.models.DocumentoVersion) for v in session.identity_map.values()):
                    raise RuntimeError('SS12 injected precommit failure after publication')
                super().commit()
        original=self.service.sessionmaker
        with patch.object(self.service,'sessionmaker',side_effect=lambda **kw:original(class_=BeforeCommitFailure,**kw)):
            self.assertEqual(self.upload(self.documents[0],self.pdf('after publish'),key)[0],409)
        self.assertEqual(self.operation(key)[0],'requiere_reconciliacion')
        self.assertEqual(self.upload(self.documents[0],self.pdf('after publish'),key)[0],409)
        self.assertEqual(self.rows(self.documents[0]),[]);self.assertEqual(len(list(self.root.rglob('*.pdf'))),1)

    def test_key_is_scoped_to_document_and_actor(self):
        key=uuid.uuid4()
        first=self.upload(self.documents[0],self.pdf('scope A'),key)
        second=self.upload(self.documents[1],self.pdf('scope A'),key)
        self.assertEqual((first[0],second[0]),(201,201))
        with self.engine.begin() as c:
            c.execute(self.text("SELECT set_config('app.current_user_id','1',true)"))
            actor=c.execute(self.text("INSERT INTO usuario(nombre,apellido_paterno,correo,contrasena_hash,rol,activo,observaciones) "
                "VALUES('SS12','QA',:email,'SS12_DISABLED_SYNTHETIC_HASH','admin',true,'SS12_STAGE2_SYNTHETIC_ONLY') RETURNING id_usuario"),
                {'email':'ss12-stage2-'+uuid.uuid4().hex+'@example.invalid'}).scalar_one()
        third=self.upload(self.documents[0],self.pdf('scope B'),key,actor_id=actor)
        self.assertEqual(third[0],201)
        replay=self.upload(self.documents[0],self.pdf('scope A'),key)
        self.assertEqual(replay[0],200);self.assertEqual(replay[1].id_documento_version,first[1].id_documento_version)
        self.assertNotEqual(self.operation(key,actor=actor)[1],first[1].id_documento_version)

    # Stage 2 closure negatives. Prepared only; requires separate QA authorization.
    def _attempt_native(self,document,content,key):
        with self.Session(self.engine) as request:
            actor=request.get(self.service.models.Usuario,self.actor)
            try:
                return asyncio.run(self.service.store_version(request,document,
                    self.UploadFile(io.BytesIO(content),filename='synthetic.pdf'),actor,idempotency_key=key))
            except self.HTTPException as error:return error

    def _operation_record(self,key,document=None,actor=None):
        with self.engine.connect() as c:
            return c.execute(self.text('SELECT to_jsonb(o) FROM documento_operacion o WHERE '
                'id_documento=:doc AND id_usuario=:actor AND clave_idempotencia=:key'),
                {'doc':document or self.documents[0],'actor':actor or self.actor,'key':str(key)}).scalar_one()

    def _reject_terminal_update(self,key,assignments,values):
        from sqlalchemy.exc import DBAPIError
        before=self._operation_record(key)
        with self.engine.connect() as c:
            transaction=c.begin()
            c.execute(self.text("SELECT set_config('app.current_user_id',:actor,true)"),{'actor':str(self.actor)})
            savepoint=c.begin_nested()
            try:
                with self.assertRaises(DBAPIError) as caught:
                    c.execute(self.text('UPDATE documento_operacion SET '+assignments+
                        ' WHERE id_operacion=:operation'),{'operation':before['id_operacion'],**values})
                self.assertEqual(caught.exception.orig.pgcode,'23514')
                self.assertIn('fn_documento_operacion_integridad',caught.exception.orig.diag.context)
            finally:
                savepoint.rollback();transaction.rollback()
        self.assertEqual(self._operation_record(key),before)

    def test_terminal_confirmed_cannot_return_to_pending_in_postgresql(self):
        key=uuid.uuid4();data=self.pdf('terminal confirmed')
        first=self._attempt_native(self.documents[0],data,key)
        self._reject_terminal_update(key,"estado='pendiente',id_documento_version=NULL,confirmado_en=NULL",{})
        replay=self._attempt_native(self.documents[0],data,key)
        self.assertEqual(replay.id_documento_version,first.id_documento_version)
        self.assertTrue(replay._idempotency_replayed);self.assertEqual(len(self.rows(self.documents[0])),1)

    def test_terminal_rejected_cannot_confirm_by_retry_or_sql(self):
        from app.services.document_errors import HEADER,DOCUMENT_DUPLICATE
        original=uuid.uuid4();rejected=uuid.uuid4();data=self.pdf('terminal rejected')
        first=self._attempt_native(self.documents[0],data,original)
        error=self._attempt_native(self.documents[0],data,rejected)
        self.assertEqual((error.status_code,error.headers[HEADER]),(409,DOCUMENT_DUPLICATE))
        before=self._operation_record(rejected)
        self._reject_terminal_update(rejected,"estado='confirmada',id_documento_version=:version,"
            "confirmado_en=clock_timestamp(),codigo_error=NULL,http_error=NULL",{'version':first.id_documento_version})
        retry=self._attempt_native(self.documents[0],data,rejected)
        self.assertEqual((retry.status_code,retry.headers[HEADER]),(409,DOCUMENT_DUPLICATE))
        self.assertEqual(self._operation_record(rejected),before);self.assertEqual(len(self.rows(self.documents[0])),1)

    def test_terminal_version_identifier_cannot_change_in_either_state(self):
        a,b,rejected=uuid.uuid4(),uuid.uuid4(),uuid.uuid4()
        self._attempt_native(self.documents[0],self.pdf('terminal A'),a)
        alternative=self._attempt_native(self.documents[0],self.pdf('terminal B'),b)
        self._attempt_native(self.documents[0],self.pdf('terminal A'),rejected)
        for key in [a,rejected]:
            with self.subTest(key=key):
                self._reject_terminal_update(key,'id_documento_version=:version',{'version':alternative.id_documento_version})
        self.assertEqual(len(self.rows(self.documents[0])),2)

    def test_incompatible_key_leaves_entire_durable_record_unchanged(self):
        from app.services.document_errors import HEADER,DOCUMENT_IDEMPOTENCY_CONFLICT
        key=uuid.uuid4();self._attempt_native(self.documents[0],self.pdf('request A'),key)
        before=self._operation_record(key)
        for _ in range(2):
            error=self._attempt_native(self.documents[0],self.pdf('request B'),key)
            self.assertEqual((error.status_code,error.headers[HEADER]),(409,DOCUMENT_IDEMPOTENCY_CONFLICT))
            self.assertEqual(self._operation_record(key),before)
        self.assertEqual(len(self.rows(self.documents[0])),1)

    def test_authorized_other_actor_cannot_lookup_owners_operation(self):
        key=uuid.uuid4();self._attempt_native(self.documents[0],self.pdf('private scope'),key)
        before=self._operation_record(key)
        with self.engine.begin() as c:
            c.execute(self.text("SELECT set_config('app.current_user_id','1',true)"))
            actor=c.execute(self.text("INSERT INTO usuario(nombre,apellido_paterno,correo,contrasena_hash,rol,activo,observaciones) "
                "VALUES('SS12','QA',:email,'SS12_DISABLED_SYNTHETIC_HASH','admin',true,'SS12_STAGE2_SYNTHETIC_ONLY') RETURNING id_usuario"),
                {'email':'ss12-stage2-'+uuid.uuid4().hex+'@example.invalid'}).scalar_one()
        with self.Session(self.engine) as request:sessions=self.service._upload_sessions(request)
        result=self.service.operations.lookup(sessions,self.documents[0],actor,key,before['huella_solicitud'],
            lambda db:self.service._authorize_upload(db,self.documents[0],actor))
        self.assertIsNone(result);self.assertEqual(self._operation_record(key),before)

    def test_revoked_link_prevents_confirmed_recovery_without_mutation(self):
        from app.services.document_errors import HEADER,DOCUMENT_REQUEST_CONFLICT
        key=uuid.uuid4();data=self.pdf('permission recheck')
        self._attempt_native(self.documents[0],data,key);before=self._operation_record(key)
        with self.engine.begin() as c:
            c.execute(self.text("SELECT set_config('app.current_user_id','1',true)"))
            c.execute(self.text("UPDATE documento_vinculo SET activo=false,fecha_baja=now(),id_usuario_baja=1,"
                "motivo_baja='SS12 synthetic replay revocation' WHERE id_documento=:doc"),{'doc':self.documents[0]})
        error=self._attempt_native(self.documents[0],data,key)
        self.assertEqual((error.status_code,error.headers[HEADER]),(409,DOCUMENT_REQUEST_CONFLICT))
        self.assertEqual(self._operation_record(key),before);self.assertEqual(len(self.rows(self.documents[0])),1)

    def test_intent_commit_failure_before_staging_publishes_nothing(self):
        from sqlalchemy.dialects.postgresql import Insert
        base=self.Session
        class IntentFailure(base):
            def execute(session,statement,*args,**kwargs):
                result=super().execute(statement,*args,**kwargs)
                if isinstance(statement,Insert) and statement.table.name=='documento_operacion':session.info['qa_intent']=True
                return result
            def commit(session):
                if session.info.get('qa_intent'):raise RuntimeError('SS12 injected failure BEFORE intent COMMIT')
                super().commit()
        original=self.service.sessionmaker;key=uuid.uuid4()
        with patch.object(self.service,'sessionmaker',side_effect=lambda **kw:original(class_=IntentFailure,**kw)),\
                patch.object(self.service,'stage_document') as staging:
            error=self._attempt_native(self.documents[0],self.pdf('no intent'),key)
            self.assertEqual(error.status_code,503);staging.assert_not_called()
        with self.engine.connect() as c:
            self.assertEqual(c.execute(self.text('SELECT count(*) FROM documento_operacion WHERE id_documento=:doc'),{'doc':self.documents[0]}).scalar_one(),0)
        self.assertFalse(list(self.root.rglob('*')));self.assertEqual(self.rows(self.documents[0]),[])

    def test_lost_intent_commit_ack_keeps_pending_and_never_stages(self):
        from sqlalchemy.dialects.postgresql import Insert
        from app.services.document_errors import HEADER,DOCUMENT_OPERATION_PENDING
        base=self.Session
        class LostIntentAck(base):
            def execute(session,statement,*args,**kwargs):
                result=super().execute(statement,*args,**kwargs)
                if isinstance(statement,Insert) and statement.table.name=='documento_operacion':session.info['qa_intent']=True
                return result
            def commit(session):
                intent=session.info.pop('qa_intent',False);super().commit()
                if intent:raise RuntimeError('SS12 injected ACK loss AFTER real intent COMMIT')
        original=self.service.sessionmaker;key=uuid.uuid4();data=self.pdf('intent ack loss')
        with patch.object(self.service,'sessionmaker',side_effect=lambda **kw:original(class_=LostIntentAck,**kw)),\
                patch.object(self.service,'stage_document') as staging:
            error=self._attempt_native(self.documents[0],data,key)
            self.assertEqual((error.status_code,error.headers[HEADER]),(425,DOCUMENT_OPERATION_PENDING));staging.assert_not_called()
        before=self._operation_record(key)
        error=self._attempt_native(self.documents[0],data,key)
        self.assertEqual((error.status_code,error.headers[HEADER]),(425,DOCUMENT_OPERATION_PENDING))
        self.assertEqual((before['estado'],before['id_documento_version'],before['identidad_archivo']),('pendiente',None,None))
        self.assertEqual(self._operation_record(key),before);self.assertFalse(list(self.root.rglob('*')))

    def test_postpublication_fault_keeps_durable_reconciliation_identity_and_code(self):
        import hashlib
        from app.services.document_errors import HEADER,DOCUMENT_RECONCILIATION_REQUIRED
        base=self.Session;key=uuid.uuid4();data=self.pdf('durable physical identity')
        class BeforeVersionCommit(base):
            def commit(session):
                if any(isinstance(v,self.service.models.DocumentoVersion) for v in session.identity_map.values()):
                    raise RuntimeError('SS12 injected fault AFTER publish and BEFORE version COMMIT')
                super().commit()
        original=self.service.sessionmaker
        with patch.object(self.service,'sessionmaker',side_effect=lambda **kw:original(class_=BeforeVersionCommit,**kw)):
            error=self._attempt_native(self.documents[0],data,key)
        self.assertEqual((error.status_code,error.headers[HEADER]),(409,DOCUMENT_RECONCILIATION_REQUIRED))
        before=self._operation_record(key);file=self.root/before['ruta_prevista']
        self.assertEqual(before['estado'],'requiere_reconciliacion');self.assertIsNone(before['id_documento_version'])
        self.assertEqual(file.read_bytes(),data);self.assertEqual(before['hash_sha256'],hashlib.sha256(data).hexdigest())
        self.assertEqual(before['tamano_bytes'],len(data))
        self.assertEqual(before['identidad_archivo'],{'device':file.stat().st_dev,'inode':file.stat().st_ino})
        self.assertTrue(before['ruta_staging']);self.assertTrue(before['staging_preparado_en'])
        retry=self._attempt_native(self.documents[0],data,key)
        self.assertEqual((retry.status_code,retry.headers[HEADER]),(409,DOCUMENT_RECONCILIATION_REQUIRED))
        self.assertEqual(self._operation_record(key),before);self.assertEqual(len(list(self.root.rglob('*.pdf'))),1)



if __name__=='__main__':unittest.main(verbosity=2)
