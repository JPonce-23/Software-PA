-- ============================================================
-- MIGRACION 017: Importacion territorial GeoJSON
-- Fecha: 2026-08-12
--
-- Estrategia: EXPAND.
--   * Agrega geometria opcional a parcela para soportar importacion GeoJSON.
--   * Protege validez espacial basica en PostgreSQL/PostGIS.
--   * Evita duplicados activos de cruces operativos tramo-nucleo.
--   * No elimina columnas ni datos existentes.
--
-- Requisitos:
--   * La migracion 016 debe estar aplicada.
--   * Ejecutar una sola vez con ON_ERROR_STOP habilitado.
-- ============================================================

BEGIN;

SELECT pg_advisory_xact_lock(20260812, 17);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '016') THEN
        RAISE EXCEPTION 'La migracion 017 requiere que la migracion 016 este aplicada';
    END IF;

    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '017') THEN
        RAISE EXCEPTION 'La migracion 017 ya fue aplicada';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM tramo_nucleo
         WHERE activo = TRUE
         GROUP BY id_tramo, id_nucleo
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Existen cruces operativos activos duplicados por tramo y nucleo; se requiere conciliacion manual';
    END IF;
END;
$$;

ALTER TABLE parcela
    ADD COLUMN IF NOT EXISTS geometria_poligono geometry(MultiPolygon, 4326);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'chk_017_parcela_geometria_valida'
           AND conrelid = 'parcela'::regclass
    ) THEN
        ALTER TABLE parcela
            ADD CONSTRAINT chk_017_parcela_geometria_valida CHECK (
                geometria_poligono IS NULL OR (
                    NOT ST_IsEmpty(geometria_poligono)
                    AND ST_IsValid(geometria_poligono)
                    AND ST_SRID(geometria_poligono) = 4326
                    AND GeometryType(geometria_poligono) = 'MULTIPOLYGON'
                )
            );
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_017_parcela_geometria
    ON parcela USING GIST (geometria_poligono);

CREATE UNIQUE INDEX IF NOT EXISTS uq_017_tramo_nucleo_activo
    ON tramo_nucleo (id_tramo, id_nucleo)
    WHERE activo = TRUE;

CREATE OR REPLACE FUNCTION fn_017_validar_parcela_geometria_nucleo()
RETURNS TRIGGER AS $$
DECLARE
    v_nucleo_activo BOOLEAN;
    v_nucleo_geom GEOMETRY;
BEGIN
    IF NEW.activo IS TRUE AND NEW.geometria_poligono IS NOT NULL THEN
        SELECT activo, geometria_poligono
          INTO v_nucleo_activo, v_nucleo_geom
          FROM nucleo_agrario
         WHERE id_nucleo = NEW.id_nucleo
         FOR KEY SHARE;

        IF NOT FOUND OR v_nucleo_activo IS NOT TRUE THEN
            RAISE EXCEPTION 'La parcela requiere un nucleo agrario activo';
        END IF;

        IF v_nucleo_geom IS NOT NULL
           AND NOT ST_Intersects(NEW.geometria_poligono, v_nucleo_geom) THEN
            RAISE EXCEPTION 'La geometria de la parcela no intersecta con su nucleo agrario';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_017_parcela_geometria_nucleo ON parcela;
CREATE TRIGGER trg_017_parcela_geometria_nucleo
    BEFORE INSERT OR UPDATE OF id_nucleo, geometria_poligono, activo ON parcela
    FOR EACH ROW EXECUTE FUNCTION fn_017_validar_parcela_geometria_nucleo();

CREATE OR REPLACE FUNCTION fn_017_validar_nucleo_parcelas()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.activo IS FALSE AND EXISTS (
        SELECT 1 FROM parcela
         WHERE id_nucleo = NEW.id_nucleo
           AND activo = TRUE
    ) THEN
        RAISE EXCEPTION 'No se puede inactivar un nucleo agrario con parcelas activas';
    END IF;

    IF NEW.geometria_poligono IS NOT NULL AND EXISTS (
        SELECT 1
          FROM parcela p
         WHERE p.id_nucleo = NEW.id_nucleo
           AND p.activo = TRUE
           AND p.geometria_poligono IS NOT NULL
           AND NOT ST_Intersects(p.geometria_poligono, NEW.geometria_poligono)
    ) THEN
        RAISE EXCEPTION 'La geometria del nucleo dejaria parcelas activas fuera de su territorio';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_017_nucleo_parcelas ON nucleo_agrario;
CREATE TRIGGER trg_017_nucleo_parcelas
    BEFORE UPDATE OF activo, geometria_poligono ON nucleo_agrario
    FOR EACH ROW EXECUTE FUNCTION fn_017_validar_nucleo_parcelas();

INSERT INTO schema_migrations (version, descripcion)
VALUES ('017', 'Importacion territorial GeoJSON');

COMMIT;
