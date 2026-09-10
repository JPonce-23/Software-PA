"""Read-only audit projections with server-side redaction."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models


_SENSITIVE_FIELD_MARKERS = ("contrasena_hash", "contraseña", "contrasena", "password", "token", "csrf", "secret", "sesion")
_GEOMETRY_FIELD_MARKERS = ("geometr", "geojson", "wkt", "wkb", "geometry", "shape", "blob", "binary")
_SENSITIVE_TEXT = re.compile(r"password|contrase(?:ñ|n)a|csrf|token|secret", re.I)


def _normalized_field_name(name: str) -> str:
    return name.strip().lower().replace("-", "_")


def is_sensitive_field(name: str) -> bool:
    return any(marker in _normalized_field_name(name) for marker in _SENSITIVE_FIELD_MARKERS)


def is_geometry_field(name: str) -> bool:
    return any(marker in _normalized_field_name(name) for marker in _GEOMETRY_FIELD_MARKERS)


def sanitize_value(value: Any, *, field_name: str) -> Any:
    if is_geometry_field(field_name):
        return "[geometría]"
    if isinstance(value, dict):
        return {key: sanitize_value(item, field_name=key) for key, item in value.items() if not is_sensitive_field(key)}
    if isinstance(value, list):
        return [sanitize_value(item, field_name=field_name) for item in value]
    return value


def calculate_changes(previous: dict[str, Any] | None, current: dict[str, Any] | None) -> list[dict[str, Any]]:
    previous, current = previous or {}, current or {}
    changes = []
    for field_name in sorted(set(previous) | set(current)):
        if is_sensitive_field(field_name):
            continue
        old_value, new_value = previous.get(field_name), current.get(field_name)
        if old_value != new_value:
            changes.append({"campo": field_name, "anterior": sanitize_value(old_value, field_name=field_name), "nuevo": sanitize_value(new_value, field_name=field_name)})
    return changes


def action_description(action: str, previous: dict[str, Any] | None, current: dict[str, Any] | None) -> str:
    if action == "insert":
        return "Alta"
    if action == "update":
        if previous and current and previous.get("activo") is True and current.get("activo") is False:
            return "Baja"
        if previous and current and previous.get("activo") is False and current.get("activo") is True:
            return "Reactivación"
        return "Modificación"
    return action.replace("_", " ").capitalize()


def _user_summaries(db: Session, user_ids: Iterable[int | None]) -> dict[int, dict[str, Any]]:
    ids = {value for value in user_ids if value is not None}
    if not ids:
        return {}
    return {
        user.id_usuario: {"id_usuario": user.id_usuario, "nombre": user.nombre, "apellido_paterno": user.apellido_paterno, "apellido_materno": user.apellido_materno, "correo": user.correo}
        for user in db.query(models.Usuario).filter(models.Usuario.id_usuario.in_(ids)).all()
    }


def _change_filters(query, **filters):
    mapping = {
        "id_usuario": models.Bitacora.id_usuario, "id_proyecto": models.Bitacora.id_proyecto,
        "id_proyecto_nucleo": models.Bitacora.id_proyecto_nucleo, "id_nucleo": models.Bitacora.id_nucleo,
        "entidad_tipo": models.Bitacora.entidad_tipo, "entidad_id": models.Bitacora.entidad_id,
        "accion": models.Bitacora.accion,
    }
    for name, column in mapping.items():
        if filters[name] is not None:
            query = query.filter(column == filters[name])
    if filters["desde"] is not None:
        query = query.filter(models.Bitacora.fecha_hora >= filters["desde"])
    if filters["hasta"] is not None:
        query = query.filter(models.Bitacora.fecha_hora <= filters["hasta"])
    return query


def list_changes(db: Session, *, skip: int, limit: int, **filters) -> dict[str, Any]:
    base = _change_filters(db.query(models.Bitacora), **filters)
    total = base.with_entities(func.count(models.Bitacora.id_bitacora)).scalar()
    records = base.order_by(models.Bitacora.fecha_hora.desc(), models.Bitacora.id_bitacora.desc()).offset(skip).limit(limit).all()
    users = _user_summaries(db, (record.id_usuario for record in records))
    return {"total": total, "items": [
        {"id_bitacora": record.id_bitacora, "fecha_hora": record.fecha_hora, "usuario": users.get(record.id_usuario),
         "id_proyecto": record.id_proyecto, "id_proyecto_nucleo": record.id_proyecto_nucleo, "id_nucleo": record.id_nucleo,
         "entidad_tipo": record.entidad_tipo, "entidad_id": record.entidad_id, "accion": record.accion,
         "accion_descripcion": action_description(record.accion, record.valor_anterior, record.valor_nuevo),
         "cambios": calculate_changes(record.valor_anterior, record.valor_nuevo)} for record in records]}


def list_access_events(db: Session, *, id_usuario: int | None, id_usuario_actor: int | None, tipo_evento: str | None, motivo_codigo: str | None, desde: datetime | None, hasta: datetime | None, skip: int, limit: int) -> dict[str, Any]:
    query = db.query(models.EventoAcceso)
    for column, value in ((models.EventoAcceso.id_usuario, id_usuario), (models.EventoAcceso.id_usuario_actor, id_usuario_actor), (models.EventoAcceso.tipo_evento, tipo_evento), (models.EventoAcceso.motivo_codigo, motivo_codigo)):
        if value is not None:
            query = query.filter(column == value)
    if desde is not None:
        query = query.filter(models.EventoAcceso.fecha_hora >= desde)
    if hasta is not None:
        query = query.filter(models.EventoAcceso.fecha_hora <= hasta)
    total = query.with_entities(func.count(models.EventoAcceso.id_evento)).scalar()
    records = query.order_by(models.EventoAcceso.fecha_hora.desc(), models.EventoAcceso.id_evento.desc()).offset(skip).limit(limit).all()
    users = _user_summaries(db, (user_id for record in records for user_id in (record.id_usuario, record.id_usuario_actor)))
    return {"total": total, "items": [
        {"id_evento": record.id_evento, "fecha_hora": record.fecha_hora, "usuario": users.get(record.id_usuario), "usuario_actor": users.get(record.id_usuario_actor),
         "tipo_evento": record.tipo_evento, "motivo_codigo": record.motivo_codigo,
         "detalle": "[redactado]" if record.detalle and _SENSITIVE_TEXT.search(record.detalle) else record.detalle,
         "id_sesion": record.id_sesion, "ip_origen": str(record.ip_origen) if record.ip_origen else None, "user_agent": record.user_agent}
        for record in records]}
