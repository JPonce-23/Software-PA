"""Prepared HTTP/ASGI + real SQL/POSIX QA. Separate authorization REQUIRED.

Reuses disposable identity/031/synthetic fixtures. Real route and canonical RBAC;
test identity dependency reads the synthetic actor, NOT a JWT/cookie integration.
No auto migration, database reset, Docker lifecycle or stored-file repair.
"""
from pathlib import Path
import os,sys,unittest,uuid
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/qa'));sys.path.insert(0,str(ROOT/'tests/security'))
import test_document_service_postgresql as publication


@unittest.skipUnless(os.getenv('SS12_QA_ENABLE')=='1' and os.getenv('SS12_QA_DOWNLOAD_ENABLE')=='1',
                     'Separate disposable HTTP download QA authorization required')
class DocumentDownloadPostgreSQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        publication.DocumentServicePostgreSQL.setUpClass.__func__(cls)

    def setUp(self):
        publication.DocumentServicePostgreSQL.setUp(self)
        from _document_download_support import download_app
        from fastapi import Depends,HTTPException
        from fastapi.testclient import TestClient
        from app.services import document_download
        self.download=document_download
        def database():
            with self.Session(self.engine) as db:yield db
        def actor(db=Depends(database)):
            user=db.get(self.service.models.Usuario,self.actor)
            if user is None or not user.activo:raise HTTPException(401,'No autorizado')
            if user.rol not in {'admin','operador','visualizador','geografo'}:raise HTTPException(403,'Sin acceso')
            return user
        app=download_app(self.service.models,database,actor,self.service.require_document_access)
        self.client=TestClient(app);self.addCleanup(self.client.close)
        key=uuid.uuid4();self.content=self.pdf('SS12_STAGE4_HTTP_SYNTHETIC')
        status,self.version=self.upload(self.documents[0],self.content,key)
        self.assertEqual(status,201);self.record=self._operation_record(key)
        self.url=f'/documentos/versiones/{self.version.id_documento_version}/descarga'

    upload=publication.DocumentServicePostgreSQL.upload
    _operation_record=publication.DocumentServicePostgreSQL._operation_record

    def records(self):
        with self.engine.connect() as c:
            return c.execute(self.text("SELECT jsonb_build_object('versions',"
                "(SELECT jsonb_agg(to_jsonb(v) ORDER BY id_documento_version) FROM documento_version v WHERE id_documento=:doc),"
                "'operations',(SELECT jsonb_agg(to_jsonb(o) ORDER BY id_operacion) FROM documento_operacion o WHERE id_documento=:doc))"),
                {'doc':self.documents[0]}).scalar_one()

    def test_real_route_complete_head_and_ranges_without_sql_writes(self):
        before=self.records()
        complete=self.client.get(self.url);self.assertEqual(complete.status_code,200)
        self.assertEqual(complete.content,self.content)
        self.assertEqual(complete.headers['x-content-type-options'],'nosniff')
        self.assertEqual(complete.headers['cache-control'],'private, no-store')
        self.assertEqual(self.client.head(self.url).content,b'')
        partial=self.client.get(self.url,headers={'Range':'bytes=1-4'})
        self.assertEqual((partial.status_code,partial.content),(206,self.content[1:5]))
        self.assertEqual(self.client.get(self.url,headers={'Range':'bytes=999999-'}).status_code,416)
        self.assertEqual(self.records(),before)

    def test_name_substitution_after_open_cannot_redirect_bytes(self):
        before=self.records();original=self.download.open_verified
        def substitute(*args):
            value=original(*args)
            other=self.root/'synthetic-replacement';other.write_bytes(b'SYNTHETIC_OTHER_BYTES')
            os.replace(other,self.root/self.record['ruta_prevista'])
            return value
        with patch.object(self.download,'open_verified',side_effect=substitute):response=self.client.get(self.url)
        self.assertEqual(response.status_code,200);self.assertEqual(response.content,self.content)
        self.assertEqual(self.records(),before)

    def test_revoked_document_link_denies_before_open(self):
        with self.engine.begin() as c:
            c.execute(self.text("SELECT set_config('app.current_user_id','1',true)"))
            c.execute(self.text("UPDATE documento_vinculo SET activo=false,fecha_baja=now(),id_usuario_baja=1,"
                "motivo_baja='SS12 stage4 synthetic revocation' WHERE id_documento=:doc"),{'doc':self.documents[0]})
        before=self.records()
        with patch.object(self.download,'open_verified') as opening:
            self.assertEqual(self.client.get(self.url).status_code,409);opening.assert_not_called()
        self.assertEqual(self.records(),before)

    def test_final_symlink_rejected_and_target_retained(self):
        before=self.records();target=self.root/self.record['ruta_prevista']
        private=self.root/'private-synthetic';private.write_bytes(self.content)
        target.unlink();target.symlink_to(private)
        self.assertEqual(self.client.get(self.url).status_code,404)
        self.assertEqual(private.read_bytes(),self.content);self.assertEqual(self.records(),before)

    def test_corrupt_bytes_do_not_change_terminal_sql(self):
        before=self.records();(self.root/self.record['ruta_prevista']).write_bytes(b'SYNTHETIC_CORRUPTION')
        response=self.client.get(self.url);self.assertEqual(response.status_code,409)
        self.assertNotIn(self.record['ruta_prevista'],response.text);self.assertEqual(self.records(),before)

    def test_repeat_download_keeps_operation_and_version(self):
        before=self.records()
        self.assertEqual(self.client.get(self.url).content,self.content)
        self.assertEqual(self.client.get(self.url).content,self.content)
        self.assertEqual(self.records(),before)


if __name__=='__main__':unittest.main(verbosity=2)
