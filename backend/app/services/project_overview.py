"""One snapshot, bounded result size, no per-nucleus requests or row limit."""
from sqlalchemy import select, func, exists, case, literal
from .. import models as m


def project_overview(db, project_id):
    pn = m.ProyectoNucleo
    nuclei = select(pn.id_proyecto_nucleo).where(pn.id_proyecto == project_id, pn.activo.is_(True)).cte("overview_nuclei")
    fields = []

    def scalar(name, query):
        fields.append(query.scalar_subquery().label(name))

    scalar("nucleos", select(func.count()).select_from(nuclei))
    a, p = m.Afectacion, m.Parcela
    af = (a.activo.is_(True), a.id_proyecto_nucleo.in_(select(nuclei)))
    scalar("parcelas", select(func.count()).select_from(p).where(p.activo.is_(True), p.id_nucleo.in_(select(pn.id_nucleo).where(pn.id_proyecto == project_id, pn.activo.is_(True)))))
    scalar("afectaciones", select(func.count()).select_from(a).where(*af))
    # Same precedence as project_surface: parent OR destinations, never both.
    dest, unit = m.AfectacionUnidadAgraria, m.UnidadAgraria
    destinations = select(dest.id_afectacion, func.sum(dest.superficie_afectada_ha).label("surface"),
        func.count().label("total"), func.count(dest.superficie_afectada_ha).label("known")).join(
        unit, unit.id_unidad_agraria == dest.id_unidad_agraria).join(a, a.id_afectacion == dest.id_afectacion).where(
        dest.activo.is_(True), unit.activo.is_(True), *af).group_by(dest.id_afectacion).cte("overview_surfaces")
    surface = func.coalesce(a.superficie_afectada_ha, destinations.c.surface)
    incomplete = case((a.superficie_afectada_ha.is_not(None), 0), (destinations.c.surface.is_(None), 1),
                      (destinations.c.known < destinations.c.total, 1), else_=0)
    surface_query = select(func.sum(surface).label("surface"), func.coalesce(func.sum(incomplete), 0).label("incomplete")).select_from(a).outerjoin(
        destinations, destinations.c.id_afectacion == a.id_afectacion).where(*af).cte("overview_surface_total")
    scalar("superficie_ha", select(surface_query.c.surface))
    scalar("sin_superficie", select(surface_query.c.incomplete))
    act = m.ActividadCampo
    for kind in ("sensibilizacion", "caminamiento"):
        conditions = (act.activo.is_(True), act.id_proyecto_nucleo.in_(select(nuclei)), act.tipo_actividad == kind)
        scalar(kind + "_total", select(func.count()).select_from(act).where(*conditions))
        scalar(kind + "_realizadas", select(func.count()).select_from(act).where(*conditions, act.fecha_realizada.is_not(None)))

    asm, cv, cat = m.Asamblea, m.AsambleaConvocatoria, m.CatalogoOperativo
    assemblies = select(asm.id_asamblea).where(asm.activo.is_(True), asm.id_proyecto_nucleo.in_(select(nuclei))).cte("overview_assemblies")
    celebrated = select(cat.id_catalogo_opcion).where(cat.tipo_catalogo == "resultado_convocatoria", cat.codigo == "celebrada", cat.activo.is_(True))
    cv_conditions = (cv.activo.is_(True), cv.id_asamblea.in_(select(assemblies)))
    scalar("convocatorias_total", select(func.count()).select_from(cv).where(*cv_conditions))
    scalar("convocatorias_realizadas", select(func.count()).select_from(cv).where(*cv_conditions, cv.fecha_realizacion.is_not(None)))
    scalar("asambleas_total", select(func.count()).select_from(assemblies))
    scalar("asambleas_realizadas", select(case((exists(celebrated), func.count(func.distinct(cv.id_asamblea))), else_=None)).where(
        *cv_conditions, cv.fecha_realizacion.is_not(None), cv.id_resultado.in_(celebrated)))

    c, ca, fa, t = m.Convenio, m.ConvenioAfectacion, m.TramiteFifonafeAfectacion, m.TramiteFifonafe
    cops = select(c.id_convenio, c.id_proyecto_nucleo, c.ambito, c.monto_90, c.monto_100).where(
        c.activo.is_(True), c.tipo_instrumento == "convenio", c.ambito.in_(("individual", "colectivo")),
        c.id_proyecto_nucleo.in_(select(nuclei))).cte("overview_cops")
    links = select(ca.id_convenio, t.id_tramite_fifonafe, t.estatus, t.hay_conflictos).join(
        cops, cops.c.id_convenio == ca.id_convenio).join(a, a.id_afectacion == ca.id_afectacion).join(
        fa, fa.id_afectacion == a.id_afectacion).join(t, t.id_tramite_fifonafe == fa.id_tramite_fifonafe).where(
        ca.activo.is_(True), a.activo.is_(True), fa.activo.is_(True), t.activo.is_(True),
        a.id_proyecto_nucleo == cops.c.id_proyecto_nucleo, t.id_proyecto_nucleo == cops.c.id_proyecto_nucleo).distinct().cte("overview_links")
    related = select(links.c.id_tramite_fifonafe).where(links.c.id_convenio == cops.c.id_convenio)
    complete = exists(related) & ~exists(related.where(links.c.estatus.is_distinct_from("completo")))
    conflict = exists(related.where(links.c.hay_conflictos.is_(True)))
    unknown = ~exists(related) | exists(related.where(links.c.hay_conflictos.is_(None)))
    pay, indemn = m.Pago, m.Indemnizacion
    payments = select(pay.id_pago, pay.monto, a.tipo_afectacion).join(indemn, indemn.id_indemnizacion == pay.id_indemnizacion).join(
        a, a.id_afectacion == indemn.id_afectacion).where(pay.activo.is_(True), indemn.activo.is_(True), *af).cte("overview_payments")
    scalar("pagos_total", select(func.sum(payments.c.monto)))
    scalar("pagos_registros", select(func.count()).select_from(payments))
    for ambit in ("individual", "colectivo"):
        scope = cops.c.ambito == ambit
        for name, condition in (("total", scope), ("completos", scope & complete), ("conflicto", scope & conflict),
                                ("sin_tramite", scope & ~exists(related)), ("conflicto_sin_dato", scope & ~conflict & unknown)):
            scalar(ambit + "_" + name, select(func.count()).select_from(cops).where(condition))
        for concept in ("90", "100"):
            column = cops.c["monto_" + concept]
            scalar(ambit + "_monto_" + concept, select(func.sum(column)).where(scope))
            scalar(ambit + "_con_dato_" + concept, select(func.count(column)).where(scope))
    return dict(db.execute(select(*fields)).mappings().one())


