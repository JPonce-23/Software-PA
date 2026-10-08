"""Project-scoped authorization resolved through canonical relationships."""

from typing import Literal

from fastapi import HTTPException
from sqlalchemy import and_, exists, false, func, or_, select, text, union
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql import ColumnElement, Select

from .. import models


AccessMode = Literal["read", "capture", "gis"]


def _person_project_statements(person_id: int | ColumnElement[int]) -> list[Select]:
    """Canonical relationship paths, also usable with a correlated person id."""
    pn, nucleus = models.ProyectoNucleo, models.NucleoAgrario

    def in_nucleus(relation, parent, parent_id, nucleus_id):
        return select(pn.id_proyecto).select_from(relation).join(
            parent, parent_id
        ).join(nucleus, nucleus.id_nucleo == nucleus_id).join(
            pn, pn.id_nucleo == nucleus.id_nucleo
        ).where(relation.activo.is_(True), parent.activo.is_(True),
                nucleus.activo.is_(True), pn.activo.is_(True))

    member, orv = models.OrvIntegrante, models.Orv
    holder, parcel = models.ParcelaTitular, models.Parcela
    titular, unit = models.UnidadAgrariaTitular, models.UnidadAgraria
    compareciente, agreement = models.ConvenioCompareciente, models.Convenio
    interviniente, procedure = models.TramiteFifonafeInterviniente, models.TramiteFifonafe
    payment, indemnity, affectation = models.Pago, models.Indemnizacion, models.Afectacion
    statements = [
        in_nucleus(member, orv, orv.id_orv == member.id_orv, orv.id_nucleo).where(member.id_persona == person_id),
        in_nucleus(holder, parcel, parcel.id_parcela == holder.id_parcela, parcel.id_nucleo).where(holder.id_persona == person_id),
        in_nucleus(titular, unit, unit.id_unidad_agraria == titular.id_unidad_agraria, unit.id_nucleo).where(titular.id_persona == person_id),
        in_nucleus(titular, unit, unit.id_unidad_agraria == titular.id_unidad_agraria, unit.id_nucleo).join(
            holder, holder.id_parcela_titular == titular.id_parcela_titular
        ).join(parcel, parcel.id_parcela == holder.id_parcela).where(
            holder.id_persona == person_id, holder.activo.is_(True), parcel.activo.is_(True)
        ),
        select(pn.id_proyecto).select_from(compareciente).join(
            agreement, agreement.id_convenio == compareciente.id_convenio
        ).join(pn, pn.id_proyecto_nucleo == agreement.id_proyecto_nucleo).where(
            compareciente.id_persona == person_id, compareciente.activo.is_(True),
            agreement.activo.is_(True), pn.activo.is_(True)
        ),
        select(pn.id_proyecto).select_from(interviniente).join(
            procedure, procedure.id_tramite_fifonafe == interviniente.id_tramite_fifonafe
        ).join(pn, pn.id_proyecto_nucleo == procedure.id_proyecto_nucleo).where(
            interviniente.id_persona == person_id, interviniente.activo.is_(True),
            procedure.activo.is_(True), pn.activo.is_(True)
        ),
        select(pn.id_proyecto).select_from(payment).join(
            indemnity, indemnity.id_indemnizacion == payment.id_indemnizacion
        ).join(affectation, affectation.id_afectacion == indemnity.id_afectacion).join(
            pn, pn.id_proyecto_nucleo == affectation.id_proyecto_nucleo
        ).where(payment.id_persona_beneficiaria == person_id, payment.activo.is_(True),
                indemnity.activo.is_(True), affectation.activo.is_(True), pn.activo.is_(True)),
    ]
    return statements


def person_project_ids(db: Session, person_id: int) -> set[int]:
    """Follow actual active business links, including indirect unit holders.

    Inactive projects remain in the set: editing shared identity must not
    silently bypass their scope. authorized_project_ids excludes them.
    """
    return set(db.execute(union(*_person_project_statements(person_id))).scalars())


