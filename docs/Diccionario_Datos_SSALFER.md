# Diccionario de datos vigente

Fuente: migraciones 001, 002 y 003.

- `actividad_campo.id_tipo_cop_operativo`: FK nullable de ciclo reportable; conserva múltiples sensibilizaciones/caminamientos.
- `asamblea.id_tipo_cop_operativo`: FK nullable de ciclo reportable; Asamblea es entidad independiente.
- `catalogo_operativo.tipo_cop_operativo`: ORIGEN, ADICIONAL, 2A_ADICIONAL, COMPLEMENTARIAS, TRANSVERSALES.
- `indemnizacion.estatus`: pendiente, programado, en_proceso, completo, pagado, cancelado, otro.
- `expediente_requisito.entidad_tipo`: incluye orv, padron_historial, actividad_campo, asamblea, asamblea_convocatoria.
- `parcela.no_parcela`: único número funcional; no existe número PPT paralelo.
- `tramite_ran.fecha_programada_ingreso` y `tramite_ran_evento`: fechas, solicitudes, calificación e inscripción canónicas.
- `vw_dashboard_kpi`: resumen compatible. `vw_reporte_avance_periodo`: proyecto, entidad, año, mes, trimestre e indicadores derivados.
