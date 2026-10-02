#!/usr/bin/env python3
"""Valida y carga de forma reproducible el catálogo nacional RAN/PHINA."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values


SOURCE = "RAN_PHINA_CATALOGO_NUCLEOS"
SCOPE = "nacional"
ENCODING = "cp1252"
EXPECTED_HEADERS = (
    "cve_unica",
    "scncve_edo",
    "scncve_mun",
    "Municipio",
    "SCNNom_Nuc",
    "Estado",
    "tipo",
)
TYPE_CODES = {"EJIDO": "ejido", "COMUNIDAD": "comunidad"}
CROSSWALK_HEADERS = ("scncve_edo", "scncve_mun", "clave_inegi", "motivo")
DEFAULT_CROSSWALK_PATH = (
    Path(__file__).resolve().parents[1]
    / "db"
    / "fixtures"
    / "ran_municipio_inegi_crosswalk.csv"
)


@dataclass(frozen=True)
class RanRow:
    line_number: int
    source_id: str
    source_state_id: str
    source_municipality_id: str
    municipality_key: str
    name: str
    source_type: str


@dataclass
class FileAudit:
    path: Path
    sha256: str
    rows: list[RanRow] = field(default_factory=list)
    total_rows: int = 0
    duplicate_keys: int = 0
    unknown_types: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def unique_keys(self) -> int:
        return len({row.source_id.strip() for row in self.rows})

    @property
    def ejidos(self) -> int:
        return sum(row.source_type == "EJIDO" for row in self.rows)

    @property
    def comunidades(self) -> int:
        return sum(row.source_type == "COMUNIDAD" for row in self.rows)

    @property
    def states(self) -> int:
        return len({row.municipality_key[:2] for row in self.rows})


@dataclass(frozen=True)
class PreparedRow:
    source_id: str
    source_state_id: str
    source_municipality_id: str
    municipality_id: int
    name: str
    tenure_type_id: int


@dataclass(frozen=True)
class CrosswalkEntry:
    source_state_id: str
    source_municipality_id: str
    municipality_key: str
    reason: str
    line_number: int


@dataclass
class CrosswalkAudit:
    path: Path
    entries: dict[tuple[str, str], CrosswalkEntry] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass
class ImportPlan:
    prepared_rows: list[PreparedRow] = field(default_factory=list)
    municipalities_found: int = 0
    missing_municipalities: list[str] = field(default_factory=list)
    new_records: int = 0
    records_to_update: int = 0
    ran_combinations: int = 0
    crosswalk_combinations: int = 0
    crosswalk_rows: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _municipality_key(state_id: str, municipality_id: str) -> str | None:
    state = state_id.strip()
    municipality = municipality_id.strip()
    if (
        not state.isascii()
        or not state.isdigit()
        or len(state) > 2
        or not municipality.isascii()
        or not municipality.isdigit()
        or len(municipality) > 3
    ):
        return None
    return state.zfill(2) + municipality.zfill(3)


def _source_pair(state_id: str, municipality_id: str) -> tuple[str, str] | None:
    if _municipality_key(state_id, municipality_id) is None:
        return None
    return str(int(state_id.strip())), str(int(municipality_id.strip()))


def audit_crosswalk(path: Path = DEFAULT_CROSSWALK_PATH) -> CrosswalkAudit:
    path = path.resolve()
    audit = CrosswalkAudit(path=path)
    if not path.is_file():
        audit.errors.append(f"El crosswalk no existe o no es un archivo: {path}")
        return audit

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            headers = reader.fieldnames
            if headers is None:
                audit.errors.append("El crosswalk no contiene encabezados")
                return audit
            if len(headers) != len(set(headers)):
                audit.errors.append("El crosswalk contiene encabezados duplicados")
                return audit
            missing = sorted(set(CROSSWALK_HEADERS) - set(headers))
            unexpected = sorted(set(headers) - set(CROSSWALK_HEADERS))
            if missing:
                audit.errors.append(
                    "Encabezados faltantes en crosswalk: " + ", ".join(missing)
                )
            if unexpected:
                audit.errors.append(
                    "Encabezados no esperados en crosswalk: "
                    + ", ".join(unexpected)
                )
            if missing or unexpected:
                return audit

            for line_number, raw in enumerate(reader, start=2):
                values = {
                    header: (raw.get(header) or "").strip()
                    for header in CROSSWALK_HEADERS
                }
                empty = [header for header, value in values.items() if not value]
                if empty:
                    audit.errors.append(
                        f"Crosswalk línea {line_number}: campos vacíos: "
                        + ", ".join(empty)
                    )
                    continue
                pair = _source_pair(
                    values["scncve_edo"], values["scncve_mun"]
                )
                if pair is None:
                    audit.errors.append(
                        f"Crosswalk línea {line_number}: par RAN inválido"
                    )
                    continue
                if not (
                    values["clave_inegi"].isascii()
                    and values["clave_inegi"].isdigit()
                    and len(values["clave_inegi"]) == 5
                ):
                    audit.errors.append(
                        f"Crosswalk línea {line_number}: clave_inegi inválida"
                    )
                    continue
                if pair in audit.entries:
                    previous = audit.entries[pair]
                    audit.errors.append(
                        "Crosswalk líneas "
                        f"{previous.line_number} y {line_number}: par RAN duplicado "
                        f"{pair[0]}/{pair[1]}"
                    )
                    continue
                audit.entries[pair] = CrosswalkEntry(
                    source_state_id=values["scncve_edo"],
                    source_municipality_id=values["scncve_mun"],
                    municipality_key=values["clave_inegi"],
                    reason=values["motivo"],
                    line_number=line_number,
                )
    except UnicodeError as exc:
        audit.errors.append(f"No fue posible leer el crosswalk como UTF-8: {exc}")
    return audit


def audit_file(path: Path) -> FileAudit:
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"El CSV no existe o no es un archivo: {path}")

    audit = FileAudit(path=path, sha256=_sha256(path))
    seen: Counter[str] = Counter()
    try:
        with path.open("r", encoding=ENCODING, newline="") as source:
            reader = csv.DictReader(source)
            headers = reader.fieldnames
            if headers is None:
                audit.errors.append("El archivo no contiene encabezados")
                return audit
            if len(headers) != len(set(headers)):
                audit.errors.append("El CSV contiene encabezados duplicados")
                return audit
            missing = sorted(set(EXPECTED_HEADERS) - set(headers))
            unexpected = sorted(set(headers) - set(EXPECTED_HEADERS))
            if missing:
                audit.errors.append("Encabezados faltantes: " + ", ".join(missing))
            if unexpected:
                audit.errors.append(
                    "Encabezados no esperados: " + ", ".join(unexpected)
                )
            if missing or unexpected:
                return audit

            for line_number, raw in enumerate(reader, start=2):
                audit.total_rows += 1
                row_errors: list[str] = []
                if None in raw:
                    row_errors.append("columnas adicionales sin encabezado")

                source_id = raw.get("cve_unica") or ""
                source_state_id = raw.get("scncve_edo") or ""
                source_municipality_id = raw.get("scncve_mun") or ""
                name = (raw.get("SCNNom_Nuc") or "").strip()
                source_type = (raw.get("tipo") or "").strip()
                identity = source_id.strip()

                if not identity:
                    row_errors.append("cve_unica vacía")
                elif len(source_id) > 120:
                    row_errors.append("cve_unica excede 120 caracteres")
                else:
                    seen[identity] += 1

                municipality_key = _municipality_key(
                    source_state_id, source_municipality_id
                )
                if municipality_key is None:
                    row_errors.append("scncve_edo/scncve_mun no forman clave INEGI")
                if not name:
                    row_errors.append("SCNNom_Nuc vacío")
                elif len(name) > 300:
                    row_errors.append("SCNNom_Nuc excede 300 caracteres")
                if source_type not in TYPE_CODES:
                    audit.unknown_types += 1
                    row_errors.append(f"tipo desconocido: {source_type or '(vacío)'}")
                if not source_state_id or len(source_state_id) > 120:
                    row_errors.append("scncve_edo vacío o demasiado largo")
                if not source_municipality_id or len(source_municipality_id) > 120:
                    row_errors.append("scncve_mun vacío o demasiado largo")

                if row_errors:
                    audit.errors.append(
                        f"Línea {line_number}: " + "; ".join(row_errors)
                    )
                    continue

                audit.rows.append(
                    RanRow(
                        line_number=line_number,
                        source_id=source_id,
                        source_state_id=source_state_id,
                        source_municipality_id=source_municipality_id,
                        municipality_key=municipality_key,
                        name=name,
                        source_type=source_type,
                    )
                )
    except UnicodeError as exc:
        audit.errors.append(f"No fue posible leer el archivo como {ENCODING}: {exc}")
        return audit

    duplicates = sorted(key for key, count in seen.items() if count > 1)
    audit.duplicate_keys = len(duplicates)
    if duplicates:
        preview = ", ".join(duplicates[:10])
        suffix = " ..." if len(duplicates) > 10 else ""
        audit.errors.append(
            f"cve_unica duplicadas ({len(duplicates)}): {preview}{suffix}"
        )
    if audit.total_rows == 0:
        audit.errors.append("El CSV no contiene filas de datos")
    return audit


def connect_database():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)

    required = {
        "user": os.getenv("DB_RUNTIME_USER"),
        "password": os.getenv("DB_RUNTIME_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "dbname": os.getenv("DB_NAME"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Configuración PostgreSQL incompleta; faltan: " + ", ".join(missing)
        )
    return psycopg2.connect(**required)


def validate_database(connection, expected_database: str | None) -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        current_database = cursor.fetchone()[0]
        if expected_database and current_database != expected_database:
            raise RuntimeError(
                f"Base inesperada: {current_database}; se esperaba {expected_database}"
            )
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM public.schema_migrations
                WHERE version = '019' AND nombre = 'catalogo_nucleos_ran'
            )
            """
        )
        if not cursor.fetchone()[0]:
            raise RuntimeError("La migración 019_catalogo_nucleos_ran no está aplicada")
    return current_database


