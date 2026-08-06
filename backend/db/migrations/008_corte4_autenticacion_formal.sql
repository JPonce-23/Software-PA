-- Corte 4: autenticacion formal, sesiones revocables y bloqueo de acceso.
-- Ejecutar una sola vez con psql -v ON_ERROR_STOP=1 después de un respaldo.

BEGIN;

SELECT pg_advisory_xact_lock(20260805, 8);

DO $$
BEGIN
    IF to_regclass('public.schema_migrations') IS NULL
       OR NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '007') THEN
        RAISE EXCEPTION 'La migracion 008 requiere la migracion 007 aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '008') THEN
        RAISE EXCEPTION 'La migracion 008 ya fue aplicada';
    END IF;
    IF EXISTS (
        SELECT 1
          FROM bitacora
         WHERE COALESCE(valor_anterior, '{}'::jsonb) ? 'contrasena_hash'
            OR COALESCE(valor_nuevo, '{}'::jsonb) ? 'contrasena_hash'
    ) THEN
        RAISE EXCEPTION
            'La bitacora contiene contrasena_hash; requiere saneamiento aprobado antes de 008';
    END IF;
END;
$$;

-- Redacta secretos de cualquier fotografia auditada futura.
CREATE OR REPLACE FUNCTION fn_audit_log() RETURNS TRIGGER AS $$
DECLARE
    current_user_id TEXT;
    pk_column TEXT;
    entidad_pk BIGINT;
    v_row_data JSONB;
    v_old_data JSONB;
    v_id_nucleo BIGINT := NULL;
    v_id_tramo_nucleo BIGINT := NULL;
BEGIN
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

CREATE TABLE evento_acceso (
    id_evento BIGSERIAL PRIMARY KEY,
    id_usuario INTEGER REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    id_usuario_actor INTEGER REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    id_sesion BIGINT,
    tipo_evento VARCHAR(40) NOT NULL,
    motivo_codigo VARCHAR(50) NOT NULL,
    detalle VARCHAR(200),
    fecha_hora TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_origen INET,
    user_agent VARCHAR(512),
    txid_registro BIGINT NOT NULL DEFAULT txid_current(),
    CONSTRAINT chk_008_evento_tipo CHECK (tipo_evento IN (
        'login_exitoso', 'login_fallido', 'cuenta_bloqueada',
        'logout', 'sesion_expirada', 'sesion_revocada', 'desbloqueo'
    )),
    CONSTRAINT chk_008_evento_motivo CHECK (motivo_codigo IN (
        'inicio_sesion', 'credenciales_invalidas', 'usuario_inactivo',
        'bloqueo_vigente', 'quinto_fallo', 'cierre_usuario',
        'cierre_total', 'revocacion_admin', 'expiracion_inactividad',
        'expiracion_absoluta', 'desbloqueo_admin',
        'desbloqueo_recuperacion'
    ))
);

CREATE TABLE estado_autenticacion_usuario (
    id_usuario INTEGER PRIMARY KEY
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    intentos_fallidos SMALLINT NOT NULL DEFAULT 0,
    bloqueado_hasta TIMESTAMPTZ,
    ultimo_acceso_en TIMESTAMPTZ,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_008_intentos_fallidos CHECK (
        intentos_fallidos BETWEEN 0 AND 5
    ),
    CONSTRAINT chk_008_bloqueo_consistente CHECK (
        (intentos_fallidos = 5 AND bloqueado_hasta IS NOT NULL)
        OR (intentos_fallidos < 5 AND bloqueado_hasta IS NULL)
    )
);

