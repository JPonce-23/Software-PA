from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from .common import (
    commit_or_conflict,
    get_active,
    mark_inactive,
    reactivate,
    set_audit_context,
)
from . import cargas_geoespaciales


ORV_LEGACY_FIELDS = (
    "comisariado_presidente",
    "comisariado_secretario",
    "comisariado_tesorero",
    "consejo_vigilancia_presidente",
    "consejo_vigilancia_secretario1",
    "consejo_vigilancia_secretario2",
)


def list_personas(
    db: Session,
    q: str | None,
    skip: int,
    limit: int,
) -> list[models.Persona]:
    query = db.query(models.Persona).filter(models.Persona.activo.is_(True))
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.Persona.nombre.ilike(pattern),
                models.Persona.apellido_paterno.ilike(pattern),
                models.Persona.apellido_materno.ilike(pattern),
                models.Persona.curp.ilike(pattern),
                models.Persona.rfc.ilike(pattern),
            )
        )
    return (
        query.order_by(
            models.Persona.nombre,
            models.Persona.apellido_paterno,
            models.Persona.id_persona,
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_persona(
    db: Session,
    data: schemas.PersonaCreate,
    user_id: int,
) -> models.Persona:
    set_audit_context(db, user_id)
    persona = models.Persona(
        **data.model_dump(exclude_unset=True),
        datos_identidad_incompletos=not bool(data.curp),
        origen_registro="captura_sistema",
    )
    db.add(persona)
    commit_or_conflict(
        db,
        {"uq_persona_curp_normalizada": "Ya existe una persona con esa CURP"},
    )
    db.refresh(persona)
    return persona


def update_persona(
    db: Session,
    persona: models.Persona,
    data: schemas.PersonaUpdate,
    user_id: int,
) -> models.Persona:
    set_audit_context(db, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(persona, field, value)
    persona.datos_identidad_incompletos = not bool(persona.curp)
    commit_or_conflict(
        db,
        {"uq_persona_curp_normalizada": "Ya existe una persona con esa CURP"},
    )
    db.refresh(persona)
    return persona


def ensure_persona_nucleo(
    db: Session,
    persona: models.Persona,
    id_nucleo: int,
    user_id: int,
    calidad_agraria: str | None = None,
) -> models.PersonaNucleo:
    get_active(
        db,
        models.NucleoAgrario,
        id_nucleo,
        "id_nucleo",
        "Núcleo agrario no encontrado",
    )
    relacion = (
        db.query(models.PersonaNucleo)
        .filter_by(id_persona=persona.id_persona, id_nucleo=id_nucleo)
        .first()
    )
    if relacion is None:
        relacion = models.PersonaNucleo(
            id_persona=persona.id_persona,
            id_nucleo=id_nucleo,
            calidad_agraria=calidad_agraria,
        )
        db.add(relacion)
    elif not relacion.activo:
        reactivate(relacion, user_id, "Reactivación por nueva vinculación")
        if calidad_agraria is not None:
            relacion.calidad_agraria = calidad_agraria
    elif calidad_agraria is not None:
        relacion.calidad_agraria = calidad_agraria
    db.flush()
    return relacion


def create_legacy_persona(
    db: Session,
    nombre_completo: str,
) -> models.Persona:
    persona = models.Persona(
        nombre=nombre_completo.strip(),
        datos_identidad_incompletos=True,
        origen_registro="captura_sistema",
    )
    db.add(persona)
    db.flush()
    return persona


def add_orv_integrante(
    db: Session,
    orv: models.Orv,
    data: schemas.OrvIntegranteCreate,
    user_id: int,
) -> models.OrvIntegrante:
    set_audit_context(db, user_id)
    persona = get_active(
        db, models.Persona, data.id_persona, "id_persona", "Persona no encontrada"
    )
    ensure_persona_nucleo(
        db,
        persona,
        orv.id_nucleo,
        user_id,
        data.calidad_agraria,
    )
    existente = (
        db.query(models.OrvIntegrante)
        .filter_by(id_orv=orv.id_orv, cargo=data.cargo, activo=True)
        .first()
    )
    if existente:
        raise HTTPException(status_code=409, detail="El cargo ya tiene un integrante activo")
    integrante = models.OrvIntegrante(
        id_orv=orv.id_orv,
        id_nucleo=orv.id_nucleo,
        id_persona=persona.id_persona,
        cargo=data.cargo,
        observaciones=data.observaciones,
    )
    db.add(integrante)
    commit_or_conflict(
        db,
        {"uq_orv_integrante_cargo_activo": "El cargo ya tiene un integrante activo"},
    )
    return (
        db.query(models.OrvIntegrante)
        .options(joinedload(models.OrvIntegrante.persona))
        .filter_by(id_orv_integrante=integrante.id_orv_integrante)
        .one()
    )


def add_parcela_titular(
    db: Session,
    parcela: models.Parcela,
    data: schemas.ParcelaTitularCreate,
    user_id: int,
) -> models.ParcelaTitular:
    set_audit_context(db, user_id)
    persona = get_active(
        db, models.Persona, data.id_persona, "id_persona", "Persona no encontrada"
    )
    ensure_persona_nucleo(
        db,
        persona,
        parcela.id_nucleo,
        user_id,
        data.calidad_agraria,
    )
    existente = (
        db.query(models.ParcelaTitular)
        .filter_by(
            id_parcela=parcela.id_parcela,
            id_persona=persona.id_persona,
            activo=True,
        )
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=409,
            detail="La persona ya es titular activa de la parcela",
        )
    titular = models.ParcelaTitular(
        id_parcela=parcela.id_parcela,
        id_nucleo=parcela.id_nucleo,
        id_persona=persona.id_persona,
        tipo_derecho=data.tipo_derecho,
        porcentaje_participacion=data.porcentaje_participacion,
        fecha_inicio=data.fecha_inicio,
        fecha_fin=data.fecha_fin,
        observaciones=data.observaciones,
    )
    db.add(titular)
    commit_or_conflict(
        db,
        {
            "uq_parcela_titular_persona_activo": (
                "La persona ya es titular activa de la parcela"
            )
        },
    )
    return (
        db.query(models.ParcelaTitular)
        .options(joinedload(models.ParcelaTitular.persona))
        .filter_by(id_parcela_titular=titular.id_parcela_titular)
        .one()
    )


def create_parcela_compatible(
    db: Session,
    data: schemas.ParcelaCreate,
    user_id: int,
) -> models.Parcela:
    set_audit_context(db, user_id)
    get_active(
        db,
        models.NucleoAgrario,
        data.id_nucleo,
        "id_nucleo",
        "Núcleo agrario no encontrado",
    )
    parcela_data = data.model_dump()
    feature_id = parcela_data.pop("id_carga_geoespacial_feature", None)
    if feature_id is not None:
        parcela_data["geometria_poligono"] = cargas_geoespaciales.confirmed_wkt(
            db, feature_id, "parcela"
        )
    parcela = models.Parcela(**parcela_data)
    db.add(parcela)
    db.flush()
    if feature_id is not None:
        cargas_geoespaciales.consume_confirmed_feature(
            db, feature_id, "parcela", parcela.id_parcela, user_id
        )

    if data.nombre_titular and data.nombre_titular.strip():
        persona = create_legacy_persona(db, data.nombre_titular)
        ensure_persona_nucleo(db, persona, parcela.id_nucleo, user_id)
        db.add(
            models.ParcelaTitular(
                id_parcela=parcela.id_parcela,
                id_nucleo=parcela.id_nucleo,
                id_persona=persona.id_persona,
                tipo_derecho="titular",
            )
        )
    db.commit()
    db.refresh(parcela)
    return parcela


def create_parcela_normalizada(
    db: Session,
    data: schemas.ParcelaConTitularCreate,
    user_id: int,
) -> models.Parcela:
    set_audit_context(db, user_id)
    get_active(
        db,
        models.NucleoAgrario,
        data.parcela.id_nucleo,
        "id_nucleo",
        "Núcleo agrario no encontrado",
    )
    persona = get_active(
        db,
        models.Persona,
        data.titular.id_persona,
        "id_persona",
        "Persona titular no encontrada",
    )
    parcela_data = data.parcela.model_dump()
    feature_id = parcela_data.pop("id_carga_geoespacial_feature", None)
    if feature_id is not None:
        parcela_data["geometria_poligono"] = cargas_geoespaciales.confirmed_wkt(
            db, feature_id, "parcela"
        )
    parcela_data["nombre_titular"] = None
    parcela = models.Parcela(**parcela_data)
    db.add(parcela)
    db.flush()
    if feature_id is not None:
        cargas_geoespaciales.consume_confirmed_feature(
            db, feature_id, "parcela", parcela.id_parcela, user_id
        )
    ensure_persona_nucleo(
        db,
        persona,
        parcela.id_nucleo,
        user_id,
        data.titular.calidad_agraria,
    )
    db.add(
        models.ParcelaTitular(
            id_parcela=parcela.id_parcela,
            id_nucleo=parcela.id_nucleo,
            id_persona=persona.id_persona,
            tipo_derecho=data.titular.tipo_derecho,
            porcentaje_participacion=data.titular.porcentaje_participacion,
            fecha_inicio=data.titular.fecha_inicio,
            fecha_fin=data.titular.fecha_fin,
            observaciones=data.titular.observaciones,
        )
    )
    db.commit()
    db.refresh(parcela)
    return parcela


def update_parcela_compatible(
    db: Session,
    parcela: models.Parcela,
    data: schemas.ParcelaUpdate,
    user_id: int,
) -> models.Parcela:
    set_audit_context(db, user_id)
    changes = data.model_dump(exclude_unset=True)
    feature_id = changes.pop("id_carga_geoespacial_feature", None)
    if feature_id is not None:
        changes["geometria_poligono"] = cargas_geoespaciales.confirmed_wkt(
            db, feature_id, "parcela"
        )
    nuevo_nombre = changes.get("nombre_titular")
    nombre_cambio = (
        "nombre_titular" in changes
        and (nuevo_nombre or "").strip() != (parcela.nombre_titular or "").strip()
    )
    for field, value in changes.items():
        setattr(parcela, field, value)

    if feature_id is not None:
        cargas_geoespaciales.consume_confirmed_feature(
            db, feature_id, "parcela", parcela.id_parcela, user_id
        )

    if nombre_cambio:
        for titular in (
            db.query(models.ParcelaTitular)
            .filter_by(id_parcela=parcela.id_parcela, activo=True)
            .all()
        ):
            mark_inactive(titular, user_id, "Sustitución de titular desde formulario legado")
        if nuevo_nombre and nuevo_nombre.strip():
            persona = create_legacy_persona(db, nuevo_nombre)
            ensure_persona_nucleo(db, persona, parcela.id_nucleo, user_id)
            db.add(
                models.ParcelaTitular(
                    id_parcela=parcela.id_parcela,
                    id_nucleo=parcela.id_nucleo,
                    id_persona=persona.id_persona,
                    tipo_derecho="titular",
                )
            )
    db.commit()
    db.refresh(parcela)
    return parcela


def create_orv_compatible(
    db: Session,
    data: schemas.OrvCreate,
    user_id: int,
) -> models.Orv:
    set_audit_context(db, user_id)
    get_active(
        db,
        models.NucleoAgrario,
        data.id_nucleo,
        "id_nucleo",
        "Núcleo agrario no encontrado",
    )
    orv = models.Orv(**data.model_dump())
    db.add(orv)
    db.flush()
    for cargo in ORV_LEGACY_FIELDS:
        nombre = getattr(data, cargo, None)
        if nombre and nombre.strip():
            persona = create_legacy_persona(db, nombre)
            ensure_persona_nucleo(
                db, persona, orv.id_nucleo, user_id, "representante"
            )
            db.add(
                models.OrvIntegrante(
                    id_orv=orv.id_orv,
                    id_nucleo=orv.id_nucleo,
                    id_persona=persona.id_persona,
                    cargo=cargo,
                )
            )
    db.commit()
    db.refresh(orv)
    return orv


def create_orv_normalizado(
    db: Session,
    data: schemas.OrvConIntegrantesCreate,
    user_id: int,
) -> models.Orv:
    set_audit_context(db, user_id)
    get_active(
        db,
        models.NucleoAgrario,
        data.orv.id_nucleo,
        "id_nucleo",
        "Núcleo agrario no encontrado",
    )
    orv_data = data.orv.model_dump()
    for field in ORV_LEGACY_FIELDS:
        orv_data[field] = None
    orv = models.Orv(**orv_data)
    db.add(orv)
    db.flush()

    for item in data.integrantes:
        persona = get_active(
            db,
            models.Persona,
            item.id_persona,
            "id_persona",
            "Persona integrante no encontrada",
        )
        ensure_persona_nucleo(
            db,
            persona,
            orv.id_nucleo,
            user_id,
            item.calidad_agraria,
        )
        db.add(
            models.OrvIntegrante(
                id_orv=orv.id_orv,
                id_nucleo=orv.id_nucleo,
                id_persona=persona.id_persona,
                cargo=item.cargo,
                observaciones=item.observaciones,
            )
        )
    commit_or_conflict(
        db,
        {"uq_orv_integrante_cargo_activo": "No se puede repetir un cargo activo"},
    )
    db.refresh(orv)
    return orv


def update_orv_compatible(
    db: Session,
    orv: models.Orv,
    data: schemas.OrvUpdate,
    user_id: int,
) -> models.Orv:
    set_audit_context(db, user_id)
    changes = data.model_dump(exclude_unset=True)
    for cargo in ORV_LEGACY_FIELDS:
        if cargo not in changes:
            continue
        nuevo_nombre = (changes[cargo] or "").strip()
        nombre_actual = (getattr(orv, cargo) or "").strip()
        if nuevo_nombre == nombre_actual:
            continue
        for integrante in (
            db.query(models.OrvIntegrante)
            .filter_by(id_orv=orv.id_orv, cargo=cargo, activo=True)
            .all()
        ):
            mark_inactive(
                integrante,
                user_id,
                "Sustitución de integrante desde formulario legado",
            )
        if nuevo_nombre:
            persona = create_legacy_persona(db, nuevo_nombre)
            ensure_persona_nucleo(
                db, persona, orv.id_nucleo, user_id, "representante"
            )
            db.add(
                models.OrvIntegrante(
                    id_orv=orv.id_orv,
                    id_nucleo=orv.id_nucleo,
                    id_persona=persona.id_persona,
                    cargo=cargo,
                )
            )

    for field, value in changes.items():
        setattr(orv, field, value)
    db.commit()
    db.refresh(orv)
    return orv


def soft_delete_relation(
    db: Session,
    entity,
    user_id: int,
    motivo: str,
) -> None:
    set_audit_context(db, user_id)
    mark_inactive(entity, user_id, motivo)
    db.commit()


def delete_persona(
    db: Session,
    persona: models.Persona,
    user_id: int,
    motivo: str,
) -> None:
    active_references = (
        db.query(models.OrvIntegrante.id_orv_integrante)
        .filter_by(id_persona=persona.id_persona, activo=True)
        .first()
        or db.query(models.ParcelaTitular.id_parcela_titular)
        .filter_by(id_persona=persona.id_persona, activo=True)
        .first()
        or db.query(models.Acuerdo.id_acuerdo)
        .filter_by(id_persona_responsable=persona.id_persona, activo=True)
        .first()
        or db.query(models.PagoIndemnizacion.id_pago)
        .filter_by(id_persona_beneficiaria=persona.id_persona, activo=True)
        .first()
    )
    if active_references:
        raise HTTPException(
            status_code=409,
            detail="La persona tiene responsabilidades o vínculos activos",
        )

    set_audit_context(db, user_id)
    for relacion in (
        db.query(models.PersonaNucleo)
        .filter_by(id_persona=persona.id_persona, activo=True)
        .all()
    ):
        mark_inactive(relacion, user_id, motivo)
    mark_inactive(persona, user_id, motivo)
    db.commit()


def validate_titular_removal(
    db: Session,
    titular: models.ParcelaTitular,
) -> None:
    otros_titulares = (
        db.query(models.ParcelaTitular.id_parcela_titular)
        .filter(
            models.ParcelaTitular.id_parcela == titular.id_parcela,
            models.ParcelaTitular.id_parcela_titular
            != titular.id_parcela_titular,
            models.ParcelaTitular.activo.is_(True),
        )
        .first()
    )
    afectacion_activa = (
        db.query(models.Afectacion.id_afectacion)
        .filter_by(
            id_parcela=titular.id_parcela,
            tipo_afectacion="individual",
            activo=True,
        )
        .first()
    )
    if afectacion_activa and not otros_titulares:
        raise HTTPException(
            status_code=409,
            detail=(
                "No se puede retirar al último titular de una parcela "
                "con afectación individual activa"
            ),
        )
