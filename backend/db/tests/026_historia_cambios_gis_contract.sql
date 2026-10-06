\set ON_ERROR_STOP on
BEGIN;
SELECT current_database();
DO $$ BEGIN
 IF current_database()<>'software_pa_test' THEN RAISE EXCEPTION 'Contrato 026 sólo permite software_pa_test'; END IF;
 IF NOT EXISTS(SELECT 1 FROM schema_migrations WHERE version='025' AND nombre='conciliacion_gis_proyecto'
 AND checksum_sha256='8338aace95845761acf0f9b675064ca25a6b0da2117013178ed060f260ec372a')
 THEN RAISE EXCEPTION '025 canónica incompatible'; END IF;
 IF NOT EXISTS(SELECT 1 FROM schema_migrations WHERE version='026' AND nombre='historia_cambios_gis'
 AND checksum_sha256='6615a137655abbb2a6ea2620d7c8b5013f07d6fcdd81aae4270a4551904ea3fd')
 THEN RAISE EXCEPTION '026 no aplicada'; END IF;
 IF (SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r'
 AND relname IN('importacion_conciliacion_ciclo','importacion_conciliacion_resultado','revision_cambio_gis','revision_cambio_gis_decision'))<>4
 THEN RAISE EXCEPTION 'Historia GIS incompleta'; END IF;
 IF (SELECT count(*) FROM pg_constraint WHERE contype='f' AND conrelid='revision_cambio_gis'::regclass)<13
 THEN RAISE EXCEPTION 'Referencias tipadas incompletas'; END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conname='fk_decision_candidato_ciclo')
 OR NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conname='fk_candidato_resultado')
 THEN RAISE EXCEPTION 'Candidatos/decisiones sin contexto histórico'; END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname='uq_candidato_destino' AND indexdef LIKE '%id_ciclo%')
 THEN RAISE EXCEPTION 'Candidatos de distintos intentos colisionan'; END IF;
 IF (SELECT count(*) FROM pg_indexes WHERE indexname IN('uq_candidato_confirmacion_feature',
 'uq_candidato_confirmacion_nucleo','uq_candidato_confirmacion_parcela','uq_nucleo_geometria_vigente','uq_parcela_geometria_vigente')
 AND indexdef LIKE '%UNIQUE%')<>5 THEN RAISE EXCEPTION 'Unicidad de confirmaciones/versiones incompleta'; END IF;
 IF EXISTS(SELECT 1 FROM importacion_feature_candidato WHERE id_ciclo IS NULL)
 OR EXISTS(SELECT 1 FROM importacion_feature_decision WHERE id_ciclo IS NULL)
 THEN RAISE EXCEPTION 'Backfill incompleto'; END IF;
 IF EXISTS(SELECT 1 FROM pg_trigger WHERE NOT tgisinternal AND tgenabled='D'
 AND tgrelid IN('importacion_feature_candidato'::regclass,'importacion_feature_decision'::regclass))
 THEN RAISE EXCEPTION 'Guardas históricas suspendidas'; END IF;
 IF position('st_intersects' IN lower(pg_get_viewdef('vw_gis_parcela_proyecto'::regclass)))>0
 THEN RAISE EXCEPTION 'GIS convertido en pertenencia administrativa'; END IF;
 IF position('revision_cambio_gis_decision' IN pg_get_viewdef('vw_revision_cambio_gis_estado'::regclass))=0
 THEN RAISE EXCEPTION 'Estado de revisión no derivado de decisiones'; END IF;
 IF (SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgname IN(
 'trg_inmutable_revision_cambio_gis','trg_inmutable_revision_cambio_gis_decision',
 'trg_gis_resultado_inmutable','trg_gis_decision_inmutable','trg_gis_ciclo_historia',
 'trg_nucleo_version_payload','trg_parcela_version_payload','trg_ddv_version_payload','trg_gis_revision_decision_contexto'))<>9
 THEN RAISE EXCEPTION 'Guardas append-only/contexto incompletas'; END IF;
 IF has_table_privilege('software_pa_app','revision_cambio_gis_decision','UPDATE')
 OR has_table_privilege('software_pa_app','revision_cambio_gis_decision','DELETE')
 OR has_table_privilege('software_pa_app','revision_cambio_gis','UPDATE')
 OR has_table_privilege('software_pa_app','importacion_conciliacion_resultado','UPDATE')
 THEN RAISE EXCEPTION 'Permisos permiten reescritura histórica'; END IF;
 IF EXISTS(SELECT 1 FROM pg_attribute WHERE attrelid='revision_cambio_gis'::regclass AND attname='estado_revision' AND NOT attisdropped)
 THEN RAISE EXCEPTION 'Estado físico redundante'; END IF;
 IF (SELECT count(*) FROM catalogo_operativo WHERE tipo_catalogo='tipo_cop_operativo'
 AND codigo IN('ORIGEN','ADICIONAL','2A_ADICIONAL','COMPLEMENTARIAS','TRANSVERSALES') AND activo)<>5
 THEN RAISE EXCEPTION 'Tipos COP alterados'; END IF;
END $$;
DO $$ DECLARE a geometry; b geometry; BEGIN
 a:=ST_GeomFromText('POLYGON((0 0,0 1,1 1,1 0,0 0))',4326);
 b:=ST_GeomFromText('POLYGON((1 1,0 1,0 0,1 0,1 1))',4326);
 IF NOT ST_Equals(a,b) OR ST_AsEWKB(a)=ST_AsEWKB(b) THEN RAISE EXCEPTION 'Igualdad topológica no probada'; END IF;
 IF ST_Equals(a,ST_Translate(b,0.000000001,0)) THEN RAISE EXCEPTION 'Diferencia pequeña ocultada'; END IF;
END $$;
ROLLBACK;
