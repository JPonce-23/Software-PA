from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services.access import require_afectacion_access, require_tramo_nucleo_access
from ..services import minutas as service
from ..services.common import get_active


router = APIRouter()
READ_ROLES = ["admin", "operador", "visualizador", "geografo"]
WRITE_ROLES = ["admin", "operador", "geografo"]


def _require_minuta_access(
    db: Session,
    current_user: models.Usuario,
    id_minuta: int,
) -> models.Minuta:
    minuta = get_active(db, models.Minuta, id_minuta, "id_minuta")
    require_tramo_nucleo_access(db, current_user, minuta.id_tramo_nucleo)
    return minuta


def _require_acuerdo_access(
    db: Session,
    current_user: models.Usuario,
    id_acuerdo: int,
) -> models.Acuerdo:
    acuerdo = get_active(db, models.Acuerdo, id_acuerdo, "id_acuerdo")
    _require_minuta_access(db, current_user, acuerdo.id_minuta)
    return acuerdo


@router.get("/minutas", response_model=List[schemas.MinutaResponse], tags=["Minutas"])
def listar_minutas(
    id_tramo_nucleo: int | None = Query(default=None),
    id_afectacion: int | None = Query(default=None),
    solo_compartidas: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.Minuta).filter(models.Minuta.activo.is_(True))
    if id_tramo_nucleo is not None:
        require_tramo_nucleo_access(db, current_user, id_tramo_nucleo)
        query = query.filter(models.Minuta.id_tramo_nucleo == id_tramo_nucleo)
    if id_afectacion is not None:
        afectacion = require_afectacion_access(db, current_user, id_afectacion)
        if id_tramo_nucleo is not None and afectacion.id_tramo_nucleo != id_tramo_nucleo:
            raise HTTPException(
                status_code=404,
                detail="Afectación no encontrada en el expediente solicitado",
            )
        query = query.filter(models.Minuta.id_afectacion == id_afectacion)
    elif solo_compartidas:
        query = query.filter(models.Minuta.id_afectacion.is_(None))
    return (
        query.order_by(models.Minuta.fecha_reunion.desc(), models.Minuta.id_minuta.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get(
    "/minutas/{id_minuta}",
    response_model=schemas.MinutaResponse,
    tags=["Minutas"],
)
def obtener_minuta(
    id_minuta: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return _require_minuta_access(db, current_user, id_minuta)


@router.post(
    "/minutas",
    response_model=schemas.MinutaResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Minutas"],
)
def crear_minuta(
    data: schemas.MinutaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    require_tramo_nucleo_access(db, current_user, data.id_tramo_nucleo)
    if data.id_afectacion is not None:
        afectacion = require_afectacion_access(db, current_user, data.id_afectacion)
        if afectacion.id_tramo_nucleo != data.id_tramo_nucleo:
            raise HTTPException(
                status_code=400,
                detail="La afectación no pertenece al expediente de la minuta",
            )
    return service.create_minuta(db, data, current_user.id_usuario)


@router.put(
    "/minutas/{id_minuta}",
    response_model=schemas.MinutaResponse,
    tags=["Minutas"],
)
def actualizar_minuta(
    id_minuta: int,
    data: schemas.MinutaUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    minuta = _require_minuta_access(db, current_user, id_minuta)
    return service.update_minuta(db, minuta, data, current_user.id_usuario)


@router.delete("/minutas/{id_minuta}", tags=["Minutas"])
def eliminar_minuta(
    id_minuta: int,
    motivo: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    minuta = _require_minuta_access(db, current_user, id_minuta)
    service.delete_minuta(db, minuta, current_user.id_usuario, motivo)
    return {"status": "success", "message": "Minuta dada de baja"}


@router.get(
    "/minutas/{id_minuta}/acuerdos",
    response_model=List[schemas.AcuerdoResponse],
    tags=["Acuerdos"],
)
def listar_acuerdos(
    id_minuta: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    _require_minuta_access(db, current_user, id_minuta)
    return (
        db.query(models.Acuerdo)
        .filter_by(id_minuta=id_minuta, activo=True)
        .order_by(models.Acuerdo.fecha_limite, models.Acuerdo.id_acuerdo)
        .all()
    )


@router.post(
    "/minutas/{id_minuta}/acuerdos",
    response_model=schemas.AcuerdoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Acuerdos"],
)
def crear_acuerdo(
    id_minuta: int,
    data: schemas.AcuerdoCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    minuta = _require_minuta_access(db, current_user, id_minuta)
    return service.create_acuerdo(db, minuta, data, current_user.id_usuario)


@router.get(
    "/acuerdos/{id_acuerdo}",
    response_model=schemas.AcuerdoResponse,
    tags=["Acuerdos"],
)
def obtener_acuerdo(
    id_acuerdo: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return _require_acuerdo_access(db, current_user, id_acuerdo)


@router.put(
    "/acuerdos/{id_acuerdo}",
    response_model=schemas.AcuerdoResponse,
    tags=["Acuerdos"],
)
def actualizar_acuerdo(
    id_acuerdo: int,
    data: schemas.AcuerdoUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    acuerdo = _require_acuerdo_access(db, current_user, id_acuerdo)
    return service.update_acuerdo(db, acuerdo, data, current_user.id_usuario)


@router.delete("/acuerdos/{id_acuerdo}", tags=["Acuerdos"])
def eliminar_acuerdo(
    id_acuerdo: int,
    motivo: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    acuerdo = _require_acuerdo_access(db, current_user, id_acuerdo)
    service.delete_acuerdo(db, acuerdo, current_user.id_usuario, motivo)
    return {"status": "success", "message": "Acuerdo dado de baja"}
