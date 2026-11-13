"""Project COP tracking. Read existing evidence; manual labels are append-only."""
from typing import Literal
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from .. import models as m, auth
from ..database import get_db
from ..services.access import require_project_access, require_agreement_access
from ..services.common import commit_or_conflict, set_audit_context

router = APIRouter(tags=["Seguimiento FIFONAFE"])
READ = ["admin", "operador", "visualizador"]
WRITE = ["admin", "operador"]

class LabelInput(BaseModel):
    codigo: Literal["espera_firma", "bienes_distintos_tierra", "observaciones_importantes"]
    habilitada: bool
    motivo: str = Field(min_length=5, max_length=2000)

    @field_validator("motivo")
    @classmethod
    def nonblank(cls, value):
        if len(value.strip()) < 5:
            raise ValueError("Escribe un motivo de al menos cinco caracteres")
        return value.strip()


def labels_ready(db):
    return db.execute(text("SELECT to_regclass('public.etiqueta_seguimiento_fifonafe') IS NOT NULL")).scalar()


def project_cops(project_id):
    c, pn = m.Convenio, m.ProyectoNucleo
    return select(c.id_convenio).join(pn, pn.id_proyecto_nucleo == c.id_proyecto_nucleo).where(
        pn.id_proyecto == project_id, pn.activo.is_(True), c.activo.is_(True),
        c.tipo_instrumento == "convenio", c.ambito.in_(["individual", "colectivo"]))


def tracking(db, ids):
    if not ids:
        return {}
    c, pn, n, mun, ent = m.Convenio, m.ProyectoNucleo, m.NucleoAgrario, m.Municipio, m.EntidadFederativa
    rows = db.execute(select(c.id_convenio, c.id_proyecto_nucleo, c.ambito, c.tipo_convenio,
        c.consecutivo, c.fecha_firma, n.nombre_nucleo, mun.nombre.label("municipio"),
        ent.nombre.label("entidad")).join(pn, pn.id_proyecto_nucleo == c.id_proyecto_nucleo)
        .join(n, n.id_nucleo == pn.id_nucleo).join(mun, mun.id_municipio == n.id_municipio)
        .join(ent, ent.id_entidad == mun.id_entidad).where(c.id_convenio.in_(ids))).mappings().all()
    result = {row["id_convenio"]: dict(row, tramites=[], etiquetas=[], personas=[]) for row in rows}
    comp = m.ConvenioCompareciente
    for row in db.execute(select(comp.id_convenio, comp.nombre_en_instrumento).join(m.Persona, m.Persona.id_persona == comp.id_persona)
                          .where(comp.id_convenio.in_(ids), comp.activo.is_(True), m.Persona.activo.is_(True)).distinct()).all():
        result[row.id_convenio]["personas"].append(row.nombre_en_instrumento)
    ca, a, fa, t = m.ConvenioAfectacion, m.Afectacion, m.TramiteFifonafeAfectacion, m.TramiteFifonafe
    relations = db.execute(select(ca.id_convenio, t.id_tramite_fifonafe).join(a, a.id_afectacion == ca.id_afectacion)
        .join(fa, fa.id_afectacion == a.id_afectacion).join(t, t.id_tramite_fifonafe == fa.id_tramite_fifonafe)
        .join(c, c.id_convenio == ca.id_convenio)
        .where(ca.id_convenio.in_(ids), ca.activo.is_(True), a.activo.is_(True), fa.activo.is_(True), t.activo.is_(True),
               a.id_proyecto_nucleo == c.id_proyecto_nucleo, t.id_proyecto_nucleo == c.id_proyecto_nucleo).distinct()).all()
    tids = {tid for _, tid in relations}
    procedures = {}
    if tids:
        for row in db.execute(select(t.id_tramite_fifonafe, t.id_proyecto_nucleo, t.estatus, t.hay_conflictos,
                t.resultado_no_conflictos, t.referencia_expediente, t.observaciones, t.version_flujo, t.acuse_fifonafe_fecha)
                .where(t.id_tramite_fifonafe.in_(tids))).mappings():
            procedures[row["id_tramite_fifonafe"]] = dict(row, eventos=[])
        e, cat = m.TramiteFifonafeEvento, m.CatalogoOperativo
        for row in db.execute(select(e.id_tramite_fifonafe, e.id_evento_fifonafe, e.ordinal, cat.codigo,
                cat.nombre, e.numero_oficio, e.fecha_oficio, e.fecha_evento, e.origen, e.destino,
                e.id_documento, e.observaciones, e.ciclo_consulta).join(cat, cat.id_catalogo_opcion == e.id_tipo_evento)
                .where(e.id_tramite_fifonafe.in_(tids), e.activo.is_(True)).order_by(e.ordinal, e.id_evento_fifonafe)).mappings():
            procedures[row["id_tramite_fifonafe"]]["eventos"].append(dict(row))
    for cid, tid in relations:
        result[cid]["tramites"].append(procedures[tid])
    if labels_ready(db):
        label = m.EtiquetaSeguimientoFifonafe
        rows = db.execute(select(label.id_convenio, label.codigo, label.habilitada, label.motivo,
                label.creado_en, label.creado_por).where(label.id_convenio.in_(ids))
                .order_by(label.id_etiqueta.desc())).mappings()
        seen = set()
        for row in rows:
            key = (row["id_convenio"], row["codigo"])
            if key not in seen:
                result[row["id_convenio"]]["etiquetas"].append(dict(row))
                seen.add(key)
    return result


