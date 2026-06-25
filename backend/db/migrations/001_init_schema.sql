-- Migración Inicial: Esquema Base y Lógica Geoespacial
CREATE EXTENSION IF NOT EXISTS postgis;

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

CREATE TABLE tramo (
    id_tramo SERIAL PRIMARY KEY,
    clave_tramo VARCHAR(20) UNIQUE NOT NULL,
    nombre_tramo VARCHAR(200) NOT NULL,
    descripcion TEXT,
    ancho_total_derecho_via_m NUMERIC(6,2) DEFAULT 40.00 CHECK (ancho_total_derecho_via_m > 0),
    geometria_linea GEOMETRY(MULTILINESTRING, 4326),
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

CREATE TABLE frente (
    id_frente SERIAL PRIMARY KEY,
    id_tramo INTEGER NOT NULL REFERENCES tramo(id_tramo),
    clave_frente VARCHAR(30) NOT NULL,
    nombre_frente VARCHAR(200) NOT NULL,
    descripcion TEXT,
    geometria_linea GEOMETRY(MULTILINESTRING, 4326),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_registro DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT uq_frente_tramo_clave UNIQUE (id_tramo, clave_frente),
    CONSTRAINT uq_frente_tramo_id UNIQUE (id_tramo, id_frente)
);

CREATE TABLE nucleo_agrario (
    id_nucleo SERIAL PRIMARY KEY,
    id_municipio INTEGER NOT NULL REFERENCES municipio(id_municipio),
    nombre_nucleo VARCHAR(300) NOT NULL,
    tipo_nucleo VARCHAR(20) NOT NULL CHECK (tipo_nucleo IN ('ejido', 'comunidad')),
    comunidad_indigena BOOLEAN NOT NULL DEFAULT FALSE,
    residencia VARCHAR(300),
    geometria_poligono GEOMETRY(MULTIPOLYGON, 4326),
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT,
    observaciones TEXT
);

CREATE TABLE tramo_nucleo (
    id_tramo_nucleo SERIAL PRIMARY KEY,
    id_tramo INTEGER NOT NULL REFERENCES tramo(id_tramo),
    id_frente INTEGER NOT NULL REFERENCES frente(id_frente),
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    consecutivo INTEGER NOT NULL,
    numero_tramo VARCHAR(50),
    geometria_segmento GEOMETRY(MULTILINESTRING, 4326),
    longitud_m NUMERIC(14,2) CHECK (longitud_m >= 0),
    es_expropiacion BOOLEAN NOT NULL DEFAULT FALSE,
    causa_problema TEXT,
    proyecto_no_afecta_uso_comun BOOLEAN,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT uq_tramo_nucleo_consecutivo UNIQUE (id_tramo, consecutivo),
    CONSTRAINT fk_tramo_nucleo_frente_mismo_tramo
        FOREIGN KEY (id_tramo, id_frente) REFERENCES frente(id_tramo, id_frente),
    CONSTRAINT uq_tramo_nucleo_nucleo_id UNIQUE (id_nucleo, id_tramo_nucleo)
);

CREATE TABLE usuario (
    id_usuario SERIAL PRIMARY KEY,
    nombre VARCHAR(250) NOT NULL,
    apellido_paterno VARCHAR(250) NOT NULL,
    apellido_materno VARCHAR(250),
    correo VARCHAR(320) UNIQUE NOT NULL,
    contrasena_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(30) NOT NULL CHECK (rol IN ('admin', 'operador', 'visualizador', 'geografo')),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_alta TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT,
    observaciones TEXT
);

CREATE TABLE bitacora (
    id_bitacora BIGSERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario),
    id_nucleo INTEGER REFERENCES nucleo_agrario(id_nucleo),
    id_tramo_nucleo INTEGER REFERENCES tramo_nucleo(id_tramo_nucleo),
    entidad_tipo VARCHAR(100) NOT NULL,
    entidad_id BIGINT,
    accion VARCHAR(30) NOT NULL CHECK (accion IN ('insert', 'update', 'delete', 'validacion', 'cambio_estado', 'carga_documento')),
    detalle_cambio TEXT,
    valor_anterior JSONB,
    valor_nuevo JSONB,
    fecha_hora TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_origen INET,
    user_agent TEXT
);

CREATE TABLE usuario_frente (
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario),
    id_frente INTEGER NOT NULL REFERENCES frente(id_frente),
    fecha_asignacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id_usuario, id_frente)
);


CREATE TABLE orv (
    id_orv SERIAL PRIMARY KEY,
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    numero_orv VARCHAR(50),
    inicio_vigencia DATE NOT NULL,
    fin_vigencia DATE NOT NULL,
    acta_eleccion_inscrita_ran BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_disponible BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_faltante TEXT,
    comisariado_presidente VARCHAR(300),
    comisariado_secretario VARCHAR(300),
    comisariado_tesorero VARCHAR(300),
    consejo_vigilancia_presidente VARCHAR(300),
    consejo_vigilancia_secretario1 VARCHAR(300),
    consejo_vigilancia_secretario2 VARCHAR(300),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT,
    observaciones TEXT
);

CREATE TABLE padron_historial (
    id_padron SERIAL PRIMARY KEY,
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    fecha_padron DATE NOT NULL,
    numero_ejidatarios_comuneros INTEGER NOT NULL CHECK (numero_ejidatarios_comuneros >= 0),
    id_usuario_registro INTEGER REFERENCES usuario(id_usuario),
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT uq_padron_nucleo UNIQUE (id_nucleo, id_padron)
);

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
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT uq_parcela_nucleo_id UNIQUE (id_nucleo, id_parcela)
);

CREATE TABLE afectacion (
    id_afectacion SERIAL PRIMARY KEY,
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    id_tramo_nucleo INTEGER NOT NULL,
    id_parcela INTEGER,
    tipo_afectacion VARCHAR(20) NOT NULL CHECK (tipo_afectacion IN ('colectivo', 'individual')),
    tipo_tenencia VARCHAR(80) NOT NULL,
    subtipo_tenencia VARCHAR(80),
    destino_superficie VARCHAR(80),
    no_parcela_solar VARCHAR(100),
    superficie_afectada_ha NUMERIC(12,4) CHECK (superficie_afectada_ha >= 0),
    geometria_afectacion GEOMETRY(Geometry, 4326),
    num_personas_afectadas INTEGER CHECK (num_personas_afectadas >= 0),
    situacion_juridica TEXT,
    documentacion_disponible BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_faltante TEXT,
    origen_registro VARCHAR(50) NOT NULL DEFAULT 'captura_sistema' CHECK (origen_registro IN ('migracion_excel', 'captura_sistema')),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT chk_afectacion_tipo_geometria CHECK (geometria_afectacion IS NULL OR ST_GeometryType(geometria_afectacion) IN ('ST_Polygon', 'ST_MultiPolygon')),
    CONSTRAINT chk_afectacion_geometria_valida CHECK (geometria_afectacion IS NULL OR ST_IsValid(geometria_afectacion)),
    CONSTRAINT chk_afectacion_srid CHECK (geometria_afectacion IS NULL OR ST_SRID(geometria_afectacion) = 4326),
    CONSTRAINT chk_geometria_requerida_nativos CHECK (origen_registro = 'migracion_excel' OR geometria_afectacion IS NOT NULL),
    CONSTRAINT chk_individual_requiere_parcela CHECK (tipo_afectacion = 'colectivo' OR id_parcela IS NOT NULL),
    CONSTRAINT fk_afectacion_tramo_nucleo_mismo_nucleo
        FOREIGN KEY (id_nucleo, id_tramo_nucleo) REFERENCES tramo_nucleo(id_nucleo, id_tramo_nucleo),
    CONSTRAINT fk_afectacion_parcela_mismo_nucleo
        FOREIGN KEY (id_nucleo, id_parcela) REFERENCES parcela(id_nucleo, id_parcela),
    CONSTRAINT uq_afectacion_tramo_id_tipo UNIQUE (id_tramo_nucleo, id_afectacion, tipo_afectacion)
);

