"""Contrato del importador seguro del catálogo nacional RAN/PHINA."""

import csv

from app.database import engine
from scripts import import_catalogo_nucleos_ran as importer


def write_csv(path, rows):
    with path.open("w", encoding="cp1252", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=importer.EXPECTED_HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def write_crosswalk(path, rows):
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=importer.CROSSWALK_HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def crosswalk_row(**overrides):
    value = {
        "scncve_edo": "12",
        "scncve_mun": "86",
        "clave_inegi": "12085",
        "motivo": "Excepción territorial de prueba",
    }
    value.update(overrides)
    return value


def row(**overrides):
    value = {
        "cve_unica": "01001E1104030001_",
        "scncve_edo": "1",
        "scncve_mun": "1",
        "Municipio": "Aguascalientes",
        "SCNNom_Nuc": "  Ejido San José  ",
        "Estado": "Aguascalientes",
        "tipo": "EJIDO",
    }
    value.update(overrides)
    return value


def test_audit_reads_cp1252_preserves_key_and_only_trims_name(tmp_path):
    path = tmp_path / "ran.csv"
    write_csv(
        path,
        [
            row(),
            row(
                cve_unica="04006ETEMPO04027_",
                SCNNom_Nuc="  Comunidad Peñón  ",
                tipo="COMUNIDAD",
            ),
        ],
    )

    audit = importer.audit_file(path)

    assert audit.errors == []
    assert audit.total_rows == 2
    assert audit.unique_keys == 2
    assert audit.ejidos == 1
    assert audit.comunidades == 1
    assert audit.states == 1
    assert audit.rows[0].source_id == "01001E1104030001_"
    assert audit.rows[0].municipality_key == "01001"
    assert audit.rows[1].name == "Comunidad Peñón"
    assert len(audit.sha256) == 64


def test_audit_rejects_duplicate_keys_and_unknown_types(tmp_path):
    path = tmp_path / "ran_invalido.csv"
    write_csv(
        path,
        [
            row(cve_unica="CLAVE_REPETIDA"),
            row(cve_unica=" CLAVE_REPETIDA ", tipo="PROPIEDAD PRIVADA"),
        ],
    )

    audit = importer.audit_file(path)

    assert audit.duplicate_keys == 1
    assert audit.unknown_types == 1
    assert any("cve_unica duplicadas" in error for error in audit.errors)
    assert any("tipo desconocido" in error for error in audit.errors)


def test_apply_is_transactional_and_idempotent(tmp_path):
    connection = engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT btrim(m.clave_inegi), u.id_usuario
                  FROM municipio m
                  CROSS JOIN LATERAL (
                    SELECT id_usuario FROM usuario
                     WHERE activo ORDER BY id_usuario LIMIT 1
                  ) u
                 WHERE m.activo
                 ORDER BY m.id_municipio
                 LIMIT 1
                """
            )
            municipality_key, actor_id = cursor.fetchone()

        path = tmp_path / "ran_integracion.csv"
        write_csv(
            path,
            [
                row(
                    cve_unica="CONTRATO_IMPORTADOR_019_E",
                    scncve_edo=municipality_key[:2],
                    scncve_mun=municipality_key[2:],
                    SCNNom_Nuc="NÚCLEO CONTRATO IMPORTADOR",
                    tipo="EJIDO",
                ),
                row(
                    cve_unica="CONTRATO_IMPORTADOR_019_C",
                    scncve_edo=municipality_key[:2],
                    scncve_mun=municipality_key[2:],
                    SCNNom_Nuc="NÚCLEO CONTRATO IMPORTADOR",
                    tipo="COMUNIDAD",
                ),
            ],
        )
        audit = importer.audit_file(path)
        assert audit.errors == []
        assert importer.validate_database(connection, "software_pa_test")

        importer.acquire_import_lock(connection)
        first_plan = importer.build_plan(connection, audit)
        assert first_plan.missing_municipalities == []
        assert first_plan.errors == []
        assert first_plan.new_records == 2
        assert first_plan.records_to_update == 0
        assert importer.apply_plan(connection, first_plan, actor_id) == (2, 0)

        second_plan = importer.build_plan(connection, audit)
        assert second_plan.new_records == 0
        assert second_plan.records_to_update == 0
        assert importer.apply_plan(connection, second_plan, actor_id) == (0, 0)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT count(*)
                  FROM nucleo_agrario
                 WHERE fuente_datos = %s
                   AND id_nucleo_fuente IN (
                     'CONTRATO_IMPORTADOR_019_E',
                     'CONTRATO_IMPORTADOR_019_C'
                   )
                """,
                (importer.SOURCE,),
            )
            assert cursor.fetchone()[0] == 2
    finally:
        connection.rollback()
        connection.close()


