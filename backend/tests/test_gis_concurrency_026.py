"""Operaciones GIS con conexiones PostgreSQL independientes y barrera común."""
import asyncio
import io
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from threading import Barrier
from types import SimpleNamespace

import pytest
from fastapi import HTTPException,UploadFile
from sqlalchemy import text

from app import models,schemas
from app.database import SessionLocal
from app.services.common import set_audit_context
from app.services import gis_history as history,gis_reconciliation as matching
from app.services.geospatial_imports import confirm_import
from tests.test_nucleus_gpkg_imports import gpkg,polygon


@pytest.fixture
def committed_gis():
    with SessionLocal() as db:
        assert db.execute(text('SELECT current_database()')).scalar_one()=='software_pa_test'
        actor=db.query(models.Usuario.id_usuario).filter_by(rol='admin',activo=True).first()[0]
        set_audit_context(db,actor)
        m=db.query(models.Municipio).filter_by(activo=True).first()
        def catalog(t,c): return db.query(models.CatalogoOperativo.id_catalogo_opcion).filter_by(tipo_catalogo=t,codigo=c).scalar()
        key=uuid.uuid4().hex
        p=models.Proyecto(clave_proyecto='G26-'+key[:20],nombre_proyecto='QA concurrencia 026',creado_por=actor)
        n=models.NucleoAgrario(id_municipio=m.id_municipio,nombre_nucleo='QA '+key,
            id_tipo_tenencia=catalog('tipo_tenencia','ejido'),fuente_datos='RAN_PHINA_CATALOGO_NUCLEOS',
            id_entidad_fuente=str(m.id_entidad),id_municipio_fuente=str(m.id_municipio),id_nucleo_fuente=key,
            alcance_identidad_fuente='nacional',creado_por=actor)
        db.add_all([p,n]);db.flush()
        pn=models.ProyectoNucleo(id_proyecto=p.id_proyecto,id_nucleo=n.id_nucleo,creado_por=actor)
        db.add(pn);db.flush()
        parcel=models.Parcela(id_nucleo=n.id_nucleo,tipo_parcela='individual',no_parcela='P-1',creado_por=actor)
        db.add(parcel);db.flush()
        unit=models.UnidadAgraria(id_nucleo=n.id_nucleo,id_parcela=parcel.id_parcela,
            id_tipo_tierra=catalog('tipo_tierra','parcelada'),id_tipo_titularidad=catalog('tipo_titularidad_unidad','persona'),creado_por=actor)
        affect=models.Afectacion(id_proyecto_nucleo=pn.id_proyecto_nucleo,tipo_afectacion='individual',creado_por=actor)
        db.add_all([unit,affect]);db.flush()
        db.add(models.AfectacionUnidadAgraria(id_afectacion=affect.id_afectacion,id_unidad_agraria=unit.id_unidad_agraria,creado_por=actor))
        pid=p.id_proyecto;pnid=pn.id_proyecto_nucleo;parcel_id=parcel.id_parcela
        db.commit()
    user=SimpleNamespace(id_usuario=actor,rol='admin',activo=True)
    try: yield pid,pnid,parcel_id,key,user
    finally:
        with SessionLocal() as db:
            set_audit_context(db,actor);p=db.get(models.Proyecto,pid)
            p.activo=False;p.fecha_baja=datetime.now(timezone.utc);p.id_usuario_baja=actor
            p.motivo_baja='Cierre fixture sintética 026';p.actualizado_por=actor
            db.commit()


def upload(ctx,tmp_path,label,kind,offset=0,*,unmatched=False):
    pid,pnid,parcel_id,key,user=ctx
    target={'nucleo':'nucleo_agrario_gpkg','parcela':'parcela_gpkg','ddv':'derecho_via_proyecto'}[kind]
    props={'cve_unica':key if not unmatched else 'NO-DESTINO'} if kind=='nucleo' else {'cve_unica_nucleo':key,'no_parcela':'P-1'} if kind=='parcela' else {}
    content=gpkg(tmp_path,label,[('g',[(polygon(offset),props)])])
    with SessionLocal() as db:
        record=asyncio.run(matching.stage(db,pid,'QA',None,UploadFile(filename=label+'.gpkg',file=io.BytesIO(content)),user,target=target))
        f=db.query(models.ImportacionFeature).filter_by(id_importacion=record.id_importacion).one()
        candidate=db.query(models.ImportacionFeatureCandidato).filter_by(id_importacion_feature=f.id_importacion_feature).first()
        return record.id_importacion,f.id_importacion_feature,candidate.id_candidato if candidate else None


def concurrent(function):
    barrier=Barrier(2)
    def worker(index):
        with SessionLocal() as db:
            pid=db.execute(text('SELECT pg_backend_pid()')).scalar_one()
            barrier.wait(timeout=10)
            try: result=function(db,index)
            except HTTPException as exc: result=exc.status_code
            return pid,result
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(worker,range(2)))
    assert len({pid for pid,_ in results})==2
    return [result for pid,result in results]


