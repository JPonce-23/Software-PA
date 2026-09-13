# Contrato API Frontend V1 — esquema 015

Este documento define los supuestos y contratos de integración entre el frontend
y el backend para el cierre del sprint. Está alineado con el esquema OpenAPI en
`docs/backend/openapi-backend-schema-015.json` y migraciones vigentes 001–015.
Los catálogos se consultan en
`GET /api/catalogos/operativos/{tipo_catalogo}`; nunca se asumen IDs.

El frontend consume exclusivamente la API HTTP del backend. No se conecta
directamente a PostgreSQL ni usa tablas, funciones o migraciones como contrato
de integración.

## Dominio

ProyectoNucleo recibe `id_nucleo`, `id_residencia`, `total_cops_planeados`, `referencias`, `afecta_tuc`, `id_motivo_no_afecta_tuc`, `motivo_no_afecta_tuc_detalle`, `tuc_revision_pendiente`, `tuc_revision_detalle`. Referencia: `tipo_referencia`, `valor`, `es_principal`. Responsable: `nombre`, `cargo`, `contacto`, `vigencia_inicio`, `vigencia_fin`, `es_principal`.

ORV usa `numero_orv`, `inicio_vigencia`, `fin_vigencia`, `estatus_fuente`, `id_estado_registral`; la inscripción RAN no pertenece a ORV, sino a TramiteRan/eventos. Padrón usa `fecha_padron`, `numero_ejidatarios_comuneros`, `fuente`, `id_documento`. Parcela tiene un único `no_parcela`; no existen `no_parcela_ppt` ni `numero_parcela_ppt`.

Actividad: `tipo_actividad` es sólo `sensibilizacion` o `caminamiento`; además `id_afectacion`, `id_tipo_cop_operativo`, `contexto_actividad`, `fecha_programada`, `fecha_realizada`, `responsable`, `resultado`. Se conservan todos los eventos reales.

`POST Asamblea` recibe `id_padron`, `id_tipo_asamblea`, `id_contexto_asamblea`, `id_tipo_cop_operativo`, `proposito`, `resultado`, `convocatorias`. `PATCH Asamblea` recibe sólo metadatos de la asamblea (`id_padron`, `id_tipo_asamblea`, `id_contexto_asamblea`, `id_tipo_cop_operativo`, `proposito`, `resultado`); las convocatorias se administran con sus endpoints hijos. Convocatoria: `ordinal`, `fecha_expedicion`, `fecha_programada`, `fecha_realizacion`, `id_resultado`, `observaciones_resultado`, `id_documento`.

## Seguimiento funcional (004)

Historial funcional operativo append-oriented asociado a un `ProyectoNucleo` y opcionalmente a un objetivo tipado (`proyecto_nucleo`, `afectacion`, `parcela`, `parcela_titular`, `unidad_agraria`, `asamblea`, `asamblea_convocatoria`, `convenio`, `tramite_ran`, `tramite_ran_evento`, `tramite_fifonafe`, `tramite_fifonafe_evento`, `orv`, `padron_historial`, `indemnizacion`).

Endpoints:
- `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/seguimiento`: lista ordenada de eventos activos.
- `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/seguimiento`: crea evento con `ambito` (`general`, `colectivo`, `individual`), `id_tipo_evento`, `id_motivo` opcional, objetivo opcional (`entidad_tipo`, `entidad_id`), `fecha_evento`, `detalle`, `id_documento`, `fuente`.
- `GET /api/seguimiento/{id_seguimiento_evento}`: obtiene detalle del evento.
- `PATCH /api/seguimiento/{id_seguimiento_evento}`: actualiza metadatos (`fecha_evento`, `detalle`, `id_documento`, `fuente`) sin reescribir la historia.
- `DELETE /api/seguimiento/{id_seguimiento_evento}`: baja lógica obligatoria con `{"motivo": "..."}`.

Catálogos:
- `tipo_evento_seguimiento`: `inicio`, `suspension`, `reapertura`, `cierre`, `cambio_alcance`, `reunion`, `negociacion`, `consulta_indigena`, `continuacion_asamblea`, `medicion_bdt`, `otro`.
- `motivo_seguimiento`: `expropiacion_directa`, `no_afectacion`, `comunidad_indigena`, `dominio_pleno`, `juicio_agrario`, `conflicto_titularidad`, `rechazo`, `cambio_trazo`, `nueva_informacion`, `calificacion_negativa`, `falta_pago`, `otro`.
- `estado_requisito_documental`: incorpora `parcial` y `pendiente_validacion`.
- Requisitos documentales opcionales: `validacion_pa_sict`, `oficio_ran_parcelas_afectacion`, `acta_complementaria`.

