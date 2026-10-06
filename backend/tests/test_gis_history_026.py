"""Historia GIS 026 con archivos pequeños y decisiones administrativas explícitas."""
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.test_nucleus_gpkg_imports import project,nucleus,gpkg,polygon,stage,preview,candidates,decision,confirm
from tests.test_parcel_gpkg_imports import parcel,link_parcel,attrs,stage as stage_parcels
from tests.test_ddv_gpkg_imports import _stage as stage_ddv,_confirm as confirm_ddv
from tests.test_gis_history_regressions import domain_counts,project_domain_rows
from tests.test_excel_closure_002 import _catalog


def reconcile(api,iid,*,key=None,expected=201,**options):
    return api('POST',f'/api/importaciones/{iid}/reconciliar',expected=expected,json={
        'motivo':'Nuevo universo administrativo','clave_solicitud':key or str(uuid.uuid4()),**options})


def cycles(api,iid):
    return api('GET',f'/api/importaciones/{iid}/conciliaciones').json()


def reviews(api,pid,**params):
    return api('GET',f'/api/proyectos/{pid}/geoespacial/revisiones',params=params).json()


def finish(api,iid,*,accept=False):
    for feature in preview(api,iid):
        current = candidates(api,iid,feature)
        if current:
            decision(api,iid,feature,'confirmar',current[-1],accept=accept)
    confirm(api,iid)


def test_late_reconciliation_three_cycles_keep_original_no_destination(transactional_api,tmp_path):
    api=transactional_api['request']; con=transactional_api['connection']; pid=project(api)
    a,key_a=nucleus(transactional_api,pid)
    b,key_b=nucleus(transactional_api,pid,linked=False)
    before=domain_counts(con)
    imported=stage(api,pid,gpkg(tmp_path,'late',[('n',[
        (polygon(),{'cve_unica':key_a}),(polygon(4),{'cve_unica':key_b})])])).json()
    iid=imported['id_importacion']; fs=preview(api,iid)
    decision(api,iid,fs[0],'confirmar',candidates(api,iid,fs[0])[0]); confirm(api,iid)
    first=cycles(api,iid)[0]
    first_detail=api('GET',f"/api/importaciones/{iid}/conciliaciones/{first['id_ciclo']}").json()
    assert first_detail['features'][1]['estado_matching']=='sin_coincidencia'
    assert domain_counts(con)==before
    second=reconcile(api,iid).json()
    assert second['numero_ciclo']==2 and second['resumen']['resultados']=={'sin_coincidencia':1}
    # Only the normal administrative API creates project membership.
    pn=api('POST',f'/api/proyectos/{pid}/nucleos',expected=201,json={'id_nucleo':b}).json()
    before=domain_counts(con); rows=project_domain_rows(con,pid)
    key=str(uuid.uuid4()); third=reconcile(api,iid,key=key).json()
    assert third['numero_ciclo']==3 and third['resumen']['features']==1
    assert reconcile(api,iid,key=key).json()['id_ciclo']==third['id_ciclo']
    cs=candidates(api,iid,fs[1]); assert len(cs)==1
    assert cs[0]['id_ciclo']==third['id_ciclo'] and cs[0]['id_proyecto_nucleo']==pn['id_proyecto_nucleo']
    decision(api,iid,fs[1],'confirmar',cs[0]); confirm(api,iid)
    assert len(cycles(api,iid))==3
    assert api('GET',f"/api/importaciones/{iid}/conciliaciones/{first['id_ciclo']}").json()==first_detail
    assert domain_counts(con)==before and project_domain_rows(con,pid)==rows
    with transactional_api['session_factory']() as db:
        with pytest.raises(DBAPIError):
            with db.begin_nested():
                db.execute(text("UPDATE importacion_conciliacion_resultado SET estado_matching='confirmado' WHERE id_ciclo=:c"),{'c':first['id_ciclo']})