CREATE INDEX idx_afectacion_geom ON afectacion USING GIST (geometria_afectacion);

CREATE TABLE actividad_campo (
    id_actividad SERIAL PRIMARY KEY,
    id_tramo_nucleo INTEGER NOT NULL REFERENCES tramo_nucleo(id_tramo_nucleo),
    tipo_actividad VARCHAR(50) NOT NULL CHECK (tipo_actividad IN ('sensibilizacion', 'caminamiento')),
    contexto_proceso VARCHAR(50) NOT NULL DEFAULT 'cop_original',
    fecha_programada DATE,
    fecha_realizada DATE,
    resultado TEXT,
    id_usuario_registro INTEGER REFERENCES usuario(id_usuario),
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT,
    observaciones TEXT
);

CREATE TABLE asamblea (
    id_asamblea SERIAL PRIMARY KEY,
    id_nucleo INTEGER NOT NULL,
    id_tramo_nucleo INTEGER NOT NULL,
    tipo_asamblea VARCHAR(50) NOT NULL CHECK (tipo_asamblea IN ('informacion', 'anuencia', 'retiro_fondos', 'conciliacion', 'no_verificativo')),
    contexto_proceso VARCHAR(50),
    fecha_exp_1a DATE,
    fecha_prog_1a DATE,
    fecha_exp_2a DATE,
    fecha_prog_2a DATE,
    fecha_realizada DATE,
    resultado_anuencia VARCHAR(30) NOT NULL DEFAULT 'pendiente' CHECK (resultado_anuencia IN ('otorgada', 'negada', 'pendiente', 'no_aplica')),
    estatus_asamblea VARCHAR(30) CHECK (estatus_asamblea IN ('programado', 'pendiente', 'completo')),
    ingreso_ran_fecha DATE,
    numero_solicitud_ran VARCHAR(100),
    calificacion_registral_ran TEXT,
    acta_inscripcion_fecha_ran DATE,
    documentacion_disponible BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_faltante TEXT,
    id_padron INTEGER,
    id_usuario_registro INTEGER REFERENCES usuario(id_usuario),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT fk_asamblea_tramo_nucleo FOREIGN KEY (id_nucleo, id_tramo_nucleo) REFERENCES tramo_nucleo(id_nucleo, id_tramo_nucleo),
    CONSTRAINT fk_asamblea_padron FOREIGN KEY (id_nucleo, id_padron) REFERENCES padron_historial(id_nucleo, id_padron),
    CONSTRAINT uq_asamblea_tramo_id UNIQUE (id_tramo_nucleo, id_asamblea)
);

CREATE TABLE convenio (
    id_convenio SERIAL PRIMARY KEY,
    id_tramo_nucleo INTEGER NOT NULL REFERENCES tramo_nucleo(id_tramo_nucleo),
    id_afectacion INTEGER NOT NULL,
    id_convenio_padre INTEGER,
    id_asamblea_autorizacion INTEGER,
    tipo_afectacion VARCHAR(20) NOT NULL CHECK (tipo_afectacion IN ('colectivo', 'individual')),
    tipo_convenio VARCHAR(50) NOT NULL CHECK (tipo_convenio IN (
        'cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias',
        'ampliacion', 'ampliacion_remanente'
    )),
    fecha_firma DATE,
    monto_100 NUMERIC(18,2) CHECK (monto_100 >= 0),
    monto_90 NUMERIC(18,2) CHECK (monto_90 >= 0),
    monto_bdt NUMERIC(18,2) CHECK (monto_bdt >= 0),
    superficie_total_ha NUMERIC(12,4) CHECK (superficie_total_ha >= 0),
    superficie_real_afectada_ha NUMERIC(12,4) CHECK (superficie_real_afectada_ha >= 0),
    superficie_adicional_ha NUMERIC(12,4) CHECK (superficie_adicional_ha >= 0),
    superficie_ampliacion_ha NUMERIC(12,4) CHECK (superficie_ampliacion_ha >= 0),
    ingreso_ran_fecha DATE,
    numero_solicitud_ingreso VARCHAR(100),
    calificacion_registral TEXT,
    convenio_inscrito_fecha_ran DATE,
    documentacion_disponible BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_faltante TEXT,
    id_usuario_registro INTEGER REFERENCES usuario(id_usuario),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT uq_convenio_linaje UNIQUE (id_tramo_nucleo, id_convenio, id_afectacion),
    CONSTRAINT fk_convenio_afectacion_compuesta
        FOREIGN KEY (id_tramo_nucleo, id_afectacion, tipo_afectacion)
        REFERENCES afectacion(id_tramo_nucleo, id_afectacion, tipo_afectacion),
    CONSTRAINT fk_convenio_padre_recursiva
        FOREIGN KEY (id_tramo_nucleo, id_convenio_padre, id_afectacion)
        REFERENCES convenio(id_tramo_nucleo, id_convenio, id_afectacion),
    CONSTRAINT fk_convenio_asamblea_compuesta
        FOREIGN KEY (id_tramo_nucleo, id_asamblea_autorizacion)
        REFERENCES asamblea(id_tramo_nucleo, id_asamblea),
    CONSTRAINT chk_tipo_convenio_por_afectacion CHECK (
        (tipo_afectacion = 'colectivo' AND tipo_convenio IN ('cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias'))
        OR
        (tipo_afectacion = 'individual' AND tipo_convenio IN ('cop_original', 'modificatorio', 'ampliacion', 'ampliacion_remanente'))
    ),
    CONSTRAINT chk_colectivo_requiere_asamblea CHECK (
        tipo_afectacion = 'individual' OR tipo_convenio IN ('modificatorio') OR id_asamblea_autorizacion IS NOT NULL
    ),
    CONSTRAINT chk_individual_sin_asamblea CHECK (
        tipo_afectacion = 'colectivo' OR id_asamblea_autorizacion IS NULL
    ),
    CONSTRAINT chk_modificatorio_requiere_padre CHECK (
        tipo_convenio != 'modificatorio' OR id_convenio_padre IS NOT NULL
    ),
    CONSTRAINT chk_bdt_no_obras_complementarias CHECK (
        (tipo_convenio = 'obras_complementarias' AND monto_bdt IS NULL)
        OR
        (tipo_convenio != 'obras_complementarias')
    ),
    CONSTRAINT chk_modificatorio_individual_restricciones CHECK (
        NOT (tipo_convenio = 'modificatorio' AND tipo_afectacion = 'individual')
        OR
        (superficie_total_ha IS NULL AND superficie_real_afectada_ha IS NULL AND superficie_adicional_ha IS NULL AND superficie_ampliacion_ha IS NULL AND monto_bdt IS NULL AND ingreso_ran_fecha IS NULL AND numero_solicitud_ingreso IS NULL AND calificacion_registral IS NULL AND convenio_inscrito_fecha_ran IS NULL)
    ),
    CONSTRAINT chk_superficie_exclusiva_estricta CHECK (
        (tipo_afectacion != 'individual' OR (superficie_real_afectada_ha IS NULL AND superficie_adicional_ha IS NULL))
        AND
        (tipo_afectacion != 'colectivo' OR (superficie_total_ha IS NULL AND superficie_ampliacion_ha IS NULL))
        AND
        (tipo_convenio != 'cop_original' OR tipo_afectacion != 'individual' OR superficie_ampliacion_ha IS NULL)
        AND
        (tipo_convenio NOT IN ('ampliacion', 'ampliacion_remanente') OR superficie_total_ha IS NULL)
        AND
        (tipo_convenio != 'superficie_adicional' OR superficie_real_afectada_ha IS NULL)
        AND
        (tipo_convenio NOT IN ('cop_original', 'obras_complementarias') OR tipo_afectacion != 'colectivo' OR superficie_adicional_ha IS NULL)
    )
);

