"""Scalar label inputs for reports; never expands ORM relationships.

Scope follows each existing read endpoint: active record, active project-nucleus,
active project and active assignment (except admin). Global nucleus activity is
not an additional condition of those endpoints. Missing/denied IDs are omitted.
"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import models
from .access import authorized_project_ids

C_FIELDS=("id_convenio", "id_proyecto_nucleo", "tipo_convenio", "consecutivo",
          "ambito", "descripcion_instrumento", "fecha_firma")
A_FIELDS=("id_afectacion", "id_proyecto_nucleo", "tipo_afectacion", "situacion", "superficie_afectada_ha")


def _columns(model, fields):
    return [getattr(model, field) for field in fields]


def references(db: Session, user: models.Usuario, nuclei: list[int],
               affectations: list[int], agreements: list[int], include_affectations: bool = False) -> dict:
    pn, n, a, c = models.ProyectoNucleo, models.ProyectoNucleoResumen, models.Afectacion, models.Convenio
    allowed = select(pn.id_proyecto_nucleo).where(
        pn.activo.is_(True), pn.id_proyecto.in_(authorized_project_ids(db, user)),
    )
    result = {"nucleos": [], "afectaciones": [], "convenios": []}
    if nuclei:
        result["nucleos"] = list(db.execute(select(n.id_proyecto_nucleo, n.nombre_nucleo).where(
            n.id_proyecto_nucleo.in_(nuclei), n.id_proyecto_nucleo.in_(allowed),
        ).order_by(n.id_proyecto_nucleo)).mappings())
    if affectations or (include_affectations and nuclei):
        requested = [a.id_afectacion.in_(affectations)]
        if include_affectations:
            requested.append(a.id_proyecto_nucleo.in_(nuclei))
        result["afectaciones"] = list(db.execute(select(*_columns(a, A_FIELDS)).where(
            a.activo.is_(True), a.id_proyecto_nucleo.in_(allowed), or_(*requested),
        ).order_by(a.id_afectacion)).mappings())
    if agreements:
        result["convenios"] = list(db.execute(select(*_columns(c, C_FIELDS)).where(
            c.id_convenio.in_(agreements), c.activo.is_(True), c.id_proyecto_nucleo.in_(allowed),
        ).order_by(c.id_convenio)).mappings())
    return result


def context_references(db: Session, user: models.Usuario, nuclei: list[int]) -> dict:
    pn, n = models.ProyectoNucleo, models.ProyectoNucleoResumen
    roots = list(db.execute(select(n.id_proyecto_nucleo, n.nombre_nucleo).join(
        pn, pn.id_proyecto_nucleo == n.id_proyecto_nucleo,
    ).where(pn.id_proyecto_nucleo.in_(nuclei), pn.activo.is_(True),
            pn.id_proyecto.in_(authorized_project_ids(db, user))).order_by(n.id_proyecto_nucleo)).mappings())
    ids = [n["id_proyecto_nucleo"] for n in roots]
    result = {"nucleos": roots, "afectaciones": [], "convenios": [], "asambleas": []}
    if not ids:
        return result
    a, c, link, assembly = models.Afectacion, models.Convenio, models.ConvenioAfectacion, models.Asamblea
    result["afectaciones"] = list(db.execute(select(*_columns(a, A_FIELDS)).where(
        a.id_proyecto_nucleo.in_(ids), a.activo.is_(True),
    ).order_by(a.id_afectacion)).mappings())
    # contexto.js walks affectations ascending and agreements ascending. Its Map
    # keeps the first insertion position, but the LAST active affectation label.
    rows = select(*_columns(c, C_FIELDS), a.id_afectacion,
        func.row_number().over(partition_by=c.id_convenio, order_by=a.id_afectacion.desc()).label("last_link"),
        func.min(a.id_afectacion).over(partition_by=c.id_convenio).label("first_affectation"),
    ).join(link, link.id_convenio == c.id_convenio).join(a, a.id_afectacion == link.id_afectacion).where(
        a.id_proyecto_nucleo.in_(ids), a.activo.is_(True), link.activo.is_(True), c.activo.is_(True),
    ).subquery()
    result["convenios"] = [{"item": {field: row[field] for field in C_FIELDS},
                             "id_afectacion": row["id_afectacion"]}
        for row in db.execute(select(rows).where(rows.c.last_link == 1).order_by(
            rows.c.first_affectation, rows.c.id_convenio)).mappings()]
    result["asambleas"] = list(db.execute(select(
        assembly.id_asamblea, assembly.id_proyecto_nucleo, assembly.proposito,
    ).where(assembly.id_proyecto_nucleo.in_(ids), assembly.activo.is_(True)).order_by(
        assembly.id_asamblea.desc())).mappings())
    return result
