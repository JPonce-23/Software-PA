\set ON_ERROR_STOP on
BEGIN;
DO $$ BEGIN
 IF current_database()<>'software_pa_test' OR current_setting('cluster_name') NOT LIKE 'pa5-pr8-%' OR current_user<>'qa_runtime' THEN RAISE EXCEPTION 'private runtime required'; END IF;
 BEGIN
  CREATE TEMP TABLE pa5_temp_object_probe(id integer);
  INSERT INTO pa5_temp_object_probe VALUES(1);
  RAISE NOTICE 'PA5_TEMP_CREATION_ALLOWED';
 EXCEPTION WHEN insufficient_privilege THEN RAISE NOTICE 'PA5_TEMP_CREATION_DENIED_42501'; END;
END $$;
ROLLBACK;
