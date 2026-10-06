"""Aislamiento administrativo, RBAC y concurrencia real entre conexiones."""
import asyncio
import io
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
import pytest
from fastapi import HTTPException,UploadFile
from sqlalchemy import text
from app import auth,models,schemas
from app.database import SessionLocal
from app.main import app
from app.services.common import set_audit_context
from app.services import gis_reconciliation as service
from tests.test_nucleus_gpkg_imports import project,nucleus,gpkg,polygon,stage,preview,candidates,decision


@pytest.mark.parametrize('role,can_write',[('admin',True),('geografo',True),('operador',False),('visualizador',False)])
def test_reconciliation_reuses_existing_roles_and_project_access(transactional_api,tmp_path,role,can_write):
    api=transactional_api['request']; pid=project(api); other=project(api)
    nid,key=nucleus(transactional_api,pid)
    staged=stage(api,pid,gpkg(tmp_path,'role',[('n',[(polygon(),{'cve_unica':key})])])).json()
    f=preview(api,staged['id_importacion'])[0]; c=candidates(api,staged['id_importacion'],f)[0]
    original=app.dependency_overrides[auth.get_current_user]
    if role=='admin': principal=original()
    else:
        user=api('POST','/api/usuarios',expected=201,json={'nombre':'GIS QA','apellido_paterno':'Sintético',
            'correo':uuid.uuid4().hex+'@example.invalid','rol':role,'contrasena':'Qa1!'+uuid.uuid4().hex+'Z'}).json()
        api('POST',f'/api/proyectos/{pid}/usuarios',expected=201,json={'id_usuario':user['id_usuario']})
        principal=SimpleNamespace(id_usuario=user['id_usuario'],rol=role,activo=True)
    try:
        app.dependency_overrides[auth.get_current_user]=lambda:principal
        assert candidates(api,staged['id_importacion'],f)
        decision(api,staged['id_importacion'],f,'confirmar',c,expected=200 if can_write else 403)
        api('GET',f'/api/proyectos/{other}/geoespacial/configuracion',expected=200 if role=='admin' else 403)
    finally: app.dependency_overrides[auth.get_current_user]=original


def test_cannot_choose_a_candidate_from_another_feature(transactional_api,tmp_path):
    api=transactional_api['request']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    staged=stage(api,pid,gpkg(tmp_path,'cross',[('n',[(polygon(),{'cve_unica':key}),(polygon(3),{'cve_unica':key})])])).json()
    fs=preview(api,staged['id_importacion'])
    decision(api,staged['id_importacion'],fs[1],'confirmar',candidates(api,staged['id_importacion'],fs[0])[0],expected=404)


def test_valid_source_must_not_be_repaired_after_pipeline_rounding(transactional_api,tmp_path,monkeypatch):
    api=transactional_api['request']; pid=project(api)
    g={'type':'MultiPolygon','coordinates':[[[[0,0],[1.00000001,0],[1.00000001,1],[0,1],[0,0]]],
                                            [[[1.00000002,0],[2,0],[2,1],[1.00000002,1],[1.00000002,0]]]]}
    original=service.iter_features
    def rounded(*args,**kwargs):
        def round_coords(coords):
            return [round(v,7) if isinstance(v,(int,float)) else round_coords(v) for v in coords]
        for layer,feature in original(*args,**kwargs):
            feature['geometry']['coordinates']=round_coords(feature['geometry']['coordinates'])
            yield layer,feature
    monkeypatch.setattr(service,'iter_features',rounded)
    from tests.test_ddv_gpkg_imports import _stage
    staged=_stage(api,pid,gpkg(tmp_path,'rounding',[('ddv',[(g,{})])])).json()
    f=preview(api,staged['id_importacion'])[0]
    assert f['estado']=='error' and f['errores'][0]['codigo']=='PIPELINE_ALTERO_TOPOLOGIA'
    assert not f['advertencias']


