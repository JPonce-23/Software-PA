# QA y mejora de lectura — Gestión geoespacial

Fecha: 14 de octubre de 2026.

La primera lectura ahora muestra estados breves, acciones y resúmenes. Las explicaciones completas se consultan mediante desplegables cerrados inicialmente. Los avisos de error y de riesgo siguen identificados; no se eliminó información de diagnóstico ni se cambiaron las reglas de validación.

## Alcance de esta ronda

Cambios de producto exclusivamente en `pages/gestionGeoespacial.html`, `js/gestionGeoespacial.js`, `js/conciliacionGeoespacial.js`, `styles/gestionGeoespacial.css` y `styles/conciliacionGeoespacial.css`.

Se conservaron los cambios locales anteriores. No se modificaron backend, endpoints, estructura de base de datos ni archivos del mapa en esta ronda. Los enlaces existentes al mapa conservan sus parámetros y comportamiento. No se agregaron selectores ni pasos, no se hizo commit ni push. Trazo del proyecto continúa fuera del selector de nuevas cargas; DDV permanece disponible.

## Inventario antes/después

Las citas con puntos suspensivos identifican el texto anterior; en la aplicación, el desplegable conserva el contenido completo, no la versión abreviada de esta tabla.

| Sección / texto anterior | Primera lectura actual | Dónde está la explicación completa / motivo |
| --- | --- | --- |
| DDV: «Carga los polígonos del derecho de vía del proyecto en un archivo GPKG.» | «Carga el archivo GPKG del derecho de vía.» | **Ver requisitos del archivo**. Conserva la referencia a polígonos. |
| Núcleos: «Primero registra y vincula los núcleos al proyecto. El sistema compara nombre, municipio, entidad y tipo de núcleo…» | «Los núcleos deben estar registrados y vinculados al proyecto.» | **Ver requisitos del archivo**. Mantiene comparación por nombre, municipio, entidad, tipo y clave oficial; también la diferencia entre falta de coincidencia y geometría inválida. |
| Parcelas: «Primero registra las parcelas y su relación con los núcleos del proyecto…» | «Las parcelas deben estar registradas y relacionadas con los núcleos.» | **Ver requisitos del archivo**. Mantiene comparación por núcleo/número, que el GPKG no crea registros y la necesidad de confirmar asociaciones. |
| Alcance: «Elige el alcance indicado por el responsable… Cambiar entre Parcial y Completa no resuelve las coincidencias…» | **Cómo elegir el alcance** | Desplegable junto al campo existente. Conserva toda la advertencia sobre reutilización del archivo con otro alcance. |
| Aviso de carga: «El archivo no modifica inmediatamente…» | **El archivo se revisa antes de incorporarlo** | Desplegable al pie del formulario, antes de preparar la previsualización. Conserva validación y confirmación explícita. |
| Coordenadas: «Define cómo se miden las coordenadas. El archivo de ejemplo usa UTM zona 14N (EPSG:32614).» | Código EPSG actual y botón para cambiarlo | **Qué significa este sistema**. Evita que una explicación técnica compita con la configuración vigente. |
| Historial: «Consultando todas las cargas disponibles…» y progreso de cargas recibidas | «Cargando historial…» y progreso entre paréntesis | Sigue siendo un estado temporal anunciado. Mantiene la cantidad recibida mientras carga. |
| Historial: «X de Y cargas disponibles coinciden. Las fechas usan la hora local del navegador.» | «Historial actualizado» o «Filtros aplicados» | **Ver detalle del historial** conserva cantidades y explicación de fechas. La paginación conserva el rango de resultados visible. |
| Historial: «No se muestran resultados parciales como si fueran el historial completo.» | «Historial no disponible» / «Vuelve a consultar las importaciones.» | **Ver detalle del historial** conserva la aclaración técnica cuando falla la consulta. El error y la indicación de reintentar siguen visibles. |
| Cargas dadas de baja: párrafo sobre consulta, conservación y dependencias protegidas | **Acerca de las cargas dadas de baja** | Desplegable sobre el historial. Las tarjetas inactivas conservan fecha, motivo y estado de sólo lectura. |
| Tarjeta: «X elementos confirmados en esta carga. Consultar el detalle no activa ni reemplaza una versión del mapa.» | «X confirmados» | **Acerca de esta carga**, o **Con errores** si corresponde, conserva la frase completa. El total aparece una sola vez en la lectura inicial. |
| Tarjeta: «Hay errores de carga, geometría o datos: consulta el detalle.» | Chip rojo **Con errores** | Desplegable de la misma tarjeta. El resumen de válidos, advertencias y errores se conserva visible. |
| Tarjeta: «Sin errores informados. Las coincidencias administrativas se consultan en el detalle.» | **Acerca de esta carga** | Desplegable de la tarjeta. No se interpreta ausencia de errores como coincidencia confirmada. |
| Conciliación: «El mismo archivo con la misma configuración reutiliza su procesamiento…» | **Cómo se reconoce una carga** | Desplegable debajo del nombre del archivo. Conserva la diferencia entre reutilización y una nueva entrega. |
| Conciliación: párrafo de formato, total, capas, coordenadas, válidos, advertencias y errores | Resumen de conciliación; chips **Con errores** / **Con advertencias** cuando aplican | **Ver datos y validación del archivo** conserva todos los datos y conteos de validación. El total de elementos no se repite en otro párrafo visible. |
| Dos tarjetas de universos y explicaciones de disponibilidad histórica/ciclos | **Ver registros administrativos y ciclos** | Desplegable con las dos tarjetas intactas. Si existen advertencias, se indica visiblemente en amarillo; si hay diferencias demostradas, el título dice **Los registros cambiaron: ver comparación**. Mantiene la diferencia entre cero y dato no disponible. |
| Sin coincidencia: conteo repetido, proporción, diagnóstico, instrucciones, destinos y cinco ejemplos | **Hay elementos sin coincidencia** + «Revisa las asociaciones pendientes. No es un error de carga.» | **Qué revisar y ejemplos del archivo** conserva proporción, diagnóstico completo, campos que comparar, destinos disponibles, instrucción de nueva conciliación y ejemplos. Los botones quedan visibles. |
| Sin coincidencia generalizada: mismo aviso anterior con explicación estructural | **Sin coincidencia en casi todo el archivo** + «Revisa los registros del proyecto y el formato de los datos del archivo. No es un error de carga.» | El mismo desplegable conserva el diagnóstico específico y el porcentaje. El criterio sigue siendo **más de 85%**, no 85% inclusive. |
| Tabla de elementos: motivo extenso, transformaciones y advertencias concatenados | **Ver observaciones** y chip **Con advertencias** cuando corresponde | Desplegable por fila. **Los errores concretos se mantienen fuera del desplegable**, en rojo. Valores originales y resultados siguen visibles. |
| Confirmación conjunta: «Confirma juntas las coincidencias con un único destino. Antes de guardar verás cuáles quedan fuera y los riesgos.» | Título con restricción al administrador y botón existente | **Qué se confirma en conjunto** conserva el párrafo. Las condiciones para mostrar y habilitar el botón no cambian. |
| Modal de confirmación conjunta: lista extensa de cinco riesgos | Aviso visible sobre reemplazos, asociaciones incorrectas y ausencia de deshacer conjunto; instrucción de no cerrar la pantalla | **Ver todos los riesgos y advertencias** conserva los cinco puntos completos, incluidas reparaciones, interrupción, conexión, registros no creados y finalización separada. Cantidad a confirmar y polígonos sin coincidencia siguen visibles. No se cambia la confirmación. |
| Finalización: «La confirmación requiere revisión humana. La conciliación puede ser parcial…» o explicación de consulta histórica | **Antes de finalizar** | Desplegable con la explicación correspondiente al estado actual. La condición de sólo lectura permanece visible en el aviso de baja. |
| Cierre: «Falta resolver X elementos; Y tienen errores… Abre Revisar elemento… Seleccionar un candidato no basta…» | **Hay elementos por resolver** o **Hay errores por resolver** | **Ver detalle del cierre** conserva texto y conteos completos. Siguen visibles **Ver elementos por resolver**, **Ver errores por resolver** y **Actualizar estado**, cuando corresponden. |
| Cierre: «No quedan decisiones ni errores pendientes… Los elementos sin coincidencia no se incorporarán al mapa.» | **Listo para finalizar** | **Ver detalle del cierre** conserva la explicación y la exclusión del mapa. |
| Otros estados de cierre: baja, consulta no verificada, carga no pendiente o DDV | **Sólo lectura**, **No se pudo verificar el cierre**, **No disponible para finalizar**, **Hay errores por resolver** o **DDV listo para revisar** | **Ver detalle del cierre** conserva cada mensaje original. El botón mantiene exactamente las restricciones previas. |
| Mapa: «El mapa publicado muestra la versión vigente confirmada…» | **Cuándo se muestra en el mapa** | Desplegable conserva la diferencia entre previsualizar y publicar. |
| Mapa: «Las coincidencias pueden revisarse juntas… Las que aún no confirmaste…» | Botón **Ver coincidencias en el mapa** | **Acerca de la vista en el mapa** conserva la explicación de previsualización. |
| Modal sin coincidencia: dos párrafos sobre asociación y pasos para incorporar al mapa | Chip **Sin coincidencia · No es un error de carga** | **Cómo resolver las coincidencias** conserva ambos párrafos. |
| Modal: etiqueta de búsqueda con ocho categorías | **Buscar en el listado** | **Qué puedes buscar** mantiene nombre, parcela, municipio, entidad, folio, motivo, código y evidencia. La búsqueda no cambia. |
| Modal: mensaje largo de diagnóstico por elemento, ciclo y evidencia | Motivo breve basado en el código, por ejemplo **El municipio no coincide** | **Ver diagnóstico y evidencia registrados** conserva mensaje completo del servidor, ciclo, códigos, campos y evidencia. Un código desconocido muestra **Diagnóstico disponible**, con su mensaje completo dentro. |
| Elementos sin diagnóstico: orientación local extensa o ausencia histórica | **Ver orientación para este elemento** o **Diagnóstico histórico no disponible** | Desplegable conserva orientación y ciclo; no inventa un diagnóstico del backend. |
| Modal: contador de página repite el total de elementos de la carga | «1–25 de N resultados» | El total de la carga permanece en el encabezado; se retira sólo la repetición del mismo dato del contador. |

