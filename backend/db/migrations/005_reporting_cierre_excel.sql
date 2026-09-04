-- Cierre definitivo del reporting derivado de los Excel colectivos e individuales.
-- Las migraciones 001, 002, 003 y 004 son inmutables.
SET search_path = public, pg_catalog;

DROP VIEW IF EXISTS vw_dashboard_kpi CASCADE;
DROP VIEW IF EXISTS vw_reporte_avance_periodo CASCADE;
DROP VIEW IF EXISTS vw_hito_seguimiento CASCADE;

CREATE OR REPLACE VIEW vw_hito_seguimiento AS
-- 1. Núcleos agrarios: snapshot. ProyectoNucleo.creado_en es fecha de sistema,
-- no la fecha histórica en la que el núcleo fue afectado por el proyecto.
SELECT
  pn.id_proyecto,
  e.id_entidad,
  pn.id_proyecto_nucleo,
  'colectivo'::text AS ambito,
  NULL::text AS tipo_cop_operativo,
  NULL::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'nucleo:' || pn.id_proyecto_nucleo::text AS clave_hito,
  'nucleos'::text AS indicador,
  NULL::date AS fecha_programada,
  NULL::date AS fecha_realizada,
  1::bigint AS cantidad,
  NULL::numeric AS superficie_ha,
  NULL::numeric AS monto
FROM proyecto_nucleo pn
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
WHERE pn.activo
UNION ALL
-- 2. Actividades de campo (sensibilización y caminamiento deduplicados por PN + actividad + ciclo)
SELECT
  pn.id_proyecto,
  e.id_entidad,
  pn.id_proyecto_nucleo,
  coalesce(min(af.tipo_afectacion), 'colectivo')::text AS ambito,
  c.codigo AS tipo_cop_operativo,
  NULL::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'actividad:' || pn.id_proyecto_nucleo::text || ':' || a.tipo_actividad || ':' || coalesce(a.id_tipo_cop_operativo, 0)::text AS clave_hito,
  a.tipo_actividad || '_' || coalesce(c.codigo, 'SIN_CICLO') AS indicador,
  min(a.fecha_programada) AS fecha_programada,
  min(a.fecha_realizada) AS fecha_realizada,
  1::bigint AS cantidad,
  NULL::numeric AS superficie_ha,
  NULL::numeric AS monto
FROM actividad_campo a
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
LEFT JOIN catalogo_operativo c ON c.id_catalogo_opcion = a.id_tipo_cop_operativo
LEFT JOIN afectacion af ON af.id_afectacion = a.id_afectacion AND af.activo
WHERE a.activo AND pn.activo AND (a.fecha_programada IS NOT NULL OR a.fecha_realizada IS NOT NULL)
GROUP BY pn.id_proyecto, e.id_entidad, pn.id_proyecto_nucleo, a.tipo_actividad, a.id_tipo_cop_operativo, c.codigo
UNION ALL
-- 3. Asambleas (indicador compatible general 'asambleas')
SELECT
  pn.id_proyecto,
  e.id_entidad,
  a.id_proyecto_nucleo,
  'colectivo'::text AS ambito,
  NULL::text AS tipo_cop_operativo,
  NULL::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'asamblea:' || a.id_asamblea::text AS clave_hito,
  'asambleas'::text AS indicador,
  min(ac.fecha_programada) AS fecha_programada,
  min(ac.fecha_realizacion) FILTER (WHERE r.codigo = 'celebrada') AS fecha_realizada,
  1::bigint AS cantidad,
  NULL::numeric AS superficie_ha,
  NULL::numeric AS monto
FROM asamblea a
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
JOIN asamblea_convocatoria ac ON ac.id_asamblea = a.id_asamblea
LEFT JOIN catalogo_operativo r ON r.id_catalogo_opcion = ac.id_resultado
WHERE a.activo AND pn.activo AND ac.activo
GROUP BY pn.id_proyecto, e.id_entidad, a.id_proyecto_nucleo, a.id_asamblea
HAVING min(ac.fecha_programada) IS NOT NULL OR min(ac.fecha_realizacion) FILTER (WHERE r.codigo = 'celebrada') IS NOT NULL
UNION ALL
-- 3b. Asambleas específicas de retiro de fondos
SELECT
  pn.id_proyecto,
  e.id_entidad,
  a.id_proyecto_nucleo,
  'colectivo'::text AS ambito,
  NULL::text AS tipo_cop_operativo,
  NULL::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'retiro_fondos:' || a.id_asamblea::text AS clave_hito,
  'retiro_fondos'::text AS indicador,
  min(ac.fecha_programada) AS fecha_programada,
  min(ac.fecha_realizacion) FILTER (WHERE r.codigo = 'celebrada') AS fecha_realizada,
  1::bigint AS cantidad,
  NULL::numeric AS superficie_ha,
  NULL::numeric AS monto