CREATE TABLE tramite_fifonafe (
    id_tramite_fifonafe SERIAL PRIMARY KEY,
    id_tramo_nucleo INTEGER NOT NULL REFERENCES tramo_nucleo(id_tramo_nucleo),
    id_convenio INTEGER,
    id_afectacion INTEGER,
    tipo_afectacion VARCHAR(20) NOT NULL CHECK (tipo_afectacion IN ('colectivo', 'individual')),
    tipo_tramite VARCHAR(50) NOT NULL CHECK (tipo_tramite IN ('indemnizacion', 'informe_no_conflictos')),
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
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT,
    observaciones TEXT,
    CONSTRAINT fk_tramite_convenio_compuesta
        FOREIGN KEY (id_tramo_nucleo, id_convenio, id_afectacion)
        REFERENCES convenio(id_tramo_nucleo, id_convenio, id_afectacion),
    CONSTRAINT fk_tramite_afectacion_compuesta
        FOREIGN KEY (id_tramo_nucleo, id_afectacion, tipo_afectacion)
        REFERENCES afectacion(id_tramo_nucleo, id_afectacion, tipo_afectacion),
    CONSTRAINT chk_estatus_completo_requiere_oficios CHECK (
        estatus != 'completo' OR (
            no_oficio_fifonafe_a_dgaopr IS NOT NULL AND
            no_oficio_dgaopr_a_repr IS NOT NULL AND
            no_oficio_rpta_repr_a_dgaopr IS NOT NULL AND
            no_oficio_rpta_dgaopr_a_fifonafe IS NOT NULL AND
            fecha_oficio_fifonafe_a_dgaopr IS NOT NULL AND
            fecha_oficio_dgaopr_a_repr IS NOT NULL AND
            fecha_oficio_rpta_repr_a_dgaopr IS NOT NULL AND
            fecha_oficio_rpta_dgaopr_a_fifonafe IS NOT NULL
        )
    )
);

CREATE TABLE documentacion_soporte (
    id_documento SERIAL PRIMARY KEY,
    entidad_relacionada_id INTEGER NOT NULL,
    entidad_relacionada_tipo VARCHAR(50) NOT NULL CHECK (entidad_relacionada_tipo IN ('nucleo_agrario', 'afectacion', 'convenio', 'orv')),
    tipo_documento VARCHAR(100) NOT NULL,
    categoria VARCHAR(20) NOT NULL CHECK (categoria IN ('disponible', 'faltante')),
    es_critico BOOLEAN NOT NULL DEFAULT FALSE,
    url_archivo TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT,
    observaciones TEXT,
    fecha_carga TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE alertas (
    id_alerta SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('vencimiento_orv', 'evento_proximo', 'documento_faltante')),
    prioridad VARCHAR(10) NOT NULL CHECK (prioridad IN ('alta', 'media', 'baja')),
    titulo VARCHAR(255) NOT NULL,
    descripcion TEXT,
    entidad_relacionada_id INTEGER NOT NULL,
    entidad_relacionada_tipo VARCHAR(50) NOT NULL,
    fecha_evento DATE,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    esta_activa BOOLEAN NOT NULL DEFAULT TRUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER,
    motivo_baja TEXT,
    fecha_reactivacion TIMESTAMPTZ,
    id_usuario_reactivacion INTEGER,
    motivo_reactivacion TEXT
);

CREATE TABLE alertas_vistas (
    id_alerta INTEGER NOT NULL REFERENCES alertas(id_alerta) ON DELETE CASCADE,
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    fecha_vista TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id_alerta, id_usuario)
);

-- Validación de referencias dinámicas de documentación soporte
CREATE OR REPLACE FUNCTION fn_validar_documentacion_soporte_referencia() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.entidad_relacionada_tipo = 'nucleo_agrario' AND NOT EXISTS (SELECT 1 FROM nucleo_agrario WHERE id_nucleo = NEW.entidad_relacionada_id AND activo = TRUE) THEN
        RAISE EXCEPTION 'La documentación soporte referencia un núcleo agrario inexistente o inactivo';
    ELSIF NEW.entidad_relacionada_tipo = 'afectacion' AND NOT EXISTS (SELECT 1 FROM afectacion WHERE id_afectacion = NEW.entidad_relacionada_id AND activo = TRUE) THEN
        RAISE EXCEPTION 'La documentación soporte referencia una afectación inexistente o inactiva';
    ELSIF NEW.entidad_relacionada_tipo = 'convenio' AND NOT EXISTS (SELECT 1 FROM convenio WHERE id_convenio = NEW.entidad_relacionada_id AND activo = TRUE) THEN
        RAISE EXCEPTION 'La documentación soporte referencia un convenio inexistente o inactivo';
    ELSIF NEW.entidad_relacionada_tipo = 'orv' AND NOT EXISTS (SELECT 1 FROM orv WHERE id_orv = NEW.entidad_relacionada_id AND activo = TRUE) THEN
        RAISE EXCEPTION 'La documentación soporte referencia un ORV inexistente o inactivo';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_documentacion_soporte_referencia
