# Migraciones vigentes

El runner aplica automáticamente archivos `NNN_*.sql` en orden y verifica checksum de los ya registrados.

Instalación limpia: `001_baseline_v1.sql` → `002_cierre_fuentes_excel.sql` → `003_reporting_fuentes_excel.sql` → `004_seguimiento_funcional_excel.sql`.

- 001: baseline canónico inmutable.
- 002: cierre de fuentes Excel, ciclos COP, estados y checklist.
- 003: reporting periódico y compatibilidad dashboard.
- 004: seguimiento funcional Excel (seguimiento_evento, tipos de evento, motivos, estados documentales parcial/pendiente_validacion, requisitos PA/SICT, RAN y acta complementaria).

Vigentes:
- 001
- 002
- 003
- 004

La siguiente migración es 005. No se editan migraciones ya publicadas; se agrega una nueva.
