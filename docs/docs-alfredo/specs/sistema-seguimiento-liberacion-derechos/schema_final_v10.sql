-- ==============================================================================
-- PROCURADURÍA AGRARIA
-- SISTEMA DE SEGUIMIENTO — LIBERACIÓN DDV EN PROPIEDAD SOCIAL
-- SCRIPT FINAL PostgreSQL/PostGIS
-- Versión final ajustada con validaciones, triggers y vistas calculadas
-- ==============================================================================

BEGIN;

-- 0. Dependencias espaciales
CREATE EXTENSION IF NOT EXISTS postgis;

-- ==============================================================================
-- MÓDULO 7 — CATÁLOGOS
-- ==============================================================================

CREATE TABLE entidad_federativa (
    id_entidad SERIAL PRIMARY KEY,
    clave_inegi CHAR(2) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE municipio (
    id_municipio SERIAL PRIMARY KEY,
    id_entidad INTEGER NOT NULL REFERENCES entidad_federativa(id_entidad),
    clave_inegi CHAR(5) UNIQUE NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_municipio_entidad_clave UNIQUE (id_entidad, clave_inegi)
);

-- ==============================================================================
-- MÓDULO 1 — ESTRUCTURA GEOGRÁFICA
-- ==============================================================================

CREATE TABLE tramo (
    id_tramo SERIAL PRIMARY KEY,
    clave_tramo VARCHAR(20) UNIQUE NOT NULL,
    nombre_tramo VARCHAR(200) NOT NULL,
    descripcion TEXT,
    geometria_linea GEOMETRY(MULTILINESTRING, 4326),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_registro DATE NOT NULL DEFAULT CURRENT_DATE,
    observaciones TEXT
);
CREATE INDEX idx_tramo_geometria ON tramo USING GIST (geometria_linea);

CREATE TABLE frente (
    id_frente SERIAL PRIMARY KEY,
    id_tramo INTEGER NOT NULL REFERENCES tramo(id_tramo),
    clave_frente VARCHAR(30) NOT NULL,
    nombre_frente VARCHAR(200) NOT NULL,
    descripcion TEXT,
    geometria_linea GEOMETRY(MULTILINESTRING, 4326),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_registro DATE NOT NULL DEFAULT CURRENT_DATE,
    observaciones TEXT,
    CONSTRAINT uq_frente_tramo_clave UNIQUE (id_tramo, clave_frente),
    -- Constraint habilitador para FK compuesta desde tramo_nucleo.
    CONSTRAINT uq_frente_tramo_id UNIQUE (id_tramo, id_frente)
);
CREATE INDEX idx_frente_geometria ON frente USING GIST (geometria_linea);
CREATE INDEX idx_frente_id_tramo ON frente(id_tramo);

CREATE TABLE nucleo_agrario (
    id_nucleo SERIAL PRIMARY KEY,
    id_municipio INTEGER NOT NULL REFERENCES municipio(id_municipio),
    nombre_nucleo VARCHAR(300) NOT NULL,
    tipo_nucleo VARCHAR(20) NOT NULL CHECK (tipo_nucleo IN ('ejido', 'comunidad')),
    comunidad_indigena BOOLEAN NOT NULL DEFAULT FALSE,
    residencia VARCHAR(300),
    geometria_poligono GEOMETRY(MULTIPOLYGON, 4326),
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    observaciones TEXT
);
CREATE INDEX idx_nucleo_geometria ON nucleo_agrario USING GIST (geometria_poligono);
CREATE INDEX idx_nucleo_id_municipio ON nucleo_agrario(id_municipio);

-- ==============================================================================
-- MÓDULO 2 — USUARIOS Y CONTROL DE ACCESO
-- ==============================================================================

CREATE TABLE usuario (
    id_usuario SERIAL PRIMARY KEY,
    nombre VARCHAR(250) NOT NULL,
    apellido_paterno VARCHAR(250) NOT NULL,
    apellido_materno VARCHAR(250),
    correo VARCHAR(320) UNIQUE NOT NULL,
    contrasena_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(30) NOT NULL CHECK (rol IN ('admin', 'operador', 'analista', 'geografo')),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_alta TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_baja TIMESTAMPTZ,
    observaciones TEXT,
    CONSTRAINT chk_usuario_fecha_baja CHECK (fecha_baja IS NULL OR fecha_baja >= fecha_alta)
);

CREATE TABLE usuario_frente (
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario),
    id_frente INTEGER NOT NULL REFERENCES frente(id_frente),
    fecha_asignacion DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_fin DATE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    observaciones TEXT,
    PRIMARY KEY (id_usuario, id_frente),
    CONSTRAINT chk_usuario_frente_fecha_fin CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_asignacion)
);
CREATE INDEX idx_usuario_frente_id_frente ON usuario_frente(id_frente);

