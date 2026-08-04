from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services import pagos as service
from ..services.common import get_active
from ..services.access import require_tramo_nucleo_access, filter_by_user_tramos


router = APIRouter()
READ_ROLES = ["admin", "operador", "visualizador", "geografo"]
WRITE_ROLES = ["admin", "operador"]


@router.get(
    "/pagos-indemnizacion",
    response_model=List[schemas.PagoIndemnizacionResponse],
    tags=["Pagos de indemnización"],
)
def listar_pagos(
    id_tramite_fifonafe: int | None = Query(default=None),
    id_afectacion: int | None = Query(default=None),
    id_ciclo_afectacion: int | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.PagoIndemnizacion).join(
        models.TramiteFifonafe,
        models.TramiteFifonafe.id_tramite_fifonafe
        == models.PagoIndemnizacion.id_tramite_fifonafe,
    ).join(
        models.TramoNucleo,
        models.TramoNucleo.id_tramo_nucleo
        == models.TramiteFifonafe.id_tramo_nucleo,
    ).filter(
        models.PagoIndemnizacion.activo.is_(True)
    )
    query = filter_by_user_tramos(
        query, db, current_user, models.TramoNucleo.id_tramo
    )
    if id_tramite_fifonafe is not None:
        query = query.filter(
            models.PagoIndemnizacion.id_tramite_fifonafe
            == id_tramite_fifonafe
        )
    if id_afectacion is not None:
        query = query.filter(models.TramiteFifonafe.id_afectacion == id_afectacion)
    if id_ciclo_afectacion is not None:
        query = query.filter(
            models.TramiteFifonafe.id_ciclo_afectacion == id_ciclo_afectacion
        )
    return (
        query.order_by(
            models.PagoIndemnizacion.fecha_pago.desc(),
            models.PagoIndemnizacion.id_pago.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get(
    "/pagos-indemnizacion/{id_pago}",
    response_model=schemas.PagoIndemnizacionResponse,
    tags=["Pagos de indemnización"],
)
def obtener_pago(
    id_pago: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    pago = get_active(
        db,
        models.PagoIndemnizacion,
        id_pago,
        "id_pago",
        "Pago no encontrado",
    )
    require_tramo_nucleo_access(
        db, current_user, pago.tramite.id_tramo_nucleo
    )
    return pago


@router.post(
    "/pagos-indemnizacion",
    response_model=schemas.PagoIndemnizacionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Pagos de indemnización"],
)
def crear_pago(
    data: schemas.PagoIndemnizacionCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    tramite = get_active(
        db, models.TramiteFifonafe, data.id_tramite_fifonafe,
        "id_tramite_fifonafe", "Trámite FIFONAFE no encontrado",
    )
    require_tramo_nucleo_access(db, current_user, tramite.id_tramo_nucleo)
    return service.create_pago(db, data, current_user.id_usuario)


@router.put(
    "/pagos-indemnizacion/{id_pago}",
    response_model=schemas.PagoIndemnizacionResponse,
    tags=["Pagos de indemnización"],
)
def actualizar_pago(
    id_pago: int,
    data: schemas.PagoIndemnizacionUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    pago = get_active(
        db,
        models.PagoIndemnizacion,
        id_pago,
        "id_pago",
        "Pago no encontrado",
    )
    require_tramo_nucleo_access(db, current_user, pago.tramite.id_tramo_nucleo)
    return service.update_pago(db, pago, data, current_user.id_usuario)


@router.delete(
    "/pagos-indemnizacion/{id_pago}",
    tags=["Pagos de indemnización"],
)
def eliminar_pago(
    id_pago: int,
    motivo: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    pago = get_active(
        db,
        models.PagoIndemnizacion,
        id_pago,
        "id_pago",
        "Pago no encontrado",
    )
    require_tramo_nucleo_access(db, current_user, pago.tramite.id_tramo_nucleo)
    service.delete_pago(db, pago, current_user.id_usuario, motivo)
    return {"status": "success", "message": "Pago dado de baja"}
