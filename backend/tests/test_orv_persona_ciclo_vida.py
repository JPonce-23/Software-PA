"""Pruebas funcionales del ciclo de vida de Persona, ORV y OrvIntegrante."""

import uuid
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app import auth, models, schemas
from app.database import SessionLocal, engine
from app.main import app
from app.services import domain as domain_service
from app.services.common import set_audit_context

from .test_excel_closure_002 import _isolated_pn


def _catalog(api, name):
    return {
        row["codigo"]: row["id_catalogo_opcion"]
        for row in api("GET", f"/api/catalogos/operativos/{name}").json()
    }


@pytest.fixture(scope="module")
def api(transactional_api):
    return transactional_api["request"]


@pytest.fixture(scope="module")
def lifecycle(api, transactional_target_domain):
    project, pn = _isolated_pn(api, transactional_target_domain)
    states = _catalog(api, "estado_registral_orv")
    organs = _catalog(api, "organo_orv")
    positions = _catalog(api, "cargo_orv")
    qualities = _catalog(api, "calidad_integrante_orv")
    finish_types = _catalog(api, "tipo_fin_orv_integrante")
    today = date.today()

    current_orv = api(
        "POST",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/orv",
        expected=201,
        json={
            "numero_orv": f"ORV-VIGENTE-{uuid.uuid4().hex[:8]}",
            "inicio_vigencia": (today - timedelta(days=30)).isoformat(),
            "fin_vigencia": (today + timedelta(days=30)).isoformat(),
            "id_estado_registral": states["inscrita"],
        },
    ).json()
    expired_orv = api(
        "POST",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/orv",
        expected=201,
        json={
            "numero_orv": f"ORV-HIST-{uuid.uuid4().hex[:8]}",
            "inicio_vigencia": (today - timedelta(days=100)).isoformat(),
            "fin_vigencia": (today - timedelta(days=1)).isoformat(),
            "id_estado_registral": states["inscrita"],
        },
    ).json()
    open_orv = api(
        "POST",
        f"/api/proyecto-nucleo/{pn['id_proyecto_nucleo']}/orv",
        expected=201,
        json={"numero_orv": f"ORV-ABIERTO-{uuid.uuid4().hex[:8]}"},
    ).json()
    return {
        "project": project,
        "pn": pn,
        "current_orv": current_orv,
        "expired_orv": expired_orv,
        "open_orv": open_orv,
        "organs": organs,
        "positions": positions,
        "qualities": qualities,
        "finish_types": finish_types,
        "today": today,
    }


def _person(api, project_id, name="Persona ciclo"):
    return api(
        "POST",
        f"/api/proyectos/{project_id}/personas",
        expected=201,
        json={
            "nombre": name,
            "apellido_paterno": uuid.uuid4().hex[:8],
            "datos_identidad_incompletos": True,
            "origen_registro": "qa",
        },
    ).json()


def _member(api, lifecycle, person, **overrides):
    payload = {
        "id_persona": person["id_persona"],
        "id_organo": lifecycle["organs"]["comisariado"],
        "id_cargo": lifecycle["positions"]["presidente"],
        "id_calidad": lifecycle["qualities"]["propietario"],
        "fecha_inicio": lifecycle["today"].isoformat(),
    }
    payload.update(overrides)
    return api(
        "POST",
        f"/api/orv/{lifecycle['current_orv']['id_orv']}/integrantes",
        expected=201,
        json=payload,
    ).json()


