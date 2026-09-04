# Diccionario de datos SOFTWARE-PA — Baseline V1

> Fuente: `backend/db/migrations/001_baseline_v1.sql`
> Esquema funcional: 51 tablas, sin `bien_afectado`

## Convenciones

Las claves primarias usan `id_*`; las referencias se implementan con FK explícitas. Las entidades con vigencia usan `activo`, fecha/motivo de baja y auditoría. Los montos y superficies no admiten valores negativos. Las geometrías se almacenan en SRID 4326.

`schema_migrations` y `spatial_ref_sys` son objetos técnicos y no forman parte de las 51 tablas funcionales.

## Catálogos y territorio

| Tabla | Responsabilidad y datos canónicos |
|---|---|
| `entidad_federativa` | Entidades federativas por clave INEGI y nombre. |
| `municipio` | Municipios/alcaldías, con FK a entidad y clave INEGI. |
| `catalogo_operativo` | Opciones de dominio por `tipo_catalogo`, `codigo`, nombre, orden y vigencia. |
| `catalogo_operativo_alias` | Alias normalizados de una opción de catálogo. |
| `catalogo_alias_territorial` | Resolución de nombres/claves territoriales importados hacia municipio. |

## Proyecto, contexto y RBAC

| Tabla | Responsabilidad y datos canónicos |
|---|---|
| `proyecto` | Proyecto administrativo, descripción y vigencia. |
| `nucleo_agrario` | Núcleo, municipio, `id_tipo_tenencia`, comunidad indígena, fuente y geometría opcional. No existe `tipo_nucleo`. |
| `proyecto_nucleo` | Relación proyecto–núcleo, `id_residencia`, planeación y estado TUC. No almacena residencia o responsable en texto. |
| `proyecto_nucleo_referencia` | Referencias 1:N del contexto; admite una principal activa por tipo. |
| `proyecto_nucleo_responsable` | Responsables 1:N, cargo, contacto, vigencia y principalidad. |
| `usuario` | Identidad de acceso, rol de aplicación, hash administrado por backend y estado activo. |
| `usuario_proyecto` | Alcance RBAC del usuario sobre proyectos. |

## Personas, representación y padrón

| Tabla | Responsabilidad y datos canónicos |
|---|---|
| `persona` | Identidad reutilizable: CURP/RFC, nombre, contacto, origen y calidad de datos. |
| `orv` | Órgano de representación del núcleo, vigencia y `id_estado_registral`. No almacena resúmenes RAN. |
| `orv_integrante` | Persona en ORV con `id_organo`, `id_cargo` e `id_calidad` catalogados. No existe `cargo` libre. |
| `padron_historial` | Corte histórico del padrón, cantidades, fecha, fuente y documento. |

## Parcelas y unidades agrarias

| Tabla | Responsabilidad y datos canónicos |
|---|---|
| `parcela` | Parcela del núcleo, número, tipo de tierra, superficie y geometría opcional. |
| `parcela_titular` | Relación histórica parcela–persona y tipo de derecho. |
| `unidad_agraria` | Identidad general del bien/unidad, núcleo, clasificaciones catalogadas, parcela opcional, referencia, detalle y superficie propia. |
| `unidad_agraria_titular` | Titularidad histórica de la unidad mediante `id_persona` o `id_parcela_titular`. |
| `afectacion_unidad_agraria` | Relación N:M afectación–unidad con superficies preliminar/afectada particulares y fuente. |

## Seguimiento de afectaciones

| Tabla | Responsabilidad y datos canónicos |
|---|---|
| `actividad_campo` | Actividad del contexto, afectación opcional, fechas, responsable y resultado. |
| `afectacion` | Seguimiento administrativo colectivo/individual, totales `superficie_preliminar_ha` y `superficie_afectada_ha`, situación, condición, avalúo y COP catalogado. No contiene parcela, destino ni número de solar. |
| `indemnizacion` | Estado y fechas de indemnización de una afectación. |
| `pago` | Pago de indemnización, fecha, monto, beneficiario, referencia y medio. |

Los totales de `afectacion` y los valores particulares de `afectacion_unidad_agraria` representan conceptos diferentes y no están obligados a coincidir.

## Asamblea

| Tabla | Responsabilidad y datos canónicos |
|---|---|
| `asamblea` | Asamblea del contexto, padrón opcional, `id_tipo_asamblea`, `id_contexto_asamblea`, propósito y resultado. |
| `asamblea_convocatoria` | Convocatorias 1:N con ordinal, fechas de expedición/programación/realización, resultado y documento. |

`asamblea` no contiene textos duplicados de catálogo, fechas planas de convocatoria, `fecha_realizada` ni campos RAN. Sólo una convocatoria activa por asamblea puede tener `fecha_realizacion`, evitando una celebración ambigua.

## Convenios y RAN

| Tabla | Responsabilidad y datos canónicos |
|---|---|
| `convenio` | Instrumento jurídico: ámbito, tipo/modalidad, consecutivo, linaje, asamblea autorizante, firma, montos y superficie. No contiene campos RAN. |
| `convenio_afectacion` | Asociación convenio–afectación y rol principal/adicional. |
| `convenio_compareciente` | Comparecencia de persona, titular parcelario opcional, calidad/acreditación, nombre en instrumento y firma. |
| `tramite_ran` | Trámite 1:N sobre exactamente una Asamblea, Convenio u ORV. Conserva `id_proyecto_nucleo` para Asamblea/Convenio e `id_nucleo` para ORV. |
| `tramite_ran_evento` | Hechos registrales ordenados: tipo, fecha, solicitud, resultado, calificación, folio y documento. |

