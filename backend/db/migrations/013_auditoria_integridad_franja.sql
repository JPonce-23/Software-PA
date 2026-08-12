BEGIN;

SELECT pg_advisory_xact_lock(hashtext('schema_migration_013'));

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '012') THEN
        RAISE EXCEPTION 'La migracion 012 es requisito para aplicar 013';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '013') THEN
        RAISE EXCEPTION 'La migracion 013 ya fue aplicada';
    END IF;
    IF to_regclass('public.franja_derecho_via') IS NULL THEN
        RAISE EXCEPTION 'No existe franja_derecho_via';
    END IF;
END;
$$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
          FROM franja_derecho_via
         WHERE btrim(fuente) = ''
    ) THEN
        RAISE EXCEPTION 'Existen franjas con fuente vacia';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM (
              SELECT fecha_vigencia_inicio,
                     lag(fecha_vigencia_inicio) OVER (
                         PARTITION BY id_tramo ORDER BY version
                     ) AS fecha_anterior
                FROM franja_derecho_via
          ) versiones
         WHERE fecha_anterior IS NOT NULL
           AND fecha_vigencia_inicio < fecha_anterior
    ) THEN
        RAISE EXCEPTION 'Existen versiones de franja fuera de orden cronologico';
    END IF;
END;
$$;

ALTER TABLE franja_derecho_via
    ADD CONSTRAINT chk_franja_fuente_no_vacia CHECK (btrim(fuente) <> '');

CREATE OR REPLACE FUNCTION fn_c5_validar_version_franja() RETURNS TRIGGER AS $$
DECLARE
    v_version_siguiente INTEGER;
    v_fecha_ultima DATE;
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM pg_advisory_xact_lock(12005, NEW.id_tramo);

        SELECT COALESCE(MAX(version), 0) + 1,
               (array_agg(fecha_vigencia_inicio ORDER BY version DESC))[1]
          INTO v_version_siguiente, v_fecha_ultima
          FROM franja_derecho_via
         WHERE id_tramo = NEW.id_tramo;

        IF NEW.version <> v_version_siguiente
           OR NEW.activo IS NOT TRUE
           OR NEW.fecha_vigencia_fin IS NOT NULL
           OR (v_fecha_ultima IS NOT NULL
               AND NEW.fecha_vigencia_inicio < v_fecha_ultima) THEN
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

INSERT INTO schema_migrations (version, descripcion)
VALUES ('013', 'Auditoria de integridad temporal de franjas');

COMMIT;
