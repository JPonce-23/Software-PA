"""Autorización territorial para recursos del flujo de liberación."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Query, Session

from .. import models


def require_tramo_access(
    db: Session,
    user: models.Usuario,
    id_tramo: int,
) -> None:
    if user.rol == "admin":
        return
    permitido = db.query(models.UsuarioTramo.id_usuario_tramo).filter(
        models.UsuarioTramo.id_usuario == user.id_usuario,
        models.UsuarioTramo.id_tramo == id_tramo,
        models.UsuarioTramo.activo.is_(True),
    ).first()
    if permitido is None:
        # Una misma respuesta evita revelar si el recurso existe en otro tramo.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso al tramo solicitado",
        )


def require_project_access(
    db: Session,
    user: models.Usuario,
    id_proyecto: int,
) -> None:
    if user.rol == "admin":
        return
    permitido = db.query(models.Tramo.id_tramo).join(
        models.UsuarioTramo,
        models.UsuarioTramo.id_tramo == models.Tramo.id_tramo,
    ).filter(
        models.Tramo.id_proyecto == id_proyecto,
        models.Tramo.activo.is_(True),
        models.UsuarioTramo.id_usuario == user.id_usuario,
        models.UsuarioTramo.activo.is_(True),
    ).first()
    if permitido is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso al proyecto solicitado",
        )


def require_tramo_nucleo_access(
    db: Session,
    user: models.Usuario,
    id_tramo_nucleo: int,
) -> models.TramoNucleo:
    tramo_nucleo = db.query(models.TramoNucleo).filter(
        models.TramoNucleo.id_tramo_nucleo == id_tramo_nucleo,
        models.TramoNucleo.activo.is_(True),
    ).first()
    if tramo_nucleo is None:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    require_tramo_access(db, user, tramo_nucleo.id_tramo)
    return tramo_nucleo


def motivo_fuera_seguimiento_pa(
    db: Session,
    tramo_nucleo: models.TramoNucleo,
) -> str | None:
    nucleo = db.query(models.NucleoAgrario).filter(
        models.NucleoAgrario.id_nucleo == tramo_nucleo.id_nucleo,
        models.NucleoAgrario.activo.is_(True),
    ).first()
    if tramo_nucleo.es_expropiacion:
        return "Expropiación directa"
    if nucleo and nucleo.comunidad_indigena:
        return "Comunidad indígena"
    if tramo_nucleo.proyecto_no_afecta_uso_comun:
        return "El proyecto no afecta tierras de uso común"
    return None


def require_seguimiento_pa_activo(
    db: Session,
    tramo_nucleo: models.TramoNucleo,
) -> None:
    motivo = motivo_fuera_seguimiento_pa(db, tramo_nucleo)
    if motivo is None:
        return
    raise HTTPException(
        status_code=409,
        detail={
            "code": "PA_SIN_SEGUIMIENTO_ORDINARIO",
            "message": (
                "Este expediente está fuera del seguimiento ordinario de la PA; "
                f"motivo: {motivo}."
            ),
        },
    )


def require_afectacion_access(
    db: Session,
    user: models.Usuario,
    id_afectacion: int,
) -> models.Afectacion:
    afectacion = db.query(models.Afectacion).filter(
        models.Afectacion.id_afectacion == id_afectacion,
        models.Afectacion.activo.is_(True),
    ).first()
    if afectacion is None:
        raise HTTPException(status_code=404, detail="Afectación no encontrada")
    require_tramo_nucleo_access(db, user, afectacion.id_tramo_nucleo)
    return afectacion


def require_nucleo_access(
    db: Session,
    user: models.Usuario,
    id_nucleo: int,
) -> None:
    if user.rol == "admin":
        return
    permitido = db.query(models.TramoNucleo.id_tramo_nucleo).join(
        models.UsuarioTramo,
        models.UsuarioTramo.id_tramo == models.TramoNucleo.id_tramo,
    ).filter(
        models.TramoNucleo.id_nucleo == id_nucleo,
        models.TramoNucleo.activo.is_(True),
        models.UsuarioTramo.id_usuario == user.id_usuario,
        models.UsuarioTramo.activo.is_(True),
    ).first()
    if permitido is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso al núcleo solicitado",
        )


def require_document_relation_access(
    db: Session,
    user: models.Usuario,
    entidad_tipo: str,
    entidad_id: int,
) -> None:
    if entidad_tipo == "tramo_nucleo":
        require_tramo_nucleo_access(db, user, entidad_id)
        return
    if entidad_tipo == "nucleo_agrario":
        nucleo = db.query(models.NucleoAgrario.id_nucleo).filter(
            models.NucleoAgrario.id_nucleo == entidad_id,
            models.NucleoAgrario.activo.is_(True),
        ).first()
        if nucleo is None:
            raise HTTPException(status_code=404, detail="Núcleo no encontrado")
        require_nucleo_access(db, user, entidad_id)
        return
    if entidad_tipo == "afectacion":
        require_afectacion_access(db, user, entidad_id)
        return
    if entidad_tipo == "convenio":
        convenio = db.query(models.Convenio).filter(
            models.Convenio.id_convenio == entidad_id,
            models.Convenio.activo.is_(True),
        ).first()
        if convenio is None:
            raise HTTPException(status_code=404, detail="Convenio no encontrado")
        require_tramo_nucleo_access(db, user, convenio.id_tramo_nucleo)
        return
    if entidad_tipo == "orv":
        orv = db.query(models.Orv).filter(
            models.Orv.id_orv == entidad_id,
            models.Orv.activo.is_(True),
        ).first()
        if orv is None:
            raise HTTPException(status_code=404, detail="ORV no encontrado")
        require_nucleo_access(db, user, orv.id_nucleo)
        return
    raise HTTPException(status_code=400, detail="Tipo de entidad documental no válido")


def require_document_access(
    db: Session,
    user: models.Usuario,
    id_documento: int,
) -> models.DocumentacionSoporte:
    documento = db.query(models.DocumentacionSoporte).filter(
        models.DocumentacionSoporte.id_documento == id_documento,
        models.DocumentacionSoporte.activo.is_(True),
    ).first()
    if documento is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    require_document_relation_access(
        db,
        user,
        documento.entidad_relacionada_tipo,
        documento.entidad_relacionada_id,
    )
    return documento


def filter_by_user_tramos(
    query: Query,
    db: Session,
    user: models.Usuario,
    id_tramo_column,
) -> Query:
    if user.rol == "admin":
        return query
    tramos = db.query(models.UsuarioTramo.id_tramo).filter(
        models.UsuarioTramo.id_usuario == user.id_usuario,
        models.UsuarioTramo.activo.is_(True),
    )
    return query.filter(id_tramo_column.in_(tramos))


def filter_by_user_nucleos(
    query: Query,
    db: Session,
    user: models.Usuario,
    id_nucleo_column,
) -> Query:
    if user.rol == "admin":
        return query
    nucleos = db.query(models.TramoNucleo.id_nucleo).join(
        models.UsuarioTramo,
        models.UsuarioTramo.id_tramo == models.TramoNucleo.id_tramo,
    ).filter(
        models.TramoNucleo.activo.is_(True),
        models.UsuarioTramo.id_usuario == user.id_usuario,
        models.UsuarioTramo.activo.is_(True),
    ).distinct()
    return query.filter(id_nucleo_column.in_(nucleos))


def filter_projects_by_user(
    query: Query,
    db: Session,
    user: models.Usuario,
) -> Query:
    if user.rol == "admin":
        return query
    projects = db.query(models.Tramo.id_proyecto).join(
        models.UsuarioTramo,
        models.UsuarioTramo.id_tramo == models.Tramo.id_tramo,
    ).filter(
        models.Tramo.activo.is_(True),
        models.UsuarioTramo.id_usuario == user.id_usuario,
        models.UsuarioTramo.activo.is_(True),
    ).distinct()
    return query.filter(models.Proyecto.id_proyecto.in_(projects))
