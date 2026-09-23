"""Contrato de base de datos para el ciclo de vida ORV/Persona de schema 018."""

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app import models
from app.database import SessionLocal, engine
from app.services.common import set_audit_context

from .test_excel_closure_002 import _isolated_pn


EXPECTED_FINISH_CODES = {
    "termino_periodo",
    "remocion_asamblea",
    "sustitucion",
    "fallecimiento",
    "correccion",
    "otro",
}


def test_018_catalog_columns_and_foreign_key(transactional_api):
    connection = transactional_api["connection"]
    codes = set(
        connection.execute(
            text(
                """
                SELECT codigo
                  FROM catalogo_operativo
                 WHERE tipo_catalogo = 'tipo_fin_orv_integrante' AND activo
                """
            )
        ).scalars()
    )
    assert EXPECTED_FINISH_CODES <= codes

    columns = set(
        connection.execute(
            text(
                """
                SELECT column_name
                  FROM information_schema.columns
                 WHERE table_schema = 'public'
                   AND table_name = 'orv_integrante'
                """
            )
        ).scalars()
    )
    assert {"id_tipo_fin", "detalle_fin"} <= columns
    assert "vigente" not in columns

    fk = connection.execute(
        text(
            """
            SELECT confrelid::regclass::text
              FROM pg_constraint
             WHERE conrelid = 'orv_integrante'::regclass
               AND conname = 'orv_integrante_id_tipo_fin_fkey'
            """
        )
    ).scalar_one()
    assert fk == "catalogo_operativo"


def test_018_overlap_is_a_database_exclusion_constraint(transactional_api):
    row = transactional_api["connection"].execute(
        text(
            """
            SELECT contype, pg_get_constraintdef(oid)
              FROM pg_constraint
             WHERE conrelid = 'orv_integrante'::regclass
               AND conname = 'ex_orv_integrante_slot_periodo'
            """
        )
    ).one()
    assert row.contype == "x"
    definition = row[1]
    assert "EXCLUDE USING gist" in definition
    assert "daterange(fecha_inicio, fecha_fin, '[]'::text) WITH &&" in definition
    assert "WHERE (activo)" in definition


def test_018_exclusion_constraint_enforces_real_period_cases(
    transactional_api, transactional_target_domain
):
    api = transactional_api["request"]
    connection = transactional_api["connection"]
    project, pn = _isolated_pn(api, transactional_target_domain)

    def catalog(kind):
        return {
            row["codigo"]: row["id_catalogo_opcion"]
            for row in api("GET", f"/api/catalogos/operativos/{kind}").json()
        }

    organ = catalog("organo_orv")["comisariado"]
    cargo = catalog("cargo_orv")["presidente"]
    qualities = catalog("calidad_integrante_orv")
    finish_type = catalog("tipo_fin_orv_integrante")["termino_periodo"]
    actor = connection.execute(
        text("SELECT min(id_usuario) FROM usuario WHERE activo AND rol='admin'")
    ).scalar_one()

    def person(label):
        return api(
            "POST",
            f"/api/proyectos/{project['id_proyecto']}/personas",
            expected=201,
            json={
                "nombre": f"GiST {label} {uuid.uuid4().hex}",
                "datos_identidad_incompletos": True,
                "origen_registro": "qa",
            },
        ).json()["id_persona"]

    def orv(label):
        return api(
            "POST",
            f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/orv",
            expected=201,
            json={"numero_orv": f"GIST-{label}-{uuid.uuid4().hex}"},
        ).json()["id_orv"]

    def insert_member(orv_id, person_id, start, end, quality, *, active=True):
        return connection.execute(
            text(
                """
                INSERT INTO orv_integrante(
                    id_orv,id_persona,id_organo,id_cargo,id_calidad,
                    fecha_inicio,fecha_fin,id_tipo_fin,activo,creado_por,
                    fecha_baja,id_usuario_baja,motivo_baja
                ) VALUES (
                    :orv,:person,:organ,:cargo,:quality,:start,:end,
                    CASE WHEN :end IS NULL THEN NULL ELSE :finish_type END,
                    :active,:actor,
                    CASE WHEN :active THEN NULL ELSE now() END,
                    CASE WHEN :active THEN NULL ELSE :actor END,
                    CASE WHEN :active THEN NULL ELSE 'Registro QA inactivo' END
                ) RETURNING id_orv_integrante
                """
            ),
            {
                "orv": orv_id,
                "person": person_id,
                "organ": organ,
                "cargo": cargo,
                "quality": quality,
                "start": start,
                "end": end,
                "finish_type": finish_type,
                "active": active,
                "actor": actor,
            },
        ).scalar_one()

    def rejected(action):
        savepoint = connection.begin_nested()
        with pytest.raises(DBAPIError):
            action()
        savepoint.rollback()

    # A: traslape del mismo slot.
    target = orv("OVERLAP")
    insert_member(target, person("A1"), date(2026, 1, 1), date(2026, 12, 31), qualities["propietario"])
    conflicting_person = person("A2")
    rejected(lambda: insert_member(target, conflicting_person, date(2026, 6, 1), date(2027, 1, 1), qualities["propietario"]))

    # B: periodos consecutivos; fecha_fin es inclusiva.
    target = orv("CONSECUTIVE")
    insert_member(target, person("B1"), date(2026, 1, 1), date(2026, 6, 30), qualities["propietario"])
    insert_member(target, person("B2"), date(2026, 7, 1), date(2027, 1, 1), qualities["propietario"])

    # C: propietario y suplente simultáneos.
    target = orv("QUALITY")
    insert_member(target, person("C1"), date(2026, 1, 1), None, qualities["propietario"])
    insert_member(target, person("C2"), date(2026, 1, 1), None, qualities["suplente"])

    # D: un registro administrativamente inactivo no bloquea.
    target = orv("INACTIVE")
    insert_member(target, person("D1"), date(2026, 1, 1), date(2026, 12, 31), qualities["propietario"], active=False)
    insert_member(target, person("D2"), date(2026, 1, 1), date(2026, 12, 31), qualities["propietario"])

    # E: dos rangos totalmente abiertos se traslapan.
    target = orv("OPEN-OPEN")
    insert_member(target, person("E1"), None, None, qualities["propietario"])
    conflicting_person = person("E2")
    rejected(lambda: insert_member(target, conflicting_person, None, None, qualities["propietario"]))

    # F: rango abierto contra rango finito coincidente.
    target = orv("OPEN-FINITE")
    insert_member(target, person("F1"), date(2026, 1, 1), date(2026, 12, 31), qualities["propietario"])
    conflicting_person = person("F2")
    rejected(lambda: insert_member(target, conflicting_person, None, None, qualities["propietario"]))

    # G (DB): la reactivación vuelve a entrar al predicado parcial.
    target = orv("REACTIVATE")
    inactive_id = insert_member(target, person("G1"), date(2026, 1, 1), None, qualities["propietario"], active=False)
    insert_member(target, person("G2"), date(2026, 6, 1), None, qualities["propietario"])
    rejected(
        lambda: connection.execute(
            text(
                """
                UPDATE orv_integrante
                   SET activo=true,fecha_baja=NULL,id_usuario_baja=NULL,motivo_baja=NULL
                 WHERE id_orv_integrante=:id
                """
            ),
            {"id": inactive_id},
        )
    )
    assert connection.execute(
        text("SELECT activo FROM orv_integrante WHERE id_orv_integrante=:id"),
        {"id": inactive_id},
    ).scalar_one() is False


