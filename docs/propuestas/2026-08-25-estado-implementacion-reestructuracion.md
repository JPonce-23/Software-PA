# Estado de implementación de la reestructuración

## Commit base

- Rama: `feature/backend-logica`.
- HEAD/base: `4a007fdb14ff0f9359f3c3b5f35d9a9ab5105069`.
- Al iniciar el trabajo, HEAD local y `origin/feature/backend-logica` coincidían (`0/0`).
- Corte de este checkpoint: `2026-08-25T22:45:10-06:00`.
- No hubo commit, push, merge ni cambio de rama.

## Fases completadas

| Fase | Estado comprobado | Validación |
|---|---|---|
| 1. Preflight / seguridad | COMPLETA Y VALIDADA | rama/HEAD/status/remoto; PostgreSQL 15.4/PostGIS 3.3.4; entorno y base local identificados; advisory locks y guards destructivos probados |
| 2. Fixture territorial | COMPLETA Y VALIDADA | 32 entidades, 2,478 municipios activos, unicidad, idempotencia y SHA-256 |
| 3. Migración 031 | COMPLETA Y VALIDADA | aplica desde 030, aplica en historia limpia, rollback inducido y base activa |
| 4. Modelos SQLAlchemy | COMPLETA Y VALIDADA | 39 objetos mapeados; `configure_mappers()` sin error; metadata contrastada con esquema |
| 5. Schemas Pydantic | COMPLETA Y VALIDADA | OpenAPI genera 58 rutas/87 operaciones; pytest objetivo verde; sin IDs de tramo/ciclo |
| 6. Services | COMPLETA Y VALIDADA | transacciones de dominio, N:M, documentos y autorización cubiertas por pytest/SQL |
| 7. Routers/API | COMPLETA Y VALIDADA | routers objetivo montados; OpenAPI y pruebas de API verdes |
| 8. RBAC por proyecto | COMPLETA Y VALIDADA | admin, operador, visualizador y geógrafo; filtro previo a paginación/dashboard/exportación |
| 9. Tests backend | COMPLETA Y VALIDADA | 14/14 pytest |
| 10. Frontend administrativo | COMPLETA Y VALIDADA | lint, build y flujos Playwright objetivo |
| 11. Migración 032 | COMPLETA Y VALIDADA | aplica después de 031, rollback inducido y base activa |
| 12. Importador GIS | COMPLETA Y VALIDADA | staging, preview, confirmación, objetivos controlados e idempotencia en pytest |
| 13. Mapa | COMPLETA Y VALIDADA | capas por proyecto y parcela sin geometría en pytest/Playwright |
| 14. Migración 033 | COMPLETA Y VALIDADA | tres vistas consultables y versión registrada |
| 15. Dashboard | COMPLETA Y VALIDADA | contrato exacto del seed, exportación, N:M sin multiplicación |
| 16. Seed nuevo | COMPLETA Y VALIDADA | ejecutado desde bases 033 vacías y en base activa; conteos exactos |
| 17. Pruebas SQL | COMPLETA Y VALIDADA | contrato 031-033+seed aprobado en tres cadenas independientes |
| 18. Pytest | COMPLETA Y VALIDADA | 14 aprobados, 0 fallidos |
| 19. Tests frontend | COMPLETA Y VALIDADA | lint: 0 errores/0 advertencias; build: aprobado |
| 20. Playwright | COMPLETA Y VALIDADA | 8 aprobados, 0 fallidos en imagen oficial 1.62.1 |
| 21. Instalación limpia | COMPLETA Y VALIDADA | bootstrap real `001`, `004`-`030`, fixture, `031`-`033`, seed y contrato |
| 22. Búsqueda legacy | COMPLETA Y VALIDADA | 0 dependencias funcionales; 11 líneas permitidas clasificadas |
| 23. `Arquitectura_Actual.md` | COMPLETA Y VALIDADA | reescrita contra SQL/ORM/API/frontend 033 |
| 24. `Diccionario_Datos_SSALFER.md` | COMPLETA Y VALIDADA | reescrito contra catálogo efectivo de columnas/constraints/vistas 033 |
| 25. Auditoría final | COMPLETA Y VALIDADA | SQL, ORM, OpenAPI, frontend, docs y Git contrastados |

No quedan fases parciales, no iniciadas o bloqueadas dentro del alcance solicitado.

## Archivos creados/modificados

Archivos nuevos (29):

