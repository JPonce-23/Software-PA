# Contrato y Especificación de la API — SOFTWARE-PA

> **Autoridad:** Especificación técnica del contrato de integración HTTP entre el cliente web (frontend) y el servidor de aplicaciones (backend).  
> **Alineación:** Referencia de backend y OpenAPI en `docs/openapi.json`; B-04 incorpora la migración `027` y B-03 la `028` al esquema canónico `001–028`.
> **Esquema de base de datos vigente:** **028** (`GET /health` responde `{"status": "ok", "schema": 28}` cuando la base consultada tiene 028 aplicada).

---

## 1. Principios Generales de Integración

1. **Consumo exclusivo vía REST HTTP JSON:**  
   El frontend consume exclusivamente los endpoints expuestos bajo el prefijo `/api`. No interactúa de forma directa con la base de datos PostgreSQL.
2. **Catálogos dinámicos:**  
   Nunca deben asumirse ni "hardcodearse" identificadores (`id_catalogo_opcion`) en el cliente. Los catálogos deben consultarse en tiempo de ejecución en:  
   `GET /api/catalogos/operativos/{tipo_catalogo}`
3. **Manejo de errores estandarizado:**  
   - `401 Unauthorized`: Sesión ausente, expirada, revocada o credenciales inválidas.
   - `403 Forbidden`: Origen no permitido en la protección CSRF, token CSRF inválido, rol insuficiente o proyecto fuera del alcance autorizado (incluido proyecto inactivo).
   - `404 Not Found`: Recurso inexistente o inactivo, según las comprobaciones de la ruta.
   - `409 Conflict`: Violación de invariantes de dominio, duplicidad de claves o concurrencia.
   - `422 Unprocessable Entity`: Cuerpos JSON o parámetros de consulta que violan los esquemas Pydantic.

---

## 2. Autenticación, Sesiones y Seguridad CSRF

El sistema implementa sesiones opacas en base de datos protegidas por cookies HTTP y un mecanismo estricto de doble envío CSRF. No se utilizan tokens Bearer ni JWT en `localStorage`.

### 2.1 Manejo de Cookies
- **Modo desarrollo (`AUTH_COOKIE_SECURE=false`):**  
  - Cookie de sesión: `pa_session_dev` (`HttpOnly`, `SameSite=Lax`).
  - Cookie CSRF: `pa_csrf_dev` (`SameSite=Lax`, accesible por JavaScript).
- **Modo producción (`AUTH_COOKIE_SECURE=true`):**  
  - Cookie de sesión: `__Host-pa_session` (`HttpOnly`, `Secure`, `SameSite=Lax`).
  - Cookie CSRF: `__Host-pa_csrf` (`Secure`, `SameSite=Lax`, accesible por JavaScript).

### 2.2 Requisitos para Peticiones Mutables
Para toda petición `POST`, `PUT`, `PATCH` o `DELETE` bajo `/api/`:
1. El cliente debe incluir la cabecera `Origin` correspondiente a un dominio permitido en `AUTH_SETTINGS.allowed_origins`.
2. Salvo el login `POST /api/auth/sesiones`, que valida únicamente el origen, el cliente con sesión debe leer la cookie CSRF y enviarla en `X-CSRF-Token`; el backend contrasta cookie, header y token de sesión. Sin cookie de sesión, la dependencia de autenticación rechaza la petición protegida.
3. Peticiones `GET` y `HEAD` no requieren validación CSRF.
4. El cliente debe configurar su librería HTTP con `credentials: "include"` (o `withCredentials: true` en Axios).

### 2.3 Endpoints de Autenticación (`/api/auth`)

| Método | Endpoint | Payload / Formato | Respuesta | Descripción |
|---|---|---|---|---|
| `POST` | `/api/auth/sesiones` | `application/x-www-form-urlencoded`<br>`username`, `password` | `200 OK`<br>`{ user, expira_en }` | Inicia sesión y establece cookies de sesión y CSRF. Si la contraseña excede 72 bytes UTF-8 o es inválida, responde genéricamente `401 Unauthorized` sin filtrar si el usuario existe. |
| `GET` | `/api/auth/sesion` | Vacío (envía cookies) | `200 OK`<br>`{ user, expira_en }` | Retorna los datos del usuario autenticado; `401` si la sesión no es válida. |
| `POST` | `/api/auth/logout` | Vacío (envía cookies) | `200 OK`<br>`{ detail }` | Revoca la sesión activa en base de datos y limpia las cookies del navegador. |
| `POST` | `/api/auth/logout-todas` | Requiere sesión y CSRF | `200 OK`<br>`{ detail }` | Revoca todas las sesiones abiertas del usuario en todos los dispositivos. |
| `POST` | `/api/auth/cambiar-contrasena` | JSON: `contrasena_actual`, `contrasena_nueva` | `200 OK`<br>`{ detail, sesiones_revocadas }` | Actualiza la contraseña personal y revoca todas las sesiones activas. |

### 2.4 Administración de Usuarios (`/api/usuarios`)
*Exclusivo para usuarios con rol `admin`. Requiere sesión activa; las operaciones mutables requieren CSRF.*

