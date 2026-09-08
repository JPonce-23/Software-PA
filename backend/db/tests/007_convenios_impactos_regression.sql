\set ON_ERROR_STOP on

-- Regresiones post-migración 007. Todos los registros creados en este archivo
-- son escenarios sintéticos QA y se revierten al final; no representan hechos
-- de los expedientes ni completan contradicciones de los Excel.
BEGIN;
SET search_path = public, pg_catalog;
SELECT set_config(
    'app.current_user_id',
    (SELECT min(id_usuario)::text FROM usuario WHERE activo),
    true
);

-- 1. Las seis vistas históricas conservan contrato y fuentes 006. La única
-- ampliación admitida es el typmod de las superficies físicas/declaradas.
DO $$
DECLARE v_faltantes text;
BEGIN
    SELECT string_agg(nombre, ', ' ORDER BY nombre) INTO v_faltantes
    FROM (VALUES
      ('vw_proyecto_nucleo_resumen'),('vw_hito_seguimiento_005'),
      ('vw_hito_seguimiento'),('vw_reporte_avance_periodo'),
      ('vw_dashboard_kpi'),('vw_reporte_snapshot_actual')
    ) x(nombre)
    WHERE to_regclass('public.'||nombre) IS NULL;
    IF v_faltantes IS NOT NULL THEN
        RAISE EXCEPTION '007 QA: vistas históricas faltantes: %',v_faltantes;
    END IF;
    IF EXISTS (
      SELECT 1 FROM (VALUES
        ('vw_hito_seguimiento_005'),('vw_hito_seguimiento'),
        ('vw_reporte_avance_periodo'),('vw_dashboard_kpi'),
        ('vw_reporte_snapshot_actual')
      ) x(nombre)
      WHERE pg_get_viewdef(('public.'||nombre)::regclass,true)
            ~ '(monto_(90|100|bdt)_impacto|superficie_impacto_ha|efecto_monto|efecto_superficie)'
    ) THEN
        RAISE EXCEPTION '007 QA: una vista histórica consume impactos 007';
    END IF;
    PERFORM count(*) FROM vw_proyecto_nucleo_resumen;
    PERFORM count(*) FROM vw_hito_seguimiento_005;
    PERFORM count(*) FROM vw_hito_seguimiento;
    PERFORM count(*) FROM vw_reporte_avance_periodo;
    PERFORM count(*) FROM vw_dashboard_kpi;
    PERFORM count(*) FROM vw_reporte_snapshot_actual;
END $$;

-- 2. Representación colectiva histórica: ORV vigente, ORV vencida y externos
-- con/sin Documento. Ser firmante nunca convierte a alguien en beneficiario.
DO $$
DECLARE
    v_user integer; v_pn integer; v_nucleo integer; v_af integer; v_convenio integer;
    v_calidad bigint; v_acred bigint; v_organo bigint; v_cargo bigint; v_cal_orv bigint;
    v_orv_vigente integer; v_orv_vencida integer;
    v_persona_vigente integer; v_persona_vencida integer;
    v_persona_externa integer; v_persona_sin_doc integer;
    v_cc_vigente bigint; v_cc_vencida bigint; v_cc_externa bigint; v_cc_sin_doc bigint;
    v_documento integer; v_error text;
