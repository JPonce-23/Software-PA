"""Servicios transaccionales para las afectaciones confirmadas.

El Subcorte 2A concentra aquí la integridad de captura. PostgreSQL mantiene la
misma defensa mediante constraints y triggers para escrituras externas.
"""

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from .common import get_active, set_audit_context
from .personas import ensure_persona_nucleo
from . import franjas
from . import cargas_geoespaciales


def _validar_contexto(
    db: Session,
    id_nucleo: int,
    id_tramo_nucleo: int,
) -> models.TramoNucleo:
    tramo_nucleo = get_active(
        db,
        models.TramoNucleo,
        id_tramo_nucleo,
        "id_tramo_nucleo",
        "El TramoNucleo especificado no existe.",
    )
    if tramo_nucleo.id_nucleo != id_nucleo:
        raise HTTPException(
            status_code=400,
            detail="Inconsistencia: El TramoNucleo no pertenece al NucleoAgrario especificado.",
        )
    return tramo_nucleo


def _titulares_activos(db: Session, id_parcela: int) -> int:
    return (
        db.query(models.ParcelaTitular)
        .join(models.Persona, models.Persona.id_persona == models.ParcelaTitular.id_persona)
        .filter(
            models.ParcelaTitular.id_parcela == id_parcela,
            models.ParcelaTitular.activo.is_(True),
            models.Persona.activo.is_(True),
        )
        .count()
    )


def validar_parcela_individual(
    db: Session,
    id_parcela: int,
    id_nucleo: int,
) -> models.Parcela:
    """Valida la parcela antes de abrir un subexpediente individual."""
    parcela = (
        db.query(models.Parcela)
        .filter(models.Parcela.id_parcela == id_parcela)
        .with_for_update()
        .first()
    )
    if parcela is None or not parcela.activo:
        raise HTTPException(status_code=404, detail="La Parcela especificada no existe o está inactiva.")
    if parcela.id_nucleo != id_nucleo:
        raise HTTPException(
            status_code=400,
            detail="Inconsistencia: La Parcela no pertenece al NucleoAgrario especificado.",
        )
    if not (parcela.no_parcela_ppt or "").strip():
        raise HTTPException(status_code=400, detail="La parcela requiere no_parcela_ppt para una afectación individual.")

    tiene_soporte = any(
        (
            (parcela.certificado_parcelario or "").strip(),
            (parcela.folio_derechos or "").strip(),
            parcela.constancia_vigencia_fecha,
            parcela.documentacion_disponible,
            (parcela.documentacion_faltante or "").strip(),
        )
    )
    if not tiene_soporte:
        raise HTTPException(
            status_code=400,
            detail="La parcela requiere soporte o justificación registral.",
        )

    titulares = _titulares_activos(db, parcela.id_parcela)
    minimo = 2 if parcela.tipo_parcela == "copropiedad" else 1
    if titulares < minimo:
        detalle = "dos titulares activos" if minimo == 2 else "un titular activo"
        raise HTTPException(
            status_code=400,
            detail=f"La parcela requiere al menos {detalle} para una afectación individual.",
        )
    return parcela


def _crear_afectacion(
    db: Session,
    data: dict,
    id_parcela: int | None,
    tramo_nucleo: models.TramoNucleo,
) -> models.Afectacion:
    wkt = data.pop("geometria_wkt")
    franjas.validar_interseccion_afectacion(db, tramo_nucleo.id_tramo, wkt)
    data.pop("parcela", None)
    data["id_parcela"] = id_parcela
    afectacion = models.Afectacion(**data)
    afectacion.geometria_afectacion = wkt
    db.add(afectacion)
    db.flush()
    return afectacion


