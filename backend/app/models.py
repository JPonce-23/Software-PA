"""SQLAlchemy mappings for the ProyectoNucleo target model (migrations 031-033)."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CHAR,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from .database import Base


class AuditableMixin:
    """Columns shared by target-domain tables with logical deletion."""

    activo = Column(Boolean, nullable=False, default=True, server_default="true")
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    creado_por = Column(Integer, ForeignKey("usuario.id_usuario"))
    actualizado_en = Column(DateTime(timezone=True))
    actualizado_por = Column(Integer, ForeignKey("usuario.id_usuario"))
    fecha_baja = Column(DateTime(timezone=True))
    id_usuario_baja = Column(Integer, ForeignKey("usuario.id_usuario"))
    motivo_baja = Column(Text)
    observaciones = Column(Text)


class EntidadFederativa(Base):
    __tablename__ = "entidad_federativa"

    id_entidad = Column(Integer, primary_key=True)
    clave_inegi = Column(CHAR(2), nullable=False, unique=True)
    nombre = Column(String(100), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)

    municipios = relationship("Municipio", back_populates="entidad", lazy="selectin")


class Municipio(Base):
    __tablename__ = "municipio"

    id_municipio = Column(Integer, primary_key=True)
    id_entidad = Column(Integer, ForeignKey("entidad_federativa.id_entidad"), nullable=False)
    clave_inegi = Column(CHAR(5), nullable=False, unique=True)
    nombre = Column(String(150), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)

    entidad = relationship("EntidadFederativa", back_populates="municipios")
    nucleos = relationship("NucleoAgrario", back_populates="municipio", lazy="selectin")


class CatalogoOperativo(Base, AuditableMixin):
    __tablename__ = "catalogo_operativo"

    id_catalogo_opcion = Column(BigInteger, primary_key=True)
    tipo_catalogo = Column(String(50), nullable=False)
    codigo = Column(String(80), nullable=False)
    nombre = Column(String(250), nullable=False)
    descripcion = Column(Text)
    orden = Column(Integer, nullable=False, default=0)
    fuente = Column(String(250))
    vigencia_inicio = Column(Date)
    vigencia_fin = Column(Date)

    aliases = relationship(
        "CatalogoOperativoAlias", back_populates="opcion", lazy="selectin"
    )


class CatalogoOperativoAlias(Base, AuditableMixin):
    __tablename__ = "catalogo_operativo_alias"

    id_catalogo_alias = Column(BigInteger, primary_key=True)
    id_catalogo_opcion = Column(
        BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion"), nullable=False
    )
    alias = Column(String(300), nullable=False)
    alias_normalizado = Column(String(300), nullable=False)
    fuente = Column(String(250))

    opcion = relationship("CatalogoOperativo", back_populates="aliases")


class Usuario(Base):
    """Existing authentication principal retained by migration 031."""

    __tablename__ = "usuario"

    id_usuario = Column(Integer, primary_key=True)
    nombre = Column(String(250), nullable=False)
    apellido_paterno = Column(String(250), nullable=False)
    apellido_materno = Column(String(250))
    correo = Column(String(320), nullable=False, unique=True)
    contrasena_hash = Column(String(255), nullable=False)
    rol = Column(String(30), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_alta = Column(DateTime(timezone=True), nullable=False)
    fecha_baja = Column(DateTime(timezone=True))
    id_usuario_baja = Column(Integer)
    motivo_baja = Column(Text)
    fecha_reactivacion = Column(DateTime(timezone=True))
    id_usuario_reactivacion = Column(Integer)
    motivo_reactivacion = Column(Text)
    observaciones = Column(Text)


class EstadoAutenticacionUsuario(Base):
    __tablename__ = "estado_autenticacion_usuario"

    id_usuario = Column(
        Integer,
        ForeignKey("usuario.id_usuario", ondelete="RESTRICT"),
        primary_key=True,
    )
    intentos_fallidos = Column(SmallInteger, nullable=False, default=0)
    bloqueado_hasta = Column(DateTime(timezone=True))
    ultimo_acceso_en = Column(DateTime(timezone=True))
    actualizado_en = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SesionUsuario(Base):
    __tablename__ = "sesion_usuario"

    id_sesion = Column(BigInteger, primary_key=True)
    id_usuario = Column(
        Integer,
        ForeignKey("usuario.id_usuario", ondelete="RESTRICT"),
        nullable=False,
    )
    token_hash = Column(String(64), nullable=False, unique=True)
    csrf_hash = Column(String(64), nullable=False)
    fecha_creacion = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ultima_actividad = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expira_en = Column(DateTime(timezone=True), nullable=False)
    revocada_en = Column(DateTime(timezone=True))
    id_usuario_revoca = Column(
        Integer, ForeignKey("usuario.id_usuario", ondelete="RESTRICT")
    )
    motivo_revocacion = Column(String(100))
    ip_creacion = Column(INET)
    user_agent_creacion = Column(String(512))


class EventoAcceso(Base):
    __tablename__ = "evento_acceso"

    id_evento = Column(BigInteger, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario", ondelete="RESTRICT"))
    id_usuario_actor = Column(
        Integer, ForeignKey("usuario.id_usuario", ondelete="RESTRICT")
    )
    id_sesion = Column(
        BigInteger, ForeignKey("sesion_usuario.id_sesion", ondelete="RESTRICT")
    )
    tipo_evento = Column(String(40), nullable=False)
    motivo_codigo = Column(String(50), nullable=False)
    detalle = Column(String(200))
    fecha_hora = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ip_origen = Column(INET)
    user_agent = Column(String(512))
    txid_registro = Column(
        BigInteger, nullable=False, server_default=func.txid_current()
    )


class Proyecto(Base, AuditableMixin):
    __tablename__ = "proyecto"

    id_proyecto = Column(Integer, primary_key=True)
    clave_proyecto = Column(String(30), nullable=False, unique=True)
    nombre_proyecto = Column(String(200), nullable=False)
    descripcion = Column(Text)
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)

    nucleos = relationship("ProyectoNucleo", back_populates="proyecto", lazy="selectin")
    trazos = relationship("TrazoProyecto", back_populates="proyecto", lazy="selectin")
    asignaciones = relationship(
        "UsuarioProyecto", back_populates="proyecto", lazy="selectin"
    )


class NucleoAgrario(Base, AuditableMixin):
    __tablename__ = "nucleo_agrario"

    id_nucleo = Column(Integer, primary_key=True)
    id_municipio = Column(
        Integer, ForeignKey("municipio.id_municipio"), nullable=False
    )
    nombre_nucleo = Column(String(300), nullable=False)
    tipo_nucleo = Column(String(20), nullable=False)
    id_tipo_tenencia = Column(
        BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion"), nullable=False
    )
    comunidad_indigena = Column(Boolean)
    geometria_poligono = Column(Geometry("MULTIPOLYGON", srid=4326))
    fuente_geometria = Column(String(250))
    fecha_fuente_geometria = Column(Date)
    fuente_datos = Column(String(120))
    id_entidad_fuente = Column(String(120))
    id_municipio_fuente = Column(String(120))
    id_nucleo_fuente = Column(String(120))
    alcance_identidad_fuente = Column(String(20))

    municipio = relationship("Municipio", back_populates="nucleos")
    proyectos = relationship("ProyectoNucleo", back_populates="nucleo", lazy="selectin")
    orvs = relationship("Orv", back_populates="nucleo", lazy="selectin")
    padrones = relationship("PadronHistorial", back_populates="nucleo", lazy="selectin")
    parcelas = relationship("Parcela", back_populates="nucleo", lazy="selectin")
    tipo_tenencia = relationship("CatalogoOperativo", foreign_keys=[id_tipo_tenencia])


class ProyectoNucleo(Base, AuditableMixin):
    __tablename__ = "proyecto_nucleo"

    id_proyecto_nucleo = Column(Integer, primary_key=True)
    id_proyecto = Column(Integer, ForeignKey("proyecto.id_proyecto"), nullable=False)
    id_nucleo = Column(
        Integer, ForeignKey("nucleo_agrario.id_nucleo"), nullable=False
    )
    residencia = Column(String(300))
    id_residencia = Column(
        BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion")
    )
    total_cops_planeados = Column(Integer)
    responsable_nombre = Column(String(300))
    contacto = Column(String(150))

    proyecto = relationship("Proyecto", back_populates="nucleos")
    nucleo = relationship("NucleoAgrario", back_populates="proyectos")
    referencias = relationship(
        "ProyectoNucleoReferencia", back_populates="proyecto_nucleo", lazy="selectin"
    )
    actividades = relationship(
        "ActividadCampo", back_populates="proyecto_nucleo", lazy="selectin"
    )
    afectaciones = relationship(
        "Afectacion", back_populates="proyecto_nucleo", lazy="selectin"
    )
    asambleas = relationship(
        "Asamblea", back_populates="proyecto_nucleo", lazy="selectin"
    )
    convenios = relationship(
        "Convenio", back_populates="proyecto_nucleo", lazy="selectin"
    )
    tramites_fifonafe = relationship(
        "TramiteFifonafe", back_populates="proyecto_nucleo", lazy="selectin"
    )
    residencia_catalogo = relationship("CatalogoOperativo", foreign_keys=[id_residencia])
    responsables = relationship(
        "ProyectoNucleoResponsable", back_populates="proyecto_nucleo", lazy="selectin"
    )
    tramites_ran = relationship(
        "TramiteRan", back_populates="proyecto_nucleo", lazy="selectin"
    )


class ProyectoNucleoResponsable(Base, AuditableMixin):
    __tablename__ = "proyecto_nucleo_responsable"

    id_responsable = Column(BigInteger, primary_key=True)
    id_proyecto_nucleo = Column(
        Integer, ForeignKey("proyecto_nucleo.id_proyecto_nucleo"), nullable=False
    )
    nombre = Column(String(300), nullable=False)
    cargo = Column(String(200))
    contacto = Column(String(200))
    vigencia_inicio = Column(Date)
    vigencia_fin = Column(Date)
    es_principal = Column(Boolean, nullable=False, default=False)

    proyecto_nucleo = relationship("ProyectoNucleo", back_populates="responsables")


class ProyectoNucleoReferencia(Base, AuditableMixin):
    __tablename__ = "proyecto_nucleo_referencia"

    id_referencia = Column(Integer, primary_key=True)
    id_proyecto_nucleo = Column(
        Integer, ForeignKey("proyecto_nucleo.id_proyecto_nucleo"), nullable=False
    )
    tipo_referencia = Column(String(30), nullable=False)
    valor = Column(String(150), nullable=False)
    es_principal = Column(Boolean, nullable=False, default=False)

    proyecto_nucleo = relationship("ProyectoNucleo", back_populates="referencias")


class Persona(Base, AuditableMixin):
    __tablename__ = "persona"

    id_persona = Column(Integer, primary_key=True)
    curp = Column(String(18))
    rfc = Column(String(13))
    nombre = Column(String(300), nullable=False)
    apellido_paterno = Column(String(200))
    apellido_materno = Column(String(200))
    telefono = Column(String(30))
    correo_electronico = Column(String(320))
    datos_identidad_incompletos = Column(Boolean, nullable=False, default=False)
    origen_registro = Column(
        String(40), nullable=False, default="captura_sistema"
    )

    participaciones_orv = relationship(
        "OrvIntegrante", back_populates="persona", lazy="selectin"
    )
    titularidades = relationship(
        "ParcelaTitular", back_populates="persona", lazy="selectin"
    )


class Orv(Base, AuditableMixin):
    __tablename__ = "orv"

    id_orv = Column(Integer, primary_key=True)
    id_nucleo = Column(
        Integer, ForeignKey("nucleo_agrario.id_nucleo"), nullable=False
    )
    numero_orv = Column(String(50))
    inicio_vigencia = Column(Date)
    fin_vigencia = Column(Date)
    estatus_fuente = Column(String(80))
    id_estado_registral = Column(
        BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion")
    )
    acta_eleccion_inscrita_ran = Column(Boolean)
    fecha_inscripcion_acta_ran = Column(Date)

    nucleo = relationship("NucleoAgrario", back_populates="orvs")
    integrantes = relationship(
        "OrvIntegrante", back_populates="orv", lazy="selectin"
    )
    estado_registral = relationship("CatalogoOperativo", foreign_keys=[id_estado_registral])
    tramites_ran = relationship("TramiteRan", back_populates="orv", lazy="selectin")


class OrvIntegrante(Base, AuditableMixin):
    __tablename__ = "orv_integrante"

    id_orv_integrante = Column(Integer, primary_key=True)
    id_orv = Column(Integer, ForeignKey("orv.id_orv"), nullable=False)
    id_persona = Column(Integer, ForeignKey("persona.id_persona"), nullable=False)
    cargo = Column(String(80))
    id_organo = Column(BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion"))
    id_cargo = Column(BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion"))
    id_calidad = Column(BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion"))
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)

    orv = relationship("Orv", back_populates="integrantes")
    persona = relationship("Persona", back_populates="participaciones_orv")
    organo = relationship("CatalogoOperativo", foreign_keys=[id_organo])
    cargo_catalogo = relationship("CatalogoOperativo", foreign_keys=[id_cargo])
    calidad = relationship("CatalogoOperativo", foreign_keys=[id_calidad])


class PadronHistorial(Base, AuditableMixin):
    __tablename__ = "padron_historial"

    id_padron = Column(Integer, primary_key=True)
    id_nucleo = Column(
        Integer, ForeignKey("nucleo_agrario.id_nucleo"), nullable=False
    )
    fecha_padron = Column(Date)
    numero_ejidatarios_comuneros = Column(Integer)
    fuente = Column(String(250))
    id_documento = Column(Integer, ForeignKey("documento.id_documento"))

    nucleo = relationship("NucleoAgrario", back_populates="padrones")
    asambleas = relationship("Asamblea", back_populates="padron", lazy="selectin")


class Parcela(Base, AuditableMixin):
    __tablename__ = "parcela"

    id_parcela = Column(Integer, primary_key=True)
    id_nucleo = Column(
        Integer, ForeignKey("nucleo_agrario.id_nucleo"), nullable=False
    )
    tipo_parcela = Column(String(30), nullable=False)
    no_parcela = Column(String(80))
    no_parcela_ppt = Column(String(80))
    certificado_parcelario = Column(String(120))
    folio_derechos = Column(String(120))
    constancia_vigencia_fecha = Column(Date)
    geometria_poligono = Column(Geometry("MULTIPOLYGON", srid=4326))
    fuente_geometria = Column(String(250))
    fecha_fuente_geometria = Column(Date)

    nucleo = relationship("NucleoAgrario", back_populates="parcelas")
    titulares = relationship(
        "ParcelaTitular", back_populates="parcela", lazy="selectin"
    )
    afectaciones = relationship(
        "Afectacion", back_populates="parcela", lazy="selectin"
    )


class ParcelaTitular(Base, AuditableMixin):
    __tablename__ = "parcela_titular"

    id_parcela_titular = Column(Integer, primary_key=True)
    id_parcela = Column(Integer, ForeignKey("parcela.id_parcela"), nullable=False)
    id_persona = Column(Integer, ForeignKey("persona.id_persona"), nullable=False)
    tipo_derecho = Column(String(50), nullable=False)
    porcentaje_participacion = Column(Numeric(7, 4))
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)

    parcela = relationship("Parcela", back_populates="titulares")
    persona = relationship("Persona", back_populates="titularidades")


class ActividadCampo(Base, AuditableMixin):
    __tablename__ = "actividad_campo"

    id_actividad = Column(Integer, primary_key=True)
    id_proyecto_nucleo = Column(
        Integer, ForeignKey("proyecto_nucleo.id_proyecto_nucleo"), nullable=False
    )
    tipo_actividad = Column(String(30), nullable=False)
    contexto_actividad = Column(String(40), nullable=False, default="general")
    fecha_programada = Column(Date)
    fecha_realizada = Column(Date)
    responsable = Column(String(300))
    resultado = Column(Text)

    proyecto_nucleo = relationship("ProyectoNucleo", back_populates="actividades")


class Afectacion(Base, AuditableMixin):
    __tablename__ = "afectacion"

    id_afectacion = Column(Integer, primary_key=True)
    id_proyecto_nucleo = Column(
        Integer, ForeignKey("proyecto_nucleo.id_proyecto_nucleo"), nullable=False
    )
    id_parcela = Column(Integer, ForeignKey("parcela.id_parcela"))
    tipo_afectacion = Column(String(20), nullable=False)
    destino_superficie = Column(String(100))
    no_parcela_solar = Column(String(100))
    superficie_preliminar_ha = Column(Numeric(14, 6))
    superficie_afectada_ha = Column(Numeric(14, 6))
    situacion = Column(String(100))
    condicion_especial = Column(String(50))
    descripcion_condicion = Column(Text)
    avaluo_monto = Column(Numeric(18, 2))
    avaluo_fecha = Column(Date)
    avaluo_referencia = Column(String(150))
    avaluo_institucion = Column(String(150))

    proyecto_nucleo = relationship("ProyectoNucleo", back_populates="afectaciones")
    parcela = relationship("Parcela", back_populates="afectaciones")
    convenios = relationship(
        "ConvenioAfectacion", back_populates="afectacion", lazy="selectin"
    )
    tramites_fifonafe = relationship(
        "TramiteFifonafeAfectacion", back_populates="afectacion", lazy="selectin"
    )
    indemnizacion = relationship(
        "Indemnizacion", back_populates="afectacion", uselist=False, lazy="selectin"
    )
    bienes = relationship(
        "BienAfectado", back_populates="afectacion", lazy="selectin"
    )


class BienAfectado(Base, AuditableMixin):
    __tablename__ = "bien_afectado"

    id_bien_afectado = Column(BigInteger, primary_key=True)
    id_afectacion = Column(
        Integer, ForeignKey("afectacion.id_afectacion"), nullable=False
    )
    id_tipo_gestion = Column(
        BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion")
    )
    id_destino_superficie = Column(
        BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion")
    )
    id_tipo_cop_operativo = Column(
        BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion")
    )
    id_parcela = Column(Integer, ForeignKey("parcela.id_parcela"))
    tipo_tierra = Column(String(120))
    referencia_alfanumerica = Column(String(150))
    titularidad = Column(String(250))
    detalle = Column(Text)
    superficie_preliminar_ha = Column(Numeric(14, 6))
    superficie_afectada_ha = Column(Numeric(14, 6))
    superficie_valor_original = Column(String(120))
    superficie_formato_origen = Column(String(50))
    fuente = Column(String(250))

    afectacion = relationship("Afectacion", back_populates="bienes")
    tipo_gestion = relationship("CatalogoOperativo", foreign_keys=[id_tipo_gestion])
    destino_superficie = relationship(
        "CatalogoOperativo", foreign_keys=[id_destino_superficie]
    )
    tipo_cop_operativo = relationship(
        "CatalogoOperativo", foreign_keys=[id_tipo_cop_operativo]
    )
    parcela = relationship("Parcela", foreign_keys=[id_parcela])


class Asamblea(Base, AuditableMixin):
    __tablename__ = "asamblea"

    id_asamblea = Column(Integer, primary_key=True)
    id_proyecto_nucleo = Column(
        Integer, ForeignKey("proyecto_nucleo.id_proyecto_nucleo"), nullable=False
    )
    id_padron = Column(Integer, ForeignKey("padron_historial.id_padron"))
    tipo_asamblea = Column(String(40), nullable=False)
    contexto_proceso = Column(String(40))
    id_tipo_asamblea = Column(
        BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion"), nullable=False
    )
    id_contexto_asamblea = Column(
        BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion")
    )
    proposito = Column(Text)
    fecha_expedicion_primera = Column(Date)
    fecha_programada_primera = Column(Date)
    fecha_expedicion_segunda = Column(Date)
    fecha_programada_segunda = Column(Date)
    fecha_realizada = Column(Date)
    resultado = Column(String(50))
    fecha_programada_ingreso_ran = Column(Date)
    fecha_ingreso_ran = Column(Date)
    numero_solicitud_ran = Column(String(120))
    calificacion_registral_ran = Column(Text)
    fecha_inscripcion_ran = Column(Date)

    proyecto_nucleo = relationship("ProyectoNucleo", back_populates="asambleas")
    padron = relationship("PadronHistorial", back_populates="asambleas")
    convenios_autorizados = relationship(
        "Convenio", back_populates="asamblea_autorizacion", lazy="selectin"
    )
    tipo_asamblea_catalogo = relationship(
        "CatalogoOperativo", foreign_keys=[id_tipo_asamblea]
    )
    contexto_asamblea_catalogo = relationship(
        "CatalogoOperativo", foreign_keys=[id_contexto_asamblea]
    )
    convocatorias = relationship(
        "AsambleaConvocatoria", back_populates="asamblea", lazy="selectin"
    )
    tramites_ran = relationship(
        "TramiteRan", back_populates="asamblea", lazy="selectin"
    )


class AsambleaConvocatoria(Base, AuditableMixin):
    __tablename__ = "asamblea_convocatoria"

    id_convocatoria = Column(BigInteger, primary_key=True)
    id_asamblea = Column(Integer, ForeignKey("asamblea.id_asamblea"), nullable=False)
    ordinal = Column(Integer, nullable=False)
    fecha_expedicion = Column(Date)
    fecha_programada = Column(Date)
    fecha_realizacion = Column(Date)
    id_resultado = Column(
        BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion")
    )
    observaciones_resultado = Column(Text)
    id_documento = Column(Integer, ForeignKey("documento.id_documento"))

    asamblea = relationship("Asamblea", back_populates="convocatorias")
    resultado_catalogo = relationship("CatalogoOperativo", foreign_keys=[id_resultado])


class Convenio(Base, AuditableMixin):
    __tablename__ = "convenio"

    id_convenio = Column(Integer, primary_key=True)
    id_proyecto_nucleo = Column(
        Integer, ForeignKey("proyecto_nucleo.id_proyecto_nucleo"), nullable=False
    )
    ambito = Column(String(20), nullable=False)
    tipo_instrumento = Column(String(20), nullable=False, default="convenio")
    tipo_convenio = Column(String(40))
    modalidad_especial = Column(String(30))
    descripcion_modalidad = Column(Text)
    descripcion_instrumento = Column(Text)
    consecutivo = Column(Integer, nullable=False, default=1)
    id_convenio_padre = Column(Integer, ForeignKey("convenio.id_convenio"))
    id_asamblea_autorizacion = Column(Integer, ForeignKey("asamblea.id_asamblea"))
    fecha_programada_firma = Column(Date)
    fecha_firma = Column(Date)
    monto_90 = Column(Numeric(18, 2))
    monto_100 = Column(Numeric(18, 2))
    monto_bdt = Column(Numeric(18, 2))
    superficie_ha = Column(Numeric(14, 6))
    fecha_programada_ingreso_ran = Column(Date)
    ingreso_ran_fecha = Column(Date)
    numero_solicitud_ingreso = Column(String(120))
    calificacion_registral = Column(Text)
    fecha_inscripcion_ran = Column(Date)

    proyecto_nucleo = relationship("ProyectoNucleo", back_populates="convenios")
    padre = relationship(
        "Convenio", remote_side=[id_convenio], back_populates="hijos"
    )
    hijos = relationship("Convenio", back_populates="padre", lazy="selectin")
    asamblea_autorizacion = relationship(
        "Asamblea", back_populates="convenios_autorizados"
    )
    afectaciones = relationship(
        "ConvenioAfectacion", back_populates="convenio", lazy="selectin"
    )
    tramites_ran = relationship(
        "TramiteRan", back_populates="convenio", lazy="selectin"
    )


class ConvenioAfectacion(Base, AuditableMixin):
    __tablename__ = "convenio_afectacion"

    id_convenio_afectacion = Column(Integer, primary_key=True)
    id_convenio = Column(Integer, ForeignKey("convenio.id_convenio"), nullable=False)
    id_afectacion = Column(
        Integer, ForeignKey("afectacion.id_afectacion"), nullable=False
    )
    rol = Column(String(20), nullable=False, default="principal")

    convenio = relationship("Convenio", back_populates="afectaciones")
    afectacion = relationship("Afectacion", back_populates="convenios")


class TramiteRan(Base, AuditableMixin):
    __tablename__ = "tramite_ran"

    id_tramite_ran = Column(BigInteger, primary_key=True)
    id_proyecto_nucleo = Column(
        Integer, ForeignKey("proyecto_nucleo.id_proyecto_nucleo"), nullable=False
    )
    id_asamblea = Column(Integer, ForeignKey("asamblea.id_asamblea"))
    id_convenio = Column(Integer, ForeignKey("convenio.id_convenio"))
    id_orv = Column(Integer, ForeignKey("orv.id_orv"))
    fecha_programada_ingreso = Column(Date)
    referencia_expediente = Column(String(150))

    proyecto_nucleo = relationship("ProyectoNucleo", back_populates="tramites_ran")
    asamblea = relationship("Asamblea", back_populates="tramites_ran")
    convenio = relationship("Convenio", back_populates="tramites_ran")
    orv = relationship("Orv", back_populates="tramites_ran")
    eventos = relationship(
        "TramiteRanEvento", back_populates="tramite", lazy="selectin"
    )


class TramiteRanEvento(Base, AuditableMixin):
    __tablename__ = "tramite_ran_evento"

    id_evento_ran = Column(BigInteger, primary_key=True)
    id_tramite_ran = Column(
        BigInteger, ForeignKey("tramite_ran.id_tramite_ran"), nullable=False
    )
    ordinal = Column(Integer, nullable=False)
    id_tipo_evento = Column(
        BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion"), nullable=False
    )
    fecha_evento = Column(Date)
    numero_solicitud = Column(String(150))
    resultado = Column(String(250))
    calificacion = Column(Text)
    folio_referencia = Column(String(200))
    id_documento = Column(Integer, ForeignKey("documento.id_documento"))

    tramite = relationship("TramiteRan", back_populates="eventos")
    tipo_evento = relationship("CatalogoOperativo", foreign_keys=[id_tipo_evento])


class TramiteFifonafe(Base, AuditableMixin):
    __tablename__ = "tramite_fifonafe"

    id_tramite_fifonafe = Column(Integer, primary_key=True)
    id_proyecto_nucleo = Column(
        Integer, ForeignKey("proyecto_nucleo.id_proyecto_nucleo"), nullable=False
    )
    ambito = Column(String(20), nullable=False)
    estatus = Column(String(30), nullable=False, default="pendiente")
    acuse_fifonafe_fecha = Column(Date)
    no_oficio_fifonafe_a_dgaopr = Column(String(100))
    fecha_oficio_fifonafe_a_dgaopr = Column(Date)
    no_oficio_dgaopr_a_representacion = Column(String(100))
    fecha_oficio_dgaopr_a_representacion = Column(Date)
    no_oficio_respuesta_representacion_a_dgaopr = Column(String(100))
    fecha_oficio_respuesta_representacion_a_dgaopr = Column(Date)
    no_oficio_respuesta_dgaopr_a_fifonafe = Column(String(100))
    fecha_oficio_respuesta_dgaopr_a_fifonafe = Column(Date)
    hay_conflictos = Column(Boolean)
    resultado_no_conflictos = Column(Text)

    proyecto_nucleo = relationship(
        "ProyectoNucleo", back_populates="tramites_fifonafe"
    )
    afectaciones = relationship(
        "TramiteFifonafeAfectacion", back_populates="tramite", lazy="selectin"
    )
    eventos = relationship(
        "TramiteFifonafeEvento", back_populates="tramite", lazy="selectin"
    )


class TramiteFifonafeEvento(Base, AuditableMixin):
    __tablename__ = "tramite_fifonafe_evento"

    id_evento_fifonafe = Column(BigInteger, primary_key=True)
    id_tramite_fifonafe = Column(
        Integer, ForeignKey("tramite_fifonafe.id_tramite_fifonafe"), nullable=False
    )
    ordinal = Column(Integer, nullable=False)
    id_tipo_evento = Column(
        BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion"), nullable=False
    )
    origen = Column(String(200))
    destino = Column(String(200))
    numero_oficio = Column(String(150))
    fecha_oficio = Column(Date)
    id_documento = Column(Integer, ForeignKey("documento.id_documento"))

    tramite = relationship("TramiteFifonafe", back_populates="eventos")
    tipo_evento = relationship("CatalogoOperativo", foreign_keys=[id_tipo_evento])


class TramiteFifonafeAfectacion(Base, AuditableMixin):
    __tablename__ = "tramite_fifonafe_afectacion"

    id_tramite_fifonafe_afectacion = Column(Integer, primary_key=True)
    id_tramite_fifonafe = Column(
        Integer,
        ForeignKey("tramite_fifonafe.id_tramite_fifonafe"),
        nullable=False,
    )
    id_afectacion = Column(
        Integer, ForeignKey("afectacion.id_afectacion"), nullable=False
    )

    tramite = relationship("TramiteFifonafe", back_populates="afectaciones")
    afectacion = relationship("Afectacion", back_populates="tramites_fifonafe")


class Indemnizacion(Base, AuditableMixin):
    __tablename__ = "indemnizacion"

    id_indemnizacion = Column(Integer, primary_key=True)
    id_afectacion = Column(
        Integer, ForeignKey("afectacion.id_afectacion"), nullable=False
    )
    estatus = Column(String(30), nullable=False, default="pendiente")
    descripcion_estatus = Column(Text)
    fecha_programada = Column(Date)
    fecha_resolucion = Column(Date)
    fecha_entrega_expediente_pa = Column(Date)

    afectacion = relationship("Afectacion", back_populates="indemnizacion")
    pagos = relationship("Pago", back_populates="indemnizacion", lazy="selectin")


class Pago(Base, AuditableMixin):
    __tablename__ = "pago"

    id_pago = Column(Integer, primary_key=True)
    id_indemnizacion = Column(
        Integer, ForeignKey("indemnizacion.id_indemnizacion"), nullable=False
    )
    fecha_pago = Column(Date, nullable=False)
    monto = Column(Numeric(18, 2), nullable=False)
    id_persona_beneficiaria = Column(Integer, ForeignKey("persona.id_persona"))
    beneficiario_nombre = Column(String(300), nullable=False)
    referencia = Column(String(150))
    medio_pago = Column(String(30))

    indemnizacion = relationship("Indemnizacion", back_populates="pagos")
    persona_beneficiaria = relationship("Persona")


class Documento(Base, AuditableMixin):
    __tablename__ = "documento"

    id_documento = Column(Integer, primary_key=True)
    tipo_documento = Column(String(80), nullable=False)
    estado = Column(String(20), nullable=False)
    titulo = Column(String(250))
    fecha_documento = Column(Date)
    numero_folio = Column(String(150))
    descripcion = Column(Text)

    versiones = relationship(
        "DocumentoVersion", back_populates="documento", lazy="selectin"
    )
    vinculos = relationship(
        "DocumentoVinculo", back_populates="documento", lazy="selectin"
    )


class DocumentoVersion(Base):
    __tablename__ = "documento_version"
    __table_args__ = (
        UniqueConstraint(
            "id_documento", "numero_version", name="uq_documento_version"
        ),
        UniqueConstraint("ruta_almacenamiento", name="uq_documento_ruta"),
        UniqueConstraint("id_documento", "hash_sha256", name="uq_documento_hash"),
    )

    id_documento_version = Column(BigInteger, primary_key=True)
    id_documento = Column(
        Integer, ForeignKey("documento.id_documento"), nullable=False
    )
    numero_version = Column(Integer, nullable=False)
    hash_sha256 = Column(CHAR(64), nullable=False)
    tamano_bytes = Column(BigInteger, nullable=False)
    nombre_original = Column(String(255), nullable=False)
    ruta_almacenamiento = Column(Text, nullable=False)
    tipo_mime = Column(String(150))
    fecha_carga = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    id_usuario_carga = Column(
        Integer, ForeignKey("usuario.id_usuario"), nullable=False
    )

    documento = relationship("Documento", back_populates="versiones")


class DocumentoVinculo(Base, AuditableMixin):
    __tablename__ = "documento_vinculo"

    id_documento_vinculo = Column(Integer, primary_key=True)
    id_documento = Column(
        Integer, ForeignKey("documento.id_documento"), nullable=False
    )
    entidad_tipo = Column(String(50), nullable=False)
    entidad_id = Column(Integer, nullable=False)

    documento = relationship("Documento", back_populates="vinculos")


class TrazabilidadFuente(Base):
    __tablename__ = "trazabilidad_fuente"

    id_trazabilidad = Column(BigInteger, primary_key=True)
    entidad_tipo = Column(String(50), nullable=False)
    entidad_id = Column(BigInteger, nullable=False)
    archivo = Column(String(255), nullable=False)
    hoja = Column(String(255))
    fila = Column(Integer)
    columna = Column(String(120))
    valor_original = Column(Text)
    valor_normalizado = Column(Text)
    tratamiento = Column(String(30), nullable=False)
    mensajes = Column(JSONB, nullable=False, default=list)
    id_importacion_tabular = Column(
        BigInteger, ForeignKey("importacion_tabular.id_importacion_tabular")
    )
    registrado_en = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    id_usuario_registro = Column(Integer, ForeignKey("usuario.id_usuario"))


class RequisitoDocumental(Base, AuditableMixin):
    __tablename__ = "requisito_documental"

    id_requisito = Column(BigInteger, primary_key=True)
    codigo = Column(String(80), nullable=False, unique=True)
    nombre = Column(String(250), nullable=False)
    descripcion = Column(Text)
    contexto = Column(String(80), nullable=False, default="general")
    obligatorio = Column(Boolean, nullable=False, default=False)
    orden = Column(Integer, nullable=False, default=0)
    fuente = Column(String(250))
    vigencia_inicio = Column(Date)
    vigencia_fin = Column(Date)

    expedientes = relationship(
        "ExpedienteRequisito", back_populates="requisito", lazy="selectin"
    )


class ExpedienteRequisito(Base, AuditableMixin):
    __tablename__ = "expediente_requisito"

    id_expediente_requisito = Column(BigInteger, primary_key=True)
    id_proyecto_nucleo = Column(
        Integer, ForeignKey("proyecto_nucleo.id_proyecto_nucleo"), nullable=False
    )
    id_afectacion = Column(Integer, ForeignKey("afectacion.id_afectacion"))
    id_requisito = Column(
        BigInteger, ForeignKey("requisito_documental.id_requisito"), nullable=False
    )
    id_estado = Column(
        BigInteger, ForeignKey("catalogo_operativo.id_catalogo_opcion"), nullable=False
    )
    id_documento = Column(Integer, ForeignKey("documento.id_documento"))
    detalle = Column(Text)

    requisito = relationship("RequisitoDocumental", back_populates="expedientes")
    estado = relationship("CatalogoOperativo", foreign_keys=[id_estado])


class ImportacionTabular(Base, AuditableMixin):
    __tablename__ = "importacion_tabular"

    id_importacion_tabular = Column(BigInteger, primary_key=True)
    id_proyecto = Column(Integer, ForeignKey("proyecto.id_proyecto"), nullable=False)
    archivo = Column(String(255), nullable=False)
    sha256 = Column(CHAR(64), nullable=False)
    hoja = Column(String(255), nullable=False)
    filas_detectadas = Column(Integer, nullable=False, default=0)
    filas_procesadas = Column(Integer, nullable=False, default=0)
    advertencias = Column(Integer, nullable=False, default=0)
    errores = Column(Integer, nullable=False, default=0)
    estado = Column(String(30), nullable=False, default="auditado")

    celdas = relationship(
        "ImportacionTabularCelda", back_populates="importacion", lazy="selectin"
    )


class ImportacionTabularCelda(Base):
    __tablename__ = "importacion_tabular_celda"

    id_importacion_celda = Column(BigInteger, primary_key=True)
    id_importacion_tabular = Column(
        BigInteger, ForeignKey("importacion_tabular.id_importacion_tabular"), nullable=False
    )
    fila = Column(Integer, nullable=False)
    columna = Column(String(20), nullable=False)
    encabezado = Column(String(300))
    valor_original = Column(Text)
    valor_normalizado = Column(Text)
    tratamiento = Column(String(30), nullable=False)
    mensajes = Column(JSONB, nullable=False, default=list)
    entidad_tipo = Column(String(50))
    entidad_id = Column(BigInteger)
    registrado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    id_usuario_registro = Column(Integer, ForeignKey("usuario.id_usuario"))

    importacion = relationship("ImportacionTabular", back_populates="celdas")


class UsuarioProyecto(Base, AuditableMixin):
    __tablename__ = "usuario_proyecto"

    id_usuario_proyecto = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False)
    id_proyecto = Column(
        Integer, ForeignKey("proyecto.id_proyecto"), nullable=False
    )
    asignado_por = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False)
    fecha_asignacion = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    usuario = relationship("Usuario", foreign_keys=[id_usuario])
    proyecto = relationship("Proyecto", back_populates="asignaciones")
    usuario_asignador = relationship("Usuario", foreign_keys=[asignado_por])


class Bitacora(Base):
    __tablename__ = "bitacora"

    id_bitacora = Column(BigInteger, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"))
    id_proyecto = Column(Integer, ForeignKey("proyecto.id_proyecto"))
    id_proyecto_nucleo = Column(
        Integer, ForeignKey("proyecto_nucleo.id_proyecto_nucleo")
    )
    id_nucleo = Column(Integer, ForeignKey("nucleo_agrario.id_nucleo"))
    entidad_tipo = Column(String(100), nullable=False)
    entidad_id = Column(BigInteger)
    accion = Column(String(30), nullable=False)
    valor_anterior = Column(JSONB)
    valor_nuevo = Column(JSONB)
    fecha_hora = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ip_origen = Column(INET)
    user_agent = Column(Text)


class TrazoProyecto(Base, AuditableMixin):
    __tablename__ = "trazo_proyecto"
    __table_args__ = (
        UniqueConstraint(
            "id_proyecto", "version", name="uq_trazo_proyecto_version"
        ),
    )

    id_trazo = Column(Integer, primary_key=True)
    id_proyecto = Column(
        Integer, ForeignKey("proyecto.id_proyecto"), nullable=False
    )
    version = Column(Integer, nullable=False)
    geometria_linea = Column(
        Geometry("MULTILINESTRING", srid=4326), nullable=False
    )
    fuente = Column(String(250), nullable=False)
    fecha_fuente = Column(Date)
    fecha_vigencia_inicio = Column(Date, nullable=False)
    fecha_vigencia_fin = Column(Date)

    proyecto = relationship("Proyecto", back_populates="trazos")


class PerfilMapeoImportacion(Base, AuditableMixin):
    __tablename__ = "perfil_mapeo_importacion"

    id_perfil = Column(BigInteger, primary_key=True)
    id_proyecto = Column(Integer, ForeignKey("proyecto.id_proyecto"))
    nombre = Column(String(120), nullable=False)
    fuente = Column(String(250), nullable=False)
    tipo_objetivo = Column(String(30), nullable=False)
    mapeo = Column(JSONB, nullable=False)
    opciones = Column(JSONB, nullable=False, default=dict)
    id_usuario_creacion = Column(
        Integer, ForeignKey("usuario.id_usuario"), nullable=False
    )


class CatalogoAliasTerritorial(Base, AuditableMixin):
    __tablename__ = "catalogo_alias_territorial"

    id_alias = Column(BigInteger, primary_key=True)
    id_entidad = Column(
        Integer, ForeignKey("entidad_federativa.id_entidad"), nullable=False
    )
    alias_nombre = Column(String(200))
    alias_normalizado = Column(String(200), nullable=False)
    alias_clave = Column(String(120))
    id_municipio_destino = Column(
        Integer, ForeignKey("municipio.id_municipio"), nullable=False
    )
    fuente = Column(String(250), nullable=False)
    fecha_vigencia_inicio = Column(Date)
    fecha_vigencia_fin = Column(Date)
    id_usuario_aprobador = Column(
        Integer, ForeignKey("usuario.id_usuario"), nullable=False
    )


class ImportacionArchivo(Base, AuditableMixin):
    __tablename__ = "importacion_archivo"

    id_importacion = Column(BigInteger, primary_key=True)
    id_proyecto = Column(
        Integer, ForeignKey("proyecto.id_proyecto"), nullable=False
    )
    tipo_objetivo = Column(String(30), nullable=False)
    nombre_original = Column(String(255), nullable=False)
    nombre_almacenado = Column(String(255), nullable=False)
    formato_detectado = Column(String(20), nullable=False)
    tamano_bytes = Column(BigInteger, nullable=False)
    sha256 = Column(CHAR(64), nullable=False)
    fuente = Column(String(250), nullable=False)
    fecha_fuente = Column(Date)
    crs_original = Column(Text)
    crs_destino = Column(String(30), nullable=False, default="EPSG:4326")
    columnas_detectadas = Column(JSONB, nullable=False, default=list)
    mapeo = Column(JSONB, nullable=False, default=dict)
    opciones_mapeo = Column(JSONB, nullable=False, default=dict)
    id_perfil = Column(
        BigInteger, ForeignKey("perfil_mapeo_importacion.id_perfil")
    )
    estado = Column(String(40), nullable=False, default="subido")
    total_features = Column(Integer, nullable=False, default=0)
    features_procesados = Column(Integer, nullable=False, default=0)
    validos = Column(Integer, nullable=False, default=0)
    advertencias = Column(Integer, nullable=False, default=0)
    errores = Column(Integer, nullable=False, default=0)
    importados = Column(Integer, nullable=False, default=0)
    descartados = Column(Integer, nullable=False, default=0)
    id_usuario_carga = Column(
        Integer, ForeignKey("usuario.id_usuario"), nullable=False
    )
    fecha_carga = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_procesamiento_inicio = Column(DateTime(timezone=True))
    fecha_procesamiento_fin = Column(DateTime(timezone=True))
    confirmacion_explicita = Column(Boolean, nullable=False, default=False)
    fecha_confirmacion = Column(DateTime(timezone=True))
    id_usuario_confirmacion = Column(
        Integer, ForeignKey("usuario.id_usuario")
    )
    error_codigo = Column(String(80))
    error_detalle = Column(Text)
    reporte = Column(JSONB, nullable=False, default=dict)
    version_control = Column(Integer, nullable=False, default=1)

    perfil = relationship("PerfilMapeoImportacion")
    features = relationship(
        "ImportacionFeature", back_populates="importacion", lazy="selectin"
    )


class ImportacionFeature(Base):
    __tablename__ = "importacion_feature"
    __table_args__ = (
        UniqueConstraint(
            "id_importacion", "indice_feature", name="uq_importacion_feature"
        ),
    )

    id_importacion_feature = Column(BigInteger, primary_key=True)
    id_importacion = Column(
        BigInteger, ForeignKey("importacion_archivo.id_importacion"), nullable=False
    )
    indice_feature = Column(Integer, nullable=False)
    capa_origen = Column(String(200))
    id_externo = Column(String(200))
    tipo_geometria = Column(String(40))
    atributos_originales = Column(JSONB, nullable=False, default=dict)
    atributos_normalizados = Column(JSONB, nullable=False, default=dict)
    geometria_normalizada = Column(Geometry("GEOMETRY", srid=4326))
    estado = Column(String(40), nullable=False, default="pendiente_revision")
    errores = Column(JSONB, nullable=False, default=list)
    advertencias = Column(JSONB, nullable=False, default=list)
    transformaciones = Column(JSONB, nullable=False, default=list)
    advertencias_aceptadas = Column(Boolean, nullable=False, default=False)
    id_usuario_revision = Column(Integer, ForeignKey("usuario.id_usuario"))
    fecha_revision = Column(DateTime(timezone=True))
    registro_destino_id = Column(Integer)
    fecha_procesamiento = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_importacion = Column(DateTime(timezone=True))

    importacion = relationship("ImportacionArchivo", back_populates="features")


class OrvEstado(Base):
    __tablename__ = "vw_orv_estado"

    id_orv = Column(Integer, primary_key=True)
    id_nucleo = Column(Integer)
    numero_orv = Column(String(50))
    inicio_vigencia = Column(Date)
    fin_vigencia = Column(Date)
    estatus_fuente = Column(String(80))
    acta_eleccion_inscrita_ran = Column(Boolean)
    fecha_inscripcion_acta_ran = Column(Date)
    estado_derivado = Column(Text)


class ProyectoNucleoResumen(Base):
    __tablename__ = "vw_proyecto_nucleo_resumen"

    id_proyecto_nucleo = Column(Integer, primary_key=True)
    id_proyecto = Column(Integer)
    clave_proyecto = Column(String(30))
    nombre_proyecto = Column(String(200))
    id_nucleo = Column(Integer)
    nombre_nucleo = Column(String(300))
    tipo_nucleo = Column(String(20))
    comunidad_indigena = Column(Boolean)
    id_entidad = Column(Integer)
    clave_entidad = Column(CHAR(2))
    entidad = Column(String(100))
    id_municipio = Column(Integer)
    clave_municipio = Column(CHAR(5))
    municipio = Column(String(150))
    residencia = Column(String(300))
    responsable_nombre = Column(String(300))
    contacto = Column(String(150))
    consecutivo_principal = Column(String(150))
    actividades = Column(BigInteger)
    asambleas = Column(BigInteger)
    afectaciones_colectivas = Column(BigInteger)
    afectaciones_individuales = Column(BigInteger)
    parcelas = Column(BigInteger)
    convenios = Column(BigInteger)
    tramites_fifonafe = Column(BigInteger)
    activo = Column(Boolean)
    creado_en = Column(DateTime(timezone=True))
    actualizado_en = Column(DateTime(timezone=True))


class DashboardKpi(Base):
    __tablename__ = "vw_dashboard_kpi"

    id_proyecto = Column(Integer, primary_key=True)
    anio = Column(Integer, primary_key=True)
    indicador = Column(Text, primary_key=True)
    programado = Column(BigInteger)
    realizado = Column(BigInteger)
    cantidad = Column(BigInteger)
    superficie_ha = Column(Numeric)
    monto = Column(Numeric)
