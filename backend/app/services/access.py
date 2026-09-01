"""Project-scoped authorization resolved through canonical relationships."""

from typing import Literal

from fastapi import HTTPException
from sqlalchemy import exists, select
from sqlalchemy.orm import Query, Session

from .. import models


AccessMode = Literal["read", "capture", "gis"]


def _forbidden() -> HTTPException:
    return HTTPException(status_code=403, detail="Proyecto fuera del alcance autorizado")


def authorized_project_ids(db: Session, user: models.Usuario) -> select:
    if user.rol == "admin":
        return select(models.Proyecto.id_proyecto).where(models.Proyecto.activo.is_(True))
    return select(models.UsuarioProyecto.id_proyecto).where(
        models.UsuarioProyecto.id_usuario == user.id_usuario,
        models.UsuarioProyecto.activo.is_(True),
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
    elif entity_type in {"nucleo_agrario", "orv", "padron_historial", "parcela"}:
        nucleus_column = {
            "nucleo_agrario": models.NucleoAgrario.id_nucleo,
            "orv": models.Orv.id_nucleo,
            "padron_historial": models.PadronHistorial.id_nucleo,
            "parcela": models.Parcela.id_nucleo,
        }[entity_type]
        model = {
            "nucleo_agrario": models.NucleoAgrario,
            "orv": models.Orv,
            "padron_historial": models.PadronHistorial,
            "parcela": models.Parcela,
        }[entity_type]
        pk = {
            "nucleo_agrario": models.NucleoAgrario.id_nucleo,
            "orv": models.Orv.id_orv,
            "padron_historial": models.PadronHistorial.id_padron,
            "parcela": models.Parcela.id_parcela,
        }[entity_type]
        query = db.query(models.ProyectoNucleo.id_proyecto).join(
            model, nucleus_column == models.ProyectoNucleo.id_nucleo
        ).filter(pk == entity_id, models.ProyectoNucleo.activo.is_(True))
    elif entity_type in {"afectacion", "asamblea", "convenio", "tramite_fifonafe"}:
        model, pk = {
            "afectacion": (models.Afectacion, models.Afectacion.id_afectacion),
            "asamblea": (models.Asamblea, models.Asamblea.id_asamblea),
            "convenio": (models.Convenio, models.Convenio.id_convenio),
            "tramite_fifonafe": (
                models.TramiteFifonafe,
                models.TramiteFifonafe.id_tramite_fifonafe,
            ),
        }[entity_type]
        query = db.query(models.ProyectoNucleo.id_proyecto).join(
            model,
            model.id_proyecto_nucleo == models.ProyectoNucleo.id_proyecto_nucleo,
        ).filter(pk == entity_id, model.activo.is_(True))
    elif entity_type == "indemnizacion":
        query = db.query(models.ProyectoNucleo.id_proyecto).join(
            models.Afectacion,
            models.Afectacion.id_proyecto_nucleo
            == models.ProyectoNucleo.id_proyecto_nucleo,
        ).join(
            models.Indemnizacion,
            models.Indemnizacion.id_afectacion == models.Afectacion.id_afectacion,
        ).filter(
            models.Indemnizacion.id_indemnizacion == entity_id,
            models.Indemnizacion.activo.is_(True),
        )
    elif entity_type == "pago":
        query = db.query(models.ProyectoNucleo.id_proyecto).join(
            models.Afectacion,
            models.Afectacion.id_proyecto_nucleo
            == models.ProyectoNucleo.id_proyecto_nucleo,
        ).join(
            models.Indemnizacion,
            models.Indemnizacion.id_afectacion == models.Afectacion.id_afectacion,
        ).join(
            models.Pago,
            models.Pago.id_indemnizacion == models.Indemnizacion.id_indemnizacion,
        ).filter(models.Pago.id_pago == entity_id, models.Pago.activo.is_(True))
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
