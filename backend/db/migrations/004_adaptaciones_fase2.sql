-- ============================================================
-- MIGRACIÓN 004: Adaptaciones estructurales de la Fase 2.0
-- Fecha: 2026-07-28
--
-- Estrategia: EXPAND.
--   * Agrega el modelo normalizado y migra los datos heredados.
--   * No elimina todavía las columnas de texto de ORV y parcela.
--   * Las columnas heredadas se retirarán en una migración CONTRACT
--     después de desplegar y verificar backend y frontend.
--
-- Requisitos:
--   * La migración 003 debe estar aplicada.
--   * Debe existir al menos un usuario activo para atribuir la
--     migración en la bitácora.
--   * Ejecutar una sola vez con ON_ERROR_STOP habilitado.
-- ============================================================

BEGIN;

SELECT pg_advisory_xact_lock(20260728, 4);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(20) PRIMARY KEY,
    descripcion TEXT NOT NULL,
    aplicada_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '004') THEN
        RAISE EXCEPTION 'La migración 004 ya fue aplicada';
    END IF;

    IF to_regclass('public.proyecto') IS NULL
       OR to_regclass('public.usuario_tramo') IS NULL
       OR to_regclass('public.frente') IS NOT NULL THEN
        RAISE EXCEPTION 'La migración 004 requiere que la migración 003 esté aplicada';
    END IF;
END;
$$;

DO $$
DECLARE
    v_usuario_tecnico INTEGER;
BEGIN
    SELECT id_usuario
      INTO v_usuario_tecnico
      FROM usuario
     WHERE activo = TRUE
     ORDER BY CASE WHEN rol = 'admin' THEN 0 ELSE 1 END, id_usuario
     LIMIT 1;

    IF v_usuario_tecnico IS NULL THEN
        RAISE EXCEPTION 'La migración 004 requiere al menos un usuario activo para la auditoría';
    END IF;

    PERFORM set_config('app.current_user_id', v_usuario_tecnico::TEXT, TRUE);
END;
$$;

-- ============================================================
-- 1. PERSONAS, VÍNCULO CON NÚCLEO Y TRAZABILIDAD DEL LEGADO
-- ============================================================

CREATE TABLE persona (
    id_persona SERIAL PRIMARY KEY,
    curp VARCHAR(18),
    rfc VARCHAR(13),
    nombre VARCHAR(300) NOT NULL,
    apellido_paterno VARCHAR(200),
    apellido_materno VARCHAR(200),
    telefono VARCHAR(20),
    correo_electronico VARCHAR(320),
    datos_identidad_incompletos BOOLEAN NOT NULL DEFAULT FALSE,
    origen_registro VARCHAR(30) NOT NULL DEFAULT 'captura_sistema'
        CHECK (origen_registro IN ('captura_sistema', 'migracion_legacy')),
    clave_origen_legacy VARCHAR(150),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER REFERENCES usuario(id_usuario),
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT chk_persona_nombre_no_vacio CHECK (NULLIF(BTRIM(nombre), '') IS NOT NULL),
    CONSTRAINT chk_persona_curp_formato CHECK (
        curp IS NULL OR curp ~ '^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[A-Z0-9][0-9]$'
    ),
    CONSTRAINT chk_persona_rfc_formato CHECK (
        rfc IS NULL OR rfc ~ '^[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}$'
    ),
    CONSTRAINT chk_persona_correo_no_vacio CHECK (
        correo_electronico IS NULL OR NULLIF(BTRIM(correo_electronico), '') IS NOT NULL
    ),
    CONSTRAINT uq_persona_clave_origen_legacy UNIQUE (clave_origen_legacy)
);

CREATE UNIQUE INDEX uq_persona_curp_normalizada
    ON persona (UPPER(curp))
    WHERE curp IS NOT NULL;
CREATE INDEX idx_persona_nombre_busqueda
    ON persona (LOWER(nombre), LOWER(apellido_paterno), LOWER(apellido_materno));

CREATE TABLE persona_nucleo (
    id_persona_nucleo SERIAL PRIMARY KEY,
    id_persona INTEGER NOT NULL REFERENCES persona(id_persona),
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    calidad_agraria VARCHAR(30)
        CHECK (calidad_agraria IS NULL OR calidad_agraria IN (
            'ejidatario', 'comunero', 'avecindado', 'posesionario',
            'representante', 'otro'
        )),
    fecha_inicio DATE,
    fecha_fin DATE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER REFERENCES usuario(id_usuario),
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT uq_persona_nucleo UNIQUE (id_nucleo, id_persona),
    CONSTRAINT chk_persona_nucleo_fechas CHECK (
        fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio
    )
);

CREATE TABLE persona_fuente_legacy (
    id_persona_fuente SERIAL PRIMARY KEY,
    id_persona INTEGER NOT NULL REFERENCES persona(id_persona),
    tabla_origen VARCHAR(40) NOT NULL CHECK (tabla_origen IN ('orv', 'parcela')),
    id_registro_origen INTEGER NOT NULL,
    campo_origen VARCHAR(80) NOT NULL,
    valor_original TEXT NOT NULL,
    valor_normalizado TEXT NOT NULL,
    requiere_revision BOOLEAN NOT NULL DEFAULT TRUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER REFERENCES usuario(id_usuario),
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT uq_persona_fuente_origen
        UNIQUE (tabla_origen, id_registro_origen, campo_origen)
);

