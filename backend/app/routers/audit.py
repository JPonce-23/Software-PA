"""Administrative read-only audit API."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services import audit as service

router = APIRouter(tags=["Auditoría"])


@router.get("/auditoria/cambios", response_model=schemas.AuditChangePageResponse)
def get_changes(id_usuario: int | None = Query(None, gt=0), id_proyecto: int | None = Query(None, gt=0), id_proyecto_nucleo: int | None = Query(None, gt=0), id_nucleo: int | None = Query(None, gt=0), entidad_tipo: str | None = Query(None, min_length=1, max_length=100), entidad_id: int | None = Query(None, gt=0), accion: str | None = Query(None, min_length=1, max_length=30), desde: datetime | None = None, hasta: datetime | None = None, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db), _: models.Usuario = Depends(auth.RoleChecker(["admin"]))):
    return service.list_changes(db, id_usuario=id_usuario, id_proyecto=id_proyecto, id_proyecto_nucleo=id_proyecto_nucleo, id_nucleo=id_nucleo, entidad_tipo=entidad_tipo, entidad_id=entidad_id, accion=accion, desde=desde, hasta=hasta, skip=skip, limit=limit)


@router.get("/auditoria/accesos", response_model=schemas.AuditAccessPageResponse)
def get_access_events(id_usuario: int | None = Query(None, gt=0), id_usuario_actor: int | None = Query(None, gt=0), tipo_evento: str | None = Query(None, min_length=1, max_length=40), motivo_codigo: str | None = Query(None, min_length=1, max_length=50), desde: datetime | None = None, hasta: datetime | None = None, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db), _: models.Usuario = Depends(auth.RoleChecker(["admin"]))):
    return service.list_access_events(db, id_usuario=id_usuario, id_usuario_actor=id_usuario_actor, tipo_evento=tipo_evento, motivo_codigo=motivo_codigo, desde=desde, hasta=hasta, skip=skip, limit=limit)