-- ==============================================================================
-- MÓDULO 3 — PARCELAS Y ORV
-- ==============================================================================

CREATE TABLE orv (
    id_orv SERIAL PRIMARY KEY,
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    numero_orv VARCHAR(50),
    fecha_padron DATE,
    numero_ejidatarios_comuneros INTEGER CHECK (numero_ejidatarios_comuneros >= 0),
    inicio_vigencia DATE NOT NULL,
    fin_vigencia DATE NOT NULL,
    orv_vigente BOOLEAN NOT NULL DEFAULT FALSE,
    acta_eleccion_inscrita_ran BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_disponible BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_faltante TEXT,
    comisariado_presidente VARCHAR(300),
    comisariado_secretario VARCHAR(300),
    comisariado_tesorero VARCHAR(300),
    consejo_vigilancia_presidente VARCHAR(300),
    consejo_vigilancia_secretario1 VARCHAR(300),
    consejo_vigilancia_secretario2 VARCHAR(300),
    observaciones TEXT,
    CONSTRAINT chk_orv_fechas_vigencia CHECK (fin_vigencia > inicio_vigencia)
);
CREATE INDEX idx_orv_id_nucleo ON orv(id_nucleo);
CREATE UNIQUE INDEX idx_orv_vigente ON orv(id_nucleo) WHERE orv_vigente = TRUE;

CREATE TABLE parcela (
    id_parcela SERIAL PRIMARY KEY,
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    tipo_parcela VARCHAR(30) CHECK (tipo_parcela IN ('individual', 'copropiedad')),
    no_parcela_ppt VARCHAR(50),
    certificado_parcelario VARCHAR(100),
    folio_derechos VARCHAR(100),
    constancia_vigencia_fecha DATE,
    nombre_titular VARCHAR(300),
    documentacion_disponible BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_faltante TEXT,
    observaciones TEXT,
    -- Constraint habilitador para FK compuesta desde afectacion.
    CONSTRAINT uq_parcela_nucleo_id UNIQUE (id_nucleo, id_parcela)
);
CREATE INDEX idx_parcela_id_nucleo ON parcela(id_nucleo);
CREATE UNIQUE INDEX uq_parcela_nucleo_no_parcela
    ON parcela(id_nucleo, no_parcela_ppt)
    WHERE no_parcela_ppt IS NOT NULL;

-- ==============================================================================
-- MÓDULO 1.4 — CRUCES TRAMO-NÚCLEO
-- ==============================================================================

