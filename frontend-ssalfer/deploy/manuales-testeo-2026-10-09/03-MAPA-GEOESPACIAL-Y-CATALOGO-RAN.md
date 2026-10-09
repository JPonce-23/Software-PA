# Manual 3 — Mapa, gestión geoespacial y catálogo RAN

**Fecha:** 9 de octubre de 2026. **Alcance:** cierre frontend del 8 de octubre.

Trabajar en `http://127.0.0.1:5184`, con proyectos y archivos de prueba identificados por el responsable de QA. Registrar cada caso como Aprobado, Falló o No ejecutado. Una lista vacía no demuestra que un caso con información funcione; si falta el ejemplo necesario, dejarlo como No ejecutado.

## Qué preparar antes de comenzar

Solicitar una cuenta administradora o de geógrafo para cargar y confirmar cartografía; y cuentas de operador/visualizador para comprobar consulta sin esas acciones. Para vincular núcleos y hacer el alta excepcional usar la cuenta autorizada que indique el responsable.

Se necesitan dos proyectos de prueba con áreas claramente distintas, un proyecto sin geometrías, archivos válidos de trazo, derecho de vía, núcleos y parcelas, y un archivo problemático cuyo rechazo sea conocido. El responsable geoespacial debe indicar qué contiene cada archivo, a qué proyecto corresponde, su sistema de coordenadas y si la entrega es parcial o completa. El tester no debe adivinar esos datos.

Preparar también un ejemplo con geometría confirmada, uno con varias versiones y, si existe, otro con geometría histórica anterior al nuevo proceso. Para revisar todas las páginas, solicitar listas de 0, 25, 26 y 51 registros; pueden ser datos ya preparados de QA. No subir decenas de archivos reales sólo para aumentar un contador.

**Importante para esta prueba:** cargar, seleccionar un destino, rechazar, ignorar, conciliar o confirmar pueden registrar cambios. Ejecutar esas acciones únicamente sobre los casos de prueba acordados. Anotar las superficies administrativas antes de empezar: el mapa no debe reescribirlas.

## 1. Mapa del proyecto

**Cómo llegar.** Desde el dashboard, abrir Ver mapa. Para entrar con un proyecto elegido, utilizar el acceso del proyecto o seleccionar su nombre en el mapa.

**Qué debe verse.** Un selector de proyecto, el nombre del proyecto seleccionado, acceso a su información general y a Gestionar cartografía; controles de capas, el mapa, un panel de detalle y un resumen del proyecto. Las capas deben distinguir Trazos del proyecto, Derecho de vía vigente, Núcleos agrarios y Parcelas. La previsualización temporal, cuando se abre desde una carga, se distingue de la información ya confirmada.

### C01 — Entrar sin proyecto y seleccionar uno

1. Entrar a Ver mapa desde el dashboard sin enviar un proyecto en el enlace.
2. Comprobar que pide seleccionar uno, sin cargar por su cuenta el primero.
3. Seleccionar el primer proyecto preparado y esperar que termine de cargar.
4. Comparar nombre, área mostrada y resumen con la referencia proporcionada por QA.
5. Elegir Ver información general y comprobar que abre la ficha de ese mismo proyecto.

**Resultado esperado:** nombre, geometrías y ficha corresponden al proyecto elegido. No se interpreta un mapa vacío como un error si ese proyecto realmente no tiene geometrías.

### C02 — Trazo y derecho de vía por separado

1. Seleccionar el proyecto con trazo y derecho de vía confirmados.
2. Desactivar Derecho de vía vigente: el polígono de derecho de vía debe ocultarse y el trazo continuar visible.
3. Reactivar el derecho de vía y desactivar Trazos del proyecto: ahora debe ocultarse el trazo y permanecer el derecho de vía.
4. Repetir con Núcleos agrarios y Parcelas, comprobando cada capa por separado.
5. Usar Tab para llegar al control del derecho de vía y la barra espaciadora para cambiar su selección.

**Resultado esperado:** cada control afecta únicamente a su capa. El derecho de vía tiene un aspecto reconocible, diferente del trazo; el control, la leyenda y el dibujo no se contradicen.

