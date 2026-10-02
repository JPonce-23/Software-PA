# Pendientes para capacitación — ronda 3

Inspección: 02-10-2026. El nombre con `2026-10-03` identifica la ronda pedida. Sólo lectura de código y QA local; no se modificó backend. Como el backend continúa cambiando, los hallazgos históricos deben revalidarse contra la versión que se entregue para capacitación.

No hubo respuestas HTTP 5xx en el recorrido de 30 pantallas autenticadas y login. No se detectó un nuevo bloqueo de backend que impida implementar el tren o el desplazamiento. Esto no certifica operaciones de escritura ni todos los contratos del sistema.

Derechos colectivos se excluyó por instrucción posterior del usuario. Su tarjeta no se cambió; no se afirma aquí que carezca de backend ni se propone su eliminación.

## Funciones limitadas y decisiones pendientes

| Pantalla / función | Texto o evidencia que llega al usuario | Causa / certeza | Recomendación para capacitación |
| --- | --- | --- | --- |
| Personas, ORV; nueva titularidad y beneficiarios | Personas explica que consulta por ID y que falta búsqueda por nombre/CURP; ORV solicita un identificador y avisa que buscar por nombre no está disponible | Limitación de contrato documentada en ronda 1 (`js/api/personas.js`, `js/orv.js`, `pages/persona.html`). No se inventó un listado | Explicar la consulta por ID y usar registros QA conocidos. Solicitar consulta paginada por proyecto y revalidar OpenAPI antes de integrar |
| Catálogos: edición de observaciones | «Las observaciones de una opción existente están disponibles solo para consulta» | Campo readonly en `js/catalogosOperativos.js`; ronda 1 confirmó exclusión del campo en `update_catalog_option` | Conservar explicación. Definir/persistir edición en backend y probar con fixture; no habilitar un campo que pudiera aparentar guardado |
| Catálogos: reactivación | «El backend actual permite desactivar opciones, pero no expone una operación efectiva de reactivación»; modal de baja: «La API actual no ofrece una reactivación efectiva» | Limitación ya documentada; `pages/catalogosOperativos.html` | Explicar que la baja no ofrece una recuperación por esta interfaz. Definir el ciclo de reactivación y reemplazar jerga técnica por una explicación funcional en una tarea posterior |
| Asignaciones usuario–proyecto | No hay ciclo completo de revocar, modificar o reactivar asignaciones | Ronda 1: GET/POST de asignaciones activas, sin ciclo completo. No es el mismo concepto que responsable funcional | Definir autorización, auditoría, duplicados y reactivación; mantener fuera de la demostración de gestión completa |
| Ficha RAN: datos generales | Botones Editar trámite/Editar datos ocultos en `js/fichaRan.js` | El frontend declara no tener operación para modificar TramiteRan directamente; los eventos sí son editables | Explicar la diferencia entre trámite y evento. Revalidar contrato vigente antes de ofrecer edición general |
| Ficha Convenio: convenios derivados | `conveniosDerivadosSeccion` oculta en `js/fichaConvenio.js`; el convenio padre sí se consulta | El frontend declara no disponer de listado específico de hijos | No prometer exploración completa de derivados. Acordar contrato o consulta adecuada sin inferir relaciones |
| Indemnización: valor financiero | «Esta fórmula aún no constituye una definición oficial del indicador» | Decisión funcional pendiente; se usa el máximo de montos declarados asociados, no una nueva regla contable | Explicar su carácter orientativo y aprobar fórmula antes de capacitar como indicador oficial |
| FIFONAFE: conflictos 409 | Mensaje genérico del servidor puede agrupar ordinal duplicado y otras restricciones | Ronda 2 confirmó el mensaje común de persistencia por código, sin provocar conflictos nuevos | Pedir códigos de error estables por causa; mantener validación local de ordinal/evidencia, que no sustituye concurrencia en servidor |
| Crear afectación: conflictos 409 | Mensaje genérico de ámbito/parcela puede ocultar causas distintas | Evidencia y restricción de revisión detalladas en ronda 2; no se reprodujo nueva creación en esta ronda | Si reaparece, obtener la restricción real desde logs; no quitar validaciones de ámbito ni asumir éxito de persistencia |
| Seguimiento: ciclo completo | Alta, edición y baja reales todavía no verificadas de extremo a extremo en esta ronda | Pendiente de QA con escrituras, no bug de backend confirmado | Ejecutar ciclo autorizado sobre fixtures aislados y comprobar lectura posterior, auditoría y relaciones |
| Menú móvil | Menú fijo ocupa una parte grande de la ventana en 390×844 | Diseño frontend anterior; el nuevo scroll ya deja el título debajo del menú | Validar manualmente la comodidad de uso. Un rediseño del menú sería una tarea distinta |

