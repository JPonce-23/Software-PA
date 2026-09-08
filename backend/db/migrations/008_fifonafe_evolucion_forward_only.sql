-- CANDIDATO NO EJECUTADO — Bloque 6 FIFONAFE.
-- Evolución forward-only sobre 001-007. El runner registra el ledger.
SET search_path = public, pg_catalog;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM schema_migrations
    WHERE version='007' AND checksum_sha256='adabd7775fb8165a1db8be04a93e7971fe207e745b410c57eb6fc76cc3a7e4f7'
  ) THEN RAISE EXCEPTION '008 requiere la migración 007 exacta'; END IF;
  IF EXISTS (SELECT 1 FROM schema_migrations WHERE version='008') THEN
    RAISE EXCEPTION '008 ya se encuentra registrada';
  END IF;
  IF to_regclass('public.tramite_fifonafe') IS NULL
     OR to_regclass('public.tramite_fifonafe_evento') IS NULL
     OR to_regclass('public.vw_hito_seguimiento') IS NULL THEN
    RAISE EXCEPTION '008 requiere el esquema FIFONAFE y reporting efectivos de 007';
  END IF;
END $$;

SELECT pg_advisory_xact_lock(hashtextextended('software-pa:008:fifonafe',0));

-- DEFAULT 1 materializa el significado legado sin UPDATE, sin disparar auditoría
-- ni reinterpretar estatus, conflictos, fechas o eventos. Tras añadir la columna,
-- el default cambia a 2 exclusivamente para solicitudes nuevas.
ALTER TABLE tramite_fifonafe
  ADD COLUMN referencia_expediente varchar(200),
  ADD COLUMN version_flujo smallint NOT NULL DEFAULT 1,
  ADD COLUMN id_asamblea_retiro integer;
ALTER TABLE tramite_fifonafe ALTER COLUMN version_flujo SET DEFAULT 2;
ALTER TABLE tramite_fifonafe
  ADD CONSTRAINT chk_fifonafe_version_flujo_008 CHECK (version_flujo IN (1,2)),
  ADD CONSTRAINT chk_fifonafe_referencia_008 CHECK
    (referencia_expediente IS NULL OR nullif(btrim(referencia_expediente),'') IS NOT NULL),
  ADD CONSTRAINT fk_fifonafe_asamblea_retiro_008 FOREIGN KEY (id_asamblea_retiro)
    REFERENCES asamblea(id_asamblea);

COMMENT ON COLUMN tramite_fifonafe.referencia_expediente IS
  'Referencia literal nullable; no es clave única y no autoriza deduplicación por texto.';
COMMENT ON COLUMN tramite_fifonafe.version_flujo IS
  '1 conserva el contrato histórico; 2 aplica hitos y evidencia del flujo 008. No editable por API.';
COMMENT ON COLUMN tramite_fifonafe.id_asamblea_retiro IS
  'Asamblea colectiva de retiro acreditada; debe pertenecer al mismo ProyectoNucleo y tener tipo/contexto retiro_fondos.';

ALTER TABLE tramite_fifonafe_evento
  ADD COLUMN ciclo_consulta integer,
  ADD COLUMN fecha_evento date,
  ADD COLUMN conflicto_impide_retiro boolean;
ALTER TABLE tramite_fifonafe_evento
  ADD CONSTRAINT chk_evento_fifonafe_ciclo_008 CHECK
    (ciclo_consulta IS NULL OR ciclo_consulta > 0);
ALTER TABLE tramite_fifonafe_evento DROP CONSTRAINT chk_evento_fifonafe_dato;
ALTER TABLE tramite_fifonafe_evento ADD CONSTRAINT chk_evento_fifonafe_dato CHECK (
  nullif(btrim(numero_oficio),'') IS NOT NULL OR fecha_oficio IS NOT NULL
  OR fecha_evento IS NOT NULL OR id_documento IS NOT NULL
  OR nullif(btrim(observaciones),'') IS NOT NULL
);
COMMENT ON COLUMN tramite_fifonafe_evento.ciclo_consulta IS
  'Ronda positiva cuando se conoce; NULL conserva eventos pendientes de conciliación.';
COMMENT ON COLUMN tramite_fifonafe_evento.fecha_evento IS
  'Fecha de negocio para actuaciones que no son oficio; no sustituye fecha_oficio.';
COMMENT ON COLUMN tramite_fifonafe_evento.conflicto_impide_retiro IS
  'Alcance acreditado de la respuesta: NULL no determinado; independiente de hay_conflictos.';

-- Los catálogos agregan hitos, no una secuencia universal.
-- El runner no representa a una persona usuaria. Se suspende únicamente la
-- auditoría de catálogo durante este seed de esquema; los triggers de
-- integridad permanecen habilitados y la auditoría se repone inmediatamente.
ALTER TABLE catalogo_operativo DISABLE TRIGGER trg_audit_catalogo_operativo;
INSERT INTO catalogo_operativo(tipo_catalogo,codigo,nombre,descripcion,orden,fuente,vigencia_inicio,activo)
SELECT 'tipo_evento_fifonafe',v.codigo,v.nombre,v.descripcion,v.orden,
       'Manual de Procedimientos de Fondos Comunes FIFONAFE',DATE '2024-08-07',true
FROM (VALUES
 ('solicitud_retiro_colectivo','Solicitud de retiro colectivo recibida','Recepción acreditada de solicitud colectiva.',110),
 ('consulta_conflictos_enviada','Consulta de conflictos enviada','Consulta directa de una ronda; no equivale a conclusión.',120),
 ('respuesta_conflictos_acreditada','Respuesta de conflictos acreditada','Respuesta soportada con alcance sobre impedimento.',130),
 ('resolucion_retiro_autorizada','Resolución/autorización positiva','Resolución positiva acreditada; no equivale a entrega.',140),
 ('cancelacion_retiro','Cancelación expresa','Cancelación acreditada de la solicitud.',150),
 ('diferimiento_retiro','Diferimiento','Diferimiento documentado; permanece pendiente.',160),
 ('entrega_recursos','Entrega de recursos acreditada','Entrega acreditada; no crea Pago ni Indemnización.',170),
 ('comprobacion_entrega','Comprobación de recursos acreditada','Comprobación de la entrega.',180),
 ('requerimiento_judicial','Requerimiento judicial','Requerimiento de la vía judicial excepcional.',190),
 ('cumplimiento_judicial','Cumplimiento judicial acreditado','Cumplimiento documentado de la vía judicial.',200),
 ('dispensa_consulta_acreditada','Excepción de consulta acreditada','Soporte que permite omitir la consulta ordinaria.',210)
) AS v(codigo,nombre,descripcion,orden)
WHERE NOT EXISTS (
  SELECT 1 FROM catalogo_operativo c
  WHERE c.tipo_catalogo='tipo_evento_fifonafe' AND c.codigo=v.codigo
);
DO $$
BEGIN
 IF (SELECT count(*) FROM catalogo_operativo WHERE tipo_catalogo='tipo_evento_fifonafe'
     AND codigo IN ('solicitud_retiro_colectivo','consulta_conflictos_enviada',
      'respuesta_conflictos_acreditada','resolucion_retiro_autorizada','cancelacion_retiro',
      'diferimiento_retiro','entrega_recursos','comprobacion_entrega','requerimiento_judicial',
      'cumplimiento_judicial','dispensa_consulta_acreditada') AND activo)=11 THEN NULL;
 ELSE RAISE EXCEPTION 'Catálogo FIFONAFE 008 ausente, duplicado o inactivo'; END IF;
