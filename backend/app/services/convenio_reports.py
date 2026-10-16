"""Read projections by instrument; money never participates in a detail JOIN.

RAN dates are the earliest dated historical facts (006), never current status.
All collections are loaded in sets, under one repeatable-read request snapshot.
"""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from fastapi import Depends, HTTPException, Path
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from .. import auth, database, models, schemas
from .access import require_project_access


MAX_COMPLETE_CONVENIOS = 10_000
M2_PER_HA = Decimal("10000")
RAN_CRITERION = "primera_fecha_historica_por_tipo"


@dataclass(frozen=True)
class ReportPrincipal:
    id_usuario: int
    rol: str


def get_report_user(
    id_proyecto: int = Path(gt=0),
    user: models.Usuario = Depends(auth.RoleChecker(["admin", "operador", "visualizador", "geografo"])),
    db: Session = Depends(database.get_db),
):
    """Finish authentication/authorization and release its connection first.

    Authentication commits activity and expires the ORM user; RoleChecker can
    reload it. Copy only the access principal, so no lazy load crosses sessions.
    This early close is confined to the three report endpoints.
    """
    try:
        principal = ReportPrincipal(id_usuario=user.id_usuario, rol=user.rol)
        require_project_access(db, principal, id_proyecto, load_details=False)
        return principal
    finally:
        db.close()


def get_report_db(_user: ReportPrincipal = Depends(get_report_user)):
    # Engine.execution_options is lazy: checkout starts at the first query,
    # after get_report_user has completed and closed the authentication session.
    report_engine = database.engine.execution_options(
        isolation_level="REPEATABLE READ", postgresql_readonly=True,
    )
    with Session(bind=report_engine) as db:
        yield db


def _m2(value):
    return None if value is None else value * M2_PER_HA


def _surface(values, origin):
    known = [v for v in values if v is not None]
    subtotal = sum(known, Decimal("0")) if known else None
    return {
        "origen": origin,
        "superficie_m2": subtotal if values and len(known) == len(values) else None,
        "subtotal_conocido_m2": subtotal,
        "registros": len(values),
        "registros_sin_superficie": len(values) - len(known),
    }


def _universe(project_id, id_entidad=None, ambito=None, naturaleza=None):
    c, pn, n, m, e = (model.__table__ for model in (
        models.Convenio, models.ProyectoNucleo, models.NucleoAgrario,
        models.Municipio, models.EntidadFederativa,
    ))
    statement = select(
        c.c.id_convenio, c.c.id_proyecto_nucleo, c.c.ambito,
        c.c.tipo_instrumento, c.c.tipo_convenio, c.c.modalidad_especial,
        c.c.id_convenio_padre, c.c.estado_antecedente, c.c.efecto_monto,
        c.c.id_asamblea_autorizacion, c.c.fecha_firma.label("fecha_firma_cop"),
        c.c.monto_90, c.c.monto_100, c.c.superficie_ha,
        e.c.id_entidad, e.c.nombre.label("estado"),
        m.c.id_municipio, m.c.nombre.label("municipio"),
        n.c.id_nucleo, n.c.nombre_nucleo.label("nucleo_agrario"),
    ).select_from(c.join(pn, pn.c.id_proyecto_nucleo == c.c.id_proyecto_nucleo)
                  .join(n, n.c.id_nucleo == pn.c.id_nucleo)
                  .join(m, m.c.id_municipio == n.c.id_municipio)
                  .join(e, e.c.id_entidad == m.c.id_entidad)).where(
        pn.c.id_proyecto == project_id, pn.c.activo, n.c.activo, c.c.activo,
    )
    for field, value in ((e.c.id_entidad, id_entidad), (c.c.ambito, ambito),
                         (c.c.tipo_convenio, naturaleza)):
        if value is not None:
            statement = statement.where(field == value)
    return statement.subquery("convenios_reporte")


def report_entities(db, user, project_id, *, ambito=None, naturaleza=None):
    require_project_access(db, user, project_id, load_details=False)
    b = _universe(project_id, ambito=ambito, naturaleza=naturaleza)
    rows = db.execute(select(
        b.c.id_entidad, b.c.estado, b.c.ambito, func.count().label("total"),
    ).group_by(b.c.id_entidad, b.c.estado, b.c.ambito)
      .order_by(b.c.id_entidad, b.c.ambito)).mappings()
    entities = {}
    for row in rows:
        entity = entities.setdefault(row["id_entidad"], {
            "id_entidad": row["id_entidad"], "estado": row["estado"],
            "individuales": 0, "colectivos": 0,
        })
        entity["individuales" if row["ambito"] == "individual" else "colectivos"] = row["total"]
    return {"id_proyecto": project_id, "entidades": list(entities.values())}


