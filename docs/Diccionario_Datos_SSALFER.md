# Diccionario de datos SSALFER

> Esquema verificado: PostgreSQL/PostGIS, `schema_migrations = 035`
> Fecha de verificación: 2026-08-25
> Alcance: objetos propios vigentes después del reset controlado 031-033, la separación de privilegios 034 y la completitud operativa aditiva 035.

## 1. Convenciones

- Las PK se llaman `id_<entidad>` y son `integer` o `bigint` autogenerados, salvo catálogos y autenticación conservados.
- Las FK usan `ON DELETE RESTRICT` o el comportamiento explícito del esquema; el dominio evita cascadas destructivas.
- Las tablas funcionales auditables incluyen `activo`, `creado_en`, `creado_por`, `actualizado_en`, `actualizado_por`, `fecha_baja`, `id_usuario_baja`, `motivo_baja` y `observaciones`, salvo que se indique lo contrario.
- La baja lógica exige consistencia entre `activo` y sus metadatos. Triggers impiden el borrado físico de tablas protegidas.
- Fechas administrativas son `date`; auditoría y eventos usan `timestamptz`; importes/superficies usan `numeric`.
- Geometrías objetivo están en SRID 4326. Son apoyo técnico y no originan superficies oficiales.
- Los índices UNIQUE parciales aplican sólo a filas activas cuando el histórico debe conservarse.

## 2. Catálogo territorial y seguridad

### `entidad_federativa`

| Columna | Tipo | Nulo | Descripción |
|---|---|---:|---|
| `id_entidad` | integer | no | PK estable |
| `clave_inegi` | char(2) | no | clave natural única |
| `nombre` | varchar | no | nombre oficial |
| `activo` | boolean | no | vigencia del catálogo |

### `municipio`

| Columna | Tipo | Nulo | Descripción |
|---|---|---:|---|
| `id_municipio` | integer | no | PK determinista entidad+municipio |
| `id_entidad` | integer | no | FK a entidad |
| `clave_inegi` | char(3) | no | clave única dentro de entidad |
| `nombre` | varchar | no | municipio/alcaldía |
| `activo` | boolean | no | vigencia |

El fixture contractual contiene 32 entidades y 2,478 municipios/alcaldías activos, sin claves duplicadas.

### `usuario`

`id_usuario` PK; nombre y apellidos; `correo` único; `contrasena_hash`; `rol` (`admin`, `operador`, `visualizador`, `geografo`); estado y metadatos de baja/reactivación. Las contraseñas sólo se crean con el mecanismo seguro de administración.

### `usuario_proyecto`

`id_usuario_proyecto` PK; `id_usuario` FK; `id_proyecto` FK; `asignado_por` FK; `fecha_asignacion`; bloque auditable. UNIQUE parcial (`id_usuario`, `id_proyecto`) para asignación activa.

Los administradores tienen alcance global; los demás roles requieren una asignación activa para leer o actuar sobre un proyecto.

### Autenticación

- `estado_autenticacion_usuario`: intentos fallidos, bloqueo y último acceso por usuario.
- `sesion_usuario`: hashes de token y CSRF, expiración, revocación, IP y user-agent.
- `evento_acceso`: evento, actor, sesión, motivo, detalle, origen y `txid`.

Roles PostgreSQL: `software_pa_app` es `NOLOGIN` sin atributos administrativos; `pa_runtime` es `LOGIN`, sin `SUPERUSER`, `CREATEDB`, `CREATEROLE`, `REPLICATION` ni `BYPASSRLS`, y hereda únicamente `software_pa_app`. El owner de tablas es `pa_app`; el owner nominal de `public` es `pg_database_owner`. Runtime sólo recibe `USAGE` de schema, DML `SELECT/INSERT/UPDATE` y uso/lectura de secuencias. `schema_migrations` y `spatial_ref_sys` son sólo lectura para runtime.

## 3. Contexto administrativo

### `proyecto`

`id_proyecto` PK; `clave_proyecto` única; `nombre_proyecto`; `descripcion`; `fecha_inicio`; `fecha_fin`; bloque auditable. CHECK impide fin anterior al inicio.

### `nucleo_agrario`

