# Diccionario de datos — SOFTWARE-PA / SSALFER

> Inventario técnico de la base de datos ejecutada en el contenedor local.
> Verificado directamente contra PostgreSQL el 29 de julio de 2026.

## 1. Estado del esquema verificado

| Concepto | Valor |
| --- | --- |
| Motor | PostgreSQL 15.4 |
| Extensión espacial | PostGIS 3.3.4 |
| Esquema | `public` |
| Migración registrada | `028` — Trazo lineal sin inferencia de anchos |
| Tablas de aplicación | 42 |
| Vistas de aplicación | 5 |
| Funciones propias | 19 |
| Triggers lógicos | 96 |
| Índices adicionales | 21 |

La fuente ejecutable sigue siendo:

- `backend/db/migrations/001_init_schema.sql`: esquema consolidado para una
  instalación limpia.
- `backend/db/migrations/003_add_proyecto_drop_frente.sql`: transición que
  incorporó `proyecto`, `usuario_tramo` y retiró `frente`.
- `backend/db/migrations/004_adaptaciones_fase2.sql`: personas normalizadas,
  titulares, integrantes ORV, minutas, acuerdos, versiones documentales,
  pagos y alertas.
- `backend/db/migrations/028_trazo_lineal_sin_anchos.sql`: Trazo lineal sin inferencia de anchos.

La instancia actual **no contiene** las tablas `frente` ni `usuario_frente`.
`tramo_nucleo` tampoco contiene `id_frente`.

PostGIS crea adicionalmente `spatial_ref_sys`, `geometry_columns` y
`geography_columns`. `schema_migrations` es una tabla técnica de control y no
forma parte del dominio.

## 2. Convenciones

| Marca | Significado |
| --- | --- |
| PK | Llave primaria |
| FK | Llave foránea |
| NN | `NOT NULL` |
| UQ | Restricción o índice único |
| D | Valor predeterminado |
| LEGACY | Columna temporal conservada para compatibilidad |

Los identificadores descritos como `SERIAL` o `BIGSERIAL` se observan en el
catálogo como `INTEGER` o `BIGINT` con una secuencia en su valor
predeterminado.

### 2.1 Bloques de ciclo de vida

Para evitar repetir ocho columnas en casi todas las tablas, se utilizan estos
bloques:

**CV-A — baja lógica sin FK declarada en los campos de actor**

| Campo | Tipo | NN | Predeterminado |
| --- | --- | --- | --- |
| `activo` | `BOOLEAN` | Sí | `TRUE` |
| `fecha_baja` | `TIMESTAMPTZ` | No | — |
| `id_usuario_baja` | `INTEGER` | No | — |
| `motivo_baja` | `TEXT` | No | — |
| `fecha_reactivacion` | `TIMESTAMPTZ` | No | — |
| `id_usuario_reactivacion` | `INTEGER` | No | — |
| `motivo_reactivacion` | `TEXT` | No | — |
| `observaciones` | `TEXT` | No | — |

**CV-B — baja lógica con FK hacia `usuario`**

Contiene las mismas columnas de CV-A, pero `id_usuario_baja` e
`id_usuario_reactivacion` son FK hacia `usuario.id_usuario`.

**CV-C — catálogo básico**

Sólo contiene `activo BOOLEAN NOT NULL DEFAULT TRUE`.

En las tablas con CV-A o CV-B, el motor bloquea el `DELETE` físico y exige
actor, fecha y motivo cuando `activo` cambia. `entidad_federativa` y
`municipio` tienen CV-C y bloqueo de `DELETE`, pero no poseen los metadatos
completos de baja.

## 3. Jerarquía y cardinalidades principales

```text
Proyecto 1 ── N Tramo
Tramo 1 ── N Tramo_Núcleo
Núcleo_Agrario 1 ── N Tramo_Núcleo
Tramo_Núcleo 1 ── N Afectación
Afectación 1 ── N Convenio
Convenio 1 ── 0..N Trámite_FIFONAFE
Trámite_FIFONAFE 1 ── N Pago_Indemnización
```

Conceptualmente:

```text
tramo_nucleo = expediente maestro territorial de liberación
afectacion   = subexpediente operativo confirmado
```

Un `tramo_nucleo` conserva el contexto compartido de investigación,
sensibilización, caminamiento y seguimiento global. Cada `afectacion`
representa una rama colectiva o individual confirmada.

## 4. Estructura territorial y acceso

### 4.1 `proyecto`

Contenedor superior de los tramos de una obra ferroviaria. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_proyecto` | `SERIAL` | PK, NN | Identificador. |
| `clave_proyecto` | `VARCHAR(30)` | NN, UQ | Clave estable del proyecto. |
| `nombre_proyecto` | `VARCHAR(200)` | NN | Nombre descriptivo. |
| `descripcion` | `TEXT` | — | Descripción libre. |
| `fecha_registro` | `DATE` | NN, D `CURRENT_DATE` | Alta funcional. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

### 4.2 `tramo`

Segmento territorial y unidad de asignación operativa. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_tramo` | `SERIAL` | PK, NN | Identificador. |
| `id_proyecto` | `INTEGER` | FK, NN | → `proyecto.id_proyecto`. |
| `clave_tramo` | `VARCHAR(20)` | NN | Única dentro del proyecto. |
| `nombre_tramo` | `VARCHAR(200)` | NN | Nombre del tramo. |
| `descripcion` | `TEXT` | — | Descripción libre. |
| `ancho_total_derecho_via_m` | `NUMERIC(6,2)` | —, D `40.00` | Ancho para construir el búfer espacial; debe ser positivo. |
| `geometria_linea` | `geometry(MultiLineString,4326)` | — | Eje geográfico del tramo. |
| `fecha_registro` | `DATE` | NN, D `CURRENT_DATE` | Fecha de alta. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

Restricciones: `UNIQUE(id_proyecto, clave_tramo)` y
`ancho_total_derecho_via_m > 0`.

### 4.3 `entidad_federativa`

Catálogo de entidades federativas. Usa CV-C.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_entidad` | `SERIAL` | PK, NN | Identificador. |
| `clave_inegi` | `CHAR(2)` | NN, UQ | Clave INEGI. |
| `nombre` | `VARCHAR(100)` | NN | Nombre oficial. |
| `activo` | `BOOLEAN` | NN, D `TRUE` | Estado lógico. |

### 4.4 `municipio`

Catálogo de municipios registrales. Usa CV-C.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_municipio` | `SERIAL` | PK, NN | Identificador. |
| `id_entidad` | `INTEGER` | FK, NN | → `entidad_federativa.id_entidad`. |
| `clave_inegi` | `CHAR(5)` | NN, UQ | Clave INEGI. |
| `nombre` | `VARCHAR(150)` | NN | Nombre oficial. |
| `activo` | `BOOLEAN` | NN, D `TRUE` | Estado lógico. |

Además existe `UNIQUE(id_entidad, clave_inegi)`.

### 4.5 `nucleo_agrario`

Ejido o comunidad propietaria de tierra social. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_nucleo` | `SERIAL` | PK, NN | Identificador. |
| `id_municipio` | `INTEGER` | FK, NN | → `municipio.id_municipio`. |
| `nombre_nucleo` | `VARCHAR(300)` | NN | Denominación registral. |
| `tipo_nucleo` | `VARCHAR(20)` | NN | `ejido` o `comunidad`. |
| `comunidad_indigena` | `BOOLEAN` | NN, D `FALSE` | Identifica el régimen de atención correspondiente. |
| `residencia` | `VARCHAR(300)` | — | Oficina o residencia responsable. |
| `geometria_poligono` | `geometry(MultiPolygon,4326)` | — | Polígono del núcleo. |
| `fecha_creacion` | `TIMESTAMPTZ` | NN, D `NOW()` | Fecha técnica de creación. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

### 4.6 `tramo_nucleo`

Cruce entre tramo y núcleo. Es el expediente maestro territorial de
liberación. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_tramo_nucleo` | `SERIAL` | PK, NN | Identificador del expediente maestro. |
| `id_tramo` | `INTEGER` | FK, NN | → `tramo.id_tramo`. |
| `id_nucleo` | `INTEGER` | FK, NN | → `nucleo_agrario.id_nucleo`. |
| `consecutivo` | `INTEGER` | NN | Consecutivo único dentro del tramo. |
| `numero_tramo` | `VARCHAR(50)` | — | Referencia operativa complementaria. |
| `geometria_segmento` | `geometry(MultiLineString,4326)` | — | Segmento de vía dentro del núcleo. |
| `longitud_m` | `NUMERIC(14,2)` | — | Longitud no negativa en metros. |
| `es_expropiacion` | `BOOLEAN` | NN, D `FALSE` | Marca la vía de expropiación directa. |
| `causa_problema` | `TEXT` | — | Obstáculo o incidencia del expediente. |
| `proyecto_no_afecta_uso_comun` | `BOOLEAN` | — | Impide afectaciones colectivas cuando es verdadero. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

