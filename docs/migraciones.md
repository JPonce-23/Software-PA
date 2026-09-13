# Migraciones vigentes

El runner aplica automáticamente archivos `NNN_*.sql` en orden y verifica checksum de los ya registrados.

Instalación limpia: `001_baseline_v1.sql` → `002_cierre_fuentes_excel.sql` → `003_reporting_fuentes_excel.sql` → `004_seguimiento_funcional_excel.sql` → `005_reporting_cierre_excel.sql` → `006_ajustes_reporting_post_auditoria.sql` → `007_convenios_impactos_precision.sql` → `008_fifonafe_evolucion_forward_only.sql` → `009_bitacora_append_only.sql` → `010_credenciales_auditoria.sql` → `011_auditoria_actor_update.sql` → `012_correccion_snapshot_tuc_triestado.sql` → `013_pagos_en_reporting.sql` → `014_convenios_colectivos_por_destino.sql` → `015_exclusion_proyectos_inactivos.sql`.

- 001: baseline canónico inmutable.
- 002: cierre de fuentes Excel, ciclos COP, estados y checklist.
- 003: reporting periódico y compatibilidad dashboard.
- 004: seguimiento funcional Excel (seguimiento_evento, tipos de evento, motivos, estados documentales parcial/pendiente_validacion, requisitos PA/SICT, RAN y acta complementaria).
- 005: reporting cierre Excel definitivo (vw_hito_seguimiento, deduplicación canónica en 2 capas, vw_reporte_avance_periodo con 15 columnas y dimensiones de ámbito, cop, convenio y destino de superficie, vw_dashboard_kpi deduplicado).
- 006: ajuste forward-only post auditoría: COP de Asamblea/RAN acta, separación de retiro de fondos, regla estricta de cuatro oficios FIFONAFE, snapshot actual no temporal y validaciones de seguimiento.
- 007: convenios, impactos y precisión: precisión de 7 decimales en superficie de afectación, trazabilidad de montos e impactos, vista de cobertura.
- 008: evolución FIFONAFE forward-only.
- 009: bitácora append-only con acceso exclusivo de inserción mediante trigger de auditoría SECURITY DEFINER.
- 010: credenciales y eventos de auditoría de acceso.
- 011: auditoría obligatoria de actor en UPDATE no de sistema.
- 012: corrección del snapshot actual (vw_reporte_snapshot_actual): semántica triestado para TUC (afecta_tuc = false solo cuenta en no_afecta_tuc cuando tuc_revision_pendiente = false; afecta_tuc IS NULL nunca equivale a false ni a cero; conteo determinista sin duplicados por ProyectoNucleo y aislamiento estricto por entidad).
- 013: representación canónica de pagos en reporting (`vw_hito_seguimiento`, `vw_reporte_avance_periodo`, `vw_dashboard_kpi`): integra los pagos reales registrados mediante la cadena canónica `Pago -> Indemnizacion -> Afectacion -> ProyectoNucleo -> Proyecto`; normaliza `clave_hito = 'pago:' || p.id_pago`, `indicador = 'pagos'`, `fecha_realizada = p.fecha_pago`, `monto = p.monto`, `programado = 0`, `superficie_ha = NULL`; distingue Pago de `estatus = 'pagado'`, retiros FIFONAFE, convenios e indemnizaciones resueltas; previene duplicación por relaciones N:M y garantiza aislamiento estricto por proyecto y entidad. Checksum: `315194e6daa7b8bffd27c8d678b6e86c0486eaf851f58aba3722e90e19a37eef`.
- 014: detalle por destino de superficie para convenios colectivos (`vw_convenio_colectivo_destino`): reconstruye la superficie física por destino a partir de la cadena canónica `Convenio -> ConvenioAfectacion -> Afectacion -> AfectacionUnidadAgraria -> UnidadAgraria -> CatalogoOperativo(destino_superficie)` para instrumentos con `ambito = 'colectivo'`. Su granularidad es una fila por `id_convenio + destino_superficie`; distingue la superficie declarada del instrumento (`c.superficie_ha`) de la superficie física (`sum(au.superficie_afectada_ha)`), conserva `monto_declarado = c.monto_100` como atributo NO ADITIVO y no prorratea montos. Los consumidores que calculen cantidades oficiales deben deduplicar convenios por `id_convenio` y asambleas por `id_asamblea`; los agregados económicos oficiales deben contar cada convenio una sola vez. Checksum: `0ac8df3e32cc5bb7a103a314160fa4b6b392d9e5e041af3aaa74c0cda9aeceab`.
- 015: corrección forward-only de read-models para excluir proyectos con `activo IS NOT TRUE`. Recrea únicamente `vw_reporte_snapshot_actual`, `vw_hito_seguimiento`, `vw_reporte_avance_periodo`, `vw_dashboard_kpi` y `vw_convenio_colectivo_destino`; conserva la semántica TUC triestado, los pagos reales y la granularidad de convenios por destino. Checksum: `4e5d7fa8926f8026923146d3a0695d933bb43e9bb5f8c71ef8f9ecd9bae4b422`.

Vigentes:
- 001
- 002
- 003
- 004
- 005
- 006
- 007
- 008
- 009
- 010
- 011
- 012
- 013
- 014
- 015

El schema actual es 015 y `GET /health` debe reportar `schema: 15`. La siguiente migración disponible es 016. No se editan migraciones ya publicadas (001–015); cualquier cambio posterior se agrega mediante una nueva migración forward-only con verificación de checksum de la anterior.
