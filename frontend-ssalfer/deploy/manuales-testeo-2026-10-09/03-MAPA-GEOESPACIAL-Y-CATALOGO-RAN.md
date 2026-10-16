# Manual 3 — Mapa, gestión geoespacial y catálogo RAN

Fecha: 9 de octubre de 2026. Actualizado: 12 de octubre de 2026. De qué trata este bloque: el mapa de cada proyecto, la carga de archivos geográficos (derecho de vía, núcleos y parcelas) y la búsqueda de núcleos en el catálogo oficial del RAN.

Trabaja en `http://127.0.0.1:5184` (o la dirección que te den), con los proyectos y archivos de prueba que te haya preparado el responsable de QA. Anota cada caso como Aprobado, Falló o No ejecutado. Ojo: que una lista aparezca vacía no significa que esa parte "ya funciona" — si no tenías datos de prueba para llenarla, el caso debe quedar como No ejecutado, no como Aprobado.

## Qué preparar antes de comenzar

Pide una cuenta de administrador o de geógrafo (son quienes pueden cargar y confirmar cartografía) y cuentas de operador/visualizador (para confirmar que ellos solo pueden consultar, sin esas acciones). Para vincular núcleos o dar de alta uno de forma excepcional, usa la cuenta que te indique el responsable.

Necesitas: dos proyectos de prueba con áreas bien distintas entre sí, un proyecto que no tenga nada de geometría cargada todavía, y archivos de ejemplo de derecho de vía, núcleos y parcelas — más uno "con problemas a propósito" para ver cómo lo rechaza el sistema. Quien te dé estos archivos debe decirte qué contiene cada uno, a qué proyecto corresponde y si es una entrega parcial o completa — no lo adivines tú.

También pide un ejemplo ya confirmado, uno que tenga varias versiones subidas, y listas de prueba con 0, 25, 26 y 51 registros (para probar que las páginas avanzan bien). No subas decenas de archivos reales solo para llenar un contador — pide que ya te los tengan preparados.

Para las pruebas de conciliación, pide estos ejemplos ya preparados: uno con candidatos que todavía no se han confirmado, otro con algunos elementos sin coincidencia, una parcela cuyo registro todavía no esté relacionado con el proyecto, un error sin resolver y otro que ya se haya ignorado con autorización. También hace falta un ejemplo donde el único pendiente esté en una página posterior. Si el equipo puede preparar más de 500 elementos, pide que uno de los errores esté después del elemento 500; no hace falta que fabriques esa carga tú.

Antes de subir los polígonos, revisa que los registros a los que se van a asociar ya existan y estén relacionados con el proyecto. Para núcleos, se comparan nombre, municipio, entidad y tipo de núcleo, o su clave oficial cuando esté disponible. Para parcelas también se revisa su número. Ojo: el archivo no da de alta automáticamente esos registros.

Si en el sistema dice "San Fernando" y en el archivo dice "Fernando", no esperes que coincidan automáticamente por nombre. Tampoco cambies un nombre o municipio sólo para que pase la prueba: primero debe confirmar el responsable cuál es el dato correcto. Un elemento sin coincidencia puede tener un polígono perfectamente válido; lo que falta es encontrar a qué registro corresponde.

Importante: cargar un archivo, elegir a qué registro corresponde, rechazarlo, ignorarlo, conciliar o confirmar — todas estas acciones pueden modificar información real. Hazlas únicamente sobre los casos de prueba que te hayan asignado. Antes de empezar, anota las superficies (hectáreas/metros) que ya existan en los registros administrativos: el mapa no debería cambiarlas por su cuenta.

## 1. Mapa del proyecto

**Cómo llegar.** Desde el dashboard, abrir Ver mapa. Para entrar con un proyecto elegido, utilizar el acceso del proyecto o seleccionar su nombre en el mapa.

**Qué debe verse.** Un selector para elegir el proyecto, el nombre del que ya está seleccionado, un acceso a su información general y otro a "Gestionar cartografía"; interruptores para prender/apagar capas, el mapa en sí, un panel de detalle (que se llena cuando seleccionas algo en el mapa) y un resumen del proyecto. Las capas que deberías poder distinguir son: Derecho de vía (DDV) vigente, Núcleos agrarios y Parcelas. Si estás viendo una previsualización de algo que acabas de subir pero que todavía no se ha confirmado, el sistema debe dejarte claro que es temporal (normalmente se ve de otro color, como naranja) — para que no lo confundas con información ya oficial.

### C01 — Entrar sin proyecto y seleccionar uno

1. Entrar a Ver mapa desde el dashboard sin enviar un proyecto en el enlace.

2. Comprobar que pide seleccionar uno, sin cargar por su cuenta el primero.

3. Seleccionar el primer proyecto preparado y esperar que termine de cargar.

4. Comparar nombre, área mostrada y resumen con la referencia proporcionada por QA.

5. Elegir Ver información general y comprobar que abre la ficha de ese mismo proyecto.

**Resultado esperado:** nombre, geometrías y ficha corresponden al proyecto elegido. No se interpreta un mapa vacío como un error si ese proyecto realmente no tiene geometrías.

### C02 — Derecho de vía y trazo oculto

1. Selecciona el proyecto preparado con derecho de vía y un trazo antiguo.
2. Comprueba que aparezcan Derecho de vía vigente, Núcleos agrarios y Parcelas. No debe aparecer Trazos del proyecto ni dibujarse su línea.
3. Desactiva Derecho de vía vigente. Debe ocultarse su polígono y apagarse su tren.
4. Actívalo de nuevo. El polígono debe regresar y el tren iluminarse. Repite con Tab y la barra espaciadora.
5. Cambia de proyecto y comprueba que el trazo siga oculto.

