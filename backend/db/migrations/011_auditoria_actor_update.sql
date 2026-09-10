-- Require an actor for every non-system UPDATE, including secret-only changes.
SET search_path = public, pg_catalog;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM schema_migrations
    WHERE version = '010'
      AND checksum_sha256 = '5673767c9a24325a17ac323ed8fbfce5241dd205fd41ffccfee644709c6c6668'
  ) THEN
    RAISE EXCEPTION '011 requiere la migración 010 exacta';
  END IF;
  IF EXISTS (SELECT 1 FROM schema_migrations WHERE version = '011') THEN
    RAISE EXCEPTION '011 ya se encuentra registrada';
  END IF;
END $$;

SELECT pg_advisory_xact_lock(hashtextextended('software-pa:011:auditoria-actor-update', 0));

CREATE OR REPLACE FUNCTION public.fn_audit_log() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
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
    v_system_event_id := current_setting('app.auth_system_event_id', TRUE);
    IF TG_TABLE_NAME = 'sesion_usuario'
       AND TG_OP = 'UPDATE'
       AND NULLIF(v_system_event_id, '') IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM evento_acceso
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
            SELECT c.id_proyecto_nucleo INTO v_pn FROM convenio c WHERE c.id_convenio = (v_row ->> 'id_convenio')::INTEGER;
        ELSIF TG_TABLE_NAME = 'indemnizacion' THEN
            SELECT a.id_proyecto_nucleo INTO v_pn FROM afectacion a WHERE a.id_afectacion = (v_row ->> 'id_afectacion')::INTEGER;
        ELSE
            SELECT a.id_proyecto_nucleo INTO v_pn
            FROM indemnizacion i JOIN afectacion a ON a.id_afectacion = i.id_afectacion
            WHERE i.id_indemnizacion = (v_row ->> 'id_indemnizacion')::INTEGER;
        END IF;
    END IF;
    IF v_pn IS NOT NULL THEN
        SELECT pn.id_proyecto, pn.id_nucleo INTO v_project, v_nucleo
        FROM proyecto_nucleo pn WHERE pn.id_proyecto_nucleo = v_pn;
    END IF;

    INSERT INTO bitacora (
        id_usuario, id_proyecto, id_proyecto_nucleo, id_nucleo,
        entidad_tipo, entidad_id, accion, valor_anterior, valor_nuevo
    ) VALUES (
        v_user_id, v_project, v_pn, v_nucleo,
        TG_TABLE_NAME, v_id, lower(TG_OP), v_old, v_new
    );
    RETURN COALESCE(NEW, OLD);
END;
$$;