def _person_orphan_access_clause(
    user: models.Usuario, authorized_projects_exist: bool | ColumnElement[bool],
) -> ColumnElement[bool]:
    """Creator fallback; callers must additionally require no derived projects."""
    if user.rol != "operador":
        return false()
    return and_(
        authorized_projects_exist,
        models.Persona.creado_por == user.id_usuario,
        func.fn_persona_tiene_relaciones_activas(models.Persona.id_persona).is_(False),
    )


def filter_persons_by_read_access(query: Query, db: Session, user: models.Usuario) -> Query:
    """Apply the existing read policy before ordering or paginating a projection."""
    query = query.filter(models.Persona.activo.is_(True))
    if user.rol == "admin":
        return query
    if not _role_allows(user, "read"):
        return query.filter(false())
    authorized = authorized_project_ids(db, user)
    statements = [statement.correlate(models.Persona) for statement in
                  _person_project_statements(models.Persona.id_persona)]
    related = or_(*(statement.exists() for statement in statements))
    readable = or_(*(statement.where(
        models.ProyectoNucleo.id_proyecto.in_(authorized)
    ).exists() for statement in statements))
    orphan = and_(~related, _person_orphan_access_clause(user, authorized.exists()))
    return query.filter(or_(readable, orphan))


def lock_person_relations(db: Session, person_id: int) -> None:
    # Existing migration 018 relation triggers use this exact transaction lock.
    db.execute(text("SELECT pg_advisory_xact_lock("
                    "hashtextextended('software-pa:persona-relaciones:' || :id, 0))"),
               {"id": str(person_id)})


def require_person_access(
    db: Session, user: models.Usuario, person_id: int, *,
    mode: Literal["read", "capture", "link"] = "read", lock: bool = False,
) -> models.Persona:
    if lock:
        lock_person_relations(db, person_id)
    query = db.query(models.Persona).filter(
        models.Persona.id_persona == person_id, models.Persona.activo.is_(True)
    )
    if lock:
        query = query.with_for_update(key_share=True).populate_existing()
    person = query.first()
    if person is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    if user.rol == "admin":
        return person
    allowed_role = "read" if mode == "read" else "capture"
    denied = HTTPException(status_code=403, detail="Persona fuera del alcance autorizado")
    if not _role_allows(user, allowed_role):
        raise denied
    related = person_project_ids(db, person_id)
    authorized = set(db.execute(authorized_project_ids(db, user)).scalars())
    if related:
        if (mode == "capture" and related <= authorized) or (
            mode != "capture" and related & authorized
        ):
            return person
        raise denied
    # A disconnected active business reference is not an orphan. Do not turn
    # an inactive parent/project into permission through the creator fallback.
    orphan = db.query(models.Persona.id_persona).filter(
        models.Persona.id_persona == person_id,
        _person_orphan_access_clause(user, bool(authorized)),
    ).first()
    if orphan is not None:
        return person
    raise denied


def _forbidden() -> HTTPException:
    return HTTPException(status_code=403, detail="Proyecto fuera del alcance autorizado")


def authorized_project_ids(db: Session, user: models.Usuario) -> select:
    if user.rol == "admin":
        return select(models.Proyecto.id_proyecto).where(models.Proyecto.activo.is_(True))
    return (
        select(models.UsuarioProyecto.id_proyecto)
        .join(
            models.Proyecto,
            models.Proyecto.id_proyecto == models.UsuarioProyecto.id_proyecto,
        )
        .where(
            models.UsuarioProyecto.id_usuario == user.id_usuario,
            models.UsuarioProyecto.activo.is_(True),
            models.Proyecto.activo.is_(True),
        )
    )


def _role_allows(user: models.Usuario, mode: AccessMode) -> bool:
    if user.rol == "admin":
        return True
    if mode == "read":
        return user.rol in {"operador", "visualizador", "geografo"}
    if mode == "capture":
        return user.rol == "operador"
    return user.rol == "geografo"


