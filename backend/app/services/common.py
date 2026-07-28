from datetime import datetime, timezone
from typing import Any, Type

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def set_audit_context(db: Session, user_id: int) -> None:
    db.execute(
        text('SET LOCAL "app.current_user_id" = :id'),
        {"id": str(user_id)},
    )


def get_active(
    db: Session,
    model: Type[Any],
    entity_id: int,
    id_column: str,
    detail: str | None = None,
):
    entity = (
        db.query(model)
        .filter(
            getattr(model, id_column) == entity_id,
            model.activo.is_(True),
        )
        .first()
    )
    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=detail or f"{model.__name__} no encontrado",
        )
    return entity


def mark_inactive(entity: Any, user_id: int, motivo: str) -> None:
    motivo = (motivo or "").strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="El motivo es obligatorio")
    entity.activo = False
    entity.fecha_baja = datetime.now(timezone.utc)
    entity.id_usuario_baja = user_id
    entity.motivo_baja = motivo


def reactivate(entity: Any, user_id: int, motivo: str) -> None:
    motivo = (motivo or "").strip()
    if not motivo:
        raise HTTPException(
            status_code=400,
            detail="El motivo de reactivación es obligatorio",
        )
    entity.activo = True
    entity.fecha_reactivacion = datetime.now(timezone.utc)
    entity.id_usuario_reactivacion = user_id
    entity.motivo_reactivacion = motivo


def commit_or_conflict(
    db: Session,
    constraint_messages: dict[str, str],
) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint = getattr(getattr(exc, "orig", None), "diag", None)
        constraint_name = getattr(constraint, "constraint_name", None)
        if constraint_name in constraint_messages:
            raise HTTPException(
                status_code=409,
                detail=constraint_messages[constraint_name],
            ) from exc
        raise