Restricciones:

- `UNIQUE(id_tramo, consecutivo)`.
- `UNIQUE(id_nucleo, id_tramo_nucleo)`, usada por FK compuestas.
- `longitud_m >= 0`.

### 4.7 `usuario_tramo`

Asignación de usuarios a tramos; reemplaza a `usuario_frente`. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_usuario_tramo` | `SERIAL` | PK, NN | Identificador. |
| `id_usuario` | `INTEGER` | FK, NN | → `usuario.id_usuario`. |
| `id_tramo` | `INTEGER` | FK, NN | → `tramo.id_tramo`. |
| `fecha_asignacion` | `TIMESTAMPTZ` | NN, D `NOW()` | Fecha de asignación. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

Restricción: `UNIQUE(id_usuario, id_tramo)`.

### 4.8 `franja_derecho_via`

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_franja` | `SERIAL` | PK, NN | Identificador. |
| `id_tramo` | `INTEGER` | FK | Tramo. |
| `version` | `INTEGER` | NN | Versión de franja. |
| `ancho_izquierdo_m` | `NUMERIC` | — | Ancho izquierdo. |
| `ancho_derecho_m` | `NUMERIC` | — | Ancho derecho. |
| `geometria_poligono` | `geometry(MultiPolygon,4326)` | — | Polígono. |
| `fuente` | `VARCHAR(200)` | NN | Fuente. |
| `fecha_vigencia_inicio` | `DATE` | NN | Inicio vigencia. |
| `fecha_vigencia_fin` | `DATE` | — | Fin vigencia. |
| `id_proyecto` | `INTEGER` | NN | Proyecto. |
| `geometria_linea` | `geometry(MultiLineString,4326)` | — | Linea. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

### 4.9 `seccion_derecho_via`

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_seccion` | `BIGSERIAL` | PK, NN | Identificador. |
| `id_franja` | `INTEGER` | NN | Franja. |
| `id_tramo` | `INTEGER` | NN | Tramo. |
| `geometria_poligono` | `geometry(MultiPolygon,4326)` | NN | Polígono. |
| `fuente` | `VARCHAR(200)` | NN | Fuente. |
| `fecha_registro` | `TIMESTAMPTZ` | NN, D `NOW()` | Fecha de registro. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

### 4.10 `candidato_tramo_nucleo`

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_candidato` | `BIGSERIAL` | PK, NN | Identificador. |
| `id_tramo` | `INTEGER` | NN | Tramo. |
| `id_nucleo` | `INTEGER` | NN | Núcleo. |
| `id_franja` | `INTEGER` | NN | Franja. |
| `area_interseccion_m2` | `NUMERIC(24,4)` | NN | Área. |
| `estado` | `VARCHAR(20)` | NN, D `pendiente` | Estado. |
| `fecha_deteccion` | `TIMESTAMPTZ` | NN, D `NOW()` | Detección. |
| `id_usuario_deteccion` | `INTEGER` | NN | Usuario que detecta. |
| `fecha_resolucion` | `TIMESTAMPTZ` | — | Resolución. |
| `id_usuario_resolucion` | `INTEGER` | — | Usuario resolutor. |
| `motivo_resolucion` | `VARCHAR(500)` | — | Motivo. |
| `id_tramo_nucleo` | `INTEGER` | — | Tramo núcleo. |
| `id_seccion` | `BIGINT` | NN | Sección. |

### 4.11 `catalogo_alias_territorial`

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_alias` | `BIGSERIAL` | PK, NN | Identificador. |
| `id_entidad` | `INTEGER` | NN | Entidad. |
| `alias_nombre` | `VARCHAR(200)` | — | Nombre. |
| `alias_normalizado` | `VARCHAR(200)` | NN | Nombre normalizado. |
| `alias_clave` | `VARCHAR(20)` | — | Clave. |
| `id_municipio_destino` | `INTEGER` | NN | Municipio destino. |
| `fuente` | `VARCHAR(300)` | NN | Fuente. |
| `fecha_vigencia_inicio` | `DATE` | — | Inicio de vigencia. |
| `fecha_vigencia_fin` | `DATE` | — | Fin de vigencia. |
| `fecha_aprobacion` | `TIMESTAMPTZ` | NN, D `NOW()` | Aprobación. |
| `id_usuario_aprobador` | `INTEGER` | NN | Usuario aprobador. |
| `activo` | `BOOLEAN` | NN, D `TRUE` | Activo. |

## 5. Personas, representación y derechos individuales

### 5.1 `persona`

Catálogo único de personas físicas. Usa CV-B.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_persona` | `SERIAL` | PK, NN | Identificador. |
| `curp` | `VARCHAR(18)` | UQ parcial | CURP normalizada; formato validado cuando existe. |
| `rfc` | `VARCHAR(13)` | — | RFC con formato validado cuando existe. |
| `nombre` | `VARCHAR(300)` | NN | Nombre no vacío. |
| `apellido_paterno` | `VARCHAR(200)` | — | Primer apellido. |
| `apellido_materno` | `VARCHAR(200)` | — | Segundo apellido. |
| `telefono` | `VARCHAR(20)` | — | Teléfono. |
| `correo_electronico` | `VARCHAR(320)` | — | Correo no vacío cuando existe. |
| `datos_identidad_incompletos` | `BOOLEAN` | NN, D `FALSE` | Marca registros pendientes de completar. |
| `origen_registro` | `VARCHAR(30)` | NN, D `captura_sistema` | `captura_sistema` o `migracion_legacy`. |
| `clave_origen_legacy` | `VARCHAR(150)` | UQ | Identificador estable de migración. |
| Bloque CV-B | — | — | Ciclo de vida y observaciones. |

### 5.2 `persona_nucleo`

Relación de una persona con un núcleo agrario. Usa CV-B.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_persona_nucleo` | `SERIAL` | PK, NN | Identificador. |
| `id_persona` | `INTEGER` | FK, NN | → `persona.id_persona`. |
| `id_nucleo` | `INTEGER` | FK, NN | → `nucleo_agrario.id_nucleo`. |
| `calidad_agraria` | `VARCHAR(30)` | — | `ejidatario`, `comunero`, `avecindado`, `posesionario`, `representante` u `otro`. |
| `fecha_inicio` | `DATE` | — | Inicio de la relación. |
| `fecha_fin` | `DATE` | — | Fin; no puede ser anterior al inicio. |
| Bloque CV-B | — | — | Ciclo de vida y observaciones. |

Restricción: `UNIQUE(id_nucleo, id_persona)`.

### 5.3 `persona_fuente_legacy`

Linaje de identidades provenientes de columnas heredadas. Usa CV-B.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_persona_fuente` | `SERIAL` | PK, NN | Identificador. |
| `id_persona` | `INTEGER` | FK, NN | → `persona.id_persona`. |
| `tabla_origen` | `VARCHAR(40)` | NN | `orv` o `parcela`. |
| `id_registro_origen` | `INTEGER` | NN | PK del registro heredado. |
| `campo_origen` | `VARCHAR(80)` | NN | Nombre de la columna fuente. |
| `valor_original` | `TEXT` | NN | Texto sin modificar. |
| `valor_normalizado` | `TEXT` | NN | Texto usado para conciliación. |
| `requiere_revision` | `BOOLEAN` | NN, D `TRUE` | Señala identidad no conciliada. |
| Bloque CV-B | — | — | Ciclo de vida y observaciones. |

Restricción:
`UNIQUE(tabla_origen, id_registro_origen, campo_origen)`.

### 5.4 `parcela`

