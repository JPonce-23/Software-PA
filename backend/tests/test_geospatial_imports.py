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
    assert preview[0]["estado_conciliacion"] == "candidato"
    feature_id=preview[0]["id_importacion_feature"]
    candidate=api("GET",f"/api/importaciones/{record['id_importacion']}/features/{feature_id}/candidatos").json()[0]
    assert candidate["id_parcela"] == parcel_id

    repeated = client.post(
        f"/api/proyectos/{project_id}/importaciones",
        headers=admin_headers,
        data=form,
        files={"archivo": ("parcelas-qa.geojson", content, "application/geo+json")},
    )
    assert repeated.status_code == 201
    assert repeated.json()["id_importacion"] == record["id_importacion"]

    api("POST",f"/api/importaciones/{record['id_importacion']}/features/{feature_id}/decisiones",json={"accion":"confirmar","id_candidato":candidate["id_candidato"],"confirmacion_explicita":True})
    confirmed = api(
        "POST",
        f"/api/importaciones/{record['id_importacion']}/confirmar",
        json={"confirmacion_explicita": True},
    ).json()
    assert confirmed["estado"] == "completo"
    assert confirmed["importados"] == 1
    parcel = api("GET", f"/api/parcelas/{parcel_id}").json()
    assert parcel["geometria_wkt"] is None
    from app.database import SessionLocal
    from sqlalchemy import text
    with SessionLocal() as db:
        assert db.execute(text("SELECT count(*) FROM proyecto_parcela_geometria WHERE id_parcela=:p"),{"p":parcel_id}).scalar_one()==1


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


def test_legacy_trace_pipeline_and_map_remain_compatible(transactional_api):
    from tests.test_nucleus_gpkg_imports import project,preview,confirm
    from sqlalchemy import text
    api=transactional_api['request']; pid=project(api)
    for version in (1,2):
        content=json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},
            'geometry':{'type':'LineString','coordinates':[[-100,20],[-99+version/10,21]]}}]}).encode()
        staged=api('POST',f'/api/proyectos/{pid}/importaciones',expected=201,
            data={'tipo_objetivo':'trazo_proyecto','fuente':'QA trazo'},
            files={'archivo':('line.geojson',content,'application/geo+json')}).json()
        assert staged['validos']==1
        confirm(api,staged['id_importacion'])
    con=transactional_api['connection']
    assert con.execute(text('SELECT version,activo FROM trazo_proyecto WHERE id_proyecto=:p ORDER BY version'),{'p':pid}).all()==[(1,False),(2,True)]
    mapa=api('GET',f'/api/proyectos/{pid}/mapa').json()
    assert any(f['geometry']['type']=='MultiLineString' for f in mapa['features'])
    assert con.execute(text('SELECT count(*) FROM derecho_via_proyecto WHERE id_proyecto=:p'),{'p':pid}).scalar_one()==0
