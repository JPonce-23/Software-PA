from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import date

# ----------------- MAPA Y ENTIDADES BASE ----------------- #
class TramoBase(BaseModel):
    clave_tramo: str
    nombre_tramo: str
    descripcion: Optional[str] = None
    ancho_total_derecho_via_m: Optional[Decimal] = 40.00
    activo: bool = True

class TramoResponse(TramoBase):
    id_tramo: int
    geometria_wkt: Optional[str] = None
    class Config:
        from_attributes = True

class FrenteResponse(BaseModel):
    id_frente: int
    id_tramo: int
    clave_frente: str
    nombre_frente: str
    geometria_wkt: Optional[str] = None
    class Config:
        from_attributes = True

class NucleoAgrarioResponse(BaseModel):
    id_nucleo: int
    nombre_nucleo: str
    tipo_nucleo: str
    comunidad_indigena: bool
    geometria_wkt: Optional[str] = None
    class Config:
        from_attributes = True

# ----------------- DASHBOARD ----------------- #
class DashboardMetrics(BaseModel):
    id_tramo_nucleo: int
    id_tramo: int
    clave_tramo: str
    id_frente: int
    id_nucleo: int
    nombre_nucleo: str
    entidad_federativa: str
    estado_legal: str
    estado_geoespacial: str
    total_superficie_afectada_ha: Decimal
    superficie_liberada_ha: Decimal
    superficie_pendiente_ha: Decimal
    porcentaje_avance_legal: Decimal
    porcentaje_avance_geoespacial: Decimal
    total_convenios_formalizados_ran: int
    class Config:
        from_attributes = True

# ----------------- FLUJO DE LIBERACIÓN ----------------- #
class AfectacionCreate(BaseModel):
    id_nucleo: int
    id_tramo_nucleo: int
    tipo_afectacion: str
    tipo_tenencia: str
    superficie_afectada_ha: Decimal
    num_personas_afectadas: Optional[int] = 0
    origen_registro: str = "captura_sistema"

class AfectacionResponse(AfectacionCreate):
    id_afectacion: int
    geometria_wkt: Optional[str] = None
    class Config:
        from_attributes = True

class AsambleaCreate(BaseModel):
    id_nucleo: int
    id_tramo_nucleo: int
    tipo_asamblea: str
    resultado_anuencia: str = "pendiente"
    fecha_realizada: Optional[date] = None

class AsambleaResponse(AsambleaCreate):
    id_asamblea: int
    class Config:
        from_attributes = True

class ConvenioCreate(BaseModel):
    id_tramo_nucleo: int
    id_afectacion: int
    tipo_afectacion: str
    tipo_convenio: str
    superficie_real_afectada_ha: Optional[Decimal] = None
    superficie_total_ha: Optional[Decimal] = None
    monto_100: Optional[Decimal] = None

class ConvenioResponse(ConvenioCreate):
    id_convenio: int
    fecha_firma: Optional[date] = None
    class Config:
        from_attributes = True
