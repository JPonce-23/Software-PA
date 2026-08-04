-- ============================================================
-- MIGRACIÓN 006: Subcorte 2B — secuencia, terminalidad y liberación
-- Estrategia EXPAND: no elimina datos ni infiere relaciones históricas.
-- ============================================================

BEGIN;

SELECT pg_advisory_xact_lock(20260803, 6);

DO $$
DECLARE
    v_usuario_tecnico INTEGER;
BEGIN
    IF to_regclass('public.schema_migrations') IS NULL
       OR NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '005') THEN
        RAISE EXCEPTION 'La migración 006 requiere la migración 005 aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '006') THEN
        RAISE EXCEPTION 'La migración 006 ya fue aplicada';
    END IF;

    SELECT id_usuario INTO v_usuario_tecnico
      FROM usuario
     WHERE activo = TRUE
     ORDER BY CASE WHEN rol = 'admin' THEN 0 ELSE 1 END, id_usuario
     LIMIT 1;
    IF v_usuario_tecnico IS NULL THEN
        RAISE EXCEPTION 'La migración 006 requiere un usuario activo para auditoría';
    END IF;
    PERFORM set_config('app.current_user_id', v_usuario_tecnico::TEXT, TRUE);
END;
$$;

-- 1. Salida terminal por afectación.
ALTER TABLE afectacion
    ADD COLUMN tipo_salida_terminal VARCHAR(50),
    ADD COLUMN fecha_salida_terminal TIMESTAMPTZ,
    ADD COLUMN motivo_salida_terminal TEXT,
    ADD CONSTRAINT chk_2b_salida_terminal_tipo CHECK (
        tipo_salida_terminal IS NULL OR tipo_salida_terminal IN (
            'fuera_seguimiento_expropiacion',
            'fuera_seguimiento_comunidad_indigena'
        )
    ),
    ADD CONSTRAINT chk_2b_salida_terminal_completa CHECK (
        (tipo_salida_terminal IS NULL
         AND fecha_salida_terminal IS NULL
         AND motivo_salida_terminal IS NULL)
        OR
        (tipo_salida_terminal IS NOT NULL
         AND fecha_salida_terminal IS NOT NULL
         AND NULLIF(BTRIM(motivo_salida_terminal), '') IS NOT NULL)
    );

-- 2. Identidad estable para cada ciclo de una afectación.
CREATE TABLE afectacion_ciclo (
    id_ciclo_afectacion SERIAL PRIMARY KEY,
    id_tramo_nucleo INTEGER NOT NULL,
    id_afectacion INTEGER NOT NULL,
    tipo_afectacion VARCHAR(20) NOT NULL,
    tipo_ciclo VARCHAR(50) NOT NULL CHECK (tipo_ciclo IN (
        'cop_original', 'superficie_adicional', 'obras_complementarias',
        'ampliacion', 'ampliacion_remanente'
    )),
    consecutivo INTEGER NOT NULL CHECK (consecutivo > 0),
    superficie_base_ciclo_ha NUMERIC(12,4)
        CHECK (superficie_base_ciclo_ha IS NULL OR superficie_base_ciclo_ha >= 0),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER REFERENCES usuario(id_usuario),
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT fk_2b_ciclo_afectacion
        FOREIGN KEY (id_tramo_nucleo, id_afectacion, tipo_afectacion)
        REFERENCES afectacion(id_tramo_nucleo, id_afectacion, tipo_afectacion),
    CONSTRAINT uq_2b_ciclo_tramo_id UNIQUE (id_tramo_nucleo, id_ciclo_afectacion),
    CONSTRAINT uq_2b_ciclo_linaje UNIQUE (
        id_tramo_nucleo, id_ciclo_afectacion, id_afectacion
    ),
    CONSTRAINT chk_2b_ciclo_tipo_derecho CHECK (
        (tipo_afectacion = 'colectivo' AND tipo_ciclo IN (
            'cop_original', 'superficie_adicional', 'obras_complementarias'
        ))
        OR
        (tipo_afectacion = 'individual' AND tipo_ciclo IN (
            'cop_original', 'ampliacion', 'ampliacion_remanente'
        ))
    )
);

CREATE UNIQUE INDEX uq_2b_ciclo_consecutivo_activo
    ON afectacion_ciclo(id_afectacion, tipo_ciclo, consecutivo)
    WHERE activo = TRUE;
CREATE UNIQUE INDEX uq_2b_ciclo_original_activo
    ON afectacion_ciclo(id_afectacion)
    WHERE activo = TRUE AND tipo_ciclo = 'cop_original';
CREATE INDEX idx_2b_ciclo_afectacion
    ON afectacion_ciclo(id_afectacion, activo, id_ciclo_afectacion);

CREATE TRIGGER trg_audit_afectacion_ciclo
    AFTER INSERT OR UPDATE ON afectacion_ciclo
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_ciclo_afectacion');
CREATE TRIGGER trg_prevent_delete_afectacion_ciclo
    BEFORE DELETE ON afectacion_ciclo
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_afectacion_ciclo
    BEFORE UPDATE OF activo ON afectacion_ciclo
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

INSERT INTO afectacion_ciclo (
    id_tramo_nucleo, id_afectacion, tipo_afectacion, tipo_ciclo, consecutivo,
    superficie_base_ciclo_ha, activo, observaciones
)
SELECT id_tramo_nucleo, id_afectacion, tipo_afectacion, 'cop_original', 1,
       superficie_afectada_ha, activo,
       'Raíz estructural creada por migración 006; no atribuye antecedentes históricos.'
  FROM afectacion;

