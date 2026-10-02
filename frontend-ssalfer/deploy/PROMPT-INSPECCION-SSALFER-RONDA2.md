# Prompt para inspección del sistema SSALFER después de la ronda 2

Necesito una inspección del frontend de SSALFER sobre el estado real actual del repositorio. Los cambios siguientes ya están aplicados: no los reimplementes ni atribuyas todo el diff del worktree a esta ronda.

## Entorno y reglas

- Repositorio local: `C:\Proyectos\Software-PA-integracion-mq`.
- Frontend: `frontend-ssalfer/`.
- QA frontend: `http://127.0.0.1:5184/`.
- QA backend: `http://127.0.0.1:8010/`.
- Base QA: `db_integracion_mq_qa_local`.
- Proyecto 4: QA Flujo Integral SSALFER 2026.
- Proyecto-núcleo 150: QA NÚCLEO AGRARIO 001.
- Inspeccionar con rol admin. Geografía, mapa, roles y permisos quedan fuera del alcance.
- En esta tarea inspecciona y reporta; no cambies código ni datos automáticamente. Si una corrección es necesaria, describe primero el hallazgo con evidencia.
- No hagas commits, restauraciones de archivos, resets, migraciones ni despliegues. Conserva las modificaciones acumuladas y UTF-8 sin BOM.
- No inventes endpoints, campos, respuestas ni registros. No incluyas credenciales en archivos o informes.

## Documentos que debes leer primero

1. `frontend-ssalfer/deploy/QA-UX-2026-10-01.md`.
2. `frontend-ssalfer/deploy/BLOQUEOS-BACKEND-2026-10-01.md`.
3. `frontend-ssalfer/deploy/QA-UX-2026-10-02-RONDA2.md`.
4. `frontend-ssalfer/deploy/BLOQUEOS-BACKEND-2026-10-02-RONDA2.md`.

Después revisa `git status --short`, los diffs pertinentes, el HTML/JS actual y los contratos de `js/api/`. El código, las respuestas reales y los datos QA prevalecen sobre diagnósticos de prompts anteriores.

## Cambios anteriores que deben conservarse

La primera ronda incorporó los seis selectores dependientes restantes de Seguimiento, precarga y limpieza de relaciones, protección frente a respuestas tardías, modales/toasts, fechas y referencias humanas. Conservó `entidad_tipo`/`entidad_id` y las restricciones del PATCH.

También añadió documentos contextuales para RAN/FIFONAFE, selectores de relaciones en Expediente, filtros humanos de Auditoría/reportes y referencias funcionales en Convenios/Estado financiero. La separación dinero/superficie y las reglas existentes no se modificaron.

## Qué se modificó en la segunda ronda

### FIFONAFE

- `js/fichaFifonafe.js`: regla de evidencia visible; ordinal duplicado detectado entre eventos activos; mensaje orientativo ante 409; bloqueo del envío mientras guarda.
- Edición con PATCH únicamente de campos modificados. Sin cambios se cierra con aviso y no se llama a la API. Las fechas vacías intactas no se envían como null.
- `js/fifonafe.js`: validación de evidencia y ordinales repetidos en eventos iniciales antes de crear el trámite, para evitar altas parcialmente inválidas detectables desde el formulario.
- **Corrección del diagnóstico:** Observaciones sí se persisten en eventos FIFONAFE mediante `_audit_values`, y el PATCH también las contempla. La BD permite observaciones como evidencia. El campo se conservó; no está bloqueado como las observaciones de catálogos.
- El evento 208 del trámite 63 devuelve `fecha_oficio=2026-09-30` y `fecha_evento=null`. API, BD y formulario coinciden. No se trasladaron fechas ni se modificaron registros históricos.

### Navegación y reportes

- Nuevo `js/utils/navegacion.js`: botones Volver con destinos fijos y contexto.
- Se añadieron botones en Afectación, ORV, Parcela, Unidad agraria, Persona, Estado financiero, Ficha de proyecto, Nuevo proyecto, Usuarios, Auditoría, Cambiar contraseña, Catálogos y los tres reportes.
- Persona respeta un `return_to` local válido y conserva el flujo existente `volverConPersona` tras una creación.
- Ficha Convenio, Ficha RAN, alta RAN y Expediente ya no usan `history.back()`. Asamblea/ORV pasan el núcleo al abrir un nuevo trámite RAN.
- Los enlaces rotos a `reporteAvancePeriodo.html` apuntan a `reporteActividadesPeriodo.html`, conservando `id_proyecto`. El script sigue siendo `reporteAvancePeriodo.js`.
- Ficha del proyecto: Reportes muestra tres bloques con icono, título y descripción, grid horizontal/apilado y hover/focus. Se mantienen los IDs y las URLs existentes.

### Diálogos y mensajes

