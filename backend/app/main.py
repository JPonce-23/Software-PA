from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from .database import engine, Base, get_db
from . import models, schemas

app = FastAPI(
    title="API - Sistema de Seguimiento de Liberación de Derechos",
    description="Backend geoespacial completo con FastAPI y PostGIS",
    version="1.2.0"
)

@app.get("/")
def root():
    return {"message": "API Geoespacial 100% configurada y lista 🚂"}

# ==================== MAPA (GEOMETRÍAS) ==================== #

@app.get("/api/tramos", response_model=List[schemas.TramoResponse])
def get_tramos(db: Session = Depends(get_db)):
    tramos = db.query(
        models.Tramo.id_tramo,
        models.Tramo.clave_tramo,
        models.Tramo.nombre_tramo,
        models.Tramo.descripcion,
        models.Tramo.ancho_total_derecho_via_m,
        models.Tramo.activo,
        models.Tramo.geometria_linea.ST_AsText().label('geometria_wkt')
    ).filter(models.Tramo.activo == True).all()
    return tramos

@app.get("/api/frentes", response_model=List[schemas.FrenteResponse])
def get_frentes(db: Session = Depends(get_db)):
    frentes = db.query(
        models.Frente.id_frente,
        models.Frente.id_tramo,
        models.Frente.clave_frente,
        models.Frente.nombre_frente,
        models.Frente.geometria_linea.ST_AsText().label('geometria_wkt')
    ).filter(models.Frente.activo == True).all()
    return frentes

@app.get("/api/nucleos", response_model=List[schemas.NucleoAgrarioResponse])
def get_nucleos(db: Session = Depends(get_db)):
    nucleos = db.query(
        models.NucleoAgrario.id_nucleo,
        models.NucleoAgrario.nombre_nucleo,
        models.NucleoAgrario.tipo_nucleo,
        models.NucleoAgrario.comunidad_indigena,
        models.NucleoAgrario.geometria_poligono.ST_AsText().label('geometria_wkt')
    ).filter(models.NucleoAgrario.activo == True).all()
    return nucleos

# ==================== DASHBOARD ==================== #

@app.get("/api/dashboard", response_model=List[schemas.DashboardMetrics])
def get_dashboard_metrics(db: Session = Depends(get_db)):
    query = text("SELECT * FROM vw_dashboard_liberacion LIMIT 100;")
    return db.execute(query).mappings().all()

# ==================== FLUJO DE TRABAJO (CRUD) ==================== #

@app.post("/api/afectaciones", response_model=schemas.AfectacionResponse, status_code=status.HTTP_201_CREATED)
def create_afectacion(afectacion: schemas.AfectacionCreate, db: Session = Depends(get_db)):
    db_afectacion = models.Afectacion(**afectacion.model_dump())
    db.add(db_afectacion)
    db.commit()
    db.refresh(db_afectacion)
    resp = db_afectacion.__dict__.copy()
    resp["geometria_wkt"] = None 
    return resp

@app.get("/api/asambleas", response_model=List[schemas.AsambleaResponse])
def get_asambleas(db: Session = Depends(get_db)):
    return db.query(models.Asamblea).filter(models.Asamblea.activo == True).all()

@app.post("/api/asambleas", response_model=schemas.AsambleaResponse, status_code=status.HTTP_201_CREATED)
def create_asamblea(asamblea: schemas.AsambleaCreate, db: Session = Depends(get_db)):
    db_asamblea = models.Asamblea(**asamblea.model_dump())
    db.add(db_asamblea)
    db.commit()
    db.refresh(db_asamblea)
    return db_asamblea

@app.get("/api/convenios", response_model=List[schemas.ConvenioResponse])
def get_convenios(db: Session = Depends(get_db)):
    return db.query(models.Convenio).filter(models.Convenio.activo == True).all()

@app.post("/api/convenios", response_model=schemas.ConvenioResponse, status_code=status.HTTP_201_CREATED)
def create_convenio(convenio: schemas.ConvenioCreate, db: Session = Depends(get_db)):
    # Aquí el motor de Postgres y el Trigger se encargarán de validar que
    # no superposicionemos hectáreas si es un "modificatorio"
    db_convenio = models.Convenio(**convenio.model_dump())
    db.add(db_convenio)
    db.commit()
    db.refresh(db_convenio)
    return db_convenio