## Catálogos y RAN

`tipo_cop_operativo`: `ORIGEN`, `ADICIONAL`, `2A_ADICIONAL`, `COMPLEMENTARIAS`, `TRANSVERSALES`. `contexto_asamblea` incluye `transversal`; `resultado_convocatoria` usa `celebrada`, `no_verificativo`, `cancelada`, `reprogramada`, `otro`.

`POST /api/tramites-ran` recibe exactamente uno de `id_asamblea`, `id_convenio`, `id_orv`, más `fecha_programada_ingreso`, `referencia_expediente`, `eventos`. Evento: `ordinal`, `id_tipo_evento`, `fecha_evento`, `numero_solicitud`, `resultado`, `calificacion`, `folio_referencia`, `id_documento`. No existen `numero_tramite` ni `estatus` planos.

`PATCH /api/tramites-ran/{id_tramite_ran}` permite actualizar exclusivamente la programación del trámite (`fecha_programada_ingreso: date | None`) sin crear un nuevo trámite, sin alterar su identidad ni recrear sus eventos. Requiere rol de captura y validación de acceso al proyecto. Los campos contextuales (`id_proyecto_nucleo`, `id_nucleo`, `id_asamblea`, `id_convenio`, `id_orv`) y eventos permanecen inmutables. Enviar campos no permitidos en el body retorna `422 Unprocessable Entity`.
Sus respuestas aplicables son `200` al actualizar, `403` por rol o proyecto fuera de alcance, `404` para trámite inexistente o inactivo, `409` ante conflicto de dominio al persistir y `422` por body inválido.

Indemnización admite `pendiente`, `programado`, `en_proceso`, `completo`, `pagado`, `cancelado`, `otro`; `pagado` no inventa Pago. Checklist admite, además de objetivos previos, `orv`, `padron_historial`, `actividad_campo`, `asamblea`, `asamblea_convocatoria`.

## Reporting (005)

- `GET /api/dashboard/kpi`: resumen compatible agregado por `id_proyecto, anio, indicador`, deduplicado a nivel anual sin multiplicar registros.
- `GET /api/reportes/avance-periodo`: endpoint de reporte periódico desagregado. Admite los filtros:
  - `id_proyecto` (int)
  - `id_entidad` (int)
  - `ambito` (`colectivo`, `individual`)
  - `tipo_cop_operativo` (`ORIGEN`, `ADICIONAL`, `2A_ADICIONAL`, `COMPLEMENTARIAS`, `TRANSVERSALES`)
  - `tipo_convenio` (`cop_original`, `modificatorio`, `superficie_adicional`, `obras_complementarias`, `ampliacion`, `ampliacion_remanente`)
  - `destino_superficie` (`tuc`, `camino`, `canal`, etc.)
  - `anio` (int)
  - `mes` (int 1..12)
  - `trimestre` (int 1..4)
  - `indicador` (str)
- Respuesta de `GET /api/reportes/avance-periodo`: lista de objetos con 15 columnas:
  `id_proyecto`, `id_entidad`, `ambito`, `tipo_cop_operativo`, `tipo_convenio`, `destino_superficie`, `anio`, `mes`, `trimestre`, `indicador`, `programado`, `realizado`, `cantidad`, `superficie_ha`, `monto`.

Las X Excel no son campos API ni BD. Se deduplica a nivel de hito canónico (`vw_hito_seguimiento`) antes de proyectar a periodos temporales; ingreso y reingreso del mismo trámite RAN cuentan una sola vez como hito, e inscripción se reporta de forma independiente. Programado y realizado usan fechas propias sin inventar periodos; mes y trimestre se derivan de la fecha.

Núcleos, parcelas y superficies por destino son snapshots cuando no existe fecha de negocio: no aparecerán artificialmente en este endpoint ni en `/api/dashboard/kpi` por la fecha de creación/importación. Para superficie por destino, el valor canónico es `AfectacionUnidadAgraria.superficie_afectada_ha`; no se replica la superficie total de afectación.