BEFORE INSERT OR UPDATE ON documentacion_soporte
FOR EACH ROW EXECUTE FUNCTION fn_validar_documentacion_soporte_referencia();

-- Índices Espaciales y de Rendimiento
CREATE INDEX idx_tramo_geometria ON tramo USING GIST (geometria_linea);
CREATE INDEX idx_frente_geometria ON frente USING GIST (geometria_linea);
CREATE INDEX idx_nucleo_geometria ON nucleo_agrario USING GIST (geometria_poligono);
CREATE INDEX idx_tramo_nucleo_geometria ON tramo_nucleo USING GIST (geometria_segmento);

-- Triggers de Reglas de Negocio (Excepciones de Dominio)
CREATE OR REPLACE FUNCTION fn_validar_afectacion_uso_comun() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.tipo_afectacion = 'colectivo' THEN
        IF EXISTS (SELECT 1 FROM tramo_nucleo WHERE id_tramo_nucleo = NEW.id_tramo_nucleo AND proyecto_no_afecta_uso_comun = TRUE) THEN
            RAISE EXCEPTION 'No se pueden crear afectaciones colectivas si el proyecto no afecta uso común';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_afectacion_uso_comun
BEFORE INSERT OR UPDATE ON afectacion
FOR EACH ROW EXECUTE FUNCTION fn_validar_afectacion_uso_comun();

CREATE OR REPLACE FUNCTION fn_validar_convenio_expropiacion() RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM tramo_nucleo WHERE id_tramo_nucleo = NEW.id_tramo_nucleo AND es_expropiacion = TRUE) THEN
        RAISE EXCEPTION 'No se pueden registrar convenios en un tramo-núcleo marcado como Expropiación Directa';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_convenio_expropiacion
BEFORE INSERT OR UPDATE ON convenio
FOR EACH ROW EXECUTE FUNCTION fn_validar_convenio_expropiacion();

-- Función centralizada de cálculo de superficie liberada
CREATE OR REPLACE FUNCTION fn_calcular_superficie_liberada_afectacion(p_id_afectacion INTEGER) RETURNS NUMERIC AS $$
DECLARE
    v_total_liberado NUMERIC := 0;
BEGIN
    SELECT COALESCE(SUM(sup_liberada_base) + SUM(sup_liberada_adicional), 0) INTO v_total_liberado
    FROM (
        WITH ModificatoriosVigentes AS (
            SELECT id_convenio_padre, id_convenio, superficie_real_afectada_ha, superficie_total_ha
            FROM (
                SELECT id_convenio_padre, id_convenio, superficie_real_afectada_ha, superficie_total_ha,
                       ROW_NUMBER() OVER (PARTITION BY id_convenio_padre ORDER BY fecha_firma DESC, id_convenio DESC) as rn
                FROM convenio
                WHERE tipo_convenio = 'modificatorio' AND convenio_inscrito_fecha_ran IS NOT NULL AND activo = TRUE
            ) t WHERE rn = 1
        ),
        ConveniosBase AS (
            SELECT c.id_tramo_nucleo,
                   COALESCE(m.superficie_real_afectada_ha, m.superficie_total_ha, c.superficie_real_afectada_ha, c.superficie_total_ha, 0) AS sup_liberada_base,
                   0 AS sup_liberada_adicional
            FROM convenio c
            LEFT JOIN ModificatoriosVigentes m ON m.id_convenio_padre = c.id_convenio
            WHERE c.tipo_convenio IN ('cop_original', 'obras_complementarias') AND c.convenio_inscrito_fecha_ran IS NOT NULL AND c.activo = TRUE AND c.id_afectacion = p_id_afectacion
        ),
        SuperficiesAdicionales AS (
            SELECT c.id_tramo_nucleo,
                   0 AS sup_liberada_base,
                   COALESCE(m.superficie_real_afectada_ha, m.superficie_total_ha, c.superficie_adicional_ha, c.superficie_ampliacion_ha, 0) AS sup_liberada_adicional
            FROM convenio c
            LEFT JOIN ModificatoriosVigentes m ON m.id_convenio_padre = c.id_convenio
            WHERE c.tipo_convenio IN ('superficie_adicional', 'ampliacion', 'ampliacion_remanente') AND c.convenio_inscrito_fecha_ran IS NOT NULL AND c.activo = TRUE AND c.id_afectacion = p_id_afectacion
        )
        SELECT sup_liberada_base, sup_liberada_adicional FROM ConveniosBase
        UNION ALL
        SELECT sup_liberada_base, sup_liberada_adicional FROM SuperficiesAdicionales
    ) calculo;
    RETURN v_total_liberado;
END;
$$ LANGUAGE plpgsql;

-- Trigger sobre Convenio (Cálculo exacto)
CREATE OR REPLACE FUNCTION fn_validar_superficie_liberada_convenio() RETURNS TRIGGER AS $$
DECLARE
    sup_afectada NUMERIC;
    sup_liberada_calculada NUMERIC;
BEGIN
    SELECT superficie_afectada_ha INTO sup_afectada FROM afectacion WHERE id_afectacion = NEW.id_afectacion AND activo = TRUE;
    sup_liberada_calculada := fn_calcular_superficie_liberada_afectacion(NEW.id_afectacion);
    
    IF sup_liberada_calculada > sup_afectada THEN
        RAISE EXCEPTION 'La suma de superficies liberadas calculada (%) excede la superficie afectada total (%)', sup_liberada_calculada, sup_afectada;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_superficie_liberada_convenio
AFTER INSERT OR UPDATE OF convenio_inscrito_fecha_ran, activo, tipo_convenio, id_convenio_padre, superficie_total_ha, superficie_real_afectada_ha, superficie_adicional_ha, superficie_ampliacion_ha, id_afectacion ON convenio
FOR EACH ROW EXECUTE FUNCTION fn_validar_superficie_liberada_convenio();

-- Trigger para sincronizar la superficie afectada base al registrar expansiones
CREATE OR REPLACE FUNCTION fn_sincronizar_superficie_adicional() RETURNS TRIGGER AS $$
DECLARE
    delta_superficie NUMERIC := 0;
    old_superficie NUMERIC := 0;
    new_superficie NUMERIC := 0;
    padre_superficie NUMERIC := 0;
    es_modificatorio_de_adicional BOOLEAN := FALSE;
