-- SS-12 etapa 2: expansión aditiva. PROPUESTA; requiere aplicación autorizada.
-- El runner registra versión/nombre/checksum en la misma transacción externa.
SET search_path = public, pg_catalog;
SELECT pg_advisory_xact_lock(hashtextextended('software-pa:031:operaciones-documentales', 0));
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='030'
        AND nombre='rbac_gis_revisiones'
        AND checksum_sha256='aa8f3f568b3abb42751202301b980d9e5dda15db2d7070c661648445e050423d')
    THEN RAISE EXCEPTION '031 requiere 030 canónica exacta'; END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version='031')
        OR to_regclass('public.documento_operacion') IS NOT NULL
    THEN RAISE EXCEPTION '031 encontró una expansión registrada o previa'; END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid='documento_version'::regclass
        AND tgname='trg_documento_version_inmutable' AND tgenabled='O')
    THEN RAISE EXCEPTION '031 requiere la inmutabilidad documental'; END IF;
END $$;

CREATE TABLE documento_operacion (
    id_operacion uuid PRIMARY KEY,
    clave_idempotencia uuid NOT NULL,
    cliente_con_clave boolean NOT NULL,
    id_documento integer NOT NULL REFERENCES documento(id_documento) ON DELETE RESTRICT,
    id_usuario integer NOT NULL REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
    huella_solicitud char(64) NOT NULL CHECK (huella_solicitud ~ '^[0-9a-f]{64}$'),
    hash_sha256 char(64) NOT NULL CHECK (hash_sha256 ~ '^[0-9a-f]{64}$'),
    tamano_bytes bigint NOT NULL CHECK (tamano_bytes > 0),
    nombre_original varchar(255) NOT NULL CHECK (NULLIF(btrim(nombre_original),'') IS NOT NULL),
    extension varchar(10) NOT NULL CHECK (extension IN ('.pdf','.docx','.xlsx','.jpg','.jpeg','.png')),
    tipo_mime varchar(150) NOT NULL CHECK (NULLIF(btrim(tipo_mime),'') IS NOT NULL),
    ruta_staging text NOT NULL,
    ruta_prevista text NOT NULL,
    estado varchar(32) NOT NULL CHECK (estado IN ('pendiente','confirmada','rechazada','requiere_reconciliacion')),
    identidad_archivo jsonb,
    id_documento_version bigint REFERENCES documento_version(id_documento_version) ON DELETE RESTRICT,
    codigo_error varchar(64) CHECK (codigo_error ~ '^[A-Z0-9_]+$'),
    http_error integer CHECK (http_error BETWEEN 400 AND 599),
    creado_en timestamptz NOT NULL DEFAULT clock_timestamp(),
    actualizado_en timestamptz NOT NULL DEFAULT clock_timestamp(),
    staging_preparado_en timestamptz,
    confirmado_en timestamptz,
    CONSTRAINT uq_documento_operacion_clave UNIQUE (id_usuario,id_documento,clave_idempotencia),
    CONSTRAINT uq_documento_operacion_version UNIQUE (id_documento_version),
    CONSTRAINT chk_operacion_rutas CHECK (
        ruta_staging=id_documento::text||'/.pending-'||replace(id_operacion::text,'-','')||'/payload'
        AND ruta_prevista=id_documento::text||'/op-'||replace(id_operacion::text,'-','')||extension),
    CONSTRAINT chk_operacion_identidad CHECK ((identidad_archivo IS NULL AND staging_preparado_en IS NULL)
        OR (identidad_archivo IS NOT NULL AND staging_preparado_en IS NOT NULL
            AND jsonb_typeof(identidad_archivo)='object'
            AND identidad_archivo ?& ARRAY['device','inode']
            AND (identidad_archivo - ARRAY['device','inode'])='{}'::jsonb
            AND jsonb_typeof(identidad_archivo->'device')='number'
            AND jsonb_typeof(identidad_archivo->'inode')='number'
            AND (identidad_archivo->>'device') ~ '^[0-9]+$'
            AND (identidad_archivo->>'inode') ~ '^[1-9][0-9]*$')),
    CONSTRAINT chk_operacion_confirmacion CHECK (
        (estado='confirmada' AND id_documento_version IS NOT NULL AND confirmado_en IS NOT NULL
            AND identidad_archivo IS NOT NULL AND codigo_error IS NULL AND http_error IS NULL)
        OR (estado<>'confirmada' AND id_documento_version IS NULL AND confirmado_en IS NULL)),
    CONSTRAINT chk_operacion_error CHECK (
        (estado IN ('rechazada','requiere_reconciliacion') AND codigo_error IS NOT NULL AND http_error IS NOT NULL)
        OR (estado IN ('pendiente','confirmada') AND codigo_error IS NULL AND http_error IS NULL))
);
CREATE INDEX idx_documento_operacion_pendiente ON documento_operacion(actualizado_en)
    WHERE estado IN ('pendiente','requiere_reconciliacion');
