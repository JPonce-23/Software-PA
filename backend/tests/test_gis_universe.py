"""Authorized universe counts, snapshot provenance and additive read contracts."""
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app import auth, models, schemas
from app.main import app
from app.services.common import set_audit_context
from tests.test_nucleus_gpkg_imports import project, nucleus, gpkg, polygon, stage, preview, candidates, decision
from tests.test_parcel_gpkg_imports import parcel, link_parcel, attrs, stage as stage_parcels
from tests.test_gis_history_026 import reconcile, cycles
from tests.test_frontend_read_models import sql_reads


def summary(api,iid): return api('GET',f'/api/importaciones/{iid}/resumen').json()
def codes(context): return {warning['codigo'] for warning in context['advertencias']}


@pytest.mark.parametrize('kind',['nucleo','parcela'])
@pytest.mark.parametrize('has_nucleus',[False,True])
def test_empty_destinations_distinguish_missing_nuclei_from_missing_parcels(transactional_api,tmp_path,kind,has_nucleus):
    api=transactional_api['request'];pid=project(api)
    if has_nucleus: nucleus(transactional_api,pid)
    upload=stage if kind=='nucleo' else stage_parcels
    record=upload(api,pid,gpkg(tmp_path,'empty-context',[('g',[(polygon(),{'cve_unica':'NO-DESTINO'})])])).json()
    report=record['reporte'];actual=report['universo_administrativo_actual'];used=report['universo_administrativo_utilizado']
    applicable=int(has_nucleus and kind=='nucleo')
    assert report['registros_administrativos']==actual['destinos_aplicables']==applicable
    assert actual['nucleos_vinculados_activos']==int(has_nucleus) and actual['parcelas_elegibles_vinculadas']==0
    expected={'SIN_PARCELAS_ELEGIBLES'}
    if not has_nucleus: expected.add('SIN_NUCLEOS_VINCULADOS')
    if not applicable: expected.add('SIN_DESTINOS_APLICABLES')
    assert codes(actual)==codes(used)==expected
    assert actual['origen']=='actual' and actual['id_ciclo'] is None
    assert used['origen']=='ciclo' and used['id_ciclo'] and used['disponibilidad']=='disponible'
    read=summary(api,record['id_importacion'])
    assert read['registros_administrativos']==applicable and read['universo_administrativo_utilizado']==used
    assert cycles(api,record['id_importacion'])[0]['universo_administrativo']==used


@pytest.mark.parametrize('kind',['nucleo','parcela'])
def test_only_own_active_administrative_memberships_are_counted(transactional_api,tmp_path,kind):
    api=transactional_api['request'];pid=project(api);other=project(api)
    nid,key=nucleus(transactional_api,pid)
    # Same nucleus and parcel catalog, with a relation ONLY in the other project.
    api('POST',f'/api/proyectos/{other}/nucleos',expected=201,json={'id_nucleo':nid})
    own=parcel(transactional_api,nid,'016');alien=parcel(transactional_api,nid,'16');unlinked=parcel(transactional_api,nid,'P-99')
    link_parcel(transactional_api,pid,nid,own);link_parcel(transactional_api,other,nid,alien)
    nucleus(transactional_api,pid,active=False)
    nucleus(transactional_api,pid,linked=False)
    upload=stage if kind=='nucleo' else stage_parcels
    properties={'cve_unica':key} if kind=='nucleo' else attrs(key,'016')
    with sql_reads(transactional_api['connection']) as reads:
        record=upload(api,pid,gpkg(tmp_path,'own-context',[('g',[(polygon(i*3),properties) for i in range(3)])])).json()
    ctx=record['reporte']['universo_administrativo_actual']
    assert (ctx['nucleos_vinculados_activos'],ctx['parcelas_elegibles_vinculadas'],ctx['destinos_aplicables'])==(1,1,1)
    assert ctx['advertencias']==[]
    # Counts/matching reuse the same universe; no feature-dependent view reads.
    assert sum('FROM vw_gis_parcela_proyecto' in query for query in reads)==1
    cs=candidates(api,record['id_importacion'],preview(api,record['id_importacion'])[0])
    if kind=='parcela': assert {c['id_parcela'] for c in cs}=={own}
    assert record['reporte']['registros_administrativos']==1


