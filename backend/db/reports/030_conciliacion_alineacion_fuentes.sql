\set ON_ERROR_STOP on
\pset pager off

-- Reporte de sólo lectura. No infiere relaciones ni modifica datos.
SELECT current_database() AS base,
       CURRENT_TIMESTAMP AS generado_en,
       MAX(version) AS ultima_migracion
  FROM schema_migrations;

SELECT tipo_tramite,
       estatus,
       COUNT(*) AS total,
       COUNT(*) FILTER (
           WHERE no_oficio_fifonafe_a_dgaopr IS NOT NULL
              OR no_oficio_dgaopr_a_repr IS NOT NULL
              OR no_oficio_rpta_repr_a_dgaopr IS NOT NULL
              OR no_oficio_rpta_dgaopr_a_fifonafe IS NOT NULL
       ) AS con_algun_oficio,
       CASE
           WHEN tipo_tramite = 'indemnizacion'
               THEN 'REQUIERE REVISION MANUAL: preservar; no atribuir ni limpiar sin evidencia'
           ELSE 'MIGRADO AUTOMATICAMENTE: regla documental validada por tipo'
       END AS clasificacion
  FROM tramite_fifonafe
 WHERE activo IS TRUE
 GROUP BY tipo_tramite, estatus
 ORDER BY tipo_tramite, estatus;

SELECT o.id_orv,
       o.id_nucleo,
       o.numero_orv,
       o.acta_eleccion_inscrita_ran,
       o.documentacion_disponible,
       COUNT(oi.id_orv_integrante) AS integrantes_normalizados,
       CASE
           WHEN COUNT(oi.id_orv_integrante) = 0
               THEN 'REQUIERE REVISION MANUAL'
           ELSE 'MIGRADO AUTOMATICAMENTE'
       END AS clasificacion
  FROM orv o
  LEFT JOIN orv_integrante oi
    ON oi.id_orv = o.id_orv
   AND oi.activo IS TRUE
 WHERE o.activo IS TRUE
 GROUP BY o.id_orv, o.id_nucleo, o.numero_orv,
          o.acta_eleccion_inscrita_ran, o.documentacion_disponible
 ORDER BY o.id_orv;

SELECT a.id_asamblea,
       a.id_nucleo,
       a.id_afectacion,
       a.id_ciclo_afectacion,
       a.tipo_asamblea,
       a.estatus_asamblea,
       a.id_padron,
       CASE
           WHEN a.id_padron IS NOT NULL THEN 'MIGRADO AUTOMATICAMENTE'
           WHEN a.estatus_asamblea = 'completo' THEN 'REQUIERE REVISION MANUAL'
           ELSE 'NO MIGRABLE SIN EVIDENCIA'
       END AS clasificacion
  FROM asamblea a
 WHERE a.activo IS TRUE
 ORDER BY a.id_asamblea;

SELECT c.id_convenio,
       c.tipo_afectacion,
       c.tipo_convenio,
       c.fecha_firma,
       c.monto_100,
       c.monto_90,
       c.monto_bdt,
       CASE
           WHEN c.fecha_firma IS NULL THEN 'NO MIGRABLE SIN EVIDENCIA'
           WHEN c.monto_100 IS NULL
             OR (
                 c.tipo_convenio NOT IN ('modificatorio', 'obras_complementarias')
                 AND c.monto_bdt IS NULL
             ) THEN 'REQUIERE REVISION MANUAL'
           ELSE 'MIGRADO AUTOMATICAMENTE'
       END AS clasificacion
  FROM convenio c
 WHERE c.activo IS TRUE
 ORDER BY c.id_convenio;

SELECT tipo_actividad,
       contexto_proceso,
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE fecha_programada IS NOT NULL) AS con_programacion,
       COUNT(*) FILTER (WHERE fecha_realizada IS NOT NULL) AS realizadas,
       COUNT(*) FILTER (WHERE NULLIF(BTRIM(resultado), '') IS NOT NULL) AS con_resultado,
       'PRESERVADO: completar sólo con evidencia de campo' AS clasificacion
  FROM actividad_campo
 WHERE activo IS TRUE
 GROUP BY tipo_actividad, contexto_proceso
 ORDER BY tipo_actividad, contexto_proceso;

SELECT categoria,
       entidad_relacionada_tipo,
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE NULLIF(BTRIM(url_archivo), '') IS NOT NULL) AS con_archivo,
       'PRESERVADO: no inferir documento, relación ni archivo faltante' AS clasificacion
  FROM documentacion_soporte
 WHERE activo IS TRUE
 GROUP BY categoria, entidad_relacionada_tipo
 ORDER BY categoria, entidad_relacionada_tipo;

WITH resumen AS (
    SELECT 'MIGRADO AUTOMATICAMENTE' AS estado,
           (
               (SELECT COUNT(*) FROM tramite_fifonafe
                 WHERE activo IS TRUE AND tipo_tramite = 'informe_no_conflictos')
               + (SELECT COUNT(*) FROM orv o WHERE o.activo IS TRUE AND EXISTS (
                   SELECT 1 FROM orv_integrante oi
                    WHERE oi.id_orv = o.id_orv AND oi.activo IS TRUE
               ))
               + (SELECT COUNT(*) FROM asamblea
                   WHERE activo IS TRUE AND id_padron IS NOT NULL)
               + (SELECT COUNT(*) FROM convenio
                   WHERE activo IS TRUE
                     AND fecha_firma IS NOT NULL
                     AND monto_100 IS NOT NULL
                     AND (tipo_convenio IN ('modificatorio', 'obras_complementarias')
                          OR monto_bdt IS NOT NULL))
           )::BIGINT AS registros
    UNION ALL
    SELECT 'REQUIERE REVISION MANUAL', (
        (SELECT COUNT(*) FROM tramite_fifonafe
          WHERE activo IS TRUE
            AND tipo_tramite = 'indemnizacion'
            AND (no_oficio_fifonafe_a_dgaopr IS NOT NULL
                 OR no_oficio_dgaopr_a_repr IS NOT NULL
                 OR no_oficio_rpta_repr_a_dgaopr IS NOT NULL
                 OR no_oficio_rpta_dgaopr_a_fifonafe IS NOT NULL))
        + (SELECT COUNT(*) FROM orv o
            WHERE o.activo IS TRUE AND NOT EXISTS (
                SELECT 1 FROM orv_integrante oi
                 WHERE oi.id_orv = o.id_orv AND oi.activo IS TRUE
            ))
        + (SELECT COUNT(*) FROM asamblea
            WHERE activo IS TRUE AND id_padron IS NULL
              AND estatus_asamblea = 'completo')
        + (SELECT COUNT(*) FROM convenio
            WHERE activo IS TRUE AND fecha_firma IS NOT NULL
              AND (monto_100 IS NULL
                   OR (tipo_convenio NOT IN ('modificatorio', 'obras_complementarias')
                       AND monto_bdt IS NULL)))
        + (SELECT COUNT(*) FROM actividad_campo
            WHERE activo IS TRUE AND fecha_realizada IS NOT NULL
              AND (fecha_programada IS NULL OR NULLIF(BTRIM(resultado), '') IS NULL))
    )::BIGINT
    UNION ALL
    SELECT 'NO MIGRABLE SIN EVIDENCIA', (
        (SELECT COUNT(*) FROM asamblea
          WHERE activo IS TRUE AND id_padron IS NULL
            AND estatus_asamblea <> 'completo')
        + (SELECT COUNT(*) FROM convenio
            WHERE activo IS TRUE AND fecha_firma IS NULL)
    )::BIGINT
)
SELECT estado, registros FROM resumen ORDER BY estado;
