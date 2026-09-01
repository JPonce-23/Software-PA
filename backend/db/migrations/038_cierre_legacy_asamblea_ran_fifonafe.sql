-- 038_cierre_legacy_asamblea_ran_fifonafe.sql
BEGIN;
SELECT pg_advisory_xact_lock(20260901, 38);

DO $preflight$
DECLARE v_required TEXT;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='037') THEN
    RAISE EXCEPTION '038 requiere la migracion 037';
  END IF;
  IF EXISTS (SELECT 1 FROM schema_migrations WHERE version='038') THEN
    RAISE EXCEPTION 'La migracion 038 ya fue aplicada';
  END IF;
  FOREACH v_required IN ARRAY ARRAY[
    'usuario','nucleo_agrario','proyecto_nucleo','orv','asamblea','asamblea_convocatoria',
    'afectacion','convenio','tramite_ran','tramite_ran_evento','tramite_fifonafe',
    'tramite_fifonafe_evento','catalogo_operativo','schema_migrations'
  ] LOOP
    IF to_regclass('public.'||v_required) IS NULL THEN
      RAISE EXCEPTION '038 requiere la tabla %',v_required;
    END IF;
  END LOOP;
  IF NOT EXISTS (SELECT 1 FROM usuario WHERE activo) THEN
    RAISE EXCEPTION '038 requiere al menos un usuario activo';
  END IF;
END;
$preflight$;

SELECT set_config('app.current_user_id',
  (SELECT min(id_usuario)::text FROM usuario WHERE activo), TRUE);

-- 1) TramiteRAN: Asamblea/Convenio por ProyectoNucleo; ORV por NucleoAgrario.
ALTER TABLE tramite_ran ADD COLUMN id_nucleo INTEGER REFERENCES nucleo_agrario(id_nucleo);
ALTER TABLE tramite_ran ALTER COLUMN id_proyecto_nucleo DROP NOT NULL;
DROP TRIGGER IF EXISTS trg_036_tramite_ran_objetivo ON tramite_ran;

UPDATE tramite_ran t
SET id_nucleo=o.id_nucleo,
    id_proyecto_nucleo=NULL,
    actualizado_en=COALESCE(t.actualizado_en,now()),
    actualizado_por=COALESCE(t.actualizado_por,NULLIF(current_setting('app.current_user_id',TRUE),'')::integer)
FROM orv o
WHERE t.id_orv=o.id_orv;

UPDATE tramite_ran SET id_nucleo=NULL
WHERE id_asamblea IS NOT NULL OR id_convenio IS NOT NULL;

ALTER TABLE tramite_ran ADD CONSTRAINT chk_tramite_ran_contexto_038 CHECK (
  (id_orv IS NOT NULL AND id_proyecto_nucleo IS NULL AND id_nucleo IS NOT NULL)
  OR
  ((id_asamblea IS NOT NULL OR id_convenio IS NOT NULL)
    AND id_proyecto_nucleo IS NOT NULL AND id_nucleo IS NULL)
);

CREATE OR REPLACE FUNCTION fn_038_validar_tramite_ran_contexto()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
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
$fn$;
CREATE TRIGGER trg_038_tramite_ran_contexto
BEFORE INSERT OR UPDATE OF id_proyecto_nucleo,id_nucleo,id_asamblea,id_convenio,id_orv,activo
ON tramite_ran FOR EACH ROW EXECUTE FUNCTION fn_038_validar_tramite_ran_contexto();

CREATE OR REPLACE FUNCTION fn_038_tramite_ran_objetivo_inmutable()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
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
$fn$;
CREATE TRIGGER trg_038_tramite_ran_objetivo_inmutable
BEFORE UPDATE OF id_proyecto_nucleo,id_nucleo,id_asamblea,id_convenio,id_orv
ON tramite_ran FOR EACH ROW EXECUTE FUNCTION fn_038_tramite_ran_objetivo_inmutable();

DROP INDEX IF EXISTS uq_tramite_ran_asamblea;
DROP INDEX IF EXISTS uq_tramite_ran_convenio;
DROP INDEX IF EXISTS uq_tramite_ran_orv;
CREATE INDEX idx_tramite_ran_asamblea ON tramite_ran(id_asamblea,creado_en DESC,id_tramite_ran DESC)
  WHERE activo AND id_asamblea IS NOT NULL;
CREATE INDEX idx_tramite_ran_convenio ON tramite_ran(id_convenio,creado_en DESC,id_tramite_ran DESC)
  WHERE activo AND id_convenio IS NOT NULL;
