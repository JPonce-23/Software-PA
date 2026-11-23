\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = pg_temp, public, pg_catalog;
SELECT pg_catalog.set_config('app.current_user_id','1',true);
CREATE TEMP TABLE bitacora (LIKE public.bitacora INCLUDING ALL);
DO $$
DECLARE pid integer; pc integer; tc integer;
BEGIN
 IF current_user<>'qa_runtime' OR current_database()<>'software_pa_test' OR current_setting('cluster_name') NOT LIKE 'pa5-pr8-%' THEN RAISE EXCEPTION 'private runtime required'; END IF;
 IF NOT has_database_privilege(current_user,current_database(),'TEMP') THEN RAISE EXCEPTION 'TEMP must stay enabled for this regression'; END IF;
 INSERT INTO public.proyecto(clave_proyecto,nombre_proyecto) VALUES('PA5_AUDIT_035','Synthetic namespace regression') RETURNING id_proyecto INTO pid;
 UPDATE public.proyecto SET nombre_proyecto='Synthetic audited update' WHERE id_proyecto=pid;
 SELECT count(*) INTO pc FROM public.bitacora WHERE entidad_tipo='proyecto' AND entidad_id=pid;
 SELECT count(*) INTO tc FROM pg_temp.bitacora WHERE entidad_tipo='proyecto' AND entidad_id=pid;
 IF pc<>2 OR tc<>0 THEN RAISE EXCEPTION 'AUDIT_035_PERSISTENCE_MISMATCH public=% temp=%',pc,tc; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.bitacora WHERE entidad_tipo='proyecto' AND entidad_id=pid AND accion='insert') OR NOT EXISTS(SELECT 1 FROM public.bitacora WHERE entidad_tipo='proyecto' AND entidad_id=pid AND accion='update' AND valor_anterior->>'nombre_proyecto'='Synthetic namespace regression' AND valor_nuevo->>'nombre_proyecto'='Synthetic audited update') THEN RAISE EXCEPTION 'audit snapshots changed'; END IF;
 RAISE NOTICE 'AUDIT_035_PERSISTENCE_INSERT_UPDATE_OK public=2 temp=0';
END $$;
-- The caller explicitly prefers public while the hostile temporary relations remain.
-- This isolates the definer's lookups from unrelated invoker-trigger resolution.
SET LOCAL search_path = public, pg_temp, pg_catalog;
CREATE TEMP TABLE proyecto_nucleo AS SELECT * FROM public.proyecto_nucleo;
UPDATE pg_temp.proyecto_nucleo SET id_proyecto=-999,id_nucleo=-999;
CREATE TEMP TABLE convenio AS SELECT * FROM public.convenio;
UPDATE pg_temp.convenio SET id_proyecto_nucleo=-999;
DO $$
DECLARE pn public.proyecto_nucleo%ROWTYPE; link public.convenio_afectacion%ROWTYPE;
BEGIN
 SELECT * INTO STRICT pn FROM public.proyecto_nucleo;
 UPDATE public.proyecto_nucleo SET total_cops_planeados=1 WHERE id_proyecto_nucleo=pn.id_proyecto_nucleo;
 SELECT * INTO STRICT link FROM public.convenio_afectacion;
 UPDATE public.convenio_afectacion SET observaciones='035 synthetic context check' WHERE id_convenio_afectacion=link.id_convenio_afectacion;
 IF NOT EXISTS(SELECT 1 FROM public.bitacora WHERE entidad_tipo='proyecto_nucleo' AND entidad_id=pn.id_proyecto_nucleo AND id_proyecto=pn.id_proyecto AND id_nucleo=pn.id_nucleo) OR NOT EXISTS(SELECT 1 FROM public.bitacora WHERE entidad_tipo='convenio_afectacion' AND entidad_id=link.id_convenio_afectacion AND id_proyecto_nucleo=pn.id_proyecto_nucleo AND id_proyecto=pn.id_proyecto AND id_nucleo=pn.id_nucleo) THEN RAISE EXCEPTION 'persistent context lookups changed'; END IF;
 IF EXISTS(SELECT 1 FROM pg_temp.bitacora) THEN RAISE EXCEPTION 'audit reached temporary sink'; END IF;
 RAISE NOTICE 'AUDIT_035_CONTEXT_LOOKUPS_OK';
END $$;
ROLLBACK;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM public.proyecto WHERE clave_proyecto='PA5_AUDIT_035') OR EXISTS(SELECT 1 FROM public.bitacora WHERE valor_nuevo->>'observaciones'='035 synthetic context check') THEN RAISE EXCEPTION '035 rollback failed'; END IF; END $$;
SELECT 'AUDIT_035_PERSISTENCE_ROLLBACK_OK';