**Resultado esperado:** el DDV continúa disponible. Ocultar el trazo no elimina las cargas antiguas del historial de importaciones.

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

**Qué debe verse.** El proyecto que elegiste, la configuración del sistema de coordenadas que usa, opciones para subir archivos nuevos, y el historial de lo que ya se ha subido antes (con sus detalles). Para derecho de vía, núcleos y parcelas vas a ver un paso extra de revisión/"conciliación" (donde el sistema compara lo que subiste contra lo que ya existe) y, al final, un botón para confirmar o finalizar, más el historial de esas conciliaciones. Trazo del proyecto ya no se ofrece para nuevas cargas; las cargas anteriores siguen disponibles para consulta. Al abrir la página, el tipo de información debe decir "Selecciona el tipo de información"; no debe venir elegido Trazo del proyecto. Debajo aparece una explicación que cambia según lo que elijas.

### C06 — Revisar configuración y permisos

1. Confirmar el nombre del proyecto antes de cualquier carga.

2. Comparar el sistema de coordenadas mostrado con el dato proporcionado por el responsable geoespacial.

3. Con geógrafo o administrador, abrir Cambiar sistema de coordenadas y cancelar, sin guardar.

4. Repetir con operador y visualizador: deben poder consultar lo autorizado, sin acciones para cambiar configuración, cargar o confirmar cartografía.

5. Si existe un caso de cambio de sistema autorizado, ejecutarlo sólo en ese proyecto. Para un proyecto con geometrías confirmadas, comprobar el rechazo previsto sin alterar sus datos.

**Resultado esperado:** no se cambian coordenadas accidentalmente. Si el sistema rechaza una modificación, explica el motivo y conserva la configuración anterior. El tester no debe cambiar la selección sólo para intentar eliminar un aviso.

### C07 — Preparar una carga [registra información]

1. Con cuenta autorizada, entrar a Gestión geoespacial y abrir Crear una importación.

2. Sin haber elegido un tipo, comprobar que aparece "Selecciona el tipo de información". Completar los demás campos con los datos de prueba e intentar Preparar previsualización: debe pedir elegir el tipo y no enviar la carga.

3. Abrir el tipo de información. Sólo deben aparecer Derecho de vía (DDV), Núcleos agrarios y Parcelas. Trazo del proyecto no debe ofrecerse. Cambiar entre las tres opciones y comprobar que la ayuda corresponda a lo elegido.

4. Dejar seleccionado el tipo que realmente contiene el archivo. Para núcleos y parcelas, leer el aviso de que primero deben existir los registros y sus relaciones con el proyecto.

5. Completar fuente, fecha y demás campos que muestre el formulario. En núcleos/parcelas, elegir entrega parcial o completa de acuerdo con el caso preparado.

6. Seleccionar el archivo de prueba y pulsar Preparar previsualización una sola vez.

7. Esperar; comprobar nombre del archivo, tipo, formato, sistema de coordenadas, cantidad de elementos, válidos, advertencias y errores. Si elegiste Parcelas, la carga debe aparecer como parcelas, no como trazo.

8. Repetir con cada tipo de archivo preparado en su caso independiente. Para DDV, núcleos y parcelas, usar archivos GPKG.

**Resultado esperado:** se exige elegir el tipo de información y la ayuda explica qué contiene cada tipo de archivo. La pantalla muestra el archivo enviado y el proyecto correcto. Preparar una previsualización no debe presentarse como confirmación o publicación definitiva. No volver a enviar por impaciencia mientras se está procesando.

**Comprobación del alcance:** al elegir Núcleos o Parcelas, el alcance debe pedir una selección; no debe aparecer Parcial elegido por su cuenta. En el caso preparado de un archivo ya cargado como Completa, intentar enviarlo como Parcial. Debe explicarse que ya fue procesado con otro alcance y ofrecer Consultar carga con el número correspondiente. Abrir esa carga sólo consulta su previsualización; no cambia el alcance ni crea otra importación. El historial debe mostrar si la entrega fue completa o parcial. No cambies a Completa sólo para quitar un aviso: si el alcance anterior estaba mal, repórtalo para revisión.

### C08 — Archivo incorrecto, advertencias y reintento

1. Intentar preparar el archivo problemático proporcionado por QA.

2. Leer y capturar el mensaje, incluyendo las advertencias si las hay. Comprobar que no se anuncia una carga confirmada cuando fue rechazada.

3. Abrir también el ejemplo ya preparado donde se cargaron polígonos de parcelas como Trazo del proyecto. No provoques el error en un proyecto real sólo para fabricar este caso.

4. Revisar las observaciones: deben explicar que esa carga espera líneas y que, si son polígonos de núcleos o parcelas, hay que crear una carga con el tipo correspondiente. No debería dejarte únicamente un código difícil de entender.

5. Comprobar que la importación equivocada conserva su resultado y no se convierte por sí sola en una carga correcta. Si está autorizado, hacer una nueva carga en el proyecto de prueba eligiendo el tipo adecuado.

6. Corregir cualquier otro problema únicamente según lo indicado por el responsable y reintentar.

7. Para el caso válido de C07, volver a enviar exactamente el mismo archivo con el mismo proyecto, tipo y configuración, si el caso autoriza esta comprobación.