CREATE INDEX idx_tramite_ran_orv ON tramite_ran(id_orv,creado_en DESC,id_tramite_ran DESC)
  WHERE activo AND id_orv IS NOT NULL;
CREATE INDEX idx_tramite_ran_nucleo ON tramite_ran(id_nucleo,creado_en DESC,id_tramite_ran DESC)
  WHERE activo AND id_nucleo IS NOT NULL;

COMMENT ON COLUMN tramite_ran.id_proyecto_nucleo IS
'Contexto requerido para RAN de Asamblea/Convenio; NULL para ORV desde 038.';
COMMENT ON COLUMN tramite_ran.id_nucleo IS
'Contexto del RAN de ORV; deriva del NucleoAgrario del ORV.';
COMMENT ON TABLE tramite_ran IS
'Tramite registral repetible 1:N por Asamblea, Convenio u ORV; ORV se contextualiza por NucleoAgrario.';

-- 2) Resumen legacy RAN: solo proyeccion del tramite activo mas reciente.
CREATE OR REPLACE FUNCTION fn_038_refrescar_resumen_ran(
  p_asamblea INTEGER,p_convenio INTEGER,p_orv INTEGER
) RETURNS VOID LANGUAGE plpgsql AS $fn$
DECLARE v_tramite BIGINT; v_codigo TEXT; v_estado BIGINT;
BEGIN
  IF p_asamblea IS NOT NULL THEN
    SELECT id_tramite_ran INTO v_tramite FROM tramite_ran
    WHERE id_asamblea=p_asamblea AND activo
    ORDER BY creado_en DESC,id_tramite_ran DESC LIMIT 1;
    UPDATE asamblea a SET
      fecha_programada_ingreso_ran=(SELECT fecha_programada_ingreso FROM tramite_ran WHERE id_tramite_ran=v_tramite),
      fecha_ingreso_ran=(SELECT min(e.fecha_evento) FROM tramite_ran_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_ran=v_tramite AND e.activo AND c.codigo IN('ingreso','reingreso')),
      numero_solicitud_ran=(SELECT e.numero_solicitud FROM tramite_ran_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_ran=v_tramite AND e.activo AND c.codigo IN('ingreso','reingreso') AND e.numero_solicitud IS NOT NULL ORDER BY e.ordinal DESC,e.id_evento_ran DESC LIMIT 1),
      calificacion_registral_ran=(SELECT e.calificacion FROM tramite_ran_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_ran=v_tramite AND e.activo AND c.codigo='calificacion' ORDER BY e.ordinal DESC,e.id_evento_ran DESC LIMIT 1),
      fecha_inscripcion_ran=(SELECT max(e.fecha_evento) FROM tramite_ran_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_ran=v_tramite AND e.activo AND c.codigo='inscripcion'),
      actualizado_en=now(), actualizado_por=NULLIF(current_setting('app.current_user_id',TRUE),'')::integer
    WHERE a.id_asamblea=p_asamblea;
  ELSIF p_convenio IS NOT NULL THEN
    SELECT id_tramite_ran INTO v_tramite FROM tramite_ran
    WHERE id_convenio=p_convenio AND activo
    ORDER BY creado_en DESC,id_tramite_ran DESC LIMIT 1;
    UPDATE convenio v SET
      fecha_programada_ingreso_ran=(SELECT fecha_programada_ingreso FROM tramite_ran WHERE id_tramite_ran=v_tramite),
      ingreso_ran_fecha=(SELECT min(e.fecha_evento) FROM tramite_ran_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_ran=v_tramite AND e.activo AND c.codigo IN('ingreso','reingreso')),
      numero_solicitud_ingreso=(SELECT e.numero_solicitud FROM tramite_ran_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_ran=v_tramite AND e.activo AND c.codigo IN('ingreso','reingreso') AND e.numero_solicitud IS NOT NULL ORDER BY e.ordinal DESC,e.id_evento_ran DESC LIMIT 1),
      calificacion_registral=(SELECT e.calificacion FROM tramite_ran_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_ran=v_tramite AND e.activo AND c.codigo='calificacion' ORDER BY e.ordinal DESC,e.id_evento_ran DESC LIMIT 1),
      fecha_inscripcion_ran=(SELECT max(e.fecha_evento) FROM tramite_ran_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_ran=v_tramite AND e.activo AND c.codigo='inscripcion'),
      actualizado_en=now(), actualizado_por=NULLIF(current_setting('app.current_user_id',TRUE),'')::integer
    WHERE v.id_convenio=p_convenio;
  ELSIF p_orv IS NOT NULL THEN
    SELECT id_tramite_ran INTO v_tramite FROM tramite_ran
    WHERE id_orv=p_orv AND activo
    ORDER BY creado_en DESC,id_tramite_ran DESC LIMIT 1;
    SELECT c.codigo INTO v_codigo FROM tramite_ran_evento e
    JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento
    WHERE e.id_tramite_ran=v_tramite AND e.activo
    ORDER BY e.ordinal DESC,e.id_evento_ran DESC LIMIT 1;
    IF v_codigo IS NOT NULL THEN
      SELECT id_catalogo_opcion INTO v_estado FROM catalogo_operativo
      WHERE tipo_catalogo='estado_registral_orv' AND activo AND codigo=CASE
        WHEN v_codigo='inscripcion' THEN 'inscrita'
        WHEN v_codigo='prevencion' THEN 'prevenida'
        WHEN v_codigo IN('ingreso','reingreso','subsanacion','calificacion') THEN 'en_proceso'
        ELSE 'otro' END;
    END IF;
    UPDATE orv o SET
      fecha_inscripcion_acta_ran=(SELECT max(e.fecha_evento) FROM tramite_ran_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_ran=v_tramite AND e.activo AND c.codigo='inscripcion'),
      id_estado_registral=COALESCE(v_estado,o.id_estado_registral),
      actualizado_en=now(), actualizado_por=NULLIF(current_setting('app.current_user_id',TRUE),'')::integer
    WHERE o.id_orv=p_orv;
  END IF;