CREATE TRIGGER trg_audit_persona
    AFTER INSERT OR UPDATE ON persona
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_persona');
CREATE TRIGGER trg_prevent_delete_persona
    BEFORE DELETE ON persona
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_persona
    BEFORE UPDATE OF activo ON persona
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

CREATE TRIGGER trg_audit_persona_nucleo
    AFTER INSERT OR UPDATE ON persona_nucleo
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_persona_nucleo');
CREATE TRIGGER trg_prevent_delete_persona_nucleo
    BEFORE DELETE ON persona_nucleo
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_persona_nucleo
    BEFORE UPDATE OF activo ON persona_nucleo
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

CREATE TRIGGER trg_audit_persona_fuente_legacy
    AFTER INSERT OR UPDATE ON persona_fuente_legacy
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_persona_fuente');
CREATE TRIGGER trg_prevent_delete_persona_fuente_legacy
    BEFORE DELETE ON persona_fuente_legacy
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_persona_fuente_legacy
    BEFORE UPDATE OF activo ON persona_fuente_legacy
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- Cada aparición heredada se conserva como identidad independiente.
-- No se fusionan personas únicamente por coincidencia de nombre.
WITH fuentes AS (
    SELECT
        'orv'::VARCHAR(40) AS tabla_origen,
        o.id_orv AS id_registro_origen,
        o.id_nucleo,
        v.campo_origen,
        BTRIM(v.valor_original) AS valor_original,
        FORMAT('orv:%s:%s', o.id_orv, v.campo_origen) AS clave_origen
    FROM orv o
    CROSS JOIN LATERAL (VALUES
        ('comisariado_presidente', o.comisariado_presidente),
        ('comisariado_secretario', o.comisariado_secretario),
        ('comisariado_tesorero', o.comisariado_tesorero),
        ('consejo_vigilancia_presidente', o.consejo_vigilancia_presidente),
        ('consejo_vigilancia_secretario1', o.consejo_vigilancia_secretario1),
        ('consejo_vigilancia_secretario2', o.consejo_vigilancia_secretario2)
    ) AS v(campo_origen, valor_original)
    WHERE NULLIF(BTRIM(v.valor_original), '') IS NOT NULL

    UNION ALL

    SELECT
        'parcela',
        p.id_parcela,
        p.id_nucleo,
        'nombre_titular',
        BTRIM(p.nombre_titular),
        FORMAT('parcela:%s:nombre_titular', p.id_parcela)
    FROM parcela p
    WHERE NULLIF(BTRIM(p.nombre_titular), '') IS NOT NULL
)
INSERT INTO persona (
    nombre, datos_identidad_incompletos, origen_registro, clave_origen_legacy
)
SELECT valor_original, TRUE, 'migracion_legacy', clave_origen
FROM fuentes
ORDER BY tabla_origen, id_registro_origen, campo_origen;

WITH fuentes AS (
    SELECT
        'orv'::VARCHAR(40) AS tabla_origen,
        o.id_orv AS id_registro_origen,
        o.id_nucleo,
        v.campo_origen,
        BTRIM(v.valor_original) AS valor_original,
        FORMAT('orv:%s:%s', o.id_orv, v.campo_origen) AS clave_origen
    FROM orv o
    CROSS JOIN LATERAL (VALUES
        ('comisariado_presidente', o.comisariado_presidente),
        ('comisariado_secretario', o.comisariado_secretario),
        ('comisariado_tesorero', o.comisariado_tesorero),
        ('consejo_vigilancia_presidente', o.consejo_vigilancia_presidente),
        ('consejo_vigilancia_secretario1', o.consejo_vigilancia_secretario1),
        ('consejo_vigilancia_secretario2', o.consejo_vigilancia_secretario2)
    ) AS v(campo_origen, valor_original)
    WHERE NULLIF(BTRIM(v.valor_original), '') IS NOT NULL

    UNION ALL

    SELECT
        'parcela',
        p.id_parcela,
        p.id_nucleo,
        'nombre_titular',
        BTRIM(p.nombre_titular),
        FORMAT('parcela:%s:nombre_titular', p.id_parcela)
    FROM parcela p
    WHERE NULLIF(BTRIM(p.nombre_titular), '') IS NOT NULL
)
INSERT INTO persona_fuente_legacy (
    id_persona, tabla_origen, id_registro_origen, campo_origen,
    valor_original, valor_normalizado
)
SELECT
    pe.id_persona,
    f.tabla_origen,
    f.id_registro_origen,
    f.campo_origen,
    f.valor_original,
    LOWER(REGEXP_REPLACE(f.valor_original, '\s+', ' ', 'g'))
FROM fuentes f
JOIN persona pe ON pe.clave_origen_legacy = f.clave_origen;

