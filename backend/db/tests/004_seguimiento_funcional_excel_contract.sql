-- Structural and functional contract for migration 004 (seguimiento funcional excel).
\set ON_ERROR_STOP on

DO $$
DECLARE
    v_count integer;
    v_def text;
BEGIN
    -- 1. Schema migrations must contain 001, 002, 003, 004 with valid SHA-256
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='001' AND checksum_sha256 ~ '^[0-9a-f]{64}$') OR
       NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='002' AND checksum_sha256 ~ '^[0-9a-f]{64}$') OR
       NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='003' AND checksum_sha256 ~ '^[0-9a-f]{64}$') OR
       NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='004' AND checksum_sha256 ~ '^[0-9a-f]{64}$') THEN
        RAISE EXCEPTION 'schema_migrations debe contener 001, 002, 003 y 004 con SHA-256';
    END IF;

    -- 2. seguimiento_evento table exists and has proper PK / FK / checks
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema='public' AND table_name='seguimiento_evento' AND table_type='BASE TABLE'
    ) THEN
        RAISE EXCEPTION 'Tabla seguimiento_evento no existe';
    END IF;

    -- Columns check
    IF (
        SELECT count(*) FROM information_schema.columns
        WHERE table_schema='public' AND table_name='seguimiento_evento'
          AND column_name IN (
            'id_seguimiento_evento','id_proyecto_nucleo','entidad_tipo','entidad_id',
            'ambito','id_tipo_evento','id_motivo','fecha_evento','detalle',
            'id_documento','fuente','activo','creado_en','creado_por',
            'actualizado_en','actualizado_por','fecha_baja','id_usuario_baja','motivo_baja'
          )
    ) < 19 THEN
        RAISE EXCEPTION 'Columnas requeridas de seguimiento_evento incompletas';
    END IF;

    -- Checks check
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='seguimiento_evento'::regclass AND conname='chk_seguimiento_evento_ambito') OR
       NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='seguimiento_evento'::regclass AND conname='chk_seguimiento_evento_objetivo') OR
       NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='seguimiento_evento'::regclass AND conname='chk_seguimiento_evento_baja') THEN
        RAISE EXCEPTION 'Constraints chk de seguimiento_evento incompletas';
    END IF;

    -- Triggers check
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid='seguimiento_evento'::regclass AND tgname='trg_prevent_delete_seguimiento_evento') OR
       NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid='seguimiento_evento'::regclass AND tgname='trg_audit_seguimiento_evento') OR
       NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid='seguimiento_evento'::regclass AND tgname='trg_validar_seguimiento_evento') THEN
        RAISE EXCEPTION 'Triggers requeridos de seguimiento_evento ausentes';
    END IF;

    -- 3. Catalogs check: tipo_evento_seguimiento
    SELECT count(*) INTO v_count
    FROM catalogo_operativo
    WHERE tipo_catalogo='tipo_evento_seguimiento' AND activo
      AND codigo IN (
        'inicio','suspension','reapertura','cierre','cambio_alcance',
        'reunion','negociacion','consulta_indigena','continuacion_asamblea',
        'medicion_bdt','otro'
      );
    IF v_count <> 11 THEN
        RAISE EXCEPTION 'Opciones de tipo_evento_seguimiento incompletas: esperadas 11, encontradas %', v_count;
    END IF;

    -- 4. Catalogs check: motivo_seguimiento
    SELECT count(*) INTO v_count
    FROM catalogo_operativo
    WHERE tipo_catalogo='motivo_seguimiento' AND activo
      AND codigo IN (
        'expropiacion_directa','no_afectacion','comunidad_indigena','dominio_pleno',
        'juicio_agrario','conflicto_titularidad','rechazo','cambio_trazo',
        'nueva_informacion','calificacion_negativa','falta_pago','otro'
      );
    IF v_count <> 12 THEN
        RAISE EXCEPTION 'Opciones de motivo_seguimiento incompletas: esperadas 12, encontradas %', v_count;
    END IF;

    -- 5. estado_requisito_documental check
    IF NOT EXISTS (SELECT 1 FROM catalogo_operativo WHERE tipo_catalogo='estado_requisito_documental' AND codigo='parcial' AND activo) OR
       NOT EXISTS (SELECT 1 FROM catalogo_operativo WHERE tipo_catalogo='estado_requisito_documental' AND codigo='pendiente_validacion' AND activo) THEN
        RAISE EXCEPTION 'Estados documentales parcial o pendiente_validacion faltantes';
    END IF;

    -- 6. requisito_documental check
    SELECT count(*) INTO v_count
    FROM requisito_documental
    WHERE codigo IN ('validacion_pa_sict','oficio_ran_parcelas_afectacion','acta_complementaria') AND activo;
    IF v_count <> 3 THEN
        RAISE EXCEPTION 'Nuevos requisitos documentales no registrados: esperados 3, encontrados %', v_count;
    END IF;

    -- 7. View check: vw_seguimiento_estado_actual
    IF to_regclass('public.vw_seguimiento_estado_actual') IS NULL THEN
        RAISE EXCEPTION 'Vista vw_seguimiento_estado_actual no existe';
    END IF;

    SELECT count(*) INTO v_count
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name='vw_seguimiento_estado_actual'
      AND column_name IN (
        'id_proyecto_nucleo','entidad_tipo','entidad_id','estado_actual',
        'tipo_ultimo_evento','motivo_actual','fecha_ultimo_evento','detalle','ambito'
      );
    IF v_count <> 9 THEN
        RAISE EXCEPTION 'Columnas de vw_seguimiento_estado_actual incompletas: esperadas 9, encontradas %', v_count;
    END IF;

    -- 8. Prohibiciones estrictas:
    -- NO nuevas columnas FIFONAFE
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='tramite_fifonafe'
          AND column_name IN ('origen_recursos','monto_solicitado','destino_recursos','forma_entrega')
    ) THEN
        RAISE EXCEPTION 'tramite_fifonafe no debe tener columnas adicionales';
    END IF;

    -- NO no_parcela_ppt ni numero_parcela_ppt
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND column_name IN ('no_parcela_ppt','numero_parcela_ppt')
    ) THEN
        RAISE EXCEPTION 'Prohibido no_parcela_ppt';
    END IF;

    -- NO columnas X
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND lower(column_name) IN ('x','columna_x','aux_x')
    ) THEN
        RAISE EXCEPTION 'Prohibida columna X';
    END IF;

    -- NO trimestre persistido
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND column_name IN ('trimestre1','trimestre2','trimestre3','trimestre4')
    ) THEN
        RAISE EXCEPTION 'Prohibido trimestre persistido';
    END IF;

    -- NO bien_afectado
    IF to_regclass('public.bien_afectado') IS NOT NULL THEN
        RAISE EXCEPTION 'bien_afectado no debe existir';
    END IF;

END $$;

SELECT * FROM vw_seguimiento_estado_actual LIMIT 0;
SELECT 'CONTRATO 004 SEGUIMIENTO FUNCIONAL APROBADO' AS resultado;
