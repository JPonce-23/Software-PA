-- Trazo oficial por proyecto y secciones espaciales por tramo.
-- Transición expansiva: tramo.geometria_linea e id_tramo en franja se conservan
-- como legado, pero dejan de ser dependencias operativas.

BEGIN;

SELECT pg_advisory_xact_lock(20260817, 26);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '025') THEN
        RAISE EXCEPTION 'La migracion 026 requiere la migracion 025 aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '026') THEN
        RAISE EXCEPTION 'La migracion 026 ya fue aplicada';
    END IF;
END;
$$;

ALTER TABLE franja_derecho_via
    ADD COLUMN id_proyecto INTEGER;

UPDATE franja_derecho_via f
   SET id_proyecto = t.id_proyecto
  FROM tramo t
 WHERE f.id_tramo = t.id_tramo
   AND f.id_proyecto IS NULL;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM franja_derecho_via WHERE id_proyecto IS NULL) THEN
        RAISE EXCEPTION 'Existen franjas sin proyecto resoluble desde su tramo legado';
    END IF;
END;
$$;

ALTER TABLE franja_derecho_via
    ADD CONSTRAINT fk_026_franja_proyecto
    FOREIGN KEY (id_proyecto) REFERENCES proyecto(id_proyecto);
ALTER TABLE franja_derecho_via
    ALTER COLUMN id_proyecto SET NOT NULL,
    ALTER COLUMN id_tramo DROP NOT NULL;

-- El ancho y la línea pertenecían al modelo de franja derivada. Se conservan
-- los datos históricos, pero los tramos nuevos ya no reciben un ancho implícito.
ALTER TABLE tramo ALTER COLUMN ancho_total_derecho_via_m DROP DEFAULT;

DROP INDEX uq_tramo_franja_activa;
ALTER TABLE franja_derecho_via DROP CONSTRAINT uq_franja_tramo_version;
ALTER TABLE franja_derecho_via
    ADD CONSTRAINT uq_026_franja_proyecto_version UNIQUE (id_proyecto, version);
CREATE UNIQUE INDEX uq_026_proyecto_franja_activa
    ON franja_derecho_via (id_proyecto) WHERE activo = TRUE;
CREATE INDEX idx_026_franja_proyecto_activa
    ON franja_derecho_via (id_proyecto, activo);

ALTER TABLE carga_geoespacial DROP CONSTRAINT carga_geoespacial_tipo_objetivo_check;
ALTER TABLE carga_geoespacial
    ADD CONSTRAINT chk_026_carga_tipo_objetivo CHECK (
        tipo_objetivo IN ('tramo', 'franja_derecho_via', 'seccion_derecho_via', 'nucleo_agrario', 'parcela')
    );

CREATE TABLE seccion_derecho_via (
    id_seccion BIGSERIAL PRIMARY KEY,
    id_franja INTEGER NOT NULL REFERENCES franja_derecho_via(id_franja),
    id_tramo INTEGER NOT NULL REFERENCES tramo(id_tramo),
    geometria_poligono geometry(MULTIPOLYGON, 4326) NOT NULL,
    fuente VARCHAR(200) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_registro TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    fecha_baja TIMESTAMP WITH TIME ZONE,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja VARCHAR(500),
    fecha_reactivacion TIMESTAMP WITH TIME ZONE,
    id_usuario_reactivacion INTEGER REFERENCES usuario(id_usuario),
    motivo_reactivacion VARCHAR(500),
    observaciones VARCHAR(500),
    CONSTRAINT uq_026_seccion_franja_tramo UNIQUE (id_franja, id_tramo),
    CONSTRAINT chk_026_seccion_fuente CHECK (btrim(fuente) <> ''),
    CONSTRAINT chk_026_seccion_geometria CHECK (
        NOT ST_IsEmpty(geometria_poligono)
        AND ST_IsValid(geometria_poligono)
        AND ST_SRID(geometria_poligono) = 4326
        AND GeometryType(geometria_poligono) = 'MULTIPOLYGON'
    )
);
CREATE INDEX idx_026_seccion_geometria
    ON seccion_derecho_via USING GIST (geometria_poligono);
CREATE UNIQUE INDEX uq_026_seccion_tramo_activa
    ON seccion_derecho_via (id_tramo) WHERE activo = TRUE;

CREATE TRIGGER trg_audit_seccion_derecho_via
    AFTER INSERT OR UPDATE ON seccion_derecho_via
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_seccion');
CREATE TRIGGER trg_prevent_delete_seccion_derecho_via
    BEFORE DELETE ON seccion_derecho_via
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_seccion_derecho_via
    BEFORE UPDATE OF activo ON seccion_derecho_via
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

