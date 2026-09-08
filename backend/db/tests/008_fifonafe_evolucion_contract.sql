\set ON_ERROR_STOP on
SET search_path=public,pg_catalog;

DO $$
DECLARE v_count bigint; v_aplicada timestamptz;
BEGIN
 IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='008') THEN
  RAISE EXCEPTION 'Contrato 008 requiere ledger aplicado'; END IF;
 IF (SELECT checksum_sha256 FROM schema_migrations WHERE version='007') <>
    'adabd7775fb8165a1db8be04a93e7971fe207e745b410c57eb6fc76cc3a7e4f7' THEN
  RAISE EXCEPTION 'Checksum 007 alterado'; END IF;
 IF (SELECT checksum_sha256 FROM schema_migrations WHERE version='008') <>
    '95bf328f18112933481488c59763df6a6467d8fd3db354bb7e5465c727c8f012' THEN
  RAISE EXCEPTION 'Checksum 008 distinto del candidato validado'; END IF;

 SELECT aplicada_en INTO v_aplicada FROM schema_migrations WHERE version='008';
 SELECT count(*) INTO v_count FROM tramite_fifonafe
 WHERE creado_en<v_aplicada AND version_flujo<>1;
 IF v_count<>0 THEN RAISE EXCEPTION 'Backfill histórico no neutral: % filas',v_count; END IF;
 IF EXISTS (SELECT 1 FROM tramite_fifonafe WHERE creado_en<v_aplicada
            AND (referencia_expediente IS NOT NULL OR id_asamblea_retiro IS NOT NULL))
 OR EXISTS (SELECT 1 FROM tramite_fifonafe_evento WHERE creado_en<v_aplicada
            AND (ciclo_consulta IS NOT NULL OR fecha_evento IS NOT NULL OR conflicto_impide_retiro IS NOT NULL))
 OR EXISTS (SELECT 1 FROM tramite_fifonafe_interviniente WHERE creado_en<v_aplicada) THEN
  RAISE EXCEPTION '008 inventó evidencia histórica'; END IF;

 IF (SELECT column_default FROM information_schema.columns WHERE table_schema='public'
     AND table_name='tramite_fifonafe' AND column_name='version_flujo') NOT LIKE '%2%' THEN
  RAISE EXCEPTION 'Nuevas solicitudes no tienen version_flujo=2'; END IF;
 IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public'
   AND table_name='tramite_fifonafe_evento' AND column_name='ciclo_consulta'
   AND is_nullable<>'YES') THEN RAISE EXCEPTION 'ciclo_consulta debe ser nullable'; END IF;

 IF EXISTS (SELECT h.* FROM vw_hito_seguimiento_007 h
             WHERE h.indicador<>'fifonafe' OR EXISTS (SELECT 1 FROM tramite_fifonafe t WHERE t.version_flujo=1 AND h.clave_hito='fifonafe:'||t.id_tramite_fifonafe)
            EXCEPT SELECT * FROM vw_hito_seguimiento)
 OR EXISTS (SELECT * FROM vw_hito_seguimiento WHERE indicador='fifonafe'
            EXCEPT SELECT h.* FROM vw_hito_seguimiento_007 h WHERE h.indicador='fifonafe'
             AND EXISTS (SELECT 1 FROM tramite_fifonafe t WHERE t.version_flujo=1 AND h.clave_hito='fifonafe:'||t.id_tramite_fifonafe)) THEN
  RAISE EXCEPTION 'El indicador legado fifonafe cambió'; END IF;
 IF EXISTS (SELECT 1 FROM vw_fifonafe_hito_008 h
   GROUP BY h.clave_hito HAVING count(*)>1) THEN
  RAISE EXCEPTION 'Reporting FIFONAFE depende de cardinalidad de afectaciones'; END IF;
END $$;

-- Objetos, columnas y tipos exactos.
SELECT table_name,column_name,data_type,is_nullable
FROM information_schema.columns
WHERE table_schema='public' AND table_name IN
 ('tramite_fifonafe','tramite_fifonafe_evento','tramite_fifonafe_interviniente',
  'vw_fifonafe_consulta_008','vw_fifonafe_cobertura_008',
  'vw_fifonafe_indicador_institucional_008')
ORDER BY table_name,ordinal_position;

DO $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='ctr_fifonafe_evidencia_evento_008'
   AND tgenabled='O' AND tgdeferrable AND tginitdeferred) THEN
  RAISE EXCEPTION 'Constraint trigger de evidencia ausente o no diferido'; END IF;
 IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid IN
   ('tramite_fifonafe'::regclass,'tramite_fifonafe_evento'::regclass,
    'tramite_fifonafe_interviniente'::regclass) AND NOT tgisinternal AND tgenabled<>'O') THEN
  RAISE EXCEPTION 'Hay triggers FIFONAFE deshabilitados'; END IF;
 IF NOT has_table_privilege('software_pa_app','tramite_fifonafe_interviniente','SELECT,INSERT,UPDATE')
 OR NOT has_table_privilege('software_pa_app','vw_fifonafe_cobertura_008','SELECT')
 OR NOT has_table_privilege('software_pa_app','vw_fifonafe_indicador_institucional_008','SELECT') THEN
  RAISE EXCEPTION 'ACL 008 incompleta'; END IF;
 IF pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid='tramite_fifonafe_interviniente'::regclass))
    <> pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid='tramite_fifonafe'::regclass)) THEN
  RAISE EXCEPTION 'Propietario 008 incompatible con tablas existentes'; END IF;
END $$;

-- Sonda contractual siempre revertida: triestado, rondas y documento compartido
-- no deduplican solicitudes. Los detalles de fixtures viven en la regresión 008.
BEGIN;
SET CONSTRAINTS ctr_fifonafe_evidencia_evento_008 IMMEDIATE;
SET CONSTRAINTS ctr_fifonafe_evidencia_evento_008 DEFERRED;
ROLLBACK;

SELECT '008_CONTRACT_OK' AS resultado;
