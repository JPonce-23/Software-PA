import os
import sys
from sqlalchemy.orm import Session
from datetime import date

# Agregamos la raíz de backend al path para que pueda importar 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import SessionLocal, engine
from app import models

def seed_db():
    db: Session = SessionLocal()
    try:
        # Configuramos un usuario activo para auditoría (ID 1)
        db.execute(text("SET LOCAL app.current_user_id = '1'"))
        
        print("Buscando tramos existentes...")
        tramos_count = db.query(models.Tramo).count()
        if tramos_count > 0:
            print(f"Ya existen {tramos_count} tramos. No es necesario insertar mock data.")
            return

        print("Insertando tramos de prueba...")
        tramo1 = models.Tramo(
            clave_tramo="T1",
            nombre_tramo="Tramo 1 (Palenque - Escárcega)",
            descripcion="Tramo de prueba",
            ancho_total_derecho_via_m=40.00,
            fecha_registro=date.today()
        )
        tramo2 = models.Tramo(
            clave_tramo="T2",
            nombre_tramo="Tramo 2 (Escárcega - Calkiní)",
            descripcion="Tramo de prueba",
            ancho_total_derecho_via_m=40.00,
            fecha_registro=date.today()
        )
        db.add(tramo1)
        db.add(tramo2)
        db.commit()
        db.refresh(tramo1)
        db.refresh(tramo2)

        print("Insertando municipio y entidad...")
        # Check if entidad exists
        entidad = db.query(models.EntidadFederativa).filter_by(clave_inegi="04").first()
        if not entidad:
            entidad = models.EntidadFederativa(clave_inegi="04", nombre="Campeche")
            db.add(entidad)
            db.commit()
            db.refresh(entidad)
        
        municipio = db.query(models.Municipio).filter_by(clave_inegi="003").first()
        if not municipio:
            municipio = models.Municipio(id_entidad=entidad.id_entidad, clave_inegi="003", nombre="Escárcega")
            db.add(municipio)
            db.commit()
            db.refresh(municipio)

        print("Insertando núcleo de prueba...")
        nucleo1 = models.NucleoAgrario(
            id_municipio=municipio.id_municipio,
            nombre_nucleo="Ejido Escárcega",
            tipo_nucleo="ejido"
        )
        db.add(nucleo1)
        db.commit()
        db.refresh(nucleo1)
        
        print("Insertando frente de prueba...")
        frente1 = models.Frente(
            id_tramo=tramo1.id_tramo,
            clave_frente="F1-01",
            nombre_frente="Frente 1 Inicial",
            fecha_registro=date.today()
        )
        db.add(frente1)
        db.commit()
        db.refresh(frente1)
        
        print("Insertando tramo_nucleo (relación)...")
        tramo_nucleo1 = models.TramoNucleo(
            id_tramo=tramo1.id_tramo,
            id_frente=frente1.id_frente,
            id_nucleo=nucleo1.id_nucleo,
            consecutivo=1,
            numero_tramo="T1-01",
            longitud_m=5000.00
        )
        db.add(tramo_nucleo1)
        db.commit()

        print("¡Base de datos inicializada con datos de simulación!")
        
    except Exception as e:
        db.rollback()
        print(f"Error insertando datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
