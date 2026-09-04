# Arquitectura actual

El esquema vigente se instala mediante 001–006. La 006 es forward-only y corrige la semántica de reporting detectada durante auditoría sin remodelar el dominio.

El dominio conserva eventos reales: actividades 1:N, Asamblea→Convocatorias 1:N, TramiteRan→Eventos 1:N y TramiteFifonafe→Eventos 1:N. `TRANSVERSALES` es clasificación operativa, no figura jurídica adicional de convenio.

`seguimiento_evento` modela la historia funcional auditada de eventos operativos (`inicio`, `suspension`, `reapertura`, `cierre`, `cambio_alcance`, `reunion`, `negociacion`, `consulta_indigena`, `continuacion_asamblea`, `medicion_bdt`, `otro`), vinculados a objetivos tipados del mismo `ProyectoNucleo` con baja lógica y bloqueo estricto de eliminación física.
`vw_seguimiento_estado_actual` deriva deterministamente el estado actual (`activo`, `suspendido`, `cerrado`) desde los eventos de transición sin mutar la historia ni alterar automáticamente atributos del núcleo (`comunidad_indigena`) o del proyecto-núcleo (`afecta_tuc`).
El subsistema documental incorpora los estados `parcial` y `pendiente_validacion` junto con los requisitos `validacion_pa_sict`, `oficio_ran_parcelas_afectacion` y `acta_complementaria`.

En reporting (005), la arquitectura de lectura opera en dos capas estrictas:
1. `vw_hito_seguimiento`: consolida cada hito operativo/jurídico único (`clave_hito`) antes de su proyección a periodos temporales, asignando sus fechas canónicas programada y realizada, su indicador, ámbito, ciclo COP, tipo de convenio, destino de superficie, cantidad, superficie y monto.
2. `vw_reporte_avance_periodo`: proyecta los hitos en periodos independientes (año, mes, trimestre) diferenciando programado y realizado, y exponiendo 15 columnas con filtros dimensionales completos (`ambito`, `tipo_cop_operativo`, `tipo_convenio`, `destino_superficie`).
3. `vw_dashboard_kpi`: agregación de alto nivel por `id_proyecto, anio, indicador`, deduplicada anualmente sin multiplicar registros ni superficies por relaciones 1:N o N:M. No almacena marcas X ni periodos auxiliares Excel.

Núcleos, parcelas y superficies sin fecha de negocio son snapshots: sus altas técnicas no se proyectan a avance temporal ni al dashboard anual. La inscripción RAN procede sólo de `tramite_ran_evento` de tipo `inscripcion`; la calificación no la reemplaza. FIFONAFE colectivo usa los cuatro oficios fechados y su máximo; no conflictos (`hay_conflictos=false`) conserva una semántica independiente.

006 expone `vw_reporte_snapshot_actual` y `GET /api/reportes/resumen-actual`: estado actual sin año/mes/trimestre. Asamblea ordinaria usa su COP propio; retiro de fondos y su RAN son indicadores exclusivos.
