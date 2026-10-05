"""Conciliación GIS dirigida por el universo administrativo del proyecto."""
from __future__ import annotations

import unicodedata
from datetime import datetime, timezone

from fastapi import HTTPException
from geoalchemy2.elements import WKBElement, WKTElement
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .. import models
from .access import require_project_access
from .common import set_audit_context
from .gis_attributes import SAFE_FIELDS, sanitize_attributes
from .gis_ingestion import IngestionError, inspect_dataset, iter_features

PIPELINE_VERSION = 'conciliacion-v2'
NUCLEUS_TARGETS = {'nucleo_agrario', 'nucleo_agrario_gpkg'}
PARCEL_TARGETS = {'parcela', 'parcela_gpkg'}
RECONCILIATION_TARGETS = NUCLEUS_TARGETS | PARCEL_TARGETS


def normalize_text(value) -> str:
    value = unicodedata.normalize('NFKD', str(value or ''))
    return ' '.join(''.join(c for c in value if not unicodedata.combining(c)).casefold().split())


def value_of(properties, *names) -> str:
    lookup = {key.casefold(): value for key, value in properties.items()}
    for name in names:
        value = lookup.get(name.casefold())
        if value is not None and str(value).strip():
            return str(value).strip()
    return ''


def working_srid(db, project_id) -> int:
    config = db.get(models.ProyectoConfiguracionGis, project_id)
    return config.srid_trabajo if config and config.activo else 4326


def configure_project(db, project_id, srid, user):
    require_project_access(db, user, project_id, mode='gis')
    try:
        db.query(models.Proyecto).filter_by(id_proyecto=project_id).with_for_update().one()
        if not db.execute(text('SELECT EXISTS(SELECT 1 FROM spatial_ref_sys WHERE srid=:s)'), {'s':srid}).scalar_one():
            raise HTTPException(422, 'CRS de trabajo no registrado en PostGIS')
        # Validate the registered CRS has a usable transformation, not just an ID.
        db.execute(text('SELECT ST_Transform(ST_SetSRID(ST_Point(0,0),4326),:s)'), {'s':srid})
        current = working_srid(db, project_id)
        if srid != current and db.query(models.ImportacionArchivo).filter(
            models.ImportacionArchivo.id_proyecto == project_id,
            models.ImportacionArchivo.importados > 0,
            models.ImportacionArchivo.version_pipeline != "legacy-v1",
        ).first():
            raise HTTPException(409, 'CRS en uso; requiere reproyección explícita del proyecto')
        set_audit_context(db, user.id_usuario)
        config = db.get(models.ProyectoConfiguracionGis, project_id)
        if config is None:
            config = models.ProyectoConfiguracionGis(id_proyecto=project_id, srid_trabajo=srid, creado_por=user.id_usuario)
            db.add(config)
        else:
            config.srid_trabajo = srid
            config.actualizado_por = user.id_usuario
            config.actualizado_en = datetime.now(timezone.utc)
        db.commit()
        return config
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(422, 'No fue posible configurar el CRS de trabajo') from exc


def administrative_universe(db, project_id, *, parcels=False):
    nuclei = db.query(models.ProyectoNucleo, models.NucleoAgrario).join(
        models.NucleoAgrario, models.ProyectoNucleo.id_nucleo == models.NucleoAgrario.id_nucleo
    ).filter(models.ProyectoNucleo.id_proyecto == project_id,
             models.ProyectoNucleo.activo.is_(True), models.NucleoAgrario.activo.is_(True)).all()
    if not parcels:
        return [(pn, nucleus, None) for pn, nucleus in nuclei]
    links = db.execute(text('SELECT id_proyecto_nucleo,id_parcela FROM vw_gis_parcela_proyecto WHERE id_proyecto=:p'), {'p':project_id}).all()
    by_pn = {pn.id_proyecto_nucleo: (pn, n) for pn,n in nuclei}
    ids = {row.id_parcela for row in links}
    by_parcel = {p.id_parcela:p for p in db.query(models.Parcela).filter(models.Parcela.id_parcela.in_(ids)).all()} if ids else {}
    return [(*by_pn[row.id_proyecto_nucleo], by_parcel[row.id_parcela]) for row in links if row.id_proyecto_nucleo in by_pn]


