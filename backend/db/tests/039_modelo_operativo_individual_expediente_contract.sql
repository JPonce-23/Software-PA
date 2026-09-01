-- Contrato transaccional posterior a 039. Ejecutar sólo en una BD *_test.
BEGIN;

DO $contract$
DECLARE
    v_usuario integer;
    v_municipio integer;
    v_proyecto bigint;
    v_proyecto2 bigint;
    v_pn bigint;
    v_pn2 bigint;
    v_nuc bigint;
    v_nuc2 bigint;
    v_persona bigint;
    v_persona2 bigint;
    v_parcela bigint;
    v_parcela2 bigint;
    v_titular bigint;
    v_titular2 bigint;
    v_unidad bigint;
    v_unidad2 bigint;
    v_afect bigint;
    v_afect2 bigint;
    v_afect3 bigint;
    v_afect_colectiva bigint;
    v_colectiva bigint;
    v_convenio bigint;
    v_convenio2 bigint;
    v_convenio_hijo bigint;
    v_tramite bigint;
    v_req bigint;
    v_estado bigint;
    v_calidad bigint;
    v_acreditacion bigint;
    v_tipo_tierra bigint;
    v_tipo_titularidad bigint;
    v_tipo_tenencia bigint;
    v_msg text;
    v_tipo text;
