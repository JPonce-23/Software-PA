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


class CatalogoOperativoCreate(AuditInput):
    tipo_catalogo: str = Field(min_length=1, max_length=50)
    codigo: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$", max_length=80)
    nombre: str = Field(min_length=1, max_length=250)
    descripcion: str | None = None
    orden: int = 0
    fuente: str | None = Field(default=None, max_length=250)
    vigencia_inicio: date | None = None
    vigencia_fin: date | None = None


class CatalogoOperativoUpdate(AuditInput):
    nombre: str | None = Field(default=None, min_length=1, max_length=250)
    descripcion: str | None = None
    orden: int | None = None
    fuente: str | None = Field(default=None, max_length=250)
    vigencia_inicio: date | None = None
    vigencia_fin: date | None = None
    activo: bool | None = None
    motivo_baja: str | None = Field(default=None, max_length=500)


class CatalogoOperativoResponse(CatalogoOperativoCreate, AuditRead):
    id_catalogo_opcion: int


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
    id_tipo_tenencia: int | None = Field(default=None, gt=0)
    tipo_nucleo: str | None = Field(default=None, max_length=20)
    comunidad_indigena: bool | None = None
    fuente_datos: str | None = Field(default=None, max_length=120)
    id_entidad_fuente: str | None = Field(default=None, max_length=120)
    id_municipio_fuente: str | None = Field(default=None, max_length=120)
    id_nucleo_fuente: str | None = Field(default=None, max_length=120)
    alcance_identidad_fuente: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validar_tenencia(self):
        if self.id_tipo_tenencia is None and not self.tipo_nucleo:
            raise ValueError("Se requiere id_tipo_tenencia")
        return self


class NucleoAgrarioUpdate(AuditInput):
    nombre_nucleo: str | None = Field(default=None, min_length=1, max_length=300)
    id_tipo_tenencia: int | None = Field(default=None, gt=0)
    tipo_nucleo: str | None = Field(default=None, max_length=20)
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
    id_residencia: int | None = Field(default=None, gt=0)
    residencia: str | None = Field(default=None, max_length=300)
    total_cops_planeados: int | None = Field(default=None, ge=0)
    responsable_nombre: str | None = Field(default=None, max_length=300)
    contacto: str | None = Field(default=None, max_length=150)
    referencias: list[ProyectoNucleoReferenciaCreate] = Field(default_factory=list)
    afecta_tuc: bool | None = None
    id_motivo_no_afecta_tuc: int | None = Field(default=None, gt=0)
    motivo_no_afecta_tuc_detalle: str | None = None
    tuc_revision_pendiente: bool = False
    tuc_revision_detalle: str | None = None


class ProyectoNucleoUpdate(AuditInput):
    id_residencia: int | None = Field(default=None, gt=0)
    residencia: str | None = Field(default=None, max_length=300)
    total_cops_planeados: int | None = Field(default=None, ge=0)
    responsable_nombre: str | None = Field(default=None, max_length=300)
    contacto: str | None = Field(default=None, max_length=150)
    afecta_tuc: bool | None = None
    id_motivo_no_afecta_tuc: int | None = Field(default=None, gt=0)
    motivo_no_afecta_tuc_detalle: str | None = None
    tuc_revision_pendiente: bool | None = None
    tuc_revision_detalle: str | None = None


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


class ProyectoNucleoResponsableCreate(AuditInput):
    nombre: str = Field(min_length=1, max_length=300)
    cargo: str | None = Field(default=None, max_length=200)
    contacto: str | None = Field(default=None, max_length=200)
    vigencia_inicio: date | None = None
    vigencia_fin: date | None = None
    es_principal: bool = False


class ProyectoNucleoResponsableUpdate(AuditInput):
    nombre: str | None = Field(default=None, min_length=1, max_length=300)
    cargo: str | None = Field(default=None, max_length=200)
    contacto: str | None = Field(default=None, max_length=200)
    vigencia_inicio: date | None = None
    vigencia_fin: date | None = None
    es_principal: bool | None = None


