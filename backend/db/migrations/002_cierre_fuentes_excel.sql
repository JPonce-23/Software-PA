-- Cierre V1 contra fuentes Excel auditadas.  La 001 es inmutable.
SET search_path = public, pg_catalog;
SELECT set_config('app.current_user_id', COALESCE((SELECT min(id_usuario)::text FROM usuario),'1'), false);

ALTER TABLE actividad_campo ADD COLUMN IF NOT EXISTS id_tipo_cop_operativo bigint;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='actividad_campo_id_tipo_cop_operativo_fkey') THEN
  ALTER TABLE actividad_campo ADD CONSTRAINT actividad_campo_id_tipo_cop_operativo_fkey FOREIGN KEY (id_tipo_cop_operativo) REFERENCES catalogo_operativo(id_catalogo_opcion);
 END IF;
END $$;
ALTER TABLE asamblea ADD COLUMN IF NOT EXISTS id_tipo_cop_operativo bigint;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='asamblea_id_tipo_cop_operativo_fkey') THEN
  ALTER TABLE asamblea ADD CONSTRAINT asamblea_id_tipo_cop_operativo_fkey FOREIGN KEY (id_tipo_cop_operativo) REFERENCES catalogo_operativo(id_catalogo_opcion);
 END IF;
END $$;

-- Una instalación limpia aún no tiene usuario de aplicación. Las opciones
-- de catálogo son datos de migración, así que se evita sólo su bitácora
-- durante estas dos inserciones; el trigger queda habilitado enseguida.
ALTER TABLE catalogo_operativo DISABLE TRIGGER trg_audit_catalogo_operativo;
INSERT INTO catalogo_operativo(tipo_catalogo,codigo,nombre,descripcion,orden,fuente)
SELECT 'tipo_cop_operativo','TRANSVERSALES','TRANSVERSALES',
       'Clasificación operativa/reportable transversal.',50,'Cierre fuentes Excel 2026'
WHERE NOT EXISTS (SELECT 1 FROM catalogo_operativo WHERE tipo_catalogo='tipo_cop_operativo' AND codigo='TRANSVERSALES');
INSERT INTO catalogo_operativo(tipo_catalogo,codigo,nombre,descripcion,orden,fuente)
SELECT 'contexto_asamblea','transversal','Transversal',
       'Contexto funcional transversal.',70,'Cierre fuentes Excel 2026'
WHERE NOT EXISTS (SELECT 1 FROM catalogo_operativo WHERE tipo_catalogo='contexto_asamblea' AND codigo='transversal');
ALTER TABLE catalogo_operativo ENABLE TRIGGER trg_audit_catalogo_operativo;

ALTER TABLE actividad_campo DROP CONSTRAINT chk_actividad_contexto;
ALTER TABLE actividad_campo ADD CONSTRAINT chk_actividad_contexto CHECK
 (contexto_actividad IN ('general','superficie_adicional','obras_complementarias','transversal','otro'));
ALTER TABLE expediente_requisito DROP CONSTRAINT chk_expediente_requisito_objetivo;
ALTER TABLE expediente_requisito ADD CONSTRAINT chk_expediente_requisito_objetivo CHECK
 (entidad_tipo IN ('proyecto_nucleo','afectacion','parcela','parcela_titular','unidad_agraria','unidad_agraria_titular','convenio','convenio_compareciente','tramite_ran','tramite_ran_evento','tramite_fifonafe','tramite_fifonafe_evento','indemnizacion','pago','orv','padron_historial','actividad_campo','asamblea','asamblea_convocatoria'));
ALTER TABLE indemnizacion DROP CONSTRAINT IF EXISTS chk_indemnizacion_estatus;
ALTER TABLE indemnizacion ADD CONSTRAINT chk_indemnizacion_estatus CHECK
 (estatus IN ('pendiente','programado','en_proceso','completo','pagado','cancelado','otro'));

CREATE OR REPLACE FUNCTION fn_validar_actividad_tipo_cop() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.id_tipo_cop_operativo IS NOT NULL AND NOT fn_opcion_catalogo_valida(NEW.id_tipo_cop_operativo,'tipo_cop_operativo') THEN
   RAISE EXCEPTION 'Tipo COP operativo de actividad invalido';
 END IF; RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION fn_validar_asamblea_catalogos() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v_tipo text; v_contexto text;
