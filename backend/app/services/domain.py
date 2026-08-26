"""Transactional services for the target administrative domain."""

from datetime import datetime, timezone
from typing import Any, TypeVar

from fastapi import HTTPException
from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from .. import models, schemas
from .access import (
    require_affectation_access,
    require_agreement_access,
    require_assembly_access,
    require_fifonafe_access,
    require_indemnity_access,
    require_nucleus_access,
    require_parcel_access,
    require_payment_access,
    require_project_access,
    require_project_nucleus_access,
)
from .common import apply_update, commit_or_conflict, mark_inactive, set_audit_context


T = TypeVar("T")


def _audit_values(user_id: int, data: schemas.BaseModel | None = None) -> dict[str, Any]:
    values = {"creado_por": user_id}
    if data is not None and hasattr(data, "observaciones"):
        values["observaciones"] = data.observaciones
    return values


def _persist(db: Session, entity: T, user_id: int, detail: str) -> T:
    set_audit_context(db, user_id)
    db.add(entity)
    commit_or_conflict(db, detail)
    db.refresh(entity)
    return entity


def _update(db: Session, entity: T, data: schemas.BaseModel, user_id: int) -> T:
    set_audit_context(db, user_id)
    apply_update(entity, data, user_id)
    commit_or_conflict(db)
    db.refresh(entity)
    return entity


def logical_delete(db: Session, entity: Any, user_id: int, motivo: str) -> None:
    set_audit_context(db, user_id)
    mark_inactive(entity, user_id, motivo)
    commit_or_conflict(db, "No es posible dar de baja el recurso")


def create_project(
    db: Session, data: schemas.ProyectoCreate, user: models.Usuario
) -> models.Proyecto:
    entity = models.Proyecto(
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "La clave de proyecto ya existe")


def create_nucleus(
    db: Session, data: schemas.NucleoAgrarioCreate, user: models.Usuario
) -> models.NucleoAgrario:
    entity = models.NucleoAgrario(
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "El núcleo agrario ya existe")


def update_nucleus_geometry(
    db: Session,
    nucleus: models.NucleoAgrario,
    data: schemas.GeometriaPoligonoUpdate,
    user: models.Usuario,
) -> models.NucleoAgrario:
    set_audit_context(db, user.id_usuario)
    nucleus.geometria_poligono = (
        WKTElement(data.geometria_wkt, srid=4326)
        if data.geometria_wkt
        else None
    )
    nucleus.fuente_geometria = data.fuente_geometria
    nucleus.fecha_fuente_geometria = data.fecha_fuente_geometria
    nucleus.actualizado_en = datetime.now(timezone.utc)
    nucleus.actualizado_por = user.id_usuario
    commit_or_conflict(db, "La geometría del núcleo no es válida")
    db.refresh(nucleus)
    return nucleus


def create_project_nucleus(
    db: Session,
    project_id: int,
    data: schemas.ProyectoNucleoCreate,
    user: models.Usuario,
) -> models.ProyectoNucleo:
    require_project_access(db, user, project_id, mode="capture")
    nucleus = db.query(models.NucleoAgrario).filter(
        models.NucleoAgrario.id_nucleo == data.id_nucleo,
        models.NucleoAgrario.activo.is_(True),
    ).first()
    if nucleus is None:
        raise HTTPException(status_code=404, detail="Núcleo no encontrado")
    set_audit_context(db, user.id_usuario)
    record = models.ProyectoNucleo(
        id_proyecto=project_id,
        id_nucleo=data.id_nucleo,
        residencia=data.residencia,
        responsable_nombre=data.responsable_nombre,
        contacto=data.contacto,
        **_audit_values(user.id_usuario, data),
    )
    db.add(record)
    try:
        db.flush()
        for reference in data.referencias:
            db.add(
                models.ProyectoNucleoReferencia(
                    id_proyecto_nucleo=record.id_proyecto_nucleo,
                    **reference.model_dump(exclude={"observaciones"}),
                    **_audit_values(user.id_usuario, reference),
                )
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe un ProyectoNucleo activo o sus referencias se duplican",
        ) from exc
    db.refresh(record)
    return record


