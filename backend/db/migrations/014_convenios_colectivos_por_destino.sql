-- Desglose por destino de superficie para convenios colectivos (vw_convenio_colectivo_destino).
-- Cadena canónica: Convenio -> ConvenioAfectacion -> Afectacion -> AfectacionUnidadAgraria -> UnidadAgraria -> CatalogoOperativo(destino_superficie).
-- Reglas de negocio:
-- 1. Ámbito estrictamente colectivo (ambito = 'colectivo').
-- 2. La superficie física por destino proviene de AfectacionUnidadAgraria.superficie_afectada_ha.
-- 3. Los montos (monto_100) y superficies declaradas (superficie_ha) pertenecen al instrumento y no se prorratean ni multiplican por N:M.
-- 4. Si no hay unidades o destino, destino_superficie = NULL y superficie_ha = NULL (NULL no es cero).
-- 5. Se deduplican destinos compartidos dentro del mismo convenio sumando sus superficies.
-- 6. Todas las entidades deben respetar su baja lógica (activo = true).
-- 7. Conserva id_asamblea para conteo deduplicado de asambleas.
SET search_path = public, pg_catalog;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM schema_migrations
    WHERE version = '013'
      AND checksum_sha256 = '315194e6daa7b8bffd27c8d678b6e86c0486eaf851f58aba3722e90e19a37eef'
  ) THEN
    RAISE EXCEPTION '014 requiere la migración 013 exacta';
  END IF;
  IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '014') THEN
    RAISE EXCEPTION '014 ya se encuentra registrada';
  END IF;
END $$;

SELECT pg_advisory_xact_lock(hashtextextended('software-pa:014:convenios-colectivos-por-destino', 0));

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
  'Desglose físico por destino de superficie de convenios colectivos derivado de AfectacionUnidadAgraria, conservando montos y superficies declaradas a nivel de instrumento.';

GRANT SELECT ON vw_convenio_colectivo_destino TO software_pa_app;
