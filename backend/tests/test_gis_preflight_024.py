"""Fixtures sintéticas; nunca dependemos de los GPKG locales entregados."""
import json
import sqlite3
import pytest
from sqlalchemy import text
from app.services.gis_ingestion import inspect_dataset, IngestionError
from tests.test_ddv_gpkg_imports import _gpkg, _polygon, _multipolygon, _project, _stage, _confirm


def add_styles(tmp_path,content):
    path=tmp_path/'with-styles.gpkg'; path.write_bytes(content)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE layer_styles(id INTEGER PRIMARY KEY,styleName TEXT)')
        db.execute("INSERT INTO layer_styles VALUES(1,'Synthetic QGIS style')")
        db.execute("INSERT INTO gpkg_contents(table_name,data_type,identifier,last_change,srs_id) VALUES('layer_styles','attributes','layer_styles','2026-01-01T00:00:00.000Z',0)")
    return path.read_bytes()


@pytest.mark.parametrize('styles',[False,True])
@pytest.mark.parametrize('crs',['EPSG:4326','EPSG:32614','EPSG:3857'])
def test_only_spatial_layers_count(tmp_path,styles,crs):
    content=_gpkg(tmp_path,'spatial',[('data',[_polygon()])],crs=crs)
    if styles: content=add_styles(tmp_path,content)
    path=tmp_path/'check.gpkg'; path.write_bytes(content)
    dataset=inspect_dataset(path)
    assert len(dataset.layers)==1 and dataset.total_features==1
    assert dataset.layers[0].crs==crs and dataset.layers[0].geometry_column=='geom'


def test_zero_spatial_layers_and_unknown_crs(tmp_path):
    content=add_styles(tmp_path,_gpkg(tmp_path,'none',[('data',[_polygon()])]))
    path=tmp_path/'none-spatial.gpkg'; path.write_bytes(content)
    with sqlite3.connect(path) as db:
        db.execute("DELETE FROM gpkg_contents WHERE table_name='data'")
        db.execute("DELETE FROM gpkg_geometry_columns WHERE table_name='data'")
        db.execute('DROP TABLE data')
    with pytest.raises(IngestionError,match='capas'): inspect_dataset(path)


def test_two_spatial_layers_rejected(transactional_api,tmp_path):
    api=transactional_api['request']; pid=_project(api)
    _stage(api,pid,_gpkg(tmp_path,'two',[('a',[_polygon()]),('b',[_polygon(3)])]),expected=422)
    _stage(api,pid,_gpkg(tmp_path,'unknown',[('a',[_polygon()])],unknown_crs=True),expected=422)


@pytest.mark.parametrize('geometry,error,warning',[
    (_polygon(),False,False),(_multipolygon(),False,False),
    ({'type':'Polygon','coordinates':[[[0,0],[2,2],[0,2],[2,0],[0,0]]]},False,True),
    ({'type':'Polygon','coordinates':[]},True,False),
    ({'type':'Point','coordinates':[0,0]},True,False),
    ({'type':'LineString','coordinates':[[0,0],[1,1]]},True,False),
    ({'type':'GeometryCollection','geometries':[_polygon()]},True,False),
])
def test_polygon_contract(transactional_api,tmp_path,geometry,error,warning):
    api=transactional_api['request']; pid=_project(api)
    staged=_stage(api,pid,_gpkg(tmp_path,'geometry',[('a',[geometry])])).json()
    assert bool(staged['errores'])==error and bool(staged['advertencias'])==warning
    if error: _confirm(api,staged['id_importacion'],accept=True,expected=409)
    elif warning:
        _confirm(api,staged['id_importacion'],expected=409)
        _confirm(api,staged['id_importacion'],accept=True)
    else: _confirm(api,staged['id_importacion'])


