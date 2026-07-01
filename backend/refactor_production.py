import re
import os

print("1. Fixing requirements.txt")
with open('/mnt/hdd/Users/lopez/Software-PA/backend/requirements.txt', 'r') as f:
    reqs = f.read()
if "aiofiles" not in reqs:
    with open('/mnt/hdd/Users/lopez/Software-PA/backend/requirements.txt', 'a') as f:
        f.write("\naiofiles\npytest\nhttpx\n")

print("2. Securing auth.py")
with open('/mnt/hdd/Users/lopez/Software-PA/backend/app/auth.py', 'r') as f:
    auth_content = f.read()

if 'os.getenv("SECRET_KEY"' not in auth_content:
    if "import os" not in auth_content:
        auth_content = auth_content.replace(
            "import bcrypt",
            "import bcrypt\nimport os"
        )
    auth_content = auth_content.replace(
        'SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"',
        'SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")'
    )
    with open('/mnt/hdd/Users/lopez/Software-PA/backend/app/auth.py', 'w') as f:
        f.write(auth_content)


print("3. Refactoring main.py (Pagination, Geo-Validation, Uploads, CORS)")
with open('/mnt/hdd/Users/lopez/Software-PA/backend/app/main.py', 'r') as f:
    main_content = f.read()

# Imports
if "UploadFile" not in main_content:
    main_content = main_content.replace(
        "from fastapi import FastAPI, Depends, HTTPException, status, Query",
        "from fastapi import FastAPI, Depends, HTTPException, status, Query, UploadFile, File\nimport os\nimport shutil\nfrom fastapi.responses import FileResponse"
    )

# CORS
if 'os.getenv("CORS_ORIGINS"' not in main_content:
    main_content = re.sub(
        r'allow_origins=\["\*"\]',
        'allow_origins=os.getenv("CORS_ORIGINS", "*").split(",")',
        main_content
    )

# WKT Validator and Upload setup
validator_str = """
os.makedirs("uploads", exist_ok=True)

def validate_wkt(db: Session, wkt: str):
    if not wkt: return
    is_valid = db.execute(text("SELECT ST_IsValid(ST_GeomFromText(:wkt, 4326))"), {"wkt": wkt}).scalar()
    if is_valid is False:
        raise HTTPException(status_code=400, detail="Geometría WKT inválida topológicamente (ej. cruces, puntos duplicados).")
"""
if "def validate_wkt" not in main_content:
    main_content = main_content.replace("def set_audit_context", validator_str + "\ndef set_audit_context")

# Apply validate_wkt to update_entity
if "validate_wkt(db, wkt)" not in main_content:
    main_content = main_content.replace(
        'if "geometria_wkt" in update_dict:\n        wkt = update_dict.pop("geometria_wkt")',
        'if "geometria_wkt" in update_dict:\n        wkt = update_dict.pop("geometria_wkt")\n        validate_wkt(db, wkt)'
    )

    # Apply validate_wkt to create_tramo
    main_content = main_content.replace(
        'wkt = data.pop("geometria_wkt")',
        'wkt = data.pop("geometria_wkt")\n    validate_wkt(db, wkt)'
    )

# Pagination for Tramos
if "skip: int = 0, limit: int = 100" not in main_content.split("def get_tramos")[1].split(":")[0]:
    main_content = re.sub(
        r'def get_tramos\(db: Session = Depends\(get_db\), current_user: models\.Usuario = Depends\(auth\.RoleChecker\(\[\'admin\', \'operador\', \'visualizador\', \'geografo\'\]\)\)\):\n    return db\.query\((.*?)\)\.filter\(models\.Tramo\.activo == True\)\.all\(\)',
        r'def get_tramos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker([\'admin\', \'operador\', \'visualizador\', \'geografo\']))):\n    return db.query(\1).filter(models.Tramo.activo == True).offset(skip).limit(limit).all()',
        main_content, flags=re.DOTALL
    )

# Pagination for Afectaciones
if "skip: int = 0, limit: int = 100" not in main_content.split("def list_afectaciones")[1].split(":")[0]:
    main_content = re.sub(
        r'def list_afectaciones\(id_tramo_nucleo: int = Query\(None\), tipo_afectacion: str = Query\(None\), db: Session = Depends\(get_db\), current_user: models\.Usuario = Depends\(auth\.RoleChecker\(\[\'admin\', \'operador\', \'visualizador\', \'geografo\'\]\)\)\):',
        r'def list_afectaciones(skip: int = 0, limit: int = 100, id_tramo_nucleo: int = Query(None), tipo_afectacion: str = Query(None), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker([\'admin\', \'operador\', \'visualizador\', \'geografo\']))):',
        main_content
    )
    main_content = main_content.replace('for a in query.all():', 'for a in query.offset(skip).limit(limit).all():')

# Pagination for Usuarios
if "skip: int = 0, limit: int = 100" not in main_content.split("def get_usuarios")[1].split(":")[0]:
    main_content = re.sub(
        r'def get_usuarios\(db: Session = Depends\(get_db\), current_user: models\.Usuario = Depends\(auth\.RoleChecker\(\[\'admin\'\]\)\)\):\n    return db\.query\(models\.Usuario\)\.filter\(models\.Usuario\.activo == True\)\.all\(\)',
        r'def get_usuarios(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker([\'admin\']))):\n    return db.query(models.Usuario).filter(models.Usuario.activo == True).offset(skip).limit(limit).all()',
        main_content
    )

# File Upload Endpoints
upload_endpoints = """
@app.post("/api/documentacion/{id_documento}/archivo")
def upload_archivo(id_documento: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador']))):
    doc = get_entity_by_id(db, models.DocumentacionSoporte, id_documento, "id_documento")
    
    file_extension = os.path.splitext(file.filename)[1]
    safe_filename = f"doc_{id_documento}{file_extension}"
    file_path = os.path.join("uploads", safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    set_audit_context(db, current_user.id_usuario)
    doc.url_archivo = file_path
    db.commit()
    return {"status": "success", "url": file_path}

@app.get("/api/documentacion/{id_documento}/archivo")
def download_archivo(id_documento: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'operador', 'visualizador', 'geografo']))):
    doc = get_entity_by_id(db, models.DocumentacionSoporte, id_documento, "id_documento")
    if not doc.url_archivo or not os.path.exists(doc.url_archivo):
        raise HTTPException(status_code=404, detail="Archivo físico no encontrado.")
    return FileResponse(doc.url_archivo, filename=os.path.basename(doc.url_archivo))
"""
if "/api/documentacion/{id_documento}/archivo" not in main_content:
    main_content += upload_endpoints

with open('/mnt/hdd/Users/lopez/Software-PA/backend/app/main.py', 'w') as f:
    f.write(main_content)

print("Refactor finished.")
