-- 035_completitud_seguimiento_operativo.sql
-- Campos aditivos confirmados por la auditoría física de las fuentes operativas.
-- No implementa bajas lógicas ni altera decisiones del dominio 031-034.

BEGIN;

SELECT pg_advisory_xact_lock(20260826, 35);

DO $preflight$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '034') THEN
        RAISE EXCEPTION '035 requiere la migración 034';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '035') THEN
        RAISE EXCEPTION 'La migración 035 ya fue aplicada';
    END IF;
END;
$preflight$;

ALTER TABLE asamblea
    ADD COLUMN contexto_proceso VARCHAR(40),
    ADD CONSTRAINT chk_asamblea_contexto_proceso CHECK (
        contexto_proceso IS NULL OR contexto_proceso IN (
            'cop_original',
            'modificatorio',
            'superficie_adicional',
            'obras_complementarias',
            'retiro_fondos',
            'otro'
        )
    );

COMMENT ON COLUMN asamblea.contexto_proceso IS
    'Proceso operativo que motiva la asamblea; no sustituye a tipo_asamblea.';

ALTER TABLE tramite_fifonafe
    ADD COLUMN acuse_fifonafe_fecha DATE;

COMMENT ON COLUMN tramite_fifonafe.acuse_fifonafe_fecha IS
    'Fecha del acuse FIFONAFE registrada por el seguimiento operativo.';

ALTER TABLE indemnizacion
    ADD COLUMN fecha_entrega_expediente_pa DATE;

COMMENT ON COLUMN indemnizacion.fecha_entrega_expediente_pa IS
    'Fecha de entrega del expediente SICT a la Procuraduría Agraria.';

ALTER TABLE documento
    ADD COLUMN fecha_documento DATE,
    ADD COLUMN numero_folio VARCHAR(150);

COMMENT ON COLUMN documento.fecha_documento IS
    'Fecha propia del documento o soporte, independiente de la fecha de carga.';
COMMENT ON COLUMN documento.numero_folio IS
    'Número de oficio, folio o referencia visible del documento.';

INSERT INTO schema_migrations (version, descripcion)
VALUES ('035', 'Completitud aditiva del seguimiento operativo y documental');

COMMIT;
