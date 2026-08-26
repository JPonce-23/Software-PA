\set ON_ERROR_STOP on
BEGIN;

SELECT pg_advisory_xact_lock(20260825, 200);
SELECT set_config('app.current_user_id', (SELECT id_usuario::text FROM usuario WHERE activo AND rol = 'admin' ORDER BY id_usuario LIMIT 1), true);

DO $contract$
DECLARE
    v_missing TEXT[];
    v_present TEXT[];
    v_count INTEGER;
BEGIN
    SELECT array_agg(name ORDER BY name) INTO v_missing
    FROM unnest(ARRAY[
      'proyecto_nucleo','proyecto_nucleo_referencia','orv','orv_integrante','padron_historial',
      'parcela','parcela_titular','actividad_campo','afectacion','asamblea','convenio',
      'convenio_afectacion','tramite_fifonafe','tramite_fifonafe_afectacion',
      'indemnizacion','pago','usuario_proyecto','documento','documento_version',
      'documento_vinculo','trazabilidad_fuente','bitacora','trazo_proyecto',
      'importacion_archivo','importacion_feature'
    ]) AS expected(name)
    WHERE to_regclass('public.' || name) IS NULL;
    IF v_missing IS NOT NULL THEN RAISE EXCEPTION 'Faltan tablas objetivo: %', v_missing; END IF;

    SELECT array_agg(name ORDER BY name) INTO v_present
    FROM unnest(ARRAY[
      'tramo','tramo_nucleo','afectacion_ciclo','usuario_tramo','candidato_tramo_nucleo',
      'seccion_derecho_via','franja_derecho_via','carga_geoespacial','carga_geoespacial_feature'
    ]) AS legacy(name)
    WHERE to_regclass('public.' || name) IS NOT NULL;
    IF v_present IS NOT NULL THEN RAISE EXCEPTION 'Persisten tablas legacy: %', v_present; END IF;

    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '033')
       OR EXISTS (SELECT 1 FROM schema_migrations WHERE version::integer > 33) THEN
        RAISE EXCEPTION 'schema_migrations no termina exactamente en 033';
    END IF;
    IF (SELECT COUNT(*) FROM entidad_federativa WHERE activo) <> 32
       OR (SELECT COUNT(*) FROM municipio WHERE activo) <> 2478 THEN
        RAISE EXCEPTION 'Catálogo territorial distinto de 32/2478';
    END IF;

    SELECT COUNT(*) INTO v_count FROM pg_constraint
    WHERE conrelid IN (
      'proyecto_nucleo'::regclass,'afectacion'::regclass,'asamblea'::regclass,
      'convenio'::regclass,'convenio_afectacion'::regclass,
      'tramite_fifonafe'::regclass,'tramite_fifonafe_afectacion'::regclass,
      'indemnizacion'::regclass,'pago'::regclass,'documento_vinculo'::regclass
    ) AND contype IN ('p','f','c');
    IF v_count < 42 THEN RAISE EXCEPTION 'Contrato PK/FK/CHECK incompleto: % constraints', v_count; END IF;

    IF EXISTS (
      SELECT 1 FROM unnest(ARRAY[
        'proyecto','nucleo_agrario','proyecto_nucleo','proyecto_nucleo_referencia','persona',
        'orv','orv_integrante','padron_historial','parcela','parcela_titular','actividad_campo',
        'afectacion','asamblea','convenio','convenio_afectacion','tramite_fifonafe',
        'tramite_fifonafe_afectacion','indemnizacion','pago','usuario_proyecto','documento',
        'documento_vinculo','trazo_proyecto','importacion_archivo'
      ]) AS audited(table_name)
      WHERE (SELECT COUNT(*) FROM information_schema.columns c
             WHERE c.table_schema = 'public' AND c.table_name = audited.table_name
               AND c.column_name IN ('activo','fecha_baja','id_usuario_baja','motivo_baja')) <> 4
    ) THEN RAISE EXCEPTION 'Una tabla auditable carece de contrato de baja lógica'; END IF;

    IF EXISTS (
      SELECT 1 FROM unnest(ARRAY[
        'uq_proyecto_nucleo_activo','uq_pn_referencia_principal','uq_convenio_afectacion_principal',
        'uq_indemnizacion_afectacion_activa','uq_importacion_idempotente'
      ]) AS required(index_name)
      WHERE to_regclass('public.' || required.index_name) IS NULL
    ) THEN RAISE EXCEPTION 'Falta un índice UNIQUE parcial obligatorio'; END IF;

    IF EXISTS (
      SELECT 1 FROM unnest(ARRAY[
        'trg_afectacion_parcela_nucleo','trg_asamblea_padron','trg_convenio_relaciones',
        'trg_convenio_afectacion_coherencia','ctr_convenio_requiere_afectacion',
        'trg_fifonafe_afectacion_coherencia','ctr_fifonafe_requiere_afectacion',
        'trg_documento_version_inmutable','trg_documento_vinculo_objetivo','trg_trazabilidad_objetivo'
      ]) AS required(trigger_name)
      WHERE NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = required.trigger_name AND NOT tgisinternal)
    ) THEN RAISE EXCEPTION 'Falta un trigger obligatorio de integridad'; END IF;

    IF to_regclass('public.vw_orv_estado') IS NULL
       OR to_regclass('public.vw_proyecto_nucleo_resumen') IS NULL
       OR to_regclass('public.vw_dashboard_kpi') IS NULL THEN
        RAISE EXCEPTION 'Faltan vistas objetivo';
    END IF;
    IF EXISTS (
      SELECT 1 FROM pg_views WHERE schemaname = 'public'
        AND viewname IN ('vw_orv_estado','vw_proyecto_nucleo_resumen','vw_dashboard_kpi')
        AND (lower(definition) LIKE '%st_area%' OR lower(definition) LIKE '%st_intersects%')
    ) THEN RAISE EXCEPTION 'Una vista objetivo usa ST_Area/ST_Intersects'; END IF;
