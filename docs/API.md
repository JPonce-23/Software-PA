# Contrato y Especificación de la API — SOFTWARE-PA

> **Autoridad:** Especificación técnica del contrato de integración HTTP entre el cliente web (frontend) y el servidor de aplicaciones (backend).  
> **Alineación:** Validado contra `backend/app/routers/`, `schemas.py`, `services/`, migraciones `001–015` y el esquema OpenAPI formal en `docs/openapi.json`.  
> **Esquema de base de datos vigente:** **015** (`GET /health` responde `{"status": "ok", "schema": 15}`).

---

## 1. Principios Generales de Integración

1. **Consumo exclusivo vía REST HTTP JSON:**  
   El frontend consume exclusivamente los endpoints expuestos bajo el prefijo `/api`. No interactúa de forma directa con la base de datos PostgreSQL.
2. **Catálogos dinámicos:**  
   Nunca deben asumirse ni "hardcodearse" identificadores (`id_catalogo_opcion`) en el cliente. Los catálogos deben consultarse en tiempo de ejecución en:  
   `GET /api/catalogos/operativos/{tipo_catalogo}`
3. **Manejo de errores estandarizado:**  
   - `401 Unauthorized`: Sesión ausente, expirada, revocada o credenciales inválidas.
   - `403 Forbidden`: Origen CORS no permitido, token CSRF inválido o rol insuficiente.
   - `404 Not Found`: Recurso inexistente o proyecto fuera del alcance asignado al usuario.
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
2. El cliente debe leer el valor de la cookie CSRF y enviarlo en la cabecera HTTP `X-CSRF-Token`.
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
*Exclusivo para usuarios con rol `admin`. Requiere sesión activa y cabecera CSRF.*

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

### 3.1 Proyecto y Asignaciones
- `GET/POST /api/proyectos`: Administración de proyectos estratégicos.
- `GET/POST /api/proyectos/{id_proyecto}/nucleos`: Asocia un núcleo agrario al proyecto, creando la relación `ProyectoNucleo`.
- `GET/POST /api/proyectos/{id_proyecto}/usuarios`: Asigna operadores a proyectos (`UsuarioProyecto`). Los usuarios no administradores sólo pueden consultar recursos de proyectos que tienen asignados y cuyo proyecto permanezca activo (`activo = true`).

### 3.2 ProyectoNucleo
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

### 3.3 Parcelas y Derechos Individuales
- `GET/POST /api/proyecto-nucleo/{id_proyecto_nucleo}/parcelas`: Consulta y alta parcelaria dentro del proyecto-núcleo.
- `GET/PATCH /api/parcelas/{id_parcela}`: Consulta y actualización de datos de la parcela.
- `PATCH /api/parcelas/{id_parcela}/geometria`: Carga y actualización de geometría poligonal opcional.
- `GET/POST /api/parcelas/{id_parcela}/titulares`: Acreditación de titulares con `certificado_parcelario`, `folio_derechos` y `constancia_vigencia`. Edición en `PATCH /api/parcela-titulares/{id_parcela_titular}`.
- **Regla canónica:** La parcela se identifica exclusivamente mediante `no_parcela`. **No existen en el contrato API los campos `no_parcela_ppt` ni `numero_parcela_ppt`**.
- La geometría (`geometria_poligono`) es opcional y su ausencia no restringe ninguna operación de negocio.

### 3.4 Actividades de Campo
- `GET/POST /api/proyecto-nucleo/{id_proyecto_nucleo}/actividades`: Registra sensibilizaciones y caminamientos del proyecto-núcleo.
- `PATCH /api/actividades/{id_actividad}`: Actualiza metadatos y resultado de la actividad.
- `tipo_actividad` admite únicamente `sensibilizacion` o `caminamiento`.
- Parámetros clave: `id_proyecto_nucleo`, `id_tipo_cop_operativo`, `fecha_programada`, `fecha_realizada`, `responsable`, `resultado`.

### 3.5 Asambleas y Convocatorias (Ruta Colectiva)
- `GET/POST /api/proyecto-nucleo/{id_proyecto_nucleo}/asambleas`: Consulta y crea la entidad colectiva de asamblea. Requiere `id_tipo_asamblea`, `id_tipo_cop_operativo`, `proposito`, `resultado` y opcionalmente una lista inicial de `convocatorias`.
- `PATCH /api/asambleas/{id_asamblea}`: Actualiza exclusivamente los metadatos de la asamblea.
- **Gestión de convocatorias hijas:** Se gestionan a través de `GET/POST /api/asambleas/{id_asamblea}/convocatorias`. Cada convocatoria contiene `ordinal` (1, 2, ...), `fecha_expedicion`, `fecha_programada`, `fecha_realizacion` y su `id_resultado` (`celebrada`, `no_verificativo`, `cancelada`, etc.). Edición individual en `PATCH /api/convocatorias/{id_convocatoria}`.

### 3.6 Convenios de Ocupación Previa (COP)
- `GET/POST /api/afectaciones/{id_afectacion}/convenios`: Consulta y alta de convenios asociados a la afectación.
- `GET/PATCH /api/convenios/{id_convenio}`: Consulta y actualización de metadatos directos del convenio. **Rechaza colecciones anidadas**; las afectaciones y comparecientes se gestionan en sus endpoints hijos:
  - `GET/POST /api/convenios/{id_convenio}/afectaciones`: Asocia afectaciones y define el efecto (`adicion`, `sustitucion`, `correccion`, `sin_cambio`, `pendiente`). Edición en `PATCH /api/convenio-afectaciones/{id_convenio_afectacion}`.
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

- `GET/POST /api/proyecto-nucleo/{id_proyecto_nucleo}/fifonafe`: Consulta y alta de solicitud de fondos asociada a `ProyectoNucleo` y clasificada por `ambito` (`colectivo` o `individual`).
- `PATCH /api/fifonafe/{id_tramite_fifonafe}`: Actualiza metadatos del trámite.
- `POST /api/fifonafe/{id_tramite_fifonafe}/afectaciones`: Asocia afectaciones amparadas por la solicitud.
- Las nuevas solicitudes nacen en `version_flujo = 2`.
- `GET/POST /api/fifonafe/{id_tramite_fifonafe}/eventos`: Registro de los cuatro oficios de la cadena de correspondencia colectiva. Edición en `PATCH /api/eventos-fifonafe/{id_evento_fifonafe}` y baja en `DELETE /api/eventos-fifonafe/{id_evento_fifonafe}`.
- `GET/POST /api/fifonafe/{id_tramite_fifonafe}/intervinientes`: Registro de partes interesadas. Baja en `DELETE /api/intervinientes-fifonafe/{id_interviniente_fifonafe}`. **Acreditación de integrantes de ORV:** El registro de un `id_orv_integrante` requiere obligatoriamente enviar un `id_evento_fifonafe` (responde `422` si se omite) y valida que el integrante pertenezca al ORV del núcleo y tenga vigencia en la fecha del acto (responde `409 Conflict` en caso de incompatibilidad).

---

## 6. Indemnizaciones y Pagos

- `GET/POST /api/afectaciones/{id_afectacion}/indemnizacion`: Consulta y registro del expediente económico por afectación. Atributos: `estatus`, `monto_total`, `fecha_resolucion`, `fecha_entrega_expediente_pa`. Edición en `PATCH /api/indemnizaciones/{id_indemnizacion}`.
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

---

## 9. Salud del Sistema

- `GET /health` (Tag: `Sistema`):  
  Comprueba la conectividad con PostgreSQL y retorna el número de la última migración aplicada:
  ```json
  {
    "status": "ok",
    "schema": 15
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