CREATE TABLE tramo_nucleo (
    id_tramo_nucleo SERIAL PRIMARY KEY,
    id_tramo INTEGER NOT NULL REFERENCES tramo(id_tramo),
    id_frente INTEGER NOT NULL REFERENCES frente(id_frente),
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    consecutivo INTEGER NOT NULL,
    numero_tramo VARCHAR(50),
    geometria_segmento GEOMETRY(MULTILINESTRING, 4326),
    longitud_m NUMERIC(14,2) CHECK (longitud_m >= 0),
    no_parcela_solar VARCHAR(100),
    es_expropiacion BOOLEAN NOT NULL DEFAULT FALSE,
    causa_problema TEXT,
    validado_liberado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_validacion_liberado TIMESTAMPTZ,
    id_usuario_validacion INTEGER REFERENCES usuario(id_usuario),
    proyecto_no_afecta_uso_comun BOOLEAN,
    observaciones TEXT,
    CONSTRAINT uq_tramo_nucleo_consecutivo UNIQUE (id_tramo, consecutivo),
    CONSTRAINT fk_tramo_nucleo_frente_mismo_tramo
        FOREIGN KEY (id_tramo, id_frente) REFERENCES frente(id_tramo, id_frente),
    -- Constraint habilitador para FKs compuestas desde afectacion y bitacora.
    CONSTRAINT uq_tramo_nucleo_nucleo_id UNIQUE (id_nucleo, id_tramo_nucleo),
    CONSTRAINT chk_tramo_nucleo_validacion_fecha
        CHECK (validado_liberado = FALSE OR fecha_validacion_liberado IS NOT NULL),
    CONSTRAINT chk_tramo_nucleo_validacion_usuario
        CHECK (validado_liberado = FALSE OR id_usuario_validacion IS NOT NULL)
);
CREATE INDEX idx_tramo_nucleo_geom ON tramo_nucleo USING GIST (geometria_segmento);
CREATE INDEX idx_tramo_nucleo_id_tramo ON tramo_nucleo(id_tramo);
CREATE INDEX idx_tramo_nucleo_id_frente ON tramo_nucleo(id_frente);
CREATE INDEX idx_tramo_nucleo_id_nucleo ON tramo_nucleo(id_nucleo);

-- ==============================================================================
-- MÓDULO 4 — PROCESO OPERATIVO
-- ==============================================================================

CREATE TABLE afectacion (
    id_afectacion SERIAL PRIMARY KEY,
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    id_tramo_nucleo INTEGER NOT NULL,
    id_parcela INTEGER,
    tipo_afectacion VARCHAR(20) NOT NULL CHECK (tipo_afectacion IN ('colectivo', 'individual')),
    tipo_tenencia VARCHAR(80) NOT NULL,
    subtipo_tenencia VARCHAR(80),
    destino_superficie VARCHAR(80),
    superficie_afectada_ha NUMERIC(12,4) CHECK (superficie_afectada_ha >= 0),
    num_personas_afectadas INTEGER CHECK (num_personas_afectadas >= 0),
    situacion_juridica TEXT,
    documentacion_disponible BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_faltante TEXT,
    observaciones TEXT,
    CONSTRAINT fk_afectacion_tramo_nucleo_mismo_nucleo
        FOREIGN KEY (id_nucleo, id_tramo_nucleo) REFERENCES tramo_nucleo(id_nucleo, id_tramo_nucleo),
    CONSTRAINT fk_afectacion_parcela_mismo_nucleo
        FOREIGN KEY (id_nucleo, id_parcela) REFERENCES parcela(id_nucleo, id_parcela),
    CONSTRAINT chk_afectacion_individual_parcela
        CHECK (tipo_afectacion <> 'individual' OR id_parcela IS NOT NULL),
    -- Constraint habilitador para convenio y tramite_fifonafe.
    CONSTRAINT uq_afectacion_tramo_id_tipo UNIQUE (id_tramo_nucleo, id_afectacion, tipo_afectacion)
);
CREATE INDEX idx_afectacion_id_nucleo ON afectacion(id_nucleo);
CREATE INDEX idx_afectacion_id_tramo_nucleo ON afectacion(id_tramo_nucleo);
CREATE INDEX idx_afectacion_id_parcela ON afectacion(id_parcela);

CREATE TABLE actividad_campo (
    id_actividad SERIAL PRIMARY KEY,
    id_tramo_nucleo INTEGER NOT NULL REFERENCES tramo_nucleo(id_tramo_nucleo),
    tipo_actividad VARCHAR(50) NOT NULL CHECK (tipo_actividad IN ('sensibilizacion', 'caminamiento')),
    contexto_proceso VARCHAR(50) NOT NULL DEFAULT 'cop_original'
        CHECK (contexto_proceso IN ('cop_original', 'superficie_adicional', 'obras_complementarias', 'ampliacion', 'ampliacion_remanente')),
    fecha_programada DATE,
    fecha_realizada DATE,
    resultado TEXT,
    id_usuario_registro INTEGER REFERENCES usuario(id_usuario),
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    observaciones TEXT
);
CREATE INDEX idx_actividad_campo_id_tramo_nucleo ON actividad_campo(id_tramo_nucleo);
CREATE INDEX idx_actividad_campo_id_usuario ON actividad_campo(id_usuario_registro);
-- Evita duplicados incluso cuando fecha_programada sea NULL.
CREATE UNIQUE INDEX uq_actividad_campo_control
ON actividad_campo(
    id_tramo_nucleo,
    tipo_actividad,
    contexto_proceso,
    COALESCE(fecha_programada, DATE '1900-01-01')
);