## Snapshot actual (006)

`GET /api/reportes/resumen-actual` representa estado actual, no avance temporal. Filtros: `id_proyecto`, `id_entidad`, `ambito`, `indicador`, `tipo_cop_operativo`, `destino_superficie`; no acepta año, mes ni trimestre. Expone núcleos, parcelas afectadas, superficies administrativas y por destino, no afecta TUC, comunidad indígena y COP planeados.

## Convenios e impactos (007)

Las superficies administrativas, de unidad agraria, declaradas e impactos usan
decimales de hasta siete posiciones; el cliente debe enviarlas como número JSON
decimal y no debe redondearlas a seis posiciones. `ConvenioUpdate` rechaza
colecciones relacionadas: comparecientes y afectaciones se administran mediante
sus endpoints hijos.

- `GET/POST /api/convenios/{id_convenio}/afectaciones` y
  `PATCH /api/convenio-afectaciones/{id_convenio_afectacion}` separan el efecto
  superficial (`adicion`, `sustitucion`, `correccion`, `sin_cambio`, `pendiente`)
  de la clase del convenio.
- `GET/POST /api/convenios/{id_convenio}/comparecientes` y
  `DELETE /api/convenio-comparecientes/{id_compareciente}` mantienen la
  comparecencia separada de beneficiarios y pagos.
- El valor declarado y el impacto económico son conceptos distintos; un impacto
  pendiente se expresa con `null`, nunca con cero implícito.
- Reporting: `/api/reportes/convenios/valores-declarados`, `/impactos`,
  `/impactos-periodo`, `/cobertura-impactos` y `/colectivos-destino` (alias `/destinos`).
  Los montos se contabilizan por instrumento y no por cada relación N:M con afectaciones.
  El endpoint `/api/reportes/convenios/colectivos-destino` expone el desglose físico por destino
  de superficie para convenios colectivos (`ambito = 'colectivo'`), distinguiendo la superficie física
  afectada (`superficie_ha`) de la superficie declarada (`superficie_declarada_ha`) y del monto del
  instrumento (`monto_declarado`). Regla económica fundamental de `monto_declarado`:
  - Es **NO ADITIVO**: sumar los valores de esta columna entre filas multidestino arrojaría un importe falso.
  - Pertenece al convenio completo (`c.monto_100`), no al destino de suelo.
  - No representa el monto del destino (no hay prorrateo por destino).
  - Para agregados económicos oficiales debe contarse una sola vez por `id_convenio`.
  El read-model tiene granularidad de detalle: una fila por `id_convenio + destino_superficie`; no calcula cantidades agregadas. Los consumidores deben deduplicar la cantidad de convenios por `id_convenio` y la de asambleas por `id_asamblea`. Nunca deben sumar `monto_declarado` directamente sobre filas multidestino.
  Soporta filtros por `id_proyecto`, `id_entidad`, `id_proyecto_nucleo`, `id_convenio`, `id_asamblea`,
  `tipo_convenio`, `tipo_cop_operativo`, `destino_superficie`, `anio`, `mes` y `trimestre`. Ordena por
  `id_proyecto`, `id_convenio` y `destino_superficie`.


## FIFONAFE (008)

`id_tramite_fifonafe` identifica la solicitud y admite varias afectaciones. Los
registros históricos conservan `version_flujo=1`; las nuevas solicitudes nacen
en versión 2. `version_flujo` es de lectura y no puede modificarse por API.
`referencia_expediente` es opcional y no constituye por sí sola una clave de
deduplicación.

- La solicitud admite `id_asamblea_retiro` sólo cuando corresponde a una
  Asamblea colectiva de retiro compatible con el mismo ProyectoNucleo.
- Los eventos exponen `ciclo_consulta`, `fecha_evento`, `fecha_oficio` y
  `conflicto_impide_retiro`. Ronda, ordinal e identidad no deben mezclarse ni
  reescribirse.
- `PATCH` y baja lógica están en
  `/api/eventos-fifonafe/{id_evento_fifonafe}`.
