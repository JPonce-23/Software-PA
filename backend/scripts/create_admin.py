import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from sqlalchemy import text
from app.database import SessionLocal
from app import models
from app.auth import get_password_hash

def create_admin():
    db = SessionLocal()
    try:
        existente = db.query(models.Usuario).filter_by(correo="admin@sistema.com").first()
        if existente:
            print("El usuario admin ya existe, no se hace nada.")
            return

        # Desactivamos temporalmente los triggers de usuario para evitar
        # el problema de huevo-y-gallina con la tabla bitacora
        db.execute(text("ALTER TABLE usuario DISABLE TRIGGER USER"))

        admin = models.Usuario(
            nombre="Admin",
            apellido_paterno="Sistema",
            apellido_materno=None,
            correo="admin@sistema.com",
            contrasena_hash=get_password_hash("Admin123!"),
            rol="admin",
            activo=True,
            fecha_alta=datetime.utcnow()
        )
        db.add(admin)
        db.commit()

        db.execute(text("ALTER TABLE usuario ENABLE TRIGGER USER"))
        db.commit()

        print("Usuario admin creado correctamente.")

    except Exception as e:
        db.rollback()
        print(f"Error creando admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()