def nucleus_criteria(properties, nucleus, *, parcel=False):
    key = value_of(properties, 'cve_unica_nucleo' if parcel else 'cve_unica')
    if key:
        if (nucleus.fuente_datos or '').strip().casefold() == 'ran_phina_catalogo_nucleos' and (nucleus.id_nucleo_fuente or '').strip() == key:
            return ['clave_oficial']
        return []
    name = value_of(properties, 'NombreNucl', 'nombre_nucleo', 'N__CLEO_AG')
    if not name or normalize_text(name) != normalize_text(nucleus.nombre_nucleo):
        return []
    criteria = ['nombre_normalizado']
    territorial = (
        (value_of(properties, 'NombreMuni', 'municipio'), nucleus.municipio.nombre, 'municipio'),
        (value_of(properties, 'NombreEnti', 'entidad', 'estado'), nucleus.municipio.entidad.nombre, 'entidad'),
        (value_of(properties, 'TipoNucleo', 'tipo_nucleo', 'TIPO_N__CL'), nucleus.tipo_tenencia.nombre, 'tipo_nucleo'),
    )
    for source, destination, field in territorial:
        if source and normalize_text(source) != normalize_text(destination):
            return []
        if source: criteria.append(field)
    return criteria


def geometry_model(parcel):
    return models.ProyectoParcelaGeometria if parcel is not None else models.ProyectoNucleoGeometria


def geometry_query(db, pn_id, parcel_id=None):
    model = geometry_model(parcel_id)
    query = db.query(model).filter(model.id_proyecto_nucleo == pn_id)
    if parcel_id is not None: query = query.filter(model.id_parcela == parcel_id)
    return query


def geometry_hash(db, pn_id, parcel_id=None):
    model = geometry_model(parcel_id)
    query = db.query(func.md5(func.ST_AsBinary(model.geometria_poligono))).filter(
        model.id_proyecto_nucleo == pn_id, model.es_vigente.is_(True))
    if parcel_id is not None: query = query.filter(model.id_parcela == parcel_id)
    return query.scalar()


def build_candidates(db, record, feature, properties, universe, user, *, direct_id=None):
    from .geospatial_imports import normalize_parcel_number
    is_parcel = record.tipo_objetivo in PARCEL_TARGETS
    for pn, nucleus, parcel in universe:
        criteria = nucleus_criteria(properties, nucleus, parcel=is_parcel)
        if direct_id is not None:
            destination = parcel.id_parcela if is_parcel else nucleus.id_nucleo
            criteria = ['id_administrativo_legacy'] if destination == direct_id else []
        if not criteria: continue
        number_criteria = []
        if is_parcel and direct_id is None:
            number = normalize_parcel_number(parcel.no_parcela or '')
            # Each source column is evaluated independently; suffixes survive.
            for column in ('PARCELA', 'Num_parcela', 'no_parcela'):
                source = value_of(properties, column)
                if source and normalize_parcel_number(source) == number:
                    number_criteria.append(column)
            if not number_criteria: continue
        observations = criteria + number_criteria
        exact = 'clave_oficial' in criteria or 'id_administrativo_legacy' in criteria
        strong = {'PARCELA','Num_parcela'}.issubset(number_criteria)
        db.add(models.ImportacionFeatureCandidato(
            id_importacion=record.id_importacion, id_importacion_feature=feature.id_importacion_feature,
            id_proyecto_nucleo=pn.id_proyecto_nucleo, id_parcela=parcel.id_parcela if parcel else None,
            criterio='ambos_numeros' if strong else number_criteria[0] if number_criteria else criteria[0],
            clasificacion='fuerte' if strong else 'exacta' if exact and not is_parcel else 'revision',
            coincidencias=observations, geometria_previa_hash=geometry_hash(db,pn.id_proyecto_nucleo,parcel.id_parcela if parcel else None),
            creado_por=user.id_usuario,
        ))
    db.flush()
    candidates = db.query(models.ImportacionFeatureCandidato).filter_by(id_importacion_feature=feature.id_importacion_feature).all()
    feature.estado_conciliacion = ('sin_coincidencia' if not candidates else 'ambiguo' if len(candidates)>1
        else 'coincidencia_exacta' if candidates[0].clasificacion=='exacta' else 'candidato')