END $$;
ALTER TABLE catalogo_operativo ENABLE TRIGGER trg_audit_catalogo_operativo;

ALTER TABLE requisito_documental DISABLE TRIGGER trg_audit_requisito_documental;
INSERT INTO requisito_documental(codigo,nombre,descripcion,contexto,obligatorio,orden,fuente,vigencia_inicio,activo)
SELECT v.codigo,v.nombre,v.descripcion,'fifonafe',false,v.orden,
       'Manual de Procedimientos de Fondos Comunes FIFONAFE',DATE '2024-08-07',true
FROM (VALUES
 ('fif_solicitud_retiro_colectivo','Solicitud colectiva de retiro','Soporte de recepción de la solicitud colectiva.',410),
 ('fif_respuesta_conflictos','Respuesta de conflictos','Respuesta u opinión con alcance acreditable.',420),
 ('fif_resolucion_retiro','Resolución o autorización de retiro','Soporte de resolución positiva.',430),
 ('fif_cancelacion_retiro','Cancelación de retiro','Soporte de cancelación expresa.',440),
 ('fif_entrega_recursos','Entrega de recursos','Soporte de entrega de recursos; no equivale a comprobación.',450),
 ('fif_comprobacion_entrega','Comprobación de entrega','Soporte de comprobación posterior a la entrega.',460),
 ('fif_requerimiento_judicial','Requerimiento judicial','Requerimiento de autoridad judicial competente.',470),
 ('fif_cumplimiento_judicial','Cumplimiento judicial','Constancia de cumplimiento judicial.',480),
 ('fif_acreditacion_interviniente','Acreditación de interviniente','Documento de representación o designación aplicable.',490)
) AS v(codigo,nombre,descripcion,orden)
WHERE NOT EXISTS (SELECT 1 FROM requisito_documental r WHERE r.codigo=v.codigo);
ALTER TABLE requisito_documental ENABLE TRIGGER trg_audit_requisito_documental;

CREATE TABLE tramite_fifonafe_interviniente (
  id_interviniente_fifonafe integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  id_tramite_fifonafe integer NOT NULL REFERENCES tramite_fifonafe(id_tramite_fifonafe),
  id_persona integer NOT NULL REFERENCES persona(id_persona),
  rol varchar(30) NOT NULL,
  id_evento_fifonafe bigint REFERENCES tramite_fifonafe_evento(id_evento_fifonafe),
  id_orv_integrante integer REFERENCES orv_integrante(id_orv_integrante),
  activo boolean NOT NULL DEFAULT true,
  creado_en timestamptz NOT NULL DEFAULT now(), creado_por integer REFERENCES usuario(id_usuario),
  actualizado_en timestamptz, actualizado_por integer REFERENCES usuario(id_usuario),
  fecha_baja timestamptz, id_usuario_baja integer REFERENCES usuario(id_usuario),
  motivo_baja text, observaciones text,
  CONSTRAINT chk_fif_interviniente_rol_008 CHECK
    (rol IN ('solicitante','representante','titular','beneficiario','receptor_designado')),
  CONSTRAINT chk_fif_interviniente_baja_008 CHECK (
    (activo AND fecha_baja IS NULL AND id_usuario_baja IS NULL AND motivo_baja IS NULL)
    OR (NOT activo AND fecha_baja IS NOT NULL AND id_usuario_baja IS NOT NULL
        AND nullif(btrim(motivo_baja),'') IS NOT NULL)
  )
);
CREATE UNIQUE INDEX uq_fif_interviniente_activo_008
  ON tramite_fifonafe_interviniente
  (id_tramite_fifonafe,id_persona,rol,coalesce(id_evento_fifonafe,0)) WHERE activo;
COMMENT ON TABLE tramite_fifonafe_interviniente IS
  'Participación en la solicitud; no crea beneficiarios de pago ni movimientos financieros.';

CREATE OR REPLACE FUNCTION fn_validar_fifonafe_asamblea_008() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.id_asamblea_retiro IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM asamblea a
    JOIN catalogo_operativo ta ON ta.id_catalogo_opcion=a.id_tipo_asamblea
    LEFT JOIN catalogo_operativo ca ON ca.id_catalogo_opcion=a.id_contexto_asamblea
    WHERE a.id_asamblea=NEW.id_asamblea_retiro AND a.activo
      AND a.id_proyecto_nucleo=NEW.id_proyecto_nucleo
      AND NEW.ambito='colectivo'
      AND (ta.codigo='retiro_fondos' OR ca.codigo='retiro_fondos')
  ) THEN RAISE EXCEPTION 'Asamblea de retiro ajena, inactiva, no colectiva o de contexto incompatible'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_validar_fifonafe_asamblea_008
BEFORE INSERT OR UPDATE OF id_asamblea_retiro,id_proyecto_nucleo,ambito ON tramite_fifonafe
FOR EACH ROW EXECUTE FUNCTION fn_validar_fifonafe_asamblea_008();

CREATE OR REPLACE FUNCTION fn_fifonafe_identidad_008() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.id_proyecto_nucleo IS DISTINCT FROM NEW.id_proyecto_nucleo
     OR OLD.ambito IS DISTINCT FROM NEW.ambito
     OR OLD.version_flujo IS DISTINCT FROM NEW.version_flujo THEN
    RAISE EXCEPTION 'Identidad y version_flujo FIFONAFE son inmutables';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_fifonafe_identidad_008 BEFORE UPDATE ON tramite_fifonafe