BEGIN
    SELECT min(id_usuario) INTO v_user FROM usuario WHERE activo;
    SELECT pn.id_proyecto_nucleo,pn.id_nucleo INTO v_pn,v_nucleo
      FROM proyecto_nucleo pn
     WHERE pn.activo AND NOT EXISTS (
       SELECT 1 FROM orv o WHERE o.id_nucleo=pn.id_nucleo AND o.activo
     ) ORDER BY pn.id_proyecto_nucleo LIMIT 1;
    IF v_pn IS NULL THEN RAISE EXCEPTION '007 QA: no hay núcleo aislable para ORV sintética'; END IF;
    SELECT id_catalogo_opcion INTO v_calidad FROM catalogo_operativo
     WHERE tipo_catalogo='calidad_compareciente_convenio' AND codigo='representante' AND activo;
    SELECT id_catalogo_opcion INTO v_acred FROM catalogo_operativo
     WHERE tipo_catalogo='tipo_acreditacion_compareciente_colectivo' AND codigo='poder_representacion' AND activo;
    SELECT id_catalogo_opcion INTO v_organo FROM catalogo_operativo
     WHERE tipo_catalogo='organo_orv' AND codigo='comisariado' AND activo;
    SELECT id_catalogo_opcion INTO v_cargo FROM catalogo_operativo
     WHERE tipo_catalogo='cargo_orv' AND codigo='presidente' AND activo;
    SELECT id_catalogo_opcion INTO v_cal_orv FROM catalogo_operativo
     WHERE tipo_catalogo='calidad_integrante_orv' AND codigo='propietario' AND activo;

    INSERT INTO afectacion(id_proyecto_nucleo,tipo_afectacion,observaciones,creado_por)
    VALUES(v_pn,'colectivo','[SINTETICO QA 007] comparecencia colectiva',v_user)
    RETURNING id_afectacion INTO v_af;
    INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,
      fecha_firma,estado_antecedente,descripcion_instrumento,creado_por)
    VALUES(v_pn,'colectivo','convenio','cop_original','2025-06-15','no_aplica',
      '[SINTETICO QA 007] representación histórica',v_user)
    RETURNING id_convenio INTO v_convenio;
    INSERT INTO convenio_afectacion(id_convenio,id_afectacion,creado_por)
    VALUES(v_convenio,v_af,v_user);

    INSERT INTO persona(nombre,origen_registro,observaciones,creado_por)
      VALUES('[SINTETICO] ORV vigente','qa','QA 007',v_user) RETURNING id_persona INTO v_persona_vigente;
    INSERT INTO persona(nombre,origen_registro,observaciones,creado_por)
      VALUES('[SINTETICO] ORV vencida','qa','QA 007',v_user) RETURNING id_persona INTO v_persona_vencida;
    INSERT INTO persona(nombre,origen_registro,observaciones,creado_por)
      VALUES('[SINTETICO] representante externo documentado','qa','QA 007',v_user) RETURNING id_persona INTO v_persona_externa;
    INSERT INTO persona(nombre,origen_registro,observaciones,creado_por)
      VALUES('[SINTETICO] representante externo sin documento','qa','QA 007',v_user) RETURNING id_persona INTO v_persona_sin_doc;

    INSERT INTO orv(id_nucleo,numero_orv,inicio_vigencia,fin_vigencia,estatus_fuente,creado_por)
      VALUES(v_nucleo,'SINT-QA-007-VIGENTE','2024-01-01','2026-12-31','sintético QA',v_user)
      RETURNING id_orv INTO v_orv_vigente;
    INSERT INTO orv(id_nucleo,numero_orv,inicio_vigencia,fin_vigencia,estatus_fuente,creado_por)
      VALUES(v_nucleo,'SINT-QA-007-VENCIDA','2020-01-01','2021-12-31','sintético QA',v_user)
      RETURNING id_orv INTO v_orv_vencida;
    INSERT INTO orv_integrante(id_orv,id_persona,fecha_inicio,fecha_fin,id_organo,id_cargo,id_calidad,creado_por)
      VALUES(v_orv_vigente,v_persona_vigente,'2024-01-01','2026-12-31',v_organo,v_cargo,v_cal_orv,v_user);
    INSERT INTO orv_integrante(id_orv,id_persona,fecha_inicio,fecha_fin,id_organo,id_cargo,id_calidad,creado_por)
      VALUES(v_orv_vencida,v_persona_vencida,'2020-01-01','2021-12-31',v_organo,v_cargo,v_cal_orv,v_user);

    INSERT INTO convenio_compareciente(id_convenio,id_persona,id_tipo_calidad,
      nombre_en_instrumento,es_firmante,es_beneficiario_pago,requiere_revision,creado_por)
    VALUES(v_convenio,v_persona_vigente,v_calidad,'ORV vigente',true,false,false,v_user)
    RETURNING id_compareciente INTO v_cc_vigente;
    INSERT INTO convenio_compareciente(id_convenio,id_persona,id_tipo_calidad,
      nombre_en_instrumento,es_firmante,es_beneficiario_pago,requiere_revision,motivo_revision,creado_por)
    VALUES(v_convenio,v_persona_vencida,v_calidad,'ORV vencida',true,false,true,
      'ORV fuera de vigencia al acto [SINTETICO]',v_user)
    RETURNING id_compareciente INTO v_cc_vencida;
    INSERT INTO convenio_compareciente(id_convenio,id_persona,id_tipo_calidad,id_tipo_acreditacion,
      referencia_acreditacion,fecha_acreditacion,nombre_en_instrumento,es_firmante,
      es_beneficiario_pago,requiere_revision,motivo_revision,creado_por)
    VALUES(v_convenio,v_persona_externa,v_calidad,v_acred,'PODER-SINT-QA-007','2025-06-01',
      'Externo documentado',true,false,true,'Documento por vincular [SINTETICO]',v_user)
    RETURNING id_compareciente INTO v_cc_externa;
    INSERT INTO documento(tipo_documento,estado,titulo,fecha_documento,creado_por)
    VALUES('poder_representacion','disponible','[SINTETICO QA 007] Poder','2025-06-01',v_user)
    RETURNING id_documento INTO v_documento;
    INSERT INTO documento_vinculo(id_documento,entidad_tipo,entidad_id,creado_por)
    VALUES(v_documento,'convenio_compareciente',v_cc_externa,v_user);
    UPDATE convenio_compareciente SET requiere_revision=false,motivo_revision=NULL,
      actualizado_por=v_user WHERE id_compareciente=v_cc_externa;

    INSERT INTO convenio_compareciente(id_convenio,id_persona,id_tipo_calidad,id_tipo_acreditacion,
      referencia_acreditacion,fecha_acreditacion,nombre_en_instrumento,es_firmante,
      es_beneficiario_pago,requiere_revision,motivo_revision,creado_por)
    VALUES(v_convenio,v_persona_sin_doc,v_calidad,v_acred,'PODER-SIN-DOC-QA-007','2025-06-01',
      'Externo sin documento',true,false,true,'Sin Documento disponible [SINTETICO]',v_user)
    RETURNING id_compareciente INTO v_cc_sin_doc;

    BEGIN
      UPDATE convenio_compareciente SET requiere_revision=false,motivo_revision=NULL,
        actualizado_por=v_user WHERE id_compareciente=v_cc_vencida;
      RAISE EXCEPTION '007 QA: ORV vencida fue aceptada sin revisión';
    EXCEPTION WHEN raise_exception THEN
      GET STACKED DIAGNOSTICS v_error = MESSAGE_TEXT;
      IF v_error NOT LIKE '007: firmante colectivo requiere ORV vigente%' THEN RAISE; END IF;
    END;
    BEGIN
      UPDATE convenio_compareciente SET requiere_revision=false,motivo_revision=NULL,
        actualizado_por=v_user WHERE id_compareciente=v_cc_sin_doc;
      RAISE EXCEPTION '007 QA: externo sin Documento fue aceptado sin revisión';
    EXCEPTION WHEN raise_exception THEN
      GET STACKED DIAGNOSTICS v_error = MESSAGE_TEXT;
      IF v_error NOT LIKE '007: firmante colectivo requiere ORV vigente%' THEN RAISE; END IF;
    END;
    IF (SELECT count(*) FROM convenio_compareciente
        WHERE id_compareciente IN (v_cc_vigente,v_cc_vencida,v_cc_externa,v_cc_sin_doc)
          AND es_beneficiario_pago) <> 0 THEN
      RAISE EXCEPTION '007 QA: firmante fue convertido en beneficiario';
    END IF;
    IF NOT (SELECT NOT requiere_revision FROM convenio_compareciente WHERE id_compareciente=v_cc_externa) THEN
      RAISE EXCEPTION '007 QA: externo documentado no cerró revisión';
    END IF;
