"""Seed ONLY the explicitly marked empty disposable deployment lab.

No migrations, resets or infrastructure provisioning. Requires synthetic owner
credentials and UID 0 inside the disposable runner for historical mode fixtures.
"""
import hashlib,json,os,uuid,sys
from pathlib import Path
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session
from app import models
from app.services.authentication import hash_password
from app.services.common import set_audit_context
if len(Path(__file__).resolve().parents)>2:
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend/tests'))
from _document_samples import minimal_pdf

assert os.environ['PR6_DEPLOY_QA']=='SYNTHETIC_DISPOSABLE_ONLY' and os.geteuid()==0
owner=create_engine(URL.create('postgresql',host='db',database='software_pa_test',username=os.environ['POSTGRES_ADMIN_USER'],password=os.environ['POSTGRES_ADMIN_PASSWORD']))
with owner.begin() as c:
    assert c.execute(text("SELECT current_setting('cluster_name')")).scalar_one()=='pr6-deployment-disposable'
    assert c.execute(text('SELECT count(*) FROM usuario')).scalar_one()==0
    c.execute(text("SELECT set_config('app.current_user_id','1',true)"))
    for ident,email,rol in [(1,'ss12-qa@example.invalid','admin'),(2,'unassigned@example.invalid','operador'),(3,'locked@example.invalid','operador'),(4,'guard@example.invalid','admin')]:
        c.execute(text("INSERT INTO usuario(id_usuario,nombre,apellido_paterno,correo,contrasena_hash,rol,activo,fecha_alta,observaciones) VALUES (:id,'PR6 synthetic','QA',:email,:password,:rol,true,now(),'PR6_SYNTHETIC_DISPOSABLE_ONLY')"),{'id':ident,'email':email,'password':hash_password(os.environ['QA_PASSWORD']),'rol':rol})
    c.execute(text("SELECT setval(pg_get_serial_sequence('usuario','id_usuario'),4,true)"))
    for version in ('031','032'):
        assert c.execute(text('SELECT checksum_sha256 FROM schema_migrations WHERE version=:v'),{'v':version}).scalar_one()==hashlib.sha256(next(Path('/app/db/migrations').glob(version+'_*.sql')).read_bytes()).hexdigest()
    assert c.execute(text('SELECT max(version::int) FROM schema_migrations')).scalar_one()==32
    c.execute(text("CREATE TABLE pr6_synthetic_fixture (value jsonb NOT NULL)"))
    c.execute(text("GRANT SELECT ON pr6_synthetic_fixture TO software_pa_app"))
with Session(owner) as db:
    set_audit_context(db,1)
    entity=models.EntidadFederativa(id_entidad=99,clave_inegi='99',nombre='PR6 synthetic state',activo=True)
    db.add(entity);db.flush()
    municipality=models.Municipio(id_municipio=99001,id_entidad=99,clave_inegi='001',nombre='PR6 synthetic town',activo=True)
    db.add(municipality);db.flush()
    tenure=db.query(models.CatalogoOperativo).filter_by(tipo_catalogo='tipo_tenencia',activo=True).first()
    nucleus=models.NucleoAgrario(id_municipio=99001,nombre_nucleo='PR6 synthetic nucleus',id_tipo_tenencia=tenure.id_catalogo_opcion,creado_por=1)
    project=models.Proyecto(clave_proyecto='PR6_SYNTHETIC',nombre_proyecto='PR6 isolated QA',creado_por=1)
    db.add_all([nucleus,project]);db.flush()
    pn=models.ProyectoNucleo(id_proyecto=project.id_proyecto,id_nucleo=nucleus.id_nucleo,creado_por=1)
    db.add(pn);db.flush()
    docs=[]
    for _ in range(7):
        doc=models.Documento(tipo_documento='pr6_qa',estado='disponible',titulo='PR6_SYNTHETIC',creado_por=1)
        db.add(doc);db.flush();docs.append(doc.id_documento)
        db.add(models.DocumentoVinculo(id_documento=doc.id_documento,entidad_tipo='proyecto_nucleo',entidad_id=pn.id_proyecto_nucleo,creado_por=1))
    content=minimal_pdf('historical synthetic only')
    directory=Path('/app/uploads')/str(docs[0]);directory.mkdir(mode=0o700);os.chown(directory,10001,10001)
    path=directory/('0001-'+uuid.uuid4().hex+'.pdf');path.write_bytes(content);path.chmod(0o644)
    version=models.DocumentoVersion(id_documento=docs[0],numero_version=1,hash_sha256=hashlib.sha256(content).hexdigest(),tamano_bytes=len(content),nombre_original='historical.pdf',ruta_almacenamiento=str(path.relative_to('/app/uploads')),tipo_mime='application/pdf',id_usuario_carga=1)
    db.add(version);db.flush()
    fixture={'project':project.id_proyecto,'docs':docs,'legacy_version':version.id_documento_version,'legacy_sha':hashlib.sha256(content).hexdigest()}
    db.execute(text('INSERT INTO pr6_synthetic_fixture VALUES (CAST(:v AS jsonb))'),{'v':json.dumps(fixture)})
    db.commit()
print('SYNTHETIC_SEED_AND_MIGRATIONS_031_032_PASS')
