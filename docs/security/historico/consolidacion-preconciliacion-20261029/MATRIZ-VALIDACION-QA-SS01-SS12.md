# Matriz de validación QA SS-01 a SS-12

Fecha: 2026-10-29. Base local 683ff75613768de28a7127c7e33a6e2ef4fc40ff; remoto observado e2699fe5c043996f7338bd63af3221957699bd65. **SSALFER oficial; React/Vite legado sin pruebas funcionales obligatorias para este PR.** Candidato aún sin rama/commit nuevo: no ejecutar una validación como si existiera un SHA publicado. [Consolidación](CONSOLIDACION-PRE-PR-SEGURIDAD.md), [cierre](MATRIZ-CIERRE-HALLAZGOS.md).

Severidades originales cualitativas: 3 altos (01/02/03), 8 medios y1 bajo (12); no se recalculan CVSS sin evidencia. PASS de un caso no cierra el hallazgo. Estados de ejecución: PASS, FAIL, BLOCKED, NOT RUN. Estado de control separado: implementado parcial/local, diseño pendiente, no implementado, QA validada, cerrado. **Hoy no hay QA integrada validada ni hallazgo cerrado por esta entrega.**

## Matriz funcional/técnica por hallazgo

| SS / gravedad original | Riesgo y archivos principales | Implementado y evidencia local actual | Pendiente explícito, no marcar PASS | QA / dependencias / evidencia necesaria |
|---|---|---|---|---|
| SS-01 Alto |XSS Leaflet; mapa.js, map-tooltip-security.cjs |span/textContent llega al renderer; 33 casos tooltip y regresiones mapa/roles aprobados |Navegador, layout sticky/apertura/cierre, capas y DOM real |QA06/07: GeoJSON sintético con acentos, &, comillas, marcado inerte y vacíos; sólo texto y sin nodos extra. SS-08 CSP RO no lo sustituye |
| SS-02 Alto |GDAL hereda secretos/privilegios; gis_ingestion y consumidores |Entorno permitido explícito, comandos estructurados/sin shell; 17 pruebas propias aprobadas |Worker separado, UID/filesystem/red/secretos inaccesibles, límites SO, drivers/remotos garantizados |QA05/09: versiones/formatos nativos y entorno sin secretos. Worker no existe: registrar NO IMPLEMENTADO, no probar payload hostil en proceso API. Depende SS-03/07/09 |
| SS-03 Alto |Consumo GIS y unidad incorrecta; gis_limits/gis_archives/gis_ingestion/imports/reconciliation |MB GDAL separados de bytes; pending/salida/capas/features/ZIP limitados, rechazos y cleanup; 32 pruebas aprobadas |Vértices, CPU/memoria/deadline global, ZIP central directory nativo, operaciones SQL/event loop/cuotas multiusuario |QA05/10: GeoJSON/KML/GPKG/ZIP pequeños sintéticos, UTF-8 fragmentado, conteos incompletos y excesos con presupuestos de ensayo aprobados; sin truncamiento/completado falso. Depende SS-02/08/11 |
| SS-04 Medio |Abuso login/IP; request_origin/authentication y comandos |Cadena XFF validada desde peer; 32 pruebas aprobadas;flags Uvicorn preservados |Rate limit global/compartido, bloqueo inducido y capacidad bcrypt/eventos; esquema/Host HTTPS efectivo |QA02/07: peer correcto, XFF falso no suplanta; cookies/CSRF/CORS/roles. No exigir un 429 de limitador inexistente ni hacer fuerza bruta. Depende SS-08/10 |
| SS-05 Medio |Un vínculo habilita documento global; sólo docs de política |Diseño A/B/C y matriz; access/models sin modificar. Evidencia AIS-03 previa no se cuenta como ejecución actual |Aprobación funcional de política, implementación y migración/ACL por contexto si se decide |QA03/06: caracterizar permiso actual D con A/B y dos versiones; separar regresión de aprobación de confidencialidad. No esperar denegaciones propuestas todavía. Dueño funcional decide; no implementar aquí |
| SS-06 Medio |Extensión/MIME no fiable; document_validation/documents/router y fixtures |Validación acotada PDF/PNG/JPEG/OOXML, MIME canónico y descarga segura; 28 pruebas aprobadas |Corpus legítimo QA, parser nativo/antivirus/CDR/cuarentena/aislamiento. Malware/políglotas no resueltos |QA03/07/09: válidos y renombrados/truncados/genéricos/incongruentes; canónico persistido y legacy octet-stream, attachment/nosniff/no-store. SHA/RBAC intactos. Depende SS-08/12 |
| SS-07 Medio |Privilegios runtime no acreditados; docs/ss07 SQL/preparador |23 consultas metadatos preparadas; 20 pruebas aprobadas, 1 gramática omitida |Permisos efectivos, PUBLIC/owners/defaults/definer/search_path/TEMP y cualquier GRANT/REVOKE |QA08: inspector/autorización explícitos existentes, sin datos de negocio o cambios. Falta permiso/guard no coincide ⇒ BLOCKED, no PASS falso. Locks de catálogo y trigger/sequence no romper. Depende SS-10/12 |
| SS-08 Medio |Proxy/headers/contextoSSALFER; nginx.conf/Dockerfile |Headers always/herencia, CSP RO, no-store/log mínimo/COPY selectiva; 15 pruebas aprobadas |Nginx/TLS/browser/error logs reales, carga HTTP/redirects, UID/caps/red/recursos |QA01/07/09: 200/401/403/404/413/500/502 con headers únicos; attachment binario; CSP RO y mapas. client_max_body_size no corregido. Depende SS-01/04/06/09/10/12 |
| SS-09 Medio |Integridad build; ignore/vendors/verificador/descriptor |20 SHA vendors; 42 pins +1 QA; 123 resoluciones Node históricas; 19 pruebas aprobadas |PRE-02 por dependencia de React retirado remoto; distribución/upstream/digests/instalados/SBOM/SCA/GitHub |QA09: después de adaptar herramientas a SSALFER, comparar imagen/asset/ABI con manifest, inventario instalado y advisories. No funcional React ni cierre por hashes locales. Depende SS-02/03/08 |
| SS-10 Medio |Logs/SQL sensibles; database/main/safe_logging, CLIs/runtime |hide_parameters + diagnósticos controlados/correlación; 21 pruebas aprobadas, 3 nativas omitidas |Excepciones SQLAlchemy/driver real, collectores/retención/error logs de Nginx y terceros |QA02/07/09/10: sentinelas sintéticas no aparecen en salida final, sí categoría/código/correlación;no str(exc)/tracebacks. No alterar eventos funcionales. Depende SS-04/07/08 |
| SS-11 Medio |Reportes/CSV/mapa sin presupuesto integral; reporting/report_limits |Límites con 413 completo, CSV por lotes/bytes/archivo privado y cierre; 23 pruebas +script contrato JS aprobados |PostGIS/mapa masivo, tiempo/memoria/concurrencia SQL y cancelación real; navegador/ASGI/SQL nativos |QA06/07/10: filtros/RBAC/cantidades/superficies/montos exactos;sin pérdidas/duplicados/truncamiento;CSV formula-safe y recursos cerrados. No pedir paginación geométrica inexistente. Depende SS-08/10 |
| SS-12 Bajo |Publicación/commit/huérfanos/TOCTOU; storage/documents y tests |Staging privado, SHA/readback/link exclusivo;publicados conservados; 24 pruebas aprobadas, 2 Starlette omitidas |Lock padre max+1, concurrencia PG real, bitácora durable/reconciliador, apertura descriptor de descarga |QA03/04/10: dos sesiones, unicidad, duplicados/rollback/commit incierto y archivos completos;no borrar ajenos. Puede409 legítimo y huérfano;no atomicidad BD/FS. Depende SS-06/07/10 |

