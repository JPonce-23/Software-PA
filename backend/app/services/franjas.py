from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sqlalchemy.exc import DBAPIError, IntegrityError
from datetime import datetime, timezone

from .. import models, schemas
from .common import set_audit_context
from . import cargas_geoespaciales

def get_franja_activa(db: Session, id_proyecto: int) -> models.FranjaDerechoVia:
    """Retorna el trazo/derecho de vía activo del proyecto, o None si no existe."""
    return db.query(models.FranjaDerechoVia).filter(
        models.FranjaDerechoVia.id_proyecto == id_proyecto,
        models.FranjaDerechoVia.activo == True
    ).first()

def validar_interseccion_afectacion(db: Session, id_tramo: int, geometria_wkt: str):
    """Valida que la afectación pertenezca a la sección vigente del tramo."""
    tramo = db.get(models.Tramo, id_tramo)
    seccion = db.query(models.SeccionDerechoVia).join(
        models.FranjaDerechoVia,
        models.FranjaDerechoVia.id_franja == models.SeccionDerechoVia.id_franja,
    ).filter(
        models.SeccionDerechoVia.id_tramo == id_tramo,
        models.SeccionDerechoVia.activo.is_(True),
        models.FranjaDerechoVia.activo.is_(True),
    ).one_or_none() if tramo else None
    if not seccion:
        raise HTTPException(
            status_code=409,
            detail="El tramo no cuenta con una sección activa del derecho de vía.",
        )

    # Validar intersección espacial
    result = db.execute(
        text("""
            SELECT ST_Intersects(
                ST_GeomFromText(:wkt, 4326),
                geometria_poligono
            ) as intersecta
            FROM seccion_derecho_via
            WHERE id_seccion = :id_seccion
        """),
        {
            "wkt": geometria_wkt,
            "id_seccion": seccion.id_seccion
        }
    ).fetchone()
    
    if not result or not result[0]:
        raise HTTPException(
            status_code=400,
            detail="La geometría de la afectación no intersecta con la sección oficial del derecho de vía del tramo."
        )

def importar_franja(
    db: Session,
    id_proyecto: int,
    data: schemas.FranjaDerechoViaCreate,
    user_id: int
) -> models.FranjaDerechoVia:
    geometry_wkt = data.geometria_wkt
    transformations = []
    geometry_kind = None
    source = "Captura técnica del trazo"
    if data.id_carga_geoespacial_feature is not None:
        geometry_wkt, geometry_kind, transformations, source = cargas_geoespaciales.confirmed_trazo_geometry(
            db,
            data.id_carga_geoespacial_feature,
        )
    proyecto = (
        db.query(models.Proyecto)
        .filter(models.Proyecto.id_proyecto == id_proyecto)
        .with_for_update()
        .first()
    )
    if proyecto is None or not proyecto.activo:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    try:
        with db.begin_nested():
            result = db.execute(
                text("""
                    WITH entrada AS (
                        SELECT ST_GeomFromText(:wkt, 4326) AS geom
                    )
                    SELECT
                        ST_IsValid(entrada.geom) AS is_valid,
                        NOT ST_IsEmpty(entrada.geom) AS is_not_empty,
                        ST_GeometryType(entrada.geom) AS geom_type
                    FROM entrada
                """),
                {"wkt": geometry_wkt},
            ).fetchone()
    except DBAPIError as exc:
        raise HTTPException(status_code=400, detail="Geometría inválida.") from exc
    
    if not result:
        raise HTTPException(status_code=400, detail="Geometría inválida.")
    if not result[0] or not result[1]:
        raise HTTPException(status_code=400, detail="Topología inválida: la geometría se auto-intersecta o está mal formada.")
    if result[2] not in ('ST_LineString', 'ST_MultiLineString', 'ST_Polygon', 'ST_MultiPolygon'):
        raise HTTPException(status_code=400, detail="El trazo confirmado debe ser una línea o un polígono válido.")
    if geometry_kind is None:
        geometry_kind = "linea" if result[2] in ('ST_LineString', 'ST_MultiLineString') else "poligono"
    set_audit_context(db, user_id)
    franja_actual = get_franja_activa(db, id_proyecto)
    siguiente_version = (
        db.query(func.coalesce(func.max(models.FranjaDerechoVia.version), 0) + 1)
        .filter(models.FranjaDerechoVia.id_proyecto == id_proyecto)
        .scalar()
    )

    if franja_actual:
        if data.fecha_vigencia_inicio < franja_actual.fecha_vigencia_inicio:
            raise HTTPException(
                status_code=400,
                detail="La nueva vigencia no puede iniciar antes que la versión activa.",
            )
        franja_actual.activo = False
        franja_actual.fecha_baja = datetime.now(timezone.utc)
        franja_actual.id_usuario_baja = user_id
        franja_actual.motivo_baja = "Sustituida por nueva versión importada."
        franja_actual.fecha_vigencia_fin = data.fecha_vigencia_inicio
        db.add(franja_actual)
    
    nueva_franja = models.FranjaDerechoVia(
        id_proyecto=id_proyecto,
        version=siguiente_version,
        fuente=source,
        fecha_vigencia_inicio=data.fecha_vigencia_inicio,
        activo=True,
        observaciones=data.observaciones
    )
    geometry_expression = func.ST_Multi(func.ST_GeomFromText(geometry_wkt, 4326))
    if geometry_kind == "linea":
        nueva_franja.geometria_linea = geometry_expression
    else:
        nueva_franja.geometria_poligono = geometry_expression
    db.add(nueva_franja)
    try:
        db.flush()
        if data.id_carga_geoespacial_feature is not None:
            cargas_geoespaciales.consume_confirmed_feature(
                db,
                data.id_carga_geoespacial_feature,
                "franja_derecho_via",
                nueva_franja.id_franja,
                user_id,
                transformations,
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La franja entra en conflicto con una versión existente.",
        ) from exc
    db.refresh(nueva_franja)
    nueva_franja.geometria_wkt = db.query(
        func.ST_AsText(func.coalesce(
            models.FranjaDerechoVia.geometria_linea,
            models.FranjaDerechoVia.geometria_poligono,
        ))
    ).filter(
        models.FranjaDerechoVia.id_franja == nueva_franja.id_franja
    ).scalar()
    return nueva_franja