BEGIN
    IF NEW.tipo_convenio IN ('superficie_adicional', 'ampliacion', 'ampliacion_remanente') THEN
        new_superficie := COALESCE(NEW.superficie_adicional_ha, NEW.superficie_ampliacion_ha, 0);
        IF TG_OP = 'UPDATE' THEN
            old_superficie := COALESCE(OLD.superficie_adicional_ha, OLD.superficie_ampliacion_ha, 0);
        END IF;
    ELSIF NEW.tipo_convenio = 'modificatorio' AND NEW.id_convenio_padre IS NOT NULL THEN
        SELECT COALESCE(superficie_adicional_ha, superficie_ampliacion_ha, 0) 
        INTO padre_superficie 
        FROM convenio WHERE id_convenio = NEW.id_convenio_padre AND tipo_convenio IN ('superficie_adicional', 'ampliacion', 'ampliacion_remanente');

        IF FOUND THEN
            es_modificatorio_de_adicional := TRUE;
            new_superficie := COALESCE(NEW.superficie_real_afectada_ha, NEW.superficie_total_ha, 0);
            
            IF TG_OP = 'INSERT' THEN
                old_superficie := padre_superficie;
            ELSIF TG_OP = 'UPDATE' THEN
                old_superficie := COALESCE(OLD.superficie_real_afectada_ha, OLD.superficie_total_ha, 0);
            END IF;
        END IF;
    END IF;

    IF NEW.tipo_convenio IN ('superficie_adicional', 'ampliacion', 'ampliacion_remanente') OR es_modificatorio_de_adicional THEN
        IF TG_OP = 'INSERT' AND NEW.activo = TRUE THEN
            delta_superficie := new_superficie - old_superficie;
        ELSIF TG_OP = 'UPDATE' THEN
            IF OLD.activo = TRUE AND NEW.activo = TRUE THEN
                delta_superficie := new_superficie - old_superficie;
            ELSIF OLD.activo = FALSE AND NEW.activo = TRUE THEN
                delta_superficie := new_superficie - padre_superficie;
            ELSIF OLD.activo = TRUE AND NEW.activo = FALSE THEN
                delta_superficie := padre_superficie - old_superficie;
            END IF;
        END IF;

        IF delta_superficie <> 0 THEN
            UPDATE afectacion 
            SET superficie_afectada_ha = COALESCE(superficie_afectada_ha, 0) + delta_superficie
            WHERE id_afectacion = NEW.id_afectacion;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sincronizar_superficie_adicional
AFTER INSERT OR UPDATE OF activo, superficie_adicional_ha, superficie_ampliacion_ha, superficie_real_afectada_ha, superficie_total_ha ON convenio
FOR EACH ROW EXECUTE FUNCTION fn_sincronizar_superficie_adicional();

-- Trigger sobre Afectación (Protección contra reducción)
CREATE OR REPLACE FUNCTION fn_validar_superficie_afectada_reducida() RETURNS TRIGGER AS $$
DECLARE
    sup_liberada_calculada NUMERIC;
BEGIN
    IF NEW.superficie_afectada_ha < OLD.superficie_afectada_ha THEN
        sup_liberada_calculada := fn_calcular_superficie_liberada_afectacion(NEW.id_afectacion);
        IF NEW.superficie_afectada_ha < sup_liberada_calculada THEN
            RAISE EXCEPTION 'La nueva superficie afectada (%) no puede ser menor a la superficie ya liberada en convenios activos (%)', NEW.superficie_afectada_ha, sup_liberada_calculada;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_superficie_afectada_reducida
BEFORE UPDATE OF superficie_afectada_ha ON afectacion
FOR EACH ROW EXECUTE FUNCTION fn_validar_superficie_afectada_reducida();

-- Validación estricta de Parcela Individual
CREATE OR REPLACE FUNCTION fn_validar_parcela_individual() RETURNS TRIGGER AS $$
DECLARE
    p_no_ppt VARCHAR;
    p_titular VARCHAR;
    p_cert VARCHAR;
    p_folio VARCHAR;
    p_doc_faltante TEXT;
BEGIN
    IF NEW.tipo_afectacion = 'individual' AND NEW.id_parcela IS NOT NULL THEN
        SELECT no_parcela_ppt, nombre_titular, certificado_parcelario, folio_derechos, documentacion_faltante
        INTO p_no_ppt, p_titular, p_cert, p_folio, p_doc_faltante
        FROM parcela WHERE id_parcela = NEW.id_parcela;
        
        IF p_no_ppt IS NULL OR p_titular IS NULL THEN
            RAISE EXCEPTION 'La parcela vinculada a una afectación individual debe tener no_parcela_ppt y nombre_titular';
        END IF;
        
        IF (p_cert IS NULL OR p_folio IS NULL) AND p_doc_faltante IS NULL THEN
            RAISE EXCEPTION 'Si la parcela carece de certificado, el campo documentacion_faltante debe estar poblado indicando la justificación.';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_parcela_individual
BEFORE INSERT OR UPDATE ON afectacion
FOR EACH ROW EXECUTE FUNCTION fn_validar_parcela_individual();

-- Validación de Modificatorio Colectivo
CREATE OR REPLACE FUNCTION fn_validar_modificatorio_colectivo() RETURNS TRIGGER AS $$
DECLARE
    padre_tipo VARCHAR;
    padre_afectacion VARCHAR;
    padre_asamblea INTEGER;
    padre_anuencia VARCHAR;
BEGIN
    IF NEW.tipo_convenio = 'modificatorio' AND NEW.tipo_afectacion = 'colectivo' THEN
        IF NEW.id_convenio_padre IS NULL THEN
            RAISE EXCEPTION 'Un modificatorio colectivo debe tener un id_convenio_padre';
        END IF;
        
        SELECT c.tipo_convenio, c.tipo_afectacion, c.id_asamblea_autorizacion, a.resultado_anuencia
        INTO padre_tipo, padre_afectacion, padre_asamblea, padre_anuencia
        FROM convenio c
        LEFT JOIN asamblea a ON a.id_asamblea = c.id_asamblea_autorizacion
        WHERE c.id_convenio = NEW.id_convenio_padre;
        
        IF padre_tipo NOT IN ('cop_original', 'obras_complementarias', 'superficie_adicional') THEN
            RAISE EXCEPTION 'El padre de un modificatorio colectivo debe ser cop_original, obras_complementarias o superficie_adicional';
        END IF;
        
        IF padre_afectacion != 'colectivo' THEN
            RAISE EXCEPTION 'El convenio padre debe ser de afectación colectiva';
        END IF;
        
        IF padre_asamblea IS NULL OR padre_anuencia != 'otorgada' THEN
            RAISE EXCEPTION 'El convenio padre debe contar con una asamblea vinculada cuya anuencia haya sido otorgada';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_modificatorio_colectivo
BEFORE INSERT OR UPDATE ON convenio
FOR EACH ROW EXECUTE FUNCTION fn_validar_modificatorio_colectivo();

-- Soft-Restrict (Inactivos) y Trazabilidad Forense
CREATE OR REPLACE FUNCTION fn_validar_baja_logica() RETURNS TRIGGER AS $$
BEGIN
    IF OLD.activo = TRUE AND NEW.activo = FALSE THEN
        IF NEW.fecha_baja IS NULL OR NEW.id_usuario_baja IS NULL OR NEW.motivo_baja IS NULL THEN
            RAISE EXCEPTION 'Toda baja lógica requiere fecha_baja, id_usuario_baja y motivo_baja';
        END IF;
    ELSIF OLD.activo = FALSE AND NEW.activo = TRUE THEN
        IF NEW.fecha_reactivacion IS NULL OR NEW.id_usuario_reactivacion IS NULL OR NEW.motivo_reactivacion IS NULL THEN
            RAISE EXCEPTION 'Toda reactivación requiere fecha_reactivacion, id_usuario_reactivacion y motivo_reactivacion, manteniendo intactos los datos de la baja original';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger Espacial para Afectación