Unidad parcelaria dentro de un núcleo. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_parcela` | `SERIAL` | PK, NN | Identificador. |
| `id_nucleo` | `INTEGER` | FK, NN | → `nucleo_agrario.id_nucleo`. |
| `tipo_parcela` | `VARCHAR(30)` | — | `individual` o `copropiedad`. |
| `no_parcela_ppt` | `VARCHAR(50)` | — | Número de parcela en plano. |
| `certificado_parcelario` | `VARCHAR(100)` | — | Certificado del RAN. |
| `folio_derechos` | `VARCHAR(100)` | — | Folio de derechos. |
| `constancia_vigencia_fecha` | `DATE` | — | Fecha de la constancia vigente. |
| `nombre_titular` | `VARCHAR(300)` | LEGACY | Lectura temporal; usar `parcela_titular`. |
| `documentacion_disponible` | `BOOLEAN` | NN, D `FALSE` | Indicador de soporte. |
| `documentacion_faltante` | `TEXT` | — | Justificación de faltantes. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

Existe `UNIQUE(id_nucleo, id_parcela)` como clave candidata para relaciones
compuestas.

### 5.5 `parcela_titular`

Relación temporal N:M entre parcelas y personas. Usa CV-B.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_parcela_titular` | `SERIAL` | PK, NN | Identificador. |
| `id_parcela` | `INTEGER` | FK compuesta, NN | Parcela relacionada. |
| `id_nucleo` | `INTEGER` | FK compuestas, NN | Debe coincidir en parcela y persona. |
| `id_persona` | `INTEGER` | FK compuesta, NN | Persona vinculada al mismo núcleo. |
| `tipo_derecho` | `VARCHAR(30)` | NN, D `titular` | `titular`, `cotitular`, `posesionario` u `otro`. |
| `porcentaje_participacion` | `NUMERIC(7,4)` | — | Mayor que cero y hasta 100. |
| `fecha_inicio` | `DATE` | — | Inicio de vigencia. |
| `fecha_fin` | `DATE` | — | Fin no anterior al inicio. |
| Bloque CV-B | — | — | Ciclo de vida y observaciones. |

Las FK compuestas garantizan que la parcela y la persona pertenezcan al mismo
núcleo. Una persona activa no puede repetirse en la misma parcela. La suma de
porcentajes activos no puede exceder 100.

### 5.6 `padron_historial`

Historial del padrón de ejidatarios o comuneros. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_padron` | `SERIAL` | PK, NN | Identificador. |
| `id_nucleo` | `INTEGER` | FK, NN | → `nucleo_agrario.id_nucleo`. |
| `fecha_padron` | `DATE` | NN | Fecha de corte. |
| `numero_ejidatarios_comuneros` | `INTEGER` | NN | Total no negativo. |
| `id_usuario_registro` | `INTEGER` | FK | → `usuario.id_usuario`. |
| `fecha_registro` | `TIMESTAMPTZ` | NN, D `NOW()` | Registro técnico. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

Existe `UNIQUE(id_nucleo, id_padron)` para validar el padrón usado por una
asamblea.

### 5.7 `orv`

Vigencia del Órgano de Representación y Vigilancia. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_orv` | `SERIAL` | PK, NN | Identificador. |
| `id_nucleo` | `INTEGER` | FK, NN | → `nucleo_agrario.id_nucleo`. |
| `numero_orv` | `VARCHAR(50)` | — | Referencia del órgano. |
| `inicio_vigencia` | `DATE` | NN | Inicio del encargo. |
| `fin_vigencia` | `DATE` | NN | Fin del encargo. |
| `acta_eleccion_inscrita_ran` | `BOOLEAN` | NN, D `FALSE` | Inscripción del acta. |
| `documentacion_disponible` | `BOOLEAN` | NN, D `FALSE` | Indicador documental. |
| `documentacion_faltante` | `TEXT` | — | Faltantes. |
| `comisariado_presidente` | `VARCHAR(300)` | LEGACY | Usar `orv_integrante`. |
| `comisariado_secretario` | `VARCHAR(300)` | LEGACY | Usar `orv_integrante`. |
| `comisariado_tesorero` | `VARCHAR(300)` | LEGACY | Usar `orv_integrante`. |
| `consejo_vigilancia_presidente` | `VARCHAR(300)` | LEGACY | Usar `orv_integrante`. |
| `consejo_vigilancia_secretario1` | `VARCHAR(300)` | LEGACY | Usar `orv_integrante`. |
| `consejo_vigilancia_secretario2` | `VARCHAR(300)` | LEGACY | Usar `orv_integrante`. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

Existe `UNIQUE(id_nucleo, id_orv)`. Los cambios de vigencia sincronizan las
alertas de ORV vencido.

### 5.8 `orv_integrante`

Integrantes normalizados y cargos del ORV. Usa CV-B.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_orv_integrante` | `SERIAL` | PK, NN | Identificador. |
| `id_orv` | `INTEGER` | FK compuesta, NN | ORV relacionado. |
| `id_nucleo` | `INTEGER` | FK compuestas, NN | Núcleo común al ORV y persona. |
| `id_persona` | `INTEGER` | FK compuesta, NN | Persona relacionada con el núcleo. |
| `cargo` | `VARCHAR(50)` | NN | Uno de los seis cargos admitidos. |
| Bloque CV-B | — | — | Ciclo de vida y observaciones. |

Cargos admitidos:

- `comisariado_presidente`
- `comisariado_secretario`
- `comisariado_tesorero`
- `consejo_vigilancia_presidente`
- `consejo_vigilancia_secretario1`
- `consejo_vigilancia_secretario2`

Un cargo activo no puede repetirse dentro del mismo ORV.

## 6. Expediente maestro, afectaciones y actuaciones

### 6.1 `actividad_campo`

Sensibilización o caminamiento del expediente maestro. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_actividad` | `SERIAL` | PK, NN | Identificador. |
| `id_tramo_nucleo` | `INTEGER` | FK, NN | → `tramo_nucleo.id_tramo_nucleo`. |
| `tipo_actividad` | `VARCHAR(50)` | NN | `sensibilizacion` o `caminamiento`. |
| `contexto_proceso` | `VARCHAR(50)` | NN, D `cop_original` | Contexto operativo. |
| `fecha_programada` | `DATE` | — | Programación. |
| `fecha_realizada` | `DATE` | — | Ejecución. |
| `resultado` | `TEXT` | — | Resultado de campo. |
| `id_usuario_registro` | `INTEGER` | FK | → `usuario.id_usuario`. |
| `fecha_registro` | `TIMESTAMPTZ` | NN, D `NOW()` | Alta técnica. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

Existe `UNIQUE(id_tramo_nucleo, id_actividad)` para la relación compuesta con
`minuta`.

### 6.2 `minuta`

Minuta de reunión del expediente maestro; puede corresponder a una actividad
de campo del mismo `tramo_nucleo`. Usa CV-B.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_minuta` | `SERIAL` | PK, NN | Identificador. |
| `id_tramo_nucleo` | `INTEGER` | FK, NN | → `tramo_nucleo.id_tramo_nucleo`. |
| `id_actividad` | `INTEGER` | FK compuesta | Actividad del mismo expediente maestro. |
| `fecha_reunion` | `DATE` | NN | Fecha de reunión. |
| `lugar` | `VARCHAR(300)` | — | Lugar. |
| `asunto` | `VARCHAR(300)` | NN | Asunto. |
| `resumen` | `TEXT` | — | Contenido. |
| `folio` | `VARCHAR(100)` | UQ parcial | Único entre minutas activas del expediente. |
| Bloque CV-B | — | — | Ciclo de vida y observaciones. |

### 6.3 `acuerdo`

Compromiso derivado de una minuta. Usa CV-B.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_acuerdo` | `SERIAL` | PK, NN | Identificador. |
| `id_minuta` | `INTEGER` | FK, NN | → `minuta.id_minuta`. |
| `descripcion` | `TEXT` | NN | Texto no vacío. |
| `fecha_limite` | `DATE` | — | Fecha comprometida. |
| `fecha_cumplimiento` | `DATE` | — | Obligatoria sólo si está cumplido. |
| `estatus` | `VARCHAR(20)` | NN, D `pendiente` | `pendiente`, `cumplido`, `cancelado` o `vencido`. |
| `prioridad` | `VARCHAR(10)` | NN, D `media` | `alta`, `media` o `baja`. |
| `id_persona_responsable` | `INTEGER` | FK | Responsable externo normalizado. |
| `id_usuario_responsable` | `INTEGER` | FK | Responsable interno. |
| `responsable_externo` | `VARCHAR(300)` | — | Responsable no registrado. |
| Bloque CV-B | — | — | Ciclo de vida y observaciones. |

Debe existir exactamente uno de los tres tipos de responsable. Un acuerdo
`cumplido` requiere `fecha_cumplimiento`; los demás estados exigen que sea
nula.

### 6.4 `afectacion`