INSERT INTO persona_nucleo (id_persona, id_nucleo, calidad_agraria)
SELECT
    pfl.id_persona,
    CASE
        WHEN pfl.tabla_origen = 'orv' THEN o.id_nucleo
        ELSE p.id_nucleo
    END,
    CASE WHEN pfl.tabla_origen = 'orv' THEN 'representante' ELSE NULL END
FROM persona_fuente_legacy pfl
LEFT JOIN orv o
    ON pfl.tabla_origen = 'orv' AND o.id_orv = pfl.id_registro_origen
LEFT JOIN parcela p
    ON pfl.tabla_origen = 'parcela' AND p.id_parcela = pfl.id_registro_origen;

-- ============================================================
-- 2. INTEGRANTES DE ORV Y TITULARIDAD DE PARCELAS
-- ============================================================

ALTER TABLE orv
    ADD CONSTRAINT uq_orv_nucleo_id UNIQUE (id_nucleo, id_orv);

CREATE TABLE orv_integrante (
    id_orv_integrante SERIAL PRIMARY KEY,
    id_orv INTEGER NOT NULL,
    id_nucleo INTEGER NOT NULL,
    id_persona INTEGER NOT NULL,
    cargo VARCHAR(50) NOT NULL CHECK (cargo IN (
        'comisariado_presidente', 'comisariado_secretario',
        'comisariado_tesorero', 'consejo_vigilancia_presidente',
        'consejo_vigilancia_secretario1', 'consejo_vigilancia_secretario2'
    )),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER REFERENCES usuario(id_usuario),
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT fk_orv_integrante_orv_nucleo
        FOREIGN KEY (id_nucleo, id_orv)
        REFERENCES orv(id_nucleo, id_orv),
    CONSTRAINT fk_orv_integrante_persona_nucleo
        FOREIGN KEY (id_nucleo, id_persona)
        REFERENCES persona_nucleo(id_nucleo, id_persona)
);

CREATE UNIQUE INDEX uq_orv_integrante_cargo_activo
    ON orv_integrante (id_orv, cargo)
    WHERE activo = TRUE;
CREATE INDEX idx_orv_integrante_persona ON orv_integrante(id_persona);

CREATE TABLE parcela_titular (
    id_parcela_titular SERIAL PRIMARY KEY,
    id_parcela INTEGER NOT NULL,
    id_nucleo INTEGER NOT NULL,
    id_persona INTEGER NOT NULL,
    tipo_derecho VARCHAR(30) NOT NULL DEFAULT 'titular'
        CHECK (tipo_derecho IN ('titular', 'cotitular', 'posesionario', 'otro')),
    porcentaje_participacion NUMERIC(7,4)
        CHECK (porcentaje_participacion IS NULL OR (
            porcentaje_participacion > 0 AND porcentaje_participacion <= 100
        )),
    fecha_inicio DATE,
    fecha_fin DATE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER REFERENCES usuario(id_usuario),
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT fk_parcela_titular_parcela_nucleo
        FOREIGN KEY (id_nucleo, id_parcela)
        REFERENCES parcela(id_nucleo, id_parcela),
    CONSTRAINT fk_parcela_titular_persona_nucleo
        FOREIGN KEY (id_nucleo, id_persona)
        REFERENCES persona_nucleo(id_nucleo, id_persona),
    CONSTRAINT chk_parcela_titular_fechas CHECK (
        fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio
    )
);

CREATE UNIQUE INDEX uq_parcela_titular_persona_activo
    ON parcela_titular (id_parcela, id_persona)
    WHERE activo = TRUE;
CREATE INDEX idx_parcela_titular_persona ON parcela_titular(id_persona);

CREATE OR REPLACE FUNCTION fn_validar_participacion_parcela()
RETURNS TRIGGER AS $$
DECLARE
    v_porcentaje_acumulado NUMERIC(9,4);
BEGIN
    PERFORM pg_advisory_xact_lock(905, NEW.id_parcela);

    IF NEW.activo = TRUE AND NEW.porcentaje_participacion IS NOT NULL THEN
        SELECT COALESCE(SUM(pt.porcentaje_participacion), 0)
          INTO v_porcentaje_acumulado
          FROM parcela_titular pt
         WHERE pt.id_parcela = NEW.id_parcela
           AND pt.activo = TRUE
           AND pt.porcentaje_participacion IS NOT NULL
           AND pt.id_parcela_titular <> COALESCE(NEW.id_parcela_titular, -1);

        IF v_porcentaje_acumulado + NEW.porcentaje_participacion > 100 THEN
            RAISE EXCEPTION 'La participación activa acumulada de una parcela no puede exceder 100%%';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_participacion_parcela
    BEFORE INSERT OR UPDATE OF id_parcela, porcentaje_participacion, activo
    ON parcela_titular
    FOR EACH ROW EXECUTE FUNCTION fn_validar_participacion_parcela();

CREATE TRIGGER trg_audit_orv_integrante
    AFTER INSERT OR UPDATE ON orv_integrante
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_orv_integrante');
CREATE TRIGGER trg_prevent_delete_orv_integrante
    BEFORE DELETE ON orv_integrante
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_orv_integrante
    BEFORE UPDATE OF activo ON orv_integrante
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

