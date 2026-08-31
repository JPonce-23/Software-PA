-- Contrato transaccional del modelo operativo 036. No deja datos.
\set ON_ERROR_STOP on
BEGIN;

DO $contract$
DECLARE
    v_user INTEGER;
    v_municipio INTEGER;
    v_proyecto INTEGER;
    v_nucleo INTEGER;
    v_nucleo_otro INTEGER;
    v_pn INTEGER;
    v_tenencia BIGINT;
    v_residencia BIGINT;
    v_gestion_tuc BIGINT;
    v_gestion_parcela BIGINT;
    v_destino_tuc BIGINT;
    v_destino_escolar BIGINT;
    v_cop_origen BIGINT;
    v_tipo_asamblea BIGINT;
    v_contexto_cop BIGINT;
    v_contexto_adicional BIGINT;
    v_contexto_obras BIGINT;
    v_contexto_retiro BIGINT;
    v_resultado_no BIGINT;
    v_resultado_reprogramada BIGINT;
    v_resultado_celebrada BIGINT;
    v_evento_ingreso BIGINT;
    v_evento_prevencion BIGINT;
    v_evento_subsanacion BIGINT;
    v_evento_reingreso BIGINT;
    v_evento_calificacion BIGINT;
    v_evento_inscripcion BIGINT;
    v_evento_desistimiento BIGINT;
    v_padron INTEGER;
    v_padron_otro INTEGER;
    v_parcela INTEGER;
    v_afectacion_tuc INTEGER;
    v_afectacion_colectiva_parcela INTEGER;
    v_afectacion_individual INTEGER;
    v_asamblea INTEGER;
    v_asamblea_adicional INTEGER;
    v_asamblea_obras INTEGER;
    v_asamblea_retiro INTEGER;
    v_convenio INTEGER;
    v_convenio_2 INTEGER;
    v_convenio_adicional INTEGER;
    v_tramite_ran BIGINT;
    v_tramite_ran_convenio BIGINT;
    v_fifonafe INTEGER;
    v_requisito BIGINT;
    v_estado_doc BIGINT;
    v_documento INTEGER;
    v_importacion BIGINT;
    v_failed BOOLEAN;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='036') THEN
        RAISE EXCEPTION 'El contrato requiere esquema 036';
    END IF;
    SELECT min(id_usuario) INTO v_user FROM usuario WHERE activo;
    PERFORM set_config('app.current_user_id',v_user::TEXT,TRUE);
    SELECT min(id_municipio) INTO v_municipio FROM municipio WHERE activo;

    SELECT id_catalogo_opcion INTO v_tenencia FROM catalogo_operativo WHERE tipo_catalogo='tipo_tenencia' AND codigo='ejido';
    SELECT id_catalogo_opcion INTO v_residencia FROM catalogo_operativo WHERE tipo_catalogo='residencia' AND codigo='queretaro';
    SELECT id_catalogo_opcion INTO v_gestion_tuc FROM catalogo_operativo WHERE tipo_catalogo='tipo_gestion' AND codigo='TUC';
    SELECT id_catalogo_opcion INTO v_gestion_parcela FROM catalogo_operativo WHERE tipo_catalogo='tipo_gestion' AND codigo='PARCELA';
    SELECT id_catalogo_opcion INTO v_destino_tuc FROM catalogo_operativo WHERE tipo_catalogo='destino_superficie' AND codigo='tuc';
    SELECT id_catalogo_opcion INTO v_destino_escolar FROM catalogo_operativo WHERE tipo_catalogo='destino_superficie' AND codigo='parcela_escolar';
    SELECT id_catalogo_opcion INTO v_cop_origen FROM catalogo_operativo WHERE tipo_catalogo='tipo_cop_operativo' AND codigo='ORIGEN';
    SELECT id_catalogo_opcion INTO v_tipo_asamblea FROM catalogo_operativo WHERE tipo_catalogo='tipo_asamblea' AND codigo='anuencia';
    SELECT id_catalogo_opcion INTO v_contexto_cop FROM catalogo_operativo WHERE tipo_catalogo='contexto_asamblea' AND codigo='cop_original';
    SELECT id_catalogo_opcion INTO v_contexto_adicional FROM catalogo_operativo WHERE tipo_catalogo='contexto_asamblea' AND codigo='superficie_adicional';
    SELECT id_catalogo_opcion INTO v_contexto_obras FROM catalogo_operativo WHERE tipo_catalogo='contexto_asamblea' AND codigo='obras_complementarias';
    SELECT id_catalogo_opcion INTO v_contexto_retiro FROM catalogo_operativo WHERE tipo_catalogo='contexto_asamblea' AND codigo='retiro_fondos';
    SELECT id_catalogo_opcion INTO v_resultado_no FROM catalogo_operativo WHERE tipo_catalogo='resultado_convocatoria' AND codigo='no_verificativo';
    SELECT id_catalogo_opcion INTO v_resultado_reprogramada FROM catalogo_operativo WHERE tipo_catalogo='resultado_convocatoria' AND codigo='reprogramada';
    SELECT id_catalogo_opcion INTO v_resultado_celebrada FROM catalogo_operativo WHERE tipo_catalogo='resultado_convocatoria' AND codigo='celebrada';
    SELECT id_catalogo_opcion INTO v_evento_ingreso FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_ran' AND codigo='ingreso';
    SELECT id_catalogo_opcion INTO v_evento_prevencion FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_ran' AND codigo='prevencion';
    SELECT id_catalogo_opcion INTO v_evento_subsanacion FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_ran' AND codigo='subsanacion';
    SELECT id_catalogo_opcion INTO v_evento_reingreso FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_ran' AND codigo='reingreso';
    SELECT id_catalogo_opcion INTO v_evento_calificacion FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_ran' AND codigo='calificacion';
    SELECT id_catalogo_opcion INTO v_evento_inscripcion FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_ran' AND codigo='inscripcion';
    SELECT id_catalogo_opcion INTO v_evento_desistimiento FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_ran' AND codigo='desistimiento';

    INSERT INTO proyecto(clave_proyecto,nombre_proyecto,creado_por)
    VALUES ('QA-036-'||txid_current(),'Contrato 036',v_user) RETURNING id_proyecto INTO v_proyecto;
    INSERT INTO nucleo_agrario(id_municipio,nombre_nucleo,tipo_nucleo,id_tipo_tenencia,comunidad_indigena,creado_por)
    VALUES (v_municipio,'NÚCLEO QA 036 '||txid_current(),'ejido',v_tenencia,NULL,v_user) RETURNING id_nucleo INTO v_nucleo;
    INSERT INTO nucleo_agrario(id_municipio,nombre_nucleo,tipo_nucleo,id_tipo_tenencia,comunidad_indigena,creado_por)
    VALUES (v_municipio,'NÚCLEO OTRO QA 036 '||txid_current(),'ejido',v_tenencia,FALSE,v_user) RETURNING id_nucleo INTO v_nucleo_otro;
    INSERT INTO proyecto_nucleo(id_proyecto,id_nucleo,residencia,id_residencia,total_cops_planeados,creado_por)
    VALUES (v_proyecto,v_nucleo,'Querétaro',v_residencia,4,v_user) RETURNING id_proyecto_nucleo INTO v_pn;
    IF (SELECT comunidad_indigena FROM nucleo_agrario WHERE id_nucleo=v_nucleo) IS NOT NULL THEN
        RAISE EXCEPTION 'NULL de comunidad indígena se convirtió indebidamente en FALSE';
    END IF;

    INSERT INTO padron_historial(id_nucleo,fecha_padron,numero_ejidatarios_comuneros,fuente,creado_por)
    VALUES (v_nucleo,DATE '2026-01-15',42,'QA',v_user) RETURNING id_padron INTO v_padron;
    INSERT INTO padron_historial(id_nucleo,fecha_padron,numero_ejidatarios_comuneros,fuente,creado_por)
    VALUES (v_nucleo_otro,DATE '2026-01-16',9,'QA',v_user) RETURNING id_padron INTO v_padron_otro;
    INSERT INTO parcela(id_nucleo,tipo_parcela,no_parcela,creado_por)
    VALUES (v_nucleo,'individual','P-60',v_user) RETURNING id_parcela INTO v_parcela;

    INSERT INTO afectacion(id_proyecto_nucleo,tipo_afectacion,creado_por)
    VALUES (v_pn,'colectivo',v_user) RETURNING id_afectacion INTO v_afectacion_tuc;
    INSERT INTO bien_afectado(id_afectacion,id_tipo_gestion,id_destino_superficie,superficie_afectada_ha,superficie_valor_original,superficie_formato_origen,creado_por)
    VALUES (v_afectacion_tuc,v_gestion_tuc,v_destino_tuc,0.016809,'00-01-68.096','H-M2-CM2',v_user);

    INSERT INTO afectacion(id_proyecto_nucleo,id_parcela,tipo_afectacion,creado_por)
    VALUES (v_pn,v_parcela,'colectivo',v_user) RETURNING id_afectacion INTO v_afectacion_colectiva_parcela;
    INSERT INTO bien_afectado(id_afectacion,id_tipo_gestion,id_destino_superficie,id_tipo_cop_operativo,id_parcela,referencia_alfanumerica,creado_por)
    VALUES (v_afectacion_colectiva_parcela,v_gestion_parcela,v_destino_escolar,v_cop_origen,v_parcela,'P-60',v_user);

    INSERT INTO afectacion(id_proyecto_nucleo,id_parcela,tipo_afectacion,creado_por)
    VALUES (v_pn,v_parcela,'individual',v_user) RETURNING id_afectacion INTO v_afectacion_individual;
    IF (SELECT tipo_afectacion FROM afectacion WHERE id_afectacion=v_afectacion_colectiva_parcela)<>'colectivo' THEN
        RAISE EXCEPTION 'TIPO_GESTION determinó indebidamente el ámbito';
    END IF;

    INSERT INTO actividad_campo(id_proyecto_nucleo,tipo_actividad,contexto_actividad,fecha_programada,creado_por)
    VALUES (v_pn,'sensibilizacion','general',DATE '2026-02-01',v_user);
    INSERT INTO actividad_campo(id_proyecto_nucleo,tipo_actividad,contexto_actividad,fecha_realizada,creado_por)
    VALUES (v_pn,'sensibilizacion','general',DATE '2026-02-02',v_user);
    INSERT INTO actividad_campo(id_proyecto_nucleo,tipo_actividad,contexto_actividad,fecha_programada,fecha_realizada,creado_por)
    VALUES (v_pn,'caminamiento','general',DATE '2026-02-03',DATE '2026-02-04',v_user);
    INSERT INTO actividad_campo(id_proyecto_nucleo,tipo_actividad,contexto_actividad,fecha_programada,fecha_realizada,creado_por)
    VALUES (v_pn,'caminamiento','general',DATE '2026-03-03',DATE '2026-03-04',v_user);
    v_failed:=FALSE;
    BEGIN
        INSERT INTO actividad_campo(id_proyecto_nucleo,tipo_actividad,contexto_actividad,fecha_programada,fecha_realizada,creado_por)
        VALUES (v_pn,'caminamiento','general',DATE '2026-03-03',DATE '2026-03-04',v_user);
    EXCEPTION WHEN unique_violation THEN v_failed:=TRUE; END;
    IF NOT v_failed THEN RAISE EXCEPTION 'Actividad Excel duplicada no fue rechazada'; END IF;

    INSERT INTO asamblea(id_proyecto_nucleo,id_padron,tipo_asamblea,id_tipo_asamblea,contexto_proceso,id_contexto_asamblea,creado_por)
    VALUES (v_pn,v_padron,'anuencia',v_tipo_asamblea,'cop_original',v_contexto_cop,v_user) RETURNING id_asamblea INTO v_asamblea;
    INSERT INTO asamblea_convocatoria(id_asamblea,ordinal,fecha_programada,id_resultado,creado_por)
    VALUES (v_asamblea,1,DATE '2026-04-01',v_resultado_no,v_user),
           (v_asamblea,2,DATE '2026-04-15',v_resultado_reprogramada,v_user),
           (v_asamblea,3,DATE '2026-04-30',v_resultado_celebrada,v_user);
    IF (SELECT count(*) FROM asamblea_convocatoria WHERE id_asamblea=v_asamblea AND activo)<>3 THEN
        RAISE EXCEPTION 'No se preservaron tres convocatorias';
    END IF;
    v_failed:=FALSE;
    BEGIN
        INSERT INTO asamblea(id_proyecto_nucleo,id_padron,tipo_asamblea,id_tipo_asamblea,contexto_proceso,id_contexto_asamblea,creado_por)
        VALUES (v_pn,v_padron_otro,'anuencia',v_tipo_asamblea,'cop_original',v_contexto_cop,v_user);
    EXCEPTION WHEN others THEN v_failed:=TRUE; END;
    IF NOT v_failed THEN RAISE EXCEPTION 'Se aceptó padrón de otro núcleo'; END IF;

    INSERT INTO asamblea(id_proyecto_nucleo,tipo_asamblea,id_tipo_asamblea,contexto_proceso,id_contexto_asamblea,creado_por)
    VALUES (v_pn,'anuencia',v_tipo_asamblea,'superficie_adicional',v_contexto_adicional,v_user) RETURNING id_asamblea INTO v_asamblea_adicional;
    INSERT INTO asamblea(id_proyecto_nucleo,tipo_asamblea,id_tipo_asamblea,contexto_proceso,id_contexto_asamblea,creado_por)
    VALUES (v_pn,'anuencia',v_tipo_asamblea,'obras_complementarias',v_contexto_obras,v_user) RETURNING id_asamblea INTO v_asamblea_obras;
    SELECT id_catalogo_opcion INTO v_tipo_asamblea FROM catalogo_operativo WHERE tipo_catalogo='tipo_asamblea' AND codigo='retiro_fondos';
    INSERT INTO asamblea(id_proyecto_nucleo,tipo_asamblea,id_tipo_asamblea,contexto_proceso,id_contexto_asamblea,creado_por)
    VALUES (v_pn,'retiro_fondos',v_tipo_asamblea,'retiro_fondos',v_contexto_retiro,v_user) RETURNING id_asamblea INTO v_asamblea_retiro;

    INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_convenio,consecutivo,id_asamblea_autorizacion,creado_por)
    VALUES (v_pn,'colectivo','cop_original',1,v_asamblea,v_user) RETURNING id_convenio INTO v_convenio;
    INSERT INTO convenio_afectacion(id_convenio,id_afectacion,rol,creado_por)
    VALUES (v_convenio,v_afectacion_tuc,'principal',v_user),(v_convenio,v_afectacion_colectiva_parcela,'adicional',v_user);
    INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_convenio,consecutivo,id_asamblea_autorizacion,creado_por)
    VALUES (v_pn,'colectivo','cop_original',1,v_asamblea,v_user) RETURNING id_convenio INTO v_convenio_2;
    INSERT INTO convenio_afectacion(id_convenio,id_afectacion,rol,creado_por)
    VALUES (v_convenio_2,v_afectacion_colectiva_parcela,'principal',v_user);
    INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_convenio,consecutivo,id_convenio_padre,id_asamblea_autorizacion,creado_por)
    VALUES (v_pn,'colectivo','superficie_adicional',2,v_convenio,v_asamblea_adicional,v_user) RETURNING id_convenio INTO v_convenio_adicional;
    INSERT INTO convenio_afectacion(id_convenio,id_afectacion,rol,creado_por)
    VALUES (v_convenio_adicional,v_afectacion_tuc,'principal',v_user);
    IF (SELECT tipo_cop_operativo FROM vw_convenio_tipo_cop_operativo WHERE id_convenio=v_convenio_adicional)<>'2A ADICIONAL' THEN
        RAISE EXCEPTION '2A ADICIONAL se modeló como tipo nuevo';
    END IF;
    v_failed:=FALSE;
    BEGIN
        UPDATE convenio SET id_convenio_padre=v_convenio_adicional WHERE id_convenio=v_convenio;
    EXCEPTION WHEN others THEN v_failed:=TRUE; END;
    IF NOT v_failed THEN RAISE EXCEPTION 'Se aceptó relación padre/hijo inválida'; END IF;

    INSERT INTO tramite_ran(id_proyecto_nucleo,id_asamblea,creado_por)
    VALUES (v_pn,v_asamblea,v_user) RETURNING id_tramite_ran INTO v_tramite_ran;
    INSERT INTO tramite_ran_evento(id_tramite_ran,ordinal,id_tipo_evento,fecha_evento,numero_solicitud,creado_por) VALUES
      (v_tramite_ran,1,v_evento_ingreso,DATE '2026-05-01','SOL-1',v_user),
      (v_tramite_ran,2,v_evento_prevencion,DATE '2026-05-05','SOL-1',v_user),
      (v_tramite_ran,3,v_evento_subsanacion,DATE '2026-05-10','SOL-1',v_user),
      (v_tramite_ran,4,v_evento_reingreso,DATE '2026-05-11','SOL-2',v_user),
      (v_tramite_ran,5,v_evento_inscripcion,DATE '2026-05-30','SOL-2',v_user);
    IF (SELECT count(*) FROM tramite_ran_evento WHERE id_tramite_ran=v_tramite_ran)<>5
       OR (SELECT numero_solicitud_ran FROM asamblea WHERE id_asamblea=v_asamblea)<>'SOL-2' THEN
        RAISE EXCEPTION 'Historial/reingreso RAN de asamblea no se preservó';
    END IF;

    INSERT INTO tramite_ran(id_proyecto_nucleo,id_convenio,creado_por)
    VALUES (v_pn,v_convenio,v_user) RETURNING id_tramite_ran INTO v_tramite_ran_convenio;
    INSERT INTO tramite_ran_evento(id_tramite_ran,ordinal,id_tipo_evento,fecha_evento,numero_solicitud,calificacion,creado_por) VALUES
      (v_tramite_ran_convenio,1,v_evento_ingreso,DATE '2026-06-01','C-1',NULL,v_user),
      (v_tramite_ran_convenio,2,v_evento_desistimiento,DATE '2026-06-02','C-1',NULL,v_user),
      (v_tramite_ran_convenio,3,v_evento_ingreso,DATE '2026-06-03','C-2',NULL,v_user),
      (v_tramite_ran_convenio,4,v_evento_calificacion,DATE '2026-06-10','C-2','POSITIVA',v_user),
      (v_tramite_ran_convenio,5,v_evento_inscripcion,DATE '2026-06-20','C-2',NULL,v_user);
    IF (SELECT count(*) FROM tramite_ran_evento WHERE id_tramite_ran=v_tramite_ran_convenio)<>5 THEN
        RAISE EXCEPTION 'Historial RAN de convenio fue sobrescrito';
    END IF;

    INSERT INTO tramite_fifonafe(id_proyecto_nucleo,ambito,estatus,creado_por)
    VALUES (v_pn,'colectivo','pendiente',v_user) RETURNING id_tramite_fifonafe INTO v_fifonafe;
    INSERT INTO tramite_fifonafe_afectacion(id_tramite_fifonafe,id_afectacion,creado_por)
    VALUES (v_fifonafe,v_afectacion_tuc,v_user),(v_fifonafe,v_afectacion_colectiva_parcela,v_user);
    INSERT INTO tramite_fifonafe_evento(id_tramite_fifonafe,ordinal,id_tipo_evento,numero_oficio,fecha_oficio,creado_por)
    SELECT v_fifonafe,1,id_catalogo_opcion,'QA-036',DATE '2026-07-01',v_user
    FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_fifonafe' AND codigo='oficio_fifonafe_dgaopr';

    INSERT INTO documento(tipo_documento,estado,titulo,creado_por)
    VALUES ('acta_no_verificativo','disponible','QA 036',v_user) RETURNING id_documento INTO v_documento;
    SELECT id_requisito INTO v_requisito FROM requisito_documental WHERE codigo='acta_no_verificativo';
    SELECT id_catalogo_opcion INTO v_estado_doc FROM catalogo_operativo WHERE tipo_catalogo='estado_requisito_documental' AND codigo='disponible';
    INSERT INTO expediente_requisito(id_proyecto_nucleo,id_requisito,id_estado,id_documento,creado_por)
    VALUES (v_pn,v_requisito,v_estado_doc,v_documento,v_user);

    INSERT INTO importacion_tabular(id_proyecto,archivo,sha256,hoja,filas_detectadas,estado,creado_por)
    VALUES (v_proyecto,'colectivo.xlsx',repeat('a',64),'INFORME M-Q',146,'auditado',v_user)
    RETURNING id_importacion_tabular INTO v_importacion;
    INSERT INTO importacion_tabular_celda(id_importacion_tabular,fila,columna,encabezado,valor_original,valor_normalizado,tratamiento,mensajes,id_usuario_registro)
    VALUES (v_importacion,7,'BM','SUPERFICIE','00-01-68.096','0.016809','PERSISTIR','["redondeo_a_6_decimales"]',v_user);

    v_failed:=FALSE;
    BEGIN DELETE FROM catalogo_operativo WHERE id_catalogo_opcion=v_gestion_tuc;
    EXCEPTION WHEN others THEN v_failed:=TRUE; END;
    IF NOT v_failed THEN RAISE EXCEPTION 'Catálogo permitió DELETE físico'; END IF;

    RAISE NOTICE 'CONTRATO 036 APROBADO';
END;
$contract$;

ROLLBACK;
