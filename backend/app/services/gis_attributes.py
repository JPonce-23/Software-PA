"""Allowlist de atributos técnicos y territoriales; nunca identidad personal."""
SAFE_FIELDS = frozenset(name.casefold() for name in (
    'cve_unica', 'cve_unica_nucleo', 'NombreNucl', 'nombre_nucleo',
    'TipoNucleo', 'tipo_nucleo', 'NombreMuni', 'municipio', 'NombreEnti',
    'entidad', 'estado', 'N__CLEO_AG', 'TIPO_N__CL', 'PARCELA', 'Num_parcela',
    'no_parcela', 'Frente', 'etiqueta', 'id_destino', 'id_nucleo',
    'id_parcela', 'record_id', 'geometria_previa_hash',
))


def sanitize_attributes(values: dict) -> dict:
    return {key: value for key, value in values.items()
            if isinstance(key, str) and key.casefold() in SAFE_FIELDS
            and (value is None or isinstance(value, (str, int, float, bool)))}
