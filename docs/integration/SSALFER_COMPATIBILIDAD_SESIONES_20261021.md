# Compatibilidad local de sesiones con F01–F06

## Publicación del merge autorizada

El usuario autorizó confirmar este resultado como merge de dos padres y publicar
únicamente `integration/ssalfer-mq-f01-f06-20261020` en el PR #2 existente, sin
squash/rebase, sin fusionar el PR y conservando su estado Draft.

La revisión previa confirma integración remota/HEAD
`5d2e06b9e24c2a019299668fcd11cbb5de369684` y destino/MERGE_HEAD
`75598ba95ae6cd2dea5907b2054114c19a7c9b33`, que serán respectivamente el primer
y segundo padre. Se revisaron los 14 archivos previstos, los hashes de fuentes
probadas y los 145 hashes backend; sin conflictos, cambios adicionales ni
artefactos de bases de datos, respaldos o credenciales. `git diff --cached --check`
se ejecutó sin errores.

Este informe y las banderas del JSON capturan la validación **antes de crear el
merge commit**. Su campo `merge_committed=false` no debe interpretarse como el
estado posterior del commit que incorpora el informe. El SHA publicado se obtiene
del historial y del HEAD del PR. Los apartados que describen una pausa o una
autorización todavía pendiente corresponden a capturas anteriores conservadas.

Se reutilizan 55 pruebas JavaScript con LF y las mismas 55 con CRLF, 23 escenarios
de sesiones, 199 comprobaciones de protección, ocho casos de autorización y
recuperación, cuatro recorridos de sesión con backend real y cinco grupos de
validación ampliada. No se ejecuta otra suite backend: las 1,488 aprobadas, tres
fallos conocidos y 27 omisiones siguen siendo evidencia histórica, distinguida
de las pruebas de compatibilidad de esta integración.

### Pendientes para la revisión colaborativa

- Obtener el nuevo HEAD publicado en un worktree independiente y repetir los
  recorridos con una copia aislada de la base local del compañero.
- Comprobar operaciones GIS de escritura y decisiones del geógrafo **sin
  asignación**, con datos y navegación reales del compañero. Las pruebas locales
  RBAC/API anteriores no sustituyen esa validación colaborativa de escrituras.
- Verificar el ledger y checksum de la migración 030 en esa copia. No volver a
  aplicarla si ya existe con el checksum canónico, ni modificar una base real.
- Mantener visible el límite de los primeros 100 núcleos en resumen COP y Excel
  del dashboard; el mapa conserva el universo completo de núcleos activos.
- Conservar los tres fallos históricos backend y las 27 omisiones con sus
  identificadores y motivos en [la evidencia completa](SSALFER_VALIDACION_20261020.json).
- Mantener los límites de cobertura documentados: BFCache efectivo, Edge/Windows
  y operaciones de negocio no comprobadas exhaustivamente.

No se ejecutan migraciones, operaciones sobre producción ni despliegues durante
el cierre/publicación. El PR permanece para revisión y pruebas, sin merge.

## Cierre de la corrección mínima autorizada

El usuario autorizó corregir el inicializador compartido después del hallazgo
descrito más abajo. **La corrección está aplicada y las verificaciones afectadas
pasaron. El merge sigue sin commit, sin push y sin cambios al PR #2.** Las
secciones posteriores conservan el diagnóstico y la pausa de la ejecución
inicial; ya no describen un bloqueo pendiente.

### Causa y secuencia de inicialización

1. `proteccion.js`, cargado en el encabezado de las páginas protegidas, crea
   `SSALFER_SESION_LISTA`. El permiso de página aún está pendiente.
2. `auth.js` consulta la sesión y llama a la protección; esta aplica la política
   de `permisos.js` y resuelve la promesa con la sesión autorizada o con null.
   La consulta se inicia independientemente de `dashboard.js`, sin ciclo de espera.
3. Antes del arreglo, `DOMContentLoaded` iniciaba todos los componentes de
   `dashboard.js` aunque esa decisión no hubiera terminado. El sidebar llegaba
   a `proyectosDelDocumento` y `ProyectosAPI.listar`. El cliente HTTP esperaba
   la barrera, rechazaba localmente el acceso denegado y su catch lo registraba
   en consola. No había fetch de negocio ni autorización GIS indebida.
