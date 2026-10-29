# Matriz de cierre y puertas de aceptación SS-01 a SS-12

Fecha: 2026-10-29. SSALFER oficial, base local 683ff75613768de28a7127c7e33a6e2ef4fc40ff y destino remoto observado e2699fe5c043996f7338bd63af3221957699bd65.0 commits nuevos, ninguna rama creada, QA integrada NOT RUN. [Pruebas](MATRIZ-VALIDACION-QA-SS01-SS12.md), [diagnóstico](CONSOLIDACION-PRE-PR-SEGURIDAD.md).

Esta matriz reemplaza únicamente la lectura del estado de preparación actual; **no altera ni borra los informes históricos o la política de acceso vigente**. La selección SSALFER no es una decisión pendiente. Riesgos de React pertenecen al legado y no se atribuyen automáticamente a SSALFER.

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
| SS-09 Medio |Implementación parcial, bloqueante de consolidación PRE |Pins/lock/vendor hashes/contexto y herramienta offline |Adaptar legado opcional al dev actual, build/plataforma/digests/upstream/instalados/SBOM/SCA/procedencia/GitHub efectivos; integración/DevSecOps/QA |No |
| SS-10 Medio |Implementación local pendiente QA |hide_parameters/diagnósticos finales allowlist y sentinelas en dobles |Driver/SQLAlchemy/ASGI real, excepciones/collectors/retención/errores proxy revisados con pruebas seguras; backend/operación/AppSec |No |
| SS-11 Medio |Implementación parcial etapa 1 |Límite de reportes/CSV completo por lotes, cierre de recursos y fórmulas exportadas |SQL/PostGIS/mapa/tiempos/concurrencia y cancelación efectivos, filtros/totales/corpus QA; backend/GIS/QA |No |
| SS-12 Bajo |Implementación parcial etapa 1 |Staging/bytes/SHA/link exclusivo/retención ante commit incierto |Serialización por documento en PostgreSQL, recuperación durable/reconciliación y descarga por descriptor si se aprueba, pruebas nativas/control de crash; backend/DBA/QA |No |

No hay celdas “QA validada” o “cerrado” por la ejecución local. Una etapa parcial puede revisarse/integrarse con aceptación explícita del alcance y riesgos, **sin declarar implementado lo que falta**. El cierre completo debe tener evidencia por control y responsables, no una decisión implícita al hacer merge.

## Evidencia de cierre que deberá registrarse

Para cada SS:SHA candidato y base, archivos/control final, modelo de amenaza/política aplicable, pruebas positivas y negativas ejecutadas con versiones/dataset sintético, resultado/limitaciones, aprobación del responsable y fecha. Adjuntar referencias protegidas, no datos institucionales. Si el riesgo se acepta, anotarlo como residual/aceptado con justificación y condiciones, no como remediado por defecto.

Un control no implementado se queda NO IMPLEMENTADO aunque una prueba caracterice la ausencia esperada. Una dependencia QA no disponible se queda BLOCKED/NOT RUN. El test Starlette que demuestra sustitución de path y los contratos SQL del lock propuesto son diagnósticos/diseños; su PASS no acredita remediación de TOCTOU/serialización en la API actual.

## Decisión consolidada de entrega

**B. NO LISTO PARA PUBLICAR.** Condición de rama/commits no satisfecha por incompatibilidad con destino actual; 0 commits creados. Resolver PRE antes de abrir Draft PR, suministrar SHA exacto al compañero y usar sólo su QA existente. No push, PR, merge, despliegue o corrección productiva incidental realizados en este turno.
