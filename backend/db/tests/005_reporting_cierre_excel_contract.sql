-- Structural and functional contract for migration 005 (reporting cierre excel).
\set ON_ERROR_STOP on

DO $$
DECLARE
    v_def text;
    v_cols text[];
    v_col text;
BEGIN
    -- 1. Schema migrations must contain 001 through 005 with valid SHA-256
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='001' AND checksum_sha256 ~ '^[0-9a-f]{64}$') OR
       NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='002' AND checksum_sha256 ~ '^[0-9a-f]{64}$') OR
       NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='003' AND checksum_sha256 ~ '^[0-9a-f]{64}$') OR
       NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='004' AND checksum_sha256 ~ '^[0-9a-f]{64}$') OR
       NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='005' AND checksum_sha256 ~ '^[0-9a-f]{64}$') THEN
        RAISE EXCEPTION 'schema_migrations debe contener 001, 002, 003, 004 y 005 con SHA-256';
    END IF;

    -- 2. Required views exist
    IF to_regclass('public.vw_hito_seguimiento') IS NULL THEN
        RAISE EXCEPTION 'Vista vw_hito_seguimiento no existe';
    END IF;
    IF to_regclass('public.vw_reporte_avance_periodo') IS NULL THEN
        RAISE EXCEPTION 'Vista vw_reporte_avance_periodo no existe';
    END IF;
    IF to_regclass('public.vw_dashboard_kpi') IS NULL THEN
        RAISE EXCEPTION 'Vista vw_dashboard_kpi no existe';
    END IF;

    -- 3. Columns of vw_reporte_avance_periodo
    v_cols := ARRAY[
        'id_proyecto', 'id_entidad', 'ambito', 'tipo_cop_operativo',
        'tipo_convenio', 'destino_superficie', 'anio', 'mes',
        'trimestre', 'indicador', 'programado', 'realizado',
        'cantidad', 'superficie_ha', 'monto'
    ];
    FOREACH v_col IN ARRAY v_cols LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name='vw_reporte_avance_periodo' AND column_name=v_col
        ) THEN
            RAISE EXCEPTION 'Columna requerida % ausente en vw_reporte_avance_periodo', v_col;
        END IF;
    END LOOP;

    -- 4. Columns of vw_dashboard_kpi
    v_cols := ARRAY[
        'id_proyecto', 'anio', 'indicador', 'programado', 'realizado',
        'cantidad', 'superficie_ha', 'monto'
    ];
    FOREACH v_col IN ARRAY v_cols LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name='vw_dashboard_kpi' AND column_name=v_col
        ) THEN
            RAISE EXCEPTION 'Columna requerida % ausente en vw_dashboard_kpi', v_col;
        END IF;
    END LOOP;

    -- 5. Canonical sources presence in view definitions
    v_def := pg_get_viewdef('vw_hito_seguimiento'::regclass, true);
    IF position('tramite_ran_evento' in v_def) = 0 THEN
        RAISE EXCEPTION 'tramite_ran_evento no referenciado en vw_hito_seguimiento';
    END IF;
    IF position('asamblea_convocatoria' in v_def) = 0 THEN
        RAISE EXCEPTION 'asamblea_convocatoria no referenciado en vw_hito_seguimiento';
    END IF;
    IF position('actividad_campo' in v_def) = 0 THEN
        RAISE EXCEPTION 'actividad_campo no referenciado en vw_hito_seguimiento';
    END IF;
    IF position('convenio' in v_def) = 0 THEN
        RAISE EXCEPTION 'convenio no referenciado en vw_hito_seguimiento';
    END IF;
    IF position('afectacion_unidad_agraria' in v_def) = 0 THEN
        RAISE EXCEPTION 'afectacion_unidad_agraria no referenciado en vw_hito_seguimiento';
    END IF;
    IF position('seguimiento_evento' in v_def) = 0 THEN
        RAISE EXCEPTION 'seguimiento_evento no referenciado en vw_hito_seguimiento';
    END IF;

    -- 6. Prohibited columns
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public'
          AND lower(column_name) IN (
            'x', 'trimestre1', 'trimestre2', 'trimestre3', 'trimestre4',
            'no_parcela_ppt', 'numero_parcela_ppt', 'ingreso_por_na',
            'inscrito_por_na', 'programada_por_nucleo', 'realizada_por_nucleo'
          )
    ) THEN
        RAISE EXCEPTION 'Columna auxiliar o prohibida detectada en schema public';
    END IF;

    -- 7. No extraneous FIFONAFE columns added to base tables
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='tramite_fifonafe'
          AND column_name NOT IN (
            'id_tramite_fifonafe','id_proyecto_nucleo','ambito','estatus',
            'hay_conflictos','resultado_no_conflictos','activo','creado_en',
            'creado_por','actualizado_en','actualizado_por','fecha_baja',
            'id_usuario_baja','motivo_baja','observaciones','acuse_fifonafe_fecha'
          )
    ) THEN
        RAISE EXCEPTION 'Columnas extrañas no autorizadas en tramite_fifonafe';
    END IF;
END $$;

SELECT * FROM vw_hito_seguimiento LIMIT 0;
SELECT * FROM vw_reporte_avance_periodo LIMIT 0;
SELECT * FROM vw_dashboard_kpi LIMIT 0;

SELECT 'CONTRATO SQL 005 REPORTING CIERRE EXCEL APROBADO' AS resultado;
