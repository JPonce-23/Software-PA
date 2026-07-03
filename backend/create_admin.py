import sys
from sqlalchemy import text
from app.database import SessionLocal
from app.models import Usuario
from app.auth import get_password_hash
from datetime import datetime, timezone

def create_admin():
    db = SessionLocal()
    # Check if admin already exists
    admin = db.query(Usuario).filter(Usuario.correo == "admin@sistema.com").first()
    if admin:
        print("El usuario admin@sistema.com ya existe.")
        return

    # Create admin
    nuevo_admin = Usuario(
        nombre="Administrador",
        apellido_paterno="Sistema",
        correo="admin@sistema.com",
        contrasena_hash=get_password_hash("Admin123!"),
        rol="admin",
        fecha_alta=datetime.now(timezone.utc),
        activo=True
    )
    db.execute(text("SET LOCAL app.current_user_id = '1'"))
    db.add(nuevo_admin)
    db.commit()
    print("   Usuario administrador creado con éxito:")
    print("   Correo: admin@sistema.com")
    print("   Contraseña: Admin123!")

if __name__ == "__main__":
    create_admin()
