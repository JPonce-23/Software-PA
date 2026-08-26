"""Single staged importer for project traces, nuclei and optional parcels."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path, PurePath
from typing import Any

from fastapi import HTTPException, UploadFile
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .. import models, schemas
from .access import (
    require_nucleus_access,
    require_parcel_access,
    require_project_access,
)
from .common import set_audit_context
from .gis_ingestion import IngestionError, inspect_dataset, iter_features


ALLOWED_TARGETS = {"trazo_proyecto", "nucleo_agrario", "parcela"}
EXTENSIONS = {
    ".geojson": "geojson",
    ".json": "geojson",
    ".kml": "kml",
    ".gpkg": "gpkg",
    ".zip": "zip",
}


def _root() -> Path:
    root = Path(os.getenv("UPLOAD_ROOT", "uploads")).resolve() / "importaciones"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def _safe_name(value: str | None) -> str:
    if not value or "\x00" in value:
        raise HTTPException(status_code=422, detail="Nombre de archivo inválido")
    normalized = value.replace("\\", "/")
    if PurePath(normalized).name != normalized:
        raise HTTPException(status_code=422, detail="Nombre de archivo no seguro")
    return PurePath(normalized).name[:255]


async def _store_upload(upload: UploadFile) -> tuple[Path, str, int, str, str]:
    original = _safe_name(upload.filename)
    declared = EXTENSIONS.get(Path(original).suffix.lower())
    if declared is None:
        raise HTTPException(
            status_code=415,
            detail="Formato no permitido; use GeoJSON, KML, GeoPackage o ZIP Shapefile",
        )
    destination = _root() / f"{uuid.uuid4().hex}{Path(original).suffix.lower()}"
    digest = hashlib.sha256()
    total = 0
    max_bytes = int(os.getenv("IMPORT_MAX_FILE_SIZE_MB", "100")) * 1024 * 1024
    try:
        with destination.open("xb") as stream:
            os.chmod(destination, 0o600)
            while chunk := await upload.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(status_code=413, detail="Archivo demasiado grande")
                digest.update(chunk)
                stream.write(chunk)
        if total == 0:
            raise HTTPException(status_code=422, detail="El archivo está vacío")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination, digest.hexdigest(), total, original, declared


def _extract_zip(path: Path) -> Path:
    destination = path.with_suffix("")
    destination.mkdir(mode=0o700)
    max_bytes = int(os.getenv("IMPORT_MAX_UNCOMPRESSED_MB", "500")) * 1024 * 1024
    total = 0
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            member = PurePath(info.filename)
            if (
                member.is_absolute()
                or ".." in member.parts
                or info.is_dir()
                or (info.external_attr >> 16) & 0o170000 == 0o120000
            ):
                if info.is_dir():
                    continue
                raise HTTPException(status_code=422, detail="ZIP no seguro")
            total += info.file_size
            if total > max_bytes:
                raise HTTPException(status_code=413, detail="ZIP expandido demasiado grande")
            target = (destination / Path(*member.parts)).resolve()
            if destination.resolve() not in target.parents:
                raise HTTPException(status_code=422, detail="ZIP no seguro")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
    shapes = sorted(destination.rglob("*.shp"))
    if len(shapes) != 1:
        raise HTTPException(
            status_code=422,
            detail="El ZIP debe contener exactamente un dataset Shapefile",
        )
    return shapes[0]


def _normalize_geometry(
    db: Session,
    geometry: dict[str, Any] | None,
    target: str,
) -> tuple[str | None, str | None]:
    if not geometry:
        return None, "GEOMETRIA_AUSENTE"
    dimension = 2 if target == "trazo_proyecto" else 3
    row = db.execute(
        text(
            """
            WITH parsed AS (
                SELECT ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326) AS geom
            ), normalized AS (
                SELECT ST_Multi(
                    ST_CollectionExtract(ST_MakeValid(geom), :dimension)
                ) AS geom
                FROM parsed
            )
            SELECT
                ST_AsText(geom) AS wkt,
                GeometryType(geom) AS geometry_type,
                ST_IsEmpty(geom) AS is_empty,
                ST_IsValid(geom) AS is_valid
            FROM normalized
            """
        ),
        {"geometry": json.dumps(geometry), "dimension": dimension},
    ).mappings().one()
    expected = "MULTILINESTRING" if dimension == 2 else "MULTIPOLYGON"
    if row["is_empty"] or not row["is_valid"] or row["geometry_type"] != expected:
        return None, f"GEOMETRIA_INVALIDA_{expected}"
    return row["wkt"], None


async def stage_import(
    db: Session,
    project_id: int,
    target: str,
    source: str,
    source_date: date | None,
    mapping: dict[str, str],
    upload: UploadFile,
    user: models.Usuario,
) -> models.ImportacionArchivo:
    require_project_access(db, user, project_id, mode="gis")
    if target not in ALLOWED_TARGETS:
        raise HTTPException(status_code=422, detail="Objetivo de importación no permitido")
    source = source.strip()
    if not source:
        raise HTTPException(status_code=422, detail="La fuente es obligatoria")
    if target != "trazo_proyecto" and not mapping.get("id_destino"):
        raise HTTPException(
            status_code=422,
            detail="Núcleo y parcela requieren mapeo explícito de id_destino",
        )
    path, digest, size, original, declared = await _store_upload(upload)
    existing = db.query(models.ImportacionArchivo).filter(
        models.ImportacionArchivo.id_proyecto == project_id,
        models.ImportacionArchivo.tipo_objetivo == target,
        models.ImportacionArchivo.sha256 == digest,
        models.ImportacionArchivo.activo.is_(True),
    ).first()
    if existing is not None:
        path.unlink(missing_ok=True)
        return existing
    dataset_path = path
    try:
        if declared == "zip":
            dataset_path = _extract_zip(path)
        dataset = inspect_dataset(dataset_path)
    except (IngestionError, zipfile.BadZipFile) as exc:
        path.unlink(missing_ok=True)
        if path.with_suffix("").is_dir():
            shutil.rmtree(path.with_suffix(""), ignore_errors=True)
        detail = getattr(exc, "public_detail", "Archivo geoespacial no procesable")
        raise HTTPException(status_code=422, detail=detail) from exc
    detected = declared if declared == "zip" else dataset.format
    if detected not in {"geojson", "kml", "gpkg", "zip", "shp"}:
        raise HTTPException(status_code=415, detail="Formato detectado no permitido")
    set_audit_context(db, user.id_usuario)
    record = models.ImportacionArchivo(
        id_proyecto=project_id,
        tipo_objetivo=target,
        nombre_original=original,
        nombre_almacenado=path.name,
        formato_detectado=detected,
        tamano_bytes=size,
        sha256=digest,
        fuente=source,
        fecha_fuente=source_date,
        crs_original=dataset.crs_description,
        columnas_detectadas=dataset.columns,
        mapeo=mapping,
        estado="procesando",
        total_features=dataset.total_features,
        id_usuario_carga=user.id_usuario,
        creado_por=user.id_usuario,
        fecha_procesamiento_inicio=datetime.now(timezone.utc),
    )
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
        valid = warnings = errors = processed = 0
        destination_key = mapping.get("id_destino")
        set_audit_context(db, user.id_usuario)
        for index, (layer, feature) in enumerate(iter_features(dataset_path, dataset)):
            properties = feature.get("properties") or {}
            geometry_wkt, geometry_error = _normalize_geometry(
                db, feature.get("geometry"), target
            )
            messages: list[dict[str, str]] = []
            normalized: dict[str, Any] = {}
            if geometry_error:
                messages.append({"codigo": geometry_error, "campo": "geometry"})
            if destination_key:
                raw_id = properties.get(destination_key)
                try:
                    normalized["id_destino"] = int(raw_id)
                except (TypeError, ValueError):
                    messages.append(
                        {"codigo": "ID_DESTINO_INVALIDO", "campo": destination_key}
                    )
            state = "error" if messages else "valido"
            errors += int(state == "error")
            valid += int(state == "valido")
            staged = models.ImportacionFeature(
                id_importacion=record.id_importacion,
                indice_feature=index,
                capa_origen=layer,
                id_externo=str(feature.get("id")) if feature.get("id") is not None else None,
                tipo_geometria=(feature.get("geometry") or {}).get("type"),
                atributos_originales=properties,
                atributos_normalizados=normalized,
                geometria_normalizada=(
                    WKTElement(geometry_wkt, srid=4326) if geometry_wkt else None
                ),
                estado=state,
                errores=messages,
                advertencias=[],
                transformaciones=[
                    {"codigo": "CRS_NORMALIZADO", "destino": "EPSG:4326"},
                    {"codigo": "TIPO_NORMALIZADO", "objetivo": target},
                ],
            )
            db.add(staged)
            processed += 1
        record.features_procesados = processed
        record.validos = valid
        record.advertencias = warnings
        record.errores = errors
        record.estado = "previsualizado"
        record.fecha_procesamiento_fin = datetime.now(timezone.utc)
        record.reporte = {
            "capas": [layer.name for layer in dataset.layers],
            "procesados": processed,
            "validos": valid,
            "errores": errors,
        }
        db.commit()
        db.refresh(record)
        return record
    except Exception as exc:
        db.rollback()
        failed = db.get(models.ImportacionArchivo, record.id_importacion)
        if failed is not None:
            set_audit_context(db, user.id_usuario)
            failed.estado = "error"
            failed.error_codigo = "STAGING_FALLIDO"
            failed.error_detalle = "No fue posible completar la previsualización"
            failed.fecha_procesamiento_fin = datetime.now(timezone.utc)
            db.commit()
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(
            status_code=422, detail="No fue posible procesar el archivo"
        ) from exc


def require_import_access(
    db: Session,
    import_id: int,
    user: models.Usuario,
    *,
    mode: str = "read",
) -> models.ImportacionArchivo:
    record = db.query(models.ImportacionArchivo).filter(
        models.ImportacionArchivo.id_importacion == import_id,
        models.ImportacionArchivo.activo.is_(True),
    ).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    require_project_access(db, user, record.id_proyecto, mode=mode)
    return record


def confirm_import(
    db: Session,
    import_id: int,
    data: schemas.ImportacionConfirmarRequest,
    user: models.Usuario,
) -> models.ImportacionArchivo:
    record = require_import_access(db, import_id, user, mode="gis")
    if not data.confirmacion_explicita:
        raise HTTPException(status_code=422, detail="Se requiere confirmación explícita")
    if record.estado != "previsualizado":
        raise HTTPException(status_code=409, detail="La importación no está previsualizada")
    if record.errores:
        raise HTTPException(status_code=409, detail="Corrija los features con error")
    if record.advertencias and not data.aceptar_advertencias:
        raise HTTPException(status_code=409, detail="Debe aceptar las advertencias")
    features = db.query(models.ImportacionFeature).filter(
        models.ImportacionFeature.id_importacion == import_id,
        models.ImportacionFeature.estado.in_(["valido", "advertencia"]),
    ).order_by(models.ImportacionFeature.indice_feature).all()
    if not features:
        raise HTTPException(status_code=409, detail="No hay features confirmables")
    set_audit_context(db, user.id_usuario)
    now = datetime.now(timezone.utc)
    try:
        if record.tipo_objetivo == "trazo_proyecto":
            active_traces = db.query(models.TrazoProyecto).filter(
                models.TrazoProyecto.id_proyecto == record.id_proyecto,
                models.TrazoProyecto.activo.is_(True),
            ).all()
            for trace in active_traces:
                trace.activo = False
                trace.fecha_baja = now
                trace.id_usuario_baja = user.id_usuario
                trace.motivo_baja = f"Sustituido por importación {record.id_importacion}"
            geometry_wkt = db.execute(
                text(
                    """
                    SELECT ST_AsText(
                        ST_Multi(ST_CollectionExtract(ST_Collect(geometria_normalizada), 2))
                    )
                    FROM importacion_feature
                    WHERE id_importacion = :id
                      AND estado IN ('valido', 'advertencia')
                    """
                ),
                {"id": import_id},
            ).scalar_one()
            version = db.query(
                func.coalesce(func.max(models.TrazoProyecto.version), 0)
            ).filter(models.TrazoProyecto.id_proyecto == record.id_proyecto).scalar() + 1
            trace = models.TrazoProyecto(
                id_proyecto=record.id_proyecto,
                version=version,
                geometria_linea=WKTElement(geometry_wkt, srid=4326),
                fuente=record.fuente,
                fecha_fuente=record.fecha_fuente,
                fecha_vigencia_inicio=record.fecha_fuente or date.today(),
                creado_por=user.id_usuario,
                observaciones=f"Generado por importación {record.id_importacion}",
            )
            db.add(trace)
            db.flush()
            for feature in features:
                feature.registro_destino_id = trace.id_trazo
                feature.estado = "confirmado"
                feature.fecha_importacion = now
        else:
            model = (
                models.NucleoAgrario
                if record.tipo_objetivo == "nucleo_agrario"
                else models.Parcela
            )
            for feature in features:
                destination_id = feature.atributos_normalizados.get("id_destino")
                destination = (
                    require_nucleus_access(
                        db, user, destination_id, mode="gis"
                    )
                    if record.tipo_objetivo == "nucleo_agrario"
                    else require_parcel_access(
                        db, user, destination_id, mode="gis"
                    )
                )
                destination_nucleus_id = (
                    destination.id_nucleo
                    if record.tipo_objetivo == "parcela"
                    else destination.id_nucleo
                )
                in_project = db.query(models.ProyectoNucleo.id_proyecto_nucleo).filter(
                    models.ProyectoNucleo.id_proyecto == record.id_proyecto,
                    models.ProyectoNucleo.id_nucleo == destination_nucleus_id,
                    models.ProyectoNucleo.activo.is_(True),
                ).first()
                if in_project is None:
                    raise HTTPException(
                        status_code=409,
                        detail="El destino geoespacial no pertenece al proyecto de la importación",
                    )
                destination.geometria_poligono = feature.geometria_normalizada
                destination.fuente_geometria = record.fuente
                destination.fecha_fuente_geometria = record.fecha_fuente
                destination.actualizado_en = now
                destination.actualizado_por = user.id_usuario
                feature.registro_destino_id = destination_id
                feature.estado = "confirmado"
                feature.fecha_importacion = now
        record.confirmacion_explicita = True
        record.fecha_confirmacion = now
        record.id_usuario_confirmacion = user.id_usuario
        record.importados = len(features)
        record.estado = "completo"
        record.actualizado_en = now
        record.actualizado_por = user.id_usuario
        record.reporte = {
            **(record.reporte or {}),
            "confirmados": len(features),
            "confirmado_en": now.isoformat(),
        }
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La confirmación se revirtió; no se modificaron geometrías",
        ) from exc
    db.refresh(record)
    return record
