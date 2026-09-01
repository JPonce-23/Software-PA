# Diccionario de datos SSALFER

> Esquema verificado: PostgreSQL/PostGIS, `schema_migrations = 039`
> Fecha de verificación: 2026-09-01
> Alcance: objetos propios vigentes después del reset controlado 031-033, la separación de privilegios 034, la completitud 035, el modelo operativo colectivo normalizado 036, la normalización de unidad agraria 037, el cierre legacy Asamblea/RAN/FIFONAFE 038 y el modelo operativo individual y expediente por objetivo 039.

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
| `tipo_nucleo` | varchar | proyección legacy sincronizada (`ejido` o `comunidad`) |
| `id_tipo_tenencia` | bigint | FK obligatoria a catálogo `tipo_tenencia` |
| `comunidad_indigena` | boolean | trivalente: `NULL` no capturado, `true` sí, `false` no |
| `geometria_poligono` | geometry | `MULTIPOLYGON(4326)`, opcional, válida y no vacía |
| `fuente_geometria`, `fecha_fuente_geometria` | varchar, date | procedencia cartográfica |
| `fuente_datos` | varchar | procedencia de identidad |
| `id_entidad_fuente`, `id_municipio_fuente`, `id_nucleo_fuente`, `alcance_identidad_fuente` | varchar | identificadores de origen |

La identidad activa normalizada es única por municipio, nombre y tipo. Tiene índice GiST de geometría.

### `proyecto_nucleo`

`id_proyecto_nucleo` PK; `id_proyecto` y `id_nucleo` FK; `id_residencia` catalogada; `total_cops_planeados >= 0`; campos legacy de residencia/responsable sólo para compatibilidad; bloque auditable. UNIQUE parcial garantiza un solo contexto activo por proyecto+núcleo. `proyecto_nucleo_responsable` conserva responsables sucesivos 1:N con nombre, cargo, contacto y vigencia.

### `proyecto_nucleo_referencia`

`id_referencia` PK; `id_proyecto_nucleo` FK; `tipo_referencia` (`consecutivo`, `clave_tramo`, `numero_tramo`, `otro`); `valor`; `es_principal`; bloque auditable. Se permite más de una referencia por tipo/valor y sólo una principal activa por tipo.

## 4. Personas, ORV, padrón y parcelas

### `persona`

`id_persona` PK; `curp`; `rfc`; `nombre`; apellidos; teléfono; correo; `datos_identidad_incompletos`; `origen_registro` (`captura_sistema`, `excel`, `qa`, `otro`); bloque auditable. CURP activa única cuando existe.

### `orv`

`id_orv` PK; `id_nucleo` FK; `numero_orv`; `inicio_vigencia`; `fin_vigencia`; `estatus_fuente`; `id_estado_registral` catalogado (`no_ingresada`, `en_proceso`, `prevenida`, `inscrita`, `otro`); campos boolean/fecha legacy como proyección; bloque auditable. La fecha final no puede preceder a la inicial. `fecha_inscripcion_acta_ran` y cualquier resumen registral conservado en ORV son proyecciones READ-ONLY del historial RAN desde 038; la fuente registral canónica es `tramite_ran` + `tramite_ran_evento`. ORV pertenece al `NucleoAgrario`; no se selecciona ni inventa un `ProyectoNucleo` para contextualizar un trámite registral del ORV.

### `orv_integrante`

`id_orv_integrante` PK; `id_orv`; `id_persona`; `id_organo`, `id_cargo` e `id_calidad` catalogados; `cargo` legacy; fechas de participación; bloque auditable. Permite Comisariado y Consejo de Vigilancia, cargos Presidente/Secretario/Tesorero/Secretario 1/Secretario 2 y calidad propietario/suplente.

### `padron_historial`

`id_padron` PK; `id_nucleo`; `fecha_padron`; `numero_ejidatarios_comuneros`; `fuente`; `id_documento`; bloque auditable. Debe existir fecha o conteo, el conteo no puede ser negativo y cada núcleo tiene un corte activo por fecha. La fuente tabular conserva textos no normalizables como `SD` sin forzarlos a `date`.