BEGIN
    -- Prerrequisitos estructurales.
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '038') THEN RAISE EXCEPTION '039: falta 038'; END IF;
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '039') THEN RAISE EXCEPTION '039: falta 039'; END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='parcela' AND column_name='no_parcela') THEN RAISE EXCEPTION '039: falta parcela.no_parcela'; END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='parcela' AND column_name='no_parcela_ppt') THEN RAISE EXCEPTION '039: no_parcela_ppt persiste'; END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='actividad_campo' AND column_name='id_afectacion' AND is_nullable='NO') THEN RAISE EXCEPTION '039: actividad id_afectacion no es nullable'; END IF;
    IF to_regclass('public.convenio_compareciente') IS NULL THEN RAISE EXCEPTION '039: falta convenio_compareciente'; END IF;
    IF to_regclass('public.tramite_ran_individual') IS NOT NULL THEN RAISE EXCEPTION '039: existe tramite_ran_individual'; END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tramite_ran' AND column_name='id_convenio') THEN RAISE EXCEPTION '039: RAN no referencia convenio'; END IF;
    IF to_regclass('public.tramite_fifonafe') IS NULL OR to_regclass('public.tramite_fifonafe_afectacion') IS NULL OR to_regclass('public.tramite_fifonafe_evento') IS NULL THEN RAISE EXCEPTION '039: faltan estructuras FIFONAFE'; END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname='fn_039_validar_convenio_compareciente_unidad') THEN RAISE EXCEPTION '039: falta función compareciente'; END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_039_compareciente_unidad' AND tgrelid='public.convenio_compareciente'::regclass AND tgconstraint <> 0 AND tgdeferrable AND tginitdeferred) THEN RAISE EXCEPTION '039: trigger compareciente no es deferred'; END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='expediente_requisito' AND column_name='entidad_tipo') OR NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='expediente_requisito' AND column_name='entidad_id') THEN RAISE EXCEPTION '039: expediente sin objetivo'; END IF;

    -- Infraestructura heredada permitida: usuario, municipio y catálogos.
    SELECT id_usuario INTO v_usuario FROM usuario WHERE activo ORDER BY id_usuario LIMIT 1;
    SELECT id_municipio INTO v_municipio FROM municipio ORDER BY id_municipio LIMIT 1;
    SELECT id_catalogo_opcion INTO v_tipo_tierra FROM catalogo_operativo WHERE tipo_catalogo='tipo_tierra' AND codigo='parcelada' AND activo;
    SELECT id_catalogo_opcion INTO v_tipo_titularidad FROM catalogo_operativo WHERE tipo_catalogo='tipo_titularidad_unidad' AND codigo='persona' AND activo;
    SELECT id_catalogo_opcion INTO v_tipo_tenencia FROM catalogo_operativo WHERE tipo_catalogo='tipo_tenencia' AND codigo='ejido' AND activo;
    IF v_usuario IS NULL OR v_municipio IS NULL OR v_tipo_tierra IS NULL OR v_tipo_titularidad IS NULL OR v_tipo_tenencia IS NULL THEN RAISE EXCEPTION '039 contract: infraestructura insuficiente'; END IF;
    PERFORM set_config('app.current_user_id', v_usuario::text, true);
    PERFORM set_config('app.audit_reason', 'Contrato QA migracion 039', true);
    -- Fixture operativo autocontenido: P1/P2, N1/N2, PN1/PN2 y dos parcelas del mismo N1.
    INSERT INTO proyecto(clave_proyecto,nombre_proyecto,creado_por) VALUES('QA039CPA','QA039-CONTRACT-P1',v_usuario) RETURNING id_proyecto INTO v_proyecto;
    INSERT INTO proyecto(clave_proyecto,nombre_proyecto,creado_por) VALUES('QA039CPB','QA039-CONTRACT-P2',v_usuario) RETURNING id_proyecto INTO v_proyecto2;
    INSERT INTO nucleo_agrario(id_municipio,nombre_nucleo,tipo_nucleo,id_tipo_tenencia,fuente_datos,creado_por) VALUES(v_municipio,'QA039-N1','ejido',v_tipo_tenencia,'contrato-039',v_usuario) RETURNING id_nucleo INTO v_nuc;
    INSERT INTO nucleo_agrario(id_municipio,nombre_nucleo,tipo_nucleo,id_tipo_tenencia,fuente_datos,creado_por) VALUES(v_municipio,'QA039-N2','ejido',v_tipo_tenencia,'contrato-039',v_usuario) RETURNING id_nucleo INTO v_nuc2;
    INSERT INTO proyecto_nucleo(id_proyecto,id_nucleo,creado_por) VALUES(v_proyecto,v_nuc,v_usuario) RETURNING id_proyecto_nucleo INTO v_pn;
    INSERT INTO proyecto_nucleo(id_proyecto,id_nucleo,creado_por) VALUES(v_proyecto2,v_nuc2,v_usuario) RETURNING id_proyecto_nucleo INTO v_pn2;
    INSERT INTO persona(nombre,apellido_paterno,origen_registro,creado_por) VALUES('QA039 Persona','Uno','qa',v_usuario) RETURNING id_persona INTO v_persona;
    INSERT INTO persona(nombre,apellido_paterno,origen_registro,creado_por) VALUES('QA039 Persona','Dos','qa',v_usuario) RETURNING id_persona INTO v_persona2;
    INSERT INTO parcela(id_nucleo,tipo_parcela,no_parcela,creado_por) VALUES(v_nuc,'individual','QA-039-PARCELA-1',v_usuario) RETURNING id_parcela INTO v_parcela;
    INSERT INTO parcela(id_nucleo,tipo_parcela,no_parcela,creado_por) VALUES(v_nuc,'individual','QA-039-PARCELA-2',v_usuario) RETURNING id_parcela INTO v_parcela2;
    INSERT INTO parcela_titular(id_parcela,id_persona,tipo_derecho,porcentaje_participacion,creado_por) VALUES(v_parcela,v_persona,'titular',100,v_usuario) RETURNING id_parcela_titular INTO v_titular;
    INSERT INTO parcela_titular(id_parcela,id_persona,tipo_derecho,porcentaje_participacion,creado_por) VALUES(v_parcela2,v_persona2,'titular',100,v_usuario) RETURNING id_parcela_titular INTO v_titular2;
    INSERT INTO unidad_agraria(id_nucleo,id_tipo_tierra,id_tipo_titularidad,id_parcela,referencia_alfanumerica,creado_por) VALUES(v_nuc,v_tipo_tierra,v_tipo_titularidad,v_parcela,'QA039-U1',v_usuario) RETURNING id_unidad_agraria INTO v_unidad;
    INSERT INTO unidad_agraria(id_nucleo,id_tipo_tierra,id_tipo_titularidad,id_parcela,referencia_alfanumerica,creado_por) VALUES(v_nuc,v_tipo_tierra,v_tipo_titularidad,v_parcela2,'QA039-U2',v_usuario) RETURNING id_unidad_agraria INTO v_unidad2;
    INSERT INTO unidad_agraria_titular(id_unidad_agraria,id_parcela_titular,porcentaje_participacion,es_principal,creado_por) VALUES(v_unidad,v_titular,100,true,v_usuario);
    INSERT INTO unidad_agraria_titular(id_unidad_agraria,id_parcela_titular,porcentaje_participacion,es_principal,creado_por) VALUES(v_unidad2,v_titular2,100,true,v_usuario);
    INSERT INTO afectacion(id_proyecto_nucleo,id_parcela,tipo_afectacion,creado_por) VALUES(v_pn,v_parcela,'individual',v_usuario) RETURNING id_afectacion INTO v_afect;
    INSERT INTO afectacion(id_proyecto_nucleo,id_parcela,tipo_afectacion,creado_por) VALUES(v_pn,v_parcela2,'individual',v_usuario) RETURNING id_afectacion INTO v_afect2;
    INSERT INTO afectacion(id_proyecto_nucleo,tipo_afectacion,creado_por) VALUES(v_pn,'colectivo',v_usuario) RETURNING id_afectacion INTO v_afect_colectiva;
    INSERT INTO afectacion(id_proyecto_nucleo,id_parcela,tipo_afectacion,creado_por) VALUES(v_pn2,NULL,'colectivo',v_usuario);
    INSERT INTO afectacion_unidad_agraria(id_afectacion,id_unidad_agraria,creado_por) VALUES(v_afect,v_unidad,v_usuario);
    INSERT INTO afectacion_unidad_agraria(id_afectacion,id_unidad_agraria,creado_por) VALUES(v_afect2,v_unidad2,v_usuario);
    INSERT INTO afectacion(id_proyecto_nucleo,id_parcela,tipo_afectacion,creado_por) VALUES(v_pn,v_parcela,'individual',v_usuario) RETURNING id_afectacion INTO v_afect3;
    INSERT INTO afectacion_unidad_agraria(id_afectacion,id_unidad_agraria,creado_por) VALUES(v_afect3,v_unidad,v_usuario);
    SELECT id_catalogo_opcion INTO v_calidad FROM catalogo_operativo WHERE tipo_catalogo='calidad_compareciente_convenio' AND activo ORDER BY orden,id_catalogo_opcion LIMIT 1;
    SELECT id_catalogo_opcion INTO v_acreditacion FROM catalogo_operativo WHERE tipo_catalogo='tipo_acreditacion_derecho_individual' AND activo ORDER BY orden,id_catalogo_opcion LIMIT 1;
    SELECT id_catalogo_opcion INTO v_estado FROM catalogo_operativo WHERE tipo_catalogo='estado_requisito_documental' AND activo ORDER BY orden,id_catalogo_opcion LIMIT 1;

    -- POS-01: actividad general; POS-02: actividad específica.
    INSERT INTO actividad_campo(id_proyecto_nucleo,id_afectacion,tipo_actividad,contexto_actividad,creado_por) VALUES (v_pn,NULL,'sensibilizacion','general',v_usuario);
    INSERT INTO actividad_campo(id_proyecto_nucleo,id_afectacion,tipo_actividad,contexto_actividad,creado_por) VALUES (v_pn,v_afect,'caminamiento','general',v_usuario);
    -- POS-03: la identidad de una unidad se reutiliza en más de una afectación.
    IF v_unidad2 IS NOT NULL AND v_afect2 IS NOT NULL AND (SELECT count(*) FROM afectacion_unidad_agraria WHERE id_unidad_agraria=v_unidad AND activo) < 1 THEN
        RAISE EXCEPTION '039: unidad sin afectación';
    END IF;
    -- SQL-NEG-B: una afectación de otro PN no puede cruzarse.
    IF v_pn2 IS NOT NULL THEN
      BEGIN INSERT INTO actividad_campo(id_proyecto_nucleo,id_afectacion,tipo_actividad,creado_por) VALUES (v_pn2,v_afect,'caminamiento',v_usuario); RAISE EXCEPTION 'SQL-NEG-B aceptado'; EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS v_msg=MESSAGE_TEXT; IF v_msg='SQL-NEG-B aceptado' OR v_msg NOT LIKE '039:%' THEN RAISE; END IF; END;
    END IF;

    -- SQL-NEG-A: unicidad normalizada por núcleo (se usa la expresión real del índice).
    IF to_regclass('public.uq_039_parcela_numero_normalizado') IS NULL THEN RAISE EXCEPTION '039: falta índice normalizado'; END IF;
    BEGIN INSERT INTO parcela(id_nucleo,tipo_parcela,no_parcela,creado_por) VALUES(v_nuc,'individual','QA-039-15',v_usuario); INSERT INTO parcela(id_nucleo,tipo_parcela,no_parcela,creado_por) VALUES(v_nuc,'individual','  qa-039-15  ',v_usuario); RAISE EXCEPTION 'SQL-NEG-A aceptado'; EXCEPTION WHEN unique_violation THEN NULL; END;

    -- SQL-NEG-C/D/E: linaje individual exige padre.
    FOREACH v_tipo IN ARRAY ARRAY['modificatorio','ampliacion','ampliacion_remanente'] LOOP
      BEGIN INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,consecutivo,creado_por) VALUES(v_pn,'individual','convenio',v_tipo,9000,v_usuario); RAISE EXCEPTION 'SQL-NEG lineage aceptado'; EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS v_msg=MESSAGE_TEXT; IF v_msg='SQL-NEG lineage aceptado' OR v_msg NOT LIKE '039:%' THEN RAISE; END IF; END;
    END LOOP;

    -- POS-04: COP original sin padre; POS-05: ampliación con padre y unidad compartida;
    -- POS-06: ampliacion_remanente con padre válido.
    INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,consecutivo,creado_por) VALUES(v_pn,'individual','convenio','cop_original',9001,v_usuario) RETURNING id_convenio INTO v_convenio;
    INSERT INTO convenio_afectacion(id_convenio,id_afectacion,creado_por) VALUES(v_convenio,v_afect,v_usuario);
    -- RAN reutilizado: el objetivo es el Convenio (no existe RAN individual).
    INSERT INTO tramite_ran(id_proyecto_nucleo,id_convenio,referencia_expediente,creado_por) VALUES(v_pn,v_convenio,'QA-039-RAN',v_usuario) RETURNING id_tramite_ran INTO v_tramite;
    INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,id_convenio_padre,consecutivo,creado_por) VALUES(v_pn,'individual','convenio','ampliacion',v_convenio,9002,v_usuario) RETURNING id_convenio INTO v_convenio2;
    INSERT INTO convenio_afectacion(id_convenio,id_afectacion,creado_por) VALUES(v_convenio2,v_afect,v_usuario);
    INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,id_convenio_padre,consecutivo,creado_por)
    VALUES(v_pn,'individual','convenio','ampliacion_remanente',v_convenio,9003,v_usuario)
    RETURNING id_convenio INTO v_convenio_hijo;
    INSERT INTO convenio_afectacion(id_convenio,id_afectacion,creado_por)
    VALUES(v_convenio_hijo,v_afect,v_usuario);

    -- SQL-NEG-F/G/H: padres inválidos.
    IF v_pn2 IS NOT NULL THEN
      BEGIN INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,id_convenio_padre,consecutivo,creado_por) VALUES(v_pn2,'individual','convenio','ampliacion',v_convenio,9004,v_usuario); RAISE EXCEPTION 'SQL-NEG-F aceptado'; EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS v_msg=MESSAGE_TEXT; IF v_msg='SQL-NEG-F aceptado' OR v_msg NOT LIKE '039:%' THEN RAISE; END IF; END;
    END IF;
    INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,consecutivo,creado_por) VALUES(v_pn,'colectivo','convenio','cop_original',9005,v_usuario) RETURNING id_convenio INTO v_colectiva;
    INSERT INTO convenio_afectacion(id_convenio,id_afectacion,creado_por) VALUES(v_colectiva,v_afect_colectiva,v_usuario);
    BEGIN INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,id_convenio_padre,consecutivo,creado_por) VALUES(v_pn,'individual','convenio','ampliacion',v_colectiva,9006,v_usuario); RAISE EXCEPTION 'SQL-NEG-G aceptado'; EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS v_msg=MESSAGE_TEXT; IF v_msg='SQL-NEG-G aceptado' OR v_msg NOT LIKE '039:%' THEN RAISE; END IF; END;
    IF v_unidad2 IS NOT NULL THEN
      INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,consecutivo,creado_por) VALUES(v_pn,'individual','convenio','cop_original',9007,v_usuario) RETURNING id_convenio INTO v_convenio2;
      INSERT INTO convenio_afectacion(id_convenio,id_afectacion,creado_por) VALUES(v_convenio2,v_afect2,v_usuario);
      BEGIN
        INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,id_convenio_padre,consecutivo,creado_por)
        VALUES(v_pn,'individual','convenio','ampliacion',v_convenio2,9008,v_usuario)
        RETURNING id_convenio INTO v_convenio_hijo;
        INSERT INTO convenio_afectacion(id_convenio,id_afectacion,creado_por)
        VALUES(v_convenio_hijo,v_afect,v_usuario);
        SET CONSTRAINTS ALL IMMEDIATE;
        RAISE EXCEPTION 'SQL-NEG-H aceptado';
      EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_msg=MESSAGE_TEXT;
        IF v_msg='SQL-NEG-H aceptado' OR v_msg NOT LIKE '039:%' THEN RAISE; END IF;
      END;
    END IF;

    -- POS-07 y SQL-NEG-K: compareciente coherente/incoherente por parcela afectada.
    IF v_titular IS NOT NULL AND v_persona IS NOT NULL THEN
      INSERT INTO convenio_compareciente(id_convenio,id_persona,id_parcela_titular,id_tipo_calidad,id_tipo_acreditacion,referencia_acreditacion,nombre_en_instrumento,es_firmante,creado_por) VALUES(v_convenio,v_persona,v_titular,v_calidad,v_acreditacion,'QA-039-A','QA PERSONA A',true,v_usuario);
      IF v_titular2 IS NOT NULL THEN
        BEGIN INSERT INTO convenio_compareciente(id_convenio,id_persona,id_parcela_titular,id_tipo_calidad,id_tipo_acreditacion,referencia_acreditacion,nombre_en_instrumento,es_firmante,creado_por) VALUES(v_convenio,v_persona2,v_titular2,v_calidad,v_acreditacion,'QA-039-B','QA PERSONA B',true,v_usuario); SET CONSTRAINTS ALL IMMEDIATE; RAISE EXCEPTION 'SQL-NEG-K aceptado'; EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS v_msg=MESSAGE_TEXT; IF v_msg='SQL-NEG-K aceptado' OR v_msg NOT LIKE '039:%' THEN RAISE; END IF; END;
      END IF;
    END IF;

    -- SQL-NEG-I/J: firmado incompleto, evaluado por triggers deferred.
    BEGIN INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,fecha_firma,consecutivo,creado_por) VALUES(v_pn,'individual','convenio','cop_original',CURRENT_DATE,9009,v_usuario) RETURNING id_convenio INTO v_convenio2; SET CONSTRAINTS ALL IMMEDIATE; RAISE EXCEPTION 'SQL-NEG-I aceptado'; EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS v_msg=MESSAGE_TEXT; IF v_msg='SQL-NEG-I aceptado' OR (v_msg NOT LIKE '039:%' AND v_msg <> 'Un convenio activo requiere al menos una afectación activa asociada') THEN RAISE; END IF; END;
    BEGIN INSERT INTO convenio(id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,fecha_firma,consecutivo,creado_por) VALUES(v_pn,'individual','convenio','cop_original',CURRENT_DATE,9010,v_usuario) RETURNING id_convenio INTO v_convenio2; INSERT INTO convenio_afectacion(id_convenio,id_afectacion,creado_por) VALUES(v_convenio2,v_afect,v_usuario); SET CONSTRAINTS ALL IMMEDIATE; RAISE EXCEPTION 'SQL-NEG-J aceptado'; EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS v_msg=MESSAGE_TEXT; IF v_msg='SQL-NEG-J aceptado' OR v_msg NOT LIKE '039:%' THEN RAISE; END IF; END;

    -- SQL-NEG-L/M: DELETE físico protegido por baja lógica.
    IF v_titular IS NOT NULL AND v_persona IS NOT NULL THEN
      BEGIN DELETE FROM convenio_compareciente WHERE id_convenio=v_convenio; RAISE EXCEPTION 'SQL-NEG-L aceptado'; EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS v_msg=MESSAGE_TEXT; IF v_msg='SQL-NEG-L aceptado' THEN RAISE; END IF; END;
      IF NOT EXISTS (SELECT 1 FROM convenio_compareciente WHERE id_convenio=v_convenio) THEN RAISE EXCEPTION '039: DELETE compareciente eliminó fila'; END IF;
    END IF;
    BEGIN DELETE FROM convenio WHERE id_convenio=v_colectiva; RAISE EXCEPTION 'SQL-NEG-M aceptado'; EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS v_msg=MESSAGE_TEXT; IF v_msg='SQL-NEG-M aceptado' THEN RAISE; END IF; END;

    -- Expediente, RAN y objetivos permitidos (cuando existen catálogos/columnas).
    IF to_regclass('public.requisito_documental') IS NOT NULL AND to_regclass('public.expediente_requisito') IS NOT NULL THEN
      SELECT id_requisito INTO v_req FROM requisito_documental ORDER BY id_requisito LIMIT 1;
      IF v_req IS NOT NULL AND v_estado IS NOT NULL THEN
        INSERT INTO expediente_requisito(id_proyecto_nucleo,id_requisito,id_estado,entidad_tipo,entidad_id,creado_por) VALUES(v_pn,v_req,v_estado,'parcela',v_parcela,v_usuario);
        INSERT INTO expediente_requisito(id_proyecto_nucleo,id_requisito,id_estado,entidad_tipo,entidad_id,creado_por) VALUES(v_pn,v_req,v_estado,'convenio',v_convenio,v_usuario);
        INSERT INTO expediente_requisito(id_proyecto_nucleo,id_requisito,id_estado,entidad_tipo,entidad_id,creado_por) VALUES(v_pn,v_req,v_estado,'tramite_ran',v_tramite,v_usuario);
        BEGIN INSERT INTO expediente_requisito(id_proyecto_nucleo,id_requisito,id_estado,entidad_tipo,entidad_id,creado_por) VALUES(v_pn,v_req,v_estado,'qa-arbitrario',v_convenio,v_usuario); RAISE EXCEPTION '039: entidad_tipo arbitrario aceptado'; EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS v_msg=MESSAGE_TEXT; IF v_msg='039: entidad_tipo arbitrario aceptado' OR v_msg NOT LIKE '039:%' THEN RAISE; END IF; END;
      END IF;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='public.parcela'::regclass AND attname='no_parcela' AND NOT attisdropped) THEN RAISE EXCEPTION '039: no_parcela ausente'; END IF;
    -- SQL-NEG-N: privilegios runtime no destructivos.
    IF has_table_privilege('software_pa_app','convenio_compareciente','DELETE') OR has_table_privilege('software_pa_app','convenio_compareciente','TRUNCATE') OR has_schema_privilege('software_pa_app','public','CREATE') THEN RAISE EXCEPTION 'SQL-NEG-N privilegios peligrosos'; END IF;
END;
$contract$;

ROLLBACK;
