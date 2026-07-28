from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services.common import get_active, reactivate, set_audit_context


router = APIRouter()
READ_ROLES = ["admin", "operador", "visualizador", "geografo"]


def _query_no_vistas(db: Session, id_usuario: int):
    vistas_activas = (
        db.query(models.AlertasVistas.id_alerta)
        .filter(
            models.AlertasVistas.id_usuario == id_usuario,
            models.AlertasVistas.activo.is_(True),
        )
    )
    return db.query(models.Alertas).filter(
        models.Alertas.activo.is_(True),
        models.Alertas.esta_activa.is_(True),
        ~models.Alertas.id_alerta.in_(vistas_activas),
    )


@router.get(
    "/alertas/no-vistas/count",
    response_model=schemas.AlertasNoVistasCount,
    tags=["Alertas"],
)
def contar_alertas_no_vistas(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    total = _query_no_vistas(db, current_user.id_usuario).count()
    return {"total": total}


@router.get(
    "/alertas/no-vistas",
    response_model=List[schemas.AlertaResponse],
    tags=["Alertas"],
)
def listar_alertas_no_vistas(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return (
        _query_no_vistas(db, current_user.id_usuario)
        .order_by(
            models.Alertas.fecha_evento.asc().nullslast(),
            models.Alertas.fecha_creacion.desc(),
        )
        .all()
    )


@router.post(
    "/alertas/generar-vencimientos",
    tags=["Alertas"],
)
def generar_alertas_vencimientos(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    insertadas = db.execute(
        text("SELECT fn_generar_alertas_orv_vencidos(:id_usuario)"),
        {"id_usuario": current_user.id_usuario},
    ).scalar_one()
    db.commit()
    return {"status": "success", "insertadas": insertadas}


@router.post(
    "/alertas/{id_alerta}/marcar-leida",
    tags=["Alertas"],
)
def marcar_alerta_leida(
    id_alerta: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    set_audit_context(db, current_user.id_usuario)
    get_active(db, models.Alertas, id_alerta, "id_alerta", "Alerta no encontrada")
    vista = (
        db.query(models.AlertasVistas)
        .filter_by(
            id_alerta=id_alerta,
            id_usuario=current_user.id_usuario,
        )
        .first()
    )
    if vista is None:
        vista = models.AlertasVistas(
            id_alerta=id_alerta,
            id_usuario=current_user.id_usuario,
            fecha_vista=func.now(),
        )
        db.add(vista)
    elif not vista.activo:
        reactivate(
            vista,
            current_user.id_usuario,
            "Marcada nuevamente como leída",
        )
        vista.fecha_vista = func.now()
    db.commit()
    return {"status": "success", "message": "Alerta marcada como leída"}
