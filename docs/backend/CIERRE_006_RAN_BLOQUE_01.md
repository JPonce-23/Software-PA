# Cierre funcional 006 — Bloque 01: ciclos RAN

Estado: `BLOQUE RAN CERRADO`.

Base de código revisada: `53a7920507faf608d11234608c9cfc5d731ac154`.
Alcance: pruebas y contrato funcional del bloque RAN; sin cambios de esquema.

## Contrato cubierto

Las regresiones preparadas mantienen un solo trámite durante ingresos, prevenciones,
subsanaciones, reingresos, calificación e inscripción, conservando el historial de
eventos, ordinales y referencias. También cubren objetivos tipados exclusivos,
rechazo de ordinal duplicado, RAN sobre ORV y ausencia de duplicación de Asamblea.

El reporte debe contar un solo ingreso por `TramiteRan`, usando la primera fecha real
de ingreso o reingreso, y sólo debe contar una inscripción cuando exista el evento
`inscripcion`. Una calificación no equivale a inscripción y una subsanación no crea
un reingreso automático.

## Contraste estático realizado

Se revisaron `TramiteRan`, `TramiteRanEvento`, los schemas de creación y respuesta,
`services/domain.py`, `routers/domain.py`, el reporting de 006 y las pruebas existentes
de 002, 005 y 006. El modelo conserva un trámite con múltiples eventos; el schema
exige exactamente un objetivo entre Asamblea, Convenio y ORV; y el servicio agrega
eventos al trámite existente. La vista de 006 deduplica ingreso/reingreso mediante
`min(fecha_evento)` y restringe inscripción al código de evento `inscripcion`.

## Paquete integrado

El ZIP contiene únicamente esta nota, la regresión
`backend/tests/test_cierre_006_ran_ciclos.py` y un parche alternativo. El parche no se
usó: carece de hunk `@@`, reporta 0 inserciones y habría creado una prueba vacía. La
prueba se integró desde el archivo completo incluido en el ZIP, sin aplicar además el
parche.

## QA permanente y evidencia de ejecución

La candidata `software_pa_cierre_excel_test`, inicialmente vacía y con 001–002, se
respaldó y renombró a `software_pa_test`. Se aplicaron exclusivamente 003–006 con el
runner oficial. El ledger final contiene exactamente 001–006 y sus seis checksums
coinciden con el HEAD indicado arriba. Se instaló el fixture territorial de 32
entidades y 2,478 municipios y un administrador exclusivo de QA.

La conexión efectiva del proceso de pruebas se comprobó como
`current_database()=software_pa_test`, `current_user=pa_runtime` y `APP_ENV=test`.
El contrato runtime confirmó que dicho usuario no puede modificar el ledger, crear
DDL ni ejecutar `DELETE`/`TRUNCATE` físicos.

Respaldos verificables:

- Previo al renombre: `backups/pre_software_pa_cierre_excel_test_rename_20260907.dump`,
  703,054 bytes, SHA-256
  `56c80a6e0c822cc8596a29106653933685868fe1ab8ea4ae461078d2416dc3d0`.
- Golden mínimo anterior a regresiones:
  `backups/software_pa_test_golden_001_006_20260907.dump`, 785,418 bytes, SHA-256
  `2606853e675e3dad836eef30bb9f1701349e17c84c29124ba011e2396d6e7c94`.

Ambos catálogos fueron leídos correctamente con `pg_restore -l`.

Resultados reales de pytest dentro del contenedor backend:

- Regresión RAN: 6 recolectados, 6 aprobados, 0 fallidos, 0 errores; 7.48 s.
- Suites 002/004/005/006: 60 recolectados, 60 aprobados, 0 fallidos, 0 errores;
  31.85 s.
- Suite backend completa: 164 recolectados, 164 aprobados, 0 fallidos, 0 errores;
  62.53 s.

Todas las ejecuciones emitieron únicamente la advertencia conocida de deprecación de
Starlette sobre `httpx`.

## Contratos SQL históricos

Los contratos específicos 002, 004 y 006 aprobaron, al igual que el contrato de ACL
runtime. Los contratos 001, 003 y 005 contienen inspecciones textuales de vistas de
su etapa original: esperan referencias físicas directas que 006 conserva mediante
las vistas encadenadas `vw_hito_seguimiento`/`vw_hito_seguimiento_005`; 001 además
requiere datos del seed demo, deliberadamente ausentes del golden mínimo. Se
clasificaron como expectativas históricas no acumulativas y no se modificaron para
hacerlas pasar. La suite funcional completa verde confirma que no constituyen un
defecto del bloque RAN.

El cierre se limita al bloque RAN. No declara cerrado todo el Modelo Excel V1 ni
autoriza avanzar automáticamente a otros bloques funcionales.