CREATE TABLE asamblea (
    id_asamblea SERIAL PRIMARY KEY,
    id_tramo_nucleo INTEGER NOT NULL REFERENCES tramo_nucleo(id_tramo_nucleo),
    tipo_asamblea VARCHAR(50) NOT NULL CHECK (tipo_asamblea IN ('informacion', 'anuencia', 'retiro_fondos', 'conciliacion', 'no_verificativo')),
    contexto_proceso VARCHAR(50)
        CHECK (contexto_proceso IN ('cop_original', 'superficie_adicional', 'obras_complementarias', 'ampliacion', 'ampliacion_remanente', 'retiro_fondos')),
    fecha_exp_1a DATE,
    fecha_prog_1a DATE,
    fecha_exp_2a DATE,
    fecha_prog_2a DATE,
    fecha_realizada DATE,
    resultado_anuencia VARCHAR(30) NOT NULL DEFAULT 'pendiente'
        CHECK (resultado_anuencia IN ('otorgada', 'negada', 'pendiente', 'no_aplica')),
    ingreso_ran_fecha DATE,
    numero_solicitud_ran VARCHAR(100),
    calificacion_registral_ran TEXT,
    acta_inscripcion_fecha_ran DATE,
    documentacion_disponible BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_faltante TEXT,
    id_usuario_registro INTEGER REFERENCES usuario(id_usuario),
    observaciones TEXT,
    -- Constraint habilitador para FK compuesta desde convenio.
    CONSTRAINT uq_asamblea_tramo_id UNIQUE (id_tramo_nucleo, id_asamblea)
);
CREATE INDEX idx_asamblea_id_tramo_nucleo ON asamblea(id_tramo_nucleo);
CREATE INDEX idx_asamblea_id_usuario ON asamblea(id_usuario_registro);

