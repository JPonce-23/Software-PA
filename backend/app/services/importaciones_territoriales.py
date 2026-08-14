"""Flujo de previsualizacion y confirmacion para importaciones GeoJSON."""

import hashlib
import json
import unicodedata
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from .access import (
    require_nucleo_access,
    require_tramo_access,
    require_tramo_nucleo_access,
)
from .common import set_audit_context


TIPOS_IMPORTACION = {
    "tramos",
    "nucleos",
    "derecho_via",
    "parcelas",
    "cruces_operativos",
}

POLYGON_TYPES = {"Polygon", "MultiPolygon"}
LINE_TYPES = {"LineString", "MultiLineString"}


def file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parse_geojson(content: bytes) -> dict[str, Any]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Archivo JSON invalido") from exc
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        raise HTTPException(status_code=400, detail="El archivo debe ser un FeatureCollection.")
    if not isinstance(data.get("features"), list) or not data["features"]:
        raise HTTPException(status_code=400, detail="El archivo no contiene features.")
    return data


def preview(
    db: Session,
    tipo: str,
    data: dict[str, Any],
    archivo_sha256: str,
    user: models.Usuario,
    contexto: dict[str, Any],
) -> schemas.ImportacionTerritorialPreviewResponse:
    _validar_tipo(tipo)
    items = []
    seen: set[str] = set()
    features = data["features"]

    if tipo == "derecho_via" and len(features) != 1:
        items.append(_item_error(0, "La importacion de derecho de via debe contener una sola feature."))
    elif tipo == "nucleos":
        items = _preview_nucleos(db, features, user, contexto)
    else:
        for index, feature in enumerate(features):
            item = _preview_feature(db, tipo, index, feature, user, contexto, seen)
            items.append(item)

    return _preview_response(tipo, archivo_sha256, items)


def confirm(
    db: Session,
    tipo: str,
    data: schemas.ImportacionTerritorialConfirmRequest,
    user: models.Usuario,
) -> schemas.ImportacionTerritorialConfirmResponse:
    _validar_tipo(tipo)
    if not data.items:
        raise HTTPException(status_code=400, detail="No hay registros para confirmar.")
    if any(item.estado == "error" or item.errores for item in data.items):
        raise HTTPException(status_code=400, detail="No se puede confirmar una importacion con errores.")

    ids: list[int] = []
    seen: set[str] = set()
    try:
        set_audit_context(db, user.id_usuario)
        items = _revalidar_nucleos(db, data.items, user) if tipo == "nucleos" else [
            _revalidar_item(db, tipo, item, user, seen) for item in data.items
        ]
        for validado in items:
            ids.append(_insertar_item(db, tipo, validado, user))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La importacion entra en conflicto con la integridad de los datos.",
        ) from exc
    except HTTPException:
        db.rollback()
        raise

    return schemas.ImportacionTerritorialConfirmResponse(
        tipo=tipo,
        total=len(ids),
        ids_creados=ids,
        mensaje=f"Se importaron {len(ids)} registros.",
    )


def _validar_tipo(tipo: str) -> None:
    if tipo not in TIPOS_IMPORTACION:
        raise HTTPException(status_code=404, detail="Tipo de importacion territorial no soportado.")


def _preview_nucleos(
    db: Session,
    features: list[Any],
    user: models.Usuario,
    contexto: dict[str, Any],
) -> list[schemas.ImportacionTerritorialPreviewItem]:
    validos: list[dict[str, Any]] = []
    errores: list[schemas.ImportacionTerritorialPreviewItem] = []
    for index, feature in enumerate(features):
        try:
            datos = _normalizar_feature(db, "nucleos", index, feature, user, contexto, set())
            validos.append(datos)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else "Feature invalida."
            errores.append(_item_error(index, detail))

    agrupados = _agrupar_nucleos(db, validos)
    items = [
        schemas.ImportacionTerritorialPreviewItem(
            index=datos["index"],
            estado="advertencia" if datos.get("advertencias") else "valido",
            accion="crear",
            resumen=datos.pop("resumen"),
            datos=datos,
            advertencias=datos.pop("advertencias", []),
        )
        for datos in agrupados
    ]
    return [*items, *errores]


def _revalidar_nucleos(
    db: Session,
    items: list[schemas.ImportacionTerritorialPreviewItem],
    user: models.Usuario,
) -> list[dict[str, Any]]:
    normalizados: list[dict[str, Any]] = []
    for item in items:
        normalizados.append(_revalidar_item(db, "nucleos", item, user, set()))
    return _agrupar_nucleos(db, normalizados)


