import sys
from app.database import SessionLocal
from app.models import Usuario
from app.auth import get_password_hash
from sqlalchemy import text

def reset_password():
    # CAMBIA ESTE CORREO POR EL DE TU OTRO USUARIO ADMIN
    correo_usuario = "TU_OTRO_CORREO_AQUI@ejemplo.com"
    nueva_contrasena = "Admin123!"
    
    db = SessionLocal()
    user = db.query(Usuario).filter(Usuario.correo == correo_usuario).first()
    
    if not user:
        print(f"❌ No se encontró ningún usuario con el correo: {correo_usuario}")
        return
        
    db.execute(text("SET LOCAL app.current_user_id = '1'"))
    user.contrasena_hash = get_password_hash(nueva_contrasena)
    db.commit()
    
    print(f"✅ Contraseña actualizada con éxito para {correo_usuario}.")
    print(f"Ya puedes iniciar sesión con la contraseña: {nueva_contrasena}")

if __name__ == "__main__":
    reset_password()
