"""Importación transaccional y territorial de núcleos agrarios."""

import json
import unicodedata
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from .. import models
from .common import set_audit_context


def _normalizar_clave(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return "".join(char for char in ascii_value.lower() if char.isalnum())


def _property(properties: dict, *aliases: str):
    aliases_normalizados = {_normalizar_clave(alias) for alias in aliases}
    for key, value in properties.items():
        if key in aliases:
            return value
        if _normalizar_clave(key) in aliases_normalizados:
            return value
    return None


def _normalizar_tipo_nucleo(value: object) -> str | None:
    if value is None:
        return None
    normalized = _normalizar_clave(value)
    if normalized in {"ejido", "ej", "e"}:
        return "ejido"
    if normalized in {"comunidad", "comunidadagraria", "com", "c"}:
        return "comunidad"
    return None


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


def _municipio_por_nombre(
    db: Session,
    municipio_nombre: object,
    entidad_nombre: object = None,
    id_entidad: object = None,
) -> int | None:
    if not isinstance(municipio_nombre, str) or not municipio_nombre.strip():
        return None
    municipio_key = _normalizar_clave(municipio_nombre)
    entidad_key = _normalizar_clave(entidad_nombre) if entidad_nombre else None
    query = db.query(
        models.Municipio.id_municipio,
        models.Municipio.nombre,
        models.Municipio.id_entidad,
        models.EntidadFederativa.nombre.label("entidad_nombre"),
    ).join(
        models.EntidadFederativa,
        models.EntidadFederativa.id_entidad == models.Municipio.id_entidad,
    ).filter(
        models.Municipio.activo.is_(True),
        models.EntidadFederativa.activo.is_(True),
    )
    id_entidad_int = _entidad_activa(db, id_entidad)
    if id_entidad_int is not None:
        query = query.filter(models.Municipio.id_entidad == id_entidad_int)
    rows = query.all()
    matches = [
        row.id_municipio
        for row in rows
        if _normalizar_clave(row.nombre) == municipio_key
        and (not entidad_key or _normalizar_clave(row.entidad_nombre) == entidad_key)
    ]
    return matches[0] if len(matches) == 1 else None


def _entidad_activa(db: Session, id_entidad: object) -> int | None:
    if isinstance(id_entidad, bool):
        return None
    try:
        valor = int(id_entidad)
    except (TypeError, ValueError):
        return None
    existe = db.query(models.EntidadFederativa.id_entidad).filter(
        models.EntidadFederativa.id_entidad == valor,
        models.EntidadFederativa.activo.is_(True),
    ).first()
    return valor if existe else None


def importar_geojson(
    db: Session,
    data: object,
    id_municipio_fallback: int | None,
    ids_tramo_contexto: list[int],
    user: models.Usuario,
    tipo_nucleo_fallback: str | None = None,
    id_entidad_fallback: int | None = None,
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
    municipios_cache: dict[str, int | None] = {}

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

        nombre = _property(
            properties,
            "nombre_nucleo",
            "nombre",
            "name",
            "Name",
            "NOMBRE",
            "NOMBRE_NUCLEO",
            "NOM_NUCLEO_AGRARIO",
            "NOM_NUCLEO",
            "NOM_NUC",
            "NUCLEO",
            "nucleo",
            "ejido",
            "NOM_EJIDO",
            "NOMBRE_EJIDO",
        )
        if not isinstance(nombre, str) or not nombre.strip():
            errores.append({"index": index, "motivo": "Falta nombre_nucleo o un campo equivalente como NOMBRE, Name o NOM_NUCLEO."})
            continue
        nombre = nombre.strip()
        if len(nombre) > 300:
            errores.append({"index": index, "motivo": "nombre_nucleo excede 300 caracteres."})
            continue

        tipo = _normalizar_tipo_nucleo(
            _property(
                properties,
                "tipo_nucleo",
                "tipo",
                "TIPO",
                "TIPO_NUCLEO",
                "TIPO_NUC",
                "tipo_propiedad",
                "TIPO_PROPIEDAD",
                "REGIMEN",
                "regimen",
                "CLASE",
                "clase",
            )
        ) or _normalizar_tipo_nucleo(tipo_nucleo_fallback)
        if tipo not in {"ejido", "comunidad"}:
            errores.append(
                {"index": index, "motivo": "tipo_nucleo debe ser ejido o comunidad, o seleccione un tipo predeterminado."}
            )
            continue

        comunidad_indigena = _property(properties, "comunidad_indigena", "indigena", "INDIGENA")
        if comunidad_indigena is None:
            comunidad_indigena = False
        if not isinstance(comunidad_indigena, bool):
            errores.append(
                {"index": index, "motivo": "comunidad_indigena debe ser booleano."}
            )
            continue

        municipio_solicitado = _property(properties, "id_municipio", "ID_MUNICIPIO", "municipio_id")
        if municipio_solicitado is None:
            municipio_solicitado = id_municipio_fallback
        municipio_nombre = _property(
            properties,
            "municipio",
            "MUNICIPIO",
            "municipio_nombre",
            "MUNICIPIO_NOMBRE",
            "nom_mun",
            "NOM_MUN",
            "NOM_MPIO",
            "NOM_MUNICIPIO",
            "NOMBRE_MUNICIPIO",
        )
        entidad_nombre = _property(
            properties,
            "entidad",
            "ENTIDAD",
            "estado",
            "ESTADO",
            "NOM_ENT",
            "NOM_ENTIDAD",
            "nombre_entidad",
            "ENTIDAD_NOMBRE",
        )
        municipio_cache_key = repr((municipio_solicitado, municipio_nombre, entidad_nombre))
        if municipio_cache_key not in municipios_cache:
            municipios_cache[municipio_cache_key] = _municipio_por_nombre(
                db,
                municipio_nombre,
                entidad_nombre,
                id_entidad_fallback,
            ) or _municipio_activo(
                db,
                municipio_solicitado,
            )
        id_municipio = municipios_cache[municipio_cache_key]
        if id_municipio is None:
            errores.append({"index": index, "motivo": "id_municipio no existe, el municipio por nombre es ambiguo o no se seleccionó municipio predeterminado."})
            continue

        residencia = _property(properties, "residencia", "RESIDENCIA")
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
                                         FROM franja_derecho_via f
                                         JOIN tramo t ON t.id_tramo = f.id_tramo
                                        WHERE f.id_tramo = ANY(:ids_tramo)
                                          AND f.activo = TRUE
                                          AND t.activo = TRUE
                                          AND ST_Intersects(geom, f.geometria_poligono)
                                          AND ST_Area(
                                              ST_CollectionExtract(
                                                  ST_Intersection(geom, f.geometria_poligono),
                                                  3
                                              )::geography
                                          ) > 0
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
                {"index": index, "motivo": "La geometría no tiene superficie de intersección con la franja activa de los tramos seleccionados."}
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

    preparados = _agrupar_nucleos(db, preparados)

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


def _nucleo_group_key(item: dict) -> str:
    return ":".join([
        str(item["id_municipio"]),
        str(item["tipo_nucleo"]),
        _normalizar_clave(item["nombre_nucleo"]),
    ])


def _validar_nucleo_disponible(db: Session, item: dict) -> None:
    nombre_key = _normalizar_clave(item["nombre_nucleo"])
    candidatos = db.query(
        models.NucleoAgrario.id_nucleo,
        models.NucleoAgrario.nombre_nucleo,
    ).filter(
        models.NucleoAgrario.id_municipio == item["id_municipio"],
        models.NucleoAgrario.tipo_nucleo == item["tipo_nucleo"],
        models.NucleoAgrario.activo.is_(True),
    ).all()
    if any(_normalizar_clave(row.nombre_nucleo) == nombre_key for row in candidatos):
        raise HTTPException(
            status_code=409,
            detail="Ya existe un núcleo agrario activo con ese nombre, tipo y municipio.",
        )


def _agrupar_nucleos(db: Session, items: list[dict]) -> list[dict]:
    grupos: dict[str, list[dict]] = {}
    orden: list[str] = []
    for item in items:
        key = _nucleo_group_key(item)
        if key not in grupos:
            grupos[key] = []
            orden.append(key)
        grupos[key].append(item)

    agrupados: list[dict] = []
    for key in orden:
        group = grupos[key]
        base = {**group[0]}
        _validar_nucleo_disponible(db, base)
        if len(group) > 1:
            base["geometry_json"] = _fusionar_poligonos(
                db,
                [item["geometry_json"] for item in group],
            )
        agrupados.append(base)
    return agrupados


def _fusionar_poligonos(db: Session, geometries_json: list[str]) -> str:
    try:
        row = db.execute(
            text(
                """
                WITH entrada AS (
                    SELECT ST_SetSRID(ST_GeomFromGeoJSON(raw.geometry_json), 4326) AS geom
                      FROM unnest(:geometries) AS raw(geometry_json)
                ),
                fusion AS (
                    SELECT ST_Multi(
                               ST_CollectionExtract(
                                   ST_UnaryUnion(ST_Collect(geom)),
                                   3
                               )
                           ) AS geom
                      FROM entrada
                )
                SELECT ST_AsGeoJSON(geom) AS geometry_json,
                       ST_IsValid(geom) AS valida,
                       NOT ST_IsEmpty(geom) AS no_vacia,
                       ST_GeometryType(geom) AS tipo
                  FROM fusion
                """
            ),
            {"geometries": geometries_json},
        ).mappings().one()
    except DBAPIError as exc:
        raise HTTPException(status_code=400, detail="No fue posible fusionar las geometrías del núcleo.") from exc

    if not row["valida"] or not row["no_vacia"] or row["tipo"] != "ST_MultiPolygon":
        raise HTTPException(status_code=400, detail="La fusión de geometrías del núcleo no produjo un multipolígono válido.")
    return row["geometry_json"]
