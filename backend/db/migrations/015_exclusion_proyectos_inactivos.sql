-- Exclusión de proyectos inactivos en read-models de reporting y convenios.
-- Conserva la semántica validada de TUC triestado, Pago e instrumentos colectivos por destino.
SET search_path = public, pg_catalog;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM schema_migrations
    WHERE version = '014'
      AND checksum_sha256 = '0ac8df3e32cc5bb7a103a314160fa4b6b392d9e5e041af3aaa74c0cda9aeceab'
  ) THEN
    RAISE EXCEPTION '015 requiere la migración 014 exacta';
  END IF;
  IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '015') THEN
    RAISE EXCEPTION '015 ya se encuentra registrada';
  END IF;
END $$;

SELECT pg_advisory_xact_lock(hashtextextended('software-pa:015:exclusion-proyectos-inactivos', 0));

CREATE OR REPLACE VIEW vw_reporte_snapshot_actual AS
SELECT pn.id_proyecto,e.id_entidad,'colectivo'::text ambito,'total_nucleos'::text indicador,NULL::text tipo_cop_operativo,NULL::text destino_superficie,count(*)::bigint cantidad,NULL::numeric superficie_ha,NULL::numeric monto FROM proyecto_nucleo pn JOIN proyecto p ON p.id_proyecto=pn.id_proyecto AND p.activo IS TRUE JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE pn.activo GROUP BY pn.id_proyecto,e.id_entidad
UNION ALL SELECT pn.id_proyecto,e.id_entidad,'individual','total_parcelas_afectadas',NULL,NULL,count(DISTINCT ua.id_parcela),NULL,NULL FROM afectacion a JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo JOIN proyecto p ON p.id_proyecto=pn.id_proyecto AND p.activo IS TRUE JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad JOIN afectacion_unidad_agraria au ON au.id_afectacion=a.id_afectacion AND au.activo JOIN unidad_agraria ua ON ua.id_unidad_agraria=au.id_unidad_agraria AND ua.activo WHERE a.activo AND pn.activo AND ua.id_parcela IS NOT NULL GROUP BY pn.id_proyecto,e.id_entidad
UNION ALL SELECT pn.id_proyecto,e.id_entidad,a.tipo_afectacion,'superficie_afectada_administrativa',cop.codigo,NULL,count(*),sum(a.superficie_afectada_ha),NULL FROM afectacion a JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo JOIN proyecto p ON p.id_proyecto=pn.id_proyecto AND p.activo IS TRUE JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad LEFT JOIN catalogo_operativo cop ON cop.id_catalogo_opcion=a.id_tipo_cop_operativo WHERE a.activo AND pn.activo AND a.superficie_afectada_ha IS NOT NULL GROUP BY pn.id_proyecto,e.id_entidad,a.tipo_afectacion,cop.codigo
UNION ALL SELECT pn.id_proyecto,e.id_entidad,a.tipo_afectacion,'superficie_por_destino',cop.codigo,dest.codigo,count(*),sum(au.superficie_afectada_ha),NULL FROM afectacion_unidad_agraria au JOIN afectacion a ON a.id_afectacion=au.id_afectacion AND a.activo JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo AND pn.activo JOIN proyecto p ON p.id_proyecto=pn.id_proyecto AND p.activo IS TRUE JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad JOIN unidad_agraria ua ON ua.id_unidad_agraria=au.id_unidad_agraria AND ua.activo JOIN catalogo_operativo dest ON dest.id_catalogo_opcion=ua.id_destino_superficie LEFT JOIN catalogo_operativo cop ON cop.id_catalogo_opcion=a.id_tipo_cop_operativo WHERE au.activo GROUP BY pn.id_proyecto,e.id_entidad,a.tipo_afectacion,cop.codigo,dest.codigo
UNION ALL SELECT pn.id_proyecto,e.id_entidad,'colectivo'::text,'no_afecta_tuc'::text,NULL::text,NULL::text,count(DISTINCT pn.id_proyecto_nucleo)::bigint,NULL::numeric,NULL::numeric FROM proyecto_nucleo pn JOIN proyecto p ON p.id_proyecto=pn.id_proyecto AND p.activo IS TRUE JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE pn.activo AND pn.afecta_tuc IS FALSE AND pn.tuc_revision_pendiente IS FALSE GROUP BY pn.id_proyecto,e.id_entidad
UNION ALL SELECT pn.id_proyecto,e.id_entidad,'colectivo','comunidad_indigena',NULL,NULL,count(*),NULL,NULL FROM proyecto_nucleo pn JOIN proyecto p ON p.id_proyecto=pn.id_proyecto AND p.activo IS TRUE JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE pn.activo AND n.comunidad_indigena=true GROUP BY pn.id_proyecto,e.id_entidad
UNION ALL SELECT pn.id_proyecto,e.id_entidad,'colectivo','total_cops_planeados',NULL,NULL,sum(coalesce(pn.total_cops_planeados,0))::bigint,NULL,NULL FROM proyecto_nucleo pn JOIN proyecto p ON p.id_proyecto=pn.id_proyecto AND p.activo IS TRUE JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE pn.activo GROUP BY pn.id_proyecto,e.id_entidad;