- Routers: `backend/app/routers/{documents,domain,geospatial_imports,reporting,users}.py`.
- Services: `backend/app/services/{documents,domain,geospatial_imports}.py`.
- Fixture: `backend/db/fixtures/{001_catalogo_territorial_inegi.sql,001_catalogo_territorial_inegi.metadata.json,README.md}`.
- Migraciones: `backend/db/migrations/{031_reset_dominio_proyecto_nucleo.sql,032_cleanup_legacy_gis_importacion.sql,033_dashboard_modelo_objetivo.sql}`.
- Seed/contrato: `backend/db/seeds/README.md`, `backend/db/seeds/assets/qa_soporte_demo.txt`, `backend/db/tests/031_033_contract.sql`, `backend/scripts/seed_objective_demo.py`.
- Pytest: `backend/tests/{test_auth_rbac,test_documents_dashboard,test_geospatial_imports,test_target_domain}.py`.
- Frontend: `frontend/src/components/{DocumentsPanel,TargetUI}.jsx`, `frontend/src/pages/{AffectationDetail,ProjectNavigator,ProjectNucleus}.jsx`, `frontend/src/utils/target.js`.
- Checkpoint: este archivo.

Archivos rastreados modificados (26):

- Backend: `backend/app/{main,models,schemas}.py`, `backend/app/services/{access,common,gis_ingestion}.py`, `backend/db/seed.sql`, `backend/scripts/seed_uat.py`, `backend/tests/conftest.py`.
- Contenedores: `docker-compose.yml`, `docker-compose.override.yml`.
- Frontend: `frontend/src/App.jsx`, `frontend/src/index.css`, `frontend/src/pages/{AdministracionUsuarios,Dashboard,ImportacionesGeoespaciales,Mapa}.jsx`, `frontend/tests/e2e/{administracion,expedientes}.spec.js`.
- Documentación: `docs/{Arquitectura_Actual,Description,Diccionario_Datos_SSALFER,README,design,requirements}.md` y `docs/propuestas/2026-08-25-diseno-reestructuracion-bd.md`.

Archivos retirados (74): routers/services/tests/scripts legacy de backend y componentes/páginas/utilidades legacy de frontend que dependían de tramo, ciclo, candidatos, secciones, alertas o cargas GIS anteriores. `git status` conserva cada baja como `D`; no se revirtió ningún cambio previo.

No se modificaron migraciones 001-030, archivos Excel ni archivos `*_fuente.md`. `fuentes_locales/` continúa ignorado.

## Migraciones implementadas

- `031_reset_dominio_proyecto_nucleo.sql`: reset protegido, dominio `ProyectoNucleo`, hechos administrativos, N:M, cadena financiera, documentos, trazabilidad, auditoría y `usuario_proyecto`.
- `032_cleanup_legacy_gis_importacion.sql`: `trazo_proyecto`, importador consolidado y eliminación de GIS/alcance legacy.
- `033_dashboard_modelo_objetivo.sql`: `vw_orv_estado`, `vw_proyecto_nucleo_resumen` y `vw_dashboard_kpi`.

031 y 032 tienen guards NULL-safe de entorno, nombre de base, confirmación y respaldo; adquieren advisory lock antes del DDL. 031 exige versión 030 y catálogo 32/2,478.

## Migraciones ejecutadas y estado del esquema

- `db_pruebas_alfredo` (base activa local): 031, 032 y 033 aplicadas; fixture y seed aplicados; `/health` devuelve `schema: 33`.
- `software_pa_objective_test`: esquema objetivo 033 y pytest objetivo.
- `software_pa_clean_test_20260825`: restauración de 030 -> 031 -> 032 -> 033 -> fixture -> seed -> contrato SQL.
- `software_pa_history_final_test_20260825`: historia limpia real `001`, administrador seguro, `004`-`030`, fixture, rollback inducido 031/032, `031`-`033`, seed y contrato.
- `software_pa_seed_test`: esquema 033 y seed objetivo para conciliación.

Estado activo comprobado: versión máxima 033; 32 entidades, 2,478 municipios, 2 proyectos, 5 `proyecto_nucleo`, 4 parcelas, 10 afectaciones, 9 convenios, 2 trámites FIFONAFE y 2 pagos. El contrato SQL confirma ausencia de los nueve objetos legacy auditados.

## Comandos de validación ejecutados

- Git: `git branch --show-current`, `git rev-parse HEAD`, comparación con remoto, `git status`, `git diff --stat`, `git diff --check`, búsqueda de cambios en 001-030 y `git check-ignore` para Excel.
- Seguridad/backup: consultas de entorno/esquema/catálogo; `pg_dump -Fc`; `pg_restore -l`; restauración con `--exit-on-error`; ejecuciones 031/032 sin un gate para inducir rollback.
- Migración: `psql -v ON_ERROR_STOP=1` para 031, 032, 033, fixture y contrato SQL.
- Seed: `python scripts/seed_objective_demo.py` con entorno/base/confirmación explícitos.
- Base: consultas de `schema_migrations`, catálogo, objetos, columnas, constraints, triggers, vistas y conteos del seed.
- Backend: `configure_mappers()`, generación OpenAPI, `/health` y `python -m pytest -q`.
- Frontend: `npm run lint`, `npm run build` en contenedor y `npm run test:e2e` en imagen oficial Playwright.
- Estática: `rg` sobre código activo para símbolos legacy, `ST_Area` y `ST_Intersects`.

