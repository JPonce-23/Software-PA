"""Complete COP aggregates and bounded exports; compatible first-100 legacy read.

The caller must authorize the project before querying. This read model neither
uses historical KPI criteria nor sums monetary values across N:M links.
"""
from fastapi import HTTPException
from sqlalchemy import Text, cast, func, literal, select, true
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import Session

from .. import models


def active_nuclei(project_id: int):
    """Same membership as vw_proyecto_nucleo_resumen, without its detail joins.

    Mandatory FKs guarantee the view's inner joins. Its active flag is the
    ProyectoNucleo flag, not an additional NucleoAgrario lifecycle predicate.
    """
    pn = models.ProyectoNucleo
    return select(pn.id_proyecto_nucleo).where(
        pn.id_proyecto == project_id, pn.activo.is_(True))


def complete_agreements(project_id: int):
    """Semijoin deduplicates by agreement PK, independently of N:M fan-out."""
    c, link, a = models.Convenio, models.ConvenioAfectacion, models.Afectacion
    reachable = select(link.id_convenio).join(
        a, a.id_afectacion == link.id_afectacion,
    ).where(link.activo.is_(True), a.activo.is_(True),
            a.id_proyecto_nucleo.in_(active_nuclei(project_id)))
    return select(c.id_convenio, c.ambito, c.tipo_convenio, c.consecutivo, c.fecha_firma).where(
        c.activo.is_(True), c.id_convenio.in_(reachable))


def summary_statement(project_id: int):
    agreements = complete_agreements(project_id).subquery()
    return select(
        select(func.count()).select_from(active_nuclei(project_id).subquery()).scalar_subquery().label("total_nucleos"),
        func.count().label("total_convenios"),
        func.count().filter(agreements.c.ambito == "individual").label("individuales"),
        func.count().filter(agreements.c.ambito == "colectivo").label("colectivos"),
        func.count().filter(agreements.c.ambito.in_(("individual", "colectivo")),
                            agreements.c.fecha_firma.is_not(None)).label("formalizados"),
    ).select_from(agreements)


def project_summary(db: Session, project_id: int) -> dict:
    """One aggregate row; caller must authorize the project first."""
    return dict(db.execute(summary_statement(project_id)).mappings().one())


def export_nuclei(project_id: int):
    """Only columns currently used by dashboard Excel, plus stable references."""
    pn, n, m, e = models.ProyectoNucleo, models.NucleoAgrario, models.Municipio, models.EntidadFederativa
    return select(
        pn.id_proyecto_nucleo, n.id_nucleo, n.nombre_nucleo,
        m.id_municipio, m.nombre.label("municipio"),
        e.id_entidad, e.nombre.label("entidad"),
    ).select_from(pn).join(n, n.id_nucleo == pn.id_nucleo).join(
        m, m.id_municipio == n.id_municipio,
    ).join(e, e.id_entidad == m.id_entidad).where(
        pn.id_proyecto == project_id, pn.activo.is_(True))


def export_page_statement(statement, id_field: str, after_id: int, limit: int):
    """Count, content revision and keyset page share one PostgreSQL snapshot.

    Only explicit exports fingerprint full scalar projections. Initial summary
    never hashes or retrieves them. SQL aggregation uses O(N) work per page;
    Python receives at most limit+1 rows and materializes no domain objects.
    """
    source = statement.cte("cop_export_source")
    identity = source.c[id_field]
    row_hash = func.md5(cast(func.row_to_json(source.table_valued()), Text))
    revision = func.md5(func.coalesce(func.string_agg(
        row_hash, aggregate_order_by(literal(""), identity)), literal("")))
    metadata = select(func.count().label("total"), revision.label("revision")).select_from(source).cte("cop_export_metadata")
    page = select(source).where(identity > after_id).order_by(identity).limit(limit + 1).cte("cop_export_page")
    return select(metadata, page).select_from(metadata.outerjoin(page, true())).order_by(page.c[id_field])


def project_export_page(db: Session, project_id: int, resource: str,
                        after_id: int, limit: int, revision: str | None) -> dict:
    if after_id and revision is None:
        raise HTTPException(status_code=422, detail=[{
            "type": "missing", "loc": ["query", "revision"],
            "msg": "revision es obligatoria después de la primera página",
            "input": None,
        }])
    statement, id_field = (
        (export_nuclei(project_id), "id_proyecto_nucleo") if resource == "nucleos"
        else (complete_agreements(project_id), "id_convenio"))
    rows = db.execute(export_page_statement(statement, id_field, after_id, limit)).mappings().all()
    current = rows[0]["revision"]
    if revision is not None and revision != current:
        raise HTTPException(status_code=409, detail="El conjunto exportable cambió; reinicie la exportación")
    items = [{k: v for k, v in row.items() if k not in ("total", "revision")}
             for row in rows if row[id_field] is not None]
    has_more = len(items) > limit
    items = items[:limit]
    return dict(items=items, total=rows[0]["total"], revision=current, hay_mas=has_more,
                siguiente_id=items[-1][id_field] if has_more else None)


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