END;
$contract$;

DO $relations$
DECLARE
    v_admin INTEGER := (SELECT id_usuario FROM usuario WHERE activo AND rol = 'admin' ORDER BY id_usuario LIMIT 1);
    v_main INTEGER := (SELECT id_proyecto FROM proyecto WHERE clave_proyecto = 'MEX-QRO');
    v_pn_source INTEGER := (SELECT id_proyecto_nucleo FROM vw_proyecto_nucleo_resumen WHERE clave_proyecto = 'MEX-QRO' AND nombre_nucleo = 'SAN ILDEFONSO');
    v_pn_other INTEGER := (SELECT id_proyecto_nucleo FROM vw_proyecto_nucleo_resumen WHERE clave_proyecto = 'MEX-QRO' AND nombre_nucleo = 'AHORCADO');
    v_parcel INTEGER := (SELECT p.id_parcela FROM parcela p JOIN nucleo_agrario n USING(id_nucleo) WHERE n.nombre_nucleo = 'AHORCADO' ORDER BY p.id_parcela LIMIT 1);
    v_collective INTEGER := (SELECT id_afectacion FROM afectacion WHERE id_proyecto_nucleo = v_pn_source AND tipo_afectacion = 'colectivo' ORDER BY id_afectacion LIMIT 1);
    v_individual INTEGER := (SELECT id_afectacion FROM afectacion WHERE id_proyecto_nucleo = v_pn_other AND tipo_afectacion = 'individual' ORDER BY id_afectacion LIMIT 1);
    v_agreement INTEGER := (SELECT c.id_convenio FROM convenio c WHERE c.id_proyecto_nucleo = v_pn_source AND c.ambito = 'colectivo' ORDER BY c.id_convenio LIMIT 1);
    v_indemnity INTEGER := (SELECT id_indemnizacion FROM indemnizacion ORDER BY id_indemnizacion LIMIT 1);
    v_failed BOOLEAN;
