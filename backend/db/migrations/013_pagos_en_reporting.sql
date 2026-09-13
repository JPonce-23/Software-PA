-- Incorporación de pagos de indemnización en reporting (vw_hito_seguimiento, vw_reporte_avance_periodo, vw_dashboard_kpi).
-- Cadena canónica financiera: Pago -> Indemnizacion -> Afectacion -> ProyectoNucleo -> Proyecto.
-- Reglas de negocio:
-- 1. Cada Pago activo es un hecho financiero independiente.
-- 2. Su fecha de negocio es pago.fecha_pago (determina año, mes y trimestre).
-- 3. Su monto es pago.monto.
-- 4. No usar Indemnizacion.estatus = 'pagado' como sustituto de un Pago real.
-- 5. No usar Indemnizacion.fecha_resolucion como fecha del Pago.
-- 6. Un Pago no se multiplica por joins N:M (Convenio, UnidadAgraria, FIFONAFE).
-- 7. Varios pagos de una misma indemnización se conservan como hechos distintos.
-- 8. Clave de hito canónica: 'pago:' || p.id_pago. Indicador: 'pagos'.
-- 9. Aislamiento estricto por proyecto y por entidad federativa.
-- 10. Registros inactivos no participan (baja lógica respetada en toda la cadena).
SET search_path = public, pg_catalog;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM schema_migrations
    WHERE version = '012'
      AND checksum_sha256 = 'c76d2d2af326a23427ae1aaf7358fdbc62faf31d91380758f744e8c8d72a7c01'
  ) THEN
    RAISE EXCEPTION '013 requiere la migración 012 exacta';
  END IF;
  IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '013') THEN
    RAISE EXCEPTION '013 ya se encuentra registrada';
  END IF;
END $$;

SELECT pg_advisory_xact_lock(hashtextextended('software-pa:013:pagos-en-reporting', 0));

CREATE OR REPLACE VIEW vw_hito_seguimiento AS
SELECT h.id_proyecto,
       h.id_entidad,
       h.id_proyecto_nucleo,
       h.ambito,
       h.tipo_cop_operativo,
       h.tipo_convenio,
       h.destino_superficie,
       h.clave_hito,
       h.indicador,
       h.fecha_programada,
       h.fecha_realizada,
       h.cantidad,
       h.superficie_ha,
       h.monto
FROM vw_hito_seguimiento_007 h
WHERE h.indicador <> 'fifonafe'::text OR NOT (EXISTS ( SELECT 1
      FROM tramite_fifonafe t
     WHERE t.version_flujo = 2 AND h.clave_hito = ('fifonafe:'::text || t.id_tramite_fifonafe)))
UNION ALL
SELECT vw_fifonafe_hito_008.id_proyecto,
       vw_fifonafe_hito_008.id_entidad,
       vw_fifonafe_hito_008.id_proyecto_nucleo,
       vw_fifonafe_hito_008.ambito,
       vw_fifonafe_hito_008.tipo_cop_operativo,
       vw_fifonafe_hito_008.tipo_convenio,
       vw_fifonafe_hito_008.destino_superficie,
       vw_fifonafe_hito_008.clave_hito,
       vw_fifonafe_hito_008.indicador,
       vw_fifonafe_hito_008.fecha_programada,
       vw_fifonafe_hito_008.fecha_realizada,
       vw_fifonafe_hito_008.cantidad,
       vw_fifonafe_hito_008.superficie_ha,
       vw_fifonafe_hito_008.monto
FROM vw_fifonafe_hito_008
UNION ALL
-- Pagos reales de indemnización (cadena canónica Pago -> Indemnizacion -> Afectacion -> ProyectoNucleo)
SELECT
  pn.id_proyecto,
  e.id_entidad,
  pn.id_proyecto_nucleo,
  a.tipo_afectacion::text AS ambito,
  co_cop.codigo AS tipo_cop_operativo,
  NULL::text AS tipo_convenio,
  NULL::text AS destino_superficie,
  'pago:' || p.id_pago::text AS clave_hito,
  'pagos'::text AS indicador,
  NULL::date AS fecha_programada,
  p.fecha_pago AS fecha_realizada,
  1::bigint AS cantidad,
  NULL::numeric AS superficie_ha,
  p.monto::numeric AS monto
