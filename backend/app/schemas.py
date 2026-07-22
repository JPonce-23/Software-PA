from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal, Any
from decimal import Decimal
from datetime import date, datetime

# ----------------- MIXINS ----------------- #
class AuditableCreate(BaseModel):
    observaciones: Optional[str] = None

class AuditableUpdate(BaseModel):
    observaciones: Optional[str] = None

# ----------------- AUTH Y USUARIOS ----------------- #
class Token(BaseModel):
    access_token: str
    token_type: str
    user: Optional[dict] = None

class TokenData(BaseModel):
    correo: Optional[str] = None

class UsuarioBase(BaseModel):
    nombre: str
    apellido_paterno: str
    apellido_materno: Optional[str] = None
    correo: str
    rol: Literal['admin', 'operador', 'visualizador', 'geografo']

class UsuarioCreate(UsuarioBase):
    contrasena: str

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido_paterno: Optional[str] = None
    apellido_materno: Optional[str] = None
    rol: Optional[Literal['admin', 'operador', 'visualizador', 'geografo']] = None
    # activo: ELIMINADO intencionalmente. La baja de usuarios es EXCLUSIVA del endpoint
    # DELETE /api/usuarios/{id} que exige motivo_baja y registra en bitácora (DA-9).

class UsuarioResponse(UsuarioBase):
    id_usuario: int
    activo: bool
    fecha_alta: datetime
    class Config:
        from_attributes = True

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
    geometria_wkt: Optional[str] = None # WKT para la BD

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
    geometria_wkt: Optional[str] = None

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
    tipo_nucleo: Literal['ejido', 'comunidad']
    comunidad_indigena: bool = False
    residencia: Optional[str] = None
    geometria_wkt: Optional[str] = None

class NucleoAgrarioUpdate(AuditableUpdate):
    nombre_nucleo: Optional[str] = None
    comunidad_indigena: Optional[bool] = None
    residencia: Optional[str] = None
    geometria_wkt: Optional[str] = None

class NucleoAgrarioResponse(BaseModel):
    id_nucleo: int
    nombre_nucleo: str
    tipo_nucleo: Literal['ejido', 'comunidad']
    comunidad_indigena: bool
    geometria_wkt: Optional[str] = None
    class Config:
        from_attributes = True

# ----------------- TRAMO NUCLEO ----------------- #
class TramoNucleoCreate(AuditableCreate):
    id_tramo: int
    id_frente: int
    id_nucleo: int
    consecutivo: int
    numero_tramo: Optional[str] = None
    geometria_wkt: Optional[str] = None  # WKT MULTILINESTRING; opcional en alta
    longitud_m: Optional[Decimal] = None
    es_expropiacion: bool = False
    causa_problema: Optional[str] = None
    proyecto_no_afecta_uso_comun: Optional[bool] = None

class TramoNucleoUpdate(AuditableUpdate):
    numero_tramo: Optional[str] = None
    geometria_wkt: Optional[str] = None
    longitud_m: Optional[Decimal] = None
    es_expropiacion: Optional[bool] = None
    causa_problema: Optional[str] = None
    proyecto_no_afecta_uso_comun: Optional[bool] = None

class TramoNucleoResponse(BaseModel):
    id_tramo_nucleo: int
    id_tramo: int
    id_frente: int
    id_nucleo: int
    consecutivo: int
    numero_tramo: Optional[str] = None
    geometria_wkt: Optional[str] = None
    longitud_m: Optional[Decimal] = None
    es_expropiacion: bool
    causa_problema: Optional[str] = None
    proyecto_no_afecta_uso_comun: Optional[bool] = None
    activo: bool
    observaciones: Optional[str] = None
    class Config:
        from_attributes = True