def _committed_member_fixture():
    """Create a row visible to independent PostgreSQL transactions."""
    with SessionLocal() as db:
        user = db.query(models.Usuario).filter(
            models.Usuario.rol == "admin", models.Usuario.activo.is_(True)
        ).order_by(models.Usuario.id_usuario).first()
        nucleus = db.query(models.NucleoAgrario).filter(
            models.NucleoAgrario.activo.is_(True)
        ).order_by(models.NucleoAgrario.id_nucleo).first()
        assert user is not None and nucleus is not None
        catalogs = {
            (row.tipo_catalogo, row.codigo): row.id_catalogo_opcion
            for row in db.query(models.CatalogoOperativo).filter(
                models.CatalogoOperativo.activo.is_(True),
                models.CatalogoOperativo.tipo_catalogo.in_([
                    "organo_orv", "cargo_orv", "calidad_integrante_orv",
                    "tipo_fin_orv_integrante",
                ]),
            )
        }
        set_audit_context(db, user.id_usuario)
        orv = models.Orv(
            id_nucleo=nucleus.id_nucleo,
            numero_orv=f"CONC-FIN-{uuid.uuid4().hex}",
            creado_por=user.id_usuario,
        )
        person = models.Persona(
            nombre=f"Persona concurrente {uuid.uuid4().hex}",
            datos_identidad_incompletos=True,
            origen_registro="qa",
            creado_por=user.id_usuario,
        )
        db.add_all([orv, person])
        db.flush()
        member = models.OrvIntegrante(
            id_orv=orv.id_orv,
            id_persona=person.id_persona,
            id_organo=catalogs[("organo_orv", "comisariado")],
            id_cargo=catalogs[("cargo_orv", "presidente")],
            id_calidad=catalogs[("calidad_integrante_orv", "propietario")],
            fecha_inicio=date(2045, 1, 1),
            creado_por=user.id_usuario,
        )
        db.add(member)
        db.commit()
        return {
            "member_id": member.id_orv_integrante,
            "orv_id": orv.id_orv,
            "person_id": person.id_persona,
            "user_id": user.id_usuario,
            "tipo_termino": catalogs[("tipo_fin_orv_integrante", "termino_periodo")],
            "tipo_sustitucion": catalogs[("tipo_fin_orv_integrante", "sustitucion")],
        }


def _cleanup_committed_member(data):
    with SessionLocal() as db:
        set_audit_context(db, data["user_id"])
        db.execute(
            text(
                "UPDATE orv_integrante SET activo=false, fecha_baja=now(), "
                "id_usuario_baja=:user_id, motivo_baja='Cleanup prueba concurrente' "
                "WHERE id_orv_integrante=:id"
            ),
            {"id": data["member_id"], "user_id": data["user_id"]},
        )
        db.execute(
            text(
                "UPDATE persona SET activo=false, fecha_baja=now(), "
                "id_usuario_baja=:user_id, motivo_baja='Cleanup prueba concurrente' "
                "WHERE id_persona=:id"
            ),
            {"id": data["person_id"], "user_id": data["user_id"]},
        )
        db.execute(
            text(
                "UPDATE orv SET activo=false, fecha_baja=now(), "
                "id_usuario_baja=:user_id, motivo_baja='Cleanup prueba concurrente' "
                "WHERE id_orv=:id"
            ),
            {"id": data["orv_id"], "user_id": data["user_id"]},
        )
        db.commit()


def _wait_until_blocked(pid: int, timeout: float = 10.0):
    deadline = time.monotonic() + timeout
    with engine.connect() as connection:
        while time.monotonic() < deadline:
            blockers = connection.execute(
                text("SELECT pg_blocking_pids(:pid)"), {"pid": pid}
            ).scalar_one()
            if blockers:
                return
    raise AssertionError(f"La transacción PostgreSQL {pid} nunca quedó bloqueada")


def test_orv_validity_is_derived_without_changing_activo(api, lifecycle):
    rows = api(
        "GET", f"/api/proyecto-nucleo/{lifecycle['pn']['id_proyecto_nucleo']}/orv"
    ).json()
    by_id = {row["id_orv"]: row for row in rows}
    assert by_id[lifecycle["current_orv"]["id_orv"]]["vigente"] is True
    assert by_id[lifecycle["expired_orv"]["id_orv"]]["vigente"] is False
    assert by_id[lifecycle["expired_orv"]["id_orv"]]["activo"] is True
    assert by_id[lifecycle["open_orv"]["id_orv"]]["vigente"] is True


def test_person_get_patch_logical_delete_reactivate_and_audit(
    api, lifecycle, transactional_api
):
    person = _person(api, lifecycle["project"]["id_proyecto"], "Persona editable")
    fetched = api("GET", f"/api/personas/{person['id_persona']}").json()
    assert fetched["id_persona"] == person["id_persona"]
    api("GET", "/api/personas/999999999", expected=404)

    updated = api(
        "PATCH",
        f"/api/personas/{person['id_persona']}",
        json={"telefono": "4420000000", "correo_electronico": "persona@example.test"},
    ).json()
    assert updated["telefono"] == "4420000000"
    assert updated["actualizado_por"] is not None

    api(
        "DELETE",
        f"/api/personas/{person['id_persona']}",
        json={"motivo": "Captura duplicada de prueba"},
    )
    db_row = transactional_api["connection"].execute(
        text(
            "SELECT activo, fecha_baja, id_usuario_baja, motivo_baja "
            "FROM persona WHERE id_persona=:id"
        ),
        {"id": person["id_persona"]},
    ).mappings().one()
    assert db_row["activo"] is False
    assert db_row["fecha_baja"] is not None
    assert db_row["id_usuario_baja"] is not None
    assert db_row["motivo_baja"] == "Captura duplicada de prueba"
    api("GET", f"/api/personas/{person['id_persona']}", expected=404)

    reactivated = api(
        "POST", f"/api/personas/{person['id_persona']}/reactivar"
    ).json()
    assert reactivated["activo"] is True
    assert reactivated["fecha_baja"] is None
    assert reactivated["motivo_baja"] is None
    api(
        "POST", f"/api/personas/{person['id_persona']}/reactivar", expected=409
    )


