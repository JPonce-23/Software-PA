import logging
import os
import time

from sqlalchemy import text

from .. import models
from ..database import SessionLocal


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def generate_alerts() -> int:
    with SessionLocal() as db:
        user_id = (
            db.query(models.Usuario.id_usuario)
            .filter(
                models.Usuario.activo.is_(True),
                models.Usuario.rol == "admin",
            )
            .order_by(models.Usuario.id_usuario)
            .scalar()
        )
        if user_id is None:
            raise RuntimeError("No existe un usuario administrador activo")
        inserted = db.execute(
            text("SELECT fn_generar_alertas_orv_vencidos(:user_id)"),
            {"user_id": user_id},
        ).scalar_one()
        db.commit()
        return inserted


def main() -> None:
    interval = int(os.getenv("ALERTAS_INTERVAL_SECONDS", "86400"))
    if interval < 60:
        raise RuntimeError("ALERTAS_INTERVAL_SECONDS debe ser al menos 60")
    while True:
        try:
            inserted = generate_alerts()
            logger.info("Alertas ORV generadas: %s", inserted)
            delay = interval
        except Exception:
            logger.exception("Falló la generación programada de alertas ORV")
            delay = min(interval, 300)
        time.sleep(delay)


if __name__ == "__main__":
    main()
