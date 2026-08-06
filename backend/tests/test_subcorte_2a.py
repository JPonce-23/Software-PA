"""Contratos y atomicidad del Subcorte 2A.

Las protecciones de PostgreSQL se validan al aplicar la migración 005; estas
pruebas cubren los contratos HTTP y la transacción de alta individual.
"""


GEOMETRIA = "MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))"


def _base_individual(seed_nucleo, seed_tramo_nucleo):
    return {
        "id_nucleo": seed_nucleo["id_nucleo"],
        "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
        "tipo_afectacion": "individual",
        "tipo_tenencia": "Parcelaria",
        "geometria_wkt": GEOMETRIA,
    }


def _crear_persona(client, admin_session, cleanup, nombre):
    response = client.post(
        "/api/personas", json={"nombre": nombre}, headers=admin_session
    )
    assert response.status_code == 201, response.text
    persona = response.json()
    cleanup.register("/api/personas", persona["id_persona"])
    return persona


def test_contrato_colectivo_no_acepta_parcela(
    client, admin_session, seed_nucleo, seed_tramo_nucleo, seed_parcela,
):
    response = client.post(
        "/api/afectaciones/colectivas",
        json={
            "id_nucleo": seed_nucleo["id_nucleo"],
            "id_tramo_nucleo": seed_tramo_nucleo["id_tramo_nucleo"],
            "tipo_tenencia": "Tierras de Uso Común",
            "id_parcela": seed_parcela["id_parcela"],
            "geometria_wkt": GEOMETRIA,
        },
        headers=admin_session,
    )
    assert response.status_code == 422


def test_contrato_individual_no_acepta_referencia_textual_parcela(
    client, admin_session, seed_nucleo, seed_tramo_nucleo, seed_parcela,
):
    response = client.post(
        "/api/afectaciones/individuales",
        json={
            **_base_individual(seed_nucleo, seed_tramo_nucleo),
            "no_parcela_solar": "No debe duplicarse",
            "parcela": {"modo": "existente", "id_parcela": seed_parcela["id_parcela"]},
        },
        headers=admin_session,
    )
    assert response.status_code == 422


def test_copropiedad_nueva_exige_dos_titulares(
    client, admin_session, seed_nucleo, seed_tramo_nucleo,
):
    response = client.post(
        "/api/afectaciones/individuales",
        json={
            **_base_individual(seed_nucleo, seed_tramo_nucleo),
            "parcela": {
                "modo": "nueva",
                "tipo_parcela": "copropiedad",
                "no_parcela_ppt": "COP-UNICO",
                "documentacion_disponible": True,
                "titulares": [{"id_persona": 1, "tipo_derecho": "titular"}],
            },
        },
        headers=admin_session,
    )
    assert response.status_code == 422
    assert "copropiedad" in response.text.lower()


def test_alta_individual_con_parcela_existente(
    client, admin_session, cleanup, seed_nucleo, seed_tramo_nucleo, seed_parcela,
):
    response = client.post(
        "/api/afectaciones/individuales",
        json={
            **_base_individual(seed_nucleo, seed_tramo_nucleo),
            "parcela": {"modo": "existente", "id_parcela": seed_parcela["id_parcela"]},
        },
        headers=admin_session,
    )
    assert response.status_code == 201, response.text
    afectacion = response.json()
    assert afectacion["tipo_afectacion"] == "individual"
    assert afectacion["id_parcela"] == seed_parcela["id_parcela"]
    cleanup.register("/api/afectaciones", afectacion["id_afectacion"])


def test_alta_atomica_revierte_parcela_si_titular_no_existe(
    client, admin_session, seed_nucleo, seed_tramo_nucleo,
):
    antes = client.get(
        f"/api/parcelas?id_nucleo={seed_nucleo['id_nucleo']}", headers=admin_session
    )
    assert antes.status_code == 200

    response = client.post(
        "/api/afectaciones/individuales",
        json={
            **_base_individual(seed_nucleo, seed_tramo_nucleo),
            "parcela": {
                "modo": "nueva",
                "tipo_parcela": "individual",
                "no_parcela_ppt": "PPT-REVERSO",
                "documentacion_disponible": True,
                "titulares": [{"id_persona": 999999, "tipo_derecho": "titular"}],
            },
        },
        headers=admin_session,
    )
    assert response.status_code == 404

    despues = client.get(
        f"/api/parcelas?id_nucleo={seed_nucleo['id_nucleo']}", headers=admin_session
    )
    assert despues.status_code == 200
    assert len(despues.json()) == len(antes.json())


def test_alta_atomica_copropiedad_con_dos_titulares(
    client, admin_session, cleanup, seed_nucleo, seed_tramo_nucleo,
):
    primera = _crear_persona(client, admin_session, cleanup, "Titular copropiedad 1")
    segunda = _crear_persona(client, admin_session, cleanup, "Titular copropiedad 2")

    response = client.post(
        "/api/afectaciones/individuales",
        json={
            **_base_individual(seed_nucleo, seed_tramo_nucleo),
            "parcela": {
                "modo": "nueva",
                "tipo_parcela": "copropiedad",
                "no_parcela_ppt": "COP-DOS",
                "documentacion_disponible": True,
                "titulares": [
                    {"id_persona": primera["id_persona"], "tipo_derecho": "titular"},
                    {"id_persona": segunda["id_persona"], "tipo_derecho": "cotitular"},
                ],
            },
        },
        headers=admin_session,
    )
    assert response.status_code == 201, response.text
    afectacion = response.json()
    cleanup.register("/api/parcelas", afectacion["id_parcela"])
    cleanup.register("/api/afectaciones", afectacion["id_afectacion"])