def test_person_with_any_active_business_reference_cannot_be_deleted(api, lifecycle):
    person = _person(api, lifecycle["project"]["id_proyecto"], "Persona referenciada")
    _member(
        api,
        lifecycle,
        person,
        id_organo=lifecycle["organs"]["consejo_vigilancia"],
        id_cargo=lifecycle["positions"]["secretario_1"],
        id_calidad=lifecycle["qualities"]["suplente"],
    )
    response = api(
        "DELETE",
        f"/api/personas/{person['id_persona']}",
        expected=409,
        json={"motivo": "No debe permitirse"},
    )
    assert "relaciones activas" in response.json()["detail"]


def test_person_patch_requires_capture_role(api, lifecycle):
    person = _person(api, lifecycle["project"]["id_proyecto"], "Persona RBAC")
    original = app.dependency_overrides[auth.get_current_user]
    viewer = models.Usuario(
        id_usuario=999999,
        nombre="Visor",
        apellido_paterno="QA",
        correo="visor@example.test",
        rol="visualizador",
        activo=True,
    )
    app.dependency_overrides[auth.get_current_user] = lambda: viewer
    try:
        api(
            "PATCH",
            f"/api/personas/{person['id_persona']}",
            expected=403,
            json={"telefono": "000"},
        )
    finally:
        app.dependency_overrides[auth.get_current_user] = original


def test_finalize_member_and_history_filters(api, lifecycle):
    person = _person(api, lifecycle["project"]["id_proyecto"], "Integrante histórico")
    member = _member(
        api,
        lifecycle,
        person,
        fecha_inicio=(lifecycle["today"] - timedelta(days=30)).isoformat(),
    )
    finish_date = lifecycle["today"] - timedelta(days=1)
    api(
        "PATCH",
        f"/api/orv-integrantes/{member['id_orv_integrante']}",
        expected=422,
        json={"fecha_fin": finish_date.isoformat()},
    )
    finalized = api(
        "POST",
        f"/api/orv-integrantes/{member['id_orv_integrante']}/finalizar",
        json={
            "fecha_fin": finish_date.isoformat(),
            "id_tipo_fin": lifecycle["finish_types"]["remocion_asamblea"],
        },
    ).json()
    assert finalized["activo"] is True
    assert finalized["vigente"] is False
    assert finalized["id_tipo_fin"] == lifecycle["finish_types"]["remocion_asamblea"]

    api(
        "POST",
        f"/api/orv-integrantes/{member['id_orv_integrante']}/finalizar",
        expected=409,
        json={
            "fecha_fin": finish_date.isoformat(),
            "id_tipo_fin": lifecycle["finish_types"]["sustitucion"],
        },
    )
    current = api(
        "GET", f"/api/orv/{lifecycle['current_orv']['id_orv']}/integrantes"
    ).json()
    assert member["id_orv_integrante"] not in {row["id_orv_integrante"] for row in current}
    history = api(
        "GET",
        f"/api/orv/{lifecycle['current_orv']['id_orv']}/integrantes?incluir_historico=true",
    ).json()
    historical = next(row for row in history if row["id_orv_integrante"] == member["id_orv_integrante"])
    assert historical["nombre"] == person["nombre"]
    assert historical["fecha_fin"] == finish_date.isoformat()
    assert historical["vigente"] is False


