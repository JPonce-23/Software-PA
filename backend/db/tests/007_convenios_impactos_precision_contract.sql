\set ON_ERROR_STOP on

-- Contrato POST-007. Se prepara en este bloque, pero no debe ejecutarse hasta
-- que 007 haya sido autorizada y aplicada por el runner en software_pa_test.
SET search_path = public, pg_catalog;

DO $$
DECLARE
    faltantes text;
BEGIN
    SELECT string_agg(v.version, ', ' ORDER BY v.version)
      INTO faltantes
      FROM (VALUES
        ('001','242ffc787beb2886d36b6fb3031c25a8baddd23ce669e78488672e274c4ad7c7'),
        ('002','ef1165711cc6054f26921062fd4e8202ce3dc0f7623ddb8f7eac1daa8639577e'),
        ('003','807279889979c3e7d55e849738f2361483e8e20810614f068515e8f95aa053ba'),
        ('004','7c1a470e2429b6ec6ff3bc003ae9e3324ce3d552a984904760d0deb57381de12'),
        ('005','a35faa802c5f43a3c906aae6c62b5bac4ef842f610e87a178a2e8524ed494c76'),
        ('006','e1a603fd2015615671c0cd072a0a795f50e92e8c21e838f26d88abec25dddee4')
      ) v(version,checksum)
     WHERE NOT EXISTS (
        SELECT 1 FROM schema_migrations sm
        WHERE sm.version=v.version AND sm.checksum_sha256=v.checksum
     );
    IF faltantes IS NOT NULL THEN
        RAISE EXCEPTION 'Migraciones previas ausentes o alteradas: %', faltantes;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='007') THEN
        RAISE EXCEPTION 'El contrato 007 sólo corre después de aplicar 007 con el runner';
    END IF;
END $$;

DO $$
DECLARE faltantes text;
BEGIN
    SELECT string_agg(x.tabla||'.'||x.columna, ', ')
      INTO faltantes
      FROM (VALUES
        ('afectacion','superficie_preliminar_ha'),
        ('afectacion','superficie_afectada_ha'),
        ('afectacion_unidad_agraria','superficie_preliminar_ha'),
        ('afectacion_unidad_agraria','superficie_afectada_ha'),
        ('convenio','superficie_ha'),
        ('convenio_afectacion','superficie_impacto_ha')
      ) x(tabla,columna)
     WHERE NOT EXISTS (
        SELECT 1 FROM information_schema.columns c
        WHERE c.table_schema='public' AND c.table_name=x.tabla
          AND c.column_name=x.columna AND c.data_type='numeric'
          AND c.numeric_precision=15 AND c.numeric_scale=7
     );
    IF faltantes IS NOT NULL THEN
        RAISE EXCEPTION 'Precisión distinta de numeric(15,7): %', faltantes;
    END IF;
END $$;

DO $$
DECLARE faltantes text;
BEGIN
    SELECT string_agg(x.nombre, ', ' ORDER BY x.nombre) INTO faltantes
    FROM (VALUES
      ('chk_convenio_efecto_monto_007'),('chk_convenio_impacto_monto_007'),
      ('chk_convenio_impacto_declarado_007'),('chk_ca_efecto_superficie_007'),
      ('chk_ca_impacto_superficie_007'),('chk_convenio_estado_antecedente_007')
    ) x(nombre)
    WHERE NOT EXISTS (
      SELECT 1 FROM pg_constraint c WHERE c.conname=x.nombre AND c.convalidated
    );
    IF faltantes IS NOT NULL THEN
        RAISE EXCEPTION 'CHECK 007 ausente o no validado: %', faltantes;
    END IF;
    IF position('tipo_instrumento IS DISTINCT FROM ''convenio''' IN
       pg_get_functiondef('fn_validar_convenio_relaciones()'::regprocedure))=0
       OR position('id_convenio_padre=NEW.id_convenio' IN
       pg_get_functiondef('fn_validar_convenio_relaciones()'::regprocedure))=0 THEN
        RAISE EXCEPTION 'Linaje general sin protección de padre-instrumento/autopadre';
    END IF;
    IF position('documento_vinculo' IN
       pg_get_functiondef('fn_convenio_firma_acreditada_007(integer)'::regprocedure))=0
       OR position('orv_integrante' IN
       pg_get_functiondef('fn_convenio_firma_acreditada_007(integer)'::regprocedure))=0 THEN
        RAISE EXCEPTION 'Firma colectiva sin comprobación dinámica ORV/documento';
    END IF;
    IF EXISTS (
      SELECT 1 FROM pg_trigger t
      WHERE t.tgname IN ('trg_audit_convenio','trg_audit_catalogo_operativo',
        'trg_audit_requisito_documental','trg_audit_expediente_requisito')
        AND t.tgenabled<>'O'
    ) THEN RAISE EXCEPTION '007 dejó deshabilitado un trigger de auditoría'; END IF;
    IF EXISTS (
      SELECT 1 FROM (VALUES
        ('trg_convenio_individual_firmado'),
        ('trg_linaje_unidad_convenio')
      ) x(nombre)
      WHERE NOT EXISTS (
        SELECT 1 FROM pg_trigger t
        JOIN pg_constraint c ON c.oid=t.tgconstraint
        WHERE t.tgname=x.nombre AND t.tgrelid='convenio'::regclass
          AND t.tgenabled='O' AND t.tgdeferrable AND t.tginitdeferred
          AND c.condeferrable AND c.condeferred
      )
    ) THEN
      RAISE EXCEPTION '007 alteró o deshabilitó constraint triggers diferidos de convenio';
    END IF;