def require_project_access(
    db: Session,
    user: models.Usuario,
    project_id: int,
    *,
    mode: AccessMode = "read",
    lock: bool = False,
) -> models.Proyecto:
    if not _role_allows(user, mode):
        raise _forbidden()
    query = db.query(models.Proyecto).filter(
        models.Proyecto.id_proyecto == project_id,
        models.Proyecto.activo.is_(True),
    )
    if user.rol != "admin":
        query = query.filter(
            exists().where(
                models.UsuarioProyecto.id_usuario == user.id_usuario,
                models.UsuarioProyecto.id_proyecto == models.Proyecto.id_proyecto,
                models.UsuarioProyecto.activo.is_(True),
            )
        )
    if lock:
        # SHARE prevents deactivation until commit, while allowing assignments
        # for different users to proceed concurrently in the same project.
        query = query.with_for_update(read=True).populate_existing()
    project = query.first()
    if project is None:
        raise _forbidden()
    return project


def filter_projects_by_user(
    query: Query,
    db: Session,
    user: models.Usuario,
) -> Query:
    if user.rol == "admin":
        return query
    return query.filter(models.Proyecto.id_proyecto.in_(authorized_project_ids(db, user)))


def require_project_nucleus_access(
    db: Session,
    user: models.Usuario,
    project_nucleus_id: int,
    *,
    mode: AccessMode = "read",
) -> models.ProyectoNucleo:
    record = db.query(models.ProyectoNucleo).filter(
        models.ProyectoNucleo.id_proyecto_nucleo == project_nucleus_id,
        models.ProyectoNucleo.activo.is_(True),
    ).first()
    if record is None:
        raise HTTPException(status_code=404, detail="ProyectoNucleo no encontrado")
    require_project_access(db, user, record.id_proyecto, mode=mode)
    return record


def require_nucleus_access(
    db: Session,
    user: models.Usuario,
    nucleus_id: int,
    *,
    mode: AccessMode = "read",
) -> models.NucleoAgrario:
    nucleus = db.query(models.NucleoAgrario).filter(
        models.NucleoAgrario.id_nucleo == nucleus_id,
        models.NucleoAgrario.activo.is_(True),
    ).first()
    if nucleus is None:
        raise HTTPException(status_code=404, detail="Núcleo no encontrado")
    if user.rol == "admin":
        if not _role_allows(user, mode):
            raise _forbidden()
        return nucleus
    if not _role_allows(user, mode):
        raise _forbidden()
    allowed = db.query(models.ProyectoNucleo.id_proyecto_nucleo).filter(
        models.ProyectoNucleo.id_nucleo == nucleus_id,
        models.ProyectoNucleo.activo.is_(True),
        models.ProyectoNucleo.id_proyecto.in_(authorized_project_ids(db, user)),
    ).first()
    if allowed is None:
        raise _forbidden()
    return nucleus


def require_parcel_access(
    db: Session,
    user: models.Usuario,
    parcel_id: int,
    *,
    mode: AccessMode = "read",
) -> models.Parcela:
    parcel = db.query(models.Parcela).filter(
        models.Parcela.id_parcela == parcel_id,
        models.Parcela.activo.is_(True),
    ).first()
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")
    require_nucleus_access(db, user, parcel.id_nucleo, mode=mode)
    return parcel


def require_agricultural_unit_access(
    db: Session, user: models.Usuario, unit_id: int, *, mode: AccessMode = "read"
) -> models.UnidadAgraria:
    unit = db.query(models.UnidadAgraria).filter(
        models.UnidadAgraria.id_unidad_agraria == unit_id,
        models.UnidadAgraria.activo.is_(True),
    ).first()
    if unit is None:
        raise HTTPException(status_code=404, detail="Unidad agraria no encontrada")
    require_nucleus_access(db, user, unit.id_nucleo, mode=mode)
    return unit


def require_affectation_access(
    db: Session,
    user: models.Usuario,
    affectation_id: int,
    *,
    mode: AccessMode = "read",
) -> models.Afectacion:
    affectation = db.query(models.Afectacion).filter(
        models.Afectacion.id_afectacion == affectation_id,
        models.Afectacion.activo.is_(True),
    ).first()
    if affectation is None:
        raise HTTPException(status_code=404, detail="Afectación no encontrada")
    require_project_nucleus_access(
        db, user, affectation.id_proyecto_nucleo, mode=mode
    )
    return affectation


