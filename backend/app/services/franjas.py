from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sqlalchemy.exc import DBAPIError, IntegrityError
from datetime import datetime, timezone

from .. import models, schemas
from .common import set_audit_context

def get_franja_activa(db: Session, id_tramo: int) -> models.FranjaDerechoVia:
    """Retorna la franja activa para el tramo, o None si no existe."""
    return db.query(models.FranjaDerechoVia).filter(
        models.FranjaDerechoVia.id_tramo == id_tramo,
        models.FranjaDerechoVia.activo == True
    ).first()

def validar_interseccion_afectacion(db: Session, id_tramo: int, geometria_wkt: str):
    """Valida que la afectación intercepte con la franja activa del tramo."""
    franja = get_franja_activa(db, id_tramo)
    if not franja:
        raise HTTPException(
            status_code=409,
            detail="El tramo no cuenta con una franja de derecho de vía activa.",
        )

    # Validar intersección espacial
    result = db.execute(
        text("""
            SELECT ST_Intersects(
                ST_GeomFromText(:wkt, 4326),
                geometria_poligono
            ) as intersecta
            FROM franja_derecho_via
            WHERE id_franja = :id_franja
        """),
        {
            "wkt": geometria_wkt,
            "id_franja": franja.id_franja
        }
    ).fetchone()
    
    if not result or not result[0]:
        raise HTTPException(
            status_code=400,
            detail="La geometría de la afectación no intersecta con la franja de derecho de vía oficial."
        )

def importar_franja(
    db: Session,
    id_tramo: int,
    data: schemas.FranjaDerechoViaCreate,
    user_id: int
) -> models.FranjaDerechoVia:
    tramo = (
        db.query(models.Tramo)
        .filter(models.Tramo.id_tramo == id_tramo)
        .with_for_update()
        .first()
    )
    if tramo is None or not tramo.activo:
        raise HTTPException(status_code=404, detail="Tramo no encontrado")

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
                        ST_GeometryType(entrada.geom) AS geom_type,
                        ST_Intersects(entrada.geom, tramo.geometria_linea) AS intersecta_tramo
                    FROM entrada
                    JOIN tramo ON tramo.id_tramo = :id_tramo
                    WHERE tramo.activo = TRUE
                      AND tramo.geometria_linea IS NOT NULL
                """),
                {"wkt": data.geometria_wkt, "id_tramo": id_tramo},
            ).fetchone()
    except DBAPIError as exc:
        raise HTTPException(status_code=400, detail="Geometría inválida.") from exc
    
    if not result:
        raise HTTPException(status_code=400, detail="Geometría inválida.")
    if not result[0] or not result[1]:
        raise HTTPException(status_code=400, detail="Topología inválida: la geometría se auto-intersecta o está mal formada.")
    if result[2] not in ('ST_Polygon', 'ST_MultiPolygon'):
        raise HTTPException(status_code=400, detail="El archivo GeoJSON debe contener un polígono o multipolígono único.")
    if not result[3]:
        raise HTTPException(
            status_code=400,
            detail="La franja de derecho de vía no intersecta con la línea del tramo.",
        )

    set_audit_context(db, user_id)
    franja_actual = get_franja_activa(db, id_tramo)
    siguiente_version = (
        db.query(func.coalesce(func.max(models.FranjaDerechoVia.version), 0) + 1)
        .filter(models.FranjaDerechoVia.id_tramo == id_tramo)
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
        id_tramo=id_tramo,
        version=siguiente_version,
        ancho_izquierdo_m=data.ancho_izquierdo_m,
        ancho_derecho_m=data.ancho_derecho_m,
        fuente=data.fuente,
        fecha_vigencia_inicio=data.fecha_vigencia_inicio,
        activo=True,
        observaciones=data.observaciones
    )
    nueva_franja.geometria_poligono = func.ST_Multi(func.ST_GeomFromText(data.geometria_wkt, 4326))
    db.add(nueva_franja)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La franja entra en conflicto con una versión existente.",
        ) from exc
    db.refresh(nueva_franja)
    return nueva_franja
