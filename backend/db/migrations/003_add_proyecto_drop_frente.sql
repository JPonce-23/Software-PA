-- ============================================================
-- MIGRACIÓN 003: Proyecto como raíz territorial y retiro de frente
-- Fecha: 2026-07-27
--
-- Se ejecuta UNA sola vez sobre bases creadas con la línea base
-- anterior. Requiere al menos un usuario activo, que se registra
-- como actor técnico de las operaciones auditadas de la migración.
-- ============================================================

BEGIN;

-- La inserción del proyecto inicial dispara la auditoría forense.
DO $$
DECLARE
    v_usuario_tecnico INTEGER;
BEGIN
    SELECT id_usuario
      INTO v_usuario_tecnico
      FROM usuario
     WHERE activo = TRUE
     ORDER BY id_usuario
     LIMIT 1;

    IF v_usuario_tecnico IS NULL THEN
        RAISE EXCEPTION 'La migración 003 requiere al menos un usuario activo para la auditoría';
    END IF;

    PERFORM set_config('app.current_user_id', v_usuario_tecnico::TEXT, TRUE);
END;
$$;

-- ============================================================
-- PASO 1: Crear proyecto y vincular los tramos existentes
-- ============================================================
CREATE TABLE proyecto (
    id_proyecto SERIAL PRIMARY KEY,
    clave_proyecto VARCHAR(30) UNIQUE NOT NULL,
    nombre_proyecto VARCHAR(200) NOT NULL,
    descripcion TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_registro DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT,
    observaciones TEXT
);

CREATE TRIGGER trg_audit_proyecto
    AFTER INSERT OR UPDATE ON proyecto
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_proyecto');
CREATE TRIGGER trg_prevent_delete_proyecto
    BEFORE DELETE ON proyecto
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_proyecto
    BEFORE UPDATE OF activo ON proyecto
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

INSERT INTO proyecto (clave_proyecto, nombre_proyecto, descripcion)
VALUES (
    'PROY-INICIAL',
    'Proyecto Inicial (Migración)',
    'Proyecto genérico creado por la migración 003 para asignar los tramos existentes.'
);

ALTER TABLE tramo ADD COLUMN id_proyecto INTEGER;
UPDATE tramo
   SET id_proyecto = (
       SELECT id_proyecto
         FROM proyecto
        WHERE clave_proyecto = 'PROY-INICIAL'
   );
ALTER TABLE tramo ALTER COLUMN id_proyecto SET NOT NULL;
ALTER TABLE tramo ADD CONSTRAINT fk_tramo_proyecto
    FOREIGN KEY (id_proyecto) REFERENCES proyecto(id_proyecto);
ALTER TABLE tramo DROP CONSTRAINT IF EXISTS tramo_clave_tramo_key;
ALTER TABLE tramo ADD CONSTRAINT uq_tramo_proyecto_clave
    UNIQUE (id_proyecto, clave_tramo);
CREATE INDEX idx_tramo_id_proyecto ON tramo(id_proyecto);

-- ============================================================
-- PASO 2: Consolidar usuario_frente en usuario_tramo
-- ============================================================
CREATE TABLE usuario_tramo (
    id_usuario_tramo SERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario),
    id_tramo INTEGER NOT NULL REFERENCES tramo(id_tramo),
    fecha_asignacion TIMESTAMPTZ NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER REFERENCES usuario(id_usuario),
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT uq_usuario_tramo UNIQUE (id_usuario, id_tramo)
);

-- Si un usuario tenía varios frentes del mismo tramo, se conserva la
-- asignación activa más reciente; en su ausencia, la más reciente.
INSERT INTO usuario_tramo (
    id_usuario, id_tramo, fecha_asignacion, activo, fecha_baja,
    id_usuario_baja, motivo_baja, fecha_reactivacion,
    id_usuario_reactivacion, motivo_reactivacion, observaciones
)
SELECT DISTINCT ON (uf.id_usuario, f.id_tramo)
    uf.id_usuario,
    f.id_tramo,
    uf.fecha_asignacion,
    uf.activo,
    uf.fecha_baja,
    uf.id_usuario_baja,
    uf.motivo_baja,
    uf.fecha_reactivacion,
    uf.id_usuario_reactivacion,
    uf.motivo_reactivacion,
    uf.observaciones
FROM usuario_frente uf
JOIN frente f ON f.id_frente = uf.id_frente
ORDER BY
    uf.id_usuario,
    f.id_tramo,
    uf.activo DESC,
    uf.fecha_asignacion DESC,
    uf.id_usuario_frente DESC;

DROP TABLE usuario_frente;

CREATE TRIGGER trg_audit_usuario_tramo
    AFTER INSERT OR UPDATE ON usuario_tramo
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_usuario_tramo');
CREATE TRIGGER trg_prevent_delete_usuario_tramo
    BEFORE DELETE ON usuario_tramo
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_usuario_tramo
    BEFORE UPDATE OF activo ON usuario_tramo
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();
CREATE INDEX idx_usuario_tramo_id_tramo ON usuario_tramo(id_tramo);

