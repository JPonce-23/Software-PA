-- RBAC vigente: geógrafos gestionan proyectos activos sin asignación.
-- No modifica registros, geometrías, decisiones históricas ni permisos SQL.
SET search_path = public, pg_catalog;
SELECT pg_advisory_xact_lock(hashtextextended('software-pa:030:rbac-gis-revisiones', 0));
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM schema_migrations WHERE version='029'
        AND nombre='diagnosticos_conciliacion_gis' AND checksum_sha256='284f8a26fc5d1215f21055657a5171431d1df4ee8d0151dc58071e38731e9716') THEN
        RAISE EXCEPTION '030 requiere 029 canónica exacta';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migrations WHERE version='030') THEN
        RAISE EXCEPTION '030 ya se encuentra registrada';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid='revision_cambio_gis_decision'::regclass
        AND tgname='trg_gis_revision_decision_contexto' AND tgenabled='O') THEN
        RAISE EXCEPTION '030 requiere el trigger de autorización de decisiones GIS';
    END IF;
END $$;

CREATE OR REPLACE FUNCTION fn_gis_revision_decision_contexto() RETURNS trigger LANGUAGE plpgsql AS $$
 DECLARE r revision_cambio_gis%ROWTYPE; e seguimiento_evento%ROWTYPE; v_actor integer;
 BEGIN
 v_actor:=NULLIF(current_setting('app.current_user_id',true),'')::integer;
 IF NEW.creado_por IS DISTINCT FROM v_actor OR NOT EXISTS(SELECT 1 FROM usuario WHERE id_usuario=v_actor AND activo AND rol IN('admin','geografo'))
 THEN RAISE EXCEPTION 'Decisión GIS requiere admin o geografo'; END IF;
 -- SELECT FOR UPDATE requiere privilegio UPDATE incluso si sólo se quiere
 -- bloquear. Usar lock transaccional de revisión conserva permisos append-only.
 PERFORM pg_advisory_xact_lock(hashtextextended('software-pa:revision-gis:'||NEW.id_revision,0));
 SELECT * INTO r FROM revision_cambio_gis WHERE id_revision=NEW.id_revision;
 IF NOT EXISTS(SELECT 1 FROM proyecto p JOIN usuario u ON u.id_usuario=v_actor
  WHERE p.id_proyecto=r.id_proyecto AND p.activo AND u.activo
  AND u.rol IN ('admin','geografo'))
 THEN RAISE EXCEPTION 'Proyecto fuera del alcance autorizado de la decisión GIS'; END IF;
 IF NEW.id_seguimiento_evento IS NOT NULL THEN
  SELECT * INTO e FROM seguimiento_evento WHERE id_seguimiento_evento=NEW.id_seguimiento_evento AND activo FOR SHARE;
  IF e.id_seguimiento_evento IS NULL OR NOT EXISTS(SELECT 1 FROM proyecto_nucleo WHERE id_proyecto_nucleo=e.id_proyecto_nucleo AND id_proyecto=r.id_proyecto)
  OR (r.id_proyecto_nucleo IS NOT NULL AND e.id_proyecto_nucleo<>r.id_proyecto_nucleo)
  OR (e.entidad_tipo IS NOT NULL AND NOT (
    (e.entidad_tipo='proyecto_nucleo' AND e.entidad_id=r.id_proyecto_nucleo)
    OR (e.entidad_tipo='parcela' AND e.entidad_id=r.id_parcela)))
  THEN RAISE EXCEPTION 'Evento incompatible con la revisión'; END IF;
 END IF;
 RETURN NEW;
END $$;
