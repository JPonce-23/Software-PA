"""Contract tests for the bounded national RAN nuclei catalog endpoint."""

import uuid
from datetime import datetime, timezone

import pytest

from app import models
from app.services.common import set_audit_context


SOURCE = "RAN_PHINA_CATALOGO_NUCLEOS"


@pytest.fixture(scope="module")
def ran_catalog_records(transactional_api):
    session_factory = transactional_api["session_factory"]
    token = f"CATALOGO-RAN-{uuid.uuid4().hex[:12]}"

    with session_factory() as db:
        municipalities = (
            db.query(models.Municipio)
            .join(models.EntidadFederativa)
            .filter(
                models.Municipio.activo.is_(True),
                models.EntidadFederativa.activo.is_(True),
            )
            .order_by(models.Municipio.id_entidad, models.Municipio.id_municipio)
            .all()
        )
        municipality_a = municipalities[0]
        municipality_b = next(
            item
            for item in municipalities
            if item.id_entidad != municipality_a.id_entidad
        )
        tenure_by_code = {
            option.codigo: option
            for option in db.query(models.CatalogoOperativo).filter(
                models.CatalogoOperativo.tipo_catalogo == "tipo_tenencia",
                models.CatalogoOperativo.codigo.in_(("ejido", "comunidad")),
                models.CatalogoOperativo.activo.is_(True),
            )
        }
        admin_id = (
            db.query(models.Usuario.id_usuario)
            .filter(models.Usuario.rol == "admin", models.Usuario.activo.is_(True))
            .order_by(models.Usuario.id_usuario)
            .first()[0]
        )

        def nucleus(
            suffix: str,
            municipality: models.Municipio,
            tenure_code: str,
            *,
            source: str = SOURCE,
            active: bool = True,
        ) -> models.NucleoAgrario:
            source_id = f"QA-{uuid.uuid4().hex}"
            return models.NucleoAgrario(
                id_municipio=municipality.id_municipio,
                nombre_nucleo=f"{token} {suffix}",
                id_tipo_tenencia=tenure_by_code[tenure_code].id_catalogo_opcion,
                fuente_datos=source,
                id_entidad_fuente=str(municipality.id_entidad),
                id_municipio_fuente=str(municipality.id_municipio),
                id_nucleo_fuente=source_id,
                alcance_identidad_fuente="nacional",
                activo=active,
                creado_por=admin_id,
                fecha_baja=datetime.now(timezone.utc) if not active else None,
                id_usuario_baja=admin_id if not active else None,
                motivo_baja="Registro inactivo de prueba" if not active else None,
            )

        ejido = nucleus("MiXtO Ejido", municipality_a, "ejido")
        comunidad = nucleus("MiXtO Comunidad", municipality_a, "comunidad")
        other_state = nucleus("MiXtO Otro", municipality_b, "ejido")
        manual = nucleus(
            "MiXtO Manual", municipality_a, "ejido", source="QA_MANUAL"
        )
        inactive = nucleus(
            "MiXtO Inactivo", municipality_a, "ejido", active=False
        )
        set_audit_context(db, admin_id)
        db.add_all((ejido, comunidad, other_state, manual, inactive))
        db.commit()
        result = {
            "token": token,
            "municipality_a": {
                "id_municipio": municipality_a.id_municipio,
                "municipio": municipality_a.nombre,
                "id_entidad": municipality_a.id_entidad,
                "entidad": municipality_a.entidad.nombre,
            },
            "municipality_b": {
                "id_municipio": municipality_b.id_municipio,
                "municipio": municipality_b.nombre,
                "id_entidad": municipality_b.id_entidad,
                "entidad": municipality_b.entidad.nombre,
            },
            "ran_ids": {ejido.id_nucleo, comunidad.id_nucleo, other_state.id_nucleo},
            "excluded_ids": {manual.id_nucleo, inactive.id_nucleo},
            "source_ids": {
                ejido.id_nucleo: ejido.id_nucleo_fuente,
                comunidad.id_nucleo: comunidad.id_nucleo_fuente,
                other_state.id_nucleo: other_state.id_nucleo_fuente,
            },
        }
    return result