4. Ahora el manejador `DOMContentLoaded` es async y espera esa misma promesa
   **antes de cualquier inicialización**. Si resulta null, retorna. Si la página
   está autorizada, continúa normalmente. Una promesa ya resuelta sigue el mismo
   flujo. En entornos sin esa barrera opcional se conserva el comportamiento previo.

No se añaden catch, filtros de errores, excepciones silenciosas, consultas de
sesión adicionales ni permisos globales. La promesa compartida de proyectos de
F04 se conserva; sidebar y dashboard siguen realizando una sola lectura inicial.

### Archivos de la corrección

| Archivo | Líneas / alcance |
| --- | --- |
| `frontend-ssalfer/js/dashboard.js` | 1 y 5–6: manejador async, espera y retorno temprano; se normaliza el salto final de archivo |
| `tests/frontend-ssalfer/dashboard-authorization.cjs` | Nuevo: cuatro casos de denegación con autorización ya resuelta/pendiente y DOM presente/retirado |
| `tests/frontend-ssalfer/dashboard-performance.cjs` | 47, 102, 116 y desde 154: harness con barrera controlada y dos regresiones de autorización normal/demorada, celdas, peticiones y cache compartido |
| Este informe y su JSON | Actualización de resultados actuales; se conserva el diagnóstico inicial como evidencia histórica |

La corrección de producto se limita al inicio de un único archivo. Los nueve
archivos entrantes distintos del dashboard siguen idénticos byte a byte a
`75598ba`: autenticación, cliente HTTP, protección, marco, estilos y sus pruebas
y documentación. El dashboard conserva también los cambios de menú del compañero
y el cuerpo de F04. F05/F06, Excel, las dos protecciones GIS y la migración 030
permanecen como estaban antes de esta corrección.

### Resultados después del arreglo

| Pruebas afectadas | Resultado |
| --- | --- |
| JavaScript F04–F06, mapa y autorización GIS/dashboard, LF | 55 aprobadas, cero fallos/omisiones: las 49 anteriores más seis nuevas |
| Las mismas pruebas con CRLF simulado | Las mismas 55 aprobadas; no son 55 casos adicionales ni certificación de Windows |
| Chromium, escenarios de sesiones del compañero con API simulada | 23 aprobados |
| Chromium, protección sobre HTML real de 35 pantallas | 199 comprobaciones aprobadas, cuatro roles y desconocido, API simulada |
| Chromium, backend real y base desechable: script de sesiones del compañero | Cuatro recorridos aprobados, una petición de logout por rol y posterior 401, sin excepciones JavaScript |
| Chromium, batería ampliada que antes fallaba | Cuatro roles completos y recuperación de enlace directo anónimo: cinco grupos aprobados |
| Chromium, dashboard real y API simulada | Ocho casos aprobados: 401/403/500/red con recuperación y autorización demorada de los cuatro roles |

En la batería ampliada se mantuvo y reforzó la expectativa de consola vacía:
ahora se comprueba tanto la entrada directa como la recarga GIS, esperando que
terminen las peticiones. Operador y visualizador no generan peticiones de negocio,
no inicializan `SSALFER_GIS` y reciben 403 en la API administrativa. Administrador
y geógrafo inicializan y seleccionan el proyecto; sus lecturas GIS autorizadas
responden 200 y un identificador inexistente conserva 404. La API sin sesión
conserva 401. Los cuatro roles mantienen mapa/indicadores en su alcance; el
operador sin asignación y los proyectos inactivos siguen bloqueados.

Los cuatro roles completaron enlace dashboard → proyecto → Atrás, recarga,
descarga y reapertura real de XLSX y las comprobaciones pertinentes de
seguimiento/reportes (incluida la denegación de páginas no habilitadas al geógrafo,
según la política previa). La recuperación real del enlace protegido tras login
y el rechazo de un `return_to` externo también pasaron. Las cookies y el
vencimiento absoluto conservan su contrato.

Los ocho escenarios adicionales usan el HTML real del dashboard. Antes de
autorizar no hay consultas de negocio; tras autorizar se inicializa normalmente
con una sola consulta compartida de proyectos. Un 401 exige login; 403, fallo de
red y 500 permiten reintentar sin cerrar sesión. Se comprueba ausencia de errores
de inicialización; los errores HTTP/red esperados de esos escenarios simulados
no se confunden con una excepción de la aplicación.

