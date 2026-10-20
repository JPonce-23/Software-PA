"""Read model for the public map's indicators (not dashboard KPI semantics).

The caller authorizes the project first. The nucleus universe is the complete
active ProyectoNucleoResumen view used by mapa.js, without the dashboard's cap.
Only scalar projections are selected; no ORM relationship is loaded.
"""
from sqlalchemy import case, exists, func, select
from sqlalchemy.orm import Session

from .. import models


def project_indicators(db: Session, project_id: int) -> dict:
    nucleus = models.ProyectoNucleoResumen
    nuclei = select(nucleus.id_proyecto_nucleo).where(
        nucleus.id_proyecto == project_id, nucleus.activo.is_(True),
    ).cte("map_nuclei")

    catalog = models.CatalogoOperativo
    celebrated = select(catalog.id_catalogo_opcion).where(
        catalog.tipo_catalogo == "resultado_convocatoria",
        catalog.codigo == "celebrada", catalog.activo.is_(True),
    ).cte("map_celebrated")
    assembly, convocation = models.Asamblea, models.AsambleaConvocatoria
    assemblies = select(func.count(func.distinct(assembly.id_asamblea))).join(
        convocation, convocation.id_asamblea == assembly.id_asamblea,
    ).where(
        assembly.id_proyecto_nucleo.in_(select(nuclei.c.id_proyecto_nucleo)),
        assembly.activo.is_(True), convocation.activo.is_(True),
        convocation.fecha_realizacion.is_not(None),
        convocation.id_resultado.in_(select(celebrated.c.id_catalogo_opcion)),
    ).scalar_subquery()

    agreement, link, affectation = models.Convenio, models.ConvenioAfectacion, models.Afectacion
    signed = select(agreement.id_convenio, agreement.ambito).join(
        link, link.id_convenio == agreement.id_convenio,
    ).join(affectation, affectation.id_afectacion == link.id_afectacion).where(
        affectation.id_proyecto_nucleo.in_(select(nuclei.c.id_proyecto_nucleo)),
        affectation.activo.is_(True), link.activo.is_(True), agreement.activo.is_(True),
        agreement.fecha_firma.is_not(None),
    ).distinct().subquery()
    counts = select(
        func.count().filter(signed.c.ambito == "individual").label("convenios_individuales"),
        func.count().filter(signed.c.ambito == "colectivo").label("convenios_colectivos"),
        func.count().filter(signed.c.ambito.in_(("individual", "colectivo"))).label("convenios_firmados"),
    ).subquery()
    statement = select(
        # The old client shows 'No disponible', even on an empty project, when
        # the active celebrated catalog entry is absent. Never turn that into 0.
        case((exists(select(celebrated.c.id_catalogo_opcion)), assemblies), else_=None).label("asambleas_realizadas"),
        counts.c.convenios_individuales, counts.c.convenios_colectivos, counts.c.convenios_firmados,
    )
    return dict(db.execute(statement).mappings().one())
