# Arquitectura actual

El esquema vigente se instala mediante 001 baseline, 002 cierre Excel y 003 reporting. La siguiente migración disponible es 004.

El dominio conserva eventos reales: actividades 1:N, Asamblea→Convocatorias 1:N, TramiteRan→Eventos 1:N y TramiteFifonafe→Eventos 1:N. `TRANSVERSALES` es clasificación operativa, no figura jurídica adicional de convenio.

`vw_convenio_tipo_cop_operativo` deriva la clasificación desde afectaciones y deja revisión cuando es contradictoria. `vw_dashboard_kpi` es el resumen compatible. `vw_reporte_avance_periodo` deriva proyecto, entidad, año, mes, trimestre e indicadores desde fechas canónicas. La deduplicación es por PN/ciclo para actividades, Asamblea para asambleas y TramiteRan para RAN; no almacena X ni trimestres.
