"""Crea perfiles de aceptación sin secretos versionados y los asigna por proyecto."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import auth, models
from app.database import DB_NAME, SessionLocal


EMAILS = {
    "geografo": "uat.geografo@pa.test",
    "operador": "uat.operador@pa.test",
    "visualizador": "uat.visualizador@pa.test",
}


def assert_environment() -> None:
    if os.getenv("APP_ENV", "").strip().lower() != "test" or "test" not in DB_NAME.lower():
        raise RuntimeError("Los usuarios UAT sólo pueden crearse en una DB_NAME aislada con APP_ENV=test")


def passwords() -> dict[str, str]:
    result = {}
    for role in EMAILS:
        name = f"UAT_{role.upper()}_PASSWORD"
        value = os.getenv(name, "")
        if len(value) < 12:
            raise RuntimeError(f"{name} es obligatoria y debe tener al menos 12 caracteres")
        result[role] = value
    return result


def seed() -> None:
    assert_environment()
    role_passwords = passwords()
    db = SessionLocal()
    try:
        with db.begin():
            actor = db.query(models.Usuario).filter(models.Usuario.activo.is_(True), models.Usuario.rol == "admin").order_by(models.Usuario.id_usuario).first()
            project = db.query(models.Proyecto).filter(models.Proyecto.clave_proyecto == "MEX-QRO", models.Proyecto.activo.is_(True)).one_or_none()
            if actor is None or project is None:
                raise RuntimeError("UAT requiere administrador seguro y seed objetivo MEX-QRO")
            db.execute(text('SET LOCAL "app.current_user_id" = :actor'), {"actor": str(actor.id_usuario)})
            for role, email in EMAILS.items():
                user = db.query(models.Usuario).filter(func.lower(func.btrim(models.Usuario.correo)) == email).one_or_none()
                if user is None:
                    user = models.Usuario(nombre="UAT", apellido_paterno=role.capitalize(), correo=email, contrasena_hash=auth.get_password_hash(role_passwords[role]), rol=role, activo=True, fecha_alta=datetime.now(timezone.utc))
                    db.add(user)
                    db.flush()
                else:
                    user.rol = role
                    user.contrasena_hash = auth.get_password_hash(role_passwords[role])
                    user.activo = True
                    user.fecha_baja = None
                    user.id_usuario_baja = None
                    user.motivo_baja = None
                assignment = db.query(models.UsuarioProyecto).filter(models.UsuarioProyecto.id_usuario == user.id_usuario, models.UsuarioProyecto.id_proyecto == project.id_proyecto, models.UsuarioProyecto.activo.is_(True)).one_or_none()
                if assignment is None:
                    db.add(models.UsuarioProyecto(id_usuario=user.id_usuario, id_proyecto=project.id_proyecto, asignado_por=actor.id_usuario, creado_por=actor.id_usuario))
        print("Perfiles UAT creados y asignados al proyecto MEX-QRO.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