def test_rejected_features_require_explicit_reopen_and_keep_candidates(transactional_api,tmp_path):
    api=transactional_api['request']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    iid=stage(api,pid,gpkg(tmp_path,'rejected',[('n',[(polygon(),{'cve_unica':key})])])).json()['id_importacion']
    f=preview(api,iid)[0]; old=candidates(api,iid,f)[0]
    decision(api,iid,f,'rechazar',old)
    reconcile(api,iid,expected=409)
    cycle=reconcile(api,iid,reabrir_rechazados=True).json()
    new=candidates(api,iid,f)
    assert len(new)==2 and new[0]['estado']=='rechazado' and new[0]['id_ciclo']!=cycle['id_ciclo']
    decision(api,iid,f,'confirmar',old,expected=404)
    decision(api,iid,f,'confirmar',new[1])
    history=api('GET',f"/api/importaciones/{iid}/features/{f['id_importacion_feature']}/decisiones").json()
    assert [d['accion'] for d in history]==['rechazar','confirmar']
    assert [d['id_ciclo'] for d in history]==[old['id_ciclo'],cycle['id_ciclo']]


def test_ambiguous_reconciliation_preserves_old_candidates(transactional_api,tmp_path):
    from tests.test_nucleus_gpkg_imports import rename_nucleus
    api=transactional_api['request'];pid=project(api)
    for _ in range(2):
        nid,key=nucleus(transactional_api,pid)
        rename_nucleus(transactional_api,nid,'SAN AMBIGUO')
    iid=stage(api,pid,gpkg(tmp_path,'ambiguous-cycle',[('n',[(polygon(),{'NombreNucl':'SAN AMBIGUO'})])])).json()['id_importacion']
    f=preview(api,iid)[0];old=candidates(api,iid,f)
    assert len(old)==2 and f['estado_conciliacion']=='ambiguo'
    reconcile(api,iid,incluir_ambiguos=False,expected=409)
    second=reconcile(api,iid).json()
    current=candidates(api,iid,f)
    assert len(current)==4 and current[:2]==old and second['resumen']['resultados']=={'ambiguo':1}
    with transactional_api['session_factory']() as db:
        with pytest.raises(DBAPIError,match='histórico inmutable'):
            with db.begin_nested():
                db.execute(text("UPDATE importacion_feature_candidato SET criterio='alterado' WHERE id_candidato=:c"),{'c':old[0]['id_candidato']})


def test_seven_ran_events_keep_one_procedure_and_one_reported_ingress(transactional_api,transactional_target_domain):
    from tests.test_excel_closure_002 import _isolated_pn
    from tests.test_cierre_006_ran_ciclos import _target
    api=transactional_api['request']
    project_row,pn=_isolated_pn(api,transactional_target_domain)
    target,target_id=_target(api,pn['id_proyecto_nucleo'],'acta')
    procedure=api('POST','/api/tramites-ran',expected=201,json={**target,
        'referencia_expediente':'QA-026-'+uuid.uuid4().hex[:12]}).json()
    codes=_catalog(api,'tipo_evento_ran')
    sequence=['ingreso','prevencion','subsanacion','reingreso','prevencion','reingreso','inscripcion']
    for ordinal,code in enumerate(sequence,1):
        body={'ordinal':ordinal,'id_tipo_evento':codes[code],
              'fecha_evento':f'2026-01-{ordinal:02d}','numero_solicitud':'QA-026'}
        if code in {'prevencion','subsanacion'}:body['resultado']='Actuación humana registrada'
        api('POST',f"/api/tramites-ran/{procedure['id_tramite_ran']}/eventos",expected=201,json=body)
    events=api('GET',f"/api/tramites-ran/{procedure['id_tramite_ran']}/eventos").json()
    assert [e['id_tipo_evento'] for e in events]==[codes[c] for c in sequence]
    assert [e['ordinal'] for e in events]==list(range(1,8))
    assert len(api('GET',f'/api/asambleas/{target_id}/tramites-ran').json())==1
    report=api('GET','/api/reportes/avance-periodo',params={'id_proyecto':project_row['id_proyecto'],
        'anio':2026,'indicador':'ingreso_ran_acta'}).json()
    assert sum(r['realizado'] for r in report)==1


