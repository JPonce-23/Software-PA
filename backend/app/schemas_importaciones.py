from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


EstadoFeature = Literal[
    "valido", "advertencia", "error", "importado",
    "pendiente_revision", "descartado",
]


class PerfilMapeoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    fuente: str = Field(min_length=1, max_length=200)
    mapeo: dict[str, str]
    opciones: dict[str, Any] = Field(default_factory=dict)

    @field_validator("nombre", "fuente")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El valor es obligatorio")
        return value


class PerfilMapeoResponse(PerfilMapeoCreate):
    id_perfil: int
    activo: bool
    fecha_creacion: datetime
    model_config = ConfigDict(from_attributes=True)


class MapeoImportacionRequest(BaseModel):
    mapeo: dict[str, str]
    opciones: dict[str, Any] = Field(default_factory=dict)
    id_perfil: int | None = None
    procedencia_archivo: Literal["original", "conversion"] | None = None
    id_importacion_origen: int | None = None
    guardar_perfil: PerfilMapeoCreate | None = None


class FeatureRevisionRequest(BaseModel):
    nombre_nucleo: str | None = Field(default=None, max_length=300)
    tipo_nucleo: str | None = Field(default=None, max_length=30)
    id_entidad: int | None = None
    id_municipio: int | None = None
    aceptar_advertencias: bool | None = None
    descartar: bool = False


class ConfirmacionImportacionRequest(BaseModel):
    aceptar_advertencias: bool = False


class AliasTerritorialCreate(BaseModel):
    id_entidad: int
    alias_nombre: str | None = Field(default=None, max_length=200)
    alias_clave: str | None = Field(default=None, max_length=20)
    id_municipio_destino: int
    fuente: str = Field(min_length=1, max_length=300)
    fecha_vigencia_inicio: date | None = None
    fecha_vigencia_fin: date | None = None


class ImportacionArchivoResponse(BaseModel):
    id_importacion: int
    nombre_original: str
    formato_detectado: str
    tamano_bytes: int
    sha256: str
    fuente: str
    crs_original: str | None
    crs_destino: str
    columnas_detectadas: list[str]
    mapeo: dict[str, str]
    opciones_mapeo: dict[str, Any]
    id_perfil: int | None
    procedencia_archivo: str | None
    id_importacion_origen: int | None
    estado: str
    total_features: int
    features_procesados: int
    validos: int
    advertencias: int
    errores: int
    importados: int
    descartados: int
    tolerancia_area_relativa: Decimal | None
    fecha_carga: datetime
    fecha_procesamiento_inicio: datetime | None
    fecha_procesamiento_fin: datetime | None
    fecha_confirmacion: datetime | None
    fecha_completado: datetime | None
    error_codigo: str | None
    error_detalle: str | None
    fecha_baja: datetime | None = None
    id_usuario_baja: int | None = None
    motivo_baja: str | None = None
    model_config = ConfigDict(from_attributes=True)


class ImportacionArchivoPageResponse(BaseModel):
    total: int
    items: list[ImportacionArchivoResponse]


class ImportacionFeatureResponse(BaseModel):
    id_importacion_feature: int
    indice_feature: int
    capa_origen: str | None
    id_externo: str | None
    atributos_normalizados: dict[str, Any]
    id_entidad_resuelta: int | None
    id_municipio_resuelto: int | None
    estado: EstadoFeature
    errores: list[dict[str, Any]]
    advertencias: list[dict[str, Any]]
    transformaciones: list[dict[str, Any]]
    area_original_m2: Decimal | None
    area_normalizada_m2: Decimal | None
    diferencia_area_relativa: Decimal | None
    advertencias_aceptadas: bool
    id_nucleo_operativo: int | None
    model_config = ConfigDict(from_attributes=True)


class FeaturePageResponse(BaseModel):
    total: int
    items: list[ImportacionFeatureResponse]


class MuestrasColumnasResponse(BaseModel):
    muestras: dict[str, list[str]]


class OperacionImportacionResponse(BaseModel):
    id_importacion: int
    estado: str
    detalle: str