### `parcela`

| Columna funcional | Tipo | Regla |
|---|---|---|
| `id_parcela` | integer | PK |
| `id_nucleo` | integer | FK obligatoria |
| `tipo_parcela` | varchar | `individual`, `copropiedad`, `otro`, `no_determinado` |
| `no_parcela` | varchar | identificador canónico, único por núcleo tras normalizar espacios y mayúsculas/minúsculas |
| `certificado_parcelario`, `folio_derechos` | varchar | referencias documentales |
| `constancia_vigencia_fecha` | date | fecha administrativa |
| `geometria_poligono` | geometry | `MULTIPOLYGON(4326)` opcional |
| `fuente_geometria`, `fecha_fuente_geometria` | varchar, date | procedencia |

Tiene bloque auditable e índice GiST. La geometría no es requisito para la ruta individual.

### `parcela_titular`

`id_parcela_titular` PK; `id_parcela`; `id_persona`; `tipo_derecho`; `porcentaje_participacion` mayor que 0 y hasta 100 cuando existe; fechas; bloque auditable. UNIQUE parcial por parcela, persona y derecho activos.

## 5. Hechos de seguimiento

### `actividad_campo`

`id_actividad` PK; `id_proyecto_nucleo`; `id_afectacion` opcional del mismo ProyectoNucleo; `tipo_actividad` (`sensibilizacion`, `caminamiento`); `contexto_actividad` (`general`, `superficie_adicional`, `obras_complementarias`, `otro`); `fecha_programada`; `fecha_realizada`; `responsable`; `resultado`; bloque auditable. NULL en `id_afectacion` representa una actividad general del núcleo.


### `unidad_agraria`

Identidad estable del bien o unidad perteneciente al Núcleo Agrario.
`id_unidad_agraria` bigint PK GENERATED BY DEFAULT AS IDENTITY.
FKs: `id_nucleo` (NOT NULL), `id_tipo_tierra` (NOT NULL), `id_tipo_gestion`, `id_destino_superficie`, `id_parcela` (opcional hacia proceso individual legacy).
Atributos: `referencia_alfanumerica`, `detalle`, `superficie_ha`, `requiere_revision`, `motivo_revision`.
Incluye control de vigencia (`activo`, `fecha_baja`, `motivo_baja`, `id_usuario_baja`) y auditoría (`creado_por`, `creado_en`, `actualizado_por`, `actualizado_en`).
Constraints: `chk_unidad_agraria_dato` asegura que exista algún dato identificativo y los triggers prohíben el DELETE físico.

### `unidad_agraria_titular`

Entidad para la vinculación entre `unidad_agraria` y los titulares (`id_persona` o `id_parcela_titular`).
`id_unidad_titular` bigint PK. Relaciona 1:N titulares por unidad agraria preservando historial con inicio/fin de vigencia. UNIQUE parcial para no duplicar relaciones activas. Evita nombres libres reutilizando la identidad de Persona.

### `afectacion_unidad_agraria`

Relación N:M entre `afectacion` y `unidad_agraria`.
`id_afectacion_unidad` bigint PK.
FKs: `id_afectacion`, `id_unidad_agraria`.
Atributos propios de la relación (no es un simple secondary table): `superficie_preliminar_ha`, `superficie_afectada_ha`, `superficie_valor_original`, `superficie_formato_origen`, `fuente`.
Un constraint UNIQUE impide relaciones activas duplicadas entre la misma afectación y unidad. Un trigger restringe que ambas entidades compartan el mismo `id_nucleo` para garantizar integridad.

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

Incluye bloque auditable. CHECK exige parcela sólo para la afectación individual; una colectiva sí puede referenciar una parcela. El trigger exige que cualquier parcela relacionada esté activa y pertenezca al núcleo del mismo `ProyectoNucleo`. `tipo_afectacion` es independiente de `tipo_gestion`.

### `asamblea`