FROM asamblea a
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
JOIN asamblea_convocatoria ac ON ac.id_asamblea = a.id_asamblea
LEFT JOIN catalogo_operativo r ON r.id_catalogo_opcion = ac.id_resultado
LEFT JOIN catalogo_operativo ta ON ta.id_catalogo_opcion = a.id_tipo_asamblea
LEFT JOIN catalogo_operativo ca ON ca.id_catalogo_opcion = a.id_contexto_asamblea
WHERE a.activo AND pn.activo AND ac.activo
  AND (ta.codigo = 'retiro_fondos' OR ca.codigo = 'retiro_fondos')
GROUP BY pn.id_proyecto, e.id_entidad, a.id_proyecto_nucleo, a.id_asamblea
HAVING min(ac.fecha_programada) IS NOT NULL OR min(ac.fecha_realizacion) FILTER (WHERE r.codigo = 'celebrada') IS NOT NULL
UNION ALL
-- 4a. RAN ingreso (acta / convenio)
SELECT
  pn.id_proyecto,
  e.id_entidad,
  tr.id_proyecto_nucleo,
  coalesce(c.ambito, 'colectivo')::text AS ambito,
  vco.tipo_cop_operativo_codigo AS tipo_cop_operativo,
  c.tipo_convenio::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'ran_ingreso:' || tr.id_tramite_ran::text AS clave_hito,
  'ingreso_ran_' || CASE WHEN tr.id_asamblea IS NOT NULL THEN 'acta' ELSE 'convenio' END AS indicador,
  tr.fecha_programada_ingreso AS fecha_programada,
  min(ev.fecha_evento) FILTER (WHERE t.codigo IN ('ingreso', 'reingreso')) AS fecha_realizada,
  1::bigint AS cantidad,
  NULL::numeric AS superficie_ha,
  NULL::numeric AS monto
FROM tramite_ran tr
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = tr.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
LEFT JOIN convenio c ON c.id_convenio = tr.id_convenio
LEFT JOIN vw_convenio_tipo_cop_operativo vco ON vco.id_convenio = tr.id_convenio
LEFT JOIN tramite_ran_evento ev ON ev.id_tramite_ran = tr.id_tramite_ran AND ev.activo
LEFT JOIN catalogo_operativo t ON t.id_catalogo_opcion = ev.id_tipo_evento
WHERE tr.activo AND pn.activo AND (tr.id_asamblea IS NOT NULL OR tr.id_convenio IS NOT NULL)
GROUP BY pn.id_proyecto, e.id_entidad, tr.id_proyecto_nucleo, tr.id_tramite_ran, tr.id_asamblea, c.ambito, vco.tipo_cop_operativo_codigo, c.tipo_convenio, tr.fecha_programada_ingreso
HAVING tr.fecha_programada_ingreso IS NOT NULL OR min(ev.fecha_evento) FILTER (WHERE t.codigo IN ('ingreso', 'reingreso')) IS NOT NULL
UNION ALL
-- 4b. RAN inscripción (acta / convenio)
SELECT
  pn.id_proyecto,
  e.id_entidad,
  tr.id_proyecto_nucleo,
  coalesce(c.ambito, 'colectivo')::text AS ambito,
  vco.tipo_cop_operativo_codigo AS tipo_cop_operativo,
  c.tipo_convenio::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'ran_inscripcion:' || tr.id_tramite_ran::text AS clave_hito,
  'inscripcion_ran_' || CASE WHEN tr.id_asamblea IS NOT NULL THEN 'acta' ELSE 'convenio' END AS indicador,
  NULL::date AS fecha_programada,
  min(ev.fecha_evento) FILTER (WHERE t.codigo = 'inscripcion') AS fecha_realizada,
  1::bigint AS cantidad,
  NULL::numeric AS superficie_ha,
  NULL::numeric AS monto
