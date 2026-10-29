Fecha: 2026-10-29. Base original `683ff75613768de28a7127c7e33a6e2ef4fc40ff`; base candidata dev `e2699fe5c043996f7338bd63af3221957699bd65`; PR #5 observado `42ef451847dea8286c0f8d395b0d91675e62b69b`. SSALFER es el frontend oficial. **0 ramas y 0 commits creados; ningún push/PR/merge/despliegue.**

# Contenido actualizado del Draft PR propuesto — no publicado

**Título:** `security: reconcile SS-01 to SS-12 hardening with SSALFER dev for QA`

Origen futuro security/ss01-ss12-qa; destino dev. No URL ni SHA candidato asignados:0 commits creados. PR #5 existente sigue abierto, no es este Draft y no se modifica. No usar su rama de origen compartida con PR4.

## Problema y resultado

La integración de seguridad local estaba basada en dev anterior al retiro React; el verificador SS09 fallaba por archivos legacy ausentes. Este candidato conserva las remediaciones SS01–12, porta flags/cuotas/logging a Compose vigente y hace opcional la fuente React retirada, manteniendo SSALFER y hashes vendors obligatorios. Selecciona únicamente hunks compatibles del PR5 para publicación/origen/documentación; no incorpora todo ese PR.

Leaflet recibe texto DOM literal; GDAL hereda sólo entorno permitido con presupuestos explícitos; documentos validan formatos/MIME y publican archivos exclusivos de forma conservadora; reportes/CSV tienen límites; diagnósticos excluyen excepción/SQL sensibles; Nginx SSALFER conserva CSP RO/no-store/log mínimo/COPY selectivo. No hay migraciones ni versiones de dependencias cambiadas.

## Matriz y límites

Ver MATRIZ-CIERRE-HALLAZGOS.md y MATRIZ-VALIDACION-QA-SS01-SS12.md. SS05 sólo diseño, SS07 sólo preparación de metadatos. GDAL worker/UID/red, rate limiter compartido y anti-bloqueo, malware/cuarentena, presupuestos mapa/SQL, locks documentales/recuperación durable/TOCTOU siguen NO IMPLEMENTADOS. SS08 necesita TLS/Nginx/browser real; SS09 necesita upstream/digests/instalados/SBOM/SCA/GitHub. No declarar 12 hallazgos resueltos.

## Selección del PR5 y coexistencia

Incorpora config HTTPS única producción y docs condicionales, .dockerignore frontend, tres404 operativos, gitignore de secretos/outputs y redacción puntual de una dirección interna. Conserva handlers/flags SS10. No incorpora UID10001, dos workers, TLS/ACME/subred/certificados, limit_req5r/m, CSP bloqueante, 101m global, actualizaciones Python o 157 bajas QA/evidencias.4 hashes cubren29 inline pero no sustituyen navegador. Coexistencia selectiva; prohibido superponer PR5 íntegro sin revisión.

## Commits y pruebas

Relación real:ningún commit. Completar esta sección con SHAs/títulos revisados tras autorización, conforme al plan Git; no publicar con placeholders como evidencia.

243 Python PASS/6skip de 249, 58 Node TAP PASS y contratoPASS;20 vendors íntegros.152 Python/36 JSON/3 JS/3 shell sintaxis conforme.192 avisos whitespace históricos documentados; sin avisos nuevos de código. El EPERM inicial de map-performance se resolvió con repetición local autorizada11/11. No PostgreSQL/PostGIS/GDAL/Docker/Nginx/HTTPS/navegador nativos ejecutados; no usar cifras declaradas en PR5 como resultados propios.

## Instrucciones QA y evidencia

El compañero usa sólo QA existente y datos sintéticos, según GUIA-ENTREGA-COMPANERO-QA.md QA01–10. Suministrar URL/SHA/commits reales y perfil exacto antes de pruebas. Registrar versiones/digests observados, dataset, procedimiento, esperado/observado y evidencia redactada. No credenciales/cookies/dumps/capturas reales o logs completos. Cuerpo Nginx interno por defecto puede bloquear uploads grandes: validar y corregir presupuesto por ruta mediante revisión independiente antes de aceptación operativa.

Responsables por función:integración para base/SHA, backend/GIS/AppSec para regresiones, QA/DevOps para build/proxy/browser, DBA para inspección autorizada, dueño funcional SS05. Nombres/asignaciones por confirmar, sin mensajes automáticos.

## Checklist de publicación y Ready for Review

- [ ] Base dev/PR5 reconsultados y hunks solapados coordinados; rama propia no compartida PR4/5.
- [ ] Commits reales revisados, sin secretos/datos QA nuevos/versiones o políticas no aprobadas.
- [ ] Suites aisladas repetidas sobre el SHA candidato real y source/manifest coincidentes.
- [ ] QA01–10 implementados ejecutados con evidencia; omisiones/NO IMPLEMENTADO no sonPASS.
- [ ] SSALFER navegador/mapa/archivos/cookies/CSRF/IP/CSV sin regresiones; sin QA funcional React obligatoria.
- [ ] Riesgos parciales aceptados explícitamente, SS05 no implementado y SS07 sin permisos alterados.
- [ ] No pérdida de logging/cuotas/publicación por superposición con PR5; evidencia histórica clasificada fuera del artefacto web.
- [ ] Autorización separada de publicación y revisión; sin auto-merge/despliegue.

Rechazar Ready/integración por secreto, cambio no autorizado, pérdida de controles, bytes/geometrías/totales incorrectos, truncamiento exitoso, borrado de ajenos/publicados con commit incierto, identidad IP suplantable o QA de SHA distinto. La aprobación parcial deQA no cierra controles que todavía no existen.