def build_plan(
    connection, audit: FileAudit, crosswalk: CrosswalkAudit | None = None
) -> ImportPlan:
    plan = ImportPlan()
    crosswalk = crosswalk or audit_crosswalk()
    if crosswalk.errors:
        plan.errors.extend(crosswalk.errors)
        return plan

    source_combinations = {
        _source_pair(row.source_state_id, row.source_municipality_id)
        for row in audit.rows
    }
    source_combinations.discard(None)
    plan.ran_combinations = len(source_combinations)
    resolved_keys: dict[tuple[str, str], str] = {}
    for pair in source_combinations:
        entry = crosswalk.entries.get(pair)
        if entry is not None:
            resolved_keys[pair] = entry.municipality_key
        else:
            resolved_keys[pair] = pair[0].zfill(2) + pair[1].zfill(3)

    municipality_keys = sorted(
        set(resolved_keys.values())
        | {entry.municipality_key for entry in crosswalk.entries.values()}
        | {
            pair[0].zfill(2) + pair[1].zfill(3)
            for pair in crosswalk.entries
        }
    )
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT btrim(clave_inegi), id_municipio
              FROM public.municipio
             WHERE activo AND btrim(clave_inegi) = ANY(%s)
            """,
            (municipality_keys,),
        )
        municipalities = dict(cursor.fetchall())
        for pair, entry in crosswalk.entries.items():
            if entry.municipality_key not in municipalities:
                plan.errors.append(
                    f"Crosswalk {pair[0]}/{pair[1]} apunta a clave_inegi "
                    f"inexistente o inactiva: {entry.municipality_key}"
                )

        for pair, destination in resolved_keys.items():
            direct_key = pair[0].zfill(2) + pair[1].zfill(3)
            entry = crosswalk.entries.get(pair)
            if (
                entry is not None
                and direct_key in municipalities
                and destination != direct_key
            ):
                plan.warnings.append(
                    f"Crosswalk {pair[0]}/{pair[1]} usa {destination}, aunque "
                    f"la coincidencia directa {direct_key} también existe"
                )
            if destination not in municipalities:
                plan.missing_municipalities.append(
                    f"{pair[0]}/{pair[1]} -> {destination}"
                )

        plan.municipalities_found = sum(
            destination in municipalities for destination in resolved_keys.values()
        )
        used_crosswalk_pairs = set(source_combinations) & set(crosswalk.entries)
        plan.crosswalk_combinations = len(used_crosswalk_pairs)
        plan.crosswalk_rows = sum(
            _source_pair(row.source_state_id, row.source_municipality_id)
            in used_crosswalk_pairs
            for row in audit.rows
        )

        cursor.execute(
            """
            SELECT codigo, id_catalogo_opcion
              FROM public.catalogo_operativo
             WHERE tipo_catalogo = 'tipo_tenencia'
               AND codigo = ANY(%s)
               AND activo
            """,
            (list(TYPE_CODES.values()),),
        )
        tenure_types = dict(cursor.fetchall())
        missing_types = sorted(set(TYPE_CODES.values()) - set(tenure_types))
        if missing_types:
            plan.errors.append(
                "Faltan tipos de tenencia activos: " + ", ".join(missing_types)
            )

        cursor.execute(
            """
            SELECT btrim(id_nucleo_fuente), id_nucleo, id_municipio,
                   nombre_nucleo, id_tipo_tenencia, fuente_datos,
                   id_entidad_fuente, id_municipio_fuente,
                   alcance_identidad_fuente
              FROM public.nucleo_agrario
             WHERE lower(btrim(fuente_datos)) = lower(%s)
               AND NULLIF(btrim(id_nucleo_fuente), '') IS NOT NULL
            """,
            (SOURCE,),
        )
        existing = {row[0]: row[1:] for row in cursor.fetchall()}

    if plan.errors or plan.missing_municipalities or missing_types:
        return plan

    for row in audit.rows:
        pair = _source_pair(row.source_state_id, row.source_municipality_id)
        prepared = PreparedRow(
            source_id=row.source_id,
            source_state_id=row.source_state_id,
            source_municipality_id=row.source_municipality_id,
            municipality_id=municipalities[resolved_keys[pair]],
            name=row.name,
            tenure_type_id=tenure_types[TYPE_CODES[row.source_type]],
        )
        plan.prepared_rows.append(prepared)
        prior = existing.get(row.source_id.strip())
        if prior is None:
            plan.new_records += 1
            continue
        (
            _internal_id,
            municipality_id,
            name,
            tenure_type_id,
            source,
            source_state_id,
            source_municipality_id,
            scope,
        ) = prior
        desired = (
            prepared.municipality_id,
            prepared.name,
            prepared.tenure_type_id,
            SOURCE,
            prepared.source_state_id,
            prepared.source_municipality_id,
            SCOPE,
        )
        current = (
            municipality_id,
            name,
            tenure_type_id,
            source,
            source_state_id,
            source_municipality_id,
            scope,
        )
        if current != desired or prior is None:
            plan.records_to_update += 1
    return plan


def acquire_import_lock(connection) -> None:
    """Serializa el plan y su aplicación para evitar decisiones obsoletas."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            ("software-pa:import:catalogo-nucleos-ran",),
        )
        cursor.execute("LOCK TABLE public.nucleo_agrario IN SHARE ROW EXCLUSIVE MODE")


