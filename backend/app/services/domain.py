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
    require_agricultural_unit_access,
    require_assembly_access,
    require_fifonafe_access,
    require_indemnity_access,
    require_nucleus_access,
    require_parcel_access,
    require_payment_access,
    require_project_access,
    require_project_nucleus_access,
    require_ran_procedure_access,
)
from .common import apply_update, commit_or_conflict, mark_inactive, set_audit_context


T = TypeVar("T")


def require_catalog_option(
    db: Session,
    catalog_type: str,
    *,
    option_id: int | None = None,
    code: str | None = None,
    required: bool = False,
) -> models.CatalogoOperativo | None:
    query = db.query(models.CatalogoOperativo).filter(
        models.CatalogoOperativo.tipo_catalogo == catalog_type,
        models.CatalogoOperativo.activo.is_(True),
    )
    if option_id is not None:
        query = query.filter(models.CatalogoOperativo.id_catalogo_opcion == option_id)
    elif code:
        query = query.filter(models.CatalogoOperativo.codigo == code)
    elif not required:
        return None
    else:
        raise HTTPException(status_code=422, detail=f"Se requiere catálogo {catalog_type}")
    option = query.first()
    if option is None:
        raise HTTPException(
            status_code=422,
            detail=f"Opción activa inválida para el catálogo {catalog_type}",
        )
    return option


def _catalog_id(db: Session, catalog_type: str, code: str) -> int:
    return require_catalog_option(
        db, catalog_type, code=code, required=True
    ).id_catalogo_opcion


def create_catalog_option(
    db: Session, data: schemas.CatalogoOperativoCreate, user: models.Usuario
) -> models.CatalogoOperativo:
    entity = models.CatalogoOperativo(
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "El código de catálogo ya existe")


def update_catalog_option(
    db: Session,
    entity: models.CatalogoOperativo,
    data: schemas.CatalogoOperativoUpdate,
    user: models.Usuario,
) -> models.CatalogoOperativo:
    values = data.model_dump(exclude_unset=True, exclude={"observaciones", "motivo_baja"})
    set_audit_context(db, user.id_usuario)
    if values.pop("activo", None) is False and entity.activo:
        mark_inactive(entity, user.id_usuario, data.motivo_baja or "Desactivación administrativa")
    for key, value in values.items():
        setattr(entity, key, value)
    entity.actualizado_en = datetime.now(timezone.utc)
    entity.actualizado_por = user.id_usuario
    commit_or_conflict(db, "No fue posible actualizar el catálogo")
    db.refresh(entity)
    return entity


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
    option = require_catalog_option(
        db,
        "tipo_tenencia",
        option_id=data.id_tipo_tenencia,
        required=True,
    )
    values = data.model_dump(exclude={"observaciones", "id_tipo_tenencia"})
    entity = models.NucleoAgrario(
        **values,
        id_tipo_tenencia=option.id_catalogo_opcion,
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "El núcleo agrario ya existe")