END $$;

DO $$
DECLARE faltantes text;
BEGIN
    SELECT string_agg(x.objeto, ', ')
      INTO faltantes
      FROM (VALUES
        ('column:convenio.efecto_monto'),
        ('column:convenio.monto_90_impacto'),
        ('column:convenio.monto_100_impacto'),
        ('column:convenio.monto_bdt_impacto'),
        ('column:convenio.estado_antecedente'),
        ('column:convenio_afectacion.efecto_superficie'),
        ('trigger:trg_estado_antecedente_007'),
        ('trigger:trg_validar_compareciente'),
        ('function:fn_convenio_firma_acreditada_007'),
        ('view:vw_convenio_valor_declarado'),
        ('view:vw_convenio_impacto'),
        ('view:vw_reporte_convenio_impacto_periodo'),
        ('view:vw_convenio_cobertura_impacto')
      ) x(objeto)
     WHERE CASE
       WHEN x.objeto LIKE 'column:%' THEN to_regclass(split_part(split_part(x.objeto,':',2),'.',1)) IS NULL
         OR NOT EXISTS (
           SELECT 1 FROM information_schema.columns c
           WHERE c.table_schema='public'
             AND c.table_name=split_part(split_part(x.objeto,':',2),'.',1)
             AND c.column_name=split_part(split_part(x.objeto,':',2),'.',2))
       WHEN x.objeto LIKE 'trigger:%' THEN NOT EXISTS (
           SELECT 1 FROM pg_trigger t WHERE t.tgname=split_part(x.objeto,':',2) AND NOT t.tgisinternal)
       WHEN x.objeto LIKE 'function:%' THEN
         to_regprocedure(split_part(x.objeto,':',2)||'(integer)') IS NULL
       ELSE to_regclass('public.'||split_part(x.objeto,':',2)) IS NULL
     END;
    IF faltantes IS NOT NULL THEN RAISE EXCEPTION 'Objetos 007 faltantes: %', faltantes; END IF;
END $$;

-- Pendiente nunca equivale a cero; los estados conocidos deben tener impacto
-- explícito conforme a los CHECK de 007.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM convenio
        WHERE efecto_monto='pendiente'
          AND num_nonnulls(monto_90_impacto,monto_100_impacto,monto_bdt_impacto)>0
    ) THEN RAISE EXCEPTION 'Impacto económico pendiente con cero/valor implícito'; END IF;
    IF EXISTS (
        SELECT 1 FROM convenio_afectacion
        WHERE efecto_superficie='pendiente' AND superficie_impacto_ha IS NOT NULL
    ) THEN RAISE EXCEPTION 'Impacto superficial pendiente con cero/valor implícito'; END IF;
    IF EXISTS (
        SELECT 1 FROM convenio
        WHERE (id_convenio_padre IS NOT NULL) <> (estado_antecedente='vinculado')
          AND tipo_instrumento='convenio'
          AND tipo_convenio IN ('modificatorio','superficie_adicional','obras_complementarias','ampliacion','ampliacion_remanente')
    ) THEN RAISE EXCEPTION 'Estado de antecedente inconsistente con el vínculo real'; END IF;
    IF EXISTS (
        SELECT 1 FROM expediente_requisito er
        JOIN catalogo_operativo ec ON ec.id_catalogo_opcion=er.id_estado
        WHERE er.detalle LIKE 'Backfill 007:%'
          AND (ec.codigo<>'pendiente_validacion' OR er.id_documento IS NOT NULL)
    ) THEN RAISE EXCEPTION 'Backfill 007 inventó firma o documento acreditado'; END IF;
END $$;

