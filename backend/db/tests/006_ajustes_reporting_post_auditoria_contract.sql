\set ON_ERROR_STOP on
DO $$
DECLARE d text;
BEGIN
 IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='006' AND checksum_sha256 ~ '^[0-9a-f]{64}$') THEN RAISE EXCEPTION '006 no registrada'; END IF;
 IF (SELECT count(*) FROM schema_migrations WHERE version IN ('001','002','003','004','005','006')) <> 6 THEN RAISE EXCEPTION 'cadena de migraciones incompleta'; END IF;
 IF to_regclass('vw_reporte_snapshot_actual') IS NULL THEN RAISE EXCEPTION 'snapshot actual ausente'; END IF;
 d := pg_get_viewdef('vw_hito_seguimiento'::regclass,true);
 IF position('ingreso_ran_retiro_fondos' IN d)=0 OR position('inscripcion_ran_retiro_fondos' IN d)=0 THEN RAISE EXCEPTION 'RAN retiro no diferenciado'; END IF;
 IF position('a.id_tipo_cop_operativo' IN d)=0 THEN RAISE EXCEPTION 'COP de Asamblea ausente'; END IF;
 IF position('numero_oficio' IN d)=0 THEN RAISE EXCEPTION 'FIFONAFE no exige número de oficio'; END IF;
 IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND lower(column_name) IN ('x','no_parcela_ppt','numero_parcela_ppt','trimestre1','trimestre2','trimestre3','trimestre4')) THEN RAISE EXCEPTION 'columna auxiliar prohibida'; END IF;
END $$;
SELECT 'CONTRATO 006 AJUSTES POST AUDITORIA APROBADO' AS resultado;