Como control negativo, los cuatro tests nuevos de denegación fallan al cargar
en memoria el dashboard anterior al guard, sin cambiar el checkout. No se
suprimió el error ni se relajaron aserciones para conseguir los resultados.

No se ejecutó otra suite backend: no hay cambios backend/DDL y sus 145 hashes
se conservan. Se reutilizan las 42 pruebas focalizadas de sesiones/RBAC ya
aprobadas y la suite completa histórica de 1,488 aprobadas, tres fallos conocidos
y 27 omisiones. La expiración por tiempo sigue respaldada por las pruebas de
reloj controlado previas y por los 401 simulados en Chromium; no se esperaron
30 minutos/ocho horas reales. Se mantienen las limitaciones BFCache efectivo,
Edge/Windows y cobertura integral de todas las operaciones de negocio.

Nueva evidencia separada, sin sobrescribir los resultados de la pausa anterior:
`/tmp/ssalfer-dashboard-guard-20261021/`. El JSON distingue explícitamente la
ejecución inicial fallida y esta revalidación satisfactoria. Las credenciales de
QA se conservan solo fuera del repositorio. El nuevo entorno desechable se
retiró al terminar las pruebas. No se modificaron bases originales ni producción.

Procede solicitar autorización para confirmar el merge local y publicar su
resultado en la misma rama y PR #2. No realizar ninguna de esas acciones todavía.

## Estado y alcance

Worktree `.worktrees/ssalfer-integracion-mq-f01-f06`, rama
`integration/ssalfer-mq-f01-f06-20261020`.

- HEAD y rama remota de integración: `5d2e06b9e24c2a019299668fcd11cbb5de369684`.
- Destino obtenido mediante `git fetch origin` y MERGE_HEAD:
  `75598ba95ae6cd2dea5907b2054114c19a7c9b33`.
- Ancestro común: `d73615f7d447159ef9512d0ef500d0ae887ee5fd`.

El worktree estaba limpio antes de ejecutar
`git merge --no-commit --no-ff origin/feature/integracion-mq-deploy`.
El merge se aplicó automáticamente: diez archivos preparados, sin conflictos
textuales ni archivos sin resolver. `dashboard.js` combina ambas ramas.
No se eligió una versión completa de ese archivo. No se confirmó el merge,
publicó, hizo rebase ni desplegó. El PR #2 continúa abierto en Draft y conserva
el HEAD publicado `5d2e06b`.

**La validación ampliada se detuvo por un error de consola preexistente en el
sidebar compartido. No se declara aprobada toda la integración ni se propone
confirmar el merge antes de resolver o aceptar expresamente ese pendiente.**

## Análisis del cambio 75598ba

El commit modifica exclusivamente frontend y pruebas/documentación. No cambia
endpoints, cookies del servidor, reglas RBAC, parámetros de caducidad ni DDL.

| Componente | Cambio y relación con la integración |
| --- | --- |
| `api/auth.js` | Logout explícito por `data-action`, controles de interacción, una sola solicitud, reintento ante fallo y sincronización de cierre entre pestañas. Conserva la promesa compartida de consulta de sesión que usa F04. |
| `api/cliente.js` | Bloquea llamadas nuevas después de una sesión invalidada, distingue 401 de 403/CSRF, conserva `AbortError` y notifica la invalidación común. Es transversal a F04, F05, F06 y GIS. No reenvía escrituras automáticamente. |
| `utils/proteccion.js` | Conserva `SSALFER_SESION_LISTA`; resuelve sesión o null y mantiene el control de rol por página. Añade aviso al perder sesión con formulario editado y reintento ante fallos de comprobación. Los dos módulos GIS corregidos siguen usando esta misma barrera. |
| `utils/marco.js`, `styles/marco.css` | Logout como botón, foco y menú común; sin criterios de proyectos ni indicadores. |
| `dashboard.js` | Solo los ajustes del menú de cuenta del compañero se superponen al archivo F04. Se conservan `proyectosDelDocumento`, carga compartida, resumen COP y registro ordenado del Excel. |

La cookie de sesión sigue siendo HttpOnly, con CSRF separado y credenciales
incluidas. El entorno de pruebas usa las cookies de desarrollo, sin Secure,
en localhost; no certifica una terminación TLS productiva.

