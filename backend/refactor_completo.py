import re

print("1. Updating schemas.py")
with open('/mnt/hdd/Users/lopez/Software-PA/backend/app/schemas.py', 'r') as f:
    schemas_content = f.read()

schemas_append = """
# ==================== BITÁCORA ==================== #
from typing import Optional, Any
from pydantic import Json

class BitacoraResponse(BaseModel):
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
    class ConfigDict:
        from_attributes = True

# ==================== USUARIO FRENTE ==================== #
class UsuarioFrenteCreate(BaseModel):
    id_usuario: int

class UsuarioFrenteResponse(BaseModel):
    id_usuario: int
    id_frente: int
    fecha_asignacion: datetime
    activo: bool
    class ConfigDict:
        from_attributes = True
"""
if "class BitacoraResponse" not in schemas_content:
    with open('/mnt/hdd/Users/lopez/Software-PA/backend/app/schemas.py', 'a') as f:
        f.write(schemas_append)

print("2. Refactoring main.py")
with open('/mnt/hdd/Users/lopez/Software-PA/backend/app/main.py', 'r') as f:
    main_content = f.read()

# ADD MISSING ENDPOINTS AT THE END
new_endpoints = """
# ==================== BITÁCORA ==================== #
@app.get("/api/bitacora", response_model=List[schemas.BitacoraResponse])
def get_bitacora(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    return db.query(models.Bitacora).order_by(models.Bitacora.fecha_hora.desc()).offset(skip).limit(limit).all()

# ==================== ASIGNACIÓN USUARIO-FRENTE ==================== #
@app.post("/api/frentes/{id_frente}/asignar-usuario", response_model=schemas.UsuarioFrenteResponse)
def asignar_usuario_frente(id_frente: int, data: schemas.UsuarioFrenteCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    exists = db.query(models.UsuarioFrente).filter_by(id_frente=id_frente, id_usuario=data.id_usuario).first()
    if exists:
        if not exists.activo:
            exists.activo = True
            db.commit()
            db.refresh(exists)
        return exists
    nuevo = models.UsuarioFrente(id_frente=id_frente, id_usuario=data.id_usuario)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@app.delete("/api/frentes/{id_frente}/remover-usuario/{id_usuario}")
def remover_usuario_frente(id_frente: int, id_usuario: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin']))):
    exists = db.query(models.UsuarioFrente).filter_by(id_frente=id_frente, id_usuario=id_usuario).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Asignación no encontrada.")
    exists.activo = False
    db.commit()
    return {"status": "success", "detail": "Usuario removido del frente."}

# ==================== ALERTAS VISTAS ==================== #
@app.post("/api/alertas/{id_alerta}/marcar-leida")
def marcar_alerta_leida(id_alerta: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    alerta = get_entity_by_id(db, models.Alertas, id_alerta, "id_alerta")
    vista = db.query(models.AlertasVistas).filter_by(id_alerta=id_alerta, id_usuario=current_user.id_usuario).first()
    if not vista:
        nueva_vista = models.AlertasVistas(id_alerta=id_alerta, id_usuario=current_user.id_usuario)
        db.add(nueva_vista)
        db.commit()
    return {"status": "success", "detail": "Alerta marcada como leída."}

# ==================== GET BY ID (Líneas Individuales) ==================== #
@app.get("/api/tramos/{id_tramo}", response_model=schemas.TramoResponse)
def get_tramo_by_id(id_tramo: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    return get_entity_by_id(db, models.Tramo, id_tramo, "id_tramo")

@app.get("/api/frentes/{id_frente}", response_model=schemas.FrenteResponse)
def get_frente_by_id(id_frente: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    return get_entity_by_id(db, models.Frente, id_frente, "id_frente")

@app.get("/api/nucleos/{id_nucleo}", response_model=schemas.NucleoAgrarioResponse)
def get_nucleo_by_id(id_nucleo: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    return get_entity_by_id(db, models.NucleoAgrario, id_nucleo, "id_nucleo")

@app.get("/api/afectaciones/{id_afectacion}", response_model=schemas.AfectacionResponse)
def get_afectacion_by_id(id_afectacion: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    return get_entity_by_id(db, models.Afectacion, id_afectacion, "id_afectacion")

@app.get("/api/asambleas/{id_asamblea}", response_model=schemas.AsambleaResponse)
def get_asamblea_by_id(id_asamblea: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    return get_entity_by_id(db, models.Asamblea, id_asamblea, "id_asamblea")

@app.get("/api/convenios/{id_convenio}", response_model=schemas.ConvenioResponse)
def get_convenio_by_id(id_convenio: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    return get_entity_by_id(db, models.Convenio, id_convenio, "id_convenio")
"""
if "/api/bitacora" not in main_content:
    main_content += new_endpoints


# PAGINATION FOR THE REST
def add_pagination(content, func_name, model_name):
    # Matches: def get_frentes(db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    # Replaces with skip and limit, and adds .offset(skip).limit(limit) to .all()
    
    # Simple regex replacing the exact declaration. We know all these functions start exactly like this:
    pattern = rf'def {func_name}\(db: Session = Depends\(get_db\), current_user: models\.Usuario = Depends\(auth\.RoleChecker\((.*?)\)\)\):'
    replacement = rf'def {func_name}(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(\1))):'
    content = re.sub(pattern, replacement, content)
    
    # Find the specific return db.query(models.X).filter(models.X.activo == True).all() inside this function block and replace .all()
    # To avoid regex nightmare on function bodies, we'll just do a targeted replace for that model
    query_str = f'db.query(models.{model_name}).filter(models.{model_name}.activo == True).all()'
    query_str_pag = f'db.query(models.{model_name}).filter(models.{model_name}.activo == True).offset(skip).limit(limit).all()'
    content = content.replace(query_str, query_str_pag)
    return content

main_content = add_pagination(main_content, "get_frentes", "Frente")
main_content = add_pagination(main_content, "get_nucleos", "NucleoAgrario")
main_content = add_pagination(main_content, "get_parcelas", "Parcela")
main_content = add_pagination(main_content, "get_asambleas", "Asamblea")
main_content = add_pagination(main_content, "get_convenios", "Convenio")
main_content = add_pagination(main_content, "get_orvs", "Orv")
main_content = add_pagination(main_content, "get_padrones", "PadronHistorial")
main_content = add_pagination(main_content, "get_actividades_campo", "ActividadCampo")
main_content = add_pagination(main_content, "get_fifonafe", "TramiteFifonafe")
main_content = add_pagination(main_content, "get_documentacion", "DocumentacionSoporte")
main_content = add_pagination(main_content, "get_alertas", "Alertas")

with open('/mnt/hdd/Users/lopez/Software-PA/backend/app/main.py', 'w') as f:
    f.write(main_content)

print("Finished applying block 6 changes.")
