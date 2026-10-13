"""Observaciones informativas del matching; no proponen ni deciden destinos."""

import re

from .. import schemas


MESSAGES = {
    "UNIVERSO_DESTINOS_VACIO": "No hay destinos administrativos elegibles del tipo importado en el proyecto.",
    "IDENTIDAD_NUCLEO_INSUFICIENTE": "No se aportó una clave oficial ni un nombre de núcleo utilizable.",
    "CLAVE_SIN_COINCIDENCIA_EN_UNIVERSO": "La clave no coincide con un núcleo vinculado al proyecto cuya fuente admite identidad oficial.",
    "NOMBRE_SIN_COINCIDENCIA_EN_UNIVERSO": "El nombre no coincide con los núcleos vinculados al proyecto.",
    "MUNICIPIO_INCOMPATIBLE": "Un núcleo con nombre coincidente fue descartado por el municipio informado.",
    "ENTIDAD_INCOMPATIBLE": "Un núcleo con nombre coincidente fue descartado por la entidad informada.",
    "TIPO_NUCLEO_INCOMPATIBLE": "Un núcleo con nombre coincidente fue descartado por el tipo informado.",
    "NUMERO_PARCELA_AUSENTE": "No se aportó un número de parcela utilizable.",
    "PARCELA_SIN_COINCIDENCIA_EN_UNIVERSO": "Se identificó el núcleo, pero no una parcela compatible en el universo del proyecto.",
    "VARIANTE_FORMATO_PENDIENTE_REVISION": "Se observó una diferencia de ceros iniciales en un segmento numérico; no establece equivalencia ni genera candidatos.",
    "MULTIPLES_DESTINOS_COMPATIBLES": "El algoritmo generó múltiples destinos compatibles; requiere una decisión explícita.",
    "ID_ADMINISTRATIVO_SIN_COINCIDENCIA_EN_UNIVERSO": "El identificador técnico mapeado no coincide con un destino elegible del proyecto.",
}


def unavailable_diagnostic():
    return schemas.DiagnosticoConciliacionGisResponse(
        origen="no_disponible", codigos=["DIAGNOSTICO_HISTORICO_NO_DISPONIBLE"],
        mensaje="No se registró un diagnóstico para este resultado histórico.",
        campos_evaluados=[], evidencia=schemas.EvidenciaDiagnosticoGis(),
    ).model_dump(mode="json")


def _numeric_segment(value):
    # A diagnostic-only observation, never a canonical identifier or match rule.
    match = re.fullmatch(r"(p-)?([0-9]+)", value)
    if match is None:
        return None
    return match[1] or "", match[2].lstrip("0") or "0"


