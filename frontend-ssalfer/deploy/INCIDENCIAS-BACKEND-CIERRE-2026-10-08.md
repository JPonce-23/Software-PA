# Incidencias backend — cierre frontend del 8 de octubre de 2026

No se reprodujeron nuevas incidencias backend bloqueantes en las consultas ejecutadas contra schema 028. La lista actual de incidencias confirmadas está vacía.

Evidencia real: `/catalogos/tipos-documento`, consolidado documental del núcleo 150, mapa del proyecto 4, importaciones, revisiones, búsqueda de personas y catálogo RAN respondieron 200. Totales observados: 2 importaciones y 0 revisiones. El catálogo documental devolvió 27 tipos. Las consultas vacías no demuestran una falla.

No reactivar B-01…B-15 por referencia histórica. Revisar cada hallazgo contra OpenAPI y respuesta actual. Las escrituras interceptadas de frontend no verifican persistencia backend; quedan para casos de QA autorizados, sin declararlas bugs.

Para agregar una incidencia, registrar:

| Campo | Evidencia requerida |
|---|---|
| Pantalla/rol/proyecto | Contexto reproducible, sin credenciales |
| Endpoint y método | Ruta real del contrato actual |
| Petición | Parámetros y cuerpo sanitizados |
| Respuesta | Status y cuerpo sanitizado |
| Obtenido/esperado | Diferencia concreta según contrato |
| Reproducción | Pasos, fecha y captura/log |
| Clasificación | Backend confirmado / frontend / pendiente de diagnóstico |

Fuera de alcance y no bloqueante: las capacidades de etapa 2 enumeradas en el informe de cierre. Validar persistencia y autorizaciones con datos de prueba antes de producción.
