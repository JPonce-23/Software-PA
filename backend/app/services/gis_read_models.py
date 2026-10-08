"""Read-only GIS projections. No relationships or descriptive copies are persisted."""

from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import and_, text

from .. import models, schemas


TOTAL_COUNT_RESPONSE = {
    200: {"headers": {"X-Total-Count": {
        "description": "Total de registros autorizados con los mismos filtros, antes de skip/limit.",
        "schema": {"type": "integer", "minimum": 0},
    }}}
}


def actor_names(db, rows, id_field, name_field):
    """Fetch only display names, including inactive historical principals, in one query."""
    ids = {row[id_field] for row in rows if row.get(id_field) is not None}
    names = {}
    if ids:
        for user_id, first, paternal, maternal in db.query(
            models.Usuario.id_usuario, models.Usuario.nombre,
            models.Usuario.apellido_paterno, models.Usuario.apellido_materno,
        ).filter(models.Usuario.id_usuario.in_(ids)).all():
            names[user_id] = " ".join(part.strip() for part in (first, paternal, maternal)
                                      if part and part.strip())
    return [{**row, name_field: names.get(row.get(id_field))} for row in rows]


def with_actor(db, records, schema, id_field="creado_por", name_field="creado_por_nombre"):
    return actor_names(db, [schema.model_validate(row).model_dump() for row in records],
                       id_field, name_field)


def revisions(db, rows):
    rows = actor_names(db, rows, "creado_por", "creado_por_nombre")
    keys = {(row["id_proyecto_nucleo"], row["id_parcela"]) for row in rows
            if row["id_proyecto_nucleo"] is not None}
    destinations = {}
    if keys:
        pn, n, p = models.ProyectoNucleo, models.NucleoAgrario, models.Parcela
        m, e = models.Municipio, models.EntidadFederativa
        # One projection query for the entire page; historical revisions remain readable.
        for row in db.query(
            pn.id_proyecto_nucleo, p.id_parcela, n.nombre_nucleo,
            m.nombre.label("municipio"), e.nombre.label("entidad"),
            p.no_parcela.label("numero_parcela"),
        ).join(n, n.id_nucleo == pn.id_nucleo).join(m, m.id_municipio == n.id_municipio).join(
            e, e.id_entidad == m.id_entidad,
        ).outerjoin(p, and_(p.id_nucleo == n.id_nucleo,
                          p.id_parcela.in_({key[1] for key in keys if key[1] is not None}))).filter(
            pn.id_proyecto_nucleo.in_({key[0] for key in keys}),
        ).all():
            destinations[(row.id_proyecto_nucleo, row.id_parcela)] = {
                "nombre_nucleo": row.nombre_nucleo, "municipio": row.municipio,
                "entidad": row.entidad, "numero_parcela": row.numero_parcela,
            }
            destinations[(row.id_proyecto_nucleo, None)] = {
                "nombre_nucleo": row.nombre_nucleo, "municipio": row.municipio,
                "entidad": row.entidad, "numero_parcela": None,
            }
    return [{**row, "destino": destinations.get((row["id_proyecto_nucleo"], row["id_parcela"]))}
            for row in rows]


def cycle_detail(db, record, cycle_id):
    cycle = db.query(models.ImportacionConciliacionCiclo).filter_by(
        id_importacion=record.id_importacion, id_ciclo=cycle_id).first()
    if cycle is None:
        raise HTTPException(404, "Ciclo no encontrado en la importación")
    results = db.query(models.ImportacionConciliacionResultado).filter_by(id_ciclo=cycle_id).order_by(
        models.ImportacionConciliacionResultado.id_importacion_feature).all()
    candidates = db.query(models.ImportacionFeatureCandidato).filter_by(id_ciclo=cycle_id).order_by(
        models.ImportacionFeatureCandidato.id_candidato).all()
    decisions = db.query(models.ImportacionFeatureDecision).filter_by(id_ciclo=cycle_id).order_by(
        models.ImportacionFeatureDecision.id_decision).all()
    by_candidates, by_decisions = defaultdict(list), defaultdict(list)
    for candidate in with_actor(db, candidates, schemas.CandidatoGisResponse,
                                "id_usuario_revision", "usuario_revision_nombre"):
        by_candidates[candidate["id_importacion_feature"]].append(candidate)
    for decision in with_actor(db, decisions, schemas.DecisionGisResponse):
        by_decisions[decision["id_importacion_feature"]].append(decision)
    items = []
    for result in results:
        cs = by_candidates[result.id_importacion_feature]
        ds = by_decisions[result.id_importacion_feature]
        state = result.estado_matching
        if ds:
            last = ds[-1]["accion"]
            if last in {"confirmar", "ignorar", "seleccionar"}:
                state = {"confirmar": "confirmado", "ignorar": "ignorado", "seleccionar": "seleccionado"}[last]
            elif last == "rechazar":
                remaining = [c for c in cs if c["estado"] != "rechazado"]
                state = "rechazado" if not remaining else "ambiguo" if len(remaining) > 1 else "candidato"
        items.append({"id_importacion_feature": result.id_importacion_feature,
                      "estado_matching": result.estado_matching, "estado_resultado": state,
                      "candidatos": cs, "decisiones": ds})
    return {**with_actor(db, [cycle], schemas.CicloGisResponse, "id_usuario", "usuario_nombre")[0],
            "features": items}


def revision_detail(db, revision_id, user):
    from .gis_history import require_revision
    revision = require_revision(db, revision_id, user)
    row = db.execute(text("SELECT * FROM vw_revision_cambio_gis_estado WHERE id_revision=:r"),
                     {"r": revision.id_revision}).mappings().one()
    decisions = db.query(models.RevisionCambioGisDecision).filter_by(id_revision=revision_id).order_by(
        models.RevisionCambioGisDecision.id_decision).all()
    return {**revisions(db, [dict(row)])[0],
            "decisiones": with_actor(db, decisions, schemas.RevisionGisDecisionResponse)}
