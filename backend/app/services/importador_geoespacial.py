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
DERIVED_INTEGRITY_CODES = {
    "ID_EXTERNO_YA_IMPORTADO",
    "ID_EXTERNO_CONTRADICTORIO",
    "ID_EXTERNO_DUPLICADO",
    "PARTES_POR_UNIR",
    "IDENTIDAD_INSUFICIENTE_DUPLICADA",
    "NUCLEO_OPERATIVO_EXISTENTE",
    "GRUPO_MULTIPARTE_INCOMPLETO",
    "FALLO_IMPORTACION_OPERATIVA",
    "GEOMETRIA_CONSOLIDADA_INVALIDA",
}
logger = logging.getLogger(__name__)


class GroupImportError(RuntimeError):
    """Error controlado que revierte únicamente el grupo operativo actual."""


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
            procedencia_archivo="original" if dataset.format == "kml" else None,
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


def column_samples(record: models.ImportacionArchivo) -> dict[str, list[str]]:
    dataset = inspect_dataset(stored_path(record))
    samples = {column: [] for column in record.columnas_detectadas or []}
    max_values = 3
    for _, feature in iter_features(stored_path(record), dataset, limit_per_layer=max_values):
        properties = feature.get("properties") or {}
        if not isinstance(properties, dict):
            continue
        for column in samples:
            value = properties.get(column)
            if value is None or isinstance(value, (dict, list)):
                continue
            display = str(value).strip()
            if not display:
                continue
            display = display[:80]
            if display not in samples[column] and len(samples[column]) < max_values:
                samples[column].append(display)
    return samples


def update_mapping(
    db: Session,
    record: models.ImportacionArchivo,
    payload: MapeoImportacionRequest,
    user: models.Usuario,
) -> models.ImportacionArchivo:
    if record.estado in RUNNING_STATES or record.estado in {"confirmando", "importando", "completado"}:
        raise HTTPException(status_code=409, detail="El mapeo ya no puede modificarse en este estado.")
    validate_mapping(payload.mapeo, record.columnas_detectadas)
    validate_options(payload.opciones)
    origin = _validate_file_provenance(db, record, payload, user)
    user_id = user.id_usuario
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
    record.procedencia_archivo = payload.procedencia_archivo
    record.id_importacion_origen = origin.id_importacion if origin else None
    record.version_control += 1
    set_audit_context(db, user_id)
    db.commit()
    db.refresh(record)
    return record


def _validate_file_provenance(
    db: Session,
    record: models.ImportacionArchivo,
    payload: MapeoImportacionRequest,
    user: models.Usuario,
) -> models.ImportacionArchivo | None:
    provenance = payload.procedencia_archivo
    origin_id = payload.id_importacion_origen
    if record.formato_detectado == "kml":
        if provenance not in {None, "original"} or origin_id is not None:
            raise HTTPException(status_code=422, detail="Un KML se registra como archivo original y no puede depender de otra importacion.")
        payload.procedencia_archivo = "original"
        return None
    if provenance is None:
        raise HTTPException(
            status_code=422,
            detail="Indique si el GeoJSON es original o fue convertido desde un KML.",
        )
    if provenance == "original":
        if origin_id is not None:
            raise HTTPException(status_code=422, detail="Un GeoJSON original no debe tener un KML de referencia.")
        return None
    if origin_id is None:
        raise HTTPException(status_code=422, detail="Seleccione el KML original usado para generar el GeoJSON.")
    if origin_id == record.id_importacion:
        raise HTTPException(status_code=422, detail="El archivo no puede ser su propio origen.")
    origin = db.get(models.ImportacionArchivo, origin_id)
    if not origin or (user.rol != "admin" and origin.id_usuario_carga != user.id_usuario):
        raise HTTPException(status_code=404, detail="Archivo original de referencia no encontrado.")
    if origin.formato_detectado != "kml":
        raise HTTPException(status_code=422, detail="El archivo original de una conversion debe ser KML.")
    if normalize_text(origin.fuente) != normalize_text(record.fuente):
        raise HTTPException(status_code=422, detail="El KML original y el GeoJSON deben pertenecer a la misma fuente.")
    return origin


