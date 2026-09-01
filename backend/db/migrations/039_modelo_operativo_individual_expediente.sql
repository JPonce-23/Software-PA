-- 039_modelo_operativo_individual_expediente.sql
--
-- Objetivo:
--   Cerrar el modelo operativo INDIVIDUAL sin convertir el Excel en esquema relacional.
--   El modelo conserva:
--     NucleoAgrario -> Parcela/ParcelaTitular/UnidadAgraria (identidad estable)
--     ProyectoNucleo -> Afectacion (hecho operativo)
--     Afectacion <-> UnidadAgraria (N:M, superficie de la afectacion)
--     Convenio (un registro por instrumento: original/modificatorio/ampliacion/remanente)
--     Convenio -> TramiteRAN 1:N -> EventoRAN 1:N
--     Afectacion -> Indemnizacion -> Pago
--     ProyectoNucleo -> TramiteFIFONAFE -> EventoFIFONAFE
--
-- Novedades 039:
--   1) ActividadCampo puede contextualizarse a una Afectacion individual.
--   2) Se valida el linaje de convenios individuales.
--   3) Se modelan comparecientes/firmantes individuales por convenio, con evidencia de derecho.
--   4) ExpedienteRequisito gana un objetivo documental concreto y repetible por instrumento/tramite.
--   5) Se amplian objetivos de DocumentoVinculo para titularidades individuales.
--   6) Se agregan catalogos/requisitos para expediente individual y eventos FIFONAFE individuales.
--
-- Fuera de alcance:
--   - importador Excel;
--   - frontend;
--   - creacion de Tramo/TramoNucleo/AfectacionCiclo;
--   - inferir firmantes historicos o convertir textos mixtos de Excel directamente a DATE.

BEGIN;

SELECT pg_advisory_xact_lock(20260902, 39);

DO LANGUAGE plpgsql $preflight$
DECLARE
    v_required TEXT;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '038') THEN
        RAISE EXCEPTION '039 requiere la migracion 038';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '039') THEN
        RAISE EXCEPTION 'La migracion 039 ya fue aplicada';
    END IF;

    FOREACH v_required IN ARRAY ARRAY[
        'usuario','catalogo_operativo','nucleo_agrario','proyecto_nucleo','persona',
        'parcela','parcela_titular','actividad_campo','afectacion','unidad_agraria',
        'unidad_agraria_titular','afectacion_unidad_agraria','convenio','convenio_afectacion',
        'tramite_ran','tramite_ran_evento','tramite_fifonafe','tramite_fifonafe_evento',
        'indemnizacion','pago','documento','documento_vinculo','requisito_documental',
        'expediente_requisito','schema_migrations'
    ] LOOP
        IF to_regclass('public.' || v_required) IS NULL THEN
            RAISE EXCEPTION '039 requiere la tabla %', v_required;
        END IF;
    END LOOP;

    IF to_regclass('public.convenio_compareciente') IS NOT NULL THEN
        RAISE EXCEPTION '039 encontro convenio_compareciente preexistente; revisar estado antes de continuar';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM usuario WHERE activo) THEN
        RAISE EXCEPTION '039 requiere al menos un usuario activo para auditar';
    END IF;
END;
$preflight$;

SELECT set_config(
    'app.current_user_id',
    (SELECT min(id_usuario)::TEXT FROM usuario WHERE activo),
    TRUE
);

-- NO. PARCELA y NO. PARCELA PPT son el mismo dato funcional. Se reconcilian
-- antes de retirar la columna para no silenciar diferencias de origen.
DO LANGUAGE plpgsql $parcela_preflight$
BEGIN
    IF EXISTS (
        SELECT 1 FROM parcela
        WHERE NULLIF(regexp_replace(btrim(no_parcela), '\\s+', ' ', 'g'), '') IS NOT NULL
          AND NULLIF(regexp_replace(btrim(no_parcela_ppt), '\\s+', ' ', 'g'), '') IS NOT NULL
          AND lower(regexp_replace(btrim(no_parcela), '\\s+', ' ', 'g'))
              IS DISTINCT FROM lower(regexp_replace(btrim(no_parcela_ppt), '\\s+', ' ', 'g'))
    ) THEN
        RAISE EXCEPTION '039 bloqueada: no_parcela y no_parcela_ppt contienen valores materialmente distintos';
    END IF;
END;
$parcela_preflight$;

UPDATE parcela
SET no_parcela = NULLIF(regexp_replace(btrim(no_parcela_ppt), '\\s+', ' ', 'g'), '')
WHERE NULLIF(regexp_replace(btrim(no_parcela), '\\s+', ' ', 'g'), '') IS NULL
  AND NULLIF(regexp_replace(btrim(no_parcela_ppt), '\\s+', ' ', 'g'), '') IS NOT NULL;
UPDATE parcela SET no_parcela = NULLIF(regexp_replace(btrim(no_parcela), '\\s+', ' ', 'g'), '');