- `js/utils/ui.js`: modal compartido con validación opcional y `solicitarTexto` para motivos/identificadores.
- `js/api/cliente.js`: errores sin contenedor mediante toast o aviso accesible, sin alterar contratos de red.
- Se migraron los avisos nativos de los módulos solicitados: ORV, Persona, RAN, Convenios, Unidades, Detalle de afectación, Indemnización, Asamblea, Proyectos, Parcela, Padrón y FIFONAFE.
- Nuevo proyecto bloquea un segundo envío mientras está abierta la confirmación.
- Los mensajes previos a redirección quedan visibles en modal hasta cerrarlo.
- El aviso nativo de autenticación en `js/api/auth.js` no se modificó; no afirmar que desaparecieron todos los diálogos nativos del sistema completo.

### Correcciones adicionales confirmadas

- ORV: etiqueta Fecha de inicio de participación; modal validado para consultar una persona conocida y mostrar su nombre real; nombres de integrantes resueltos por consultas existentes. No se inventó búsqueda general de personas.
- Avalúo: Cancelar ya no anuncia un guardado; descarta los valores temporales y reabrir recupera los datos originales. El mensaje de éxito pertenece al guardado real.
- Unidades agrarias: corregido acceso nulo a `unidadSeleccionada.id_parcela` que detenía la carga inicial. El botón de titular se actualiza al cargar una unidad, manteniendo el requisito de parcela relacionada.
- Seleccionar/vincular ya tenía icono `bi-link-45deg`; se verificó después de corregir la carga.
- Detalle de afectación presenta textos humanos para FIFONAFE y notas. El texto técnico señalado en Afectación era un comentario HTML, no contenido visible.

## Qué debes inspeccionar

1. FIFONAFE: datos reales de fechas, edición sin cambios, PATCH mínimo, evidencia y ordinal duplicado. No confundir una fecha ya guardada en oficio con un bug del editor.
2. Navegación: probar todos los destinos Volver y enlaces de reportes con/sin contexto; Persona abre su modal automáticamente si llega con `return_to`, y permite cancelarlo antes de volver.
3. Auditoría: comprobar que Cambios/Accesos muestran exclusivamente su panel.
4. Avalúo: modificar temporalmente, cancelar y reabrir sin persistir.
5. Afectación: revisión COP exige detalle y el payload lo incluye. La aceptación final en BD no se comprobó con escritura.
6. Indemnización: descripción del estatus precargada en edición, aunque la consulta la oculte cuando no es Otro.
7. ORV: identificador inválido deja error en modal; persona conocida 843 resuelve QA Gabriela Titular. Cancelar sin guardar integrante.
8. Unidades: listado real de QA-UA-001 y QA-UA-IND-001, navegación y vínculo sin acceso nulo.
9. Reportes FIFONAFE: parámetros del proyecto 4, respuesta real y tabla o vacío comprensible; ninguna respuesta simulada.
10. Reportes en ficha: tres opciones claras, teclado/focus y apilado en móvil. Revisar especialmente el menú fijo heredado que se superpone a parte del contenido a 390 px; el grid fue comprobado, pero la navegación móvil global no está certificada.
11. Motivos y confirmaciones de Persona/Compareciente: validar y cancelar sin modificar registros.
12. Regresión de los flujos de Seguimiento y Expediente de la primera ronda.

## Verificación y límites

- Se construyó y recreó únicamente `frontend_ssalfer` con `.env.qa-local` y los tres compose canónicos. No hubo despliegue a servidor.
- Se comprobó sintaxis, UTF-8 sin BOM y `git diff --check`.
- Pruebas disponibles: `deploy/qa-seguimiento.cjs` y `deploy/qa-ronda2.cjs`. Requieren Edge, Playwright externo y credenciales mediante variables de entorno; no están incrustadas en los scripts.
- La prueba de ronda 2 intercepta y aborta las solicitudes de escritura usadas para inspeccionar payloads: eso no demuestra persistencia en backend. Sus consultas GET sí son reales.
- **No se ejecutó el ciclo de alta/edición/baja real de Seguimiento.** La revisión automática lo rechazó por conflicto con la prohibición previa de crear datos de prueba. Se pidió autorización específica; no debe inferirse de una solicitud genérica de continuar. Mantén esta prueba pendiente hasta recibir autorización inequívoca para un solo evento QA y su baja lógica posterior.

## Backend y decisiones pendientes

Conserva los bloqueos anteriores: búsqueda general de personas, actualización de observaciones en catálogos y gestión completa de asignaciones usuario-proyecto.

Nuevo hallazgo de código: el 409 de eventos FIFONAFE mezcla ordinal duplicado y otros conflictos. Afectaciones también utiliza un mensaje común que puede ocultar una restricción diferente. Documenta la causa real antes de atribuir un error al ámbito, a una parcela o a observaciones.

No reinterpretes como bugs ni cambies decisiones sobre COP colectivos, modificatorios sin padre, responsables, fórmula financiera, límite del resultado de Asamblea, cargos ORV o asambleas vinculadas a convenios.

## Entrega esperada

Entrega un informe por pantalla con PASS, REGRESIÓN, REVIEW/datos o BLOCKED/backend. Para cada hallazgo incluye ruta/archivo, pasos, resultado esperado/observado y evidencia real. Distingue una prueba de lectura/interceptación de una escritura realmente persistida. No declares listo para producción; el máximo estado es listo para QA local manual con pendientes explícitos.
