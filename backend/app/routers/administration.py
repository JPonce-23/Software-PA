"""Consultas y comandos exclusivos de administración territorial."""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services import administration as service


router = APIRouter(prefix="/administracion", tags=["Administración territorial"])
admin_only = auth.RoleChecker(["admin"])


@router.get("/proyectos", response_model=List[schemas.ProyectoResponse])
def list_projects(
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(admin_only),
):
    del current_user
    query = db.query(models.Proyecto)
    if not incluir_inactivos:
        query = query.filter(models.Proyecto.activo.is_(True))
    return query.order_by(models.Proyecto.clave_proyecto).all()


@router.get("/tramos", response_model=List[schemas.TramoResponse])
def list_sections(
    id_proyecto: int | None = None,
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(admin_only),
):
    del current_user
    query = db.query(
        models.Tramo.id_tramo,
        models.Tramo.id_proyecto,
        models.Tramo.clave_tramo,
        models.Tramo.nombre_tramo,
        models.Tramo.descripcion,
        models.Tramo.ancho_total_derecho_via_m,
        models.Tramo.activo,
        models.Tramo.fecha_registro,
        models.Tramo.geometria_linea.ST_AsText().label("geometria_wkt"),
    )
    if id_proyecto is not None:
        query = query.filter(models.Tramo.id_proyecto == id_proyecto)
    if not incluir_inactivos:
        query = query.filter(models.Tramo.activo.is_(True))
    return query.order_by(models.Tramo.clave_tramo).all()


@router.get("/nucleos", response_model=List[schemas.NucleoAgrarioResponse])
def list_land_units(
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(admin_only),
):
    del current_user
    query = db.query(
        models.NucleoAgrario.id_nucleo,
        models.NucleoAgrario.id_municipio,
        models.NucleoAgrario.nombre_nucleo,
        models.NucleoAgrario.tipo_nucleo,
        models.NucleoAgrario.comunidad_indigena,
        models.NucleoAgrario.residencia,
        models.NucleoAgrario.geometria_poligono.ST_AsText().label("geometria_wkt"),
        models.NucleoAgrario.activo,
        models.NucleoAgrario.observaciones,
    )
    if not incluir_inactivos:
        query = query.filter(models.NucleoAgrario.activo.is_(True))
    return query.order_by(models.NucleoAgrario.nombre_nucleo).all()


@router.get("/tramos-nucleos", response_model=List[schemas.TramoNucleoResponse])
def list_section_land_units(
    id_tramo: int | None = None,
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(admin_only),
):
    del current_user
    query = db.query(
        models.TramoNucleo.id_tramo_nucleo,
        models.TramoNucleo.id_tramo,
        models.TramoNucleo.id_nucleo,
        models.TramoNucleo.consecutivo,
        models.TramoNucleo.numero_tramo,
        models.TramoNucleo.geometria_segmento.ST_AsText().label("geometria_wkt"),
        models.TramoNucleo.longitud_m,
        models.TramoNucleo.es_expropiacion,
        models.TramoNucleo.causa_problema,
        models.TramoNucleo.proyecto_no_afecta_uso_comun,
        models.TramoNucleo.activo,
        models.TramoNucleo.observaciones,
    )
    if id_tramo is not None:
        query = query.filter(models.TramoNucleo.id_tramo == id_tramo)
    if not incluir_inactivos:
        query = query.filter(models.TramoNucleo.activo.is_(True))
    return query.order_by(
        models.TramoNucleo.id_tramo,
        models.TramoNucleo.consecutivo,
    ).all()


@router.get("/usuarios", response_model=List[schemas.UsuarioResponse])
def list_users(
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(admin_only),
):
    del current_user
    query = db.query(models.Usuario)
    if not incluir_inactivos:
        query = query.filter(models.Usuario.activo.is_(True))
    return query.order_by(models.Usuario.correo).all()


@router.get(
    "/tramos/{id_tramo}/asignaciones",
    response_model=List[schemas.AsignacionAdministrativaResponse],
)
def list_assignments(
    id_tramo: int,
    incluir_inactivas: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(admin_only),
):
    del current_user
    return service.list_tramo_assignments(
        db,
        id_tramo,
        include_inactive=incluir_inactivas,
    )


@router.put(
    "/tramos/{id_tramo}/asignaciones",
    response_model=schemas.AdministracionResumenResponse,
)
def replace_assignments(
    id_tramo: int,
    data: schemas.AsignacionesTramoReplace,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(admin_only),
):
    return service.replace_tramo_assignments(
        db,
        id_tramo=id_tramo,
        data=data,
        actor_user_id=current_user.id_usuario,
    )


_REACTIVATION_MODELS = {
    "proyectos": (models.Proyecto, "id_proyecto"),
    "tramos": (models.Tramo, "id_tramo"),
    "nucleos": (models.NucleoAgrario, "id_nucleo"),
    "tramos-nucleos": (models.TramoNucleo, "id_tramo_nucleo"),
    "usuarios": (models.Usuario, "id_usuario"),
}


@router.post("/{entity_type}/{entity_id}/reactivar")
def reactivate(
    entity_type: str,
    entity_id: int,
    data: schemas.AuthActionRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(admin_only),
):
    target = _REACTIVATION_MODELS.get(entity_type)
    if target is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Tipo de registro no encontrado")
    model, id_column = target
    service.reactivate_entity(
        db,
        model=model,
        id_column=id_column,
        entity_id=entity_id,
        actor_user_id=current_user.id_usuario,
        reason=data.motivo,
    )
    return {"detail": "Registro reactivado"}
