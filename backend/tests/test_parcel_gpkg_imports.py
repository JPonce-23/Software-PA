"""Contrato GPKG estricto de geometrías para parcelas existentes."""

import uuid
from types import SimpleNamespace

from geoalchemy2.elements import WKTElement
from sqlalchemy import event, text

from app import auth, models
from app.database import engine
from app.main import app
from app.services.common import set_audit_context
from app.services.geospatial_imports import normalize_parcel_number
from tests.test_nucleus_gpkg_imports import (
    confirm, gpkg, nucleus, polygon, preview, project,
)


def parcel(transactional_api, nucleus_id, number, *, active=True, geometry=None):
    with transactional_api["session_factory"]() as db:
        admin = db.query(models.Usuario).filter(models.Usuario.rol == "admin").first()
        set_audit_context(db, admin.id_usuario)
        item = models.Parcela(
            id_nucleo=nucleus_id,
            tipo_parcela="individual",
            no_parcela=number,
            geometria_poligono=WKTElement(geometry, srid=4326) if geometry else None,
            fuente_geometria="Fuente anterior" if geometry else None,
            activo=active,
            creado_por=admin.id_usuario,
        )
        if not active:
            from datetime import datetime, timezone
            item.fecha_baja = datetime.now(timezone.utc)
            item.id_usuario_baja = admin.id_usuario
            item.motivo_baja = "QA"
        db.add(item)
        db.commit()
        return item.id_parcela


def stage(api, project_id, content, *, name="parcelas.gpkg", expected=201, extra=None):
    return api(
        "POST", f"/api/proyectos/{project_id}/geoespacial/parcelas/importaciones",
        expected=expected,
        data={"alcance_entrega": "parcial", "fuente": "Cartografía parcelaria QA", "fecha_fuente": "2026-09-25", **(extra or {})},
        files={"archivo": (name, content, "application/geopackage+sqlite3")},
    )


def attrs(key, number, **extra):
    return {"cve_unica_nucleo": key, "no_parcela": number, **extra}


import pytest
from tests.test_nucleus_gpkg_imports import candidates, decision, rename_nucleus


def link_parcel(ctx, project_id, nucleus_id, parcel_id):
    """Prepara la relación administrativa ANTES de ejecutar GIS."""
    with ctx['session_factory']() as db:
        admin=db.query(models.Usuario).filter_by(rol='admin',activo=True).first(); set_audit_context(db,admin.id_usuario)
        pn=db.query(models.ProyectoNucleo).filter_by(id_proyecto=project_id,id_nucleo=nucleus_id,activo=True).one()
        def catalog(kind,code): return db.query(models.CatalogoOperativo.id_catalogo_opcion).filter_by(tipo_catalogo=kind,codigo=code).scalar()
        unit=models.UnidadAgraria(id_nucleo=nucleus_id,id_parcela=parcel_id,id_tipo_tierra=catalog('tipo_tierra','parcelada'),
            id_tipo_titularidad=catalog('tipo_titularidad_unidad','persona'),id_tipo_gestion=catalog('tipo_gestion','PARCELA'),
            id_destino_superficie=catalog('destino_superficie','parcela_ejidal'),creado_por=admin.id_usuario)
        affectation=models.Afectacion(id_proyecto_nucleo=pn.id_proyecto_nucleo,tipo_afectacion='individual',creado_por=admin.id_usuario)
        db.add_all([unit,affectation]); db.flush()
        db.add(models.AfectacionUnidadAgraria(id_afectacion=affectation.id_afectacion,id_unidad_agraria=unit.id_unidad_agraria,creado_por=admin.id_usuario))
        db.commit()


def test_parcel_number_normalization_is_narrow():
    assert normalize_parcel_number(' P.-666 ')==normalize_parcel_number('P-666')=='p-666'
    assert len({normalize_parcel_number('P-585'+c) for c in 'ABCD'})==4
    assert normalize_parcel_number('P.-585A')!=normalize_parcel_number('P-585A')
    assert normalize_parcel_number('P/666')!=normalize_parcel_number('P-666')
    assert normalize_parcel_number('016')!=normalize_parcel_number('16')