ALTER TABLE candidato_tramo_nucleo
    ADD COLUMN id_seccion BIGINT REFERENCES seccion_derecho_via(id_seccion);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM candidato_tramo_nucleo) THEN
        RAISE EXCEPTION 'La migracion 026 requiere migrar candidatos existentes de forma controlada';
    END IF;
END;
$$;

ALTER TABLE candidato_tramo_nucleo
    ALTER COLUMN id_seccion SET NOT NULL;
ALTER TABLE candidato_tramo_nucleo
    DROP CONSTRAINT uq_025_candidato_franja_nucleo;
ALTER TABLE candidato_tramo_nucleo
    ADD CONSTRAINT uq_026_candidato_seccion_nucleo UNIQUE (id_seccion, id_nucleo);

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

CREATE OR REPLACE FUNCTION fn_019_validar_franja_tramo()
RETURNS TRIGGER AS $$
DECLARE v_proyecto_activo BOOLEAN;
BEGIN
    IF NEW.activo IS NOT TRUE THEN RETURN NEW; END IF;
    SELECT activo INTO v_proyecto_activo FROM proyecto
     WHERE id_proyecto = NEW.id_proyecto FOR KEY SHARE;
    IF NOT FOUND OR v_proyecto_activo IS NOT TRUE THEN
        RAISE EXCEPTION 'FRANJA_PROYECTO_ACTIVO_REQUERIDO';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER trg_019_franja_coherente ON franja_derecho_via;
CREATE TRIGGER trg_019_franja_coherente
    BEFORE INSERT OR UPDATE OF activo, id_proyecto, id_tramo, geometria_poligono
    ON franja_derecho_via
    FOR EACH ROW EXECUTE FUNCTION fn_019_validar_franja_tramo();

DROP TRIGGER trg_015_franja_padre_activo ON franja_derecho_via;
CREATE TRIGGER trg_015_franja_padre_activo
    BEFORE INSERT OR UPDATE OF activo, id_proyecto, id_tramo ON franja_derecho_via
    FOR EACH ROW EXECUTE FUNCTION fn_015_validar_hijo_activo();

CREATE OR REPLACE FUNCTION fn_026_validar_seccion_derecho_via()
RETURNS TRIGGER AS $$
DECLARE v_franja_geom GEOMETRY; v_proyecto_franja INTEGER; v_proyecto_tramo INTEGER; v_franja_activa BOOLEAN; v_tramo_activo BOOLEAN;
BEGIN
    IF NEW.activo IS NOT TRUE THEN RETURN NEW; END IF;
    SELECT geometria_poligono, id_proyecto, activo INTO v_franja_geom, v_proyecto_franja, v_franja_activa
      FROM franja_derecho_via WHERE id_franja = NEW.id_franja FOR KEY SHARE;
    SELECT id_proyecto, activo INTO v_proyecto_tramo, v_tramo_activo
      FROM tramo WHERE id_tramo = NEW.id_tramo FOR KEY SHARE;
    IF NOT FOUND OR v_franja_activa IS NOT TRUE OR v_tramo_activo IS NOT TRUE OR v_proyecto_franja <> v_proyecto_tramo THEN
        RAISE EXCEPTION 'SECCION_FUERA_DE_PROYECTO_O_INACTIVA';
    END IF;
    IF COALESCE(ST_Area(ST_CollectionExtract(ST_Intersection(NEW.geometria_poligono, v_franja_geom), 3)::geography), 0) <= 0 THEN
        RAISE EXCEPTION 'SECCION_SIN_SUPERFICIE_EN_TRAZO';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_026_seccion_coherente
    BEFORE INSERT OR UPDATE OF activo, id_franja, id_tramo, geometria_poligono
    ON seccion_derecho_via FOR EACH ROW EXECUTE FUNCTION fn_026_validar_seccion_derecho_via();

CREATE OR REPLACE FUNCTION fn_019_validar_tramo_nucleo_franja()
RETURNS TRIGGER AS $$
DECLARE v_seccion_geom GEOMETRY; v_nucleo_geom GEOMETRY;
BEGIN
    IF NEW.activo IS NOT TRUE THEN RETURN NEW; END IF;
    SELECT s.geometria_poligono INTO v_seccion_geom
      FROM seccion_derecho_via s JOIN franja_derecho_via f ON f.id_franja = s.id_franja
     WHERE s.id_tramo = NEW.id_tramo AND s.activo = TRUE AND f.activo = TRUE FOR KEY SHARE;
    SELECT geometria_poligono INTO v_nucleo_geom FROM nucleo_agrario
     WHERE id_nucleo = NEW.id_nucleo AND activo = TRUE FOR KEY SHARE;
    IF v_seccion_geom IS NULL OR v_nucleo_geom IS NULL THEN
        RAISE EXCEPTION 'TRAMO_NUCLEO_SECCION_Y_GEOMETRIA_REQUERIDAS';
    END IF;
    IF COALESCE(ST_Area(ST_CollectionExtract(ST_Intersection(v_nucleo_geom, v_seccion_geom), 3)::geography), 0) <= 0 THEN
        RAISE EXCEPTION 'TRAMO_NUCLEO_SIN_SUPERFICIE_EN_SECCION';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Las afectaciones pertenecen al expediente de un tramo. Por tanto se validan
