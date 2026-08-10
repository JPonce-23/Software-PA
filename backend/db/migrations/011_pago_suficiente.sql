-- Migración 011: Cierre financiero con pago suficiente

BEGIN;

SELECT pg_advisory_xact_lock(20260810, 11);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE version = '010'
    ) THEN
        RAISE EXCEPTION 'La migracion 011 requiere la migracion 010 aplicada';
    END IF;
    IF EXISTS (
        SELECT 1 FROM schema_migrations WHERE version = '011'
    ) THEN
        RAISE EXCEPTION 'La migracion 011 ya fue aplicada';
    END IF;
END;
$$;

-- Preflight: Verificar que no existan trámites completos con saldo pendiente.
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
      FROM tramite_fifonafe tf
     WHERE tf.activo = TRUE
       AND tf.tipo_tramite = 'indemnizacion'
       AND tf.estatus = 'completo'
       AND COALESCE(fn_2b_total_pagado_ciclo(tf.id_ciclo_afectacion), 0)
           < COALESCE(fn_2b_limite_ciclo(tf.id_ciclo_afectacion), 0);
    IF v_count > 0 THEN
        RAISE EXCEPTION 'PREFLIGHT FALLIDO: Hay % tramites completos sin pago suficiente', v_count;
    END IF;
END $$;

-- 1. Actualizar fn_2b_validar_fifonafe para exigir pago suficiente al completar indemnización
CREATE OR REPLACE FUNCTION fn_2b_validar_fifonafe()
RETURNS TRIGGER AS $$
DECLARE
    v_ciclo afectacion_ciclo%ROWTYPE;
    v_convenio convenio%ROWTYPE;
    v_informe tramite_fifonafe%ROWTYPE;
