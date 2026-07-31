-- ============================================================
-- MIGRACIÓN 005: Integridad de afectaciones colectivas e individuales
-- Subcorte 2A
--
-- Estrategia: EXPAND. No reclasifica ni corrige datos existentes.
-- Si encuentra inconsistencias, aborta sin cambiar datos ni esquema.
-- Ejecutar una sola vez con ON_ERROR_STOP habilitado.
-- ============================================================

BEGIN;

SELECT pg_advisory_xact_lock(20260731, 5);

DO $$
DECLARE
    v_usuario_tecnico INTEGER;
BEGIN
    IF to_regclass('public.schema_migrations') IS NULL
       OR NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '004')
       OR to_regclass('public.parcela_titular') IS NULL THEN
        RAISE EXCEPTION 'La migración 005 requiere la migración 004 aplicada';
    END IF;

    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '005') THEN
        RAISE EXCEPTION 'La migración 005 ya fue aplicada';
    END IF;

    SELECT id_usuario
      INTO v_usuario_tecnico
      FROM usuario
     WHERE activo = TRUE
     ORDER BY CASE WHEN rol = 'admin' THEN 0 ELSE 1 END, id_usuario
     LIMIT 1;

    IF v_usuario_tecnico IS NULL THEN
        RAISE EXCEPTION 'La migración 005 requiere un usuario activo para la auditoría';
    END IF;

    PERFORM set_config('app.current_user_id', v_usuario_tecnico::TEXT, TRUE);
END;
$$;

-- No se debe inferir, corregir ni reclasificar información histórica.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
          FROM afectacion
         WHERE (tipo_afectacion = 'colectivo' AND id_parcela IS NOT NULL)
            OR (tipo_afectacion = 'individual' AND id_parcela IS NULL)
    ) THEN
        RAISE EXCEPTION
            'Subcorte 2A: existen afectaciones con tipo y parcela incompatibles; corrija los datos antes de migrar';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM afectacion a
          JOIN parcela p ON p.id_parcela = a.id_parcela
         WHERE a.activo = TRUE
           AND a.tipo_afectacion = 'individual'
           AND (
               p.activo = FALSE
               OR NULLIF(BTRIM(p.no_parcela_ppt), '') IS NULL
               OR (
                   NULLIF(BTRIM(p.certificado_parcelario), '') IS NULL
                   AND NULLIF(BTRIM(p.folio_derechos), '') IS NULL
                   AND p.constancia_vigencia_fecha IS NULL
                   AND COALESCE(p.documentacion_disponible, FALSE) = FALSE
                   AND NULLIF(BTRIM(p.documentacion_faltante), '') IS NULL
               )
               OR NOT EXISTS (
                   SELECT 1
                     FROM parcela_titular pt
                     JOIN persona pe ON pe.id_persona = pt.id_persona
                    WHERE pt.id_parcela = p.id_parcela
                      AND pt.activo = TRUE
                      AND pe.activo = TRUE
               )
               OR (
                   p.tipo_parcela = 'copropiedad'
                   AND 2 > (
                       SELECT COUNT(*)
                         FROM parcela_titular pt
                         JOIN persona pe ON pe.id_persona = pt.id_persona
                        WHERE pt.id_parcela = p.id_parcela
                          AND pt.activo = TRUE
                          AND pe.activo = TRUE
                   )
               )
           )
    ) THEN
        RAISE EXCEPTION
            'Subcorte 2A: existen parcelas activas de afectaciones individuales sin PPT, soporte/justificación o titulares suficientes';
    END IF;
END;
$$;

ALTER TABLE afectacion
    DROP CONSTRAINT IF EXISTS chk_individual_requiere_parcela;

ALTER TABLE afectacion
    ADD CONSTRAINT chk_afectacion_tipo_parcela CHECK (
        (tipo_afectacion = 'colectivo' AND id_parcela IS NULL)
        OR
        (tipo_afectacion = 'individual' AND id_parcela IS NOT NULL)
    );

CREATE OR REPLACE FUNCTION fn_validar_parcela_para_afectacion(
    p_id_parcela INTEGER
) RETURNS VOID AS $$
DECLARE
    v_parcela parcela%ROWTYPE;
    v_titulares_activos INTEGER;
    v_minimo_titulares INTEGER;