@pytest.mark.parametrize('kind',['nucleo','parcela','ddv'])
def test_two_connections_serialize_confirmation(tmp_path,kind):
    """Las filas se preparan y hacen commit antes de abrir las dos conexiones."""
    with SessionLocal() as db:
        assert db.execute(text('SELECT current_database()')).scalar_one()=='software_pa_test'
        admin=db.query(models.Usuario).filter_by(rol='admin',activo=True).first()
        actor=admin.id_usuario; set_audit_context(db,actor)
        municipality=db.query(models.Municipio).filter_by(activo=True).first()
        def catalog(t,c): return db.query(models.CatalogoOperativo.id_catalogo_opcion).filter_by(tipo_catalogo=t,codigo=c).scalar()
        token=uuid.uuid4().hex
        p=models.Proyecto(clave_proyecto='GC-'+token[:20],nombre_proyecto='Concurrencia sintética GIS',creado_por=actor)
        n=models.NucleoAgrario(id_municipio=municipality.id_municipio,nombre_nucleo='GIS concurrente '+token,
            id_tipo_tenencia=catalog('tipo_tenencia','ejido'),fuente_datos='RAN_PHINA_CATALOGO_NUCLEOS',
            id_entidad_fuente=str(municipality.id_entidad),id_municipio_fuente=str(municipality.id_municipio),
            id_nucleo_fuente=token,alcance_identidad_fuente='nacional',creado_por=actor)
        db.add_all([p,n]); db.flush()
        pn=models.ProyectoNucleo(id_proyecto=p.id_proyecto,id_nucleo=n.id_nucleo,creado_por=actor)
        db.add(pn); db.flush(); parcel_id=None
        if kind=='parcela':
            parcel=models.Parcela(id_nucleo=n.id_nucleo,tipo_parcela='individual',no_parcela='P-1',creado_por=actor)
            db.add(parcel); db.flush(); parcel_id=parcel.id_parcela
            unit=models.UnidadAgraria(id_nucleo=n.id_nucleo,id_parcela=parcel_id,id_tipo_tierra=catalog('tipo_tierra','parcelada'),
                id_tipo_titularidad=catalog('tipo_titularidad_unidad','persona'),creado_por=actor)
            a=models.Afectacion(id_proyecto_nucleo=pn.id_proyecto_nucleo,tipo_afectacion='individual',creado_por=actor)
            db.add_all([unit,a]); db.flush()
            db.add(models.AfectacionUnidadAgraria(id_afectacion=a.id_afectacion,id_unidad_agraria=unit.id_unidad_agraria,creado_por=actor))
        pid=p.id_proyecto; pnid=pn.id_proyecto_nucleo; db.commit()
    user=SimpleNamespace(id_usuario=actor,rol='admin',activo=True)
    try:
        target={'nucleo':'nucleo_agrario_gpkg','parcela':'parcela_gpkg','ddv':'derecho_via_proyecto'}[kind]
        properties={'cve_unica':token} if kind=='nucleo' else {'cve_unica_nucleo':token,'no_parcela':'P-1'} if kind=='parcela' else {}
        content=gpkg(tmp_path,'concurrent',[('g',[(polygon(),properties),(polygon(3),properties)])])
        with SessionLocal() as db:
            staged=asyncio.run(service.stage(db,pid,'QA',None,UploadFile(filename='qa.gpkg',file=io.BytesIO(content)),user,target=target))
            iid=staged.id_importacion
            features=db.query(models.ImportacionFeature).filter_by(id_importacion=iid).order_by(models.ImportacionFeature.indice_feature).all()
            fids=[f.id_importacion_feature for f in features]
            cids=[db.query(models.ImportacionFeatureCandidato.id_candidato).filter_by(id_importacion_feature=fid).scalar() for fid in fids] if kind!='ddv' else []
        imports=[iid]
        if kind=='ddv':
            with SessionLocal() as db:
                other=gpkg(tmp_path,'concurrent-other',[('g',[(polygon(6),{})])])
                imports.append(asyncio.run(service.stage(db,pid,'QA',None,UploadFile(filename='qa2.gpkg',file=io.BytesIO(other)),user,target=target)).id_importacion)
        barrier=Barrier(2)
        def confirm_index(index):
            with SessionLocal() as db:
                barrier.wait(timeout=10)
                try:
                    if kind=='ddv':
                        from app.services.geospatial_imports import confirm_import
                        confirm_import(db,imports[index],schemas.ImportacionConfirmarRequest(confirmacion_explicita=True),user)
                    else:
                        service.decide(db,iid,fids[index],schemas.DecisionGisRequest(accion='confirmar',id_candidato=cids[index],confirmacion_explicita=True),user)
                    return 200
                except HTTPException as error: return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(confirm_index,range(2)))
        with SessionLocal() as db:
            if kind=='ddv':
                assert results==[200,200]
                assert db.execute(text('SELECT version,es_vigente FROM derecho_via_proyecto WHERE id_proyecto=:p ORDER BY version'),{'p':pid}).all()==[(1,False),(2,True)]
            else:
                assert sorted(results)==[200,409]
                model=models.ProyectoParcelaGeometria if kind=='parcela' else models.ProyectoNucleoGeometria
                assert db.query(model).filter_by(id_proyecto_nucleo=pnid).count()==1
                assert db.query(models.ImportacionFeatureDecision).filter(models.ImportacionFeatureDecision.id_importacion_feature.in_(fids)).count()==1
    finally:
        with SessionLocal() as db:
            from datetime import datetime,timezone
            set_audit_context(db,actor)
            p=db.get(models.Proyecto,pid); p.activo=False; p.fecha_baja=datetime.now(timezone.utc); p.id_usuario_baja=actor;p.motivo_baja='Cierre fixture concurrencia GIS';p.actualizado_por=actor
            db.commit()


def test_database_rejects_cross_project_ddv_destination(transactional_api,tmp_path):
    from tests.test_ddv_gpkg_imports import _stage,_confirm,_gpkg,_polygon
    from sqlalchemy.exc import DBAPIError
    api=transactional_api['request']; left=project(api); right=project(api)
    content=_gpkg(tmp_path,'ddv-scope',[('d',[_polygon()])])
    first=_stage(api,left,content).json(); second=_stage(api,right,content).json()
    done=_confirm(api,second['id_importacion']).json()
    with transactional_api['session_factory']() as db:
        with pytest.raises(DBAPIError):
            with db.begin_nested():
                db.execute(text('UPDATE importacion_feature SET registro_destino_id=:dest WHERE id_importacion=:i'),
                    {'dest':done['reporte']['id_derecho_via'],'i':first['id_importacion']})


def test_confirmed_source_and_decisions_are_immutable(transactional_api,tmp_path):
    from sqlalchemy.exc import DBAPIError
    api=transactional_api['request']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    staged=stage(api,pid,gpkg(tmp_path,'immutable',[('n',[(polygon(),{'cve_unica':key})])])).json()
    f=preview(api,staged['id_importacion'])[0]; c=candidates(api,staged['id_importacion'],f)[0]
    decision(api,staged['id_importacion'],f,'confirmar',c)
    with transactional_api['session_factory']() as db:
        for statement in ('UPDATE importacion_feature SET atributos_originales=\'{}\' WHERE id_importacion_feature=:f',
                          "UPDATE importacion_feature_decision SET motivo='alterado' WHERE id_importacion_feature=:f"):
            with pytest.raises(DBAPIError):
                with db.begin_nested(): db.execute(text(statement),{'f':f['id_importacion_feature']})