### C03 — Seleccionar una geometría y consultar su detalle

1. Hacer clic en el derecho de vía visible.
2. Revisar su nombre, proyecto, estado y enlace Consultar cartografía.
3. Comprobar que desaparece el mensaje que pedía seleccionar una geometría.
4. Seleccionar después un núcleo y una parcela preparados; comparar su identificación con la ficha correspondiente.
5. Abrir el enlace de información que ofrezca el detalle y comprobar que corresponde al registro elegido.

**Resultado esperado:** nunca aparecen simultáneamente el detalle seleccionado y el aviso de que todavía falta seleccionar. No se muestra información de una geometría anterior como si fuera la actual. Los datos disponibles deben ser legibles; no se deben inventar nombres ausentes.

### C04 — Cambiar de proyecto y evitar mezclas

1. Elegir el primer proyecto y, mientras carga o inmediatamente después, elegir el segundo.
2. Esperar a que termine la carga.
3. Revisar nombre, resumen, capas y detalle: todo debe pertenecer al segundo.
4. Repetir cambiando de proyecto con un detalle abierto.
5. Volver al primero y comprobar que recupera sus propias geometrías.

**Resultado esperado:** no quedan polígonos, trazos ni detalles del proyecto anterior. Una respuesta que tarde más no debe devolver la pantalla a una selección vieja.

### C05 — Proyecto vacío y errores controlados

1. Abrir el proyecto sin geometrías.
2. Comprobar que se informa esa condición sin anunciar una carga fallida.
3. Con ayuda de soporte, probar un proyecto no autorizado o una consulta interrumpida.
4. Leer el aviso y volver a seleccionar un proyecto permitido cuando se recupere el servicio.

**Resultado esperado:** se distingue entre ausencia de geometrías, falta de permiso y problemas de consulta. El mapa puede recuperarse sin mostrar información de otro proyecto como sustitución.

## 2. Gestión geoespacial e importaciones

**Cómo llegar.** Desde el mapa del proyecto, pulsar Gestionar cartografía, o usar el acceso de Gestión geoespacial disponible en el sistema.

**Qué debe verse.** Proyecto seleccionado, configuración del sistema de coordenadas, opciones para cargar archivos, historial de importaciones y sus detalles. En los procesos nuevos de derecho de vía, núcleos y parcelas se presentan revisión o conciliación de elementos, finalización y, cuando corresponde, historial de conciliaciones. El trazo conserva su flujo propio; no exigir que tenga todos los botones de conciliación de núcleos.

### C06 — Revisar configuración y permisos

1. Confirmar el nombre del proyecto antes de cualquier carga.
2. Comparar el sistema de coordenadas mostrado con el dato proporcionado por el responsable geoespacial.
3. Con geógrafo o administrador, abrir Cambiar sistema de coordenadas y cancelar, sin guardar.
4. Repetir con operador y visualizador: deben poder consultar lo autorizado, sin acciones para cambiar configuración, cargar o confirmar cartografía.
5. Si existe un caso de cambio de sistema autorizado, ejecutarlo sólo en ese proyecto. Para un proyecto con geometrías confirmadas, comprobar el rechazo previsto sin alterar sus datos.

**Resultado esperado:** no se cambian coordenadas accidentalmente. Si el sistema rechaza una modificación, explica el motivo y conserva la configuración anterior. El tester no debe cambiar la selección sólo para intentar eliminar un aviso.

### C07 — Preparar una carga [registra información]

1. Con cuenta autorizada, abrir la opción de nueva importación.
2. Elegir el tipo que realmente contiene el archivo: trazo, Derecho de vía (DDV), Núcleos agrarios o Parcelas.
3. Completar fuente, fecha y demás campos que muestre el formulario. En núcleos/parcelas, elegir entrega parcial o completa de acuerdo con el caso preparado.
4. Seleccionar el archivo de prueba y pulsar Preparar previsualización.
5. Esperar; comprobar nombre del archivo, tipo, formato, sistema de coordenadas, cantidad de elementos, válidos, advertencias y errores.
6. Repetir con cada tipo de archivo preparado en su caso independiente.

