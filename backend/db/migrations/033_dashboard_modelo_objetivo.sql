-- Vistas de lectura del modelo objetivo. Ningún KPI usa geometría.
BEGIN;

SELECT pg_advisory_xact_lock(20260825, 33);

DO $preflight$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '032') THEN
        RAISE EXCEPTION '033 requiere la migración 032';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '033') THEN
        RAISE EXCEPTION 'La migración 033 ya fue aplicada';
    END IF;
END;
$preflight$;

CREATE OR REPLACE VIEW vw_orv_estado AS
SELECT
    o.id_orv,
    o.id_nucleo,
    o.numero_orv,
    o.inicio_vigencia,
    o.fin_vigencia,
    o.estatus_fuente,
    o.acta_eleccion_inscrita_ran,
    o.fecha_inscripcion_acta_ran,
    CASE
        WHEN NOT o.activo THEN 'inactivo'
        WHEN o.inicio_vigencia IS NOT NULL AND o.inicio_vigencia > CURRENT_DATE THEN 'programado'
        WHEN o.fin_vigencia IS NOT NULL AND o.fin_vigencia < CURRENT_DATE THEN 'vencido'
        ELSE 'vigente'
    END AS estado_derivado
FROM orv o;

CREATE OR REPLACE VIEW vw_proyecto_nucleo_resumen AS
SELECT
    pn.id_proyecto_nucleo,
    pn.id_proyecto,
    p.clave_proyecto,
    p.nombre_proyecto,
    pn.id_nucleo,
    n.nombre_nucleo,
    n.tipo_nucleo,
    n.comunidad_indigena,
    e.id_entidad,
    e.clave_inegi AS clave_entidad,
    e.nombre AS entidad,
    m.id_municipio,
    m.clave_inegi AS clave_municipio,
    m.nombre AS municipio,
    pn.residencia,
    pn.responsable_nombre,
    pn.contacto,
    (
        SELECT r.valor FROM proyecto_nucleo_referencia r
        WHERE r.id_proyecto_nucleo = pn.id_proyecto_nucleo
          AND r.tipo_referencia = 'consecutivo' AND r.activo
        ORDER BY r.es_principal DESC, r.id_referencia
        LIMIT 1
    ) AS consecutivo_principal,
    (SELECT COUNT(*) FROM actividad_campo a WHERE a.id_proyecto_nucleo = pn.id_proyecto_nucleo AND a.activo) AS actividades,
    (SELECT COUNT(*) FROM asamblea a WHERE a.id_proyecto_nucleo = pn.id_proyecto_nucleo AND a.activo) AS asambleas,
    (SELECT COUNT(*) FROM afectacion a WHERE a.id_proyecto_nucleo = pn.id_proyecto_nucleo AND a.activo AND a.tipo_afectacion = 'colectivo') AS afectaciones_colectivas,
    (SELECT COUNT(*) FROM afectacion a WHERE a.id_proyecto_nucleo = pn.id_proyecto_nucleo AND a.activo AND a.tipo_afectacion = 'individual') AS afectaciones_individuales,
    (SELECT COUNT(*) FROM parcela pa WHERE pa.id_nucleo = pn.id_nucleo AND pa.activo) AS parcelas,
    (SELECT COUNT(*) FROM convenio c WHERE c.id_proyecto_nucleo = pn.id_proyecto_nucleo AND c.activo) AS convenios,
    (SELECT COUNT(*) FROM tramite_fifonafe tf WHERE tf.id_proyecto_nucleo = pn.id_proyecto_nucleo AND tf.activo) AS tramites_fifonafe,
    pn.activo,
    pn.creado_en,
    pn.actualizado_en
FROM proyecto_nucleo pn
JOIN proyecto p ON p.id_proyecto = pn.id_proyecto
JOIN nucleo_agrario n ON n.id_nucleo = pn.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa e ON e.id_entidad = m.id_entidad;

