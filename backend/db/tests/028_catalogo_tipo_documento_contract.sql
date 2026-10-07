\set ON_ERROR_STOP on
-- Pasar expected_checksum (SHA-256 del archivo 028) y expected_documents.
-- expected_document_hash es opcional: huella de filas completas antes de expandir.
BEGIN;
SET LOCAL search_path = public, pg_catalog;
SELECT set_config('app.contract_028_checksum', :'expected_checksum', true),
       set_config('app.contract_028_documents', :'expected_documents', true);
\if :{?expected_document_hash}
SELECT set_config('app.contract_028_document_hash', :'expected_document_hash', true);
\endif

DO $$
DECLARE v_actual text[];
BEGIN
    IF current_database() <> 'software_pa_test' THEN
        RAISE EXCEPTION 'Contrato 028 sólo permite software_pa_test';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '028'
        AND nombre = 'catalogo_tipo_documento'
        AND checksum_sha256 = current_setting('app.contract_028_checksum')) THEN
        RAISE EXCEPTION 'Ledger 028 ausente o checksum incorrecto';
    END IF;
    IF (SELECT count(*) FROM documento) <> current_setting('app.contract_028_documents')::bigint
       OR EXISTS (SELECT 1 FROM documento WHERE id_tipo_documento IS NOT NULL) THEN
        RAISE EXCEPTION 'Documentos iniciales cambiaron o hubo backfill';
    END IF;
    IF current_setting('app.contract_028_document_hash', true) IS NOT NULL AND
       (SELECT md5(COALESCE(string_agg((to_jsonb(d) - 'id_tipo_documento')::text,
            '|' ORDER BY id_documento), '')) FROM documento d)
       IS DISTINCT FROM current_setting('app.contract_028_document_hash', true) THEN
        RAISE EXCEPTION 'La huella histórica completa cambió';
    END IF;
    SELECT array_agg(codigo ORDER BY orden) INTO v_actual FROM catalogo_tipo_documento;
    IF v_actual IS DISTINCT FROM ARRAY['MINUTA','FOTOGRAFIA','ACTA_ASAMBLEA','PADRON','ACTA_ELECCION_ORV','ACTA_REMOCION_ORV','ACTA_NO_VERIFICATIVO','ACTA_COMPLEMENTARIA','ACTA_DELIMITACION_DESTINO_ASIGNACION','CONVOCATORIA_PRIMERA','CONVOCATORIA_SEGUNDA','CONVENIO','ACUSE_RAN','SOLICITUD_RAN','AVISO_INSCRIPCION_RAN','CONSTANCIA_INSCRIPCION_RAN','FOLIO_EJIDOS_COMUNIDADES','CREDENCIAL_INE','CREDENCIAL_RAN','CERTIFICADO_PARCELARIO','CERTIFICADO_DERECHOS_AGRARIOS','CONSTANCIA_VIGENCIA_DERECHOS','OFICIO','RESPUESTA','VALIDACION','AVALUO','OTRO']
       OR EXISTS (SELECT 1 FROM catalogo_tipo_documento WHERE NOT activo)
       OR (SELECT orden FROM catalogo_tipo_documento WHERE codigo = 'OTRO') <> 999 THEN
        RAISE EXCEPTION 'Semilla V1 incorrecta';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
        AND table_name = 'documento' AND column_name = 'id_tipo_documento'
        AND data_type = 'bigint' AND is_nullable = 'YES')
       OR NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
        AND table_name = 'documento' AND column_name = 'tipo_documento'
        AND character_maximum_length = 80 AND is_nullable = 'NO')
       OR NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'documento'::regclass
        AND conname = 'fk_documento_tipo_documento' AND contype = 'f'
        AND confrelid = 'catalogo_tipo_documento'::regclass AND confdeltype = 'r' AND convalidated)
       OR to_regclass('public.idx_documento_tipo_catalogo') IS NULL THEN
        RAISE EXCEPTION 'Expansión de Documento incorrecta';
    END IF;
END $$;

-- Una excepción ajena al SQLSTATE/constraint esperado no constituye éxito.
CREATE FUNCTION pg_temp.expect_failure(p_sql text, p_state text, p_constraint text,
                                      p_message text DEFAULT NULL) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE v_state text; v_constraint text; v_message text;
BEGIN
    BEGIN
        EXECUTE p_sql;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE,
            v_constraint = CONSTRAINT_NAME, v_message = MESSAGE_TEXT;
        IF v_state <> p_state OR COALESCE(v_constraint, '') <> COALESCE(p_constraint, '')
           OR (p_message IS NOT NULL AND v_message NOT LIKE p_message) THEN
            RAISE EXCEPTION 'Error inesperado: SQLSTATE %, constraint %, mensaje %',
                v_state, v_constraint, v_message;
        END IF;
        RETURN;
    END;
    RAISE EXCEPTION 'Escritura inválida fue aceptada: %', p_sql;
END $$;

DO $$
DECLARE v_actor integer; v_doc integer; v_other bigint; v_minuta bigint; v_photo bigint;
        v_description text;
