"""Integridad del artefacto y controles de la sincronización RAN."""

import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.database import engine
from scripts import import_catalogo_nucleos_ran as importer
from scripts import sync_catalogo_ran as sync


APPROVED_SHA = "863d31fff0f9b0338a103c7858872d4f531fe2b2593aade514dac2233d2fa6c3"
FIXTURES = sync.DEFAULT_METADATA.parent


def test_approved_dataset_exact_bytes_and_contract():
    metadata, dataset, crosswalk, audit = sync.validate_manifest(sync.DEFAULT_METADATA)
    assert dataset.stat().st_size == metadata["size_bytes"] == 2341409
    assert importer._sha256(dataset) == metadata["sha256"] == APPROVED_SHA
    assert audit.total_rows == audit.unique_keys == 32278
    assert audit.states == 32
    assert audit.ejidos == 29852 and audit.comunidades == 2426
    assert audit.duplicate_keys == audit.unknown_types == 0
    assert all(r.source_id.strip() and r.name.strip() for r in audit.rows)
    assert metadata["encoding"] == "cp1252"
    assert importer._sha256(crosswalk) == metadata["crosswalk_sha256"] == (
        "ddadabf417571722b50289724486045037f020c7e6fc2e49db69585d6c6651cb"
    )
    with dataset.open(encoding="cp1252", newline="") as source:
        assert next(csv.reader(source)) == [
            "cve_unica", "scncve_edo", "Estado", "scncve_mun", "Municipio", "SCNNom_Nuc", "tipo"
        ]


def test_dataset_excludes_actual_additional_ran_identities():
    _, _, _, audit = sync.validate_manifest(sync.DEFAULT_METADATA)
    keys = {r.source_id.strip() for r in audit.rows}
    connection = engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT btrim(id_nucleo_fuente) FROM nucleo_agrario WHERE fuente_datos = %s",
                           (importer.SOURCE,))
            stored = {r[0] for r in cursor.fetchall()}
        extras = stored - keys
        assert len(extras) == 51
        assert extras.isdisjoint(keys)
        assert keys.issubset(stored)
    finally:
        if connection.is_valid:
            connection.rollback()
            connection.close()


@pytest.fixture
def manifest(tmp_path):
    dataset = tmp_path / "ran.csv"
    with dataset.open("w", encoding="cp1252", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=importer.EXPECTED_HEADERS)
        writer.writeheader()
        for index, kind in enumerate(("EJIDO", "COMUNIDAD")):
            writer.writerow(dict(cve_unica=f"TEST_SYNC_{index}", scncve_edo="1", scncve_mun="1",
                                 Estado="Aguascalientes", Municipio="Aguascalientes",
                                 SCNNom_Nuc="Peñón", tipo=kind))
    crosswalk = tmp_path / "crosswalk.csv"
    crosswalk.write_bytes((FIXTURES / "ran_municipio_inegi_crosswalk.csv").read_bytes())
    metadata = json.loads(sync.DEFAULT_METADATA.read_text())
    metadata.update(filename=dataset.name, sha256=importer._sha256(dataset),
                    size_bytes=dataset.stat().st_size, rows=2, unique_keys=2,
                    expected_entities=1, expected_types={"EJIDO": 1, "COMUNIDAD": 1},
                    columns=list(importer.EXPECTED_HEADERS), crosswalk_filename=crosswalk.name)
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(metadata))
    return path, metadata, dataset, crosswalk


@pytest.mark.parametrize("change,match", [
    ({"sha256": "0" * 64}, "Checksum"),
    ({"size_bytes": 1}, "Tamaño"),
    ({"rows": 3, "unique_keys": 3, "expected_types": {"EJIDO": 2, "COMUNIDAD": 1}}, "Conteos distintos"),
    ({"expected_entities": 2}, "Conteos distintos"),
    ({"crosswalk_sha256": "0" * 64}, "Checksum"),
    ({"filename": "absent.csv"}, "inexistente"),
    ({"filename": "../ran.csv"}, "junto"),
    ({"encoding": "utf-8"}, "encoding"),
    ({"columns": ["secret"]}, "Columnas"),
    ({"rows": True}, "Metadata"),
    ({"source": "QA"}, "Fuente"),
])
def test_manifest_rejects_invalid_artifacts(manifest, change, match):
    path, metadata, _, _ = manifest
    metadata.update(change)
    path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match=match):
        sync.validate_manifest(path)


@pytest.mark.parametrize("value", ["{bad", "[]", "null"])
def test_invalid_metadata_json(manifest, value):
    path = manifest[0]
    path.write_text(value)
    with pytest.raises(ValueError):
        sync.validate_manifest(path)