- `POST /api/usuarios`: Alta de nuevo usuario (`nombre`, `apellido_paterno`, `apellido_materno`, `correo`, `rol`, `contrasena`). Roles válidos: `admin`, `operador`, `visualizador`, `geografo`.
- `GET /api/usuarios`: Consulta paginada (`skip`, `limit`, `estado` ∈ `activos`, `inactivos`, `todos`).
- `PATCH /api/usuarios/{id_usuario}`: Modifica nombres, apellidos o rol. Previene degradar al último administrador activo.
- `PATCH /api/usuarios/{id_usuario}/correo`: Modifica correo y revoca las sesiones del usuario.
- `DELETE /api/usuarios/{id_usuario}`: Baja lógica obligatoria con cuerpo `{"motivo": "..."}`. Revoca sesiones activas y asignaciones.
- `POST /api/usuarios/{id_usuario}/reactivar`: Reactivación de cuenta con motivo.
- `POST /api/usuarios/{id_usuario}/desbloquear`: Desbloquea cuenta bloqueada por intentos fallidos.
- `POST /api/usuarios/{id_usuario}/restablecer-contrasena`: Asigna nueva contraseña administrativa y revoca sesiones.

---

## 3. Dominio Territorial y Operativo

### 3.1 Catálogo nacional de núcleos agrarios RAN

- `GET /api/catalogos/nucleos`: consulta acotada del catálogo nacional PHINA/RAN para usuarios con rol de lectura (`admin`, `operador`, `visualizador` o `geografo`).
- Filtros opcionales: `id_entidad`, `id_municipio` y `q` (coincidencia parcial por nombre normalizado sin distinguir mayúsculas/minúsculas).
- `limit` es opcional, vale `20` por defecto y admite de `1` a `100`.
- Sólo devuelve núcleos activos cuya `fuente_datos` es `RAN_PHINA_CATALOGO_NUCLEOS`; excluye altas manuales, seeds y QA.
- `id_entidad`, `entidad`, `id_municipio` y `municipio` se resuelven por las llaves foráneas internas `nucleo_agrario → municipio → entidad_federativa`.
- El orden es estable por nombre normalizado y `id_nucleo`.
- Cada registro expone: `id_nucleo`, `nombre_nucleo`, `id_tipo_tenencia`, `codigo_tipo_tenencia`, `tipo_tenencia`, `id_municipio`, `municipio`, `id_entidad`, `entidad` e `id_nucleo_fuente`.

### 3.2 Proyecto y Asignaciones
- `GET/POST /api/proyectos`: Administración de proyectos estratégicos.
- `GET/POST /api/proyectos/{id_proyecto}/nucleos`: Asocia un núcleo agrario al proyecto, creando la relación `ProyectoNucleo`.
- `GET /api/proyectos/{id_proyecto}/usuarios`: Exclusivo `admin`; lista únicamente relaciones `UsuarioProyecto` activas.
- `POST /api/proyectos/{id_proyecto}/usuarios`: Exclusivo `admin`; recibe `{"id_usuario": 42}` y crea una nueva relación con `201`. Requiere una cuenta activa; una asignación activa duplicada responde `409`.
- Los usuarios no administradores sólo pueden consultar recursos de proyectos que tienen asignados y cuyo proyecto permanezca activo (`activo = true`). La asignación autoriza acceso según el rol propio; no designa responsables del seguimiento ni responsables operativos. La figura funcional de responsable del seguimiento permanece en REVIEW.

#### Desasignación administrativa

`DELETE /api/proyectos/{id_proyecto}/usuarios/{id_usuario}` es exclusivo del rol `admin`. Requiere sesión autenticada, cookies, `Origin` permitido y cabecera `X-CSRF-Token`, conforme a la protección CSRF existente. El cuerpo JSON es obligatorio (`BajaRequest`); `motivo` se recorta y debe contener al menos 3 caracteres y como máximo 500.

```http
DELETE /api/proyectos/17/usuarios/42
Content-Type: application/json
Origin: http://localhost:5173
X-CSRF-Token: <token de la cookie CSRF>
Cookie: <cookies de sesión y CSRF>

{"motivo":"Reasignación administrativa de personal"}
```

Respuesta `200 OK` (`AuthOperationResponse`):

```json
{"detail":"Asignación desactivada"}
```

| HTTP | Condición |
|---|---|
| `401` | Sin autenticación o sesión inválida, conforme al flujo de sesión existente. |
| `403` | Rol distinto de `admin`, CSRF/origen inválido, o proyecto inexistente/inactivo (`Proyecto fuera del alcance autorizado`), según la convención de acceso vigente. |
| `404` | Usuario inexistente (`Usuario no encontrado`) o ausencia de relación activa para esa pareja (`Asignación activa no encontrada`). |
| `409` | Conflicto de integridad al persistir; la transacción se revierte. |
| `422` | Cuerpo/motivo ausente o inválido, motivo vacío, sólo espacios, menor de 3 caracteres útiles o mayor de 500. |

La operación desactiva exclusivamente la relación activa indicada, incluso si la cuenta objetivo ya está inactiva. Conserva la fila y sus fechas de creación/asignación; registra `activo=false`, `fecha_baja`, `id_usuario_baja`, `motivo_baja`, `actualizado_en` y `actualizado_por` en una transacción. El trigger existente genera un `UPDATE` en bitácora con actor y valores anteriores/nuevos. Los bloqueos de fila serializan bajas concurrentes; el índice único parcial sigue garantizando una sola asignación activa por pareja.

