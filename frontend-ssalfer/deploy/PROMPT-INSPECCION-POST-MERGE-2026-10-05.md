# Prompt para inspeccionar SSALFER después de la integración

Continúa en `C:\Proyectos\Software-PA-integracion-mq`. Inspecciona la integración del frontend realizada el 05-10-2026 y corrige problemas reproducibles dentro de `frontend-ssalfer/`. Conserva los cambios locales y las mejoras de las rondas 1–3. No toques `.qa-backups/`, el repositorio `C:\Proyectos\Software-PA`, backend, roles, esquema ni migraciones. UTF-8 sin BOM. No hagas commits, push ni despliegues de producción sin una instrucción expresa.

## Estado y fuentes de verdad

La base revisada fue `e797df8`, rama `feature/integracion-mq-deploy`. Se consultó GitHub: `origin/feature/backend-logica` estaba en `49f12f747a1eda4fc75930d78e0f23dd00baf422` y ya estaba incluida en HEAD. Comprueba si hubo avances antes de afirmar que sigue actualizada; no hagas merge automático sobre los cambios locales. El contrato consultado tiene 119 rutas agrupadas y 178 operaciones. Usa el código del backend y `docs/openapi.json`; no inventes contratos ni reglas.

Lee primero estos archivos de `frontend-ssalfer/deploy/`:

- `QA-INTEGRACION-2026-10-05.md`: cambios, relación endpoint–pantalla, resultados y límites de prueba.
- `BLOQUEOS-BACKEND-2026-10-05.md`: seis limitaciones con evidencia.
- `QA-UX-2026-10-03-RONDA3.md`: comportamiento previo que debe conservarse.
- `INTEGRACION-POST-MERGE-EN-CURSO.md`: seguimiento cerrado para esta ronda.

Estado máximo acreditado: **listo para QA local manual con pendientes de backend**. La persistencia de las nuevas operaciones de negocio no se ha probado. No lo declares listo para producción ni capacitación operativa completa sólo porque las pantallas abren.

## Qué se agregó y corrigió

1. **Documentos:** nueva `pages/documentos.html`, `js/documentos.js` y gestor reutilizable `js/utils/gestorDocumentos.js`. Metadatos, versiones, subida multipart con campo `archivo`, descarga autenticada, vínculos entre registros y procedencia. Contexto con 22 categorías y etiquetas legibles. Acceso desde Expediente, Seguimiento, Padrón, RAN y FIFONAFE; refresco de selectores sin recargar. El cliente de baja documental envía el motivo exigido. Los tipos propuestos proceden de documentos/requisitos existentes; no hay catálogo normativo de tipos.
2. **Derechos colectivos:** nuevas pantalla, lógica y estilos; tarjeta del núcleo habilitada. Usa afectaciones colectivas reales, unidades/destinos, convenios, indemnización y pagos. Resumen de representación y trámites. La creación reutiliza la captura de afectación con tipo colectivo fijo. Sí existe soporte mediante estas entidades: no afirmar que todo el módulo carece de backend.
3. **Reporte colectivo:** nueva pantalla y componente `reporteColectivo.js`, acceso desde núcleo y reportes del proyecto. Filtros reales y CSV. El monto declarado se muestra una vez por convenio y es no aditivo; no sumarlo por destino. Corregida la lectura del nombre real del proyecto.
4. **Núcleos:** búsqueda RAN con filtros territoriales; selección de resultado y vínculo al proyecto. Alta manual sólo como excepción explícita. Si el vínculo falla después de crear, reintentar el vínculo sin crear duplicados. Nueva gestión de datos del vínculo, TUC, COP planeados, referencias y responsables con vigencias. Baja del vínculo con motivo.
5. **Personas:** directorio contextual de personas referenciadas en ORV, titulares, comparecientes, intervinientes y pagos; resolución de nombres con caché. Búsqueda local y registro/selección inmediata. Se sustituyó el pedido de ID en ORV y la consulta por ID de la ficha de Personas por selectores de núcleo/persona. La ficha conserva edición, baja y reactivación. No simular una búsqueda global que el backend no ofrece.
6. **FIFONAFE:** intervinientes con persona, rol, evento y acreditación ORV opcional filtrada por persona y vigencia. Lista, alta y baja con motivo. Breadcrumb al núcleo corregido.
7. **Ediciones:** pagos; titulares de parcela y unidad; comparecientes; efecto y superficie de afectaciones de convenio. Baja de titular de unidad y retirada de vínculo afectación–unidad. Se permite titular persona en unidad sin parcela según el contrato. La comparación numérica evita reenviar importes sin cambios.
8. **Convenios/RAN:** consulta de trámites por convenio y edición de fecha programada de ingreso, único campo general admitido. Convenios derivados visibles mediante la relación real con el padre y el contexto del núcleo.
9. **ORV:** distinguir finalizar vigencia, eliminar registro y restaurar baja. Restauración ofrecida para bajas conocidas durante la sesión; no fingir recuperación de bajas históricas ni reapertura de participaciones finalizadas.
10. **Usuarios:** sección de proyectos asignados con consulta, asignación y revocación con motivo; selectores por nombre y carga paginada. No se modificaron roles/permisos.
11. **Geoespacial:** incluido por instrucción expresa del usuario aunque el adjunto inicial lo excluía. Mapa, historial y previsualización descartan respuestas tardías de otro proyecto. El mapa valida antes de agregar capas. Selector bloqueado durante operaciones y confirmación mediante modal común. Sólo se muestran las geometrías disponibles: trazos, núcleos y parcelas; obras transversales y geometrías propias de unidades requieren backend.
12. **UX compartida:** modales con validación asíncrona, bloqueo de doble envío, foco restaurado, Tab y Escape sólo para el modal superior. Formularios reutilizables con errores visibles; estados vacíos legibles sin tabla ancha vacía. Navegación Volver, carga y desplazamiento en pantallas nuevas. Menú móvil de estas pantallas corregido; enlace Todos los proyectos corregido.
13. **Auditoría y clientes:** revisada la corrección de heartbeat de migración 020 integrada; no se oculta ni elimina auditoría desde frontend. Reutilizado el catálogo de requisitos documentales. `AuditoriaAPI.construirQuery` ya se usa internamente. El snapshot `ReportesAPI.obtenerResumenActual` no sustituye los indicadores por periodo y permanece sin nuevo consumidor.