| Columna funcional | Tipo | Regla |
|---|---|---|
| `id_nucleo` | integer | PK |
| `id_municipio` | integer | FK obligatoria |
| `nombre_nucleo` | varchar | obligatorio |
| `tipo_nucleo` | varchar | `ejido` o `comunidad` |
| `comunidad_indigena` | boolean | obligatorio |
| `geometria_poligono` | geometry | `MULTIPOLYGON(4326)`, opcional, válida y no vacía |
| `fuente_geometria`, `fecha_fuente_geometria` | varchar, date | procedencia cartográfica |
| `fuente_datos` | varchar | procedencia de identidad |
| `id_entidad_fuente`, `id_municipio_fuente`, `id_nucleo_fuente`, `alcance_identidad_fuente` | varchar | identificadores de origen |

La identidad activa normalizada es única por municipio, nombre y tipo. Tiene índice GiST de geometría.

### `proyecto_nucleo`

`id_proyecto_nucleo` PK; `id_proyecto` y `id_nucleo` FK; `residencia`; `responsable_nombre`; `contacto`; bloque auditable. UNIQUE parcial garantiza un solo contexto activo por proyecto+núcleo.

### `proyecto_nucleo_referencia`

`id_referencia` PK; `id_proyecto_nucleo` FK; `tipo_referencia` (`consecutivo`, `clave_tramo`, `numero_tramo`, `otro`); `valor`; `es_principal`; bloque auditable. Se permite más de una referencia por tipo/valor y sólo una principal activa por tipo.

## 4. Personas, ORV, padrón y parcelas

### `persona`

`id_persona` PK; `curp`; `rfc`; `nombre`; apellidos; teléfono; correo; `datos_identidad_incompletos`; `origen_registro` (`captura_sistema`, `excel`, `qa`, `otro`); bloque auditable. CURP activa única cuando existe.

### `orv`

`id_orv` PK; `id_nucleo` FK; `numero_orv`; `inicio_vigencia`; `fin_vigencia`; `estatus_fuente`; `acta_eleccion_inscrita_ran`; `fecha_inscripcion_acta_ran`; bloque auditable. La fecha final no puede preceder a la inicial.

### `orv_integrante`

`id_orv_integrante` PK; `id_orv`; `id_persona`; `cargo`; fechas de participación; bloque auditable. Una persona/cargo no se duplica dentro del ORV activo.

### `padron_historial`

`id_padron` PK; `id_nucleo`; `fecha_padron`; `numero_ejidatarios_comuneros`; bloque auditable. Debe existir fecha o conteo, el conteo no puede ser negativo y cada núcleo tiene un corte activo por fecha.

### `parcela`

| Columna funcional | Tipo | Regla |
|---|---|---|
| `id_parcela` | integer | PK |
| `id_nucleo` | integer | FK obligatoria |
| `tipo_parcela` | varchar | `individual`, `copropiedad`, `otro`, `no_determinado` |
| `no_parcela`, `no_parcela_ppt` | varchar | referencias únicas por núcleo cuando existen |
| `certificado_parcelario`, `folio_derechos` | varchar | referencias documentales |
| `constancia_vigencia_fecha` | date | fecha administrativa |
| `geometria_poligono` | geometry | `MULTIPOLYGON(4326)` opcional |
| `fuente_geometria`, `fecha_fuente_geometria` | varchar, date | procedencia |

Tiene bloque auditable e índice GiST. La geometría no es requisito para la ruta individual.

### `parcela_titular`

`id_parcela_titular` PK; `id_parcela`; `id_persona`; `tipo_derecho`; `porcentaje_participacion` mayor que 0 y hasta 100 cuando existe; fechas; bloque auditable. UNIQUE parcial por parcela, persona y derecho activos.

## 5. Hechos de seguimiento

### `actividad_campo`

`id_actividad` PK; `id_proyecto_nucleo`; `tipo_actividad` (`sensibilizacion`, `caminamiento`); `contexto_actividad` (`general`, `superficie_adicional`, `obras_complementarias`, `otro`); `fecha_programada`; `fecha_realizada`; `responsable`; `resultado`; bloque auditable. No tiene FK a afectación, convenio ni ciclo.

### `afectacion`

