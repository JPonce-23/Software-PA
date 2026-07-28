from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
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
    model_config = ConfigDict(from_attributes=True)

# ----------------- PROYECTO ----------------- #
class ProyectoBase(BaseModel):
    clave_proyecto: str
    nombre_proyecto: str
    descripcion: Optional[str] = None
    activo: bool = True
    fecha_registro: date

class ProyectoCreate(AuditableCreate):
    clave_proyecto: str
    nombre_proyecto: str
    descripcion: Optional[str] = None

class ProyectoUpdate(AuditableUpdate):
    nombre_proyecto: Optional[str] = None
    descripcion: Optional[str] = None

class ProyectoResponse(ProyectoBase):
    id_proyecto: int
    model_config = ConfigDict(from_attributes=True)

# ----------------- MAPA Y ENTIDADES BASE ----------------- #
class TramoBase(BaseModel):
    clave_tramo: str
    nombre_tramo: str
    descripcion: Optional[str] = None
    ancho_total_derecho_via_m: Optional[Decimal] = 40.00
    activo: bool = True
    fecha_registro: date

class TramoCreate(AuditableCreate):
    id_proyecto: int
    clave_tramo: str
    nombre_tramo: str
    descripcion: Optional[str] = None
    ancho_total_derecho_via_m: Optional[Decimal] = 40.00
    geometria_wkt: Optional[str] = None

class TramoUpdate(AuditableUpdate):
    nombre_tramo: Optional[str] = None
    descripcion: Optional[str] = None
    ancho_total_derecho_via_m: Optional[Decimal] = None
    geometria_wkt: Optional[str] = None

class TramoResponse(TramoBase):
    id_tramo: int
    id_proyecto: int
    geometria_wkt: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

# ----------------- TRAMO NUCLEO ----------------- #
class TramoNucleoCreate(AuditableCreate):
    id_tramo: int
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
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

# ----------------- DASHBOARD ----------------- #
class DashboardMetrics(BaseModel):
    id_tramo_nucleo: int
    id_tramo: int
    clave_tramo: str
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
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

class ConvenioCreate(AuditableCreate):
    id_tramo_nucleo: int
    id_afectacion: int
    tipo_afectacion: Literal['colectivo', 'individual']
    tipo_convenio: Literal['cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias', 'ampliacion', 'ampliacion_remanente']
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
    superficie_real_afectada_ha: Optional[Decimal] = None
    superficie_total_ha: Optional[Decimal] = None
    superficie_adicional_ha: Optional[Decimal] = None
    superficie_ampliacion_ha: Optional[Decimal] = None
    monto_100: Optional[Decimal] = None
    monto_90: Optional[Decimal] = None
    monto_bdt: Optional[Decimal] = None

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
    model_config = ConfigDict(from_attributes=True)

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

    @model_validator(mode='after')
    def validar_vigencia(self):
        if self.fin_vigencia < self.inicio_vigencia:
            raise ValueError('fin_vigencia no puede ser anterior a inicio_vigencia')
        return self

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
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

class TramiteFifonafeCreate(AuditableCreate):
    id_tramo_nucleo: int
    id_convenio: Optional[int] = None
    id_afectacion: Optional[int] = None
    tipo_afectacion: Literal['colectivo', 'individual']
    tipo_tramite: Literal['indemnizacion', 'informe_no_conflictos']
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
    model_config = ConfigDict(from_attributes=True)

class DocumentacionSoporteCreate(AuditableCreate):
    entidad_relacionada_id: int
    entidad_relacionada_tipo: str
    tipo_documento: str
    categoria: str
    es_critico: bool = False

class DocumentacionSoporteUpdate(AuditableUpdate):
    categoria: Optional[str] = None

class DocumentacionSoporteResponse(DocumentacionSoporteCreate):
    id_documento: int
    url_archivo: Optional[str] = None
    activo: bool
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

# ==================== ADAPTACIONES FASE 2 ==================== #

