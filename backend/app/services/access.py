"""Autorización territorial para recursos del flujo de liberación."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Query, Session

from .. import models


def require_tramo_access(
    db: Session,
    user: models.Usuario,
    id_tramo: int,
) -> None:
    if user.rol == "admin":
        return
    permitido = db.query(models.UsuarioTramo.id_usuario_tramo).filter(
        models.UsuarioTramo.id_usuario == user.id_usuario,
        models.UsuarioTramo.id_tramo == id_tramo,
        models.UsuarioTramo.activo.is_(True),
    ).first()
    if permitido is None:
        # Una misma respuesta evita revelar si el recurso existe en otro tramo.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso al tramo solicitado",
        )


def require_tramo_nucleo_access(
    db: Session,
    user: models.Usuario,
    id_tramo_nucleo: int,
) -> models.TramoNucleo:
    tramo_nucleo = db.query(models.TramoNucleo).filter(
        models.TramoNucleo.id_tramo_nucleo == id_tramo_nucleo,
        models.TramoNucleo.activo.is_(True),
    ).first()
    if tramo_nucleo is None:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    require_tramo_access(db, user, tramo_nucleo.id_tramo)
    return tramo_nucleo


def require_afectacion_access(
    db: Session,
    user: models.Usuario,
    id_afectacion: int,
) -> models.Afectacion:
    afectacion = db.query(models.Afectacion).filter(
        models.Afectacion.id_afectacion == id_afectacion,
        models.Afectacion.activo.is_(True),
    ).first()
    if afectacion is None:
        raise HTTPException(status_code=404, detail="Afectación no encontrada")
    require_tramo_nucleo_access(db, user, afectacion.id_tramo_nucleo)
    return afectacion


def require_nucleo_access(
    db: Session,
    user: models.Usuario,
    id_nucleo: int,
) -> None:
    if user.rol == "admin":
        return
    permitido = db.query(models.TramoNucleo.id_tramo_nucleo).join(
        models.UsuarioTramo,
        models.UsuarioTramo.id_tramo == models.TramoNucleo.id_tramo,
    ).filter(
        models.TramoNucleo.id_nucleo == id_nucleo,
        models.TramoNucleo.activo.is_(True),
        models.UsuarioTramo.id_usuario == user.id_usuario,
        models.UsuarioTramo.activo.is_(True),
    ).first()
    if permitido is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso al núcleo solicitado",
        )


def filter_by_user_tramos(
    query: Query,
    db: Session,
    user: models.Usuario,
    id_tramo_column,
) -> Query:
    if user.rol == "admin":
        return query
    tramos = db.query(models.UsuarioTramo.id_tramo).filter(
        models.UsuarioTramo.id_usuario == user.id_usuario,
        models.UsuarioTramo.activo.is_(True),
    )
    return query.filter(id_tramo_column.in_(tramos))