Los errores operativos, el conflicto por geometría cambiada y los avisos de confirmación que requieren actuar inmediatamente conservan su mensaje completo. El aviso de un archivo posiblemente cargado con el tipo equivocado permanece visible. No se ocultaron controles ni requisitos de aceptación.

## Comparación visual por sección

Capturas del mismo escenario simulado, navegador Edge de escritorio a 1440 × 1000. Las imágenes de secciones pueden ser más altas que la ventana porque abarcan el bloque completo. No representan datos reales del proyecto.

| Sección | Antes | Después | Diferencia visible |
| --- | --- | --- | --- |
| Carga | [Antes](qa-ux-gis-carga-antes-2026-10-14.png) | [Después](qa-ux-gis-carga-despues-2026-10-14.png) | Requisitos, alcance y explicación de incorporación quedan desplegables; los mismos campos y botón permanecen disponibles. |
| Historial | [Antes](qa-ux-gis-historial-antes-2026-10-14.png) | [Después](qa-ux-gis-historial-despues-2026-10-14.png) | Menos párrafos antes de las tarjetas y menos aclaraciones repetidas dentro de cada carga. |
| Conciliación | [Antes](qa-ux-gis-conciliacion-antes-2026-10-14.png) | [Después](qa-ux-gis-conciliacion-despues-2026-10-14.png) | Resumen y acciones primero; datos técnicos, universos y ejemplos se abren a petición. La tabla conserva valores originales. |
| Modal sin coincidencia | [Antes](qa-ux-gis-modal-antes-2026-10-14.png) | [Después](qa-ux-gis-modal-despues-2026-10-14.png) | Aviso corto, búsqueda con nombre sencillo y causas breves; evidencia completa dentro de cada fila. |