CalidadAgraria = Literal[
    'ejidatario', 'comunero', 'avecindado', 'posesionario',
    'representante', 'otro'
]
CargoOrv = Literal[
    'comisariado_presidente', 'comisariado_secretario',
    'comisariado_tesorero', 'consejo_vigilancia_presidente',
    'consejo_vigilancia_secretario1', 'consejo_vigilancia_secretario2'
]


class PersonaCreate(AuditableCreate):
    curp: Optional[str] = None
    rfc: Optional[str] = None
    nombre: str = Field(min_length=1, max_length=300)
    apellido_paterno: Optional[str] = Field(default=None, max_length=200)
    apellido_materno: Optional[str] = Field(default=None, max_length=200)
    telefono: Optional[str] = Field(default=None, max_length=20)
    correo_electronico: Optional[str] = Field(default=None, max_length=320)

    @field_validator(
        'curp', 'rfc', 'apellido_paterno', 'apellido_materno',
        'telefono', 'correo_electronico', mode='before'
    )
    @classmethod
    def normalizar_opcionales(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator('curp', 'rfc')
    @classmethod
    def normalizar_identificadores(cls, value):
        return value.upper() if value else None

    @field_validator('nombre')
    @classmethod
    def nombre_no_vacio(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('El nombre no puede estar vacío')
        return value


class PersonaUpdate(BaseModel):
    curp: Optional[str] = None
    rfc: Optional[str] = None
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=300)
    apellido_paterno: Optional[str] = Field(default=None, max_length=200)
    apellido_materno: Optional[str] = Field(default=None, max_length=200)
    telefono: Optional[str] = Field(default=None, max_length=20)
    correo_electronico: Optional[str] = Field(default=None, max_length=320)
    observaciones: Optional[str] = None

    @field_validator(
        'curp', 'rfc', 'apellido_paterno', 'apellido_materno',
        'telefono', 'correo_electronico', mode='before'
    )
    @classmethod
    def normalizar_texto(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator('curp', 'rfc')
    @classmethod
    def normalizar_identificadores(cls, value):
        return value.upper() if value else None

    @field_validator('nombre', mode='before')
    @classmethod
    def nombre_no_nulo(cls, value):
        if value is None or not isinstance(value, str) or not value.strip():
            raise ValueError('El nombre no puede ser nulo ni vacío')
        return value.strip()


class PersonaResponse(PersonaCreate):
    id_persona: int
    datos_identidad_incompletos: bool
    origen_registro: Literal['captura_sistema', 'migracion_legacy']
    activo: bool
    model_config = ConfigDict(from_attributes=True)


class PersonaNucleoCreate(BaseModel):
    id_nucleo: int
    calidad_agraria: Optional[CalidadAgraria] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    observaciones: Optional[str] = None

    @model_validator(mode='after')
    def validar_fechas(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError('fecha_fin no puede ser anterior a fecha_inicio')
        return self


class PersonaNucleoResponse(PersonaNucleoCreate):
    id_persona_nucleo: int
    id_persona: int
    activo: bool
    model_config = ConfigDict(from_attributes=True)


class OrvIntegranteCreate(BaseModel):
    id_persona: int
    cargo: CargoOrv
    calidad_agraria: Optional[CalidadAgraria] = 'representante'
    observaciones: Optional[str] = None


class OrvIntegranteResponse(BaseModel):
    id_orv_integrante: int
    id_orv: int
    id_nucleo: int
    id_persona: int
    cargo: CargoOrv
    activo: bool
    persona: PersonaResponse
    model_config = ConfigDict(from_attributes=True)


class ParcelaTitularCreate(BaseModel):
    id_persona: int
    tipo_derecho: Literal['titular', 'cotitular', 'posesionario', 'otro'] = 'titular'
    porcentaje_participacion: Optional[Decimal] = Field(
        default=None, gt=0, le=100, max_digits=7, decimal_places=4
    )
    calidad_agraria: Optional[CalidadAgraria] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    observaciones: Optional[str] = None

    @model_validator(mode='after')
    def validar_fechas(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError('fecha_fin no puede ser anterior a fecha_inicio')
        return self


class ParcelaTitularResponse(ParcelaTitularCreate):
    id_parcela_titular: int
    id_parcela: int
    id_nucleo: int
    activo: bool
    persona: PersonaResponse
    model_config = ConfigDict(from_attributes=True)


class ParcelaConTitularCreate(BaseModel):
    parcela: ParcelaCreate
    titular: ParcelaTitularCreate


class OrvConIntegrantesCreate(BaseModel):
    orv: OrvCreate
    integrantes: List[OrvIntegranteCreate] = Field(min_length=1, max_length=6)

    @model_validator(mode='after')
    def validar_cargos_unicos(self):
        cargos = [integrante.cargo for integrante in self.integrantes]
        if len(cargos) != len(set(cargos)):
            raise ValueError('No se puede repetir un cargo en el mismo ORV')
        return self


class MinutaCreate(AuditableCreate):
    id_tramo_nucleo: int
    id_actividad: Optional[int] = None
    fecha_reunion: date
    lugar: Optional[str] = Field(default=None, max_length=300)
    asunto: str = Field(min_length=1, max_length=300)
    resumen: Optional[str] = None
    folio: Optional[str] = Field(default=None, max_length=100)

    @field_validator('asunto')
    @classmethod
    def asunto_no_vacio(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('El asunto no puede estar vacío')
        return value


class MinutaUpdate(AuditableUpdate):
    id_actividad: Optional[int] = None
    fecha_reunion: Optional[date] = None
    lugar: Optional[str] = Field(default=None, max_length=300)
    asunto: Optional[str] = Field(default=None, min_length=1, max_length=300)
    resumen: Optional[str] = None
    folio: Optional[str] = Field(default=None, max_length=100)

    @field_validator('asunto')
    @classmethod
    def asunto_no_vacio(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError('El asunto no puede estar vacío')
        return value


class MinutaResponse(MinutaCreate):
    id_minuta: int
    activo: bool
    model_config = ConfigDict(from_attributes=True)


class AcuerdoCreate(AuditableCreate):
    descripcion: str = Field(min_length=1)
    fecha_limite: Optional[date] = None
    fecha_cumplimiento: Optional[date] = None
    estatus: Literal['pendiente', 'cumplido', 'cancelado', 'vencido'] = 'pendiente'
    prioridad: Literal['alta', 'media', 'baja'] = 'media'
    id_persona_responsable: Optional[int] = None
    id_usuario_responsable: Optional[int] = None
    responsable_externo: Optional[str] = Field(default=None, max_length=300)

    @field_validator('descripcion')
    @classmethod
    def descripcion_no_vacia(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('La descripción no puede estar vacía')
        return value

    @field_validator('responsable_externo', mode='before')
    @classmethod
    def normalizar_responsable_externo(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @model_validator(mode='after')
    def validar_responsable_y_cumplimiento(self):
        responsables = [
            self.id_persona_responsable is not None,
            self.id_usuario_responsable is not None,
            bool(self.responsable_externo and self.responsable_externo.strip()),
        ]
        if sum(responsables) != 1:
            raise ValueError('Debe indicar exactamente un responsable')
        if (self.estatus == 'cumplido') != (self.fecha_cumplimiento is not None):
            raise ValueError('Un acuerdo cumplido requiere fecha_cumplimiento')
        return self


class AcuerdoUpdate(BaseModel):
    descripcion: Optional[str] = Field(default=None, min_length=1)
    fecha_limite: Optional[date] = None
    fecha_cumplimiento: Optional[date] = None
    estatus: Optional[Literal['pendiente', 'cumplido', 'cancelado', 'vencido']] = None
    prioridad: Optional[Literal['alta', 'media', 'baja']] = None
    id_persona_responsable: Optional[int] = None
    id_usuario_responsable: Optional[int] = None
    responsable_externo: Optional[str] = Field(default=None, max_length=300)
    observaciones: Optional[str] = None

    @field_validator('descripcion')
    @classmethod
    def descripcion_no_vacia(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError('La descripción no puede estar vacía')
        return value

    @field_validator('responsable_externo', mode='before')
    @classmethod
    def normalizar_responsable_externo(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value


class AcuerdoResponse(AcuerdoCreate):
    id_acuerdo: int
    id_minuta: int
    activo: bool
    model_config = ConfigDict(from_attributes=True)


class DocumentoVersionResponse(BaseModel):
    id_documento_version: int
    id_documento: int
    numero_version: int
    hash_sha256: str
    tamano_bytes: int
    nombre_archivo_original: str
    tipo_mime: Optional[str] = None
    fecha_carga: datetime
    activo: bool
    model_config = ConfigDict(from_attributes=True)


class PagoIndemnizacionCreate(AuditableCreate):
    id_tramite_fifonafe: int
    monto_pagado: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    fecha_pago: date
    tipo_pago: Literal['anticipo', 'parcial', 'total']
    medio_pago: Optional[
        Literal['transferencia', 'cheque', 'deposito', 'otro']
    ] = None
    banco_emisor: Optional[str] = Field(default=None, max_length=100)
    referencia_bancaria: Optional[str] = Field(default=None, max_length=100)
    id_persona_beneficiaria: Optional[int] = None
    beneficiario_externo: Optional[str] = Field(default=None, max_length=300)

    @field_validator(
        'banco_emisor',
        'referencia_bancaria',
        'beneficiario_externo',
        mode='before',
    )
    @classmethod
    def normalizar_textos_opcionales(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @model_validator(mode='after')
    def validar_beneficiario(self):
        valores = [
            self.id_persona_beneficiaria is not None,
            bool(self.beneficiario_externo and self.beneficiario_externo.strip()),
        ]
        if sum(valores) != 1:
            raise ValueError('Debe indicar exactamente un beneficiario')
        return self


class PagoIndemnizacionUpdate(BaseModel):
    monto_pagado: Optional[Decimal] = Field(
        default=None, gt=0, max_digits=18, decimal_places=2
    )
    fecha_pago: Optional[date] = None
    tipo_pago: Optional[Literal['anticipo', 'parcial', 'total']] = None
    medio_pago: Optional[
        Literal['transferencia', 'cheque', 'deposito', 'otro']
    ] = None
    banco_emisor: Optional[str] = Field(default=None, max_length=100)
    referencia_bancaria: Optional[str] = Field(default=None, max_length=100)
    id_persona_beneficiaria: Optional[int] = None
    beneficiario_externo: Optional[str] = Field(default=None, max_length=300)
    observaciones: Optional[str] = None

    @field_validator(
        'banco_emisor',
        'referencia_bancaria',
        'beneficiario_externo',
        mode='before',
    )
    @classmethod
    def normalizar_textos_opcionales(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value


class PagoIndemnizacionResponse(PagoIndemnizacionCreate):
    id_pago: int
    activo: bool
    model_config = ConfigDict(from_attributes=True)


class AlertasNoVistasCount(BaseModel):
    total: int

# ==================== CATÁLOGOS ==================== #
class EntidadFederativaResponse(BaseModel):
    id_entidad: int
    clave_inegi: str
    nombre: str
    activo: bool
    model_config = ConfigDict(from_attributes=True)

class MunicipioResponse(BaseModel):
    id_municipio: int
    id_entidad: int
    clave_inegi: str
    nombre: str
    activo: bool
    model_config = ConfigDict(from_attributes=True)

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

# ==================== USUARIO TRAMO ==================== #
class UsuarioTramoCreate(BaseModel):
    id_usuario: int
    motivo_reactivacion: Optional[str] = Field(default=None, min_length=1)

class UsuarioTramoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_usuario_tramo: int
    id_usuario: int
    id_tramo: int
    fecha_asignacion: datetime
    activo: bool