END;
$fn$;

CREATE OR REPLACE FUNCTION fn_036_resumir_ran_legacy()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
DECLARE a INTEGER; c INTEGER; o INTEGER; oa INTEGER; oc INTEGER; oo INTEGER;
BEGIN
  SELECT id_asamblea,id_convenio,id_orv INTO a,c,o FROM tramite_ran WHERE id_tramite_ran=NEW.id_tramite_ran;
  IF TG_OP='UPDATE' AND OLD.id_tramite_ran IS DISTINCT FROM NEW.id_tramite_ran THEN
    SELECT id_asamblea,id_convenio,id_orv INTO oa,oc,oo FROM tramite_ran WHERE id_tramite_ran=OLD.id_tramite_ran;
    PERFORM fn_038_refrescar_resumen_ran(oa,oc,oo);
  END IF;
  PERFORM fn_038_refrescar_resumen_ran(a,c,o);
  RETURN NEW;
END;
$fn$;
DROP TRIGGER IF EXISTS trg_036_evento_ran_resumen_legacy ON tramite_ran_evento;
CREATE TRIGGER trg_038_evento_ran_resumen_legacy
AFTER INSERT OR UPDATE OF id_tramite_ran,id_tipo_evento,fecha_evento,numero_solicitud,calificacion,activo
ON tramite_ran_evento FOR EACH ROW EXECUTE FUNCTION fn_036_resumir_ran_legacy();

CREATE OR REPLACE FUNCTION fn_038_tramite_ran_refrescar_legacy()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
BEGIN
  PERFORM fn_038_refrescar_resumen_ran(NEW.id_asamblea,NEW.id_convenio,NEW.id_orv);
  RETURN NEW;
END;
$fn$;
CREATE TRIGGER trg_038_tramite_ran_refrescar_legacy
AFTER INSERT OR UPDATE OF fecha_programada_ingreso,activo
ON tramite_ran FOR EACH ROW EXECUTE FUNCTION fn_038_tramite_ran_refrescar_legacy();

