-- Ajustes forward-only de reporting posteriores a la auditoría Excel V1.
SET search_path = public, pg_catalog;

DROP VIEW IF EXISTS vw_dashboard_kpi CASCADE;
DROP VIEW IF EXISTS vw_reporte_avance_periodo CASCADE;
ALTER VIEW vw_hito_seguimiento RENAME TO vw_hito_seguimiento_005;

CREATE OR REPLACE VIEW vw_hito_seguimiento AS
-- Conserva los hitos 005 que no cambian en esta auditoría.
SELECT * FROM vw_hito_seguimiento_005
WHERE indicador NOT IN ('asambleas','retiro_fondos','ingreso_ran_acta','inscripcion_ran_acta','ingreso_ran_convenio','inscripcion_ran_convenio','fifonafe','informe_no_conflictos')
  AND indicador NOT LIKE 'sensibilizacion_%' AND indicador NOT LIKE 'caminamiento_%'
UNION ALL
-- Actividad Excel V1 siempre es colectiva, aun si conserva una afectación individual de detalle.
SELECT pn.id_proyecto,e.id_entidad,pn.id_proyecto_nucleo,'colectivo'::text,c.codigo,NULL::text,NULL::text,
 'actividad:'||pn.id_proyecto_nucleo||':'||a.tipo_actividad||':'||coalesce(a.id_tipo_cop_operativo,0),
 a.tipo_actividad||'_'||coalesce(c.codigo,'SIN_CICLO'),min(a.fecha_programada),min(a.fecha_realizada),1::bigint,NULL::numeric,NULL::numeric
FROM actividad_campo a JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo
JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio
JOIN entidad_federativa e ON e.id_entidad=m.id_entidad LEFT JOIN catalogo_operativo c ON c.id_catalogo_opcion=a.id_tipo_cop_operativo
WHERE a.activo AND pn.activo AND (a.fecha_programada IS NOT NULL OR a.fecha_realizada IS NOT NULL)
GROUP BY pn.id_proyecto,e.id_entidad,pn.id_proyecto_nucleo,a.tipo_actividad,a.id_tipo_cop_operativo,c.codigo
UNION ALL
-- Asamblea ordinaria COP: una unidad por id_asamblea, con ciclo COP propio.
SELECT pn.id_proyecto,e.id_entidad,a.id_proyecto_nucleo,'colectivo'::text,cop.codigo,NULL::text,NULL::text,
 'asamblea:'||a.id_asamblea,'asambleas',min(ac.fecha_programada),min(ac.fecha_realizacion) FILTER(WHERE r.codigo='celebrada'),1::bigint,NULL::numeric,NULL::numeric
FROM asamblea a JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo
JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad
JOIN asamblea_convocatoria ac ON ac.id_asamblea=a.id_asamblea LEFT JOIN catalogo_operativo r ON r.id_catalogo_opcion=ac.id_resultado
LEFT JOIN catalogo_operativo cop ON cop.id_catalogo_opcion=a.id_tipo_cop_operativo
LEFT JOIN catalogo_operativo ta ON ta.id_catalogo_opcion=a.id_tipo_asamblea LEFT JOIN catalogo_operativo ca ON ca.id_catalogo_opcion=a.id_contexto_asamblea
WHERE a.activo AND pn.activo AND ac.activo AND coalesce(ta.codigo,'')<>'retiro_fondos' AND coalesce(ca.codigo,'')<>'retiro_fondos'
GROUP BY pn.id_proyecto,e.id_entidad,a.id_proyecto_nucleo,a.id_asamblea,cop.codigo
HAVING min(ac.fecha_programada) IS NOT NULL OR min(ac.fecha_realizacion) FILTER(WHERE r.codigo='celebrada') IS NOT NULL
UNION ALL
-- Retiro de fondos es un bloque exclusivo, no una segunda asamblea COP.
SELECT pn.id_proyecto,e.id_entidad,a.id_proyecto_nucleo,'colectivo'::text,NULL::text,NULL::text,NULL::text,
 'retiro_fondos:'||a.id_asamblea,'retiro_fondos',min(ac.fecha_programada),min(ac.fecha_realizacion) FILTER(WHERE r.codigo='celebrada'),1::bigint,NULL::numeric,NULL::numeric
