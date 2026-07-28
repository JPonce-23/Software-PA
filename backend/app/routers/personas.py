from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from .. import auth, models, schemas
from ..database import get_db
from ..services import personas as service
from ..services.common import get_active, mark_inactive, set_audit_context


router = APIRouter()
READ_ROLES = ["admin", "operador", "visualizador", "geografo"]
WRITE_ROLES = ["admin", "operador", "geografo"]


@router.get(
    "/parcelas",
    response_model=List[schemas.ParcelaResponse],
    tags=["Parcelas"],
)
def listar_parcelas(
    id_nucleo: int | None = Query(default=None),
    tipo_parcela: str | None = Query(default=None),
    id_persona: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.Parcela).filter(models.Parcela.activo.is_(True))
    if id_nucleo is not None:
        query = query.filter(models.Parcela.id_nucleo == id_nucleo)
    if tipo_parcela is not None:
        query = query.filter(models.Parcela.tipo_parcela == tipo_parcela)
    if id_persona is not None:
        query = query.join(
            models.ParcelaTitular,
            models.ParcelaTitular.id_parcela == models.Parcela.id_parcela,
        ).filter(
            models.ParcelaTitular.id_persona == id_persona,
            models.ParcelaTitular.activo.is_(True),
        )
    return query.order_by(models.Parcela.id_parcela).distinct().all()