-- 3) Guardas: columnas legacy quedan read-only; triggers hijos pueden proyectarlas.
CREATE OR REPLACE FUNCTION fn_038_bloquear_asamblea_legacy()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
BEGIN
  IF pg_trigger_depth()>1 THEN RETURN NEW; END IF;
  IF TG_OP='INSERT' THEN
    IF num_nonnulls(NEW.fecha_expedicion_primera,NEW.fecha_programada_primera,
      NEW.fecha_expedicion_segunda,NEW.fecha_programada_segunda,NEW.fecha_realizada,
      NEW.fecha_programada_ingreso_ran,NEW.fecha_ingreso_ran,NEW.numero_solicitud_ran,
      NEW.calificacion_registral_ran,NEW.fecha_inscripcion_ran)>0 THEN
      RAISE EXCEPTION '038: campos legacy Asamblea read-only; use convocatoria/TramiteRAN';
    END IF;
  ELSIF OLD.fecha_expedicion_primera IS DISTINCT FROM NEW.fecha_expedicion_primera
     OR OLD.fecha_programada_primera IS DISTINCT FROM NEW.fecha_programada_primera
     OR OLD.fecha_expedicion_segunda IS DISTINCT FROM NEW.fecha_expedicion_segunda
     OR OLD.fecha_programada_segunda IS DISTINCT FROM NEW.fecha_programada_segunda
     OR OLD.fecha_realizada IS DISTINCT FROM NEW.fecha_realizada
     OR OLD.fecha_programada_ingreso_ran IS DISTINCT FROM NEW.fecha_programada_ingreso_ran
     OR OLD.fecha_ingreso_ran IS DISTINCT FROM NEW.fecha_ingreso_ran
     OR OLD.numero_solicitud_ran IS DISTINCT FROM NEW.numero_solicitud_ran
     OR OLD.calificacion_registral_ran IS DISTINCT FROM NEW.calificacion_registral_ran
     OR OLD.fecha_inscripcion_ran IS DISTINCT FROM NEW.fecha_inscripcion_ran THEN
    RAISE EXCEPTION '038: campos legacy Asamblea read-only; use estructuras canonicas';
  END IF;
  RETURN NEW;
END;
$fn$;
CREATE TRIGGER trg_038_asamblea_legacy_readonly
BEFORE INSERT OR UPDATE OF fecha_expedicion_primera,fecha_programada_primera,
 fecha_expedicion_segunda,fecha_programada_segunda,fecha_realizada,
 fecha_programada_ingreso_ran,fecha_ingreso_ran,numero_solicitud_ran,
 calificacion_registral_ran,fecha_inscripcion_ran
ON asamblea FOR EACH ROW EXECUTE FUNCTION fn_038_bloquear_asamblea_legacy();

CREATE OR REPLACE FUNCTION fn_038_bloquear_convenio_ran_legacy()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
BEGIN
  IF pg_trigger_depth()>1 THEN RETURN NEW; END IF;
  IF TG_OP='INSERT' THEN
    IF num_nonnulls(NEW.fecha_programada_ingreso_ran,NEW.ingreso_ran_fecha,
      NEW.numero_solicitud_ingreso,NEW.calificacion_registral,NEW.fecha_inscripcion_ran)>0 THEN
      RAISE EXCEPTION '038: RAN legacy Convenio read-only; use TramiteRAN';
    END IF;
  ELSIF OLD.fecha_programada_ingreso_ran IS DISTINCT FROM NEW.fecha_programada_ingreso_ran
     OR OLD.ingreso_ran_fecha IS DISTINCT FROM NEW.ingreso_ran_fecha
     OR OLD.numero_solicitud_ingreso IS DISTINCT FROM NEW.numero_solicitud_ingreso
     OR OLD.calificacion_registral IS DISTINCT FROM NEW.calificacion_registral
     OR OLD.fecha_inscripcion_ran IS DISTINCT FROM NEW.fecha_inscripcion_ran THEN
    RAISE EXCEPTION '038: RAN legacy Convenio read-only; use TramiteRAN';
  END IF;
  RETURN NEW;
END;
$fn$;
CREATE TRIGGER trg_038_convenio_ran_legacy_readonly
BEFORE INSERT OR UPDATE OF fecha_programada_ingreso_ran,ingreso_ran_fecha,
 numero_solicitud_ingreso,calificacion_registral,fecha_inscripcion_ran
ON convenio FOR EACH ROW EXECUTE FUNCTION fn_038_bloquear_convenio_ran_legacy();