def require_assembly_access(
    db: Session,
    user: models.Usuario,
    assembly_id: int,
    *,
    mode: AccessMode = "read",
) -> models.Asamblea:
    assembly = db.query(models.Asamblea).filter(
        models.Asamblea.id_asamblea == assembly_id,
        models.Asamblea.activo.is_(True),
    ).first()
    if assembly is None:
        raise HTTPException(status_code=404, detail="Asamblea no encontrada")
    require_project_nucleus_access(db, user, assembly.id_proyecto_nucleo, mode=mode)
    return assembly


def require_agreement_access(
    db: Session,
    user: models.Usuario,
    agreement_id: int,
    *,
    mode: AccessMode = "read",
) -> models.Convenio:
    agreement = db.query(models.Convenio).filter(
        models.Convenio.id_convenio == agreement_id,
        models.Convenio.activo.is_(True),
    ).first()
    if agreement is None:
        raise HTTPException(status_code=404, detail="Convenio no encontrado")
    require_project_nucleus_access(db, user, agreement.id_proyecto_nucleo, mode=mode)
    return agreement


def require_fifonafe_access(
    db: Session,
    user: models.Usuario,
    procedure_id: int,
    *,
    mode: AccessMode = "read",
) -> models.TramiteFifonafe:
    procedure = db.query(models.TramiteFifonafe).filter(
        models.TramiteFifonafe.id_tramite_fifonafe == procedure_id,
        models.TramiteFifonafe.activo.is_(True),
    ).first()
    if procedure is None:
        raise HTTPException(status_code=404, detail="Trámite FIFONAFE no encontrado")
    require_project_nucleus_access(db, user, procedure.id_proyecto_nucleo, mode=mode)
    return procedure


def require_indemnity_access(
    db: Session,
    user: models.Usuario,
    indemnity_id: int,
    *,
    mode: AccessMode = "read",
) -> models.Indemnizacion:
    indemnity = db.query(models.Indemnizacion).filter(
        models.Indemnizacion.id_indemnizacion == indemnity_id,
        models.Indemnizacion.activo.is_(True),
    ).first()
    if indemnity is None:
        raise HTTPException(status_code=404, detail="Indemnización no encontrada")
    require_affectation_access(db, user, indemnity.id_afectacion, mode=mode)
    return indemnity


def require_payment_access(
    db: Session,
    user: models.Usuario,
    payment_id: int,
    *,
    mode: AccessMode = "read",
) -> models.Pago:
    payment = db.query(models.Pago).filter(
        models.Pago.id_pago == payment_id,
        models.Pago.activo.is_(True),
    ).first()
    if payment is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    require_indemnity_access(db, user, payment.id_indemnizacion, mode=mode)
    return payment


def _project_ids_for_ran(
    db: Session,
    ran: models.TramiteRan | None,
) -> list[int]:
    if ran is None or not ran.activo:
        return []
    if ran.id_proyecto_nucleo is not None:
        query = db.query(models.ProyectoNucleo.id_proyecto).filter(
            models.ProyectoNucleo.id_proyecto_nucleo == ran.id_proyecto_nucleo,
            models.ProyectoNucleo.activo.is_(True),
        )
    elif ran.id_nucleo is not None:
        query = db.query(models.ProyectoNucleo.id_proyecto).filter(
            models.ProyectoNucleo.id_nucleo == ran.id_nucleo,
            models.ProyectoNucleo.activo.is_(True),
        )
    else:
        return []
    return [row[0] for row in query.distinct().all()]