def test_018_exclusion_constraint_serializes_concurrent_inserts():
    with SessionLocal() as db:
        user = db.query(models.Usuario).filter(
            models.Usuario.rol == "admin", models.Usuario.activo.is_(True)
        ).order_by(models.Usuario.id_usuario).first()
        nucleus = db.query(models.NucleoAgrario).filter(
            models.NucleoAgrario.activo.is_(True)
        ).order_by(models.NucleoAgrario.id_nucleo).first()
        assert user is not None and nucleus is not None

        def catalog(kind, code):
            return db.query(models.CatalogoOperativo.id_catalogo_opcion).filter(
                models.CatalogoOperativo.tipo_catalogo == kind,
                models.CatalogoOperativo.codigo == code,
                models.CatalogoOperativo.activo.is_(True),
            ).scalar()

        set_audit_context(db, user.id_usuario)
        orv = models.Orv(
            id_nucleo=nucleus.id_nucleo,
            numero_orv=f"GIST-CONCURRENT-{uuid.uuid4().hex}",
            creado_por=user.id_usuario,
        )
        people = [
            models.Persona(
                nombre=f"GiST concurrente {index} {uuid.uuid4().hex}",
                datos_identidad_incompletos=True,
                origen_registro="qa",
                creado_por=user.id_usuario,
            )
            for index in (1, 2)
        ]
        db.add_all([orv, *people])
        db.commit()
        fixture = {
            "orv": orv.id_orv,
            "people": [person.id_persona for person in people],
            "organ": catalog("organo_orv", "comisariado"),
            "cargo": catalog("cargo_orv", "presidente"),
            "quality": catalog("calidad_integrante_orv", "propietario"),
            "actor": user.id_usuario,
        }

    insert_sql = text(
        """
        INSERT INTO orv_integrante(
            id_orv,id_persona,id_organo,id_cargo,id_calidad,
            fecha_inicio,activo,creado_por
        ) VALUES (:orv,:person,:organ,:cargo,:quality,DATE '2050-01-01',true,:actor)
        RETURNING id_orv_integrante
        """
    )
    first_inserted = threading.Event()
    release_first = threading.Event()
    second_pid_ready = threading.Event()
    second_pid = {}

    def first_transaction():
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                set_audit_context(__import__("sqlalchemy.orm", fromlist=["Session"]).Session(bind=connection), fixture["actor"])
                member_id = connection.execute(
                    insert_sql, {**fixture, "person": fixture["people"][0]}
                ).scalar_one()
                first_inserted.set()
                assert release_first.wait(timeout=10)
                transaction.commit()
                return ("committed", member_id)
            except Exception:
                transaction.rollback()
                raise

    def second_transaction():
        assert first_inserted.wait(timeout=10)
        with engine.connect() as connection:
            transaction = connection.begin()
            second_pid["value"] = connection.execute(
                text("SELECT pg_backend_pid()")
            ).scalar_one()
            second_pid_ready.set()
            try:
                member_id = connection.execute(
                    insert_sql, {**fixture, "person": fixture["people"][1]}
                ).scalar_one()
                transaction.commit()
                return ("committed", member_id)
            except DBAPIError:
                transaction.rollback()
                return ("conflict", None)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(first_transaction)
            second = pool.submit(second_transaction)
            assert second_pid_ready.wait(timeout=10)
            deadline = time.monotonic() + 10
            with engine.connect() as observer:
                while time.monotonic() < deadline:
                    if observer.execute(
                        text("SELECT cardinality(pg_blocking_pids(:pid))"),
                        {"pid": second_pid["value"]},
                    ).scalar_one() > 0:
                        break
                else:
                    raise AssertionError("La segunda inserción nunca esperó a PostgreSQL")
            release_first.set()
            results = [first.result(timeout=10), second.result(timeout=10)]

        assert [status for status, _ in results].count("committed") == 1
        assert [status for status, _ in results].count("conflict") == 1
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT count(*) FROM orv_integrante WHERE id_orv=:orv"),
                {"orv": fixture["orv"]},
            ).scalar_one() == 1
    finally:
        release_first.set()
        with SessionLocal() as db:
            set_audit_context(db, fixture["actor"])
            db.execute(
                text(
                    "UPDATE orv_integrante SET activo=false, fecha_baja=now(), "
                    "id_usuario_baja=:actor, motivo_baja='Cleanup prueba concurrente' "
                    "WHERE id_orv=:orv"
                ),
                fixture,
            )
            db.execute(
                text(
                    "UPDATE persona SET activo=false, fecha_baja=now(), "
                    "id_usuario_baja=:actor, motivo_baja='Cleanup prueba concurrente' "
                    "WHERE id_persona = ANY(:ids)"
                ),
                {"ids": fixture["people"], "actor": fixture["actor"]},
            )
            db.execute(
                text(
                    "UPDATE orv SET activo=false, fecha_baja=now(), "
                    "id_usuario_baja=:actor, motivo_baja='Cleanup prueba concurrente' "
                    "WHERE id_orv=:orv"
                ),
                fixture,
            )
            db.commit()