CREATE OR REPLACE FUNCTION fn_038_bloquear_fifonafe_legacy()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
BEGIN
  IF pg_trigger_depth()>1 THEN RETURN NEW; END IF;
  IF TG_OP='INSERT' THEN
    IF num_nonnulls(NEW.no_oficio_fifonafe_a_dgaopr,NEW.fecha_oficio_fifonafe_a_dgaopr,
      NEW.no_oficio_dgaopr_a_representacion,NEW.fecha_oficio_dgaopr_a_representacion,
      NEW.no_oficio_respuesta_representacion_a_dgaopr,NEW.fecha_oficio_respuesta_representacion_a_dgaopr,
      NEW.no_oficio_respuesta_dgaopr_a_fifonafe,NEW.fecha_oficio_respuesta_dgaopr_a_fifonafe)>0 THEN
      RAISE EXCEPTION '038: oficios FIFONAFE legacy read-only; use eventos';
    END IF;
  ELSIF OLD.no_oficio_fifonafe_a_dgaopr IS DISTINCT FROM NEW.no_oficio_fifonafe_a_dgaopr
     OR OLD.fecha_oficio_fifonafe_a_dgaopr IS DISTINCT FROM NEW.fecha_oficio_fifonafe_a_dgaopr
     OR OLD.no_oficio_dgaopr_a_representacion IS DISTINCT FROM NEW.no_oficio_dgaopr_a_representacion
     OR OLD.fecha_oficio_dgaopr_a_representacion IS DISTINCT FROM NEW.fecha_oficio_dgaopr_a_representacion
     OR OLD.no_oficio_respuesta_representacion_a_dgaopr IS DISTINCT FROM NEW.no_oficio_respuesta_representacion_a_dgaopr
     OR OLD.fecha_oficio_respuesta_representacion_a_dgaopr IS DISTINCT FROM NEW.fecha_oficio_respuesta_representacion_a_dgaopr
     OR OLD.no_oficio_respuesta_dgaopr_a_fifonafe IS DISTINCT FROM NEW.no_oficio_respuesta_dgaopr_a_fifonafe
     OR OLD.fecha_oficio_respuesta_dgaopr_a_fifonafe IS DISTINCT FROM NEW.fecha_oficio_respuesta_dgaopr_a_fifonafe THEN
    RAISE EXCEPTION '038: oficios FIFONAFE legacy read-only; use eventos';
  END IF;
  RETURN NEW;
END;
$fn$;
CREATE TRIGGER trg_038_fifonafe_legacy_readonly
BEFORE INSERT OR UPDATE OF no_oficio_fifonafe_a_dgaopr,fecha_oficio_fifonafe_a_dgaopr,
 no_oficio_dgaopr_a_representacion,fecha_oficio_dgaopr_a_representacion,
 no_oficio_respuesta_representacion_a_dgaopr,fecha_oficio_respuesta_representacion_a_dgaopr,
 no_oficio_respuesta_dgaopr_a_fifonafe,fecha_oficio_respuesta_dgaopr_a_fifonafe
ON tramite_fifonafe FOR EACH ROW EXECUTE FUNCTION fn_038_bloquear_fifonafe_legacy();

-- La fecha registral ORV queda como resumen RAN. id_estado_registral sigue siendo
-- el estado canónico y acta_eleccion_inscrita_ran ya se deriva de éste desde 036.
CREATE OR REPLACE FUNCTION fn_038_bloquear_orv_fecha_ran_legacy()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
BEGIN
  IF pg_trigger_depth()>1 THEN RETURN NEW; END IF;
  IF TG_OP='INSERT' THEN
    IF NEW.fecha_inscripcion_acta_ran IS NOT NULL THEN
      RAISE EXCEPTION '038: fecha RAN legacy ORV read-only; use TramiteRAN';
    END IF;
  ELSIF OLD.fecha_inscripcion_acta_ran IS DISTINCT FROM NEW.fecha_inscripcion_acta_ran THEN
    RAISE EXCEPTION '038: fecha RAN legacy ORV read-only; use TramiteRAN';
  END IF;
  RETURN NEW;
END;
$fn$;
CREATE TRIGGER trg_038_orv_fecha_ran_legacy_readonly
BEFORE INSERT OR UPDATE OF fecha_inscripcion_acta_ran
ON orv FOR EACH ROW EXECUTE FUNCTION fn_038_bloquear_orv_fecha_ran_legacy();

-- 4) FIFONAFE completo se valida contra eventos canonicos, no columnas legacy.
ALTER TABLE tramite_fifonafe DROP CONSTRAINT IF EXISTS chk_fifonafe_completo;

CREATE OR REPLACE FUNCTION fn_038_validar_fifonafe_completo()
RETURNS TRIGGER LANGUAGE plpgsql AS $fn$
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
$fn$;

DO $existing$
BEGIN
  IF EXISTS(
    SELECT 1 FROM tramite_fifonafe t
    WHERE t.activo AND t.estatus='completo'
      AND 4<>(SELECT count(DISTINCT c.codigo)
        FROM tramite_fifonafe_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento
        WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.activo
          AND c.tipo_catalogo='tipo_evento_fifonafe'
          AND c.codigo IN('oficio_fifonafe_dgaopr','oficio_dgaopr_representacion',
            'respuesta_representacion_dgaopr','respuesta_dgaopr_fifonafe')
          AND NULLIF(btrim(e.numero_oficio),'') IS NOT NULL AND e.fecha_oficio IS NOT NULL)
  ) THEN
    RAISE EXCEPTION '038 encontro FIFONAFE completo sin cuatro eventos canonicos';
  END IF;