DO LANGUAGE plpgsql $parcela_duplicados$
BEGIN
    IF EXISTS (
        SELECT 1 FROM parcela WHERE no_parcela IS NOT NULL
        GROUP BY id_nucleo, lower(regexp_replace(no_parcela, '\\s+', ' ', 'g'))
        HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION '039 bloqueada: la reconciliacion de no_parcela produce duplicados normalizados por nucleo';
    END IF;
END;
$parcela_duplicados$;

ALTER TABLE parcela DROP CONSTRAINT IF EXISTS uq_parcela_ppt;
ALTER TABLE parcela DROP CONSTRAINT IF EXISTS uq_parcela_numero;
DROP INDEX IF EXISTS uq_parcela_ppt;
DROP INDEX IF EXISTS uq_parcela_numero;
ALTER TABLE parcela DROP COLUMN no_parcela_ppt;
CREATE UNIQUE INDEX uq_039_parcela_numero_normalizado
    ON parcela (id_nucleo, lower(regexp_replace(btrim(no_parcela), '\\s+', ' ', 'g')))
    WHERE activo AND no_parcela IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 1. Catalogos individuales.
-- ---------------------------------------------------------------------------

INSERT INTO catalogo_operativo
    (tipo_catalogo, codigo, nombre, descripcion, orden, fuente)
VALUES
    ('calidad_compareciente_convenio','titular_parcelario','Titular parcelario',
     'Persona que comparece como titular acreditado de derechos sobre la parcela.',10,
     'Ley Agraria arts. 76-79 / RLA-MOPR arts. 56-58'),
    ('calidad_compareciente_convenio','cotitular','Cotitular',
     'Persona que comparece como cotitular o coparticipe acreditado.',20,
     'Modelo individual / evidencia registral'),
    ('calidad_compareciente_convenio','sucesor_acreditado','Sucesor acreditado',
     'Persona que acredita sucesion o transmision de derechos mediante documento competente.',30,
     'RAN/FIFONAFE'),
    ('calidad_compareciente_convenio','beneficiario','Beneficiario',
     'Beneficiario del pago; no implica por si mismo titularidad parcelaria ni facultad para firmar el COP.',40,
     'FIFONAFE'),
    ('calidad_compareciente_convenio','representante','Representante',
     'Persona que comparece mediante representacion acreditada; no sustituye la acreditacion del derecho.',50,
     'Modelo juridico'),
    ('calidad_compareciente_convenio','otro','Otro',NULL,999,'Modelo operativo'),

    ('tipo_acreditacion_derecho_individual','certificado_derechos_agrarios','Certificado de derechos agrarios',NULL,10,
     'Ley Agraria art. 78 / PA / FIFONAFE'),
    ('tipo_acreditacion_derecho_individual','certificado_parcelario','Certificado parcelario',NULL,20,
     'Ley Agraria art. 78 / PA / FIFONAFE'),
    ('tipo_acreditacion_derecho_individual','resolucion_tribunal_agrario','Resolucion o sentencia de Tribunal Agrario',NULL,30,
     'Ley Agraria art. 78 / PA / FIFONAFE'),
    ('tipo_acreditacion_derecho_individual','constancia_ran_vigente','Constancia RAN de vigencia de derechos',NULL,40,
     'RAN-04-051 / PA / FIFONAFE'),
    ('tipo_acreditacion_derecho_individual','traslado_derechos','Traslado/transmision de derechos acreditado',NULL,50,
     'RAN/FIFONAFE'),
    ('tipo_acreditacion_derecho_individual','otra','Otra acreditacion',NULL,999,'Modelo operativo'),

    ('tipo_evento_fifonafe','solicitud_retiro_individual','Solicitud de retiro de fondos de uso individual',
     'Solicitud suscrita por titular o beneficiario para retiro individual.',5,'FIFONAFE'),
    ('tipo_evento_fifonafe','acuse_retiro_individual','Acuse de expediente de retiro individual',
     'Recepcion/acuse del expediente individual ante FIFONAFE.',6,'FIFONAFE'),
    ('tipo_evento_fifonafe','resolucion_retiro_individual','Resolucion del retiro individual',
     'Resolucion administrativa del tramite de retiro individual.',45,'FIFONAFE')
ON CONFLICT (tipo_catalogo, codigo) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. Actividades individuales: el mismo ProyectoNucleo puede tener cientos de
--    parcelas/afectaciones. La actividad puede quedar ligada a una afectacion.
-- ---------------------------------------------------------------------------

ALTER TABLE actividad_campo
    ADD COLUMN id_afectacion INTEGER REFERENCES afectacion(id_afectacion);

CREATE INDEX idx_039_actividad_afectacion
    ON actividad_campo (id_afectacion, fecha_realizada DESC, id_actividad DESC)
    WHERE activo AND id_afectacion IS NOT NULL;

DROP INDEX IF EXISTS uq_036_actividad_hecho;
CREATE UNIQUE INDEX uq_039_actividad_hecho
    ON actividad_campo (
        id_proyecto_nucleo,
        COALESCE(id_afectacion, 0),
        tipo_actividad,
        contexto_actividad,
        COALESCE(fecha_programada, DATE 'infinity'),
        COALESCE(fecha_realizada, DATE 'infinity'),
        COALESCE(btrim(responsable), ''),
        md5(COALESCE(resultado, ''))
    )
    WHERE activo;

CREATE OR REPLACE FUNCTION fn_039_validar_actividad_afectacion()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
DECLARE
    v_pn INTEGER;
BEGIN
    IF NEW.id_afectacion IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT id_proyecto_nucleo
      INTO v_pn
      FROM afectacion
     WHERE id_afectacion = NEW.id_afectacion
       AND activo;

    IF v_pn IS NULL THEN
        RAISE EXCEPTION '039: la afectacion de la actividad no existe o esta inactiva';
    END IF;
    IF v_pn IS DISTINCT FROM NEW.id_proyecto_nucleo THEN
        RAISE EXCEPTION '039: actividad y afectacion deben pertenecer al mismo ProyectoNucleo';
    END IF;
    RETURN NEW;
END;
$fn$;

CREATE TRIGGER trg_039_actividad_afectacion
BEFORE INSERT OR UPDATE OF id_proyecto_nucleo,id_afectacion,activo
ON actividad_campo
FOR EACH ROW EXECUTE FUNCTION fn_039_validar_actividad_afectacion();

COMMENT ON COLUMN actividad_campo.id_afectacion IS
'Contexto opcional de una actividad individual. NULL conserva actividades de alcance ProyectoNucleo; evita duplicar ActividadCampo por cada tipo de flujo.';

-- ---------------------------------------------------------------------------
-- 3. Linaje de convenios individuales.
--    Cada original/modificatorio/ampliacion/remanente es una fila de Convenio;
--    no se crean columnas repetidas _2/_3 como en una hoja Excel.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_039_validar_linaje_convenio_individual()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
DECLARE
    v_padre convenio%ROWTYPE;
    v_cycle BOOLEAN := FALSE;
BEGIN
    IF NOT NEW.activo OR NEW.ambito IS DISTINCT FROM 'individual' THEN
        RETURN NEW;
    END IF;

    -- En tierras parceladas el consentimiento/comparecencia es individual;
    -- no se usa asamblea como autorizacion del instrumento individual.
    IF NEW.id_asamblea_autorizacion IS NOT NULL THEN
        RAISE EXCEPTION '039: convenio individual no debe usar Asamblea como autorizacion';
    END IF;

    IF NEW.tipo_instrumento = 'convenio' THEN
        IF NEW.tipo_convenio NOT IN ('cop_original','modificatorio','ampliacion','ampliacion_remanente') THEN
            RAISE EXCEPTION '039: tipo de convenio % no corresponde al flujo individual', NEW.tipo_convenio;
        END IF;

        IF NEW.tipo_convenio = 'cop_original' AND NEW.id_convenio_padre IS NOT NULL THEN
            RAISE EXCEPTION '039: cop_original individual no debe tener convenio padre';
        END IF;

        IF NEW.tipo_convenio IN ('modificatorio','ampliacion','ampliacion_remanente')
           AND NEW.id_convenio_padre IS NULL THEN
            RAISE EXCEPTION '039: % individual requiere convenio padre', NEW.tipo_convenio;
        END IF;

        IF NEW.id_convenio_padre IS NOT NULL THEN
            IF NEW.id_convenio IS NOT NULL AND NEW.id_convenio_padre = NEW.id_convenio THEN
                RAISE EXCEPTION '039: un convenio no puede ser su propio padre';
            END IF;

            SELECT * INTO v_padre
              FROM convenio
             WHERE id_convenio = NEW.id_convenio_padre
               AND activo;

            IF NOT FOUND THEN
                RAISE EXCEPTION '039: convenio padre inexistente o inactivo';
            END IF;
            IF v_padre.id_proyecto_nucleo IS DISTINCT FROM NEW.id_proyecto_nucleo
               OR v_padre.ambito IS DISTINCT FROM 'individual'
               OR v_padre.tipo_instrumento IS DISTINCT FROM 'convenio' THEN
                RAISE EXCEPTION '039: convenio padre debe compartir ProyectoNucleo, ambito individual y ser un convenio';
            END IF;

            -- La fuente identifica ampliacion y remanente como instrumentos del mismo
            -- expediente/parcelario, pero no establece una regla juridica fiable sobre
            -- el TIPO del padre directo. No se inventa esa restriccion.

            IF NEW.id_convenio IS NOT NULL THEN
                WITH RECURSIVE ancestros AS (
                    SELECT c.id_convenio, c.id_convenio_padre
                      FROM convenio c
                     WHERE c.id_convenio = NEW.id_convenio_padre
                    UNION ALL
                    SELECT p.id_convenio, p.id_convenio_padre
                      FROM convenio p
                      JOIN ancestros a ON p.id_convenio = a.id_convenio_padre
                     WHERE p.id_convenio_padre IS NOT NULL
                )
                SELECT EXISTS(
                    SELECT 1 FROM ancestros WHERE id_convenio = NEW.id_convenio
                ) INTO v_cycle;

                IF v_cycle THEN
                    RAISE EXCEPTION '039: el linaje de convenio no puede contener ciclos';
                END IF;
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$fn$;

CREATE TRIGGER trg_039_linaje_convenio_individual
BEFORE INSERT OR UPDATE OF id_proyecto_nucleo,ambito,tipo_instrumento,tipo_convenio,
    id_convenio_padre,id_asamblea_autorizacion,activo
ON convenio
FOR EACH ROW EXECUTE FUNCTION fn_039_validar_linaje_convenio_individual();

COMMENT ON COLUMN convenio.id_convenio_padre IS
'Linaje juridico/operativo. En individual 039: original sin padre; modificatorio/ampliacion/remanente como instrumentos hijos. No equivale a TIPO COP operativo de Afectacion.';

-- El Excel individual agrupa original/modificatorio/ampliacion/remanente en la
-- misma fila parcelaria. Para no enlazar por error instrumentos de parcelas
-- distintas del mismo ProyectoNucleo, un hijo debe compartir al menos una
-- UnidadAgraria canonica con su padre. Se valida diferido porque los vinculos
-- ConvenioAfectacion se crean dentro de la misma transaccion que el Convenio.
CREATE OR REPLACE FUNCTION fn_039_validar_linaje_unidad_individual()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
DECLARE
    v_id_convenio INTEGER;
    v_padre INTEGER;
    v_ambito VARCHAR(20);
    v_activo BOOLEAN;
BEGIN
    v_id_convenio := NEW.id_convenio;

    SELECT id_convenio_padre, ambito, activo
      INTO v_padre, v_ambito, v_activo
      FROM convenio
     WHERE id_convenio = v_id_convenio;

    IF NOT COALESCE(v_activo,FALSE)
       OR v_ambito IS DISTINCT FROM 'individual'
       OR v_padre IS NULL THEN
        RETURN NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM convenio_afectacion ca_hijo
          JOIN afectacion_unidad_agraria au_hijo
            ON au_hijo.id_afectacion = ca_hijo.id_afectacion
           AND au_hijo.activo
          JOIN convenio_afectacion ca_padre
            ON ca_padre.id_convenio = v_padre
           AND ca_padre.activo
          JOIN afectacion_unidad_agraria au_padre
            ON au_padre.id_afectacion = ca_padre.id_afectacion
           AND au_padre.id_unidad_agraria = au_hijo.id_unidad_agraria
           AND au_padre.activo
         WHERE ca_hijo.id_convenio = v_id_convenio
           AND ca_hijo.activo
    ) THEN
        RAISE EXCEPTION '039: convenio individual hijo debe compartir al menos una UnidadAgraria con su convenio padre';
    END IF;

    RETURN NULL;
