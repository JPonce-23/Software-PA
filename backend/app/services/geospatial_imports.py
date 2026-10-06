"""Staged GIS imports, including the strict GeoPackage flow for DDV."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path, PurePath
from typing import Any

from fastapi import HTTPException, UploadFile
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, text
from sqlalchemy.exc import DBAPIError
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
RAN_NUCLEI_SOURCE = "RAN_PHINA_CATALOGO_NUCLEOS"
STRICT_NUCLEUS_TARGET = "nucleo_agrario_gpkg"
STRICT_PARCEL_TARGET = "parcela_gpkg"


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


async def _store_upload(
    upload: UploadFile, *, allowed_formats: set[str] | None = None,
    strict_label: str = "El DDV",
) -> tuple[Path, str, int, str, str]:
    original = _safe_name(upload.filename)
    declared = EXTENSIONS.get(Path(original).suffix.lower())
    if allowed_formats is not None and declared not in allowed_formats:
        raise HTTPException(status_code=415, detail=f"{strict_label} requiere un archivo .gpkg")
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
                SELECT ST_SetSRID(ST_Force2D(ST_GeomFromGeoJSON(:geometry)), 4326) AS geom
            ), normalized AS (
                SELECT ST_Multi(
                    ST_CollectionExtract(ST_MakeValid(geom), :dimension)
                ) AS geom
                FROM parsed
            )
            SELECT
                ST_AsText(geom, 17) AS wkt,
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


def _normalize_ddv_geometry(
    db: Session, geometry: dict[str, Any] | None,
    *, source_is_valid: bool | None = None,
) -> tuple[str | None, list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    warnings: list[dict[str, str]] = []
    transformations: list[dict[str, str]] = []
    if not geometry:
        return None, [{"codigo": "GEOMETRIA_AUSENTE", "campo": "geometry"}], warnings, transformations
    original_type = geometry.get("type")
    if original_type not in {"Polygon", "MultiPolygon"}:
        return None, [{"codigo": "TIPO_GEOMETRIA_NO_PERMITIDO", "campo": "geometry"}], warnings, transformations
    payload = json.dumps(geometry)
    reason = "No se pudo interpretar la geometría"
    try:
        with db.begin_nested():
            inspected = db.execute(
                text(
                    """
                    WITH source AS (
                        SELECT ST_SetSRID(ST_Force2D(ST_GeomFromGeoJSON(:geometry)), 4326) AS geom
                    )
                    SELECT ST_IsEmpty(geom) AS vacia,
                           ST_IsValid(geom) AS valida,
                           ST_IsValidReason(geom) AS razon
                    FROM source
                    """
                ),
                {"geometry": payload},
            ).mappings().one()
            reason = inspected["razon"]
            if inspected["vacia"]:
                return None, [{
                    "codigo": "GEOMETRIA_IRRECUPERABLE",
                    "campo": "geometry",
                    "razon": "Geometría vacía",
                }], warnings, transformations
            if not inspected["valida"] and source_is_valid is True:
                return None, [{"codigo":"PIPELINE_ALTERO_TOPOLOGIA","campo":"geometry","razon":reason}], warnings, transformations
            expression = (
                "ST_Multi(geom)" if inspected["valida"]
                else "ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))"
            )
            row = db.execute(
                text(f"""
                    WITH source AS (
                        SELECT ST_SetSRID(ST_Force2D(ST_GeomFromGeoJSON(:geometry)), 4326) AS geom
                    ), normalized AS (
                        SELECT {expression} AS geom FROM source
                    )
                    SELECT ST_AsText(geom, 17) AS wkt,
                           GeometryType(geom) AS tipo,
                           ST_IsEmpty(geom) AS vacia,
                           ST_IsValid(geom) AS valida
                    FROM normalized
                """),
                {"geometry": payload},
            ).mappings().one()
    except (DBAPIError, ValueError, TypeError):
        return None, [{
            "codigo": "GEOMETRIA_IRRECUPERABLE",
            "campo": "geometry",
            "razon": reason,
        }], warnings, transformations
    if row["vacia"] or not row["valida"] or row["tipo"] != "MULTIPOLYGON":
        return None, [{
            "codigo": "GEOMETRIA_IRRECUPERABLE",
            "campo": "geometry",
            "razon": reason if not inspected["valida"] else "Sin componente poligonal valido",
        }], warnings, transformations
    if original_type == "Polygon":
        transformations.append({"codigo": "POLYGON_A_MULTIPOLYGON"})
    if not inspected["valida"]:
        repair = {"codigo": "GEOMETRIA_REPARADA", "razon": reason}
        warnings.append(repair)
        transformations.append(repair)
    return row["wkt"], [], warnings, transformations


def _ddv_crs_identifiable(description: str) -> bool:
    normalized = description.strip().upper()
    if not normalized or normalized in {"EPSG:0", "EPSG:-1"}:
        return False
    return not (
        normalized.startswith((
            'GEOGCRS["UNDEFINED', 'GEOGCS["UNDEFINED',
            'PROJCRS["UNDEFINED', 'PROJCS["UNDEFINED',
            'GEOGCRS["UNKNOWN', 'GEOGCS["UNKNOWN',
            'PROJCRS["UNKNOWN', 'PROJCS["UNKNOWN',
        ))
        or 'DATUM["UNKNOWN"' in normalized
    )


async def stage_ddv_import(
    db: Session,
    project_id: int,
    source: str,
    source_date: date | None,
    upload: UploadFile,
    user: models.Usuario,
) -> models.ImportacionArchivo:
    return await _stage_strict_gpkg_import(
        db, project_id, source, source_date, upload, user,
        target="derecho_via_proyecto",
    )


async def stage_nucleus_import(
    db: Session,
    project_id: int,
    source: str,
    source_date: date | None,
    upload: UploadFile,
    user: models.Usuario,
    *, scope: str,
) -> models.ImportacionArchivo:
    return await _stage_strict_gpkg_import(
        db, project_id, source, source_date, upload, user,
        target=STRICT_NUCLEUS_TARGET, scope=scope,
    )


async def stage_parcel_import(
    db: Session,
    project_id: int,
    source: str,
    source_date: date | None,
    upload: UploadFile,
    user: models.Usuario,
    *, scope: str,
) -> models.ImportacionArchivo:
    return await _stage_strict_gpkg_import(
        db, project_id, source, source_date, upload, user,
        target=STRICT_PARCEL_TARGET, scope=scope,
    )


def normalize_parcel_number(value: str) -> str:
    """Coincide con el índice actual (espacios/caja) y el único formato Excel auditado.

    No elimina sufijos ni signos generales: sólo P.-<dígitos> equivale a P-<dígitos>.
    """
    normalized = re.sub(r"\s+", " ", value.strip()).lower()
    if re.fullmatch(r"p\.-[0-9]+", normalized):
        return "p-" + normalized[3:]
    return normalized


async def _stage_strict_gpkg_import(db, project_id, source, source_date, upload, user, *, target, scope="completa"):
    from .gis_reconciliation import stage
    return await stage(db,project_id,source,source_date,upload,user,target=target,scope=scope)


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
    if target in {"nucleo_agrario", "parcela"}:
        if not mapping.get("id_destino"):
            raise HTTPException(422, "Se requiere mapeo explícito de id_destino")
        from .gis_reconciliation import stage
        return await stage(db,project_id,source,source_date,upload,user,target=target,mapping=mapping,strict=False)
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


def _confirm_ddv_import(
    db: Session,
    record: models.ImportacionArchivo,
    data: schemas.ImportacionConfirmarRequest,
    user: models.Usuario,
) -> models.ImportacionArchivo:
    try:
        db.query(models.Proyecto).filter_by(id_proyecto=record.id_proyecto).with_for_update().one()
        require_project_access(db,user,record.id_proyecto,mode='gis')
        from .gis_reconciliation import working_srid
        if working_srid(db,record.id_proyecto)!=record.srid_trabajo:
            raise HTTPException(409,"La configuración CRS cambió; reprocesar fuente")
        record = db.query(models.ImportacionArchivo).filter(
            models.ImportacionArchivo.id_importacion == record.id_importacion,
            models.ImportacionArchivo.activo.is_(True),
        ).populate_existing().with_for_update().one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="Importación no encontrada")
        if record.tipo_objetivo != "derecho_via_proyecto":
            raise HTTPException(status_code=409, detail="Objetivo de importación inconsistente")
        if record.estado == "completo":
            db.commit()
            return record
        if record.estado != "previsualizado":
            raise HTTPException(status_code=409, detail="La importación no está previsualizada")
        if record.errores:
            raise HTTPException(status_code=409, detail="Corrija los features con error")
        if record.advertencias and not data.aceptar_advertencias:
            raise HTTPException(status_code=409, detail="Debe aceptar las advertencias")

        # La fila del proyecto serializa confirmaciones de importaciones DDV
        # diferentes antes de consultar max(version) y cambiar la vigente.
        db.query(models.Proyecto).filter(
            models.Proyecto.id_proyecto == record.id_proyecto,
            models.Proyecto.activo.is_(True),
        ).with_for_update().one()
        features = db.query(models.ImportacionFeature).filter(
            models.ImportacionFeature.id_importacion == record.id_importacion,
            models.ImportacionFeature.estado.in_(["valido", "advertencia"]),
        ).order_by(models.ImportacionFeature.indice_feature).all()
        if (
            not features
            or len(features) != record.total_features
            or len(features) != record.features_procesados
            or any(feature.geometria_normalizada is None for feature in features)
        ):
            raise HTTPException(status_code=409, detail="Staging DDV incompleto")

        assembled = db.execute(
            text(
                """
                WITH aggregate AS (
                    SELECT ST_Multi(ST_CollectionExtract(
                        ST_UnaryUnion(ST_Collect(geometria_normalizada)), 3
                    )) AS geom
                    FROM importacion_feature
                    WHERE id_importacion = :id
                      AND estado IN ('valido', 'advertencia')
                )
                SELECT ST_AsText(geom, 17) AS wkt,
                       GeometryType(geom) AS tipo,
                       ST_IsEmpty(geom) AS vacia,
                       ST_IsValid(geom) AS valida
                FROM aggregate
                """
            ),
            {"id": record.id_importacion},
        ).mappings().one()
        if (
            not assembled["wkt"]
            or assembled["tipo"] != "MULTIPOLYGON"
            or assembled["vacia"]
            or not assembled["valida"]
        ):
            raise HTTPException(status_code=409, detail="DDV agregado inválido")

        working = db.execute(text("""
            WITH assembled AS (
                SELECT ST_Multi(ST_CollectionExtract(ST_UnaryUnion(ST_Collect(
                    COALESCE(geometria_trabajo,geometria_normalizada))),3)) AS geom
                FROM importacion_feature WHERE id_importacion=:i
            ) SELECT ST_AsText(geom,17) AS wkt,ST_IsValid(geom) AS valid,
                ST_IsEmpty(geom) AS empty,ST_SRID(geom) AS srid FROM assembled
        """),{"i":record.id_importacion}).mappings().one()
        if not working["valid"] or working["empty"] or working["srid"]!=record.srid_trabajo:
            raise HTTPException(409,"DDV agregado inválido en el CRS de trabajo")
        now = datetime.now(timezone.utc)
        set_audit_context(db, user.id_usuario)
        previous = db.query(models.DerechoViaProyecto).filter(
            models.DerechoViaProyecto.id_proyecto == record.id_proyecto,
            models.DerechoViaProyecto.es_vigente.is_(True),
        ).one_or_none()
        if previous is not None:
            previous.es_vigente = False
            previous.actualizado_en = now
            previous.actualizado_por = user.id_usuario
            db.flush()
        version = db.query(
            func.coalesce(func.max(models.DerechoViaProyecto.version), 0)
        ).filter(
            models.DerechoViaProyecto.id_proyecto == record.id_proyecto
        ).scalar() + 1
        derecho_via = models.DerechoViaProyecto(
            id_proyecto=record.id_proyecto,
            version=version,
            es_vigente=True,
            activo=True,
            geometria_poligono=WKTElement(assembled["wkt"], srid=4326),
            fuente=record.fuente,
            fecha_fuente=record.fecha_fuente,
            creado_por=user.id_usuario,
            id_importacion=record.id_importacion,
            sha256=record.sha256,
            srid_trabajo=record.srid_trabajo,
            geometria_trabajo=WKTElement(working["wkt"],srid=record.srid_trabajo),
            observaciones=f"Generado por importación {record.id_importacion}",
        )
        db.add(derecho_via)
        db.flush()
        for feature in features:
            feature.estado_conciliacion = "confirmado"
            feature.registro_destino_id = derecho_via.id_derecho_via
            feature.estado = "confirmado"
            feature.fecha_importacion = now
            if feature.advertencias:
                feature.advertencias_aceptadas = True
                feature.id_usuario_revision = user.id_usuario
                feature.fecha_revision = now
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
            "version_ddv": version,
            "id_derecho_via": derecho_via.id_derecho_via,
            "advertencias_aceptadas": bool(record.advertencias),
            "confirmado_en": now.isoformat(),
        }
        from .gis_history import ddv_changed
        ddv_changed(db,record,previous,derecho_via,user)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La confirmación DDV se revirtió completamente",
        ) from exc
    db.refresh(record)
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
    if record.tipo_objetivo == "derecho_via_proyecto":
        return _confirm_ddv_import(db, record, data, user)
    if record.tipo_objetivo in {STRICT_NUCLEUS_TARGET, STRICT_PARCEL_TARGET, "nucleo_agrario", "parcela"}:
        from .gis_reconciliation import finalize
        return finalize(db,record,data,user)
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
