# Pendientes de backend detectados en QA UX

Fecha: 01-10-2026. Entorno: QA local, proyecto 4, proyecto-núcleo 150.
Estado: inspección de código, contratos OpenAPI y consultas reales; backend y datos de negocio sin modificar.

## 1. BLOCKED/backend — búsqueda general de personas

**Impacto:** no puede completarse un selector general por nombre/CURP en ORV, nuevas titularidades o beneficiarios de pagos que necesiten buscar personas del proyecto.

**Evidencia:** `backend/app/routers/domain.py:445` expone POST para `/proyectos/{id_proyecto}/personas`; la consulta disponible es GET `/personas/{id_persona}` (`:459`). El OpenAPI consultado no ofrece un GET de listado/búsqueda por proyecto. `frontend-ssalfer/js/api/personas.js:8-16` refleja esta limitación.

La lectura de personas ya relacionadas sí funciona: la titularidad de parcela 1 refiere a la persona 843 y permite mostrar su nombre. Esto no permite descubrir todas las personas elegibles del proyecto.

**Solicitud para backend:** definir y documentar una consulta paginada, limitada al proyecto y a los permisos actuales, que permita buscar por nombre/CURP y devuelva el identificador de persona y los campos humanos autorizados. Precisar tratamiento de personas inactivas, duplicados y ausencia de resultados. La ruta y el contrato deben acordarse en backend; no se ha supuesto ni creado un endpoint en frontend.

**Verificación posterior:** buscar una persona real permitida, comprobar aislamiento por proyecto, paginación, vacío y permisos; integrar después el selector conservando el campo de relación que cada operación espera.

## 2. BLOCKED/backend — observaciones de catálogos no se actualizan

**Impacto:** no es seguro ofrecer edición de observaciones como si se guardara; el formulario mantiene ese campo de consulta con una explicación humana.

**Evidencia de código:** `CatalogoOperativoUpdate` en `backend/app/schemas.py:210` hereda la entrada de auditoría. `update_catalog_option` en `backend/app/services/domain.py:77-94` excluye explícitamente `observaciones` del diccionario de actualización y no asigna posteriormente ese campo. Se confirmó por inspección, sin ejecutar un PATCH sobre datos reales.

La creación es distinta: utiliza `_audit_values`, por lo que no se concluye que las observaciones fallen también al crear. Además, `activo: true` se consume mediante `pop` sin reactivar la opción; no se añadió una acción Reactivar.

**Solicitud para backend:** decidir si las observaciones se pueden modificar. Si se permiten, persistirlas y auditar el cambio, definir el significado de null/vacío y verificar lectura posterior. Si son inmutables, expresar esa restricción en el contrato. La reactivación requiere una definición propia antes de exponerla en la UI.

**Verificación posterior:** prueba de servicio/integración sobre un fixture aislado: cambiar observaciones, consultar y comprobar persistencia; no utilizar registros operativos para esta prueba.

## 3. BLOCKED/backend — ciclo incompleto de asignaciones usuario-proyecto

**Impacto:** el contrato actual permite listar y crear asignaciones, pero no gestionar su revocación, actualización o reactivación. Este pendiente ya estaba señalado; no se modificaron roles ni permisos.

**Evidencia:** `backend/app/routers/domain.py:1812-1838` contiene GET y POST `/proyectos/{id_proyecto}/usuarios`. El GET devuelve asignaciones activas. `assign_user_to_project` en `backend/app/services/domain.py:1353-1372` crea una nueva instancia de `UsuarioProyecto`; no recupera/reactiva una anterior. El OpenAPI revisado no ofrece operaciones para completar ese ciclo.

**Solicitud para backend:** acordar las operaciones soportadas, autorización, auditoría, manejo de duplicados y comportamiento al reasignar un vínculo inactivo. No equiparar una asignación con la responsabilidad funcional del proyecto.

**Verificación posterior:** pruebas de integración con fixtures de vínculo activo/inactivo y usuarios permitidos/no permitidos. La definición de responsables sigue en REVIEW.

## No clasificados como nuevos bugs

- No se observaron respuestas 500 en las rutas ejercitadas; estos hallazgos son limitaciones de contrato o implementación, no incidentes 500 reproducidos.
- Documentos vacíos, intervinientes FIFONAFE vacíos y ausencia de indemnización en la afectación individual son respuestas válidas de QA.
- El límite de 50 caracteres del resultado de Asamblea requiere decisión y backend si se amplía; se conserva.
- Se mantienen pendientes de decisión: COP formalizados colectivos, modificatorio sin padre permitido, responsables, fórmula financiera de indemnización, cargos ORV y cambios de asamblea asociada a convenios.
- Geografía/mapa y roles/permisos continúan en standby.

No se crearon datos, endpoints ni relaciones para ocultar estas limitaciones.