FROM asamblea a JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo
JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad JOIN asamblea_convocatoria ac ON ac.id_asamblea=a.id_asamblea
LEFT JOIN catalogo_operativo r ON r.id_catalogo_opcion=ac.id_resultado LEFT JOIN catalogo_operativo ta ON ta.id_catalogo_opcion=a.id_tipo_asamblea LEFT JOIN catalogo_operativo ca ON ca.id_catalogo_opcion=a.id_contexto_asamblea
WHERE a.activo AND pn.activo AND ac.activo AND (ta.codigo='retiro_fondos' OR ca.codigo='retiro_fondos')
GROUP BY pn.id_proyecto,e.id_entidad,a.id_proyecto_nucleo,a.id_asamblea
HAVING min(ac.fecha_programada) IS NOT NULL OR min(ac.fecha_realizacion) FILTER(WHERE r.codigo='celebrada') IS NOT NULL
UNION ALL
-- RAN: acta usa COP de Asamblea; retiro cambia de indicador y nunca se duplica como acta.
SELECT pn.id_proyecto,e.id_entidad,tr.id_proyecto_nucleo,coalesce(cv.ambito,'colectivo')::text,
 CASE WHEN tr.id_asamblea IS NOT NULL THEN acop.codigo ELSE vco.tipo_cop_operativo_codigo END,cv.tipo_convenio::text,NULL::text,
 'ran_ingreso:'||tr.id_tramite_ran,CASE WHEN ta.codigo='retiro_fondos' OR ca.codigo='retiro_fondos' THEN 'ingreso_ran_retiro_fondos' WHEN tr.id_asamblea IS NOT NULL THEN 'ingreso_ran_acta' ELSE 'ingreso_ran_convenio' END,
 tr.fecha_programada_ingreso,min(ev.fecha_evento) FILTER(WHERE te.codigo IN ('ingreso','reingreso')),1::bigint,NULL::numeric,NULL::numeric
FROM tramite_ran tr JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=tr.id_proyecto_nucleo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad
LEFT JOIN asamblea a ON a.id_asamblea=tr.id_asamblea LEFT JOIN catalogo_operativo acop ON acop.id_catalogo_opcion=a.id_tipo_cop_operativo LEFT JOIN catalogo_operativo ta ON ta.id_catalogo_opcion=a.id_tipo_asamblea LEFT JOIN catalogo_operativo ca ON ca.id_catalogo_opcion=a.id_contexto_asamblea
LEFT JOIN convenio cv ON cv.id_convenio=tr.id_convenio LEFT JOIN vw_convenio_tipo_cop_operativo vco ON vco.id_convenio=tr.id_convenio LEFT JOIN tramite_ran_evento ev ON ev.id_tramite_ran=tr.id_tramite_ran AND ev.activo LEFT JOIN catalogo_operativo te ON te.id_catalogo_opcion=ev.id_tipo_evento
WHERE tr.activo AND pn.activo AND (tr.id_asamblea IS NOT NULL OR tr.id_convenio IS NOT NULL)
GROUP BY pn.id_proyecto,e.id_entidad,tr.id_proyecto_nucleo,tr.id_tramite_ran,tr.id_asamblea,acop.codigo,ta.codigo,ca.codigo,cv.ambito,vco.tipo_cop_operativo_codigo,cv.tipo_convenio,tr.fecha_programada_ingreso
HAVING tr.fecha_programada_ingreso IS NOT NULL OR min(ev.fecha_evento) FILTER(WHERE te.codigo IN ('ingreso','reingreso')) IS NOT NULL
UNION ALL
SELECT pn.id_proyecto,e.id_entidad,tr.id_proyecto_nucleo,coalesce(cv.ambito,'colectivo')::text,
 CASE WHEN tr.id_asamblea IS NOT NULL THEN acop.codigo ELSE vco.tipo_cop_operativo_codigo END,cv.tipo_convenio::text,NULL::text,
 'ran_inscripcion:'||tr.id_tramite_ran,CASE WHEN ta.codigo='retiro_fondos' OR ca.codigo='retiro_fondos' THEN 'inscripcion_ran_retiro_fondos' WHEN tr.id_asamblea IS NOT NULL THEN 'inscripcion_ran_acta' ELSE 'inscripcion_ran_convenio' END,
 NULL::date,min(ev.fecha_evento),1::bigint,NULL::numeric,NULL::numeric