CREATE TABLE convenio (
    id_convenio SERIAL PRIMARY KEY,
    id_tramo_nucleo INTEGER NOT NULL REFERENCES tramo_nucleo(id_tramo_nucleo),
    id_afectacion INTEGER NOT NULL,
    id_convenio_padre INTEGER,
    id_asamblea_autorizacion INTEGER,
    tipo_afectacion VARCHAR(20) NOT NULL CHECK (tipo_afectacion IN ('colectivo', 'individual')),
    tipo_convenio VARCHAR(50) NOT NULL
        CHECK (tipo_convenio IN ('cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias', 'ampliacion', 'ampliacion_remanente')),
    fecha_firma DATE,
    monto_100 NUMERIC(18,2) CHECK (monto_100 >= 0),
    monto_90 NUMERIC(18,2) CHECK (monto_90 >= 0),
    monto_bdt NUMERIC(18,2) CHECK (monto_bdt >= 0),
    superficie_total_ha NUMERIC(12,4) CHECK (superficie_total_ha >= 0),
    superficie_real_afectada_ha NUMERIC(12,4) CHECK (superficie_real_afectada_ha >= 0),
    superficie_adicional_ha NUMERIC(12,4) CHECK (superficie_adicional_ha >= 0),
    ingreso_ran_fecha DATE,
    numero_solicitud_ingreso VARCHAR(100),
    calificacion_registral TEXT,
    convenio_inscrito_fecha_ran DATE,
    documentacion_disponible BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_faltante TEXT,
    id_usuario_registro INTEGER REFERENCES usuario(id_usuario),
    observaciones TEXT,

    -- Constraints únicos habilitadores.
    CONSTRAINT uq_convenio_tramo_id UNIQUE (id_tramo_nucleo, id_convenio),
    CONSTRAINT uq_convenio_tramo_id_tipo UNIQUE (id_tramo_nucleo, id_convenio, tipo_afectacion),

    -- FK compuesta hacia afectacion: garantiza mismo cruce y mismo tipo de afectación.
    CONSTRAINT fk_convenio_afectacion_compuesta
        FOREIGN KEY (id_tramo_nucleo, id_afectacion, tipo_afectacion)
        REFERENCES afectacion(id_tramo_nucleo, id_afectacion, tipo_afectacion),

    -- FK compuesta recursiva: garantiza convenio padre del mismo cruce y tipo de afectación.
    CONSTRAINT fk_convenio_padre_recursiva
        FOREIGN KEY (id_tramo_nucleo, id_convenio_padre, tipo_afectacion)
        REFERENCES convenio(id_tramo_nucleo, id_convenio, tipo_afectacion),

    -- FK compuesta hacia asamblea: impide que el convenio apunte a asambleas de otro cruce.
    CONSTRAINT fk_convenio_asamblea_compuesta
        FOREIGN KEY (id_tramo_nucleo, id_asamblea_autorizacion)
        REFERENCES asamblea(id_tramo_nucleo, id_asamblea),

    CONSTRAINT chk_convenio_padre_no_autorreferencia
        CHECK (id_convenio_padre IS NULL OR id_convenio <> id_convenio_padre),

    CONSTRAINT chk_convenio_reglas_tipo_padre
        CHECK (
            (tipo_convenio = 'cop_original' AND id_convenio_padre IS NULL)
            OR
            (tipo_convenio IN ('modificatorio', 'superficie_adicional', 'ampliacion', 'ampliacion_remanente')
             AND id_convenio_padre IS NOT NULL)
            OR
            (tipo_convenio = 'obras_complementarias')
        ),

    -- Regla de negocio: COP original colectivo requiere asamblea autorizadora.
    CONSTRAINT chk_convenio_cop_colectivo_asamblea
        CHECK (
            NOT (tipo_afectacion = 'colectivo' AND tipo_convenio = 'cop_original')
            OR id_asamblea_autorizacion IS NOT NULL
        )
);
CREATE INDEX idx_convenio_id_tramo_nucleo ON convenio(id_tramo_nucleo);
CREATE INDEX idx_convenio_id_afectacion ON convenio(id_afectacion);
CREATE INDEX idx_convenio_id_convenio_padre ON convenio(id_convenio_padre);
CREATE INDEX idx_convenio_id_asamblea_autorizacion ON convenio(id_asamblea_autorizacion);
CREATE INDEX idx_convenio_id_usuario ON convenio(id_usuario_registro);

-- ==============================================================================
-- TRIGGERS Y FUNCIONES — Validación de asamblea autorizadora
-- ==============================================================================

CREATE OR REPLACE FUNCTION fn_validar_convenio_asamblea_autorizacion()
RETURNS TRIGGER AS $$
DECLARE
    v_tipo VARCHAR(50);
    v_res VARCHAR(30);
BEGIN
    IF NEW.id_asamblea_autorizacion IS NOT NULL THEN
        SELECT a.tipo_asamblea, a.resultado_anuencia
        INTO v_tipo, v_res
        FROM asamblea a
        WHERE a.id_asamblea = NEW.id_asamblea_autorizacion
          AND a.id_tramo_nucleo = NEW.id_tramo_nucleo;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Integridad fallida: la asamblea autorizadora % no existe para el cruce tramo_nucleo %.',
                NEW.id_asamblea_autorizacion, NEW.id_tramo_nucleo;
        END IF;

        IF v_tipo IS DISTINCT FROM 'anuencia'
           OR v_res IS DISTINCT FROM 'otorgada' THEN
            RAISE EXCEPTION 'Integridad fallida: la asamblea autorizadora debe ser de tipo anuencia y tener resultado otorgada.';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_convenio_asamblea_autorizacion_biu
BEFORE INSERT OR UPDATE OF id_asamblea_autorizacion, id_tramo_nucleo ON convenio
FOR EACH ROW
EXECUTE FUNCTION fn_validar_convenio_asamblea_autorizacion();