BEGIN
    PERFORM pg_advisory_xact_lock(906, p_id_parcela);

    SELECT *
      INTO v_parcela
      FROM parcela
     WHERE id_parcela = p_id_parcela
     FOR KEY SHARE;

    IF NOT FOUND OR v_parcela.activo = FALSE THEN
        RAISE EXCEPTION 'La parcela de una afectación individual debe existir y estar activa';
    END IF;

    IF NULLIF(BTRIM(v_parcela.no_parcela_ppt), '') IS NULL THEN
        RAISE EXCEPTION 'La parcela de una afectación individual requiere no_parcela_ppt';
    END IF;

    IF NULLIF(BTRIM(v_parcela.certificado_parcelario), '') IS NULL
       AND NULLIF(BTRIM(v_parcela.folio_derechos), '') IS NULL
       AND v_parcela.constancia_vigencia_fecha IS NULL
       AND COALESCE(v_parcela.documentacion_disponible, FALSE) = FALSE
       AND NULLIF(BTRIM(v_parcela.documentacion_faltante), '') IS NULL THEN
        RAISE EXCEPTION 'La parcela de una afectación individual requiere soporte o justificación registral';
    END IF;

    SELECT COUNT(*)
      INTO v_titulares_activos
      FROM parcela_titular pt
      JOIN persona pe ON pe.id_persona = pt.id_persona
     WHERE pt.id_parcela = p_id_parcela
       AND pt.activo = TRUE
       AND pe.activo = TRUE;

    v_minimo_titulares := CASE WHEN v_parcela.tipo_parcela = 'copropiedad' THEN 2 ELSE 1 END;
    IF v_titulares_activos < v_minimo_titulares THEN
        RAISE EXCEPTION
            'La parcela de una afectación individual requiere al menos % titular(es) activo(s)',
            v_minimo_titulares;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Reemplaza la validación parcial creada por la migración 004.
CREATE OR REPLACE FUNCTION fn_validar_parcela_individual() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.tipo_afectacion = 'individual' AND NEW.activo = TRUE THEN
        PERFORM fn_validar_parcela_para_afectacion(NEW.id_parcela);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validar_parcela_individual ON afectacion;
CREATE TRIGGER trg_validar_parcela_individual
    BEFORE INSERT OR UPDATE OF tipo_afectacion, id_parcela, activo ON afectacion
    FOR EACH ROW EXECUTE FUNCTION fn_validar_parcela_individual();

CREATE OR REPLACE FUNCTION fn_proteger_parcela_con_afectacion() RETURNS TRIGGER AS $$
BEGIN
    IF OLD.activo = TRUE AND NEW.activo = FALSE
       AND EXISTS (
           SELECT 1 FROM afectacion a
            WHERE a.id_parcela = OLD.id_parcela
              AND a.tipo_afectacion = 'individual'
              AND a.activo = TRUE
       ) THEN
        RAISE EXCEPTION 'No se puede inactivar una parcela con afectación individual activa';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_revalidar_parcela_referenciada() RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM afectacion a
         WHERE a.id_parcela = NEW.id_parcela
           AND a.tipo_afectacion = 'individual'
           AND a.activo = TRUE
    ) THEN
        PERFORM fn_validar_parcela_para_afectacion(NEW.id_parcela);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_revalidar_titulares_parcela() RETURNS TRIGGER AS $$
DECLARE
    v_id_parcela_anterior INTEGER;
    v_id_parcela_nueva INTEGER;
BEGIN
    v_id_parcela_anterior := CASE WHEN TG_OP = 'UPDATE' THEN OLD.id_parcela ELSE NULL END;
    v_id_parcela_nueva := NEW.id_parcela;

    IF v_id_parcela_anterior IS NOT NULL
       AND v_id_parcela_anterior <> v_id_parcela_nueva
       AND EXISTS (
           SELECT 1 FROM afectacion a
            WHERE a.id_parcela = v_id_parcela_anterior
              AND a.tipo_afectacion = 'individual'
              AND a.activo = TRUE
       ) THEN
        PERFORM fn_validar_parcela_para_afectacion(v_id_parcela_anterior);
    END IF;

    IF EXISTS (
        SELECT 1 FROM afectacion a
         WHERE a.id_parcela = v_id_parcela_nueva
           AND a.tipo_afectacion = 'individual'
           AND a.activo = TRUE
    ) THEN
        PERFORM fn_validar_parcela_para_afectacion(v_id_parcela_nueva);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_2a_proteger_parcela_referenciada ON parcela;
CREATE TRIGGER trg_2a_proteger_parcela_referenciada
    BEFORE UPDATE OF activo ON parcela
    FOR EACH ROW EXECUTE FUNCTION fn_proteger_parcela_con_afectacion();

DROP TRIGGER IF EXISTS trg_2a_revalidar_parcela_referenciada ON parcela;
CREATE TRIGGER trg_2a_revalidar_parcela_referenciada
    AFTER UPDATE OF tipo_parcela, no_parcela_ppt, certificado_parcelario,
                    folio_derechos, constancia_vigencia_fecha,
                    documentacion_disponible, documentacion_faltante ON parcela
    FOR EACH ROW EXECUTE FUNCTION fn_revalidar_parcela_referenciada();

DROP TRIGGER IF EXISTS trg_2a_revalidar_titulares_parcela ON parcela_titular;
CREATE TRIGGER trg_2a_revalidar_titulares_parcela
    AFTER INSERT OR UPDATE OF activo, id_parcela ON parcela_titular
    FOR EACH ROW EXECUTE FUNCTION fn_revalidar_titulares_parcela();

INSERT INTO schema_migrations (version, descripcion)
VALUES ('005', 'Subcorte 2A: integridad de afectaciones colectivas e individuales');

COMMIT;