def _load_details(db, ids, assembly_ids):
    ca, a, au, ua, p, cat = (model.__table__ for model in (
        models.ConvenioAfectacion, models.Afectacion, models.AfectacionUnidadAgraria,
        models.UnidadAgraria, models.Parcela, models.CatalogoOperativo,
    ))
    chain = ca.join(a, and_(a.c.id_afectacion == ca.c.id_afectacion, a.c.activo))
    scope = (ca.c.id_convenio.in_(ids), ca.c.activo)
    affects = defaultdict(list)
    for row in db.execute(select(
        ca.c.id_convenio, ca.c.id_convenio_afectacion, ca.c.id_afectacion,
        ca.c.rol, ca.c.efecto_superficie, ca.c.superficie_impacto_ha,
        a.c.superficie_afectada_ha, cat.c.codigo.label("tipo_cop_operativo"),
    ).select_from(chain.outerjoin(cat, and_(
        cat.c.id_catalogo_opcion == a.c.id_tipo_cop_operativo,
        cat.c.tipo_catalogo == "tipo_cop_operativo",
    ))).where(*scope).order_by(ca.c.id_convenio_afectacion)).mappings():
        affects[row["id_convenio"]].append({
            key: row[key] for key in ("id_convenio_afectacion", "id_afectacion", "rol",
                                    "efecto_superficie", "tipo_cop_operativo")
        } | {"superficie_afectada_m2": _m2(row["superficie_afectada_ha"]),
             "superficie_impacto_m2": _m2(row["superficie_impacto_ha"])})
    units = defaultdict(list)
    for row in db.execute(select(
        ca.c.id_convenio, au.c.id_afectacion_unidad, au.c.id_afectacion,
        ua.c.id_unidad_agraria, p.c.id_parcela, p.c.no_parcela,
        ua.c.id_destino_superficie, cat.c.codigo.label("destino_codigo"),
        cat.c.nombre.label("destino_nombre"), au.c.superficie_afectada_ha,
    ).select_from(chain.join(au, and_(au.c.id_afectacion == a.c.id_afectacion, au.c.activo))
                  .join(ua, and_(ua.c.id_unidad_agraria == au.c.id_unidad_agraria, ua.c.activo))
                  .outerjoin(p, and_(p.c.id_parcela == ua.c.id_parcela, p.c.activo))
                  .outerjoin(cat, and_(cat.c.id_catalogo_opcion == ua.c.id_destino_superficie,
                                      cat.c.tipo_catalogo == "destino_superficie")))
       .where(*scope).order_by(au.c.id_afectacion_unidad)).mappings():
        units[row["id_convenio"]].append({
            key: row[key] for key in ("id_afectacion_unidad", "id_afectacion", "id_unidad_agraria",
                                    "id_parcela", "no_parcela", "id_destino_superficie",
                                    "destino_codigo", "destino_nombre")
        } | {"superficie_afectada_m2": _m2(row["superficie_afectada_ha"])})
    asm, ac = models.Asamblea.__table__, models.AsambleaConvocatoria.__table__
    assemblies = {}
    if assembly_ids:
        for row in db.execute(select(
            asm.c.id_asamblea, ac.c.id_convocatoria, ac.c.fecha_realizacion,
        ).select_from(asm.join(ac, and_(ac.c.id_asamblea == asm.c.id_asamblea, ac.c.activo))
                      .join(cat, and_(cat.c.id_catalogo_opcion == ac.c.id_resultado,
                                      cat.c.tipo_catalogo == "resultado_convocatoria",
                                      cat.c.codigo == "celebrada")))
           .where(asm.c.id_asamblea.in_(assembly_ids), asm.c.activo)
           .order_by(ac.c.id_convocatoria)).mappings():
            assemblies[row["id_asamblea"]] = dict(row)
    tr, ev = models.TramiteRan.__table__, models.TramiteRanEvento.__table__
    active_assemblies = select(asm.c.id_asamblea).where(asm.c.activo)
    procedures = defaultdict(dict)
    for row in db.execute(select(
        tr.c.id_tramite_ran, tr.c.id_convenio, tr.c.id_asamblea,
        ev.c.id_evento_ran, ev.c.ordinal, ev.c.fecha_evento, ev.c.id_documento,
        cat.c.codigo.label("tipo_evento"),
    ).select_from(tr.outerjoin(ev, and_(ev.c.id_tramite_ran == tr.c.id_tramite_ran, ev.c.activo))
                  .outerjoin(cat, cat.c.id_catalogo_opcion == ev.c.id_tipo_evento))
       .where(tr.c.activo, or_(tr.c.id_convenio.in_(ids), and_(
           tr.c.id_asamblea.in_(assembly_ids), tr.c.id_asamblea.in_(active_assemblies))))
       .order_by(tr.c.id_tramite_ran, ev.c.ordinal, ev.c.id_evento_ran)).mappings():
        key = ("convenio", row["id_convenio"]) if row["id_convenio"] is not None else ("asamblea", row["id_asamblea"])
        procedure = procedures[key].setdefault(row["id_tramite_ran"], {
            "id_tramite_ran": row["id_tramite_ran"], "eventos": [],
        })
        if row["id_evento_ran"] is not None:
            procedure["eventos"].append({key: row[key] for key in (
                "id_tramite_ran", "id_evento_ran", "ordinal", "tipo_evento", "fecha_evento", "id_documento",
            )})
    return affects, units, assemblies, procedures