| Columna | Tipo | Descripción |
|---|---|---|
| `id_afectacion` | integer | PK |
| `id_proyecto_nucleo` | integer | contexto obligatorio |
| `id_parcela` | integer nullable | obligatoria sólo para individual |
| `tipo_afectacion` | varchar | `colectiva` o `individual` |
| `destino_superficie`, `no_parcela_solar` | varchar | clasificación/referencia administrativa |
| `superficie_preliminar_ha`, `superficie_afectada_ha` | numeric | valores capturados, no geométricos; no negativos |
| `situacion` | varchar | situación de seguimiento |
| `condicion_especial`, `descripcion_condicion` | varchar, text | condición y detalle coherente |
| `avaluo_monto`, `avaluo_fecha`, `avaluo_referencia`, `avaluo_institucion` | numeric/date/varchar | avalúo simple |

Incluye bloque auditable. CHECK exige colectiva sin parcela e individual con parcela. Un trigger exige que la parcela individual esté activa y pertenezca al núcleo del mismo `ProyectoNucleo`. No contiene geometría.

### `asamblea`

`id_asamblea` PK; `id_proyecto_nucleo`; `id_padron` opcional; `tipo_asamblea` (`anuencia`, `modificatorio`, `superficie_adicional`, `obras_complementarias`, `retiro_fondos`, `otra`); `contexto_proceso` opcional (`cop_original`, `modificatorio`, `superficie_adicional`, `obras_complementarias`, `retiro_fondos`, `otro`); propósito; expedición/programación de primera y segunda convocatoria; `fecha_realizada`; `resultado`; programación/ingreso RAN; `numero_solicitud_ran`; `calificacion_registral_ran`; `fecha_inscripcion_ran`; bloque auditable. La UI de nuevas capturas separa tipo jurídico y motivo operativo.

Un trigger exige que el padrón opcional pertenezca al mismo núcleo. Asamblea no tiene FK a afectación.

### `convenio`

| Grupo | Columnas/reglas |
|---|---|
| Identidad | `id_convenio`, `id_proyecto_nucleo`, `ambito`, `tipo_instrumento`, `tipo_convenio`, `consecutivo` |
| Variante | `modalidad_especial`, `descripcion_modalidad`, `descripcion_instrumento` |
| Relación | `id_convenio_padre`, `id_asamblea_autorizacion` |
| Firma/montos | fechas programada/real; `monto_90`, `monto_100`, `monto_bdt`, `superficie_ha` |
| RAN | fecha programada, `ingreso_ran_fecha`, solicitud, calificación e inscripción |

Ámbito es `colectivo` o `individual`. Los tipos colectivos son `cop_original`, `modificatorio`, `superficie_adicional`, `obras_complementarias`; los individuales agregan `ampliacion` y `ampliacion_remanente` según las reglas del CHECK. `permuta` sólo es modalidad de `cop_original`. Montos y superficie no pueden ser negativos. Incluye bloque auditable.

`id_asamblea_autorizacion` sólo se admite para convenio colectivo y debe apuntar a una asamblea activa del mismo contexto. Padre e hijo deben compartir contexto y ámbito.

### `convenio_afectacion`

`id_convenio_afectacion` PK; `id_convenio`; `id_afectacion`; `rol` (`principal`, `adicional`); bloque auditable. UNIQUE parcial impide duplicar el par y limita a un vínculo principal activo por convenio.

Triggers normales y diferidos validan contexto, ámbito, entidades activas y que un convenio confirmado no quede sin afectación.

### `tramite_fifonafe`

`id_tramite_fifonafe` PK; `id_proyecto_nucleo`; `ambito` colectivo/individual; `estatus` (`programado`, `pendiente`, `completo`, `cancelado`, `otro`); `acuse_fifonafe_fecha`; cuatro campos de número de oficio y sus cuatro fechas:

1. `no_oficio_fifonafe_a_dgaopr` / `fecha_oficio_fifonafe_a_dgaopr`;
2. `no_oficio_dgaopr_a_representacion` / `fecha_oficio_dgaopr_a_representacion`;
3. `no_oficio_respuesta_representacion_a_dgaopr` / `fecha_oficio_respuesta_representacion_a_dgaopr`;
4. `no_oficio_respuesta_dgaopr_a_fifonafe` / `fecha_oficio_respuesta_dgaopr_a_fifonafe`.