def update_nucleus(
    db: Session,
    entity: models.NucleoAgrario,
    data: schemas.NucleoAgrarioUpdate,
    user: models.Usuario,
) -> models.NucleoAgrario:
    values = data.model_dump(exclude_unset=True, exclude={"observaciones"})
    if "id_tipo_tenencia" in values:
        option = require_catalog_option(
            db, "tipo_tenencia",
            option_id=values.pop("id_tipo_tenencia", None),
            required=True,
        )
        values["id_tipo_tenencia"] = option.id_catalogo_opcion
    set_audit_context(db, user.id_usuario)
    for key, value in values.items():
        setattr(entity, key, value)
    entity.actualizado_en = datetime.now(timezone.utc)
    entity.actualizado_por = user.id_usuario
    commit_or_conflict(db, "El núcleo o su tenencia no son válidos")
    db.refresh(entity)
    return entity


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
    residence = require_catalog_option(
        db, "residencia", option_id=data.id_residencia, required=False
    )
    record = models.ProyectoNucleo(
        id_proyecto=project_id,
        id_nucleo=data.id_nucleo,
        id_residencia=residence.id_catalogo_opcion if residence else None,
        total_cops_planeados=data.total_cops_planeados,
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


def update_project_nucleus(
    db: Session,
    entity: models.ProyectoNucleo,
    data: schemas.ProyectoNucleoUpdate,
    user: models.Usuario,
) -> models.ProyectoNucleo:
    values = data.model_dump(exclude_unset=True, exclude={"observaciones"})
    if "id_residencia" in values:
        option = require_catalog_option(
            db, "residencia", option_id=values.pop("id_residencia"), required=False
        )
        values["id_residencia"] = option.id_catalogo_opcion if option else None
    set_audit_context(db, user.id_usuario)
    for key, value in values.items():
        setattr(entity, key, value)
    entity.actualizado_en = datetime.now(timezone.utc)
    entity.actualizado_por = user.id_usuario
    commit_or_conflict(db, "El expediente o su residencia no son válidos")
    db.refresh(entity)
    return entity


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


def create_responsible(
    db: Session,
    project_nucleus_id: int,
    data: schemas.ProyectoNucleoResponsableCreate,
    user: models.Usuario,
) -> models.ProyectoNucleoResponsable:
    require_project_nucleus_access(db, user, project_nucleus_id, mode="capture")
    set_audit_context(db, user.id_usuario)
    if data.es_principal:
        now = datetime.now(timezone.utc)
        db.query(models.ProyectoNucleoResponsable).filter(
            models.ProyectoNucleoResponsable.id_proyecto_nucleo == project_nucleus_id,
            models.ProyectoNucleoResponsable.activo.is_(True),
            models.ProyectoNucleoResponsable.es_principal.is_(True),
        ).update(
            {
                models.ProyectoNucleoResponsable.es_principal: False,
                models.ProyectoNucleoResponsable.actualizado_en: now,
                models.ProyectoNucleoResponsable.actualizado_por: user.id_usuario,
            },
            synchronize_session=False,
        )
    entity = models.ProyectoNucleoResponsable(
        id_proyecto_nucleo=project_nucleus_id,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "El responsable no es válido")


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
    state_id = data.id_estado_registral
    if state_id is not None:
        state_id = require_catalog_option(
            db, "estado_registral_orv", option_id=state_id, required=True
        ).id_catalogo_opcion
    values = data.model_dump(exclude={"observaciones", "id_estado_registral"})
    entity = models.Orv(
        id_nucleo=project_nucleus.id_nucleo,
        **values,
        id_estado_registral=state_id,
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "El ORV activo se duplica")


def update_orv(
    db: Session,
    entity: models.Orv,
    data: schemas.OrvUpdate,
    user: models.Usuario,
) -> models.Orv:
    values = data.model_dump(exclude_unset=True, exclude={"observaciones"})
    if "id_estado_registral" in values:
        option = require_catalog_option(
            db, "estado_registral_orv", option_id=values["id_estado_registral"], required=False
        )
        values["id_estado_registral"] = option.id_catalogo_opcion if option else None
    set_audit_context(db, user.id_usuario)
    for key, value in values.items():
        setattr(entity, key, value)
    entity.actualizado_en = datetime.now(timezone.utc)
    entity.actualizado_por = user.id_usuario
    commit_or_conflict(db, "El ORV o su estado registral no son válidos")
    db.refresh(entity)
    return entity


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
    if data.id_tipo_cop_operativo is not None:
        require_catalog_option(db, "tipo_cop_operativo", option_id=data.id_tipo_cop_operativo, required=True)
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
    type_option = require_catalog_option(
        db,
        "tipo_asamblea",
        option_id=data.id_tipo_asamblea,
        required=True,
    )
    context_option = require_catalog_option(
        db,
        "contexto_asamblea",
        option_id=data.id_contexto_asamblea,
        required=False,
    )
    cop_option = require_catalog_option(
        db, "tipo_cop_operativo", option_id=data.id_tipo_cop_operativo, required=False
    )
    values = data.model_dump(
        exclude={
            "observaciones", "convocatorias", "id_tipo_asamblea",
            "id_contexto_asamblea", "id_tipo_cop_operativo",
        }
    )
    entity = models.Asamblea(
        id_proyecto_nucleo=project_nucleus_id,
        **values,
        id_tipo_asamblea=type_option.id_catalogo_opcion,
        id_contexto_asamblea=(context_option.id_catalogo_opcion if context_option else None),
        id_tipo_cop_operativo=(cop_option.id_catalogo_opcion if cop_option else None),
        **_audit_values(user.id_usuario, data),
    )
    set_audit_context(db, user.id_usuario)
    db.add(entity)
    try:
        db.flush()
        for convocation in data.convocatorias:
            db.add(models.AsambleaConvocatoria(
                id_asamblea=entity.id_asamblea,
                **convocation.model_dump(exclude={"observaciones"}),
                **_audit_values(user.id_usuario, convocation),
            ))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="La asamblea, padrón o convocatorias no son válidos") from exc
    db.refresh(entity)
    return entity


