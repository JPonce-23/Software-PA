# Arquitectura actual

El esquema vigente se instala mediante 001 baseline, 002 cierre Excel, 003 reporting y 004 seguimiento funcional. Las migraciones vigentes son 001, 002, 003 y 004; la siguiente migración es 005.

El dominio conserva eventos reales: actividades 1:N, Asamblea→Convocatorias 1:N, TramiteRan→Eventos 1:N y TramiteFifonafe→Eventos 1:N. `TRANSVERSALES` es clasificación operativa, no figura jurídica adicional de convenio.

`seguimiento_evento` modela la historia funcional auditada de eventos operativos (`inicio`, `suspension`, `reapertura`, `cierre`, `cambio_alcance`, `reunion`, `negociacion`, `consulta_indigena`, `continuacion_asamblea`, `medicion_bdt`, `otro`), vinculados a objetivos tipados del mismo `ProyectoNucleo` con baja lógica y bloqueo estricto de eliminación física.
`vw_seguimiento_estado_actual` deriva deterministamente el estado actual (`activo`, `suspendido`, `cerrado`) desde los eventos de transición sin mutar la historia ni alterar automáticamente atributos del núcleo (`comunidad_indigena`) o del proyecto-núcleo (`afecta_tuc`).
El subsistema documental incorpora los estados `parcial` y `pendiente_validacion` junto con los requisitos `validacion_pa_sict`, `oficio_ran_parcelas_afectacion` y `acta_complementaria`.

`vw_convenio_tipo_cop_operativo` deriva la clasificación desde afectaciones y deja revisión cuando es contradictoria. `vw_dashboard_kpi` es el resumen compatible. `vw_reporte_avance_periodo` deriva proyecto, entidad, año, mes, trimestre e indicadores desde fechas canónicas. La deduplicación es por PN/ciclo para actividades, Asamblea para asambleas y TramiteRan para RAN; no almacena X ni trimestres.