def _commit_or_raise(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint = getattr(getattr(exc, "orig", None), "diag", None)
        nombre = getattr(constraint, "constraint_name", None)
        mensajes = {
            "chk_afectacion_tipo_parcela": "El tipo de afectación no corresponde con su parcela.",
            "chk_individual_requiere_parcela": "Una afectación individual requiere una parcela.",
            "fk_afectacion_parcela_mismo_nucleo": "La parcela no pertenece al mismo núcleo agrario.",
        }
        if nombre in mensajes:
            raise HTTPException(status_code=409, detail=mensajes[nombre]) from exc
        raise


def crear_colectiva(
    db: Session,
    data: schemas.AfectacionColectivaCreate,
    user_id: int,
) -> models.Afectacion:
    set_audit_context(db, user_id)
    tramo_nucleo = _validar_contexto(db, data.id_nucleo, data.id_tramo_nucleo)
    afectacion = _crear_afectacion(db, data.model_dump(), None, tramo_nucleo)
    _commit_or_raise(db)
    db.refresh(afectacion)
    return afectacion


def _crear_parcela_nueva(
    db: Session,
    data: schemas.ParcelaNuevaParaAfectacion,
    id_nucleo: int,
    user_id: int,
) -> models.Parcela:
    parcela_data = data.model_dump(exclude={"modo", "titulares"})
    feature_id = parcela_data.pop("id_carga_geoespacial_feature", None)
    if feature_id is not None:
        parcela_data["geometria_poligono"] = cargas_geoespaciales.confirmed_wkt(
            db, feature_id, "parcela"
        )
    parcela = models.Parcela(
        id_nucleo=id_nucleo,
        nombre_titular=None,
        **parcela_data,
    )
    db.add(parcela)
    db.flush()
    if feature_id is not None:
        cargas_geoespaciales.consume_confirmed_feature(
            db, feature_id, "parcela", parcela.id_parcela, user_id
        )

    for titular_data in data.titulares:
        persona = get_active(
            db,
            models.Persona,
            titular_data.id_persona,
            "id_persona",
            "Persona titular no encontrada",
        )
        ensure_persona_nucleo(
            db,
            persona,
            id_nucleo,
            user_id,
            titular_data.calidad_agraria,
        )
        db.add(
            models.ParcelaTitular(
                id_parcela=parcela.id_parcela,
                id_nucleo=id_nucleo,
                id_persona=persona.id_persona,
                tipo_derecho=titular_data.tipo_derecho,
                porcentaje_participacion=titular_data.porcentaje_participacion,
                fecha_inicio=titular_data.fecha_inicio,
                fecha_fin=titular_data.fecha_fin,
                observaciones=titular_data.observaciones,
            )
        )
    db.flush()
    return parcela


def crear_individual(
    db: Session,
    data: schemas.AfectacionIndividualCreate,
    user_id: int,
) -> models.Afectacion:
    """Crea una individual y, si aplica, parcela y titulares en una transacción."""
    try:
        set_audit_context(db, user_id)
        tramo_nucleo = _validar_contexto(db, data.id_nucleo, data.id_tramo_nucleo)
        if isinstance(data.parcela, schemas.ParcelaExistenteParaAfectacion):
            parcela = validar_parcela_individual(
                db, data.parcela.id_parcela, data.id_nucleo
            )
        else:
            parcela = _crear_parcela_nueva(db, data.parcela, data.id_nucleo, user_id)
            validar_parcela_individual(db, parcela.id_parcela, data.id_nucleo)

        afectacion = _crear_afectacion(
            db,
            data.model_dump(),
            parcela.id_parcela,
            tramo_nucleo,
        )
        _commit_or_raise(db)
        db.refresh(afectacion)
        return afectacion
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def actualizar_afectacion(
    db: Session,
    afectacion: models.Afectacion,
    data: schemas.AfectacionColectivaUpdate | schemas.AfectacionIndividualUpdate,
    user_id: int,
) -> models.Afectacion:
    set_audit_context(db, user_id)
    cambios = data.model_dump(exclude_unset=True)
    wkt = cambios.pop("geometria_wkt", None)
    for campo, valor in cambios.items():
        setattr(afectacion, campo, valor)
    if wkt is not None:
        tramo_nucleo = _validar_contexto(db, afectacion.id_nucleo, afectacion.id_tramo_nucleo)
        franjas.validar_interseccion_afectacion(db, tramo_nucleo.id_tramo, wkt)
        afectacion.geometria_afectacion = wkt
    _commit_or_raise(db)
    db.refresh(afectacion)
    return afectacion
