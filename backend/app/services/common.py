"""Shared transaction and logical-deletion helpers."""

from datetime import datetime, timezone
from typing import Any, Type

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session


def set_audit_context(db: Session, user_id: int) -> None:
    db.execute(
        text("SELECT set_config('app.current_user_id', :id, true)"),
        {"id": str(user_id)},
    )


def get_active(
    db: Session,
    model: Type[Any],
    entity_id: int,
    id_column: str,
    detail: str | None = None,
):
    entity = db.query(model).filter(
        getattr(model, id_column) == entity_id,
        model.activo.is_(True),
    ).first()
    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=detail or f"{model.__name__} no encontrado",
        )
    return entity


def apply_update(entity: Any, data: Any, user_id: int) -> None:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(entity, key, value)
    if hasattr(entity, "actualizado_en"):
        entity.actualizado_en = datetime.now(timezone.utc)
        entity.actualizado_por = user_id


def mark_inactive(entity: Any, user_id: int, motivo: str) -> None:
    motivo = (motivo or "").strip()
    if len(motivo) < 3:
        raise HTTPException(status_code=400, detail="El motivo es obligatorio")
    entity.activo = False
    entity.fecha_baja = datetime.now(timezone.utc)
    entity.id_usuario_baja = user_id
    entity.motivo_baja = motivo


def commit_or_conflict(db: Session, detail: str = "Conflicto de integridad") -> None:
    try:
        db.commit()
    except (IntegrityError, DBAPIError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from exc


def flush_or_conflict(db: Session, detail: str = "Conflicto de integridad") -> None:
    try:
        db.flush()
    except (IntegrityError, DBAPIError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from exc
