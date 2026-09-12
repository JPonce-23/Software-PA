# Guía de pruebas — flujo completo SSALFER

Esta guía sigue el flujo real que exige el backend (confirmado
contra `app/schemas.py` y `app/routers/domain.py`), no un flujo
"lógico" inventado. Cada paso indica: la pantalla real a usar, qué
endpoint dispara, los campos que el backend exige u obliga por
validación, y qué revisar para confirmar que quedó bien conectado.

Como es un flujo largo, ve tachando cada paso y anota el `id`
numérico que te regrese cada creación (proyecto, núcleo, afectación,
etc.) — los vas a necesitar para los pasos siguientes.

Antes de empezar: abre la consola del navegador (F12 → Console/
Network) en cada pantalla. Si algo falla, ahí vas a ver el código
HTTP real y el mensaje de error del backend — es la forma más rápida
de distinguir "el frontend mandó mal el dato" de "el backend
rechazó algo por una regla de negocio".


## 0. Prerrequisitos

- [ ] Backend levantado (`db` + `backend` saludables en Docker
      Desktop).
- [ ] Al menos un usuario admin creado. Si no existe ninguno
      todavía, se crea con el script `backend/scripts/create_admin.py`
      (usa las variables `ADMIN_EMAIL`, `ADMIN_NOMBRE`, etc. de tu
      `.env`) — no hay pantalla para el primer usuario, es
      intencional (bootstrap).
- [ ] Frontend SSALFER sirviendo y `CORS_ORIGINS` / `env.js`
      configurados como en `DEPLOY.md`.
- [ ] Inicia sesión en `Index.html`. Confirma en `dashboard.html`
      que tu nombre real aparece en "Bienvenido" (ya no debe decir
      "Carlos Pérez" ni quedarse en blanco).


## 1. Proyecto

**Pantalla:** `pages/nuevoProyecto.html`
**Endpoint:** `POST /proyectos`

Campos que el backend exige: `nombre_proyecto`, `clave_proyecto`
(máx. 30 caracteres — si el formulario te deja escribir más, es un
bug ya conocido, ver `ENTREGA.md`). `fecha_inicio`/`fecha_fin` y
`descripcion` son opcionales.

- [ ] Crea el proyecto. Debe regresar `201` y redirigir a
      `pages/fichaProyecto.html?id=<idProyecto>`.
- [ ] En `fichaProyecto.html`, confirma que el nombre, clave y
      vigencia mostrados son los que capturaste (no "AIFA - Pachuca").
- [ ] Confirma que aparece en el sidebar de **cualquier otra
      página** (antes eran 3 proyectos fijos) y en las tarjetas de
      `dashboard.html`.
- [ ] Anota `idProyecto`.


## 2. Núcleo agrario (dos pasos: crear el núcleo maestro, luego vincularlo al proyecto)

El backend separa el **núcleo agrario** (catálogo maestro,
reutilizable entre proyectos) de su **vínculo con un proyecto**
(`ProyectoNucleo`). El frontend no tiene una pantalla separada para
"crear núcleo maestro" — revisa si `nucleoAgrario.html` ya lo
resuelve en un solo formulario (llama primero a `POST /nucleos` y
luego a `POST /proyectos/{id}/nucleos`) o si falta ese primer paso;
si falta, es un hueco a reportar, no algo que debas rellenar a mano
vía Swagger salvo para destrabar la prueba.

**Endpoints:**
- `POST /nucleos` → requiere `id_municipio` (catálogo), `nombre_nucleo`,
  `id_tipo_tenencia` (catálogo). Regresa `id_nucleo`.
- `POST /proyectos/{idProyecto}/nucleos` → requiere `id_nucleo` (el
  del paso anterior). Regresa `id_proyecto_nucleo`.

- [ ] Crea/vincula el núcleo desde la pantalla correspondiente.
- [ ] Verifica que `fichaProyecto.html?id=<idProyecto>` ya muestra
      este núcleo en la cuadrícula, con contadores en cero (0
      parcelas, 0 afectaciones) — si muestra otra cosa, hay datos
      cacheados o mal referenciados.
- [ ] Entra a la ficha del núcleo. Anota `idProyectoNucleo`.


## 3. Persona (necesaria para asamblea/ORV/titulares más adelante)

