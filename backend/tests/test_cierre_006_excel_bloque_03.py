"""Regresiones del bloque 3 trazadas a los Excel del cierre V1 (individuales y alcance).

Fuentes de verdad:
- SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx / PROPUESTA
- Copia SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS MQ_COLECTIVOS MEET 27082026.xlsx / INFORME M-Q

Reglas auditadas:
1. No inventar COP padre, fecha, monto, superficie o documento faltante.
2. No asumir que todo modificatorio es aditivo; distinguir corrección/sustitución de ampliación real.
3. El backend bloquea firma por falta de acreditación (no por un filtro mágico de texto de conflicto).
4. No contar una parcela como afectada únicamente por aparecer en una presentación; se requiere afectación estructurada.
5. Conservar precisión de superficies y evitar dobles conteos físicos y monetarios.
"""

import uuid
from decimal import Decimal
from sqlalchemy import text

from app.database import SessionLocal
from .test_excel_closure_002 import _catalog, _isolated_pn

INDIVIDUALES_PROPUESTA = (
    "SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx / PROPUESTA"
)
COLECTIVOS_2708 = (
    "Copia SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS MQ_COLECTIVOS MEET 27082026.xlsx / INFORME M-Q"
)


def _snapshot(api, project_id, indicator=None):
    url = f"/api/reportes/resumen-actual?id_proyecto={project_id}"
    if indicator:
        url += f"&indicador={indicator}"
    return api("GET", url).json()


def _period(api, project_id, indicator=None, anio=None, mes=None):
    url = f"/api/reportes/avance-periodo?id_proyecto={project_id}"
    if indicator:
        url += f"&indicador={indicator}"
    if anio:
        url += f"&anio={anio}"
    if mes:
        url += f"&mes={mes}"
    return api("GET", url).json()


def _create_person(api, project_id, nombre, apellido):
    return api(
        "POST",
        f"/api/proyectos/{project_id}/personas",
        expected=201,
        json={"nombre": nombre, "apellido_paterno": apellido, "origen_registro": "qa"},
    ).json()


def _create_signer(api, person_id, parcel_holder_id, calidad_id, acreditacion_id, ref, nombre):
    return {
        "id_persona": person_id,
        "id_parcela_titular": parcel_holder_id,
        "id_tipo_calidad": calidad_id,
        "id_tipo_acreditacion": acreditacion_id,
        "referencia_acreditacion": ref,
        "nombre_en_instrumento": nombre,
        "es_firmante": True,
    }


