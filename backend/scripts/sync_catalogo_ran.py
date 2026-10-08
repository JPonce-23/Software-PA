#!/usr/bin/env python3
"""Sincronización explícita RAN; el importador conserva la lógica de carga."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from psycopg2.extensions import parse_dsn

if __package__:
    from . import import_catalogo_nucleos_ran as importer
else:
    import import_catalogo_nucleos_ran as importer


DEFAULT_METADATA = (
    Path(__file__).resolve().parents[1]
    / "db/fixtures/catalogo_nucleos_ran.metadata.json"
)


def validate_manifest(path: Path):
    """Comprueba bytes y contrato del artefacto antes de conectar a PostgreSQL."""
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("Manifiesto inexistente o JSON inválido") from exc
    if not isinstance(metadata, dict):
        raise ValueError("El manifiesto debe ser un objeto")
    for key in ("name", "filename", "source", "sha256", "encoding",
                "external_identity", "crosswalk_filename", "crosswalk_sha256"):
        if not isinstance(metadata.get(key), str) or not metadata[key]:
            raise ValueError(f"Metadata inválida: {key}")
    for key in ("rows", "size_bytes", "unique_keys", "expected_entities"):
        if type(metadata.get(key)) is not int or metadata[key] <= 0:
            raise ValueError(f"Metadata inválida: {key}")
    if (metadata["source"] != importer.SOURCE
            or metadata["encoding"] != importer.ENCODING
            or metadata["external_identity"] != "cve_unica"):
        raise ValueError("Fuente, encoding o identidad no compatibles con el importador")
    columns = metadata.get("columns")
    if (not isinstance(columns, list)
            or len(columns) != len(importer.EXPECTED_HEADERS)
            or any(not isinstance(c, str) for c in columns)
            or set(columns) != set(importer.EXPECTED_HEADERS)):
        raise ValueError("Columnas inválidas en metadata")
    types = metadata.get("expected_types")
    if (not isinstance(types, dict) or set(types) != set(importer.TYPE_CODES)
            or any(type(n) is not int or n <= 0 for n in types.values())
            or sum(types.values()) != metadata["rows"]
            or metadata["unique_keys"] != metadata["rows"]):
        raise ValueError("Conteos inválidos en metadata")
    for key in ("sha256", "crosswalk_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", metadata[key]):
            raise ValueError(f"Checksum inválido: {key}")
    paths = []
    for filename_key, hash_key in (("filename", "sha256"),
                                   ("crosswalk_filename", "crosswalk_sha256")):
        name = metadata[filename_key]
        if name in (".", "..") or Path(name).name != name:
            raise ValueError("Los artefactos deben estar junto al manifiesto")
        artifact = path.resolve().parent / name
        if not artifact.is_file():
            raise ValueError(f"Archivo inexistente: {name}")
        if importer._sha256(artifact) != metadata[hash_key]:
            raise ValueError(f"Checksum incorrecto: {name}")
        paths.append(artifact)
    dataset, crosswalk_path = paths
    if dataset.stat().st_size != metadata["size_bytes"]:
        raise ValueError("Tamaño incorrecto del dataset")
    with dataset.open(encoding=metadata["encoding"], newline="") as source:
        if next(csv.reader(source), None) != columns:
            raise ValueError("Encabezados distintos del manifiesto")
    audit = importer.audit_file(dataset)
    crosswalk = importer.audit_crosswalk(crosswalk_path)
    if audit.errors or crosswalk.errors:
        raise ValueError("Artefactos inválidos: " + "; ".join(audit.errors + crosswalk.errors))
    actual = (audit.total_rows, audit.unique_keys, audit.states,
              audit.ejidos, audit.comunidades)
    expected = (metadata["rows"], metadata["unique_keys"], metadata["expected_entities"],
                types["EJIDO"], types["COMUNIDAD"])
    if actual != expected:
        raise ValueError(f"Conteos distintos del manifiesto: {actual}")
    return metadata, dataset, crosswalk_path, audit


def validate_connection_configuration() -> None:
    """Evita que DATABASE_URL silencie una configuración DB_* contradictoria."""
    url = os.getenv("DATABASE_URL")
    if not url:
        return
    try:
        parsed = parse_dsn(url)
    except Exception as exc:
        raise ValueError("DATABASE_URL inválida") from exc
    defaults = {"host": os.getenv("PGHOST", ""), "port": os.getenv("PGPORT", "5432")}
    for variable, parameter in (("DB_NAME", "dbname"), ("DB_HOST", "host"),
                                ("DB_PORT", "port"), ("DB_RUNTIME_USER", "user"),
                                ("DB_RUNTIME_PASSWORD", "password")):
        configured = os.getenv(variable)
        if configured is not None and configured != parsed.get(parameter, defaults.get(parameter)):
            raise ValueError(f"Configuración contradictoria: DATABASE_URL y {variable}")


def preflight_database(expected: str, actor_email: str | None) -> tuple[str, int | None]:
    validate_connection_configuration()
    connection = importer.connect_database()
    try:
        connection.set_session(readonly=True)
        database = importer.validate_database(connection, expected)
        actor_id = None
        if actor_email is not None:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id_usuario, activo, rol FROM public.usuario "
                    "WHERE lower(btrim(correo)) = lower(%s)",
                    (actor_email.strip(" "),),
                )
                users = cursor.fetchall()
            if len(users) != 1 or not users[0][1] or users[0][2] != "admin":
                raise ValueError("El actor debe ser exactamente un administrador activo")
            actor_id = users[0][0]
        return database, actor_id
    finally:
        connection.rollback()
        connection.close()


def run_importer(dataset: Path, crosswalk: Path, expected: str,
                 metadata: dict, *, actor_id: int | None = None) -> dict:
    command = [sys.executable, str(Path(importer.__file__).resolve()), str(dataset),
               "--crosswalk-path", str(crosswalk), "--expected-database", expected,
               "--report-json"]
    if actor_id is None:
        command.append("--dry-run")
    else:
        command.extend(["--apply", "--actor-user-id", str(actor_id)])
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    try:
        report = json.loads(result.stdout)
    except ValueError as exc:
        raise ValueError("El importador no produjo un reporte JSON válido") from exc
    if isinstance(report, dict):
        print(json.dumps(report, ensure_ascii=False))
    if (not isinstance(report, dict) or result.returncode != 0
            or report.get("success") is not True or report.get("errors") != 0
            or report.get("unresolved_crosswalk") != 0):
        raise ValueError("El importador falló o encontró errores/crosswalk sin resolver")
    if (report.get("database") != expected
            or report.get("dataset_sha256") != metadata["sha256"]
            or report.get("rows") != metadata["rows"]
            or report.get("mode") != ("apply" if actor_id is not None else "dry-run")):
        raise ValueError("Reporte del importador incompatible con el destino/artefacto")
    counts = [report.get(k) for k in ("insertions", "updates", "unchanged")]
    if any(type(n) is not int or n < 0 for n in counts) or sum(counts) != metadata["rows"]:
        raise ValueError("Conteos inválidos en reporte del importador")
    return report


def verify_coverage(expected: str, audit) -> dict:
    connection = importer.connect_database()
    try:
        connection.set_session(readonly=True)
        importer.validate_database(connection, expected)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT btrim(id_nucleo_fuente), activo FROM public.nucleo_agrario "
                "WHERE fuente_datos = %s", (importer.SOURCE,),
            )
            rows = cursor.fetchall()
        keys = {row.source_id.strip() for row in audit.rows}
        stored = {row[0] for row in rows}
        if not keys.issubset(stored):
            raise ValueError("La cobertura final del dataset está incompleta")
        return {"covered_keys": len(keys),
                "active_dataset_keys": len({key for key, active in rows if active} & keys),
                "extra_keys": len(stored - keys)}
    finally:
        connection.rollback()
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--actor-email", help="Administrador activo del destino; obligatorio con --apply")
    parser.add_argument("--apply", action="store_true", help="Autoriza altas/cambios después del dry-run")
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA,
                        help="Manifiesto aprobado (por defecto el incluido en el repositorio)")
    args = parser.parse_args(argv)
    if not args.expected_database.strip() or (args.apply and not (args.actor_email or "").strip()):
        parser.error("Se requiere destino no vacío y --actor-email con --apply")
    try:
        metadata, dataset, crosswalk, audit = validate_manifest(args.metadata)
        _, actor_id = preflight_database(args.expected_database, args.actor_email)
        plan = run_importer(dataset, crosswalk, args.expected_database, metadata)
        if plan["insertions"] == plan["updates"] == 0:
            print(json.dumps(verify_coverage(args.expected_database, audit)))
            print("CATALOGO RAN YA SINCRONIZADO")
            return 0
        if not args.apply:
            print("DRY-RUN: hay altas/cambios pendientes; no se modificó la base. Use --apply para autorizar.")
            return 0
        # Revalidar artefactos y actor antes de la escritura; apply vuelve a planificar bajo lock.
        if validate_manifest(args.metadata)[0] != metadata:
            raise ValueError("El manifiesto cambió durante la sincronización")
        _, current_actor = preflight_database(args.expected_database, args.actor_email)
        if current_actor != actor_id:
            raise ValueError("El actor cambió durante la sincronización")
        run_importer(dataset, crosswalk, args.expected_database, metadata, actor_id=actor_id)
        validate_manifest(args.metadata)
        final = run_importer(dataset, crosswalk, args.expected_database, metadata)
        if final["insertions"] or final["updates"]:
            raise ValueError("El segundo dry-run todavía encuentra cambios")
        print(json.dumps(verify_coverage(args.expected_database, audit)))
        print("CATALOGO RAN SINCRONIZADO")
        return 0
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        # Los errores de conexión pueden contener datos sensibles: sólo mostrar la clase.
        print(f"ERROR: sincronización abortada ({type(exc).__name__})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