FROM pago p
JOIN indemnizacion i ON i.id_indemnizacion = p.id_indemnizacion AND i.activo
JOIN afectacion a ON a.id_afectacion = i.id_afectacion AND a.activo
JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo AND pn.activo
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
LEFT JOIN catalogo_operativo co_cop ON co_cop.id_catalogo_opcion = a.id_tipo_cop_operativo
WHERE p.activo;

COMMENT ON VIEW vw_hito_seguimiento IS
  'Hitos canónicos de seguimiento: conserva contratos 007 y FIFONAFE v2 008, e incorpora pagos reales de indemnización (indicador pagos).';

CREATE OR REPLACE VIEW vw_reporte_avance_periodo AS
WITH f AS (
  SELECT id_proyecto,id_entidad,ambito,tipo_cop_operativo,tipo_convenio,destino_superficie,clave_hito,indicador,fecha_programada fecha,1::bigint programado,0::bigint realizado,NULL::numeric superficie_ha,NULL::numeric monto FROM vw_hito_seguimiento WHERE fecha_programada IS NOT NULL
  UNION ALL
  SELECT id_proyecto,id_entidad,ambito,tipo_cop_operativo,tipo_convenio,destino_superficie,clave_hito,indicador,fecha_realizada,0::bigint,1::bigint,superficie_ha,monto FROM vw_hito_seguimiento WHERE fecha_realizada IS NOT NULL)
SELECT id_proyecto,id_entidad,ambito,tipo_cop_operativo,tipo_convenio,destino_superficie,
  extract(year FROM fecha)::integer anio,extract(month FROM fecha)::integer mes,extract(quarter FROM fecha)::integer trimestre,
  indicador,sum(programado)::bigint programado,sum(realizado)::bigint realizado,count(DISTINCT clave_hito)::bigint cantidad,
  sum(superficie_ha)::numeric superficie_ha,sum(monto)::numeric monto
FROM f GROUP BY id_proyecto,id_entidad,ambito,tipo_cop_operativo,tipo_convenio,destino_superficie,
  extract(year FROM fecha),extract(month FROM fecha),extract(quarter FROM fecha),indicador;

COMMENT ON VIEW vw_reporte_avance_periodo IS
  'Reporte de avance periódico temporal por año, mes y trimestre con dimensiones de ámbito, COP, convenio, destino e indicador de hechos.';

CREATE OR REPLACE VIEW vw_dashboard_kpi AS
WITH f AS (
  SELECT id_proyecto,extract(year FROM fecha_programada)::integer anio,indicador,clave_hito,1::bigint programado,0::bigint realizado,NULL::numeric superficie_ha,NULL::numeric monto FROM vw_hito_seguimiento WHERE fecha_programada IS NOT NULL
  UNION ALL
  SELECT id_proyecto,extract(year FROM fecha_realizada)::integer,indicador,clave_hito,0::bigint,1::bigint,superficie_ha,monto FROM vw_hito_seguimiento WHERE fecha_realizada IS NOT NULL)
SELECT id_proyecto,anio,indicador,sum(programado)::bigint programado,sum(realizado)::bigint realizado,
  count(DISTINCT clave_hito)::bigint cantidad,sum(superficie_ha)::numeric superficie_ha,sum(monto)::numeric monto
FROM f GROUP BY id_proyecto,anio,indicador;

COMMENT ON VIEW vw_dashboard_kpi IS
  'Dashboard KPI anual con deduplicación por clave_hito e indicadores canónicos.';

GRANT SELECT ON vw_hito_seguimiento, vw_reporte_avance_periodo, vw_dashboard_kpi TO software_pa_app;