**Resultado esperado:** los errores se explican y permiten volver al formulario. El mismo archivo/configuración debe reutilizar su procesamiento según lo informado por el sistema; no debe aparentar nuevas publicaciones independientes. Un archivo con contenido distinto puede generar otro registro. Ojo: estas mejoras de pantalla no reparan las cargas antiguas ni garantizan que un archivo enviado con el tipo equivocado se rechace antes de procesarlo.

### C09 — Previsualización en el mapa

1. Abrir Ver detalle de una importación y Revisar elemento cuando corresponda.

2. Observar el mapa pequeño y sus observaciones.

3. Pulsar Abrir previsualización en el mapa.

4. Comprobar que se centra en el elemento temporal y que se indica que aún no está confirmado.

5. Repetir con un elemento de prueba sin geometría disponible.

6. Regresar a la gestión y cambiar de proyecto mientras se abre otro elemento.

**Resultado esperado:** la geometría temporal se distingue en naranja y no se presenta como versión vigente. Si no hay geometría, se muestra un mensaje claro; no un mapa que aparente tenerla. Cambiar de proyecto descarta el detalle anterior.

## 3. Conciliación, historial y revisiones

**Qué debe verse.** Al abrir un archivo ya subido de núcleos o parcelas, vas a ver cada elemento que traía ese archivo, con su resultado (a qué registro se asignó, o si quedó pendiente) y observaciones. Arriba hay un filtro de "Estado de conciliación", botones para Anterior/Siguiente, y debe decirte cuántos hay en total y cuáles estás viendo. Si abres "Revisar elemento", te muestra a qué registros podría corresponder (sus "destinos propuestos") y el historial de decisiones que se han tomado sobre él. Esos destinos deben identificarse por su nombre, ubicación y número de parcela — no por un código que no signifique nada para ti. Cada elemento debe conservar su número y nombre. También vas a encontrar los filtros Por resolver antes de finalizar y Errores por resolver. En Finalizar hay un aviso con lo que falta, accesos a esas listas y un botón Actualizar estado. Si hay pendientes, el botón de finalizar debe estar deshabilitado.

Antes de seguir, prueba también Ver coincidencias en el mapa desde una carga con candidatos. Debe mostrar las coincidencias como una capa temporal claramente identificada. El Resumen cartográfico cuenta únicamente geometrías confirmadas vigentes del proyecto, no esa previsualización ni las cargas repetidas. Los elementos sin coincidencia se consultan y exportan desde Gestión geoespacial. Cambia de proyecto y comprueba que desaparezcan la capa temporal y los datos anteriores.

### C10 — Filtrar elementos y comprobar sus nombres

1. Abrir una importación con elementos en distintos estados.

2. En Estado de conciliación, elegir uno presente; comparar las filas con el resultado seleccionado. Elegir otro estado y después Todos.

3. Elegir Por resolver antes de finalizar y comprobar que reúne los elementos que todavía impiden cerrar la conciliación. Un elemento que sólo está Sin coincidencia, sin errores, no debe aparecer aquí.

4. Elegir Errores por resolver: deben aparecer los errores que todavía necesitan atención, sin incluir los que ya se ignoraron con una decisión registrada.

5. Elegir un estado sin registros y revisar el mensaje.

6. Abrir Revisar elemento en una parcela con destino conocido; comprobar núcleo, número de parcela, municipio y entidad cuando estén disponibles.

7. Anotar el número y nombre de un elemento, cambiar el filtro y volver a encontrarlo. Debe conservar su identificación; no debe renumerarse por ser ahora la primera fila de la lista.

**Resultado esperado:** el total corresponde al filtro, no al archivo completo. Los nombres permiten reconocer el destino sin escribir números internos. Se distingue un error de geometría o datos de un elemento que simplemente no encontró coincidencia. Un dato ausente debe tener una explicación legible, no un nombre inventado.

### C11 — Seleccionar, confirmar, rechazar o ignorar [guarda decisiones]

**Preparación:** acordar qué elemento se usará para cada decisión; no ejecutar todas sobre el mismo elemento sin un plan.

1. En el caso de selección, abrir Revisar elemento, elegir el destino correcto y pulsar Seleccionar. Completar el formulario que aparezca y guardar.

2. Revisar el historial: debe reflejar la elección. Comprobar que ese elemento sigue por resolver; seleccionar por sí solo no publica el polígono ni permite darlo por terminado.

3. En el caso de confirmación, pulsar Confirmar y marcar que se revisaron destino y geometría. Aceptar advertencias únicamente cuando el responsable haya verificado que son admisibles.

4. En otro caso preparado, usar Rechazar con un motivo; en otro, Ignorar elemento con su motivo. No ignorar un error sólo para habilitar el botón de finalizar.

5. Recargar la consulta después de cada decisión y comprobar el estado y el historial. Volver a Ver elementos por resolver y revisar que la lista se actualice. Si se rechazó una propuesta pero quedan otras por revisar, el elemento puede seguir pendiente.

6. Consultar el caso con un error ya ignorado por el responsable: debe conservarse en el historial, pero ya no contarse entre los Errores por resolver.

**Resultado esperado:** cada acción registra su propia decisión y actualiza la consulta. Seleccionar registra una elección, mientras Confirmar incorpora la geometría. Rechazar e Ignorar no deben aparentar una confirmación. Si hay conflicto, se informa y no se anuncia guardado exitoso.

### C12 — Sin coincidencias y nueva conciliación [puede guardar datos]

1. Abrir el caso preparado con algunos elementos sin destino y otros con candidatos. Repetir con un archivo donde todos estén sin coincidencia.