El backend actualiza `ultima_actividad` al autenticar una petición y conserva
el vencimiento absoluto. No aparece un endpoint de renovación, contador previo
de inactividad ni recuperación automática de borradores. El aviso mantiene
temporalmente el DOM; no guarda datos de formularios en almacenamiento local.
Las pruebas backend controlan el reloj para caducidad por inactividad y absoluta;
no se esperaron 30 minutos ni ocho horas en navegador. En navegador se comprobó
que consultas sucesivas no cambian `expira_en` en los recorridos ampliados
alcanzados.

## Conservación comprobada

Los hashes de 145 archivos de backend, migraciones y pruebas coinciden con la
[evidencia completa anterior](SSALFER_VALIDACION_20261020.json). La migración
030 permanece idéntica, SHA256
`aa8f3f568b3abb42751202301b980d9e5dda15db2d7070c661648445e050423d`.

Los scripts `gestionGeoespacial.js`, `conciliacionGeoespacial.js`, `mapa.js`,
`seguimiento.js` y `utils/dashboardExcel.js` permanecen idénticos a `5d2e06b`.
Así se conservan la protección administrativa GIS, el mapa publicado, F05/F06,
la presentación «Tipo no informado» y el orden de convenios por ID. La combinación
automática del dashboard conserva F04, comprobado con las regresiones de celdas,
contadores y solicitudes.

Se conserva el alcance vigente: administrador/visualizador/geógrafo leen
proyectos activos; operador solo asignados. La administración GIS continúa
exclusiva de administrador/geógrafo y las asignaciones nuevas solo a operadores.
No cambian `READ_ROLES` ni los contratos API.

## Pruebas ejecutadas

| Conjunto | Resultado y alcance |
| --- | --- |
| JavaScript de integración con LF | 49 aprobadas, cero fallos/omisiones; F04–F06, exportaciones y módulos GIS |
| Mismas JavaScript con CRLF simulado | Las mismas 49 aprobadas; no son casos adicionales ni ejecución en Windows |
| Backend focalizado, PostgreSQL/PostGIS | 42 aprobadas, cero fallos/omisiones: autenticación 2, GIS 35, expiración/logout 3, revocación por contraseña 1 y revocación/desbloqueo administrativo 1 |
| Nuevo script de sesiones del compañero | 23 escenarios aprobados en Chromium real con API simulada |
| Protección del HTML real | 35 pantallas, cuatro roles y desconocido: 199 comprobaciones aprobadas, API simulada |
| Nuevo script integrado del compañero | Cuatro recorridos reales aprobados: login, recarga, mapa, Atrás y logout; una petición de cierre por rol y posterior 401, sin excepciones JavaScript |
| Batería ampliada con API real | Administrador completado; operador falla en el requisito de consola limpia al recargar GIS denegado. La batería completa **no está aprobada** |
| Comparación del hallazgo | Operador/visualizador en `5d2e06b` y en el merge: mismo error local del sidebar; cero peticiones de negocio, cero excepciones no capturadas y 403 real de API GIS |

El recorrido ampliado de administrador comprueba enlace dashboard → proyecto →
Atrás, recarga, descarga/reapertura del XLSX, mapa y alcance por proyecto, GIS,
identificadores directos e inicialización de seguimiento/reportes. El operador
alcanzó y aprobó navegación, descarga/reapertura XLSX y alcance de mapa antes del
fallo de consola. No se completaron sus pasos posteriores, los recorridos
ampliados de visualizador/geógrafo ni el caso adicional de recuperación de enlace
directo anónimo/retorno externo de esa batería. No se cuentan como aprobados.

El script integrado de cuatro roles verifica sus recorridos de sesión; no
certifica todas las operaciones de negocio de esos roles. Los tests VM y
API focalizados aportan cobertura independiente de reportes, valores, seguridad
por ID, bajas e historia. El paso real por Atrás se ejecutó con la configuración
normal de Playwright; no certifica una restauración efectiva desde BFCache.
No se certifican Edge/Windows, todos los formularios o comparaciones visuales
exhaustivas de capas e historia cartográfica.

## Hallazgo que requiere decisión

Pasos reproducidos con operador asignado y visualizador sin asignación:

1. Iniciar sesión en el entorno aislado.
2. Abrir directamente `/pages/gestionGeoespacial.html?id_proyecto=5` y recargar.
3. La protección muestra «Acceso no permitido» y resuelve
   `SSALFER_SESION_LISTA` con null.
