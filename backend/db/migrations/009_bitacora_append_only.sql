-- Append-only application access to bitacora. The audit trigger remains SECURITY DEFINER.
SET search_path = public, pg_catalog;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM schema_migrations
    WHERE version = '008'
      AND checksum_sha256 = '95bf328f18112933481488c59763df6a6467d8fd3db354bb7e5465c727c8f012'
  ) THEN
    RAISE EXCEPTION '009 requiere la migración 008 exacta';
  END IF;
  IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '009') THEN
    RAISE EXCEPTION '009 ya se encuentra registrada';
  END IF;
  IF NOT EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.proname = 'fn_audit_log'
      AND p.prosecdef
      AND has_table_privilege(p.proowner, 'public.bitacora', 'INSERT')
  ) THEN
    RAISE EXCEPTION '009 requiere fn_audit_log SECURITY DEFINER con INSERT sobre bitacora';
  END IF;
END $$;

SELECT pg_advisory_xact_lock(hashtextextended('software-pa:009:bitacora-append-only', 0));

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.bitacora FROM software_pa_app;
GRANT SELECT ON public.bitacora TO software_pa_app;