def project_ids_for_document_target(
    db: Session,
    entity_type: str,
    entity_id: int,
) -> list[int]:
    if entity_type == "proyecto_nucleo":
        query = db.query(models.ProyectoNucleo.id_proyecto).filter(
            models.ProyectoNucleo.id_proyecto_nucleo == entity_id,
            models.ProyectoNucleo.activo.is_(True),
        )
    elif entity_type in {
        "nucleo_agrario",
        "orv",
        "padron_historial",
        "parcela",
        "unidad_agraria",
    }:
        nucleus_column, model, pk = {
            "nucleo_agrario": (
                models.NucleoAgrario.id_nucleo,
                models.NucleoAgrario,
                models.NucleoAgrario.id_nucleo,
            ),
            "orv": (models.Orv.id_nucleo, models.Orv, models.Orv.id_orv),
            "padron_historial": (
                models.PadronHistorial.id_nucleo,
                models.PadronHistorial,
                models.PadronHistorial.id_padron,
            ),
            "parcela": (
                models.Parcela.id_nucleo,
                models.Parcela,
                models.Parcela.id_parcela,
            ),
            "unidad_agraria": (
                models.UnidadAgraria.id_nucleo,
                models.UnidadAgraria,
                models.UnidadAgraria.id_unidad_agraria,
            ),
        }[entity_type]
        query = db.query(models.ProyectoNucleo.id_proyecto).join(
            model, nucleus_column == models.ProyectoNucleo.id_nucleo
        ).filter(
            pk == entity_id,
            model.activo.is_(True),
            models.ProyectoNucleo.activo.is_(True),
        )
    elif entity_type == "parcela_titular":
        query = (
            db.query(models.ProyectoNucleo.id_proyecto)
            .join(
                models.Parcela,
                models.Parcela.id_nucleo == models.ProyectoNucleo.id_nucleo,
            )
            .join(
                models.ParcelaTitular,
                models.ParcelaTitular.id_parcela == models.Parcela.id_parcela,
            )
            .filter(
                models.ParcelaTitular.id_parcela_titular == entity_id,
                models.ParcelaTitular.activo.is_(True),
                models.Parcela.activo.is_(True),
                models.ProyectoNucleo.activo.is_(True),
            )
        )
    elif entity_type == "unidad_agraria_titular":
        query = (
            db.query(models.ProyectoNucleo.id_proyecto)
            .join(
                models.UnidadAgraria,
                models.UnidadAgraria.id_nucleo == models.ProyectoNucleo.id_nucleo,
            )
            .join(
                models.UnidadAgrariaTitular,
                models.UnidadAgrariaTitular.id_unidad_agraria
                == models.UnidadAgraria.id_unidad_agraria,
            )
            .filter(
                models.UnidadAgrariaTitular.id_unidad_titular == entity_id,
                models.UnidadAgrariaTitular.activo.is_(True),
                models.UnidadAgraria.activo.is_(True),
                models.ProyectoNucleo.activo.is_(True),
            )
        )
    elif entity_type in {
        "afectacion",
        "actividad_campo",
        "asamblea",
        "convenio",
        "tramite_fifonafe",
        "expediente_requisito",
    }:
        model, pk = {
            "afectacion": (models.Afectacion, models.Afectacion.id_afectacion),
            "actividad_campo": (models.ActividadCampo, models.ActividadCampo.id_actividad),
            "asamblea": (models.Asamblea, models.Asamblea.id_asamblea),
            "convenio": (models.Convenio, models.Convenio.id_convenio),
            "tramite_fifonafe": (
                models.TramiteFifonafe,
                models.TramiteFifonafe.id_tramite_fifonafe,
            ),
            "expediente_requisito": (
                models.ExpedienteRequisito,
                models.ExpedienteRequisito.id_expediente_requisito,
            ),
        }[entity_type]
        query = db.query(models.ProyectoNucleo.id_proyecto).join(
            model,
            model.id_proyecto_nucleo == models.ProyectoNucleo.id_proyecto_nucleo,
        ).filter(
            pk == entity_id,
            model.activo.is_(True),
            models.ProyectoNucleo.activo.is_(True),
        )
    elif entity_type == "afectacion_unidad_agraria":
        query = (
            db.query(models.ProyectoNucleo.id_proyecto)
            .join(
                models.Afectacion,
                models.Afectacion.id_proyecto_nucleo
                == models.ProyectoNucleo.id_proyecto_nucleo,
            )
            .join(
                models.AfectacionUnidadAgraria,
                models.AfectacionUnidadAgraria.id_afectacion
                == models.Afectacion.id_afectacion,
            )
            .filter(
                models.AfectacionUnidadAgraria.id_afectacion_unidad == entity_id,
                models.AfectacionUnidadAgraria.activo.is_(True),
                models.Afectacion.activo.is_(True),
                models.ProyectoNucleo.activo.is_(True),
            )
        )
    elif entity_type == "asamblea_convocatoria":
        query = (
            db.query(models.ProyectoNucleo.id_proyecto)
            .join(
                models.Asamblea,
                models.Asamblea.id_proyecto_nucleo
                == models.ProyectoNucleo.id_proyecto_nucleo,
            )
            .join(
                models.AsambleaConvocatoria,
                models.AsambleaConvocatoria.id_asamblea
                == models.Asamblea.id_asamblea,
            )
            .filter(
                models.AsambleaConvocatoria.id_convocatoria == entity_id,
                models.AsambleaConvocatoria.activo.is_(True),
                models.Asamblea.activo.is_(True),
                models.ProyectoNucleo.activo.is_(True),
            )
        )
    elif entity_type == "convenio_compareciente":
        query = (
            db.query(models.ProyectoNucleo.id_proyecto)
            .join(
                models.Convenio,
                models.Convenio.id_proyecto_nucleo
                == models.ProyectoNucleo.id_proyecto_nucleo,
            )
            .join(
                models.ConvenioCompareciente,
                models.ConvenioCompareciente.id_convenio
                == models.Convenio.id_convenio,
            )
            .filter(
                models.ConvenioCompareciente.id_compareciente == entity_id,
                models.ConvenioCompareciente.activo.is_(True),
                models.Convenio.activo.is_(True),
                models.ProyectoNucleo.activo.is_(True),
            )
        )
    elif entity_type == "tramite_ran":
        ran = db.query(models.TramiteRan).filter(
            models.TramiteRan.id_tramite_ran == entity_id,
            models.TramiteRan.activo.is_(True),
        ).first()
        return _project_ids_for_ran(db, ran)
    elif entity_type == "tramite_ran_evento":
        event = db.query(models.TramiteRanEvento).join(
            models.TramiteRan,
            models.TramiteRan.id_tramite_ran == models.TramiteRanEvento.id_tramite_ran,
        ).filter(
            models.TramiteRanEvento.id_evento_ran == entity_id,
            models.TramiteRanEvento.activo.is_(True),
            models.TramiteRan.activo.is_(True),
        ).first()
        if event is None:
            return []
        return _project_ids_for_ran(db, event.tramite)
    elif entity_type == "tramite_fifonafe_evento":
        query = (
            db.query(models.ProyectoNucleo.id_proyecto)
            .join(
                models.TramiteFifonafe,
                models.TramiteFifonafe.id_proyecto_nucleo
                == models.ProyectoNucleo.id_proyecto_nucleo,
            )
            .join(
                models.TramiteFifonafeEvento,
                models.TramiteFifonafeEvento.id_tramite_fifonafe
                == models.TramiteFifonafe.id_tramite_fifonafe,
            )
            .filter(
                models.TramiteFifonafeEvento.id_evento_fifonafe == entity_id,
                models.TramiteFifonafeEvento.activo.is_(True),
                models.TramiteFifonafe.activo.is_(True),
                models.ProyectoNucleo.activo.is_(True),
            )
        )
    elif entity_type == "tramite_fifonafe_interviniente":
        query = (
            db.query(models.ProyectoNucleo.id_proyecto)
            .join(
                models.TramiteFifonafe,
                models.TramiteFifonafe.id_proyecto_nucleo
                == models.ProyectoNucleo.id_proyecto_nucleo,
            )
            .join(
                models.TramiteFifonafeInterviniente,
                models.TramiteFifonafeInterviniente.id_tramite_fifonafe
                == models.TramiteFifonafe.id_tramite_fifonafe,
            )
            .filter(
                models.TramiteFifonafeInterviniente.id_interviniente_fifonafe
                == entity_id,
                models.TramiteFifonafeInterviniente.activo.is_(True),
                models.TramiteFifonafe.activo.is_(True),
                models.ProyectoNucleo.activo.is_(True),
            )
        )
    elif entity_type == "indemnizacion":
        query = (
            db.query(models.ProyectoNucleo.id_proyecto)
            .join(
                models.Afectacion,
                models.Afectacion.id_proyecto_nucleo
                == models.ProyectoNucleo.id_proyecto_nucleo,
            )
            .join(
                models.Indemnizacion,
                models.Indemnizacion.id_afectacion == models.Afectacion.id_afectacion,
            )
            .filter(
                models.Indemnizacion.id_indemnizacion == entity_id,
                models.Indemnizacion.activo.is_(True),
                models.Afectacion.activo.is_(True),
                models.ProyectoNucleo.activo.is_(True),
            )
        )
    elif entity_type == "pago":
        query = (
            db.query(models.ProyectoNucleo.id_proyecto)
            .join(
                models.Afectacion,
                models.Afectacion.id_proyecto_nucleo
                == models.ProyectoNucleo.id_proyecto_nucleo,
            )
            .join(
                models.Indemnizacion,
                models.Indemnizacion.id_afectacion == models.Afectacion.id_afectacion,
            )
            .join(
                models.Pago,
                models.Pago.id_indemnizacion == models.Indemnizacion.id_indemnizacion,
            )
            .filter(
                models.Pago.id_pago == entity_id,
                models.Pago.activo.is_(True),
                models.Indemnizacion.activo.is_(True),
                models.Afectacion.activo.is_(True),
                models.ProyectoNucleo.activo.is_(True),
            )
        )
    else:
        raise HTTPException(status_code=422, detail="Tipo documental no permitido")
    return [row[0] for row in query.distinct().all()]


