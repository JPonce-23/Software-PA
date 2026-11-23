\set ON_ERROR_STOP on
BEGIN;
SELECT set_config('app.current_user_id','1',true);
DO $$
DECLARE project_id int; persistent_count int; temporary_count int;
BEGIN
 IF current_database()<>'software_pa_test' OR current_setting('cluster_name') NOT LIKE 'pa5-pr8-%' OR current_user<>'qa_runtime' THEN RAISE EXCEPTION 'private runtime required'; END IF;
 CREATE TEMP TABLE bitacora (LIKE public.bitacora INCLUDING ALL);
 INSERT INTO public.proyecto(clave_proyecto,nombre_proyecto) VALUES('PA5_TEMP_SHADOW_PROBE','Synthetic audit lookup probe') RETURNING id_proyecto INTO project_id;
 SELECT count(*) INTO persistent_count FROM public.bitacora WHERE entidad_tipo='proyecto' AND entidad_id=project_id;
 SELECT count(*) INTO temporary_count FROM pg_temp.bitacora WHERE entidad_tipo='proyecto' AND entidad_id=project_id;
 RAISE NOTICE 'PA5_AUDIT_SHADOW_COUNTS persistent=% temporary=%',persistent_count,temporary_count;
 IF persistent_count=0 AND temporary_count=1 THEN
  RAISE NOTICE 'PA5_AUDIT_TEMP_SHADOW_REPRODUCED';
 ELSIF persistent_count=1 AND temporary_count=0 THEN
  RAISE NOTICE 'PA5_AUDIT_TEMP_SHADOW_NOT_REPRODUCED';
 ELSE RAISE EXCEPTION 'unexpected audit counts'; END IF;
END $$;
ROLLBACK;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM public.proyecto WHERE clave_proyecto='PA5_TEMP_SHADOW_PROBE') THEN RAISE EXCEPTION 'shadow probe rollback failed'; END IF; END $$;
SELECT 'PA5_AUDIT_TEMP_SHADOW_ROLLBACK_OK';