- Intervinientes: `GET/POST /api/fifonafe/{id_tramite_fifonafe}/intervinientes`
  y baja lógica en
  `/api/intervinientes-fifonafe/{id_interviniente_fifonafe}`. Registrar
  solicitante, representante, titular, beneficiario o receptor no crea un Pago.
  La acreditación de un integrante ORV (`id_orv_integrante`) requiere
  obligatoriamente en el payload un evento (`id_evento_fifonafe`), retornando
  `422 Unprocessable Entity` si se omite. Asimismo, el servicio valida con
  `409 Conflict` que el evento pertenezca al trámite y cuente con fecha de negocio
  (`fecha_evento` o `fecha_oficio`), que la persona coincida, que el ORV pertenezca
  al núcleo del trámite y que el nombramiento esté vigente en la fecha del acto.
  `POST` responde `201 Created`; su schema OpenAPI expresa la dependencia
  `id_orv_integrante` no nulo → `id_evento_fifonafe` no nulo y documenta `409 Conflict`
  para las incompatibilidades de dominio anteriores.
- `hay_conflictos` y `conflicto_impide_retiro` son triestados independientes.
  Consulta, resolución, entrega y comprobación son hitos distintos. Cuatro
  oficios no completan automáticamente un flujo v2.
- Reporting: `/api/reportes/fifonafe/cobertura` e
  `/api/reportes/fifonafe/indicador-institucional`. El indicador legado
  `fifonafe` conserva exclusivamente la semántica v1.

## Integración, autenticación y CSRF

La autenticación es una sesión opaca por cookies; no hay Bearer/JWT. El cliente
debe enviar `credentials: "include"`. Con `AUTH_COOKIE_SECURE=false` las
cookies son `pa_session_dev` (HttpOnly) y `pa_csrf_dev`; con
`AUTH_COOKIE_SECURE=true` son `__Host-pa_session` (HttpOnly) y
`__Host-pa_csrf`. La cookie CSRF es legible por el cliente para copiar su valor
en `X-CSRF-Token`.

`POST /api/auth/sesiones` exige un `Origin` permitido, pero no CSRF. En las
demás mutaciones, cuando la petición trae una cookie de sesión, se requieren
un `Origin` permitido y la cookie y encabezado CSRF coincidentes y válidos.
Una mutación sin sesión continúa hacia la dependencia del endpoint y normalmente
responde `401`; `GET` y `HEAD` no requieren CSRF.

### Sesión

- `POST /api/auth/sesiones`: body `application/x-www-form-urlencoded` con
  `username` y `password`. Responde `200` con
  `{ "user": { "id_usuario", "nombre", "apellido_paterno", "correo", "rol" }, "expira_en" }`
  y establece ambas cookies. Credenciales inválidas, cuenta inactiva o cuenta
  bloqueada responden `401` con `{"detail":"Credenciales incorrectas"}`.
  Una contraseña de más de 72 bytes UTF-8 también responde ese mismo `401`;
  nunca permite distinguir usuario inexistente de contraseña incorrecta.
- `GET /api/auth/sesion`: requiere sesión válida; responde `200` con la misma
  forma de sesión, o `401` si falta, expiró o fue revocada.
- `POST /api/auth/logout`: revoca la sesión indicada por cookie si existe,
  limpia las cookies y responde `200` con `{"detail":"Sesión cerrada"}`.
- `POST /api/auth/logout-todas`: requiere sesión propia y CSRF; revoca todas
  las sesiones activas del usuario, limpia las cookies y responde `200` con
  `{"detail":"Todas las sesiones fueron cerradas"}`.
- `POST /api/auth/cambiar-contrasena`: requiere sesión propia y CSRF. Body JSON
  exacto: `{"contrasena_actual":"...","contrasena_nueva":"..."}`. Responde
  `200` con `{"detail":"Contraseña actualizada","sesiones_revocadas":n}` y
  limpia las cookies; la sesión actual también queda revocada. Devuelve `400`
  si la actual es incorrecta, `409` si la nueva coincide con la actual y `422`
  para body inválido.

La contraseña usada en creación, cambio propio y restablecimiento administrativo
debe tener al menos 8 caracteres, al menos una letra y un número, y un máximo
de 72 bytes UTF-8. Mayúsculas y símbolos son válidos, pero no obligatorios. No
se truncan contraseñas. Para el cambio propio, `contrasena_actual` que supera
72 bytes UTF-8 se rechaza con `422`.

### Administración de usuarios