def matching_diagnostic(properties, universe, nucleus_universe, candidates, *, parcel, direct_id=None, direct_id_field=None):
    """Use the same predicates and authorized, preloaded context as this attempt.

    For parcels, the nucleus context also includes linked nuclei with no eligible
    parcels. It cannot add a matching destination. Territorial inspection stops
    at the first failed predicate, exactly as nucleus_criteria does.
    """
    from .geospatial_imports import normalize_parcel_number
    from .gis_reconciliation import normalize_text, nucleus_criteria

    codes, fields = [], []
    unique_nuclei = {pn.id_proyecto_nucleo: n for pn, n, _ in nucleus_universe}
    destinations = {(pn.id_proyecto_nucleo, p.id_parcela if p else None) for pn, _, p in universe}
    compatible = set()
    discards = {"municipio": 0, "entidad": 0, "tipo_nucleo": 0}
    lookup = {key.casefold(): (key, str(value).strip() if value is not None else "")
              for key, value in properties.items()}

    def observed(*aliases):
        for alias in aliases:
            key, value = lookup.get(alias.casefold(), (None, ""))
            if key is not None and value:
                if key not in fields:
                    fields.append(key)
                return value
        return ""

    if not destinations:
        codes.append("UNIVERSO_DESTINOS_VACIO")
    if direct_id is not None:
        # Technical mapping bypasses nucleus and number matching in the legacy API.
        if direct_id_field is not None:
            fields.append(direct_id_field)
        compatible = {c.id_proyecto_nucleo for c in candidates}
        if not candidates:
            codes.append("ID_ADMINISTRATIVO_SIN_COINCIDENCIA_EN_UNIVERSO")
    else:
        key = observed("cve_unica_nucleo" if parcel else "cve_unica")
        name = "" if key else observed("NombreNucl", "nombre_nucleo", "N__CLEO_AG")
        name_matches = 0
        for pn_id, nucleus in unique_nuclei.items():
            criteria = nucleus_criteria(properties, nucleus, parcel=parcel)
            if criteria:
                compatible.add(pn_id)
            if key or not name or normalize_text(name) != normalize_text(nucleus.nombre_nucleo):
                continue
            name_matches += 1
            for aliases, destination, field in (
                (("NombreMuni", "municipio"), nucleus.municipio.nombre, "municipio"),
                (("NombreEnti", "entidad", "estado"), nucleus.municipio.entidad.nombre, "entidad"),
                (("TipoNucleo", "tipo_nucleo", "TIPO_N__CL"), nucleus.tipo_tenencia.nombre, "tipo_nucleo"),
            ):
                source = observed(*aliases)
                if source and normalize_text(source) != normalize_text(destination):
                    discards[field] += 1
                    break
        if not key and not name:
            codes.append("IDENTIDAD_NUCLEO_INSUFICIENTE")
        elif unique_nuclei and not compatible:
            if key:
                codes.append("CLAVE_SIN_COINCIDENCIA_EN_UNIVERSO")
            elif not name_matches:
                codes.append("NOMBRE_SIN_COINCIDENCIA_EN_UNIVERSO")
            else:
                codes.extend(code for field, code in (
                    ("municipio", "MUNICIPIO_INCOMPATIBLE"),
                    ("entidad", "ENTIDAD_INCOMPATIBLE"),
                    ("tipo_nucleo", "TIPO_NUCLEO_INCOMPATIBLE"),
                ) if discards[field])

    eligible = [(pn, p) for pn, _, p in universe if p is not None and pn.id_proyecto_nucleo in compatible]
    variants = []
    if parcel and direct_id is None:
        numbers = [(column, observed(column)) for column in ("PARCELA", "Num_parcela", "no_parcela")]
        if not any(value for _, value in numbers):
            codes.append("NUMERO_PARCELA_AUSENTE")
        elif compatible and not candidates:
            codes.append("PARCELA_SIN_COINCIDENCIA_EN_UNIVERSO")
            segments = []
            for column, value in numbers:
                if value:
                    source = normalize_parcel_number(value)
                    segments.append((column, source, _numeric_segment(source)))
            # Normalize each eligible destination once, shared by all source columns.
            normalized_destinations = []
            if any(segment is not None for _, _, segment in segments):
                for pn, p in eligible:
                    number = normalize_parcel_number(p.no_parcela or "")
                    normalized_destinations.append(((pn.id_proyecto_nucleo, p.id_parcela), number, _numeric_segment(number)))
            for column, source, segment in segments:
                differing = {destination for destination, number, numeric_segment in normalized_destinations
                    if segment is not None and source != number and segment == numeric_segment}
                if differing:
                    variants.append(schemas.VarianteFormatoGis(campo=column,
                        regla="DIFERENCIA_CEROS_INICIALES_SEGMENTO_NUMERICO", destinos_observados=len(differing)))
            if variants:
                codes.append("VARIANTE_FORMATO_PENDIENTE_REVISION")
    if len(candidates) > 1:
        codes.append("MULTIPLES_DESTINOS_COMPATIBLES")
    return schemas.DiagnosticoConciliacionGisResponse(
        origen="registrado", codigos=codes,
        mensaje=" ".join(MESSAGES[code] for code in codes) if codes else
            "Se generó un destino compatible; su utilización requiere una decisión explícita.",
        campos_evaluados=fields,
        evidencia=schemas.EvidenciaDiagnosticoGis(
            destinos_evaluados=len(destinations), nucleos_evaluados=0 if direct_id is not None else len(unique_nuclei),
            nucleos_compatibles=len(compatible), parcelas_evaluadas=(len(destinations) if direct_id is not None else len(eligible)) if parcel else 0,
            candidatos=len(candidates), descartes_territoriales=schemas.DescartesTerritorialesGis(**discards),
            variantes_formato=variants,
        ),
    ).model_dump(mode="json")