BEGIN
    IF (SELECT COUNT(*) FROM proyecto_nucleo WHERE id_proyecto = v_main AND activo) <> 5 THEN RAISE EXCEPTION 'ProyectoNucleo esperado: 5'; END IF;
    IF (SELECT COUNT(*) FROM proyecto_nucleo_referencia WHERE id_proyecto_nucleo = v_pn_source AND tipo_referencia = 'consecutivo' AND activo) <> 2 THEN RAISE EXCEPTION 'Referencias múltiples no preservadas'; END IF;
    IF (SELECT COUNT(*) FROM proyecto_nucleo_referencia WHERE id_proyecto_nucleo = v_pn_source AND tipo_referencia = 'consecutivo' AND es_principal AND activo) <> 1 THEN RAISE EXCEPTION 'Principal de referencia no es único'; END IF;
    IF (SELECT COUNT(*) FROM parcela WHERE geometria_poligono IS NULL AND activo) <> 3 THEN RAISE EXCEPTION 'Geometría opcional de parcela no comprobada'; END IF;
    IF EXISTS (SELECT 1 FROM afectacion WHERE (tipo_afectacion = 'colectivo') <> (id_parcela IS NULL)) THEN RAISE EXCEPTION 'Ámbito/parcela incoherente en seed'; END IF;

    v_failed := FALSE;
    BEGIN
      INSERT INTO afectacion (id_proyecto_nucleo,id_parcela,tipo_afectacion,creado_por) VALUES (v_pn_source,v_parcel,'colectivo',v_admin);
    EXCEPTION WHEN check_violation OR raise_exception THEN v_failed := TRUE; END;
    IF NOT v_failed THEN RAISE EXCEPTION 'Se aceptó afectación colectiva con parcela'; END IF;

    v_failed := FALSE;
    BEGIN
      INSERT INTO afectacion (id_proyecto_nucleo,tipo_afectacion,creado_por) VALUES (v_pn_source,'individual',v_admin);
    EXCEPTION WHEN check_violation OR raise_exception THEN v_failed := TRUE; END;
    IF NOT v_failed THEN RAISE EXCEPTION 'Se aceptó afectación individual sin parcela'; END IF;

    v_failed := FALSE;
    BEGIN
      INSERT INTO afectacion (id_proyecto_nucleo,id_parcela,tipo_afectacion,creado_por) VALUES (v_pn_source,v_parcel,'individual',v_admin);
    EXCEPTION WHEN raise_exception THEN v_failed := TRUE; END;
    IF NOT v_failed THEN RAISE EXCEPTION 'Se aceptó parcela de otro núcleo'; END IF;

    IF NOT EXISTS (SELECT 1 FROM convenio_afectacion WHERE activo GROUP BY id_convenio HAVING COUNT(*) > 1 AND COUNT(*) FILTER (WHERE rol='principal') = 1) THEN RAISE EXCEPTION 'Seed no contiene convenio N:M con principal único'; END IF;
    v_failed := FALSE;
    BEGIN
      INSERT INTO convenio_afectacion (id_convenio,id_afectacion,rol,creado_por) VALUES (v_agreement,v_individual,'adicional',v_admin);
    EXCEPTION WHEN raise_exception THEN v_failed := TRUE; END;
    IF NOT v_failed THEN RAISE EXCEPTION 'Se aceptó vínculo convenio fuera de PN/ámbito'; END IF;

    v_failed := FALSE;
    BEGIN
      INSERT INTO indemnizacion (id_afectacion,estatus,creado_por) SELECT id_afectacion,'pendiente',v_admin FROM indemnizacion WHERE id_indemnizacion=v_indemnity;
    EXCEPTION WHEN unique_violation THEN v_failed := TRUE; END;
    IF NOT v_failed THEN RAISE EXCEPTION 'Se aceptó segunda indemnización activa'; END IF;

    IF (SELECT COUNT(*) FROM pago p JOIN indemnizacion i USING(id_indemnizacion) JOIN afectacion a USING(id_afectacion) JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE p.activo AND i.activo AND a.activo AND pn.activo) <> 2 THEN RAISE EXCEPTION 'Cadena financiera canónica incompleta'; END IF;
    IF NOT EXISTS (SELECT 1 FROM tramite_fifonafe_afectacion WHERE activo GROUP BY id_tramite_fifonafe HAVING COUNT(*) > 1) THEN RAISE EXCEPTION 'Seed no contiene FIFONAFE N:M'; END IF;

    v_failed := FALSE;
    BEGIN
      INSERT INTO documento_vinculo (id_documento,entidad_tipo,entidad_id,creado_por) VALUES ((SELECT id_documento FROM documento LIMIT 1),'pago',-1,v_admin);
    EXCEPTION WHEN raise_exception THEN v_failed := TRUE; END;
    IF NOT v_failed THEN RAISE EXCEPTION 'Se aceptó objetivo documental inexistente'; END IF;

    v_failed := FALSE;
    BEGIN
      UPDATE documento_version SET nombre_original='alterado.txt' WHERE id_documento_version=(SELECT id_documento_version FROM documento_version LIMIT 1);
    EXCEPTION WHEN raise_exception THEN v_failed := TRUE; END;
    IF NOT v_failed THEN RAISE EXCEPTION 'Se permitió mutar una versión documental'; END IF;
END;
$relations$;

DO $seed_contract$
DECLARE
    v_project INTEGER := (SELECT id_proyecto FROM proyecto WHERE clave_proyecto = 'MEX-QRO');