Todos estos endpoints requieren sesión, CSRF y rol `admin`; un usuario sin ese
rol recibe `403` y una sesión ausente/inválida recibe `401`.

- `POST /api/usuarios`: body JSON `nombre`, `apellido_paterno`,
  `apellido_materno` opcional, `correo`, `rol` (`admin`, `operador`,
  `visualizador`, `geografo`) y `contrasena`. Responde `201` con el usuario
  (`id_usuario`, datos, `activo`, `fecha_alta`); `409` si el correo ya existe y
  `422` ante datos o contraseña inválidos.
- `GET /api/usuarios`: query `skip` (>=0), `limit` (1..200) y `estado`
  (`activos`, `inactivos`, `todos`; por defecto `activos`). Responde `200` con
  una lista de usuarios, incluyendo `bloqueado`, `bloqueado_hasta` y
  `ultimo_acceso_en`.
- `PATCH /api/usuarios/{id_usuario}`: actualiza sólo `nombre`,
  `apellido_paterno`, `apellido_materno` y/o `rol`. Responde `200` con el
  usuario, `404` si no existe o está inactivo y `409` si intenta degradar al
  último administrador activo.
- `PATCH /api/usuarios/{id_usuario}/correo`: body JSON exacto
  `{"correo":"...","motivo":"..."}` (`motivo` 3..100 caracteres).
  Responde `200` con `{"detail":"Correo actualizado","sesiones_revocadas":n}`;
  revoca las sesiones activas del usuario. Puede devolver `404`, `409` (sin
  cambio o correo duplicado) y `422`.
- `DELETE /api/usuarios/{id_usuario}`: body `{"motivo":"..."}` (3..500).
  Hace baja lógica, desactiva asignaciones y revoca sesiones activas. Responde
  `200` con `{"detail":"Usuario desactivado"}`; `404` si no está activo y
  `409` si es el último administrador activo.
- `POST /api/usuarios/{id_usuario}/reactivar`: body JSON exacto
  `{"motivo":"..."}` (3..100). Responde `200` con
  `{"detail":"Usuario reactivado"}`, `404` si no existe o `409` si ya está
  activo.
- `POST /api/usuarios/{id_usuario}/desbloquear`: mismo body de acción. Responde
  `200` con `{"detail":"Cuenta desbloqueada"}`, `404` si no existe o `409`
  si no tiene bloqueo vigente.
- `POST /api/usuarios/{id_usuario}/revocar-sesiones`: mismo body de acción.
  Responde `200` con `{"detail":"Sesiones revocadas","sesiones_revocadas":n}`;
  devuelve `404` si el usuario no existe.
- `POST /api/usuarios/{id_usuario}/restablecer-contrasena`: body JSON exacto
  `{"contrasena_nueva":"...","motivo":"..."}`. Responde `200` con
  `{"detail":"Contraseña restablecida","sesiones_revocadas":n}` y revoca
  las sesiones activas del destinatario. Devuelve `404` si no existe, `409` si
  se intenta restablecer la propia contraseña o reutilizar la actual y `422`
  para body/contraseña inválidos.

### Roles y errores comunes

Los roles posibles son `admin`, `operador`, `visualizador` y `geografo`.
Administración de usuarios y auditoría son exclusivas de `admin`; en dominio,
documentos y reporting, lectura admite los cuatro roles, captura admite
`admin`/`operador` y operaciones GIS admiten `admin`/`geografo`.

- `401 Unauthorized`: sesión ausente, expirada, revocada o credenciales de
  inicio inválidas.
- `403 Forbidden`: origen o CSRF inválido, o rol sin permiso.
- `404 Not Found`: recurso inexistente o no accesible según el endpoint.
- `409 Conflict`: duplicidad, transición prohibida o invariante de negocio.
- `422 Unprocessable Entity`: body, parámetros o tipos que no satisfacen el
  schema.

`GET /health` no requiere sesión y, para la instancia de integración actual,
debe responder `{ "status": "ok", "schema": 15 }`. La siguiente migración disponible es 016.

Las consultas y mutaciones de dominio siguen aplicando la autorización por
proyecto del backend. Los usuarios no administradores sólo reciben IDs de
asignaciones activas cuyo proyecto también está activo. Los read-models de snapshot,
seguimiento, avance periódico, dashboard y convenios colectivos por destino excluyen
proyectos con `activo IS NOT TRUE`.