def test_018_finalization_rules_are_enforced_by_database(
    transactional_api, transactional_target_domain
):
    api = transactional_api["request"]
    project = api(
        "POST",
        "/api/proyectos",
        expected=201,
        json={"clave_proyecto": "SCHEMA-018-FIN", "nombre_proyecto": "Schema 018"},
    ).json()
    nucleus = api(
        "POST",
        "/api/nucleos",
        expected=201,
        json={
            "id_municipio": transactional_target_domain["municipality"]["id_municipio"],
            "nombre_nucleo": "Núcleo schema 018",
            "id_tipo_tenencia": api(
                "GET", "/api/catalogos/operativos/tipo_tenencia"
            ).json()[0]["id_catalogo_opcion"],
        },
    ).json()
    pn = api(
        "POST",
        f"/api/proyectos/{project['id_proyecto']}/nucleos",
        expected=201,
        json={"id_nucleo": nucleus["id_nucleo"]},
    ).json()
    orv = api(
        "POST",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/orv",
        expected=201,
        json={"numero_orv": "SCHEMA-018"},
    ).json()
    person = api(
        "POST",
        f"/api/proyectos/{project['id_proyecto']}/personas",
        expected=201,
        json={"nombre": "Persona schema", "datos_identidad_incompletos": True},
    ).json()

    def catalog(catalog_type):
        return {
            row["codigo"]: row["id_catalogo_opcion"]
            for row in api("GET", f"/api/catalogos/operativos/{catalog_type}").json()
        }

    organs = catalog("organo_orv")
    positions = catalog("cargo_orv")
    qualities = catalog("calidad_integrante_orv")
    finish_types = catalog("tipo_fin_orv_integrante")
    member = api(
        "POST",
        f"/api/orv/{orv['id_orv']}/integrantes",
        expected=201,
        json={
            "id_persona": person["id_persona"],
            "id_organo": organs["comisariado"],
            "id_cargo": positions["presidente"],
            "id_calidad": qualities["propietario"],
            "fecha_inicio": "2026-01-01",
        },
    ).json()
    connection = transactional_api["connection"]

    invalid_statements = [
        (
            "UPDATE orv_integrante SET fecha_fin=DATE '2026-06-30' "
            "WHERE id_orv_integrante=:id",
            {},
        ),
        (
            "UPDATE orv_integrante SET id_tipo_fin=:type "
            "WHERE id_orv_integrante=:id",
            {"type": finish_types["termino_periodo"]},
        ),
        (
            "UPDATE orv_integrante SET fecha_fin=DATE '2026-06-30', "
            "id_tipo_fin=:type WHERE id_orv_integrante=:id",
            {"type": finish_types["otro"]},
        ),
        (
            "UPDATE orv_integrante SET fecha_fin=DATE '2025-12-31', "
            "id_tipo_fin=:type WHERE id_orv_integrante=:id",
            {"type": finish_types["termino_periodo"]},
        ),
    ]
    for statement, params in invalid_statements:
        savepoint = connection.begin_nested()
        try:
            connection.execute(text(statement), {"id": member["id_orv_integrante"], **params})
        except Exception:
            savepoint.rollback()
        else:
            savepoint.rollback()
            raise AssertionError(f"La base aceptó una finalización inválida: {statement}")

    connection.execute(
        text(
            """
            UPDATE orv_integrante
               SET fecha_fin = DATE '2026-06-30',
                   id_tipo_fin = :type,
                   detalle_fin = 'Causa documentada'
             WHERE id_orv_integrante = :id
            """
        ),
        {"id": member["id_orv_integrante"], "type": finish_types["otro"]},
    )