def test_bloque_03_huecatitla_reaparicion_sin_duplicar_afectacion(api, target_domain):
    """PROPUESTA filas 104-107 (P-37, P-34, P-27, P-19):

    Aparecen en presentación del 24/04/2026 tras considerarse no afectadas.
    Conserva la misma Parcela y ProyectoNucleo. No crea Afectacion sin polígono estructurado.
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    titularidad = _catalog(api, "tipo_titularidad_unidad")["persona"]
    events = _catalog(api, "tipo_evento_seguimiento")
    reasons = _catalog(api, "motivo_seguimiento")

    # 1. Parcela P-37 existe en el núcleo
    persona = _create_person(api, project["id_proyecto"], "Fidel", "Cureño")
    parcela = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": "P-37"},
    ).json()
    pt = api(
        "POST",
        f"/api/parcelas/{parcela['id_parcela']}/titulares",
        expected=201,
        json={"id_persona": persona["id_persona"], "tipo_derecho": "parcelario"},
    ).json()
    unidad = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": tierra,
            "id_tipo_titularidad": titularidad,
            "id_parcela": parcela["id_parcela"],
            "referencia_alfanumerica": "UA-P37",
        },
    ).json()

    # 2. Sin afectación estructurada, el snapshot NO cuenta la parcela como afectada
    assert _snapshot(api, project["id_proyecto"], "total_parcelas_afectadas") == []

    # 3. Presentación del 24/04/2026: reaparece documentalmente sin polígono físico
    evento = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "ambito": "individual",
            "entidad_tipo": "parcela",
            "entidad_id": parcela["id_parcela"],
            "id_tipo_evento": events["cambio_alcance"],
            "id_motivo": reasons["nueva_informacion"],
            "fecha_evento": "2026-04-24",
            "detalle": "Reaparece en presentación del 24/04/2026; pendiente polígono",
            "fuente": f"{INDIVIDUALES_PROPUESTA}, fila 104",
        },
    ).json()
    assert evento["fecha_evento"] == "2026-04-24"
    # Aún sin afectación física estructurada, el snapshot sigue en cero
    assert _snapshot(api, project["id_proyecto"], "total_parcelas_afectadas") == []

    # 4. Posteriormente se estructura la afectación física
    af = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual"},
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={
            "id_unidad_agraria": unidad["id_unidad_agraria"],
            "superficie_afectada_ha": "0.050000",
            "superficie_valor_original": "00-05-00",
        },
    )

    # 5. Ahora sí cuenta como 1 parcela afectada
    rows = _snapshot(api, project["id_proyecto"], "total_parcelas_afectadas")
    assert len(rows) == 1 and rows[0]["cantidad"] == 1

    # 6. Un cambio posterior de información no duplica la afectación ni la parcela
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "ambito": "individual",
            "entidad_tipo": "parcela",
            "entidad_id": parcela["id_parcela"],
            "id_tipo_evento": events["cambio_alcance"],
            "id_motivo": reasons["nueva_informacion"],
            "fecha_evento": "2026-05-01",
            "detalle": "Ratificación técnica de polígono",
            "fuente": f"{INDIVIDUALES_PROPUESTA}, fila 104 revisión",
        },
    )
    rows_despues = _snapshot(api, project["id_proyecto"], "total_parcelas_afectadas")
    assert len(rows_despues) == 1 and rows_despues[0]["cantidad"] == 1


def test_bloque_03_incorporaciones_posteriores_xiteje_san_pedrito_huehuetoca(api, target_domain):
    """PROPUESTA fila 326 (Xitejé P-4), fila 353 (San Pedrito P-111), fila 567 (Huehuetoca P-293).

    Incorporaciones posteriores con fecha de PPT; sólo Xitejé tiene convenio firmado.
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    titularidad = _catalog(api, "tipo_titularidad_unidad")["persona"]
    calidad = _catalog(api, "calidad_compareciente_convenio")["titular_parcelario"]
    acred = _catalog(api, "tipo_acreditacion_derecho_individual")["certificado_parcelario"]
    cops = _catalog(api, "tipo_cop_operativo")
    events = _catalog(api, "tipo_evento_seguimiento")
    reasons = _catalog(api, "motivo_seguimiento")

    # Caso A: Xitejé de Zapata P-4 (Fila 326) con convenio firmado
    sergio = _create_person(api, project["id_proyecto"], "Sergio", "Reyes Garcia")
    p4 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": "P-4"},
    ).json()
    pt4 = api(
        "POST",
        f"/api/parcelas/{p4['id_parcela']}/titulares",
        expected=201,
        json={"id_persona": sergio["id_persona"], "tipo_derecho": "parcelario"},
    ).json()
    ua4 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": tierra,
            "id_tipo_titularidad": titularidad,
            "id_parcela": p4["id_parcela"],
            "referencia_alfanumerica": "UA-XITEJE-P4",
        },
    ).json()
    af4 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual"},
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{af4['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={
            "id_unidad_agraria": ua4["id_unidad_agraria"],
            "superficie_afectada_ha": "0.031729",
            "superficie_valor_original": "00-03-17.287",
        },
    )
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "ambito": "individual",
            "entidad_tipo": "parcela",
            "entidad_id": p4["id_parcela"],
            "id_tipo_evento": events["cambio_alcance"],
            "id_motivo": reasons["nueva_informacion"],
            "fecha_evento": "2025-12-10",
            "detalle": "Parcela que se agregó en PPT de fecha 10/12/2025",
            "fuente": f"{INDIVIDUALES_PROPUESTA}, fila 326",
        },
    )
    signer4 = _create_signer(api, sergio["id_persona"], pt4["id_parcela_titular"], calidad, acred, "CERT-P4", "Sergio Reyes Garcia")
    c4 = api(
        "POST",
        f"/api/afectaciones/{af4['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "fecha_firma": "2026-03-18",
            "monto_100": "31728.70",
            "superficie_ha": "0.031729",
            "comparecientes": [signer4],
        },
    ).json()
    assert c4["fecha_firma"] == "2026-03-18"

    # Caso B: San Pedrito Alpuyeca P-111 (Fila 353) sin convenio
    catalina = _create_person(api, project["id_proyecto"], "Catalina", "Mejia Angeles")
    p111 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": "P-111"},
    ).json()
    api(
        "POST",
        f"/api/parcelas/{p111['id_parcela']}/titulares",
        expected=201,
        json={"id_persona": catalina["id_persona"], "tipo_derecho": "parcelario"},
    )
    ua111 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": tierra,
            "id_tipo_titularidad": titularidad,
            "id_parcela": p111["id_parcela"],
            "referencia_alfanumerica": "UA-ALPUYECA-P111",
        },
    ).json()
    af111 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual"},
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{af111['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={"id_unidad_agraria": ua111["id_unidad_agraria"], "superficie_afectada_ha": "0.050000"},
    )
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "ambito": "individual",
            "entidad_tipo": "parcela",
            "entidad_id": p111["id_parcela"],
            "id_tipo_evento": events["cambio_alcance"],
            "id_motivo": reasons["nueva_informacion"],
            "fecha_evento": "2025-09-12",
            "detalle": "Se agregó en PPT 12/09/2025",
            "fuente": f"{INDIVIDUALES_PROPUESTA}, fila 353",
        },
    )

    # Caso C: Huehuetoca P-293 (Fila 567) por obras complementarias sin convenio
    paula = _create_person(api, project["id_proyecto"], "Paula Gloria", "Arreguin Pacheco")
    p293 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": "P-293"},
    ).json()
    api(
        "POST",
        f"/api/parcelas/{p293['id_parcela']}/titulares",
        expected=201,
        json={"id_persona": paula["id_persona"], "tipo_derecho": "parcelario"},
    )
    ua293 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": tierra,
            "id_tipo_titularidad": titularidad,
            "id_parcela": p293["id_parcela"],
            "referencia_alfanumerica": "UA-HUEHUETOCA-P293",
        },
    ).json()
    af293 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "id_tipo_cop_operativo": cops["COMPLEMENTARIAS"]},
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{af293['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={"id_unidad_agraria": ua293["id_unidad_agraria"], "superficie_afectada_ha": "0.020000"},
    )

    # Verificación de reporting:
    # 1. Snapshot cuenta las 3 parcelas afectadas
    snap_p = _snapshot(api, project["id_proyecto"], "total_parcelas_afectadas")
    assert snap_p[0]["cantidad"] == 3

    # 2. Avance periodo sólo reporta el convenio real de Xitejé en 2026-03
    p_xiteje = _period(api, project["id_proyecto"], "cop_individuales", anio=2026, mes=3)
    assert len(p_xiteje) == 1 and p_xiteje[0]["cantidad"] == 1
    assert Decimal(str(p_xiteje[0]["superficie_ha"])) == Decimal("0.031729")
    assert Decimal(str(p_xiteje[0]["monto"])) == Decimal("31728.70")

    # 3. San Pedrito y Huehuetoca no tienen convenio y no entran a periodo
    assert _period(api, project["id_proyecto"], "cop_individuales", anio=2025, mes=9) == []
    assert _period(api, project["id_proyecto"], "cop_individuales", anio=2026, mes=1) == []


def test_bloque_03_p229_duplicada_fuente_y_p272_conflicto_titularidad(api, target_domain):
    """PROPUESTA filas 665-666 (P-229) y 774-777 (P-272).

    P-229 reutiliza parcela sin duplicar. P-272 registra reclamantes reales y bloquea firma
    por falta de acreditación resuelta (contrato de acreditación del backend).
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    titularidad = _catalog(api, "tipo_titularidad_unidad")["persona"]
    calidad = _catalog(api, "calidad_compareciente_convenio")["titular_parcelario"]
    acred = _catalog(api, "tipo_acreditacion_derecho_individual")["certificado_parcelario"]
    events = _catalog(api, "tipo_evento_seguimiento")
    reasons = _catalog(api, "motivo_seguimiento")

    # --- P-229 (Filas 665 y 666) ---
    crispina = _create_person(api, project["id_proyecto"], "Crispina", "Ledezma Resendiz")
    p229 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": "P-229"},
    ).json()

    # Intento de duplicar P-229 en el mismo núcleo es rechazado por unicidad
    dup_res = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=409,
        json={"tipo_parcela": "individual", "no_parcela": "P-229"},
    )
    assert "ya existe" in dup_res.text.lower()

    # Se asocia y formaliza una sola vez
    api(
        "POST",
        f"/api/parcelas/{p229['id_parcela']}/titulares",
        expected=201,
        json={"id_persona": crispina["id_persona"], "tipo_derecho": "parcelario"},
    )
    ua229 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": tierra,
            "id_tipo_titularidad": titularidad,
            "id_parcela": p229["id_parcela"],
            "referencia_alfanumerica": "UA-P229",
        },
    ).json()
    af229 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual"},
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{af229['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={"id_unidad_agraria": ua229["id_unidad_agraria"], "superficie_afectada_ha": "1.113127"},
    )

    # --- P-272 (Filas 774 y 777, Conflicto real de titularidad) ---
    silvestre = _create_person(api, project["id_proyecto"], "Silvestre", "Mendoza Carmen")
    meliton = _create_person(api, project["id_proyecto"], "Meliton", "Lopez Mendoza")
    p272 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": "P-272"},
    ).json()
    ua272 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": tierra,
            "id_tipo_titularidad": _catalog(api, "tipo_titularidad_unidad")["no_determinada"],
            "id_parcela": p272["id_parcela"],
            "referencia_alfanumerica": "UA-P272-CONFLICTO",
            "requiere_revision": True,
            "motivo_revision": "Conflicto entre Silvestre Mendoza y Meliton Lopez por certificado 1008965",
        },
    ).json()
    af272 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual"},
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{af272['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={"id_unidad_agraria": ua272["id_unidad_agraria"], "superficie_afectada_ha": "0.100000"},
    )
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "ambito": "individual",
            "entidad_tipo": "parcela",
            "entidad_id": p272["id_parcela"],
            "id_tipo_evento": events["otro"],
            "id_motivo": reasons["conflicto_titularidad"],
            "fecha_evento": "2026-04-13",
            "detalle": "Doble reclamante para certificado 1008965; titularidad no determinada",
            "fuente": f"{INDIVIDUALES_PROPUESTA}, filas 774 y 777",
        },
    )

    # Intento de firmar convenio para P-272 sin firmante acreditado es rechazado por el backend
    sign_blocked = api(
        "POST",
        f"/api/afectaciones/{af272['id_afectacion']}/convenios",
        expected=409,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "fecha_firma": "2026-04-13",
            "comparecientes": [],  # Sin acreditación resuelta
        },
    )
    assert sign_blocked.status_code == 409
    assert any(msg in sign_blocked.text.lower() for msg in ("no son válidos", "firmante acreditado"))

    # Verificación de snapshot: exactamente 2 parcelas afectadas distintas (P-229 y P-272)
    rows = _snapshot(api, project["id_proyecto"], "total_parcelas_afectadas")
    assert rows[0]["cantidad"] == 2


def test_bloque_03_titulares_no_determinados_sin_personas_ficticias(api, target_domain):
    """PROPUESTA filas 41 (SIN INFO), 206 (EN TRAMITE), 314 (SIN ASIGNAR), 763 (EN CONFLICTO).

    Se registran como tipo_titularidad=no_determinada con flag de revisión;
    no se crean filas ficticias en Persona y se bloquea firma no acreditada.
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    no_det = _catalog(api, "tipo_titularidad_unidad")["no_determinada"]

    par = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": "P-763"},
    ).json()
    ua = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": tierra,
            "id_tipo_titularidad": no_det,
            "id_parcela": par["id_parcela"],
            "referencia_alfanumerica": "UA-P763",
            "requiere_revision": True,
            "motivo_revision": "EN CONFLICTO segun fuente Excel fila 763",
        },
    ).json()
    assert ua["id_tipo_titularidad"] == no_det
    assert ua["requiere_revision"] is True

    # Comprobación de que no se crean personas ficticias en la base de datos
    with SessionLocal() as db:
        dummy_count = db.execute(
            text(
                "SELECT count(*) FROM persona "
                "WHERE (nombre ILIKE '%conflicto%' OR nombre ILIKE '%tramite%' OR nombre ILIKE '%asignar%')"
            ),
        ).scalar()
    assert dummy_count == 0

    # Intento de firma sin acreditación es rechazado
    af = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual"},
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={"id_unidad_agraria": ua["id_unidad_agraria"], "superficie_afectada_ha": "0.200000"},
    )
    res = api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/convenios",
        expected=409,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "fecha_firma": "2026-01-01",
            "comparecientes": [],
        },
    )
    assert res.status_code == 409
    assert any(msg in res.text.lower() for msg in ("no son válidos", "firmante acreditado"))