@router.get(
    "/parcelas/{id_parcela}",
    response_model=schemas.ParcelaResponse,
    tags=["Parcelas"],
)
def obtener_parcela(
    id_parcela: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return get_active(db, models.Parcela, id_parcela, "id_parcela")


@router.get(
    "/orvs",
    response_model=List[schemas.OrvResponse],
    tags=["ORVs"],
)
def listar_orvs(
    id_nucleo: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.Orv).filter(models.Orv.activo.is_(True))
    if id_nucleo is not None:
        query = query.filter(models.Orv.id_nucleo == id_nucleo)
    return query.order_by(models.Orv.inicio_vigencia.desc()).all()


@router.get(
    "/personas",
    response_model=List[schemas.PersonaResponse],
    tags=["Personas"],
)
def listar_personas(
    q: str | None = Query(default=None, max_length=100),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return service.list_personas(db, q, skip, limit)


@router.get(
    "/personas/{id_persona}",
    response_model=schemas.PersonaResponse,
    tags=["Personas"],
)
def obtener_persona(
    id_persona: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return get_active(db, models.Persona, id_persona, "id_persona")


@router.post(
    "/personas",
    response_model=schemas.PersonaResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Personas"],
)
def crear_persona(
    data: schemas.PersonaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    return service.create_persona(db, data, current_user.id_usuario)


@router.put(
    "/personas/{id_persona}",
    response_model=schemas.PersonaResponse,
    tags=["Personas"],
)
def actualizar_persona(
    id_persona: int,
    data: schemas.PersonaUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    persona = get_active(db, models.Persona, id_persona, "id_persona")
    return service.update_persona(db, persona, data, current_user.id_usuario)


@router.delete("/personas/{id_persona}", tags=["Personas"])
def eliminar_persona(
    id_persona: int,
    motivo: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    persona = get_active(db, models.Persona, id_persona, "id_persona")
    service.delete_persona(db, persona, current_user.id_usuario, motivo)
    return {"status": "success", "message": "Persona dada de baja"}


@router.get(
    "/personas/{id_persona}/nucleos",
    response_model=List[schemas.PersonaNucleoResponse],
    tags=["Personas"],
)
def listar_nucleos_persona(
    id_persona: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    get_active(db, models.Persona, id_persona, "id_persona")
    return (
        db.query(models.PersonaNucleo)
        .filter_by(id_persona=id_persona, activo=True)
        .all()
    )


@router.post(
    "/personas/{id_persona}/nucleos",
    response_model=schemas.PersonaNucleoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Personas"],
)
def vincular_persona_nucleo(
    id_persona: int,
    data: schemas.PersonaNucleoCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    set_audit_context(db, current_user.id_usuario)
    persona = get_active(db, models.Persona, id_persona, "id_persona")
    relacion = service.ensure_persona_nucleo(
        db,
        persona,
        data.id_nucleo,
        current_user.id_usuario,
        data.calidad_agraria,
    )
    relacion.fecha_inicio = data.fecha_inicio
    relacion.fecha_fin = data.fecha_fin
    relacion.observaciones = data.observaciones
    db.commit()
    db.refresh(relacion)
    return relacion


@router.get(
    "/orvs/{id_orv}/integrantes",
    response_model=List[schemas.OrvIntegranteResponse],
    tags=["ORVs"],
)
def listar_integrantes_orv(
    id_orv: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    get_active(db, models.Orv, id_orv, "id_orv")
    return (
        db.query(models.OrvIntegrante)
        .options(joinedload(models.OrvIntegrante.persona))
        .filter_by(id_orv=id_orv, activo=True)
        .order_by(models.OrvIntegrante.cargo)
        .all()
    )


@router.post(
    "/orvs/{id_orv}/integrantes",
    response_model=schemas.OrvIntegranteResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["ORVs"],
)
def agregar_integrante_orv(
    id_orv: int,
    data: schemas.OrvIntegranteCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    orv = get_active(db, models.Orv, id_orv, "id_orv")
    return service.add_orv_integrante(db, orv, data, current_user.id_usuario)


@router.delete(
    "/orvs/{id_orv}/integrantes/{id_integrante}",
    tags=["ORVs"],
)
def eliminar_integrante_orv(
    id_orv: int,
    id_integrante: int,
    motivo: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    integrante = get_active(
        db, models.OrvIntegrante, id_integrante, "id_orv_integrante"
    )
    if integrante.id_orv != id_orv:
        raise HTTPException(status_code=404, detail="Integrante no encontrado en el ORV")
    service.soft_delete_relation(
        db, integrante, current_user.id_usuario, motivo
    )
    return {"status": "success", "message": "Integrante dado de baja"}


@router.get(
    "/parcelas/{id_parcela}/titulares",
    response_model=List[schemas.ParcelaTitularResponse],
    tags=["Parcelas"],
)
def listar_titulares_parcela(
    id_parcela: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    get_active(db, models.Parcela, id_parcela, "id_parcela")
    return (
        db.query(models.ParcelaTitular)
        .options(joinedload(models.ParcelaTitular.persona))
        .filter_by(id_parcela=id_parcela, activo=True)
        .order_by(models.ParcelaTitular.id_parcela_titular)
        .all()
    )


@router.post(
    "/parcelas/{id_parcela}/titulares",
    response_model=schemas.ParcelaTitularResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Parcelas"],
)
def agregar_titular_parcela(
    id_parcela: int,
    data: schemas.ParcelaTitularCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    parcela = get_active(db, models.Parcela, id_parcela, "id_parcela")
    return service.add_parcela_titular(
        db, parcela, data, current_user.id_usuario
    )


@router.delete(
    "/parcelas/{id_parcela}/titulares/{id_titular}",
    tags=["Parcelas"],
)
def eliminar_titular_parcela(
    id_parcela: int,
    id_titular: int,
    motivo: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    titular = get_active(
        db, models.ParcelaTitular, id_titular, "id_parcela_titular"
    )
    if titular.id_parcela != id_parcela:
        raise HTTPException(status_code=404, detail="Titular no encontrado en la parcela")
    service.validate_titular_removal(db, titular)
    service.soft_delete_relation(db, titular, current_user.id_usuario, motivo)
    return {"status": "success", "message": "Titular dado de baja"}


# Compatibilidad temporal: estos endpoints conservan los contratos actuales,
# pero escriben también en las relaciones normalizadas.
@router.post(
    "/parcelas/con-titular",
    response_model=schemas.ParcelaResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Parcelas"],
)
def crear_parcela_normalizada(
    data: schemas.ParcelaConTitularCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    return service.create_parcela_normalizada(
        db,
        data,
        current_user.id_usuario,
    )


@router.post(
    "/parcelas",
    response_model=schemas.ParcelaResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Parcelas"],
)
def crear_parcela_compatible(
    data: schemas.ParcelaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    return service.create_parcela_compatible(db, data, current_user.id_usuario)


@router.put(
    "/parcelas/{id_parcela}",
    response_model=schemas.ParcelaResponse,
    tags=["Parcelas"],
)
def actualizar_parcela_compatible(
    id_parcela: int,
    data: schemas.ParcelaUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    parcela = get_active(db, models.Parcela, id_parcela, "id_parcela")
    return service.update_parcela_compatible(
        db, parcela, data, current_user.id_usuario
    )


@router.delete("/parcelas/{id_parcela}", tags=["Parcelas"])
def eliminar_parcela_compatible(
    id_parcela: int,
    motivo: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    set_audit_context(db, current_user.id_usuario)
    parcela = get_active(db, models.Parcela, id_parcela, "id_parcela")
    afectacion_activa = (
        db.query(models.Afectacion.id_afectacion)
        .filter_by(id_parcela=id_parcela, activo=True)
        .first()
    )
    if afectacion_activa:
        raise HTTPException(
            status_code=409,
            detail="La parcela tiene una afectación activa",
        )
    for titular in (
        db.query(models.ParcelaTitular)
        .filter_by(id_parcela=id_parcela, activo=True)
        .all()
    ):
        mark_inactive(titular, current_user.id_usuario, motivo)
    mark_inactive(parcela, current_user.id_usuario, motivo)
    db.commit()
    return {"status": "success", "message": "Parcela dada de baja"}


@router.post(
    "/orvs/con-integrantes",
    response_model=schemas.OrvResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["ORVs"],
)
def crear_orv_normalizado(
    data: schemas.OrvConIntegrantesCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    return service.create_orv_normalizado(
        db,
        data,
        current_user.id_usuario,
    )


@router.post(
    "/orvs",
    response_model=schemas.OrvResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["ORVs"],
)
def crear_orv_compatible(
    data: schemas.OrvCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    return service.create_orv_compatible(db, data, current_user.id_usuario)


@router.put(
    "/orvs/{id_orv}",
    response_model=schemas.OrvResponse,
    tags=["ORVs"],
)
def actualizar_orv_compatible(
    id_orv: int,
    data: schemas.OrvUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    orv = get_active(db, models.Orv, id_orv, "id_orv")
    return service.update_orv_compatible(db, orv, data, current_user.id_usuario)


@router.delete("/orvs/{id_orv}", tags=["ORVs"])
def eliminar_orv_compatible(
    id_orv: int,
    motivo: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(WRITE_ROLES)),
):
    set_audit_context(db, current_user.id_usuario)
    orv = get_active(db, models.Orv, id_orv, "id_orv")
    for integrante in (
        db.query(models.OrvIntegrante)
        .filter_by(id_orv=id_orv, activo=True)
        .all()
    ):
        mark_inactive(integrante, current_user.id_usuario, motivo)
    mark_inactive(orv, current_user.id_usuario, motivo)
    db.commit()
    return {"status": "success", "message": "ORV dado de baja"}
