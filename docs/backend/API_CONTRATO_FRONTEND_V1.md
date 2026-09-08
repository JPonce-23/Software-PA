# Contrato API Frontend V1 — esquema 008

Fuente de verdad: rutas FastAPI, `schemas.py`, el archivo generado
`docs/backend/openapi-backend-schema-008.json` y migraciones vigentes 001–008.
Los catálogos se consultan en
`GET /api/catalogos/operativos/{tipo_catalogo}`; nunca se asumen IDs.

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
  `/impactos-periodo` y `/cobertura-impactos`. Los montos se contabilizan por
  instrumento y no por cada relación N:M con afectaciones.

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
- `hay_conflictos` y `conflicto_impide_retiro` son triestados independientes.
  Consulta, resolución, entrega y comprobación son hitos distintos. Cuatro
  oficios no completan automáticamente un flujo v2.
- Reporting: `/api/reportes/fifonafe/cobertura` e
  `/api/reportes/fifonafe/indicador-institucional`. El indicador legado
  `fifonafe` conserva exclusivamente la semántica v1.

## Integración y permisos

La aplicación utiliza un esquema de sesión opaca basado en cookies HttpOnly y
protección contra CSRF. El OpenAPI generado no publica todavía
`securitySchemes`; la integración debe seguir estrictamente los endpoints de
sesión y el encabezado CSRF documentados aquí, sin inferir cabeceras Bearer/JWT.

- **Inicio de sesión**: `POST /api/auth/sesiones` (form-urlencoded con `username`
  y `password`). Establece la cookie de sesión HttpOnly (`software_pa_session`)
  y la cookie accesible para el cliente (`software_pa_csrf`). Retorna los datos
  del usuario autenticado y su expiración.
- **Sesión activa**: `GET /api/auth/sesion`. Retorna el usuario y la vigencia de
  la sesión autenticada actual.
- **Cierre de sesión**: `POST /api/auth/logout`. Invalida la sesión actual en el
  servidor y limpia las cookies del cliente. Cierre global: `POST /api/auth/logout-todas`.
- **Protección CSRF**: Todas las mutaciones de estado (`POST`, `PUT`, `PATCH`,
  `DELETE`) requieren incluir el encabezado HTTP `X-CSRF-Token` con el valor
  obtenido de la cookie `software_pa_csrf`. Las peticiones `GET` y `HEAD` no lo
  requieren.
- **Verificación de estado**: `GET /health` reporta `{ "status": "ok", "schema": 8 }`.
- **Autorización por proyecto**: Todas las consultas y mutaciones se filtran de
  forma estricta por los proyectos autorizados del usuario autenticado.
- **Aislamiento en QA / Demostración**: El frontend debe seleccionar un
  `id_proyecto` explícito para demostraciones en QA; los agregados sin filtro
  pueden incluir fixtures sintéticas históricas.
- **Respuestas de error**:
  - `401 Unauthorized`: Sesión ausente, expirada o inválida.
  - `403 Forbidden`: Token CSRF inválido o falta de permisos sobre el recurso.
  - `404 Not Found`: Recurso inexistente o perteneciente a un proyecto no asignado.
  - `409 Conflict`: Reglas de negocio e invariantes de dominio (ej. duplicidad,
    dependencias faltantes, transiciones prohibidas).
  - `422 Unprocessable Entity`: Errores de validación estructural y formato de
    esquema Pydantic.
