# Evidencia y pendientes de backend — ronda 2

Fecha de cierre de revisión: 02-10-2026. Proyecto 4, proyecto-núcleo 150, base `db_integracion_mq_qa_local`.
No se modificaron backend, esquemas, migraciones ni datos de negocio. Las consultas SQL se ejecutaron dentro de `BEGIN READ ONLY` y finalizaron con `ROLLBACK`.

## Diagnóstico corregido: observaciones de eventos FIFONAFE sí están soportadas

La premisa del prompt de entrada no coincide con el código ni con los datos actuales:

- `backend/app/services/domain.py:1133`: `add_fifonafe_event` excluye observaciones de `model_dump`, pero inmediatamente incorpora `**_audit_values(user.id_usuario, data)`.
- `backend/app/services/domain.py:95`: `_audit_values` copia `data.observaciones`.
- `backend/app/routers/domain.py:1523`: el PATCH de eventos usa `service.update_entity`.
- `backend/app/services/domain.py:111` y `backend/app/services/common.py:38`: la actualización aplica los campos presentes mediante `model_dump(exclude_unset=True)`, sin excluir observaciones.
- GET real `/api/fifonafe/63/eventos` devuelve el evento 208 con observaciones guardadas. SELECT de la misma fila en QA confirma ese valor.
- `chk_evento_fifonafe_dato`, inspeccionada con `pg_get_constraintdef`, acepta número de oficio, fecha de oficio, fecha del evento, documento **u observaciones no vacías**.

Por tanto, no se deshabilitó Observaciones ni se eliminó como evidencia válida. La petición de hacerlo estaba condicionada a que el backend no lo persistiera; esa condición no se cumple. No confundir este flujo con la limitación real de observaciones en la actualización de **catálogos**, documentada en la primera ronda.

## Diagnóstico corregido: las fechas de QA no están intercambiadas por el editor

El evento 208 del trámite QA-FIF-63-EDIT devuelve y almacena:

| Campo | Valor real |
| --- | --- |
| `fecha_oficio` | `2026-09-30` |
| `fecha_evento` | null |

La prueba de navegador comprobó que los dos controles precargan exactamente esos valores. El alta inicial en `js/fifonafe.js` tiene una entrada etiquetada Fecha del oficio y la envía como `fecha_oficio`; no se detectó un mapeo cruzado. No se trasladaron fechas entre columnas ni se corrigieron datos históricos por suposición.

Se aplicó un PATCH mínimo en frontend: sólo campos que difieren del formulario inicial. Sin cambios no hay petición. Las fechas vacías intactas quedan fuera del PATCH.

## BLOCKED/backend — diagnóstico ambiguo de conflictos FIFONAFE

**Evidencia:** `backend/app/services/domain.py:1145` pasa a `_persist` el mensaje «El evento FIFONAFE no es válido o repite ordinal». `commit_or_conflict` en `backend/app/services/common.py` convierte errores de integridad/BD en 409 con ese mensaje. La restricción de evidencia aparece en `backend/db/migrations/008_fifonafe_evolucion_forward_only.sql:53`.

**Impacto:** el cliente no puede distinguir con certeza un ordinal ocupado de otra restricción de integridad sólo a partir del mensaje. La validación local de duplicados no evita una carrera con otra sesión.

**Mitigación frontend aplicada:** evidencia explícita, comprobación de ordinal activo ya cargado y mensaje orientativo al recibir 409. La lista local no sustituye la validación de concurrencia del servidor.

**Solicitud técnica:** clasificar la restricción que falla y devolver códigos de error estables para ordinal duplicado, evidencia insuficiente y demás conflictos, sin exponer SQL ni detalles sensibles. Probar con fixtures aislados. No se reprodujo un nuevo 409 enviando datos de negocio en esta ronda; el hallazgo del mensaje ambiguo está confirmado por código.

## REVIEW/backend — mensaje genérico al crear afectaciones

**Evidencia:** `create_affectation` en `backend/app/services/domain.py:773-789` utiliza «La afectación no cumple el ámbito o la parcela pertenece a otro núcleo» como mensaje común de persistencia.

La restricción real `chk_afectacion_tipo_cop_revision` exige detalle no vacío cuando `tipo_cop_revision_pendiente` es true (`backend/db/migrations/001_baseline_v1.sql:1513`, confirmada también en la BD QA). `fn_validar_afectacion_tipo_cop` valida el catálogo COP; son causas distintas que pueden quedar ocultas por el mensaje genérico.

El navegador confirmó que el detalle se exige y que el payload lo incluye al marcar revisión. Se interceptó y abortó esa petición antes de persistir: **no se afirma haber confirmado el éxito de una nueva afectación en BD** ni reproducido el error de ámbito reportado. Las afectaciones reales 186/187 tienen revisión false y detalle null, combinación válida.

**Solicitud técnica si reaparece:** obtener la restricción exacta del error en los logs del servidor y diferenciar el mensaje por causa. No eliminar una validación de ámbito ni cambiar reglas desde frontend.

## Pendientes anteriores conservados

Ver `BLOQUEOS-BACKEND-2026-10-01.md`:

1. Búsqueda/listado general de personas por proyecto.
2. Observaciones al actualizar catálogos y definición de reactivación.
3. Ciclo de revocación/reactivación de asignaciones usuario-proyecto.

No se inventaron endpoints para resolverlos. ORV consulta una persona conocida por su identificador y presenta el nombre real cuando está disponible; no ofrece una búsqueda simulada.