**Resultado esperado:** la pantalla muestra la información del archivo enviado y no la de una carga anterior. Preparar una previsualización no debe presentarse como confirmación o publicación definitiva. No volver a enviar por impaciencia mientras se está procesando.

### C08 — Archivo incorrecto, advertencias y reintento

1. Intentar preparar el archivo problemático proporcionado por QA.
2. Leer y capturar el mensaje, incluyendo las advertencias si las hay.
3. Comprobar que no se anuncia una carga confirmada cuando fue rechazada.
4. Corregir únicamente lo indicado por el responsable y reintentar.
5. Para el caso válido de C07, volver a enviar exactamente el mismo archivo con la misma configuración, si el caso autoriza esta comprobación.

**Resultado esperado:** los errores se explican y permiten volver al formulario. El mismo archivo/configuración debe reutilizar su procesamiento según lo informado por el sistema; no debe aparentar nuevas publicaciones independientes. Un archivo con contenido distinto puede generar otro registro.

### C09 — Previsualización en el mapa

1. Abrir Ver detalle de una importación y Revisar elemento cuando corresponda.
2. Observar el mapa pequeño y sus observaciones.
3. Pulsar Abrir previsualización en el mapa.
4. Comprobar que se centra en el elemento temporal y que se indica que aún no está confirmado.
5. Repetir con un elemento de prueba sin geometría disponible.
6. Regresar a la gestión y cambiar de proyecto mientras se abre otro elemento.

**Resultado esperado:** la geometría temporal se distingue en naranja y no se presenta como versión vigente. Si no hay geometría, se muestra un mensaje claro; no un mapa que aparente tenerla. Cambiar de proyecto descarta el detalle anterior.

## 3. Conciliación, historial y revisiones

**Qué debe verse.** Al abrir una importación de núcleos o parcelas, la lista presenta elementos del archivo, resultado y observaciones, un filtro Estado de conciliación, botones Anterior/Siguiente y el rango visible con su total. Revisar elemento muestra los destinos propuestos y el historial de decisiones. Los destinos deben identificarse por nombres, ubicación y parcela cuando corresponda.

### C10 — Filtrar elementos y comprobar sus nombres

1. Abrir una importación con elementos en distintos estados.
2. En Estado de conciliación, elegir uno presente; comparar las filas con el resultado seleccionado.
3. Elegir otro estado y después Todos.
4. Elegir un estado sin registros y revisar el mensaje.
5. Abrir Revisar elemento en una parcela con destino conocido; comprobar núcleo, número de parcela, municipio y entidad cuando estén disponibles.

**Resultado esperado:** el total corresponde al filtro, no al archivo completo. Los nombres permiten reconocer el destino sin escribir números internos. Un dato ausente debe tener una explicación legible, no un nombre inventado.

### C11 — Seleccionar, confirmar, rechazar o ignorar [guarda decisiones]

**Preparación:** acordar qué elemento se usará para cada decisión; no ejecutar todas sobre el mismo elemento sin un plan.

1. En el caso de selección, abrir Revisar elemento, elegir el destino correcto y pulsar Seleccionar. Completar el formulario que aparezca y guardar.
2. Revisar el historial: debe reflejar la elección. No darla por publicada sólo por haberla seleccionado.
3. En el caso de confirmación, pulsar Confirmar y marcar que se revisaron destino y geometría. Aceptar advertencias únicamente cuando el responsable haya verificado que son admisibles.
4. En otro caso preparado, usar Rechazar con un motivo; en otro, Ignorar elemento con su motivo.
5. Recargar la consulta después de cada decisión y comprobar el estado y el historial.

**Resultado esperado:** cada acción registra su propia decisión y actualiza la consulta. Seleccionar registra una elección, mientras Confirmar incorpora la geometría. Rechazar e Ignorar no deben aparentar una confirmación. Si hay conflicto, se informa y no se anuncia guardado exitoso.

### C12 — Sin coincidencias y nueva conciliación [puede guardar datos]