-- Sondas negativas sin persistencia: cada bloque PL/pgSQL usa una subtransacción
-- que se revierte al capturar la violación esperada.
DO $$
DECLARE v_convenio integer; v_relacion integer; rechazo boolean;
BEGIN
    SELECT id_convenio INTO v_convenio FROM convenio WHERE activo ORDER BY id_convenio LIMIT 1;
    SELECT id_convenio_afectacion INTO v_relacion
      FROM convenio_afectacion WHERE activo ORDER BY id_convenio_afectacion LIMIT 1;
    IF v_convenio IS NULL OR v_relacion IS NULL THEN
        RAISE EXCEPTION 'Faltan fixtures mínimos para sondas negativas 007';
    END IF;

    rechazo := false;
    BEGIN
        UPDATE convenio SET efecto_monto='pendiente',monto_90_impacto=0
         WHERE id_convenio=v_convenio;
    EXCEPTION WHEN check_violation THEN rechazo := true;
    END;
    IF NOT rechazo THEN RAISE EXCEPTION 'Pendiente económico aceptó cero implícito'; END IF;

    rechazo := false;
    BEGIN
        UPDATE convenio_afectacion
           SET efecto_superficie='pendiente',superficie_impacto_ha=0
         WHERE id_convenio_afectacion=v_relacion;
    EXCEPTION WHEN check_violation THEN rechazo := true;
    END;
    IF NOT rechazo THEN RAISE EXCEPTION 'Pendiente superficial aceptó cero implícito'; END IF;

    rechazo := false;
    BEGIN
        UPDATE convenio SET id_convenio_padre=id_convenio,
               estado_antecedente='vinculado'
         WHERE id_convenio=v_convenio;
    EXCEPTION WHEN raise_exception THEN rechazo := true;
    END;
    IF NOT rechazo THEN RAISE EXCEPTION 'Linaje aceptó autopadre'; END IF;
END $$;

-- La rama económica tiene una clave por instrumento/concepto y no depende de
-- la cardinalidad convenio_afectacion.
DO $$
BEGIN
    IF EXISTS (
        SELECT clave_impacto FROM vw_convenio_impacto
        WHERE concepto IN ('monto_90','monto_100','monto_bdt')
        GROUP BY clave_impacto HAVING count(*)<>1
    ) THEN RAISE EXCEPTION 'Impacto económico multiplicado por relación N:M'; END IF;
    IF EXISTS (
        SELECT c.id_convenio FROM convenio c
        WHERE c.activo AND c.efecto_monto='pendiente'
          AND c.monto_90 IS NULL AND c.monto_100 IS NULL AND c.monto_bdt IS NULL
          AND NOT EXISTS (
            SELECT 1 FROM vw_convenio_impacto vi
            WHERE vi.id_convenio=c.id_convenio
              AND vi.concepto='monto_pendiente_clasificar'
              AND vi.pendiente AND vi.valor_impacto IS NULL
          )
    ) THEN RAISE EXCEPTION 'Instrumento sin universo económico desapareció del contador pendiente'; END IF;
    IF EXISTS (
        SELECT 1 FROM vw_reporte_convenio_impacto_periodo
        WHERE concepto='monto_90+monto_100+monto_bdt'
    ) THEN RAISE EXCEPTION 'Los universos 90%%, 100%% y BDT fueron sumados'; END IF;
END $$;

