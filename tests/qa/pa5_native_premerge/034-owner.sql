\set ON_ERROR_STOP on
BEGIN;
SELECT set_config('app.current_user_id','1',true);
DO $$
DECLARE cid int; rowid bigint; s text; error_message text; n int:=0;
BEGIN
 IF current_user<>'qa_owner' OR current_database()<>'software_pa_test' OR current_setting('cluster_name') NOT LIKE 'pa5-pr8-%' THEN RAISE EXCEPTION 'private owner required'; END IF;
 SELECT id_convenio INTO STRICT cid FROM convenio WHERE descripcion_instrumento='PA5 synthetic fixture';
 INSERT INTO etiqueta_seguimiento_fifonafe(id_convenio,codigo,habilitada,motivo,creado_por) VALUES(cid,'observaciones_importantes',true,'PA5 owner trigger test',1) RETURNING id_etiqueta INTO rowid;
 FOREACH s IN ARRAY ARRAY[format('UPDATE etiqueta_seguimiento_fifonafe SET motivo=''owner forbidden'' WHERE id_etiqueta=%s',rowid),format('DELETE FROM etiqueta_seguimiento_fifonafe WHERE id_etiqueta=%s',rowid)] LOOP
  BEGIN EXECUTE s; RAISE EXCEPTION 'owner trigger failed';
  EXCEPTION WHEN SQLSTATE 'P0001' THEN
   GET STACKED DIAGNOSTICS error_message=MESSAGE_TEXT;
   IF error_message<>'El historial de etiquetas no se modifica; registre una nueva decisión' THEN RAISE; END IF;
   n:=n+1;
  END;
 END LOOP;
 IF n<>2 OR (SELECT count(*) FROM etiqueta_seguimiento_fifonafe)<>1 THEN RAISE EXCEPTION 'owner rows changed'; END IF;
 RAISE NOTICE 'PA5_034_OWNER_UPDATE_DELETE_TRIGGER_P0001_OK';
END $$;
ROLLBACK;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM etiqueta_seguimiento_fifonafe) OR EXISTS(SELECT 1 FROM bitacora WHERE entidad_tipo='etiqueta_seguimiento_fifonafe') THEN RAISE EXCEPTION 'owner rollback failed'; END IF; END $$;
SELECT 'PA5_034_OWNER_ROLLBACK_OK';
