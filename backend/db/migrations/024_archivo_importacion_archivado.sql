-- Archivar (baja logica) importaciones geoespaciales sin perder trazabilidad.

BEGIN;

SELECT pg_advisory_xact_lock(20260814, 24);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '023') THEN
        RAISE EXCEPTION 'La migracion 024 requiere la migracion 023 aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '024') THEN
        RAISE EXCEPTION 'La migracion 024 ya fue aplicada';
    END IF;
END;
$$;

ALTER TABLE importacion_archivo
    ADD COLUMN IF NOT EXISTS fecha_baja TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    ADD COLUMN IF NOT EXISTS motivo_baja VARCHAR;

CREATE INDEX IF NOT EXISTS idx_024_importacion_archivo_fecha_baja
    ON importacion_archivo (fecha_baja)
    WHERE fecha_baja IS NOT NULL;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('024', 'Baja logica de importaciones geoespaciales');

COMMIT;