CREATE OR REPLACE FUNCTION fn_2b_crear_ciclo_original()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO afectacion_ciclo (
        id_tramo_nucleo, id_afectacion, tipo_afectacion, tipo_ciclo, consecutivo,
        superficie_base_ciclo_ha
    ) VALUES (
        NEW.id_tramo_nucleo, NEW.id_afectacion, NEW.tipo_afectacion,
        'cop_original', 1, NEW.superficie_afectada_ha
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_2b_crear_ciclo_original
    AFTER INSERT ON afectacion
    FOR EACH ROW EXECUTE FUNCTION fn_2b_crear_ciclo_original();

CREATE OR REPLACE FUNCTION fn_2b_sincronizar_ciclos_afectacion()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE afectacion_ciclo
       SET activo = NEW.activo,
           fecha_baja = CASE WHEN NEW.activo THEN fecha_baja ELSE NEW.fecha_baja END,
           id_usuario_baja = CASE WHEN NEW.activo THEN id_usuario_baja ELSE NEW.id_usuario_baja END,
           motivo_baja = CASE WHEN NEW.activo THEN motivo_baja ELSE NEW.motivo_baja END,
           fecha_reactivacion = CASE WHEN NEW.activo THEN NEW.fecha_reactivacion ELSE fecha_reactivacion END,
           id_usuario_reactivacion = CASE WHEN NEW.activo THEN NEW.id_usuario_reactivacion ELSE id_usuario_reactivacion END,
           motivo_reactivacion = CASE WHEN NEW.activo THEN NEW.motivo_reactivacion ELSE motivo_reactivacion END
     WHERE id_afectacion = NEW.id_afectacion
       AND activo IS DISTINCT FROM NEW.activo;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_2b_sincronizar_ciclos_afectacion
    AFTER UPDATE OF activo ON afectacion
    FOR EACH ROW EXECUTE FUNCTION fn_2b_sincronizar_ciclos_afectacion();

-- 3. Relaciones expansivas. Permanecen NULL en filas históricas ambiguas.
ALTER TABLE actividad_campo
    ADD COLUMN id_ciclo_afectacion INTEGER,
    ADD CONSTRAINT fk_2b_actividad_ciclo
        FOREIGN KEY (id_tramo_nucleo, id_ciclo_afectacion)
        REFERENCES afectacion_ciclo(id_tramo_nucleo, id_ciclo_afectacion);

ALTER TABLE asamblea
    ADD COLUMN id_afectacion INTEGER,
    ADD COLUMN id_ciclo_afectacion INTEGER,
    ADD CONSTRAINT fk_2b_asamblea_ciclo
        FOREIGN KEY (id_tramo_nucleo, id_ciclo_afectacion, id_afectacion)
        REFERENCES afectacion_ciclo(
            id_tramo_nucleo, id_ciclo_afectacion, id_afectacion
        );

ALTER TABLE convenio
    ADD COLUMN id_ciclo_afectacion INTEGER,
    ADD COLUMN vigencia_financiera_desde TIMESTAMPTZ,
    ADD COLUMN vigencia_financiera_hasta TIMESTAMPTZ,
    ADD CONSTRAINT fk_2b_convenio_ciclo
        FOREIGN KEY (id_tramo_nucleo, id_ciclo_afectacion, id_afectacion)
        REFERENCES afectacion_ciclo(
            id_tramo_nucleo, id_ciclo_afectacion, id_afectacion
        ),
    ADD CONSTRAINT chk_2b_convenio_montos CHECK (
        monto_90 IS NULL OR monto_100 IS NULL OR monto_90 <= monto_100
    ),
    ADD CONSTRAINT chk_2b_vigencia_financiera CHECK (
        (vigencia_financiera_desde IS NULL AND vigencia_financiera_hasta IS NULL)
        OR
        (vigencia_financiera_desde IS NOT NULL AND (
            vigencia_financiera_hasta IS NULL
            OR vigencia_financiera_hasta >= vigencia_financiera_desde
        ))
    );

ALTER TABLE tramite_fifonafe
    ADD COLUMN id_ciclo_afectacion INTEGER,
    ADD COLUMN id_tramite_no_conflictos INTEGER,
    ADD CONSTRAINT fk_2b_fifonafe_ciclo
        FOREIGN KEY (id_tramo_nucleo, id_ciclo_afectacion, id_afectacion)
        REFERENCES afectacion_ciclo(
            id_tramo_nucleo, id_ciclo_afectacion, id_afectacion
        ),
    ADD CONSTRAINT fk_2b_fifonafe_no_conflictos
        FOREIGN KEY (id_tramite_no_conflictos)
        REFERENCES tramite_fifonafe(id_tramite_fifonafe);

CREATE INDEX idx_2b_actividad_ciclo ON actividad_campo(id_ciclo_afectacion);
CREATE INDEX idx_2b_asamblea_ciclo ON asamblea(id_ciclo_afectacion, tipo_asamblea);
CREATE INDEX idx_2b_convenio_ciclo ON convenio(id_ciclo_afectacion, tipo_convenio);
CREATE INDEX idx_2b_fifonafe_ciclo ON tramite_fifonafe(id_ciclo_afectacion, tipo_tramite);
CREATE UNIQUE INDEX uq_2b_convenio_base_ciclo_activo
    ON convenio(id_ciclo_afectacion)
    WHERE activo = TRUE
      AND id_ciclo_afectacion IS NOT NULL
      AND tipo_convenio <> 'modificatorio';
CREATE UNIQUE INDEX uq_2b_version_financiera_vigente
    ON convenio(id_ciclo_afectacion)
    WHERE activo = TRUE
      AND id_ciclo_afectacion IS NOT NULL
      AND vigencia_financiera_desde IS NOT NULL
      AND vigencia_financiera_hasta IS NULL;
CREATE UNIQUE INDEX uq_2b_fifonafe_tipo_ciclo_activo
    ON tramite_fifonafe(id_ciclo_afectacion, tipo_tramite)
    WHERE activo = TRUE AND id_ciclo_afectacion IS NOT NULL;
CREATE UNIQUE INDEX uq_2b_retiro_fondos_ciclo_completo
    ON asamblea(id_ciclo_afectacion)
    WHERE activo = TRUE
      AND id_ciclo_afectacion IS NOT NULL
      AND tipo_asamblea = 'retiro_fondos'
      AND estatus_asamblea = 'completo';

-- 4. Utilidades comunes de terminalidad y secuencia.
CREATE OR REPLACE FUNCTION fn_2b_salida_terminal_efectiva(p_id_afectacion INTEGER)
RETURNS VARCHAR AS $$
DECLARE
    v_tipo VARCHAR;
BEGIN
    SELECT CASE
               WHEN (tn.es_expropiacion AND na.comunidad_indigena)
                 OR (a.tipo_salida_terminal = 'fuera_seguimiento_expropiacion'
                     AND na.comunidad_indigena)
                 OR (a.tipo_salida_terminal = 'fuera_seguimiento_comunidad_indigena'
                     AND tn.es_expropiacion)
                   THEN 'inconsistente_terminal'
               ELSE COALESCE(
                   a.tipo_salida_terminal,
                   CASE WHEN tn.es_expropiacion
                        THEN 'fuera_seguimiento_expropiacion' END,
                   CASE WHEN na.comunidad_indigena
                        THEN 'fuera_seguimiento_comunidad_indigena' END
               )
           END
      INTO v_tipo
      FROM afectacion a
      JOIN tramo_nucleo tn ON tn.id_tramo_nucleo = a.id_tramo_nucleo
      JOIN nucleo_agrario na ON na.id_nucleo = a.id_nucleo
     WHERE a.id_afectacion = p_id_afectacion;
    RETURN v_tipo;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION fn_2b_validar_ciclo()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.activo = TRUE
       AND fn_2b_salida_terminal_efectiva(NEW.id_afectacion) IS NOT NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_FLUJO_TERMINAL';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_2b_validar_ciclo
    BEFORE INSERT OR UPDATE OF activo, tipo_ciclo, id_afectacion
    ON afectacion_ciclo
    FOR EACH ROW EXECUTE FUNCTION fn_2b_validar_ciclo();

CREATE OR REPLACE FUNCTION fn_2b_validar_actividad()
RETURNS TRIGGER AS $$
DECLARE
    v_ciclo afectacion_ciclo%ROWTYPE;
BEGIN
    IF NEW.activo = FALSE THEN RETURN NEW; END IF;

    IF NEW.id_ciclo_afectacion IS NULL THEN
        IF NEW.contexto_proceso <> 'cop_original' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = '2B_ACTIVIDAD_CICLO_REQUERIDO';
        END IF;
    ELSE
        SELECT * INTO v_ciclo FROM afectacion_ciclo
         WHERE id_ciclo_afectacion = NEW.id_ciclo_afectacion
           AND id_tramo_nucleo = NEW.id_tramo_nucleo
           AND activo = TRUE;
        IF NOT FOUND OR v_ciclo.tipo_ciclo <> NEW.contexto_proceso THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = '2B_ACTIVIDAD_CICLO_INVALIDO';
        END IF;
        IF fn_2b_salida_terminal_efectiva(v_ciclo.id_afectacion) IS NOT NULL THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = '2B_FLUJO_TERMINAL';
        END IF;
    END IF;

    IF NEW.tipo_actividad = 'caminamiento'
       AND NEW.fecha_realizada IS NOT NULL
       AND NOT EXISTS (
           SELECT 1 FROM actividad_campo s
            WHERE s.id_tramo_nucleo = NEW.id_tramo_nucleo
              AND s.tipo_actividad = 'sensibilizacion'
              AND s.contexto_proceso = NEW.contexto_proceso
              AND s.id_ciclo_afectacion IS NOT DISTINCT FROM NEW.id_ciclo_afectacion
              AND s.fecha_realizada IS NOT NULL
              AND s.activo = TRUE
       ) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = '2B_SENSIBILIZACION_REQUERIDA';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_2b_validar_actividad
    BEFORE INSERT OR UPDATE OF id_tramo_nucleo, id_ciclo_afectacion,
        contexto_proceso, tipo_actividad, fecha_realizada, activo
    ON actividad_campo
    FOR EACH ROW EXECUTE FUNCTION fn_2b_validar_actividad();

CREATE OR REPLACE FUNCTION fn_2b_validar_creacion_afectacion()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.activo = TRUE
       AND (TG_OP = 'INSERT' OR OLD.activo = FALSE)
       AND NOT EXISTS (
           SELECT 1 FROM actividad_campo ac
            WHERE ac.id_tramo_nucleo = NEW.id_tramo_nucleo
              AND ac.tipo_actividad = 'caminamiento'
              AND ac.contexto_proceso = 'cop_original'
              AND ac.id_ciclo_afectacion IS NULL
              AND ac.fecha_realizada IS NOT NULL
              AND ac.activo = TRUE
       ) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001',
            MESSAGE = '2B_CAMINAMIENTO_REQUERIDO';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_2b_validar_creacion_afectacion
    BEFORE INSERT OR UPDATE OF activo ON afectacion
    FOR EACH ROW EXECUTE FUNCTION fn_2b_validar_creacion_afectacion();

CREATE OR REPLACE FUNCTION fn_2b_validar_salida_terminal()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND OLD.tipo_salida_terminal IS NOT NULL
       AND (NEW.tipo_salida_terminal IS DISTINCT FROM OLD.tipo_salida_terminal
            OR NEW.fecha_salida_terminal IS DISTINCT FROM OLD.fecha_salida_terminal
            OR NEW.motivo_salida_terminal IS DISTINCT FROM OLD.motivo_salida_terminal) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_TERMINAL_IRREVERSIBLE';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_2b_validar_salida_terminal
    BEFORE UPDATE OF tipo_salida_terminal, fecha_salida_terminal,
        motivo_salida_terminal ON afectacion
    FOR EACH ROW EXECUTE FUNCTION fn_2b_validar_salida_terminal();

-- 5. Asamblea, convenio y seguimiento registral.
CREATE OR REPLACE FUNCTION fn_2b_validar_asamblea()
RETURNS TRIGGER AS $$
DECLARE
    v_ciclo afectacion_ciclo%ROWTYPE;
BEGIN
    IF NEW.activo = FALSE THEN RETURN NEW; END IF;
    IF NEW.id_afectacion IS NULL OR NEW.id_ciclo_afectacion IS NULL THEN
        IF TG_OP = 'INSERT' OR NEW IS DISTINCT FROM OLD THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_ASAMBLEA_CICLO_REQUERIDO';
        END IF;
        RETURN NEW;
    END IF;

    SELECT * INTO v_ciclo FROM afectacion_ciclo
     WHERE id_ciclo_afectacion = NEW.id_ciclo_afectacion
       AND id_afectacion = NEW.id_afectacion
       AND id_tramo_nucleo = NEW.id_tramo_nucleo
       AND activo = TRUE;
    IF NOT FOUND OR v_ciclo.tipo_afectacion <> 'colectivo' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_ASAMBLEA_SOLO_COLECTIVA';
    END IF;
    IF fn_2b_salida_terminal_efectiva(NEW.id_afectacion) IS NOT NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_FLUJO_TERMINAL';
    END IF;

    IF v_ciclo.tipo_ciclo <> 'cop_original'
       AND NOT EXISTS (
           SELECT 1 FROM actividad_campo ac
            WHERE ac.id_ciclo_afectacion = v_ciclo.id_ciclo_afectacion
              AND ac.tipo_actividad = 'caminamiento'
              AND ac.fecha_realizada IS NOT NULL AND ac.activo = TRUE
       ) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_CAMINAMIENTO_REQUERIDO';
    END IF;

    IF NEW.acta_inscripcion_fecha_ran IS NOT NULL AND NEW.ingreso_ran_fecha IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_RAN_INGRESO_REQUERIDO';
    END IF;
    IF NEW.ingreso_ran_fecha IS NOT NULL AND NEW.fecha_realizada IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_ASAMBLEA_REALIZADA_REQUERIDA';
    END IF;
    IF TG_OP = 'UPDATE' AND (
        (OLD.ingreso_ran_fecha IS NOT NULL AND NEW.ingreso_ran_fecha IS NULL)
        OR (OLD.acta_inscripcion_fecha_ran IS NOT NULL AND NEW.acta_inscripcion_fecha_ran IS NULL)
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_REGRESION_PROHIBIDA';
    END IF;

    IF NEW.tipo_asamblea = 'retiro_fondos'
       AND NEW.estatus_asamblea = 'completo' THEN
        IF NEW.fecha_realizada IS NULL OR NOT EXISTS (
            SELECT 1 FROM tramite_fifonafe tf
             WHERE tf.id_ciclo_afectacion = NEW.id_ciclo_afectacion
               AND tf.tipo_tramite = 'indemnizacion'
               AND tf.estatus = 'completo' AND tf.activo = TRUE
        ) THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001',
                MESSAGE = '2B_INDEMNIZACION_COMPLETA_REQUERIDA';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_2b_validar_asamblea
    BEFORE INSERT OR UPDATE ON asamblea
    FOR EACH ROW EXECUTE FUNCTION fn_2b_validar_asamblea();

CREATE OR REPLACE FUNCTION fn_2b_validar_convenio()
RETURNS TRIGGER AS $$
DECLARE
    v_ciclo afectacion_ciclo%ROWTYPE;
    v_padre convenio%ROWTYPE;
    v_asamblea asamblea%ROWTYPE;
BEGIN
    IF NEW.activo = FALSE THEN RETURN NEW; END IF;
    IF NEW.id_ciclo_afectacion IS NULL THEN
        IF TG_OP = 'INSERT' OR NEW IS DISTINCT FROM OLD THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_CONVENIO_CICLO_REQUERIDO';
        END IF;
        RETURN NEW;
    END IF;

    SELECT * INTO v_ciclo FROM afectacion_ciclo
     WHERE id_ciclo_afectacion = NEW.id_ciclo_afectacion
       AND id_afectacion = NEW.id_afectacion
       AND id_tramo_nucleo = NEW.id_tramo_nucleo
       AND activo = TRUE;
    IF NOT FOUND OR v_ciclo.tipo_afectacion <> NEW.tipo_afectacion THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_CONVENIO_CICLO_INVALIDO';
    END IF;
    IF fn_2b_salida_terminal_efectiva(NEW.id_afectacion) IS NOT NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_FLUJO_TERMINAL';
    END IF;

    IF NEW.tipo_convenio = 'modificatorio' THEN
        SELECT * INTO v_padre FROM convenio
         WHERE id_convenio = NEW.id_convenio_padre AND activo = TRUE;
        IF NOT FOUND OR v_padre.tipo_convenio = 'modificatorio'
           OR v_padre.id_ciclo_afectacion IS DISTINCT FROM NEW.id_ciclo_afectacion
           OR v_padre.id_afectacion <> NEW.id_afectacion THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_MODIFICATORIO_PADRE_INVALIDO';
        END IF;
        IF NEW.monto_90 IS NULL OR NEW.monto_100 IS NULL
           OR (NEW.tipo_afectacion = 'colectivo' AND NEW.monto_bdt IS NULL)
           OR (NEW.tipo_afectacion = 'individual' AND NEW.monto_bdt IS NOT NULL) THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_MODIFICATORIO_MONTOS_INVALIDOS';
        END IF;
    ELSIF NEW.tipo_convenio <> v_ciclo.tipo_ciclo THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_CONVENIO_TIPO_CICLO_INVALIDO';
    END IF;

    IF NEW.tipo_afectacion = 'colectivo' AND NEW.tipo_convenio <> 'modificatorio' THEN
        SELECT * INTO v_asamblea FROM asamblea
         WHERE id_asamblea = NEW.id_asamblea_autorizacion
           AND id_afectacion = NEW.id_afectacion
           AND id_ciclo_afectacion = NEW.id_ciclo_afectacion
           AND activo = TRUE;
        IF NOT FOUND OR v_asamblea.resultado_anuencia <> 'otorgada'
           OR v_asamblea.fecha_realizada IS NULL THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_ASAMBLEA_APROBADA_REQUERIDA';
        END IF;
    END IF;

    IF NEW.ingreso_ran_fecha IS NOT NULL AND NEW.fecha_firma IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_CONVENIO_FIRMA_REQUERIDA';
    END IF;
    IF NEW.convenio_inscrito_fecha_ran IS NOT NULL AND NEW.ingreso_ran_fecha IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_RAN_INGRESO_REQUERIDO';
    END IF;
    IF TG_OP = 'UPDATE' AND (
        (OLD.fecha_firma IS NOT NULL AND NEW.fecha_firma IS NULL)
        OR (OLD.ingreso_ran_fecha IS NOT NULL AND NEW.ingreso_ran_fecha IS NULL)
        OR (OLD.convenio_inscrito_fecha_ran IS NOT NULL AND NEW.convenio_inscrito_fecha_ran IS NULL)
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_REGRESION_PROHIBIDA';
    END IF;

    IF NEW.tipo_convenio <> 'modificatorio'
       AND NEW.fecha_firma IS NOT NULL
       AND NEW.vigencia_financiera_desde IS NULL THEN
        NEW.vigencia_financiera_desde := CURRENT_TIMESTAMP;
    END IF;

    IF NEW.tipo_convenio = 'modificatorio'
       AND NEW.vigencia_financiera_desde IS NOT NULL
       AND (TG_OP = 'INSERT' OR OLD.vigencia_financiera_desde IS NULL) THEN
        IF NEW.fecha_firma IS NULL THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_CONVENIO_FIRMA_REQUERIDA';
        END IF;
        IF NEW.tipo_afectacion = 'colectivo'
           AND NEW.convenio_inscrito_fecha_ran IS NULL THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_MODIFICATORIO_RAN_REQUERIDO';
        END IF;
    END IF;

    IF TG_OP = 'UPDATE'
       AND OLD.vigencia_financiera_desde IS NOT NULL
       AND OLD.vigencia_financiera_hasta IS NULL
       AND (NEW.monto_90 IS DISTINCT FROM OLD.monto_90
            OR NEW.monto_100 IS DISTINCT FROM OLD.monto_100
            OR NEW.monto_bdt IS DISTINCT FROM OLD.monto_bdt) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_VERSION_FINANCIERA_INMUTABLE';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validar_regresion_estado_convenio ON convenio;
CREATE TRIGGER trg_2b_validar_convenio
    BEFORE INSERT OR UPDATE ON convenio
    FOR EACH ROW EXECUTE FUNCTION fn_2b_validar_convenio();

CREATE OR REPLACE FUNCTION fn_2b_sincronizar_superficie_ciclo()
RETURNS TRIGGER AS $$
DECLARE
    v_superficie NUMERIC(12,4);
BEGIN
    IF NEW.id_ciclo_afectacion IS NULL OR NEW.tipo_convenio = 'modificatorio' THEN
        RETURN NEW;
    END IF;
    v_superficie := CASE
        WHEN NEW.tipo_convenio = 'superficie_adicional' THEN NEW.superficie_adicional_ha
        WHEN NEW.tipo_convenio IN ('ampliacion', 'ampliacion_remanente')
            THEN NEW.superficie_ampliacion_ha
        WHEN NEW.tipo_afectacion = 'colectivo' THEN NEW.superficie_real_afectada_ha
        ELSE NEW.superficie_total_ha
    END;
    IF v_superficie IS NOT NULL THEN
        UPDATE afectacion_ciclo
           SET superficie_base_ciclo_ha = v_superficie
         WHERE id_ciclo_afectacion = NEW.id_ciclo_afectacion
           AND superficie_base_ciclo_ha IS DISTINCT FROM v_superficie;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_2b_sincronizar_superficie_ciclo
    AFTER INSERT OR UPDATE OF superficie_real_afectada_ha, superficie_total_ha,
        superficie_adicional_ha, superficie_ampliacion_ha ON convenio
    FOR EACH ROW EXECUTE FUNCTION fn_2b_sincronizar_superficie_ciclo();

-- 6. FIFONAFE, pagos y sustitución financiera por ciclo.
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
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.estatus = 'completo' AND NEW.estatus <> 'completo' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_REGRESION_PROHIBIDA';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_2b_validar_fifonafe
    BEFORE INSERT OR UPDATE ON tramite_fifonafe
    FOR EACH ROW EXECUTE FUNCTION fn_2b_validar_fifonafe();

CREATE OR REPLACE FUNCTION fn_2b_limite_ciclo(p_id_ciclo INTEGER)
RETURNS NUMERIC AS $$
DECLARE
    v_limite NUMERIC(18,2);
BEGIN
    SELECT CASE
                WHEN c.tipo_afectacion = 'colectivo'
                     OR c.tipo_convenio <> 'modificatorio'
                THEN COALESCE(c.monto_100, 0) + COALESCE(c.monto_bdt, 0)
                ELSE COALESCE(c.monto_100, 0)
           END
      INTO v_limite
      FROM convenio c
     WHERE c.id_ciclo_afectacion = p_id_ciclo
       AND c.activo = TRUE
       AND c.vigencia_financiera_desde IS NOT NULL
       AND c.vigencia_financiera_hasta IS NULL;
    RETURN v_limite;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION fn_2b_total_pagado_ciclo(p_id_ciclo INTEGER)
RETURNS NUMERIC AS $$
    SELECT COALESCE(SUM(p.monto_pagado), 0)::NUMERIC(18,2)
      FROM tramite_fifonafe tf
      JOIN pago_indemnizacion p
        ON p.id_tramite_fifonafe = tf.id_tramite_fifonafe
       AND p.activo = TRUE
     WHERE tf.id_ciclo_afectacion = p_id_ciclo
       AND tf.tipo_tramite = 'indemnizacion'
       AND tf.activo = TRUE;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION fn_validar_pago_indemnizacion()
RETURNS TRIGGER AS $$
DECLARE
    v_tramite tramite_fifonafe%ROWTYPE;
    v_limite NUMERIC(18,2);
    v_total NUMERIC(18,2);
BEGIN
    SELECT * INTO v_tramite FROM tramite_fifonafe
     WHERE id_tramite_fifonafe = NEW.id_tramite_fifonafe;

    IF NEW.activo = TRUE THEN
        IF v_tramite.tipo_tramite IS DISTINCT FROM 'indemnizacion'
           OR v_tramite.activo IS DISTINCT FROM TRUE THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_PAGO_TRAMITE_INVALIDO';
        END IF;

        IF v_tramite.id_ciclo_afectacion IS NULL THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_PAGO_CICLO_REQUERIDO';
        END IF;
        PERFORM 1 FROM afectacion_ciclo
         WHERE id_ciclo_afectacion = v_tramite.id_ciclo_afectacion
         FOR UPDATE;
        IF fn_2b_salida_terminal_efectiva(v_tramite.id_afectacion) IS NOT NULL THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_FLUJO_TERMINAL';
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM tramite_fifonafe nc
             WHERE nc.id_tramite_fifonafe = v_tramite.id_tramite_no_conflictos
               AND nc.estatus = 'completo' AND nc.hay_conflictos = FALSE
               AND nc.activo = TRUE
        ) THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_NO_CONFLICTOS_REQUERIDO';
        END IF;

        v_limite := fn_2b_limite_ciclo(v_tramite.id_ciclo_afectacion);
        IF v_limite IS NULL OR v_limite <= 0 THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_LIMITE_FINANCIERO_NO_VIGENTE';
        END IF;
        SELECT COALESCE(SUM(p.monto_pagado), 0) INTO v_total
          FROM pago_indemnizacion p
          JOIN tramite_fifonafe tf
            ON tf.id_tramite_fifonafe = p.id_tramite_fifonafe
         WHERE tf.id_ciclo_afectacion = v_tramite.id_ciclo_afectacion
           AND p.activo = TRUE
           AND p.id_pago <> COALESCE(NEW.id_pago, -1);
        IF v_total + NEW.monto_pagado > v_limite THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_LIMITE_PAGO_EXCEDIDO';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_proteger_limite_convenio_pagado()
RETURNS TRIGGER AS $$
DECLARE
    v_total NUMERIC(18,2);
    v_limite NUMERIC(18,2);
BEGIN
    IF NEW.id_ciclo_afectacion IS NULL THEN RETURN NEW; END IF;
    PERFORM 1 FROM afectacion_ciclo
     WHERE id_ciclo_afectacion = NEW.id_ciclo_afectacion FOR UPDATE;
    v_total := fn_2b_total_pagado_ciclo(NEW.id_ciclo_afectacion);
    v_limite := CASE
        WHEN NEW.tipo_afectacion = 'colectivo'
             OR NEW.tipo_convenio <> 'modificatorio'
        THEN COALESCE(NEW.monto_100, 0) + COALESCE(NEW.monto_bdt, 0)
        ELSE COALESCE(NEW.monto_100, 0)
    END;
    IF v_total > 0 AND NEW.activo = FALSE THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_CONVENIO_CON_PAGOS';
    END IF;
    IF NEW.activo = TRUE AND NEW.vigencia_financiera_hasta IS NULL
       AND NEW.vigencia_financiera_desde IS NOT NULL AND v_total > v_limite THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = '2B_LIMITE_MENOR_QUE_PAGADO';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_proteger_limite_convenio_pagado ON convenio;
CREATE TRIGGER trg_proteger_limite_convenio_pagado
    BEFORE UPDATE OF monto_100, monto_bdt, activo,
        vigencia_financiera_desde, vigencia_financiera_hasta ON convenio
    FOR EACH ROW EXECUTE FUNCTION fn_proteger_limite_convenio_pagado();

-- 7. Estados derivados. Nunca se almacena una bandera manual de liberación.
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
           EXISTS (
               SELECT 1 FROM tramite_fifonafe tf
                WHERE tf.id_ciclo_afectacion = b.id_ciclo_afectacion
                  AND tf.tipo_tramite = 'indemnizacion'
                  AND tf.estatus = 'completo' AND tf.activo = TRUE
           ) AS indemnizacion_completa,
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

CREATE OR REPLACE VIEW vw_afectacion_estado AS
SELECT a.id_afectacion,
       a.id_tramo_nucleo,
       a.id_nucleo,
       a.tipo_afectacion,
       fn_2b_salida_terminal_efectiva(a.id_afectacion) AS estado_terminal,
       COUNT(c.id_ciclo_afectacion) AS total_ciclos,
       COUNT(*) FILTER (WHERE c.estado_financiero = 'concluido') AS ciclos_concluidos,
       COALESCE(SUM(c.superficie_ciclo_ha), 0) AS superficie_total_ciclos_ha,
       COALESCE(SUM(c.superficie_ciclo_ha)
           FILTER (WHERE c.estado_financiero = 'concluido'), 0)
           AS superficie_liberada_ha,
       CASE
           WHEN fn_2b_salida_terminal_efectiva(a.id_afectacion) IS NOT NULL
               THEN 'no_aplica_terminal'
           WHEN COUNT(c.id_ciclo_afectacion) > 0
                AND BOOL_AND(c.estado_financiero = 'concluido') THEN 'liberada'
           WHEN BOOL_OR(c.id_convenio IS NOT NULL OR c.no_conflictos_completo
                       OR c.total_pagado > 0) THEN 'en_proceso'
           ELSE 'pendiente'
       END AS estado_liberacion,
       CASE
           WHEN BOOL_OR(c.estado_registral = 'inscrito_ran') THEN 'con_avance_registral'
           WHEN BOOL_OR(c.estado_registral = 'ingresado_ran') THEN 'ingresado_ran'
           ELSE 'no_iniciado'
       END AS estado_registral,
       CASE
           WHEN BOOL_AND(c.estado_financiero = 'concluido') THEN 'concluido'
           WHEN BOOL_OR(c.estado_financiero <> 'informe_no_conflictos_pendiente')
               THEN 'en_proceso'
           ELSE 'no_iniciado'
       END AS estado_financiero
  FROM afectacion a
  LEFT JOIN vw_afectacion_ciclo_estado c ON c.id_afectacion = a.id_afectacion
 WHERE a.activo = TRUE
 GROUP BY a.id_afectacion, a.id_tramo_nucleo, a.id_nucleo, a.tipo_afectacion;

CREATE OR REPLACE VIEW vw_tramo_nucleo_estado AS
WITH resumen AS (
    SELECT ae.id_tramo_nucleo,
           COUNT(*) AS total_afectaciones,
           COUNT(*) FILTER (WHERE ae.estado_liberacion = 'liberada') AS liberadas,
           COUNT(*) FILTER (WHERE ae.estado_liberacion = 'pendiente') AS pendientes,
           COUNT(*) FILTER (WHERE ae.estado_liberacion = 'en_proceso') AS en_proceso,
           COUNT(*) FILTER (WHERE ae.estado_liberacion = 'no_aplica_terminal') AS terminales
      FROM vw_afectacion_estado ae GROUP BY ae.id_tramo_nucleo
)
SELECT tn.id_tramo_nucleo, tn.id_tramo, tn.id_nucleo, tn.consecutivo,
       tn.longitud_m, tn.causa_problema,
       EXISTS (SELECT 1 FROM asamblea a
                WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo
                  AND a.resultado_anuencia = 'otorgada' AND a.activo = TRUE)
           AS tiene_anuencia,
       EXISTS (SELECT 1 FROM convenio c
                WHERE c.id_tramo_nucleo = tn.id_tramo_nucleo
                  AND c.convenio_inscrito_fecha_ran IS NOT NULL AND c.activo = TRUE)
           AS tiene_convenio_inscrito_ran,
       CASE
           WHEN tn.es_expropiacion OR EXISTS (
               SELECT 1 FROM nucleo_agrario na
                WHERE na.id_nucleo = tn.id_nucleo
                  AND na.comunidad_indigena = TRUE
           ) THEN 'fuera_seguimiento'
           WHEN COALESCE(r.total_afectaciones, 0) = 0 THEN 'pendiente'
           WHEN r.liberadas = r.total_afectaciones THEN 'liberado'
           WHEN r.terminales = r.total_afectaciones THEN 'fuera_seguimiento'
           WHEN r.liberadas > 0 OR r.terminales > 0 THEN 'mixto'
           WHEN r.en_proceso > 0 THEN 'en_proceso'
           ELSE 'pendiente'
       END AS estado_legal,
       CASE
           WHEN COALESCE(r.total_afectaciones, 0) = 0 OR EXISTS (
               SELECT 1 FROM afectacion a
                WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo
                  AND a.activo = TRUE AND a.geometria_afectacion IS NULL
           ) THEN 'pendiente_digitalizacion'
           ELSE 'completo'
       END AS estado_geoespacial,
       COALESCE(r.total_afectaciones, 0) AS total_afectaciones,
       COALESCE(r.liberadas, 0) AS afectaciones_liberadas,
       COALESCE(r.pendientes, 0) AS afectaciones_pendientes,
       COALESCE(r.en_proceso, 0) AS afectaciones_en_proceso,
       COALESCE(r.terminales, 0) AS afectaciones_terminales
  FROM tramo_nucleo tn
  LEFT JOIN resumen r ON r.id_tramo_nucleo = tn.id_tramo_nucleo
 WHERE tn.activo = TRUE;

CREATE OR REPLACE VIEW vw_dashboard_liberacion AS
WITH superficies AS (
    SELECT ae.id_tramo_nucleo,
           SUM(ae.superficie_total_ciclos_ha) AS total_superficie_afectada_ha,
           SUM(ae.superficie_liberada_ha) AS superficie_liberada_ha,
           SUM(ae.superficie_liberada_ha) FILTER (WHERE ae.tipo_afectacion = 'colectivo')
               AS total_colectivo_ha,
           SUM(ae.superficie_liberada_ha) FILTER (WHERE ae.tipo_afectacion = 'individual')
               AS total_individual_ha
      FROM vw_afectacion_estado ae GROUP BY ae.id_tramo_nucleo
), formalizados AS (
    SELECT c.id_tramo_nucleo,
           COUNT(*) FILTER (WHERE c.convenio_inscrito_fecha_ran IS NOT NULL)
               AS total_convenios_formalizados_ran,
           COUNT(*) FILTER (WHERE c.convenio_inscrito_fecha_ran IS NOT NULL
                             AND c.tipo_afectacion = 'colectivo')
               AS total_convenios_colectivos_formalizados_ran,
           COUNT(*) FILTER (WHERE c.convenio_inscrito_fecha_ran IS NOT NULL
                             AND c.tipo_afectacion = 'individual')
               AS total_convenios_individuales_formalizados_ran
      FROM convenio c
     WHERE c.activo = TRUE AND c.tipo_convenio <> 'modificatorio'
     GROUP BY c.id_tramo_nucleo
)
SELECT v.id_tramo_nucleo, p.id_proyecto, p.clave_proyecto, p.nombre_proyecto,
       t.id_tramo, t.clave_tramo, n.id_nucleo, n.nombre_nucleo,
       ef.nombre AS entidad_federativa, v.estado_legal, v.estado_geoespacial,
       COALESCE(s.total_superficie_afectada_ha, 0) AS total_superficie_afectada_ha,
       COALESCE(s.superficie_liberada_ha, 0) AS superficie_liberada_ha,
       GREATEST(COALESCE(s.total_superficie_afectada_ha, 0)
                - COALESCE(s.superficie_liberada_ha, 0), 0) AS superficie_pendiente_ha,
       CASE WHEN COALESCE(s.total_superficie_afectada_ha, 0) = 0 THEN 0
            ELSE ROUND(COALESCE(s.superficie_liberada_ha, 0)
                       / s.total_superficie_afectada_ha * 100, 2) END
           AS porcentaje_avance_legal,
       CASE WHEN COALESCE(s.total_superficie_afectada_ha, 0) = 0 THEN 0
            ELSE ROUND(COALESCE(g.superficie_con_geometria, 0)
                       / s.total_superficie_afectada_ha * 100, 2) END
           AS porcentaje_avance_geoespacial,
       COALESCE(f.total_convenios_formalizados_ran, 0)
           AS total_convenios_formalizados_ran,
       COALESCE(f.total_convenios_colectivos_formalizados_ran, 0)
           AS total_convenios_colectivos_formalizados_ran,
       COALESCE(f.total_convenios_individuales_formalizados_ran, 0)
           AS total_convenios_individuales_formalizados_ran,
       COALESCE(s.total_colectivo_ha, 0) AS total_colectivo_ha,
       COALESCE(s.total_individual_ha, 0) AS total_individual_ha
  FROM vw_tramo_nucleo_estado v
  JOIN tramo t ON t.id_tramo = v.id_tramo AND t.activo = TRUE
  JOIN proyecto p ON p.id_proyecto = t.id_proyecto AND p.activo = TRUE
  JOIN nucleo_agrario n ON n.id_nucleo = v.id_nucleo AND n.activo = TRUE
  JOIN municipio m ON m.id_municipio = n.id_municipio AND m.activo = TRUE
  JOIN entidad_federativa ef ON ef.id_entidad = m.id_entidad AND ef.activo = TRUE
  LEFT JOIN superficies s ON s.id_tramo_nucleo = v.id_tramo_nucleo
  LEFT JOIN formalizados f ON f.id_tramo_nucleo = v.id_tramo_nucleo
  LEFT JOIN (
      SELECT a.id_tramo_nucleo,
             SUM(COALESCE(a.superficie_afectada_ha, 0)) AS superficie_con_geometria
        FROM afectacion a
       WHERE a.activo = TRUE AND a.geometria_afectacion IS NOT NULL
       GROUP BY a.id_tramo_nucleo
  ) g ON g.id_tramo_nucleo = v.id_tramo_nucleo;

INSERT INTO schema_migrations(version, descripcion)
VALUES ('006', 'Subcorte 2B: secuencia, terminalidad y liberación por afectación');

COMMIT;
