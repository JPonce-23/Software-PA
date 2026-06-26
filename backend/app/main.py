from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Type, Any
from datetime import datetime, timezone

from .database import engine, Base, get_db
from . import models, schemas

app = FastAPI(
    title="API - Sistema de Seguimiento de Liberación de Derechos",
    description="Backend con lógica de negocio geoespacial y administrativa",
    version="1.3.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def set_audit_context(db: Session, user_id: int = 1):
    db.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))

# ==================== UTILIDAD GENÉRICA CRUD ==================== #
def get_entity_by_id(db: Session, model: Type[Any], entity_id: int, id_column: str):
    entity = db.query(model).filter(getattr(model, id_column) == entity_id, model.activo == True).first()
    if not entity:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return entity

def update_entity(db: Session, entity: Any, update_data: Any):
    set_audit_context(db)
    update_dict = update_data.model_dump(exclude_unset=True)
    # Excluir explicitamente la logica manual WKT de update dict generico si existe
    if "geometria_wkt" in update_dict:
        wkt = update_dict.pop("geometria_wkt")
        if hasattr(entity, "geometria_linea"):
            entity.geometria_linea = wkt
        elif hasattr(entity, "geometria_poligono"):
            entity.geometria_poligono = wkt
            
    for key, value in update_dict.items():
        setattr(entity, key, value)
    db.commit()
    db.refresh(entity)
    return entity

def soft_delete_entity(db: Session, entity: Any, motivo: str = "Baja desde API"):
    set_audit_context(db)
    entity.activo = False
    entity.fecha_baja = datetime.now(timezone.utc)
    entity.id_usuario_baja = 1
    entity.motivo_baja = motivo
    db.commit()
    return {"status": "success", "message": "Registro eliminado lógicamente"}

@app.get("/")
def root():
    return {"message": "API 100% configurada y lista 🚂"}

# ==================== TRAMOS ==================== #
@app.get("/api/tramos", response_model=List[schemas.TramoResponse])
def get_tramos(db: Session = Depends(get_db)):
    return db.query(
        models.Tramo.id_tramo,
        models.Tramo.clave_tramo,
        models.Tramo.nombre_tramo,
        models.Tramo.descripcion,
        models.Tramo.ancho_total_derecho_via_m,
        models.Tramo.activo,
        models.Tramo.geometria_linea.ST_AsText().label('geometria_wkt')
    ).filter(models.Tramo.activo == True).all()

@app.post("/api/tramos", response_model=schemas.TramoResponse, status_code=status.HTTP_201_CREATED)
def create_tramo(tramo: schemas.TramoCreate, db: Session = Depends(get_db)):
    set_audit_context(db)
    data = tramo.model_dump()
    wkt = data.pop("geometria_wkt")
    db_tramo = models.Tramo(**data, geometria_linea=wkt)
    db_tramo.fecha_registro = datetime.now().date()
    db.add(db_tramo)
    db.commit()
    db.refresh(db_tramo)
    resp = db_tramo.__dict__.copy()
    resp["geometria_wkt"] = None
    return resp

@app.put("/api/tramos/{id_tramo}", response_model=schemas.TramoResponse)
def update_tramo(id_tramo: int, data: schemas.TramoUpdate, db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.Tramo, id_tramo, "id_tramo")
    db_tramo = update_entity(db, entity, data)
    resp = db_tramo.__dict__.copy()
    resp["geometria_wkt"] = None
    return resp

@app.delete("/api/tramos/{id_tramo}")
def delete_tramo(id_tramo: int, motivo: str = Query(...), db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.Tramo, id_tramo, "id_tramo")
    return soft_delete_entity(db, entity, motivo)

# ==================== FRENTES ==================== #
@app.get("/api/frentes", response_model=List[schemas.FrenteResponse])
def get_frentes(id_tramo: int = Query(None), db: Session = Depends(get_db)):
    query = db.query(
        models.Frente.id_frente,
        models.Frente.id_tramo,
        models.Frente.clave_frente,
        models.Frente.nombre_frente,
        models.Frente.geometria_linea.ST_AsText().label('geometria_wkt')
    ).filter(models.Frente.activo == True)
    if id_tramo:
        query = query.filter(models.Frente.id_tramo == id_tramo)
    return query.all()

