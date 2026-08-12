BEGIN;

SELECT pg_advisory_xact_lock(hashtext('software_pa_migration_012'));

DO $$
DECLARE
    v_usuario_tecnico INTEGER;
BEGIN
    IF to_regclass('public.schema_migrations') IS NULL
       OR NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '010')
       OR NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '011') THEN
        RAISE EXCEPTION 'La migracion 012 requiere 010 y 011 aplicadas';
    END IF;

    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '012') THEN
        RAISE EXCEPTION 'La migracion 012 ya fue aplicada';
    END IF;

    IF to_regclass('public.franja_derecho_via') IS NULL
       OR to_regclass('public.tramo') IS NULL
       OR to_regclass('public.afectacion') IS NULL THEN
        RAISE EXCEPTION 'La migracion 012 requiere las tablas de Corte 5';
    END IF;

    SELECT id_usuario
      INTO v_usuario_tecnico
      FROM usuario
     WHERE activo = TRUE
     ORDER BY CASE WHEN rol = 'admin' THEN 0 ELSE 1 END, id_usuario
     LIMIT 1;

    IF v_usuario_tecnico IS NULL THEN
        RAISE EXCEPTION 'La migracion 012 requiere un usuario activo para auditoria';
    END IF;

    PERFORM set_config('app.current_user_id', v_usuario_tecnico::TEXT, TRUE);

    IF EXISTS (
        SELECT 1
          FROM franja_derecho_via
         WHERE version <= 0
            OR ST_IsEmpty(geometria_poligono)
            OR NOT ST_IsValid(geometria_poligono)
            OR ST_SRID(geometria_poligono) <> 4326
            OR GeometryType(geometria_poligono) <> 'MULTIPOLYGON'
    ) THEN
        RAISE EXCEPTION 'Existen franjas con version o geometria invalida; se requiere conciliacion manual';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM franja_derecho_via
         GROUP BY id_tramo, version
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Existen versiones de franja duplicadas; se requiere conciliacion manual';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM franja_derecho_via
         WHERE activo
         GROUP BY id_tramo
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Existe mas de una franja activa por tramo';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM tramo t
         WHERE t.activo
           AND EXISTS (
               SELECT 1 FROM franja_derecho_via f
                WHERE f.id_tramo = t.id_tramo
           )
           AND NOT EXISTS (
               SELECT 1 FROM franja_derecho_via f
                WHERE f.id_tramo = t.id_tramo AND f.activo
           )
    ) THEN
        RAISE EXCEPTION 'Existen tramos activos con historial de franja pero sin version activa';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM tramo t
         WHERE t.activo
           AND NOT EXISTS (
               SELECT 1 FROM franja_derecho_via f
                WHERE f.id_tramo = t.id_tramo AND f.activo
           )
           AND (
               t.geometria_linea IS NULL
               OR ST_IsEmpty(t.geometria_linea)
               OR NOT ST_IsValid(t.geometria_linea)
               OR t.ancho_total_derecho_via_m IS NULL
               OR t.ancho_total_derecho_via_m <= 0
           )
    ) THEN
        RAISE EXCEPTION 'Hay tramos activos sin datos heredados validos para generar la franja inicial';
    END IF;
END;
$$;

ALTER TABLE franja_derecho_via
    ADD CONSTRAINT uq_franja_tramo_version UNIQUE (id_tramo, version),
    ADD CONSTRAINT chk_franja_version_positiva CHECK (version > 0),
    ADD CONSTRAINT chk_franja_geometria_valida CHECK (
        NOT ST_IsEmpty(geometria_poligono)
        AND ST_IsValid(geometria_poligono)
        AND ST_SRID(geometria_poligono) = 4326
        AND GeometryType(geometria_poligono) = 'MULTIPOLYGON'
    ),
    ADD CONSTRAINT fk_franja_usuario_baja
        FOREIGN KEY (id_usuario_baja) REFERENCES usuario(id_usuario),
    ADD CONSTRAINT fk_franja_usuario_reactivacion
        FOREIGN KEY (id_usuario_reactivacion) REFERENCES usuario(id_usuario);

