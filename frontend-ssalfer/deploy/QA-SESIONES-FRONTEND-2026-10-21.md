# Revisión y corrección de sesiones — frontend SSALFER

Fecha: 21 de octubre de 2026.

## Alcance y diagnóstico

Trabajo local en `feature/integracion-mq-deploy`, sobre `d73615f7d447159ef9512d0ef500d0ae887ee5fd`. La auditoría entregada corresponde a `630f7dd66c494a1f2a4b4375184ff49a3a5b540b`. Se compararon esos dos commits en los componentes de sesión, protección, menú y dashboard antes de editar.

Entre esas versiones se habían añadido controles de acceso por rol y ajustes del dashboard, pero persistían la identificación de logout por texto, la falta de bloqueo de solicitudes repetidas y el tratamiento de 403 como sesión inválida. `marco.js` no había cambiado entre esos commits. No se atribuyen estos hallazgos a otras ramas ni se afirma haber inspeccionado el servidor en mantenimiento.

La auditoría **no demostró un cierre automático cada cinco minutos**. Estas correcciones eliminan debilidades reproducibles; no identifican retrospectivamente el evento que originó los POST de los incidentes del servidor.

## Cambios aplicados

| Archivo / componente | Antes | Ahora |
| --- | --- | --- |
| `js/api/auth.js`: delegación de clics | Reconocía la frase «cerrar sesión» en cualquier enlace. | Solo actúa sobre enlaces o botones con `data-action="logout"`. No interpreta el texto. |
| `auth.js`: eventos | Aceptaba activaciones sintéticas y no comprobaba si el evento estaba cancelado. | Exige un clic de usuario, ignora eventos cancelados, modificadores, controles ocultos/inertes/deshabilitados. El botón nativo funciona con Enter y Espacio. `isTrusted` reduce activaciones accidentales; no es una barrera contra código malicioso del mismo origen. |
| `auth.js`: `cerrarSesion` | Cada activación podía enviar otro POST. | Comparte la solicitud mientras se procesa y conserva el cierre confirmado. Un fallo permite reintentar. La carga repetida del módulo no duplica el listener. |
| `auth.js`: `requerirSesion` y comprobación inicial | 401 y 403 provocaban redirección. | Solo 401 acredita sesión inválida. Ante 403, red o fallo del servidor se muestra una pantalla de reintento, sin solicitar logout ni enviar al login. Una respuesta incompleta tampoco se interpreta como cierre. |
| `js/api/cliente.js`: `request` | Un 401 de negocio redirigía directamente; cancelaciones se convertían en error de conexión. | Notifica la invalidez a la protección común, que evita avisos repetidos. Mantiene 403 y su detalle, incluido CSRF. Conserva `AbortError`. El 401 del intento de login queda excluido de la invalidación. También se atiende un 401 de una operación autenticada como cambiar contraseña. |
| `cliente.js`: acceso posterior al vencimiento | La promesa inicial podía seguir indicando la sesión ya resuelta. | Una marca solo en memoria bloquea nuevas peticiones de negocio cuando se conoce la pérdida de sesión. No se reenvían escrituras automáticamente. |
| `js/utils/marco.js` | Logout era un enlace con destino `#`. | Es un botón `type="button"`. El desplegable se cierra al sacar el foco; Escape devuelve el foco al control de cuenta. Se conserva su posición fuera del aside. |
| `js/dashboard.js`: `configurarMenuCuenta` | Volvía a preparar un menú que también construye el componente común; buscaba acciones por texto. | Deja construir el menú al componente común. El mecanismo alternativo usa identificadores explícitos. |
| `styles/marco.css` | Estilos del menú orientados solo a enlaces. | Botón y enlaces comparten presentación, con foco visible y estado de procesamiento. |
| `js/utils/proteccion.js`: formularios | Un 401 podía redirigir inmediatamente, perdiendo lo escrito. | Si se detectó edición de un formulario, muestra un diálogo antes de abandonar la página. Mantiene el DOM en memoria, bloquea nuevas operaciones y explica que ir al login pierde lo no guardado. Cerrar sesión voluntariamente pide revisar los cambios y permite cancelar la salida. |
| Varias pestañas | Otra pestaña podía conservar la presentación de una sesión cerrada. | `BroadcastChannel` comunica únicamente «sesion-cerrada» después del éxito del logout. Las demás pestañas no envían otro POST. Las que contienen edición muestran el aviso; las restantes vuelven al login. Si el canal no está disponible, el siguiente 401 conserva el control de acceso. |

