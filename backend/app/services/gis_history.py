"""Historia de conciliación y observaciones técnicas, sin escrituras administrativas."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from fastapi import HTTPException
from geoalchemy2.elements import WKBElement
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert

from .. import models
from .access import require_project_access
from .common import set_audit_context

ALGORITHM = "conciliacion-v3-historia"


def objective(target):
    from .gis_reconciliation import PARCEL_TARGETS, NUCLEUS_TARGETS
    return "parcela" if target in PARCEL_TARGETS else "nucleo" if target in NUCLEUS_TARGETS else "ddv"


def previous_delivery(db, project_id, target):
    from .gis_reconciliation import PARCEL_TARGETS, NUCLEUS_TARGETS
    targets = PARCEL_TARGETS if target in PARCEL_TARGETS else NUCLEUS_TARGETS if target in NUCLEUS_TARGETS else {target}
    return db.query(models.ImportacionArchivo).filter(
        models.ImportacionArchivo.id_proyecto == project_id,
        models.ImportacionArchivo.tipo_objetivo.in_(targets),
        models.ImportacionArchivo.estado == "completo",
        models.ImportacionArchivo.activo.is_(True),
        models.ImportacionArchivo.version_pipeline != "legacy-v1",
    ).order_by(models.ImportacionArchivo.id_importacion.desc()).first()


def create_cycle(db, record, universe, user, *, reason, kind="inicial", request_key=None):
    number = db.query(func.coalesce(func.max(models.ImportacionConciliacionCiclo.numero_ciclo), 0)).filter_by(
        id_importacion=record.id_importacion).scalar() + 1
    cycle = models.ImportacionConciliacionCiclo(
        id_importacion=record.id_importacion, numero_ciclo=number, tipo_ciclo=kind,
        motivo=reason, id_usuario=user.id_usuario, version_algoritmo=ALGORITHM,
        universo_destinos=[{"id_proyecto_nucleo":pn.id_proyecto_nucleo,
                            "id_nucleo":n.id_nucleo,"id_parcela":p.id_parcela if p else None,
                            "nombre_nucleo":n.nombre_nucleo,"fuente_identidad":n.fuente_datos,
                            "clave_oficial":n.id_nucleo_fuente,"municipio":n.municipio.nombre,
                            "entidad":n.municipio.entidad.nombre,"tipo_nucleo":n.tipo_tenencia.nombre,
                            "numero_parcela":p.no_parcela if p else None}
                           for pn,n,p in universe], clave_solicitud=request_key,
    )
    db.add(cycle)
    db.flush()
    return cycle


def feature_cycle(db, feature_id):
    return db.query(models.ImportacionConciliacionCiclo).join(
        models.ImportacionConciliacionResultado,
        models.ImportacionConciliacionResultado.id_ciclo == models.ImportacionConciliacionCiclo.id_ciclo,
    ).filter(models.ImportacionConciliacionResultado.id_importacion_feature == feature_id).order_by(
        models.ImportacionConciliacionCiclo.numero_ciclo.desc()).first()


def close_cycles(db, record):
    now = datetime.now(timezone.utc)
    for cycle in db.query(models.ImportacionConciliacionCiclo).filter_by(
        id_importacion=record.id_importacion, estado="abierto").all():
        cycle.estado = "finalizado"
        cycle.fecha_fin = now


def reconcile(db, import_id, data, user):
    from .geospatial_imports import require_import_access
    from . import gis_reconciliation as matching
    try:
        record = require_import_access(db, import_id, user, mode="gis")
        db.query(models.Proyecto).filter_by(id_proyecto=record.id_proyecto).with_for_update().one()
        require_project_access(db,user,record.id_proyecto,mode="gis")
        record = db.query(models.ImportacionArchivo).filter_by(id_importacion=import_id).populate_existing().with_for_update().one()
        if record.tipo_objetivo not in matching.RECONCILIATION_TARGETS or record.version_pipeline == "legacy-v1":
            raise HTTPException(409, "Esta importación no conserva staging conciliable por proyecto")
        if record.estado not in {"previsualizado", "completo"}:
            raise HTTPException(409, "Importación no disponible para reconciliación")
        if record.srid_trabajo != matching.working_srid(db, record.id_proyecto):
            raise HTTPException(409, "La configuración CRS cambió; reprocesar fuente")
        existing = db.query(models.ImportacionConciliacionCiclo).filter_by(
            id_importacion=import_id, clave_solicitud=data.clave_solicitud).first()
        parameters = {"incluir_ambiguos":data.incluir_ambiguos,"reabrir_rechazados":data.reabrir_rechazados}
        if existing:
            if existing.motivo != data.motivo or existing.resumen.get("parametros") != parameters:
                raise HTTPException(409, "Clave de solicitud reutilizada con otro contenido")
            db.commit()
            return existing
        states = {"sin_coincidencia"}
        if data.incluir_ambiguos: states.add("ambiguo")
        if data.reabrir_rechazados: states.add("rechazado")
        features = db.query(models.ImportacionFeature).filter(
            models.ImportacionFeature.id_importacion == import_id,
            models.ImportacionFeature.estado_conciliacion.in_(states),
        ).order_by(models.ImportacionFeature.id_importacion_feature).with_for_update().all()
        if not features:
            raise HTTPException(409, "No hay features elegibles")
        if any(f.geometria_normalizada is None or f.geometria_trabajo is None or f.errores for f in features):
            raise HTTPException(409, "Staging incompleto o inválido; no puede reconciliarse")
        universe = matching.administrative_universe(db, record.id_proyecto, parcels=record.tipo_objetivo in matching.PARCEL_TARGETS)
        set_audit_context(db, user.id_usuario)
        # Close the preceding attempt without changing its results or decisions.
        close_cycles(db, record)
        cycle = create_cycle(db, record, universe, user, reason=data.motivo,
                             kind="reconciliacion", request_key=data.clave_solicitud)
        for feature in features:
            direct_id = feature.atributos_normalizados.get("id_destino") if record.mapeo.get("id_destino") else None
            matching.build_candidates(db, record, feature, feature.atributos_originales, universe, user,
                                      direct_id=direct_id, cycle=cycle)
        results = dict(db.query(models.ImportacionConciliacionResultado.estado_matching,func.count()).filter_by(
            id_ciclo=cycle.id_ciclo).group_by(models.ImportacionConciliacionResultado.estado_matching).all())
        cycle.resumen = {"features":len(features),"resultados":results,"parametros":parameters}
        record.estado = "previsualizado"
        record.actualizado_por = user.id_usuario
        record.actualizado_en = datetime.now(timezone.utc)
        record.reporte = {**record.reporte,**matching.reconciliation_summary(db, record)}
        db.commit()
        db.refresh(cycle)
        return cycle
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(409, "La reconciliación se revirtió completamente") from exc


def cycle_detail(db, record, cycle_id):
    from .gis_read_models import cycle_detail as project_cycle
    return project_cycle(db, record, cycle_id)


def record_revision(db, user, **values):
    # Logical source identity excludes descriptive metrics and timestamps.
    identity = {k:v for k,v in values.items() if k.startswith("id_") or k in {"objetivo","tipo_cambio","subtipo_cambio"}}
    key = hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
    db.execute(insert(models.RevisionCambioGis).values(
        **values,clave_comparacion=key,creado_por=user.id_usuario,
    ).on_conflict_do_nothing(index_elements=["clave_comparacion"]))


def compare_geometry(db, old_geom, new_geom, srid):
    """Equality first; m² only for a registered, explicitly metre-based projection."""
    def ewkb(value):
        return bytes(value.data)
    result = db.execute(text("""
        WITH shapes AS (SELECT ST_Transform(ST_GeomFromEWKB(:a),:s) a,
                               ST_Transform(ST_GeomFromEWKB(:b),:s) b)
        SELECT ST_Equals(a,b) AS iguales, ST_NumGeometries(a) AS componentes_antes,
        ST_NumGeometries(b) AS componentes_despues,
        CASE WHEN :medible THEN ST_Area(a) END AS area_anterior_m2,
        CASE WHEN :medible THEN ST_Area(b) END AS area_nueva_m2,
        CASE WHEN :medible THEN ST_Area(ST_SymDifference(a,b)) END AS area_diferencia_m2
        FROM shapes
    """), {"a":ewkb(old_geom),"b":ewkb(new_geom),"s":srid,"medible":metric_crs(db,srid)}).mappings().one()
    values = {k:result[k] for k in ("area_anterior_m2","area_nueva_m2","area_diferencia_m2")}
    if result["area_anterior_m2"] is not None:
        values["srid_medicion"] = srid
        values["porcentaje_diferencia"] = (100*result["area_diferencia_m2"]/result["area_anterior_m2"]
                                            if result["area_anterior_m2"]>0 else None)
    values["metricas"]={"politica":"ST_Equals; sin tolerancia", "componentes_antes":result["componentes_antes"],
                       "componentes_despues":result["componentes_despues"],
                       "medicion_metrica":result["area_anterior_m2"] is not None}
    return result["iguales"], values


def metric_crs(db, srid):
    # A false negative leaves metrics NULL; it never reports degrees as m².
    return bool(db.execute(text("""SELECT proj4text ~ '(\\+units=m( |$)|\\+to_meter=1( |$))'
        AND proj4text !~ '\\+proj=(longlat|latlong|geocent)( |$)'
        FROM spatial_ref_sys WHERE srid=:s"""),{"s":srid}).scalar())


def geometry_changed(db, record, previous, new, user):
    if previous is None: return
    equal, metrics = compare_geometry(db,previous.geometria_trabajo,new.geometria_trabajo,record.srid_trabajo)
    if equal: return
    kind = objective(record.tipo_objetivo)
    old_feature = db.get(models.ImportacionFeature,previous.id_importacion_feature)
    values = {"id_proyecto":record.id_proyecto,"objetivo":kind,
              "id_proyecto_nucleo":new.id_proyecto_nucleo,"id_parcela":getattr(new,"id_parcela",None),
              "id_importacion_anterior":old_feature.id_importacion,"id_importacion_nueva":record.id_importacion,
              "tipo_cambio":"geometria_modificada",
              f"id_{kind}_geometria_anterior":previous.id_geometria,
              f"id_{kind}_geometria_nueva":new.id_geometria,**metrics}
    record_revision(db,user,**values)


def feature_identity(record, feature):
    from .gis_reconciliation import value_of, normalize_text
    from .geospatial_imports import normalize_parcel_number
    props = feature.atributos_originales
    kind = objective(record.tipo_objetivo)
    official = value_of(props,"cve_unica_nucleo" if kind=="parcela" else "cve_unica")
    name = normalize_text(value_of(props,"NombreNucl","nombre_nucleo","N__CLEO_AG"))
    nucleus = ("oficial",official) if official else ("texto",name,
        normalize_text(value_of(props,"NombreMuni","municipio")),normalize_text(value_of(props,"NombreEnti","entidad","estado")))
    if not official and not name: return None
    if kind != "parcela": return nucleus
    # No precedence between the two source numbers, including contradictions.
    numbers = tuple(sorted({normalize_parcel_number(value_of(props,c)) for c in ("PARCELA","Num_parcela","no_parcela") if value_of(props,c)}))
    return (nucleus,numbers) if numbers else None


def appearances(db, record, user):
    if record.id_importacion_anterior is None: return
    previous = db.get(models.ImportacionArchivo,record.id_importacion_anterior)
    identities = {feature_identity(previous,f) for f in db.query(models.ImportacionFeature).filter_by(id_importacion=previous.id_importacion)}
    previous_destinations = {(c.id_proyecto_nucleo,c.id_parcela) for c in db.query(models.ImportacionFeatureCandidato).filter_by(
        id_importacion=previous.id_importacion,estado="confirmado")}
    for feature in db.query(models.ImportacionFeature).filter_by(id_importacion=record.id_importacion):
        identity = feature_identity(record,feature)
        proposed = db.query(models.ImportacionFeatureCandidato).filter_by(id_importacion_feature=feature.id_importacion_feature).all()
        if identity is None or identity in identities or any((c.id_proyecto_nucleo,c.id_parcela) in previous_destinations for c in proposed): continue
        record_revision(db,user,id_proyecto=record.id_proyecto,objetivo=objective(record.tipo_objetivo),
                        id_feature_nueva=feature.id_importacion_feature,id_importacion_anterior=previous.id_importacion,
                        id_importacion_nueva=record.id_importacion,tipo_cambio="aparece_en_nueva_version")


def disappearances(db, record, user):
    if record.alcance_entrega != "completa" or record.id_importacion_anterior is None: return
    previous = db.get(models.ImportacionArchivo,record.id_importacion_anterior)
    if previous.alcance_entrega != "completa" or previous.estado != "completo" or previous.srid_trabajo != record.srid_trabajo: return
    from . import gis_reconciliation as matching
    universe = {(pn.id_proyecto_nucleo,p.id_parcela if p else None) for pn,n,p in matching.administrative_universe(
        db,record.id_proyecto,parcels=record.tipo_objetivo in matching.PARCEL_TARGETS)}
    features = db.query(models.ImportacionFeature).filter_by(id_importacion=record.id_importacion).all()
    identities = {feature_identity(record,f) for f in features}
    # Potential identity prevents an absence claim, including ignored ambiguity.
    destinations = {(c.id_proyecto_nucleo,c.id_parcela) for c in db.query(models.ImportacionFeatureCandidato).filter_by(id_importacion=record.id_importacion)}
    for candidate in db.query(models.ImportacionFeatureCandidato).filter_by(id_importacion=previous.id_importacion,estado="confirmado"):
        key = candidate.id_proyecto_nucleo,candidate.id_parcela
        old_feature = db.get(models.ImportacionFeature,candidate.id_importacion_feature)
        identity = feature_identity(previous,old_feature)
        if key not in universe or key in destinations or identity is None or identity in identities: continue
        old = matching.geometry_query(db,*key).filter_by(id_importacion_feature=old_feature.id_importacion_feature).one()
        kind = objective(record.tipo_objetivo)
        record_revision(db,user,id_proyecto=record.id_proyecto,objetivo=kind,
                        id_proyecto_nucleo=key[0],id_parcela=key[1],id_importacion_anterior=previous.id_importacion,
                        id_importacion_nueva=record.id_importacion,tipo_cambio="desaparece_en_nueva_version",
                        **{f"id_{kind}_geometria_anterior":old.id_geometria})


def ddv_changed(db, record, previous, new, user):
    if previous is None: return
    # A freshly assembled DDV still carries WKTElement in the ORM. Read the
    # stored version as EWKB, just as project-scoped confirmed geometries.
    db.refresh(new,attribute_names=['geometria_poligono','geometria_trabajo'])
    equal, metrics = compare_geometry(db,previous.geometria_trabajo or previous.geometria_poligono,
                                     new.geometria_trabajo,record.srid_trabajo)
    if not equal:
        record_revision(db,user,id_proyecto=record.id_proyecto,objetivo="ddv",
                        id_importacion_anterior=previous.id_importacion,id_importacion_nueva=record.id_importacion,
                        id_ddv_anterior=previous.id_derecho_via,id_ddv_nueva=new.id_derecho_via,
                        tipo_cambio="geometria_modificada",**metrics)
    from . import gis_reconciliation as matching
    for kind, parcels in (("nucleo",False),("parcela",True)):
        for pn,n,p in matching.administrative_universe(db,record.id_proyecto,parcels=parcels):
            geom = matching.geometry_query(db,pn.id_proyecto_nucleo,p.id_parcela if p else None).filter_by(es_vigente=True,activo=True).first()
            if geom is None: continue
            relation = db.execute(text("""WITH shapes AS(SELECT ST_Transform(ST_GeomFromEWKB(:g),:s) g,
                ST_Transform(ST_GeomFromEWKB(:a),:s) a,ST_Transform(ST_GeomFromEWKB(:b),:s) b)
                SELECT ST_Intersects(g,a) old,ST_Intersects(g,b) new,
                ST_Equals(ST_Intersection(g,a),ST_Intersection(g,b)) equal,
                ST_AsEWKB(ST_Intersection(g,a)) old_intersection,
                ST_AsEWKB(ST_Intersection(g,b)) new_intersection FROM shapes"""),
                {"g":bytes(geom.geometria_trabajo.data),
                 "a":bytes((previous.geometria_trabajo or previous.geometria_poligono).data),
                 "b":bytes(new.geometria_trabajo.data),"s":record.srid_trabajo}).mappings().one()
            subtype = ("antes_intersectaba_ahora_no" if relation["old"] and not relation["new"] else
                       "antes_no_intersectaba_ahora_si" if relation["new"] and not relation["old"] else
                       "intersecta_en_ambas_con_cambio" if relation["old"] and relation["new"] and not relation["equal"] else None)
            if subtype:
                _, relation_metrics = compare_geometry(db,
                    WKBElement(bytes(relation['old_intersection']),extended=True),
                    WKBElement(bytes(relation['new_intersection']),extended=True),record.srid_trabajo)
                relation_metrics['metricas']['medida']='interseccion_ddv'
                record_revision(db,user,id_proyecto=record.id_proyecto,objetivo=kind,
                    id_proyecto_nucleo=pn.id_proyecto_nucleo,id_parcela=p.id_parcela if p else None,
                    id_importacion_anterior=previous.id_importacion,id_importacion_nueva=record.id_importacion,
                    id_ddv_anterior=previous.id_derecho_via,id_ddv_nueva=new.id_derecho_via,
                    tipo_cambio="cambio_relacion_ddv",subtipo_cambio=subtype,**relation_metrics,
                    **{f"id_{kind}_geometria_anterior":geom.id_geometria,f"id_{kind}_geometria_nueva":geom.id_geometria})


def require_revision(db, revision_id, user, *, mode="read"):
    revision = db.get(models.RevisionCambioGis,revision_id)
    if revision is None: raise HTTPException(404,"Revisión GIS no encontrada")
    require_project_access(db,user,revision.id_proyecto,mode=mode)
    return revision


def revision_detail(db, revision_id, user):
    from .gis_read_models import revision_detail as project_revision
    return project_revision(db, revision_id, user)


def decide_revision(db, revision_id, data, user):
    try:
        revision = require_revision(db,revision_id,user,mode="gis")
        db.query(models.Proyecto).filter_by(id_proyecto=revision.id_proyecto).with_for_update().one()
        require_project_access(db,user,revision.id_proyecto,mode="gis")
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('software-pa:revision-gis:' || :r,0))"),
                   {'r':str(revision_id)})
        existing = db.query(models.RevisionCambioGisDecision).filter_by(id_revision=revision_id,clave_solicitud=data.clave_solicitud).first()
        if existing:
            if (existing.accion,existing.motivo,existing.id_seguimiento_evento)!=(data.accion,data.motivo,data.id_seguimiento_evento):
                raise HTTPException(409,"Clave de solicitud reutilizada con otro contenido")
            db.commit()
            return existing
        if data.id_seguimiento_evento is not None:
            if data.accion != "aplicado": raise HTTPException(422,"Sólo APLICADO admite un evento existente")
            event = db.query(models.SeguimientoEvento).filter_by(id_seguimiento_evento=data.id_seguimiento_evento,activo=True).with_for_update(read=True).one_or_none()
            if event is None: raise HTTPException(404,"Evento administrativo existente no encontrado")
            pn = db.get(models.ProyectoNucleo,event.id_proyecto_nucleo)
            if pn.id_proyecto != revision.id_proyecto or (revision.id_proyecto_nucleo is not None and pn.id_proyecto_nucleo != revision.id_proyecto_nucleo):
                raise HTTPException(409,"Evento de otro proyecto o núcleo")
            allowed = {None:(None,),"proyecto_nucleo":(revision.id_proyecto_nucleo,),"parcela":(revision.id_parcela,)}
            if event.entidad_tipo not in allowed or (event.entidad_tipo is not None and event.entidad_id not in allowed[event.entidad_tipo]):
                raise HTTPException(409,"Entidad del evento incompatible")
        set_audit_context(db,user.id_usuario)
        decision=models.RevisionCambioGisDecision(id_revision=revision_id,accion=data.accion,motivo=data.motivo,
            clave_solicitud=data.clave_solicitud,id_seguimiento_evento=data.id_seguimiento_evento,creado_por=user.id_usuario)
        db.add(decision)
        db.commit()
        db.refresh(decision)
        return decision
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(409,"La decisión de revisión se revirtió completamente") from exc
