# Migraciones vigentes

El runner aplica automáticamente archivos `NNN_*.sql` en orden y verifica checksum de los ya registrados.

Instalación limpia: `001_baseline_v1.sql` → `002_cierre_fuentes_excel.sql` → `003_reporting_fuentes_excel.sql`.

- 001: baseline canónico inmutable.
- 002: cierre de fuentes Excel, ciclos COP, estados y checklist.
- 003: reporting periódico y compatibilidad dashboard.

La siguiente migración es 004. No se editan migraciones ya publicadas; se agrega una nueva.
