"""Consultas y comandos exclusivos de administración territorial."""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import literal
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services import administration as service


router = APIRouter(prefix="/administracion", tags=["Administración territorial"])
admin_only = auth.RoleChecker(["admin"])
territory_setup = auth.RoleChecker(["admin", "geografo"])


@router.get("/proyectos", response_model=List[schemas.ProyectoResponse])
def list_projects(
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(territory_setup),
):
    query = db.query(models.Proyecto)
    if current_user.rol != "admin" or not incluir_inactivos:
        query = query.filter(models.Proyecto.activo.is_(True))
    return query.order_by(models.Proyecto.clave_proyecto).all()


@router.get("/tramos", response_model=List[schemas.TramoResponse])
def list_sections(
    id_proyecto: int | None = None,
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(territory_setup),
):
    query = db.query(
        models.Tramo.id_tramo,
        models.Tramo.id_proyecto,
        models.Tramo.clave_tramo,
        models.Tramo.nombre_tramo,
        models.Tramo.descripcion,
        models.Tramo.ancho_total_derecho_via_m,
        models.Tramo.activo,
        models.Tramo.fecha_registro,
        literal(None).label("geometria_wkt"),
    )
    if id_proyecto is not None:
        query = query.filter(models.Tramo.id_proyecto == id_proyecto)
    if current_user.rol != "admin":
        query = query.join(
            models.UsuarioTramo,
            models.UsuarioTramo.id_tramo == models.Tramo.id_tramo,
        ).filter(
            models.UsuarioTramo.id_usuario == current_user.id_usuario,
            models.UsuarioTramo.activo.is_(True),
        )
    if current_user.rol != "admin" or not incluir_inactivos:
        query = query.filter(models.Tramo.activo.is_(True))
    return query.order_by(models.Tramo.clave_tramo).all()


@router.get("/nucleos", response_model=List[schemas.NucleoAgrarioResponse])
def list_land_units(
    id_proyecto: int | None = None,
    id_entidad: int | None = None,
    id_municipio: int | None = None,
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(territory_setup),
):
    query = db.query(
        models.NucleoAgrario.id_nucleo,
        models.NucleoAgrario.id_municipio,
        models.Municipio.id_entidad,
        models.Municipio.nombre.label("municipio_nombre"),
        models.EntidadFederativa.nombre.label("entidad_nombre"),
        models.NucleoAgrario.nombre_nucleo,
        models.NucleoAgrario.tipo_nucleo,
        models.NucleoAgrario.comunidad_indigena,
        models.NucleoAgrario.residencia,
        models.NucleoAgrario.geometria_poligono.ST_AsText().label("geometria_wkt"),
        models.NucleoAgrario.activo,
        models.NucleoAgrario.observaciones,
    ).join(
        models.Municipio,
        models.Municipio.id_municipio == models.NucleoAgrario.id_municipio,
    ).join(
        models.EntidadFederativa,
        models.EntidadFederativa.id_entidad == models.Municipio.id_entidad,
    )
    if id_proyecto is not None:
        query = query.filter(
            db.query(models.TramoNucleo.id_tramo_nucleo).join(
                models.Tramo,
                models.Tramo.id_tramo == models.TramoNucleo.id_tramo,
            ).filter(
                models.TramoNucleo.id_nucleo == models.NucleoAgrario.id_nucleo,
                models.TramoNucleo.activo.is_(True),
                models.Tramo.id_proyecto == id_proyecto,
                models.Tramo.activo.is_(True),
            ).exists()
        )
    if id_entidad is not None:
        query = query.filter(models.Municipio.id_entidad == id_entidad)
    if id_municipio is not None:
        query = query.filter(models.NucleoAgrario.id_municipio == id_municipio)
    if current_user.rol != "admin" or not incluir_inactivos:
        query = query.filter(models.NucleoAgrario.activo.is_(True))
    rows = query.order_by(models.NucleoAgrario.nombre_nucleo).all()
    projects_by_nucleo: dict[int, list[schemas.ProyectoResumen]] = {}
    if rows:
        nucleus_ids = [row.id_nucleo for row in rows]
        project_rows = db.query(
            models.TramoNucleo.id_nucleo,
            models.Proyecto.id_proyecto,
            models.Proyecto.clave_proyecto,
            models.Proyecto.nombre_proyecto,
        ).join(
            models.Tramo,
            models.Tramo.id_tramo == models.TramoNucleo.id_tramo,
        ).join(
            models.Proyecto,
            models.Proyecto.id_proyecto == models.Tramo.id_proyecto,
        ).filter(
            models.TramoNucleo.id_nucleo.in_(nucleus_ids),
            models.TramoNucleo.activo.is_(True),
            models.Tramo.activo.is_(True),
            models.Proyecto.activo.is_(True),
        ).distinct().order_by(models.Proyecto.clave_proyecto).all()
        for project in project_rows:
            projects_by_nucleo.setdefault(project.id_nucleo, []).append(
                schemas.ProyectoResumen(
                    id_proyecto=project.id_proyecto,
                    clave_proyecto=project.clave_proyecto,
                    nombre_proyecto=project.nombre_proyecto,
                )
            )
    return [
        {
            **row._asdict(),
            "proyectos_territoriales": projects_by_nucleo.get(row.id_nucleo, []),
        }
        for row in rows
    ]


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