**Pantalla:** `pages/persona.html`
**Endpoint:** `POST /proyectos/{idProyecto}/personas`

Solo `nombre` es obligatorio; `curp`/`rfc` tienen límite de longitud
(18 y 13 caracteres respectivamente — si el formulario no valida
esto client-side, el backend lo rechazará con `422`).

- [ ] Da de alta 2-3 personas (te van a servir como comparecientes
      de convenio, integrantes de ORV y titulares).
- [ ] **Nota de alcance ya documentada:** no existe `GET /personas`
      general — solo puedes verlas embebidas donde el backend las
      expone (titulares, integrantes de ORV, comparecientes). Si el
      formulario de persona muestra un listado general, sería
      inventado; repórtalo.


## 4. Asamblea (para el camino colectivo)

**Pantalla:** `pages/asamblea.html?id_proyecto_nucleo=<idProyectoNucleo>`
**Endpoint:** `POST /proyecto-nucleo/{idProyectoNucleo}/asambleas`

Obligatorio: `id_tipo_asamblea` (catálogo). Si mandas
`convocatorias`, cada una necesita `ordinal` único (no puede haber
dos convocatorias con el mismo ordinal — el backend lo rechaza con
`422` y el mensaje "Los ordinales de convocatoria no pueden
repetirse").

- [ ] Crea la asamblea con al menos una convocatoria.
- [ ] Anota `idAsamblea`.
- [ ] Verifica que el link "Registrar asamblea" desde
      `nucleoAgrario.html` te trajo aquí con el `id_proyecto_nucleo`
      correcto en la URL (bug ya corregido en una pasada anterior,
      vale la pena reconfirmar).


## 5. Trámite RAN desde la asamblea

**Pantalla:** el flujo ya conectado desde `asamblea.html` (o
directo a `POST /tramites-ran`).

Regla dura del backend (constraint de base de datos, no solo
validación de Pydantic): un trámite RAN debe tener
**exactamente uno** de `id_asamblea` / `id_convenio` / `id_orv`, ni
cero ni dos. Si el formulario permite mandar dos a la vez, o
ninguno, el backend debe rechazarlo con `422` — confirma que sí lo
hace (es una prueba negativa útil).

- [ ] Crea un trámite RAN con `id_asamblea = idAsamblea` del paso 4.
- [ ] Prueba negativa: intenta forzar (si tienes acceso a
      `/docs` de FastAPI) un trámite con `id_asamblea` **e**
      `id_convenio` a la vez → debe regresar `422`.


## 6. Parcela + titular (para el camino individual)

**Pantalla:** `pages/parcela.html?id_proyecto_nucleo=<idProyectoNucleo>`
**Endpoints:**
- `POST /proyecto-nucleo/{idProyectoNucleo}/parcelas` → requiere
  `tipo_parcela` (`individual` | `copropiedad` | `otro` |
  `no_determinado`).
- `POST /parcelas/{idParcela}/titulares`

- [ ] Crea una parcela y al menos un titular.
- [ ] Anota `idParcela`.


## 7. Unidad agraria + titular

**Pantalla:** `pages/unidadAgraria.html?id_proyecto_nucleo=<idProyectoNucleo>`
**Endpoint:** `POST /proyecto-nucleo/{idProyectoNucleo}/unidades-agrarias`

Obligatorio: `id_tipo_tierra`, `id_tipo_titularidad` (catálogos).
`id_parcela` es opcional (una unidad agraria puede o no estar ligada
a una parcela específica).

Para el titular (`POST /unidades-agrarias/{id}/titulares`): el
backend exige **exactamente uno** de `id_persona` /
`id_parcela_titular`, nunca los dos ni ninguno — mismo patrón de
validación que el trámite RAN, buena prueba negativa también.

- [ ] Crea la unidad agraria, ligada a la parcela del paso 6 si
      quieres probar esa relación.
- [ ] Anota `idUnidadAgraria`.


## 8. Afectación (colectiva o individual)

**Pantalla:** `pages/afectacion.html?id_proyecto_nucleo=<idProyectoNucleo>`
**Endpoint:** `POST /proyecto-nucleo/{idProyectoNucleo}/afectaciones`

- [ ] Antes de crear nada, confirma que el listado que ya existía
      en esta pantalla (corregido en la última pasada) carga
      **vacío** para este núcleo, no las 3 tarjetas de ejemplo
      viejas (AF-001/002/003 con montos inventados). Si las ves,
      quedó código cacheado del navegador — refresca forzado
      (Ctrl+Shift+R).
- [ ] Crea una afectación `individual`.
- [ ] Crea una afectación `colectivo`.
- [ ] Confirma que ambas aparecen en la cuadrícula con estado
      "Pendiente" (no tienen avalúo ni superficie afectada real
      todavía) y que los contadores del resumen (total/completas/
      pendientes/superficie) se actualizaron.
- [ ] Entra a `detalleAfectacion.html?id=<idAfectacion>` de una de
      ellas. Anota `idAfectacion`.
- [ ] En "Continuar captura", agrega situación y superficie
      afectada real → Guardar. Confirma que el badge de estado y el
      texto de la sección "Información general" cambian sin
      recargar la página.
- [ ] En "Capturar avalúo", registra monto/fecha/institución →
      Guardar. Confirma que la tarjeta de afectación en
      `afectacion.html` ahora muestra "Completa" si también
      capturaste superficie afectada (criterio: situación +
      superficie afectada + avalúo, los tres presentes).
- [ ] Vincula la unidad agraria del paso 7 a esta afectación
      (botón "Agregar unidad" → te debe mandar a `unidadAgraria.html`
      con `id_proyecto_nucleo` **e** `id_afectacion` en la URL).
      Regresa a `detalleAfectacion.html` y confirma que aparece en
      "Unidades agrarias relacionadas".


## 9. Convenio desde la afectación

**Pantalla:** `pages/nuevoConvenio.html?id_afectacion=<idAfectacion>`
**Endpoint:** `POST /afectaciones/{idAfectacion}/convenios`

Reglas de validación reales a probar (todas del backend, no del
formulario):
- `monto_90` no puede ser mayor que `monto_100` → prueba mandar
  90 > 100 y confirma que da `422`, no que se guarda silenciosamente.
- Si `tipo_convenio = cop_original`: no puede tener
  `id_convenio_padre`, y `estado_antecedente` solo puede ser
  `no_aplica` o vacío.
- Si `modalidad_especial = permuta`: solo es válida junto con
  `tipo_convenio = cop_original`.
- Si mandas `id_convenio_padre`, `estado_antecedente` debe ser
  `vinculado`.
- Los comparecientes van **anidados** en el mismo payload de
  creación (no es una llamada aparte) — confirma en la pestaña
  Network que solo se hace un `POST`, no un `POST` + varios más.

- [ ] Crea un convenio `cop_original` simple, sin padre, con 1-2
      comparecientes (usa las personas del paso 3).
- [ ] Prueba negativa: intenta guardar con `monto_90` mayor que
      `monto_100` → confirma `422` y que el formulario te lo señala.
- [ ] Anota `idConvenio`. Verifica que aparece en la tabla de
      convenios de `detalleAfectacion.html`, con link a
      `fichaConvenio.html?id_convenio=<idConvenio>`.
- [ ] En `fichaConvenio.html`, confirma que los datos mostrados
      coinciden con lo capturado (no valores de ejemplo).


## 10. Indemnización y pagos

**Pantalla:** `pages/indemnizacion.html?id_afectacion=<idAfectacion>`
**Endpoints:**
- `POST /afectaciones/{idAfectacion}/indemnizacion`
- `POST /indemnizaciones/{idIndemnizacion}/pagos`

- [ ] Registra la indemnización.
- [ ] Regresa a `detalleAfectacion.html?id=<idAfectacion>` →
      confirma que la sección "Indemnización" ya no dice "Sin
      registro" y que el botón cambió a "Ver / continuar
      indemnización".
- [ ] Registra un pago desde `indemnizacion.html`.
- [ ] Confirma en `detalleAfectacion.html` que la tabla de "Pagos"
      ahora muestra ese pago real (antes decía "No hay pagos
      registrados" de forma fija).


## 11. FIFONAFE (a nivel núcleo, no afectación)

**Pantalla:** `pages/fifonafe.html?id_proyecto_nucleo=<idProyectoNucleo>`
**Endpoint:** `POST /proyecto-nucleo/{idProyectoNucleo}/fifonafe`

Obligatorio: `ids_afectacion` con **al menos un** id, todos
positivos y sin repetirse.

- [ ] Crea un trámite FIFONAFE incluyendo el `idAfectacion` del
      paso 8.
- [ ] Confirma que **no** aparece nada de esto en
      `detalleAfectacion.html` de esa afectación más que el aviso
      "el backend aún no expone una consulta de FIFONAFE por
      afectación" con el link a esta misma pantalla — es el
      comportamiento esperado (limitación real del backend, no un
      bug del frontend).


## 12. ORV

**Pantalla:** `pages/orv.html?id_proyecto_nucleo=<idProyectoNucleo>`
**Endpoints:**
- `POST /proyecto-nucleo/{idProyectoNucleo}/orv`
- `POST /orv/{idOrv}/integrantes` → requiere `id_persona`,
  `id_organo`, `id_cargo` (catálogos).

- [ ] Crea el ORV y agrega un integrante con una de las personas
      del paso 3.
- [ ] Intenta crear un segundo trámite RAN, ahora con
      `id_orv = idOrv` (en vez de `id_asamblea`) → debe funcionar
      igual que en el paso 5, confirmando que el mismo formulario/
      lógica maneja los tres objetivos posibles.


## 13. Reportes del proyecto

**Pantalla:** `pages/estadoFinanciero.html?id_proyecto=<idProyecto>`

- [ ] Con todo lo capturado arriba, confirma que:
  - La tarjeta "Convenios registrados" refleja al menos el convenio
    del paso 9 (puede tardar en aparecer si depende de un job/vista
    materializada — revisa si `vw_dashboard_kpi` se actualiza en
    tiempo real o por batch; si es por batch, es esperado que no se
    vea de inmediato, anótalo).
  - "Valor declarado en convenios" refleja los montos capturados.
  - Las tablas de avance de periodo / cobertura de impactos /
    FIFONAFE no truenan aunque estén vacías (deben decir "todavía no
    tiene... registrados", no quedarse en "Cargando…" para siempre
    ni mostrar un error).
- [ ] Dale clic a "Exportar CSV de este proyecto" → debe descargar
      un archivo (o abrirlo en el navegador) sin error 404/500.


## 14. Regresión general del dashboard

- [ ] `dashboard.html`: el proyecto del paso 1 aparece con
      contadores reales (núcleos/parcelas/afectaciones/superficie).
- [ ] El botón "Exportar dashboard (CSV)" también descarga sin
      error (esta vez sin filtrar por proyecto).
- [ ] Cierra sesión y vuelve a entrar con **otro** usuario (si
      tienes uno de prueba) → confirma que el nombre en "Bienvenido"
      cambia (para descartar que quedó cacheado el del primer
      usuario).


## 15. Qué NO vas a poder probar todavía (huecos declarados)

Estas partes del backend no tienen pantalla — no busques cómo
probarlas desde la interfaz, porque no existe. Si necesitas
verificarlas, es directo contra la API (por ejemplo desde
`/docs`, la interfaz Swagger que FastAPI genera automáticamente,
si está habilitada en tu entorno):

- Administración de usuarios (`/usuarios`, PATCH de bloqueo/rol).
- Catálogos operativos (alta/edición de opciones).
- Importaciones geoespaciales (shapefile/GeoJSON).
- Auditoría (`/auditoria/cambios`, `/auditoria/accesos`).


## 16. Al terminar

Si algo falló en un paso, antes de reportarlo revisa en la pestaña
**Network** del navegador:
1. ¿Qué URL exacta se llamó y con qué método?
2. ¿Qué código regresó (`422` = dato inválido según el backend,
   `404` = el recurso/ruta no existe, `401`/`403` = sesión o
   permisos, `500` = error del servidor, revisar logs del contenedor
   `backend` en Docker Desktop)?
3. ¿El `body` de la respuesta trae un mensaje de validación
   específico (Pydantic los da bastante claros, ej. "monto_90 no
   puede exceder monto_100")?

Con esos tres datos ya se puede diagnosticar si el problema es del
frontend (mandó algo mal armado) o una regla de negocio del backend
que el frontend todavía no refleja en la UI (por ejemplo, no avisa
antes de enviar que monto_90 no puede exceder monto_100).