CREATE TRIGGER trg_audit_parcela_titular
    AFTER INSERT OR UPDATE ON parcela_titular
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_parcela_titular');
CREATE TRIGGER trg_prevent_delete_parcela_titular
    BEFORE DELETE ON parcela_titular
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_parcela_titular
    BEFORE UPDATE OF activo ON parcela_titular
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

INSERT INTO orv_integrante (id_orv, id_nucleo, id_persona, cargo)
SELECT
    o.id_orv,
    o.id_nucleo,
    pfl.id_persona,
    pfl.campo_origen
FROM persona_fuente_legacy pfl
JOIN orv o
  ON pfl.tabla_origen = 'orv'
 AND o.id_orv = pfl.id_registro_origen;

INSERT INTO parcela_titular (
    id_parcela, id_nucleo, id_persona, tipo_derecho
)
SELECT
    p.id_parcela,
    p.id_nucleo,
    pfl.id_persona,
    'titular'
FROM persona_fuente_legacy pfl
JOIN parcela p
  ON pfl.tabla_origen = 'parcela'
 AND p.id_parcela = pfl.id_registro_origen;

COMMENT ON COLUMN orv.comisariado_presidente
    IS 'LEGACY FASE 2: lectura temporal; usar orv_integrante';
COMMENT ON COLUMN orv.comisariado_secretario
    IS 'LEGACY FASE 2: lectura temporal; usar orv_integrante';
COMMENT ON COLUMN orv.comisariado_tesorero
    IS 'LEGACY FASE 2: lectura temporal; usar orv_integrante';
COMMENT ON COLUMN orv.consejo_vigilancia_presidente
    IS 'LEGACY FASE 2: lectura temporal; usar orv_integrante';
COMMENT ON COLUMN orv.consejo_vigilancia_secretario1
    IS 'LEGACY FASE 2: lectura temporal; usar orv_integrante';
COMMENT ON COLUMN orv.consejo_vigilancia_secretario2
    IS 'LEGACY FASE 2: lectura temporal; usar orv_integrante';
COMMENT ON COLUMN parcela.nombre_titular
    IS 'LEGACY FASE 2: lectura temporal; usar parcela_titular';

-- Las afectaciones individuales se validan contra la estructura nueva.
CREATE OR REPLACE FUNCTION fn_validar_parcela_individual() RETURNS TRIGGER AS $$
DECLARE
    p_no_ppt VARCHAR;
    p_cert VARCHAR;
    p_folio VARCHAR;
    p_doc_faltante TEXT;
    p_titulares_activos INTEGER;
BEGIN
    IF NEW.tipo_afectacion = 'individual' AND NEW.id_parcela IS NOT NULL THEN
        SELECT
            p.no_parcela_ppt,
            p.certificado_parcelario,
            p.folio_derechos,
            p.documentacion_faltante,
            COUNT(pe.id_persona)
        INTO
            p_no_ppt, p_cert, p_folio, p_doc_faltante, p_titulares_activos
        FROM parcela p
        LEFT JOIN parcela_titular pt
          ON pt.id_parcela = p.id_parcela
         AND pt.activo = TRUE
        LEFT JOIN persona pe
          ON pe.id_persona = pt.id_persona
         AND pe.activo = TRUE
        WHERE p.id_parcela = NEW.id_parcela
        GROUP BY
            p.no_parcela_ppt, p.certificado_parcelario,
            p.folio_derechos, p.documentacion_faltante;

        IF p_no_ppt IS NULL OR COALESCE(p_titulares_activos, 0) = 0 THEN
            RAISE EXCEPTION 'La parcela de una afectación individual requiere no_parcela_ppt y al menos un titular activo';
        END IF;

        IF (p_cert IS NULL OR p_folio IS NULL)
           AND NULLIF(BTRIM(p_doc_faltante), '') IS NULL THEN
            RAISE EXCEPTION 'Si la parcela carece de certificado o folio, documentacion_faltante debe justificarlo';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 3. MINUTAS Y ACUERDOS
-- ============================================================

ALTER TABLE actividad_campo
    ADD CONSTRAINT uq_actividad_tramo_nucleo_id
    UNIQUE (id_tramo_nucleo, id_actividad);

CREATE TABLE minuta (
    id_minuta SERIAL PRIMARY KEY,
    id_tramo_nucleo INTEGER NOT NULL REFERENCES tramo_nucleo(id_tramo_nucleo),
    id_actividad INTEGER,
    fecha_reunion DATE NOT NULL,
    lugar VARCHAR(300),
    asunto VARCHAR(300) NOT NULL,
    resumen TEXT,
    folio VARCHAR(100),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER REFERENCES usuario(id_usuario),
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT fk_minuta_actividad_mismo_expediente
        FOREIGN KEY (id_tramo_nucleo, id_actividad)
        REFERENCES actividad_campo(id_tramo_nucleo, id_actividad)
);

CREATE INDEX idx_minuta_tramo_nucleo ON minuta(id_tramo_nucleo);
CREATE UNIQUE INDEX uq_minuta_folio_activo
    ON minuta (id_tramo_nucleo, folio)
    WHERE activo = TRUE AND folio IS NOT NULL;

