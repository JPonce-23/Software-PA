-- Corrección del snapshot actual (vw_reporte_snapshot_actual):
-- Semántica triestado para TUC y exclusión de revisiones pendientes en 'no_afecta_tuc'.
-- 'no_afecta_tuc' solo contabiliza casos confirmados (afecta_tuc = false y tuc_revision_pendiente = false).
-- afecta_tuc IS NULL representa condición no evaluada y nunca equivale a false ni a cero.
-- Conteo determinista sin duplicados con count(DISTINCT pn.id_proyecto_nucleo)::bigint.
SET search_path = public, pg_catalog;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM schema_migrations
    WHERE version = '011'
      AND checksum_sha256 = 'f28b2705694fb8a011f943a81376c687cba380474aa37cbad31cc524e010df5d'
  ) THEN
    RAISE EXCEPTION '012 requiere la migración 011 exacta';
  END IF;
  IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '012') THEN
    RAISE EXCEPTION '012 ya se encuentra registrada';
  END IF;
END $$;

SELECT pg_advisory_xact_lock(hashtextextended('software-pa:012:snapshot-tuc-triestado', 0));

CREATE OR REPLACE VIEW vw_reporte_snapshot_actual AS
SELECT pn.id_proyecto,e.id_entidad,'colectivo'::text ambito,'total_nucleos'::text indicador,NULL::text tipo_cop_operativo,NULL::text destino_superficie,count(*)::bigint cantidad,NULL::numeric superficie_ha,NULL::numeric monto FROM proyecto_nucleo pn JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE pn.activo GROUP BY pn.id_proyecto,e.id_entidad
UNION ALL SELECT pn.id_proyecto,e.id_entidad,'individual','total_parcelas_afectadas',NULL,NULL,count(DISTINCT ua.id_parcela),NULL,NULL FROM afectacion a JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad JOIN afectacion_unidad_agraria au ON au.id_afectacion=a.id_afectacion AND au.activo JOIN unidad_agraria ua ON ua.id_unidad_agraria=au.id_unidad_agraria AND ua.activo WHERE a.activo AND pn.activo AND ua.id_parcela IS NOT NULL GROUP BY pn.id_proyecto,e.id_entidad
UNION ALL SELECT pn.id_proyecto,e.id_entidad,a.tipo_afectacion,'superficie_afectada_administrativa',cop.codigo,NULL,count(*),sum(a.superficie_afectada_ha),NULL FROM afectacion a JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad LEFT JOIN catalogo_operativo cop ON cop.id_catalogo_opcion=a.id_tipo_cop_operativo WHERE a.activo AND pn.activo AND a.superficie_afectada_ha IS NOT NULL GROUP BY pn.id_proyecto,e.id_entidad,a.tipo_afectacion,cop.codigo
UNION ALL SELECT pn.id_proyecto,e.id_entidad,a.tipo_afectacion,'superficie_por_destino',cop.codigo,dest.codigo,count(*),sum(au.superficie_afectada_ha),NULL FROM afectacion_unidad_agraria au JOIN afectacion a ON a.id_afectacion=au.id_afectacion AND a.activo JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo AND pn.activo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad JOIN unidad_agraria ua ON ua.id_unidad_agraria=au.id_unidad_agraria AND ua.activo JOIN catalogo_operativo dest ON dest.id_catalogo_opcion=ua.id_destino_superficie LEFT JOIN catalogo_operativo cop ON cop.id_catalogo_opcion=a.id_tipo_cop_operativo WHERE au.activo GROUP BY pn.id_proyecto,e.id_entidad,a.tipo_afectacion,cop.codigo,dest.codigo
UNION ALL SELECT pn.id_proyecto,e.id_entidad,'colectivo'::text,'no_afecta_tuc'::text,NULL::text,NULL::text,count(DISTINCT pn.id_proyecto_nucleo)::bigint,NULL::numeric,NULL::numeric FROM proyecto_nucleo pn JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE pn.activo AND pn.afecta_tuc IS FALSE AND pn.tuc_revision_pendiente IS FALSE GROUP BY pn.id_proyecto,e.id_entidad
UNION ALL SELECT pn.id_proyecto,e.id_entidad,'colectivo','comunidad_indigena',NULL,NULL,count(*),NULL,NULL FROM proyecto_nucleo pn JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE pn.activo AND n.comunidad_indigena=true GROUP BY pn.id_proyecto,e.id_entidad
UNION ALL SELECT pn.id_proyecto,e.id_entidad,'colectivo','total_cops_planeados',NULL,NULL,sum(coalesce(pn.total_cops_planeados,0))::bigint,NULL,NULL FROM proyecto_nucleo pn JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE pn.activo GROUP BY pn.id_proyecto,e.id_entidad;

COMMENT ON VIEW vw_reporte_snapshot_actual IS
  'Snapshot actual de indicadores clave por proyecto y entidad; no_afecta_tuc requiere confirmación explícita (afecta_tuc=false y tuc_revision_pendiente=false).';

GRANT SELECT ON vw_reporte_snapshot_actual TO software_pa_app;
