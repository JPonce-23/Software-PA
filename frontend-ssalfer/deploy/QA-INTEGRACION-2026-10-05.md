# Integración del frontend tras el merge — 05-10-2026

Estado: **listo para QA local manual, con los límites de backend documentados**. No constituye aprobación para producción. Los cambios están en `C:\Proyectos\Software-PA-integracion-mq\frontend-ssalfer`. No se modificaron backend, migraciones, esquema ni roles; no se hicieron commits, push ni despliegue de producción. Se reconstruyó y recreó únicamente el servicio local `frontend_ssalfer`.

La base `e797df8` contiene `origin/feature/backend-logica` en `49f12f7`, verificado mediante fetch al retomar la ronda. Se revisaron los contratos de código y OpenAPI: 119 rutas agrupadas y 178 operaciones. La corrección de auditoría/heartbeat de la migración 020 está en esa rama integrada; no se ocultan ni borran registros de auditoría desde el frontend. El documento externo de derechos colectivos mencionado en el prompt no se encontró en el árbol remoto.

## Cambios implementados

| Área | Cambios y comportamiento |
| --- | --- |
| Documentos | Nueva pantalla `documentos.html` y gestor reutilizable. Alta y edición de metadatos; sugerencias de tipo, estado, título, fecha, folio y descripción. Versiones, carga de archivo, descarga, vínculo de un documento existente a otro registro y consulta/registro de procedencia. Categorías y registros con referencias legibles, limpieza en cascada y descarte de respuestas tardías. |
| Selectores documentales | Acceso al gestor desde Expediente, Seguimiento, Padrón, RAN y FIFONAFE. Actualización de colecciones y selectores sin recargar la página; conservación de la selección actual. |
| Derechos colectivos | Nueva pantalla `derechosColectivos.html`, tarjeta activa en el núcleo. Consulta afectaciones colectivas reales; bloques de unidades/destinos, convenios, indemnización y pagos. Accesos a creación y fichas existentes. Resumen de ORV, padrón, asambleas/convocatorias, RAN y FIFONAFE. Nueva afectación reutiliza la captura existente fijando el tipo colectivo. |
| Reporte colectivo | Nueva pantalla `reportesColectivos.html`, también integrada en Derechos colectivos y accesible desde Reportes del proyecto. Filtros por proyecto, núcleo, convenio, asamblea, tipo de convenio, COP, destino, año, mes y trimestre. Monto declarado una vez por convenio, rotulado no aditivo. CSV con encabezados legibles y protección frente a fórmulas en texto. |
| Núcleos | Búsqueda en catálogo RAN por nombre y filtros territoriales, selección por nombre/tenencia/municipio/entidad y vínculo mediante la identidad real. Alta manual explícitamente excepcional. Si la creación funciona y el vínculo falla, se conserva el núcleo creado para reintentar sólo el vínculo. Edición de residencia, COP planeados y TUC; baja del vínculo al proyecto con motivo. Referencias y responsables del núcleo con altas/ediciones y vigencias. |
| Personas | Directorio real del núcleo a partir de referencias existentes, resolución de fichas con caché y búsqueda local por nombre/CURP. Disponible en ORV, titulares, comparecientes y pagos. Alta de persona desde el directorio y selección inmediata. La ficha de Personas también usa un selector de núcleo y directorio; mantiene edición, baja y reactivación. No ofrece búsqueda global ficticia. |
| FIFONAFE | Sección de intervinientes con persona, rol, evento y acreditación ORV opcional. La acreditación se filtra por persona y vigencia en la fecha del evento. Lista, alta y baja con motivo. |
| Ediciones pendientes | Pagos, titulares de parcela y unidad, comparecientes y efecto/superficie de afectaciones de convenio. Baja de titular de unidad y retirada del vínculo afectación–unidad. Las unidades sin parcela permiten incorporar una persona del directorio conforme al contrato. |
| Convenios y RAN | Ficha RAN permite editar la fecha programada de ingreso, único campo general admitido. Los trámites del convenio usan su consulta específica. Derivados obtenidos de convenios reales del núcleo por relación de padre; se muestran sus enlaces. |
| ORV | Acciones diferenciadas de finalizar participación, eliminar registro con motivo y restaurar una baja conocida durante la sesión. La reactivación no cambia fechas de vigencia. La recuperación de bajas anteriores y la reapertura de finalizados tienen límites de backend: ver B-02. |
| Usuarios | Sección Proyectos asignados: consulta, alta por selector de usuario y revocación con motivo. Carga paginada de usuarios/proyectos. No cambia el rol ni los permisos definidos por el servidor. |
| Geoespacial | El mapa descarta una respuesta anterior **antes de agregar sus capas**. Historial y previsualización de importaciones comprueban el proyecto y la vigencia de la consulta. Se bloquea el selector durante operaciones y se confirma la importación mediante el modal común. Se conservan las capas reales de trazos, núcleos y parcelas. Obras transversales requieren backend: B-05. |
| UX común | Modales con validación asíncrona, bloqueo de envío duplicado, foco restaurado, navegación por Tab y Escape sólo en el modal superior. Formularios compartidos con errores visibles y comparación numérica para no reenviar importes sin cambios. Pantallas nuevas con Volver fijo, indicador de carga y reglas de desplazamiento. Menú móvil corregido en esas pantallas. Breadcrumb de FIFONAFE y Todos los proyectos corregidos. |

