import re

with open('/mnt/hdd/Users/lopez/Software-PA/backend/app/main.py', 'r') as f:
    main_content = f.read()

# Add json import if not present
if "import json" not in main_content:
    main_content = main_content.replace("import os", "import os\nimport json")

geojson_endpoint = """
# ==================== GEOJSON IMPORTER ==================== #
@app.post("/api/geometria/importar-geojson")
def importar_geojson(
    tipo_entidad: str = Query(..., description="Opciones: tramo, frente, nucleo_agrario, tramo_nucleo, afectacion"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.RoleChecker(['admin', 'geografo']))
):
    \"\"\"
    Importa masivamente registros desde un archivo GeoJSON.
    Las 'properties' del GeoJSON deben coincidir con los nombres de las columnas de la tabla destino.
    \"\"\"
    # Mapeo de tablas y sus columnas espaciales
    mapa_entidades = {
        "tramo": (models.Tramo, "geometria_linea"),
        "frente": (models.Frente, "geometria_linea"),
        "nucleo_agrario": (models.NucleoAgrario, "geometria_poligono"),
        "tramo_nucleo": (models.TramoNucleo, "geometria_segmento"),
        "afectacion": (models.Afectacion, "geometria_afectacion")
    }

    if tipo_entidad not in mapa_entidades:
        raise HTTPException(status_code=400, detail="Tipo de entidad no soportado para importación GeoJSON.")

    Modelo, geom_column_name = mapa_entidades[tipo_entidad]

    try:
        content = file.file.read()
        geojson_data = json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Archivo GeoJSON inválido o malformado.")

    if "features" not in geojson_data:
        raise HTTPException(status_code=400, detail="El GeoJSON debe contener un arreglo de 'features'.")

    # Establecer contexto de auditoría
    set_audit_context(db, current_user.id_usuario)

    columnas_validas = [c.name for c in Modelo.__table__.columns]
    registros_insertados = 0

    for feature in geojson_data["features"]:
        propiedades = feature.get("properties", {})
        geometria = feature.get("geometry", None)

        if not geometria:
            continue

        # Filtrar propiedades para que solo queden las que existen en el modelo (ignorar id y geom_column)
        datos_limpios = {}
        for k, v in propiedades.items():
            if k in columnas_validas and k not in ["id", geom_column_name] and not k.startswith("id_"):
                datos_limpios[k] = v

        # Asegurar requerimientos de negocio o defaults
        if "activo" not in datos_limpios:
            datos_limpios["activo"] = True
            
        # Dependiendo del modelo, algunas columnas de fecha deben pasarse si no están
        if Modelo == models.Tramo or Modelo == models.Frente:
            if "fecha_registro" not in datos_limpios:
                datos_limpios["fecha_registro"] = datetime.now().date()
                
        if Modelo == models.NucleoAgrario:
            if "fecha_creacion" not in datos_limpios:
                datos_limpios["fecha_creacion"] = datetime.now()

        # Crear instancia del ORM
        nuevo_registro = Modelo(**datos_limpios)
        
        # Asignar geometría usando ST_GeomFromGeoJSON
        # Para que SQLAlchemy acepte la función cruda en la propiedad, usamos text() en un UPDATE, 
        # pero como es INSERT, lo mejor es hacer un flush() y luego un UPDATE, 
        # o asignar la propiedad en la creación usando db.scalar. 
        # Lo más limpio en GeoAlchemy2 es castear el string del geom:
        # Pero GeoAlchemy soporta WKT, no GeoJSON directo en asignación a propiedad.
        # Por lo tanto, guardamos temporalmente el registro sin geometría, hacemos flush y luego update con postgis.
        
        db.add(nuevo_registro)
        db.flush() # Obtenemos el ID generado
        
        pk_name = inspect(Modelo).primary_key[0].name
        pk_value = getattr(nuevo_registro, pk_name)

        # Actualizamos la geometría nativamente en PostGIS para asegurar conversión perfecta
        geom_str = json.dumps(geometria)
        stmt = text(f"UPDATE {Modelo.__tablename__} SET {geom_column_name} = ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326) WHERE {pk_name} = :id")
        db.execute(stmt, {"geom": geom_str, "id": pk_value})
        
        registros_insertados += 1

    db.commit()
    return {"status": "success", "mensaje": f"{registros_insertados} registros importados a la tabla {Modelo.__tablename__}."}
"""

if "/api/geometria/importar-geojson" not in main_content:
    # also add inspect to imports
    if "from sqlalchemy.inspection import inspect" not in main_content:
        main_content = main_content.replace(
            "from sqlalchemy import text",
            "from sqlalchemy import text\nfrom sqlalchemy.inspection import inspect"
        )
    main_content += geojson_endpoint

with open('/mnt/hdd/Users/lopez/Software-PA/backend/app/main.py', 'w') as f:
    f.write(main_content)

print("GeoJSON importer implemented.")