def test_crosswalk_12_86_preserves_source_and_resolves_to_12085(tmp_path):
    path = tmp_path / "ran_crosswalk.csv"
    write_csv(
        path,
        [
            row(
                cve_unica="1214109621823659_",
                scncve_edo="12",
                scncve_mun="86",
                Estado="GUERRERO",
                Municipio="SAN NICOLAS",
                SCNNom_Nuc="SAN NICOLAS",
            )
        ],
    )
    audit = importer.audit_file(path)
    crosswalk = importer.audit_crosswalk()
    assert crosswalk.errors == []

    connection = engine.raw_connection()
    try:
        plan = importer.build_plan(connection, audit, crosswalk)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id_municipio FROM municipio WHERE btrim(clave_inegi) = '12085'"
            )
            municipality_id_12085 = cursor.fetchone()[0]

        assert plan.errors == []
        assert plan.missing_municipalities == []
        assert plan.crosswalk_combinations == 1
        assert plan.crosswalk_rows == 1
        assert plan.prepared_rows[0].source_state_id == "12"
        assert plan.prepared_rows[0].source_municipality_id == "86"
        assert plan.prepared_rows[0].municipality_id == municipality_id_12085
    finally:
        connection.rollback()
        connection.close()


def test_unknown_code_without_direct_match_or_crosswalk_aborts(tmp_path):
    path = tmp_path / "ran_desconocido.csv"
    write_csv(path, [row(scncve_edo="99", scncve_mun="999")])
    audit = importer.audit_file(path)

    connection = engine.raw_connection()
    try:
        plan = importer.build_plan(connection, audit, importer.audit_crosswalk())
        assert plan.municipalities_found == 0
        assert plan.missing_municipalities == ["99/999 -> 99999"]
        assert plan.prepared_rows == []
    finally:
        connection.rollback()
        connection.close()


def test_crosswalk_destination_must_exist(tmp_path):
    csv_path = tmp_path / "ran.csv"
    crosswalk_path = tmp_path / "crosswalk.csv"
    write_csv(csv_path, [row(scncve_edo="12", scncve_mun="86")])
    write_crosswalk(
        crosswalk_path,
        [crosswalk_row(clave_inegi="99999")],
    )

    connection = engine.raw_connection()
    try:
        plan = importer.build_plan(
            connection,
            importer.audit_file(csv_path),
            importer.audit_crosswalk(crosswalk_path),
        )
        assert any("clave_inegi inexistente o inactiva: 99999" in e for e in plan.errors)
        assert plan.prepared_rows == []
    finally:
        connection.rollback()
        connection.close()


def test_crosswalk_rejects_duplicate_ran_pair(tmp_path):
    path = tmp_path / "crosswalk_duplicado.csv"
    write_crosswalk(
        path,
        [
            crosswalk_row(),
            crosswalk_row(scncve_edo="012", motivo="Duplicado"),
        ],
    )

    audit = importer.audit_crosswalk(path)

    assert any("par RAN inválido" in error for error in audit.errors)

    write_crosswalk(
        path,
        [crosswalk_row(), crosswalk_row(motivo="Duplicado exacto")],
    )
    audit = importer.audit_crosswalk(path)
    assert any("par RAN duplicado 12/86" in error for error in audit.errors)


def test_normal_flow_uses_direct_concatenation(tmp_path):
    path = tmp_path / "ran_directo.csv"
    write_csv(path, [row(scncve_edo="1", scncve_mun="1")])
    audit = importer.audit_file(path)

    connection = engine.raw_connection()
    try:
        plan = importer.build_plan(connection, audit, importer.audit_crosswalk())
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id_municipio FROM municipio WHERE btrim(clave_inegi) = '01001'"
            )
            municipality_id_01001 = cursor.fetchone()[0]
        assert plan.errors == []
        assert plan.missing_municipalities == []
        assert plan.crosswalk_combinations == 0
        assert plan.prepared_rows[0].municipality_id == municipality_id_01001
    finally:
        connection.rollback()
        connection.close()


def test_crosswalk_warns_when_it_overrides_an_existing_direct_match(tmp_path):
    csv_path = tmp_path / "ran.csv"
    crosswalk_path = tmp_path / "crosswalk.csv"
    write_csv(csv_path, [row(scncve_edo="1", scncve_mun="1")])
    write_crosswalk(
        crosswalk_path,
        [
            crosswalk_row(
                scncve_edo="1",
                scncve_mun="1",
                clave_inegi="01002",
            )
        ],
    )

    connection = engine.raw_connection()
    try:
        plan = importer.build_plan(
            connection,
            importer.audit_file(csv_path),
            importer.audit_crosswalk(crosswalk_path),
        )
        assert any("coincidencia directa 01001 también existe" in w for w in plan.warnings)
    finally:
        connection.rollback()
        connection.close()