def _validate_conversion_feature_count(db: Session, record: models.ImportacionArchivo) -> None:
    if record.formato_detectado == "geojson" and not record.procedencia_archivo:
        raise IngestionError(
            "PROCEDENCIA_NO_DECLARADA",
            "Indique si el GeoJSON es original o fue convertido desde un KML antes de prevalidarlo.",
        )
    if record.procedencia_archivo != "conversion":
        return
    origin = db.get(models.ImportacionArchivo, record.id_importacion_origen)
    if not origin:
        raise IngestionError("ORIGEN_NO_DISPONIBLE", "El KML original de referencia no esta disponible.")
    if origin.total_features != record.total_features:
        difference = record.total_features - origin.total_features
        direction = "menos" if difference < 0 else "mas"
        raise IngestionError(
            "PERDIDA_CONVERSION",
            f"El KML original contiene {origin.total_features} features y el GeoJSON contiene {record.total_features}: la conversion produjo {abs(difference)} {direction}. Use el archivo original o repita la conversion.",
        )
    _validate_conversion_feature_fingerprints(origin, record)


def _feature_conversion_fingerprint(raw_feature: dict) -> str:
    payload = {
        "properties": raw_feature.get("properties") or {},
        "geometry": raw_feature.get("geometry"),
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _conversion_fingerprints(record: models.ImportacionArchivo) -> list[str]:
    dataset = inspect_dataset(stored_path(record))
    fingerprints: list[str] = []
    for _, raw_feature in iter_features(stored_path(record), dataset):
        fingerprints.append(_feature_conversion_fingerprint(raw_feature))
    return sorted(fingerprints)


def _validate_conversion_feature_fingerprints(
    origin: models.ImportacionArchivo,
    conversion: models.ImportacionArchivo,
) -> None:
    try:
        origin_fingerprints = _conversion_fingerprints(origin)
        conversion_fingerprints = _conversion_fingerprints(conversion)
    except (FileNotFoundError, IngestionError) as exc:
        raise IngestionError(
            "ORIGEN_NO_COMPARABLE",
            "No fue posible comparar cada feature con el KML original; la conversion queda bloqueada.",
        ) from exc
    if origin_fingerprints != conversion_fingerprints:
        raise IngestionError(
            "CAMBIO_CONVERSION",
            "El GeoJSON convertido no conserva el mismo conjunto de atributos y geometrías del KML original. Use el archivo original o repita la conversion.",
        )


def validate_confirmation_provenance(db: Session, record: models.ImportacionArchivo) -> None:
    try:
        _validate_conversion_feature_count(db, record)
    except IngestionError as exc:
        raise HTTPException(status_code=409, detail=exc.public_detail) from exc


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
    # Algunos extractos RAN usan 0 como marcador de "sin identificador".
    # Conservarlo en atributos_originales, pero nunca usarlo como identidad.
    if not cleaned or cleaned.casefold() in {"0", "null", "n/a", "na", "s/d"}:
        return None
    return cleaned[:200]


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
        delta_str = str(delta) if delta is not None else None
        transformations.append(_message(
            "ST_MAKEVALID", 
            "geometria", 
            "La geometria invalida fue procesada con ST_MakeValid.",
            validez_original=result["was_valid"],
            area_original=float(result["original_area"]) if result["original_area"] is not None else None,
            area_resultante=float(result["repaired_area"]) if result["repaired_area"] is not None else None,
            diferencia_absoluta=abs(float(result["repaired_area"]) - float(result["original_area"])) if (result["repaired_area"] is not None and result["original_area"] is not None) else None,
            diferencia_relativa=float(delta) if delta is not None else None,
            tolerancia_configurada=float(tolerance) if tolerance is not None else None,
        ))
        if tolerance is None:
            errors.append(_message("TOLERANCIA_AREA_NO_CONFIGURADA", "geometria", "La geometria fue reparada, pero no existe una tolerancia de area aprobada; el feature queda bloqueado."))
        elif delta is None or delta > tolerance:
            percentage = f"{(delta or Decimal(0)) * 100:.2f}"
            errors.append(_message("REPARACION_SUPERA_TOLERANCIA", "geometria", f"La reparacion cambio el area {percentage} %, superando la tolerancia configurada.", diferencia_area_relativa=delta_str))
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


def _multipart_group_identity(record: models.ImportacionArchivo, feature: models.ImportacionFeature) -> tuple | None:
    """Identidad final de una parte que ya tiene territorio resuelto."""
    return _external_identity(record, feature)


def _source_nucleus_identity(record: models.ImportacionArchivo, feature: models.ImportacionFeature) -> tuple | None:
    """Clave conservadora para no separar partes mientras una carece de municipio resuelto."""
    if not feature.id_nucleo_fuente:
        return None
    source = normalize_text(record.fuente)
    scope = (record.opciones_mapeo or {}).get("alcance_id_nucleo_fuente", "territorial")
    if scope == "global":
        return ("global", source, feature.id_nucleo_fuente)
    return ("territorial_pendiente", source, feature.id_nucleo_fuente)


def _append_problem(feature: models.ImportacionFeature, problem: dict, warning: bool = False) -> None:
    target_list = feature.advertencias if warning else feature.errores
    current_problems = target_list or []
    
    # Check for duplicate
    is_duplicate = False
    for existing in current_problems:
        if (existing.get("codigo") == problem.get("codigo") and
            existing.get("campo") == problem.get("campo") and
            existing.get("mensaje") == problem.get("mensaje")):
            is_duplicate = True
            break
            
    if not is_duplicate:
        if warning:
            feature.advertencias = [*current_problems, problem]
            if feature.estado == "valido":
                feature.estado = "advertencia"
        else:
            feature.errores = [*current_problems, problem]
            feature.estado = "error"


def _reset_derived_integrity_problems(features: Iterable[models.ImportacionFeature]) -> None:
    """Elimina hallazgos derivados antes de volver a evaluar una importación."""
    for feature in features:
        if feature.estado in {"importado", "descartado"}:
            continue
        feature.errores = [
            problem for problem in (feature.errores or [])
            if problem.get("codigo") not in DERIVED_INTEGRITY_CODES
        ]
        feature.advertencias = [
            problem for problem in (feature.advertencias or [])
            if problem.get("codigo") not in DERIVED_INTEGRITY_CODES
        ]
        feature.estado = "error" if feature.errores else "advertencia" if feature.advertencias else "valido"


def _detect_duplicates(db: Session, record: models.ImportacionArchivo) -> None:
    features = (
        db.query(models.ImportacionFeature)
        .filter(models.ImportacionFeature.id_importacion == record.id_importacion)
        .order_by(models.ImportacionFeature.indice_feature)
        .all()
    )
    _reset_derived_integrity_problems(features)
    identities: dict[tuple, list[models.ImportacionFeature]] = defaultdict(list)
    source_nucleus_groups: dict[tuple, list[models.ImportacionFeature]] = defaultdict(list)
    names: dict[tuple, list[models.ImportacionFeature]] = defaultdict(list)
    for feature in features:
        identity = _external_identity(record, feature)
        if identity:
            identities[identity].append(feature)
        source_nucleus_identity = _source_nucleus_identity(record, feature)
        if source_nucleus_identity:
            source_nucleus_groups[source_nucleus_identity].append(feature)
        name = normalize_text((feature.atributos_normalizados or {}).get("nombre_nucleo"))
        if name and feature.id_municipio_resuelto:
            names[(feature.id_municipio_resuelto, name)].append(feature)

    join_parts = bool((record.opciones_mapeo or {}).get("unir_partes_mismo_id"))
    for group in source_nucleus_groups.values():
        if len(group) <= 1:
            continue
        # Sin municipio resuelto no puede demostrarse a cuál identidad territorial
        # pertenece la parte. Se bloquea todo el ID de fuente hasta resolverlo.
        if any(item.id_municipio_resuelto is None for item in group):
            for feature in group:
                if feature.estado != "error":
                    _append_problem(
                        feature,
                        _message(
                            "GRUPO_MULTIPARTE_INCOMPLETO",
                            "geometria",
                            "El núcleo multiparte tiene al menos una parte con error, descartada o sin resolución; ninguna parte puede importarse por separado.",
                        ),
                    )
            continue
        groups_by_territory: dict[int, list[models.ImportacionFeature]] = defaultdict(list)
        for feature in group:
            groups_by_territory[feature.id_municipio_resuelto].append(feature)
        for territorial_group in groups_by_territory.values():
            if len(territorial_group) <= 1:
                continue
            if any(
                item.estado in {"error", "pendiente_revision", "descartado"}
                or item.geometria_normalizada is None
                for item in territorial_group
            ):
                for feature in territorial_group:
                    if feature.estado != "error":
                        _append_problem(
                            feature,
                            _message(
                                "GRUPO_MULTIPARTE_INCOMPLETO",
                                "geometria",
                                "El núcleo multiparte tiene al menos una parte con error, descartada o sin resolución; ninguna parte puede importarse por separado.",
                            ),
                        )
                continue
            signatures = {
                (
                    normalize_text((item.atributos_normalizados or {}).get("nombre_nucleo")),
                    (item.atributos_normalizados or {}).get("tipo_nucleo"),
                    item.id_municipio_resuelto,
                )
                for item in territorial_group
            }
            if len(signatures) > 1:
                detalles_contradictorios = list(signatures)
                for feature in territorial_group:
                    _append_problem(feature, _message(
                        "ID_EXTERNO_CONTRADICTORIO", 
                        "id_nucleo_fuente", 
                        "El mismo ID externo contiene nombre, tipo o territorio contradictorio.",
                        valores_encontrados=[{"nombre": s[0], "tipo": s[1], "municipio_id": s[2]} for s in detalles_contradictorios]
                    ))

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
            detalles_contradictorios = list(signatures)
            for feature in group:
                _append_problem(feature, _message(
                    "ID_EXTERNO_CONTRADICTORIO", 
                    "id_nucleo_fuente", 
                    "El mismo ID externo contiene nombre, tipo o territorio contradictorio.",
                    valores_encontrados=[{"nombre": s[0], "tipo": s[1], "municipio_id": s[2]} for s in detalles_contradictorios]
                ))
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
    
    total = record.validos + record.advertencias + record.errores + record.importados + record.descartados
    if total != record.total_features:
        logger.error(f"Inconsistencia en conteo de features: suma {total} != total {record.total_features}")
        raise IngestionError("CONTEO_INCONSISTENTE", f"La suma de estados ({total}) no coincide con el total de features ({record.total_features}).")


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
        _validate_conversion_feature_count(db, record)
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
        if payload.aceptar_advertencias is not None:
            feature.advertencias_aceptadas = payload.aceptar_advertencias
        feature.estado = "error" if feature.errores else "advertencia" if feature.advertencias else "valido"
        feature.id_usuario_revision = user_id
        feature.fecha_revision = utcnow()
    _detect_duplicates(db, record)
    _recount(db, record)
    set_audit_context(db, user_id)
    db.commit()
    db.refresh(feature)
    return feature


def _confirmation_groups(
    record: models.ImportacionArchivo,
    candidates: list[models.ImportacionFeature],
    all_features: list[models.ImportacionFeature],
) -> list[list[models.ImportacionFeature]]:
    """Devuelve sólo grupos completos; una parte no autorizada bloquea al núcleo entero."""
    all_by_identity: dict[tuple, list[models.ImportacionFeature]] = defaultdict(list)
    for feature in all_features:
        identity = _multipart_group_identity(record, feature)
        if identity:
            all_by_identity[identity].append(feature)

    candidate_ids = {feature.id_importacion_feature for feature in candidates}
    groups: list[list[models.ImportacionFeature]] = []
    seen: set[tuple] = set()
    for feature in candidates:
        identity = _multipart_group_identity(record, feature)
        key = identity or ("feature", feature.id_importacion_feature)
        if key in seen:
            continue
        seen.add(key)
        group = all_by_identity.get(identity, [feature]) if identity else [feature]
        complete = all(
            part.id_importacion_feature in candidate_ids
            and part.estado in {"valido", "advertencia"}
            and (part.estado != "advertencia" or part.advertencias_aceptadas)
            and part.geometria_normalizada is not None
            and part.id_municipio_resuelto is not None
            for part in group
        )
        if not complete:
            continue
        groups.append(group)
    return groups


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
                       OR (
                           estado = 'completado'
                           AND EXISTS (
                               SELECT 1
                                 FROM importacion_feature feature
                                WHERE feature.id_importacion = importacion_archivo.id_importacion
                                  AND feature.estado = 'advertencia'
                                  AND (feature.advertencias_aceptadas = TRUE OR :accept_warnings = TRUE)
                           )
                       )
                   )
                RETURNING id_importacion
                """
            ),
            {"id": import_id, "user_id": user_id, "accept_warnings": accept_warnings},
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
        candidates = (
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
        all_features = (
            db.query(models.ImportacionFeature)
            .filter(models.ImportacionFeature.id_importacion == import_id)
            .order_by(models.ImportacionFeature.indice_feature)
            .all()
        )
        groups = _confirmation_groups(record, candidates, all_features)
        batch_size = max(1, int(os.getenv("IMPORT_CONFIRM_BATCH_SIZE", "100")))
        for offset in range(0, len(groups), batch_size):
            for group in groups[offset : offset + batch_size]:
                try:
                    with db.begin_nested():
                        _import_group(db, record, group, user_id)
                except (DBAPIError, IntegrityError, GroupImportError) as exc:
                    for feature in group:
                        if isinstance(exc, GroupImportError):
                            _append_problem(feature, _message("GEOMETRIA_CONSOLIDADA_INVALIDA", "geometria", "La geometría consolidada del núcleo multiparte no es válida y no fue importada."))
                        else:
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
            WITH consolidada AS (
                SELECT ST_Multi(ST_CollectionExtract(ST_UnaryUnion(ST_Collect(geometria_normalizada)), 3)) AS geom
                  FROM importacion_feature
                 WHERE id_importacion_feature = ANY(:ids)
            )
            SELECT ST_AsText(geom) AS wkt,
                   ST_IsValid(geom) AS is_valid,
                   ST_SRID(geom) AS srid,
                   ST_GeometryType(geom) AS tipo,
                   ST_Area(ST_Transform(geom, 6933)) AS area_m2,
                   NOT ST_IsEmpty(geom)
                   AND ST_IsValid(geom)
                   AND ST_SRID(geom) = 4326
                   AND ST_GeometryType(geom) = 'ST_MultiPolygon'
                   AND ST_NumGeometries(geom) > 0 AS es_valida
              FROM consolidada
            """
        ),
        {"ids": [item.id_importacion_feature for item in group]},
    ).mappings().one()
    
    if not geometry["es_valida"] or not geometry["wkt"]:
        raise GroupImportError(
            f"La geometría consolidada no cumple el contrato MultiPolygon EPSG:4326. Validez: {geometry['is_valid']}, Tipo: {geometry['tipo']}, SRID: {geometry['srid']}"
        )
        
    consolidated_info = _message(
        "GEOMETRIA_CONSOLIDADA", 
        "geometria", 
        "Las partes se consolidaron en un unico MultiPolygon.",
        partes_originales=len(group),
        es_valida=geometry["is_valid"],
        tipo=geometry["tipo"],
        srid=geometry["srid"],
        area_final_m2=float(geometry["area_m2"]) if geometry["area_m2"] is not None else None
    )
    nucleus = models.NucleoAgrario(
        id_municipio=first.id_municipio_resuelto,
        nombre_nucleo=str(attrs["nombre_nucleo"]).strip(),
        tipo_nucleo=attrs["tipo_nucleo"],
        comunidad_indigena=bool(attrs.get("comunidad_indigena")),
        residencia=attrs.get("residencia"),
        geometria_poligono=geometry["wkt"],
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
        if len(group) > 1:
            feature.transformaciones = [*(feature.transformaciones or []), consolidated_info]
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
    writer.writerow(["formato_detectado", record.formato_detectado])
    writer.writerow(["crs_original", record.crs_original or ""])
    writer.writerow(["procedencia_archivo", record.procedencia_archivo or ""])
    writer.writerow(["importacion_origen_id", record.id_importacion_origen or ""])
    if record.id_importacion_origen:
        origin = db.get(models.ImportacionArchivo, record.id_importacion_origen)
        writer.writerow(["archivo_origen", origin.nombre_original if origin else ""])
        writer.writerow(["sha256_origen", origin.sha256 if origin else ""])
        writer.writerow(["features_origen", origin.total_features if origin else ""])
    writer.writerow(["perfil_mapeo_id", record.id_perfil or ""])
    writer.writerow(["mapeo_efectivo", json.dumps(record.mapeo or {}, ensure_ascii=False)])
    
    opciones = record.opciones_mapeo or {}
    writer.writerow(["opciones_efectivas", json.dumps(opciones, ensure_ascii=False)])
    writer.writerow(["alcance_id_nucleo_fuente", opciones.get("alcance_id_nucleo_fuente", "territorial")])
    writer.writerow(["unir_partes_mismo_id", opciones.get("unir_partes_mismo_id", False)])
    writer.writerow(["id_municipio_fuente_semantica", opciones.get("id_municipio_fuente_semantica", "")])
    writer.writerow(["tolerancia_area_relativa", record.tolerancia_area_relativa if record.tolerancia_area_relativa is not None else ""])
    
    writer.writerow(["features_recibidos", record.total_features])
    writer.writerow(["validos_pendientes", record.validos])
    writer.writerow(["advertencias_pendientes", record.advertencias])
    writer.writerow(["errores", record.errores])
    writer.writerow(["importados", record.importados])
    writer.writerow(["descartados", record.descartados])
    writer.writerow([])
    writer.writerow([
        "indice", "capa_origen", "estado", "id_externo", 
        "id_entidad_fuente", "id_municipio_fuente", "id_nucleo_fuente",
        "nombre_nucleo", "tipo_nucleo",
        "entidad_id", "municipio_id", "errores", "advertencias",
        "transformaciones", "area_original_m2", "area_normalizada_m2",
        "diferencia_area_absoluta_m2", "diferencia_area_relativa", 
        "advertencias_aceptadas", "usuario_revision", "fecha_revision",
        "nucleo_operativo_id",
    ])
    yield "\ufeff" + header_buffer.getvalue()
    query = (
        db.query(models.ImportacionFeature)
        .filter(models.ImportacionFeature.id_importacion == record.id_importacion)
        .order_by(models.ImportacionFeature.indice_feature)
        .yield_per(250)
    )
    def _csv_val(val: Any) -> Any:
        return "" if val is None else val

    identities_summary = defaultdict(list)
    for feature in query:
        row_buffer = io.StringIO()
        row_writer = csv.writer(row_buffer)
        attrs = feature.atributos_normalizados or {}
        diff_abs = ""
        if feature.area_normalizada_m2 is not None and feature.area_original_m2 is not None:
            diff_abs = abs(feature.area_normalizada_m2 - feature.area_original_m2)

        # Para el resumen territorial
        ident_key = (
            normalize_text(record.fuente),
            feature.id_municipio_resuelto or "NO_RESUELTO",
            feature.id_nucleo_fuente or "SIN_ID_FUENTE"
        )
        identities_summary[ident_key].append(feature)

        row_writer.writerow([
            feature.indice_feature,
            _csv_val(feature.capa_origen),
            feature.estado,
            _csv_val(feature.id_externo),
            _csv_val(feature.id_entidad_fuente),
            _csv_val(feature.id_municipio_fuente),
            _csv_val(feature.id_nucleo_fuente),
            _csv_val(attrs.get("nombre_nucleo")),
            _csv_val(attrs.get("tipo_nucleo")),
            _csv_val(feature.id_entidad_resuelta),
            _csv_val(feature.id_municipio_resuelto),
            json.dumps(feature.errores or [], ensure_ascii=False),
            json.dumps(feature.advertencias or [], ensure_ascii=False),
            json.dumps(feature.transformaciones or [], ensure_ascii=False),
            _csv_val(feature.area_original_m2),
            _csv_val(feature.area_normalizada_m2),
            _csv_val(diff_abs),
            _csv_val(feature.diferencia_area_relativa),
            "true" if feature.advertencias_aceptadas else "false",
            _csv_val(feature.id_usuario_revision),
            feature.fecha_revision.isoformat() if feature.fecha_revision else "",
            _csv_val(feature.id_nucleo_operativo),
        ])
        yield row_buffer.getvalue()

    # Escribir resumen por identidad territorial
    yield "\r\n"
    resumen_buffer = io.StringIO()
    resumen_writer = csv.writer(resumen_buffer)
    resumen_writer.writerow(["RESUMEN POR IDENTIDAD TERRITORIAL"])
    resumen_writer.writerow([
        "fuente", "municipio_resuelto", "id_nucleo_fuente",
        "tipo_nucleo_agrupado", "numero_partes", "nucleos_operativos_generados",
        "identidad_importable", "bloqueada", "causa_bloqueo"
    ])
    yield resumen_buffer.getvalue()

    for (fuente, id_mun, id_nuc), parts in identities_summary.items():
        resumen_buffer = io.StringIO()
        resumen_writer = csv.writer(resumen_buffer)
        
        # Determinar estado de la identidad
        bloqueada = any(p.estado in {"error", "descartado"} for p in parts)
        importable = all(p.estado in {"valido", "importado"} or (p.estado == "advertencia" and p.advertencias_aceptadas) for p in parts)
        
        causas = set()
        for p in parts:
            for error in (p.errores or []):
                causas.add(error.get("codigo", ""))
        
        operativos = {p.id_nucleo_operativo for p in parts if p.id_nucleo_operativo}
        tipos = { (p.atributos_normalizados or {}).get("tipo_nucleo", "") for p in parts }
        
        resumen_writer.writerow([
            fuente, id_mun, id_nuc,
            "|".join(filter(None, tipos)),
            len(parts),
            "|".join(map(str, operativos)),
            "true" if importable and not bloqueada else "false",
            "true" if bloqueada else "false",
            "|".join(filter(None, causas))
        ])
        yield resumen_buffer.getvalue()


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


def archivar_importacion(
    db: Session,
    record: models.ImportacionArchivo,
    id_usuario: int,
    motivo_baja: str,
) -> dict[str, str]:
    if record.estado in RUNNING_STATES:
        raise HTTPException(409, f"No se puede archivar una importación en estado '{record.estado}'")
    if record.fecha_baja is not None:
        raise HTTPException(400, "La importación ya se encuentra archivada")

    set_audit_context(db, id_usuario)
    record.fecha_baja = utcnow()
    record.id_usuario_baja = id_usuario
    record.motivo_baja = motivo_baja
    db.commit()
    return {"status": "ok", "message": "Importación archivada correctamente"}