Subexpediente confirmado, colectivo o individual. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_afectacion` | `SERIAL` | PK, NN | Identificador del subexpediente. |
| `id_nucleo` | `INTEGER` | FK, NN | Núcleo que debe coincidir con `tramo_nucleo` y parcela. |
| `id_tramo_nucleo` | `INTEGER` | FK compuesta, NN | Expediente maestro. |
| `id_parcela` | `INTEGER` | FK compuesta | Obligatoria para afectación individual. |
| `tipo_afectacion` | `VARCHAR(20)` | NN | `colectivo` o `individual`. |
| `tipo_tenencia` | `VARCHAR(80)` | NN | Clasificación de tenencia. |
| `subtipo_tenencia` | `VARCHAR(80)` | — | Detalle de tenencia. |
| `destino_superficie` | `VARCHAR(80)` | — | Uso o destino. |
| `no_parcela_solar` | `VARCHAR(100)` | — | Referencia parcelaria o solar. |
| `superficie_afectada_ha` | `NUMERIC(12,4)` | — | Superficie no negativa. |
| `geometria_afectacion` | `geometry(Geometry,4326)` | — | En la práctica sólo Polygon/MultiPolygon válidos. |
| `num_personas_afectadas` | `INTEGER` | — | Conteo no negativo. |
| `situacion_juridica` | `TEXT` | — | Diagnóstico jurídico. |
| `documentacion_disponible` | `BOOLEAN` | NN, D `FALSE` | Indicador documental. |
| `documentacion_faltante` | `TEXT` | — | Faltantes o justificación. |
| `origen_registro` | `VARCHAR(50)` | NN, D `captura_sistema` | `captura_sistema` o `migracion_excel`. |
| `tipo_salida_terminal` | `VARCHAR(50)` | — | Tipo de salida terminal. |
| `fecha_salida_terminal` | `TIMESTAMPTZ` | — | Fecha de salida. |
| `motivo_salida_terminal` | `TEXT` | — | Motivo. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

Reglas espaciales y de integridad:

- La geometría es obligatoria para `captura_sistema`; los registros
  `migracion_excel` pueden quedar pendientes de digitalización.
- Cuando existe, debe tener SRID 4326, ser válida y ser Polygon o
  MultiPolygon.
- La parcela individual debe pertenecer al mismo núcleo y tener
  `no_parcela_ppt`, al menos un titular activo y soporte o justificación
  registral.
- Una afectación colectiva se rechaza si
  `tramo_nucleo.proyecto_no_afecta_uso_comun = TRUE`.
- La reducción de superficie no puede quedar por debajo de lo ya liberado.
- `UNIQUE(id_tramo_nucleo, id_afectacion, tipo_afectacion)` soporta
  relaciones compuestas con convenio y FIFONAFE.

### 6.5 `asamblea`

Actuación colectiva del expediente maestro. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_asamblea` | `SERIAL` | PK, NN | Identificador. |
| `id_nucleo` | `INTEGER` | FK compuestas, NN | Debe coincidir con expediente y padrón. |
| `id_tramo_nucleo` | `INTEGER` | FK compuesta, NN | Expediente maestro. |
| `tipo_asamblea` | `VARCHAR(50)` | NN | Tipo de acto. |
| `contexto_proceso` | `VARCHAR(50)` | — | Ciclo al que corresponde. |
| `fecha_exp_1a` | `DATE` | — | Expedición de primera convocatoria. |
| `fecha_prog_1a` | `DATE` | — | Primera fecha programada. |
| `fecha_exp_2a` | `DATE` | — | Expedición de segunda convocatoria. |
| `fecha_prog_2a` | `DATE` | — | Segunda fecha programada. |
| `fecha_realizada` | `DATE` | — | Fecha real. |
| `resultado_anuencia` | `VARCHAR(30)` | NN, D `pendiente` | Resultado. |
| `estatus_asamblea` | `VARCHAR(30)` | — | Estado operativo. |
| `ingreso_ran_fecha` | `DATE` | — | Ingreso al RAN. |
| `numero_solicitud_ran` | `VARCHAR(100)` | — | Folio de solicitud. |
| `calificacion_registral_ran` | `TEXT` | — | Resultado registral. |
| `acta_inscripcion_fecha_ran` | `DATE` | — | Inscripción del acta. |
| `documentacion_disponible` | `BOOLEAN` | NN, D `FALSE` | Indicador documental. |
| `documentacion_faltante` | `TEXT` | — | Faltantes. |
| `id_padron` | `INTEGER` | FK compuesta | Padrón del mismo núcleo. |
| `id_usuario_registro` | `INTEGER` | FK | → `usuario.id_usuario`. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

Tipos: `informacion`, `anuencia`, `retiro_fondos`, `conciliacion` y
`no_verificativo`.

Resultados: `otorgada`, `negada`, `pendiente` o `no_aplica`.

Estados admitidos cuando se captura: `programado`, `pendiente` o `completo`.

### 6.6 `convenio`

Convenio vinculado obligatoriamente con una afectación confirmada. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_convenio` | `SERIAL` | PK, NN | Identificador. |
| `id_tramo_nucleo` | `INTEGER` | FK compuestas, NN | Expediente maestro. |
| `id_afectacion` | `INTEGER` | FK compuestas, NN | Subexpediente. |
| `id_convenio_padre` | `INTEGER` | FK recursiva | Convenio original del linaje. |
| `id_asamblea_autorizacion` | `INTEGER` | FK compuesta | Asamblea del mismo expediente. |
| `tipo_afectacion` | `VARCHAR(20)` | FK compuesta, NN | Debe coincidir con afectación. |
| `tipo_convenio` | `VARCHAR(50)` | NN | Variante jurídica. |
| `fecha_firma` | `DATE` | — | Firma. |
| `monto_100` | `NUMERIC(18,2)` | — | Valor pactado por la tierra. |
| `monto_90` | `NUMERIC(18,2)` | — | Anticipo contenido en `monto_100`; no se suma al límite. |
| `monto_bdt` | `NUMERIC(18,2)` | — | Bienes distintos a la tierra; complementario a `monto_100`. |
| `superficie_total_ha` | `NUMERIC(12,4)` | — | Superficie individual base. |
| `superficie_real_afectada_ha` | `NUMERIC(12,4)` | — | Superficie colectiva base. |
| `superficie_adicional_ha` | `NUMERIC(12,4)` | — | Expansión colectiva. |
| `superficie_ampliacion_ha` | `NUMERIC(12,4)` | — | Expansión individual. |
| `ingreso_ran_fecha` | `DATE` | — | Ingreso registral. |
| `numero_solicitud_ingreso` | `VARCHAR(100)` | — | Folio. |
| `calificacion_registral` | `TEXT` | — | Calificación del RAN. |
| `convenio_inscrito_fecha_ran` | `DATE` | — | Fecha de inscripción. |
| `documentacion_disponible` | `BOOLEAN` | NN, D `FALSE` | Indicador documental. |
| `documentacion_faltante` | `TEXT` | — | Faltantes. |
| `id_usuario_registro` | `INTEGER` | FK | → `usuario.id_usuario`. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

Tipos colectivos:

- `cop_original`
- `modificatorio`
- `superficie_adicional`
- `obras_complementarias`

Tipos individuales:

- `cop_original`
- `modificatorio`
- `ampliacion`
- `ampliacion_remanente`

Reglas principales:

- Montos y superficies no pueden ser negativos.
- Obras complementarias no admiten `monto_bdt`.
- Los convenios colectivos requieren asamblea, salvo la excepción definida
  para modificatorios; los individuales no admiten asamblea.
- Un modificatorio requiere convenio padre del mismo expediente y afectación.
- El modificatorio individual no captura superficies, BDT ni ciclo RAN.
- Las superficies son mutuamente excluyentes según tipo y vía.
- No se permiten convenios cuando el expediente maestro está marcado como
  expropiación directa.
- En actualizaciones no se puede quitar una fecha de firma o inscripción ya
  establecida. Si se informa la inscripción, también debe existir la fecha de
  ingreso al RAN. El motor no exige una firma previa ni aplica esta secuencia
  al `INSERT` inicial.
- El límite pagable es `monto_100 + monto_bdt`; `monto_90` es anticipo.
- No se puede reducir ese límite por debajo de pagos activos.

### 6.7 `tramite_fifonafe`

Seguimiento de oficios y trámite de indemnización o no conflictos. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_tramite_fifonafe` | `SERIAL` | PK, NN | Identificador. |
| `id_tramo_nucleo` | `INTEGER` | FK compuestas, NN | Expediente maestro. |
| `id_convenio` | `INTEGER` | FK compuesta | Convenio del mismo expediente y afectación. |
| `id_afectacion` | `INTEGER` | FK compuestas | Afectación relacionada. |
| `tipo_afectacion` | `VARCHAR(20)` | FK compuesta, NN | `colectivo` o `individual`. |
| `tipo_tramite` | `VARCHAR(50)` | NN | `indemnizacion` o `informe_no_conflictos`. |
| `estatus` | `VARCHAR(30)` | NN, D `pendiente` | `programado`, `pendiente`, `completo` o `cancelado`. |
| `hay_conflictos` | `BOOLEAN` | — | Resultado del informe. |
| `no_oficio_fifonafe_a_dgaopr` | `VARCHAR(50)` | — | Oficio 1. |
| `no_oficio_dgaopr_a_repr` | `VARCHAR(50)` | — | Oficio 2. |
| `no_oficio_rpta_repr_a_dgaopr` | `VARCHAR(50)` | — | Oficio 3. |
| `no_oficio_rpta_dgaopr_a_fifonafe` | `VARCHAR(50)` | — | Oficio 4. |
| `fecha_oficio_fifonafe_a_dgaopr` | `DATE` | — | Fecha de oficio 1. |
| `fecha_oficio_dgaopr_a_repr` | `DATE` | — | Fecha de oficio 2. |
| `fecha_oficio_rpta_repr_a_dgaopr` | `DATE` | — | Fecha de oficio 3. |
| `fecha_oficio_rpta_dgaopr_a_fifonafe` | `DATE` | — | Fecha de oficio 4. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

