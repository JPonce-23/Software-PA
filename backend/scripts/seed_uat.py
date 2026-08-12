"""Crea un escenario UAT mínimo e idempotente en una base aislada."""

import os
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, text

from app import auth, models
from app.database import DB_NAME, SessionLocal


EMAILS = {
    "admin": "uat.admin@pa.test",
    "geografo": "uat.geografo@pa.test",
    "operador": "uat.operador@pa.test",
    "visualizador": "uat.visualizador@pa.test",
}


def _assert_uat_environment() -> None:
    environment = os.getenv("APP_ENV", "").strip().lower()
    database_name = DB_NAME.strip().lower()
    if environment != "test" or not any(marker in database_name for marker in ("_test", "test_", "_uat", "uat_")):
        raise RuntimeError(
            "El fixture UAT exige APP_ENV=test y una DB_NAME aislada con marcador test/uat."
        )


def _passwords() -> dict[str, str]:
    values = {}
    for role in EMAILS:
        name = f"UAT_{role.upper()}_PASSWORD"
        value = os.getenv(name, "")
        if len(value) < 12:
            raise RuntimeError(f"{name} es obligatoria y debe tener al menos 12 caracteres")
        values[role] = value
    return values


def _set_audit_context(db, actor_id: int) -> None:
    db.execute(
        text('SET LOCAL "app.current_user_id" = :actor_id'),
        {"actor_id": str(actor_id)},
    )


def _reactivate(entity, actor_id: int, reason: str) -> None:
    if entity.activo:
        return
    entity.activo = True
    entity.fecha_reactivacion = datetime.now(timezone.utc)
    entity.id_usuario_reactivacion = actor_id
    entity.motivo_reactivacion = reason


