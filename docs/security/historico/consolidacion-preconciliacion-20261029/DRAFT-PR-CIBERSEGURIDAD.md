# Contenido preparado para futuro Draft PR — no creado

Fecha: 2026-10-29. Estado de publicación **B. NO LISTO PARA PUBLICAR**. Esta es una plantilla revisable: no existe URL/PR, rama nueva o commit candidato.0 commits creados. Completar SHA y relación real sólo después de resolver bloqueantes; no publicar esta plantilla con campos hipotéticos como si fueran evidencia.

**Título propuesto:** `security: consolidate SS-01 to SS-12 hardening for SSALFER QA`

Origen propuesto: `security/ss01-ss12-qa`. Destino: `dev`. Base local original 683ff75613768de28a7127c7e33a6e2ef4fc40ff; dev remoto observado e2699fe5c043996f7338bd63af3221957699bd65. Tipo: **Draft**, sin auto-merge ni despliegue. Frontend oficial: SSALFER. React/Vite legado no se modifica aquí ni requiere validación funcional para aceptar este trabajo.

## Descripción propuesta del cambio final

Los tooltips Leaflet podían interpretar etiquetas como HTML; el procesamiento GIS tenía presupuestos incompletos y subprocesos con configuración heredada; documentos/reportes y diagnósticos requerían controles adicionales. Este conjunto añade texto DOM literal, entorno GDAL permitido y cuotas, validación documental/MIME, publicación exclusiva conservadora, límites de reportes/CSV, diagnósticos seguros y configuración HTTP inicial de SSALFER.

La entrega incluye diseños y verificadores offline para privilegios/dependencias y política de documento compartido. **No cierra los doce hallazgos**: diferencia implementación local, controles parciales y diseños pendientes. SS-05 no cambia autorización; SS-07 no cambia permisos PostgreSQL; no se agregan migraciones/versiones de dependencias.

## Bloqueantes antes de publicar este PR

- [ ] Alinear la base con el dev real sin perder trabajo; no hacerlo mediante comandos prohibidos en esta fase.
- [ ] Adaptar SS-09/pruebas/descriptores a SSALFER oficial y ausencia de frontend/ en destino. Proyección actual falla por frontend/package.json, sin merge ejecutado.
- [ ] Revisar Compose compartidos preservando SS-04/10 y nuevas variables; no copiar remoto encima de cambios locales ni reintroducir React retirado allí.
- [ ] Registrar rama y SHAs reales tras commits revisados y nueva ejecución sobre el candidato alineado.
- [ ] Revisar staging explícito, datos/secretos, alcance/visibilidad del repositorio y autorización de push/PR.

## Resumen por hallazgo

| Hallazgo | Alcance incluido | Estado que debe comunicar el PR |
|---|---|---|
| SS-01 Alto |Leaflet span/textContent y regresiones |Local conforme; navegador pendiente |
| SS-02 Alto |Entorno restringido de GDAL |Parcial; no worker/UID/red/filesystem aislados |
| SS-03 Alto |Unidad GDAL, buffers/ZIP/capas/features/salida |Parcial; presupuestos integrales/SO/SQL pendientes |
| SS-04 Medio |Identidad de peer/cadena y flags Uvicorn |Parcial; no rate limit global ni solución completa a bloqueo inducido |
| SS-05 Medio |Política documental A/B/C y matriz |Diseño pendiente, no implementación |
| SS-06 Medio |Formatos/MIME y descarga segura |Local pendiente corpus/stack QA; no antimalware |
| SS-07 Medio |Inventario/consultas opt-in metadata |Efectivos desconocidos, sin hardening aplicado |
| SS-08 Medio |Headers/RO/cache/log/COPY SSALFER |Parcial; Nginx/HTTPS/cargas/redirects/error logs nativos pendientes |
| SS-09 Medio |Contexto/backend, vendors/verificador/inventario |Parcial; adaptación de integración, upstream/instalados/SBOM/SCA/GitHub pendientes |
| SS-10 Medio |hide_parameters y diagnósticos estructurados |Local pendiente drivers/collectors QA |
| SS-11 Medio |Reportes completos limitados/CSV por lotes |Parcial; mapa/SQL/tiempos/concurrencia integral pendientes |
| SS-12 Bajo |Staging/bytes/SHA/link exclusivo y conservación |Parcial; locks PG, recuperación durable/huérfanos y TOCTOU pendientes |

## Commits y archivos

Commits locales reales creados en esta preparación: **ninguno**. No inventar títulos/SHA como si hubiesen sido creados. Ver agrupaciones propuestas en PLAN-INTEGRACION-SEGURIDAD-GIT.md; cuando se autoricen y pasen gates, reemplazar este párrafo por el historial real y SHA candidato.