def test_missing_metadata(tmp_path):
    with pytest.raises(ValueError, match="Manifiesto"):
        sync.validate_manifest(tmp_path / "absent.json")


def test_corrupt_crosswalk_with_updated_hash_still_rejected(manifest):
    path, metadata, _, crosswalk = manifest
    crosswalk.write_text("wrong,headers\n1,2\n")
    metadata["crosswalk_sha256"] = importer._sha256(crosswalk)
    path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="Artefactos inválidos"):
        sync.validate_manifest(path)


@pytest.mark.parametrize("variable,value", [
    ("DB_NAME", "wrong"), ("DB_HOST", "other"), ("DB_PORT", "9999"),
    ("DB_RUNTIME_USER", "other"), ("DB_RUNTIME_PASSWORD", "other"),
])
def test_conflicting_connection_config_stops(monkeypatch, variable, value):
    for key in ("DB_NAME", "DB_HOST", "DB_PORT", "DB_RUNTIME_USER", "DB_RUNTIME_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://account:secret@db:5432/target")
    monkeypatch.setenv(variable, value)
    with pytest.raises(ValueError, match="contradictoria"):
        sync.validate_connection_configuration()


class FakeConnection:
    def __init__(self, users=()):
        self.users = users
        self.closed = self.rolled_back = False
    def set_session(self, **kwargs):
        assert kwargs == {"readonly": True}
    def cursor(self):
        return self
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def execute(self, statement, params):
        assert "lower(btrim(correo))" in statement
        assert params == ("actor@example.invalid",)
    def fetchall(self):
        return self.users
    def rollback(self):
        self.rolled_back = True
    def close(self):
        self.closed = True


@pytest.mark.parametrize("users", [[], [(7, False, "admin")], [(7, True, "operador")],
                                   [(7, True, "admin"), (8, True, "admin")]])
def test_actor_rejected_and_connection_closed(monkeypatch, users):
    connection = FakeConnection(users)
    monkeypatch.setattr(sync, "validate_connection_configuration", lambda: None)
    monkeypatch.setattr(importer, "connect_database", lambda: connection)
    monkeypatch.setattr(importer, "validate_database", lambda c, d: d)
    with pytest.raises(ValueError, match="administrador activo"):
        sync.preflight_database("target", "actor@example.invalid")
    assert connection.closed and connection.rolled_back


def test_actor_id_resolved_not_assumed(monkeypatch):
    connection = FakeConnection([(42, True, "admin")])
    monkeypatch.setattr(sync, "validate_connection_configuration", lambda: None)
    monkeypatch.setattr(importer, "connect_database", lambda: connection)
    monkeypatch.setattr(importer, "validate_database", lambda c, d: d)
    assert sync.preflight_database("target", "actor@example.invalid") == ("target", 42)
    assert connection.closed and connection.rolled_back


def test_wrong_real_database_aborts(monkeypatch):
    connection = FakeConnection()
    monkeypatch.setattr(sync, "validate_connection_configuration", lambda: None)
    monkeypatch.setattr(importer, "connect_database", lambda: connection)
    def reject(c, d):
        raise ValueError("Base inesperada")
    monkeypatch.setattr(importer, "validate_database", reject)
    with pytest.raises(ValueError, match="inesperada"):
        sync.preflight_database("target", None)
    assert connection.closed and connection.rolled_back


def report(insertions=0, updates=0, mode="dry-run", **changes):
    value = dict(database="target", dataset_sha256=APPROVED_SHA, rows=32278,
                 insertions=insertions, updates=updates, unchanged=32278-insertions-updates,
                 errors=0, unresolved_crosswalk=0, success=True, mode=mode)
    value.update(changes)
    return value


@pytest.mark.parametrize("bad", [dict(success=False), dict(errors=1), dict(unresolved_crosswalk=1),
                                  dict(database="wrong"), dict(dataset_sha256="wrong"),
                                  dict(insertions=-1), dict(unchanged=1), dict(mode="apply")])
def test_rejects_invalid_importer_report(monkeypatch, bad):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=0, stdout=json.dumps(report(**bad))))
    with pytest.raises(ValueError):
        sync.run_importer(Path("ran.csv"), Path("crosswalk.csv"), "target",
                          {"rows": 32278, "sha256": APPROVED_SHA})


@pytest.mark.parametrize("returncode,stdout", [(1, json.dumps(report())), (0, "not JSON")])
def test_importer_failure_aborts(monkeypatch, returncode, stdout):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=returncode, stdout=stdout))
    with pytest.raises(ValueError):
        sync.run_importer(Path("ran.csv"), Path("crosswalk.csv"), "target",
                          {"rows": 32278, "sha256": APPROVED_SHA})


