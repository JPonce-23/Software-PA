"""Importación transaccional y territorial de núcleos agrarios."""

import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from .. import models
from .common import set_audit_context


def _tramos_contexto(
    db: Session,
    user: models.Usuario,
    ids_solicitados: list[int],
) -> list[int]:
    ids = list(dict.fromkeys(ids_solicitados))
    if user.rol == "geografo" and not ids:
        raise HTTPException(
            status_code=400,
            detail="Seleccione al menos un tramo asignado para la importación.",
        )
    if not ids:
        return []

    query = db.query(models.Tramo.id_tramo).filter(
        models.Tramo.id_tramo.in_(ids),
        models.Tramo.activo.is_(True),
        models.Tramo.geometria_linea.is_not(None),
    )
    if user.rol != "admin":
        query = query.join(
            models.UsuarioTramo,
            models.UsuarioTramo.id_tramo == models.Tramo.id_tramo,
        ).filter(
            models.UsuarioTramo.id_usuario == user.id_usuario,
            models.UsuarioTramo.activo.is_(True),
        )

    autorizados = {row[0] for row in query.all()}
    if autorizados != set(ids):
        raise HTTPException(
            status_code=403,
            detail="Uno o más tramos no están disponibles dentro de su alcance territorial.",
        )
    return ids


def _municipio_activo(db: Session, id_municipio: object) -> int | None:
    if isinstance(id_municipio, bool):
        return None
    try:
        valor = int(id_municipio)
    except (TypeError, ValueError):
        return None
    existe = db.query(models.Municipio.id_municipio).filter(
        models.Municipio.id_municipio == valor,
        models.Municipio.activo.is_(True),
    ).first()
    return valor if existe else None


def importar_geojson(
    db: Session,
    data: object,
    id_municipio_fallback: int | None,
    ids_tramo_contexto: list[int],
    user: models.Usuario,
) -> dict:
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection" or not isinstance(
        data.get("features"), list
    ):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser un FeatureCollection.",
        )

    features = data["features"]
    if not features:
        raise HTTPException(status_code=400, detail="El archivo no contiene features.")

    tramos = _tramos_contexto(db, user, ids_tramo_contexto)
    errores: list[dict] = []
    preparados: list[dict] = []
    municipios_cache: dict[object, int | None] = {}

    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            errores.append({"index": index, "motivo": "No es un Feature válido."})
            continue

        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") not in {
            "Polygon",
            "MultiPolygon",
        }:
            errores.append(
                {"index": index, "motivo": "La geometría debe ser Polygon o MultiPolygon."}
            )
            continue

        properties = feature.get("properties")
        if properties is None:
            properties = {}
        elif not isinstance(properties, dict):
            errores.append({"index": index, "motivo": "Properties debe ser un objeto."})
            continue

        nombre = properties.get("nombre_nucleo") or properties.get("nombre")
        if not isinstance(nombre, str) or not nombre.strip():
            errores.append({"index": index, "motivo": "Falta nombre_nucleo."})
            continue
        nombre = nombre.strip()
        if len(nombre) > 300:
            errores.append({"index": index, "motivo": "nombre_nucleo excede 300 caracteres."})
            continue

        tipo = properties.get("tipo_nucleo") or properties.get("tipo")
        if not isinstance(tipo, str) or tipo.lower() not in {"ejido", "comunidad"}:
            errores.append(
                {"index": index, "motivo": "tipo_nucleo debe ser ejido o comunidad."}
            )
            continue
        tipo = tipo.lower()

        comunidad_indigena = properties.get("comunidad_indigena", False)
        if not isinstance(comunidad_indigena, bool):
            errores.append(
                {"index": index, "motivo": "comunidad_indigena debe ser booleano."}
            )
            continue

        municipio_solicitado = properties.get("id_municipio")
        if municipio_solicitado is None:
            municipio_solicitado = id_municipio_fallback
        municipio_cache_key = repr(municipio_solicitado)
        if municipio_cache_key not in municipios_cache:
            municipios_cache[municipio_cache_key] = _municipio_activo(
                db,
                municipio_solicitado,
            )
        id_municipio = municipios_cache[municipio_cache_key]
        if id_municipio is None:
            errores.append({"index": index, "motivo": "id_municipio no existe o está inactivo."})
            continue

        residencia = properties.get("residencia")
        if residencia is not None and (
            not isinstance(residencia, str) or len(residencia) > 300
        ):
            errores.append(
                {"index": index, "motivo": "residencia debe ser texto de hasta 300 caracteres."}
            )
            continue

        geometry_json = json.dumps(geometry, separators=(",", ":"))
        try:
            with db.begin_nested():
                validacion = db.execute(
                    text(
                        """
                        WITH entrada AS (
                            SELECT ST_SetSRID(
                                ST_GeomFromGeoJSON(:geometry), 4326
                            ) AS geom
                        )
                        SELECT ST_IsValid(geom) AS valida,
                               NOT ST_IsEmpty(geom) AS no_vacia,
                               ST_GeometryType(geom) IN (
                                   'ST_Polygon', 'ST_MultiPolygon'
                               ) AS tipo_valido,
                               CASE
                                   WHEN :validar_contexto THEN EXISTS (
                                       SELECT 1
                                         FROM tramo t
                                        WHERE t.id_tramo = ANY(:ids_tramo)
                                          AND t.activo = TRUE
                                          AND ST_Intersects(geom, t.geometria_linea)
                                   )
                                   ELSE TRUE
                               END AS intersecta
                          FROM entrada
                        """
                    ),
                    {
                        "geometry": geometry_json,
                        "validar_contexto": bool(tramos),
                        "ids_tramo": tramos or [0],
                    },
                ).one()
        except DBAPIError:
            errores.append({"index": index, "motivo": "Geometría GeoJSON inválida."})
            continue

        if not validacion.valida or not validacion.no_vacia or not validacion.tipo_valido:
            errores.append({"index": index, "motivo": "Geometría vacía, inválida o no poligonal."})
            continue
        if not validacion.intersecta:
            errores.append(
                {"index": index, "motivo": "La geometría no intersecta los tramos seleccionados."}
            )
            continue

        preparados.append(
            {
                "index": index,
                "id_municipio": id_municipio,
                "nombre_nucleo": nombre,
                "tipo_nucleo": tipo,
                "comunidad_indigena": comunidad_indigena,
                "residencia": residencia,
                "geometry_json": geometry_json,
            }
        )

    if errores:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail={
                "mensaje": "Se abortó la importación porque hubo errores.",
                "total_procesados": len(features),
                "errores": errores,
            },
        )

    set_audit_context(db, user.id_usuario)
    creados: list[models.NucleoAgrario] = []
    try:
        for item in preparados:
            nucleo = models.NucleoAgrario(
                id_municipio=item["id_municipio"],
                nombre_nucleo=item["nombre_nucleo"],
                tipo_nucleo=item["tipo_nucleo"],
                comunidad_indigena=item["comunidad_indigena"],
                residencia=item["residencia"],
                fecha_creacion=datetime.now(timezone.utc),
                activo=True,
                geometria_poligono=func.ST_Multi(
                    func.ST_SetSRID(
                        func.ST_GeomFromGeoJSON(item["geometry_json"]),
                        4326,
                    )
                ),
            )
            db.add(nucleo)
            db.flush()
            creados.append(nucleo)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La importación entra en conflicto con la integridad de los datos.",
        ) from exc

    return {
        "mensaje": f"Se importaron {len(creados)} núcleos exitosamente.",
        "total": len(creados),
        "ids_nucleo": [nucleo.id_nucleo for nucleo in creados],
    }