class ProyectoNucleoResponsableResponse(ProyectoNucleoResponsableCreate, AuditRead):
    id_responsable: int
    id_proyecto_nucleo: int


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
    id_estado_registral: int | None = Field(default=None, gt=0)
    acta_eleccion_inscrita_ran: bool | None = None


class OrvUpdate(OrvCreate):
    pass


class OrvResponse(OrvCreate, AuditRead):
    id_orv: int
    id_nucleo: int
    fecha_inscripcion_acta_ran: date | None = None
    estado_derivado: str | None = None


class OrvIntegranteCreate(AuditInput):
    id_persona: int = Field(gt=0)
    cargo: str | None = Field(default=None, min_length=1, max_length=80)
    id_organo: int | None = Field(default=None, gt=0)
    id_cargo: int | None = Field(default=None, gt=0)
    id_calidad: int | None = Field(default=None, gt=0)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None

    @model_validator(mode="after")
    def validar_estructura(self):
        ids = (self.id_organo, self.id_cargo, self.id_calidad)
        if any(item is not None for item in ids) and not all(item is not None for item in ids):
            raise ValueError("Órgano, cargo y calidad deben capturarse juntos")
        if not self.cargo and not all(item is not None for item in ids):
            raise ValueError("Se requiere estructura ORV normalizada")
        return self


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
    id_organo: int | None = Field(default=None, gt=0)
    id_cargo: int | None = Field(default=None, gt=0)
    id_calidad: int | None = Field(default=None, gt=0)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


class PadronHistorialCreate(AuditInput):
    fecha_padron: date | None = None
    numero_ejidatarios_comuneros: int | None = Field(default=None, ge=0)
    fuente: str | None = Field(default=None, max_length=250)
    id_documento: int | None = Field(default=None, gt=0)

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
    fuente: str | None = Field(default=None, max_length=250)
    id_documento: int | None = Field(default=None, gt=0)


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


class UnidadAgrariaTitularBase(BaseModel):
    id_persona: int | None = Field(default=None, gt=0)
    id_parcela_titular: int | None = Field(default=None, gt=0)
    porcentaje_participacion: Decimal | None = Field(default=None, ge=0, le=100)
    es_principal: bool = False

class UnidadAgrariaTitularCreate(UnidadAgrariaTitularBase, AuditInput):
    pass

class UnidadAgrariaTitularUpdate(UnidadAgrariaTitularBase, AuditInput):
    pass

class UnidadAgrariaTitularResponse(UnidadAgrariaTitularBase, AuditRead):
    id_unidad_titular: int
    id_unidad_agraria: int

class UnidadAgrariaBase(BaseModel):
    id_tipo_tierra: int = Field(gt=0)
    id_tipo_gestion: int | None = Field(default=None, gt=0)
    id_destino_superficie: int | None = Field(default=None, gt=0)
    id_tipo_titularidad: int = Field(gt=0)
    id_parcela: int | None = Field(default=None, gt=0)
    referencia_alfanumerica: str | None = Field(default=None, max_length=150)
    detalle: str | None = None
    fuente: str | None = Field(default=None, max_length=250)
    requiere_revision: bool = False
    motivo_revision: str | None = None

class UnidadAgrariaCreate(UnidadAgrariaBase, AuditInput):
    pass

class UnidadAgrariaUpdate(BaseModel):
    id_tipo_tierra: int | None = Field(default=None, gt=0)
    id_tipo_gestion: int | None = Field(default=None, gt=0)
    id_destino_superficie: int | None = Field(default=None, gt=0)
    id_tipo_titularidad: int | None = Field(default=None, gt=0)
    id_parcela: int | None = Field(default=None, gt=0)
    referencia_alfanumerica: str | None = Field(default=None, max_length=150)
    detalle: str | None = None
    fuente: str | None = Field(default=None, max_length=250)
    requiere_revision: bool | None = None
    motivo_revision: str | None = None
    actualizado_por: int | None = Field(default=None, gt=0)

class UnidadAgrariaResponse(UnidadAgrariaBase, AuditRead):
    id_unidad_agraria: int
    id_nucleo: int
    referencia_normalizada: str | None = None
    titulares: list[UnidadAgrariaTitularResponse] = []

