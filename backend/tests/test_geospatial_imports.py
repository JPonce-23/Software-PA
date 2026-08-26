import json


def _geojson(parcel_id: int) -> bytes:
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": "qa-1",
                    "properties": {"record_id": parcel_id},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-100.0, 20.0],
                                [-99.99, 20.0],
                                [-99.99, 20.01],
                                [-100.0, 20.01],
                                [-100.0, 20.0],
                            ]
                        ],
                    },
                }
            ],
        }
    ).encode()


def test_parcel_import_preview_confirmation_and_idempotency(
    client, admin_headers, api, target_domain
):
    project_id = target_domain["project"]["id_proyecto"]
    parcel_id = target_domain["parcels"][1]["id_parcela"]
    content = _geojson(parcel_id)
    form = {
        "tipo_objetivo": "parcela",
        "fuente": "Geometría sintética QA, no cartografía RAN",
        "fecha_fuente": "2026-08-25",
        "mapeo": json.dumps({"id_destino": "record_id"}),
    }
    staged = client.post(
        f"/api/proyectos/{project_id}/importaciones",
        headers=admin_headers,
        data=form,
        files={"archivo": ("parcelas-qa.geojson", content, "application/geo+json")},
    )
    assert staged.status_code == 201, staged.text
    record = staged.json()
    assert record["estado"] == "previsualizado"
    assert record["validos"] == 1
    assert record["errores"] == 0
    preview = api(
        "GET", f"/api/importaciones/{record['id_importacion']}/features"
    ).json()
    assert preview[0]["estado"] == "valido"
    assert preview[0]["atributos_normalizados"]["id_destino"] == parcel_id

    repeated = client.post(
        f"/api/proyectos/{project_id}/importaciones",
        headers=admin_headers,
        data=form,
        files={"archivo": ("parcelas-qa.geojson", content, "application/geo+json")},
    )
    assert repeated.status_code == 201
    assert repeated.json()["id_importacion"] == record["id_importacion"]

    confirmed = api(
        "POST",
        f"/api/importaciones/{record['id_importacion']}/confirmar",
        json={"confirmacion_explicita": True},
    ).json()
    assert confirmed["estado"] == "completo"
    assert confirmed["importados"] == 1
    parcel = api("GET", f"/api/parcelas/{parcel_id}").json()
    assert parcel["geometria_wkt"].startswith("MULTIPOLYGON")


def test_import_requires_explicit_target_mapping(
    client, admin_headers, target_domain
):
    project_id = target_domain["project"]["id_proyecto"]
    response = client.post(
        f"/api/proyectos/{project_id}/importaciones",
        headers=admin_headers,
        data={
            "tipo_objetivo": "parcela",
            "fuente": "QA",
            "mapeo": "{}",
        },
        files={
            "archivo": (
                "sin-mapeo.geojson",
                _geojson(target_domain["parcels"][0]["id_parcela"]),
                "application/geo+json",
            )
        },
    )
    assert response.status_code == 422