Además: `hay_conflictos`, `resultado_no_conflictos` y bloque auditable. El estado completo requiere los cuatro pares oficio/fecha y resultado coherente.

### `tramite_fifonafe_afectacion`

`id_tramite_fifonafe_afectacion` PK; `id_tramite_fifonafe`; `id_afectacion`; bloque auditable. UNIQUE parcial por par activo. Triggers verifican mismo contexto y ámbito, y exigen al menos una cobertura para un trámite confirmado activo.

### `indemnizacion`

`id_indemnizacion` PK; `id_afectacion`; `estatus` (`pendiente`, `programado`, `completo`, `otro`); `descripcion_estatus`; `fecha_programada`; `fecha_resolucion`; `fecha_entrega_expediente_pa`; bloque auditable. UNIQUE parcial limita a una indemnización activa por afectación.

### `pago`

`id_pago` PK; `id_indemnizacion`; `fecha_pago`; `monto > 0`; `id_persona_beneficiaria` opcional; `beneficiario_nombre` obligatorio; `referencia`; `medio_pago` (`transferencia`, `cheque`, `efectivo`, `deposito`, `otro`); bloque auditable. Una referencia activa no se duplica dentro de la indemnización.

La cadena financiera es `pago -> indemnizacion -> afectacion -> proyecto_nucleo`. No existe FK financiera obligatoria a FIFONAFE.

## 6. Documentos y trazabilidad

### `documento`

`id_documento` PK; `tipo_documento`; `estado` (`disponible`, `faltante`, `referenciado`); título; `fecha_documento`; `numero_folio`; descripción; bloque auditable.

### `documento_version`

`id_documento_version` bigint PK; `id_documento`; `numero_version > 0`; `hash_sha256` de 64 caracteres hexadecimales; `tamano_bytes`; `nombre_original`; `ruta_almacenamiento`; MIME; fecha y usuario de carga. UNIQUE por documento+versión y documento+hash. Un trigger rechaza UPDATE/DELETE: las versiones son inmutables.

### `documento_vinculo`

`id_documento_vinculo` PK; `id_documento`; `entidad_tipo`; `entidad_id`; bloque auditable. Tipos controlados: `proyecto_nucleo`, `nucleo_agrario`, `orv`, `padron_historial`, `parcela`, `afectacion`, `asamblea`, `convenio`, `tramite_fifonafe`, `indemnizacion`, `pago`. Un trigger valida tipo, objetivo existente y activo.

### `trazabilidad_fuente`

`id_trazabilidad` bigint PK; `entidad_tipo`; `entidad_id`; `archivo`; `hoja`; `fila`; `columna`; `valor_original`; `tratamiento`; `registrado_en`; `id_usuario_registro`.

Tratamientos permitidos: `PERSISTIR`, `DERIVAR`, `REFERENCIA`, `DOCUMENTAR`, `REVISAR`, `NO IMPLEMENTAR`. Un trigger valida el objetivo mediante la misma lista controlada de entidades. Los Excel permanecen fuera de Git.

### `bitacora`

`id_bitacora` bigint PK; actor; proyecto, contexto y núcleo opcionales; tipo/ID de entidad; acción; JSON anterior/nuevo; fecha; IP; user-agent. `fn_audit_log` registra inserciones y actualizaciones de las tablas funcionales auditadas.

## 7. Geoespacial e importación

### `trazo_proyecto`

`id_trazo` PK; `id_proyecto`; `version > 0`; `geometria_linea MULTILINESTRING(4326)` obligatoria, válida y no vacía; `fuente`; `fecha_fuente`; inicio/fin de vigencia; bloque auditable. UNIQUE parcial permite un trazo activo por proyecto; índice GiST para geometría.

### `perfil_mapeo_importacion`

`id_perfil` bigint PK; proyecto opcional; nombre; fuente; `tipo_objetivo`; `mapeo` y `opciones` JSON; usuario creador; bloque auditable. Objetivos: `trazo_proyecto`, `nucleo_agrario`, `parcela`.