@pytest.mark.parametrize('first,second,state,classification,count',[
    ('P-1','P-1','candidato','fuerte',1),('P-1','otro','candidato','revision',1),
    ('otro','P-1','candidato','revision',1),('P-1',None,'candidato','revision',1),
    (None,'P-1','candidato','revision',1),('P-1','P-2','ambiguo',None,2),
    ('otro','ninguno','sin_coincidencia',None,0),(None,None,'sin_coincidencia',None,0),
])
def test_independent_parcel_numbers(transactional_api,tmp_path,first,second,state,classification,count):
    api=transactional_api['request']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    ids=[parcel(transactional_api,nid,'P-'+str(i)) for i in (1,2)]
    for parcel_id in ids: link_parcel(transactional_api,pid,nid,parcel_id)
    con=transactional_api['connection']; before=con.execute(text('SELECT count(*) FROM parcela')).scalar_one()
    properties={'cve_unica_nucleo':key,'PARCELA':first,'Num_parcela':second,
        'titular':'Persona sintética excluida','CURP':'QA-NO-PERSONAL','domicilio':'No conservar','NOM_SEDATU':'Excluir'}
    staged=stage(api,pid,gpkg(tmp_path,'numbers',[('p',[(polygon(),properties)])])).json()
    f=preview(api,staged['id_importacion'])[0]
    assert f['estado_conciliacion']==state
    assert f['atributos_originales']['PARCELA']==first and f['atributos_originales']['Num_parcela']==second
    assert not {'CURP','titular','domicilio','NOM_SEDATU'}&set(f['atributos_originales'])
    cs=candidates(api,staged['id_importacion'],f); assert len(cs)==count
    if count==1: assert cs[0]['clasificacion']==classification
    assert con.execute(text('SELECT count(*) FROM parcela')).scalar_one()==before
    assert con.execute(text('SELECT count(*) FROM proyecto_parcela_geometria g JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE pn.id_proyecto='+str(pid))).scalar_one()==0


def test_textual_parcel_without_official_nucleus_key_and_suffixes(transactional_api,tmp_path):
    api=transactional_api['request']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    rename_nucleus(transactional_api,nid,'San José')
    ids={letter:parcel(transactional_api,nid,'P-585'+letter) for letter in 'ABCD'}
    for parcel_id in ids.values(): link_parcel(transactional_api,pid,nid,parcel_id)
    staged=stage(api,pid,gpkg(tmp_path,'suffixes',[('p',[(polygon(i*3),{'N__CLEO_AG':' SAN  JOSE ','Num_parcela':'P-585'+c}) for i,c in enumerate('ABCD')])])).json()
    fs=preview(api,staged['id_importacion'])
    assert all(f['estado_conciliacion']=='candidato' for f in fs)
    for f in fs: decision(api,staged['id_importacion'],f,'confirmar',candidates(api,staged['id_importacion'],f)[0])
    confirm(api,staged['id_importacion'])
    con=transactional_api['connection']
    assert set(con.execute(text('SELECT id_parcela FROM proyecto_parcela_geometria g JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE pn.id_proyecto='+str(pid))).scalars())==set(ids.values())
    assert all(con.execute(text('SELECT geometria_poligono IS NULL FROM parcela WHERE id_parcela=:p'),{'p':p}).scalar_one() for p in ids.values())


def test_unlinked_or_other_project_parcels_are_not_destinations(transactional_api,tmp_path):
    api=transactional_api['request']; pid=project(api); other=project(api); nid,key=nucleus(transactional_api,pid)
    with transactional_api['session_factory']() as db:
        admin=db.query(models.Usuario).filter_by(rol='admin',activo=True).first(); set_audit_context(db,admin.id_usuario)
        db.add(models.ProyectoNucleo(id_proyecto=other,id_nucleo=nid,creado_por=admin.id_usuario)); db.commit()
    p1=parcel(transactional_api,nid,'P-1'); p2=parcel(transactional_api,nid,'P-2')
    link_parcel(transactional_api,other,nid,p1)
    content=gpkg(tmp_path,'scope',[('p',[(polygon(),attrs(key,'P-1')),(polygon(3),attrs(key,'P-2'))])])
    staged=stage(api,pid,content).json()
    assert all(f['estado_conciliacion']=='sin_coincidencia' for f in preview(api,staged['id_importacion']))
    assert confirm(api,staged['id_importacion']).json()['importados']==0
    assert api('GET',f"/api/importaciones/{staged['id_importacion']}/resumen").json()['registros_administrativos']==0
    assert transactional_api['connection'].execute(text('SELECT count(*) FROM proyecto_parcela_geometria g JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE pn.id_proyecto='+str(pid))).scalar_one()==0