CREATE TABLE acuerdo (
    id_acuerdo SERIAL PRIMARY KEY,
    id_minuta INTEGER NOT NULL REFERENCES minuta(id_minuta),
    descripcion TEXT NOT NULL,
    fecha_limite DATE,
    fecha_cumplimiento DATE,
    estatus VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (estatus IN ('pendiente', 'cumplido', 'cancelado', 'vencido')),
    prioridad VARCHAR(10) NOT NULL DEFAULT 'media'
        CHECK (prioridad IN ('alta', 'media', 'baja')),
    id_persona_responsable INTEGER REFERENCES persona(id_persona),
    id_usuario_responsable INTEGER REFERENCES usuario(id_usuario),
    responsable_externo VARCHAR(300),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER REFERENCES usuario(id_usuario),
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT chk_acuerdo_descripcion_no_vacia
        CHECK (NULLIF(BTRIM(descripcion), '') IS NOT NULL),
    CONSTRAINT chk_acuerdo_un_responsable CHECK (
        num_nonnulls(
            id_persona_responsable,
            id_usuario_responsable,
            NULLIF(BTRIM(responsable_externo), '')
        ) = 1
    ),
    CONSTRAINT chk_acuerdo_cumplimiento CHECK (
        (estatus = 'cumplido' AND fecha_cumplimiento IS NOT NULL)
        OR
        (estatus <> 'cumplido' AND fecha_cumplimiento IS NULL)
    )
);

CREATE INDEX idx_acuerdo_minuta ON acuerdo(id_minuta);
CREATE INDEX idx_acuerdo_pendiente
    ON acuerdo(fecha_limite)
    WHERE activo = TRUE AND estatus = 'pendiente';

CREATE TRIGGER trg_audit_minuta
    AFTER INSERT OR UPDATE ON minuta
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_minuta');
CREATE TRIGGER trg_prevent_delete_minuta
    BEFORE DELETE ON minuta
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_minuta
    BEFORE UPDATE OF activo ON minuta
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

CREATE TRIGGER trg_audit_acuerdo
    AFTER INSERT OR UPDATE ON acuerdo
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_acuerdo');
CREATE TRIGGER trg_prevent_delete_acuerdo
    BEFORE DELETE ON acuerdo
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_acuerdo
    BEFORE UPDATE OF activo ON acuerdo
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- ============================================================
-- 4. VERSIONES DOCUMENTALES INMUTABLES
-- ============================================================

CREATE TABLE documento_version (
    id_documento_version SERIAL PRIMARY KEY,
    id_documento INTEGER NOT NULL REFERENCES documentacion_soporte(id_documento),
    numero_version INTEGER NOT NULL CHECK (numero_version >= 1),
    hash_sha256 CHAR(64) NOT NULL
        CHECK (hash_sha256 ~ '^[0-9a-f]{64}$'),
    tamano_bytes BIGINT NOT NULL CHECK (tamano_bytes >= 0),
    nombre_archivo_original VARCHAR(255) NOT NULL,
    ruta_almacenamiento TEXT NOT NULL,
    tipo_mime VARCHAR(150),
    id_usuario_carga INTEGER NOT NULL REFERENCES usuario(id_usuario),
    fecha_carga TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER REFERENCES usuario(id_usuario),
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT uq_documento_version UNIQUE (id_documento, numero_version),
    CONSTRAINT uq_documento_version_ruta UNIQUE (ruta_almacenamiento),
    CONSTRAINT chk_documento_nombre_no_vacio
        CHECK (NULLIF(BTRIM(nombre_archivo_original), '') IS NOT NULL),
    CONSTRAINT chk_documento_ruta_no_vacia
        CHECK (NULLIF(BTRIM(ruta_almacenamiento), '') IS NOT NULL)
);

CREATE INDEX idx_documento_version_documento
    ON documento_version(id_documento, numero_version DESC);

CREATE TRIGGER trg_audit_documento_version
    AFTER INSERT OR UPDATE ON documento_version
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_documento_version');
CREATE TRIGGER trg_prevent_delete_documento_version
    BEFORE DELETE ON documento_version
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_documento_version
    BEFORE UPDATE OF activo ON documento_version
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

COMMENT ON COLUMN documentacion_soporte.url_archivo
    IS 'LEGACY FASE 2: usar documento_version.ruta_almacenamiento';

-- ============================================================
-- 5. PAGOS DE INDEMNIZACIÓN
-- ============================================================