Después de la baja, GET deja de listar esa relación. En nuevas peticiones, el usuario no administrador pierde el acceso al proyecto, sus `ProyectoNucleo` y las operaciones asociadas; conserva el acceso a otros proyectos con asignación válida. La cuenta, su rol y sus sesiones globales no cambian. Los administradores mantienen su alcance global por rol.

Repetir DELETE sin una nueva asignación activa responde `404`, sin actualizar el registro histórico, sus timestamps ni su bitácora. El POST existente permite una reasignación mediante una **nueva fila activa con otro `id_usuario_proyecto`**, conservando todas las filas anteriores inactivas y sus datos de baja. No reactiva registros históricos ni concede permisos superiores al rol; reactivar una cuenta tampoco restaura asignaciones revocadas. Esta entrega no incorpora un endpoint de reactivación de asignaciones.

### 3.3 ProyectoNucleo
- Al crear o actualizar un `ProyectoNucleo`, los campos administrados incluyen:
  - `id_residencia`: Llave foránea hacia residencia regional de la PA.
  - `total_cops_planeados`: Meta numérica entera de convenios esperados.
  - `afecta_tuc`: Booleano triestado (`true`, `false`, `null`).
  - `id_motivo_no_afecta_tuc`, `motivo_no_afecta_tuc_detalle`.
  - `tuc_revision_pendiente`, `tuc_revision_detalle`.
- Sub-recursos asociados:
  - `GET/POST /api/proyecto-nucleo/{id_proyecto_nucleo}/referencias`: Claves históricas de tramo y consecutivos de control (`consecutivo`, `clave_tramo`, `numero_tramo`). Edición en `PATCH /api/referencias/{id_referencia}`.
  - `GET/POST /api/proyecto-nucleo/{id_proyecto_nucleo}/responsables`: Brigadistas y enlaces institucionales. Edición en `PATCH /api/responsables/{id_responsable}`.
  - `GET/POST /api/proyecto-nucleo/{id_proyecto_nucleo}/padrones`: Registro del padrón agrario oficial. Edición en `PATCH /api/padrones/{id_padron}`.

#### Integrantes ORV: vigencia e histórico administrativo

`GET /api/orv/{id_orv}/integrantes` conserva los roles de lectura `admin`,
`operador`, `visualizador` y `geografo`. Acepta dos booleanos, ambos `false`
por defecto:

| `incluir_historico` | `incluir_bajas` | Integrantes devueltos |
|---|---|---|
| false | false | Activos y funcionalmente vigentes |
| true | false | Todos los activos, sin filtro temporal |
| false | true | Activos vigentes y todas las bajas administrativas, sin filtrar fechas de las bajas |
| true | true | Todos los activos y todas las bajas administrativas |

Omitir `incluir_bajas` o enviarlo como `false` conserva los resultados anteriores.
La Persona debe estar activa incluso al consultar bajas. Se exige ORV activo,
núcleo activo y el acceso vigente al núcleo; no hay excepciones históricas para
padres inactivos o proyectos fuera del alcance. Admin conserva el alcance del
listado existente. Autenticación ausente: `401`; alcance no autorizado: `403`;
ORV o núcleo inexistente/inactivo: `404`; booleano inválido: `422`.

La respuesta sigue siendo `OrvIntegranteDetailResponse` y el orden sigue siendo
órgano, cargo y nombre. Una baja se identifica por `activo=false`, `vigente=false`,
`fecha_baja`, `motivo_baja` e `id_usuario_baja`. No se añade nombre, correo ni
perfil del actor. Ejemplo para localizar todas las bajas junto con el histórico
funcional: `GET /api/orv/42/integrantes?incluir_historico=true&incluir_bajas=true`.

`vigente` se calcula con el estado activo y las fechas propias del integrante,
con inicio y fin inclusivos. Un fin hoy o futuro puede seguir siendo vigente;
la vigencia del ORV padre no se incorpora a esta propiedad.

`POST /api/orv-integrantes/{id_orv_integrante}/finalizar` termina el periodo
funcional mediante `fecha_fin`, `id_tipo_fin` y `detalle_fin`, conservando
`activo=true`. Sigue disponible para admin y operador con captura autorizada.
`DELETE /api/orv-integrantes/{id_orv_integrante}` es una baja administrativa,
exclusiva de admin: conserva el periodo y registra los campos de baja.
`POST /api/orv-integrantes/{id_orv_integrante}/reactivar`, también exclusivo de
admin, restaura `activo=true` y limpia esos campos de baja; conserva el cierre
funcional y puede responder `409` por conflicto. No reabre un periodo finalizado.
Si el registro ya está activo responde `409`, tenga o no cierre. No existe una
operación de reapertura; una nueva participación se registra con el POST
existente del ORV, sujeto a la protección temporal vigente.

### 3.4 Parcelas y Derechos Individuales
- `GET/POST /api/proyecto-nucleo/{id_proyecto_nucleo}/parcelas`: Consulta y alta parcelaria dentro del proyecto-núcleo.
- `GET/PATCH /api/parcelas/{id_parcela}`: Consulta y actualización de datos de la parcela.
- `PATCH /api/parcelas/{id_parcela}/geometria`: Carga y actualización de geometría poligonal opcional.
- `GET/POST /api/parcelas/{id_parcela}/titulares`: Acreditación de titulares con `certificado_parcelario`, `folio_derechos` y `constancia_vigencia`. Edición en `PATCH /api/parcela-titulares/{id_parcela_titular}`.
- **Regla canónica:** La parcela se identifica exclusivamente mediante `no_parcela`. **No existen en el contrato API los campos `no_parcela_ppt` ni `numero_parcela_ppt`**.
- La geometría (`geometria_poligono`) es opcional y su ausencia no restringe ninguna operación de negocio.