[Móvil: modal a 390 × 844](qa-ux-gis-modal-movil-despues-2026-10-14.png).

Se añadieron espacio entre bloques, foco visible en los desplegables y ancho mínimo para que las etiquetas y los botones de la tabla no se partan en fragmentos. La tabla puede desplazarse horizontalmente dentro de su región sin ensanchar toda la página.

## Verificación realizada

Pruebas en Edge sin interfaz visible, con archivos del directorio de trabajo y API interceptada. No se usaron credenciales ni se importaron o confirmaron datos reales. Las pruebas existentes se adaptaron para distinguir texto visible de contenido conservado dentro de un desplegable; las comprobaciones de permisos, bloqueos y solicitudes permanecen.

- `node frontend-ssalfer/deploy/qa-conciliacion-orientacion.cjs`: aprobada. Filtros sobre 205 cargas, fechas inválidas, recuperación tras error, umbral 85%/86%, originales con ceros iniciales, 997 parcelas en búsqueda/CSV, error posterior a la primera página, cierre bloqueado, error ignorado, checkbox obligatorio, rechazo por geometría cambiada aun con checkbox, confirmación conjunta sólo para administrador, cancelación sin envíos, interrupción del lote, limpieza de contexto y consultas retrasadas.
- `node frontend-ssalfer/deploy/qa-gis-contratos-029.cjs`: aprobada. Diagnósticos registrados/históricos/desconocidos, ausencia frente a cero, evidencia, CSV, contenido escapado, ciclo propio, consulta histórica, motivos de baja, CSRF y respuestas 403/404/409/422.
- `node frontend-ssalfer/deploy/qa-ux-gestion-geoespacial-2026-10-14.cjs`: aprobada. Desplegables cerrados inicialmente, apertura con Enter, cierre con espacio, foco visible, expansión del diagnóstico completo, búsqueda por código oculto, Escape con retorno de foco y modal móvil.
- Capturas anteriores: la misma prueba UX con `QA_UX_FASE=antes` sirve los cinco archivos respaldados al inicio de esta ronda desde `.qa-backups/ux-divulgacion-2026-10-14`, siempre con API simulada. No restaura ni sobrescribe los archivos de trabajo.
- Comprobación de sintaxis de ambos JavaScript y `git diff --check`: sin errores.

