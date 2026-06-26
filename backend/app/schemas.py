from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime

# ----------------- MIXINS ----------------- #
class AuditableCreate(BaseModel):
    observaciones: Optional[str] = None

class AuditableUpdate(BaseModel):
    activo: Optional[bool] = None
    motivo_baja: Optional[str] = None
    motivo_reactivacion: Optional[str] = None
    observaciones: Optional[str] = None

# ----------------- MAPA Y ENTIDADES BASE ----------------- #
class TramoBase(BaseModel):
    clave_tramo: str
    nombre_tramo: str
    descripcion: Optional[str] = None
    ancho_total_derecho_via_m: Optional[Decimal] = 40.00
    activo: bool = True
    fecha_registro: Optional[date] = None

class TramoCreate(AuditableCreate):
    clave_tramo: str
    nombre_tramo: str
    descripcion: Optional[str] = None
    ancho_total_derecho_via_m: Optional[Decimal] = 40.00
    fecha_registro: Optional[date] = None
    geometria_wkt: str # WKT para la BD

class TramoUpdate(AuditableUpdate):
    nombre_tramo: Optional[str] = None
    descripcion: Optional[str] = None
    ancho_total_derecho_via_m: Optional[Decimal] = None
    geometria_wkt: Optional[str] = None

class TramoResponse(TramoBase):
    id_tramo: int
    geometria_wkt: Optional[str] = None
    class Config:
        from_attributes = True

class FrenteCreate(AuditableCreate):
    id_tramo: int
    clave_frente: str
    nombre_frente: str
    descripcion: Optional[str] = None
    fecha_registro: Optional[date] = None
    geometria_wkt: str

class FrenteUpdate(AuditableUpdate):
    nombre_frente: Optional[str] = None
    descripcion: Optional[str] = None
    geometria_wkt: Optional[str] = None

class FrenteResponse(BaseModel):
    id_frente: int
    id_tramo: int
    clave_frente: str
    nombre_frente: str
    geometria_wkt: Optional[str] = None
    class Config:
        from_attributes = True

class NucleoAgrarioCreate(AuditableCreate):
    id_municipio: int
    nombre_nucleo: str
    tipo_nucleo: str
    comunidad_indigena: bool = False
    residencia: Optional[str] = None
    geometria_wkt: str

class NucleoAgrarioUpdate(AuditableUpdate):
    nombre_nucleo: Optional[str] = None
    comunidad_indigena: Optional[bool] = None
    residencia: Optional[str] = None
    geometria_wkt: Optional[str] = None

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
class AfectacionCreate(AuditableCreate):
    id_nucleo: int
    id_tramo_nucleo: int
    tipo_afectacion: str
    tipo_tenencia: str
    superficie_afectada_ha: Decimal
    num_personas_afectadas: Optional[int] = 0
    origen_registro: str = "captura_sistema"

class AfectacionUpdate(AuditableUpdate):
    superficie_afectada_ha: Optional[Decimal] = None
    num_personas_afectadas: Optional[int] = None
    situacion_juridica: Optional[str] = None
    documentacion_disponible: Optional[bool] = None
    documentacion_faltante: Optional[str] = None

class AfectacionResponse(AfectacionCreate):
    id_afectacion: int
    geometria_wkt: Optional[str] = None
    activo: bool
    class Config:
        from_attributes = True

class AsambleaCreate(AuditableCreate):
    id_nucleo: int
    id_tramo_nucleo: int
    tipo_asamblea: str
    resultado_anuencia: str = "pendiente"
    fecha_realizada: Optional[date] = None
    id_padron: Optional[int] = None
    documentacion_disponible: Optional[bool] = False
    documentacion_faltante: Optional[str] = None

class AsambleaUpdate(AuditableUpdate):
    resultado_anuencia: Optional[str] = None
    estatus_asamblea: Optional[str] = None
    ingreso_ran_fecha: Optional[date] = None
    numero_solicitud_ran: Optional[str] = None
    calificacion_registral_ran: Optional[str] = None
    acta_inscripcion_fecha_ran: Optional[date] = None
    documentacion_disponible: Optional[bool] = None
    documentacion_faltante: Optional[str] = None
    id_padron: Optional[int] = None

class AsambleaResponse(AsambleaCreate):
    id_asamblea: int
    activo: bool
    class Config:
        from_attributes = True

class ConvenioCreate(AuditableCreate):
    id_tramo_nucleo: int
    id_afectacion: int
    tipo_afectacion: str
    tipo_convenio: str
    superficie_real_afectada_ha: Optional[Decimal] = None
    superficie_total_ha: Optional[Decimal] = None
    superficie_adicional_ha: Optional[Decimal] = None
    superficie_ampliacion_ha: Optional[Decimal] = None
    monto_100: Optional[Decimal] = None
    monto_90: Optional[Decimal] = None
    monto_bdt: Optional[Decimal] = None
    id_convenio_padre: Optional[int] = None
    id_asamblea_autorizacion: Optional[int] = None

