"""Consolidated documentary support through existing, active canonical targets."""

from sqlalchemy import and_, BigInteger, cast, func, literal, or_, select, String, union_all
from sqlalchemy.orm import noload

from .. import models, schemas
from .access import require_document_target_access


def document_targets(pn_id, nucleus_id):
    """A SQL projection, restricted to one PN plus its existing shared nucleus targets.

    Each branch follows project_ids_for_document_target's active ancestry. Narrowing
    project-owned records to this PN prevents leaks when two projects share a nucleus.
    """
    statements = []

    def target(kind, model, pk, condition, parents=(), label=None):
        origin = func.coalesce(label, literal(kind + " #") + cast(pk, String)) if label is not None else (
            literal(kind + " #") + cast(pk, String))
        statement = select(literal(kind).label("entidad_tipo"), pk.label("entidad_id"),
                           origin.label("origen")).select_from(model)
        for parent, on in parents:
            statement = statement.join(parent, on)
        statements.append(statement.where(condition, model.activo.is_(True),
                                          *(parent.activo.is_(True) for parent, _ in parents)))

    pn, n = models.ProyectoNucleo, models.NucleoAgrario
    target("proyecto_nucleo", pn, pn.id_proyecto_nucleo, pn.id_proyecto_nucleo == pn_id,
           label=select(n.nombre_nucleo).where(n.id_nucleo == nucleus_id).scalar_subquery())
    target("nucleo_agrario", n, n.id_nucleo, n.id_nucleo == nucleus_id, label=n.nombre_nucleo)
    for kind, model, pk, label in [
        ("orv", models.Orv, models.Orv.id_orv, models.Orv.numero_orv),
        ("padron_historial", models.PadronHistorial, models.PadronHistorial.id_padron, None),
        ("parcela", models.Parcela, models.Parcela.id_parcela, models.Parcela.no_parcela),
        ("unidad_agraria", models.UnidadAgraria, models.UnidadAgraria.id_unidad_agraria,
         models.UnidadAgraria.referencia_alfanumerica),
    ]:
        target(kind, model, pk, model.id_nucleo == nucleus_id, label=label)
    for kind, model, pk, label in [
        ("afectacion", models.Afectacion, models.Afectacion.id_afectacion, None),
        ("actividad_campo", models.ActividadCampo, models.ActividadCampo.id_actividad, None),
        ("asamblea", models.Asamblea, models.Asamblea.id_asamblea, models.Asamblea.proposito),
        ("convenio", models.Convenio, models.Convenio.id_convenio, None),
        ("tramite_fifonafe", models.TramiteFifonafe, models.TramiteFifonafe.id_tramite_fifonafe,
         models.TramiteFifonafe.referencia_expediente),
        ("expediente_requisito", models.ExpedienteRequisito,
         models.ExpedienteRequisito.id_expediente_requisito, None),
    ]:
        target(kind, model, pk, model.id_proyecto_nucleo == pn_id, label=label)
    for kind, child, pk, parent, on, condition in [
        ("parcela_titular", models.ParcelaTitular, models.ParcelaTitular.id_parcela_titular,
         models.Parcela, models.Parcela.id_parcela == models.ParcelaTitular.id_parcela,
         models.Parcela.id_nucleo == nucleus_id),
        ("unidad_agraria_titular", models.UnidadAgrariaTitular, models.UnidadAgrariaTitular.id_unidad_titular,
         models.UnidadAgraria, models.UnidadAgraria.id_unidad_agraria == models.UnidadAgrariaTitular.id_unidad_agraria,
         models.UnidadAgraria.id_nucleo == nucleus_id),
        ("afectacion_unidad_agraria", models.AfectacionUnidadAgraria, models.AfectacionUnidadAgraria.id_afectacion_unidad,
         models.Afectacion, models.Afectacion.id_afectacion == models.AfectacionUnidadAgraria.id_afectacion,
         models.Afectacion.id_proyecto_nucleo == pn_id),
        ("asamblea_convocatoria", models.AsambleaConvocatoria, models.AsambleaConvocatoria.id_convocatoria,
         models.Asamblea, models.Asamblea.id_asamblea == models.AsambleaConvocatoria.id_asamblea,
         models.Asamblea.id_proyecto_nucleo == pn_id),
        ("convenio_compareciente", models.ConvenioCompareciente, models.ConvenioCompareciente.id_compareciente,
         models.Convenio, models.Convenio.id_convenio == models.ConvenioCompareciente.id_convenio,
         models.Convenio.id_proyecto_nucleo == pn_id),
        ("tramite_fifonafe_evento", models.TramiteFifonafeEvento, models.TramiteFifonafeEvento.id_evento_fifonafe,
         models.TramiteFifonafe, models.TramiteFifonafe.id_tramite_fifonafe == models.TramiteFifonafeEvento.id_tramite_fifonafe,
         models.TramiteFifonafe.id_proyecto_nucleo == pn_id),
        ("tramite_fifonafe_interviniente", models.TramiteFifonafeInterviniente,
         models.TramiteFifonafeInterviniente.id_interviniente_fifonafe,
         models.TramiteFifonafe, models.TramiteFifonafe.id_tramite_fifonafe == models.TramiteFifonafeInterviniente.id_tramite_fifonafe,
         models.TramiteFifonafe.id_proyecto_nucleo == pn_id),
    ]:
        target(kind, child, pk, condition, [(parent, on)])
    ran = models.TramiteRan
    ran_scope = or_(ran.id_proyecto_nucleo == pn_id,
                    and_(ran.id_proyecto_nucleo.is_(None), ran.id_nucleo == nucleus_id))
    target("tramite_ran", ran, ran.id_tramite_ran, ran_scope, label=ran.referencia_expediente)
    event = models.TramiteRanEvento
    target("tramite_ran_evento", event, event.id_evento_ran, ran_scope,
           [(ran, ran.id_tramite_ran == event.id_tramite_ran)])
    a, i, p = models.Afectacion, models.Indemnizacion, models.Pago
    indemnity_parents = [(a, a.id_afectacion == i.id_afectacion)]
    target("indemnizacion", i, i.id_indemnizacion, a.id_proyecto_nucleo == pn_id, indemnity_parents)
    target("pago", p, p.id_pago, a.id_proyecto_nucleo == pn_id,
           [(i, i.id_indemnizacion == p.id_indemnizacion), *indemnity_parents])
    return union_all(*statements).cte("document_targets")


