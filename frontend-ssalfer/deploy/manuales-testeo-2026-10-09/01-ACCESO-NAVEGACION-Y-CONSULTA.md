# Manual 1 — Acceso, navegación y consulta general

**Fecha:** 9 de octubre de 2026. **Alcance:** cambios del cierre frontend del 8 de octubre y comprobaciones de navegación que permiten usarlos.

Este manual describe lo que se debe comprobar; no significa que el tester ya lo haya aprobado. Trabajar en el entorno de pruebas `http://127.0.0.1:5184`. Los nombres y cantidades dependen de los registros preparados para la prueba. No hay que obtener necesariamente los mismos números de las capturas anteriores.

En cada caso registrar **Aprobado**, **Falló** o **No ejecutado**. Si falta una cuenta, un archivo o un registro, marcar No ejecutado y explicar qué falta; no marcar Aprobado por no encontrar información. Las acciones que guardan, dan de baja, reactivan o confirman se realizan solamente en registros de prueba identificados por el responsable de QA.

## Qué preparar antes de comenzar

Solicitar cuentas de administrador, operador, visualizador y geógrafo; no compartir contraseñas en el reporte. El responsable debe indicar qué proyectos puede consultar cada cuenta. Preparar dos proyectos identificables por nombre, uno con información y otro sin datos o con pocos registros. Anotar los valores de referencia que se esperan en sus resúmenes.

Abrir primero una ventana normal y después una ventana privada del navegador. La privada servirá para comprobar el acceso sin sesión. En el equipo de pruebas deben estar disponibles Excel o una aplicación que abra archivos de Excel.

## 1. Inicio de sesión y acceso directo a pantallas

**Qué debe verse.** Sin sesión, el sistema debe mostrar la pantalla de acceso, con correo, contraseña, botón Iniciar sesión y un espacio para avisos. Una pantalla privada, como ORV, no debe mostrar datos antes de comprobar quién está entrando. Al entrar desde la pantalla de acceso habitual se abre el dashboard; al llegar desde un enlace privado, se debe regresar a ese enlace después de iniciar sesión.

### A01 — Entrar normalmente

1. Abrir `http://127.0.0.1:5184/Index.html` sin sesión activa.
2. Presionar Iniciar sesión sin escribir correo ni contraseña.
3. Comprobar que pide los datos y permanece en la pantalla de acceso.
4. Escribir una vez una contraseña incorrecta para una cuenta de prueba y comprobar que aparece un aviso. No insistir repetidamente para evitar bloquearla.
5. Ingresar con las credenciales correctas.

**Resultado esperado:** se abre el dashboard, aparece el nombre de la persona que ingresó y no aparecen errores ni ventanas vacías.

### A02 — Pegar directamente un enlace privado, especialmente ORV

1. Con sesión activa, abrir un proyecto, uno de sus núcleos y su pantalla de ORV. Copiar la dirección completa del navegador.
2. Pegar esa dirección en una ventana privada sin sesión.
3. Observar la pantalla desde el momento en que comienza a cargar.
4. Iniciar sesión con una cuenta que tenga acceso a ese proyecto.
5. Repetir con enlaces copiados de Documentos, Mapa y Gestión geoespacial; incluir Usuarios y Auditoría con la cuenta administradora.

**Resultado esperado:** primero pide inicio de sesión; no debe mostrar nombres de integrantes ni datos del proyecto durante la espera. Después del acceso debe abrir la pantalla solicitada con el mismo proyecto o núcleo. No inventar números en las direcciones: utilizar enlaces copiados de registros existentes.

### A03 — Cerrar sesión y usar Atrás

1. Desde una pantalla privada, abrir el menú del nombre de usuario y elegir Cerrar sesión.
2. Comprobar que vuelve al acceso.
3. Presionar Atrás y después recargar con F5.
4. Pegar nuevamente el enlace privado copiado en A02.

**Resultado esperado:** no permite continuar trabajando con la sesión cerrada; vuelve a solicitar el acceso. No deben reaparecer datos utilizables del usuario anterior.

### A04 — Sesión vencida o servicio temporalmente no disponible

**Preparación especial:** coordinar con soporte una cuenta de prueba cuya sesión pueda revocarse y una interrupción controlada de conexión. No apagar servicios por cuenta propia.