Un trámite `completo` requiere los cuatro números y las cuatro fechas de
oficio. Cuando `id_convenio` e `id_afectacion` están informados, las FK
compuestas impiden mezclar expedientes, afectaciones, tipos y convenios. Como
ambas columnas admiten `NULL` y las FK usan `MATCH SIMPLE`, la validación
compuesta no se ejecuta por completo cuando falta alguno de esos valores.

### 6.8 `pago_indemnizacion`

Pagos aplicados a un trámite de indemnización. Usa CV-B.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_pago` | `SERIAL` | PK, NN | Identificador. |
| `id_tramite_fifonafe` | `INTEGER` | FK, NN | → `tramite_fifonafe.id_tramite_fifonafe`. |
| `monto_pagado` | `NUMERIC(18,2)` | NN | Mayor que cero. |
| `fecha_pago` | `DATE` | NN | Fecha efectiva. |
| `tipo_pago` | `VARCHAR(20)` | NN | `anticipo`, `parcial` o `total`. |
| `medio_pago` | `VARCHAR(20)` | — | `transferencia`, `cheque`, `deposito` u `otro`. |
| `banco_emisor` | `VARCHAR(100)` | — | Banco. |
| `referencia_bancaria` | `VARCHAR(100)` | UQ parcial | Referencia única entre pagos activos. |
| `id_persona_beneficiaria` | `INTEGER` | FK | → `persona.id_persona`. |
| `beneficiario_externo` | `VARCHAR(300)` | — | Beneficiario no normalizado. |
| Bloque CV-B | — | — | Ciclo de vida y observaciones. |

Debe existir exactamente un beneficiario, regla impuesta por un `CHECK`. Sólo
se paga un trámite de `indemnizacion` activo ligado a convenio activo. Para
registrar un pago activo, `monto_100` es obligatorio y, en convenios
`cop_original`, `ampliacion` o `ampliacion_remanente`, `monto_bdt` debe estar
capturado aunque su valor sea cero. La suma de pagos activos no puede superar
`monto_100 + monto_bdt`, y sólo puede existir un pago total activo por
trámite.

### 6.9 `afectacion_ciclo`

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_ciclo_afectacion` | `SERIAL` | PK, NN | Identificador. |
| `id_tramo_nucleo` | `INTEGER` | NN | |
| `id_afectacion` | `INTEGER` | NN | |
| `tipo_afectacion` | `VARCHAR(20)` | NN | |
| `tipo_ciclo` | `VARCHAR(50)` | NN | |
| `consecutivo` | `INTEGER` | NN | |
| `superficie_base_ciclo_ha` | `NUMERIC` | — | |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |


## 7. Documentos y alertas

### 7.1 `documentacion_soporte`

Metadatos documentales con referencia polimórfica validada por trigger. Usa
CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_documento` | `SERIAL` | PK, NN | Identificador. |
| `entidad_relacionada_id` | `INTEGER` | NN | PK de la entidad relacionada. |
| `entidad_relacionada_tipo` | `VARCHAR(50)` | NN | Tipo polimórfico admitido. |
| `tipo_documento` | `VARCHAR(100)` | NN | Clasificación documental. |
| `categoria` | `VARCHAR(20)` | NN | `disponible` o `faltante`. |
| `es_critico` | `BOOLEAN` | NN, D `FALSE` | Documento indispensable. |
| `url_archivo` | `TEXT` | LEGACY | Usar `documento_version.ruta_almacenamiento`. |
| `fecha_carga` | `TIMESTAMPTZ` | NN, D `NOW()` | Fecha del metadato. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

Tipos admitidos actualmente:

- `nucleo_agrario`
- `afectacion`
- `convenio`
- `orv`

`tramo_nucleo` **no está admitido actualmente** por el `CHECK` ni por
`fn_validar_documentacion_soporte_referencia()`. El Corte 2 deberá resolver
cómo representar documentos compartidos del expediente maestro.

### 7.2 `documento_version`

Versiones tratadas como inmutables por el servicio. PostgreSQL bloquea su
eliminación física, pero permite actualizaciones auditadas de sus metadatos.
Usa CV-B.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_documento_version` | `SERIAL` | PK, NN | Identificador. |
| `id_documento` | `INTEGER` | FK, NN | → `documentacion_soporte.id_documento`. |
| `numero_version` | `INTEGER` | NN | Entero desde 1; único por documento. |
| `hash_sha256` | `CHAR(64)` | NN | SHA-256 hexadecimal en minúsculas. |
| `tamano_bytes` | `BIGINT` | NN | Tamaño no negativo. |
| `nombre_archivo_original` | `VARCHAR(255)` | NN | Nombre no vacío. |
| `ruta_almacenamiento` | `TEXT` | NN, UQ | Ruta no vacía y única. |
| `tipo_mime` | `VARCHAR(150)` | — | MIME declarado. |
| `id_usuario_carga` | `INTEGER` | FK, NN | → `usuario.id_usuario`. |
| `fecha_carga` | `TIMESTAMPTZ` | NN, D `NOW()` | Fecha de carga. |
| Bloque CV-B | — | — | Ciclo de vida y observaciones. |

### 7.3 `alertas`

Alertas operativas generadas manual o automáticamente. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_alerta` | `SERIAL` | PK, NN | Identificador. |
| `tipo` | `VARCHAR(50)` | NN | `vencimiento_orv`, `evento_proximo` o `documento_faltante`. |
| `prioridad` | `VARCHAR(10)` | NN | `alta`, `media` o `baja`. |
| `titulo` | `VARCHAR(255)` | NN | Título. |
| `descripcion` | `TEXT` | — | Detalle. |
| `entidad_relacionada_id` | `INTEGER` | NN | Referencia polimórfica. |
| `entidad_relacionada_tipo` | `VARCHAR(50)` | NN | Tipo de entidad. |
| `fecha_evento` | `DATE` | — | Fecha relevante. |
| `fecha_creacion` | `TIMESTAMPTZ` | NN, D `NOW()` | Alta. |
| `esta_activa` | `BOOLEAN` | NN, D `TRUE` | Vigencia funcional de la alerta. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

Sólo puede existir una alerta activa de vencimiento por ORV.

### 7.4 `alertas_vistas`

Registro de lectura de alertas por usuario. Usa CV-A.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_alerta_vista` | `SERIAL` | PK, NN | Identificador. |
| `id_alerta` | `INTEGER` | FK, NN | → `alertas.id_alerta`. |
| `id_usuario` | `INTEGER` | FK, NN | → `usuario.id_usuario`. |
| `fecha_vista` | `TIMESTAMPTZ` | NN, D `NOW()` | Primera lectura. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

Restricción: `UNIQUE(id_alerta, id_usuario)`.

## 8. Seguridad y auditoría

### 8.1 `usuario`

