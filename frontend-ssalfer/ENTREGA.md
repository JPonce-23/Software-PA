# Entrega — Frontend SSALFER conectado al backend

## 1. Alcance de este release (declarado explícitamente)

Estas cuatro áreas **quedan fuera de este release** porque el
backend ya expone los endpoints pero el frontend no tiene ninguna
pantalla para ellas. Se documentan aquí en vez de ocultarse:

- **Administración de usuarios** (CRUD, desbloqueo, revocar
  sesiones) — expuesto por `app/routers/users.py`. No existe ninguna
  pantalla; solo el superadmin puede operar esto hoy directamente
  contra la API (ej. con un cliente HTTP) hasta que se construya la
  pantalla.
- **Administración de catálogos operativos** (alta/edición de
  opciones de los selects) — expuesto por `CatalogosAPI` /
  endpoints de catálogos. Los catálogos deben seguir
  mantenerse por otra vía (SQL directo / script) hasta que exista
  pantalla.
- **Importaciones geoespaciales** (shapefile/GeoJSON) — expuesto por
  `app/routers/geospatial_imports.py`. Sin pantalla.
- **Auditoría** (`app/routers/audit.py`, endpoints
  `GET /auditoria/cambios` y `GET /auditoria/accesos`, ambos
  restringidos a rol `admin`) — este vacío no se había declarado
  hasta ahora. No existe `AuditoriaAPI` en `js/api/` ni ninguna
  pantalla que la consuma. Se detectó al revisar la lista completa
  de routers del backend; queda pendiente para el siguiente release
  igual que las tres anteriores.

Ninguna de las tres tenía pantalla antes de este release tampoco;
no se retiró nada, solo se deja constancia explícita de que siguen
pendientes.


## 2. Qué se corrigió en este release

### Dashboard y navegación de proyectos
- `dashboard.html` ya no lista 3 proyectos fijos (AIFA-Pachuca,
  México-Querétaro, Saltillo-Nuevo Laredo): ahora llama a
  `ProyectosAPI.listar()` y `NucleosAPI.listarPorProyecto()` para
  cada uno y arma las tarjetas con datos reales.
- El nombre de usuario ("Carlos Pérez" / "Nombre usuario") se
  reemplazó en **todas** las páginas por el nombre real vía
  `AuthAPI.obtenerSesionActual()` (lógica centralizada en
  `dashboard.js`, que se carga en todas las páginas).
- El listado de proyectos del menú lateral (antes 3 links fijos en
  cada una de las ~23 páginas) ahora se genera dinámicamente en
  todas ellas desde el mismo lugar en `dashboard.js`.
- Se agregó el botón **"Exportar dashboard (CSV)"** en
  `dashboard.html`, conectado a
  `ReportesAPI.urlExportacionDashboardCsv()` (antes ese endpoint
  nunca se invocaba desde ningún archivo).

### Páginas de proyecto (AIFA-PACHUCA.html, MEXICO-QUERETARO.html, SALTILLO-NUEVOLAREDO.html)
- Se **eliminaron** las 3 páginas estáticas casi idénticas.
- Se creó `pages/fichaProyecto.html` + `js/fichaProyecto.js`: lee
  `?id=<idProyecto>` de la URL, llama a `ProyectosAPI.obtener()` y
  `NucleosAPI.listarPorProyecto()`, y calcula sus KPIs (núcleos,
  parcelas, afectaciones, superficie afectada) a partir de datos
  reales — nada hardcodeado.
- `nucleoAgrario.js`: el botón "Volver al proyecto" apuntaba fijo a
  `AIFA-PACHUCA.html`; ahora usa el `id_proyecto` real de la
  respuesta del backend.

### Estado financiero
- `estadoFinanciero.html`/`.js` (antes 100% simulado, ~885 líneas
  sin una sola llamada a la API) se **rediseñó** como un dashboard
  de reportes reales por proyecto (`?id_proyecto=`), conectado a:
  `ReportesAPI.obtenerKpiDashboard`, `obtenerAvancePeriodo`,
  `obtenerConveniosValoresDeclarados`,
  `obtenerConveniosCoberturaImpactos`, `obtenerFifonafeCobertura`, y
  el botón de exportación CSV ya filtrado por proyecto.
- **Decisión de alcance documentada aquí**: las tablas anteriores de
  "convenios/pagos individuales por beneficiario" con montos
  90/100/BDT específicos **no tienen un endpoint equivalente a nivel
  proyecto** (`ConveniosAPI` e `IndemnizacionAPI` solo listan por
  afectación, no por proyecto completo). Por eso esta página ahora
  muestra reportes **agregados** (lo que el backend sí ofrece a
  nivel proyecto), y el detalle por beneficiario se sigue
  consultando desde `detalleAfectacion.html`, `fichaConvenio.html`
  e `indemnizacion.html`, que sí tienen el contexto de la afectación
  específica.