BEGIN
 IF NOT fn_opcion_catalogo_valida(NEW.id_tipo_asamblea,'tipo_asamblea')
    OR (NEW.id_contexto_asamblea IS NOT NULL AND NOT fn_opcion_catalogo_valida(NEW.id_contexto_asamblea,'contexto_asamblea'))
    OR (NEW.id_tipo_cop_operativo IS NOT NULL AND NOT fn_opcion_catalogo_valida(NEW.id_tipo_cop_operativo,'tipo_cop_operativo')) THEN
   RAISE EXCEPTION 'Tipo, contexto o tipo COP de asamblea invalido';
 END IF;
 SELECT codigo INTO v_tipo FROM catalogo_operativo WHERE id_catalogo_opcion=NEW.id_tipo_asamblea;
 SELECT codigo INTO v_contexto FROM catalogo_operativo WHERE id_catalogo_opcion=NEW.id_contexto_asamblea;
 IF (v_tipo='retiro_fondos' AND v_contexto IS DISTINCT FROM 'retiro_fondos') OR (v_tipo='anuencia' AND v_contexto='retiro_fondos') THEN RAISE EXCEPTION 'Tipo de asamblea y contexto contradictorios'; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS trg_validar_actividad_tipo_cop ON actividad_campo;
CREATE TRIGGER trg_validar_actividad_tipo_cop BEFORE INSERT OR UPDATE OF id_tipo_cop_operativo ON actividad_campo FOR EACH ROW EXECUTE FUNCTION fn_validar_actividad_tipo_cop();
DROP TRIGGER IF EXISTS trg_validar_asamblea_catalogos ON asamblea;
CREATE TRIGGER trg_validar_asamblea_catalogos BEFORE INSERT OR UPDATE OF id_tipo_asamblea,id_contexto_asamblea,id_tipo_cop_operativo ON asamblea FOR EACH ROW EXECUTE FUNCTION fn_validar_asamblea_catalogos();

-- Un flujo individual no requiere los cuatro oficios colectivos.
CREATE OR REPLACE FUNCTION fn_validar_fifonafe_completo() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (SELECT 1 FROM tramite_fifonafe t WHERE t.activo AND t.estatus='completo' AND t.ambito='colectivo' AND 4<>(SELECT count(DISTINCT c.codigo) FROM tramite_fifonafe_evento e JOIN catalogo_operativo c ON c.id_catalogo_opcion=e.id_tipo_evento WHERE e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.activo AND c.tipo_catalogo='tipo_evento_fifonafe' AND c.codigo IN ('oficio_fifonafe_dgaopr','oficio_dgaopr_representacion','respuesta_representacion_dgaopr','respuesta_dgaopr_fifonafe') AND NULLIF(btrim(e.numero_oficio),'') IS NOT NULL AND e.fecha_oficio IS NOT NULL)) THEN
   RAISE EXCEPTION 'FIFONAFE colectivo completo requiere los cuatro eventos canonicos con numero y fecha';
 END IF; RETURN NULL;
END $$;

-- Conserva la validación canónica de 001 para los objetivos preexistentes y la
-- extiende sin editar la línea base.
DO $$ BEGIN
 IF to_regprocedure('fn_objetivo_requisito_en_pn_001(text,bigint,integer)') IS NULL THEN
  ALTER FUNCTION fn_objetivo_requisito_en_pn(text,bigint,integer) RENAME TO fn_objetivo_requisito_en_pn_001;
 END IF;
END $$;
CREATE OR REPLACE FUNCTION fn_objetivo_requisito_en_pn(p_tipo text,p_id bigint,p_pn integer) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
BEGIN
 CASE p_tipo
 WHEN 'orv' THEN RETURN EXISTS(SELECT 1 FROM orv o JOIN proyecto_nucleo pn ON pn.id_nucleo=o.id_nucleo WHERE o.id_orv=p_id AND pn.id_proyecto_nucleo=p_pn AND o.activo AND pn.activo);
 WHEN 'padron_historial' THEN RETURN EXISTS(SELECT 1 FROM padron_historial ph JOIN proyecto_nucleo pn ON pn.id_nucleo=ph.id_nucleo WHERE ph.id_padron=p_id AND pn.id_proyecto_nucleo=p_pn AND ph.activo AND pn.activo);
 WHEN 'actividad_campo' THEN RETURN EXISTS(SELECT 1 FROM actividad_campo a WHERE a.id_actividad=p_id AND a.id_proyecto_nucleo=p_pn AND a.activo);
 WHEN 'asamblea' THEN RETURN EXISTS(SELECT 1 FROM asamblea a WHERE a.id_asamblea=p_id AND a.id_proyecto_nucleo=p_pn AND a.activo);
 WHEN 'asamblea_convocatoria' THEN RETURN EXISTS(SELECT 1 FROM asamblea_convocatoria ac JOIN asamblea a USING(id_asamblea) WHERE ac.id_convocatoria=p_id AND a.id_proyecto_nucleo=p_pn AND ac.activo AND a.activo);
 ELSE RETURN public.fn_objetivo_requisito_en_pn_001(p_tipo,p_id,p_pn);
 END CASE;