def add_reference(
    db: Session,
    project_nucleus_id: int,
    data: schemas.ProyectoNucleoReferenciaCreate,
    user: models.Usuario,
) -> models.ProyectoNucleoReferencia:
    require_project_nucleus_access(db, user, project_nucleus_id, mode="capture")
    set_audit_context(db, user.id_usuario)
    if data.es_principal:
        now = datetime.now(timezone.utc)
        db.query(models.ProyectoNucleoReferencia).filter(
            models.ProyectoNucleoReferencia.id_proyecto_nucleo
            == project_nucleus_id,
            models.ProyectoNucleoReferencia.tipo_referencia
            == data.tipo_referencia,
            models.ProyectoNucleoReferencia.es_principal.is_(True),
            models.ProyectoNucleoReferencia.activo.is_(True),
        ).update(
            {
                models.ProyectoNucleoReferencia.es_principal: False,
                models.ProyectoNucleoReferencia.actualizado_en: now,
                models.ProyectoNucleoReferencia.actualizado_por: user.id_usuario,
            },
            synchronize_session=False,
        )
    reference = models.ProyectoNucleoReferencia(
        id_proyecto_nucleo=project_nucleus_id,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    db.add(reference)
    commit_or_conflict(db, "La referencia activa ya existe")
    db.refresh(reference)
    return reference


def create_person(
    db: Session, data: schemas.PersonaCreate, user: models.Usuario
) -> models.Persona:
    entity = models.Persona(
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "La persona ya existe")


def create_orv(
    db: Session,
    project_nucleus_id: int,
    data: schemas.OrvCreate,
    user: models.Usuario,
) -> models.Orv:
    project_nucleus = require_project_nucleus_access(
        db, user, project_nucleus_id, mode="capture"
    )
    entity = models.Orv(
        id_nucleo=project_nucleus.id_nucleo,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "El ORV activo se duplica")


def add_orv_member(
    db: Session,
    orv: models.Orv,
    data: schemas.OrvIntegranteCreate,
    user: models.Usuario,
) -> models.OrvIntegrante:
    person = db.query(models.Persona).filter(
        models.Persona.id_persona == data.id_persona,
        models.Persona.activo.is_(True),
    ).first()
    if person is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    entity = models.OrvIntegrante(
        id_orv=orv.id_orv,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "El integrante de ORV ya existe")


def create_register(
    db: Session,
    project_nucleus_id: int,
    data: schemas.PadronHistorialCreate,
    user: models.Usuario,
) -> models.PadronHistorial:
    project_nucleus = require_project_nucleus_access(
        db, user, project_nucleus_id, mode="capture"
    )
    entity = models.PadronHistorial(
        id_nucleo=project_nucleus.id_nucleo,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "El padrón ya existe")


def create_parcel(
    db: Session,
    project_nucleus_id: int,
    data: schemas.ParcelaCreate,
    user: models.Usuario,
) -> models.Parcela:
    project_nucleus = require_project_nucleus_access(
        db, user, project_nucleus_id, mode="capture"
    )
    entity = models.Parcela(
        id_nucleo=project_nucleus.id_nucleo,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "La parcela ya existe")


def update_parcel_geometry(
    db: Session,
    parcel: models.Parcela,
    data: schemas.GeometriaPoligonoUpdate,
    user: models.Usuario,
) -> models.Parcela:
    set_audit_context(db, user.id_usuario)
    parcel.geometria_poligono = (
        WKTElement(data.geometria_wkt, srid=4326)
        if data.geometria_wkt
        else None
    )
    parcel.fuente_geometria = data.fuente_geometria
    parcel.fecha_fuente_geometria = data.fecha_fuente_geometria
    parcel.actualizado_en = datetime.now(timezone.utc)
    parcel.actualizado_por = user.id_usuario
    commit_or_conflict(db, "La geometría de parcela no es válida")
    db.refresh(parcel)
    return parcel


def add_parcel_holder(
    db: Session,
    parcel: models.Parcela,
    data: schemas.ParcelaTitularCreate,
    user: models.Usuario,
) -> models.ParcelaTitular:
    person = db.query(models.Persona).filter(
        models.Persona.id_persona == data.id_persona,
        models.Persona.activo.is_(True),
    ).first()
    if person is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    entity = models.ParcelaTitular(
        id_parcela=parcel.id_parcela,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "La titularidad ya existe")


def create_activity(
    db: Session,
    project_nucleus_id: int,
    data: schemas.ActividadCampoCreate,
    user: models.Usuario,
) -> models.ActividadCampo:
    require_project_nucleus_access(db, user, project_nucleus_id, mode="capture")
    entity = models.ActividadCampo(
        id_proyecto_nucleo=project_nucleus_id,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "Actividad inválida")


def create_affectation(
    db: Session,
    project_nucleus_id: int,
    data: schemas.AfectacionCreate,
    user: models.Usuario,
) -> models.Afectacion:
    require_project_nucleus_access(db, user, project_nucleus_id, mode="capture")
    entity = models.Afectacion(
        id_proyecto_nucleo=project_nucleus_id,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(
        db,
        entity,
        user.id_usuario,
        "La afectación no cumple el ámbito o la parcela pertenece a otro núcleo",
    )


def create_assembly(
    db: Session,
    project_nucleus_id: int,
    data: schemas.AsambleaCreate,
    user: models.Usuario,
) -> models.Asamblea:
    require_project_nucleus_access(db, user, project_nucleus_id, mode="capture")
    entity = models.Asamblea(
        id_proyecto_nucleo=project_nucleus_id,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(
        db, entity, user.id_usuario, "La asamblea o su padrón no son válidos"
    )


def create_agreement(
    db: Session,
    initial_affectation_id: int,
    data: schemas.ConvenioCreate,
    user: models.Usuario,
) -> models.Convenio:
    affectation = require_affectation_access(
        db, user, initial_affectation_id, mode="capture"
    )
    set_audit_context(db, user.id_usuario)
    agreement = models.Convenio(
        id_proyecto_nucleo=affectation.id_proyecto_nucleo,
        ambito=affectation.tipo_afectacion,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    db.add(agreement)
    try:
        db.flush()
        db.add(
            models.ConvenioAfectacion(
                id_convenio=agreement.id_convenio,
                id_afectacion=affectation.id_afectacion,
                rol="principal",
                creado_por=user.id_usuario,
            )
        )
        if data.id_convenio_padre is not None:
            parent = require_agreement_access(
                db, user, data.id_convenio_padre, mode="capture"
            )
            if (
                parent.id_proyecto_nucleo != affectation.id_proyecto_nucleo
                or parent.ambito != affectation.tipo_afectacion
            ):
                raise HTTPException(
                    status_code=409,
                    detail="El convenio padre no comparte ProyectoNucleo y ámbito",
                )
            parent_links = db.query(models.ConvenioAfectacion).filter(
                models.ConvenioAfectacion.id_convenio == parent.id_convenio,
                models.ConvenioAfectacion.activo.is_(True),
                models.ConvenioAfectacion.id_afectacion
                != initial_affectation_id,
            ).all()
            for link in parent_links:
                db.add(
                    models.ConvenioAfectacion(
                        id_convenio=agreement.id_convenio,
                        id_afectacion=link.id_afectacion,
                        rol="adicional",
                        creado_por=user.id_usuario,
                    )
                )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="El convenio y su afectación principal no son válidos",
        ) from exc
    db.refresh(agreement)
    return agreement


def add_agreement_affectation(
    db: Session,
    agreement_id: int,
    affectation_id: int,
    user: models.Usuario,
) -> models.ConvenioAfectacion:
    agreement = require_agreement_access(db, user, agreement_id, mode="capture")
    require_affectation_access(db, user, affectation_id, mode="capture")
    entity = models.ConvenioAfectacion(
        id_convenio=agreement.id_convenio,
        id_afectacion=affectation_id,
        rol="adicional",
        creado_por=user.id_usuario,
    )
    return _persist(
        db,
        entity,
        user.id_usuario,
        "La afectación adicional no comparte ProyectoNucleo/ámbito o ya está asociada",
    )


def create_fifonafe(
    db: Session,
    project_nucleus_id: int,
    data: schemas.TramiteFifonafeCreate,
    user: models.Usuario,
) -> models.TramiteFifonafe:
    require_project_nucleus_access(db, user, project_nucleus_id, mode="capture")
    affectations = [
        require_affectation_access(db, user, item, mode="capture")
        for item in data.ids_afectacion
    ]
    scopes = {
        (item.id_proyecto_nucleo, item.tipo_afectacion) for item in affectations
    }
    if len(scopes) != 1 or next(iter(scopes))[0] != project_nucleus_id:
        raise HTTPException(
            status_code=409,
            detail="Todas las afectaciones FIFONAFE deben compartir ProyectoNucleo y ámbito",
        )
    ambito = affectations[0].tipo_afectacion
    set_audit_context(db, user.id_usuario)
    procedure = models.TramiteFifonafe(
        id_proyecto_nucleo=project_nucleus_id,
        ambito=ambito,
        **data.model_dump(exclude={"ids_afectacion", "observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    db.add(procedure)
    try:
        db.flush()
        for affectation in affectations:
            db.add(
                models.TramiteFifonafeAfectacion(
                    id_tramite_fifonafe=procedure.id_tramite_fifonafe,
                    id_afectacion=affectation.id_afectacion,
                    creado_por=user.id_usuario,
                )
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="El trámite FIFONAFE o sus afectaciones no son válidos",
        ) from exc
    db.refresh(procedure)
    return procedure


def add_fifonafe_affectation(
    db: Session,
    procedure_id: int,
    affectation_id: int,
    user: models.Usuario,
) -> models.TramiteFifonafeAfectacion:
    procedure = require_fifonafe_access(db, user, procedure_id, mode="capture")
    require_affectation_access(db, user, affectation_id, mode="capture")
    entity = models.TramiteFifonafeAfectacion(
        id_tramite_fifonafe=procedure.id_tramite_fifonafe,
        id_afectacion=affectation_id,
        creado_por=user.id_usuario,
    )
    return _persist(
        db,
        entity,
        user.id_usuario,
        "La afectación no comparte ProyectoNucleo/ámbito o ya está asociada",
    )


def create_indemnity(
    db: Session,
    affectation_id: int,
    data: schemas.IndemnizacionCreate,
    user: models.Usuario,
) -> models.Indemnizacion:
    require_affectation_access(db, user, affectation_id, mode="capture")
    entity = models.Indemnizacion(
        id_afectacion=affectation_id,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(
        db,
        entity,
        user.id_usuario,
        "La afectación ya tiene una indemnización activa",
    )


def create_payment(
    db: Session,
    indemnity_id: int,
    data: schemas.PagoCreate,
    user: models.Usuario,
) -> models.Pago:
    require_indemnity_access(db, user, indemnity_id, mode="capture")
    entity = models.Pago(
        id_indemnizacion=indemnity_id,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "El pago no es válido")


def create_trace(
    db: Session,
    project_id: int,
    data: schemas.TrazoProyectoCreate,
    user: models.Usuario,
) -> models.TrazoProyecto:
    require_project_access(db, user, project_id, mode="gis")
    values = data.model_dump(exclude={"geometria_wkt", "observaciones"})
    entity = models.TrazoProyecto(
        id_proyecto=project_id,
        geometria_linea=WKTElement(data.geometria_wkt, srid=4326),
        **values,
        **_audit_values(user.id_usuario, data),
    )
    return _persist(
        db,
        entity,
        user.id_usuario,
        "El trazo no es MULTILINESTRING 4326 válido o ya existe una versión activa",
    )


def assign_user_to_project(
    db: Session,
    project_id: int,
    data: schemas.UsuarioProyectoCreate,
    user: models.Usuario,
) -> models.UsuarioProyecto:
    require_project_access(db, user, project_id)
    target = db.query(models.Usuario).filter(
        models.Usuario.id_usuario == data.id_usuario,
        models.Usuario.activo.is_(True),
    ).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    entity = models.UsuarioProyecto(
        id_usuario=data.id_usuario,
        id_proyecto=project_id,
        asignado_por=user.id_usuario,
        creado_por=user.id_usuario,
    )
    return _persist(db, entity, user.id_usuario, "La asignación ya existe")


def update_entity(
    db: Session,
    entity: T,
    data: schemas.BaseModel,
    user: models.Usuario,
) -> T:
    return _update(db, entity, data, user.id_usuario)
