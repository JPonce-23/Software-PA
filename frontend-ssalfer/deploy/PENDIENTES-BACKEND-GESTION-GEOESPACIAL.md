# Pendientes de backend — Gestión geoespacial

Estas observaciones no implican cambios de backend en esta ronda.

## Demostración QA: revisiones de aparición sin nombre de destino (15-10-2026)

Al preparar el proyecto 4 «QA Flujo Integral SSALFER 2026», la carga 11 generó diez revisiones `aparece_en_nueva_version`. Tanto el listado como el detalle de la revisión 10 responden HTTP 200, pero entregan `destino: null` e `id_proyecto_nucleo: null`, aun después de confirmar los diez núcleos. Sí conservan `id_feature_nueva` e `id_importacion_nueva: 11`.

La pantalla muestra «Destino sin nombre disponible». No impide confirmar las geometrías ni verlas en el mapa, pero dificulta identificar qué núcleo se está revisando. `gis_history.appearances` registra la aparición mediante el elemento del archivo y `gis_read_models.revisions` resuelve nombres únicamente con el vínculo administrativo almacenado. Evaluar una proyección de lectura que identifique el elemento de origen y, cuando exista, su destino confirmado, sin alterar el historial ni inventar destinos.

No se modificó backend. Evidencia local: `outputs/demo-geoespacial-qa-2026-10-14/revision-diagnostico.json`. Se comprobó también que el detalle se abre desde una entrada nueva a la pantalla.

## Actualización del 14 de octubre de 2026

Los contratos GIS 029 y entregas 2/3 ya resuelven la consulta explícita de inactivas, la baja lógica con motivo y los diagnósticos registrados por elemento. El frontend ya consume esas capacidades. Los apartados siguientes conservan el antecedente de la revisión anterior; no deben interpretarse como funciones que siguen faltando.

Actualización del 15/10/2026: con autorización del usuario se amplió la baja del endpoint existente a cargas confirmadas y con dependencias. Admin/geógrafo con permiso GIS pueden retirar sus geometrías vigentes del mapa, conservando archivo, decisiones e historial. Las dependencias históricas se conservan y no bloquean la baja. Si está procesándose, debe terminar primero. Las inactivas se consultan con `incluir_inactivas=true` en modo de sólo lectura. No se añadió reactivación ni restauración automática de versiones. Véase `QA-UX-BAJAS-Y-FICHA-PROYECTO-2026-10-15.md` para pruebas y alcance.

Los diagnósticos registrados tienen prioridad sobre las orientaciones locales. Los históricos no disponibles se identifican sin inventar motivos; los conteos desconocidos se muestran como «No disponible». Se distingue el universo actual del contexto guardado por cada ciclo.

Sigue pendiente evaluar filtros de estado, tipo y fechas en servidor para historiales muy grandes. También sigue vigente la observación sobre una eventual restricción de confirmación conjunta impuesta por backend. No se detectó un defecto del contrato que impida implementar esta ronda.

## Antecedente: historial, inactivas y baja lógica

La consulta actual de importaciones del proyecto sólo devuelve registros activos y admite `skip` y `limit`. No permite solicitar inactivas ni dar de baja una importación desde este flujo.

El frontend filtra estado, tipo y fechas sobre todas las páginas disponibles, no sólo sobre las primeras 25 filas. Por eso requiere descargar el historial activo completo antes de aplicar los filtros. Para historiales muy grandes conviene evaluar filtrado y paginación en servidor con un total filtrado consistente.

Pendientes: consulta autorizada de activas/inactivas, baja lógica con motivo obligatorio, permisos, auditoría y definición del efecto de dar de baja una importación que ya confirmó geometrías. La baja no debería interpretarse como restauración automática de una versión anterior. La interfaz informa que estas funciones aún no están disponibles, sin enviar peticiones a endpoints inventados.

## Antecedente: motivo preciso de falta de coincidencia

La interfaz muestra valores y columnas originales para compararlos con SSALFER. No inventa qué campo falló: el estado sin coincidencia no identifica por sí solo si falta un vínculo, un registro o si difieren uno o más campos.

El modal añadido el 13 de octubre reutiliza los atributos originales para indicar campos vacíos o no identificados. No deduce diferencias de municipio, entidad o tipo a partir del estado sin coincidencia.

Evaluar un diagnóstico estructurado por elemento que explique qué criterio impidió la asociación, sin exponer registros fuera de los permisos del usuario.

## Permisos de confirmación conjunta

El botón conjunto es exclusivo de administrador en frontend. Los servicios individuales existentes permiten decisiones de geógrafos. Una regla de exclusividad impuesta por servidor para operaciones conjuntas requiere diseño y autorización propios; la restricción visual no sustituye esa validación.


## Caso verificado: parcela 35 de México–Querétaro (14-10-2026)

El núcleo coincide en los cuatro criterios, pero no tiene parcelas administrativas. El proyecto tiene cero parcelas elegibles; la carga 8 ya está completa con 997 sin coincidencia y cero geometrías importadas. No es un error de geometría ni un bloqueo causado por «Información histórica parcial».

Pendiente operativo: registrar/importar parcelas y sus vínculos administrativos, después ejecutar Nueva conciliación. Pendiente de alcance funcional, sólo si se requiere: definir publicación de cartografía parcelaria antes de disponer de esas relaciones. Exige evaluación del backend; no se implementó un atajo desde frontend.

Evidencia y pasos: [Diagnóstico del registro 35](DIAGNOSTICO-PARCELA-35-MQ-2026-10-14.md).
