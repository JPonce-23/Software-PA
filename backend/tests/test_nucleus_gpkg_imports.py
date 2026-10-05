"""Contrato GPKG estricto para geometrías de núcleos RAN ya existentes."""

import json
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from geoalchemy2.elements import WKTElement
from sqlalchemy import event, text

from app import auth, models
from app.database import engine
from app.main import app
from app.services.common import set_audit_context


def polygon(offset=0):
    return {"type": "Polygon", "coordinates": [[
        [offset, 0], [offset, 1], [offset + 1, 1], [offset + 1, 0], [offset, 0],
    ]]}


def gpkg(tmp_path, label, layers, *, crs="EPSG:4326", unknown_crs=False):
    destination = tmp_path / f"{label}.gpkg"
    for layer_name, features in layers:
        source = tmp_path / f"{label}-{layer_name}.geojson"
        source.write_text(json.dumps({
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "id": str(index), "geometry": geometry,
                 "properties": properties}
                for index, (geometry, properties) in enumerate(features)
            ],
        }, sort_keys=True), encoding="utf-8")
        command = ["ogr2ogr", "-f", "GPKG"]
        if destination.exists():
            command.append("-update")
        command.extend([str(destination), str(source), "-nln", layer_name, "-a_srs", crs])
        subprocess.run(command, check=True, capture_output=True, text=True)
    with sqlite3.connect(destination) as connection:
        connection.execute("UPDATE gpkg_contents SET last_change = '2026-01-01T00:00:00.000Z'")
        if unknown_crs:
            connection.execute("UPDATE gpkg_geometry_columns SET srs_id = 0")
            connection.execute("UPDATE gpkg_contents SET srs_id = 0")
    return destination.read_bytes()


def project(api):
    return api("POST", "/api/proyectos", expected=201, json={
        "clave_proyecto": f"NG-{uuid.uuid4().hex[:12]}",
        "nombre_proyecto": "Proyecto sintético núcleos GPKG",
    }).json()["id_proyecto"]


def nucleus(transactional_api, project_id, *, active=True, linked=True, geometry=None):
    with transactional_api["session_factory"]() as db:
        admin = db.query(models.Usuario).filter(models.Usuario.rol == "admin").first()
        municipality = db.query(models.Municipio).filter(models.Municipio.activo.is_(True)).first()
        tenure = db.query(models.CatalogoOperativo).filter(
            models.CatalogoOperativo.tipo_catalogo == "tipo_tenencia",
            models.CatalogoOperativo.codigo == "ejido",
        ).first()
        key = f"QA-{uuid.uuid4().hex}"
        set_audit_context(db, admin.id_usuario)
        item = models.NucleoAgrario(
            id_municipio=municipality.id_municipio,
            nombre_nucleo=f"Núcleo QA {key}",
            id_tipo_tenencia=tenure.id_catalogo_opcion,
            fuente_datos="RAN_PHINA_CATALOGO_NUCLEOS",
            id_entidad_fuente=str(municipality.id_entidad),
            id_municipio_fuente=str(municipality.id_municipio),
            id_nucleo_fuente=key,
            alcance_identidad_fuente="nacional",
            geometria_poligono=WKTElement(geometry, srid=4326) if geometry else None,
            fuente_geometria="Fuente anterior" if geometry else None,
            activo=active,
            creado_por=admin.id_usuario,
            fecha_baja=datetime.now(timezone.utc) if not active else None,
            id_usuario_baja=admin.id_usuario if not active else None,
            motivo_baja="QA" if not active else None,
        )
        db.add(item)
        db.flush()
        if linked:
            db.add(models.ProyectoNucleo(
                id_proyecto=project_id, id_nucleo=item.id_nucleo,
                activo=True, creado_por=admin.id_usuario,
            ))
        result = item.id_nucleo, key
        db.commit()
        return result


