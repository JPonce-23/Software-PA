-- Fase SWITCH: la regla documental queda limitada al informe de no conflictos.
-- Los valores historicos de indemnizacion se conservan sin modificaciones.

BEGIN;

SELECT pg_advisory_xact_lock(20260822, 30);

DO $$
DECLARE
    v_invalidos INTEGER;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '029') THEN
        RAISE EXCEPTION 'La migracion 030 requiere la migracion 029 aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '030') THEN
        RAISE EXCEPTION 'La migracion 030 ya fue aplicada';
    END IF;

    SELECT COUNT(*)
      INTO v_invalidos
      FROM tramite_fifonafe
     WHERE tipo_tramite = 'informe_no_conflictos'
       AND estatus = 'completo'
       AND (
            hay_conflictos IS NULL
            OR no_oficio_fifonafe_a_dgaopr IS NULL
            OR no_oficio_dgaopr_a_repr IS NULL
            OR no_oficio_rpta_repr_a_dgaopr IS NULL
            OR no_oficio_rpta_dgaopr_a_fifonafe IS NULL
            OR fecha_oficio_fifonafe_a_dgaopr IS NULL
            OR fecha_oficio_dgaopr_a_repr IS NULL
            OR fecha_oficio_rpta_repr_a_dgaopr IS NULL
            OR fecha_oficio_rpta_dgaopr_a_fifonafe IS NULL
       );

    IF v_invalidos > 0 THEN
        RAISE EXCEPTION
            'PREFLIGHT FALLIDO: existen % informes completos sin resultado u oficios',
            v_invalidos;
    END IF;
END;
$$;

ALTER TABLE tramite_fifonafe
    DROP CONSTRAINT chk_estatus_completo_requiere_oficios;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('030', 'FIFONAFE: requisitos documentales por tipo de tramite (switch)');

COMMIT;
