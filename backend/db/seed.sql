-- Minimal canonical development seed for SOFTWARE-PA baseline v1.
-- Prerequisites: migration 001, territorial fixture and one active admin.
-- No credentials or legacy projections are created here.

DO $$
DECLARE
    v_actor integer;
    v_municipio integer;
    v_tenencia bigint;
    v_residencia bigint;
    v_tipo_tierra bigint;
    v_tipo_gestion bigint;
    v_destino bigint;
    v_titularidad bigint;
    v_tipo_asamblea bigint;
    v_contexto_asamblea bigint;
    v_resultado_convocatoria bigint;
    v_evento_ran bigint;
    v_evento_fifonafe bigint;
    v_proyecto integer;
    v_nucleo integer;
    v_pn integer;
    v_parcela integer;
    v_persona integer;
    v_parcela_titular integer;
    v_unidad bigint;
    v_afectacion integer;
    v_asamblea integer;
    v_tramite_ran bigint;
    v_fifonafe integer;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations
        WHERE version='001' AND nombre='baseline_v1'
          AND checksum_sha256 ~ '^[0-9a-f]{64}$'
    ) THEN
        RAISE EXCEPTION 'El seed requiere el baseline v1 registrado como 001';
    END IF;

    SELECT id_usuario INTO v_actor FROM usuario
     WHERE activo AND rol='admin' ORDER BY id_usuario LIMIT 1;
    SELECT id_municipio INTO v_municipio FROM municipio
     WHERE activo ORDER BY id_municipio LIMIT 1;
    IF v_actor IS NULL OR v_municipio IS NULL THEN
        RAISE EXCEPTION 'El seed requiere un administrador y el fixture territorial';
    END IF;

    IF EXISTS (SELECT 1 FROM proyecto WHERE clave_proyecto='BASELINE-V1-DEMO') THEN
        RAISE NOTICE 'El seed canónico ya fue aplicado';
        RETURN;
    END IF;

    PERFORM set_config('app.current_user_id', v_actor::text, true);
    SELECT id_catalogo_opcion INTO v_tenencia FROM catalogo_operativo
     WHERE tipo_catalogo='tipo_tenencia' AND codigo='ejido' AND activo;
    SELECT id_catalogo_opcion INTO v_residencia FROM catalogo_operativo
     WHERE tipo_catalogo='residencia' AND codigo='queretaro' AND activo;
    SELECT id_catalogo_opcion INTO v_tipo_tierra FROM catalogo_operativo
     WHERE tipo_catalogo='tipo_tierra' AND codigo='parcelada' AND activo;
    SELECT id_catalogo_opcion INTO v_tipo_gestion FROM catalogo_operativo
     WHERE tipo_catalogo='tipo_gestion' AND codigo='PARCELA' AND activo;
    SELECT id_catalogo_opcion INTO v_destino FROM catalogo_operativo
     WHERE tipo_catalogo='destino_superficie' AND codigo='parcela_ejidal' AND activo;
    SELECT id_catalogo_opcion INTO v_titularidad FROM catalogo_operativo
     WHERE tipo_catalogo='tipo_titularidad_unidad' AND codigo='persona' AND activo;
    SELECT id_catalogo_opcion INTO v_tipo_asamblea FROM catalogo_operativo
     WHERE tipo_catalogo='tipo_asamblea' AND codigo='anuencia' AND activo;
    SELECT id_catalogo_opcion INTO v_contexto_asamblea FROM catalogo_operativo
     WHERE tipo_catalogo='contexto_asamblea' AND codigo='cop_original' AND activo;
    SELECT id_catalogo_opcion INTO v_resultado_convocatoria FROM catalogo_operativo
     WHERE tipo_catalogo='resultado_convocatoria' AND codigo='celebrada' AND activo;
    SELECT id_catalogo_opcion INTO v_evento_ran FROM catalogo_operativo
     WHERE tipo_catalogo='tipo_evento_ran' AND codigo='ingreso' AND activo;
    SELECT id_catalogo_opcion INTO v_evento_fifonafe FROM catalogo_operativo
     WHERE tipo_catalogo='tipo_evento_fifonafe' AND codigo='oficio_fifonafe_dgaopr' AND activo;

    INSERT INTO proyecto(clave_proyecto,nombre_proyecto,fecha_inicio,creado_por,observaciones)
    VALUES('BASELINE-V1-DEMO','Proyecto demostrativo baseline v1',CURRENT_DATE,v_actor,
           'Seed mínimo canónico') RETURNING id_proyecto INTO v_proyecto;
    INSERT INTO nucleo_agrario(id_municipio,nombre_nucleo,id_tipo_tenencia,fuente_datos,creado_por)
    VALUES(v_municipio,'Núcleo demostrativo baseline v1',v_tenencia,'seed_baseline_v1',v_actor)
    RETURNING id_nucleo INTO v_nucleo;
    INSERT INTO proyecto_nucleo(id_proyecto,id_nucleo,id_residencia,creado_por)
    VALUES(v_proyecto,v_nucleo,v_residencia,v_actor) RETURNING id_proyecto_nucleo INTO v_pn;
    INSERT INTO proyecto_nucleo_responsable(
        id_proyecto_nucleo,nombre,cargo,contacto,es_principal,creado_por
    ) VALUES(v_pn,'Responsable demostrativo','Enlace','sin contacto',true,v_actor);
    INSERT INTO proyecto_nucleo_referencia(
        id_proyecto_nucleo,tipo_referencia,valor,es_principal,creado_por
    ) VALUES(v_pn,'consecutivo','BASELINE-V1',true,v_actor);

    INSERT INTO parcela(id_nucleo,tipo_parcela,no_parcela,creado_por)
    VALUES(v_nucleo,'individual','DEMO-001',v_actor) RETURNING id_parcela INTO v_parcela;
    INSERT INTO persona(nombre,apellido_paterno,origen_registro,creado_por)
    VALUES('Persona','Demostrativa','qa',v_actor)
    RETURNING id_persona INTO v_persona;
    INSERT INTO parcela_titular(id_parcela,id_persona,tipo_derecho,creado_por)
    VALUES(v_parcela,v_persona,'parcelario',v_actor)
    RETURNING id_parcela_titular INTO v_parcela_titular;
    INSERT INTO unidad_agraria(
        id_nucleo,id_tipo_tierra,id_tipo_gestion,id_destino_superficie,
        id_tipo_titularidad,id_parcela,referencia_alfanumerica,creado_por
    ) VALUES(
        v_nucleo,v_tipo_tierra,v_tipo_gestion,v_destino,v_titularidad,
        v_parcela,'UA-DEMO-001',v_actor
    ) RETURNING id_unidad_agraria INTO v_unidad;
    INSERT INTO unidad_agraria_titular(
        id_unidad_agraria,id_parcela_titular,es_principal,creado_por
    ) VALUES(v_unidad,v_parcela_titular,true,v_actor);

    INSERT INTO afectacion(
        id_proyecto_nucleo,tipo_afectacion,superficie_preliminar_ha,
        superficie_afectada_ha,situacion,creado_por
    ) VALUES(v_pn,'individual',1.250000,1.100000,'demostrativa',v_actor)
    RETURNING id_afectacion INTO v_afectacion;
    INSERT INTO afectacion_unidad_agraria(
        id_afectacion,id_unidad_agraria,superficie_preliminar_ha,
        superficie_afectada_ha,fuente,creado_por
    ) VALUES(v_afectacion,v_unidad,1.000000,0.900000,'seed_baseline_v1',v_actor);

    INSERT INTO asamblea(
        id_proyecto_nucleo,id_tipo_asamblea,id_contexto_asamblea,proposito,creado_por
    ) VALUES(v_pn,v_tipo_asamblea,v_contexto_asamblea,'Demostración canónica',v_actor)
    RETURNING id_asamblea INTO v_asamblea;
    INSERT INTO asamblea_convocatoria(
        id_asamblea,ordinal,fecha_programada,fecha_realizacion,id_resultado,creado_por
    ) VALUES(v_asamblea,1,CURRENT_DATE,CURRENT_DATE,v_resultado_convocatoria,v_actor);
    INSERT INTO tramite_ran(
        id_proyecto_nucleo,id_asamblea,referencia_expediente,creado_por
    ) VALUES(v_pn,v_asamblea,'RAN-DEMO-001',v_actor)
    RETURNING id_tramite_ran INTO v_tramite_ran;
    INSERT INTO tramite_ran_evento(
        id_tramite_ran,ordinal,id_tipo_evento,fecha_evento,numero_solicitud,creado_por
    ) VALUES(v_tramite_ran,1,v_evento_ran,CURRENT_DATE,'SOL-DEMO-001',v_actor);

    INSERT INTO tramite_fifonafe(
        id_proyecto_nucleo,ambito,estatus,hay_conflictos,creado_por
    ) VALUES(v_pn,'individual','pendiente',false,v_actor)
    RETURNING id_tramite_fifonafe INTO v_fifonafe;
    INSERT INTO tramite_fifonafe_afectacion(
        id_tramite_fifonafe,id_afectacion,creado_por
    ) VALUES(v_fifonafe,v_afectacion,v_actor);
    INSERT INTO tramite_fifonafe_evento(
        id_tramite_fifonafe,ordinal,id_tipo_evento,numero_oficio,fecha_oficio,creado_por
    ) VALUES(v_fifonafe,1,v_evento_fifonafe,'OF-DEMO-001',CURRENT_DATE,v_actor);
END;
$$;