CREATE OR REPLACE FUNCTION fn_validar_coherencia_espacial() RETURNS TRIGGER AS $$
DECLARE
    v_nucleo_geom GEOMETRY;
    v_tramo_geom GEOMETRY;
    v_ancho NUMERIC;
BEGIN
    IF NEW.origen_registro = 'captura_sistema' AND NEW.geometria_afectacion IS NOT NULL THEN
        SELECT geometria_poligono INTO v_nucleo_geom FROM nucleo_agrario WHERE id_nucleo = NEW.id_nucleo;
        IF NOT ST_Intersects(NEW.geometria_afectacion, v_nucleo_geom) THEN
            RAISE EXCEPTION 'La afectación no intersecta con su núcleo agrario';
        END IF;

        SELECT t.geometria_linea, t.ancho_total_derecho_via_m INTO v_tramo_geom, v_ancho 
        FROM tramo_nucleo tn JOIN tramo t ON tn.id_tramo = t.id_tramo WHERE tn.id_tramo_nucleo = NEW.id_tramo_nucleo;
        
        IF NOT ST_Intersects(NEW.geometria_afectacion, ST_Buffer(v_tramo_geom::geography, v_ancho / 2)::geometry) THEN
            RAISE EXCEPTION 'La afectación no intersecta con el derecho de vía del tramo';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_coherencia_espacial
BEFORE INSERT OR UPDATE ON afectacion
FOR EACH ROW EXECUTE FUNCTION fn_validar_coherencia_espacial();

-- Prohibición estricta de DELETE Físico
CREATE OR REPLACE FUNCTION fn_prevent_physical_delete() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Borrado físico prohibido por auditoría. Use UPDATE activo = FALSE';
END;
$$ LANGUAGE plpgsql;

-- Función Genérica de Auditoría Universal
CREATE OR REPLACE FUNCTION fn_audit_log() RETURNS TRIGGER AS $$
DECLARE
    current_user_id TEXT;
    pk_column TEXT;
    entidad_pk BIGINT;
