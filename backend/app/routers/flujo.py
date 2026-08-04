from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services import flujo as service


router = APIRouter(tags=["Flujo de liberación 2B"])
READ_ROLES = ["admin", "operador", "visualizador", "geografo"]
WRITE_ROLES = ["admin", "operador"]


@router.get(
    "/afectaciones/{id_afectacion}/ciclos",
    response_model=list[schemas.AfectacionCicloResponse],
)
def listar_ciclos(
    id_afectacion: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return service.listar_ciclos(db, current_user, id_afectacion)


@router.post(
    "/afectaciones/{id_afectacion}/ciclos",
    response_model=schemas.AfectacionCicloResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_ciclo(
    id_afectacion: int,
    data: schemas.AfectacionCicloCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    return service.crear_ciclo(db, current_user, id_afectacion, data)


@router.get(
    "/afectaciones/{id_afectacion}/estado",
    response_model=schemas.AfectacionEstadoResponse,
)
def estado_afectacion(
    id_afectacion: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return service.obtener_estado_afectacion(db, current_user, id_afectacion)


@router.get(
    "/tramos-nucleos/{id_tramo_nucleo}/estado",
    response_model=schemas.TramoNucleoEstadoResponse,
)
def estado_tramo_nucleo(
    id_tramo_nucleo: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return service.obtener_estado_tramo_nucleo(db, current_user, id_tramo_nucleo)


@router.put(
    "/afectaciones/{id_afectacion}/salida-terminal",
    response_model=schemas.AfectacionResponse,
)
def salida_terminal(
    id_afectacion: int,
    data: schemas.SalidaTerminalRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    return service.marcar_salida_terminal(db, current_user, id_afectacion, data)


@router.post(
    "/fifonafe/{id_tramite}/completar-indemnizacion",
    response_model=schemas.TramiteFifonafeResponse,
)
def completar_indemnizacion(
    id_tramite: int,
    data: schemas.ConfirmarTransicionRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    return service.completar_indemnizacion(db, current_user, id_tramite, data)


@router.post(
    "/asambleas/{id_asamblea}/completar-retiro-fondos",
    response_model=schemas.AsambleaResponse,
)
def completar_retiro_fondos(
    id_asamblea: int,
    data: schemas.ConfirmarTransicionRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    return service.completar_retiro_fondos(db, current_user, id_asamblea, data)


@router.post(
    "/convenios/{id_convenio}/activar-modificatorio",
    response_model=schemas.ConvenioResponse,
)
def activar_modificatorio(
    id_convenio: int,
    data: schemas.ConfirmarTransicionRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    return service.activar_modificatorio(db, current_user, id_convenio, data)