2. Revisar el aviso que indica cuántos elementos están Sin coincidencia. Debe explicar que eso no es, por sí solo, un error de geometría y que esos polígonos todavía no se incorporarán al mapa.

3. Comparar los ejemplos de nombres mostrados con el archivo de prueba. El aviso presenta hasta cinco ejemplos; usar Ver sin coincidencia para consultar la lista completa, avanzando de página cuando haga falta.

4. Revisar la cantidad de Destinos administrativos disponibles. En el caso de parcelas sin registros asociados al proyecto, debe mostrar cero y pedir revisar las parcelas y su relación con los núcleos; no basta con que existan núcleos.

5. Utilizar Revisar registros del proyecto y comprobar que abre la ficha del proyecto correcto.

6. Si está autorizado, resolver el caso preparado: vincular el núcleo adecuado siguiendo C17, completar la relación de la parcela o corregir el dato que haya validado el responsable. No cambiar nombres a ciegas ni crear duplicados para forzar una coincidencia.

7. Volver a la importación y pulsar Nueva conciliación. Escribir un motivo reconocible; usar las opciones de volver a revisar ambigüedades o destinos rechazados sólo según el caso acordado.

8. Guardar, revisar el resultado y abrir Historial de conciliaciones.

**Resultado esperado:** el aviso aparece aunque sólo una parte del archivo esté sin coincidencia. La nueva comparación usa los registros actuales y conserva el historial anterior. Si siguen faltando datos para coincidir, el sistema debe indicarlo. Cargar o finalizar un archivo no crea por su cuenta los núcleos o parcelas que faltan.

### C13 — Actores y destinos en los historiales

1. Abrir Historial de decisiones y Ver ciclo en una conciliación preparada.

2. Comparar acción, motivo, fecha y persona con la referencia de QA.

3. Buscar un elemento conocido y comprobar que se muestra su número y nombre, iguales a los de la lista principal. No debe cambiar de número porque esté en otra posición dentro del ciclo.

4. Si el caso incluye un elemento cuyo nombre ya no está disponible, comprobar que la pantalla lo indique sin inventar uno. El identificador que aparezca sirve para reportarlo a soporte.

5. Revisar un caso realizado por un usuario que posteriormente fue dado de baja y otro histórico sin nombre de usuario disponible, si fueron preparados.

6. Abrir una revisión asociada a una parcela y comprobar que el nombre del núcleo y la parcela coinciden con el destino conocido.

**Resultado esperado:** los elementos se reconocen por su número y nombre cuando están disponibles. Un actor inactivo conserva su nombre cuando existe en el historial. Si falta, aparece una indicación como Nombre de usuario no disponible. No dar de baja cuentas reales para fabricar este caso.

### C14 — Finalizar y comprobar la publicación [guarda datos]

**Preparación:** usar casos separados de núcleos/parcelas con pendientes, otro sin pendientes y uno de DDV. Pedir ayuda a soporte para la interrupción de consulta y el conflicto entre revisiones; si no están preparados, anotarlos como No ejecutados.

1. En una importación de núcleos o parcelas con candidatos pendientes, ir a Finalizar. El botón Finalizar conciliación debe estar deshabilitado y debe verse cuántos elementos faltan por resolver y cuántos tienen errores. No hace falta provocar un error en la consola para aprobar esta parte.

2. Pulsar Ver elementos por resolver y, si aparece, Ver errores por resolver. Comprobar que cada acceso muestra las filas correspondientes. Seleccionar un candidato sin confirmarlo no debe eliminarlo de los pendientes.

3. Repetir con el caso cuyo único pendiente está en otra página. El cierre debe seguir bloqueado aunque en la página que estás viendo no haya ningún problema.

4. Resolver únicamente los casos acordados en C11 y pulsar Actualizar estado. Cuando ya no queden decisiones ni errores pendientes, el botón debe habilitarse. Los errores ya ignorados no deben seguir bloqueando por su cuenta.

5. En el caso que sólo tiene elementos Sin coincidencia y ninguna otra causa de bloqueo, comprobar que se permite finalizar y que se advierte que esos elementos no se incorporarán al mapa. Ojo: esto no significa que los polígonos hayan quedado asociados correctamente.

6. Abrir Finalizar conciliación. Revisar las cantidades de elementos confirmados y sin coincidencia que muestra el formulario antes de marcar que se revisaron los resultados. Guardar sólo si el caso lo autoriza.

7. Con soporte, interrumpir la consulta del estado. Debe quedar bloqueada la finalización y verse un aviso de que no pudo verificarse la carga. Recuperar la consulta y pulsar Actualizar estado; debe volver a mostrar la situación real.

8. En el conflicto preparado por soporte, comprobar que el mensaje del servidor se pueda leer dentro del formulario y que no se anuncie un guardado exitoso. Registrar el mensaje completo, sin intentar resolverlo ignorando elementos por cuenta propia.

9. Para DDV válido y sin errores, comprobar que Confirmar versión de DDV se permite después de consultar su estado. No debe exigir candidatos de núcleos o parcelas. Confirmar sólo en el caso autorizado.

10. Abrir de nuevo una importación que ya está completa. La pantalla debe indicar que ya no está pendiente de finalización y no ofrecer repetir esa confirmación.

11. Abrir el mapa normal del proyecto, sin el enlace de previsualización, y recargarlo. Comprobar que las geometrías confirmadas aparecen en su capa; los elementos que siguen sin coincidencia no deben aparecer como si acabaran de confirmarse. Si ya había una versión vigente anterior, compararla con lo que QA indicó que debía conservarse.