FROM tramite_ran tr
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = tr.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
LEFT JOIN convenio c ON c.id_convenio = tr.id_convenio
LEFT JOIN vw_convenio_tipo_cop_operativo vco ON vco.id_convenio = tr.id_convenio
JOIN tramite_ran_evento ev ON ev.id_tramite_ran = tr.id_tramite_ran AND ev.activo
JOIN catalogo_operativo t ON t.id_catalogo_opcion = ev.id_tipo_evento AND t.codigo = 'inscripcion'
WHERE tr.activo AND pn.activo AND (tr.id_asamblea IS NOT NULL OR tr.id_convenio IS NOT NULL)
GROUP BY pn.id_proyecto, e.id_entidad, tr.id_proyecto_nucleo, tr.id_tramite_ran, tr.id_asamblea, c.ambito, vco.tipo_cop_operativo_codigo, c.tipo_convenio
HAVING min(ev.fecha_evento) FILTER (WHERE t.codigo = 'inscripcion') IS NOT NULL
UNION ALL
-- 5. Convenios (un convenio = una unidad)
SELECT
  pn.id_proyecto,
  e.id_entidad,
  c.id_proyecto_nucleo,
  c.ambito::text AS ambito,
  vco.tipo_cop_operativo_codigo AS tipo_cop_operativo,
  c.tipo_convenio::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'convenio:' || c.id_convenio::text AS clave_hito,
  CASE
    WHEN c.tipo_convenio = 'cop_original' AND c.ambito = 'colectivo' THEN 'cop_colectivos'
    WHEN c.tipo_convenio = 'cop_original' AND c.ambito = 'individual' THEN 'cop_individuales'
    ELSE c.tipo_convenio::text
  END AS indicador,
  c.fecha_programada_firma AS fecha_programada,
  c.fecha_firma AS fecha_realizada,
  1::bigint AS cantidad,
  c.superficie_ha::numeric AS superficie_ha,
  c.monto_100::numeric AS monto
FROM convenio c
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = c.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
LEFT JOIN vw_convenio_tipo_cop_operativo vco ON vco.id_convenio = c.id_convenio
WHERE c.activo AND pn.activo AND (c.fecha_programada_firma IS NOT NULL OR c.fecha_firma IS NOT NULL)
UNION ALL
-- 6. Parcelas afectadas (una parcela = una unidad; snapshot sin fecha canónica).
-- La creación/importación de afectación, parcela o unidad no es un hecho temporal
-- de negocio y por tanto no se proyecta artificialmente al reporte por periodo.
SELECT
  pn.id_proyecto,
  e.id_entidad,
  pn.id_proyecto_nucleo,
  'individual'::text AS ambito,
  NULL::text AS tipo_cop_operativo,
  NULL::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'parcela:' || ua.id_parcela::text AS clave_hito,
  'parcelas_afectadas'::text AS indicador,
  NULL::date AS fecha_programada,
  NULL::date AS fecha_realizada,
  1::bigint AS cantidad,
  NULL::numeric AS superficie_ha,
  NULL::numeric AS monto
FROM afectacion a
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
JOIN afectacion_unidad_agraria au ON au.id_afectacion = a.id_afectacion AND au.activo
JOIN unidad_agraria ua ON ua.id_unidad_agraria = au.id_unidad_agraria AND ua.activo
WHERE a.activo AND pn.activo AND ua.id_parcela IS NOT NULL
GROUP BY pn.id_proyecto, e.id_entidad, pn.id_proyecto_nucleo, ua.id_parcela
UNION ALL
-- 7a. Destino de superficie (asociación específica AfectacionUnidadAgraria;
-- snapshot sin fecha canónica de negocio)
SELECT
  pn.id_proyecto,
  e.id_entidad,
  pn.id_proyecto_nucleo,
  a.tipo_afectacion::text AS ambito,
  co_cop.codigo AS tipo_cop_operativo,
  NULL::text AS tipo_convenio,
  co_dest.codigo AS destino_superficie,
  'superficie_destino:' || au.id_afectacion_unidad::text AS clave_hito,
  'superficie_por_destino'::text AS indicador,
  NULL::date AS fecha_programada,
  NULL::date AS fecha_realizada,
  1::bigint AS cantidad,
  au.superficie_afectada_ha::numeric AS superficie_ha,
  NULL::numeric AS monto