`id_asamblea` PK; `id_proyecto_nucleo`; `id_padron` opcional; `id_tipo_asamblea` e `id_contexto_asamblea` catalogados; propósito; fecha/resultado de cierre; bloque auditable. Los campos legacy de convocatoria (`fecha_expedicion_primera`, `fecha_programada_primera`, `fecha_expedicion_segunda`, `fecha_programada_segunda`, `fecha_realizada`) y los campos legacy RAN (`fecha_programada_ingreso_ran`, `fecha_ingreso_ran`, `numero_solicitud_ran`, `calificacion_registral_ran`, `fecha_inscripcion_ran`) son READ-ONLY desde 038: triggers de la migración 038 bloquean escritura directa. La fuente canónica de convocatorias es `asamblea_convocatoria` y la fuente canónica RAN es `tramite_ran` + `tramite_ran_evento`.

### `asamblea_convocatoria`

`id_convocatoria` PK; `id_asamblea`; `ordinal > 0`; fechas de expedición, programación y realización; `id_resultado` catalogado; observaciones; `id_documento`; bloque auditable. UNIQUE parcial por asamblea+ordinal. Es la fuente canónica repetible para convocatorias y actas de no verificativo.

Un trigger exige que el padrón opcional pertenezca al mismo núcleo. Asamblea no tiene FK a afectación. Crear una asamblea NO genera automáticamente un `TramiteRan`.

### `convenio`

| Grupo | Columnas/reglas |
|---|---|
| Identidad | `id_convenio`, `id_proyecto_nucleo`, `ambito`, `tipo_instrumento`, `tipo_convenio`, `consecutivo` |
| Variante | `modalidad_especial`, `descripcion_modalidad`, `descripcion_instrumento` |
| Relación | `id_convenio_padre`, `id_asamblea_autorizacion` |
| Firma/montos | fechas programada/real; `monto_90`, `monto_100`, `monto_bdt`, `superficie_ha` |
| RAN (READ-ONLY desde 038) | fecha programada, `ingreso_ran_fecha`, solicitud, calificación e inscripción; proyección del historial RAN, no fuente de escritura |

Ámbito es `colectivo` o `individual`. Los tipos colectivos son `cop_original`, `modificatorio`, `superficie_adicional`, `obras_complementarias`; los individuales son `cop_original` (sin padre) y `modificatorio`, `ampliacion`, `ampliacion_remanente` (requieren padre individual del mismo ProyectoNucleo, sin ciclos). `permuta` sólo es modalidad de `cop_original`. Montos y superficie no pueden ser negativos. Incluye bloque auditable. Crear un convenio NO genera automáticamente un `TramiteRan`. La fuente canónica RAN es `tramite_ran` + `tramite_ran_evento`.

`id_asamblea_autorizacion` sólo se admite para convenio colectivo y debe apuntar a una asamblea activa del mismo contexto. Padre e hijo deben compartir contexto y ámbito. En el modelo individual (039), crear un convenio hijo NO copia automáticamente las afectaciones del padre; el cliente/API debe asociar las afectaciones correspondientes y un constraint trigger diferido (`fn_039_validar_linaje_unidad_individual`) valida que padre e hijo compartan al menos una `UnidadAgraria` efectivamente vinculada.

### `convenio_compareciente`

`id_compareciente` PK; `id_convenio` FK; `id_persona` FK; `id_parcela_titular` FK opcional; `id_tipo_calidad` e `id_tipo_acreditacion` catalogados; `referencia_acreditacion`; `nombre_en_instrumento`; `es_firmante`; bloque auditable. Un constraint trigger diferido (`fn_039_validar_convenio_compareciente_unidad`) valida que, si se especifica `id_parcela_titular`, la parcela correspondiente pertenezca a una `UnidadAgraria` efectivamente afectada por el convenio. Representa una instantánea auditable de la comparecencia y firma del instrumento sin alterar la titularidad histórica de `parcela_titular`.

### `convenio_afectacion`

`id_convenio_afectacion` PK; `id_convenio`; `id_afectacion`; `rol` (`principal`, `adicional`); bloque auditable. UNIQUE parcial impide duplicar el par y limita a un vínculo principal activo por convenio.

