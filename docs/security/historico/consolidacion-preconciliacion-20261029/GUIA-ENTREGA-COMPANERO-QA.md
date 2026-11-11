# Guía de entrega al compañero responsable de QA

Fecha: 2026-10-29. Frontend oficial **SSALFER**; backend FastAPI y PostgreSQL/PostGIS. React/Vite es legado conservado localmente y no requiere QA funcional para aceptar este Draft PR. Este documento no solicita crear otro QA ni cambiar la configuración del entorno existente.

## Ficha de recepción

| Dato | Estado de esta entrega |
|---|---|
| URL del Draft PR |No existe; no se abrió ni publicó rama |
| Rama recomendada |security/ss01-ss12-qa, todavía no creada |
| SHA candidato |No asignado; 0 commits creados. No confundir con la base local 683ff75613768de28a7127c7e33a6e2ef4fc40ff |
| Destino |dev, remoto observado e2699fe5c043996f7338bd63af3221957699bd65 |
| Preparación/publicación |B. NO LISTO PARA PUBLICAR por PRE-01–04, ver consolidación |
| QA integrado actual |NOT RUN; no se conectó a tu entorno |
| Responsable QA |Compañero administrador del QA, nombre por confirmar; no se inventa identidad |

**No desplegar la rama inexistente o aplicar patches archivados.** El coordinador completará URL, SHA exacto, commits y resolución de bloqueantes tras autorización. Confirmar esos datos antes de iniciar: un resultado sin SHA/versiones/dataset no valida este candidato.

## Condiciones y perfil esperado

- Usar sólo tu QA existente y recursos/datos sintéticos autorizados. No usar credenciales o datos institucionales en fixtures, capturas o logs. No envíes .env, cookies, tokens, DSN o backups al PR.
- SSALFER se sirve desde frontend_ssalfer/Nginx y usa /api del mismo origen. La composición local de referencia base+prod+ssalfer es una **descripción**, no una orden de arranque; el remoto ya actualizó esa arquitectura y debe reconciliarse antes de entrega real.
- Si el perfil conserva varios servicios, seleccionar explícitamente backend y frontend_ssalfer para build y db/backend/frontend_ssalfer para operación autorizada; no un up/build general que arranque React o pgAdmin. Coordina esto con la configuración existente; no cambiar servicios sin tu procedimiento de aprobación.
- Backend sin reload/binds de código para el perfil de aceptación, --no-proxy-headers y --no-access-log con logging.json SS-10. Cookies Secure/__Host-, Origin/CORS exactos y cadena TLS/Host/puerto/Location verificados con tu configuración, sin inventar IP de proxy.
- No se añaden migraciones. El código se revisó con la cadena canónica 001–030 existente; comprobar compatibilidad/registro/checksums del esquema sin ejecutar runner/seed/bootstrap automáticamente. No “actualizar” tu BD sólo para hacer pasar una prueba.
- Imagen/bibliotecas efectivas deben registrarse: GDAL/GEOS/PROJ/libpq, Python/FastAPI/SQLAlchemy/Starlette, PostgreSQL/PostGIS y Nginx/navegador. Las etiquetas y requisitos fuente no acreditan instalados.
- Las guardas con nombre de cluster/BD de tests SS-07/12 pueden no corresponder a tu QA. Si no corresponden, reporta BLOCKED, no alteres cluster_name ni variables de destino para simular autorización. Los nombres de BD por sí solos no prueban aislamiento.

La [matriz SS](MATRIZ-VALIDACION-QA-SS01-SS12.md) contiene comandos propuestos y scripts existentes. Ninguno se ejecutó contra tu entorno durante esta preparación.

## Datos sintéticos mínimos

Dos proyectos A/B y tercero ajeno, usuarios sintéticos de cuatro roles y operadores sólo A/B/ambos/ninguno; un documento D con vínculos A/B y dos versiones, otra versión anterior a un vínculo; PDF/OOXML/PNG/JPEG pequeños válidos y malformados sintéticos; importaciones GeoJSON/KML/GPKG/ZIP de trazos/DDV/núcleos/parcelas con CRS/dimensiones controladas; reportes con totales conocidos y texto que parezca fórmula; sentinelas únicas de datos/tokens falsos para logs. No usar malware, expedientes reales o archivos hostiles grandes en un proceso no aislado.

Los casos de recurso deben parametrizar límites pequeños/autorizados y contener pocos objetos; no ejecutar fuerza bruta, fuzzing o carga como sustituto. Cualquier construcción/arranque/manipulación de recursos la realiza exclusivamente el administrador QA dentro de su autorización existente.

## Casos mínimos sobre el candidato futuro