1. Abrir una pantalla privada con la cuenta de prueba.
2. Pedir a soporte que revoque esa sesión; intentar abrir otra pantalla o actualizar los datos.
3. Comprobar que se solicita iniciar sesión nuevamente.
4. En un intento separado, abrir una pantalla mientras no se puede comprobar la sesión por falta de conexión.
5. Restaurar la conexión y presionar Reintentar.

**Resultado esperado:** una sesión vencida no conserva acceso. Si el problema es de conexión, aparece un mensaje de reintento; no se muestra información privada ni una pantalla indefinidamente en blanco. Al recuperar la conexión, puede continuar normalmente.

## 2. Dashboard y barra lateral

**Qué debe verse.** La barra lateral muestra la bienvenida con el nombre del usuario y los accesos disponibles para su cuenta. Permite consultar Todos los proyectos y entrar a un proyecto. Los accesos administrativos, como Usuarios y Auditoría, corresponden a administración; no se debe exigir que todas las cuentas vean los mismos botones.

El cuerpo del dashboard contiene las tarjetas de los proyectos autorizados. En cada tarjeta se identifica nombre y clave, se presentan indicadores del proyecto y los gráficos disponibles. Revisar núcleos vinculados, asambleas y su nota de celebradas, COP y datos de convenios/montos de 90 % y 100 %, cuando correspondan a los registros. Los gráficos deben indicar qué representan; una ausencia de datos no debe confundirse con un cero confirmado.

Actualmente se muestran **Exportar dashboard (Excel)** y **CSV de respaldo**. El primero descarga un libro de Excel; el segundo descarga un archivo de datos sencillo. No esperar un libro con varias hojas al elegir CSV.

### A05 — Navegar desde la barra y desde una tarjeta

1. Elegir Todos los proyectos: debe mostrar el dashboard.
2. Elegir un proyecto de la barra lateral y anotar el nombre que aparece en su ficha.
3. Volver a Todos los proyectos y abrir la tarjeta de ese mismo proyecto.
4. Comparar nombre y clave: debe ser el mismo proyecto.
5. Repetir con el segundo proyecto para descartar que siempre abra el primero.
6. Contraer la barra lateral y utilizar el acceso Proyectos. Dentro de una ficha debe abrir el proyecto en curso; sin proyecto seleccionado debe llevar al listado.

**Resultado esperado:** los enlaces conservan el proyecto correcto y no mezclan información de proyectos distintos.

### A06 — Revisar los indicadores del dashboard

1. Comparar núcleos vinculados con los que aparecen en la ficha del proyecto de prueba.
2. Comparar las asambleas totales y celebradas con la relación preparada por el responsable de QA.
3. Revisar que el gráfico de asambleas y su leyenda correspondan a esas cantidades.
4. Comparar los datos de convenios del 90 % y 100 % con los registros de referencia. Revisar también la nota de convenios con dato, no sólo el monto.
5. Repetir con el proyecto vacío o incompleto.

**Resultado esperado:** cantidades y leyendas coherentes con los datos conocidos. No sumar ni comparar como si fueran equivalentes indicadores con distinto significado. Si una cifra difiere, reportar el proyecto y los registros usados para la comparación.

### A07 — Abrir los accesos administrativos

1. Con administrador, elegir Usuarios y comprobar que abre la administración de usuarios.
2. Elegir Catálogos operativos y comprobar que abre su pantalla.
3. Elegir Auditoría y comprobar que abre el historial y sus filtros.
4. Volver al dashboard entre cada intento.
5. Repetir con una cuenta de consulta, usando sólo los accesos disponibles para ella.

**Resultado esperado:** cada acceso abre la pantalla anunciada. Una cuenta sin autorización no debe poder consultar datos administrativos restringidos aunque copie el enlace. No usar este caso para crear usuarios ni modificar catálogos.

### A08 — Menú del nombre de usuario

1. En el dashboard de administrador, pulsar el nombre de usuario de la parte inferior de la barra lateral.
2. Comprobar Usuarios y permisos, Cambiar contraseña y Cerrar sesión.
3. Abrir Usuarios y permisos y después volver.
4. Abrir Cambiar contraseña; comprobar que corresponde a la propia cuenta. No cambiarla sin un caso de prueba acordado.
5. Abrir nuevamente el menú y cerrarlo haciendo clic fuera; repetir cerrándolo con Escape.
6. En una pantalla interior, verificar el menú correspondiente a esa pantalla. No exigir los tres accesos del dashboard si allí sólo se ofrecen cambio de contraseña y cierre de sesión.

**Resultado esperado:** menú visible y legible, sin quedar detrás del contenido o fuera de la ventana. Los enlaces funcionan y Escape devuelve el foco al control que abrió el menú.