CREATE TABLE pago_indemnizacion (
    id_pago SERIAL PRIMARY KEY,
    id_tramite_fifonafe INTEGER NOT NULL
        REFERENCES tramite_fifonafe(id_tramite_fifonafe),
    monto_pagado NUMERIC(18,2) NOT NULL CHECK (monto_pagado > 0),
    fecha_pago DATE NOT NULL,
    tipo_pago VARCHAR(20) NOT NULL
        CHECK (tipo_pago IN ('anticipo', 'parcial', 'total')),
    medio_pago VARCHAR(20)
        CHECK (medio_pago IS NULL OR medio_pago IN (
            'transferencia', 'cheque', 'deposito', 'otro'
        )),
    banco_emisor VARCHAR(100),
    referencia_bancaria VARCHAR(100),
    id_persona_beneficiaria INTEGER REFERENCES persona(id_persona),
    beneficiario_externo VARCHAR(300),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER REFERENCES usuario(id_usuario),
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT chk_pago_un_beneficiario CHECK (
        num_nonnulls(
            id_persona_beneficiaria,
            NULLIF(BTRIM(beneficiario_externo), '')
        ) = 1
    )
);

CREATE INDEX idx_pago_tramite
    ON pago_indemnizacion(id_tramite_fifonafe, fecha_pago DESC);
CREATE UNIQUE INDEX uq_pago_total_activo
    ON pago_indemnizacion(id_tramite_fifonafe)
    WHERE activo = TRUE AND tipo_pago = 'total';
CREATE UNIQUE INDEX uq_pago_referencia_activa
    ON pago_indemnizacion(banco_emisor, referencia_bancaria)
    WHERE activo = TRUE
      AND banco_emisor IS NOT NULL
      AND referencia_bancaria IS NOT NULL;

CREATE OR REPLACE FUNCTION fn_validar_pago_indemnizacion()
RETURNS TRIGGER AS $$
DECLARE
    v_tipo_tramite VARCHAR;
    v_id_convenio INTEGER;
    v_tramite_activo BOOLEAN;
    v_convenio_activo BOOLEAN;
    v_tipo_convenio VARCHAR;
    v_monto_100 NUMERIC(18,2);
    v_monto_bdt NUMERIC(18,2);
    v_limite_pagable NUMERIC(18,2);
    v_total_pagado NUMERIC(18,2);
BEGIN
    PERFORM pg_advisory_xact_lock(906, NEW.id_tramite_fifonafe);

    SELECT
        tf.tipo_tramite,
        tf.id_convenio,
        tf.activo,
        c.activo,
        c.tipo_convenio,
        c.monto_100,
        c.monto_bdt
    INTO
        v_tipo_tramite,
        v_id_convenio,
        v_tramite_activo,
        v_convenio_activo,
        v_tipo_convenio,
        v_monto_100,
        v_monto_bdt
    FROM tramite_fifonafe tf
    LEFT JOIN convenio c ON c.id_convenio = tf.id_convenio
    WHERE tf.id_tramite_fifonafe = NEW.id_tramite_fifonafe;

    -- Una baja lógica debe seguir siendo posible aunque el trámite o convenio
    -- ya no estén activos. Las validaciones financieras aplican a pagos activos.
    IF NEW.activo = TRUE THEN
        IF v_tipo_tramite IS DISTINCT FROM 'indemnizacion'
           OR v_id_convenio IS NULL
           OR v_tramite_activo IS DISTINCT FROM TRUE
           OR v_convenio_activo IS DISTINCT FROM TRUE THEN
            RAISE EXCEPTION 'El pago requiere un trámite de indemnización activo vinculado a un convenio activo';
        END IF;

        IF v_monto_100 IS NULL THEN
            RAISE EXCEPTION 'El convenio requiere monto_100 antes de registrar pagos';
        END IF;

        IF v_tipo_convenio IN (
            'cop_original', 'ampliacion', 'ampliacion_remanente'
        ) AND v_monto_bdt IS NULL THEN
            RAISE EXCEPTION 'El tipo de convenio % requiere capturar monto_bdt antes de registrar pagos', v_tipo_convenio;
        END IF;

        -- monto_90 es un anticipo contenido en monto_100; no se suma.
        -- BDT es complementario e independiente del valor de la tierra.
        v_limite_pagable := COALESCE(v_monto_100, 0) + COALESCE(v_monto_bdt, 0);

        IF v_limite_pagable <= 0 THEN
            RAISE EXCEPTION 'El convenio debe tener monto_100 y/o monto_bdt para registrar pagos';
        END IF;

        SELECT COALESCE(SUM(p.monto_pagado), 0)
          INTO v_total_pagado
          FROM pago_indemnizacion p
         WHERE p.id_tramite_fifonafe = NEW.id_tramite_fifonafe
           AND p.activo = TRUE
           AND p.id_pago <> COALESCE(NEW.id_pago, -1);

        IF v_total_pagado + NEW.monto_pagado > v_limite_pagable THEN
            RAISE EXCEPTION
                'El total pagado (%) excedería el límite del convenio: monto_100 (%) + monto_bdt (%) = %',
                v_total_pagado + NEW.monto_pagado,
                COALESCE(v_monto_100, 0),
                COALESCE(v_monto_bdt, 0),
                v_limite_pagable;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_pago_indemnizacion
    BEFORE INSERT OR UPDATE
    ON pago_indemnizacion
    FOR EACH ROW EXECUTE FUNCTION fn_validar_pago_indemnizacion();

CREATE OR REPLACE FUNCTION fn_proteger_limite_convenio_pagado()
RETURNS TRIGGER AS $$
DECLARE
    v_total_pagado NUMERIC(18,2);
    v_nuevo_limite NUMERIC(18,2);
