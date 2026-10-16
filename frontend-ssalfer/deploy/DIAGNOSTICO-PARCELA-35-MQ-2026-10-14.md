# Diagnóstico del registro 35 — parcelas de México–Querétaro

Consulta del 14 de octubre de 2026. Se revisaron el GPKG original de Downloads y la base utilizada por el backend local de QA (puerto 8010). Todas las consultas SQL se ejecutaron con `SET TRANSACTION READ ONLY` y rollback. No se modificaron frontend, backend, endpoints, datos, geometrías ni decisiones.

## Hallazgo confirmado

El núcleo sí coincide. Falta el registro administrativo de la parcela y su vínculo con el proyecto. El importador actual asocia polígonos a parcelas existentes; no crea parcelas a partir del GPKG ni basta con asociar todas las parcelas directamente al núcleo.

| Evidencia | Resultado |
| --- | --- |
| Archivo original | `C:/Users/jplop/Downloads/TMQ_PARCELAS.gpkg` |
| Fila GPKG | `fid=35`, atributo `id=1029` |
| Núcleo | SAN SEBASTIAN DE LAS BARRANCAS |
| Municipio / entidad / tipo | SAN JUAN DEL RÍO / QUERÉTARO / EJIDO |
| Referencias del archivo | `PARCELA=24 Z-1 P 1/4`; `Num_parcela=024` |
| Carga correcta de Parcelas | Importación 8, `parcela_gpkg` |
| Elemento almacenado | 3156; índice 34; identificador externo 35 |
| Resultado del elemento | Geometría válida, sin errores, sin coincidencia |
| Núcleo registrado y vinculado | Núcleo 149, vínculo proyecto-núcleo 149; ambos activos |
| Comparación real del núcleo | Coinciden nombre normalizado, municipio, entidad y tipo de núcleo |
| Parcelas administrativas del núcleo 149 | 0 (no hay registros, ni siquiera inactivos, en la consulta del núcleo) |
| Unidades agrarias activas del núcleo con parcela | 0 |
| Afectaciones activas del núcleo en el proyecto | 2; por sí solas no constituyen vínculos a parcelas |
| Parcelas activas en los núcleos vinculados al proyecto 3 | 0 |
| Parcelas elegibles del proyecto (`vw_gis_parcela_proyecto`) | 0 |
| Carga 8 completa | 997 válidos, 0 errores, 997 sin coincidencia, 0 importados |
| Estado actual de la carga 8 | `completo`, confirmada el 12-10-2026 a las 18:18:41 UTC |
| Ciclo 5 | Finalizado, 0 destinos administrativos guardados |

## Qué significa el mensaje histórico

«Información histórica parcial» indica que el ciclo antiguo permite reconstruir sólo algunos conteos. En una importación de parcelas, los destinos históricos no demuestran cuántos núcleos existían sin parcelas elegibles. Por eso el conteo de núcleos dice «No disponible», no cero.

Las advertencias de cero parcelas y cero destinos proceden del contexto histórico. La consulta actual también confirma cero destinos elegibles. Estas advertencias informativas no bloquean por sí mismas el cierre.

La carga 8 ya está completa; el botón Finalizar no se habilita para finalizar otra vez una carga completa. Cerrar una carga con elementos sin coincidencia no publica sus polígonos. Si se está consultando la carga 7, es el mismo nombre de archivo pero fue importado como Núcleos agrarios: no sirve para publicar correctamente parcelas.

## Regla actual y ruta para resolver

La vista administrativa exige vínculos activos entre proyecto, núcleo, afectación, unidad agraria y parcela. Después se compara el núcleo y el número de parcela. La relación admite muchas parcelas por núcleo; lo que falta aquí son las parcelas individuales y sus relaciones.

1. Registrar o importar administrativamente las parcelas con sus referencias verificadas.
2. Vincularlas al núcleo y al proyecto por el flujo de afectación/unidad agraria previsto por el sistema.
3. En la carga 8 de tipo Parcelas, ejecutar Nueva conciliación para comparar contra los registros actuales. El backend permite una nueva conciliación sobre una carga completa y la devuelve al estado de previsualización.
4. Revisar y confirmar las asociaciones, y finalizar cuando se hayan resuelto los pendientes. Sólo los polígonos confirmados se publican en el mapa.

No es necesario volver a subir el mismo GPKG sólo para repetir la comparación. Ejecutar Nueva conciliación antes de crear los registros volvería a producir cero coincidencias.

La comparación actual no convierte automáticamente `024`, `24` y `24 Z-1 P 1/4` en el mismo identificador. Evalúa las columnas de número por separado, conserva ceros iniciales y sufijos y normaliza espacios/mayúsculas. Es un punto a revisar al preparar los registros, pero no es la causa inmediata de este caso: ahora no existe ninguna parcela administrativa contra la cual comparar.

## Pendientes para evaluar

- Preparar la carga administrativa de parcelas y sus vínculos; el registro de núcleos y afectaciones por sí solo no cubre este requisito.
- Si el objetivo de negocio es mostrar cartografía de parcelas antes de tener los registros administrativos, definir un flujo independiente y explícito en backend. El flujo actual no ofrece esa publicación únicamente por coincidencia del núcleo. No se debe simular desde frontend ni crear registros automáticamente sin una regla aprobada.
- Mantener claramente diferenciados «Carga completa» y «Geometrías confirmadas». La ausencia de coincidencias puede ser compatible con el cierre, pero no con publicar esos polígonos.

Este caso no demuestra un error de lectura del GPKG ni un fallo del emparejamiento del núcleo. Confirma un requisito administrativo no satisfecho y una diferencia entre cerrar la carga y publicar sus geometrías.

Fuentes de código: `backend/app/services/gis_reconciliation.py` (`administrative_universe`, `nucleus_criteria`, `build_candidates`, `finalize`); `backend/app/services/gis_universe.py` (`historical_context`); `backend/app/services/gis_history.py` (`reconcile`); vista de `backend/db/migrations/025_conciliacion_gis_proyecto.sql`.
