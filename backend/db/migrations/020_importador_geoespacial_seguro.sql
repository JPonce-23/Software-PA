-- ============================================================
-- MIGRACION 020: Importador geoespacial seguro y auditable
--
-- * Separa staging de las tablas operativas.
-- * Conserva identidad y atributos de fuentes externas.
-- * Agrega perfiles de mapeo y alias territoriales aprobados.
-- * Impide eliminacion fisica de la trazabilidad de importacion.
-- ============================================================

BEGIN;

SELECT pg_advisory_xact_lock(20260814, 20);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '019') THEN
        RAISE EXCEPTION 'La migracion 020 requiere que la migracion 019 este aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '020') THEN
        RAISE EXCEPTION 'La migracion 020 ya fue aplicada';
    END IF;
END;
$$;

CREATE TABLE perfil_mapeo_importacion (
    id_perfil BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL UNIQUE,
    fuente VARCHAR(200) NOT NULL,
    tipo_objetivo VARCHAR(40) NOT NULL DEFAULT 'nucleo_agrario',
    mapeo JSONB NOT NULL,
    opciones JSONB NOT NULL DEFAULT '{}'::jsonb,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    id_usuario_creacion INTEGER NOT NULL REFERENCES usuario(id_usuario),
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_020_perfil_nombre CHECK (btrim(nombre) <> ''),
    CONSTRAINT chk_020_perfil_fuente CHECK (btrim(fuente) <> ''),
    CONSTRAINT chk_020_perfil_objetivo CHECK (tipo_objetivo = 'nucleo_agrario'),
    CONSTRAINT chk_020_perfil_mapeo_objeto CHECK (jsonb_typeof(mapeo) = 'object'),
    CONSTRAINT chk_020_perfil_opciones_objeto CHECK (jsonb_typeof(opciones) = 'object')
);

CREATE TABLE catalogo_alias_territorial (
    id_alias BIGSERIAL PRIMARY KEY,
    id_entidad INTEGER NOT NULL REFERENCES entidad_federativa(id_entidad),
    alias_nombre VARCHAR(200),
    alias_normalizado VARCHAR(200) NOT NULL,
    alias_clave VARCHAR(20),
    id_municipio_destino INTEGER NOT NULL REFERENCES municipio(id_municipio),
    fuente VARCHAR(300) NOT NULL,
    fecha_vigencia_inicio DATE,
    fecha_vigencia_fin DATE,
    fecha_aprobacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    id_usuario_aprobador INTEGER NOT NULL REFERENCES usuario(id_usuario),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_020_alias_identidad CHECK (
        (alias_nombre IS NOT NULL AND btrim(alias_nombre) <> '')
        OR (alias_clave IS NOT NULL AND btrim(alias_clave) <> '')
    ),
    CONSTRAINT chk_020_alias_normalizado CHECK (btrim(alias_normalizado) <> ''),
    CONSTRAINT chk_020_alias_fuente CHECK (btrim(fuente) <> ''),
    CONSTRAINT chk_020_alias_vigencia CHECK (
        fecha_vigencia_fin IS NULL
        OR fecha_vigencia_inicio IS NULL
        OR fecha_vigencia_inicio <= fecha_vigencia_fin
    )
);

CREATE UNIQUE INDEX uq_020_alias_nombre_activo
    ON catalogo_alias_territorial (id_entidad, alias_normalizado)
    WHERE activo = TRUE;