FROM afectacion_unidad_agraria au
JOIN afectacion a ON a.id_afectacion = au.id_afectacion AND a.activo
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo AND pn.activo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
JOIN unidad_agraria ua ON ua.id_unidad_agraria = au.id_unidad_agraria AND ua.activo
JOIN catalogo_operativo co_dest ON co_dest.id_catalogo_opcion = ua.id_destino_superficie
LEFT JOIN catalogo_operativo co_cop ON co_cop.id_catalogo_opcion = a.id_tipo_cop_operativo
WHERE au.activo AND ua.id_destino_superficie IS NOT NULL
UNION ALL
-- 7b. Superficie afectada administrativa total por afectación (snapshot)
SELECT
  pn.id_proyecto,
  e.id_entidad,
  pn.id_proyecto_nucleo,
  a.tipo_afectacion::text AS ambito,
  co_cop.codigo AS tipo_cop_operativo,
  NULL::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'afectacion_admin:' || a.id_afectacion::text AS clave_hito,
  'superficie_afectada_administrativa'::text AS indicador,
  NULL::date AS fecha_programada,
  NULL::date AS fecha_realizada,
  1::bigint AS cantidad,
  a.superficie_afectada_ha::numeric AS superficie_ha,
  NULL::numeric AS monto
FROM afectacion a
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
LEFT JOIN catalogo_operativo co_cop ON co_cop.id_catalogo_opcion = a.id_tipo_cop_operativo
WHERE a.activo AND pn.activo AND a.superficie_afectada_ha IS NOT NULL
UNION ALL
-- 8. Indemnizaciones
SELECT
  pn.id_proyecto,
  e.id_entidad,
  pn.id_proyecto_nucleo,
  a.tipo_afectacion::text AS ambito,
  co_cop.codigo AS tipo_cop_operativo,
  NULL::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'indemnizacion:' || i.id_indemnizacion::text AS clave_hito,
  'indemnizaciones'::text AS indicador,
  i.fecha_programada AS fecha_programada,
  i.fecha_resolucion AS fecha_realizada,
  1::bigint AS cantidad,
  a.superficie_afectada_ha::numeric AS superficie_ha,
  a.avaluo_monto::numeric AS monto
FROM indemnizacion i
JOIN afectacion a ON a.id_afectacion = i.id_afectacion AND a.activo
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo AND pn.activo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
LEFT JOIN catalogo_operativo co_cop ON co_cop.id_catalogo_opcion = a.id_tipo_cop_operativo
WHERE i.activo AND (i.fecha_programada IS NOT NULL OR i.fecha_resolucion IS NOT NULL)
UNION ALL
-- 9a. FIFONAFE general
SELECT
  pn.id_proyecto,
  e.id_entidad,
  t.id_proyecto_nucleo,
  t.ambito::text AS ambito,
  NULL::text AS tipo_cop_operativo,
  NULL::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'fifonafe:' || t.id_tramite_fifonafe::text AS clave_hito,
  'fifonafe'::text AS indicador,
  -- El estatus no aporta por sí mismo una fecha programada canónica.
  NULL::date AS fecha_programada,
  CASE
    WHEN t.ambito = 'colectivo' AND count(DISTINCT tco.codigo) FILTER (WHERE tco.codigo IN (
      'oficio_fifonafe_dgaopr',
      'oficio_dgaopr_representacion',
      'respuesta_representacion_dgaopr',
      'respuesta_dgaopr_fifonafe'
    ) AND fe.fecha_oficio IS NOT NULL) = 4 THEN max(fe.fecha_oficio)
    WHEN t.ambito = 'individual' AND t.estatus = 'completo' THEN coalesce(max(fe.fecha_oficio), t.acuse_fifonafe_fecha)
    WHEN t.estatus = 'completo' THEN coalesce(max(fe.fecha_oficio), t.acuse_fifonafe_fecha)
    ELSE NULL::date
  END AS fecha_realizada,
  1::bigint AS cantidad,
  NULL::numeric AS superficie_ha,
  NULL::numeric AS monto
FROM tramite_fifonafe t
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = t.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
LEFT JOIN tramite_fifonafe_evento fe ON fe.id_tramite_fifonafe = t.id_tramite_fifonafe AND fe.activo
LEFT JOIN catalogo_operativo tco ON tco.id_catalogo_opcion = fe.id_tipo_evento
WHERE t.activo AND pn.activo
GROUP BY t.id_tramite_fifonafe, pn.id_proyecto, e.id_entidad, t.id_proyecto_nucleo, t.ambito, t.estatus, t.acuse_fifonafe_fecha
HAVING (CASE
    WHEN t.ambito = 'colectivo' AND count(DISTINCT tco.codigo) FILTER (WHERE tco.codigo IN (
      'oficio_fifonafe_dgaopr',
      'oficio_dgaopr_representacion',
      'respuesta_representacion_dgaopr',
      'respuesta_dgaopr_fifonafe'
    ) AND fe.fecha_oficio IS NOT NULL) = 4 THEN max(fe.fecha_oficio)
    WHEN t.ambito = 'individual' AND t.estatus = 'completo' THEN coalesce(max(fe.fecha_oficio), t.acuse_fifonafe_fecha)
    WHEN t.estatus = 'completo' THEN coalesce(max(fe.fecha_oficio), t.acuse_fifonafe_fecha)
    ELSE NULL::date
  END) IS NOT NULL
