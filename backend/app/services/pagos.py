from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from .common import commit_or_conflict, get_active, mark_inactive, set_audit_context
from .access import require_seguimiento_pa_activo


PAYMENT_CONFLICTS = {
    "uq_pago_total_activo": "El trámite ya tiene un pago total activo",
    "uq_pago_referencia_activa": "La referencia bancaria ya está registrada",
}


def _validar_beneficiario(
    db: Session,
    id_persona: int | None,
    beneficiario_externo: str | None,
) -> None:
    opciones = [
        id_persona is not None,
        bool(beneficiario_externo and beneficiario_externo.strip()),
    ]
    if sum(opciones) != 1:
        raise HTTPException(
            status_code=400,
            detail="Debe indicar exactamente un beneficiario",
        )
    if id_persona is not None:
        get_active(
            db,
            models.Persona,
            id_persona,
            "id_persona",
            "Persona beneficiaria no encontrada",
        )


def _validar_tramite(db: Session, id_tramite: int) -> models.TramiteFifonafe:
    tramite = get_active(
        db,
        models.TramiteFifonafe,
        id_tramite,
        "id_tramite_fifonafe",
        "Trámite FIFONAFE no encontrado",
    )
    if tramite.tipo_tramite != "indemnizacion" or tramite.id_convenio is None:
        raise HTTPException(
            status_code=400,
            detail="El pago requiere un trámite de indemnización vinculado a un convenio",
        )
    get_active(
        db,
        models.Convenio,
        tramite.id_convenio,
        "id_convenio",
        "Convenio no encontrado",
    )
    tramo_nucleo = get_active(
        db,
        models.TramoNucleo,
        tramite.id_tramo_nucleo,
        "id_tramo_nucleo",
        "Expediente no encontrado",
    )
    require_seguimiento_pa_activo(db, tramo_nucleo)
    return tramite


def create_pago(
    db: Session,
    data: schemas.PagoIndemnizacionCreate,
    user_id: int,
) -> models.PagoIndemnizacion:
    set_audit_context(db, user_id)
    _validar_tramite(db, data.id_tramite_fifonafe)
    _validar_beneficiario(
        db,
        data.id_persona_beneficiaria,
        data.beneficiario_externo,
    )
    pago = models.PagoIndemnizacion(**data.model_dump(exclude_unset=True))
    db.add(pago)
    commit_or_conflict(db, PAYMENT_CONFLICTS)
    db.refresh(pago)
    return pago


def update_pago(
    db: Session,
    pago: models.PagoIndemnizacion,
    data: schemas.PagoIndemnizacionUpdate,
    user_id: int,
) -> models.PagoIndemnizacion:
    set_audit_context(db, user_id)
    changes = data.model_dump(exclude_unset=True)
    required_values = {
        "monto_pagado": changes.get("monto_pagado", pago.monto_pagado),
        "fecha_pago": changes.get("fecha_pago", pago.fecha_pago),
        "tipo_pago": changes.get("tipo_pago", pago.tipo_pago),
    }
    if any(value is None for value in required_values.values()):
        raise HTTPException(
            status_code=400,
            detail="monto_pagado, fecha_pago y tipo_pago son obligatorios",
        )
    id_persona = changes.get(
        "id_persona_beneficiaria",
        pago.id_persona_beneficiaria,
    )
    beneficiario_externo = changes.get(
        "beneficiario_externo",
        pago.beneficiario_externo,
    )
    _validar_beneficiario(db, id_persona, beneficiario_externo)
    for field, value in changes.items():
        setattr(pago, field, value)
    commit_or_conflict(db, PAYMENT_CONFLICTS)
    db.refresh(pago)
    return pago


def delete_pago(
    db: Session,
    pago: models.PagoIndemnizacion,
    user_id: int,
    motivo: str,
) -> None:
    set_audit_context(db, user_id)
    mark_inactive(pago, user_id, motivo)
    db.commit()