def stage(api, project_id, content, *, name="nucleos.gpkg", expected=201, extra=None):
    return api(
        "POST", f"/api/proyectos/{project_id}/geoespacial/nucleos/importaciones",
        expected=expected,
        data={"fuente": "Cartografía QA", "fecha_fuente": "2026-09-25", **(extra or {})},
        files={"archivo": (name, content, "application/geopackage+sqlite3")},
    )


def confirm(api, import_id, *, accept=False, expected=200):
    return api(
        "POST", f"/api/importaciones/{import_id}/confirmar", expected=expected,
        json={"confirmacion_explicita": True, "aceptar_advertencias": accept},
    )


def preview(api, import_id):
    return api("GET", f"/api/importaciones/{import_id}/features").json()


import pytest


def candidates(api, import_id, feature):
    return api('GET',f"/api/importaciones/{import_id}/features/{feature['id_importacion_feature']}/candidatos").json()


def decision(api, import_id, feature, action, candidate=None, *, accept=False, expected=200):
    return api('POST',f"/api/importaciones/{import_id}/features/{feature['id_importacion_feature']}/decisiones",
        expected=expected,json={'accion':action,'id_candidato':candidate['id_candidato'] if candidate else None,
                              'confirmacion_explicita':action=='confirmar','aceptar_advertencias':accept})


def rename_nucleus(ctx, nucleus_id, name):
    with ctx['session_factory']() as db:
        admin=db.query(models.Usuario).filter_by(rol='admin',activo=True).first()
        set_audit_context(db,admin.id_usuario)
        n=db.get(models.NucleoAgrario,nucleus_id); n.nombre_nucleo=name
        n.actualizado_por=admin.id_usuario
        db.commit()


@pytest.mark.parametrize('name',['SAN JOSÉ','san jose','  San   José  ','San Jose\u0301'])
def test_text_is_candidate_until_explicit_confirmation(transactional_api,tmp_path,name):
    api=transactional_api['request']; project_id=project(api)
    nucleus_id,key=nucleus(transactional_api,project_id)
    rename_nucleus(transactional_api,nucleus_id,'San José')
    staged=stage(api,project_id,gpkg(tmp_path,'text', [('nucleos',[(polygon(),{'NombreNucl':name})])])).json()
    feature=preview(api,staged['id_importacion'])[0]
    assert feature['estado_conciliacion']=='candidato' and feature['registro_destino_id'] is None
    assert transactional_api['connection'].execute(text('SELECT count(*) FROM proyecto_nucleo_geometria g JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE pn.id_proyecto='+str(project_id if 'project_id' in locals() else pid))).scalar_one()==0
    candidate=candidates(api,staged['id_importacion'],feature)[0]
    decision(api,staged['id_importacion'],feature,'seleccionar',candidate)
    assert transactional_api['connection'].execute(text('SELECT count(*) FROM proyecto_nucleo_geometria g JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE pn.id_proyecto='+str(project_id if 'project_id' in locals() else pid))).scalar_one()==0
    decision(api,staged['id_importacion'],feature,'confirmar',candidate)
    assert transactional_api['connection'].execute(text('SELECT geometria_poligono IS NULL FROM nucleo_agrario WHERE id_nucleo=:n'),{'n':nucleus_id}).scalar_one()
    assert confirm(api,staged['id_importacion']).json()['estado']=='completo'