-- ============================================================
-- PASO 3: Retirar frente y reconstruir vistas dependientes
-- ============================================================
DROP VIEW IF EXISTS vw_dashboard_liberacion;
DROP VIEW IF EXISTS vw_tramo_nucleo_estado;

ALTER TABLE tramo_nucleo
    DROP CONSTRAINT IF EXISTS fk_tramo_nucleo_frente_mismo_tramo;
ALTER TABLE tramo_nucleo
    DROP CONSTRAINT IF EXISTS tramo_nucleo_id_frente_fkey;
ALTER TABLE tramo_nucleo DROP COLUMN id_frente;

DROP TABLE frente;

CREATE VIEW vw_tramo_nucleo_estado AS
SELECT
    tn.id_tramo_nucleo,
    tn.id_tramo,
    tn.id_nucleo,
    tn.consecutivo,
    tn.longitud_m,
    tn.causa_problema,
    EXISTS (
        SELECT 1 FROM asamblea a
        WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo
          AND a.resultado_anuencia = 'otorgada'
          AND a.activo = TRUE
    ) AS tiene_anuencia,
    EXISTS (
        SELECT 1 FROM convenio c
        WHERE c.id_tramo_nucleo = tn.id_tramo_nucleo
          AND c.convenio_inscrito_fecha_ran IS NOT NULL
          AND c.activo = TRUE
    ) AS tiene_convenio_inscrito_ran,
    CASE
        WHEN tn.es_expropiacion = TRUE THEN 'problema'
        WHEN NULLIF(BTRIM(tn.causa_problema), '') IS NOT NULL THEN 'problema'
        WHEN (
            SELECT COUNT(*) FROM afectacion a
            WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo AND a.activo = TRUE
        ) > 0 AND NOT EXISTS (
            SELECT 1 FROM afectacion a
            WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo
              AND a.activo = TRUE
              AND NOT EXISTS (
                  SELECT 1 FROM convenio c
                  WHERE c.id_afectacion = a.id_afectacion
                    AND c.convenio_inscrito_fecha_ran IS NOT NULL
                    AND c.activo = TRUE
              )
        ) THEN 'liberado'
        WHEN EXISTS (
            SELECT 1 FROM convenio c
            WHERE c.id_tramo_nucleo = tn.id_tramo_nucleo AND c.activo = TRUE
        ) THEN 'en_proceso'
        ELSE 'pendiente'
    END AS estado_legal,
    CASE
        WHEN (
            SELECT COUNT(*) FROM afectacion a
            WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo AND a.activo = TRUE
        ) = 0 THEN 'pendiente_digitalizacion'
        WHEN EXISTS (
            SELECT 1 FROM afectacion a
            WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo
              AND a.geometria_afectacion IS NULL
              AND a.activo = TRUE
        ) THEN 'pendiente_digitalizacion'
        ELSE 'completo'
    END AS estado_geoespacial
FROM tramo_nucleo tn
WHERE tn.activo = TRUE;