def importar_seccion(
    db: Session,
    id_tramo: int,
    data: schemas.SeccionDerechoViaCreate,
    user_id: int,
) -> models.SeccionDerechoVia:
    tramo = db.query(models.Tramo).filter_by(id_tramo=id_tramo, activo=True).with_for_update().one_or_none()
    if not tramo:
        raise HTTPException(status_code=404, detail="Tramo no encontrado.")
    franja = get_franja_activa(db, tramo.id_proyecto)
    if not franja:
        raise HTTPException(status_code=409, detail="El proyecto requiere un trazo activo antes de cargar una sección.")
    geometry_wkt = data.geometria_wkt
    if data.id_carga_geoespacial_feature is not None:
        geometry_wkt = cargas_geoespaciales.confirmed_wkt(db, data.id_carga_geoespacial_feature, "seccion_derecho_via")
    try:
        result = db.execute(text("""
            WITH entrada AS (SELECT ST_GeomFromText(:wkt, 4326) AS geom)
            SELECT ST_IsValid(geom), NOT ST_IsEmpty(geom), ST_GeometryType(geom)
              FROM entrada
        """), {"wkt": geometry_wkt}).one()
    except DBAPIError as exc:
        raise HTTPException(status_code=400, detail="Geometría inválida.") from exc
    if not result[0] or not result[1] or result[2] not in ("ST_Polygon", "ST_MultiPolygon"):
        raise HTTPException(status_code=422, detail="La sección debe ser un polígono o multipolígono válido.")

    set_audit_context(db, user_id)
    anterior = db.query(models.SeccionDerechoVia).filter_by(id_tramo=id_tramo, activo=True).with_for_update().one_or_none()
    if anterior:
        anterior.activo = False
        anterior.fecha_baja = datetime.now(timezone.utc)
        anterior.id_usuario_baja = user_id
        anterior.motivo_baja = "Sustituida por una nueva sección del derecho de vía."
    seccion = models.SeccionDerechoVia(
        id_franja=franja.id_franja,
        id_tramo=id_tramo,
        fuente=data.fuente.strip(),
        activo=True,
        geometria_poligono=func.ST_Multi(func.ST_GeomFromText(geometry_wkt, 4326)),
    )
    db.add(seccion)
    try:
        db.flush()
        if data.id_carga_geoespacial_feature is not None:
            cargas_geoespaciales.consume_confirmed_feature(
                db, data.id_carga_geoespacial_feature, "seccion_derecho_via", seccion.id_seccion, user_id
            )
        db.commit()
    except (IntegrityError, DBAPIError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="La sección entra en conflicto con la división vigente del tramo.") from exc
    db.refresh(seccion)
    return seccion
