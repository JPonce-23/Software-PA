-- ============================================================
-- MIGRACION 018: Unicidad de nucleos agrarios activos
-- Fecha: 2026-08-13
--
-- Estrategia: EXPAND con precondicion de limpieza.
--   * Define normalizacion canonica para nombres de nucleo.
--   * Bloquea duplicados activos por municipio, tipo y nombre normalizado.
--   * No fusiona ni elimina datos existentes; si hay duplicados, aborta.
--
-- Requisitos:
--   * La migracion 017 debe estar aplicada.
--   * Ejecutar una sola vez con ON_ERROR_STOP habilitado.
-- ============================================================

BEGIN;

SELECT pg_advisory_xact_lock(20260813, 18);

CREATE OR REPLACE FUNCTION fn_018_normalizar_nombre_nucleo(value TEXT)
RETURNS TEXT AS $$
    SELECT regexp_replace(
        translate(lower(btrim(coalesce(value, ''))), 'áéíóúüñ', 'aeiouun'),
        '[^a-z0-9]+',
        '',
        'g'
    );
$$ LANGUAGE sql IMMUTABLE;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '017') THEN
        RAISE EXCEPTION 'La migracion 018 requiere que la migracion 017 este aplicada';
    END IF;

    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '018') THEN
        RAISE EXCEPTION 'La migracion 018 ya fue aplicada';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM nucleo_agrario
         WHERE activo = TRUE
         GROUP BY id_municipio, tipo_nucleo, fn_018_normalizar_nombre_nucleo(nombre_nucleo)
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Existen nucleos agrarios activos duplicados por municipio, tipo y nombre normalizado; se requiere conciliacion manual antes de aplicar 018';
    END IF;
END;
$$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_018_nucleo_activo_municipio_tipo_nombre
    ON nucleo_agrario (
        id_municipio,
        tipo_nucleo,
        fn_018_normalizar_nombre_nucleo(nombre_nucleo)
    )
    WHERE activo = TRUE;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('018', 'Unicidad de nucleos agrarios activos por municipio, tipo y nombre normalizado');

COMMIT;
