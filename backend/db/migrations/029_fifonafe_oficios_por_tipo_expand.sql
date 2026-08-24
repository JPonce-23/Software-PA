-- Alinea los requisitos documentales de FIFONAFE con el tipo de tramite.
-- Fase EXPAND: agrega y valida la regla nueva sin retirar aun la legacy.

BEGIN;

SELECT pg_advisory_xact_lock(20260822, 29);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '028') THEN
        RAISE EXCEPTION 'La migracion 029 requiere la migracion 028 aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '029') THEN
        RAISE EXCEPTION 'La migracion 029 ya fue aplicada';
    END IF;
END;
$$;

ALTER TABLE tramite_fifonafe
    ADD CONSTRAINT chk_029_informe_completo_requiere_resultado_y_oficios
    CHECK (
        tipo_tramite <> 'informe_no_conflictos'
        OR estatus <> 'completo'
        OR (
            hay_conflictos IS NOT NULL
            AND no_oficio_fifonafe_a_dgaopr IS NOT NULL
            AND no_oficio_dgaopr_a_repr IS NOT NULL
            AND no_oficio_rpta_repr_a_dgaopr IS NOT NULL
            AND no_oficio_rpta_dgaopr_a_fifonafe IS NOT NULL
            AND fecha_oficio_fifonafe_a_dgaopr IS NOT NULL
            AND fecha_oficio_dgaopr_a_repr IS NOT NULL
            AND fecha_oficio_rpta_repr_a_dgaopr IS NOT NULL
            AND fecha_oficio_rpta_dgaopr_a_fifonafe IS NOT NULL
        )
    ) NOT VALID;

ALTER TABLE tramite_fifonafe
    VALIDATE CONSTRAINT chk_029_informe_completo_requiere_resultado_y_oficios;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('029', 'FIFONAFE: requisitos de resultado y oficios por tipo de tramite (expand)');

COMMIT;