@pytest.mark.parametrize('kind',['nucleo','parcela'])
@pytest.mark.parametrize('same_topology',[True,False])
def test_new_delivery_versions_use_topology_and_preserve_domain(transactional_api,tmp_path,kind,same_topology):
    api=transactional_api['request']; con=transactional_api['connection']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    props={'cve_unica':key}; upload=stage; table='proyecto_nucleo_geometria'
    if kind=='parcela':
        parcel_id=parcel(transactional_api,nid,'P-100');link_parcel(transactional_api,pid,nid,parcel_id)
        props=attrs(key,'P-100');upload=stage_parcels;table='proyecto_parcela_geometria'
    before=domain_counts(con); rows=project_domain_rows(con,pid)
    x=polygon(); y=polygon()
    y['coordinates'][0]=list(reversed(y['coordinates'][0])) if same_topology else polygon(4)['coordinates'][0]
    for version,g in [(1,x),(2,y)]:
        iid=upload(api,pid,gpkg(tmp_path,f'{kind}-{version}-{same_topology}',[('g',[(g,props)])])).json()['id_importacion']
        finish(api,iid,accept=not same_topology)
    versions=con.execute(text(f'''SELECT g.version,g.activo,g.es_vigente FROM {table} g
        JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE pn.id_proyecto=:p ORDER BY version'''),{'p':pid}).all()
    assert versions==[(1,True,False),(2,True,True)]
    changes=reviews(api,pid,tipo_cambio='geometria_modificada')
    assert len(changes)==(0 if same_topology else 1)
    if changes:
        assert changes[0]['area_diferencia_m2'] is None # EPSG:4326 is angular.
        assert changes[0]['metricas']['politica']=='ST_Equals; sin tolerancia'
    assert domain_counts(con)==before and project_domain_rows(con,pid)==rows


@pytest.mark.parametrize('old_scope,new_scope,disappears',[
    ('completa','completa',True),('completa','parcial',False),('parcial','completa',False)])
@pytest.mark.parametrize('kind',['nucleo','parcela'])
def test_missing_feature_requires_two_complete_closed_deliveries(transactional_api,tmp_path,old_scope,new_scope,disappears,kind):
    api=transactional_api['request']; con=transactional_api['connection']; pid=project(api)
    if kind=='nucleo':
        ids=[nucleus(transactional_api,pid) for _ in range(3)]
        properties=[{'cve_unica':key} for _,key in ids]; upload=stage
    else:
        nid,key=nucleus(transactional_api,pid)
        ids=[parcel(transactional_api,nid,f'P-{number}') for number in range(3)]
        for item in ids: link_parcel(transactional_api,pid,nid,item)
        properties=[attrs(key,f'P-{number}') for number in range(3)];upload=stage_parcels
    old=upload(api,pid,gpkg(tmp_path,'complete-old',[('g',[(polygon(i*4),p) for i,p in enumerate(properties)])]),extra={'alcance_entrega':old_scope}).json()
    finish(api,old['id_importacion'])
    before=domain_counts(con); rows=project_domain_rows(con,pid)
    new=upload(api,pid,gpkg(tmp_path,'complete-new',[('g',[(polygon(i*4),properties[i]) for i in [0,2]])]),extra={'alcance_entrega':new_scope}).json()
    assert not reviews(api,pid,tipo_cambio='desaparece_en_nueva_version')
    confirm(api,new['id_importacion'],expected=409)
    finish(api,new['id_importacion'])
    changes=reviews(api,pid,tipo_cambio='desaparece_en_nueva_version')
    assert len(changes)==int(disappears)
    confirm(api,new['id_importacion']) # retry never duplicates the observation
    assert reviews(api,pid,tipo_cambio='desaparece_en_nueva_version')==changes
    assert domain_counts(con)==before and project_domain_rows(con,pid)==rows