CREATE TABLE sesion_usuario (
    id_sesion BIGSERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    token_hash CHAR(64) NOT NULL UNIQUE,
    csrf_hash CHAR(64) NOT NULL,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ultima_actividad TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expira_en TIMESTAMPTZ NOT NULL,
    revocada_en TIMESTAMPTZ,
    id_usuario_revoca INTEGER
        REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    motivo_revocacion VARCHAR(100),
    ip_creacion INET,
    user_agent_creacion VARCHAR(512),
    CONSTRAINT chk_008_token_hash CHECK (
        token_hash ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT chk_008_csrf_hash CHECK (
        csrf_hash ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT chk_008_sesion_fechas CHECK (
        ultima_actividad >= fecha_creacion AND expira_en > fecha_creacion
    ),
    CONSTRAINT chk_008_revocacion_consistente CHECK (
        (revocada_en IS NULL AND id_usuario_revoca IS NULL
            AND motivo_revocacion IS NULL)
        OR
        (revocada_en IS NOT NULL
            AND NULLIF(BTRIM(motivo_revocacion), '') IS NOT NULL)
    )
);

ALTER TABLE evento_acceso
    ADD CONSTRAINT fk_008_evento_sesion
    FOREIGN KEY (id_sesion) REFERENCES sesion_usuario(id_sesion)
    ON DELETE RESTRICT;

CREATE INDEX idx_008_sesion_usuario
    ON sesion_usuario(id_usuario, expira_en DESC);
CREATE INDEX idx_008_sesion_actividad
    ON sesion_usuario(ultima_actividad)
    WHERE revocada_en IS NULL;
CREATE INDEX idx_008_evento_usuario_fecha
    ON evento_acceso(id_usuario, fecha_hora DESC);
CREATE INDEX idx_008_evento_fecha
    ON evento_acceso(fecha_hora DESC);

INSERT INTO estado_autenticacion_usuario(id_usuario)
SELECT id_usuario FROM usuario;

CREATE OR REPLACE FUNCTION fn_008_prevent_event_change()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Los eventos de acceso son inmutables';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_008_validar_estado_evento()
RETURNS TRIGGER AS $$
DECLARE
    v_event_id TEXT;
BEGIN
    v_event_id := current_setting('app.auth_event_id', true);
    IF v_event_id IS NULL OR v_event_id = '' OR NOT EXISTS (
        SELECT 1
          FROM evento_acceso
         WHERE id_evento = v_event_id::BIGINT
           AND id_usuario = NEW.id_usuario
           AND txid_registro = txid_current()
    ) THEN
        RAISE EXCEPTION
            'Estado de autenticacion sin evento correlacionado en la transaccion';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_008_inicializar_estado_usuario()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO estado_autenticacion_usuario(id_usuario)
    VALUES (NEW.id_usuario)
    ON CONFLICT (id_usuario) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_008_revocar_sesiones_usuario_inactivo()
RETURNS TRIGGER AS $$
DECLARE
    v_actor TEXT;
    v_sesion RECORD;
BEGIN
    IF OLD.activo = TRUE AND NEW.activo = FALSE THEN
        v_actor := current_setting('app.current_user_id', true);
        IF v_actor IS NULL OR v_actor = '' THEN
            RAISE EXCEPTION
                'La baja de usuario requiere actor para revocar sesiones';
        END IF;
        FOR v_sesion IN
            UPDATE sesion_usuario
               SET revocada_en = NOW(),
                   id_usuario_revoca = v_actor::INTEGER,
                   motivo_revocacion = 'usuario_inactivo'
             WHERE id_usuario = NEW.id_usuario
               AND revocada_en IS NULL
            RETURNING id_sesion
        LOOP
            INSERT INTO evento_acceso (
                id_usuario, id_usuario_actor, id_sesion,
                tipo_evento, motivo_codigo
            ) VALUES (
                NEW.id_usuario, v_actor::INTEGER, v_sesion.id_sesion,
                'sesion_revocada', 'usuario_inactivo'
            );
        END LOOP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_008_evento_inmutable
    BEFORE UPDATE OR DELETE ON evento_acceso
    FOR EACH ROW EXECUTE FUNCTION fn_008_prevent_event_change();
CREATE TRIGGER trg_008_prevent_delete_estado
    BEFORE DELETE ON estado_autenticacion_usuario
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_008_validar_estado_evento
    BEFORE UPDATE ON estado_autenticacion_usuario
    FOR EACH ROW EXECUTE FUNCTION fn_008_validar_estado_evento();
CREATE TRIGGER trg_008_inicializar_estado_usuario
    AFTER INSERT ON usuario
    FOR EACH ROW EXECUTE FUNCTION fn_008_inicializar_estado_usuario();
CREATE TRIGGER trg_008_revocar_sesiones_usuario_inactivo
    AFTER UPDATE OF activo ON usuario
    FOR EACH ROW EXECUTE FUNCTION fn_008_revocar_sesiones_usuario_inactivo();
CREATE TRIGGER trg_008_prevent_delete_sesion
    BEFORE DELETE ON sesion_usuario
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_008_audit_sesion
    AFTER INSERT OR UPDATE ON sesion_usuario
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_sesion');

INSERT INTO schema_migrations(version, descripcion)
VALUES ('008', 'Corte 4: autenticacion formal y sesiones revocables');

COMMIT;