def _preview_feature(
    db: Session,
    tipo: str,
    index: int,
    feature: Any,
    user: models.Usuario,
    contexto: dict[str, Any],
    seen: set[str],
) -> schemas.ImportacionTerritorialPreviewItem:
    try:
        datos = _normalizar_feature(db, tipo, index, feature, user, contexto, seen)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "Feature invalida."
        return _item_error(index, detail)
    return schemas.ImportacionTerritorialPreviewItem(
        index=index,
        estado="advertencia" if datos.get("advertencias") else "valido",
        accion="versionar" if tipo == "derecho_via" else "crear",
        resumen=datos.pop("resumen"),
        datos=datos,
        advertencias=datos.pop("advertencias", []),
    )


def _revalidar_item(
    db: Session,
    tipo: str,
    item: schemas.ImportacionTerritorialPreviewItem,
    user: models.Usuario,
    seen: set[str],
) -> dict[str, Any]:
    feature = {
        "type": "Feature",
        "properties": item.datos.get("properties", {}),
        "geometry": item.datos.get("geometry"),
    }
    contexto = item.datos.get("contexto", {})
    return _normalizar_feature(db, tipo, item.index, feature, user, contexto, seen)


def _normalizar_feature(
    db: Session,
    tipo: str,
    index: int,
    feature: Any,
    user: models.Usuario,
    contexto: dict[str, Any],
    seen: set[str],
) -> dict[str, Any]:
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        raise HTTPException(status_code=400, detail="No es un Feature valido.")
    geometry = feature.get("geometry")
    properties = feature.get("properties") or {}
    if not isinstance(properties, dict):
        raise HTTPException(status_code=400, detail="Properties debe ser un objeto.")

    if tipo == "tramos":
        return _normalizar_tramo(db, index, geometry, properties, user, contexto, seen)
    if tipo == "nucleos":
        return _normalizar_nucleo(db, index, geometry, properties, user, contexto)
    if tipo == "derecho_via":
        return _normalizar_derecho_via(db, index, geometry, properties, user, contexto)
    if tipo == "parcelas":
        return _normalizar_parcela(db, index, geometry, properties, user, contexto)
    return _normalizar_cruce(db, index, geometry, properties, user, contexto, seen)


def _normalizar_tramo(
    db: Session,
    index: int,
    geometry: Any,
    properties: dict[str, Any],
    user: models.Usuario,
    contexto: dict[str, Any],
    seen: set[str],
) -> dict[str, Any]:
    id_proyecto = _int_context(contexto, "id_proyecto")
    proyecto = _proyecto_activo(db, id_proyecto)
    clave = _text(properties.get("clave_tramo") or properties.get("clave"), 20, "clave_tramo")
    nombre = _text(properties.get("nombre_tramo") or properties.get("nombre"), 200, "nombre_tramo")
    descripcion = _optional_text(properties.get("descripcion"), 1000)
    ancho = _decimal_optional(properties.get("ancho_total_derecho_via_m"), "ancho_total_derecho_via_m") or Decimal("40.00")
    if ancho <= 0:
        raise HTTPException(status_code=400, detail="ancho_total_derecho_via_m debe ser mayor que cero.")
    geometry_json = _validar_geometria(db, geometry, LINE_TYPES, "linea")

    key = f"{id_proyecto}:{clave.lower()}"
    if key in seen:
        raise HTTPException(status_code=400, detail="clave_tramo duplicada dentro del archivo.")
    seen.add(key)
    existe = db.query(models.Tramo.id_tramo).filter(
        models.Tramo.id_proyecto == id_proyecto,
        func.lower(models.Tramo.clave_tramo) == clave.lower(),
        models.Tramo.activo.is_(True),
    ).first()
    if existe:
        raise HTTPException(status_code=409, detail="Ya existe un tramo activo con esa clave en el proyecto.")

    return _datos(
        index,
        f"{clave} - {nombre}",
        properties,
        geometry,
        contexto,
        id_proyecto=id_proyecto,
        clave_tramo=clave,
        nombre_tramo=nombre,
        descripcion=descripcion,
        ancho_total_derecho_via_m=str(ancho),
        geometry_json=geometry_json,
        nombre_proyecto=proyecto.nombre_proyecto,
    )