END;
$fn$;

CREATE CONSTRAINT TRIGGER trg_039_linaje_unidad_convenio
AFTER INSERT OR UPDATE ON convenio
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION fn_039_validar_linaje_unidad_individual();

CREATE CONSTRAINT TRIGGER trg_039_linaje_unidad_vinculo
AFTER INSERT OR UPDATE ON convenio_afectacion
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION fn_039_validar_linaje_unidad_individual();

-- ---------------------------------------------------------------------------
-- 4. Comparecientes/firmantes del convenio individual.
--    ParcelaTitular describe titularidad estable/historica; esta tabla conserva
--    quien comparecio y con que evidencia en ESE instrumento.
-- ---------------------------------------------------------------------------

CREATE TABLE convenio_compareciente (
    id_compareciente BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_convenio INTEGER NOT NULL REFERENCES convenio(id_convenio),
    id_persona INTEGER NOT NULL REFERENCES persona(id_persona),
    id_parcela_titular INTEGER REFERENCES parcela_titular(id_parcela_titular),
    id_tipo_calidad BIGINT NOT NULL REFERENCES catalogo_operativo(id_catalogo_opcion),
    id_tipo_acreditacion BIGINT REFERENCES catalogo_operativo(id_catalogo_opcion),
    referencia_acreditacion VARCHAR(200),
    fecha_acreditacion DATE,
    nombre_en_instrumento VARCHAR(300) NOT NULL,
    es_firmante BOOLEAN NOT NULL DEFAULT TRUE,
    es_beneficiario_pago BOOLEAN NOT NULL DEFAULT FALSE,
    requiere_revision BOOLEAN NOT NULL DEFAULT FALSE,
    motivo_revision TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por INTEGER REFERENCES usuario(id_usuario),
    actualizado_en TIMESTAMPTZ,
    actualizado_por INTEGER REFERENCES usuario(id_usuario),
    fecha_baja TIMESTAMPTZ,
    id_usuario_baja INTEGER REFERENCES usuario(id_usuario),
    motivo_baja TEXT,
    observaciones TEXT,
    CONSTRAINT chk_039_compareciente_nombre CHECK (
        NULLIF(btrim(nombre_en_instrumento), '') IS NOT NULL
    ),
    CONSTRAINT chk_039_compareciente_revision CHECK (
        NOT requiere_revision OR NULLIF(btrim(motivo_revision), '') IS NOT NULL
    ),
    CONSTRAINT chk_039_compareciente_baja CHECK (
        (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
        OR
        (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL
         AND NULLIF(btrim(motivo_baja), '') IS NOT NULL)
    )
);

CREATE UNIQUE INDEX uq_039_compareciente_activo
    ON convenio_compareciente (
        id_convenio,
        id_persona,
        COALESCE(id_parcela_titular,0),
        id_tipo_calidad
    )
    WHERE activo;

CREATE INDEX idx_039_compareciente_convenio
    ON convenio_compareciente (id_convenio, es_firmante DESC, id_compareciente)
    WHERE activo;
CREATE INDEX idx_039_compareciente_persona
    ON convenio_compareciente (id_persona, id_convenio)
    WHERE activo;

CREATE OR REPLACE FUNCTION fn_039_validar_compareciente()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
DECLARE
    v_ambito VARCHAR(20);
    v_pn INTEGER;
    v_nucleo INTEGER;
    v_persona_titular INTEGER;
    v_nucleo_parcela INTEGER;
    v_titular_inicio DATE;
    v_titular_fin DATE;
    v_fecha_firma DATE;
BEGIN
    IF NOT NEW.activo THEN
        RETURN NEW;
    END IF;

    SELECT c.ambito, c.id_proyecto_nucleo, pn.id_nucleo, c.fecha_firma
      INTO v_ambito, v_pn, v_nucleo, v_fecha_firma
      FROM convenio c
      JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = c.id_proyecto_nucleo
     WHERE c.id_convenio = NEW.id_convenio
       AND c.activo
       AND pn.activo;

    IF v_pn IS NULL THEN
        RAISE EXCEPTION '039: convenio del compareciente inexistente o inactivo';
    END IF;
    IF v_ambito IS DISTINCT FROM 'individual' THEN
        RAISE EXCEPTION '039: convenio_compareciente queda reservado al ambito individual en esta migracion';
    END IF;

    IF NOT fn_036_opcion_catalogo_valida(NEW.id_tipo_calidad,'calidad_compareciente_convenio') THEN
        RAISE EXCEPTION '039: calidad de compareciente invalida';
    END IF;
    IF NEW.id_tipo_acreditacion IS NOT NULL
       AND NOT fn_036_opcion_catalogo_valida(NEW.id_tipo_acreditacion,'tipo_acreditacion_derecho_individual') THEN
        RAISE EXCEPTION '039: tipo de acreditacion individual invalido';
    END IF;

    IF NEW.id_parcela_titular IS NOT NULL THEN
        SELECT pt.id_persona, p.id_nucleo, pt.fecha_inicio, pt.fecha_fin
          INTO v_persona_titular, v_nucleo_parcela, v_titular_inicio, v_titular_fin
          FROM parcela_titular pt
          JOIN parcela p ON p.id_parcela = pt.id_parcela
         WHERE pt.id_parcela_titular = NEW.id_parcela_titular
           AND pt.activo
           AND p.activo;

        IF v_persona_titular IS NULL THEN
            RAISE EXCEPTION '039: ParcelaTitular del compareciente inexistente o inactivo';
        END IF;
        IF v_persona_titular IS DISTINCT FROM NEW.id_persona THEN
            RAISE EXCEPTION '039: ParcelaTitular no pertenece a la persona compareciente';
        END IF;
        IF v_nucleo_parcela IS DISTINCT FROM v_nucleo THEN
            RAISE EXCEPTION '039: la parcela del compareciente no pertenece al NucleoAgrario del ProyectoNucleo';
        END IF;
        IF v_fecha_firma IS NOT NULL
           AND v_titular_inicio IS NOT NULL
           AND v_fecha_firma < v_titular_inicio THEN
            RAISE EXCEPTION '039: la titularidad inicia despues de la fecha de firma del convenio';
        END IF;
        IF v_fecha_firma IS NOT NULL
           AND v_titular_fin IS NOT NULL
           AND v_fecha_firma > v_titular_fin THEN
            RAISE EXCEPTION '039: la titularidad termino antes de la fecha de firma del convenio';
        END IF;
    END IF;

    -- Para firmar un convenio individual debe existir un vínculo de titularidad
    -- o una acreditacion alternativa explicitamente registrada. No se infiere.
    IF NEW.es_firmante
       AND NEW.id_parcela_titular IS NULL
       AND NEW.id_tipo_acreditacion IS NULL THEN
        RAISE EXCEPTION '039: firmante individual requiere ParcelaTitular o acreditacion alternativa';
    END IF;
    IF NEW.es_firmante
       AND NEW.id_parcela_titular IS NULL
       AND NEW.id_tipo_acreditacion IS NOT NULL
       AND NULLIF(btrim(NEW.referencia_acreditacion), '') IS NULL
       AND NOT NEW.requiere_revision THEN
        RAISE EXCEPTION '039: acreditacion alternativa sin referencia debe quedar explicitamente en revision';
    END IF;

    RETURN NEW;
END;
$fn$;

CREATE TRIGGER trg_039_validar_compareciente
BEFORE INSERT OR UPDATE OF id_convenio,id_persona,id_parcela_titular,
    id_tipo_calidad,id_tipo_acreditacion,referencia_acreditacion,fecha_acreditacion,
    es_firmante,requiere_revision,activo
ON convenio_compareciente
FOR EACH ROW EXECUTE FUNCTION fn_039_validar_compareciente();

CREATE OR REPLACE FUNCTION fn_039_validar_convenio_compareciente_unidad()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
BEGIN
    IF NEW.activo AND NEW.id_parcela_titular IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM convenio_afectacion ca
        JOIN afectacion a ON a.id_afectacion = ca.id_afectacion AND a.activo
        JOIN afectacion_unidad_agraria aua ON aua.id_afectacion = a.id_afectacion AND aua.activo
        JOIN unidad_agraria ua ON ua.id_unidad_agraria = aua.id_unidad_agraria AND ua.activo
        JOIN parcela_titular pt ON pt.id_parcela_titular = NEW.id_parcela_titular AND pt.activo
        WHERE ca.id_convenio = NEW.id_convenio
          AND ca.activo
          AND ua.id_parcela = pt.id_parcela
    ) THEN
        RAISE EXCEPTION '039: ParcelaTitular no corresponde a una UnidadAgraria afectada por el convenio';
    END IF;
    RETURN NULL;