class AfectacionUnidadAgrariaBase(BaseModel):
    id_unidad_agraria: int = Field(gt=0)
    superficie_preliminar_ha: Decimal | None = Field(default=None, ge=0)
    superficie_afectada_ha: Decimal | None = Field(default=None, ge=0)
    superficie_valor_original: str | None = Field(default=None, max_length=120)
    superficie_formato_origen: str | None = Field(default=None, max_length=50)
    fuente: str | None = Field(default=None, max_length=250)

class AfectacionUnidadAgrariaCreate(AfectacionUnidadAgrariaBase, AuditInput):
    pass

class AfectacionUnidadAgrariaResponse(AfectacionUnidadAgrariaBase, AuditRead):
    id_afectacion_unidad: int
    id_afectacion: int
    unidad_agraria: UnidadAgrariaResponse | None = None

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

    id_tipo_cop_operativo: int | None = Field(default=None, gt=0)
    tipo_cop_revision_pendiente: bool = False
    tipo_cop_revision_detalle: str | None = None
    @model_validator(mode="after")
    def validar_ambito(self):
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
    id_tipo_cop_operativo: int | None = Field(default=None, gt=0)
    tipo_cop_revision_pendiente: bool | None = None
    tipo_cop_revision_detalle: str | None = None


class AfectacionResponse(AfectacionCreate, AuditRead):
    id_afectacion: int
    id_proyecto_nucleo: int
    id_tipo_cop_operativo: int | None = None
    tipo_cop_revision_pendiente: bool = False
    tipo_cop_revision_detalle: str | None = None
    unidades_agrarias: list[AfectacionUnidadAgrariaResponse] = Field(default_factory=list)


class BienAfectadoCreate(AuditInput):
    id_tipo_gestion: int | None = Field(default=None, gt=0)
    id_destino_superficie: int | None = Field(default=None, gt=0)
    id_parcela: int | None = Field(default=None, gt=0)
    tipo_tierra: str | None = Field(default=None, max_length=120)
    referencia_alfanumerica: str | None = Field(default=None, max_length=150)
    titularidad: str | None = Field(default=None, max_length=250)
    detalle: str | None = None
    superficie_preliminar_ha: Decimal | None = Field(default=None, ge=0)
    superficie_afectada_ha: Decimal | None = Field(default=None, ge=0)
    superficie_valor_original: str | None = Field(default=None, max_length=120)
    superficie_formato_origen: str | None = Field(default=None, max_length=50)
    fuente: str | None = Field(default=None, max_length=250)

    @model_validator(mode="after")
    def validar_identidad_bien(self):
        if not any((self.id_tipo_gestion, self.id_destino_superficie, self.id_parcela,
                    self.tipo_tierra, self.referencia_alfanumerica)):
            raise ValueError("El bien requiere gestión, destino, parcela, tierra o referencia")
        return self


class BienAfectadoUpdate(BienAfectadoCreate):
    @model_validator(mode="after")
    def validar_identidad_bien(self):
        # En PATCH la identidad puede permanecer en los campos no enviados.
        return self


class BienAfectadoResponse(BienAfectadoCreate, AuditRead):
    id_bien_afectado: int
    id_afectacion: int


class AsambleaConvocatoriaCreate(AuditInput):
    ordinal: int = Field(gt=0)
    fecha_expedicion: date | None = None
    fecha_programada: date | None = None
    fecha_realizacion: date | None = None
    id_resultado: int | None = Field(default=None, gt=0)
    observaciones_resultado: str | None = None
    id_documento: int | None = Field(default=None, gt=0)


class AsambleaConvocatoriaUpdate(AuditInput):
    fecha_expedicion: date | None = None
    fecha_programada: date | None = None
    fecha_realizacion: date | None = None
    id_resultado: int | None = Field(default=None, gt=0)
    observaciones_resultado: str | None = None
    id_documento: int | None = Field(default=None, gt=0)


class AsambleaConvocatoriaResponse(AsambleaConvocatoriaCreate, AuditRead):
    id_convocatoria: int
    id_asamblea: int


