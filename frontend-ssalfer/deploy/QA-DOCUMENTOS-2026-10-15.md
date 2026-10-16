# Documentos: accesos, fecha de carga y baja

15 de octubre de 2026. Cambios exclusivamente de frontend. Sin commit ni push. Los cambios de backend de la ronda geoespacial anterior permanecen intactos; esta ronda no los modifica.

## Resultado

Se reutilizó el evento `ssalfer:contexto-documentos`. Los contratos actuales de Convenio y Trámite RAN ya incluyen `id_proyecto_nucleo`; no hace falta recorrer nuevamente sus relaciones ni añadir consultas. Indemnización y Detalle de afectación utilizan el núcleo de la afectación consultada.

El listado del gestor distingue **Fecha del documento** de **Última carga**. Esta última proviene de `fecha_carga` de la versión con mayor `numero_version`. Sin versiones muestra **Sin archivo**. Si falla consultar las versiones, informa **Fecha no disponible** y permite consultarlas de nuevo; no confunde un fallo con ausencia de archivo. Las consultas tienen concurrencia limitada a cuatro. Al subir una versión se refresca el listado.

**Dar de baja** sólo aparece para administrador y operador. Pide motivo de al menos tres caracteres y confirmación. Advierte que la baja auditada afecta al documento en todos sus vínculos, conserva el archivo físico y el historial. Utiliza el DELETE y el cliente `DocumentosAPI.eliminar` ya existentes. El cliente API no necesitó modificación. Cancelar no envía ninguna escritura; un error del servidor mantiene abierto el formulario y el motivo.

El selector de archivo admite `.pdf,.docx,.xlsx,.jpg,.jpeg,.png` y explica el límite de 20 MB. La validación definitiva sigue a cargo del backend existente. No se alteraron los tipos de registro, el vínculo de documentos existentes ni la procedencia. Se amplió únicamente el modal del gestor documental para acomodar ambas fechas y las acciones.

## Pantallas probadas

Las pruebas abrieron las páginas con datos simulados, comprobaron el acceso y, en las 15 pantallas con gestor, abrieron el modal y verificaron documentos del núcleo 150. En Núcleo agrario se comprobó el enlace existente hacia Documentos. No son una auditoría funcional completa de los demás formularios de esas páginas.

| Pantalla | Resultado | Cambio | Captura |
|---|---|---|---|
| Núcleo agrario | Acceso OK | Acceso existente a documentos.html conservado | [Ver](../../outputs/qa-documentos-nucleoAgrario-2026-10-15.png) |
| ORV | Acceso OK | Se añadió la carga faltante del gestor | [Ver](../../outputs/qa-documentos-orv-2026-10-15.png) |
| Padrones | Acceso OK | Acceso existente conservado | [Ver](../../outputs/qa-documentos-padrones-2026-10-15.png) |
| Personas | Acceso OK | Se añadió la carga faltante del gestor | [Ver](../../outputs/qa-documentos-persona-2026-10-15.png) |
| Actividades | Acceso OK | Acceso existente conservado | [Ver](../../outputs/qa-documentos-actividades-2026-10-15.png) |
| Asamblea | Acceso OK | Se añadieron gestor y dependencias | [Ver](../../outputs/qa-documentos-asamblea-2026-10-15.png) |
| Parcela | Acceso OK | Se añadió la carga faltante del gestor | [Ver](../../outputs/qa-documentos-parcela-2026-10-15.png) |
| Unidad agraria | Acceso OK | Se añadió la carga faltante del gestor | [Ver](../../outputs/qa-documentos-unidadAgraria-2026-10-15.png) |
| Seguimiento | Acceso OK | Acceso existente conservado | [Ver](../../outputs/qa-documentos-seguimiento-2026-10-15.png) |
| Ficha FIFONAFE | Acceso OK | Acceso existente conservado | [Ver](../../outputs/qa-documentos-fichaFifonafe-2026-10-15.png) |
| Listado FIFONAFE | Acceso OK | Se añadieron gestor y dependencias | [Ver](../../outputs/qa-documentos-fifonafe-2026-10-15.png) |
| Convenio | Acceso OK | Antes sin botón: evento con núcleo del convenio y carga del gestor | [Ver](../../outputs/qa-documentos-fichaConvenio-2026-10-15.png) |
| Afectación | Acceso OK | Antes sin botón: contenedor y dependencias del gestor | [Ver](../../outputs/qa-documentos-afectacion-2026-10-15.png) |
| Detalle de afectación | Acceso OK | Antes sin botón: contenedor, evento y carga del gestor | [Ver](../../outputs/qa-documentos-detalleAfectacion-2026-10-15.png) |
| Trámite RAN | Acceso OK | Antes sin botón: evento con núcleo del trámite | [Ver](../../outputs/qa-documentos-fichaRan-2026-10-15.png) |
| Indemnización | Acceso OK | Antes sin botón: evento con núcleo de la afectación y carga del gestor | [Ver](../../outputs/qa-documentos-indemnizacion-2026-10-15.png) |

## Evidencias del gestor

- [Tabla con ambas fechas, Sin archivo y Dar de baja](../../outputs/qa-documentos-tabla-2026-10-15.png).
- [Advertencia, motivo y confirmación de baja](../../outputs/qa-documentos-baja-2026-10-15.png).
- [Resultados de las pruebas](../../outputs/qa-documentos-2026-10-15.json).
- Script reproducible: `qa-documentos-2026-10-15.cjs`, ejecutado con Node y Playwright/Edge.

## Verificaciones aprobadas

- Los 16 accesos anteriores y el núcleo correcto, también sin `id_proyecto_nucleo` en las cuatro fichas que resuelven su contexto.
- Fecha declarada distinta de fecha de última versión; documento sin archivos; respuesta fallida de versiones diferenciada.
- Extensiones de `accept` y ayuda del límite de 20 MB.
- Cancelación y campos obligatorios sin emitir DELETE.
- Error 409 visible y reintento que conserva el motivo.
- DELETE con motivo y actualización del listado tras éxito.
- Baja disponible para administrador/operador, ausente para geógrafo/visualizador.
- Revisión visual de la tabla y del diálogo de baja, y `git diff --check` sin errores de espacios.

Toda la API estuvo interceptada. No se borraron ni modificaron documentos reales. Estas pruebas validan la integración frontend con los contratos existentes; no certifican una baja real en el servidor.

## Prueba manual sugerida

1. Abre cualquiera de las fichas y selecciona Documentos. Confirma que corresponde al núcleo correcto.
2. Elige un tipo y registro con documentos. Compara Fecha del documento con Última carga. Un documento sin versiones debe decir Sin archivo.
3. Abre Versiones y archivos y verifica la fecha más reciente. En Subir nueva versión comprueba formatos y ayuda de 20 MB.
4. Con administrador u operador y un documento de pruebas, abre Dar de baja. Cancela primero: el documento permanece.
5. Reabre y prueba guardar sin motivo o sin confirmación: no debe enviarse la baja. Completa ambos y confirma sólo si quieres retirar ese documento de prueba de todos sus vínculos.
6. Tras el éxito, el documento deja de aparecer en la lista. Con geógrafo o visualizador no debe mostrarse Dar de baja.
