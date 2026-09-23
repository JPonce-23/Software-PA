"""Dashboard, export and project map read models."""

import csv
import io
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, literal
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


@router.get("/reportes/avance-periodo", response_model=list[schemas.ReporteAvancePeriodoResponse])
def reporte_avance_periodo(
    id_proyecto: int | None = None,
    id_entidad: int | None = Query(default=None, gt=0),
    anio: int | None = Query(default=None, ge=2000, le=2200),
    mes: int | None = Query(default=None, ge=1, le=12),
    trimestre: int | None = Query(default=None, ge=1, le=4),
    indicador: str | None = None,
    ambito: str | None = None,
    tipo_cop_operativo: str | None = None,
    tipo_convenio: str | None = None,
    destino_superficie: str | None = None,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.ReporteAvancePeriodo)
    if id_proyecto is not None:
        require_project_access(db, user, id_proyecto)
        query = query.filter(models.ReporteAvancePeriodo.id_proyecto == id_proyecto)
    else:
        query = query.filter(models.ReporteAvancePeriodo.id_proyecto.in_(authorized_project_ids(db, user)))
    if id_entidad is not None:
        query = query.filter(models.ReporteAvancePeriodo.id_entidad == id_entidad)
    if anio is not None:
        query = query.filter(models.ReporteAvancePeriodo.anio == anio)
    if mes is not None:
        query = query.filter(models.ReporteAvancePeriodo.mes == mes)
    if trimestre is not None:
        query = query.filter(models.ReporteAvancePeriodo.trimestre == trimestre)
    if indicador is not None:
        query = query.filter(models.ReporteAvancePeriodo.indicador == indicador)
    if ambito is not None:
        query = query.filter(models.ReporteAvancePeriodo.ambito == ambito)
    if tipo_cop_operativo is not None:
        query = query.filter(models.ReporteAvancePeriodo.tipo_cop_operativo == tipo_cop_operativo)
    if tipo_convenio is not None:
        query = query.filter(models.ReporteAvancePeriodo.tipo_convenio == tipo_convenio)
    if destino_superficie is not None:
        query = query.filter(models.ReporteAvancePeriodo.destino_superficie == destino_superficie)
    return query.order_by(
        models.ReporteAvancePeriodo.id_proyecto,
        models.ReporteAvancePeriodo.anio,
        models.ReporteAvancePeriodo.mes,
        models.ReporteAvancePeriodo.indicador,
    ).all()


@router.get("/reportes/resumen-actual", response_model=list[schemas.ReporteSnapshotActualResponse])
def reporte_resumen_actual(
    id_proyecto: int | None = None,
    id_entidad: int | None = Query(default=None, gt=0),
    ambito: str | None = None,
    indicador: str | None = None,
    tipo_cop_operativo: str | None = None,
    destino_superficie: str | None = None,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.ReporteSnapshotActual)
    if id_proyecto is not None:
        require_project_access(db, user, id_proyecto)
        query = query.filter(models.ReporteSnapshotActual.id_proyecto == id_proyecto)
    else:
        query = query.filter(models.ReporteSnapshotActual.id_proyecto.in_(authorized_project_ids(db, user)))
    for field, value in ((models.ReporteSnapshotActual.id_entidad, id_entidad), (models.ReporteSnapshotActual.ambito, ambito), (models.ReporteSnapshotActual.indicador, indicador), (models.ReporteSnapshotActual.tipo_cop_operativo, tipo_cop_operativo), (models.ReporteSnapshotActual.destino_superficie, destino_superficie)):
        if value is not None:
            query = query.filter(field == value)
    rows = query.order_by(
        models.ReporteSnapshotActual.id_proyecto,
        models.ReporteSnapshotActual.indicador,
    ).all()

    # 006 no publicó un snapshot de esta condición. Se calcula en la capa de
    # lectura desde el valor vigente de afectaciones activas y se deduplica por
    # ProyectoNucleo; los eventos históricos no participan en el conteo.
    include_current_expropriation = (
        indicador in (None, "expropiacion_directa_actual")
        and ambito in (None, "colectivo")
        and tipo_cop_operativo is None
        and destino_superficie is None
    )
    if include_current_expropriation:
        current = (
            db.query(
                models.ProyectoNucleo.id_proyecto.label("id_proyecto"),
                models.Municipio.id_entidad.label("id_entidad"),
                literal("colectivo").label("ambito"),
                literal("expropiacion_directa_actual").label("indicador"),
                literal(None).label("tipo_cop_operativo"),
                literal(None).label("destino_superficie"),
                func.count(
                    func.distinct(models.ProyectoNucleo.id_proyecto_nucleo)
                ).label("cantidad"),
                literal(None).label("superficie_ha"),
                literal(None).label("monto"),
            )
            .join(
                models.NucleoAgrario,
                models.NucleoAgrario.id_nucleo == models.ProyectoNucleo.id_nucleo,
            )
            .join(
                models.Municipio,
                models.Municipio.id_municipio == models.NucleoAgrario.id_municipio,
            )
            .join(
                models.Afectacion,
                models.Afectacion.id_proyecto_nucleo
                == models.ProyectoNucleo.id_proyecto_nucleo,
            )
            .filter(
                models.ProyectoNucleo.activo.is_(True),
                models.NucleoAgrario.activo.is_(True),
                models.Afectacion.activo.is_(True),
                models.Afectacion.condicion_especial == "expropiacion_directa",
            )
        )
        if id_proyecto is not None:
            current = current.filter(models.ProyectoNucleo.id_proyecto == id_proyecto)
        else:
            current = current.filter(
                models.ProyectoNucleo.id_proyecto.in_(authorized_project_ids(db, user))
            )
        if id_entidad is not None:
            current = current.filter(models.Municipio.id_entidad == id_entidad)
        current = current.group_by(
            models.ProyectoNucleo.id_proyecto,
            models.Municipio.id_entidad,
        )
        rows.extend(current.all())

    return sorted(
        rows,
        key=lambda row: (row.id_proyecto, row.indicador, row.id_entidad),
    )


@router.get(
    "/reportes/convenios/valores-declarados",
    response_model=list[schemas.ConvenioValorDeclaradoResponse],
)
def reporte_convenios_valores_declarados(
    id_proyecto: int | None = None,
    id_entidad: int | None = Query(default=None, gt=0),
    id_proyecto_nucleo: int | None = Query(default=None, gt=0),
    id_convenio: int | None = Query(default=None, gt=0),
    ambito: str | None = None,
    concepto: str | None = None,
    firma_acreditada: bool | None = None,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.ConvenioValorDeclarado)
    if id_proyecto is not None:
        require_project_access(db, user, id_proyecto)
        query = query.filter(models.ConvenioValorDeclarado.id_proyecto == id_proyecto)
    else:
        query = query.filter(
            models.ConvenioValorDeclarado.id_proyecto.in_(authorized_project_ids(db, user))
        )
    for field, value in (
        (models.ConvenioValorDeclarado.id_entidad, id_entidad),
        (models.ConvenioValorDeclarado.id_proyecto_nucleo, id_proyecto_nucleo),
        (models.ConvenioValorDeclarado.id_convenio, id_convenio),
        (models.ConvenioValorDeclarado.ambito, ambito),
        (models.ConvenioValorDeclarado.concepto, concepto),
        (models.ConvenioValorDeclarado.firma_acreditada, firma_acreditada),
    ):
        if value is not None:
            query = query.filter(field == value)
    return query.order_by(
        models.ConvenioValorDeclarado.id_proyecto,
        models.ConvenioValorDeclarado.id_convenio,
        models.ConvenioValorDeclarado.concepto,
    ).all()


@router.get(
    "/reportes/convenios/impactos",
    response_model=list[schemas.ConvenioImpactoResponse],
)
def reporte_convenios_impactos(
    id_proyecto: int | None = None,
    id_entidad: int | None = Query(default=None, gt=0),
    id_proyecto_nucleo: int | None = Query(default=None, gt=0),
    id_convenio: int | None = Query(default=None, gt=0),
    id_afectacion: int | None = Query(default=None, gt=0),
    ambito: str | None = None,
    concepto: str | None = None,
    efecto: str | None = None,
    pendiente: bool | None = None,
    firma_acreditada: bool | None = None,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.ConvenioImpacto)
    if id_proyecto is not None:
        require_project_access(db, user, id_proyecto)
        query = query.filter(models.ConvenioImpacto.id_proyecto == id_proyecto)
    else:
        query = query.filter(
            models.ConvenioImpacto.id_proyecto.in_(authorized_project_ids(db, user))
        )
    for field, value in (
        (models.ConvenioImpacto.id_entidad, id_entidad),
        (models.ConvenioImpacto.id_proyecto_nucleo, id_proyecto_nucleo),
        (models.ConvenioImpacto.id_convenio, id_convenio),
        (models.ConvenioImpacto.id_afectacion, id_afectacion),
        (models.ConvenioImpacto.ambito, ambito),
        (models.ConvenioImpacto.concepto, concepto),
        (models.ConvenioImpacto.efecto, efecto),
        (models.ConvenioImpacto.pendiente, pendiente),
        (models.ConvenioImpacto.firma_acreditada, firma_acreditada),
    ):
        if value is not None:
            query = query.filter(field == value)
    return query.order_by(
        models.ConvenioImpacto.id_proyecto,
        models.ConvenioImpacto.id_convenio,
        models.ConvenioImpacto.clave_impacto,
    ).all()


@router.get(
    "/reportes/convenios/impactos-periodo",
    response_model=list[schemas.ReporteConvenioImpactoPeriodoResponse],
)
def reporte_convenios_impactos_periodo(
    id_proyecto: int | None = None,
    id_entidad: int | None = Query(default=None, gt=0),
    anio: int | None = Query(default=None, ge=2000, le=2200),
    mes: int | None = Query(default=None, ge=1, le=12),
    trimestre: int | None = Query(default=None, ge=1, le=4),
    ambito: str | None = None,
    tipo_cop_operativo: str | None = None,
    tipo_convenio: str | None = None,
    concepto: str | None = None,
    efecto: str | None = None,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.ReporteConvenioImpactoPeriodo)
    if id_proyecto is not None:
        require_project_access(db, user, id_proyecto)
        query = query.filter(
            models.ReporteConvenioImpactoPeriodo.id_proyecto == id_proyecto
        )
    else:
        query = query.filter(
            models.ReporteConvenioImpactoPeriodo.id_proyecto.in_(
                authorized_project_ids(db, user)
            )
        )
    for field, value in (
        (models.ReporteConvenioImpactoPeriodo.id_entidad, id_entidad),
        (models.ReporteConvenioImpactoPeriodo.anio, anio),
        (models.ReporteConvenioImpactoPeriodo.mes, mes),
        (models.ReporteConvenioImpactoPeriodo.trimestre, trimestre),
        (models.ReporteConvenioImpactoPeriodo.ambito, ambito),
        (models.ReporteConvenioImpactoPeriodo.tipo_cop_operativo, tipo_cop_operativo),
        (models.ReporteConvenioImpactoPeriodo.tipo_convenio, tipo_convenio),
        (models.ReporteConvenioImpactoPeriodo.concepto, concepto),
        (models.ReporteConvenioImpactoPeriodo.efecto, efecto),
    ):
        if value is not None:
            query = query.filter(field == value)
    return query.order_by(
        models.ReporteConvenioImpactoPeriodo.id_proyecto,
        models.ReporteConvenioImpactoPeriodo.anio,
        models.ReporteConvenioImpactoPeriodo.mes,
        models.ReporteConvenioImpactoPeriodo.concepto,
    ).all()


@router.get(
    "/reportes/convenios/cobertura-impactos",
    response_model=list[schemas.ConvenioCoberturaImpactoResponse],
)
def reporte_convenios_cobertura_impactos(
    id_proyecto: int | None = None,
    id_entidad: int | None = Query(default=None, gt=0),
    ambito: str | None = None,
    concepto: str | None = None,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.ConvenioCoberturaImpacto)
    if id_proyecto is not None:
        require_project_access(db, user, id_proyecto)
        query = query.filter(
            models.ConvenioCoberturaImpacto.id_proyecto == id_proyecto
        )
    else:
        query = query.filter(
            models.ConvenioCoberturaImpacto.id_proyecto.in_(
                authorized_project_ids(db, user)
            )
        )
    for field, value in (
        (models.ConvenioCoberturaImpacto.id_entidad, id_entidad),
        (models.ConvenioCoberturaImpacto.ambito, ambito),
        (models.ConvenioCoberturaImpacto.concepto, concepto),
    ):
        if value is not None:
            query = query.filter(field == value)
    return query.order_by(
        models.ConvenioCoberturaImpacto.id_proyecto,
        models.ConvenioCoberturaImpacto.id_entidad,
        models.ConvenioCoberturaImpacto.concepto,
    ).all()


@router.get(
    "/reportes/convenios/colectivos-destino",
    response_model=list[schemas.ConvenioColectivoDestinoResponse],
)
@router.get(
    "/reportes/convenios/destinos",
    response_model=list[schemas.ConvenioColectivoDestinoResponse],
    include_in_schema=False,
)
def reporte_convenios_colectivos_destino(
    id_proyecto: int | None = None,
    id_entidad: int | None = Query(default=None, gt=0),
    id_proyecto_nucleo: int | None = Query(default=None, gt=0),
    id_convenio: int | None = Query(default=None, gt=0),
    id_asamblea: int | None = Query(default=None, gt=0),
    tipo_convenio: str | None = None,
    tipo_cop_operativo: str | None = None,
    destino_superficie: str | None = None,
    anio: int | None = Query(default=None, ge=2000, le=2200),
    mes: int | None = Query(default=None, ge=1, le=12),
    trimestre: int | None = Query(default=None, ge=1, le=4),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.ConvenioColectivoDestino)
    if id_proyecto is not None:
        require_project_access(db, user, id_proyecto)
        query = query.filter(models.ConvenioColectivoDestino.id_proyecto == id_proyecto)
    else:
        query = query.filter(
            models.ConvenioColectivoDestino.id_proyecto.in_(authorized_project_ids(db, user))
        )
    for field, value in (
        (models.ConvenioColectivoDestino.id_entidad, id_entidad),
        (models.ConvenioColectivoDestino.id_proyecto_nucleo, id_proyecto_nucleo),
        (models.ConvenioColectivoDestino.id_convenio, id_convenio),
        (models.ConvenioColectivoDestino.id_asamblea, id_asamblea),
        (models.ConvenioColectivoDestino.tipo_convenio, tipo_convenio),
        (models.ConvenioColectivoDestino.tipo_cop_operativo, tipo_cop_operativo),
        (models.ConvenioColectivoDestino.destino_superficie, destino_superficie),
        (models.ConvenioColectivoDestino.anio, anio),
        (models.ConvenioColectivoDestino.mes, mes),
        (models.ConvenioColectivoDestino.trimestre, trimestre),
    ):
        if value is not None:
            query = query.filter(field == value)
    return query.order_by(
        models.ConvenioColectivoDestino.id_proyecto,
        models.ConvenioColectivoDestino.id_convenio,
        models.ConvenioColectivoDestino.destino_superficie.nulls_last(),
    ).all()


@router.get(
    "/reportes/fifonafe/cobertura",
    response_model=list[schemas.FifonafeCoberturaResponse],
)
def reporte_fifonafe_cobertura(
    id_proyecto: int | None = None,
    ambito: str | None = None,
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.FifonafeCobertura)
    if id_proyecto is not None:
        require_project_access(db, user, id_proyecto)
        query = query.filter(models.FifonafeCobertura.id_proyecto == id_proyecto)
    else:
        query = query.filter(
            models.FifonafeCobertura.id_proyecto.in_(authorized_project_ids(db, user))
        )
    if ambito is not None:
        query = query.filter(models.FifonafeCobertura.ambito == ambito)
    return query.order_by(
        models.FifonafeCobertura.id_proyecto, models.FifonafeCobertura.ambito
    ).all()


@router.get(
    "/reportes/fifonafe/indicador-institucional",
    response_model=list[schemas.FifonafeIndicadorInstitucionalResponse],
)
def reporte_fifonafe_indicador_institucional(
    id_proyecto: int | None = None,
    anio: int | None = Query(default=None, ge=2000, le=2200),
    db: Session = Depends(get_db),
    user: models.Usuario = Depends(auth.RoleChecker(READ_ROLES)),
):
    query = db.query(models.FifonafeIndicadorInstitucional)
    if id_proyecto is not None:
        require_project_access(db, user, id_proyecto)
        query = query.filter(
            models.FifonafeIndicadorInstitucional.id_proyecto == id_proyecto
        )
    else:
        query = query.filter(
            models.FifonafeIndicadorInstitucional.id_proyecto.in_(
                authorized_project_ids(db, user)
            )
        )
    if anio is not None:
        query = query.filter(models.FifonafeIndicadorInstitucional.anio == anio)
    return query.order_by(
        models.FifonafeIndicadorInstitucional.id_proyecto,
        models.FifonafeIndicadorInstitucional.anio,
    ).all()


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
