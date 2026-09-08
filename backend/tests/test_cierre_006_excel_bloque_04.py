"""Regresiones del bloque 4 trazadas a los Excel del cierre V1 (Asambleas y Convocatorias).

Fuentes de verdad auditadas:
- Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx / ASAMBLEAS PENDIENTES, INFORME M-Q, PCOLECTIVAS
- Copia SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS MQ_COLECTIVOS MEET 27082026.xlsx / INFORME M-Q, RESUMEN
- PROYECTOS VÍAS SEGUIMIENTO GENERAL.xlsx / INFORME GENERAL, COP´S COLECTIVOS
- SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx / PROPUESTA, COP´S PENDIENTES, Hoja1

Marco Jurídico Agrario y Administrativo Aplicable:
1. Ley Agraria arts. 23-28 y 95:
   - Art. 23 fracc. II: Asambleas de formalidades simples para asuntos de interés ejidal (servidumbres ordinarias y ocupaciones que no asignan ni delimitan tierras).
   - Art. 23 fracc. IX y Art. 28: Asambleas de formalidades especiales (quórum calificado de 3/4 en 1a o 2/3 en ulterior convocatoria, presencia de fedatario público y representante de la Procuraduría Agraria) aplicables obligatoriamente cuando la asamblea asigna, delimita o destina solares urbanos a favor del ejido (caso San Sebastián de las Barrancas).
   - Art. 24 y 25: Convocatorias y cédulas de fijación. Una convocatoria emitida sin la debida publicación en estrados queda sin efecto legal (cancelada; no constituye acto no verificativo al no haberse instalado la mesa de asamblea ni computado quórum).
   - Art. 26 y 27: Reglas generales de quórum e instalación.
2. Reglamento de la Ley Agraria en Materia de Certificación de Derechos Ejidales y Titulación de Solares (REG-REGISTRAL) art. 13 y Lineamientos de la Procuraduría Agraria 2025 (reforma 29/05/2026):
   - Regula expresamente la instalación y declaración de Asamblea en Sesión Permanente y sus recesos. Las continuaciones forman parte del mismo acto jurídico y no constituyen asambleas distintas ni requieren nueva convocatoria general.
3. Desistimiento Administrativo Registral ante el RAN:
   - Ley Federal de Procedimiento Administrativo (LFPA) arts. 13, 48, 57 fracción I y 63 (de aplicación supletoria al Registro Agrario Nacional en términos del artículo 2 de la LFPA). El desistimiento voluntario pone fin al procedimiento registral específico para el retiro y subsanación de documentos técnicos sin extinguir el acuerdo sustantivo de la asamblea ejidal, pero NO genera una continuidad jurídica automática del mismo trámite registral.
   - Revisión documental: La falta de acuses o soporte documental en los libros de Excel no determina la nulidad de un acto ejidal celebrado; representa una condición operativa de revisión documental.
4. Escenarios Sintéticos de Laboratorio:
   - Todo escenario de prueba no obrante en libros se identifica con códigos ficticios 'LAB-SINT-...' para evitar cualquier confusión con folios o actos registrales reales.
5. Identidad del acto frente a destinos compartidos y consulta indígena:
   - Un acta de asamblea compartida por múltiples destinos (TUC, canal, solares) computa como 1 solo acto jurídico en el indicador 'asambleas'.
   - La suspensión o reprogramación de convocatorias para desahogar consulta previa, libre e informada (Art. 2 Constitucional y Convenio 169 de la OIT) es un deber legal sustantivo.
"""

import uuid
from decimal import Decimal

from .test_excel_closure_002 import _catalog, _isolated_pn

ASAMBLEAS_PENDIENTES = (
    "Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx / ASAMBLEAS PENDIENTES"
)
INFORME_MQ_REV = (
    "Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx / INFORME M-Q"
)
INFORME_MQ_MEET = (
    "Copia SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS MQ_COLECTIVOS MEET 27082026.xlsx / INFORME M-Q"
)
PROYECTOS_VIAS_GRAL = (
    "PROYECTOS VÍAS SEGUIMIENTO GENERAL.xlsx / INFORME GENERAL"
)


def _period(api, project_id, **params):
    qs = "&".join([f"id_proyecto={project_id}", *(f"{k}={v}" for k, v in params.items())])
    return api("GET", f"/api/reportes/avance-periodo?{qs}").json()


def _dashboard(api, project_id, anio=None):
    url = f"/api/dashboard/kpi?id_proyecto={project_id}"
    if anio is not None:
        url += f"&anio={anio}"
    return {row["indicador"]: row for row in api("GET", url).json()}