FOR EACH ROW EXECUTE FUNCTION fn_fifonafe_identidad_008();

CREATE OR REPLACE FUNCTION fn_fifonafe_evento_identidad_008() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.id_tramite_fifonafe IS DISTINCT FROM NEW.id_tramite_fifonafe
    OR OLD.ordinal IS DISTINCT FROM NEW.ordinal THEN
  RAISE EXCEPTION 'Trámite y ordinal del evento FIFONAFE son inmutables; use baja lógica y alta nueva';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER trg_fifonafe_evento_identidad_008
BEFORE UPDATE ON tramite_fifonafe_evento FOR EACH ROW
EXECUTE FUNCTION fn_fifonafe_evento_identidad_008();

CREATE OR REPLACE FUNCTION fn_validar_fifonafe_interviniente_008() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE v_fecha date;
BEGIN
  IF TG_OP='UPDATE' AND (OLD.id_tramite_fifonafe,OLD.id_persona,OLD.rol,OLD.id_evento_fifonafe)
       IS DISTINCT FROM (NEW.id_tramite_fifonafe,NEW.id_persona,NEW.rol,NEW.id_evento_fifonafe) THEN
    RAISE EXCEPTION 'Identidad del interviniente inmutable; use baja lógica y alta nueva';
  END IF;
  IF NEW.activo AND NOT EXISTS (SELECT 1 FROM persona WHERE id_persona=NEW.id_persona AND activo) THEN
    RAISE EXCEPTION 'Persona inexistente o inactiva';
  END IF;
  IF NEW.id_evento_fifonafe IS NOT NULL THEN
    SELECT coalesce(e.fecha_evento,e.fecha_oficio) INTO v_fecha
    FROM tramite_fifonafe_evento e
    WHERE e.id_evento_fifonafe=NEW.id_evento_fifonafe AND e.activo
      AND e.id_tramite_fifonafe=NEW.id_tramite_fifonafe;
    IF NOT FOUND THEN RAISE EXCEPTION 'Evento ajeno o inactivo'; END IF;
  END IF;
  IF NEW.id_orv_integrante IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM orv_integrante oi JOIN orv o ON o.id_orv=oi.id_orv
    JOIN proyecto_nucleo pn ON pn.id_nucleo=o.id_nucleo
    WHERE oi.id_orv_integrante=NEW.id_orv_integrante AND oi.activo AND o.activo
      AND oi.id_persona=NEW.id_persona
      AND pn.id_proyecto_nucleo=(SELECT id_proyecto_nucleo FROM tramite_fifonafe
                                 WHERE id_tramite_fifonafe=NEW.id_tramite_fifonafe)
      AND (v_fecha IS NULL OR ((oi.fecha_inicio IS NULL OR oi.fecha_inicio<=v_fecha)
            AND (oi.fecha_fin IS NULL OR oi.fecha_fin>=v_fecha)))
  ) THEN RAISE EXCEPTION 'Integrante ORV no acredita persona, nucleo o vigencia a la fecha del acto'; END IF;
  IF NEW.id_orv_integrante IS NOT NULL AND
     (NEW.id_evento_fifonafe IS NULL OR v_fecha IS NULL) THEN
    RAISE EXCEPTION 'La representación ORV histórica requiere un acto FIFONAFE con fecha de negocio';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_validar_fifonafe_interviniente_008
BEFORE INSERT OR UPDATE ON tramite_fifonafe_interviniente
FOR EACH ROW EXECUTE FUNCTION fn_validar_fifonafe_interviniente_008();
CREATE TRIGGER trg_audit_tramite_fifonafe_interviniente_008
AFTER INSERT OR UPDATE ON tramite_fifonafe_interviniente
FOR EACH ROW EXECUTE FUNCTION fn_audit_log('id_interviniente_fifonafe');

-- Amplía exclusivamente los objetivos polimórficos necesarios.
ALTER TABLE documento_vinculo DROP CONSTRAINT chk_documento_vinculo_tipo;
ALTER TABLE documento_vinculo ADD CONSTRAINT chk_documento_vinculo_tipo CHECK (entidad_tipo IN (
 'proyecto_nucleo','nucleo_agrario','orv','padron_historial','parcela','parcela_titular','afectacion',
 'unidad_agraria','unidad_agraria_titular','afectacion_unidad_agraria','asamblea','asamblea_convocatoria',
 'convenio','convenio_compareciente','tramite_ran','tramite_ran_evento','tramite_fifonafe',
 'tramite_fifonafe_evento','tramite_fifonafe_interviniente','indemnizacion','pago','expediente_requisito'
));
ALTER TABLE expediente_requisito DROP CONSTRAINT chk_expediente_requisito_objetivo;
ALTER TABLE expediente_requisito ADD CONSTRAINT chk_expediente_requisito_objetivo CHECK (entidad_tipo IN (
 'proyecto_nucleo','afectacion','parcela','parcela_titular','unidad_agraria','unidad_agraria_titular',
 'convenio','convenio_compareciente','tramite_ran','tramite_ran_evento','tramite_fifonafe',
 'tramite_fifonafe_evento','tramite_fifonafe_interviniente','indemnizacion','pago','orv','padron_historial',
 'actividad_campo','asamblea','asamblea_convocatoria'
));