@pytest.mark.parametrize('administrative_destination',[False,True])
def test_new_feature_without_destination_produces_observation_not_membership(transactional_api,tmp_path,administrative_destination):
    api=transactional_api['request']; con=transactional_api['connection']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    old=stage(api,pid,gpkg(tmp_path,'appear-old',[('g',[(polygon(),{'cve_unica':key})])])).json()
    finish(api,old['id_importacion'])
    key_d=nucleus(transactional_api,pid)[1] if administrative_destination else 'NO-ADMIN'
    before=domain_counts(con)
    new=stage(api,pid,gpkg(tmp_path,'appear-new',[('g',[(polygon(),{'cve_unica':key}),(polygon(4),{'cve_unica':key_d})])])).json()
    f=preview(api,new['id_importacion'])[1]
    assert f['estado_conciliacion']==('coincidencia_exacta' if administrative_destination else 'sin_coincidencia')
    changes=reviews(api,pid,tipo_cambio='aparece_en_nueva_version')
    assert len(changes)==1 and changes[0]['id_feature_nueva']==f['id_importacion_feature']
    assert changes[0]['id_proyecto_nucleo'] is None
    assert domain_counts(con)==before


def test_metric_crs_keeps_administrative_surfaces_amounts_and_cop_catalog(transactional_api,tmp_path):
    api=transactional_api['request']; con=transactional_api['connection']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    pn=api('GET',f'/api/proyectos/{pid}/nucleos').json()[0]['id_proyecto_nucleo']
    affect=api('POST',f'/api/proyecto-nucleo/{pn}/afectaciones',expected=201,json={
        'tipo_afectacion':'colectivo','superficie_preliminar_ha':'123.1234567',
        'superficie_afectada_ha':'12.7654321','avaluo_monto':'123456.78',
        'id_tipo_cop_operativo':_catalog(api,'tipo_cop_operativo')['TRANSVERSALES']}).json()
    agreement=api('POST',f"/api/afectaciones/{affect['id_afectacion']}/convenios",expected=201,json={
        'tipo_convenio':'cop_original','monto_100':'123456.78','fecha_firma':'2026-01-01'}).json()
    before=con.execute(text('SELECT to_jsonb(a),to_jsonb(c) FROM afectacion a JOIN convenio c USING(id_proyecto_nucleo) WHERE a.id_afectacion=:a'),{'a':affect['id_afectacion']}).all()
    api('PUT',f'/api/proyectos/{pid}/geoespacial/configuracion',json={'srid_trabajo':3857})
    for version in [1,2]:
        g=polygon();g['coordinates'][0][2][0]+=0.000000001*version
        iid=stage(api,pid,gpkg(tmp_path,f'metric-{version}',[('g',[(g,{'cve_unica':key})])])).json()['id_importacion']
        finish(api,iid,accept=version==2)
    change=reviews(api,pid,tipo_cambio='geometria_modificada')[0]
    assert change['srid_medicion']==3857 and change['area_diferencia_m2']>0
    assert change['porcentaje_diferencia']>0
    assert con.execute(text('SELECT to_jsonb(a),to_jsonb(c) FROM afectacion a JOIN convenio c USING(id_proyecto_nucleo) WHERE a.id_afectacion=:a'),{'a':affect['id_afectacion']}).all()==before


def test_ddv_both_intersect_with_changed_intersection_generates_review(transactional_api,tmp_path):
    api=transactional_api['request'];pid=project(api);nid,key=nucleus(transactional_api,pid)
    iid=stage(api,pid,gpkg(tmp_path,'both-n',[('n',[(polygon(),{'cve_unica':key})])])).json()['id_importacion']
    finish(api,iid)
    for version,offset in [(1,0),(2,0.5)]:
        ddv=stage_ddv(api,pid,gpkg(tmp_path,f'both-ddv-{version}',[('d',[(polygon(offset),{})])])).json()
        confirm_ddv(api,ddv['id_importacion'])
    changes=reviews(api,pid,tipo_cambio='cambio_relacion_ddv')
    assert len(changes)==1 and changes[0]['subtipo_cambio']=='intersecta_en_ambas_con_cambio'