@pytest.mark.parametrize("insertions,updates,apply,expected_modes", [
    (0, 0, False, ["dry-run"]), (0, 0, True, ["dry-run"]),
    (2, 0, False, ["dry-run"]), (0, 2, False, ["dry-run"]),
    (2, 0, True, ["dry-run", "apply", "dry-run"]),
    (0, 2, True, ["dry-run", "apply", "dry-run"]),
])
def test_sync_control_flow(monkeypatch, insertions, updates, apply, expected_modes):
    metadata = {"rows": 32278, "sha256": APPROVED_SHA}
    monkeypatch.setattr(sync, "validate_manifest", lambda p: (metadata, Path("ran.csv"), Path("cross.csv"), None))
    monkeypatch.setattr(sync, "preflight_database", lambda d, a: (d, 42))
    monkeypatch.setattr(sync, "verify_coverage", lambda d, a: {"covered_keys": 32278})
    modes = []
    def invoke(*a, actor_id=None):
        modes.append("apply" if actor_id is not None else "dry-run")
        if actor_id is not None:
            assert actor_id == 42
        return report(insertions, updates) if len(modes) == 1 else report()
    monkeypatch.setattr(sync, "run_importer", invoke)
    args = ["--expected-database", "target"]
    if apply:
        args += ["--apply", "--actor-email", "actor@example.invalid"]
    assert sync.main(args) == 0
    assert modes == expected_modes


def test_dirty_second_dry_run_is_error(monkeypatch):
    monkeypatch.setattr(sync, "validate_manifest", lambda p: ({}, Path("a"), Path("b"), None))
    monkeypatch.setattr(sync, "preflight_database", lambda d, a: (d, 42))
    monkeypatch.setattr(sync, "run_importer", lambda *a, **k: report(updates=1))
    assert sync.main(["--expected-database", "target", "--actor-email", "actor@example.invalid", "--apply"]) == 1


def test_apply_requires_actor():
    with pytest.raises(SystemExit) as exc:
        sync.main(["--expected-database", "target", "--apply"])
    assert exc.value.code == 2


def test_shell_from_other_directory_validates_before_database(tmp_path):
    result = subprocess.run(["bash", str(Path(sync.__file__).with_suffix(".sh")),
                             "--expected-database", "target", "--metadata", str(tmp_path / "absent.json")],
                            cwd=tmp_path, capture_output=True, text=True,
                            env={**os.environ, "PYTHON_BIN": sys.executable})
    assert result.returncode == 1
    assert "Manifiesto inexistente" in result.stderr


def test_importer_json_missing_file_is_machine_readable(tmp_path, capsys):
    assert importer.main([str(tmp_path / "missing.csv"), "--report-json"]) == 1
    value = json.loads(capsys.readouterr().out)
    assert value["success"] is False and value["errors"] == 1
    assert value["mode"] == "dry-run"


