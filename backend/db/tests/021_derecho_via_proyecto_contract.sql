\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_actor integer;
    v_proyecto integer;
    v_primero integer;
    v_segundo integer;
    v_geom text := 'MULTIPOLYGON(((0 0,0 1,1 1,1 0,0 0)))';
    v_rechazo boolean;
BEGIN
 IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='020' AND nombre='auditoria_heartbeat_sesion' AND checksum_sha256='cfa4dadb2e8b5bb9b8cddddf617c34132380ad49a660de9037de43850263f4c8') THEN RAISE EXCEPTION 'Dependencia canónica 020 incompatible'; END IF;
    IF current_database() <> 'software_pa_test' THEN
        RAISE EXCEPTION '021 contract solo puede ejecutarse en software_pa_test';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations
         WHERE version = '021' AND nombre = 'derecho_via_proyecto' AND checksum_sha256 = 'c759eaab96a7ed88679fd5fa288504b4bdf36724479d82e155044a572da90d4e'
    ) THEN
        RAISE EXCEPTION '021 no esta aplicada';
    END IF;
    IF to_regclass('public.trazo_proyecto') IS NULL THEN
        RAISE EXCEPTION 'trazo_proyecto legacy debe permanecer';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM geometry_columns
         WHERE f_table_schema = 'public'
           AND f_table_name = 'derecho_via_proyecto'
           AND f_geometry_column = 'geometria_poligono'
           AND type = 'MULTIPOLYGON' AND srid = 4326
    ) THEN
        RAISE EXCEPTION 'Geometria DDV debe ser MultiPolygon 4326';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
         WHERE schemaname = 'public'
           AND tablename = 'derecho_via_proyecto'
           AND indexname = 'idx_derecho_via_proyecto_geom'
           AND indexdef ILIKE '%USING gist%'
    ) THEN
        RAISE EXCEPTION 'Falta indice espacial GiST';
    END IF;

    SELECT id_usuario INTO v_actor FROM usuario
     WHERE activo ORDER BY id_usuario LIMIT 1;
    IF v_actor IS NULL THEN
        RAISE EXCEPTION 'Falta usuario actor para el contrato';
    END IF;
    PERFORM set_config('app.current_user_id', v_actor::text, true);

    INSERT INTO proyecto (clave_proyecto, nombre_proyecto, creado_por)
    VALUES ('DDV021-CONTRATO', 'Contrato DDV 021', v_actor)
    RETURNING id_proyecto INTO v_proyecto;

    INSERT INTO derecho_via_proyecto
        (id_proyecto, version, es_vigente, geometria_poligono, fuente, creado_por)
    VALUES
        (v_proyecto, 1, true, ST_GeomFromText(v_geom, 4326), 'QA 021', v_actor)
    RETURNING id_derecho_via INTO v_primero;

    v_rechazo := false;
    BEGIN
        INSERT INTO derecho_via_proyecto
            (id_proyecto, version, es_vigente, geometria_poligono, fuente)
        VALUES (v_proyecto, 2, true, ST_GeomFromText(v_geom, 4326), 'QA 021');
    EXCEPTION WHEN unique_violation THEN v_rechazo := true;
    END;
    IF NOT v_rechazo THEN
        RAISE EXCEPTION 'Se aceptaron dos versiones vigentes del mismo proyecto';
    END IF;

    UPDATE derecho_via_proyecto SET es_vigente = false
     WHERE id_derecho_via = v_primero;
    INSERT INTO derecho_via_proyecto
        (id_proyecto, version, es_vigente, geometria_poligono, fuente)
    VALUES (v_proyecto, 2, true, ST_GeomFromText(v_geom, 4326), 'QA 021')
    RETURNING id_derecho_via INTO v_segundo;
    IF NOT EXISTS (
        SELECT 1 FROM derecho_via_proyecto
         WHERE id_derecho_via = v_primero AND activo AND NOT es_vigente
    ) THEN
        RAISE EXCEPTION 'La version historica debe conservar activo=true';
    END IF;

    v_rechazo := false;
    BEGIN
        INSERT INTO derecho_via_proyecto
            (id_proyecto, version, geometria_poligono, fuente)
        VALUES (v_proyecto, 1, ST_GeomFromText(v_geom, 4326), 'QA 021');
    EXCEPTION WHEN unique_violation THEN v_rechazo := true;
    END;
    IF NOT v_rechazo THEN RAISE EXCEPTION 'Se acepto version duplicada'; END IF;

    v_rechazo := false;
    BEGIN
        INSERT INTO derecho_via_proyecto
            (id_proyecto, version, geometria_poligono, fuente)
        VALUES (v_proyecto, 0, ST_GeomFromText(v_geom, 4326), 'QA 021');
    EXCEPTION WHEN check_violation THEN v_rechazo := true;
    END;
    IF NOT v_rechazo THEN RAISE EXCEPTION 'Se acepto version 0'; END IF;

    v_rechazo := false;
    BEGIN
        INSERT INTO derecho_via_proyecto
            (id_proyecto, version, geometria_poligono, fuente)
        VALUES (-1, 1, ST_GeomFromText(v_geom, 4326), 'QA 021');
    EXCEPTION WHEN foreign_key_violation THEN v_rechazo := true;
    END;
    IF NOT v_rechazo THEN RAISE EXCEPTION 'Se acepto proyecto inexistente'; END IF;

    v_rechazo := false;
    BEGIN
        INSERT INTO derecho_via_proyecto
            (id_proyecto, version, geometria_poligono, fuente)
        VALUES (v_proyecto, 3, ST_GeomFromText('MULTIPOLYGON EMPTY', 4326), 'QA 021');
    EXCEPTION WHEN check_violation THEN v_rechazo := true;
    END;
    IF NOT v_rechazo THEN RAISE EXCEPTION 'Se acepto geometria vacia'; END IF;

    v_rechazo := false;
    BEGIN
        INSERT INTO derecho_via_proyecto
            (id_proyecto, version, geometria_poligono, fuente)
        VALUES (v_proyecto, 3,
                ST_GeomFromText('MULTIPOLYGON(((0 0,1 1,0 1,1 0,0 0)))', 4326),
                'QA 021');
    EXCEPTION WHEN check_violation THEN v_rechazo := true;
    END;
    IF NOT v_rechazo THEN RAISE EXCEPTION 'Se acepto geometria invalida'; END IF;

    v_rechazo := false;
    BEGIN
        INSERT INTO derecho_via_proyecto
            (id_proyecto, version, geometria_poligono, fuente)
        VALUES (v_proyecto, 3, ST_GeomFromText(v_geom, 3857), 'QA 021');
    EXCEPTION WHEN OTHERS THEN
        IF SQLERRM LIKE 'Geometry SRID (3857) does not match column SRID (4326)' THEN
            v_rechazo := true;
        ELSE
            RAISE;
        END IF;
    END;
    IF NOT v_rechazo THEN RAISE EXCEPTION 'Se acepto SRID distinto de 4326'; END IF;

    v_rechazo := false;
    BEGIN
        INSERT INTO derecho_via_proyecto
            (id_proyecto, version, geometria_poligono, fuente)
        VALUES (v_proyecto, 3,
                ST_GeomFromText('MULTILINESTRING((0 0,1 1))', 4326), 'QA 021');
    EXCEPTION WHEN OTHERS THEN
        IF SQLERRM LIKE 'Geometry type (MultiLineString) does not match column type (MultiPolygon)' THEN
            v_rechazo := true;
        ELSE
            RAISE;
        END IF;
    END;
    IF NOT v_rechazo THEN RAISE EXCEPTION 'Se acepto tipo distinto de MultiPolygon'; END IF;

    v_rechazo := false;
    BEGIN
        UPDATE derecho_via_proyecto SET activo = false
         WHERE id_derecho_via = v_segundo;
    EXCEPTION WHEN check_violation THEN v_rechazo := true;
    END;
    IF NOT v_rechazo THEN RAISE EXCEPTION 'Se acepto baja incompleta de vigente'; END IF;

    UPDATE derecho_via_proyecto SET es_vigente = false
     WHERE id_derecho_via = v_segundo;
    UPDATE derecho_via_proyecto
       SET activo = false, fecha_baja = now(), id_usuario_baja = v_actor,
           motivo_baja = 'Baja de contrato QA'
     WHERE id_derecho_via = v_segundo;
    IF NOT EXISTS (
        SELECT 1 FROM derecho_via_proyecto
         WHERE id_derecho_via = v_primero AND activo AND NOT es_vigente
    ) THEN
        RAISE EXCEPTION 'La baja de otra version altero la historia';
    END IF;

    v_rechazo := false;
    BEGIN
        DELETE FROM derecho_via_proyecto WHERE id_derecho_via = v_segundo;
    EXCEPTION WHEN raise_exception THEN v_rechazo := true;
    END;
    IF NOT v_rechazo THEN RAISE EXCEPTION 'Se acepto DELETE fisico'; END IF;

    IF NOT EXISTS (
        SELECT 1 FROM bitacora
         WHERE entidad_tipo = 'derecho_via_proyecto'
           AND entidad_id = v_primero AND id_proyecto = v_proyecto
           AND accion = 'insert'
    ) OR NOT EXISTS (
        SELECT 1 FROM bitacora
         WHERE entidad_tipo = 'derecho_via_proyecto'
           AND entidad_id = v_segundo AND accion = 'update'
    ) THEN
        RAISE EXCEPTION 'Falta auditoria de alta o cambio DDV';
    END IF;

    RAISE NOTICE '021 OK: geometria, versiones, vigencia, baja y auditoria';
END $$;

ROLLBACK;
