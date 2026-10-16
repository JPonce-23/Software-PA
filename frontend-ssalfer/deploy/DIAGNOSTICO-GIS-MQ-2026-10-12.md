# Importación GIS de México–Querétaro — 12 de octubre de 2026

## Entorno y alcance

Proyecto 3, México–Querétaro, base `db_integracion_mq_qa_local`, frontend QA 5184 y backend QA 8010. Se analizaron únicamente DDV, núcleos y parcelas de Downloads; se omitió Obras transversales. No se cambiaron backend, endpoints, geometrías, decisiones ni vínculos administrativos. Se usaron las importaciones existentes para verificar el procesamiento real; no se subieron duplicados ni se confirmaron propuestas de forma automática.

## Evidencia de archivos y datos reales

Los tres GPKG conservan las mismas huellas SHA-256 que las cargas existentes. GDAL volvió a revisar todos sus elementos: MultiPolygon Z, EPSG:32614, sin geometrías inválidas ni vacías.

| Archivo / importación correcta en México–Querétaro | Elementos válidos | Situación |
|---|---:|---|
| TMQ_DDV.gpkg / 4 | 1 de 1 | Confirmado y vigente |
| TMQ_NUCLEOS_AGRARIOS.gpkg / 5 | 64 de 64 | 61 candidatos, 3 sin coincidencia, 0 confirmados |
| TMQ_PARCELAS.gpkg / 8 | 997 de 997 | 997 sin coincidencia, 0 errores geométricos |

La importación 6 contiene el mismo archivo de parcelas, pero se procesó como trazo y tiene 997 errores. La 7 también contiene parcelas, pero se procesó como núcleos: generó 839 candidatos y 158 elementos sin coincidencia. Esas propuestas de la carga 7 no deben confundirse con polígonos de núcleos validados; requieren revisión del tipo de entrega.

Se volvieron a ejecutar las reglas de coincidencia sobre el universo administrativo actual de México–Querétaro, sin guardar decisiones: 61 de 64 núcleos coinciden. El universo de parcelas tiene cero destinos. La vista `vw_gis_parcela_proyecto` requiere relaciones activas entre proyecto-núcleo, afectación, unidad agraria y parcela; no basta con que coincida un nombre en el archivo. No se crearon esas relaciones a partir del GPKG.

Las tres diferencias de núcleos siguen siendo: municipio distinto para ACOCULCO DE TULA; PUERTA DE PALMILLAS sin vínculo al proyecto; SANTA MARIA MACUA frente a STA MARIA MACUA. La corrección administrativa requiere validar los datos.

Como comprobación espacial adicional con las geometrías normalizadas y el DDV vigente, 63 de 64 núcleos y 713 de 997 parcelas intersectan el DDV. Esto no constituye una regla de identidad ni prueba que las restantes geometrías estén mal: intersectar el DDV y coincidir con un registro administrativo son comprobaciones diferentes.

## Cambios del frontend

- Aviso de nombres/números y vínculos a revisar; acceso a registros con diseño de botón.
- DDV explicado como franja poligonal y trazo como recorrido lineal opcional. Para estos archivos no hace falta cargar trazo.
- Advertencia cancelable cuando el nombre del archivo sugiere un tipo distinto al seleccionado. No se usa el nombre como validación de geometría.
- Consulta conjunta de coincidencias mediante una capa temporal claramente identificada. Incluye candidatos únicos, coincidencias fuertes y confirmados del archivo; no incorpora ambiguos ni cambia versiones vigentes.
- Detalle de conciliación en el mapa por archivo, con cantidades y nombres sin coincidencia. Consulta paginada y limpieza al cambiar de proyecto.
- Historial indica el número confirmado en cada carga y aclara que consultar no activa otra versión. No se llama “vigente” al archivo más reciente ni al que solo está completo.
- Explicación de Revisiones geoespaciales: seguimiento de diferencias entre entregas y cambios respecto al DDV. Marcar una revisión no cambia por sí solo la versión visible.

## Pendientes que requieren backend

1. **Activar/restaurar una entrega anterior:** no existe una operación actual para hacerlo por importación. Definir alcance por proyecto y capa, autorización, advertencia de reemplazo, transacción, auditoría y tratamiento de entregas parciales. Una entrega puede aportar solo parte de las geometrías vigentes; “último archivo” no equivale a “único archivo activo”.
2. **Eliminar/retirar una carga:** falta una operación de retiro con control de dependencias y conservación del historial. No agregar un botón que solo oculte localmente los datos o borre el registro por SQL.
3. **Identificar archivos vigentes en el historial:** el mapa devuelve tipo, ID y nombre de geometría, pero no el ID de importación de origen. Hace falta exponer la procedencia y cuántas geometrías de cada entrega siguen vigentes para etiquetar el historial con certeza.
4. **Carga con tipo equivocado:** mejorar validación inicial de esquema/objetivo en el servidor. El frontend ahora advierte por el nombre del archivo, pero no garantiza detectar todo contenido incorrecto.
5. **Parcelas sin destinos:** preparar o importar sus registros y relaciones administrativas por el flujo autorizado, o definir expresamente un flujo de cartografía independiente. No eliminar la conciliación ni convertir coincidencias por nombre en confirmaciones automáticas.