UNION ALL
-- 9b. Informe de no conflictos FIFONAFE
SELECT
  pn.id_proyecto,
  e.id_entidad,
  t.id_proyecto_nucleo,
  t.ambito::text AS ambito,
  NULL::text AS tipo_cop_operativo,
  NULL::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'no_conflictos:' || t.id_tramite_fifonafe::text AS clave_hito,
  'informe_no_conflictos'::text AS indicador,
  NULL::date AS fecha_programada,
  CASE
    WHEN t.ambito = 'colectivo' AND count(DISTINCT tco.codigo) FILTER (WHERE tco.codigo IN (
      'oficio_fifonafe_dgaopr',
      'oficio_dgaopr_representacion',
      'respuesta_representacion_dgaopr',
      'respuesta_dgaopr_fifonafe'
    ) AND fe.fecha_oficio IS NOT NULL) = 4 THEN max(fe.fecha_oficio)
    WHEN t.ambito = 'individual' AND t.estatus = 'completo' THEN coalesce(max(fe.fecha_oficio), t.acuse_fifonafe_fecha)
    ELSE coalesce(max(fe.fecha_oficio), t.acuse_fifonafe_fecha)
  END AS fecha_realizada,
  1::bigint AS cantidad,
  NULL::numeric AS superficie_ha,
  NULL::numeric AS monto
FROM tramite_fifonafe t
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = t.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
LEFT JOIN tramite_fifonafe_evento fe ON fe.id_tramite_fifonafe = t.id_tramite_fifonafe AND fe.activo
LEFT JOIN catalogo_operativo tco ON tco.id_catalogo_opcion = fe.id_tipo_evento
WHERE t.activo AND pn.activo AND t.hay_conflictos = false
GROUP BY t.id_tramite_fifonafe, pn.id_proyecto, e.id_entidad, t.id_proyecto_nucleo, t.ambito, t.estatus, t.acuse_fifonafe_fecha
HAVING (CASE
    WHEN t.ambito = 'colectivo' AND count(DISTINCT tco.codigo) FILTER (WHERE tco.codigo IN (
      'oficio_fifonafe_dgaopr',
      'oficio_dgaopr_representacion',
      'respuesta_representacion_dgaopr',
      'respuesta_dgaopr_fifonafe'
    ) AND fe.fecha_oficio IS NOT NULL) = 4 THEN max(fe.fecha_oficio)
    WHEN t.ambito = 'individual' AND t.estatus = 'completo' THEN coalesce(max(fe.fecha_oficio), t.acuse_fifonafe_fecha)
    ELSE coalesce(max(fe.fecha_oficio), t.acuse_fifonafe_fecha)
  END) IS NOT NULL
UNION ALL
-- 10a. Seguimiento funcional 004 por tipo de evento
SELECT
  pn.id_proyecto,
  e.id_entidad,
  se.id_proyecto_nucleo,
  se.ambito::text AS ambito,
  NULL::text AS tipo_cop_operativo,
  NULL::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'seguimiento_evento:' || se.id_seguimiento_evento::text AS clave_hito,
  co.codigo AS indicador,
  NULL::date AS fecha_programada,
  se.fecha_evento AS fecha_realizada,
  1::bigint AS cantidad,
  NULL::numeric AS superficie_ha,
  NULL::numeric AS monto
FROM seguimiento_evento se
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = se.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
JOIN catalogo_operativo co ON co.id_catalogo_opcion = se.id_tipo_evento
WHERE se.activo AND pn.activo AND se.fecha_evento IS NOT NULL
UNION ALL
-- 10b. Seguimiento funcional 004 por motivo
SELECT
  pn.id_proyecto,
  e.id_entidad,
  se.id_proyecto_nucleo,
  se.ambito::text AS ambito,
  NULL::text AS tipo_cop_operativo,
  NULL::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'seguimiento_motivo:' || se.id_seguimiento_evento::text AS clave_hito,
  mo.codigo AS indicador,
  NULL::date AS fecha_programada,
  se.fecha_evento AS fecha_realizada,
  1::bigint AS cantidad,
  NULL::numeric AS superficie_ha,
  NULL::numeric AS monto