12. Para un caso autorizado con segunda versión, comprobar que se muestra la vigente esperada. Comparar las superficies administrativas anotadas al inicio: no deben cambiar por cargar o dibujar un polígono.

13. En el proyecto histórico preparado, comprobar que siguen consultándose sus geometrías anteriores cuando el servidor las considera vigentes, sin editar esas geometrías.

**Resultado esperado:** el cierre sólo se habilita cuando se pudo comprobar el estado y no hay pendientes bloqueantes. Confirmar un elemento incorpora su geometría; finalizar cierra la revisión, pero no confirma por su cuenta lo que quedó sin coincidencia ni crea registros administrativos. Un archivo completo puede tener elementos que no se incorporaron, y la pantalla debe dejarlo claro.

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

Aplicar esta prueba por separado a importaciones, elementos, historial de conciliaciones y revisiones. El responsable debe preparar las cantidades y decir cuál lista corresponde a cada caso.

| Cantidad preparada | Comprobación esperada |
|---|---|
| 0 | Mensaje sin registros y sin poder avanzar a páginas ficticias. |
| 25 | Una página completa; Siguiente deshabilitado. |
| 26 | Primera página con 25; segunda con 1; Siguiente deshabilitado al final. |
| 51 | Páginas con 25, 25 y 1; Anterior permite volver sin perder registros. |

1. Anotar el rango visible y el total en la primera página.

2. Avanzar y retroceder; comparar primero/último registro para detectar repeticiones o saltos inesperados.

3. En elementos, aplicar un filtro que reduzca el total. Repetir con Por resolver antes de finalizar, Errores por resolver y Sin coincidencia. En revisiones, combinar sus filtros.

4. Comprobar que el total cambie al de los resultados filtrados y que una búsqueda nueva empiece desde la primera página.

5. Cambiar de proyecto y revisar que no queden rango, filas o botones de la lista anterior.

6. Si se preparó el ejemplo con más de 500 elementos, comprobar también que el pendiente posterior al elemento 500 aparezca en el filtro y mantenga bloqueada la finalización, aunque la primera página no tenga errores.

**Resultado esperado:** no se exige una página extra vacía para descubrir que terminó una lista de exactamente 25. El total del archivo no reemplaza al total filtrado. Si no se prepararon suficientes registros para una lista, dejar esa parte como No ejecutada.

## 4. Catálogo RAN y vinculación al proyecto

**Cómo llegar.** En la ficha de un proyecto, abrir Agregar núcleo agrario con la cuenta autorizada.

**Qué debe verse.** Un campo para el nombre del núcleo, filtros de Entidad y Municipio, un botón "Buscar en catálogo RAN", un selector para elegir el núcleo que encontró el catálogo, y algo que te diga cuántos resultados hay. También hay una casilla aparte, "No aparece en el catálogo: crear núcleo nuevo" — esto es para el caso excepcional en que el núcleo de verdad no esté en el catálogo oficial; no debe mezclarse con el flujo normal de buscar y elegir uno que ya existe.

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

7. Cierre del bloque

8. Registrar C01–C18 y cada subcaso de paginación. Adjuntar capturas con nombre del proyecto, control de capas, detalle, filtros y total visible. Para cargas, anotar nombre del archivo, tipo elegido, fecha/hora y motivo de cada decisión. Distinguir las pruebas que sólo consultaron de las que confirmaron información.

9. No exigir en este cierre cálculos oficiales nuevos de superficie, configuración nueva de mapas base o estados de proyecto que todavía no existan. Si surge una falla, describir lo observado y lo esperado; el equipo técnico determinará si se origina en pantalla o servidor.

## Aclaraciones para las pruebas del historial

Consultar carga abre su detalle; no reactiva el archivo. La cantidad de elementos confirmados en una carga no asegura que todos sigan siendo los vigentes. Por ahora no hay botones para eliminar una entrega ni restaurar una anterior: estas funciones requieren soporte adicional del servidor. No marques como fallo que no aparezcan esos botones todavía.

El DDV es un polígono que representa la franja de terreno y el trazo es una línea del recorrido. Trazo del proyecto se retiró del formulario de nuevas cargas; los trazos anteriores sólo conservan su consulta en el historial de importaciones. Prueba que, al elegir Núcleos con un archivo cuyo nombre indica Parcelas, aparezca una advertencia y que Cancelar no envíe la carga. Es una ayuda basada en el nombre, no una comprobación de todo el contenido.

Revisiones geoespaciales sirve para dar seguimiento a diferencias entre entregas y cambios respecto al DDV. Leer o marcar esas revisiones no activa una versión histórica del mapa. Comprueba que esa explicación esté visible.

## Cierre del bloque

Anota el resultado de C01–C18 y de cada caso adicional que sí pudiste probar. Si faltaron archivos, permisos o datos preparados, deja esa parte como No ejecutada. Adjunta capturas donde se vea el proyecto, el archivo, el tipo de información elegido, los filtros y las cantidades. Para cada decisión guardada, anota cuál fue y por qué se tomó.

En especial, guarda evidencia del botón de finalizar deshabilitado con pendientes, la lista Por resolver antes de finalizar, el aviso Sin coincidencia, los nombres en Ver ciclo y el cierre habilitado cuando ya corresponde. Distingue las pruebas de consulta de las que confirmaron información. No tomes este manual como una lista de pruebas ya aprobadas: el resultado lo registra quien las ejecute.

Si algo falla, escribe qué hiciste, qué esperabas y qué ocurrió. No cambies datos administrativos ni ignores errores sólo para que el caso aparezca aprobado.


