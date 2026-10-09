# Manual 2 — Personas, ORV, documentos y actividades

**Fecha:** 9 de octubre de 2026. **Alcance:** cambios del cierre frontend del 8 de octubre y comprobaciones de navegación que permiten usarlos.

Este manual describe lo que se debe comprobar; no significa que el tester ya lo haya aprobado. Trabajar en el entorno de pruebas `http://127.0.0.1:5184`. Los nombres y cantidades dependen de los registros preparados para la prueba. No hay que obtener necesariamente los mismos números de las capturas anteriores.

En cada caso registrar **Aprobado**, **Falló** o **No ejecutado**. Si falta una cuenta, un archivo o un registro, marcar No ejecutado y explicar qué falta; no marcar Aprobado por no encontrar información. Las acciones que guardan, dan de baja, reactivan o confirman se realizan solamente en registros de prueba identificados por el responsable de QA.

## Qué preparar antes de comenzar

Solicitar un proyecto y un núcleo exclusivamente de prueba. Debe haber una persona conocida con nombre acentuado, CURP y RFC; un nombre con más de 20 coincidencias autorizadas si se va a probar paginación; un órgano de representación con integrantes vigentes, participaciones finalizadas y bajas administrativas; y una actividad de campo.

Para documentos, preparar un PDF o imagen inocua, un documento sin archivo, un documento con dos versiones, uno relacionado con dos registros, uno antiguo con tipo escrito libremente y uno con tipo histórico que ya no se ofrece para registros nuevos. El responsable debe identificar cada caso por un nombre reconocible. Si falta un ejemplo, dejar ese caso como No ejecutado.

Usar operador o administrador para captura. Usar administrador para baja/reactivación administrativa de integrantes. Repetir consulta con visualizador y geógrafo.

## 1. Buscar y seleccionar una persona

**Cómo llegar.** Abrir el proyecto y su núcleo. Entrar a ORV, elegir un órgano e iniciar el formulario para agregar integrante; usar Buscar persona. También puede probarse el selector desde los formularios existentes de comparecientes o intervinientes que lo ofrezcan.

**Qué debe verse.** Una ventana Buscar persona existente, un selector Buscar por con Nombre, CURP y RFC; un campo para escribir; Buscar; Ver directorio de este núcleo; una lista para elegir persona; Anterior y Siguiente; y Cancelar/Seleccionar. Registrar persona nueva sólo debe ofrecerse a cuentas de captura. Los resultados deben permitir reconocer a la persona por nombre, CURP y RFC, sin pedir que el tester copie un número interno.

### B01 — Buscar por nombre y conservar acentos

1. Elegir Nombre y escribir el nombre conocido, incluyendo su acento, por ejemplo José si ese es el dato preparado.
2. Presionar Buscar y comparar los resultados con la persona esperada.
3. Hacer una búsqueda con un solo carácter y después con el campo vacío.
4. Volver a escribir al menos dos caracteres y buscar.
5. Si se preparó una persona cuyo nombre contiene %, guion bajo o barra invertida, buscar ese texto exacto. Si no existe ese caso, no inventar un resultado esperado.

**Resultado esperado:** los acentos se conservan; el sistema pide un criterio válido para un nombre demasiado corto o vacío. Los caracteres especiales se tratan como parte del texto, no como una orden para mostrar a todas las personas. No se promete búsqueda aproximada de errores ortográficos.

### B02 — Buscar por CURP y RFC

1. Cambiar Buscar por a CURP; escribir la CURP de prueba o la parte admitida del criterio y presionar Buscar.
2. Comprobar que no obliga a completar 18 caracteres sólo para ejecutar una búsqueda y que el campo no admite más de 18.
3. Cambiar a RFC; buscar el RFC preparado y comprobar el límite de 13 caracteres.
4. Si hay dos personas con el mismo RFC, revisar que puedan distinguirse por nombre y demás datos disponibles.

**Resultado esperado:** se usa un criterio a la vez. Cambiar de criterio no conserva una selección anterior como si perteneciera a los nuevos resultados. Un RFC no se considera identificación única; nunca elegir automáticamente una persona sólo porque fue la primera coincidencia.

### B03 — Recorrer resultados y cambiar de búsqueda

1. Usar el nombre preparado con más de 20 coincidencias.
2. Anotar la primera y última persona de la página; presionar Siguiente.
3. Comprobar que cambia la página y usar Anterior para regresar.
4. Cambiar el texto por otra búsqueda y pulsar Buscar.
5. Hacer dos búsquedas seguidas con textos distintos y comprobar que al final se muestran los resultados de la última.

**Resultado esperado:** la búsqueda nueva comienza desde el inicio y no conserva una persona seleccionada de la anterior. No exigir un total global que la pantalla no ofrece. Si una última página tiene exactamente 20 resultados, puede requerirse avanzar para descubrir que no hay más; no confundir esto con las listas geoespaciales, que sí disponen de total.