BEGIN
    SELECT COALESCE(SUM(p.monto_pagado), 0)
      INTO v_total_pagado
      FROM tramite_fifonafe tf
      JOIN pago_indemnizacion p
        ON p.id_tramite_fifonafe = tf.id_tramite_fifonafe
       AND p.activo = TRUE
     WHERE tf.id_convenio = NEW.id_convenio;

    v_nuevo_limite := COALESCE(NEW.monto_100, 0) + COALESCE(NEW.monto_bdt, 0);

    IF v_total_pagado > 0 AND NEW.activo = FALSE THEN
        RAISE EXCEPTION 'No se puede dar de baja un convenio con pagos activos';
    END IF;

    IF NEW.activo = TRUE AND v_total_pagado > v_nuevo_limite THEN
        RAISE EXCEPTION
            'El nuevo límite del convenio (%) es menor que el total ya pagado (%)',
            v_nuevo_limite,
            v_total_pagado;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_proteger_limite_convenio_pagado
    BEFORE UPDATE OF monto_100, monto_bdt, activo ON convenio
    FOR EACH ROW EXECUTE FUNCTION fn_proteger_limite_convenio_pagado();
CREATE TRIGGER trg_audit_pago_indemnizacion
    AFTER INSERT OR UPDATE ON pago_indemnizacion
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_pago');
CREATE TRIGGER trg_prevent_delete_pago_indemnizacion
    BEFORE DELETE ON pago_indemnizacion
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_pago_indemnizacion
    BEFORE UPDATE OF activo ON pago_indemnizacion
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- ============================================================
-- 6. ALERTAS DE ORV: EVENTO + FUNCIÓN PARA EJECUCIÓN DIARIA
-- ============================================================

-- Si una instalación anterior ya contiene duplicados activos, se conserva
-- como vigente la alerta más reciente y las demás quedan cerradas.
WITH alertas_duplicadas AS (
    SELECT
        id_alerta,
        ROW_NUMBER() OVER (
            PARTITION BY entidad_relacionada_tipo, entidad_relacionada_id, tipo
            ORDER BY fecha_creacion DESC, id_alerta DESC
        ) AS rn
    FROM alertas
    WHERE entidad_relacionada_tipo = 'orv'
      AND tipo = 'vencimiento_orv'
      AND esta_activa = TRUE
      AND activo = TRUE
)
UPDATE alertas a
   SET esta_activa = FALSE,
       observaciones = CONCAT_WS(
           E'\n',
           a.observaciones,
           'Cerrada por la migración 004 al consolidar alertas ORV duplicadas.'
       )
  FROM alertas_duplicadas d
 WHERE a.id_alerta = d.id_alerta
   AND d.rn > 1;

CREATE UNIQUE INDEX uq_alerta_orv_vencida_activa
    ON alertas(entidad_relacionada_tipo, entidad_relacionada_id, tipo)
    WHERE entidad_relacionada_tipo = 'orv'
      AND tipo = 'vencimiento_orv'
      AND esta_activa = TRUE
      AND activo = TRUE;

CREATE OR REPLACE FUNCTION fn_sincronizar_alerta_orv_vencido()
RETURNS TRIGGER AS $$
DECLARE
    v_usuario TEXT;
BEGIN
    v_usuario := current_setting('app.current_user_id', TRUE);
    IF v_usuario IS NULL OR v_usuario = '' THEN
        RAISE EXCEPTION 'La actualización de ORV requiere contexto de usuario para sincronizar alertas';
    END IF;

    PERFORM pg_advisory_xact_lock(904, NEW.id_orv);

    IF NEW.activo = TRUE AND NEW.fin_vigencia < CURRENT_DATE THEN
        IF NOT EXISTS (
            SELECT 1
            FROM alertas a
            WHERE a.entidad_relacionada_tipo = 'orv'
              AND a.entidad_relacionada_id = NEW.id_orv
              AND a.tipo = 'vencimiento_orv'
              AND a.esta_activa = TRUE
              AND a.activo = TRUE
        ) THEN
            INSERT INTO alertas (
                tipo, prioridad, titulo, descripcion,
                entidad_relacionada_id, entidad_relacionada_tipo,
                fecha_evento
            )
            VALUES (
                'vencimiento_orv',
                'alta',
                'ORV vencido',
                FORMAT(
                    'El ORV %s del núcleo agrario %s venció el %s.',
                    NEW.id_orv, NEW.id_nucleo, NEW.fin_vigencia
                ),
                NEW.id_orv,
                'orv',
                NEW.fin_vigencia
            )
            ON CONFLICT (
                entidad_relacionada_tipo,
                entidad_relacionada_id,
                tipo
            )
            WHERE entidad_relacionada_tipo = 'orv'
              AND tipo = 'vencimiento_orv'
              AND esta_activa = TRUE
              AND activo = TRUE
            DO NOTHING;
        END IF;
    ELSE
        UPDATE alertas
           SET esta_activa = FALSE,
               observaciones = CONCAT_WS(
                   E'\n',
                   observaciones,
                   'Cerrada automáticamente al actualizar la vigencia o dar de baja el ORV.'
               )
         WHERE entidad_relacionada_tipo = 'orv'
           AND entidad_relacionada_id = NEW.id_orv
           AND tipo = 'vencimiento_orv'
           AND esta_activa = TRUE
           AND activo = TRUE;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sincronizar_alerta_orv_vencido
    AFTER INSERT OR UPDATE OF fin_vigencia, activo ON orv
    FOR EACH ROW EXECUTE FUNCTION fn_sincronizar_alerta_orv_vencido();