END;
$fn$;

CREATE CONSTRAINT TRIGGER trg_039_compareciente_unidad
AFTER INSERT OR UPDATE ON convenio_compareciente
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION fn_039_validar_convenio_compareciente_unidad();

CREATE OR REPLACE FUNCTION fn_039_compareciente_identidad_inmutable()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
BEGIN
    IF OLD.id_convenio IS DISTINCT FROM NEW.id_convenio
       OR OLD.id_persona IS DISTINCT FROM NEW.id_persona
       OR OLD.id_parcela_titular IS DISTINCT FROM NEW.id_parcela_titular THEN
        RAISE EXCEPTION '039: identidad del compareciente inmutable; cree un nuevo registro y de baja logica al anterior';
    END IF;
    RETURN NEW;
END;
$fn$;

CREATE TRIGGER trg_039_compareciente_identidad_inmutable
BEFORE UPDATE OF id_convenio,id_persona,id_parcela_titular
ON convenio_compareciente
FOR EACH ROW EXECUTE FUNCTION fn_039_compareciente_identidad_inmutable();

-- Una firma individual nueva no puede quedar sin afectacion individual ni firmante.
-- Es diferido para permitir que Convenio, ConvenioAfectacion y Compareciente se creen
-- en la misma transaccion.
CREATE OR REPLACE FUNCTION fn_039_validar_convenio_individual_firmado()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
DECLARE
    v_id_convenio INTEGER;
    v_ambito VARCHAR(20);
    v_fecha_firma DATE;
    v_activo BOOLEAN;