1. Abrir el caso preparado cuyos elementos no encuentran destinos.
2. Revisar el aviso No hay coincidencias, la cantidad de núcleos vinculados y los nombres del archivo que se ofrecen como referencia.
3. Utilizar Ir a vincular núcleos y comprobar que abre la ficha del proyecto correcto.
4. Si está autorizado, vincular el núcleo adecuado siguiendo C17. Volver a la importación y pulsar Nueva conciliación.
5. Escribir un motivo reconocible; usar las opciones de volver a revisar ambigüedades o destinos rechazados sólo según el caso acordado.
6. Guardar, revisar el resultado y abrir Historial de conciliaciones.

**Resultado esperado:** la nueva comparación usa los registros actuales y conserva el historial anterior. No debe borrarse una decisión previa para fingir que nunca existió. Si siguen faltando datos para coincidir, el sistema debe indicarlo.

### C13 — Actores y destinos en los historiales

1. Abrir Historial de decisiones y Ver ciclo en una conciliación preparada.
2. Comparar acción, motivo, fecha y persona con la referencia de QA.
3. Revisar un caso realizado por un usuario que posteriormente fue dado de baja.
4. Revisar un caso histórico sin nombre disponible, si fue preparado.
5. Abrir una revisión asociada a una parcela y comprobar que el nombre del núcleo y la parcela coinciden con el destino conocido.

**Resultado esperado:** un actor inactivo conserva su nombre cuando existe en el historial. Si no hay nombre, aparece una indicación como Nombre de usuario no disponible; no se expone únicamente un número incomprensible. No dar de baja cuentas reales para fabricar este caso.

### C14 — Finalizar y comprobar la publicación [guarda datos]

1. En una importación con pendientes conocidos, intentar Finalizar conciliación o Confirmar versión de DDV, según el tipo.
2. Comprobar que los pendientes bloqueantes se informan y que no se publica silenciosamente.
3. Resolver únicamente los casos acordados; volver a finalizar y confirmar la revisión requerida.
4. Abrir el mapa normal del proyecto, sin el enlace de previsualización. Recargarlo.
5. Comprobar que aparece la geometría confirmada en su capa correspondiente y que no se indica erróneamente que lo confirmado no se publica.
6. Para un caso autorizado con segunda versión, comprobar que se muestra la vigente esperada, sin dibujar una versión antigua como si fuera actual.
7. Comparar las superficies administrativas anotadas al inicio.
8. En el proyecto histórico preparado, comprobar que siguen consultándose sus geometrías anteriores cuando el servidor las considera vigentes.

**Resultado esperado:** la publicación sigue la confirmación válida; la versión vigente coincide con el caso preparado. No se sobreescriben superficies administrativas por cargar o dibujar un polígono. La comprobación del proyecto histórico no requiere editar sus geometrías.

### C15 — Revisiones geoespaciales y sus filtros [consulta; resolver guarda]

1. Localizar Revisiones geoespaciales.
2. Filtrar Estado por Pendiente, Revisado, No aplica y Aplicado, usando casos preparados; probar también Todos.
3. Filtrar Capa por Derecho de vía, Núcleo o Parcela y combinar con Estado.
4. Probar Tipo de cambio: Aparece en nueva versión, Desaparece en nueva versión, Geometría modificada o Cambio de relación con DDV, según los ejemplos disponibles.
5. Abrir Consultar revisión; comprobar capa, destino, fecha, persona y las superficies que se informen. Una ausencia de dato no debe transformarse en cero por cuenta de la pantalla.
6. Con un caso autorizado, usar Marcar como revisado, No aplica o Aplicado; registrar el motivo y, para Aplicado, el evento de seguimiento si corresponde.
7. Recargar y buscar la revisión bajo el estado nuevo.

**Resultado esperado:** las filas cumplen todos los filtros elegidos. Una combinación vacía muestra un aviso normal. La decisión guardada queda en el historial con su motivo y no se pierde al recargar.

### C16 — Páginas y totales de las cuatro listas

Aplicar esta prueba por separado a **importaciones**, **elementos**, **historial de conciliaciones** y **revisiones**. El responsable debe preparar las cantidades y decir cuál lista corresponde a cada caso.