def _normalizar_nucleo(
    db: Session,
    index: int,
    geometry: Any,
    properties: dict[str, Any],
    user: models.Usuario,
    contexto: dict[str, Any],
) -> dict[str, Any]:
    ids_tramo = _ids_context(contexto, "ids_tramo_contexto")
    if user.rol == "geografo" and not ids_tramo:
        raise HTTPException(status_code=400, detail="Seleccione al menos un tramo asignado.")
    for id_tramo in ids_tramo:
        require_tramo_access(db, user, id_tramo)

    nombre = _text(
        _property(
            properties,
            "nombre_nucleo",
            "nombre",
            "name",
            "Name",
            "NOMBRE",
            "NOMBRE_NUCLEO",
            "NOM_NUCLEO_AGRARIO",
            "NOM_NUCLEO",
            "NOM_NUC",
            "NUCLEO",
            "nucleo",
            "ejido",
            "NOM_EJIDO",
            "NOMBRE_EJIDO",
        ),
        300,
        "nombre_nucleo",
    )
    tipo = _normalizar_tipo_nucleo(
        _property(
            properties,
            "tipo_nucleo",
            "tipo",
            "TIPO",
            "TIPO_NUCLEO",
            "TIPO_NUC",
            "tipo_propiedad",
            "TIPO_PROPIEDAD",
            "REGIMEN",
            "regimen",
            "CLASE",
            "clase",
        )
    ) or _normalizar_tipo_nucleo(contexto.get("tipo_nucleo_fallback"))
    if tipo not in {"ejido", "comunidad"}:
        raise HTTPException(status_code=400, detail="tipo_nucleo debe ser ejido o comunidad, o seleccione un tipo predeterminado.")
    comunidad_indigena = bool(_property(properties, "comunidad_indigena", "indigena", "INDIGENA") or False)
    residencia = _optional_text(_property(properties, "residencia", "RESIDENCIA"), 300)
    municipio_nombre = _property(
        properties,
        "municipio",
        "MUNICIPIO",
        "municipio_nombre",
        "MUNICIPIO_NOMBRE",
        "nom_mun",
        "NOM_MUN",
        "NOM_MPIO",
        "NOM_MUNICIPIO",
        "NOMBRE_MUNICIPIO",
    )
    entidad_nombre = _property(
        properties,
        "entidad",
        "ENTIDAD",
        "estado",
        "ESTADO",
        "NOM_ENT",
        "NOM_ENTIDAD",
        "nombre_entidad",
        "ENTIDAD_NOMBRE",
    )
    id_municipio = _municipio_por_nombre(
        db,
        municipio_nombre,
        entidad_nombre,
        contexto.get("id_entidad_fallback"),
    ) or _municipio_activo_id(
        db,
        _property(properties, "id_municipio", "ID_MUNICIPIO", "municipio_id"),
    ) or _municipio_activo_id(db, contexto.get("id_municipio_fallback"))
    if id_municipio is None:
        raise HTTPException(
            status_code=400,
            detail="No se pudo resolver el municipio. Use MUNICIPIO/nom_mun con entidad predeterminada o seleccione municipio predeterminado.",
        )
    geometry_json = _validar_geometria(db, geometry, POLYGON_TYPES, "poligono", ids_tramo)

    return _datos(
        index,
        nombre,
        properties,
        geometry,
        contexto,
        id_municipio=id_municipio,
        nombre_nucleo=nombre,
        tipo_nucleo=tipo,
        comunidad_indigena=comunidad_indigena,
        residencia=residencia,
        features_agrupadas=1,
        indices_origen=[index],
        geometry_json=geometry_json,
    )


def _nucleo_group_key(datos: dict[str, Any]) -> str:
    return ":".join([
        str(datos["id_municipio"]),
        str(datos["tipo_nucleo"]),
        _normalizar_clave(datos["nombre_nucleo"]),
    ])


def _validar_nucleo_disponible(db: Session, datos: dict[str, Any]) -> None:
    nombre_key = _normalizar_clave(datos["nombre_nucleo"])
    candidatos = db.query(
        models.NucleoAgrario.id_nucleo,
        models.NucleoAgrario.nombre_nucleo,
    ).filter(
        models.NucleoAgrario.id_municipio == datos["id_municipio"],
        models.NucleoAgrario.tipo_nucleo == datos["tipo_nucleo"],
        models.NucleoAgrario.activo.is_(True),
    ).all()
    if any(_normalizar_clave(row.nombre_nucleo) == nombre_key for row in candidatos):
        raise HTTPException(
            status_code=409,
            detail="Ya existe un nucleo agrario activo con ese nombre, tipo y municipio.",
        )