CREATE OR REPLACE FUNCTION fn_generar_alertas_orv_vencidos(
    p_id_usuario INTEGER
)
RETURNS INTEGER AS $$
DECLARE
    v_insertadas INTEGER;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM usuario
        WHERE id_usuario = p_id_usuario AND activo = TRUE
    ) THEN
        RAISE EXCEPTION 'Se requiere un usuario activo para generar alertas';
    END IF;

    PERFORM set_config('app.current_user_id', p_id_usuario::TEXT, TRUE);
    PERFORM pg_advisory_xact_lock(904, 0);

    INSERT INTO alertas (
        tipo, prioridad, titulo, descripcion,
        entidad_relacionada_id, entidad_relacionada_tipo,
        fecha_evento
    )
    SELECT
        'vencimiento_orv',
        'alta',
        'ORV vencido',
        FORMAT(
            'El ORV %s del núcleo agrario %s venció el %s.',
            o.id_orv, o.id_nucleo, o.fin_vigencia
        ),
        o.id_orv,
        'orv',
        o.fin_vigencia
    FROM orv o
    WHERE o.activo = TRUE
      AND o.fin_vigencia < CURRENT_DATE
      AND NOT EXISTS (
          SELECT 1
          FROM alertas a
          WHERE a.entidad_relacionada_tipo = 'orv'
            AND a.entidad_relacionada_id = o.id_orv
            AND a.tipo = 'vencimiento_orv'
            AND a.esta_activa = TRUE
            AND a.activo = TRUE
      )
    ON CONFLICT (
        entidad_relacionada_tipo,
        entidad_relacionada_id,
        tipo
    )
    WHERE entidad_relacionada_tipo = 'orv'
      AND tipo = 'vencimiento_orv'
      AND esta_activa = TRUE
      AND activo = TRUE
    DO NOTHING;

    GET DIAGNOSTICS v_insertadas = ROW_COUNT;
    RETURN v_insertadas;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    v_usuario INTEGER;
BEGIN
    v_usuario := current_setting('app.current_user_id')::INTEGER;
    PERFORM fn_generar_alertas_orv_vencidos(v_usuario);
END;
$$;

-- ============================================================
-- 7. VERIFICACIONES DE PARIDAD Y REGISTRO DE LA MIGRACIÓN
-- ============================================================

DO $$
DECLARE
    v_orv_legacy INTEGER;
    v_orv_normalizado INTEGER;
    v_parcela_legacy INTEGER;
    v_parcela_normalizada INTEGER;
BEGIN
    SELECT COUNT(*)
      INTO v_orv_legacy
      FROM orv o
      CROSS JOIN LATERAL (VALUES
          (o.comisariado_presidente),
          (o.comisariado_secretario),
          (o.comisariado_tesorero),
          (o.consejo_vigilancia_presidente),
          (o.consejo_vigilancia_secretario1),
          (o.consejo_vigilancia_secretario2)
      ) AS v(nombre)
     WHERE NULLIF(BTRIM(v.nombre), '') IS NOT NULL;

    SELECT COUNT(*) INTO v_orv_normalizado FROM orv_integrante;

    SELECT COUNT(*)
      INTO v_parcela_legacy
      FROM parcela
     WHERE NULLIF(BTRIM(nombre_titular), '') IS NOT NULL;

    SELECT COUNT(*) INTO v_parcela_normalizada FROM parcela_titular;

    IF v_orv_legacy <> v_orv_normalizado THEN
        RAISE EXCEPTION
            'Paridad ORV fallida: % valores legacy contra % integrantes',
            v_orv_legacy, v_orv_normalizado;
    END IF;

    IF v_parcela_legacy <> v_parcela_normalizada THEN
        RAISE EXCEPTION
            'Paridad parcela fallida: % titulares legacy contra % relaciones',
            v_parcela_legacy, v_parcela_normalizada;
    END IF;
END;
$$;

INSERT INTO schema_migrations (version, descripcion)
VALUES (
    '004',
    'Personas normalizadas, titulares, ORV, minutas, acuerdos, versiones documentales, pagos y alertas ORV'
);

COMMIT;

-- Programación requerida después del despliegue:
-- ejecutar diariamente, dentro de una transacción, con un usuario
-- técnico activo:
--
--   BEGIN;
--   SELECT fn_generar_alertas_orv_vencidos(<id_usuario_tecnico>);
--   COMMIT;
--
-- La migración no instala pg_cron porque esa extensión depende de
-- la infraestructura y no está declarada en docker-compose.yml.