## Recorrido actualizado — historial, nueva carga y confirmación conjunta (12 de octubre)

Este recorrido corresponde a los últimos cambios de Gestión geoespacial. Hazlo en México–Querétaro con los casos que te entregue QA. Para guardar decisiones utiliza datos de prueba autorizados. Obras transversales queda fuera de esta ronda.

### G01 — Entrar y reconocer la pantalla

Al ingresar se muestra la ayuda «¿Cómo cargo los archivos?». Debajo aparece Gestión geoespacial, el título Importación de información geográfica y los botones Crear una importación y Ver mapa. Después está la tarjeta para elegir proyecto, los cuatro pasos y el sistema de coordenadas actual. Más abajo están el historial y las revisiones geoespaciales.

Tareas a realizar:

- Selecciona México–Querétaro y comprueba que el historial corresponda a ese proyecto.
- Lee el sistema de coordenadas. Debe mostrar la configuración guardada; no tiene que decir siempre EPSG:4326. No lo cambies para quitar una alerta.
- Comprueba que el paso actual se distinga por el texto verde, sin el rectángulo que rodeaba todo el paso. El foco al navegar con el teclado sí debe seguir siendo visible.
- Revisa que el historial aproveche el ancho cuando el formulario esté cerrado. El nombre, tipo, fecha, alcance, estado y cantidades deben leerse sin encimarse.
- Abre Crear una importación. El formulario debe aparecer a la izquierda y el historial a la derecha. En una pantalla angosta se acomodan uno debajo del otro.

Resultado esperado: se identifica el proyecto, el paso actual y cada carga sin interpretar que algo está roto por su apariencia.

### G02 — Consultar una carga y empezar otra

Cada tarjeta del historial tiene Consultar carga. Al pulsarlo, la pantalla debe bajar hasta la información del archivo elegido. Consultar no activa una versión antigua ni reemplaza las geometrías del mapa.

Tareas a realizar:

- Consulta una carga de parcelas. Comprueba que la pantalla se desplace al detalle y que el título muestre ese archivo.
- Consulta después una de núcleos. Debe verse la información de núcleos, sin conservar debajo la conciliación de parcelas.
- Con una conciliación abierta, pulsa Crear una importación. Deben desaparecer la consulta y la previsualización anterior; el historial permanece.
- Prepara otro archivo autorizado y comprueba que sólo aparezca su resultado.
- Si QA dispone de una carga antigua de trazo, consúltala y después consulta una de núcleos. No deben quedar dos paneles de archivos distintos abiertos.
- Si una consulta tarda, pulsa Crear una importación antes de que termine. La respuesta anterior no debe volver a abrirse sobre el formulario nuevo.
- Cierra el formulario: el historial debe volver a ocupar el ancho disponible.

Resultado esperado: se trabaja una carga a la vez. Limpiar la vista no elimina archivos ni decisiones del historial.

### G03 — Elegir qué se va a cargar

El formulario ofrece Derecho de vía (DDV), Núcleos agrarios y Parcelas. Trazo del proyecto ya no aparece para nuevas importaciones. El DDV representa la franja de terreno del proyecto; un trazo es la línea del recorrido. Se conserva la consulta de los trazos anteriores en el historial de importaciones; no se dibujan en el mapa.

Tareas a realizar:

- Abre la lista y verifica esas tres opciones.
- Elige el tipo correcto del archivo preparado. Para núcleos y parcelas, selecciona Parcial o Completa conforme a la entrega, no para intentar corregir coincidencias.
- Si aparece «El mismo archivo ya fue procesado con otro alcance», consulta la carga ofrecida. No debe enviarse otra carga automáticamente ni cambiarse tu selección.
- Comprueba que un archivo sin coincidencias muestre la orientación para revisar nombres y registros del proyecto. Un polígono válido no garantiza que ya tenga su registro administrativo asociado.

Resultado esperado: la pantalla diferencia el tipo de archivo, su alcance y las coincidencias pendientes.

### G04 — Confirmar todas las coincidencias como administrador [guarda decisiones]

Con una cuenta de administrador y una carga pendiente que tenga propuestas, aparece Confirmar todas las coincidencias. Sirve para aceptar juntas las asociaciones que tienen un solo destino disponible. No crea núcleos ni parcelas y no confirma los elementos sin coincidencia, ambiguos, con errores o cuyas propuestas comparten destino.

Tareas a realizar:

- Abre el caso preparado y anota cuántos elementos están confirmados antes de empezar.
- Pulsa Confirmar todas las coincidencias. Debe abrirse una advertencia con el archivo, proyecto, cantidad que se confirmará y aviso sobre reparaciones o reemplazos. También explica que, si falla una decisión, las anteriores se conservan.
- Primero pulsa Cancelar. No debe aumentar el número de confirmados.
- Repite y acepta únicamente en el caso de prueba autorizado. Debe mostrarse el avance y un resultado con cuántas asociaciones se confirmaron.
- Comprueba que no se pueda cambiar de proyecto, consultar otra carga o iniciar una nueva mientras se guardan las decisiones.
- Revisa los elementos sin coincidencia y con varias propuestas: deben conservar su condición. No debe anunciarse que todos los polígonos se confirmaron si había excepciones.
- Con ayuda de QA, prueba una interrupción después de una decisión exitosa. El proceso debe detenerse, indicar el problema y conservar lo guardado. Actualiza el estado antes de reintentar; con una pérdida de conexión, el último envío podría haberse guardado aunque no llegara la respuesta.
- Vuelve a abrir una carga con algunas decisiones ya confirmadas. El botón sólo debe considerar las que siguen pendientes.
- Entra con geógrafo: no debe aparecer este botón conjunto. Sus acciones individuales autorizadas siguen disponibles. Repite con los otros roles: tampoco deben tener el botón conjunto.