## Comandos de regresión local, realmente ejecutados

Desde la raíz del candidato, sin instalar ni usar conftest:

```text
python3 -B -m unittest discover -s tests/security -p 'test_*.py' -v
node tests/frontend-ssalfer/map-tooltip-security.cjs
node tests/frontend-ssalfer/map-gis-rbac.cjs
node tests/frontend-ssalfer/gis-bootstrap-rbac.cjs
env -u F05_EVIDENCE_DIR -u F05_BASELINE_ONLY node tests/frontend-ssalfer/map-performance.cjs
node tests/frontend-ssalfer/report-limits-contract.cjs
node --check frontend-ssalfer/js/mapa.js
python3 -B docs/security/ss09/verificar_cadena.py
git diff --check
```

Resultado actual: 231 Python PASS/6 skips, 58 Node TAP PASS y script contrato PASS. map-performance requirió permiso de ejecución fuera del sandbox para su git show; sin red/BD/writes. Los comandos propuestos para otro equipo deben inspeccionarse en su SHA de ejecución: no ejecutar un archivo cambiado sin revisión sólo por coincidir el nombre.

## Comandos integrados propuestos, NO ejecutados aquí

El responsable QA debe confirmar endpoint/identidad/datos sintéticos/configuración antes de cualquier comando. No se suministran env/credenciales/direcciones inventadas ni se fuerza el nombre de BD para pasar guardas. backend/tests/conftest valida APP_ENV/test y nombre, pero eso no prueba que DB_HOST sea QA; importa engine/app tras su preflight y sus fixtures escriben. collect-only no es un sustituto seguro.

