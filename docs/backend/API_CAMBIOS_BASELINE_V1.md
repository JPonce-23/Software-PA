# Cambios de API — Baseline V1

Este documento enumera únicamente incompatibilidades de backend que debe adaptar el frontend. Los modelos de entrada rechazan campos desconocidos.

## Núcleo agrario

- ENDPOINT: `POST /api/nucleos`, `PATCH /api/nucleos/{id_nucleo}`
- CAMBIO: la tenencia se captura exclusivamente mediante catálogo.
- CAMPO ELIMINADO: `tipo_nucleo`.
- SUSTITUTO: `id_tipo_tenencia`, obtenido de `GET /api/catalogos/operativos/tipo_tenencia`.
- REQUEST ANTERIOR: `{ "tipo_nucleo": "ejido", ... }`.
- REQUEST NUEVO: `{ "id_tipo_tenencia": 1, ... }`.
- RESPONSE ANTERIOR: incluía `tipo_nucleo`.
- RESPONSE NUEVA: incluye `id_tipo_tenencia`; el contexto de proyecto expone además `tipo_tenencia_codigo` y `tipo_tenencia_nombre`.
- ACCIÓN FRONTEND: enviar la FK seleccionada y dejar de leer/escribir el texto libre.

## Proyecto–núcleo

- ENDPOINT: `POST /api/proyectos/{id_proyecto}/nucleos`, `PATCH /api/proyecto-nucleo/{id_proyecto_nucleo}`.
- CAMBIO: residencia y responsables tienen fuentes normalizadas.
- CAMPOS ELIMINADOS: `residencia`, `responsable_nombre`, `contacto` como campos editables de ProyectoNucleo.
- SUSTITUTO: `id_residencia` y los endpoints `/api/proyecto-nucleo/{id_proyecto_nucleo}/responsables`.
- REQUEST ANTERIOR: podía enviar los tres textos planos.
- REQUEST NUEVO: envía `id_residencia`; crea o actualiza responsables por su recurso propio.
- RESPONSE ANTERIOR: devolvía los textos almacenados en ProyectoNucleo.
- RESPONSE NUEVA: `residencia_codigo`, `residencia_nombre`, `responsable_nombre`, `responsable_cargo` y `responsable_contacto` son proyecciones de catálogo y del responsable principal activo.
- ACCIÓN FRONTEND: separar la edición del contexto y la del responsable.

## ORV

- ENDPOINT: `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/orv`, `PATCH /api/orv/{id_orv}`.
- CAMBIO: el estado registral y el historial RAN son canónicos.
- CAMPOS ELIMINADOS: `acta_eleccion_inscrita_ran`, `fecha_inscripcion_acta_ran`.
- SUSTITUTO: `id_estado_registral`, `POST /api/tramites-ran` y eventos en `/api/tramites-ran/{id_tramite_ran}/eventos`.
- REQUEST ANTERIOR: podía enviar booleano y fecha RAN planos.
- REQUEST NUEVO: envía `id_estado_registral`; registra cada hecho RAN como trámite/evento.
- RESPONSE ANTERIOR: incluía booleano y fecha planos.
- RESPONSE NUEVA: incluye `id_estado_registral`; el historial está en los endpoints RAN.
- ACCIÓN FRONTEND: obtener el estado del catálogo y mostrar el historial de eventos.

## Integrantes ORV

- ENDPOINT: `POST /api/orv/{id_orv}/integrantes`, `PATCH /api/orv-integrantes/{id_orv_integrante}`.
- CAMBIO: órgano, cargo y calidad son catalogados.
- CAMPO ELIMINADO: `cargo` de texto libre.
- SUSTITUTO: `id_organo`, `id_cargo`, `id_calidad`.
- REQUEST ANTERIOR: incluía `cargo`.
- REQUEST NUEVO: `{ "id_persona": 1, "id_organo": 1, "id_cargo": 2, "id_calidad": 3, ... }`.
- RESPONSE ANTERIOR: incluía `cargo`.
- RESPONSE NUEVA: incluye las tres FK.
- ACCIÓN FRONTEND: usar catálogos operativos para las tres selecciones.

## Afectaciones y bienes

- ENDPOINT: `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/afectaciones`, `PATCH /api/afectaciones/{id_afectacion}`.
- CAMBIO: la afectación conserva sólo totales administrativos; las unidades afectadas son recursos propios.
- CAMPOS ELIMINADOS: `id_parcela`, `destino_superficie`, `no_parcela_solar`.
- SUSTITUTO: `unidad_agraria`, `afectacion_unidad_agraria` y, cuando exista geometría parcelaria, `unidad_agraria.id_parcela`.
- REQUEST ANTERIOR: podía enviar los tres campos planos.
- REQUEST NUEVO: crea la afectación con sus totales y vincula unidades mediante `POST /api/afectaciones/{id_afectacion}/unidades-agrarias`.
- RESPONSE ANTERIOR: incluía los tres campos planos y/o bienes.
- RESPONSE NUEVA: incluye `unidades_agrarias`, cada vínculo con sus superficies particulares.
- ACCIÓN FRONTEND: capturar y consultar unidades agrarias y sus vínculos.