def test_bloque_04_san_sebastian_juarez_no_verificativo_y_permanente(api, target_domain):
    """Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx / ASAMBLEAS PENDIENTES Fila 61.

    Núcleo: San Sebastián de Juárez (Jilotepec, Edo. Méx., Consecutivo 150422).

    1. Hechos literales del Excel:
       - 1a Convocatoria: AC61 / AD61: programada 2025-06-29, no verificativa (08/07/2025).
       - 2a Convocatoria: AC61 / AD61: programada 2025-09-17, no verificativa (28/09/2025).
       - 3a Convocatoria: AC61 / AD61 / AF61: programada 2025-10-14, celebrada 2025-10-24.
       - Declaración de asamblea permanente: Observaciones BW61 ("SE DECLARA ASAMBLEA PERMANENTE, NO ACEPTARON FIRMA DE COP").
       - Firma de COP: AV61: 2025-10-24.
    2. Contradicciones entre fuentes:
       - Ninguna respecto a convocatorias ni fecha de celebración.
    3. Datos sin soporte:
       - En los libros de Excel no obran registradas las fechas de receso o continuaciones de la sesión permanente.
    4. Escenarios sintéticos de laboratorio:
       - LAB-SINT-CONT-01 (2025-11-05) y LAB-SINT-CONT-02 (2025-11-12): continuaciones de receso
         creadas en laboratorio para validar que las prórrogas no duplican la Asamblea ni alteran los conteos.
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    proj_id = project["id_proyecto"]

    tipos_asamblea = _catalog(api, "tipo_asamblea")
    contextos = _catalog(api, "contexto_asamblea")
    cop = _catalog(api, "tipo_cop_operativo")
    resultados = _catalog(api, "resultado_convocatoria")
    eventos_seg = _catalog(api, "tipo_evento_seguimiento")

    # 1. Crear Asamblea con la 1a Convocatoria no verificativa (2025-06-29 literal)
    asamblea = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": tipos_asamblea["anuencia"],
            "id_contexto_asamblea": contextos["cop_original"],
            "id_tipo_cop_operativo": cop["ORIGEN"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2025-06-29",
                    "id_resultado": resultados["no_verificativo"],
                    "observaciones_resultado": "No verificativa por falta de quórum",
                }
            ],
        },
    ).json()
    asamblea_id = asamblea["id_asamblea"]

    # 2. Agregar 2a Convocatoria no verificativa (2025-09-17 literal)
    api(
        "POST",
        f"/api/asambleas/{asamblea_id}/convocatorias",
        expected=201,
        json={
            "ordinal": 2,
            "fecha_programada": "2025-09-17",
            "id_resultado": resultados["no_verificativo"],
            "observaciones_resultado": "Segunda convocatoria no verificativa",
        },
    )

    # 3. Agregar 3a Convocatoria celebrada (programada 2025-10-14, celebrada 2025-10-24 literal)
    api(
        "POST",
        f"/api/asambleas/{asamblea_id}/convocatorias",
        expected=201,
        json={
            "ordinal": 3,
            "fecha_programada": "2025-10-14",
            "fecha_realizacion": "2025-10-24",
            "id_resultado": resultados["celebrada"],
            "observaciones_resultado": "Celebrada válidamente; se declara asamblea permanente",
        },
    )

    # 4. Registrar continuaciones de laboratorio en SeguimientoEvento (LAB-SINT-CONT-01 y 02)
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "entidad_tipo": "asamblea",
            "entidad_id": asamblea_id,
            "ambito": "colectivo",
            "id_tipo_evento": eventos_seg["continuacion_asamblea"],
            "fecha_evento": "2025-11-05",
            "detalle": "LAB-SINT-CONT-01: 1ra Continuación asamblea permanente [SINTÉTICO AUDITADO]",
            "fuente": ASAMBLEAS_PENDIENTES,
        },
    )
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "entidad_tipo": "asamblea",
            "entidad_id": asamblea_id,
            "ambito": "colectivo",
            "id_tipo_evento": eventos_seg["continuacion_asamblea"],
            "fecha_evento": "2025-11-12",
            "detalle": "LAB-SINT-CONT-02: 2da Continuación asamblea permanente [SINTÉTICO AUDITADO]",
            "fuente": ASAMBLEAS_PENDIENTES,
        },
    )

    # Verificación de integridad estructural en API
    assemblies = api("GET", f"/api/proyecto-nucleo/{pn_id}/asambleas").json()
    assert len(assemblies) == 1, "Debe conservarse la misma y única asamblea"
    convocatorias = api("GET", f"/api/asambleas/{asamblea_id}/convocatorias").json()
    assert len(convocatorias) == 3
    assert [c["ordinal"] for c in convocatorias] == [1, 2, 3]
    assert convocatorias[0]["id_resultado"] == resultados["no_verificativo"]
    assert convocatorias[0]["fecha_realizacion"] is None
    assert convocatorias[1]["id_resultado"] == resultados["no_verificativo"]
    assert convocatorias[1]["fecha_realizacion"] is None
    assert convocatorias[2]["id_resultado"] == resultados["celebrada"]
    assert convocatorias[2]["fecha_realizacion"] == "2025-10-24"

    seguimiento = api("GET", f"/api/proyecto-nucleo/{pn_id}/seguimiento").json()
    continuaciones = [s for s in seguimiento if s["id_tipo_evento"] == eventos_seg["continuacion_asamblea"]]
    assert len(continuaciones) == 2

    # Reporte de avance por periodo
    # Junio 2025: programada (min fecha_programada = 2025-06-29), realizado = 0
    p_jun = _period(api, proj_id, anio=2025, mes=6, indicador="asambleas")
    assert len(p_jun) == 1
    assert p_jun[0]["programado"] == 1
    assert p_jun[0]["realizado"] == 0
    assert p_jun[0]["cantidad"] == 1

    # Septiembre 2025: no hay realizado
    p_sep = _period(api, proj_id, anio=2025, mes=9, indicador="asambleas")
    assert sum(r["realizado"] for r in p_sep) == 0

    # Octubre 2025: celebrada el 2025-10-24, realizado = 1
    p_oct = _period(api, proj_id, anio=2025, mes=10, indicador="asambleas")
    assert len(p_oct) == 1
    assert p_oct[0]["programado"] == 0
    assert p_oct[0]["realizado"] == 1
    assert p_oct[0]["cantidad"] == 1

    # Noviembre 2025: mes de continuaciones; NO debe generar hitos de asambleas
    p_nov = _period(api, proj_id, anio=2025, mes=11, indicador="asambleas")
    assert len(p_nov) == 0, "Las continuaciones no deben computar como asambleas"

    # Dashboard anual 2025: conteo exacto e invariante
    dash = _dashboard(api, proj_id, anio=2025)
    kpi = dash["asambleas"]
    assert kpi["programado"] == 1
    assert kpi["realizado"] == 1
    assert kpi["cantidad"] == 1, "count(DISTINCT clave_hito) debe ser 1"


def test_bloque_04_pedro_escobedo_reprogramada_desistimiento_y_retiro_fondos(api, target_domain):
    """Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx / ASAMBLEAS PENDIENTES Fila 17.

    Núcleo: Pedro Escobedo (Querétaro, Consecutivo 220218).

    1. Hechos literales del Excel:
       - 1a Convocatoria: AC17 / AC24: 2025-05-23 (no verificativa).
       - 2a Convocatoria: AD17 / AD24: programada para 2025-06-06, reprogramada formalmente
         para 2025-06-10 por error en cédula de citación (BW17 / EN24).
       - Celebración de Asamblea: AF17 / AF24: 2025-06-10.
       - Ingreso RAN de acta: AJ17 / AJ24: 2025-07-07, Solicitud AM17 / AK24: 22250006618.
       - Firma de COP: AV17 / AV24: 2025-07-10.
       - Asamblea independiente de Retiro de Fondos: DU24 / DW24: celebrada el 2025-07-31.
       - Ingreso RAN de COP: BB24: 2025-09-05, Solicitud BC24: 22250009069.
    2. Contradicciones entre fuentes:
       - REV (Fila 17 BW17 y Fila 24 EN24) registra literalmente:
         '*DESISTIMIENTO EL 10 DE JULIO 2025 EN LA INSCRIPCIÓN DE ACTAS DE ASAMBLEA QUE ESTÁN CONTABILIZADAS EN PPT'.
       - MEET (Fila 27 Col 48/51) registra: '*DESISTIMIENTO EL 10 DE JUNIO 2025'
         (discrepancia material / errata, pues antecede al ingreso al RAN del 07/07/2025).
    3. Datos sin soporte:
       - BX17 / EO24 indican falta de soporte documental de acta corregida y nuevo ingreso
         (catalogado como revisión documental).
    4. Escenarios sintéticos de laboratorio:
       - LAB-SINT-SUBSANACION: evento auxiliar del 2025-07-15 para validar el registro de subsanación técnica.
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    proj_id = project["id_proyecto"]

    tipos_asamblea = _catalog(api, "tipo_asamblea")
    contextos = _catalog(api, "contexto_asamblea")
    cop = _catalog(api, "tipo_cop_operativo")
    resultados = _catalog(api, "resultado_convocatoria")
    eventos_ran = _catalog(api, "tipo_evento_ran")

    # 1. Crear Asamblea COP original con 1a convocatoria (2025-05-23 literal)
    asamblea = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": tipos_asamblea["anuencia"],
            "id_contexto_asamblea": contextos["cop_original"],
            "id_tipo_cop_operativo": cop["ORIGEN"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2025-05-23",
                    "id_resultado": resultados["no_verificativo"],
                    "observaciones_resultado": "1a convocatoria no verificativa",
                }
            ],
        },
    ).json()
    asamblea_id = asamblea["id_asamblea"]

    # 2. Agregar 2a Convocatoria programada para 2025-06-06 y reprogramada por error en citación (literal)
    conv2 = api(
        "POST",
        f"/api/asambleas/{asamblea_id}/convocatorias",
        expected=201,
        json={
            "ordinal": 2,
            "fecha_programada": "2025-06-06",
            "id_resultado": resultados["reprogramada"],
            "observaciones_resultado": "Error en cédula de citación; se reprograma",
        },
    ).json()
    assert conv2["id_resultado"] == resultados["reprogramada"]
    assert conv2["fecha_realizacion"] is None

    # PATCH sobre convocatoria reprogramada actualiza observaciones sin forzar fecha_realizacion
    api(
        "PATCH",
        f"/api/convocatorias/{conv2['id_convocatoria']}",
        expected=200,
        json={"observaciones_resultado": "Reprogramada formalmente al 10/06/2025 por error en cédula"},
    )

    # 3. Agregar 3a Convocatoria celebrada el 2025-06-10 (literal)
    api(
        "POST",
        f"/api/asambleas/{asamblea_id}/convocatorias",
        expected=201,
        json={
            "ordinal": 3,
            "fecha_programada": "2025-06-10",
            "fecha_realizacion": "2025-06-10",
            "id_resultado": resultados["celebrada"],
            "observaciones_resultado": "Celebrada válidamente el 10/06/2025",
        },
    )

    # 4. Trámite RAN sobre el acta de anuencia (ingreso literal 2025-07-07, desistimiento 2025-07-10)
    ran = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": asamblea_id,
            "referencia_expediente": f"RAN-PE-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2025-07-07",
        },
    ).json()
    ran_id = ran["id_tramite_ran"]

    api(
        "POST",
        f"/api/tramites-ran/{ran_id}/eventos",
        expected=201,
        json={
            "ordinal": 1,
            "id_tipo_evento": eventos_ran["ingreso"],
            "fecha_evento": "2025-07-07",
            "numero_solicitud": "22250006618",
        },
    )
    api(
        "POST",
        f"/api/tramites-ran/{ran_id}/eventos",
        expected=201,
        json={
            "ordinal": 2,
            "id_tipo_evento": eventos_ran["desistimiento"],
            "fecha_evento": "2025-07-10",
            "numero_solicitud": "22250006618",
            "resultado": "Desistimiento voluntario para aclaración técnica (REV 10/07 vs MEET 10/06)",
        },
    )
    # [SINTÉTICO AUDITADO: subsanación 2025-07-15]
    api(
        "POST",
        f"/api/tramites-ran/{ran_id}/eventos",
        expected=201,
        json={
            "ordinal": 3,
            "id_tipo_evento": eventos_ran["subsanacion"],
            "fecha_evento": "2025-07-15",
            "numero_solicitud": "22250006618",
            "resultado": "LAB-SINT-SUBSANACION: Subsanación técnica del acta [SINTÉTICO AUDITADO]",
        },
    )

    # 5. Segunda asamblea formal e independiente para Retiro de Fondos (2025-07-31 literal)
    asamblea_retiro = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": tipos_asamblea["retiro_fondos"],
            "id_contexto_asamblea": contextos["retiro_fondos"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2025-07-31",
                    "fecha_realizacion": "2025-07-31",
                    "id_resultado": resultados["celebrada"],
                    "observaciones_resultado": "Asamblea formal para retiro de fondos",
                }
            ],
        },
    ).json()
    assert asamblea_retiro["id_asamblea"] != asamblea_id

    # Verificaciones estructurales
    assemblies = api("GET", f"/api/proyecto-nucleo/{pn_id}/asambleas").json()
    assert len(assemblies) == 2, "Deben existir exactamente dos asambleas con propósitos distintos"

    # Verificación en reportes periódicos:
    # Mayo 2025: asambleas programada = 1, realizado = 0
    p_may = _period(api, proj_id, anio=2025, mes=5, indicador="asambleas")
    assert len(p_may) == 1
    assert p_may[0]["programado"] == 1
    assert p_may[0]["realizado"] == 0

    # Junio 2025: asamblea anuencia realizada = 1
    p_jun = _period(api, proj_id, anio=2025, mes=6, indicador="asambleas")
    assert len(p_jun) == 1
    assert p_jun[0]["realizado"] == 1

    # Julio 2025:
    # - asambleas: NO debe tener realizadas
    p_jul_asamblea = _period(api, proj_id, anio=2025, mes=7, indicador="asambleas")
    assert sum(r["realizado"] for r in p_jul_asamblea) == 0

    # - retiro_fondos: realizado = 1, cantidad = 1
    p_jul_retiro = _period(api, proj_id, anio=2025, mes=7, indicador="retiro_fondos")
    assert len(p_jul_retiro) == 1
    assert p_jul_retiro[0]["realizado"] == 1
    assert p_jul_retiro[0]["cantidad"] == 1

    # - ingreso_ran_acta: realizado = 1, cantidad = 1
    p_jul_ran = _period(api, proj_id, anio=2025, mes=7, indicador="ingreso_ran_acta")
    assert len(p_jul_ran) == 1
    assert p_jul_ran[0]["realizado"] == 1
    assert p_jul_ran[0]["cantidad"] == 1

    # Dashboard anual 2025: indicadores independientes y deduplicados
    dash = _dashboard(api, proj_id, anio=2025)
    assert dash["asambleas"]["realizado"] == 1
    assert dash["asambleas"]["cantidad"] == 1
    assert dash["retiro_fondos"]["realizado"] == 1
    assert dash["retiro_fondos"]["cantidad"] == 1
    assert dash["ingreso_ran_acta"]["realizado"] == 1
    assert dash["ingreso_ran_acta"]["cantidad"] == 1