BEGIN
    SELECT id_usuario INTO STRICT v_actor FROM usuario WHERE rol = 'admin' AND activo
    ORDER BY id_usuario LIMIT 1;
    PERFORM set_config('app.current_user_id', v_actor::text, true);
    SELECT id_tipo_documento INTO STRICT v_other FROM catalogo_tipo_documento WHERE codigo = 'OTRO';
    SELECT id_tipo_documento INTO STRICT v_minuta FROM catalogo_tipo_documento WHERE codigo = 'MINUTA';
    SELECT id_tipo_documento INTO STRICT v_photo FROM catalogo_tipo_documento WHERE codigo = 'FOTOGRAFIA';

    PERFORM pg_temp.expect_failure(
        'INSERT INTO catalogo_tipo_documento(codigo,nombre,orden) VALUES (''MINUTA'',''Duplicado'',10)',
        '23505', 'uq_catalogo_tipo_documento_codigo');
    PERFORM pg_temp.expect_failure(
        'INSERT INTO catalogo_tipo_documento(codigo,nombre,orden) VALUES (''minusculas'',''Inválido'',10)',
        '23514', 'chk_catalogo_tipo_documento_codigo');
    PERFORM pg_temp.expect_failure(
        'INSERT INTO catalogo_tipo_documento(codigo,nombre,orden) VALUES (''TEST_028'',''   '',10)',
        '23514', 'chk_catalogo_tipo_documento_nombre');
    PERFORM pg_temp.expect_failure(
        'INSERT INTO catalogo_tipo_documento(codigo,nombre,orden) VALUES (''TEST_028'',''Contrato'',-1)',
        '23514', 'chk_catalogo_tipo_documento_orden');
    PERFORM pg_temp.expect_failure(
        'UPDATE catalogo_tipo_documento SET activo=false WHERE codigo=''MINUTA''',
        '23514', 'chk_catalogo_tipo_documento_baja');
    PERFORM pg_temp.expect_failure(
        'UPDATE catalogo_tipo_documento SET codigo=''MINUTA_2'' WHERE codigo=''MINUTA''',
        '23514', 'catalogo_tipo_documento_codigo_inmutable');
    PERFORM pg_temp.expect_failure(
        'DELETE FROM catalogo_tipo_documento WHERE codigo=''MINUTA''',
        'P0001', '', 'La tabla catalogo_tipo_documento no admite DELETE fisico;%');

    PERFORM pg_temp.expect_failure(
        'INSERT INTO documento(tipo_documento,estado,id_tipo_documento) VALUES (''Contrato'',''disponible'',-1)',
        '23503', 'fk_documento_tipo_documento');
    FOREACH v_description IN ARRAY ARRAY[NULL, '', ' ', '   '] LOOP
        PERFORM pg_temp.expect_failure(format(
            'INSERT INTO documento(tipo_documento,estado,id_tipo_documento,descripcion) VALUES (''Contrato'',''disponible'',%s,%L)',
            v_other, v_description), '23514', 'documento_otro_descripcion');
    END LOOP;
    INSERT INTO documento(tipo_documento,estado,id_tipo_documento,descripcion,titulo)
    VALUES ('Otro documento','disponible',v_other,'Detalle de contrato','DOC-B03-CONTRACT');
    INSERT INTO documento(tipo_documento,estado,titulo)
    VALUES ('  Texto histórico de contrato  ','disponible','DOC-B03-CONTRACT')
    RETURNING id_documento INTO v_doc;
    UPDATE documento SET id_tipo_documento = v_minuta WHERE id_documento = v_doc;
    IF (SELECT tipo_documento FROM documento WHERE id_documento=v_doc) <> '  Texto histórico de contrato  ' THEN
        RAISE EXCEPTION 'Se sobrescribió el texto histórico';
    END IF;
    PERFORM pg_temp.expect_failure(format(
        'UPDATE documento SET id_tipo_documento=NULL WHERE id_documento=%s',v_doc),
        '23514','documento_clasificacion_irrevocable');
    PERFORM pg_temp.expect_failure(format(
        'UPDATE documento SET tipo_documento=''Cambio falso'' WHERE id_documento=%s',v_doc),
        '23514','documento_tipo_legado_protegido');
    PERFORM pg_temp.expect_failure(format(
        'UPDATE documento SET id_tipo_documento=%s,descripcion=NULL WHERE id_documento=%s',v_other,v_doc),
        '23514','documento_otro_descripcion');

    UPDATE catalogo_tipo_documento SET activo=false,fecha_baja=now(),
        id_usuario_baja=v_actor,motivo_baja='Baja de contrato 028'
    WHERE id_tipo_documento IN (v_minuta,v_photo);
    UPDATE documento SET descripcion='Metadato permitido en clasificación inactiva' WHERE id_documento=v_doc;
    IF NOT EXISTS (SELECT 1 FROM documento d JOIN catalogo_tipo_documento c USING(id_tipo_documento)
        WHERE d.id_documento=v_doc AND NOT c.activo AND c.codigo='MINUTA') THEN
        RAISE EXCEPTION 'Tipo inactivo perdió legibilidad';
    END IF;
    PERFORM pg_temp.expect_failure(format(
        'INSERT INTO documento(tipo_documento,estado,id_tipo_documento) VALUES (''Contrato'',''disponible'',%s)',v_minuta),
        '23514','documento_tipo_catalogo_activo');
    PERFORM pg_temp.expect_failure(format(
        'UPDATE documento SET id_tipo_documento=%s WHERE id_documento=%s',v_photo,v_doc),
        '23514','documento_tipo_catalogo_activo');
    IF (SELECT id_tipo_documento FROM documento WHERE id_documento=v_doc) <> v_minuta THEN
        RAISE EXCEPTION 'Una escritura rechazada modificó la fila';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM bitacora WHERE entidad_tipo='catalogo_tipo_documento') THEN
        RAISE EXCEPTION 'Catálogo sin auditoría';
    END IF;
    RAISE NOTICE '028 OK: semilla, históricos, FK, OTRO, inactivos, inmutabilidad, baja y auditoría';
END $$;
ROLLBACK;