def _agrupar_nucleos(db: Session, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grupos: dict[str, list[dict[str, Any]]] = {}
    orden: list[str] = []
    for item in items:
        key = _nucleo_group_key(item)
        if key not in grupos:
            grupos[key] = []
            orden.append(key)
        grupos[key].append(item)

    agrupados: list[dict[str, Any]] = []
    for key in orden:
        group = grupos[key]
        base = {**group[0]}
        _validar_nucleo_disponible(db, base)

        indices = [item["index"] for item in group]
        base["indices_origen"] = indices
        base["features_agrupadas"] = len(group)

        advertencias = list(base.get("advertencias", []))
        if len(group) > 1:
            merged_geometry_json = _fusionar_poligonos(db, [item["geometry_json"] for item in group])
            base["geometry_json"] = merged_geometry_json
            base["geometry"] = json.loads(merged_geometry_json)
            base["properties"] = {
                **base.get("properties", {}),
                "_features_agrupadas": len(group),
                "_indices_origen": indices,
            }
            advertencias.append(
                f"Nucleo fusionado desde {len(group)} features del archivo en una geometria multipoligonal."
            )

            residencias = {item.get("residencia") for item in group}
            comunidades = {item.get("comunidad_indigena") for item in group}
            if len(residencias) > 1 or len(comunidades) > 1:
                advertencias.append(
                    "El grupo tenia atributos no geometricos distintos; se conservaron los valores del primer feature."
                )

        base["advertencias"] = advertencias
        agrupados.append(base)
    return agrupados


def _fusionar_poligonos(db: Session, geometries_json: list[str]) -> str:
    try:
        row = db.execute(
            text(
                """
                WITH entrada AS (
                    SELECT ST_SetSRID(ST_GeomFromGeoJSON(raw.geometry_json), 4326) AS geom
                      FROM unnest(:geometries) AS raw(geometry_json)
                ),
                fusion AS (
                    SELECT ST_Multi(
                               ST_CollectionExtract(
                                   ST_UnaryUnion(ST_Collect(geom)),
                                   3
                               )
                           ) AS geom
                      FROM entrada
                )
                SELECT ST_AsGeoJSON(geom) AS geometry_json,
                       ST_IsValid(geom) AS valida,
                       NOT ST_IsEmpty(geom) AS no_vacia,
                       ST_GeometryType(geom) AS tipo
                  FROM fusion
                """
            ),
            {"geometries": geometries_json},
        ).mappings().one()
    except DBAPIError as exc:
        raise HTTPException(status_code=400, detail="No fue posible fusionar las geometrias del nucleo.") from exc

    if not row["valida"] or not row["no_vacia"] or row["tipo"] != "ST_MultiPolygon":
        raise HTTPException(status_code=400, detail="La fusion de geometrias del nucleo no produjo un multipoligono valido.")
    return row["geometry_json"]


def _normalizar_derecho_via(
    db: Session,
    index: int,
    geometry: Any,
    properties: dict[str, Any],
    user: models.Usuario,
    contexto: dict[str, Any],
) -> dict[str, Any]:
    id_tramo = _int_context(contexto, "id_tramo")
    require_tramo_access(db, user, id_tramo)
    tramo = _tramo_activo(db, id_tramo)
    fuente = _text(contexto.get("fuente") or properties.get("fuente"), 200, "fuente")
    fecha = _date_value(contexto.get("fecha_vigencia_inicio") or properties.get("fecha_vigencia_inicio"))
    ancho_izq = _decimal_optional(contexto.get("ancho_izquierdo_m") or properties.get("ancho_izquierdo_m"), "ancho_izquierdo_m")
    ancho_der = _decimal_optional(contexto.get("ancho_derecho_m") or properties.get("ancho_derecho_m"), "ancho_derecho_m")
    geometry_json = _validar_geometria(db, geometry, POLYGON_TYPES, "poligono")
    _validar_interseccion_tramo(db, geometry_json, id_tramo)

    return _datos(
        index,
        f"Franja para {tramo.clave_tramo}",
        properties,
        geometry,
        contexto,
        id_tramo=id_tramo,
        fuente=fuente,
        fecha_vigencia_inicio=fecha.isoformat(),
        ancho_izquierdo_m=str(ancho_izq) if ancho_izq is not None else None,
        ancho_derecho_m=str(ancho_der) if ancho_der is not None else None,
        geometry_json=geometry_json,
    )


def _normalizar_parcela(
    db: Session,
    index: int,
    geometry: Any,
    properties: dict[str, Any],
    user: models.Usuario,
    contexto: dict[str, Any],
) -> dict[str, Any]:
    id_nucleo = _resolver_nucleo_contexto(db, user, contexto)
    tipo_parcela = properties.get("tipo_parcela")
    if tipo_parcela is not None:
        tipo_parcela = str(tipo_parcela).strip().lower()
        if tipo_parcela not in {"individual", "copropiedad"}:
            raise HTTPException(status_code=400, detail="tipo_parcela debe ser individual o copropiedad.")
    no_ppt = _optional_text(properties.get("no_parcela_ppt") or properties.get("parcela"), 50)
    certificado = _optional_text(properties.get("certificado_parcelario"), 100)
    folio = _optional_text(properties.get("folio_derechos"), 100)
    if not any([no_ppt, certificado, folio]):
        raise HTTPException(status_code=400, detail="La parcela requiere no_parcela_ppt, certificado_parcelario o folio_derechos.")
    geometry_json = _validar_geometria(db, geometry, POLYGON_TYPES, "poligono")
    _validar_interseccion_nucleo(db, geometry_json, id_nucleo)
    advertencias = []
    if properties.get("nombre_titular"):
        advertencias.append("nombre_titular no se importara automaticamente; registre titulares con evidencia fuerte.")

    return _datos(
        index,
        no_ppt or certificado or folio,
        properties,
        geometry,
        contexto,
        advertencias=advertencias,
        id_nucleo=id_nucleo,
        tipo_parcela=tipo_parcela,
        no_parcela_ppt=no_ppt,
        certificado_parcelario=certificado,
        folio_derechos=folio,
        constancia_vigencia_fecha=_date_optional(properties.get("constancia_vigencia_fecha")),
        documentacion_disponible=bool(properties.get("documentacion_disponible", False)),
        documentacion_faltante=_optional_text(properties.get("documentacion_faltante"), 1000),
        geometry_json=geometry_json,
    )


def _normalizar_cruce(
    db: Session,
    index: int,
    geometry: Any,
    properties: dict[str, Any],
    user: models.Usuario,
    contexto: dict[str, Any],
    seen: set[str],
) -> dict[str, Any]:
    if user.rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administrador puede importar cruces operativos.")
    id_tramo = _int_context(contexto, "id_tramo")
    id_nucleo = _int_or_none(properties.get("id_nucleo")) or _int_context(contexto, "id_nucleo")
    _tramo_activo(db, id_tramo)
    _nucleo_activo(db, id_nucleo)
    consecutivo = _int_or_none(properties.get("consecutivo"))
    if consecutivo is None or consecutivo <= 0:
        raise HTTPException(status_code=400, detail="consecutivo debe ser mayor que cero.")
    numero_tramo = _optional_text(properties.get("numero_tramo"), 50)
    longitud_m = _decimal_optional(properties.get("longitud_m"), "longitud_m")
    if longitud_m is not None and longitud_m < 0:
        raise HTTPException(status_code=400, detail="longitud_m no puede ser negativa.")
    geometry_json = _validar_geometria(db, geometry, LINE_TYPES, "linea")
    _validar_interseccion_tramo(db, geometry_json, id_tramo)
    _validar_interseccion_nucleo(db, geometry_json, id_nucleo)

    key = f"{id_tramo}:{id_nucleo}"
    if key in seen:
        raise HTTPException(status_code=400, detail="Cruce operativo duplicado dentro del archivo.")
    seen.add(key)
    if db.query(models.TramoNucleo.id_tramo_nucleo).filter(
        models.TramoNucleo.id_tramo == id_tramo,
        models.TramoNucleo.id_nucleo == id_nucleo,
        models.TramoNucleo.activo.is_(True),
    ).first():
        raise HTTPException(status_code=409, detail="Ya existe un cruce operativo activo para ese tramo y nucleo.")
    if db.query(models.TramoNucleo.id_tramo_nucleo).filter(
        models.TramoNucleo.id_tramo == id_tramo,
        models.TramoNucleo.consecutivo == consecutivo,
        models.TramoNucleo.activo.is_(True),
    ).first():
        raise HTTPException(status_code=409, detail="Ya existe un cruce operativo activo con ese consecutivo en el tramo.")

    return _datos(
        index,
        f"Tramo {id_tramo} / nucleo {id_nucleo}",
        properties,
        geometry,
        contexto,
        id_tramo=id_tramo,
        id_nucleo=id_nucleo,
        consecutivo=consecutivo,
        numero_tramo=numero_tramo,
        longitud_m=str(longitud_m) if longitud_m is not None else None,
        geometry_json=geometry_json,
        es_expropiacion=bool(properties.get("es_expropiacion", False)),
        causa_problema=_optional_text(properties.get("causa_problema"), 1000),
        proyecto_no_afecta_uso_comun=properties.get("proyecto_no_afecta_uso_comun"),
    )


def _insertar_item(db: Session, tipo: str, datos: dict[str, Any], user: models.Usuario) -> int:
    if tipo == "tramos":
        tramo = models.Tramo(
            id_proyecto=datos["id_proyecto"],
            clave_tramo=datos["clave_tramo"],
            nombre_tramo=datos["nombre_tramo"],
            descripcion=datos["descripcion"],
            ancho_total_derecho_via_m=Decimal(datos["ancho_total_derecho_via_m"]),
            fecha_registro=datetime.now(timezone.utc).date(),
            activo=True,
            geometria_linea=_geom_expr(datos["geometry_json"]),
        )
        db.add(tramo)
        db.flush()
        if user.rol == "geografo":
            db.add(models.UsuarioTramo(
                id_usuario=user.id_usuario,
                id_tramo=tramo.id_tramo,
                fecha_asignacion=datetime.now(timezone.utc),
                activo=True,
            ))
        return tramo.id_tramo

    if tipo == "nucleos":
        nucleo = models.NucleoAgrario(
            id_municipio=datos["id_municipio"],
            nombre_nucleo=datos["nombre_nucleo"],
            tipo_nucleo=datos["tipo_nucleo"],
            comunidad_indigena=datos["comunidad_indigena"],
            residencia=datos["residencia"],
            fecha_creacion=datetime.now(timezone.utc),
            activo=True,
            geometria_poligono=_geom_expr(datos["geometry_json"]),
        )
        db.add(nucleo)
        db.flush()
        return nucleo.id_nucleo

    if tipo == "derecho_via":
        return _insertar_franja(db, datos, user.id_usuario)

    if tipo == "parcelas":
        parcela = models.Parcela(
            id_nucleo=datos["id_nucleo"],
            tipo_parcela=datos["tipo_parcela"],
            no_parcela_ppt=datos["no_parcela_ppt"],
            certificado_parcelario=datos["certificado_parcelario"],
            folio_derechos=datos["folio_derechos"],
            constancia_vigencia_fecha=_date_optional(datos["constancia_vigencia_fecha"]),
            documentacion_disponible=datos["documentacion_disponible"],
            documentacion_faltante=datos["documentacion_faltante"],
            activo=True,
            geometria_poligono=_geom_expr(datos["geometry_json"]),
        )
        db.add(parcela)
        db.flush()
        return parcela.id_parcela

    cruce = models.TramoNucleo(
        id_tramo=datos["id_tramo"],
        id_nucleo=datos["id_nucleo"],
        consecutivo=datos["consecutivo"],
        numero_tramo=datos["numero_tramo"],
        longitud_m=Decimal(datos["longitud_m"]) if datos["longitud_m"] is not None else None,
        es_expropiacion=datos["es_expropiacion"],
        causa_problema=datos["causa_problema"],
        proyecto_no_afecta_uso_comun=datos["proyecto_no_afecta_uso_comun"],
        activo=True,
        geometria_segmento=_geom_expr(datos["geometry_json"]),
    )
    db.add(cruce)
    db.flush()
    return cruce.id_tramo_nucleo


def _insertar_franja(db: Session, datos: dict[str, Any], user_id: int) -> int:
    tramo = db.query(models.Tramo).filter(
        models.Tramo.id_tramo == datos["id_tramo"],
        models.Tramo.activo.is_(True),
    ).with_for_update().first()
    if tramo is None:
        raise HTTPException(status_code=404, detail="Tramo no encontrado")

    siguiente_version = (
        db.query(func.coalesce(func.max(models.FranjaDerechoVia.version), 0) + 1)
        .filter(models.FranjaDerechoVia.id_tramo == datos["id_tramo"])
        .scalar()
    )
    actual = db.query(models.FranjaDerechoVia).filter(
        models.FranjaDerechoVia.id_tramo == datos["id_tramo"],
        models.FranjaDerechoVia.activo.is_(True),
    ).with_for_update().first()
    fecha_inicio = _date_value(datos["fecha_vigencia_inicio"])
    if actual:
        if fecha_inicio < actual.fecha_vigencia_inicio:
            raise HTTPException(status_code=400, detail="La nueva vigencia no puede iniciar antes que la version activa.")
        actual.activo = False
        actual.fecha_baja = datetime.now(timezone.utc)
        actual.id_usuario_baja = user_id
        actual.motivo_baja = "Sustituida por nueva version importada."
        actual.fecha_vigencia_fin = fecha_inicio

    franja = models.FranjaDerechoVia(
        id_tramo=datos["id_tramo"],
        version=siguiente_version,
        ancho_izquierdo_m=Decimal(datos["ancho_izquierdo_m"]) if datos["ancho_izquierdo_m"] else None,
        ancho_derecho_m=Decimal(datos["ancho_derecho_m"]) if datos["ancho_derecho_m"] else None,
        fuente=datos["fuente"],
        fecha_vigencia_inicio=fecha_inicio,
        activo=True,
        geometria_poligono=_geom_expr(datos["geometry_json"]),
    )
    db.add(franja)
    db.flush()
    return franja.id_franja


def _validar_geometria(
    db: Session,
    geometry: Any,
    allowed_types: set[str],
    label: str,
    ids_tramo_contexto: list[int] | None = None,
) -> str:
    if not isinstance(geometry, dict) or geometry.get("type") not in allowed_types:
        raise HTTPException(status_code=400, detail=f"La geometria debe ser {', '.join(sorted(allowed_types))}.")
    geometry_json = json.dumps(geometry, separators=(",", ":"))
    try:
        result = db.execute(
            text(
                """
                WITH entrada AS (
                    SELECT ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326) AS geom
                )
                SELECT ST_IsValid(geom) AS valida,
                       NOT ST_IsEmpty(geom) AS no_vacia,
                       ST_GeometryType(geom) AS tipo,
                       CASE
                           WHEN :validar_contexto THEN EXISTS (
                               SELECT 1
                                 FROM franja_derecho_via f
                                 JOIN tramo t ON t.id_tramo = f.id_tramo
                                WHERE f.id_tramo = ANY(:ids_tramo)
                                  AND f.activo = TRUE
                                  AND t.activo = TRUE
                                  AND ST_Intersects(geom, f.geometria_poligono)
                                  AND ST_Area(
                                      ST_CollectionExtract(
                                          ST_Intersection(geom, f.geometria_poligono),
                                          3
                                      )::geography
                                  ) > 0
                           )
                           ELSE TRUE
                       END AS intersecta_contexto
                  FROM entrada
                """
            ),
            {
                "geometry": geometry_json,
                "validar_contexto": bool(ids_tramo_contexto),
                "ids_tramo": ids_tramo_contexto or [0],
            },
        ).mappings().one()
    except DBAPIError as exc:
        raise HTTPException(status_code=400, detail="Geometria GeoJSON invalida.") from exc
    postgis_allowed = {"ST_" + kind for kind in allowed_types}
    if not result["valida"] or not result["no_vacia"] or result["tipo"] not in postgis_allowed:
        raise HTTPException(status_code=400, detail=f"La geometria de {label} es invalida o esta vacia.")
    if not result["intersecta_contexto"]:
        raise HTTPException(
            status_code=400,
            detail="La geometria no tiene superficie de interseccion con la franja activa de los tramos seleccionados.",
        )
    return geometry_json


def _validar_interseccion_tramo(db: Session, geometry_json: str, id_tramo: int) -> None:
    result = db.execute(
        text(
            """
            SELECT ST_Intersects(ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326), geometria_linea)
              FROM tramo
             WHERE id_tramo = :id_tramo
               AND activo = TRUE
               AND geometria_linea IS NOT NULL
            """
        ),
        {"geometry": geometry_json, "id_tramo": id_tramo},
    ).scalar()
    if result is not True:
        raise HTTPException(status_code=400, detail="La geometria no intersecta con el tramo seleccionado.")


def _validar_interseccion_nucleo(db: Session, geometry_json: str, id_nucleo: int) -> None:
    result = db.execute(
        text(
            """
            SELECT ST_Intersects(ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326), geometria_poligono)
              FROM nucleo_agrario
             WHERE id_nucleo = :id_nucleo
               AND activo = TRUE
               AND geometria_poligono IS NOT NULL
            """
        ),
        {"geometry": geometry_json, "id_nucleo": id_nucleo},
    ).scalar()
    if result is not True:
        raise HTTPException(status_code=400, detail="La geometria no intersecta con el nucleo seleccionado.")


def _geom_expr(geometry_json: str):
    return func.ST_Multi(func.ST_SetSRID(func.ST_GeomFromGeoJSON(geometry_json), 4326))


def _datos(
    index: int,
    resumen: str,
    properties: dict[str, Any],
    geometry: Any,
    contexto: dict[str, Any],
    advertencias: list[str] | None = None,
    **values: Any,
) -> dict[str, Any]:
    values["resumen"] = resumen
    values["properties"] = properties
    values["geometry"] = geometry
    values["contexto"] = contexto
    values["advertencias"] = advertencias or []
    values["index"] = index
    return values


def _preview_response(
    tipo: str,
    archivo_sha256: str,
    items: list[schemas.ImportacionTerritorialPreviewItem],
) -> schemas.ImportacionTerritorialPreviewResponse:
    return schemas.ImportacionTerritorialPreviewResponse(
        tipo=tipo,
        archivo_sha256=archivo_sha256,
        total=len(items),
        validos=sum(1 for item in items if item.estado != "error"),
        errores=sum(1 for item in items if item.estado == "error"),
        advertencias=sum(1 for item in items if item.estado == "advertencia"),
        items=items,
    )


def _item_error(index: int, motivo: str) -> schemas.ImportacionTerritorialPreviewItem:
    return schemas.ImportacionTerritorialPreviewItem(
        index=index,
        estado="error",
        resumen=f"Feature {index}",
        errores=[motivo],
    )


def _text(value: Any, max_len: int, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(status_code=400, detail=f"{field} es obligatorio.")
    value = value.strip()
    if len(value) > max_len:
        raise HTTPException(status_code=400, detail=f"{field} excede {max_len} caracteres.")
    return value


def _normalizar_clave(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return "".join(char for char in ascii_value.lower() if char.isalnum())


def _property(properties: dict[str, Any], *aliases: str):
    aliases_normalizados = {_normalizar_clave(alias) for alias in aliases}
    for key, value in properties.items():
        if key in aliases:
            return value
        if _normalizar_clave(key) in aliases_normalizados:
            return value
    return None


def _normalizar_tipo_nucleo(value: Any) -> str | None:
    normalized = _normalizar_clave(value)
    if normalized in {"ejido", "ej", "e"}:
        return "ejido"
    if normalized in {"comunidad", "comunidadagraria", "com", "c"}:
        return "comunidad"
    return None


def _optional_text(value: Any, max_len: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return None
    if len(value) > max_len:
        raise HTTPException(status_code=400, detail=f"El texto excede {max_len} caracteres.")
    return value


def _int_context(contexto: dict[str, Any], key: str) -> int:
    value = _int_or_none(contexto.get(key))
    if value is None:
        raise HTTPException(status_code=400, detail=f"{key} es obligatorio.")
    return value


def _ids_context(contexto: dict[str, Any], key: str) -> list[int]:
    raw = contexto.get(key) or []
    if isinstance(raw, str):
        raw = [raw]
    ids = []
    for value in raw:
        parsed = _int_or_none(value)
        if parsed is not None:
            ids.append(parsed)
    return list(dict.fromkeys(ids))


def _int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _decimal_optional(value: Any, field: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{field} debe ser numerico.") from exc
    if parsed <= 0:
        raise HTTPException(status_code=400, detail=f"{field} debe ser mayor que cero.")
    return parsed


def _date_value(value: Any) -> date:
    parsed = _date_optional(value)
    if parsed is None:
        raise HTTPException(status_code=400, detail="fecha_vigencia_inicio es obligatoria.")
    return parsed


def _date_optional(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="La fecha debe tener formato YYYY-MM-DD.") from exc


def _proyecto_activo(db: Session, id_proyecto: int) -> models.Proyecto:
    proyecto = db.query(models.Proyecto).filter(
        models.Proyecto.id_proyecto == id_proyecto,
        models.Proyecto.activo.is_(True),
    ).first()
    if proyecto is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return proyecto


def _tramo_activo(db: Session, id_tramo: int) -> models.Tramo:
    tramo = db.query(models.Tramo).filter(
        models.Tramo.id_tramo == id_tramo,
        models.Tramo.activo.is_(True),
    ).first()
    if tramo is None:
        raise HTTPException(status_code=404, detail="Tramo no encontrado")
    return tramo


def _nucleo_activo(db: Session, id_nucleo: int) -> models.NucleoAgrario:
    nucleo = db.query(models.NucleoAgrario).filter(
        models.NucleoAgrario.id_nucleo == id_nucleo,
        models.NucleoAgrario.activo.is_(True),
    ).first()
    if nucleo is None:
        raise HTTPException(status_code=404, detail="Nucleo agrario no encontrado")
    return nucleo


def _municipio_activo_id(db: Session, id_municipio: Any) -> int | None:
    if isinstance(id_municipio, bool):
        return None
    try:
        valor = int(id_municipio)
    except (TypeError, ValueError):
        return None
    exists = db.query(models.Municipio.id_municipio).filter(
        models.Municipio.id_municipio == valor,
        models.Municipio.activo.is_(True),
    ).first()
    return valor if exists else None


def _municipio_activo(db: Session, id_municipio: int) -> None:
    exists = _municipio_activo_id(db, id_municipio)
    if exists is None:
        raise HTTPException(status_code=400, detail="id_municipio no existe o esta inactivo.")


def _municipio_por_nombre(
    db: Session,
    municipio_nombre: Any,
    entidad_nombre: Any = None,
    id_entidad: Any = None,
) -> int | None:
    if not isinstance(municipio_nombre, str) or not municipio_nombre.strip():
        return None
    municipio_key = _normalizar_clave(municipio_nombre)
    entidad_key = _normalizar_clave(entidad_nombre) if entidad_nombre else None
    query = db.query(
        models.Municipio.id_municipio,
        models.Municipio.nombre,
        models.EntidadFederativa.nombre.label("entidad_nombre"),
    ).join(
        models.EntidadFederativa,
        models.EntidadFederativa.id_entidad == models.Municipio.id_entidad,
    ).filter(
        models.Municipio.activo.is_(True),
        models.EntidadFederativa.activo.is_(True),
    )
    id_entidad_int = _entidad_activa(db, id_entidad)
    if id_entidad_int is not None:
        query = query.filter(models.Municipio.id_entidad == id_entidad_int)
    rows = query.all()
    matches = [
        row.id_municipio
        for row in rows
        if _normalizar_clave(row.nombre) == municipio_key
        and (not entidad_key or _normalizar_clave(row.entidad_nombre) == entidad_key)
    ]
    return matches[0] if len(matches) == 1 else None


def _entidad_activa(db: Session, id_entidad: Any) -> int | None:
    if isinstance(id_entidad, bool):
        return None
    try:
        valor = int(id_entidad)
    except (TypeError, ValueError):
        return None
    exists = db.query(models.EntidadFederativa.id_entidad).filter(
        models.EntidadFederativa.id_entidad == valor,
        models.EntidadFederativa.activo.is_(True),
    ).first()
    return valor if exists else None


def _resolver_nucleo_contexto(db: Session, user: models.Usuario, contexto: dict[str, Any]) -> int:
    id_tramo_nucleo = _int_or_none(contexto.get("id_tramo_nucleo"))
    if id_tramo_nucleo is not None:
        cruce = require_tramo_nucleo_access(db, user, id_tramo_nucleo)
        return cruce.id_nucleo
    id_nucleo = _int_context(contexto, "id_nucleo")
    require_nucleo_access(db, user, id_nucleo)
    _nucleo_activo(db, id_nucleo)
    return id_nucleo
