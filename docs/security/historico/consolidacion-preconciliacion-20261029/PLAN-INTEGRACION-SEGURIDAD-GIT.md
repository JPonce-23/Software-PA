# Plan de integración Git de ciberseguridad

Fecha: 2026-10-29. Rama propuesta security/ss01-ss12-qa → dev. Frontend oficial SSALFER; React legado no se modifica/retira aquí ni se convierte en aceptación funcional obligatoria.

## Operaciones reales de esta entrega

Rama creada: **ninguna**. Commits nuevos: **0**. SHAs/descripciones de commits creados: **no aplica**. Índice vacío. Activa dev con HEAD 683ff75613768de28a7127c7e33a6e2ef4fc40ff. No se modifican refs, remoto o worktrees ajenos. Se generan sólo siete documentos; las fuentes/pruebas anteriores se preservan por hash.

La autorización de rama/commits es condicional. Se detienen esas escrituras por PRE-01–04/INT-001–002: dev GitHub ya es e2699fe5c043996f7338bd63af3221957699bd65, distinto al origin/dev local cacheado, y elimina dependencias fuente obligatorias de SS-09. No hay duda sobre el frontend oficial; el bloqueo es transporte/coherencia de herramientas con el destino. No se elimina el legado local ni se aplica el retiro remoto.

No se ejecutan fetch/pull/merge/rebase/cherry-pick/reset/clean/stash, push, PR o despliegue. No se proponen como pasos automáticos de esta fase. La futura alineación con el remoto necesita autorización/procedimiento independiente y nueva comprobación de vigencia; no se puede fabricar una rama basada en objetos remotos que aún no se incorporaron localmente.

## Precondiciones antes de crear rama y commits

1. Acordar base de integración real con el mantenedor y autorizar, aparte, el procedimiento de alineación permitido. Conservar snapshot/diff y todos los untracked revisados; no perder trabajo con comandos destructivos.
2. Adaptar verificador/fixtures SS-09 para que la ausencia de frontend/ legado no bloquee inventario SSALFER. Mantener inventario histórico de React como evidencia opcional, no restaurar archivos retirados por otro cambio ni alterar versiones.
3. Ajustar descriptor/metadata vigentes a SSALFER oficial y actualizar su snapshot de inventario/pruebas con trazabilidad, conservando informes históricos. El perfil operativo/TLS/servicios auxiliares lo valida el responsable QA, no reabrir elección de frontend.
4. Revisar Compose base/override/prod/ssalfer: preservar no-proxy-headers/no-access-log/logging y variables REPORT/DOCUMENT/IMPORT; no usar versiones remotas sin portar endurecimiento. Confirmar que se seleccionará SSALFER sin iniciar React/pgAdmin accidentalmente.
5. Ejecutar suites aisladas en la base candidata efectiva, corregir únicamente lo autorizado y documentar incidentes. Ninguna prueba fallida se oculta en historia o se convierte en skip para publicar.
6. Confirmar procedencia/allowlist (93 candidatos originales, siete docs), ausencia de datos/secretos y nombre de rama libre. Este turno no detectó cambios ajenos; si aparecen, separarlos sin pérdida o detenerse.
7. Revisar hooks/configuración de commits antes de ejecutarlos para evitar scripts, instalaciones o conexiones implícitas. No saltarse hooks con --no-verify por conveniencia; resolver efectos/autorizaciones con el mantenedor.

## Agrupación propuesta, no historial ejecutado

Se priorizan commits funcionalmente coherentes frente a 12 commits artificiales. Archivos compartidos contienen varias etapas: no reconstruir versiones intermedias riesgosas para simular un commit por SS. Los títulos describen endurecimiento parcial, no resolución total.

