"""Carga datos reproducibles del flujo territorial para dos proyectos.

El script usa los trazos activos de la base y los KML RAN locales. No inventa
un trazo: si un proyecto no tiene una franja lineal activa, termina con error.
Las secciones de prueba se generan como una banda tecnica de 25 m alrededor
de cada division del eje, exclusivamente para poder ejercitar afectaciones.

Uso dentro del contenedor backend:
    python scripts/seed_proceso_proyectos.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.services.common import set_audit_context  # noqa: E402
from app.services.gis_ingestion import inspect_dataset, iter_features  # noqa: E402


PROJECTS = (
    {
        "name": "Irapuato - Guadalajara",
        "key": "IRAPUATO_GUADALAJARA",
        "files": ("guanajuato", "jalisco"),
    },
    {
        "name": "México - Querétaro",
        "key": "MEXICO_QUERETARO",
        "files": ("mexico", "queretaro"),
    },
)
TODAY = date(2026, 8, 18)


def normalize(value: object) -> str:
    text_value = unicodedata.normalize("NFKD", str(value or ""))
    text_value = "".join(char for char in text_value if not unicodedata.combining(char))
    return " ".join(text_value.casefold().split())


def commit(db, user_id: int) -> None:
    set_audit_context(db, user_id)
    db.commit()


def scalar(db, sql: str, params: dict) -> object:
    return db.execute(text(sql), params).scalar_one_or_none()


def get_seed_user(db):
    requested = os.getenv("SEED_USER_ID")
    if requested:
        user = db.get(models.Usuario, int(requested))
    else:
        user = (
            db.query(models.Usuario)
            .filter(models.Usuario.activo.is_(True), models.Usuario.rol == "admin")
            .order_by(models.Usuario.id_usuario)
            .first()
        )
    if not user:
        raise RuntimeError("No existe un usuario admin activo para la auditoria del seed.")
    return user


def find_project(db, name: str):
    project = (
        db.query(models.Proyecto)
        .filter(models.Proyecto.nombre_proyecto == name, models.Proyecto.activo.is_(True))
        .first()
    )
    if not project:
        raise RuntimeError(
            f'No existe el proyecto activo "{name}". Cree el proyecto y cargue su trazo antes de ejecutar el seed.'
        )
    franja = (
        db.query(models.FranjaDerechoVia)
        .filter(
            models.FranjaDerechoVia.id_proyecto == project.id_proyecto,
            models.FranjaDerechoVia.activo.is_(True),
            models.FranjaDerechoVia.geometria_linea.isnot(None),
        )
        .order_by(models.FranjaDerechoVia.version.desc())
        .first()
    )
    if not franja:
        raise RuntimeError(f'El proyecto "{name}" no tiene un trazo lineal activo.')
    return project, franja


def line_group(db, franja_id: int, low: int, high: int) -> str:
    result = scalar(
        db,
        """
        SELECT ST_AsText(ST_Multi(ST_CollectionExtract(ST_Collect(
            ST_GeometryN(geometria_linea, n)
        ), 2)))
          FROM franja_derecho_via
          CROSS JOIN LATERAL generate_series(:low, :high) AS n
         WHERE id_franja = :franja
        """,
        {"franja": franja_id, "low": low, "high": high},
    )
    if not result or result == "MULTILINESTRING EMPTY":
        raise RuntimeError(f"No se pudo formar un segmento para la franja {franja_id}.")
    return str(result)


def ensure_tramos_and_sections(db, project, franja, user_id: int) -> list[dict]:
    tramos = (
        db.query(models.Tramo)
        .filter(models.Tramo.id_proyecto == project.id_proyecto, models.Tramo.activo.is_(True))
        .order_by(models.Tramo.id_tramo)
        .all()
    )
    if not tramos:
        parts = int(
            scalar(
                db,
                "SELECT ST_NumGeometries(geometria_linea) FROM franja_derecho_via WHERE id_franja = :id",
                {"id": franja.id_franja},
            )
            or 0
        )
        if parts < 1:
            raise RuntimeError(f"La franja {franja.id_franja} no contiene componentes lineales.")
        count = 2 if parts > 1 else 1
        for index in range(count):
            tramo = models.Tramo(
                id_proyecto=project.id_proyecto,
                clave_tramo=f"SEED-{project.id_proyecto}-{index + 1:02d}",
                nombre_tramo=f"Segmento de prueba {index + 1:02d}",
                descripcion="División reproducible del trazo activo para datos de demostración.",
                fecha_registro=TODAY,
                activo=True,
            )
            db.add(tramo)
            tramos.append(tramo)
        commit(db, user_id)

    sections: list[dict] = []
    parts = int(
        scalar(
            db,
            "SELECT ST_NumGeometries(geometria_linea) FROM franja_derecho_via WHERE id_franja = :id",
            {"id": franja.id_franja},
        )
        or 0
    )
    for index, tramo in enumerate(tramos):
        low = (parts * index) // len(tramos) + 1
        high = (parts * (index + 1)) // len(tramos)
        high = max(low, high)
        line_wkt = line_group(db, franja.id_franja, low, high)
        section_id = scalar(
            db,
            "SELECT id_seccion FROM seccion_derecho_via WHERE id_franja = :franja AND id_tramo = :tramo AND activo",
            {"franja": franja.id_franja, "tramo": tramo.id_tramo},
        )
        if section_id is None:
            set_audit_context(db, user_id)
            section_id = db.execute(
                text(
                    """
                    INSERT INTO seccion_derecho_via
                        (id_franja, id_tramo, geometria_poligono, fuente, activo)
                    VALUES (
                        :franja, :tramo,
                        ST_Multi(ST_CollectionExtract(ST_Transform(
                            ST_Buffer(ST_Transform(ST_GeomFromText(:line, 4326), 3857), 25),
                            4326
                        ), 3)),
                        :fuente, TRUE
                    )
                    RETURNING id_seccion
                    """
                ),
                {
                    "franja": franja.id_franja,
                    "tramo": tramo.id_tramo,
                    "line": line_wkt,
                    "fuente": "SEED_TRAZO_ACTIVO_BUFFER_25M",
                },
            ).scalar_one()
            commit(db, user_id)
        sections.append({"tramo": tramo, "section_id": int(section_id), "line_wkt": line_wkt})
    return sections


def catalogs(db):
    entities = {normalize(item.nombre): item for item in db.query(models.EntidadFederativa).filter_by(activo=True)}
    municipalities = {}
    for item in db.query(models.Municipio).filter_by(activo=True):
        municipalities[(item.id_entidad, normalize(item.nombre))] = item
    return entities, municipalities


def resolve_feature(db, properties: dict, entities, municipalities):
    entity = entities.get(normalize(properties.get("NombreEntidadFederativa")))
    if not entity:
        return None
    municipality = municipalities.get((entity.id_entidad, normalize(properties.get("NombreMunicipio"))))
    if not municipality:
        return None
    kind = normalize(properties.get("TipoNucleoAgrario"))
    if kind not in {"ejido", "comunidad"}:
        return None
    name = str(properties.get("NombreNucleoAgrario") or properties.get("Name") or "").strip()
    source_id = str(properties.get("IdNucleoAgrario") or "").strip()
    if not name or not source_id:
        return None
    return entity, municipality, name, kind, source_id


def intersects_franja(db, franja_id: int, geometry: dict) -> bool:
    value = scalar(
        db,
        """
        SELECT ST_Intersects(
            ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_GeomFromGeoJSON(:geometry)), 3)),
            geometria_linea
        )
          FROM franja_derecho_via
         WHERE id_franja = :franja AND activo
        """,
        {"franja": franja_id, "geometry": json.dumps(geometry),},
    )
    return bool(value)


def ensure_nucleus(db, resolved, properties, geometry: dict, source: str, user_id: int):
    entity, municipality, name, kind, source_id = resolved
    existing = (
        db.query(models.NucleoAgrario)
        .filter(
            models.NucleoAgrario.id_municipio == municipality.id_municipio,
            models.NucleoAgrario.id_nucleo_fuente == source_id,
            models.NucleoAgrario.fuente_datos == source,
            models.NucleoAgrario.activo.is_(True),
        )
        .first()
    )
    if existing:
        return existing, False
    set_audit_context(db, user_id)
    nucleus_id = db.execute(
        text(
            """
            INSERT INTO nucleo_agrario
                (id_municipio, nombre_nucleo, tipo_nucleo, comunidad_indigena,
                 geometria_poligono, fuente_datos, id_entidad_fuente,
                 id_municipio_fuente, id_nucleo_fuente, alcance_identidad_fuente,
                 fecha_creacion, activo)
            VALUES (
                :municipio, :nombre, :tipo, FALSE,
                ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_GeomFromGeoJSON(:geometry)), 3)),
                :fuente, :entidad_fuente, :municipio_fuente, :nucleo_fuente,
                'territorial', :fecha, TRUE
            )
            RETURNING id_nucleo
            """
        ),
        {
            "municipio": municipality.id_municipio,
            "nombre": name,
            "tipo": kind,
            "geometry": json.dumps(geometry),
            "fuente": source,
            "entidad_fuente": str(properties.get("IdEntidadFederativa") or ""),
            "municipio_fuente": str(properties.get("IdMunicipio") or ""),
            "nucleo_fuente": source_id,
            "fecha": datetime.now(timezone.utc),
        },
    ).scalar_one()
    commit(db, user_id)
    return db.get(models.NucleoAgrario, nucleus_id), True


def choose_section(db, nucleus_id: int, sections: list[dict]):
    best = None
    for item in sections:
        row = db.execute(
            text(
                """
                SELECT ST_Area(
                    ST_CollectionExtract(ST_Intersection(n.geometria_poligono, s.geometria_poligono), 3)::geography
                )
                  FROM nucleo_agrario n
                  JOIN seccion_derecho_via s ON s.id_seccion = :section
                 WHERE n.id_nucleo = :nucleo
                """
            ),
            {"section": item["section_id"], "nucleo": nucleus_id},
        ).scalar_one_or_none()
        area = float(row or 0)
        if area > (best["area"] if best else 0):
            best = {**item, "area": area}
    return best


def ensure_tramo_nucleo(db, nucleus, section, user_id: int):
    existing = (
        db.query(models.TramoNucleo)
        .filter_by(id_tramo=section["tramo"].id_tramo, id_nucleo=nucleus.id_nucleo, activo=True)
        .first()
    )
    if existing:
        return existing, False
    next_number = (
        db.query(models.TramoNucleo)
        .filter_by(id_tramo=section["tramo"].id_tramo, activo=True)
        .count()
        + 1
    )
    set_audit_context(db, user_id)
    tn_id = db.execute(
        text(
            """
            INSERT INTO tramo_nucleo
                (id_tramo, id_nucleo, consecutivo, numero_tramo, geometria_segmento,
                 longitud_m, activo)
            SELECT :tramo, :nucleo, :consecutivo, :numero,
                   ST_Multi(ST_CollectionExtract(ST_Intersection(
                       n.geometria_poligono, ST_GeomFromText(:line, 4326)
                   ), 2)),
                   ST_Length(ST_CollectionExtract(ST_Intersection(
                       n.geometria_poligono, ST_GeomFromText(:line, 4326)
                   ), 2)::geography), TRUE
              FROM nucleo_agrario n
             WHERE n.id_nucleo = :nucleo
            RETURNING id_tramo_nucleo
            """
        ),
        {
            "tramo": section["tramo"].id_tramo,
            "nucleo": nucleus.id_nucleo,
            "consecutivo": next_number,
            "numero": f"{section['tramo'].clave_tramo}-{next_number:03d}",
            "line": section["line_wkt"],
        },
    ).scalar_one()
    commit(db, user_id)
    return db.get(models.TramoNucleo, tn_id), True


def ensure_activity(db, tn, kind: str, user_id: int):
    activity = (
        db.query(models.ActividadCampo)
        .filter_by(id_tramo_nucleo=tn.id_tramo_nucleo, tipo_actividad=kind, contexto_proceso="cop_original", activo=True)
        .first()
    )
    if activity:
        return activity
    activity = models.ActividadCampo(
        id_tramo_nucleo=tn.id_tramo_nucleo,
        tipo_actividad=kind,
        contexto_proceso="cop_original",
        fecha_programada=TODAY,
        fecha_realizada=TODAY,
        resultado="Realizada satisfactoriamente; datos simulados.",
        id_usuario_registro=user_id,
        fecha_registro=datetime.now(timezone.utc),
        activo=True,
    )
    db.add(activity)
    commit(db, user_id)
    return activity


def ensure_padron(db, nucleus, user_id: int):
    existing = db.query(models.PadronHistorial).filter_by(id_nucleo=nucleus.id_nucleo, activo=True).first()
    if existing:
        return existing
    padron = models.PadronHistorial(
        id_nucleo=nucleus.id_nucleo,
        fecha_padron=TODAY,
        numero_ejidatarios_comuneros=120,
        id_usuario_registro=user_id,
        fecha_registro=datetime.now(timezone.utc),
        activo=True,
    )
    db.add(padron)
    commit(db, user_id)
    return padron


def ensure_orv(db, nucleus, user_id: int):
    existing = db.query(models.Orv).filter_by(id_nucleo=nucleus.id_nucleo, activo=True).first()
    if existing:
        return existing
    orv = models.Orv(
        id_nucleo=nucleus.id_nucleo,
        numero_orv=f"SEED-ORV-{nucleus.id_nucleo}",
        inicio_vigencia=date(2025, 1, 1),
        fin_vigencia=date(2027, 12, 31),
        acta_eleccion_inscrita_ran=True,
        documentacion_disponible=True,
        comisariado_presidente="Presidente simulado",
        comisariado_secretario="Secretario simulado",
        comisariado_tesorero="Tesorero simulado",
        activo=True,
    )
    db.add(orv)
    commit(db, user_id)
    return orv


def ensure_person_and_parcel(db, nucleus, section, user_id: int):
    token = f"SEED-TITULAR-{nucleus.id_nucleo}"
    person = db.query(models.Persona).filter_by(clave_origen_legacy=token).first()
    if not person:
        person = models.Persona(
            nombre="Titular de prueba",
            apellido_paterno=f"Nucleo {nucleus.id_nucleo}",
            datos_identidad_incompletos=True,
            origen_registro="captura_sistema",
            clave_origen_legacy=token,
        )
        db.add(person)
        commit(db, user_id)
    membership = db.query(models.PersonaNucleo).filter_by(
        id_nucleo=nucleus.id_nucleo,
        id_persona=person.id_persona,
        activo=True,
    ).first()
    if not membership:
        db.add(models.PersonaNucleo(
            id_nucleo=nucleus.id_nucleo,
            id_persona=person.id_persona,
            calidad_agraria="ejidatario",
            fecha_inicio=TODAY,
            activo=True,
        ))
        commit(db, user_id)
    parcel = db.query(models.Parcela).filter_by(no_parcela_ppt=f"SEED-PPT-{nucleus.id_nucleo}", activo=True).first()
    if not parcel:
        set_audit_context(db, user_id)
        parcel_id = db.execute(
            text(
                """
                INSERT INTO parcela
                    (id_nucleo, tipo_parcela, no_parcela_ppt, nombre_titular,
                     certificado_parcelario, folio_derechos, geometria_poligono,
                     documentacion_disponible, activo)
                SELECT :nucleo, 'individual', :ppt, :titular,
                       :certificado, :folio,
                       ST_Multi(ST_CollectionExtract(ST_Intersection(
                           n.geometria_poligono, s.geometria_poligono
                       ), 3)), FALSE, TRUE
                  FROM nucleo_agrario n
                  JOIN seccion_derecho_via s ON s.id_seccion = :section
                 WHERE n.id_nucleo = :nucleo
                RETURNING id_parcela
                """
            ),
            {
                "nucleo": nucleus.id_nucleo,
                "section": section["section_id"],
                "ppt": f"SEED-PPT-{nucleus.id_nucleo}",
                "titular": person.nombre,
                "certificado": f"SEED-CERT-{nucleus.id_nucleo}",
                "folio": f"SEED-FOLIO-{nucleus.id_nucleo}",
            },
        ).scalar_one()
        commit(db, user_id)
        parcel = db.get(models.Parcela, parcel_id)
    if not parcel.documentacion_disponible:
        parcel.documentacion_disponible = True
        parcel.certificado_parcelario = parcel.certificado_parcelario or f"SEED-CERT-{nucleus.id_nucleo}"
        parcel.folio_derechos = parcel.folio_derechos or f"SEED-FOLIO-{nucleus.id_nucleo}"
        commit(db, user_id)
    link = db.query(models.ParcelaTitular).filter_by(id_parcela=parcel.id_parcela, id_persona=person.id_persona, activo=True).first()
    if not link:
        db.add(models.ParcelaTitular(
            id_parcela=parcel.id_parcela,
            id_nucleo=nucleus.id_nucleo,
            id_persona=person.id_persona,
            tipo_derecho="titular",
            porcentaje_participacion=Decimal("100"),
            fecha_inicio=TODAY,
            activo=True,
        ))
        commit(db, user_id)
    return parcel, person


def ensure_affectation(db, nucleus, tn, section, parcel, index: int, user_id: int):
    existing = db.query(models.Afectacion).filter_by(id_tramo_nucleo=tn.id_tramo_nucleo, activo=True).first()
    if existing:
        return existing
    kind = "colectivo" if index % 3 == 0 else "individual"
    set_audit_context(db, user_id)
    affected_id = db.execute(
        text(
            """
            INSERT INTO afectacion
                (id_nucleo, id_tramo_nucleo, id_parcela, tipo_afectacion,
                 tipo_tenencia, subtipo_tenencia, destino_superficie,
                 superficie_afectada_ha, geometria_afectacion,
                 num_personas_afectadas, situacion_juridica,
                 documentacion_disponible, origen_registro, activo)
            SELECT :nucleo, :tn, :parcela, :tipo, 'social', 'ejidal',
                   'derecho_de_via',
                   ST_Area(ST_CollectionExtract(ST_Intersection(
                       n.geometria_poligono, s.geometria_poligono
                   ), 3)::geography) / 10000,
                   ST_Multi(ST_CollectionExtract(ST_Intersection(
                       n.geometria_poligono, s.geometria_poligono
                   ), 3)),
                   CASE WHEN :tipo = 'colectivo' THEN 120 ELSE 1 END,
                   'En integración; datos simulados.', FALSE, 'captura_sistema', TRUE
              FROM nucleo_agrario n
              JOIN seccion_derecho_via s ON s.id_seccion = :section
             WHERE n.id_nucleo = :nucleo
            RETURNING id_afectacion
            """
        ),
        {
            "nucleo": nucleus.id_nucleo,
            "tn": tn.id_tramo_nucleo,
            "parcela": parcel.id_parcela if kind == "individual" and parcel else None,
            "tipo": kind,
            "section": section["section_id"],
        },
    ).scalar_one()
    commit(db, user_id)
    return db.get(models.Afectacion, affected_id)


def ensure_collective_assembly(db, nucleus, tn, affectation, user_id: int):
    existing = db.query(models.Asamblea).filter_by(id_afectacion=affectation.id_afectacion, tipo_asamblea="anuencia", activo=True).first()
    if existing:
        return existing
    assembly = models.Asamblea(
        id_nucleo=nucleus.id_nucleo,
        id_tramo_nucleo=tn.id_tramo_nucleo,
        id_afectacion=affectation.id_afectacion,
        id_ciclo_afectacion=None,
        tipo_asamblea="anuencia",
        contexto_proceso="cop_original",
        fecha_realizada=date(2025, 4, 15),
        resultado_anuencia="otorgada",
        estatus_asamblea="completo",
        ingreso_ran_fecha=date(2025, 5, 10),
        numero_solicitud_ran=f"SEED-SOL-{affectation.id_afectacion}",
        calificacion_registral_ran="procedente",
        acta_inscripcion_fecha_ran=date(2025, 6, 20),
        documentacion_disponible=True,
        id_padron=None,
        id_usuario_registro=user_id,
        activo=True,
    )
    cycle = db.query(models.AfectacionCiclo).filter_by(id_afectacion=affectation.id_afectacion, activo=True).one()
    assembly.id_ciclo_afectacion = cycle.id_ciclo_afectacion
    db.add(assembly)
    commit(db, user_id)
    return assembly


def ensure_convenio_and_followup(db, nucleus, tn, affectation, index: int, user_id: int):
    cycle = db.query(models.AfectacionCiclo).filter_by(id_afectacion=affectation.id_afectacion, activo=True).one()
    existing = db.query(models.Convenio).filter_by(id_ciclo_afectacion=cycle.id_ciclo_afectacion, activo=True).first()
    if existing:
        return existing
    stage = index % 4
    assembly = ensure_collective_assembly(db, nucleus, tn, affectation, user_id) if affectation.tipo_afectacion == "colectivo" else None
    signed = stage < 3
    entered_ran = stage == 0 or stage == 1
    registered = stage == 0
    if not signed:
        return None
    convenio = models.Convenio(
        id_tramo_nucleo=tn.id_tramo_nucleo,
        id_afectacion=affectation.id_afectacion,
        id_ciclo_afectacion=cycle.id_ciclo_afectacion,
        tipo_afectacion=affectation.tipo_afectacion,
        tipo_convenio="cop_original",
        fecha_firma=date(2025, 7, 1),
        superficie_real_afectada_ha=(
            affectation.superficie_afectada_ha
            if affectation.tipo_afectacion == "colectivo"
            else None
        ),
        superficie_total_ha=(
            affectation.superficie_afectada_ha
            if affectation.tipo_afectacion == "individual"
            else None
        ),
        monto_100=Decimal("100000.00"),
        monto_bdt=Decimal("10000.00") if affectation.tipo_afectacion == "colectivo" else None,
        ingreso_ran_fecha=date(2025, 8, 1) if entered_ran else None,
        numero_solicitud_ingreso=f"SEED-CONV-{affectation.id_afectacion}" if entered_ran else None,
        calificacion_registral="procedente" if registered else None,
        convenio_inscrito_fecha_ran=date(2025, 9, 1) if registered else None,
        id_asamblea_autorizacion=assembly.id_asamblea if assembly else None,
        documentacion_disponible=True,
        id_usuario_registro=user_id,
        activo=True,
    )
    db.add(convenio)
    commit(db, user_id)
    if not registered:
        return convenio

    no_conflicts = models.TramiteFifonafe(
        id_tramo_nucleo=tn.id_tramo_nucleo,
        id_convenio=convenio.id_convenio,
        id_afectacion=affectation.id_afectacion,
        id_ciclo_afectacion=cycle.id_ciclo_afectacion,
        tipo_afectacion=affectation.tipo_afectacion,
        tipo_tramite="informe_no_conflictos",
        estatus="completo",
        hay_conflictos=False,
        no_oficio_fifonafe_a_dgaopr=f"SEED-NC-01-{affectation.id_afectacion}",
        no_oficio_dgaopr_a_repr=f"SEED-NC-02-{affectation.id_afectacion}",
        no_oficio_rpta_repr_a_dgaopr=f"SEED-NC-03-{affectation.id_afectacion}",
        no_oficio_rpta_dgaopr_a_fifonafe=f"SEED-NC-04-{affectation.id_afectacion}",
        fecha_oficio_fifonafe_a_dgaopr= date(2025, 9, 10),
        fecha_oficio_dgaopr_a_repr=date(2025, 9, 12),
        fecha_oficio_rpta_repr_a_dgaopr=date(2025, 9, 15),
        fecha_oficio_rpta_dgaopr_a_fifonafe=date(2025, 9, 18),
        activo=True,
    )
    db.add(no_conflicts)
    commit(db, user_id)
    indemnization = models.TramiteFifonafe(
        id_tramo_nucleo=tn.id_tramo_nucleo,
        id_convenio=convenio.id_convenio,
        id_afectacion=affectation.id_afectacion,
        id_ciclo_afectacion=cycle.id_ciclo_afectacion,
        id_tramite_no_conflictos=no_conflicts.id_tramite_fifonafe,
        tipo_afectacion=affectation.tipo_afectacion,
        tipo_tramite="indemnizacion",
        estatus="pendiente",
        hay_conflictos=False,
        no_oficio_fifonafe_a_dgaopr=f"SEED-IND-01-{affectation.id_afectacion}",
        no_oficio_dgaopr_a_repr=f"SEED-IND-02-{affectation.id_afectacion}",
        no_oficio_rpta_repr_a_dgaopr=f"SEED-IND-03-{affectation.id_afectacion}",
        no_oficio_rpta_dgaopr_a_fifonafe=f"SEED-IND-04-{affectation.id_afectacion}",
        fecha_oficio_fifonafe_a_dgaopr=date(2025, 10, 5),
        fecha_oficio_dgaopr_a_repr=date(2025, 10, 7),
        fecha_oficio_rpta_repr_a_dgaopr=date(2025, 10, 10),
        fecha_oficio_rpta_dgaopr_a_fifonafe=date(2025, 10, 12),
        activo=True,
    )
    db.add(indemnization)
    commit(db, user_id)
    db.add(models.PagoIndemnizacion(
        id_tramite_fifonafe=indemnization.id_tramite_fifonafe,
        monto_pagado=Decimal("110000.00") if affectation.tipo_afectacion == "colectivo" else Decimal("100000.00"),
        fecha_pago=date(2025, 10, 1),
        tipo_pago="total",
        medio_pago="transferencia",
        referencia_bancaria=f"SEED-PAGO-{affectation.id_afectacion}",
        beneficiario_externo=f"Beneficiario simulado {nucleus.id_nucleo}",
        activo=True,
    ))
    commit(db, user_id)
    indemnization.estatus = "completo"
    commit(db, user_id)
    return convenio


def process_project(db, project_config: dict, user_id: int, entities, municipalities) -> dict:
    project, franja = find_project(db, project_config["name"])
    sections = ensure_tramos_and_sections(db, project, franja, user_id)
    selected = created = 0
    source = f"SEED_RAN_{project_config['key']}"
    seen_identities: set[tuple[int, str]] = set()
    data_root = ROOT / "seed_data"
    for state in project_config["files"]:
        path = data_root / f"ran_nucleosagrarios_{state}.kml"
        dataset = inspect_dataset(path)
        for _, raw in iter_features(path, dataset):
            properties = raw.get("properties") or {}
            resolved = resolve_feature(db, properties, entities, municipalities)
            if not resolved or not intersects_franja(db, franja.id_franja, raw.get("geometry") or {}):
                continue
            identity = (resolved[1].id_municipio, resolved[4])
            if identity in seen_identities:
                continue
            seen_identities.add(identity)
            nucleus, was_created = ensure_nucleus(db, resolved, properties, raw["geometry"], source, user_id)
            selected += 1
            created += int(was_created)
            section = choose_section(db, nucleus.id_nucleo, sections)
            if not section:
                continue
            tn, _ = ensure_tramo_nucleo(db, nucleus, section, user_id)
            ensure_padron(db, nucleus, user_id)
            ensure_orv(db, nucleus, user_id)
            ensure_activity(db, tn, "sensibilizacion", user_id)
            ensure_activity(db, tn, "caminamiento", user_id)
            parcel, _ = ensure_person_and_parcel(db, nucleus, section, user_id)
            affectation = ensure_affectation(db, nucleus, tn, section, parcel, selected, user_id)
            ensure_convenio_and_followup(db, nucleus, tn, affectation, selected, user_id)
    return {"project": project_config["name"], "selected": selected, "nuclei_created": created}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    db = SessionLocal()
    try:
        user = get_seed_user(db)
        entities, municipalities = catalogs(db)
        summaries = [process_project(db, config, user.id_usuario, entities, municipalities) for config in PROJECTS]
        print(json.dumps({"seed": "proceso_proyectos", "results": summaries}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