def test_018_historical_backfill_never_invents_a_reason(transactional_api):
    connection = transactional_api["connection"]
    historical = connection.execute(
        text(
            """
            SELECT count(*)
              FROM orv_integrante oi
              JOIN catalogo_operativo c ON c.id_catalogo_opcion = oi.id_tipo_fin
             WHERE oi.fecha_fin IS NOT NULL
               AND c.tipo_catalogo = 'tipo_fin_orv_integrante'
               AND c.codigo = 'sin_clasificar'
               AND c.fuente = 'Migración de datos históricos'
            """
        )
    ).scalar_one()
    # En bases sin historia previa la opción neutral puede no existir. Si el
    # runner la necesitó, todos sus usos conservan explícitamente ese origen.
    neutral_uses = connection.execute(
        text(
            """
            SELECT count(*)
              FROM orv_integrante oi
              JOIN catalogo_operativo c ON c.id_catalogo_opcion = oi.id_tipo_fin
             WHERE c.codigo = 'sin_clasificar'
            """
        )
    ).scalar_one()
    assert historical == neutral_uses


def test_018_person_deactivation_has_database_guard(transactional_api):
    connection = transactional_api["connection"]
    triggers = set(
        connection.execute(
            text(
                """
                SELECT tgname
                  FROM pg_trigger
                 WHERE NOT tgisinternal
                   AND tgname IN (
                     'trg_persona_proteger_baja',
                     'trg_orv_integrante_persona_activa',
                     'trg_parcela_titular_persona_activa',
                     'trg_unidad_titular_persona_activa',
                     'trg_compareciente_persona_activa',
                     'trg_fif_interviniente_persona_activa',
                     'trg_pago_persona_activa'
                   )
                """
            )
        ).scalars()
    )
    assert len(triggers) == 7


