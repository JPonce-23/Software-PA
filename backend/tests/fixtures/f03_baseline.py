"""Frozen territorial reads from 6e622ff; route decorators omitted only."""
from fastapi import Depends, Query
from sqlalchemy.orm import Session
from app import auth, models, schemas
from app.database import get_db
from app.services import domain as service
from app.services.access import authorized_project_ids
READ_ROLES = ["admin", "operador", "visualizador", "geografo"]

def list_states(db: Session=Depends(get_db), _: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    return db.query(models.EntidadFederativa).filter(models.EntidadFederativa.activo.is_(True)).order_by(models.EntidadFederativa.clave_inegi).all()

def list_municipalities(id_entidad: int | None=None, db: Session=Depends(get_db), _: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    query = db.query(models.Municipio).filter(models.Municipio.activo.is_(True))
    if id_entidad is not None:
        query = query.filter(models.Municipio.id_entidad == id_entidad)
    return query.order_by(models.Municipio.clave_inegi).all()

def list_ran_nuclei_catalog(id_entidad: int | None=Query(default=None, gt=0), id_municipio: int | None=Query(default=None, gt=0), q: str | None=Query(default=None, min_length=1, max_length=300), limit: int=Query(default=20, ge=1, le=100), db: Session=Depends(get_db), _: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    return service.list_ran_nuclei_catalog(db, state_id=id_entidad, municipality_id=id_municipio, name_query=q, limit=limit)

def list_nuclei(id_municipio: int | None=None, skip: int=Query(0, ge=0), limit: int=Query(100, ge=1, le=200), db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    query = db.query(models.NucleoAgrario).filter(models.NucleoAgrario.activo.is_(True))
    if user.rol != 'admin':
        query = query.join(models.ProyectoNucleo, models.ProyectoNucleo.id_nucleo == models.NucleoAgrario.id_nucleo).filter(models.ProyectoNucleo.activo.is_(True), models.ProyectoNucleo.id_proyecto.in_(authorized_project_ids(db, user))).distinct()
    if id_municipio is not None:
        query = query.filter(models.NucleoAgrario.id_municipio == id_municipio)
    return query.order_by(models.NucleoAgrario.nombre_nucleo).offset(skip).limit(limit).all()
