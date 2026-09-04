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
- `vw_hito_seguimiento`: vista hito canónica en capa base que normaliza `clave_hito`, `indicador`, fechas canónicas (`fecha_programada`, `fecha_realizada`), dimensiones de segmentación (`ambito`, `tipo_cop_operativo`, `tipo_convenio`, `destino_superficie`), `cantidad`, `superficie_ha` y `monto`. Deduplica antes de proyectar a periodos temporales.
- `vw_reporte_avance_periodo`: desglose temporal de 15 columnas (`id_proyecto`, `id_entidad`, `ambito`, `tipo_cop_operativo`, `tipo_convenio`, `destino_superficie`, `anio`, `mes`, `trimestre`, `indicador`, `programado`, `realizado`, `cantidad`, `superficie_ha`, `monto`). Proyecta `fecha_programada` y `fecha_realizada` en sus periodos respectivos sin inventar periodos ni duplicar cantidades.
- `vw_dashboard_kpi`: agregación de alto nivel compatible por `id_proyecto, anio, indicador`, deduplicada a nivel anual.
