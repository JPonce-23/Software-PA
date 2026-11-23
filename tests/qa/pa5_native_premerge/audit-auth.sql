\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = public, pg_temp, pg_catalog;
SELECT pg_catalog.set_config('app.current_user_id','1',true);
CREATE TEMP TABLE bitacora (LIKE public.bitacora INCLUDING ALL);
CREATE TEMP TABLE evento_acceso AS SELECT * FROM public.evento_acceso WITH NO DATA;
DO $$
DECLARE sid bigint; eid bigint; fakeid bigint:=900000001; auditcount integer; message text;
BEGIN
 IF current_user<>'qa_runtime' OR current_database()<>'software_pa_test' OR current_setting('cluster_name') NOT LIKE 'pa5-pr8-%' THEN RAISE EXCEPTION 'private runtime required'; END IF;
 INSERT INTO public.sesion_usuario(id_usuario,token_hash,csrf_hash,expira_en) VALUES(1,repeat('a',64),repeat('b',64),now()+interval '1 day') RETURNING id_sesion INTO sid;
 SELECT count(*) INTO auditcount FROM public.bitacora WHERE entidad_tipo='sesion_usuario' AND entidad_id=sid;
 IF auditcount<>1 THEN RAISE EXCEPTION 'session insert audit missing'; END IF;
 UPDATE public.sesion_usuario SET ultima_actividad=clock_timestamp() WHERE id_sesion=sid;
 IF (SELECT count(*) FROM public.bitacora WHERE entidad_tipo='sesion_usuario' AND entidad_id=sid)<>auditcount THEN RAISE EXCEPTION 'heartbeat no longer suppressed'; END IF;
 PERFORM set_config('app.current_user_id','',true);
 BEGIN
  UPDATE public.sesion_usuario SET csrf_hash=repeat('c',64) WHERE id_sesion=sid;
  RAISE EXCEPTION 'secret-only update accepted without actor';
 EXCEPTION WHEN SQLSTATE 'P0001' THEN
  GET STACKED DIAGNOSTICS message=MESSAGE_TEXT;
  IF message<>'Auditoría fallida: falta app.current_user_id en la transacción' THEN RAISE; END IF;
 END;
 PERFORM set_config('app.current_user_id','1',true);
 UPDATE public.sesion_usuario SET csrf_hash=repeat('c',64) WHERE id_sesion=sid;
 IF (SELECT count(*) FROM public.bitacora WHERE entidad_tipo='sesion_usuario' AND entidad_id=sid)<>auditcount THEN RAISE EXCEPTION 'secret-only audit suppression changed'; END IF;
 UPDATE public.sesion_usuario SET csrf_hash=repeat('d',64),user_agent_creacion='synthetic 035' WHERE id_sesion=sid;
 auditcount:=auditcount+1;
 IF (SELECT count(*) FROM public.bitacora WHERE entidad_tipo='sesion_usuario' AND entidad_id=sid)<>auditcount OR EXISTS(SELECT 1 FROM public.bitacora WHERE entidad_tipo='sesion_usuario' AND entidad_id=sid AND (valor_anterior ?| ARRAY['token_hash','csrf_hash','contrasena_hash'] OR valor_nuevo ?| ARRAY['token_hash','csrf_hash','contrasena_hash'])) THEN RAISE EXCEPTION 'secret redaction or combined audit changed'; END IF;
 -- A fake event in pg_temp must not authorize the privileged system-event bypass.
 INSERT INTO pg_temp.evento_acceso(id_evento,id_usuario,id_usuario_actor,id_sesion,tipo_evento,motivo_codigo,txid_registro) VALUES(fakeid,1,NULL,sid,'sesion_expirada','expiracion_inactividad',txid_current());
 PERFORM set_config('app.current_user_id','',true);
 PERFORM set_config('app.auth_system_event_id',fakeid::text,true);
 BEGIN
  UPDATE public.sesion_usuario SET revocada_en=clock_timestamp(),motivo_revocacion='expiracion_inactividad' WHERE id_sesion=sid;
  RAISE EXCEPTION 'temporary event authorized system expiration';
 EXCEPTION WHEN SQLSTATE 'P0001' THEN
  GET STACKED DIAGNOSTICS message=MESSAGE_TEXT;
  IF message<>'Expiración de sesión sin evento de sistema correlacionado o con cambios no permitidos' THEN RAISE; END IF;
 END;
 INSERT INTO public.evento_acceso(id_usuario,id_usuario_actor,id_sesion,tipo_evento,motivo_codigo) VALUES(1,NULL,sid,'sesion_expirada','expiracion_inactividad') RETURNING id_evento INTO eid;
 PERFORM set_config('app.auth_system_event_id',eid::text,true);
 UPDATE public.sesion_usuario SET revocada_en=clock_timestamp(),motivo_revocacion='expiracion_inactividad' WHERE id_sesion=sid;
 IF NOT EXISTS(SELECT 1 FROM public.sesion_usuario WHERE id_sesion=sid AND revocada_en IS NOT NULL) OR (SELECT count(*) FROM public.bitacora WHERE entidad_tipo='sesion_usuario' AND entidad_id=sid)<>auditcount OR EXISTS(SELECT 1 FROM pg_temp.bitacora) THEN RAISE EXCEPTION 'legitimate system-event behavior changed'; END IF;
 RAISE NOTICE 'AUDIT_035_AUTH_ACTOR_SECRET_HEARTBEAT_EVENT_OK';
END $$;
ROLLBACK;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM public.sesion_usuario) OR EXISTS(SELECT 1 FROM public.evento_acceso) THEN RAISE EXCEPTION 'authentication rollback failed'; END IF; END $$;
SELECT 'AUDIT_035_AUTH_ROLLBACK_OK';