def consolidated_documents(db, pn_id, user):
    # This reuses project_ids_for_document_target and the existing role/project policy.
    require_document_target_access(db, user, "proyecto_nucleo", pn_id)
    nucleus_id = db.query(models.ProyectoNucleo.id_nucleo).filter_by(id_proyecto_nucleo=pn_id).scalar()
    targets = document_targets(pn_id, nucleus_id)
    link, req = models.DocumentoVinculo, models.ExpedienteRequisito
    scoped_links = select(
        link.id_documento, targets.c.entidad_tipo, targets.c.entidad_id, targets.c.origen,
        literal("vinculo").label("fuente_relacion"), link.id_documento_vinculo,
        cast(literal(None), BigInteger).label("id_expediente_requisito"),
    ).join(targets, and_(link.entidad_tipo == targets.c.entidad_tipo,
                        link.entidad_id == targets.c.entidad_id)).where(link.activo.is_(True)).cte("scoped_links")
    requirements = select(
        req.id_documento, literal("expediente_requisito"), req.id_expediente_requisito,
        literal("Requisito: ") + models.RequisitoDocumental.nombre,
        literal("expediente_requisito"), cast(literal(None), BigInteger), req.id_expediente_requisito,
    ).join(models.RequisitoDocumental).where(
        req.id_proyecto_nucleo == pn_id, req.activo.is_(True),
        req.id_documento.in_(select(scoped_links.c.id_documento)),
    )
    # A requirement reference never grants new document access. There must also
    # be an existing active link within the requested scope (as for document GET).
    sources = union_all(select(scoped_links), requirements).cte("document_sources")
    latest = select(models.DocumentoVersion.id_documento,
                    func.max(models.DocumentoVersion.numero_version).label("numero_version")).where(
                        models.DocumentoVersion.id_documento.in_(select(sources.c.id_documento)),
                    ).group_by(
                        models.DocumentoVersion.id_documento).subquery()
    rows = db.query(models.Documento, models.DocumentoVersion, sources).join(
        sources, sources.c.id_documento == models.Documento.id_documento,
    ).outerjoin(latest, latest.c.id_documento == models.Documento.id_documento).outerjoin(
        models.DocumentoVersion, and_(models.DocumentoVersion.id_documento == latest.c.id_documento,
                                     models.DocumentoVersion.numero_version == latest.c.numero_version),
    ).options(noload(models.Documento.vinculos), noload(models.Documento.versiones)).filter(
        models.Documento.activo.is_(True),
    ).order_by(sources.c.entidad_tipo, sources.c.entidad_id,
               models.Documento.tipo_documento, models.Documento.id_documento,
               sources.c.fuente_relacion).all()
    return [{"entidad_tipo": row.entidad_tipo, "entidad_id": row.entidad_id,
             "origen": row.origen, "fuente_relacion": row.fuente_relacion,
             "id_documento_vinculo": row.id_documento_vinculo,
             "id_expediente_requisito": row.id_expediente_requisito,
             "documento": schemas.DocumentoResponse.model_validate(row[0]),
             "version_vigente": schemas.DocumentoVersionResponse.model_validate(row[1]) if row[1] else None}
            for row in rows]