CREATE OR REPLACE FUNCTION fn_objetivo_controlado_existe(p_tipo text,p_id bigint) RETURNS boolean
LANGUAGE plpgsql STABLE AS $$
DECLARE v_pk text; v_exists boolean;
BEGIN
 v_pk := CASE p_tipo
  WHEN 'proyecto' THEN 'id_proyecto' WHEN 'proyecto_nucleo' THEN 'id_proyecto_nucleo'
  WHEN 'proyecto_nucleo_referencia' THEN 'id_referencia' WHEN 'proyecto_nucleo_responsable' THEN 'id_responsable'
  WHEN 'nucleo_agrario' THEN 'id_nucleo' WHEN 'persona' THEN 'id_persona' WHEN 'orv' THEN 'id_orv'
  WHEN 'orv_integrante' THEN 'id_orv_integrante' WHEN 'padron_historial' THEN 'id_padron'
  WHEN 'parcela' THEN 'id_parcela' WHEN 'parcela_titular' THEN 'id_parcela_titular'
  WHEN 'actividad_campo' THEN 'id_actividad' WHEN 'afectacion' THEN 'id_afectacion'
  WHEN 'unidad_agraria' THEN 'id_unidad_agraria' WHEN 'unidad_agraria_titular' THEN 'id_unidad_titular'
  WHEN 'afectacion_unidad_agraria' THEN 'id_afectacion_unidad' WHEN 'asamblea' THEN 'id_asamblea'
  WHEN 'asamblea_convocatoria' THEN 'id_convocatoria' WHEN 'convenio' THEN 'id_convenio'
  WHEN 'convenio_compareciente' THEN 'id_compareciente' WHEN 'tramite_ran' THEN 'id_tramite_ran'
  WHEN 'tramite_ran_evento' THEN 'id_evento_ran' WHEN 'tramite_fifonafe' THEN 'id_tramite_fifonafe'
  WHEN 'tramite_fifonafe_evento' THEN 'id_evento_fifonafe'
  WHEN 'tramite_fifonafe_interviniente' THEN 'id_interviniente_fifonafe'
  WHEN 'indemnizacion' THEN 'id_indemnizacion' WHEN 'pago' THEN 'id_pago'
  WHEN 'documento' THEN 'id_documento' WHEN 'expediente_requisito' THEN 'id_expediente_requisito'
  WHEN 'importacion_tabular' THEN 'id_importacion_tabular' ELSE NULL END;
 IF v_pk IS NULL OR to_regclass('public.'||p_tipo) IS NULL THEN RETURN false; END IF;
 EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I WHERE %I=$1)',p_tipo,v_pk) INTO v_exists USING p_id;
 RETURN v_exists;
END $$;

CREATE OR REPLACE FUNCTION fn_objetivo_requisito_en_pn(p_tipo text,p_id bigint,p_pn integer)
RETURNS boolean LANGUAGE plpgsql STABLE AS $$
BEGIN
 CASE p_tipo
 WHEN 'orv' THEN RETURN EXISTS(SELECT 1 FROM orv o JOIN proyecto_nucleo pn ON pn.id_nucleo=o.id_nucleo WHERE o.id_orv=p_id AND pn.id_proyecto_nucleo=p_pn AND o.activo AND pn.activo);
 WHEN 'padron_historial' THEN RETURN EXISTS(SELECT 1 FROM padron_historial ph JOIN proyecto_nucleo pn ON pn.id_nucleo=ph.id_nucleo WHERE ph.id_padron=p_id AND pn.id_proyecto_nucleo=p_pn AND ph.activo AND pn.activo);
 WHEN 'actividad_campo' THEN RETURN EXISTS(SELECT 1 FROM actividad_campo a WHERE a.id_actividad=p_id AND a.id_proyecto_nucleo=p_pn AND a.activo);
 WHEN 'asamblea' THEN RETURN EXISTS(SELECT 1 FROM asamblea a WHERE a.id_asamblea=p_id AND a.id_proyecto_nucleo=p_pn AND a.activo);
 WHEN 'asamblea_convocatoria' THEN RETURN EXISTS(SELECT 1 FROM asamblea_convocatoria ac JOIN asamblea a USING(id_asamblea) WHERE ac.id_convocatoria=p_id AND a.id_proyecto_nucleo=p_pn AND ac.activo AND a.activo);
 WHEN 'tramite_fifonafe_interviniente' THEN RETURN EXISTS(SELECT 1 FROM tramite_fifonafe_interviniente i JOIN tramite_fifonafe t USING(id_tramite_fifonafe) WHERE i.id_interviniente_fifonafe=p_id AND t.id_proyecto_nucleo=p_pn AND i.activo AND t.activo);
 ELSE RETURN public.fn_objetivo_requisito_en_pn_001(p_tipo,p_id,p_pn);
 END CASE;
END $$;

CREATE OR REPLACE FUNCTION fn_fifonafe_evento_documentado_008(p_evento bigint)
RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT EXISTS(
  SELECT 1 FROM tramite_fifonafe_evento e JOIN documento d ON d.id_documento=e.id_documento
  WHERE e.id_evento_fifonafe=p_evento AND e.activo AND d.activo AND d.estado='disponible'
  UNION ALL
  SELECT 1 FROM documento_vinculo dv JOIN documento d USING(id_documento)
  WHERE dv.entidad_tipo='tramite_fifonafe_evento' AND dv.entidad_id=p_evento
    AND dv.activo AND d.activo AND d.estado='disponible'
 )
$$;

CREATE OR REPLACE FUNCTION fn_fifonafe_asamblea_retiro_acreditada_008(p_tramite integer)
RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT EXISTS(
  SELECT 1 FROM tramite_fifonafe t
  JOIN asamblea a ON a.id_asamblea=t.id_asamblea_retiro AND a.activo
  JOIN catalogo_operativo ta ON ta.id_catalogo_opcion=a.id_tipo_asamblea
  LEFT JOIN catalogo_operativo ca ON ca.id_catalogo_opcion=a.id_contexto_asamblea
  WHERE t.id_tramite_fifonafe=p_tramite AND t.activo AND t.ambito='colectivo'
    AND a.id_proyecto_nucleo=t.id_proyecto_nucleo
    AND (ta.codigo='retiro_fondos' OR ca.codigo='retiro_fondos')
    AND EXISTS (
      SELECT 1 FROM asamblea_convocatoria ac
      JOIN catalogo_operativo r ON r.id_catalogo_opcion=ac.id_resultado
      WHERE ac.id_asamblea=a.id_asamblea AND ac.activo
        AND r.codigo='celebrada' AND ac.fecha_realizacion IS NOT NULL
    )
    AND EXISTS (
      SELECT 1 FROM documento_vinculo dv JOIN documento d USING(id_documento)
      WHERE dv.entidad_tipo='asamblea' AND dv.entidad_id=a.id_asamblea
        AND dv.activo AND d.activo AND d.estado='disponible'
    )
 )
$$;

