from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime, timezone

from .. import models, schemas
from .common import get_active, set_audit_context

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
        # Por compatibilidad, si no hay franja activa (debería haber por la migración), 
        # asume que pasa o rechaza. Según el diseño, todas deben tener V1.
        return

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
    set_audit_context(db, user_id)
    
    # Validar geometría WKT (debe ser POLYGON o MULTIPOLYGON y válido)
    # Validado en el request pero podemos hacer validación estricta postgis
    result = db.execute(
        text("""
            SELECT 
                ST_IsValid(geom) as is_valid, 
                ST_GeometryType(geom) as geom_type 
            FROM (SELECT ST_GeomFromText(:wkt, 4326) as geom) as t
        """),
        {"wkt": data.geometria_wkt}
    ).fetchone()
    
    if not result:
        raise HTTPException(status_code=400, detail="Geometría inválida.")
    if not result[0]:
        raise HTTPException(status_code=400, detail="Topología inválida: la geometría se auto-intersecta o está mal formada.")
    if result[1] not in ('ST_Polygon', 'ST_MultiPolygon'):
        raise HTTPException(status_code=400, detail="El archivo GeoJSON debe contener un polígono o multipolígono único.")
    
    # Inactivar franja actual
    franja_actual = get_franja_activa(db, id_tramo)
    siguiente_version = 1
    
    if franja_actual:
        siguiente_version = franja_actual.version + 1
        franja_actual.activo = False
        franja_actual.fecha_baja = datetime.now(timezone.utc)
        franja_actual.id_usuario_baja = user_id
        franja_actual.motivo_baja = "Sustituida por nueva versión importada."
        franja_actual.fecha_vigencia_fin = data.fecha_vigencia_inicio
        db.add(franja_actual)
    
    # Insertar nueva franja
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
    # Para asegurar formato en MULTIPOLYGON (si vino como POLYGON)
    nueva_franja.geometria_poligono = func.ST_Multi(func.ST_GeomFromText(data.geometria_wkt, 4326))
    db.add(nueva_franja)
    db.commit()
    db.refresh(nueva_franja)
    return nueva_franja