CREATE OR REPLACE FUNCTION fn_prevenir_invalidar_asamblea_autorizadora()
RETURNS TRIGGER AS $$
BEGIN
    IF (NEW.tipo_asamblea IS DISTINCT FROM 'anuencia'
        OR NEW.resultado_anuencia IS DISTINCT FROM 'otorgada')
       AND EXISTS (
           SELECT 1
           FROM convenio c
           WHERE c.id_tramo_nucleo = NEW.id_tramo_nucleo
             AND c.id_asamblea_autorizacion = NEW.id_asamblea
       ) THEN
        RAISE EXCEPTION 'Integridad fallida: no se puede cambiar la asamblea %, porque autoriza uno o más convenios.', NEW.id_asamblea;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_asamblea_no_invalidar_autorizadora_bu
BEFORE UPDATE OF tipo_asamblea, resultado_anuencia ON asamblea
FOR EACH ROW
EXECUTE FUNCTION fn_prevenir_invalidar_asamblea_autorizadora();

-- ==============================================================================
-- MÓDULO 5 — FIFONAFE
-- ==============================================================================

CREATE TABLE tramite_fifonafe (
    id_tramite_fifonafe SERIAL PRIMARY KEY,
    id_tramo_nucleo INTEGER NOT NULL REFERENCES tramo_nucleo(id_tramo_nucleo),
    id_convenio INTEGER,
    id_afectacion INTEGER,
    tipo_afectacion VARCHAR(20) NOT NULL CHECK (tipo_afectacion IN ('colectivo', 'individual')),
    tipo_tramite VARCHAR(50) NOT NULL CHECK (tipo_tramite IN ('retiro_fondos', 'indemnizacion', 'informe_no_conflictos')),
    estatus VARCHAR(30) NOT NULL DEFAULT 'pendiente' CHECK (estatus IN ('programado', 'pendiente', 'completo', 'cancelado')),
    hay_conflictos BOOLEAN,
    no_oficio_fifonafe_a_dgaopr VARCHAR(50),
    no_oficio_dgaopr_a_repr VARCHAR(50),
    no_oficio_rpta_repr_a_dgaopr VARCHAR(50),
    no_oficio_rpta_dgaopr_a_fifonafe VARCHAR(50),
    fecha_oficio_fifonafe_a_dgaopr DATE,
    fecha_oficio_dgaopr_a_repr DATE,
    fecha_oficio_rpta_repr_a_dgaopr DATE,
    fecha_oficio_rpta_dgaopr_a_fifonafe DATE,
    observaciones TEXT,

    -- Exactamente un origen: convenio o afectación, pero nunca ambos ni ninguno.
    CONSTRAINT chk_tramite_fifonafe_origen_xor
        CHECK (
            (id_convenio IS NOT NULL AND id_afectacion IS NULL)
            OR
            (id_convenio IS NULL AND id_afectacion IS NOT NULL)
        ),

    CONSTRAINT fk_tramite_convenio_compuesta
        FOREIGN KEY (id_tramo_nucleo, id_convenio, tipo_afectacion)
        REFERENCES convenio(id_tramo_nucleo, id_convenio, tipo_afectacion),

    CONSTRAINT fk_tramite_afectacion_compuesta
        FOREIGN KEY (id_tramo_nucleo, id_afectacion, tipo_afectacion)
        REFERENCES afectacion(id_tramo_nucleo, id_afectacion, tipo_afectacion),

    CONSTRAINT chk_tramite_tipo_afectacion
        CHECK (
            (tipo_tramite = 'retiro_fondos' AND tipo_afectacion = 'colectivo')
            OR
            (tipo_tramite = 'indemnizacion')
            OR
            (tipo_tramite = 'informe_no_conflictos')
        )
);
CREATE INDEX idx_tramite_fifonafe_id_tramo_nucleo ON tramite_fifonafe(id_tramo_nucleo);
CREATE INDEX idx_tramite_fifonafe_id_convenio ON tramite_fifonafe(id_convenio);
CREATE INDEX idx_tramite_fifonafe_id_afectacion ON tramite_fifonafe(id_afectacion);

-- ==============================================================================
-- MÓDULO 6 — AUDITORÍA
-- ==============================================================================

