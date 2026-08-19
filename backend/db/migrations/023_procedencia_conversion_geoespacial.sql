-- Registra la procedencia de archivos convertidos y permite comprobar perdidas.

BEGIN;

SELECT pg_advisory_xact_lock(20260814, 23);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '022') THEN
        RAISE EXCEPTION 'La migracion 023 requiere la migracion 022 aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '023') THEN
        RAISE EXCEPTION 'La migracion 023 ya fue aplicada';
    END IF;
END;
$$;

ALTER TABLE importacion_archivo
    ADD COLUMN procedencia_archivo VARCHAR(20),
    ADD COLUMN id_importacion_origen BIGINT
        REFERENCES importacion_archivo(id_importacion) ON DELETE RESTRICT;

ALTER TABLE importacion_archivo
    ADD CONSTRAINT chk_023_archivo_procedencia CHECK (
        procedencia_archivo IS NULL
        OR procedencia_archivo IN ('original', 'conversion')
    ),
    ADD CONSTRAINT chk_023_archivo_origen_distinto CHECK (
        id_importacion_origen IS NULL
        OR id_importacion_origen <> id_importacion
    ),
    ADD CONSTRAINT chk_023_archivo_conversion_origen CHECK (
        (procedencia_archivo IS NULL AND id_importacion_origen IS NULL)
        OR (procedencia_archivo = 'original' AND id_importacion_origen IS NULL)
        OR (procedencia_archivo = 'conversion' AND id_importacion_origen IS NOT NULL)
    );

CREATE INDEX idx_023_archivo_importacion_origen
    ON importacion_archivo (id_importacion_origen)
    WHERE id_importacion_origen IS NOT NULL;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('023', 'Procedencia y control de conteo para conversiones geoespaciales');

COMMIT;