Los principales componentes nuevos están en `js/utils/gestion.js`, `contexto.js`, `directorioPersonas.js`, `ediciones.js`, `gestorDocumentos.js`, `paginaGestion.js` y `reporteColectivo.js`; además de `gestionNucleo.js`, `intervinientesFifonafe.js` y `asignacionesUsuarios.js`. Revisa el diff completo: hay cambios de conexión en las pantallas existentes.

## Inspección y pruebas

1. Empieza con `git status`, diff y lectura de contratos. Comprueba dependencias de scripts, sintaxis, UTF-8 sin BOM y `git diff --check`. Preserva cambios ajenos.
2. QA local: frontend `http://127.0.0.1:5184`, API mediante `/api`, backend `http://127.0.0.1:8010`. Obtén las credenciales del entorno autorizado, nunca de un archivo de código ni las imprimas. Las pruebas usan `QA_USER`, `QA_PASSWORD` y `QA_PLAYWRIGHT`.
3. Scripts reproducibles en `deploy/`: `qa-post-merge.cjs`, `qa-ediciones-post-merge.cjs`, `qa-documentos-versiones.cjs`, `qa-mapa-aislamiento.cjs`. Se validaron lecturas reales y peticiones interceptadas/abortadas. Documentos/versiones y la carrera del mapa usan fixtures sólo en respuestas del navegador. No confundir fixtures con datos persistidos.
4. `qa-ronda3.cjs` pasó como regresión: carga, formularios, desplazamiento, CSV, movimiento reducido y móvil. Si lo repites, preserva sus capturas históricas; escribe nuevas evidencias con otro nombre.
5. Referencias técnicas QA ya consultadas, que no deben pedirse como IDs al usuario: proyecto 4, núcleo 150; afectaciones 186/187; convenios 133–136 (136 deriva de 134); RAN 263; FIFONAFE 63; ORV 150; persona 843; parcela 1; unidades 193/194; indemnización 7/pago 1. Verifica que sigan existiendo antes de utilizarlas.
6. Revisa en escritorio y móvil: navegación desde proyecto/núcleo, estado vacío, errores, modales anidados, selects en cascada, formato de fechas/dinero/ha y cambios rápidos de contexto. Comprueba directorio de Personas y enlace de convenio derivado. Sin IDs como dato principal, diálogos nativos ni mensajes técnicos para operadores.
7. Para geoespacial, comprueba proyecto A → B con A respondiendo tarde; no deben aparecer sus capas ni historial/preview. No confirmes importaciones reales durante esta inspección de lectura.

Las escrituras reales de negocio requieren autorización concreta previa según el apartado 5 del prompt original. No las ejecutes por asumir que una autorización para editar archivos equivale a autorización para alterar datos. El informe incluye dos casos preparados (documento y participación FIFONAFE) con registros, operaciones y baja del dato de prueba; deben autorizarse antes de ejecutarlos. Hasta entonces valida payloads interceptados, lecturas y controles. La autenticación de la cuenta autorizada se usó para estas pruebas.

## Pendientes que deben permanecer visibles

- B-01: no hay búsqueda/listado global de personas; las personas sin referencias dejan de estar disponibles en el directorio contextual al abandonar la sesión.
- B-02: histórico ORV excluye bajas administrativas y reactivar no reabre una vigencia finalizada.
- B-03: no existe catálogo normativo de tipos de documento.
- B-04: `actividad_campo` no está soportado como objetivo documental por la resolución de acceso del backend.
- B-05: faltan capas/importación de obras transversales y geometrías propias de unidades; geometrías agrarias compartidas, sin versión distinta por proyecto.
- B-06: catálogo oficial RAN responde 200 vacío en la instancia QA; pendiente validar vínculo oficial con datos reales disponibles.

Mantén como decisiones funcionales abiertas: COP formalizados sólo colectivos, modificatorios sin padre, fórmula financiera de indemnización, resultado de asamblea de 50 caracteres, cargos ORV, cambio de asamblea asociada y significado de responsable de seguimiento. No resuelvas esas decisiones cambiando reglas de negocio en el frontend.

Entrega hallazgos reproducibles con pantalla/archivo, contrato, pasos, impacto y evidencia; corrige lo que corresponda al frontend y actualiza la lista de backend. Reporta por separado implementación, lecturas verificadas, payloads interceptados y persistencia pendiente. Termina con un dictamen de preparación para QA, sin aprobar producción con pruebas pendientes.