### B04 — Sin resultados y directorio del núcleo

1. Buscar un texto preparado que no tenga coincidencias autorizadas.
2. Leer el mensaje completo.
3. Pulsar Ver directorio de este núcleo y revisar la lista contextual.
4. Compararla con personas relacionadas con ese núcleo; no compararla como si fuera todo el padrón del sistema.

**Resultado esperado:** el mensaje aclara que no hay coincidencias que esa cuenta pueda consultar; no afirma que la persona no exista en todo el sistema. El directorio se presenta como información del núcleo. Una consulta incompleta debe avisarse, no aparecer como una lista completa.

### B05 — Seleccionar no equivale a guardar una relación

1. Buscar a la persona de prueba, elegirla y pulsar Seleccionar.
2. Comprobar que vuelve al formulario de integrante con esa persona visible.
3. Cancelar el formulario sin guardar.
4. Recargar ORV y comprobar que no se agregó una participación.
5. Repetir desde un formulario de compareciente o interviniente disponible, también cancelando antes de guardar.

**Resultado esperado:** seleccionar sólo rellena el formulario. No crea un integrante, compareciente o interviniente hasta guardar la operación correspondiente.

### B06 — Persona nueva y posible duplicado [guarda datos]

1. Buscar primero la identidad preparada para evitar duplicarla.
2. Con operador o administrador, elegir Registrar persona nueva y llenar los datos de una persona ficticia autorizada por QA.
3. Guardar, comprobar que queda disponible para selección y anotar su nombre de prueba.
4. Buscarla de nuevo desde un flujo donde esa cuenta tenga acceso a ella.
5. Con un caso de duplicado acordado, intentar registrar la misma identidad que el servidor ya reconoce.

**Resultado esperado:** un alta correcta se informa y puede seleccionarse; todavía no crea una relación con ORV u otro registro por sí sola. Ante identidad duplicada se orienta a buscarla o revisar acceso con administración, no a seguir creando copias. Repetir con visualizador/geógrafo: no deben tener Registrar persona nueva.

## 2. Órganos de representación y sus integrantes

**Qué debe verse.** La pantalla permite elegir un órgano y consultar sus integrantes. Cada integrante presenta nombre, órgano, cargo, calidad, fechas de participación y estado. Hay dos casillas: Incluir participaciones finalizadas e Incluir bajas administrativas. Una baja debe informar fecha y motivo cuando se consulta. Las acciones de captura y administración dependen de la cuenta.

### B07 — Comprobar las cuatro combinaciones de filtros

Seleccionar el órgano preparado y probar esta tabla. Antes de cada intento anotar quién debería aparecer según los registros de prueba.

| Participaciones finalizadas | Bajas administrativas | Qué debe incluir la lista |
|---|---|---|
| Desmarcada | Desmarcada | Participaciones vigentes que no estén dadas de baja. |
| Marcada | Desmarcada | Participaciones vigentes y finalizadas, excluyendo bajas administrativas. |
| Desmarcada | Marcada | Participaciones vigentes, incluyendo las que tengan baja administrativa. |
| Marcada | Marcada | Participaciones vigentes y finalizadas, incluyendo bajas administrativas. |

**Resultado esperado:** el cambio de cada casilla actualiza la lista. No dar por hecho que marcar bajas siempre aumentará el número: depende de las fechas de los casos preparados. Una lista vacía con filtros restrictivos puede ser correcta.

### B08 — Conservar filtros y fechas al recargar

1. Marcar ambas casillas y anotar los integrantes mostrados.
2. Presionar F5 y volver a seleccionar el órgano si la pantalla lo solicita.
3. Revisar que las casillas conserven su selección y que los mismos registros sigan disponibles.
4. Revisar fechas de inicio, término y baja: deben ser comprensibles, en día-mes-año.
5. Comprobar que una participación finalizada se identifique como Finalizado y que una baja se identifique como registro dado de baja.

**Resultado esperado:** la información no depende de lo que se hizo antes de recargar. Una baja administrativa y el fin de una participación no deben presentarse como la misma operación.

### B09 — Finalizar participación [guarda datos]

1. Con cuenta de captura, elegir un integrante vigente de prueba y pulsar Finalizar participación.
2. Completar fecha, tipo de fin y los datos que pida el formulario.
3. Guardar; activar Incluir participaciones finalizadas si el integrante deja de aparecer.
4. Revisar estado y fecha final; presionar F5 y consultar nuevamente.

**Resultado esperado:** se conserva la finalización y no se duplica el integrante. Si el servidor rechaza la operación, muestra el motivo y no debe anunciar guardado exitoso. No repetir la operación como forma de resolver un error sin revisar antes el registro.