El cambio de contraseña sigue siendo navegación mediante un enlace normal. No cambian los endpoints, cookies HttpOnly, encabezado CSRF, reglas de permisos ni parámetros de expiración. No se guardan credenciales, tokens ni valores de formularios en localStorage/sessionStorage. El aviso de otra pestaña no contiene identificadores de usuario ni de sesión.

## Formularios: alcance real de la protección

La marca de edición es conservadora: recuerda que hubo interacción con un formulario durante la visita, pero no conoce si cada módulo guardó con éxito. Por eso dice «Revisa que hayas guardado» y no afirma que existan cambios pendientes. Los formularios identificados como búsqueda (`role="search"`) se excluyen.

**No hay recuperación automática de borradores ni reautenticación dentro del formulario.** El aviso evita una redirección silenciosa, pero lo no guardado se pierde al ir al login, recargar o cerrar la pestaña. No se promete protección ante cierres del navegador, controles editables fuera de un formulario ni operaciones que ya estaban en curso. Los datos permanecen únicamente en el DOM de esa página hasta abandonarla.

## Inactividad: evaluación y pendiente separado

La respuesta existente de `/auth/sesion` expone `user` y `expira_en`. La inspección de lectura del servicio confirma que `expira_en` representa el vencimiento absoluto; la inactividad se comprueba aparte con `ultima_actividad` y la configuración del servidor.

No se añadió un contador de 30 minutos calculado desde la apertura de la página: sería inexacto entre pestañas y podría ocultar un vencimiento anterior. Tampoco se añadió una consulta periódica que mantenga la sesión activa indefinidamente.

Para un aviso previo fiable por inactividad conviene que el equipo de backend defina cómo comunicar el límite efectivo o la última actividad autoritativa y cómo consultar esa información sin renovar automáticamente la sesión. Sobre ese contrato se puede construir un botón explícito «Continuar trabajando». **Es una mejora pendiente, no un endpoint implementado ni una modificación de esta ronda.** El vencimiento absoluto no debe prolongarse con ese botón.

## Pruebas y evidencia

### Navegador real con API simulada: 23 casos aprobados

Script: `frontend-ssalfer/deploy/qa-sesiones-2026-10-21.cjs`.

Incluye: enlace de negocio que menciona cerrar sesión; clic sintético; evento cancelado; doble clic con respuesta demorada; Enter y Espacio; Escape y foco; posición del menú en escritorio y móvil; 401/403/500/red en la comprobación inicial y durante el uso; formulario con edición ante 401 simultáneos; bloqueo de nuevas operaciones; cancelar la salida; reintento tras un logout fallido; dos pestañas; módulo cargado dos veces; login rechazado; cookie y encabezado CSRF; conservación del detalle 403; cancelación de peticiones; y 401 al cambiar contraseña.

Resultados: `outputs/sesiones-2026-10-21/resultados.json`. Capturas de prueba: `menu-escritorio.png`, `menu-movil.png`, `sesion-terminada-formulario.png` en esa carpeta. Las capturas del entorno simulado muestran componentes compartidos sobre una página mínima, no una ficha de negocio completa.

### Protección de pantallas y roles: 199 comprobaciones aprobadas

Script existente: `frontend-ssalfer/deploy/qa-roles-2026-10-19.cjs`.

35 pantallas; administrador, operador, geógrafo, visualizador y rol desconocido; controles dinámicos y restricciones de escritura. Utiliza el HTML real y aísla las consultas de negocio. No es una prueba integral de todas las operaciones de las 35 pantallas.

Evidencia de ejecución: `outputs/sesiones-2026-10-21/roles.log`.