def test_018_backfill_specific_record_from_017_transition(transactional_api):
    """Verifica que un registro específico con fecha_fin IS NOT NULL proveniente de
    schema 017 recibe id_tipo_fin -> sin_clasificar tras la migración 018,
    sin inferir automáticamente termino_periodo, remocion_asamblea, sustitucion
    o fallecimiento."""
    connection = transactional_api["connection"]
    savepoint = connection.begin_nested()
    try:
        # 1. Comprueba los registros históricos específicos migrados en la base
        rows = connection.execute(
            text(
                """
                SELECT oi.id_orv_integrante, oi.fecha_inicio, oi.fecha_fin,
                       c.codigo AS tipo_fin_codigo
                  FROM orv_integrante oi
                  JOIN catalogo_operativo c ON c.id_catalogo_opcion = oi.id_tipo_fin
                 WHERE oi.fecha_fin IS NOT NULL
                 ORDER BY oi.id_orv_integrante
                 LIMIT 5
                """
            )
        ).mappings().all()
        assert len(rows) > 0, "Debe existir al menos un registro histórico migrado"
        for r in rows:
            assert r["fecha_fin"] is not None
            assert r["tipo_fin_codigo"] == "sin_clasificar"
            assert r["tipo_fin_codigo"] not in {
                "termino_periodo",
                "remocion_asamblea",
                "sustitucion",
                "fallecimiento",
                "correccion",
                "otro",
            }

        # 2. Prueba aislada de transición que recrea la estructura de schema 017
        connection.execute(
            text(
                """
                CREATE TEMP TABLE orv_integrante_017_sample (
                    id_sample serial PRIMARY KEY,
                    identificador text NOT NULL,
                    fecha_inicio date,
                    fecha_fin date
                ) ON COMMIT DROP
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO orv_integrante_017_sample(identificador, fecha_inicio, fecha_fin)
                VALUES
                    ('REGISTRO-CON-FIN', DATE '2026-01-01', DATE '2026-06-30'),
                    ('REGISTRO-SIN-FIN', DATE '2026-01-01', NULL)
                """
            )
        )
        # Aplicar el DDL y backfill de 018 sobre la tabla muestra de 017
        connection.execute(
            text("ALTER TABLE orv_integrante_017_sample ADD COLUMN id_tipo_fin bigint")
        )
        sin_clasificar_id = connection.execute(
            text(
                """
                SELECT id_catalogo_opcion
                  FROM catalogo_operativo
                 WHERE tipo_catalogo = 'tipo_fin_orv_integrante'
                   AND codigo = 'sin_clasificar'
                   AND activo
                """
            )
        ).scalar_one()

        connection.execute(
            text(
                """
                UPDATE orv_integrante_017_sample
                   SET id_tipo_fin = :sin_clasificar_id
                 WHERE fecha_fin IS NOT NULL
                """
            ),
            {"sin_clasificar_id": sin_clasificar_id},
        )

        samples = {
            r["identificador"]: r["id_tipo_fin"]
            for r in connection.execute(
                text("SELECT identificador, id_tipo_fin FROM orv_integrante_017_sample")
            ).mappings().all()
        }
        assert samples["REGISTRO-CON-FIN"] == sin_clasificar_id
        assert samples["REGISTRO-SIN-FIN"] is None

        # Comprobar que no se infirió ninguna causa funcional
        causas_funcionales = set(
            connection.execute(
                text(
                    """
                    SELECT id_catalogo_opcion
                      FROM catalogo_operativo
                     WHERE tipo_catalogo = 'tipo_fin_orv_integrante'
                       AND codigo IN ('termino_periodo', 'remocion_asamblea', 'sustitucion', 'fallecimiento')
                    """
                )
            ).scalars()
        )
        assert samples["REGISTRO-CON-FIN"] not in causas_funcionales
    finally:
        savepoint.rollback()