END $$;

-- 3. Cinco efectos, siete decimales, N:M, pendiente NULL y monto una vez por
-- instrumento. Superficie física, declarada e impacto permanecen separados.
DO $$
DECLARE
  v_user integer; v_pn integer; v_af1 integer; v_af2 integer; v_c integer;
  v_ca1 integer; v_ca2 integer; v_error text;
BEGIN
  SELECT min(id_usuario) INTO v_user FROM usuario WHERE activo;
  SELECT min(id_proyecto_nucleo) INTO v_pn FROM proyecto_nucleo WHERE activo;
  INSERT INTO afectacion(id_proyecto_nucleo,tipo_afectacion,superficie_afectada_ha,observaciones,creado_por)
    VALUES(v_pn,'colectivo',0.3000001,'[SINTETICO QA 007] N:M A',v_user) RETURNING id_afectacion INTO v_af1;
  INSERT INTO afectacion(id_proyecto_nucleo,tipo_afectacion,superficie_afectada_ha,observaciones,creado_por)
    VALUES(v_pn,'colectivo',0.4000002,'[SINTETICO QA 007] N:M B',v_user) RETURNING id_afectacion INTO v_af2;
  INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,
    monto_100,superficie_ha,efecto_monto,estado_antecedente,descripcion_instrumento,creado_por)
  VALUES(v_pn,'colectivo','convenio','cop_original',100.00,0.1668079,'pendiente','no_aplica',
    '[SINTETICO QA 007] impactos N:M',v_user) RETURNING id_convenio INTO v_c;
  INSERT INTO convenio_afectacion(id_convenio,id_afectacion,rol,creado_por)
    VALUES(v_c,v_af1,'principal',v_user) RETURNING id_convenio_afectacion INTO v_ca1;
  INSERT INTO convenio_afectacion(id_convenio,id_afectacion,rol,creado_por)
    VALUES(v_c,v_af2,'adicional',v_user) RETURNING id_convenio_afectacion INTO v_ca2;

  UPDATE convenio SET efecto_monto='sin_cambio',monto_100_impacto=0 WHERE id_convenio=v_c;
  UPDATE convenio SET efecto_monto='adicion',monto_100_impacto=10 WHERE id_convenio=v_c;
  UPDATE convenio SET efecto_monto='sustitucion',monto_100_impacto=-5 WHERE id_convenio=v_c;
  UPDATE convenio SET efecto_monto='correccion',monto_100_impacto=-1 WHERE id_convenio=v_c;
  UPDATE convenio SET efecto_monto='pendiente',monto_100_impacto=NULL WHERE id_convenio=v_c;
  BEGIN
    UPDATE convenio SET efecto_monto='pendiente',monto_100_impacto=0 WHERE id_convenio=v_c;
    RAISE EXCEPTION '007 QA: pendiente económico aceptó cero';
  EXCEPTION WHEN check_violation THEN NULL; END;
  BEGIN
    UPDATE convenio SET efecto_monto='adicion',monto_100_impacto=-1 WHERE id_convenio=v_c;
    RAISE EXCEPTION '007 QA: adición económica aceptó negativo';
  EXCEPTION WHEN check_violation THEN NULL; END;
  UPDATE convenio SET efecto_monto='correccion',monto_100_impacto=-5 WHERE id_convenio=v_c;

  UPDATE convenio_afectacion SET efecto_superficie='sin_cambio',superficie_impacto_ha=0 WHERE id_convenio_afectacion=v_ca1;
  UPDATE convenio_afectacion SET efecto_superficie='adicion',superficie_impacto_ha=0.1000001 WHERE id_convenio_afectacion=v_ca1;
  UPDATE convenio_afectacion SET efecto_superficie='sustitucion',superficie_impacto_ha=-0.1000001 WHERE id_convenio_afectacion=v_ca1;
  UPDATE convenio_afectacion SET efecto_superficie='correccion',superficie_impacto_ha=-0.0000001 WHERE id_convenio_afectacion=v_ca1;
  BEGIN
    UPDATE convenio_afectacion SET efecto_superficie='pendiente',superficie_impacto_ha=0 WHERE id_convenio_afectacion=v_ca1;
    RAISE EXCEPTION '007 QA: pendiente superficial aceptó cero';
  EXCEPTION WHEN check_violation THEN NULL; END;
  UPDATE convenio_afectacion SET efecto_superficie='adicion',superficie_impacto_ha=0.1000001 WHERE id_convenio_afectacion=v_ca1;
  -- v_ca2 permanece pendiente/NULL para comprobar cobertura incompleta.

  IF (SELECT superficie_ha FROM convenio WHERE id_convenio=v_c) <> 0.1668079::numeric
     OR (SELECT superficie_impacto_ha FROM convenio_afectacion WHERE id_convenio_afectacion=v_ca1) <> 0.1000001::numeric THEN
    RAISE EXCEPTION '007 QA: round-trip de siete decimales falló';
  END IF;
  IF (SELECT count(*) FROM vw_convenio_impacto WHERE id_convenio=v_c AND concepto='monto_100') <> 1
     OR (SELECT count(*) FROM vw_convenio_impacto WHERE id_convenio=v_c AND concepto='superficie') <> 2 THEN
    RAISE EXCEPTION '007 QA: monto multiplicado o relaciones N:M colapsadas';
  END IF;
  IF (SELECT count(*) FROM vw_convenio_impacto WHERE id_convenio=v_c AND pendiente) <> 1
     OR (SELECT count(*) FROM vw_convenio_impacto WHERE id_convenio=v_c AND pendiente AND valor_impacto IS NULL) <> 1 THEN
    RAISE EXCEPTION '007 QA: cobertura pendiente no conserva NULL';
  END IF;
  IF (SELECT sum(superficie_afectada_ha) FROM afectacion WHERE id_afectacion IN(v_af1,v_af2)) =
     (SELECT superficie_ha FROM convenio WHERE id_convenio=v_c) THEN
    RAISE EXCEPTION '007 QA: superficie física se equiparó a declarada';
  END IF;
  IF EXISTS (SELECT 1 FROM vw_convenio_impacto
             WHERE id_convenio=v_c AND (firma_acreditada OR fecha_efecto IS NOT NULL)) THEN
    RAISE EXCEPTION '007 QA: instrumento sin firma acreditada quedó periodizable';
  END IF;