BEGIN
    IF TG_TABLE_NAME = 'convenio' THEN
        v_id_convenio := NEW.id_convenio;
        IF TG_OP = 'UPDATE'
           AND OLD.fecha_firma IS NOT DISTINCT FROM NEW.fecha_firma
           AND OLD.ambito IS NOT DISTINCT FROM NEW.ambito
           AND OLD.activo IS NOT DISTINCT FROM NEW.activo THEN
            RETURN NULL;
        END IF;
    ELSE
        v_id_convenio := NEW.id_convenio;
    END IF;

    SELECT ambito, fecha_firma, activo
      INTO v_ambito, v_fecha_firma, v_activo
      FROM convenio
     WHERE id_convenio = v_id_convenio;

    IF NOT COALESCE(v_activo,FALSE)
       OR v_ambito IS DISTINCT FROM 'individual'
       OR v_fecha_firma IS NULL THEN
        RETURN NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM convenio_afectacion ca
          JOIN afectacion a ON a.id_afectacion = ca.id_afectacion
         WHERE ca.id_convenio = v_id_convenio
           AND ca.activo
           AND a.activo
           AND a.tipo_afectacion = 'individual'
    ) THEN
        RAISE EXCEPTION '039: convenio individual firmado requiere al menos una afectacion individual activa';
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM convenio_compareciente cc
         WHERE cc.id_convenio = v_id_convenio
           AND cc.activo
           AND cc.es_firmante
    ) THEN
        RAISE EXCEPTION '039: convenio individual firmado requiere al menos un firmante acreditado';
    END IF;

    RETURN NULL;
END;
$fn$;

CREATE CONSTRAINT TRIGGER trg_039_convenio_individual_firmado
AFTER INSERT OR UPDATE ON convenio
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION fn_039_validar_convenio_individual_firmado();

CREATE CONSTRAINT TRIGGER trg_039_compareciente_convenio_firmado
AFTER INSERT OR UPDATE ON convenio_compareciente
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION fn_039_validar_convenio_individual_firmado();

CREATE CONSTRAINT TRIGGER trg_039_convenio_afectacion_firmado
AFTER INSERT OR UPDATE ON convenio_afectacion
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION fn_039_validar_convenio_individual_firmado();

