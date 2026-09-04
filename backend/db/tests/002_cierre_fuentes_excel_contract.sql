\set ON_ERROR_STOP on
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='001') THEN RAISE EXCEPTION '001 missing'; END IF;
  IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='002') THEN RAISE EXCEPTION '002 missing'; END IF;
  IF NOT EXISTS (SELECT 1 FROM catalogo_operativo WHERE tipo_catalogo='tipo_cop_operativo' AND codigo='TRANSVERSALES' AND activo) THEN RAISE EXCEPTION 'TRANSVERSALES missing'; END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='actividad_campo' AND column_name='id_tipo_cop_operativo') THEN RAISE EXCEPTION 'activity COP missing'; END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='asamblea' AND column_name='id_tipo_cop_operativo') THEN RAISE EXCEPTION 'assembly COP missing'; END IF;
  IF NOT EXISTS (SELECT 1 FROM catalogo_operativo WHERE tipo_catalogo='contexto_asamblea' AND codigo='transversal' AND activo) THEN RAISE EXCEPTION 'transversal assembly context missing'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='indemnizacion'::regclass AND pg_get_constraintdef(oid) LIKE '%pagado%') THEN RAISE EXCEPTION 'indemnizacion does not accept pagado'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='expediente_requisito'::regclass AND pg_get_constraintdef(oid) LIKE '%actividad_campo%' AND pg_get_constraintdef(oid) LIKE '%asamblea_convocatoria%' AND pg_get_constraintdef(oid) LIKE '%padron_historial%' AND pg_get_constraintdef(oid) LIKE '%orv%') THEN RAISE EXCEPTION 'new documental targets missing'; END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND column_name IN ('programada_por_nucleo','realizada_por_nucleo','gestion_por_nucleo','ingreso_por_na','inscrito_por_na','no_parcela_ppt','numero_parcela_ppt')) THEN RAISE EXCEPTION 'forbidden Excel helper column exists'; END IF;
  IF to_regclass('public.bien_afectado') IS NOT NULL THEN RAISE EXCEPTION 'bien_afectado must not exist'; END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tramite_ran' AND column_name='fecha_programada_ingreso') THEN RAISE EXCEPTION 'RAN programmed date missing'; END IF;
  IF (SELECT count(*) FROM information_schema.columns WHERE table_name='tramite_ran_evento' AND column_name IN ('fecha_evento','numero_solicitud','calificacion')) <> 3 THEN RAISE EXCEPTION 'RAN event fields missing'; END IF;
END $$;
SELECT * FROM vw_dashboard_kpi LIMIT 0;
