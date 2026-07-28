from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import JSONB, INET
from .database import Base

# Mixin for Soft Delete and Auditing fields present in all operational tables
class AuditableMixin:
    fecha_baja = Column(DateTime(timezone=True))
    id_usuario_baja = Column(Integer)
    motivo_baja = Column(String)
    fecha_reactivacion = Column(DateTime(timezone=True))
    id_usuario_reactivacion = Column(Integer)
    motivo_reactivacion = Column(String)
    observaciones = Column(String)

class EntidadFederativa(Base):
    __tablename__ = "entidad_federativa"
    id_entidad = Column(Integer, primary_key=True, index=True)
    clave_inegi = Column(String(2), unique=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    municipios = relationship("Municipio", back_populates="entidad")

class Municipio(Base):
    __tablename__ = "municipio"
    id_municipio = Column(Integer, primary_key=True, index=True)
    id_entidad = Column(Integer, ForeignKey("entidad_federativa.id_entidad"), nullable=False)
    clave_inegi = Column(String(5), unique=True, nullable=False)
    nombre = Column(String(150), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    entidad = relationship("EntidadFederativa", back_populates="municipios")
    nucleos = relationship("NucleoAgrario", back_populates="municipio")

class Proyecto(Base, AuditableMixin):
    __tablename__ = "proyecto"
    id_proyecto = Column(Integer, primary_key=True, index=True)
    clave_proyecto = Column(String(30), unique=True, nullable=False)
    nombre_proyecto = Column(String(200), nullable=False)
    descripcion = Column(String)
    activo = Column(Boolean, default=True, nullable=False)
    fecha_registro = Column(Date, nullable=False)
    tramos = relationship("Tramo", back_populates="proyecto")

class Tramo(Base, AuditableMixin):
    __tablename__ = "tramo"
    __table_args__ = (
        UniqueConstraint("id_proyecto", "clave_tramo", name="uq_tramo_proyecto_clave"),
    )
    id_tramo = Column(Integer, primary_key=True, index=True)
    id_proyecto = Column(Integer, ForeignKey("proyecto.id_proyecto"), nullable=False)
    clave_tramo = Column(String(20), nullable=False)
    nombre_tramo = Column(String(200), nullable=False)
    descripcion = Column(String)
    ancho_total_derecho_via_m = Column(Numeric(6, 2), default=40.00)
    geometria_linea = Column(Geometry(geometry_type='MULTILINESTRING', srid=4326))
    activo = Column(Boolean, default=True, nullable=False)
    fecha_registro = Column(Date, nullable=False)
    proyecto = relationship("Proyecto", back_populates="tramos")

class NucleoAgrario(Base, AuditableMixin):
    __tablename__ = "nucleo_agrario"
    __table_args__ = (CheckConstraint("tipo_nucleo IN ('ejido', 'comunidad')", name='chk_tipo_nucleo'),)
    id_nucleo = Column(Integer, primary_key=True, index=True)
    id_municipio = Column(Integer, ForeignKey("municipio.id_municipio"), nullable=False)
    nombre_nucleo = Column(String(300), nullable=False)
    tipo_nucleo = Column(String(20), nullable=False)
    comunidad_indigena = Column(Boolean, default=False, nullable=False)
    residencia = Column(String(300))
    geometria_poligono = Column(Geometry(geometry_type='MULTIPOLYGON', srid=4326))
    fecha_creacion = Column(DateTime(timezone=True), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    municipio = relationship("Municipio", back_populates="nucleos")

class TramoNucleo(Base, AuditableMixin):
    __tablename__ = "tramo_nucleo"
    id_tramo_nucleo = Column(Integer, primary_key=True, index=True)
    id_tramo = Column(Integer, ForeignKey("tramo.id_tramo"), nullable=False)

    id_nucleo = Column(Integer, ForeignKey("nucleo_agrario.id_nucleo"), nullable=False)
    consecutivo = Column(Integer, nullable=False)
    numero_tramo = Column(String(50))
    geometria_segmento = Column(Geometry(geometry_type='MULTILINESTRING', srid=4326))
    longitud_m = Column(Numeric(14,2))
    es_expropiacion = Column(Boolean, default=False, nullable=False)
    causa_problema = Column(String)
    proyecto_no_afecta_uso_comun = Column(Boolean)
    activo = Column(Boolean, default=True, nullable=False)

class Usuario(Base, AuditableMixin):
    __tablename__ = "usuario"
    id_usuario = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(250), nullable=False)
    apellido_paterno = Column(String(250), nullable=False)
    apellido_materno = Column(String(250))
    correo = Column(String(320), unique=True, nullable=False)
    contrasena_hash = Column(String(255), nullable=False)
    rol = Column(String(30), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    fecha_alta = Column(DateTime(timezone=True), nullable=False)

class Orv(Base, AuditableMixin):
    __tablename__ = "orv"
    id_orv = Column(Integer, primary_key=True, index=True)
    id_nucleo = Column(Integer, ForeignKey("nucleo_agrario.id_nucleo"), nullable=False)
    numero_orv = Column(String(50))
    inicio_vigencia = Column(Date, nullable=False)
    fin_vigencia = Column(Date, nullable=False)
    acta_eleccion_inscrita_ran = Column(Boolean, default=False, nullable=False)
    documentacion_disponible = Column(Boolean, default=False, nullable=False)
    documentacion_faltante = Column(String)
    comisariado_presidente = Column(String(300))
    comisariado_secretario = Column(String(300))
    comisariado_tesorero = Column(String(300))
    consejo_vigilancia_presidente = Column(String(300))
    consejo_vigilancia_secretario1 = Column(String(300))
    consejo_vigilancia_secretario2 = Column(String(300))
    activo = Column(Boolean, default=True, nullable=False)

class PadronHistorial(Base, AuditableMixin):
    __tablename__ = "padron_historial"
    id_padron = Column(Integer, primary_key=True, index=True)
    id_nucleo = Column(Integer, ForeignKey("nucleo_agrario.id_nucleo"), nullable=False)
    fecha_padron = Column(Date, nullable=False)
    numero_ejidatarios_comuneros = Column(Integer, nullable=False)
    id_usuario_registro = Column(Integer, ForeignKey("usuario.id_usuario"))
    fecha_registro = Column(DateTime(timezone=True), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

class Parcela(Base, AuditableMixin):
    __tablename__ = "parcela"
    id_parcela = Column(Integer, primary_key=True, index=True)
    id_nucleo = Column(Integer, ForeignKey("nucleo_agrario.id_nucleo"), nullable=False)
    tipo_parcela = Column(String(30))
    no_parcela_ppt = Column(String(50))
    certificado_parcelario = Column(String(100))
    folio_derechos = Column(String(100))
    constancia_vigencia_fecha = Column(Date)
    nombre_titular = Column(String(300))
    documentacion_disponible = Column(Boolean, default=False, nullable=False)
    documentacion_faltante = Column(String)
    activo = Column(Boolean, default=True, nullable=False)

class Afectacion(Base, AuditableMixin):
    __tablename__ = "afectacion"
    __table_args__ = (CheckConstraint("tipo_afectacion IN ('colectivo', 'individual')", name='chk_tipo_afectacion'),)
    id_afectacion = Column(Integer, primary_key=True, index=True)
    id_nucleo = Column(Integer, ForeignKey("nucleo_agrario.id_nucleo"), nullable=False)
    id_tramo_nucleo = Column(Integer, ForeignKey("tramo_nucleo.id_tramo_nucleo"), nullable=False)
    id_parcela = Column(Integer, ForeignKey("parcela.id_parcela"))
    tipo_afectacion = Column(String(20), nullable=False)
    tipo_tenencia = Column(String(80), nullable=False)
    subtipo_tenencia = Column(String(80))
    destino_superficie = Column(String(80))
    no_parcela_solar = Column(String(100))
    superficie_afectada_ha = Column(Numeric(12,4))
    geometria_afectacion = Column(Geometry(geometry_type='GEOMETRY', srid=4326))
    num_personas_afectadas = Column(Integer)
    situacion_juridica = Column(String)
    documentacion_disponible = Column(Boolean, default=False, nullable=False)
    documentacion_faltante = Column(String)
    origen_registro = Column(String(50), default='captura_sistema', nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

class ActividadCampo(Base, AuditableMixin):
    __tablename__ = "actividad_campo"
    id_actividad = Column(Integer, primary_key=True, index=True)
    id_tramo_nucleo = Column(Integer, ForeignKey("tramo_nucleo.id_tramo_nucleo"), nullable=False)
    tipo_actividad = Column(String(50), nullable=False)
    contexto_proceso = Column(String(50), nullable=False, default='cop_original')
    fecha_programada = Column(Date)
    fecha_realizada = Column(Date)
    resultado = Column(String)
    id_usuario_registro = Column(Integer, ForeignKey("usuario.id_usuario"))
    fecha_registro = Column(DateTime(timezone=True), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

class Asamblea(Base, AuditableMixin):
    __tablename__ = "asamblea"
    __table_args__ = (CheckConstraint("tipo_asamblea IN ('informacion', 'anuencia', 'retiro_fondos', 'conciliacion', 'no_verificativo')", name='chk_tipo_asamblea'),)
    id_asamblea = Column(Integer, primary_key=True, index=True)
    id_nucleo = Column(Integer, nullable=False)
    id_tramo_nucleo = Column(Integer, ForeignKey("tramo_nucleo.id_tramo_nucleo"), nullable=False)
    tipo_asamblea = Column(String(50), nullable=False)
    contexto_proceso = Column(String(50))
    fecha_exp_1a = Column(Date)
    fecha_prog_1a = Column(Date)
    fecha_exp_2a = Column(Date)
    fecha_prog_2a = Column(Date)
    fecha_realizada = Column(Date)
    resultado_anuencia = Column(String(30), default='pendiente', nullable=False)
    estatus_asamblea = Column(String(30))
    ingreso_ran_fecha = Column(Date)
    numero_solicitud_ran = Column(String(100))
    calificacion_registral_ran = Column(String)
    acta_inscripcion_fecha_ran = Column(Date)
    documentacion_disponible = Column(Boolean, default=False, nullable=False)
    documentacion_faltante = Column(String)
    id_padron = Column(Integer, ForeignKey("padron_historial.id_padron"))
    id_usuario_registro = Column(Integer, ForeignKey("usuario.id_usuario"))
    activo = Column(Boolean, default=True, nullable=False)

class Convenio(Base, AuditableMixin):
    __tablename__ = "convenio"
    __table_args__ = (CheckConstraint("tipo_afectacion IN ('colectivo', 'individual')", name='chk_convenio_tipo_afectacion'), CheckConstraint("tipo_convenio IN ('cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias', 'ampliacion', 'ampliacion_remanente')", name='chk_tipo_convenio'),)
    id_convenio = Column(Integer, primary_key=True, index=True)
    id_tramo_nucleo = Column(Integer, ForeignKey("tramo_nucleo.id_tramo_nucleo"), nullable=False)
    id_afectacion = Column(Integer, ForeignKey("afectacion.id_afectacion"), nullable=False)
    id_convenio_padre = Column(Integer, ForeignKey("convenio.id_convenio"))
    id_asamblea_autorizacion = Column(Integer, ForeignKey("asamblea.id_asamblea"))
    tipo_afectacion = Column(String(20), nullable=False)
    tipo_convenio = Column(String(50), nullable=False)
    fecha_firma = Column(Date)
    monto_100 = Column(Numeric(18,2))
    monto_90 = Column(Numeric(18,2))
    monto_bdt = Column(Numeric(18,2))
    superficie_total_ha = Column(Numeric(12,4))
    superficie_real_afectada_ha = Column(Numeric(12,4))
    superficie_adicional_ha = Column(Numeric(12,4))
    superficie_ampliacion_ha = Column(Numeric(12,4))
    ingreso_ran_fecha = Column(Date)
    numero_solicitud_ingreso = Column(String(100))
    calificacion_registral = Column(String)
    convenio_inscrito_fecha_ran = Column(Date)
    documentacion_disponible = Column(Boolean, default=False, nullable=False)
    documentacion_faltante = Column(String)
    id_usuario_registro = Column(Integer, ForeignKey("usuario.id_usuario"))
    activo = Column(Boolean, default=True, nullable=False)

class TramiteFifonafe(Base, AuditableMixin):
    __tablename__ = "tramite_fifonafe"
    __table_args__ = (CheckConstraint("tipo_tramite IN ('indemnizacion', 'informe_no_conflictos')", name='chk_tipo_tramite'),)
    id_tramite_fifonafe = Column(Integer, primary_key=True, index=True)
    id_tramo_nucleo = Column(Integer, ForeignKey("tramo_nucleo.id_tramo_nucleo"), nullable=False)
    id_convenio = Column(Integer, ForeignKey("convenio.id_convenio"))
    id_afectacion = Column(Integer, ForeignKey("afectacion.id_afectacion"))
    tipo_afectacion = Column(String(20), nullable=False)
    tipo_tramite = Column(String(50), nullable=False)
    estatus = Column(String(30), nullable=False, default='pendiente')
    hay_conflictos = Column(Boolean)
    no_oficio_fifonafe_a_dgaopr = Column(String(50))
    no_oficio_dgaopr_a_repr = Column(String(50))
    no_oficio_rpta_repr_a_dgaopr = Column(String(50))
    no_oficio_rpta_dgaopr_a_fifonafe = Column(String(50))
    fecha_oficio_fifonafe_a_dgaopr = Column(Date)
    fecha_oficio_dgaopr_a_repr = Column(Date)
    fecha_oficio_rpta_repr_a_dgaopr = Column(Date)
    fecha_oficio_rpta_dgaopr_a_fifonafe = Column(Date)
    activo = Column(Boolean, default=True, nullable=False)

class DocumentacionSoporte(Base, AuditableMixin):
    __tablename__ = "documentacion_soporte"
    id_documento = Column(Integer, primary_key=True, index=True)
    entidad_relacionada_id = Column(Integer, nullable=False)
    entidad_relacionada_tipo = Column(String(50), nullable=False)
    tipo_documento = Column(String(100), nullable=False)
    categoria = Column(String(20), nullable=False)
    es_critico = Column(Boolean, nullable=False, default=False)
    url_archivo = Column(String)
    activo = Column(Boolean, default=True, nullable=False)
    fecha_carga = Column(DateTime(timezone=True), nullable=False)

class Alertas(Base, AuditableMixin):
    __tablename__ = "alertas"
    id_alerta = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(50), nullable=False)
    prioridad = Column(String(10), nullable=False)
    titulo = Column(String(255), nullable=False)
    descripcion = Column(String)
    entidad_relacionada_id = Column(Integer, nullable=False)
    entidad_relacionada_tipo = Column(String(50), nullable=False)
    fecha_evento = Column(Date)
    fecha_creacion = Column(DateTime(timezone=True), nullable=False)
    esta_activa = Column(Boolean, default=True, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

class AlertasVistas(Base):
    __tablename__ = "alertas_vistas"
    id_alerta = Column(Integer, ForeignKey("alertas.id_alerta", ondelete="CASCADE"), primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario", ondelete="CASCADE"), primary_key=True)
    fecha_vista = Column(DateTime(timezone=True), nullable=False)

class Bitacora(Base):
    __tablename__ = "bitacora"
    id_bitacora = Column(BigInteger, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False)
    id_nucleo = Column(Integer, ForeignKey("nucleo_agrario.id_nucleo"))
    id_tramo_nucleo = Column(Integer, ForeignKey("tramo_nucleo.id_tramo_nucleo"))
    entidad_tipo = Column(String(100), nullable=False)
    entidad_id = Column(BigInteger)
    accion = Column(String(30), nullable=False)
    detalle_cambio = Column(String)
    valor_anterior = Column(JSONB)
    valor_nuevo = Column(JSONB)
    fecha_hora = Column(DateTime(timezone=True), nullable=False)
    ip_origen = Column(INET)
    user_agent = Column(String)

class UsuarioTramo(Base):
    __tablename__ = "usuario_tramo"
    __table_args__ = (
        UniqueConstraint("id_usuario", "id_tramo", name="uq_usuario_tramo"),
    )
    id_usuario_tramo = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False)
    id_tramo = Column(Integer, ForeignKey("tramo.id_tramo"), nullable=False)
    fecha_asignacion = Column(DateTime(timezone=True), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    
    # Campos para baja lógica (DA-9)
    fecha_baja = Column(DateTime(timezone=True), nullable=True)
    id_usuario_baja = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=True)
    motivo_baja = Column(String, nullable=True)
    fecha_reactivacion = Column(DateTime(timezone=True), nullable=True)
    id_usuario_reactivacion = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=True)
    motivo_reactivacion = Column(String, nullable=True)
    observaciones = Column(String, nullable=True)