@pytest.mark.parametrize('same_key',[False,True])
def test_concurrent_reconciliation_numbers_and_request_dedup(committed_gis,tmp_path,same_key):
    iid,fid,_=upload(committed_gis,tmp_path,'unmatched','nucleo',unmatched=True)
    user=committed_gis[-1]
    keys=[str(uuid.uuid4()),str(uuid.uuid4())]
    if same_key: keys[1]=keys[0]
    results=concurrent(lambda db,i: history.reconcile(db,iid,schemas.ReconciliarGisRequest(
        motivo='QA nuevos destinos',clave_solicitud=keys[i]),user).numero_ciclo)
    assert sorted(results)==([2,2] if same_key else [2,3])
    with SessionLocal() as db:
        numbers=db.query(models.ImportacionConciliacionCiclo.numero_ciclo).filter_by(id_importacion=iid).order_by(models.ImportacionConciliacionCiclo.numero_ciclo).all()
        assert numbers==([(1,),(2,)] if same_key else [(1,),(2,),(3,)])


@pytest.mark.parametrize('kind',['nucleo','parcela','ddv'])
def test_concurrent_same_confirmation_is_idempotent(committed_gis,tmp_path,kind):
    iid,fid,cid=upload(committed_gis,tmp_path,'confirm-twice',kind)
    user=committed_gis[-1]
    def confirm(db,index):
        if kind=='ddv':confirm_import(db,iid,schemas.ImportacionConfirmarRequest(confirmacion_explicita=True),user)
        else:matching.decide(db,iid,fid,schemas.DecisionGisRequest(accion='confirmar',id_candidato=cid,confirmacion_explicita=True),user)
        return 200
    assert concurrent(confirm)==[200,200]
    model={'nucleo':models.ProyectoNucleoGeometria,'parcela':models.ProyectoParcelaGeometria,'ddv':models.DerechoViaProyecto}[kind]
    with SessionLocal() as db:
        query=db.query(model).filter_by(id_proyecto=committed_gis[0]) if kind=='ddv' else db.query(model).filter_by(id_proyecto_nucleo=committed_gis[1])
        assert query.count()==1


@pytest.mark.parametrize('kind',['nucleo','parcela','ddv'])
def test_two_deliveries_same_destination_keep_one_current_version(committed_gis,tmp_path,kind):
    imports=[upload(committed_gis,tmp_path,f'concurrent-{i}',kind,offset=i*4) for i in range(2)]
    user=committed_gis[-1]
    def confirm(db,index):
        iid,fid,cid=imports[index]
        if kind=='ddv':confirm_import(db,iid,schemas.ImportacionConfirmarRequest(confirmacion_explicita=True),user)
        else:matching.decide(db,iid,fid,schemas.DecisionGisRequest(accion='confirmar',id_candidato=cid,confirmacion_explicita=True,aceptar_advertencias=True),user)
        return 200
    results=concurrent(confirm)
    assert sorted(results)==([200,200] if kind=='ddv' else [200,409])
    model={'nucleo':models.ProyectoNucleoGeometria,'parcela':models.ProyectoParcelaGeometria,'ddv':models.DerechoViaProyecto}[kind]
    with SessionLocal() as db:
        query=db.query(model).filter_by(id_proyecto=committed_gis[0]) if kind=='ddv' else db.query(model).filter_by(id_proyecto_nucleo=committed_gis[1])
        assert query.filter_by(es_vigente=True).count()==1


def test_concurrent_revision_generation_and_decisions_deduplicate(committed_gis,tmp_path):
    first=upload(committed_gis,tmp_path,'baseline','nucleo')
    user=committed_gis[-1]
    with SessionLocal() as db:
        matching.decide(db,first[0],first[1],schemas.DecisionGisRequest(accion='confirmar',id_candidato=first[2],confirmacion_explicita=True),user)
    second=upload(committed_gis,tmp_path,'changed','nucleo',offset=4)
    with SessionLocal() as db:
        matching.decide(db,second[0],second[1],schemas.DecisionGisRequest(accion='confirmar',id_candidato=second[2],confirmacion_explicita=True,aceptar_advertencias=True),user)
        revision=db.query(models.RevisionCambioGis).filter_by(id_importacion_nueva=second[0]).one();rid=revision.id_revision
    def compare(db,index):
        set_audit_context(db,user.id_usuario)
        record=db.get(models.ImportacionArchivo,second[0])
        geometries=db.query(models.ProyectoNucleoGeometria).filter_by(id_proyecto_nucleo=committed_gis[1]).order_by(models.ProyectoNucleoGeometria.version).all()
        history.geometry_changed(db,record,*geometries,user);db.commit();return 200
    assert concurrent(compare)==[200,200]
    request=schemas.RevisionGisDecisionRequest(accion='no_aplica',motivo='QA sin acción',clave_solicitud=str(uuid.uuid4()))
    results=concurrent(lambda db,i: history.decide_revision(db,rid,request,user).id_decision)
    assert results[0]==results[1]
    with SessionLocal() as db:
        assert db.query(models.RevisionCambioGis).filter_by(id_importacion_nueva=second[0]).count()==1
        assert db.query(models.RevisionCambioGisDecision).filter_by(id_revision=rid).count()==1