Resultado esperado: sólo el administrador tiene el acceso conjunto en la interfaz, siempre con advertencia. La confirmación no finaliza automáticamente la conciliación: revisa lo restante y después usa Finalizar conciliación cuando corresponda.

### G05 — Entender y probar Revisiones geoespaciales

Esta sección es una lista de cambios detectados entre entregas, para que alguien les dé seguimiento. Por ejemplo, al ampliar el derecho de vía, una parcela puede pasar a quedar dentro de él. También puede cambiar un polígono, aparecer uno nuevo o dejar de venir uno que estaba antes. Aquí se consulta esa diferencia y se deja constancia de su revisión. No es otra carga de archivos ni un botón para recuperar una versión anterior.

Tareas a realizar:

- Lee la explicación de la sección. Los filtros Estado, Capa y Tipo de cambio deben aparecer separados y con espacio suficiente.
- Selecciona Todos en Estado y Todas en Capa. Prueba cada tipo de cambio con los ejemplos preparados por QA.
- Abre una revisión conocida y compara el destino, la diferencia y las superficies con el caso preparado.
- Si tienes autorización para resolver ese caso, prueba Marcar como revisado, No aplica o Aplicado según corresponda. Escribe el motivo solicitado y comprueba el historial de decisiones. No selecciones Aplicado sólo para cambiar lo que se ve en el mapa.
- Si no existen revisiones con esos filtros, debe indicarlo. No necesitas llenar esta sección para subir un archivo. Una lista vacía no acredita la prueba de una revisión con datos: anota ese caso como No ejecutado.

Resultado esperado: se entiende qué cambió y quién le dio seguimiento, sin confundirlo con activar o eliminar importaciones.

### Evidencia que debe entregar el tester

Anota cada caso G01–G05 como Aprobado, Falló o No ejecutado. Incluye capturas del historial, formulario con historial a la derecha, detalle al consultar, advertencia conjunta, resultado y ausencia del botón para geógrafo. Registra proyecto, archivo, rol, fecha, cantidades antes/después y el mensaje exacto de cualquier problema. Nunca incluyas contraseñas.

Nota para la revisión técnica: la restricción exclusiva de administrador para el botón conjunto está aplicada en frontend. Las decisiones usan los servicios individuales existentes, que también permiten decisiones de geógrafos. Una prohibición de operaciones masivas impuesta por el servidor queda pendiente de evaluación del backend; no se modificaron sus archivos ni sus endpoints en esta ronda.


### G06 — Botón conjunto visible y mensajes de ayuda

Al consultar una carga pendiente como administrador, arriba de la lista de elementos debe verse Confirmación conjunta · Sólo administrador y su botón. No hace falta bajar hasta Finalizar para encontrarlo.

- Abre la advertencia. Revisa cantidad y archivo, la lista de polígonos sin coincidencia y los otros elementos excluidos. Los nombres deben corresponder a esa carga.
- Lee los riesgos: asociación incorrecta, reemplazo de geometrías, reparaciones, guardado parcial e interrupción. Cancelar no guarda ninguna decisión.
- Comprueba que los ya confirmados o ignorados no se vuelvan a confirmar por esta acción.
- Si un elemento dice Ignorado, abre Revisar elemento y lee su Historial de decisiones. Debe indicar motivo, fecha y responsable disponibles. No lo interpretes como error de coordenadas.
- Consulta el ejemplo de parcelas registrado como Núcleos agrarios. Debe aparecer una advertencia para revisar el tipo y no confirmar ahí si es incorrecto.
- En un caso preparado con propuesta antigua, comprueba que «La geometría cambió» explique por qué el checkbox no basta. Si el tipo es correcto, una Nueva conciliación permite obtener propuestas actuales para volver a revisarlas; no debe ejecutarse por su cuenta.
- En el mapa, cada control de capa debe mostrar un tren iluminado al activarse y apagado al desactivarse. Comprueba también la operación con Tab y la barra espaciadora.

Resultado esperado: las advertencias explican qué se va a guardar y qué queda fuera, sin saltarse las verificaciones del servidor.


### G07 — Diagnóstico, valores originales y filtros del historial

Al consultar una carga con elementos sin coincidencia, el aviso muestra cuántos son respecto del total. Si superan el 85 %, orienta a revisar registros, vínculos y formato de campos clave; si no, orienta a revisar los casos concretos. Esto es una ayuda de diagnóstico, no una causa confirmada.

- Prueba un caso con pocos elementos sin destino y otro con más del 85 %. Comprueba que cambie la orientación y que el porcentaje use el total del archivo, no sólo la página visible.
- En la tabla y en Ver sin coincidencia, compara núcleo, municipio, entidad y parcela con el archivo original. Deben conservarse los ceros del número de parcela y mostrarse los nombres de las columnas. Un campo ausente dice No informado; uno vacío dice Vacío.
- El aviso no debe asegurar que un campo concreto causó el problema cuando el servidor no lo informó.
- Distingue el azul y el ícono informativo de Sin coincidencia administrativa frente al rojo y la marca de Error de geometría o datos. Compruébalo también en la advertencia conjunta, el detalle del mapa y las cargas históricas.
- En el historial, combina estado, tipo, Desde y Hasta. Las fechas corresponden a la hora local del navegador. Usa un caso situado después de la primera página para comprobar que también se encuentre.
- Invierte Desde y Hasta: debe pedir corregir el intervalo. Pulsa Limpiar filtros y comprueba que vuelvan las cargas disponibles.
- Simula una consulta fallida con ayuda de QA. No debe mostrarse una parte del historial como si fuera el total. Actualizar importaciones debe permitir reintentar.
- Confirma que Disponibilidad informa Activas (únicas disponibles). Las inactivas y la baja con motivo están pendientes del backend; no esperes botones que aparenten funcionar.
- Verifica que desapareció el campo manual de columna identificadora. DDV, núcleos y parcelas conservan su flujo actual de carga.
- Recorre filtros y paginación con Tab. Los controles deben conservar nombres comprensibles y foco visible, también después de pasar de página.

