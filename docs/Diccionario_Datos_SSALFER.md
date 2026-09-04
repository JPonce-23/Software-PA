# Diccionario de datos vigente

Fuente: migraciones 001, 002, 003, 004 y 005. Siguiente migración: 006. El Modelo Excel V1 queda funcionalmente congelado en 005; 006+ sólo se justifica por requerimientos nuevos o defectos reales, no por campos ya presentes en las fuentes auditadas.

- `seguimiento_evento`: entidad de historia funcional operativa con PK `id_seguimiento_evento`, FK `id_proyecto_nucleo`, objetivo opcional (`entidad_tipo`, `entidad_id`), `ambito` (general, colectivo, individual), `id_tipo_evento` (FK catalogo_operativo), `id_motivo` (FK catalogo_operativo nullable), `fecha_evento`, `detalle`, `id_documento`, `fuente`, auditoría y baja lógica.
- `catalogo_operativo.tipo_evento_seguimiento`: inicio, suspension, reapertura, cierre, cambio_alcance, reunion, negociacion, consulta_indigena, continuacion_asamblea, medicion_bdt, otro.
- `catalogo_operativo.motivo_seguimiento`: expropiacion_directa, no_afectacion, comunidad_indigena, dominio_pleno, juicio_agrario, conflicto_titularidad, rechazo, cambio_trazo, nueva_informacion, calificacion_negativa, falta_pago, otro.
- `catalogo_operativo.estado_requisito_documental`: adiciona parcial, pendiente_validacion a los preexistentes (pendiente, disponible, faltante, no_aplica, otro).
- `requisito_documental`: incorpora validacion_pa_sict (Validación PA/SICT), oficio_ran_parcelas_afectacion (Oficio RAN de parcelas con afectación) y acta_complementaria (Acta complementaria).
- `vw_seguimiento_estado_actual`: read-model determinista por proyecto-núcleo y objetivo (estado_actual, tipo_ultimo_evento, motivo_actual, fecha_ultimo_evento, detalle, ambito).
- `actividad_campo.id_tipo_cop_operativo`: FK nullable de ciclo reportable; conserva múltiples sensibilizaciones/caminamientos.
- `asamblea.id_tipo_cop_operativo`: FK nullable de ciclo reportable; Asamblea es entidad independiente.
- `catalogo_operativo.tipo_cop_operativo`: ORIGEN, ADICIONAL, 2A_ADICIONAL, COMPLEMENTARIAS, TRANSVERSALES.
- `indemnizacion.estatus`: pendiente, programado, en_proceso, completo, pagado, cancelado, otro.
- `expediente_requisito.entidad_tipo`: incluye orv, padron_historial, actividad_campo, asamblea, asamblea_convocatoria.
- `parcela.no_parcela`: único número funcional; no existe número PPT paralelo.
- `tramite_ran.fecha_programada_ingreso` y `tramite_ran_evento`: fechas, solicitudes, calificación e inscripción canónicas.
- `Asamblea` y `AsambleaConvocatoria`: una Asamblea es la unidad de conteo; convocatorias son 1:N y sólo la convocatoria con resultado `celebrada` aporta su fecha realizada. Una Asamblea de tipo/contexto `retiro_fondos` genera un único hito retiro, sin depender de texto libre ni de `seguimiento_evento`.
- `TramiteRan` y `TramiteRanEvento`: el trámite se vincula exactamente a Asamblea, Convenio u ORV; ingreso usa el primer evento `ingreso`/`reingreso`, y la inscripción sólo `fecha_evento` de evento `inscripcion`. Calificación, alta técnica y otros eventos no sustituyen inscripción.
- `Convenio`: conserva independientemente `ambito`, `tipo_convenio`, firmas, superficie y monto. `vw_convenio_tipo_cop_operativo` deriva COP desde afectaciones activas únicamente cuando es inequívoco; si hay ORIGEN y ADICIONAL, el COP queda `NULL` para revisión, nunca se elige uno.
- `AfectacionUnidadAgraria`: relación canónica para superficie por destino (`superficie_afectada_ha`); no se repite la superficie total de Afectacion por cada destino. Parcelas y núcleos son snapshots sin fecha histórica canónica.
- `TramiteFifonafe`/`TramiteFifonafeEvento`: colectivo se completa con los cuatro oficios fechados y fecha `MAX(fecha_oficio)`; individual no exige esa cadena. `hay_conflictos=false` es el hecho de no conflictos y no equivale por sí mismo a los cuatro oficios.
- `Indemnizacion`: `fecha_resolucion` es la única fecha realizada para reporting; estatus `pagado` sin ella permanece sin periodo y no exige Pago.
- `vw_hito_seguimiento`: vista hito canónica que normaliza `clave_hito`, indicador, fechas de negocio, ámbito, COP, convenio, destino, cantidad, superficie y monto. Incluye snapshots sin fecha (núcleos, parcelas, superficies administrativas/destino) para consulta técnica, pero no los fecha con `creado_en`.
- `vw_reporte_avance_periodo`: desglose temporal de 15 columnas (`id_proyecto`, `id_entidad`, `ambito`, `tipo_cop_operativo`, `tipo_convenio`, `destino_superficie`, `anio`, `mes`, `trimestre`, `indicador`, `programado`, `realizado`, `cantidad`, `superficie_ha`, `monto`). Sólo proyecta fechas canónicas; trimestre deriva de la fecha.
- `vw_dashboard_kpi`: agregación anual directa sobre hitos deduplicados. `cantidad` cuenta `clave_hito` distinta; superficie/monto se proyectan sólo en realizado, por lo que programación y firma no los duplican.
- `docs/backend/MATRIZ_COBERTURA_EXCEL_V1.md`: trazabilidad exhaustiva Excel V1, incluyendo tratamiento PERSISTIR/DERIVAR/DOCUMENTAR/REVISAR/NO_PERSISTIR_AUXILIAR.
