"""REST API for the ProyectoNucleo administrative domain."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services import domain as service
from ..services.access import (
    authorized_project_ids,
    filter_projects_by_user,
    require_affectation_access,
    require_agreement_access,
    require_assembly_access,
    require_fifonafe_access,
    require_indemnity_access,
    require_nucleus_access,
    require_parcel_access,
    require_payment_access,
    require_project_access,
    require_project_nucleus_access,
)


router = APIRouter()
READ_ROLES = ["admin", "operador", "visualizador", "geografo"]
CAPTURE_ROLES = ["admin", "operador"]
GIS_ROLES = ["admin", "geografo"]


def _active_or_404(db: Session, model, pk, value: int, detail: str):
    entity = db.query(model).filter(pk == value, model.activo.is_(True)).first()
    if entity is None:
        raise HTTPException(status_code=404, detail=detail)
    return entity


@router.get("/catalogos/entidades", response_model=list[schemas.EntidadFederativaResponse])
def list_states(
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return db.query(models.EntidadFederativa).filter(
        models.EntidadFederativa.activo.is_(True)
    ).order_by(models.EntidadFederativa.clave_inegi).all()


@router.get("/catalogos/municipios", response_model=list[schemas.MunicipioResponse])
def list_municipalities(
    id_entidad: int | None = None,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.Municipio).filter(models.Municipio.activo.is_(True))
    if id_entidad is not None:
        query = query.filter(models.Municipio.id_entidad == id_entidad)
    return query.order_by(models.Municipio.clave_inegi).all()


@router.get(
    "/catalogos/operativos/{tipo_catalogo}",
    response_model=list[schemas.CatalogoOperativoResponse],
)
def list_operational_catalog(
    tipo_catalogo: str,
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.CatalogoOperativo).filter(
        models.CatalogoOperativo.tipo_catalogo == tipo_catalogo
    )
    if not incluir_inactivos:
        query = query.filter(models.CatalogoOperativo.activo.is_(True))
    return query.order_by(
        models.CatalogoOperativo.activo.desc(),
        models.CatalogoOperativo.orden,
        models.CatalogoOperativo.nombre,
    ).all()


@router.post(
    "/catalogos/operativos",
    response_model=schemas.CatalogoOperativoResponse,
    status_code=201,
)
def create_operational_catalog_option(
    data: schemas.CatalogoOperativoCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    return service.create_catalog_option(db, data, user)


@router.patch(
    "/catalogos/operativos/opciones/{id_catalogo_opcion}",
    response_model=schemas.CatalogoOperativoResponse,
)
def update_operational_catalog_option(
    id_catalogo_opcion: int,
    data: schemas.CatalogoOperativoUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    entity = db.query(models.CatalogoOperativo).filter(
        models.CatalogoOperativo.id_catalogo_opcion == id_catalogo_opcion
    ).first()
    if entity is None:
        raise HTTPException(status_code=404, detail="Opción de catálogo no encontrada")
    return service.update_catalog_option(db, entity, data, user)


@router.get("/proyectos", response_model=list[schemas.ProyectoResponse])
def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.Proyecto).filter(models.Proyecto.activo.is_(True))
    query = filter_projects_by_user(query, db, user)
    return query.order_by(models.Proyecto.nombre_proyecto).offset(skip).limit(limit).all()


@router.post("/proyectos", response_model=schemas.ProyectoResponse, status_code=201)
def create_project(
    data: schemas.ProyectoCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    return service.create_project(db, data, user)


@router.get("/proyectos/{id_proyecto}", response_model=schemas.ProyectoResponse)
def get_project(
    id_proyecto: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return require_project_access(db, user, id_proyecto)


@router.patch("/proyectos/{id_proyecto}", response_model=schemas.ProyectoResponse)
def update_project(
    id_proyecto: int,
    data: schemas.ProyectoUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    project = require_project_access(db, user, id_proyecto)
    return service.update_entity(db, project, data, user)


@router.delete("/proyectos/{id_proyecto}", response_model=schemas.AuthOperationResponse)
def delete_project(
    id_proyecto: int,
    data: schemas.BajaRequest,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    project = require_project_access(db, user, id_proyecto)
    service.logical_delete(db, project, user.id_usuario, data.motivo)
    return {"detail": "Proyecto dado de baja"}


@router.get("/nucleos", response_model=list[schemas.NucleoAgrarioResponse])
def list_nuclei(
    id_municipio: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.NucleoAgrario).filter(
        models.NucleoAgrario.activo.is_(True)
    )
    if user.rol != "admin":
        query = query.join(
            models.ProyectoNucleo,
            models.ProyectoNucleo.id_nucleo == models.NucleoAgrario.id_nucleo,
        ).filter(
            models.ProyectoNucleo.activo.is_(True),
            models.ProyectoNucleo.id_proyecto.in_(authorized_project_ids(db, user)),
        ).distinct()
    if id_municipio is not None:
        query = query.filter(models.NucleoAgrario.id_municipio == id_municipio)
    return query.order_by(models.NucleoAgrario.nombre_nucleo).offset(skip).limit(limit).all()


@router.post("/nucleos", response_model=schemas.NucleoAgrarioResponse, status_code=201)
def create_nucleus(
    data: schemas.NucleoAgrarioCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    return service.create_nucleus(db, data, user)


@router.get("/nucleos/{id_nucleo}", response_model=schemas.NucleoAgrarioResponse)
def get_nucleus(
    id_nucleo: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    nucleus = require_nucleus_access(db, user, id_nucleo)
    geometry = db.query(func.ST_AsText(models.NucleoAgrario.geometria_poligono)).filter(
        models.NucleoAgrario.id_nucleo == id_nucleo
    ).scalar()
    result = schemas.NucleoAgrarioResponse.model_validate(nucleus).model_dump()
    result["geometria_wkt"] = geometry
    return result


@router.patch("/nucleos/{id_nucleo}", response_model=schemas.NucleoAgrarioResponse)
def update_nucleus(
    id_nucleo: int,
    data: schemas.NucleoAgrarioUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    nucleus = require_nucleus_access(db, user, id_nucleo, mode="capture")
    return service.update_nucleus(db, nucleus, data, user)


@router.patch(
    "/nucleos/{id_nucleo}/geometria",
    response_model=schemas.NucleoAgrarioResponse,
)
def update_nucleus_geometry(
    id_nucleo: int,
    data: schemas.GeometriaPoligonoUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(GIS_ROLES)),
):
    nucleus = require_nucleus_access(db, user, id_nucleo, mode="gis")
    return service.update_nucleus_geometry(db, nucleus, data, user)


@router.get(
    "/proyectos/{id_proyecto}/nucleos",
    response_model=list[schemas.ProyectoNucleoResponse],
)
def list_project_nuclei(
    id_proyecto: int,
    id_entidad: int | None = None,
    id_municipio: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_project_access(db, user, id_proyecto)
    query = db.query(models.ProyectoNucleoResumen).filter(
        models.ProyectoNucleoResumen.id_proyecto == id_proyecto,
        models.ProyectoNucleoResumen.activo.is_(True),
    )
    if id_entidad is not None:
        query = query.filter(models.ProyectoNucleoResumen.id_entidad == id_entidad)
    if id_municipio is not None:
        query = query.filter(
            models.ProyectoNucleoResumen.id_municipio == id_municipio
        )
    return query.order_by(
        models.ProyectoNucleoResumen.entidad,
        models.ProyectoNucleoResumen.municipio,
        models.ProyectoNucleoResumen.nombre_nucleo,
    ).offset(skip).limit(limit).all()


@router.post(
    "/proyectos/{id_proyecto}/nucleos",
    response_model=schemas.ProyectoNucleoResponse,
    status_code=201,
)
def create_project_nucleus(
    id_proyecto: int,
    data: schemas.ProyectoNucleoCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    record = service.create_project_nucleus(db, id_proyecto, data, user)
    return db.get(models.ProyectoNucleoResumen, record.id_proyecto_nucleo)


@router.get(
    "/proyecto-nucleo/{id_proyecto_nucleo}",
    response_model=schemas.ProyectoNucleoResponse,
)
def get_project_nucleus(
    id_proyecto_nucleo: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    record = db.get(models.ProyectoNucleoResumen, id_proyecto_nucleo)
    if record is None:
        raise HTTPException(status_code=404, detail="ProyectoNucleo no encontrado")
    return record


@router.patch(
    "/proyecto-nucleo/{id_proyecto_nucleo}",
    response_model=schemas.ProyectoNucleoResponse,
)
def update_project_nucleus(
    id_proyecto_nucleo: int,
    data: schemas.ProyectoNucleoUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    record = require_project_nucleus_access(
        db, user, id_proyecto_nucleo, mode="capture"
    )
    service.update_project_nucleus(db, record, data, user)
    return db.get(models.ProyectoNucleoResumen, id_proyecto_nucleo)


@router.delete(
    "/proyecto-nucleo/{id_proyecto_nucleo}",
    response_model=schemas.AuthOperationResponse,
)
def delete_project_nucleus(
    id_proyecto_nucleo: int,
    data: schemas.BajaRequest,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    record = require_project_nucleus_access(
        db, user, id_proyecto_nucleo, mode="capture"
    )
    service.logical_delete(db, record, user.id_usuario, data.motivo)
    return {"detail": "ProyectoNucleo dado de baja"}


@router.get(
    "/proyecto-nucleo/{id_proyecto_nucleo}/referencias",
    response_model=list[schemas.ProyectoNucleoReferenciaResponse],
)
def list_references(
    id_proyecto_nucleo: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    return db.query(models.ProyectoNucleoReferencia).filter(
        models.ProyectoNucleoReferencia.id_proyecto_nucleo
        == id_proyecto_nucleo,
        models.ProyectoNucleoReferencia.activo.is_(True),
    ).order_by(
        models.ProyectoNucleoReferencia.tipo_referencia,
        models.ProyectoNucleoReferencia.es_principal.desc(),
    ).all()


@router.post(
    "/proyecto-nucleo/{id_proyecto_nucleo}/referencias",
    response_model=schemas.ProyectoNucleoReferenciaResponse,
    status_code=201,
)
def add_reference(
    id_proyecto_nucleo: int,
    data: schemas.ProyectoNucleoReferenciaCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.add_reference(db, id_proyecto_nucleo, data, user)


@router.patch(
    "/referencias/{id_referencia}",
    response_model=schemas.ProyectoNucleoReferenciaResponse,
)
def update_reference(
    id_referencia: int,
    data: schemas.ProyectoNucleoReferenciaUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = _active_or_404(
        db, models.ProyectoNucleoReferencia,
        models.ProyectoNucleoReferencia.id_referencia,
        id_referencia, "Referencia no encontrada",
    )
    require_project_nucleus_access(
        db, user, entity.id_proyecto_nucleo, mode="capture"
    )
    return service.update_entity(db, entity, data, user)


@router.get(
    "/proyecto-nucleo/{id_proyecto_nucleo}/responsables",
    response_model=list[schemas.ProyectoNucleoResponsableResponse],
)
def list_responsibles(
    id_proyecto_nucleo: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    return db.query(models.ProyectoNucleoResponsable).filter(
        models.ProyectoNucleoResponsable.id_proyecto_nucleo == id_proyecto_nucleo,
        models.ProyectoNucleoResponsable.activo.is_(True),
    ).order_by(
        models.ProyectoNucleoResponsable.es_principal.desc(),
        models.ProyectoNucleoResponsable.vigencia_inicio.desc().nullslast(),
    ).all()


@router.post(
    "/proyecto-nucleo/{id_proyecto_nucleo}/responsables",
    response_model=schemas.ProyectoNucleoResponsableResponse,
    status_code=201,
)
def create_responsible(
    id_proyecto_nucleo: int,
    data: schemas.ProyectoNucleoResponsableCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_responsible(db, id_proyecto_nucleo, data, user)


@router.patch(
    "/responsables/{id_responsable}",
    response_model=schemas.ProyectoNucleoResponsableResponse,
)
def update_responsible(
    id_responsable: int,
    data: schemas.ProyectoNucleoResponsableUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = _active_or_404(
        db, models.ProyectoNucleoResponsable,
        models.ProyectoNucleoResponsable.id_responsable,
        id_responsable, "Responsable no encontrado",
    )
    require_project_nucleus_access(db, user, entity.id_proyecto_nucleo, mode="capture")
    return service.update_entity(db, entity, data, user)


@router.post(
    "/proyectos/{id_proyecto}/personas",
    response_model=schemas.PersonaResponse,
    status_code=201,
)
def create_person(
    id_proyecto: int,
    data: schemas.PersonaCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    require_project_access(db, user, id_proyecto, mode="capture")
    return service.create_person(db, data, user)


@router.get(
    "/proyecto-nucleo/{id_proyecto_nucleo}/orv",
    response_model=list[schemas.OrvResponse],
)
def list_orv(
    id_proyecto_nucleo: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    pn = require_project_nucleus_access(db, user, id_proyecto_nucleo)
    return db.query(models.Orv).filter(
        models.Orv.id_nucleo == pn.id_nucleo,
        models.Orv.activo.is_(True),
    ).order_by(models.Orv.inicio_vigencia.desc().nullslast()).all()


@router.post(
    "/proyecto-nucleo/{id_proyecto_nucleo}/orv",
    response_model=schemas.OrvResponse,
    status_code=201,
)
def create_orv(
    id_proyecto_nucleo: int,
    data: schemas.OrvCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_orv(db, id_proyecto_nucleo, data, user)


@router.patch("/orv/{id_orv}", response_model=schemas.OrvResponse)
def update_orv(
    id_orv: int,
    data: schemas.OrvUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = _active_or_404(db, models.Orv, models.Orv.id_orv, id_orv, "ORV no encontrado")
    require_nucleus_access(db, user, entity.id_nucleo, mode="capture")
    return service.update_orv(db, entity, data, user)


@router.post(
    "/orv/{id_orv}/integrantes",
    response_model=schemas.OrvIntegranteResponse,
    status_code=201,
)
def add_orv_member(
    id_orv: int,
    data: schemas.OrvIntegranteCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    orv = _active_or_404(db, models.Orv, models.Orv.id_orv, id_orv, "ORV no encontrado")
    require_nucleus_access(db, user, orv.id_nucleo, mode="capture")
    return service.add_orv_member(db, orv, data, user)


@router.get(
    "/orv/{id_orv}/integrantes",
    response_model=list[schemas.OrvIntegranteDetailResponse],
)
def list_orv_members(
    id_orv: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    orv = _active_or_404(db, models.Orv, models.Orv.id_orv, id_orv, "ORV no encontrado")
    require_nucleus_access(db, user, orv.id_nucleo)
    rows = db.query(models.OrvIntegrante, models.Persona).join(
        models.Persona, models.Persona.id_persona == models.OrvIntegrante.id_persona
    ).filter(
        models.OrvIntegrante.id_orv == id_orv,
        models.OrvIntegrante.activo.is_(True),
        models.Persona.activo.is_(True),
    ).order_by(models.OrvIntegrante.cargo, models.Persona.nombre).all()
    return [
        {
            **schemas.OrvIntegranteResponse.model_validate(link).model_dump(),
            "nombre": person.nombre,
            "apellido_paterno": person.apellido_paterno,
            "apellido_materno": person.apellido_materno,
            "telefono": person.telefono,
            "correo_electronico": person.correo_electronico,
        }
        for link, person in rows
    ]


@router.patch(
    "/orv-integrantes/{id_orv_integrante}",
    response_model=schemas.OrvIntegranteResponse,
)
def update_orv_member(
    id_orv_integrante: int,
    data: schemas.OrvIntegranteUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = _active_or_404(
        db, models.OrvIntegrante, models.OrvIntegrante.id_orv_integrante,
        id_orv_integrante, "Integrante ORV no encontrado",
    )
    orv = _active_or_404(db, models.Orv, models.Orv.id_orv, entity.id_orv, "ORV no encontrado")
    require_nucleus_access(db, user, orv.id_nucleo, mode="capture")
    return service.update_entity(db, entity, data, user)


@router.get(
    "/proyecto-nucleo/{id_proyecto_nucleo}/padrones",
    response_model=list[schemas.PadronHistorialResponse],
)
def list_registers(
    id_proyecto_nucleo: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    pn = require_project_nucleus_access(db, user, id_proyecto_nucleo)
    return db.query(models.PadronHistorial).filter(
        models.PadronHistorial.id_nucleo == pn.id_nucleo,
        models.PadronHistorial.activo.is_(True),
    ).order_by(models.PadronHistorial.fecha_padron.desc().nullslast()).all()


@router.post(
    "/proyecto-nucleo/{id_proyecto_nucleo}/padrones",
    response_model=schemas.PadronHistorialResponse,
    status_code=201,
)
def create_register(
    id_proyecto_nucleo: int,
    data: schemas.PadronHistorialCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_register(db, id_proyecto_nucleo, data, user)


@router.patch("/padrones/{id_padron}", response_model=schemas.PadronHistorialResponse)
def update_register(
    id_padron: int,
    data: schemas.PadronHistorialUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = _active_or_404(
        db, models.PadronHistorial, models.PadronHistorial.id_padron,
        id_padron, "Padrón no encontrado",
    )
    require_nucleus_access(db, user, entity.id_nucleo, mode="capture")
    return service.update_entity(db, entity, data, user)


@router.get(
    "/proyecto-nucleo/{id_proyecto_nucleo}/actividades",
    response_model=list[schemas.ActividadCampoResponse],
)
def list_activities(
    id_proyecto_nucleo: int,
    tipo: str | None = None,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    query = db.query(models.ActividadCampo).filter(
        models.ActividadCampo.id_proyecto_nucleo == id_proyecto_nucleo,
        models.ActividadCampo.activo.is_(True),
    )
    if tipo is not None:
        query = query.filter(models.ActividadCampo.tipo_actividad == tipo)
    return query.order_by(
        models.ActividadCampo.fecha_realizada.desc().nullslast(),
        models.ActividadCampo.id_actividad,
    ).all()


@router.post(
    "/proyecto-nucleo/{id_proyecto_nucleo}/actividades",
    response_model=schemas.ActividadCampoResponse,
    status_code=201,
)
def create_activity(
    id_proyecto_nucleo: int,
    data: schemas.ActividadCampoCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_activity(db, id_proyecto_nucleo, data, user)


@router.patch("/actividades/{id_actividad}", response_model=schemas.ActividadCampoResponse)
def update_activity(
    id_actividad: int,
    data: schemas.ActividadCampoUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = _active_or_404(
        db, models.ActividadCampo, models.ActividadCampo.id_actividad,
        id_actividad, "Actividad no encontrada"
    )
    require_project_nucleus_access(db, user, entity.id_proyecto_nucleo, mode="capture")
    return service.update_entity(db, entity, data, user)


@router.get(
    "/proyecto-nucleo/{id_proyecto_nucleo}/parcelas",
    response_model=list[schemas.ParcelaResponse],
)
def list_parcels(
    id_proyecto_nucleo: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    pn = require_project_nucleus_access(db, user, id_proyecto_nucleo)
    return db.query(models.Parcela).filter(
        models.Parcela.id_nucleo == pn.id_nucleo,
        models.Parcela.activo.is_(True),
    ).order_by(models.Parcela.no_parcela.nullslast(), models.Parcela.id_parcela).all()


@router.post(
    "/proyecto-nucleo/{id_proyecto_nucleo}/parcelas",
    response_model=schemas.ParcelaResponse,
    status_code=201,
)
def create_parcel(
    id_proyecto_nucleo: int,
    data: schemas.ParcelaCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_parcel(db, id_proyecto_nucleo, data, user)


@router.get("/parcelas/{id_parcela}", response_model=schemas.ParcelaResponse)
def get_parcel(
    id_parcela: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    parcel = require_parcel_access(db, user, id_parcela)
    geometry = db.query(func.ST_AsText(models.Parcela.geometria_poligono)).filter(
        models.Parcela.id_parcela == id_parcela
    ).scalar()
    result = schemas.ParcelaResponse.model_validate(parcel).model_dump()
    result["geometria_wkt"] = geometry
    return result


@router.patch("/parcelas/{id_parcela}", response_model=schemas.ParcelaResponse)
def update_parcel(
    id_parcela: int,
    data: schemas.ParcelaUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    parcel = require_parcel_access(db, user, id_parcela, mode="capture")
    return service.update_entity(db, parcel, data, user)


@router.patch(
    "/parcelas/{id_parcela}/geometria",
    response_model=schemas.ParcelaResponse,
)
def update_parcel_geometry(
    id_parcela: int,
    data: schemas.GeometriaPoligonoUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(GIS_ROLES)),
):
    parcel = require_parcel_access(db, user, id_parcela, mode="gis")
    return service.update_parcel_geometry(db, parcel, data, user)


@router.get(
    "/parcelas/{id_parcela}/titulares",
    response_model=list[schemas.ParcelaTitularDetailResponse],
)
def list_parcel_holders(
    id_parcela: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_parcel_access(db, user, id_parcela)
    rows = db.query(models.ParcelaTitular, models.Persona).join(
        models.Persona, models.Persona.id_persona == models.ParcelaTitular.id_persona
    ).filter(
        models.ParcelaTitular.id_parcela == id_parcela,
        models.ParcelaTitular.activo.is_(True),
        models.Persona.activo.is_(True),
    ).order_by(models.Persona.nombre, models.ParcelaTitular.id_parcela_titular).all()
    return [
        {
            **schemas.ParcelaTitularResponse.model_validate(link).model_dump(),
            "nombre": person.nombre,
            "apellido_paterno": person.apellido_paterno,
            "apellido_materno": person.apellido_materno,
            "telefono": person.telefono,
            "correo_electronico": person.correo_electronico,
        }
        for link, person in rows
    ]


@router.post(
    "/parcelas/{id_parcela}/titulares",
    response_model=schemas.ParcelaTitularResponse,
    status_code=201,
)
def add_parcel_holder(
    id_parcela: int,
    data: schemas.ParcelaTitularCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    parcel = require_parcel_access(db, user, id_parcela, mode="capture")
    return service.add_parcel_holder(db, parcel, data, user)


@router.patch(
    "/parcela-titulares/{id_parcela_titular}",
    response_model=schemas.ParcelaTitularResponse,
)
def update_parcel_holder(
    id_parcela_titular: int,
    data: schemas.ParcelaTitularUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = _active_or_404(
        db, models.ParcelaTitular, models.ParcelaTitular.id_parcela_titular,
        id_parcela_titular, "Titular de parcela no encontrado",
    )
    require_parcel_access(db, user, entity.id_parcela, mode="capture")
    return service.update_entity(db, entity, data, user)


@router.get(
    "/proyecto-nucleo/{id_proyecto_nucleo}/afectaciones",
    response_model=list[schemas.AfectacionResponse],
)
def list_affectations(
    id_proyecto_nucleo: int,
    tipo: str | None = None,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    query = db.query(models.Afectacion).filter(
        models.Afectacion.id_proyecto_nucleo == id_proyecto_nucleo,
        models.Afectacion.activo.is_(True),
    )
    if tipo is not None:
        query = query.filter(models.Afectacion.tipo_afectacion == tipo)
    return query.order_by(models.Afectacion.id_afectacion).all()


@router.post(
    "/proyecto-nucleo/{id_proyecto_nucleo}/afectaciones",
    response_model=schemas.AfectacionResponse,
    status_code=201,
)
def create_affectation(
    id_proyecto_nucleo: int,
    data: schemas.AfectacionCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_affectation(db, id_proyecto_nucleo, data, user)


@router.get("/afectaciones/{id_afectacion}", response_model=schemas.AfectacionResponse)
def get_affectation(
    id_afectacion: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return require_affectation_access(db, user, id_afectacion)


@router.patch("/afectaciones/{id_afectacion}", response_model=schemas.AfectacionResponse)
def update_affectation(
    id_afectacion: int,
    data: schemas.AfectacionUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = require_affectation_access(db, user, id_afectacion, mode="capture")
    return service.update_entity(db, entity, data, user)


@router.delete("/afectaciones/{id_afectacion}", response_model=schemas.AuthOperationResponse)
def delete_affectation(
    id_afectacion: int,
    data: schemas.BajaRequest,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = require_affectation_access(db, user, id_afectacion, mode="capture")
    service.logical_delete(db, entity, user.id_usuario, data.motivo)
    return {"detail": "Afectación dada de baja"}


@router.get(
    "/afectaciones/{id_afectacion}/bienes",
    response_model=list[schemas.BienAfectadoResponse],
)
def list_affected_assets(
    id_afectacion: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_affectation_access(db, user, id_afectacion)
    return db.query(models.BienAfectado).filter(
        models.BienAfectado.id_afectacion == id_afectacion,
        models.BienAfectado.activo.is_(True),
    ).order_by(models.BienAfectado.id_bien_afectado).all()


@router.post(
    "/afectaciones/{id_afectacion}/bienes",
    response_model=schemas.BienAfectadoResponse,
    status_code=201,
)
def create_affected_asset(
    id_afectacion: int,
    data: schemas.BienAfectadoCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_affected_asset(db, id_afectacion, data, user)


@router.patch(
    "/bienes-afectados/{id_bien_afectado}",
    response_model=schemas.BienAfectadoResponse,
)
def update_affected_asset(
    id_bien_afectado: int,
    data: schemas.BienAfectadoUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = _active_or_404(
        db, models.BienAfectado, models.BienAfectado.id_bien_afectado,
        id_bien_afectado, "Bien afectado no encontrado",
    )
    require_affectation_access(db, user, entity.id_afectacion, mode="capture")
    return service.update_entity(db, entity, data, user)


@router.get(
    "/proyecto-nucleo/{id_proyecto_nucleo}/asambleas",
    response_model=list[schemas.AsambleaResponse],
)
def list_assemblies(
    id_proyecto_nucleo: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    return db.query(models.Asamblea).filter(
        models.Asamblea.id_proyecto_nucleo == id_proyecto_nucleo,
        models.Asamblea.activo.is_(True),
    ).order_by(models.Asamblea.fecha_realizada.desc().nullslast()).all()


@router.post(
    "/proyecto-nucleo/{id_proyecto_nucleo}/asambleas",
    response_model=schemas.AsambleaResponse,
    status_code=201,
)
def create_assembly(
    id_proyecto_nucleo: int,
    data: schemas.AsambleaCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_assembly(db, id_proyecto_nucleo, data, user)


@router.patch("/asambleas/{id_asamblea}", response_model=schemas.AsambleaResponse)
def update_assembly(
    id_asamblea: int,
    data: schemas.AsambleaUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = require_assembly_access(db, user, id_asamblea, mode="capture")
    return service.update_assembly(db, entity, data, user)


@router.get(
    "/asambleas/{id_asamblea}/convocatorias",
    response_model=list[schemas.AsambleaConvocatoriaResponse],
)
def list_convocations(
    id_asamblea: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_assembly_access(db, user, id_asamblea)
    return db.query(models.AsambleaConvocatoria).filter(
        models.AsambleaConvocatoria.id_asamblea == id_asamblea,
        models.AsambleaConvocatoria.activo.is_(True),
    ).order_by(models.AsambleaConvocatoria.ordinal).all()


@router.post(
    "/asambleas/{id_asamblea}/convocatorias",
    response_model=schemas.AsambleaConvocatoriaResponse,
    status_code=201,
)
def add_convocation(
    id_asamblea: int,
    data: schemas.AsambleaConvocatoriaCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.add_convocation(db, id_asamblea, data, user)


@router.patch(
    "/convocatorias/{id_convocatoria}",
    response_model=schemas.AsambleaConvocatoriaResponse,
)
def update_convocation(
    id_convocatoria: int,
    data: schemas.AsambleaConvocatoriaUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = _active_or_404(
        db, models.AsambleaConvocatoria, models.AsambleaConvocatoria.id_convocatoria,
        id_convocatoria, "Convocatoria no encontrada",
    )
    require_assembly_access(db, user, entity.id_asamblea, mode="capture")
    return service.update_entity(db, entity, data, user)


@router.get(
    "/proyecto-nucleo/{id_proyecto_nucleo}/tramites-ran",
    response_model=list[schemas.TramiteRanResponse],
)
def list_ran_procedures(
    id_proyecto_nucleo: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    return db.query(models.TramiteRan).filter(
        models.TramiteRan.id_proyecto_nucleo == id_proyecto_nucleo,
        models.TramiteRan.activo.is_(True),
    ).order_by(models.TramiteRan.id_tramite_ran).all()


@router.post(
    "/proyecto-nucleo/{id_proyecto_nucleo}/tramites-ran",
    response_model=schemas.TramiteRanResponse,
    status_code=201,
)
def create_ran_procedure(
    id_proyecto_nucleo: int,
    data: schemas.TramiteRanCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_ran_procedure(db, id_proyecto_nucleo, data, user)


@router.post(
    "/tramites-ran/{id_tramite_ran}/eventos",
    response_model=schemas.TramiteRanEventoResponse,
    status_code=201,
)
def add_ran_event(
    id_tramite_ran: int,
    data: schemas.TramiteRanEventoCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    procedure = _active_or_404(
        db, models.TramiteRan, models.TramiteRan.id_tramite_ran,
        id_tramite_ran, "Trámite RAN no encontrado",
    )
    return service.add_ran_event(db, procedure, data, user)


@router.patch(
    "/eventos-ran/{id_evento_ran}",
    response_model=schemas.TramiteRanEventoResponse,
)
def update_ran_event(
    id_evento_ran: int,
    data: schemas.TramiteRanEventoUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = _active_or_404(
        db, models.TramiteRanEvento, models.TramiteRanEvento.id_evento_ran,
        id_evento_ran, "Evento RAN no encontrado",
    )
    require_project_nucleus_access(db, user, entity.tramite.id_proyecto_nucleo, mode="capture")
    return service.update_entity(db, entity, data, user)


@router.get(
    "/afectaciones/{id_afectacion}/convenios",
    response_model=list[schemas.ConvenioResponse],
)
def list_agreements(
    id_afectacion: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_affectation_access(db, user, id_afectacion)
    return db.query(models.Convenio).join(models.ConvenioAfectacion).filter(
        models.ConvenioAfectacion.id_afectacion == id_afectacion,
        models.ConvenioAfectacion.activo.is_(True),
        models.Convenio.activo.is_(True),
    ).order_by(models.Convenio.id_convenio).all()


@router.post(
    "/afectaciones/{id_afectacion}/convenios",
    response_model=schemas.ConvenioResponse,
    status_code=201,
)
def create_agreement(
    id_afectacion: int,
    data: schemas.ConvenioCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_agreement(db, id_afectacion, data, user)


@router.get("/convenios/{id_convenio}", response_model=schemas.ConvenioResponse)
def get_agreement(
    id_convenio: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return require_agreement_access(db, user, id_convenio)


@router.patch("/convenios/{id_convenio}", response_model=schemas.ConvenioResponse)
def update_agreement(
    id_convenio: int,
    data: schemas.ConvenioUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = require_agreement_access(db, user, id_convenio, mode="capture")
    return service.update_entity(db, entity, data, user)


@router.post(
    "/convenios/{id_convenio}/afectaciones",
    response_model=schemas.ConvenioAfectacionResponse,
    status_code=201,
)
def add_agreement_affectation(
    id_convenio: int,
    data: schemas.ConvenioAfectacionCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.add_agreement_affectation(
        db, id_convenio, data.id_afectacion, user
    )


@router.get(
    "/proyecto-nucleo/{id_proyecto_nucleo}/fifonafe",
    response_model=list[schemas.TramiteFifonafeResponse],
)
def list_fifonafe(
    id_proyecto_nucleo: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    return db.query(models.TramiteFifonafe).filter(
        models.TramiteFifonafe.id_proyecto_nucleo == id_proyecto_nucleo,
        models.TramiteFifonafe.activo.is_(True),
    ).order_by(models.TramiteFifonafe.id_tramite_fifonafe).all()


@router.post(
    "/proyecto-nucleo/{id_proyecto_nucleo}/fifonafe",
    response_model=schemas.TramiteFifonafeResponse,
    status_code=201,
)
def create_fifonafe(
    id_proyecto_nucleo: int,
    data: schemas.TramiteFifonafeCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_fifonafe(db, id_proyecto_nucleo, data, user)


@router.patch(
    "/fifonafe/{id_tramite_fifonafe}",
    response_model=schemas.TramiteFifonafeResponse,
)
def update_fifonafe(
    id_tramite_fifonafe: int,
    data: schemas.TramiteFifonafeUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = require_fifonafe_access(
        db, user, id_tramite_fifonafe, mode="capture"
    )
    return service.update_entity(db, entity, data, user)


@router.post(
    "/fifonafe/{id_tramite_fifonafe}/afectaciones",
    response_model=schemas.TramiteFifonafeAfectacionResponse,
    status_code=201,
)
def add_fifonafe_affectation(
    id_tramite_fifonafe: int,
    data: schemas.ConvenioAfectacionCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.add_fifonafe_affectation(
        db, id_tramite_fifonafe, data.id_afectacion, user
    )


@router.get(
    "/fifonafe/{id_tramite_fifonafe}/eventos",
    response_model=list[schemas.TramiteFifonafeEventoResponse],
)
def list_fifonafe_events(
    id_tramite_fifonafe: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_fifonafe_access(db, user, id_tramite_fifonafe)
    return db.query(models.TramiteFifonafeEvento).filter(
        models.TramiteFifonafeEvento.id_tramite_fifonafe == id_tramite_fifonafe,
        models.TramiteFifonafeEvento.activo.is_(True),
    ).order_by(models.TramiteFifonafeEvento.ordinal).all()


@router.post(
    "/fifonafe/{id_tramite_fifonafe}/eventos",
    response_model=schemas.TramiteFifonafeEventoResponse,
    status_code=201,
)
def add_fifonafe_event(
    id_tramite_fifonafe: int,
    data: schemas.TramiteFifonafeEventoCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    procedure = require_fifonafe_access(db, user, id_tramite_fifonafe, mode="capture")
    return service.add_fifonafe_event(db, procedure, data, user)


@router.get(
    "/catalogos/requisitos-documentales",
    response_model=list[schemas.RequisitoDocumentalResponse],
)
def list_document_requirements(
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.RequisitoDocumental)
    if not incluir_inactivos:
        query = query.filter(models.RequisitoDocumental.activo.is_(True))
    return query.order_by(models.RequisitoDocumental.contexto, models.RequisitoDocumental.orden).all()


@router.get(
    "/proyecto-nucleo/{id_proyecto_nucleo}/requisitos-documentales",
    response_model=list[schemas.ExpedienteRequisitoResponse],
)
def list_project_document_requirements(
    id_proyecto_nucleo: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_project_nucleus_access(db, user, id_proyecto_nucleo)
    return db.query(models.ExpedienteRequisito).filter(
        models.ExpedienteRequisito.id_proyecto_nucleo == id_proyecto_nucleo,
        models.ExpedienteRequisito.activo.is_(True),
    ).order_by(models.ExpedienteRequisito.id_expediente_requisito).all()


@router.post(
    "/proyecto-nucleo/{id_proyecto_nucleo}/requisitos-documentales",
    response_model=schemas.ExpedienteRequisitoResponse,
    status_code=201,
)
def create_project_document_requirement(
    id_proyecto_nucleo: int,
    data: schemas.ExpedienteRequisitoCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_document_requirement(db, id_proyecto_nucleo, data, user)


@router.patch(
    "/requisitos-documentales/{id_expediente_requisito}",
    response_model=schemas.ExpedienteRequisitoResponse,
)
def update_project_document_requirement(
    id_expediente_requisito: int,
    data: schemas.ExpedienteRequisitoUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = _active_or_404(
        db, models.ExpedienteRequisito,
        models.ExpedienteRequisito.id_expediente_requisito,
        id_expediente_requisito, "Requisito de expediente no encontrado",
    )
    require_project_nucleus_access(db, user, entity.id_proyecto_nucleo, mode="capture")
    return service.update_entity(db, entity, data, user)


@router.get(
    "/afectaciones/{id_afectacion}/indemnizacion",
    response_model=schemas.IndemnizacionResponse | None,
)
def get_indemnity(
    id_afectacion: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_affectation_access(db, user, id_afectacion)
    return db.query(models.Indemnizacion).filter(
        models.Indemnizacion.id_afectacion == id_afectacion,
        models.Indemnizacion.activo.is_(True),
    ).first()


@router.post(
    "/afectaciones/{id_afectacion}/indemnizacion",
    response_model=schemas.IndemnizacionResponse,
    status_code=201,
)
def create_indemnity(
    id_afectacion: int,
    data: schemas.IndemnizacionCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_indemnity(db, id_afectacion, data, user)


@router.patch(
    "/indemnizaciones/{id_indemnizacion}",
    response_model=schemas.IndemnizacionResponse,
)
def update_indemnity(
    id_indemnizacion: int,
    data: schemas.IndemnizacionUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = require_indemnity_access(
        db, user, id_indemnizacion, mode="capture"
    )
    return service.update_entity(db, entity, data, user)


@router.get(
    "/indemnizaciones/{id_indemnizacion}/pagos",
    response_model=list[schemas.PagoResponse],
)
def list_payments(
    id_indemnizacion: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_indemnity_access(db, user, id_indemnizacion)
    return db.query(models.Pago).filter(
        models.Pago.id_indemnizacion == id_indemnizacion,
        models.Pago.activo.is_(True),
    ).order_by(models.Pago.fecha_pago, models.Pago.id_pago).all()


@router.post(
    "/indemnizaciones/{id_indemnizacion}/pagos",
    response_model=schemas.PagoResponse,
    status_code=201,
)
def create_payment(
    id_indemnizacion: int,
    data: schemas.PagoCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_payment(db, id_indemnizacion, data, user)


@router.patch("/pagos/{id_pago}", response_model=schemas.PagoResponse)
def update_payment(
    id_pago: int,
    data: schemas.PagoUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    entity = require_payment_access(db, user, id_pago, mode="capture")
    return service.update_entity(db, entity, data, user)


@router.get(
    "/proyectos/{id_proyecto}/trazos",
    response_model=list[schemas.TrazoProyectoResponse],
)
def list_traces(
    id_proyecto: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_project_access(db, user, id_proyecto)
    rows = db.query(
        models.TrazoProyecto,
        func.ST_AsText(models.TrazoProyecto.geometria_linea).label("geometria_wkt"),
    ).filter(
        models.TrazoProyecto.id_proyecto == id_proyecto,
        models.TrazoProyecto.activo.is_(True),
    ).order_by(models.TrazoProyecto.version.desc()).all()
    result = []
    for trace, geometry in rows:
        item = schemas.TrazoProyectoResponse.model_validate(trace).model_dump()
        item["geometria_wkt"] = geometry
        result.append(item)
    return result


@router.post(
    "/proyectos/{id_proyecto}/trazos",
    response_model=schemas.TrazoProyectoResponse,
    status_code=201,
)
def create_trace(
    id_proyecto: int,
    data: schemas.TrazoProyectoCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(GIS_ROLES)),
):
    trace = service.create_trace(db, id_proyecto, data, user)
    result = schemas.TrazoProyectoResponse.model_validate(trace).model_dump()
    result["geometria_wkt"] = data.geometria_wkt
    return result


@router.get(
    "/proyectos/{id_proyecto}/usuarios",
    response_model=list[schemas.UsuarioProyectoResponse],
)
def list_project_users(
    id_proyecto: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    require_project_access(db, user, id_proyecto)
    return db.query(models.UsuarioProyecto).filter(
        models.UsuarioProyecto.id_proyecto == id_proyecto,
        models.UsuarioProyecto.activo.is_(True),
    ).order_by(models.UsuarioProyecto.id_usuario).all()


@router.post(
    "/proyectos/{id_proyecto}/usuarios",
    response_model=schemas.UsuarioProyectoResponse,
    status_code=201,
)
def assign_project_user(
    id_proyecto: int,
    data: schemas.UsuarioProyectoCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(["admin"])),
):
    return service.assign_user_to_project(db, id_proyecto, data, user)


@router.post(
    "/nucleos/{nucleo_id}/unidades-agrarias",
    response_model=schemas.UnidadAgrariaResponse,
    status_code=201,
)
def create_unidad_agraria(
    nucleo_id: int,
    data: schemas.UnidadAgrariaCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.create_unidad_agraria(db, nucleo_id, data, user)


@router.get(
    "/nucleos/{nucleo_id}/unidades-agrarias",
    response_model=list[schemas.UnidadAgrariaResponse],
)
def get_unidades_agrarias_by_nucleo(
    nucleo_id: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return service.get_unidades_agrarias_by_nucleo(db, nucleo_id, user)


@router.patch(
    "/unidades-agrarias/{unidad_id}",
    response_model=schemas.UnidadAgrariaResponse,
)
def update_unidad_agraria(
    unidad_id: int,
    data: schemas.UnidadAgrariaUpdate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.update_unidad_agraria(db, unidad_id, data, user)


@router.post(
    "/afectaciones/{afectacion_id}/unidades-agrarias",
    response_model=schemas.AfectacionUnidadAgrariaResponse,
    status_code=201,
)
def associate_afectacion_unidad_agraria(
    afectacion_id: int,
    data: schemas.AfectacionUnidadAgrariaCreate,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(CAPTURE_ROLES)),
):
    return service.associate_afectacion_unidad_agraria(db, afectacion_id, data, user)


@router.get(
    "/afectaciones/{afectacion_id}/unidades-agrarias",
    response_model=list[schemas.AfectacionUnidadAgrariaResponse],
)
def get_unidades_agrarias_by_afectacion(
    afectacion_id: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return service.get_unidades_agrarias_by_afectacion(db, afectacion_id, user)
