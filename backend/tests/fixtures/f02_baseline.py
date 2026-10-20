"""F02 reference query bodies extracted from f98586e; scope follows deploy RBAC.

The query bodies/defaults retain the original authorization and read behavior,
except the explicit d73615f scope policy: only operators require assignment.
Used on synthetic data only.
"""
from fastapi import Depends, HTTPException, Query
from sqlalchemy import exists, select
from sqlalchemy.orm import Session, raiseload
from app import auth, models, schemas
from app.database import get_db
from app.services.access import AccessMode
READ_ROLES = ["admin", "operador", "visualizador", "geografo"]


def _forbidden() -> HTTPException:
    return HTTPException(status_code=403, detail='Proyecto fuera del alcance autorizado')

def authorized_project_ids(db: Session, user: models.Usuario) -> select:
    if user.rol in {'admin', 'visualizador', 'geografo'}:
        return select(models.Proyecto.id_proyecto).where(models.Proyecto.activo.is_(True))
    return select(models.UsuarioProyecto.id_proyecto).join(models.Proyecto, models.Proyecto.id_proyecto == models.UsuarioProyecto.id_proyecto).where(models.UsuarioProyecto.id_usuario == user.id_usuario, models.UsuarioProyecto.activo.is_(True), models.Proyecto.activo.is_(True))

def _role_allows(user: models.Usuario, mode: AccessMode) -> bool:
    if user.rol == 'admin':
        return True
    if mode == 'read':
        return user.rol in {'operador', 'visualizador', 'geografo'}
    if mode == 'capture':
        return user.rol == 'operador'
    return user.rol == 'geografo'

def require_project_access(db: Session, user: models.Usuario, project_id: int, *, mode: AccessMode='read', lock: bool=False, load_details: bool=True) -> models.Proyecto:
    if not _role_allows(user, mode):
        raise _forbidden()
    query = db.query(models.Proyecto).filter(models.Proyecto.id_proyecto == project_id, models.Proyecto.activo.is_(True))
    if not load_details:
        query = query.options(raiseload('*'))
    if user.rol == 'operador':
        query = query.filter(exists().where(models.UsuarioProyecto.id_usuario == user.id_usuario, models.UsuarioProyecto.id_proyecto == models.Proyecto.id_proyecto, models.UsuarioProyecto.activo.is_(True)))
    if lock:
        query = query.with_for_update(read=True).populate_existing()
    project = query.first()
    if project is None:
        raise _forbidden()
    return project

def require_project_nucleus_access(db: Session, user: models.Usuario, project_nucleus_id: int, *, mode: AccessMode='read') -> models.ProyectoNucleo:
    record = db.query(models.ProyectoNucleo).filter(models.ProyectoNucleo.id_proyecto_nucleo == project_nucleus_id, models.ProyectoNucleo.activo.is_(True)).first()
    if record is None:
        raise HTTPException(status_code=404, detail='ProyectoNucleo no encontrado')
    require_project_access(db, user, record.id_proyecto, mode=mode)
    return record

def require_affectation_access(db: Session, user: models.Usuario, affectation_id: int, *, mode: AccessMode='read') -> models.Afectacion:
    affectation = db.query(models.Afectacion).filter(models.Afectacion.id_afectacion == affectation_id, models.Afectacion.activo.is_(True)).first()
    if affectation is None:
        raise HTTPException(status_code=404, detail='Afectación no encontrada')
    require_project_nucleus_access(db, user, affectation.id_proyecto_nucleo, mode=mode)
    return affectation

def get_project(id_proyecto: int, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    return require_project_access(db, user, id_proyecto)

def list_project_nuclei(id_proyecto: int, id_entidad: int | None=None, id_municipio: int | None=None, skip: int=Query(0, ge=0), limit: int=Query(100, ge=1, le=200), db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    require_project_access(db, user, id_proyecto)
    query = db.query(models.ProyectoNucleoResumen).filter(models.ProyectoNucleoResumen.id_proyecto == id_proyecto, models.ProyectoNucleoResumen.activo.is_(True))
    if id_entidad is not None:
        query = query.filter(models.ProyectoNucleoResumen.id_entidad == id_entidad)
    if id_municipio is not None:
        query = query.filter(models.ProyectoNucleoResumen.id_municipio == id_municipio)
    return query.order_by(models.ProyectoNucleoResumen.entidad, models.ProyectoNucleoResumen.municipio, models.ProyectoNucleoResumen.nombre_nucleo).offset(skip).limit(limit).all()

def get_project_nucleus(id_proyecto_nucleo: int, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    record = db.get(models.ProyectoNucleoResumen, id_proyecto_nucleo)
    if record is None:
        raise HTTPException(status_code=404, detail='ProyectoNucleo no encontrado')
    return record

def list_references(id_proyecto_nucleo: int, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    return db.query(models.ProyectoNucleoReferencia).filter(models.ProyectoNucleoReferencia.id_proyecto_nucleo == id_proyecto_nucleo, models.ProyectoNucleoReferencia.activo.is_(True)).order_by(models.ProyectoNucleoReferencia.tipo_referencia, models.ProyectoNucleoReferencia.es_principal.desc()).all()

def list_activities(id_proyecto_nucleo: int, tipo: str | None=None, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    query = db.query(models.ActividadCampo).filter(models.ActividadCampo.id_proyecto_nucleo == id_proyecto_nucleo, models.ActividadCampo.activo.is_(True))
    if tipo is not None:
        query = query.filter(models.ActividadCampo.tipo_actividad == tipo)
    return query.order_by(models.ActividadCampo.fecha_realizada.desc().nullslast(), models.ActividadCampo.id_actividad).all()

def list_affectations(id_proyecto_nucleo: int, tipo: str | None=None, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    query = db.query(models.Afectacion).filter(models.Afectacion.id_proyecto_nucleo == id_proyecto_nucleo, models.Afectacion.activo.is_(True))
    if tipo is not None:
        query = query.filter(models.Afectacion.tipo_afectacion == tipo)
    return query.order_by(models.Afectacion.id_afectacion).all()

def list_assemblies(id_proyecto_nucleo: int, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    return db.query(models.Asamblea).filter(models.Asamblea.id_proyecto_nucleo == id_proyecto_nucleo, models.Asamblea.activo.is_(True)).order_by(models.Asamblea.id_asamblea.desc()).all()

def list_ran_procedures(id_proyecto_nucleo: int, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    require_project_nucleus_access(db, user, id_proyecto_nucleo, mode='read')
    return db.query(models.TramiteRan).filter(models.TramiteRan.id_proyecto_nucleo == id_proyecto_nucleo, models.TramiteRan.activo.is_(True)).order_by(models.TramiteRan.id_tramite_ran).all()

def list_agreements(id_afectacion: int, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    require_affectation_access(db, user, id_afectacion)
    return db.query(models.Convenio).join(models.ConvenioAfectacion).filter(models.ConvenioAfectacion.id_afectacion == id_afectacion, models.ConvenioAfectacion.activo.is_(True), models.Convenio.activo.is_(True)).order_by(models.Convenio.id_convenio).all()

def list_fifonafe(id_proyecto_nucleo: int, db: Session=Depends(get_db), user: models.Usuario=Depends(auth.RoleChecker(READ_ROLES))):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    return db.query(models.TramiteFifonafe).filter(models.TramiteFifonafe.id_proyecto_nucleo == id_proyecto_nucleo, models.TramiteFifonafe.activo.is_(True)).order_by(models.TramiteFifonafe.id_tramite_fifonafe).all()
