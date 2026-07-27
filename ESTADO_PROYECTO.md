# ESTADO DEL PROYECTO - SOFTWARE-PA

> **Instrucción para la IA:** Si acabas de unirte a la conversación, lee este documento completo antes de generar cualquier código. Contiene las reglas estrictas de negocio, arquitectura y el punto exacto donde nos quedamos.

## 1. Descripción General
Sistema de gestión, control y analítica para la liberación de derecho de vía (vías férreas). Integra datos geoespaciales (PostGIS), legales, documentales y financieros.

## 2. Stack Tecnológico
* **Backend:** Python (FastAPI), SQLAlchemy (ORM), Pydantic (Validación), PostgreSQL + PostGIS (Base de datos).
* **Frontend:** React (Vite), Axios, Tailwind (o similar).

## 3. Reglas de Oro y Lineamientos de Auditoría (OBLIGATORIAS)
* **Auditoría Destructiva (White-Box):** No se asume que el código "está bien". Siempre verificar vulnerabilidades IDOR (Cross-tenant), N+1 queries en ciclos, inyecciones de dependencias faltantes y validaciones cruzadas entre llaves foráneas.
* **Trazabilidad Absoluta:** Todos los endpoints de creación/actualización deben invocar `set_audit_context(db, current_user.id_usuario)` antes del commit, para que el `AuditableMixin` de SQLAlchemy y la función SQL `set_current_user()` registren en la bitácora quién hizo qué.
* **Borrado Lógico:** Prohibido hacer `DELETE` físico. Todas las entidades usan `activo = False`, registran `fecha_baja`, `id_usuario_baja` y un `motivo_baja` obligatorio.
* **Integridad Geoespacial:** Se usa `ST_AsText()` para consultas de lectura. La inserción desde GeoJSON (`importar-geojson`) limpia los datos, asigna las FKs y castiga correctamente la geometría mediante `ST_SetSRID(ST_GeomFromGeoJSON(...), 4326)`.
* **Manejo de Fechas:** Todo timestamp debe generarse estrictamente con `datetime.now(timezone.utc)`.
* **Sanitización de Errores:** Nunca devolver mensajes crudos de PostgreSQL al cliente para evitar *Information Disclosure*. El handler global ya limpia los `IntegrityError` e `InternalError`.

## 4. Hitos Alcanzados (Fase 1: Backend Core y QA Completo)
Se resolvieron exitosamente 20 vulnerabilidades críticas operativas en el backend (Bugs BUG-01 al BUG-20), incluyendo:
* Eliminación de cuellos de botella por Query N+1.
* Fixes de validaciones Pydantic (Tipado estricto con `Literal`).
* Implementación de seguridad transversal contra IDOR (validando que al relacionar Asambleas, Convenios, Fifonafe, el núcleo agrario y tramo correspondan jerárquicamente, evitando corrupción de datos cruzados).
* Actualización progresiva de montos financieros habilitada en esquemas Pydantic.

## 5. Próximo Paso INMEDIATO (Fase 2: Proyectos y Refactorización del Front-End)
El backend core está certificado. **La próxima tarea a realizar es:**
1. **Crear el módulo "Proyecto" en el Backend:**
   * Archivo de migración `.sql` para crear la tabla `proyecto`.
   * Agregar la clase `Proyecto` en `models.py`.
   * Crear los esquemas de validación en `schemas.py`.
   * Desarrollar los endpoints CRUD en `main.py`.
2. **Refactorizar `Dashboard.jsx` en el Frontend:**
   * Eliminar todos los valores en código duro (*hardcodeados*).
   * Conectar el frontend con el nuevo endpoint de proyectos para volver dinámicos los selectores y tarjetas de métricas.

---
**Agente de IA:** Con esta información, dile al usuario que estás listo para ejecutar el paso 1 de la Fase 2 (Crear el módulo Proyecto) y espera su confirmación.