def reconciliation_summary(db, record):
    universe = administrative_universe(db, record.id_proyecto, parcels=record.tipo_objetivo in PARCEL_TARGETS)
    keys = {(pn.id_proyecto_nucleo, p.id_parcela if p else None) for pn,n,p in universe}
    confirmed_keys = set()
    for pn_id, parcel_id in keys:
        if geometry_query(db,pn_id,parcel_id).filter(geometry_model(parcel_id).es_vigente.is_(True)).first():
            confirmed_keys.add((pn_id,parcel_id))
    feature_states = dict(db.query(models.ImportacionFeature.estado_conciliacion,func.count()).filter(
        models.ImportacionFeature.id_importacion==record.id_importacion).group_by(models.ImportacionFeature.estado_conciliacion).all())
    return {'registros_administrativos':len(keys), 'features_archivo':record.total_features,
            'confirmados':feature_states.get('confirmado',0), 'ambiguos':feature_states.get('ambiguo',0),
            'candidatos':feature_states.get('candidato',0)+feature_states.get('coincidencia_exacta',0),
            'registros_sin_geometria':len(keys-confirmed_keys),
            'features_sin_destino':feature_states.get('sin_coincidencia',0),
            'features_no_utilizadas':record.total_features-feature_states.get('confirmado',0),
            'ignoradas':feature_states.get('ignorado',0), 'rechazadas':feature_states.get('rechazado',0)}