COMMENT ON VIEW vw_reporte_snapshot_actual IS
  'Snapshot actual de indicadores clave por proyecto activo y entidad; no_afecta_tuc requiere confirmación explícita (afecta_tuc=false y tuc_revision_pendiente=false).';

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
JOIN proyecto proy ON proy.id_proyecto = h.id_proyecto AND proy.activo IS TRUE
WHERE h.indicador <> 'fifonafe'::text OR NOT (EXISTS ( SELECT 1
      FROM tramite_fifonafe t
     WHERE t.version_flujo = 2 AND h.clave_hito = ('fifonafe:'::text || t.id_tramite_fifonafe)))
UNION ALL
SELECT fh.id_proyecto,
       fh.id_entidad,
       fh.id_proyecto_nucleo,
       fh.ambito,
       fh.tipo_cop_operativo,
       fh.tipo_convenio,
       fh.destino_superficie,
       fh.clave_hito,
       fh.indicador,
       fh.fecha_programada,
       fh.fecha_realizada,
       fh.cantidad,
       fh.superficie_ha,
       fh.monto
FROM vw_fifonafe_hito_008 fh
JOIN proyecto proy ON proy.id_proyecto = fh.id_proyecto AND proy.activo IS TRUE
UNION ALL
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
JOIN proyecto proy ON proy.id_proyecto = pn.id_proyecto AND proy.activo IS TRUE
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
LEFT JOIN catalogo_operativo co_cop ON co_cop.id_catalogo_opcion = a.id_tipo_cop_operativo
WHERE p.activo;

COMMENT ON VIEW vw_hito_seguimiento IS
  'Hitos canónicos de seguimiento de proyectos activos: conserva contratos 007 y FIFONAFE v2 008, e incorpora pagos reales de indemnización (indicador pagos).';

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
  'Reporte de avance periódico de proyectos activos por año, mes y trimestre con dimensiones de ámbito, COP, convenio, destino e indicador de hechos.';

CREATE OR REPLACE VIEW vw_dashboard_kpi AS
WITH f AS (
  SELECT id_proyecto,extract(year FROM fecha_programada)::integer anio,indicador,clave_hito,1::bigint programado,0::bigint realizado,NULL::numeric superficie_ha,NULL::numeric monto FROM vw_hito_seguimiento WHERE fecha_programada IS NOT NULL
  UNION ALL
  SELECT id_proyecto,extract(year FROM fecha_realizada)::integer,indicador,clave_hito,0::bigint,1::bigint,superficie_ha,monto FROM vw_hito_seguimiento WHERE fecha_realizada IS NOT NULL)