def add_convocation(
    db: Session,
    assembly_id: int,
    data: schemas.AsambleaConvocatoriaCreate,
    user: models.Usuario,
) -> models.AsambleaConvocatoria:
    require_assembly_access(db, user, assembly_id, mode="capture")
    entity = models.AsambleaConvocatoria(
        id_asamblea=assembly_id,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "La convocatoria no es válida o repite ordinal")


def update_assembly(
    db: Session,
    entity: models.Asamblea,
    data: schemas.AsambleaUpdate,
    user: models.Usuario,
) -> models.Asamblea:
    values = data.model_dump(exclude_unset=True, exclude={"convocatorias", "observaciones"})
    if "id_tipo_asamblea" in values:
        option = require_catalog_option(
            db, "tipo_asamblea",
            option_id=values.pop("id_tipo_asamblea", None),
            required=True,
        )
        values["id_tipo_asamblea"] = option.id_catalogo_opcion
    if "id_contexto_asamblea" in values:
        option = require_catalog_option(
            db, "contexto_asamblea",
            option_id=values.pop("id_contexto_asamblea", None),
            required=False,
        )
        values["id_contexto_asamblea"] = option.id_catalogo_opcion if option else None
    if "id_tipo_cop_operativo" in values:
        option = require_catalog_option(db, "tipo_cop_operativo", option_id=values.pop("id_tipo_cop_operativo", None), required=False)
        values["id_tipo_cop_operativo"] = option.id_catalogo_opcion if option else None
    set_audit_context(db, user.id_usuario)
    for key, value in values.items():
        setattr(entity, key, value)
    entity.actualizado_en = datetime.now(timezone.utc)
    entity.actualizado_por = user.id_usuario
    commit_or_conflict(db, "La asamblea o su contexto no son válidos")
    db.refresh(entity)
    return entity