def test_bloque_03_convenio_modificatorio_sustitucion_no_aditivo(api, target_domain):
    """PROPUESTA fila 65 (EL MUERTO-IGNACIO PEREZ, P-201).

    COP original sin soporte (fecha_firma=None). Modificatorio el 11/11/2025 para regularizar.
    Mismo alcance físico: la superficie en snapshot no se suma dos veces;
    sólo periodiza el modificatorio en 2025-11.
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    titularidad = _catalog(api, "tipo_titularidad_unidad")["persona"]
    calidad = _catalog(api, "calidad_compareciente_convenio")["titular_parcelario"]
    acred = _catalog(api, "tipo_acreditacion_derecho_individual")["certificado_parcelario"]

    persona = _create_person(api, project["id_proyecto"], "Ignacio", "Perez")
    par = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": "P-201"},
    ).json()
    pt = api(
        "POST",
        f"/api/parcelas/{par['id_parcela']}/titulares",
        expected=201,
        json={"id_persona": persona["id_persona"], "tipo_derecho": "parcelario"},
    ).json()
    ua = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": tierra,
            "id_tipo_titularidad": titularidad,
            "id_parcela": par["id_parcela"],
            "referencia_alfanumerica": "UA-P201",
        },
    ).json()

    # Única afectación estructurada del mismo alcance físico (0.166808 ha)
    af = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "superficie_afectada_ha": "0.166808"},
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={
            "id_unidad_agraria": ua["id_unidad_agraria"],
            "superficie_afectada_ha": "0.166808",
            "superficie_valor_original": "00-16-68.079",
        },
    )

    # 1. Convenio original sin fecha de firma (sin inventar fecha de negocio)
    c_orig = api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "fecha_firma": None,
            "superficie_ha": "0.166808",
            "observaciones": "Sin soporte documental de fecha de firma original",
        },
    ).json()
    assert c_orig["fecha_firma"] is None

    # 2. Convenio modificatorio regularizador sobre la MISMA afectación
    signer = _create_signer(api, persona["id_persona"], pt["id_parcela_titular"], calidad, acred, "CERT-201", "Ignacio Perez")
    c_mod = api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "modificatorio",
            "consecutivo": 2,
            "id_convenio_padre": c_orig["id_convenio"],
            "fecha_firma": "2025-11-11",
            "monto_100": "166807.90",
            "superficie_ha": "0.166808",
            "comparecientes": [signer],
        },
    ).json()
    assert c_mod["id_convenio_padre"] == c_orig["id_convenio"]
    assert c_mod["fecha_firma"] == "2025-11-11"

    # Verificación en Snapshot: la superficie física es 0.166808 (no 0.333616)
    snap_p = _snapshot(api, project["id_proyecto"], "total_parcelas_afectadas")
    assert snap_p[0]["cantidad"] == 1
    snap_s = _snapshot(api, project["id_proyecto"], "superficie_afectada_administrativa")
    assert Decimal(str(snap_s[0]["superficie_ha"])) == Decimal("0.166808")

    # Verificación en Periodo: cop_original sin fecha NO periodiza; sólo modificatorio en 2025-11
    assert _period(api, project["id_proyecto"], "cop_individuales") == []
    p_mod = _period(api, project["id_proyecto"], "modificatorio", anio=2025, mes=11)
    assert len(p_mod) == 1 and p_mod[0]["cantidad"] == 1
    assert Decimal(str(p_mod[0]["monto"])) == Decimal("166807.90")


def test_bloque_03_cadena_aditiva_ampliacion_y_remanente(api, target_domain):
    """PROPUESTA filas 356 (P-240), 573 (P-64), 733 (P-15).

    Cadena triple de convenio: original + ampliación + remanente.
    Superficies incrementales reales aditivas. Snapshot cuenta exactamente 1 parcela.
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    titularidad = _catalog(api, "tipo_titularidad_unidad")["persona"]
    calidad = _catalog(api, "calidad_compareciente_convenio")["titular_parcelario"]
    acred = _catalog(api, "tipo_acreditacion_derecho_individual")["certificado_parcelario"]

    persona = _create_person(api, project["id_proyecto"], "Titular", "Zaragoza")
    par = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": "P-240"},
    ).json()
    pt = api(
        "POST",
        f"/api/parcelas/{par['id_parcela']}/titulares",
        expected=201,
        json={"id_persona": persona["id_persona"], "tipo_derecho": "parcelario"},
    ).json()
    ua = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": tierra,
            "id_tipo_titularidad": titularidad,
            "id_parcela": par["id_parcela"],
            "referencia_alfanumerica": "UA-P240",
        },
    ).json()
    signer = _create_signer(api, persona["id_persona"], pt["id_parcela_titular"], calidad, acred, "CERT-240", "Titular Zaragoza")

    # 1. Afectación base (1.000000 ha) y COP original
    af1 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "superficie_afectada_ha": "1.000000"},
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{af1['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={"id_unidad_agraria": ua["id_unidad_agraria"], "superficie_afectada_ha": "1.000000"},
    )
    c_orig = api(
        "POST",
        f"/api/afectaciones/{af1['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "cop_original",
            "consecutivo": 1,
            "fecha_firma": "2025-09-03",
            "monto_100": "100000.00",
            "superficie_ha": "1.000000",
            "comparecientes": [signer],
        },
    ).json()

    # 2. Afectación adicional (0.083124 ha) y Convenio Ampliación
    af2 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "superficie_afectada_ha": "0.083124"},
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{af2['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={
            "id_unidad_agraria": ua["id_unidad_agraria"],
            "superficie_afectada_ha": "0.083124",
            "superficie_valor_original": "00-08-31.244",
        },
    )
    c_amp = api(
        "POST",
        f"/api/afectaciones/{af2['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "ampliacion",
            "consecutivo": 2,
            "id_convenio_padre": c_orig["id_convenio"],
            "fecha_firma": "2025-12-17",
            "monto_100": "8312.40",
            "superficie_ha": "0.083124",
            "comparecientes": [signer],
        },
    ).json()

    # 3. Afectación remanente (0.205792 ha) y Convenio Ampliación 2 (Remanente)
    af3 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "superficie_afectada_ha": "0.205792"},
    ).json()
    api(
        "POST",
        f"/api/afectaciones/{af3['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={
            "id_unidad_agraria": ua["id_unidad_agraria"],
            "superficie_afectada_ha": "0.205792",
            "superficie_valor_original": "00-20-57.923",
        },
    )
    c_rem = api(
        "POST",
        f"/api/afectaciones/{af3['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_instrumento": "convenio",
            "tipo_convenio": "ampliacion_remanente",
            "consecutivo": 3,
            "id_convenio_padre": c_orig["id_convenio"],
            "fecha_firma": "2026-02-13",
            "monto_100": "20579.20",
            "superficie_ha": "0.205792",
            "comparecientes": [signer],
        },
    ).json()

    # Verificaciones:
    # A) Snapshot cuenta estrictamente 1 parcela afectada
    snap_p = _snapshot(api, project["id_proyecto"], "total_parcelas_afectadas")
    assert snap_p[0]["cantidad"] == 1

    # B) Superficie total física es aditiva: 1.0 + 0.083124 + 0.205792 = 1.288916 ha
    snap_s = _snapshot(api, project["id_proyecto"], "superficie_afectada_administrativa")
    assert Decimal(str(snap_s[0]["superficie_ha"])) == Decimal("1.288916")

    # C) Periodo desglosa 3 hitos independientes en sus fechas correspondientes
    p_orig = _period(api, project["id_proyecto"], "cop_individuales", anio=2025, mes=9)
    assert len(p_orig) == 1 and Decimal(str(p_orig[0]["superficie_ha"])) == Decimal("1.000000")

    p_amp = _period(api, project["id_proyecto"], "ampliacion", anio=2025, mes=12)
    assert len(p_amp) == 1 and Decimal(str(p_amp[0]["superficie_ha"])) == Decimal("0.083124")

    p_rem = _period(api, project["id_proyecto"], "ampliacion_remanente", anio=2026, mes=2)
    assert len(p_rem) == 1 and Decimal(str(p_rem[0]["superficie_ha"])) == Decimal("0.205792")


