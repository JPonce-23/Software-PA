# Cambios de API respecto al Baseline V1

## 002_cierre_fuentes_excel

**Antes:** el reporte dependía de interpretaciones planas de hojas Excel y no clasificaba actividades/asambleas por ciclo operativo.

**Ahora:** `ActividadCampo` y `Asamblea` aceptan `id_tipo_cop_operativo`; el catálogo incluye `TRANSVERSALES` y el contexto de asamblea incluye `transversal`. Indemnización admite `en_proceso`, `pagado`, `cancelado`. Checklist acepta `orv`, `padron_historial`, `actividad_campo`, `asamblea`, `asamblea_convocatoria`.

**Impacto frontend:** aditivo. Las X no son campos API. RAN permanece normalizado como trámite/eventos; parcela conserva sólo `no_parcela`. FIFONAFE distingue flujo colectivo completo e individual.

## 003_reporting_fuentes_excel

**Antes:** dashboard agrupaba hitos con una fecha coalescida y no exponía inscripción RAN en forma compatible.

**Ahora:** conserva `GET /api/dashboard/kpi` y agrega `GET /api/reportes/avance-periodo`, con `id_proyecto`, `id_entidad`, `anio`, `mes`, `trimestre`, `indicador`. Recupera `inscripcion_ran_acta` e `inscripcion_ran_convenio`; ingreso y reingreso del mismo trámite cuentan una vez.

**Impacto frontend:** aditivo para el endpoint periódico; cambio de comportamiento correcto en periodos: programado y realizado se asignan a sus fechas propias. Mes/trimestre son derivados, no columnas persistidas.