FROM tramite_ran tr JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=tr.id_proyecto_nucleo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad
LEFT JOIN asamblea a ON a.id_asamblea=tr.id_asamblea LEFT JOIN catalogo_operativo acop ON acop.id_catalogo_opcion=a.id_tipo_cop_operativo LEFT JOIN catalogo_operativo ta ON ta.id_catalogo_opcion=a.id_tipo_asamblea LEFT JOIN catalogo_operativo ca ON ca.id_catalogo_opcion=a.id_contexto_asamblea
LEFT JOIN convenio cv ON cv.id_convenio=tr.id_convenio LEFT JOIN vw_convenio_tipo_cop_operativo vco ON vco.id_convenio=tr.id_convenio JOIN tramite_ran_evento ev ON ev.id_tramite_ran=tr.id_tramite_ran AND ev.activo JOIN catalogo_operativo te ON te.id_catalogo_opcion=ev.id_tipo_evento AND te.codigo='inscripcion'
WHERE tr.activo AND pn.activo AND (tr.id_asamblea IS NOT NULL OR tr.id_convenio IS NOT NULL)
GROUP BY pn.id_proyecto,e.id_entidad,tr.id_proyecto_nucleo,tr.id_tramite_ran,tr.id_asamblea,acop.codigo,ta.codigo,ca.codigo,cv.ambito,vco.tipo_cop_operativo_codigo,cv.tipo_convenio
UNION ALL
-- FIFONAFE colectivo: cuatro códigos con número y fecha; MAX sólo de esos cuatro.
SELECT pn.id_proyecto,e.id_entidad,t.id_proyecto_nucleo,t.ambito::text,NULL::text,NULL::text,NULL::text,'fifonafe:'||t.id_tramite_fifonafe,'fifonafe',NULL::date,
 CASE WHEN t.ambito='colectivo' AND count(DISTINCT co.codigo) FILTER(WHERE co.codigo IN ('oficio_fifonafe_dgaopr','oficio_dgaopr_representacion','respuesta_representacion_dgaopr','respuesta_dgaopr_fifonafe') AND nullif(btrim(fe.numero_oficio),'') IS NOT NULL AND fe.fecha_oficio IS NOT NULL)=4
 THEN max(fe.fecha_oficio) FILTER(WHERE co.codigo IN ('oficio_fifonafe_dgaopr','oficio_dgaopr_representacion','respuesta_representacion_dgaopr','respuesta_dgaopr_fifonafe') AND nullif(btrim(fe.numero_oficio),'') IS NOT NULL) WHEN t.ambito='individual' AND t.estatus='completo' THEN coalesce(max(fe.fecha_oficio),t.acuse_fifonafe_fecha) END,1::bigint,NULL::numeric,NULL::numeric
FROM tramite_fifonafe t JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=t.id_proyecto_nucleo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad LEFT JOIN tramite_fifonafe_evento fe ON fe.id_tramite_fifonafe=t.id_tramite_fifonafe AND fe.activo LEFT JOIN catalogo_operativo co ON co.id_catalogo_opcion=fe.id_tipo_evento WHERE t.activo AND pn.activo GROUP BY t.id_tramite_fifonafe,pn.id_proyecto,e.id_entidad,t.id_proyecto_nucleo,t.ambito,t.estatus,t.acuse_fifonafe_fecha
HAVING (t.ambito='colectivo' AND count(DISTINCT co.codigo) FILTER(WHERE co.codigo IN ('oficio_fifonafe_dgaopr','oficio_dgaopr_representacion','respuesta_representacion_dgaopr','respuesta_dgaopr_fifonafe') AND nullif(btrim(fe.numero_oficio),'') IS NOT NULL AND fe.fecha_oficio IS NOT NULL)=4) OR (t.ambito='individual' AND t.estatus='completo' AND coalesce(max(fe.fecha_oficio),t.acuse_fifonafe_fecha) IS NOT NULL);