CREATE TABLE bitacora (
    id_bitacora BIGSERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL,
    id_nucleo INTEGER,
    id_tramo_nucleo INTEGER,
    entidad_tipo VARCHAR(100) NOT NULL,
    entidad_id BIGINT,
    accion VARCHAR(30) NOT NULL CHECK (accion IN ('insert', 'update', 'delete', 'validacion', 'cambio_estado', 'carga_documento')),
    detalle_cambio TEXT,
    valor_anterior JSONB,
    valor_nuevo JSONB,
    fecha_hora TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_origen INET,
    user_agent TEXT,

    CONSTRAINT fk_bitacora_usuario FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario),
    CONSTRAINT fk_bitacora_nucleo FOREIGN KEY (id_nucleo) REFERENCES nucleo_agrario(id_nucleo),
    CONSTRAINT fk_bitacora_tramo_nucleo_simple FOREIGN KEY (id_tramo_nucleo) REFERENCES tramo_nucleo(id_tramo_nucleo),
    CONSTRAINT fk_bitacora_tramo_nucleo_compuesta
        FOREIGN KEY (id_nucleo, id_tramo_nucleo)
        REFERENCES tramo_nucleo(id_nucleo, id_tramo_nucleo)
);
CREATE INDEX idx_bitacora_id_usuario ON bitacora(id_usuario);
CREATE INDEX idx_bitacora_id_nucleo ON bitacora(id_nucleo);
CREATE INDEX idx_bitacora_id_tramo_nucleo ON bitacora(id_tramo_nucleo);
CREATE INDEX idx_bitacora_fecha_hora ON bitacora(fecha_hora);

-- ==============================================================================
-- VISTAS RECOMENDADAS — CAMPOS CALCULADOS PARA DASHBOARD
-- ==============================================================================

CREATE OR REPLACE VIEW vw_tramo_nucleo_estado AS
SELECT
    tn.id_tramo_nucleo,
    tn.id_tramo,
    tn.id_frente,
    tn.id_nucleo,
    tn.consecutivo,
    tn.numero_tramo,
    tn.geometria_segmento,
    tn.longitud_m,
    tn.no_parcela_solar,
    tn.es_expropiacion,
    tn.causa_problema,
    tn.validado_liberado,
    tn.fecha_validacion_liberado,
    tn.id_usuario_validacion,
    tn.proyecto_no_afecta_uso_comun,
    tn.observaciones,

    EXISTS (
        SELECT 1
        FROM asamblea a
        WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo
          AND a.tipo_asamblea = 'anuencia'
          AND a.resultado_anuencia = 'otorgada'
    ) AS tiene_anuencia,

    EXISTS (
        SELECT 1
        FROM asamblea a
        WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo
          AND a.tipo_asamblea = 'anuencia'
          AND a.resultado_anuencia = 'otorgada'
          AND a.acta_inscripcion_fecha_ran IS NOT NULL
    ) AS acta_anuencia_inscrita_ran,

    EXISTS (
        SELECT 1
        FROM convenio c
        WHERE c.id_tramo_nucleo = tn.id_tramo_nucleo
    ) AS tiene_convenio,

    EXISTS (
        SELECT 1
        FROM convenio c
        WHERE c.id_tramo_nucleo = tn.id_tramo_nucleo
          AND c.convenio_inscrito_fecha_ran IS NOT NULL
    ) AS tiene_convenio_inscrito_ran,

    EXISTS (
        SELECT 1
        FROM actividad_campo ac
        WHERE ac.id_tramo_nucleo = tn.id_tramo_nucleo
    ) AS tiene_actividad_campo,

    EXISTS (
        SELECT 1
        FROM tramite_fifonafe tf
        WHERE tf.id_tramo_nucleo = tn.id_tramo_nucleo
          AND tf.estatus = 'completo'
    ) AS tiene_tramite_fifonafe_completo,

    CASE
        WHEN tn.validado_liberado = TRUE THEN 'liberado'
        WHEN tn.es_expropiacion = TRUE THEN 'problema'
        WHEN NULLIF(BTRIM(tn.causa_problema), '') IS NOT NULL THEN 'problema'
        WHEN EXISTS (SELECT 1 FROM convenio c WHERE c.id_tramo_nucleo = tn.id_tramo_nucleo) THEN 'en_proceso'
        WHEN EXISTS (SELECT 1 FROM asamblea a WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo) THEN 'en_proceso'
        WHEN EXISTS (SELECT 1 FROM actividad_campo ac WHERE ac.id_tramo_nucleo = tn.id_tramo_nucleo) THEN 'en_proceso'
        WHEN EXISTS (SELECT 1 FROM afectacion af WHERE af.id_tramo_nucleo = tn.id_tramo_nucleo) THEN 'en_proceso'
        WHEN EXISTS (SELECT 1 FROM tramite_fifonafe tf WHERE tf.id_tramo_nucleo = tn.id_tramo_nucleo) THEN 'en_proceso'
        ELSE 'pendiente'
    END AS estado_operativo_calculado