CREATE OR REPLACE FUNCTION fn_validar_fifonafe_evento_v2_008() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE v_codigo text; v_version smallint; v_pn integer;
BEGIN
 SELECT c.codigo,t.version_flujo,t.id_proyecto_nucleo INTO v_codigo,v_version,v_pn
 FROM catalogo_operativo c CROSS JOIN tramite_fifonafe t
 WHERE c.id_catalogo_opcion=NEW.id_tipo_evento AND c.tipo_catalogo='tipo_evento_fifonafe'
   AND t.id_tramite_fifonafe=NEW.id_tramite_fifonafe;
 IF v_codigo IS NULL THEN RAISE EXCEPTION 'Tipo de evento FIFONAFE inválido'; END IF;
 IF v_version=1 AND v_codigo IN (
   'solicitud_retiro_colectivo','consulta_conflictos_enviada',
   'respuesta_conflictos_acreditada','resolucion_retiro_autorizada',
   'cancelacion_retiro','diferimiento_retiro','entrega_recursos',
   'comprobacion_entrega','requerimiento_judicial','cumplimiento_judicial',
   'dispensa_consulta_acreditada'
 ) THEN RAISE EXCEPTION 'Un trámite legado no adopta eventos v2 sin migración explícita autorizada'; END IF;
 IF NEW.id_documento IS NOT NULL AND NOT EXISTS (
   SELECT 1 FROM documento d JOIN documento_vinculo dv USING(id_documento)
   WHERE d.id_documento=NEW.id_documento AND d.activo AND dv.activo
     AND fn_objetivo_requisito_en_pn(dv.entidad_tipo,dv.entidad_id,v_pn)
 ) THEN RAISE EXCEPTION 'Documento FIFONAFE inexistente, inactivo o ajeno al ProyectoNucleo'; END IF;
 IF NEW.conflicto_impide_retiro IS NOT NULL
    AND v_codigo NOT IN ('respuesta_conflictos_acreditada','respuesta_dgaopr_fifonafe') THEN
   RAISE EXCEPTION 'El impedimento sólo corresponde a una respuesta de conflictos';
 END IF;
 IF v_version=2 AND v_codigo='respuesta_conflictos_acreditada' AND
    (NEW.ciclo_consulta IS NULL OR coalesce(NEW.fecha_evento,NEW.fecha_oficio) IS NULL
     OR NEW.conflicto_impide_retiro IS NULL) THEN
   RAISE EXCEPTION 'Respuesta acreditada v2 requiere ronda, fecha y alcance del impedimento';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER trg_validar_fifonafe_evento_v2_008
BEFORE INSERT OR UPDATE ON tramite_fifonafe_evento
FOR EACH ROW EXECUTE FUNCTION fn_validar_fifonafe_evento_v2_008();

CREATE OR REPLACE FUNCTION fn_validar_fifonafe_evidencia_008() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (
  SELECT 1 FROM tramite_fifonafe_evento e JOIN tramite_fifonafe t USING(id_tramite_fifonafe)
  JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento
  WHERE e.activo AND t.activo AND t.version_flujo=2
    AND c.codigo='respuesta_conflictos_acreditada'
    AND NOT fn_fifonafe_evento_documentado_008(e.id_evento_fifonafe)
 ) THEN RAISE EXCEPTION 'Respuesta de conflictos acreditada requiere documento disponible'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER ctr_fifonafe_evidencia_evento_008
AFTER INSERT OR UPDATE ON tramite_fifonafe_evento DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION fn_validar_fifonafe_evidencia_008();
CREATE CONSTRAINT TRIGGER ctr_fifonafe_evidencia_documento_008
AFTER INSERT OR UPDATE ON documento_vinculo DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION fn_validar_fifonafe_evidencia_008();
CREATE CONSTRAINT TRIGGER ctr_fifonafe_evidencia_archivo_008
AFTER UPDATE OF estado,activo ON documento DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION fn_validar_fifonafe_evidencia_008();

-- Version 1 conserva exactamente la regla colectiva 002. Version 2 separa
-- cancelación, vía judicial y conclusión integral; nunca genera Pago.
CREATE OR REPLACE FUNCTION fn_validar_fifonafe_completo() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (SELECT 1 FROM tramite_fifonafe t WHERE t.activo AND t.version_flujo=1
  AND t.estatus='completo' AND t.ambito='colectivo' AND 4<>(SELECT count(DISTINCT c.codigo)
   FROM tramite_fifonafe_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento
   WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.activo
    AND c.codigo IN ('oficio_fifonafe_dgaopr','oficio_dgaopr_representacion','respuesta_representacion_dgaopr','respuesta_dgaopr_fifonafe')
    AND nullif(btrim(e.numero_oficio),'') IS NOT NULL AND e.fecha_oficio IS NOT NULL))
 THEN RAISE EXCEPTION 'FIFONAFE colectivo legado completo requiere cuatro eventos canonicos'; END IF;

 IF EXISTS (SELECT 1 FROM tramite_fifonafe t WHERE t.activo AND t.version_flujo=2
  AND t.estatus='cancelado' AND NOT EXISTS (
   SELECT 1 FROM tramite_fifonafe_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento
   WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.activo AND c.codigo='cancelacion_retiro'
    AND coalesce(e.fecha_evento,e.fecha_oficio) IS NOT NULL AND fn_fifonafe_evento_documentado_008(e.id_evento_fifonafe)))
 THEN RAISE EXCEPTION 'Cancelación v2 requiere evento expreso, fecha y soporte'; END IF;

 IF EXISTS (SELECT 1 FROM tramite_fifonafe t WHERE t.activo AND t.version_flujo=2
  AND t.estatus='completo' AND NOT (
   -- Ruta judicial excepcional: requerimiento y cumplimiento acreditados.
   (EXISTS (SELECT 1 FROM tramite_fifonafe_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.activo AND c.codigo='requerimiento_judicial' AND coalesce(e.fecha_evento,e.fecha_oficio) IS NOT NULL AND fn_fifonafe_evento_documentado_008(e.id_evento_fifonafe))
    AND EXISTS (SELECT 1 FROM tramite_fifonafe_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.activo AND c.codigo='cumplimiento_judicial' AND coalesce(e.fecha_evento,e.fecha_oficio) IS NOT NULL AND fn_fifonafe_evento_documentado_008(e.id_evento_fifonafe)))
   OR
   -- Ruta administrativa: resolución, entrega y comprobación; la consulta
   -- debe concluir en una ronda sin impedimento o tener dispensa acreditada.
   ((t.ambito='individual' OR fn_fifonafe_asamblea_retiro_acreditada_008(t.id_tramite_fifonafe))
    AND EXISTS (SELECT 1 FROM tramite_fifonafe_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.activo AND ((t.ambito='colectivo' AND c.codigo='solicitud_retiro_colectivo') OR (t.ambito='individual' AND c.codigo='solicitud_retiro_individual')) AND coalesce(e.fecha_evento,e.fecha_oficio) IS NOT NULL AND fn_fifonafe_evento_documentado_008(e.id_evento_fifonafe))
    AND EXISTS (SELECT 1 FROM tramite_fifonafe_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.activo AND c.codigo='resolucion_retiro_autorizada' AND coalesce(e.fecha_evento,e.fecha_oficio) IS NOT NULL AND fn_fifonafe_evento_documentado_008(e.id_evento_fifonafe))
    AND EXISTS (SELECT 1 FROM tramite_fifonafe_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.activo AND c.codigo='entrega_recursos' AND coalesce(e.fecha_evento,e.fecha_oficio) IS NOT NULL AND fn_fifonafe_evento_documentado_008(e.id_evento_fifonafe))
    AND EXISTS (SELECT 1 FROM tramite_fifonafe_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.activo AND c.codigo='comprobacion_entrega' AND coalesce(e.fecha_evento,e.fecha_oficio) IS NOT NULL AND fn_fifonafe_evento_documentado_008(e.id_evento_fifonafe))
    AND (EXISTS (SELECT 1 FROM tramite_fifonafe_evento s JOIN catalogo_operativo cs ON cs.id_catalogo_opcion=s.id_tipo_evento JOIN tramite_fifonafe_evento r ON r.id_tramite_fifonafe=s.id_tramite_fifonafe AND r.ciclo_consulta=s.ciclo_consulta AND r.activo JOIN catalogo_operativo cr ON cr.id_catalogo_opcion=r.id_tipo_evento WHERE s.id_tramite_fifonafe=t.id_tramite_fifonafe AND s.activo AND s.ciclo_consulta IS NOT NULL AND cs.codigo='consulta_conflictos_enviada' AND coalesce(s.fecha_evento,s.fecha_oficio) IS NOT NULL AND (nullif(btrim(s.numero_oficio),'') IS NOT NULL OR fn_fifonafe_evento_documentado_008(s.id_evento_fifonafe)) AND cr.codigo='respuesta_conflictos_acreditada' AND r.conflicto_impide_retiro=false AND fn_fifonafe_evento_documentado_008(r.id_evento_fifonafe))
      OR EXISTS (SELECT 1 FROM tramite_fifonafe_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.activo AND c.codigo='dispensa_consulta_acreditada' AND coalesce(e.fecha_evento,e.fecha_oficio) IS NOT NULL AND fn_fifonafe_evento_documentado_008(e.id_evento_fifonafe))))))
 THEN RAISE EXCEPTION 'FIFONAFE v2 completo requiere evidencia integral de una ruta aplicable'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER ctr_fifonafe_completo_vinculo_008