def test_importer_json_dry_run_is_one_object(manifest, monkeypatch, capsys):
    connection = FakeConnection()
    monkeypatch.setattr(importer, "connect_database", lambda: connection)
    monkeypatch.setattr(importer, "validate_database", lambda c, d: "target")
    monkeypatch.setattr(importer, "build_plan", lambda *a: importer.ImportPlan(new_records=1))
    assert importer.main([str(manifest[2]), "--crosswalk-path", str(manifest[3]),
                          "--expected-database", "target", "--report-json"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["database"] == "target"
    assert value["insertions"] == value["unchanged"] == 1
    assert value["updates"] == value["errors"] == value["unresolved_crosswalk"] == 0
    assert value["success"] is True and value["mode"] == "dry-run"
    assert connection.rolled_back and connection.closed


def test_importer_human_cli_preserved(manifest, monkeypatch, capsys):
    connection = FakeConnection()
    monkeypatch.setattr(importer, "connect_database", lambda: connection)
    monkeypatch.setattr(importer, "validate_database", lambda c, d: "target")
    monkeypatch.setattr(importer, "build_plan", lambda *a: importer.ImportPlan(new_records=2))
    assert importer.main([str(manifest[2]), "--crosswalk-path", str(manifest[3])]) == 0
    output = capsys.readouterr().out
    assert "registros nuevos: 2" in output
    assert "Resultado: DRY-RUN correcto; no se modificó la base de datos" in output
    assert connection.rolled_back and connection.closed


def test_importer_error_after_dml_rolls_back(tmp_path, monkeypatch, capsys):
    """DML real sin commit: la excepción debe eliminar también su auditoría."""
    connection = engine.raw_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT id_usuario FROM usuario WHERE activo AND rol = 'admin' ORDER BY id_usuario LIMIT 1")
        actor = cursor.fetchone()[0]
    connection.rollback()
    path = tmp_path / "rollback.csv"
    key = "TEST_SYNC_ROLLBACK_B06"
    with path.open("w", encoding="cp1252", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=importer.EXPECTED_HEADERS)
        writer.writeheader()
        writer.writerow(dict(cve_unica=key, scncve_edo="1", scncve_mun="1", Estado="Aguascalientes",
                             Municipio="Aguascalientes", SCNNom_Nuc="PRUEBA ROLLBACK B06", tipo="EJIDO"))
    original_apply = importer.apply_plan
    def fail_after_insert(conn, plan, user_id):
        assert original_apply(conn, plan, user_id) == (1, 0)
        raise RuntimeError("Fallo simulado después del DML")
    monkeypatch.setattr(importer, "connect_database", lambda: connection)
    monkeypatch.setattr(importer, "apply_plan", fail_after_insert)
    try:
        assert importer.main([str(path), "--apply", "--expected-database", "software_pa_test",
                              "--actor-user-id", str(actor), "--report-json"]) == 1
        value = json.loads(capsys.readouterr().out)
        assert value["success"] is False and value["errors"] == 1
        assert value["mode"] == "apply"
    finally:
        if connection.is_valid:
            connection.rollback()
            connection.close()
    check = engine.raw_connection()
    try:
        with check.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM nucleo_agrario WHERE id_nucleo_fuente = %s", (key,))
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT count(*) FROM bitacora WHERE valor_nuevo::text LIKE %s", (f"%{key}%",))
            assert cursor.fetchone()[0] == 0
    finally:
        check.rollback()
        check.close()


def test_full_dataset_reproduces_in_explicit_empty_database(monkeypatch):
    """Requiere DB desechable preparada con 001–028, actor y fixture territorial."""
    target = os.getenv("RAN_REPRO_DATABASE")
    if not target:
        pytest.skip("Definir RAN_REPRO_DATABASE con una DB desechable preparada")
    assert target.startswith("software_pa_ran_repro_")
    assert target != "software_pa_test"
    monkeypatch.setenv("DB_NAME", target)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    connection = importer.connect_database()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM nucleo_agrario WHERE fuente_datos = %s", (importer.SOURCE,))
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT correo FROM usuario WHERE activo AND rol = 'admin'")
            actors = cursor.fetchall()
            assert len(actors) == 1
            email = actors[0][0]
        connection.rollback()
        script = Path(sync.__file__).with_suffix(".sh")
        command = ["bash", str(script), "--expected-database", target, "--actor-email", email]
        env = {**os.environ, "PYTHON_BIN": sys.executable}
        dry = subprocess.run(command, capture_output=True, text=True, env=env)
        assert dry.returncode == 0, dry.stderr
        assert json.loads(dry.stdout.splitlines()[0])["insertions"] == 32278
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM nucleo_agrario WHERE fuente_datos = %s", (importer.SOURCE,))
            assert cursor.fetchone()[0] == 0
        connection.rollback()
        first = subprocess.run(command + ["--apply"], capture_output=True, text=True, env=env)
        assert first.returncode == 0, first.stderr
        reports = [json.loads(line) for line in first.stdout.splitlines() if line.startswith("{")]
        assert [r.get("mode") for r in reports[:3]] == ["dry-run", "apply", "dry-run"]
        assert reports[1]["insertions"] == 32278
        assert reports[2]["insertions"] == reports[2]["updates"] == reports[2]["errors"] == 0
        assert reports[3] == dict(covered_keys=32278, active_dataset_keys=32278, extra_keys=0)
        with connection.cursor() as cursor:
            cursor.execute("SELECT btrim(id_nucleo_fuente), id_nucleo FROM nucleo_agrario WHERE fuente_datos = %s", (importer.SOURCE,))
            before = dict(cursor.fetchall())
        connection.rollback()
        second = subprocess.run(command + ["--apply"], capture_output=True, text=True, env=env)
        assert second.returncode == 0, second.stderr
        assert "CATALOGO RAN YA SINCRONIZADO" in second.stdout
        assert '"mode": "apply"' not in second.stdout
        _, _, _, audit = sync.validate_manifest(sync.DEFAULT_METADATA)
        assert set(before) == {r.source_id.strip() for r in audit.rows}
        with connection.cursor() as cursor:
            cursor.execute("SELECT btrim(id_nucleo_fuente), id_nucleo FROM nucleo_agrario WHERE fuente_datos = %s", (importer.SOURCE,))
            after_rows = cursor.fetchall()
            assert len(after_rows) == len(before) == 32278
            assert dict(after_rows) == before
    finally:
        connection.rollback()
        connection.close()