Resultado esperado: se puede investigar la falta de asociaciones sin confundirla con una carga fallida, y filtrar el historial completo disponible sin perder registros por paginación.


### G08 — Listado emergente sin coincidencia (13 de octubre de 2026)

En el resumen de la carga, pulsa Ver elementos sin coincidencia. Se abre una ventana con el archivo, el proyecto y la cantidad de núcleos o parcelas sin asociación. Puedes cerrarla sin perder la conciliación; Filtrar tabla sin coincidencia conserva el acceso al filtro de la tabla principal.

- Comprueba que cada fila tenga un identificador, los valores originales y una explicación comprensible. Sin nombre o número debe usar la posición en el archivo y el folio cuando esté disponible.
- Si un campo reconocido llegó vacío, debe indicarlo. Si no fue identificado entre las columnas recibidas, debe decirlo sin asegurar que ese fue el motivo exacto del rechazo. Municipio o entidad distintos requieren evidencia del servidor: no se deben inventar.
- En un caso grande, busca una parcela que esté después del elemento 500. Usa también municipio, entidad, folio y palabras del motivo. Comprueba la cantidad y la paginación de 25 filas.
- Exporta con un filtro: el CSV debe incluir todos los resultados del filtro, no sólo la página visible. Limpia la búsqueda y exporta el listado completo. Con cero resultados, la exportación debe estar deshabilitada.
- Compara acentos, números con ceros, comillas y comas con el archivo CSV. Los textos que pudieran interpretarse como fórmulas deben exportarse como texto seguro. Si Excel cambia el formato de un número al abrirlo, impórtalo como columna de texto para conservar sus ceros.
- Comprueba que los errores de geometría, confirmados e ignorados no se incluyan en este listado.
- Usa Tab y Shift+Tab: el foco permanece en la ventana. Escape debe cerrarla y devolver el foco al botón que la abrió. La tabla y el filtro principal deben seguir como estaban.
- En móvil, comprueba búsqueda, cierre y desplazamiento del listado para leer todas las columnas. El modal no debe salir del ancho de la pantalla.

Resultado esperado: el geógrafo puede encontrar y compartir los elementos pendientes sin transcribirlos, sin confirmar nada y sin confundirlos con errores de carga.


### C19 — Cabecera, detalle y ampliación del mapa (13 de octubre de 2026)

Al entrar al mapa, el selector es una acción principal dentro de Consulta geoespacial. Sin proyecto, su etiqueta dice Selecciona un proyecto; al elegirlo cambia a Proyecto seleccionado. En esa misma tarjeta aparecen Ver información general y Gestionar cartografía. Ya no hay una tarjeta separada con el nombre del proyecto ni el aviso general de capas que estaba arriba.

- Selecciona un núcleo: al final del detalle debe aparecer Información del responsable, con Nombre, Cargo y Contacto. Los valores ausentes dicen No registrado.
- Pulsa otra vez ese núcleo: debe quedar desmarcado, desaparecer su detalle y restaurarse los colores del resto. Prueba también Quitar selección y pulsaciones rápidas mientras se consulta el detalle.
- Pulsa Ampliar mapa: el menú lateral se colapsa, el mapa ocupa la ventana, las capas quedan dentro a la izquierda y el detalle queda minimizado a la derecha. Las capas muestran sólo sus nombres en esta vista, sin los íconos ni el tren.
- Activa y desactiva capas en la vista ampliada. Abre Mostrar detalle y vuelve a minimizarlo. Al pulsar Reducir mapa o Escape se recupera la distribución anterior y el estado previo del menú lateral.
- Repite con teclado y en móvil. Comprueba foco visible, navegación dentro del visor ampliado y acceso al botón para salir.
- El Resumen cartográfico sustituye al listado de archivos: cuenta núcleos y parcelas con geometría confirmada vigente e indica si hay DDV. No suma importaciones repetidas y no cambia al ocultar una capa.
- El Resumen del proyecto agrupa ocho indicadores en una tarjeta: superficie administrativa, núcleos, parcelas, afectaciones, asambleas realizadas, convenios individuales firmados, convenios colectivos firmados y convenios firmados totales.
- Las asambleas se cuentan una vez por registro activo con convocatoria activa celebrada y fecha de realización, de todos los tipos y años. Varias convocatorias de una misma asamblea no la duplican.
- Los convenios se cuentan una vez por identificador activo con fecha de firma y se separan por ámbito. Un convenio sin firma no cuenta como firmado.
- Simula fallos de consulta: los nuevos indicadores deben decir No disponible, sin inventar un cero ni impedir consultar el mapa. Cambiar de proyecto debe descartar respuestas atrasadas.

Resultado esperado: el mapa permite presentar los datos esenciales y explorar sin quedar atrapado en una selección. Las cifras cartográficas y administrativas quedan claramente diferenciadas.
