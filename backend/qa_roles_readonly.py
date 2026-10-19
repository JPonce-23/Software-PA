"""Verifica permisos sobre QA sin escribir registros; asignaciones con persistencia simulada."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from sqlalchemy import text
from fastapi import HTTPException
from app import models, schemas
from app.database import SessionLocal
from app.services import access, domain

checks = 0
with SessionLocal() as db:
    db.execute(text("SET TRANSACTION READ ONLY"))
    projects = db.query(models.Proyecto).filter(models.Proyecto.activo.is_(True)).all()
    all_ids = {p.id_proyecto for p in projects}
    assert all_ids, "Se necesita un proyecto activo para comprobar el alcance"
    for role in ("admin", "operador", "visualizador", "geografo"):
        # Cuenta no persistida y sin asignaciones; no suplantamos ni cambiamos usuarios.
        user = SimpleNamespace(id_usuario=-999, rol=role)
        ids = set(db.execute(access.authorized_project_ids(db, user)).scalars())
        assert ids == (set() if role == "operador" else all_ids)
        checks += 1
        for mode in ("read", "capture", "gis"):
            allowed = role == "admin" or role == "geografo" and mode in ("read", "gis") or role == "visualizador" and mode == "read"
            try:
                access.require_project_access(db, user, projects[0].id_proyecto, mode=mode, load_details=False)
                assert allowed, (role, mode)
            except HTTPException as exc:
                assert not allowed and exc.status_code == 403, (role, mode)
            checks += 1
    # Todos los nucleos de los proyectos asignados son accesibles al operador.
    operators = db.query(models.Usuario).filter(models.Usuario.rol == "operador", models.Usuario.activo.is_(True)).all()
    for user in operators:
        expected = {r.id_proyecto for r in db.query(models.UsuarioProyecto).filter(models.UsuarioProyecto.id_usuario == user.id_usuario, models.UsuarioProyecto.activo.is_(True)).all()} & all_ids
        assert set(db.execute(access.authorized_project_ids(db, user)).scalars()) == expected
        for pn in db.query(models.ProyectoNucleo).filter(models.ProyectoNucleo.id_proyecto.in_(expected), models.ProyectoNucleo.activo.is_(True)).all():
            access.require_project_nucleus_access(db, user, pn.id_proyecto_nucleo, mode="capture")
            checks += 1
    db.rollback()
for role in ("admin", "operador", "visualizador", "geografo"):
    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.populate_existing.return_value.first.return_value = SimpleNamespace(activo=True, rol=role)
    with patch.object(domain, "require_project_access"), patch.object(domain, "_persist") as persist:
        try:
            domain.assign_user_to_project(db, 1, schemas.UsuarioProyectoCreate(id_usuario=99), SimpleNamespace(id_usuario=1, rol="admin"))
            assert role == "operador"
            persist.assert_called_once()
        except HTTPException as exc:
            assert role != "operador" and exc.status_code == 422
            persist.assert_not_called()
        checks += 1
print(f"OK: {checks} comprobaciones; lectura sin escrituras y asignaciones simuladas")
