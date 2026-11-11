"""Administrative affected area, without adding parent and destination twice."""
from sqlalchemy import case, func
from .. import models


def summarize_surfaces(db, nucleus_ids):
    if not nucleus_ids:
        return {}
    a = models.Afectacion
    d = models.AfectacionUnidadAgraria
    u = models.UnidadAgraria
    destinations = (db.query(
        d.id_afectacion.label("id"),
        func.sum(d.superficie_afectada_ha).label("surface"),
        func.count(d.id_afectacion_unidad).label("total"),
        func.count(d.superficie_afectada_ha).label("known"),
    ).join(u, u.id_unidad_agraria == d.id_unidad_agraria)
      .join(a, a.id_afectacion == d.id_afectacion)
      .filter(d.activo.is_(True), u.activo.is_(True), a.activo.is_(True),
              a.id_proyecto_nucleo.in_(nucleus_ids))
      .group_by(d.id_afectacion).subquery())
    surface = func.coalesce(a.superficie_afectada_ha, destinations.c.surface)
    incomplete = case((a.superficie_afectada_ha.is_not(None), 0),
                      (destinations.c.surface.is_(None), 1),
                      (destinations.c.known < destinations.c.total, 1), else_=0)
    rows = (db.query(a.id_proyecto_nucleo,
                    func.sum(surface).label("surface"),
                    func.sum(incomplete).label("incomplete"))
            .outerjoin(destinations, destinations.c.id == a.id_afectacion)
            .filter(a.activo.is_(True), a.id_proyecto_nucleo.in_(nucleus_ids))
            .group_by(a.id_proyecto_nucleo).all())
    return {row.id_proyecto_nucleo: {
        "superficie_resumen_ha": row.surface,
        "afectaciones_superficie_incompleta": int(row.incomplete),
    } for row in rows}