| Grupo | Selección orientativa para el entorno QA existente autorizado | Requisitos / limitación |
|---|---|---|
| Auth/auditoría |`python -m pytest backend/tests/test_auth_rbac.py backend/tests/test_credential_management.py backend/tests/test_audit_api.py -q` |Rutas/fixtures inspeccionadas en SHA candidato; cuenta y BD sintéticas autorizadas, configuración secreta fuera del informe |
| Documentos/consolidado |`python -m pytest backend/tests/test_document_targets_039.py backend/tests/test_documents_dashboard.py backend/tests/test_frontend_read_models.py -q` |Versiones/roles y fixture PDF SS-06; validar escritura/filesystem y actor. Hay casos GIS en read_models: revisar selección con QA, no ejecutarlo a ciegas |
| GIS |`python -m pytest backend/tests/test_geospatial_imports.py backend/tests/test_gis_management_rbac.py backend/tests/test_gis_concurrency_026.py -q` |GDAL/PostGIS/migraciones y permisos efectivos; pruebas de concurrencia crean datos confirmados. Usar sólo recursos QA autorizados |
| Publicación SQL SS-12 |`python -B -m unittest discover -s tests/qa -p 'test_document_publication_postgresql.py' -v` |Opt-in SS12_QA_ENABLE y campos dedicados; guards exigen software_pa_test/cluster ss12-document-disposable y actor sintético. Si el QA existente no cumple, BLOCKED; **no renombrar/reconfigurar cluster para hacer pasar tests**. Son 6 contratos SQL/protocolo, no servicio/RBAC real ni lock implementado |
| Metadatos SS-07 |Preparador offline con config QA protegida, luego 23 consultas bajo inspector autorizado |No conecta el preparador; SQL tiene opt-in/guardas. No ejecutar bootstrap/migraciones/grants o modificar marker. Registrar capacidades no observables |
| HTTP |`nginx -t`; solicitudes HEAD a origen QA autorizado y respuestas stub de error |Sólo el compañero autorizado; no volcar nginx -T/env/inspect completo a informes por posibles secretos. Ningún comando Docker/Nginx ejecutado en esta entrega |
| Navegador SSALFER |Casos QA06/07 de la guía con navegador/evidencia reales |Sin CDN/tiles institucionales en pruebas locales: usar stub autorizado. No se instala navegador aquí y no se inventa un reporte Playwright |

Para SS-07, ejemplo de preparación sólo si la configuración y aprobación ya existen:

```text
python3 -B docs/security/ss07/preparar_verificador.py --config '<CONFIG_QA_PROTEGIDA>' --autorizacion-qa '<ID_QA>' --clon-desechable-verificado --salida '<ARCHIVO_NUEVO_PROTEGIDO>'
```

No compartir esa configuración o el SQL con parámetros internos en un comentario público. Una guarda que no coincide, falta de dependencia o permiso del inspector produce BLOCKED/NOT RUN, nunca PASS. El compañero no debe crear otra infraestructura por estas instrucciones; reporta la limitación al coordinador.

## Criterios de aprobación/rechazo

PASS de una etapa implementada exige resultado esperado + evidencia de SHA/dataset/herramientas y ausencia de regresión. FAIL es desviación reproducible del alcance implementado. BLOCKED es falta de precondición/entorno o incompatibilidad del candidato. NOT RUN incluye control inexistente, prueba sin autorización o no ejecutada, indicando causa exacta.

Rechazar Ready for Review/integración si se pierde un control previo, aparecen secretos, se cambia autorización SS-05/privilegios SS-07 sin aprobación, se reintroduce React como requisito funcional, se entregan CSV/GIS truncados como éxito, se borran archivos ajenos/publicados por commit incierto, o el SHA QA no coincide con el candidato. Un test SQL del diseño de lock que pasa no acredita que ese lock exista en store_version. Ninguna omisión es aprobación.