def test_018_person_deactivation_blocked_by_all_six_active_relations(
    transactional_api, transactional_target_domain
):
    """Verifica el comportamiento real de protección de Persona frente a las
    seis relaciones de negocio activas:
    1. orv_integrante.id_persona
    2. parcela_titular.id_persona
    3. unidad_agraria_titular.id_persona
    4. convenio_compareciente.id_persona
    5. tramite_fifonafe_interviniente.id_persona
    6. pago.id_persona_beneficiaria
    """
    api = transactional_api["request"]
    connection = transactional_api["connection"]
    project, pn = _isolated_pn(api, transactional_target_domain)
    project_id = project["id_proyecto"]
    pn_id = pn["id_proyecto_nucleo"]

    actor = connection.execute(
        text("SELECT min(id_usuario) FROM usuario WHERE activo AND rol='admin'")
    ).scalar_one()

    def make_person(label: str) -> int:
        return api(
            "POST",
            f"/api/proyectos/{project_id}/personas",
            expected=201,
            json={
                "nombre": f"Relacion {label} {uuid.uuid4().hex[:8]}",
                "datos_identidad_incompletos": True,
                "origen_registro": "qa",
            },
        ).json()["id_persona"]

    def try_deactivate_person(person_id: int):
        savepoint = connection.begin_nested()
        with pytest.raises(DBAPIError) as excinfo:
            connection.execute(
                text(
                    """
                    UPDATE persona
                       SET activo=false, fecha_baja=now(), id_usuario_baja=:actor,
                           motivo_baja='Intento de baja con relacion activa'
                     WHERE id_persona=:id
                    """
                ),
                {"actor": actor, "id": person_id},
            )
        savepoint.rollback()
        assert "relaciones activas" in str(excinfo.value).lower()

    def assert_person_and_rel_active(person_id: int, rel_table: str, rel_pk: str, pk_val: int):
        p_active = connection.execute(
            text("SELECT activo FROM persona WHERE id_persona=:id"),
            {"id": person_id},
        ).scalar_one()
        assert p_active is True
        r_active = connection.execute(
            text(f"SELECT activo FROM {rel_table} WHERE {rel_pk}=:id"),
            {"id": pk_val},
        ).scalar_one()
        assert r_active is True

    def deactivate_and_verify_person_can_now_be_deleted(
        person_id: int, rel_table: str, rel_pk: str, pk_val: int
    ):
        connection.execute(
            text(
                f"""
                UPDATE {rel_table}
                   SET activo=false, fecha_baja=now(), id_usuario_baja=:actor,
                       motivo_baja='Baja de relacion para prueba'
                 WHERE {rel_pk}=:id
                """
            ),
            {"actor": actor, "id": pk_val},
        )
        connection.execute(
            text(
                """
                UPDATE persona
                   SET activo=false, fecha_baja=now(), id_usuario_baja=:actor,
                       motivo_baja='Baja permitida tras desactivar relacion'
                 WHERE id_persona=:id
                """
            ),
            {"actor": actor, "id": person_id},
        )
        assert connection.execute(
            text("SELECT activo FROM persona WHERE id_persona=:id"),
            {"id": person_id},
        ).scalar_one() is False

    # 1. orv_integrante.id_persona
    p1 = make_person("ORV")
    orv_id = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/orv",
        expected=201,
        json={"numero_orv": f"ORV-REL-{uuid.uuid4().hex[:8]}"},
    ).json()["id_orv"]
    organ = connection.execute(
        text("SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo='organo_orv' AND codigo='comisariado'")
    ).scalar_one()
    cargo = connection.execute(
        text("SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo='cargo_orv' AND codigo='presidente'")
    ).scalar_one()
    calidad = connection.execute(
        text("SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo='calidad_integrante_orv' AND codigo='propietario'")
    ).scalar_one()
    rel1 = connection.execute(
        text(
            """
            INSERT INTO orv_integrante(
                id_orv, id_persona, id_organo, id_cargo, id_calidad, fecha_inicio, activo, creado_por
            ) VALUES (:o, :p, :org, :car, :cal, DATE '2030-01-01', true, :actor)
            RETURNING id_orv_integrante
            """
        ),
        {"o": orv_id, "p": p1, "org": organ, "car": cargo, "cal": calidad, "actor": actor},
    ).scalar_one()
    try_deactivate_person(p1)
    assert_person_and_rel_active(p1, "orv_integrante", "id_orv_integrante", rel1)
    deactivate_and_verify_person_can_now_be_deleted(p1, "orv_integrante", "id_orv_integrante", rel1)

    # 2. parcela_titular.id_persona
    p2 = make_person("Parcela")
    parcel = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": f"P-{uuid.uuid4().hex[:6]}"},
    ).json()
    rel2 = connection.execute(
        text(
            """
            INSERT INTO parcela_titular(
                id_parcela, id_persona, tipo_derecho, activo, creado_por
            ) VALUES (:parc, :p, 'ejidatario', true, :actor)
            RETURNING id_parcela_titular
            """
        ),
        {"parc": parcel["id_parcela"], "p": p2, "actor": actor},
    ).scalar_one()
    try_deactivate_person(p2)
    assert_person_and_rel_active(p2, "parcela_titular", "id_parcela_titular", rel2)
    deactivate_and_verify_person_can_now_be_deleted(p2, "parcela_titular", "id_parcela_titular", rel2)

    # 3. unidad_agraria_titular.id_persona
    p3 = make_person("Unidad")
    land_type = connection.execute(
        text("SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo='tipo_tierra' AND activo LIMIT 1")
    ).scalar_one()
    mgmt = connection.execute(
        text("SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo='tipo_gestion' AND activo LIMIT 1")
    ).scalar_one()
    dest = connection.execute(
        text("SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo='destino_superficie' AND activo LIMIT 1")
    ).scalar_one()
    ownership = connection.execute(
        text("SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo='tipo_titularidad_unidad' AND codigo='persona' AND activo")
    ).scalar_one()
    unit = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": land_type,
            "id_tipo_gestion": mgmt,
            "id_destino_superficie": dest,
            "id_tipo_titularidad": ownership,
            "referencia_alfanumerica": f"UA-{uuid.uuid4().hex[:6]}",
        },
    ).json()
    rel3 = connection.execute(
        text(
            """
            INSERT INTO unidad_agraria_titular(
                id_unidad_agraria, id_persona, es_principal, activo, creado_por
            ) VALUES (:u, :p, false, true, :actor)
            RETURNING id_unidad_titular
            """
        ),
        {"u": unit["id_unidad_agraria"], "p": p3, "actor": actor},
    ).scalar_one()
    try_deactivate_person(p3)
    assert_person_and_rel_active(p3, "unidad_agraria_titular", "id_unidad_titular", rel3)
    deactivate_and_verify_person_can_now_be_deleted(p3, "unidad_agraria_titular", "id_unidad_titular", rel3)

    # 4. convenio_compareciente.id_persona
    p4 = make_person("Convenio")
    calidad_compareciente = connection.execute(
        text("SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo='calidad_compareciente_convenio' AND codigo='titular_parcelario'")
    ).scalar_one()
    conv = connection.execute(
        text(
            """
            INSERT INTO convenio(
                id_proyecto_nucleo, ambito, tipo_instrumento, tipo_convenio, consecutivo, activo, creado_por
            ) VALUES (
                :pn, 'colectivo', 'convenio', 'cop_original',
                COALESCE((SELECT max(consecutivo) + 1 FROM convenio WHERE id_proyecto_nucleo = :pn), 1),
                true, :actor
            )
            RETURNING id_convenio
            """
        ),
        {"pn": pn_id, "actor": actor},
    ).scalar_one()
    rel4 = connection.execute(
        text(
            """
            INSERT INTO convenio_compareciente(
                id_convenio, id_persona, id_tipo_calidad, nombre_en_instrumento,
                es_firmante, es_beneficiario_pago, requiere_revision, activo, creado_por
            ) VALUES (
                :c, :p, :cal, 'Compareciente Test', false, true, false, true, :actor
            ) RETURNING id_compareciente
            """
        ),
        {"c": conv, "p": p4, "cal": calidad_compareciente, "actor": actor},
    ).scalar_one()
    try_deactivate_person(p4)
    assert_person_and_rel_active(p4, "convenio_compareciente", "id_compareciente", rel4)
    deactivate_and_verify_person_can_now_be_deleted(p4, "convenio_compareciente", "id_compareciente", rel4)

    # 5. tramite_fifonafe_interviniente.id_persona
    p5 = make_person("Fifonafe")
    tramite = connection.execute(
        text(
            """
            INSERT INTO tramite_fifonafe(
                id_proyecto_nucleo, ambito, estatus, creado_por
            ) VALUES (:pn, 'individual', 'pendiente', :actor)
            RETURNING id_tramite_fifonafe
            """
        ),
        {"pn": pn_id, "actor": actor},
    ).scalar_one()
    rel5 = connection.execute(
        text(
            """
            INSERT INTO tramite_fifonafe_interviniente(
                id_tramite_fifonafe, id_persona, rol, activo, creado_por
            ) VALUES (:t, :p, 'representante', true, :actor)
            RETURNING id_interviniente_fifonafe
            """
        ),
        {"t": tramite, "p": p5, "actor": actor},
    ).scalar_one()
    try_deactivate_person(p5)
    assert_person_and_rel_active(p5, "tramite_fifonafe_interviniente", "id_interviniente_fifonafe", rel5)
    deactivate_and_verify_person_can_now_be_deleted(p5, "tramite_fifonafe_interviniente", "id_interviniente_fifonafe", rel5)

    # 6. pago.id_persona_beneficiaria
    p6 = make_person("Pago")
    af = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "individual",
            "superficie_preliminar_ha": "1.000000",
            "superficie_afectada_ha": "1.000000",
        },
    ).json()
    indemnizacion_id = connection.execute(
        text(
            """
            INSERT INTO indemnizacion(id_afectacion, estatus, activo, creado_por)
            VALUES (:af, 'pendiente', true, :actor)
            RETURNING id_indemnizacion
            """
        ),
        {"af": af["id_afectacion"], "actor": actor},
    ).scalar_one()
    rel6 = connection.execute(
        text(
            """
            INSERT INTO pago(
                id_indemnizacion, fecha_pago, monto, beneficiario_nombre,
                id_persona_beneficiaria, activo, creado_por
            ) VALUES (
                :ind, CURRENT_DATE, 1000.00, 'Beneficiario Test', :p, true, :actor
            ) RETURNING id_pago
            """
        ),
        {"ind": indemnizacion_id, "p": p6, "actor": actor},
    ).scalar_one()
    try_deactivate_person(p6)
    assert_person_and_rel_active(p6, "pago", "id_pago", rel6)
    deactivate_and_verify_person_can_now_be_deleted(p6, "pago", "id_pago", rel6)


