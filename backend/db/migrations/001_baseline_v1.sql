-- SOFTWARE-PA canonical baseline v1.
-- Installs a new empty development database directly at the current model.
-- Historical migrations 001-039 are intentionally not replayed.

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: fn_auth_inicializar_estado_usuario(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_auth_inicializar_estado_usuario() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO estado_autenticacion_usuario(id_usuario)
    VALUES (NEW.id_usuario)
    ON CONFLICT (id_usuario) DO NOTHING;
    RETURN NEW;
END;
$$;


--
-- Name: fn_auth_prevent_event_change(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_auth_prevent_event_change() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'Los eventos de acceso son inmutables';
END;
$$;


--
-- Name: fn_auth_revocar_sesiones_usuario_inactivo(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_auth_revocar_sesiones_usuario_inactivo() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_actor TEXT;
    v_sesion RECORD;
BEGIN
    IF OLD.activo = TRUE AND NEW.activo = FALSE THEN
        v_actor := current_setting('app.current_user_id', true);
        IF v_actor IS NULL OR v_actor = '' THEN
            RAISE EXCEPTION
                'La baja de usuario requiere actor para revocar sesiones';
        END IF;
        FOR v_sesion IN
            UPDATE sesion_usuario
               SET revocada_en = NOW(),
                   id_usuario_revoca = v_actor::INTEGER,
                   motivo_revocacion = 'usuario_inactivo'
             WHERE id_usuario = NEW.id_usuario
               AND revocada_en IS NULL
            RETURNING id_sesion
        LOOP
            INSERT INTO evento_acceso (
                id_usuario, id_usuario_actor, id_sesion,
                tipo_evento, motivo_codigo
            ) VALUES (
                NEW.id_usuario, v_actor::INTEGER, v_sesion.id_sesion,
                'sesion_revocada', 'usuario_inactivo'
            );
        END LOOP;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_auth_validar_estado_evento(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_auth_validar_estado_evento() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_event_id TEXT;
BEGIN
    v_event_id := current_setting('app.auth_event_id', true);
    IF v_event_id IS NULL OR v_event_id = '' OR NOT EXISTS (
        SELECT 1
          FROM evento_acceso
         WHERE id_evento = v_event_id::BIGINT
           AND id_usuario = NEW.id_usuario
           AND txid_registro = txid_current()
    ) THEN
        RAISE EXCEPTION
            'Estado de autenticacion sin evento correlacionado en la transaccion';
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_validar_administrador_activo(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_administrador_activo() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF OLD.activo AND OLD.rol = 'admin'
       AND (NEW.activo IS FALSE OR NEW.rol <> 'admin') THEN
        PERFORM pg_advisory_xact_lock(hashtext('software_pa_active_admin'));
        IF NOT EXISTS (
            SELECT 1 FROM usuario
             WHERE activo AND rol = 'admin' AND id_usuario <> OLD.id_usuario
        ) THEN
            RAISE EXCEPTION 'ADM_ULTIMO_ADMIN_ACTIVO';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_catalogo_alias_no_delete(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_catalogo_alias_no_delete() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'Los aliases de catálogo no admiten DELETE físico; desactive el alias';
END;
$$;


--
-- Name: fn_catalogo_inmutable(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_catalogo_inmutable() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Los catálogos no admiten DELETE físico; desactive la opción';
    END IF;
    IF NEW.tipo_catalogo IS DISTINCT FROM OLD.tipo_catalogo
       OR NEW.codigo IS DISTINCT FROM OLD.codigo THEN
        RAISE EXCEPTION 'El tipo y código estable de catálogo son inmutables';
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_opcion_catalogo_valida(bigint, text, boolean); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_opcion_catalogo_valida(p_id bigint, p_tipo text, p_permitir_inactiva boolean DEFAULT true) RETURNS boolean
    LANGUAGE sql STABLE
    AS $$
    SELECT p_id IS NULL OR EXISTS (
        SELECT 1 FROM catalogo_operativo c
        WHERE c.id_catalogo_opcion = p_id
          AND c.tipo_catalogo = p_tipo
          AND (p_permitir_inactiva OR c.activo)
    );
$$;


--
-- Canonical catalog-domain validation.
--

CREATE FUNCTION public.fn_validar_catalogos_dominio() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_organo TEXT;
    v_cargo TEXT;
BEGIN
    IF TG_TABLE_NAME='nucleo_agrario' THEN
        IF NOT fn_opcion_catalogo_valida(NEW.id_tipo_tenencia,'tipo_tenencia') THEN
            RAISE EXCEPTION 'Tipo de tenencia invalido';
        END IF;
    ELSIF TG_TABLE_NAME='proyecto_nucleo' THEN
        IF NEW.id_residencia IS NOT NULL
           AND NOT fn_opcion_catalogo_valida(NEW.id_residencia,'residencia') THEN
            RAISE EXCEPTION 'Residencia invalida';
        END IF;
    ELSIF TG_TABLE_NAME='orv' THEN
        IF NEW.id_estado_registral IS NOT NULL
           AND NOT fn_opcion_catalogo_valida(NEW.id_estado_registral,'estado_registral_orv') THEN
            RAISE EXCEPTION 'Estado registral ORV invalido';
        END IF;
    ELSIF TG_TABLE_NAME='orv_integrante' THEN
        IF NOT fn_opcion_catalogo_valida(NEW.id_organo,'organo_orv')
           OR NOT fn_opcion_catalogo_valida(NEW.id_cargo,'cargo_orv')
           OR NOT fn_opcion_catalogo_valida(NEW.id_calidad,'calidad_integrante_orv') THEN
            RAISE EXCEPTION 'Estructura ORV invalida';
        END IF;
        SELECT codigo INTO v_organo FROM catalogo_operativo WHERE id_catalogo_opcion=NEW.id_organo;
        SELECT codigo INTO v_cargo FROM catalogo_operativo WHERE id_catalogo_opcion=NEW.id_cargo;
        IF (v_organo='comisariado' AND v_cargo NOT IN ('presidente','secretario','tesorero'))
           OR (v_organo='consejo_vigilancia' AND v_cargo NOT IN ('presidente','secretario_1','secretario_2')) THEN
            RAISE EXCEPTION 'Cargo % no pertenece al organo %',v_cargo,v_organo;
        END IF;
    ELSIF TG_TABLE_NAME='tramite_ran_evento' THEN
        IF NOT fn_opcion_catalogo_valida(NEW.id_tipo_evento,'tipo_evento_ran') THEN
            RAISE EXCEPTION 'Tipo de evento RAN invalido';
        END IF;
    ELSIF TG_TABLE_NAME='tramite_fifonafe_evento' THEN
        IF NOT fn_opcion_catalogo_valida(NEW.id_tipo_evento,'tipo_evento_fifonafe') THEN
            RAISE EXCEPTION 'Tipo de evento FIFONAFE invalido';
        END IF;
    ELSIF TG_TABLE_NAME='expediente_requisito' THEN
        IF NOT fn_opcion_catalogo_valida(NEW.id_estado,'estado_requisito_documental') THEN
            RAISE EXCEPTION 'Estado de requisito documental invalido';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

--
-- Name: fn_validar_importacion_celda(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_importacion_celda() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.entidad_id IS NOT NULL AND NOT fn_objetivo_controlado_existe(NEW.entidad_tipo,NEW.entidad_id) THEN
        RAISE EXCEPTION 'Objetivo de celda importada %:% no existe',NEW.entidad_tipo,NEW.entidad_id;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_normalizar_referencia(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_normalizar_referencia(p_valor text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT NULLIF(
        upper(regexp_replace(btrim(COALESCE(p_valor,'')), '[[:space:]]+', ' ', 'g')),
        ''
    );
$$;


--
-- Name: fn_prevenir_delete_fisico(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_prevenir_delete_fisico() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'La tabla % no admite DELETE fisico; utilice baja logica',TG_TABLE_NAME;
END;
$$;


--
-- Name: fn_validar_afectacion_tipo_cop(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_afectacion_tipo_cop() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NOT fn_opcion_catalogo_valida(NEW.id_tipo_cop_operativo,'tipo_cop_operativo') THEN
        RAISE EXCEPTION 'TIPO COP operativo invalido';
    END IF;
    RETURN NEW;
END;
$$;


--
-- Affected units are canonical; Afectacion has no direct parcel pointer.
--

CREATE FUNCTION public.fn_validar_afectacion_unidad() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_nucleo_afectacion INTEGER;
    v_nucleo_unidad INTEGER;
    v_tipo_afectacion TEXT;
    v_parcela_unidad INTEGER;
BEGIN
    SELECT pn.id_nucleo, a.tipo_afectacion
      INTO v_nucleo_afectacion, v_tipo_afectacion
      FROM afectacion a
      JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
     WHERE a.id_afectacion=NEW.id_afectacion AND a.activo AND pn.activo;

    SELECT id_nucleo, id_parcela
      INTO v_nucleo_unidad, v_parcela_unidad
      FROM unidad_agraria
     WHERE id_unidad_agraria=NEW.id_unidad_agraria AND activo;

    IF v_nucleo_afectacion IS NULL OR v_nucleo_unidad IS NULL
       OR v_nucleo_afectacion<>v_nucleo_unidad THEN
        RAISE EXCEPTION 'Afectacion y unidad agraria deben pertenecer al mismo nucleo';
    END IF;
    IF v_tipo_afectacion='individual' AND v_parcela_unidad IS NULL THEN
        RAISE EXCEPTION 'La unidad de una afectacion individual debe referenciar una parcela';
    END IF;
    RETURN NEW;
END;
$$;

--
-- Name: fn_validar_pn_tuc(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_pn_tuc() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_codigo TEXT;
BEGIN
    IF NOT fn_opcion_catalogo_valida(NEW.id_motivo_no_afecta_tuc,'motivo_no_afecta_tuc') THEN
        RAISE EXCEPTION 'Motivo de no afectacion TUC invalido';
    END IF;

    IF NEW.afecta_tuc IS FALSE THEN
        SELECT codigo INTO v_codigo
        FROM catalogo_operativo
        WHERE id_catalogo_opcion=NEW.id_motivo_no_afecta_tuc;
        IF v_codigo='otro' AND NULLIF(btrim(NEW.motivo_no_afecta_tuc_detalle),'') IS NULL THEN
            RAISE EXCEPTION 'El motivo otro requiere detalle';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_validar_unidad_agraria(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_unidad_agraria() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_nucleo_parcela INTEGER;
BEGIN
    IF NOT fn_opcion_catalogo_valida(NEW.id_tipo_tierra,'tipo_tierra')
       OR NOT fn_opcion_catalogo_valida(NEW.id_tipo_gestion,'tipo_gestion')
       OR NOT fn_opcion_catalogo_valida(NEW.id_destino_superficie,'destino_superficie')
       OR NOT fn_opcion_catalogo_valida(NEW.id_tipo_titularidad,'tipo_titularidad_unidad') THEN
        RAISE EXCEPTION 'La unidad agraria contiene catalogos de tipo incorrecto';
    END IF;

    NEW.referencia_normalizada := fn_normalizar_referencia(NEW.referencia_alfanumerica);

    IF NEW.id_parcela IS NOT NULL AND NEW.activo THEN
        SELECT id_nucleo INTO v_nucleo_parcela
        FROM parcela
        WHERE id_parcela=NEW.id_parcela AND activo;
        IF v_nucleo_parcela IS NULL OR v_nucleo_parcela<>NEW.id_nucleo THEN
            RAISE EXCEPTION 'La parcela de la unidad agraria debe pertenecer al mismo nucleo';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_validar_unidad_titular(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_unidad_titular() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_nucleo_unidad INTEGER;
    v_nucleo_parcela INTEGER;
    v_persona_parcela INTEGER;
    v_persona_directa INTEGER;
    v_tipo_titularidad TEXT;
BEGIN
    SELECT u.id_nucleo, c.codigo
      INTO v_nucleo_unidad, v_tipo_titularidad
    FROM unidad_agraria u
    JOIN catalogo_operativo c ON c.id_catalogo_opcion=u.id_tipo_titularidad
    WHERE u.id_unidad_agraria=NEW.id_unidad_agraria AND u.activo;

    IF v_nucleo_unidad IS NULL THEN
        RAISE EXCEPTION 'La unidad agraria titular debe estar activa';
    END IF;
    IF v_tipo_titularidad NOT IN ('persona','copropiedad') THEN
        RAISE EXCEPTION 'Solo unidades con titularidad persona/copropiedad admiten titulares persona';
    END IF;

    IF NEW.id_parcela_titular IS NOT NULL THEN
        SELECT p.id_nucleo, pt.id_persona
          INTO v_nucleo_parcela, v_persona_parcela
        FROM parcela_titular pt
        JOIN parcela p ON p.id_parcela=pt.id_parcela
        WHERE pt.id_parcela_titular=NEW.id_parcela_titular
          AND pt.activo AND p.activo;
        IF v_nucleo_parcela IS NULL OR v_nucleo_parcela<>v_nucleo_unidad THEN
            RAISE EXCEPTION 'ParcelaTitular debe pertenecer al mismo nucleo de la unidad agraria';
        END IF;
    ELSE
        SELECT id_persona INTO v_persona_directa
        FROM persona WHERE id_persona=NEW.id_persona AND activo;
        IF v_persona_directa IS NULL THEN
            RAISE EXCEPTION 'La persona titular debe estar activa';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_tramite_ran_objetivo_inmutable(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_tramite_ran_objetivo_inmutable() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF OLD.id_asamblea IS DISTINCT FROM NEW.id_asamblea
     OR OLD.id_convenio IS DISTINCT FROM NEW.id_convenio
     OR OLD.id_orv IS DISTINCT FROM NEW.id_orv
     OR OLD.id_proyecto_nucleo IS DISTINCT FROM NEW.id_proyecto_nucleo
     OR OLD.id_nucleo IS DISTINCT FROM NEW.id_nucleo THEN
    RAISE EXCEPTION 'Objetivo/contexto TramiteRAN inmutable; cree un nuevo tramite';
  END IF;
  RETURN NEW;
END;
$$;


--
-- Name: fn_validar_fifonafe_completo(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_fifonafe_completo() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF EXISTS(
    SELECT 1 FROM tramite_fifonafe t
    WHERE t.activo AND t.estatus='completo'
      AND 4<>(SELECT count(DISTINCT c.codigo)
        FROM tramite_fifonafe_evento e
        JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento
        WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.activo
          AND c.tipo_catalogo='tipo_evento_fifonafe'
          AND c.codigo IN('oficio_fifonafe_dgaopr','oficio_dgaopr_representacion',
            'respuesta_representacion_dgaopr','respuesta_dgaopr_fifonafe')
          AND NULLIF(btrim(e.numero_oficio),'') IS NOT NULL AND e.fecha_oficio IS NOT NULL)
  ) THEN
    RAISE EXCEPTION 'FIFONAFE completo requiere los cuatro eventos canonicos con numero y fecha';
  END IF;
  RETURN NULL;
END;
$$;


--
-- Name: fn_validar_tramite_ran_contexto(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_tramite_ran_contexto() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE v_pn INTEGER; v_nucleo INTEGER;
BEGIN
  IF NOT NEW.activo THEN RETURN NEW; END IF;
  IF NEW.id_asamblea IS NOT NULL THEN
    SELECT id_proyecto_nucleo INTO v_pn FROM asamblea
    WHERE id_asamblea=NEW.id_asamblea AND activo;
    IF v_pn IS NULL OR NEW.id_proyecto_nucleo IS DISTINCT FROM v_pn OR NEW.id_nucleo IS NOT NULL THEN
      RAISE EXCEPTION 'TramiteRAN de Asamblea debe usar su ProyectoNucleo';
    END IF;
  ELSIF NEW.id_convenio IS NOT NULL THEN
    SELECT id_proyecto_nucleo INTO v_pn FROM convenio
    WHERE id_convenio=NEW.id_convenio AND activo;
    IF v_pn IS NULL OR NEW.id_proyecto_nucleo IS DISTINCT FROM v_pn OR NEW.id_nucleo IS NOT NULL THEN
      RAISE EXCEPTION 'TramiteRAN de Convenio debe usar su ProyectoNucleo';
    END IF;
  ELSIF NEW.id_orv IS NOT NULL THEN
    SELECT id_nucleo INTO v_nucleo FROM orv WHERE id_orv=NEW.id_orv AND activo;
    IF v_nucleo IS NULL OR NEW.id_nucleo IS DISTINCT FROM v_nucleo OR NEW.id_proyecto_nucleo IS NOT NULL THEN
      RAISE EXCEPTION 'TramiteRAN de ORV debe usar su NucleoAgrario';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;


--
-- Name: fn_compareciente_identidad_inmutable(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_compareciente_identidad_inmutable() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF OLD.id_convenio IS DISTINCT FROM NEW.id_convenio
       OR OLD.id_persona IS DISTINCT FROM NEW.id_persona
       OR OLD.id_parcela_titular IS DISTINCT FROM NEW.id_parcela_titular THEN
        RAISE EXCEPTION '039: identidad del compareciente inmutable; cree un nuevo registro y de baja logica al anterior';
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_objetivo_requisito_en_pn(text, bigint, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_objetivo_requisito_en_pn(p_tipo text, p_id bigint, p_pn integer) RETURNS boolean
    LANGUAGE plpgsql STABLE
    AS $$
DECLARE
    v_ok BOOLEAN := FALSE;
BEGIN
    CASE p_tipo
        WHEN 'proyecto_nucleo' THEN
            SELECT EXISTS(
                SELECT 1 FROM proyecto_nucleo pn
                 WHERE pn.id_proyecto_nucleo=p_id AND pn.id_proyecto_nucleo=p_pn AND pn.activo
            ) INTO v_ok;
        WHEN 'afectacion' THEN
            SELECT EXISTS(
                SELECT 1 FROM afectacion a
                 WHERE a.id_afectacion=p_id AND a.id_proyecto_nucleo=p_pn AND a.activo
            ) INTO v_ok;
        WHEN 'parcela' THEN
            SELECT EXISTS(
                SELECT 1 FROM parcela p
                JOIN proyecto_nucleo pn ON pn.id_nucleo=p.id_nucleo
                 WHERE p.id_parcela=p_id AND pn.id_proyecto_nucleo=p_pn AND p.activo AND pn.activo
            ) INTO v_ok;
        WHEN 'parcela_titular' THEN
            SELECT EXISTS(
                SELECT 1 FROM parcela_titular pt
                JOIN parcela p ON p.id_parcela=pt.id_parcela
                JOIN proyecto_nucleo pn ON pn.id_nucleo=p.id_nucleo
                 WHERE pt.id_parcela_titular=p_id AND pn.id_proyecto_nucleo=p_pn
                   AND pt.activo AND p.activo AND pn.activo
            ) INTO v_ok;
        WHEN 'unidad_agraria' THEN
            SELECT EXISTS(
                SELECT 1 FROM unidad_agraria u
                JOIN proyecto_nucleo pn ON pn.id_nucleo=u.id_nucleo
                 WHERE u.id_unidad_agraria=p_id AND pn.id_proyecto_nucleo=p_pn
                   AND u.activo AND pn.activo
            ) INTO v_ok;
        WHEN 'unidad_agraria_titular' THEN
            SELECT EXISTS(
                SELECT 1 FROM unidad_agraria_titular ut
                JOIN unidad_agraria u ON u.id_unidad_agraria=ut.id_unidad_agraria
                JOIN proyecto_nucleo pn ON pn.id_nucleo=u.id_nucleo
                 WHERE ut.id_unidad_titular=p_id AND pn.id_proyecto_nucleo=p_pn
                   AND ut.activo AND u.activo AND pn.activo
            ) INTO v_ok;
        WHEN 'convenio' THEN
            SELECT EXISTS(
                SELECT 1 FROM convenio c
                 WHERE c.id_convenio=p_id AND c.id_proyecto_nucleo=p_pn AND c.activo
            ) INTO v_ok;
        WHEN 'convenio_compareciente' THEN
            SELECT EXISTS(
                SELECT 1 FROM convenio_compareciente cc
                JOIN convenio c ON c.id_convenio=cc.id_convenio
                 WHERE cc.id_compareciente=p_id AND c.id_proyecto_nucleo=p_pn
                   AND cc.activo AND c.activo
            ) INTO v_ok;
        WHEN 'tramite_ran' THEN
            SELECT EXISTS(
                SELECT 1 FROM tramite_ran t
                 WHERE t.id_tramite_ran=p_id AND t.id_proyecto_nucleo=p_pn AND t.activo
            ) INTO v_ok;
        WHEN 'tramite_ran_evento' THEN
            SELECT EXISTS(
                SELECT 1 FROM tramite_ran_evento e
                JOIN tramite_ran t ON t.id_tramite_ran=e.id_tramite_ran
                 WHERE e.id_evento_ran=p_id AND t.id_proyecto_nucleo=p_pn
                   AND e.activo AND t.activo
            ) INTO v_ok;
        WHEN 'tramite_fifonafe' THEN
            SELECT EXISTS(
                SELECT 1 FROM tramite_fifonafe t
                 WHERE t.id_tramite_fifonafe=p_id AND t.id_proyecto_nucleo=p_pn AND t.activo
            ) INTO v_ok;
        WHEN 'tramite_fifonafe_evento' THEN
            SELECT EXISTS(
                SELECT 1 FROM tramite_fifonafe_evento e
                JOIN tramite_fifonafe t ON t.id_tramite_fifonafe=e.id_tramite_fifonafe
                 WHERE e.id_evento_fifonafe=p_id AND t.id_proyecto_nucleo=p_pn
                   AND e.activo AND t.activo
            ) INTO v_ok;
        WHEN 'indemnizacion' THEN
            SELECT EXISTS(
                SELECT 1 FROM indemnizacion i
                JOIN afectacion a ON a.id_afectacion=i.id_afectacion
                 WHERE i.id_indemnizacion=p_id AND a.id_proyecto_nucleo=p_pn
                   AND i.activo AND a.activo
            ) INTO v_ok;
        WHEN 'pago' THEN
            SELECT EXISTS(
                SELECT 1 FROM pago pg
                JOIN indemnizacion i ON i.id_indemnizacion=pg.id_indemnizacion
                JOIN afectacion a ON a.id_afectacion=i.id_afectacion
                 WHERE pg.id_pago=p_id AND a.id_proyecto_nucleo=p_pn
                   AND pg.activo AND i.activo AND a.activo
            ) INTO v_ok;
        ELSE
            v_ok := FALSE;
    END CASE;
    RETURN COALESCE(v_ok,FALSE);
END;
$$;


--
-- Name: fn_validar_actividad_afectacion(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_actividad_afectacion() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_pn INTEGER;
BEGIN
    IF NEW.id_afectacion IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT id_proyecto_nucleo
      INTO v_pn
      FROM afectacion
     WHERE id_afectacion = NEW.id_afectacion
       AND activo;

    IF v_pn IS NULL THEN
        RAISE EXCEPTION '039: la afectacion de la actividad no existe o esta inactiva';
    END IF;
    IF v_pn IS DISTINCT FROM NEW.id_proyecto_nucleo THEN
        RAISE EXCEPTION '039: actividad y afectacion deben pertenecer al mismo ProyectoNucleo';
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_validar_compareciente(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_compareciente() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_ambito VARCHAR(20);
    v_pn INTEGER;
    v_nucleo INTEGER;
    v_persona_titular INTEGER;
    v_nucleo_parcela INTEGER;
    v_titular_inicio DATE;
    v_titular_fin DATE;
    v_fecha_firma DATE;
BEGIN
    IF NOT NEW.activo THEN
        RETURN NEW;
    END IF;

    SELECT c.ambito, c.id_proyecto_nucleo, pn.id_nucleo, c.fecha_firma
      INTO v_ambito, v_pn, v_nucleo, v_fecha_firma
      FROM convenio c
      JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo = c.id_proyecto_nucleo
     WHERE c.id_convenio = NEW.id_convenio
       AND c.activo
       AND pn.activo;

    IF v_pn IS NULL THEN
        RAISE EXCEPTION '039: convenio del compareciente inexistente o inactivo';
    END IF;
    IF v_ambito IS DISTINCT FROM 'individual' THEN
        RAISE EXCEPTION '039: convenio_compareciente queda reservado al ambito individual en esta migracion';
    END IF;

    IF NOT fn_opcion_catalogo_valida(NEW.id_tipo_calidad,'calidad_compareciente_convenio') THEN
        RAISE EXCEPTION '039: calidad de compareciente invalida';
    END IF;
    IF NEW.id_tipo_acreditacion IS NOT NULL
       AND NOT fn_opcion_catalogo_valida(NEW.id_tipo_acreditacion,'tipo_acreditacion_derecho_individual') THEN
        RAISE EXCEPTION '039: tipo de acreditacion individual invalido';
    END IF;

    IF NEW.id_parcela_titular IS NOT NULL THEN
        SELECT pt.id_persona, p.id_nucleo, pt.fecha_inicio, pt.fecha_fin
          INTO v_persona_titular, v_nucleo_parcela, v_titular_inicio, v_titular_fin
          FROM parcela_titular pt
          JOIN parcela p ON p.id_parcela = pt.id_parcela
         WHERE pt.id_parcela_titular = NEW.id_parcela_titular
           AND pt.activo
           AND p.activo;

        IF v_persona_titular IS NULL THEN
            RAISE EXCEPTION '039: ParcelaTitular del compareciente inexistente o inactivo';
        END IF;
        IF v_persona_titular IS DISTINCT FROM NEW.id_persona THEN
            RAISE EXCEPTION '039: ParcelaTitular no pertenece a la persona compareciente';
        END IF;
        IF v_nucleo_parcela IS DISTINCT FROM v_nucleo THEN
            RAISE EXCEPTION '039: la parcela del compareciente no pertenece al NucleoAgrario del ProyectoNucleo';
        END IF;
        IF v_fecha_firma IS NOT NULL
           AND v_titular_inicio IS NOT NULL
           AND v_fecha_firma < v_titular_inicio THEN
            RAISE EXCEPTION '039: la titularidad inicia despues de la fecha de firma del convenio';
        END IF;
        IF v_fecha_firma IS NOT NULL
           AND v_titular_fin IS NOT NULL
           AND v_fecha_firma > v_titular_fin THEN
            RAISE EXCEPTION '039: la titularidad termino antes de la fecha de firma del convenio';
        END IF;
    END IF;

    -- Para firmar un convenio individual debe existir un vínculo de titularidad
    -- o una acreditacion alternativa explicitamente registrada. No se infiere.
    IF NEW.es_firmante
       AND NEW.id_parcela_titular IS NULL
       AND NEW.id_tipo_acreditacion IS NULL THEN
        RAISE EXCEPTION '039: firmante individual requiere ParcelaTitular o acreditacion alternativa';
    END IF;
    IF NEW.es_firmante
       AND NEW.id_parcela_titular IS NULL
       AND NEW.id_tipo_acreditacion IS NOT NULL
       AND NULLIF(btrim(NEW.referencia_acreditacion), '') IS NULL
       AND NOT NEW.requiere_revision THEN
        RAISE EXCEPTION '039: acreditacion alternativa sin referencia debe quedar explicitamente en revision';
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: fn_validar_convenio_compareciente_unidad(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_convenio_compareciente_unidad() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.activo AND NEW.id_parcela_titular IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM convenio_afectacion ca
        JOIN afectacion a ON a.id_afectacion = ca.id_afectacion AND a.activo
        JOIN afectacion_unidad_agraria aua ON aua.id_afectacion = a.id_afectacion AND aua.activo
        JOIN unidad_agraria ua ON ua.id_unidad_agraria = aua.id_unidad_agraria AND ua.activo
        JOIN parcela_titular pt ON pt.id_parcela_titular = NEW.id_parcela_titular AND pt.activo
        WHERE ca.id_convenio = NEW.id_convenio
          AND ca.activo
          AND ua.id_parcela = pt.id_parcela
    ) THEN
        RAISE EXCEPTION '039: ParcelaTitular no corresponde a una UnidadAgraria afectada por el convenio';
    END IF;
    RETURN NULL;
END;
$$;


--
-- Name: fn_validar_convenio_individual_firmado(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_convenio_individual_firmado() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id_convenio INTEGER;
    v_ambito VARCHAR(20);
    v_fecha_firma DATE;
    v_activo BOOLEAN;
BEGIN
    IF TG_TABLE_NAME = 'convenio' THEN
        v_id_convenio := NEW.id_convenio;
        IF TG_OP = 'UPDATE'
           AND OLD.fecha_firma IS NOT DISTINCT FROM NEW.fecha_firma
           AND OLD.ambito IS NOT DISTINCT FROM NEW.ambito
           AND OLD.activo IS NOT DISTINCT FROM NEW.activo THEN
            RETURN NULL;
        END IF;
    ELSE
        v_id_convenio := NEW.id_convenio;
    END IF;

    SELECT ambito, fecha_firma, activo
      INTO v_ambito, v_fecha_firma, v_activo
      FROM convenio
     WHERE id_convenio = v_id_convenio;

    IF NOT COALESCE(v_activo,FALSE)
       OR v_ambito IS DISTINCT FROM 'individual'
       OR v_fecha_firma IS NULL THEN
        RETURN NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM convenio_afectacion ca
          JOIN afectacion a ON a.id_afectacion = ca.id_afectacion
         WHERE ca.id_convenio = v_id_convenio
           AND ca.activo
           AND a.activo
           AND a.tipo_afectacion = 'individual'
    ) THEN
        RAISE EXCEPTION '039: convenio individual firmado requiere al menos una afectacion individual activa';
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM convenio_compareciente cc
         WHERE cc.id_convenio = v_id_convenio
           AND cc.activo
           AND cc.es_firmante
    ) THEN
        RAISE EXCEPTION '039: convenio individual firmado requiere al menos un firmante acreditado';
    END IF;

    RETURN NULL;
END;
$$;


--
-- Every requirement names its canonical concrete target.
--

CREATE FUNCTION public.fn_validar_expediente_requisito_objetivo() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NOT fn_objetivo_requisito_en_pn(
        NEW.entidad_tipo, NEW.entidad_id, NEW.id_proyecto_nucleo
    ) THEN
        RAISE EXCEPTION 'Objetivo documental %:% no pertenece al ProyectoNucleo %',
            NEW.entidad_tipo, NEW.entidad_id, NEW.id_proyecto_nucleo;
    END IF;
    RETURN NEW;
END;
$$;

--
-- Name: fn_validar_linaje_convenio_individual(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_linaje_convenio_individual() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_padre convenio%ROWTYPE;
    v_cycle BOOLEAN := FALSE;
BEGIN
    IF NOT NEW.activo OR NEW.ambito IS DISTINCT FROM 'individual' THEN
        RETURN NEW;
    END IF;

    -- En tierras parceladas el consentimiento/comparecencia es individual;
    -- no se usa asamblea como autorizacion del instrumento individual.
    IF NEW.id_asamblea_autorizacion IS NOT NULL THEN
        RAISE EXCEPTION '039: convenio individual no debe usar Asamblea como autorizacion';
    END IF;

    IF NEW.tipo_instrumento = 'convenio' THEN
        IF NEW.tipo_convenio NOT IN ('cop_original','modificatorio','ampliacion','ampliacion_remanente') THEN
            RAISE EXCEPTION '039: tipo de convenio % no corresponde al flujo individual', NEW.tipo_convenio;
        END IF;

        IF NEW.tipo_convenio = 'cop_original' AND NEW.id_convenio_padre IS NOT NULL THEN
            RAISE EXCEPTION '039: cop_original individual no debe tener convenio padre';
        END IF;

        IF NEW.tipo_convenio IN ('modificatorio','ampliacion','ampliacion_remanente')
           AND NEW.id_convenio_padre IS NULL THEN
            RAISE EXCEPTION '039: % individual requiere convenio padre', NEW.tipo_convenio;
        END IF;

        IF NEW.id_convenio_padre IS NOT NULL THEN
            IF NEW.id_convenio IS NOT NULL AND NEW.id_convenio_padre = NEW.id_convenio THEN
                RAISE EXCEPTION '039: un convenio no puede ser su propio padre';
            END IF;

            SELECT * INTO v_padre
              FROM convenio
             WHERE id_convenio = NEW.id_convenio_padre
               AND activo;

            IF NOT FOUND THEN
                RAISE EXCEPTION '039: convenio padre inexistente o inactivo';
            END IF;
            IF v_padre.id_proyecto_nucleo IS DISTINCT FROM NEW.id_proyecto_nucleo
               OR v_padre.ambito IS DISTINCT FROM 'individual'
               OR v_padre.tipo_instrumento IS DISTINCT FROM 'convenio' THEN
                RAISE EXCEPTION '039: convenio padre debe compartir ProyectoNucleo, ambito individual y ser un convenio';
            END IF;

            -- La fuente identifica ampliacion y remanente como instrumentos del mismo
            -- expediente/parcelario, pero no establece una regla juridica fiable sobre
            -- el TIPO del padre directo. No se inventa esa restriccion.

            IF NEW.id_convenio IS NOT NULL THEN
                WITH RECURSIVE ancestros AS (
                    SELECT c.id_convenio, c.id_convenio_padre
                      FROM convenio c
                     WHERE c.id_convenio = NEW.id_convenio_padre
                    UNION ALL
                    SELECT p.id_convenio, p.id_convenio_padre
                      FROM convenio p
                      JOIN ancestros a ON p.id_convenio = a.id_convenio_padre
                     WHERE p.id_convenio_padre IS NOT NULL
                )
                SELECT EXISTS(
                    SELECT 1 FROM ancestros WHERE id_convenio = NEW.id_convenio
                ) INTO v_cycle;

                IF v_cycle THEN
                    RAISE EXCEPTION '039: el linaje de convenio no puede contener ciclos';
                END IF;
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: fn_validar_linaje_unidad_individual(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_linaje_unidad_individual() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id_convenio INTEGER;
    v_padre INTEGER;
    v_ambito VARCHAR(20);
    v_activo BOOLEAN;
BEGIN
    v_id_convenio := NEW.id_convenio;

    SELECT id_convenio_padre, ambito, activo
      INTO v_padre, v_ambito, v_activo
      FROM convenio
     WHERE id_convenio = v_id_convenio;

    IF NOT COALESCE(v_activo,FALSE)
       OR v_ambito IS DISTINCT FROM 'individual'
       OR v_padre IS NULL THEN
        RETURN NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM convenio_afectacion ca_hijo
          JOIN afectacion_unidad_agraria au_hijo
            ON au_hijo.id_afectacion = ca_hijo.id_afectacion
           AND au_hijo.activo
          JOIN convenio_afectacion ca_padre
            ON ca_padre.id_convenio = v_padre
           AND ca_padre.activo
          JOIN afectacion_unidad_agraria au_padre
            ON au_padre.id_afectacion = ca_padre.id_afectacion
           AND au_padre.id_unidad_agraria = au_hijo.id_unidad_agraria
           AND au_padre.activo
         WHERE ca_hijo.id_convenio = v_id_convenio
           AND ca_hijo.activo
    ) THEN
        RAISE EXCEPTION '039: convenio individual hijo debe compartir al menos una UnidadAgraria con su convenio padre';
    END IF;

    RETURN NULL;
END;
$$;


--
-- Name: fn_audit_log(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_audit_log() RETURNS trigger
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
        v_old := to_jsonb(OLD) - ARRAY['contrasena_hash', 'token_hash', 'csrf_hash'];
        v_new := to_jsonb(NEW) - ARRAY['contrasena_hash', 'token_hash', 'csrf_hash'];
        v_row := v_new;
    ELSE
        v_old := to_jsonb(OLD) - ARRAY['contrasena_hash', 'token_hash', 'csrf_hash'];
        v_row := v_old;
    END IF;

    v_user_id := NULLIF(current_setting('app.current_user_id', TRUE), '')::INTEGER;
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Auditoría fallida: falta app.current_user_id en la transacción';
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


--
-- Name: fn_auth_prevent_physical_delete(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_auth_prevent_physical_delete() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'Los estados y sesiones de autenticación no admiten DELETE físico';
END;
$$;


--
-- Name: fn_convenio_requiere_afectacion(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_convenio_requiere_afectacion() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id INTEGER := CASE WHEN TG_TABLE_NAME = 'convenio' THEN NEW.id_convenio ELSE NEW.id_convenio END;
BEGIN
    IF EXISTS (SELECT 1 FROM convenio WHERE id_convenio = v_id AND activo)
       AND NOT EXISTS (SELECT 1 FROM convenio_afectacion WHERE id_convenio = v_id AND activo) THEN
        RAISE EXCEPTION 'Un convenio activo requiere al menos una afectación activa asociada';
    END IF;
    RETURN NULL;
END;
$$;


--
-- Name: fn_documento_version_inmutable(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_documento_version_inmutable() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'Las versiones documentales son inmutables';
END;
$$;


--
-- Name: fn_fifonafe_requiere_afectacion(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_fifonafe_requiere_afectacion() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id INTEGER := NEW.id_tramite_fifonafe;
BEGIN
    IF EXISTS (SELECT 1 FROM tramite_fifonafe WHERE id_tramite_fifonafe = v_id AND activo)
       AND NOT EXISTS (SELECT 1 FROM tramite_fifonafe_afectacion WHERE id_tramite_fifonafe = v_id AND activo) THEN
        RAISE EXCEPTION 'Un trámite FIFONAFE activo requiere al menos una afectación activa asociada';
    END IF;
    RETURN NULL;
END;
$$;


--
-- Polymorphic target existence validation for controlled tables.
--

CREATE FUNCTION public.fn_objetivo_controlado_existe(p_tipo text, p_id bigint) RETURNS boolean
    LANGUAGE plpgsql STABLE
    AS $_$
DECLARE v_pk TEXT; v_exists BOOLEAN;
BEGIN
    v_pk := CASE p_tipo
        WHEN 'proyecto' THEN 'id_proyecto' WHEN 'proyecto_nucleo' THEN 'id_proyecto_nucleo'
        WHEN 'proyecto_nucleo_referencia' THEN 'id_referencia' WHEN 'proyecto_nucleo_responsable' THEN 'id_responsable'
        WHEN 'nucleo_agrario' THEN 'id_nucleo' WHEN 'persona' THEN 'id_persona'
        WHEN 'orv' THEN 'id_orv' WHEN 'orv_integrante' THEN 'id_orv_integrante'
        WHEN 'padron_historial' THEN 'id_padron' WHEN 'parcela' THEN 'id_parcela'
        WHEN 'parcela_titular' THEN 'id_parcela_titular' WHEN 'actividad_campo' THEN 'id_actividad'
        WHEN 'afectacion' THEN 'id_afectacion'
        WHEN 'unidad_agraria' THEN 'id_unidad_agraria'
        WHEN 'unidad_agraria_titular' THEN 'id_unidad_titular'
        WHEN 'afectacion_unidad_agraria' THEN 'id_afectacion_unidad'
        WHEN 'asamblea' THEN 'id_asamblea' WHEN 'asamblea_convocatoria' THEN 'id_convocatoria'
        WHEN 'convenio' THEN 'id_convenio' WHEN 'convenio_compareciente' THEN 'id_compareciente'
        WHEN 'tramite_ran' THEN 'id_tramite_ran' WHEN 'tramite_ran_evento' THEN 'id_evento_ran'
        WHEN 'tramite_fifonafe' THEN 'id_tramite_fifonafe'
        WHEN 'tramite_fifonafe_evento' THEN 'id_evento_fifonafe'
        WHEN 'indemnizacion' THEN 'id_indemnizacion' WHEN 'pago' THEN 'id_pago'
        WHEN 'documento' THEN 'id_documento' WHEN 'expediente_requisito' THEN 'id_expediente_requisito'
        WHEN 'importacion_tabular' THEN 'id_importacion_tabular' ELSE NULL END;
    IF v_pk IS NULL OR to_regclass('public.'||p_tipo) IS NULL THEN RETURN FALSE; END IF;
    EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I WHERE %I=$1)',p_tipo,v_pk)
       INTO v_exists USING p_id;
    RETURN v_exists;
END;
$_$;

--
-- Name: fn_validar_alias_territorial_objetivo(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_alias_territorial_objetivo() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_entidad INTEGER;
BEGIN
    SELECT id_entidad INTO v_entidad FROM municipio WHERE id_municipio = NEW.id_municipio_destino AND activo;
    IF v_entidad IS NULL OR v_entidad <> NEW.id_entidad THEN
        RAISE EXCEPTION 'El municipio destino del alias no pertenece a la entidad indicada';
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_validar_asamblea_padron(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_asamblea_padron() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_nucleo_pn INTEGER;
    v_nucleo_padron INTEGER;
BEGIN
    IF NEW.id_padron IS NOT NULL AND NEW.activo THEN
        SELECT id_nucleo INTO v_nucleo_pn FROM proyecto_nucleo
        WHERE id_proyecto_nucleo = NEW.id_proyecto_nucleo AND activo;
        SELECT id_nucleo INTO v_nucleo_padron FROM padron_historial
        WHERE id_padron = NEW.id_padron AND activo;
        IF v_nucleo_pn IS NULL OR v_nucleo_padron IS NULL OR v_nucleo_pn <> v_nucleo_padron THEN
            RAISE EXCEPTION 'El padrón de la asamblea debe pertenecer al mismo núcleo';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_validar_convenio_afectacion(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_convenio_afectacion() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_convenio convenio%ROWTYPE;
    v_afectacion afectacion%ROWTYPE;
BEGIN
    IF NEW.activo THEN
        SELECT * INTO v_convenio FROM convenio WHERE id_convenio = NEW.id_convenio AND activo;
        SELECT * INTO v_afectacion FROM afectacion WHERE id_afectacion = NEW.id_afectacion AND activo;
        IF v_convenio.id_convenio IS NULL OR v_afectacion.id_afectacion IS NULL
           OR v_convenio.id_proyecto_nucleo <> v_afectacion.id_proyecto_nucleo
           OR v_convenio.ambito <> v_afectacion.tipo_afectacion THEN
            RAISE EXCEPTION 'Convenio y afectación deben estar activos y compartir ProyectoNucleo/ámbito';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_validar_convenio_relaciones(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_convenio_relaciones() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE v_padre convenio%ROWTYPE; v_asamblea asamblea%ROWTYPE; v_contexto TEXT;
BEGIN
    IF NEW.id_convenio_padre IS NOT NULL THEN
        SELECT * INTO v_padre FROM convenio WHERE id_convenio=NEW.id_convenio_padre AND activo;
        IF v_padre.id_convenio IS NULL OR v_padre.id_proyecto_nucleo<>NEW.id_proyecto_nucleo OR v_padre.ambito<>NEW.ambito THEN
            RAISE EXCEPTION 'El convenio padre debe estar activo y pertenecer al mismo ProyectoNucleo/ámbito';
        END IF;
        IF NEW.tipo_convenio='cop_original'
           OR (NEW.tipo_convenio='superficie_adicional' AND v_padre.tipo_convenio NOT IN ('cop_original','superficie_adicional'))
           OR (NEW.tipo_convenio='obras_complementarias' AND v_padre.tipo_convenio NOT IN ('cop_original','obras_complementarias'))
           OR (NEW.tipo_convenio IN ('ampliacion','ampliacion_remanente') AND v_padre.tipo_convenio NOT IN ('cop_original','ampliacion')) THEN
            RAISE EXCEPTION 'Relación padre/hijo no permitida para los tipos de convenio';
        END IF;
        IF NEW.id_convenio IS NOT NULL AND EXISTS (
            WITH RECURSIVE ancestro AS (
                SELECT id_convenio_padre FROM convenio WHERE id_convenio=NEW.id_convenio_padre
                UNION ALL SELECT c.id_convenio_padre FROM convenio c JOIN ancestro a ON c.id_convenio=a.id_convenio_padre
                WHERE c.id_convenio_padre IS NOT NULL
            ) SELECT 1 FROM ancestro WHERE id_convenio_padre=NEW.id_convenio
        ) THEN RAISE EXCEPTION 'La relación de convenios produciría un ciclo'; END IF;
    END IF;
    IF NEW.id_asamblea_autorizacion IS NOT NULL THEN
        SELECT * INTO v_asamblea FROM asamblea WHERE id_asamblea=NEW.id_asamblea_autorizacion AND activo;
        IF NEW.ambito<>'colectivo' OR v_asamblea.id_asamblea IS NULL OR v_asamblea.id_proyecto_nucleo<>NEW.id_proyecto_nucleo THEN
            RAISE EXCEPTION 'La asamblea sólo autoriza convenios colectivos del mismo ProyectoNucleo';
        END IF;
        SELECT c.codigo INTO v_contexto FROM catalogo_operativo c WHERE c.id_catalogo_opcion=v_asamblea.id_contexto_asamblea;
        IF v_contexto IS NOT NULL AND v_contexto<>'otro' AND v_contexto<>NEW.tipo_convenio THEN
            RAISE EXCEPTION 'El contexto de la asamblea no corresponde al tipo de convenio';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_validar_documento_vinculo(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_documento_vinculo() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.activo AND NOT fn_objetivo_controlado_existe(NEW.entidad_tipo, NEW.entidad_id) THEN
        RAISE EXCEPTION 'El objetivo documental %:% no existe', NEW.entidad_tipo, NEW.entidad_id;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_validar_fifonafe_afectacion(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_fifonafe_afectacion() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_tramite tramite_fifonafe%ROWTYPE;
    v_afectacion afectacion%ROWTYPE;
BEGIN
    IF NEW.activo THEN
        SELECT * INTO v_tramite FROM tramite_fifonafe WHERE id_tramite_fifonafe = NEW.id_tramite_fifonafe AND activo;
        SELECT * INTO v_afectacion FROM afectacion WHERE id_afectacion = NEW.id_afectacion AND activo;
        IF v_tramite.id_tramite_fifonafe IS NULL OR v_afectacion.id_afectacion IS NULL
           OR v_tramite.id_proyecto_nucleo <> v_afectacion.id_proyecto_nucleo
           OR v_tramite.ambito <> v_afectacion.tipo_afectacion THEN
            RAISE EXCEPTION 'FIFONAFE y afectación deben estar activos y compartir ProyectoNucleo/ámbito';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_validar_importacion_feature_objetivo(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_importacion_feature_objetivo() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_objetivo VARCHAR(30);
    v_tipo TEXT;
    v_destino_existe BOOLEAN;
BEGIN
    SELECT tipo_objetivo INTO v_objetivo
    FROM importacion_archivo WHERE id_importacion = NEW.id_importacion AND activo;
    IF v_objetivo IS NULL THEN
        RAISE EXCEPTION 'La importación padre no existe o está inactiva';
    END IF;

    IF NEW.geometria_normalizada IS NOT NULL THEN
        v_tipo := GeometryType(NEW.geometria_normalizada);
        IF (v_objetivo = 'trazo_proyecto' AND v_tipo <> 'MULTILINESTRING')
           OR (v_objetivo IN ('nucleo_agrario', 'parcela') AND v_tipo <> 'MULTIPOLYGON') THEN
            RAISE EXCEPTION 'Tipo geométrico % inválido para objetivo %', v_tipo, v_objetivo;
        END IF;
    END IF;

    IF NEW.registro_destino_id IS NOT NULL THEN
        IF v_objetivo = 'trazo_proyecto' THEN
            SELECT EXISTS (SELECT 1 FROM trazo_proyecto WHERE id_trazo = NEW.registro_destino_id) INTO v_destino_existe;
        ELSIF v_objetivo = 'nucleo_agrario' THEN
            SELECT EXISTS (SELECT 1 FROM nucleo_agrario WHERE id_nucleo = NEW.registro_destino_id) INTO v_destino_existe;
        ELSE
            SELECT EXISTS (SELECT 1 FROM parcela WHERE id_parcela = NEW.registro_destino_id) INTO v_destino_existe;
        END IF;
        IF NOT v_destino_existe THEN
            RAISE EXCEPTION 'El registro destino confirmado no existe para el objetivo %', v_objetivo;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: fn_validar_trazabilidad_objetivo(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_validar_trazabilidad_objetivo() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NOT fn_objetivo_controlado_existe(NEW.entidad_tipo, NEW.entidad_id) THEN
        RAISE EXCEPTION 'El objetivo de trazabilidad %:% no existe o no está permitido', NEW.entidad_tipo, NEW.entidad_id;
    END IF;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;


--
-- Name: actividad_campo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.actividad_campo (
    id_actividad integer NOT NULL,
    id_proyecto_nucleo integer NOT NULL,
    tipo_actividad character varying(30) NOT NULL,
    contexto_actividad character varying(40) DEFAULT 'general'::character varying NOT NULL,
    fecha_programada date,
    fecha_realizada date,
    responsable character varying(300),
    resultado text,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    id_afectacion integer,
    CONSTRAINT chk_actividad_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_actividad_contexto CHECK (((contexto_actividad)::text = ANY ((ARRAY['general'::character varying, 'superficie_adicional'::character varying, 'obras_complementarias'::character varying, 'otro'::character varying])::text[]))),
    CONSTRAINT chk_actividad_fechas CHECK (((fecha_realizada IS NULL) OR (fecha_programada IS NULL) OR (fecha_realizada >= fecha_programada))),
    CONSTRAINT chk_actividad_tipo CHECK (((tipo_actividad)::text = ANY ((ARRAY['sensibilizacion'::character varying, 'caminamiento'::character varying])::text[])))
);


--
-- Name: COLUMN actividad_campo.id_afectacion; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actividad_campo.id_afectacion IS 'Contexto opcional de una actividad individual. NULL conserva actividades de alcance ProyectoNucleo; evita duplicar ActividadCampo por cada tipo de flujo.';


--
-- Name: actividad_campo_id_actividad_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.actividad_campo ALTER COLUMN id_actividad ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.actividad_campo_id_actividad_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: afectacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.afectacion (
    id_afectacion integer NOT NULL,
    id_proyecto_nucleo integer NOT NULL,
    tipo_afectacion character varying(20) NOT NULL,
    superficie_preliminar_ha numeric(14,6),
    superficie_afectada_ha numeric(14,6),
    situacion character varying(100),
    condicion_especial character varying(50),
    descripcion_condicion text,
    avaluo_monto numeric(18,2),
    avaluo_fecha date,
    avaluo_referencia character varying(150),
    avaluo_institucion character varying(150),
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    id_tipo_cop_operativo bigint,
    tipo_cop_revision_pendiente boolean DEFAULT false NOT NULL,
    tipo_cop_revision_detalle text,
    CONSTRAINT chk_afectacion_avaluo CHECK (((avaluo_monto IS NULL) OR (avaluo_monto >= (0)::numeric))),
    CONSTRAINT chk_afectacion_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_afectacion_condicion CHECK (((condicion_especial IS NULL) OR ((condicion_especial)::text = ANY ((ARRAY['expropiacion_directa'::character varying, 'comunidad_indigena'::character varying, 'otro'::character varying])::text[])))),
    CONSTRAINT chk_afectacion_condicion_otro CHECK ((((condicion_especial)::text <> 'otro'::text) OR (NULLIF(btrim(descripcion_condicion), ''::text) IS NOT NULL))),
    CONSTRAINT chk_afectacion_superficies CHECK ((((superficie_preliminar_ha IS NULL) OR (superficie_preliminar_ha >= (0)::numeric)) AND ((superficie_afectada_ha IS NULL) OR (superficie_afectada_ha >= (0)::numeric)))),
    CONSTRAINT chk_afectacion_tipo_cop_revision CHECK (((NOT tipo_cop_revision_pendiente) OR (NULLIF(btrim(tipo_cop_revision_detalle), ''::text) IS NOT NULL)))
);


--
-- Name: COLUMN afectacion.condicion_especial; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.afectacion.condicion_especial IS 'Compatibilidad. no_afectacion_uso_comun deja de ser fuente canónica en 037; usar proyecto_nucleo.afecta_tuc + motivo. Expropiacion/comunidad siguen como contexto de afectacion cuando corresponda.';


--
-- Name: COLUMN afectacion.id_tipo_cop_operativo; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.afectacion.id_tipo_cop_operativo IS 'Clasificacion operativa de planeacion/proceso (ORIGEN/ADICIONAL/2A ADICIONAL/COMPLEMENTARIAS). El convenio juridico sigue siendo convenio.tipo_convenio + consecutivo.';


--
-- Name: afectacion_id_afectacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.afectacion ALTER COLUMN id_afectacion ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.afectacion_id_afectacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: afectacion_unidad_agraria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.afectacion_unidad_agraria (
    id_afectacion_unidad bigint NOT NULL,
    id_afectacion integer NOT NULL,
    id_unidad_agraria bigint NOT NULL,
    superficie_preliminar_ha numeric(14,6),
    superficie_afectada_ha numeric(14,6),
    superficie_valor_original character varying(120),
    superficie_formato_origen character varying(50),
    fuente character varying(250),
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_afectacion_unidad_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_afectacion_unidad_superficie CHECK ((((superficie_preliminar_ha IS NULL) OR (superficie_preliminar_ha >= (0)::numeric)) AND ((superficie_afectada_ha IS NULL) OR (superficie_afectada_ha >= (0)::numeric))))
);


--
-- Name: TABLE afectacion_unidad_agraria; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.afectacion_unidad_agraria IS 'Relacion ProyectoNucleo/Afectacion con una unidad agraria del mismo nucleo; permite reutilizar el mismo bien en procesos distintos.';


--
-- Name: afectacion_unidad_agraria_id_afectacion_unidad_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.afectacion_unidad_agraria ALTER COLUMN id_afectacion_unidad ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.afectacion_unidad_agraria_id_afectacion_unidad_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: asamblea; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.asamblea (
    id_asamblea integer NOT NULL,
    id_proyecto_nucleo integer NOT NULL,
    id_padron integer,
    proposito text,
    resultado character varying(50),
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    id_tipo_asamblea bigint NOT NULL,
    id_contexto_asamblea bigint,
    CONSTRAINT chk_asamblea_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL))))
);


--
-- Name: asamblea_convocatoria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.asamblea_convocatoria (
    id_convocatoria bigint NOT NULL,
    id_asamblea integer NOT NULL,
    ordinal integer NOT NULL,
    fecha_expedicion date,
    fecha_programada date,
    fecha_realizacion date,
    id_resultado bigint,
    observaciones_resultado text,
    id_documento integer,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_convocatoria_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_convocatoria_fechas CHECK (((fecha_programada IS NULL) OR (fecha_expedicion IS NULL) OR (fecha_programada >= fecha_expedicion))),
    CONSTRAINT chk_convocatoria_ordinal CHECK ((ordinal > 0))
);


--
-- Name: asamblea_convocatoria_id_convocatoria_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.asamblea_convocatoria ALTER COLUMN id_convocatoria ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.asamblea_convocatoria_id_convocatoria_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: asamblea_id_asamblea_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.asamblea ALTER COLUMN id_asamblea ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.asamblea_id_asamblea_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: bitacora; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bitacora (
    id_bitacora bigint NOT NULL,
    id_usuario integer,
    id_proyecto integer,
    id_proyecto_nucleo integer,
    id_nucleo integer,
    entidad_tipo character varying(100) NOT NULL,
    entidad_id bigint,
    accion character varying(30) NOT NULL,
    valor_anterior jsonb,
    valor_nuevo jsonb,
    fecha_hora timestamp with time zone DEFAULT now() NOT NULL,
    ip_origen inet,
    user_agent text,
    CONSTRAINT bitacora_accion_check CHECK (((accion)::text = ANY ((ARRAY['insert'::character varying, 'update'::character varying, 'delete'::character varying, 'validacion'::character varying, 'cambio_estado'::character varying, 'carga_documento'::character varying])::text[])))
);


--
-- Name: bitacora_id_bitacora_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.bitacora ALTER COLUMN id_bitacora ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.bitacora_id_bitacora_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: catalogo_alias_territorial; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.catalogo_alias_territorial (
    id_alias bigint NOT NULL,
    id_entidad integer NOT NULL,
    alias_nombre character varying(200),
    alias_normalizado character varying(200) NOT NULL,
    alias_clave character varying(120),
    id_municipio_destino integer NOT NULL,
    fuente character varying(250) NOT NULL,
    fecha_vigencia_inicio date,
    fecha_vigencia_fin date,
    id_usuario_aprobador integer NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_alias_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_alias_identidad CHECK (((alias_nombre IS NOT NULL) OR (alias_clave IS NOT NULL))),
    CONSTRAINT chk_alias_vigencia CHECK (((fecha_vigencia_fin IS NULL) OR (fecha_vigencia_inicio IS NULL) OR (fecha_vigencia_fin >= fecha_vigencia_inicio)))
);


--
-- Name: catalogo_alias_territorial_id_alias_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.catalogo_alias_territorial ALTER COLUMN id_alias ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.catalogo_alias_territorial_id_alias_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: catalogo_operativo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.catalogo_operativo (
    id_catalogo_opcion bigint NOT NULL,
    tipo_catalogo character varying(50) NOT NULL,
    codigo character varying(80) NOT NULL,
    nombre character varying(250) NOT NULL,
    descripcion text,
    orden integer DEFAULT 0 NOT NULL,
    fuente character varying(250),
    vigencia_inicio date,
    vigencia_fin date,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_catalogo_operativo_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_catalogo_operativo_codigo CHECK (((codigo)::text ~ '^[A-Za-z0-9][A-Za-z0-9_-]*$'::text)),
    CONSTRAINT chk_catalogo_operativo_nombre CHECK ((NULLIF(btrim((nombre)::text), ''::text) IS NOT NULL)),
    CONSTRAINT chk_catalogo_operativo_tipo CHECK ((NULLIF(btrim((tipo_catalogo)::text), ''::text) IS NOT NULL)),
    CONSTRAINT chk_catalogo_operativo_vigencia CHECK (((vigencia_fin IS NULL) OR (vigencia_inicio IS NULL) OR (vigencia_fin >= vigencia_inicio)))
);


--
-- Name: catalogo_operativo_alias; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.catalogo_operativo_alias (
    id_catalogo_alias bigint NOT NULL,
    id_catalogo_opcion bigint NOT NULL,
    alias character varying(300) NOT NULL,
    alias_normalizado character varying(300) NOT NULL,
    fuente character varying(250),
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_catalogo_alias_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_catalogo_alias_valor CHECK (((NULLIF(btrim((alias)::text), ''::text) IS NOT NULL) AND (NULLIF(btrim((alias_normalizado)::text), ''::text) IS NOT NULL)))
);


--
-- Name: catalogo_operativo_alias_id_catalogo_alias_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.catalogo_operativo_alias ALTER COLUMN id_catalogo_alias ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.catalogo_operativo_alias_id_catalogo_alias_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: catalogo_operativo_id_catalogo_opcion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.catalogo_operativo ALTER COLUMN id_catalogo_opcion ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.catalogo_operativo_id_catalogo_opcion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: convenio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.convenio (
    id_convenio integer NOT NULL,
    id_proyecto_nucleo integer NOT NULL,
    ambito character varying(20) NOT NULL,
    tipo_instrumento character varying(20) DEFAULT 'convenio'::character varying NOT NULL,
    tipo_convenio character varying(40),
    modalidad_especial character varying(30),
    descripcion_modalidad text,
    descripcion_instrumento text,
    consecutivo integer DEFAULT 1 NOT NULL,
    id_convenio_padre integer,
    id_asamblea_autorizacion integer,
    fecha_programada_firma date,
    fecha_firma date,
    monto_90 numeric(18,2),
    monto_100 numeric(18,2),
    monto_bdt numeric(18,2),
    superficie_ha numeric(14,6),
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_convenio_ambito CHECK (((ambito)::text = ANY ((ARRAY['colectivo'::character varying, 'individual'::character varying])::text[]))),
    CONSTRAINT chk_convenio_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_convenio_consecutivo CHECK ((consecutivo > 0)),
    CONSTRAINT chk_convenio_instrumento CHECK (((tipo_instrumento)::text = ANY ((ARRAY['convenio'::character varying, 'otro'::character varying])::text[]))),
    CONSTRAINT chk_convenio_modalidad CHECK (((modalidad_especial IS NULL) OR ((modalidad_especial)::text = ANY ((ARRAY['permuta'::character varying, 'otra'::character varying])::text[])))),
    CONSTRAINT chk_convenio_modalidad_descripcion CHECK ((((modalidad_especial)::text <> 'otra'::text) OR (NULLIF(btrim(descripcion_modalidad), ''::text) IS NOT NULL))),
    CONSTRAINT chk_convenio_montos CHECK ((((monto_90 IS NULL) OR (monto_90 >= (0)::numeric)) AND ((monto_100 IS NULL) OR (monto_100 >= (0)::numeric)) AND ((monto_bdt IS NULL) OR (monto_bdt >= (0)::numeric)) AND ((monto_90 IS NULL) OR (monto_100 IS NULL) OR (monto_90 <= monto_100)) AND ((superficie_ha IS NULL) OR (superficie_ha >= (0)::numeric)))),
    CONSTRAINT chk_convenio_padre CHECK (((id_convenio_padre IS NULL) OR (id_convenio_padre <> id_convenio))),
    CONSTRAINT chk_convenio_permuta CHECK ((((modalidad_especial)::text <> 'permuta'::text) OR ((tipo_convenio)::text = 'cop_original'::text))),
    CONSTRAINT chk_convenio_tipo_ambito CHECK (((((tipo_instrumento)::text = 'otro'::text) AND (tipo_convenio IS NULL) AND (NULLIF(btrim(descripcion_instrumento), ''::text) IS NOT NULL)) OR (((tipo_instrumento)::text = 'convenio'::text) AND ((((ambito)::text = 'colectivo'::text) AND ((tipo_convenio)::text = ANY ((ARRAY['cop_original'::character varying, 'modificatorio'::character varying, 'superficie_adicional'::character varying, 'obras_complementarias'::character varying])::text[]))) OR (((ambito)::text = 'individual'::text) AND ((tipo_convenio)::text = ANY ((ARRAY['cop_original'::character varying, 'modificatorio'::character varying, 'ampliacion'::character varying, 'ampliacion_remanente'::character varying])::text[])))))))
);


--
-- Name: COLUMN convenio.id_convenio_padre; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.convenio.id_convenio_padre IS 'Linaje juridico/operativo. En individual 039: original sin padre; modificatorio/ampliacion/remanente como instrumentos hijos. No equivale a TIPO COP operativo de Afectacion.';


--
-- Name: convenio_afectacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.convenio_afectacion (
    id_convenio_afectacion integer NOT NULL,
    id_convenio integer NOT NULL,
    id_afectacion integer NOT NULL,
    rol character varying(20) DEFAULT 'principal'::character varying NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_convenio_afectacion_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_convenio_afectacion_rol CHECK (((rol)::text = ANY ((ARRAY['principal'::character varying, 'adicional'::character varying])::text[])))
);


--
-- Name: convenio_afectacion_id_convenio_afectacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.convenio_afectacion ALTER COLUMN id_convenio_afectacion ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.convenio_afectacion_id_convenio_afectacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: convenio_compareciente; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.convenio_compareciente (
    id_compareciente bigint NOT NULL,
    id_convenio integer NOT NULL,
    id_persona integer NOT NULL,
    id_parcela_titular integer,
    id_tipo_calidad bigint NOT NULL,
    id_tipo_acreditacion bigint,
    referencia_acreditacion character varying(200),
    fecha_acreditacion date,
    nombre_en_instrumento character varying(300) NOT NULL,
    es_firmante boolean DEFAULT true NOT NULL,
    es_beneficiario_pago boolean DEFAULT false NOT NULL,
    requiere_revision boolean DEFAULT false NOT NULL,
    motivo_revision text,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_compareciente_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_compareciente_nombre CHECK ((NULLIF(btrim((nombre_en_instrumento)::text), ''::text) IS NOT NULL)),
    CONSTRAINT chk_compareciente_revision CHECK (((NOT requiere_revision) OR (NULLIF(btrim(motivo_revision), ''::text) IS NOT NULL)))
);


--
-- Name: TABLE convenio_compareciente; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.convenio_compareciente IS 'Compareciente historico por instrumento individual. No sustituye Persona/ParcelaTitular: conserva quien firmo/comparecio y la evidencia usada en ese convenio.';


--
-- Name: COLUMN convenio_compareciente.nombre_en_instrumento; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.convenio_compareciente.nombre_en_instrumento IS 'Instantanea textual del nombre tal como aparece en el instrumento; Persona sigue siendo la identidad canonica.';


--
-- Name: COLUMN convenio_compareciente.es_beneficiario_pago; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.convenio_compareciente.es_beneficiario_pago IS 'Rol de pago independiente de es_firmante; ser beneficiario no prueba por si mismo facultad para firmar.';


--
-- Name: convenio_compareciente_id_compareciente_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.convenio_compareciente ALTER COLUMN id_compareciente ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.convenio_compareciente_id_compareciente_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: convenio_id_convenio_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.convenio ALTER COLUMN id_convenio ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.convenio_id_convenio_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: documento; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento (
    id_documento integer NOT NULL,
    tipo_documento character varying(80) NOT NULL,
    estado character varying(20) NOT NULL,
    titulo character varying(250),
    descripcion text,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    fecha_documento date,
    numero_folio character varying(150),
    CONSTRAINT chk_documento_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_documento_estado CHECK (((estado)::text = ANY ((ARRAY['disponible'::character varying, 'faltante'::character varying, 'referenciado'::character varying])::text[]))),
    CONSTRAINT chk_documento_tipo CHECK ((NULLIF(btrim((tipo_documento)::text), ''::text) IS NOT NULL))
);


--
-- Name: COLUMN documento.fecha_documento; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.documento.fecha_documento IS 'Fecha propia del documento o soporte, independiente de la fecha de carga.';


--
-- Name: COLUMN documento.numero_folio; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.documento.numero_folio IS 'Número de oficio, folio o referencia visible del documento.';


--
-- Name: documento_id_documento_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.documento ALTER COLUMN id_documento ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.documento_id_documento_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: documento_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento_version (
    id_documento_version bigint NOT NULL,
    id_documento integer NOT NULL,
    numero_version integer NOT NULL,
    hash_sha256 character(64) NOT NULL,
    tamano_bytes bigint NOT NULL,
    nombre_original character varying(255) NOT NULL,
    ruta_almacenamiento text NOT NULL,
    tipo_mime character varying(150),
    fecha_carga timestamp with time zone DEFAULT now() NOT NULL,
    id_usuario_carga integer NOT NULL,
    CONSTRAINT chk_documento_hash CHECK ((hash_sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT chk_documento_version CHECK (((numero_version > 0) AND (tamano_bytes >= 0)))
);


--
-- Name: documento_version_id_documento_version_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.documento_version ALTER COLUMN id_documento_version ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.documento_version_id_documento_version_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: documento_vinculo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento_vinculo (
    id_documento_vinculo integer NOT NULL,
    id_documento integer NOT NULL,
    entidad_tipo character varying(50) NOT NULL,
    entidad_id integer NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_documento_vinculo_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_documento_vinculo_tipo CHECK (((entidad_tipo)::text = ANY ((ARRAY['proyecto_nucleo'::character varying, 'nucleo_agrario'::character varying, 'orv'::character varying, 'padron_historial'::character varying, 'parcela'::character varying, 'parcela_titular'::character varying, 'afectacion'::character varying, 'unidad_agraria'::character varying, 'unidad_agraria_titular'::character varying, 'afectacion_unidad_agraria'::character varying, 'asamblea'::character varying, 'asamblea_convocatoria'::character varying, 'convenio'::character varying, 'convenio_compareciente'::character varying, 'tramite_ran'::character varying, 'tramite_ran_evento'::character varying, 'tramite_fifonafe'::character varying, 'tramite_fifonafe_evento'::character varying, 'indemnizacion'::character varying, 'pago'::character varying, 'expediente_requisito'::character varying])::text[])))
);


--
-- Name: documento_vinculo_id_documento_vinculo_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.documento_vinculo ALTER COLUMN id_documento_vinculo ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.documento_vinculo_id_documento_vinculo_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: entidad_federativa; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entidad_federativa (
    id_entidad integer NOT NULL,
    clave_inegi character(2) NOT NULL,
    nombre character varying(100) NOT NULL,
    activo boolean DEFAULT true NOT NULL
);


--
-- Name: entidad_federativa_id_entidad_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entidad_federativa_id_entidad_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entidad_federativa_id_entidad_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entidad_federativa_id_entidad_seq OWNED BY public.entidad_federativa.id_entidad;


--
-- Name: estado_autenticacion_usuario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.estado_autenticacion_usuario (
    id_usuario integer NOT NULL,
    intentos_fallidos smallint DEFAULT 0 NOT NULL,
    bloqueado_hasta timestamp with time zone,
    ultimo_acceso_en timestamp with time zone,
    actualizado_en timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_auth_bloqueo_consistente CHECK ((((intentos_fallidos = 5) AND (bloqueado_hasta IS NOT NULL)) OR ((intentos_fallidos < 5) AND (bloqueado_hasta IS NULL)))),
    CONSTRAINT chk_auth_intentos_fallidos CHECK (((intentos_fallidos >= 0) AND (intentos_fallidos <= 5)))
);


--
-- Name: evento_acceso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evento_acceso (
    id_evento bigint NOT NULL,
    id_usuario integer,
    id_usuario_actor integer,
    id_sesion bigint,
    tipo_evento character varying(40) NOT NULL,
    motivo_codigo character varying(50) NOT NULL,
    detalle character varying(200),
    fecha_hora timestamp with time zone DEFAULT now() NOT NULL,
    ip_origen inet,
    user_agent character varying(512),
    txid_registro bigint DEFAULT txid_current() NOT NULL,
    CONSTRAINT chk_auth_evento_motivo CHECK (((motivo_codigo)::text = ANY ((ARRAY['inicio_sesion'::character varying, 'credenciales_invalidas'::character varying, 'usuario_inactivo'::character varying, 'bloqueo_vigente'::character varying, 'quinto_fallo'::character varying, 'cierre_usuario'::character varying, 'cierre_total'::character varying, 'revocacion_admin'::character varying, 'expiracion_inactividad'::character varying, 'expiracion_absoluta'::character varying, 'desbloqueo_admin'::character varying, 'desbloqueo_recuperacion'::character varying])::text[]))),
    CONSTRAINT chk_auth_evento_tipo CHECK (((tipo_evento)::text = ANY ((ARRAY['login_exitoso'::character varying, 'login_fallido'::character varying, 'cuenta_bloqueada'::character varying, 'logout'::character varying, 'sesion_expirada'::character varying, 'sesion_revocada'::character varying, 'desbloqueo'::character varying])::text[])))
);


--
-- Name: evento_acceso_id_evento_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.evento_acceso_id_evento_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evento_acceso_id_evento_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.evento_acceso_id_evento_seq OWNED BY public.evento_acceso.id_evento;


--
-- Name: expediente_requisito; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.expediente_requisito (
    id_expediente_requisito bigint NOT NULL,
    id_proyecto_nucleo integer NOT NULL,
    id_requisito bigint NOT NULL,
    id_estado bigint NOT NULL,
    id_documento integer,
    detalle text,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    entidad_tipo character varying(50) NOT NULL,
    entidad_id bigint NOT NULL,
    CONSTRAINT chk_expediente_requisito_objetivo CHECK (((entidad_tipo)::text = ANY ((ARRAY['proyecto_nucleo'::character varying, 'afectacion'::character varying, 'parcela'::character varying, 'parcela_titular'::character varying, 'unidad_agraria'::character varying, 'unidad_agraria_titular'::character varying, 'convenio'::character varying, 'convenio_compareciente'::character varying, 'tramite_ran'::character varying, 'tramite_ran_evento'::character varying, 'tramite_fifonafe'::character varying, 'tramite_fifonafe_evento'::character varying, 'indemnizacion'::character varying, 'pago'::character varying])::text[]))),
    CONSTRAINT chk_expediente_requisito_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL))))
);


--
-- Name: COLUMN expediente_requisito.entidad_tipo; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.expediente_requisito.entidad_tipo IS 'Objetivo concreto del requisito. Permite repetir un mismo requisito por convenio/tramite/evento sin duplicar la definicion del catalogo.';


--
-- Name: COLUMN expediente_requisito.entidad_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.expediente_requisito.entidad_id IS 'PK del objetivo controlado por entidad_tipo; su pertenencia al ProyectoNucleo se valida por trigger 039.';


--
-- Name: expediente_requisito_id_expediente_requisito_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.expediente_requisito ALTER COLUMN id_expediente_requisito ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.expediente_requisito_id_expediente_requisito_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: importacion_archivo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.importacion_archivo (
    id_importacion bigint NOT NULL,
    id_proyecto integer NOT NULL,
    tipo_objetivo character varying(30) NOT NULL,
    nombre_original character varying(255) NOT NULL,
    nombre_almacenado character varying(255) NOT NULL,
    formato_detectado character varying(20) NOT NULL,
    tamano_bytes bigint NOT NULL,
    sha256 character(64) NOT NULL,
    fuente character varying(250) NOT NULL,
    fecha_fuente date,
    crs_original text,
    crs_destino character varying(30) DEFAULT 'EPSG:4326'::character varying NOT NULL,
    columnas_detectadas jsonb DEFAULT '[]'::jsonb NOT NULL,
    mapeo jsonb DEFAULT '{}'::jsonb NOT NULL,
    opciones_mapeo jsonb DEFAULT '{}'::jsonb NOT NULL,
    id_perfil bigint,
    estado character varying(40) DEFAULT 'subido'::character varying NOT NULL,
    total_features integer DEFAULT 0 NOT NULL,
    features_procesados integer DEFAULT 0 NOT NULL,
    validos integer DEFAULT 0 NOT NULL,
    advertencias integer DEFAULT 0 NOT NULL,
    errores integer DEFAULT 0 NOT NULL,
    importados integer DEFAULT 0 NOT NULL,
    descartados integer DEFAULT 0 NOT NULL,
    id_usuario_carga integer NOT NULL,
    fecha_carga timestamp with time zone DEFAULT now() NOT NULL,
    fecha_procesamiento_inicio timestamp with time zone,
    fecha_procesamiento_fin timestamp with time zone,
    confirmacion_explicita boolean DEFAULT false NOT NULL,
    fecha_confirmacion timestamp with time zone,
    id_usuario_confirmacion integer,
    error_codigo character varying(80),
    error_detalle text,
    reporte jsonb DEFAULT '{}'::jsonb NOT NULL,
    version_control integer DEFAULT 1 NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_importacion_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_importacion_confirmacion CHECK ((((NOT confirmacion_explicita) AND (fecha_confirmacion IS NULL) AND (id_usuario_confirmacion IS NULL)) OR (confirmacion_explicita AND (fecha_confirmacion IS NOT NULL) AND (id_usuario_confirmacion IS NOT NULL)))),
    CONSTRAINT chk_importacion_contadores CHECK (((total_features >= 0) AND (features_procesados >= 0) AND (validos >= 0) AND (advertencias >= 0) AND (errores >= 0) AND (importados >= 0) AND (descartados >= 0))),
    CONSTRAINT chk_importacion_estado CHECK (((estado)::text = ANY ((ARRAY['subido'::character varying, 'mapeado'::character varying, 'procesando'::character varying, 'previsualizado'::character varying, 'confirmando'::character varying, 'completo'::character varying, 'error'::character varying, 'cancelado'::character varying])::text[]))),
    CONSTRAINT chk_importacion_formato CHECK (((formato_detectado)::text = ANY ((ARRAY['geojson'::character varying, 'gpkg'::character varying, 'shp'::character varying, 'kml'::character varying, 'zip'::character varying])::text[]))),
    CONSTRAINT chk_importacion_hash CHECK ((sha256 ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT chk_importacion_objetivo CHECK (((tipo_objetivo)::text = ANY ((ARRAY['trazo_proyecto'::character varying, 'nucleo_agrario'::character varying, 'parcela'::character varying])::text[]))),
    CONSTRAINT chk_importacion_tamano CHECK ((tamano_bytes > 0))
);


--
-- Name: importacion_archivo_id_importacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.importacion_archivo ALTER COLUMN id_importacion ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.importacion_archivo_id_importacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: importacion_feature; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.importacion_feature (
    id_importacion_feature bigint NOT NULL,
    id_importacion bigint NOT NULL,
    indice_feature integer NOT NULL,
    capa_origen character varying(200),
    id_externo character varying(200),
    tipo_geometria character varying(40),
    atributos_originales jsonb DEFAULT '{}'::jsonb NOT NULL,
    atributos_normalizados jsonb DEFAULT '{}'::jsonb NOT NULL,
    geometria_normalizada public.geometry(Geometry,4326),
    estado character varying(40) DEFAULT 'pendiente_revision'::character varying NOT NULL,
    errores jsonb DEFAULT '[]'::jsonb NOT NULL,
    advertencias jsonb DEFAULT '[]'::jsonb NOT NULL,
    transformaciones jsonb DEFAULT '[]'::jsonb NOT NULL,
    advertencias_aceptadas boolean DEFAULT false NOT NULL,
    id_usuario_revision integer,
    fecha_revision timestamp with time zone,
    registro_destino_id integer,
    fecha_procesamiento timestamp with time zone DEFAULT now() NOT NULL,
    fecha_importacion timestamp with time zone,
    CONSTRAINT chk_importacion_feature_estado CHECK (((estado)::text = ANY ((ARRAY['pendiente_revision'::character varying, 'valido'::character varying, 'advertencia'::character varying, 'error'::character varying, 'confirmado'::character varying, 'descartado'::character varying])::text[]))),
    CONSTRAINT chk_importacion_feature_geometria CHECK (((geometria_normalizada IS NULL) OR ((NOT public.st_isempty(geometria_normalizada)) AND public.st_isvalid(geometria_normalizada) AND (public.st_srid(geometria_normalizada) = 4326)))),
    CONSTRAINT chk_importacion_feature_indice CHECK ((indice_feature >= 0))
);


--
-- Name: importacion_feature_id_importacion_feature_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.importacion_feature ALTER COLUMN id_importacion_feature ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.importacion_feature_id_importacion_feature_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: importacion_tabular; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.importacion_tabular (
    id_importacion_tabular bigint NOT NULL,
    id_proyecto integer NOT NULL,
    archivo character varying(255) NOT NULL,
    sha256 character(64) NOT NULL,
    hoja character varying(255) NOT NULL,
    filas_detectadas integer DEFAULT 0 NOT NULL,
    filas_procesadas integer DEFAULT 0 NOT NULL,
    advertencias integer DEFAULT 0 NOT NULL,
    errores integer DEFAULT 0 NOT NULL,
    estado character varying(30) DEFAULT 'auditado'::character varying NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_importacion_tabular_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_importacion_tabular_conteos CHECK (((filas_detectadas >= 0) AND (filas_procesadas >= 0) AND (advertencias >= 0) AND (errores >= 0))),
    CONSTRAINT chk_importacion_tabular_estado CHECK (((estado)::text = ANY ((ARRAY['auditado'::character varying, 'previsualizado'::character varying, 'importando'::character varying, 'completo'::character varying, 'con_advertencias'::character varying, 'error'::character varying, 'cancelado'::character varying])::text[]))),
    CONSTRAINT chk_importacion_tabular_hash CHECK ((sha256 ~ '^[0-9a-f]{64}$'::text))
);


--
-- Name: importacion_tabular_celda; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.importacion_tabular_celda (
    id_importacion_celda bigint NOT NULL,
    id_importacion_tabular bigint NOT NULL,
    fila integer NOT NULL,
    columna character varying(20) NOT NULL,
    encabezado character varying(300),
    valor_original text,
    valor_normalizado text,
    tratamiento character varying(30) NOT NULL,
    mensajes jsonb DEFAULT '[]'::jsonb NOT NULL,
    entidad_tipo character varying(50),
    entidad_id bigint,
    registrado_en timestamp with time zone DEFAULT now() NOT NULL,
    id_usuario_registro integer,
    CONSTRAINT chk_importacion_celda_columna CHECK (((columna)::text ~ '^[A-Z]+$'::text)),
    CONSTRAINT chk_importacion_celda_fila CHECK ((fila > 0)),
    CONSTRAINT chk_importacion_celda_objetivo CHECK ((((entidad_tipo IS NULL) AND (entidad_id IS NULL)) OR ((entidad_tipo IS NOT NULL) AND (entidad_id IS NOT NULL)))),
    CONSTRAINT chk_importacion_celda_tratamiento CHECK (((tratamiento)::text = ANY ((ARRAY['PERSISTIR'::character varying, 'DERIVAR'::character varying, 'REFERENCIA'::character varying, 'DOCUMENTAR'::character varying, 'REVISAR'::character varying, 'NO_IMPLEMENTAR'::character varying, 'ERROR'::character varying])::text[])))
);


--
-- Name: importacion_tabular_celda_id_importacion_celda_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.importacion_tabular_celda ALTER COLUMN id_importacion_celda ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.importacion_tabular_celda_id_importacion_celda_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: importacion_tabular_id_importacion_tabular_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.importacion_tabular ALTER COLUMN id_importacion_tabular ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.importacion_tabular_id_importacion_tabular_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: indemnizacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.indemnizacion (
    id_indemnizacion integer NOT NULL,
    id_afectacion integer NOT NULL,
    estatus character varying(30) DEFAULT 'pendiente'::character varying NOT NULL,
    descripcion_estatus text,
    fecha_programada date,
    fecha_resolucion date,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    fecha_entrega_expediente_pa date,
    CONSTRAINT chk_indemnizacion_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_indemnizacion_estatus CHECK (((estatus)::text = ANY ((ARRAY['pendiente'::character varying, 'programado'::character varying, 'completo'::character varying, 'otro'::character varying])::text[]))),
    CONSTRAINT chk_indemnizacion_fechas CHECK (((fecha_resolucion IS NULL) OR (fecha_programada IS NULL) OR (fecha_resolucion >= fecha_programada))),
    CONSTRAINT chk_indemnizacion_otro CHECK ((((estatus)::text <> 'otro'::text) OR (NULLIF(btrim(descripcion_estatus), ''::text) IS NOT NULL)))
);


--
-- Name: COLUMN indemnizacion.fecha_entrega_expediente_pa; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.indemnizacion.fecha_entrega_expediente_pa IS 'Fecha de entrega del expediente SICT a la Procuraduría Agraria.';


--
-- Name: indemnizacion_id_indemnizacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.indemnizacion ALTER COLUMN id_indemnizacion ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.indemnizacion_id_indemnizacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: municipio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.municipio (
    id_municipio integer NOT NULL,
    id_entidad integer NOT NULL,
    clave_inegi character(5) NOT NULL,
    nombre character varying(150) NOT NULL,
    activo boolean DEFAULT true NOT NULL
);


--
-- Name: municipio_id_municipio_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.municipio_id_municipio_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: municipio_id_municipio_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.municipio_id_municipio_seq OWNED BY public.municipio.id_municipio;


--
-- Name: nucleo_agrario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nucleo_agrario (
    id_nucleo integer NOT NULL,
    id_municipio integer NOT NULL,
    nombre_nucleo character varying(300) NOT NULL,
    comunidad_indigena boolean,
    geometria_poligono public.geometry(MultiPolygon,4326),
    fuente_geometria character varying(250),
    fecha_fuente_geometria date,
    fuente_datos character varying(120),
    id_entidad_fuente character varying(120),
    id_municipio_fuente character varying(120),
    id_nucleo_fuente character varying(120),
    alcance_identidad_fuente character varying(20),
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    id_tipo_tenencia bigint NOT NULL,
    CONSTRAINT chk_nucleo_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_nucleo_geometria CHECK (((geometria_poligono IS NULL) OR ((NOT public.st_isempty(geometria_poligono)) AND public.st_isvalid(geometria_poligono) AND (public.st_srid(geometria_poligono) = 4326) AND (public.geometrytype(geometria_poligono) = 'MULTIPOLYGON'::text))))
);


--
-- Name: COLUMN nucleo_agrario.comunidad_indigena; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nucleo_agrario.comunidad_indigena IS 'Trivaluado: NULL=no capturado, TRUE=sí, FALSE=no. No se infiere de la tenencia.';


--
-- Name: nucleo_agrario_id_nucleo_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.nucleo_agrario ALTER COLUMN id_nucleo ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.nucleo_agrario_id_nucleo_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: orv; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orv (
    id_orv integer NOT NULL,
    id_nucleo integer NOT NULL,
    numero_orv character varying(50),
    inicio_vigencia date,
    fin_vigencia date,
    estatus_fuente character varying(80),
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    id_estado_registral bigint,
    CONSTRAINT chk_orv_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_orv_vigencia CHECK (((fin_vigencia IS NULL) OR (inicio_vigencia IS NULL) OR (fin_vigencia >= inicio_vigencia)))
);


--
-- Name: orv_id_orv_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.orv ALTER COLUMN id_orv ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.orv_id_orv_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: orv_integrante; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orv_integrante (
    id_orv_integrante integer NOT NULL,
    id_orv integer NOT NULL,
    id_persona integer NOT NULL,
    fecha_inicio date,
    fecha_fin date,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    id_organo bigint NOT NULL,
    id_cargo bigint NOT NULL,
    id_calidad bigint NOT NULL,
    CONSTRAINT chk_orv_integrante_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_orv_integrante_fechas CHECK (((fecha_fin IS NULL) OR (fecha_inicio IS NULL) OR (fecha_fin >= fecha_inicio)))
);


--
-- Name: orv_integrante_id_orv_integrante_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.orv_integrante ALTER COLUMN id_orv_integrante ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.orv_integrante_id_orv_integrante_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: padron_historial; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.padron_historial (
    id_padron integer NOT NULL,
    id_nucleo integer NOT NULL,
    fecha_padron date,
    numero_ejidatarios_comuneros integer,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    fuente character varying(250),
    id_documento integer,
    CONSTRAINT chk_padron_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_padron_datos CHECK ((((fecha_padron IS NOT NULL) OR (numero_ejidatarios_comuneros IS NOT NULL)) AND ((numero_ejidatarios_comuneros IS NULL) OR (numero_ejidatarios_comuneros >= 0))))
);


--
-- Name: COLUMN padron_historial.fecha_padron; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.padron_historial.fecha_padron IS 'Fecha de emisión del corte de padrón; una fila representa un solo corte.';


--
-- Name: padron_historial_id_padron_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.padron_historial ALTER COLUMN id_padron ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.padron_historial_id_padron_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: pago; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pago (
    id_pago integer NOT NULL,
    id_indemnizacion integer NOT NULL,
    fecha_pago date NOT NULL,
    monto numeric(18,2) NOT NULL,
    id_persona_beneficiaria integer,
    beneficiario_nombre character varying(300) NOT NULL,
    referencia character varying(150),
    medio_pago character varying(30),
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_pago_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_pago_beneficiario CHECK ((NULLIF(btrim((beneficiario_nombre)::text), ''::text) IS NOT NULL)),
    CONSTRAINT chk_pago_medio CHECK (((medio_pago IS NULL) OR ((medio_pago)::text = ANY ((ARRAY['transferencia'::character varying, 'cheque'::character varying, 'efectivo'::character varying, 'deposito'::character varying, 'otro'::character varying])::text[])))),
    CONSTRAINT chk_pago_monto CHECK ((monto > (0)::numeric))
);


--
-- Name: pago_id_pago_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.pago ALTER COLUMN id_pago ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.pago_id_pago_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: parcela; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parcela (
    id_parcela integer NOT NULL,
    id_nucleo integer NOT NULL,
    tipo_parcela character varying(30) NOT NULL,
    no_parcela character varying(80),
    certificado_parcelario character varying(120),
    folio_derechos character varying(120),
    constancia_vigencia_fecha date,
    geometria_poligono public.geometry(MultiPolygon,4326),
    fuente_geometria character varying(250),
    fecha_fuente_geometria date,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_parcela_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_parcela_geometria CHECK (((geometria_poligono IS NULL) OR ((NOT public.st_isempty(geometria_poligono)) AND public.st_isvalid(geometria_poligono) AND (public.st_srid(geometria_poligono) = 4326) AND (public.geometrytype(geometria_poligono) = 'MULTIPOLYGON'::text)))),
    CONSTRAINT chk_parcela_tipo CHECK (((tipo_parcela)::text = ANY ((ARRAY['individual'::character varying, 'copropiedad'::character varying, 'otro'::character varying, 'no_determinado'::character varying])::text[])))
);


--
-- Name: COLUMN parcela.no_parcela; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.parcela.no_parcela IS 'Identificador canónico de parcela; 039 reconcilia y elimina no_parcela_ppt.';


--
-- Name: COLUMN parcela.certificado_parcelario; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.parcela.certificado_parcelario IS 'Referencia del certificado disponible; la evidencia documental puede vincularse a Parcela/ParcelaTitular/ExpedienteRequisito.';


--
-- Name: COLUMN parcela.folio_derechos; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.parcela.folio_derechos IS 'Referencia/folio de derechos proveniente de la fuente operativa; no sustituye la validacion registral.';


--
-- Name: COLUMN parcela.constancia_vigencia_fecha; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.parcela.constancia_vigencia_fecha IS 'Fecha de la constancia de vigencia cuando la fuente contiene una fecha validada; textos mixtos de origen deben preservarse en trazabilidad, no forzarse a DATE.';


--
-- Name: parcela_id_parcela_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.parcela ALTER COLUMN id_parcela ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.parcela_id_parcela_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: parcela_titular; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parcela_titular (
    id_parcela_titular integer NOT NULL,
    id_parcela integer NOT NULL,
    id_persona integer NOT NULL,
    tipo_derecho character varying(50) NOT NULL,
    porcentaje_participacion numeric(7,4),
    fecha_inicio date,
    fecha_fin date,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_parcela_titular_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_parcela_titular_fechas CHECK (((fecha_fin IS NULL) OR (fecha_inicio IS NULL) OR (fecha_fin >= fecha_inicio))),
    CONSTRAINT chk_parcela_titular_porcentaje CHECK (((porcentaje_participacion IS NULL) OR ((porcentaje_participacion > (0)::numeric) AND (porcentaje_participacion <= (100)::numeric))))
);


--
-- Name: parcela_titular_id_parcela_titular_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.parcela_titular ALTER COLUMN id_parcela_titular ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.parcela_titular_id_parcela_titular_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: perfil_mapeo_importacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.perfil_mapeo_importacion (
    id_perfil bigint NOT NULL,
    id_proyecto integer,
    nombre character varying(120) NOT NULL,
    fuente character varying(250) NOT NULL,
    tipo_objetivo character varying(30) NOT NULL,
    mapeo jsonb NOT NULL,
    opciones jsonb DEFAULT '{}'::jsonb NOT NULL,
    id_usuario_creacion integer NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_perfil_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_perfil_objetivo CHECK (((tipo_objetivo)::text = ANY ((ARRAY['trazo_proyecto'::character varying, 'nucleo_agrario'::character varying, 'parcela'::character varying])::text[])))
);


--
-- Name: perfil_mapeo_importacion_id_perfil_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.perfil_mapeo_importacion ALTER COLUMN id_perfil ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.perfil_mapeo_importacion_id_perfil_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: persona; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.persona (
    id_persona integer NOT NULL,
    curp character varying(18),
    rfc character varying(13),
    nombre character varying(300) NOT NULL,
    apellido_paterno character varying(200),
    apellido_materno character varying(200),
    telefono character varying(30),
    correo_electronico character varying(320),
    datos_identidad_incompletos boolean DEFAULT false NOT NULL,
    origen_registro character varying(40) DEFAULT 'captura_sistema'::character varying NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_persona_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_persona_nombre CHECK ((NULLIF(btrim((nombre)::text), ''::text) IS NOT NULL)),
    CONSTRAINT chk_persona_origen CHECK (((origen_registro)::text = ANY ((ARRAY['captura_sistema'::character varying, 'excel'::character varying, 'qa'::character varying, 'otro'::character varying])::text[])))
);


--
-- Name: persona_id_persona_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.persona ALTER COLUMN id_persona ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.persona_id_persona_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: proyecto; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proyecto (
    id_proyecto integer NOT NULL,
    clave_proyecto character varying(30) NOT NULL,
    nombre_proyecto character varying(200) NOT NULL,
    descripcion text,
    fecha_inicio date,
    fecha_fin date,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_proyecto_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_proyecto_fechas CHECK (((fecha_fin IS NULL) OR (fecha_inicio IS NULL) OR (fecha_fin >= fecha_inicio)))
);


--
-- Name: proyecto_id_proyecto_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.proyecto ALTER COLUMN id_proyecto ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.proyecto_id_proyecto_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: proyecto_nucleo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proyecto_nucleo (
    id_proyecto_nucleo integer NOT NULL,
    id_proyecto integer NOT NULL,
    id_nucleo integer NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    id_residencia bigint,
    total_cops_planeados integer,
    afecta_tuc boolean,
    id_motivo_no_afecta_tuc bigint,
    motivo_no_afecta_tuc_detalle text,
    tuc_revision_pendiente boolean DEFAULT false NOT NULL,
    tuc_revision_detalle text,
    CONSTRAINT chk_proyecto_nucleo_alcance_tuc CHECK ((((afecta_tuc IS NULL) AND (id_motivo_no_afecta_tuc IS NULL) AND (motivo_no_afecta_tuc_detalle IS NULL)) OR ((afecta_tuc IS TRUE) AND (id_motivo_no_afecta_tuc IS NULL) AND (motivo_no_afecta_tuc_detalle IS NULL)) OR ((afecta_tuc IS FALSE) AND (id_motivo_no_afecta_tuc IS NOT NULL)))),
    CONSTRAINT chk_proyecto_nucleo_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_proyecto_nucleo_total_cops CHECK (((total_cops_planeados IS NULL) OR (total_cops_planeados >= 0))),
    CONSTRAINT chk_proyecto_nucleo_tuc_revision CHECK (((NOT tuc_revision_pendiente) OR (NULLIF(btrim(tuc_revision_detalle), ''::text) IS NOT NULL)))
);


--
-- Name: COLUMN proyecto_nucleo.total_cops_planeados; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.proyecto_nucleo.total_cops_planeados IS 'Planeación explícita del Excel; no es COUNT de filas ni de convenios existentes.';


--
-- Name: COLUMN proyecto_nucleo.afecta_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.proyecto_nucleo.afecta_tuc IS 'Trivaluado: NULL=no evaluado/no capturado; TRUE=existe afectacion a TUC; FALSE=se determino que el proyecto no afecta TUC.';


--
-- Name: COLUMN proyecto_nucleo.id_motivo_no_afecta_tuc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.proyecto_nucleo.id_motivo_no_afecta_tuc IS 'Motivo requerido cuando afecta_tuc=FALSE. No sustituye atributos intrinsecos del nucleo como comunidad_indigena.';


--
-- Name: proyecto_nucleo_id_proyecto_nucleo_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.proyecto_nucleo ALTER COLUMN id_proyecto_nucleo ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.proyecto_nucleo_id_proyecto_nucleo_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: proyecto_nucleo_referencia; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proyecto_nucleo_referencia (
    id_referencia integer NOT NULL,
    id_proyecto_nucleo integer NOT NULL,
    tipo_referencia character varying(30) NOT NULL,
    valor character varying(150) NOT NULL,
    es_principal boolean DEFAULT false NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_pn_referencia_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_pn_referencia_tipo CHECK (((tipo_referencia)::text = ANY ((ARRAY['consecutivo'::character varying, 'clave_tramo'::character varying, 'numero_tramo'::character varying, 'otro'::character varying])::text[]))),
    CONSTRAINT chk_pn_referencia_valor CHECK ((NULLIF(btrim((valor)::text), ''::text) IS NOT NULL))
);


--
-- Name: proyecto_nucleo_referencia_id_referencia_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.proyecto_nucleo_referencia ALTER COLUMN id_referencia ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.proyecto_nucleo_referencia_id_referencia_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: proyecto_nucleo_responsable; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proyecto_nucleo_responsable (
    id_responsable bigint NOT NULL,
    id_proyecto_nucleo integer NOT NULL,
    nombre character varying(300) NOT NULL,
    cargo character varying(200),
    contacto character varying(200),
    vigencia_inicio date,
    vigencia_fin date,
    es_principal boolean DEFAULT false NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_responsable_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_responsable_nombre CHECK ((NULLIF(btrim((nombre)::text), ''::text) IS NOT NULL)),
    CONSTRAINT chk_responsable_vigencia CHECK (((vigencia_fin IS NULL) OR (vigencia_inicio IS NULL) OR (vigencia_fin >= vigencia_inicio)))
);


--
-- Name: proyecto_nucleo_responsable_id_responsable_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.proyecto_nucleo_responsable ALTER COLUMN id_responsable ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.proyecto_nucleo_responsable_id_responsable_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: requisito_documental; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.requisito_documental (
    id_requisito bigint NOT NULL,
    codigo character varying(80) NOT NULL,
    nombre character varying(250) NOT NULL,
    descripcion text,
    contexto character varying(80) DEFAULT 'general'::character varying NOT NULL,
    obligatorio boolean DEFAULT false NOT NULL,
    orden integer DEFAULT 0 NOT NULL,
    fuente character varying(250),
    vigencia_inicio date,
    vigencia_fin date,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_requisito_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_requisito_codigo CHECK (((codigo)::text ~ '^[a-z0-9][a-z0-9_-]*$'::text)),
    CONSTRAINT chk_requisito_nombre CHECK ((NULLIF(btrim((nombre)::text), ''::text) IS NOT NULL)),
    CONSTRAINT chk_requisito_vigencia CHECK (((vigencia_fin IS NULL) OR (vigencia_inicio IS NULL) OR (vigencia_fin >= vigencia_inicio)))
);


--
-- Name: requisito_documental_id_requisito_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.requisito_documental ALTER COLUMN id_requisito ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.requisito_documental_id_requisito_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: sesion_usuario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sesion_usuario (
    id_sesion bigint NOT NULL,
    id_usuario integer NOT NULL,
    token_hash character(64) NOT NULL,
    csrf_hash character(64) NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT now() NOT NULL,
    ultima_actividad timestamp with time zone DEFAULT now() NOT NULL,
    expira_en timestamp with time zone NOT NULL,
    revocada_en timestamp with time zone,
    id_usuario_revoca integer,
    motivo_revocacion character varying(100),
    ip_creacion inet,
    user_agent_creacion character varying(512),
    CONSTRAINT chk_auth_csrf_hash CHECK ((csrf_hash ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT chk_auth_revocacion_consistente CHECK ((((revocada_en IS NULL) AND (id_usuario_revoca IS NULL) AND (motivo_revocacion IS NULL)) OR ((revocada_en IS NOT NULL) AND (NULLIF(btrim((motivo_revocacion)::text), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_auth_sesion_fechas CHECK (((ultima_actividad >= fecha_creacion) AND (expira_en > fecha_creacion))),
    CONSTRAINT chk_auth_token_hash CHECK ((token_hash ~ '^[0-9a-f]{64}$'::text))
);


--
-- Name: sesion_usuario_id_sesion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sesion_usuario_id_sesion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sesion_usuario_id_sesion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sesion_usuario_id_sesion_seq OWNED BY public.sesion_usuario.id_sesion;


--
-- Name: tramite_fifonafe; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tramite_fifonafe (
    id_tramite_fifonafe integer NOT NULL,
    id_proyecto_nucleo integer NOT NULL,
    ambito character varying(20) NOT NULL,
    estatus character varying(30) DEFAULT 'pendiente'::character varying NOT NULL,
    hay_conflictos boolean,
    resultado_no_conflictos text,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    acuse_fifonafe_fecha date,
    CONSTRAINT chk_fifonafe_ambito CHECK (((ambito)::text = ANY ((ARRAY['colectivo'::character varying, 'individual'::character varying])::text[]))),
    CONSTRAINT chk_fifonafe_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_fifonafe_estatus CHECK (((estatus)::text = ANY ((ARRAY['programado'::character varying, 'pendiente'::character varying, 'completo'::character varying, 'cancelado'::character varying, 'otro'::character varying])::text[])))
);


--
-- Name: COLUMN tramite_fifonafe.acuse_fifonafe_fecha; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tramite_fifonafe.acuse_fifonafe_fecha IS 'Fecha del acuse FIFONAFE registrada por el seguimiento operativo.';


--
-- Name: tramite_fifonafe_afectacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tramite_fifonafe_afectacion (
    id_tramite_fifonafe_afectacion integer NOT NULL,
    id_tramite_fifonafe integer NOT NULL,
    id_afectacion integer NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_fifonafe_afectacion_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL))))
);


--
-- Name: tramite_fifonafe_afectacion_id_tramite_fifonafe_afectacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tramite_fifonafe_afectacion ALTER COLUMN id_tramite_fifonafe_afectacion ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tramite_fifonafe_afectacion_id_tramite_fifonafe_afectacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: tramite_fifonafe_evento; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tramite_fifonafe_evento (
    id_evento_fifonafe bigint NOT NULL,
    id_tramite_fifonafe integer NOT NULL,
    ordinal integer NOT NULL,
    id_tipo_evento bigint NOT NULL,
    origen character varying(200),
    destino character varying(200),
    numero_oficio character varying(150),
    fecha_oficio date,
    id_documento integer,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_evento_fifonafe_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_evento_fifonafe_dato CHECK (((NULLIF(btrim((numero_oficio)::text), ''::text) IS NOT NULL) OR (fecha_oficio IS NOT NULL) OR (NULLIF(btrim(observaciones), ''::text) IS NOT NULL))),
    CONSTRAINT chk_evento_fifonafe_ordinal CHECK ((ordinal > 0))
);


--
-- Name: tramite_fifonafe_evento_id_evento_fifonafe_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tramite_fifonafe_evento ALTER COLUMN id_evento_fifonafe ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tramite_fifonafe_evento_id_evento_fifonafe_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: tramite_fifonafe_id_tramite_fifonafe_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tramite_fifonafe ALTER COLUMN id_tramite_fifonafe ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tramite_fifonafe_id_tramite_fifonafe_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: tramite_ran; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tramite_ran (
    id_tramite_ran bigint NOT NULL,
    id_proyecto_nucleo integer,
    id_asamblea integer,
    id_convenio integer,
    id_orv integer,
    fecha_programada_ingreso date,
    referencia_expediente character varying(150),
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    id_nucleo integer,
    CONSTRAINT chk_tramite_ran_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_tramite_ran_contexto CHECK ((((id_orv IS NOT NULL) AND (id_proyecto_nucleo IS NULL) AND (id_nucleo IS NOT NULL)) OR (((id_asamblea IS NOT NULL) OR (id_convenio IS NOT NULL)) AND (id_proyecto_nucleo IS NOT NULL) AND (id_nucleo IS NULL)))),
    CONSTRAINT chk_tramite_ran_objetivo CHECK ((num_nonnulls(id_asamblea, id_convenio, id_orv) = 1))
);


--
-- Name: TABLE tramite_ran; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.tramite_ran IS 'Tramite registral repetible 1:N por Asamblea, Convenio u ORV; ORV se contextualiza por NucleoAgrario.';


--
-- Name: COLUMN tramite_ran.id_proyecto_nucleo; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tramite_ran.id_proyecto_nucleo IS 'Contexto requerido para RAN de Asamblea/Convenio; NULL para ORV desde 038.';


--
-- Name: COLUMN tramite_ran.id_nucleo; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.tramite_ran.id_nucleo IS 'Contexto del RAN de ORV; deriva del NucleoAgrario del ORV.';


--
-- Name: tramite_ran_evento; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tramite_ran_evento (
    id_evento_ran bigint NOT NULL,
    id_tramite_ran bigint NOT NULL,
    ordinal integer NOT NULL,
    id_tipo_evento bigint NOT NULL,
    fecha_evento date,
    numero_solicitud character varying(150),
    resultado character varying(250),
    calificacion text,
    folio_referencia character varying(200),
    id_documento integer,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_evento_ran_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_evento_ran_ordinal CHECK ((ordinal > 0))
);


--
-- Name: TABLE tramite_ran_evento; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.tramite_ran_evento IS 'Eventos registrales normalizados. Una celda Excel con estatus textual sin fecha debe representarse en resultado/calificacion/folio y conservar su valor original en trazabilidad; no se convierte artificialmente a DATE.';


--
-- Name: tramite_ran_evento_id_evento_ran_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tramite_ran_evento ALTER COLUMN id_evento_ran ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tramite_ran_evento_id_evento_ran_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: tramite_ran_id_tramite_ran_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tramite_ran ALTER COLUMN id_tramite_ran ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tramite_ran_id_tramite_ran_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: trazabilidad_fuente; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trazabilidad_fuente (
    id_trazabilidad bigint NOT NULL,
    entidad_tipo character varying(50) NOT NULL,
    entidad_id bigint NOT NULL,
    archivo character varying(255) NOT NULL,
    hoja character varying(255),
    fila integer,
    columna character varying(120),
    valor_original text,
    tratamiento character varying(30) NOT NULL,
    registrado_en timestamp with time zone DEFAULT now() NOT NULL,
    id_usuario_registro integer,
    id_importacion_tabular bigint,
    valor_normalizado text,
    mensajes jsonb DEFAULT '[]'::jsonb NOT NULL,
    CONSTRAINT chk_trazabilidad_archivo CHECK ((NULLIF(btrim((archivo)::text), ''::text) IS NOT NULL)),
    CONSTRAINT chk_trazabilidad_fila CHECK (((fila IS NULL) OR (fila > 0))),
    CONSTRAINT chk_trazabilidad_tratamiento CHECK (((tratamiento)::text = ANY ((ARRAY['PERSISTIR'::character varying, 'DERIVAR'::character varying, 'REFERENCIA'::character varying, 'DOCUMENTAR'::character varying, 'REVISAR'::character varying, 'NO IMPLEMENTAR'::character varying])::text[])))
);


--
-- Name: trazabilidad_fuente_id_trazabilidad_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.trazabilidad_fuente ALTER COLUMN id_trazabilidad ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.trazabilidad_fuente_id_trazabilidad_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: trazo_proyecto; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trazo_proyecto (
    id_trazo integer NOT NULL,
    id_proyecto integer NOT NULL,
    version integer NOT NULL,
    geometria_linea public.geometry(MultiLineString,4326) NOT NULL,
    fuente character varying(250) NOT NULL,
    fecha_fuente date,
    fecha_vigencia_inicio date NOT NULL,
    fecha_vigencia_fin date,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_trazo_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_trazo_fuente CHECK ((NULLIF(btrim((fuente)::text), ''::text) IS NOT NULL)),
    CONSTRAINT chk_trazo_geometria CHECK (((NOT public.st_isempty(geometria_linea)) AND public.st_isvalid(geometria_linea) AND (public.st_srid(geometria_linea) = 4326) AND (public.geometrytype(geometria_linea) = 'MULTILINESTRING'::text))),
    CONSTRAINT chk_trazo_version CHECK ((version > 0)),
    CONSTRAINT chk_trazo_vigencia CHECK (((fecha_vigencia_fin IS NULL) OR (fecha_vigencia_fin >= fecha_vigencia_inicio)))
);


--
-- Name: trazo_proyecto_id_trazo_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.trazo_proyecto ALTER COLUMN id_trazo ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.trazo_proyecto_id_trazo_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: unidad_agraria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.unidad_agraria (
    id_unidad_agraria bigint NOT NULL,
    id_nucleo integer NOT NULL,
    id_tipo_tierra bigint NOT NULL,
    id_tipo_gestion bigint,
    id_destino_superficie bigint,
    id_tipo_titularidad bigint NOT NULL,
    id_parcela integer,
    referencia_alfanumerica character varying(150),
    referencia_normalizada character varying(150),
    detalle text,
    fuente character varying(250),
    requiere_revision boolean DEFAULT false NOT NULL,
    motivo_revision text,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_unidad_agraria_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_unidad_agraria_dato CHECK (((id_parcela IS NOT NULL) OR (id_tipo_gestion IS NOT NULL) OR (id_destino_superficie IS NOT NULL) OR (NULLIF(btrim((referencia_alfanumerica)::text), ''::text) IS NOT NULL) OR (NULLIF(btrim(detalle), ''::text) IS NOT NULL))),
    CONSTRAINT chk_unidad_agraria_revision CHECK (((NOT requiere_revision) OR (NULLIF(btrim(motivo_revision), ''::text) IS NOT NULL)))
);


--
-- Name: TABLE unidad_agraria; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.unidad_agraria IS 'Identidad de bien/unidad agraria del NucleoAgrario. No depende de un ProyectoNucleo ni de una Afectacion concreta.';


--
-- Name: COLUMN unidad_agraria.id_tipo_tierra; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.unidad_agraria.id_tipo_tierra IS 'Clasificacion normalizada; no se infiere automaticamente desde TIPO_GESTION ni destino.';


--
-- Name: COLUMN unidad_agraria.id_tipo_titularidad; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.unidad_agraria.id_tipo_titularidad IS 'Clasificacion normalizada de titularidad. Los titulares persona se detallan en unidad_agraria_titular.';


--
-- Name: COLUMN unidad_agraria.id_parcela; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.unidad_agraria.id_parcela IS 'Referencia opcional a parcela. Puede existir en unidades colectivas sin convertir la afectacion en individual.';


--
-- Name: unidad_agraria_id_unidad_agraria_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.unidad_agraria ALTER COLUMN id_unidad_agraria ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unidad_agraria_id_unidad_agraria_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: unidad_agraria_titular; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.unidad_agraria_titular (
    id_unidad_titular bigint NOT NULL,
    id_unidad_agraria bigint NOT NULL,
    id_persona integer,
    id_parcela_titular integer,
    porcentaje_participacion numeric(7,4),
    es_principal boolean DEFAULT false NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_unidad_titular_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL)))),
    CONSTRAINT chk_unidad_titular_objetivo CHECK ((num_nonnulls(id_persona, id_parcela_titular) = 1)),
    CONSTRAINT chk_unidad_titular_porcentaje CHECK (((porcentaje_participacion IS NULL) OR ((porcentaje_participacion > (0)::numeric) AND (porcentaje_participacion <= (100)::numeric))))
);


--
-- Name: TABLE unidad_agraria_titular; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.unidad_agraria_titular IS 'Titulares persona de una unidad agraria. Reutiliza Persona/ParcelaTitular y evita nombres libres como fuente canónica.';


--
-- Name: unidad_agraria_titular_id_unidad_titular_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.unidad_agraria_titular ALTER COLUMN id_unidad_titular ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unidad_agraria_titular_id_unidad_titular_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: usuario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario (
    id_usuario integer NOT NULL,
    nombre character varying(250) NOT NULL,
    apellido_paterno character varying(250) NOT NULL,
    apellido_materno character varying(250),
    correo character varying(320) NOT NULL,
    contrasena_hash character varying(255) NOT NULL,
    rol character varying(30) NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    fecha_alta timestamp with time zone DEFAULT now() NOT NULL,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    fecha_reactivacion timestamp with time zone,
    id_usuario_reactivacion integer,
    motivo_reactivacion text,
    observaciones text,
    CONSTRAINT usuario_rol_check CHECK (((rol)::text = ANY ((ARRAY['admin'::character varying, 'operador'::character varying, 'visualizador'::character varying, 'geografo'::character varying])::text[])))
);


--
-- Name: usuario_id_usuario_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_id_usuario_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_id_usuario_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_id_usuario_seq OWNED BY public.usuario.id_usuario;


--
-- Name: usuario_proyecto; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario_proyecto (
    id_usuario_proyecto integer NOT NULL,
    id_usuario integer NOT NULL,
    id_proyecto integer NOT NULL,
    asignado_por integer NOT NULL,
    fecha_asignacion timestamp with time zone DEFAULT now() NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    creado_por integer,
    actualizado_en timestamp with time zone,
    actualizado_por integer,
    fecha_baja timestamp with time zone,
    id_usuario_baja integer,
    motivo_baja text,
    observaciones text,
    CONSTRAINT chk_usuario_proyecto_baja CHECK (((activo AND (fecha_baja IS NULL) AND (id_usuario_baja IS NULL) AND (motivo_baja IS NULL)) OR ((NOT activo) AND (fecha_baja IS NOT NULL) AND (id_usuario_baja IS NOT NULL) AND (NULLIF(btrim(motivo_baja), ''::text) IS NOT NULL))))
);


--
-- Name: usuario_proyecto_id_usuario_proyecto_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.usuario_proyecto ALTER COLUMN id_usuario_proyecto ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.usuario_proyecto_id_usuario_proyecto_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: entidad_federativa id_entidad; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entidad_federativa ALTER COLUMN id_entidad SET DEFAULT nextval('public.entidad_federativa_id_entidad_seq'::regclass);


--
-- Name: evento_acceso id_evento; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_acceso ALTER COLUMN id_evento SET DEFAULT nextval('public.evento_acceso_id_evento_seq'::regclass);


--
-- Name: municipio id_municipio; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipio ALTER COLUMN id_municipio SET DEFAULT nextval('public.municipio_id_municipio_seq'::regclass);


--
-- Name: sesion_usuario id_sesion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario ALTER COLUMN id_sesion SET DEFAULT nextval('public.sesion_usuario_id_sesion_seq'::regclass);


--
-- Name: usuario id_usuario; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario ALTER COLUMN id_usuario SET DEFAULT nextval('public.usuario_id_usuario_seq'::regclass);


--
-- Migration ledger. Rows are written by backend/scripts/run_migrations.sh.
--

CREATE TABLE public.schema_migrations (
    version character varying(3) PRIMARY KEY,
    nombre character varying(200) NOT NULL,
    checksum_sha256 character(64) NOT NULL,
    aplicada_en timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_schema_migrations_version CHECK (version ~ '^[0-9]{3}$'),
    CONSTRAINT chk_schema_migrations_checksum CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$')
);

--
-- Structural catalogs (canonical application data).
--

INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (1, 'tipo_tenencia', 'ejido', 'Ejido', 'Núcleo agrario constituido como ejido.', 10, 'Ley Agraria/RAN', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (2, 'tipo_tenencia', 'comunidad', 'Comunidad', 'Núcleo agrario constituido como comunidad.', 20, 'Ley Agraria/RAN', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (3, 'residencia', 'naucalpan', 'Naucalpan', NULL, 10, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (4, 'residencia', 'atlacomulco', 'Atlacomulco', NULL, 20, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (5, 'residencia', 'tula', 'Tula', NULL, 30, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (6, 'residencia', 'queretaro', 'Querétaro', NULL, 40, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (7, 'tipo_gestion', 'PARCELA', 'Parcela', NULL, 10, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (8, 'tipo_gestion', 'TUC', 'Tierras de Uso Común (TUC)', NULL, 20, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (9, 'tipo_cop_operativo', 'ORIGEN', 'ORIGEN', 'cop_original; secuencia 1.', 10, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (10, 'tipo_cop_operativo', 'ADICIONAL', 'ADICIONAL', 'superficie_adicional; secuencia 1.', 20, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (11, 'tipo_cop_operativo', '2A_ADICIONAL', '2A ADICIONAL', 'superficie_adicional; secuencia 2.', 30, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (12, 'tipo_cop_operativo', 'COMPLEMENTARIAS', 'COMPLEMENTARIAS', 'obras_complementarias; secuencia 1.', 40, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (13, 'destino_superficie', 'tuc', 'Tierras de Uso Común', NULL, 10, 'Excel colectivo/RAN', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (14, 'destino_superficie', 'sin_asignar', 'Sin asignar', NULL, 20, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (15, 'destino_superficie', 'favor_nucleo', 'A favor del núcleo agrario', NULL, 30, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (16, 'destino_superficie', 'parcela_escolar', 'Parcela escolar', NULL, 40, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (17, 'destino_superficie', 'uaim', 'Unidad Agrícola Industrial de la Mujer (UAIM)', NULL, 50, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (18, 'destino_superficie', 'camino', 'Camino', NULL, 60, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (19, 'destino_superficie', 'canal', 'Canal de riego o dren', NULL, 70, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (20, 'destino_superficie', 'derecho_paso', 'Derecho de paso', NULL, 80, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (21, 'destino_superficie', 'servidumbre_paso', 'Servidumbre de paso', NULL, 90, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (22, 'destino_superficie', 'infraestructura', 'Infraestructura', NULL, 100, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (23, 'destino_superficie', 'asentamiento_humano', 'Asentamiento humano', NULL, 110, 'Excel colectivo/RAN', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (24, 'destino_superficie', 'parcela_ejidal', 'Parcela ejidal', NULL, 120, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (25, 'destino_superficie', 'solar', 'Solar', NULL, 130, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (26, 'destino_superficie', 'otro', 'Otro', NULL, 999, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (27, 'estado_registral_orv', 'no_ingresada', 'No ingresada', NULL, 10, 'Modelo operativo', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (28, 'estado_registral_orv', 'en_proceso', 'En proceso', NULL, 20, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (29, 'estado_registral_orv', 'prevenida', 'Prevenida', NULL, 30, 'Modelo registral RAN', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (30, 'estado_registral_orv', 'inscrita', 'Inscrita', NULL, 40, 'Excel colectivo/RAN', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (31, 'estado_registral_orv', 'otro', 'Otro', NULL, 999, 'Modelo operativo', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (32, 'organo_orv', 'comisariado', 'Comisariado', NULL, 10, 'Ley Agraria', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (33, 'organo_orv', 'consejo_vigilancia', 'Consejo de Vigilancia', NULL, 20, 'Ley Agraria', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (34, 'cargo_orv', 'presidente', 'Presidente', NULL, 10, 'Ley Agraria', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (35, 'cargo_orv', 'secretario', 'Secretario', NULL, 20, 'Ley Agraria', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (36, 'cargo_orv', 'tesorero', 'Tesorero', NULL, 30, 'Ley Agraria', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (37, 'cargo_orv', 'secretario_1', 'Secretario 1', NULL, 40, 'Fuente funcional', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (38, 'cargo_orv', 'secretario_2', 'Secretario 2', NULL, 50, 'Fuente funcional', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (39, 'calidad_integrante_orv', 'propietario', 'Propietario', NULL, 10, 'Ley Agraria', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (40, 'calidad_integrante_orv', 'suplente', 'Suplente', NULL, 20, 'Ley Agraria', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (41, 'tipo_asamblea', 'anuencia', 'Anuencia', NULL, 10, 'Excel colectivo/Reglamento MOPR', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (42, 'tipo_asamblea', 'retiro_fondos', 'Retiro de fondos', NULL, 20, 'Excel colectivo/FIFONAFE', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (43, 'tipo_asamblea', 'otra', 'Otra', NULL, 999, 'Modelo operativo', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (44, 'contexto_asamblea', 'cop_original', 'COP original', NULL, 10, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (45, 'contexto_asamblea', 'modificatorio', 'Modificatorio', NULL, 20, 'Dominio vigente', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (46, 'contexto_asamblea', 'superficie_adicional', 'Superficie adicional', NULL, 30, 'Dominio vigente', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (47, 'contexto_asamblea', 'obras_complementarias', 'Obras complementarias', NULL, 40, 'Dominio vigente', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (48, 'contexto_asamblea', 'retiro_fondos', 'Retiro de fondos', NULL, 50, 'Excel colectivo/FIFONAFE', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (49, 'contexto_asamblea', 'otro', 'Otro', NULL, 999, 'Modelo operativo', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (50, 'resultado_convocatoria', 'celebrada', 'Celebrada', NULL, 10, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (51, 'resultado_convocatoria', 'no_verificativo', 'No verificativo', NULL, 20, 'Excel colectivo/FIFONAFE', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (52, 'resultado_convocatoria', 'cancelada', 'Cancelada', NULL, 30, 'Modelo operativo', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (53, 'resultado_convocatoria', 'reprogramada', 'Reprogramada', NULL, 40, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (54, 'resultado_convocatoria', 'otro', 'Otro', NULL, 999, 'Modelo operativo', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (55, 'tipo_evento_ran', 'ingreso', 'Ingreso', NULL, 10, 'RAN/Excel colectivo', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (56, 'tipo_evento_ran', 'reingreso', 'Reingreso', NULL, 20, 'Modelo registral', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (57, 'tipo_evento_ran', 'prevencion', 'Prevención', NULL, 30, 'Modelo registral', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (58, 'tipo_evento_ran', 'subsanacion', 'Subsanación/corrección', NULL, 40, 'Modelo registral', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (59, 'tipo_evento_ran', 'desistimiento', 'Desistimiento', NULL, 50, 'Modelo registral', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (60, 'tipo_evento_ran', 'calificacion', 'Calificación', NULL, 60, 'RAN/Excel colectivo', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (61, 'tipo_evento_ran', 'inscripcion', 'Inscripción', NULL, 70, 'RAN/Excel colectivo', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (62, 'tipo_evento_ran', 'otro', 'Otro', NULL, 999, 'Modelo registral', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (63, 'tipo_evento_fifonafe', 'oficio_fifonafe_dgaopr', 'Oficio FIFONAFE a DGAOPR/Representación', NULL, 10, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (64, 'tipo_evento_fifonafe', 'oficio_dgaopr_representacion', 'Oficio DGAOPR a Representación', NULL, 20, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (65, 'tipo_evento_fifonafe', 'respuesta_representacion_dgaopr', 'Respuesta Representación a DGAOPR', NULL, 30, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (66, 'tipo_evento_fifonafe', 'respuesta_dgaopr_fifonafe', 'Respuesta DGAOPR/Representación a FIFONAFE', NULL, 40, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (67, 'tipo_evento_fifonafe', 'otro', 'Otro', NULL, 999, 'Modelo operativo', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (68, 'estado_requisito_documental', 'pendiente', 'Pendiente', NULL, 10, 'Modelo documental', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (69, 'estado_requisito_documental', 'disponible', 'Disponible', NULL, 20, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (70, 'estado_requisito_documental', 'faltante', 'Faltante', NULL, 30, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (71, 'estado_requisito_documental', 'no_aplica', 'No aplica', NULL, 40, 'Modelo documental', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (72, 'estado_requisito_documental', 'otro', 'Otro', NULL, 999, 'Modelo documental', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (78, 'tipo_tierra', 'uso_comun', 'Tierras de uso comun', 'Destino juridico/catastral de tierras de uso comun; no equivale por si solo a ambito colectivo.', 10, 'Ley Agraria/RAN', NULL, NULL, true, '2026-08-31 22:48:48.236083+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (79, 'tipo_tierra', 'parcelada', 'Tierra parcelada', 'Tierra identificada como parcelada; no determina por si sola el ambito de la afectacion.', 20, 'Ley Agraria/RAN', NULL, NULL, true, '2026-08-31 22:48:48.236083+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (80, 'tipo_tierra', 'asentamiento_humano', 'Asentamiento humano', 'Tierra destinada al asentamiento humano.', 30, 'Ley Agraria/RAN', NULL, NULL, true, '2026-08-31 22:48:48.236083+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (81, 'tipo_tierra', 'otra', 'Otra', NULL, 900, 'Modelo operativo', NULL, NULL, true, '2026-08-31 22:48:48.236083+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (82, 'tipo_tierra', 'no_determinada', 'No determinada', 'La fuente disponible no permite clasificar sin inferencia.', 999, 'Modelo operativo', NULL, NULL, true, '2026-08-31 22:48:48.236083+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (83, 'tipo_titularidad_unidad', 'nucleo_agrario', 'Nucleo agrario', 'El derecho/bien se administra como titularidad del nucleo agrario.', 10, 'Modelo agrario', NULL, NULL, true, '2026-08-31 22:48:48.236083+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (84, 'tipo_titularidad_unidad', 'persona', 'Persona titular', 'Existe una persona titular identificada mediante relaciones normalizadas.', 20, 'Modelo individual', NULL, NULL, true, '2026-08-31 22:48:48.236083+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (85, 'tipo_titularidad_unidad', 'copropiedad', 'Copropiedad / cotitularidad', 'Existen dos o mas titulares identificados.', 30, 'Modelo individual', NULL, NULL, true, '2026-08-31 22:48:48.236083+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (86, 'tipo_titularidad_unidad', 'no_determinada', 'No determinada', 'La fuente no permite establecer titularidad sin revision.', 900, 'Modelo operativo', NULL, NULL, true, '2026-08-31 22:48:48.236083+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (87, 'tipo_titularidad_unidad', 'otra', 'Otra', NULL, 999, 'Modelo operativo', NULL, NULL, true, '2026-08-31 22:48:48.236083+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (88, 'motivo_no_afecta_tuc', 'expropiacion_directa', 'Expropiacion directa', 'Salida operativa cuando no se da seguimiento PA a TUC por expropiacion directa.', 10, 'Fuente funcional', NULL, NULL, true, '2026-08-31 22:48:48.236083+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (89, 'motivo_no_afecta_tuc', 'comunidad_indigena', 'Comunidad indigena', 'Motivo operativo diferenciado; no sustituye nucleo_agrario.comunidad_indigena.', 20, 'Fuente funcional', NULL, NULL, true, '2026-08-31 22:48:48.236083+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (90, 'motivo_no_afecta_tuc', 'no_afectacion_colectiva', 'No existe afectacion colectiva a TUC', 'El proyecto no afecta tierras de uso comun en el contexto del expediente.', 30, 'Fuente funcional', NULL, NULL, true, '2026-08-31 22:48:48.236083+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (91, 'motivo_no_afecta_tuc', 'otro', 'Otro', NULL, 999, 'Modelo operativo', NULL, NULL, true, '2026-08-31 22:48:48.236083+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (92, 'calidad_compareciente_convenio', 'titular_parcelario', 'Titular parcelario', 'Persona que comparece como titular acreditado de derechos sobre la parcela.', 10, 'Ley Agraria arts. 76-79 / RLA-MOPR arts. 56-58', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (93, 'calidad_compareciente_convenio', 'cotitular', 'Cotitular', 'Persona que comparece como cotitular o coparticipe acreditado.', 20, 'Modelo individual / evidencia registral', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (94, 'calidad_compareciente_convenio', 'sucesor_acreditado', 'Sucesor acreditado', 'Persona que acredita sucesion o transmision de derechos mediante documento competente.', 30, 'RAN/FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (95, 'calidad_compareciente_convenio', 'beneficiario', 'Beneficiario', 'Beneficiario del pago; no implica por si mismo titularidad parcelaria ni facultad para firmar el COP.', 40, 'FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (96, 'calidad_compareciente_convenio', 'representante', 'Representante', 'Persona que comparece mediante representacion acreditada; no sustituye la acreditacion del derecho.', 50, 'Modelo juridico', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (97, 'calidad_compareciente_convenio', 'otro', 'Otro', NULL, 999, 'Modelo operativo', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (98, 'tipo_acreditacion_derecho_individual', 'certificado_derechos_agrarios', 'Certificado de derechos agrarios', NULL, 10, 'Ley Agraria art. 78 / PA / FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (99, 'tipo_acreditacion_derecho_individual', 'certificado_parcelario', 'Certificado parcelario', NULL, 20, 'Ley Agraria art. 78 / PA / FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (100, 'tipo_acreditacion_derecho_individual', 'resolucion_tribunal_agrario', 'Resolucion o sentencia de Tribunal Agrario', NULL, 30, 'Ley Agraria art. 78 / PA / FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (101, 'tipo_acreditacion_derecho_individual', 'constancia_ran_vigente', 'Constancia RAN de vigencia de derechos', NULL, 40, 'RAN-04-051 / PA / FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (102, 'tipo_acreditacion_derecho_individual', 'traslado_derechos', 'Traslado/transmision de derechos acreditado', NULL, 50, 'RAN/FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (103, 'tipo_acreditacion_derecho_individual', 'otra', 'Otra acreditacion', NULL, 999, 'Modelo operativo', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (104, 'tipo_evento_fifonafe', 'solicitud_retiro_individual', 'Solicitud de retiro de fondos de uso individual', 'Solicitud suscrita por titular o beneficiario para retiro individual.', 5, 'FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (105, 'tipo_evento_fifonafe', 'acuse_retiro_individual', 'Acuse de expediente de retiro individual', 'Recepcion/acuse del expediente individual ante FIFONAFE.', 6, 'FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo (id_catalogo_opcion, tipo_catalogo, codigo, nombre, descripcion, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (106, 'tipo_evento_fifonafe', 'resolucion_retiro_individual', 'Resolucion del retiro individual', 'Resolucion administrativa del tramite de retiro individual.', 45, 'FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo_alias (id_catalogo_alias, id_catalogo_opcion, alias, alias_normalizado, fuente, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (1, 6, 'QUERETARO', 'QUERETARO', 'Excel colectivo 2026', true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo_alias (id_catalogo_alias, id_catalogo_opcion, alias, alias_normalizado, fuente, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (2, 11, '2A ADICIONAL', '2A ADICIONAL', 'Excel colectivo 2026', true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo_alias (id_catalogo_alias, id_catalogo_opcion, alias, alias_normalizado, fuente, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (3, 13, 'TIERRAS DE USO COMÚN', 'TIERRAS DE USO COMUN', 'Excel colectivo 2026', true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo_alias (id_catalogo_alias, id_catalogo_opcion, alias, alias_normalizado, fuente, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (4, 14, 'SIN ASIGNAR', 'SIN ASIGNAR', 'Excel colectivo 2026', true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo_alias (id_catalogo_alias, id_catalogo_opcion, alias, alias_normalizado, fuente, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (5, 15, 'A FAVOR DEL NÚCLEO AGRARIO', 'A FAVOR DEL NUCLEO AGRARIO', 'Excel colectivo 2026', true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo_alias (id_catalogo_alias, id_catalogo_opcion, alias, alias_normalizado, fuente, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (6, 16, 'PARCELA ESCOLAR', 'PARCELA ESCOLAR', 'Excel colectivo 2026', true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo_alias (id_catalogo_alias, id_catalogo_opcion, alias, alias_normalizado, fuente, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (7, 17, 'UNIDAD AGRICOLA INDUSTRIAL DE LA MUJER', 'UNIDAD AGRICOLA INDUSTRIAL DE LA MUJER', 'Excel colectivo 2026', true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo_alias (id_catalogo_alias, id_catalogo_opcion, alias, alias_normalizado, fuente, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (8, 18, 'CAMINOS', 'CAMINOS', 'Excel colectivo 2026', true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo_alias (id_catalogo_alias, id_catalogo_opcion, alias, alias_normalizado, fuente, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (9, 19, 'CANAL DE RIEGO Y DRENES', 'CANAL DE RIEGO Y DRENES', 'Excel colectivo 2026', true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo_alias (id_catalogo_alias, id_catalogo_opcion, alias, alias_normalizado, fuente, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (10, 19, 'CANAL', 'CANAL', 'Excel colectivo 2026', true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo_alias (id_catalogo_alias, id_catalogo_opcion, alias, alias_normalizado, fuente, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (11, 20, 'DERECHO DE PASO', 'DERECHO DE PASO', 'Excel colectivo 2026', true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo_alias (id_catalogo_alias, id_catalogo_opcion, alias, alias_normalizado, fuente, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (12, 21, 'SERVIDUMBRE DE PASO', 'SERVIDUMBRE DE PASO', 'Excel colectivo 2026', true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo_alias (id_catalogo_alias, id_catalogo_opcion, alias, alias_normalizado, fuente, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (13, 23, 'ASENTAMIENTO HUMANO', 'ASENTAMIENTO HUMANO', 'Excel colectivo 2026', true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.catalogo_operativo_alias (id_catalogo_alias, id_catalogo_opcion, alias, alias_normalizado, fuente, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (14, 24, 'PARCELA EJIDAL', 'PARCELA EJIDAL', 'Excel colectivo 2026', true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (1, 'padron', 'Padrón de ejidatarios/comuneros', NULL, 'datos_generales', false, 10, 'Excel colectivo/FIFONAFE', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (2, 'acta_eleccion_orv', 'Acta de elección de ORV', NULL, 'orv', false, 20, 'Excel colectivo/FIFONAFE', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (3, 'constancia_orv_ran', 'Constancia/inscripción ORV en RAN', NULL, 'orv', false, 30, 'Excel colectivo/RAN', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (4, 'convocatoria_asamblea', 'Convocatoria de asamblea', NULL, 'asamblea', false, 40, 'Excel colectivo/FIFONAFE', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (5, 'acta_no_verificativo', 'Acta de no verificativo', NULL, 'asamblea', false, 50, 'Excel colectivo/FIFONAFE', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (6, 'acta_asamblea', 'Acta de asamblea', NULL, 'asamblea', false, 60, 'Excel colectivo/FIFONAFE', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (7, 'convenio_ocupacion_previa', 'Convenio de ocupación previa', NULL, 'convenio', false, 70, 'Excel colectivo/Reglamento MOPR', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (8, 'acuse_ran', 'Acuse de ingreso al RAN', NULL, 'ran', false, 80, 'Excel colectivo/RAN', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (9, 'soporte_sensibilizacion', 'Soporte de sensibilización', NULL, 'actividad', false, 90, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (10, 'soporte_caminamiento', 'Soporte de caminamiento', NULL, 'actividad', false, 100, 'Excel colectivo 2026', NULL, NULL, true, '2026-08-31 20:47:15.152482+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (11, 'ind_derecho_acreditacion', 'Acreditacion del derecho individual', 'Evidencia vigente del derecho sobre la parcela. Puede acreditarse con certificado de derechos agrarios/parcelario, resolucion del Tribunal Agrario o constancia RAN vigente, segun corresponda.', 'individual_parcela', true, 10, 'Ley Agraria art. 78 / PA / RAN', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (12, 'ind_convenio_firmado', 'Convenio individual firmado', 'Instrumento suscrito para la ocupacion previa individual; se instancia por cada COP original, modificatorio, ampliacion o remanente aplicable.', 'individual_convenio', true, 20, 'RLA-MOPR arts. 56-58 / PA', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (13, 'ind_ran_acuse_ingreso', 'Acuse o evidencia de ingreso al RAN', 'Evidencia documental del ingreso/reingreso del instrumento al Registro Agrario Nacional.', 'individual_ran', true, 30, 'RLA-MOPR art. 58 / flujo PA-RAN', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (14, 'ind_ran_inscripcion', 'Aviso/constancia de inscripcion RAN', 'Evidencia documental de la inscripcion del instrumento cuando el tramite haya concluido favorablemente.', 'individual_ran', true, 40, 'RAN / flujo operativo individual', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (15, 'ind_fif_solicitud_retiro', 'Solicitud de retiro de fondos de uso individual', 'Solicitud escrita de retiro de fondos de uso individual con origen, monto, destino y forma de pago.', 'individual_fifonafe', true, 50, 'FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (16, 'ind_fif_acreditacion_derecho', 'Acreditacion de derecho para FIFONAFE', 'Certificado de derechos agrarios/parcelarios, resolucion competente o constancia RAN vigente a favor del beneficiario, segun corresponda.', 'individual_fifonafe', true, 60, 'FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (17, 'ind_fif_identificacion_oficial', 'Identificacion oficial vigente', 'Identificacion oficial del solicitante/beneficiario para el tramite individual.', 'individual_fifonafe', true, 70, 'FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (18, 'ind_fif_curp', 'CURP del solicitante/beneficiario', 'CURP requerida para el expediente individual FIFONAFE.', 'individual_fifonafe', true, 80, 'FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (19, 'ind_fif_cuenta_bancaria', 'Cuenta/CLABE para transferencia', 'Contrato o version publica de estado de cuenta con institucion, titular, cuenta y CLABE; aplica cuando el pago sea por transferencia.', 'individual_fifonafe', false, 90, 'FIFONAFE', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (20, 'ind_fif_sucesion', 'Resolucion o acreditacion de sucesion', 'Documento competente cuando el solicitante actua como sucesor/beneficiario y resulte aplicable.', 'individual_fifonafe', false, 100, 'FIFONAFE/RAN/TUA', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO public.requisito_documental (id_requisito, codigo, nombre, descripcion, contexto, obligatorio, orden, fuente, vigencia_inicio, vigencia_fin, activo, creado_en, creado_por, actualizado_en, actualizado_por, fecha_baja, id_usuario_baja, motivo_baja, observaciones) VALUES (21, 'ind_fif_parcela_sin_asignar', 'Acreditacion de asignacion de parcela previamente no asignada', 'Resolucion competente o acta de asamblea inscrita en RAN que acredite la asignacion cuando el supuesto resulte aplicable.', 'individual_fifonafe', false, 110, 'FIFONAFE/RAN', NULL, NULL, true, '2026-09-01 23:43:37.922284+00', NULL, NULL, NULL, NULL, NULL, NULL, NULL);
SELECT pg_catalog.setval('public.catalogo_operativo_alias_id_catalogo_alias_seq', 14, true);
SELECT pg_catalog.setval('public.catalogo_operativo_id_catalogo_opcion_seq', 106, true);
SELECT pg_catalog.setval('public.requisito_documental_id_requisito_seq', 21, true);

--
-- Name: actividad_campo actividad_campo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividad_campo
    ADD CONSTRAINT actividad_campo_pkey PRIMARY KEY (id_actividad);


--
-- Name: afectacion afectacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.afectacion
    ADD CONSTRAINT afectacion_pkey PRIMARY KEY (id_afectacion);


--
-- Name: afectacion_unidad_agraria afectacion_unidad_agraria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.afectacion_unidad_agraria
    ADD CONSTRAINT afectacion_unidad_agraria_pkey PRIMARY KEY (id_afectacion_unidad);


--
-- Name: asamblea_convocatoria asamblea_convocatoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea_convocatoria
    ADD CONSTRAINT asamblea_convocatoria_pkey PRIMARY KEY (id_convocatoria);


--
-- Name: asamblea asamblea_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea
    ADD CONSTRAINT asamblea_pkey PRIMARY KEY (id_asamblea);


--
-- Name: bitacora bitacora_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bitacora
    ADD CONSTRAINT bitacora_pkey PRIMARY KEY (id_bitacora);


--
-- Name: catalogo_alias_territorial catalogo_alias_territorial_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_alias_territorial
    ADD CONSTRAINT catalogo_alias_territorial_pkey PRIMARY KEY (id_alias);


--
-- Name: catalogo_operativo_alias catalogo_operativo_alias_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_operativo_alias
    ADD CONSTRAINT catalogo_operativo_alias_pkey PRIMARY KEY (id_catalogo_alias);


--
-- Name: catalogo_operativo catalogo_operativo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_operativo
    ADD CONSTRAINT catalogo_operativo_pkey PRIMARY KEY (id_catalogo_opcion);


--
-- Name: convenio_afectacion convenio_afectacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_afectacion
    ADD CONSTRAINT convenio_afectacion_pkey PRIMARY KEY (id_convenio_afectacion);


--
-- Name: convenio_compareciente convenio_compareciente_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_compareciente
    ADD CONSTRAINT convenio_compareciente_pkey PRIMARY KEY (id_compareciente);


--
-- Name: convenio convenio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio
    ADD CONSTRAINT convenio_pkey PRIMARY KEY (id_convenio);


--
-- Name: documento documento_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento
    ADD CONSTRAINT documento_pkey PRIMARY KEY (id_documento);


--
-- Name: documento_version documento_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_version
    ADD CONSTRAINT documento_version_pkey PRIMARY KEY (id_documento_version);


--
-- Name: documento_vinculo documento_vinculo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_vinculo
    ADD CONSTRAINT documento_vinculo_pkey PRIMARY KEY (id_documento_vinculo);


--
-- Name: entidad_federativa entidad_federativa_clave_inegi_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entidad_federativa
    ADD CONSTRAINT entidad_federativa_clave_inegi_key UNIQUE (clave_inegi);


--
-- Name: entidad_federativa entidad_federativa_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entidad_federativa
    ADD CONSTRAINT entidad_federativa_pkey PRIMARY KEY (id_entidad);


--
-- Name: estado_autenticacion_usuario estado_autenticacion_usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.estado_autenticacion_usuario
    ADD CONSTRAINT estado_autenticacion_usuario_pkey PRIMARY KEY (id_usuario);


--
-- Name: evento_acceso evento_acceso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_acceso
    ADD CONSTRAINT evento_acceso_pkey PRIMARY KEY (id_evento);


--
-- Name: expediente_requisito expediente_requisito_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_requisito
    ADD CONSTRAINT expediente_requisito_pkey PRIMARY KEY (id_expediente_requisito);


--
-- Name: importacion_archivo importacion_archivo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_archivo
    ADD CONSTRAINT importacion_archivo_pkey PRIMARY KEY (id_importacion);


--
-- Name: importacion_feature importacion_feature_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_feature
    ADD CONSTRAINT importacion_feature_pkey PRIMARY KEY (id_importacion_feature);


--
-- Name: importacion_tabular_celda importacion_tabular_celda_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_tabular_celda
    ADD CONSTRAINT importacion_tabular_celda_pkey PRIMARY KEY (id_importacion_celda);


--
-- Name: importacion_tabular importacion_tabular_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_tabular
    ADD CONSTRAINT importacion_tabular_pkey PRIMARY KEY (id_importacion_tabular);


--
-- Name: indemnizacion indemnizacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.indemnizacion
    ADD CONSTRAINT indemnizacion_pkey PRIMARY KEY (id_indemnizacion);


--
-- Name: municipio municipio_clave_inegi_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipio
    ADD CONSTRAINT municipio_clave_inegi_key UNIQUE (clave_inegi);


--
-- Name: municipio municipio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipio
    ADD CONSTRAINT municipio_pkey PRIMARY KEY (id_municipio);


--
-- Name: nucleo_agrario nucleo_agrario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nucleo_agrario
    ADD CONSTRAINT nucleo_agrario_pkey PRIMARY KEY (id_nucleo);


--
-- Name: orv_integrante orv_integrante_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv_integrante
    ADD CONSTRAINT orv_integrante_pkey PRIMARY KEY (id_orv_integrante);


--
-- Name: orv orv_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv
    ADD CONSTRAINT orv_pkey PRIMARY KEY (id_orv);


--
-- Name: padron_historial padron_historial_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.padron_historial
    ADD CONSTRAINT padron_historial_pkey PRIMARY KEY (id_padron);


--
-- Name: pago pago_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pago
    ADD CONSTRAINT pago_pkey PRIMARY KEY (id_pago);


--
-- Name: parcela parcela_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcela
    ADD CONSTRAINT parcela_pkey PRIMARY KEY (id_parcela);


--
-- Name: parcela_titular parcela_titular_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcela_titular
    ADD CONSTRAINT parcela_titular_pkey PRIMARY KEY (id_parcela_titular);


--
-- Name: perfil_mapeo_importacion perfil_mapeo_importacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.perfil_mapeo_importacion
    ADD CONSTRAINT perfil_mapeo_importacion_pkey PRIMARY KEY (id_perfil);


--
-- Name: persona persona_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona
    ADD CONSTRAINT persona_pkey PRIMARY KEY (id_persona);


--
-- Name: proyecto proyecto_clave_proyecto_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto
    ADD CONSTRAINT proyecto_clave_proyecto_key UNIQUE (clave_proyecto);


--
-- Name: proyecto_nucleo proyecto_nucleo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo
    ADD CONSTRAINT proyecto_nucleo_pkey PRIMARY KEY (id_proyecto_nucleo);


--
-- Name: proyecto_nucleo_referencia proyecto_nucleo_referencia_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo_referencia
    ADD CONSTRAINT proyecto_nucleo_referencia_pkey PRIMARY KEY (id_referencia);


--
-- Name: proyecto_nucleo_responsable proyecto_nucleo_responsable_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo_responsable
    ADD CONSTRAINT proyecto_nucleo_responsable_pkey PRIMARY KEY (id_responsable);


--
-- Name: proyecto proyecto_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto
    ADD CONSTRAINT proyecto_pkey PRIMARY KEY (id_proyecto);


--
-- Name: requisito_documental requisito_documental_codigo_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requisito_documental
    ADD CONSTRAINT requisito_documental_codigo_key UNIQUE (codigo);


--
-- Name: requisito_documental requisito_documental_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requisito_documental
    ADD CONSTRAINT requisito_documental_pkey PRIMARY KEY (id_requisito);


--
-- Name: sesion_usuario sesion_usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario
    ADD CONSTRAINT sesion_usuario_pkey PRIMARY KEY (id_sesion);


--
-- Name: sesion_usuario sesion_usuario_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario
    ADD CONSTRAINT sesion_usuario_token_hash_key UNIQUE (token_hash);


--
-- Name: tramite_fifonafe_afectacion tramite_fifonafe_afectacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe_afectacion
    ADD CONSTRAINT tramite_fifonafe_afectacion_pkey PRIMARY KEY (id_tramite_fifonafe_afectacion);


--
-- Name: tramite_fifonafe_evento tramite_fifonafe_evento_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe_evento
    ADD CONSTRAINT tramite_fifonafe_evento_pkey PRIMARY KEY (id_evento_fifonafe);


--
-- Name: tramite_fifonafe tramite_fifonafe_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe
    ADD CONSTRAINT tramite_fifonafe_pkey PRIMARY KEY (id_tramite_fifonafe);


--
-- Name: tramite_ran_evento tramite_ran_evento_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran_evento
    ADD CONSTRAINT tramite_ran_evento_pkey PRIMARY KEY (id_evento_ran);


--
-- Name: tramite_ran tramite_ran_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran
    ADD CONSTRAINT tramite_ran_pkey PRIMARY KEY (id_tramite_ran);


--
-- Name: trazabilidad_fuente trazabilidad_fuente_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trazabilidad_fuente
    ADD CONSTRAINT trazabilidad_fuente_pkey PRIMARY KEY (id_trazabilidad);


--
-- Name: trazo_proyecto trazo_proyecto_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trazo_proyecto
    ADD CONSTRAINT trazo_proyecto_pkey PRIMARY KEY (id_trazo);


--
-- Name: unidad_agraria unidad_agraria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria
    ADD CONSTRAINT unidad_agraria_pkey PRIMARY KEY (id_unidad_agraria);


--
-- Name: unidad_agraria_titular unidad_agraria_titular_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria_titular
    ADD CONSTRAINT unidad_agraria_titular_pkey PRIMARY KEY (id_unidad_titular);


--
-- Name: catalogo_operativo_alias uq_catalogo_alias; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_operativo_alias
    ADD CONSTRAINT uq_catalogo_alias UNIQUE (id_catalogo_opcion, alias_normalizado);


--
-- Name: catalogo_operativo uq_catalogo_operativo_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_operativo
    ADD CONSTRAINT uq_catalogo_operativo_codigo UNIQUE (tipo_catalogo, codigo);


--
-- Name: documento_version uq_documento_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_version
    ADD CONSTRAINT uq_documento_hash UNIQUE (id_documento, hash_sha256);


--
-- Name: documento_version uq_documento_ruta; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_version
    ADD CONSTRAINT uq_documento_ruta UNIQUE (ruta_almacenamiento);


--
-- Name: documento_version uq_documento_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_version
    ADD CONSTRAINT uq_documento_version UNIQUE (id_documento, numero_version);


--
-- Name: importacion_feature uq_importacion_feature; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_feature
    ADD CONSTRAINT uq_importacion_feature UNIQUE (id_importacion, indice_feature);


--
-- Name: importacion_tabular uq_importacion_tabular; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_tabular
    ADD CONSTRAINT uq_importacion_tabular UNIQUE (id_proyecto, sha256, hoja);


--
-- Name: importacion_tabular_celda uq_importacion_tabular_celda; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_tabular_celda
    ADD CONSTRAINT uq_importacion_tabular_celda UNIQUE (id_importacion_tabular, fila, columna);


--
-- Name: municipio uq_municipio_entidad_clave; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipio
    ADD CONSTRAINT uq_municipio_entidad_clave UNIQUE (id_entidad, clave_inegi);


--
-- Name: trazo_proyecto uq_trazo_proyecto_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trazo_proyecto
    ADD CONSTRAINT uq_trazo_proyecto_version UNIQUE (id_proyecto, version);


--
-- Name: usuario usuario_correo_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_correo_key UNIQUE (correo);


--
-- Name: usuario usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_pkey PRIMARY KEY (id_usuario);


--
-- Name: usuario_proyecto usuario_proyecto_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_proyecto
    ADD CONSTRAINT usuario_proyecto_pkey PRIMARY KEY (id_usuario_proyecto);


--
-- Name: idx_auth_evento_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auth_evento_fecha ON public.evento_acceso USING btree (fecha_hora DESC);


--
-- Name: idx_auth_evento_usuario_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auth_evento_usuario_fecha ON public.evento_acceso USING btree (id_usuario, fecha_hora DESC);


--
-- Name: idx_auth_sesion_actividad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auth_sesion_actividad ON public.sesion_usuario USING btree (ultima_actividad) WHERE (revocada_en IS NULL);


--
-- Name: idx_auth_sesion_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auth_sesion_usuario ON public.sesion_usuario USING btree (id_usuario, expira_en DESC);


--
-- Name: idx_actividad_afectacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actividad_afectacion ON public.actividad_campo USING btree (id_afectacion, fecha_realizada DESC, id_actividad DESC) WHERE (activo AND (id_afectacion IS NOT NULL));


--
-- Name: idx_compareciente_convenio; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_compareciente_convenio ON public.convenio_compareciente USING btree (id_convenio, es_firmante DESC, id_compareciente) WHERE activo;


--
-- Name: idx_compareciente_persona; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_compareciente_persona ON public.convenio_compareciente USING btree (id_persona, id_convenio) WHERE activo;


--
-- Name: idx_expediente_requisito_objetivo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_expediente_requisito_objetivo ON public.expediente_requisito USING btree (entidad_tipo, entidad_id, id_estado) WHERE activo;


--
-- Name: idx_actividad_fechas; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actividad_fechas ON public.actividad_campo USING btree (fecha_programada, fecha_realizada) WHERE activo;


--
-- Name: idx_actividad_pn_tipo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actividad_pn_tipo ON public.actividad_campo USING btree (id_proyecto_nucleo, tipo_actividad, contexto_actividad) WHERE activo;


--
-- Name: idx_afectacion_condicion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_afectacion_condicion ON public.afectacion USING btree (condicion_especial) WHERE activo;


--
-- Name: idx_afectacion_pn_tipo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_afectacion_pn_tipo ON public.afectacion USING btree (id_proyecto_nucleo, tipo_afectacion) WHERE activo;


--
-- Name: idx_afectacion_tipo_cop_operativo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_afectacion_tipo_cop_operativo ON public.afectacion USING btree (id_tipo_cop_operativo) WHERE (activo AND (id_tipo_cop_operativo IS NOT NULL));


--
-- Name: idx_afectacion_unidad_unidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_afectacion_unidad_unidad ON public.afectacion_unidad_agraria USING btree (id_unidad_agraria) WHERE activo;


--
-- Name: idx_bitacora_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bitacora_fecha ON public.bitacora USING btree (fecha_hora DESC);


--
-- Name: idx_bitacora_objetivo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bitacora_objetivo ON public.bitacora USING btree (entidad_tipo, entidad_id);


--
-- Name: idx_bitacora_pn; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bitacora_pn ON public.bitacora USING btree (id_proyecto_nucleo, fecha_hora DESC);


--
-- Name: idx_bitacora_proyecto; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bitacora_proyecto ON public.bitacora USING btree (id_proyecto, fecha_hora DESC);


--
-- Name: idx_bitacora_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bitacora_usuario ON public.bitacora USING btree (id_usuario, fecha_hora DESC);


--
-- Name: idx_catalogo_alias_busqueda; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_catalogo_alias_busqueda ON public.catalogo_operativo_alias USING btree (alias_normalizado) WHERE activo;


--
-- Name: idx_catalogo_operativo_lista; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_catalogo_operativo_lista ON public.catalogo_operativo USING btree (tipo_catalogo, activo DESC, orden, nombre);


--
-- Name: idx_convenio_afectacion_afectacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_convenio_afectacion_afectacion ON public.convenio_afectacion USING btree (id_afectacion) WHERE activo;


--
-- Name: idx_convenio_padre; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_convenio_padre ON public.convenio USING btree (id_convenio_padre) WHERE activo;


--
-- Name: idx_convenio_pn_ambito_tipo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_convenio_pn_ambito_tipo ON public.convenio USING btree (id_proyecto_nucleo, ambito, tipo_convenio) WHERE activo;


--
-- Name: idx_convocatoria_fechas; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_convocatoria_fechas ON public.asamblea_convocatoria USING btree (fecha_programada, fecha_realizacion) WHERE activo;


--
-- Name: idx_documento_tipo_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documento_tipo_estado ON public.documento USING btree (tipo_documento, estado) WHERE activo;


--
-- Name: idx_documento_vinculo_objetivo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documento_vinculo_objetivo ON public.documento_vinculo USING btree (entidad_tipo, entidad_id) WHERE activo;


--
-- Name: idx_evento_fifonafe_historial; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evento_fifonafe_historial ON public.tramite_fifonafe_evento USING btree (id_tramite_fifonafe, fecha_oficio, ordinal) WHERE activo;


--
-- Name: idx_evento_ran_historial; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evento_ran_historial ON public.tramite_ran_evento USING btree (id_tramite_ran, fecha_evento, ordinal) WHERE activo;


--
-- Name: idx_evento_ran_solicitud; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evento_ran_solicitud ON public.tramite_ran_evento USING btree (numero_solicitud) WHERE (activo AND (numero_solicitud IS NOT NULL));


--
-- Name: idx_expediente_requisito_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_expediente_requisito_estado ON public.expediente_requisito USING btree (id_proyecto_nucleo, id_estado) WHERE activo;


--
-- Name: idx_fifonafe_afectacion_afectacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fifonafe_afectacion_afectacion ON public.tramite_fifonafe_afectacion USING btree (id_afectacion) WHERE activo;


--
-- Name: idx_fifonafe_pn_ambito; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fifonafe_pn_ambito ON public.tramite_fifonafe USING btree (id_proyecto_nucleo, ambito, estatus) WHERE activo;


--
-- Name: idx_importacion_celda_objetivo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_importacion_celda_objetivo ON public.importacion_tabular_celda USING btree (entidad_tipo, entidad_id) WHERE (entidad_id IS NOT NULL);


--
-- Name: idx_importacion_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_importacion_estado ON public.importacion_archivo USING btree (id_proyecto, estado, fecha_carga DESC) WHERE activo;


--
-- Name: idx_importacion_feature_destino; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_importacion_feature_destino ON public.importacion_feature USING btree (registro_destino_id) WHERE (registro_destino_id IS NOT NULL);


--
-- Name: idx_importacion_feature_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_importacion_feature_estado ON public.importacion_feature USING btree (id_importacion, estado);


--
-- Name: idx_importacion_feature_geom; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_importacion_feature_geom ON public.importacion_feature USING gist (geometria_normalizada);


--
-- Name: idx_importacion_tabular_proyecto; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_importacion_tabular_proyecto ON public.importacion_tabular USING btree (id_proyecto, creado_en DESC) WHERE activo;


--
-- Name: idx_importacion_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_importacion_usuario ON public.importacion_archivo USING btree (id_usuario_carga, fecha_carga DESC) WHERE activo;


--
-- Name: idx_indemnizacion_estatus; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_indemnizacion_estatus ON public.indemnizacion USING btree (estatus) WHERE activo;


--
-- Name: idx_nucleo_geometria; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nucleo_geometria ON public.nucleo_agrario USING gist (geometria_poligono);


--
-- Name: idx_orv_integrante_persona; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orv_integrante_persona ON public.orv_integrante USING btree (id_persona) WHERE activo;


--
-- Name: idx_orv_nucleo_fin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orv_nucleo_fin ON public.orv USING btree (id_nucleo, fin_vigencia) WHERE activo;


--
-- Name: idx_padron_nucleo_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_padron_nucleo_fecha ON public.padron_historial USING btree (id_nucleo, fecha_padron DESC) WHERE activo;


--
-- Name: idx_pago_indemnizacion_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pago_indemnizacion_fecha ON public.pago USING btree (id_indemnizacion, fecha_pago) WHERE activo;


--
-- Name: idx_pago_persona; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pago_persona ON public.pago USING btree (id_persona_beneficiaria) WHERE activo;


--
-- Name: idx_parcela_certificado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parcela_certificado ON public.parcela USING btree (certificado_parcelario) WHERE activo;


--
-- Name: idx_parcela_folio; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parcela_folio ON public.parcela USING btree (folio_derechos) WHERE activo;


--
-- Name: idx_parcela_geometria; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parcela_geometria ON public.parcela USING gist (geometria_poligono);


--
-- Name: idx_parcela_titular_persona; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parcela_titular_persona ON public.parcela_titular USING btree (id_persona) WHERE activo;


--
-- Name: idx_persona_nombre; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_persona_nombre ON public.persona USING btree (lower((nombre)::text), lower((apellido_paterno)::text), lower((apellido_materno)::text));


--
-- Name: idx_proyecto_nombre; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_proyecto_nombre ON public.proyecto USING btree (lower((nombre_proyecto)::text));


--
-- Name: idx_proyecto_nucleo_nucleo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_proyecto_nucleo_nucleo ON public.proyecto_nucleo USING btree (id_nucleo) WHERE activo;


--
-- Name: idx_requisito_lista; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_requisito_lista ON public.requisito_documental USING btree (contexto, activo DESC, orden, nombre);


--
-- Name: idx_responsable_historial; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_responsable_historial ON public.proyecto_nucleo_responsable USING btree (id_proyecto_nucleo, vigencia_inicio DESC);


--
-- Name: idx_tramite_ran_asamblea; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_ran_asamblea ON public.tramite_ran USING btree (id_asamblea, creado_en DESC, id_tramite_ran DESC) WHERE (activo AND (id_asamblea IS NOT NULL));


--
-- Name: idx_tramite_ran_convenio; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_ran_convenio ON public.tramite_ran USING btree (id_convenio, creado_en DESC, id_tramite_ran DESC) WHERE (activo AND (id_convenio IS NOT NULL));


--
-- Name: idx_tramite_ran_nucleo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_ran_nucleo ON public.tramite_ran USING btree (id_nucleo, creado_en DESC, id_tramite_ran DESC) WHERE (activo AND (id_nucleo IS NOT NULL));


--
-- Name: idx_tramite_ran_orv; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_ran_orv ON public.tramite_ran USING btree (id_orv, creado_en DESC, id_tramite_ran DESC) WHERE (activo AND (id_orv IS NOT NULL));


--
-- Name: idx_tramite_ran_pn; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tramite_ran_pn ON public.tramite_ran USING btree (id_proyecto_nucleo) WHERE activo;


--
-- Name: idx_trazabilidad_fuente; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trazabilidad_fuente ON public.trazabilidad_fuente USING btree (archivo, hoja, fila);


--
-- Name: idx_trazabilidad_objetivo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trazabilidad_objetivo ON public.trazabilidad_fuente USING btree (entidad_tipo, entidad_id);


--
-- Name: idx_trazo_proyecto_geom; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_trazo_proyecto_geom ON public.trazo_proyecto USING gist (geometria_linea);


--
-- Name: idx_unidad_agraria_clasificacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_unidad_agraria_clasificacion ON public.unidad_agraria USING btree (id_tipo_tierra, id_tipo_gestion, id_destino_superficie) WHERE activo;


--
-- Name: idx_unidad_agraria_nucleo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_unidad_agraria_nucleo ON public.unidad_agraria USING btree (id_nucleo) WHERE activo;


--
-- Name: idx_unidad_agraria_parcela; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_unidad_agraria_parcela ON public.unidad_agraria USING btree (id_parcela) WHERE (activo AND (id_parcela IS NOT NULL));


--
-- Name: idx_unidad_agraria_referencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_unidad_agraria_referencia ON public.unidad_agraria USING btree (id_nucleo, referencia_normalizada) WHERE (activo AND (referencia_normalizada IS NOT NULL));


--
-- Name: idx_usuario_proyecto_proyecto; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuario_proyecto_proyecto ON public.usuario_proyecto USING btree (id_proyecto) WHERE activo;


--
-- Name: uq_usuario_correo_normalizado; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_usuario_correo_normalizado ON public.usuario USING btree (lower(btrim((correo)::text)));


--
-- Name: uq_actividad_hecho; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_actividad_hecho ON public.actividad_campo USING btree (id_proyecto_nucleo, COALESCE(id_afectacion, 0), tipo_actividad, contexto_actividad, COALESCE(fecha_programada, 'infinity'::date), COALESCE(fecha_realizada, 'infinity'::date), COALESCE(btrim((responsable)::text), ''::text), md5(COALESCE(resultado, ''::text))) WHERE activo;


--
-- Name: uq_compareciente_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_compareciente_activo ON public.convenio_compareciente USING btree (id_convenio, id_persona, COALESCE(id_parcela_titular, 0), id_tipo_calidad) WHERE activo;


--
-- Name: uq_expediente_requisito_objetivo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_expediente_requisito_objetivo ON public.expediente_requisito USING btree (id_proyecto_nucleo, id_requisito, entidad_tipo, entidad_id) WHERE activo;


--
-- Name: uq_parcela_numero_normalizado; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_parcela_numero_normalizado ON public.parcela USING btree (id_nucleo, lower(regexp_replace(btrim((no_parcela)::text), '\\s+'::text, ' '::text, 'g'::text))) WHERE (activo AND (no_parcela IS NOT NULL));


--
-- Name: uq_afectacion_unidad_activa; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_afectacion_unidad_activa ON public.afectacion_unidad_agraria USING btree (id_afectacion, id_unidad_agraria) WHERE activo;


--
-- Name: uq_alias_territorial_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_alias_territorial_activo ON public.catalogo_alias_territorial USING btree (id_entidad, alias_normalizado, COALESCE(alias_clave, ''::character varying)) WHERE activo;


--
-- Name: uq_convenio_afectacion_activa; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_convenio_afectacion_activa ON public.convenio_afectacion USING btree (id_convenio, id_afectacion) WHERE activo;


--
-- Name: uq_convenio_afectacion_principal; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_convenio_afectacion_principal ON public.convenio_afectacion USING btree (id_convenio) WHERE (activo AND ((rol)::text = 'principal'::text));


--
-- Name: uq_convenio_padre_consecutivo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_convenio_padre_consecutivo ON public.convenio USING btree (id_convenio_padre, consecutivo) WHERE (activo AND (id_convenio_padre IS NOT NULL));


--
-- Name: uq_convocatoria_ordinal; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_convocatoria_ordinal ON public.asamblea_convocatoria USING btree (id_asamblea, ordinal) WHERE activo;


--
-- Name: uq_documento_vinculo_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_documento_vinculo_activo ON public.documento_vinculo USING btree (id_documento, entidad_tipo, entidad_id) WHERE activo;


--
-- Name: uq_evento_fifonafe_ordinal; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_evento_fifonafe_ordinal ON public.tramite_fifonafe_evento USING btree (id_tramite_fifonafe, ordinal) WHERE activo;


--
-- Name: uq_evento_ran_ordinal; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_evento_ran_ordinal ON public.tramite_ran_evento USING btree (id_tramite_ran, ordinal) WHERE activo;


--
-- Name: uq_fifonafe_afectacion_activa; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_fifonafe_afectacion_activa ON public.tramite_fifonafe_afectacion USING btree (id_tramite_fifonafe, id_afectacion) WHERE activo;


--
-- Name: uq_importacion_idempotente; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_importacion_idempotente ON public.importacion_archivo USING btree (id_proyecto, tipo_objetivo, sha256) WHERE activo;


--
-- Name: uq_indemnizacion_afectacion_activa; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_indemnizacion_afectacion_activa ON public.indemnizacion USING btree (id_afectacion) WHERE activo;


--
-- Name: uq_orv_nucleo_inicio; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_orv_nucleo_inicio ON public.orv USING btree (id_nucleo, inicio_vigencia) WHERE (activo AND (inicio_vigencia IS NOT NULL));


--
-- Name: uq_padron_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_padron_fecha ON public.padron_historial USING btree (id_nucleo, fecha_padron) WHERE (activo AND (fecha_padron IS NOT NULL));


--
-- Name: uq_pago_referencia; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_pago_referencia ON public.pago USING btree (id_indemnizacion, referencia) WHERE (activo AND (referencia IS NOT NULL));


--
-- Name: uq_parcela_titular_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_parcela_titular_activo ON public.parcela_titular USING btree (id_parcela, id_persona, tipo_derecho) WHERE activo;


--
-- Name: uq_perfil_nombre_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_perfil_nombre_activo ON public.perfil_mapeo_importacion USING btree (COALESCE(id_proyecto, 0), lower((nombre)::text)) WHERE activo;


--
-- Name: uq_persona_curp; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_persona_curp ON public.persona USING btree (upper((curp)::text)) WHERE (activo AND (curp IS NOT NULL));


--
-- Name: uq_pn_referencia_activa; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_pn_referencia_activa ON public.proyecto_nucleo_referencia USING btree (id_proyecto_nucleo, tipo_referencia, valor) WHERE activo;


--
-- Name: uq_pn_referencia_principal; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_pn_referencia_principal ON public.proyecto_nucleo_referencia USING btree (id_proyecto_nucleo, tipo_referencia) WHERE (activo AND es_principal);


--
-- Name: uq_proyecto_nucleo_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_proyecto_nucleo_activo ON public.proyecto_nucleo USING btree (id_proyecto, id_nucleo) WHERE activo;


--
-- Name: uq_responsable_principal; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_responsable_principal ON public.proyecto_nucleo_responsable USING btree (id_proyecto_nucleo) WHERE (activo AND es_principal);


--
-- Name: uq_trazo_proyecto_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_trazo_proyecto_activo ON public.trazo_proyecto USING btree (id_proyecto) WHERE activo;


--
-- Name: uq_unidad_titular_parcela_titular; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_unidad_titular_parcela_titular ON public.unidad_agraria_titular USING btree (id_unidad_agraria, id_parcela_titular) WHERE (activo AND (id_parcela_titular IS NOT NULL));


--
-- Name: uq_unidad_titular_persona; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_unidad_titular_persona ON public.unidad_agraria_titular USING btree (id_unidad_agraria, id_persona) WHERE (activo AND (id_persona IS NOT NULL));


--
-- Name: uq_usuario_proyecto_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_usuario_proyecto_activo ON public.usuario_proyecto USING btree (id_usuario, id_proyecto) WHERE activo;


--
-- Name: tramite_fifonafe_evento ctr_fifonafe_completo_evento; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER ctr_fifonafe_completo_evento AFTER INSERT OR UPDATE ON public.tramite_fifonafe_evento DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.fn_validar_fifonafe_completo();


--
-- Name: tramite_fifonafe ctr_fifonafe_completo_parent; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER ctr_fifonafe_completo_parent AFTER INSERT OR UPDATE ON public.tramite_fifonafe DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.fn_validar_fifonafe_completo();


--
-- Name: convenio ctr_convenio_requiere_afectacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER ctr_convenio_requiere_afectacion AFTER INSERT OR UPDATE OF activo ON public.convenio DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.fn_convenio_requiere_afectacion();


--
-- Name: convenio_afectacion ctr_convenio_vinculo_requerido; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER ctr_convenio_vinculo_requerido AFTER INSERT OR UPDATE OF activo, id_convenio ON public.convenio_afectacion DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.fn_convenio_requiere_afectacion();


--
-- Name: tramite_fifonafe ctr_fifonafe_requiere_afectacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER ctr_fifonafe_requiere_afectacion AFTER INSERT OR UPDATE OF activo ON public.tramite_fifonafe DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.fn_fifonafe_requiere_afectacion();


--
-- Name: tramite_fifonafe_afectacion ctr_fifonafe_vinculo_requerido; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER ctr_fifonafe_vinculo_requerido AFTER INSERT OR UPDATE OF activo, id_tramite_fifonafe ON public.tramite_fifonafe_afectacion DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.fn_fifonafe_requiere_afectacion();


--
-- Name: sesion_usuario trg_auth_audit_sesion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_audit_sesion AFTER INSERT OR UPDATE ON public.sesion_usuario FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_sesion');


--
-- Name: evento_acceso trg_auth_evento_inmutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_evento_inmutable BEFORE DELETE OR UPDATE ON public.evento_acceso FOR EACH ROW EXECUTE FUNCTION public.fn_auth_prevent_event_change();


--
-- Name: usuario trg_auth_inicializar_estado_usuario; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_inicializar_estado_usuario AFTER INSERT ON public.usuario FOR EACH ROW EXECUTE FUNCTION public.fn_auth_inicializar_estado_usuario();


--
-- Name: estado_autenticacion_usuario trg_auth_prevent_delete_estado; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_prevent_delete_estado BEFORE DELETE ON public.estado_autenticacion_usuario FOR EACH ROW EXECUTE FUNCTION public.fn_auth_prevent_physical_delete();


--
-- Name: sesion_usuario trg_auth_prevent_delete_sesion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_prevent_delete_sesion BEFORE DELETE ON public.sesion_usuario FOR EACH ROW EXECUTE FUNCTION public.fn_auth_prevent_physical_delete();


--
-- Name: usuario trg_auth_revocar_sesiones_usuario_inactivo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_revocar_sesiones_usuario_inactivo AFTER UPDATE OF activo ON public.usuario FOR EACH ROW EXECUTE FUNCTION public.fn_auth_revocar_sesiones_usuario_inactivo();


--
-- Name: estado_autenticacion_usuario trg_auth_validar_estado_evento; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_validar_estado_evento BEFORE UPDATE ON public.estado_autenticacion_usuario FOR EACH ROW EXECUTE FUNCTION public.fn_auth_validar_estado_evento();


--
-- Name: usuario trg_ultimo_admin; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_ultimo_admin BEFORE UPDATE OF activo, rol ON public.usuario FOR EACH ROW EXECUTE FUNCTION public.fn_validar_administrador_activo();


--
-- Name: catalogo_operativo_alias trg_catalogo_alias_no_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_catalogo_alias_no_delete BEFORE DELETE ON public.catalogo_operativo_alias FOR EACH ROW EXECUTE FUNCTION public.fn_catalogo_alias_no_delete();


--
-- Name: catalogo_operativo trg_catalogo_inmutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_catalogo_inmutable BEFORE DELETE OR UPDATE ON public.catalogo_operativo FOR EACH ROW EXECUTE FUNCTION public.fn_catalogo_inmutable();


--
-- Name: asamblea_convocatoria trg_convocatoria_catalogo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_convocatoria_catalogo BEFORE INSERT OR UPDATE OF id_resultado ON public.asamblea_convocatoria FOR EACH ROW EXECUTE FUNCTION public.fn_validar_catalogos_dominio();


--
-- Name: tramite_fifonafe_evento trg_evento_fifonafe_catalogo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_evento_fifonafe_catalogo BEFORE INSERT OR UPDATE OF id_tipo_evento ON public.tramite_fifonafe_evento FOR EACH ROW EXECUTE FUNCTION public.fn_validar_catalogos_dominio();


--
-- Name: tramite_ran_evento trg_evento_ran_catalogo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_evento_ran_catalogo BEFORE INSERT OR UPDATE OF id_tipo_evento ON public.tramite_ran_evento FOR EACH ROW EXECUTE FUNCTION public.fn_validar_catalogos_dominio();


--
-- Name: importacion_tabular_celda trg_importacion_celda_objetivo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_importacion_celda_objetivo BEFORE INSERT OR UPDATE OF entidad_tipo, entidad_id ON public.importacion_tabular_celda FOR EACH ROW EXECUTE FUNCTION public.fn_validar_importacion_celda();


--
-- Name: orv_integrante trg_integrante_catalogo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_integrante_catalogo BEFORE INSERT OR UPDATE OF id_organo, id_cargo, id_calidad ON public.orv_integrante FOR EACH ROW EXECUTE FUNCTION public.fn_validar_catalogos_dominio();


--
-- Name: expediente_requisito trg_requisito_estado; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_requisito_estado BEFORE INSERT OR UPDATE OF id_estado ON public.expediente_requisito FOR EACH ROW EXECUTE FUNCTION public.fn_validar_catalogos_dominio();


--
-- Name: requisito_documental trg_requisito_no_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_requisito_no_delete BEFORE DELETE ON public.requisito_documental FOR EACH ROW EXECUTE FUNCTION public.fn_catalogo_alias_no_delete();


--
-- Name: afectacion trg_afectacion_tipo_cop; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_afectacion_tipo_cop BEFORE INSERT OR UPDATE OF id_tipo_cop_operativo ON public.afectacion FOR EACH ROW EXECUTE FUNCTION public.fn_validar_afectacion_tipo_cop();


--
-- Name: afectacion_unidad_agraria trg_afectacion_unidad_no_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_afectacion_unidad_no_delete BEFORE DELETE ON public.afectacion_unidad_agraria FOR EACH ROW EXECUTE FUNCTION public.fn_prevenir_delete_fisico();


--
-- Name: afectacion_unidad_agraria trg_afectacion_unidad_validar; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_afectacion_unidad_validar BEFORE INSERT OR UPDATE OF id_afectacion, id_unidad_agraria, activo ON public.afectacion_unidad_agraria FOR EACH ROW EXECUTE FUNCTION public.fn_validar_afectacion_unidad();


--
-- Name: proyecto_nucleo trg_pn_tuc; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_pn_tuc BEFORE INSERT OR UPDATE OF afecta_tuc, id_motivo_no_afecta_tuc, motivo_no_afecta_tuc_detalle ON public.proyecto_nucleo FOR EACH ROW EXECUTE FUNCTION public.fn_validar_pn_tuc();


--
-- Name: unidad_agraria trg_unidad_agraria_validar; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_unidad_agraria_validar BEFORE INSERT OR UPDATE OF id_nucleo, id_tipo_tierra, id_tipo_gestion, id_destino_superficie, id_tipo_titularidad, id_parcela, referencia_alfanumerica, activo ON public.unidad_agraria FOR EACH ROW EXECUTE FUNCTION public.fn_validar_unidad_agraria();


--
-- Name: unidad_agraria trg_unidad_no_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_unidad_no_delete BEFORE DELETE ON public.unidad_agraria FOR EACH ROW EXECUTE FUNCTION public.fn_prevenir_delete_fisico();


--
-- Name: unidad_agraria_titular trg_unidad_titular_no_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_unidad_titular_no_delete BEFORE DELETE ON public.unidad_agraria_titular FOR EACH ROW EXECUTE FUNCTION public.fn_prevenir_delete_fisico();


--
-- Name: unidad_agraria_titular trg_unidad_titular_validar; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_unidad_titular_validar BEFORE INSERT OR UPDATE OF id_unidad_agraria, id_persona, id_parcela_titular, activo ON public.unidad_agraria_titular FOR EACH ROW EXECUTE FUNCTION public.fn_validar_unidad_titular();


--
-- Name: tramite_ran trg_tramite_ran_contexto; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tramite_ran_contexto BEFORE INSERT OR UPDATE OF id_proyecto_nucleo, id_nucleo, id_asamblea, id_convenio, id_orv, activo ON public.tramite_ran FOR EACH ROW EXECUTE FUNCTION public.fn_validar_tramite_ran_contexto();


--
-- Name: tramite_ran trg_tramite_ran_objetivo_inmutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_tramite_ran_objetivo_inmutable BEFORE UPDATE OF id_proyecto_nucleo, id_nucleo, id_asamblea, id_convenio, id_orv ON public.tramite_ran FOR EACH ROW EXECUTE FUNCTION public.fn_tramite_ran_objetivo_inmutable();


--
-- Name: actividad_campo trg_actividad_afectacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_actividad_afectacion BEFORE INSERT OR UPDATE OF id_proyecto_nucleo, id_afectacion, activo ON public.actividad_campo FOR EACH ROW EXECUTE FUNCTION public.fn_validar_actividad_afectacion();


--
-- Name: convenio_compareciente trg_compareciente_convenio_firmado; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER trg_compareciente_convenio_firmado AFTER INSERT OR UPDATE ON public.convenio_compareciente DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.fn_validar_convenio_individual_firmado();


--
-- Name: convenio_compareciente trg_compareciente_identidad_inmutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_compareciente_identidad_inmutable BEFORE UPDATE OF id_convenio, id_persona, id_parcela_titular ON public.convenio_compareciente FOR EACH ROW EXECUTE FUNCTION public.fn_compareciente_identidad_inmutable();


--
-- Name: convenio_compareciente trg_compareciente_no_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_compareciente_no_delete BEFORE DELETE ON public.convenio_compareciente FOR EACH ROW EXECUTE FUNCTION public.fn_prevenir_delete_fisico();


--
-- Name: convenio_compareciente trg_compareciente_unidad; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER trg_compareciente_unidad AFTER INSERT OR UPDATE ON public.convenio_compareciente DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.fn_validar_convenio_compareciente_unidad();


--
-- Name: convenio_afectacion trg_convenio_afectacion_firmado; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER trg_convenio_afectacion_firmado AFTER INSERT OR UPDATE ON public.convenio_afectacion DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.fn_validar_convenio_individual_firmado();


--
-- Name: convenio trg_convenio_individual_firmado; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER trg_convenio_individual_firmado AFTER INSERT OR UPDATE ON public.convenio DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.fn_validar_convenio_individual_firmado();


--
-- Name: convenio trg_linaje_convenio_individual; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_linaje_convenio_individual BEFORE INSERT OR UPDATE OF id_proyecto_nucleo, ambito, tipo_instrumento, tipo_convenio, id_convenio_padre, id_asamblea_autorizacion, activo ON public.convenio FOR EACH ROW EXECUTE FUNCTION public.fn_validar_linaje_convenio_individual();


--
-- Name: convenio trg_linaje_unidad_convenio; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER trg_linaje_unidad_convenio AFTER INSERT OR UPDATE ON public.convenio DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.fn_validar_linaje_unidad_individual();


--
-- Name: convenio_afectacion trg_linaje_unidad_vinculo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER trg_linaje_unidad_vinculo AFTER INSERT OR UPDATE ON public.convenio_afectacion DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.fn_validar_linaje_unidad_individual();


--
-- Name: convenio_compareciente trg_validar_compareciente; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_validar_compareciente BEFORE INSERT OR UPDATE OF id_convenio, id_persona, id_parcela_titular, id_tipo_calidad, id_tipo_acreditacion, referencia_acreditacion, fecha_acreditacion, es_firmante, requiere_revision, activo ON public.convenio_compareciente FOR EACH ROW EXECUTE FUNCTION public.fn_validar_compareciente();


--
-- Name: catalogo_alias_territorial trg_alias_territorial_objetivo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_alias_territorial_objetivo BEFORE INSERT OR UPDATE OF id_entidad, id_municipio_destino ON public.catalogo_alias_territorial FOR EACH ROW EXECUTE FUNCTION public.fn_validar_alias_territorial_objetivo();


--
-- Name: asamblea trg_asamblea_padron; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_asamblea_padron BEFORE INSERT OR UPDATE OF id_proyecto_nucleo, id_padron, activo ON public.asamblea FOR EACH ROW EXECUTE FUNCTION public.fn_validar_asamblea_padron();


--
-- Name: actividad_campo trg_audit_actividad_campo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_actividad_campo AFTER INSERT OR UPDATE ON public.actividad_campo FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_actividad');


--
-- Name: afectacion trg_audit_afectacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_afectacion AFTER INSERT OR UPDATE ON public.afectacion FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_afectacion');


--
-- Name: afectacion_unidad_agraria trg_audit_afectacion_unidad_agraria; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_afectacion_unidad_agraria AFTER INSERT OR UPDATE ON public.afectacion_unidad_agraria FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_afectacion_unidad');


--
-- Name: asamblea trg_audit_asamblea; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_asamblea AFTER INSERT OR UPDATE ON public.asamblea FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_asamblea');


--
-- Name: asamblea_convocatoria trg_audit_asamblea_convocatoria; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_asamblea_convocatoria AFTER INSERT OR UPDATE ON public.asamblea_convocatoria FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_convocatoria');


--
-- Name: catalogo_alias_territorial trg_audit_catalogo_alias_territorial; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_catalogo_alias_territorial AFTER INSERT OR UPDATE ON public.catalogo_alias_territorial FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_alias');


--
-- Name: catalogo_operativo trg_audit_catalogo_operativo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_catalogo_operativo AFTER INSERT OR UPDATE ON public.catalogo_operativo FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_catalogo_opcion');


--
-- Name: catalogo_operativo_alias trg_audit_catalogo_operativo_alias; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_catalogo_operativo_alias AFTER INSERT OR UPDATE ON public.catalogo_operativo_alias FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_catalogo_alias');


--
-- Name: convenio trg_audit_convenio; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_convenio AFTER INSERT OR UPDATE ON public.convenio FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_convenio');


--
-- Name: convenio_afectacion trg_audit_convenio_afectacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_convenio_afectacion AFTER INSERT OR UPDATE ON public.convenio_afectacion FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_convenio_afectacion');


--
-- Name: convenio_compareciente trg_audit_convenio_compareciente; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_convenio_compareciente AFTER INSERT OR UPDATE ON public.convenio_compareciente FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_compareciente');


--
-- Name: documento trg_audit_documento; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_documento AFTER INSERT OR UPDATE ON public.documento FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_documento');


--
-- Name: documento_vinculo trg_audit_documento_vinculo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_documento_vinculo AFTER INSERT OR UPDATE ON public.documento_vinculo FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_documento_vinculo');


--
-- Name: expediente_requisito trg_audit_expediente_requisito; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_expediente_requisito AFTER INSERT OR UPDATE ON public.expediente_requisito FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_expediente_requisito');


--
-- Name: importacion_archivo trg_audit_importacion_archivo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_importacion_archivo AFTER INSERT OR UPDATE ON public.importacion_archivo FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_importacion');


--
-- Name: importacion_tabular trg_audit_importacion_tabular; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_importacion_tabular AFTER INSERT OR UPDATE ON public.importacion_tabular FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_importacion_tabular');


--
-- Name: indemnizacion trg_audit_indemnizacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_indemnizacion AFTER INSERT OR UPDATE ON public.indemnizacion FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_indemnizacion');


--
-- Name: nucleo_agrario trg_audit_nucleo_agrario; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_nucleo_agrario AFTER INSERT OR UPDATE ON public.nucleo_agrario FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_nucleo');


--
-- Name: orv trg_audit_orv; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_orv AFTER INSERT OR UPDATE ON public.orv FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_orv');


--
-- Name: orv_integrante trg_audit_orv_integrante; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_orv_integrante AFTER INSERT OR UPDATE ON public.orv_integrante FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_orv_integrante');


--
-- Name: padron_historial trg_audit_padron_historial; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_padron_historial AFTER INSERT OR UPDATE ON public.padron_historial FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_padron');


--
-- Name: pago trg_audit_pago; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_pago AFTER INSERT OR UPDATE ON public.pago FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_pago');


--
-- Name: parcela trg_audit_parcela; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_parcela AFTER INSERT OR UPDATE ON public.parcela FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_parcela');


--
-- Name: parcela_titular trg_audit_parcela_titular; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_parcela_titular AFTER INSERT OR UPDATE ON public.parcela_titular FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_parcela_titular');


--
-- Name: perfil_mapeo_importacion trg_audit_perfil_mapeo_importacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_perfil_mapeo_importacion AFTER INSERT OR UPDATE ON public.perfil_mapeo_importacion FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_perfil');


--
-- Name: persona trg_audit_persona; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_persona AFTER INSERT OR UPDATE ON public.persona FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_persona');


--
-- Name: proyecto trg_audit_proyecto; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_proyecto AFTER INSERT OR UPDATE ON public.proyecto FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_proyecto');


--
-- Name: proyecto_nucleo trg_audit_proyecto_nucleo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_proyecto_nucleo AFTER INSERT OR UPDATE ON public.proyecto_nucleo FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_proyecto_nucleo');


--
-- Name: proyecto_nucleo_referencia trg_audit_proyecto_nucleo_referencia; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_proyecto_nucleo_referencia AFTER INSERT OR UPDATE ON public.proyecto_nucleo_referencia FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_referencia');


--
-- Name: proyecto_nucleo_responsable trg_audit_proyecto_nucleo_responsable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_proyecto_nucleo_responsable AFTER INSERT OR UPDATE ON public.proyecto_nucleo_responsable FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_responsable');


--
-- Name: requisito_documental trg_audit_requisito_documental; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_requisito_documental AFTER INSERT OR UPDATE ON public.requisito_documental FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_requisito');


--
-- Name: tramite_fifonafe trg_audit_tramite_fifonafe; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_tramite_fifonafe AFTER INSERT OR UPDATE ON public.tramite_fifonafe FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_tramite_fifonafe');


--
-- Name: tramite_fifonafe_afectacion trg_audit_tramite_fifonafe_afectacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_tramite_fifonafe_afectacion AFTER INSERT OR UPDATE ON public.tramite_fifonafe_afectacion FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_tramite_fifonafe_afectacion');


--
-- Name: tramite_fifonafe_evento trg_audit_tramite_fifonafe_evento; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_tramite_fifonafe_evento AFTER INSERT OR UPDATE ON public.tramite_fifonafe_evento FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_evento_fifonafe');


--
-- Name: tramite_ran trg_audit_tramite_ran; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_tramite_ran AFTER INSERT OR UPDATE ON public.tramite_ran FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_tramite_ran');


--
-- Name: tramite_ran_evento trg_audit_tramite_ran_evento; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_tramite_ran_evento AFTER INSERT OR UPDATE ON public.tramite_ran_evento FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_evento_ran');


--
-- Name: trazo_proyecto trg_audit_trazo_proyecto; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_trazo_proyecto AFTER INSERT OR UPDATE ON public.trazo_proyecto FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_trazo');


--
-- Name: unidad_agraria trg_audit_unidad_agraria; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_unidad_agraria AFTER INSERT OR UPDATE ON public.unidad_agraria FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_unidad_agraria');


--
-- Name: unidad_agraria_titular trg_audit_unidad_agraria_titular; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_unidad_agraria_titular AFTER INSERT OR UPDATE ON public.unidad_agraria_titular FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_unidad_titular');


--
-- Name: usuario trg_audit_usuario; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_usuario AFTER INSERT OR UPDATE ON public.usuario FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_usuario');


--
-- Name: usuario_proyecto trg_audit_usuario_proyecto; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_usuario_proyecto AFTER INSERT OR UPDATE ON public.usuario_proyecto FOR EACH ROW EXECUTE FUNCTION public.fn_audit_log('id_usuario_proyecto');


--
-- Name: convenio_afectacion trg_convenio_afectacion_coherencia; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_convenio_afectacion_coherencia BEFORE INSERT OR UPDATE OF id_convenio, id_afectacion, activo ON public.convenio_afectacion FOR EACH ROW EXECUTE FUNCTION public.fn_validar_convenio_afectacion();


--
-- Name: convenio trg_convenio_relaciones; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_convenio_relaciones BEFORE INSERT OR UPDATE OF id_proyecto_nucleo, ambito, id_convenio_padre, id_asamblea_autorizacion ON public.convenio FOR EACH ROW EXECUTE FUNCTION public.fn_validar_convenio_relaciones();


--
-- Name: documento_version trg_documento_version_inmutable; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_documento_version_inmutable BEFORE DELETE OR UPDATE ON public.documento_version FOR EACH ROW EXECUTE FUNCTION public.fn_documento_version_inmutable();


--
-- Name: documento_vinculo trg_documento_vinculo_objetivo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_documento_vinculo_objetivo BEFORE INSERT OR UPDATE OF entidad_tipo, entidad_id, activo ON public.documento_vinculo FOR EACH ROW EXECUTE FUNCTION public.fn_validar_documento_vinculo();


--
-- Name: tramite_fifonafe_afectacion trg_fifonafe_afectacion_coherencia; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_fifonafe_afectacion_coherencia BEFORE INSERT OR UPDATE OF id_tramite_fifonafe, id_afectacion, activo ON public.tramite_fifonafe_afectacion FOR EACH ROW EXECUTE FUNCTION public.fn_validar_fifonafe_afectacion();


--
-- Name: importacion_feature trg_importacion_feature_objetivo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_importacion_feature_objetivo BEFORE INSERT OR UPDATE OF id_importacion, geometria_normalizada, registro_destino_id ON public.importacion_feature FOR EACH ROW EXECUTE FUNCTION public.fn_validar_importacion_feature_objetivo();


--
-- Name: trazabilidad_fuente trg_trazabilidad_objetivo; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_trazabilidad_objetivo BEFORE INSERT OR UPDATE OF entidad_tipo, entidad_id ON public.trazabilidad_fuente FOR EACH ROW EXECUTE FUNCTION public.fn_validar_trazabilidad_objetivo();


--
-- Name: actividad_campo actividad_campo_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividad_campo
    ADD CONSTRAINT actividad_campo_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: actividad_campo actividad_campo_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividad_campo
    ADD CONSTRAINT actividad_campo_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: actividad_campo actividad_campo_id_afectacion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividad_campo
    ADD CONSTRAINT actividad_campo_id_afectacion_fkey FOREIGN KEY (id_afectacion) REFERENCES public.afectacion(id_afectacion);


--
-- Name: actividad_campo actividad_campo_id_proyecto_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividad_campo
    ADD CONSTRAINT actividad_campo_id_proyecto_nucleo_fkey FOREIGN KEY (id_proyecto_nucleo) REFERENCES public.proyecto_nucleo(id_proyecto_nucleo);


--
-- Name: actividad_campo actividad_campo_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actividad_campo
    ADD CONSTRAINT actividad_campo_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: afectacion afectacion_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.afectacion
    ADD CONSTRAINT afectacion_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: afectacion afectacion_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.afectacion
    ADD CONSTRAINT afectacion_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: afectacion afectacion_id_proyecto_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.afectacion
    ADD CONSTRAINT afectacion_id_proyecto_nucleo_fkey FOREIGN KEY (id_proyecto_nucleo) REFERENCES public.proyecto_nucleo(id_proyecto_nucleo);


--
-- Name: afectacion afectacion_id_tipo_cop_operativo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.afectacion
    ADD CONSTRAINT afectacion_id_tipo_cop_operativo_fkey FOREIGN KEY (id_tipo_cop_operativo) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: afectacion afectacion_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.afectacion
    ADD CONSTRAINT afectacion_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: afectacion_unidad_agraria afectacion_unidad_agraria_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.afectacion_unidad_agraria
    ADD CONSTRAINT afectacion_unidad_agraria_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: afectacion_unidad_agraria afectacion_unidad_agraria_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.afectacion_unidad_agraria
    ADD CONSTRAINT afectacion_unidad_agraria_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: afectacion_unidad_agraria afectacion_unidad_agraria_id_afectacion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.afectacion_unidad_agraria
    ADD CONSTRAINT afectacion_unidad_agraria_id_afectacion_fkey FOREIGN KEY (id_afectacion) REFERENCES public.afectacion(id_afectacion);


--
-- Name: afectacion_unidad_agraria afectacion_unidad_agraria_id_unidad_agraria_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.afectacion_unidad_agraria
    ADD CONSTRAINT afectacion_unidad_agraria_id_unidad_agraria_fkey FOREIGN KEY (id_unidad_agraria) REFERENCES public.unidad_agraria(id_unidad_agraria);


--
-- Name: afectacion_unidad_agraria afectacion_unidad_agraria_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.afectacion_unidad_agraria
    ADD CONSTRAINT afectacion_unidad_agraria_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: asamblea asamblea_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea
    ADD CONSTRAINT asamblea_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: asamblea_convocatoria asamblea_convocatoria_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea_convocatoria
    ADD CONSTRAINT asamblea_convocatoria_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: asamblea_convocatoria asamblea_convocatoria_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea_convocatoria
    ADD CONSTRAINT asamblea_convocatoria_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: asamblea_convocatoria asamblea_convocatoria_id_asamblea_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea_convocatoria
    ADD CONSTRAINT asamblea_convocatoria_id_asamblea_fkey FOREIGN KEY (id_asamblea) REFERENCES public.asamblea(id_asamblea);


--
-- Name: asamblea_convocatoria asamblea_convocatoria_id_documento_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea_convocatoria
    ADD CONSTRAINT asamblea_convocatoria_id_documento_fkey FOREIGN KEY (id_documento) REFERENCES public.documento(id_documento);


--
-- Name: asamblea_convocatoria asamblea_convocatoria_id_resultado_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea_convocatoria
    ADD CONSTRAINT asamblea_convocatoria_id_resultado_fkey FOREIGN KEY (id_resultado) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: asamblea_convocatoria asamblea_convocatoria_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea_convocatoria
    ADD CONSTRAINT asamblea_convocatoria_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: asamblea asamblea_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea
    ADD CONSTRAINT asamblea_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: asamblea asamblea_id_contexto_asamblea_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea
    ADD CONSTRAINT asamblea_id_contexto_asamblea_fkey FOREIGN KEY (id_contexto_asamblea) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: asamblea asamblea_id_padron_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea
    ADD CONSTRAINT asamblea_id_padron_fkey FOREIGN KEY (id_padron) REFERENCES public.padron_historial(id_padron);


--
-- Name: asamblea asamblea_id_proyecto_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea
    ADD CONSTRAINT asamblea_id_proyecto_nucleo_fkey FOREIGN KEY (id_proyecto_nucleo) REFERENCES public.proyecto_nucleo(id_proyecto_nucleo);


--
-- Name: asamblea asamblea_id_tipo_asamblea_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea
    ADD CONSTRAINT asamblea_id_tipo_asamblea_fkey FOREIGN KEY (id_tipo_asamblea) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: asamblea asamblea_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asamblea
    ADD CONSTRAINT asamblea_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: bitacora bitacora_id_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bitacora
    ADD CONSTRAINT bitacora_id_nucleo_fkey FOREIGN KEY (id_nucleo) REFERENCES public.nucleo_agrario(id_nucleo);


--
-- Name: bitacora bitacora_id_proyecto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bitacora
    ADD CONSTRAINT bitacora_id_proyecto_fkey FOREIGN KEY (id_proyecto) REFERENCES public.proyecto(id_proyecto);


--
-- Name: bitacora bitacora_id_proyecto_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bitacora
    ADD CONSTRAINT bitacora_id_proyecto_nucleo_fkey FOREIGN KEY (id_proyecto_nucleo) REFERENCES public.proyecto_nucleo(id_proyecto_nucleo);


--
-- Name: bitacora bitacora_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bitacora
    ADD CONSTRAINT bitacora_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario);


--
-- Name: catalogo_alias_territorial catalogo_alias_territorial_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_alias_territorial
    ADD CONSTRAINT catalogo_alias_territorial_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: catalogo_alias_territorial catalogo_alias_territorial_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_alias_territorial
    ADD CONSTRAINT catalogo_alias_territorial_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: catalogo_alias_territorial catalogo_alias_territorial_id_entidad_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_alias_territorial
    ADD CONSTRAINT catalogo_alias_territorial_id_entidad_fkey FOREIGN KEY (id_entidad) REFERENCES public.entidad_federativa(id_entidad);


--
-- Name: catalogo_alias_territorial catalogo_alias_territorial_id_municipio_destino_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_alias_territorial
    ADD CONSTRAINT catalogo_alias_territorial_id_municipio_destino_fkey FOREIGN KEY (id_municipio_destino) REFERENCES public.municipio(id_municipio);


--
-- Name: catalogo_alias_territorial catalogo_alias_territorial_id_usuario_aprobador_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_alias_territorial
    ADD CONSTRAINT catalogo_alias_territorial_id_usuario_aprobador_fkey FOREIGN KEY (id_usuario_aprobador) REFERENCES public.usuario(id_usuario);


--
-- Name: catalogo_alias_territorial catalogo_alias_territorial_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_alias_territorial
    ADD CONSTRAINT catalogo_alias_territorial_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: catalogo_operativo catalogo_operativo_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_operativo
    ADD CONSTRAINT catalogo_operativo_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: catalogo_operativo_alias catalogo_operativo_alias_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_operativo_alias
    ADD CONSTRAINT catalogo_operativo_alias_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: catalogo_operativo_alias catalogo_operativo_alias_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_operativo_alias
    ADD CONSTRAINT catalogo_operativo_alias_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: catalogo_operativo_alias catalogo_operativo_alias_id_catalogo_opcion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_operativo_alias
    ADD CONSTRAINT catalogo_operativo_alias_id_catalogo_opcion_fkey FOREIGN KEY (id_catalogo_opcion) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: catalogo_operativo_alias catalogo_operativo_alias_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_operativo_alias
    ADD CONSTRAINT catalogo_operativo_alias_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: catalogo_operativo catalogo_operativo_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_operativo
    ADD CONSTRAINT catalogo_operativo_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: catalogo_operativo catalogo_operativo_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_operativo
    ADD CONSTRAINT catalogo_operativo_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: convenio convenio_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio
    ADD CONSTRAINT convenio_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: convenio_afectacion convenio_afectacion_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_afectacion
    ADD CONSTRAINT convenio_afectacion_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: convenio_afectacion convenio_afectacion_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_afectacion
    ADD CONSTRAINT convenio_afectacion_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: convenio_afectacion convenio_afectacion_id_afectacion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_afectacion
    ADD CONSTRAINT convenio_afectacion_id_afectacion_fkey FOREIGN KEY (id_afectacion) REFERENCES public.afectacion(id_afectacion);


--
-- Name: convenio_afectacion convenio_afectacion_id_convenio_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_afectacion
    ADD CONSTRAINT convenio_afectacion_id_convenio_fkey FOREIGN KEY (id_convenio) REFERENCES public.convenio(id_convenio);


--
-- Name: convenio_afectacion convenio_afectacion_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_afectacion
    ADD CONSTRAINT convenio_afectacion_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: convenio_compareciente convenio_compareciente_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_compareciente
    ADD CONSTRAINT convenio_compareciente_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: convenio_compareciente convenio_compareciente_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_compareciente
    ADD CONSTRAINT convenio_compareciente_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: convenio_compareciente convenio_compareciente_id_convenio_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_compareciente
    ADD CONSTRAINT convenio_compareciente_id_convenio_fkey FOREIGN KEY (id_convenio) REFERENCES public.convenio(id_convenio);


--
-- Name: convenio_compareciente convenio_compareciente_id_parcela_titular_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_compareciente
    ADD CONSTRAINT convenio_compareciente_id_parcela_titular_fkey FOREIGN KEY (id_parcela_titular) REFERENCES public.parcela_titular(id_parcela_titular);


--
-- Name: convenio_compareciente convenio_compareciente_id_persona_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_compareciente
    ADD CONSTRAINT convenio_compareciente_id_persona_fkey FOREIGN KEY (id_persona) REFERENCES public.persona(id_persona);


--
-- Name: convenio_compareciente convenio_compareciente_id_tipo_acreditacion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_compareciente
    ADD CONSTRAINT convenio_compareciente_id_tipo_acreditacion_fkey FOREIGN KEY (id_tipo_acreditacion) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: convenio_compareciente convenio_compareciente_id_tipo_calidad_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_compareciente
    ADD CONSTRAINT convenio_compareciente_id_tipo_calidad_fkey FOREIGN KEY (id_tipo_calidad) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: convenio_compareciente convenio_compareciente_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio_compareciente
    ADD CONSTRAINT convenio_compareciente_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: convenio convenio_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio
    ADD CONSTRAINT convenio_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: convenio convenio_id_asamblea_autorizacion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio
    ADD CONSTRAINT convenio_id_asamblea_autorizacion_fkey FOREIGN KEY (id_asamblea_autorizacion) REFERENCES public.asamblea(id_asamblea);


--
-- Name: convenio convenio_id_convenio_padre_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio
    ADD CONSTRAINT convenio_id_convenio_padre_fkey FOREIGN KEY (id_convenio_padre) REFERENCES public.convenio(id_convenio);


--
-- Name: convenio convenio_id_proyecto_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio
    ADD CONSTRAINT convenio_id_proyecto_nucleo_fkey FOREIGN KEY (id_proyecto_nucleo) REFERENCES public.proyecto_nucleo(id_proyecto_nucleo);


--
-- Name: convenio convenio_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.convenio
    ADD CONSTRAINT convenio_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: documento documento_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento
    ADD CONSTRAINT documento_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: documento documento_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento
    ADD CONSTRAINT documento_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: documento documento_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento
    ADD CONSTRAINT documento_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: documento_version documento_version_id_documento_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_version
    ADD CONSTRAINT documento_version_id_documento_fkey FOREIGN KEY (id_documento) REFERENCES public.documento(id_documento);


--
-- Name: documento_version documento_version_id_usuario_carga_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_version
    ADD CONSTRAINT documento_version_id_usuario_carga_fkey FOREIGN KEY (id_usuario_carga) REFERENCES public.usuario(id_usuario);


--
-- Name: documento_vinculo documento_vinculo_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_vinculo
    ADD CONSTRAINT documento_vinculo_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: documento_vinculo documento_vinculo_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_vinculo
    ADD CONSTRAINT documento_vinculo_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: documento_vinculo documento_vinculo_id_documento_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_vinculo
    ADD CONSTRAINT documento_vinculo_id_documento_fkey FOREIGN KEY (id_documento) REFERENCES public.documento(id_documento);


--
-- Name: documento_vinculo documento_vinculo_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_vinculo
    ADD CONSTRAINT documento_vinculo_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: estado_autenticacion_usuario estado_autenticacion_usuario_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.estado_autenticacion_usuario
    ADD CONSTRAINT estado_autenticacion_usuario_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: evento_acceso evento_acceso_id_usuario_actor_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_acceso
    ADD CONSTRAINT evento_acceso_id_usuario_actor_fkey FOREIGN KEY (id_usuario_actor) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: evento_acceso evento_acceso_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_acceso
    ADD CONSTRAINT evento_acceso_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: expediente_requisito expediente_requisito_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_requisito
    ADD CONSTRAINT expediente_requisito_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: expediente_requisito expediente_requisito_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_requisito
    ADD CONSTRAINT expediente_requisito_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: expediente_requisito expediente_requisito_id_documento_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_requisito
    ADD CONSTRAINT expediente_requisito_id_documento_fkey FOREIGN KEY (id_documento) REFERENCES public.documento(id_documento);


--
-- Name: expediente_requisito expediente_requisito_id_estado_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_requisito
    ADD CONSTRAINT expediente_requisito_id_estado_fkey FOREIGN KEY (id_estado) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: expediente_requisito expediente_requisito_id_proyecto_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_requisito
    ADD CONSTRAINT expediente_requisito_id_proyecto_nucleo_fkey FOREIGN KEY (id_proyecto_nucleo) REFERENCES public.proyecto_nucleo(id_proyecto_nucleo);


--
-- Name: expediente_requisito expediente_requisito_id_requisito_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_requisito
    ADD CONSTRAINT expediente_requisito_id_requisito_fkey FOREIGN KEY (id_requisito) REFERENCES public.requisito_documental(id_requisito);


--
-- Name: expediente_requisito expediente_requisito_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.expediente_requisito
    ADD CONSTRAINT expediente_requisito_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: evento_acceso fk_auth_evento_sesion; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_acceso
    ADD CONSTRAINT fk_auth_evento_sesion FOREIGN KEY (id_sesion) REFERENCES public.sesion_usuario(id_sesion) ON DELETE RESTRICT;


--
-- Name: importacion_archivo importacion_archivo_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_archivo
    ADD CONSTRAINT importacion_archivo_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: importacion_archivo importacion_archivo_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_archivo
    ADD CONSTRAINT importacion_archivo_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: importacion_archivo importacion_archivo_id_perfil_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_archivo
    ADD CONSTRAINT importacion_archivo_id_perfil_fkey FOREIGN KEY (id_perfil) REFERENCES public.perfil_mapeo_importacion(id_perfil);


--
-- Name: importacion_archivo importacion_archivo_id_proyecto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_archivo
    ADD CONSTRAINT importacion_archivo_id_proyecto_fkey FOREIGN KEY (id_proyecto) REFERENCES public.proyecto(id_proyecto);


--
-- Name: importacion_archivo importacion_archivo_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_archivo
    ADD CONSTRAINT importacion_archivo_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: importacion_archivo importacion_archivo_id_usuario_carga_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_archivo
    ADD CONSTRAINT importacion_archivo_id_usuario_carga_fkey FOREIGN KEY (id_usuario_carga) REFERENCES public.usuario(id_usuario);


--
-- Name: importacion_archivo importacion_archivo_id_usuario_confirmacion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_archivo
    ADD CONSTRAINT importacion_archivo_id_usuario_confirmacion_fkey FOREIGN KEY (id_usuario_confirmacion) REFERENCES public.usuario(id_usuario);


--
-- Name: importacion_feature importacion_feature_id_importacion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_feature
    ADD CONSTRAINT importacion_feature_id_importacion_fkey FOREIGN KEY (id_importacion) REFERENCES public.importacion_archivo(id_importacion);


--
-- Name: importacion_feature importacion_feature_id_usuario_revision_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_feature
    ADD CONSTRAINT importacion_feature_id_usuario_revision_fkey FOREIGN KEY (id_usuario_revision) REFERENCES public.usuario(id_usuario);


--
-- Name: importacion_tabular importacion_tabular_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_tabular
    ADD CONSTRAINT importacion_tabular_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: importacion_tabular_celda importacion_tabular_celda_id_importacion_tabular_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_tabular_celda
    ADD CONSTRAINT importacion_tabular_celda_id_importacion_tabular_fkey FOREIGN KEY (id_importacion_tabular) REFERENCES public.importacion_tabular(id_importacion_tabular);


--
-- Name: importacion_tabular_celda importacion_tabular_celda_id_usuario_registro_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_tabular_celda
    ADD CONSTRAINT importacion_tabular_celda_id_usuario_registro_fkey FOREIGN KEY (id_usuario_registro) REFERENCES public.usuario(id_usuario);


--
-- Name: importacion_tabular importacion_tabular_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_tabular
    ADD CONSTRAINT importacion_tabular_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: importacion_tabular importacion_tabular_id_proyecto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_tabular
    ADD CONSTRAINT importacion_tabular_id_proyecto_fkey FOREIGN KEY (id_proyecto) REFERENCES public.proyecto(id_proyecto);


--
-- Name: importacion_tabular importacion_tabular_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.importacion_tabular
    ADD CONSTRAINT importacion_tabular_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: indemnizacion indemnizacion_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.indemnizacion
    ADD CONSTRAINT indemnizacion_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: indemnizacion indemnizacion_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.indemnizacion
    ADD CONSTRAINT indemnizacion_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: indemnizacion indemnizacion_id_afectacion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.indemnizacion
    ADD CONSTRAINT indemnizacion_id_afectacion_fkey FOREIGN KEY (id_afectacion) REFERENCES public.afectacion(id_afectacion);


--
-- Name: indemnizacion indemnizacion_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.indemnizacion
    ADD CONSTRAINT indemnizacion_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: municipio municipio_id_entidad_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipio
    ADD CONSTRAINT municipio_id_entidad_fkey FOREIGN KEY (id_entidad) REFERENCES public.entidad_federativa(id_entidad);


--
-- Name: nucleo_agrario nucleo_agrario_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nucleo_agrario
    ADD CONSTRAINT nucleo_agrario_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: nucleo_agrario nucleo_agrario_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nucleo_agrario
    ADD CONSTRAINT nucleo_agrario_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: nucleo_agrario nucleo_agrario_id_municipio_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nucleo_agrario
    ADD CONSTRAINT nucleo_agrario_id_municipio_fkey FOREIGN KEY (id_municipio) REFERENCES public.municipio(id_municipio);


--
-- Name: nucleo_agrario nucleo_agrario_id_tipo_tenencia_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nucleo_agrario
    ADD CONSTRAINT nucleo_agrario_id_tipo_tenencia_fkey FOREIGN KEY (id_tipo_tenencia) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: nucleo_agrario nucleo_agrario_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nucleo_agrario
    ADD CONSTRAINT nucleo_agrario_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: orv orv_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv
    ADD CONSTRAINT orv_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: orv orv_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv
    ADD CONSTRAINT orv_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: orv orv_id_estado_registral_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv
    ADD CONSTRAINT orv_id_estado_registral_fkey FOREIGN KEY (id_estado_registral) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: orv orv_id_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv
    ADD CONSTRAINT orv_id_nucleo_fkey FOREIGN KEY (id_nucleo) REFERENCES public.nucleo_agrario(id_nucleo);


--
-- Name: orv orv_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv
    ADD CONSTRAINT orv_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: orv_integrante orv_integrante_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv_integrante
    ADD CONSTRAINT orv_integrante_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: orv_integrante orv_integrante_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv_integrante
    ADD CONSTRAINT orv_integrante_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: orv_integrante orv_integrante_id_calidad_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv_integrante
    ADD CONSTRAINT orv_integrante_id_calidad_fkey FOREIGN KEY (id_calidad) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: orv_integrante orv_integrante_id_cargo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv_integrante
    ADD CONSTRAINT orv_integrante_id_cargo_fkey FOREIGN KEY (id_cargo) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: orv_integrante orv_integrante_id_organo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv_integrante
    ADD CONSTRAINT orv_integrante_id_organo_fkey FOREIGN KEY (id_organo) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: orv_integrante orv_integrante_id_orv_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv_integrante
    ADD CONSTRAINT orv_integrante_id_orv_fkey FOREIGN KEY (id_orv) REFERENCES public.orv(id_orv);


--
-- Name: orv_integrante orv_integrante_id_persona_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv_integrante
    ADD CONSTRAINT orv_integrante_id_persona_fkey FOREIGN KEY (id_persona) REFERENCES public.persona(id_persona);


--
-- Name: orv_integrante orv_integrante_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orv_integrante
    ADD CONSTRAINT orv_integrante_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: padron_historial padron_historial_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.padron_historial
    ADD CONSTRAINT padron_historial_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: padron_historial padron_historial_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.padron_historial
    ADD CONSTRAINT padron_historial_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: padron_historial padron_historial_id_documento_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.padron_historial
    ADD CONSTRAINT padron_historial_id_documento_fkey FOREIGN KEY (id_documento) REFERENCES public.documento(id_documento);


--
-- Name: padron_historial padron_historial_id_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.padron_historial
    ADD CONSTRAINT padron_historial_id_nucleo_fkey FOREIGN KEY (id_nucleo) REFERENCES public.nucleo_agrario(id_nucleo);


--
-- Name: padron_historial padron_historial_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.padron_historial
    ADD CONSTRAINT padron_historial_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: pago pago_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pago
    ADD CONSTRAINT pago_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: pago pago_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pago
    ADD CONSTRAINT pago_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: pago pago_id_indemnizacion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pago
    ADD CONSTRAINT pago_id_indemnizacion_fkey FOREIGN KEY (id_indemnizacion) REFERENCES public.indemnizacion(id_indemnizacion);


--
-- Name: pago pago_id_persona_beneficiaria_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pago
    ADD CONSTRAINT pago_id_persona_beneficiaria_fkey FOREIGN KEY (id_persona_beneficiaria) REFERENCES public.persona(id_persona);


--
-- Name: pago pago_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pago
    ADD CONSTRAINT pago_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: parcela parcela_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcela
    ADD CONSTRAINT parcela_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: parcela parcela_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcela
    ADD CONSTRAINT parcela_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: parcela parcela_id_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcela
    ADD CONSTRAINT parcela_id_nucleo_fkey FOREIGN KEY (id_nucleo) REFERENCES public.nucleo_agrario(id_nucleo);


--
-- Name: parcela parcela_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcela
    ADD CONSTRAINT parcela_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: parcela_titular parcela_titular_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcela_titular
    ADD CONSTRAINT parcela_titular_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: parcela_titular parcela_titular_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcela_titular
    ADD CONSTRAINT parcela_titular_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: parcela_titular parcela_titular_id_parcela_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcela_titular
    ADD CONSTRAINT parcela_titular_id_parcela_fkey FOREIGN KEY (id_parcela) REFERENCES public.parcela(id_parcela);


--
-- Name: parcela_titular parcela_titular_id_persona_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcela_titular
    ADD CONSTRAINT parcela_titular_id_persona_fkey FOREIGN KEY (id_persona) REFERENCES public.persona(id_persona);


--
-- Name: parcela_titular parcela_titular_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parcela_titular
    ADD CONSTRAINT parcela_titular_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: perfil_mapeo_importacion perfil_mapeo_importacion_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.perfil_mapeo_importacion
    ADD CONSTRAINT perfil_mapeo_importacion_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: perfil_mapeo_importacion perfil_mapeo_importacion_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.perfil_mapeo_importacion
    ADD CONSTRAINT perfil_mapeo_importacion_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: perfil_mapeo_importacion perfil_mapeo_importacion_id_proyecto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.perfil_mapeo_importacion
    ADD CONSTRAINT perfil_mapeo_importacion_id_proyecto_fkey FOREIGN KEY (id_proyecto) REFERENCES public.proyecto(id_proyecto);


--
-- Name: perfil_mapeo_importacion perfil_mapeo_importacion_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.perfil_mapeo_importacion
    ADD CONSTRAINT perfil_mapeo_importacion_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: perfil_mapeo_importacion perfil_mapeo_importacion_id_usuario_creacion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.perfil_mapeo_importacion
    ADD CONSTRAINT perfil_mapeo_importacion_id_usuario_creacion_fkey FOREIGN KEY (id_usuario_creacion) REFERENCES public.usuario(id_usuario);


--
-- Name: persona persona_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona
    ADD CONSTRAINT persona_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: persona persona_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona
    ADD CONSTRAINT persona_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: persona persona_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona
    ADD CONSTRAINT persona_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: proyecto proyecto_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto
    ADD CONSTRAINT proyecto_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: proyecto proyecto_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto
    ADD CONSTRAINT proyecto_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: proyecto proyecto_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto
    ADD CONSTRAINT proyecto_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: proyecto_nucleo proyecto_nucleo_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo
    ADD CONSTRAINT proyecto_nucleo_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: proyecto_nucleo proyecto_nucleo_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo
    ADD CONSTRAINT proyecto_nucleo_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: proyecto_nucleo proyecto_nucleo_id_motivo_no_afecta_tuc_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo
    ADD CONSTRAINT proyecto_nucleo_id_motivo_no_afecta_tuc_fkey FOREIGN KEY (id_motivo_no_afecta_tuc) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: proyecto_nucleo proyecto_nucleo_id_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo
    ADD CONSTRAINT proyecto_nucleo_id_nucleo_fkey FOREIGN KEY (id_nucleo) REFERENCES public.nucleo_agrario(id_nucleo);


--
-- Name: proyecto_nucleo proyecto_nucleo_id_proyecto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo
    ADD CONSTRAINT proyecto_nucleo_id_proyecto_fkey FOREIGN KEY (id_proyecto) REFERENCES public.proyecto(id_proyecto);


--
-- Name: proyecto_nucleo proyecto_nucleo_id_residencia_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo
    ADD CONSTRAINT proyecto_nucleo_id_residencia_fkey FOREIGN KEY (id_residencia) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: proyecto_nucleo proyecto_nucleo_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo
    ADD CONSTRAINT proyecto_nucleo_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: proyecto_nucleo_referencia proyecto_nucleo_referencia_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo_referencia
    ADD CONSTRAINT proyecto_nucleo_referencia_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: proyecto_nucleo_referencia proyecto_nucleo_referencia_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo_referencia
    ADD CONSTRAINT proyecto_nucleo_referencia_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: proyecto_nucleo_referencia proyecto_nucleo_referencia_id_proyecto_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo_referencia
    ADD CONSTRAINT proyecto_nucleo_referencia_id_proyecto_nucleo_fkey FOREIGN KEY (id_proyecto_nucleo) REFERENCES public.proyecto_nucleo(id_proyecto_nucleo);


--
-- Name: proyecto_nucleo_referencia proyecto_nucleo_referencia_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo_referencia
    ADD CONSTRAINT proyecto_nucleo_referencia_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: proyecto_nucleo_responsable proyecto_nucleo_responsable_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo_responsable
    ADD CONSTRAINT proyecto_nucleo_responsable_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: proyecto_nucleo_responsable proyecto_nucleo_responsable_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo_responsable
    ADD CONSTRAINT proyecto_nucleo_responsable_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: proyecto_nucleo_responsable proyecto_nucleo_responsable_id_proyecto_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo_responsable
    ADD CONSTRAINT proyecto_nucleo_responsable_id_proyecto_nucleo_fkey FOREIGN KEY (id_proyecto_nucleo) REFERENCES public.proyecto_nucleo(id_proyecto_nucleo);


--
-- Name: proyecto_nucleo_responsable proyecto_nucleo_responsable_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proyecto_nucleo_responsable
    ADD CONSTRAINT proyecto_nucleo_responsable_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: requisito_documental requisito_documental_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requisito_documental
    ADD CONSTRAINT requisito_documental_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: requisito_documental requisito_documental_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requisito_documental
    ADD CONSTRAINT requisito_documental_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: requisito_documental requisito_documental_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requisito_documental
    ADD CONSTRAINT requisito_documental_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: sesion_usuario sesion_usuario_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario
    ADD CONSTRAINT sesion_usuario_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: sesion_usuario sesion_usuario_id_usuario_revoca_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario
    ADD CONSTRAINT sesion_usuario_id_usuario_revoca_fkey FOREIGN KEY (id_usuario_revoca) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: tramite_fifonafe tramite_fifonafe_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe
    ADD CONSTRAINT tramite_fifonafe_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: tramite_fifonafe_afectacion tramite_fifonafe_afectacion_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe_afectacion
    ADD CONSTRAINT tramite_fifonafe_afectacion_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: tramite_fifonafe_afectacion tramite_fifonafe_afectacion_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe_afectacion
    ADD CONSTRAINT tramite_fifonafe_afectacion_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: tramite_fifonafe_afectacion tramite_fifonafe_afectacion_id_afectacion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe_afectacion
    ADD CONSTRAINT tramite_fifonafe_afectacion_id_afectacion_fkey FOREIGN KEY (id_afectacion) REFERENCES public.afectacion(id_afectacion);


--
-- Name: tramite_fifonafe_afectacion tramite_fifonafe_afectacion_id_tramite_fifonafe_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe_afectacion
    ADD CONSTRAINT tramite_fifonafe_afectacion_id_tramite_fifonafe_fkey FOREIGN KEY (id_tramite_fifonafe) REFERENCES public.tramite_fifonafe(id_tramite_fifonafe);


--
-- Name: tramite_fifonafe_afectacion tramite_fifonafe_afectacion_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe_afectacion
    ADD CONSTRAINT tramite_fifonafe_afectacion_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: tramite_fifonafe tramite_fifonafe_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe
    ADD CONSTRAINT tramite_fifonafe_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: tramite_fifonafe_evento tramite_fifonafe_evento_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe_evento
    ADD CONSTRAINT tramite_fifonafe_evento_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: tramite_fifonafe_evento tramite_fifonafe_evento_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe_evento
    ADD CONSTRAINT tramite_fifonafe_evento_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: tramite_fifonafe_evento tramite_fifonafe_evento_id_documento_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe_evento
    ADD CONSTRAINT tramite_fifonafe_evento_id_documento_fkey FOREIGN KEY (id_documento) REFERENCES public.documento(id_documento);


--
-- Name: tramite_fifonafe_evento tramite_fifonafe_evento_id_tipo_evento_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe_evento
    ADD CONSTRAINT tramite_fifonafe_evento_id_tipo_evento_fkey FOREIGN KEY (id_tipo_evento) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: tramite_fifonafe_evento tramite_fifonafe_evento_id_tramite_fifonafe_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe_evento
    ADD CONSTRAINT tramite_fifonafe_evento_id_tramite_fifonafe_fkey FOREIGN KEY (id_tramite_fifonafe) REFERENCES public.tramite_fifonafe(id_tramite_fifonafe);


--
-- Name: tramite_fifonafe_evento tramite_fifonafe_evento_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe_evento
    ADD CONSTRAINT tramite_fifonafe_evento_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: tramite_fifonafe tramite_fifonafe_id_proyecto_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe
    ADD CONSTRAINT tramite_fifonafe_id_proyecto_nucleo_fkey FOREIGN KEY (id_proyecto_nucleo) REFERENCES public.proyecto_nucleo(id_proyecto_nucleo);


--
-- Name: tramite_fifonafe tramite_fifonafe_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_fifonafe
    ADD CONSTRAINT tramite_fifonafe_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: tramite_ran tramite_ran_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran
    ADD CONSTRAINT tramite_ran_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: tramite_ran tramite_ran_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran
    ADD CONSTRAINT tramite_ran_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: tramite_ran_evento tramite_ran_evento_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran_evento
    ADD CONSTRAINT tramite_ran_evento_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: tramite_ran_evento tramite_ran_evento_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran_evento
    ADD CONSTRAINT tramite_ran_evento_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: tramite_ran_evento tramite_ran_evento_id_documento_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran_evento
    ADD CONSTRAINT tramite_ran_evento_id_documento_fkey FOREIGN KEY (id_documento) REFERENCES public.documento(id_documento);


--
-- Name: tramite_ran_evento tramite_ran_evento_id_tipo_evento_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran_evento
    ADD CONSTRAINT tramite_ran_evento_id_tipo_evento_fkey FOREIGN KEY (id_tipo_evento) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: tramite_ran_evento tramite_ran_evento_id_tramite_ran_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran_evento
    ADD CONSTRAINT tramite_ran_evento_id_tramite_ran_fkey FOREIGN KEY (id_tramite_ran) REFERENCES public.tramite_ran(id_tramite_ran);


--
-- Name: tramite_ran_evento tramite_ran_evento_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran_evento
    ADD CONSTRAINT tramite_ran_evento_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: tramite_ran tramite_ran_id_asamblea_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran
    ADD CONSTRAINT tramite_ran_id_asamblea_fkey FOREIGN KEY (id_asamblea) REFERENCES public.asamblea(id_asamblea);


--
-- Name: tramite_ran tramite_ran_id_convenio_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran
    ADD CONSTRAINT tramite_ran_id_convenio_fkey FOREIGN KEY (id_convenio) REFERENCES public.convenio(id_convenio);


--
-- Name: tramite_ran tramite_ran_id_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran
    ADD CONSTRAINT tramite_ran_id_nucleo_fkey FOREIGN KEY (id_nucleo) REFERENCES public.nucleo_agrario(id_nucleo);


--
-- Name: tramite_ran tramite_ran_id_orv_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran
    ADD CONSTRAINT tramite_ran_id_orv_fkey FOREIGN KEY (id_orv) REFERENCES public.orv(id_orv);


--
-- Name: tramite_ran tramite_ran_id_proyecto_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran
    ADD CONSTRAINT tramite_ran_id_proyecto_nucleo_fkey FOREIGN KEY (id_proyecto_nucleo) REFERENCES public.proyecto_nucleo(id_proyecto_nucleo);


--
-- Name: tramite_ran tramite_ran_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tramite_ran
    ADD CONSTRAINT tramite_ran_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: trazabilidad_fuente trazabilidad_fuente_id_importacion_tabular_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trazabilidad_fuente
    ADD CONSTRAINT trazabilidad_fuente_id_importacion_tabular_fkey FOREIGN KEY (id_importacion_tabular) REFERENCES public.importacion_tabular(id_importacion_tabular);


--
-- Name: trazabilidad_fuente trazabilidad_fuente_id_usuario_registro_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trazabilidad_fuente
    ADD CONSTRAINT trazabilidad_fuente_id_usuario_registro_fkey FOREIGN KEY (id_usuario_registro) REFERENCES public.usuario(id_usuario);


--
-- Name: trazo_proyecto trazo_proyecto_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trazo_proyecto
    ADD CONSTRAINT trazo_proyecto_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: trazo_proyecto trazo_proyecto_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trazo_proyecto
    ADD CONSTRAINT trazo_proyecto_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: trazo_proyecto trazo_proyecto_id_proyecto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trazo_proyecto
    ADD CONSTRAINT trazo_proyecto_id_proyecto_fkey FOREIGN KEY (id_proyecto) REFERENCES public.proyecto(id_proyecto);


--
-- Name: trazo_proyecto trazo_proyecto_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trazo_proyecto
    ADD CONSTRAINT trazo_proyecto_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: unidad_agraria unidad_agraria_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria
    ADD CONSTRAINT unidad_agraria_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: unidad_agraria unidad_agraria_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria
    ADD CONSTRAINT unidad_agraria_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: unidad_agraria unidad_agraria_id_destino_superficie_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria
    ADD CONSTRAINT unidad_agraria_id_destino_superficie_fkey FOREIGN KEY (id_destino_superficie) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: unidad_agraria unidad_agraria_id_nucleo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria
    ADD CONSTRAINT unidad_agraria_id_nucleo_fkey FOREIGN KEY (id_nucleo) REFERENCES public.nucleo_agrario(id_nucleo);


--
-- Name: unidad_agraria unidad_agraria_id_parcela_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria
    ADD CONSTRAINT unidad_agraria_id_parcela_fkey FOREIGN KEY (id_parcela) REFERENCES public.parcela(id_parcela);


--
-- Name: unidad_agraria unidad_agraria_id_tipo_gestion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria
    ADD CONSTRAINT unidad_agraria_id_tipo_gestion_fkey FOREIGN KEY (id_tipo_gestion) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: unidad_agraria unidad_agraria_id_tipo_tierra_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria
    ADD CONSTRAINT unidad_agraria_id_tipo_tierra_fkey FOREIGN KEY (id_tipo_tierra) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: unidad_agraria unidad_agraria_id_tipo_titularidad_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria
    ADD CONSTRAINT unidad_agraria_id_tipo_titularidad_fkey FOREIGN KEY (id_tipo_titularidad) REFERENCES public.catalogo_operativo(id_catalogo_opcion);


--
-- Name: unidad_agraria unidad_agraria_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria
    ADD CONSTRAINT unidad_agraria_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: unidad_agraria_titular unidad_agraria_titular_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria_titular
    ADD CONSTRAINT unidad_agraria_titular_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: unidad_agraria_titular unidad_agraria_titular_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria_titular
    ADD CONSTRAINT unidad_agraria_titular_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: unidad_agraria_titular unidad_agraria_titular_id_parcela_titular_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria_titular
    ADD CONSTRAINT unidad_agraria_titular_id_parcela_titular_fkey FOREIGN KEY (id_parcela_titular) REFERENCES public.parcela_titular(id_parcela_titular);


--
-- Name: unidad_agraria_titular unidad_agraria_titular_id_persona_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria_titular
    ADD CONSTRAINT unidad_agraria_titular_id_persona_fkey FOREIGN KEY (id_persona) REFERENCES public.persona(id_persona);


--
-- Name: unidad_agraria_titular unidad_agraria_titular_id_unidad_agraria_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria_titular
    ADD CONSTRAINT unidad_agraria_titular_id_unidad_agraria_fkey FOREIGN KEY (id_unidad_agraria) REFERENCES public.unidad_agraria(id_unidad_agraria);


--
-- Name: unidad_agraria_titular unidad_agraria_titular_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_agraria_titular
    ADD CONSTRAINT unidad_agraria_titular_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: usuario_proyecto usuario_proyecto_actualizado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_proyecto
    ADD CONSTRAINT usuario_proyecto_actualizado_por_fkey FOREIGN KEY (actualizado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: usuario_proyecto usuario_proyecto_asignado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_proyecto
    ADD CONSTRAINT usuario_proyecto_asignado_por_fkey FOREIGN KEY (asignado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: usuario_proyecto usuario_proyecto_creado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_proyecto
    ADD CONSTRAINT usuario_proyecto_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES public.usuario(id_usuario);


--
-- Name: usuario_proyecto usuario_proyecto_id_proyecto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_proyecto
    ADD CONSTRAINT usuario_proyecto_id_proyecto_fkey FOREIGN KEY (id_proyecto) REFERENCES public.proyecto(id_proyecto);


--
-- Name: usuario_proyecto usuario_proyecto_id_usuario_baja_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_proyecto
    ADD CONSTRAINT usuario_proyecto_id_usuario_baja_fkey FOREIGN KEY (id_usuario_baja) REFERENCES public.usuario(id_usuario);


--
-- Name: usuario_proyecto usuario_proyecto_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_proyecto
    ADD CONSTRAINT usuario_proyecto_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario);


--
-- PostgreSQL database dump complete
--


--
-- A celebrated assembly is derived from exactly one active convocation.
--

CREATE FUNCTION public.fn_validar_asamblea_catalogos() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE v_tipo TEXT; v_contexto TEXT;
BEGIN
    IF NOT fn_opcion_catalogo_valida(NEW.id_tipo_asamblea,'tipo_asamblea')
       OR (NEW.id_contexto_asamblea IS NOT NULL
           AND NOT fn_opcion_catalogo_valida(NEW.id_contexto_asamblea,'contexto_asamblea')) THEN
        RAISE EXCEPTION 'Tipo o contexto de asamblea invalido';
    END IF;
    SELECT codigo INTO v_tipo FROM catalogo_operativo WHERE id_catalogo_opcion=NEW.id_tipo_asamblea;
    SELECT codigo INTO v_contexto FROM catalogo_operativo WHERE id_catalogo_opcion=NEW.id_contexto_asamblea;
    IF (v_tipo='retiro_fondos' AND v_contexto IS DISTINCT FROM 'retiro_fondos')
       OR (v_tipo='anuencia' AND v_contexto='retiro_fondos') THEN
        RAISE EXCEPTION 'Tipo de asamblea y contexto contradictorios';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION public.fn_validar_asamblea_convocatoria() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_resultado TEXT;
BEGIN
    IF NEW.id_resultado IS NOT NULL THEN
        SELECT codigo INTO v_resultado
          FROM catalogo_operativo
         WHERE id_catalogo_opcion=NEW.id_resultado
           AND tipo_catalogo='resultado_convocatoria';
        IF v_resultado IS NULL THEN
            RAISE EXCEPTION 'Resultado de convocatoria invalido';
        END IF;
    END IF;

    IF NEW.fecha_realizacion IS NOT NULL AND v_resultado IS DISTINCT FROM 'celebrada' THEN
        RAISE EXCEPTION 'fecha_realizacion requiere resultado celebrada';
    END IF;
    IF v_resultado='celebrada' AND NEW.fecha_realizacion IS NULL THEN
        RAISE EXCEPTION 'Una convocatoria celebrada requiere fecha_realizacion';
    END IF;

    IF NEW.activo AND v_resultado='celebrada' THEN
        PERFORM 1 FROM asamblea WHERE id_asamblea=NEW.id_asamblea FOR UPDATE;
        IF EXISTS (
            SELECT 1
              FROM asamblea_convocatoria ac
              JOIN catalogo_operativo co ON co.id_catalogo_opcion=ac.id_resultado
             WHERE ac.id_asamblea=NEW.id_asamblea
               AND ac.activo
               AND co.tipo_catalogo='resultado_convocatoria'
               AND co.codigo='celebrada'
               AND ac.id_convocatoria IS DISTINCT FROM NEW.id_convocatoria
        ) THEN
            RAISE EXCEPTION 'Una asamblea solo puede tener una convocatoria celebrada activa';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

--
-- Canonical reporting views.
--

SET search_path = public, pg_catalog;

CREATE VIEW public.vw_convenio_tipo_cop_operativo AS
SELECT c.id_convenio,
       c.id_proyecto_nucleo,
       c.ambito,
       c.tipo_instrumento,
       c.tipo_convenio,
       c.consecutivo,
       c.id_convenio_padre,
       co.id_catalogo_opcion AS id_tipo_cop_operativo,
       co.codigo AS tipo_cop_operativo_codigo,
       co.nombre AS tipo_cop_operativo_nombre
  FROM convenio c
  LEFT JOIN catalogo_operativo co
    ON co.tipo_catalogo='tipo_cop_operativo'
   AND co.codigo = CASE
       WHEN c.tipo_convenio='cop_original' AND c.consecutivo=1 THEN 'ORIGEN'
       WHEN c.tipo_convenio='superficie_adicional' AND c.consecutivo=1 THEN 'ADICIONAL'
       WHEN c.tipo_convenio='superficie_adicional' AND c.consecutivo=2 THEN '2A_ADICIONAL'
       WHEN c.tipo_convenio='obras_complementarias' THEN 'COMPLEMENTARIAS'
       ELSE NULL
   END;

CREATE VIEW public.vw_orv_estado AS
WITH ran AS (
    SELECT tr.id_orv,
           max(tre.fecha_evento) FILTER (WHERE co.codigo='inscripcion') AS fecha_inscripcion_ran
      FROM tramite_ran tr
      JOIN tramite_ran_evento tre ON tre.id_tramite_ran=tr.id_tramite_ran AND tre.activo
      JOIN catalogo_operativo co ON co.id_catalogo_opcion=tre.id_tipo_evento
     WHERE tr.activo AND tr.id_orv IS NOT NULL
     GROUP BY tr.id_orv
)
SELECT o.id_orv, o.id_nucleo, o.numero_orv, o.inicio_vigencia, o.fin_vigencia,
       o.id_estado_registral,
       estado.codigo AS estado_registral_codigo,
       estado.nombre AS estado_registral_nombre,
       ran.fecha_inscripcion_ran,
       CASE WHEN NOT o.activo THEN 'inactivo'
            WHEN o.fin_vigencia IS NOT NULL AND o.fin_vigencia<CURRENT_DATE THEN 'vencido'
            ELSE 'vigente' END AS estado_vigencia,
       o.activo
  FROM orv o
  LEFT JOIN catalogo_operativo estado ON estado.id_catalogo_opcion=o.id_estado_registral
  LEFT JOIN ran ON ran.id_orv=o.id_orv;

CREATE VIEW public.vw_proyecto_nucleo_resumen AS
WITH responsable AS (
    SELECT DISTINCT ON (r.id_proyecto_nucleo)
           r.id_proyecto_nucleo, r.nombre, r.cargo, r.contacto
      FROM proyecto_nucleo_responsable r
     WHERE r.activo AND r.es_principal
     ORDER BY r.id_proyecto_nucleo, r.vigencia_inicio DESC NULLS LAST, r.id_responsable DESC
), referencia AS (
    SELECT DISTINCT ON (r.id_proyecto_nucleo)
           r.id_proyecto_nucleo, r.tipo_referencia, r.valor
      FROM proyecto_nucleo_referencia r
     WHERE r.activo AND r.es_principal
     ORDER BY r.id_proyecto_nucleo, r.tipo_referencia, r.id_referencia DESC
), parcelas AS (
    SELECT id_nucleo, count(*)::bigint AS total_parcelas
      FROM parcela WHERE activo GROUP BY id_nucleo
), afectaciones AS (
    SELECT id_proyecto_nucleo, count(*)::bigint AS total_afectaciones,
           count(*) FILTER (WHERE tipo_afectacion='colectivo')::bigint AS afectaciones_colectivas,
           count(*) FILTER (WHERE tipo_afectacion='individual')::bigint AS afectaciones_individuales,
           coalesce(sum(superficie_preliminar_ha),0)::numeric AS superficie_preliminar_ha,
           coalesce(sum(superficie_afectada_ha),0)::numeric AS superficie_afectada_ha
      FROM afectacion WHERE activo GROUP BY id_proyecto_nucleo
), asambleas AS (
    SELECT id_proyecto_nucleo, count(*)::bigint AS total_asambleas
      FROM asamblea WHERE activo GROUP BY id_proyecto_nucleo
), convenios AS (
    SELECT id_proyecto_nucleo, count(*)::bigint AS total_convenios
      FROM convenio WHERE activo GROUP BY id_proyecto_nucleo
), unidades AS (
    SELECT pn.id_proyecto_nucleo, count(DISTINCT aua.id_unidad_agraria)::bigint AS total_unidades_afectadas
      FROM proyecto_nucleo pn
      JOIN afectacion a ON a.id_proyecto_nucleo=pn.id_proyecto_nucleo AND a.activo
      JOIN afectacion_unidad_agraria aua ON aua.id_afectacion=a.id_afectacion AND aua.activo
     GROUP BY pn.id_proyecto_nucleo
)
SELECT pn.id_proyecto_nucleo, pn.id_proyecto, p.nombre_proyecto,
       pn.id_nucleo, n.nombre_nucleo,
       n.id_tipo_tenencia, tenencia.codigo AS tipo_tenencia_codigo,
       tenencia.nombre AS tipo_tenencia_nombre,
       pn.id_residencia, residencia.codigo AS residencia_codigo,
       residencia.nombre AS residencia_nombre,
       n.id_municipio, m.nombre AS municipio, e.id_entidad, e.nombre AS entidad,
       responsable.nombre AS responsable_nombre,
       responsable.cargo AS responsable_cargo,
       responsable.contacto AS responsable_contacto,
       referencia.tipo_referencia, referencia.valor AS referencia_principal,
       coalesce(parcelas.total_parcelas,0) AS total_parcelas,
       coalesce(afectaciones.total_afectaciones,0) AS total_afectaciones,
       coalesce(afectaciones.afectaciones_colectivas,0) AS afectaciones_colectivas,
       coalesce(afectaciones.afectaciones_individuales,0) AS afectaciones_individuales,
       coalesce(afectaciones.superficie_preliminar_ha,0) AS superficie_preliminar_ha,
       coalesce(afectaciones.superficie_afectada_ha,0) AS superficie_afectada_ha,
       coalesce(asambleas.total_asambleas,0) AS total_asambleas,
       coalesce(convenios.total_convenios,0) AS total_convenios,
       coalesce(unidades.total_unidades_afectadas,0) AS total_unidades_afectadas,
       pn.total_cops_planeados, pn.afecta_tuc, pn.id_motivo_no_afecta_tuc,
       pn.motivo_no_afecta_tuc_detalle, pn.tuc_revision_pendiente,
       pn.tuc_revision_detalle, pn.activo, pn.creado_en, pn.creado_por,
       pn.actualizado_en, pn.actualizado_por, pn.fecha_baja,
       pn.id_usuario_baja, pn.motivo_baja, pn.observaciones
  FROM proyecto_nucleo pn
  JOIN proyecto p ON p.id_proyecto=pn.id_proyecto
  JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo
  JOIN municipio m ON m.id_municipio=n.id_municipio
  JOIN entidad_federativa e ON e.id_entidad=m.id_entidad
  JOIN catalogo_operativo tenencia ON tenencia.id_catalogo_opcion=n.id_tipo_tenencia
  LEFT JOIN catalogo_operativo residencia ON residencia.id_catalogo_opcion=pn.id_residencia
  LEFT JOIN responsable ON responsable.id_proyecto_nucleo=pn.id_proyecto_nucleo
  LEFT JOIN referencia ON referencia.id_proyecto_nucleo=pn.id_proyecto_nucleo
  LEFT JOIN parcelas ON parcelas.id_nucleo=pn.id_nucleo
  LEFT JOIN afectaciones ON afectaciones.id_proyecto_nucleo=pn.id_proyecto_nucleo
  LEFT JOIN asambleas ON asambleas.id_proyecto_nucleo=pn.id_proyecto_nucleo
  LEFT JOIN convenios ON convenios.id_proyecto_nucleo=pn.id_proyecto_nucleo
  LEFT JOIN unidades ON unidades.id_proyecto_nucleo=pn.id_proyecto_nucleo;

CREATE VIEW public.vw_dashboard_kpi AS
WITH nucleos AS (
    SELECT pn.id_proyecto, extract(year FROM pn.creado_en)::integer AS anio,
           'nucleos'::text AS indicador, 0::bigint AS programado,
           count(*)::bigint AS realizado, count(*)::bigint AS cantidad,
           NULL::numeric AS superficie_ha, NULL::numeric AS monto
      FROM proyecto_nucleo pn WHERE pn.activo
     GROUP BY pn.id_proyecto, extract(year FROM pn.creado_en)
), actividades AS (
    SELECT pn.id_proyecto,
           extract(year FROM coalesce(a.fecha_realizada,a.fecha_programada,a.creado_en::date))::integer AS anio,
           a.tipo_actividad::text AS indicador,
           count(*) FILTER (WHERE a.fecha_programada IS NOT NULL)::bigint AS programado,
           count(*) FILTER (WHERE a.fecha_realizada IS NOT NULL)::bigint AS realizado,
           count(*)::bigint AS cantidad, NULL::numeric AS superficie_ha, NULL::numeric AS monto
      FROM actividad_campo a JOIN proyecto_nucleo pn USING(id_proyecto_nucleo)
     WHERE a.activo AND pn.activo
     GROUP BY pn.id_proyecto, extract(year FROM coalesce(a.fecha_realizada,a.fecha_programada,a.creado_en::date)), a.tipo_actividad
), asamblea_base AS (
    SELECT a.id_asamblea, pn.id_proyecto, tipo.codigo AS tipo_codigo,
           extract(year FROM coalesce(
               max(ac.fecha_realizacion) FILTER (WHERE resultado.codigo='celebrada'),
               min(ac.fecha_programada), a.creado_en::date))::integer AS anio,
           bool_or(ac.fecha_programada IS NOT NULL) AS programada,
           bool_or(resultado.codigo='celebrada') AS celebrada
      FROM asamblea a JOIN proyecto_nucleo pn USING(id_proyecto_nucleo)
      JOIN catalogo_operativo tipo ON tipo.id_catalogo_opcion=a.id_tipo_asamblea
      LEFT JOIN asamblea_convocatoria ac ON ac.id_asamblea=a.id_asamblea AND ac.activo
      LEFT JOIN catalogo_operativo resultado ON resultado.id_catalogo_opcion=ac.id_resultado
     WHERE a.activo AND pn.activo
     GROUP BY a.id_asamblea,pn.id_proyecto,tipo.codigo,a.creado_en
), asambleas AS (
    SELECT id_proyecto,anio,'asambleas'::text AS indicador,
           count(*) FILTER (WHERE programada)::bigint AS programado,
           count(*) FILTER (WHERE celebrada)::bigint AS realizado,
           count(*)::bigint AS cantidad,NULL::numeric AS superficie_ha,NULL::numeric AS monto
      FROM asamblea_base GROUP BY id_proyecto,anio
), retiro_fondos AS (
    SELECT id_proyecto,anio,'retiro_fondos'::text AS indicador,
           count(*) FILTER (WHERE programada)::bigint AS programado,
           count(*) FILTER (WHERE celebrada)::bigint AS realizado,
           count(*)::bigint AS cantidad,NULL::numeric AS superficie_ha,NULL::numeric AS monto
      FROM asamblea_base WHERE tipo_codigo='retiro_fondos' GROUP BY id_proyecto,anio
), ran_base AS (
    SELECT tr.id_tramite_ran,pn.id_proyecto,tr.fecha_programada_ingreso,tr.creado_en,
           CASE WHEN tr.id_asamblea IS NOT NULL THEN 'acta' ELSE 'convenio' END AS objetivo,
           max(e.fecha_evento) FILTER (WHERE tipo.codigo IN ('ingreso','reingreso')) AS fecha_ingreso,
           max(e.fecha_evento) FILTER (WHERE tipo.codigo='inscripcion') AS fecha_inscripcion
      FROM tramite_ran tr JOIN proyecto_nucleo pn USING(id_proyecto_nucleo)
      LEFT JOIN tramite_ran_evento e ON e.id_tramite_ran=tr.id_tramite_ran AND e.activo
      LEFT JOIN catalogo_operativo tipo ON tipo.id_catalogo_opcion=e.id_tipo_evento
     WHERE tr.activo AND pn.activo AND (tr.id_asamblea IS NOT NULL OR tr.id_convenio IS NOT NULL)
     GROUP BY tr.id_tramite_ran,pn.id_proyecto,tr.fecha_programada_ingreso,tr.creado_en,
              CASE WHEN tr.id_asamblea IS NOT NULL THEN 'acta' ELSE 'convenio' END
), ran AS (
    SELECT rb.id_proyecto,
           extract(year FROM coalesce(rb.fecha_inscripcion,rb.fecha_ingreso,rb.fecha_programada_ingreso,rb.creado_en::date))::integer AS anio,
           v.indicador, count(*) FILTER (WHERE v.programada)::bigint AS programado,
           count(*) FILTER (WHERE v.realizada)::bigint AS realizado,
           count(*) FILTER (WHERE v.realizada)::bigint AS cantidad,
           NULL::numeric AS superficie_ha,NULL::numeric AS monto
      FROM ran_base rb
      CROSS JOIN LATERAL (VALUES
          ('ingreso_ran_'||rb.objetivo,rb.fecha_programada_ingreso IS NOT NULL,rb.fecha_ingreso IS NOT NULL),
          ('inscripcion_ran_'||rb.objetivo,false,rb.fecha_inscripcion IS NOT NULL)
      ) v(indicador,programada,realizada)
     GROUP BY rb.id_proyecto,extract(year FROM coalesce(rb.fecha_inscripcion,rb.fecha_ingreso,rb.fecha_programada_ingreso,rb.creado_en::date)),v.indicador
), convenios AS (
    SELECT pn.id_proyecto,extract(year FROM coalesce(c.fecha_firma,c.fecha_programada_firma,c.creado_en::date))::integer AS anio,
           CASE WHEN c.tipo_convenio='cop_original' AND c.ambito='colectivo' THEN 'cop_colectivos'
                WHEN c.tipo_convenio='cop_original' AND c.ambito='individual' THEN 'cop_individuales'
                WHEN c.tipo_convenio='modificatorio' THEN 'modificatorios'
                WHEN c.tipo_convenio='superficie_adicional' THEN 'superficies_adicionales'
                WHEN c.tipo_convenio='obras_complementarias' THEN 'obras_complementarias'
                WHEN c.tipo_convenio='ampliacion' THEN 'ampliaciones'
                WHEN c.tipo_convenio='ampliacion_remanente' THEN 'ampliaciones_remanentes'
                ELSE 'otros_instrumentos' END::text AS indicador,
           count(*) FILTER (WHERE c.fecha_programada_firma IS NOT NULL)::bigint AS programado,
           count(*) FILTER (WHERE c.fecha_firma IS NOT NULL)::bigint AS realizado,
           count(*)::bigint AS cantidad,sum(c.superficie_ha)::numeric AS superficie_ha,sum(c.monto_100)::numeric AS monto
      FROM convenio c JOIN proyecto_nucleo pn USING(id_proyecto_nucleo)
     WHERE c.activo AND pn.activo
     GROUP BY pn.id_proyecto,extract(year FROM coalesce(c.fecha_firma,c.fecha_programada_firma,c.creado_en::date)),
              CASE WHEN c.tipo_convenio='cop_original' AND c.ambito='colectivo' THEN 'cop_colectivos'
                   WHEN c.tipo_convenio='cop_original' AND c.ambito='individual' THEN 'cop_individuales'
                   WHEN c.tipo_convenio='modificatorio' THEN 'modificatorios'
                   WHEN c.tipo_convenio='superficie_adicional' THEN 'superficies_adicionales'
                   WHEN c.tipo_convenio='obras_complementarias' THEN 'obras_complementarias'
                   WHEN c.tipo_convenio='ampliacion' THEN 'ampliaciones'
                   WHEN c.tipo_convenio='ampliacion_remanente' THEN 'ampliaciones_remanentes'
                   ELSE 'otros_instrumentos' END
), afectaciones AS (
    SELECT pn.id_proyecto,extract(year FROM a.creado_en)::integer AS anio,v.indicador,
           0::bigint AS programado,
           CASE WHEN v.indicador='expropiacion_directa' THEN count(*) FILTER (WHERE a.condicion_especial='expropiacion_directa')
                ELSE count(DISTINCT a.id_afectacion) END::bigint AS realizado,
           CASE WHEN v.indicador='expropiacion_directa' THEN count(*) FILTER (WHERE a.condicion_especial='expropiacion_directa')
                ELSE count(DISTINCT a.id_afectacion) END::bigint AS cantidad,
           CASE WHEN v.indicador='superficie_preliminar_administrativa' THEN sum(a.superficie_preliminar_ha)
                WHEN v.indicador='superficie_afectada_administrativa' THEN sum(a.superficie_afectada_ha) END::numeric AS superficie_ha,
           NULL::numeric AS monto
      FROM afectacion a JOIN proyecto_nucleo pn USING(id_proyecto_nucleo)
      CROSS JOIN (VALUES ('expropiacion_directa'::text),
                         ('superficie_preliminar_administrativa'),('superficie_afectada_administrativa')) v(indicador)
     WHERE a.activo AND pn.activo
     GROUP BY pn.id_proyecto,extract(year FROM a.creado_en),v.indicador
), parcelas_afectadas AS (
    SELECT pn.id_proyecto,extract(year FROM a.creado_en)::integer AS anio,
           'parcelas_afectadas'::text AS indicador,0::bigint AS programado,
           count(DISTINCT ua.id_parcela)::bigint AS realizado,
           count(DISTINCT ua.id_parcela)::bigint AS cantidad,
           NULL::numeric AS superficie_ha,NULL::numeric AS monto
      FROM afectacion a JOIN proyecto_nucleo pn USING(id_proyecto_nucleo)
      JOIN afectacion_unidad_agraria aua ON aua.id_afectacion=a.id_afectacion AND aua.activo
      JOIN unidad_agraria ua ON ua.id_unidad_agraria=aua.id_unidad_agraria AND ua.activo
     WHERE a.activo AND pn.activo AND ua.id_parcela IS NOT NULL
     GROUP BY pn.id_proyecto,extract(year FROM a.creado_en)
), fifonafe_base AS (
    SELECT tf.id_tramite_fifonafe,pn.id_proyecto,tf.estatus,tf.hay_conflictos,tf.creado_en,
           min(e.fecha_oficio) AS fecha_inicio,max(e.fecha_oficio) AS fecha_fin
      FROM tramite_fifonafe tf JOIN proyecto_nucleo pn USING(id_proyecto_nucleo)
      LEFT JOIN tramite_fifonafe_evento e ON e.id_tramite_fifonafe=tf.id_tramite_fifonafe AND e.activo
     WHERE tf.activo AND pn.activo
     GROUP BY tf.id_tramite_fifonafe,pn.id_proyecto,tf.estatus,tf.hay_conflictos,tf.creado_en
), fifonafe AS (
    SELECT id_proyecto,extract(year FROM coalesce(fecha_fin,fecha_inicio,creado_en::date))::integer AS anio,v.indicador,
           count(*) FILTER (WHERE estatus IN ('programado','pendiente'))::bigint AS programado,
           count(*) FILTER (WHERE estatus='completo')::bigint AS realizado,
           CASE WHEN v.indicador='no_conflictos' THEN count(*) FILTER (WHERE hay_conflictos IS FALSE) ELSE count(*) END::bigint AS cantidad,
           NULL::numeric AS superficie_ha,NULL::numeric AS monto
      FROM fifonafe_base CROSS JOIN (VALUES ('fifonafe'::text),('no_conflictos')) v(indicador)
     WHERE v.indicador<>'no_conflictos' OR hay_conflictos IS FALSE
     GROUP BY id_proyecto,extract(year FROM coalesce(fecha_fin,fecha_inicio,creado_en::date)),v.indicador
), indemnizaciones AS (
    SELECT pn.id_proyecto,extract(year FROM coalesce(i.fecha_resolucion,i.fecha_programada,i.creado_en::date))::integer AS anio,
           'indemnizaciones'::text AS indicador,count(*) FILTER (WHERE i.fecha_programada IS NOT NULL)::bigint AS programado,
           count(*) FILTER (WHERE i.fecha_resolucion IS NOT NULL OR i.estatus='completo')::bigint AS realizado,
           count(*)::bigint AS cantidad,NULL::numeric AS superficie_ha,NULL::numeric AS monto
      FROM indemnizacion i JOIN afectacion a USING(id_afectacion) JOIN proyecto_nucleo pn USING(id_proyecto_nucleo)
     WHERE i.activo AND a.activo AND pn.activo
     GROUP BY pn.id_proyecto,extract(year FROM coalesce(i.fecha_resolucion,i.fecha_programada,i.creado_en::date))
), pagos AS (
    SELECT pn.id_proyecto,extract(year FROM p.fecha_pago)::integer AS anio,'pagos'::text AS indicador,
           0::bigint AS programado,count(*)::bigint AS realizado,count(*)::bigint AS cantidad,
           NULL::numeric AS superficie_ha,sum(p.monto)::numeric AS monto
      FROM pago p JOIN indemnizacion i USING(id_indemnizacion)
      JOIN afectacion a USING(id_afectacion) JOIN proyecto_nucleo pn USING(id_proyecto_nucleo)
     WHERE p.activo AND i.activo AND a.activo AND pn.activo
     GROUP BY pn.id_proyecto,extract(year FROM p.fecha_pago)
)
SELECT * FROM nucleos UNION ALL SELECT * FROM actividades UNION ALL SELECT * FROM asambleas
UNION ALL SELECT * FROM retiro_fondos UNION ALL SELECT * FROM ran UNION ALL SELECT * FROM convenios
UNION ALL SELECT * FROM afectaciones UNION ALL SELECT * FROM parcelas_afectadas UNION ALL SELECT * FROM fifonafe
UNION ALL SELECT * FROM indemnizaciones UNION ALL SELECT * FROM pagos;

SELECT pg_catalog.set_config('search_path', '', false);


CREATE INDEX idx_nucleo_municipio_tenencia
ON public.nucleo_agrario USING btree (id_municipio, id_tipo_tenencia)
WHERE activo;

CREATE UNIQUE INDEX uq_nucleo_activo_normalizado
ON public.nucleo_agrario USING btree (
    id_municipio,
    id_tipo_tenencia,
    lower(btrim(nombre_nucleo))
) WHERE activo;

CREATE TRIGGER trg_validar_asamblea_catalogos
BEFORE INSERT OR UPDATE OF id_tipo_asamblea, id_contexto_asamblea
ON public.asamblea
FOR EACH ROW EXECUTE FUNCTION public.fn_validar_asamblea_catalogos();

CREATE TRIGGER trg_validar_nucleo_catalogo
BEFORE INSERT OR UPDATE OF id_tipo_tenencia ON public.nucleo_agrario
FOR EACH ROW EXECUTE FUNCTION public.fn_validar_catalogos_dominio();

CREATE TRIGGER trg_validar_proyecto_nucleo_catalogo
BEFORE INSERT OR UPDATE OF id_residencia ON public.proyecto_nucleo
FOR EACH ROW EXECUTE FUNCTION public.fn_validar_catalogos_dominio();

CREATE TRIGGER trg_validar_orv_catalogo
BEFORE INSERT OR UPDATE OF id_estado_registral ON public.orv
FOR EACH ROW EXECUTE FUNCTION public.fn_validar_catalogos_dominio();

CREATE TRIGGER trg_validar_asamblea_convocatoria
BEFORE INSERT OR UPDATE OF id_asamblea, id_resultado, fecha_realizacion, activo
ON public.asamblea_convocatoria
FOR EACH ROW EXECUTE FUNCTION public.fn_validar_asamblea_convocatoria();

--
-- Application ACL. Role creation and passwords belong to bootstrap, not migrations.
--

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='software_pa_app') THEN
        RAISE EXCEPTION 'Required role software_pa_app does not exist; run role bootstrap first';
    END IF;
END;
$$;

GRANT USAGE ON SCHEMA public TO software_pa_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO software_pa_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO software_pa_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO software_pa_app;
REVOKE DELETE, TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM software_pa_app;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON public.schema_migrations FROM software_pa_app;
GRANT SELECT ON public.schema_migrations TO software_pa_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE ON TABLES TO software_pa_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO software_pa_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO software_pa_app;


-- End SOFTWARE-PA canonical baseline v1.
