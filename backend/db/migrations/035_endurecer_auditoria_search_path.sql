-- Forward-only audit namespace hardening. Historical SQL and ACL stay unchanged.
SET search_path = pg_catalog, public, pg_temp;

SELECT pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended('software-pa:035:endurecer-auditoria-search-path', 0)
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.schema_migrations
        WHERE version = '034' AND nombre = 'seguimiento_fifonafe_etiquetas'
          AND checksum_sha256 = '75e07a23e96da26d1a93a5ed90e9a3ad3990a58adc878b50ff9476f659bd1aef'
    ) THEN
        RAISE EXCEPTION '035 requiere la migración 034 exacta';
    END IF;
    IF EXISTS (SELECT 1 FROM public.schema_migrations WHERE version = '035') THEN
        RAISE EXCEPTION '035 ya se encuentra registrada';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_proc p
        WHERE p.oid = pg_catalog.to_regprocedure('public.fn_audit_log()')
          AND p.prosecdef AND p.prorettype = 'pg_catalog.trigger'::pg_catalog.regtype
          AND pg_catalog.has_table_privilege(p.proowner, 'public.bitacora', 'INSERT')
    ) THEN
        RAISE EXCEPTION '035 requiere fn_audit_log SECURITY DEFINER y su owner con INSERT en public.bitacora';
    END IF;
    -- Fail closed instead of changing global schema or TEMP grants.
    IF pg_catalog.has_schema_privilege('software_pa_app', 'public', 'CREATE') THEN
        RAISE EXCEPTION '035 requiere public no escribible por software_pa_app';
    END IF;
END $$;

-- Same 020 actor/secret/heartbeat/system-event semantics. Qualify every stored
-- relation and search built-ins first; pg_temp remains available but searched last.
CREATE OR REPLACE FUNCTION public.fn_audit_log() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path = pg_catalog, public, pg_temp
    AS $$
DECLARE
    v_row JSONB;
    v_old JSONB;
    v_new JSONB;
    v_id BIGINT;
    v_user_id INTEGER;
    v_pn INTEGER;
    v_project INTEGER;
    v_nucleo INTEGER;
    v_system_event_id TEXT;