Triggers normales y diferidos validan contexto, ámbito, entidades activas y que un convenio confirmado no quede sin afectación.

### `tramite_fifonafe`

`id_tramite_fifonafe` PK; `id_proyecto_nucleo`; `ambito` colectivo/individual; estatus, acuse, conflictos y bloque auditable. Los siguientes campos propios del trámite continúan siendo canónicos: `estatus`, `acuse_fifonafe_fecha`, `hay_conflictos`, `resultado_no_conflictos`. Los cuatro pares históricos de oficios siguientes son READ-ONLY/proyección desde 038; la fuente canónica es `tramite_fifonafe_evento`:

1. `no_oficio_fifonafe_a_dgaopr` / `fecha_oficio_fifonafe_a_dgaopr`;
2. `no_oficio_dgaopr_a_representacion` / `fecha_oficio_dgaopr_a_representacion`;
3. `no_oficio_respuesta_representacion_a_dgaopr` / `fecha_oficio_respuesta_representacion_a_dgaopr`;
4. `no_oficio_respuesta_dgaopr_a_fifonafe` / `fecha_oficio_respuesta_dgaopr_a_fifonafe`.

Los triggers de la migración 038 (`trg_038_fifonafe_legacy_readonly`) bloquean escritura directa a estos campos. Además, el estatus `completo` requiere los cuatro eventos canónicos definidos por 038, cada uno con `numero_oficio` y `fecha_oficio` no vacíos, validados por los constraint triggers diferidos `ctr_038_fifonafe_completo_insert` y `ctr_038_fifonafe_completo_update`.

### `tramite_fifonafe_evento`

`id_evento_fifonafe` PK; `id_tramite_fifonafe`; `ordinal > 0`; `id_tipo_evento` catalogado; origen/destino; número y fecha de oficio; `id_documento`; observaciones; bloque auditable. Es la fuente canónica 1:N y admite reenvíos, correcciones y respuestas múltiples.

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

`schema_migrations(version, descripcion, aplicada_en)` registra hasta 039. `spatial_ref_sys`, `geometry_columns` y `geography_columns` pertenecen a PostGIS. Los default privileges del owner conceden al rol NOLOGIN sólo `SELECT/INSERT/UPDATE` en tablas futuras y `USAGE/SELECT` en secuencias; PUBLIC no recibe DML ni `CREATE` en `public`.

No existen en el esquema 036 las tablas/vistas funcionales retiradas: `tramo`, `tramo_nucleo`, `afectacion_ciclo`, `usuario_tramo`, `seccion_derecho_via`, `franja_derecho_via`, `candidato_tramo_nucleo`, `carga_geoespacial` ni `carga_geoespacial_feature`. Su historia permanece únicamente en migraciones 001-030.

## 11. Objetos introducidos por el modelo operativo 036 y extendidos en 039

### `catalogo_operativo` y `catalogo_operativo_alias`

`catalogo_operativo` contiene PK bigint, `tipo_catalogo`, `codigo` estable e inmutable, `nombre` editable, descripción, orden, fuente, inicio/fin de vigencia y bloque auditable. UNIQUE parcial por tipo+código. No admite borrado físico; una opción inactiva conserva todas sus FK históricas. `catalogo_operativo_alias` resuelve variantes de fuente por catálogo y texto normalizado. Los códigos iniciales no limitan futuras altas por API.

### `bien_afectado`

`id_bien_afectado` PK; `id_afectacion`; FKs opcionales a catálogos `tipo_gestion`, `destino_superficie` y `tipo_cop_operativo`; `id_parcela` opcional; tipo de tierra; referencia alfanumérica; titularidad; detalle; superficies preliminar/afectada en ha; valor y formato originales; fuente; bloque auditable. Requiere al menos una clasificación o referencia. Una referencia de parcela no convierte por sí sola el derecho en individual.

### `tramite_ran` y `tramite_ran_evento`