### Detalle de afectación
- `detalleAfectacion.js` (antes sin una sola llamada real) ahora
  conecta:
  - `AfectacionesAPI.obtener()` para información general y avalúo
    (incluye edición real vía `PATCH` con formularios inline).
  - `ConveniosAPI.listarPorAfectacion()` para la tabla de convenios.
  - `IndemnizacionAPI.listarPorAfectacion()` +
    `IndemnizacionAPI.listarPagos()` para indemnización y pagos.
  - Unidades agrarias: vienen anidadas en la propia respuesta de
    `AfectacionesAPI.obtener()` (`unidades_agrarias`), no requieren
    llamada aparte.
- **Limitación real del backend, documentada en la propia pantalla**:
  no existe un endpoint para consultar FIFONAFE por afectación
  (`app/routers/domain.py` solo permite gestionar FIFONAFE a nivel
  proyecto-núcleo). La sección de FIFONAFE en esta página lo indica
  honestamente y enlaza a la ficha de FIFONAFE del núcleo
  correspondiente, en vez de simular datos.
- Corregidos los links "Volver a afectaciones" (arriba y abajo de la
  página), que apuntaban a `afectacion.html` sin el parámetro
  `id_proyecto_nucleo` que esa página necesita para cargar.

### Bugs de navegación encontrados y corregidos (no estaban en el pedido original, pero rompían la navegación)
- `afectacion.html`: el tercer link del menú lateral apuntaba a
  `SALTILLO-NUEVO-LAREDO.html` (con un guion de más) en vez de
  `SALTILLO-NUEVOLAREDO.html`.
- `afectacion.js`: tras crear una afectación nueva, redirigía a
  `detalleAfectacion.html?id_afectacion=X`, pero esa página espera
  `?id=X` — quedaría en blanco.
- `nuevoConvenio.html`: el breadcrumb `id="enlaceDetalle"` estaba
  fijo en `detalleAfectacion.html?id=1` sin importar la afectación
  real; ahora se actualiza dinámicamente.
- **Hallazgo mayor**: `afectacion.html` mostraba 3 tarjetas de
  afectación **completamente estáticas** (montos de avalúo y
  superficies inventados) y `afectacion.js` nunca tenía código para
  listar afectaciones reales (solo manejaba el formulario de
  creación). Se agregó `AfectacionesAPI.listarPorProyectoNucleo()`
  con render real, actualizando también los contadores del resumen
  (total, completas, pendientes, superficie) que ya tenían los `id`
  listos pero nunca se llenaban.
- Los breadcrumbs que apuntaban a las páginas de proyecto eliminadas
  (en asamblea, nucleoAgrario, nuevoConvenio, fifonafe) se dejaron
  apuntando de forma segura a `/dashboard.html` — **pendiente
  declarado**: no se le dio a cada uno su enlace dinámico al
  proyecto específico (requeriría tocar ~19 archivos JS más, fuera
  del alcance de esta pasada); no quedan rotos, pero no son tan
  específicos como podrían ser.

### Configuración para producción
- `js/env.js` (nuevo): único punto de inyección de
  `window.SSALFER_API_URL`, cargado antes de `config.js` en las 24
  páginas (antes apuntaba siempre a `localhost:8000` sin forma de
  cambiarlo por archivo).
- `deploy/Dockerfile` + `deploy/nginx.conf` +
  `deploy/docker-compose.ssalfer.yml` (nuevos): sirven el frontend
  estático y reenvían `/api/` al backend por el mismo origen,
  requisito real de las cookies `__Host-pa_session` /
  `__Host-pa_csrf` en producción (confirmado contra
  `app/config.py` del backend). No modifican ningún archivo del
  backend — es un compose adicional que se levanta junto al
  existente.
- Ver `DEPLOY.md` para el paso a paso completo (local y producción)
  con Docker Desktop.


## 3. Cosas que NO se tocaron, tal como se pidió
- `ClienteAPI` / `js/api/*.js` (cookies, CSRF, manejo de errores):
  sin cambios.
- Ningún archivo del backend (`Software-PA-feature-backend-logica/backend`):
  sin cambios. Todas las correcciones de "conexión" son 100%
  frontend + variables de entorno / configuración de despliegue.


## 4. Pendientes sugeridos para la siguiente pasada
1. Breadcrumbs dinámicos por proyecto en las páginas profundas
   (asamblea, nucleoAgrario, nuevoConvenio, fifonafe, y las demás
   ~19 páginas que no se tocaron en esta pasada).
2. Pantallas de administración de usuarios, catálogos operativos e
   importaciones geoespaciales (sección 1 de este documento).
3. Verificar en caliente contra un backend real corriendo (todo lo
   anterior se validó por lectura exhaustiva del código fuente real
   del backend — schemas, routers y migraciones — pero no se ejecutó
   contra una base de datos con datos, así que vale la pena una
   pasada de pruebas manuales con datos reales antes de dar por
   cerrado el release).
