from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


TipoCargaGeoespacial = Literal["franja_derecho_via", "seccion_derecho_via", "nucleo_agrario", "parcela"]


class CargaFeatureResponse(BaseModel):
    id_carga_feature: int
    indice_feature: int
    capa_origen: str | None
    tipo_geometria: str | None
    estado: Literal["valido", "advertencia", "error"]
    errores: list[dict[str, Any]]
    advertencias: list[dict[str, Any]]
    transformaciones: list[dict[str, Any]]
    area_original_m2: Decimal | None
    area_normalizada_m2: Decimal | None
    diferencia_area_relativa: Decimal | None
    seleccionado: bool
    geometria_geojson: dict[str, Any] | None = None


class CargaGeoespacialResponse(BaseModel):
    id_carga: int
    tipo_objetivo: TipoCargaGeoespacial
    tipo_geometria_esperado: Literal["linea", "poligono", "trazo"]
    nombre_original: str
    formato_detectado: Literal["kml", "geojson", "shapefile"]
    tamano_bytes: int
    sha256: str
    fuente: str | None
    crs_original: str
    crs_destino: str
    total_features: int
    features_validos: int
    features_advertencia: int
    features_error: int
    estado: str
    fecha_carga: datetime
    fecha_procesamiento: datetime | None
    fecha_confirmacion: datetime | None
    error_codigo: str | None
    error_detalle: str | None
    features: list[CargaFeatureResponse] = Field(default_factory=list)


class ConfirmarCargaRequest(BaseModel):
    id_carga_feature: int


class CandidatoTramoNucleoResponse(BaseModel):
    id_candidato: int
    id_tramo: int
    id_nucleo: int
    id_franja: int
    id_seccion: int
    nombre_nucleo: str | None = None
    area_interseccion_m2: Decimal
    estado: Literal["pendiente", "aceptado", "rechazado"]
    fecha_deteccion: datetime
    fecha_resolucion: datetime | None = None
    motivo_resolucion: str | None = None
    id_tramo_nucleo: int | None = None
    model_config = ConfigDict(from_attributes=True)


class ConfirmarCandidatoRequest(BaseModel):
    consecutivo: int = Field(ge=1)
    numero_tramo: str | None = Field(default=None, max_length=50)
    observaciones: str | None = None
    es_expropiacion: bool = False
    proyecto_no_afecta_uso_comun: bool | None = None


class RechazarCandidatoRequest(BaseModel):
    motivo: str = Field(min_length=3, max_length=500)