COMMENT ON TABLE convenio_compareciente IS
'Compareciente historico por instrumento individual. No sustituye Persona/ParcelaTitular: conserva quien firmo/comparecio y la evidencia usada en ese convenio.';
COMMENT ON COLUMN convenio_compareciente.nombre_en_instrumento IS
'Instantanea textual del nombre tal como aparece en el instrumento; Persona sigue siendo la identidad canonica.';
COMMENT ON COLUMN convenio_compareciente.es_beneficiario_pago IS
'Rol de pago independiente de es_firmante; ser beneficiario no prueba por si mismo facultad para firmar.';

-- ---------------------------------------------------------------------------
-- 5. ExpedienteRequisito: objetivo concreto. Antes 036 solo permitia PN +
--    afectacion, insuficiente para repetir el mismo requisito por COP original,
--    ampliacion, TramiteRAN o FIFONAFE.
-- ---------------------------------------------------------------------------

ALTER TABLE expediente_requisito
    ADD COLUMN entidad_tipo VARCHAR(50),
    ADD COLUMN entidad_id BIGINT;

UPDATE expediente_requisito
SET entidad_tipo = CASE
        WHEN id_afectacion IS NOT NULL THEN 'afectacion'
        ELSE 'proyecto_nucleo'
    END,
    entidad_id = CASE
        WHEN id_afectacion IS NOT NULL THEN id_afectacion::BIGINT
        ELSE id_proyecto_nucleo::BIGINT
    END
WHERE entidad_tipo IS NULL OR entidad_id IS NULL;

ALTER TABLE expediente_requisito
    ALTER COLUMN entidad_tipo SET NOT NULL,
    ALTER COLUMN entidad_id SET NOT NULL,
    ADD CONSTRAINT chk_039_expediente_requisito_objetivo CHECK (
        entidad_tipo IN (
            'proyecto_nucleo','afectacion','parcela','parcela_titular',
            'unidad_agraria','unidad_agraria_titular','convenio','convenio_compareciente',
            'tramite_ran','tramite_ran_evento','tramite_fifonafe','tramite_fifonafe_evento',
            'indemnizacion','pago'
        )
    );

DROP INDEX IF EXISTS uq_expediente_requisito;
CREATE UNIQUE INDEX uq_039_expediente_requisito_objetivo
    ON expediente_requisito (
        id_proyecto_nucleo,
        id_requisito,
        entidad_tipo,
        entidad_id
    )
    WHERE activo;
CREATE INDEX idx_039_expediente_requisito_objetivo
    ON expediente_requisito (entidad_tipo,entidad_id,id_estado)
    WHERE activo;

CREATE OR REPLACE FUNCTION fn_039_objetivo_requisito_en_pn(
    p_tipo TEXT,
    p_id BIGINT,
    p_pn INTEGER
) RETURNS BOOLEAN LANGUAGE plpgsql STABLE AS $fn$
DECLARE
    v_ok BOOLEAN := FALSE;
BEGIN
    CASE p_tipo
        WHEN 'proyecto_nucleo' THEN
            SELECT EXISTS(
                SELECT 1 FROM proyecto_nucleo pn
                 WHERE pn.id_proyecto_nucleo=p_id AND pn.id_proyecto_nucleo=p_pn AND pn.activo
            ) INTO v_ok;
        WHEN 'afectacion' THEN
            SELECT EXISTS(
                SELECT 1 FROM afectacion a
                 WHERE a.id_afectacion=p_id AND a.id_proyecto_nucleo=p_pn AND a.activo
            ) INTO v_ok;
        WHEN 'parcela' THEN
            SELECT EXISTS(
                SELECT 1 FROM parcela p
                JOIN proyecto_nucleo pn ON pn.id_nucleo=p.id_nucleo
                 WHERE p.id_parcela=p_id AND pn.id_proyecto_nucleo=p_pn AND p.activo AND pn.activo
            ) INTO v_ok;
        WHEN 'parcela_titular' THEN
            SELECT EXISTS(
                SELECT 1 FROM parcela_titular pt
                JOIN parcela p ON p.id_parcela=pt.id_parcela
                JOIN proyecto_nucleo pn ON pn.id_nucleo=p.id_nucleo
                 WHERE pt.id_parcela_titular=p_id AND pn.id_proyecto_nucleo=p_pn
                   AND pt.activo AND p.activo AND pn.activo
            ) INTO v_ok;
        WHEN 'unidad_agraria' THEN
            SELECT EXISTS(
                SELECT 1 FROM unidad_agraria u
                JOIN proyecto_nucleo pn ON pn.id_nucleo=u.id_nucleo
                 WHERE u.id_unidad_agraria=p_id AND pn.id_proyecto_nucleo=p_pn
                   AND u.activo AND pn.activo
            ) INTO v_ok;
        WHEN 'unidad_agraria_titular' THEN
            SELECT EXISTS(
                SELECT 1 FROM unidad_agraria_titular ut
                JOIN unidad_agraria u ON u.id_unidad_agraria=ut.id_unidad_agraria
                JOIN proyecto_nucleo pn ON pn.id_nucleo=u.id_nucleo
                 WHERE ut.id_unidad_titular=p_id AND pn.id_proyecto_nucleo=p_pn
                   AND ut.activo AND u.activo AND pn.activo
            ) INTO v_ok;
        WHEN 'convenio' THEN
            SELECT EXISTS(
                SELECT 1 FROM convenio c
                 WHERE c.id_convenio=p_id AND c.id_proyecto_nucleo=p_pn AND c.activo
            ) INTO v_ok;
        WHEN 'convenio_compareciente' THEN
            SELECT EXISTS(
                SELECT 1 FROM convenio_compareciente cc
                JOIN convenio c ON c.id_convenio=cc.id_convenio
                 WHERE cc.id_compareciente=p_id AND c.id_proyecto_nucleo=p_pn
                   AND cc.activo AND c.activo
            ) INTO v_ok;
        WHEN 'tramite_ran' THEN
            SELECT EXISTS(
                SELECT 1 FROM tramite_ran t
                 WHERE t.id_tramite_ran=p_id AND t.id_proyecto_nucleo=p_pn AND t.activo
            ) INTO v_ok;
        WHEN 'tramite_ran_evento' THEN
            SELECT EXISTS(
                SELECT 1 FROM tramite_ran_evento e
                JOIN tramite_ran t ON t.id_tramite_ran=e.id_tramite_ran
                 WHERE e.id_evento_ran=p_id AND t.id_proyecto_nucleo=p_pn
                   AND e.activo AND t.activo
            ) INTO v_ok;
        WHEN 'tramite_fifonafe' THEN
            SELECT EXISTS(
                SELECT 1 FROM tramite_fifonafe t
                 WHERE t.id_tramite_fifonafe=p_id AND t.id_proyecto_nucleo=p_pn AND t.activo
            ) INTO v_ok;
        WHEN 'tramite_fifonafe_evento' THEN
            SELECT EXISTS(
                SELECT 1 FROM tramite_fifonafe_evento e
                JOIN tramite_fifonafe t ON t.id_tramite_fifonafe=e.id_tramite_fifonafe
                 WHERE e.id_evento_fifonafe=p_id AND t.id_proyecto_nucleo=p_pn
                   AND e.activo AND t.activo
            ) INTO v_ok;
        WHEN 'indemnizacion' THEN
            SELECT EXISTS(
                SELECT 1 FROM indemnizacion i
                JOIN afectacion a ON a.id_afectacion=i.id_afectacion
                 WHERE i.id_indemnizacion=p_id AND a.id_proyecto_nucleo=p_pn
                   AND i.activo AND a.activo
            ) INTO v_ok;
        WHEN 'pago' THEN
            SELECT EXISTS(
                SELECT 1 FROM pago pg
                JOIN indemnizacion i ON i.id_indemnizacion=pg.id_indemnizacion
                JOIN afectacion a ON a.id_afectacion=i.id_afectacion
                 WHERE pg.id_pago=p_id AND a.id_proyecto_nucleo=p_pn
                   AND pg.activo AND i.activo AND a.activo
            ) INTO v_ok;
        ELSE
            v_ok := FALSE;
    END CASE;
    RETURN COALESCE(v_ok,FALSE);
