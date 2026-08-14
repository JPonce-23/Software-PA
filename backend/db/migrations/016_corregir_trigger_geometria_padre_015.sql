BEGIN;

SELECT pg_advisory_xact_lock(hashtext('schema_migration_016'));

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '015') THEN
        RAISE EXCEPTION 'La migracion 015 es requisito para aplicar 016';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '016') THEN
        RAISE EXCEPTION 'La migracion 016 ya fue aplicada';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION fn_015_validar_geometria_padre() RETURNS TRIGGER AS $$
BEGIN
    IF TG_TABLE_NAME = 'tramo' THEN
        IF NEW.geometria_linea IS DISTINCT FROM OLD.geometria_linea
           AND EXISTS (
               SELECT 1 FROM tramo_nucleo tn
                WHERE tn.id_tramo = NEW.id_tramo
                  AND tn.activo
                  AND tn.geometria_segmento IS NOT NULL
                  AND NEW.geometria_linea IS NOT NULL
                  AND NOT ST_Intersects(tn.geometria_segmento, NEW.geometria_linea)
           ) THEN
            RAISE EXCEPTION 'ADM_GEOMETRIA_TRAMO_ROMPE_RELACIONES';
        END IF;
        RETURN NEW;
    END IF;

    IF TG_TABLE_NAME = 'nucleo_agrario' THEN
        IF NEW.geometria_poligono IS DISTINCT FROM OLD.geometria_poligono
           AND EXISTS (
               SELECT 1 FROM tramo_nucleo tn
                WHERE tn.id_nucleo = NEW.id_nucleo
                  AND tn.activo
                  AND tn.geometria_segmento IS NOT NULL
                  AND NEW.geometria_poligono IS NOT NULL
                  AND NOT ST_Intersects(tn.geometria_segmento, NEW.geometria_poligono)
           ) THEN
            RAISE EXCEPTION 'ADM_GEOMETRIA_NUCLEO_ROMPE_RELACIONES';
        END IF;
        RETURN NEW;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('016', 'Correccion de trigger de geometria padre de administracion territorial');

COMMIT;
