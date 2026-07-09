BEGIN;
SET LOCAL "app.current_user_id" = '1';

-- 1. Actualizar la Función Genérica
CREATE OR REPLACE FUNCTION fn_audit_log() RETURNS TRIGGER AS $$
DECLARE
    current_user_id TEXT;
    pk_column TEXT;
    entidad_pk BIGINT;
    v_row_data JSONB;
    v_id_nucleo BIGINT := NULL;
    v_id_tramo_nucleo BIGINT := NULL;
BEGIN
    current_user_id := current_setting('app.current_user_id', true);
    IF current_user_id IS NULL OR current_user_id = '' THEN
        RAISE EXCEPTION 'Auditoría fallida: Falta el contexto de usuario (app.current_user_id). Use BEGIN; SET LOCAL "app.current_user_id" = 1; COMMIT;';
    END IF;

    pk_column := TG_ARGV[0];
    IF pk_column IS NULL OR pk_column = '' THEN
        RAISE EXCEPTION 'Auditoría fallida: el trigger debe indicar la columna PK en TG_ARGV[0]';
    END IF;

    IF TG_OP = 'UPDATE' OR TG_OP = 'INSERT' THEN
        v_row_data := to_jsonb(NEW);
    ELSIF TG_OP = 'DELETE' THEN
        v_row_data := to_jsonb(OLD);
    END IF;

    BEGIN
        v_id_nucleo := (v_row_data ->> 'id_nucleo')::BIGINT;
    EXCEPTION WHEN OTHERS THEN v_id_nucleo := NULL; END;
    
    BEGIN
        v_id_tramo_nucleo := (v_row_data ->> 'id_tramo_nucleo')::BIGINT;
    EXCEPTION WHEN OTHERS THEN v_id_tramo_nucleo := NULL; END;

    IF TG_OP = 'INSERT' THEN
        entidad_pk := (v_row_data ->> pk_column)::BIGINT;
        INSERT INTO bitacora (id_usuario, id_nucleo, id_tramo_nucleo, entidad_tipo, entidad_id, accion, valor_nuevo)
        VALUES (current_user_id::INTEGER, v_id_nucleo, v_id_tramo_nucleo, TG_TABLE_NAME, entidad_pk, 'insert', v_row_data);
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        entidad_pk := (v_row_data ->> pk_column)::BIGINT;
        INSERT INTO bitacora (id_usuario, id_nucleo, id_tramo_nucleo, entidad_tipo, entidad_id, accion, valor_anterior, valor_nuevo)
        VALUES (current_user_id::INTEGER, v_id_nucleo, v_id_tramo_nucleo, TG_TABLE_NAME, entidad_pk, 'update', row_to_json(OLD), v_row_data);
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 2. Modificar la Tabla 'alertas'
ALTER TABLE alertas ADD COLUMN observaciones TEXT;

-- 3. Modificar 'usuario_frente'
ALTER TABLE usuario_frente DROP CONSTRAINT usuario_frente_pkey;
ALTER TABLE usuario_frente 
    ADD COLUMN id_usuario_frente SERIAL PRIMARY KEY,
    ADD COLUMN fecha_baja TIMESTAMPTZ,
    ADD COLUMN id_usuario_baja INTEGER,
    ADD COLUMN motivo_baja TEXT,
    ADD COLUMN fecha_reactivacion TIMESTAMPTZ,
    ADD COLUMN id_usuario_reactivacion INTEGER,
    ADD COLUMN motivo_reactivacion TEXT,
    ADD COLUMN observaciones TEXT,
    ADD CONSTRAINT uq_usuario_frente UNIQUE (id_usuario, id_frente);

-- 4. Modificar 'alertas_vistas'
ALTER TABLE alertas_vistas DROP CONSTRAINT alertas_vistas_pkey;
ALTER TABLE alertas_vistas DROP CONSTRAINT alertas_vistas_id_alerta_fkey;
ALTER TABLE alertas_vistas DROP CONSTRAINT alertas_vistas_id_usuario_fkey;

ALTER TABLE alertas_vistas 
    ADD CONSTRAINT alertas_vistas_id_alerta_fkey FOREIGN KEY (id_alerta) REFERENCES alertas(id_alerta),
    ADD CONSTRAINT alertas_vistas_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario),
    ADD COLUMN id_alerta_vista SERIAL PRIMARY KEY,
    ADD COLUMN activo BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN fecha_baja TIMESTAMPTZ,
    ADD COLUMN id_usuario_baja INTEGER,
    ADD COLUMN motivo_baja TEXT,
    ADD COLUMN fecha_reactivacion TIMESTAMPTZ,
    ADD COLUMN id_usuario_reactivacion INTEGER,
    ADD COLUMN motivo_reactivacion TEXT,
    ADD COLUMN observaciones TEXT,
    ADD CONSTRAINT uq_alertas_vistas UNIQUE (id_alerta, id_usuario);

-- 5. Instanciar los nuevos Triggers
CREATE TRIGGER trg_audit_usuario_frente
    AFTER INSERT OR UPDATE ON usuario_frente
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_usuario_frente');
CREATE TRIGGER trg_prevent_delete_usuario_frente
    BEFORE DELETE ON usuario_frente
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_usuario_frente
    BEFORE UPDATE OF activo ON usuario_frente
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

CREATE TRIGGER trg_audit_alertas_vistas
    AFTER INSERT OR UPDATE ON alertas_vistas
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_alerta_vista');
CREATE TRIGGER trg_prevent_delete_alertas_vistas
    BEFORE DELETE ON alertas_vistas
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_alertas_vistas
    BEFORE UPDATE OF activo ON alertas_vistas
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

COMMIT;
