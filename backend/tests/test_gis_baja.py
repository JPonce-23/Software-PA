"""Logical cancellation, project authorization and preserved GIS provenance."""
import json
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app import auth, models, schemas
from app.main import app
from app.services.common import set_audit_context
from tests.test_nucleus_gpkg_imports import project, nucleus, gpkg, polygon, stage, preview, candidates, decision, confirm
from tests.test_parcel_gpkg_imports import parcel, link_parcel, attrs, stage as stage_parcels
from tests.test_ddv_gpkg_imports import _stage as stage_ddv
from tests.test_gis_history_026 import reconcile, cycles


def baja(api, iid, motivo='Cancelación técnica QA', expected=200):
    return api('POST', f'/api/importaciones/{iid}/baja', expected=expected, json={'motivo':motivo})


def staged(ctx, tmp_path, kind='nucleo', label='cancel'):
    api=ctx['request']; pid=project(api); nid,key=nucleus(ctx,pid)
    if kind=='trazo':
        content=json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},
            'geometry':{'type':'LineString','coordinates':[[-100,20],[-99,21]]}}]}).encode()
        record=api('POST',f'/api/proyectos/{pid}/importaciones',expected=201,
            data={'tipo_objetivo':'trazo_proyecto','fuente':'QA'},
            files={'archivo':('trace.geojson',content,'application/geo+json')}).json()
        return pid,record,content
    properties={'cve_unica':key}; upload=stage
    if kind=='parcela':
        parcel_id=parcel(ctx,nid,'016'); link_parcel(ctx,pid,nid,parcel_id)
        properties=attrs(key,'016'); upload=stage_parcels
    if kind=='ddv': properties={}; upload=stage_ddv
    content=gpkg(tmp_path,label,[('g',[(polygon(),properties)])])
    return pid,upload(api,pid,content).json(),content


def change_import(ctx,iid,**values):
    with ctx['session_factory']() as db:
        user=app.dependency_overrides[auth.get_current_user]()
        set_audit_context(db,user.id_usuario)
        row=db.get(models.ImportacionArchivo,iid)
        for key,value in values.items(): setattr(row,key,value)
        db.commit()


@pytest.mark.parametrize('kind',['nucleo','parcela','ddv','trazo'])
@pytest.mark.parametrize('failed',[False,True])
def test_cancel_unconfirmed_and_exact_retry_preserves_audit(transactional_api,tmp_path,kind,failed):
    api=transactional_api['request']; pid,record,_=staged(transactional_api,tmp_path,kind)
    iid=record['id_importacion']
    if failed: change_import(transactional_api,iid,estado='error')
    fs=preview(api,iid)
    old_cycles=cycles(api,iid)
    first=baja(api,iid).json()
    assert first['activo'] is False and first['fecha_baja'] and first['id_usuario_baja']
    assert first['estado']==('error' if failed else 'previsualizado')
    assert baja(api,iid).json()==first
    baja(api,iid,'Otro motivo',expected=409)
    assert api('GET',f'/api/importaciones/{iid}',params={'incluir_inactivas':True}).json()==first
    for suffix in ['', '/features','/resumen','/conciliaciones']:
        api('GET',f'/api/importaciones/{iid}{suffix}',expected=404)
    assert api('GET',f'/api/importaciones/{iid}/features',params={'incluir_inactivas':True}).json()==fs
    if old_cycles:
        historic=api('GET',f'/api/importaciones/{iid}/conciliaciones',params={'incluir_inactivas':True}).json()
        assert all(c['estado']=='finalizado' and c['fecha_fin'] for c in historic)
        detail=api('GET',f"/api/importaciones/{iid}/conciliaciones/{old_cycles[0]['id_ciclo']}",params={'incluir_inactivas':True}).json()
        assert detail['features'][0]['diagnostico']==fs[0]['diagnostico']
    fid=fs[0]['id_importacion_feature']
    for suffix in [f'/features/{fid}/candidatos',f'/features/{fid}/decisiones',f'/features/{fid}/geometria','/resumen']:
        api('GET',f'/api/importaciones/{iid}{suffix}',expected=404)
        api('GET',f'/api/importaciones/{iid}{suffix}',params={'incluir_inactivas':True})
    confirm(api,iid,expected=404)
    reconcile(api,iid,expected=404)
    api('POST',f'/api/importaciones/{iid}/features/{fid}/decisiones',expected=404,
        params={'incluir_inactivas':True},json={'accion':'ignorar','motivo':'QA'})


@pytest.mark.parametrize('state',['completo','procesando','confirmando','subido','mapeado','cancelado'])
def test_reject_unsafe_states(transactional_api,tmp_path,state):
    _,record,_=staged(transactional_api,tmp_path)
    change_import(transactional_api,record['id_importacion'],estado=state)
    baja(transactional_api['request'],record['id_importacion'],expected=409)


