\set ON_ERROR_STOP on
BEGIN;
DO $$
DECLARE s text; n int:=0;
BEGIN
 IF current_user<>'qa_runtime' OR current_database()<>'software_pa_test' OR current_setting('cluster_name') NOT LIKE 'pa5-pr8-%' THEN RAISE EXCEPTION 'not private runtime connection'; END IF;
 IF EXISTS(SELECT 1 FROM pg_class WHERE relnamespace='public'::regnamespace AND relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)) OR EXISTS(SELECT 1 FROM pg_proc WHERE pronamespace='public'::regnamespace AND proowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)) OR EXISTS(SELECT 1 FROM pg_namespace WHERE nspowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)) THEN RAISE EXCEPTION 'runtime owns objects'; END IF;
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname IN ('qa_runtime','software_pa_app') AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)) THEN RAISE EXCEPTION 'privileged role'; END IF;
 FOREACH s IN ARRAY ARRAY[
 'INSERT INTO schema_migrations(version,nombre,checksum_sha256) VALUES (''999'',''qa_forbidden'',repeat(''0'',64))',
 'UPDATE schema_migrations SET nombre=nombre WHERE false',
 'DELETE FROM schema_migrations WHERE false',
 'TRUNCATE schema_migrations',
 'ALTER TABLE schema_migrations ADD COLUMN qa_forbidden text',
 'DROP TABLE schema_migrations',
 'CREATE TABLE public.qa_forbidden(id int)',
 'CREATE SCHEMA qa_forbidden',
 'ALTER TABLE proyecto ADD COLUMN qa_forbidden text',
 'DROP TABLE proyecto',
 'DELETE FROM proyecto WHERE false',
 'TRUNCATE proyecto',
 'CREATE ROLE qa_forbidden_role',
 'GRANT qa_owner TO qa_runtime',
 'SET ROLE qa_owner',
 'SET session_replication_role=replica'
 ] LOOP
  BEGIN EXECUTE s; RAISE EXCEPTION 'forbidden operation succeeded: %',s;
  EXCEPTION WHEN insufficient_privilege THEN n:=n+1; END;
 END LOOP;
 IF n<>16 THEN RAISE EXCEPTION 'negative count %',n; END IF;
 RAISE NOTICE 'PA5_RUNTIME_16_SQLSTATE_42501_NEGATIVES_OK';
END $$;
ROLLBACK;
