"""Operaciones compuestas para administración territorial y de accesos."""

from datetime import datetime, timezone
from typing import Any, Type

from fastapi import HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .. import models, schemas


def set_audit_context(db: Session, user_id: int) -> None:
    db.execute(
        text('SET LOCAL "app.current_user_id" = :id'),
        {"id": str(user_id)},
    )


def _now():
    return datetime.now(timezone.utc)


def _active_or_404(db: Session, model: Type[Any], id_column: str, entity_id: int):
    entity = db.query(model).filter(
        getattr(model, id_column) == entity_id,
        model.activo.is_(True),
    ).with_for_update().first()
    if entity is None:
        raise HTTPException(status_code=404, detail="Registro activo no encontrado")
    return entity


def deactivate_user(
    db: Session,
    *,
    target_user_id: int,
    actor_user_id: int,
    reason: str,
) -> None:
    reason = reason.strip()
    if not reason:
        raise HTTPException(status_code=400, detail="El motivo es obligatorio")
    try:
        set_audit_context(db, actor_user_id)
        user = _active_or_404(db, models.Usuario, "id_usuario", target_user_id)
        if user.rol == "admin":
            db.execute(text("SELECT pg_advisory_xact_lock(hashtext('software_pa_active_admin'))"))
            other_admin = db.query(models.Usuario.id_usuario).filter(
                models.Usuario.activo.is_(True),
                models.Usuario.rol == "admin",
                models.Usuario.id_usuario != target_user_id,
            ).first()
            if other_admin is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No se puede desactivar al último administrador activo",
                )
        assignments = db.query(models.UsuarioTramo).filter(
            models.UsuarioTramo.id_usuario == target_user_id,
            models.UsuarioTramo.activo.is_(True),
        ).with_for_update().all()
        moment = _now()
        for assignment in assignments:
            assignment.activo = False
            assignment.fecha_baja = moment
            assignment.id_usuario_baja = actor_user_id
            assignment.motivo_baja = reason
        if assignments:
            db.flush(assignments)
        user.activo = False
        user.fecha_baja = moment
        user.id_usuario_baja = actor_user_id
        user.motivo_baja = reason
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise


def reactivate_entity(
    db: Session,
    *,
    model: Type[Any],
    id_column: str,
    entity_id: int,
    actor_user_id: int,
    reason: str,
):
    try:
        set_audit_context(db, actor_user_id)
        entity = db.query(model).filter(
            getattr(model, id_column) == entity_id,
        ).with_for_update().first()
        if entity is None:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        if entity.activo:
            raise HTTPException(status_code=409, detail="El registro ya está activo")
        if model is models.Tramo:
            parent_active = db.query(models.Proyecto.id_proyecto).filter(
                models.Proyecto.id_proyecto == entity.id_proyecto,
                models.Proyecto.activo.is_(True),
            ).first()
            if parent_active is None:
                raise HTTPException(
                    status_code=409,
                    detail="El proyecto del tramo debe estar activo antes de reactivarlo",
                )
        elif model is models.TramoNucleo:
            active_parents = db.query(models.Tramo.id_tramo).join(
                models.NucleoAgrario,
                models.NucleoAgrario.id_nucleo == entity.id_nucleo,
            ).filter(
                models.Tramo.id_tramo == entity.id_tramo,
                models.Tramo.activo.is_(True),
                models.NucleoAgrario.activo.is_(True),
            ).first()
            if active_parents is None:
                raise HTTPException(
                    status_code=409,
                    detail="El tramo y el núcleo deben estar activos antes de reactivar la relación",
                )
        entity.activo = True
        entity.fecha_reactivacion = _now()
        entity.id_usuario_reactivacion = actor_user_id
        entity.motivo_reactivacion = reason.strip()
        db.commit()
        db.refresh(entity)
        return entity
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise


def list_tramo_assignments(
    db: Session,
    id_tramo: int,
    *,
    include_inactive: bool = False,
):
    tramo = db.query(models.Tramo.id_tramo).filter(
        models.Tramo.id_tramo == id_tramo,
    ).first()
    if tramo is None:
        raise HTTPException(status_code=404, detail="Tramo no encontrado")
    query = db.query(
        models.UsuarioTramo.id_usuario_tramo,
        models.UsuarioTramo.id_usuario,
        models.UsuarioTramo.id_tramo,
        models.UsuarioTramo.fecha_asignacion,
        models.UsuarioTramo.activo,
        func.concat_ws(
            " ",
            models.Usuario.nombre,
            models.Usuario.apellido_paterno,
            models.Usuario.apellido_materno,
        ).label("nombre_usuario"),
        models.Usuario.correo,
        models.Usuario.rol,
    ).join(
        models.Usuario,
        models.Usuario.id_usuario == models.UsuarioTramo.id_usuario,
    ).filter(models.UsuarioTramo.id_tramo == id_tramo)
    if not include_inactive:
        query = query.filter(models.UsuarioTramo.activo.is_(True))
    return query.order_by(models.Usuario.correo).all()


def replace_tramo_assignments(
    db: Session,
    *,
    id_tramo: int,
    data: schemas.AsignacionesTramoReplace,
    actor_user_id: int,
):
    try:
        set_audit_context(db, actor_user_id)
        tramo = _active_or_404(db, models.Tramo, "id_tramo", id_tramo)
        del tramo

        desired_ids = set(data.ids_usuario)
        users = []
        if desired_ids:
            users = db.query(models.Usuario).filter(
                models.Usuario.id_usuario.in_(desired_ids),
            ).with_for_update().all()
            valid_ids = {user.id_usuario for user in users if user.activo}
            if valid_ids != desired_ids:
                raise HTTPException(
                    status_code=409,
                    detail="Todas las asignaciones deben corresponder a usuarios activos",
                )

        existing = db.query(models.UsuarioTramo).filter(
            models.UsuarioTramo.id_tramo == id_tramo,
        ).with_for_update().all()
        existing_by_user = {item.id_usuario: item for item in existing}
        active_ids = {item.id_usuario for item in existing if item.activo}
        to_disable = active_ids - desired_ids
        to_enable = desired_ids - active_ids
        moment = _now()
        reactivations = 0
        additions = 0

        for user_id in to_disable:
            assignment = existing_by_user[user_id]
            assignment.activo = False
            assignment.fecha_baja = moment
            assignment.id_usuario_baja = actor_user_id
            assignment.motivo_baja = data.motivo

        for user_id in to_enable:
            assignment = existing_by_user.get(user_id)
            if assignment is None:
                db.add(models.UsuarioTramo(
                    id_usuario=user_id,
                    id_tramo=id_tramo,
                    fecha_asignacion=moment,
                    activo=True,
                ))
                additions += 1
            else:
                assignment.activo = True
                assignment.fecha_asignacion = moment
                assignment.fecha_reactivacion = moment
                assignment.id_usuario_reactivacion = actor_user_id
                assignment.motivo_reactivacion = data.motivo
                reactivations += 1

        db.commit()
        return schemas.AdministracionResumenResponse(
            detail="Asignaciones territoriales actualizadas",
            altas=additions,
            bajas=len(to_disable),
            reactivaciones=reactivations,
        )
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise
