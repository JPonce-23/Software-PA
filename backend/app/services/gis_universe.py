"""Informational administrative counts; never used to select GIS destinations."""
from datetime import datetime, timezone

from sqlalchemy import text

from .. import schemas


WARNINGS = {
    'nucleos_vinculados_activos': ('SIN_NUCLEOS_VINCULADOS', 'El proyecto no tiene núcleos vinculados y activos.'),
    'parcelas_elegibles_vinculadas': ('SIN_PARCELAS_ELEGIBLES', 'El proyecto no tiene parcelas elegibles vinculadas administrativamente.'),
    'destinos_aplicables': ('SIN_DESTINOS_APLICABLES', 'No hay destinos administrativos aplicables al tipo de importación.'),
}


def context(**values):
    # Missing counts never produce an absence warning.
    warnings = [{'codigo':code,'mensaje':message} for field,(code,message) in WARNINGS.items()
                if values.get(field) == 0]
    return schemas.UniversoAdministrativoGisResponse(**values, advertencias=warnings).model_dump(mode='json')


def current_context(db, record, *, universe, nuclei):
    from .gis_reconciliation import PARCEL_TARGETS
    if record.tipo_objetivo in PARCEL_TARGETS:
        parcels = len({(pn.id_proyecto_nucleo,p.id_parcela) for pn,_,p in universe})
    else:
        # The same canonical eligibility view as matching; no catalog-wide or
        # spatial counts, and no parcel objects need to be loaded for nuclei.
        parcels = db.execute(text('SELECT count(*) FROM vw_gis_parcela_proyecto WHERE id_proyecto=:p'),
                             {'p':record.id_proyecto}).scalar_one()
    return context(origen='actual',disponibilidad='disponible',tipo_objetivo=record.tipo_objetivo,
                   fecha_evaluacion=datetime.now(timezone.utc),
                   nucleos_vinculados_activos=len({pn.id_proyecto_nucleo for pn,_,_ in nuclei}),
                   parcelas_elegibles_vinculadas=parcels,
                   destinos_aplicables=len({(pn.id_proyecto_nucleo,p.id_parcela if p else None)
                                           for pn,_,p in universe}))


def register_context(cycle, actual):
    """Only called for a new cycle, in the same transaction as its results."""
    snapshot = {**actual,'origen':'ciclo','id_ciclo':cycle.id_ciclo,
                'fecha_evaluacion':cycle.fecha_inicio.isoformat()}
    cycle.resumen = {**(cycle.resumen or {}),'universo_administrativo':snapshot}
    return snapshot


def historical_context(cycle, tipo_objetivo):
    from .gis_reconciliation import NUCLEUS_TARGETS, PARCEL_TARGETS
    if cycle is not None and cycle.resumen.get('universo_administrativo') is not None:
        return schemas.UniversoAdministrativoGisResponse.model_validate(
            cycle.resumen['universo_administrativo']).model_dump(mode='json')
    base = dict(origen='ciclo',tipo_objetivo=tipo_objetivo,
                id_ciclo=cycle.id_ciclo if cycle else None,
                fecha_evaluacion=cycle.fecha_inicio if cycle else None)
    if cycle is None or cycle.resumen.get('universo_historico_no_reconstruible') or tipo_objetivo not in NUCLEUS_TARGETS | PARCEL_TARGETS:
        return context(**base,disponibilidad='no_disponible')
    keys = {(item['id_proyecto_nucleo'],item.get('id_parcela')) for item in cycle.universo_destinos}
    # A parcel snapshot omits nuclei without eligible parcels. A nucleus
    # snapshot contains no parcel inventory. Neither can prove the other count.
    return context(**base,disponibilidad='parcial',destinos_aplicables=len(keys),
                   nucleos_vinculados_activos=len(keys) if tipo_objetivo in NUCLEUS_TARGETS else None,
                   parcelas_elegibles_vinculadas=len(keys) if tipo_objetivo in PARCEL_TARGETS else None)