| Cantidad preparada | Comprobación esperada |
|---|---|
| 0 | Mensaje sin registros y sin poder avanzar a páginas ficticias. |
| 25 | Una página completa; Siguiente deshabilitado. |
| 26 | Primera página con 25; segunda con 1; Siguiente deshabilitado al final. |
| 51 | Páginas con 25, 25 y 1; Anterior permite volver sin perder registros. |

1. Anotar el rango visible y el total en la primera página.
2. Avanzar y retroceder; comparar primero/último registro para detectar repeticiones o saltos inesperados.
3. En elementos, aplicar un filtro que reduzca el total. En revisiones, combinar sus filtros.
4. Comprobar que el total cambie al de los resultados filtrados y que una búsqueda nueva empiece desde la primera página.
5. Cambiar de proyecto y revisar que no queden rango, filas o botones de la lista anterior.

**Resultado esperado:** no se exige una página extra vacía para descubrir que terminó una lista de exactamente 25. El total del archivo no reemplaza al total filtrado. Si no se prepararon suficientes registros para una lista, dejar esa parte como No ejecutada.

## 4. Catálogo RAN y vinculación al proyecto

**Cómo llegar.** En la ficha de un proyecto, abrir Agregar núcleo agrario con la cuenta autorizada.

**Qué debe verse.** Nombre del núcleo, filtros de entidad y municipio, Buscar en catálogo RAN, selector Núcleo del catálogo y una indicación de resultados. La casilla No aparece en el catálogo: crear núcleo nuevo mantiene separada el alta excepcional del uso del catálogo existente.

### C17 — Buscar y vincular un núcleo del catálogo [vincular guarda]

1. Seleccionar una entidad y esperar sus municipios. Elegir un municipio.
2. Escribir el nombre acentuado preparado y pulsar Buscar en catálogo RAN.
3. Revisar que los resultados muestren nombre, tipo de tenencia, municipio y entidad coherentes con los filtros.
4. Cambiar de entidad y comprobar que no se conserva como selección válida un municipio de la anterior; hacer una nueva búsqueda.
5. Elegir el núcleo de prueba correcto y completar la vinculación al proyecto si está autorizada.
6. Recargar la ficha y comprobar que el núcleo vinculado corresponde al elegido y no aparece duplicado por reintentar.

**Resultado esperado:** el texto conserva sus acentos aunque se muestre en mayúsculas. La selección se realiza por un nombre legible y su ubicación. Buscar por sí solo no vincula el núcleo; la vinculación requiere guardar la operación.

### C18 — Límite, vacío y alta excepcional

1. Con un criterio amplio preparado, obtener 100 resultados.
2. Comprobar que se pide precisar el nombre o los filtros. No debe ofrecer una segunda página inexistente.
3. Afinar el criterio y repetir la búsqueda; elegir el resultado correcto si aparece.
4. Probar un criterio sin coincidencias y revisar el mensaje.
5. Marcar No aparece en el catálogo: crear núcleo nuevo. Revisar que se distinga el alta excepcional y sus campos; cancelar si no hay un caso de alta acordado.
6. Si se autorizó un alta excepcional, completar nombre, municipio y tenencia con los datos ficticios acordados, guardar una sola vez y comprobar el resultado.

**Resultado esperado:** no se interpreta que el núcleo no existe sólo por no estar entre los primeros 100. Se invita a refinar; el alta excepcional no sustituye automáticamente una búsqueda sin resultados.

## Cierre del bloque

Registrar C01–C18 y cada subcaso de paginación. Adjuntar capturas con nombre del proyecto, control de capas, detalle, filtros y total visible. Para cargas, anotar nombre del archivo, tipo elegido, fecha/hora y motivo de cada decisión. Distinguir las pruebas que sólo consultaron de las que confirmaron información.

No exigir en este cierre cálculos oficiales nuevos de superficie, configuración nueva de mapas base o estados de proyecto que todavía no existan. Si surge una falla, describir lo observado y lo esperado; el equipo técnico determinará si se origina en pantalla o servidor.