## Contratos conectados

Las rutas siguientes son relativas a `/api`.

| Endpoint o familia | Pantalla/componente | Verificación en esta ronda |
| --- | --- | --- |
| GET/POST `/documentos/objetivos/{tipo}/{id}`; PATCH `/documentos/{id}` | Documentos / gestor contextual | Consultas reales; alta interceptada. Edición implementada; persistencia pendiente. |
| GET/POST `/documentos/{id}/versiones`; GET `/documentos/versiones/{id}/descarga` | Versiones y archivos | Fixtures de lectura y descarga; multipart comprobado con campo `archivo`; POST abortado. |
| POST `/documentos/{id}/vinculos/{tipo}/{id}` | Vincular documento | Selectores origen/destino y petición interceptada. |
| GET/POST `/trazabilidad/objetivos/{tipo}/{id}` | Procedencia | Consulta y formulario; POST interceptado. |
| GET `/proyecto-nucleo/{id}/afectaciones?tipo=colectivo` y sus unidades/convenios/indemnización/pagos | Derechos colectivos | Lectura real de QA. |
| GET `/reportes/convenios/colectivos-destino` | Reporte colectivo | Lectura real, filtros y exportación local. No usa el alias oculto. |
| GET `/catalogos/nucleos`; POST `/proyectos/{id}/nucleos` | Ficha de proyecto | Catálogo responde 200 vacío en QA; selección oficial real pendiente de datos. Alta/vínculo implementados. |
| PATCH/DELETE `/proyecto-nucleo/{id}` | Ficha del núcleo | PATCH interceptado; baja conectada con motivo, sin ejecución real. |
| GET/POST referencias/responsables del núcleo; PATCH `/referencias/{id}` y `/responsables/{id}` | Ficha del núcleo | Lecturas reales y altas interceptadas; ediciones implementadas. |
| POST `/proyectos/{id}/personas`; GET `/personas/{id}` | Directorio / Personas | Lecturas reales y selección desde la ficha; alta conectada, sin creación real. |
| GET/POST `/fifonafe/{id}/intervinientes`; DELETE `/intervinientes-fifonafe/{id}` | Ficha FIFONAFE | Lectura real, alta interceptada; baja conectada. |
| PATCH `/pagos/{id}`; PATCH `/parcela-titulares/{id}` | Indemnización / Parcela | Peticiones interceptadas; conservan campos sin cambios. |
| POST titulares de unidad; PATCH/DELETE `/unidad-agraria-titulares/{id}` | Unidad agraria | Alta de persona en unidad sin parcela interceptada. Edición/baja conectadas; no hay titulares de unidad en la muestra QA para comprobar persistencia. |
| DELETE `/afectacion-unidades-agrarias/{id}` | Detalle de afectación | Acción con motivo; no se ejecutó baja real. |
| PATCH/DELETE `/convenio-comparecientes/{id}`; PATCH `/convenio-afectaciones/{id}` | Ficha convenio | Edición de compareciente interceptada; baja existente conservada; efecto/superficie conectado y validado contra esquema. |
| GET `/convenios/{id}/tramites-ran`; PATCH `/tramites-ran/{id}` | Ficha convenio / RAN | Lectura real y PATCH de fecha interceptado. |
| DELETE `/orv-integrantes/{id}`; POST `/orv-integrantes/{id}/reactivar` | ORV | Clientes/acciones conectados dentro de los límites B-02; no se ejecutaron bajas/restauraciones. |
| GET/POST `/proyectos/{id}/usuarios`; DELETE `/proyectos/{id}/usuarios/{id_usuario}` | Usuarios | Lectura y apertura de formulario reales; no se asignaron/revocaron usuarios. |
| GET `/proyectos/{id}/mapa` y consultas de importaciones | Mapa / Gestión geoespacial | Prueba de respuestas fuera de orden con fixture; sin importaciones reales. |

