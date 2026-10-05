\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_objetivo text;
    v_contrato text;
    v_trigger text;
BEGIN
 IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='021' AND nombre='derecho_via_proyecto' AND checksum_sha256='c759eaab96a7ed88679fd5fa288504b4bdf36724479d82e155044a572da90d4e') THEN RAISE EXCEPTION 'Dependencia canónica 021 incompatible'; END IF;
    IF current_database() <> 'software_pa_test' THEN
        RAISE EXCEPTION '022 contract solo puede ejecutarse en software_pa_test';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations
         WHERE version = '022' AND nombre = 'importacion_ddv_gpkg'
           AND checksum_sha256 = '40e988e06f7f211995ea62456ee7fc64e951fabd2ff14609f155de968171d58f'
    ) THEN
        RAISE EXCEPTION '022 no esta aplicada con el checksum esperado';
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
    RAISE NOTICE '022 OK: staging DDV estricto y objetivos legacy preservados';
END $$;

ROLLBACK;