async def stage(db, project_id, source, source_date, upload, user, *, target, mapping=None, strict=True):
    from . import geospatial_imports as legacy
    project = require_project_access(db,user,project_id,mode='gis')
    if not source.strip(): raise HTTPException(422,'La fuente es obligatoria')
    mapping = mapping or {}
    if mapping.get('id_destino') and mapping['id_destino'].casefold() not in {'record_id','id_destino','id_parcela','id_nucleo'}:
        raise HTTPException(422,'El mapeo debe usar un identificador administrativo técnico')
    path,digest,size,original,declared = await legacy._store_upload(upload,allowed_formats={'gpkg'} if strict else None)
    dataset_path = path
    record = None
    try:
        # Lock order shared with configuration and confirmation: project, then import.
        db.query(models.Proyecto).filter_by(id_proyecto=project.id_proyecto).with_for_update().one()
        srid = working_srid(db,project_id)
        existing = db.query(models.ImportacionArchivo).filter_by(id_proyecto=project_id,tipo_objetivo=target,
            sha256=digest,version_pipeline=PIPELINE_VERSION,srid_trabajo=srid,activo=True).first()
        if existing and existing.estado!='error': return existing
        set_audit_context(db,user.id_usuario)
        if existing:
            existing.activo=False; existing.fecha_baja=datetime.now(timezone.utc)
            existing.id_usuario_baja=user.id_usuario; existing.motivo_baja='Reintento de procesamiento fallido'
            db.flush()
        if declared=='zip': dataset_path=legacy._extract_zip(path)
        dataset=inspect_dataset(dataset_path)
        if strict and dataset.format!='gpkg': raise HTTPException(415,'El contenido no es GeoPackage')
        if dataset.format=='gpkg' and len(dataset.layers)!=1:
            raise HTTPException(422,'Se requiere exactamente una capa espacial de datos')
        for layer in dataset.layers:
            if not legacy._ddv_crs_identifiable(layer.crs): raise HTTPException(422,'CRS desconocido')
            if any(c.casefold().startswith('__pa_') for c in layer.columns): raise HTTPException(422,'Columna técnica reservada')
            if strict and target in RECONCILIATION_TARGETS and {c.casefold() for c in layer.columns}&{'id_nucleo','id_parcela','id_destino'}:
                raise HTTPException(422,'No se admiten identificadores internos en GPKG')
        record=models.ImportacionArchivo(id_proyecto=project_id,tipo_objetivo=target,nombre_original=original,
            nombre_almacenado=path.name,formato_detectado=dataset.format if declared!='zip' else 'zip',tamano_bytes=size,
            sha256=digest,fuente=source.strip(),fecha_fuente=source_date,crs_original=dataset.crs_description,
            crs_fuente_wkt='\n'.join(l.crs_wkt for l in dataset.layers),crs_destino='EPSG:4326',
            version_pipeline=PIPELINE_VERSION,srid_trabajo=srid,columnas_detectadas=[c for c in dataset.columns if c.casefold() in SAFE_FIELDS],
            mapeo=mapping,opciones_mapeo={},estado='procesando',total_features=dataset.total_features,
            id_usuario_carga=user.id_usuario,creado_por=user.id_usuario,fecha_procesamiento_inicio=datetime.now(timezone.utc))
        db.add(record); db.flush()
        universe=administrative_universe(db,project_id,parcels=target in PARCEL_TARGETS) if target in RECONCILIATION_TARGETS else []
        by_layer={l.name:l for l in dataset.layers}
        for index,(layer_name,item) in enumerate(iter_features(dataset_path,dataset,preserve_source_geometry=True)):
            layer=by_layer[layer_name]; raw=item.get('properties') or {}; geometry=item.get('geometry')
            source_fid=raw.pop('__pa_source_fid',item.get('id'))
            source_wkb=raw.pop('__pa_source_wkb',None)
            source_is_valid=None
            original_geometry=None
            dimension='XY'
            if source_wkb:
                inspected=db.execute(text("""WITH source AS (SELECT ST_GeomFromWKB(:g,:s) AS geom)
                    SELECT ST_Zmflag(geom) AS flags,ST_AsEWKB(geom) AS ewkb,
                           ST_IsValid(ST_Force2D(geom)) AS valid FROM source"""),
                    {'g':bytes.fromhex(source_wkb),'s':layer.srid or 0}).mappings().one()
                original_geometry=WKBElement(bytes(inspected['ewkb']),extended=True)
                source_is_valid=inspected['valid']
                dimension={0:'XY',1:'XYM',2:'XYZ',3:'XYZM'}[inspected['flags']]
            elif geometry:
                # GeoJSON input has no M representation.
                def coordinates_have_z(coords):
                    return bool(coords and (len(coords)>2 if isinstance(coords[0],(float,int)) else any(coordinates_have_z(c) for c in coords)))
                dimension='XYZ' if coordinates_have_z(geometry.get('coordinates',[])) else 'XY'
            wkt,errors,warnings,transformations=legacy._normalize_ddv_geometry(db,geometry,source_is_valid=source_is_valid)
            if dimension!='XY':
                transformations.append({'codigo':'DIMENSION_A_2D','origen':dimension,'destino':'XY'})
            if not layer.is_wgs84:
                transformations.insert(0,{'codigo':'CRS_REPROYECTADO','origen':layer.crs,'destino':'EPSG:4326'})
            working_geom=None
            if wkt:
                if srid != 4326 and srid == layer.srid and source_is_valid:
                    # Preserve native coordinates when source already uses the
                    # project's CRS. No 4326 -> source round-trip is necessary.
                    working_wkt=db.execute(text('SELECT ST_AsText(ST_Multi(ST_Force2D(ST_GeomFromEWKB(:g))),17)'),
                        {'g':bytes(inspected['ewkb'])}).scalar_one()
                    transformations.append({'codigo':'CRS_TRABAJO_SIN_REPROYECCION','crs':layer.crs})
                else:
                    working_wkt=db.execute(text('SELECT ST_AsText(ST_Transform(ST_GeomFromText(:g,4326),:s),17)'),{'g':wkt,'s':srid}).scalar_one()
                    if srid!=4326: transformations.append({'codigo':'CRS_TRABAJO','origen':'EPSG:4326','destino':f'EPSG:{srid}'})
                work_validation=db.execute(text('SELECT ST_IsValid(g),ST_IsEmpty(g),ST_IsValidReason(g) FROM (SELECT ST_GeomFromText(:g,:s) g) q'),{'g':working_wkt,'s':srid}).one()
                if work_validation[0] and not work_validation[1]:
                    working_geom=WKTElement(working_wkt,srid=srid)
                else:
                    errors.append({'codigo':'CRS_TRABAJO_ALTERO_TOPOLOGIA','razon':work_validation[2]})
            attrs=sanitize_attributes(raw)
            feature=models.ImportacionFeature(id_importacion=record.id_importacion,indice_feature=index,capa_origen=layer_name,
                id_externo=str(source_fid) if source_fid is not None else None,tipo_geometria=(geometry or {}).get('type'),
                atributos_originales=attrs,atributos_normalizados={},geometria_original=original_geometry,
                geometria_normalizada=WKTElement(wkt,srid=4326) if wkt else None,geometria_trabajo=working_geom,
                crs_fuente=layer.crs,dimension_fuente=dimension,
                estado='error' if errors else 'advertencia' if warnings else 'valido',errores=errors,advertencias=warnings,transformaciones=transformations)
            db.add(feature); db.flush()
            if target in RECONCILIATION_TARGETS:
                direct_id=None
                if mapping.get('id_destino'):
                    try: direct_id=int(raw[mapping['id_destino']])
                    except (ValueError,TypeError,KeyError): direct_id=-1
                if direct_id is not None: feature.atributos_normalizados={'id_destino':direct_id}
                build_candidates(db,record,feature,attrs,universe,user,direct_id=direct_id)
        counts=dict(db.query(models.ImportacionFeature.estado,func.count()).filter_by(id_importacion=record.id_importacion).group_by(models.ImportacionFeature.estado).all())
        record.validos=counts.get('valido',0); record.advertencias=counts.get('advertencia',0); record.errores=counts.get('error',0)
        record.features_procesados=sum(counts.values())
        if record.features_procesados!=dataset.total_features: raise IngestionError('CONTEO_FEATURES_INCONSISTENTE','Conteo inconsistente')
        record.estado='previsualizado'; record.fecha_procesamiento_fin=datetime.now(timezone.utc)
        record.reporte={'capas':[l.name for l in dataset.layers],'procesados':record.features_procesados,
            'validos':record.validos,'advertencias':record.advertencias,'errores':record.errores,
            'crs_original':dataset.crs_description,'crs_destino':'EPSG:4326','srid_trabajo':srid,
            'archivo_original_retenido':False}
        if target in RECONCILIATION_TARGETS: record.reporte={**record.reporte,**reconciliation_summary(db,record)}
        db.commit(); db.refresh(record)
        return record
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(422,getattr(exc,'public_detail','No fue posible procesar el archivo GIS')) from exc
    finally:
        # WKB, allowed source attributes and SHA retain technical provenance.
        # Uploaded originals can contain personal data and are not retained.
        path.unlink(missing_ok=True)
        if dataset_path!=path and path.with_suffix('').is_dir():
            import shutil
            shutil.rmtree(path.with_suffix(''))


