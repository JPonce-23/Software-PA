\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_municipio integer;
    v_tenencia bigint;
    v_actor integer;
    v_duplicado_rechazado boolean := false;
    v_ran_incompleto_rechazado boolean := false;
BEGIN
    IF current_database() <> 'software_pa_test' THEN
        RAISE EXCEPTION '019 contract sólo puede ejecutarse en software_pa_test';
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM schema_migrations
         WHERE version = '019'
           AND nombre = 'catalogo_nucleos_ran'
    ) THEN
        RAISE EXCEPTION '019 no está aplicada';
    END IF;

    SELECT id_municipio
      INTO v_municipio
      FROM municipio
     WHERE activo
     ORDER BY id_municipio
     LIMIT 1;

    SELECT id_catalogo_opcion
      INTO v_tenencia
      FROM catalogo_operativo
     WHERE tipo_catalogo = 'tipo_tenencia'
       AND codigo = 'ejido'
       AND activo;

    SELECT id_usuario
      INTO v_actor
      FROM usuario
     WHERE activo
     ORDER BY id_usuario
     LIMIT 1;

    IF v_municipio IS NULL OR v_tenencia IS NULL OR v_actor IS NULL THEN
        RAISE EXCEPTION 'Faltan fixtures territoriales, tenencia o usuario actor';
    END IF;
    PERFORM set_config('app.current_user_id', v_actor::text, true);

    -- A: la coincidencia municipio + tenencia + nombre ya no es identidad.
    INSERT INTO nucleo_agrario (
        id_municipio, nombre_nucleo, id_tipo_tenencia, fuente_datos,
        id_entidad_fuente, id_municipio_fuente, id_nucleo_fuente,
        alcance_identidad_fuente
    ) VALUES
        (v_municipio, 'CONTRATO 019 MISMO NOMBRE', v_tenencia,
         'RAN_PHINA_CATALOGO_NUCLEOS', '99', '999',
         'CONTRATO_019_A_1', 'nacional'),
        (v_municipio, 'CONTRATO 019 MISMO NOMBRE', v_tenencia,
         'RAN_PHINA_CATALOGO_NUCLEOS', '99', '999',
         'CONTRATO_019_A_2', 'nacional');

    IF (
        SELECT count(*)
          FROM nucleo_agrario
         WHERE id_nucleo_fuente IN ('CONTRATO_019_A_1', 'CONTRATO_019_A_2')
    ) <> 2 THEN
        RAISE EXCEPTION 'A falló: no coexistieron ambas identidades RAN';
    END IF;

    -- B: fuente + id externo es única aun con nombre distinto.
    BEGIN
        INSERT INTO nucleo_agrario (
            id_municipio, nombre_nucleo, id_tipo_tenencia, fuente_datos,
            id_entidad_fuente, id_municipio_fuente, id_nucleo_fuente,
            alcance_identidad_fuente
        ) VALUES (
            v_municipio, 'CONTRATO 019 OTRO NOMBRE', v_tenencia,
            ' ran_phina_catalogo_nucleos ', '99', '999',
            ' CONTRATO_019_A_1 ', 'nacional'
        );
    EXCEPTION WHEN unique_violation THEN
        v_duplicado_rechazado := true;
    END;
    IF NOT v_duplicado_rechazado THEN
        RAISE EXCEPTION 'B falló: se aceptó una identidad externa duplicada';
    END IF;

    -- C: toda fila RAN necesita la identidad y procedencia territorial.
    BEGIN
        INSERT INTO nucleo_agrario (
            id_municipio, nombre_nucleo, id_tipo_tenencia, fuente_datos,
            id_entidad_fuente, id_municipio_fuente, id_nucleo_fuente,
            alcance_identidad_fuente
        ) VALUES (
            v_municipio, 'CONTRATO 019 RAN INCOMPLETO', v_tenencia,
            'RAN_PHINA_CATALOGO_NUCLEOS', '99', '999', NULL, 'nacional'
        );
    EXCEPTION WHEN check_violation THEN
        v_ran_incompleto_rechazado := true;
    END;
    IF NOT v_ran_incompleto_rechazado THEN
        RAISE EXCEPTION 'C falló: se aceptó una fila RAN sin cve_unica';
    END IF;

    -- D: filas manuales sin identidad externa continúan coexistiendo.
    INSERT INTO nucleo_agrario (
        id_municipio, nombre_nucleo, id_tipo_tenencia,
        fuente_datos, id_nucleo_fuente
    ) VALUES
        (v_municipio, 'CONTRATO 019 MANUAL', v_tenencia, 'manual', NULL),
        (v_municipio, 'CONTRATO 019 MANUAL', v_tenencia, 'manual', NULL);

    IF (
        SELECT count(*)
          FROM nucleo_agrario
         WHERE nombre_nucleo = 'CONTRATO 019 MANUAL'
           AND id_nucleo_fuente IS NULL
    ) <> 2 THEN
        RAISE EXCEPTION 'D falló: no coexistieron filas manuales sin ID externo';
    END IF;

    RAISE NOTICE 'A OK: mismo municipio/tenencia/nombre con distinta cve_unica';
    RAISE NOTICE 'B OK: fuente + id_nucleo_fuente duplicados rechazados';
    RAISE NOTICE 'C OK: fila RAN sin id_nucleo_fuente rechazada';
    RAISE NOTICE 'D OK: filas manuales con id_nucleo_fuente NULL coexistieron';
END $$;

ROLLBACK;