Identidad de acceso al sistema. Su ciclo de vida tiene las mismas columnas de
CV-A y además `fecha_alta`.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_usuario` | `SERIAL` | PK, NN | Identificador. |
| `nombre` | `VARCHAR(250)` | NN | Nombre. |
| `apellido_paterno` | `VARCHAR(250)` | NN | Primer apellido. |
| `apellido_materno` | `VARCHAR(250)` | — | Segundo apellido. |
| `correo` | `VARCHAR(320)` | NN, UQ | Credencial de acceso. |
| `contrasena_hash` | `VARCHAR(255)` | NN | Hash de contraseña. |
| `rol` | `VARCHAR(30)` | NN | `admin`, `operador`, `visualizador` o `geografo`. |
| `fecha_alta` | `TIMESTAMPTZ` | NN, D `NOW()` | Alta del usuario. |
| Bloque CV-A | — | — | Ciclo de vida y observaciones. |

### 8.2 `bitacora`

Registro forense generado por `fn_audit_log()`. No usa baja lógica ni recibe
triggers de auditoría para evitar recursión.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_bitacora` | `BIGSERIAL` | PK, NN | Identificador. |
| `id_usuario` | `INTEGER` | FK, NN | Actor tomado de `app.current_user_id`. |
| `id_nucleo` | `INTEGER` | FK | Núcleo extraído de la fila auditada. |
| `id_tramo_nucleo` | `INTEGER` | FK | Expediente maestro extraído de la fila. |
| `entidad_tipo` | `VARCHAR(100)` | NN | Tabla modificada. |
| `entidad_id` | `BIGINT` | — | PK de la fila. |
| `accion` | `VARCHAR(30)` | NN | `insert`, `update`, `delete`, `validacion`, `cambio_estado` o `carga_documento`. |
| `detalle_cambio` | `TEXT` | — | Detalle opcional. |
| `valor_anterior` | `JSONB` | — | Fotografía previa. |
| `valor_nuevo` | `JSONB` | — | Fotografía posterior. |
| `fecha_hora` | `TIMESTAMPTZ` | NN, D `NOW()` | Momento del evento. |
| `ip_origen` | `INET` | — | IP, cuando se establece. |
| `user_agent` | `TEXT` | — | Cliente, cuando se establece. |

Toda escritura auditada requiere que la transacción establezca
`SET LOCAL app.current_user_id`.

### 8.3 `estado_autenticacion_usuario`

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_usuario` | `INTEGER` | PK, NN | |
| `intentos_fallidos` | `SMALLINT` | NN, D `0` | |
| `bloqueado_hasta` | `TIMESTAMPTZ` | — | |
| `ultimo_acceso_en` | `TIMESTAMPTZ` | — | |
| `actualizado_en` | `TIMESTAMPTZ` | NN, D `NOW()` | |

### 8.4 `evento_acceso`

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_evento` | `BIGSERIAL` | PK, NN | Identificador. |
| `id_usuario` | `INTEGER` | — | |
| `id_usuario_actor` | `INTEGER` | — | |
| `id_sesion` | `BIGINT` | — | |
| `tipo_evento` | `VARCHAR(40)` | NN | |
| `motivo_codigo` | `VARCHAR(50)` | NN | |
| `detalle` | `VARCHAR(200)` | — | |
| `fecha_hora` | `TIMESTAMPTZ` | NN, D `NOW()` | |
| `ip_origen` | `INET` | — | |
| `user_agent` | `VARCHAR(512)` | — | |
| `txid_registro` | `BIGINT` | NN | |

