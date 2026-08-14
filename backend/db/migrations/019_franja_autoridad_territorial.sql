-- ============================================================
-- MIGRACION 019: Franja activa como autoridad territorial
--
-- * Agrega indice espacial para cruces nucleo-franja.
-- * Exige que la franja activa intersecte la linea de su tramo.
-- * Exige superficie positiva de franja dentro de cada nucleo relacionado.
-- * Impide que una nueva version de franja invalide relaciones activas.
-- ============================================================

BEGIN;

SELECT pg_advisory_xact_lock(20260814, 19);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '018') THEN
        RAISE EXCEPTION 'La migracion 019 requiere que la migracion 018 este aplicada';
    END IF;

    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '019') THEN
        RAISE EXCEPTION 'La migracion 019 ya fue aplicada';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM franja_derecho_via f
          JOIN tramo t ON t.id_tramo = f.id_tramo
         WHERE f.activo = TRUE
           AND (
               t.activo IS NOT TRUE
               OR t.geometria_linea IS NULL
               OR NOT ST_Intersects(f.geometria_poligono, t.geometria_linea)
           )
    ) THEN
        RAISE EXCEPTION 'Existen franjas activas que no intersectan la linea de su tramo';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM tramo_nucleo tn
          JOIN nucleo_agrario n ON n.id_nucleo = tn.id_nucleo
          LEFT JOIN franja_derecho_via f
            ON f.id_tramo = tn.id_tramo
           AND f.activo = TRUE
         WHERE tn.activo = TRUE
           AND (
               n.geometria_poligono IS NULL
               OR f.id_franja IS NULL
               OR COALESCE(
                   ST_Area(
                       ST_CollectionExtract(
                           ST_Intersection(n.geometria_poligono, f.geometria_poligono),
                           3
                       )::geography
                   ),
                   0
               ) <= 0
           )
    ) THEN
        RAISE EXCEPTION 'Existen relaciones activas sin superficie dentro de la franja';
    END IF;
END;
$$;

CREATE INDEX idx_019_franja_geometria
    ON franja_derecho_via USING GIST (geometria_poligono);

CREATE OR REPLACE FUNCTION fn_019_validar_franja_tramo()
RETURNS TRIGGER AS $$
DECLARE
    v_tramo_activo BOOLEAN;
    v_tramo_geom GEOMETRY;
BEGIN
    IF NEW.activo IS NOT TRUE THEN
        RETURN NEW;
    END IF;

    SELECT activo, geometria_linea
      INTO v_tramo_activo, v_tramo_geom
      FROM tramo
     WHERE id_tramo = NEW.id_tramo
     FOR KEY SHARE;

    IF NOT FOUND OR v_tramo_activo IS NOT TRUE OR v_tramo_geom IS NULL THEN
        RAISE EXCEPTION 'FRANJA_TRAMO_ACTIVO_CON_GEOMETRIA_REQUERIDO';
    END IF;

    IF NOT ST_Intersects(NEW.geometria_poligono, v_tramo_geom) THEN
        RAISE EXCEPTION 'FRANJA_FUERA_DE_TRAZO';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM tramo_nucleo tn
          JOIN nucleo_agrario n ON n.id_nucleo = tn.id_nucleo
         WHERE tn.id_tramo = NEW.id_tramo
           AND tn.activo = TRUE
           AND (
               n.geometria_poligono IS NULL
               OR COALESCE(
                   ST_Area(
                       ST_CollectionExtract(
                           ST_Intersection(n.geometria_poligono, NEW.geometria_poligono),
                           3
                       )::geography
                   ),
                   0
               ) <= 0
           )
    ) THEN
        RAISE EXCEPTION 'FRANJA_ROMPE_RELACIONES_TRAMO_NUCLEO';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_019_franja_coherente
    BEFORE INSERT OR UPDATE OF activo, id_tramo, geometria_poligono
    ON franja_derecho_via
    FOR EACH ROW EXECUTE FUNCTION fn_019_validar_franja_tramo();

CREATE OR REPLACE FUNCTION fn_019_validar_tramo_nucleo_franja()
RETURNS TRIGGER AS $$
DECLARE
    v_franja_geom GEOMETRY;
    v_nucleo_geom GEOMETRY;
BEGIN
    IF NEW.activo IS NOT TRUE THEN
        RETURN NEW;
    END IF;

    SELECT geometria_poligono
      INTO v_franja_geom
      FROM franja_derecho_via
     WHERE id_tramo = NEW.id_tramo
       AND activo = TRUE
     FOR KEY SHARE;

    SELECT geometria_poligono
      INTO v_nucleo_geom
      FROM nucleo_agrario
     WHERE id_nucleo = NEW.id_nucleo
       AND activo = TRUE
     FOR KEY SHARE;

    IF v_franja_geom IS NULL OR v_nucleo_geom IS NULL THEN
        RAISE EXCEPTION 'TRAMO_NUCLEO_FRANJA_Y_GEOMETRIA_REQUERIDAS';
    END IF;

    IF COALESCE(
        ST_Area(
            ST_CollectionExtract(
                ST_Intersection(v_nucleo_geom, v_franja_geom),
                3
            )::geography
        ),
        0
    ) <= 0 THEN
        RAISE EXCEPTION 'TRAMO_NUCLEO_SIN_SUPERFICIE_EN_FRANJA';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_019_tramo_nucleo_en_franja
    BEFORE INSERT OR UPDATE OF activo, id_tramo, id_nucleo
    ON tramo_nucleo
    FOR EACH ROW EXECUTE FUNCTION fn_019_validar_tramo_nucleo_franja();

INSERT INTO schema_migrations (version, descripcion)
VALUES ('019', 'Franja activa como autoridad territorial');

COMMIT;