BEGIN
    IF TG_TABLE_SCHEMA <> 'public' THEN
        RAISE EXCEPTION 'Auditoría sólo admite relaciones de public';
    END IF;
    v_system_event_id := current_setting('app.auth_system_event_id', TRUE);
    IF TG_TABLE_NAME = 'sesion_usuario'
       AND TG_OP = 'UPDATE'
       AND NULLIF(v_system_event_id, '') IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM public.evento_acceso
            WHERE id_evento = v_system_event_id::BIGINT
              AND id_sesion = NEW.id_sesion
              AND id_usuario = NEW.id_usuario
              AND id_usuario_actor IS NULL
              AND tipo_evento = 'sesion_expirada'
              AND motivo_codigo = NEW.motivo_revocacion
              AND motivo_codigo IN ('expiracion_inactividad', 'expiracion_absoluta')
              AND txid_registro = txid_current()
        ) OR OLD.revocada_en IS NOT NULL
          OR NEW.revocada_en IS NULL
          OR NEW.id_usuario_revoca IS NOT NULL
          OR to_jsonb(NEW) - ARRAY['revocada_en','id_usuario_revoca','motivo_revocacion']
             IS DISTINCT FROM
             to_jsonb(OLD) - ARRAY['revocada_en','id_usuario_revoca','motivo_revocacion'] THEN
            RAISE EXCEPTION 'Expiración de sesión sin evento de sistema correlacionado o con cambios no permitidos';
        END IF;
        RETURN NEW;
    END IF;

    IF TG_OP = 'INSERT' THEN
        v_new := to_jsonb(NEW) - ARRAY['contrasena_hash', 'token_hash', 'csrf_hash'];
        v_row := v_new;
    ELSIF TG_OP = 'UPDATE' THEN
        -- This check deliberately precedes the secret-only no-op return.
        v_user_id := NULLIF(current_setting('app.current_user_id', TRUE), '')::INTEGER;
        IF v_user_id IS NULL THEN
            RAISE EXCEPTION 'Auditoría fallida: falta app.current_user_id en la transacción';
        END IF;
        -- Ordinary activity is exempt only after actor validation. Compare the
        -- complete rows so simultaneous changes, including secrets, are audited.
        IF TG_TABLE_NAME = 'sesion_usuario'
           AND to_jsonb(OLD) - 'ultima_actividad'
               IS NOT DISTINCT FROM to_jsonb(NEW) - 'ultima_actividad' THEN
            RETURN NEW;
        END IF;
        v_old := to_jsonb(OLD) - ARRAY['contrasena_hash', 'token_hash', 'csrf_hash'];
        v_new := to_jsonb(NEW) - ARRAY['contrasena_hash', 'token_hash', 'csrf_hash'];
        IF v_old IS NOT DISTINCT FROM v_new THEN
            RETURN NEW;
        END IF;
        v_row := v_new;
    ELSE
        v_old := to_jsonb(OLD) - ARRAY['contrasena_hash', 'token_hash', 'csrf_hash'];
        v_row := v_old;
    END IF;

    IF TG_OP <> 'UPDATE' THEN
        v_user_id := NULLIF(current_setting('app.current_user_id', TRUE), '')::INTEGER;
        IF v_user_id IS NULL THEN
            RAISE EXCEPTION 'Auditoría fallida: falta app.current_user_id en la transacción';
        END IF;
    END IF;
    v_id := NULLIF(v_row ->> TG_ARGV[0], '')::BIGINT;
    v_pn := NULLIF(v_row ->> 'id_proyecto_nucleo', '')::INTEGER;
    v_project := NULLIF(v_row ->> 'id_proyecto', '')::INTEGER;
    v_nucleo := NULLIF(v_row ->> 'id_nucleo', '')::INTEGER;

    IF TG_TABLE_NAME = 'proyecto' THEN v_project := v_id::INTEGER; END IF;
    IF TG_TABLE_NAME = 'proyecto_nucleo' THEN v_pn := v_id::INTEGER; END IF;
    IF TG_TABLE_NAME = 'nucleo_agrario' THEN v_nucleo := v_id::INTEGER; END IF;

    IF v_pn IS NULL AND TG_TABLE_NAME IN ('convenio_afectacion', 'indemnizacion', 'pago') THEN
        IF TG_TABLE_NAME = 'convenio_afectacion' THEN
            SELECT c.id_proyecto_nucleo INTO v_pn FROM public.convenio c WHERE c.id_convenio = (v_row ->> 'id_convenio')::INTEGER;
        ELSIF TG_TABLE_NAME = 'indemnizacion' THEN
            SELECT a.id_proyecto_nucleo INTO v_pn FROM public.afectacion a WHERE a.id_afectacion = (v_row ->> 'id_afectacion')::INTEGER;
        ELSE
            SELECT a.id_proyecto_nucleo INTO v_pn
            FROM public.indemnizacion i JOIN public.afectacion a ON a.id_afectacion = i.id_afectacion
            WHERE i.id_indemnizacion = (v_row ->> 'id_indemnizacion')::INTEGER;
        END IF;
    END IF;
    IF v_pn IS NOT NULL THEN
        SELECT pn.id_proyecto, pn.id_nucleo INTO v_project, v_nucleo
        FROM public.proyecto_nucleo pn WHERE pn.id_proyecto_nucleo = v_pn;
    END IF;

    INSERT INTO public.bitacora (
        id_usuario, id_proyecto, id_proyecto_nucleo, id_nucleo,
        entidad_tipo, entidad_id, accion, valor_anterior, valor_nuevo
    ) VALUES (
        v_user_id, v_project, v_pn, v_nucleo,
        TG_TABLE_NAME, v_id, lower(TG_OP), v_old, v_new
    );
    RETURN COALESCE(NEW, OLD);
END;
$$;