## Tests que pasan

- Fixture: 32/32 entidades y 2,478/2,478 municipios; carga idempotente; checksum SQL `99184affa3c50b18e7ea6531a3c0d8786e250befe40a507c459bd49ff5a5759b`.
- Backups: respaldo 030 limpio/restorable `57b4b2e1b659f9f91e276ca8dd09376ba491015ed855ff02975b0ba5071f28f3`; respaldo pre-reset restorable `351c6c34636326d3ec68d92c43de3b52bd336c3299cae28669f6d9d59dae0760`.
- Guards/rollback: 2/2 fallos inducidos esperados (031 y 032) dejaron la transacción previa intacta.
- Contrato SQL 031-033+seed: 3/3 ejecuciones aprobadas; cada ejecución revierte sus casos negativos.
- SQLAlchemy/OpenAPI: 39 objetos mapeados; 58 rutas; 87 operaciones.
- Pytest: 14 aprobados, 0 fallidos, 1 advertencia de deprecación Starlette/httpx.
- Frontend lint: 0 errores, 0 advertencias en 20 archivos/91 reglas.
- Frontend build: 1 aprobado, 144 módulos transformados.
- Playwright: 8 aprobados, 0 fallidos, 31.4 s en la ejecución final.
- Servicios activos: DB, backend y frontend saludables; `/health` 200 con esquema 33.

El seed validado contiene: 2 proyectos, 5 núcleos (ejidos y comunidad QA identificada), ORV/integrantes, padrón, sensibilización/caminamiento, 10 afectaciones colectivas/individuales, 4 parcelas/titulares, asamblea compartida, 9 convenios (COP, modificatorio, superficie adicional, obras complementarias, ampliaciones, permuta como modalidad y N:M), 2 FIFONAFE multiafectación con cuatro oficios, una indemnización, 2 pagos, documentos/versiones, geometría sintética QA y 14 trazas de fuente. El soporte QA tiene SHA-256 `dee42d98c899eb2dc8dba9f95326ded525de0b4ce752a82208880da79e679717`.

## Tests que fallan y causa

- El respaldo bruto inicial de 030 no restaura una FK legacy de bitácora por 19,386 referencias huérfanas de datos de prueba. Se conserva como evidencia forense y se generó/restauró un segundo respaldo que excluye sólo esos datos de bitácora; no bloqueó el reset.
- Las primeras ejecuciones Playwright dentro del contenedor mínimo fallaron por navegador y `libglib` ausentes. La imagen oficial Playwright eliminó el problema de entorno.
- La primera ejecución funcional en imagen oficial quedó 6/8 por dos aserciones E2E obsoletas; se corrigieron contra los indicadores/markup reales y la repetición quedó 8/8.
- La repetición de lint/build en el host falló con código 127 porque el host no tiene `frontend/node_modules`; las mismas dos tareas dentro del contenedor reproducible aprobaron.
- Una consulta auxiliar final de ausencia legacy perdió comillas en el shell; el contrato SQL equivalente aprobado comprueba la ausencia. No fue una falla del esquema.
- No quedan tests funcionales fallidos al cierre.

## Fase exacta en la que quedó

Las 25 fases solicitadas están COMPLETAS Y VALIDADAS. Gates A-H aprobados en el entorno local controlado. Primer gate pendiente: ninguno dentro del alcance de implementación.

## Siguiente acción concreta

Revisión humana del diff y, sólo con autorización explícita posterior, creación del commit. No ejecutar de nuevo el reset activo ni consolidar/squashear 001-033.

## Riesgos/bloqueos

- Bloqueos reales: ninguno para la implementación local solicitada.
- Riesgo conservado: el dump bruto 030 contiene corrupción referencial legacy en bitácora; usar el respaldo restorable verificado para recuperación funcional y conservar el bruto sólo como evidencia.
- Advertencia no bloqueante: Starlette TestClient reporta deprecación de integración con `httpx`; no afecta los 14 tests.
- Advertencia no bloqueante: Vite informa que Leaflet también se importa estáticamente, por lo que ese dynamic import no crea un chunk separado.
- No se realizó despliegue a producción/staging ni se validaron integraciones externas, acciones fuera del alcance y la autoridad concedida.

## Git status resumido

- Rama/HEAD: `feature/backend-logica` / `4a007fdb14ff0f9359f3c3b5f35d9a9ab5105069`.
- Estado: 74 archivos rastreados eliminados, 26 modificados y 29 archivos nuevos no rastreados (26 entradas `??` agrupadas por directorio en `git status`).
- Diff rastreado antes de este checkpoint: 100 archivos, 2,962 inserciones y 33,091 eliminaciones; los archivos nuevos no se incluyen en esa estadística.
- `git diff --check`: aprobado.
- Migraciones 001-030: sin cambios.
- `fuentes_locales/`: ignorado y sin cambios visibles en status.
- Push/merge/commit: no realizados.
