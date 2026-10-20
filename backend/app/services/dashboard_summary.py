"""Dashboard COP semantics, including the existing first-100-nuclei scope.

The caller must authorize the project before querying. This read model neither
uses historical KPI criteria nor sums monetary values across N:M links.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models


def project_agreements(db: Session, project_id: int) -> dict:
    nucleus = models.ProyectoNucleoResumen
    # Same view, active filter, ordering and default page as NucleosAPI.
    nuclei = db.query(nucleus.id_proyecto_nucleo).filter(
        nucleus.id_proyecto == project_id, nucleus.activo.is_(True),
    ).order_by(nucleus.entidad, nucleus.municipio, nucleus.nombre_nucleo).limit(100).all()
    agreement, link, affectation = models.Convenio, models.ConvenioAfectacion, models.Afectacion
    unique = db.query(
        agreement.id_convenio, agreement.ambito, agreement.tipo_convenio,
        agreement.consecutivo, agreement.fecha_firma,
    ).join(link, link.id_convenio == agreement.id_convenio).join(
        affectation, affectation.id_afectacion == link.id_afectacion,
    ).filter(
        affectation.id_proyecto_nucleo.in_([n.id_proyecto_nucleo for n in nuclei]),
        affectation.activo.is_(True), link.activo.is_(True), agreement.activo.is_(True),
    ).distinct().subquery()
    rows = db.query(
        unique,
        func.count().filter(unique.c.ambito == "individual").over().label("individuales"),
        func.count().filter(unique.c.ambito == "colectivo").over().label("colectivos"),
        func.count().filter(
            unique.c.ambito.in_(("individual", "colectivo")), unique.c.fecha_firma.is_not(None),
        ).over().label("formalizados"),
    ).order_by(unique.c.id_convenio).all()
    return {
        "individuales": rows[0].individuales if rows else 0,
        "colectivos": rows[0].colectivos if rows else 0,
        "formalizados": rows[0].formalizados if rows else 0,
        "convenios": [{key: getattr(row, key) for key in (
            "id_convenio", "ambito", "tipo_convenio", "consecutivo", "fecha_firma",
        )} for row in rows],
    }
