from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Type, Any
from datetime import datetime, timezone

from .database import engine, Base, get_db
from . import models, schemas
from fastapi.security import OAuth2PasswordRequestForm
from . import auth


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

def set_audit_context(db: Session, user_id: int):
    db.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))

# ==================== UTILIDAD GENÉRICA CRUD ==================== #
def get_entity_by_id(db: Session, model: Type[Any], entity_id: int, id_column: str):
    entity = db.query(model).filter(getattr(model, id_column) == entity_id, model.activo == True).first()
    if not entity:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return entity

def update_entity(db: Session, entity: Any, update_data: Any, user_id: int):
    set_audit_context(db, user_id)
    update_dict = update_data.model_dump(exclude_unset=True)
    # Despachar geometria_wkt al campo de geometría correcto según la entidad
    if "geometria_wkt" in update_dict:
        wkt = update_dict.pop("geometria_wkt")
        if hasattr(entity, "geometria_linea"):
            entity.geometria_linea = wkt
        elif hasattr(entity, "geometria_poligono"):
            entity.geometria_poligono = wkt
        elif hasattr(entity, "geometria_segmento"):
            entity.geometria_segmento = wkt

    for key, value in update_dict.items():
        setattr(entity, key, value)
    db.commit()
    db.refresh(entity)
    return entity

def soft_delete_entity(db: Session, entity: Any, user_id: int, motivo: str = "Baja desde API"):
    set_audit_context(db, user_id)
    entity.activo = False
    entity.fecha_baja = datetime.now(timezone.utc)
    entity.id_usuario_baja = user_id
    entity.motivo_baja = motivo
    db.commit()
    return {"status": "success", "message": "Registro eliminado lógicamente"}

@app.get("/")
def root():
    return {"message": "API 100% configurada y lista 🚂"}

