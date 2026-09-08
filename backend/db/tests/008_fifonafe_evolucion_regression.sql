\set ON_ERROR_STOP on
SET search_path=public,pg_catalog;

-- Regresión sintética post-008. Selecciona identidades existentes sin atribuirles
-- hechos históricos; toda escritura se revierte.
BEGIN;
DO $$
DECLARE
 v_pn integer; v_af integer; v_user integer; v_tipo bigint;
 v_t1 integer; v_t2 integer; v_e bigint; v_doc integer;
BEGIN
 SELECT id_proyecto_nucleo INTO v_pn FROM proyecto_nucleo WHERE activo ORDER BY id_proyecto_nucleo LIMIT 1;
 SELECT id_afectacion INTO v_af FROM afectacion WHERE activo AND id_proyecto_nucleo=v_pn ORDER BY id_afectacion LIMIT 1;
 SELECT id_usuario INTO v_user FROM usuario WHERE activo ORDER BY id_usuario LIMIT 1;
 IF v_pn IS NULL OR v_af IS NULL OR v_user IS NULL THEN RAISE EXCEPTION 'Fixture QA insuficiente'; END IF;
 PERFORM set_config('app.current_user_id',v_user::text,true);

 INSERT INTO documento(tipo_documento,estado,titulo,creado_por)
 VALUES ('fifonafe_prueba_008','disponible','SINTETICO 008',v_user) RETURNING id_documento INTO v_doc;
 INSERT INTO documento_vinculo(id_documento,entidad_tipo,entidad_id,creado_por)
 VALUES (v_doc,'proyecto_nucleo',v_pn,v_user);
 INSERT INTO tramite_fifonafe(id_proyecto_nucleo,ambito,estatus,hay_conflictos,creado_por)
 SELECT v_pn,a.tipo_afectacion,'pendiente',NULL,v_user FROM afectacion a WHERE a.id_afectacion=v_af
 RETURNING id_tramite_fifonafe INTO v_t1;
 INSERT INTO tramite_fifonafe(id_proyecto_nucleo,ambito,estatus,hay_conflictos,creado_por)
 SELECT v_pn,a.tipo_afectacion,'pendiente',false,v_user FROM afectacion a WHERE a.id_afectacion=v_af
 RETURNING id_tramite_fifonafe INTO v_t2;
 IF v_t1=v_t2 OR (SELECT version_flujo FROM tramite_fifonafe WHERE id_tramite_fifonafe=v_t1)<>2 THEN
  RAISE EXCEPTION 'Identidad/version v2 incorrecta'; END IF;
 -- Un mismo soporte puede pertenecer a dos solicitudes: no se fusionan por hash/documento.
 INSERT INTO tramite_fifonafe_afectacion(id_tramite_fifonafe,id_afectacion,creado_por)
 VALUES (v_t1,v_af,v_user),(v_t2,v_af,v_user);

 SELECT id_catalogo_opcion INTO v_tipo FROM catalogo_operativo
 WHERE tipo_catalogo='tipo_evento_fifonafe' AND codigo=(
   SELECT CASE tipo_afectacion WHEN 'colectivo' THEN 'solicitud_retiro_colectivo'
          ELSE 'solicitud_retiro_individual' END FROM afectacion WHERE id_afectacion=v_af
 );
 INSERT INTO tramite_fifonafe_evento(id_tramite_fifonafe,ordinal,id_tipo_evento,fecha_evento,id_documento,creado_por)
 VALUES (v_t1,1,v_tipo,DATE '2026-01-01',v_doc,v_user),
        (v_t2,1,v_tipo,DATE '2026-01-01',v_doc,v_user);
 IF (SELECT count(*) FROM vw_fifonafe_hito_008 WHERE indicador='fif_solicitud_recibida'
     AND split_part(clave_hito,':',2)::integer IN (v_t1,v_t2))<>2 THEN
  RAISE EXCEPTION 'Un documento compartido fusionó solicitudes distintas'; END IF;

 SELECT id_catalogo_opcion INTO v_tipo FROM catalogo_operativo
 WHERE tipo_catalogo='tipo_evento_fifonafe' AND codigo='consulta_conflictos_enviada';
 INSERT INTO tramite_fifonafe_evento(id_tramite_fifonafe,ordinal,id_tipo_evento,ciclo_consulta,fecha_oficio,numero_oficio,creado_por)
 VALUES (v_t1,2,v_tipo,NULL,DATE '2026-01-05','SINT-SIN-CICLO',v_user),
        (v_t2,2,v_tipo,1,DATE '2026-01-10','SINT-1',v_user),
        (v_t2,3,v_tipo,2,DATE '2026-02-10','SINT-2',v_user);
 SELECT id_catalogo_opcion INTO v_tipo FROM catalogo_operativo
 WHERE tipo_catalogo='tipo_evento_fifonafe' AND codigo='respuesta_conflictos_acreditada';
 INSERT INTO tramite_fifonafe_evento(id_tramite_fifonafe,ordinal,id_tipo_evento,ciclo_consulta,fecha_evento,
   conflicto_impide_retiro,id_documento,creado_por)
 VALUES (v_t2,4,v_tipo,2,DATE '2026-02-20',false,v_doc,v_user) RETURNING id_evento_fifonafe INTO v_e;
 IF NOT EXISTS (SELECT 1 FROM vw_fifonafe_cobertura_008
                WHERE eventos_consulta_sin_ciclo>0) THEN
  RAISE EXCEPTION 'Evento sin ciclo no quedó en cobertura pendiente'; END IF;
 IF EXISTS (SELECT 1 FROM vw_fifonafe_consulta_008 WHERE id_tramite_fifonafe=v_t2
             AND ciclo_consulta=1 AND consulta_concluida_sin_impedimento) THEN
  RAISE EXCEPTION 'Se mezclaron rondas'; END IF;
 IF NOT EXISTS (SELECT 1 FROM vw_fifonafe_consulta_008 WHERE id_tramite_fifonafe=v_t2
                AND ciclo_consulta=2 AND consulta_concluida_sin_impedimento) THEN
  RAISE EXCEPTION 'Ronda 2 acreditada no fue reconocida'; END IF;
 IF NOT EXISTS (SELECT 1 FROM vw_fifonafe_hito_008 WHERE indicador='informe_no_conflictos'
                AND clave_hito LIKE 'fifonafe_v2:'||v_t2||':%') THEN
  RAISE EXCEPTION 'informe_no_conflictos acreditado ausente'; END IF;
 IF EXISTS (SELECT 1 FROM pago WHERE creado_en>=transaction_timestamp())
 OR EXISTS (SELECT 1 FROM indemnizacion WHERE creado_en>=transaction_timestamp()) THEN
  RAISE EXCEPTION 'FIFONAFE creó Pago o Indemnización'; END IF;
END $$;
SET CONSTRAINTS ctr_fifonafe_completo_evento,ctr_fifonafe_completo_parent,
 ctr_fifonafe_requiere_afectacion,ctr_fifonafe_vinculo_requerido,
 ctr_fifonafe_evidencia_evento_008,ctr_fifonafe_evidencia_documento_008,
 ctr_fifonafe_evidencia_archivo_008,ctr_fifonafe_completo_vinculo_008,
 ctr_fifonafe_completo_documento_008,ctr_fifonafe_completo_asamblea_008,
 ctr_fifonafe_completo_convocatoria_008 IMMEDIATE;
ROLLBACK;

SELECT '008_REGRESSION_OK' AS resultado;