def require_document_target_access(
    db: Session,
    user: models.Usuario,
    entity_type: str,
    entity_id: int,
    *,
    mode: AccessMode = "read",
) -> int:
    project_ids = project_ids_for_document_target(db, entity_type, entity_id)
    if not project_ids:
        raise HTTPException(status_code=404, detail="Objetivo documental no encontrado")
    for project_id in project_ids:
        try:
            require_project_access(db, user, project_id, mode=mode)
            return project_id
        except HTTPException:
            continue
    raise _forbidden()


def require_document_access(
    db: Session,
    user: models.Usuario,
    document_id: int,
    *,
    mode: AccessMode = "read",
) -> models.Documento:
    document = db.query(models.Documento).filter(
        models.Documento.id_documento == document_id,
        models.Documento.activo.is_(True),
    ).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    links = db.query(models.DocumentoVinculo).filter(
        models.DocumentoVinculo.id_documento == document_id,
        models.DocumentoVinculo.activo.is_(True),
    ).all()
    if not links:
        raise HTTPException(status_code=409, detail="Documento sin vínculo activo")
    for link in links:
        try:
            require_document_target_access(
                db, user, link.entidad_tipo, link.entidad_id, mode=mode
            )
            return document
        except HTTPException:
            continue
    raise _forbidden()


