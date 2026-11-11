# Consolidación de ciberseguridad previa al Draft PR

Fecha: 2026-10-29, America/Mexico_City. Alcance oficial: **SSALFER (`frontend-ssalfer/`), FastAPI, PostgreSQL/PostGIS, Nginx y GIS/documentos**. React/Vite local es legado, no objetivo funcional obligatorio de QA. No se elimina o modifica en esta preparación.

## Dictamen: B. NO LISTO PARA PUBLICAR

Las regresiones aisladas del árbol local pasan, pero hay una incompatibilidad de integración comprobable con dev remoto. El remoto avanzó desde `683ff75613768de28a7127c7e33a6e2ef4fc40ff` a `e2699fe5c043996f7338bd63af3221957699bd65`, que retira frontend/ y actualiza Compose. SS-09 aún exige frontend/package.json, lock y Dockerfile; proyectando esas bajas en las lecturas del verificador se obtiene código 2/SOURCE_OR_ARGUMENTS_INVALID. No es un fallo funcional demostrado de SSALFER: es acoplamiento de herramientas/pruebas a un árbol legado que el destino ya no tiene.

**Rama local creada: ninguna. Commits nuevos: 0. SHA de commits creados: no aplica.** Rama activa dev, HEAD local igual al de referencia. No se hizo staging. La solicitud adjunta autoriza rama/commits sólo tras las precondiciones y ordena detener escrituras Git ante dependencias incompatibles/bloqueantes; se aplica esa excepción. No se efectuaron fetch/pull/merge/rebase/cherry-pick/reset/clean/stash/push/PR/despliegue.

La elección del frontend ya está resuelta por el solicitante: SSALFER. No se pide decidir de nuevo entre React y SSALFER. Se requiere una intervención posterior autorizada para acordar/alinear la base de integración y adaptar los controles offline a la arquitectura oficial, sin reintroducir React o perder las correcciones locales. No se crea/configura otro QA ni se toca el QA del compañero.

## Git: observado y no supuesto

| Referencia/estado | Resultado observado |
|---|---|
| Rama actual, HEAD, dev local |dev / 683ff75613768de28a7127c7e33a6e2ef4fc40ff |
| origin/dev local almacenada |683ff75613768de28a7127c7e33a6e2ef4fc40ff, desactualizada respecto de GitHub |
| dev remoto consultado sólo por API GET |e2699fe5c043996f7338bd63af3221957699bd65, 1 commit delante, 0 detrás de la referencia |
| Padre del commit remoto |683ff75613768de28a7127c7e33a6e2ef4fc40ff |
| Rama security/ss01-ss12-qa |No existe localmente; no creada por bloqueo |
| Índice staged |Vacío antes y después; 0 commits nuevos |
| Cambios iniciales |23 modificados, 70 sin seguimiento, 0 eliminados, 93 candidatos |
| Entrega documental de este turno |7 archivos nuevos; total candidato tras entrega: 100 (23 M y77 ??), confirmado en la comprobación final |

