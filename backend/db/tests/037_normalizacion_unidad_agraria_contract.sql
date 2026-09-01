-- 037_normalizacion_unidad_agraria_contract.sql
-- Contrato transaccional. Debe ejecutarse despues de aplicar la migracion 037.
-- No deja datos: todo ocurre dentro de BEGIN/ROLLBACK.
\set ON_ERROR_STOP on
BEGIN;

DO $contract$
DECLARE
    v_user INTEGER;
    v_municipio INTEGER;
    v_municipio_2 INTEGER;
    v_proyecto INTEGER;
    v_nucleo INTEGER;
    v_nucleo_2 INTEGER;
    v_pn INTEGER;
    v_parcela INTEGER;
    v_persona INTEGER;
    v_parcela_titular INTEGER;
    v_afectacion_colectiva INTEGER;
    v_afectacion_adicional INTEGER;
    v_afectacion_individual INTEGER;
    v_unidad_colectiva BIGINT;
    v_unidad_individual BIGINT;
    v_unidad_otro_nucleo BIGINT;
    v_tenencia BIGINT;
    v_residencia BIGINT;
    v_tipo_tierra BIGINT;
    v_gestion_parcela BIGINT;
    v_destino_escolar BIGINT;
    v_tit_nucleo BIGINT;
    v_tit_persona BIGINT;
    v_cop_origen BIGINT;
    v_cop_adicional BIGINT;
    v_motivo_expro BIGINT;
    v_count INTEGER;
    v_failed BOOLEAN;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='037') THEN
        RAISE EXCEPTION 'El contrato requiere esquema 037';
    END IF;

    SELECT min(id_usuario) INTO v_user FROM usuario WHERE activo;
    PERFORM set_config('app.current_user_id',v_user::TEXT,TRUE);
    SELECT min(id_municipio) INTO v_municipio FROM municipio WHERE activo;
    SELECT min(id_municipio) INTO v_municipio_2 FROM municipio WHERE activo AND id_municipio<>v_municipio;
    IF v_user IS NULL OR v_municipio IS NULL OR v_municipio_2 IS NULL THEN
        RAISE EXCEPTION 'Contrato 037 requiere usuario y al menos dos municipios activos';
    END IF;

    SELECT id_catalogo_opcion INTO v_tenencia FROM catalogo_operativo WHERE tipo_catalogo='tipo_tenencia' AND codigo='ejido';
    SELECT id_catalogo_opcion INTO v_residencia FROM catalogo_operativo WHERE tipo_catalogo='residencia' ORDER BY orden,id_catalogo_opcion LIMIT 1;
    SELECT id_catalogo_opcion INTO v_tipo_tierra FROM catalogo_operativo WHERE tipo_catalogo='tipo_tierra' AND codigo='no_determinada';
    SELECT id_catalogo_opcion INTO v_gestion_parcela FROM catalogo_operativo WHERE tipo_catalogo='tipo_gestion' AND codigo='PARCELA';
    SELECT id_catalogo_opcion INTO v_destino_escolar FROM catalogo_operativo WHERE tipo_catalogo='destino_superficie' AND codigo='parcela_escolar';
    SELECT id_catalogo_opcion INTO v_tit_nucleo FROM catalogo_operativo WHERE tipo_catalogo='tipo_titularidad_unidad' AND codigo='nucleo_agrario';
    SELECT id_catalogo_opcion INTO v_tit_persona FROM catalogo_operativo WHERE tipo_catalogo='tipo_titularidad_unidad' AND codigo='persona';
    SELECT id_catalogo_opcion INTO v_cop_origen FROM catalogo_operativo WHERE tipo_catalogo='tipo_cop_operativo' AND codigo='ORIGEN';
    SELECT id_catalogo_opcion INTO v_cop_adicional FROM catalogo_operativo WHERE tipo_catalogo='tipo_cop_operativo' AND codigo='ADICIONAL';
    SELECT id_catalogo_opcion INTO v_motivo_expro FROM catalogo_operativo WHERE tipo_catalogo='motivo_no_afecta_tuc' AND codigo='expropiacion_directa';

    IF v_tenencia IS NULL OR v_residencia IS NULL OR v_tipo_tierra IS NULL
       OR v_gestion_parcela IS NULL OR v_destino_escolar IS NULL
       OR v_tit_nucleo IS NULL OR v_tit_persona IS NULL
       OR v_cop_origen IS NULL OR v_cop_adicional IS NULL OR v_motivo_expro IS NULL THEN
        RAISE EXCEPTION 'Faltan catalogos obligatorios de 037';
    END IF;

    INSERT INTO proyecto(clave_proyecto,nombre_proyecto,creado_por)
    VALUES ('QA037-'||txid_current(),'Contrato QA 037',v_user)
    RETURNING id_proyecto INTO v_proyecto;

    INSERT INTO nucleo_agrario(id_municipio,nombre_nucleo,tipo_nucleo,id_tipo_tenencia,comunidad_indigena,creado_por)
    VALUES (v_municipio,'NUCLEO QA 037 A '||txid_current(),'ejido',v_tenencia,NULL,v_user)
    RETURNING id_nucleo INTO v_nucleo;

    INSERT INTO nucleo_agrario(id_municipio,nombre_nucleo,tipo_nucleo,id_tipo_tenencia,comunidad_indigena,creado_por)
    VALUES (v_municipio_2,'NUCLEO QA 037 B '||txid_current(),'ejido',v_tenencia,FALSE,v_user)
    RETURNING id_nucleo INTO v_nucleo_2;

    INSERT INTO proyecto_nucleo(id_proyecto,id_nucleo,id_residencia,residencia,creado_por)
    VALUES (v_proyecto,v_nucleo,v_residencia,'compatibilidad',v_user)
    RETURNING id_proyecto_nucleo INTO v_pn;

    INSERT INTO parcela(id_nucleo,tipo_parcela,no_parcela,creado_por)
    VALUES (v_nucleo,'individual','P-QA-037',v_user)
    RETURNING id_parcela INTO v_parcela;

    INSERT INTO persona(nombre,origen_registro,creado_por)
    VALUES ('PERSONA SINTETICA QA 037','qa',v_user)
    RETURNING id_persona INTO v_persona;

    INSERT INTO parcela_titular(id_parcela,id_persona,tipo_derecho,porcentaje_participacion,creado_por)
    VALUES (v_parcela,v_persona,'titular',100,v_user)
    RETURNING id_parcela_titular INTO v_parcela_titular;

    -- Colectivo + PARCELA + parcela escolar es valido.
    INSERT INTO afectacion(id_proyecto_nucleo,id_parcela,tipo_afectacion,id_tipo_cop_operativo,creado_por)
    VALUES (v_pn,v_parcela,'colectivo',v_cop_origen,v_user)
    RETURNING id_afectacion INTO v_afectacion_colectiva;

    INSERT INTO unidad_agraria(
        id_nucleo,id_tipo_tierra,id_tipo_gestion,id_destino_superficie,
        id_tipo_titularidad,id_parcela,referencia_alfanumerica,fuente,creado_por
    ) VALUES (
        v_nucleo,v_tipo_tierra,v_gestion_parcela,v_destino_escolar,
        v_tit_nucleo,v_parcela,'P-QA-037','contract_037',v_user
    ) RETURNING id_unidad_agraria INTO v_unidad_colectiva;

    INSERT INTO afectacion_unidad_agraria(
        id_afectacion,id_unidad_agraria,superficie_afectada_ha,
        superficie_valor_original,superficie_formato_origen,fuente,creado_por
    ) VALUES (
        v_afectacion_colectiva,v_unidad_colectiva,0.201694,
        '00-20-16.940','H-M2-CM2','contract_037',v_user
    );

    IF (SELECT tipo_afectacion FROM afectacion WHERE id_afectacion=v_afectacion_colectiva)<>'colectivo' THEN
        RAISE EXCEPTION 'TIPO_GESTION=PARCELA altero indebidamente el ambito colectivo';
    END IF;

    -- El mismo bien puede participar en otra afectacion/proceso sin duplicarse.
    INSERT INTO afectacion(id_proyecto_nucleo,id_parcela,tipo_afectacion,id_tipo_cop_operativo,creado_por)
    VALUES (v_pn,v_parcela,'colectivo',v_cop_adicional,v_user)
    RETURNING id_afectacion INTO v_afectacion_adicional;

    INSERT INTO afectacion_unidad_agraria(id_afectacion,id_unidad_agraria,superficie_afectada_ha,fuente,creado_por)
    VALUES (v_afectacion_adicional,v_unidad_colectiva,0.010000,'contract_037',v_user);

    SELECT count(*) INTO v_count
    FROM afectacion_unidad_agraria
    WHERE id_unidad_agraria=v_unidad_colectiva AND activo;
    IF v_count<>2 THEN
        RAISE EXCEPTION 'La misma unidad no pudo relacionarse con dos afectaciones/procesos';
    END IF;
    IF (SELECT id_tipo_cop_operativo FROM afectacion WHERE id_afectacion=v_afectacion_colectiva)=
       (SELECT id_tipo_cop_operativo FROM afectacion WHERE id_afectacion=v_afectacion_adicional) THEN
        RAISE EXCEPTION 'TIPO COP no quedo separado por afectacion/proceso';
    END IF;

    -- Individual usa la misma parcela fisica, pero una unidad juridica con titularidad persona.
    INSERT INTO afectacion(id_proyecto_nucleo,id_parcela,tipo_afectacion,id_tipo_cop_operativo,creado_por)
    VALUES (v_pn,v_parcela,'individual',v_cop_origen,v_user)
    RETURNING id_afectacion INTO v_afectacion_individual;

    INSERT INTO unidad_agraria(
        id_nucleo,id_tipo_tierra,id_tipo_gestion,id_destino_superficie,
        id_tipo_titularidad,id_parcela,referencia_alfanumerica,fuente,creado_por
    ) VALUES (
        v_nucleo,v_tipo_tierra,v_gestion_parcela,NULL,
        v_tit_persona,v_parcela,'P-QA-037','contract_037',v_user
    ) RETURNING id_unidad_agraria INTO v_unidad_individual;

    INSERT INTO unidad_agraria_titular(
        id_unidad_agraria,id_parcela_titular,porcentaje_participacion,es_principal,creado_por
    ) VALUES (v_unidad_individual,v_parcela_titular,100,TRUE,v_user);

    INSERT INTO afectacion_unidad_agraria(id_afectacion,id_unidad_agraria,superficie_afectada_ha,fuente,creado_por)
    VALUES (v_afectacion_individual,v_unidad_individual,0.005000,'contract_037',v_user);

    IF v_unidad_individual=v_unidad_colectiva THEN
        RAISE EXCEPTION 'Se colapso indebidamente la unidad colectiva con la individual';
    END IF;

    -- Una unidad de otro nucleo no puede asociarse a la afectacion.
    INSERT INTO unidad_agraria(
        id_nucleo,id_tipo_tierra,id_tipo_gestion,id_destino_superficie,
        id_tipo_titularidad,referencia_alfanumerica,fuente,creado_por
    ) VALUES (
        v_nucleo_2,v_tipo_tierra,v_gestion_parcela,v_destino_escolar,
        v_tit_nucleo,'OTRO-NUCLEO','contract_037',v_user
    ) RETURNING id_unidad_agraria INTO v_unidad_otro_nucleo;

    v_failed:=FALSE;
    BEGIN
        INSERT INTO afectacion_unidad_agraria(id_afectacion,id_unidad_agraria,fuente,creado_por)
        VALUES (v_afectacion_colectiva,v_unidad_otro_nucleo,'contract_037',v_user);
    EXCEPTION WHEN others THEN
        v_failed:=TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'Se acepto una unidad agraria de otro nucleo';
    END IF;

    -- NO AFECTA TUC se registra en ProyectoNucleo, sin crear una afectacion ficticia.
    SELECT count(*) INTO v_count FROM afectacion WHERE id_proyecto_nucleo=v_pn;
    UPDATE proyecto_nucleo
    SET afecta_tuc=FALSE,
        id_motivo_no_afecta_tuc=v_motivo_expro,
        motivo_no_afecta_tuc_detalle='QA'
    WHERE id_proyecto_nucleo=v_pn;
    IF (SELECT afecta_tuc FROM proyecto_nucleo WHERE id_proyecto_nucleo=v_pn) IS DISTINCT FROM FALSE THEN
        RAISE EXCEPTION 'No se pudo registrar NO AFECTA TUC';
    END IF;
    IF (SELECT count(*) FROM afectacion WHERE id_proyecto_nucleo=v_pn)<>v_count THEN
        RAISE EXCEPTION 'Registrar NO AFECTA TUC genero una afectacion ficticia';
    END IF;

    -- Catálogo de tipo incorrecto debe rechazarse.
    v_failed:=FALSE;
    BEGIN
        INSERT INTO unidad_agraria(
            id_nucleo,id_tipo_tierra,id_tipo_gestion,id_tipo_titularidad,
            referencia_alfanumerica,creado_por
        ) VALUES (
            v_nucleo,v_gestion_parcela,v_gestion_parcela,v_tit_nucleo,
            'CAT-INVALIDO',v_user
        );
    EXCEPTION WHEN others THEN
        v_failed:=TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'Se acepto un catalogo incorrecto como tipo_tierra';
    END IF;

    -- DELETE fisico debe bloquearse.
    v_failed:=FALSE;
    BEGIN
        DELETE FROM unidad_agraria WHERE id_unidad_agraria=v_unidad_otro_nucleo;
    EXCEPTION WHEN others THEN
        v_failed:=TRUE;
    END;
    IF NOT v_failed THEN
        RAISE EXCEPTION 'unidad_agraria permitio DELETE fisico';
    END IF;

    RAISE NOTICE 'CONTRATO 037 APROBADO';
END;
$contract$;

ROLLBACK;