-- Las seis vistas históricas deben sobrevivir con sus permisos; las cuatro
-- nuevas exponen indicadores separados y cobertura pendiente.
DO $$
DECLARE nombre text;
BEGIN
    FOREACH nombre IN ARRAY ARRAY[
      'vw_proyecto_nucleo_resumen','vw_hito_seguimiento_005','vw_hito_seguimiento','vw_reporte_avance_periodo',
      'vw_dashboard_kpi','vw_reporte_snapshot_actual','vw_convenio_valor_declarado',
      'vw_convenio_impacto','vw_reporte_convenio_impacto_periodo',
      'vw_convenio_cobertura_impacto'
    ] LOOP
        IF to_regclass('public.'||nombre) IS NULL THEN
            RAISE EXCEPTION 'Vista ausente: %', nombre;
        END IF;
        IF NOT has_table_privilege('software_pa_app','public.'||nombre,'SELECT') THEN
            RAISE EXCEPTION 'Permiso SELECT ausente en %', nombre;
        END IF;
    END LOOP;
    FOREACH nombre IN ARRAY ARRAY[
      'vw_proyecto_nucleo_resumen','vw_hito_seguimiento_005','vw_hito_seguimiento',
      'vw_reporte_avance_periodo','vw_dashboard_kpi','vw_reporte_snapshot_actual'
    ] LOOP
        IF NOT has_table_privilege('software_pa_app','public.'||nombre,'INSERT')
           OR NOT has_table_privilege('software_pa_app','public.'||nombre,'UPDATE')
           OR has_table_privilege('software_pa_app','public.'||nombre,'DELETE')
           OR has_table_privilege('software_pa_app','public.'||nombre,'TRUNCATE') THEN
            RAISE EXCEPTION 'ACL histórica no preservada en %', nombre;
        END IF;
    END LOOP;
    IF EXISTS (
      SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='public'
        AND c.relname IN ('vw_proyecto_nucleo_resumen','vw_hito_seguimiento_005',
          'vw_hito_seguimiento','vw_reporte_avance_periodo','vw_dashboard_kpi',
          'vw_reporte_snapshot_actual')
        AND pg_get_userbyid(c.relowner)<>current_user
    ) THEN RAISE EXCEPTION 'No se preservó el propietario de una vista histórica'; END IF;
    IF EXISTS (
      SELECT 1 FROM (VALUES
        ('vw_convenio_valor_declarado'),('vw_convenio_impacto'),
        ('vw_reporte_convenio_impacto_periodo'),('vw_convenio_cobertura_impacto')
      ) x(nombre)
      WHERE obj_description(to_regclass('public.'||x.nombre),'pg_class') IS NULL
    ) THEN RAISE EXCEPTION 'Vista 007 sin comentario semántico'; END IF;
    IF position('monto_100' IN pg_get_viewdef('vw_hito_seguimiento_005'::regclass,true))=0
       OR position('monto_100_impacto' IN pg_get_viewdef('vw_hito_seguimiento_005'::regclass,true))>0
       OR position('superficie_afectada_ha' IN pg_get_viewdef('vw_reporte_snapshot_actual'::regclass,true))=0 THEN
        RAISE EXCEPTION 'Una vista histórica cambió de valor declarado/físico a impacto 007';
    END IF;
END $$;

DO $$
DECLARE faltantes text;
BEGIN
    SELECT string_agg(x.vista||'.'||x.columna||':'||x.tipo, ', ')
      INTO faltantes
      FROM (VALUES
        ('vw_convenio_valor_declarado','valor_declarado','numeric'),
        ('vw_convenio_valor_declarado','fecha_instrumento_reportada','date'),
        ('vw_convenio_valor_declarado','firma_acreditada','boolean'),
        ('vw_convenio_impacto','clave_impacto','text'),
        ('vw_convenio_impacto','valor_impacto','numeric'),
        ('vw_convenio_impacto','pendiente','boolean'),
        ('vw_convenio_impacto','firma_acreditada','boolean'),
        ('vw_reporte_convenio_impacto_periodo','cantidad','bigint'),
        ('vw_reporte_convenio_impacto_periodo','valor_impacto','numeric'),
        ('vw_convenio_cobertura_impacto','universo','bigint'),
        ('vw_convenio_cobertura_impacto','clasificados','bigint'),
        ('vw_convenio_cobertura_impacto','pendientes','bigint'),
        ('vw_convenio_cobertura_impacto','sin_firma_acreditada','bigint')
      ) x(vista,columna,tipo)
     WHERE NOT EXISTS (
       SELECT 1 FROM information_schema.columns c
       WHERE c.table_schema='public' AND c.table_name=x.vista
         AND c.column_name=x.columna AND c.data_type=x.tipo
     );
    IF faltantes IS NOT NULL THEN
        RAISE EXCEPTION 'Columnas/tipos de reporting 007 incorrectos: %', faltantes;
    END IF;
END $$;

-- Casos de aceptación que deben cargarse con trazabilidad_fuente después de
-- aplicar 007; este contrato deliberadamente no inventa/importa hechos:
--   El Muerto P-201: sustitución/sin doble conteo; padre sólo si está soportado.
--   San Pedrito: sin convenio soportado => no crear instrumento.
--   Pueblo Nuevo: contradicciones permanecen pendientes de revisión.
--   San Clemente y Barrancas: asamblea compartida no multiplica impactos.
--   P-15: ampliación/remanente sólo con efecto y antecedente documentados.

DO $$
BEGIN
    -- Literales de superficie que 14,6 no podía conservar. Esta comprobación
    -- sólo valida capacidad/serialización decimal; no autoriza el backfill.
    IF 0.1668079::numeric(15,7) <> 0.1668079::numeric
       OR 0.1403761::numeric(15,7) <> 0.1403761::numeric
       OR 0.9443113::numeric(15,7) <> 0.9443113::numeric
       OR 0.3978597::numeric(15,7) <> 0.3978597::numeric
       OR 0.4128559::numeric(15,7) <> 0.4128559::numeric THEN
        RAISE EXCEPTION 'numeric(15,7) no conserva los literales auditados';
    END IF;
END $$;

SELECT '007_convenios_impactos_precision_contract: OK' AS resultado;