BEGIN
    IF NEW.activo = FALSE THEN RETURN NEW; END IF;
    IF NEW.id_afectacion IS NULL OR NEW.id_convenio IS NULL
       OR NEW.id_ciclo_afectacion IS NULL THEN
        IF TG_OP = 'INSERT' OR NEW IS DISTINCT FROM OLD THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_FIFONAFE_LINAJE_REQUERIDO';
        END IF;
        RETURN NEW;
    END IF;

    SELECT * INTO v_ciclo FROM afectacion_ciclo
     WHERE id_ciclo_afectacion = NEW.id_ciclo_afectacion
       AND id_afectacion = NEW.id_afectacion
       AND id_tramo_nucleo = NEW.id_tramo_nucleo AND activo = TRUE;
    SELECT * INTO v_convenio FROM convenio
     WHERE id_convenio = NEW.id_convenio
       AND id_ciclo_afectacion = NEW.id_ciclo_afectacion
       AND id_afectacion = NEW.id_afectacion AND activo = TRUE;
    IF NOT FOUND OR v_convenio.tipo_convenio = 'modificatorio'
       OR v_ciclo.id_ciclo_afectacion IS NULL
       OR v_ciclo.tipo_afectacion <> NEW.tipo_afectacion THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_FIFONAFE_LINAJE_INVALIDO';
    END IF;
    IF fn_2b_salida_terminal_efectiva(NEW.id_afectacion) IS NOT NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_FLUJO_TERMINAL';
    END IF;
    IF v_convenio.convenio_inscrito_fecha_ran IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_RAN_CONVENIO_REQUERIDO';
    END IF;
    IF NEW.tipo_afectacion = 'colectivo' AND NOT EXISTS (
        SELECT 1 FROM asamblea a
         WHERE a.id_asamblea = v_convenio.id_asamblea_autorizacion
           AND a.id_ciclo_afectacion = NEW.id_ciclo_afectacion
           AND a.acta_inscripcion_fecha_ran IS NOT NULL AND a.activo = TRUE
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_RAN_ASAMBLEA_REQUERIDO';
    END IF;

    IF NEW.tipo_tramite = 'informe_no_conflictos' THEN
        IF NEW.id_tramite_no_conflictos IS NOT NULL THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_INFORME_AUTORREFERENCIA_INVALIDA';
        END IF;
        IF NEW.estatus = 'completo' AND NEW.hay_conflictos IS NULL THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_RESULTADO_CONFLICTOS_REQUERIDO';
        END IF;
    ELSE
        SELECT * INTO v_informe FROM tramite_fifonafe
         WHERE id_tramite_fifonafe = NEW.id_tramite_no_conflictos
           AND id_ciclo_afectacion = NEW.id_ciclo_afectacion
           AND tipo_tramite = 'informe_no_conflictos'
           AND estatus = 'completo' AND hay_conflictos = FALSE AND activo = TRUE;
        IF NOT FOUND THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_NO_CONFLICTOS_REQUERIDO';
        END IF;
        
        -- NUEVA REGLA: Exigir pago suficiente al completar
        IF NEW.estatus = 'completo' THEN
            IF COALESCE(fn_2b_total_pagado_ciclo(NEW.id_ciclo_afectacion), 0) < COALESCE(fn_2b_limite_ciclo(NEW.id_ciclo_afectacion), 0) THEN
                RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_PAGO_INSUFICIENTE';
            END IF;
        END IF;
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.estatus = 'completo' AND NEW.estatus <> 'completo' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_REGRESION_PROHIBIDA';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Proteger pagos completados de ser reducidos
CREATE OR REPLACE FUNCTION fn_2b_validar_suficiencia_pago()
RETURNS TRIGGER AS $$
DECLARE
    v_tramite tramite_fifonafe%ROWTYPE;
    v_limite NUMERIC(18,2);
    v_total NUMERIC(18,2);
BEGIN
    IF TG_OP = 'DELETE' OR (TG_OP = 'UPDATE' AND (NEW.activo = FALSE OR NEW.monto_pagado < OLD.monto_pagado)) THEN
        SELECT * INTO v_tramite FROM tramite_fifonafe WHERE id_tramite_fifonafe = OLD.id_tramite_fifonafe;
        IF v_tramite.estatus = 'completo' AND v_tramite.tipo_tramite = 'indemnizacion' AND v_tramite.activo = TRUE THEN
            v_limite := fn_2b_limite_ciclo(v_tramite.id_ciclo_afectacion);
            SELECT COALESCE(SUM(monto_pagado), 0) INTO v_total
              FROM pago_indemnizacion
             WHERE id_tramite_fifonafe = v_tramite.id_tramite_fifonafe
               AND activo = TRUE
               AND id_pago <> OLD.id_pago;
               
            IF TG_OP = 'UPDATE' AND NEW.activo = TRUE THEN
                v_total := v_total + NEW.monto_pagado;
            END IF;
            
            IF v_total < v_limite THEN
                RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_PAGO_INSUFICIENTE_REDUCCION';
            END IF;
        END IF;
    END IF;
    
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_2b_validar_suficiencia_pago ON pago_indemnizacion;
CREATE TRIGGER trg_2b_validar_suficiencia_pago
    BEFORE UPDATE OR DELETE ON pago_indemnizacion
    FOR EACH ROW EXECUTE FUNCTION fn_2b_validar_suficiencia_pago();

-- 3. Reemplazar sólo la vista cuyo cálculo cambia. Las vistas superiores
-- conservan su contrato y consumen este resultado sin ser redefinidas.
CREATE OR REPLACE VIEW vw_afectacion_ciclo_estado AS
WITH base AS (
    SELECT ac.*,
           c.id_convenio,
           c.fecha_firma,
           c.ingreso_ran_fecha,
           c.convenio_inscrito_fecha_ran,
           CASE WHEN c.tipo_afectacion = 'colectivo'
                THEN COALESCE(c.superficie_real_afectada_ha,
                              c.superficie_adicional_ha, 0)
                ELSE COALESCE(c.superficie_total_ha,
                              c.superficie_ampliacion_ha, 0) END AS superficie_convenio_ha
      FROM afectacion_ciclo ac
      LEFT JOIN convenio c
        ON c.id_ciclo_afectacion = ac.id_ciclo_afectacion
       AND c.tipo_convenio <> 'modificatorio' AND c.activo = TRUE
     WHERE ac.activo = TRUE
), hechos AS (
    SELECT b.*,
           fn_2b_salida_terminal_efectiva(b.id_afectacion) AS estado_terminal,
           EXISTS (
               SELECT 1 FROM tramite_fifonafe tf
                WHERE tf.id_ciclo_afectacion = b.id_ciclo_afectacion
                  AND tf.tipo_tramite = 'informe_no_conflictos'
                  AND tf.estatus = 'completo' AND tf.hay_conflictos = FALSE
                  AND tf.activo = TRUE
           ) AS no_conflictos_completo,
           (EXISTS (
               SELECT 1 FROM tramite_fifonafe tf
                WHERE tf.id_ciclo_afectacion = b.id_ciclo_afectacion
                  AND tf.tipo_tramite = 'indemnizacion'
                  AND tf.estatus = 'completo' AND tf.activo = TRUE
           ) AND COALESCE(fn_2b_total_pagado_ciclo(b.id_ciclo_afectacion), 0) >= COALESCE(fn_2b_limite_ciclo(b.id_ciclo_afectacion), 0)) AS indemnizacion_completa,
           EXISTS (
               SELECT 1 FROM asamblea asa
                WHERE asa.id_ciclo_afectacion = b.id_ciclo_afectacion
                  AND asa.tipo_asamblea = 'retiro_fondos'
                  AND asa.estatus_asamblea = 'completo'
                  AND asa.fecha_realizada IS NOT NULL AND asa.activo = TRUE
           ) AS retiro_fondos_completo,
           fn_2b_limite_ciclo(b.id_ciclo_afectacion) AS limite_pagable,
           fn_2b_total_pagado_ciclo(b.id_ciclo_afectacion) AS total_pagado
      FROM base b
      JOIN afectacion a ON a.id_afectacion = b.id_afectacion
)
SELECT h.*,
       CASE
           WHEN h.id_convenio IS NULL THEN 'convenio_pendiente'
           WHEN h.fecha_firma IS NULL THEN 'convenio_pendiente_firma'
           ELSE 'convenio_firmado'
       END AS estado_operativo,
       CASE
           WHEN h.convenio_inscrito_fecha_ran IS NOT NULL THEN 'inscrito_ran'
           WHEN h.ingreso_ran_fecha IS NOT NULL THEN 'ingresado_ran'
           ELSE 'no_iniciado'
       END AS estado_registral,
       CASE
           WHEN h.estado_terminal IS NOT NULL THEN 'no_aplica_terminal'
           WHEN h.indemnizacion_completa = FALSE THEN
               CASE WHEN h.no_conflictos_completo
                    THEN 'indemnizacion_pendiente'
                    ELSE 'informe_no_conflictos_pendiente' END
           WHEN h.tipo_afectacion = 'colectivo' AND h.retiro_fondos_completo = FALSE
               THEN 'retiro_fondos_pendiente'
           ELSE 'concluido'
       END AS estado_financiero,
       COALESCE(h.superficie_base_ciclo_ha, h.superficie_convenio_ha, 0)
           AS superficie_ciclo_ha,
       GREATEST(COALESCE(h.limite_pagable, 0) - COALESCE(h.total_pagado, 0), 0)
           AS saldo_disponible
  FROM hechos h;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('011', 'Cierre financiero con pago suficiente');

COMMIT;