# ==================== TRAMOS ==================== #
@app.get("/api/tramos", response_model=List[schemas.TramoResponse])
def get_tramos(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
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
def create_tramo(tramo: schemas.TramoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
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
def update_tramo(id_tramo: int, data: schemas.TramoUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Tramo, id_tramo, "id_tramo")
    db_tramo = update_entity(db, entity, data, current_user.id_usuario)
    resp = db_tramo.__dict__.copy()
    resp["geometria_wkt"] = None
    return resp

@app.delete("/api/tramos/{id_tramo}")
def delete_tramo(id_tramo: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Tramo, id_tramo, "id_tramo")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== FRENTES ==================== #
@app.get("/api/frentes", response_model=List[schemas.FrenteResponse])
def get_frentes(id_tramo: int = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
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
def create_frente(frente: schemas.FrenteCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
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
def update_frente(id_frente: int, data: schemas.FrenteUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Frente, id_frente, "id_frente")
    db_frente = update_entity(db, entity, data, current_user.id_usuario)
    resp = db_frente.__dict__.copy()
    resp["geometria_wkt"] = None
    return resp

@app.delete("/api/frentes/{id_frente}")
def delete_frente(id_frente: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Frente, id_frente, "id_frente")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== NUCLEOS AGRARIOS ==================== #
@app.get("/api/nucleos", response_model=List[schemas.NucleoAgrarioResponse])
def get_nucleos(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    return db.query(
        models.NucleoAgrario.id_nucleo,
        models.NucleoAgrario.nombre_nucleo,
        models.NucleoAgrario.tipo_nucleo,
        models.NucleoAgrario.comunidad_indigena,
        models.NucleoAgrario.geometria_poligono.ST_AsText().label('geometria_wkt')
    ).filter(models.NucleoAgrario.activo == True).all()

@app.post("/api/nucleos", response_model=schemas.NucleoAgrarioResponse, status_code=status.HTTP_201_CREATED)
def create_nucleo(nucleo: schemas.NucleoAgrarioCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
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
def update_nucleo(id_nucleo: int, data: schemas.NucleoAgrarioUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.NucleoAgrario, id_nucleo, "id_nucleo")
    db_nucleo = update_entity(db, entity, data, current_user.id_usuario)
    resp = db_nucleo.__dict__.copy()
    resp["geometria_wkt"] = None
    return resp

@app.delete("/api/nucleos/{id_nucleo}")
def delete_nucleo(id_nucleo: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.NucleoAgrario, id_nucleo, "id_nucleo")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== TRAMOS-NUCLEOS ==================== #
@app.get("/api/tramos-nucleos", response_model=List[schemas.TramoNucleoResponse])
def list_tramos_nucleos(
    id_tramo: int = Query(None),
    id_frente: int = Query(None),
    id_nucleo: int = Query(None),
    db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))
):
    query = db.query(
        models.TramoNucleo.id_tramo_nucleo,
        models.TramoNucleo.id_tramo,
        models.TramoNucleo.id_frente,
        models.TramoNucleo.id_nucleo,
        models.TramoNucleo.consecutivo,
        models.TramoNucleo.numero_tramo,
        models.TramoNucleo.geometria_segmento.ST_AsText().label('geometria_wkt'),
        models.TramoNucleo.longitud_m,
        models.TramoNucleo.es_expropiacion,
        models.TramoNucleo.causa_problema,
        models.TramoNucleo.proyecto_no_afecta_uso_comun,
        models.TramoNucleo.activo,
        models.TramoNucleo.observaciones,
    ).filter(models.TramoNucleo.activo == True)
    if id_tramo:
        query = query.filter(models.TramoNucleo.id_tramo == id_tramo)
    if id_frente:
        query = query.filter(models.TramoNucleo.id_frente == id_frente)
    if id_nucleo:
        query = query.filter(models.TramoNucleo.id_nucleo == id_nucleo)
    return query.all()

@app.get("/api/tramos-nucleos/{id_tramo_nucleo}", response_model=schemas.TramoNucleoResponse)
def get_tramo_nucleo(id_tramo_nucleo: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    row = db.query(
        models.TramoNucleo.id_tramo_nucleo,
        models.TramoNucleo.id_tramo,
        models.TramoNucleo.id_frente,
        models.TramoNucleo.id_nucleo,
        models.TramoNucleo.consecutivo,
        models.TramoNucleo.numero_tramo,
        models.TramoNucleo.geometria_segmento.ST_AsText().label('geometria_wkt'),
        models.TramoNucleo.longitud_m,
        models.TramoNucleo.es_expropiacion,
        models.TramoNucleo.causa_problema,
        models.TramoNucleo.proyecto_no_afecta_uso_comun,
        models.TramoNucleo.activo,
        models.TramoNucleo.observaciones,
    ).filter(
        models.TramoNucleo.id_tramo_nucleo == id_tramo_nucleo,
        models.TramoNucleo.activo == True
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="TramoNucleo not found")
    return row

@app.post("/api/tramos-nucleos", response_model=schemas.TramoNucleoResponse, status_code=status.HTTP_201_CREATED)
def create_tramo_nucleo(tramo_nucleo: schemas.TramoNucleoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    data = tramo_nucleo.model_dump()
    wkt = data.pop("geometria_wkt", None)
    db_tn = models.TramoNucleo(**data)
    if wkt:
        db_tn.geometria_segmento = wkt
    db.add(db_tn)
    db.commit()
    db.refresh(db_tn)
    resp = db_tn.__dict__.copy()
    resp["geometria_wkt"] = None  # la geometría no se serializa al refrescar
    return resp

@app.put("/api/tramos-nucleos/{id_tramo_nucleo}", response_model=schemas.TramoNucleoResponse)
def update_tramo_nucleo(id_tramo_nucleo: int, data: schemas.TramoNucleoUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.TramoNucleo, id_tramo_nucleo, "id_tramo_nucleo")
    updated = update_entity(db, entity, data, current_user.id_usuario)
    resp = updated.__dict__.copy()
    resp["geometria_wkt"] = None
    return resp

@app.delete("/api/tramos-nucleos/{id_tramo_nucleo}")
def delete_tramo_nucleo(id_tramo_nucleo: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.TramoNucleo, id_tramo_nucleo, "id_tramo_nucleo")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== PARCELAS ==================== #
@app.get("/api/parcelas", response_model=List[schemas.ParcelaResponse])
def list_parcelas(
    id_nucleo: int = Query(None),
    tipo_parcela: str = Query(None),
    db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))
):
    query = db.query(models.Parcela).filter(models.Parcela.activo == True)
    if id_nucleo:
        query = query.filter(models.Parcela.id_nucleo == id_nucleo)
    if tipo_parcela:
        query = query.filter(models.Parcela.tipo_parcela == tipo_parcela)
    return query.all()

@app.get("/api/parcelas/{id_parcela}", response_model=schemas.ParcelaResponse)
def get_parcela(id_parcela: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    return get_entity_by_id(db, models.Parcela, id_parcela, "id_parcela")

@app.post("/api/parcelas", response_model=schemas.ParcelaResponse, status_code=status.HTTP_201_CREATED)
def create_parcela(parcela: schemas.ParcelaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    db_parcela = models.Parcela(**parcela.model_dump())
    db.add(db_parcela)
    db.commit()
    db.refresh(db_parcela)
    return db_parcela

@app.put("/api/parcelas/{id_parcela}", response_model=schemas.ParcelaResponse)
def update_parcela(id_parcela: int, data: schemas.ParcelaUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Parcela, id_parcela, "id_parcela")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/parcelas/{id_parcela}")
def delete_parcela(id_parcela: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Parcela, id_parcela, "id_parcela")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== DASHBOARD & REPORTES ==================== #
@app.get("/api/dashboard", response_model=List[schemas.DashboardMetrics])
def get_dashboard_metrics(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = text("SELECT * FROM vw_dashboard_liberacion LIMIT 100;")
    return db.execute(query).mappings().all()

@app.get("/api/reportes/resumen")
def generar_reporte_resumen(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    return {
        "generado_el": datetime.now(),
        "total_convenios": db.query(models.Convenio).filter(models.Convenio.activo == True).count(),
        "total_nucleos": db.query(models.NucleoAgrario).filter(models.NucleoAgrario.activo == True).count(),
        "total_afectaciones": db.query(models.Afectacion).filter(models.Afectacion.activo == True).count()
    }

# ==================== AFECTACIONES ==================== #
@app.get("/api/afectaciones", response_model=List[schemas.AfectacionResponse])
def list_afectaciones(id_tramo_nucleo: int = Query(None), tipo_afectacion: str = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
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
def create_afectacion(afectacion: schemas.AfectacionCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    
    # B9: Individual requiere parcela
    if afectacion.tipo_afectacion == 'individual' and not afectacion.id_parcela:
        raise HTTPException(status_code=400, detail="Una afectación individual requiere id_parcela")
        
    db_afectacion = models.Afectacion(**afectacion.model_dump())
    db.add(db_afectacion)
    db.commit()
    db.refresh(db_afectacion)
    resp = db_afectacion.__dict__.copy()
    resp["geometria_wkt"] = None
    return resp

@app.put("/api/afectaciones/{id_afectacion}", response_model=schemas.AfectacionResponse)
def update_afectacion_route(id_afectacion: int, data: schemas.AfectacionUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Afectacion, id_afectacion, "id_afectacion")
    db_afectacion = update_entity(db, entity, data, current_user.id_usuario)
    resp = db_afectacion.__dict__.copy()
    resp["geometria_wkt"] = None
    return resp

@app.delete("/api/afectaciones/{id_afectacion}")
def delete_afectacion(id_afectacion: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Afectacion, id_afectacion, "id_afectacion")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== ASAMBLEAS ==================== #
@app.get("/api/asambleas", response_model=List[schemas.AsambleaResponse])
def list_asambleas(id_tramo_nucleo: int = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.Asamblea).filter(models.Asamblea.activo == True)
    if id_tramo_nucleo:
        query = query.filter(models.Asamblea.id_tramo_nucleo == id_tramo_nucleo)
    return query.all()

@app.post("/api/asambleas", response_model=schemas.AsambleaResponse, status_code=status.HTTP_201_CREATED)
def create_asamblea(asamblea: schemas.AsambleaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    db_asamblea = models.Asamblea(**asamblea.model_dump())
    db.add(db_asamblea)
    db.commit()
    db.refresh(db_asamblea)
    return db_asamblea

@app.put("/api/asambleas/{id_asamblea}", response_model=schemas.AsambleaResponse)
def update_asamblea_route(id_asamblea: int, data: schemas.AsambleaUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Asamblea, id_asamblea, "id_asamblea")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/asambleas/{id_asamblea}")
def delete_asamblea(id_asamblea: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Asamblea, id_asamblea, "id_asamblea")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== CONVENIOS ==================== #
@app.get("/api/convenios", response_model=List[schemas.ConvenioResponse])
def list_convenios(
    id_tramo_nucleo: int = Query(None),
    tipo_convenio: str = Query(None),
    inscrito: bool = Query(None),
    db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))
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
def create_convenio(convenio: schemas.ConvenioCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    
    # B6 / B7: Asamblea constraint
    if convenio.tipo_afectacion == 'colectivo' and not convenio.id_asamblea_autorizacion:
        raise HTTPException(status_code=400, detail="Convenios colectivos requieren id_asamblea_autorizacion (chk_colectivo_requiere_asamblea)")
    if convenio.tipo_afectacion == 'individual' and convenio.id_asamblea_autorizacion:
        raise HTTPException(status_code=400, detail="Convenios individuales no deben tener asamblea (chk_individual_sin_asamblea)")
        
    # B8: Modificatorio padre constraint
    if convenio.tipo_convenio == 'modificatorio' and not convenio.id_convenio_padre:
        raise HTTPException(status_code=400, detail="Los convenios modificatorios requieren un id_convenio_padre")
        
    # RN-1: Compatibilidad tipo_convenio vs tipo_afectacion
    colectivo_permitidos = ['ocupacion_previa', 'modificatorio', 'superficie_adicional', 'obras_complementarias']
    individual_permitidos = ['ocupacion_previa', 'modificatorio', 'ampliacion', 'ampliacion_remanentes']
    if convenio.tipo_afectacion == 'colectivo' and convenio.tipo_convenio not in colectivo_permitidos:
        raise HTTPException(status_code=400, detail=f"tipo_convenio {convenio.tipo_convenio} no permitido para afectación colectivo")
    if convenio.tipo_afectacion == 'individual' and convenio.tipo_convenio not in individual_permitidos:
        raise HTTPException(status_code=400, detail=f"tipo_convenio {convenio.tipo_convenio} no permitido para afectación individual")
        
    # RN-2: Obras Complementarias sin BDT
    if convenio.tipo_convenio == 'obras_complementarias' and convenio.monto_bdt is not None:
        raise HTTPException(status_code=400, detail="Convenios de obras complementarias no deben tener monto_bdt")
        
    # RN-3: Modificatorio individual restricciones
    if convenio.tipo_convenio == 'modificatorio' and convenio.tipo_afectacion == 'individual':
        if convenio.superficie_real_afectada_ha or convenio.superficie_total_ha or convenio.monto_bdt:
             raise HTTPException(status_code=400, detail="Modificatorio individual solo permite fecha_firma, monto_90 y monto_100")
             
    # RN-5: Superficie field exclusivity
    if convenio.tipo_afectacion == 'colectivo' and convenio.superficie_total_ha is not None:
        raise HTTPException(status_code=400, detail="Afectación colectiva debe usar superficie_real_afectada_ha, no superficie_total_ha")
    if convenio.tipo_afectacion == 'individual' and convenio.superficie_real_afectada_ha is not None:
        raise HTTPException(status_code=400, detail="Afectación individual debe usar superficie_total_ha, no superficie_real_afectada_ha")

    db_convenio = models.Convenio(**convenio.model_dump())
    db.add(db_convenio)
    db.commit()
    db.refresh(db_convenio)
    return db_convenio

@app.put("/api/convenios/{id_convenio}", response_model=schemas.ConvenioResponse)
def update_convenio_route(id_convenio: int, data: schemas.ConvenioUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Convenio, id_convenio, "id_convenio")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/convenios/{id_convenio}")
def delete_convenio(id_convenio: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Convenio, id_convenio, "id_convenio")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== ORV ==================== #
@app.get("/api/orvs", response_model=List[schemas.OrvResponse])
def list_orvs(id_nucleo: int = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.Orv).filter(models.Orv.activo == True)
    if id_nucleo:
        query = query.filter(models.Orv.id_nucleo == id_nucleo)
    return query.all()

@app.post("/api/orvs", response_model=schemas.OrvResponse, status_code=status.HTTP_201_CREATED)
def create_orv(orv: schemas.OrvCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    db_orv = models.Orv(**orv.model_dump())
    db.add(db_orv)
    db.commit()
    db.refresh(db_orv)
    return db_orv

@app.put("/api/orvs/{id_orv}", response_model=schemas.OrvResponse)
def update_orv_route(id_orv: int, data: schemas.OrvUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Orv, id_orv, "id_orv")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/orvs/{id_orv}")
def delete_orv(id_orv: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Orv, id_orv, "id_orv")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== PADRON ==================== #
@app.get("/api/padrones", response_model=List[schemas.PadronHistorialResponse])
def list_padrones(id_nucleo: int = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.PadronHistorial).filter(models.PadronHistorial.activo == True)
    if id_nucleo:
        query = query.filter(models.PadronHistorial.id_nucleo == id_nucleo)
    return query.all()

@app.post("/api/padrones", response_model=schemas.PadronHistorialResponse, status_code=status.HTTP_201_CREATED)
def create_padron(padron: schemas.PadronHistorialCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    db_padron = models.PadronHistorial(**padron.model_dump())
    db_padron.fecha_registro = datetime.now()
    db.add(db_padron)
    db.commit()
    db.refresh(db_padron)
    return db_padron

@app.put("/api/padrones/{id_padron}", response_model=schemas.PadronHistorialResponse)
def update_padron_route(id_padron: int, data: schemas.PadronHistorialUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.PadronHistorial, id_padron, "id_padron")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/padrones/{id_padron}")
def delete_padron(id_padron: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.PadronHistorial, id_padron, "id_padron")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== ACTIVIDAD CAMPO ==================== #
@app.get("/api/actividades-campo", response_model=List[schemas.ActividadCampoResponse])
def list_actividades(id_tramo_nucleo: int = Query(None), tipo_actividad: str = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.ActividadCampo).filter(models.ActividadCampo.activo == True)
    if id_tramo_nucleo:
        query = query.filter(models.ActividadCampo.id_tramo_nucleo == id_tramo_nucleo)
    if tipo_actividad:
        query = query.filter(models.ActividadCampo.tipo_actividad == tipo_actividad)
    return query.all()

@app.post("/api/actividades-campo", response_model=schemas.ActividadCampoResponse, status_code=status.HTTP_201_CREATED)
def create_actividad(act: schemas.ActividadCampoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    db_act = models.ActividadCampo(**act.model_dump())
    db_act.fecha_registro = datetime.now()
    db.add(db_act)
    db.commit()
    db.refresh(db_act)
    return db_act

@app.put("/api/actividades-campo/{id_actividad}", response_model=schemas.ActividadCampoResponse)
def update_actividad_route(id_actividad: int, data: schemas.ActividadCampoUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.ActividadCampo, id_actividad, "id_actividad")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/actividades-campo/{id_actividad}")
def delete_actividad(id_actividad: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.ActividadCampo, id_actividad, "id_actividad")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== TRAMITE FIFONAFE ==================== #
@app.get("/api/fifonafe", response_model=List[schemas.TramiteFifonafeResponse])
def list_fifonafe(id_tramo_nucleo: int = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.TramiteFifonafe).filter(models.TramiteFifonafe.activo == True)
    if id_tramo_nucleo:
        query = query.filter(models.TramiteFifonafe.id_tramo_nucleo == id_tramo_nucleo)
    return query.all()

@app.post("/api/fifonafe", response_model=schemas.TramiteFifonafeResponse, status_code=status.HTTP_201_CREATED)
def create_fifonafe(tramite: schemas.TramiteFifonafeCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    db_tram = models.TramiteFifonafe(**tramite.model_dump())
    db.add(db_tram)
    db.commit()
    db.refresh(db_tram)
    return db_tram

@app.put("/api/fifonafe/{id_tramite}", response_model=schemas.TramiteFifonafeResponse)
def update_fifonafe_route(id_tramite: int, data: schemas.TramiteFifonafeUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.TramiteFifonafe, id_tramite, "id_tramite_fifonafe")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/fifonafe/{id_tramite}")
def delete_fifonafe(id_tramite: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.TramiteFifonafe, id_tramite, "id_tramite_fifonafe")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== DOCUMENTACION ==================== #
@app.get("/api/documentacion", response_model=List[schemas.DocumentacionSoporteResponse])
def list_documentacion(entidad_tipo: str = Query(None), entidad_id: int = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.DocumentacionSoporte).filter(models.DocumentacionSoporte.activo == True)
    if entidad_tipo:
        query = query.filter(models.DocumentacionSoporte.entidad_relacionada_tipo == entidad_tipo)
    if entidad_id:
        query = query.filter(models.DocumentacionSoporte.entidad_relacionada_id == entidad_id)
    return query.all()

@app.post("/api/documentacion", response_model=schemas.DocumentacionSoporteResponse, status_code=status.HTTP_201_CREATED)
def create_documentacion(doc: schemas.DocumentacionSoporteCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    db_doc = models.DocumentacionSoporte(**doc.model_dump())
    db_doc.fecha_carga = datetime.now()
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

@app.put("/api/documentacion/{id_documento}", response_model=schemas.DocumentacionSoporteResponse)
def update_documentacion_route(id_documento: int, data: schemas.DocumentacionSoporteUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.DocumentacionSoporte, id_documento, "id_documento")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/documentacion/{id_documento}")
def delete_documentacion(id_documento: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.DocumentacionSoporte, id_documento, "id_documento")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)

# ==================== ALERTAS ==================== #
@app.get("/api/alertas", response_model=List[schemas.AlertaResponse])
def list_alertas(activa: bool = Query(True), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    query = db.query(models.Alertas).filter(models.Alertas.activo == True)
    if activa is not None:
        query = query.filter(models.Alertas.esta_activa == activa)
    return query.all()

@app.post("/api/alertas", response_model=schemas.AlertaResponse, status_code=status.HTTP_201_CREATED)
def create_alerta(alerta: schemas.AlertaCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    set_audit_context(db, current_user.id_usuario)
    db_alerta = models.Alertas(**alerta.model_dump())
    db_alerta.fecha_creacion = datetime.now()
    db.add(db_alerta)
    db.commit()
    db.refresh(db_alerta)
    return db_alerta

@app.put("/api/alertas/{id_alerta}", response_model=schemas.AlertaResponse)
def update_alerta(id_alerta: int, data: schemas.AlertaUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Alertas, id_alerta, "id_alerta")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/alertas/{id_alerta}")
def delete_alerta(id_alerta: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'geografo']))):
    entity = get_entity_by_id(db, models.Alertas, id_alerta, "id_alerta")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)
# ==================== AUTH ==================== #
@app.post("/api/auth/login", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.correo == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.contrasena_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.activo:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.correo, "rol": user.rol}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# ==================== USUARIOS ==================== #
@app.post("/api/usuarios", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def create_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    set_audit_context(db, current_user.id_usuario)
    db_user = db.query(models.Usuario).filter(models.Usuario.correo == usuario.correo).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    hashed_password = auth.get_password_hash(usuario.contrasena)
    user_data = usuario.model_dump(exclude={"contrasena"})
    db_usuario = models.Usuario(**user_data, contrasena_hash=hashed_password, fecha_alta=datetime.now(timezone.utc))
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

@app.get("/api/usuarios", response_model=list[schemas.UsuarioResponse])
def get_usuarios(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    return db.query(models.Usuario).filter(models.Usuario.activo == True).all()

@app.put("/api/usuarios/{id_usuario}", response_model=schemas.UsuarioResponse)
def update_usuario(id_usuario: int, data: schemas.UsuarioUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    entity = get_entity_by_id(db, models.Usuario, id_usuario, "id_usuario")
    return update_entity(db, entity, data, current_user.id_usuario)

@app.delete("/api/usuarios/{id_usuario}")
def delete_usuario(id_usuario: int, motivo: str = Query(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    entity = get_entity_by_id(db, models.Usuario, id_usuario, "id_usuario")
    return soft_delete_entity(db, entity, current_user.id_usuario, motivo)
