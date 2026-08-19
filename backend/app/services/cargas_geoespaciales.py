"""Staging comun de archivos geoespaciales para capturas operativas."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePath
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from .. import models
from .common import set_audit_context
from .gis_ingestion import IngestionError, inspect_dataset, iter_features


TARGETS = {
    "franja_derecho_via": "trazo",
    "seccion_derecho_via": "poligono",
    "nucleo_agrario": "poligono",
    "parcela": "poligono",
}
VALID_STATES = {"valido", "advertencia"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _root() -> Path:
    root = Path(os.getenv("UPLOAD_ROOT", "uploads")) / "cargas_geoespaciales"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def _safe_name(filename: str | None) -> str:
    if not filename or "\x00" in filename:
        raise HTTPException(status_code=400, detail="El archivo debe tener un nombre valido.")
    normalized = filename.replace("\\", "/")
    if PurePath(normalized).name != normalized:
        raise HTTPException(status_code=400, detail="El nombre del archivo no es seguro.")
    name = PurePath(normalized).name.strip()
    if not name or len(name) > 255:
        raise HTTPException(status_code=400, detail="El nombre del archivo no es valido.")
    return name


def _declared_format(name: str) -> str:
    suffix = Path(name).suffix.casefold()
    if suffix == ".kml":
        return "kml"
    if suffix in {".geojson", ".json"}:
        return "geojson"
    if suffix == ".zip":
        return "shapefile"
    raise HTTPException(status_code=415, detail="Formatos admitidos: KML, GeoJSON y Shapefile (.zip).")


def _safe_zip_dataset(archive_path: Path, destination: Path) -> Path:
    max_bytes = int(os.getenv("IMPORT_MAX_FILE_SIZE_MB", "100")) * 1024 * 1024
    try:
        with zipfile.ZipFile(archive_path) as archive:
            entries = [item for item in archive.infolist() if not item.is_dir()]
            if not entries or len(entries) > 32:
                raise HTTPException(status_code=422, detail="El ZIP de Shapefile tiene una estructura no permitida.")
            total = sum(item.file_size for item in entries)
            if total > max_bytes:
                raise HTTPException(status_code=413, detail="El Shapefile descomprimido excede el limite permitido.")
            for item in entries:
                relative = PurePath(item.filename.replace("\\", "/"))
                if relative.is_absolute() or ".." in relative.parts:
                    raise HTTPException(status_code=422, detail="El ZIP contiene rutas no permitidas.")
                target = destination.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=422, detail="El archivo no es un ZIP de Shapefile valido.") from exc

    shapefiles = sorted(destination.rglob("*.shp")) + sorted(destination.rglob("*.SHP"))
    if len(shapefiles) != 1:
        raise HTTPException(status_code=422, detail="El ZIP debe contener exactamente un archivo .shp.")
    shapefile = shapefiles[0]
    suffixes = {path.suffix.casefold() for path in shapefile.parent.glob(f"{shapefile.stem}.*")}
    missing = {".shp", ".shx", ".dbf", ".prj"} - suffixes
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"El Shapefile requiere los archivos {', '.join(sorted(missing))}.",
        )
    return shapefile


def _message(code: str, field: str, detail: str) -> dict[str, str]:
    return {"codigo": code, "campo": field, "detalle": detail}


def _area_tolerance() -> float | None:
    raw = os.getenv("IMPORT_MAKE_VALID_MAX_AREA_DELTA", "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError("IMPORT_MAKE_VALID_MAX_AREA_DELTA debe estar entre 0 y 1.") from exc
    if not 0 <= value <= 1:
        raise RuntimeError("IMPORT_MAKE_VALID_MAX_AREA_DELTA debe estar entre 0 y 1.")
    return value


def _normalize_geometry(db: Session, geometry: Any, expected: str) -> dict[str, Any]:
    if not isinstance(geometry, dict):
        return {"estado": "error", "errores": [_message("GEOMETRIA_AUSENTE", "geometria", "El feature no contiene una geometria.")]}
    if expected == "trazo":
        source_type = str(geometry.get("type") or "")
        if source_type in {"LineString", "MultiLineString"}:
            expected = "linea"
        elif source_type in {"Polygon", "MultiPolygon"}:
            expected = "poligono"
        else:
            return {
                "estado": "error",
                "errores": [_message(
                    "TIPO_GEOMETRIA",
                    "geometria",
                    "El trazo debe contener líneas o polígonos.",
                )],
            }
    dimension = 2 if expected == "linea" else 3
    target_name = "MULTILINESTRING" if expected == "linea" else "MULTIPOLYGON"
    try:
        row = db.execute(
            text(
                """
                WITH raw AS (
                    SELECT ST_SetSRID(ST_Force2D(ST_GeomFromGeoJSON(:geometry)), 4326) AS geom
                ), prepared AS (
                    SELECT geom, ST_GeometryType(geom) AS original_type,
                           ST_IsValid(geom) AS original_valid,
                           ST_NDims(ST_GeomFromGeoJSON(:geometry)) > 2 AS had_z
                    FROM raw
                ), normalized AS (
                    SELECT original_type, original_valid, had_z,
                           ST_Multi(ST_CollectionExtract(
                               CASE WHEN original_valid THEN geom ELSE ST_MakeValid(geom) END,
                               :dimension
                           )) AS geom,
                           CASE WHEN :dimension = 3
                                THEN ST_Area(ST_Transform(geom, 6933))
                           END AS area_original_m2
                    FROM prepared
                )
                SELECT ST_AsText(geom) AS wkt,
                       original_type,
                       ST_GeometryType(geom) AS geometry_type,
                       ST_IsValid(geom) AS is_valid,
                       ST_IsEmpty(geom) AS is_empty,
                       had_z,
                       original_valid,
                       area_original_m2,
                       CASE WHEN :dimension = 3 THEN ST_Area(ST_Transform(geom, 6933)) END AS area_normalizada_m2
                FROM normalized
                """
            ),
            {"geometry": json.dumps(geometry), "dimension": dimension},
        ).mappings().one()
    except DBAPIError:
        return {"estado": "error", "errores": [_message("GEOMETRIA_INVALIDA", "geometria", "La geometria no puede interpretarse de forma segura.")]}

    accepted_source_types = (
        {"ST_LineString", "ST_MultiLineString", "ST_GeometryCollection"}
        if expected == "linea"
        else {"ST_Polygon", "ST_MultiPolygon", "ST_GeometryCollection"}
    )
    if row["is_empty"] and row["original_type"] not in accepted_source_types:
        return {"estado": "error", "errores": [_message("TIPO_GEOMETRIA", "geometria", f"Se requiere una geometria {target_name}.")]}
    if row["is_empty"] or not row["is_valid"]:
        return {"estado": "error", "errores": [_message("GEOMETRIA_INVALIDA", "geometria", "La geometria esta vacia o no es valida.")]}
    expected_type = "ST_MultiLineString" if expected == "linea" else "ST_MultiPolygon"
    if row["geometry_type"] != expected_type:
        return {"estado": "error", "errores": [_message("TIPO_GEOMETRIA", "geometria", f"Se requiere una geometria {target_name}.")]}

    transformations: list[dict[str, str]] = [{"codigo": "FORCE_2D", "detalle": "Geometria normalizada a dos dimensiones."}]
    warnings: list[dict[str, str]] = []
    if row["had_z"]:
        transformations.append({"codigo": "DIMENSION_3D_ELIMINADA", "detalle": "Se removio la dimension Z durante la normalizacion."})
    original_area = row["area_original_m2"]
    normalized_area = row["area_normalizada_m2"]
    delta = None
    if not row["original_valid"]:
        transformations.append({"codigo": "MAKE_VALID", "detalle": "Se aplico ST_MakeValid antes de normalizar."})
        if original_area and normalized_area is not None and original_area > 0:
            delta = abs(normalized_area - original_area) / original_area
        tolerance = _area_tolerance()
        if expected == "poligono" and (tolerance is None or delta is None or delta > tolerance):
            if tolerance is None:
                detail = (
                    "La geometría requirió reparación"
                    + (f"; el área cambiaría {delta:.6%}" if delta is not None else "")
                    + ". No existe una tolerancia de reparación autorizada."
                )
            elif delta is None:
                detail = "La geometría requirió reparación, pero no fue posible medir de forma segura el cambio de área."
            else:
                detail = (
                    f"La geometría requirió reparación y el área cambiaría {delta:.6%}, "
                    f"superando la tolerancia autorizada de {tolerance:.6%}."
                )
            return {
                "estado": "error",
                "errores": [_message("REPARACION_GEOMETRICA_BLOQUEADA", "geometria", detail)],
                "transformaciones": transformations,
                "area_original_m2": original_area,
                "area_normalizada_m2": normalized_area,
                "diferencia_area_relativa": delta,
            }
        warnings.append(_message("GEOMETRIA_REPARADA", "geometria", "La geometria fue reparada dentro de la tolerancia autorizada."))
    return {
        "estado": "advertencia" if warnings else "valido",
        "wkt": row["wkt"],
        "tipo_geometria": row["geometry_type"].removeprefix("ST_"),
        "advertencias": warnings,
        "transformaciones": transformations,
        "area_original_m2": original_area,
        "area_normalizada_m2": normalized_area,
        "diferencia_area_relativa": delta,
    }


async def stage_upload(
    db: Session,
    upload: UploadFile,
    target: str,
    user_id: int,
    source: str | None = None,
) -> models.CargaGeoespacial:
    if target not in TARGETS:
        raise HTTPException(status_code=422, detail="El objetivo geoespacial no es valido.")
    original_name = _safe_name(upload.filename)
    declared = _declared_format(original_name)
    if source is not None and len(source.strip()) > 200:
        raise HTTPException(status_code=422, detail="La fuente no puede exceder 200 caracteres.")
    max_bytes = int(os.getenv("IMPORT_MAX_FILE_SIZE_MB", "100")) * 1024 * 1024
    stored_name = f"{uuid.uuid4().hex}{Path(original_name).suffix.casefold()}"
    stored_path = _root() / stored_name
    digest = hashlib.sha256()
    size = 0
    try:
        with stored_path.open("xb") as output:
            os.chmod(stored_path, 0o600)
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(status_code=413, detail="El archivo excede el limite configurado.")
                digest.update(chunk)
                output.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="El archivo esta vacio.")
        with tempfile.TemporaryDirectory(dir=_root(), prefix="validar-") as temp_dir:
            dataset_path = _safe_zip_dataset(stored_path, Path(temp_dir)) if declared == "shapefile" else stored_path
            dataset = inspect_dataset(dataset_path)
            if dataset.format != declared:
                raise HTTPException(status_code=415, detail="La extension no coincide con el formato detectado por GDAL/OGR.")
            record = models.CargaGeoespacial(
                tipo_objetivo=target,
                tipo_geometria_esperado=TARGETS[target],
                nombre_original=original_name,
                nombre_almacenado=stored_name,
                formato_detectado=dataset.format,
                tamano_bytes=size,
                sha256=digest.hexdigest(),
                fuente=source.strip() if source and source.strip() else None,
                crs_original=dataset.crs_description,
                total_features=dataset.total_features,
                estado="prevalidando",
                id_usuario_carga=user_id,
            )
            set_audit_context(db, user_id)
            db.add(record)
            db.flush()
            processed = 0
            for layer, feature in iter_features(dataset_path, dataset):
                result = _normalize_geometry(db, feature.get("geometry"), TARGETS[target])
                attributes = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
                staged = models.CargaGeoespacialFeature(
                    id_carga=record.id_carga,
                    indice_feature=processed,
                    capa_origen=layer,
                    atributos_originales=attributes,
                    estado=result["estado"],
                    errores=result.get("errores", []),
                    advertencias=result.get("advertencias", []),
                    transformaciones=result.get("transformaciones", []),
                    tipo_geometria=result.get("tipo_geometria"),
                    area_original_m2=result.get("area_original_m2"),
                    area_normalizada_m2=result.get("area_normalizada_m2"),
                    diferencia_area_relativa=result.get("diferencia_area_relativa"),
                )
                if result.get("wkt"):
                    staged.geometria_normalizada = result["wkt"]
                db.add(staged)
                processed += 1
            if processed != dataset.total_features:
                raise HTTPException(status_code=422, detail="El conteo de features procesados no coincide con el archivo original.")
            db.flush()
            record.features_validos = db.query(models.CargaGeoespacialFeature).filter_by(id_carga=record.id_carga, estado="valido").count()
            record.features_advertencia = db.query(models.CargaGeoespacialFeature).filter_by(id_carga=record.id_carga, estado="advertencia").count()
            record.features_error = db.query(models.CargaGeoespacialFeature).filter_by(id_carga=record.id_carga, estado="error").count()
            record.estado = "listo_revision"
            record.fecha_procesamiento = utcnow()
            db.commit()
            db.refresh(record)
            return record
    except IngestionError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=exc.public_detail) from exc
    except Exception:
        db.rollback()
        raise
    finally:
        if stored_path.exists() and not db.query(models.CargaGeoespacial).filter_by(nombre_almacenado=stored_name).first():
            stored_path.unlink(missing_ok=True)


def get_carga_or_404(db: Session, carga_id: int, user: models.Usuario) -> models.CargaGeoespacial:
    record = db.get(models.CargaGeoespacial, carga_id)
    if not record or (user.rol != "admin" and record.id_usuario_carga != user.id_usuario):
        raise HTTPException(status_code=404, detail="Carga geoespacial no encontrada.")
    return record


def confirm_feature(db: Session, record: models.CargaGeoespacial, feature_id: int, user_id: int) -> models.CargaGeoespacialFeature:
    locked = db.query(models.CargaGeoespacial).filter_by(id_carga=record.id_carga).with_for_update().one()
    if locked.estado != "listo_revision":
        raise HTTPException(status_code=409, detail="La carga no esta disponible para confirmacion.")
    feature = db.query(models.CargaGeoespacialFeature).filter_by(
        id_carga_feature=feature_id, id_carga=locked.id_carga
    ).with_for_update().one_or_none()
    if not feature or feature.estado not in VALID_STATES or feature.geometria_normalizada is None:
        raise HTTPException(status_code=422, detail="Seleccione una feature geometrica valida.")
    db.query(models.CargaGeoespacialFeature).filter_by(id_carga=locked.id_carga).update(
        {models.CargaGeoespacialFeature.seleccionado: False}, synchronize_session=False
    )
    feature.seleccionado = True
    locked.estado = "confirmado"
    locked.fecha_confirmacion = utcnow()
    locked.id_usuario_confirmacion = user_id
    set_audit_context(db, user_id)
    db.commit()
    db.refresh(feature)
    return feature


def _same_layer_filter(query, layer_name: str | None):
    if layer_name is None:
        return query.filter(models.CargaGeoespacialFeature.capa_origen.is_(None))
    return query.filter(models.CargaGeoespacialFeature.capa_origen == layer_name)


def confirmed_wkt(db: Session, feature_id: int, target: str) -> str:
    feature = db.query(models.CargaGeoespacialFeature).join(models.CargaGeoespacial).filter(
        models.CargaGeoespacialFeature.id_carga_feature == feature_id,
        models.CargaGeoespacialFeature.seleccionado.is_(True),
        models.CargaGeoespacialFeature.id_registro_operativo.is_(None),
        models.CargaGeoespacial.estado == "confirmado",
        models.CargaGeoespacial.tipo_objetivo == target,
    ).with_for_update().one_or_none()
    if not feature:
        consumed = db.query(models.CargaGeoespacialFeature.id_registro_operativo).join(
            models.CargaGeoespacial
        ).filter(
            models.CargaGeoespacialFeature.id_carga_feature == feature_id,
            models.CargaGeoespacialFeature.seleccionado.is_(True),
            models.CargaGeoespacial.estado == "confirmado",
            models.CargaGeoespacial.tipo_objetivo == target,
            models.CargaGeoespacialFeature.id_registro_operativo.is_not(None),
        ).first()
        if consumed:
            raise HTTPException(status_code=409, detail="La geometría confirmada ya fue utilizada en un registro operativo.")
        raise HTTPException(status_code=422, detail="La geometria confirmada no corresponde a esta operacion.")
    return db.query(func.ST_AsText(models.CargaGeoespacialFeature.geometria_normalizada)).filter(
        models.CargaGeoespacialFeature.id_carga_feature == feature_id
    ).scalar()


def confirmed_trazo_geometry(
    db: Session,
    feature_id: int,
) -> tuple[str, str, list[dict[str, str]], str]:
    """Obtiene el eje o polígono confirmado sin inferir una franja por ancho."""
    feature = db.query(models.CargaGeoespacialFeature).join(models.CargaGeoespacial).filter(
        models.CargaGeoespacialFeature.id_carga_feature == feature_id,
        models.CargaGeoespacialFeature.seleccionado.is_(True),
        models.CargaGeoespacialFeature.id_registro_operativo.is_(None),
        models.CargaGeoespacial.estado == "confirmado",
        models.CargaGeoespacial.tipo_objetivo == "franja_derecho_via",
    ).with_for_update().one_or_none()
    if feature is None:
        raise HTTPException(status_code=422, detail="La geometría confirmada no corresponde al trazo ferroviario.")

    record = db.get(models.CargaGeoespacial, feature.id_carga)
    if record is None:
        raise HTTPException(status_code=422, detail="No se encontró el archivo de origen del trazo.")
    source = record.fuente or f"Archivo geoespacial: {record.nombre_original}"
    layer_features = _same_layer_filter(
        db.query(models.CargaGeoespacialFeature), feature.capa_origen
    ).filter(models.CargaGeoespacialFeature.id_carga == feature.id_carga)
    if layer_features.filter(models.CargaGeoespacialFeature.estado == "error").first():
        raise HTTPException(
            status_code=422,
            detail="La capa seleccionada contiene geometrías con error y no puede registrarse como trazo.",
        )

    valid_features = layer_features.filter(
        models.CargaGeoespacialFeature.estado.in_(VALID_STATES),
        models.CargaGeoespacialFeature.geometria_normalizada.is_not(None),
    )
    geometry_types = {
        row[0]
        for row in valid_features.with_entities(
            func.ST_GeometryType(models.CargaGeoespacialFeature.geometria_normalizada)
        ).all()
    }
    if len(geometry_types) != 1 or not geometry_types <= {"ST_MultiLineString", "ST_MultiPolygon"}:
        raise HTTPException(status_code=422, detail="La capa seleccionada mezcla tipos de geometría incompatibles para un trazo.")
    geometry_type = geometry_types.pop()
    component_count = valid_features.count()
    if component_count == 0:
        raise HTTPException(status_code=422, detail="La capa seleccionada no contiene geometrías válidas.")

    if geometry_type == "ST_MultiLineString":
        operation = "ST_Multi(ST_LineMerge(ST_UnaryUnion(ST_Collect(geometria_normalizada))))"
        expected_type = "ST_MultiLineString"
        kind = "linea"
        code = "UNION_SEGMENTOS_TRAZO"
        detail = f"Se unieron {component_count} segmentos lineales de la capa seleccionada."
    else:
        operation = "ST_Multi(ST_CollectionExtract(ST_UnaryUnion(ST_Collect(geometria_normalizada)), 3))"
        expected_type = "ST_MultiPolygon"
        kind = "poligono"
        code = "UNION_COMPONENTES_TRAZO"
        detail = f"Se unieron {component_count} polígonos de la capa seleccionada."

    layer_clause = "capa_origen IS NULL" if feature.capa_origen is None else "capa_origen = :layer_name"
    params = {"id_carga": feature.id_carga}
    if feature.capa_origen is not None:
        params["layer_name"] = feature.capa_origen
    row = db.execute(text(f"""
        SELECT ST_AsText({operation}) AS wkt,
               ST_IsValid({operation}) AS valid,
               ST_IsEmpty({operation}) AS empty,
               ST_GeometryType({operation}) AS geometry_type
          FROM carga_geoespacial_feature
         WHERE id_carga = :id_carga
           AND estado IN ('valido', 'advertencia')
           AND {layer_clause}
    """), params).mappings().one()
    if not row["wkt"] or not row["valid"] or row["empty"] or row["geometry_type"] != expected_type:
        raise HTTPException(status_code=422, detail="No fue posible consolidar una geometría válida desde la capa seleccionada.")
    return row["wkt"], kind, [{"codigo": code, "detalle": detail}], source


def consume_confirmed_feature(
    db: Session,
    feature_id: int,
    target: str,
    operational_id: int,
    user_id: int,
    transformations: list[dict[str, str]] | None = None,
) -> None:
    feature = db.query(models.CargaGeoespacialFeature).join(models.CargaGeoespacial).filter(
        models.CargaGeoespacialFeature.id_carga_feature == feature_id,
        models.CargaGeoespacialFeature.seleccionado.is_(True),
        models.CargaGeoespacialFeature.id_registro_operativo.is_(None),
        models.CargaGeoespacial.estado == "confirmado",
        models.CargaGeoespacial.tipo_objetivo == target,
    ).with_for_update().one_or_none()
    if not feature:
        raise HTTPException(status_code=409, detail="La geometría confirmada ya fue utilizada o no corresponde a esta operación.")
    selected_features = [feature]
    if target == "franja_derecho_via":
        grouped = _same_layer_filter(
            db.query(models.CargaGeoespacialFeature), feature.capa_origen
        ).filter(
            models.CargaGeoespacialFeature.id_carga == feature.id_carga,
            models.CargaGeoespacialFeature.estado.in_(VALID_STATES),
            models.CargaGeoespacialFeature.id_registro_operativo.is_(None),
        ).with_for_update().all()
        if grouped:
            selected_features = grouped
    for selected_feature in selected_features:
        selected_feature.id_registro_operativo = operational_id
        selected_feature.fecha_consumo = utcnow()
        selected_feature.id_usuario_consumo = user_id
        if transformations:
            selected_feature.transformaciones = [*(selected_feature.transformaciones or []), *transformations]


def detect_candidates(db: Session, tramo_id: int, user_id: int) -> int:
    section = db.query(models.SeccionDerechoVia).join(models.FranjaDerechoVia).filter(
        models.SeccionDerechoVia.id_tramo == tramo_id,
        models.SeccionDerechoVia.activo.is_(True),
        models.FranjaDerechoVia.activo.is_(True),
    ).with_for_update().one_or_none()
    if not section:
        raise HTTPException(status_code=409, detail="El tramo requiere una sección activa del derecho de vía antes de detectar candidatos.")
    candidates = db.execute(text("""
        SELECT n.id_nucleo,
               ST_Area(ST_CollectionExtract(ST_Intersection(n.geometria_poligono, s.geometria_poligono), 3)::geography) AS area_m2
          FROM nucleo_agrario n
          JOIN seccion_derecho_via s ON s.id_seccion = :id_seccion
         WHERE n.activo = TRUE
           AND n.geometria_poligono IS NOT NULL
           AND n.geometria_poligono && s.geometria_poligono
           AND ST_Intersects(n.geometria_poligono, s.geometria_poligono)
           AND ST_Area(ST_CollectionExtract(ST_Intersection(n.geometria_poligono, s.geometria_poligono), 3)::geography) > 0
           AND NOT EXISTS (
               SELECT 1 FROM tramo_nucleo tn
                WHERE tn.id_tramo = :tramo_id AND tn.id_nucleo = n.id_nucleo AND tn.activo = TRUE
           )
    """), {"id_seccion": section.id_seccion, "tramo_id": tramo_id}).mappings().all()
    created = 0
    for item in candidates:
        existing = db.query(models.CandidatoTramoNucleo).filter_by(id_seccion=section.id_seccion, id_nucleo=item["id_nucleo"]).with_for_update().one_or_none()
        if existing is None:
            db.add(models.CandidatoTramoNucleo(
                id_tramo=tramo_id,
                id_nucleo=item["id_nucleo"],
                id_franja=section.id_franja,
                id_seccion=section.id_seccion,
                area_interseccion_m2=item["area_m2"],
                id_usuario_deteccion=user_id,
            ))
            created += 1
        elif existing.estado == "pendiente":
            existing.area_interseccion_m2 = item["area_m2"]
            existing.fecha_deteccion = utcnow()
    set_audit_context(db, user_id)
    db.commit()
    return created


def confirm_candidate(
    db: Session,
    candidate_id: int,
    consecutivo: int,
    user_id: int,
    numero_tramo: str | None = None,
    observaciones: str | None = None,
    es_expropiacion: bool = False,
    proyecto_no_afecta_uso_comun: bool | None = None,
) -> models.TramoNucleo:
    candidate = db.query(models.CandidatoTramoNucleo).filter_by(id_candidato=candidate_id).with_for_update().one_or_none()
    if not candidate or candidate.estado != "pendiente":
        raise HTTPException(status_code=409, detail="El candidato ya fue resuelto o no existe.")
    section = db.query(models.SeccionDerechoVia).join(models.FranjaDerechoVia).filter(
        models.SeccionDerechoVia.id_seccion == candidate.id_seccion,
        models.SeccionDerechoVia.activo.is_(True),
        models.FranjaDerechoVia.activo.is_(True),
    ).with_for_update().one_or_none()
    if not section:
        raise HTTPException(status_code=409, detail="La sección del candidato ya no está activa.")
    duplicate = db.query(models.TramoNucleo.id_tramo_nucleo).filter_by(
        id_tramo=candidate.id_tramo, id_nucleo=candidate.id_nucleo, activo=True
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="El tramo ya tiene un expediente activo para este nucleo.")
    relation = models.TramoNucleo(
        id_tramo=candidate.id_tramo,
        id_nucleo=candidate.id_nucleo,
        consecutivo=consecutivo,
        numero_tramo=numero_tramo,
        geometria_segmento=None,
        longitud_m=None,
        es_expropiacion=es_expropiacion,
        proyecto_no_afecta_uso_comun=proyecto_no_afecta_uso_comun,
        observaciones=observaciones,
        activo=True,
    )
    set_audit_context(db, user_id)
    db.add(relation)
    db.flush()
    candidate.estado = "aceptado"
    candidate.fecha_resolucion = utcnow()
    candidate.id_usuario_resolucion = user_id
    candidate.id_tramo_nucleo = relation.id_tramo_nucleo
    db.commit()
    db.refresh(relation)
    return relation


def reject_candidate(db: Session, candidate_id: int, reason: str, user_id: int) -> None:
    candidate = db.query(models.CandidatoTramoNucleo).filter_by(id_candidato=candidate_id).with_for_update().one_or_none()
    if not candidate or candidate.estado != "pendiente":
        raise HTTPException(status_code=409, detail="El candidato ya fue resuelto o no existe.")
    candidate.estado = "rechazado"
    candidate.fecha_resolucion = utcnow()
    candidate.id_usuario_resolucion = user_id
    candidate.motivo_resolucion = reason.strip()
    set_audit_context(db, user_id)
    db.commit()