### B10 — Baja administrativa y reactivación [guarda datos]

1. Como administrador, usar un integrante de prueba acordado para baja y pulsar Eliminar registro.
2. Leer el aviso, escribir un motivo reconocible de QA y confirmar.
3. Activar Incluir bajas administrativas y, si la participación ya terminó, también Incluir participaciones finalizadas.
4. Comprobar fecha y motivo; recargar y volver a consultar.
5. En una participación que ya tenía fecha de término, pulsar Reactivar registro y aceptar.
6. Recargar nuevamente y revisar su estado y fecha de término.

**Resultado esperado:** la baja permanece después de F5. Reactivar restaura el registro administrativo, pero no borra la fecha de término: una participación finalizada debe seguir finalizada. El operador no debe disponer de las acciones administrativas reservadas al administrador.

### B11 — Integrantes utilizados en FIFONAFE

1. Abrir un trámite FIFONAFE del mismo núcleo y llegar al formulario que permite elegir un interviniente procedente de ORV.
2. Consultar los integrantes disponibles del órgano de prueba.
3. Comprobar que pueda usarse el histórico activo preparado, sin incluir como opción válida una baja administrativa.
4. Cancelar el formulario si sólo se está revisando la lista.

**Resultado esperado:** la lista respeta el histórico de participaciones que no están dadas de baja. No hace falta guardar un interviniente para comprobar este caso.

## 3. Documentos del núcleo

**Cómo llegar.** Abrir el núcleo y su acceso Documentos. En las pantallas que lo ofrecen, Documentos de este núcleo abre el gestor; para probar la lista completa, usar la pantalla Documentos.

**Qué debe verse.** El apartado Documentos registrados del núcleo presenta filtros Categoría, Estado y Buscar; Actualizar documentos; un contador y una tabla. La tabla muestra título, tipo, estado, fecha, folio, descripción, registro de origen, versión vigente, archivo y tamaño. Ofrece Ver, Descargar e Historial de versiones. El apartado Registrar y gestionar documentos se despliega cuando se quiere trabajar con registros específicos.

### B12 — Lista consolidada y procedencias

1. Localizar el documento de prueba relacionado con dos registros o con un registro y un requisito.
2. Comprobar que aparece una sola fila y que Registro de origen informa ambas procedencias.
3. Comparar título, fecha, folio, tipo y archivo con los datos preparados.
4. Revisar un documento antiguo: debe conservar su tipo escrito, sin aparecer vacío sólo por no tener clasificación nueva.
5. Revisar uno clasificado: debe mostrar el nombre de su tipo, no únicamente un número.

**Resultado esperado:** documentos agrupados sin perder el origen. Un núcleo realmente sin documentos debe mostrar un mensaje de ausencia de registros, no un error de carga.

### B13 — Filtros combinados

1. Elegir una Categoría conocida, por ejemplo Actividades de campo cuando tenga documentos.
2. Elegir un Estado presente en los datos preparados.
3. Escribir parte del título o folio en Buscar.
4. Comprobar que cada fila cumple los tres criterios y que el contador coincide con lo visible.
5. Usar una combinación sin coincidencias y después quitar los filtros, eligiendo Todas/Todos y borrando el texto.
6. Pulsar Actualizar documentos después de un cambio realizado en otra ventana de prueba.

**Resultado esperado:** filtrar no borra documentos. Al retirar filtros reaparecen los registros correspondientes. Actualizar recupera los cambios guardados; una lista vacía por filtros no debe parecer una falla.

### B14 — Ver, descargar e historial

1. En el PDF o imagen preparado, pulsar Ver. Permitir la nueva pestaña si el navegador la bloquea.
2. Comprobar que abre el archivo correcto; cerrar esa pestaña.
3. Pulsar Descargar y comprobar nombre y contenido del archivo.
4. Abrir Historial de versiones de un documento con dos versiones; comparar numeración y nombres con lo preparado.
5. Comprobar que el listado principal identifica la versión vigente, no una versión vieja.
6. Intentar Ver en el documento sin archivo.

**Resultado esperado:** archivos correctos, historial legible y aviso claro cuando aún no existe archivo. Un formato que no se puede visualizar de forma segura puede descargarse para abrirlo en su aplicación; no debe ejecutarse como contenido de la página.

### B15 — Registrar un documento con el catálogo nuevo [guarda datos]

1. Desplegar Registrar y gestionar documentos.
2. Elegir Tipo de registro y Registro por sus nombres. Confirmar que se está en el destino de prueba correcto.
3. Pulsar Registrar documento y elegir un Tipo de documento de la lista disponible.
4. Seleccionar Estado; llenar título, fecha, folio y descripción según el caso preparado.
5. Guardar y comprobar que aparece en el gestor y en la lista del núcleo.
6. Abrir Versiones y archivos, elegir Subir nueva versión y agregar el archivo de prueba.
7. Volver al listado, actualizar y verificar que se puede consultar el archivo.