def test_bloque_04_los_alvarez_desistimiento_ran_conserva_asamblea_sin_duplicar(api, target_domain):
    """Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx / ASAMBLEAS PENDIENTES Fila 10.

    Núcleo: Los Álvarez (Pedro Escobedo, Querétaro, Consecutivo 220220).

    1. Hechos literales del Excel:
       - 1a Convocatoria: AC10 / AC12 / AI12: 2025-06-21 (no verificativa).
       - 2a Convocatoria y Celebración: AD10 / AF10 / AD12 / AF12 / AJ12 / AM12: 2025-07-01.
       - Ingreso RAN de acta: AJ10 / AJ12 / AQ12: 2025-07-07, Solicitud AM10 / AK12 / AR12: 22250006620.
       - Firma de COP: AV10 / AV12 / AZ12: 2025-07-10.
       - Ingreso RAN de COP: BB12 / BF12: 2025-09-12, Solicitud BC12 / BG12: 22250009281.
       - Inscripción RAN de COP: BJ12: 2025-11-08.
    2. Contradicciones entre fuentes:
       - REV (Fila 10 BW10 y Fila 12 EN12) registra:
         '*DESISTIMIENTO EL 10 DE JULIO 2025, EN LA INSCRIPCIÓN DE ACTAS DE ASAMBLEA ESTÁN CONTABILIZADAS EN PPT.'
       - MEET (Fila 12 CJ12) registra:
         '*DESISTIMIENTO EL 01 DE JULIO 2025, EN LA INSCRIPCIÓN DE ACTAS DE ASAMBLEA ESTÁN CONTABILIZADAS EN PPT.'
    3. Datos sin soporte:
       - BX10 / EO12 / CL12 registran falta de soporte de acta de asamblea corregida, acuse de ingreso
         y calificación/inscripción del acta (condición: revisión documental).
    4. Escenarios sintéticos de laboratorio:
       - Para verificar invarianza y deduplicación registral en caso de reapertura o reingreso:
         * 2025-07-25: Subsanación técnica (LAB-SINT-SUBSANACION).
         * 2025-08-05: Reingreso con solicitud ficticia 'LAB-SINT-SOL-02'.
         * 2025-08-20: Calificación procedente (LAB-SINT-CALIFICACION).
         * 2025-09-12: Inscripción registral (LAB-SINT-INSCRIPCION).
       - Valida que el reingreso no duplica 'ingreso_ran_acta' y que se conserva la asamblea original.
       - Fundamento: LFPA arts. 13, 48, 57 fracc. I y 63 (supletoria al RAN).
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    proj_id = project["id_proyecto"]

    tipos_asamblea = _catalog(api, "tipo_asamblea")
    contextos = _catalog(api, "contexto_asamblea")
    cop = _catalog(api, "tipo_cop_operativo")
    resultados = _catalog(api, "resultado_convocatoria")
    eventos_ran = _catalog(api, "tipo_evento_ran")

    # 1. Crear Asamblea con Convocatoria 1 no verificativa (2025-06-21 literal)
    asamblea = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": tipos_asamblea["anuencia"],
            "id_contexto_asamblea": contextos["cop_original"],
            "id_tipo_cop_operativo": cop["ORIGEN"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2025-06-21",
                    "id_resultado": resultados["no_verificativo"],
                }
            ],
        },
    ).json()
    asamblea_id = asamblea["id_asamblea"]

    # 2. Convocatoria 2 celebrada (2025-07-01 literal)
    api(
        "POST",
        f"/api/asambleas/{asamblea_id}/convocatorias",
        expected=201,
        json={
            "ordinal": 2,
            "fecha_programada": "2025-07-01",
            "fecha_realizacion": "2025-07-01",
            "id_resultado": resultados["celebrada"],
        },
    )

    # 3. Trámite RAN del acta
    ran = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": asamblea_id,
            "referencia_expediente": f"RAN-LA-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2025-07-07",
        },
    ).json()
    ran_id = ran["id_tramite_ran"]

    ran_sequence = [
        (1, "ingreso", "2025-07-07", "22250006620", None, None),
        (2, "desistimiento", "2025-07-10", "22250006620", "Desistimiento voluntario (REV 10/07 vs MEET 01/07)", None),
        (3, "subsanacion", "2025-07-25", "22250006620", "LAB-SINT-SUBSANACION: Subsanación técnica [SINTÉTICO AUDITADO]", None),
        (4, "reingreso", "2025-08-05", "LAB-SINT-SOL-02", "LAB-SINT-REINGRESO: Reingreso [SINTÉTICO AUDITADO]", None),
        (5, "calificacion", "2025-08-20", "LAB-SINT-SOL-02", "LAB-SINT-CALIFICACION: Calificación [SINTÉTICO AUDITADO]", "procedente"),
        (6, "inscripcion", "2025-09-12", "LAB-SINT-SOL-02", "LAB-SINT-INSCRIPCION: Inscripción [SINTÉTICO AUDITADO]", None),
    ]

    for ordinal, code, date_str, req_num, res_text, calif in ran_sequence:
        payload = {
            "ordinal": ordinal,
            "id_tipo_evento": eventos_ran[code],
            "fecha_evento": date_str,
            "numero_solicitud": req_num,
        }
        if res_text:
            payload["resultado"] = res_text
        if calif:
            payload["calificacion"] = calif
        api("POST", f"/api/tramites-ran/{ran_id}/eventos", expected=201, json=payload)

    # Verificaciones estructurales
    assemblies = api("GET", f"/api/proyecto-nucleo/{pn_id}/asambleas").json()
    assert len(assemblies) == 1, "Debe existir únicamente 1 asamblea"

    # Reportes periódicos:
    # Julio 2025: asamblea realizada = 1, ingreso_ran_acta realizada = 1
    p_jul_a = _period(api, proj_id, anio=2025, mes=7, indicador="asambleas")
    assert p_jul_a[0]["realizado"] == 1

    p_jul_ran = _period(api, proj_id, anio=2025, mes=7, indicador="ingreso_ran_acta")
    assert p_jul_ran[0]["realizado"] == 1
    assert p_jul_ran[0]["cantidad"] == 1

    # Agosto 2025: el reingreso NO duplica ingreso_ran_acta realizado
    p_ago_ran = _period(api, proj_id, anio=2025, mes=8, indicador="ingreso_ran_acta")
    assert len(p_ago_ran) == 0, "El reingreso no debe generar un segundo hito de ingreso_ran_acta"

    # Septiembre 2025: inscripcion_ran_acta realizada = 1
    p_sep_ran = _period(api, proj_id, anio=2025, mes=9, indicador="inscripcion_ran_acta")
    assert len(p_sep_ran) == 1
    assert p_sep_ran[0]["realizado"] == 1
    assert p_sep_ran[0]["cantidad"] == 1

    # Dashboard anual 2025
    dash = _dashboard(api, proj_id, anio=2025)
    assert dash["asambleas"]["realizado"] == 1
    assert dash["asambleas"]["cantidad"] == 1
    assert dash["ingreso_ran_acta"]["realizado"] == 1
    assert dash["ingreso_ran_acta"]["cantidad"] == 1
    assert dash["inscripcion_ran_acta"]["realizado"] == 1
    assert dash["inscripcion_ran_acta"]["cantidad"] == 1


def test_bloque_04_la_cueva_convocatoria_cancelada_no_crea_asamblea(api, target_domain):
    """Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx / ASAMBLEAS PENDIENTES Fila 73.

    Núcleo: La Cueva (San Juan del Río, Querétaro, Consecutivo 220322).

    1. Hechos literales del Excel:
       - Convocatoria 1 cancelada: 2025-07-05 ("SE CANCELÓ PROGRAMACIÓN DE ASAMBLEA DEL DÍA 5 DE JULIO"
         en BW73 / EN109 / CJ132).
       - Reunión comunitaria informativa: 2025-08-17 ("CONVOCATORIA ??? 17 DE AGOSTO (ASAMBLEA INFORMATIVA
         POR NO TENER CONVOCATORIA) *SE LLEVÓ A CABO REUNIÓN Y NO SE ACEPTO LA FIRMA DEL COP").
       - Convocatoria formal: 1a Conv 2025-08-31, 2a Conv y Celebrada: 2025-09-28 (AF73 / AF109 / AM132).
       - Firma de COP: AV73 / AV109 / AZ132: 2025-09-28.
       - Ingreso RAN de COP: 2025-10-09, Solicitud 22250010531, Inscrito 2025-12-23 (BJ132).
       - Ingreso RAN de Acta: 2025-11-06, Solicitud 22250011588 (MEET Fila 132 Col AQ132 / AR132).
    2. Contradicciones entre fuentes:
       - REV AP Fila 73 anota '*SIN SOPORTE DE ACTA DE ASAMBLEA'. MEET Fila 132 Col CK132 acredita soporte
         documental de 1a convocatoria, acta del 28/09/2025 y acuse de ingreso al RAN del 06/11/2025.
    3. Datos sin soporte:
       - En REV falta acuse físico del acta; en MEET está plenamente acreditado.
    4. Escenarios sintéticos de laboratorio:
       - Ninguno necesario; se prueban exclusivamente las reglas de que la cancelación y la reunión
         no formal no crean Asambleas ni distorsionan el indicador.
       - Fundamento: Ley Agraria arts. 24 y 25.
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    proj_id = project["id_proyecto"]

    tipos_asamblea = _catalog(api, "tipo_asamblea")
    contextos = _catalog(api, "contexto_asamblea")
    cop = _catalog(api, "tipo_cop_operativo")
    resultados = _catalog(api, "resultado_convocatoria")
    eventos_seg = _catalog(api, "tipo_evento_seguimiento")
    eventos_ran = _catalog(api, "tipo_evento_ran")

    # 1. Crear Asamblea con Convocatoria 1 cancelada (2025-07-05 literal)
    asamblea = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": tipos_asamblea["anuencia"],
            "id_contexto_asamblea": contextos["cop_original"],
            "id_tipo_cop_operativo": cop["ORIGEN"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2025-07-05",
                    "id_resultado": resultados["cancelada"],
                    "observaciones_resultado": "Cancelada por conflicto interno / falta de condiciones",
                }
            ],
        },
    ).json()
    asamblea_id = asamblea["id_asamblea"]

    # 2. Registrar reunión informativa comunitaria previa en SeguimientoEvento (2025-08-17 literal)
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "entidad_tipo": "asamblea",
            "entidad_id": asamblea_id,
            "ambito": "colectivo",
            "id_tipo_evento": eventos_seg["reunion"],
            "fecha_evento": "2025-08-17",
            "detalle": "Reunión informativa comunitaria sin convocatoria formal previa",
            "fuente": ASAMBLEAS_PENDIENTES,
        },
    )

    # 3. Convocatoria 2 formal celebrada (2025-09-28 literal)
    api(
        "POST",
        f"/api/asambleas/{asamblea_id}/convocatorias",
        expected=201,
        json={
            "ordinal": 2,
            "fecha_programada": "2025-09-28",
            "fecha_realizacion": "2025-09-28",
            "id_resultado": resultados["celebrada"],
            "observaciones_resultado": "Celebrada válidamente el 28/09/2025",
        },
    )

    # 4. Trámite RAN del acta ingresada en noviembre (2025-11-06 literal, Solicitud 22250011588)
    ran = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": asamblea_id,
            "referencia_expediente": f"RAN-LC-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2025-11-06",
        },
    ).json()
    api(
        "POST",
        f"/api/tramites-ran/{ran['id_tramite_ran']}/eventos",
        expected=201,
        json={
            "ordinal": 1,
            "id_tipo_evento": eventos_ran["ingreso"],
            "fecha_evento": "2025-11-06",
            "numero_solicitud": "22250011588",
        },
    )

    # Verificaciones de periodo:
    # Julio 2025: programada = 1, realizado = 0
    p_jul = _period(api, proj_id, anio=2025, mes=7, indicador="asambleas")
    assert len(p_jul) == 1
    assert p_jul[0]["programado"] == 1
    assert p_jul[0]["realizado"] == 0

    # Agosto 2025: la reunión comunitaria NO genera hito de asambleas
    p_ago = _period(api, proj_id, anio=2025, mes=8, indicador="asambleas")
    assert len(p_ago) == 0

    # Septiembre 2025: asamblea realizada = 1
    p_sep = _period(api, proj_id, anio=2025, mes=9, indicador="asambleas")
    assert len(p_sep) == 1
    assert p_sep[0]["realizado"] == 1
    assert p_sep[0]["cantidad"] == 1

    # Noviembre 2025: ingreso RAN del acta
    p_nov_ran = _period(api, proj_id, anio=2025, mes=11, indicador="ingreso_ran_acta")
    assert len(p_nov_ran) == 1
    assert p_nov_ran[0]["realizado"] == 1

    # Dashboard anual 2025: deduplicado
    dash = _dashboard(api, proj_id, anio=2025)
    assert dash["asambleas"]["programado"] == 1
    assert dash["asambleas"]["realizado"] == 1
    assert dash["asambleas"]["cantidad"] == 1
    assert dash["ingreso_ran_acta"]["realizado"] == 1