CREATE OR REPLACE VIEW vw_reporte_avance_periodo AS
WITH f AS (SELECT id_proyecto,id_entidad,ambito,tipo_cop_operativo,tipo_convenio,destino_superficie,clave_hito,indicador,fecha_programada fecha,1::bigint programado,0::bigint realizado,NULL::numeric superficie_ha,NULL::numeric monto FROM vw_hito_seguimiento WHERE fecha_programada IS NOT NULL UNION ALL SELECT id_proyecto,id_entidad,ambito,tipo_cop_operativo,tipo_convenio,destino_superficie,clave_hito,indicador,fecha_realizada,0::bigint,1::bigint,superficie_ha,monto FROM vw_hito_seguimiento WHERE fecha_realizada IS NOT NULL)
SELECT id_proyecto,id_entidad,ambito,tipo_cop_operativo,tipo_convenio,destino_superficie,extract(year FROM fecha)::integer anio,extract(month FROM fecha)::integer mes,extract(quarter FROM fecha)::integer trimestre,indicador,sum(programado)::bigint programado,sum(realizado)::bigint realizado,count(DISTINCT clave_hito)::bigint cantidad,sum(superficie_ha)::numeric superficie_ha,sum(monto)::numeric monto FROM f GROUP BY id_proyecto,id_entidad,ambito,tipo_cop_operativo,tipo_convenio,destino_superficie,extract(year FROM fecha),extract(month FROM fecha),extract(quarter FROM fecha),indicador;
CREATE OR REPLACE VIEW vw_dashboard_kpi AS
WITH f AS (SELECT id_proyecto,extract(year FROM fecha_programada)::integer anio,indicador,clave_hito,1::bigint programado,0::bigint realizado,NULL::numeric superficie_ha,NULL::numeric monto FROM vw_hito_seguimiento WHERE fecha_programada IS NOT NULL UNION ALL SELECT id_proyecto,extract(year FROM fecha_realizada)::integer,indicador,clave_hito,0::bigint,1::bigint,superficie_ha,monto FROM vw_hito_seguimiento WHERE fecha_realizada IS NOT NULL) SELECT id_proyecto,anio,indicador,sum(programado)::bigint programado,sum(realizado)::bigint realizado,count(DISTINCT clave_hito)::bigint cantidad,sum(superficie_ha)::numeric superficie_ha,sum(monto)::numeric monto FROM f GROUP BY id_proyecto,anio,indicador;

