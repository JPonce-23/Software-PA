import os
import bcrypt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from . import models, database
from .config import AUTH_SETTINGS
from .services import authentication as authentication_service

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("La variable de entorno SECRET_KEY es obligatoria.")

_SECRET_KEY_MIN_LENGTH = 32
_INSECURE_SECRET_MARKERS = (
    "change_me",
    "changeme",
    "default",
    "example",
    "secret_key",
)


def _is_insecure_secret_key(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        len(normalized) < _SECRET_KEY_MIN_LENGTH
        or any(marker in normalized for marker in _INSECURE_SECRET_MARKERS)
    )


if _is_insecure_secret_key(SECRET_KEY):
    raise RuntimeError(
        "La variable de entorno SECRET_KEY debe ser un secreto propio del "
        "entorno, no un placeholder, y tener al menos 32 caracteres."
    )

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def get_session_context(
    request: Request,
    db: Session = Depends(database.get_db),
) -> tuple[models.Usuario, models.SesionUsuario]:
    token = request.cookies.get(AUTH_SETTINGS.session_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo validar la sesión",
        )
    return authentication_service.authenticate_session(db, request, token)


def get_current_user(
    request: Request,
    db: Session = Depends(database.get_db),
):
    session_token = request.cookies.get(AUTH_SETTINGS.session_cookie_name)
    if session_token:
        user, _ = authentication_service.authenticate_session(
            db, request, session_token
        )
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
    )

class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user: models.Usuario = Depends(get_current_user)):
        if user.rol not in self.allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operación no permitida para este rol")
        return user