END $$;

-- 4. Tratamientos conservadores aplicables a los casos auditados: P-201/P-15
-- sólo vinculan un padre real; Pueblo Nuevo puede quedar pendiente; San Pedrito
-- no obliga a crear instrumento; San Clemente/Barrancas no multiplican montos
-- por compartir relaciones. Esta sonda no carga hechos de esos expedientes.
DO $$
DECLARE
  v_user integer; v_pn integer; v_af integer; v_original integer;
  v_vinculado integer; v_referido integer; v_pendiente integer; v_error text;
BEGIN
  SELECT min(id_usuario) INTO v_user FROM usuario WHERE activo;
  SELECT min(id_proyecto_nucleo) INTO v_pn FROM proyecto_nucleo WHERE activo;
  INSERT INTO afectacion(id_proyecto_nucleo,tipo_afectacion,observaciones,creado_por)
    VALUES(v_pn,'colectivo','[SINTETICO QA 007] antecedentes',v_user) RETURNING id_afectacion INTO v_af;
  INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,
    estado_antecedente,descripcion_instrumento,creado_por)
    VALUES(v_pn,'colectivo','convenio','cop_original','no_aplica',
      '[SINTETICO QA] regla P-201/P-15 original',v_user) RETURNING id_convenio INTO v_original;
  INSERT INTO convenio_afectacion(id_convenio,id_afectacion,creado_por) VALUES(v_original,v_af,v_user);
  INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,
    id_convenio_padre,estado_antecedente,descripcion_instrumento,creado_por)
    VALUES(v_pn,'colectivo','convenio','modificatorio',v_original,'vinculado',
      '[SINTETICO QA] vínculo soportado',v_user) RETURNING id_convenio INTO v_vinculado;
  INSERT INTO convenio_afectacion(id_convenio,id_afectacion,creado_por) VALUES(v_vinculado,v_af,v_user);
  INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,
    estado_antecedente,descripcion_instrumento,creado_por)
    VALUES(v_pn,'colectivo','convenio','modificatorio','referido_sin_soporte',
      '[SINTETICO QA] antecedente referido, sin padre ficticio',v_user) RETURNING id_convenio INTO v_referido;
  INSERT INTO convenio_afectacion(id_convenio,id_afectacion,creado_por) VALUES(v_referido,v_af,v_user);
  INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,
    descripcion_instrumento,creado_por)
    VALUES(v_pn,'colectivo','convenio','modificatorio',
      '[SINTETICO QA] Pueblo Nuevo: pendiente documental',v_user) RETURNING id_convenio INTO v_pendiente;
  INSERT INTO convenio_afectacion(id_convenio,id_afectacion,creado_por) VALUES(v_pendiente,v_af,v_user);
  IF (SELECT estado_antecedente FROM convenio WHERE id_convenio=v_pendiente) <> 'pendiente_identificar'
     OR (SELECT id_convenio_padre FROM convenio WHERE id_convenio=v_pendiente) IS NOT NULL THEN
    RAISE EXCEPTION '007 QA: antecedente pendiente creó o exigió padre ficticio';
  END IF;
  BEGIN
    UPDATE convenio SET estado_antecedente='vinculado' WHERE id_convenio=v_pendiente;
    RAISE EXCEPTION '007 QA: vinculado sin padre fue aceptado';
  EXCEPTION WHEN raise_exception THEN
    GET STACKED DIAGNOSTICS v_error = MESSAGE_TEXT;
    IF v_error NOT LIKE '007: instrumento sin padre requiere antecedente%' THEN RAISE; END IF;
  END;
  BEGIN
    UPDATE convenio SET id_convenio_padre=v_vinculado,estado_antecedente='vinculado'
      WHERE id_convenio=v_original;
    RAISE EXCEPTION '007 QA: COP original con padre fue aceptada';
  EXCEPTION WHEN check_violation OR raise_exception THEN NULL; END;
END $$;

-- Fuerza todas las validaciones diferidas relevantes de los fixtures antes de
-- declarar éxito; se nombran expresamente y luego se restaura el modo original.
SET CONSTRAINTS ctr_convenio_requiere_afectacion,
  trg_convenio_individual_firmado,trg_linaje_unidad_convenio IMMEDIATE;
SET CONSTRAINTS ctr_convenio_requiere_afectacion,
  trg_convenio_individual_firmado,trg_linaje_unidad_convenio DEFERRED;

SELECT '007_convenios_impactos_regression: OK' AS resultado;
ROLLBACK;
