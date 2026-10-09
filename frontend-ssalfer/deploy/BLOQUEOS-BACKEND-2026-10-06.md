# Pendientes de backend y decisiones — GIS y UX, 06-10-2026

Base local inspeccionada: `91b8126`, integración posterior de `feature/backend-logica`. Sólo se modificó frontend. Las observaciones siguientes se obtuvieron del código actual y de lecturas QA; no se ejecutaron escrituras GIS ni administrativas.

## B-07. Mapa publicado y consulta de versiones por proyecto

`backend/app/routers/reporting.py:523–563`, función `project_map`, sigue leyendo `TrazoProyecto`, `NucleoAgrario.geometria_poligono` y `Parcela.geometria_poligono`. No consulta las versiones `proyecto_nucleo_geometria`/`proyecto_parcela_geometria` ni el DDV. Las confirmaciones del nuevo flujo no aparecen en ese mapa. Se requiere una consulta autorizada de geometrías vigentes por proyecto y DDV, con procedencia y versión.

Las rutas de `backend/app/routers/geospatial_imports.py` ofrecen la geometría de un elemento en previsualización, no un listado de versiones DDV ni su versión vigente. `ImportacionArchivoResponse`/`ImportacionFeatureResponse` en `backend/app/schemas.py:1401–1453` tampoco exponen superficie calculada oficial del DDV. El frontend muestra la previsualización y sus componentes geométricos; no inventa una superficie oficial ni presenta staging como versión vigente. Falta exponer esas métricas/versiones para completar el resumen DDV solicitado.

Las obras transversales siguen pendientes: no se añadió un contrato para su geometría/importación en esta integración. El B-05 anterior queda parcialmente superado por las versiones de núcleos/parcelas por proyecto, pero no por la publicación del mapa ni por obras transversales.

## B-08. Estado completado de proyecto

`backend/app/schemas.py:239`, `ProyectoUpdate`, sólo permite nombre, descripción y fechas, además de campos de auditoría. La baja de `backend/app/routers/domain.py:177–185` es lógica. Se solicita definir `estado_proyecto` (activo/completado/baja), fecha, motivo, transiciones y efecto en indicadores. El frontend no interpreta `fecha_fin` como completar.

La lista filtra `Proyecto.activo` (`routers/domain.py:143`); el acceso exige proyecto activo (`services/access.py:144–163`) y la migración 015 excluye proyectos inactivos de reportes. Una baja retira el acceso operativo por ese proyecto; no equivale a borrar físicamente núcleos, asignaciones o auditoría.

## B-09. Datos laborales de usuarios y vínculo de responsables

`UsuarioBase` en `backend/app/schemas.py:86` contiene nombre, apellidos, correo y rol. No hay número de empleado ni cargo laboral. El responsable del núcleo guarda nombre/cargo/contacto/vigencias; no tiene relación formal con usuario. Se solicita agregar esos campos y definir el vínculo si se requiere sincronización futura. La precarga del frontend copia los datos disponibles y conserva cargo editable; el rol se muestra separado del cargo.

Los nombres de autores GIS no vienen en `DecisionGisResponse`/`RevisionGisDecisionResponse`, sólo `creado_por`. Para admin se resuelven mediante el listado autorizado de usuarios. Para otros roles puede mostrarse nombre no disponible; una respuesta GIS con nombre público del actor evitaría depender de permisos del directorio.

## B-10. Excel nativo del dashboard (mejora opcional)

`backend/app/routers/reporting.py:475` ofrece `/exportaciones/dashboard.csv`. No existe `/exportaciones/dashboard.xlsx`. La exportación implementada en frontend genera un libro con imágenes de los gráficos y datos disponibles. Si se requieren gráficos nativos editables de Excel y generación centralizada, se solicita un endpoint XLSX con los mismos filtros y permisos. No se agregó backend ni se usó el CSV como si fuera XLSX.

## B-11. Documentos consolidados del núcleo (mejora de rendimiento)

El contrato documental sólo ofrece `/documentos/objetivos/{tipo}/{id}`. No existe listado consolidado por proyecto-núcleo. El frontend reúne una categoría bajo demanda, con cuatro consultas simultáneas como máximo y caché; informa resultados parciales. Se solicita `GET /proyecto-nucleo/{id}/documentos` con origen legible, versión vigente, filtros y paginación para evitar múltiples consultas.

## B-12. Advertencias de reemplazo no incluidas en los candidatos

`services/gis_reconciliation.py:384–397` añade `GEOMETRIA_EXISTENTE_DISTINTA` al confirmar si existe una geometría distinta. `CandidatoGisResponse` no devuelve esta advertencia ni la geometría vigente para comparar. El frontend muestra las advertencias del elemento y, si la confirmación responde que requiere aceptar reparación/reemplazo, presenta la casilla de aceptación explícita para el reintento. Sería preferible entregar esa advertencia antes del intento, con el detalle de la versión afectada. No se acepta automáticamente.

## Contrato adicional encontrado

- Cargas de núcleos/parcelas: `alcance_entrega` es obligatorio (completa/parcial). DDV no lo admite, su entrega es completa por contrato.
- Ciclos/revisiones: `SolicitudGisRequest` exige `motivo` y UUID `clave_solicitud`; se conserva la misma clave en reintentos del formulario abierto.
- Seleccionar registra una decisión, pero no escribe geometría. Confirmar sí escribe geometría; rechazar/ignorar no la incorporan.

## Pendientes anteriores conservados

B-01 búsqueda global de personas; B-02 histórico de bajas y reapertura ORV; B-03 catálogo normativo documental; B-04 documentos de actividades; B-06 catálogo RAN sin datos. No se intentaron resolver en backend. También siguen abiertas las decisiones funcionales mencionadas en el prompt.

Lectura QA del 06-10-2026: el reporte colectivo del núcleo 150 devolvió convenio 133 con asamblea, fecha de firma, año, mes y trimestre nulos. Esto confirma la razón del vacío al filtrar por periodo. Configuración GIS del proyecto 4 respondió 200 con EPSG:4326.