@pytest.mark.parametrize('kind',['nucleo','parcela'])
def test_snapshot_survives_administrative_changes_and_reconciliation(transactional_api,tmp_path,kind):
    api=transactional_api['request'];pid=project(api);nid,key=nucleus(transactional_api,pid)
    number='016';upload=stage if kind=='nucleo' else stage_parcels
    props={'cve_unica':'MISSING'} if kind=='nucleo' else attrs(key,number)
    record=upload(api,pid,gpkg(tmp_path,'history-context',[('g',[(polygon(),props)])])).json()
    iid=record['id_importacion'];first=cycles(api,iid)[0];snapshot=first['universo_administrativo']
    diagnostic=preview(api,iid)[0]['diagnostico']
    if kind=='nucleo':
        nucleus(transactional_api,pid)
    else:
        p=parcel(transactional_api,nid,number);link_parcel(transactional_api,pid,nid,p)
    current=summary(api,iid)
    assert current['universo_administrativo_utilizado']==snapshot
    assert current['registros_administrativos']==snapshot['destinos_aplicables']+1
    # Import report is a persisted calculation, not a live administrative read.
    persisted=api('GET',f'/api/importaciones/{iid}').json()['reporte']
    assert persisted['registros_administrativos']==record['reporte']['registros_administrativos']
    second=reconcile(api,iid).json()
    assert second['universo_administrativo']['destinos_aplicables']==current['registros_administrativos']
    assert second['universo_administrativo']['id_ciclo']!=snapshot['id_ciclo']
    old=api('GET',f"/api/importaciones/{iid}/conciliaciones/{first['id_ciclo']}").json()
    assert old['universo_administrativo']==snapshot and old['features'][0]['diagnostico']==diagnostic
    assert summary(api,iid)['universo_administrativo_utilizado']==second['universo_administrativo']
    with transactional_api['session_factory']() as db:
        with pytest.raises(DBAPIError):
            with db.begin_nested():
                db.execute(text("UPDATE importacion_conciliacion_ciclo SET resumen='{}' WHERE id_ciclo=:c"),{'c':first['id_ciclo']})


@pytest.mark.parametrize('kind',['nucleo','parcela'])
def test_previous_snapshots_are_partial_and_never_filled_from_current_universe(transactional_api,tmp_path,kind):
    api=transactional_api['request'];pid=project(api);nid,key=nucleus(transactional_api,pid)
    p=parcel(transactional_api,nid,'016');link_parcel(transactional_api,pid,nid,p)
    upload=stage if kind=='nucleo' else stage_parcels
    record=upload(api,pid,gpkg(tmp_path,'old-context',[('g',[(polygon(),{'cve_unica':key} if kind=='nucleo' else attrs(key,'016'))])])).json()
    iid=record['id_importacion'];cycle=cycles(api,iid)[0]
    with transactional_api['session_factory']() as db:
        set_audit_context(db,app.dependency_overrides[auth.get_current_user]().id_usuario)
        c=db.get(models.ImportacionConciliacionCiclo,cycle['id_ciclo'])
        c.resumen={k:v for k,v in c.resumen.items() if k!='universo_administrativo'}
        db.commit()
    historic=cycles(api,iid)[0]['universo_administrativo']
    assert historic['disponibilidad']=='parcial' and historic['destinos_aplicables']==1
    assert historic['nucleos_vinculados_activos']==(1 if kind=='nucleo' else None)
    assert historic['parcelas_elegibles_vinculadas']==(1 if kind=='parcela' else None)
    assert historic['advertencias']==[]
    assert summary(api,iid)['universo_administrativo_actual']['disponibilidad']=='disponible'
    assert summary(api,iid)['universo_administrativo_utilizado']==historic


def test_pre026_unreconstructible_cycles_and_legacy_without_cycles(transactional_api):
    api=transactional_api['request'];pid=project(api);nucleus(transactional_api,pid)
    user=app.dependency_overrides[auth.get_current_user]()
    with transactional_api['session_factory']() as db:
        set_audit_context(db,user.id_usuario)
        row=models.ImportacionArchivo(id_proyecto=pid,tipo_objetivo='nucleo_agrario',
            nombre_original='qa',nombre_almacenado='qa',formato_detectado='geojson',tamano_bytes=1,
            sha256=uuid.uuid4().hex*2,fuente='QA',estado='previsualizado',id_usuario_carga=user.id_usuario,creado_por=user.id_usuario)
        db.add(row);db.flush();iid=row.id_importacion;db.commit()
    before=summary(api,iid)['universo_administrativo_utilizado']
    assert before['disponibilidad']=='no_disponible' and before['id_ciclo'] is None
    with transactional_api['session_factory']() as db:
        set_audit_context(db,user.id_usuario)
        db.add(models.ImportacionConciliacionCiclo(id_importacion=iid,numero_ciclo=1,tipo_ciclo='historico',
            motivo='Backfill sintético 026',id_usuario=user.id_usuario,version_algoritmo='conciliacion-v2',
            universo_destinos=[],resumen={'universo_historico_no_reconstruible':True}))
        db.commit()
    historic=cycles(api,iid)[0]['universo_administrativo']
    assert historic['disponibilidad']=='no_disponible' and historic['destinos_aplicables'] is None
    assert historic['nucleos_vinculados_activos'] is None and historic['parcelas_elegibles_vinculadas'] is None
    assert historic['advertencias']==[]
    actual=summary(api,iid)['universo_administrativo_actual']
    assert actual['nucleos_vinculados_activos']==actual['destinos_aplicables']==1


