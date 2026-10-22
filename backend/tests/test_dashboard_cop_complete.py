"""Complete COP: synthetic data only, on the isolated PostgreSQL/PostGIS fixture."""
from contextlib import contextmanager
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import statistics
import time
import tracemalloc
from types import SimpleNamespace
import uuid

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, insert, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app import auth, models, main as main_module
from app.main import app
from app.services.common import set_audit_context
from app.services import dashboard_summary
from app.services.authentication import hash_password
from tests.test_auth_rbac import _login

SIZES = (0, 99, 100, 101, 105, 200, 201, 1000)
ROLES = ("admin", "operador", "visualizador", "geografo")


def make_cop_env(transactional_api, sizes):
    env = dict(transactional_api)
    with env["session_factory"]() as db:
        assert db.execute(text("SELECT current_database(), current_setting('cluster_name')")).one() == (
            "software_pa_test", "convenio-report-disposable")
        actor = app.dependency_overrides[auth.get_current_user]().id_usuario
        set_audit_context(db, actor)
        # Previous tests may have forced deferred triggers to IMMEDIATE.
        # Build both sides of the relationship, then validate all constraints.
        db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        tenures = [r[0] for r in db.query(models.CatalogoOperativo.id_catalogo_opcion).filter(
            models.CatalogoOperativo.tipo_catalogo == "tipo_tenencia",
            models.CatalogoOperativo.codigo.in_(("ejido", "comunidad")),
        ).order_by(models.CatalogoOperativo.codigo).all()]
        cop = db.query(models.CatalogoOperativo.id_catalogo_opcion).filter_by(
            tipo_catalogo="tipo_cop_operativo", codigo="ORIGEN").scalar()
        assert len(tenures) == 2
        token = uuid.uuid4().hex[:10]
        projects, datasets = {}, {}
        for size in sizes:
            project = db.execute(insert(models.Proyecto).values(
                clave_proyecto=f"COP-{token}-{size}", nombre_proyecto=f"COP sintético {size}",
                creado_por=actor).returning(models.Proyecto.id_proyecto)).scalar_one()
            projects[size] = project
            if not size:
                datasets[size] = dict(nuclei=[], pns=[], affects=[], agreements=[], links=[], expected=(0, 0, 0))
                continue
            # Equal entity/municipality/name with different tenures: valid ties
            # under uq_nucleo_activo_normalizado, without disabling constraints.
            nuclei = list(db.execute(insert(models.NucleoAgrario).returning(models.NucleoAgrario.id_nucleo), [
                dict(id_municipio=1, nombre_nucleo=f"COP {token} {size} {i//2:05}",
                     id_tipo_tenencia=tenures[i % 2], creado_por=actor) for i in range(size)
            ]).scalars())
            pns = list(db.execute(insert(models.ProyectoNucleo).returning(models.ProyectoNucleo.id_proyecto_nucleo), [
                dict(id_proyecto=project, id_nucleo=n, creado_por=actor) for n in nuclei
            ]).scalars())
            # Unsigned individual instruments avoid introducing unrelated
            # individual-signature titular/census requirements into fixtures.
            affects = list(db.execute(insert(models.Afectacion).returning(models.Afectacion.id_afectacion), [
                dict(id_proyecto_nucleo=pn, tipo_afectacion="individual" if i % 2 else "colectivo",
                     id_tipo_cop_operativo=None if i % 2 else cop, creado_por=actor) for i, pn in enumerate(pns)
            ]).scalars())
            agreements = list(db.execute(insert(models.Convenio).returning(models.Convenio.id_convenio), [
                dict(id_proyecto_nucleo=pn, ambito="individual" if i % 2 else "colectivo",
                     tipo_instrumento="otro", tipo_convenio=None,
                     descripcion_instrumento="Instrumento COP sintético", consecutivo=1,
                     fecha_firma=None if i % 2 else date(2026, 1, 2), creado_por=actor)
                for i, pn in enumerate(pns)
            ]).scalars())
            links = list(db.execute(insert(models.ConvenioAfectacion).returning(models.ConvenioAfectacion.id_convenio_afectacion), [
                dict(id_convenio=c, id_afectacion=a, creado_por=actor) for c, a in zip(agreements, affects)
            ]).scalars())
            # Multiple active affectations for a single agreement must not count
            # or export that agreement twice.
            extra = db.execute(insert(models.Afectacion).values(
                id_proyecto_nucleo=pns[0], tipo_afectacion="colectivo", id_tipo_cop_operativo=cop, creado_por=actor
            ).returning(models.Afectacion.id_afectacion)).scalar_one()
            db.execute(insert(models.ConvenioAfectacion).values(
                id_convenio=agreements[0], id_afectacion=extra, rol="adicional", creado_por=actor))
            datasets[size] = dict(nuclei=nuclei, pns=pns, affects=affects, agreements=agreements,
                                  links=links, extra_affect=extra, expected=(size//2, (size+1)//2, (size+1)//2))
        users, emails = {}, {}
        password = "CopSintetico2026!QA"
        password_hash = hash_password(password)
        for role in (*ROLES, "unassigned", "revoked"):
            email = f"{uuid.uuid4().hex}@local.invalid"
            uid = db.execute(insert(models.Usuario).values(
                nombre="COP", apellido_paterno="QA", correo=email,
                rol=role if role in ROLES else "operador", contrasena_hash=password_hash,
                fecha_alta=datetime.now(timezone.utc),
            ).returning(models.Usuario.id_usuario)).scalar_one()
            users[role] = SimpleNamespace(id_usuario=uid, rol=role if role in ROLES else "operador")
            emails[role] = email
            if role == "operador":
                db.execute(insert(models.UsuarioProyecto), [dict(id_usuario=uid, id_proyecto=p,
                    asignado_por=actor, creado_por=actor) for p in projects.values()])
        # Validate deferred integrity too; no trigger is disabled for fixtures.
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        db.commit()
        env.update(projects=projects, datasets=datasets, users=users, emails=emails, password=password, actor=actor, cop=cop)
    return env


@pytest.fixture(scope="module")
def cop_env(transactional_api):
    return make_cop_env(transactional_api, SIZES)


@contextmanager
def checkpoint(env):
    tx = env["connection"].begin_nested()
    try:
        yield
    finally:
        tx.rollback()


@pytest.fixture
def cop_scale_env(transactional_api):
    with checkpoint(transactional_api):
        yield make_cop_env(transactional_api, (10000,))


def save_evidence(name, value):
    directory = os.getenv("COP_EVIDENCE_DIR")
    if directory:
        Path(directory).mkdir(parents=True, exist_ok=True)
        Path(directory, name).write_text(json.dumps(value, indent=2, default=str))


def sample(env, client, paths, *, memory=False):
    stats = dict(selects=0, orm_objects=0, http_requests=0)
    def sql(conn, cursor, statement, params, context, many):
        if statement.lstrip().upper().startswith(("SELECT", "WITH")):
            stats["selects"] += 1
    def loaded(session, obj):
        stats["orm_objects"] += 1
    event.listen(env["connection"], "before_cursor_execute", sql)
    event.listen(Session, "loaded_as_persistent", loaded)
    if memory:
        tracemalloc.start()
    try:
        started = time.perf_counter()
        responses = []
        for path in paths:
            response = client.get(path)
            stats["http_requests"] += 1
            assert response.status_code == 200, response.text
            responses.append(response)
        stats["milliseconds"] = (time.perf_counter() - started) * 1000
        stats["json_bytes"] = sum(len(r.content) for r in responses)
        if memory:
            stats["python_peak_bytes"] = tracemalloc.get_traced_memory()[1]
        return stats, [r.json() for r in responses]
    finally:
        if memory:
            tracemalloc.stop()
        event.remove(env["connection"], "before_cursor_execute", sql)
        event.remove(Session, "loaded_as_persistent", loaded)


def test_capture_baseline(cop_env):
    """Current F04 endpoint, before app changes; not the pre-F04 N+1 traversal."""
    results = {}
    with TestClient(app) as client:
        for size, project in cop_env["projects"].items():
            base = f"/api/proyectos/{project}"
            paths = [base + "/nucleos", base + "/dashboard/convenios"]
            sample(cop_env, client, paths)
            samples = [sample(cop_env, client, paths)[0] for _ in range(5)]
            memory, payload = sample(cop_env, client, paths, memory=True)
            nuclei, agreements = payload
            assert len(nuclei) == min(size, 100)
            assert len(agreements["convenios"]) == min(size, 100)
            results[str(size)] = dict(samples=samples, median_ms=statistics.median(
                s["milliseconds"] for s in samples), memory=memory,
                nuclei=len(nuclei), agreements=len(agreements["convenios"]),
                counts={k: agreements[k] for k in ("individuales", "colectivos", "formalizados")})
    save_evidence("baseline.json", results)


def read_all(client, base, resource, limit=200):
    path = base + "/dashboard/exportacion/" + resource
    cursor, revision, items, totals = 0, None, [], []
    while True:
        params = dict(despues_de=cursor, limit=limit)
        if revision is not None:
            params["revision"] = revision
        response = client.get(path, params=params)
        assert response.status_code == 200, response.text
        page = response.json()
        if revision is None:
            revision = page["revision"]
        assert page["revision"] == revision
        assert len(page["items"]) <= limit
        items.extend(page["items"])
        totals.append(page["total"])
        if not page["hay_mas"]:
            assert page["siguiente_id"] is None
            break
        assert page["siguiente_id"] > cursor
        cursor = page["siguiente_id"]
    key = "id_convenio" if resource == "convenios" else "id_proyecto_nucleo"
    assert len(items) == len({i[key] for i in items}) == totals[0]
    assert totals == [totals[0]] * len(totals)
    assert [i[key] for i in items] == sorted(i[key] for i in items)
    return items, revision


@pytest.mark.parametrize("size", SIZES)
def test_complete_counts_and_export(cop_env, size):
    data = cop_env["datasets"][size]
    base = f"/api/proyectos/{cop_env['projects'][size]}"
    with TestClient(app) as client:
        summary = client.get(base + "/dashboard/resumen").json()
        assert summary == dict(total_nucleos=size, total_convenios=size,
            individuales=data["expected"][0], colectivos=data["expected"][1], formalizados=data["expected"][2])
        # A deliberately awkward page size exercises ties and boundaries.
        nuclei, _ = read_all(client, base, "nucleos", 99)
        agreements, _ = read_all(client, base, "convenios", 99)
        assert {n["id_proyecto_nucleo"] for n in nuclei} == set(data["pns"])
        assert {c["id_convenio"] for c in agreements} == set(data["agreements"])
        assert all(c["tipo_convenio"] is None for c in agreements)
        if size:
            assert len({n["nombre_nucleo"] for n in nuclei}) < size
            # Every tail agreement is present, including nuclei 101/201/1000.
            assert agreements[-1]["id_convenio"] == data["agreements"][-1]


@pytest.mark.parametrize("role", (*ROLES, "unassigned", "revoked", "anonymous"))
@pytest.mark.parametrize("resource", ("resumen", "exportacion/nucleos", "exportacion/convenios"))
def test_authorization(cop_env, monkeypatch, role, resource):
    env = cop_env
    if role == "anonymous":
        monkeypatch.delitem(app.dependency_overrides, auth.get_current_user)
    else:
        monkeypatch.setitem(app.dependency_overrides, auth.get_current_user, lambda: env["users"][role])
    with checkpoint(env):
        if role == "revoked":
            with env["session_factory"]() as db:
                set_audit_context(db, env["actor"])
                db.execute(insert(models.UsuarioProyecto).values(
                    id_usuario=env["users"][role].id_usuario, id_proyecto=env["projects"][201],
                    asignado_por=env["actor"], creado_por=env["actor"], activo=False,
                    fecha_baja=datetime.now(timezone.utc), id_usuario_baja=env["actor"], motivo_baja="Revocación sintética"))
                db.commit()
        with TestClient(app) as client:
            response = client.get(f"/api/proyectos/{env['projects'][201]}/dashboard/{resource}")
            assert response.status_code == (401 if role == "anonymous" else 403 if role in ("unassigned", "revoked") else 200)
            if role in ROLES:
                assert client.get(f"/api/proyectos/2147483647/dashboard/{resource}").status_code == 403
                with env["session_factory"]() as db:
                    set_audit_context(db, env["actor"])
                    db.execute(text("UPDATE proyecto SET activo=false, fecha_baja=now(), id_usuario_baja=:actor, motivo_baja='Prueba COP' WHERE id_proyecto=:p"),
                               dict(actor=env["actor"], p=env["projects"][201]))
                    db.commit()
                assert client.get(f"/api/proyectos/{env['projects'][201]}/dashboard/{resource}").status_code == 403


@pytest.mark.parametrize("role", (*ROLES, "unassigned"))
def test_real_sessions(cop_env, monkeypatch, role):
    env = cop_env
    monkeypatch.delitem(app.dependency_overrides, auth.get_current_user)
    monkeypatch.setattr(main_module, "SessionLocal", env["session_factory"])
    with checkpoint(env):
        client, _ = _login(env["emails"][role], env["password"])
        try:
            for route in ("resumen", "exportacion/nucleos", "exportacion/convenios"):
                path = f"/api/proyectos/{env['projects'][201]}/dashboard/{route}"
                assert client.get(path).status_code == (403 if role == "unassigned" else 200)
        finally:
            client.close()


@pytest.mark.parametrize("state", ("pn", "nucleus", "affectation", "link", "agreement", "all_agreements"))
@pytest.mark.parametrize("role", ROLES)
def test_active_semantics_and_dedup(cop_env, monkeypatch, state, role):
    env = cop_env
    monkeypatch.setitem(app.dependency_overrides, auth.get_current_user, lambda: env["users"][role])
    data = env["datasets"][105]
    base = f"/api/proyectos/{env['projects'][105]}"
    with checkpoint(env):
        with env["session_factory"]() as db:
            set_audit_context(db, env["actor"])
            table, key, identity = {
                "pn": ("proyecto_nucleo", "id_proyecto_nucleo", data["pns"][-1]),
                "nucleus": ("nucleo_agrario", "id_nucleo", data["nuclei"][-1]),
                "affectation": ("afectacion", "id_afectacion", data["affects"][-1]),
                "link": ("convenio_afectacion", "id_convenio_afectacion", data["links"][-1]),
                "agreement": ("convenio", "id_convenio", data["agreements"][-1]),
                "all_agreements": ("convenio", "id_proyecto_nucleo", None),
            }[state]
            if state == "link":
                # Keep a legal active link, but to an inactive affectation.
                # The inactive primary link must not make the agreement visible.
                alternative = db.execute(insert(models.Afectacion).values(
                    id_proyecto_nucleo=data["pns"][-1], tipo_afectacion="colectivo",
                    id_tipo_cop_operativo=env["cop"], creado_por=env["actor"],
                ).returning(models.Afectacion.id_afectacion)).scalar_one()
                db.execute(insert(models.ConvenioAfectacion).values(
                    id_convenio=data["agreements"][-1], id_afectacion=alternative,
                    rol="adicional", creado_por=env["actor"]))
                db.execute(text("UPDATE afectacion SET activo=false, fecha_baja=now(), id_usuario_baja=:actor, motivo_baja='Prueba COP' WHERE id_afectacion=:id"),
                           dict(actor=env["actor"], id=alternative))
            # Only constant table/column names above; values remain bound.
            condition = f"{key}=:id" if state != "all_agreements" else "id_proyecto_nucleo IN (SELECT id_proyecto_nucleo FROM proyecto_nucleo WHERE id_proyecto=:project)"
            db.execute(text(f"UPDATE {table} SET activo=false, fecha_baja=now(), id_usuario_baja=:actor, motivo_baja='Prueba COP' WHERE {condition}"),
                       dict(actor=env["actor"], id=identity, project=env["projects"][105]))
            db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            db.commit()
        with TestClient(app) as client:
            summary = client.get(base + "/dashboard/resumen").json()
            agreements, _ = read_all(client, base, "convenios")
            nuclei, _ = read_all(client, base, "nucleos")
            # Explicitly preserve the view's historical PN-active criterion.
            expected = 0 if state == "all_agreements" else 105 if state == "nucleus" else 104
            assert summary["total_convenios"] == len(agreements) == expected
            assert summary["total_nucleos"] == len(nuclei) == (104 if state == "pn" else 105)
            if expected:
                assert sum(c["id_convenio"] == data["agreements"][0] for c in agreements) == 1


def test_cross_nucleus_link_remains_invalid(cop_env):
    env = cop_env
    data = env["datasets"][105]
    with checkpoint(env), env["session_factory"]() as db:
        set_audit_context(db, env["actor"])
        with pytest.raises(DBAPIError, match="compartir ProyectoNucleo"):
            db.execute(insert(models.ConvenioAfectacion).values(
                id_convenio=data["agreements"][0], id_afectacion=data["affects"][2],
                rol="adicional", creado_por=env["actor"]))


@pytest.mark.parametrize("change", ("unsigned_collective", "signed_individual", "cop_original"))
def test_signature_and_category_are_agreement_fields(cop_env, change):
    env = cop_env
    data = env["datasets"][105]
    target = data["agreements"][1 if change == "signed_individual" else -1]
    with checkpoint(env), env["session_factory"]() as db:
        set_audit_context(db, env["actor"])
        db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        if change == "signed_individual":
            person = db.execute(insert(models.Persona).values(
                nombre="Firmante COP sintético", apellido_paterno="QA", creado_por=env["actor"],
            ).returning(models.Persona.id_persona)).scalar_one()
            def catalog(kind, code):
                return db.query(models.CatalogoOperativo.id_catalogo_opcion).filter_by(
                    tipo_catalogo=kind, codigo=code, activo=True).scalar()
            db.execute(insert(models.ConvenioCompareciente).values(
                id_convenio=target, id_persona=person,
                id_tipo_calidad=catalog("calidad_compareciente_convenio", "titular_parcelario"),
                id_tipo_acreditacion=catalog("tipo_acreditacion_derecho_individual", "certificado_parcelario"),
                referencia_acreditacion="COP-SINTETICO", nombre_en_instrumento="Firmante COP sintético",
                es_firmante=True, creado_por=env["actor"]))
            db.execute(text("UPDATE convenio SET fecha_firma='2026-01-03' WHERE id_convenio=:id"), dict(id=target))
        elif change == "unsigned_collective":
            db.execute(text("UPDATE convenio SET fecha_firma=NULL WHERE id_convenio=:id"), dict(id=target))
        else:
            db.execute(text("UPDATE convenio SET tipo_instrumento='convenio', tipo_convenio='cop_original' WHERE id_convenio=:id"), dict(id=target))
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        db.commit()
        with TestClient(app) as client:
            base = f"/api/proyectos/{env['projects'][105]}"
            response = client.get(base + "/dashboard/resumen")
            assert response.status_code == 200, response.text
            expected_signed = 52 if change == "unsigned_collective" else 54 if change == "signed_individual" else 53
            assert response.json() == dict(total_nucleos=105, total_convenios=105,
                                          individuales=52, colectivos=53, formalizados=expected_signed)
            items, _ = read_all(client, base, "convenios")
            agreement = next(c for c in items if c["id_convenio"] == target)
            assert agreement["tipo_convenio"] == ("cop_original" if change == "cop_original" else None)


@pytest.mark.parametrize("resource", ("nucleos", "convenios"))
@pytest.mark.parametrize("params", ({"limit": 0}, {"limit": 201}, {"despues_de": -1},
                                    {"revision": "bad"}, {"despues_de": 1}))
def test_invalid_pagination(cop_env, resource, params):
    with TestClient(app) as client:
        response = client.get(f"/api/proyectos/{cop_env['projects'][105]}/dashboard/exportacion/{resource}", params=params)
        assert response.status_code == 422


@pytest.mark.parametrize("resource", ("nucleos", "convenios"))
def test_revision_detects_same_count_edits_and_deletions(cop_env, resource):
    env = cop_env
    base = f"/api/proyectos/{env['projects'][105]}/dashboard/exportacion/{resource}"
    with TestClient(app) as client:
        first = client.get(base, params={"limit": 1}).json()
        with checkpoint(env):
            with env["session_factory"]() as db:
                set_audit_context(db, env["actor"])
                if resource == "nucleos":
                    db.execute(text("UPDATE nucleo_agrario SET nombre_nucleo=nombre_nucleo || ' editado' WHERE id_nucleo=:id"),
                               dict(id=env["datasets"][105]["nuclei"][-1]))
                else:
                    db.execute(text("UPDATE convenio SET fecha_firma='2026-02-01' WHERE id_convenio=:id"),
                               dict(id=env["datasets"][105]["agreements"][-1]))
                db.commit()
            for cursor in (0, first["siguiente_id"]):
                response = client.get(base, params=dict(despues_de=cursor, revision=first["revision"]))
                assert response.status_code == 409
        # Original revision is valid again after rollback of synthetic edit.
        assert client.get(base, params=dict(despues_de=first["siguiente_id"], revision=first["revision"])).status_code == 200
        end = client.get(base, params=dict(despues_de=2147483647, revision=first["revision"])).json()
        assert end["items"] == [] and end["total"] == 105
        assert end["hay_mas"] is False and end["siguiente_id"] is None


@pytest.mark.parametrize("resource", ("nucleos", "convenios"))
def test_removal_and_revocation_between_pages(cop_env, monkeypatch, resource):
    env = cop_env
    project = env["projects"][105]
    path = f"/api/proyectos/{project}/dashboard/exportacion/{resource}"
    monkeypatch.setitem(app.dependency_overrides, auth.get_current_user, lambda: env["users"]["operador"])
    with TestClient(app) as client:
        first = client.get(path, params={"limit": 1}).json()
        params = dict(despues_de=first["siguiente_id"], revision=first["revision"])
        with checkpoint(env), env["session_factory"]() as db:
            set_audit_context(db, env["actor"])
            db.execute(text("UPDATE proyecto_nucleo SET activo=false, fecha_baja=now(), id_usuario_baja=:actor, motivo_baja='Prueba COP' WHERE id_proyecto_nucleo=:id"),
                       dict(actor=env["actor"], id=env["datasets"][105]["pns"][-1]))
            db.commit()
            assert client.get(path, params=params).status_code == 409
        with checkpoint(env), env["session_factory"]() as db:
            set_audit_context(db, env["actor"])
            db.execute(text("UPDATE usuario_proyecto SET activo=false, fecha_baja=now(), id_usuario_baja=:actor, motivo_baja='Prueba COP' WHERE id_proyecto=:p AND id_usuario=:u"),
                       dict(actor=env["actor"], p=project, u=env["users"]["operador"].id_usuario))
            db.commit()
            assert client.get(path, params=params).status_code == 403


def test_export_performance(cop_env):
    """Explicit export includes all batches and two final revision validations."""
    env = cop_env
    results = {}
    with TestClient(app) as client:
        for size, project in env["projects"].items():
            base = f"/api/proyectos/{project}"
            paths = []
            for resource in ("nucleos", "convenios"):
                cursor, revision = 0, None
                route = base + "/dashboard/exportacion/" + resource
                while True:
                    path = f"{route}?limit=200&despues_de={cursor}" + (f"&revision={revision}" if revision else "")
                    page = client.get(path).json()
                    paths.append(path)
                    revision = page["revision"]
                    if not page["hay_mas"]:
                        break
                    cursor = page["siguiente_id"]
                paths.append(f"{route}?limit=1&revision={revision}")
            samples = [sample(env, client, paths)[0] for _ in range(5)]
            memory, payload = sample(env, client, paths, memory=True)
            expected_requests = 2 * max(1, (size + 199)//200) + 2
            assert all(s["http_requests"] == expected_requests and s["selects"] == 2*expected_requests
                       and s["orm_objects"] == expected_requests for s in samples)
            assert all(p["total"] == size for p in payload)
            results[str(size)] = dict(samples=samples, median_ms=statistics.median(s["milliseconds"] for s in samples),
                memory=memory, unique_rows=2*size, max_page_rows=200, final_revision_checks=2)
    save_evidence("export.json", results)


def test_ten_thousand_nuclei_export_cost(cop_scale_env):
    """Stress the O(N) revision per page separately from initial indicators."""
    env = cop_scale_env
    project = env["projects"][10000]
    base = f"/api/proyectos/{project}"
    result = {}
    with TestClient(app) as client:
        summary_paths = [base + "/dashboard/resumen"]
        sample(env, client, summary_paths)
        initial = [sample(env, client, summary_paths)[0] for _ in range(5)]
        assert all(s["selects"] == 2 and s["http_requests"] == 1 and s["orm_objects"] == 1 for s in initial)
        memory, payload = sample(env, client, summary_paths, memory=True)
        assert payload[0] == dict(total_nucleos=10000, total_convenios=10000,
                                   individuales=5000, colectivos=5000, formalizados=5000)
        result["summary"] = dict(samples=initial, median_ms=statistics.median(s["milliseconds"] for s in initial), memory=memory)
        paths = []
        for resource in ("nucleos", "convenios"):
            rows, revision = read_all(client, base, resource)
            assert len(rows) == 10000
            key = "id_convenio" if resource == "convenios" else "id_proyecto_nucleo"
            route = base + "/dashboard/exportacion/" + resource
            for start in range(0, 10000, 200):
                cursor = 0 if start == 0 else rows[start-1][key]
                paths.append(f"{route}?limit=200&despues_de={cursor}&revision={revision}")
            paths.append(f"{route}?limit=1&revision={revision}")
        samples = [sample(env, client, paths)[0] for _ in range(3)]
        assert all(s["selects"] == 204 and s["http_requests"] == 102 for s in samples)
        memory, _ = sample(env, client, paths, memory=True)
        result["export"] = dict(samples=samples, median_ms=statistics.median(s["milliseconds"] for s in samples),
                                memory=memory, unique_rows=20000, max_page_rows=200, final_revision_checks=2)
    save_evidence("scale-10000.json", result)


def test_published_openapi_matches_runtime():
    docs = Path(os.environ.get("REPORT_CONTRACT_DOCS", str(Path(__file__).resolve().parents[2]/"docs")))
    assert json.loads((docs/"openapi.json").read_text()) == app.openapi()


def test_revision_required_error_matches_openapi():
    from tests.test_convenio_general_report import validate_contract
    with pytest.raises(HTTPException) as error:
        dashboard_summary.project_export_page(None, 1, "convenios", 1, 200, None)
    assert error.value.status_code == 422
    validate_contract({"detail": error.value.detail}, "HTTPValidationError")


def test_summary_performance_and_sql_plans(cop_env):
    env = cop_env
    results, plans = {}, {}
    with TestClient(app) as client:
        for size, project in env["projects"].items():
            base = f"/api/proyectos/{project}"
            paths = {"baseline_initial": [base+"/nucleos", base+"/dashboard/convenios"],
                     "complete_summary": [base+"/dashboard/resumen"],
                     "complete_with_visible_page": [base+"/nucleos", base+"/dashboard/resumen"]}
            measurements = {}
            for variant, urls in paths.items():
                sample(env, client, urls)
                samples = [sample(env, client, urls)[0] for _ in range(5)]
                memory, payloads = sample(env, client, urls, memory=True)
                measurements[variant] = dict(samples=samples, median_ms=statistics.median(s["milliseconds"] for s in samples),
                                             memory=memory, counts=payloads[-1] if variant != "baseline_initial" else {
                                                 k:payloads[-1][k] for k in ("individuales", "colectivos", "formalizados")})
                expected_selects = {"baseline_initial":5, "complete_summary":2, "complete_with_visible_page":4}[variant]
                assert all(s["selects"] == expected_selects for s in samples)
                if variant == "complete_summary":
                    assert all(s["orm_objects"] == 1 and s["http_requests"] == 1 for s in samples)
                    assert memory["json_bytes"] < 160
            results[str(size)] = measurements
            if size in (100, 201, 1000):
                with env["session_factory"]() as db:
                    statements = {"summary": dashboard_summary.summary_statement(project),
                        "export_nuclei": dashboard_summary.export_page_statement(dashboard_summary.export_nuclei(project), "id_proyecto_nucleo", 0, 200),
                        "export_agreements": dashboard_summary.export_page_statement(dashboard_summary.complete_agreements(project), "id_convenio", 0, 200)}
                    plans[str(size)] = {}
                    for name, stmt in statements.items():
                        sql = str(stmt.compile(db.bind, compile_kwargs={"literal_binds": True}))
                        plan = db.execute(text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql)).scalar_one()
                        plans[str(size)][name] = dict(sql=sql, plan=plan)
                    plans["indexes"] = [dict(r) for r in db.execute(text("SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' AND tablename IN ('proyecto_nucleo','afectacion','convenio','convenio_afectacion','nucleo_agrario') ORDER BY tablename,indexname")).mappings()]
    save_evidence("comparison.json", results)
    save_evidence("plans.json", plans)