def test_without_filters_is_bounded_stable_and_only_returns_ran(transactional_api):
    api = transactional_api["request"]
    records = api("GET", "/api/catalogos/nucleos").json()

    assert len(records) == 20
    assert records == api("GET", "/api/catalogos/nucleos").json()
    same_name_ids: dict[str, list[int]] = {}
    for item in records:
        same_name_ids.setdefault(item["nombre_nucleo"].strip().lower(), []).append(
            item["id_nucleo"]
        )
    assert all(ids == sorted(ids) for ids in same_name_ids.values())

    ids = [item["id_nucleo"] for item in records]
    with transactional_api["session_factory"]() as db:
        sources = dict(
            db.query(models.NucleoAgrario.id_nucleo, models.NucleoAgrario.fuente_datos)
            .filter(models.NucleoAgrario.id_nucleo.in_(ids))
            .all()
        )
    assert set(sources.values()) == {SOURCE}


def test_filters_by_internal_state_fk(transactional_api, ran_catalog_records):
    api = transactional_api["request"]
    state_id = ran_catalog_records["municipality_a"]["id_entidad"]
    records = api("GET", f"/api/catalogos/nucleos?id_entidad={state_id}").json()

    assert records
    assert all(item["id_entidad"] == state_id for item in records)


def test_filters_by_internal_municipality_fk(transactional_api, ran_catalog_records):
    api = transactional_api["request"]
    municipality_id = ran_catalog_records["municipality_a"]["id_municipio"]
    records = api(
        "GET", f"/api/catalogos/nucleos?id_municipio={municipality_id}"
    ).json()

    assert records
    assert all(item["id_municipio"] == municipality_id for item in records)


def test_name_search_is_case_insensitive(transactional_api, ran_catalog_records):
    api = transactional_api["request"]
    records = api(
        "GET", f"/api/catalogos/nucleos?q={ran_catalog_records['token'].swapcase()}"
    ).json()

    assert {item["id_nucleo"] for item in records} == ran_catalog_records["ran_ids"]


def test_combines_municipality_and_name(transactional_api, ran_catalog_records):
    api = transactional_api["request"]
    municipality_id = ran_catalog_records["municipality_a"]["id_municipio"]
    records = api(
        "GET",
        "/api/catalogos/nucleos"
        f"?id_municipio={municipality_id}&q={ran_catalog_records['token']}",
    ).json()

    assert len(records) == 2
    assert all(item["id_municipio"] == municipality_id for item in records)


def test_valid_limit_and_maximum_are_enforced(transactional_api):
    api = transactional_api["request"]

    assert len(api("GET", "/api/catalogos/nucleos?limit=7").json()) == 7
    assert len(api("GET", "/api/catalogos/nucleos?limit=100").json()) == 100
    api("GET", "/api/catalogos/nucleos?limit=101", expected=422)


def test_excludes_non_ran_and_inactive_records(transactional_api, ran_catalog_records):
    api = transactional_api["request"]
    records = api(
        "GET", f"/api/catalogos/nucleos?q={ran_catalog_records['token']}"
    ).json()
    result_ids = {item["id_nucleo"] for item in records}

    assert result_ids == ran_catalog_records["ran_ids"]
    assert result_ids.isdisjoint(ran_catalog_records["excluded_ids"])


def test_returns_ejido_and_comunidad_contract(transactional_api, ran_catalog_records):
    api = transactional_api["request"]
    records = api(
        "GET", f"/api/catalogos/nucleos?q={ran_catalog_records['token']}"
    ).json()
    tenure = {
        (item["codigo_tipo_tenencia"], item["tipo_tenencia"])
        for item in records
    }

    assert tenure == {("ejido", "Ejido"), ("comunidad", "Comunidad")}


def test_territorial_names_and_source_id_match_internal_fks(
    transactional_api, ran_catalog_records
):
    api = transactional_api["request"]
    records = api(
        "GET", f"/api/catalogos/nucleos?q={ran_catalog_records['token']}"
    ).json()

    municipalities = {
        item["id_municipio"]: item
        for item in (
            ran_catalog_records["municipality_a"],
            ran_catalog_records["municipality_b"],
        )
    }
    for item in records:
        expected = municipalities[item["id_municipio"]]
        assert item["municipio"] == expected["municipio"]
        assert item["id_entidad"] == expected["id_entidad"]
        assert item["entidad"] == expected["entidad"]
        assert item["id_nucleo_fuente"] == ran_catalog_records["source_ids"][
            item["id_nucleo"]
        ]


def test_returns_empty_list_without_matches(transactional_api):
    api = transactional_api["request"]
    missing = f"NO-EXISTE-{uuid.uuid4().hex}"

    assert api("GET", f"/api/catalogos/nucleos?q={missing}").json() == []
    assert api("GET", "/api/catalogos/nucleos?q=%20%20%20").json() == []