### `catalogo_alias_territorial`

`id_alias` bigint PK; entidad; alias de nombre/clave; alias normalizado; municipio destino; fuente; vigencia; usuario aprobador; bloque auditable. Un trigger comprueba que el municipio destino pertenezca a la entidad.

### `importacion_archivo`

| Grupo | Columnas |
|---|---|
| Archivo | `id_importacion`, proyecto, objetivo, nombres, formato, tamaño, SHA-256, fuente/fecha |
| Espacial | CRS original/destino (4326) |
| Mapeo | columnas, mapeo, opciones e `id_perfil` |
| Proceso | estado, métricas de features, inicio/fin, error y reporte JSON |
| Confirmación | `confirmacion_explicita`, fecha y usuario |
| Control | `version_control` y bloque auditable |

Formatos: `geojson`, `gpkg`, `shp`, `kml`, `zip`. Estados: `subido`, `mapeado`, `procesando`, `previsualizado`, `confirmando`, `completo`, `error`, `cancelado`. UNIQUE parcial proyecto+objetivo+SHA-256 brinda idempotencia activa.

### `importacion_feature`

`id_importacion_feature` bigint PK; importación; índice de feature; capa/id externo; tipo geométrico; atributos originales/normalizados JSON; `geometria_normalizada geometry(Geometry,4326)`; estado; errores, advertencias y transformaciones JSON; aceptación/revisor; `registro_destino_id`; fechas.

Estados: `pendiente_revision`, `valido`, `advertencia`, `error`, `confirmado`, `descartado`. El trigger de objetivo exige geometría lineal para trazo, multipolígono para núcleo y permite parcela sin geometría. La confirmación conserva trazabilidad y no crea `ProyectoNucleo` por intersección.

## 8. Vistas de lectura

### `vw_orv_estado`

Expone datos de ORV y `estado_derivado` a partir de vigencias reales.

### `vw_proyecto_nucleo_resumen`

Expone proyecto, núcleo, entidad, municipio, responsable y referencia principal, más conteos independientes de actividades, asambleas, afectaciones por ámbito, parcelas, convenios y trámites FIFONAFE.

### `vw_dashboard_kpi`

Columnas: `id_proyecto`, `anio`, `indicador`, `programado`, `realizado`, `cantidad`, `superficie_ha`, `monto`.

Incluye núcleos, sensibilización, caminamiento, asambleas y RAN de acta, convenios/RAN por tipo y ámbito, retiro de fondos, expropiación directa, parcelas, FIFONAFE/no conflictos, indemnizaciones, pagos y superficies administrativas. Cada familia se agrega antes de combinarse para evitar multiplicación por las relaciones N:M.

## 9. Integridad técnica

Las funciones especializadas vigentes comprueban:

- núcleo de la parcela de una afectación individual;
- padrón de la asamblea;
- convenio padre/asamblea y asociaciones de convenio;
- coberturas FIFONAFE;
- existencia de objetivos documentales y de trazabilidad;
- destino de aliases e importaciones;
- inmutabilidad de versiones documentales;
- auditoría y prevención de borrado físico.

Las funciones N:M usan constraint triggers diferidos para permitir creación transaccional y validar el estado final de la transacción. Los índices parciales cubren unicidad activa; los GiST cubren geometrías; los índices de FK/estado soportan autorización, navegación y dashboard.

## 10. Objetos técnicos y objetos retirados

`schema_migrations(version, descripcion, aplicada_en)` registra hasta 035. `spatial_ref_sys`, `geometry_columns` y `geography_columns` pertenecen a PostGIS. Los default privileges del owner conceden al rol NOLOGIN sólo `SELECT/INSERT/UPDATE` en tablas futuras y `USAGE/SELECT` en secuencias; PUBLIC no recibe DML ni `CREATE` en `public`.

No existen en el esquema 035 las tablas/vistas funcionales retiradas: `tramo`, `tramo_nucleo`, `afectacion_ciclo`, `usuario_tramo`, `seccion_derecho_via`, `franja_derecho_via`, `candidato_tramo_nucleo`, `carga_geoespacial` ni `carga_geoespacial_feature`. Su historia permanece únicamente en migraciones 001-030.