def test_parcel_mixed_import_finishes_without_using_extra_features(transactional_api,tmp_path):
    api=transactional_api['request']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    p1=parcel(transactional_api,nid,'P-666'); link_parcel(transactional_api,pid,nid,p1)
    staged=stage(api,pid,gpkg(tmp_path,'partial',[('p',[(polygon(),attrs(key,'P.-666')),(polygon(3),attrs(key,'EXTRA'))])])).json()
    fs=preview(api,staged['id_importacion'])
    decision(api,staged['id_importacion'],fs[0],'confirmar',candidates(api,staged['id_importacion'],fs[0])[0])
    assert confirm(api,staged['id_importacion']).json()['importados']==1
    summary=api('GET',f"/api/importaciones/{staged['id_importacion']}/resumen").json()
    assert summary['features_sin_destino']==1 and summary['features_no_utilizadas']==1


def test_parcel_rollback_on_geometry_insert(transactional_api,tmp_path):
    api=transactional_api['request']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    p1=parcel(transactional_api,nid,'P-1'); link_parcel(transactional_api,pid,nid,p1)
    staged=stage(api,pid,gpkg(tmp_path,'rollback',[('p',[(polygon(),attrs(key,'P-1'))])])).json()
    f=preview(api,staged['id_importacion'])[0]; c=candidates(api,staged['id_importacion'],f)[0]
    def fail(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().startswith('INSERT INTO proyecto_parcela_geometria'): raise RuntimeError('Rollback')
    event.listen(engine,'before_cursor_execute',fail)
    try: decision(api,staged['id_importacion'],f,'confirmar',c,expected=409)
    finally: event.remove(engine,'before_cursor_execute',fail)
    assert preview(api,staged['id_importacion'])[0]['estado_conciliacion']=='candidato'
    assert transactional_api['connection'].execute(text('SELECT count(*) FROM proyecto_parcela_geometria g JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE pn.id_proyecto='+str(pid))).scalar_one()==0


def test_documented_number_variants_can_be_ambiguous(transactional_api,tmp_path):
    api=transactional_api['request']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    for number in ('P-666','P.-666'):
        p=parcel(transactional_api,nid,number); link_parcel(transactional_api,pid,nid,p)
    staged=stage(api,pid,gpkg(tmp_path,'variant-ambiguous',[('p',[(polygon(),attrs(key,'P-666'))])])).json()
    f=preview(api,staged['id_importacion'])[0]
    assert f['estado_conciliacion']=='ambiguo' and len(candidates(api,staged['id_importacion'],f))==2


def test_lost_administrative_membership_blocks_confirmation(transactional_api,tmp_path):
    api=transactional_api['request']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    p=parcel(transactional_api,nid,'P-1'); link_parcel(transactional_api,pid,nid,p)
    staged=stage(api,pid,gpkg(tmp_path,'stale-member',[('p',[(polygon(),attrs(key,'P-1'))])])).json()
    f=preview(api,staged['id_importacion'])[0]; c=candidates(api,staged['id_importacion'],f)[0]
    with transactional_api['session_factory']() as db:
        from datetime import datetime,timezone
        admin=db.query(models.Usuario).filter_by(rol='admin',activo=True).first(); set_audit_context(db,admin.id_usuario)
        link=db.query(models.AfectacionUnidadAgraria).join(models.UnidadAgraria).filter(models.UnidadAgraria.id_parcela==p).one()
        link.activo=False;link.fecha_baja=datetime.now(timezone.utc);link.id_usuario_baja=admin.id_usuario;link.motivo_baja='QA';link.actualizado_por=admin.id_usuario
        db.commit()
    decision(api,staged['id_importacion'],f,'confirmar',c,expected=409)


def test_database_candidate_must_have_explicit_project_membership(transactional_api,tmp_path):
    from sqlalchemy.exc import DBAPIError
    api=transactional_api['request']; pid=project(api); nid,key=nucleus(transactional_api,pid)
    p=parcel(transactional_api,nid,'P-1')  # Global catalogue membership is insufficient.
    staged=stage(api,pid,gpkg(tmp_path,'forged',[('p',[(polygon(),attrs(key,'P-1'))])])).json()
    f=preview(api,staged['id_importacion'])[0]
    with transactional_api['session_factory']() as db:
        admin=db.query(models.Usuario).filter_by(rol='admin',activo=True).first(); set_audit_context(db,admin.id_usuario)
        pn=db.query(models.ProyectoNucleo).filter_by(id_proyecto=pid,id_nucleo=nid).one()
        with pytest.raises(DBAPIError):
            with db.begin_nested():
                db.add(models.ImportacionFeatureCandidato(id_importacion=staged['id_importacion'],id_importacion_feature=f['id_importacion_feature'],
                    id_proyecto_nucleo=pn.id_proyecto_nucleo,id_parcela=p,criterio='forjado',clasificacion='revision',coincidencias=[],creado_por=admin.id_usuario))
                db.flush()
