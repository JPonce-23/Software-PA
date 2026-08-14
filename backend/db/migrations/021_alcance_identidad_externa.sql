-- Corrige el alcance de IDs externos que se reinician por territorio.

BEGIN;

SELECT pg_advisory_xact_lock(20260814, 21);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '020') THEN
        RAISE EXCEPTION 'La migracion 021 requiere la migracion 020 aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '021') THEN
        RAISE EXCEPTION 'La migracion 021 ya fue aplicada';
    END IF;
END;
$$;

ALTER TABLE nucleo_agrario
    ADD COLUMN alcance_identidad_fuente VARCHAR(20);

ALTER TABLE nucleo_agrario
    ADD CONSTRAINT chk_021_alcance_identidad_fuente CHECK (
        alcance_identidad_fuente IS NULL
        OR alcance_identidad_fuente IN ('global', 'territorial')
    );

DROP INDEX uq_020_nucleo_identidad_fuente_activa;

CREATE UNIQUE INDEX uq_021_nucleo_identidad_fuente_global
    ON nucleo_agrario (lower(fuente_datos), id_nucleo_fuente)
    WHERE activo = TRUE
      AND alcance_identidad_fuente = 'global'
      AND fuente_datos IS NOT NULL
      AND id_nucleo_fuente IS NOT NULL;

CREATE UNIQUE INDEX uq_021_nucleo_identidad_fuente_territorial
    ON nucleo_agrario (
        lower(fuente_datos),
        id_entidad_fuente,
        id_municipio_fuente,
        id_nucleo_fuente
    )
    WHERE activo = TRUE
      AND alcance_identidad_fuente = 'territorial'
      AND fuente_datos IS NOT NULL
      AND id_entidad_fuente IS NOT NULL
      AND id_municipio_fuente IS NOT NULL
      AND id_nucleo_fuente IS NOT NULL;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('021', 'Alcance explicito para identidad externa global o territorial');

COMMIT;