CREATE OR REPLACE VIEW vw_dashboard_kpi AS
WITH
nucleos AS (
    SELECT pn.id_proyecto,
           EXTRACT(YEAR FROM pn.creado_en)::INTEGER AS anio,
           'nucleos'::TEXT AS indicador,
           0::BIGINT AS programado,
           COUNT(*)::BIGINT AS realizado,
           COUNT(*)::BIGINT AS cantidad,
           NULL::NUMERIC AS superficie_ha,
           NULL::NUMERIC AS monto
    FROM proyecto_nucleo pn
    WHERE pn.activo
    GROUP BY pn.id_proyecto, EXTRACT(YEAR FROM pn.creado_en)::INTEGER
),
actividades AS (
    SELECT pn.id_proyecto,
           EXTRACT(YEAR FROM COALESCE(a.fecha_realizada, a.fecha_programada, a.creado_en::DATE))::INTEGER AS anio,
           a.tipo_actividad::TEXT AS indicador,
           COUNT(*) FILTER (WHERE a.fecha_programada IS NOT NULL)::BIGINT AS programado,
           COUNT(*) FILTER (WHERE a.fecha_realizada IS NOT NULL)::BIGINT AS realizado,
           COUNT(*)::BIGINT AS cantidad,
           NULL::NUMERIC AS superficie_ha,
           NULL::NUMERIC AS monto
    FROM actividad_campo a
    JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo
    WHERE a.activo AND pn.activo
    GROUP BY pn.id_proyecto,
             EXTRACT(YEAR FROM COALESCE(a.fecha_realizada, a.fecha_programada, a.creado_en::DATE))::INTEGER,
             a.tipo_actividad
),
asambleas_total AS (
    SELECT pn.id_proyecto,
           EXTRACT(YEAR FROM COALESCE(a.fecha_realizada, a.fecha_programada_primera, a.creado_en::DATE))::INTEGER AS anio,
           'asambleas'::TEXT AS indicador,
           COUNT(*) FILTER (WHERE a.fecha_programada_primera IS NOT NULL OR a.fecha_programada_segunda IS NOT NULL)::BIGINT AS programado,
           COUNT(*) FILTER (WHERE a.fecha_realizada IS NOT NULL)::BIGINT AS realizado,
           COUNT(*)::BIGINT AS cantidad,
           NULL::NUMERIC AS superficie_ha,
           NULL::NUMERIC AS monto
    FROM asamblea a
    JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo
    WHERE a.activo AND pn.activo
    GROUP BY pn.id_proyecto,
             EXTRACT(YEAR FROM COALESCE(a.fecha_realizada, a.fecha_programada_primera, a.creado_en::DATE))::INTEGER
),
asambleas_ran AS (
    SELECT pn.id_proyecto,
           EXTRACT(YEAR FROM COALESCE(a.fecha_inscripcion_ran, a.fecha_ingreso_ran, a.fecha_programada_ingreso_ran, a.creado_en::DATE))::INTEGER AS anio,
           v.indicador,
           CASE WHEN v.indicador = 'ingreso_ran_acta'
                THEN COUNT(*) FILTER (WHERE a.fecha_programada_ingreso_ran IS NOT NULL)
                ELSE 0 END::BIGINT AS programado,
           CASE WHEN v.indicador = 'ingreso_ran_acta'
                THEN COUNT(*) FILTER (WHERE a.fecha_ingreso_ran IS NOT NULL)
                ELSE COUNT(*) FILTER (WHERE a.fecha_inscripcion_ran IS NOT NULL) END::BIGINT AS realizado,
           COUNT(*) FILTER (WHERE
                (v.indicador = 'ingreso_ran_acta' AND a.fecha_ingreso_ran IS NOT NULL)
                OR (v.indicador = 'inscripcion_ran_acta' AND a.fecha_inscripcion_ran IS NOT NULL)
           )::BIGINT AS cantidad,
           NULL::NUMERIC AS superficie_ha,
           NULL::NUMERIC AS monto
    FROM asamblea a
    JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo
    CROSS JOIN (VALUES ('ingreso_ran_acta'::TEXT), ('inscripcion_ran_acta'::TEXT)) v(indicador)
    WHERE a.activo AND pn.activo
    GROUP BY pn.id_proyecto,
             EXTRACT(YEAR FROM COALESCE(a.fecha_inscripcion_ran, a.fecha_ingreso_ran, a.fecha_programada_ingreso_ran, a.creado_en::DATE))::INTEGER,
             v.indicador
),
retiro_fondos AS (
    SELECT pn.id_proyecto,
           EXTRACT(YEAR FROM COALESCE(a.fecha_realizada, a.fecha_programada_primera, a.creado_en::DATE))::INTEGER AS anio,
           'retiro_fondos'::TEXT AS indicador,
           COUNT(*) FILTER (WHERE a.fecha_programada_primera IS NOT NULL OR a.fecha_programada_segunda IS NOT NULL)::BIGINT AS programado,
           COUNT(*) FILTER (WHERE a.fecha_realizada IS NOT NULL)::BIGINT AS realizado,
           COUNT(*)::BIGINT AS cantidad,
           NULL::NUMERIC AS superficie_ha,
           NULL::NUMERIC AS monto
    FROM asamblea a
    JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo
    WHERE a.activo AND pn.activo AND a.tipo_asamblea = 'retiro_fondos'
    GROUP BY pn.id_proyecto,
             EXTRACT(YEAR FROM COALESCE(a.fecha_realizada, a.fecha_programada_primera, a.creado_en::DATE))::INTEGER
),
convenios AS (
    SELECT c.id_proyecto_nucleo,
           pn.id_proyecto,
           EXTRACT(YEAR FROM COALESCE(c.fecha_firma, c.fecha_programada_firma, c.creado_en::DATE))::INTEGER AS anio,
           CASE
               WHEN c.tipo_convenio = 'cop_original' AND c.ambito = 'colectivo' THEN 'cop_colectivos'
               WHEN c.tipo_convenio = 'cop_original' AND c.ambito = 'individual' THEN 'cop_individuales'
               WHEN c.tipo_convenio = 'modificatorio' THEN 'modificatorios'
               WHEN c.tipo_convenio = 'superficie_adicional' THEN 'superficies_adicionales'
               WHEN c.tipo_convenio = 'obras_complementarias' THEN 'obras_complementarias'
               WHEN c.tipo_convenio = 'ampliacion' THEN 'ampliaciones'
               WHEN c.tipo_convenio = 'ampliacion_remanente' THEN 'ampliaciones_remanentes'
               ELSE 'otros_instrumentos'
           END::TEXT AS indicador,
           COUNT(*) FILTER (WHERE c.fecha_programada_firma IS NOT NULL)::BIGINT AS programado,
           COUNT(*) FILTER (WHERE c.fecha_firma IS NOT NULL)::BIGINT AS realizado,
           COUNT(*)::BIGINT AS cantidad,
           SUM(c.superficie_ha)::NUMERIC AS superficie_ha,
           SUM(c.monto_100)::NUMERIC AS monto
    FROM convenio c
    JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = c.id_proyecto_nucleo
    WHERE c.activo AND pn.activo
    GROUP BY c.id_proyecto_nucleo, pn.id_proyecto,
             EXTRACT(YEAR FROM COALESCE(c.fecha_firma, c.fecha_programada_firma, c.creado_en::DATE))::INTEGER,
             CASE
               WHEN c.tipo_convenio = 'cop_original' AND c.ambito = 'colectivo' THEN 'cop_colectivos'
               WHEN c.tipo_convenio = 'cop_original' AND c.ambito = 'individual' THEN 'cop_individuales'
               WHEN c.tipo_convenio = 'modificatorio' THEN 'modificatorios'
               WHEN c.tipo_convenio = 'superficie_adicional' THEN 'superficies_adicionales'
               WHEN c.tipo_convenio = 'obras_complementarias' THEN 'obras_complementarias'
               WHEN c.tipo_convenio = 'ampliacion' THEN 'ampliaciones'
               WHEN c.tipo_convenio = 'ampliacion_remanente' THEN 'ampliaciones_remanentes'
               ELSE 'otros_instrumentos'
             END
),
convenios_por_proyecto AS (
    SELECT id_proyecto, anio, indicador,
           SUM(programado)::BIGINT AS programado,
           SUM(realizado)::BIGINT AS realizado,
           SUM(cantidad)::BIGINT AS cantidad,
           SUM(superficie_ha)::NUMERIC AS superficie_ha,
           SUM(monto)::NUMERIC AS monto
    FROM convenios
    GROUP BY id_proyecto, anio, indicador
),
convenios_ran AS (
    SELECT pn.id_proyecto,
           EXTRACT(YEAR FROM COALESCE(c.fecha_inscripcion_ran, c.ingreso_ran_fecha, c.fecha_programada_ingreso_ran, c.creado_en::DATE))::INTEGER AS anio,
           v.indicador,
           CASE WHEN v.indicador = 'ingreso_ran_convenio'
                THEN COUNT(*) FILTER (WHERE c.fecha_programada_ingreso_ran IS NOT NULL)
                ELSE 0 END::BIGINT AS programado,
           CASE WHEN v.indicador = 'ingreso_ran_convenio'
                THEN COUNT(*) FILTER (WHERE c.ingreso_ran_fecha IS NOT NULL)
                ELSE COUNT(*) FILTER (WHERE c.fecha_inscripcion_ran IS NOT NULL) END::BIGINT AS realizado,
           COUNT(*) FILTER (WHERE
                (v.indicador = 'ingreso_ran_convenio' AND c.ingreso_ran_fecha IS NOT NULL)
                OR (v.indicador = 'inscripcion_ran_convenio' AND c.fecha_inscripcion_ran IS NOT NULL)
           )::BIGINT AS cantidad,
           NULL::NUMERIC AS superficie_ha,
           NULL::NUMERIC AS monto
    FROM convenio c
    JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = c.id_proyecto_nucleo
    CROSS JOIN (VALUES ('ingreso_ran_convenio'::TEXT), ('inscripcion_ran_convenio'::TEXT)) v(indicador)
    WHERE c.activo AND pn.activo
    GROUP BY pn.id_proyecto,
             EXTRACT(YEAR FROM COALESCE(c.fecha_inscripcion_ran, c.ingreso_ran_fecha, c.fecha_programada_ingreso_ran, c.creado_en::DATE))::INTEGER,
             v.indicador
),
afectaciones AS (
    SELECT pn.id_proyecto,
           EXTRACT(YEAR FROM a.creado_en)::INTEGER AS anio,
           v.indicador,
           0::BIGINT AS programado,
           COUNT(*)::BIGINT AS realizado,
           CASE
             WHEN v.indicador = 'parcelas_afectadas' THEN COUNT(DISTINCT a.id_parcela)
             WHEN v.indicador = 'expropiacion_directa' THEN COUNT(*) FILTER (WHERE a.condicion_especial = 'expropiacion_directa')
             ELSE COUNT(*)
           END::BIGINT AS cantidad,
           CASE v.indicador
             WHEN 'superficie_preliminar_administrativa' THEN SUM(a.superficie_preliminar_ha)
             WHEN 'superficie_afectada_administrativa' THEN SUM(a.superficie_afectada_ha)
             ELSE NULL
           END::NUMERIC AS superficie_ha,
           NULL::NUMERIC AS monto
    FROM afectacion a
    JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo
    CROSS JOIN (VALUES
        ('parcelas_afectadas'::TEXT), ('expropiacion_directa'::TEXT),
        ('superficie_preliminar_administrativa'::TEXT), ('superficie_afectada_administrativa'::TEXT)
    ) v(indicador)
    WHERE a.activo AND pn.activo
      AND (v.indicador <> 'parcelas_afectadas' OR a.tipo_afectacion = 'individual')
      AND (v.indicador <> 'expropiacion_directa' OR a.condicion_especial = 'expropiacion_directa')
    GROUP BY pn.id_proyecto, EXTRACT(YEAR FROM a.creado_en)::INTEGER, v.indicador
),
fifonafe AS (
    SELECT pn.id_proyecto,
           EXTRACT(YEAR FROM COALESCE(tf.fecha_oficio_respuesta_dgaopr_a_fifonafe, tf.fecha_oficio_fifonafe_a_dgaopr, tf.creado_en::DATE))::INTEGER AS anio,
           v.indicador,
           COUNT(*) FILTER (WHERE tf.estatus IN ('programado', 'pendiente'))::BIGINT AS programado,
           COUNT(*) FILTER (WHERE tf.estatus = 'completo')::BIGINT AS realizado,
           CASE WHEN v.indicador = 'no_conflictos'
                THEN COUNT(*) FILTER (WHERE tf.hay_conflictos IS FALSE)
                ELSE COUNT(*) END::BIGINT AS cantidad,
           NULL::NUMERIC AS superficie_ha,
           NULL::NUMERIC AS monto
    FROM tramite_fifonafe tf
    JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = tf.id_proyecto_nucleo
    CROSS JOIN (VALUES ('fifonafe'::TEXT), ('no_conflictos'::TEXT)) v(indicador)
    WHERE tf.activo AND pn.activo
      AND (v.indicador <> 'no_conflictos' OR tf.hay_conflictos IS FALSE)
    GROUP BY pn.id_proyecto,
             EXTRACT(YEAR FROM COALESCE(tf.fecha_oficio_respuesta_dgaopr_a_fifonafe, tf.fecha_oficio_fifonafe_a_dgaopr, tf.creado_en::DATE))::INTEGER,
             v.indicador
),
indemnizaciones AS (
    SELECT pn.id_proyecto,
           EXTRACT(YEAR FROM COALESCE(i.fecha_resolucion, i.fecha_programada, i.creado_en::DATE))::INTEGER AS anio,
           'indemnizaciones'::TEXT AS indicador,
           COUNT(*) FILTER (WHERE i.fecha_programada IS NOT NULL)::BIGINT AS programado,
           COUNT(*) FILTER (WHERE i.fecha_resolucion IS NOT NULL OR i.estatus = 'completo')::BIGINT AS realizado,
           COUNT(*)::BIGINT AS cantidad,
           NULL::NUMERIC AS superficie_ha,
           NULL::NUMERIC AS monto
    FROM indemnizacion i
    JOIN afectacion a ON a.id_afectacion = i.id_afectacion
    JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo
    WHERE i.activo AND a.activo AND pn.activo
    GROUP BY pn.id_proyecto,
             EXTRACT(YEAR FROM COALESCE(i.fecha_resolucion, i.fecha_programada, i.creado_en::DATE))::INTEGER
),
pagos AS (
    SELECT pn.id_proyecto,
           EXTRACT(YEAR FROM p.fecha_pago)::INTEGER AS anio,
           'pagos'::TEXT AS indicador,
           0::BIGINT AS programado,
           COUNT(*)::BIGINT AS realizado,
           COUNT(*)::BIGINT AS cantidad,
           NULL::NUMERIC AS superficie_ha,
           SUM(p.monto)::NUMERIC AS monto
    FROM pago p
    JOIN indemnizacion i ON i.id_indemnizacion = p.id_indemnizacion
    JOIN afectacion a ON a.id_afectacion = i.id_afectacion
    JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = a.id_proyecto_nucleo
    WHERE p.activo AND i.activo AND a.activo AND pn.activo
    GROUP BY pn.id_proyecto, EXTRACT(YEAR FROM p.fecha_pago)::INTEGER
)
SELECT * FROM nucleos
UNION ALL SELECT * FROM actividades
UNION ALL SELECT * FROM asambleas_total
UNION ALL SELECT * FROM asambleas_ran
UNION ALL SELECT * FROM retiro_fondos
UNION ALL SELECT * FROM convenios_por_proyecto
UNION ALL SELECT * FROM convenios_ran
UNION ALL SELECT * FROM afectaciones
UNION ALL SELECT * FROM fifonafe
UNION ALL SELECT * FROM indemnizaciones
UNION ALL SELECT * FROM pagos;

GRANT SELECT ON vw_orv_estado, vw_proyecto_nucleo_resumen, vw_dashboard_kpi TO software_pa_app;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('033', 'Vistas objetivo de ORV, resumen ProyectoNucleo y dashboard KPI');

COMMIT;