Se revisaron las capturas de escritorio y móvil. Las pruebas demuestran el comportamiento del frontend con respuestas controladas; no son una certificación del procesamiento real de los GPKG en el backend.

## Barrido manual sugerido

1. Entra a Gestión geoespacial y selecciona un proyecto. Abre una nueva carga y prueba DDV, Núcleos y Parcelas. Debes ver una frase breve; abre **Ver requisitos del archivo** y comprueba que la explicación corresponda al tipo actual.
2. Abre **Cómo elegir el alcance**. Comprueba que Parcial y Completa siguen teniendo la misma advertencia y que no se puede enviar sin elegir el alcance cuando es obligatorio.
3. En el historial, prueba estado, tipo y fechas. La paginación debe mostrar los resultados; **Ver detalle del historial** debe mostrar la cantidad filtrada frente al total y cómo se interpretan las fechas.
4. Consulta una carga. Revisa los números del resumen y abre sus datos de validación, registros administrativos y ejemplos. Comprueba que no se confunda una falta de coincidencia azul con un error rojo.
5. En **Ver elementos sin coincidencia**, compara los valores del archivo, abre el diagnóstico de una fila y busca una palabra de su explicación o código aunque el desplegable esté cerrado. Exporta el listado filtrado y comprueba que conserve el detalle.
6. Prueba una carga con pendientes: el cierre debe estar deshabilitado y ofrecer los botones para revisarlos. Abre **Ver detalle del cierre** para consultar la explicación completa. Comprueba también el estado listo para finalizar y el caso de una carga histórica.
7. Como administrador, abre la confirmación conjunta sin confirmar datos reales. Deben verse cantidad, riesgos principales y elementos sin coincidencia. Abre **Ver todos los riesgos y advertencias** y cancela. Como geógrafo, el botón conjunto no debe aparecer.
8. Recorre los desplegables con Tab, Enter y espacio. Abre y cierra el modal con Escape; el foco debe regresar al botón que lo abrió. Repite en pantalla estrecha y desplaza la tabla dentro de su región.

## Conservación y pendientes

No desaparecieron errores, advertencias ni bloqueos reales: se conserva su contenido completo y las condiciones que los producen. Los errores de las filas permanecen visibles; las advertencias tienen señal visible y detalle disponible. Se preservan los diagnósticos originales, la búsqueda y el CSV completos. Los conteos repetidos se concentran en el resumen, la paginación o el detalle, según corresponda.

Esta mejora no requiere cambios de backend. No se añadieron endpoints ni mecanismos para omitir validaciones. Las incidencias de backend documentadas en rondas anteriores siguen fuera del alcance de esta mejora de presentación.