| Caso | Precondiciones y procedimiento | Resultado esperado / evidencia | Decisión |
|---|---|---|---|
| QA-01 Inicio |SHA recibido, perfil SSALFER revisado y esquema compatible. El administrador construye/activa sólo mediante su procedimiento autorizado; abrir login/health y ruta API canónica |SSALFER correcto, sin React arrancado accidentalmente, API disponible y versión/schema coherentes; versiones e imagen/servicios sin secretos |PASS con evidencia real; dependencia/esquema/perfil no aprobado ⇒ BLOCKED; fallo del candidato ⇒ FAIL |
| QA-02 Autenticación |Usuarios sintéticos activos/inactivos, roles, sesiones; login/logout/expiración/CSRF/Origin/CORS y XFF falsificado/directo/proxies |Sesiones/cookies/roles preservados, IP conforme a peer/cadena, negativos 401/403 controlados. Rate limiter global no existe: NO IMPLEMENTADO, no exigir 429 ni simular protección |Captura segura de flags/códigos/correlación, nunca valores de cookie/token. BLOCKED si cadena TLS/proxy no acreditable |
| QA-03 Documentos |Corpus sintético y storage autorizado; alta/metadata, formatos válidos/incongruentes/truncados, MIME genérico, versión/descarga/permiso positivo-negativo |Canónico persistido, bytes/SHA intactos, attachment/octet-stream/nosniff/private, no-store, historia preservada. D compartido conserva política actual, sin aprobación implícita de SS-05 |FAIL por pérdida de bytes, bypass o validación incorrecta. Un PDF estructuralmente válido no prueba malware ausente |
| QA-04 Concurrencia documental |Dos sesiones QA autorizadas; mismo documento/bytes/distintos documentos, fallos controlados de escritura/commit y consulta de estado |Unicidad real y conflictos controlados; publicados conservados ante confirmación incierta; no borrar ajenos. No se promete dos 201 para mismo documento ni ausencia de huérfanos |Registrar SQLSTATE/timeline anonimizados y hash/IDs sintéticos. Parent lock/bitácora durable ausentes quedan NOT RUN para eficacia de esos controles |
| QA-05 GIS |GDAL/PostGIS disponibles, datos sintéticos pequeños; probar GeoJSON/KML/GPKG/ZIP, legacy/DDV/núcleos/parcelas y referencia RAN sintética sólo si autorizada |CRS/4326/Z-M/procedencia/idempotencia y reglas previas intactas; límites explícitos sin parcial exitoso; stdout/proceso/temp propios liberados en casos controlados |Capturar versiones, tamaño/conteos y rechazos. Worker no implementado: no probar escapes hostiles como si hubiera sandbox |
| QA-06 Reportes/seguimiento/mapas |Totales sintéticos conocidos, filtros/roles, arrays dentro límite y exceso, CSV/texto fórmula, seguimiento individual/colectivo |Totales/superficies/montos exactos, 413 sin truncar, CSV completo con recursos cerrados, mapa conserva parcelas/núcleos/trazos/DDV y tooltips texto literal |Evidencia DOM/navegador y filas/conteos, no expedientes. Geometrías masivas/presupuestos SQL no implementados no se marcan PASS |
| QA-07 Nginx/navegador/HTTPS |Mismo binario/config real, certificados/origen QA autorizados; 200/401/403/404/413/500/502; slash/Location; assets y descargas; CSP RO; atrás/logout, framing y blobs |Headers únicos/always, sin errores de MIME, cookies seguras, IP no suplantada, estilo/interacciones intactos. Observar límite de carga efectivo y errores Nginx sensibles |nginx -t/headers sanitizados/console y capturas sintéticas. CSP no bloqueante no equivale a enforcement; 404 antes de seleccionar server puede tener otro alcance |
| QA-08 Privilegios |DBA confirma inspector/destino y autorización SS-07 de sólo metadatos; ejecutar su procedimiento opt-in si guardas corresponden |ACL/owners/PUBLIC/membresías/defaults/funciones/secuencias acreditados o no observables registrados; 0 cambios GRANT/REVOKE |Sin permisos/guardas ⇒ BLOCKED, no ausencia de exceso. No pedir credenciales o modificar rol para forzar PASS |
| QA-09 Dependencias/build |Herramientas SS-09 adaptadas al nuevo dev; el administrador construye artefactos aprobados con contexto controlado |Vendors locales coinciden; instalados/digests/ABI/SBOM/SCA/procedencia documentados; rutas operativas no publicadas; no filtración por contexto/capas |Tag no es digest, inventario declarado no es SBOM. SCA pendiente no es0 CVEs. No funcional React requerida |
| QA-10 Recuperación/regresión |Recursos QA autorizados, plan de recuperación del administrador y fallos sintéticos acotados |Recursos propios liberados, archivos completos preservados cuando se publica, sin borrado automático de huérfanos/historia. Logs sin sentinelas sensibles y comportamiento de red/cancelación registrado |Registrar ventanas de fallo y diferencia código/entorno. No restaurar/borrar tu BD o volúmenes por comandos de esta guía |

Cada caso se reporta PASS/FAIL/BLOCKED/NOT RUN para su alcance, por SHA. Un control inexistente se etiqueta NO IMPLEMENTADO aparte y su eficacia no se aprueba. El éxito de tests que ejemplifican un protocolo propuesto no demuestra que ese protocolo esté en la API.

## Evidencia que debe devolver QA

Para cada caso:SHA candidato/base, versión de artefacto/digest si observado, ID del dataset sintético, precondiciones y permisos de prueba, comando/procedimiento exacto con secretos eliminados, esperado/observado, resultado, versiones relevantes, evidencia segura y responsable/fecha. Distinguir ejecución real de inspección estática o dobles.

Usar [formato de incidencias](REPORTE-INCIDENCIAS-QA.md). Conservar evidencias completas en el espacio protegido de QA; el PR recibe referencias/redacciones, no logs completos, .env, URLs con tokens, PDF reales, dumps o capturas de personas. Al publicar evidencia, revisar también metadatos/EXIF/queries y no sólo el texto visible.

Si no puede ejecutarse un caso por guardas/infraestructura, indicar BLOCKED/NOT RUN y causa. No instalar herramientas, crear otro QA, cambiar DB/cluster o desactivar auditoría/roles para hacerlo pasar sin aprobación de tu operación.

## Gates de entrega

Hoy el paquete es diagnóstico y plantillas, **no una solicitud de desplegar**. Tras resolver PRE-01–04, el coordinador deberá suministrar rama y SHA reales y autorización de publicación. QA satisfactoria de las etapas implementadas permite revisión técnica; no cierra SS-05/07/12 ni otros controles ausentes. Integración requiere revisión/riesgos residuales aceptados, y despliegue institucional sigue siendo una autorización separada.
