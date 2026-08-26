"""Regression contract for the PostgreSQL LOGIN used by FastAPI."""

import os
import subprocess
import sys
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.database import DB_RUNTIME_USER, engine


AUDITED_RELATIONS = (
    "proyecto",
    "proyecto_nucleo",
    "afectacion",
    "convenio",
    "tramite_fifonafe",
    "indemnizacion",
    "pago",
)


def _sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None) or getattr(error.orig, "pgcode", None)


def _assert_insufficient_privilege(statement: str) -> None:
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with pytest.raises(DBAPIError) as denied:
                connection.execute(text(statement))
            assert _sqlstate(denied.value) == "42501", str(denied.value)
        finally:
            transaction.rollback()


def test_fastapi_connection_is_exclusively_runtime() -> None:
    assert DB_RUNTIME_USER
    assert DB_RUNTIME_USER not in {"software_pa_app", "pa_app"}
    with engine.connect() as connection:
        identity = connection.execute(text("SELECT current_user")).scalar_one()
    assert identity == DB_RUNTIME_USER


def test_database_configuration_never_falls_back_to_owner_variables() -> None:
    isolated_environment = os.environ.copy()
    isolated_environment.pop("DB_RUNTIME_USER", None)
    isolated_environment.pop("DB_RUNTIME_PASSWORD", None)
    isolated_environment.update(
        {
            "DB_USER": "forbidden_legacy_owner",
            "DB_PASSWORD": "not-a-secret-test-value",
            "POSTGRES_USER": "forbidden_bootstrap_owner",
            "POSTGRES_ADMIN_USER": "forbidden_admin_owner",
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", "import app.database"],
        cwd="/app",
        env=isolated_environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Configuración PostgreSQL runtime incompleta" in result.stderr
    assert "DB_RUNTIME_USER" in result.stderr
    assert "DB_RUNTIME_PASSWORD" in result.stderr


def test_runtime_role_is_non_owner_non_admin_and_public_create_is_denied() -> None:
    with engine.connect() as connection:
        role = connection.execute(
            text(
                """
                SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                       rolreplication, rolbypassrls
                FROM pg_roles
                WHERE rolname = current_user
                """
            )
        ).one()
        assert tuple(role) == (True, False, False, False, False, False)

        application_role = connection.execute(
            text(
                """
                SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                       rolreplication, rolbypassrls
                FROM pg_roles
                WHERE rolname = 'software_pa_app'
                """
            )
        ).one()
        assert tuple(application_role) == (False, False, False, False, False, False)

        memberships = connection.execute(
            text(
                """
                SELECT parent.rolname
                FROM pg_auth_members membership
                JOIN pg_roles parent ON parent.oid = membership.roleid
                JOIN pg_roles member ON member.oid = membership.member
                WHERE member.rolname = current_user
                ORDER BY parent.rolname
                """
            )
        ).scalars().all()
        assert memberships == ["software_pa_app"]

        schema_owner = connection.execute(
            text(
                """
                SELECT pg_get_userbyid(nspowner)
                FROM pg_namespace
                WHERE nspname = 'public'
                """
            )
        ).scalar_one()
        assert schema_owner != DB_RUNTIME_USER

        owners = connection.execute(
            text(
                """
                SELECT relname, pg_get_userbyid(relowner)
                FROM pg_class
                WHERE relnamespace = 'public'::regnamespace
                  AND relname = ANY(:relations)
                ORDER BY relname
                """
            ),
            {"relations": list(AUDITED_RELATIONS)},
        ).all()
        assert len(owners) == len(AUDITED_RELATIONS)
        assert all(owner != DB_RUNTIME_USER for _, owner in owners)
        assert connection.execute(
            text("SELECT has_schema_privilege(current_user, 'public', 'CREATE')")
        ).scalar_one() is False


def test_runtime_select_insert_update_are_real_and_transactional() -> None:
    marker = f"RT-PY-{uuid.uuid4().hex[:20]}"
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            actor = connection.execute(
                text("SELECT id_usuario FROM usuario WHERE activo ORDER BY id_usuario LIMIT 1")
            ).scalar_one()
            connection.execute(
                text("SELECT set_config('app.current_user_id', :actor, true)"),
                {"actor": str(actor)},
            )
            project_id = connection.execute(
                text(
                    """
                    INSERT INTO proyecto (clave_proyecto, nombre_proyecto)
                    VALUES (:marker, 'Prueba runtime pytest')
                    RETURNING id_proyecto
                    """
                ),
                {"marker": marker},
            ).scalar_one()
            updated = connection.execute(
                text(
                    """
                    UPDATE proyecto
                    SET nombre_proyecto = 'Prueba runtime actualizada'
                    WHERE id_proyecto = :project_id
                    RETURNING nombre_proyecto
                    """
                ),
                {"project_id": project_id},
            ).scalar_one()
            assert updated == "Prueba runtime actualizada"
        finally:
            transaction.rollback()


@pytest.mark.parametrize(
    "statement",
    (
        "DELETE FROM proyecto WHERE false",
        "TRUNCATE TABLE proyecto",
        "CREATE TABLE public.runtime_forbidden_pytest (id integer)",
        "ALTER TABLE proyecto ADD COLUMN runtime_forbidden_pytest text",
        "DROP TABLE proyecto",
    ),
)
def test_runtime_destructive_ddl_and_dml_are_denied(statement: str) -> None:
    _assert_insufficient_privilege(statement)