AFTER INSERT OR UPDATE ON documento_vinculo DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION fn_validar_fifonafe_completo();
CREATE CONSTRAINT TRIGGER ctr_fifonafe_completo_documento_008
AFTER UPDATE OF estado,activo ON documento DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION fn_validar_fifonafe_completo();
CREATE CONSTRAINT TRIGGER ctr_fifonafe_completo_asamblea_008
AFTER UPDATE OF activo,id_proyecto_nucleo,id_tipo_asamblea,id_contexto_asamblea ON asamblea
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION fn_validar_fifonafe_completo();
CREATE CONSTRAINT TRIGGER ctr_fifonafe_completo_convocatoria_008
AFTER INSERT OR UPDATE OF activo,fecha_realizacion,id_resultado,id_asamblea ON asamblea_convocatoria
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION fn_validar_fifonafe_completo();

-- Lecturas acreditadas, sin unir afectaciones: una solicitud nunca se multiplica N:M.
CREATE VIEW vw_fifonafe_evento_acreditado_008 AS
SELECT e.id_evento_fifonafe,e.id_tramite_fifonafe,e.ciclo_consulta,c.codigo tipo_evento,e.numero_oficio,
       coalesce(e.fecha_evento,e.fecha_oficio) fecha_negocio,e.conflicto_impide_retiro,
       fn_fifonafe_evento_documentado_008(e.id_evento_fifonafe) soporte_disponible
FROM tramite_fifonafe_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento
WHERE e.activo AND c.tipo_catalogo='tipo_evento_fifonafe';

CREATE VIEW vw_fifonafe_consulta_008 AS
SELECT t.id_tramite_fifonafe,t.id_proyecto_nucleo,t.ambito,t.hay_conflictos,r.ciclo_consulta,
 min(s.fecha_negocio) fecha_consulta_enviada,min(r.fecha_negocio) fecha_respuesta,
 bool_or(r.soporte_disponible AND r.fecha_negocio IS NOT NULL) respuesta_acreditada,
 bool_or(r.soporte_disponible AND r.fecha_negocio IS NOT NULL AND r.conflicto_impide_retiro=false) consulta_concluida_sin_impedimento,
 bool_or(r.soporte_disponible AND r.fecha_negocio IS NOT NULL AND r.conflicto_impide_retiro=true) impedimento_reportado
FROM tramite_fifonafe t
JOIN vw_fifonafe_evento_acreditado_008 r ON r.id_tramite_fifonafe=t.id_tramite_fifonafe
 AND r.tipo_evento='respuesta_conflictos_acreditada' AND r.ciclo_consulta IS NOT NULL
LEFT JOIN vw_fifonafe_evento_acreditado_008 s ON s.id_tramite_fifonafe=t.id_tramite_fifonafe
 AND s.ciclo_consulta=r.ciclo_consulta AND s.tipo_evento='consulta_conflictos_enviada'
 AND s.fecha_negocio IS NOT NULL
 AND (nullif(btrim(s.numero_oficio),'') IS NOT NULL OR s.soporte_disponible)
WHERE t.activo AND t.version_flujo=2
GROUP BY t.id_tramite_fifonafe,t.id_proyecto_nucleo,t.ambito,t.hay_conflictos,r.ciclo_consulta;
COMMENT ON VIEW vw_fifonafe_consulta_008 IS
 'Una fila por solicitud+ronda; no mezcla eventos sin ciclo ni rondas distintas.';