class ConvenioUpdate(AuditableUpdate):
    fecha_firma: Optional[date] = None
    ingreso_ran_fecha: Optional[date] = None
    numero_solicitud_ingreso: Optional[str] = None
    calificacion_registral: Optional[str] = None
    convenio_inscrito_fecha_ran: Optional[date] = None
    documentacion_disponible: Optional[bool] = None
    documentacion_faltante: Optional[str] = None

class ConvenioResponse(ConvenioCreate):
    id_convenio: int
    fecha_firma: Optional[date] = None
    activo: bool
    class Config:
        from_attributes = True

class OrvCreate(AuditableCreate):
    id_nucleo: int
    inicio_vigencia: date
    fin_vigencia: date
    comisariado_presidente: Optional[str] = None
    comisariado_secretario: Optional[str] = None
    comisariado_tesorero: Optional[str] = None
    consejo_vigilancia_presidente: Optional[str] = None
    consejo_vigilancia_secretario1: Optional[str] = None
    consejo_vigilancia_secretario2: Optional[str] = None
    acta_eleccion_inscrita_ran: Optional[bool] = False

class OrvUpdate(AuditableUpdate):
    inicio_vigencia: Optional[date] = None
    fin_vigencia: Optional[date] = None
    comisariado_presidente: Optional[str] = None
    acta_eleccion_inscrita_ran: Optional[bool] = None

class OrvResponse(OrvCreate):
    id_orv: int
    activo: bool
    class Config:
        from_attributes = True

class PadronHistorialCreate(AuditableCreate):
    id_nucleo: int
    fecha_padron: date
    numero_ejidatarios_comuneros: int

class PadronHistorialUpdate(AuditableUpdate):
    fecha_padron: Optional[date] = None
    numero_ejidatarios_comuneros: Optional[int] = None

class PadronHistorialResponse(PadronHistorialCreate):
    id_padron: int
    activo: bool
    class Config:
        from_attributes = True

class ActividadCampoCreate(AuditableCreate):
    id_tramo_nucleo: int
    tipo_actividad: str
    fecha_programada: Optional[date] = None
    fecha_realizada: Optional[date] = None

class ActividadCampoUpdate(AuditableUpdate):
    fecha_programada: Optional[date] = None
    fecha_realizada: Optional[date] = None
    resultado: Optional[str] = None

class ActividadCampoResponse(ActividadCampoCreate):
    id_actividad: int
    activo: bool
    class Config:
        from_attributes = True

class TramiteFifonafeCreate(AuditableCreate):
    id_tramo_nucleo: int
    id_convenio: Optional[int] = None
    id_afectacion: Optional[int] = None
    tipo_afectacion: str
    tipo_tramite: str
    estatus: str = 'pendiente'

class TramiteFifonafeUpdate(AuditableUpdate):
    estatus: Optional[str] = None
    hay_conflictos: Optional[bool] = None
    no_oficio_fifonafe_a_dgaopr: Optional[str] = None
    no_oficio_dgaopr_a_repr: Optional[str] = None
    no_oficio_rpta_repr_a_dgaopr: Optional[str] = None
    no_oficio_rpta_dgaopr_a_fifonafe: Optional[str] = None
    fecha_oficio_fifonafe_a_dgaopr: Optional[date] = None
    fecha_oficio_dgaopr_a_repr: Optional[date] = None
    fecha_oficio_rpta_repr_a_dgaopr: Optional[date] = None
    fecha_oficio_rpta_dgaopr_a_fifonafe: Optional[date] = None

class TramiteFifonafeResponse(TramiteFifonafeCreate):
    id_tramite_fifonafe: int
    activo: bool
    class Config:
        from_attributes = True

class DocumentacionSoporteCreate(AuditableCreate):
    entidad_relacionada_id: int
    entidad_relacionada_tipo: str
    tipo_documento: str
    categoria: str
    es_critico: bool = False
    url_archivo: Optional[str] = None

class DocumentacionSoporteUpdate(AuditableUpdate):
    categoria: Optional[str] = None
    url_archivo: Optional[str] = None

class DocumentacionSoporteResponse(DocumentacionSoporteCreate):
    id_documento: int
    activo: bool
    class Config:
        from_attributes = True

# --- Para Alertas ---
class AlertaCreate(AuditableCreate):
    tipo: str
    prioridad: str
    titulo: str
    descripcion: Optional[str] = None
    entidad_relacionada_id: int
    entidad_relacionada_tipo: str
    fecha_evento: Optional[date] = None

class AlertaUpdate(AuditableUpdate):
    esta_activa: Optional[bool] = None

class AlertaResponse(AlertaCreate):
    id_alerta: int
    esta_activa: bool
    fecha_creacion: datetime
    class Config:
        from_attributes = True
