# Bloqueos y límites del backend — integración posterior al merge

Base revisada: `e797df8`, incluye `origin/feature/backend-logica` (`49f12f7`). No se modificó backend ni esquema.

## B-01. Directorio global de personas

No hay GET de listado/búsqueda de personas por nombre/CURP o proyecto. `backend/app/routers/domain.py` expone creación por proyecto y operaciones individuales. El frontend usa personas referenciadas en ORV, parcelas, unidades, comparecientes, intervinientes y pagos del núcleo. Las personas sin referencias no se pueden recuperar mediante este directorio tras abandonar la sesión. Se necesita un endpoint autorizado de búsqueda para completar ese caso.

## B-02. Reactivación e histórico de integrantes ORV

`backend/app/services/domain.py:list_orv_members` filtra siempre `OrvIntegrante.activo IS TRUE`; `incluir_historico=true` no devuelve bajas administrativas. No se pueden localizar esas bajas después de recargar para ofrecer reactivación por nombre.

`reactivate_orv_member` devuelve 409 si `entity.activo` ya es verdadero y conserva `fecha_fin`. Por tanto **no reabre una participación finalizada**. El requerimiento de reactivar finalizados no coincide con el contrato real. Hace falta definir si se permitirá reabrir la vigencia o se deberá crear una participación nueva. No debe confundirse con restaurar una baja administrativa.

## B-03. Tipos de documento

`DocumentoCreate.tipo_documento` es texto libre de hasta 80 caracteres. No se encontró un catálogo específico de tipos de documento. La captura propone tipos de documentos ya consultados y nombres del catálogo de requisitos, y permite escribir otro tipo. Un catálogo normativo de tipos requiere definición del backend/equipo funcional.

## B-04. Documentos de actividades de campo

Los requisitos admiten `actividad_campo` en su esquema, pero `project_ids_for_document_target` en `backend/app/services/access.py` no resuelve ese objetivo documental y devuelve 422 «Tipo documental no permitido». No se ofrece ese objetivo en el gestor nuevo. Para documentos asociados directamente a actividades se necesita soporte de autorización/relación en el backend; los documentos del núcleo siguen disponibles.

## B-05. Capas de obras transversales y otras unidades geoespaciales

`backend/app/routers/reporting.py:project_map` entrega únicamente `trazo_proyecto`, `nucleo_agrario` y `parcela`. `backend/app/services/geospatial_imports.py:ALLOWED_TARGETS` admite los mismos tres destinos. No hay capa geográfica de obras transversales ni geometría propia de unidades agrarias. Los conceptos administrativos existentes no equivalen a geometrías disponibles. Se requiere ampliar persistencia, importación y respuesta del mapa para ofrecer esas capas reales. El frontend no dibuja ubicaciones inventadas.

Las geometrías de núcleos y parcelas pertenecen al registro agrario compartido y se consultan mediante el vínculo del proyecto. Si se requiere una versión geométrica diferente para el mismo núcleo/parcela por proyecto, el contrato actual tampoco la modela.

## B-06. Catálogo oficial RAN vacío en QA local

El 05-10-2026, `GET /api/catalogos/nucleos?limit=5` en QA devolvió HTTP 200 y `[]`; la búsqueda por «San» tampoco encontró opciones. El endpoint existe, pero no hay datos visibles de catálogo oficial en esta instancia. La interfaz ofrece búsqueda y estado vacío; la vinculación de un resultado oficial real queda pendiente de contar con catálogo cargado y autorización del caso de escritura. No se cargaron semillas ni se sustituyó el catálogo por datos inventados.

## Decisiones que se mantienen abiertas

COP formalizados sólo colectivos; modificatorio sin padre; fórmula del valor financiero de indemnización; Resultado de asamblea de 50 caracteres; cargos ORV; cambio de asamblea asociada a convenios; significado funcional de «responsable de seguimiento». La pantalla usa «Responsables del núcleo» con el contrato actual.

Informe al cierre de esta ronda de implementación. Los límites anteriores se verificaron contra código y, para B-06, mediante consultas de lectura en QA; no mediante escrituras de negocio. La persistencia de las operaciones nuevas del frontend queda pendiente de pruebas autorizadas.