FROM tramo_nucleo tn;

CREATE OR REPLACE VIEW vw_dashboard_liberacion AS
SELECT
    v.id_tramo_nucleo,
    t.id_tramo,
    t.clave_tramo,
    t.nombre_tramo,
    f.id_frente,
    f.clave_frente,
    f.nombre_frente,
    n.id_nucleo,
    n.nombre_nucleo,
    n.tipo_nucleo,
    n.comunidad_indigena,
    n.residencia,
    m.id_municipio,
    m.nombre AS municipio,
    ef.id_entidad,
    ef.nombre AS entidad_federativa,
    v.consecutivo,
    v.numero_tramo,
    v.longitud_m,
    v.es_expropiacion,
    v.proyecto_no_afecta_uso_comun,
    v.tiene_anuencia,
    v.acta_anuencia_inscrita_ran,
    v.tiene_convenio,
    v.tiene_convenio_inscrito_ran,
    v.tiene_actividad_campo,
    v.tiene_tramite_fifonafe_completo,
    v.validado_liberado,
    v.fecha_validacion_liberado,
    v.causa_problema,
    v.estado_operativo_calculado,
    COALESCE(af.total_superficie_afectada_ha, 0) AS total_superficie_afectada_ha,
    COALESCE(cv.total_monto_100, 0) AS total_monto_100,
    COALESCE(cv.total_monto_90, 0) AS total_monto_90,
    COALESCE(cv.total_monto_bdt, 0) AS total_monto_bdt,
    COALESCE(cv.total_convenios, 0) AS total_convenios
FROM vw_tramo_nucleo_estado v
JOIN tramo t ON t.id_tramo = v.id_tramo
JOIN frente f ON f.id_frente = v.id_frente
JOIN nucleo_agrario n ON n.id_nucleo = v.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa ef ON ef.id_entidad = m.id_entidad
LEFT JOIN (
    SELECT
        id_tramo_nucleo,
        SUM(COALESCE(superficie_afectada_ha, 0)) AS total_superficie_afectada_ha
    FROM afectacion
    GROUP BY id_tramo_nucleo
) af ON af.id_tramo_nucleo = v.id_tramo_nucleo
LEFT JOIN (
    SELECT
        id_tramo_nucleo,
        COUNT(*) AS total_convenios,
        SUM(COALESCE(monto_100, 0)) AS total_monto_100,
        SUM(COALESCE(monto_90, 0)) AS total_monto_90,
        SUM(COALESCE(monto_bdt, 0)) AS total_monto_bdt
    FROM convenio
    GROUP BY id_tramo_nucleo
) cv ON cv.id_tramo_nucleo = v.id_tramo_nucleo;

-- Geometría calculada por tramo a partir de segmentos de cruce, con fallback al trazo original.
CREATE OR REPLACE VIEW vmz_geometria_tramo AS
SELECT
    t.id_tramo,
    t.clave_tramo,
    t.nombre_tramo,
    COALESCE(gs.geometria_linea, t.geometria_linea) AS geometria_linea
FROM tramo t
LEFT JOIN (
    SELECT
        id_tramo,
        ST_Multi(ST_CollectionExtract(ST_Union(geometria_segmento), 2))::GEOMETRY(MULTILINESTRING, 4326) AS geometria_linea
    FROM tramo_nucleo
    WHERE geometria_segmento IS NOT NULL
    GROUP BY id_tramo
) gs ON gs.id_tramo = t.id_tramo;

COMMIT;