| Grupo futuro | Título propuesto / alcance | Archivos productivos/config/test principales | Dependencia |
|---|---|---|---|
| G00 |chore(security): align offline QA controls with SSALFER target |Adaptación autorizada de ss09/verificador/tests/descriptores/inventario y Compose según base real |Bloqueante previo; **no implementado ni committed**. No retirar React aquí |
| G01 |fix(security): SS-04/SS-10 preserve peer trust and safe diagnostics |authentication.py, request_origin.py, database.py, main.py, safe_logging.py, logging.json, 4 scripts CLI de logs, backend/Dockerfile y dos Compose compartidos; tests auth_origin/safe_logging y docs respectivas |Fundación para storage/GDAL/logging. El commit debe declarar plumbing de límites de SS-03/06/11 presente en Compose, sin fingir autoría de un sólo SS |
| G02 |fix(security): SS-02/SS-03 constrain GDAL environment and GIS budgets |gis_ingestion.py, gis_limits.py, gis_archives.py, geospatial_imports.py, gis_reconciliation.py; 2 tests GIS;docs SS-02/03/worker |Tras G01 y variables compartidas; entorno y parser no se separan artificialmente en un módulo roto |
| G03 |fix(security): SS-06/SS-12 validate and publish document versions safely |documents service/router, document_validation.py, document_storage.py;tests document_validation/storage/Starlette, QA protocolo;helper PDF y 3 tests backend adaptados;docs SS-06/12 |safe_logging de G01. Conservar expectativa SS-12 de publicados retenidos; no volver a compensación insegura de SS-06 anterior |
| G04 |fix(security): SS-11 bound report reads and CSV staging |routers/reporting.py, report_limits.py, test_reporting_resource_limits.py, report-limits-contract.cjs;docs SS-11 |G01 runtime/logging; sin cambios de mapa/SQL global |
| G05 |fix(security): SS-01 render Leaflet labels as text |mapa.js, map-tooltip-security.cjs, validación/parche históricos SS-01 |Sin nuevas dependencias; incluir sólo la corrección local conocida |
| G06 |fix(security): SS-08 harden SSALFER HTTP configuration |deploy/nginx.conf y Dockerfile, test_http_deployment_security.py, inventario-recursos.json ydocs SS-08 |G01/G03/G05; CSP RO y contrato descarga preservados |
| G07 |docs(security): SS-07 prepare read-only privilege audit |docs SS-07 yss07 SQL/preparador/config/inventario, test_postgresql_privilege_audit.py |Sin GRANT/REVOKE/migraciones; artefactos offline completos |
| G08 |chore(security): SS-09 add offline supply-chain controls |backend/.dockerignore, ss09/verificador/vendors/perfiles/inventario, test_supply_chain_offline.py ydocs SS-09 |G00/G06. No incluir snapshots obsoletos como perfil actual o modificar vendors/dependencias |
| G09 |docs(security): SS-05 specify shared document policy |Los 3 documentos de política/matriz/plan SS-05 |Sin autorización productiva; no decir fix de vulnerabilidad |
| G10 |docs(security): consolidate audit evidence and QA handoff |6 informes originales y estos 7 entregables; restantes parches/evidencias se agrupan con su SS |Último: registrar SHAs reales y alcance de la base candidata, no títulos hipotéticos como commits creados |

Cada grupo incluye sus documentos/pruebas y patch histórico correspondiente cuando corresponda. Los 93 paths del inventario son la allowlist de entrada; cualquier archivo nuevo de una corrección posterior necesita revisión adicional. Un archivo compartido se incluye una sola vez en un grupo conjunto explicado. No aplicar patches para componerlo, no crear commits vacíos o que aparenten cerrar SS-05/07.

## Procedimiento local futuro, sólo tras resolver bloqueantes

Comprobar otra vez status/branch/log/diff/base/índice. Si security/ss01-ss12-qa existe, verificar identidad y alcance en lugar de sobreescribirla. La creación sugerida **no ejecutada** es `git switch -c security/ss01-ss12-qa` desde el estado local acordado, preservando el working tree. No cambiar dev mediante commits directos.

Para cada grupo: usar `git add --` con lista exacta revisada y staging selectivo de hunks sólo si es seguro; revisar `git diff --cached --name-status`, `git diff --cached --check` y contenido staged, incluidas altas. Nunca `git add .`, selección ciega de todo docs/security o credenciales/volúmenes. Validar sintaxis e imports de la etapa y pruebas pertinentes antes del commit. La suite completa y herramientas que dependen de varios grupos se validan al final, no se despliega un commit intermedio.

Crear commit con título y cuerpo sobre alcance real y controles pendientes, revisar git show --stat y el historial, registrar SHA. No hacer commit de resultados de otro SHA ni mezclar cambios ajenos. Si falla una prueba después del commit, parar preparación de publicación, abrir incidencia y añadir corrección autorizada con nuevo commit; no rebase/reset/force o maquillaje de historial.

## Validación final de commits y publicación

- Inventario staged/commits coincide con allowlist aprobada y las nuevas correcciones documentadas; nada queda omitido por estar untracked.
- Diff acumulado conserva controles anteriores y no incluye frontend legado reintroducido, migraciones/roles cambiados o datos institucionales.
- Hashes de vendors y migraciones, suites aisladas y QA del alcance conforme a sus gates; errores/skips registrados.
- Reportes/PR actualizados con rama y SHAs realmente creados, base dev vigente y lista de commits, sin autorreferencia de SHA inventada.
- Responsable autoriza publicación de rama y creación Draft PR como acción separada. **No ejecutarlo en esta etapa**. No activar auto-merge/deploy o solicitar pruebas funcionales React.

## Cuatro estados distintos

**Preparado para QA:** código/commits revisables y coherentes con base, pruebas locales conformes y guía completa. Hoy hay guía/pruebas, pero PRE bloquea preparación final.

**QA satisfactoria del alcance implementado:** evidencia integrada del SHA entregado, negativos/regresiones y omisiones justificadas. Hoy NOT RUN.

**Preparado para integración:** QA, revisión técnica, aceptación de riesgos y aprobaciones funcionales imprescindibles. Hoy no.

**Hallazgo cerrado:** controles requeridos realmente implementados y evidencia de eficacia, no sólo un PR/commit/suite aprobados. Hoy no se cierra ninguno.
