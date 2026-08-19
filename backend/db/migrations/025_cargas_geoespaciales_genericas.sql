-- Staging comun para geometria individual y candidatos territoriales revisables.

BEGIN;

SELECT pg_advisory_xact_lock(20260814, 25);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '024') THEN
        RAISE EXCEPTION 'La migracion 025 requiere la migracion 024 aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '025') THEN
        RAISE EXCEPTION 'La migracion 025 ya fue aplicada';
    END IF;
END;
$$;

CREATE TABLE carga_geoespacial (
    id_carga BIGSERIAL PRIMARY KEY,
    tipo_objetivo VARCHAR(40) NOT NULL CHECK (tipo_objetivo IN ('tramo', 'franja_derecho_via', 'nucleo_agrario', 'parcela')),
    tipo_geometria_esperado VARCHAR(20) NOT NULL CHECK (tipo_geometria_esperado IN ('linea', 'poligono')),
    nombre_original VARCHAR(255) NOT NULL,
    nombre_almacenado VARCHAR(100) NOT NULL UNIQUE,
    formato_detectado VARCHAR(20) NOT NULL CHECK (formato_detectado IN ('kml', 'geojson', 'shapefile')),
    tamano_bytes BIGINT NOT NULL CHECK (tamano_bytes > 0),
    sha256 VARCHAR(64) NOT NULL,
    fuente VARCHAR(200),
    crs_original TEXT NOT NULL,
    crs_destino VARCHAR(20) NOT NULL DEFAULT 'EPSG:4326',
    total_features INTEGER NOT NULL DEFAULT 0 CHECK (total_features >= 0),
    features_validos INTEGER NOT NULL DEFAULT 0 CHECK (features_validos >= 0),
    features_advertencia INTEGER NOT NULL DEFAULT 0 CHECK (features_advertencia >= 0),
    features_error INTEGER NOT NULL DEFAULT 0 CHECK (features_error >= 0),
    estado VARCHAR(30) NOT NULL DEFAULT 'subido' CHECK (estado IN ('subido', 'prevalidando', 'listo_revision', 'confirmado', 'cancelado', 'fallido')),
    id_usuario_carga INTEGER NOT NULL REFERENCES usuario(id_usuario),
    fecha_carga TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    fecha_procesamiento TIMESTAMP WITH TIME ZONE,
    fecha_confirmacion TIMESTAMP WITH TIME ZONE,
    id_usuario_confirmacion INTEGER REFERENCES usuario(id_usuario),
    error_codigo VARCHAR(80),
    error_detalle TEXT
);

CREATE INDEX idx_025_carga_geoespacial_usuario_fecha
    ON carga_geoespacial (id_usuario_carga, fecha_carga DESC);
CREATE INDEX idx_025_carga_geoespacial_sha
    ON carga_geoespacial (sha256);

CREATE TABLE carga_geoespacial_feature (
    id_carga_feature BIGSERIAL PRIMARY KEY,
    id_carga BIGINT NOT NULL REFERENCES carga_geoespacial(id_carga) ON DELETE RESTRICT,
    indice_feature INTEGER NOT NULL CHECK (indice_feature >= 0),
    capa_origen VARCHAR(200),
    atributos_originales JSONB NOT NULL DEFAULT '{}'::jsonb,
    geometria_normalizada geometry(Geometry, 4326),
    tipo_geometria VARCHAR(40),
    estado VARCHAR(20) NOT NULL CHECK (estado IN ('valido', 'advertencia', 'error')),
    errores JSONB NOT NULL DEFAULT '[]'::jsonb,
    advertencias JSONB NOT NULL DEFAULT '[]'::jsonb,
    transformaciones JSONB NOT NULL DEFAULT '[]'::jsonb,
    area_original_m2 NUMERIC(24, 4),
    area_normalizada_m2 NUMERIC(24, 4),
    diferencia_area_relativa NUMERIC(16, 12),
    seleccionado BOOLEAN NOT NULL DEFAULT FALSE,
    id_registro_operativo BIGINT,
    fecha_consumo TIMESTAMP WITH TIME ZONE,
    id_usuario_consumo INTEGER REFERENCES usuario(id_usuario),
    CONSTRAINT uq_025_carga_feature UNIQUE (id_carga, capa_origen, indice_feature),
    CONSTRAINT chk_025_carga_feature_geometria CHECK (
        geometria_normalizada IS NULL OR (
            NOT ST_IsEmpty(geometria_normalizada)
            AND ST_IsValid(geometria_normalizada)
            AND ST_SRID(geometria_normalizada) = 4326
        )
    ),
    CONSTRAINT chk_025_carga_feature_consumo CHECK (
        (id_registro_operativo IS NULL AND fecha_consumo IS NULL AND id_usuario_consumo IS NULL)
        OR (id_registro_operativo IS NOT NULL AND fecha_consumo IS NOT NULL AND id_usuario_consumo IS NOT NULL)
    )
);

CREATE INDEX idx_025_carga_feature_carga_estado
    ON carga_geoespacial_feature (id_carga, estado, indice_feature);
CREATE INDEX idx_025_carga_feature_geometria
    ON carga_geoespacial_feature USING GIST (geometria_normalizada);
CREATE UNIQUE INDEX uq_025_carga_feature_seleccionada
    ON carga_geoespacial_feature (id_carga) WHERE seleccionado;

CREATE TABLE candidato_tramo_nucleo (
    id_candidato BIGSERIAL PRIMARY KEY,
    id_tramo INTEGER NOT NULL REFERENCES tramo(id_tramo),
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    id_franja INTEGER NOT NULL REFERENCES franja_derecho_via(id_franja),
    area_interseccion_m2 NUMERIC(24, 4) NOT NULL CHECK (area_interseccion_m2 > 0),
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aceptado', 'rechazado')),
    fecha_deteccion TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    id_usuario_deteccion INTEGER NOT NULL REFERENCES usuario(id_usuario),
    fecha_resolucion TIMESTAMP WITH TIME ZONE,
    id_usuario_resolucion INTEGER REFERENCES usuario(id_usuario),
    motivo_resolucion VARCHAR(500),
    id_tramo_nucleo INTEGER REFERENCES tramo_nucleo(id_tramo_nucleo),
    CONSTRAINT uq_025_candidato_franja_nucleo UNIQUE (id_franja, id_nucleo),
    CONSTRAINT chk_025_candidato_resolucion CHECK (
        (estado = 'pendiente' AND fecha_resolucion IS NULL AND id_usuario_resolucion IS NULL AND id_tramo_nucleo IS NULL)
        OR (estado = 'aceptado' AND fecha_resolucion IS NOT NULL AND id_usuario_resolucion IS NOT NULL AND id_tramo_nucleo IS NOT NULL)
        OR (estado = 'rechazado' AND fecha_resolucion IS NOT NULL AND id_usuario_resolucion IS NOT NULL AND id_tramo_nucleo IS NULL)
    )
);

CREATE INDEX idx_025_candidato_tramo_estado
    ON candidato_tramo_nucleo (id_tramo, estado, fecha_deteccion DESC);

INSERT INTO schema_migrations (version, descripcion)
VALUES ('025', 'Staging geoespacial generico y candidatos tramo-nucleo');

COMMIT;
