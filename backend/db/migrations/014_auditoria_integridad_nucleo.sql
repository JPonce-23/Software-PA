BEGIN;

SELECT pg_advisory_xact_lock(hashtext('schema_migration_014'));

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '013') THEN
        RAISE EXCEPTION 'La migracion 013 es requisito para aplicar 014';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '014') THEN
        RAISE EXCEPTION 'La migracion 014 ya fue aplicada';
    END IF;
    IF to_regclass('public.nucleo_agrario') IS NULL THEN
        RAISE EXCEPTION 'No existe nucleo_agrario';
    END IF;
END;
$$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
          FROM nucleo_agrario
         WHERE geometria_poligono IS NOT NULL
           AND (
               ST_IsEmpty(geometria_poligono)
               OR NOT ST_IsValid(geometria_poligono)
               OR ST_SRID(geometria_poligono) <> 4326
               OR GeometryType(geometria_poligono) <> 'MULTIPOLYGON'
           )
    ) THEN
        RAISE EXCEPTION 'Existen nucleos con geometria incompatible';
    END IF;
END;
$$;

ALTER TABLE nucleo_agrario
    ADD CONSTRAINT chk_nucleo_geometria_valida CHECK (
        geometria_poligono IS NULL
        OR (
            NOT ST_IsEmpty(geometria_poligono)
            AND ST_IsValid(geometria_poligono)
            AND ST_SRID(geometria_poligono) = 4326
            AND GeometryType(geometria_poligono) = 'MULTIPOLYGON'
        )
    );

INSERT INTO schema_migrations (version, descripcion)
VALUES ('014', 'Auditoria de integridad geometrica de nucleos');

COMMIT;