def apply_plan(connection, plan: ImportPlan, actor_user_id: int) -> tuple[int, int]:
    if plan.errors or plan.missing_municipalities:
        raise RuntimeError("No se puede aplicar un plan con errores")
    values = [
        (
            row.source_id,
            row.source_state_id,
            row.source_municipality_id,
            row.municipality_id,
            row.name,
            row.tenure_type_id,
        )
        for row in plan.prepared_rows
    ]
    with connection.cursor() as cursor:
        acquire_import_lock(connection)
        cursor.execute("DROP TABLE IF EXISTS pg_temp.tmp_catalogo_nucleos_ran")
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM public.usuario
                 WHERE id_usuario = %s AND activo
            )
            """,
            (actor_user_id,),
        )
        if not cursor.fetchone()[0]:
            raise RuntimeError("El actor de importación no existe o está inactivo")
        cursor.execute(
            sql.SQL('SET LOCAL "app.current_user_id" = {}').format(
                sql.Literal(str(actor_user_id))
            )
        )
        cursor.execute(
            """
            CREATE TEMP TABLE tmp_catalogo_nucleos_ran (
                id_nucleo_fuente text NOT NULL,
                id_entidad_fuente text NOT NULL,
                id_municipio_fuente text NOT NULL,
                id_municipio integer NOT NULL,
                nombre_nucleo text NOT NULL,
                id_tipo_tenencia bigint NOT NULL
            ) ON COMMIT DROP
            """
        )
        execute_values(
            cursor,
            """
            INSERT INTO tmp_catalogo_nucleos_ran (
                id_nucleo_fuente, id_entidad_fuente, id_municipio_fuente,
                id_municipio, nombre_nucleo, id_tipo_tenencia
            ) VALUES %s
            """,
            values,
            page_size=1000,
        )
        cursor.execute(
            """
            UPDATE public.nucleo_agrario AS target
               SET id_municipio = source.id_municipio,
                   nombre_nucleo = source.nombre_nucleo,
                   id_tipo_tenencia = source.id_tipo_tenencia,
                   fuente_datos = %s,
                   id_entidad_fuente = source.id_entidad_fuente,
                   id_municipio_fuente = source.id_municipio_fuente,
                   id_nucleo_fuente = source.id_nucleo_fuente,
                   alcance_identidad_fuente = %s,
                   actualizado_en = now(),
                   actualizado_por = %s
              FROM tmp_catalogo_nucleos_ran AS source
             WHERE lower(btrim(target.fuente_datos)) = lower(%s)
               AND btrim(target.id_nucleo_fuente) = btrim(source.id_nucleo_fuente)
               AND ROW(
                    target.id_municipio, target.nombre_nucleo,
                    target.id_tipo_tenencia, target.fuente_datos,
                    target.id_entidad_fuente, target.id_municipio_fuente,
                    target.id_nucleo_fuente, target.alcance_identidad_fuente
               ) IS DISTINCT FROM ROW(
                    source.id_municipio, source.nombre_nucleo,
                    source.id_tipo_tenencia, %s,
                    source.id_entidad_fuente, source.id_municipio_fuente,
                    source.id_nucleo_fuente, %s
               )
            """,
            (SOURCE, SCOPE, actor_user_id, SOURCE, SOURCE, SCOPE),
        )
        updated = cursor.rowcount
        cursor.execute(
            """
            INSERT INTO public.nucleo_agrario (
                id_municipio, nombre_nucleo, id_tipo_tenencia,
                fuente_datos, id_entidad_fuente, id_municipio_fuente,
                id_nucleo_fuente, alcance_identidad_fuente,
                creado_por
            )
            SELECT source.id_municipio, source.nombre_nucleo,
                   source.id_tipo_tenencia, %s,
                   source.id_entidad_fuente, source.id_municipio_fuente,
                   source.id_nucleo_fuente, %s, %s
              FROM tmp_catalogo_nucleos_ran AS source
             WHERE NOT EXISTS (
                SELECT 1
                  FROM public.nucleo_agrario AS target
                 WHERE lower(btrim(target.fuente_datos)) = lower(%s)
                   AND btrim(target.id_nucleo_fuente)
                       = btrim(source.id_nucleo_fuente)
             )
            """,
            (SOURCE, SCOPE, actor_user_id, SOURCE),
        )
        inserted = cursor.rowcount
    return inserted, updated


def print_report(
    audit: FileAudit,
    crosswalk: CrosswalkAudit,
    plan: ImportPlan | None,
) -> None:
    plan = plan or ImportPlan()
    print(f"archivo: {audit.path}")
    print(f"SHA-256: {audit.sha256}")
    print(f"filas: {audit.total_rows}")
    print(f"claves únicas: {audit.unique_keys}")
    print(f"Ejidos: {audit.ejidos}")
    print(f"Comunidades: {audit.comunidades}")
    print(f"entidades: {audit.states}")
    print(f"combinaciones territoriales RAN: {plan.ran_combinations}")
    print(f"municipios encontrados: {plan.municipalities_found}")
    print(f"municipios sin correspondencia: {len(plan.missing_municipalities)}")
    if plan.missing_municipalities:
        print("  " + ", ".join(plan.missing_municipalities))
    print(f"resoluciones mediante crosswalk: {plan.crosswalk_combinations}")
    print(f"filas resueltas mediante crosswalk: {plan.crosswalk_rows}")
    print(f"claves duplicadas: {audit.duplicate_keys}")
    print(f"tipos desconocidos: {audit.unknown_types}")
    print(f"registros nuevos: {plan.new_records}")
    print(f"registros que serían actualizados: {plan.records_to_update}")
    errors = [*audit.errors, *crosswalk.errors, *plan.errors]
    print(f"errores: {len(errors)}")
    for error in errors:
        print(f"  - {error}")
    print(f"advertencias: {len(plan.warnings)}")
    for warning in plan.warnings:
        print(f"  - {warning}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audita o importa el catálogo nacional RAN/PHINA"
    )
    parser.add_argument("csv_path", type=Path, help="Ruta al CSV oficial")
    parser.add_argument(
        "--crosswalk-path",
        type=Path,
        default=DEFAULT_CROSSWALK_PATH,
        help="Crosswalk explícito RAN a INEGI",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Sólo valida (predeterminado)")
    mode.add_argument("--apply", action="store_true", help="Aplica INSERT/UPDATE")
    parser.add_argument(
        "--expected-database",
        help="Nombre exacto esperado; es obligatorio con --apply",
    )
    parser.add_argument(
        "--actor-user-id",
        type=int,
        default=None,
        help="Usuario activo responsable; también IMPORT_ACTOR_USER_ID",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.apply and not args.expected_database:
        print("ERROR: --apply requiere --expected-database", file=sys.stderr)
        return 2
    actor_user_id = args.actor_user_id
    if actor_user_id is None and os.getenv("IMPORT_ACTOR_USER_ID"):
        try:
            actor_user_id = int(os.environ["IMPORT_ACTOR_USER_ID"])
        except ValueError:
            print("ERROR: IMPORT_ACTOR_USER_ID debe ser entero", file=sys.stderr)
            return 2
    if args.apply and actor_user_id is None:
        print("ERROR: --apply requiere --actor-user-id", file=sys.stderr)
        return 2

    try:
        audit = audit_file(args.csv_path)
        crosswalk = audit_crosswalk(args.crosswalk_path)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    connection = None
    plan = None
    try:
        if not audit.errors and not crosswalk.errors:
            connection = connect_database()
            current_database = validate_database(connection, args.expected_database)
            if args.apply:
                acquire_import_lock(connection)
            plan = build_plan(connection, audit, crosswalk)
            print(f"base de datos: {current_database}")
        print_report(audit, crosswalk, plan)

        if (
            audit.errors
            or crosswalk.errors
            or plan is None
            or plan.errors
            or plan.missing_municipalities
        ):
            if connection is not None:
                connection.rollback()
            print("Resultado: ABORTADO; no se modificó la base de datos")
            return 1
        if not args.apply:
            connection.rollback()
            print("Resultado: DRY-RUN correcto; no se modificó la base de datos")
            return 0

        inserted, updated = apply_plan(connection, plan, actor_user_id)
        connection.commit()
        print(f"insertados: {inserted}")
        print(f"actualizados: {updated}")
        print("Resultado: APPLY confirmado")
        return 0
    except Exception as exc:
        if connection is not None:
            connection.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Resultado: ABORTADO; transacción revertida")
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