**Resultado esperado:** no se piden números internos ni escribir a mano el tipo de un documento nuevo. Guardar los datos del documento y subir su archivo son pasos distintos; comprobar ambos.

### B16 — Tipo Otro y campos obligatorios [guarda datos]

1. Iniciar un documento de prueba, elegir Otro y dejar Descripción vacía.
2. Intentar guardar con los demás campos obligatorios completos.
3. Comprobar que pide descripción y que no se anuncia un alta exitosa.
4. Escribir una descripción concreta y guardar.
5. Probar también omitir el Estado o el Tipo de documento en un alta distinta, cancelándola después de comprobar la validación.

**Resultado esperado:** Otro requiere explicación; los campos obligatorios no se aceptan vacíos. No deben generarse copias por los intentos rechazados.

### B17 — Editar documentos antiguos e inactivos [guarda datos]

1. Abrir Editar en el documento antiguo con tipo libre. Anotar su tipo antes del cambio.
2. Cambiar sólo título o folio, sin elegir nueva clasificación; guardar y recargar.
3. Comprobar que el tipo original se conserva.
4. Repetir en un documento ya clasificado y en el que tiene tipo histórico inactivo.
5. Iniciar un documento nuevo y revisar las opciones de tipo: el inactivo histórico no debe estar disponible para una nueva alta.

**Resultado esperado:** editar otros datos no borra ni cambia la clasificación. El tipo histórico sigue siendo legible aunque ya no pueda elegirse para nuevos documentos.

### B18 — Clasificar o reclasificar expresamente [guarda datos]

1. Abrir Editar en el documento antiguo.
2. Elegir una opción activa en Clasificar o reclasificar con catálogo (opcional), guardar y recargar.
3. Comprobar que ahora muestra ese tipo.
4. Repetir con un documento ya clasificado, cambiándolo expresamente a otro tipo activo. Si se elige Otro, llenar la descripción.
5. Anotar quién hizo el cambio y su hora para localizarlo en Auditoría, caso A12.

**Resultado esperado:** el tipo sólo cambia porque se eligió una nueva clasificación. No debe deducirse automáticamente a partir de palabras del título o del tipo antiguo.

## 4. Documentos desde una actividad

**Qué debe verse.** En Actividades de campo, cada actividad presenta un botón Documentos. Al abrirlo, el gestor debe quedar en Actividades de campo y en la actividad elegida, identificada por tipo, fecha y sus datos descriptivos disponibles.

### B19 — Contexto, registro, vínculo y procedencia [guarda datos]

1. Abrir Actividades de campo y pulsar Documentos en la actividad preparada.
2. Comparar fecha, tipo y resultado del registro seleccionado con la fila desde la que se entró.
3. Registrar un documento de prueba siguiendo B15.
4. Regresar a Documentos del núcleo y comprobar que se incluye con procedencia de actividad.
5. Volver al gestor de la actividad, pulsar Vincular documento existente, elegir tipo de registro de origen, registro y documento por sus nombres; guardar.
6. Comprobar que el documento queda relacionado sin crear una copia independiente. Verificar sus procedencias en el listado completo.
7. Abrir Consultar procedencia. Si el caso incluye registrar procedencia, hacerlo con datos de QA y comprobar que permanece tras recargar; no inventar un archivo de origen real.

**Resultado esperado:** todo corresponde a la actividad elegida. Los selectores permiten reconocer registros sin introducir números internos. La procedencia puede estar vacía si aún no se registró; debe indicarlo claramente.

### B20 — Consulta, falta de permiso y registro no disponible

1. Repetir consulta documental como visualizador y geógrafo.
2. Comprobar que puedan consultar/descargar lo autorizado, sin botones de registrar, editar, vincular o subir documentos reservados a captura.
3. Pedir al responsable un enlace de un registro fuera del alcance de la cuenta o que ya no esté disponible; abrirlo.
4. Revisar el aviso y regresar a un registro autorizado.
5. Repetir la ventana documental de actividad en pantalla angosta: abrir, desplazarse, usar los botones y cerrar.

**Resultado esperado:** mensajes comprensibles ante falta de permiso o registro no disponible; no se muestran datos de otro registro como sustitución. La ventana no queda bloqueada y sus botones siguen alcanzables.

## Cierre del bloque

Registrar B01–B20; incluir el nombre del núcleo, órgano, actividad y documentos usados. Guardar capturas antes y después de los cambios, sin datos personales innecesarios. Anotar los registros ficticios creados para que el responsable decida su conservación o limpieza; no eliminarlos indiscriminadamente.