def _locked_context(db,import_id,user):
    from .geospatial_imports import require_import_access
    record=require_import_access(db,import_id,user,mode='gis')
    db.query(models.Proyecto).filter_by(id_proyecto=record.id_proyecto).with_for_update().one()
    record=db.query(models.ImportacionArchivo).filter_by(id_importacion=import_id).populate_existing().with_for_update().one()
    if record.version_pipeline=='legacy-v1' or record.tipo_objetivo not in RECONCILIATION_TARGETS:
        raise HTTPException(409,'Esta importación no usa conciliación por proyecto')
    if record.estado!='previsualizado': raise HTTPException(409,'La importación no está previsualizada')
    if working_srid(db,record.id_proyecto)!=record.srid_trabajo: raise HTTPException(409,'La configuración CRS cambió; vuelva a procesar la fuente')
    return record


def decide(db,import_id,feature_id,data,user):
    try:
        record=_locked_context(db,import_id,user)
        set_audit_context(db,user.id_usuario)
        feature=db.query(models.ImportacionFeature).filter_by(id_importacion=import_id,id_importacion_feature=feature_id).with_for_update().one_or_none()
        if feature is None: raise HTTPException(404,'Feature no encontrada')
        if feature.estado_conciliacion in {'confirmado','ignorado'}: raise HTTPException(409,'La feature ya tiene decisión final')
        candidate=None; now=datetime.now(timezone.utc)
        if data.accion!='ignorar':
            candidate=db.query(models.ImportacionFeatureCandidato).filter_by(id_candidato=data.id_candidato,id_importacion_feature=feature_id).with_for_update().one_or_none()
            if candidate is None: raise HTTPException(404,'Candidato no encontrado en esta feature')
            if candidate.estado=='rechazado': raise HTTPException(409,'El candidato fue rechazado')
        elif data.id_candidato is not None:
            raise HTTPException(422,'Ignorar no admite candidato')
        if data.accion in {'seleccionar','confirmar'}:
            if feature.errores or feature.geometria_normalizada is None: raise HTTPException(409,'Feature sin geometría válida')
            # Revalidate and lock every row constituting membership. Project locks
            # serialize GIS decisions; admin updates are held until commit too.
            pn=db.query(models.ProyectoNucleo).filter_by(id_proyecto_nucleo=candidate.id_proyecto_nucleo,
                id_proyecto=record.id_proyecto,activo=True).with_for_update().one_or_none()
            if pn is None: raise HTTPException(409,'El destino ya no pertenece al proyecto')
            nucleus=db.query(models.NucleoAgrario).filter_by(id_nucleo=pn.id_nucleo,activo=True).with_for_update().one_or_none()
            if nucleus is None: raise HTTPException(409,'Núcleo inactivo')
            parcel=None
            if candidate.id_parcela is not None:
                links=db.execute(text('''SELECT a.id_afectacion,au.id_afectacion_unidad,u.id_unidad_agraria
                    FROM afectacion a JOIN afectacion_unidad_agraria au USING(id_afectacion)
                    JOIN unidad_agraria u USING(id_unidad_agraria)
                    WHERE a.id_proyecto_nucleo=:pn AND u.id_parcela=:p AND u.id_nucleo=:n
                      AND a.activo AND au.activo AND u.activo
                    FOR UPDATE OF a,au,u'''),{'pn':pn.id_proyecto_nucleo,'p':candidate.id_parcela,'n':pn.id_nucleo}).all()
                parcel=db.query(models.Parcela).filter_by(id_parcela=candidate.id_parcela,id_nucleo=pn.id_nucleo,activo=True).with_for_update().one_or_none()
                if not links or parcel is None: raise HTTPException(409,'Parcela sin vínculo administrativo activo')
            props=feature.atributos_originales
            if 'id_administrativo_legacy' not in candidate.coincidencias:
                criteria=nucleus_criteria(props,nucleus,parcel=parcel is not None)
                if not criteria: raise HTTPException(409,'La identidad administrativa cambió desde staging')
                if parcel is not None:
                    from .geospatial_imports import normalize_parcel_number
                    observed=[c for c in candidate.coincidencias if c in {'PARCELA','Num_parcela','no_parcela'}]
                    if not observed or not any(normalize_parcel_number(value_of(props,c))==normalize_parcel_number(parcel.no_parcela or '') for c in observed):
                        raise HTTPException(409,'El número administrativo cambió desde staging')
            previous=geometry_query(db,pn.id_proyecto_nucleo,candidate.id_parcela).filter(geometry_model(candidate.id_parcela).es_vigente.is_(True)).with_for_update().one_or_none()
            current_hash=geometry_hash(db,pn.id_proyecto_nucleo,candidate.id_parcela)
            if current_hash!=candidate.geometria_previa_hash: raise HTTPException(409,'La geometría cambió desde staging')
            warnings=list(feature.advertencias)
            if previous is not None:
                different=db.query(func.ST_Equals(previous.geometria_poligono,feature.geometria_normalizada)).scalar() is False
                if different: warnings.append({'codigo':'GEOMETRIA_EXISTENTE_DISTINTA'})
            if data.accion=='confirmar':
                if not data.confirmacion_explicita: raise HTTPException(422,'Se requiere confirmación explícita')
                if warnings and not data.aceptar_advertencias: raise HTTPException(409,'Debe aceptar las advertencias de reparación o reemplazo')
            selected=db.query(models.ImportacionFeatureCandidato).filter(
                models.ImportacionFeatureCandidato.id_importacion_feature==feature_id,
                models.ImportacionFeatureCandidato.estado=='seleccionado').all()
            for item in selected:
                if item.id_candidato!=candidate.id_candidato:
                    item.estado='propuesto'; item.actualizado_por=user.id_usuario; item.actualizado_en=now
            db.flush()
            candidate.estado='confirmado' if data.accion=='confirmar' else 'seleccionado'
            candidate.id_usuario_revision=user.id_usuario; candidate.fecha_revision=now
            candidate.actualizado_por=user.id_usuario; candidate.actualizado_en=now
            db.flush()  # unique indexes reject a destination selected twice.
            if data.accion=='confirmar':
                feature.estado='confirmado'; feature.estado_conciliacion='confirmado'
                feature.registro_destino_id=candidate.id_parcela if candidate.id_parcela is not None else pn.id_proyecto_nucleo
                feature.fecha_importacion=now; feature.fecha_revision=now; feature.id_usuario_revision=user.id_usuario
                feature.advertencias=warnings; feature.advertencias_aceptadas=bool(warnings)
                db.flush()
                model=geometry_model(candidate.id_parcela)
                if previous is not None:
                    previous.es_vigente=False; previous.actualizado_por=user.id_usuario; previous.actualizado_en=now
                    db.flush()
                version=geometry_query(db,pn.id_proyecto_nucleo,candidate.id_parcela).with_entities(func.coalesce(func.max(model.version),0)).scalar()+1
                values=dict(id_proyecto_nucleo=pn.id_proyecto_nucleo,id_importacion_feature=feature_id,
                    version=version,es_vigente=True,geometria_poligono=feature.geometria_normalizada,
                    geometria_trabajo=feature.geometria_trabajo,srid_trabajo=record.srid_trabajo,
                    fuente=record.fuente,fecha_fuente=record.fecha_fuente,creado_por=user.id_usuario)
                if candidate.id_parcela is not None: values['id_parcela']=candidate.id_parcela
                db.add(model(**values)); db.flush()
        elif data.accion=='rechazar':
            candidate.estado='rechazado'; candidate.id_usuario_revision=user.id_usuario; candidate.fecha_revision=now
            candidate.actualizado_por=user.id_usuario; candidate.actualizado_en=now; db.flush()
            remaining=db.query(models.ImportacionFeatureCandidato).filter(
                models.ImportacionFeatureCandidato.id_importacion_feature==feature_id,
                models.ImportacionFeatureCandidato.estado!='rechazado').count()
            feature.estado_conciliacion='rechazado' if not remaining else 'ambiguo' if remaining>1 else 'candidato'
        elif data.accion=='ignorar':
            for item in db.query(models.ImportacionFeatureCandidato).filter_by(id_importacion_feature=feature_id,estado='seleccionado').all():
                item.estado='propuesto'; item.actualizado_por=user.id_usuario; item.actualizado_en=now
            feature.estado='descartado'; feature.estado_conciliacion='ignorado'
            feature.id_usuario_revision=user.id_usuario; feature.fecha_revision=now
        db.add(models.ImportacionFeatureDecision(id_importacion_feature=feature_id,
            id_candidato=candidate.id_candidato if candidate else None,accion=data.accion,motivo=data.motivo,creado_por=user.id_usuario))
        db.flush()
        record.advertencias=db.query(models.ImportacionFeature).filter(models.ImportacionFeature.id_importacion==import_id,func.jsonb_array_length(models.ImportacionFeature.advertencias)>0).count()
        record.importados=db.query(models.ImportacionFeature).filter_by(id_importacion=import_id,estado_conciliacion='confirmado').count()
        record.descartados=db.query(models.ImportacionFeature).filter_by(id_importacion=import_id,estado_conciliacion='ignorado').count()
        record.reporte={**record.reporte,**reconciliation_summary(db,record)}
        record.actualizado_por=user.id_usuario; record.actualizado_en=now
        db.commit(); db.refresh(feature); return feature
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback(); raise HTTPException(409,'La decisión se revirtió; destino duplicado o contexto concurrente modificado') from exc