CREATE VIEW vw_fifonafe_hito_008 AS
WITH base AS (
 SELECT t.id_tramite_fifonafe,t.id_proyecto_nucleo,t.ambito,pn.id_proyecto,m.id_entidad,
        e.ciclo_consulta,e.tipo_evento,e.numero_oficio,e.fecha_negocio,e.soporte_disponible,
        e.conflicto_impide_retiro,t.hay_conflictos
 FROM tramite_fifonafe t JOIN proyecto_nucleo pn USING(id_proyecto_nucleo)
 JOIN nucleo_agrario n USING(id_nucleo) JOIN municipio m USING(id_municipio)
 JOIN vw_fifonafe_evento_acreditado_008 e USING(id_tramite_fifonafe)
 WHERE t.activo AND pn.activo AND t.version_flujo=2
), hitos AS (
 SELECT DISTINCT ON (id_tramite_fifonafe,indicador,coalesce(ciclo_consulta,0))
  id_proyecto,id_entidad,id_proyecto_nucleo,ambito,NULL::text tipo_cop_operativo,NULL::text tipo_convenio,
  NULL::text destino_superficie,
  'fifonafe_v2:'||id_tramite_fifonafe||':'||indicador||':'||coalesce(ciclo_consulta,0) clave_hito,
  indicador,NULL::date fecha_programada,fecha_negocio fecha_realizada,1::bigint cantidad,
  NULL::numeric superficie_ha,NULL::numeric monto
 FROM (
  SELECT b.*,
   CASE
    WHEN tipo_evento IN ('solicitud_retiro_colectivo','solicitud_retiro_individual') AND soporte_disponible THEN 'fif_solicitud_recibida'
    WHEN tipo_evento='consulta_conflictos_enviada' AND ciclo_consulta IS NOT NULL
      AND (nullif(btrim(numero_oficio),'') IS NOT NULL OR soporte_disponible) THEN 'fif_consulta_enviada'
    WHEN tipo_evento='respuesta_conflictos_acreditada' AND soporte_disponible AND ciclo_consulta IS NOT NULL THEN 'fif_respuesta_acreditada'
    WHEN tipo_evento='resolucion_retiro_autorizada' AND soporte_disponible THEN 'fif_resolucion_positiva'
    WHEN tipo_evento='cancelacion_retiro' AND soporte_disponible THEN 'fif_cancelacion'
    WHEN tipo_evento='diferimiento_retiro' AND soporte_disponible THEN 'fif_diferimiento'
    WHEN tipo_evento='entrega_recursos' AND soporte_disponible THEN 'fif_entrega'
    WHEN tipo_evento='comprobacion_entrega' AND soporte_disponible THEN 'fif_comprobacion'
    WHEN tipo_evento='cumplimiento_judicial' AND soporte_disponible THEN 'fif_cumplimiento_judicial'
   END indicador
  FROM base b WHERE fecha_negocio IS NOT NULL
 ) x WHERE indicador IS NOT NULL
 ORDER BY id_tramite_fifonafe,indicador,coalesce(ciclo_consulta,0),fecha_negocio
), consulta AS (
 SELECT pn.id_proyecto,m.id_entidad,c.id_proyecto_nucleo,c.ambito,NULL::text,NULL::text,NULL::text,
  'fifonafe_v2:'||c.id_tramite_fifonafe||':consulta:'||c.ciclo_consulta,
  'fif_consulta_concluida',NULL::date,c.fecha_respuesta,1::bigint,NULL::numeric,NULL::numeric
 FROM vw_fifonafe_consulta_008 c JOIN proyecto_nucleo pn USING(id_proyecto_nucleo)
 JOIN nucleo_agrario n USING(id_nucleo) JOIN municipio m USING(id_municipio)
 WHERE c.fecha_consulta_enviada IS NOT NULL AND c.consulta_concluida_sin_impedimento
), no_conflictos AS (
 SELECT pn.id_proyecto,m.id_entidad,c.id_proyecto_nucleo,c.ambito,NULL::text,NULL::text,NULL::text,
  'fifonafe_v2:'||c.id_tramite_fifonafe||':no_conflictos:'||c.ciclo_consulta,
  'informe_no_conflictos',NULL::date,c.fecha_respuesta,1::bigint,NULL::numeric,NULL::numeric
 FROM vw_fifonafe_consulta_008 c
 JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) JOIN nucleo_agrario n USING(id_nucleo)
 JOIN municipio m USING(id_municipio)
 WHERE c.fecha_consulta_enviada IS NOT NULL AND c.consulta_concluida_sin_impedimento
   AND c.hay_conflictos=false
)
SELECT * FROM hitos UNION ALL SELECT * FROM consulta UNION ALL SELECT * FROM no_conflictos;
COMMENT ON VIEW vw_fifonafe_hito_008 IS
 'Hitos v2 acreditados por solicitud o solicitud+ronda, sin joins N:M a afectaciones.';

-- Conserva físicamente la vista 007 y publica una envoltura compatible.
ALTER VIEW vw_hito_seguimiento RENAME TO vw_hito_seguimiento_007;
CREATE VIEW vw_hito_seguimiento AS
SELECT h.* FROM vw_hito_seguimiento_007 h
WHERE h.indicador<>'fifonafe' OR NOT EXISTS (
 SELECT 1 FROM tramite_fifonafe t
 WHERE t.version_flujo=2 AND h.clave_hito='fifonafe:'||t.id_tramite_fifonafe
)
UNION ALL SELECT * FROM vw_fifonafe_hito_008;
COMMENT ON VIEW vw_hito_seguimiento IS
 'Contrato legado 007 sin cambios más hitos FIFONAFE v2 acreditados; fifonafe histórico conserva significado.';

CREATE OR REPLACE VIEW vw_reporte_avance_periodo AS
WITH f AS (
 SELECT id_proyecto,id_entidad,ambito,tipo_cop_operativo,tipo_convenio,destino_superficie,clave_hito,indicador,fecha_programada fecha,1::bigint programado,0::bigint realizado,NULL::numeric superficie_ha,NULL::numeric monto FROM vw_hito_seguimiento WHERE fecha_programada IS NOT NULL
 UNION ALL
 SELECT id_proyecto,id_entidad,ambito,tipo_cop_operativo,tipo_convenio,destino_superficie,clave_hito,indicador,fecha_realizada,0::bigint,1::bigint,superficie_ha,monto FROM vw_hito_seguimiento WHERE fecha_realizada IS NOT NULL)
SELECT id_proyecto,id_entidad,ambito,tipo_cop_operativo,tipo_convenio,destino_superficie,
 extract(year FROM fecha)::integer anio,extract(month FROM fecha)::integer mes,extract(quarter FROM fecha)::integer trimestre,
 indicador,sum(programado)::bigint programado,sum(realizado)::bigint realizado,count(DISTINCT clave_hito)::bigint cantidad,
 sum(superficie_ha)::numeric superficie_ha,sum(monto)::numeric monto
FROM f GROUP BY id_proyecto,id_entidad,ambito,tipo_cop_operativo,tipo_convenio,destino_superficie,
 extract(year FROM fecha),extract(month FROM fecha),extract(quarter FROM fecha),indicador;