@pytest.mark.parametrize('z',[False,True])
@pytest.mark.parametrize('multi',[False,True])
def test_utm_and_z_source_preserved_and_explicitly_normalized(transactional_api,tmp_path,z,multi):
    api=transactional_api['request']; pid=_project(api)
    api('PUT',f'/api/proyectos/{pid}/geoespacial/configuracion',json={'srid_trabajo':32614})
    coords=[[400000,2200000],[400010,2200000],[400010,2200010],[400000,2200010],[400000,2200000]]
    if z: coords=[c+[17] for c in coords]
    g={'type':'MultiPolygon' if multi else 'Polygon','coordinates':[[coords]] if multi else [coords]}
    content=add_styles(tmp_path,_gpkg(tmp_path,'utm',[('a',[g])],crs='EPSG:32614'))
    staged=_stage(api,pid,content).json()
    assert staged['srid_trabajo']==32614 and staged['crs_original']=='EPSG:32614'
    f=api('GET',f"/api/importaciones/{staged['id_importacion']}/features").json()[0]
    assert f['dimension_fuente']==('XYZ' if z else 'XY')
    assert ('DIMENSION_A_2D' in {t['codigo'] for t in f['transformaciones']})==z
    row=transactional_api['connection'].execute(text('''SELECT ST_SRID(geometria_original),ST_NDims(geometria_original),
        ST_NDims(geometria_normalizada),ST_SRID(geometria_trabajo),ST_NPoints(geometria_trabajo),ST_IsValid(geometria_trabajo)
        FROM importacion_feature WHERE id_importacion=:id'''),{'id':staged['id_importacion']}).one()
    assert row==(32614,3 if z else 2,2,32614,5,True)
    assert transactional_api['connection'].execute(text('SELECT ST_Equals(ST_Multi(ST_Force2D(geometria_original)),geometria_trabajo) FROM importacion_feature WHERE id_importacion=:i'),{'i':staged['id_importacion']}).scalar_one()
    if z:
        assert transactional_api['connection'].execute(text('SELECT ST_Z(ST_PointN(ST_ExteriorRing(ST_GeometryN(geometria_original,1)),1)) FROM importacion_feature WHERE id_importacion=:id'),{'id':staged['id_importacion']}).scalar_one()==17
    _confirm(api,staged['id_importacion'])
    import hashlib
    ddv=transactional_api['connection'].execute(text('SELECT srid_trabajo,ST_SRID(geometria_trabajo),sha256 FROM derecho_via_proyecto WHERE id_importacion=:id'),{'id':staged['id_importacion']}).one()
    assert ddv==(32614,32614,hashlib.sha256(content).hexdigest())
    web=api('GET',f"/api/importaciones/{staged['id_importacion']}/features/{f['id_importacion_feature']}/geometria").json()
    assert web['geometry']['type']=='MultiPolygon'
    assert -180<web['geometry']['coordinates'][0][0][0][0]<180
    api('PUT',f'/api/proyectos/{pid}/geoespacial/configuracion',expected=409,json={'srid_trabajo':3857})


def test_pipeline_and_crs_are_part_of_idempotency(transactional_api,tmp_path,monkeypatch):
    from app.services import gis_reconciliation
    api=transactional_api['request']; pid=_project(api)
    content=_gpkg(tmp_path,'idempotent',[('a',[_polygon()])])
    first=_stage(api,pid,content).json(); repeated=_stage(api,pid,content).json()
    assert first['id_importacion']==repeated['id_importacion']
    monkeypatch.setattr(gis_reconciliation,'PIPELINE_VERSION','conciliacion-v3-test')
    second=_stage(api,pid,content).json()
    assert second['id_importacion']!=first['id_importacion'] and second['sha256']==first['sha256']
    api('PUT',f'/api/proyectos/{pid}/geoespacial/configuracion',json={'srid_trabajo':3857})
    third=_stage(api,pid,content).json()
    assert third['id_importacion']!=second['id_importacion']
    _confirm(api,first['id_importacion'],expected=409)  # stale CRS snapshot


def test_unregistered_working_crs_rejected(transactional_api):
    api=transactional_api['request']; pid=_project(api)
    api('PUT',f'/api/proyectos/{pid}/geoespacial/configuracion',expected=422,json={'srid_trabajo':999998})