def test_concurrent_finalize_serializes_and_preserves_first_commit(monkeypatch):
    data = _committed_member_fixture()
    first_has_lock = threading.Event()
    release_first = threading.Event()
    second_pid_ready = threading.Event()
    second_pid = {}
    original_require_catalog = domain_service.require_catalog_option

    def coordinated_catalog(*args, **kwargs):
        if (
            threading.current_thread().name == "finalize-first"
            and args[1] == "tipo_fin_orv_integrante"
        ):
            first_has_lock.set()
            assert release_first.wait(timeout=10)
        return original_require_catalog(*args, **kwargs)

    monkeypatch.setattr(domain_service, "require_catalog_option", coordinated_catalog)

    def attempt(name, finish_date, finish_type, detail):
        threading.current_thread().name = name
        with SessionLocal() as db:
            user = db.get(models.Usuario, data["user_id"])
            if name == "finalize-second":
                second_pid["value"] = db.execute(
                    text("SELECT pg_backend_pid()")
                ).scalar_one()
                second_pid_ready.set()
            try:
                row = domain_service.finalize_orv_member(
                    db,
                    data["member_id"],
                    schemas.OrvIntegranteFinalizarRequest(
                        fecha_fin=finish_date,
                        id_tipo_fin=finish_type,
                        detalle_fin=detail,
                    ),
                    user,
                )
                return (200, row.fecha_fin, row.id_tipo_fin, row.detalle_fin)
            except HTTPException as exc:
                db.rollback()
                return (exc.status_code, None, None, None)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(
                attempt,
                "finalize-first",
                date(2045, 6, 30),
                data["tipo_termino"],
                "Primer commit",
            )
            assert first_has_lock.wait(timeout=10)
            second = pool.submit(
                attempt,
                "finalize-second",
                date(2045, 7, 31),
                data["tipo_sustitucion"],
                "No debe persistir",
            )
            assert second_pid_ready.wait(timeout=10)
            _wait_until_blocked(second_pid["value"])
            release_first.set()
            first_result = first.result(timeout=10)
            second_result = second.result(timeout=10)

        assert first_result == (
            200,
            date(2045, 6, 30),
            data["tipo_termino"],
            "Primer commit",
        )
        assert second_result[0] == 409
        with SessionLocal() as db:
            persisted = db.get(models.OrvIntegrante, data["member_id"])
            assert persisted.activo is True
            assert persisted.fecha_fin == date(2045, 6, 30)
            assert persisted.id_tipo_fin == data["tipo_termino"]
            assert persisted.detalle_fin == "Primer commit"
    finally:
        release_first.set()
        _cleanup_committed_member(data)


def test_finish_type_validation_and_other_detail(api, lifecycle):
    first = _person(api, lifecycle["project"]["id_proyecto"], "Tipo fin inválido")
    member = _member(
        api,
        lifecycle,
        first,
        id_cargo=lifecycle["positions"]["secretario"],
    )
    api(
        "POST",
        f"/api/orv-integrantes/{member['id_orv_integrante']}/finalizar",
        expected=422,
        json={"fecha_fin": lifecycle["today"].isoformat(), "id_tipo_fin": 999999999},
    )
    api(
        "POST",
        f"/api/orv-integrantes/{member['id_orv_integrante']}/finalizar",
        expected=422,
        json={
            "fecha_fin": lifecycle["today"].isoformat(),
            "id_tipo_fin": lifecycle["finish_types"]["otro"],
        },
    )
    result = api(
        "POST",
        f"/api/orv-integrantes/{member['id_orv_integrante']}/finalizar",
        json={
            "fecha_fin": lifecycle["today"].isoformat(),
            "id_tipo_fin": lifecycle["finish_types"]["otro"],
            "detalle_fin": "  Causa documentada  ",
        },
    ).json()
    assert result["detalle_fin"] == "Causa documentada"

    if "sin_clasificar" in lifecycle["finish_types"]:
        second = _person(api, lifecycle["project"]["id_proyecto"], "Neutral no permitido")
        neutral_member = _member(
            api,
            lifecycle,
            second,
            id_organo=lifecycle["organs"]["consejo_vigilancia"],
            id_cargo=lifecycle["positions"]["secretario_2"],
        )
        api(
            "POST",
            f"/api/orv-integrantes/{neutral_member['id_orv_integrante']}/finalizar",
            expected=422,
            json={
                "fecha_fin": lifecycle["today"].isoformat(),
                "id_tipo_fin": lifecycle["finish_types"]["sin_clasificar"],
            },
        )