CREATE OR REPLACE FUNCTION fn_c5_validar_version_franja() RETURNS TRIGGER AS $$
DECLARE
    v_version_siguiente INTEGER;
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM pg_advisory_xact_lock(12005, NEW.id_tramo);

        SELECT COALESCE(MAX(version), 0) + 1
          INTO v_version_siguiente
          FROM franja_derecho_via
         WHERE id_tramo = NEW.id_tramo;

        IF NEW.version <> v_version_siguiente
           OR NEW.activo IS NOT TRUE
           OR NEW.fecha_vigencia_fin IS NOT NULL THEN
            RAISE EXCEPTION 'C5_VERSION_FRANJA_INVALIDA';
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.id_tramo <> OLD.id_tramo
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

    IF OLD.activo IS TRUE
       AND NEW.activo IS FALSE
       AND NEW.fecha_vigencia_fin IS NULL THEN
        RAISE EXCEPTION 'C5_FRANJA_INACTIVA_SIN_FIN';
    END IF;

    IF OLD.activo IS FALSE
       AND NEW.fecha_vigencia_fin IS DISTINCT FROM OLD.fecha_vigencia_fin THEN
        RAISE EXCEPTION 'C5_FRANJA_VERSION_INMUTABLE';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_c5_validar_version_franja
    BEFORE INSERT OR UPDATE ON franja_derecho_via
    FOR EACH ROW EXECUTE FUNCTION fn_c5_validar_version_franja();

CREATE TRIGGER trg_audit_franja_derecho_via
    AFTER INSERT OR UPDATE OR DELETE ON franja_derecho_via
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_franja');

CREATE TRIGGER trg_prevent_delete_franja_derecho_via
    BEFORE DELETE ON franja_derecho_via
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();

CREATE TRIGGER trg_baja_logica_franja_derecho_via
    BEFORE UPDATE ON franja_derecho_via
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

INSERT INTO franja_derecho_via (
    id_tramo,
    version,
    ancho_izquierdo_m,
    ancho_derecho_m,
    geometria_poligono,
    fuente,
    fecha_vigencia_inicio,
    activo
)
SELECT
    t.id_tramo,
    1,
    t.ancho_total_derecho_via_m / 2,
    t.ancho_total_derecho_via_m / 2,
    ST_Multi(
        ST_Buffer(
            t.geometria_linea::geography,
            t.ancho_total_derecho_via_m / 2
        )::geometry
    ),
    'Regularizacion correctiva desde bufer heredado',
    t.fecha_registro,
    TRUE
FROM tramo t
WHERE t.activo
  AND NOT EXISTS (
      SELECT 1 FROM franja_derecho_via f WHERE f.id_tramo = t.id_tramo
  );

CREATE OR REPLACE FUNCTION fn_validar_coherencia_espacial() RETURNS TRIGGER AS $$
DECLARE
    v_nucleo_geom GEOMETRY;
    v_franja_geom GEOMETRY;
BEGIN
    IF NEW.origen_registro = 'captura_sistema'
       AND NEW.geometria_afectacion IS NOT NULL THEN
        SELECT geometria_poligono
          INTO v_nucleo_geom
          FROM nucleo_agrario
         WHERE id_nucleo = NEW.id_nucleo
           AND activo = TRUE;

        IF v_nucleo_geom IS NULL
           OR NOT ST_Intersects(NEW.geometria_afectacion, v_nucleo_geom) THEN
            RAISE EXCEPTION 'La afectacion no intersecta con su nucleo agrario';
        END IF;

        SELECT f.geometria_poligono
          INTO v_franja_geom
          FROM tramo_nucleo tn
          JOIN franja_derecho_via f
            ON f.id_tramo = tn.id_tramo
           AND f.activo = TRUE
         WHERE tn.id_tramo_nucleo = NEW.id_tramo_nucleo
           AND tn.activo = TRUE;

        IF v_franja_geom IS NULL THEN
            RAISE EXCEPTION 'C5_FRANJA_ACTIVA_REQUERIDA';
        END IF;

        IF NOT ST_Intersects(NEW.geometria_afectacion, v_franja_geom) THEN
            RAISE EXCEPTION 'C5_AFECTACION_FUERA_FRANJA';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
          FROM tramo t
         WHERE t.activo
           AND NOT EXISTS (
               SELECT 1 FROM franja_derecho_via f
                WHERE f.id_tramo = t.id_tramo AND f.activo
           )
    ) THEN
        RAISE EXCEPTION 'La regularizacion no dejo una franja activa por tramo activo';
    END IF;
END;
$$;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('012', 'Regularizacion correctiva de Corte 5');

COMMIT;
