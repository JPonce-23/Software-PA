\set ON_ERROR_STOP on
BEGIN;
SELECT pg_catalog.set_config('app.current_user_id','1',true);
CREATE TEMP TABLE proyecto AS SELECT * FROM public.proyecto WITH NO DATA;
CREATE TRIGGER qa_forged_audit AFTER INSERT ON pg_temp.proyecto FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_proyecto');
DO $$
DECLARE message text;
BEGIN
 IF current_user<>'qa_runtime' OR current_database()<>'software_pa_test' OR current_setting('cluster_name') NOT LIKE 'pa5-pr8-%' THEN RAISE EXCEPTION 'private runtime required'; END IF;
 BEGIN
  INSERT INTO pg_temp.proyecto SELECT * FROM public.proyecto WHERE clave_proyecto='PA5_SYNTHETIC';
  RAISE EXCEPTION 'AUDIT_035_FORGED_TRIGGER_ACCEPTED';
 EXCEPTION WHEN SQLSTATE 'P0001' THEN
  GET STACKED DIAGNOSTICS message=MESSAGE_TEXT;
  IF message<>'Auditoría sólo admite relaciones de public' THEN RAISE; END IF;
 END;
 RAISE NOTICE 'AUDIT_035_TEMP_TRIGGER_REJECTED_OK';
END $$;
ROLLBACK;
SELECT 'AUDIT_035_ORIGIN_ROLLBACK_OK';