def require_ran_procedure_access(
    db: Session,
    user: models.Usuario,
    procedure_id: int,
    *,
    mode: AccessMode = "read",
) -> models.TramiteRan:
    procedure = db.query(models.TramiteRan).filter(
        models.TramiteRan.id_tramite_ran == procedure_id,
        models.TramiteRan.activo.is_(True),
    ).first()
    if procedure is None:
        raise HTTPException(status_code=404, detail="Trámite RAN no encontrado")
    if procedure.id_asamblea is not None:
        if procedure.id_proyecto_nucleo is not None:
            require_project_nucleus_access(db, user, procedure.id_proyecto_nucleo, mode=mode)
        else:
            require_assembly_access(db, user, procedure.id_asamblea, mode=mode)
    elif procedure.id_convenio is not None:
        if procedure.id_proyecto_nucleo is not None:
            require_project_nucleus_access(db, user, procedure.id_proyecto_nucleo, mode=mode)
        else:
            require_agreement_access(db, user, procedure.id_convenio, mode=mode)
    elif procedure.id_orv is not None:
        if procedure.id_nucleo is not None:
            require_nucleus_access(db, user, procedure.id_nucleo, mode=mode)
        else:
            orv = db.query(models.Orv).filter(
                models.Orv.id_orv == procedure.id_orv,
                models.Orv.activo.is_(True),
            ).first()
            if orv is None:
                raise HTTPException(status_code=404, detail="ORV no encontrado")
            require_nucleus_access(db, user, orv.id_nucleo, mode=mode)
    elif procedure.id_proyecto_nucleo is not None:
        require_project_nucleus_access(db, user, procedure.id_proyecto_nucleo, mode=mode)
    elif procedure.id_nucleo is not None:
        require_nucleus_access(db, user, procedure.id_nucleo, mode=mode)
    else:
        raise _forbidden()
    return procedure
