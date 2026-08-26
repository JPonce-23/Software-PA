-- Reestructuración integral del dominio administrativo SOFTWARE-PA.
-- Requiere entorno autorizado, confirmación explícita y respaldo restorable;
-- el bloque preflight aborta antes de cualquier DDL cuando falta un gate.
BEGIN;

SELECT pg_advisory_xact_lock(20260825, 31);

DO $preflight$
DECLARE
    v_environment TEXT := lower(current_setting('app.environment', TRUE));
    v_confirm TEXT := current_setting('app.allow_destructive_test_reset', TRUE);
    v_backup TEXT := current_setting('app.backup_verified', TRUE);
    v_database TEXT := current_database();
    v_entidades INTEGER;
    v_municipios INTEGER;
BEGIN
    IF v_environment IS NULL OR v_environment NOT IN ('development', 'test') THEN
        RAISE EXCEPTION '031 bloqueada: app.environment debe ser development o test';
    END IF;
    IF v_database !~* '(test|prueba|dev|local)' THEN
        RAISE EXCEPTION '031 bloqueada: la base % no está identificada como desarrollo/prueba', v_database;
    END IF;
    IF v_confirm IS DISTINCT FROM '1' THEN
        RAISE EXCEPTION '031 bloqueada: falta confirmación explícita app.allow_destructive_test_reset=1';
    END IF;
    IF v_backup IS DISTINCT FROM '1' THEN
        RAISE EXCEPTION '031 bloqueada: falta confirmación de respaldo restorable app.backup_verified=1';
    END IF;
    IF to_regclass('public.schema_migrations') IS NULL
       OR NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '030') THEN
        RAISE EXCEPTION '031 requiere esquema en versión 030';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '031') THEN
        RAISE EXCEPTION 'La migración 031 ya fue aplicada';
    END IF;

    SELECT COUNT(*) INTO v_entidades FROM entidad_federativa WHERE activo;
    SELECT COUNT(*) INTO v_municipios FROM municipio WHERE activo;
    IF v_entidades <> 32 OR v_municipios <> 2478 THEN
        RAISE EXCEPTION
            '031 bloqueada: catálogo territorial no reproducible (% entidades, % municipios)',
            v_entidades, v_municipios;
    END IF;
END;
$preflight$;

-- Retirar primero lecturas y triggers conservados que dependen del legado.
DROP VIEW IF EXISTS vw_dashboard_liberacion CASCADE;
DROP VIEW IF EXISTS vw_tramo_nucleo_estado CASCADE;
DROP VIEW IF EXISTS vw_afectacion_estado CASCADE;
DROP VIEW IF EXISTS vw_afectacion_ciclo_estado CASCADE;
DROP VIEW IF EXISTS vw_orv_estado CASCADE;

DROP TRIGGER IF EXISTS trg_015_usuario_sin_asignaciones ON usuario;
DROP TRIGGER IF EXISTS trg_audit_usuario ON usuario;
DROP TRIGGER IF EXISTS trg_audit_entidad_federativa ON entidad_federativa;
DROP TRIGGER IF EXISTS trg_prevent_delete_entidad_federativa ON entidad_federativa;
DROP TRIGGER IF EXISTS trg_audit_municipio ON municipio;
DROP TRIGGER IF EXISTS trg_prevent_delete_municipio ON municipio;

-- Los datos son de prueba: se elimina el dominio incompatible sin backfill ni IDs puente.
DROP TABLE IF EXISTS alertas_vistas CASCADE;
DROP TABLE IF EXISTS alertas CASCADE;
DROP TABLE IF EXISTS acuerdo CASCADE;
DROP TABLE IF EXISTS minuta CASCADE;
DROP TABLE IF EXISTS pago_indemnizacion CASCADE;
DROP TABLE IF EXISTS documento_version CASCADE;
DROP TABLE IF EXISTS documentacion_soporte CASCADE;
DROP TABLE IF EXISTS tramite_fifonafe CASCADE;
DROP TABLE IF EXISTS convenio CASCADE;
DROP TABLE IF EXISTS asamblea CASCADE;
DROP TABLE IF EXISTS actividad_campo CASCADE;
DROP TABLE IF EXISTS afectacion_ciclo CASCADE;
DROP TABLE IF EXISTS afectacion CASCADE;
DROP TABLE IF EXISTS orv_integrante CASCADE;
DROP TABLE IF EXISTS parcela_titular CASCADE;
DROP TABLE IF EXISTS persona_fuente_legacy CASCADE;
DROP TABLE IF EXISTS persona_nucleo CASCADE;
DROP TABLE IF EXISTS padron_historial CASCADE;
DROP TABLE IF EXISTS orv CASCADE;
DROP TABLE IF EXISTS parcela CASCADE;
DROP TABLE IF EXISTS persona CASCADE;
DROP TABLE IF EXISTS tramo_nucleo CASCADE;
DROP TABLE IF EXISTS bitacora CASCADE;

-- Se recrean los maestros funcionales; las tablas GIS legacy restantes se retiran en 032.
DROP TABLE IF EXISTS nucleo_agrario CASCADE;
DROP TABLE IF EXISTS proyecto CASCADE;

DO $drop_legacy_functions$
DECLARE
    v_signature TEXT;
BEGIN
    FOR v_signature IN
        SELECT p.oid::regprocedure::TEXT
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND (
              p.proname LIKE 'fn_2b_%'
              OR p.proname LIKE 'fn_2c_%'
              OR p.proname LIKE 'fn_017_%'
              OR p.proname LIKE 'fn_019_%'
              OR p.proname LIKE 'fn_026_%'
              OR p.proname IN (
                  'fn_audit_log', 'fn_prevent_physical_delete', 'fn_validar_baja_logica',
                  'fn_calcular_superficie_liberada_afectacion',
                  'fn_sincronizar_superficie_adicional',
                  'fn_validar_afectacion_uso_comun',
                  'fn_validar_coherencia_espacial',
                  'fn_validar_convenio_expropiacion',
                  'fn_validar_modificatorio_colectivo',
                  'fn_validar_pago_indemnizacion',
                  'fn_validar_parcela_individual',
                  'fn_validar_parcela_para_afectacion',
                  'fn_validar_participacion_parcela',
                  'fn_validar_regresion_estado_convenio',
                  'fn_validar_superficie_afectada_reducida',
                  'fn_validar_superficie_liberada_convenio',
                  'fn_proteger_limite_convenio_pagado',
                  'fn_proteger_parcela_con_afectacion',
                  'fn_revalidar_parcela_referenciada',
                  'fn_revalidar_titulares_parcela',
                  'fn_generar_alertas_orv_vencidos',
                  'fn_sincronizar_alerta_orv_vencido',
                  'fn_validar_documentacion_soporte_referencia'
              )
          )
    LOOP
        EXECUTE format('DROP FUNCTION IF EXISTS %s CASCADE', v_signature);
    END LOOP;
END;
$drop_legacy_functions$;