END;
$fn$;

CREATE OR REPLACE FUNCTION fn_039_validar_expediente_requisito_objetivo()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
DECLARE
    v_afectacion_pn INTEGER;
BEGIN
    -- Compatibilidad con consumidores 036/038: si no mandan objetivo concreto,
    -- se deriva del contexto ya existente.
    IF NEW.entidad_tipo IS NULL OR NEW.entidad_id IS NULL THEN
        IF NEW.id_afectacion IS NOT NULL THEN
            NEW.entidad_tipo := 'afectacion';
            NEW.entidad_id := NEW.id_afectacion;
        ELSE
            NEW.entidad_tipo := 'proyecto_nucleo';
            NEW.entidad_id := NEW.id_proyecto_nucleo;
        END IF;
    END IF;

    IF NEW.id_afectacion IS NOT NULL THEN
        SELECT id_proyecto_nucleo INTO v_afectacion_pn
          FROM afectacion
         WHERE id_afectacion=NEW.id_afectacion AND activo;
        IF v_afectacion_pn IS NULL OR v_afectacion_pn IS DISTINCT FROM NEW.id_proyecto_nucleo THEN
            RAISE EXCEPTION '039: id_afectacion del requisito no pertenece al ProyectoNucleo';
        END IF;
    END IF;

    IF NOT fn_039_objetivo_requisito_en_pn(
        NEW.entidad_tipo, NEW.entidad_id, NEW.id_proyecto_nucleo
    ) THEN
        RAISE EXCEPTION '039: objetivo documental %:% no pertenece al ProyectoNucleo %',
            NEW.entidad_tipo, NEW.entidad_id, NEW.id_proyecto_nucleo;
    END IF;

    RETURN NEW;
END;
$fn$;

CREATE TRIGGER trg_039_expediente_requisito_objetivo
BEFORE INSERT OR UPDATE OF id_proyecto_nucleo,id_afectacion,entidad_tipo,entidad_id,activo
ON expediente_requisito
FOR EACH ROW EXECUTE FUNCTION fn_039_validar_expediente_requisito_objetivo();

COMMENT ON COLUMN expediente_requisito.entidad_tipo IS
'Objetivo concreto del requisito. Permite repetir un mismo requisito por convenio/tramite/evento sin duplicar la definicion del catalogo.';
COMMENT ON COLUMN expediente_requisito.entidad_id IS
'PK del objetivo controlado por entidad_tipo; su pertenencia al ProyectoNucleo se valida por trigger 039.';

-- ---------------------------------------------------------------------------
-- 6. DocumentoVinculo: habilitar evidencia directamente sobre titularidades.
--    No se agrega Persona para evitar que el expediente operacional se convierta
--    en repositorio general de PII; identificaciones pueden vincularse al
--    ExpedienteRequisito correspondiente.
-- ---------------------------------------------------------------------------

ALTER TABLE documento_vinculo DROP CONSTRAINT chk_documento_vinculo_tipo;
ALTER TABLE documento_vinculo ADD CONSTRAINT chk_documento_vinculo_tipo CHECK (entidad_tipo IN (
    'proyecto_nucleo','nucleo_agrario','orv','padron_historial','parcela','parcela_titular','afectacion',
    'bien_afectado','unidad_agraria','unidad_agraria_titular','afectacion_unidad_agraria',
    'asamblea','asamblea_convocatoria','convenio','convenio_compareciente','tramite_ran','tramite_ran_evento',
    'tramite_fifonafe','tramite_fifonafe_evento','indemnizacion','pago','expediente_requisito'
));

-- fn_objetivo_controlado_existe ya conoce parcela_titular y unidad_agraria_titular desde 037.

-- ---------------------------------------------------------------------------
-- 7. Catalogo de requisitos documentales individuales.
--    Se define el tipo de requisito; NO se crean ocurrencias ficticias para
--    expedientes existentes. La aplicabilidad se instancia por objetivo.
-- ---------------------------------------------------------------------------