def test_delivery_scope_is_explicit_and_identical_sha_cannot_change_scope(transactional_api,tmp_path):
    api=transactional_api['request'];pid=project(api);nid,key=nucleus(transactional_api,pid)
    content=gpkg(tmp_path,'scope',[('n',[(polygon(),{'cve_unica':key})])])
    api('POST',f'/api/proyectos/{pid}/geoespacial/nucleos/importaciones',expected=422,
        data={'fuente':'QA'},files={'archivo':('n.gpkg',content,'application/geopackage+sqlite3')})
    stage(api,pid,content,extra={'alcance_entrega':'completa'})
    stage(api,pid,content,expected=409,extra={'alcance_entrega':'parcial'})


@pytest.mark.parametrize('role,write',[('admin',True),('geografo',True),('operador',False),('visualizador',False)])
def test_history_endpoints_preserve_gis_roles_and_project_access(transactional_api,tmp_path,role,write):
    from types import SimpleNamespace
    from app import auth
    from app.main import app
    api=transactional_api['request'];pid=project(api);other=project(api);nid,key=nucleus(transactional_api,pid)
    for version in [1,2]:
        iid=stage(api,pid,gpkg(tmp_path,f'role-{version}',[('g',[(polygon(version*4),{'cve_unica':key}),
            (polygon(10),{'cve_unica':'NO-DESTINO'})])])).json()['id_importacion']
        finish(api,iid,accept=version==2)
    review=reviews(api,pid,tipo_cambio='geometria_modificada')[0]
    original=app.dependency_overrides[auth.get_current_user]
    if role=='admin': principal=original()
    else:
        created=api('POST','/api/usuarios',expected=201,json={'nombre':'QA GIS','apellido_paterno':'Sintético',
            'correo':uuid.uuid4().hex+'@example.invalid','rol':role,'contrasena':'Qa1!'+uuid.uuid4().hex+'Z'}).json()
        api('POST',f'/api/proyectos/{pid}/usuarios',expected=201,json={'id_usuario':created['id_usuario']})
        principal=SimpleNamespace(id_usuario=created['id_usuario'],rol=role,activo=True)
    try:
        app.dependency_overrides[auth.get_current_user]=lambda:principal
        assert cycles(api,iid)
        assert reviews(api,pid)
        api('GET',f"/api/geoespacial/revisiones/{review['id_revision']}")
        reconcile(api,iid,expected=201 if write else 403)
        api('POST',f"/api/geoespacial/revisiones/{review['id_revision']}/decisiones",expected=201 if write else 403,
            json={'accion':'revisado','motivo':'QA técnica','clave_solicitud':str(uuid.uuid4())})
        api('GET',f'/api/proyectos/{other}/geoespacial/revisiones',expected=200 if role=='admin' else 403)
    finally:
        app.dependency_overrides[auth.get_current_user]=original


@pytest.mark.parametrize('kind',['nucleo','parcela'])
def test_ddv_relation_changes_only_confirmed_authorized_geometry(transactional_api,tmp_path,kind):
    api=transactional_api['request']; con=transactional_api['connection']; pid=project(api)
    ids=[nucleus(transactional_api,pid) for _ in range(3)]
    props=[{'cve_unica':k} for n,k in ids];upload=stage
    if kind=='parcela':
        props=[];upload=stage_parcels
        for n,k in ids:
            p=parcel(transactional_api,n,'P-1');link_parcel(transactional_api,pid,n,p);props.append(attrs(k,'P-1'))
    imported=upload(api,pid,gpkg(tmp_path,'confirmed-abc',[('g',[(polygon(i*4),prop) for i,prop in enumerate(props)])])).json()
    finish(api,imported['id_importacion'])
    before=domain_counts(con); rows=project_domain_rows(con,pid)
    for version,offsets in [(1,[0,4]),(2,[0,8])]:
        ddv=stage_ddv(api,pid,gpkg(tmp_path,f'ddv-rel-{version}',[('d',[(polygon(x),{}) for x in offsets])])).json()
        confirm_ddv(api,ddv['id_importacion'])
    changes=reviews(api,pid,tipo_cambio='cambio_relacion_ddv',objetivo=kind)
    assert {c['subtipo_cambio'] for c in changes}=={'antes_intersectaba_ahora_no','antes_no_intersectaba_ahora_si'}
    assert len(changes)==2
    assert domain_counts(con)==before and project_domain_rows(con,pid)==rows


