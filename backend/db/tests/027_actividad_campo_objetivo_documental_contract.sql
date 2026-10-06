\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = public, pg_catalog;
SELECT current_database();

DO $$
DECLARE
    v_definicion text;
    v_tipo text;
    v_constraint text;
    v_actor integer;
    v_pn integer;
    v_actividad integer;
    v_documento integer;
    v_requisito bigint;
    v_estado bigint;
BEGIN
    IF current_database() <> 'software_pa_test' THEN
        RAISE EXCEPTION 'Contrato 027 sólo permite software_pa_test';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE version = '026'
        AND nombre = 'historia_cambios_gis'
        AND checksum_sha256 = '6615a137655abbb2a6ea2620d7c8b5013f07d6fcdd81aae4270a4551904ea3fd'
    ) OR NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE version = '027'
        AND nombre = 'actividad_campo_objetivo_documental'
        AND checksum_sha256 = 'd5371660b3d0f6a257bcdffe453feb72984b225d24804991e6b4cf7c1ce68665'
    ) THEN
        RAISE EXCEPTION 'Contrato requiere 026 y 027 canónicas aplicadas';
    END IF;

    -- Ejecuta el CHECK real sin que los triggers de existencia oculten su resultado.
    SELECT pg_get_constraintdef(oid) INTO STRICT v_definicion
    FROM pg_constraint WHERE conrelid = 'documento_vinculo'::regclass
      AND conname = 'chk_documento_vinculo_tipo' AND contype = 'c' AND convalidated;
    EXECUTE 'CREATE TEMP TABLE contrato_027_vinculo (entidad_tipo varchar(50) NOT NULL, '
            || 'CONSTRAINT chk_documento_vinculo_tipo ' || v_definicion || ') ON COMMIT DROP';
    FOREACH v_tipo IN ARRAY ARRAY[
        'proyecto_nucleo','nucleo_agrario','orv','padron_historial','parcela',
        'parcela_titular','afectacion','unidad_agraria','unidad_agraria_titular',
        'afectacion_unidad_agraria','asamblea','asamblea_convocatoria',
        'convenio','convenio_compareciente','tramite_ran','tramite_ran_evento',
        'tramite_fifonafe','tramite_fifonafe_evento','tramite_fifonafe_interviniente',
        'indemnizacion','pago','expediente_requisito','actividad_campo'
    ] LOOP
        INSERT INTO contrato_027_vinculo VALUES (v_tipo);
    END LOOP;
    BEGIN
        INSERT INTO contrato_027_vinculo VALUES ('tipo_arbitrario_invalido');
        RAISE EXCEPTION 'CHECK documental aceptó un tipo inválido';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_constraint = CONSTRAINT_NAME;
        IF v_constraint <> 'chk_documento_vinculo_tipo' THEN RAISE; END IF;
    END;

    -- Los 20 tipos de requisitos de 026 siguen admitidos por su CHECK real.
    SELECT pg_get_constraintdef(oid) INTO STRICT v_definicion
    FROM pg_constraint WHERE conrelid = 'expediente_requisito'::regclass
      AND conname = 'chk_expediente_requisito_objetivo' AND contype = 'c' AND convalidated;
    EXECUTE 'CREATE TEMP TABLE contrato_027_requisito (entidad_tipo varchar(50) NOT NULL, '
            || 'CONSTRAINT chk_expediente_requisito_objetivo ' || v_definicion || ') ON COMMIT DROP';
    FOREACH v_tipo IN ARRAY ARRAY[
        'proyecto_nucleo','afectacion','parcela','parcela_titular','unidad_agraria',
        'unidad_agraria_titular','convenio','convenio_compareciente','tramite_ran',
        'tramite_ran_evento','tramite_fifonafe','tramite_fifonafe_evento',
        'tramite_fifonafe_interviniente','indemnizacion','pago','orv','padron_historial',
        'actividad_campo','asamblea','asamblea_convocatoria'
    ] LOOP
        INSERT INTO contrato_027_requisito VALUES (v_tipo);
    END LOOP;
    BEGIN
        INSERT INTO contrato_027_requisito VALUES ('tipo_arbitrario_invalido');
        RAISE EXCEPTION 'CHECK de requisito aceptó un tipo inválido';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_constraint = CONSTRAINT_NAME;
        IF v_constraint <> 'chk_expediente_requisito_objetivo' THEN RAISE; END IF;
    END;

    SELECT id_usuario INTO v_actor FROM usuario WHERE activo AND rol = 'admin'
    ORDER BY id_usuario LIMIT 1;
    SELECT pn.id_proyecto_nucleo INTO v_pn FROM proyecto_nucleo pn
    JOIN proyecto p USING (id_proyecto) WHERE pn.activo AND p.activo
    ORDER BY pn.id_proyecto_nucleo LIMIT 1;
    SELECT id_requisito INTO v_requisito FROM requisito_documental WHERE activo
    ORDER BY id_requisito LIMIT 1;
    SELECT id_catalogo_opcion INTO v_estado FROM catalogo_operativo
    WHERE activo AND tipo_catalogo = 'estado_requisito_documental'
    ORDER BY id_catalogo_opcion LIMIT 1;
    IF v_actor IS NULL OR v_pn IS NULL OR v_requisito IS NULL OR v_estado IS NULL THEN
        RAISE EXCEPTION 'Faltan fixtures de actor, ProyectoNucleo o catálogos de requisitos';
    END IF;
    PERFORM set_config('app.current_user_id', v_actor::text, true);

    INSERT INTO actividad_campo (id_proyecto_nucleo, tipo_actividad, responsable, creado_por)
    VALUES (v_pn, 'caminamiento', 'Contrato 027 ' || txid_current()::text, v_actor)
    RETURNING id_actividad INTO v_actividad;
    IF NOT fn_objetivo_controlado_existe('actividad_campo', v_actividad)
       OR fn_objetivo_controlado_existe('actividad_campo', -1)
       OR NOT fn_objetivo_requisito_en_pn('actividad_campo', v_actividad, v_pn)
       OR fn_objetivo_requisito_en_pn('actividad_campo', v_actividad, -1) THEN
        RAISE EXCEPTION 'Funciones de objetivo/requisito dejaron de reconocer la actividad y su pertenencia';
    END IF;

    INSERT INTO documento (tipo_documento, estado, creado_por)
    VALUES ('contrato_027', 'disponible', v_actor) RETURNING id_documento INTO v_documento;
    INSERT INTO documento_vinculo (id_documento, entidad_tipo, entidad_id, creado_por)
    VALUES (v_documento, 'actividad_campo', v_actividad, v_actor);
    INSERT INTO expediente_requisito (
        id_proyecto_nucleo, id_requisito, id_estado, id_documento,
        entidad_tipo, entidad_id, creado_por
    ) VALUES (v_pn, v_requisito, v_estado, v_documento, 'actividad_campo', v_actividad, v_actor);
    RAISE NOTICE '027 OK: 23 tipos documentales, rechazo inválidos, funciones y requisito de actividad sin regresión';
END $$;

ROLLBACK;