def create_ran_procedure(
    db: Session,
    data: schemas.TramiteRanCreate,
    user: models.Usuario,
) -> models.TramiteRan:
    id_pn: int | None = None
    id_nuc: int | None = None

    if data.id_asamblea is not None:
        asamblea = require_assembly_access(db, user, data.id_asamblea, mode="capture")
        id_pn = asamblea.id_proyecto_nucleo
        id_nuc = None
    elif data.id_convenio is not None:
        convenio = require_agreement_access(db, user, data.id_convenio, mode="capture")
        id_pn = convenio.id_proyecto_nucleo
        id_nuc = None
    elif data.id_orv is not None:
        orv = db.query(models.Orv).filter(
            models.Orv.id_orv == data.id_orv,
            models.Orv.activo.is_(True),
        ).first()
        if orv is None:
            raise HTTPException(status_code=404, detail="ORV no encontrado")
        require_nucleus_access(db, user, orv.id_nucleo, mode="capture")
        id_nuc = orv.id_nucleo
        id_pn = None
    else:
        raise HTTPException(status_code=422, detail="Se requiere un objetivo para el trámite RAN")

    set_audit_context(db, user.id_usuario)
    procedure = models.TramiteRan(
        id_proyecto_nucleo=id_pn,
        id_nucleo=id_nuc,
        **data.model_dump(exclude={"eventos", "observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    db.add(procedure)
    try:
        db.flush()
        for event in data.eventos:
            db.add(models.TramiteRanEvento(
                id_tramite_ran=procedure.id_tramite_ran,
                **event.model_dump(exclude={"observaciones"}),
                **_audit_values(user.id_usuario, event),
            ))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El trámite RAN o sus eventos no son válidos") from exc
    db.refresh(procedure)
    return procedure


def add_ran_event(
    db: Session,
    procedure: models.TramiteRan,
    data: schemas.TramiteRanEventoCreate,
    user: models.Usuario,
) -> models.TramiteRanEvento:
    require_ran_procedure_access(db, user, procedure.id_tramite_ran, mode="capture")
    entity = models.TramiteRanEvento(
        id_tramite_ran=procedure.id_tramite_ran,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "El evento RAN no es válido o repite ordinal")


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
        **data.model_dump(exclude={"observaciones", "comparecientes"}),
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
        db.flush()
        for compareciente in data.comparecientes:
            if compareciente.id_parcela_titular is not None:
                parcel_holder = db.query(models.ParcelaTitular).filter(
                    models.ParcelaTitular.id_parcela_titular == compareciente.id_parcela_titular,
                    models.ParcelaTitular.activo.is_(True),
                ).first()
                if parcel_holder is None or not db.query(models.AfectacionUnidadAgraria).join(
                    models.UnidadAgraria,
                    models.UnidadAgraria.id_unidad_agraria == models.AfectacionUnidadAgraria.id_unidad_agraria,
                ).join(models.Afectacion, models.Afectacion.id_afectacion == models.AfectacionUnidadAgraria.id_afectacion).filter(
                    models.AfectacionUnidadAgraria.id_afectacion == affectation.id_afectacion,
                    models.AfectacionUnidadAgraria.activo.is_(True),
                    models.UnidadAgraria.activo.is_(True),
                    models.UnidadAgraria.id_parcela == parcel_holder.id_parcela,
                ).first():
                    raise HTTPException(status_code=409, detail="La ParcelaTitular no corresponde a una unidad afectada por el convenio")
            db.add(models.ConvenioCompareciente(
                id_convenio=agreement.id_convenio,
                **compareciente.model_dump(exclude={"observaciones"}),
                **_audit_values(user.id_usuario, compareciente),
            ))
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


def add_agreement_compareciente(
    db: Session,
    agreement_id: int,
    data: schemas.ConvenioComparecienteCreate,
    user: models.Usuario,
) -> models.ConvenioCompareciente:
    agreement = require_agreement_access(db, user, agreement_id, mode="capture")
    entity = models.ConvenioCompareciente(
        id_convenio=agreement.id_convenio,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "El compareciente no es válido")


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
        **data.model_dump(exclude={"ids_afectacion", "eventos", "observaciones"}),
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
        for event in data.eventos:
            db.add(models.TramiteFifonafeEvento(
                id_tramite_fifonafe=procedure.id_tramite_fifonafe,
                **event.model_dump(exclude={"observaciones"}),
                **_audit_values(user.id_usuario, event),
            ))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="El trámite FIFONAFE o sus afectaciones no son válidos",
        ) from exc
    db.refresh(procedure)
    return procedure


def add_fifonafe_event(
    db: Session,
    procedure: models.TramiteFifonafe,
    data: schemas.TramiteFifonafeEventoCreate,
    user: models.Usuario,
) -> models.TramiteFifonafeEvento:
    require_project_nucleus_access(db, user, procedure.id_proyecto_nucleo, mode="capture")
    entity = models.TramiteFifonafeEvento(
        id_tramite_fifonafe=procedure.id_tramite_fifonafe,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "El evento FIFONAFE no es válido o repite ordinal")


def create_document_requirement(
    db: Session,
    project_nucleus_id: int,
    data: schemas.ExpedienteRequisitoCreate,
    user: models.Usuario,
) -> models.ExpedienteRequisito:
    require_project_nucleus_access(db, user, project_nucleus_id, mode="capture")
    entity = models.ExpedienteRequisito(
        id_proyecto_nucleo=project_nucleus_id,
        **data.model_dump(exclude={"observaciones"}),
        **_audit_values(user.id_usuario, data),
    )
    return _persist(db, entity, user.id_usuario, "El requisito documental no es válido o está duplicado")


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


def create_unidad_agraria(
    db: Session,
    nucleo_id: int,
    data: schemas.UnidadAgrariaCreate,
    user: models.Usuario,
) -> models.UnidadAgraria:
    require_nucleus_access(db, user, nucleo_id, mode="capture")
    entity = models.UnidadAgraria(
        id_nucleo=nucleo_id,
        **data.model_dump(exclude_unset=True),
        creado_por=user.id_usuario,
    )
    return _persist(db, entity, user.id_usuario, "La unidad agraria ya existe")


def create_unidad_agraria_for_project_nucleus(db: Session, project_nucleus_id: int, data: schemas.UnidadAgrariaCreate, user: models.Usuario) -> models.UnidadAgraria:
    pn = require_project_nucleus_access(db, user, project_nucleus_id, mode="capture")
    return create_unidad_agraria(db, pn.id_nucleo, data, user)


def add_unidad_agraria_titular(db: Session, unit_id: int, data: schemas.UnidadAgrariaTitularCreate, user: models.Usuario) -> models.UnidadAgrariaTitular:
    unit = require_agricultural_unit_access(db, user, unit_id, mode="capture")
    if data.id_parcela_titular is not None:
        holder = db.query(models.ParcelaTitular).join(models.Parcela).filter(
            models.ParcelaTitular.id_parcela_titular == data.id_parcela_titular,
            models.ParcelaTitular.activo.is_(True), models.Parcela.activo.is_(True),
        ).first()
        if holder is None or holder.parcela.id_nucleo != unit.id_nucleo or (unit.id_parcela is not None and holder.id_parcela != unit.id_parcela):
            raise HTTPException(status_code=409, detail="La titularidad no corresponde a la unidad agraria")
    entity = models.UnidadAgrariaTitular(id_unidad_agraria=unit.id_unidad_agraria, **data.model_dump(exclude={"observaciones"}), **_audit_values(user.id_usuario, data))
    return _persist(db, entity, user.id_usuario, "La titularidad de unidad no es válida")


def get_unidades_agrarias_by_nucleo(
    db: Session, nucleo_id: int, user: models.Usuario
) -> list[models.UnidadAgraria]:
    require_nucleus_access(db, user, nucleo_id, mode="read")
    return (
        db.query(models.UnidadAgraria)
        .filter(
            models.UnidadAgraria.id_nucleo == nucleo_id,
            models.UnidadAgraria.activo.is_(True),
        )
        .all()
    )


def update_unidad_agraria(
    db: Session, unidad_id: int, data: schemas.UnidadAgrariaUpdate, user: models.Usuario
) -> models.UnidadAgraria:
    entity = (
        db.query(models.UnidadAgraria)
        .filter(
            models.UnidadAgraria.id_unidad_agraria == unidad_id,
            models.UnidadAgraria.activo.is_(True),
        )
        .first()
    )
    if entity is None:
        raise HTTPException(status_code=404, detail="Unidad agraria no encontrada")
    require_nucleus_access(db, user, entity.id_nucleo, mode="capture")
    return _update(db, entity, data, user.id_usuario)


def delete_unidad_agraria(
    db: Session, unidad_id: int, motivo: str, user: models.Usuario
) -> None:
    entity = require_agricultural_unit_access(db, user, unidad_id, mode="capture")

    has_titular = (
        db.query(models.UnidadAgrariaTitular.id_unidad_titular)
        .filter(
            models.UnidadAgrariaTitular.id_unidad_agraria == unidad_id,
            models.UnidadAgrariaTitular.activo.is_(True),
        )
        .first()
    )
    if has_titular:
        raise HTTPException(
            status_code=409,
            detail="La unidad agraria tiene relaciones activas y no puede darse de baja",
        )

    has_afectacion_unidad = (
        db.query(models.AfectacionUnidadAgraria.id_afectacion_unidad)
        .filter(
            models.AfectacionUnidadAgraria.id_unidad_agraria == unidad_id,
            models.AfectacionUnidadAgraria.activo.is_(True),
        )
        .first()
    )
    if has_afectacion_unidad:
        raise HTTPException(
            status_code=409,
            detail="La unidad agraria tiene relaciones activas y no puede darse de baja",
        )

    logical_delete(db, entity, user.id_usuario, motivo)


def associate_afectacion_unidad_agraria(
    db: Session,
    afectacion_id: int,
    data: schemas.AfectacionUnidadAgrariaCreate,
    user: models.Usuario,
) -> models.AfectacionUnidadAgraria:
    require_affectation_access(db, user, afectacion_id, mode="capture")

    afectacion = (
        db.query(models.Afectacion)
        .filter(
            models.Afectacion.id_afectacion == afectacion_id,
            models.Afectacion.activo.is_(True),
        )
        .first()
    )
    if not afectacion:
        raise HTTPException(status_code=404, detail="Afectación no encontrada")

    unidad = (
        db.query(models.UnidadAgraria)
        .filter(
            models.UnidadAgraria.id_unidad_agraria == data.id_unidad_agraria,
            models.UnidadAgraria.activo.is_(True),
        )
        .first()
    )
    if not unidad:
        raise HTTPException(status_code=404, detail="Unidad agraria no encontrada")

    # Validate nucleus match
    proyecto_nucleo = (
        db.query(models.ProyectoNucleo)
        .filter(models.ProyectoNucleo.id_proyecto_nucleo == afectacion.id_proyecto_nucleo)
        .first()
    )
    if proyecto_nucleo.id_nucleo != unidad.id_nucleo:
        raise HTTPException(
            status_code=409,
            detail="La unidad agraria pertenece a un núcleo diferente al de la afectación",
        )

    # Check for duplicate association
    existing = (
        db.query(models.AfectacionUnidadAgraria)
        .filter(
            models.AfectacionUnidadAgraria.id_afectacion == afectacion_id,
            models.AfectacionUnidadAgraria.id_unidad_agraria == data.id_unidad_agraria,
            models.AfectacionUnidadAgraria.activo.is_(True),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="La asociación ya existe")

    entity = models.AfectacionUnidadAgraria(
        id_afectacion=afectacion_id,
        **data.model_dump(exclude_unset=True),
        creado_por=user.id_usuario,
    )
    set_audit_context(db, user.id_usuario)
    db.add(entity)
    commit_or_conflict(db, "Conflicto de integridad")
    db.refresh(entity)
    return entity


def get_unidades_agrarias_by_afectacion(
    db: Session, afectacion_id: int, user: models.Usuario
) -> list[models.AfectacionUnidadAgraria]:
    require_affectation_access(db, user, afectacion_id, mode="read")
    return (
        db.query(models.AfectacionUnidadAgraria)
        .filter(
            models.AfectacionUnidadAgraria.id_afectacion == afectacion_id,
            models.AfectacionUnidadAgraria.activo.is_(True),
        )
        .all()
    )