CREATE VIEW vw_dashboard_liberacion AS
WITH modificatorios_vigentes AS (
    SELECT id_convenio_padre, id_convenio, superficie_real_afectada_ha, superficie_total_ha
    FROM (
        SELECT
            id_convenio_padre,
            id_convenio,
            superficie_real_afectada_ha,
            superficie_total_ha,
            ROW_NUMBER() OVER (
                PARTITION BY id_convenio_padre
                ORDER BY fecha_firma DESC, id_convenio DESC
            ) AS rn
        FROM convenio
        WHERE tipo_convenio = 'modificatorio'
          AND convenio_inscrito_fecha_ran IS NOT NULL
          AND activo = TRUE
    ) modificatorios
    WHERE rn = 1
),
convenios_base AS (
    SELECT
        c.id_tramo_nucleo,
        c.id_convenio,
        c.tipo_afectacion,
        COALESCE(
            m.superficie_real_afectada_ha,
            m.superficie_total_ha,
            c.superficie_real_afectada_ha,
            c.superficie_total_ha,
            0
        ) AS superficie_liberada_ha
    FROM convenio c
    LEFT JOIN modificatorios_vigentes m ON m.id_convenio_padre = c.id_convenio
    WHERE c.tipo_convenio IN ('cop_original', 'obras_complementarias')
      AND c.convenio_inscrito_fecha_ran IS NOT NULL
      AND c.activo = TRUE
),
superficies_adicionales AS (
    SELECT
        c.id_tramo_nucleo,
        c.id_convenio,
        c.tipo_afectacion,
        COALESCE(
            m.superficie_real_afectada_ha,
            m.superficie_total_ha,
            c.superficie_adicional_ha,
            c.superficie_ampliacion_ha,
            0
        ) AS superficie_liberada_ha
    FROM convenio c
    LEFT JOIN modificatorios_vigentes m ON m.id_convenio_padre = c.id_convenio
    WHERE c.tipo_convenio IN ('superficie_adicional', 'ampliacion', 'ampliacion_remanente')
      AND c.convenio_inscrito_fecha_ran IS NOT NULL
      AND c.activo = TRUE
),
liberacion_unificada AS (
    SELECT * FROM convenios_base
    UNION ALL
    SELECT * FROM superficies_adicionales
),
agrupacion_liberada AS (
    SELECT
        id_tramo_nucleo,
        SUM(superficie_liberada_ha) AS superficie_liberada_ha,
        COUNT(DISTINCT id_convenio) AS total_convenios_formalizados_ran,
        COUNT(DISTINCT CASE WHEN tipo_afectacion = 'colectivo' THEN id_convenio END)
            AS total_convenios_colectivos_formalizados_ran,
        COUNT(DISTINCT CASE WHEN tipo_afectacion = 'individual' THEN id_convenio END)
            AS total_convenios_individuales_formalizados_ran,
        SUM(CASE WHEN tipo_afectacion = 'colectivo' THEN superficie_liberada_ha ELSE 0 END)
            AS total_colectivo_ha,
        SUM(CASE WHEN tipo_afectacion = 'individual' THEN superficie_liberada_ha ELSE 0 END)
            AS total_individual_ha
    FROM liberacion_unificada
    GROUP BY id_tramo_nucleo
)
SELECT
    v.id_tramo_nucleo,
    p.id_proyecto,
    p.clave_proyecto,
    p.nombre_proyecto,
    t.id_tramo,
    t.clave_tramo,
    n.id_nucleo,
    n.nombre_nucleo,
    ef.nombre AS entidad_federativa,
    v.estado_legal,
    v.estado_geoespacial,
    COALESCE(af.total_superficie_afectada_ha, 0) AS total_superficie_afectada_ha,
    COALESCE(al.superficie_liberada_ha, 0) AS superficie_liberada_ha,
    COALESCE(af.total_superficie_afectada_ha, 0) - COALESCE(al.superficie_liberada_ha, 0)
        AS superficie_pendiente_ha,
    CASE
        WHEN COALESCE(af.total_superficie_afectada_ha, 0) = 0 THEN 0
        ELSE ROUND((COALESCE(al.superficie_liberada_ha, 0) / af.total_superficie_afectada_ha) * 100, 2)
    END AS porcentaje_avance_legal,
    CASE
        WHEN COALESCE(af.total_superficie_afectada_ha, 0) = 0 THEN 0
        ELSE ROUND((COALESCE(af_geo.superficie_con_geometria, 0) / af.total_superficie_afectada_ha) * 100, 2)
    END AS porcentaje_avance_geoespacial,
    COALESCE(al.total_convenios_formalizados_ran, 0) AS total_convenios_formalizados_ran,
    COALESCE(al.total_convenios_colectivos_formalizados_ran, 0)
        AS total_convenios_colectivos_formalizados_ran,
    COALESCE(al.total_convenios_individuales_formalizados_ran, 0)
        AS total_convenios_individuales_formalizados_ran,
    COALESCE(al.total_colectivo_ha, 0) AS total_colectivo_ha,
    COALESCE(al.total_individual_ha, 0) AS total_individual_ha
FROM vw_tramo_nucleo_estado v
JOIN tramo t ON t.id_tramo = v.id_tramo AND t.activo = TRUE
JOIN proyecto p ON p.id_proyecto = t.id_proyecto AND p.activo = TRUE
JOIN nucleo_agrario n ON n.id_nucleo = v.id_nucleo AND n.activo = TRUE
JOIN municipio m ON m.id_municipio = n.id_municipio AND m.activo = TRUE
JOIN entidad_federativa ef ON ef.id_entidad = m.id_entidad AND ef.activo = TRUE
LEFT JOIN (
    SELECT id_tramo_nucleo, SUM(COALESCE(superficie_afectada_ha, 0)) AS total_superficie_afectada_ha
    FROM afectacion
    WHERE activo = TRUE
    GROUP BY id_tramo_nucleo
) af ON af.id_tramo_nucleo = v.id_tramo_nucleo
LEFT JOIN (
    SELECT id_tramo_nucleo, SUM(COALESCE(superficie_afectada_ha, 0)) AS superficie_con_geometria
    FROM afectacion
    WHERE activo = TRUE AND geometria_afectacion IS NOT NULL
    GROUP BY id_tramo_nucleo
) af_geo ON af_geo.id_tramo_nucleo = v.id_tramo_nucleo
LEFT JOIN agrupacion_liberada al ON al.id_tramo_nucleo = v.id_tramo_nucleo;

COMMIT;
