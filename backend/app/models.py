from sqlalchemy import Column, Integer, String, Boolean, Numeric, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from .database import Base

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

class Tramo(Base):
    __tablename__ = "tramo"
    id_tramo = Column(Integer, primary_key=True, index=True)
    clave_tramo = Column(String(20), unique=True, nullable=False)
    nombre_tramo = Column(String(200), nullable=False)
    descripcion = Column(String)
    ancho_total_derecho_via_m = Column(Numeric(6, 2), default=40.00)
    # Columna Espacial usando GeoAlchemy2
    geometria_linea = Column(Geometry(geometry_type='MULTILINESTRING', srid=4326))
    activo = Column(Boolean, default=True, nullable=False)

    frentes = relationship("Frente", back_populates="tramo")

class Frente(Base):
    __tablename__ = "frente"
    id_frente = Column(Integer, primary_key=True, index=True)
    id_tramo = Column(Integer, ForeignKey("tramo.id_tramo"), nullable=False)
    clave_frente = Column(String(30), nullable=False)
    nombre_frente = Column(String(200), nullable=False)
    geometria_linea = Column(Geometry(geometry_type='MULTILINESTRING', srid=4326))
    activo = Column(Boolean, default=True, nullable=False)

    tramo = relationship("Tramo", back_populates="frentes")

class NucleoAgrario(Base):
    __tablename__ = "nucleo_agrario"
    id_nucleo = Column(Integer, primary_key=True, index=True)
    id_municipio = Column(Integer, ForeignKey("municipio.id_municipio"), nullable=False)
    nombre_nucleo = Column(String(300), nullable=False)
    tipo_nucleo = Column(String(20), nullable=False)
    comunidad_indigena = Column(Boolean, default=False, nullable=False)
    # Columna Espacial usando GeoAlchemy2
    geometria_poligono = Column(Geometry(geometry_type='MULTIPOLYGON', srid=4326))
    activo = Column(Boolean, default=True, nullable=False)

    municipio = relationship("Municipio", back_populates="nucleos")
