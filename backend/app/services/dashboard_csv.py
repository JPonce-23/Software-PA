"""CSV KPI projection with a single expansion of the canonical event view.

The two dated facts retain the dashboard view's DISTINCT event identity,
NULL amounts on scheduled facts and annual grouping. Authorization is supplied
as a project-id SELECT by the caller; no event or KPI semantics are changed.
"""
from sqlalchemy import BigInteger, Date, Integer, Numeric, Text, cast, column, extract, func, table, true, values


def query(db, project_ids, year=None):
    h = table("vw_hito_seguimiento",
        column("id_proyecto", Integer), column("indicador", Text), column("clave_hito", Text),
        column("fecha_programada", Date), column("fecha_realizada", Date),
        column("superficie_ha", Numeric), column("monto", Numeric))
    facts = values(column("fecha", Date), column("programado", BigInteger),
        column("realizado", BigInteger), column("superficie_ha", Numeric),
        column("monto", Numeric), name="dated_facts").data([
            (h.c.fecha_programada, 1, 0, None, None),
            (h.c.fecha_realizada, 0, 1, h.c.superficie_ha, h.c.monto),
        ]).lateral()
    annual = cast(extract("year", facts.c.fecha), Integer)
    result = db.query(h.c.id_proyecto, annual.label("anio"), h.c.indicador,
        cast(func.sum(facts.c.programado), BigInteger).label("programado"),
        cast(func.sum(facts.c.realizado), BigInteger).label("realizado"),
        cast(func.count(func.distinct(h.c.clave_hito)), BigInteger).label("cantidad"),
        cast(func.sum(facts.c.superficie_ha), Numeric).label("superficie_ha"),
        cast(func.sum(facts.c.monto), Numeric).label("monto"),
    ).select_from(h.join(facts, true())).filter(
        h.c.id_proyecto.in_(project_ids), facts.c.fecha.is_not(None))
    if year is not None:
        result = result.filter(annual == year)
    return result.group_by(h.c.id_proyecto, annual, h.c.indicador).order_by(
        h.c.id_proyecto, annual, h.c.indicador)
