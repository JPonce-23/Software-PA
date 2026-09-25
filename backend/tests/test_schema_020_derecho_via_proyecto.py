"""Contrato ORM y estructura para el Derecho de Via de schema 020."""

from sqlalchemy import inspect, text

from app import models
from app.database import engine


def test_020_mapping_matches_database(transactional_api):
    connection = transactional_api["connection"]
    inspector = inspect(engine)

    assert inspector.has_table("derecho_via_proyecto")
    assert inspector.has_table("trazo_proyecto")
    assert connection.execute(
        text("SELECT count(*) FROM schema_migrations WHERE version = '020'")
    ).scalar_one() == 1

    columns = {column["name"]: column for column in inspector.get_columns("derecho_via_proyecto")}
    assert not columns["id_proyecto"]["nullable"]
    assert not columns["version"]["nullable"]
    assert not columns["es_vigente"]["nullable"]
    assert not columns["geometria_poligono"]["nullable"]

    assert models.DerechoViaProyecto.__table__.c.geometria_poligono.type.geometry_type == "MULTIPOLYGON"
    assert models.DerechoViaProyecto.__table__.c.geometria_poligono.type.srid == 4326
    assert models.Proyecto.derechos_via.property.mapper.class_ is models.DerechoViaProyecto

    indexes = {index["name"]: index for index in inspector.get_indexes("derecho_via_proyecto")}
    assert indexes["idx_derecho_via_proyecto_geom"]["dialect_options"]["postgresql_using"] == "gist"
    assert indexes["uq_derecho_via_proyecto_vigente"]["unique"]
    assert indexes["uq_derecho_via_proyecto_vigente"]["dialect_options"]["postgresql_where"] is not None
