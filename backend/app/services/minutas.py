from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from .common import get_active, mark_inactive, set_audit_context


def _validar_afectacion_ciclo(
    db: Session,
    id_tramo_nucleo: int,
    id_afectacion: int | None,
    id_ciclo_afectacion: int | None,
) -> None:
    if (id_afectacion is None) != (id_ciclo_afectacion is None):
        raise HTTPException(
            status_code=400,
            detail="La minuta propia requiere afectación y ciclo",
        )
    if id_afectacion is None:
        return
    ciclo = db.query(models.AfectacionCiclo).filter(
        models.AfectacionCiclo.id_tramo_nucleo == id_tramo_nucleo,
        models.AfectacionCiclo.id_afectacion == id_afectacion,
        models.AfectacionCiclo.id_ciclo_afectacion == id_ciclo_afectacion,
        models.AfectacionCiclo.activo.is_(True),
    ).first()
    if ciclo is None:
        raise HTTPException(
            status_code=400,
            detail="La afectación y el ciclo no pertenecen al expediente",
        )


def _validar_actividad_vs_ciclo(
    db: Session,
    id_actividad: int | None,
    id_tramo_nucleo: int,
    id_ciclo_afectacion: int | None,
) -> None:
    if id_actividad is None:
        return
    actividad = get_active(
        db,
        models.ActividadCampo,
        id_actividad,
        "id_actividad",
        "Actividad de campo no encontrada",
    )
    if actividad.id_tramo_nucleo != id_tramo_nucleo:
        raise HTTPException(
            status_code=400,
            detail="La actividad no pertenece al expediente de la minuta",
        )
    if id_ciclo_afectacion is None and actividad.id_ciclo_afectacion is not None:
        raise HTTPException(
            status_code=400,
            detail="Una minuta compartida no puede apuntar a una actividad propia de ciclo",
        )
    if (
        id_ciclo_afectacion is not None
        and actividad.id_ciclo_afectacion != id_ciclo_afectacion
    ):
        raise HTTPException(
            status_code=400,
            detail="La actividad no pertenece al ciclo indicado",
        )


def create_minuta(
    db: Session,
    data: schemas.MinutaCreate,
    user_id: int,
) -> models.Minuta:
    set_audit_context(db, user_id)
    get_active(
        db,
        models.TramoNucleo,
        data.id_tramo_nucleo,
        "id_tramo_nucleo",
        "Expediente Tramo-Núcleo no encontrado",
    )
    _validar_afectacion_ciclo(
        db,
        data.id_tramo_nucleo,
        data.id_afectacion,
        data.id_ciclo_afectacion,
    )
    _validar_actividad_vs_ciclo(
        db,
        data.id_actividad,
        data.id_tramo_nucleo,
        data.id_ciclo_afectacion,
    )
    minuta = models.Minuta(**data.model_dump(exclude_unset=True))
    db.add(minuta)
    db.commit()
    db.refresh(minuta)
    return minuta


def update_minuta(
    db: Session,
    minuta: models.Minuta,
    data: schemas.MinutaUpdate,
    user_id: int,
) -> models.Minuta:
    set_audit_context(db, user_id)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("fecha_reunion", minuta.fecha_reunion) is None:
        raise HTTPException(status_code=400, detail="fecha_reunion es obligatoria")
    if changes.get("asunto", minuta.asunto) is None:
        raise HTTPException(status_code=400, detail="asunto es obligatorio")
    id_afectacion = changes.get("id_afectacion", minuta.id_afectacion)
    id_ciclo_afectacion = changes.get(
        "id_ciclo_afectacion",
        minuta.id_ciclo_afectacion,
    )
    id_actividad = changes.get("id_actividad", minuta.id_actividad)
    _validar_afectacion_ciclo(
        db,
        minuta.id_tramo_nucleo,
        id_afectacion,
        id_ciclo_afectacion,
    )
    _validar_actividad_vs_ciclo(
        db,
        id_actividad,
        minuta.id_tramo_nucleo,
        id_ciclo_afectacion,
    )
    for field, value in changes.items():
        setattr(minuta, field, value)
    db.commit()
    db.refresh(minuta)
    return minuta


def _validar_responsable(
    db: Session,
    id_persona: int | None,
    id_usuario: int | None,
    responsable_externo: str | None,
) -> None:
    responsables = [
        id_persona is not None,
        id_usuario is not None,
        bool(responsable_externo and responsable_externo.strip()),
    ]
    if sum(responsables) != 1:
        raise HTTPException(
            status_code=400,
            detail="Debe indicar exactamente un responsable",
        )
    if id_persona is not None:
        get_active(
            db, models.Persona, id_persona, "id_persona", "Persona no encontrada"
        )
    if id_usuario is not None:
        get_active(
            db, models.Usuario, id_usuario, "id_usuario", "Usuario no encontrado"
        )


def create_acuerdo(
    db: Session,
    minuta: models.Minuta,
    data: schemas.AcuerdoCreate,
    user_id: int,
) -> models.Acuerdo:
    set_audit_context(db, user_id)
    _validar_responsable(
        db,
        data.id_persona_responsable,
        data.id_usuario_responsable,
        data.responsable_externo,
    )
    acuerdo = models.Acuerdo(
        id_minuta=minuta.id_minuta,
        **data.model_dump(exclude_unset=True),
    )
    db.add(acuerdo)
    db.commit()
    db.refresh(acuerdo)
    return acuerdo


def update_acuerdo(
    db: Session,
    acuerdo: models.Acuerdo,
    data: schemas.AcuerdoUpdate,
    user_id: int,
) -> models.Acuerdo:
    set_audit_context(db, user_id)
    changes = data.model_dump(exclude_unset=True)
    values = {
        "descripcion": acuerdo.descripcion,
        "id_persona_responsable": acuerdo.id_persona_responsable,
        "id_usuario_responsable": acuerdo.id_usuario_responsable,
        "responsable_externo": acuerdo.responsable_externo,
        "estatus": acuerdo.estatus,
        "fecha_cumplimiento": acuerdo.fecha_cumplimiento,
    }
    values.update(changes)
    if values["descripcion"] is None:
        raise HTTPException(status_code=400, detail="descripcion es obligatoria")
    _validar_responsable(
        db,
        values["id_persona_responsable"],
        values["id_usuario_responsable"],
        values["responsable_externo"],
    )
    if (values["estatus"] == "cumplido") != (
        values["fecha_cumplimiento"] is not None
    ):
        raise HTTPException(
            status_code=400,
            detail="Un acuerdo cumplido requiere fecha_cumplimiento",
        )
    for field, value in changes.items():
        setattr(acuerdo, field, value)
    db.commit()
    db.refresh(acuerdo)
    return acuerdo


def delete_minuta(
    db: Session,
    minuta: models.Minuta,
    user_id: int,
    motivo: str,
) -> None:
    if (
        db.query(models.Acuerdo)
        .filter_by(id_minuta=minuta.id_minuta, activo=True)
        .first()
    ):
        raise HTTPException(
            status_code=409,
            detail="La minuta tiene acuerdos activos; délos de baja primero",
        )
    set_audit_context(db, user_id)
    mark_inactive(minuta, user_id, motivo)
    db.commit()


def delete_acuerdo(
    db: Session,
    acuerdo: models.Acuerdo,
    user_id: int,
    motivo: str,
) -> None:
    set_audit_context(db, user_id)
    mark_inactive(acuerdo, user_id, motivo)
    db.commit()