@pytest.mark.parametrize('kind',['nucleo','parcela','ddv','trazo'])
def test_real_confirmed_geometry_prevents_cancellation_and_stays_intact(transactional_api,tmp_path,kind):
    api=transactional_api['request']; pid,record,_=staged(transactional_api,tmp_path,kind)
    iid=record['id_importacion']; f=preview(api,iid)[0]
    if kind in ['nucleo','parcela']:
        decision(api,iid,f,'confirmar',candidates(api,iid,f)[0])
    else: confirm(api,iid)
    table={'nucleo':'proyecto_nucleo_geometria','parcela':'proyecto_parcela_geometria',
           'ddv':'derecho_via_proyecto','trazo':'trazo_proyecto'}[kind]
    con=transactional_api['connection']
    before=con.execute(text(f'SELECT to_jsonb(g) FROM {table} g')).all()
    # Corrupt counters cannot authorize cancellation; actual references survive.
    change_import(transactional_api,iid,estado='previsualizado',importados=0,
                  confirmacion_explicita=False,fecha_confirmacion=None,id_usuario_confirmacion=None)
    baja(api,iid,expected=409)
    assert con.execute(text(f'SELECT to_jsonb(g) FROM {table} g')).all()==before


@pytest.mark.parametrize('dependency',['entrega','revision'])
def test_reject_dependencies_even_without_geometries(transactional_api,tmp_path,dependency):
    api=transactional_api['request']; pid,record,_=staged(transactional_api,tmp_path)
    iid=record['id_importacion']
    with transactional_api['session_factory']() as db:
        user=app.dependency_overrides[auth.get_current_user](); set_audit_context(db,user.id_usuario)
        if dependency=='entrega':
            other=models.ImportacionArchivo(id_proyecto=pid,tipo_objetivo=record['tipo_objetivo'],
                version_pipeline=record['version_pipeline'],nombre_original='qa',nombre_almacenado='qa',formato_detectado='gpkg',tamano_bytes=1,
                sha256=uuid.uuid4().hex*2,fuente='QA',estado='error',id_usuario_carga=user.id_usuario,
                creado_por=user.id_usuario,id_importacion_anterior=iid)
            db.add(other)
        else:
            from app.services.gis_history import record_revision
            fid=db.query(models.ImportacionFeature.id_importacion_feature).filter_by(id_importacion=iid).scalar()
            record_revision(db,user,id_proyecto=pid,objetivo='nucleo',id_importacion_nueva=iid,
                id_feature_nueva=fid,tipo_cambio='aparece_en_nueva_version')
        db.commit()
    baja(api,iid,expected=409)


def test_pagination_and_sha_reimport_keep_history(transactional_api,tmp_path):
    api=transactional_api['request'];pid,record,content=staged(transactional_api,tmp_path)
    iid=record['id_importacion']; fs=preview(api,iid); cs=candidates(api,iid,fs[0])
    baja(api,iid)
    new=stage(api,pid,content).json(); assert new['id_importacion']!=iid
    default=api('GET',f'/api/proyectos/{pid}/importaciones')
    assert default.headers['X-Total-Count']=='1' and default.json()[0]['id_importacion']==new['id_importacion']
    for skip in [0,1,2]:
        page=api('GET',f'/api/proyectos/{pid}/importaciones',params={'incluir_inactivas':True,'skip':skip,'limit':1})
        assert page.headers['X-Total-Count']=='2' and len(page.json())==(0 if skip==2 else 1)
    historic=api('GET',f"/api/importaciones/{iid}/features/{fs[0]['id_importacion_feature']}/candidatos",params={'incluir_inactivas':True}).json()
    assert historic==cs


@pytest.mark.parametrize('role',['admin','geografo','operador','visualizador'])
def test_roles_and_project_isolation(transactional_api,tmp_path,role):
    api=transactional_api['request']; pid,record,_=staged(transactional_api,tmp_path)
    other,alien,_=staged(transactional_api,tmp_path,label='alien')
    original=app.dependency_overrides[auth.get_current_user]
    principal=original()
    if role!='admin':
        row=api('POST','/api/usuarios',expected=201,json={'nombre':'QA GIS','apellido_paterno':'Baja',
            'correo':uuid.uuid4().hex+'@example.invalid','rol':role,'contrasena':'Qa1!'+uuid.uuid4().hex+'Z'}).json()
        api('POST',f'/api/proyectos/{pid}/usuarios',expected=201,json={'id_usuario':row['id_usuario']})
        principal=SimpleNamespace(id_usuario=row['id_usuario'],rol=role,activo=True)
    try:
        app.dependency_overrides[auth.get_current_user]=lambda:principal
        baja(api,record['id_importacion'],expected=200 if role in ['admin','geografo'] else 403)
        baja(api,alien['id_importacion'],expected=200 if role=='admin' else 403)
        api('GET',f'/api/proyectos/{other}/importaciones',params={'incluir_inactivas':True},expected=200 if role=='admin' else 403)
        api('GET',f"/api/importaciones/{alien['id_importacion']}",params={'incluir_inactivas':True},expected=200 if role=='admin' else 403)
    finally: app.dependency_overrides[auth.get_current_user]=original


