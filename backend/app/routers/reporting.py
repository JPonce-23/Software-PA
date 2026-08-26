"""Dashboard, export and project map read models."""

import csv
import io
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services.access import authorized_project_ids, require_project_access


router = APIRouter(tags=["Dashboard y mapa"])
READ_ROLES = ["admin", "operador", "visualizador", "geografo"]


def _dashboard_query(
    db: Session,
    user: models.Usuario,
    project_id: int | None,
    year: int | None,
):
    query = db.query(models.DashboardKpi)
    if project_id is not None:
        require_project_access(db, user, project_id)
        query = query.filter(models.DashboardKpi.id_proyecto == project_id)
    else:
        query = query.filter(
            models.DashboardKpi.id_proyecto.in_(authorized_project_ids(db, user))
        )
    if year is not None:
        query = query.filter(models.DashboardKpi.anio == year)
    return query


@router.get("/dashboard/kpi", response_model=list[schemas.DashboardKpiResponse])
def dashboard(
    id_proyecto: int | None = None,
    anio: int | None = Query(default=None, ge=2000, le=2200),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    return _dashboard_query(db, user, id_proyecto, anio).order_by(
        models.DashboardKpi.id_proyecto,
        models.DashboardKpi.anio,
        models.DashboardKpi.indicador,
    ).offset(skip).limit(limit).all()


@router.get("/exportaciones/dashboard.csv")
def export_dashboard(
    id_proyecto: int | None = None,
    anio: int | None = Query(default=None, ge=2000, le=2200),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    rows = _dashboard_query(db, user, id_proyecto, anio).order_by(
        models.DashboardKpi.id_proyecto,
        models.DashboardKpi.anio,
        models.DashboardKpi.indicador,
    ).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id_proyecto",
            "anio",
            "indicador",
            "programado",
            "realizado",
            "cantidad",
            "superficie_ha",
            "monto",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.id_proyecto,
                row.anio,
                row.indicador,
                row.programado,
                row.realizado,
                row.cantidad,
                row.superficie_ha,
                row.monto,
            ]
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=dashboard.csv"},
    )


@router.get("/proyectos/{id_proyecto}/mapa")
def project_map(
    id_proyecto: int,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    require_project_access(db, user, id_proyecto)
    traces = db.query(
        models.TrazoProyecto.id_trazo.label("id"),
        models.TrazoProyecto.version.label("nombre"),
        func.ST_AsGeoJSON(models.TrazoProyecto.geometria_linea).label("geometry"),
    ).filter(
        models.TrazoProyecto.id_proyecto == id_proyecto,
        models.TrazoProyecto.activo.is_(True),
    ).all()
    nuclei = db.query(
        models.NucleoAgrario.id_nucleo.label("id"),
        models.NucleoAgrario.nombre_nucleo.label("nombre"),
        func.ST_AsGeoJSON(models.NucleoAgrario.geometria_poligono).label("geometry"),
    ).join(
        models.ProyectoNucleo,
        models.ProyectoNucleo.id_nucleo == models.NucleoAgrario.id_nucleo,
    ).filter(
        models.ProyectoNucleo.id_proyecto == id_proyecto,
        models.ProyectoNucleo.activo.is_(True),
        models.NucleoAgrario.activo.is_(True),
    ).distinct().all()
    parcels = db.query(
        models.Parcela.id_parcela.label("id"),
        func.coalesce(
            models.Parcela.no_parcela,
            models.Parcela.no_parcela_ppt,
            func.concat("Parcela ", models.Parcela.id_parcela),
        ).label("nombre"),
        func.ST_AsGeoJSON(models.Parcela.geometria_poligono).label("geometry"),
    ).join(
        models.ProyectoNucleo,
        models.ProyectoNucleo.id_nucleo == models.Parcela.id_nucleo,
    ).filter(
        models.ProyectoNucleo.id_proyecto == id_proyecto,
        models.ProyectoNucleo.activo.is_(True),
        models.Parcela.activo.is_(True),
        models.Parcela.geometria_poligono.is_not(None),
    ).distinct().all()

    def feature(kind: str, row) -> dict:
        return {
            "type": "Feature",
            "id": f"{kind}:{row.id}",
            "geometry": json.loads(row.geometry) if row.geometry else None,
            "properties": {"tipo": kind, "id": row.id, "nombre": str(row.nombre)},
        }

    return {
        "type": "FeatureCollection",
        "features": [
            *(feature("trazo_proyecto", row) for row in traces),
            *(feature("nucleo_agrario", row) for row in nuclei if row.geometry),
            *(feature("parcela", row) for row in parcels),
        ],
    }
