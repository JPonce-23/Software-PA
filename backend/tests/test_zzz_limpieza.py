"""Verificación final de que la suite usa una base aislada y desechable."""

import os


def test_entorno_de_pruebas_es_aislado_y_desechable(cleanup):
    """Los fixtures se descartan junto con la BD, sin falsear bajas de negocio."""
    database_name = os.environ["DB_NAME"].lower()
    assert os.environ["APP_ENV"].lower() == "test"
    assert database_name.startswith("test_") or database_name.endswith("_test") or "_test_" in database_name
    assert cleanup.items, "La sesión no registró fixtures para validar"
