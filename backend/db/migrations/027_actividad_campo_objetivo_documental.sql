-- B-04: actividad_campo como objetivo del vínculo documental genérico.
-- Forward-only: conserva los 22 tipos de 026 y no modifica datos ni requisitos.
SET search_path = public, pg_catalog;

SELECT pg_advisory_xact_lock(
    hashtextextended('software-pa:027:actividad-campo-objetivo-documental', 0)
);

DO $$
DECLARE
    v_definicion text;
    v_tipos text[];
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations
        WHERE version = '026' AND nombre = 'historia_cambios_gis'
          AND checksum_sha256 = '6615a137655abbb2a6ea2620d7c8b5013f07d6fcdd81aae4270a4551904ea3fd'
    ) THEN
        RAISE EXCEPTION '027 requiere 026 canónica exacta';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '027') THEN
        RAISE EXCEPTION '027 ya se encuentra registrada';
    END IF;

    SELECT pg_get_constraintdef(oid) INTO v_definicion
    FROM pg_constraint
    WHERE conrelid = 'documento_vinculo'::regclass
      AND conname = 'chk_documento_vinculo_tipo'
      AND contype = 'c' AND convalidated;
    SELECT array_agg(m[1] ORDER BY m[1]) INTO v_tipos
    FROM regexp_matches(v_definicion, '''([a-z_]+)''', 'g') AS m;
    IF v_tipos IS DISTINCT FROM ARRAY(
        SELECT unnest(ARRAY[
            'proyecto_nucleo','nucleo_agrario','orv','padron_historial','parcela',
            'parcela_titular','afectacion','unidad_agraria','unidad_agraria_titular',
            'afectacion_unidad_agraria','asamblea','asamblea_convocatoria',
            'convenio','convenio_compareciente','tramite_ran','tramite_ran_evento',
            'tramite_fifonafe','tramite_fifonafe_evento','tramite_fifonafe_interviniente',
            'indemnizacion','pago','expediente_requisito'
        ]::text[]) ORDER BY 1
    ) THEN
        RAISE EXCEPTION 'chk_documento_vinculo_tipo no corresponde a los 22 tipos canónicos de 026';
    END IF;
END $$;

ALTER TABLE documento_vinculo DROP CONSTRAINT chk_documento_vinculo_tipo;
ALTER TABLE documento_vinculo ADD CONSTRAINT chk_documento_vinculo_tipo CHECK (
    entidad_tipo IN (
        'proyecto_nucleo','nucleo_agrario','orv','padron_historial','parcela',
        'parcela_titular','afectacion','unidad_agraria','unidad_agraria_titular',
        'afectacion_unidad_agraria','asamblea','asamblea_convocatoria',
        'convenio','convenio_compareciente','tramite_ran','tramite_ran_evento',
        'tramite_fifonafe','tramite_fifonafe_evento','tramite_fifonafe_interviniente',
        'indemnizacion','pago','expediente_requisito','actividad_campo'
    )
);