CREATE OR REPLACE VIEW vw_dashboard_kpi AS
WITH f AS (
 SELECT id_proyecto,extract(year FROM fecha_programada)::integer anio,indicador,clave_hito,1::bigint programado,0::bigint realizado,NULL::numeric superficie_ha,NULL::numeric monto FROM vw_hito_seguimiento WHERE fecha_programada IS NOT NULL
 UNION ALL
 SELECT id_proyecto,extract(year FROM fecha_realizada)::integer,indicador,clave_hito,0::bigint,1::bigint,superficie_ha,monto FROM vw_hito_seguimiento WHERE fecha_realizada IS NOT NULL)
SELECT id_proyecto,anio,indicador,sum(programado)::bigint programado,sum(realizado)::bigint realizado,
 count(DISTINCT clave_hito)::bigint cantidad,sum(superficie_ha)::numeric superficie_ha,sum(monto)::numeric monto
FROM f GROUP BY id_proyecto,anio,indicador;

CREATE VIEW vw_fifonafe_cobertura_008 AS
SELECT pn.id_proyecto,t.ambito,count(*)::bigint universo_solicitudes,
 count(*) FILTER (WHERE EXISTS (SELECT 1 FROM vw_fifonafe_evento_acreditado_008 e WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.tipo_evento IN ('solicitud_retiro_colectivo','solicitud_retiro_individual') AND e.fecha_negocio IS NOT NULL AND e.soporte_disponible))::bigint solicitudes_recibidas_acreditadas,
 count(*) FILTER (WHERE EXISTS (SELECT 1 FROM tramite_fifonafe_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.activo AND c.codigo IN ('consulta_conflictos_enviada','respuesta_conflictos_acreditada') AND e.ciclo_consulta IS NULL))::bigint eventos_consulta_sin_ciclo,
 count(*) FILTER (WHERE EXISTS (SELECT 1 FROM vw_fifonafe_evento_acreditado_008 e WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.tipo_evento='respuesta_conflictos_acreditada' AND NOT e.soporte_disponible))::bigint respuestas_sin_soporte,
 count(*) FILTER (WHERE EXISTS (SELECT 1 FROM vw_fifonafe_evento_acreditado_008 e WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.tipo_evento IN ('solicitud_retiro_colectivo','solicitud_retiro_individual','respuesta_conflictos_acreditada','resolucion_retiro_autorizada','cancelacion_retiro','diferimiento_retiro','entrega_recursos','comprobacion_entrega','requerimiento_judicial','cumplimiento_judicial','dispensa_consulta_acreditada') AND NOT e.soporte_disponible))::bigint actuaciones_sin_soporte,
 count(*) FILTER (WHERE t.estatus='completo')::bigint completos_integrales,
 count(*) FILTER (WHERE t.estatus<>'completo')::bigint pendientes_integrales
FROM tramite_fifonafe t JOIN proyecto_nucleo pn USING(id_proyecto_nucleo)
WHERE t.activo AND pn.activo AND t.version_flujo=2 GROUP BY pn.id_proyecto,t.ambito;

CREATE VIEW vw_fifonafe_indicador_institucional_008 AS
WITH recibidas AS (
 SELECT b.id_proyecto,extract(year FROM b.fecha_realizada)::integer anio,count(DISTINCT split_part(b.clave_hito,':',2)::integer)::bigint solicitudes_recibidas
 FROM vw_fifonafe_hito_008 b WHERE b.indicador='fif_solicitud_recibida' GROUP BY b.id_proyecto,extract(year FROM b.fecha_realizada)
), resueltas AS (
 SELECT b.id_proyecto,extract(year FROM b.fecha_realizada)::integer anio,count(DISTINCT split_part(b.clave_hito,':',2)::integer)::bigint solicitudes_resueltas_positivas
 FROM vw_fifonafe_hito_008 b WHERE b.indicador='fif_resolucion_positiva' GROUP BY b.id_proyecto,extract(year FROM b.fecha_realizada)
)
SELECT r.id_proyecto,r.anio,r.solicitudes_recibidas,coalesce(s.solicitudes_resueltas_positivas,0)::bigint solicitudes_resueltas_positivas,
 CASE WHEN r.solicitudes_recibidas=0 THEN NULL ELSE round(100.0*coalesce(s.solicitudes_resueltas_positivas,0)/r.solicitudes_recibidas,2) END::numeric porcentaje
FROM recibidas r LEFT JOIN resueltas s USING(id_proyecto,anio);

COMMENT ON VIEW vw_fifonafe_cobertura_008 IS
 'Cobertura v2 por solicitud; los pendientes y falta de soporte impiden presentar subtotales como total definitivo.';
COMMENT ON VIEW vw_fifonafe_indicador_institucional_008 IS
 'Contrato separado: solicitudes resueltas positivamente / solicitudes recibidas; no cuenta oficios, parcelas, entregas ni pagos.';

GRANT SELECT,INSERT,UPDATE ON tramite_fifonafe_interviniente TO software_pa_app;
GRANT USAGE,SELECT ON SEQUENCE tramite_fifonafe_interviniente_id_interviniente_fifonafe_seq TO software_pa_app;
GRANT SELECT,INSERT,UPDATE ON vw_hito_seguimiento,vw_reporte_avance_periodo,vw_dashboard_kpi TO software_pa_app;
GRANT SELECT ON vw_fifonafe_evento_acreditado_008,vw_fifonafe_consulta_008,vw_fifonafe_hito_008,
 vw_fifonafe_cobertura_008,vw_fifonafe_indicador_institucional_008 TO software_pa_app;

-- Invariantes neutrales del backfill.
DO $$
BEGIN
 IF EXISTS (SELECT 1 FROM tramite_fifonafe WHERE version_flujo<>1) THEN
  RAISE EXCEPTION 'El backfill sólo puede clasificar registros preexistentes como versión 1';
 END IF;
 IF EXISTS (SELECT 1 FROM tramite_fifonafe WHERE referencia_expediente IS NOT NULL OR id_asamblea_retiro IS NOT NULL)
    OR EXISTS (SELECT 1 FROM tramite_fifonafe_evento WHERE ciclo_consulta IS NOT NULL OR fecha_evento IS NOT NULL OR conflicto_impide_retiro IS NOT NULL)
    OR EXISTS (SELECT 1 FROM tramite_fifonafe_interviniente) THEN
  RAISE EXCEPTION '008 no debe inventar referencias, asambleas, ciclos, fechas, conflictos o intervinientes';
 END IF;
END $$;
