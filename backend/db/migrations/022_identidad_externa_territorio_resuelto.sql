-- Usa el municipio resuelto como contexto estable de la identidad externa territorial.

BEGIN;

SELECT pg_advisory_xact_lock(20260814, 22);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '021') THEN
        RAISE EXCEPTION 'La migracion 022 requiere la migracion 021 aplicada';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '022') THEN
        RAISE EXCEPTION 'La migracion 022 ya fue aplicada';
    END IF;
    IF EXISTS (
        SELECT 1
          FROM nucleo_agrario
         WHERE activo = TRUE
           AND alcance_identidad_fuente = 'territorial'
           AND fuente_datos IS NOT NULL
           AND id_nucleo_fuente IS NOT NULL
         GROUP BY lower(fuente_datos), id_municipio, id_nucleo_fuente
        HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Existen identidades externas territoriales duplicadas; concilie los datos antes de aplicar 022';
    END IF;
END;
$$;

DROP INDEX uq_021_nucleo_identidad_fuente_territorial;

CREATE UNIQUE INDEX uq_022_nucleo_identidad_fuente_territorial
    ON nucleo_agrario (lower(fuente_datos), id_municipio, id_nucleo_fuente)
    WHERE activo = TRUE
      AND alcance_identidad_fuente = 'territorial'
      AND fuente_datos IS NOT NULL
      AND id_nucleo_fuente IS NOT NULL;

INSERT INTO schema_migrations (version, descripcion)
VALUES ('022', 'Identidad externa territorial basada en municipio resuelto');

COMMIT;