def test_partial_reconciliation_keeps_each_feature_cycle_and_snapshot(transactional_api,tmp_path):
    api=transactional_api['request'];pid=project(api);nid,key=nucleus(transactional_api,pid)
    iid=stage(api,pid,gpkg(tmp_path,'partial-context',[('g',[(polygon(),{'cve_unica':key}),
        (polygon(4),{'cve_unica':'UNMATCHED'})])])).json()['id_importacion']
    first=preview(api,iid);first_cycle=cycles(api,iid)[0]
    nucleus(transactional_api,pid)
    second=reconcile(api,iid).json();after=preview(api,iid)
    assert after[0]['id_ciclo_conciliacion']==first_cycle['id_ciclo']
    assert after[0]['diagnostico']==first[0]['diagnostico']
    assert after[1]['id_ciclo_conciliacion']==second['id_ciclo']
    assert first_cycle['universo_administrativo']['nucleos_vinculados_activos']==1
    assert second['universo_administrativo']['nucleos_vinculados_activos']==2


def test_summary_queries_remain_bounded_as_destinations_grow(transactional_api,tmp_path):
    api=transactional_api['request'];pid=project(api);nid,key=nucleus(transactional_api,pid)
    iid=stage(api,pid,gpkg(tmp_path,'query-context',[('g',[(polygon(),{'cve_unica':key})])])).json()['id_importacion']
    with sql_reads(transactional_api['connection']) as first: summary(api,iid)
    for _ in range(4): nucleus(transactional_api,pid)
    with sql_reads(transactional_api['connection']) as second: result=summary(api,iid)
    assert result['registros_administrativos']==5
    assert len(first)==len(second)
    assert sum("FROM vw_gis_parcela_proyecto" in q for q in second)==1
    assert sum('FROM proyecto_nucleo_geometria' in q for q in second)==1
    with sql_reads(transactional_api['connection']) as one:
        api('GET',f'/api/importaciones/{iid}/conciliaciones',params={'limit':1})
    with sql_reads(transactional_api['connection']) as many:
        api('GET',f'/api/importaciones/{iid}/conciliaciones',params={'limit':100})
    assert len(one)==len(many)


def test_context_schema_is_additive_and_openapi_valid():
    contract=app.openapi()['components']['schemas']
    assert 'universo_administrativo' not in contract['CicloGisResponse']['required']
    context=schemas.UniversoAdministrativoGisResponse(origen='ciclo',disponibilidad='no_disponible')
    assert context.model_dump()['destinos_aplicables'] is None and context.advertencias==[]
    assert 'AdvertenciaUniversoGisResponse' in contract


@pytest.mark.parametrize('role',['operador','visualizador','geografo'])
def test_universe_administration_requires_gis_role(transactional_api,tmp_path,monkeypatch,role):
    from types import SimpleNamespace
    api=transactional_api['request'];pid=project(api);iid=stage(api,pid,gpkg(tmp_path,'scope-context',[('g',[(polygon(),{})])])).json()['id_importacion']
    row=api('POST','/api/usuarios',expected=201,json={'nombre':'QA','apellido_paterno':'Universo','rol':role,
        'correo':uuid.uuid4().hex+'@example.invalid','contrasena':'Qa1!'+uuid.uuid4().hex+'Z'}).json()
    monkeypatch.setitem(app.dependency_overrides,auth.get_current_user,lambda:SimpleNamespace(id_usuario=row['id_usuario'],rol=role,activo=True))
    api('GET',f'/api/importaciones/{iid}/resumen',expected=200 if role=='geografo' else 403)
    api('GET',f'/api/importaciones/{iid}/conciliaciones',expected=200 if role=='geografo' else 403)


def test_idempotent_old_reconciliation_returns_correct_snapshot_without_rewriting(transactional_api,tmp_path):
    api=transactional_api['request'];pid=project(api)
    record=stage(api,pid,gpkg(tmp_path,'old-retry',[('g',[(polygon(),{'cve_unica':'NO-DESTINO'})])])).json()
    iid=record['id_importacion'];key=str(uuid.uuid4());old=reconcile(api,iid,key=key).json()
    with transactional_api['session_factory']() as db:
        set_audit_context(db,app.dependency_overrides[auth.get_current_user]().id_usuario)
        c=db.get(models.ImportacionConciliacionCiclo,old['id_ciclo'])
        c.resumen={k:v for k,v in c.resumen.items() if k!='universo_administrativo'}
        db.commit()
    before=transactional_api['connection'].execute(text('SELECT resumen FROM importacion_conciliacion_ciclo WHERE id_ciclo=:c'),{'c':old['id_ciclo']}).scalar_one()
    with sql_reads(transactional_api['connection']) as reads: retry=reconcile(api,iid,key=key).json()
    ctx=retry['universo_administrativo']
    assert ctx['disponibilidad']=='parcial' and ctx['tipo_objetivo']==record['tipo_objetivo']
    assert ctx['destinos_aplicables']==0 and ctx['parcelas_elegibles_vinculadas'] is None
    assert sum('SELECT importacion_archivo.tipo_objetivo' in q for q in reads)==1
    assert transactional_api['connection'].execute(text('SELECT resumen FROM importacion_conciliacion_ciclo WHERE id_ciclo=:c'),{'c':old['id_ciclo']}).scalar_one()==before
