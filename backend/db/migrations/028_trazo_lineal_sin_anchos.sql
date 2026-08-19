-- El trazo ferroviario es un eje lineal. La superficie operativa se carga
-- explícitamente por tramo en seccion_derecho_via; no se infiere con anchos.

BEGIN;

SELECT pg_advisory_xact_lock(20260817, 28);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '027') THEN
        RAISE EXCEPTION 'La migracion 028 requiere la migracion 027 aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '028') THEN
        RAISE EXCEPTION 'La migracion 028 ya fue aplicada';
    END IF;
END;
$$;

ALTER TABLE franja_derecho_via
    ADD COLUMN geometria_linea geometry(MULTILINESTRING, 4326);
ALTER TABLE franja_derecho_via
    ALTER COLUMN geometria_poligono DROP NOT NULL;
ALTER TABLE franja_derecho_via
    DROP CONSTRAINT chk_franja_anchos_positivos,
    DROP CONSTRAINT chk_franja_geometria_valida;
ALTER TABLE franja_derecho_via
    ADD CONSTRAINT chk_028_franja_geometria_exclusiva CHECK (
        (
            geometria_linea IS NOT NULL
            AND geometria_poligono IS NULL
            AND NOT ST_IsEmpty(geometria_linea)
            AND ST_IsValid(geometria_linea)
            AND ST_SRID(geometria_linea) = 4326
            AND GeometryType(geometria_linea) = 'MULTILINESTRING'
        ) OR (
            geometria_linea IS NULL
            AND geometria_poligono IS NOT NULL
            AND NOT ST_IsEmpty(geometria_poligono)
            AND ST_IsValid(geometria_poligono)
            AND ST_SRID(geometria_poligono) = 4326
            AND GeometryType(geometria_poligono) = 'MULTIPOLYGON'
        )
    );
CREATE INDEX idx_028_franja_geometria_linea
    ON franja_derecho_via USING GIST (geometria_linea);

CREATE OR REPLACE FUNCTION fn_c5_validar_version_franja() RETURNS TRIGGER AS $$
DECLARE
    v_version_siguiente INTEGER;
    v_fecha_ultima DATE;
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM pg_advisory_xact_lock(12005, NEW.id_proyecto);
        SELECT COALESCE(MAX(version), 0) + 1,
               (array_agg(fecha_vigencia_inicio ORDER BY version DESC))[1]
          INTO v_version_siguiente, v_fecha_ultima
          FROM franja_derecho_via
         WHERE id_proyecto = NEW.id_proyecto;
        IF NEW.version <> v_version_siguiente
           OR NEW.activo IS NOT TRUE
           OR NEW.fecha_vigencia_fin IS NOT NULL
           OR (v_fecha_ultima IS NOT NULL AND NEW.fecha_vigencia_inicio < v_fecha_ultima) THEN
            RAISE EXCEPTION 'C5_VERSION_FRANJA_INVALIDA';
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.id_proyecto <> OLD.id_proyecto
       OR NEW.version <> OLD.version
       OR NEW.geometria_linea IS DISTINCT FROM OLD.geometria_linea
       OR NEW.geometria_poligono IS DISTINCT FROM OLD.geometria_poligono
       OR NEW.fuente <> OLD.fuente
       OR NEW.fecha_vigencia_inicio <> OLD.fecha_vigencia_inicio
       OR NEW.ancho_izquierdo_m IS DISTINCT FROM OLD.ancho_izquierdo_m
       OR NEW.ancho_derecho_m IS DISTINCT FROM OLD.ancho_derecho_m THEN
        RAISE EXCEPTION 'C5_FRANJA_VERSION_INMUTABLE';
    END IF;
    IF OLD.activo IS FALSE AND NEW.activo IS TRUE THEN
        RAISE EXCEPTION 'C5_FRANJA_NO_REACTIVABLE';
    END IF;
    IF NEW.activo IS TRUE AND NEW.fecha_vigencia_fin IS NOT NULL THEN
        RAISE EXCEPTION 'C5_FRANJA_ACTIVA_CON_FIN';
    END IF;
    IF OLD.activo IS TRUE AND NEW.activo IS FALSE AND NEW.fecha_vigencia_fin IS NULL THEN
        RAISE EXCEPTION 'C5_FRANJA_INACTIVA_SIN_FIN';
    END IF;
    IF OLD.activo IS FALSE AND NEW.fecha_vigencia_fin IS DISTINCT FROM OLD.fecha_vigencia_fin THEN
        RAISE EXCEPTION 'C5_FRANJA_VERSION_INMUTABLE';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER trg_019_franja_coherente ON franja_derecho_via;
CREATE TRIGGER trg_019_franja_coherente
    BEFORE INSERT OR UPDATE OF activo, id_proyecto, id_tramo, geometria_linea, geometria_poligono
    ON franja_derecho_via
    FOR EACH ROW EXECUTE FUNCTION fn_019_validar_franja_tramo();

CREATE OR REPLACE FUNCTION fn_026_validar_seccion_derecho_via()
RETURNS TRIGGER AS $$
DECLARE
    v_franja_linea GEOMETRY;
    v_franja_poligono GEOMETRY;
    v_proyecto_franja INTEGER;
    v_proyecto_tramo INTEGER;
    v_franja_activa BOOLEAN;
    v_tramo_activo BOOLEAN;
BEGIN
    IF NEW.activo IS NOT TRUE THEN RETURN NEW; END IF;
    SELECT geometria_linea, geometria_poligono, id_proyecto, activo
      INTO v_franja_linea, v_franja_poligono, v_proyecto_franja, v_franja_activa
      FROM franja_derecho_via WHERE id_franja = NEW.id_franja FOR KEY SHARE;
    SELECT id_proyecto, activo INTO v_proyecto_tramo, v_tramo_activo
      FROM tramo WHERE id_tramo = NEW.id_tramo FOR KEY SHARE;
    IF NOT FOUND OR v_franja_activa IS NOT TRUE OR v_tramo_activo IS NOT TRUE OR v_proyecto_franja <> v_proyecto_tramo THEN
        RAISE EXCEPTION 'SECCION_FUERA_DE_PROYECTO_O_INACTIVA';
    END IF;
    IF v_franja_linea IS NOT NULL AND NOT ST_Intersects(NEW.geometria_poligono, v_franja_linea) THEN
        RAISE EXCEPTION 'SECCION_SIN_INTERSECCION_CON_EJE';
    ELSIF v_franja_poligono IS NOT NULL
          AND COALESCE(ST_Area(ST_CollectionExtract(ST_Intersection(NEW.geometria_poligono, v_franja_poligono), 3)::geography), 0) <= 0 THEN
        RAISE EXCEPTION 'SECCION_SIN_SUPERFICIE_EN_TRAZO';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('028', 'Trazo lineal sin inferencia de ancho y secciones espaciales explicitas');

COMMIT;