def seed() -> None:
    _assert_uat_environment()
    passwords = _passwords()
    db = SessionLocal()
    try:
        with db.begin():
            actor = db.query(models.Usuario).filter(
                models.Usuario.activo.is_(True),
                models.Usuario.rol == "admin",
            ).order_by(models.Usuario.id_usuario).first()
            if actor is None:
                raise RuntimeError("La base UAT requiere un administrador bootstrap activo")
            _set_audit_context(db, actor.id_usuario)

            users = {}
            for role, email in EMAILS.items():
                user = db.query(models.Usuario).filter(
                    func.lower(func.btrim(models.Usuario.correo)) == email
                ).one_or_none()
                if user is None:
                    user = models.Usuario(
                        nombre="UAT",
                        apellido_paterno=role.capitalize(),
                        correo=email,
                        contrasena_hash=auth.get_password_hash(passwords[role]),
                        rol=role,
                        activo=True,
                        fecha_alta=datetime.now(timezone.utc),
                    )
                    db.add(user)
                    db.flush()
                else:
                    _reactivate(user, actor.id_usuario, "Preparación del escenario UAT")
                    user.rol = role
                    user.contrasena_hash = auth.get_password_hash(passwords[role])
                users[role] = user

            project = db.query(models.Proyecto).filter_by(clave_proyecto="UAT-PA").one_or_none()
            if project is None:
                project = models.Proyecto(
                    clave_proyecto="UAT-PA",
                    nombre_proyecto="Escenario de aceptación territorial",
                    descripcion="Datos sintéticos y desechables para recorrido funcional",
                    fecha_registro=date.today(),
                    activo=True,
                )
                db.add(project)
                db.flush()
            else:
                _reactivate(project, actor.id_usuario, "Preparación del escenario UAT")

            tramo_specs = (
                (
                    "UAT-A", "Tramo UAT asignado",
                    "MULTILINESTRING((-90.00 20.00,-89.99 20.01))",
                    "MULTIPOLYGON(((-90.005 19.995,-89.985 19.995,-89.985 20.015,-90.005 20.015,-90.005 19.995)))",
                ),
                (
                    "UAT-B", "Tramo UAT de aislamiento",
                    "MULTILINESTRING((-90.02 20.00,-90.01 20.01))",
                    "MULTIPOLYGON(((-90.025 19.995,-90.005 19.995,-90.005 20.015,-90.025 20.015,-90.025 19.995)))",
                ),
            )
            tramos = []
            for key, name, geometry, franja_geometry in tramo_specs:
                tramo = db.query(models.Tramo).filter_by(
                    id_proyecto=project.id_proyecto,
                    clave_tramo=key,
                ).one_or_none()
                if tramo is None:
                    tramo = models.Tramo(
                        id_proyecto=project.id_proyecto,
                        clave_tramo=key,
                        nombre_tramo=name,
                        ancho_total_derecho_via_m=Decimal("40.00"),
                        geometria_linea=geometry,
                        fecha_registro=date.today(),
                        activo=True,
                    )
                    db.add(tramo)
                    db.flush()
                else:
                    _reactivate(tramo, actor.id_usuario, "Preparación del escenario UAT")
                tramos.append(tramo)
                active_franja = db.query(models.FranjaDerechoVia).filter_by(
                    id_tramo=tramo.id_tramo,
                    activo=True,
                ).one_or_none()
                if active_franja is None:
                    next_version = (db.query(func.coalesce(func.max(models.FranjaDerechoVia.version), 0))
                                    .filter_by(id_tramo=tramo.id_tramo).scalar() + 1)
                    db.add(models.FranjaDerechoVia(
                        id_tramo=tramo.id_tramo,
                        version=next_version,
                        ancho_izquierdo_m=Decimal("20.00"),
                        ancho_derecho_m=Decimal("20.00"),
                        geometria_poligono=franja_geometry,
                        fuente="Fixture UAT sintético",
                        fecha_vigencia_inicio=date.today(),
                        activo=True,
                    ))

            municipality = db.query(models.Municipio).filter(models.Municipio.activo.is_(True)).first()
            if municipality is None:
                raise RuntimeError("La base UAT requiere al menos un municipio activo")
            nuclei_specs = (
                ("Ejido UAT Norte", "MULTIPOLYGON(((-90.01 19.99,-89.98 19.99,-89.98 20.02,-90.01 20.02,-90.01 19.99)))"),
                ("Ejido UAT Sur", "MULTIPOLYGON(((-90.03 19.99,-90.00 19.99,-90.00 20.02,-90.03 20.02,-90.03 19.99)))"),
            )
            nuclei = []
            for name, geometry in nuclei_specs:
                nucleus = db.query(models.NucleoAgrario).filter_by(nombre_nucleo=name).one_or_none()
                if nucleus is None:
                    nucleus = models.NucleoAgrario(
                        id_municipio=municipality.id_municipio,
                        nombre_nucleo=name,
                        tipo_nucleo="ejido",
                        comunidad_indigena=False,
                        geometria_poligono=geometry,
                        fecha_creacion=datetime.now(timezone.utc),
                        activo=True,
                    )
                    db.add(nucleus)
                    db.flush()
                else:
                    _reactivate(nucleus, actor.id_usuario, "Preparación del escenario UAT")
                nuclei.append(nucleus)

            for index, (tramo, nucleus) in enumerate(zip(tramos, nuclei), start=1):
                relation = db.query(models.TramoNucleo).filter_by(
                    id_tramo=tramo.id_tramo,
                    id_nucleo=nucleus.id_nucleo,
                ).one_or_none()
                if relation is None:
                    relation = models.TramoNucleo(
                        id_tramo=tramo.id_tramo,
                        id_nucleo=nucleus.id_nucleo,
                        consecutivo=9000 + index,
                        numero_tramo=f"UAT-{index}",
                        geometria_segmento=tramo_specs[index - 1][2],
                        activo=True,
                    )
                    db.add(relation)
                else:
                    _reactivate(relation, actor.id_usuario, "Preparación del escenario UAT")

            parcel = db.query(models.Parcela).filter_by(
                id_nucleo=nuclei[0].id_nucleo,
                no_parcela_ppt="UAT-001",
            ).one_or_none()
            if parcel is None:
                db.add(models.Parcela(
                    id_nucleo=nuclei[0].id_nucleo,
                    tipo_parcela="individual",
                    no_parcela_ppt="UAT-001",
                    nombre_titular="Titular sintético UAT",
                    documentacion_disponible=False,
                    documentacion_faltante="Escenario para captura documental",
                    activo=True,
                ))
            else:
                _reactivate(parcel, actor.id_usuario, "Preparación del escenario UAT")

            desired = {
                users["geografo"].id_usuario,
                users["operador"].id_usuario,
                users["visualizador"].id_usuario,
            }
            for user_id in desired:
                assignment = db.query(models.UsuarioTramo).filter_by(
                    id_usuario=user_id,
                    id_tramo=tramos[0].id_tramo,
                ).one_or_none()
                if assignment is None:
                    db.add(models.UsuarioTramo(
                        id_usuario=user_id,
                        id_tramo=tramos[0].id_tramo,
                        fecha_asignacion=datetime.now(timezone.utc),
                        activo=True,
                    ))
                else:
                    _reactivate(assignment, actor.id_usuario, "Preparación del escenario UAT")
                    assignment.fecha_asignacion = datetime.now(timezone.utc)
        print("Fixture UAT preparado en una sola transacción.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