def test_three_administrative_nuclei_six_features_partial_reconciliation(transactional_api,tmp_path):
    api=transactional_api['request']; project_id=project(api)
    ids=[nucleus(transactional_api,project_id) for _ in range(3)]
    for (nid,key),name in zip(ids,['San José','El Roble','San Jose']): rename_nucleus(transactional_api,nid,name)
    con=transactional_api['connection']
    tables=['proyecto','proyecto_nucleo','nucleo_agrario','parcela','afectacion','expediente_requisito']
    before={t:con.execute(text(f'SELECT count(*) FROM {t}')).scalar_one() for t in tables}
    staged=stage(api,project_id,gpkg(tmp_path,'six',[('nucleos',[
        (polygon(),{'cve_unica':ids[0][1]}),(polygon(3),{'NombreNucl':' EL  ROBLE '}),
        (polygon(6),{'NombreNucl':'san josé'}),(polygon(9),{'NombreNucl':'Extra GIS'}),
        (polygon(12),{'cve_unica':'NO-EXISTE'}),(polygon(15),{'NombreNucl':'Otra geometría'}),
    ])])).json()
    features=preview(api,staged['id_importacion'])
    assert [f['estado_conciliacion'] for f in features]==['coincidencia_exacta','candidato','ambiguo','sin_coincidencia','sin_coincidencia','sin_coincidencia']
    confirm(api,staged['id_importacion'],expected=409)
    for feature in features[:2]: decision(api,staged['id_importacion'],feature,'confirmar',candidates(api,staged['id_importacion'],feature)[0])
    ambiguous=api('GET',f"/api/importaciones/{staged['id_importacion']}/features?estado_conciliacion=ambiguo").json()
    assert len(ambiguous)==1
    assert len(candidates(api,staged['id_importacion'],features[2]))==2
    decision(api,staged['id_importacion'],features[2],'ignorar')
    finished=confirm(api,staged['id_importacion']).json()
    assert finished['importados']==2
    summary=api('GET',f"/api/importaciones/{staged['id_importacion']}/resumen").json()
    assert summary==dict(registros_administrativos=3,features_archivo=6,confirmados=2,ambiguos=0,candidatos=0,
                        registros_sin_geometria=1,features_sin_destino=3,features_no_utilizadas=4,ignoradas=1,rechazadas=0)
    assert before=={t:con.execute(text(f'SELECT count(*) FROM {t}')).scalar_one() for t in tables}
    assert con.execute(text('SELECT count(*) FROM proyecto_nucleo_geometria g JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE es_vigente AND pn.id_proyecto='+str(project_id))).scalar_one()==2


def test_official_key_outside_project_never_becomes_destination(transactional_api,tmp_path):
    api=transactional_api['request']; pid=project(api)
    nid,key=nucleus(transactional_api,pid,linked=False)
    staged=stage(api,pid,gpkg(tmp_path,'outside',[('n',[(polygon(),{'cve_unica':key})])])).json()
    feature=preview(api,staged['id_importacion'])[0]
    assert feature['estado_conciliacion']=='sin_coincidencia'
    assert candidates(api,staged['id_importacion'],feature)==[]
    confirm(api,staged['id_importacion'])
    assert transactional_api['connection'].execute(text('SELECT count(*) FROM proyecto_nucleo WHERE id_proyecto=:p'),{'p':pid}).scalar_one()==0


def test_rejected_and_ignored_features_leave_domain_unchanged(transactional_api,tmp_path):
    api=transactional_api['request']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    staged=stage(api,pid,gpkg(tmp_path,'reject',[('n',[(polygon(),{'cve_unica':key}),(polygon(3),{'cve_unica':key})])])).json()
    features=preview(api,staged['id_importacion'])
    decision(api,staged['id_importacion'],features[0],'rechazar',candidates(api,staged['id_importacion'],features[0])[0])
    decision(api,staged['id_importacion'],features[1],'ignorar')
    assert confirm(api,staged['id_importacion']).json()['importados']==0
    assert transactional_api['connection'].execute(text('SELECT count(*) FROM proyecto_nucleo_geometria g JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE pn.id_proyecto='+str(project_id if 'project_id' in locals() else pid))).scalar_one()==0
    decisions=api('GET',f"/api/importaciones/{staged['id_importacion']}/features/{features[0]['id_importacion_feature']}/decisiones").json()
    assert decisions[0]['accion']=='rechazar' and decisions[0]['creado_por']