BEGIN
    IF (SELECT COUNT(*) FROM proyecto) <> 2 OR (SELECT COUNT(*) FROM proyecto_nucleo) <> 5
       OR (SELECT COUNT(*) FROM parcela) <> 4 OR (SELECT COUNT(*) FROM afectacion) <> 10
       OR (SELECT COUNT(*) FROM asamblea) <> 3 OR (SELECT COUNT(*) FROM convenio) <> 9
       OR (SELECT COUNT(*) FROM convenio_afectacion) <> 11
       OR (SELECT COUNT(*) FROM tramite_fifonafe) <> 2
       OR (SELECT COUNT(*) FROM tramite_fifonafe_afectacion) <> 6
       OR (SELECT COUNT(*) FROM indemnizacion) <> 1 OR (SELECT COUNT(*) FROM pago) <> 2
       OR (SELECT COUNT(*) FROM documento) <> 3 OR (SELECT COUNT(*) FROM documento_version) <> 1
       OR (SELECT COUNT(*) FROM trazabilidad_fuente) <> 14 THEN
        RAISE EXCEPTION 'Conteos del seed distintos del contrato';
    END IF;
    IF EXISTS (SELECT 1 FROM proyecto_nucleo pn JOIN proyecto p USING(id_proyecto) WHERE p.clave_proyecto='QRO-IRA') THEN RAISE EXCEPTION 'Proyecto vacío QRO-IRA dejó de estar vacío'; END IF;
    IF (SELECT COUNT(*) FROM vw_dashboard_kpi WHERE id_proyecto=v_project AND anio=2025) <> 24 THEN RAISE EXCEPTION 'KPI esperados: 24 filas'; END IF;
    IF NOT EXISTS (SELECT 1 FROM vw_dashboard_kpi WHERE id_proyecto=v_project AND anio=2025 AND indicador='nucleos' AND cantidad=5)
       OR NOT EXISTS (SELECT 1 FROM vw_dashboard_kpi WHERE id_proyecto=v_project AND anio=2025 AND indicador='sensibilizacion' AND programado=2 AND realizado=2 AND cantidad=3)
       OR NOT EXISTS (SELECT 1 FROM vw_dashboard_kpi WHERE id_proyecto=v_project AND anio=2025 AND indicador='caminamiento' AND programado=2 AND realizado=2 AND cantidad=2)
       OR NOT EXISTS (SELECT 1 FROM vw_dashboard_kpi WHERE id_proyecto=v_project AND anio=2025 AND indicador='asambleas' AND cantidad=3)
       OR NOT EXISTS (SELECT 1 FROM vw_dashboard_kpi WHERE id_proyecto=v_project AND anio=2025 AND indicador='cop_colectivos' AND cantidad=2)
       OR NOT EXISTS (SELECT 1 FROM vw_dashboard_kpi WHERE id_proyecto=v_project AND anio=2025 AND indicador='cop_individuales' AND cantidad=2)
       OR NOT EXISTS (SELECT 1 FROM vw_dashboard_kpi WHERE id_proyecto=v_project AND anio=2025 AND indicador='fifonafe' AND cantidad=2)
       OR NOT EXISTS (SELECT 1 FROM vw_dashboard_kpi WHERE id_proyecto=v_project AND anio=2025 AND indicador='no_conflictos' AND cantidad=2)
       OR NOT EXISTS (SELECT 1 FROM vw_dashboard_kpi WHERE id_proyecto=v_project AND anio=2025 AND indicador='pagos' AND cantidad=2 AND monto=2800000.00)
       OR NOT EXISTS (SELECT 1 FROM vw_dashboard_kpi WHERE id_proyecto=v_project AND anio=2025 AND indicador='superficie_afectada_administrativa' AND superficie_ha=30.043549) THEN
        RAISE EXCEPTION 'Valores KPI del seed distintos del contrato';
    END IF;
    IF (SELECT cantidad FROM vw_dashboard_kpi WHERE id_proyecto=v_project AND anio=2025 AND indicador='cop_colectivos') <> (SELECT COUNT(*) FROM convenio WHERE id_proyecto_nucleo IN (SELECT id_proyecto_nucleo FROM proyecto_nucleo WHERE id_proyecto=v_project) AND ambito='colectivo' AND tipo_convenio='cop_original' AND activo) THEN RAISE EXCEPTION 'N:M duplicó COP colectivos'; END IF;
    IF (SELECT cantidad FROM vw_dashboard_kpi WHERE id_proyecto=v_project AND anio=2025 AND indicador='fifonafe') <> (SELECT COUNT(*) FROM tramite_fifonafe WHERE id_proyecto_nucleo IN (SELECT id_proyecto_nucleo FROM proyecto_nucleo WHERE id_proyecto=v_project) AND activo) THEN RAISE EXCEPTION 'N:M duplicó FIFONAFE'; END IF;
END;
$seed_contract$;

ROLLBACK;
\echo 'CONTRATO SQL 031-033 Y SEED: OK'