INSERT INTO requisito_documental
    (codigo,nombre,descripcion,contexto,obligatorio,orden,fuente)
VALUES
    ('ind_derecho_acreditacion','Acreditacion del derecho individual',
     'Evidencia vigente del derecho sobre la parcela. Puede acreditarse con certificado de derechos agrarios/parcelario, resolucion del Tribunal Agrario o constancia RAN vigente, segun corresponda.',
     'individual_parcela',TRUE,10,'Ley Agraria art. 78 / PA / RAN'),
    ('ind_convenio_firmado','Convenio individual firmado',
     'Instrumento suscrito para la ocupacion previa individual; se instancia por cada COP original, modificatorio, ampliacion o remanente aplicable.',
     'individual_convenio',TRUE,20,'RLA-MOPR arts. 56-58 / PA'),
    ('ind_ran_acuse_ingreso','Acuse o evidencia de ingreso al RAN',
     'Evidencia documental del ingreso/reingreso del instrumento al Registro Agrario Nacional.',
     'individual_ran',TRUE,30,'RLA-MOPR art. 58 / flujo PA-RAN'),
    ('ind_ran_inscripcion','Aviso/constancia de inscripcion RAN',
     'Evidencia documental de la inscripcion del instrumento cuando el tramite haya concluido favorablemente.',
     'individual_ran',TRUE,40,'RAN / flujo operativo individual'),
    ('ind_fif_solicitud_retiro','Solicitud de retiro de fondos de uso individual',
     'Solicitud escrita de retiro de fondos de uso individual con origen, monto, destino y forma de pago.',
     'individual_fifonafe',TRUE,50,'FIFONAFE'),
    ('ind_fif_acreditacion_derecho','Acreditacion de derecho para FIFONAFE',
     'Certificado de derechos agrarios/parcelarios, resolucion competente o constancia RAN vigente a favor del beneficiario, segun corresponda.',
     'individual_fifonafe',TRUE,60,'FIFONAFE'),
    ('ind_fif_identificacion_oficial','Identificacion oficial vigente',
     'Identificacion oficial del solicitante/beneficiario para el tramite individual.',
     'individual_fifonafe',TRUE,70,'FIFONAFE'),
    ('ind_fif_curp','CURP del solicitante/beneficiario',
     'CURP requerida para el expediente individual FIFONAFE.',
     'individual_fifonafe',TRUE,80,'FIFONAFE'),
    ('ind_fif_cuenta_bancaria','Cuenta/CLABE para transferencia',
     'Contrato o version publica de estado de cuenta con institucion, titular, cuenta y CLABE; aplica cuando el pago sea por transferencia.',
     'individual_fifonafe',FALSE,90,'FIFONAFE'),
    ('ind_fif_sucesion','Resolucion o acreditacion de sucesion',
     'Documento competente cuando el solicitante actua como sucesor/beneficiario y resulte aplicable.',
     'individual_fifonafe',FALSE,100,'FIFONAFE/RAN/TUA'),
    ('ind_fif_parcela_sin_asignar','Acreditacion de asignacion de parcela previamente no asignada',
     'Resolucion competente o acta de asamblea inscrita en RAN que acredite la asignacion cuando el supuesto resulte aplicable.',
     'individual_fifonafe',FALSE,110,'FIFONAFE/RAN')
ON CONFLICT (codigo) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 8. Auditoria, no DELETE fisico y privilegios runtime.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_039_prevenir_delete_fisico()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
BEGIN
    RAISE EXCEPTION 'La tabla % no admite DELETE fisico; utilice baja logica', TG_TABLE_NAME;
END;
$fn$;

CREATE TRIGGER trg_039_compareciente_no_delete
BEFORE DELETE ON convenio_compareciente
FOR EACH ROW EXECUTE FUNCTION fn_039_prevenir_delete_fisico();

CREATE TRIGGER trg_audit_convenio_compareciente
AFTER INSERT OR UPDATE ON convenio_compareciente
FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_compareciente');

GRANT SELECT,INSERT,UPDATE ON convenio_compareciente TO software_pa_app;
DO LANGUAGE plpgsql $grant_sequence$
DECLARE
    v_seq TEXT;
BEGIN
    v_seq := pg_get_serial_sequence('public.convenio_compareciente','id_compareciente');
    IF v_seq IS NOT NULL THEN
        EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %s TO software_pa_app', v_seq);
    END IF;
END;
$grant_sequence$;

REVOKE DELETE,TRUNCATE,REFERENCES,TRIGGER
ON convenio_compareciente,actividad_campo,convenio,expediente_requisito,documento_vinculo
FROM software_pa_app;
REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON schema_migrations FROM software_pa_app;

-- ---------------------------------------------------------------------------
-- 9. Comentarios de compatibilidad/semantica.
-- ---------------------------------------------------------------------------

COMMENT ON COLUMN parcela.no_parcela IS
'Identificador canónico de parcela; 039 reconcilia y elimina no_parcela_ppt.';
COMMENT ON COLUMN parcela.certificado_parcelario IS
'Referencia del certificado disponible; la evidencia documental puede vincularse a Parcela/ParcelaTitular/ExpedienteRequisito.';
COMMENT ON COLUMN parcela.folio_derechos IS
'Referencia/folio de derechos proveniente de la fuente operativa; no sustituye la validacion registral.';
COMMENT ON COLUMN parcela.constancia_vigencia_fecha IS
'Fecha de la constancia de vigencia cuando la fuente contiene una fecha validada; textos mixtos de origen deben preservarse en trazabilidad, no forzarse a DATE.';
COMMENT ON TABLE tramite_ran_evento IS
'Eventos registrales normalizados. Una celda Excel con estatus textual sin fecha debe representarse en resultado/calificacion/folio y conservar su valor original en trazabilidad; no se convierte artificialmente a DATE.';

INSERT INTO schema_migrations(version, descripcion)
VALUES ('039', 'Modelo operativo individual: actividades por afectacion, linaje/comparecientes de convenio y expediente documental por objetivo');

COMMIT;
