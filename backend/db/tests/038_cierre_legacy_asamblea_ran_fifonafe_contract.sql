-- 038_cierre_legacy_asamblea_ran_fifonafe_contract.sql
\set ON_ERROR_STOP on
BEGIN;

DO $contract$
DECLARE
  u INTEGER; mun INTEGER; p INTEGER; n INTEGER; pn INTEGER;
  ten BIGINT; res BIGINT; ta BIGINT; ca BIGINT;
  ran_ing BIGINT; ran_ins BIGINT; orv_estado BIGINT;
  f1 BIGINT; f2 BIGINT; f3 BIGINT; f4 BIGINT;
  a INTEGER; o INTEGER; af INTEGER; cv INTEGER; ff INTEGER;
  ra1 BIGINT; ra2 BIGINT; ro1 BIGINT; ro2 BIGINT;
  failed BOOLEAN; cnt INTEGER;
BEGIN
  IF NOT EXISTS(SELECT 1 FROM schema_migrations WHERE version='038') THEN
    RAISE EXCEPTION 'Contrato 038 requiere esquema 038';
  END IF;
  SELECT min(id_usuario) INTO u FROM usuario WHERE activo;
  SELECT min(id_municipio) INTO mun FROM municipio WHERE activo;
  IF u IS NULL OR mun IS NULL THEN RAISE EXCEPTION 'Faltan usuario/municipio activos'; END IF;
  PERFORM set_config('app.current_user_id',u::text,TRUE);

  SELECT id_catalogo_opcion INTO ten FROM catalogo_operativo WHERE tipo_catalogo='tipo_tenencia' AND codigo='ejido' AND activo;
  SELECT id_catalogo_opcion INTO res FROM catalogo_operativo WHERE tipo_catalogo='residencia' AND activo ORDER BY orden,id_catalogo_opcion LIMIT 1;
  SELECT id_catalogo_opcion INTO ta FROM catalogo_operativo WHERE tipo_catalogo='tipo_asamblea' AND codigo='anuencia' AND activo;
  SELECT id_catalogo_opcion INTO ca FROM catalogo_operativo WHERE tipo_catalogo='contexto_asamblea' AND codigo='cop_original' AND activo;
  SELECT id_catalogo_opcion INTO ran_ing FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_ran' AND codigo='ingreso' AND activo;
  SELECT id_catalogo_opcion INTO ran_ins FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_ran' AND codigo='inscripcion' AND activo;
  SELECT id_catalogo_opcion INTO orv_estado FROM catalogo_operativo WHERE tipo_catalogo='estado_registral_orv' AND codigo='no_ingresada' AND activo;
  SELECT id_catalogo_opcion INTO f1 FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_fifonafe' AND codigo='oficio_fifonafe_dgaopr' AND activo;
  SELECT id_catalogo_opcion INTO f2 FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_fifonafe' AND codigo='oficio_dgaopr_representacion' AND activo;
  SELECT id_catalogo_opcion INTO f3 FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_fifonafe' AND codigo='respuesta_representacion_dgaopr' AND activo;
  SELECT id_catalogo_opcion INTO f4 FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_fifonafe' AND codigo='respuesta_dgaopr_fifonafe' AND activo;
  IF ten IS NULL OR res IS NULL OR ta IS NULL OR ca IS NULL OR ran_ing IS NULL OR ran_ins IS NULL
     OR orv_estado IS NULL OR f1 IS NULL OR f2 IS NULL OR f3 IS NULL OR f4 IS NULL THEN
    RAISE EXCEPTION 'Faltan catalogos 038';
  END IF;

  INSERT INTO proyecto(clave_proyecto,nombre_proyecto,creado_por)
  VALUES('QA038-'||txid_current(),'Contrato QA 038',u) RETURNING id_proyecto INTO p;
  INSERT INTO nucleo_agrario(id_municipio,nombre_nucleo,tipo_nucleo,id_tipo_tenencia,creado_por)
  VALUES(mun,'NUCLEO QA 038 '||txid_current(),'ejido',ten,u) RETURNING id_nucleo INTO n;
  INSERT INTO proyecto_nucleo(id_proyecto,id_nucleo,id_residencia,residencia,creado_por)
  VALUES(p,n,res,'compatibilidad',u) RETURNING id_proyecto_nucleo INTO pn;
  INSERT INTO afectacion(id_proyecto_nucleo,tipo_afectacion,creado_por)
  VALUES(pn,'colectivo',u) RETURNING id_afectacion INTO af;

  INSERT INTO asamblea(id_proyecto_nucleo,id_tipo_asamblea,id_contexto_asamblea,tipo_asamblea,contexto_proceso,creado_por)
  VALUES(pn,ta,ca,'anuencia','cop_original',u) RETURNING id_asamblea INTO a;
  INSERT INTO orv(id_nucleo,numero_orv,id_estado_registral,creado_por)
  VALUES(n,'ORV-QA-038',orv_estado,u) RETURNING id_orv INTO o;

  INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,consecutivo,creado_por)
  VALUES(pn,'colectivo','convenio','cop_original',1,u) RETURNING id_convenio INTO cv;
  INSERT INTO convenio_afectacion(id_convenio,id_afectacion,rol,creado_por)
  VALUES(cv,af,'principal',u);

  -- RAN 1:N para Asamblea.
  INSERT INTO tramite_ran(id_proyecto_nucleo,id_asamblea,fecha_programada_ingreso,referencia_expediente,creado_por)
  VALUES(pn,a,DATE '2026-09-01','A-QA-1',u) RETURNING id_tramite_ran INTO ra1;
  INSERT INTO tramite_ran(id_proyecto_nucleo,id_asamblea,fecha_programada_ingreso,referencia_expediente,creado_por)
  VALUES(pn,a,DATE '2026-09-02','A-QA-2',u) RETURNING id_tramite_ran INTO ra2;
  SELECT count(*) INTO cnt FROM tramite_ran WHERE id_asamblea=a AND activo;
  IF cnt<>2 THEN RAISE EXCEPTION 'RAN de Asamblea no admite 1:N'; END IF;

  INSERT INTO tramite_ran_evento(id_tramite_ran,ordinal,id_tipo_evento,fecha_evento,numero_solicitud,creado_por)
  VALUES(ra2,1,ran_ing,DATE '2026-09-03','SOL-QA-038',u);
  IF (SELECT fecha_programada_ingreso_ran FROM asamblea WHERE id_asamblea=a)
     IS DISTINCT FROM DATE '2026-09-02' THEN
    RAISE EXCEPTION 'Resumen RAN Asamblea no usa tramite mas reciente';
  END IF;
  IF (SELECT numero_solicitud_ran FROM asamblea WHERE id_asamblea=a)
     IS DISTINCT FROM 'SOL-QA-038' THEN
    RAISE EXCEPTION 'Evento RAN no proyecto resumen Asamblea';
  END IF;

  -- ORV por Nucleo, sin ProyectoNucleo y tambien 1:N.
  INSERT INTO tramite_ran(id_nucleo,id_orv,referencia_expediente,creado_por)
  VALUES(n,o,'ORV-QA-1',u) RETURNING id_tramite_ran INTO ro1;
  INSERT INTO tramite_ran(id_nucleo,id_orv,referencia_expediente,creado_por)
  VALUES(n,o,'ORV-QA-2',u) RETURNING id_tramite_ran INTO ro2;
  SELECT count(*) INTO cnt FROM tramite_ran
  WHERE id_orv=o AND activo AND id_nucleo=n AND id_proyecto_nucleo IS NULL;
  IF cnt<>2 THEN RAISE EXCEPTION 'RAN ORV no quedo 1:N por NucleoAgrario'; END IF;

  failed:=FALSE;
  BEGIN
    INSERT INTO tramite_ran(id_proyecto_nucleo,id_orv,creado_por) VALUES(pn,o,u);
  EXCEPTION WHEN others THEN failed:=TRUE;
  END;
  IF NOT failed THEN RAISE EXCEPTION 'ORV acepto ProyectoNucleo arbitrario'; END IF;

  INSERT INTO tramite_ran_evento(id_tramite_ran,ordinal,id_tipo_evento,fecha_evento,creado_por)
  VALUES(ro2,1,ran_ins,DATE '2026-09-04',u);
  IF (SELECT fecha_inscripcion_acta_ran FROM orv WHERE id_orv=o)
     IS DISTINCT FROM DATE '2026-09-04' THEN
    RAISE EXCEPTION 'Evento RAN ORV no proyecto fecha de inscripcion';
  END IF;

  failed:=FALSE;
  BEGIN
    UPDATE orv SET fecha_inscripcion_acta_ran=DATE '2026-10-01' WHERE id_orv=o;
  EXCEPTION WHEN others THEN failed:=TRUE;
  END;
  IF NOT failed THEN RAISE EXCEPTION 'ORV permitio escritura de fecha RAN legacy'; END IF;

  -- Legacy Asamblea bloqueado; convocatoria canonica proyecta.
  failed:=FALSE;
  BEGIN
    UPDATE asamblea SET fecha_programada_primera=DATE '2026-10-01' WHERE id_asamblea=a;
  EXCEPTION WHEN others THEN failed:=TRUE;
  END;
  IF NOT failed THEN RAISE EXCEPTION 'Asamblea permitio escritura legacy'; END IF;

  INSERT INTO asamblea_convocatoria(id_asamblea,ordinal,fecha_expedicion,fecha_programada,creado_por)
  VALUES(a,1,DATE '2026-09-05',DATE '2026-09-10',u);
  IF (SELECT fecha_programada_primera FROM asamblea WHERE id_asamblea=a)
     IS DISTINCT FROM DATE '2026-09-10' THEN
    RAISE EXCEPTION 'Convocatoria no proyecto resumen Asamblea';
  END IF;

  -- Legacy RAN Convenio bloqueado.
  failed:=FALSE;
  BEGIN
    UPDATE convenio SET numero_solicitud_ingreso='LEGACY-NO' WHERE id_convenio=cv;
  EXCEPTION WHEN others THEN failed:=TRUE;
  END;
  IF NOT failed THEN RAISE EXCEPTION 'Convenio permitio escritura RAN legacy'; END IF;

  -- FIFONAFE: legacy bloqueado, eventos canonicos y contrato de completo.
  INSERT INTO tramite_fifonafe(id_proyecto_nucleo,ambito,estatus,creado_por)
  VALUES(pn,'colectivo','pendiente',u) RETURNING id_tramite_fifonafe INTO ff;
  INSERT INTO tramite_fifonafe_afectacion(id_tramite_fifonafe,id_afectacion,creado_por)
  VALUES(ff,af,u);

  failed:=FALSE;
  BEGIN
    UPDATE tramite_fifonafe SET no_oficio_fifonafe_a_dgaopr='LEGACY-NO'
    WHERE id_tramite_fifonafe=ff;
  EXCEPTION WHEN others THEN failed:=TRUE;
  END;
  IF NOT failed THEN RAISE EXCEPTION 'FIFONAFE permitio escritura legacy'; END IF;

  INSERT INTO tramite_fifonafe_evento(id_tramite_fifonafe,ordinal,id_tipo_evento,origen,destino,numero_oficio,fecha_oficio,creado_por)
  VALUES
    (ff,1,f1,'FIFONAFE','DGAOPR/Representacion','OF-1',DATE '2026-09-01',u),
    (ff,2,f2,'DGAOPR','Representacion','OF-2',DATE '2026-09-02',u),
    (ff,3,f3,'Representacion','DGAOPR','OF-3',DATE '2026-09-03',u),
    (ff,4,f4,'DGAOPR/Representacion','FIFONAFE','OF-4',DATE '2026-09-04',u);
  IF (SELECT no_oficio_respuesta_dgaopr_a_fifonafe FROM tramite_fifonafe WHERE id_tramite_fifonafe=ff)
     IS DISTINCT FROM 'OF-4' THEN
    RAISE EXCEPTION 'Eventos FIFONAFE no proyectaron resumen';
  END IF;

  UPDATE tramite_fifonafe SET estatus='completo' WHERE id_tramite_fifonafe=ff;
  SET CONSTRAINTS ALL IMMEDIATE;
  SET CONSTRAINTS ALL DEFERRED;

  failed:=FALSE;
  BEGIN
    UPDATE tramite_fifonafe_evento
    SET activo=FALSE,fecha_baja=now(),id_usuario_baja=u,motivo_baja='QA 038'
    WHERE id_tramite_fifonafe=ff AND id_tipo_evento=f4;
    SET CONSTRAINTS ALL IMMEDIATE;
  EXCEPTION WHEN others THEN
    failed:=TRUE;
    SET CONSTRAINTS ALL DEFERRED;
  END;
  IF NOT failed THEN RAISE EXCEPTION 'FIFONAFE completo acepto evento requerido faltante'; END IF;

  IF to_regclass('public.uq_tramite_ran_asamblea') IS NOT NULL
     OR to_regclass('public.uq_tramite_ran_convenio') IS NOT NULL
     OR to_regclass('public.uq_tramite_ran_orv') IS NOT NULL THEN
    RAISE EXCEPTION 'Persisten indices 1:1 de TramiteRAN';
  END IF;

  RAISE NOTICE 'CONTRATO 038 APROBADO';
END;
$contract$;

ROLLBACK;