def test_overlap_consecutive_quality_and_new_period_rules(api, lifecycle):
    project_id = lifecycle["project"]["id_proyecto"]
    start = date(2040, 1, 1)
    end = date(2040, 6, 30)
    first_person = _person(api, project_id, "Primer periodo")
    first = _member(api, lifecycle, first_person, fecha_inicio=start.isoformat())
    api(
        "POST",
        f"/api/orv-integrantes/{first['id_orv_integrante']}/finalizar",
        json={
            "fecha_fin": end.isoformat(),
            "id_tipo_fin": lifecycle["finish_types"]["termino_periodo"],
        },
    )

    overlap_person = _person(api, project_id, "Traslape")
    api(
        "POST",
        f"/api/orv/{lifecycle['current_orv']['id_orv']}/integrantes",
        expected=409,
        json={
            "id_persona": overlap_person["id_persona"],
            "id_organo": lifecycle["organs"]["comisariado"],
            "id_cargo": lifecycle["positions"]["presidente"],
            "id_calidad": lifecycle["qualities"]["propietario"],
            "fecha_inicio": end.isoformat(),
        },
    )

    next_period = _member(
        api,
        lifecycle,
        first_person,
        fecha_inicio=(end + timedelta(days=1)).isoformat(),
    )
    assert next_period["id_orv_integrante"] != first["id_orv_integrante"]

    substitute = _person(api, project_id, "Suplente simultáneo")
    simultaneous = _member(
        api,
        lifecycle,
        substitute,
        id_calidad=lifecycle["qualities"]["suplente"],
        fecha_inicio=start.isoformat(),
    )
    assert simultaneous["id_calidad"] == lifecycle["qualities"]["suplente"]

    secretary = _person(api, project_id, "Otro cargo")
    other_position = _member(
        api,
        lifecycle,
        secretary,
        id_cargo=lifecycle["positions"]["secretario"],
        fecha_inicio=start.isoformat(),
    )
    assert other_position["id_cargo"] == lifecycle["positions"]["secretario"]


def test_administrative_delete_and_reactivation_preserve_finish_data(api, lifecycle):
    person = _person(api, lifecycle["project"]["id_proyecto"], "Baja administrativa")
    member = _member(
        api,
        lifecycle,
        person,
        id_cargo=lifecycle["positions"]["tesorero"],
        fecha_inicio=(lifecycle["today"] - timedelta(days=100)).isoformat(),
    )
    finish_date = lifecycle["today"] - timedelta(days=50)
    api(
        "POST",
        f"/api/orv-integrantes/{member['id_orv_integrante']}/finalizar",
        json={
            "fecha_fin": finish_date.isoformat(),
            "id_tipo_fin": lifecycle["finish_types"]["sustitucion"],
        },
    )
    api(
        "DELETE",
        f"/api/orv-integrantes/{member['id_orv_integrante']}",
        json={"motivo": "Registro anulado administrativamente"},
    )
    history = api(
        "GET",
        f"/api/orv/{lifecycle['current_orv']['id_orv']}/integrantes?incluir_historico=true",
    ).json()
    assert member["id_orv_integrante"] not in {row["id_orv_integrante"] for row in history}

    restored = api(
        "POST", f"/api/orv-integrantes/{member['id_orv_integrante']}/reactivar"
    ).json()
    assert restored["activo"] is True
    assert restored["fecha_fin"] == finish_date.isoformat()
    assert restored["id_tipo_fin"] == lifecycle["finish_types"]["sustitucion"]
    assert restored["vigente"] is False


def test_reactivation_that_overlaps_returns_conflict(api, lifecycle):
    person_a = _person(api, lifecycle["project"]["id_proyecto"], "Reactiva A")
    old = _member(
        api,
        lifecycle,
        person_a,
        id_organo=lifecycle["organs"]["consejo_vigilancia"],
        id_cargo=lifecycle["positions"]["presidente"],
        fecha_inicio="2030-01-01",
    )
    api(
        "DELETE",
        f"/api/orv-integrantes/{old['id_orv_integrante']}",
        json={"motivo": "Anulación temporal de prueba"},
    )
    person_b = _person(api, lifecycle["project"]["id_proyecto"], "Reactiva B")
    _member(
        api,
        lifecycle,
        person_b,
        id_organo=lifecycle["organs"]["consejo_vigilancia"],
        id_cargo=lifecycle["positions"]["presidente"],
        fecha_inicio="2030-06-01",
    )
    response = api(
        "POST",
        f"/api/orv-integrantes/{old['id_orv_integrante']}/reactivar",
        expected=409,
    )
    assert "traslapa" in response.json()["detail"]
