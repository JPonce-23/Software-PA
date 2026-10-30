"""Lectura segura y uniforme de fuentes vectoriales mediante GDAL/OGR."""

from __future__ import annotations

import json
import os
import select
import subprocess
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .gis_limits import load_limits


class IngestionError(RuntimeError):
    def __init__(self, code: str, public_detail: str):
        super().__init__(public_detail)
        self.code = code
        self.public_detail = public_detail


@dataclass(frozen=True)
class LayerInfo:
    name: str
    feature_count: int
    columns: tuple[str, ...]
    crs: str
    is_wgs84: bool
    fid_column: str = ""
    geometry_column: str = ""
    geometry_type: str = ""
    crs_wkt: str = ""
    srid: int | None = None


@dataclass(frozen=True)
class DatasetInfo:
    driver: str
    format: str
    layers: tuple[LayerInfo, ...]

    @property
    def total_features(self) -> int:
        return sum(max(0, layer.feature_count) for layer in self.layers)

    @property
    def counts_known(self) -> bool:
        return all(layer.feature_count >= 0 for layer in self.layers)

    @property
    def columns(self) -> list[str]:
        return sorted({column for layer in self.layers for column in layer.columns})

    @property
    def crs_description(self) -> str:
        values = list(dict.fromkeys(layer.crs for layer in self.layers))
        return " | ".join(values)


def _gdal_environment() -> dict[str, str]:
    """Linux GDAL child environment: fixed policy plus local data directories only.

    Never forward API credentials, loader/plugin settings, proxies or user config.
    This reduces ambient configuration; it is not a network/filesystem sandbox.
    """
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "HOME": "/nonexistent",
        "XDG_CONFIG_HOME": "/nonexistent",
        "XDG_CACHE_HOME": "/nonexistent",
        "TMPDIR": "/tmp",
        "CPL_TMPDIR": "/tmp",
        "GDAL_CONFIG_FILE": "/dev/null",
        "PROJ_NETWORK": "OFF",
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": "",
        "CPL_CURL_VERBOSE": "NO",
        "OGR_GEOJSON_MAX_OBJ_SIZE": str(load_limits().geojson_feature_mb),
    }
    # Resource directories may differ between packaged GDAL/PROJ builds.
    # PROJ_DATA (>=9.1) and its older PROJ_LIB fallback support search lists.
    for name in ("GDAL_DATA", "PROJ_DATA", "PROJ_LIB"):
        value = os.getenv(name)
        if not value:
            continue
        paths = [value] if name == "GDAL_DATA" else value.split(os.pathsep)
        if (any(ord(char) < 32 for char in value)
                or any(not Path(part).is_absolute() or part.startswith("/vsi") for part in paths)):
            raise IngestionError("GDAL_CONFIG_INVALIDA", f"{name} requiere directorios locales absolutos.")
        env[name] = value
    return env