@pytest.mark.parametrize('body',[{}, {'motivo':''},{'motivo':'  '}])
def test_mandatory_reason(transactional_api,tmp_path,body):
    _,record,_=staged(transactional_api,tmp_path)
    transactional_api['request']('POST',f"/api/importaciones/{record['id_importacion']}/baja",expected=422,json=body)


def test_cancel_failure_rolls_back_cycle_and_audit(transactional_api,tmp_path,monkeypatch):
    from app.services import gis_history
    api=transactional_api['request'];_,record,_=staged(transactional_api,tmp_path)
    iid=record['id_importacion'];before=cycles(api,iid); original=gis_history.close_cycles
    def fail(db,record):
        original(db,record); db.flush(); raise RuntimeError('Synthetic failure')
    monkeypatch.setattr(gis_history,'close_cycles',fail)
    baja(api,iid,expected=409)
    assert api('GET',f'/api/importaciones/{iid}').json()['activo'] is True
    assert cycles(api,iid)==before

# Independent committed connections are required to exercise real row locks.
from tests.test_gis_concurrency_026 import committed_gis, upload, concurrent
from app.database import SessionLocal
from app.services import geospatial_imports as imports, gis_history, gis_reconciliation
from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread


@pytest.mark.parametrize('different_reason',[False,True])
def test_concurrent_baja_is_idempotent_or_conflicts(committed_gis,tmp_path,different_reason):
    iid,_,_=upload(committed_gis,tmp_path,'cancel-race','nucleo')
    user=committed_gis[-1]
    def cancel(db,index):
        reason='Cancelación QA '+str(index if different_reason else 0)
        row=imports.baja_import(db,iid,schemas.BajaRequest(motivo=reason),user)
        return (row.fecha_baja,row.id_usuario_baja,row.motivo_baja)
    results=concurrent(cancel)
    if different_reason: assert sum(r==409 for r in results)==1
    else: assert results[0]==results[1]


@pytest.mark.parametrize('operation,kind',[
    ('reconciliar','nucleo'),('decidir','nucleo'),('confirmar','nucleo'),
    ('confirmar','parcela'),('confirmar','ddv'),
])
def test_stale_read_cannot_write_after_baja(committed_gis,tmp_path,monkeypatch,operation,kind):
    iid,fid,cid=upload(committed_gis,tmp_path,'cancel-before-write',kind,unmatched=operation!='decidir')
    user=committed_gis[-1]; read=Event(); original=imports.require_import_access
    def notify(*args,**kwargs):
        record=original(*args,**kwargs)
        if current_thread().name.startswith('gis-writer'): read.set()
        return record
    monkeypatch.setattr(imports,'require_import_access',notify)
    def writer():
        with SessionLocal() as db:
            try:
                if operation=='reconciliar':
                    gis_history.reconcile(db,iid,schemas.ReconciliarGisRequest(motivo='QA',clave_solicitud=str(uuid.uuid4())),user)
                elif operation=='decidir':
                    gis_reconciliation.decide(db,iid,fid,schemas.DecisionGisRequest(accion='confirmar',id_candidato=cid,confirmacion_explicita=True),user)
                else: imports.confirm_import(db,iid,schemas.ImportacionConfirmarRequest(confirmacion_explicita=True),user)
            except Exception as exc:
                return getattr(exc,'status_code',None)
    with SessionLocal() as db:
        db.query(models.Proyecto).filter_by(id_proyecto=committed_gis[0]).with_for_update().one()
        with ThreadPoolExecutor(max_workers=1,thread_name_prefix='gis-writer') as pool:
            pending=pool.submit(writer)
            assert read.wait(timeout=10)
            imports.baja_import(db,iid,schemas.BajaRequest(motivo='Cancelación gana bloqueo'),user)
            assert pending.result(timeout=15)==404
    with SessionLocal() as db:
        assert db.query(models.ImportacionFeatureDecision).filter_by(id_importacion_feature=fid).count()==0
        assert db.query(models.ImportacionConciliacionCiclo).filter_by(id_importacion=iid).count()==(0 if kind=='ddv' else 1)
        assert db.query(models.DerechoViaProyecto).filter_by(id_importacion=iid).count()==0


@pytest.mark.parametrize('pipeline',['legacy-v1','unknown-future'])
def test_unknown_or_untraceable_pipeline_is_rejected(transactional_api,tmp_path,pipeline):
    api=transactional_api['request'];_,record,_=staged(transactional_api,tmp_path)
    iid=record['id_importacion'];change_import(transactional_api,iid,version_pipeline=pipeline)
    baja(api,iid,expected=409)