CREATE INDEX idx_documento_operacion_documento ON documento_operacion(id_documento,creado_en);

CREATE FUNCTION fn_documento_operacion_integridad() RETURNS trigger
LANGUAGE plpgsql SET search_path=public,pg_catalog AS $$
DECLARE v_actor integer; v_version documento_version%ROWTYPE;
BEGIN
    v_actor:=NULLIF(current_setting('app.current_user_id',true),'')::integer;
    IF v_actor IS DISTINCT FROM NEW.id_usuario THEN
        RAISE EXCEPTION 'Operación fuera del contexto de actor' USING ERRCODE='23514';
    END IF;
    IF TG_OP='INSERT' THEN
        IF NEW.estado<>'pendiente' OR NEW.identidad_archivo IS NOT NULL
            OR NOT EXISTS(SELECT 1 FROM usuario WHERE id_usuario=v_actor AND activo AND rol IN('admin','operador'))
        THEN RAISE EXCEPTION 'Intención documental inicial inválida' USING ERRCODE='23514'; END IF;
    ELSE
        IF OLD.estado IN ('confirmada','rechazada') OR
            ROW(NEW.id_operacion,NEW.clave_idempotencia,NEW.cliente_con_clave,NEW.id_documento,NEW.id_usuario,
                NEW.huella_solicitud,NEW.hash_sha256,NEW.tamano_bytes,NEW.nombre_original,NEW.extension,
                NEW.tipo_mime,NEW.ruta_staging,NEW.ruta_prevista,NEW.creado_en)
            IS DISTINCT FROM
            ROW(OLD.id_operacion,OLD.clave_idempotencia,OLD.cliente_con_clave,OLD.id_documento,OLD.id_usuario,
                OLD.huella_solicitud,OLD.hash_sha256,OLD.tamano_bytes,OLD.nombre_original,OLD.extension,
                OLD.tipo_mime,OLD.ruta_staging,OLD.ruta_prevista,OLD.creado_en)
        THEN RAISE EXCEPTION 'Identidad o resultado documental inmutable' USING ERRCODE='23514'; END IF;
        IF OLD.identidad_archivo IS NOT NULL AND
            ROW(NEW.identidad_archivo,NEW.staging_preparado_en) IS DISTINCT FROM ROW(OLD.identidad_archivo,OLD.staging_preparado_en)
        THEN RAISE EXCEPTION 'Identidad física ya registrada' USING ERRCODE='23514'; END IF;
        IF OLD.estado='requiere_reconciliacion' AND NEW.estado NOT IN ('requiere_reconciliacion','confirmada','rechazada') THEN
            RAISE EXCEPTION 'No se permite reanudar automáticamente una intención incierta' USING ERRCODE='23514';
        END IF;
        NEW.actualizado_en:=clock_timestamp();
    END IF;
    IF NEW.estado='confirmada' THEN
        SELECT * INTO v_version FROM documento_version WHERE id_documento_version=NEW.id_documento_version;
        IF NOT FOUND OR ROW(v_version.id_documento,v_version.id_usuario_carga,v_version.hash_sha256,
            v_version.tamano_bytes,v_version.nombre_original,v_version.tipo_mime,v_version.ruta_almacenamiento)
            IS DISTINCT FROM ROW(NEW.id_documento,NEW.id_usuario,NEW.hash_sha256,NEW.tamano_bytes,
                NEW.nombre_original,NEW.tipo_mime,NEW.ruta_prevista)
        THEN RAISE EXCEPTION 'Resultado documental incompatible con su intención' USING ERRCODE='23514'; END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_documento_operacion_integridad BEFORE INSERT OR UPDATE ON documento_operacion
    FOR EACH ROW EXECUTE FUNCTION fn_documento_operacion_integridad();
CREATE TRIGGER trg_documento_operacion_no_delete BEFORE DELETE ON documento_operacion
    FOR EACH ROW EXECUTE FUNCTION fn_prevenir_delete_fisico();
REVOKE ALL ON documento_operacion FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON documento_operacion TO software_pa_app;
REVOKE DELETE, TRUNCATE ON documento_operacion FROM software_pa_app;
COMMENT ON TABLE documento_operacion IS
    'SS12: intención durable por usuario/documento/clave. Pendiente no autoriza republicación; reconciliación requiere etapa 3.';
