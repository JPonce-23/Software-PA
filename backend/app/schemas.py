"""Pydantic contracts for the ProyectoNucleo target API."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Role = Literal["admin", "operador", "visualizador", "geografo"]
Ambito = Literal["colectivo", "individual"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AuditInput(BaseModel):
    observaciones: str | None = None


class AuditRead(ORMModel):
    activo: bool
    creado_en: datetime
    creado_por: int | None = None
    actualizado_en: datetime | None = None
    actualizado_por: int | None = None
    fecha_baja: datetime | None = None
    id_usuario_baja: int | None = None
    motivo_baja: str | None = None
    observaciones: str | None = None


class BajaRequest(BaseModel):
    motivo: str = Field(min_length=3, max_length=500)

    @field_validator("motivo")
    @classmethod
    def normalizar_motivo(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("El motivo es obligatorio")
        return value


class AuthUserResponse(ORMModel):
    id_usuario: int
    nombre: str
    apellido_paterno: str
    correo: str
    rol: Role


class AuthSessionResponse(BaseModel):
    user: AuthUserResponse
    expira_en: datetime


class AuthActionRequest(BajaRequest):
    pass


class AuthOperationResponse(BaseModel):
    detail: str


class UsuarioBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=250)
    apellido_paterno: str = Field(min_length=1, max_length=250)
    apellido_materno: str | None = Field(default=None, max_length=250)
    correo: str = Field(max_length=320)
    rol: Role

    @field_validator("correo")
    @classmethod
    def normalizar_correo(cls, value: str) -> str:
        value = value.strip().lower()
        local, separator, domain = value.partition("@")
        if not separator or not local or "." not in domain:
            raise ValueError("El correo electrónico no es válido")
        return value


class UsuarioCreate(UsuarioBase):
    contrasena: str

    @field_validator("contrasena")
    @classmethod
    def validar_contrasena(cls, value: str) -> str:
        checks = (
            len(value) >= 12,
            any(char.islower() for char in value),
            any(char.isupper() for char in value),
            any(char.isdigit() for char in value),
            any(not char.isalnum() for char in value),
        )
        if not all(checks):
            raise ValueError(
                "La contraseña debe tener al menos 12 caracteres e incluir "
                "mayúscula, minúscula, número y símbolo"
            )
        return value


class UsuarioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=250)
    apellido_paterno: str | None = Field(default=None, min_length=1, max_length=250)
    apellido_materno: str | None = Field(default=None, max_length=250)
    rol: Role | None = None


class UsuarioResponse(UsuarioBase, ORMModel):
    id_usuario: int
    activo: bool
    fecha_alta: datetime


class EntidadFederativaResponse(ORMModel):
    id_entidad: int
    clave_inegi: str
    nombre: str
    activo: bool


class MunicipioResponse(ORMModel):
    id_municipio: int
    id_entidad: int
    clave_inegi: str
    nombre: str
    activo: bool


class ProyectoCreate(AuditInput):
    clave_proyecto: str = Field(min_length=1, max_length=30)
    nombre_proyecto: str = Field(min_length=1, max_length=200)
    descripcion: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None

    @model_validator(mode="after")
    def validar_fechas(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")
        return self


class ProyectoUpdate(AuditInput):
    nombre_proyecto: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


class ProyectoResponse(ProyectoCreate, AuditRead):
    id_proyecto: int


class NucleoAgrarioCreate(AuditInput):
    id_municipio: int = Field(gt=0)
    nombre_nucleo: str = Field(min_length=1, max_length=300)
    tipo_nucleo: Literal["ejido", "comunidad"]
    comunidad_indigena: bool = False
    fuente_datos: str | None = Field(default=None, max_length=120)
    id_entidad_fuente: str | None = Field(default=None, max_length=120)
    id_municipio_fuente: str | None = Field(default=None, max_length=120)
    id_nucleo_fuente: str | None = Field(default=None, max_length=120)
    alcance_identidad_fuente: str | None = Field(default=None, max_length=20)


class NucleoAgrarioUpdate(AuditInput):
    nombre_nucleo: str | None = Field(default=None, min_length=1, max_length=300)
    tipo_nucleo: Literal["ejido", "comunidad"] | None = None
    comunidad_indigena: bool | None = None
    fuente_datos: str | None = Field(default=None, max_length=120)


class GeometriaPoligonoUpdate(BaseModel):
    geometria_wkt: str | None = None
    fuente_geometria: str | None = Field(default=None, max_length=250)
    fecha_fuente_geometria: date | None = None


class NucleoAgrarioResponse(NucleoAgrarioCreate, AuditRead):
    id_nucleo: int
    geometria_wkt: str | None = None


class ProyectoNucleoReferenciaCreate(AuditInput):
    tipo_referencia: Literal["consecutivo", "clave_tramo", "numero_tramo", "otro"]
    valor: str = Field(min_length=1, max_length=150)
    es_principal: bool = False


class ProyectoNucleoReferenciaResponse(ProyectoNucleoReferenciaCreate, AuditRead):
    id_referencia: int
    id_proyecto_nucleo: int


class ProyectoNucleoReferenciaUpdate(AuditInput):
    valor: str | None = Field(default=None, min_length=1, max_length=150)
    es_principal: bool | None = None


class ProyectoNucleoCreate(AuditInput):
    id_nucleo: int = Field(gt=0)
    residencia: str | None = Field(default=None, max_length=300)
    responsable_nombre: str | None = Field(default=None, max_length=300)
    contacto: str | None = Field(default=None, max_length=150)
    referencias: list[ProyectoNucleoReferenciaCreate] = Field(default_factory=list)


class ProyectoNucleoUpdate(AuditInput):
    residencia: str | None = Field(default=None, max_length=300)
    responsable_nombre: str | None = Field(default=None, max_length=300)
    contacto: str | None = Field(default=None, max_length=150)


class ProyectoNucleoResponse(ProyectoNucleoUpdate, AuditRead):
    id_proyecto_nucleo: int
    id_proyecto: int
    id_nucleo: int
    clave_proyecto: str | None = None
    nombre_proyecto: str | None = None
    nombre_nucleo: str | None = None
    tipo_nucleo: str | None = None
    id_entidad: int | None = None
    entidad: str | None = None
    id_municipio: int | None = None
    municipio: str | None = None
    consecutivo_principal: str | None = None
    actividades: int = 0
    asambleas: int = 0
    afectaciones_colectivas: int = 0
    afectaciones_individuales: int = 0
    parcelas: int = 0
    convenios: int = 0
    tramites_fifonafe: int = 0


class PersonaCreate(AuditInput):
    curp: str | None = Field(default=None, max_length=18)
    rfc: str | None = Field(default=None, max_length=13)
    nombre: str = Field(min_length=1, max_length=300)
    apellido_paterno: str | None = Field(default=None, max_length=200)
    apellido_materno: str | None = Field(default=None, max_length=200)
    telefono: str | None = Field(default=None, max_length=30)
    correo_electronico: str | None = Field(default=None, max_length=320)
    datos_identidad_incompletos: bool = False
    origen_registro: Literal["captura_sistema", "excel", "qa", "otro"] = "captura_sistema"


class PersonaUpdate(AuditInput):
    curp: str | None = Field(default=None, max_length=18)
    rfc: str | None = Field(default=None, max_length=13)
    nombre: str | None = Field(default=None, min_length=1, max_length=300)
    apellido_paterno: str | None = Field(default=None, max_length=200)
    apellido_materno: str | None = Field(default=None, max_length=200)
    telefono: str | None = Field(default=None, max_length=30)
    correo_electronico: str | None = Field(default=None, max_length=320)
    datos_identidad_incompletos: bool | None = None


class PersonaResponse(PersonaCreate, AuditRead):
    id_persona: int


class OrvCreate(AuditInput):
    numero_orv: str | None = Field(default=None, max_length=50)
    inicio_vigencia: date | None = None
    fin_vigencia: date | None = None
    estatus_fuente: str | None = Field(default=None, max_length=80)
    acta_eleccion_inscrita_ran: bool | None = None
    fecha_inscripcion_acta_ran: date | None = None


class OrvUpdate(OrvCreate):
    pass


class OrvResponse(OrvCreate, AuditRead):
    id_orv: int
    id_nucleo: int
    estado_derivado: str | None = None


class OrvIntegranteCreate(AuditInput):
    id_persona: int = Field(gt=0)
    cargo: str = Field(min_length=1, max_length=80)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


class OrvIntegranteResponse(OrvIntegranteCreate, AuditRead):
    id_orv_integrante: int
    id_orv: int


class OrvIntegranteDetailResponse(OrvIntegranteResponse):
    nombre: str
    apellido_paterno: str | None = None
    apellido_materno: str | None = None
    telefono: str | None = None
    correo_electronico: str | None = None


class OrvIntegranteUpdate(AuditInput):
    cargo: str | None = Field(default=None, min_length=1, max_length=80)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


class PadronHistorialCreate(AuditInput):
    fecha_padron: date | None = None
    numero_ejidatarios_comuneros: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validar_datos(self):
        if self.fecha_padron is None and self.numero_ejidatarios_comuneros is None:
            raise ValueError("Se requiere fecha o cantidad del padrón")
        return self


class PadronHistorialResponse(PadronHistorialCreate, AuditRead):
    id_padron: int
    id_nucleo: int


class PadronHistorialUpdate(AuditInput):
    fecha_padron: date | None = None
    numero_ejidatarios_comuneros: int | None = Field(default=None, ge=0)


class ParcelaCreate(AuditInput):
    tipo_parcela: Literal["individual", "copropiedad", "otro", "no_determinado"]
    no_parcela: str | None = Field(default=None, max_length=80)
    no_parcela_ppt: str | None = Field(default=None, max_length=80)
    certificado_parcelario: str | None = Field(default=None, max_length=120)
    folio_derechos: str | None = Field(default=None, max_length=120)
    constancia_vigencia_fecha: date | None = None


class ParcelaUpdate(AuditInput):
    tipo_parcela: Literal["individual", "copropiedad", "otro", "no_determinado"] | None = None
    no_parcela: str | None = Field(default=None, max_length=80)
    no_parcela_ppt: str | None = Field(default=None, max_length=80)
    certificado_parcelario: str | None = Field(default=None, max_length=120)
    folio_derechos: str | None = Field(default=None, max_length=120)
    constancia_vigencia_fecha: date | None = None


class ParcelaResponse(ParcelaCreate, AuditRead):
    id_parcela: int
    id_nucleo: int
    geometria_wkt: str | None = None


class ParcelaTitularCreate(AuditInput):
    id_persona: int = Field(gt=0)
    tipo_derecho: str = Field(min_length=1, max_length=50)
    porcentaje_participacion: Decimal | None = Field(default=None, gt=0, le=100)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


class ParcelaTitularResponse(ParcelaTitularCreate, AuditRead):
    id_parcela_titular: int
    id_parcela: int


class ParcelaTitularDetailResponse(ParcelaTitularResponse):
    nombre: str
    apellido_paterno: str | None = None
    apellido_materno: str | None = None
    telefono: str | None = None
    correo_electronico: str | None = None


class ParcelaTitularUpdate(AuditInput):
    tipo_derecho: str | None = Field(default=None, min_length=1, max_length=50)
    porcentaje_participacion: Decimal | None = Field(default=None, gt=0, le=100)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


class ActividadCampoCreate(AuditInput):
    tipo_actividad: Literal["sensibilizacion", "caminamiento"]
    contexto_actividad: Literal[
        "general", "superficie_adicional", "obras_complementarias", "otro"
    ] = "general"
    fecha_programada: date | None = None
    fecha_realizada: date | None = None
    responsable: str | None = Field(default=None, max_length=300)
    resultado: str | None = None


class ActividadCampoUpdate(ActividadCampoCreate):
    tipo_actividad: Literal["sensibilizacion", "caminamiento"] | None = None
    contexto_actividad: Literal[
        "general", "superficie_adicional", "obras_complementarias", "otro"
    ] | None = None


class ActividadCampoResponse(ActividadCampoCreate, AuditRead):
    id_actividad: int
    id_proyecto_nucleo: int


class AfectacionCreate(AuditInput):
    tipo_afectacion: Ambito
    id_parcela: int | None = Field(default=None, gt=0)
    destino_superficie: str | None = Field(default=None, max_length=100)
    no_parcela_solar: str | None = Field(default=None, max_length=100)
    superficie_preliminar_ha: Decimal | None = Field(default=None, ge=0)
    superficie_afectada_ha: Decimal | None = Field(default=None, ge=0)
    situacion: str | None = Field(default=None, max_length=100)
    condicion_especial: Literal[
        "expropiacion_directa",
        "comunidad_indigena",
        "no_afectacion_uso_comun",
        "otro",
    ] | None = None
    descripcion_condicion: str | None = None
    avaluo_monto: Decimal | None = Field(default=None, ge=0)
    avaluo_fecha: date | None = None
    avaluo_referencia: str | None = Field(default=None, max_length=150)
    avaluo_institucion: str | None = Field(default=None, max_length=150)

    @model_validator(mode="after")
    def validar_ambito(self):
        if self.tipo_afectacion == "colectivo" and self.id_parcela is not None:
            raise ValueError("Una afectación colectiva no admite parcela")
        if self.tipo_afectacion == "individual" and self.id_parcela is None:
            raise ValueError("Una afectación individual requiere parcela")
        if self.condicion_especial == "otro" and not (
            self.descripcion_condicion and self.descripcion_condicion.strip()
        ):
            raise ValueError("La condición 'otro' requiere descripción")
        return self


class AfectacionUpdate(AuditInput):
    destino_superficie: str | None = Field(default=None, max_length=100)
    no_parcela_solar: str | None = Field(default=None, max_length=100)
    superficie_preliminar_ha: Decimal | None = Field(default=None, ge=0)
    superficie_afectada_ha: Decimal | None = Field(default=None, ge=0)
    situacion: str | None = Field(default=None, max_length=100)
    condicion_especial: Literal[
        "expropiacion_directa",
        "comunidad_indigena",
        "no_afectacion_uso_comun",
        "otro",
    ] | None = None
    descripcion_condicion: str | None = None
    avaluo_monto: Decimal | None = Field(default=None, ge=0)
    avaluo_fecha: date | None = None
    avaluo_referencia: str | None = Field(default=None, max_length=150)
    avaluo_institucion: str | None = Field(default=None, max_length=150)


class AfectacionResponse(AfectacionCreate, AuditRead):
    id_afectacion: int
    id_proyecto_nucleo: int


class AsambleaCreate(AuditInput):
    id_padron: int | None = Field(default=None, gt=0)
    tipo_asamblea: Literal[
        "anuencia",
        "modificatorio",
        "superficie_adicional",
        "obras_complementarias",
        "retiro_fondos",
        "otra",
    ]
    contexto_proceso: Literal[
        "cop_original",
        "modificatorio",
        "superficie_adicional",
        "obras_complementarias",
        "retiro_fondos",
        "otro",
    ] | None = None
    proposito: str | None = None
    fecha_expedicion_primera: date | None = None
    fecha_programada_primera: date | None = None
    fecha_expedicion_segunda: date | None = None
    fecha_programada_segunda: date | None = None
    fecha_realizada: date | None = None
    resultado: str | None = Field(default=None, max_length=50)
    fecha_programada_ingreso_ran: date | None = None
    fecha_ingreso_ran: date | None = None
    numero_solicitud_ran: str | None = Field(default=None, max_length=120)
    calificacion_registral_ran: str | None = None
    fecha_inscripcion_ran: date | None = None


class AsambleaUpdate(AsambleaCreate):
    tipo_asamblea: Literal[
        "anuencia",
        "modificatorio",
        "superficie_adicional",
        "obras_complementarias",
        "retiro_fondos",
        "otra",
    ] | None = None


class AsambleaResponse(AsambleaCreate, AuditRead):
    id_asamblea: int
    id_proyecto_nucleo: int


class ConvenioCreate(AuditInput):
    tipo_instrumento: Literal["convenio", "otro"] = "convenio"
    tipo_convenio: Literal[
        "cop_original",
        "modificatorio",
        "superficie_adicional",
        "obras_complementarias",
        "ampliacion",
        "ampliacion_remanente",
    ] | None = None
    modalidad_especial: Literal["permuta", "otra"] | None = None
    descripcion_modalidad: str | None = None
    descripcion_instrumento: str | None = None
    consecutivo: int = Field(default=1, gt=0)
    id_convenio_padre: int | None = Field(default=None, gt=0)
    id_asamblea_autorizacion: int | None = Field(default=None, gt=0)
    fecha_programada_firma: date | None = None
    fecha_firma: date | None = None
    monto_90: Decimal | None = Field(default=None, ge=0)
    monto_100: Decimal | None = Field(default=None, ge=0)
    monto_bdt: Decimal | None = Field(default=None, ge=0)
    superficie_ha: Decimal | None = Field(default=None, ge=0)
    fecha_programada_ingreso_ran: date | None = None
    ingreso_ran_fecha: date | None = None
    numero_solicitud_ingreso: str | None = Field(default=None, max_length=120)
    calificacion_registral: str | None = None
    fecha_inscripcion_ran: date | None = None

    @model_validator(mode="after")
    def validar_instrumento(self):
        if self.tipo_instrumento == "convenio" and self.tipo_convenio is None:
            raise ValueError("Un convenio requiere tipo_convenio")
        if self.tipo_instrumento == "otro" and not (
            self.descripcion_instrumento and self.descripcion_instrumento.strip()
        ):
            raise ValueError("Un instrumento 'otro' requiere descripción")
        if self.modalidad_especial == "permuta" and self.tipo_convenio != "cop_original":
            raise ValueError("Permuta sólo es modalidad de cop_original")
        if self.modalidad_especial == "otra" and not (
            self.descripcion_modalidad and self.descripcion_modalidad.strip()
        ):
            raise ValueError("La modalidad 'otra' requiere descripción")
        if self.monto_90 is not None and self.monto_100 is not None:
            if self.monto_90 > self.monto_100:
                raise ValueError("monto_90 no puede exceder monto_100")
        return self


class ConvenioUpdate(ConvenioCreate):
    tipo_instrumento: Literal["convenio", "otro"] | None = None
    consecutivo: int | None = Field(default=None, gt=0)


class ConvenioAfectacionCreate(BaseModel):
    id_afectacion: int = Field(gt=0)


class ConvenioAfectacionResponse(AuditRead):
    id_convenio_afectacion: int
    id_convenio: int
    id_afectacion: int
    rol: Literal["principal", "adicional"]


class ConvenioResponse(ConvenioCreate, AuditRead):
    id_convenio: int
    id_proyecto_nucleo: int
    ambito: Ambito
    afectaciones: list[ConvenioAfectacionResponse] = Field(default_factory=list)


class TramiteFifonafeCreate(AuditInput):
    ids_afectacion: list[int] = Field(min_length=1)
    estatus: Literal["programado", "pendiente", "completo", "cancelado", "otro"] = "pendiente"
    acuse_fifonafe_fecha: date | None = None
    no_oficio_fifonafe_a_dgaopr: str | None = Field(default=None, max_length=100)
    fecha_oficio_fifonafe_a_dgaopr: date | None = None
    no_oficio_dgaopr_a_representacion: str | None = Field(default=None, max_length=100)
    fecha_oficio_dgaopr_a_representacion: date | None = None
    no_oficio_respuesta_representacion_a_dgaopr: str | None = Field(default=None, max_length=100)
    fecha_oficio_respuesta_representacion_a_dgaopr: date | None = None
    no_oficio_respuesta_dgaopr_a_fifonafe: str | None = Field(default=None, max_length=100)
    fecha_oficio_respuesta_dgaopr_a_fifonafe: date | None = None
    hay_conflictos: bool | None = None
    resultado_no_conflictos: str | None = None

    @field_validator("ids_afectacion")
    @classmethod
    def validar_ids(cls, value: list[int]) -> list[int]:
        if any(item <= 0 for item in value) or len(value) != len(set(value)):
            raise ValueError("Las afectaciones deben ser IDs positivos únicos")
        return value


class TramiteFifonafeUpdate(AuditInput):
    estatus: Literal["programado", "pendiente", "completo", "cancelado", "otro"] | None = None
    acuse_fifonafe_fecha: date | None = None
    no_oficio_fifonafe_a_dgaopr: str | None = Field(default=None, max_length=100)
    fecha_oficio_fifonafe_a_dgaopr: date | None = None
    no_oficio_dgaopr_a_representacion: str | None = Field(default=None, max_length=100)
    fecha_oficio_dgaopr_a_representacion: date | None = None
    no_oficio_respuesta_representacion_a_dgaopr: str | None = Field(default=None, max_length=100)
    fecha_oficio_respuesta_representacion_a_dgaopr: date | None = None
    no_oficio_respuesta_dgaopr_a_fifonafe: str | None = Field(default=None, max_length=100)
    fecha_oficio_respuesta_dgaopr_a_fifonafe: date | None = None
    hay_conflictos: bool | None = None
    resultado_no_conflictos: str | None = None


class TramiteFifonafeAfectacionResponse(AuditRead):
    id_tramite_fifonafe_afectacion: int
    id_tramite_fifonafe: int
    id_afectacion: int


class TramiteFifonafeResponse(TramiteFifonafeUpdate, AuditRead):
    id_tramite_fifonafe: int
    id_proyecto_nucleo: int
    ambito: Ambito
    estatus: str
    afectaciones: list[TramiteFifonafeAfectacionResponse] = Field(default_factory=list)


class IndemnizacionCreate(AuditInput):
    estatus: Literal["pendiente", "programado", "completo", "otro"] = "pendiente"
    descripcion_estatus: str | None = None
    fecha_programada: date | None = None
    fecha_resolucion: date | None = None
    fecha_entrega_expediente_pa: date | None = None

    @model_validator(mode="after")
    def validar_otro(self):
        if self.estatus == "otro" and not (
            self.descripcion_estatus and self.descripcion_estatus.strip()
        ):
            raise ValueError("El estatus 'otro' requiere descripción")
        return self


class IndemnizacionUpdate(IndemnizacionCreate):
    estatus: Literal["pendiente", "programado", "completo", "otro"] | None = None


class IndemnizacionResponse(IndemnizacionCreate, AuditRead):
    id_indemnizacion: int
    id_afectacion: int


class PagoCreate(AuditInput):
    fecha_pago: date
    monto: Decimal = Field(gt=0)
    id_persona_beneficiaria: int | None = Field(default=None, gt=0)
    beneficiario_nombre: str = Field(min_length=1, max_length=300)
    referencia: str | None = Field(default=None, max_length=150)
    medio_pago: Literal[
        "transferencia", "cheque", "efectivo", "deposito", "otro"
    ] | None = None


class PagoUpdate(AuditInput):
    fecha_pago: date | None = None
    monto: Decimal | None = Field(default=None, gt=0)
    id_persona_beneficiaria: int | None = Field(default=None, gt=0)
    beneficiario_nombre: str | None = Field(default=None, min_length=1, max_length=300)
    referencia: str | None = Field(default=None, max_length=150)
    medio_pago: Literal[
        "transferencia", "cheque", "efectivo", "deposito", "otro"
    ] | None = None


class PagoResponse(PagoCreate, AuditRead):
    id_pago: int
    id_indemnizacion: int


class DocumentoCreate(AuditInput):
    tipo_documento: str = Field(min_length=1, max_length=80)
    estado: Literal["disponible", "faltante", "referenciado"]
    titulo: str | None = Field(default=None, max_length=250)
    fecha_documento: date | None = None
    numero_folio: str | None = Field(default=None, max_length=150)
    descripcion: str | None = None


class DocumentoResponse(DocumentoCreate, AuditRead):
    id_documento: int


class DocumentoUpdate(AuditInput):
    tipo_documento: str | None = Field(default=None, min_length=1, max_length=80)
    estado: Literal["disponible", "faltante", "referenciado"] | None = None
    titulo: str | None = Field(default=None, max_length=250)
    fecha_documento: date | None = None
    numero_folio: str | None = Field(default=None, max_length=150)
    descripcion: str | None = None


class DocumentoVinculoResponse(AuditRead):
    id_documento_vinculo: int
    id_documento: int
    entidad_tipo: Literal[
        "proyecto_nucleo",
        "nucleo_agrario",
        "orv",
        "padron_historial",
        "parcela",
        "afectacion",
        "asamblea",
        "convenio",
        "tramite_fifonafe",
        "indemnizacion",
        "pago",
    ]
    entidad_id: int


class DocumentoVersionResponse(ORMModel):
    id_documento_version: int
    id_documento: int
    numero_version: int
    hash_sha256: str
    tamano_bytes: int
    nombre_original: str
    tipo_mime: str | None = None
    fecha_carga: datetime


class TrazabilidadFuenteCreate(BaseModel):
    archivo: str = Field(min_length=1, max_length=255)
    hoja: str | None = Field(default=None, max_length=255)
    fila: int | None = Field(default=None, gt=0)
    columna: str | None = Field(default=None, max_length=120)
    valor_original: str | None = None
    tratamiento: Literal[
        "PERSISTIR",
        "DERIVAR",
        "REFERENCIA",
        "DOCUMENTAR",
        "REVISAR",
        "NO IMPLEMENTAR",
    ]


class TrazabilidadFuenteResponse(TrazabilidadFuenteCreate, ORMModel):
    id_trazabilidad: int
    entidad_tipo: str
    entidad_id: int
    registrado_en: datetime
    id_usuario_registro: int | None = None


class UsuarioProyectoCreate(BaseModel):
    id_usuario: int = Field(gt=0)


class UsuarioProyectoResponse(AuditRead):
    id_usuario_proyecto: int
    id_usuario: int
    id_proyecto: int
    asignado_por: int
    fecha_asignacion: datetime


class TrazoProyectoCreate(AuditInput):
    version: int = Field(gt=0)
    geometria_wkt: str = Field(min_length=1)
    fuente: str = Field(min_length=1, max_length=250)
    fecha_fuente: date | None = None
    fecha_vigencia_inicio: date
    fecha_vigencia_fin: date | None = None


class TrazoProyectoResponse(AuditRead):
    id_trazo: int
    id_proyecto: int
    version: int
    geometria_wkt: str | None = None
    fuente: str
    fecha_fuente: date | None = None
    fecha_vigencia_inicio: date
    fecha_vigencia_fin: date | None = None


class ImportacionArchivoResponse(AuditRead):
    id_importacion: int
    id_proyecto: int
    tipo_objetivo: Literal["trazo_proyecto", "nucleo_agrario", "parcela"]
    nombre_original: str
    formato_detectado: str
    tamano_bytes: int
    sha256: str
    fuente: str
    fecha_fuente: date | None = None
    crs_original: str | None = None
    crs_destino: str
    estado: str
    total_features: int
    features_procesados: int
    validos: int
    advertencias: int
    errores: int
    importados: int
    descartados: int
    confirmacion_explicita: bool
    reporte: dict[str, Any]


class ImportacionFeatureResponse(ORMModel):
    id_importacion_feature: int
    id_importacion: int
    indice_feature: int
    capa_origen: str | None = None
    id_externo: str | None = None
    tipo_geometria: str | None = None
    atributos_originales: dict[str, Any]
    atributos_normalizados: dict[str, Any]
    estado: str
    errores: list[Any]
    advertencias: list[Any]
    transformaciones: list[Any]
    advertencias_aceptadas: bool
    registro_destino_id: int | None = None


class ImportacionConfirmarRequest(BaseModel):
    confirmacion_explicita: Literal[True]
    aceptar_advertencias: bool = False


class DashboardKpiResponse(ORMModel):
    id_proyecto: int
    anio: int
    indicador: str
    programado: int
    realizado: int
    cantidad: int
    superficie_ha: Decimal | None = None
    monto: Decimal | None = None


class BitacoraResponse(ORMModel):
    id_bitacora: int
    id_usuario: int | None = None
    id_proyecto: int | None = None
    id_proyecto_nucleo: int | None = None
    id_nucleo: int | None = None
    entidad_tipo: str
    entidad_id: int | None = None
    accion: str
    valor_anterior: dict[str, Any] | None = None
    valor_nuevo: dict[str, Any] | None = None
    fecha_hora: datetime
    ip_origen: str | None = None
    user_agent: str | None = None