class AsambleaCreate(AuditInput):
    id_padron: int | None = Field(default=None, gt=0)
    id_tipo_asamblea: int | None = Field(default=None, gt=0)
    id_contexto_asamblea: int | None = Field(default=None, gt=0)
    tipo_asamblea: str | None = Field(default=None, max_length=40)
    contexto_proceso: str | None = Field(default=None, max_length=40)
    proposito: str | None = None
    resultado: str | None = Field(default=None, max_length=50)
    convocatorias: list[AsambleaConvocatoriaCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_tipo_catalogado(self):
        if self.id_tipo_asamblea is None and not self.tipo_asamblea:
            raise ValueError("Se requiere id_tipo_asamblea")
        if len({item.ordinal for item in self.convocatorias}) != len(self.convocatorias):
            raise ValueError("Los ordinales de convocatoria no pueden repetirse")
        return self


class AsambleaUpdate(AsambleaCreate):
    convocatorias: list[AsambleaConvocatoriaCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_tipo_catalogado(self):
        # El tipo ya existe en la entidad; sólo se valida cuando se crea.
        if len({item.ordinal for item in self.convocatorias}) != len(self.convocatorias):
            raise ValueError("Los ordinales de convocatoria no pueden repetirse")
        return self


class AsambleaResponse(AsambleaCreate, AuditRead):
    id_asamblea: int
    id_proyecto_nucleo: int
    fecha_expedicion_primera: date | None = None
    fecha_programada_primera: date | None = None
    fecha_expedicion_segunda: date | None = None
    fecha_programada_segunda: date | None = None
    fecha_realizada: date | None = None
    fecha_programada_ingreso_ran: date | None = None
    fecha_ingreso_ran: date | None = None
    numero_solicitud_ran: str | None = None
    calificacion_registral_ran: str | None = None
    fecha_inscripcion_ran: date | None = None
    convocatorias: list[AsambleaConvocatoriaResponse] = Field(default_factory=list)


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
    fecha_programada_ingreso_ran: date | None = None
    ingreso_ran_fecha: date | None = None
    numero_solicitud_ingreso: str | None = None
    calificacion_registral: str | None = None
    fecha_inscripcion_ran: date | None = None
    afectaciones: list[ConvenioAfectacionResponse] = Field(default_factory=list)


class TramiteRanEventoCreate(AuditInput):
    ordinal: int = Field(gt=0)
    id_tipo_evento: int = Field(gt=0)
    fecha_evento: date | None = None
    numero_solicitud: str | None = Field(default=None, max_length=150)
    resultado: str | None = Field(default=None, max_length=250)
    calificacion: str | None = None
    folio_referencia: str | None = Field(default=None, max_length=200)
    id_documento: int | None = Field(default=None, gt=0)


class TramiteRanEventoUpdate(AuditInput):
    id_tipo_evento: int | None = Field(default=None, gt=0)
    fecha_evento: date | None = None
    numero_solicitud: str | None = Field(default=None, max_length=150)
    resultado: str | None = Field(default=None, max_length=250)
    calificacion: str | None = None
    folio_referencia: str | None = Field(default=None, max_length=200)
    id_documento: int | None = Field(default=None, gt=0)


class TramiteRanEventoResponse(TramiteRanEventoCreate, AuditRead):
    id_evento_ran: int
    id_tramite_ran: int


class TramiteRanCreate(AuditInput):
    id_asamblea: int | None = Field(default=None, gt=0)
    id_convenio: int | None = Field(default=None, gt=0)
    id_orv: int | None = Field(default=None, gt=0)
    fecha_programada_ingreso: date | None = None
    referencia_expediente: str | None = Field(default=None, max_length=150)
    eventos: list[TramiteRanEventoCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_objetivo(self):
        if sum(item is not None for item in (self.id_asamblea,self.id_convenio,self.id_orv)) != 1:
            raise ValueError("El trámite RAN requiere exactamente un objetivo tipado")
        if len({item.ordinal for item in self.eventos}) != len(self.eventos):
            raise ValueError("Los ordinales RAN no pueden repetirse")
        return self


class TramiteRanResponse(TramiteRanCreate, AuditRead):
    id_tramite_ran: int
    id_proyecto_nucleo: int | None = None
    id_nucleo: int | None = None
    eventos: list[TramiteRanEventoResponse] = Field(default_factory=list)


class TramiteFifonafeEventoCreate(AuditInput):
    ordinal: int = Field(gt=0)
    id_tipo_evento: int = Field(gt=0)
    origen: str | None = Field(default=None, max_length=200)
    destino: str | None = Field(default=None, max_length=200)
    numero_oficio: str | None = Field(default=None, max_length=150)
    fecha_oficio: date | None = None
    id_documento: int | None = Field(default=None, gt=0)


class TramiteFifonafeEventoResponse(TramiteFifonafeEventoCreate, AuditRead):
    id_evento_fifonafe: int
    id_tramite_fifonafe: int


class TramiteFifonafeCreate(AuditInput):
    ids_afectacion: list[int] = Field(min_length=1)
    estatus: Literal["programado", "pendiente", "completo", "cancelado", "otro"] = "pendiente"
    acuse_fifonafe_fecha: date | None = None
    hay_conflictos: bool | None = None
    resultado_no_conflictos: str | None = None
    eventos: list[TramiteFifonafeEventoCreate] = Field(default_factory=list)

    @field_validator("ids_afectacion")
    @classmethod
    def validar_ids(cls, value: list[int]) -> list[int]:
        if any(item <= 0 for item in value) or len(value) != len(set(value)):
            raise ValueError("Las afectaciones deben ser IDs positivos únicos")
        return value


class TramiteFifonafeUpdate(AuditInput):
    estatus: Literal["programado", "pendiente", "completo", "cancelado", "otro"] | None = None
    acuse_fifonafe_fecha: date | None = None
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
    no_oficio_fifonafe_a_dgaopr: str | None = None
    fecha_oficio_fifonafe_a_dgaopr: date | None = None
    no_oficio_dgaopr_a_representacion: str | None = None
    fecha_oficio_dgaopr_a_representacion: date | None = None
    no_oficio_respuesta_representacion_a_dgaopr: str | None = None
    fecha_oficio_respuesta_representacion_a_dgaopr: date | None = None
    no_oficio_respuesta_dgaopr_a_fifonafe: str | None = None
    fecha_oficio_respuesta_dgaopr_a_fifonafe: date | None = None
    afectaciones: list[TramiteFifonafeAfectacionResponse] = Field(default_factory=list)
    eventos: list[TramiteFifonafeEventoResponse] = Field(default_factory=list)


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
    entidad_tipo: str
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
    valor_normalizado: str | None = None
    mensajes: list[Any] = Field(default_factory=list)
    id_importacion_tabular: int | None = Field(default=None, gt=0)
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


class RequisitoDocumentalCreate(AuditInput):
    codigo: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=80)
    nombre: str = Field(min_length=1, max_length=250)
    descripcion: str | None = None
    contexto: str = Field(default="general", min_length=1, max_length=80)
    obligatorio: bool = False
    orden: int = 0
    fuente: str | None = Field(default=None, max_length=250)
    vigencia_inicio: date | None = None
    vigencia_fin: date | None = None


class RequisitoDocumentalResponse(RequisitoDocumentalCreate, AuditRead):
    id_requisito: int


class ExpedienteRequisitoCreate(AuditInput):
    id_afectacion: int | None = Field(default=None, gt=0)
    id_requisito: int = Field(gt=0)
    id_estado: int = Field(gt=0)
    id_documento: int | None = Field(default=None, gt=0)
    detalle: str | None = None


class ExpedienteRequisitoUpdate(AuditInput):
    id_estado: int | None = Field(default=None, gt=0)
    id_documento: int | None = Field(default=None, gt=0)
    detalle: str | None = None


class ExpedienteRequisitoResponse(ExpedienteRequisitoCreate, AuditRead):
    id_expediente_requisito: int
    id_proyecto_nucleo: int


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