-- contra la sección vigente de ese tramo, no contra una línea o ancho legado.
CREATE OR REPLACE FUNCTION fn_validar_coherencia_espacial() RETURNS TRIGGER AS $$
DECLARE v_nucleo_geom GEOMETRY; v_seccion_geom GEOMETRY;
BEGIN
    IF NEW.origen_registro = 'captura_sistema' AND NEW.geometria_afectacion IS NOT NULL THEN
        SELECT geometria_poligono INTO v_nucleo_geom
          FROM nucleo_agrario
         WHERE id_nucleo = NEW.id_nucleo AND activo = TRUE;
        IF v_nucleo_geom IS NULL OR NOT ST_Intersects(NEW.geometria_afectacion, v_nucleo_geom) THEN
            RAISE EXCEPTION 'La afectacion no intersecta con su nucleo agrario';
        END IF;

        SELECT s.geometria_poligono INTO v_seccion_geom
          FROM tramo_nucleo tn
          JOIN seccion_derecho_via s ON s.id_tramo = tn.id_tramo AND s.activo = TRUE
          JOIN franja_derecho_via f ON f.id_franja = s.id_franja AND f.activo = TRUE
         WHERE tn.id_tramo_nucleo = NEW.id_tramo_nucleo AND tn.activo = TRUE
         FOR KEY SHARE;
        IF v_seccion_geom IS NULL THEN
            RAISE EXCEPTION 'C5_SECCION_ACTIVA_REQUERIDA';
        END IF;
        IF NOT ST_Intersects(NEW.geometria_afectacion, v_seccion_geom) THEN
            RAISE EXCEPTION 'C5_AFECTACION_FUERA_SECCION';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_015_validar_hijo_activo() RETURNS TRIGGER AS $$
DECLARE v_padre_activo BOOLEAN; v_otro_padre_activo BOOLEAN;
BEGIN
    IF NEW.activo IS NOT TRUE THEN RETURN NEW; END IF;
    IF TG_TABLE_NAME = 'tramo' THEN
        SELECT activo INTO v_padre_activo FROM proyecto WHERE id_proyecto = NEW.id_proyecto FOR KEY SHARE;
    ELSIF TG_TABLE_NAME = 'franja_derecho_via' THEN
        SELECT activo INTO v_padre_activo FROM proyecto WHERE id_proyecto = NEW.id_proyecto FOR KEY SHARE;
    ELSIF TG_TABLE_NAME = 'usuario_tramo' THEN
        SELECT activo INTO v_padre_activo FROM usuario WHERE id_usuario = NEW.id_usuario FOR KEY SHARE;
        SELECT activo INTO v_otro_padre_activo FROM tramo WHERE id_tramo = NEW.id_tramo FOR KEY SHARE;
    ELSIF TG_TABLE_NAME = 'tramo_nucleo' THEN
        SELECT activo INTO v_padre_activo FROM tramo WHERE id_tramo = NEW.id_tramo FOR KEY SHARE;
        SELECT activo INTO v_otro_padre_activo FROM nucleo_agrario WHERE id_nucleo = NEW.id_nucleo FOR KEY SHARE;
    END IF;
    IF v_padre_activo IS NOT TRUE OR (TG_TABLE_NAME IN ('usuario_tramo', 'tramo_nucleo') AND v_otro_padre_activo IS NOT TRUE) THEN
        RAISE EXCEPTION 'ADM_PADRE_INACTIVO';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_015_validar_geometria_padre() RETURNS TRIGGER AS $$
BEGIN
    IF TG_TABLE_NAME = 'nucleo_agrario' AND NEW.geometria_poligono IS DISTINCT FROM OLD.geometria_poligono
       AND EXISTS (SELECT 1 FROM tramo_nucleo tn WHERE tn.id_nucleo = NEW.id_nucleo AND tn.activo AND tn.geometria_segmento IS NOT NULL AND NEW.geometria_poligono IS NOT NULL AND NOT ST_Intersects(tn.geometria_segmento, NEW.geometria_poligono)) THEN
        RAISE EXCEPTION 'ADM_GEOMETRIA_NUCLEO_ROMPE_RELACIONES';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('026', 'Trazo ferroviario por proyecto y secciones espaciales por tramo');

COMMIT;
