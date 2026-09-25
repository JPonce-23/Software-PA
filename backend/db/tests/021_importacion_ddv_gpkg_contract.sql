\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_objetivo text;
    v_contrato text;
    v_trigger text;
BEGIN
    IF current_database() <> 'software_pa_test' THEN
        RAISE EXCEPTION '021 contract solo puede ejecutarse en software_pa_test';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations
         WHERE version = '021' AND nombre = 'importacion_ddv_gpkg'
           AND checksum_sha256 = '16f63229569574f078105423a1a914c1621b6662150dfc090124f60817b719f6'
    ) THEN
        RAISE EXCEPTION '021 no esta aplicada con el checksum esperado';
    END IF;
    SELECT pg_get_constraintdef(oid) INTO v_objetivo
      FROM pg_constraint
     WHERE conrelid = 'importacion_archivo'::regclass
       AND conname = 'chk_importacion_objetivo';
    IF v_objetivo IS NULL
       OR position('derecho_via_proyecto' in v_objetivo) = 0
       OR position('trazo_proyecto' in v_objetivo) = 0
       OR position('nucleo_agrario' in v_objetivo) = 0
       OR position('parcela' in v_objetivo) = 0 THEN
        RAISE EXCEPTION 'Objetivos de importacion incompletos';
    END IF;

    SELECT pg_get_constraintdef(oid) INTO v_contrato
      FROM pg_constraint
     WHERE conrelid = 'importacion_archivo'::regclass
       AND conname = 'chk_importacion_ddv_gpkg';
    IF v_contrato IS NULL
       OR position('gpkg' in v_contrato) = 0
       OR position('mapeo' in v_contrato) = 0
       OR position('EPSG:4326' in v_contrato) = 0 THEN
        RAISE EXCEPTION 'Falta contrato GPKG sin mapeo para DDV';
    END IF;

    SELECT pg_get_functiondef('fn_validar_importacion_feature_objetivo()'::regprocedure)
      INTO v_trigger;
    IF position('derecho_via_proyecto' in v_trigger) = 0
       OR position('id_proyecto = v_id_proyecto' in v_trigger) = 0
       OR position('MULTIPOLYGON' in v_trigger) = 0 THEN
        RAISE EXCEPTION 'El trigger no valida geometria y destino DDV del proyecto';
    END IF;
    RAISE NOTICE '021 OK: staging DDV estricto y objetivos legacy preservados';
END $$;

ROLLBACK;
