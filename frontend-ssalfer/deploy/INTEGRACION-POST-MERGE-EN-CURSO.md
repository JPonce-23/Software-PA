# Integración tras merge — seguimiento de implementación

Reanudación: 05-10-2026. Base local `e797df8`, rama `feature/integracion-mq-deploy`. GitHub revisado: `origin/feature/backend-logica` en `49f12f7`, ya contenido en HEAD. Sin cambios posteriores pendientes de traer. No se harán commits ni push en esta ronda.

El usuario amplió expresamente el alcance a geoespacial por proyecto, prevaleciendo sobre su exclusión en el adjunto. Se mantienen: sólo editar `frontend-ssalfer/`, sin backend/migraciones/roles; no escrituras QA de negocio sin autorización concreta; máximo estado QA local manual.

Contrato revisado: 119 paths, 178 operaciones en `docs/openapi.json`. Backend QA `/health` informa esquema 20 y ofrece catálogo RAN y revocación de asignaciones. Documento `DERECHOS_COLECTIVOS_PARA_FRONTEND.md` ausente en árbol remoto; se trabaja con contratos reales. La migración 020 corrige el heartbeat en auditoría; no filtrar ni borrar historial desde frontend.

- [x] Documentos: vínculos, versiones/descargas, trazabilidad; refresco de selectores.
- [x] Derechos colectivos: resumen por afectación y reporte no aditivo de destinos.
- [x] Núcleos: búsqueda oficial y excepción de alta, contexto, referencias y responsables. Catálogo vacío en QA: pendiente de datos para probar un vínculo oficial real.
- [x] Directorio contextual de personas e intervinientes FIFONAFE. Ciclo ORV conectado dentro de los límites de histórico/reactivación del backend.
- [x] Ediciones: pagos, titulares, comparecientes, vínculos, RAN; asignaciones de usuarios.
- [x] Navegación, funciones sin uso, textos humanos y protección geoespacial contra respuestas de otro proyecto. Capas de obras transversales pendientes del backend.
- [x] Pruebas de lectura y payloads interceptados, informe endpoint→pantalla, bloqueos y casos concretos para autorizar persistencia.

Cierre de implementación de esta ronda: **QA local manual**, no producción. Las casillas indican implementación y verificaciones descritas, no persistencia real ni resolución de bloqueos del backend. No se ejecutaron escrituras de negocio.

- Informe: [QA-INTEGRACION-2026-10-05.md](QA-INTEGRACION-2026-10-05.md).
- Pendientes con evidencia: [BLOQUEOS-BACKEND-2026-10-05.md](BLOQUEOS-BACKEND-2026-10-05.md).
- Instrucciones de revisión: [PROMPT-INSPECCION-POST-MERGE-2026-10-05.md](PROMPT-INSPECCION-POST-MERGE-2026-10-05.md).

Pruebas históricas y componentes de las rondas 1–3 deben conservarse. Credenciales sólo en entorno, nunca en archivos.