Inventario íntegro con SHA-256 de 93 archivos originales y siete documentos nuevos en CONSOLIDACION-PRE-PR-SEGURIDAD.md. Archivos compartidos principales: gis_ingestion/imports/reconciliation (SS-02/03), documents (SS-06/12), Dockerfile/Compose (SS-03/04/06/10/11), logs SS-10 usados por almacenamiento SS-12. No aplicar los diez patches históricos al hacer checkout de la rama.

## Pruebas locales realizadas el 2026-10-29

- 231 Python aprobadas, 6 omitidas (237 descubiertas), 0 fallos finales.
- 58 casos Node TAP aprobados y script de contrato de reportes aprobado.
- Sintaxis: 38 Python candidatos sin imports, 3 JS/CJS, 8 JSON y 3 bash -n; diff --check conforme.
- 20 vendors coinciden con manifiesto local. Autenticidad upstream e instalados no verificados.
- Proyección de bajas remotas: falla con código 2 por fuente legacy obligatoria; bloqueante real de herramientas, no test de merge ni ejecución de SSALFER sobre remoto.

map-performance falló inicialmente por sandbox EPERM de git show y aprobó 11 casos tras permiso de ejecución local; no código corregido ni resultado ocultado. Omisiones: 2 Starlette, 3 SQLAlchemy/psycopg2, 1 pglast. No PostgreSQL/Docker/Nginx/GDAL/navegador real/HTTPS en esta ejecución.

## Instrucciones al responsable QA

Usar exclusivamente tu entorno existente autorizado, con datos sintéticos y el SHA exacto que se suministre posteriormente. Seguir GUIA-ENTREGA-COMPANERO-QA.md y MATRIZ-VALIDACION-QA-SS01-SS12.md, casos QA-01–10. No crear otra infraestructura ni ejecutar .patch, bootstrap, seeds, migraciones o GRANT/REVOKE por inferencia.

Responsables por función: QA/DevOps valida entorno/build/proxy/navegador; DBA valida sólo metadatos/privilegios bajo autorización; backend/AppSec revisa errores/regresiones; dueño funcional decide SS-05; mantenedor de integración valida base/commits. Nombres y asignaciones se acuerdan antes de publicar; no se envía mensaje a otra persona automáticamente.

Evidencia requerida:SHA, versión/digest realmente observado, dataset sintético, procedimiento/resultado y capturas/logs redactados. Guardar evidencia sensible en QA, no adjuntar .env/cookies/dumps/datos institucionales al PR. Usar REPORTE-INCIDENCIAS-QA.md.

## Riesgos residuales/configuración

CSP Report-Only no bloquea XSS; no-store no revoca copias ni memoria. Default de cuerpo Nginx puede impedir uploads legítimos; esquema/Host/Location requieren TLS real. GDAL no es worker aislado. No hay rate limiter distribuido. Drivers/installed hashes/digests/SBOM no se acreditan por etiquetas. Documentos compartidos conservan política actual; max+1 no serializado y BD/filesystem no son atómicos; archivo huérfano no se borra automáticamente. Los tests SQL SS-12 de protocolo propuesto no prueban su implantación en servicio.

## Checklist para pasar a Ready for Review

- [ ] Bloqueantes PRE resueltos y base/SHA del candidato vigentes.
- [ ] QA-01–10 del alcance implementado ejecutados con evidencia, omisiones y limitaciones justificadas.
- [ ] Rechazos negativos/RBAC/cookies/CSRF/descargas/mapa/reportes sin regresiones.
- [ ] No hay secretos/datos reales/artefactos de QA no aprobados o cambios inesperados en commits.
- [ ] No se exige funcionalidad React para aceptar SSALFER; legacy no reintroducido en destino por accidente.
- [ ] No se declara PASS de worker/rate limiter/política/privilegios/locks que no existen.
- [ ] SS-05 sigue sin implementar hasta aprobación; SS-07 sin cambios de privilegios no autorizados.
- [ ] Riesgos residuales y aceptación de etapa parcial revisados por responsables.
- [ ] Revisión técnica completa; CI/publicación/despliegue no se activan automáticamente.

Rechazar/seguir Draft por evidencia de pérdida de controles, secreto, cambio no autorizado, truncamiento exitoso, borrado ajeno/commit incierto, cadena IP suplantable o QA de SHA distinto. Ready for Review no equivale a integración aprobada, y QA aprobada no equivale a cierre de hallazgos no implementados.
