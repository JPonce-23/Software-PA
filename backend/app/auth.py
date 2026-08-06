from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import os
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
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

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # RNF-9: Vigencia estricta de 30 minutos

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def _get_bearer_user(token: str, db: Session) -> models.Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        correo: str = payload.get("sub")
        if correo is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.Usuario).filter(models.Usuario.correo == correo).first()
    if user is None or not user.activo:
        raise credentials_exception
    return user


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
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
):
    session_token = request.cookies.get(AUTH_SETTINGS.session_cookie_name)
    if token and session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se proporcionaron credenciales ambiguas",
        )
    if session_token:
        user, _ = authentication_service.authenticate_session(
            db, request, session_token
        )
        return user
    if token:
        return _get_bearer_user(token, db)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user: models.Usuario = Depends(get_current_user)):
        if user.rol not in self.allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operación no permitida para este rol")
        return user