CREATE TABLE importacion_archivo (
    id_importacion BIGSERIAL PRIMARY KEY,
    tipo_objetivo VARCHAR(40) NOT NULL DEFAULT 'nucleo_agrario',
    nombre_original VARCHAR(255) NOT NULL,
    nombre_almacenado VARCHAR(100) NOT NULL UNIQUE,
    formato_detectado VARCHAR(20) NOT NULL,
    tamano_bytes BIGINT NOT NULL,
    sha256 CHAR(64) NOT NULL,
    fuente VARCHAR(200) NOT NULL,
    crs_original TEXT,
    crs_destino VARCHAR(20) NOT NULL DEFAULT 'EPSG:4326',
    columnas_detectadas JSONB NOT NULL DEFAULT '[]'::jsonb,
    mapeo JSONB NOT NULL DEFAULT '{}'::jsonb,
    opciones_mapeo JSONB NOT NULL DEFAULT '{}'::jsonb,
    id_perfil BIGINT REFERENCES perfil_mapeo_importacion(id_perfil),
    estado VARCHAR(30) NOT NULL DEFAULT 'subido',
    total_features INTEGER NOT NULL DEFAULT 0,
    features_procesados INTEGER NOT NULL DEFAULT 0,
    validos INTEGER NOT NULL DEFAULT 0,
    advertencias INTEGER NOT NULL DEFAULT 0,
    errores INTEGER NOT NULL DEFAULT 0,
    importados INTEGER NOT NULL DEFAULT 0,
    descartados INTEGER NOT NULL DEFAULT 0,
    tolerancia_area_relativa NUMERIC(12,10),
    id_usuario_carga INTEGER NOT NULL REFERENCES usuario(id_usuario),
    fecha_carga TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_procesamiento_inicio TIMESTAMPTZ,
    fecha_procesamiento_fin TIMESTAMPTZ,
    fecha_confirmacion TIMESTAMPTZ,
    id_usuario_confirmacion INTEGER REFERENCES usuario(id_usuario),
    fecha_completado TIMESTAMPTZ,
    archivo_eliminado_en TIMESTAMPTZ,
    error_codigo VARCHAR(80),
    error_detalle TEXT,
    version_control INTEGER NOT NULL DEFAULT 1,
    CONSTRAINT chk_020_archivo_objetivo CHECK (tipo_objetivo = 'nucleo_agrario'),
    CONSTRAINT chk_020_archivo_formato CHECK (formato_detectado IN ('kml', 'geojson')),
    CONSTRAINT chk_020_archivo_tamano CHECK (tamano_bytes > 0),
    CONSTRAINT chk_020_archivo_sha CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT chk_020_archivo_fuente CHECK (btrim(fuente) <> ''),
    CONSTRAINT chk_020_archivo_estado CHECK (estado IN (
        'subido', 'analizando', 'normalizando', 'resolviendo',
        'listo_revision', 'confirmando', 'importando', 'completado', 'fallido'
    )),
    CONSTRAINT chk_020_archivo_conteos CHECK (
        total_features >= 0 AND features_procesados >= 0
        AND validos >= 0 AND advertencias >= 0 AND errores >= 0
        AND importados >= 0 AND descartados >= 0
    ),
    CONSTRAINT chk_020_archivo_mapeo CHECK (jsonb_typeof(mapeo) = 'object'),
    CONSTRAINT chk_020_archivo_opciones CHECK (jsonb_typeof(opciones_mapeo) = 'object'),
    CONSTRAINT chk_020_archivo_columnas CHECK (jsonb_typeof(columnas_detectadas) = 'array'),
    CONSTRAINT chk_020_tolerancia_area CHECK (
        tolerancia_area_relativa IS NULL
        OR (tolerancia_area_relativa >= 0 AND tolerancia_area_relativa <= 1)
    )
);

CREATE UNIQUE INDEX uq_020_archivo_sha_objetivo
    ON importacion_archivo (sha256, tipo_objetivo);
CREATE INDEX idx_020_archivo_estado
    ON importacion_archivo (estado, fecha_carga DESC);
CREATE INDEX idx_020_archivo_usuario
    ON importacion_archivo (id_usuario_carga, fecha_carga DESC);

CREATE TABLE importacion_feature (
    id_importacion_feature BIGSERIAL PRIMARY KEY,
    id_importacion BIGINT NOT NULL REFERENCES importacion_archivo(id_importacion),
    indice_feature INTEGER NOT NULL,
    capa_origen VARCHAR(200),
    id_externo VARCHAR(500),
    id_entidad_fuente VARCHAR(100),
    id_municipio_fuente VARCHAR(100),
    id_nucleo_fuente VARCHAR(200),
    atributos_originales JSONB NOT NULL DEFAULT '{}'::jsonb,
    atributos_normalizados JSONB NOT NULL DEFAULT '{}'::jsonb,
    geometria_normalizada geometry(MultiPolygon, 4326),
    id_entidad_resuelta INTEGER REFERENCES entidad_federativa(id_entidad),
    id_municipio_resuelto INTEGER REFERENCES municipio(id_municipio),
    estado VARCHAR(30) NOT NULL DEFAULT 'pendiente_revision',
    errores JSONB NOT NULL DEFAULT '[]'::jsonb,
    advertencias JSONB NOT NULL DEFAULT '[]'::jsonb,
    transformaciones JSONB NOT NULL DEFAULT '[]'::jsonb,
    area_original_m2 NUMERIC(24,4),
    area_normalizada_m2 NUMERIC(24,4),
    diferencia_area_relativa NUMERIC(16,12),
    advertencias_aceptadas BOOLEAN NOT NULL DEFAULT FALSE,
    id_usuario_revision INTEGER REFERENCES usuario(id_usuario),
    fecha_revision TIMESTAMPTZ,
    id_nucleo_operativo INTEGER REFERENCES nucleo_agrario(id_nucleo),
    fecha_procesamiento TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_importacion TIMESTAMPTZ,
    CONSTRAINT uq_020_feature_archivo_indice UNIQUE (id_importacion, indice_feature),
    CONSTRAINT chk_020_feature_indice CHECK (indice_feature >= 0),
    CONSTRAINT chk_020_feature_estado CHECK (estado IN (
        'valido', 'advertencia', 'error', 'importado',
        'pendiente_revision', 'descartado'
    )),
    CONSTRAINT chk_020_feature_json CHECK (
        jsonb_typeof(atributos_originales) = 'object'
        AND jsonb_typeof(atributos_normalizados) = 'object'
        AND jsonb_typeof(errores) = 'array'
        AND jsonb_typeof(advertencias) = 'array'
        AND jsonb_typeof(transformaciones) = 'array'
    ),
    CONSTRAINT chk_020_feature_area CHECK (
        area_original_m2 IS NULL OR area_original_m2 >= 0
    ),
    CONSTRAINT chk_020_feature_area_normalizada CHECK (
        area_normalizada_m2 IS NULL OR area_normalizada_m2 >= 0
    ),
    CONSTRAINT chk_020_feature_diferencia CHECK (
        diferencia_area_relativa IS NULL OR diferencia_area_relativa >= 0
    )
);