END $$;
DROP TRIGGER IF EXISTS trg_validar_expediente_requisito_objetivo ON expediente_requisito;
CREATE TRIGGER trg_validar_expediente_requisito_objetivo BEFORE INSERT OR UPDATE OF entidad_tipo,entidad_id,id_proyecto_nucleo ON expediente_requisito FOR EACH ROW EXECUTE FUNCTION fn_validar_expediente_requisito_objetivo();

CREATE OR REPLACE VIEW vw_convenio_tipo_cop_operativo AS
SELECT c.id_convenio,c.id_proyecto_nucleo,c.ambito,c.tipo_instrumento,c.tipo_convenio,c.consecutivo,c.id_convenio_padre,
       co.id_catalogo_opcion AS id_tipo_cop_operativo,co.codigo AS tipo_cop_operativo_codigo,co.nombre AS tipo_cop_operativo_nombre
FROM convenio c
LEFT JOIN LATERAL (
 SELECT x.* FROM catalogo_operativo x WHERE x.tipo_catalogo='tipo_cop_operativo' AND x.codigo=(
  SELECT CASE WHEN count(DISTINCT a.id_tipo_cop_operativo)=1 THEN max(x2.codigo) END
  FROM convenio_afectacion ca JOIN afectacion a ON a.id_afectacion=ca.id_afectacion AND a.activo
  JOIN catalogo_operativo x2 ON x2.id_catalogo_opcion=a.id_tipo_cop_operativo
  WHERE ca.id_convenio=c.id_convenio AND ca.activo)
) co ON true;

