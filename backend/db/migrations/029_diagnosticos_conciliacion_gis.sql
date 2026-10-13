-- Expansión informativa: no modifica matching, decisiones ni geometrías.
SET search_path = public, pg_catalog;
SELECT pg_advisory_xact_lock(hashtextextended('software-pa:029:diagnosticos-conciliacion-gis', 0));

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE version = '028'
          AND nombre = 'catalogo_tipo_documento'
          AND checksum_sha256 = '1395d96c59af2fe2192598af13bd5e4f88ca675d4d35e9ba4f19d25cfc7bc845'
    ) THEN RAISE EXCEPTION '029 requiere 028 canónica exacta'; END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '029') THEN
        RAISE EXCEPTION '029 ya se encuentra registrada';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
        AND table_name = 'importacion_conciliacion_resultado' AND column_name = 'diagnostico') THEN
        RAISE EXCEPTION '029 encontró una expansión previa no registrada';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid = 'importacion_conciliacion_resultado'::regclass
        AND tgname = 'trg_gis_resultado_inmutable' AND tgenabled = 'O') THEN
        RAISE EXCEPTION '029 requiere la protección histórica de resultados';
    END IF;
END $$;

ALTER TABLE importacion_conciliacion_resultado ADD COLUMN diagnostico jsonb;
ALTER TABLE importacion_conciliacion_resultado ADD CONSTRAINT chk_resultado_gis_diagnostico CHECK (
    diagnostico IS NULL OR ((
        jsonb_typeof(diagnostico) = 'object'
        AND diagnostico->>'version' = '1'
        AND diagnostico->>'origen' = 'registrado'
        AND jsonb_typeof(diagnostico->'codigos') = 'array'
        AND jsonb_typeof(diagnostico->'mensaje') = 'string'
        AND jsonb_typeof(diagnostico->'campos_evaluados') = 'array'
        AND jsonb_typeof(diagnostico->'evidencia') = 'object'
    ) IS TRUE)
);
CREATE INDEX idx_resultado_gis_feature_ciclo
    ON importacion_conciliacion_resultado (id_importacion_feature, id_ciclo);
COMMENT ON COLUMN importacion_conciliacion_resultado.diagnostico IS
    'Diagnóstico V1 informativo e inmutable del matching de este ciclo. SQL NULL = histórico sin diagnóstico registrado; sin backfill ni reconstrucción con el universo actual.';

-- La guarda existente compara to_jsonb(NEW)/OLD y protege también esta columna.
-- No se amplían permisos ni se deshabilitan triggers.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM importacion_conciliacion_resultado WHERE diagnostico IS NOT NULL) THEN
        RAISE EXCEPTION '029 no debe rellenar diagnósticos históricos';
    END IF;
    IF NOT has_table_privilege('software_pa_app', 'importacion_conciliacion_resultado', 'SELECT')
       OR NOT has_table_privilege('software_pa_app', 'importacion_conciliacion_resultado', 'INSERT')
       OR has_table_privilege('software_pa_app', 'importacion_conciliacion_resultado', 'UPDATE')
       OR has_table_privilege('software_pa_app', 'importacion_conciliacion_resultado', 'DELETE') THEN
        RAISE EXCEPTION '029 requiere permisos append-only de resultados';
    END IF;
END $$;