@app.post("/api/frentes", response_model=schemas.FrenteResponse, status_code=status.HTTP_201_CREATED)
def create_frente(frente: schemas.FrenteCreate, db: Session = Depends(get_db)):
    set_audit_context(db)
    data = frente.model_dump()
    wkt = data.pop("geometria_wkt")
    db_frente = models.Frente(**data, geometria_linea=wkt)
    db_frente.fecha_registro = datetime.now().date()
    db.add(db_frente)
    db.commit()
    db.refresh(db_frente)
    resp = db_frente.__dict__.copy()
    resp["geometria_wkt"] = None
    return resp

@app.put("/api/frentes/{id_frente}", response_model=schemas.FrenteResponse)
def update_frente(id_frente: int, data: schemas.FrenteUpdate, db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.Frente, id_frente, "id_frente")
    db_frente = update_entity(db, entity, data)
    resp = db_frente.__dict__.copy()
    resp["geometria_wkt"] = None
    return resp

@app.delete("/api/frentes/{id_frente}")
def delete_frente(id_frente: int, motivo: str = Query(...), db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.Frente, id_frente, "id_frente")
    return soft_delete_entity(db, entity, motivo)

# ==================== NUCLEOS AGRARIOS ==================== #
@app.get("/api/nucleos", response_model=List[schemas.NucleoAgrarioResponse])
def get_nucleos(db: Session = Depends(get_db)):
    return db.query(
        models.NucleoAgrario.id_nucleo,
        models.NucleoAgrario.nombre_nucleo,
        models.NucleoAgrario.tipo_nucleo,
        models.NucleoAgrario.comunidad_indigena,
        models.NucleoAgrario.geometria_poligono.ST_AsText().label('geometria_wkt')
    ).filter(models.NucleoAgrario.activo == True).all()

@app.post("/api/nucleos", response_model=schemas.NucleoAgrarioResponse, status_code=status.HTTP_201_CREATED)
def create_nucleo(nucleo: schemas.NucleoAgrarioCreate, db: Session = Depends(get_db)):
    set_audit_context(db)
    data = nucleo.model_dump()
    wkt = data.pop("geometria_wkt")
    db_nucleo = models.NucleoAgrario(**data, geometria_poligono=wkt)
    db_nucleo.fecha_creacion = datetime.now(timezone.utc)
    db.add(db_nucleo)
    db.commit()
    db.refresh(db_nucleo)
    resp = db_nucleo.__dict__.copy()
    resp["geometria_wkt"] = None
    return resp

@app.put("/api/nucleos/{id_nucleo}", response_model=schemas.NucleoAgrarioResponse)
def update_nucleo(id_nucleo: int, data: schemas.NucleoAgrarioUpdate, db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.NucleoAgrario, id_nucleo, "id_nucleo")
    db_nucleo = update_entity(db, entity, data)
    resp = db_nucleo.__dict__.copy()
    resp["geometria_wkt"] = None
    return resp

@app.delete("/api/nucleos/{id_nucleo}")
def delete_nucleo(id_nucleo: int, motivo: str = Query(...), db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.NucleoAgrario, id_nucleo, "id_nucleo")
    return soft_delete_entity(db, entity, motivo)

# ==================== DASHBOARD & REPORTES ==================== #
@app.get("/api/dashboard", response_model=List[schemas.DashboardMetrics])
def get_dashboard_metrics(db: Session = Depends(get_db)):
    query = text("SELECT * FROM vw_dashboard_liberacion LIMIT 100;")
    return db.execute(query).mappings().all()

@app.get("/api/reportes/resumen")
def generar_reporte_resumen(db: Session = Depends(get_db)):
    return {
        "generado_el": datetime.now(),
        "total_convenios": db.query(models.Convenio).filter(models.Convenio.activo == True).count(),
        "total_nucleos": db.query(models.NucleoAgrario).filter(models.NucleoAgrario.activo == True).count(),
        "total_afectaciones": db.query(models.Afectacion).filter(models.Afectacion.activo == True).count()
    }

# ==================== AFECTACIONES ==================== #
@app.get("/api/afectaciones", response_model=List[schemas.AfectacionResponse])
def list_afectaciones(id_tramo_nucleo: int = Query(None), tipo_afectacion: str = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.Afectacion).filter(models.Afectacion.activo == True)
    if id_tramo_nucleo:
        query = query.filter(models.Afectacion.id_tramo_nucleo == id_tramo_nucleo)
    if tipo_afectacion:
        query = query.filter(models.Afectacion.tipo_afectacion == tipo_afectacion)
    
    results = []
    for a in query.all():
        resp = a.__dict__.copy()
        resp["geometria_wkt"] = None
        results.append(resp)
    return results

