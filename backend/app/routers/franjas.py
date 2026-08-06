from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db
from ..services import franjas as franjas_service
from ..services.access import require_tramo_access

router = APIRouter(tags=["Franjas de Derecho de Vía"])

@router.get(
    "/tramos/{id_tramo}/franjas",
    summary="Listar historial de franjas de un tramo",
    response_model=List[schemas.FranjaDerechoViaResponse]
)
def list_franjas(
    id_tramo: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))
):
    require_tramo_access(db, current_user, id_tramo)
    return db.query(models.FranjaDerechoVia).filter(
        models.FranjaDerechoVia.id_tramo == id_tramo
    ).order_by(models.FranjaDerechoVia.version.desc()).all()


@router.post(
    "/tramos/{id_tramo}/franjas/importar",
    summary="Importar nueva versión de franja",
    response_model=schemas.FranjaDerechoViaResponse,
    status_code=status.HTTP_201_CREATED
)
def importar_franja(
    id_tramo: int,
    data: schemas.FranjaDerechoViaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'geografo']))
):
    require_tramo_access(db, current_user, id_tramo)
    return franjas_service.importar_franja(db, id_tramo, data, current_user.id_usuario)
