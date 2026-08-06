-- Corte 4: evita atribuir expiraciones automáticas al usuario objetivo.

BEGIN;

SELECT pg_advisory_xact_lock(20260805, 9);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '008') THEN
        RAISE EXCEPTION 'La migracion 009 requiere la migracion 008 aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '009') THEN
        RAISE EXCEPTION 'La migracion 009 ya fue aplicada';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION fn_audit_log() RETURNS TRIGGER AS $$
DECLARE
    current_user_id TEXT;
    v_system_event_id TEXT;
    pk_column TEXT;
    entidad_pk BIGINT;
    v_row_data JSONB;
    v_old_data JSONB;
    v_id_nucleo BIGINT := NULL;
    v_id_tramo_nucleo BIGINT := NULL;
BEGIN
    -- Una expiración automática de sesión no tiene actor humano. Se admite
    -- omitir bitácora sólo si ya existe su evento forense, sin actor, para la
    -- misma sesión y transacción. Cualquier otra escritura sigue exigiendo
    -- app.current_user_id y la auditoría genérica normal.
    v_system_event_id := current_setting('app.auth_system_event_id', true);
    IF TG_TABLE_NAME = 'sesion_usuario'
       AND TG_OP = 'UPDATE'
       AND v_system_event_id IS NOT NULL
       AND v_system_event_id <> '' THEN
        IF NOT EXISTS (
            SELECT 1
              FROM evento_acceso
             WHERE id_evento = v_system_event_id::BIGINT
               AND id_sesion = NEW.id_sesion
               AND id_usuario = NEW.id_usuario
               AND id_usuario_actor IS NULL
               AND tipo_evento = 'sesion_expirada'
               AND motivo_codigo = NEW.motivo_revocacion
               AND motivo_codigo IN (
                   'expiracion_inactividad', 'expiracion_absoluta'
               )
               AND txid_registro = txid_current()
        ) THEN
            RAISE EXCEPTION
                'Expiracion de sesion sin evento de sistema correlacionado';
        END IF;
        IF OLD.revocada_en IS NOT NULL
           OR NEW.revocada_en IS NULL
           OR NEW.id_usuario_revoca IS NOT NULL
           OR (
               to_jsonb(NEW) - ARRAY[
                   'revocada_en', 'id_usuario_revoca', 'motivo_revocacion'
               ]
               IS DISTINCT FROM
               to_jsonb(OLD) - ARRAY[
                   'revocada_en', 'id_usuario_revoca', 'motivo_revocacion'
               ]
           ) THEN
            RAISE EXCEPTION
                'La expiracion automatica intento modificar campos no permitidos';
        END IF;
        RETURN NEW;
    END IF;

    current_user_id := current_setting('app.current_user_id', true);
    IF current_user_id IS NULL OR current_user_id = '' THEN
        RAISE EXCEPTION
            'Auditoria fallida: falta app.current_user_id en la transaccion';
    END IF;

    pk_column := TG_ARGV[0];
    IF pk_column IS NULL OR pk_column = '' THEN
        RAISE EXCEPTION
            'Auditoria fallida: el trigger debe indicar la columna PK';
    END IF;

    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        v_row_data := to_jsonb(NEW)
            - ARRAY['contrasena_hash', 'token_hash', 'csrf_hash'];
    ELSE
        v_row_data := to_jsonb(OLD)
            - ARRAY['contrasena_hash', 'token_hash', 'csrf_hash'];
    END IF;
    IF TG_OP = 'UPDATE' THEN
        v_old_data := to_jsonb(OLD)
            - ARRAY['contrasena_hash', 'token_hash', 'csrf_hash'];
    END IF;

    BEGIN
        v_id_nucleo := (v_row_data ->> 'id_nucleo')::BIGINT;
    EXCEPTION WHEN OTHERS THEN
        v_id_nucleo := NULL;
    END;
    BEGIN
        v_id_tramo_nucleo := (v_row_data ->> 'id_tramo_nucleo')::BIGINT;
    EXCEPTION WHEN OTHERS THEN
        v_id_tramo_nucleo := NULL;
    END;

    entidad_pk := (v_row_data ->> pk_column)::BIGINT;
    IF TG_OP = 'INSERT' THEN
        INSERT INTO bitacora (
            id_usuario, id_nucleo, id_tramo_nucleo, entidad_tipo,
            entidad_id, accion, valor_nuevo
        ) VALUES (
            current_user_id::INTEGER, v_id_nucleo, v_id_tramo_nucleo,
            TG_TABLE_NAME, entidad_pk, 'insert', v_row_data
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO bitacora (
            id_usuario, id_nucleo, id_tramo_nucleo, entidad_tipo,
            entidad_id, accion, valor_anterior, valor_nuevo
        ) VALUES (
            current_user_id::INTEGER, v_id_nucleo, v_id_tramo_nucleo,
            TG_TABLE_NAME, entidad_pk, 'update', v_old_data, v_row_data
        );
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

INSERT INTO schema_migrations(version, descripcion)
VALUES ('009', 'Corte 4: auditoria veraz de expiraciones de sesion');

COMMIT;