CREATE OR REPLACE VIEW vw_reporte_snapshot_actual AS
SELECT pn.id_proyecto,e.id_entidad,'colectivo'::text ambito,'total_nucleos'::text indicador,NULL::text tipo_cop_operativo,NULL::text destino_superficie,count(*)::bigint cantidad,NULL::numeric superficie_ha,NULL::numeric monto FROM proyecto_nucleo pn JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE pn.activo GROUP BY pn.id_proyecto,e.id_entidad
UNION ALL SELECT pn.id_proyecto,e.id_entidad,'individual','total_parcelas_afectadas',NULL,NULL,count(DISTINCT ua.id_parcela),NULL,NULL FROM afectacion a JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad JOIN afectacion_unidad_agraria au ON au.id_afectacion=a.id_afectacion AND au.activo JOIN unidad_agraria ua ON ua.id_unidad_agraria=au.id_unidad_agraria AND ua.activo WHERE a.activo AND pn.activo AND ua.id_parcela IS NOT NULL GROUP BY pn.id_proyecto,e.id_entidad
UNION ALL SELECT pn.id_proyecto,e.id_entidad,a.tipo_afectacion,'superficie_afectada_administrativa',cop.codigo,NULL,count(*),sum(a.superficie_afectada_ha),NULL FROM afectacion a JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad LEFT JOIN catalogo_operativo cop ON cop.id_catalogo_opcion=a.id_tipo_cop_operativo WHERE a.activo AND pn.activo AND a.superficie_afectada_ha IS NOT NULL GROUP BY pn.id_proyecto,e.id_entidad,a.tipo_afectacion,cop.codigo
UNION ALL SELECT pn.id_proyecto,e.id_entidad,a.tipo_afectacion,'superficie_por_destino',cop.codigo,dest.codigo,count(*),sum(au.superficie_afectada_ha),NULL FROM afectacion_unidad_agraria au JOIN afectacion a ON a.id_afectacion=au.id_afectacion AND a.activo JOIN proyecto_nucleo pn ON pn.id_proyecto_nucleo=a.id_proyecto_nucleo AND pn.activo JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad JOIN unidad_agraria ua ON ua.id_unidad_agraria=au.id_unidad_agraria AND ua.activo JOIN catalogo_operativo dest ON dest.id_catalogo_opcion=ua.id_destino_superficie LEFT JOIN catalogo_operativo cop ON cop.id_catalogo_opcion=a.id_tipo_cop_operativo WHERE au.activo GROUP BY pn.id_proyecto,e.id_entidad,a.tipo_afectacion,cop.codigo,dest.codigo
UNION ALL SELECT pn.id_proyecto,e.id_entidad,'colectivo','no_afecta_tuc',NULL,NULL,count(*),NULL,NULL FROM proyecto_nucleo pn JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE pn.activo AND pn.afecta_tuc=false GROUP BY pn.id_proyecto,e.id_entidad
UNION ALL SELECT pn.id_proyecto,e.id_entidad,'colectivo','comunidad_indigena',NULL,NULL,count(*),NULL,NULL FROM proyecto_nucleo pn JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE pn.activo AND n.comunidad_indigena=true GROUP BY pn.id_proyecto,e.id_entidad
UNION ALL SELECT pn.id_proyecto,e.id_entidad,'colectivo','total_cops_planeados',NULL,NULL,sum(coalesce(pn.total_cops_planeados,0))::bigint,NULL,NULL FROM proyecto_nucleo pn JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE pn.activo GROUP BY pn.id_proyecto,e.id_entidad;

CREATE OR REPLACE FUNCTION fn_validar_seguimiento_post_auditoria() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE tipo text;
BEGIN
 SELECT codigo INTO tipo FROM catalogo_operativo WHERE id_catalogo_opcion=NEW.id_tipo_evento;
 IF tipo IN ('inicio','suspension','reapertura','cierre','cambio_alcance') AND NEW.fecha_evento IS NULL THEN RAISE EXCEPTION 'El evento de transición % requiere fecha_evento',tipo; END IF;
 IF NEW.id_documento IS NOT NULL AND NOT EXISTS (SELECT 1 FROM documento d JOIN documento_vinculo dv ON dv.id_documento=d.id_documento AND dv.activo WHERE d.id_documento=NEW.id_documento AND d.activo AND fn_objetivo_requisito_en_pn(dv.entidad_tipo,dv.entidad_id,NEW.id_proyecto_nucleo)) THEN RAISE EXCEPTION 'Documento inexistente, inactivo o ajeno al ProyectoNucleo del seguimiento'; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS trg_validar_seguimiento_post_auditoria ON seguimiento_evento;
CREATE TRIGGER trg_validar_seguimiento_post_auditoria BEFORE INSERT OR UPDATE ON seguimiento_evento FOR EACH ROW EXECUTE FUNCTION fn_validar_seguimiento_post_auditoria();
GRANT SELECT ON vw_hito_seguimiento,vw_reporte_avance_periodo,vw_dashboard_kpi,vw_reporte_snapshot_actual TO software_pa_app;