def test_bloque_04_barrancas_convocatoria_sin_publicar_vs_no_verificativa(api, target_domain):
    """Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx / ASAMBLEAS PENDIENTES Fila 78.

    Núcleo: San Sebastián de las Barrancas (San Juan del Río, Querétaro, Consecutivo 220303).

    1. Hechos literales del Excel:
       - 1a Convocatoria: emitida para 2025-09-04, queda sin efecto legal por omitirse su publicación
         en los lugares más visibles del ejido (BW78 / EN117 / CJ145).
       - Convocatoria formal y Celebración de Asamblea: 2025-09-21 (AF78 / AF117 / AM145).
       - Ingreso RAN de Acta: 2025-09-24, Solicitud 22250009808 (compartido entre TUC y solares).
       - Destinos y convenios amparados en la misma asamblea:
         * TUC (Derecho de paso, calles y banquetas): Convenio firmado 2025-09-21 ($1,452,669.00),
           ingresado al RAN 2025-09-24 (Solicitud 22250009814), inscrito 2025-10-02.
         * Solares a favor del núcleo (S-1 MZ-3, S-2 MZ-2): Convenio firmado 2025-09-21 ($2,972,545.00),
           ingresado al RAN 2025-09-24 (Solicitud 22250009815), inscrito 2025-10-02.
    2. Contradicciones entre fuentes:
       - Ninguna en fechas de convocatoria, asamblea ni solicitudes RAN.
    3. Datos sin soporte:
       - CL145 señala falta de soporte de calificación registral e inscripción del acta (revisión documental).
    4. Escenarios sintéticos de laboratorio:
       - LAB-SINT-CALIFICACION: evento auxiliar del 2025-10-20 para comprobar que la calificación favorable
         del acta no computa como inscripción registral.
       - Fundamento:
         * Ley Agraria art. 23 fracc. II (formalidades simples para servidumbres en TUC).
         * Ley Agraria art. 23 fracc. IX y art. 28 (formalidades especiales obligatorias para asignación
           y titulación de solares urbanos a favor del núcleo ejidal: quórum 3/4 o 2/3, fedatario público y PA).
         * Ley Agraria art. 25 (convocatoria no publicada queda cancelada / sin efecto, no es no verificativa).
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    proj_id = project["id_proyecto"]

    tipos_asamblea = _catalog(api, "tipo_asamblea")
    contextos = _catalog(api, "contexto_asamblea")
    cop = _catalog(api, "tipo_cop_operativo")
    resultados = _catalog(api, "resultado_convocatoria")
    eventos_ran = _catalog(api, "tipo_evento_ran")

    # 1. Crear Asamblea con Convocatoria 1 sin efecto por falta de publicación (cancelada, 2025-09-04 literal)
    asamblea = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": tipos_asamblea["anuencia"],
            "id_contexto_asamblea": contextos["cop_original"],
            "id_tipo_cop_operativo": cop["ORIGEN"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2025-09-04",
                    "id_resultado": resultados["cancelada"],
                    "observaciones_resultado": "Sin efecto por falta de debida publicación en estrados ejidales",
                }
            ],
        },
    ).json()
    asamblea_id = asamblea["id_asamblea"]

    # 2. Convocatoria 2 celebrada válidamente (2025-09-21 literal)
    api(
        "POST",
        f"/api/asambleas/{asamblea_id}/convocatorias",
        expected=201,
        json={
            "ordinal": 2,
            "fecha_programada": "2025-09-21",
            "fecha_realizacion": "2025-09-21",
            "id_resultado": resultados["celebrada"],
            "observaciones_resultado": "Celebrada válidamente con quórum legal",
        },
    )

    # 3. Trámite RAN del ACTA: ingreso real el 2025-09-24 con solicitud 22250009808
    ran_acta = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": asamblea_id,
            "referencia_expediente": f"RAN-SB-ACTA-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2025-09-24",
        },
    ).json()

    api(
        "POST",
        f"/api/tramites-ran/{ran_acta['id_tramite_ran']}/eventos",
        expected=201,
        json={
            "ordinal": 1,
            "id_tipo_evento": eventos_ran["ingreso"],
            "fecha_evento": "2025-09-24",
            "numero_solicitud": "22250009808",
        },
    )
    # [SINTÉTICO AUDITADO: calificación registral de prueba 2025-10-20]
    api(
        "POST",
        f"/api/tramites-ran/{ran_acta['id_tramite_ran']}/eventos",
        expected=201,
        json={
            "ordinal": 2,
            "id_tipo_evento": eventos_ran["calificacion"],
            "fecha_evento": "2025-10-20",
            "numero_solicitud": "22250009808",
            "calificacion": "procedente",
            "resultado": "LAB-SINT-CALIFICACION: Calificación registral favorable en laboratorio [SINTÉTICO AUDITADO]",
        },
    )

    # 4. Dos afectaciones / convenios derivados del mismo acuerdo de asamblea:
    # 4a. Afectación TUC
    aff_tuc = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "colectivo",
            "superficie_afectada_ha": "0.145267",
            "id_tipo_cop_operativo": cop["ORIGEN"],
        },
    ).json()
    conv_tuc = api(
        "POST",
        f"/api/afectaciones/{aff_tuc['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_convenio": "cop_original",
            "fecha_firma": "2025-09-21",
            "monto_100": "1452669",
            "superficie_ha": "0.145267",
        },
    ).json()
    ran_conv_tuc = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_convenio": conv_tuc["id_convenio"],
            "referencia_expediente": f"RAN-SB-CONV-TUC-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2025-09-24",
        },
    ).json()
    api(
        "POST",
        f"/api/tramites-ran/{ran_conv_tuc['id_tramite_ran']}/eventos",
        expected=201,
        json={
            "ordinal": 1,
            "id_tipo_evento": eventos_ran["ingreso"],
            "fecha_evento": "2025-09-24",
            "numero_solicitud": "22250009814",
        },
    )
    api(
        "POST",
        f"/api/tramites-ran/{ran_conv_tuc['id_tramite_ran']}/eventos",
        expected=201,
        json={
            "ordinal": 2,
            "id_tipo_evento": eventos_ran["inscripcion"],
            "fecha_evento": "2025-10-02",
        },
    )

    # 4b. Afectación Solares a favor del núcleo
    aff_sol = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "colectivo",
            "superficie_afectada_ha": "0.297255",
            "id_tipo_cop_operativo": cop["ORIGEN"],
        },
    ).json()
    conv_sol = api(
        "POST",
        f"/api/afectaciones/{aff_sol['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_convenio": "cop_original",
            "fecha_firma": "2025-09-21",
            "monto_100": "2972545",
            "superficie_ha": "0.297255",
        },
    ).json()
    ran_conv_sol = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_convenio": conv_sol["id_convenio"],
            "referencia_expediente": f"RAN-SB-CONV-SOL-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2025-09-24",
        },
    ).json()
    api(
        "POST",
        f"/api/tramites-ran/{ran_conv_sol['id_tramite_ran']}/eventos",
        expected=201,
        json={
            "ordinal": 1,
            "id_tipo_evento": eventos_ran["ingreso"],
            "fecha_evento": "2025-09-24",
            "numero_solicitud": "22250009815",
        },
    )
    api(
        "POST",
        f"/api/tramites-ran/{ran_conv_sol['id_tramite_ran']}/eventos",
        expected=201,
        json={
            "ordinal": 2,
            "id_tipo_evento": eventos_ran["inscripcion"],
            "fecha_evento": "2025-10-02",
        },
    )

    # Verificaciones:
    # Septiembre 2025:
    # - asambleas: realizado = 1, cantidad = 1 (invarianza: una sola asamblea a pesar de 2 afectaciones/convenios)
    p_sep_a = _period(api, proj_id, anio=2025, mes=9, indicador="asambleas")
    assert len(p_sep_a) == 1
    assert p_sep_a[0]["realizado"] == 1
    assert p_sep_a[0]["cantidad"] == 1

    # - ingreso_ran_acta: realizado = 1, cantidad = 1 (Solicitud 22250009808 literal)
    p_sep_ran_acta = _period(api, proj_id, anio=2025, mes=9, indicador="ingreso_ran_acta")
    assert len(p_sep_ran_acta) == 1
    assert p_sep_ran_acta[0]["realizado"] == 1
    assert p_sep_ran_acta[0]["cantidad"] == 1

    # - ingreso_ran_convenio: realizado = 2 (un ingreso por cada convenio independiente)
    p_sep_ran_conv = _period(api, proj_id, anio=2025, mes=9, indicador="ingreso_ran_convenio")
    assert sum(r["realizado"] for r in p_sep_ran_conv) == 2

    # Octubre 2025:
    # - inscripcion_ran_convenio: realizado = 2
    p_oct_inscrip_conv = _period(api, proj_id, anio=2025, mes=10, indicador="inscripcion_ran_convenio")
    assert sum(r["realizado"] for r in p_oct_inscrip_conv) == 2

    # - inscripcion_ran_acta: la calificación del acta NO genera inscripción
    p_oct_inscrip_acta = _period(api, proj_id, anio=2025, mes=10, indicador="inscripcion_ran_acta")
    assert len(p_oct_inscrip_acta) == 0, "La calificación no debe computarse como inscripción del acta"

    # Dashboard anual 2025
    dash = _dashboard(api, proj_id, anio=2025)
    assert dash["asambleas"]["realizado"] == 1
    assert dash["ingreso_ran_acta"]["realizado"] == 1
    assert dash["ingreso_ran_convenio"]["realizado"] == 2
    assert dash["inscripcion_ran_convenio"]["realizado"] == 2
    assert "inscripcion_ran_acta" not in dash or dash["inscripcion_ran_acta"]["realizado"] == 0


def test_bloque_04_santiago_oxthoc_permanente_vs_asamblea_posterior(api, target_domain):
    """Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx / ASAMBLEAS PENDIENTES Fila 62.

    Núcleo: Santiago Oxthoc (Jilotepec, Edo. Méx., Consecutivo 150419).

    1. Hechos literales del Excel:
       - Proceso 1 (Sesión Permanente):
         * 1a Convocatoria: AC62 / AC98 / AI117: 2025-06-29 (no verificativa).
         * 2a Convocatoria e Instalación: AD62 / AD98 / AJ117: 2025-07-08 (declarada en Sesión Permanente).
         * Continuación de Asamblea Permanente: AD62 / AD98 / AJ117: 2025-09-07, con rechazo formal a firma de COP
           (BW62 / EN98 / CJ117: "SE DECLARA ASAMBLEA PERMANENTE NO SE ACEPTO LA FIRMA DE COP").
       - Proceso 2 (Asamblea Posterior Formal e Independiente):
         * Convocatoria y Celebración: AF98 / AM117: 2025-11-18 (en 1a Convocatoria, aprobada válidamente).
         * Firma de COP: AV98 / AZ117: 2025-11-18 ($1,841,874.00, 00-61-39.58 ha).
         * Ingreso RAN de Acta 2: AQ117 / AR117: 2025-11-20, Solicitud 15250052850.
         * Ingreso RAN de Convenio: BF117 / BG117: 2025-12-17, Solicitud 15250057354,
           Calificación POSITIVA (BI117), Inscripción 2026-01-14 (BJ117).
    2. Contradicciones entre fuentes:
       - Ninguna en fechas ni solicitudes registrales.
    3. Datos sin soporte:
       - CL117 anota falta de soporte físico local del acuse de acta; en AR117 figura la solicitud 15250052850 (revisión documental).
    4. Escenarios sintéticos de laboratorio:
       - Ninguno necesario; se prueban hechos literales acreditados.
       - Semántica del indicador: Ambas asambleas fueron formalmente instaladas y celebradas en 2025 (julio y noviembre);
         el indicador 'asambleas' computa exactamente 2 asambleas celebradas.
       - Fundamento: Art. 13 REG-REGISTRAL y Lineamientos PA 2025.
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    proj_id = project["id_proyecto"]

    tipos_asamblea = _catalog(api, "tipo_asamblea")
    contextos = _catalog(api, "contexto_asamblea")
    cop = _catalog(api, "tipo_cop_operativo")
    resultados = _catalog(api, "resultado_convocatoria")
    motivos = _catalog(api, "motivo_seguimiento")
    eventos_seg = _catalog(api, "tipo_evento_seguimiento")
    eventos_ran = _catalog(api, "tipo_evento_ran")

    # 1. Primera Asamblea (iniciada 2025-06-29, instalada 2025-07-08 como permanente)
    asamblea1 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": tipos_asamblea["anuencia"],
            "id_contexto_asamblea": contextos["cop_original"],
            "id_tipo_cop_operativo": cop["ORIGEN"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2025-06-29",
                    "id_resultado": resultados["no_verificativo"],
                    "observaciones_resultado": "1a convocatoria no verificativa",
                },
                {
                    "ordinal": 2,
                    "fecha_programada": "2025-07-08",
                    "fecha_realizacion": "2025-07-08",
                    "id_resultado": resultados["celebrada"],
                    "observaciones_resultado": "Instalada en 2a convocatoria; se declara asamblea permanente",
                },
            ],
        },
    ).json()
    asamblea1_id = asamblea1["id_asamblea"]

    # 2. Continuación de la primera asamblea el 2025-09-07 con rechazo de firma de COP
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "entidad_tipo": "asamblea",
            "entidad_id": asamblea1_id,
            "ambito": "colectivo",
            "id_tipo_evento": eventos_seg["continuacion_asamblea"],
            "id_motivo": motivos["rechazo"],
            "fecha_evento": "2025-09-07",
            "detalle": "Continuación de asamblea permanente del 07/09/2025: no se aceptó la firma del COP",
            "fuente": INFORME_MQ_REV,
        },
    )

    # 3. Segunda Asamblea posterior formalmente convocada en 1a convocatoria para el 2025-11-18
    asamblea2 = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": tipos_asamblea["anuencia"],
            "id_contexto_asamblea": contextos["cop_original"],
            "id_tipo_cop_operativo": cop["ORIGEN"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2025-11-18",
                    "fecha_realizacion": "2025-11-18",
                    "id_resultado": resultados["celebrada"],
                    "observaciones_resultado": "Asamblea posterior celebrada; se aprueba anuencia y se firma COP",
                }
            ],
        },
    ).json()
    asamblea2_id = asamblea2["id_asamblea"]
    assert asamblea2_id != asamblea1_id

    # 4. Trámite RAN del acta de la 2da asamblea (ingreso literal 2025-11-20, Solicitud 15250052850)
    ran_acta = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": asamblea2_id,
            "referencia_expediente": f"RAN-OX-ACTA-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2025-11-20",
        },
    ).json()
    api(
        "POST",
        f"/api/tramites-ran/{ran_acta['id_tramite_ran']}/eventos",
        expected=201,
        json={
            "ordinal": 1,
            "id_tipo_evento": eventos_ran["ingreso"],
            "fecha_evento": "2025-11-20",
            "numero_solicitud": "15250052850",
        },
    )

    # 5. Afectación y Convenio COP firmado en noviembre
    aff = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/afectaciones",
        expected=201,
        json={
            "tipo_afectacion": "colectivo",
            "superficie_afectada_ha": "0.613958",
            "id_tipo_cop_operativo": cop["ORIGEN"],
        },
    ).json()
    conv = api(
        "POST",
        f"/api/afectaciones/{aff['id_afectacion']}/convenios",
        expected=201,
        json={
            "tipo_convenio": "cop_original",
            "fecha_firma": "2025-11-18",
            "monto_90": "1657686.60",
            "monto_100": "1841874.00",
            "superficie_ha": "0.613958",
            "id_asamblea_autorizacion": asamblea2_id,
        },
    ).json()

    # 6. Trámite RAN del convenio (ingreso literal 2025-12-17, Sol. 15250057354; inscripción 2026-01-14)
    ran_conv = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_convenio": conv["id_convenio"],
            "referencia_expediente": f"RAN-OX-CONV-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2025-12-17",
        },
    ).json()
    api(
        "POST",
        f"/api/tramites-ran/{ran_conv['id_tramite_ran']}/eventos",
        expected=201,
        json={
            "ordinal": 1,
            "id_tipo_evento": eventos_ran["ingreso"],
            "fecha_evento": "2025-12-17",
            "numero_solicitud": "15250057354",
        },
    )
    api(
        "POST",
        f"/api/tramites-ran/{ran_conv['id_tramite_ran']}/eventos",
        expected=201,
        json={
            "ordinal": 2,
            "id_tipo_evento": eventos_ran["calificacion"],
            "fecha_evento": "2026-01-14",
            "numero_solicitud": "15250057354",
            "calificacion": "POSITIVA",
            "resultado": "Calificación positiva de convenio",
        },
    )
    api(
        "POST",
        f"/api/tramites-ran/{ran_conv['id_tramite_ran']}/eventos",
        expected=201,
        json={
            "ordinal": 3,
            "id_tipo_evento": eventos_ran["inscripcion"],
            "fecha_evento": "2026-01-14",
            "numero_solicitud": "15250057354",
        },
    )

    # Verificaciones periódicas:
    # Junio 2025: asamblea 1 programada en 1a convocatoria
    p_jun = _period(api, proj_id, anio=2025, mes=6, indicador="asambleas")
    assert len(p_jun) == 1
    assert p_jun[0]["programado"] == 1
    assert p_jun[0]["realizado"] == 0

    # Julio 2025: asamblea 1 instalada y celebrada como sesión permanente
    p_jul = _period(api, proj_id, anio=2025, mes=7, indicador="asambleas")
    assert len(p_jul) == 1
    assert p_jul[0]["realizado"] == 1

    # Septiembre 2025: continuación con rechazo; NO genera nueva asamblea
    p_sep = _period(api, proj_id, anio=2025, mes=9, indicador="asambleas")
    assert len(p_sep) == 0, "La continuación infructuosa no debe computar como asamblea"

    # Noviembre 2025:
    # - asambleas: asamblea 2 realizada = 1
    p_nov_a = _period(api, proj_id, anio=2025, mes=11, indicador="asambleas")
    assert len(p_nov_a) == 1
    assert p_nov_a[0]["realizado"] == 1

    # - ingreso_ran_acta: realizado = 1 (Solicitud 15250052850)
    p_nov_acta = _period(api, proj_id, anio=2025, mes=11, indicador="ingreso_ran_acta")
    assert len(p_nov_acta) == 1
    assert p_nov_acta[0]["realizado"] == 1

    # Diciembre 2025:
    # - ingreso_ran_convenio: realizado = 1 (Solicitud 15250057354)
    p_dic_conv = _period(api, proj_id, anio=2025, mes=12, indicador="ingreso_ran_convenio")
    assert len(p_dic_conv) == 1
    assert p_dic_conv[0]["realizado"] == 1

    # Enero 2026:
    # - inscripcion_ran_convenio: realizado = 1
    p_ene_conv = _period(api, proj_id, anio=2026, mes=1, indicador="inscripcion_ran_convenio")
    assert len(p_ene_conv) == 1
    assert p_ene_conv[0]["realizado"] == 1

    # Dashboard anual 2025:
    # Exactamente 2 asambleas celebradas (julio y noviembre)
    dash2025 = _dashboard(api, proj_id, anio=2025)
    assert dash2025["asambleas"]["realizado"] == 2
    assert dash2025["asambleas"]["cantidad"] == 2
    assert dash2025["ingreso_ran_acta"]["realizado"] == 1
    assert dash2025["ingreso_ran_convenio"]["realizado"] == 1

    dash2026 = _dashboard(api, proj_id, anio=2026)
    assert dash2026["inscripcion_ran_convenio"]["realizado"] == 1