-- Los hitos se deduplican por entidad/ciclo en el reporte; las filas de eventos
-- se conservan completas.  No existen columnas auxiliares X.
CREATE OR REPLACE VIEW vw_dashboard_kpi AS
WITH activity AS (
 SELECT pn.id_proyecto,extract(year FROM coalesce(a.fecha_realizada,a.fecha_programada,a.creado_en::date))::integer anio,
        a.tipo_actividad||'_'||coalesce(tc.codigo,'SIN_CICLO') indicador,
        count(DISTINCT (a.id_proyecto_nucleo,coalesce(a.id_tipo_cop_operativo,0))) FILTER (WHERE a.fecha_programada IS NOT NULL)::bigint programado,
        count(DISTINCT (a.id_proyecto_nucleo,coalesce(a.id_tipo_cop_operativo,0))) FILTER (WHERE a.fecha_realizada IS NOT NULL)::bigint realizado,
        count(DISTINCT (a.id_proyecto_nucleo,coalesce(a.id_tipo_cop_operativo,0)))::bigint cantidad,NULL::numeric superficie_ha,NULL::numeric monto
 FROM actividad_campo a JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) LEFT JOIN catalogo_operativo tc ON tc.id_catalogo_opcion=a.id_tipo_cop_operativo
 WHERE a.activo AND pn.activo GROUP BY pn.id_proyecto,extract(year FROM coalesce(a.fecha_realizada,a.fecha_programada,a.creado_en::date)),a.tipo_actividad,tc.codigo
), nucleos AS (
 SELECT pn.id_proyecto,extract(year FROM pn.creado_en)::integer anio,'nucleos'::text indicador,0::bigint programado,count(*)::bigint realizado,count(*)::bigint cantidad,NULL::numeric superficie_ha,NULL::numeric monto FROM proyecto_nucleo pn WHERE pn.activo GROUP BY pn.id_proyecto,extract(year FROM pn.creado_en)
), assembly_base AS (
 SELECT a.id_asamblea,pn.id_proyecto,extract(year FROM coalesce(max(ac.fecha_realizacion),min(ac.fecha_programada),a.creado_en::date))::integer anio,
  bool_or(ac.fecha_programada IS NOT NULL) programada,bool_or(rc.codigo='celebrada') realizada
 FROM asamblea a JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) LEFT JOIN asamblea_convocatoria ac ON ac.id_asamblea=a.id_asamblea AND ac.activo LEFT JOIN catalogo_operativo rc ON rc.id_catalogo_opcion=ac.id_resultado
 WHERE a.activo AND pn.activo GROUP BY a.id_asamblea,pn.id_proyecto,a.creado_en
), assembly AS (
 SELECT id_proyecto,anio,'asambleas'::text indicador,count(*) FILTER(WHERE programada)::bigint programado,count(*) FILTER(WHERE realizada)::bigint realizado,count(*)::bigint cantidad,NULL::numeric superficie_ha,NULL::numeric monto FROM assembly_base GROUP BY id_proyecto,anio
), ran AS (
 SELECT pn.id_proyecto,extract(year FROM coalesce(max(e.fecha_evento),tr.fecha_programada_ingreso,tr.creado_en::date))::integer anio,
  'ingreso_ran_'||CASE WHEN tr.id_asamblea IS NOT NULL THEN 'acta' ELSE 'convenio' END indicador,
  CASE WHEN tr.fecha_programada_ingreso IS NOT NULL THEN 1::bigint ELSE 0::bigint END programado,
  CASE WHEN bool_or(tc.codigo IN('ingreso','reingreso')) THEN 1::bigint ELSE 0::bigint END realizado,
  CASE WHEN bool_or(tc.codigo IN('ingreso','reingreso')) THEN 1::bigint ELSE 0::bigint END cantidad,NULL::numeric superficie_ha,NULL::numeric monto
 FROM tramite_ran tr JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) LEFT JOIN tramite_ran_evento e ON e.id_tramite_ran=tr.id_tramite_ran AND e.activo LEFT JOIN catalogo_operativo tc ON tc.id_catalogo_opcion=e.id_tipo_evento WHERE tr.activo AND (tr.id_asamblea IS NOT NULL OR tr.id_convenio IS NOT NULL) GROUP BY tr.id_tramite_ran,pn.id_proyecto,tr.fecha_programada_ingreso,tr.creado_en,CASE WHEN tr.id_asamblea IS NOT NULL THEN 'acta' ELSE 'convenio' END
), convenios AS (
 SELECT pn.id_proyecto,extract(year FROM coalesce(c.fecha_firma,c.fecha_programada_firma,c.creado_en::date))::integer anio,'convenios_'||coalesce(v.tipo_cop_operativo_codigo,'REVISION') indicador,
 count(DISTINCT c.id_convenio) FILTER(WHERE c.fecha_programada_firma IS NOT NULL)::bigint programado,count(DISTINCT c.id_convenio) FILTER(WHERE c.fecha_firma IS NOT NULL)::bigint realizado,count(DISTINCT c.id_convenio)::bigint cantidad,sum(c.superficie_ha)::numeric superficie_ha,sum(c.monto_100)::numeric monto
 FROM convenio c JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) LEFT JOIN vw_convenio_tipo_cop_operativo v USING(id_convenio) WHERE c.activo AND pn.activo GROUP BY pn.id_proyecto,extract(year FROM coalesce(c.fecha_firma,c.fecha_programada_firma,c.creado_en::date)),v.tipo_cop_operativo_codigo
), parcelas AS (
 SELECT pn.id_proyecto,extract(year FROM a.creado_en)::integer anio,'parcelas_afectadas'::text indicador,0::bigint programado,count(DISTINCT ua.id_parcela)::bigint realizado,count(DISTINCT ua.id_parcela)::bigint cantidad,NULL::numeric superficie_ha,NULL::numeric monto FROM afectacion a JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) JOIN afectacion_unidad_agraria au ON au.id_afectacion=a.id_afectacion AND au.activo JOIN unidad_agraria ua ON ua.id_unidad_agraria=au.id_unidad_agraria AND ua.activo WHERE a.activo AND ua.id_parcela IS NOT NULL GROUP BY pn.id_proyecto,extract(year FROM a.creado_en)
), indemn AS (
 SELECT pn.id_proyecto,extract(year FROM coalesce(i.fecha_resolucion,i.fecha_programada,i.creado_en::date))::integer anio,'indemnizaciones'::text indicador,count(*) FILTER(WHERE i.fecha_programada IS NOT NULL)::bigint programado,count(*) FILTER(WHERE i.fecha_resolucion IS NOT NULL OR i.estatus IN('completo','pagado'))::bigint realizado,count(*)::bigint cantidad,NULL::numeric superficie_ha,NULL::numeric monto FROM indemnizacion i JOIN afectacion a USING(id_afectacion) JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE i.activo AND a.activo GROUP BY pn.id_proyecto,extract(year FROM coalesce(i.fecha_resolucion,i.fecha_programada,i.creado_en::date))
), fifonafe AS (
 SELECT pn.id_proyecto,extract(year FROM coalesce(max(e.fecha_oficio),min(t.creado_en)::date))::integer anio,'fifonafe'::text indicador,
 count(*) FILTER (WHERE t.estatus IN('programado','pendiente'))::bigint programado,count(*) FILTER (WHERE t.estatus='completo')::bigint realizado,count(*)::bigint cantidad,NULL::numeric superficie_ha,NULL::numeric monto
 FROM tramite_fifonafe t JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) LEFT JOIN tramite_fifonafe_evento e ON e.id_tramite_fifonafe=t.id_tramite_fifonafe AND e.activo
 WHERE t.activo GROUP BY pn.id_proyecto
), legacy_convenios AS (
 SELECT pn.id_proyecto,extract(year FROM coalesce(c.fecha_firma,c.fecha_programada_firma,c.creado_en::date))::integer anio,
 CASE WHEN c.tipo_convenio='cop_original' AND c.ambito='colectivo' THEN 'cop_colectivos' WHEN c.tipo_convenio='cop_original' AND c.ambito='individual' THEN 'cop_individuales' WHEN c.tipo_convenio='modificatorio' THEN 'modificatorios' WHEN c.tipo_convenio='superficie_adicional' THEN 'superficies_adicionales' WHEN c.tipo_convenio='obras_complementarias' THEN 'obras_complementarias' WHEN c.tipo_convenio='ampliacion' THEN 'ampliaciones' WHEN c.tipo_convenio='ampliacion_remanente' THEN 'ampliaciones_remanentes' ELSE 'otros_instrumentos' END::text indicador,
 count(DISTINCT c.id_convenio) FILTER(WHERE c.fecha_programada_firma IS NOT NULL)::bigint programado,count(DISTINCT c.id_convenio) FILTER(WHERE c.fecha_firma IS NOT NULL)::bigint realizado,count(DISTINCT c.id_convenio)::bigint cantidad,sum(c.superficie_ha)::numeric superficie_ha,sum(c.monto_100)::numeric monto
 FROM convenio c JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) WHERE c.activo AND pn.activo GROUP BY pn.id_proyecto,extract(year FROM coalesce(c.fecha_firma,c.fecha_programada_firma,c.creado_en::date)),CASE WHEN c.tipo_convenio='cop_original' AND c.ambito='colectivo' THEN 'cop_colectivos' WHEN c.tipo_convenio='cop_original' AND c.ambito='individual' THEN 'cop_individuales' WHEN c.tipo_convenio='modificatorio' THEN 'modificatorios' WHEN c.tipo_convenio='superficie_adicional' THEN 'superficies_adicionales' WHEN c.tipo_convenio='obras_complementarias' THEN 'obras_complementarias' WHEN c.tipo_convenio='ampliacion' THEN 'ampliaciones' WHEN c.tipo_convenio='ampliacion_remanente' THEN 'ampliaciones_remanentes' ELSE 'otros_instrumentos' END
), affectations AS (
 SELECT pn.id_proyecto,extract(year FROM a.creado_en)::integer anio,v.indicador,0::bigint programado,count(DISTINCT a.id_afectacion)::bigint realizado,count(DISTINCT a.id_afectacion)::bigint cantidad,CASE WHEN v.indicador='superficie_preliminar_administrativa' THEN sum(a.superficie_preliminar_ha) ELSE sum(a.superficie_afectada_ha) END::numeric superficie_ha,NULL::numeric monto FROM afectacion a JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) CROSS JOIN (VALUES ('superficie_preliminar_administrativa'::text),('superficie_afectada_administrativa'::text)) v(indicador) WHERE a.activo AND pn.activo GROUP BY pn.id_proyecto,extract(year FROM a.creado_en),v.indicador
)
SELECT * FROM nucleos UNION ALL SELECT * FROM activity UNION ALL SELECT * FROM assembly UNION ALL SELECT * FROM ran UNION ALL SELECT * FROM convenios UNION ALL SELECT * FROM legacy_convenios UNION ALL SELECT * FROM affectations UNION ALL SELECT * FROM parcelas UNION ALL SELECT * FROM indemn UNION ALL SELECT * FROM fifonafe;
