Fecha: 2026-10-29. Base original `683ff75613768de28a7127c7e33a6e2ef4fc40ff`; base candidata dev `e2699fe5c043996f7338bd63af3221957699bd65`; PR #5 observado `42ef451847dea8286c0f8d395b0d91675e62b69b`. SSALFER es el frontend oficial. **0 ramas y 0 commits creados; ningún push/PR/merge/despliegue.**

# Matriz vigente de cierre

Preparación local A para commits seleccionados; QA NOT RUN y ningún hallazgo cerrado. Conciliar SS-09 con SSALFER no acredita upstream, instalados, SBOM o CVE. SS-08 añade defensa de publicación; no TLS/CSP enforcement ni presupuesto HTTP corregidos. SS-04 no tiene limitador distribuido.

| ID / gravedad original | Estado real ahora | Qué sí está evidenciado | Condición adicional de cierre / responsable | ¿Cerrado? |
|---|---|---|---|---|
| SS-01 Alto |Implementación local pendiente QA |Etiquetas como texto en código y dobles, 33 casos específicos |Navegador/DOM/layout/eventos/mapa real con datos sintéticos, negativos y evidencia; frontend/AppSec/QA |No |
| SS-02 Alto |Implementación parcial etapa 1 |Entorno GDAL explícito y comandos sin shell |Diseñar/implementar/aprobar worker/UID/volumen/red/secretos/límites y demostrar aislamiento real; backend/DevSecOps/AppSec |No |
| SS-03 Alto |Implementación parcial etapa 1 |Unidad MB, buffers/salida/capas/features/ZIP y errores explícitos |Presupuesto integral CPU/memoria/vértices/SQL/tiempo/concurrencia, formatos nativos y cleanup; GIS/backend/QA |No |
| SS-04 Medio |Implementación parcial |Peer/cadena confiables y flags/logging |Rate limiter compartido y anti-bloqueo inducido no implementados; TLS/Host y atribución efectiva QA; backend/DevOps/AppSec |No |
| SS-05 Medio |Diseño pendiente aprobación |Alternativas funcionales y matriz, política actual conservada |Aprobación del dueño funcional y posterior implementación/migración/pruebas necesarias de política elegida; no aprobar el diseño por un test unitario |No |
| SS-06 Medio |Implementación local pendiente QA, riesgos de contenido residuales |Perfil estructural acotado, MIME y descarga |Corpus legítimo y malformed QA, seguridad del parsing y decisión/controles de malware/cuarentena/CDR según modelo de riesgo; documental/AppSec/QA |No |
| SS-07 Medio |Auditoría estática/preparación de inspección; efectivo desconocido |Inventario y 23 consultas metadata opt-in |Inspección autorizada efectiva, mínimo privilegio y dependencias probados; cambios sólo con nueva autorización, DBA/DevOps/AppSec |No |
| SS-08 Medio |Implementación parcial/local pendiente QA |Headers/RO/cache/log mínimo y COPY selectiva |HTTPS/Nginx/navegador/errores/cargas/redirects y manifiesto runtime real verificados, riesgos host/logs atendidos; DevOps/frontend/QA |No |
| SS-09 Medio |Implementación parcial, acoplamiento legado resuelto |Pins/lock/vendor hashes/contexto y herramienta offline |Legado opcional adaptado localmente; falta build/plataforma/digests/upstream/instalados/SBOM/SCA/procedencia/GitHub efectivos; integración/DevSecOps/QA |No |
| SS-10 Medio |Implementación local pendiente QA |hide_parameters/diagnósticos finales allowlist y sentinelas en dobles |Driver/SQLAlchemy/ASGI real, excepciones/collectors/retención/errores proxy revisados con pruebas seguras; backend/operación/AppSec |No |
| SS-11 Medio |Implementación parcial etapa 1 |Límite de reportes/CSV completo por lotes, cierre de recursos y fórmulas exportadas |SQL/PostGIS/mapa/tiempos/concurrencia y cancelación efectivos, filtros/totales/corpus QA; backend/GIS/QA |No |
| SS-12 Bajo |Implementación parcial etapa 1 |Staging/bytes/SHA/link exclusivo/retención ante commit incierto |Serialización por documento en PostgreSQL, recuperación durable/reconciliación y descarga por descriptor si se aprueba, pruebas nativas/control de crash; backend/DBA/QA |No |


No hay evidencia integrada nueva. SS-05 aprobación funcional, SS-07 permisos efectivos y SS-12 locks/recuperación/TOCTOU siguen pendientes; su éxito unitario no los resuelve. Roles/políticas/migraciones no modificados. Los cuatro estados preparado QA, QA conforme, preparado integración y hallazgo cerrado siguen siendo diferentes. Ver informe de conciliación y guía QA vigente.
