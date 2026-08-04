-- ============================================================
-- MIGRACION 007: Subcorte 2C - navegacion por afectacion y
-- aislamiento documental.
-- Estrategia EXPAND: no elimina datos ni infiere relaciones historicas.
-- ============================================================

BEGIN;

SELECT pg_advisory_xact_lock(20260804, 7);

DO $$
DECLARE
    v_usuario_tecnico INTEGER;
    v_constraint RECORD;
BEGIN
    IF to_regclass('public.schema_migrations') IS NULL
       OR NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '006') THEN
        RAISE EXCEPTION 'La migracion 007 requiere la migracion 006 aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '007') THEN
        RAISE EXCEPTION 'La migracion 007 ya fue aplicada';
    END IF;

    SELECT id_usuario INTO v_usuario_tecnico
      FROM usuario
     WHERE activo = TRUE
     ORDER BY CASE WHEN rol = 'admin' THEN 0 ELSE 1 END, id_usuario
     LIMIT 1;
    IF v_usuario_tecnico IS NULL THEN
        RAISE EXCEPTION 'La migracion 007 requiere un usuario activo para auditoria';
    END IF;
    PERFORM set_config('app.current_user_id', v_usuario_tecnico::TEXT, TRUE);

    IF EXISTS (
        SELECT 1
          FROM documentacion_soporte
         WHERE entidad_relacionada_tipo NOT IN (
             'nucleo_agrario', 'tramo_nucleo', 'afectacion', 'convenio', 'orv'
         )
    ) THEN
        RAISE EXCEPTION 'Existen documentos con tipo de entidad no reconocido';
    END IF;

    FOR v_constraint IN
        SELECT conname
          FROM pg_constraint
         WHERE conrelid = 'documentacion_soporte'::regclass
           AND contype = 'c'
           AND pg_get_constraintdef(oid) ILIKE '%entidad_relacionada_tipo%'
    LOOP
        EXECUTE format(
            'ALTER TABLE documentacion_soporte DROP CONSTRAINT %I',
            v_constraint.conname
        );
    END LOOP;
END;
$$;

ALTER TABLE documentacion_soporte
    ADD CONSTRAINT chk_2c_documentacion_entidad_tipo CHECK (
        entidad_relacionada_tipo IN (
            'nucleo_agrario', 'tramo_nucleo', 'afectacion', 'convenio', 'orv'
        )
    );

CREATE OR REPLACE FUNCTION fn_validar_documentacion_soporte_referencia()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.entidad_relacionada_tipo = 'nucleo_agrario' THEN
        IF NOT EXISTS (
            SELECT 1 FROM nucleo_agrario
             WHERE id_nucleo = NEW.entidad_relacionada_id
               AND activo = TRUE
        ) THEN
            RAISE EXCEPTION 'La documentacion soporte referencia un nucleo agrario inexistente o inactivo';
        END IF;
    ELSIF NEW.entidad_relacionada_tipo = 'tramo_nucleo' THEN
        IF NOT EXISTS (
            SELECT 1 FROM tramo_nucleo
             WHERE id_tramo_nucleo = NEW.entidad_relacionada_id
               AND activo = TRUE
        ) THEN
            RAISE EXCEPTION 'La documentacion soporte referencia un expediente tramo-nucleo inexistente o inactivo';
        END IF;
    ELSIF NEW.entidad_relacionada_tipo = 'afectacion' THEN
        IF NOT EXISTS (
            SELECT 1 FROM afectacion
             WHERE id_afectacion = NEW.entidad_relacionada_id
               AND activo = TRUE
        ) THEN
            RAISE EXCEPTION 'La documentacion soporte referencia una afectacion inexistente o inactiva';
        END IF;
    ELSIF NEW.entidad_relacionada_tipo = 'convenio' THEN
        IF NOT EXISTS (
            SELECT 1 FROM convenio
             WHERE id_convenio = NEW.entidad_relacionada_id
               AND activo = TRUE
        ) THEN
            RAISE EXCEPTION 'La documentacion soporte referencia un convenio inexistente o inactivo';
        END IF;
    ELSIF NEW.entidad_relacionada_tipo = 'orv' THEN
        IF NOT EXISTS (
            SELECT 1 FROM orv
             WHERE id_orv = NEW.entidad_relacionada_id
               AND activo = TRUE
        ) THEN
            RAISE EXCEPTION 'La documentacion soporte referencia un ORV inexistente o inactivo';
        END IF;
    ELSE
        RAISE EXCEPTION 'Tipo de entidad documental no reconocido';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

ALTER TABLE minuta
    ADD COLUMN id_afectacion INTEGER,
    ADD COLUMN id_ciclo_afectacion INTEGER,
    ADD CONSTRAINT chk_2c_minuta_afectacion_ciclo_completos CHECK (
        (id_afectacion IS NULL AND id_ciclo_afectacion IS NULL)
        OR
        (id_afectacion IS NOT NULL AND id_ciclo_afectacion IS NOT NULL)
    ),
    ADD CONSTRAINT fk_2c_minuta_ciclo
        FOREIGN KEY (id_tramo_nucleo, id_ciclo_afectacion, id_afectacion)
        REFERENCES afectacion_ciclo(
            id_tramo_nucleo, id_ciclo_afectacion, id_afectacion
        );

CREATE OR REPLACE FUNCTION fn_2c_validar_minuta_afectacion()
RETURNS TRIGGER AS $$
DECLARE
    v_actividad actividad_campo%ROWTYPE;
BEGIN
    IF (NEW.id_afectacion IS NULL) <> (NEW.id_ciclo_afectacion IS NULL) THEN
        RAISE EXCEPTION 'La minuta propia requiere afectacion y ciclo completos';
    END IF;

    IF NEW.id_actividad IS NOT NULL THEN
        SELECT * INTO v_actividad
          FROM actividad_campo
         WHERE id_actividad = NEW.id_actividad
           AND id_tramo_nucleo = NEW.id_tramo_nucleo
           AND activo = TRUE;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'La actividad de la minuta no existe o no pertenece al expediente';
        END IF;

        IF NEW.id_ciclo_afectacion IS NULL
           AND v_actividad.id_ciclo_afectacion IS NOT NULL THEN
            RAISE EXCEPTION 'Una minuta compartida no puede apuntar a una actividad propia de ciclo';
        END IF;

        IF NEW.id_ciclo_afectacion IS NOT NULL
           AND v_actividad.id_ciclo_afectacion IS DISTINCT FROM NEW.id_ciclo_afectacion THEN
            RAISE EXCEPTION 'La actividad de la minuta no pertenece al ciclo indicado';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_2c_validar_minuta_afectacion
    BEFORE INSERT OR UPDATE OF id_tramo_nucleo, id_actividad, id_afectacion,
        id_ciclo_afectacion
    ON minuta
    FOR EACH ROW EXECUTE FUNCTION fn_2c_validar_minuta_afectacion();

CREATE INDEX idx_2c_documentacion_tipo_id
    ON documentacion_soporte(entidad_relacionada_tipo, entidad_relacionada_id)
    WHERE activo = TRUE;
CREATE INDEX idx_2c_minuta_afectacion
    ON minuta(id_afectacion)
    WHERE activo = TRUE AND id_afectacion IS NOT NULL;
CREATE INDEX idx_2c_minuta_ciclo
    ON minuta(id_ciclo_afectacion)
    WHERE activo = TRUE AND id_ciclo_afectacion IS NOT NULL;

INSERT INTO schema_migrations(version, descripcion)
VALUES ('007', 'Subcorte 2C: navegacion por afectacion y aislamiento documental');

COMMIT;
