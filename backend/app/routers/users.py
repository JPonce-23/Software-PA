"""Secure user administration and project assignments."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services.common import commit_or_conflict, set_audit_context


router = APIRouter(tags=["Usuarios"])


@router.post("/usuarios", response_model=schemas.UsuarioResponse, status_code=201)
def create_user(
    data: schemas.UsuarioCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    existing = db.query(models.Usuario.id_usuario).filter(
        func.lower(func.btrim(models.Usuario.correo)) == data.correo
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="El correo ya está registrado")
    set_audit_context(db, user.id_usuario)
    record = models.Usuario(
        **data.model_dump(exclude={"contrasena"}),
        contrasena_hash=auth.get_password_hash(data.contrasena),
        fecha_alta=datetime.now(timezone.utc),
    )
    db.add(record)
    commit_or_conflict(db, "No fue posible crear el usuario")
    db.refresh(record)
    return record


@router.get("/usuarios", response_model=list[schemas.UsuarioResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    return db.query(models.Usuario).filter(
        models.Usuario.activo.is_(True)
    ).order_by(models.Usuario.correo).offset(skip).limit(limit).all()


@router.patch("/usuarios/{id_usuario}", response_model=schemas.UsuarioResponse)
def update_user(
    id_usuario: int,
    data: schemas.UsuarioUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    target = db.query(models.Usuario).filter(
        models.Usuario.id_usuario == id_usuario,
        models.Usuario.activo.is_(True),
    ).with_for_update().first()
    if target is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if target.rol == "admin" and data.rol is not None and data.rol != "admin":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext('software_pa_active_admin'))")
        )
        other = db.query(models.Usuario.id_usuario).filter(
            models.Usuario.rol == "admin",
            models.Usuario.activo.is_(True),
            models.Usuario.id_usuario != id_usuario,
        ).first()
        if other is None:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="No se puede degradar al último administrador activo",
            )
    set_audit_context(db, user.id_usuario)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(target, key, value)
    commit_or_conflict(db)
    db.refresh(target)
    return target


@router.delete(
    "/usuarios/{id_usuario}",
    response_model=schemas.AuthOperationResponse,
)
def delete_user(
    id_usuario: int,
    data: schemas.BajaRequest,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    target = db.query(models.Usuario).filter(
        models.Usuario.id_usuario == id_usuario,
        models.Usuario.activo.is_(True),
    ).with_for_update().first()
    if target is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if target.rol == "admin":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext('software_pa_active_admin'))")
        )
        other = db.query(models.Usuario.id_usuario).filter(
            models.Usuario.rol == "admin",
            models.Usuario.activo.is_(True),
            models.Usuario.id_usuario != id_usuario,
        ).first()
        if other is None:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="No se puede desactivar al último administrador activo",
            )
    set_audit_context(db, user.id_usuario)
    now = datetime.now(timezone.utc)
    assignments = db.query(models.UsuarioProyecto).filter(
        models.UsuarioProyecto.id_usuario == id_usuario,
        models.UsuarioProyecto.activo.is_(True),
    ).all()
    for assignment in assignments:
        assignment.activo = False
        assignment.fecha_baja = now
        assignment.id_usuario_baja = user.id_usuario
        assignment.motivo_baja = data.motivo
    sessions = db.query(models.SesionUsuario).filter(
        models.SesionUsuario.id_usuario == id_usuario,
        models.SesionUsuario.revocada_en.is_(None),
    ).all()
    for session in sessions:
        session.revocada_en = now
        session.id_usuario_revoca = user.id_usuario
        session.motivo_revocacion = "usuario_inactivo"
    target.activo = False
    target.fecha_baja = now
    target.id_usuario_baja = user.id_usuario
    target.motivo_baja = data.motivo
    commit_or_conflict(db, "No fue posible desactivar el usuario")
    return {"detail": "Usuario desactivado"}
