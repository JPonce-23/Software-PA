-- Permite que un trazo ferroviario segmentado se convierta, de manera
-- explícita y auditable, en la franja poligonal de derecho de vía.

BEGIN;

SELECT pg_advisory_xact_lock(20260817, 27);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '026') THEN
        RAISE EXCEPTION 'La migracion 027 requiere la migracion 026 aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '027') THEN
        RAISE EXCEPTION 'La migracion 027 ya fue aplicada';
    END IF;
END;
$$;

ALTER TABLE carga_geoespacial
    DROP CONSTRAINT carga_geoespacial_tipo_geometria_esperado_check;
ALTER TABLE carga_geoespacial
    ADD CONSTRAINT chk_027_carga_tipo_geometria_esperado
    CHECK (tipo_geometria_esperado IN ('linea', 'poligono', 'trazo'));

INSERT INTO schema_migrations (version, descripcion)
VALUES ('027', 'Trazo lineal segmentado a franja poligonal controlada');

COMMIT;