def test_bloque_04_san_clemente_destinos_compartidos_y_consulta_indigena(api, target_domain):
    """Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx / ASAMBLEAS PENDIENTES Fila 15.

    Núcleo: San Clemente (Pedro Escobedo, Querétaro, Consecutivo 220226).

    1. Hechos literales del Excel:
       - Presencia de población indígena reconocida (CB20: SÍ; PROYECTOS VÍAS SEGUIMIENTO GENERAL.xlsx Fila 53).
       - Convocatorias iniciales canceladas formalmente por presencia indígena y consulta previa requerida ante INPI
         (EN20 / CJ20: "CANCELADA POR PRESENCIA DE POBLACIÓN INDÍGENA... SE CONSULTARÁ AL INPI").
       - Consulta indígena comunitaria: Presentación de protocolo el 2025-09-07 y reunión con la comunidad el 2025-09-14 (literal).
       - Convocatoria formal y Celebración de Asamblea: 2025-09-21 (AF20 / AM20).
       - Firma de COP: AV20 / AZ20: 2025-09-21.
       - Tres destinos colectivos compartidos bajo la misma y única acta de asamblea:
         * TUC Uso Común ($631,692.45)
         * TUC Canal de Riego y Drenes ($773,214.30)
         * TUC Derecho de Paso ($130,345.20)
       - Ingreso RAN de Acta: 2025-09-24 (CK20 en MEET).
       - Ingreso RAN de COP: 2025-09-24, Solicitud 22250009824, Inscrito 2025-10-02 (BF20 / BG20 / BJ20 en MEET).
    2. Contradicciones entre fuentes:
       - Ninguna en fechas de consulta, asamblea ni convenios.
    3. Datos sin soporte:
       - EO20 / CL20 señalan falta de soporte documental de calificación registral del acta (revisión documental).
    4. Escenarios sintéticos de laboratorio:
       - Ninguno necesario; se prueban hechos literales acreditados.
       - Invarianza de reporting: El reporte cuenta actos jurídicos únicos por tipo COP;
         los 3 destinos y convenios derivados computan exactamente 1 sola asamblea celebrada.
       - Fundamento: Art. 2 Constitucional, Convenio 169 OIT y Ley Agraria art. 23 fracc. II.
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    proj_id = project["id_proyecto"]

    tipos_asamblea = _catalog(api, "tipo_asamblea")
    contextos = _catalog(api, "contexto_asamblea")
    cop = _catalog(api, "tipo_cop_operativo")
    resultados = _catalog(api, "resultado_convocatoria")
    eventos_seg = _catalog(api, "tipo_evento_seguimiento")
    motivos = _catalog(api, "motivo_seguimiento")

    # 1. Crear Asamblea con Convocatoria 1 cancelada por consulta indígena (2025-06-21 literal)
    asamblea = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": tipos_asamblea["anuencia"],
            "id_contexto_asamblea": contextos["cop_original"],
            "id_tipo_cop_operativo": cop["ORIGEN"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2025-06-21",
                    "id_resultado": resultados["cancelada"],
                    "observaciones_resultado": "Cancelada por presencia de población indígena; se requiere consulta previa INPI",
                }
            ],
        },
    ).json()
    asamblea_id = asamblea["id_asamblea"]

    # 2. Registrar eventos de consulta indígena en SeguimientoEvento (7 y 14 de septiembre literal)
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "entidad_tipo": "asamblea",
            "entidad_id": asamblea_id,
            "ambito": "colectivo",
            "id_tipo_evento": eventos_seg["consulta_indigena"],
            "id_motivo": motivos["comunidad_indigena"],
            "fecha_evento": "2025-09-07",
            "detalle": "Presentación de protocolo de consulta indígena a autoridades ejidales e INPI",
            "fuente": ASAMBLEAS_PENDIENTES,
        },
    )
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "entidad_tipo": "asamblea",
            "entidad_id": asamblea_id,
            "ambito": "colectivo",
            "id_tipo_evento": eventos_seg["consulta_indigena"],
            "id_motivo": motivos["comunidad_indigena"],
            "fecha_evento": "2025-09-14",
            "detalle": "Reunión de consulta indígena con la comunidad de San Clemente",
            "fuente": ASAMBLEAS_PENDIENTES,
        },
    )

    # 3. Convocatoria formal celebrada válidamente el 2025-09-21 (literal)
    api(
        "POST",
        f"/api/asambleas/{asamblea_id}/convocatorias",
        expected=201,
        json={
            "ordinal": 2,
            "fecha_programada": "2025-09-21",
            "fecha_realizacion": "2025-09-21",
            "id_resultado": resultados["celebrada"],
            "observaciones_resultado": "Celebrada válidamente tras consulta previa",
        },
    )

    # 4. Tres afectaciones y tres convenios bajo la misma asamblea de anuencia
    destinos = [
        ("0.140376", "631692.45", "TUC Uso Común"),
        ("0.171825", "773214.30", "TUC Canal de Riego"),
        ("0.028966", "130345.20", "TUC Derecho de Paso"),
    ]
    for sup, monto, desc in destinos:
        aff = api(
            "POST",
            f"/api/proyecto-nucleo/{pn_id}/afectaciones",
            expected=201,
            json={
                "tipo_afectacion": "colectivo",
                "superficie_afectada_ha": sup,
                "id_tipo_cop_operativo": cop["ORIGEN"],
            },
        ).json()
        api(
            "POST",
            f"/api/afectaciones/{aff['id_afectacion']}/convenios",
            expected=201,
            json={
                "tipo_convenio": "cop_original",
                "fecha_firma": "2025-09-21",
                "monto_100": monto,
                "superficie_ha": sup,
                "descripcion_instrumento": desc,
                "id_asamblea_autorizacion": asamblea_id,
            },
        )

    # Verificación en reportes:
    # Junio 2025: programada = 1, realizado = 0
    p_jun = _period(api, proj_id, anio=2025, mes=6, indicador="asambleas")
    assert len(p_jun) == 1
    assert p_jun[0]["programado"] == 1
    assert p_jun[0]["realizado"] == 0

    # Septiembre 2025: a pesar de 3 destinos y convenios, cuenta EXACTAMENTE 1 asamblea celebrada
    p_sep = _period(api, proj_id, anio=2025, mes=9, indicador="asambleas")
    assert len(p_sep) == 1
    assert p_sep[0]["realizado"] == 1
    assert p_sep[0]["cantidad"] == 1, "No debe triplicarse el conteo de asambleas por destinos múltiples"

    # Dashboard anual 2025
    dash = _dashboard(api, proj_id, anio=2025)
    assert dash["asambleas"]["realizado"] == 1
    assert dash["asambleas"]["cantidad"] == 1


def test_bloque_04_separacion_programado_y_realizado_invarianza_conteos(api, target_domain):
    """Escenario sintético transversal de laboratorio: invarianza de conteos y separación temporal.

    1. Hechos literales del Excel:
       - No aplica; es un escenario de diseño sintético transversal para contrastar el comportamiento
         del motor de reporting ante ciclos complejos con convocatorias no verificativas, reprogramadas,
         celebradas, continuaciones y trámites registrales con reingreso.
    2. Contradicciones entre fuentes:
       - No aplica.
    3. Datos sin soporte:
       - No aplica.
    4. Escenarios sintéticos de laboratorio:
       - Convocatoria 1 (2025-01-10): no verificativa.
       - Convocatoria 2 (2025-02-14): reprogramada.
       - Convocatoria 3 (2025-03-20): celebrada.
       - Continuación de asamblea permanente (2025-04-10): LAB-SINT-CONT-INV.
       - Trámite RAN del acta con solicitud ficticia LAB-SINT-SOL-01 (ingreso mayo, prevención junio, subsanación julio)
         y reingreso con solicitud ficticia LAB-SINT-SOL-02 (agosto) y calificación (septiembre).
       - Invarianzas verificadas:
         * sum(programado) == 1 en enero para asambleas.
         * sum(realizado) == 1 en marzo para asambleas.
         * En abril las continuaciones no generan duplicados.
         * sum(programado) == 1 y sum(realizado) == 1 para ingreso_ran_acta en mayo.
         * En agosto el reingreso no duplica ingreso_ran_acta.
         * En septiembre la calificación no genera inscripción.
         * Dashboard anual: count(DISTINCT clave_hito) == 1 para cada indicador.
    """
    project, pn = _isolated_pn(api, target_domain)
    pn_id = pn["id_proyecto_nucleo"]
    proj_id = project["id_proyecto"]

    tipos_asamblea = _catalog(api, "tipo_asamblea")
    contextos = _catalog(api, "contexto_asamblea")
    cop = _catalog(api, "tipo_cop_operativo")
    resultados = _catalog(api, "resultado_convocatoria")
    eventos_ran = _catalog(api, "tipo_evento_ran")
    eventos_seg = _catalog(api, "tipo_evento_seguimiento")

    # 1. Convocatoria 1 (2025-01-10, no verificativa)
    asamblea = api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/asambleas",
        expected=201,
        json={
            "id_tipo_asamblea": tipos_asamblea["anuencia"],
            "id_contexto_asamblea": contextos["cop_original"],
            "id_tipo_cop_operativo": cop["ORIGEN"],
            "convocatorias": [
                {
                    "ordinal": 1,
                    "fecha_programada": "2025-01-10",
                    "id_resultado": resultados["no_verificativo"],
                }
            ],
        },
    ).json()
    asamblea_id = asamblea["id_asamblea"]

    # 2. Convocatoria 2 (2025-02-14, reprogramada)
    api(
        "POST",
        f"/api/asambleas/{asamblea_id}/convocatorias",
        expected=201,
        json={
            "ordinal": 2,
            "fecha_programada": "2025-02-14",
            "id_resultado": resultados["reprogramada"],
            "observaciones_resultado": "Reprogramada formalmente",
        },
    )

    # 3. Convocatoria 3 (2025-03-20, celebrada)
    api(
        "POST",
        f"/api/asambleas/{asamblea_id}/convocatorias",
        expected=201,
        json={
            "ordinal": 3,
            "fecha_programada": "2025-03-20",
            "fecha_realizacion": "2025-03-20",
            "id_resultado": resultados["celebrada"],
        },
    )

    # 4. Continuación de asamblea permanente en abril (2025-04-10)
    api(
        "POST",
        f"/api/proyecto-nucleo/{pn_id}/seguimiento",
        expected=201,
        json={
            "entidad_tipo": "asamblea",
            "entidad_id": asamblea_id,
            "ambito": "colectivo",
            "id_tipo_evento": eventos_seg["continuacion_asamblea"],
            "fecha_evento": "2025-04-10",
            "detalle": "LAB-SINT-CONT-INV: Continuación de asamblea en sesión permanente [SINTÉTICO AUDITADO]",
            "fuente": "QA Invarianza",
        },
    )

    # 5. Trámite RAN del acta
    ran = api(
        "POST",
        "/api/tramites-ran",
        expected=201,
        json={
            "id_asamblea": asamblea_id,
            "referencia_expediente": f"RAN-INV-{uuid.uuid4().hex[:6]}",
            "fecha_programada_ingreso": "2025-05-02",
        },
    ).json()
    ran_id = ran["id_tramite_ran"]

    ran_events = [
        (1, "ingreso", "2025-05-02", "LAB-SINT-SOL-01", None, None),
        (2, "prevencion", "2025-06-05", "LAB-SINT-SOL-01", "Observación de forma", None),
        (3, "subsanacion", "2025-07-08", "LAB-SINT-SOL-01", "LAB-SINT-SUBSANACION: Aclaración técnica [SINTÉTICO AUDITADO]", None),
        (4, "reingreso", "2025-08-12", "LAB-SINT-SOL-02", "LAB-SINT-REINGRESO: Reingreso [SINTÉTICO AUDITADO]", None),
        (5, "calificacion", "2025-09-18", "LAB-SINT-SOL-02", "LAB-SINT-CALIFICACION: Calificación [SINTÉTICO AUDITADO]", "procedente"),
    ]
    for ordinal, code, date_str, req_num, res_text, calif in ran_events:
        payload = {
            "ordinal": ordinal,
            "id_tipo_evento": eventos_ran[code],
            "fecha_evento": date_str,
            "numero_solicitud": req_num,
        }
        if res_text:
            payload["resultado"] = res_text
        if calif:
            payload["calificacion"] = calif
        api("POST", f"/api/tramites-ran/{ran_id}/eventos", expected=201, json=payload)

    # Verificaciones periódicas mes a mes
    # Enero 2025: asambleas programado = 1, realizado = 0
    p_ene = _period(api, proj_id, anio=2025, mes=1, indicador="asambleas")
    assert len(p_ene) == 1
    assert p_ene[0]["programado"] == 1
    assert p_ene[0]["realizado"] == 0
    assert p_ene[0]["cantidad"] == 1

    # Febrero 2025: no hay realizado
    p_feb = _period(api, proj_id, anio=2025, mes=2, indicador="asambleas")
    assert sum(r["realizado"] for r in p_feb) == 0

    # Marzo 2025: asambleas programado = 0, realizado = 1
    p_mar = _period(api, proj_id, anio=2025, mes=3, indicador="asambleas")
    assert len(p_mar) == 1
    assert p_mar[0]["programado"] == 0
    assert p_mar[0]["realizado"] == 1
    assert p_mar[0]["cantidad"] == 1

    # Abril 2025: no hay hitos de asambleas generados por la continuación
    p_abr = _period(api, proj_id, anio=2025, mes=4, indicador="asambleas")
    assert len(p_abr) == 0

    # Mayo 2025: ingreso_ran_acta programado = 1, realizado = 1
    p_may_ran = _period(api, proj_id, anio=2025, mes=5, indicador="ingreso_ran_acta")
    assert len(p_may_ran) == 1
    assert p_may_ran[0]["programado"] == 1
    assert p_may_ran[0]["realizado"] == 1
    assert p_may_ran[0]["cantidad"] == 1

    # Agosto 2025: reingreso no duplica ingreso_ran_acta realizado
    p_ago_ran = _period(api, proj_id, anio=2025, mes=8, indicador="ingreso_ran_acta")
    assert len(p_ago_ran) == 0

    # Septiembre 2025: calificación no genera inscripción
    p_sep_inscrip = _period(api, proj_id, anio=2025, mes=9, indicador="inscripcion_ran_acta")
    assert len(p_sep_inscrip) == 0

    # Dashboard anual 2025: invarianza estricta
    dash = _dashboard(api, proj_id, anio=2025)
    assert dash["asambleas"]["programado"] == 1
    assert dash["asambleas"]["realizado"] == 1
    assert dash["asambleas"]["cantidad"] == 1

    assert dash["ingreso_ran_acta"]["programado"] == 1
    assert dash["ingreso_ran_acta"]["realizado"] == 1
    assert dash["ingreso_ran_acta"]["cantidad"] == 1

    assert "inscripcion_ran_acta" not in dash or dash["inscripcion_ran_acta"]["realizado"] == 0
