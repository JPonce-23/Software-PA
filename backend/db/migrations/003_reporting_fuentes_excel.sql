-- Reporting temporal derivado; no persiste marcas X ni periodos Excel.
SET search_path = public, pg_catalog;

CREATE OR REPLACE VIEW vw_reporte_avance_periodo AS
WITH filas AS (
  SELECT pn.id_proyecto,e.id_entidad,pn.id_proyecto_nucleo::text AS clave,'nucleos'::text AS indicador,pn.creado_en::date AS fecha,0::bigint AS programado,1::bigint AS realizado,NULL::numeric AS superficie_ha,NULL::numeric AS monto
  FROM proyecto_nucleo pn JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE pn.activo
  UNION ALL
  SELECT pn.id_proyecto,e.id_entidad,a.id_proyecto_nucleo::text||':'||coalesce(a.id_tipo_cop_operativo,0)::text clave,
         a.tipo_actividad||'_'||coalesce(c.codigo,'SIN_CICLO') indicador,a.fecha_programada fecha,1::bigint programado,0::bigint realizado,NULL::numeric superficie_ha,NULL::numeric monto
  FROM actividad_campo a JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad LEFT JOIN catalogo_operativo c ON c.id_catalogo_opcion=a.id_tipo_cop_operativo
  WHERE a.activo AND pn.activo AND a.fecha_programada IS NOT NULL
  UNION ALL
  SELECT pn.id_proyecto,e.id_entidad,a.id_proyecto_nucleo::text||':'||coalesce(a.id_tipo_cop_operativo,0)::text,a.tipo_actividad||'_'||coalesce(c.codigo,'SIN_CICLO'),a.fecha_realizada,0,1,NULL,NULL
  FROM actividad_campo a JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad LEFT JOIN catalogo_operativo c ON c.id_catalogo_opcion=a.id_tipo_cop_operativo
  WHERE a.activo AND pn.activo AND a.fecha_realizada IS NOT NULL
  UNION ALL
  SELECT pn.id_proyecto,e.id_entidad,a.id_asamblea::text,'asambleas',ac.fecha_programada,1,0,NULL,NULL
  FROM asamblea a JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad JOIN asamblea_convocatoria ac USING(id_asamblea)
  WHERE a.activo AND pn.activo AND ac.activo AND ac.fecha_programada IS NOT NULL
  UNION ALL
  SELECT pn.id_proyecto,e.id_entidad,a.id_asamblea::text,'asambleas',ac.fecha_realizacion,0,1,NULL,NULL
  FROM asamblea a JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad JOIN asamblea_convocatoria ac USING(id_asamblea) JOIN catalogo_operativo r ON r.id_catalogo_opcion=ac.id_resultado
  WHERE a.activo AND pn.activo AND ac.activo AND r.codigo='celebrada' AND ac.fecha_realizacion IS NOT NULL
  UNION ALL
  SELECT pn.id_proyecto,e.id_entidad,tr.id_tramite_ran::text,'ingreso_ran_'||CASE WHEN tr.id_asamblea IS NOT NULL THEN 'acta' ELSE 'convenio' END,tr.fecha_programada_ingreso,1,0,NULL,NULL
  FROM tramite_ran tr JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad
  WHERE tr.activo AND tr.fecha_programada_ingreso IS NOT NULL AND (tr.id_asamblea IS NOT NULL OR tr.id_convenio IS NOT NULL)
  UNION ALL
  SELECT pn.id_proyecto,e.id_entidad,tr.id_tramite_ran::text,'ingreso_ran_'||CASE WHEN tr.id_asamblea IS NOT NULL THEN 'acta' ELSE 'convenio' END,ev.fecha_evento,0,1,NULL,NULL
  FROM tramite_ran tr JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad JOIN tramite_ran_evento ev USING(id_tramite_ran) JOIN catalogo_operativo t ON t.id_catalogo_opcion=ev.id_tipo_evento
  WHERE tr.activo AND ev.activo AND t.codigo IN('ingreso','reingreso') AND ev.fecha_evento IS NOT NULL AND (tr.id_asamblea IS NOT NULL OR tr.id_convenio IS NOT NULL)
  UNION ALL
  SELECT pn.id_proyecto,e.id_entidad,tr.id_tramite_ran::text,'inscripcion_ran_'||CASE WHEN tr.id_asamblea IS NOT NULL THEN 'acta' ELSE 'convenio' END,ev.fecha_evento,0,1,NULL,NULL
  FROM tramite_ran tr JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad JOIN tramite_ran_evento ev USING(id_tramite_ran) JOIN catalogo_operativo t ON t.id_catalogo_opcion=ev.id_tipo_evento
  WHERE tr.activo AND ev.activo AND t.codigo='inscripcion' AND ev.fecha_evento IS NOT NULL AND (tr.id_asamblea IS NOT NULL OR tr.id_convenio IS NOT NULL)
  UNION ALL
  SELECT pn.id_proyecto,e.id_entidad,c.id_convenio::text,CASE WHEN c.tipo_convenio='cop_original' AND c.ambito='colectivo' THEN 'cop_colectivos' WHEN c.tipo_convenio='cop_original' AND c.ambito='individual' THEN 'cop_individuales' ELSE 'otros_instrumentos' END, c.fecha_programada_firma,1,0,NULL,NULL
  FROM convenio c JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad
  WHERE c.activo AND c.fecha_programada_firma IS NOT NULL
  UNION ALL
  SELECT pn.id_proyecto,e.id_entidad,c.id_convenio::text,CASE WHEN c.tipo_convenio='cop_original' AND c.ambito='colectivo' THEN 'cop_colectivos' WHEN c.tipo_convenio='cop_original' AND c.ambito='individual' THEN 'cop_individuales' ELSE 'otros_instrumentos' END, c.fecha_firma,0,1,c.superficie_ha,c.monto_100
  FROM convenio c JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad
  WHERE c.activo AND c.fecha_firma IS NOT NULL
  UNION ALL
  SELECT pn.id_proyecto,e.id_entidad,ua.id_parcela::text,'parcelas_afectadas',a.creado_en::date,0,1,NULL,NULL
  FROM afectacion a JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad JOIN afectacion_unidad_agraria au ON au.id_afectacion=a.id_afectacion AND au.activo JOIN unidad_agraria ua ON ua.id_unidad_agraria=au.id_unidad_agraria AND ua.activo
  WHERE a.activo AND ua.id_parcela IS NOT NULL
  UNION ALL
  SELECT pn.id_proyecto,e.id_entidad,t.id_tramite_fifonafe::text,'fifonafe',t.creado_en::date,CASE WHEN t.estatus IN('programado','pendiente') THEN 1 ELSE 0 END,CASE WHEN t.estatus='completo' THEN 1 ELSE 0 END,NULL,NULL
  FROM tramite_fifonafe t JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE t.activo
  UNION ALL
  SELECT pn.id_proyecto,e.id_entidad,a.id_afectacion::text,'superficie_afectada_administrativa',a.creado_en::date,0,1,a.superficie_afectada_ha,NULL
  FROM afectacion a JOIN proyecto_nucleo pn USING(id_proyecto_nucleo) JOIN nucleo_agrario n ON n.id_nucleo=pn.id_nucleo JOIN municipio m ON m.id_municipio=n.id_municipio JOIN entidad_federativa e ON e.id_entidad=m.id_entidad WHERE a.activo
)
SELECT id_proyecto,id_entidad,extract(year FROM fecha)::integer anio,extract(month FROM fecha)::integer mes,extract(quarter FROM fecha)::integer trimestre,indicador,
       count(DISTINCT clave) FILTER (WHERE programado=1)::bigint programado,count(DISTINCT clave) FILTER (WHERE realizado=1)::bigint realizado,count(DISTINCT clave)::bigint cantidad,
       sum(superficie_ha)::numeric superficie_ha,sum(monto)::numeric monto
FROM filas GROUP BY id_proyecto,id_entidad,extract(year FROM fecha),extract(month FROM fecha),extract(quarter FROM fecha),indicador;

-- El dashboard existente conserva sus columnas/año; las fechas distintas se
-- agregan desde el read-model periódico sin mezclar sus periodos de origen.
CREATE OR REPLACE VIEW vw_dashboard_kpi AS
SELECT id_proyecto,anio,indicador,sum(programado)::bigint programado,sum(realizado)::bigint realizado,sum(cantidad)::bigint cantidad,sum(superficie_ha)::numeric superficie_ha,sum(monto)::numeric monto
FROM vw_reporte_avance_periodo GROUP BY id_proyecto,anio,indicador;
