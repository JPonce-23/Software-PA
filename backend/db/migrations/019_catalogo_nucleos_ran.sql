-- Formaliza nucleo_agrario como catalogo maestro nacional con identidad externa RAN.
-- No carga datos: la poblacion del catalogo se realiza mediante un importador reproducible.
SET search_path = public, pg_catalog;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM schema_migrations
         WHERE version = '018'
           AND checksum_sha256 = '2fb5676b52d902b636b3941490ea71a8044a791764b2913a18b6a905d9ddfea3'
    ) THEN
        RAISE EXCEPTION '019 requiere la migracion 018 exacta';
    END IF;

    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '019') THEN
        RAISE EXCEPTION '019 ya se encuentra registrada';
    END IF;
END $$;

SELECT pg_advisory_xact_lock(
    hashtextextended('software-pa:019:catalogo-nucleos-ran', 0)
);

LOCK TABLE nucleo_agrario IN SHARE ROW EXCLUSIVE MODE;

-- La identidad funcional de un nucleo no puede inferirse de
-- municipio + tenencia + nombre. El catalogo oficial RAN contiene claves
-- externas distintas para registros que comparten esos tres atributos.
DROP INDEX IF EXISTS uq_nucleo_activo_normalizado;

-- Se conserva la misma expresion como indice de busqueda, ya sin imponer
-- una regla de unicidad que el dato oficial no cumple.
CREATE INDEX idx_nucleo_activo_normalizado
ON nucleo_agrario (
    id_municipio,
    id_tipo_tenencia,
    lower(btrim(nombre_nucleo))
)
WHERE activo;

-- Antes de crear la identidad externa unica se rechaza cualquier estado
-- preexistente ambiguo. Los registros historicos/manuales sin
-- id_nucleo_fuente no participan en esta regla.
DO $$
DECLARE
    v_duplicados text;
BEGIN
    SELECT string_agg(
               fuente_normalizada || ':' || id_fuente_normalizado,
               ', '
               ORDER BY fuente_normalizada, id_fuente_normalizado
           )
      INTO v_duplicados
      FROM (
        SELECT
            lower(btrim(fuente_datos)) AS fuente_normalizada,
            btrim(id_nucleo_fuente) AS id_fuente_normalizado
          FROM nucleo_agrario
         WHERE NULLIF(btrim(fuente_datos), '') IS NOT NULL
           AND NULLIF(btrim(id_nucleo_fuente), '') IS NOT NULL
         GROUP BY
            lower(btrim(fuente_datos)),
            btrim(id_nucleo_fuente)
        HAVING count(*) > 1
      ) d;

    IF v_duplicados IS NOT NULL THEN
        RAISE EXCEPTION
            '019 abortada: identidades externas de nucleo duplicadas: %',
            v_duplicados;
    END IF;
END $$;

CREATE UNIQUE INDEX uq_nucleo_identidad_fuente
ON nucleo_agrario (
    lower(btrim(fuente_datos)),
    btrim(id_nucleo_fuente)
)
WHERE NULLIF(btrim(fuente_datos), '') IS NOT NULL
  AND NULLIF(btrim(id_nucleo_fuente), '') IS NOT NULL;

-- Para filas provenientes del catalogo nacional PHINA/RAN se exige conservar
-- la clave unica y los identificadores territoriales tal como los entrega la
-- fuente. La vinculacion con municipio.id_municipio se resuelve por el
-- importador y no sustituye estos valores de procedencia.
ALTER TABLE nucleo_agrario
    ADD CONSTRAINT chk_nucleo_ran_identidad_fuente
    CHECK (
        lower(btrim(COALESCE(fuente_datos, '')))
            <> 'ran_phina_catalogo_nucleos'
        OR (
            NULLIF(btrim(id_nucleo_fuente), '') IS NOT NULL
            AND NULLIF(btrim(id_entidad_fuente), '') IS NOT NULL
            AND NULLIF(btrim(id_municipio_fuente), '') IS NOT NULL
        )
    );

COMMENT ON COLUMN nucleo_agrario.id_nucleo IS
    'Identificador interno estable de SOFTWARE-PA; no se sustituye por claves de fuentes externas.';

COMMENT ON COLUMN nucleo_agrario.fuente_datos IS
    'Codigo estable de procedencia del dato maestro. Para el catalogo nacional PHINA/RAN se usa RAN_PHINA_CATALOGO_NUCLEOS.';

COMMENT ON COLUMN nucleo_agrario.id_nucleo_fuente IS
    'Identificador estable del nucleo en la fuente externa; para RAN corresponde a cve_unica.';

COMMENT ON COLUMN nucleo_agrario.id_entidad_fuente IS
    'Identificador de entidad entregado por la fuente externa, conservado para trazabilidad.';

COMMENT ON COLUMN nucleo_agrario.id_municipio_fuente IS
    'Identificador de municipio entregado por la fuente externa, conservado para trazabilidad.';

COMMENT ON INDEX idx_nucleo_activo_normalizado IS
    'Indice de busqueda por municipio, tenencia y nombre normalizado; deliberadamente no es UNIQUE.';

COMMENT ON INDEX uq_nucleo_identidad_fuente IS
    'Identidad externa estable del nucleo por fuente + id_nucleo_fuente, independiente de su estado activo.';

DO $$
BEGIN
    IF to_regclass('public.uq_nucleo_activo_normalizado') IS NOT NULL THEN
        RAISE EXCEPTION
            '019 postcondicion: persiste la unicidad historica por municipio/tenencia/nombre';
    END IF;

    IF to_regclass('public.idx_nucleo_activo_normalizado') IS NULL
       OR to_regclass('public.uq_nucleo_identidad_fuente') IS NULL THEN
        RAISE EXCEPTION
            '019 postcondicion: faltan indices esperados de nucleo_agrario';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM nucleo_agrario
         WHERE lower(btrim(COALESCE(fuente_datos, '')))
                   = 'ran_phina_catalogo_nucleos'
           AND (
                NULLIF(btrim(id_nucleo_fuente), '') IS NULL
                OR NULLIF(btrim(id_entidad_fuente), '') IS NULL
                OR NULLIF(btrim(id_municipio_fuente), '') IS NULL
           )
    ) THEN
        RAISE EXCEPTION
            '019 postcondicion: existen filas RAN sin identidad de fuente completa';
    END IF;
END $$;
