# Dashboard y Excel completos — 22 de octubre de 2026

Adaptación frontend local sobre `5ccef495ca0ca70a3ca7d432121313a0536f152a`, en `C:\Proyectos\Software-PA-qa-f01-f06`. PR #2 abierto y Draft. No se hizo commit, push, merge ni despliegue. La rama de desarrollo `feature/integracion-mq-deploy` permanece en `75598ba`, sin modificaciones de archivos versionados. El servicio habitual en 5184 y la referencia en 15175 no recibieron estos cambios.

## Qué cambió

- `frontend-ssalfer/js/api/nucleos.js`: consumo del resumen global y las dos exportaciones por cursor. Conserva el listado administrativo anterior para otras pantallas. Valida cantidades, revisiones independientes, IDs estrictamente crecientes, límites, cursor y fin de la descarga. Comprueba nuevamente las revisiones y contrasta los cinco totales contra las filas descargadas y el resumen mostrado.
- `frontend-ssalfer/js/dashboard.js`: una consulta de resumen por proyecto, sin descargar núcleos ni convenios al abrir. Usa `total_nucleos` y las cifras COP completas. Un fallo de resumen muestra «Reintentar resumen»; no lo convierte en un proyecto vacío. El Excel queda deshabilitado si falta un proyecto o falló la consulta de KPI/valores.
- `frontend-ssalfer/js/utils/dashboardExcel.js`: descarga explícita en páginas de 200, hasta dos recursos concurrentes de un mismo proyecto. Comprueba integridad antes de construir el libro y nuevamente después de preparar sus hojas/gráficos, antes de descargarlo. No reutiliza lotes entre exportaciones, cuentas o proyectos. Conserva las hojas, valores históricos, orden de convenios por ID y «Tipo no informado».
- Exportación con botón ocupado y aviso accesible, sin impedir navegar. AbortController cancela al salir, cambiar de pantalla, recibir una sesión inválida o el aviso de cierre desde otra pestaña. Verifica la cuenta frente a la sesión del documento al inicio y de nuevo al terminar. Ante error no descarga un archivo parcial. Reintentar inicia una nueva exportación completa.
- Pruebas frontend: se actualizó `dashboard-performance.cjs` para el contrato nuevo y se añadió `dashboard-completo.cjs`. La comparación heredada con datos pequeños se conserva; no se usa el recorte histórico como evidencia de integridad de proyectos grandes.

No se modificaron código backend, endpoints, contratos ni esquema. Se utilizaron los endpoints publicados por el otro equipo; únicamente se reinició el backend candidato para cargarlos. No se volvió a aplicar la migración 030.

## Pruebas realizadas

- **85 pruebas JavaScript aprobadas con LF y las mismas 85 con CRLF**, sin fallos ni omisiones. Incluyen 30 casos nuevos de integridad/paginación. No son 170 pruebas distintas.
- Edge/Chromium en Windows, backend real y base aislada: proyectos sintéticos de **0, 99, 100, 101, 200, 201 y 1000 núcleos**, con un convenio por núcleo, tipos nulos, nombres repetidos válidos y varias afectaciones para el primer convenio. Se confirmó la deduplicación: ese convenio ocupa una sola fila.
- Excel descargado desde la página y reabierto: cantidades de filas y cifras del resumen correctas en los siete tamaños. Los cuatro roles exportaron el proyecto de 1000 núcleos; el operador estaba asignado. El operador no asignado recibió 403 en las tres rutas nuevas.
- Navegador: cortes de red, HTTP 500/403/409/401 en página intermedia; cero archivos parciales. Tras el corte de red, un nuevo intento completó el archivo. Navegación a la ficha del proyecto, cierre notificado desde otra pestaña y cambio de cuenta antes de exportar también impidieron la descarga antigua.
- **409 real del backend**: durante la descarga se modificó el nombre de un núcleo exclusivamente sintético, sin cambiar la cantidad. La revisión cambió, el servidor rechazó la continuación y la página mostró el aviso de actualización. Se restauró el nombre original al terminar.
- Prueba final **sin interceptar respuestas**: los diez proyectos disponibles en la copia aislada exportaron **1786 núcleos y 1771 convenios** en total; se contrastó cada hoja y resumen contra la API. Sin excepciones JavaScript en la página.
- Carga inicial de ese último recorrido: **14 peticiones API**, incluidas sesión, listado de proyectos, KPI, valores declarados y diez resúmenes. Cero solicitudes de detalle exportable al abrir. Los archivos estáticos `/js/api/*` se excluyen de este conteo. No se hicieron mediciones SQL ni un nuevo benchmark estadístico; no se extrapolan tiempos a producción.

