# Baja de cargas, revisiones y ficha del proyecto

Fecha: 15 de octubre de 2026. Cambios locales; sin commit ni push.

## Qué cambió

- **Baja de importaciones:** antes se rechazaban cargas con confirmaciones o dependencias; ahora administrador y geógrafo con acceso GIS al proyecto pueden darlas de baja. El diálogo exige motivo y confirmación y advierte del retiro del mapa. Se conserva archivo, historial y registros administrativos. No se restauran versiones anteriores. Una carga aún en procesamiento debe terminar primero.
- **Mapa:** se retiran únicamente las geometrías de esa carga. Dar de baja una entrega antigua no retira las geometrías de una entrega posterior. Se evita que reaparezcan polígonos globales antiguos como sustitutos de una geometría retirada del proyecto.
- **Paginación:** Anterior/Siguiente lleva al principio de la tabla o del historial, con foco de teclado, en lugar de dejar al usuario al final.
- **Revisiones:** los filtros conservan su posición y foco. Se muestra «Aplicando filtros…», después el número de resultados y los filtros utilizados. Si no hay resultados, se explica cómo volver a los pendientes. Las respuestas atrasadas no sustituyen una selección posterior. Se conserva la consulta al backend y el detalle de revisión.
- **Ficha del proyecto:** dos pestañas, «Resumen del proyecto» y «Núcleos vinculados». Administración y usuarios responsables permanecen fuera de estas pestañas, respetando sus permisos. Las tarjetas de núcleos son compactas, con cuatro columnas en escritorio, dos en pantallas intermedias y una en móvil. La altura se adapta al texto para evitar recortes.
- **Buscador:** encuentra núcleos por nombre, municipio o entidad, sin distinguir acentos o mayúsculas. Consulta todas las páginas de núcleos; filtrar las tarjetas no cambia los indicadores generales.

No se cambiaron endpoints ni la estructura de la base de datos. El cambio de backend fue autorizado expresamente. Trazo del proyecto continúa oculto en la nueva importación.

## Pruebas realizadas

1. **42 pruebas de backend aprobadas** en una base temporal aislada con las migraciones existentes, sin utilizar los proyectos reales. Incluyen DDV, núcleos, parcelas y trazos históricos; preservación del historial; permisos; motivo; reintento; concurrencia; rollback; retirada de una versión antigua; nueva carga después de la baja; y no afectar otro proyecto que comparte un núcleo. Registro: `../../outputs/qa-bajas-2026-10-15.log` (ruta desde la raíz del frontend).
2. **Ficha en Edge, API simulada:** 205 núcleos, búsqueda de un registro en la segunda página, navegación de pestañas por teclado, indicadores constantes y columnas adaptables. Script: `qa-ficha-proyecto-2026-10-15.cjs`.
3. **Revisiones en Edge, API simulada:** filtros enviados correctamente, indicador de carga, lista vacía, restablecer pendientes, conservación del foco y descarte de respuestas atrasadas. Script: `qa-revisiones-2026-10-15.cjs`.
4. **Regresión de conciliación:** `qa-gis-contratos-029.cjs` y `qa-ux-gestion-geoespacial-2026-10-14.cjs` aprobados: diagnósticos, históricos, errores de API, roles, confirmación de baja, CSRF, móvil y detalle expandible. Sin errores JavaScript ni llamadas a la API real.
5. `git diff --check` sin errores de espacios. El servidor local utiliza recarga automática del código.

No se dieron de baja las cargas de demostración ni se modificaron registros reales. Las capturas de esta ronda usan datos simulados; no prueban un cambio en producción. Evidencias en `outputs/qa-ficha-proyecto-2026-10-15.png`, `outputs/qa-ficha-proyecto-movil-2026-10-15.png` y `outputs/qa-revisiones-2026-10-15.png`, desde la raíz del repositorio.

## Cómo comprobarlo manualmente

### Gestión geoespacial

Entra con administrador o geógrafo a un proyecto de pruebas. En el historial debe aparecer «Dar de baja esta importación» también en una carga confirmada. Usa una carga nueva de prueba, para conservar la demostración ya preparada.

1. Abre la baja y lee la advertencia. Cancela: el archivo y el mapa deben permanecer iguales.
2. Vuelve a abrirla. Sin motivo o sin marcar la confirmación no debe completarse.
3. Completa los datos y acepta. La carga deja de aparecer en la vista de activas. En «Activas y dadas de baja» permanece su historial y motivo.
4. Actualiza el mapa: ya no deben aparecer los polígonos vigentes de esa carga. Los registros administrativos siguen disponibles. Una baja de DDV no elimina las parcelas o núcleos de otras cargas.
5. Si das de baja una carga antigua ya reemplazada, la versión posterior debe seguir visible. Si das de baja la actual, la anterior no se activa automáticamente.
6. Sube y confirma una nueva entrega de prueba: vuelve a aparecer en el mapa. También puede cargarse otra vez el archivo dado de baja como una nueva importación.
7. Con un rol sin permiso GIS, la acción no debe estar disponible y una petición directa tampoco debe autorizarse.
8. En una tabla con más de una página, usa Siguiente y Anterior. Debes llegar al inicio de sus resultados.

### Revisiones geoespaciales

Selecciona Estado, Capa y Tipo de cambio. Mientras consulta aparece el aviso de carga; al terminar cambian el conteo y las filas. Una combinación sin cambios debe mostrar una lista vacía explícita. «Ver todos los pendientes» restablece Estado a Pendiente y elimina los otros filtros. Si cambias rápidamente de opción, el resultado final debe corresponder a la última selección.

Las revisiones describen cambios entre entregas; no son un botón para publicar ni recuperar archivos. El pendiente ya documentado sobre revisiones históricas sin nombre de destino continúa separado de esta mejora.

### Ficha del proyecto

Al abrir el proyecto se muestra Resumen del proyecto. Selecciona Núcleos vinculados para ver tarjetas y buscador. Busca por nombre o municipio; prueba un nombre con y sin acento. Limpia la búsqueda para recuperar todos. Vuelve al resumen: los totales deben permanecer iguales. Comprueba administración y usuarios responsables en ambas vistas, según tus permisos. En móvil las tarjetas se acomodan en una sola columna y los nombres largos no se recortan.