def _process_chunks(command: list[str], max_bytes: int) -> Iterator[bytes]:
    """Bound stdout before accumulation; always reap the direct GDAL child."""
    timeout = int(os.getenv("IMPORT_GDAL_TIMEOUT_SECONDS", "300"))
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=_gdal_environment(), shell=False)
    except FileNotFoundError as exc:
        raise IngestionError("GDAL_NO_DISPONIBLE", "El servicio geoespacial no esta disponible.") from exc
    stdout = process.stdout
    assert stdout is not None
    deadline = time.monotonic() + timeout
    total = 0
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([stdout], [], [], remaining)[0]:
                raise subprocess.TimeoutExpired(command, timeout)
            chunk = os.read(stdout.fileno(), min(64 * 1024, max_bytes - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise IngestionError("LIMITE_SALIDA_GDAL", "La salida GIS excede el presupuesto permitido.")
            yield chunk
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(command, timeout)
        process.wait(timeout=remaining)
        if process.returncode != 0:
            raise IngestionError("CONVERSION_OGR_FALLIDA", "GDAL/OGR no pudo procesar el archivo.")
    except subprocess.TimeoutExpired as exc:
        raise IngestionError("GDAL_TIMEOUT", "El archivo excedio el tiempo permitido de procesamiento.") from exc
    finally:
        try:
            if process.poll() is None:
                process.kill()
                process.wait()
        finally:
            stdout.close()


def _run_json(command: list[str]) -> dict:
    output = bytearray()
    with closing(_process_chunks(command, load_limits().inspection_bytes)) as chunks:
        for chunk in chunks:
            output.extend(chunk)
    try:
        metadata = json.loads(output)
        if not isinstance(metadata, dict):
            raise ValueError("metadata object required")
        return metadata
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise IngestionError("METADATOS_INVALIDOS", "GDAL/OGR no devolvio metadatos validos.") from exc


def _authority_from_coordinate_system(coordinate_system: dict | None) -> tuple[str, bool]:
    if not coordinate_system:
        return "", False
    wkt = str(coordinate_system.get("wkt") or "").strip()
    projjson = coordinate_system.get("projjson") or {}
    identifier = projjson.get("id") or {}
    authority = str(identifier.get("authority") or "").upper()
    code = str(identifier.get("code") or "")
    canonical = f"{authority}:{code}" if authority and code else ""
    description = canonical or wkt
    if canonical:
        is_wgs84 = canonical in {"EPSG:4326", "OGC:CRS84"}
    else:
        normalized_wkt = wkt.upper()
        is_wgs84 = (
            normalized_wkt.startswith(("GEOGCRS", "GEOGCS"))
            and (
                'ID["EPSG",4326]' in normalized_wkt
                or 'AUTHORITY["EPSG","4326"]' in normalized_wkt
            )
        )
    return description, is_wgs84


def get_spatial_layers(metadata: dict) -> list[dict]:
    """OGR expone también tablas QGIS; sólo cuentan campos geométricos."""
    return [layer for layer in metadata.get("layers", []) if any(
        str(field.get("type", "Unknown")).lower() not in {"none", "", "null"}
        for field in layer.get("geometryFields", [])
    )]


def _feature_count(value) -> int:
    if value is None:
        return -1
    try:
        count = int(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise IngestionError("METADATOS_INVALIDOS", "Conteo GDAL invalido.") from exc
    return max(-1, count)


def inspect_dataset(path: Path) -> DatasetInfo:
    metadata = _run_json(["ogrinfo", "-ro", "-so", "-al", "-json", str(path)])
    driver = str(metadata.get("driverShortName") or metadata.get("driverLongName") or "")
    driver_normalized = driver.lower()
    if "kml" in driver_normalized:
        detected_format = "kml"
    elif "geojson" in driver_normalized:
        detected_format = "geojson"
    elif "esri shapefile" in driver_normalized or driver_normalized == "shapefile":
        detected_format = "shp"
    elif "gpkg" in driver_normalized or "geopackage" in driver_normalized:
        detected_format = "gpkg"
    else:
        raise IngestionError(
            "FORMATO_NO_SOPORTADO",
            "El contenido detectado no es KML, GeoJSON, GeoPackage ni Shapefile.",
        )

    limits = load_limits()
    spatial_layers = get_spatial_layers(metadata)
    if len(spatial_layers) > limits.layers:
        raise IngestionError("LIMITE_CAPAS", "El archivo excede el limite de capas GIS.")
    layers: list[LayerInfo] = []
    for raw_layer in spatial_layers:
        name = str(raw_layer.get("name") or "").strip()
        if not name:
            continue
        geometry_fields = raw_layer.get("geometryFields") or []
        coordinate_system = raw_layer.get("coordinateSystem")
        if geometry_fields and not coordinate_system:
            coordinate_system = geometry_fields[0].get("coordinateSystem")
        crs, is_wgs84 = _authority_from_coordinate_system(coordinate_system)
        if not crs:
            raise IngestionError(
                "CRS_DESCONOCIDO",
                f'CRS no identificado en la capa "{name}". Se requiere intervencion antes de continuar.',
            )
        columns = tuple(
            str(field.get("name"))
            for field in (raw_layer.get("fields") or [])
            if field.get("name")
        )
        layers.append(
            LayerInfo(
                name=name,
                feature_count=_feature_count(raw_layer.get("featureCount")),
                columns=columns,
                crs=crs,
                is_wgs84=is_wgs84,
                fid_column=str(raw_layer.get("fidColumnName") or ""),
                geometry_column=str(geometry_fields[0].get("name") or ""),
                geometry_type=str(geometry_fields[0].get("type") or ""),
                crs_wkt=str((coordinate_system or {}).get("wkt") or ""),
                srid=int(crs.split(":")[1]) if crs.startswith("EPSG:") and crs.split(":")[1].isdigit() else None,
            )
        )
    if not layers:
        raise IngestionError("SIN_CAPAS", "El archivo no contiene capas vectoriales procesables.")
    if sum(max(0, layer.feature_count) for layer in layers) > limits.features:
        raise IngestionError("LIMITE_FEATURES", "El archivo excede el limite de features GIS.")
    if all(layer.feature_count == 0 for layer in layers):
        raise IngestionError("SIN_FEATURES", "El archivo no contiene features.")
    return DatasetInfo(driver=driver, format=detected_format, layers=tuple(layers))


def iter_features(
    path: Path,
    dataset: DatasetInfo,
    limit_per_layer: int | None = None,
    *,
    preserve_source_geometry: bool = False,
) -> Iterator[tuple[str, dict]]:
    """Convierte cada capa a GeoJSONSeq en stdout y entrega un feature a la vez."""
    limits = load_limits()
    if len(dataset.layers) > limits.layers:
        raise IngestionError("LIMITE_CAPAS", "El archivo excede el limite de capas GIS.")
    if dataset.total_features > limits.features:
        raise IngestionError("LIMITE_FEATURES", "El archivo excede el limite de features GIS.")
    if limit_per_layer is not None and limit_per_layer <= 0:
        raise IngestionError("LIMITE_FEATURES", "El limite por capa debe ser positivo.")
    observed = output_bytes = 0
    for layer in dataset.layers:
        command = [
            "ogr2ogr",
            "-f",
            "GeoJSONSeq",
            "/vsistdout/",
            str(path),
        ]
        if preserve_source_geometry and dataset.format == "gpkg":
            # WKB is lossless, including source Z/M, and survives GeoJSONSeq's
            # mandatory 4326 conversion. Identifiers originate in OGR metadata.
            quoted_layer = layer.name.replace('"', '""')
            quoted_geom = layer.geometry_column.replace('"', '""')
            fid = layer.fid_column.replace('"', '""')
            select_fid = f', "{fid}" AS "__pa_source_fid"' if fid else ''
            command.extend(["-dialect", "SQLite", "-sql",
                f'SELECT *{select_fid}, hex(ST_AsBinary("{quoted_geom}")) AS "__pa_source_wkb" FROM "{quoted_layer}"'])
        else:
            # argv prevents shell commands, but a leading '-' could be an OGR option.
            if layer.name.startswith("-"):
                raise IngestionError("CAPA_NO_SEGURA", "El nombre de capa no puede comenzar con un guion.")
            command.append(layer.name)
        command.extend([
            "-t_srs",
            "EPSG:4326",
            "-lco",
            "RS=NO",
            "-lco",
            "COORDINATE_PRECISION=15",
        ])
        pending = bytearray()
        layer_count = 0

        def consume_line(line: bytes) -> dict | None:
            payload = line.lstrip(b"\x1e").strip()
            if not payload:
                return None
            try:
                item = json.loads(payload)
                if not isinstance(item, dict) or item.get("type") != "Feature":
                    raise ValueError("feature object required")
                return item
            except (ValueError, UnicodeError, RecursionError) as exc:
                raise IngestionError("FEATURE_OGR_INVALIDO", "GDAL produjo un feature invalido.") from exc

        # Bytes avoid splitting UTF-8 code points; decode only complete records.
        with closing(_process_chunks(command, limits.output_bytes - output_bytes)) as chunks:
            for chunk in chunks:
                output_bytes += len(chunk)
                parts = chunk.split(b"\n")
                for index, part in enumerate(parts):
                    if len(pending) + len(part) > limits.record_bytes:
                        raise IngestionError("LIMITE_REGISTRO", "Una feature GIS excede el limite de bytes por registro.")
                    pending.extend(part)
                    if index == len(parts) - 1:
                        continue
                    item = consume_line(pending)
                    pending.clear()
                    if item is not None:
                        observed += 1
                        layer_count += 1
                        if observed > limits.features or (limit_per_layer is not None and layer_count > limit_per_layer):
                            raise IngestionError("LIMITE_FEATURES", "La lectura excede el limite de features GIS.")
                        yield layer.name, item
            item = consume_line(pending)
            if item is not None:
                observed += 1
                layer_count += 1
                if observed > limits.features or (limit_per_layer is not None and layer_count > limit_per_layer):
                    raise IngestionError("LIMITE_FEATURES", "La lectura excede el limite de features GIS.")
                yield layer.name, item
        if layer.feature_count >= 0 and layer_count != layer.feature_count:
            raise IngestionError("CONTEO_FEATURES_INCONSISTENTE", "El conteo observado no coincide con GDAL.")
    if observed == 0:
        raise IngestionError("SIN_FEATURES", "El archivo no contiene features.")
