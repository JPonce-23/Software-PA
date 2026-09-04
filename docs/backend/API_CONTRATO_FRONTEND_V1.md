# Contrato API Frontend V1 — esquema 003

Fuente de verdad: rutas FastAPI, `schemas.py`, OpenAPI y migraciones 001–003. Los catálogos se consultan en `GET /api/catalogos/operativos/{tipo_catalogo}`; nunca se asumen IDs.

## Dominio

ProyectoNucleo recibe `id_nucleo`, `id_residencia`, `total_cops_planeados`, `referencias`, `afecta_tuc`, `id_motivo_no_afecta_tuc`, `motivo_no_afecta_tuc_detalle`, `tuc_revision_pendiente`, `tuc_revision_detalle`. Referencia: `tipo_referencia`, `valor`, `es_principal`. Responsable: `nombre`, `cargo`, `contacto`, `vigencia_inicio`, `vigencia_fin`, `es_principal`.

ORV usa `numero_orv`, `inicio_vigencia`, `fin_vigencia`, `estatus_fuente`, `id_estado_registral`; la inscripción RAN no pertenece a ORV, sino a TramiteRan/eventos. Padrón usa `fecha_padron`, `numero_ejidatarios_comuneros`, `fuente`, `id_documento`. Parcela tiene un único `no_parcela`; no existen `no_parcela_ppt` ni `numero_parcela_ppt`.

Actividad: `tipo_actividad` es sólo `sensibilizacion` o `caminamiento`; además `id_afectacion`, `id_tipo_cop_operativo`, `contexto_actividad`, `fecha_programada`, `fecha_realizada`, `responsable`, `resultado`. Se conservan todos los eventos reales.

Asamblea recibe `id_padron`, `id_tipo_asamblea`, `id_contexto_asamblea`, `id_tipo_cop_operativo`, `proposito`, `resultado`, `convocatorias`. Convocatoria: `ordinal`, `fecha_expedicion`, `fecha_programada`, `fecha_realizacion`, `id_resultado`, `observaciones_resultado`, `id_documento`.

## Catálogos y RAN

`tipo_cop_operativo`: `ORIGEN`, `ADICIONAL`, `2A_ADICIONAL`, `COMPLEMENTARIAS`, `TRANSVERSALES`. `contexto_asamblea` incluye `transversal`; `resultado_convocatoria` usa `celebrada`, `no_verificativo`, `cancelada`, `reprogramada`, `otro`.

`POST /api/tramites-ran` recibe exactamente uno de `id_asamblea`, `id_convenio`, `id_orv`, más `fecha_programada_ingreso`, `referencia_expediente`, `eventos`. Evento: `ordinal`, `id_tipo_evento`, `fecha_evento`, `numero_solicitud`, `resultado`, `calificacion`, `folio_referencia`, `id_documento`. No existen `numero_tramite` ni `estatus` planos.

Indemnización admite `pendiente`, `programado`, `en_proceso`, `completo`, `pagado`, `cancelado`, `otro`; `pagado` no inventa Pago. Checklist admite, además de objetivos previos, `orv`, `padron_historial`, `actividad_campo`, `asamblea`, `asamblea_convocatoria`.

## Reporting

`GET /api/dashboard/kpi` conserva el resumen compatible. `GET /api/reportes/avance-periodo` filtra por `id_proyecto`, `id_entidad`, `anio`, `mes`, `trimestre`, `indicador` y responde esas dimensiones más `programado`, `realizado`, `cantidad`, `superficie_ha`, `monto`.

Las X Excel no son campos API ni BD. Se deduplica actividad por ProyectoNucleo+ciclo, Asamblea por Asamblea y RAN por TramiteRan; ingreso+reingreso cuenta una vez e inscripción se reporta aparte. Programado y realizado usan fechas propias; mes/trimestre se derivan.
