"""Staging, validacion y confirmacion del importador geoespacial de nucleos."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
import re
import unicodedata
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path, PurePath
from typing import Any, Iterable

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, or_, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from .. import models
from ..database import SessionLocal
from ..schemas_importaciones import FeatureRevisionRequest, MapeoImportacionRequest
from .common import set_audit_context
from .gis_ingestion import DatasetInfo, IngestionError, inspect_dataset, iter_features


CANONICAL_FIELDS = {
    "nombre_nucleo",
    "tipo_nucleo",
    "entidad",
    "clave_entidad_inegi",
    "municipio",
    "clave_municipio_inegi",
    "id_entidad_fuente",
    "id_municipio_fuente",
    "id_nucleo_fuente",
    "comunidad_indigena",
    "residencia",
}
REQUIRED_FIELDS = {"nombre_nucleo", "tipo_nucleo"}
COLUMN_EQUIVALENTS = {
    "nombre_nucleo": ("name", "nombre", "nombrenucleoagrario", "nombre_nucleo", "nom_nucleo"),
    "tipo_nucleo": ("tiponucleoagrario", "tipo_nucleo", "regimen", "tipo"),
    "entidad": ("nombreentidadfederativa", "estado", "entidad", "nom_ent"),
    "clave_entidad_inegi": ("cve_ent", "clave_entidad_inegi", "claveentidad"),
    "municipio": ("nombremunicipio", "nom_mun", "municipio", "nombre_municipio"),
    "clave_municipio_inegi": ("cvegeo", "clave_municipio_inegi", "cve_mun_inegi"),
    "id_entidad_fuente": ("identidad", "identidadfederativa", "id_entidad_fuente"),
    "id_municipio_fuente": ("idmunicipio", "id_municipio_fuente", "cve_mun"),
    "id_nucleo_fuente": ("idnucleo", "idnucleoagrario", "id_nucleo_fuente", "fid", "objectid"),
    "comunidad_indigena": ("comunidadindigena", "comunidad_indigena"),
    "residencia": ("residencia",),
}
TYPE_EQUIVALENTS = {
    "ejido": "ejido",
    "ejidal": "ejido",
    "ej": "ejido",
    "e": "ejido",
    "comunidad": "comunidad",
    "comunal": "comunidad",
    "com": "comunidad",
    "c": "comunidad",
}
RUNNING_STATES = {"analizando", "normalizando", "resolviendo", "confirmando", "importando"}
logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKD", str(value).strip())
    ascii_value = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def normalize_column(value: str) -> str:
    return normalize_text(value).replace(" ", "")


def suggest_mapping(columns: Iterable[str]) -> dict[str, str]:
    by_normalized: dict[str, list[str]] = defaultdict(list)
    for column in columns:
        by_normalized[normalize_column(column)].append(column)
    mapping: dict[str, str] = {}
    for target, candidates in COLUMN_EQUIVALENTS.items():
        matches = {
            source
            for candidate in candidates
            for source in by_normalized.get(normalize_column(candidate), [])
        }
        if len(matches) == 1:
            mapping[target] = matches.pop()
    return mapping


def validate_mapping(mapping: dict[str, str], columns: Iterable[str]) -> None:
    unknown_targets = sorted(set(mapping) - CANONICAL_FIELDS)
    if unknown_targets:
        raise HTTPException(status_code=422, detail="El mapeo contiene campos destino no permitidos.")
    available = set(columns)
    missing_sources = sorted({source for source in mapping.values() if source not in available})
    if missing_sources:
        raise HTTPException(
            status_code=422,
            detail="El mapeo referencia columnas que no existen en el archivo.",
        )
    missing_required = sorted(REQUIRED_FIELDS - set(mapping))
    entity_ready = "entidad" in mapping or "clave_entidad_inegi" in mapping
    municipality_ready = any(
        key in mapping
        for key in ("municipio", "clave_municipio_inegi", "id_municipio_fuente")
    )
    if missing_required or not entity_ready or not municipality_ready:
        raise HTTPException(
            status_code=422,
            detail=(
                "El mapeo debe identificar nombre, tipo, entidad y municipio sin ambiguedad."
            ),
        )


def validate_options(options: dict[str, Any]) -> None:
    scope = options.get("alcance_id_nucleo_fuente", "territorial")
    if scope not in {"territorial", "global"}:
        raise HTTPException(
            status_code=422,
            detail="El alcance del ID externo debe ser territorial o global.",
        )


def _upload_root() -> Path:
    root = Path(os.getenv("UPLOAD_ROOT", "uploads")) / "importaciones_geoespaciales"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def _safe_original_name(filename: str | None) -> str:
    if not filename or "\x00" in filename:
        raise HTTPException(status_code=400, detail="El archivo debe tener un nombre valido.")
    normalized = filename.replace("\\", "/")
    if PurePath(normalized).name != normalized or normalized in {".", ".."}:
        raise HTTPException(status_code=400, detail="El nombre del archivo no es seguro.")
    basename = PurePath(normalized).name.strip()
    if not basename or len(basename) > 255:
        raise HTTPException(status_code=400, detail="El nombre del archivo no es valido.")
    return basename


def _declared_extension(filename: str) -> str:
    suffix = Path(filename).suffix.casefold()
    if suffix == ".kml":
        return "kml"
    if suffix in {".geojson", ".json"}:
        return "geojson"
    raise HTTPException(status_code=415, detail="Solo se permiten archivos KML o GeoJSON.")


async def stage_upload(
    db: Session,
    upload: UploadFile,
    fuente: str,
    user_id: int,
) -> models.ImportacionArchivo:
    original_name = _safe_original_name(upload.filename)
    declared_format = _declared_extension(original_name)
    source = fuente.strip()
    if not source or len(source) > 200:
        raise HTTPException(status_code=422, detail="La fuente es obligatoria y debe ser identificable.")
    max_bytes = int(os.getenv("IMPORT_MAX_FILE_SIZE_MB", "100")) * 1024 * 1024
    stored_name = f"{uuid.uuid4().hex}{Path(original_name).suffix.casefold()}"
    destination = _upload_root() / stored_name
    digest = hashlib.sha256()
    size = 0
    head = bytearray()
    try:
        with destination.open("xb") as target:
            os.chmod(destination, 0o600)
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"El archivo excede el limite configurado de {max_bytes // 1024 // 1024} MiB.",
                    )
                if len(head) < 4096:
                    head.extend(chunk[: 4096 - len(head)])
                digest.update(chunk)
                target.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="El archivo esta vacio.")
        head_bytes = bytes(head)
        if head_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
            head_text = head_bytes.decode("utf-16", errors="ignore").lstrip()
        else:
            head_text = head_bytes.decode("utf-8-sig", errors="ignore").lstrip()
        first_non_space = head_text[:1]
        apparent = "kml" if first_non_space == "<" else "geojson" if first_non_space in {"{", "["} else ""
        if apparent != declared_format:
            raise HTTPException(
                status_code=415,
                detail="La extension no coincide con el contenido del archivo.",
            )
        dataset = inspect_dataset(destination)
        if dataset.format != declared_format:
            raise HTTPException(
                status_code=415,
                detail="El formato detectado por GDAL/OGR no coincide con la extension.",
            )
        sha256 = digest.hexdigest()
        existing = (
            db.query(models.ImportacionArchivo)
            .filter(
                models.ImportacionArchivo.sha256 == sha256,
                models.ImportacionArchivo.tipo_objetivo == "nucleo_agrario",
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"El mismo archivo ya fue registrado como importacion {existing.id_importacion}.",
            )
        mapping = suggest_mapping(dataset.columns)
        record = models.ImportacionArchivo(
            nombre_original=original_name,
            nombre_almacenado=stored_name,
            formato_detectado=dataset.format,
            tamano_bytes=size,
            sha256=sha256,
            fuente=source,
            crs_original=dataset.crs_description,
            columnas_detectadas=dataset.columns,
            mapeo=mapping,
            opciones_mapeo={},
            total_features=dataset.total_features,
            id_usuario_carga=user_id,
            tolerancia_area_relativa=_configured_area_tolerance(),
        )
        set_audit_context(db, user_id)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except IngestionError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=exc.public_detail) from exc
    except Exception:
        logger.exception("Fallo no controlado al registrar el archivo %s", original_name)
        db.rollback()
        raise
    finally:
        if destination.exists() and not db.query(models.ImportacionArchivo).filter_by(nombre_almacenado=stored_name).first():
            destination.unlink(missing_ok=True)


def _configured_area_tolerance() -> Decimal | None:
    raw = os.getenv("IMPORT_MAKE_VALID_MAX_AREA_DELTA", "").strip()
    if not raw:
        return None
    try:
        value = Decimal(raw)
    except Exception as exc:
        raise RuntimeError("IMPORT_MAKE_VALID_MAX_AREA_DELTA debe ser un decimal entre 0 y 1") from exc
    if value < 0 or value > 1:
        raise RuntimeError("IMPORT_MAKE_VALID_MAX_AREA_DELTA debe estar entre 0 y 1")
    return value


def stored_path(record: models.ImportacionArchivo) -> Path:
    path = _upload_root() / record.nombre_almacenado
    if path.parent != _upload_root() or not path.is_file():
        raise IngestionError("ARCHIVO_TEMPORAL_NO_DISPONIBLE", "El archivo temporal ya no esta disponible.")
    return path


def get_import_or_404(db: Session, import_id: int, user: models.Usuario) -> models.ImportacionArchivo:
    record = db.get(models.ImportacionArchivo, import_id)
    if not record or (user.rol != "admin" and record.id_usuario_carga != user.id_usuario):
        raise HTTPException(status_code=404, detail="Importacion no encontrada.")
    return record


def update_mapping(
    db: Session,
    record: models.ImportacionArchivo,
    payload: MapeoImportacionRequest,
    user_id: int,
) -> models.ImportacionArchivo:
    if record.estado in RUNNING_STATES or record.estado in {"confirmando", "importando", "completado"}:
        raise HTTPException(status_code=409, detail="El mapeo ya no puede modificarse en este estado.")
    validate_mapping(payload.mapeo, record.columnas_detectadas)
    validate_options(payload.opciones)
    profile_id = payload.id_perfil
    if profile_id is not None:
        profile = db.get(models.PerfilMapeoImportacion, profile_id)
        if not profile or not profile.activo:
            raise HTTPException(status_code=404, detail="Perfil de mapeo no encontrado.")
    if payload.guardar_perfil:
        profile = models.PerfilMapeoImportacion(
            nombre=payload.guardar_perfil.nombre,
            fuente=payload.guardar_perfil.fuente,
            mapeo=payload.mapeo,
            opciones=payload.opciones,
            id_usuario_creacion=user_id,
        )
        db.add(profile)
        try:
            set_audit_context(db, user_id)
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="Ya existe un perfil con ese nombre.") from exc
        profile_id = profile.id_perfil
    record.mapeo = payload.mapeo
    record.opciones_mapeo = payload.opciones
    record.id_perfil = profile_id
    record.version_control += 1
    set_audit_context(db, user_id)
    db.commit()
    db.refresh(record)
    return record


def create_profile(db: Session, payload: Any, user_id: int) -> models.PerfilMapeoImportacion:
    profile = models.PerfilMapeoImportacion(
        nombre=payload.nombre,
        fuente=payload.fuente,
        mapeo=payload.mapeo,
        opciones=payload.opciones,
        id_usuario_creacion=user_id,
    )
    set_audit_context(db, user_id)
    db.add(profile)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un perfil con ese nombre.") from exc
    db.refresh(profile)
    return profile


def create_alias(db: Session, payload: Any, user_id: int) -> models.CatalogoAliasTerritorial:
    entity = db.get(models.EntidadFederativa, payload.id_entidad)
    municipality = db.get(models.Municipio, payload.id_municipio_destino)
    if not entity or not entity.activo or not municipality or not municipality.activo:
        raise HTTPException(status_code=422, detail="Entidad o municipio destino no valido.")
    if municipality.id_entidad != entity.id_entidad:
        raise HTTPException(status_code=422, detail="El municipio destino no pertenece a la entidad indicada.")
    if not payload.alias_nombre and not payload.alias_clave:
        raise HTTPException(status_code=422, detail="El alias debe tener nombre o clave de origen.")
    alias = models.CatalogoAliasTerritorial(
        id_entidad=entity.id_entidad,
        alias_nombre=payload.alias_nombre.strip() if payload.alias_nombre else None,
        alias_normalizado=normalize_text(payload.alias_nombre or payload.alias_clave),
        alias_clave=payload.alias_clave.strip() if payload.alias_clave else None,
        id_municipio_destino=municipality.id_municipio,
        fuente=payload.fuente.strip(),
        fecha_vigencia_inicio=payload.fecha_vigencia_inicio,
        fecha_vigencia_fin=payload.fecha_vigencia_fin,
        id_usuario_aprobador=user_id,
    )
    set_audit_context(db, user_id)
    db.add(alias)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El alias entra en conflicto con otro alias activo.") from exc
    db.refresh(alias)
    return alias


def _message(code: str, field: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"codigo": code, "campo": field, "mensaje": detail, **extra}


def _mapped(properties: dict[str, Any], mapping: dict[str, str], target: str) -> Any:
    source = mapping.get(target)
    return properties.get(source) if source else None


def _clean_source_id(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned[:200] if cleaned else None


def _normalize_type(value: Any) -> str | None:
    return TYPE_EQUIVALENTS.get(normalize_text(value))


def _bool_value(value: Any) -> bool:
    return normalize_text(value) in {"1", "si", "s", "true", "verdadero"}


def _catalogs(db: Session) -> dict[str, Any]:
    entities = db.query(models.EntidadFederativa).filter(models.EntidadFederativa.activo.is_(True)).all()
    municipalities = db.query(models.Municipio).filter(models.Municipio.activo.is_(True)).all()
    aliases = db.query(models.CatalogoAliasTerritorial).filter(models.CatalogoAliasTerritorial.activo.is_(True)).all()
    return {
        "entities_by_code": {entity.clave_inegi: entity for entity in entities},
        "entities_by_name": _multi_index(entities, lambda item: normalize_text(item.nombre)),
        "municipalities_by_code": {item.clave_inegi: item for item in municipalities},
        "municipalities_by_id": {item.id_municipio: item for item in municipalities},
        "municipalities_by_entity_name": _multi_index(
            municipalities, lambda item: (item.id_entidad, normalize_text(item.nombre))
        ),
        "aliases": _multi_index(
            aliases, lambda item: (item.id_entidad, item.alias_normalizado)
        ),
    }


def _multi_index(items: Iterable[Any], key_function: Any) -> dict[Any, list[Any]]:
    result: dict[Any, list[Any]] = defaultdict(list)
    for item in items:
        result[key_function(item)].append(item)
    return result


def _resolve_territory(
    normalized: dict[str, Any],
    options: dict[str, Any],
    catalogs: dict[str, Any],
) -> tuple[models.EntidadFederativa | None, models.Municipio | None, list[dict], list[dict]]:
    errors: list[dict] = []
    warnings: list[dict] = []
    entity = None
    entity_code = _clean_source_id(normalized.get("clave_entidad_inegi"))
    entity_name = normalize_text(normalized.get("entidad"))
    if entity_code:
        entity = catalogs["entities_by_code"].get(entity_code.zfill(2))
    elif entity_name:
        matches = catalogs["entities_by_name"].get(entity_name, [])
        if len(matches) == 1:
            entity = matches[0]
        elif len(matches) > 1:
            errors.append(_message("ENTIDAD_AMBIGUA", "entidad", f'La entidad "{normalized.get("entidad")}" es ambigua.'))
    if not entity:
        if not errors:
            errors.append(_message("ENTIDAD_NO_ENCONTRADA", "entidad", f'Entidad "{normalized.get("entidad") or entity_code or "(vacia)"}" no encontrada.'))
        return None, None, errors, warnings

    municipality = None
    full_code = _clean_source_id(normalized.get("clave_municipio_inegi"))
    external_code = _clean_source_id(normalized.get("id_municipio_fuente"))
    code_semantics = options.get("id_municipio_fuente_semantica")
    candidate_code = full_code
    if not candidate_code and external_code and code_semantics == "clave_inegi_completa":
        candidate_code = external_code
    elif not candidate_code and external_code and code_semantics == "clave_municipal_inegi":
        candidate_code = f"{entity.clave_inegi}{external_code.zfill(3)}"
    if candidate_code:
        municipality = catalogs["municipalities_by_code"].get(candidate_code.zfill(5))
        if municipality and municipality.id_entidad != entity.id_entidad:
            municipality = None
            errors.append(_message("MUNICIPIO_FUERA_DE_ENTIDAD", "municipio", "La clave municipal pertenece a otra entidad federativa."))

    municipality_name = normalize_text(normalized.get("municipio"))
    if municipality is None and not errors and municipality_name:
        matches = catalogs["municipalities_by_entity_name"].get((entity.id_entidad, municipality_name), [])
        if len(matches) == 1:
            municipality = matches[0]
        elif len(matches) > 1:
            errors.append(_message("MUNICIPIO_AMBIGUO", "municipio", f'El municipio "{normalized.get("municipio")}" tiene mas de una coincidencia dentro de {entity.nombre}.'))
        else:
            alias_matches = catalogs["aliases"].get((entity.id_entidad, municipality_name), [])
            if len(alias_matches) == 1:
                alias = alias_matches[0]
                municipality = catalogs["municipalities_by_id"].get(alias.id_municipio_destino)
                warnings.append(_message("ALIAS_TERRITORIAL_APLICADO", "municipio", f'Se aplico el alias aprobado "{alias.alias_nombre or alias.alias_clave}".', id_alias=alias.id_alias))
            elif len(alias_matches) > 1:
                errors.append(_message("ALIAS_TERRITORIAL_AMBIGUO", "municipio", "El alias territorial tiene mas de un destino activo."))
    if municipality is None and not errors:
        provided = normalized.get("municipio") or candidate_code or external_code or "(vacio)"
        errors.append(_message("MUNICIPIO_NO_ENCONTRADO", "municipio", f'Municipio "{provided}" no encontrado dentro de {entity.nombre}.'))
    return entity, municipality, errors, warnings


GEOMETRY_SQL = text(
    """
    WITH parsed AS (
        SELECT ST_SetSRID(ST_Force2D(ST_GeomFromGeoJSON(:geometry)), 4326) AS geom
    ), polygonal AS (
        SELECT ST_CollectionExtract(geom, 3) AS geom,
               ST_IsValid(geom) AS was_valid,
               GeometryType(geom) AS original_type
          FROM parsed
    ), repaired AS (
        SELECT geom AS original_geom, was_valid, original_type,
               ST_CollectionExtract(ST_MakeValid(geom), 3) AS repaired_geom
          FROM polygonal
    ), measured AS (
        SELECT original_geom, was_valid, original_type,
               ST_Multi(repaired_geom) AS normalized_geom,
               ST_Area(ST_Transform(original_geom, 6933)) AS original_area,
               ST_Area(ST_Transform(repaired_geom, 6933)) AS repaired_area
          FROM repaired
    )
    SELECT was_valid, original_type,
           ST_IsEmpty(normalized_geom) AS is_empty,
           ST_IsValid(normalized_geom) AS is_valid,
           normalized_geom,
           original_area,
           repaired_area,
           CASE WHEN original_area > 0
                THEN abs(repaired_area - original_area) / original_area
                ELSE NULL END AS area_delta
      FROM measured
    """
)


def _has_z_coordinates(geometry: Any) -> bool:
    if not isinstance(geometry, dict):
        return False
    stack = [geometry.get("coordinates")]
    while stack:
        current = stack.pop()
        if isinstance(current, list) and current:
            if all(isinstance(item, (int, float)) for item in current):
                return len(current) > 2
            stack.extend(current)
    return False


def _normalize_geometry(
    db: Session,
    geometry: Any,
    layer: Any,
    tolerance: Decimal | None,
) -> tuple[Any, Decimal | None, Decimal | None, Decimal | None, list[dict], list[dict], list[dict]]:
    errors: list[dict] = []
    warnings: list[dict] = []
    transformations: list[dict] = []
    if not isinstance(geometry, dict):
        errors.append(_message("GEOMETRIA_AUSENTE", "geometria", "El feature no contiene una geometria."))
        return None, None, None, None, errors, warnings, transformations
    geometry_type = geometry.get("type")
    if geometry_type not in {"Polygon", "MultiPolygon", "GeometryCollection"}:
        errors.append(_message("TIPO_GEOMETRIA_NO_PERMITIDO", "geometria", f'La geometria "{geometry_type}" no contiene poligonos importables.'))
        return None, None, None, None, errors, warnings, transformations
    if not layer.is_wgs84:
        transformations.append(_message("CRS_TRANSFORMADO", "geometria", f"Geometria transformada de {layer.crs} a EPSG:4326."))
    if _has_z_coordinates(geometry):
        transformations.append(_message("FORCE_2D", "geometria", "Se elimino la dimension Z mediante Force2D."))
    if geometry_type == "GeometryCollection":
        transformations.append(_message("EXTRACCION_POLIGONOS", "geometria", "Se extrajeron los componentes poligonales de GeometryCollection."))
    if geometry_type == "Polygon":
        transformations.append(_message("POLYGON_A_MULTIPOLYGON", "geometria", "Polygon normalizado a MultiPolygon."))
    try:
        with db.begin_nested():
            result = db.execute(GEOMETRY_SQL, {"geometry": json.dumps(geometry)}).mappings().one()
    except DBAPIError:
        errors.append(_message("GEOMETRIA_NO_RECUPERABLE", "geometria", "PostGIS no pudo interpretar o reparar la geometria."))
        return None, None, None, None, errors, warnings, transformations
    if result["is_empty"] or not result["is_valid"]:
        errors.append(_message("GEOMETRIA_NO_RECUPERABLE", "geometria", "La geometria no produjo un MultiPolygon valido y no vacio."))
    delta = Decimal(result["area_delta"]) if result["area_delta"] is not None else None
    if not result["was_valid"]:
        transformations.append(_message("ST_MAKEVALID", "geometria", "La geometria invalida fue procesada con ST_MakeValid."))
        if tolerance is None:
            errors.append(_message("TOLERANCIA_AREA_NO_CONFIGURADA", "geometria", "La geometria fue reparada, pero no existe una tolerancia de area aprobada; el feature queda bloqueado."))
        elif delta is None or delta > tolerance:
            percentage = f"{(delta or Decimal(0)) * 100:.2f}"
            errors.append(_message("REPARACION_SUPERA_TOLERANCIA", "geometria", f"La reparacion cambio el area {percentage} %, superando la tolerancia configurada.", diferencia_area_relativa=str(delta) if delta is not None else None))
        else:
            warnings.append(_message("GEOMETRIA_REPARADA", "geometria", f"La geometria fue reparada; la diferencia relativa de area fue {delta * 100:.2f} %."))
    return (
        result["normalized_geom"],
        Decimal(result["original_area"]) if result["original_area"] is not None else None,
        Decimal(result["repaired_area"]) if result["repaired_area"] is not None else None,
        delta,
        errors,
        warnings,
        transformations,
    )


def _process_one(
    db: Session,
    record: models.ImportacionArchivo,
    dataset: DatasetInfo,
    layer_name: str,
    raw_feature: dict[str, Any],
    index: int,
    catalogs: dict[str, Any],
) -> models.ImportacionFeature:
    properties = raw_feature.get("properties") or {}
    if not isinstance(properties, dict):
        properties = {}
    mapping = record.mapeo or {}
    normalized = {target: _mapped(properties, mapping, target) for target in mapping}
    normalized["nombre_nucleo"] = str(normalized.get("nombre_nucleo") or "").strip()
    normalized["tipo_nucleo"] = _normalize_type(normalized.get("tipo_nucleo"))
    normalized["comunidad_indigena"] = _bool_value(normalized.get("comunidad_indigena"))
    normalized["residencia"] = str(normalized.get("residencia") or "").strip() or None
    id_entity_source = _clean_source_id(normalized.get("id_entidad_fuente"))
    id_municipality_source = _clean_source_id(normalized.get("id_municipio_fuente"))
    id_nucleus_source = _clean_source_id(normalized.get("id_nucleo_fuente"))
    external_id = id_nucleus_source or _clean_source_id(raw_feature.get("id"))
    errors: list[dict] = []
    warnings: list[dict] = []
    if not normalized["nombre_nucleo"]:
        errors.append(_message("NOMBRE_NUCLEO_AUSENTE", "nombre_nucleo", "El nombre del nucleo agrario es obligatorio."))
    if not normalized["tipo_nucleo"]:
        raw_type = _mapped(properties, mapping, "tipo_nucleo")
        errors.append(_message("TIPO_NUCLEO_DESCONOCIDO", "tipo_nucleo", f'El tipo de nucleo "{raw_type or "(vacio)"}" no tiene una regla de equivalencia aprobada.'))
    entity, municipality, territory_errors, territory_warnings = _resolve_territory(
        normalized, record.opciones_mapeo or {}, catalogs
    )
    errors.extend(territory_errors)
    warnings.extend(territory_warnings)
    layer = next(item for item in dataset.layers if item.name == layer_name)
    geometry, original_area, repaired_area, delta, geometry_errors, geometry_warnings, transformations = _normalize_geometry(
        db, raw_feature.get("geometry"), layer, record.tolerancia_area_relativa
    )
    errors.extend(geometry_errors)
    warnings.extend(geometry_warnings)
    status = "error" if errors else "advertencia" if warnings else "valido"
    staged = (
        db.query(models.ImportacionFeature)
        .filter_by(id_importacion=record.id_importacion, indice_feature=index)
        .first()
    )
    if staged is None:
        staged = models.ImportacionFeature(id_importacion=record.id_importacion, indice_feature=index)
        db.add(staged)
    staged.capa_origen = layer_name
    staged.id_externo = external_id
    staged.id_entidad_fuente = id_entity_source
    staged.id_municipio_fuente = id_municipality_source
    staged.id_nucleo_fuente = id_nucleus_source
    staged.atributos_originales = properties
    staged.atributos_normalizados = normalized
    staged.geometria_normalizada = geometry
    staged.id_entidad_resuelta = entity.id_entidad if entity else None
    staged.id_municipio_resuelto = municipality.id_municipio if municipality else None
    staged.estado = status
    staged.errores = errors
    staged.advertencias = warnings
    staged.transformaciones = transformations
    staged.area_original_m2 = original_area
    staged.area_normalizada_m2 = repaired_area
    staged.diferencia_area_relativa = delta
    staged.advertencias_aceptadas = False
    staged.id_usuario_revision = None
    staged.fecha_revision = None
    staged.fecha_procesamiento = utcnow()
    return staged


def _external_identity(record: models.ImportacionArchivo, feature: models.ImportacionFeature) -> tuple | None:
    if not feature.id_nucleo_fuente:
        return None
    scope = (record.opciones_mapeo or {}).get("alcance_id_nucleo_fuente", "territorial")
    if scope == "global":
        return ("global", normalize_text(record.fuente), feature.id_nucleo_fuente)
    if feature.id_municipio_resuelto:
        return (
            "territorial",
            normalize_text(record.fuente),
            feature.id_municipio_resuelto,
            feature.id_nucleo_fuente,
        )
    return None


def _append_problem(feature: models.ImportacionFeature, problem: dict, warning: bool = False) -> None:
    if warning:
        feature.advertencias = [*(feature.advertencias or []), problem]
        if feature.estado == "valido":
            feature.estado = "advertencia"
    else:
        feature.errores = [*(feature.errores or []), problem]
        feature.estado = "error"


def _detect_duplicates(db: Session, record: models.ImportacionArchivo) -> None:
    features = (
        db.query(models.ImportacionFeature)
        .filter(models.ImportacionFeature.id_importacion == record.id_importacion)
        .order_by(models.ImportacionFeature.indice_feature)
        .all()
    )
    identities: dict[tuple, list[models.ImportacionFeature]] = defaultdict(list)
    names: dict[tuple, list[models.ImportacionFeature]] = defaultdict(list)
    for feature in features:
        identity = _external_identity(record, feature)
        if identity:
            identities[identity].append(feature)
        name = normalize_text((feature.atributos_normalizados or {}).get("nombre_nucleo"))
        if name and feature.id_municipio_resuelto:
            names[(feature.id_municipio_resuelto, name)].append(feature)

    join_parts = bool((record.opciones_mapeo or {}).get("unir_partes_mismo_id"))
    for identity, group in identities.items():
        existing_query = db.query(models.NucleoAgrario).filter(
            models.NucleoAgrario.activo.is_(True),
            models.NucleoAgrario.alcance_identidad_fuente == identity[0],
            func.lower(models.NucleoAgrario.fuente_datos) == record.fuente.casefold(),
        )
        if identity[0] == "global":
            existing_query = existing_query.filter(
                models.NucleoAgrario.id_nucleo_fuente == identity[2]
            )
        else:
            existing_query = existing_query.filter(
                models.NucleoAgrario.id_municipio == identity[2],
                models.NucleoAgrario.id_nucleo_fuente == identity[3],
            )
        existing = existing_query.first()
        if existing:
            for feature in group:
                _append_problem(feature, _message("ID_EXTERNO_YA_IMPORTADO", "id_nucleo_fuente", f"La identidad externa ya corresponde al nucleo operativo {existing.id_nucleo}; no se sobrescribira."))
        if len(group) <= 1:
            continue
        signatures = {
            (
                normalize_text((item.atributos_normalizados or {}).get("nombre_nucleo")),
                (item.atributos_normalizados or {}).get("tipo_nucleo"),
                item.id_municipio_resuelto,
            )
            for item in group
        }
        if len(signatures) > 1:
            for feature in group:
                _append_problem(feature, _message("ID_EXTERNO_CONTRADICTORIO", "id_nucleo_fuente", "El mismo ID externo contiene nombre, tipo o territorio contradictorio."))
        elif not join_parts:
            for feature in group:
                _append_problem(feature, _message("ID_EXTERNO_DUPLICADO", "id_nucleo_fuente", "El ID externo aparece mas de una vez. Active explicitamente la union de partes si la fuente documenta esta estructura."))
        else:
            for feature in group:
                _append_problem(feature, _message("PARTES_POR_UNIR", "geometria", "Las partes con la misma identidad externa se uniran solamente durante la confirmacion."), warning=True)

    for key, group in names.items():
        if len(group) > 1 and not all(_external_identity(record, item) for item in group):
            for feature in group:
                _append_problem(feature, _message("IDENTIDAD_INSUFICIENTE_DUPLICADA", "nombre_nucleo", "Hay mas de un feature con el mismo nombre y municipio sin una identidad externa estable."))
        existing = (
            db.query(models.NucleoAgrario)
            .filter(
                models.NucleoAgrario.activo.is_(True),
                models.NucleoAgrario.id_municipio == key[0],
                func.lower(func.btrim(models.NucleoAgrario.nombre_nucleo)) == str((group[0].atributos_normalizados or {}).get("nombre_nucleo", "")).strip().lower(),
            )
            .first()
        )
        if existing:
            for feature in group:
                _append_problem(feature, _message("NUCLEO_OPERATIVO_EXISTENTE", "nombre_nucleo", f"Ya existe el nucleo operativo {existing.id_nucleo} con el mismo nombre y municipio; se requiere conciliacion, no sobrescritura."))


def _recount(db: Session, record: models.ImportacionArchivo) -> None:
    counts = dict(
        db.query(models.ImportacionFeature.estado, func.count(models.ImportacionFeature.id_importacion_feature))
        .filter(models.ImportacionFeature.id_importacion == record.id_importacion)
        .group_by(models.ImportacionFeature.estado)
        .all()
    )
    record.validos = counts.get("valido", 0)
    record.advertencias = counts.get("advertencia", 0)
    record.errores = counts.get("error", 0)
    record.importados = counts.get("importado", 0)
    record.descartados = counts.get("descartado", 0)


def process_import(import_id: int, user_id: int) -> None:
    db = SessionLocal()
    record = None
    try:
        record = db.get(models.ImportacionArchivo, import_id)
        if not record:
            return
        validate_mapping(record.mapeo or {}, record.columnas_detectadas or [])
        validate_options(record.opciones_mapeo or {})
        set_audit_context(db, user_id)
        claimed = db.execute(
            text(
                """
                UPDATE importacion_archivo
                   SET estado = 'analizando', fecha_procesamiento_inicio = NOW(),
                       fecha_procesamiento_fin = NULL, error_codigo = NULL,
                       error_detalle = NULL, features_procesados = 0,
                       version_control = version_control + 1
                 WHERE id_importacion = :id
                   AND estado IN ('subido', 'listo_revision', 'fallido')
                RETURNING id_importacion
                """
            ),
            {"id": import_id},
        ).scalar_one_or_none()
        if claimed is None:
            return
        db.commit()
        record = db.get(models.ImportacionArchivo, import_id)
        dataset = inspect_dataset(stored_path(record))
        if dataset.format != record.formato_detectado or dataset.total_features != record.total_features:
            raise IngestionError("METADATOS_CAMBIARON", "El archivo temporal no coincide con los metadatos registrados.")
        catalogs = _catalogs(db)
        record.estado = "normalizando"
        set_audit_context(db, user_id)
        db.commit()
        batch_size = max(1, int(os.getenv("IMPORT_STAGING_BATCH_SIZE", "250")))
        processed = 0
        for index, (layer_name, raw_feature) in enumerate(iter_features(stored_path(record), dataset)):
            record = db.get(models.ImportacionArchivo, import_id)
            _process_one(db, record, dataset, layer_name, raw_feature, index, catalogs)
            processed += 1
            if processed % batch_size == 0:
                record.features_procesados = processed
                record.estado = "resolviendo"
                set_audit_context(db, user_id)
                db.commit()
        if processed != record.total_features:
            raise IngestionError(
                "PERDIDA_FEATURES",
                f"OGR detecto {record.total_features} features, pero el pipeline produjo {processed}; la importacion queda bloqueada.",
            )
        record = db.get(models.ImportacionArchivo, import_id)
        record.features_procesados = processed
        set_audit_context(db, user_id)
        # SessionLocal usa autoflush=False: los features del ultimo lote deben
        # persistirse antes de consultar duplicados dentro del mismo archivo.
        db.flush()
        _detect_duplicates(db, record)
        db.flush()
        _recount(db, record)
        record.estado = "listo_revision"
        record.fecha_procesamiento_fin = utcnow()
        set_audit_context(db, user_id)
        db.commit()
    except HTTPException as exc:
        db.rollback()
        _mark_failed(import_id, user_id, "MAPEO_INVALIDO", str(exc.detail))
    except IngestionError as exc:
        db.rollback()
        _mark_failed(import_id, user_id, exc.code, exc.public_detail)
    except Exception:
        logger.exception("Fallo no controlado al prevalidar importacion %s", import_id)
        db.rollback()
        _mark_failed(import_id, user_id, "PROCESAMIENTO_FALLIDO", "La prevalidacion no pudo completarse. Revise el registro del servidor.")
    finally:
        db.close()


def _mark_failed(import_id: int, user_id: int, code: str, detail: str) -> None:
    db = SessionLocal()
    try:
        set_audit_context(db, user_id)
        record = db.get(models.ImportacionArchivo, import_id)
        if record:
            record.estado = "fallido"
            record.error_codigo = code
            record.error_detalle = detail[:2000]
            record.fecha_procesamiento_fin = utcnow()
            set_audit_context(db, user_id)
            db.commit()
    finally:
        db.close()


def revise_feature(
    db: Session,
    record: models.ImportacionArchivo,
    feature_id: int,
    payload: FeatureRevisionRequest,
    user_id: int,
) -> models.ImportacionFeature:
    if record.estado != "listo_revision":
        raise HTTPException(status_code=409, detail="La importacion no esta disponible para revision.")
    feature = (
        db.query(models.ImportacionFeature)
        .filter_by(id_importacion=record.id_importacion, id_importacion_feature=feature_id)
        .first()
    )
    if not feature:
        raise HTTPException(status_code=404, detail="Feature no encontrado.")
    if payload.descartar:
        feature.estado = "descartado"
        feature.id_usuario_revision = user_id
        feature.fecha_revision = utcnow()
    else:
        attrs = dict(feature.atributos_normalizados or {})
        if payload.nombre_nucleo is not None:
            name = payload.nombre_nucleo.strip()
            if not name:
                raise HTTPException(status_code=422, detail="El nombre del nucleo es obligatorio.")
            attrs["nombre_nucleo"] = name
        if payload.tipo_nucleo is not None:
            normalized_type = _normalize_type(payload.tipo_nucleo)
            if not normalized_type:
                raise HTTPException(status_code=422, detail="El tipo de nucleo no tiene una equivalencia aprobada.")
            attrs["tipo_nucleo"] = normalized_type
        if payload.id_entidad is not None or payload.id_municipio is not None:
            if payload.id_entidad is None or payload.id_municipio is None:
                raise HTTPException(status_code=422, detail="Entidad y municipio deben corregirse juntos.")
            entity = db.get(models.EntidadFederativa, payload.id_entidad)
            municipality = db.get(models.Municipio, payload.id_municipio)
            if not entity or not entity.activo or not municipality or not municipality.activo or municipality.id_entidad != entity.id_entidad:
                raise HTTPException(status_code=422, detail="El municipio no pertenece a la entidad seleccionada.")
            feature.id_entidad_resuelta = entity.id_entidad
            feature.id_municipio_resuelto = municipality.id_municipio
            attrs["entidad"] = entity.nombre
            attrs["municipio"] = municipality.nombre
        feature.atributos_normalizados = attrs
        unresolved_codes = {
            "NOMBRE_NUCLEO_AUSENTE", "TIPO_NUCLEO_DESCONOCIDO", "ENTIDAD_AMBIGUA",
            "ENTIDAD_NO_ENCONTRADA", "MUNICIPIO_FUERA_DE_ENTIDAD", "MUNICIPIO_AMBIGUO",
            "MUNICIPIO_NO_ENCONTRADO", "ALIAS_TERRITORIAL_AMBIGUO",
        }
        feature.errores = [item for item in (feature.errores or []) if item.get("codigo") not in unresolved_codes]
        if not attrs.get("nombre_nucleo"):
            feature.errores.append(_message("NOMBRE_NUCLEO_AUSENTE", "nombre_nucleo", "El nombre del nucleo agrario es obligatorio."))
        if attrs.get("tipo_nucleo") not in {"ejido", "comunidad"}:
            feature.errores.append(_message("TIPO_NUCLEO_DESCONOCIDO", "tipo_nucleo", "El tipo de nucleo no es valido."))
        if not feature.id_municipio_resuelto:
            feature.errores.append(_message("MUNICIPIO_NO_ENCONTRADO", "municipio", "El municipio no ha sido resuelto."))
        feature.advertencias_aceptadas = bool(payload.aceptar_advertencias)
        feature.estado = "error" if feature.errores else "advertencia" if feature.advertencias else "valido"
        feature.id_usuario_revision = user_id
        feature.fecha_revision = utcnow()
    _recount(db, record)
    set_audit_context(db, user_id)
    db.commit()
    db.refresh(feature)
    return feature


def _confirmation_groups(record: models.ImportacionArchivo, features: list[models.ImportacionFeature]) -> list[list[models.ImportacionFeature]]:
    grouped: dict[tuple, list[models.ImportacionFeature]] = defaultdict(list)
    for feature in features:
        identity = _external_identity(record, feature)
        grouped[identity or ("feature", feature.id_importacion_feature)].append(feature)
    return list(grouped.values())


def confirm_import(import_id: int, user_id: int, accept_warnings: bool) -> None:
    db = SessionLocal()
    try:
        set_audit_context(db, user_id)
        claimed = db.execute(
            text(
                """
                UPDATE importacion_archivo
                   SET estado = 'confirmando', fecha_confirmacion = NOW(),
                       id_usuario_confirmacion = :user_id,
                       error_codigo = NULL, error_detalle = NULL,
                       version_control = version_control + 1
                 WHERE id_importacion = :id
                   AND (
                       estado = 'listo_revision'
                       OR (estado = 'fallido' AND error_codigo = 'CONFIRMACION_FALLIDA')
                   )
                RETURNING id_importacion
                """
            ),
            {"id": import_id, "user_id": user_id},
        ).scalar_one_or_none()
        if claimed is None:
            return
        db.commit()
        record = db.get(models.ImportacionArchivo, import_id)
        if accept_warnings:
            db.query(models.ImportacionFeature).filter(
                models.ImportacionFeature.id_importacion == import_id,
                models.ImportacionFeature.estado == "advertencia",
            ).update(
                {
                    models.ImportacionFeature.advertencias_aceptadas: True,
                    models.ImportacionFeature.id_usuario_revision: user_id,
                    models.ImportacionFeature.fecha_revision: utcnow(),
                },
                synchronize_session=False,
            )
        record.estado = "importando"
        set_audit_context(db, user_id)
        db.commit()
        features = (
            db.query(models.ImportacionFeature)
            .filter(
                models.ImportacionFeature.id_importacion == import_id,
                or_(
                    models.ImportacionFeature.estado == "valido",
                    (
                        (models.ImportacionFeature.estado == "advertencia")
                        & models.ImportacionFeature.advertencias_aceptadas.is_(True)
                    ),
                ),
            )
            .order_by(models.ImportacionFeature.indice_feature)
            .all()
        )
        groups = _confirmation_groups(record, features)
        batch_size = max(1, int(os.getenv("IMPORT_CONFIRM_BATCH_SIZE", "100")))
        for offset in range(0, len(groups), batch_size):
            for group in groups[offset : offset + batch_size]:
                try:
                    with db.begin_nested():
                        _import_group(db, record, group, user_id)
                except (DBAPIError, IntegrityError):
                    for feature in group:
                        _append_problem(feature, _message("FALLO_IMPORTACION_OPERATIVA", "importacion", "El registro entro en conflicto con la integridad operativa y no fue importado."))
            set_audit_context(db, user_id)
            db.commit()
        record = db.get(models.ImportacionArchivo, import_id)
        _recount(db, record)
        record.estado = "completado"
        record.fecha_completado = utcnow()
        set_audit_context(db, user_id)
        db.commit()
    except Exception:
        logger.exception("Fallo no controlado al confirmar importacion %s", import_id)
        db.rollback()
        _mark_failed(import_id, user_id, "CONFIRMACION_FALLIDA", "La confirmacion no pudo completarse. Los lotes confirmados conservan su trazabilidad y no se duplicaran al reintentar.")
    finally:
        db.close()


def _import_group(
    db: Session,
    record: models.ImportacionArchivo,
    group: list[models.ImportacionFeature],
    user_id: int,
) -> None:
    first = group[0]
    attrs = first.atributos_normalizados or {}
    geometry = db.execute(
        text(
            """
            SELECT ST_Multi(ST_CollectionExtract(ST_UnaryUnion(ST_Collect(geometria_normalizada)), 3))
              FROM importacion_feature
             WHERE id_importacion_feature = ANY(:ids)
            """
        ),
        {"ids": [item.id_importacion_feature for item in group]},
    ).scalar_one()
    nucleus = models.NucleoAgrario(
        id_municipio=first.id_municipio_resuelto,
        nombre_nucleo=str(attrs["nombre_nucleo"]).strip(),
        tipo_nucleo=attrs["tipo_nucleo"],
        comunidad_indigena=bool(attrs.get("comunidad_indigena")),
        residencia=attrs.get("residencia"),
        geometria_poligono=geometry,
        fuente_datos=record.fuente,
        id_entidad_fuente=first.id_entidad_fuente,
        id_municipio_fuente=first.id_municipio_fuente,
        id_nucleo_fuente=first.id_nucleo_fuente,
        alcance_identidad_fuente=(record.opciones_mapeo or {}).get(
            "alcance_id_nucleo_fuente", "territorial"
        ) if first.id_nucleo_fuente else None,
        fecha_creacion=utcnow(),
        activo=True,
    )
    set_audit_context(db, user_id)
    db.add(nucleus)
    db.flush()
    for feature in group:
        feature.estado = "importado"
        feature.id_nucleo_operativo = nucleus.id_nucleo
        feature.fecha_importacion = utcnow()


def csv_report(db: Session, record: models.ImportacionArchivo) -> Iterable[str]:
    header_buffer = io.StringIO()
    writer = csv.writer(header_buffer)
    writer.writerow(["archivo", record.nombre_original])
    writer.writerow(["sha256", record.sha256])
    writer.writerow(["fuente", record.fuente])
    writer.writerow(["usuario_id", record.id_usuario_carga])
    writer.writerow(["fecha_carga", record.fecha_carga.isoformat()])
    writer.writerow(["crs_original", record.crs_original or ""])
    writer.writerow(["perfil_mapeo_id", record.id_perfil or ""])
    writer.writerow(["features_recibidos", record.total_features])
    writer.writerow(["validos_pendientes", record.validos])
    writer.writerow(["advertencias_pendientes", record.advertencias])
    writer.writerow(["errores", record.errores])
    writer.writerow(["importados", record.importados])
    writer.writerow(["descartados", record.descartados])
    writer.writerow([])
    writer.writerow([
        "indice", "estado", "id_externo", "nombre_nucleo", "tipo_nucleo",
        "entidad_id", "municipio_id", "errores", "advertencias",
        "transformaciones", "area_original_m2", "area_normalizada_m2",
        "diferencia_area_relativa", "nucleo_operativo_id",
    ])
    yield "\ufeff" + header_buffer.getvalue()
    query = (
        db.query(models.ImportacionFeature)
        .filter(models.ImportacionFeature.id_importacion == record.id_importacion)
        .order_by(models.ImportacionFeature.indice_feature)
        .yield_per(250)
    )
    for feature in query:
        row_buffer = io.StringIO()
        row_writer = csv.writer(row_buffer)
        attrs = feature.atributos_normalizados or {}
        row_writer.writerow([
            feature.indice_feature,
            feature.estado,
            feature.id_externo or "",
            attrs.get("nombre_nucleo") or "",
            attrs.get("tipo_nucleo") or "",
            feature.id_entidad_resuelta or "",
            feature.id_municipio_resuelto or "",
            json.dumps(feature.errores or [], ensure_ascii=False),
            json.dumps(feature.advertencias or [], ensure_ascii=False),
            json.dumps(feature.transformaciones or [], ensure_ascii=False),
            feature.area_original_m2 or "",
            feature.area_normalizada_m2 or "",
            feature.diferencia_area_relativa or "",
            feature.id_nucleo_operativo or "",
        ])
        yield row_buffer.getvalue()


def cleanup_expired_files() -> int:
    retention_days = max(1, int(os.getenv("IMPORT_STAGING_RETENTION_DAYS", "30")))
    db = SessionLocal()
    removed = 0
    try:
        rows = db.execute(
            text(
                """
                SELECT id_importacion, nombre_almacenado
                  FROM importacion_archivo
                 WHERE archivo_eliminado_en IS NULL
                   AND estado NOT IN ('analizando', 'normalizando', 'resolviendo', 'confirmando', 'importando')
                   AND fecha_carga < NOW() - make_interval(days => :days)
                """
            ),
            {"days": retention_days},
        ).mappings().all()
        system_user = db.query(models.Usuario).filter(models.Usuario.activo.is_(True), models.Usuario.rol == "admin").order_by(models.Usuario.id_usuario).first()
        if not system_user:
            return 0
        for row in rows:
            (_upload_root() / row["nombre_almacenado"]).unlink(missing_ok=True)
            record = db.get(models.ImportacionArchivo, row["id_importacion"])
            record.archivo_eliminado_en = utcnow()
            removed += 1
        set_audit_context(db, system_user.id_usuario)
        db.commit()
        return removed
    finally:
        db.close()