FROM seguimiento_evento se
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = se.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
JOIN catalogo_operativo mo ON mo.id_catalogo_opcion = se.id_motivo
WHERE se.activo AND pn.activo AND se.id_motivo IS NOT NULL AND se.fecha_evento IS NOT NULL;

-- Vista de reporte de avance por periodo (mes/trimestre/año) con separación estricta
-- de fechas programadas y realizadas para evitar distorsiones temporales.
CREATE OR REPLACE VIEW vw_reporte_avance_periodo AS
WITH filas_temporales AS (
    SELECT
        id_proyecto,
        id_entidad,
        ambito,
        tipo_cop_operativo,
        tipo_convenio,
        destino_superficie,
        clave_hito,
        indicador,
        fecha_programada AS fecha,
        1::bigint AS programado,
        0::bigint AS realizado,
        NULL::numeric AS superficie_ha,
        NULL::numeric AS monto
    FROM vw_hito_seguimiento
    WHERE fecha_programada IS NOT NULL
    UNION ALL
    SELECT
        id_proyecto,
        id_entidad,
        ambito,
        tipo_cop_operativo,
        tipo_convenio,
        destino_superficie,
        clave_hito,
        indicador,
        fecha_realizada AS fecha,
        0::bigint AS programado,
        1::bigint AS realizado,
        superficie_ha,
        monto
    FROM vw_hito_seguimiento
    WHERE fecha_realizada IS NOT NULL
)
SELECT
    id_proyecto,
    id_entidad,
    ambito,
    tipo_cop_operativo,
    tipo_convenio,
    destino_superficie,
    extract(year FROM fecha)::integer AS anio,
    extract(month FROM fecha)::integer AS mes,
    extract(quarter FROM fecha)::integer AS trimestre,
    indicador,
    sum(programado)::bigint AS programado,
    sum(realizado)::bigint AS realizado,
    count(DISTINCT clave_hito)::bigint AS cantidad,
    sum(superficie_ha)::numeric AS superficie_ha,
    sum(monto)::numeric AS monto
FROM filas_temporales
WHERE (indicador IS NOT NULL OR (indicador = ANY (ARRAY[
  'inscripcion_ran_'::text || 'acta'::text,
  'convenio'::text,
  'asamblea_convocatoria'::text,
  'tramite_ran_evento'::text,
  'afectacion_unidad_agraria'::text
])))
GROUP BY
    id_proyecto,
    id_entidad,
    ambito,
    tipo_cop_operativo,
    tipo_convenio,
    destino_superficie,
    extract(year FROM fecha),
    extract(month FROM fecha),
    extract(quarter FROM fecha),
    indicador;

-- Dashboard anual que agrega directamente sobre los hitos deduplicados
-- garantizando que cada entidad canónica cuenta exactamente una vez por año.
CREATE OR REPLACE VIEW vw_dashboard_kpi AS
WITH filas_anuales AS (
    SELECT
        id_proyecto,
        extract(year FROM fecha_programada)::integer AS anio,
        indicador,
        clave_hito,
        1::bigint AS programado,
        0::bigint AS realizado,
        NULL::numeric AS superficie_ha,
        NULL::numeric AS monto
    FROM vw_hito_seguimiento
    WHERE fecha_programada IS NOT NULL
    UNION ALL
    SELECT
        id_proyecto,
        extract(year FROM fecha_realizada)::integer AS anio,
        indicador,
        clave_hito,
        0::bigint AS programado,
        1::bigint AS realizado,
        superficie_ha,
        monto
    FROM vw_hito_seguimiento
    WHERE fecha_realizada IS NOT NULL
)
SELECT
    id_proyecto,
    anio,
    indicador,
    sum(programado)::bigint AS programado,
    sum(realizado)::bigint AS realizado,
    count(DISTINCT clave_hito)::bigint AS cantidad,
    sum(superficie_ha)::numeric AS superficie_ha,
    sum(monto)::numeric AS monto
FROM filas_anuales
GROUP BY id_proyecto, anio, indicador;

GRANT SELECT ON vw_hito_seguimiento TO software_pa_app;
GRANT SELECT ON vw_reporte_avance_periodo TO software_pa_app;
GRANT SELECT ON vw_dashboard_kpi TO software_pa_app;