### A09 — Entrada al mapa y a gestión geoespacial

1. Volver al dashboard y elegir Ver mapa sin haber seleccionado un proyecto para el mapa.
2. Comprobar que pide elegir un proyecto y no carga arbitrariamente el primero.
3. Seleccionar uno y comprobar que su nombre corresponde a lo elegido.
4. Entrar a Gestión geoespacial desde su acceso disponible, por ejemplo Gestionar cartografía en el mapa.

**Resultado esperado:** se abre el flujo anunciado y se identifica el proyecto. La carga, revisión y confirmación detalladas se prueban en el manual 3.

### A10 — Exportar Excel y CSV

1. Esperar a que terminen de cargar los proyectos y se habilite Exportar dashboard (Excel).
2. Presionar el botón y abrir `SSALFER-dashboard.xlsx`.
3. Revisar las hojas Resumen, Gráficos y las hojas de los proyectos exportados. Comparar nombres y cantidades con la pantalla.
4. Comprobar que los gráficos están incluidos, que los títulos son legibles y que no aparecen avisos de archivo dañado.
5. Regresar al dashboard y elegir CSV de respaldo.
6. Abrir el archivo descargado y revisar que tenga columnas y datos reconocibles; si Excel pide separador o codificación, elegir la importación adecuada antes de reportar columnas corridas.

**Resultado esperado:** Excel y CSV se descargan como formatos distintos. El libro conserva sus hojas y gráficos; el CSV contiene datos, no tiene por qué contener imágenes ni varias hojas.

## 3. Roles, auditoría y presentación

### A11 — Comprobar lo que permite cada cuenta

1. Ingresar por separado como administrador, operador, visualizador y geógrafo.
2. Comparar los proyectos visibles con la asignación indicada por el responsable de QA.
3. Con operador, comprobar las acciones de captura administrativa y documental autorizadas.
4. Con visualizador, comprobar consulta sin acciones de guardar o modificar.
5. Con geógrafo, comprobar gestión de cartografía y consulta documental; no debe ofrecer alta documental como si fuera operador.
6. Con administrador, comprobar administración y auditoría.

**Resultado esperado:** cada cuenta trabaja dentro de su función y sus proyectos autorizados. La propuesta de roles entregada sirve para revisión con usuarios; no concede permisos nuevos ni significa acceso a todos los proyectos. Reportar una diferencia indicando la cuenta por su nombre de prueba y rol, sin contraseña.

### A12 — Auditoría de clasificación documental

**Necesitas:** un documento de prueba al que se le haya cambiado el tipo durante el manual 2.

1. Con administrador, abrir Auditoría y sus filtros de cambios.
2. Seleccionar el proyecto y el usuario que hizo la modificación; acotar fechas si hay muchos movimientos.
3. Buscar el cambio del documento y abrir Ver detalle.
4. Revisar qué cambió, quién lo hizo y cuándo. En el tipo documental debe mostrarse su nombre si está disponible.
5. Abrir y cerrar el detalle técnico sólo como comprobación adicional; no debe sustituir la explicación legible.
6. Quitar el filtro de usuario y comprobar que el historial puede mostrar otros movimientos autorizados.

**Resultado esperado:** el administrador puede filtrar por usuario; la pantalla no está limitada automáticamente a sus propios movimientos. La información legible y el detalle deben corresponder al cambio realmente realizado.

### A13 — Repetición en pantalla angosta y con teclado

1. Reducir la ventana al tamaño aproximado de un teléfono o usar el dispositivo de prueba.
2. Repetir abrir/cerrar barra lateral, menú de usuario, proyecto y mapa.
3. Recorrer botones con Tab y activarlos con Enter; cerrar ventanas emergentes con Escape cuando tengan esa opción.
4. Revisar textos, iconos, títulos y mensajes de carga. Desplazarse hasta los botones inferiores.

**Resultado esperado:** no hay botones inaccesibles, menús tapados ni textos cortados que impidan entender una acción. En tablas anchas puede existir desplazamiento horizontal; la página completa no debe desacomodarse por ello. Registrar qué control o texto presenta el problema.

## Cierre del bloque

Registrar A01–A13 por separado. Adjuntar una captura del dashboard, del menú abierto en pantalla angosta y de cualquier diferencia. Conservar una copia de las exportaciones de prueba. No marcar como completados los casos de sesión, roles o auditoría que no pudieron prepararse.
