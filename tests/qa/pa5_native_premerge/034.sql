\set ON_ERROR_STOP on
BEGIN;
SELECT set_config('app.current_user_id','1',true);
DO $$
DECLARE cid int; rowid bigint; failures int:=0; error_message text;
BEGIN
 IF current_database()<>'software_pa_test' OR current_setting('cluster_name') NOT LIKE 'pa5-pr8-%' OR current_user<>'qa_runtime' THEN RAISE EXCEPTION 'private runtime required'; END IF;
 IF EXISTS(SELECT 1 FROM etiqueta_seguimiento_fifonafe) THEN RAISE EXCEPTION 'labels must be empty'; END IF;
 SELECT id_convenio INTO STRICT cid FROM convenio WHERE descripcion_instrumento='PA5 synthetic fixture';
 INSERT INTO etiqueta_seguimiento_fifonafe(id_convenio,codigo,habilitada,motivo,creado_por) VALUES(cid,'espera_firma',true,'PA5 synthetic activation',1) RETURNING id_etiqueta INTO rowid;
 INSERT INTO etiqueta_seguimiento_fifonafe(id_convenio,codigo,habilitada,motivo,creado_por) VALUES(cid,'espera_firma',false,'PA5 synthetic retirement',1);
 IF (SELECT count(*) FROM etiqueta_seguimiento_fifonafe)<>2 OR (SELECT count(*) FROM bitacora WHERE entidad_tipo='etiqueta_seguimiento_fifonafe' AND accion='insert')<>2 THEN RAISE EXCEPTION 'append/audit missing'; END IF;
 BEGIN
  UPDATE etiqueta_seguimiento_fifonafe SET motivo='PA5 forbidden change' WHERE id_etiqueta=rowid;
  RAISE EXCEPTION 'UPDATE unexpectedly succeeded';
 EXCEPTION WHEN SQLSTATE 'P0001' THEN
  GET STACKED DIAGNOSTICS error_message=MESSAGE_TEXT;
  IF error_message<>'El historial de etiquetas no se modifica; registre una nueva decisión' THEN RAISE; END IF;
  failures:=failures+1;
 END;
 BEGIN DELETE FROM etiqueta_seguimiento_fifonafe WHERE id_etiqueta=rowid; RAISE EXCEPTION 'runtime DELETE succeeded';
 EXCEPTION WHEN insufficient_privilege THEN failures:=failures+1; END;
 IF failures<>2 OR (SELECT count(*) FROM etiqueta_seguimiento_fifonafe)<>2 OR NOT EXISTS(SELECT 1 FROM etiqueta_seguimiento_fifonafe WHERE id_etiqueta=rowid AND motivo='PA5 synthetic activation') THEN RAISE EXCEPTION 'unexpected rows after negative'; END IF;
 RAISE NOTICE 'PA5_034_RUNTIME_APPEND_AUDIT_UPDATE_P0001_DELETE_42501_OK';
END $$;
ROLLBACK;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM etiqueta_seguimiento_fifonafe) OR EXISTS(SELECT 1 FROM bitacora WHERE entidad_tipo='etiqueta_seguimiento_fifonafe') THEN RAISE EXCEPTION 'rollback failed'; END IF; END $$;
SELECT 'PA5_034_RUNTIME_ROLLBACK_OK';
