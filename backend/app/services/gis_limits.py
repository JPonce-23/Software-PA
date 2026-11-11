"""Finite per-import budgets. Values are policy ceilings, not host capacity claims."""
import os
from dataclasses import dataclass


def positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} debe ser un entero positivo") from exc
    if value <= 0:
        raise ValueError(f"{name} debe ser un entero positivo")
    return value


@dataclass(frozen=True)
class GisLimits:
    geojson_feature_mb: int
    record_bytes: int
    output_bytes: int
    inspection_bytes: int
    layers: int
    features: int
    zip_entries: int
    zip_member_bytes: int
    zip_total_bytes: int


def load_limits() -> GisLimits:
    return GisLimits(
        geojson_feature_mb=positive_int('IMPORT_GEOJSON_MAX_FEATURE_MB', 16),
        record_bytes=positive_int('IMPORT_MAX_RECORD_BYTES', 64 * 1024 * 1024),
        output_bytes=positive_int('IMPORT_MAX_OUTPUT_BYTES', 512 * 1024 * 1024),
        inspection_bytes=positive_int('IMPORT_MAX_INSPECTION_BYTES', 8 * 1024 * 1024),
        layers=positive_int('IMPORT_MAX_LAYERS', 16),
        features=positive_int('IMPORT_MAX_FEATURES', 100_000),
        zip_entries=positive_int('IMPORT_ZIP_MAX_ENTRIES', 2048),
        zip_member_bytes=positive_int('IMPORT_ZIP_MAX_MEMBER_BYTES', 256 * 1024 * 1024),
        zip_total_bytes=positive_int('IMPORT_MAX_UNCOMPRESSED_MB', 500) * 1024 * 1024,
    )