- ENDPOINT RETIRADO: `GET|POST /api/afectaciones/{id_afectacion}/bienes`.
- ENDPOINT RETIRADO: `PATCH /api/bienes-afectados/{id_bien_afectado}`.
- CAMBIO: la entidad `bien_afectado` ya no existe.
- SUSTITUTO: `/api/proyecto-nucleo/{id_proyecto_nucleo}/unidades-agrarias`, `/api/unidades-agrarias/{unidad_id}` y `/api/afectaciones/{id_afectacion}/unidades-agrarias`.
- ACCIÓN FRONTEND: eliminar toda llamada a `/bienes` y migrar al flujo canónico.

## Asamblea

- ENDPOINT: `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/asambleas`, `PATCH /api/asambleas/{id_asamblea}`.
- CAMBIO: tipo/contexto son catálogos; convocatorias y RAN son colecciones independientes.
- CAMPOS ELIMINADOS: `tipo_asamblea`, `contexto_proceso`, `fecha_expedicion_primera`, `fecha_programada_primera`, `fecha_expedicion_segunda`, `fecha_programada_segunda`, `fecha_realizada`, `fecha_programada_ingreso_ran`, `fecha_ingreso_ran`, `numero_solicitud_ran`, `calificacion_registral_ran`, `fecha_inscripcion_ran`.
- SUSTITUTO: `id_tipo_asamblea`, `id_contexto_asamblea`, `convocatorias`, `tramite_ran` y `tramite_ran_evento`.
- REQUEST ANTERIOR: fechas y resultados RAN planos en Asamblea.
- REQUEST NUEVO: la Asamblea recibe FK de catálogo y opcionalmente `convocatorias`; las altas posteriores usan `/api/asambleas/{id_asamblea}/convocatorias` y `/api/tramites-ran`.
- RESPONSE ANTERIOR: incluía los campos planos.
- RESPONSE NUEVA: incluye `convocatorias`; RAN se obtiene con `/api/asambleas/{id_asamblea}/tramites-ran`.
- ACCIÓN FRONTEND: presentar convocatorias/eventos como listas y derivar celebración de la única convocatoria activa con `fecha_realizacion`.

## Convenio

- ENDPOINT: `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/convenios`, `PATCH /api/convenios/{id_convenio}`.
- CAMBIO: el convenio conserva sólo datos del instrumento jurídico.
- CAMPOS ELIMINADOS: `fecha_programada_ingreso_ran`, `ingreso_ran_fecha`, `numero_solicitud_ran`, `calificacion_registral_ran`, `fecha_inscripcion_ran`.
- SUSTITUTO: `POST /api/tramites-ran`, `/api/convenios/{id_convenio}/tramites-ran` y eventos RAN.
- REQUEST ANTERIOR: podía enviar el resumen RAN plano.
- REQUEST NUEVO: no acepta esos campos; crea el trámite y sus eventos por separado.
- RESPONSE ANTERIOR: incluía el resumen RAN.
- RESPONSE NUEVA: el convenio no lo incluye; el historial se consulta en el endpoint RAN.
- ACCIÓN FRONTEND: separar la captura jurídica de la registral.

## FIFONAFE

- ENDPOINT: `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/fifonafe`, `PATCH /api/fifonafe/{id_tramite_fifonafe}`.
- CAMBIO: oficios repetibles pertenecen exclusivamente a eventos.
- CAMPOS ELIMINADOS: `no_oficio_fifonafe_a_dgaopr`, `fecha_oficio_fifonafe_a_dgaopr`, `no_oficio_dgaopr_a_representacion`, `fecha_oficio_dgaopr_a_representacion`, `no_oficio_respuesta_representacion_a_dgaopr`, `fecha_oficio_respuesta_representacion_a_dgaopr`, `no_oficio_respuesta_dgaopr_a_fifonafe`, `fecha_oficio_respuesta_dgaopr_a_fifonafe`.
- SUSTITUTO: `eventos[]` y `POST /api/fifonafe/{id_tramite_fifonafe}/eventos`, con `id_tipo_evento`, `numero_oficio` y `fecha_oficio`.
- REQUEST ANTERIOR: contenía los ocho campos planos.
- REQUEST NUEVO: contiene `ids_afectacion`, estado y opcionalmente eventos; el PATCH del trámite sólo modifica el estado propio.
- RESPONSE ANTERIOR: incluía ocho campos planos.
- RESPONSE NUEVA: incluye `eventos`.
- ACCIÓN FRONTEND: renderizar y editar la secuencia de eventos.

## Expediente documental

- ENDPOINT: `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/requisitos-documentales`.
- CAMBIO: el objetivo del requisito es polimórfico y explícito.
- CAMPO ELIMINADO: `id_afectacion`.
- SUSTITUTO: `entidad_tipo="afectacion"` y `entidad_id`.
- REQUEST ANTERIOR: podía usar `id_afectacion`.
- REQUEST NUEVO: `{ "entidad_tipo": "afectacion", "entidad_id": 1, "id_requisito": 1, "id_estado": 1, ... }`.
- RESPONSE ANTERIOR: incluía `id_afectacion`.
- RESPONSE NUEVA: incluye `entidad_tipo` y `entidad_id`.
- ACCIÓN FRONTEND: enviar siempre el objetivo tipado.