END;
$existing$;

CREATE CONSTRAINT TRIGGER ctr_038_fifonafe_completo_parent
AFTER INSERT OR UPDATE ON tramite_fifonafe
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION fn_038_validar_fifonafe_completo();
CREATE CONSTRAINT TRIGGER ctr_038_fifonafe_completo_evento
AFTER INSERT OR UPDATE ON tramite_fifonafe_evento
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION fn_038_validar_fifonafe_completo();

-- Comentarios de compatibilidad.
COMMENT ON COLUMN asamblea.fecha_expedicion_primera IS 'LEGACY READ-ONLY 038: asamblea_convocatoria ordinal 1.';
COMMENT ON COLUMN asamblea.fecha_programada_primera IS 'LEGACY READ-ONLY 038: asamblea_convocatoria ordinal 1.';
COMMENT ON COLUMN asamblea.fecha_expedicion_segunda IS 'LEGACY READ-ONLY 038: asamblea_convocatoria ordinal 2.';
COMMENT ON COLUMN asamblea.fecha_programada_segunda IS 'LEGACY READ-ONLY 038: asamblea_convocatoria ordinal 2.';
COMMENT ON COLUMN asamblea.fecha_realizada IS 'LEGACY READ-ONLY 038: resumen de asamblea_convocatoria.';
COMMENT ON COLUMN asamblea.fecha_programada_ingreso_ran IS 'LEGACY READ-ONLY 038: TramiteRAN mas reciente.';
COMMENT ON COLUMN asamblea.fecha_ingreso_ran IS 'LEGACY READ-ONLY 038: tramite_ran_evento.';
COMMENT ON COLUMN asamblea.numero_solicitud_ran IS 'LEGACY READ-ONLY 038: tramite_ran_evento.';
COMMENT ON COLUMN asamblea.calificacion_registral_ran IS 'LEGACY READ-ONLY 038: tramite_ran_evento.';
COMMENT ON COLUMN asamblea.fecha_inscripcion_ran IS 'LEGACY READ-ONLY 038: tramite_ran_evento.';
COMMENT ON COLUMN convenio.fecha_programada_ingreso_ran IS 'LEGACY READ-ONLY 038: TramiteRAN mas reciente.';
COMMENT ON COLUMN convenio.ingreso_ran_fecha IS 'LEGACY READ-ONLY 038: tramite_ran_evento.';
COMMENT ON COLUMN convenio.numero_solicitud_ingreso IS 'LEGACY READ-ONLY 038: tramite_ran_evento.';
COMMENT ON COLUMN convenio.calificacion_registral IS 'LEGACY READ-ONLY 038: tramite_ran_evento.';
COMMENT ON COLUMN convenio.fecha_inscripcion_ran IS 'LEGACY READ-ONLY 038: tramite_ran_evento.';
COMMENT ON COLUMN orv.fecha_inscripcion_acta_ran IS 'Resumen legacy de TramiteRAN ORV desde 038.';
COMMENT ON COLUMN tramite_fifonafe.no_oficio_fifonafe_a_dgaopr IS 'LEGACY READ-ONLY 038: tramite_fifonafe_evento.';
COMMENT ON COLUMN tramite_fifonafe.no_oficio_dgaopr_a_representacion IS 'LEGACY READ-ONLY 038: tramite_fifonafe_evento.';
COMMENT ON COLUMN tramite_fifonafe.no_oficio_respuesta_representacion_a_dgaopr IS 'LEGACY READ-ONLY 038: tramite_fifonafe_evento.';
COMMENT ON COLUMN tramite_fifonafe.no_oficio_respuesta_dgaopr_a_fifonafe IS 'LEGACY READ-ONLY 038: tramite_fifonafe_evento.';

REVOKE DELETE,TRUNCATE,REFERENCES,TRIGGER
ON tramite_ran,tramite_ran_evento,asamblea,asamblea_convocatoria,convenio,
   tramite_fifonafe,tramite_fifonafe_evento
FROM software_pa_app;
REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON schema_migrations FROM software_pa_app;

INSERT INTO schema_migrations(version,descripcion) VALUES
('038','Cierre legacy Asamblea/RAN/FIFONAFE, TramiteRAN 1:N y ORV por NucleoAgrario');
COMMIT;