def _ran(procedures):
    procedures = list(procedures.values())
    events = [event for tr in procedures for event in tr["eventos"]]

    def first(codes):
        candidates = [e for e in events if e["tipo_evento"] in codes and e["fecha_evento"] is not None]
        return min(candidates, key=lambda e: (e["fecha_evento"], e["id_tramite_ran"], e["ordinal"], e["id_evento_ran"]), default=None)

    ingress, inscription = first({"ingreso", "reingreso"}), first({"inscripcion"})
    return {
        "criterio": RAN_CRITERION,
        "fecha_ingreso": ingress["fecha_evento"] if ingress else None,
        "fecha_inscripcion": inscription["fecha_evento"] if inscription else None,
        "ingreso": ingress, "inscripcion": inscription,
        "tramite_vigente_determinado": False,
        "multiples_tramites": len(procedures) > 1,
        "fechas_de_distintos_tramites": bool(ingress and inscription and ingress["id_tramite_ran"] != inscription["id_tramite_ran"]),
        "cantidad_reingresos": sum(e["tipo_evento"] == "reingreso" for e in events),
        "eventos_sin_fecha": sum(e["fecha_evento"] is None for e in events),
        "tramites": procedures,
    }


def general_report(db, user, project_id, *, id_entidad=None, ambito=None,
                   naturaleza=None, pagina=1, tamano_pagina=100, completo=False):
    require_project_access(db, user, project_id, load_details=False)
    b = _universe(project_id, id_entidad, ambito, naturaleza)
    totals = dict(db.execute(select(b.c.ambito, func.count()).group_by(b.c.ambito)).all())
    if completo and sum(totals.values()) > MAX_COMPLETE_CONVENIOS:
        raise HTTPException(413, detail=schemas.LimiteConveniosReporteDetalle(
            limite_convenios=MAX_COMPLETE_CONVENIOS, total_convenios=sum(totals.values()),
        ).model_dump())
    order = [b.c.id_entidad, b.c.id_municipio, b.c.id_nucleo, b.c.id_convenio]
    numbered = select(b, func.row_number().over(partition_by=b.c.ambito, order_by=order).label("no")).subquery()
    query = select(numbered)
    offset = (pagina - 1) * tamano_pagina
    if not completo:
        query = query.where(numbered.c.no > offset, numbered.c.no <= offset + tamano_pagina)
    rows = db.execute(query.order_by(numbered.c.ambito, numbered.c.no)).mappings().all()
    result = {"id_proyecto": project_id, "completo": completo, "individuales": [], "colectivos": []}
    if rows:
        ids = [r["id_convenio"] for r in rows]
        assembly_ids = sorted({r["id_asamblea_autorizacion"] for r in rows if r["id_asamblea_autorizacion"] is not None})
        affects, units, assemblies, procedures = _load_details(db, ids, assembly_ids)
        for row in rows:
            item = dict(row)
            cid, aid = item["id_convenio"], item.pop("id_asamblea_autorizacion")
            declared, amount90, amount100 = item.pop("superficie_ha"), item.pop("monto_90"), item.pop("monto_100")
            aff, us = affects[cid], units[cid]
            codes = {a["tipo_cop_operativo"] for a in aff if a["tipo_cop_operativo"] is not None}
            incomplete = not aff or any(a["tipo_cop_operativo"] is None for a in aff) or len(codes) != 1
            ran = _ran(procedures[("convenio", cid)])
            warnings = []
            if incomplete:
                warnings.append("CLASIFICACION_COP_INCOMPLETA_O_AMBIGUA")
            if ran["multiples_tramites"]:
                warnings.append("RAN_CONVENIO_MULTIPLES_TRAMITES_SIN_VIGENCIA_DETERMINADA")
            if not aff:
                warnings.append("SIN_AFECTACIONES_ACTIVAS")
            if not us:
                warnings.append("SIN_UNIDADES_ACTIVAS")
            item.update(
                monto_total_90=amount90, monto_total_100=amount100,
                tipo_cop_operativo=next(iter(codes)) if len(codes) == 1 else None,
                clasificacion_cop_incompleta=incomplete, superficie_declarada_m2=_m2(declared),
                superficie_administrativa_afectada=_surface([a["superficie_afectada_m2"] for a in aff], "afectacion.superficie_afectada_ha"),
                superficie_unidades=_surface([u["superficie_afectada_m2"] for u in us], "afectacion_unidad_agraria.superficie_afectada_ha"),
                afectaciones=aff, unidades=us, ran_convenio=ran,
                fecha_ingreso_ran_convenio=ran["fecha_ingreso"],
                fecha_inscripcion_ran_convenio=ran["fecha_inscripcion"], advertencias=warnings,
            )
            if item["ambito"] == "individual":
                parcels = {}
                for u in us:
                    if u["id_parcela"] is not None:
                        parcel = parcels.setdefault(u["id_parcela"], {"id_parcela": u["id_parcela"], "no_parcela": u["no_parcela"], "ids_afectacion_unidad": []})
                        parcel["ids_afectacion_unidad"].append(u["id_afectacion_unidad"])
                item.update(parcelas=sorted(parcels.values(), key=lambda p: p["id_parcela"]))
                warnings.append("SUPERFICIE_EXCEL_INDIVIDUAL_PENDIENTE_DEFINICION")
                result["individuales"].append(item)
            else:
                groups = defaultdict(list)
                for u in us:
                    groups[u["id_destino_superficie"]].append(u)
                destinations = []
                for dest_id in sorted(groups, key=lambda key: (key is None, key or 0)):
                    group = groups[dest_id]
                    destinations.append({
                        "id_destino_superficie": dest_id, "codigo": group[0]["destino_codigo"], "nombre": group[0]["destino_nombre"],
                        "superficie": _surface([u["superficie_afectada_m2"] for u in group], "afectacion_unidad_agraria.superficie_afectada_ha"),
                        "ids_afectacion_unidad": [u["id_afectacion_unidad"] for u in group],
                    })
                asm = assemblies.get(aid, {})
                ran_asm = _ran(procedures[("asamblea", aid)])
                if not asm:
                    warnings.append("SIN_ASAMBLEA_CELEBRADA_VINCULADA")
                if ran_asm["multiples_tramites"]:
                    warnings.append("RAN_ASAMBLEA_MULTIPLES_TRAMITES_SIN_VIGENCIA_DETERMINADA")
                item.update(destinos=destinations, id_asamblea_autorizacion=aid,
                            id_convocatoria_celebrada=asm.get("id_convocatoria"), fecha_asamblea_realizada=asm.get("fecha_realizacion"),
                            ran_asamblea=ran_asm, fecha_ingreso_ran_asamblea=ran_asm["fecha_ingreso"], fecha_inscripcion_ran_asamblea=ran_asm["fecha_inscripcion"])
                result["colectivos"].append(item)
    for scope, label in (("individual", "individuales"), ("colectivo", "colectivos")):
        result["paginacion_" + label] = {
            "total": totals.get(scope, 0), "pagina": 1 if completo else pagina,
            "tamano_pagina": None if completo else tamano_pagina,
            "hay_mas": not completo and offset + tamano_pagina < totals.get(scope, 0),
        }
    return result