def test_duplicate_destination_and_rollback_are_atomic(transactional_api,tmp_path):
    api=transactional_api['request']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    staged=stage(api,pid,gpkg(tmp_path,'duplicate',[('n',[(polygon(),{'cve_unica':key}),(polygon(3),{'cve_unica':key})])])).json()
    features=preview(api,staged['id_importacion']); candidate=candidates(api,staged['id_importacion'],features[0])[0]
    def fail_insert(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().startswith('INSERT INTO proyecto_nucleo_geometria'): raise RuntimeError('Rollback sintético')
    event.listen(engine,'before_cursor_execute',fail_insert)
    try: decision(api,staged['id_importacion'],features[0],'confirmar',candidate,expected=409)
    finally: event.remove(engine,'before_cursor_execute',fail_insert)
    assert preview(api,staged['id_importacion'])[0]['registro_destino_id'] is None
    assert api('GET',f"/api/importaciones/{staged['id_importacion']}/features/{features[0]['id_importacion_feature']}/decisiones").json()==[]
    decision(api,staged['id_importacion'],features[0],'confirmar',candidate)
    decision(api,staged['id_importacion'],features[1],'confirmar',candidates(api,staged['id_importacion'],features[1])[0],expected=409)
    assert transactional_api['connection'].execute(text('SELECT count(*) FROM proyecto_nucleo_geometria g JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE pn.id_proyecto='+str(project_id if 'project_id' in locals() else pid))).scalar_one()==1


def test_replacement_versions_and_independent_project_geometry(transactional_api,tmp_path):
    api=transactional_api['request']; pid=project(api); nid,key=nucleus(transactional_api,pid,geometry='MULTIPOLYGON(((0 0,0 1,1 1,1 0,0 0)))')
    other=project(api)
    with transactional_api['session_factory']() as db:
        admin=db.query(models.Usuario).filter_by(rol='admin',activo=True).first(); set_audit_context(db,admin.id_usuario)
        db.add(models.ProyectoNucleo(id_proyecto=other,id_nucleo=nid,creado_por=admin.id_usuario)); db.commit()
    for index in (1,2):
        staged=stage(api,pid,gpkg(tmp_path,f'version{index}',[('n',[(polygon(index*3),{'cve_unica':key})])])).json()
        f=preview(api,staged['id_importacion'])[0]; c=candidates(api,staged['id_importacion'],f)[0]
        if index==2: decision(api,staged['id_importacion'],f,'confirmar',c,expected=409)
        decision(api,staged['id_importacion'],f,'confirmar',c,accept=index==2); confirm(api,staged['id_importacion'])
    con=transactional_api['connection']
    assert con.execute(text('SELECT g.version,g.es_vigente,g.activo FROM proyecto_nucleo_geometria g JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE pn.id_proyecto='+str(pid)+' ORDER BY version')).all()==[(1,False,True),(2,True,True)]
    assert con.execute(text('SELECT count(*) FROM proyecto_nucleo_geometria g JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE pn.id_proyecto=:p'),{'p':other}).scalar_one()==0
    assert con.execute(text('SELECT ST_AsText(geometria_poligono) FROM nucleo_agrario WHERE id_nucleo=:n'),{'n':nid}).scalar_one()=='MULTIPOLYGON(((0 0,0 1,1 1,1 0,0 0)))'


def test_territorial_mismatch_and_fuzzy_name_do_not_match(transactional_api,tmp_path):
    api=transactional_api['request']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    rename_nucleus(transactional_api,nid,'San José')
    data=[{'NombreNucl':'San José','NombreMuni':'Municipio distinto'}, {'NombreNucl':'San Jos'}, {'cve_unica':'CLAVE-INCORRECTA','NombreNucl':'San José'}]
    staged=stage(api,pid,gpkg(tmp_path,'no-fuzzy',[('n',[(polygon(i*3),a) for i,a in enumerate(data)])])).json()
    assert all(f['estado_conciliacion']=='sin_coincidencia' for f in preview(api,staged['id_importacion']))


def test_strict_identifiers_and_layer_count(transactional_api,tmp_path):
    api=transactional_api['request']; pid=project(api)
    stage(api,pid,b'invalid',name='n.kmz',expected=415)
    stage(api,pid,gpkg(tmp_path,'ids',[('n',[(polygon(),{'id_nucleo':5})])]),expected=422)
    stage(api,pid,gpkg(tmp_path,'multi',[('n',[(polygon(),{})]),('other',[(polygon(3),{})])]),expected=422)
