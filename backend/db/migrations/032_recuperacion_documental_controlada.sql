-- Proposed additive SS-12 expansion. Never apply outside authorized QA/operation.
SET search_path = public, pg_catalog;
SELECT pg_advisory_xact_lock(hashtextextended('software-pa:032:recuperacion-documental',0));
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='031'
    AND nombre='operaciones_documentales'
    AND checksum_sha256='ca02cb3c6298e2fe5cef9ff80800414c56ce1684a0fe27c5c9fb12d1ec149d35')
  THEN RAISE EXCEPTION '032 requiere 031 canonica exacta'; END IF;
  IF EXISTS (SELECT 1 FROM schema_migrations WHERE version='032')
    OR to_regclass('public.documento_coordinacion') IS NOT NULL
    OR to_regclass('public.documento_recuperacion') IS NOT NULL
  THEN RAISE EXCEPTION '032 encontro una expansion previa'; END IF;
END $$;

CREATE TABLE documento_coordinacion (
  id_operacion uuid PRIMARY KEY REFERENCES documento_operacion(id_operacion) ON DELETE RESTRICT,
  protocolo smallint NOT NULL CHECK (protocolo=1),
  identidad jsonb NOT NULL CHECK (jsonb_typeof(identidad)='object'
    AND identidad ?& ARRAY['root','directory','lock']
    AND (identidad-ARRAY['root','directory','lock'])='{}'::jsonb),
  creado_en timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE documento_recuperacion (
  id_intento uuid PRIMARY KEY,
  id_operacion uuid NOT NULL REFERENCES documento_operacion(id_operacion) ON DELETE RESTRICT,
  id_documento integer NOT NULL,
  id_usuario integer NOT NULL REFERENCES usuario(id_usuario) ON DELETE RESTRICT,
  motivo varchar(32) NOT NULL CHECK (motivo='OPERATOR_REVIEW'),
  estado varchar(16) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','confirmada','bloqueada')),
  codigo varchar(64),
  id_documento_version bigint REFERENCES documento_version(id_documento_version) ON DELETE RESTRICT,
  creado_en timestamptz NOT NULL DEFAULT clock_timestamp(),
  terminado_en timestamptz,
  CHECK ((estado='pendiente' AND codigo IS NULL AND terminado_en IS NULL AND id_documento_version IS NULL)
    OR (estado='bloqueada' AND codigo IS NOT NULL AND codigo ~ '^[A-Z0-9_]+$' AND terminado_en IS NOT NULL AND id_documento_version IS NULL)
    OR (estado='confirmada' AND codigo IS NOT NULL AND codigo IN ('RECOVERED','EXISTING_RESULT') AND terminado_en IS NOT NULL
        AND id_documento_version IS NOT NULL))
);
CREATE INDEX idx_documento_recuperacion_operacion ON documento_recuperacion(id_operacion,creado_en);

CREATE FUNCTION fn_documento_recuperacion_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=public,pg_catalog AS $$
DECLARE op documento_operacion%ROWTYPE; actor integer; value jsonb;
BEGIN
  IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Historial de recuperacion inmutable'; END IF;
  actor:=NULLIF(current_setting('app.current_user_id',true),'')::integer;
  SELECT * INTO op FROM documento_operacion WHERE id_operacion=NEW.id_operacion;
  IF NOT FOUND OR actor IS DISTINCT FROM op.id_usuario THEN
    RAISE EXCEPTION 'Recuperacion sin actor propietario'; END IF;
  IF TG_TABLE_NAME='documento_coordinacion' THEN
    IF TG_OP<>'INSERT' OR op.estado<>'pendiente' OR op.identidad_archivo IS NOT NULL THEN
      RAISE EXCEPTION 'Coordinacion solo al preparar una carga nueva'; END IF;
    FOR value IN SELECT jsonb_array_elements(jsonb_build_array(
      NEW.identidad->'root',NEW.identidad->'directory',NEW.identidad->'lock')) LOOP
      IF jsonb_typeof(value)<>'array' OR jsonb_array_length(value)<>2
        OR jsonb_typeof(value->0)<>'number' OR jsonb_typeof(value->1)<>'number'
        OR value->>0 !~ '^[0-9]+$' OR value->>1 !~ '^[1-9][0-9]*$'
      THEN RAISE EXCEPTION 'Identidad de coordinacion invalida'; END IF;
    END LOOP;
  ELSE
    IF NEW.id_usuario IS DISTINCT FROM actor OR NEW.id_documento IS DISTINCT FROM op.id_documento THEN
      RAISE EXCEPTION 'Intento fuera de su alcance'; END IF;
    IF TG_OP='INSERT' THEN
      IF NEW.estado<>'pendiente' OR NOT EXISTS(SELECT 1 FROM usuario WHERE id_usuario=actor
        AND activo AND rol IN ('admin','operador')) THEN RAISE EXCEPTION 'Intento inicial invalido'; END IF;
    ELSE
      IF OLD.estado<>'pendiente' OR ROW(NEW.id_intento,NEW.id_operacion,NEW.id_documento,NEW.id_usuario,NEW.motivo,NEW.creado_en)
        IS DISTINCT FROM ROW(OLD.id_intento,OLD.id_operacion,OLD.id_documento,OLD.id_usuario,OLD.motivo,OLD.creado_en)
      THEN RAISE EXCEPTION 'Identidad o resultado de intento inmutable'; END IF;
      IF NEW.estado='pendiente' THEN RAISE EXCEPTION 'Actualizacion sin resultado'; END IF;
    END IF;
    IF NEW.estado='confirmada' AND (op.estado<>'confirmada'
      OR NEW.id_documento_version IS DISTINCT FROM op.id_documento_version) THEN
      RAISE EXCEPTION 'Resultado sin operacion confirmada'; END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_documento_coordinacion_guard BEFORE INSERT OR UPDATE OR DELETE ON documento_coordinacion
  FOR EACH ROW EXECUTE FUNCTION fn_documento_recuperacion_guard();
CREATE TRIGGER trg_documento_recuperacion_guard BEFORE INSERT OR UPDATE OR DELETE ON documento_recuperacion
  FOR EACH ROW EXECUTE FUNCTION fn_documento_recuperacion_guard();
REVOKE ALL ON documento_coordinacion,documento_recuperacion FROM PUBLIC;
GRANT SELECT,INSERT ON documento_coordinacion TO software_pa_app;
GRANT SELECT,INSERT,UPDATE ON documento_recuperacion TO software_pa_app;
REVOKE UPDATE,DELETE,TRUNCATE ON documento_coordinacion FROM software_pa_app;
REVOKE DELETE,TRUNCATE ON documento_recuperacion FROM software_pa_app;
