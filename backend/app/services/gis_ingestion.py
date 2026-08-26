"""Lectura segura y uniforme de fuentes vectoriales mediante GDAL/OGR."""

from __future__ import annotations

import json
import os
import codecs
import select
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


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


@dataclass(frozen=True)
class DatasetInfo:
    driver: str
    format: str
    layers: tuple[LayerInfo, ...]

    @property
    def total_features(self) -> int:
        return sum(layer.feature_count for layer in self.layers)

    @property
    def columns(self) -> list[str]:
        return sorted({column for layer in self.layers for column in layer.columns})

    @property
    def crs_description(self) -> str:
        values = list(dict.fromkeys(layer.crs for layer in self.layers))
        return " | ".join(values)


def _gdal_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
            "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": "",
            "CPL_CURL_VERBOSE": "NO",
            "OGR_GEOJSON_MAX_OBJ_SIZE": str(
                int(os.getenv("IMPORT_MAX_FILE_SIZE_MB", "100")) * 1024 * 1024
            ),
        }
    )
    return env


def _run_json(command: list[str]) -> dict:
    timeout = int(os.getenv("IMPORT_GDAL_TIMEOUT_SECONDS", "300"))
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            timeout=timeout,
            env=_gdal_environment(),
            text=True,
        )
    except FileNotFoundError as exc:
        raise IngestionError(
            "GDAL_NO_DISPONIBLE",
            "El servicio geoespacial no esta disponible en el backend.",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise IngestionError(
            "GDAL_TIMEOUT",
            "El archivo excedio el tiempo permitido de inspeccion.",
        ) from exc
    if result.returncode != 0:
        raise IngestionError(
            "ARCHIVO_NO_PROCESABLE",
            "GDAL/OGR no pudo abrir el contenido como un archivo vectorial permitido.",
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise IngestionError(
            "METADATOS_INVALIDOS",
            "GDAL/OGR no devolvio metadatos validos para el archivo.",
        ) from exc


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

    layers: list[LayerInfo] = []
    for raw_layer in metadata.get("layers") or []:
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
                feature_count=max(0, int(raw_layer.get("featureCount") or 0)),
                columns=columns,
                crs=crs,
                is_wgs84=is_wgs84,
            )
        )
    if not layers:
        raise IngestionError("SIN_CAPAS", "El archivo no contiene capas vectoriales procesables.")
    if sum(layer.feature_count for layer in layers) <= 0:
        raise IngestionError("SIN_FEATURES", "El archivo no contiene features.")
    return DatasetInfo(driver=driver, format=detected_format, layers=tuple(layers))


def iter_features(
    path: Path,
    dataset: DatasetInfo,
    limit_per_layer: int | None = None,
) -> Iterator[tuple[str, dict]]:
    """Convierte cada capa a GeoJSONSeq en stdout y entrega un feature a la vez."""
    timeout = int(os.getenv("IMPORT_GDAL_TIMEOUT_SECONDS", "300"))
    for layer in dataset.layers:
        command = [
            "ogr2ogr",
            "-f",
            "GeoJSONSeq",
            "/vsistdout/",
            str(path),
            layer.name,
        ]
        if limit_per_layer is not None:
            command.extend(["-limit", str(max(1, limit_per_layer))])
        command.extend([
            "-t_srs",
            "EPSG:4326",
            "-lco",
            "RS=NO",
        ])
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=_gdal_environment(),
            )
        except FileNotFoundError as exc:
            raise IngestionError(
                "GDAL_NO_DISPONIBLE",
                "El servicio geoespacial no esta disponible en el backend.",
            ) from exc
        assert process.stdout is not None
        stdout = process.stdout
        deadline = time.monotonic() + timeout
        decoder = codecs.getincrementaldecoder("utf-8")()
        pending = ""

        def consume_line(line: str) -> dict | None:
            payload = line.lstrip("\x1e").strip()
            if not payload:
                return None
            try:
                return json.loads(payload)
            except json.JSONDecodeError as exc:
                raise IngestionError(
                    "FEATURE_OGR_INVALIDO",
                    f'GDAL produjo un feature invalido en la capa "{layer.name}".',
                ) from exc

        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout)
                readable, _, _ = select.select([stdout], [], [], remaining)
                if not readable:
                    raise subprocess.TimeoutExpired(command, timeout)
                chunk = os.read(stdout.fileno(), 64 * 1024)
                if not chunk:
                    break
                pending += decoder.decode(chunk)
                while "\n" in pending:
                    line, pending = pending.split("\n", 1)
                    feature = consume_line(line)
                    if feature is not None:
                        yield layer.name, feature
            pending += decoder.decode(b"", final=True)
            feature = consume_line(pending)
            if feature is not None:
                yield layer.name, feature
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            raise IngestionError(
                "GDAL_TIMEOUT",
                f'La capa "{layer.name}" excedio el tiempo permitido de conversion.',
            ) from exc
        finally:
            if process.poll() is None:
                process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            stdout.close()
        if process.returncode != 0:
            raise IngestionError(
                "CONVERSION_OGR_FALLIDA",
                f'No fue posible normalizar la capa "{layer.name}".',
            )
