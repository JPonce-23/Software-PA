# Contrato API Frontend V1 — esquema 004

Fuente de verdad: rutas FastAPI, `schemas.py`, OpenAPI y migraciones vigentes 001–004. La siguiente migración es 005. Los catálogos se consultan en `GET /api/catalogos/operativos/{tipo_catalogo}`; nunca se asumen IDs.

## Dominio

ProyectoNucleo recibe `id_nucleo`, `id_residencia`, `total_cops_planeados`, `referencias`, `afecta_tuc`, `id_motivo_no_afecta_tuc`, `motivo_no_afecta_tuc_detalle`, `tuc_revision_pendiente`, `tuc_revision_detalle`. Referencia: `tipo_referencia`, `valor`, `es_principal`. Responsable: `nombre`, `cargo`, `contacto`, `vigencia_inicio`, `vigencia_fin`, `es_principal`.

ORV usa `numero_orv`, `inicio_vigencia`, `fin_vigencia`, `estatus_fuente`, `id_estado_registral`; la inscripción RAN no pertenece a ORV, sino a TramiteRan/eventos. Padrón usa `fecha_padron`, `numero_ejidatarios_comuneros`, `fuente`, `id_documento`. Parcela tiene un único `no_parcela`; no existen `no_parcela_ppt` ni `numero_parcela_ppt`.

Actividad: `tipo_actividad` es sólo `sensibilizacion` o `caminamiento`; además `id_afectacion`, `id_tipo_cop_operativo`, `contexto_actividad`, `fecha_programada`, `fecha_realizada`, `responsable`, `resultado`. Se conservan todos los eventos reales.

Asamblea recibe `id_padron`, `id_tipo_asamblea`, `id_contexto_asamblea`, `id_tipo_cop_operativo`, `proposito`, `resultado`, `convocatorias`. Convocatoria: `ordinal`, `fecha_expedicion`, `fecha_programada`, `fecha_realizacion`, `id_resultado`, `observaciones_resultado`, `id_documento`.

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

## Reporting

`GET /api/dashboard/kpi` conserva el resumen compatible. `GET /api/reportes/avance-periodo` filtra por `id_proyecto`, `id_entidad`, `anio`, `mes`, `trimestre`, `indicador` y responde esas dimensiones más `programado`, `realizado`, `cantidad`, `superficie_ha`, `monto`.

Las X Excel no son campos API ni BD. Se deduplica actividad por ProyectoNucleo+ciclo, Asamblea por Asamblea y RAN por TramiteRan; ingreso+reingreso cuenta una vez e inscripción se reporta aparte. Programado y realizado usan fechas propias; mes/trimestre se derivan.
