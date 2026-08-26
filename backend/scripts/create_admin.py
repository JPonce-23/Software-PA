import getpass
import os
import re
import sys
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models
from app.auth import get_password_hash
from app.database import SessionLocal


PLACEHOLDER_MARKERS = ("change_me", "changeme", "example", "password")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class BootstrapError(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise BootstrapError(f"{name} es obligatoria.")
    return value


def _database_session_factory():
    """Use owner credentials only for an explicitly requested bootstrap."""
    if os.getenv("ADMIN_DATABASE_MODE", "runtime").strip().lower() != "owner":
        return SessionLocal, None

    owner_user = _required_env("POSTGRES_ADMIN_USER")
    owner_password = _required_env("POSTGRES_ADMIN_PASSWORD")
    owner_engine = create_engine(
        URL.create(
            drivername="postgresql",
            username=owner_user,
            password=owner_password,
            host=_required_env("DB_HOST"),
            port=int(_required_env("DB_PORT")),
            database=_required_env("DB_NAME"),
        ),
        pool_pre_ping=True,
    )
    return sessionmaker(autocommit=False, autoflush=False, bind=owner_engine), owner_engine


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        any(marker in normalized for marker in PLACEHOLDER_MARKERS)
        or normalized in {"admin123", "admin123!", "secret", "secret123"}
        or normalized.endswith("@sistema.com")
        or normalized.endswith("@example.local")
    )


def validate_admin_config(email: str, password: str, nombre: str, apellido: str) -> None:
    if not email or not EMAIL_RE.match(email) or _is_placeholder(email):
        raise BootstrapError("ADMIN_EMAIL debe ser un correo real del entorno.")
    if not nombre or _is_placeholder(nombre):
        raise BootstrapError("ADMIN_NOMBRE debe ser un nombre real del responsable.")
    if not apellido or _is_placeholder(apellido):
        raise BootstrapError("ADMIN_APELLIDO_PATERNO debe ser un apellido real.")
    if not password or len(password) < 12:
        raise BootstrapError("ADMIN_PASSWORD debe tener al menos 12 caracteres.")
    if _is_placeholder(password):
        raise BootstrapError("ADMIN_PASSWORD no puede ser un placeholder.")
    checks = (
        any(char.islower() for char in password),
        any(char.isupper() for char in password),
        any(char.isdigit() for char in password),
        any(not char.isalnum() for char in password),
    )
    if not all(checks):
        raise BootstrapError(
            "ADMIN_PASSWORD debe incluir mayúscula, minúscula, número y símbolo."
        )


def _read_password() -> str:
    env_password = os.getenv("ADMIN_PASSWORD")
    if env_password:
        return env_password
    if not sys.stdin.isatty():
        raise BootstrapError(
            "Define ADMIN_PASSWORD o ejecuta el script en una terminal interactiva."
        )
    password = getpass.getpass("Contraseña inicial del administrador: ")
    confirm = getpass.getpass("Confirma la contraseña: ")
    if password != confirm:
        raise BootstrapError("Las contraseñas no coinciden.")
    return password


def get_admin_config() -> dict[str, str | None]:
    email = os.getenv("ADMIN_EMAIL", "").strip()
    nombre = os.getenv("ADMIN_NOMBRE", "").strip()
    apellido = os.getenv("ADMIN_APELLIDO_PATERNO", "").strip()
    apellido_materno = os.getenv("ADMIN_APELLIDO_MATERNO")
    password = _read_password()
    validate_admin_config(email, password, nombre, apellido)
    return {
        "email": email,
        "password": password,
        "nombre": nombre,
        "apellido_paterno": apellido,
        "apellido_materno": apellido_materno.strip() if apellido_materno else None,
    }


def create_admin() -> None:
    config = get_admin_config()
    session_factory, owner_engine = _database_session_factory()
    db = session_factory()
    triggers_disabled = False
    try:
        existente = (
            db.query(models.Usuario)
            .filter_by(correo=config["email"])
            .first()
        )
        if existente:
            print("El usuario administrador indicado ya existe; no se hace nada.")
            return

        total_usuarios = db.query(models.Usuario.id_usuario).count()
        if total_usuarios == 0:
            # Primer usuario: la auditoría normal aún no tiene un actor válido.
            # Se desactiva sólo el trigger de bitácora; los triggers de
            # integridad y la inicialización del estado auth permanecen activos.
            db.execute(
                text("ALTER TABLE usuario DISABLE TRIGGER trg_audit_usuario")
            )
            triggers_disabled = True
        else:
            actor = (
                db.query(models.Usuario.id_usuario)
                .filter(models.Usuario.rol == "admin", models.Usuario.activo.is_(True))
                .order_by(models.Usuario.id_usuario)
                .first()
            )
            if actor is None:
                raise BootstrapError(
                    "Ya existen usuarios, pero no hay un administrador activo "
                    "para auditar la creación."
                )
            db.execute(
                text('SET LOCAL "app.current_user_id" = :id_usuario'),
                {"id_usuario": str(actor[0])},
            )

        admin = models.Usuario(
            nombre=config["nombre"],
            apellido_paterno=config["apellido_paterno"],
            apellido_materno=config["apellido_materno"],
            correo=config["email"],
            contrasena_hash=get_password_hash(config["password"]),
            rol="admin",
            activo=True,
            fecha_alta=datetime.now(timezone.utc),
        )
        db.add(admin)
        db.commit()
        print("Usuario administrador creado correctamente.")

    except Exception:
        db.rollback()
        raise
    finally:
        if triggers_disabled:
            try:
                db.execute(
                    text("ALTER TABLE usuario ENABLE TRIGGER trg_audit_usuario")
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
        db.close()
        if owner_engine is not None:
            owner_engine.dispose()


if __name__ == "__main__":
    try:
        create_admin()
    except BootstrapError as exc:
        print(f"No se creó el administrador: {exc}", file=sys.stderr)
        raise SystemExit(1)