4. Los dos módulos administrativos retornan correctamente sin inicializar GIS.
5. El inicializador compartido del sidebar en `dashboard.js`, alrededor de la
   lectura de `proyectosLista`, ya intentó cargar proyectos. `cliente.js` bloquea
   la operación **antes de fetch**, pero el catch del sidebar la registra en
   consola mediante `mostrarErrorAPI`.

Mensaje en el merge: `Error de API: ErrorAPI: No se autorizó el acceso a esta
pantalla`, con stack en `cliente.js:183`, `api/proyectos.js:23` y
`dashboard.js:707`. La versión `5d2e06b` muestra el mismo fallo de inicialización,
con el mensaje anterior «Inicia sesión para acceder al sistema» y estado local
401. El nuevo cliente usa 403 para la barrera de página, según el cambio del
compañero. El backend GIS sigue respondiendo 403 en ambas versiones.

La comparación se ejecutó sustituyendo las seis fuentes de sesión/menú de
`5d2e06b` solo en memoria mediante rutas Playwright. No se cambió el checkout.
No se encontró exposición de datos ni una regresión nueva de autorización.
Es un defecto preexistente de presentación que los tests VM de los dos módulos
GIS no cubrían: no ejecutaban el sidebar común sobre una página denegada real.
No se alteró la expectativa de consola limpia para hacer pasar la batería.

Alternativas para autorización:

1. **Recomendada:** hacer que la inicialización compartida de `dashboard.js`
   espere la barrera de página y retorne si no fue autorizada, antes de preparar
   componentes o llamar a `proyectosDelDocumento`. Mantener los 403 del backend,
   el cache por documento de F04 y la política de roles. Añadir la regresión del
   sidebar real y repetir las pruebas afectadas y la batería ampliada.
2. Mantener el código actual y aceptar expresamente el error de consola como
   pendiente preexistente. La batería ampliada debe seguir registrada como
   fallida; no equivale a una certificación completa.

No se implementó ninguna de estas alternativas. El merge permanece pendiente
a la espera de la decisión, conforme a la instrucción de detenerse ante un
problema funcional o decisión ambigua.

## Entorno y evidencia

Proyecto Docker nuevo `ssalfer-sesiones-20261021`, base `software_pa_test`,
cluster `convenio-report-disposable`, PostgreSQL/PostGIS en tmpfs sin puerto
publicado. Se usaron esquema de pruebas saneado, catálogos, datos públicos RAN
y cuentas/proyectos sintéticos. La 030 se aplicó solo a esta base nueva para
reproducir la integración; su archivo no se modificó.

Backend QA en localhost:18003 y servidor/proxy temporal del frontend en
localhost:15177; la red adicional del proyecto permitió publicar solo ese
backend, manteniendo la base en su red interna. No se usaron producción,
credenciales reales ni las bases/servicios del compañero. Los contextos de
Playwright fueron independientes por rol/escenario. El entorno y servidor QA
se retiraron al terminar las comprobaciones.

Chromium, Playwright y tres bibliotecas faltantes se descargaron/extraían solo
en `/tmp`, sin instalar paquetes del sistema ni dependencias en el repo. El
adaptador temporal cambia únicamente el ejecutable Linux y la ruta de
bibliotecas; las aserciones de los scripts del compañero no se modifican.
Los reintentos de preparación (ruta del ejecutable, bibliotecas y carga XLSX
por bytes del bundle browser) fueron del harness y no fallos de la aplicación.
El fallo final de consola sí se registra como hallazgo de producto.

[Evidencia y hashes](SSALFER_COMPATIBILIDAD_SESIONES_20261021.json).
Logs, scripts temporales y resultados originales:
`/tmp/ssalfer-sesiones-20261021/`. No se incluyen cookies o contraseñas en los
informes versionables.

Se reutiliza la suite backend completa anterior: 1,488 aprobadas, tres fallos
preexistentes y 27 omisiones, con identificadores/motivos en la evidencia del
20 de octubre. No se repitió ni se declara corregida. El límite de 100 núcleos
en resumen COP/Excel del dashboard continúa pendiente; el mapa conserva su
universo completo. El defecto Excel `tipo_convenio=null` sigue corregido, no
se vuelve a clasificar como pendiente.