La revisión final adicional después de construir el libro agrega dos comprobaciones de revisión y un resumen por proyecto. Es deliberada para detectar cambios durante la generación de gráficos/hojas. La descarga de detalle crece por páginas, no por núcleo o afectación.

## Cómo revisar en pantalla

Abrir `http://127.0.0.1:15174/Index.html` con las cuentas sintéticas del candidato. Usar un perfil de navegador separado del habitual para evitar compartir cookies entre puertos. Los accesos existentes se conservan en el archivo privado `ACCESOS-QA.txt` del entorno de pruebas; no se incluyen contraseñas en este informe.

**Ruta: Inicio de sesión → Dashboard → Todos los proyectos.** Encontrar las tarjetas «QA frontend COP …». Los proyectos existentes de la copia también pueden aparecer.

| Tarjeta | Núcleos | Individuales | Colectivos | Formalizados |
| --- | ---: | ---: | ---: | ---: |
| QA frontend COP 0 | 0 | 0 | 0 | 0 |
| QA frontend COP 99 | 99 | 49 | 50 | 50 |
| QA frontend COP 100 | 100 | 50 | 50 | 50 |
| QA frontend COP 101 | 101 | 50 | 51 | 51 |
| QA frontend COP 200 | 200 | 100 | 100 | 100 |
| QA frontend COP 201 | 201 | 100 | 101 | 101 |
| QA frontend COP 1000 | 1000 | 500 | 500 | 500 |

Estos conteos corresponden al conjunto sintético; no son cifras del proyecto México-Querétaro. Las asambleas/montos históricos mantienen su propia fuente y no se convierten en los totales COP.

**Ruta: Dashboard → Exportar dashboard (Excel).** Se muestra «Preparando Excel…» y el proyecto que se está consultando. El botón evita descargas duplicadas. Al terminar se descarga `SSALFER-dashboard.xlsx` con Resumen, Gráficos y una hoja por proyecto autorizado. En la hoja del proyecto de 1000, verificar 1000 filas bajo «Núcleo» y 1000 bajo «Convenio», sin contar sus encabezados. En Resumen deben repetirse las cifras de la tabla anterior. CSV de respaldo conserva su comportamiento anterior; la adaptación corresponde al botón Excel.

**Ruta: Dashboard → Exportar dashboard (Excel) → abrir una tarjeta de proyecto durante la preparación.** Debe abrirse la ficha y cancelarse la descarga anterior. Para repetir con facilidad puede usarse conexión lenta desde las herramientas del navegador, solo en el candidato.

Si se interrumpe la conexión, no debe aparecer un archivo incompleto y el botón debe permitir volver a intentar. Si cambian los datos, el aviso pide actualizar el dashboard; después de actualizar se puede iniciar otra exportación. Si caduca la sesión se conserva el flujo de inicio de sesión existente. No se deben modificar registros reales para provocar estos casos.

## Evidencia local y límites

Carpeta: `C:\Proyectos\Software-PA-integracion-mq\outputs\cop-frontend-2026-10-22`.

- `javascript-LF.log`, `javascript-CRLF.log`: 85/85.
- `resultados-navegador.json`: trece escenarios de navegador, incluidos los cuatro roles, siete tamaños y cancelaciones.
- `smoke-completo.json`: recorrido final sin interceptar respuestas, conteos por proyecto y peticiones API iniciales.
- `dashboard-completo.xlsx`: siete proyectos sintéticos; `dashboard-rol-2/3/5.xlsx` y `dashboard-reintento.xlsx` comprueban roles y recuperación.
- `dashboard-todos-los-proyectos.xlsx`: exportación final de la copia. Contiene datos de la copia local; no publicar ni adjuntar a GitHub sin revisar su contenido.
- `dashboard-totales.png` y `exportacion-cambio-409.png`: capturas revisadas de resultados y aviso.
- `datos-sinteticos.json`: proyectos de prueba 7–13. Permanecen disponibles para revisión manual. Se preparó un respaldo privado antes de insertarlos, sin tocar la base original.

Los errores de red/500/403/401 y un caso de 409 se provocaron interceptando únicamente la respuesta de prueba en el navegador. Otro caso de 409 se verificó realmente con una edición reversible del núcleo sintético. En la prueba de siete tamaños se filtró solo el listado de proyectos para facilitar la comprobación; las consultas de resumen/exportación fueron reales. El recorrido final de los diez proyectos no interceptó ninguna respuesta.

No se promete congelar la base después de la última comprobación: se conserva el control optimista del contrato. No se certifican todos los módulos ni rendimiento productivo; los pendientes backend históricos de INEGI/RAN/linaje no fueron alterados ni repetidos en esta ronda. La validación manual del usuario y la publicación autorizada de estos cambios locales siguen pendientes; PR #2 permanece Draft.