Se actualizó la expectativa 403 del script histórico `qa-proteccion-2026-10-08.cjs`: ahora espera reintento sin redirección. Ese script completo no se ejecutó en esta ronda; sus escenarios de autenticación afectados están cubiertos en la batería nueva.

### Frontend y backend reales en una copia QA: cuatro roles aprobados

Script: `frontend-ssalfer/deploy/qa-sesiones-integracion-2026-10-21.cjs`.

Se usó `http://127.0.0.1:15175`, la copia QA aislada de referencia preparada previamente, con el frontend local modificado y usuarios sintéticos. En cada rol se comprobó login, dashboard, recarga, navegación al mapa, regreso y cierre con teclado. Cada flujo envió un solo POST de logout y posteriormente `/auth/sesion` respondió 401. No hubo errores JavaScript en los flujos completados.

Evidencia: `outputs/sesiones-2026-10-21/sesiones-reales-qa.json` y `menu-real-admin.png`, `menu-real-operador.png`, `menu-real-geografo.png`, `menu-real-visualizador.png`.

Estas pruebas crean y cierran sesiones sintéticas y sus eventos normales de auditoría en la copia QA. No modifican registros de negocio ni cuentas reales. Se verificó la disponibilidad de los controles de sesión; no se exige que terminen todas las consultas de datos o capas del mapa para probar la navegación.

### Límites de la validación

- No se esperaron 30 minutos/8 horas para medir la expiración real por tiempo; se verificó el comportamiento frontend ante 401 y una revocación real por logout en QA.
- No se modificó producción ni se reprodujo el incidente histórico sobre las sesiones de personas reales.
- No se ejecutó una regresión completa de cada formulario o módulo de negocio, ni lectores de pantalla específicos.
- Para cerrar la investigación del incidente, aún hace falta correlacionar la hora del POST de logout del servidor con la acción del usuario en una reproducción controlada. No deben compartirse cookies, contraseñas ni archivos HAR sin sanitizar.

## Prueba manual breve

1. **Ruta: Inicio de sesión → Dashboard → nombre del usuario.** Abrir el menú. Deben aparecer Cambiar contraseña y Cerrar sesión; administrador puede ver además Gestión de usuarios. Abrirlo no debe cerrar la sesión.
2. **Ruta: Dashboard → nombre del usuario → Cambiar contraseña.** Debe abrir la pantalla correspondiente sin enviar logout.
3. **Ruta: Dashboard → nombre del usuario → Cerrar sesión.** Dar doble clic. Debe volver al inicio; en la pestaña Red debe existir un solo POST de logout para esa activación.
4. Entrar nuevamente. Abrir el menú con teclado, recorrer opciones con Tab y cerrar con Escape. El foco debe volver al nombre del usuario. Cerrar sesión funciona con Enter o Espacio sobre el botón.
5. Abrir otra pestaña del mismo entorno. Cerrar sesión en la primera. La segunda debe pedir inicio de sesión sin enviar un segundo logout; si estaba editando un formulario, debe mostrar el aviso antes de abandonarlo.
6. **Ruta: Dashboard → nombre del usuario → Cambiar contraseña.** Escribir solo un valor de prueba, sin guardar. Intentar cerrar sesión: el aviso permite cancelar. No se requiere cambiar ninguna contraseña para esta prueba.
7. Los fallos de red, 403/CSRF y 500 se reproducen sin datos reales mediante `qa-sesiones-2026-10-21.cjs`. Deben mostrar error o reintento sin logout. Un 401 debe exigir autenticación; si había edición, aparece el diálogo de sesión terminada.
8. Para probar expiración real, usar una cuenta QA y un formulario con datos ficticios, dejar de realizar peticiones autenticadas durante el límite configurado y después intentar una consulta. Verificar el 401 y el aviso. No confundir dejar de mover el mouse con inactividad del servidor: otras pestañas o solicitudes autenticadas pueden mantener actividad.

## Estado de entrega

Cambios exclusivamente de frontend y sus pruebas/documentación. Sin cambios de backend, endpoints o base de datos. Sin commit, push, merge ni despliegue. Los archivos locales previos se conservaron.