def test_018_person_deactivation_and_relation_creation_concurrent_serialization():
    """Demuestra que la creación concurrente de una relación activa y la baja de Persona
    se serializan vía el advisory lock de PostgreSQL, impidiendo Persona.activo=false
    con relación activa=true."""
    with SessionLocal() as db:
        actor = db.execute(
            text("SELECT min(id_usuario) FROM usuario WHERE activo AND rol='admin'")
        ).scalar_one()
        set_audit_context(db, actor)
        nucleus = db.query(models.NucleoAgrario).filter(
            models.NucleoAgrario.activo.is_(True)
        ).order_by(models.NucleoAgrario.id_nucleo).first()
        assert nucleus is not None
        orv = models.Orv(
            id_nucleo=nucleus.id_nucleo,
            numero_orv=f"CONC-PERS-{uuid.uuid4().hex[:8]}",
            creado_por=actor,
        )
        person = models.Persona(
            nombre=f"Persona Concurrente {uuid.uuid4().hex[:8]}",
            datos_identidad_incompletos=True,
            origen_registro="qa",
            creado_por=actor,
        )
        db.add_all([orv, person])
        db.flush()
        organ = db.execute(
            text("SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo='organo_orv' AND codigo='comisariado'")
        ).scalar_one()
        cargo = db.execute(
            text("SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo='cargo_orv' AND codigo='presidente'")
        ).scalar_one()
        calidad = db.execute(
            text("SELECT id_catalogo_opcion FROM catalogo_operativo WHERE tipo_catalogo='calidad_integrante_orv' AND codigo='propietario'")
        ).scalar_one()
        db.commit()
        fixture = {
            "orv_id": orv.id_orv,
            "person_id": person.id_persona,
            "organ": organ,
            "cargo": cargo,
            "calidad": calidad,
            "actor": actor,
        }

    t1_has_lock = threading.Event()
    release_t1 = threading.Event()
    t2_pid_ready = threading.Event()
    t2_pid = {}

    def t1():
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                conn.execute(
                    text("SELECT set_config('app.current_user_id', :a, true)"),
                    {"a": str(fixture["actor"])},
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO orv_integrante(
                            id_orv, id_persona, id_organo, id_cargo, id_calidad,
                            fecha_inicio, activo, creado_por
                        ) VALUES (:o, :p, :org, :car, :cal, DATE '2035-01-01', true, :a)
                        """
                    ),
                    {
                        "o": fixture["orv_id"],
                        "p": fixture["person_id"],
                        "org": fixture["organ"],
                        "car": fixture["cargo"],
                        "cal": fixture["calidad"],
                        "a": fixture["actor"],
                    },
                )
                t1_has_lock.set()
                assert release_t1.wait(timeout=10)
                trans.commit()
                return "t1_committed"
            except Exception:
                trans.rollback()
                raise

    def t2():
        assert t1_has_lock.wait(timeout=10)
        with engine.connect() as conn:
            trans = conn.begin()
            t2_pid["val"] = conn.execute(text("SELECT pg_backend_pid()")).scalar_one()
            t2_pid_ready.set()
            try:
                conn.execute(
                    text("SELECT set_config('app.current_user_id', :a, true)"),
                    {"a": str(fixture["actor"])},
                )
                conn.execute(
                    text(
                        """
                        UPDATE persona
                           SET activo=false, fecha_baja=now(), id_usuario_baja=:a,
                               motivo_baja='Intento concurrente de baja'
                         WHERE id_persona=:p
                        """
                    ),
                    {"a": fixture["actor"], "p": fixture["person_id"]},
                )
                trans.commit()
                return "t2_committed"
            except DBAPIError:
                trans.rollback()
                return "t2_conflict"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(t1)
            f2 = pool.submit(t2)
            assert t2_pid_ready.wait(timeout=10)
            deadline = time.monotonic() + 10
            with engine.connect() as observer:
                while time.monotonic() < deadline:
                    if (
                        observer.execute(
                            text("SELECT cardinality(pg_blocking_pids(:pid))"),
                            {"pid": t2_pid["val"]},
                        ).scalar_one()
                        > 0
                    ):
                        break
                else:
                    raise AssertionError("T2 nunca quedó bloqueado por el advisory lock de PostgreSQL")
            release_t1.set()
            r1 = f1.result(timeout=10)
            r2 = f2.result(timeout=10)

        assert r1 == "t1_committed"
        assert r2 == "t2_conflict"

        with SessionLocal() as db:
            p_active = db.execute(
                text("SELECT activo FROM persona WHERE id_persona=:p"),
                {"p": fixture["person_id"]},
            ).scalar_one()
            rel_active = db.execute(
                text("SELECT activo FROM orv_integrante WHERE id_persona=:p"),
                {"p": fixture["person_id"]},
            ).scalar_one()
            assert p_active is True
            assert rel_active is True
    finally:
        release_t1.set()
        with SessionLocal() as db:
            set_audit_context(db, fixture["actor"])
            db.execute(
                text(
                    """
                    UPDATE orv_integrante
                       SET activo=false, fecha_baja=now(), id_usuario_baja=:a,
                           motivo_baja='Cleanup prueba concurrente'
                     WHERE id_persona=:p
                    """
                ),
                {"p": fixture["person_id"], "a": fixture["actor"]},
            )
            db.execute(
                text(
                    """
                    UPDATE persona
                       SET activo=false, fecha_baja=now(), id_usuario_baja=:a,
                           motivo_baja='Cleanup prueba concurrente'
                     WHERE id_persona=:p
                    """
                ),
                {"p": fixture["person_id"], "a": fixture["actor"]},
            )
            db.execute(
                text(
                    """
                    UPDATE orv
                       SET activo=false, fecha_baja=now(), id_usuario_baja=:a,
                           motivo_baja='Cleanup prueba concurrente'
                     WHERE id_orv=:o
                    """
                ),
                {"o": fixture["orv_id"], "a": fixture["actor"]},
            )
            db.commit()