# ----------------- PARCELA ----------------- #
class ParcelaCreate(AuditableCreate):
    id_nucleo: int
    tipo_parcela: Optional[Literal['individual', 'copropiedad']] = None
    no_parcela_ppt: Optional[str] = None
    certificado_parcelario: Optional[str] = None
    folio_derechos: Optional[str] = None
    constancia_vigencia_fecha: Optional[date] = None
    nombre_titular: Optional[str] = None
    documentacion_disponible: bool = False
    documentacion_faltante: Optional[str] = None

class ParcelaUpdate(AuditableUpdate):
    tipo_parcela: Optional[Literal['individual', 'copropiedad']] = None
    no_parcela_ppt: Optional[str] = None
    certificado_parcelario: Optional[str] = None
    folio_derechos: Optional[str] = None
    constancia_vigencia_fecha: Optional[date] = None
    nombre_titular: Optional[str] = None
    documentacion_disponible: Optional[bool] = None
    documentacion_faltante: Optional[str] = None

class ParcelaResponse(ParcelaCreate):
    id_parcela: int
    activo: bool
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
    id_parcela: Optional[int] = None           # Obligatorio cuando tipo_afectacion='individual'
    tipo_afectacion: Literal['colectivo', 'individual']
    tipo_tenencia: str
    subtipo_tenencia: Optional[str] = None
    destino_superficie: Optional[str] = None   # Aplica a derechos colectivos
    no_parcela_solar: Optional[str] = None
    superficie_afectada_ha: Optional[Decimal] = Field(default=None, ge=0)
    num_personas_afectadas: Optional[int] = Field(default=None, ge=0)
    situacion_juridica: Optional[str] = None
    documentacion_disponible: bool = False
    documentacion_faltante: Optional[str] = None
    origen_registro: Literal['captura_sistema', 'migracion_excel'] = 'captura_sistema'
    geometria_wkt: Optional[str] = None

class AfectacionUpdate(AuditableUpdate):
    geometria_wkt: Optional[str] = None
    tipo_tenencia: Optional[str] = None
    subtipo_tenencia: Optional[str] = None
    destino_superficie: Optional[str] = None
    no_parcela_solar: Optional[str] = None
    superficie_afectada_ha: Optional[Decimal] = Field(default=None, ge=0)
    num_personas_afectadas: Optional[int] = Field(default=None, ge=0)
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
    contexto_proceso: Literal['cop_original', 'obras_complementarias', 'superficie_adicional'] = 'cop_original'
    tipo_asamblea: Literal['informacion', 'anuencia', 'retiro_fondos', 'conciliacion', 'no_verificativo']
    resultado_anuencia: Literal['otorgada', 'negada', 'pendiente', 'no_aplica'] = "pendiente"
    fecha_exp_1a: Optional[date] = None
    fecha_prog_1a: Optional[date] = None
    fecha_exp_2a: Optional[date] = None
    fecha_prog_2a: Optional[date] = None
    fecha_realizada: Optional[date] = None
    estatus_asamblea: Literal['programado', 'pendiente', 'completo'] = 'programado'
    ingreso_ran_fecha: Optional[date] = None
    numero_solicitud_ran: Optional[str] = None
    calificacion_registral_ran: Optional[str] = None
    acta_inscripcion_fecha_ran: Optional[date] = None
    id_padron: Optional[int] = None
    documentacion_disponible: Optional[bool] = False
    documentacion_faltante: Optional[str] = None