`CatalogosAPI.obtenerRequisitosDocumentales` se reutiliza desde el cliente documental. `AuditoriaAPI.construirQuery` ya es un ayudante interno usado por ambas consultas de auditoría; no era una pantalla pendiente. `ReportesAPI.obtenerResumenActual` permanece disponible sin nuevo consumidor: corresponde a un snapshot, no sustituye los indicadores actuales por periodo ni el reporte de destinos. No se alteró su significado.

## Pruebas y límites

- Verificación final: sintaxis de 75 archivos JS y cuatro scripts CJS nuevos; UTF-8 sin BOM en los 71 archivos de texto modificados o nuevos revisados; dependencias locales de pantallas nuevas/Personas y `git diff --check` correctos.
- `qa-post-merge.cjs`: las 22 categorías del contexto resolvieron referencias válidas en QA; Documentos, Derechos colectivos, reporte y accesos del núcleo funcionaron sin errores JS ni respuestas API fallidas. Alta documental interceptada.
- `qa-ediciones-post-merge.cjs`: nueve peticiones de alta/edición interceptadas. Núcleo, referencia, responsable, titular de parcela, pago, compareciente, RAN, interviniente FIFONAFE y titular de unidad. Sin errores JS ni respuestas GET fallidas en la ejecución final. Catálogo RAN vacío detectado expresamente.
- `qa-documentos-versiones.cjs`: descarga, multipart, procedencia, vínculo y ventanas anidadas/Escape; tres escrituras interceptadas. Usa documentos ficticios sólo en respuestas del navegador, nunca insertados en QA.
- `qa-mapa-aislamiento.cjs`: dos proyectos reales visibles y geometrías de prueba sólo en respuestas interceptadas. La respuesta atrasada no agregó capas al cambiar al segundo proyecto.
- Regresión `qa-ronda3.cjs`: carga, retardo, duración mínima, errores/cancelación, formularios, desplazamiento, CSV, movimiento reducido y móvil pasaron. Cero escrituras de negocio. Las capturas históricas se conservaron; las nuevas usan nombres propios.
- Lectura adicional: directorio desde `persona.html` seleccionó una persona QA real; derivados de convenio enlazaron el hijo real; la pantalla colectiva no mostró valores `undefined`.
- Inspección visual de Documentos en móvil y Derechos colectivos en escritorio. Se corrigió el solapamiento del menú móvil detectado en esa revisión.
- Tras los últimos ajustes se reconstruyó y recreó sólo el frontend local y se repitió `qa-documentos-versiones.cjs`: correcto, con tres escrituras interceptadas. La captura móvil confirma que el estado vacío documental se lee completo. Se comprobó que no hay modificaciones de archivos versionados fuera de `frontend-ssalfer/` ni cambios en las capturas históricas de ronda 3; `.qa-backups/` se dejó intacto.

No se verificó commit/persistencia/relectura posterior de operaciones de negocio, concurrencia entre operadores ni un despliegue de producción. No se subieron archivos ni se confirmaron importaciones geográficas reales. No se incorporaron datos al catálogo RAN. No se enviaron mensajes ni se modificó GitHub.

## Casos concretos de escritura pendientes de autorización

El apartado 5 del prompt del usuario exige autorización previa para escrituras reales. Están preparados para una siguiente prueba, sin haberlos ejecutado:

1. En proyecto QA 4, núcleo 150: crear documento `QA Integración documental 2026-10-05`, subir `qa-integracion.txt` con texto de prueba, vincularlo a la afectación colectiva 186, registrar procedencia y comprobar relectura. Dar de baja únicamente ese documento de prueba con motivo; conservará auditoría.
2. En FIFONAFE QA 63, núcleo 150: incorporar a la persona QA 843 como beneficiaria sin acreditación ORV/evento, comprobar relectura y dar de baja únicamente la participación creada para la prueba.

Los casos de catálogo RAN, restauración de bajas ORV anteriores y obras transversales dependen primero de resolver los bloqueos documentados. No deben ejecutarse sobre datos operativos como sustituto de QA.

Bloqueos y decisiones: `BLOQUEOS-BACKEND-2026-10-05.md`. Prompt de inspección: `PROMPT-INSPECCION-POST-MERGE-2026-10-05.md`.