### 8.5 `sesion_usuario`

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_sesion` | `BIGSERIAL` | PK, NN | Identificador. |
| `id_usuario` | `INTEGER` | NN | |
| `token_hash` | `CHAR(64)` | NN | |
| `csrf_hash` | `CHAR(64)` | NN | |
| `fecha_creacion` | `TIMESTAMPTZ` | NN, D `NOW()` | |
| `ultima_actividad` | `TIMESTAMPTZ` | NN, D `NOW()` | |
| `expira_en` | `TIMESTAMPTZ` | NN | |
| `revocada_en` | `TIMESTAMPTZ` | — | |
| `id_usuario_revoca` | `INTEGER` | — | |
| `motivo_revocacion` | `VARCHAR(100)` | — | |
| `ip_creacion` | `INET` | — | |
| `user_agent_creacion` | `VARCHAR(512)` | — | |

## 9. Vistas

### 9.1 `vw_orv_estado`

Expone las 22 columnas de `orv` y agrega:

| Campo calculado | Tipo | Regla |
| --- | --- | --- |
| `orv_vigente` | `BOOLEAN` | Verdadero cuando el ORV está activo y su fecha de vigencia incluye la fecha actual. |

### 9.2 `vw_tramo_nucleo_estado`

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `id_tramo_nucleo` | `INTEGER` | Expediente maestro. |
| `id_tramo` | `INTEGER` | Tramo. |
| `id_nucleo` | `INTEGER` | Núcleo. |
| `consecutivo` | `INTEGER` | Consecutivo. |
| `longitud_m` | `NUMERIC(14,2)` | Longitud. |
| `causa_problema` | `TEXT` | Incidencia. |
| `tiene_anuencia` | `BOOLEAN` | Existe asamblea activa con anuencia otorgada. |
| `tiene_convenio_inscrito_ran` | `BOOLEAN` | Existe convenio activo inscrito. |
| `estado_legal` | `TEXT` | `problema`, `liberado`, `en_proceso` o `pendiente`. |
| `estado_geoespacial` | `TEXT` | `pendiente_digitalizacion` o `completo`. |

### 9.3 `vw_dashboard_liberacion`

Agrega métricas por expediente maestro:

| Campo | Tipo |
| --- | --- |
| `id_tramo_nucleo` | `INTEGER` |
| `id_proyecto` | `INTEGER` |
| `clave_proyecto` | `VARCHAR(30)` |
| `nombre_proyecto` | `VARCHAR(200)` |
| `id_tramo` | `INTEGER` |
| `clave_tramo` | `VARCHAR(20)` |
| `id_nucleo` | `INTEGER` |
| `nombre_nucleo` | `VARCHAR(300)` |
| `entidad_federativa` | `VARCHAR(100)` |
| `estado_legal` | `TEXT` |
| `estado_geoespacial` | `TEXT` |
| `total_superficie_afectada_ha` | `NUMERIC` |
| `superficie_liberada_ha` | `NUMERIC` |
| `superficie_pendiente_ha` | `NUMERIC` |
| `porcentaje_avance_legal` | `NUMERIC` |
| `porcentaje_avance_geoespacial` | `NUMERIC` |
| `total_convenios_formalizados_ran` | `BIGINT` |
| `total_convenios_colectivos_formalizados_ran` | `BIGINT` |
| `total_convenios_individuales_formalizados_ran` | `BIGINT` |
| `total_colectivo_ha` | `NUMERIC` |
| `total_individual_ha` | `NUMERIC` |

Los modificatorios inscritos más recientes sustituyen el valor de superficie
del convenio padre para el cálculo; no se suman como una liberación nueva.

### 9.4 `vw_afectacion_estado`

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `id_afectacion` | `INTEGER` | |
| `id_tramo_nucleo` | `INTEGER` | |
| `id_nucleo` | `INTEGER` | |
| `tipo_afectacion` | `VARCHAR` | |
| `estado_terminal` | `TEXT` | |
| `total_ciclos` | `BIGINT` | |
| `ciclos_concluidos` | `BIGINT` | |
| `superficie_total_ciclos_ha` | `NUMERIC` | |
| `superficie_liberada_ha` | `NUMERIC` | |
| `estado_liberacion` | `TEXT` | |
| `estado_registral` | `TEXT` | |
| `estado_financiero` | `TEXT` | |

### 9.5 `vw_afectacion_ciclo_estado`

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `id_ciclo_afectacion` | `INTEGER` | |
| `id_tramo_nucleo` | `INTEGER` | |
| `id_afectacion` | `INTEGER` | |
| `tipo_afectacion` | `VARCHAR` | |
| `tipo_ciclo` | `VARCHAR` | |
| `consecutivo` | `INTEGER` | |
| `superficie_base_ciclo_ha` | `NUMERIC` | |
| `activo` | `BOOLEAN` | |
| `fecha_baja` | `TIMESTAMPTZ` | |
| `id_usuario_baja` | `INTEGER` | |
| `motivo_baja` | `TEXT` | |
| `fecha_reactivacion` | `TIMESTAMPTZ` | |
| `id_usuario_reactivacion` | `INTEGER` | |
| `motivo_reactivacion` | `TEXT` | |
| `observaciones` | `TEXT` | |
| `id_convenio` | `INTEGER` | |
| `fecha_firma` | `DATE` | |
| `ingreso_ran_fecha` | `DATE` | |
| `convenio_inscrito_fecha_ran` | `DATE` | |
| `superficie_convenio_ha` | `NUMERIC` | |
| `estado_terminal` | `TEXT` | |
| `no_conflictos_completo` | `BOOLEAN` | |
| `indemnizacion_completa` | `BOOLEAN` | |
| `retiro_fondos_completo` | `BOOLEAN` | |
| `limite_pagable` | `NUMERIC` | |
| `total_pagado` | `NUMERIC` | |
| `estado_operativo` | `TEXT` | |
| `estado_registral` | `TEXT` | |
| `estado_financiero` | `TEXT` | |
| `superficie_ciclo_ha` | `NUMERIC` | |
| `saldo_disponible` | `NUMERIC` | |

## 10. Funciones propias

| Función | Retorno | Responsabilidad |
| --- | --- | --- |
| `fn_audit_log()` | `TRIGGER` | Registra INSERT/UPDATE en `bitacora`; exige contexto de usuario. |
| `fn_prevent_physical_delete()` | `TRIGGER` | Bloquea `DELETE` físico. |
| `fn_validar_baja_logica()` | `TRIGGER` | Exige metadatos de baja o reactivación. |
| `fn_calcular_superficie_liberada_afectacion(integer)` | `NUMERIC` | Calcula superficie liberada por afectación considerando linajes y modificatorios vigentes. |
| `fn_validar_afectacion_uso_comun()` | `TRIGGER` | Impide afectación colectiva en cruces sin uso común. |
| `fn_validar_coherencia_espacial()` | `TRIGGER` | Verifica intersección con núcleo y búfer del tramo. |
| `fn_validar_parcela_individual()` | `TRIGGER` | Exige parcela, datos registrales o justificación y titular activo. |
| `fn_validar_superficie_afectada_reducida()` | `TRIGGER` | Impide reducir debajo de la superficie liberada. |
| `fn_validar_convenio_expropiacion()` | `TRIGGER` | Impide convenios en expropiación directa. |
| `fn_validar_modificatorio_colectivo()` | `TRIGGER` | Verifica padre colectivo y asamblea con anuencia. |
| `fn_validar_superficie_liberada_convenio()` | `TRIGGER` | Impide liberar más superficie que la afectada. |
| `fn_sincronizar_superficie_adicional()` | `TRIGGER` | Ajusta la superficie afectada al registrar expansiones. |
| `fn_validar_regresion_estado_convenio()` | `TRIGGER` | En actualizaciones impide quitar firma o inscripción y exige ingreso al RAN cuando existe inscripción; no exige firma previa ni valida el orden en el INSERT inicial. |
| `fn_validar_documentacion_soporte_referencia()` | `TRIGGER` | Valida la referencia polimórfica y que esté activa. |
| `fn_validar_participacion_parcela()` | `TRIGGER` | Impide que participaciones activas excedan 100 %. |
| `fn_validar_pago_indemnizacion()` | `TRIGGER` | Valida trámite, convenio, montos requeridos y límite pagable; el beneficiario se controla mediante CHECK y FK. |
| `fn_proteger_limite_convenio_pagado()` | `TRIGGER` | Protege convenios con pagos y su límite económico. |
| `fn_sincronizar_alerta_orv_vencido()` | `TRIGGER` | Abre o cierra la alerta correspondiente al cambiar un ORV. |
| `fn_generar_alertas_orv_vencidos(integer)` | `INTEGER` | Genera en lote alertas faltantes para ORV vencidos. |

## 11. Triggers

### 11.1 Patrón común

Todas las tablas de aplicación salvo `bitacora` tienen:

- `trg_audit_<tabla>` para INSERT y UPDATE.
- `trg_prevent_delete_<tabla>` para bloquear DELETE.

Las tablas con CV-A o CV-B tienen además `trg_baja_logica_<tabla>`.
`entidad_federativa` y `municipio` no tienen ese último trigger porque no
poseen el bloque completo de metadatos.

### 11.2 Triggers especializados

| Tabla | Trigger |
| --- | --- |
| `afectacion` | `trg_validar_afectacion_uso_comun` |
| `afectacion` | `trg_validar_coherencia_espacial` |
| `afectacion` | `trg_validar_parcela_individual` |
| `afectacion` | `trg_validar_superficie_afectada_reducida` |
| `convenio` | `trg_validar_convenio_expropiacion` |
| `convenio` | `trg_validar_modificatorio_colectivo` |
| `convenio` | `trg_validar_superficie_liberada_convenio` |
| `convenio` | `trg_sincronizar_superficie_adicional` |
| `convenio` | `trg_validar_regresion_estado_convenio` |
| `convenio` | `trg_proteger_limite_convenio_pagado` |
| `documentacion_soporte` | `trg_validar_documentacion_soporte_referencia` |
| `orv` | `trg_sincronizar_alerta_orv_vencido` |
| `pago_indemnizacion` | `trg_validar_pago_indemnizacion` |
| `parcela_titular` | `trg_validar_participacion_parcela` |

## 12. Índices adicionales

Los PK, FK candidatas y `UNIQUE` declarativos generan sus propios índices.
Además existen:

| Índice | Tabla | Tipo o propósito |
| --- | --- | --- |
| `idx_tramo_geometria` | `tramo` | GiST espacial |
| `idx_nucleo_geometria` | `nucleo_agrario` | GiST espacial |
| `idx_tramo_nucleo_geometria` | `tramo_nucleo` | GiST espacial |
| `idx_afectacion_geom` | `afectacion` | GiST espacial |
| `idx_tramo_id_proyecto` | `tramo` | Navegación por proyecto |
| `idx_usuario_tramo_id_tramo` | `usuario_tramo` | Asignaciones por tramo |
| `idx_persona_nombre_busqueda` | `persona` | Búsqueda por nombre normalizado |
| `uq_persona_curp_normalizada` | `persona` | CURP única, sin distinguir mayúsculas |
| `idx_parcela_titular_persona` | `parcela_titular` | Búsqueda por persona |
| `uq_parcela_titular_persona_activo` | `parcela_titular` | Titular activo único por parcela/persona |
| `idx_orv_integrante_persona` | `orv_integrante` | Búsqueda por persona |
| `uq_orv_integrante_cargo_activo` | `orv_integrante` | Cargo activo único por ORV |
| `idx_minuta_tramo_nucleo` | `minuta` | Minutas del expediente maestro |
| `uq_minuta_folio_activo` | `minuta` | Folio activo único por expediente |
| `idx_acuerdo_minuta` | `acuerdo` | Acuerdos por minuta |
| `idx_acuerdo_pendiente` | `acuerdo` | Vencimientos pendientes activos |
| `idx_documento_version_documento` | `documento_version` | Versiones por documento |
| `idx_pago_tramite` | `pago_indemnizacion` | Pagos por trámite y fecha |
| `uq_pago_total_activo` | `pago_indemnizacion` | Un pago total activo por trámite |
| `uq_pago_referencia_activa` | `pago_indemnizacion` | Referencia bancaria activa única |
| `uq_alerta_orv_vencida_activa` | `alertas` | Una alerta de vencimiento activa por ORV |

El catálogo reporta 21 índices adicionales no respaldados por una restricción
declarativa; la lista anterior también muestra los índices únicos parciales
relevantes para negocio.

## 13. Objetos técnicos

### 13.1 `schema_migrations`

Controla migraciones incrementales aplicadas después del esquema base.

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `version` | `VARCHAR(20)` | PK, NN | Identificador de migración. |
| `descripcion` | `TEXT` | NN | Resumen de la migración. |
| `aplicada_en` | `TIMESTAMPTZ` | NN, D `NOW()` | Momento de aplicación. |

La instancia verificada contiene la versión `028`. El esquema base
consolidado se crea mediante `001_init_schema.sql` y no agrega una fila propia
en esta tabla.

### 13.2 Objetos PostGIS

PostGIS administra:

- `spatial_ref_sys`: catálogo de sistemas de referencia.
- `geometry_columns`: vista de columnas geométricas.
- `geography_columns`: vista de columnas geográficas.

Estos objetos no deben modificarse desde las migraciones funcionales del
proyecto.

## 14. Deuda de transición visible en el esquema

La base ejecutada conserva deliberadamente estas columnas heredadas:

- Seis nombres de cargo en `orv`; la fuente normalizada es
  `orv_integrante`.
- `parcela.nombre_titular`; la fuente normalizada es `parcela_titular`.
- `documentacion_soporte.url_archivo`; la fuente versionada es
  `documento_version.ruta_almacenamiento`.
- `persona_fuente_legacy`, necesaria mientras se conserve linaje de
  conciliación.

No deben eliminarse hasta ejecutar la fase de contracción de Adaptaciones 2.0
y comprobar que backend, frontend y datos dejaron de depender de ellas.

También permanece pendiente resolver documentalmente el nivel
`tramo_nucleo`: el expediente maestro existe en el dominio, pero
`documentacion_soporte.entidad_relacionada_tipo` todavía no lo admite.

## 15. Importación Geoespacial

### 15.1 `carga_geoespacial`

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_carga` | `BIGSERIAL` | PK, NN | Identificador. |
| `tipo_objetivo` | `VARCHAR(40)` | NN | |
| `tipo_geometria_esperado` | `VARCHAR(20)` | NN | |
| `nombre_original` | `VARCHAR(255)` | NN | |
| `nombre_almacenado` | `VARCHAR(100)` | NN | |
| `formato_detectado` | `VARCHAR(20)` | NN | |
| `tamano_bytes` | `BIGINT` | NN | |
| `sha256` | `VARCHAR(64)` | NN | |
| `fuente` | `VARCHAR(200)` | — | |
| `crs_original` | `TEXT` | NN | |
| `crs_destino` | `VARCHAR(20)` | NN, D `EPSG:4326` | |
| `total_features` | `INTEGER` | NN, D `0` | |
| `features_validos` | `INTEGER` | NN, D `0` | |
| `features_advertencia` | `INTEGER` | NN, D `0` | |
| `features_error` | `INTEGER` | NN, D `0` | |
| `estado` | `VARCHAR(30)` | NN, D `subido` | |
| `id_usuario_carga` | `INTEGER` | NN | |
| `fecha_carga` | `TIMESTAMPTZ` | NN, D `NOW()` | |
| `fecha_procesamiento` | `TIMESTAMPTZ` | — | |
| `fecha_confirmacion` | `TIMESTAMPTZ` | — | |
| `id_usuario_confirmacion` | `INTEGER` | — | |
| `error_codigo` | `VARCHAR(80)` | — | |
| `error_detalle` | `TEXT` | — | |