@app.post("/api/afectaciones", response_model=schemas.AfectacionResponse, status_code=status.HTTP_201_CREATED)
def create_afectacion(afectacion: schemas.AfectacionCreate, db: Session = Depends(get_db)):
    set_audit_context(db)
    db_afectacion = models.Afectacion(**afectacion.model_dump())
    db.add(db_afectacion)
    db.commit()
    db.refresh(db_afectacion)
    resp = db_afectacion.__dict__.copy()
    resp["geometria_wkt"] = None
    return resp

@app.put("/api/afectaciones/{id_afectacion}", response_model=schemas.AfectacionResponse)
def update_afectacion_route(id_afectacion: int, data: schemas.AfectacionUpdate, db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.Afectacion, id_afectacion, "id_afectacion")
    db_afectacion = update_entity(db, entity, data)
    resp = db_afectacion.__dict__.copy()
    resp["geometria_wkt"] = None
    return resp

@app.delete("/api/afectaciones/{id_afectacion}")
def delete_afectacion(id_afectacion: int, motivo: str = Query(...), db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.Afectacion, id_afectacion, "id_afectacion")
    return soft_delete_entity(db, entity, motivo)

# ==================== ASAMBLEAS ==================== #
@app.get("/api/asambleas", response_model=List[schemas.AsambleaResponse])
def list_asambleas(id_tramo_nucleo: int = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.Asamblea).filter(models.Asamblea.activo == True)
    if id_tramo_nucleo:
        query = query.filter(models.Asamblea.id_tramo_nucleo == id_tramo_nucleo)
    return query.all()

@app.post("/api/asambleas", response_model=schemas.AsambleaResponse, status_code=status.HTTP_201_CREATED)
def create_asamblea(asamblea: schemas.AsambleaCreate, db: Session = Depends(get_db)):
    set_audit_context(db)
    db_asamblea = models.Asamblea(**asamblea.model_dump())
    db.add(db_asamblea)
    db.commit()
    db.refresh(db_asamblea)
    return db_asamblea

@app.put("/api/asambleas/{id_asamblea}", response_model=schemas.AsambleaResponse)
def update_asamblea_route(id_asamblea: int, data: schemas.AsambleaUpdate, db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.Asamblea, id_asamblea, "id_asamblea")
    return update_entity(db, entity, data)

@app.delete("/api/asambleas/{id_asamblea}")
def delete_asamblea(id_asamblea: int, motivo: str = Query(...), db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.Asamblea, id_asamblea, "id_asamblea")
    return soft_delete_entity(db, entity, motivo)