`chk_tramite_ran_contexto` y la validación por trigger exigen:

- Asamblea/Convenio → `id_proyecto_nucleo` no nulo e `id_nucleo` nulo;
- ORV → `id_nucleo` no nulo e `id_proyecto_nucleo` nulo.

## FIFONAFE

| Tabla | Responsabilidad y datos canónicos |
|---|---|
| `tramite_fifonafe` | Trámite del contexto, ámbito, estatus, acuse y resultado de conflictos. |
| `tramite_fifonafe_afectacion` | Cobertura N:M de afectaciones por trámite. |
| `tramite_fifonafe_evento` | Oficios/eventos repetibles con tipo, origen, destino, número, fecha y documento. |

No existen los ocho campos planos de oficio/fecha; todos los oficios pertenecen a `tramite_fifonafe_evento`.

## Documentos, expediente y trazabilidad

| Tabla | Responsabilidad y datos canónicos |
|---|---|
| `documento` | Identidad y metadatos funcionales del documento. |
| `documento_version` | Contenido versionado, hash SHA-256, tamaño, ruta y MIME; es inmutable. |
| `documento_vinculo` | Vínculo tipado entre documento y objetivo funcional canónico. |
| `requisito_documental` | Definición catalogada del requisito, contexto, obligatoriedad y vigencia. |
| `expediente_requisito` | Estado de requisito para `proyecto_nucleo` y objetivo `entidad_tipo`/`entidad_id`. No existe `id_afectacion` dedicado. |
| `trazabilidad_fuente` | Archivo, hoja, fila, columna, valor original, tratamiento y objetivo funcional. |
| `bitacora` | Auditoría de cambios de dominio con actor, contexto y valores anterior/nuevo. |

`bien_afectado` no es un target de documentos ni trazabilidad.

## Importación tabular

| Tabla | Responsabilidad y datos canónicos |
|---|---|
| `importacion_tabular` | Cabecera de archivo tabular, hash, estado, métricas y proyecto. |
| `importacion_tabular_celda` | Hoja, fila, columna, encabezado, valores original/normalizado, tratamiento, advertencias, errores y destino. |

La granularidad por celda se conserva; no se reemplaza por un JSONB opaco.

## Importación geoespacial y GIS

| Tabla | Responsabilidad y datos canónicos |
|---|---|
| `trazo_proyecto` | Versión de trazo `MULTILINESTRING(4326)`, fuente y vigencia. |
| `perfil_mapeo_importacion` | Configuración reutilizable de mapeo y opciones GIS. |
| `importacion_archivo` | Cabecera GIS: archivo, hash, formato, CRS, mapeo, estado, métricas y confirmación. |
| `importacion_feature` | Feature de staging con atributos, geometría normalizada, validación y destino. |

Los índices GiST cubren geometrías consultadas. La importación tabular y la geoespacial no comparten staging porque preservan trazabilidades distintas.

## Autenticación y seguridad

| Tabla | Responsabilidad y datos canónicos |
|---|---|
| `sesion_usuario` | Sesión opaca, hashes, expiración, revocación, IP y user-agent. |
| `estado_autenticacion_usuario` | Fallos, bloqueo y último acceso por usuario. |
| `evento_acceso` | Evento de autenticación inmutable, sesión opcional y metadatos. |

`usuario`, `usuario_proyecto`, `sesion_usuario`, `estado_autenticacion_usuario`, `evento_acceso` y `bitacora` se mantienen separados por responsabilidad.

## Objetos técnicos

`schema_migrations` contiene:

| Columna | Tipo | Regla |
|---|---|---|
| `version` | `varchar(3)` | PK |
| `nombre` | `varchar(200)` | NOT NULL |
| `checksum_sha256` | `char(64)` | NOT NULL |
| `aplicada_en` | `timestamptz` | NOT NULL, default `now()` |

PostGIS aporta `spatial_ref_sys`, `geometry_columns` y `geography_columns`.

## Vistas SOFTWARE-PA

| Vista | Fuente |
|---|---|
| `vw_proyecto_nucleo_resumen` | Proyecto/núcleo, catálogos, responsable/referencia principal y agregaciones previas. |
| `vw_dashboard_kpi` | Convocatorias, RAN/eventos, FIFONAFE/eventos, afectaciones/unidades, convenios, indemnizaciones y pagos. |
| `vw_orv_estado` | ORV, estado registral catalogado y vigencia. |
| `vw_convenio_tipo_cop_operativo` | Tipo jurídico y consecutivo del convenio. |

## Elementos que no pertenecen al Baseline V1

- tabla `bien_afectado`;
- `nucleo_agrario.tipo_nucleo`;
- `proyecto_nucleo.residencia`, `responsable_nombre`, `contacto`;
- `orv_integrante.cargo`;
- `afectacion.id_parcela`, `destino_superficie`, `no_parcela_solar`;
- textos y fechas legacy en `asamblea`;
- resúmenes RAN en `asamblea`, `convenio` u `orv`;
- pares planos de oficio/fecha en `tramite_fifonafe`;
- `expediente_requisito.id_afectacion`;
- funciones y triggers de sincronización de esos campos.
# Cierre V1 / Excel auditado

`actividad_campo.id_tipo_cop_operativo` y `asamblea.id_tipo_cop_operativo` clasifican ORIGEN, ADICIONAL, 2A_ADICIONAL, COMPLEMENTARIAS y TRANSVERSALES. `indemnizacion.estatus` incluye pendiente, programado, en_proceso, completo, pagado, cancelado y otro. No hay segundo número de parcela ni columnas de marca `X`.