def test_review_decisions_append_only_link_existing_event_and_reject_cross_project(transactional_api,tmp_path):
    api=transactional_api['request']; con=transactional_api['connection']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    for version in [1,2]:
        iid=stage(api,pid,gpkg(tmp_path,f'decision-v{version}',[('g',[(polygon(version*4),{'cve_unica':key})])])).json()['id_importacion']
        finish(api,iid,accept=version==2)
    review=reviews(api,pid,tipo_cambio='geometria_modificada')[0]; rid=review['id_revision']; pn=review['id_proyecto_nucleo']
    before=domain_counts(con)
    body={'accion':'no_aplica','motivo':'Revisión técnica sin efectos','clave_solicitud':str(uuid.uuid4())}
    first=api('POST',f'/api/geoespacial/revisiones/{rid}/decisiones',expected=201,json=body).json()
    assert api('POST',f'/api/geoespacial/revisiones/{rid}/decisiones',expected=201,json=body).json()==first
    assert domain_counts(con)==before
    event_types=_catalog(api,'tipo_evento_seguimiento'); reasons=_catalog(api,'motivo_seguimiento')
    event=api('POST',f'/api/proyecto-nucleo/{pn}/seguimiento',expected=201,json={
        'ambito':'general','id_tipo_evento':event_types['cambio_alcance'],
        'id_motivo':reasons['nueva_informacion'],'fecha_evento':'2026-12-01','detalle':'Decisión humana'}).json()
    before=domain_counts(con)
    body={'accion':'aplicado','motivo':'Evento administrativo registrado por usuario',
          'clave_solicitud':str(uuid.uuid4()),'id_seguimiento_evento':event['id_seguimiento_evento']}
    api('POST',f'/api/geoespacial/revisiones/{rid}/decisiones',expected=201,json=body)
    detail=api('GET',f'/api/geoespacial/revisiones/{rid}').json()
    assert detail['estado_revision']=='aplicado' and len(detail['decisiones'])==2
    assert api('GET',f'/api/proyecto-nucleo/{pn}/seguimiento').json()==[event]
    assert domain_counts(con)==before
    other=project(api); other_nid,other_key=nucleus(transactional_api,other)
    other_pn=api('GET',f'/api/proyectos/{other}/nucleos').json()[0]['id_proyecto_nucleo']
    other_event=api('POST',f'/api/proyecto-nucleo/{other_pn}/seguimiento',expected=201,json={
        'ambito':'general','id_tipo_evento':event_types['cambio_alcance'],
        'id_motivo':reasons['nueva_informacion'],'fecha_evento':'2026-12-02','detalle':'Decisión humana en otro proyecto'}).json()
    body.update(clave_solicitud=str(uuid.uuid4()),id_seguimiento_evento=other_event['id_seguimiento_evento'])
    api('POST',f'/api/geoespacial/revisiones/{rid}/decisiones',expected=409,json=body)
    with transactional_api['session_factory']() as db:
        for statement in ["UPDATE revision_cambio_gis_decision SET motivo='cambio' WHERE id_revision=:r",
                          "UPDATE revision_cambio_gis SET metricas='{}' WHERE id_revision=:r"]:
            with pytest.raises(DBAPIError):
                with db.begin_nested(): db.execute(text(statement),{'r':rid})