SELECT id_proyecto,anio,indicador,sum(programado)::bigint programado,sum(realizado)::bigint realizado,
  count(DISTINCT clave_hito)::bigint cantidad,sum(superficie_ha)::numeric superficie_ha,sum(monto)::numeric monto
FROM f GROUP BY id_proyecto,anio,indicador;

COMMENT ON VIEW vw_dashboard_kpi IS
  'Dashboard KPI anual de proyectos activos con deduplicación por clave_hito e indicadores canónicos.';

CREATE OR REPLACE VIEW vw_convenio_colectivo_destino AS
WITH ca_unidades AS (
    SELECT
        c.id_convenio,
        dest.codigo AS destino_superficie,
        au.id_afectacion_unidad,
        au.superficie_afectada_ha
    FROM convenio c
    JOIN convenio_afectacion ca ON ca.id_convenio = c.id_convenio AND ca.activo
    JOIN afectacion a ON a.id_afectacion = ca.id_afectacion AND a.activo
    JOIN afectacion_unidad_agraria au ON au.id_afectacion = a.id_afectacion AND au.activo
    JOIN unidad_agraria ua ON ua.id_unidad_agraria = au.id_unidad_agraria AND ua.activo
    LEFT JOIN catalogo_operativo dest ON dest.id_catalogo_opcion = ua.id_destino_superficie
                                     AND dest.tipo_catalogo = 'destino_superficie'
                                     AND dest.activo
    WHERE c.activo AND c.ambito = 'colectivo'
),
convenio_destinos AS (
    SELECT
        id_convenio,
        destino_superficie,
        sum(superficie_afectada_ha)::numeric AS superficie_ha
    FROM ca_unidades
    GROUP BY id_convenio, destino_superficie
),
convenios_colectivos AS (
    SELECT
        c.id_convenio,
        c.id_proyecto_nucleo,
        c.id_asamblea_autorizacion AS id_asamblea,
        c.ambito,
        c.tipo_convenio,
        c.superficie_ha::numeric AS superficie_declarada_ha,
        c.monto_100::numeric AS monto_declarado,
        c.fecha_firma,
        vco.tipo_cop_operativo_codigo AS tipo_cop_operativo,
        pn.id_proyecto,
        e.id_entidad
    FROM convenio c
    JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = c.id_proyecto_nucleo AND pn.activo
    JOIN proyecto proy ON proy.id_proyecto = pn.id_proyecto AND proy.activo IS TRUE
    JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
    JOIN municipio m ON m.id_municipio = n.id_municipio
    JOIN entidad_federativa e ON e.id_entidad = m.id_entidad
    LEFT JOIN vw_convenio_tipo_cop_operativo vco ON vco.id_convenio = c.id_convenio
    WHERE c.activo AND c.ambito = 'colectivo'
)
SELECT
    cc.id_proyecto,
    cc.id_entidad,
    cc.id_proyecto_nucleo,
    cc.id_convenio,
    cc.id_asamblea,
    cc.ambito,
    cc.tipo_convenio,
    cc.tipo_cop_operativo,
    cd.destino_superficie,
    cd.superficie_ha,
    cc.superficie_declarada_ha,
    cc.monto_declarado,
    cc.fecha_firma,
    extract(year FROM cc.fecha_firma)::integer AS anio,
    extract(month FROM cc.fecha_firma)::integer AS mes,
    extract(quarter FROM cc.fecha_firma)::integer AS trimestre
FROM convenios_colectivos cc
LEFT JOIN convenio_destinos cd ON cd.id_convenio = cc.id_convenio;

COMMENT ON VIEW vw_convenio_colectivo_destino IS
  'Detalle físico por convenio colectivo activo y destino de superficie, limitado a proyectos activos; los montos y superficies declaradas permanecen a nivel de instrumento.';

GRANT SELECT ON vw_reporte_snapshot_actual, vw_hito_seguimiento,
  vw_reporte_avance_periodo, vw_dashboard_kpi,
  vw_convenio_colectivo_destino TO software_pa_app;