def overview_sources(db, project_id, kind, skip, limit):
    pn, n = m.ProyectoNucleo, m.NucleoAgrario
    def count(model, *conditions):
        return select(func.count()).select_from(model).where(*conditions).correlate(pn).scalar_subquery()
    if kind == "parcelas":
        p = m.Parcela
        total = count(p, p.activo.is_(True), p.id_nucleo == pn.id_nucleo)
        done = total; pending = 0
    elif kind == "afectaciones":
        a = m.Afectacion
        total = count(a, a.activo.is_(True), a.id_proyecto_nucleo == pn.id_proyecto_nucleo)
        done = total; pending = 0
    elif kind == "pagos":
        p, i, a = m.Pago, m.Indemnizacion, m.Afectacion
        total = select(func.count()).select_from(p).join(i, i.id_indemnizacion == p.id_indemnizacion).join(a, a.id_afectacion == i.id_afectacion).where(
            p.activo.is_(True), i.activo.is_(True), a.activo.is_(True), a.id_proyecto_nucleo == pn.id_proyecto_nucleo).correlate(pn).scalar_subquery()
        done = total; pending = 0
    elif kind in ("sensibilizacion", "caminamiento"):
        a = m.ActividadCampo
        filters = (a.activo.is_(True), a.id_proyecto_nucleo == pn.id_proyecto_nucleo, a.tipo_actividad == kind)
        total = count(a, *filters)
        done = count(a, *filters, a.fecha_realizada.is_not(None))
        pending = count(a, *filters, a.fecha_realizada.is_(None), a.fecha_programada.is_not(None))
    else:
        a, cv = m.Asamblea, m.AsambleaConvocatoria
        filters = (a.activo.is_(True), a.id_proyecto_nucleo == pn.id_proyecto_nucleo)
        cvs = select(cv.id_asamblea).where(cv.activo.is_(True), cv.fecha_realizacion.is_not(None))
        if kind == "asambleas":
            total = count(a, *filters)
            cat=m.CatalogoOperativo
            celebrated=select(cat.id_catalogo_opcion).where(cat.tipo_catalogo=="resultado_convocatoria",cat.codigo=="celebrada",cat.activo.is_(True))
            cvs=cvs.where(cv.id_resultado.in_(celebrated))
            done = count(a, *filters, a.id_asamblea.in_(cvs)); pending = total - done
        else:
            def convocations(*extra):
                return select(func.count()).select_from(cv).join(a, a.id_asamblea == cv.id_asamblea).where(*filters, cv.activo.is_(True), *extra).correlate(pn).scalar_subquery()
            total=convocations(); done=convocations(cv.fecha_realizacion.is_not(None)); pending=total-done
    query=select(pn.id_proyecto_nucleo, n.nombre_nucleo, total.label("total"), done.label("realizados"),
                 (pending if hasattr(pending,"label") else literal(pending)).label("pendientes")).join(n,n.id_nucleo==pn.id_nucleo).where(pn.id_proyecto==project_id,pn.activo.is_(True))
    if kind != "pagos": query=query.where(total>0)
    return [dict(r) for r in db.execute(query.order_by(n.nombre_nucleo,pn.id_proyecto_nucleo).offset(skip).limit(limit)).mappings()]