#### Acceso a Persona y datos compartidos

`GET /api/personas` busca Personas activas dentro del alcance de lectura del
usuario. Admite los roles `admin`, `operador`, `visualizador` y `geografo`.
Debe enviarse **exactamente uno** de `q`, `curp` o `rfc`; la ausencia de criterio,
los valores vacíos o la combinación de criterios producen HTTP `422`.

- `q`: entre 2 y 300 caracteres después de retirar espacios ordinarios exteriores.
  Se divide en palabras: todas deben aparecer en alguno de `nombre`,
  `apellido_paterno` o `apellido_materno`, sin depender del orden ni distinguir
  mayúsculas. No elimina acentos: `PEREZ` no equivale a `PÉREZ`. `%`, `_` y `\`
  se comparan literalmente; no hay búsqueda fuzzy.
- `curp`: valor no vacío, máximo 18 caracteres después de retirar espacios
  ordinarios exteriores y convertir a mayúsculas; igualdad contra
  `upper(btrim(curp))`. No admite búsqueda parcial ni exige 18 caracteres.
- `rfc`: misma comparación por igualdad, máximo 13 caracteres normalizados.
  No supone unicidad. La normalización sólo se usa para comparar; no cambia
  datos almacenados ni la persistencia de POST/PATCH.
- `limit`: predeterminado 20, entre 1 y 100; `skip`: predeterminado 0, mínimo 0.

Devuelve una lista con únicamente `id_persona`, `nombre`, `apellido_paterno`,
`apellido_materno`, `curp` y `rfc`; apellidos e identificadores admiten `null`.
Ordena por apellidos, nombre e id, sin distinguir caja y con apellidos nulos
al final. Aplica visibilidad antes de paginar y no duplica Personas compartidas.

Admin encuentra todas las Personas activas. Los demás roles sólo encuentran
Personas relacionadas con algún proyecto activo autorizado, más la excepción
del creador operador descrita abajo. Una referencia activa con padre inactivo
no convierte a la Persona en huérfana recuperable por el creador. Las Personas
inactivas se excluyen para todos, incluido admin. Una coincidencia fuera de
alcance devuelve `200 []`, igual que una búsqueda sin resultados; no revela id
ni existencia. Autenticación ausente: `401`; rol no admitido: `403`.

Ejemplos: `GET /api/personas?q=Juan%20P%C3%A9rez&limit=20&skip=0` y
`GET /api/personas?curp=ABCD1234`. Buscar o seleccionar no crea relaciones.
La vinculación posterior vuelve a comprobar permisos y reglas de negocio.
El conflicto de creación conserva `409 {"detail":"La persona ya existe"}`
sin devolver identidad; buscar previamente no sustituye la restricción SQL.

`GET /api/personas/{id_persona}` requiere lectura y un proyecto autorizado
vinculado mediante ORV, titularidad parcelaria, titularidad de unidad agraria
(directa o por titular parcelario), comparecencia en convenio, intervención
FIFONAFE o pago de indemnización. Se comprueba el estado activo de la relación
y sus padres; una asignación a otro proyecto no basta para acceder.

`PATCH /api/personas/{id_persona}` modifica campos globales compartidos y exige
al operador captura en **todos** los proyectos relacionados. Leer una persona
compartida no autoriza su edición ni da acceso a los demás proyectos. Admin
conserva lectura y edición global. Una referencia activa a un proyecto inactivo
no permite eludir esta condición mediante la excepción del creador.

Una persona sin referencias activas sólo es accesible a admin o a su creador
operador mientras éste conserve alguna asignación vigente. El creador puede
leer, editar y hacer la primera vinculación a un recurso con captura autorizada.
El POST `/api/proyectos/{id_proyecto}/personas` conserva su contrato y no crea
un vínculo implícito con ese proyecto. Las demás altas y cambios de referencias
validan previamente el acceso legítimo a Persona; no permiten incorporar una
persona fuera del alcance para obtener acceso indirectamente. La vinculación
exige lectura legítima de Persona y captura en el recurso destino, sin modificar
sus campos globales.

Fuera de alcance: `403 {"detail":"Persona fuera del alcance autorizado"}`;
registro inexistente/inactivo: `404 {"detail":"Persona no encontrada"}`.
Se conservan autenticación, permisos por rol y CSRF existentes. Estas reglas
fueron confirmadas para esta corrección; no introducen responsabilidades de
seguimiento ni asignaciones automáticas.

### 3.5 Actividades de Campo
- `GET/POST /api/proyecto-nucleo/{id_proyecto_nucleo}/actividades`: Registra sensibilizaciones y caminamientos del proyecto-núcleo.
- `PATCH /api/actividades/{id_actividad}`: Actualiza metadatos y resultado de la actividad.
- `tipo_actividad` admite únicamente `sensibilizacion` o `caminamiento`.
- Parámetros clave: `id_proyecto_nucleo`, `id_tipo_cop_operativo`, `fecha_programada`, `fecha_realizada`, `responsable`, `resultado`.

Desde 027, una actividad puede ser objetivo documental directo con las rutas genéricas:

- `GET /api/documentos/objetivos/actividad_campo/{id_actividad}`: lista documentos y vínculos activos.
- `POST /api/documentos/objetivos/actividad_campo/{id_actividad}`: crea metadatos `DocumentoCreate` y su vínculo; responde `201`.
- `POST /api/documentos/{id_documento}/vinculos/actividad_campo/{id_actividad}`: vincula un documento existente, comprobando acceso al documento y a la actividad.

La pertenencia se resuelve por `ActividadCampo → ProyectoNucleo → Proyecto`, sin depender de `id_afectacion`. Actividad inexistente/inactiva o ProyectoNucleo inactivo: `404`, `Objetivo documental no encontrado`. Proyecto inactivo o fuera del alcance: `403`, `Proyecto fuera del alcance autorizado`. Lectura: admin, operador, visualizador y geógrafo; captura: admin y operador, con asignación de proyecto para usuarios no administradores. Versiones, baja lógica y trazabilidad usan el mecanismo documental existente. `ExpedienteRequisito` conserva su contrato previo.

### 3.6 Asambleas y Convocatorias (Ruta Colectiva)
- `GET/POST /api/proyecto-nucleo/{id_proyecto_nucleo}/asambleas`: Consulta y crea la entidad colectiva de asamblea. El alta requiere `id_tipo_asamblea`; `id_tipo_cop_operativo`, `proposito`, `resultado` y la lista inicial de `convocatorias` son opcionales según AsambleaCreate.
- `PATCH /api/asambleas/{id_asamblea}`: Actualiza exclusivamente los metadatos de la asamblea.
- **Gestión de convocatorias hijas:** Se gestionan a través de `GET/POST /api/asambleas/{id_asamblea}/convocatorias`. Cada convocatoria contiene `ordinal` (1, 2, ...), `fecha_expedicion`, `fecha_programada`, `fecha_realizacion` y su `id_resultado` (`celebrada`, `no_verificativo`, `cancelada`, etc.). Edición individual en `PATCH /api/convocatorias/{id_convocatoria}`.

### 3.7 Convenios de Ocupación Previa (COP)
- `GET/POST /api/afectaciones/{id_afectacion}/convenios`: Consulta y alta de convenios asociados a la afectación.
- `GET/PATCH /api/convenios/{id_convenio}`: Consulta y actualización de metadatos directos del convenio. **Rechaza colecciones anidadas**; las afectaciones y comparecientes se gestionan en sus endpoints hijos:
  - `GET/POST /api/convenios/{id_convenio}/afectaciones`: Asocia afectaciones y define `efecto_superficie` (`adicion`, `sustitucion`, `correccion`, `sin_cambio`, `pendiente`) y `superficie_impacto_ha` opcional. Edición en `PATCH /api/convenio-afectaciones/{id_convenio_afectacion}`.
  - `GET/POST /api/convenios/{id_convenio}/comparecientes`: Asocia sujetos firmantes. Edición en `PATCH /api/convenio-comparecientes/{id_compareciente}` y baja en `DELETE /api/convenio-comparecientes/{id_compareciente}`.
- **Precisión numérica obligatoria:** Las superficies (`superficie_ha`) admiten hasta 7 decimales. El cliente debe transmitirlas como números decimales sin redondear a 6 posiciones.

---

## 4. Trámites Registrales ante el RAN (`/api/tramites-ran`)

- `POST /api/tramites-ran`: Crea un expediente registral. Debe especificar **exactamente uno** de los siguientes objetivos:
  - `id_asamblea` (RAN del acta de asamblea)
  - `id_convenio` (RAN del convenio COP)
  - `id_orv` (RAN del acta de elección de mesa directiva)
  Junto con `fecha_programada_ingreso`, `referencia_expediente` y una lista inicial de eventos.
- `GET/PATCH /api/tramites-ran/{id_tramite_ran}`: Consulta y modificación **únicamente de la programación del trámite** (`fecha_programada_ingreso`). Los campos estructurales (`id_asamblea`, `id_convenio`, etc.) y sus eventos son inmutables por este método.
- **Eventos registrales:** Se consultan y añaden en `GET/POST /api/tramites-ran/{id_tramite_ran}/eventos`. Edición en `PATCH /api/eventos-ran/{id_evento_ran}`. Tipos: `ingreso`, `prevencion`, `subsanacion`, `calificacion`, `inscripcion`, `reingreso`. La calificación intermedia no equivale a inscripción; el hito de inscripción sólo procede del tipo `inscripcion`.

---

## 5. Procedimiento FIFONAFE (`/api/fifonafe`)

- `GET/POST /api/proyecto-nucleo/{id_proyecto_nucleo}/fifonafe`: Consulta y alta de solicitud de fondos asociada a `ProyectoNucleo`. El alta requiere `ids_afectacion`; `ambito` (`colectivo` o `individual`) se deriva de esas afectaciones, no es un selector en TramiteFifonafeCreate.
- `PATCH /api/fifonafe/{id_tramite_fifonafe}`: Actualiza metadatos del trámite.
- `POST /api/fifonafe/{id_tramite_fifonafe}/afectaciones`: Asocia afectaciones amparadas por la solicitud.
- Las nuevas solicitudes nacen en `version_flujo = 2`.
- `GET/POST /api/fifonafe/{id_tramite_fifonafe}/eventos`: Registro de eventos del catálogo `tipo_evento_fifonafe`, incluidos los cuatro oficios históricos y los eventos de solicitud, consulta por ronda, respuesta, resolución, entrega y comprobación del flujo v2. Cuatro oficios no bastan para completar v2; véase MODELO_FUNCIONAL.md §9.4 y la validación existente de 008. Edición en `PATCH /api/eventos-fifonafe/{id_evento_fifonafe}` y baja en `DELETE /api/eventos-fifonafe/{id_evento_fifonafe}`.
- `GET/POST /api/fifonafe/{id_tramite_fifonafe}/intervinientes`: Registro de partes interesadas. Baja en `DELETE /api/intervinientes-fifonafe/{id_interviniente_fifonafe}`. **Acreditación de integrantes de ORV:** El registro de un `id_orv_integrante` requiere obligatoriamente enviar un `id_evento_fifonafe` (responde `422` si se omite) y valida que el integrante pertenezca al ORV del núcleo y tenga vigencia en la fecha del acto (responde `409 Conflict` en caso de incompatibilidad).

---

## 6. Indemnizaciones y Pagos

- `GET/POST /api/afectaciones/{id_afectacion}/indemnizacion`: Consulta y registro por afectación, colectiva o individual. Atributos: `estatus`, `descripcion_estatus`, `fecha_programada`, `fecha_resolucion`, `fecha_entrega_expediente_pa`; no existe `monto_total` en Indemnizacion. Estatus admitidos: `pendiente`, `programado`, `en_proceso`, `completo`, `pagado`, `cancelado`, `otro` (este último requiere descripción). Edición en `PATCH /api/indemnizaciones/{id_indemnizacion}`. `pagado` no crea un Pago ni proporciona una fecha de resolución.
- `GET/POST /api/indemnizaciones/{id_indemnizacion}/pagos`: Consulta y registro de liquidaciones efectivas. Requiere `fecha_pago`, `monto` y `beneficiario_nombre`. Edición en `PATCH /api/pagos/{id_pago}`. Cada pago activo genera un hito propio en los reportes de avance y tableros (`indicador = 'pagos'`).

---

## 7. Seguimiento Funcional y Contingencias (`/api/seguimiento`)

Módulo append-oriented para registrar la no linealidad operativa:
- `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/seguimiento`: Consulta la cronología de eventos de un núcleo.
- `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/seguimiento`: Inserta un evento indicando `ambito`, `id_tipo_evento`, `id_motivo` opcional, entidad objetivo opcional (`entidad_tipo`, `entidad_id`), `fecha_evento`, `detalle` y `fuente`.
- `GET/PATCH /api/seguimiento/{id_seguimiento_evento}`: Consulta y edición del evento.
- `DELETE /api/seguimiento/{id_seguimiento_evento}`: Baja lógica obligatoria enviando `{"motivo": "..."}`.
- Catálogo `tipo_evento_seguimiento`: `inicio`, `suspension`, `reapertura`, `cierre`, `cambio_alcance`, `reunion`, `negociacion`, `consulta_indigena`, `continuacion_asamblea`, `medicion_bdt`, `otro`.
- Catálogo `motivo_seguimiento`: `expropiacion_directa`, `no_afectacion`, `comunidad_indigena`, `dominio_pleno`, `juicio_agrario`, `conflicto_titularidad`, `rechazo`, `cambio_trazo`, `nueva_informacion`, `calificacion_negativa`, `falta_pago`, `otro`.

---

## 8. Reporting y Tableros Ejecutivos

Todos los endpoints de reporting filtran y excluyen automáticamente los proyectos con `activo IS NOT TRUE`.

### 8.1 Avance Periódico (`GET /api/reportes/avance-periodo`)
Desglose estructurado en 15 columnas con filtros dimensionales completos:
- **Filtros admitidos:** `id_proyecto`, `id_entidad`, `ambito` (`colectivo`, `individual`), `tipo_cop_operativo`, `tipo_convenio`, `destino_superficie`, `anio`, `mes`, `trimestre`, `indicador`.
- **Estructura de respuesta:** Arreglo de objetos con las 15 columnas canónicas:
  `id_proyecto`, `id_entidad`, `ambito`, `tipo_cop_operativo`, `tipo_convenio`, `destino_superficie`, `anio`, `mes`, `trimestre`, `indicador`, `programado`, `realizado`, `cantidad`, `superficie_ha`, `monto`.

### 8.2 Tablero de Control Anual (`GET /api/dashboard/kpi`)
Resumen ejecutivo anual deduplicado en origen por `id_proyecto, anio, indicador`. Previene la multiplicación de cifras por relaciones N:M.

### 8.3 Snapshot de Estado Actual (`GET /api/reportes/resumen-actual`)
Refleja el estado presente acumulado sin dimensión temporal:
- **Filtros admitidos:** `id_proyecto`, `id_entidad`, `ambito`, `indicador`, `tipo_cop_operativo`, `destino_superficie`.
- **Regla estricta:** No admite año, mes ni trimestre.

### 8.4 Convenios Colectivos por Destino (`GET /api/reportes/convenios/colectivos-destino`)
Detalle de convenios colectivos desglosados por destino de suelo:
- Expone `superficie_ha` (física), `superficie_declarada_ha` (instrumento) y `monto_declarado`.
- **Regla de no aditividad:** `monto_declarado` pertenece al convenio entero y **NO DEBE SUMARSE** entre filas con diferentes destinos para un mismo instrumento.

### 8.5 Mapa por Proyecto (`GET /api/proyectos/{id_proyecto}/mapa`)

Devuelve un GeoJSON `FeatureCollection` en EPSG:4326. Mantiene los roles de lectura
(`admin`, `operador`, `visualizador`, `geografo`) y la autorización por proyecto.
Cada feature conserva `id = "{tipo}:{id}"` y las propiedades `tipo`, `id`, `nombre`.

- `nucleo_agrario`: geometría activa y vigente de `proyecto_nucleo_geometria` para
  el ProyectoNucleo activo, con núcleo activo. Sin esa geometría, utiliza el campo
  global legacy del núcleo; el ID de la feature sigue siendo `id_nucleo`.
- `parcela`: geometría activa y vigente de `proyecto_parcela_geometria` para
  `ProyectoNucleo + Parcela`, con fallback global legacy sólo si falta la vigente.
  En ambos casos exige pertenencia administrativa activa mediante
  `vw_gis_parcela_proyecto`; compartir núcleo no basta. El ID sigue siendo `id_parcela`.
- `derecho_via_proyecto`: DDV poligonal activo y vigente del proyecto; el ID es
  `id_derecho_via` y `nombre` es la versión convertida a texto.
- `trazo_proyecto`: trazo lineal legacy activo del proyecto, como capa independiente
  del DDV; conserva `id_trazo` y la versión como nombre.

Las geometrías de otros proyectos y las versiones no vigentes de núcleo/parcela/DDV
no se publican. Staging sin confirmación no se publica. El endpoint sólo lee:
no crea registros administrativos ni modifica superficies, convenios o pagos.
La corrección B-07 utiliza el esquema existente y no añade migraciones ni endpoints.
Las áreas GIS y `ST_Area` son métricas auxiliares/cartográficas: no representan
superficie oficial ni sustituyen `superficie_afectada_ha` o `superficie_ha`.

La conciliación vigente utiliza `conciliacion-v3-historia`, identificada en
`gis_history.ALGORITHM`. `conciliacion-v2` corresponde al contrato histórico de
025; el linaje canónico actual termina en 028.

---

## 9. Salud del Sistema

- `GET /health` (Tag: `Sistema`):  
  Comprueba la conectividad con PostgreSQL y retorna el número de la última migración aplicada:
  ```json
  {
    "status": "ok",
    "schema": 28
  }
  ```

- `GET /`:  
  Retorna los metadatos del servicio:
  ```json
  {
    "service": "SOFTWARE-PA",
    "model": "ProyectoNucleo",
    "version": "2.0.0"
  }
  ```

## 10. Clasificación documental (B-03, esquema 028)

### Catálogo

`GET /api/catalogos/tipos-documento?incluir_inactivos=false` permite lectura a admin,
operador, visualizador y geógrafo. Devuelve, sin paginación, únicamente
`id_tipo_documento`, `codigo`, `nombre`, `descripcion`, `orden` y `activo`.
Por defecto sólo incluye opciones activas; `incluir_inactivos=true` también incluye
las bajas. Orden: activo descendente, orden, nombre, código e ID. Un booleano
inválido produce `422`. No existe CRUD público del catálogo.

### Captura y compatibilidad

`POST /api/documentos/objetivos/{entidad_tipo}/{entidad_id}` conserva permisos y
vínculos existentes. Debe recibir **exactamente uno** de `id_tipo_documento` o
`tipo_documento`, además de los metadatos existentes (`estado` requerido).

- Un ID existente y activo crea la FK y rellena el texto de compatibilidad con el
  **nombre** del catálogo: ACTA_ASAMBLEA produce `"Acta de asamblea"`.
  Durante la coexistencia el nombre debe caber en los 80 caracteres del campo
  legado; todos los nombres de la taxonomía V1 cumplen ese límite.
- Un texto legado válido crea el documento con FK NULL y conserva exactamente el
  texto enviado (máximo 80 caracteres, sin normalización).
- Ambos selectores, ninguno, NULL explícito, texto vacío/sólo espacios, ID
  inexistente o inactivo producen `422`.
- OTRO exige `descripcion` no NULL y con contenido distinto de espacios ordinarios;
  se valida antes de persistir y también en PostgreSQL. La descripción se conserva
  tal como se recibe.

`PATCH /api/documentos/{id_documento}` conserva permisos existentes:

- Omitir ambos selectores no cambia la clasificación.
- `id_tipo_documento` permite clasificar o reclasificar usando una opción activa;
  siempre conserva el `tipo_documento` anterior, incluidos los históricos.
- El texto legado sólo puede actualizarse mientras la FK sea NULL.
- No se permite quitar la clasificación ni enviar NULL explícito en un selector.
  Tampoco se permiten ambos selectores en el mismo PATCH; estos casos producen `422`.
- Una clasificación inactiva sigue siendo legible y permite editar otros
  metadatos. Seleccionarla de nuevo o reclasificar hacia ella produce `422`.
- Si la clasificación final es OTRO, la descripción final debe seguir siendo válida,
  tanto si se recibe en ese PATCH como si se conserva la anterior.

### Lectura e históricos

`DocumentoResponse` conserva sus campos y añade `id_tipo_documento` nullable y
`clasificacion` nullable. Esta última expone sólo ID, código, nombre y activo;
la descripción del tipo se consulta en el endpoint del catálogo.
La clasificación es autoritativa cuando existe FK. Los históricos conservan
`tipo_documento` original, `id_tipo_documento=null` y `clasificacion=null`; no se
infiere una clasificación por semejanza del texto y 028 no realiza backfill.
No cambian `estado`, requisitos, actividades, versiones ni objetivos documentales.
La taxonomía V1 completa se describe en el diccionario de datos.


## 11. Proyecciones de lectura para el frontend (esquema 028)

Estas proyecciones no requieren migración ni cambian Excel-First, reglas de
negocio, permisos o escrituras. Conservan los cuatro roles de lectura y el
alcance por proyecto de las rutas existentes.

### 11.1 Actor GIS

Los IDs existentes se conservan. Las respuestas añaden sólo el nombre completo
obtenido de Usuario, sin correo, rol, número de empleado ni datos laborales:

| Respuesta | Campo opcional añadido |
|---|---|
| Decisiones de feature y de revisión | `creado_por_nombre` |
| Ciclos, incluidos detalle y reconciliar | `usuario_nombre` |
| Revisiones, incluidos listado y detalle | `creado_por_nombre` |
| Candidatos | `usuario_revision_nombre` |

Los nombres se consultan en bloque, incluidos actores históricos inactivos;
son nombres actuales del directorio, no snapshots. Si no existe actor se devuelve
`null`. No se modifica Usuario ni se crea vínculo con Responsable.

### 11.2 Documentos por ProyectoNucleo

`GET /api/proyecto-nucleo/{id_proyecto_nucleo}/documentos` devuelve una lista de
procedencias, de sólo lectura. Cada fila contiene `entidad_tipo`, `entidad_id`,
`origen` legible derivado (o tipo + ID), `fuente_relacion`,
`id_documento_vinculo`, `id_expediente_requisito`, `documento` con el contrato
DocumentoResponse actual y `version_vigente` con DocumentoVersionResponse o
`null`. La versión vigente es la de mayor `numero_version` existente; no existe
una nueva marca de vigencia ni se expone la ruta de almacenamiento.

Incluye vínculos activos de documentos activos del propio ProyectoNucleo,
afectaciones, actividades, asambleas/convocatorias, convenios/comparecientes,
trámites RAN/eventos, FIFONAFE/eventos/intervinientes, indemnizaciones, pagos y
requisitos, siguiendo sólo sus relaciones existentes y padres activos.
También incluye objetivos compartidos del núcleo: núcleo, ORV, padrón, parcelas,
unidades agrarias y titulares, conforme al alcance documental actual. Un núcleo
compartido nunca incorpora registros propiedad de otro ProyectoNucleo.

Una referencia directa de ExpedienteRequisito se presenta como una procedencia
adicional (`fuente_relacion = "expediente_requisito"`, tipo e ID del requisito),
únicamente si el documento tiene además un vínculo activo dentro del alcance.
La referencia por sí sola no otorga acceso. Una fila por vínculo o referencia
conserva las distintas procedencias de un mismo documento; no duplica documentos
persistidos ni devuelve vínculos de otros proyectos. No modifica requisitos,
archivos, objetivos, carpetas ni metadatos. Las consultas se realizan en bloque.

Autorización: reutiliza `require_document_target_access` y
`project_ids_for_document_target`; un ProyectoNucleo inexistente/inactivo produce
404 y un proyecto no autorizado/inactivo produce 403.

### 11.3 Destinos GIS legibles

Las revisiones añaden `destino` opcional con `nombre_nucleo`, `municipio`,
`entidad`, `numero_parcela`, derivados con una consulta por página. DDV sin
ProyectoNucleo y observaciones sin destino devuelven `destino = null`.
No se cambian IDs, matching, métricas, ST_Area o conciliación.

Los candidatos conservan sus IDs de ciclo/destino. **No se añaden copias de
etiquetas a cada candidato:** `universo_destinos` del ciclo ya contiene
`nombre_nucleo`, `municipio`, `entidad` y `numero_parcela`. Obtener
`GET /api/importaciones/{id_importacion}/conciliaciones/{id_ciclo}` permite
mostrar todos sus candidatos usando un índice por
`(id_proyecto_nucleo, id_parcela)`, sin consultas por fila, y conserva las
etiquetas históricas del snapshot. El detalle consulta candidatos y decisiones
en bloque, con un número de consultas independiente de la cantidad de features.

### 11.4 Totales GIS

Los siguientes GET mantienen el array JSON, parámetros, orden y límites actuales,
y añaden el header `X-Total-Count` antes de aplicar `skip/limit`:

- `/api/proyectos/{id_proyecto}/importaciones` (sólo activas del proyecto).
- `/api/importaciones/{id_importacion}/features` (incluye `estado_conciliacion`).
- `/api/importaciones/{id_importacion}/conciliaciones` (ciclos de la importación).
- `/api/proyectos/{id_proyecto}/geoespacial/revisiones` (incluye estado, tipo,
  objetivo, ProyectoNucleo y rango de fechas).

El total reutiliza exactamente los filtros del listado autorizado, incluso cuando
la página es vacía. CORS expone `X-Total-Count` a los orígenes ya permitidos.
OpenAPI documenta el header; no se añade paginación donde no existía.