def finalize(db,record,data,user):
    try:
        record=_locked_context(db,record.id_importacion,user)
        if not data.confirmacion_explicita: raise HTTPException(422,'Se requiere confirmación explícita')
        # Unmatched features are valid residuals. Proposed/ambiguous features
        # require a decision, so completion never silently throws them away.
        pending=db.query(models.ImportacionFeature).filter(
            models.ImportacionFeature.id_importacion==record.id_importacion,
            (models.ImportacionFeature.estado_conciliacion.in_(['pendiente','candidato','coincidencia_exacta','ambiguo']) | ((models.ImportacionFeature.estado=='error') & (models.ImportacionFeature.estado_conciliacion!='ignorado')))).count()
        if pending: raise HTTPException(409,'Resuelva o ignore los candidatos pendientes antes de finalizar')
        set_audit_context(db,user.id_usuario); now=datetime.now(timezone.utc)
        record.confirmacion_explicita=True; record.fecha_confirmacion=now; record.id_usuario_confirmacion=user.id_usuario
        record.estado='completo'; record.actualizado_por=user.id_usuario; record.actualizado_en=now
        record.reporte={**record.reporte,**reconciliation_summary(db,record)}
        db.commit(); db.refresh(record); return record
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback(); raise HTTPException(409,'La finalización se revirtió completamente') from exc