@router.get("/proyectos/{id_proyecto}/fifonafe/seguimiento")
def list_tracking(id_proyecto: int, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
                  ambito: Literal["individual", "colectivo"] | None = None,
                  db: Session = Depends(get_db), user=Depends(auth.RoleChecker(READ))):
    require_project_access(db, user, id_proyecto, load_details=False)
    base = project_cops(id_proyecto)
    universe = base.subquery()
    counts = dict(db.execute(select(m.Convenio.ambito, func.count()).where(m.Convenio.id_convenio.in_(select(universe)))
                            .group_by(m.Convenio.ambito)).all())
    if ambito:
        base = base.where(m.Convenio.ambito == ambito)
    total = sum(counts.values()) if not ambito else counts.get(ambito, 0)
    ids = list(db.execute(base.order_by(m.Convenio.id_convenio).offset(skip).limit(limit)).scalars())
    data = tracking(db, ids)
    return {"items": [data[i] for i in ids], "total": total, "individuales": counts.get("individual", 0),
            "colectivos": counts.get("colectivo", 0), "hay_mas": skip + len(ids) < total,
            "etiquetas_disponibles": bool(labels_ready(db))}


@router.post("/convenios/{id_convenio}/fifonafe/etiquetas", status_code=201)
def add_label(id_convenio: int, data: LabelInput, db: Session = Depends(get_db),
              user=Depends(auth.RoleChecker(WRITE))):
    agreement = require_agreement_access(db, user, id_convenio, mode="capture")
    if agreement.tipo_instrumento != "convenio":
        raise HTTPException(422, "Este instrumento no corresponde a un COP")
    if not labels_ready(db):
        raise HTTPException(503, "Las etiquetas requieren actualizar la base de datos")
    db.execute(select(m.Convenio.id_convenio).where(m.Convenio.id_convenio == id_convenio).with_for_update())
    set_audit_context(db, user.id_usuario)
    row = m.EtiquetaSeguimientoFifonafe(id_convenio=id_convenio, creado_por=user.id_usuario, **data.model_dump())
    db.add(row)
    commit_or_conflict(db, "No fue posible guardar la etiqueta")
    return {"id_etiqueta": row.id_etiqueta, "codigo": row.codigo, "habilitada": row.habilitada}
