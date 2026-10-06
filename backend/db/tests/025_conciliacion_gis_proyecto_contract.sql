\set ON_ERROR_STOP on
BEGIN;
SELECT current_database();
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='024' AND nombre='importacion_parcelas_gpkg' AND checksum_sha256='15f36ea78a591aeb0f587a84e7e2bddb21f53de455d80daaf8532422796bc2d6') THEN RAISE EXCEPTION 'Dependencia canónica 024 incompatible'; END IF;
 IF current_database()<>'software_pa_test' THEN RAISE EXCEPTION 'Contrato 025 sólo permite software_pa_test'; END IF;
 IF NOT EXISTS(SELECT 1 FROM schema_migrations WHERE version='025' AND nombre='conciliacion_gis_proyecto' AND checksum_sha256='8338aace95845761acf0f9b675064ca25a6b0da2117013178ed060f260ec372a') THEN RAISE EXCEPTION '025 no aplicada'; END IF;
 IF (SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN
 ('proyecto_configuracion_gis','proyecto_nucleo_geometria','proyecto_parcela_geometria',
  'importacion_feature_candidato','importacion_feature_decision'))<>5 THEN RAISE EXCEPTION 'Tablas 025 incompletas'; END IF;
 IF (SELECT count(*) FROM information_schema.columns WHERE table_name='importacion_feature' AND column_name IN
 ('geometria_original','geometria_trabajo','crs_fuente','dimension_fuente','estado_conciliacion'))<>5 THEN RAISE EXCEPTION 'Staging incompleto'; END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_indexes WHERE indexname='uq_importacion_idempotente' AND indexdef LIKE '%version_pipeline, srid_trabajo%') THEN RAISE EXCEPTION 'Idempotencia sin versión/CRS'; END IF;
 IF (SELECT count(*) FROM pg_indexes WHERE indexname IN('uq_candidato_seleccion_feature',
 'uq_candidato_seleccion_nucleo','uq_candidato_seleccion_parcela') AND indexdef LIKE '%UNIQUE%')<>3 THEN RAISE EXCEPTION 'Unicidad de decisiones incompleta'; END IF;
 IF (SELECT count(*) FROM pg_indexes WHERE tablename IN('proyecto_nucleo_geometria','proyecto_parcela_geometria') AND indexdef LIKE '%USING gist%')<>4 THEN RAISE EXCEPTION 'GiST incompleto'; END IF;
 IF (SELECT count(*) FROM pg_constraint WHERE contype='f' AND conrelid='importacion_feature_candidato'::regclass)<4 THEN RAISE EXCEPTION 'FK de candidatos incompletas'; END IF;
 IF position('st_intersects' IN lower(pg_get_viewdef('vw_gis_parcela_proyecto'::regclass)))>0 THEN RAISE EXCEPTION 'Intersección convertida en pertenencia'; END IF;
 IF NOT has_table_privilege('software_pa_app','importacion_feature_decision','INSERT') OR has_table_privilege('software_pa_app','importacion_feature_decision','UPDATE') OR has_table_privilege('software_pa_app','importacion_feature_decision','DELETE') THEN RAISE EXCEPTION 'Decisiones no append-only'; END IF;
 IF (SELECT count(*) FROM geometry_columns WHERE f_table_name IN('nucleo_agrario','parcela','trazo_proyecto') AND srid=4326)<>3 THEN RAISE EXCEPTION 'Geometrías legacy alteradas'; END IF;
 IF EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE '%obras_transversales%') THEN RAISE EXCEPTION 'Obras fuera de alcance'; END IF;
END $$;
-- Geometría con hueco estrecho y dos componentes separados < 7 decimales.
DO $$ DECLARE g geometry; BEGIN
 g:=ST_GeomFromText('MULTIPOLYGON(((0 0,1.00000001 0,1.00000001 1,0 1,0 0),(0.1 0.1,0.10000001 0.1,0.10000001 0.2,0.1 0.2,0.1 0.1)),((1.00000002 0,2 0,2 1,1.00000002 1,1.00000002 0)))',4326);
 IF NOT ST_IsValid(g) OR ST_NumGeometries(g)<>2 OR ST_NPoints(g)<>15 THEN RAISE EXCEPTION 'Fixture de precisión incorrecta'; END IF;
 IF ST_NPoints(ST_GeomFromGeoJSON(ST_AsGeoJSON(g,15)))<>15 OR NOT ST_IsValid(ST_GeomFromGeoJSON(ST_AsGeoJSON(g,15))) THEN RAISE EXCEPTION 'Precisión insuficiente'; END IF;
END $$;
ROLLBACK;
