-- Structural and functional contract for SOFTWARE-PA canonical baseline v1.
\set ON_ERROR_STOP on

DO $$
DECLARE
    v_count integer;
    v_definition text;
    v_assembly integer;
    v_actor integer;
    v_celebrated bigint;
BEGIN
    SELECT count(*) INTO v_count FROM schema_migrations;
    IF v_count < 1 OR NOT EXISTS (
        SELECT 1 FROM schema_migrations
         WHERE version='001' AND nombre='baseline_v1'
           AND checksum_sha256 ~ '^[0-9a-f]{64}$'
    ) THEN
        RAISE EXCEPTION 'schema_migrations debe conservar baseline 001 con SHA-256';
    END IF;

    -- Final schemas may add tables. The complete baseline set must survive.
    IF EXISTS (SELECT 1 FROM (VALUES
            ('actividad_campo'),
            ('afectacion'),
            ('afectacion_unidad_agraria'),
            ('asamblea'),
            ('asamblea_convocatoria'),
            ('bitacora'),
            ('catalogo_alias_territorial'),
            ('catalogo_operativo'),
            ('catalogo_operativo_alias'),
            ('convenio'),
            ('convenio_afectacion'),
            ('convenio_compareciente'),
            ('documento'),
            ('documento_version'),
            ('documento_vinculo'),
            ('entidad_federativa'),
            ('estado_autenticacion_usuario'),
            ('evento_acceso'),
            ('expediente_requisito'),
            ('importacion_archivo'),
            ('importacion_feature'),
            ('importacion_tabular'),
            ('importacion_tabular_celda'),
            ('indemnizacion'),
            ('municipio'),
            ('nucleo_agrario'),
            ('orv'),
            ('orv_integrante'),
            ('padron_historial'),
            ('pago'),
            ('parcela'),
            ('parcela_titular'),
            ('perfil_mapeo_importacion'),
            ('persona'),
            ('proyecto'),
            ('proyecto_nucleo'),
            ('proyecto_nucleo_referencia'),
            ('proyecto_nucleo_responsable'),
            ('requisito_documental'),
            ('sesion_usuario'),
            ('tramite_fifonafe'),
            ('tramite_fifonafe_afectacion'),
            ('tramite_fifonafe_evento'),
            ('tramite_ran'),
            ('tramite_ran_evento'),
            ('trazabilidad_fuente'),
            ('trazo_proyecto'),
            ('unidad_agraria'),
            ('unidad_agraria_titular'),
            ('usuario'),
            ('usuario_proyecto'),
            ('schema_migrations')) required(table_name)
        WHERE NOT EXISTS (SELECT 1 FROM information_schema.tables t
          WHERE t.table_schema='public' AND t.table_type='BASE TABLE'
            AND t.table_name=required.table_name)) THEN
        RAISE EXCEPTION 'Faltan tablas obligatorias del baseline';
    END IF;
    IF EXISTS (SELECT 1 FROM (VALUES
        ('proyecto','id_proyecto'),('proyecto','activo'),
        ('proyecto_nucleo','id_proyecto_nucleo'),('proyecto_nucleo','id_proyecto'),
        ('proyecto_nucleo','id_nucleo'),('parcela','id_parcela'),
        ('afectacion','id_proyecto_nucleo'),('convenio','id_proyecto_nucleo'),
        ('tramite_ran_evento','id_tramite_ran'),('usuario','id_usuario')
      ) required(table_name,column_name)
      WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns c
        WHERE c.table_schema='public' AND c.table_name=required.table_name
          AND c.column_name=required.column_name)) THEN
        RAISE EXCEPTION 'Faltan columnas esenciales del baseline';
    END IF;
    IF to_regprocedure('public.fn_audit_log()') IS NULL THEN
        RAISE EXCEPTION 'Falta función de auditoría baseline';
    END IF;

    IF to_regclass('public.bien_afectado') IS NOT NULL THEN
        RAISE EXCEPTION 'bien_afectado no pertenece al baseline canónico';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM information_schema.columns c
          JOIN (VALUES
            ('nucleo_agrario','tipo_nucleo'),
            ('proyecto_nucleo','residencia'),
            ('proyecto_nucleo','responsable_nombre'),
            ('proyecto_nucleo','contacto'),
            ('orv_integrante','cargo'),
            ('afectacion','id_parcela'),
            ('afectacion','destino_superficie'),
            ('afectacion','no_parcela_solar'),
            ('asamblea','tipo_asamblea'),
            ('asamblea','contexto_proceso'),
            ('asamblea','fecha_expedicion_primera'),
            ('asamblea','fecha_programada_primera'),
            ('asamblea','fecha_expedicion_segunda'),
            ('asamblea','fecha_programada_segunda'),
            ('asamblea','fecha_realizada'),
            ('asamblea','fecha_programada_ingreso_ran'),
            ('asamblea','fecha_ingreso_ran'),
            ('asamblea','numero_solicitud_ran'),
            ('asamblea','calificacion_registral_ran'),
            ('asamblea','fecha_inscripcion_ran'),
            ('convenio','fecha_programada_ingreso_ran'),
            ('convenio','ingreso_ran_fecha'),
            ('convenio','numero_solicitud_ingreso'),
            ('convenio','calificacion_registral'),
            ('convenio','fecha_inscripcion_ran'),
            ('orv','acta_eleccion_inscrita_ran'),
            ('orv','fecha_inscripcion_acta_ran'),
            ('tramite_fifonafe','no_oficio_fifonafe_a_dgaopr'),
            ('tramite_fifonafe','fecha_oficio_fifonafe_a_dgaopr'),
            ('tramite_fifonafe','no_oficio_dgaopr_a_representacion'),
            ('tramite_fifonafe','fecha_oficio_dgaopr_a_representacion'),
            ('tramite_fifonafe','no_oficio_respuesta_representacion_a_dgaopr'),
            ('tramite_fifonafe','fecha_oficio_respuesta_representacion_a_dgaopr'),
            ('tramite_fifonafe','no_oficio_respuesta_dgaopr_a_fifonafe'),
            ('tramite_fifonafe','fecha_oficio_respuesta_dgaopr_a_fifonafe'),
            ('expediente_requisito','id_afectacion')
          ) removed(table_name,column_name)
            USING(table_name,column_name)
         WHERE c.table_schema='public'
    ) THEN
        RAISE EXCEPTION 'Persisten columnas legacy retiradas';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema='public' AND table_name='tramite_ran'
           AND column_name='id_proyecto_nucleo'
    ) OR NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema='public' AND table_name='tramite_ran'
           AND column_name='id_nucleo'
    ) OR NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema='public' AND table_name='orv'
           AND column_name='id_estado_registral'
    ) THEN
        RAISE EXCEPTION 'Faltan columnas canónicas obligatorias de RAN/ORV';
    END IF;

    SELECT pg_get_constraintdef(oid) INTO v_definition
      FROM pg_constraint
     WHERE conrelid='tramite_ran'::regclass
       AND conname='chk_tramite_ran_contexto';
    IF v_definition IS NULL
       OR position('id_proyecto_nucleo' in v_definition)=0
       OR position('id_nucleo' in v_definition)=0
       OR position('id_orv' in v_definition)=0 THEN
        RAISE EXCEPTION 'No existe la coherencia tipada del contexto RAN';
    END IF;

    SELECT count(*) INTO v_count FROM information_schema.views
     WHERE table_schema='public' AND table_name IN (
        'vw_proyecto_nucleo_resumen','vw_dashboard_kpi',
        'vw_orv_estado','vw_convenio_tipo_cop_operativo'
     );
    IF v_count <> 4 THEN
        RAISE EXCEPTION 'Faltan vistas canónicas';
    END IF;

    SELECT pg_get_viewdef('vw_proyecto_nucleo_resumen'::regclass,true)
      INTO v_definition;
    IF position('proyecto_nucleo_responsable' in v_definition)=0
       OR position('proyecto_nucleo_referencia' in v_definition)=0
       OR position('catalogo_operativo' in v_definition)=0 THEN
        RAISE EXCEPTION 'vw_proyecto_nucleo_resumen no usa fuentes canónicas';
    END IF;

    IF to_regclass('public.vw_reporte_avance_periodo') IS NULL THEN
        SELECT pg_get_viewdef('vw_dashboard_kpi'::regclass,true) INTO v_definition;
        IF position('asamblea_convocatoria' in v_definition)=0
           OR position('tramite_ran_evento' in v_definition)=0
           OR position('tramite_fifonafe_evento' in v_definition)=0
           OR position('afectacion_unidad_agraria' in v_definition)=0 THEN
            RAISE EXCEPTION 'vw_dashboard_kpi no usa todas las fuentes canónicas';
        END IF;
    ELSE
        -- Later migrations place canonical sources behind intermediate views.
        -- Validate actual transitive dependencies instead of SQL text in one layer.
        WITH RECURSIVE sources(oid) AS (
          SELECT 'public.vw_reporte_avance_periodo'::regclass::oid
          UNION
          SELECT d.refobjid FROM sources s
          JOIN pg_rewrite rw ON rw.ev_class=s.oid
          JOIN pg_depend d ON d.classid='pg_rewrite'::regclass AND d.objid=rw.oid
            AND d.refclassid='pg_class'::regclass AND d.refobjid<>s.oid
        ) SELECT count(DISTINCT c.relname) INTO v_count
          FROM sources s JOIN pg_class c ON c.oid=s.oid
          WHERE c.relname IN ('asamblea_convocatoria','tramite_ran_evento',
                             'tramite_fifonafe_evento','afectacion_unidad_agraria');
        IF v_count<>4 THEN
          RAISE EXCEPTION 'Reporting no conserva todas las fuentes canónicas baseline';
        END IF;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_trigger t
        JOIN pg_class c ON c.oid=t.tgrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE NOT t.tgisinternal AND n.nspname='public'
          AND (t.tgname ILIKE '%legacy%' OR pg_get_triggerdef(t.oid) ILIKE '%bien_afectado%')
    ) THEN
        RAISE EXCEPTION 'Persisten triggers legacy';
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
         WHERE n.nspname='public'
           AND p.prokind IN ('f','p')
           AND (p.proname ILIKE '%legacy%' OR pg_get_functiondef(p.oid) ILIKE '%bien_afectado%')
    ) THEN
        RAISE EXCEPTION 'Persisten funciones exclusivamente legacy';
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_indexes
         WHERE schemaname='public'
           AND (indexname ILIKE '%legacy%' OR indexdef ILIKE '%bien_afectado%')
    ) THEN
        RAISE EXCEPTION 'Persisten índices legacy';
    END IF;

    -- The seed deliberately keeps administrative and per-unit totals different.
    IF NOT EXISTS (
        SELECT 1 FROM afectacion a
        JOIN afectacion_unidad_agraria aua USING(id_afectacion)
        WHERE a.activo AND aua.activo
          AND a.superficie_afectada_ha IS DISTINCT FROM aua.superficie_afectada_ha
    ) THEN
        RAISE EXCEPTION 'No se comprobó la independencia de superficies';
    END IF;

    -- A second active celebrated convocation for one assembly must be rejected.
    SELECT a.id_asamblea,a.creado_por INTO v_assembly,v_actor
      FROM asamblea a JOIN asamblea_convocatoria ac USING(id_asamblea)
      JOIN catalogo_operativo co ON co.id_catalogo_opcion=ac.id_resultado
     WHERE a.activo AND ac.activo AND co.tipo_catalogo='resultado_convocatoria'
       AND co.codigo='celebrada' ORDER BY a.id_asamblea LIMIT 1;
    SELECT id_catalogo_opcion INTO v_celebrated FROM catalogo_operativo
     WHERE tipo_catalogo='resultado_convocatoria' AND codigo='celebrada' AND activo;
    BEGIN
        INSERT INTO asamblea_convocatoria(
            id_asamblea,ordinal,fecha_programada,fecha_realizacion,id_resultado,creado_por
        ) VALUES(v_assembly,999,CURRENT_DATE,CURRENT_DATE,v_celebrated,v_actor);
        RAISE EXCEPTION 'Se aceptó una segunda convocatoria celebrada';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM='Se aceptó una segunda convocatoria celebrada' THEN
            RAISE;
        END IF;
    END;

    PERFORM * FROM vw_proyecto_nucleo_resumen;
    PERFORM * FROM vw_dashboard_kpi;
    PERFORM * FROM vw_orv_estado;
    PERFORM * FROM vw_convenio_tipo_cop_operativo;
END;
$$;

SELECT 'CONTRATO BASELINE V1 APROBADO' AS resultado;
