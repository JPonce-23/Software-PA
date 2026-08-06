import argparse
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models
from app.database import SessionLocal


def unlock_admin(email: str, reason: str) -> None:
    normalized_reason = reason.strip()
    if len(normalized_reason) < 10:
        raise RuntimeError("El motivo de recuperación debe tener al menos 10 caracteres")

    db = SessionLocal()
    try:
        user = (
            db.query(models.Usuario)
            .filter(
                models.Usuario.correo == email,
                models.Usuario.rol == "admin",
                models.Usuario.activo.is_(True),
            )
            .with_for_update()
            .one_or_none()
        )
        if user is None:
            raise RuntimeError("No existe un administrador activo con ese correo")
        state = (
            db.query(models.EstadoAutenticacionUsuario)
            .filter(
                models.EstadoAutenticacionUsuario.id_usuario == user.id_usuario
            )
            .with_for_update()
            .one()
        )
        event = models.EventoAcceso(
            id_usuario=user.id_usuario,
            id_usuario_actor=None,
            tipo_evento="desbloqueo",
            motivo_codigo="desbloqueo_recuperacion",
            detalle=normalized_reason[:200],
            fecha_hora=datetime.now(timezone.utc),
        )
        db.add(event)
        db.flush()
        db.execute(
            text("SELECT set_config('app.auth_event_id', :event_id, true)"),
            {"event_id": str(event.id_evento)},
        )
        state.intentos_fallidos = 0
        state.bloqueado_hasta = None
        state.actualizado_en = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Desbloquea de emergencia una cuenta administradora activa"
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    unlock_admin(args.email.strip(), args.reason)
    print("Cuenta administradora desbloqueada; evento de recuperación registrado.")


if __name__ == "__main__":
    main()