BEGIN
    current_user_id := current_setting('app.current_user_id', true);
    IF current_user_id IS NULL OR current_user_id = '' THEN
        RAISE EXCEPTION 'Auditoría fallida: Falta el contexto de usuario (app.current_user_id). Use BEGIN; SET LOCAL "app.current_user_id" = 1; COMMIT;';
    END IF;

    pk_column := TG_ARGV[0];
    IF pk_column IS NULL OR pk_column = '' THEN
        RAISE EXCEPTION 'Auditoría fallida: el trigger debe indicar la columna PK en TG_ARGV[0]';
    END IF;

    IF TG_OP = 'INSERT' THEN
        entidad_pk := (to_jsonb(NEW) ->> pk_column)::BIGINT;
        INSERT INTO bitacora (id_usuario, entidad_tipo, entidad_id, accion, valor_nuevo)
        VALUES (current_user_id::INTEGER, TG_TABLE_NAME, entidad_pk, 'insert', row_to_json(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        entidad_pk := (to_jsonb(NEW) ->> pk_column)::BIGINT;
        INSERT INTO bitacora (id_usuario, entidad_tipo, entidad_id, accion, valor_anterior, valor_nuevo)
        VALUES (current_user_id::INTEGER, TG_TABLE_NAME, entidad_pk, 'update', row_to_json(OLD), row_to_json(NEW));
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- =============================================================
-- C-01: INSTANCIACIÓN EXPLÍCITA DE TRIGGERS DE AUDITORÍA,
--       PROTECCIÓN DE BORRADO FÍSICO Y BAJA LÓGICA
-- Corrección post-auditoría: se reemplazan los comentarios
-- plantilla por sentencias SQL ejecutables para cada tabla
-- operativa. Omitir cualquiera de estos triggers invalidaría
-- el Req. 25 (auditoría universal) en producción.
-- =============================================================

-- entidad_federativa
CREATE TRIGGER trg_audit_entidad_federativa
    AFTER INSERT OR UPDATE ON entidad_federativa
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_entidad');
CREATE TRIGGER trg_prevent_delete_entidad_federativa
    BEFORE DELETE ON entidad_federativa
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();

-- municipio
CREATE TRIGGER trg_audit_municipio
    AFTER INSERT OR UPDATE ON municipio
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_municipio');
CREATE TRIGGER trg_prevent_delete_municipio
    BEFORE DELETE ON municipio
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();

-- tramo
CREATE TRIGGER trg_audit_tramo
    AFTER INSERT OR UPDATE ON tramo
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_tramo');
CREATE TRIGGER trg_prevent_delete_tramo
    BEFORE DELETE ON tramo
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_tramo
    BEFORE UPDATE OF activo ON tramo
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- frente
CREATE TRIGGER trg_audit_frente
    AFTER INSERT OR UPDATE ON frente
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_frente');
CREATE TRIGGER trg_prevent_delete_frente
    BEFORE DELETE ON frente
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_frente
    BEFORE UPDATE OF activo ON frente
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- nucleo_agrario
CREATE TRIGGER trg_audit_nucleo_agrario
    AFTER INSERT OR UPDATE ON nucleo_agrario
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_nucleo');
CREATE TRIGGER trg_prevent_delete_nucleo_agrario
    BEFORE DELETE ON nucleo_agrario
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_nucleo_agrario
    BEFORE UPDATE OF activo ON nucleo_agrario
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- tramo_nucleo
CREATE TRIGGER trg_audit_tramo_nucleo
    AFTER INSERT OR UPDATE ON tramo_nucleo
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_tramo_nucleo');
CREATE TRIGGER trg_prevent_delete_tramo_nucleo
    BEFORE DELETE ON tramo_nucleo
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_tramo_nucleo
    BEFORE UPDATE OF activo ON tramo_nucleo
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- usuario
CREATE TRIGGER trg_audit_usuario
    AFTER INSERT OR UPDATE ON usuario
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_usuario');
CREATE TRIGGER trg_prevent_delete_usuario
    BEFORE DELETE ON usuario
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_usuario
    BEFORE UPDATE OF activo ON usuario
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- orv
CREATE TRIGGER trg_audit_orv
    AFTER INSERT OR UPDATE ON orv
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_orv');
CREATE TRIGGER trg_prevent_delete_orv
    BEFORE DELETE ON orv
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_orv
    BEFORE UPDATE OF activo ON orv
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- padron_historial
CREATE TRIGGER trg_audit_padron_historial
    AFTER INSERT OR UPDATE ON padron_historial
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_padron');
CREATE TRIGGER trg_prevent_delete_padron_historial
    BEFORE DELETE ON padron_historial
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_padron_historial
    BEFORE UPDATE OF activo ON padron_historial
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- parcela
CREATE TRIGGER trg_audit_parcela
    AFTER INSERT OR UPDATE ON parcela
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_parcela');
CREATE TRIGGER trg_prevent_delete_parcela
    BEFORE DELETE ON parcela
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_parcela
    BEFORE UPDATE OF activo ON parcela
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- afectacion
CREATE TRIGGER trg_audit_afectacion
    AFTER INSERT OR UPDATE ON afectacion
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_afectacion');
CREATE TRIGGER trg_prevent_delete_afectacion
    BEFORE DELETE ON afectacion
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_afectacion
    BEFORE UPDATE OF activo ON afectacion
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- actividad_campo
CREATE TRIGGER trg_audit_actividad_campo
    AFTER INSERT OR UPDATE ON actividad_campo
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_actividad');
CREATE TRIGGER trg_prevent_delete_actividad_campo
    BEFORE DELETE ON actividad_campo
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_actividad_campo
    BEFORE UPDATE OF activo ON actividad_campo
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- asamblea
CREATE TRIGGER trg_audit_asamblea
    AFTER INSERT OR UPDATE ON asamblea
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_asamblea');
CREATE TRIGGER trg_prevent_delete_asamblea
    BEFORE DELETE ON asamblea
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_asamblea
    BEFORE UPDATE OF activo ON asamblea
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- convenio
CREATE TRIGGER trg_audit_convenio
    AFTER INSERT OR UPDATE ON convenio
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_convenio');
CREATE TRIGGER trg_prevent_delete_convenio
    BEFORE DELETE ON convenio
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_convenio
    BEFORE UPDATE OF activo ON convenio
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- tramite_fifonafe
CREATE TRIGGER trg_audit_tramite_fifonafe
    AFTER INSERT OR UPDATE ON tramite_fifonafe
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_tramite_fifonafe');
CREATE TRIGGER trg_prevent_delete_tramite_fifonafe
    BEFORE DELETE ON tramite_fifonafe
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_tramite_fifonafe
    BEFORE UPDATE OF activo ON tramite_fifonafe
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- documentacion_soporte
CREATE TRIGGER trg_audit_documentacion_soporte
    AFTER INSERT OR UPDATE ON documentacion_soporte
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_documento');
CREATE TRIGGER trg_prevent_delete_documentacion_soporte
    BEFORE DELETE ON documentacion_soporte
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_documentacion_soporte
    BEFORE UPDATE OF activo ON documentacion_soporte
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- alertas
CREATE TRIGGER trg_audit_alertas
    AFTER INSERT OR UPDATE ON alertas
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_alerta');
CREATE TRIGGER trg_prevent_delete_alertas
    BEFORE DELETE ON alertas
    FOR EACH ROW EXECUTE FUNCTION fn_prevent_physical_delete();
CREATE TRIGGER trg_baja_logica_alertas
    BEFORE UPDATE OF activo ON alertas
    FOR EACH ROW EXECUTE FUNCTION fn_validar_baja_logica();

-- =============================================================
-- C-02: PROTECCIÓN CONTRA REGRESIÓN DE ESTADO DE CONVENIO
-- Corrección post-auditoría: el estado borrador→firmado→inscrito
-- es unidireccional. Sin este trigger, un UPDATE podría poner
-- fecha_firma o convenio_inscrito_fecha_ran a NULL, provocando
-- una regresión silenciosa de estado que violaría la Property 9.
-- =============================================================

CREATE OR REPLACE FUNCTION fn_validar_regresion_estado_convenio() RETURNS TRIGGER AS $$
BEGIN
    -- Bloquear regresión: fecha_firma no puede pasar de valor a NULL
    IF OLD.fecha_firma IS NOT NULL AND NEW.fecha_firma IS NULL THEN
        RAISE EXCEPTION
            'Regresión de estado prohibida: convenio % ya fue firmado (fecha_firma = %). '
            'No se puede eliminar la fecha de firma.',
            OLD.id_convenio, OLD.fecha_firma;
    END IF;

    -- Bloquear regresión: convenio_inscrito_fecha_ran no puede pasar de valor a NULL
    IF OLD.convenio_inscrito_fecha_ran IS NOT NULL AND NEW.convenio_inscrito_fecha_ran IS NULL THEN
        RAISE EXCEPTION
            'Regresión de estado prohibida: convenio % ya fue inscrito en RAN (fecha = %). '
            'No se puede eliminar la fecha de inscripción.',
            OLD.id_convenio, OLD.convenio_inscrito_fecha_ran;
    END IF;

    -- Bloquear adelanto de pasos: no se puede inscribir sin haber ingresado
    IF NEW.convenio_inscrito_fecha_ran IS NOT NULL AND NEW.ingreso_ran_fecha IS NULL THEN
        RAISE EXCEPTION
            'Secuencia inválida en convenio %: no se puede registrar inscripción en RAN '
            'sin antes registrar la fecha de ingreso (ingreso_ran_fecha).',
            NEW.id_convenio;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_regresion_estado_convenio
    BEFORE UPDATE OF fecha_firma, ingreso_ran_fecha, convenio_inscrito_fecha_ran
    ON convenio
    FOR EACH ROW EXECUTE FUNCTION fn_validar_regresion_estado_convenio();



CREATE OR REPLACE VIEW vw_orv_estado AS
SELECT 
    *,
    (CURRENT_DATE BETWEEN inicio_vigencia AND fin_vigencia) AS orv_vigente 
FROM orv WHERE activo = TRUE;

CREATE OR REPLACE VIEW vw_tramo_nucleo_estado AS
SELECT
    tn.id_tramo_nucleo,
    tn.id_tramo,
    tn.id_frente,
    tn.id_nucleo,
    tn.consecutivo,
    tn.longitud_m,
    tn.causa_problema,
    EXISTS (SELECT 1 FROM asamblea a WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo AND a.resultado_anuencia = 'otorgada' AND a.activo = TRUE) AS tiene_anuencia,
    EXISTS (SELECT 1 FROM convenio c WHERE c.id_tramo_nucleo = tn.id_tramo_nucleo AND c.convenio_inscrito_fecha_ran IS NOT NULL AND c.activo = TRUE) AS tiene_convenio_inscrito_ran,
    -- ESTADO LEGAL
    CASE
        WHEN tn.es_expropiacion = TRUE THEN 'problema'
        WHEN NULLIF(BTRIM(tn.causa_problema), '') IS NOT NULL THEN 'problema'
        WHEN (SELECT COUNT(*) FROM afectacion a WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo AND a.activo = TRUE) > 0 
             AND NOT EXISTS (
                 SELECT 1 FROM afectacion a WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo AND a.activo = TRUE
                 AND NOT EXISTS (SELECT 1 FROM convenio c WHERE c.id_afectacion = a.id_afectacion AND c.convenio_inscrito_fecha_ran IS NOT NULL AND c.activo = TRUE)
             ) THEN 'liberado'
        WHEN EXISTS (SELECT 1 FROM convenio c WHERE c.id_tramo_nucleo = tn.id_tramo_nucleo AND c.activo = TRUE) THEN 'en_proceso'
        ELSE 'pendiente'
    END AS estado_legal,
    -- ESTADO GEOESPACIAL
    CASE
        WHEN (SELECT COUNT(*) FROM afectacion a WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo AND a.activo = TRUE) = 0 THEN 'pendiente_digitalizacion'
        WHEN EXISTS (SELECT 1 FROM afectacion a WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo AND a.geometria_afectacion IS NULL AND a.activo = TRUE) THEN 'pendiente_digitalizacion'
        ELSE 'completo'
    END AS estado_geoespacial
FROM tramo_nucleo tn WHERE tn.activo = TRUE;

CREATE OR REPLACE VIEW vw_dashboard_liberacion AS
WITH ModificatoriosVigentes AS (
    SELECT id_convenio_padre, id_convenio, superficie_real_afectada_ha, superficie_total_ha
    FROM (
        SELECT id_convenio_padre, id_convenio, superficie_real_afectada_ha, superficie_total_ha,
               ROW_NUMBER() OVER (PARTITION BY id_convenio_padre ORDER BY fecha_firma DESC, id_convenio DESC) as rn
        FROM convenio
        WHERE tipo_convenio = 'modificatorio' AND convenio_inscrito_fecha_ran IS NOT NULL AND activo = TRUE
    ) t WHERE rn = 1
),
ConveniosBase AS (
    SELECT c.id_tramo_nucleo,
           c.id_convenio,
           c.tipo_afectacion,
           COALESCE(m.superficie_real_afectada_ha, m.superficie_total_ha, c.superficie_real_afectada_ha, c.superficie_total_ha, 0) AS superficie_liberada_ha
    FROM convenio c
    LEFT JOIN ModificatoriosVigentes m ON m.id_convenio_padre = c.id_convenio
    WHERE c.tipo_convenio IN ('cop_original', 'obras_complementarias')
      AND c.convenio_inscrito_fecha_ran IS NOT NULL
      AND c.activo = TRUE
),
SuperficiesAdicionales AS (
    SELECT c.id_tramo_nucleo,
           c.id_convenio,
           c.tipo_afectacion,
           COALESCE(m.superficie_real_afectada_ha, m.superficie_total_ha, c.superficie_adicional_ha, c.superficie_ampliacion_ha, 0) AS superficie_liberada_ha
    FROM convenio c
    LEFT JOIN ModificatoriosVigentes m ON m.id_convenio_padre = c.id_convenio
    WHERE c.tipo_convenio IN ('superficie_adicional', 'ampliacion', 'ampliacion_remanente')
      AND c.convenio_inscrito_fecha_ran IS NOT NULL
      AND c.activo = TRUE
),
LiberacionUnificada AS (
    SELECT * FROM ConveniosBase
    UNION ALL
    SELECT * FROM SuperficiesAdicionales
),
AgrupacionLiberada AS (
    SELECT id_tramo_nucleo,
           SUM(superficie_liberada_ha) AS superficie_liberada_ha,
           COUNT(DISTINCT id_convenio) AS total_convenios_formalizados_ran,
           COUNT(DISTINCT CASE WHEN tipo_afectacion = 'colectivo' THEN id_convenio END) AS total_convenios_colectivos_formalizados_ran,
           COUNT(DISTINCT CASE WHEN tipo_afectacion = 'individual' THEN id_convenio END) AS total_convenios_individuales_formalizados_ran,
           SUM(CASE WHEN tipo_afectacion = 'colectivo' THEN superficie_liberada_ha ELSE 0 END) AS total_colectivo_ha,
           SUM(CASE WHEN tipo_afectacion = 'individual' THEN superficie_liberada_ha ELSE 0 END) AS total_individual_ha
    FROM LiberacionUnificada
    GROUP BY id_tramo_nucleo
)
SELECT
    v.id_tramo_nucleo,
    t.id_tramo,
    t.clave_tramo,
    f.id_frente,
    n.id_nucleo,
    n.nombre_nucleo,
    ef.nombre AS entidad_federativa,
    v.estado_legal,
    v.estado_geoespacial,
    COALESCE(af.total_superficie_afectada_ha, 0) AS total_superficie_afectada_ha,
    COALESCE(al.superficie_liberada_ha, 0) AS superficie_liberada_ha,
    COALESCE(af.total_superficie_afectada_ha, 0) - COALESCE(al.superficie_liberada_ha, 0) AS superficie_pendiente_ha,
    CASE 
        WHEN COALESCE(af.total_superficie_afectada_ha, 0) = 0 THEN 0
        ELSE ROUND((COALESCE(al.superficie_liberada_ha, 0) / af.total_superficie_afectada_ha) * 100, 2)
    END AS porcentaje_avance_legal,
    CASE 
        WHEN COALESCE(af.total_superficie_afectada_ha, 0) = 0 THEN 0
        ELSE ROUND((COALESCE(af_geo.superficie_con_geometria, 0) / af.total_superficie_afectada_ha) * 100, 2)
    END AS porcentaje_avance_geoespacial,
    COALESCE(al.total_convenios_formalizados_ran, 0) AS total_convenios_formalizados_ran,
    COALESCE(al.total_convenios_colectivos_formalizados_ran, 0) AS total_convenios_colectivos_formalizados_ran,
    COALESCE(al.total_convenios_individuales_formalizados_ran, 0) AS total_convenios_individuales_formalizados_ran,
    COALESCE(al.total_colectivo_ha, 0) AS total_colectivo_ha,
    COALESCE(al.total_individual_ha, 0) AS total_individual_ha
FROM vw_tramo_nucleo_estado v
JOIN tramo t ON t.id_tramo = v.id_tramo AND t.activo = TRUE
JOIN frente f ON f.id_frente = v.id_frente AND f.activo = TRUE
JOIN nucleo_agrario n ON n.id_nucleo = v.id_nucleo AND n.activo = TRUE
JOIN municipio m ON m.id_municipio = n.id_municipio AND m.activo = TRUE
JOIN entidad_federativa ef ON ef.id_entidad = m.id_entidad AND ef.activo = TRUE
LEFT JOIN (
    SELECT id_tramo_nucleo, SUM(COALESCE(superficie_afectada_ha, 0)) AS total_superficie_afectada_ha
    FROM afectacion WHERE activo = TRUE GROUP BY id_tramo_nucleo
) af ON af.id_tramo_nucleo = v.id_tramo_nucleo
LEFT JOIN (
    SELECT id_tramo_nucleo, SUM(COALESCE(superficie_afectada_ha, 0)) AS superficie_con_geometria
    FROM afectacion WHERE activo = TRUE AND geometria_afectacion IS NOT NULL GROUP BY id_tramo_nucleo
) af_geo ON af_geo.id_tramo_nucleo = v.id_tramo_nucleo
LEFT JOIN AgrupacionLiberada al ON al.id_tramo_nucleo = v.id_tramo_nucleo;