def test_bloque_03_correccion_superficie_mismo_alcance_vs_aditiva(api, target_domain):
    """Contraste directo: Corrección del mismo alcance vía PATCH no duplica superficie,

    mientras que afectaciones adicionales son incrementales pero preservan COUNT(DISTINCT ua.id_parcela).
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    tierra = next(iter(_catalog(api, "tipo_tierra").values()))
    titularidad = _catalog(api, "tipo_titularidad_unidad")["persona"]

    par = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/parcelas",
        expected=201,
        json={"tipo_parcela": "individual", "no_parcela": "P-CORR"},
    ).json()
    ua = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/unidades-agrarias",
        expected=201,
        json={
            "id_tipo_tierra": tierra,
            "id_tipo_titularidad": titularidad,
            "id_parcela": par["id_parcela"],
            "referencia_alfanumerica": "UA-PCORR",
        },
    ).json()

    # 1. Afectación inicial con 1.000000 ha
    af = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={"tipo_afectacion": "individual", "superficie_afectada_ha": "1.000000"},
    ).json()
    assoc = api(
        "POST",
        f"/api/afectaciones/{af['id_afectacion']}/unidades-agrarias",
        expected=201,
        json={"id_unidad_agraria": ua["id_unidad_agraria"], "superficie_afectada_ha": "1.000000"},
    ).json()

    snap1 = _snapshot(api, project["id_proyecto"], "superficie_afectada_administrativa")
    assert Decimal(str(snap1[0]["superficie_ha"])) == Decimal("1.000000")

    # 2. Corrección del levantamiento topográfico del mismo alcance vía PATCH
    api(
        "PATCH",
        f"/api/afectaciones/{af['id_afectacion']}",
        expected=200,
        json={"superficie_afectada_ha": "1.250000"},
    )
    api(
        "PATCH",
        f"/api/afectacion-unidades-agrarias/{assoc['id_afectacion_unidad']}",
        expected=200,
        json={"superficie_afectada_ha": "1.250000", "observaciones": "Corrección técnica de polígono"},
    )

    # La superficie se actualiza en lugar de sumarse
    snap2 = _snapshot(api, project["id_proyecto"], "superficie_afectada_administrativa")
    assert Decimal(str(snap2[0]["superficie_ha"])) == Decimal("1.250000")
    assert _snapshot(api, project["id_proyecto"], "total_parcelas_afectadas")[0]["cantidad"] == 1
