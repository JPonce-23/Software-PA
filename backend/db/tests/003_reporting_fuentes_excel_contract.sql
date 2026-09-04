\set ON_ERROR_STOP on
DO $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='001') OR NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='002') OR NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='003') THEN RAISE EXCEPTION 'migrations 001-003 required'; END IF;
 IF to_regclass('public.vw_reporte_avance_periodo') IS NULL THEN RAISE EXCEPTION 'periodic reporting view missing'; END IF;
 IF position('inscripcion_ran_' in pg_get_viewdef('vw_reporte_avance_periodo'::regclass,true))=0 OR position('''acta''' in pg_get_viewdef('vw_reporte_avance_periodo'::regclass,true))=0 OR position('''convenio''' in pg_get_viewdef('vw_reporte_avance_periodo'::regclass,true))=0 THEN RAISE EXCEPTION 'RAN inscription indicators missing'; END IF;
 IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND column_name IN ('trimestre1','trimestre2','no_parcela_ppt','numero_parcela_ppt','ingreso_por_na','inscrito_por_na')) THEN RAISE EXCEPTION 'forbidden reporting column'; END IF;
END $$;
SELECT * FROM vw_reporte_avance_periodo LIMIT 0;