`tramite_ran` contiene objetivo tipado mediante exactamente una FK no nula (`id_asamblea`, `id_convenio` o `id_orv`), propósito, estado y bloque auditable. Desde 038, la cardinalidad es **1:N por objetivo** (ya no existe restricción 1:1 por unique index). El contexto se bifurca en dos columnas:

- Para Asamblea y Convenio: `id_proyecto_nucleo` NOT NULL, `id_nucleo` NULL.
- Para ORV: `id_nucleo` NOT NULL, `id_proyecto_nucleo` NULL.

El constraint `chk_tramite_ran_contexto_038` garantiza la integridad. Un trigger (`fn_038_validar_tramite_ran_contexto`) comprueba que el objetivo pertenece al ProyectoNucleo o NucleoAgrario correctos. No se usa una FK polimórfica insegura.

`tramite_ran_evento` contiene trámite, ordinal, tipo catalogado, fecha, intento, número de solicitud, resultado, calificación, folio/referencia, observaciones, documento y bloque auditable. UNIQUE parcial por trámite+ordinal. Ingreso, reingreso, prevención, corrección, desistimiento, calificación e inscripción se preservan como hechos separados.

### Convenio operativo

`vw_convenio_tipo_cop_operativo` deriva la etiqueta de Datos Generales: `cop_original/1 -> ORIGEN`, `superficie_adicional/1 -> ADICIONAL`, `superficie_adicional/2 -> 2A ADICIONAL` y `obras_complementarias -> COMPLEMENTARIAS`. `modificatorio` continúa como tipo jurídico. El trigger de relaciones valida mismo `ProyectoNucleo`, mismo ámbito, semántica padre/hijo, ausencia de ciclos y coherencia con la asamblea autorizante.

### Checklist documental

`requisito_documental` define código estable, etiqueta, descripción, etapa, ámbito, obligatoriedad, orden, fuente, vigencia y auditoría. En 039 se incorporaron requisitos documentales para el expediente individual (`ind_derecho_acreditacion`, `ind_convenio_firmado`, `ind_ran_acuse_ingreso`, `ind_ran_inscripcion`, `ind_fif_*`).

`expediente_requisito` asocia un requisito a `ProyectoNucleo` y opcionalmente a un objetivo específico mediante `entidad_tipo` y `entidad_id` (admitiendo `proyecto_nucleo`, `afectacion`, `parcela`, `parcela_titular`, `unidad_agraria`, `unidad_agraria_titular`, `convenio`, `convenio_compareciente`, `tramite_ran`, `tramite_ran_evento`, `tramite_fifonafe`, `tramite_fifonafe_evento`, `indemnizacion`, `pago`), con estado catalogado, documento, observaciones y auditoría. Un trigger (`fn_039_validar_expediente_requisito_objetivo`) valida que todo objetivo documental pertenezca al `ProyectoNucleo` indicado.

### Importación tabular

`importacion_tabular` conserva archivo, nombre original, SHA-256, fuente, fecha, estado, métricas y auditoría; UNIQUE parcial por proyecto+SHA-256. `importacion_tabular_celda` conserva hoja, fila, columna, encabezado, valor original, valor normalizado, tratamiento (`persistir`, `derivar`, `referencia`, `documentar`, `revisar`, `no_implementar`), advertencias, errores y vínculo destino. `trazabilidad_fuente.id_importacion_tabular` enlaza la entidad funcional con la cabecera de importación y conserva en la propia trazabilidad sus coordenadas y valores de celda. Este flujo no reutiliza staging GIS.

## 12. Compatibilidad y deprecación

Los campos planos de convocatoria y RAN en `asamblea`/`convenio`, los cuatro pares de oficio en `tramite_fifonafe`, `fecha_inscripcion_acta_ran` en `orv`, el tipo de núcleo textual y los responsables planos son exclusivamente compatibilidad. Desde 038, triggers read-only bloquean escritura directa a estos campos legacy; las funciones de resumen (`fn_038_refrescar_resumen_ran`) proyectan desde los modelos canónicos. Las escrituras de API crean eventos canónicos y no escriben campos legacy. No deben utilizarse para reportes nuevos. Su retiro se evaluará después de migrar totalmente el frontend.