## Verificación

- GDAL sobre copias en memoria de los tres GPKG; originales intactos.
- SELECT y reglas de comparación sobre México–Querétaro: 64/64 y 997/997 geometrías válidas; 61 coincidencias de núcleos y cero destinos de parcelas.
- `qa-conciliacion-orientacion.cjs`: API interceptada; selección, ruta existente de parcelas, discrepancia de tipo cancelable, bloqueo de cierre, filtros, error ignorado, DDV y detalle de 409.
- `qa-mapa-coincidencias.cjs`: API interceptada; 61 geometrías temporales y 3 elementos sin coincidencia, limpieza al cambiar proyecto y respuestas tardías. La captura de esta prueba usa geometrías simuladas; no es una captura cartográfica real de México–Querétaro.

La vista temporal sirve para revisar; publicar y restaurar versiones son operaciones distintas. No se probó una nueva confirmación real ni un reemplazo de versión.

## Publicación en QA

Se construyó y recreó únicamente el frontend. Una segunda construcción para incluir el último control de selección falló por resolución DNS de Docker Hub; ese archivo se sincronizó directamente al contenedor frontend. Se compararon por HTTP los ocho archivos de aplicación modificados y todos coinciden con el repositorio. Antes de recrear nuevamente el frontend desde la imagen, reconstruirla para conservar también ese último control. Backend y base de datos no se recrearon.

## Conflicto al cambiar el alcance de un archivo existente

Confirmado en QA: las importaciones 5 (núcleos) y 8 (parcelas) tienen alcance `completa`. El backend compara proyecto, objetivo, hash del contenido, pipeline y CRS; si encuentra el archivo con otro alcance responde 409. Parcial no significa publicar solo las coincidencias, y no corrige la ausencia de destinos administrativos.

Se añadió manejo específico del conflicto: aviso legible, consulta paginada del historial e identificación por SHA-256, proyecto y tipo para ofrecer la carga existente. No hay reintento automático ni modificación del alcance. El selector requiere elegir alcance explícitamente y el historial lo muestra. Las pruebas interceptadas verifican que un archivo homónimo con otro contenido no se ofrezca como si fuera el mismo y que no se envíe un segundo POST.

Cambiar el alcance de una carga existente requiere una decisión y una operación del backend que hoy no está expuesta. Consultar su previsualización sigue disponible aunque el reenvío sea rechazado.

La reconstrucción pendiente por DNS quedó resuelta durante esta corrección de alcance: imagen frontend construida y contenedor recreado correctamente. Los archivos de carga servidos por HTTP coinciden con los locales.


## Pendiente para evaluación del backend: confirmación conjunta exclusiva del administrador

El botón nuevo Confirmar todas las coincidencias sólo se muestra y se ejecuta desde la interfaz para `admin`. Usa la decisión individual existente por cada asociación; no agrega endpoints ni modifica el servidor. El servidor actual permite decisiones individuales de `admin` y `geografo`, por lo que no puede distinguir una serie automatizada de decisiones individuales de una confirmación conjunta. Si se requiere que la exclusividad de la operación masiva sea una regla de seguridad del servidor, deberá evaluarse una operación masiva con autorización propia. No debe presentarse la restricción de interfaz como una garantía del backend.

La ejecución del frontend se detiene al primer fallo y conserva las decisiones anteriores. Después de una pérdida de conexión, consultar el estado antes de reintentar: una petición puede haber sido guardada aunque su respuesta no llegara.


## Consulta posterior: Ignorado y geometría cambiada

Verificado mediante consultas de sólo lectura sobre el entorno local de QA:

- Importación 5, primer elemento: decisión `ignorar`, motivo `PRUEBA-QA`, registrada el 12 de octubre de 2026 a las 18:20:45 UTC (12:20:45 hora de Ciudad de México). Es una decisión persistida, no un error de transformación.
- Importación 7, `TMQ_PARCELAS.gpkg`: registrada como `nucleo_agrario_gpkg`, con 997 elementos válidos en la consulta. No corresponde al tipo Parcelas. Hay 839 propuestas y varios polígonos apuntan al mismo núcleo (hasta 60 propuestas para uno).
- 58 propuestas de esa importación tienen una referencia de geometría anterior diferente a la geometría vigente. El servidor bloquea la confirmación para no sobrescribir un cambio posterior; aceptar advertencias no evita esa verificación.
- Hay una decisión confirmada para el primer elemento de la importación 7. El responsable GIS debe revisar las geometrías confirmadas desde esta carga incorrectamente tipificada y determinar si corresponde restaurarlas. No se restauró ni alteró ninguna geometría durante este diagnóstico.

El frontend ahora orienta sobre tipo de carga incorrecto y propuestas desactualizadas. No se recomienda simplemente repetir la conciliación de la carga 7, porque seguiría interpretando parcelas como núcleos. Evaluar en backend una validación adicional de la semántica de las capas al importar; la validez geométrica por sí sola no detecta esta confusión.