### 15.2 `carga_geoespacial_feature`

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_carga_feature` | `BIGSERIAL` | PK, NN | Identificador. |
| `id_carga` | `BIGINT` | NN | |
| `indice_feature` | `INTEGER` | NN | |
| `capa_origen` | `VARCHAR(200)` | — | |
| `atributos_originales` | `JSONB` | NN, D `{}` | |
| `geometria_normalizada` | `geometry(Geometry,4326)` | — | |
| `tipo_geometria` | `VARCHAR(40)` | — | |
| `estado` | `VARCHAR(20)` | NN | |
| `errores` | `JSONB` | NN, D `[]` | |
| `advertencias` | `JSONB` | NN, D `[]` | |
| `transformaciones` | `JSONB` | NN, D `[]` | |
| `area_original_m2` | `NUMERIC` | — | |
| `area_normalizada_m2` | `NUMERIC` | — | |
| `diferencia_area_relativa` | `NUMERIC` | — | |
| `seleccionado` | `BOOLEAN` | NN, D `FALSE` | |
| `id_registro_operativo` | `BIGINT` | — | |
| `fecha_consumo` | `TIMESTAMPTZ` | — | |
| `id_usuario_consumo` | `INTEGER` | — | |

### 15.3 `importacion_archivo`

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_importacion` | `BIGSERIAL` | PK, NN | Identificador. |
| `tipo_objetivo` | `VARCHAR(40)` | NN, D `nucleo_agrario` | |
| `nombre_original` | `VARCHAR(255)` | NN | |
| `nombre_almacenado` | `VARCHAR(100)` | NN | |
| `formato_detectado` | `VARCHAR(20)` | NN | |
| `tamano_bytes` | `BIGINT` | NN | |
| `sha256` | `CHAR(64)` | NN | |
| `fuente` | `VARCHAR(200)` | NN | |
| `crs_original` | `TEXT` | — | |
| `crs_destino` | `VARCHAR(20)` | NN, D `EPSG:4326` | |
| `columnas_detectadas` | `JSONB` | NN, D `[]` | |
| `mapeo` | `JSONB` | NN, D `{}` | |
| `opciones_mapeo` | `JSONB` | NN, D `{}` | |
| `id_perfil` | `BIGINT` | — | |
| `estado` | `VARCHAR(30)` | NN, D `subido` | |
| `total_features` | `INTEGER` | NN, D `0` | |
| `features_procesados` | `INTEGER` | NN, D `0` | |
| `validos` | `INTEGER` | NN, D `0` | |
| `advertencias` | `INTEGER` | NN, D `0` | |
| `errores` | `INTEGER` | NN, D `0` | |
| `importados` | `INTEGER` | NN, D `0` | |
| `descartados` | `INTEGER` | NN, D `0` | |
| `tolerancia_area_relativa` | `NUMERIC` | — | |
| `id_usuario_carga` | `INTEGER` | NN | |
| `fecha_carga` | `TIMESTAMPTZ` | NN, D `NOW()` | |
| `fecha_procesamiento_inicio` | `TIMESTAMPTZ` | — | |
| `fecha_procesamiento_fin` | `TIMESTAMPTZ` | — | |
| `fecha_confirmacion` | `TIMESTAMPTZ` | — | |
| `id_usuario_confirmacion` | `INTEGER` | — | |
| `fecha_completado` | `TIMESTAMPTZ` | — | |
| `archivo_eliminado_en` | `TIMESTAMPTZ` | — | |
| `error_codigo` | `VARCHAR(80)` | — | |
| `error_detalle` | `TEXT` | — | |
| `version_control` | `INTEGER` | NN, D `1` | |
| `procedencia_archivo` | `VARCHAR(20)` | — | |
| `id_importacion_origen` | `BIGINT` | — | |
| Bloque CV-A | — | — | Ciclo de vida. |

### 15.4 `importacion_feature`

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_importacion_feature` | `BIGSERIAL` | PK, NN | Identificador. |
| `id_importacion` | `BIGINT` | NN | |
| `indice_feature` | `INTEGER` | NN | |
| `capa_origen` | `VARCHAR(200)` | — | |
| `id_externo` | `VARCHAR(500)` | — | |
| `id_entidad_fuente` | `VARCHAR(100)` | — | |
| `id_municipio_fuente` | `VARCHAR(100)` | — | |
| `id_nucleo_fuente` | `VARCHAR(200)` | — | |
| `atributos_originales` | `JSONB` | NN, D `{}` | |
| `atributos_normalizados` | `JSONB` | NN, D `{}` | |
| `geometria_normalizada` | `geometry(MultiPolygon,4326)` | — | |
| `id_entidad_resuelta` | `INTEGER` | — | |
| `id_municipio_resuelto` | `INTEGER` | — | |
| `estado` | `VARCHAR(30)` | NN, D `pendiente_revision` | |
| `errores` | `JSONB` | NN, D `[]` | |
| `advertencias` | `JSONB` | NN, D `[]` | |
| `transformaciones` | `JSONB` | NN, D `[]` | |
| `area_original_m2` | `NUMERIC` | — | |
| `area_normalizada_m2` | `NUMERIC` | — | |
| `diferencia_area_relativa` | `NUMERIC` | — | |
| `advertencias_aceptadas` | `BOOLEAN` | NN, D `FALSE` | |
| `id_usuario_revision` | `INTEGER` | — | |
| `fecha_revision` | `TIMESTAMPTZ` | — | |
| `id_nucleo_operativo` | `INTEGER` | — | |
| `fecha_procesamiento` | `TIMESTAMPTZ` | NN, D `NOW()` | |
| `fecha_importacion` | `TIMESTAMPTZ` | — | |

### 15.5 `perfil_mapeo_importacion`

| Campo | Tipo | Claves | Descripción |
| --- | --- | --- | --- |
| `id_perfil` | `BIGSERIAL` | PK, NN | Identificador. |
| `nombre` | `VARCHAR(150)` | NN | |
| `fuente` | `VARCHAR(200)` | NN | |
| `tipo_objetivo` | `VARCHAR(40)` | NN, D `nucleo_agrario` | |
| `mapeo` | `JSONB` | NN | |
| `opciones` | `JSONB` | NN, D `{}` | |
| `activo` | `BOOLEAN` | NN, D `TRUE` | |
| `id_usuario_creacion` | `INTEGER` | NN | |
| `fecha_creacion` | `TIMESTAMPTZ` | NN, D `NOW()` | |
| `fecha_actualizacion` | `TIMESTAMPTZ` | NN, D `NOW()` | |