La consulta se realizó con el conector GitHub en modo lectura: [comparación](https://github.com/JPonce-23/Software-PA/compare/683ff75613768de28a7127c7e33a6e2ef4fc40ff...e2699fe5c043996f7338bd63af3221957699bd65), [commit remoto](https://github.com/JPonce-23/Software-PA/commit/e2699fe5c043996f7338bd63af3221957699bd65). No se descargaron refs/objetos al Git local. El indicador legacy protected:false de la respuesta de rama no excluye rulesets; políticas efectivas de organización siguen sin verificarse. No se almacenan autor/correo o datos personales del commit en esta entrega.

El remoto modifica Compose base/override/prod/ssalfer, env.js y documentación, y retira frontend/. Intersección con archivos modificados locales: docker-compose.yml y docker-compose.override.yml. Esto es solapamiento por archivo, **no un conflicto textual Git reproducido**: no se intentó merge ni se inventa su resultado. La incompatibilidad semántica del verificador sí se reprodujo con doble de lecturas según bajas remotas, sin ejecutar código remoto.

## Bloqueantes e incompatibilidades

| ID | Tipo/alcance | Evidencia | Resolución requerida, no aplicada |
|---|---|---|---|
| PRE-01 |Bloqueo de consolidación/publicación |Base local y origin/dev cacheadas no son dev remoto actual |Acordar base y actualización/integración en nueva fase autorizada; preservar el árbol. No forzar push o restaurar frontend retirado |
| PRE-02 |Bloqueo de herramientas/pruebas del destino |SS-09 SOURCES requiere frontend/package.json/lock/Dockerfile/.dockerignore; proyección de bajas remotas falla con código 2 |Hacer inventario legado opcional cuando ausente, mantener controles SSALFER obligatorios, actualizar fixtures/oráculos/inventarios y perfil. No imponer QA funcional React para aceptarlo |
| PRE-03 |Inconsistencia de documentos de decisión |Perfil SS-09 e informes históricos hablan de frontend pendiente/ambos candidatos |Conservar historia; el presente paquete fija SSALFER oficial. Actualizar descriptor operativo futuro y evidencia actual sin reescribir retrospectivamente conclusiones de auditoría |
| PRE-04 |Riesgo de regresión al transportar cambios |Compose locales comparten SS-03/04/06/10/11; remoto cambia servicios y quita frontend |Conservar --no-proxy-headers, --no-access-log, logging.json y variables nuevas al alinear; no copiar el Compose remoto encima de las correcciones |
| QA-DEP |Condición de pruebas nativas, no fallo de código probado |Faltan Starlette/SQLAlchemy/psycopg2/pglast en auditor local; integrado no ejecutado |El compañero usa su QA existente y autorizado. No instalar paquetes ni construir otra infraestructura aquí |
| QA-CARGA |Limitación conocida a observar, no corregida |Nginx SS-08 no fija client_max_body_size; default puede impedir cargas válidas API |QA verifica valor efectivo/413 y reporta; límites por ruta requieren corrección revisada, no ampliación indiscriminada |

Los controles no implementados (worker SS-02, rate limit SS-04, política SS-05, hardening efectivo SS-07, presupuesto integral mapa/SQL SS-11, serialización/recuperación/TOCTOU SS-12) son pendientes de alcance, **no PASS de QA**. No se requiere cerrarlos ficticiamente para describir una etapa parcial; integración de esa etapa necesita revisión y aceptación explícita de riesgos.

## Compatibilidad revisada

- SS-01/08: span/textContent y eventos conservados; CSP sólo Report-Only. Los 29 inline no se convierten en bloqueo; visual/mapa real sigue pendiente.
- SS-02/03: un único punto Popen GDAL con entorno restringido y presupuestos; módulos de límites/ZIP presentes. No se acreditan drivers/SO/red/CPU aislados.
- SS-04/08/10: peer y XFF exactos, comandos Uvicorn sin proxy headers y logs seguros preservados. Esquema/Host/Location HTTPS y error logs Nginx requieren QA, no se compensan relajando autenticación.
- SS-05: access.py/modelos/schemas sin cambios; no se implementa política nueva. Referencias/versiones compartidas conservan comportamiento actual.
- SS-06/12: validación previa, MIME canónico, SHA, staging exclusivo y conservación ante commit incierto coexisten; actualización de fixtures PDF es sintética y justificada.
- SS-07: no cambia migraciones/roles/grants; revisar locks de catálogo FOR SHARE y secuencias/definer en QA. No revocar UPDATE/TEMP para hacer pasar un checklist.
- SS-08/09: COPY selectivo SSALFER intacto; ignore backend preserva app/logging/scripts/init/migraciones, excluye tests de imagen runtime. QA con mounts ya existentes o artefacto de tests autorizado, sin exigir otro entorno.
- SS-10: middleware de diagnóstico añadido una vez; respuestas públicas/CSRF intactas. Driver/Starlette real y collectors pendientes.
- SS-11: arrays completos dentro del presupuesto y 413 sin truncamiento; CSV preparado por lotes a archivo privado, DB cerrada antes del streaming. No se implementó paginación de geometrías/mapa.
- SS-12: no mutex por proceso, max+1 sigue sin serialización; archivos publicados no se borran al fallar commit. Ficheros huérfanos y descarga por path siguen riesgos, no se eliminan automáticamente.

Se compilaron 38 archivos Python candidatos sin imports/bytecode, 3 JS/CJS mediante node --check, 8 JSON y 3 scripts shell con bash -n. Grafo de 43 módulos app y 128 aristas top-level directas: no se detectan ciclos inmediatos. El grafo que incluye imports dentro de funciones sí presenta ciclos GIS diferidos; no se etiquetan como imports rotos sin ejecución nativa. No se importó engine/main para “probar arranque”.

## Parches y doble aplicación

No se aplica ningún patch. Las funciones/headers críticos no aparecen duplicados: middleware seguro, store_version, validador, configuración de unidades y headers Nginx tienen una sola incorporación en los lugares previstos; las regresiones comprueban su resultado. Esto no reconstruye una historia Git inexistente de aplicaciones manuales.

| Patch archivado | Comprobación inversa sólo --check |
|---|---|
| `SS-01-CORRECCION-2026-10-28.patch` | Conforme al estado actual |
| `SS-02-ETAPA1-CORRECCION-2026-10-28.patch` | Conforme al estado actual |
| `SS-03-ETAPA1-CORRECCION-2026-10-28.patch` | Contexto superado por etapas posteriores |
| `SS-04-ETAPA1-CORRECCION-2026-10-28.patch` | Contexto superado por etapas posteriores |
| `SS-06-ETAPA1-CORRECCION-2026-10-28.patch` | Contexto superado por etapas posteriores |
| `SS-08-ETAPA1-CORRECCION-2026-10-29.patch` | Conforme al estado actual |
| `SS-09-ETAPA1-CORRECCION-2026-10-29.patch` | Conforme al estado actual |
| `SS-10-CORRECCION-2026-10-28.patch` | Conforme al estado actual |
| `SS-11-ETAPA1-CORRECCION-2026-10-28.patch` | Contexto superado por etapas posteriores |
| `SS-12-ETAPA1-CORRECCION-2026-10-28.patch` | Conforme al estado actual |

SS-03 fue seguido por SS-02 en gis_ingestion y por más variables Compose; SS-04 fue seguido por SS-10 en comandos/logging; SS-06 por SS-12 en servicio/pruebas; SS-11 por SS-06 en bloques de variables Compose. Los cuatro contextos superados no demuestran doble aplicación o pérdida. Los diez patches son evidencia histórica, **no un instalador secuencial ni sustituto del árbol actual**. No regenerarlos sobreescribiendo la historia, no aplicar ni revertirlos al compañero QA.

## Resultados locales reales de esta ejecución

| Suite/comprobación | Resultado actual | Límite |
|---|---|---|
| unittest tests/security |237 descubiertas, 231 aprobadas, 6 omitidas, 0 fallos |Sin BD/GDAL/servidor real |
| map-tooltip-security.cjs |33 aprobadas |DOM/API dobles, renderer local Leaflet |
| map-gis-rbac.cjs |4 aprobadas |RBAC/estado de mapa con dobles |
| gis-bootstrap-rbac.cjs |10 aprobadas |Bootstrap/roles simulados |
| map-performance.cjs |11 aprobadas tras repetición autorizada |Primer intento sandbox EPERM al hacer spawnSync git; repetido sólo git show y datos sintéticos, sin writes |
| report-limits-contract.cjs |Script aprobado, sin conteo TAP propio |Arrays/filtros/URLs/rechazos; no se inventa un número de tests |
| Verificador SS-09 local |Código0, 20 vendors coinciden; assessment=incomplete_requires_qa |No SCA/build/SBOM de instalados |
| Proyección disponibilidad archivos remoto |Código2; primer faltante frontend/package.json |Reproducción de acoplamiento, no merge ni despliegue |
| git diff --check / sintaxis |Conformes |No sustituye nginx -t/arranque/import real |

Total Node TAP: 58 aprobadas, más un script de contrato aprobado. El primer fallo de ejecución de map-performance fue restricción de sandbox, no regresión; se conserva la evidencia y la repetición no ocultó ni cambió código. F05_EVIDENCE_DIR/F05_BASELINE_ONLY se retiraron sólo del proceso de prueba para evitar escritos. No se reutilizan cifras históricas sin ejecutar.

| Módulo unittest | Total | Aprobadas | Omitidas |
|---|---:|---:|---:|
| `test_auth_origin_security.py` | 32 | 32 | 0 |
| `test_document_starlette_pending.py` | 2 | 0 | 2 |
| `test_document_storage.py` | 24 | 24 | 0 |
| `test_document_validation.py` | 28 | 28 | 0 |
| `test_gis_resource_limits.py` | 32 | 32 | 0 |
| `test_gis_subprocess_environment.py` | 17 | 17 | 0 |
| `test_http_deployment_security.py` | 15 | 15 | 0 |
| `test_postgresql_privilege_audit.py` | 21 | 20 | 1 |
| `test_reporting_resource_limits.py` | 23 | 23 | 0 |
| `test_safe_logging_security.py` | 24 | 21 | 3 |
| `test_supply_chain_offline.py` | 19 | 19 | 0 |

Omisiones: 2 Starlette (incluye prueba que demuestra el TOCTOU actual, no aceptación de un arreglo), 1 gramática PostgreSQL/pglast, 3 SQLAlchemy/psycopg2 de logging. No se instalaron dependencias. Las seis pruebas PostgreSQL SS-12 preparadas no se ejecutan ni importan en esta suite. No se ejecuta pytest/collect-only con backend/conftest, Docker, Nginx, HTTPS, navegador o API/BD real.

## Revisión de seguridad del paquete

Revisión local del conjunto candidato: 0 paths de .env/material de claves/BD/backups detectados, 0 archivos mayores de 5 MiB, sin coincidencias de las familias revisadas de claves privadas/tokens GitHub/AWS/DSN con credenciales. No se imprimen valores ni se accede a archivos ignorados. Las fixtures nuevas son sintéticas y no hay binarios documentales/volúmenes añadidos. **No es un scanner de secretos ni prueba exhaustiva de ausencia**: segunda revisión humana de contenido/staging y clasificación institucional antes de publicar.

No hay migraciones, access.py, models.py, schemas.py, config.py o versiones requirements/Node modificados. El índice inicial está vacío; no se incluyeron secretos en commits porque no se creó ninguno. Evitar git add . o staging de uploads, .env, backups, capturas de expedientes/logs completos. Documentación de vulnerabilidades/arquitectura puede ser sensible aunque no contenga contraseñas: confirmar visibilidad/revisores del PR.

## Inventario completo de los 93 candidatos de entrada

M=modificado tracked; ??=nuevo sin seguimiento. SHA-256 fija los bytes locales revisados, no autenticidad upstream ni commit instalado. La clasificación permite staging explícito posterior; **nada de esta tabla fue staged/committed ahora**.

| Estado | Archivo | Categoría | SHA-256 local revisado |
|---|---|---|---|
| M | `backend/.dockerignore` | configuración/build | `eec6ba694e1b109285adf9802d8aa3e1a5c33dac9e1df90bd0643e5279f9978b` |
| M | `backend/Dockerfile` | configuración/build | `b816f56ebff741e408bf0d6a63ce6543b26169c731d585dee8e026882899257e` |
| M | `backend/app/database.py` | código productivo | `8735feda6d5a1fc37f3e328e9cf8d5dcb3ea40504ab0e9430640422d436b1eda` |
| M | `backend/app/main.py` | código productivo | `f76afb7fa9003a983ade3092451d6e7cf45ae5ecfa1fadf718d168ab18dc865e` |
| M | `backend/app/routers/documents.py` | código productivo | `2ad8106a2c6b94384b633efc01555457e5222179b4b3644617c14a85e6372e56` |
| M | `backend/app/routers/reporting.py` | código productivo | `9bbb785dced4b4eaf610caf98b53eabe11f5dfba5a7ce5a8abf5117b71cd788e` |
| ?? | `backend/app/safe_logging.py` | código productivo | `f316d0b6d898314bf9cae546172f980d28b33bb186904e182ac56fe0c1982cd8` |
| M | `backend/app/services/authentication.py` | código productivo | `c6aa445c565db2c7b536e596ef3dd1a0d0cab8820ee2d6fa3bda904ec0ba1f09` |
| ?? | `backend/app/services/document_storage.py` | código productivo | `4c9f70f526c078c4f4a1fc15729654f1eed7409f30880c378fc90ad46adae541` |
| ?? | `backend/app/services/document_validation.py` | código productivo | `ca81df595d85419406d7f7a00ad6a90499ff1bbc1dfd332cdb5d249f3f6a277c` |
| M | `backend/app/services/documents.py` | código productivo | `a9df440899a0d1a121a6821c461a3082204b8bc20d583c80b1cde27700939dc9` |
| M | `backend/app/services/geospatial_imports.py` | código productivo | `63b6df6caff39f6154f3e2713285800fb10fc8c4158162d5c7ce9581257d66b9` |
| ?? | `backend/app/services/gis_archives.py` | código productivo | `ac2a1adccb60bf82b73568cabcb78dd5eaf2b9fb043d72668008175229e74ba2` |
| M | `backend/app/services/gis_ingestion.py` | código productivo | `dae7019a8e0520cd928779e3565bec4b02c9b012f799075e1d1be32e2bca6339` |
| ?? | `backend/app/services/gis_limits.py` | código productivo | `a5063763a87e9e92a3a6376436b9322bda2268e07c700592de505ec6bb294aad` |
| M | `backend/app/services/gis_reconciliation.py` | código productivo | `9f8c4bf1b37e3354ed70b33e35e0550bdbd97a51373d722a336ffdd09a1d1977` |
| ?? | `backend/app/services/report_limits.py` | código productivo | `94d994a42e40793c6b2396c2615aedbc7406ca32db5f2b85e78d85a4d22d79f7` |
| ?? | `backend/app/services/request_origin.py` | código productivo | `defab18911b29fd771b2ec7c7b895a2b29e62a16c00b9b98c545e62f7bc95943` |
| ?? | `backend/logging.json` | configuración/build | `46c2cf1b8ca2c89bf446bb85b87469281179c396f4509b4b4a5e98205955221f` |
| M | `backend/scripts/create_admin.py` | herramienta administrativa (logs) | `5fb2d76a9aefc40ce957c04c7b64ef1d115b62cbdf0c8000c4e7ad95d51f8e13` |
| M | `backend/scripts/import_catalogo_nucleos_ran.py` | herramienta administrativa (logs) | `d712812bb8f144b2ccaa626329ac9e165597e74303a60f487fc036ee9d9b34b5` |
| M | `backend/scripts/reconcile_gis_migration_lineage.py` | herramienta administrativa (logs) | `fed52eea17910ffa4c0ca475223b30b259b3e26b8b05033cb60e37d5b91c8457` |
| M | `backend/scripts/sync_catalogo_ran.py` | herramienta administrativa (logs) | `eb8590c40b9e8a65616c22766c6d4bb961592fc852896fbef809c5c740d06adb` |
| ?? | `backend/tests/_document_samples.py` | prueba/fixture sintético | `2f65ec5f698d0f639e9eaa887b73f5ccae824394b27c1b2e153795be662f37ad` |
| M | `backend/tests/test_document_targets_039.py` | prueba/fixture sintético | `71627685a865ed5701f6f09807505b8b8b871e671b3c8eca31b6ba14c9360265` |
| M | `backend/tests/test_documents_dashboard.py` | prueba/fixture sintético | `09667044b9fe5f6f2ceaa4a55c532d2d409ef08c122dabd943c0ae32a1bfee09` |
| M | `backend/tests/test_frontend_read_models.py` | prueba/fixture sintético | `22cb1fedc535fefda07f2156b05944ca16e7b8d6f507bfa9e47629107e035b68` |
| M | `docker-compose.override.yml` | configuración/build | `f3d0aeaf2c18cea7a085fc6cdd70ee96fdcf0b2db6e24a2797203bd0950645d2` |
| M | `docker-compose.yml` | configuración/build | `c8ff985a99895e92ee3b8189fe96a83e7e353fe1e7af383d7a4841ec3514e0b6` |
| ?? | `docs/security/AUDITORIA-SEGURIDAD-2026-10.md` | documentación/evidencia | `81c5711fbb9e2d0b320c8877ca024abd2049d2b80421f4c475368ebed6e480b1` |
| ?? | `docs/security/CHECKLIST-AUDITORIA-SERVIDOR.md` | documentación/evidencia | `a4798de8de9a006956a3d1ea4ec07de971031f1c27449772477f56a1b7560333` |
| ?? | `docs/security/COBERTURA-PRUEBAS-SEGURIDAD.md` | documentación/evidencia | `faac2a907f2f023432d751285497fd84d52d77076264af127beb7ab6984ef5cd` |
| ?? | `docs/security/MATRIZ-ENDPOINTS-RBAC.md` | documentación/evidencia | `264de5ee448d559e8be8bdc992dc900f659a549c84d1190d8035c7f9a5c18a08` |
| ?? | `docs/security/MATRIZ-RIESGOS-SEGURIDAD.md` | documentación/evidencia | `3ab2a9cf5d60380aef27e2afd5e71e6dc53b9df5722aab10d13a386975484d05` |
| ?? | `docs/security/PLAN-REMEDIACION-SEGURIDAD.md` | documentación/evidencia | `90148afd69ffb0f2bd563ced087983b7506a9f5ce9b6c3847108b95a4ad4ebf0` |
| ?? | `docs/security/SS-01-CORRECCION-2026-10-28.patch` | parche histórico, no aplicar | `00d04c2e9e5bb5bf4456b766caa04c900ac1f71d40f674ae397b9f47c056c0bf` |
| ?? | `docs/security/SS-01-VALIDACION-FINAL-2026-10-28.json` | documentación/evidencia | `adae5cde7113c4517771366f3bdb1b85c11870402bcb26ce25faed6901b5680e` |
| ?? | `docs/security/SS-01-VALIDACION-FINAL-2026-10-28.md` | documentación/evidencia | `7b6f5f4f756814cd35add6209a3b45d102c5a02aae9960f780165f7604f4fe99` |
| ?? | `docs/security/SS-02-ETAPA1-CORRECCION-2026-10-28.md` | documentación/evidencia | `59697a855d7aeb9140b73d30582c824b9fe376181168011c6e8cf444e07f8e50` |
| ?? | `docs/security/SS-02-ETAPA1-CORRECCION-2026-10-28.patch` | parche histórico, no aplicar | `2b26a4d9e34b590caf9ebaf03d59a6e8d2cfda3c147efe8a2ec9e0475f2bd196` |
| ?? | `docs/security/SS-02-ETAPA2-DISENO-WORKER.md` | diseño pendiente | `53f166fed04da009227de52b992140791051dec495f89c19a5cf41898549d109` |
| ?? | `docs/security/SS-03-ETAPA1-CORRECCION-2026-10-28.md` | documentación/evidencia | `689de32555c603fc6977d2d0bfcefde3477c6848f654d24bc9f9740a5598cb2a` |
| ?? | `docs/security/SS-03-ETAPA1-CORRECCION-2026-10-28.patch` | parche histórico, no aplicar | `775c7c53ee9b41e394fc20f554b057e973467a8851d9d595eaa33267b124e59c` |
| ?? | `docs/security/SS-04-ETAPA1-CORRECCION-2026-10-28.md` | documentación/evidencia | `78f48fafb70241f491534479132e93670ce1358f793be8c817b30c26341438dd` |
| ?? | `docs/security/SS-04-ETAPA1-CORRECCION-2026-10-28.patch` | parche histórico, no aplicar | `45037cbdffdcea67798ab237efb72845cdd2c21a4ab05f76105a155afa52f732` |
| ?? | `docs/security/SS-05-ANALISIS-POLITICA-DOCUMENTAL-2026-10-28.md` | diseño pendiente | `32eec8122cbfc9ff3679b93e7e589422c9dbfeabfb0e1f9c1a1c6b35d10f02fa` |
| ?? | `docs/security/SS-05-MATRIZ-DECISION-RBAC-2026-10-28.md` | diseño pendiente | `32e9703717509d61bbcc70d7c4b2fcb4e8c195c153622a1122213ab451971f04` |
| ?? | `docs/security/SS-05-PLAN-IMPLEMENTACION-2026-10-28.md` | diseño pendiente | `767647e96e18264d5b0d27cf976c0b535771a9e2d442a94b662d00d284cd5bfb` |
| ?? | `docs/security/SS-06-ETAPA1-CORRECCION-2026-10-28.md` | documentación/evidencia | `6c174c3d564b7a110cf95edf19b18ed80efd59a542ff6070a58f3fd9ae583654` |
| ?? | `docs/security/SS-06-ETAPA1-CORRECCION-2026-10-28.patch` | parche histórico, no aplicar | `cd90edebe42d6e1ef0655b4b2252cff9940fef347366c8fec1e38ce493f8afd8` |
| ?? | `docs/security/SS-07-ETAPA1-AUDITORIA-PRIVILEGIOS-2026-10-28.md` | documentación/evidencia | `33c083d880279a031ea7af00a8337d2bc8eb78dd5f7712313c959ce97b1e564a` |
| ?? | `docs/security/SS-07-MATRIZ-PRIVILEGIOS-2026-10-28.md` | documentación/evidencia | `63e2e0eaed30efa86b14e0be1d4896ca6ba76ab9548ab3112f475cca481be5a2` |
| ?? | `docs/security/SS-07-PLAN-HARDENING-POSTGRESQL.md` | documentación/evidencia | `d7704ac6c4bb7d6e2806c895a179a4b498ff35a7df60f5f96bf7e12410205c73` |
| ?? | `docs/security/SS-08-ETAPA1-CORRECCION-2026-10-29.md` | documentación/evidencia | `5dcd18feaa73402bfd3ad778dbaed075901708760852b341311522c78c807c71` |
| ?? | `docs/security/SS-08-ETAPA1-CORRECCION-2026-10-29.patch` | parche histórico, no aplicar | `76ed20b49cb77045b969971d4576ac8d8a9fc7cba204173e5fae29e3c683dad7` |
| ?? | `docs/security/SS-08-INVENTARIO-DESPLIEGUE-2026-10-29.md` | documentación/evidencia | `4744af774c6f62881391c851a06b22b871d189c31305a3765ac7a947d451e9fb` |
| ?? | `docs/security/SS-08-MATRIZ-CABECERAS-RUTAS-2026-10-29.md` | documentación/evidencia | `dc406dce86b33843bdad132dd29f5c264bd346b09a81f4a6a91e7869dcdc17b5` |
| ?? | `docs/security/SS-09-ETAPA1-CORRECCION-2026-10-29.md` | documentación/evidencia | `9eb7b446d9496f515209d3879c1e5199cd7549228c966d2021e48f5e15376b43` |
| ?? | `docs/security/SS-09-ETAPA1-CORRECCION-2026-10-29.patch` | parche histórico, no aplicar | `30e9d083334fcb9a4253041dc8faba2d753d97ba25a76ea5d2b08c0600a6df44` |
| ?? | `docs/security/SS-09-INVENTARIO-DEPENDENCIAS-2026-10-29.md` | documentación/evidencia | `426a29b3df8f90c992141d730170bcf7024623be64a6549f51f469e6fa68ae8e` |
| ?? | `docs/security/SS-09-PLAN-CADENA-SUMINISTRO.md` | documentación/evidencia | `c3378869097bbe0f545009335b7515d4c4dda7f86836a96e21d9cf5d1198f14d` |
| ?? | `docs/security/SS-10-CORRECCION-2026-10-28.md` | documentación/evidencia | `ad1ed3e6e52b731efd17b8691c1157d8b76fdcb22bfd20b1ecadbe5563e80fe7` |
| ?? | `docs/security/SS-10-CORRECCION-2026-10-28.patch` | parche histórico, no aplicar | `c90d5c2482e79ae489026b0a253568e273ea629000abc5bf9e0799134ca45f1e` |
| ?? | `docs/security/SS-11-ETAPA1-CORRECCION-2026-10-28.md` | documentación/evidencia | `4dad2d78d26c456293bc61351baf39c9f3a1c4e17a6aebe1ccf48e1abb69c3d2` |
| ?? | `docs/security/SS-11-ETAPA1-CORRECCION-2026-10-28.patch` | parche histórico, no aplicar | `02a5a7a1399672ff0b2b9c43b0ce3b776155826c8ae4e1d68d7562b972bbdcbf` |
| ?? | `docs/security/SS-12-ETAPA1-CORRECCION-2026-10-28.md` | documentación/evidencia | `39f61e15b4e30892fde7ee76477c86af7faad1157badade1beeb567f3911ffb0` |
| ?? | `docs/security/SS-12-ETAPA1-CORRECCION-2026-10-28.patch` | parche histórico, no aplicar | `86a2d2f2d922edea5594aa6162de3ad8ec8bcf24d11f0aa5007c74f7940efc9e` |
| ?? | `docs/security/ss07/config-ejemplo.json` | inventario/configuración de diseño | `a924deca778f680a0d7ae1fd5853e091c5dd65cf260f1a9a0f723d36c0f65d7a` |
| ?? | `docs/security/ss07/consultas-privilegios.sql.in` | herramienta/datos de auditoría | `a62acf5f8eb0934c6f97ea41e63011570dc12c2e488e85e2b4e928af213a26d5` |
| ?? | `docs/security/ss07/inventario-estatico.json` | inventario/configuración de diseño | `ad683908e26c3050c885e27a77a47efc06d878989635215462edbc987ce85598` |
| ?? | `docs/security/ss07/preparar_verificador.py` | herramienta/datos de auditoría | `78cc7ba2dea04e3ae64b619a110f285d0270f517aa985ba829f5aadd184b2900` |
| ?? | `docs/security/ss08/inventario-recursos.json` | documentación/evidencia | `b2c6031f6357f41f64b52209dbd518febd84ea1108f4243002a57fd107fa1e23` |
| ?? | `docs/security/ss09/inventario-declarado.json` | inventario/configuración de diseño | `925cbccd48785e6f095acce6fcea5093ca3ea9cf6807002f152dc641bc29523c` |
| ?? | `docs/security/ss09/perfiles-despliegue-propuestos.json` | inventario/configuración de diseño | `7495ae541b29c5d8c98582e89356bcd5cac81bfd054f286ba3720846c210762a` |
| ?? | `docs/security/ss09/vendors-sha256.json` | inventario/configuración de diseño | `be6a58964203dbb5fa46fd3ab9478183a12f4262b0a7aac63bc80b8ccc4b0a30` |
| ?? | `docs/security/ss09/verificar_cadena.py` | herramienta/datos de auditoría | `b396fb3cae4eb0cdb3025147a0090d97ce23e871509016169096de2b8d1b7e46` |
| M | `frontend-ssalfer/deploy/Dockerfile` | configuración/build | `af0ee10c1e87274745b7f61c554933b536272da21c00345c537ba07169c4e4bc` |
| M | `frontend-ssalfer/deploy/nginx.conf` | configuración/build | `f6f91064d3552239ac17f5968738f0105ff2fea17ea74455314bf50e90a44b9b` |
| M | `frontend-ssalfer/js/mapa.js` | código productivo | `2d051e4204701a9bb63775422bc882f11b10c138f7ee8f577c0a9d94b229bfab` |
| ?? | `tests/frontend-ssalfer/map-tooltip-security.cjs` | prueba/fixture sintético | `1ae6ad7471ef4a565a65d39d3ed84a8165a2511ae08279f365e224f528b0d192` |
| ?? | `tests/frontend-ssalfer/report-limits-contract.cjs` | prueba/fixture sintético | `74eeec2f52ca372445eeed3486499b987e1a11b2f649c16c654e0fb44a93cde1` |
| ?? | `tests/qa/test_document_publication_postgresql.py` | prueba/fixture sintético | `2b1f89888c6182acd463915e22ebf696103af56e21256a0f93e04c919684f1dc` |
| ?? | `tests/security/test_auth_origin_security.py` | prueba/fixture sintético | `62efe433284cf009262d883d8b4d32e8f02fa16a314e331bf61677c043e3c7b8` |
| ?? | `tests/security/test_document_starlette_pending.py` | prueba/fixture sintético | `fccba68a1ccffc4155dd567dd04d4cef8dcea1986d03ac5b814d5093797a620a` |
| ?? | `tests/security/test_document_storage.py` | prueba/fixture sintético | `bc177a4572c2932094fccb5097f87adac3c40ac725c130d246a764ec9d1a39c0` |
| ?? | `tests/security/test_document_validation.py` | prueba/fixture sintético | `341b18e6476ba36fe4db454708e03b4a0221d7aa8955af1e165cb7aca1271f56` |
| ?? | `tests/security/test_gis_resource_limits.py` | prueba/fixture sintético | `435763a2b4bd72ffb646488a13460bc35581a79f5ca8f92b04d27afc35ca3dea` |
| ?? | `tests/security/test_gis_subprocess_environment.py` | prueba/fixture sintético | `504295d50195ddcc81c34607d72bfefdfb14fa25b7db15689b3c6a6a100f8829` |
| ?? | `tests/security/test_http_deployment_security.py` | prueba/fixture sintético | `2bf6e26f50632bb1be1596d66da2571ce9dcf4c668b34ccb945e4bcfe4084c26` |
| ?? | `tests/security/test_postgresql_privilege_audit.py` | prueba/fixture sintético | `daef8ffe97edf9a56975f1d25f97792d0e08bf750020f127648383db3b0af10a` |
| ?? | `tests/security/test_reporting_resource_limits.py` | prueba/fixture sintético | `806225b1074fdc61bf2565ca3b57fdcc43d89170b746ad24db09ff67e0d11dfa` |
| ?? | `tests/security/test_safe_logging_security.py` | prueba/fixture sintético | `6a9a1fb0cf1cdc4167592e421283b416c9a06288ee228653cf571fc190bf1875` |
| ?? | `tests/security/test_supply_chain_offline.py` | prueba/fixture sintético | `49106e7bb133ae65aba491be6d10bdc669c67ae2eddcf84727885d65d6073329` |

Se añaden exclusivamente los siete entregables de consolidación: CONSOLIDACION-PRE-PR-SEGURIDAD.md, MATRIZ-VALIDACION-QA-SS01-SS12.md, GUIA-ENTREGA-COMPANERO-QA.md, DRAFT-PR-CIBERSEGURIDAD.md, REPORTE-INCIDENCIAS-QA.md, PLAN-INTEGRACION-SEGURIDAD-GIT.md y MATRIZ-CIERRE-HALLAZGOS.md. Son documentación nueva, sin hash autorreferencial dentro del propio inventario; el futuro commit congelará el conjunto. La guía usa el nombre ASCII de la solicitud adjunta vigente.

## Próximo paso permitido sólo tras revisión

Resolver PRE-01–04 en una intervención autorizada, sin retirar legado local o modificar SS-05/07 por cuenta propia. Reejecutar verificaciones sobre el árbol candidato alineado; sólo entonces rama/commits explícitos y registro de SHA reales. El compañero valida el SHA futuro en su QA existente siguiendo la matriz. Publicación de rama/PR y cualquier integración requieren autorización posterior. **Cero cambios de código productivo realizados en esta consolidación.**

## Comprobación final de preservación

Se compararon SHA-256 de los **745 archivos preexistentes incluidos en el snapshot de esta intervención**: ninguno cambió ni desapareció. Sólo se añadieron los siete documentos enumerados; no se incluyeron archivos ignorados sensibles en esa lectura. El conjunto candidato final contiene **100 archivos: 23 modificados y 77 sin seguimiento**, índice vacío, rama activa `dev` y HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff`. `git diff --check` no reportó errores. Los siete documentos son las únicas escrituras al repositorio de esta preparación; no hubo cambios productivos, rama nueva ni commits.