CREATE TABLE proyecto (
    id_proyecto INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    clave_proyecto VARCHAR(30) NOT NULL UNIQUE,
    nombre_proyecto VARCHAR(200) NOT NULL,
    descripcion TEXT,
    fecha_inicio DATE,
    fecha_fin DATE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_proyecto_fechas CHECK (fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio),
    CONSTRAINT chk_proyecto_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE INDEX idx_proyecto_nombre ON proyecto (lower(nombre_proyecto));

CREATE TABLE nucleo_agrario (
    id_nucleo INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_municipio INTEGER NOT NULL REFERENCES municipio(id_municipio),
    nombre_nucleo VARCHAR(300) NOT NULL,
    tipo_nucleo VARCHAR(20) NOT NULL,
    comunidad_indigena BOOLEAN NOT NULL DEFAULT FALSE,
    geometria_poligono geometry(MULTIPOLYGON, 4326),
    fuente_geometria VARCHAR(250),
    fecha_fuente_geometria DATE,
    fuente_datos VARCHAR(120),
    id_entidad_fuente VARCHAR(120),
    id_municipio_fuente VARCHAR(120),
    id_nucleo_fuente VARCHAR(120),
    alcance_identidad_fuente VARCHAR(20),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_nucleo_tipo CHECK (tipo_nucleo IN ('ejido', 'comunidad')),
    CONSTRAINT chk_nucleo_geometria CHECK (
        geometria_poligono IS NULL OR (
            NOT ST_IsEmpty(geometria_poligono)
            AND ST_IsValid(geometria_poligono)
            AND ST_SRID(geometria_poligono) = 4326
            AND GeometryType(geometria_poligono) = 'MULTIPOLYGON'
        )
    ),
    CONSTRAINT chk_nucleo_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_nucleo_activo_normalizado
    ON nucleo_agrario (id_municipio, tipo_nucleo, lower(regexp_replace(btrim(nombre_nucleo), '\s+', ' ', 'g')))
    WHERE activo;
CREATE INDEX idx_nucleo_municipio_tipo ON nucleo_agrario (id_municipio, tipo_nucleo) WHERE activo;
CREATE INDEX idx_nucleo_geometria ON nucleo_agrario USING gist (geometria_poligono);

CREATE TABLE proyecto_nucleo (
    id_proyecto_nucleo INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_proyecto INTEGER NOT NULL REFERENCES proyecto(id_proyecto),
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    residencia VARCHAR(300),
    responsable_nombre VARCHAR(300),
    contacto VARCHAR(150),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_proyecto_nucleo_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_proyecto_nucleo_activo
    ON proyecto_nucleo (id_proyecto, id_nucleo) WHERE activo;
CREATE INDEX idx_proyecto_nucleo_proyecto ON proyecto_nucleo (id_proyecto) WHERE activo;
CREATE INDEX idx_proyecto_nucleo_nucleo ON proyecto_nucleo (id_nucleo) WHERE activo;

CREATE TABLE proyecto_nucleo_referencia (
    id_referencia INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_proyecto_nucleo INTEGER NOT NULL REFERENCES proyecto_nucleo(id_proyecto_nucleo),
    tipo_referencia VARCHAR(30) NOT NULL,
    valor VARCHAR(150) NOT NULL,
    es_principal BOOLEAN NOT NULL DEFAULT FALSE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_pn_referencia_tipo CHECK (tipo_referencia IN ('consecutivo', 'clave_tramo', 'numero_tramo', 'otro')),
    CONSTRAINT chk_pn_referencia_valor CHECK (NULLIF(btrim(valor), '') IS NOT NULL),
    CONSTRAINT chk_pn_referencia_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_pn_referencia_activa
    ON proyecto_nucleo_referencia (id_proyecto_nucleo, tipo_referencia, valor) WHERE activo;
CREATE UNIQUE INDEX uq_pn_referencia_principal
    ON proyecto_nucleo_referencia (id_proyecto_nucleo, tipo_referencia) WHERE activo AND es_principal;

CREATE TABLE persona (
    id_persona INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    curp VARCHAR(18),
    rfc VARCHAR(13),
    nombre VARCHAR(300) NOT NULL,
    apellido_paterno VARCHAR(200),
    apellido_materno VARCHAR(200),
    telefono VARCHAR(30),
    correo_electronico VARCHAR(320),
    datos_identidad_incompletos BOOLEAN NOT NULL DEFAULT FALSE,
    origen_registro VARCHAR(40) NOT NULL DEFAULT 'captura_sistema',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_persona_nombre CHECK (NULLIF(btrim(nombre), '') IS NOT NULL),
    CONSTRAINT chk_persona_origen CHECK (origen_registro IN ('captura_sistema', 'excel', 'qa', 'otro')),
    CONSTRAINT chk_persona_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_persona_curp ON persona (upper(curp)) WHERE activo AND curp IS NOT NULL;
CREATE INDEX idx_persona_nombre ON persona (lower(nombre), lower(apellido_paterno), lower(apellido_materno));

CREATE TABLE orv (
    id_orv INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    numero_orv VARCHAR(50),
    inicio_vigencia DATE,
    fin_vigencia DATE,
    estatus_fuente VARCHAR(80),
    acta_eleccion_inscrita_ran BOOLEAN,
    fecha_inscripcion_acta_ran DATE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_orv_vigencia CHECK (fin_vigencia IS NULL OR inicio_vigencia IS NULL OR fin_vigencia >= inicio_vigencia),
    CONSTRAINT chk_orv_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_orv_nucleo_inicio ON orv (id_nucleo, inicio_vigencia) WHERE activo AND inicio_vigencia IS NOT NULL;
CREATE INDEX idx_orv_nucleo_fin ON orv (id_nucleo, fin_vigencia) WHERE activo;

CREATE TABLE orv_integrante (
    id_orv_integrante INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_orv INTEGER NOT NULL REFERENCES orv(id_orv),
    id_persona INTEGER NOT NULL REFERENCES persona(id_persona),
    cargo VARCHAR(80) NOT NULL,
    fecha_inicio DATE,
    fecha_fin DATE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_orv_integrante_cargo CHECK (NULLIF(btrim(cargo), '') IS NOT NULL),
    CONSTRAINT chk_orv_integrante_fechas CHECK (fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio),
    CONSTRAINT chk_orv_integrante_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_orv_integrante_activo
    ON orv_integrante (id_orv, id_persona, cargo) WHERE activo;
CREATE INDEX idx_orv_integrante_persona ON orv_integrante (id_persona) WHERE activo;

CREATE TABLE padron_historial (
    id_padron INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    fecha_padron DATE,
    numero_ejidatarios_comuneros INTEGER,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_padron_datos CHECK (
        (fecha_padron IS NOT NULL OR numero_ejidatarios_comuneros IS NOT NULL)
        AND (numero_ejidatarios_comuneros IS NULL OR numero_ejidatarios_comuneros >= 0)
    ),
    CONSTRAINT chk_padron_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_padron_fecha ON padron_historial (id_nucleo, fecha_padron) WHERE activo AND fecha_padron IS NOT NULL;
CREATE INDEX idx_padron_nucleo_fecha ON padron_historial (id_nucleo, fecha_padron DESC) WHERE activo;

CREATE TABLE parcela (
    id_parcela INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    tipo_parcela VARCHAR(30) NOT NULL,
    no_parcela VARCHAR(80),
    no_parcela_ppt VARCHAR(80),
    certificado_parcelario VARCHAR(120),
    folio_derechos VARCHAR(120),
    constancia_vigencia_fecha DATE,
    geometria_poligono geometry(MULTIPOLYGON, 4326),
    fuente_geometria VARCHAR(250),
    fecha_fuente_geometria DATE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_parcela_tipo CHECK (tipo_parcela IN ('individual', 'copropiedad', 'otro', 'no_determinado')),
    CONSTRAINT chk_parcela_geometria CHECK (
        geometria_poligono IS NULL OR (
            NOT ST_IsEmpty(geometria_poligono)
            AND ST_IsValid(geometria_poligono)
            AND ST_SRID(geometria_poligono) = 4326
            AND GeometryType(geometria_poligono) = 'MULTIPOLYGON'
        )
    ),
    CONSTRAINT chk_parcela_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_parcela_numero ON parcela (id_nucleo, no_parcela) WHERE activo AND no_parcela IS NOT NULL;
CREATE UNIQUE INDEX uq_parcela_ppt ON parcela (id_nucleo, no_parcela_ppt) WHERE activo AND no_parcela_ppt IS NOT NULL;
CREATE INDEX idx_parcela_certificado ON parcela (certificado_parcelario) WHERE activo;
CREATE INDEX idx_parcela_folio ON parcela (folio_derechos) WHERE activo;
CREATE INDEX idx_parcela_geometria ON parcela USING gist (geometria_poligono);

CREATE TABLE parcela_titular (
    id_parcela_titular INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_parcela INTEGER NOT NULL REFERENCES parcela(id_parcela),
    id_persona INTEGER NOT NULL REFERENCES persona(id_persona),
    tipo_derecho VARCHAR(50) NOT NULL,
    porcentaje_participacion NUMERIC(7,4),
    fecha_inicio DATE,
    fecha_fin DATE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_parcela_titular_porcentaje CHECK (porcentaje_participacion IS NULL OR porcentaje_participacion > 0 AND porcentaje_participacion <= 100),
    CONSTRAINT chk_parcela_titular_fechas CHECK (fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio),
    CONSTRAINT chk_parcela_titular_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_parcela_titular_activo
    ON parcela_titular (id_parcela, id_persona, tipo_derecho) WHERE activo;
CREATE INDEX idx_parcela_titular_persona ON parcela_titular (id_persona) WHERE activo;

CREATE TABLE actividad_campo (
    id_actividad INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_proyecto_nucleo INTEGER NOT NULL REFERENCES proyecto_nucleo(id_proyecto_nucleo),
    tipo_actividad VARCHAR(30) NOT NULL,
    contexto_actividad VARCHAR(40) NOT NULL DEFAULT 'general',
    fecha_programada DATE,
    fecha_realizada DATE,
    responsable VARCHAR(300),
    resultado TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_actividad_tipo CHECK (tipo_actividad IN ('sensibilizacion', 'caminamiento')),
    CONSTRAINT chk_actividad_contexto CHECK (contexto_actividad IN ('general', 'superficie_adicional', 'obras_complementarias', 'otro')),
    CONSTRAINT chk_actividad_fechas CHECK (fecha_realizada IS NULL OR fecha_programada IS NULL OR fecha_realizada >= fecha_programada),
    CONSTRAINT chk_actividad_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE INDEX idx_actividad_pn_tipo ON actividad_campo (id_proyecto_nucleo, tipo_actividad, contexto_actividad) WHERE activo;
CREATE INDEX idx_actividad_fechas ON actividad_campo (fecha_programada, fecha_realizada) WHERE activo;

CREATE TABLE afectacion (
    id_afectacion INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_proyecto_nucleo INTEGER NOT NULL REFERENCES proyecto_nucleo(id_proyecto_nucleo),
    id_parcela INTEGER REFERENCES parcela(id_parcela),
    tipo_afectacion VARCHAR(20) NOT NULL,
    destino_superficie VARCHAR(100),
    no_parcela_solar VARCHAR(100),
    superficie_preliminar_ha NUMERIC(14,6),
    superficie_afectada_ha NUMERIC(14,6),
    situacion VARCHAR(100),
    condicion_especial VARCHAR(50),
    descripcion_condicion TEXT,
    avaluo_monto NUMERIC(18,2),
    avaluo_fecha DATE,
    avaluo_referencia VARCHAR(150),
    avaluo_institucion VARCHAR(150),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_afectacion_ambito_parcela CHECK (
        (tipo_afectacion = 'colectivo' AND id_parcela IS NULL)
        OR (tipo_afectacion = 'individual' AND id_parcela IS NOT NULL)
    ),
    CONSTRAINT chk_afectacion_superficies CHECK (
        (superficie_preliminar_ha IS NULL OR superficie_preliminar_ha >= 0)
        AND (superficie_afectada_ha IS NULL OR superficie_afectada_ha >= 0)
    ),
    CONSTRAINT chk_afectacion_avaluo CHECK (avaluo_monto IS NULL OR avaluo_monto >= 0),
    CONSTRAINT chk_afectacion_condicion CHECK (
        condicion_especial IS NULL OR condicion_especial IN (
            'expropiacion_directa', 'comunidad_indigena', 'no_afectacion_uso_comun', 'otro'
        )
    ),
    CONSTRAINT chk_afectacion_condicion_otro CHECK (
        condicion_especial <> 'otro' OR NULLIF(btrim(descripcion_condicion), '') IS NOT NULL
    ),
    CONSTRAINT chk_afectacion_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE INDEX idx_afectacion_pn_tipo ON afectacion (id_proyecto_nucleo, tipo_afectacion) WHERE activo;
CREATE INDEX idx_afectacion_parcela ON afectacion (id_parcela) WHERE activo;
CREATE INDEX idx_afectacion_destino ON afectacion (destino_superficie) WHERE activo;
CREATE INDEX idx_afectacion_condicion ON afectacion (condicion_especial) WHERE activo;

CREATE OR REPLACE FUNCTION fn_validar_afectacion_parcela_nucleo()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
DECLARE
    v_nucleo_pn INTEGER;
    v_nucleo_parcela INTEGER;
BEGIN
    IF NEW.tipo_afectacion = 'individual' AND NEW.activo THEN
        SELECT id_nucleo INTO v_nucleo_pn
        FROM proyecto_nucleo WHERE id_proyecto_nucleo = NEW.id_proyecto_nucleo AND activo;
        SELECT id_nucleo INTO v_nucleo_parcela
        FROM parcela WHERE id_parcela = NEW.id_parcela AND activo;
        IF v_nucleo_pn IS NULL OR v_nucleo_parcela IS NULL OR v_nucleo_pn <> v_nucleo_parcela THEN
            RAISE EXCEPTION 'La parcela individual debe estar activa y pertenecer al mismo núcleo de ProyectoNucleo';
        END IF;
    END IF;
    RETURN NEW;
END;
$fn$;
CREATE TRIGGER trg_afectacion_parcela_nucleo
    BEFORE INSERT OR UPDATE OF id_proyecto_nucleo, id_parcela, tipo_afectacion, activo
    ON afectacion FOR EACH ROW EXECUTE FUNCTION fn_validar_afectacion_parcela_nucleo();

CREATE TABLE asamblea (
    id_asamblea INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_proyecto_nucleo INTEGER NOT NULL REFERENCES proyecto_nucleo(id_proyecto_nucleo),
    id_padron INTEGER REFERENCES padron_historial(id_padron),
    tipo_asamblea VARCHAR(40) NOT NULL,
    proposito TEXT,
    fecha_expedicion_primera DATE,
    fecha_programada_primera DATE,
    fecha_expedicion_segunda DATE,
    fecha_programada_segunda DATE,
    fecha_realizada DATE,
    resultado VARCHAR(50),
    fecha_programada_ingreso_ran DATE,
    fecha_ingreso_ran DATE,
    numero_solicitud_ran VARCHAR(120),
    calificacion_registral_ran TEXT,
    fecha_inscripcion_ran DATE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_asamblea_tipo CHECK (tipo_asamblea IN ('anuencia', 'modificatorio', 'superficie_adicional', 'obras_complementarias', 'retiro_fondos', 'otra')),
    CONSTRAINT chk_asamblea_convocatorias CHECK (
        (fecha_programada_primera IS NULL OR fecha_expedicion_primera IS NULL OR fecha_programada_primera >= fecha_expedicion_primera)
        AND (fecha_programada_segunda IS NULL OR fecha_expedicion_segunda IS NULL OR fecha_programada_segunda >= fecha_expedicion_segunda)
    ),
    CONSTRAINT chk_asamblea_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE INDEX idx_asamblea_pn_tipo ON asamblea (id_proyecto_nucleo, tipo_asamblea) WHERE activo;
CREATE INDEX idx_asamblea_ran ON asamblea (fecha_ingreso_ran, fecha_inscripcion_ran) WHERE activo;
CREATE INDEX idx_asamblea_solicitud ON asamblea (numero_solicitud_ran) WHERE activo;

CREATE OR REPLACE FUNCTION fn_validar_asamblea_padron()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
DECLARE
    v_nucleo_pn INTEGER;
    v_nucleo_padron INTEGER;
BEGIN
    IF NEW.id_padron IS NOT NULL AND NEW.activo THEN
        SELECT id_nucleo INTO v_nucleo_pn FROM proyecto_nucleo
        WHERE id_proyecto_nucleo = NEW.id_proyecto_nucleo AND activo;
        SELECT id_nucleo INTO v_nucleo_padron FROM padron_historial
        WHERE id_padron = NEW.id_padron AND activo;
        IF v_nucleo_pn IS NULL OR v_nucleo_padron IS NULL OR v_nucleo_pn <> v_nucleo_padron THEN
            RAISE EXCEPTION 'El padrón de la asamblea debe pertenecer al mismo núcleo';
        END IF;
    END IF;
    RETURN NEW;
END;
$fn$;
CREATE TRIGGER trg_asamblea_padron
    BEFORE INSERT OR UPDATE OF id_proyecto_nucleo, id_padron, activo
    ON asamblea FOR EACH ROW EXECUTE FUNCTION fn_validar_asamblea_padron();

CREATE TABLE convenio (
    id_convenio INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_proyecto_nucleo INTEGER NOT NULL REFERENCES proyecto_nucleo(id_proyecto_nucleo),
    ambito VARCHAR(20) NOT NULL,
    tipo_instrumento VARCHAR(20) NOT NULL DEFAULT 'convenio',
    tipo_convenio VARCHAR(40),
    modalidad_especial VARCHAR(30),
    descripcion_modalidad TEXT,
    descripcion_instrumento TEXT,
    consecutivo INTEGER NOT NULL DEFAULT 1,
    id_convenio_padre INTEGER REFERENCES convenio(id_convenio),
    id_asamblea_autorizacion INTEGER REFERENCES asamblea(id_asamblea),
    fecha_programada_firma DATE,
    fecha_firma DATE,
    monto_90 NUMERIC(18,2),
    monto_100 NUMERIC(18,2),
    monto_bdt NUMERIC(18,2),
    superficie_ha NUMERIC(14,6),
    fecha_programada_ingreso_ran DATE,
    ingreso_ran_fecha DATE,
    numero_solicitud_ingreso VARCHAR(120),
    calificacion_registral TEXT,
    fecha_inscripcion_ran DATE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_convenio_ambito CHECK (ambito IN ('colectivo', 'individual')),
    CONSTRAINT chk_convenio_instrumento CHECK (tipo_instrumento IN ('convenio', 'otro')),
    CONSTRAINT chk_convenio_tipo_ambito CHECK (
        (tipo_instrumento = 'otro' AND tipo_convenio IS NULL AND NULLIF(btrim(descripcion_instrumento), '') IS NOT NULL)
        OR (tipo_instrumento = 'convenio' AND (
            (ambito = 'colectivo' AND tipo_convenio IN ('cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias'))
            OR (ambito = 'individual' AND tipo_convenio IN ('cop_original', 'modificatorio', 'ampliacion', 'ampliacion_remanente'))
        ))
    ),
    CONSTRAINT chk_convenio_modalidad CHECK (
        modalidad_especial IS NULL
        OR modalidad_especial IN ('permuta', 'otra')
    ),
    CONSTRAINT chk_convenio_modalidad_descripcion CHECK (
        modalidad_especial <> 'otra' OR NULLIF(btrim(descripcion_modalidad), '') IS NOT NULL
    ),
    CONSTRAINT chk_convenio_permuta CHECK (
        modalidad_especial <> 'permuta' OR tipo_convenio = 'cop_original'
    ),
    CONSTRAINT chk_convenio_consecutivo CHECK (consecutivo > 0),
    CONSTRAINT chk_convenio_padre CHECK (id_convenio_padre IS NULL OR id_convenio_padre <> id_convenio),
    CONSTRAINT chk_convenio_montos CHECK (
        (monto_90 IS NULL OR monto_90 >= 0)
        AND (monto_100 IS NULL OR monto_100 >= 0)
        AND (monto_bdt IS NULL OR monto_bdt >= 0)
        AND (monto_90 IS NULL OR monto_100 IS NULL OR monto_90 <= monto_100)
        AND (superficie_ha IS NULL OR superficie_ha >= 0)
    ),
    CONSTRAINT chk_convenio_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_convenio_padre_consecutivo
    ON convenio (id_convenio_padre, consecutivo) WHERE activo AND id_convenio_padre IS NOT NULL;
CREATE INDEX idx_convenio_pn_ambito_tipo ON convenio (id_proyecto_nucleo, ambito, tipo_convenio) WHERE activo;
CREATE INDEX idx_convenio_padre ON convenio (id_convenio_padre) WHERE activo;
CREATE INDEX idx_convenio_ran ON convenio (ingreso_ran_fecha, fecha_inscripcion_ran) WHERE activo;

CREATE TABLE convenio_afectacion (
    id_convenio_afectacion INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_convenio INTEGER NOT NULL REFERENCES convenio(id_convenio),
    id_afectacion INTEGER NOT NULL REFERENCES afectacion(id_afectacion),
    rol VARCHAR(20) NOT NULL DEFAULT 'principal',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_convenio_afectacion_rol CHECK (rol IN ('principal', 'adicional')),
    CONSTRAINT chk_convenio_afectacion_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_convenio_afectacion_activa
    ON convenio_afectacion (id_convenio, id_afectacion) WHERE activo;
CREATE UNIQUE INDEX uq_convenio_afectacion_principal
    ON convenio_afectacion (id_convenio) WHERE activo AND rol = 'principal';
CREATE INDEX idx_convenio_afectacion_afectacion ON convenio_afectacion (id_afectacion) WHERE activo;

CREATE OR REPLACE FUNCTION fn_validar_convenio_relaciones()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
DECLARE
    v_padre convenio%ROWTYPE;
    v_asamblea asamblea%ROWTYPE;
BEGIN
    IF NEW.id_convenio_padre IS NOT NULL THEN
        SELECT * INTO v_padre FROM convenio WHERE id_convenio = NEW.id_convenio_padre AND activo;
        IF v_padre.id_convenio IS NULL
           OR v_padre.id_proyecto_nucleo <> NEW.id_proyecto_nucleo
           OR v_padre.ambito <> NEW.ambito THEN
            RAISE EXCEPTION 'El convenio padre debe estar activo y pertenecer al mismo ProyectoNucleo/ámbito';
        END IF;
    END IF;
    IF NEW.id_asamblea_autorizacion IS NOT NULL THEN
        SELECT * INTO v_asamblea FROM asamblea WHERE id_asamblea = NEW.id_asamblea_autorizacion AND activo;
        IF NEW.ambito <> 'colectivo' OR v_asamblea.id_asamblea IS NULL
           OR v_asamblea.id_proyecto_nucleo <> NEW.id_proyecto_nucleo THEN
            RAISE EXCEPTION 'La asamblea sólo autoriza convenios colectivos del mismo ProyectoNucleo';
        END IF;
    END IF;
    RETURN NEW;
END;
$fn$;
CREATE TRIGGER trg_convenio_relaciones
    BEFORE INSERT OR UPDATE OF id_proyecto_nucleo, ambito, id_convenio_padre, id_asamblea_autorizacion
    ON convenio FOR EACH ROW EXECUTE FUNCTION fn_validar_convenio_relaciones();

CREATE OR REPLACE FUNCTION fn_validar_convenio_afectacion()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
DECLARE
    v_convenio convenio%ROWTYPE;
    v_afectacion afectacion%ROWTYPE;
BEGIN
    IF NEW.activo THEN
        SELECT * INTO v_convenio FROM convenio WHERE id_convenio = NEW.id_convenio AND activo;
        SELECT * INTO v_afectacion FROM afectacion WHERE id_afectacion = NEW.id_afectacion AND activo;
        IF v_convenio.id_convenio IS NULL OR v_afectacion.id_afectacion IS NULL
           OR v_convenio.id_proyecto_nucleo <> v_afectacion.id_proyecto_nucleo
           OR v_convenio.ambito <> v_afectacion.tipo_afectacion THEN
            RAISE EXCEPTION 'Convenio y afectación deben estar activos y compartir ProyectoNucleo/ámbito';
        END IF;
    END IF;
    RETURN NEW;
END;
$fn$;
CREATE TRIGGER trg_convenio_afectacion_coherencia
    BEFORE INSERT OR UPDATE OF id_convenio, id_afectacion, activo
    ON convenio_afectacion FOR EACH ROW EXECUTE FUNCTION fn_validar_convenio_afectacion();

CREATE OR REPLACE FUNCTION fn_convenio_requiere_afectacion()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
DECLARE
    v_id INTEGER := CASE WHEN TG_TABLE_NAME = 'convenio' THEN NEW.id_convenio ELSE NEW.id_convenio END;
BEGIN
    IF EXISTS (SELECT 1 FROM convenio WHERE id_convenio = v_id AND activo)
       AND NOT EXISTS (SELECT 1 FROM convenio_afectacion WHERE id_convenio = v_id AND activo) THEN
        RAISE EXCEPTION 'Un convenio activo requiere al menos una afectación activa asociada';
    END IF;
    RETURN NULL;
END;
$fn$;
CREATE CONSTRAINT TRIGGER ctr_convenio_requiere_afectacion
    AFTER INSERT OR UPDATE OF activo ON convenio
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION fn_convenio_requiere_afectacion();
CREATE CONSTRAINT TRIGGER ctr_convenio_vinculo_requerido
    AFTER INSERT OR UPDATE OF activo, id_convenio ON convenio_afectacion
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION fn_convenio_requiere_afectacion();

CREATE TABLE tramite_fifonafe (
    id_tramite_fifonafe INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_proyecto_nucleo INTEGER NOT NULL REFERENCES proyecto_nucleo(id_proyecto_nucleo),
    ambito VARCHAR(20) NOT NULL,
    estatus VARCHAR(30) NOT NULL DEFAULT 'pendiente',
    no_oficio_fifonafe_a_dgaopr VARCHAR(100),
    fecha_oficio_fifonafe_a_dgaopr DATE,
    no_oficio_dgaopr_a_representacion VARCHAR(100),
    fecha_oficio_dgaopr_a_representacion DATE,
    no_oficio_respuesta_representacion_a_dgaopr VARCHAR(100),
    fecha_oficio_respuesta_representacion_a_dgaopr DATE,
    no_oficio_respuesta_dgaopr_a_fifonafe VARCHAR(100),
    fecha_oficio_respuesta_dgaopr_a_fifonafe DATE,
    hay_conflictos BOOLEAN,
    resultado_no_conflictos TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_fifonafe_ambito CHECK (ambito IN ('colectivo', 'individual')),
    CONSTRAINT chk_fifonafe_estatus CHECK (estatus IN ('programado', 'pendiente', 'completo', 'cancelado', 'otro')),
    CONSTRAINT chk_fifonafe_completo CHECK (
        estatus <> 'completo' OR (
            NULLIF(btrim(no_oficio_fifonafe_a_dgaopr), '') IS NOT NULL AND fecha_oficio_fifonafe_a_dgaopr IS NOT NULL
            AND NULLIF(btrim(no_oficio_dgaopr_a_representacion), '') IS NOT NULL AND fecha_oficio_dgaopr_a_representacion IS NOT NULL
            AND NULLIF(btrim(no_oficio_respuesta_representacion_a_dgaopr), '') IS NOT NULL AND fecha_oficio_respuesta_representacion_a_dgaopr IS NOT NULL
            AND NULLIF(btrim(no_oficio_respuesta_dgaopr_a_fifonafe), '') IS NOT NULL AND fecha_oficio_respuesta_dgaopr_a_fifonafe IS NOT NULL
        )
    ),
    CONSTRAINT chk_fifonafe_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE INDEX idx_fifonafe_pn_ambito ON tramite_fifonafe (id_proyecto_nucleo, ambito, estatus) WHERE activo;

CREATE TABLE tramite_fifonafe_afectacion (
    id_tramite_fifonafe_afectacion INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_tramite_fifonafe INTEGER NOT NULL REFERENCES tramite_fifonafe(id_tramite_fifonafe),
    id_afectacion INTEGER NOT NULL REFERENCES afectacion(id_afectacion),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_fifonafe_afectacion_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_fifonafe_afectacion_activa
    ON tramite_fifonafe_afectacion (id_tramite_fifonafe, id_afectacion) WHERE activo;
CREATE INDEX idx_fifonafe_afectacion_afectacion ON tramite_fifonafe_afectacion (id_afectacion) WHERE activo;

CREATE OR REPLACE FUNCTION fn_validar_fifonafe_afectacion()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
DECLARE
    v_tramite tramite_fifonafe%ROWTYPE;
    v_afectacion afectacion%ROWTYPE;
BEGIN
    IF NEW.activo THEN
        SELECT * INTO v_tramite FROM tramite_fifonafe WHERE id_tramite_fifonafe = NEW.id_tramite_fifonafe AND activo;
        SELECT * INTO v_afectacion FROM afectacion WHERE id_afectacion = NEW.id_afectacion AND activo;
        IF v_tramite.id_tramite_fifonafe IS NULL OR v_afectacion.id_afectacion IS NULL
           OR v_tramite.id_proyecto_nucleo <> v_afectacion.id_proyecto_nucleo
           OR v_tramite.ambito <> v_afectacion.tipo_afectacion THEN
            RAISE EXCEPTION 'FIFONAFE y afectación deben estar activos y compartir ProyectoNucleo/ámbito';
        END IF;
    END IF;
    RETURN NEW;
END;
$fn$;
CREATE TRIGGER trg_fifonafe_afectacion_coherencia
    BEFORE INSERT OR UPDATE OF id_tramite_fifonafe, id_afectacion, activo
    ON tramite_fifonafe_afectacion FOR EACH ROW EXECUTE FUNCTION fn_validar_fifonafe_afectacion();

CREATE OR REPLACE FUNCTION fn_fifonafe_requiere_afectacion()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
DECLARE
    v_id INTEGER := NEW.id_tramite_fifonafe;
BEGIN
    IF EXISTS (SELECT 1 FROM tramite_fifonafe WHERE id_tramite_fifonafe = v_id AND activo)
       AND NOT EXISTS (SELECT 1 FROM tramite_fifonafe_afectacion WHERE id_tramite_fifonafe = v_id AND activo) THEN
        RAISE EXCEPTION 'Un trámite FIFONAFE activo requiere al menos una afectación activa asociada';
    END IF;
    RETURN NULL;
END;
$fn$;
CREATE CONSTRAINT TRIGGER ctr_fifonafe_requiere_afectacion
    AFTER INSERT OR UPDATE OF activo ON tramite_fifonafe
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION fn_fifonafe_requiere_afectacion();
CREATE CONSTRAINT TRIGGER ctr_fifonafe_vinculo_requerido
    AFTER INSERT OR UPDATE OF activo, id_tramite_fifonafe ON tramite_fifonafe_afectacion
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION fn_fifonafe_requiere_afectacion();

CREATE TABLE indemnizacion (
    id_indemnizacion INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_afectacion INTEGER NOT NULL REFERENCES afectacion(id_afectacion),
    estatus VARCHAR(30) NOT NULL DEFAULT 'pendiente',
    descripcion_estatus TEXT,
    fecha_programada DATE,
    fecha_resolucion DATE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_indemnizacion_estatus CHECK (estatus IN ('pendiente', 'programado', 'completo', 'otro')),
    CONSTRAINT chk_indemnizacion_otro CHECK (estatus <> 'otro' OR NULLIF(btrim(descripcion_estatus), '') IS NOT NULL),
    CONSTRAINT chk_indemnizacion_fechas CHECK (fecha_resolucion IS NULL OR fecha_programada IS NULL OR fecha_resolucion >= fecha_programada),
    CONSTRAINT chk_indemnizacion_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_indemnizacion_afectacion_activa ON indemnizacion (id_afectacion) WHERE activo;
CREATE INDEX idx_indemnizacion_estatus ON indemnizacion (estatus) WHERE activo;

CREATE TABLE pago (
    id_pago INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_indemnizacion INTEGER NOT NULL REFERENCES indemnizacion(id_indemnizacion),
    fecha_pago DATE NOT NULL,
    monto NUMERIC(18,2) NOT NULL,
    id_persona_beneficiaria INTEGER REFERENCES persona(id_persona),
    beneficiario_nombre VARCHAR(300) NOT NULL,
    referencia VARCHAR(150),
    medio_pago VARCHAR(30),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_pago_monto CHECK (monto > 0),
    CONSTRAINT chk_pago_beneficiario CHECK (NULLIF(btrim(beneficiario_nombre), '') IS NOT NULL),
    CONSTRAINT chk_pago_medio CHECK (medio_pago IS NULL OR medio_pago IN ('transferencia', 'cheque', 'efectivo', 'deposito', 'otro')),
    CONSTRAINT chk_pago_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_pago_referencia ON pago (id_indemnizacion, referencia) WHERE activo AND referencia IS NOT NULL;
CREATE INDEX idx_pago_indemnizacion_fecha ON pago (id_indemnizacion, fecha_pago) WHERE activo;
CREATE INDEX idx_pago_persona ON pago (id_persona_beneficiaria) WHERE activo;

CREATE TABLE documento (
    id_documento INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tipo_documento VARCHAR(80) NOT NULL,
    estado VARCHAR(20) NOT NULL,
    titulo VARCHAR(250),
    descripcion TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_documento_tipo CHECK (NULLIF(btrim(tipo_documento), '') IS NOT NULL),
    CONSTRAINT chk_documento_estado CHECK (estado IN ('disponible', 'faltante', 'referenciado')),
    CONSTRAINT chk_documento_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE INDEX idx_documento_tipo_estado ON documento (tipo_documento, estado) WHERE activo;

CREATE TABLE documento_version (
    id_documento_version BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_documento INTEGER NOT NULL REFERENCES documento(id_documento),
    numero_version INTEGER NOT NULL,
    hash_sha256 CHAR(64) NOT NULL,
    tamano_bytes BIGINT NOT NULL,
    nombre_original VARCHAR(255) NOT NULL,
    ruta_almacenamiento TEXT NOT NULL,
    tipo_mime VARCHAR(150),
    fecha_carga TIMESTAMPTZ NOT NULL DEFAULT now(),
    id_usuario_carga INTEGER NOT NULL REFERENCES usuario(id_usuario),
    CONSTRAINT uq_documento_version UNIQUE (id_documento, numero_version),
    CONSTRAINT uq_documento_ruta UNIQUE (ruta_almacenamiento),
    CONSTRAINT uq_documento_hash UNIQUE (id_documento, hash_sha256),
    CONSTRAINT chk_documento_version CHECK (numero_version > 0 AND tamano_bytes >= 0),
    CONSTRAINT chk_documento_hash CHECK (hash_sha256 ~ '^[0-9a-f]{64}$')
);

CREATE OR REPLACE FUNCTION fn_documento_version_inmutable()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
BEGIN
    RAISE EXCEPTION 'Las versiones documentales son inmutables';
END;
$fn$;
CREATE TRIGGER trg_documento_version_inmutable
    BEFORE UPDATE OR DELETE ON documento_version
    FOR EACH ROW EXECUTE FUNCTION fn_documento_version_inmutable();

CREATE TABLE documento_vinculo (
    id_documento_vinculo INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_documento INTEGER NOT NULL REFERENCES documento(id_documento),
    entidad_tipo VARCHAR(50) NOT NULL,
    entidad_id INTEGER NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_documento_vinculo_tipo CHECK (entidad_tipo IN (
        'proyecto_nucleo', 'nucleo_agrario', 'orv', 'padron_historial', 'parcela',
        'afectacion', 'asamblea', 'convenio', 'tramite_fifonafe', 'indemnizacion', 'pago'
    )),
    CONSTRAINT chk_documento_vinculo_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_documento_vinculo_activo
    ON documento_vinculo (id_documento, entidad_tipo, entidad_id) WHERE activo;
CREATE INDEX idx_documento_vinculo_objetivo ON documento_vinculo (entidad_tipo, entidad_id) WHERE activo;

CREATE OR REPLACE FUNCTION fn_objetivo_controlado_existe(p_tipo TEXT, p_id BIGINT)
RETURNS BOOLEAN LANGUAGE plpgsql STABLE AS $fn$
DECLARE
    v_pk TEXT;
    v_exists BOOLEAN;
BEGIN
    v_pk := CASE p_tipo
        WHEN 'proyecto' THEN 'id_proyecto'
        WHEN 'proyecto_nucleo' THEN 'id_proyecto_nucleo'
        WHEN 'proyecto_nucleo_referencia' THEN 'id_referencia'
        WHEN 'nucleo_agrario' THEN 'id_nucleo'
        WHEN 'persona' THEN 'id_persona'
        WHEN 'orv' THEN 'id_orv'
        WHEN 'orv_integrante' THEN 'id_orv_integrante'
        WHEN 'padron_historial' THEN 'id_padron'
        WHEN 'parcela' THEN 'id_parcela'
        WHEN 'parcela_titular' THEN 'id_parcela_titular'
        WHEN 'actividad_campo' THEN 'id_actividad'
        WHEN 'afectacion' THEN 'id_afectacion'
        WHEN 'asamblea' THEN 'id_asamblea'
        WHEN 'convenio' THEN 'id_convenio'
        WHEN 'tramite_fifonafe' THEN 'id_tramite_fifonafe'
        WHEN 'indemnizacion' THEN 'id_indemnizacion'
        WHEN 'pago' THEN 'id_pago'
        WHEN 'documento' THEN 'id_documento'
        ELSE NULL
    END;
    IF v_pk IS NULL OR to_regclass('public.' || p_tipo) IS NULL THEN
        RETURN FALSE;
    END IF;
    EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I WHERE %I = $1)', p_tipo, v_pk)
       INTO v_exists USING p_id;
    RETURN v_exists;
END;
$fn$;

CREATE OR REPLACE FUNCTION fn_validar_documento_vinculo()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
BEGIN
    IF NEW.activo AND NOT fn_objetivo_controlado_existe(NEW.entidad_tipo, NEW.entidad_id) THEN
        RAISE EXCEPTION 'El objetivo documental %:% no existe', NEW.entidad_tipo, NEW.entidad_id;
    END IF;
    RETURN NEW;
END;
$fn$;
CREATE TRIGGER trg_documento_vinculo_objetivo
    BEFORE INSERT OR UPDATE OF entidad_tipo, entidad_id, activo ON documento_vinculo
    FOR EACH ROW EXECUTE FUNCTION fn_validar_documento_vinculo();

CREATE TABLE trazabilidad_fuente (
    id_trazabilidad BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    entidad_tipo VARCHAR(50) NOT NULL,
    entidad_id BIGINT NOT NULL,
    archivo VARCHAR(255) NOT NULL,
    hoja VARCHAR(255),
    fila INTEGER,
    columna VARCHAR(120),
    valor_original TEXT,
    tratamiento VARCHAR(30) NOT NULL,
    registrado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    id_usuario_registro INTEGER REFERENCES usuario(id_usuario),
    CONSTRAINT chk_trazabilidad_archivo CHECK (NULLIF(btrim(archivo), '') IS NOT NULL),
    CONSTRAINT chk_trazabilidad_fila CHECK (fila IS NULL OR fila > 0),
    CONSTRAINT chk_trazabilidad_tratamiento CHECK (tratamiento IN (
        'PERSISTIR', 'DERIVAR', 'REFERENCIA', 'DOCUMENTAR', 'REVISAR', 'NO IMPLEMENTAR'
    ))
);
CREATE INDEX idx_trazabilidad_objetivo ON trazabilidad_fuente (entidad_tipo, entidad_id);
CREATE INDEX idx_trazabilidad_fuente ON trazabilidad_fuente (archivo, hoja, fila);

CREATE OR REPLACE FUNCTION fn_validar_trazabilidad_objetivo()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
BEGIN
    IF NOT fn_objetivo_controlado_existe(NEW.entidad_tipo, NEW.entidad_id) THEN
        RAISE EXCEPTION 'El objetivo de trazabilidad %:% no existe o no está permitido', NEW.entidad_tipo, NEW.entidad_id;
    END IF;
    RETURN NEW;
END;
$fn$;
CREATE TRIGGER trg_trazabilidad_objetivo
    BEFORE INSERT OR UPDATE OF entidad_tipo, entidad_id ON trazabilidad_fuente
    FOR EACH ROW EXECUTE FUNCTION fn_validar_trazabilidad_objetivo();

CREATE TABLE usuario_proyecto (
    id_usuario_proyecto INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario),
    id_proyecto INTEGER NOT NULL REFERENCES proyecto(id_proyecto),
    asignado_por INTEGER NOT NULL REFERENCES usuario(id_usuario),
    fecha_asignacion TIMESTAMPTZ NOT NULL DEFAULT now(),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_usuario_proyecto_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uq_usuario_proyecto_activo ON usuario_proyecto (id_usuario, id_proyecto) WHERE activo;
CREATE INDEX idx_usuario_proyecto_usuario ON usuario_proyecto (id_usuario) WHERE activo;
CREATE INDEX idx_usuario_proyecto_proyecto ON usuario_proyecto (id_proyecto) WHERE activo;

CREATE TABLE bitacora (
    id_bitacora BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_usuario INTEGER REFERENCES usuario(id_usuario),
    id_proyecto INTEGER REFERENCES proyecto(id_proyecto),
    id_proyecto_nucleo INTEGER REFERENCES proyecto_nucleo(id_proyecto_nucleo),
    id_nucleo INTEGER REFERENCES nucleo_agrario(id_nucleo),
    entidad_tipo VARCHAR(100) NOT NULL,
    entidad_id BIGINT,
    accion VARCHAR(30) NOT NULL CHECK (accion IN ('insert', 'update', 'delete', 'validacion', 'cambio_estado', 'carga_documento')),
    valor_anterior JSONB,
    valor_nuevo JSONB,
    fecha_hora TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_origen INET,
    user_agent TEXT
);
CREATE INDEX idx_bitacora_fecha ON bitacora (fecha_hora DESC);
CREATE INDEX idx_bitacora_usuario ON bitacora (id_usuario, fecha_hora DESC);
CREATE INDEX idx_bitacora_proyecto ON bitacora (id_proyecto, fecha_hora DESC);
CREATE INDEX idx_bitacora_pn ON bitacora (id_proyecto_nucleo, fecha_hora DESC);
CREATE INDEX idx_bitacora_objetivo ON bitacora (entidad_tipo, entidad_id);

CREATE OR REPLACE FUNCTION fn_audit_log()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $fn$
DECLARE
    v_row JSONB;
    v_old JSONB;
    v_new JSONB;
    v_id BIGINT;
    v_user_id INTEGER;
    v_pn INTEGER;
    v_project INTEGER;
    v_nucleo INTEGER;
    v_system_event_id TEXT;
BEGIN
    v_system_event_id := current_setting('app.auth_system_event_id', TRUE);
    IF TG_TABLE_NAME = 'sesion_usuario'
       AND TG_OP = 'UPDATE'
       AND NULLIF(v_system_event_id, '') IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM evento_acceso
            WHERE id_evento = v_system_event_id::BIGINT
              AND id_sesion = NEW.id_sesion
              AND id_usuario = NEW.id_usuario
              AND id_usuario_actor IS NULL
              AND tipo_evento = 'sesion_expirada'
              AND motivo_codigo = NEW.motivo_revocacion
              AND motivo_codigo IN ('expiracion_inactividad', 'expiracion_absoluta')
              AND txid_registro = txid_current()
        ) OR OLD.revocada_en IS NOT NULL
          OR NEW.revocada_en IS NULL
          OR NEW.id_usuario_revoca IS NOT NULL
          OR to_jsonb(NEW) - ARRAY['revocada_en','id_usuario_revoca','motivo_revocacion']
             IS DISTINCT FROM
             to_jsonb(OLD) - ARRAY['revocada_en','id_usuario_revoca','motivo_revocacion'] THEN
            RAISE EXCEPTION 'Expiración de sesión sin evento de sistema correlacionado o con cambios no permitidos';
        END IF;
        RETURN NEW;
    END IF;

    IF TG_OP = 'INSERT' THEN
        v_new := to_jsonb(NEW) - ARRAY['contrasena_hash', 'token_hash', 'csrf_hash'];
        v_row := v_new;
    ELSIF TG_OP = 'UPDATE' THEN
        v_old := to_jsonb(OLD) - ARRAY['contrasena_hash', 'token_hash', 'csrf_hash'];
        v_new := to_jsonb(NEW) - ARRAY['contrasena_hash', 'token_hash', 'csrf_hash'];
        v_row := v_new;
    ELSE
        v_old := to_jsonb(OLD) - ARRAY['contrasena_hash', 'token_hash', 'csrf_hash'];
        v_row := v_old;
    END IF;

    v_user_id := NULLIF(current_setting('app.current_user_id', TRUE), '')::INTEGER;
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Auditoría fallida: falta app.current_user_id en la transacción';
    END IF;
    v_id := NULLIF(v_row ->> TG_ARGV[0], '')::BIGINT;
    v_pn := NULLIF(v_row ->> 'id_proyecto_nucleo', '')::INTEGER;
    v_project := NULLIF(v_row ->> 'id_proyecto', '')::INTEGER;
    v_nucleo := NULLIF(v_row ->> 'id_nucleo', '')::INTEGER;

    IF TG_TABLE_NAME = 'proyecto' THEN v_project := v_id::INTEGER; END IF;
    IF TG_TABLE_NAME = 'proyecto_nucleo' THEN v_pn := v_id::INTEGER; END IF;
    IF TG_TABLE_NAME = 'nucleo_agrario' THEN v_nucleo := v_id::INTEGER; END IF;

    IF v_pn IS NULL AND TG_TABLE_NAME IN ('convenio_afectacion', 'indemnizacion', 'pago') THEN
        IF TG_TABLE_NAME = 'convenio_afectacion' THEN
            SELECT c.id_proyecto_nucleo INTO v_pn FROM convenio c WHERE c.id_convenio = (v_row ->> 'id_convenio')::INTEGER;
        ELSIF TG_TABLE_NAME = 'indemnizacion' THEN
            SELECT a.id_proyecto_nucleo INTO v_pn FROM afectacion a WHERE a.id_afectacion = (v_row ->> 'id_afectacion')::INTEGER;
        ELSE
            SELECT a.id_proyecto_nucleo INTO v_pn
            FROM indemnizacion i JOIN afectacion a ON a.id_afectacion = i.id_afectacion
            WHERE i.id_indemnizacion = (v_row ->> 'id_indemnizacion')::INTEGER;
        END IF;
    END IF;
    IF v_pn IS NOT NULL THEN
        SELECT pn.id_proyecto, pn.id_nucleo INTO v_project, v_nucleo
        FROM proyecto_nucleo pn WHERE pn.id_proyecto_nucleo = v_pn;
    END IF;

    INSERT INTO bitacora (
        id_usuario, id_proyecto, id_proyecto_nucleo, id_nucleo,
        entidad_tipo, entidad_id, accion, valor_anterior, valor_nuevo
    ) VALUES (
        v_user_id, v_project, v_pn, v_nucleo,
        TG_TABLE_NAME, v_id, lower(TG_OP), v_old, v_new
    );
    RETURN COALESCE(NEW, OLD);
END;
$fn$;

CREATE OR REPLACE FUNCTION fn_auth_prevent_physical_delete()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
BEGIN
    RAISE EXCEPTION 'Los estados y sesiones de autenticación no admiten DELETE físico';
END;
$fn$;

CREATE TRIGGER trg_008_prevent_delete_estado
    BEFORE DELETE ON estado_autenticacion_usuario
    FOR EACH ROW EXECUTE FUNCTION fn_auth_prevent_physical_delete();
CREATE TRIGGER trg_008_prevent_delete_sesion
    BEFORE DELETE ON sesion_usuario
    FOR EACH ROW EXECUTE FUNCTION fn_auth_prevent_physical_delete();
CREATE TRIGGER trg_008_audit_sesion
    AFTER INSERT OR UPDATE ON sesion_usuario
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_sesion');

DO $audit_triggers$
DECLARE
    v_item TEXT[];
BEGIN
    FOREACH v_item SLICE 1 IN ARRAY ARRAY[
        ARRAY['proyecto','id_proyecto'], ARRAY['nucleo_agrario','id_nucleo'],
        ARRAY['proyecto_nucleo','id_proyecto_nucleo'], ARRAY['proyecto_nucleo_referencia','id_referencia'],
        ARRAY['persona','id_persona'], ARRAY['orv','id_orv'], ARRAY['orv_integrante','id_orv_integrante'],
        ARRAY['padron_historial','id_padron'], ARRAY['parcela','id_parcela'],
        ARRAY['parcela_titular','id_parcela_titular'], ARRAY['actividad_campo','id_actividad'],
        ARRAY['afectacion','id_afectacion'], ARRAY['asamblea','id_asamblea'],
        ARRAY['convenio','id_convenio'], ARRAY['convenio_afectacion','id_convenio_afectacion'],
        ARRAY['tramite_fifonafe','id_tramite_fifonafe'],
        ARRAY['tramite_fifonafe_afectacion','id_tramite_fifonafe_afectacion'],
        ARRAY['indemnizacion','id_indemnizacion'], ARRAY['pago','id_pago'],
        ARRAY['documento','id_documento'], ARRAY['documento_vinculo','id_documento_vinculo'],
        ARRAY['usuario_proyecto','id_usuario_proyecto'], ARRAY['usuario','id_usuario']
    ]
    LOOP
        EXECUTE format(
            'CREATE TRIGGER %I AFTER INSERT OR UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION fn_audit_log(%L)',
            'trg_audit_' || v_item[1], v_item[1], v_item[2]
        );
    END LOOP;
END;
$audit_triggers$;

-- Rol lógico de aplicación: lectura/escritura sin DELETE físico.
DO $role$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'software_pa_app') THEN
        CREATE ROLE software_pa_app NOLOGIN;
    END IF;
END;
$role$;
GRANT USAGE ON SCHEMA public TO software_pa_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO software_pa_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO software_pa_app;
REVOKE DELETE, TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM software_pa_app;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('031', 'Reset controlado y dominio ProyectoNucleo/Parcela objetivo');

COMMIT;