class AsambleaUpdate(AuditableUpdate):
    fecha_exp_1a: Optional[date] = None
    fecha_prog_1a: Optional[date] = None
    fecha_exp_2a: Optional[date] = None
    fecha_prog_2a: Optional[date] = None
    fecha_realizada: Optional[date] = None
    resultado_anuencia: Optional[Literal['otorgada', 'negada', 'pendiente', 'no_aplica']] = None
    estatus_asamblea: Optional[Literal['programado', 'pendiente', 'completo']] = None
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
    tipo_afectacion: Literal['colectivo', 'individual']
    tipo_convenio: Optional[Literal['cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias', 'ampliacion', 'ampliacion_remanente']] = None
    fecha_firma: Optional[date] = None
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
    ingreso_ran_fecha: Optional[date] = None
    numero_solicitud_ingreso: Optional[str] = None
    calificacion_registral: Optional[str] = None
    convenio_inscrito_fecha_ran: Optional[date] = None
    documentacion_disponible: Optional[bool] = None
    documentacion_faltante: Optional[str] = None
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
    numero_orv: Optional[str] = None
    inicio_vigencia: Optional[date] = None
    fin_vigencia: Optional[date] = None
    comisariado_presidente: Optional[str] = None
    comisariado_secretario: Optional[str] = None
    comisariado_tesorero: Optional[str] = None
    consejo_vigilancia_presidente: Optional[str] = None
    consejo_vigilancia_secretario1: Optional[str] = None
    consejo_vigilancia_secretario2: Optional[str] = None
    acta_eleccion_inscrita_ran: Optional[bool] = None
    documentacion_disponible: Optional[bool] = None
    documentacion_faltante: Optional[str] = None

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
    tipo_actividad: Literal['sensibilizacion', 'caminamiento']
    contexto_proceso: Literal['cop_original', 'obras_complementarias', 'superficie_adicional'] = 'cop_original'
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
    hay_conflictos: Optional[bool] = None
    no_oficio_fifonafe_a_dgaopr: Optional[str] = None
    no_oficio_dgaopr_a_repr: Optional[str] = None
    no_oficio_rpta_repr_a_dgaopr: Optional[str] = None
    no_oficio_rpta_dgaopr_a_fifonafe: Optional[str] = None
    fecha_oficio_fifonafe_a_dgaopr: Optional[date] = None
    fecha_oficio_dgaopr_a_repr: Optional[date] = None
    fecha_oficio_rpta_repr_a_dgaopr: Optional[date] = None
    fecha_oficio_rpta_dgaopr_a_fifonafe: Optional[date] = None
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
class AlertaCreate(BaseModel):
    tipo: Literal['vencimiento_orv', 'evento_proximo', 'documento_faltante']
    prioridad: Literal['alta', 'media', 'baja']
    titulo: str
    descripcion: Optional[str] = None
    entidad_relacionada_id: int
    entidad_relacionada_tipo: Literal['nucleo_agrario', 'afectacion', 'convenio', 'orv']
    fecha_evento: Optional[date] = None

class AlertaUpdate(BaseModel):
    esta_activa: Optional[bool] = None
    # activo: ELIMINADO intencionalmente. La baja de alertas es EXCLUSIVA del endpoint
    # DELETE /api/alertas/{id} que exige motivo_baja y registra en bitácora (DA-9).

class AlertaResponse(AlertaCreate):
    id_alerta: int
    esta_activa: bool
    fecha_creacion: datetime
    class Config:
        from_attributes = True

# ==================== CATÁLOGOS ==================== #
class EntidadFederativaResponse(BaseModel):
    id_entidad: int
    clave_inegi: str
    nombre: str
    activo: bool
    class Config:
        from_attributes = True

class MunicipioResponse(BaseModel):
    id_municipio: int
    id_entidad: int
    clave_inegi: str
    nombre: str
    activo: bool
    class Config:
        from_attributes = True

# ==================== BITÁCORA ==================== #
class BitacoraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_bitacora: int
    id_usuario: int
    id_nucleo: Optional[int] = None
    id_tramo_nucleo: Optional[int] = None
    entidad_tipo: str
    entidad_id: Optional[int] = None
    accion: str
    detalle_cambio: Optional[str] = None
    valor_anterior: Optional[Any] = None
    valor_nuevo: Optional[Any] = None
    fecha_hora: datetime
    ip_origen: Optional[str] = None
    user_agent: Optional[str] = None

# ==================== USUARIO FRENTE ==================== #
class UsuarioFrenteCreate(BaseModel):
    id_usuario: int

class UsuarioFrenteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_usuario: int
    id_frente: int
    fecha_asignacion: datetime
    activo: bool