**Corrección histórica importante:** Observaciones de eventos FIFONAFE sí tiene soporte según código, respuesta real y BD revisados en ronda 2. No confundirlo con Observaciones de catálogos ni volver a deshabilitarlo. Las fechas del evento QA revisado tampoco estaban intercambiadas por el editor. Ver `BLOQUEOS-BACKEND-2026-10-02-RONDA2.md`.

Otras decisiones conservadas: definición de COP formalizados colectivos, modificatorio sin padre permitido, responsables, cargos ORV, límite de resultado de Asamblea y cambio de asamblea asociada a convenio. No se cambiaron estas reglas para completar la interfaz.

## Enlaces `#` después de cargar la página

La búsqueda estática contiene numerosos enlaces que JavaScript transforma correctamente. Se comprobó el DOM cargado; el inventario íntegro está en `inventario-controles-ronda3.json`.

| Pantalla | Enlace | Diagnóstico | Recomendación |
| --- | --- | --- | --- |
| Dashboard | Todos los proyectos | Conserva `href="#"`; funciona como enlace a la parte superior, no como destino explícito del dashboard | Usar un destino o ancla de sección real en una corrección posterior |
| FIFONAFE (listado) | Núcleo agrario (`enlaceNucleo`) | Conserva `href="#"`; `js/fifonafe.js` no configura este enlace. El botón Volver sí funciona | Corregir el enlace al núcleo usando el contexto existente; pendiente frontend, no backend |
| Nuevo trámite RAN | Asamblea / origen (`enlaceAsamblea`) | Conserva `#`, pero tiene handler `preventDefault()` y llama `volver()`; no es enlace sin acción | Cambiar a URL explícita por semántica y apertura en otra pestaña; no bloquea el retorno actual |
| Afectaciones | Ver mapa | El inventario lo encuentra visible con `#`; geografía está excluida | Revisarlo con la tarea de geografía, sin modificarlo en esta ronda |

Se conservaron estos enlaces porque el paso de auditoría pide reportar el resto sin alterar funciones adicionales. Las opciones de cuenta, enlaces internos del núcleo y las exportaciones se resuelven por JavaScript; no se clasificaron como rotos sólo por el HTML inicial.

## Controles deshabilitados, vacíos y textos técnicos

- Paginadores en primera/única página (Usuarios, Auditoría, reportes) y selectores que esperan proyecto/núcleo no son módulos ausentes. El inventario registra sus IDs y el estado inicial, no una indisponibilidad permanente.
- Convenio padre se habilita según el tipo de convenio. Ordinal y relación/persona inmutables al editar se conservan por contrato. No se cambiaron esas restricciones.
- Documentos, intervinientes FIFONAFE, titulares de unidad y listados sin filas muestran estados vacíos. Las respuestas vacías QA son válidas; no se agregaron datos para ocultarlas.
- «Referencia no disponible», «Documento asociado no disponible en el listado», «Nombre no disponible» y avisos de referencias parciales en Seguimiento, Expediente, Convenios, Auditoría y reportes son fallbacks ante referencias ausentes o consultas fallidas. Conservar el ID interno para no perder la relación y revisar el registro/ruta cuando se reproduzca. No son evidencia suficiente para afirmar que falta todo un módulo.
- «No hay un selector disponible para esta relación» en Seguimiento es un fallback para tipos no soportados. En la ronda 1 se implementaron los tipos actuales; las pruebas verificaron los nueve directos y las dependencias conocidas. Nuevos tipos de backend exigirán verificar su integración.
- Usuarios informa «El backend normaliza el correo a minúsculas»; reportes de convenios y avance mencionan alcance/filtros validados por backend y datos recibidos. Son textos técnicos visibles, no funcionalidades incompletas. Recomendación editorial posterior: hablar de «sistema» y explicar el efecto para la persona usuaria.
- Los textos técnicos de Afectación/Expediente que aparecían en la búsqueda de archivos están en comentarios HTML; no se presentaron como avisos visibles. «Si la actividad aún no se realiza…» es una instrucción válida de captura, no un pendiente.
- Las hojas de iconos externas ya existían. El tren nuevo funciona sin ellas; disponibilidad de esos iconos en una red cerrada sigue siendo una comprobación de entorno para capacitación.

No se retiraron controles ni se cambiaron reglas como resultado de esta auditoría. Priorizar la búsqueda de personas, catálogos, asignaciones y pruebas con persistencia; revalidar estos pendientes al incorporar los cambios del equipo de backend.
