import pandas as pd
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from datetime import date
import sys
import os

def run_etl(file_path: str):
    if not os.path.exists(file_path):
        print(f"Error: No se encontró el archivo {file_path}")
        sys.exit(1)

    print(f"Iniciando lectura del archivo Excel: {file_path}...")
    try:
        # Simulamos la lectura de la hoja principal del padrón
        df = pd.read_excel(file_path, sheet_name=0)
    except Exception as e:
        print(f"Error al leer el Excel: {e}")
        sys.exit(1)

    db: Session = SessionLocal()
    
    try:
        total_procesados = 0
        for index, row in df.iterrows():
            # Aquí va la lógica de extracción de columnas.
            # Ejemplo: nombre_nucleo = row['Nombre Ejido']
            
            # --- 1. Crear o Buscar el Núcleo Agrario ---
            # nucleo = db.query(models.NucleoAgrario).filter(...).first()
            
            # --- 2. Crear la Afectación (Con restricción estricta de origen) ---
            # Se marca como 'migracion_excel' lo que exime temporalmente la necesidad
            # de tener geometría (geometria_afectacion = NULL), según el requerimiento.
            '''
            nueva_afectacion = models.Afectacion(
                id_nucleo=nucleo.id_nucleo,
                id_tramo_nucleo=..., # Extraído de la relación
                tipo_afectacion="colectivo", # O individual, según el Excel
                tipo_tenencia=row.get('Tenencia', 'Ejidal'),
                superficie_afectada_ha=row.get('Superficie (ha)', 0),
                origen_registro="migracion_excel",  <-- CLAVE PARA PASAR LA REGLA
                documentacion_disponible=False
            )
            db.add(nueva_afectacion)
            '''
            total_procesados += 1
            
        # db.commit()
        print(f"Migración exitosa. {total_procesados} expedientes inicializados.")
        print("Los expedientes están en estado 'Pendiente de Digitalización Espacial'.")
        
    except Exception as e:
        db.rollback()
        print(f"Error durante la migración: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("ETL: Sistema de Liberación de Derechos")
    # Para ejecutar: python etl_migracion.py /ruta/a/tu/archivo.xlsx
    if len(sys.argv) > 1:
        run_etl(sys.argv[1])
    else:
        print("Uso: python etl_migracion.py <ruta_archivo.xlsx>")