# ==================== CONVENIOS ==================== #
@app.get("/api/convenios", response_model=List[schemas.ConvenioResponse])
def list_convenios(
    id_tramo_nucleo: int = Query(None),
    tipo_convenio: str = Query(None),
    inscrito: bool = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(models.Convenio).filter(models.Convenio.activo == True)
    if id_tramo_nucleo:
        query = query.filter(models.Convenio.id_tramo_nucleo == id_tramo_nucleo)
    if tipo_convenio:
        query = query.filter(models.Convenio.tipo_convenio == tipo_convenio)
    if inscrito is True:
        query = query.filter(models.Convenio.convenio_inscrito_fecha_ran != None)
    return query.all()

@app.post("/api/convenios", response_model=schemas.ConvenioResponse, status_code=status.HTTP_201_CREATED)
def create_convenio(convenio: schemas.ConvenioCreate, db: Session = Depends(get_db)):
    set_audit_context(db)
    db_convenio = models.Convenio(**convenio.model_dump())
    db.add(db_convenio)
    db.commit()
    db.refresh(db_convenio)
    return db_convenio

@app.put("/api/convenios/{id_convenio}", response_model=schemas.ConvenioResponse)
def update_convenio_route(id_convenio: int, data: schemas.ConvenioUpdate, db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.Convenio, id_convenio, "id_convenio")
    return update_entity(db, entity, data)

@app.delete("/api/convenios/{id_convenio}")
def delete_convenio(id_convenio: int, motivo: str = Query(...), db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.Convenio, id_convenio, "id_convenio")
    return soft_delete_entity(db, entity, motivo)

# ==================== ORV ==================== #
@app.get("/api/orvs", response_model=List[schemas.OrvResponse])
def list_orvs(id_nucleo: int = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.Orv).filter(models.Orv.activo == True)
    if id_nucleo:
        query = query.filter(models.Orv.id_nucleo == id_nucleo)
    return query.all()

@app.post("/api/orvs", response_model=schemas.OrvResponse, status_code=status.HTTP_201_CREATED)
def create_orv(orv: schemas.OrvCreate, db: Session = Depends(get_db)):
    set_audit_context(db)
    db_orv = models.Orv(**orv.model_dump())
    db.add(db_orv)
    db.commit()
    db.refresh(db_orv)
    return db_orv

@app.put("/api/orvs/{id_orv}", response_model=schemas.OrvResponse)
def update_orv_route(id_orv: int, data: schemas.OrvUpdate, db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.Orv, id_orv, "id_orv")
    return update_entity(db, entity, data)

@app.delete("/api/orvs/{id_orv}")
def delete_orv(id_orv: int, motivo: str = Query(...), db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.Orv, id_orv, "id_orv")
    return soft_delete_entity(db, entity, motivo)

# ==================== PADRON ==================== #
@app.get("/api/padrones", response_model=List[schemas.PadronHistorialResponse])
def list_padrones(id_nucleo: int = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.PadronHistorial).filter(models.PadronHistorial.activo == True)
    if id_nucleo:
        query = query.filter(models.PadronHistorial.id_nucleo == id_nucleo)
    return query.all()

@app.post("/api/padrones", response_model=schemas.PadronHistorialResponse, status_code=status.HTTP_201_CREATED)
def create_padron(padron: schemas.PadronHistorialCreate, db: Session = Depends(get_db)):
    set_audit_context(db)
    db_padron = models.PadronHistorial(**padron.model_dump())
    db_padron.fecha_registro = datetime.now()
    db.add(db_padron)
    db.commit()
    db.refresh(db_padron)
    return db_padron

@app.put("/api/padrones/{id_padron}", response_model=schemas.PadronHistorialResponse)
def update_padron_route(id_padron: int, data: schemas.PadronHistorialUpdate, db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.PadronHistorial, id_padron, "id_padron")
    return update_entity(db, entity, data)

@app.delete("/api/padrones/{id_padron}")
def delete_padron(id_padron: int, motivo: str = Query(...), db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.PadronHistorial, id_padron, "id_padron")
    return soft_delete_entity(db, entity, motivo)

# ==================== ACTIVIDAD CAMPO ==================== #
@app.get("/api/actividades-campo", response_model=List[schemas.ActividadCampoResponse])
def list_actividades(id_tramo_nucleo: int = Query(None), tipo_actividad: str = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.ActividadCampo).filter(models.ActividadCampo.activo == True)
    if id_tramo_nucleo:
        query = query.filter(models.ActividadCampo.id_tramo_nucleo == id_tramo_nucleo)
    if tipo_actividad:
        query = query.filter(models.ActividadCampo.tipo_actividad == tipo_actividad)
    return query.all()

@app.post("/api/actividades-campo", response_model=schemas.ActividadCampoResponse, status_code=status.HTTP_201_CREATED)
def create_actividad(act: schemas.ActividadCampoCreate, db: Session = Depends(get_db)):
    set_audit_context(db)
    db_act = models.ActividadCampo(**act.model_dump())
    db_act.fecha_registro = datetime.now()
    db.add(db_act)
    db.commit()
    db.refresh(db_act)
    return db_act

@app.put("/api/actividades-campo/{id_actividad}", response_model=schemas.ActividadCampoResponse)
def update_actividad_route(id_actividad: int, data: schemas.ActividadCampoUpdate, db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.ActividadCampo, id_actividad, "id_actividad")
    return update_entity(db, entity, data)

@app.delete("/api/actividades-campo/{id_actividad}")
def delete_actividad(id_actividad: int, motivo: str = Query(...), db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.ActividadCampo, id_actividad, "id_actividad")
    return soft_delete_entity(db, entity, motivo)

# ==================== TRAMITE FIFONAFE ==================== #
@app.get("/api/fifonafe", response_model=List[schemas.TramiteFifonafeResponse])
def list_fifonafe(id_tramo_nucleo: int = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.TramiteFifonafe).filter(models.TramiteFifonafe.activo == True)
    if id_tramo_nucleo:
        query = query.filter(models.TramiteFifonafe.id_tramo_nucleo == id_tramo_nucleo)
    return query.all()

@app.post("/api/fifonafe", response_model=schemas.TramiteFifonafeResponse, status_code=status.HTTP_201_CREATED)
def create_fifonafe(tramite: schemas.TramiteFifonafeCreate, db: Session = Depends(get_db)):
    set_audit_context(db)
    db_tram = models.TramiteFifonafe(**tramite.model_dump())
    db.add(db_tram)
    db.commit()
    db.refresh(db_tram)
    return db_tram

@app.put("/api/fifonafe/{id_tramite}", response_model=schemas.TramiteFifonafeResponse)
def update_fifonafe_route(id_tramite: int, data: schemas.TramiteFifonafeUpdate, db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.TramiteFifonafe, id_tramite, "id_tramite_fifonafe")
    return update_entity(db, entity, data)

@app.delete("/api/fifonafe/{id_tramite}")
def delete_fifonafe(id_tramite: int, motivo: str = Query(...), db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.TramiteFifonafe, id_tramite, "id_tramite_fifonafe")
    return soft_delete_entity(db, entity, motivo)

# ==================== DOCUMENTACION ==================== #
@app.get("/api/documentacion", response_model=List[schemas.DocumentacionSoporteResponse])
def list_documentacion(entidad_tipo: str = Query(None), entidad_id: int = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.DocumentacionSoporte).filter(models.DocumentacionSoporte.activo == True)
    if entidad_tipo:
        query = query.filter(models.DocumentacionSoporte.entidad_relacionada_tipo == entidad_tipo)
    if entidad_id:
        query = query.filter(models.DocumentacionSoporte.entidad_relacionada_id == entidad_id)
    return query.all()

@app.post("/api/documentacion", response_model=schemas.DocumentacionSoporteResponse, status_code=status.HTTP_201_CREATED)
def create_documentacion(doc: schemas.DocumentacionSoporteCreate, db: Session = Depends(get_db)):
    set_audit_context(db)
    db_doc = models.DocumentacionSoporte(**doc.model_dump())
    db_doc.fecha_carga = datetime.now()
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

@app.put("/api/documentacion/{id_documento}", response_model=schemas.DocumentacionSoporteResponse)
def update_documentacion_route(id_documento: int, data: schemas.DocumentacionSoporteUpdate, db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.DocumentacionSoporte, id_documento, "id_documento")
    return update_entity(db, entity, data)

@app.delete("/api/documentacion/{id_documento}")
def delete_documentacion(id_documento: int, motivo: str = Query(...), db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.DocumentacionSoporte, id_documento, "id_documento")
    return soft_delete_entity(db, entity, motivo)

# ==================== ALERTAS ==================== #
@app.get("/api/alertas", response_model=List[schemas.AlertaResponse])
def list_alertas(activa: bool = Query(True), db: Session = Depends(get_db)):
    query = db.query(models.Alertas).filter(models.Alertas.activo == True)
    if activa is not None:
        query = query.filter(models.Alertas.esta_activa == activa)
    return query.all()

@app.post("/api/alertas", response_model=schemas.AlertaResponse, status_code=status.HTTP_201_CREATED)
def create_alerta(alerta: schemas.AlertaCreate, db: Session = Depends(get_db)):
    set_audit_context(db)
    db_alerta = models.Alertas(**alerta.model_dump())
    db_alerta.fecha_creacion = datetime.now()
    db.add(db_alerta)
    db.commit()
    db.refresh(db_alerta)
    return db_alerta

@app.put("/api/alertas/{id_alerta}", response_model=schemas.AlertaResponse)
def update_alerta(id_alerta: int, data: schemas.AlertaUpdate, db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.Alertas, id_alerta, "id_alerta")
    return update_entity(db, entity, data)

@app.delete("/api/alertas/{id_alerta}")
def delete_alerta(id_alerta: int, motivo: str = Query(...), db: Session = Depends(get_db)):
    entity = get_entity_by_id(db, models.Alertas, id_alerta, "id_alerta")
    return soft_delete_entity(db, entity, motivo)