CREATE INDEX idx_020_feature_archivo_estado
    ON importacion_feature (id_importacion, estado, indice_feature);
CREATE INDEX idx_020_feature_id_externo
    ON importacion_feature (id_importacion, id_externo)
    WHERE id_externo IS NOT NULL;
CREATE INDEX idx_020_feature_municipio
    ON importacion_feature (id_municipio_resuelto)
    WHERE id_municipio_resuelto IS NOT NULL;
CREATE INDEX idx_020_feature_geometria
    ON importacion_feature USING GIST (geometria_normalizada);

ALTER TABLE nucleo_agrario
    ADD COLUMN fuente_datos VARCHAR(200),
    ADD COLUMN id_entidad_fuente VARCHAR(100),
    ADD COLUMN id_municipio_fuente VARCHAR(100),
    ADD COLUMN id_nucleo_fuente VARCHAR(200);

ALTER TABLE nucleo_agrario
    ADD CONSTRAINT chk_020_nucleo_fuente CHECK (
        fuente_datos IS NULL OR btrim(fuente_datos) <> ''
    );

CREATE UNIQUE INDEX uq_020_nucleo_identidad_fuente_activa
    ON nucleo_agrario (lower(fuente_datos), id_nucleo_fuente)
    WHERE activo = TRUE
      AND fuente_datos IS NOT NULL
      AND id_nucleo_fuente IS NOT NULL;

CREATE OR REPLACE FUNCTION fn_020_validar_alias_territorial()
RETURNS TRIGGER AS $$
DECLARE
    v_entidad_destino INTEGER;
BEGIN
    SELECT id_entidad
      INTO v_entidad_destino
      FROM municipio
     WHERE id_municipio = NEW.id_municipio_destino
       AND activo = TRUE
     FOR KEY SHARE;

    IF v_entidad_destino IS NULL OR v_entidad_destino <> NEW.id_entidad THEN
        RAISE EXCEPTION 'ALIAS_MUNICIPIO_FUERA_DE_ENTIDAD';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_020_alias_entidad
    BEFORE INSERT OR UPDATE OF id_entidad, id_municipio_destino, activo
    ON catalogo_alias_territorial
    FOR EACH ROW EXECUTE FUNCTION fn_020_validar_alias_territorial();

CREATE TRIGGER trg_audit_perfil_mapeo_importacion
    AFTER INSERT OR UPDATE ON perfil_mapeo_importacion
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_perfil');
CREATE TRIGGER trg_audit_catalogo_alias_territorial
    AFTER INSERT OR UPDATE ON catalogo_alias_territorial
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_alias');
CREATE TRIGGER trg_audit_importacion_archivo
    AFTER INSERT OR UPDATE ON importacion_archivo
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_importacion');

CREATE TRIGGER trg_prevent_delete_perfil_mapeo_importacion
    BEFORE DELETE ON perfil_mapeo_importacion
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_prevent_delete_catalogo_alias_territorial
    BEFORE DELETE ON catalogo_alias_territorial
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_prevent_delete_importacion_archivo
    BEFORE DELETE ON importacion_archivo
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_prevent_delete_importacion_feature
    BEFORE DELETE ON importacion_feature
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();

INSERT INTO schema_migrations (version, descripcion)
VALUES ('020', 'Importador geoespacial seguro con staging auditable');

COMMIT;
