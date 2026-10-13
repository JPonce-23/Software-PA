\set ON_ERROR_STOP on
BEGIN;
SELECT current_database();
DO $$
BEGIN
    IF current_database() <> 'software_pa_test' THEN
        RAISE EXCEPTION 'Contrato 029 sólo permite software_pa_test';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '029'
        AND nombre = 'diagnosticos_conciliacion_gis'
        AND checksum_sha256 = '284f8a26fc5d1215f21055657a5171431d1df4ee8d0151dc58071e38731e9716') THEN
        RAISE EXCEPTION '029 no aplicada o checksum incompatible';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
        AND table_name = 'importacion_conciliacion_resultado' AND column_name = 'diagnostico'
        AND data_type = 'jsonb' AND is_nullable = 'YES' AND column_default IS NULL) THEN
        RAISE EXCEPTION 'Diagnóstico debe ser JSONB nullable sin default/backfill';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_resultado_gis_diagnostico'
        AND conrelid = 'importacion_conciliacion_resultado'::regclass AND convalidated) THEN
        RAISE EXCEPTION 'Diagnóstico sin check validado';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_resultado_gis_feature_ciclo'
        AND indexdef LIKE '%(id_importacion_feature, id_ciclo)%') THEN
        RAISE EXCEPTION 'Falta índice de lectura por feature';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'importacion_conciliacion_resultado'::regclass
        AND contype = 'p' AND pg_get_constraintdef(oid) LIKE '%(id_ciclo, id_importacion_feature)%') THEN
        RAISE EXCEPTION 'Identidad histórica de resultados modificada';
    END IF;
    IF (SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgenabled = 'O'
        AND tgname IN ('trg_gis_resultado_contexto', 'trg_gis_resultado_inmutable',
                      'trg_gis_decision_inmutable', 'trg_gis_ciclo_historia',
                      'trg_nucleo_version_payload', 'trg_parcela_version_payload', 'trg_ddv_version_payload')) <> 7 THEN
        RAISE EXCEPTION 'Guardas de historia/geometrías alteradas';
    END IF;
    IF NOT has_table_privilege('software_pa_app', 'importacion_conciliacion_resultado', 'SELECT')
       OR NOT has_table_privilege('software_pa_app', 'importacion_conciliacion_resultado', 'INSERT')
       OR has_table_privilege('software_pa_app', 'importacion_conciliacion_resultado', 'UPDATE')
       OR has_table_privilege('software_pa_app', 'importacion_conciliacion_resultado', 'DELETE') THEN
        RAISE EXCEPTION 'Permisos de resultados no son append-only';
    END IF;
END $$;

-- Fixture propia: prueba como owner incluso sin resultados históricos previos.
-- Todas las filas sintéticas se revierten al terminar el contrato.
DO $$
DECLARE
    actor integer;
    project_id integer;
    import_id bigint;
    feature_id bigint;
    cycle_id bigint;
    original jsonb := '{"version":"1","origen":"registrado","codigos":["UNIVERSO_DESTINOS_VACIO"],"mensaje":"Fixture sintética SQL 029","campos_evaluados":[],"evidencia":{"destinos_evaluados":0,"nucleos_evaluados":0,"nucleos_compatibles":0,"parcelas_evaluadas":0,"candidatos":0,"descartes_territoriales":{"municipio":0,"entidad":0,"tipo_nucleo":0},"variantes_formato":[]}}';
BEGIN
    SELECT id_usuario INTO actor FROM usuario WHERE activo AND rol = 'admin' ORDER BY id_usuario LIMIT 1;
    IF actor IS NULL THEN
        RAISE EXCEPTION 'Contrato 029 requiere administrador bootstrap de pruebas';
    END IF;
    PERFORM set_config('app.current_user_id', actor::text, true);
    INSERT INTO proyecto(clave_proyecto, nombre_proyecto, creado_por)
        VALUES ('GIS029-' || substr(md5(random()::text || clock_timestamp()::text), 1, 16),
                'Proyecto sintético contrato SQL 029', actor)
        RETURNING id_proyecto INTO project_id;
    INSERT INTO importacion_archivo(id_proyecto, tipo_objetivo, nombre_original,
        nombre_almacenado, formato_detectado, tamano_bytes, sha256, fuente,
        version_pipeline, estado, total_features, id_usuario_carga, creado_por)
        VALUES (project_id, 'nucleo_agrario_gpkg', 'sql029.gpkg', 'sql029.gpkg',
                'gpkg', 1, repeat('a', 64), 'Fixture sintética SQL 029',
                'conciliacion-v3-historia', 'previsualizado', 1, actor, actor)
        RETURNING id_importacion INTO import_id;
    INSERT INTO importacion_feature(id_importacion, indice_feature, estado, estado_conciliacion)
        VALUES (import_id, 0, 'valido', 'sin_coincidencia')
        RETURNING id_importacion_feature INTO feature_id;
    INSERT INTO importacion_conciliacion_ciclo(id_importacion, numero_ciclo, tipo_ciclo,
        motivo, id_usuario, version_algoritmo, universo_destinos)
        VALUES (import_id, 1, 'inicial', 'Fixture sintética SQL 029', actor,
                'conciliacion-v3-historia', '[]')
        RETURNING id_ciclo INTO cycle_id;
    INSERT INTO importacion_conciliacion_resultado(id_ciclo, id_importacion_feature, estado_matching, diagnostico)
        VALUES (cycle_id, feature_id, 'sin_coincidencia', original);
    BEGIN
        UPDATE importacion_conciliacion_resultado
           SET diagnostico = jsonb_set(diagnostico, '{mensaje}', '"Alteración rechazada"')
         WHERE id_ciclo = cycle_id AND id_importacion_feature = feature_id;
        RAISE EXCEPTION 'Se permitió actualizar un diagnóstico' USING ERRCODE = '23514';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'Las decisiones GIS son append-only' THEN RAISE; END IF;
    END;
    BEGIN
        DELETE FROM importacion_conciliacion_resultado
         WHERE id_ciclo = cycle_id AND id_importacion_feature = feature_id;
        RAISE EXCEPTION 'Se permitió eliminar un resultado' USING ERRCODE = '23514';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'Las decisiones GIS son append-only' THEN RAISE; END IF;
    END;
    IF NOT EXISTS (SELECT 1 FROM importacion_conciliacion_resultado
        WHERE id_ciclo = cycle_id AND id_importacion_feature = feature_id AND diagnostico = original) THEN
        RAISE EXCEPTION 'El diagnóstico sintético no permaneció intacto';
    END IF;
END $$;
ROLLBACK;
