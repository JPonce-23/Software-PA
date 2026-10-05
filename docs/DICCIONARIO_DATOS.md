# Diccionario de Datos — SOFTWARE-PA

> **Autoridad:** Especificación canónica del modelo físico y lógico de datos de SOFTWARE-PA.  
> **Validación:** Verificado contra `backend/app/models.py`, migraciones vigentes `001–025` y read-models de base de datos en PostgreSQL 15 / PostGIS.

---

## 1. Convenciones Estructurales y Auditoría

Todas las tablas de dominio incorporan el conjunto estándar de columnas de auditoría y baja lógica (`AuditableMixin`):

| Campo | Tipo SQL | Nullable | Descripción |
|---|---|---|---|
| `activo` | `BOOLEAN` | No (default `true`) | Bandera de vigencia lógica. La eliminación física está inhabilitada. |
| `creado_en` | `TIMESTAMPTZ` | No (default `now()`) | Fecha y hora técnica de inserción del registro en el sistema. |
| `creado_por` | `INTEGER` | Sí (FK `usuario.id_usuario`) | Usuario que realizó el alta técnica. |
| `actualizado_en` | `TIMESTAMPTZ` | Sí | Fecha y hora de la última modificación. |
| `actualizado_por` | `INTEGER` | Sí (FK `usuario.id_usuario`) | Usuario que realizó la última mutación. |
| `fecha_baja` | `TIMESTAMPTZ` | Sí | Fecha de la baja lógica del registro. |
| `id_usuario_baja` | `INTEGER` | Sí (FK `usuario.id_usuario`) | Usuario que ordenó la baja. |
| `motivo_baja` | `TEXT` | Sí | Justificación administrativa obligatoria de la baja. |
| `observaciones` | `TEXT` | Sí | Notas operativas o aclaratorias. |

---

## 2. Entidades de Dominio Administrativo y Territorial

### 2.1 `entidad_federativa` y `municipio`
Catálogo territorial oficial derivado de los estándares del INEGI.

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `entidad_federativa` | `id_entidad` | `INTEGER` | No | PK | Identificador interno de la entidad. | Sistema | `/api/catalogos/entidades` |
| `entidad_federativa` | `clave_inegi` | `CHAR(2)` | No | UNIQUE | Clave de dos dígitos del INEGI. | ENTIDAD | Filtro territorial oficial |
| `entidad_federativa` | `nombre` | `VARCHAR(100)` | No | — | Nombre oficial del estado. | ENTIDAD | Selector y reportes |
| `municipio` | `id_municipio` | `INTEGER` | No | PK | Identificador interno del municipio. | Sistema | `/api/catalogos/municipios` |
| `municipio` | `id_entidad` | `INTEGER` | No | `entidad_federativa` | Entidad a la que pertenece el municipio. | MUNICIPIO | Agrupador territorial |
| `municipio` | `clave_inegi` | `CHAR(5)` | No | UNIQUE | Clave de 5 dígitos del INEGI. | MUNICIPIO | Conciliación geográfica |
| `municipio` | `nombre` | `VARCHAR(150)` | No | — | Nombre oficial del municipio. | MUNICIPIO | Despliegue en interfaz |

### 2.2 `catalogo_operativo` y `catalogo_operativo_alias`
Catálogos configurables para normalizar valores de los libros Excel y resolver variaciones léxicas de captura.

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `catalogo_operativo` | `id_catalogo_opcion` | `BIGINT` | No | PK | Identificador único de la opción de catálogo. | Sistema | `/api/catalogos/operativos/{tipo}` |
| `catalogo_operativo` | `tipo_catalogo` | `VARCHAR(50)` | No | — | Clasificador del catálogo (p. ej. `tipo_cop_operativo`). | Columnas tipo | Agrupador de catálogo |
| `catalogo_operativo` | `codigo` | `VARCHAR(80)` | No | — | Clave funcional estandarizada. | Celdas Excel | Contrato en API y reportes |
| `catalogo_operativo` | `nombre` | `VARCHAR(250)` | No | — | Etiqueta legible para la interfaz de usuario. | Texto legible | Despliegue en selectores |
| `catalogo_operativo_alias` | `id_catalogo_alias` | `BIGINT` | No | PK | Identificador del alias. | Sistema | Normalización |
| `catalogo_operativo_alias` | `alias_normalizado` | `VARCHAR(300)` | No | — | Texto canónico en mayúsculas sin acentos. | Variantes Excel | Ingesta y conciliación |

### 2.3 `proyecto`
Proyecto estratégico o ferroviario amparado por las tareas de liberación de vía.

| Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|
| `id_proyecto` | `INTEGER` | No | PK | Identificador primario del proyecto. | Sistema | `/api/proyectos` |
| `clave_proyecto` | `VARCHAR(50)` | No | UNIQUE | Código institucional del proyecto. | PROYECTO | Identificador de negocio |
| `nombre_proyecto` | `VARCHAR(200)` | No | — | Nombre descriptivo oficial. | PROYECTO | Encabezados y reportes |
| `descripcion` | `TEXT` | Sí | — | Alcance y notas descriptivas. | Notas | Interfaz |
| `fecha_inicio` | `DATE` | Sí | — | Fecha de arranque institucional del proyecto. | Calendario | Trazabilidad |
| `fecha_fin_estimada` | `DATE` | Sí | — | Fecha meta de culminación. | Cronograma | Trazabilidad |

### 2.3.1 `derecho_via_proyecto`

DDV cartográfico canónico ligado directamente a `proyecto`. Admite historial de versiones y como máximo una versión vigente por proyecto. `es_vigente` expresa vigencia cartográfica; `activo` expresa baja lógica. Una versión anterior conserva `activo = true` al ser sustituida. `trazo_proyecto` (`MULTILINESTRING`) permanece como estructura legacy para consumidores actuales.

| Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen | Uso |
|---|---|---|---|---|---|---|
| `id_derecho_via` | `INTEGER` | No | PK | Identificador de la versión. | Sistema | Auditoría |
| `id_proyecto` | `INTEGER` | No | `proyecto.id_proyecto` | Proyecto propietario del DDV. | Proyecto | Alcance |
| `version` | `INTEGER` | No | `UNIQUE(id_proyecto, version)`, `> 0` | Versión secuencial por proyecto. | Captura cartográfica | Historial |
| `es_vigente` | `BOOLEAN` | No | Índice único parcial por proyecto; default `false` | Marca la versión cartográfica vigente; requiere `activo = true`. | Promoción explícita | Consulta futura |
| `geometria_poligono` | `geometry(MULTIPOLYGON,4326)` | No | GiST; no vacía y válida | Polígono del Derecho de Vía. | Cartografía | Consulta espacial futura |
| `fuente` | `VARCHAR(250)` | No | No vacía | Procedencia de la geometría. | Cartografía | Trazabilidad |
| `fecha_fuente` | `DATE` | Sí | — | Fecha declarada de la fuente. | Cartografía | Trazabilidad |

Incluye las columnas estándar de auditoría y baja lógica descritas en §1. Esta fase no sustituye superficies administrativas ni cambia los endpoints de trazo y mapa.

### 2.3.2 Staging de importación DDV

`importacion_archivo.tipo_objetivo = 'derecho_via_proyecto'` identifica el flujo estricto de GeoPackage. En este objetivo, `formato_detectado = 'gpkg'`, `mapeo` y `opciones_mapeo` son objetos vacíos, `id_perfil` es nulo y `crs_destino = 'EPSG:4326'`. `importacion_archivo` conserva nombre del archivo, tamaño, SHA-256, fuente, fecha, CRS original, capa en el reporte, contadores, usuario y fechas. `importacion_feature` conserva índice, capa, atributos originales, geometría normalizada, estado, errores, advertencias, transformaciones y, tras confirmar, `registro_destino_id` hacia el DDV del mismo proyecto. Una reparación válida registra `GEOMETRIA_REPARADA` y requiere aceptación explícita; una geometría irrecuperable queda en error. El staging no modifica `derecho_via_proyecto` ni entidades administrativas.

### 2.4 `nucleo_agrario`
Catálogo maestro nacional de núcleos agrarios (ejidos y comunidades). Su identidad interna permanece en `id_nucleo`; para el catálogo RAN/PHINA, la `cve_unica` oficial se almacena físicamente en `id_nucleo_fuente` y se identifica junto con `fuente_datos = 'RAN_PHINA_CATALOGO_NUCLEOS'`. No existe una columna física `clave_ran`. `ProyectoNucleo` continúa siendo el vínculo operativo con cada proyecto, conforme al principio Excel-First.

La conciliación vigente (025) usa `POST /api/proyectos/{id_proyecto}/geoespacial/nucleos/importaciones`. `cve_unica` es opcional: si está presente se verifica contra la identidad oficial; si falta se proponen candidatos por nombre y territorio dentro de los `ProyectoNucleo` existentes. Ninguna coincidencia guarda automáticamente geometría. La confirmación escribe únicamente `proyecto_nucleo_geometria`, conserva el campo global legacy y registra una decisión auditada. Véase el contrato 025 al final de este diccionario.

| Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|
| `id_nucleo` | `INTEGER` | No | PK | Identificador interno estable del núcleo agrario. | Sistema | `/api/nucleos` |
| `id_municipio` | `INTEGER` | No | `municipio.id_municipio` | Municipio registral del núcleo. | MUNICIPIO | Agrupación geográfica |
| `nombre_nucleo` | `VARCHAR(300)` | No | — | Nombre oficial según PHINA/RAN. | NÚCLEO AGRARIO | Búsquedas y visualización |
| `id_tipo_tenencia` | `BIGINT` | No | `catalogo_operativo` | Modalidad (`ejido` o `comunidad`). | E/C | Bifurcación funcional |
| `comunidad_indigena`| `BOOLEAN` | Sí | Triestado | `NULL` indica no capturado; no se infiere del tipo de tenencia. | COMUNIDAD INDÍGENA | Condición operativa (no terminal) |
| `fuente_datos` | `VARCHAR(120)` | Sí | Identidad externa | Código estable de procedencia; para este catálogo usa `RAN_PHINA_CATALOGO_NUCLEOS`. | RAN/PHINA | Trazabilidad institucional |
| `id_entidad_fuente` | `VARCHAR(120)` | Sí | — | Valor `scncve_edo` conservado desde la fuente RAN. | RAN/PHINA | Conciliación territorial |
| `id_municipio_fuente` | `VARCHAR(120)` | Sí | — | Valor `scncve_mun` conservado desde la fuente RAN. | RAN/PHINA | Conciliación territorial |
| `id_nucleo_fuente` | `VARCHAR(120)` | Sí | Identidad externa | Para RAN contiene `cve_unica` como texto, sin interpretar su estructura. Es único junto con `fuente_datos` cuando ambos existen. | RAN/PHINA | Identidad oficial |
| `alcance_identidad_fuente` | `VARCHAR(20)` | Sí | — | Para el catálogo RAN se usa `nacional`. | RAN/PHINA | Alcance de identidad |
| `geometria_poligono`| `MULTIPOLYGON` | Sí | SRID 4326 | Perímetro global legacy; no recibe nuevas escrituras de importación GIS. | Cartografía | Visor cartográfico de apoyo |

### 2.5 `proyecto_nucleo`
Eje operativo fundamental. Vincula el proyecto estratégico con el núcleo agrario específico.

| Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|
| `id_proyecto_nucleo` | `INTEGER` | No | PK | Identificador del expediente proyecto-núcleo. | Sistema | `/api/proyecto-nucleo` |
| `id_proyecto` | `INTEGER` | No | `proyecto.id_proyecto` | Proyecto asignado. | Fila Excel | Alcance y permisos |
| `id_nucleo` | `INTEGER` | No | `nucleo_agrario.id_nucleo` | Núcleo agrario atendido. | Fila Excel | Agrupador operativo |
| `id_residencia` | `BIGINT` | Sí | `catalogo_operativo` | Residencia regional de la PA a cargo. | RESIDENCIA | Gestión y filtros |
| `total_cops_planeados`| `INTEGER` | Sí | — | Meta de convenios programados en el núcleo. | TOTAL COP | Indicador snapshot |
| `afecta_tuc` | `BOOLEAN` | Sí | Triestado | ¿El trazo afecta tierras de uso común? (`false` indica no afectación a TUC; no prohíbe otros destinos colectivos ni bloquea individuales). | NO AFECTA TUC | Condición de uso común / Snapshot |
| `id_motivo_no_afecta_tuc` | `BIGINT` | Sí | `catalogo_operativo` | Justificación cuando no afecta uso común. | Notas TUC | Trazabilidad |
| `motivo_no_afecta_tuc_detalle` | `TEXT` | Sí | — | Explicación complementaria de campo. | Notas TUC | Auditoría operativa |
| `tuc_revision_pendiente` | `BOOLEAN` | No | Default `false` | ¿La no afectación está sujeta a revisión? | Notas TUC | Semántica triestado |
| `tuc_revision_detalle` | `TEXT` | Sí | — | Detalle de la revisión pendiente. | Notas TUC | Auditoría operativa |

### 2.6 `proyecto_nucleo_referencia` y `proyecto_nucleo_responsable`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `proyecto_nucleo_referencia` | `tipo_referencia` | `VARCHAR(30)` | No | — | `consecutivo`, `clave_tramo`, `numero_tramo`. | Columnas tramo | Referencia documental |
| `proyecto_nucleo_referencia` | `valor` | `VARCHAR(150)` | No | — | Texto de la clave o consecutivo original. | CONSECUTIVO | Búsquedas y trazabilidad |
| `proyecto_nucleo_referencia` | `es_principal` | `BOOLEAN` | No | — | Marca de referencia primaria del libro. | Columna fuente | Ordenamiento en UI |
| `proyecto_nucleo_responsable` | `nombre` | `VARCHAR(300)` | No | — | Nombre del enlace o brigadista. | RESPONSABLE | Asignación operativa |
| `proyecto_nucleo_responsable` | `cargo` | `VARCHAR(200)` | Sí | — | Cargo institucional. | RESPONSABLE | Directorio interno |
| `proyecto_nucleo_responsable` | `contacto` | `VARCHAR(200)` | Sí | — | Teléfono o correo de localización. | CONTACTO | Contacto inmediato |
| `proyecto_nucleo_responsable` | `es_principal` | `BOOLEAN` | No | — | Responsable vigente a cargo del núcleo. | Celda principal | Indicador en ficha técnica |

---

## 3. Órganos Ejidales, Padrón y Actividades de Campo

### 3.1 `orv`, `orv_integrante` y `padron_historial`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `orv` | `numero_orv` | `VARCHAR(50)` | No | — | Número de acta o registro del ORV. | ORV | `/api/orvs` |
| `orv` | `inicio_vigencia` / `fin_vigencia` | `DATE` | Sí | — | Periodo de ejercicio legal del Comisariado. | VIGENCIA ORV | Validación jurídica |
| `orv` | `id_estado_registral` | `BIGINT` | Sí | `catalogo_operativo` | Estado registral de la mesa directiva. | ESTATUS ORV | Evidencia institucional |
| `orv_integrante` | `id_persona` | `BIGINT` | No | `persona.id_persona` | Persona que ostenta el cargo ejidal. | INTEGRANTES | Acreditación en convenios |
| `orv_integrante` | `cargo` | `VARCHAR(100)` | No | — | Presidente, Secretario, Tesorero, Consejo. | CARGO | Cláusulas de convenio |
| `padron_historial` | `fecha_padron` | `DATE` | No | — | Fecha de expedición del padrón ejidal. | FECHA PADRÓN | Quórum de asamblea |
| `padron_historial` | `numero_ejidatarios_comuneros` | `INTEGER` | No | — | Total de sujetos de derecho reconocidos. | NO. SUJETOS | Verificación de mayorías |

### 3.2 `actividad_campo`
Sensibilización comunitaria y caminamientos técnicos.

| Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|
| `id_actividad` | `BIGINT` | No | PK | Identificador primario de la actividad. | Sistema | `/api/actividades-campo` |
| `id_proyecto_nucleo` | `INTEGER` | No | `proyecto_nucleo` | Proyecto-núcleo donde se efectuó. | Fila Excel | Agrupador operativo |
| `tipo_actividad` | `VARCHAR(50)` | No | — | Solo `sensibilizacion` o `caminamiento`. | Bloques W:AH | Hito de avance |
| `id_tipo_cop_operativo` | `BIGINT` | Sí | `catalogo_operativo` | Dimensión COP asociada (`ORIGEN`, etc.). | TIPO COP | Reporting dimensional |
| `contexto_actividad` | `VARCHAR(50)` | Sí | — | Contexto específico (`general`, etc.). | Notas | Trazabilidad |
| `fecha_programada` | `DATE` | Sí | — | Fecha agendada para el evento. | PROGRAMADA | Indicador de programación |
| `fecha_realizada` | `DATE` | Sí | — | Fecha efectiva de ejecución en campo. | REALIZADA | Indicador de avance real |
| `responsable` | `VARCHAR(250)` | Sí | — | Brigadista que condujo la actividad. | RESPONSABLE | Auditoría operativa |
| `resultado` | `TEXT` | Sí | — | Minuta o acuerdos alcanzados. | RESULTADO | Despliegue en expediente |

---

## 4. Derechos Individuales: Parcelas y Titulares

### 4.1 `parcela` y `parcela_titular`
La unidad operativa central de la ruta individual.

`Parcela.no_parcela` es el único identificador funcional canónico; no existe un segundo campo de dominio `no_parcela_ppt`. Sus orígenes Excel son `NO. DE PARCELA` / `NO. DE PARCELA PPT`. Los valores fuente individuales se preservan mediante `TrazabilidadFuente` / `ImportacionCelda` (modelo implementado: `ImportacionTabularCelda`), **no en dos columnas de `Parcela`**. Deben conservarse por columna, cuando corresponda, `archivo`, `hoja`, `fila`, `columna`, `valor_original`, `valor_normalizado`, `tratamiento` y `mensajes`; en las celdas de importación, archivo y hoja se obtienen de `ImportacionTabular`.

La resolución del identificador sigue [MODELO_FUNCIONAL.md §6.1](MODELO_FUNCIONAL.md#61-identificador-funcional-canónico-único) y [FUENTES_Y_COBERTURA_EXCEL.md §3.1](FUENTES_Y_COBERTURA_EXCEL.md#31-unicidad-del-identificador-parcelario-no_parcela): equivalencia o diferencia de formato produce un único valor conservando ambos originales; un solo valor presente se utiliza con su procedencia exacta; divergencia sustantiva requiere **REVISAR** y aclaración humana sin crear automáticamente dos parcelas ni asumir prioridad PPT. Sin ambos valores, `no_parcela` puede quedar `NULL` y la ausencia se conserva en trazabilidad/revisión al importar, incluidas las 17 filas auditadas.

La conciliación vigente (025) usa `POST /api/proyectos/{id_proyecto}/geoespacial/parcelas/importaciones`. `cve_unica_nucleo` es opcional y no se inventa. Sólo son destinos las parcelas previamente vinculadas al proyecto por la cadena administrativa de afectación. `PARCELA` y `Num_parcela` se conservan y comparan separadamente; letras, sufijos y otros signos permanecen distintos. La confirmación escribe `proyecto_parcela_geometria`, sin actualizar la geometría global ni superficies administrativas. Véase el contrato 025 al final de este diccionario.

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `parcela` | `id_parcela` | `INTEGER` | No | PK | Identificador interno de la parcela. | Sistema | `/api/parcelas` |
| `parcela` | `id_nucleo` | `INTEGER` | No | `nucleo_agrario` | Núcleo agrario al que pertenece. | NÚCLEO | Pertenencia agraria |
| `parcela` | `no_parcela` | `VARCHAR(80)` | Sí | — | **Único identificador funcional canónico.** | NO. DE PARCELA / NO. DE PARCELA PPT | Identificación unívoca |
| `parcela` | `tipo_parcela` | `VARCHAR(50)` | Sí | — | Ejidal, comunal, infraestructura, etc. | TIPO PARCELA | Clasificación |
| `parcela` | `geometria_poligono`| `MULTIPOLYGON` | Sí | SRID 4326 | Polígono global legacy; no recibe nuevas escrituras de importación GIS. | Legacy | Visor cartográfico (opcional) |
| `parcela_titular` | `id_parcela` | `INTEGER` | No | `parcela.id_parcela` | Parcela correspondiente. | Fila titular | Vínculo de titularidad |
| `parcela_titular` | `id_persona` | `BIGINT` | No | `persona.id_persona` | Sujeto de derecho acreditado. | TITULAR | Suscripción de convenios |
| `parcela_titular` | `tipo_derecho` | `VARCHAR(50)` | No | — | Titular, posesionario, sucesor. | CALIDAD | Cláusulas contractuales |
| `parcela_titular` | `certificado_parcelario` | `VARCHAR(80)` | Sí | — | Folio del certificado parcelario oficial. | CERTIFICADO | Acreditación jurídica |
| `parcela_titular` | `folio_derechos` | `VARCHAR(80)` | Sí | — | Folio registral de derechos agrarios. | FOLIO | Acreditación jurídica |
| `parcela_titular` | `constancia_vigencia` | `VARCHAR(80)` | Sí | — | Referencia de constancia emitida por RAN. | CONSTANCIA | Soporte de vigencia |

---

## 5. Afectaciones y Unidades Agrarias

### 5.1 `afectacion`, `unidad_agraria` y `afectacion_unidad_agraria`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `afectacion` | `id_afectacion` | `INTEGER` | No | PK | Identificador del subexpediente de afectación. | Sistema | `/api/afectaciones` |
| `afectacion` | `id_proyecto_nucleo` | `INTEGER` | No | `proyecto_nucleo` | Proyecto-núcleo propietario. | Fila Excel | Agrupador maestro |
| `afectacion` | `id_parcela` | `INTEGER` | Sí | `parcela.id_parcela` | Parcela afectada (sólo en ruta individual). | NO PARCELA | Null en colectivos |
| `afectacion` | `tipo_afectacion` | `VARCHAR(30)` | No | — | `colectiva` o `individual`. | Ámbito | Bifurcación funcional |
| `afectacion` | `id_tipo_cop_operativo` | `BIGINT` | Sí | `catalogo_operativo` | Clasificación COP (`ORIGEN`, etc.). | TIPO COP | Reporting dimensional |
| `afectacion` | `superficie_preliminar_ha` | `NUMERIC(14,7)` | Sí | — | Superficie estimada inicialmente en campo. | SUP. PRELIMINAR | Referencia técnica |
| `afectacion` | `superficie_afectada_ha` | `NUMERIC(14,7)` | Sí | — | **Superficie administrativa capturada.** | SUP. AFECTADA | Cómputo y reporting administrativo |
| `afectacion` | `avaluo_monto` | `NUMERIC(14,2)` | Sí | — | Monto determinado por INDAABIN. | AVALÚO MAESTRO | Referencia indemnizatoria |
| `unidad_agraria` | `id_destino_superficie` | `BIGINT` | No | `catalogo_operativo` | Destino de suelo (TUC, canal, camino, etc.). | DESTINO | Catálogo operativo |
| `afectacion_unidad_agraria` | `superficie_afectada_ha` | `NUMERIC(14,7)` | No | — | Superficie física exacta por destino de suelo. | SUP. DESTINO | Desglose multidestino |

---

## 6. Asambleas y Convocatorias (Ruta Colectiva)

### 6.1 `asamblea` y `asamblea_convocatoria`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `asamblea` | `id_asamblea` | `INTEGER` | No | PK | Identificador único de la asamblea ejidal. | Sistema | `/api/asambleas` |
| `asamblea` | `id_proyecto_nucleo` | `INTEGER` | No | `proyecto_nucleo` | Proyecto-núcleo propietario. | Fila colectivo | Ámbito colectivo |
| `asamblea` | `id_tipo_asamblea` | `BIGINT` | No | `catalogo_operativo` | Acto formal (anuencia, retiro fondos, etc.). | TIPO ASAMBLEA | Clasificación legal |
| `asamblea` | `id_tipo_cop_operativo` | `BIGINT` | Sí | `catalogo_operativo` | Dimensión COP (`ORIGEN`, `ADICIONAL`, etc.). | TIPO COP | Reporting dimensional |
| `asamblea` | `proposito` / `resultado` | `TEXT` | Sí | — | Objetivo y acta sintética de la asamblea. | Celdas notas | Expediente |
| `asamblea_convocatoria` | `id_convocatoria` | `BIGINT` | No | PK | Identificador de la convocatoria. | Sistema | `/api/asambleas/{id}/convocatorias` |
| `asamblea_convocatoria` | `ordinal` | `SMALLINT` | No | — | Número de convocatoria (1 = 1ª, 2 = 2ª, etc.). | 1A / 2A | Quórum legal Ley Agraria |
| `asamblea_convocatoria` | `fecha_expedicion` | `DATE` | Sí | — | Fecha en que se fijó la convocatoria. | EXPEDICIÓN | Validez temporal |
| `asamblea_convocatoria` | `fecha_programada` | `DATE` | Sí | — | Fecha agendada para la asamblea. | PROGRAMADA | Hito programado |
| `asamblea_convocatoria` | `fecha_realizacion` | `DATE` | Sí | — | Fecha en que efectivamente se desahogó. | REALIZADA | Hito de asamblea |
| `asamblea_convocatoria` | `id_resultado` | `BIGINT` | Sí | `catalogo_operativo` | `celebrada`, `no_verificativo`, `cancelada`. | RESULTADO | Solo celebrada acredita hito |

---

## 7. Convenios de Ocupación Previa (COP)

### 7.1 `convenio`, `convenio_afectacion` y `convenio_compareciente`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `convenio` | `id_convenio` | `INTEGER` | No | PK | Identificador del convenio celebrado. | Sistema | `/api/convenios` |
| `convenio` | `ambito` | `VARCHAR(30)` | No | — | `colectivo` o `individual`. | Ámbito | Bifurcación funcional |
| `convenio` | `tipo_convenio` | `VARCHAR(50)` | No | — | `cop_original`, `modificatorio`, `ampliacion`... | TIPO CONVENIO | Catálogo contractual |
| `convenio` | `modalidad_especial` | `VARCHAR(50)` | Sí | — | `permuta` u otras modalidades excepcionales. | MODALIDAD | Tratamiento de permuta |
| `convenio` | `id_asamblea_autorizacion` | `INTEGER` | Sí | `asamblea.id_asamblea` | Asamblea que autorizó la firma (colectivo). | ASAMBLEA | Null en individuales |
| `convenio` | `fecha_programada_firma` | `DATE` | Sí | — | Fecha meta de formalización. | PROG. FIRMA | Programación de convenio |
| `convenio` | `fecha_firma` | `DATE` | Sí | — | **Fecha real de firma del convenio.** | FIRMA REAL | Hito de formalización |
| `convenio` | `superficie_ha` | `NUMERIC(14,7)` | Sí | — | Superficie total amparada en el instrumento. | SUPERFICIE | Declarado en instrumento |
| `convenio` | `monto_100` | `NUMERIC(14,2)` | Sí | — | **Importe pactado total del convenio.** | MONTO 100% | **NO ADITIVO** en multidestino |
| `convenio_afectacion` | `id_convenio` / `id_afectacion` | `INTEGER` | No | PK compuesta | Relación N:M entre convenios y afectaciones. | Cruce operativo | Cobertura sin duplicar montos |
| `convenio_compareciente` | `id_persona` | `BIGINT` | No | `persona.id_persona` | Comparecientes (titulares o comisariados). | FIRMANTES | Acreditación de partes |

---

## 8. Tramitaciones Registrales ante el RAN

### 8.1 `tramite_ran` y `tramite_ran_evento`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `tramite_ran` | `id_tramite_ran` | `INTEGER` | No | PK | Identificador del expediente registral. | Sistema | `/api/tramites-ran` |
| `tramite_ran` | `id_asamblea` | `INTEGER` | Sí | `asamblea.id_asamblea` | Vinculado a acta de asamblea (exclusivo). | RAN ACTA | Inscripción de asamblea |
| `tramite_ran` | `id_convenio` | `INTEGER` | Sí | `convenio.id_convenio` | Vinculado a convenio COP (exclusivo). | RAN CONVENIO | Inscripción de convenio |
| `tramite_ran` | `id_orv` | `INTEGER` | Sí | `orv.id_orv` | Vinculado a acta de elección ORV. | RAN ORV | Inscripción de directiva |
| `tramite_ran` | `fecha_programada_ingreso` | `DATE` | Sí | — | Fecha agendada de presentación ante el RAN. | PROG. INGRESO | Planificación registral |
| `tramite_ran_evento` | `id_tipo_evento` | `BIGINT` | No | `catalogo_operativo` | `ingreso`, `prevencion`, `inscripcion`, etc. | Hitos RAN | Línea de tiempo registral |
| `tramite_ran_evento` | `fecha_evento` | `DATE` | No | — | Fecha formal del sello o actuación del RAN. | FECHA INGRESO / INSCRIPCIÓN | Fechas de hito oficiales |
| `tramite_ran_evento` | `numero_solicitud` | `VARCHAR(100)` | Sí | — | Número oficial de trámite / código de barras. | NO. SOLICITUD | Seguimiento en portal RAN |
| `tramite_ran_evento` | `calificacion` | `VARCHAR(50)` | Sí | — | Calificación intermedia (favorable / observaciones). | CALIFICACIÓN | No equivale a inscripción |

---

## 9. Procedimiento FIFONAFE

### 9.1 `tramite_fifonafe`, `tramite_fifonafe_evento` y `tramite_fifonafe_afectacion`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `tramite_fifonafe` | `id_tramite_fifonafe` | `INTEGER` | No | PK | Identificador de la solicitud fiduciaria. | Sistema | `/api/fifonafe` |
| `tramite_fifonafe` | `id_proyecto_nucleo` | `INTEGER` | No | `proyecto_nucleo` | Proyecto-núcleo propietario. | Fila Excel | Alcance institucional |
| `tramite_fifonafe` | `ambito` | `VARCHAR(30)` | No | — | `colectivo` o `individual`. | Ámbito | Regla de los 4 oficios |
| `tramite_fifonafe` | `hay_conflictos` | `BOOLEAN` | Sí | Triestado | Resultado del análisis de conflictos sociales. | NO CONFLICTOS | Semántica independiente |
| `tramite_fifonafe` | `acuse_fifonafe_fecha` | `DATE` | Sí | — | Fecha del sello de recepción de FIFONAFE. | ACUSE | Evidencia fiduciaria |
| `tramite_fifonafe_evento` | `id_tipo_evento` | `BIGINT` | No | `catalogo_operativo` | Identifica uno de los 4 oficios formales. | CC:CF | Cadena de correspondencia |
| `tramite_fifonafe_evento` | `numero_oficio` | `VARCHAR(100)` | Sí | — | Número oficial de correspondencia. | NO. OFICIO | Trazabilidad documental |
| `tramite_fifonafe_evento` | `fecha_oficio` | `DATE` | Sí | — | Fecha asentada en el oficio. | FECHA OFICIO | `MAX(fecha_oficio)` para cierre |
| `tramite_fifonafe_afectacion` | `id_tramite_fifonafe` / `id_afectacion` | `INTEGER` | No | PK compuesta | Afectaciones y parcelas cubiertas. | Cruce fiduciario | Cobertura N:M sin duplicar |

---

## 10. Cadena Financiera: Indemnización y Pagos

### 10.1 `indemnizacion` y `pago`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `indemnizacion` | `id_indemnizacion` | `INTEGER` | No | PK | Identificador del expediente indemnizatorio. | Sistema | `/api/indemnizaciones` |
| `indemnizacion` | `id_afectacion` | `INTEGER` | No | `afectacion.id_afectacion` | Afectación compensada (máximo 1 activa). | Fila Excel | Vínculo físico |
| `indemnizacion` | `estatus` | `VARCHAR(50)` | No | — | `pendiente`, `en_proceso`, `pagado`, etc. | ESTATUS PAGO | Estado administrativo |
| `indemnizacion` | `fecha_resolucion` | `DATE` | Sí | — | **Fecha legal en que se resolvió la indemnización.** | FECHA RESOLUCIÓN | **Hito de indemnización resuelta** |
| `indemnizacion` | `monto_total` | `NUMERIC(14,2)` | Sí | — | Importe global determinado a indemnizar. | MONTO INDEMNIZACIÓN | Balance económico |
| `indemnizacion` | `fecha_entrega_expediente_pa` | `DATE` | Sí | — | Fecha de entrega del expediente SICT a PA. | ENTREGA SICT/PA | Trazabilidad interinstitucional |
| `pago` | `id_pago` | `BIGINT` | No | PK | Identificador del desembolso real. | Sistema | `/api/pagos` |
| `pago` | `id_indemnizacion` | `INTEGER` | No | `indemnizacion` | Indemnización amparada. | Vínculo pago | Cadena canónica financiera |
| `pago` | `fecha_pago` | `DATE` | No | — | **Fecha real de entrega/dispersión del recurso.** | FECHA PAGO | **Hito de pago efectivo** |
| `pago` | `monto` | `NUMERIC(14,2)` | No | — | Cantidad líquida pagada en el evento. | MONTO PAGADO | Agregación económica |
| `pago` | `beneficiario_nombre` | `VARCHAR(300)` | No | — | Persona o núcleo que recibió el recurso. | BENEFICIARIO | Comprobación de entrega |

---

## 11. Subsistema Documental, Trazabilidad y Eventos

### 11.1 `documento`, `documento_version` y `documento_vinculo`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `documento` | `id_documento` | `BIGINT` | No | PK | Identidad lógica del documento. | Sistema | `/api/documentos` |
| `documento` | `tipo_documento` | `VARCHAR(50)` | No | — | Clasificación documental (acta, convenio, etc.). | Tipo soporte | Catálogo |
| `documento` | `fecha_documento` | `DATE` | Sí | — | Fecha propia del documento físico. | FECHA OFICIO | Metadato jurídico |
| `documento` | `numero_folio` | `VARCHAR(100)` | Sí | — | Número de oficio, acta o folio impreso. | FOLIO / NO. OFICIO | Identificación documental |
| `documento_version` | `id_version` | `BIGINT` | No | PK | Versión inmutable del archivo digital. | Sistema | Descarga de archivos |
| `documento_version` | `sha256` | `CHAR(64)` | No | — | Hash criptográfico para integridad. | Archivo | Detección de alteración |
| `documento_vinculo` | `entidad_tipo` / `entidad_id` | `VARCHAR` / `BIGINT` | No | Polimórfico | Entidad asociada (convenio, asamblea...). | Asociación | Vinculación y aislamiento |

### 11.2 `seguimiento_evento` y `trazabilidad_fuente`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `seguimiento_evento` | `id_seguimiento_evento` | `BIGINT` | No | PK | Identificador del evento histórico. | Sistema | `/api/seguimiento` |
| `seguimiento_evento` | `id_proyecto_nucleo` | `INTEGER` | No | `proyecto_nucleo` | Proyecto-núcleo sobre el que incide. | Fila Excel | Pertenencia |
| `seguimiento_evento` | `id_tipo_evento` | `BIGINT` | No | `catalogo_operativo` | `suspension`, `reapertura`, `cierre`, etc. | Hechos de campo | Transiciones |
| `seguimiento_evento` | `id_motivo` | `BIGINT` | Sí | `catalogo_operativo` | `expropiacion_directa`, `juicio`, etc. | Motivos Excel | Justificación |
| `seguimiento_evento` | `fecha_evento` | `DATE` | No | — | Fecha en que ocurrió el suceso. | FECHA EVENTO | Cronología determinista |
| `trazabilidad_fuente` | `archivo` | `VARCHAR(255)` | No | — | Nombre del libro Excel de origen; conserva la procedencia de cada columna parcelaria. | Archivo auditado | Trazabilidad de ingesta |
| `trazabilidad_fuente` | `hoja` / `fila` / `columna` | `VARCHAR` / `INTEGER` | Sí | — | Coordenadas exactas de cada valor fuente en el libro Excel. | Hoja / Columna | Auditoría de migración |
| `trazabilidad_fuente` | `tratamiento` | `VARCHAR(30)` | No | — | `PERSISTIR`, `DERIVAR`, `REVISAR`, etc. | Matriz cobertura | Verificación de integridad |
| `trazabilidad_fuente` | `valor_original` / `valor_normalizado` | `TEXT` | Sí | — | Valor individual de cada columna fuente y resultado de normalización; no reemplazar el original. | NO. DE PARCELA / NO. DE PARCELA PPT | Auditoría de identidad parcelaria |
| `trazabilidad_fuente` | `mensajes` | `JSONB` | No | — | Explicaciones de normalización, discrepancias o ausencia de identificador. | Revisión de fuente | Aclaración humana |

---

## 12. Vistas y Read-Models de Reporting (Base de Datos)

| Nombre de la Vista | Nivel de Detalle / Granularidad | Indicadores y Columnas Expuestas | Regla de Deduplicación y Aislamiento |
|---|---|---|---|
| `vw_hito_seguimiento` | Una fila por hito único (`clave_hito`). | `id_proyecto`, `id_entidad`, `ambito`, `tipo_cop_operativo`, `tipo_convenio`, `destino_superficie`, `fecha_programada`, `fecha_realizada`, `indicador`, `cantidad`, `superficie_ha`, `monto`. | Agrega y deduplica en origen antes de proyectar a tiempo; asigna claves canónicas (`convenio:n`, `pago:n`). |
| `vw_reporte_avance_periodo` | Desglose temporal (año, mes, trimestre). | 15 columnas: `id_proyecto`, `id_entidad`, `ambito`, `tipo_cop_operativo`, `tipo_convenio`, `destino_superficie`, `anio`, `mes`, `trimestre`, `indicador`, `programado`, `realizado`, `cantidad`, `superficie_ha`, `monto`. | Filtros dimensionales completos. Sólo proyecta fechas canónicas de negocio. Excluye proyectos inactivos. |
| `vw_dashboard_kpi` | Agregado anual por proyecto e indicador. | `id_proyecto`, `anio`, `indicador`, `programado`, `realizado`, `cantidad`, `superficie_ha`, `monto`. | Conteo exacto de `COUNT(DISTINCT clave_hito)`; evita que relaciones 1:N o N:M inflen indicadores anuales. |
| `vw_reporte_snapshot_actual` | Corte fotográfico del estado presente. | `id_proyecto`, `id_entidad`, `ambito`, `indicador`, `tipo_cop_operativo`, `destino_superficie`, `cantidad`, `superficie_ha`, `monto`. | No acepta año/mes/trimestre. Reporta núcleos, parcelas intervenidas, superficies físicas y condición TUC acumulada. |
| `vw_convenio_colectivo_destino` | Detalle por `id_convenio + destino_superficie`. | `id_convenio`, `destino_superficie`, `ambito`, `tipo_convenio`, `superficie_ha`, `superficie_declarada_ha`, `monto_declarado`, `fecha_firma`. | `monto_declarado` es **NO ADITIVO**; superficie física proviene de `AfectacionUnidadAgraria`. |
| `vw_seguimiento_estado_actual` | Estado vigente por proyecto-núcleo y objetivo. | `id_proyecto_nucleo`, `entidad_tipo`, `entidad_id`, `estado_actual`, `tipo_ultimo_evento`, `motivo_actual`, `fecha_ultimo_evento`. | Computa deterministamente el estado vigente basándose en el evento más reciente sin alterar registros base. |


## Conciliación GIS por proyecto — contrato 025

### Entidades complementarias nuevas

| Tabla | Clave y referencias | Campos funcionales | Restricciones y uso |
|---|---|---|---|
| `proyecto_configuracion_gis` | PK/FK `id_proyecto`; FK `srid_trabajo → spatial_ref_sys` | `srid_trabajo`, auditoría estándar | Una configuración explícita por proyecto; sin fila se usa 4326. Cambio bloqueado cuando hay geometrías confirmadas. |
| `importacion_feature_candidato` | PK bigint `id_candidato`; FKs importación, feature/importación, `id_proyecto_nucleo`, `id_parcela` opcional | `criterio`, `clasificacion`, `coincidencias`, `estado`, `geometria_previa_hash`, `id_usuario_revision`, `fecha_revision`, auditoría estándar | 0..N destinos tipados. `clasificacion`: exacta/fuerte/revision; `estado`: propuesto/seleccionado/rechazado/confirmado. Una selección por feature y por destino/importación. Se valida ámbito y vínculo administrativo. |
| `importacion_feature_decision` | PK bigint `id_decision`; FK feature; FK compuesta candidato/feature opcional; FK usuario | `accion`, `motivo`, `creado_por`, `creado_en` | Append-only. Acciones seleccionar/confirmar/rechazar/ignorar. Ignorar no lleva candidato. |
| `proyecto_nucleo_geometria` | PK bigint `id_geometria`; FK `id_proyecto_nucleo`; FK única `id_importacion_feature` | `version`, `es_vigente`, `geometria_poligono`, `geometria_trabajo`, `srid_trabajo`, `fuente`, `fecha_fuente`, auditoría estándar | Versionado por vínculo administrativo, una vigente; geometrías no vacías/válidas. Procedencia se obtiene de feature/importación, incluyendo SHA y transformaciones. |
| `proyecto_parcela_geometria` | Igual a núcleo, más FK `id_parcela` | Mismos campos geométricos y de auditoría | Versionado por `id_proyecto_nucleo + id_parcela`; requiere vínculo administrativo por afectación, no sólo pertenencia al núcleo. |

Las geometrías web son `geometry(MULTIPOLYGON,4326)`. Las geometrías de trabajo son `geometry(MULTIPOLYGON)` con SRID explícito validado contra `srid_trabajo`, dimensión XY, validez y no vacío. Ambas representaciones cuentan con GiST. Estas entidades no duplican el modelo administrativo.

`vw_gis_parcela_proyecto` contiene `id_proyecto`, `id_proyecto_nucleo`, `id_parcela`, `id_nucleo`. Deriva exclusivamente de `ProyectoNucleo → Afectacion → AfectacionUnidadAgraria → UnidadAgraria → Parcela`, con todos los registros activos y núcleos concordantes. No usa intersección espacial.

### Ampliaciones de tablas existentes

| Tabla | Campo nuevo | Tipo / significado |
|---|---|---|
| `importacion_archivo` | `version_pipeline` | varchar(40), no nulo; histórico `legacy-v1`, nuevo `conciliacion-v2`. |
| `importacion_archivo` | `srid_trabajo` | integer no nulo, FK `spatial_ref_sys`; CRS de trabajo fijado al procesar. |
| `importacion_archivo` | `crs_fuente_wkt` | text nullable; WKT del CRS leído por GDAL. |
| `importacion_feature` | `geometria_original` | geometry nullable, sin typmod; conserva WKB/CRS/dimensión de origen. |
| `importacion_feature` | `geometria_trabajo` | geometry(MULTIPOLYGON) nullable; XY válida/no vacía. |
| `importacion_feature` | `crs_fuente` | text nullable; referencia del CRS fuente. |
| `importacion_feature` | `dimension_fuente` | varchar(8), XY/XYZ/XYM/XYZM. |
| `importacion_feature` | `estado_conciliacion` | varchar(30) no nulo: pendiente/coincidencia_exacta/candidato/ambiguo/sin_coincidencia/confirmado/rechazado/ignorado. |
| `derecho_via_proyecto` | `id_importacion` | bigint nullable, FK importación; conserva compatibilidad de versiones anteriores. |
| `derecho_via_proyecto` | `sha256` | char(64) nullable, SHA del archivo fuente. |
| `derecho_via_proyecto` | `srid_trabajo` | integer nullable, FK `spatial_ref_sys`. |
| `derecho_via_proyecto` | `geometria_trabajo` | geometry(MULTIPOLYGON) nullable, XY válida/no vacía, SRID concordante. |

Se conserva en `importacion_archivo` el nombre original/almacenado, tamaño, SHA, proyecto, objetivo, fuente/fecha, estados, contadores y reporte existentes. El archivo almacenado es temporal: el reporte declara `archivo_original_retenido = false`; se conserva trazabilidad técnica mediante WKB y atributos autorizados, sin retener la copia con posibles datos personales.

`importacion_feature` conserva índice, FID externo, capa, geometría 4326 normalizada, atributos originales/normalizados permitidos, errores, advertencias, transformaciones, aceptación y auditoría existentes. En `conciliacion-v2`, `registro_destino_id` sólo se establece al confirmar: para núcleos es `id_proyecto_nucleo`; para parcelas es `id_parcela` (el candidato conserva además el vínculo del proyecto); para DDV es `id_derecho_via`. Los triggers interpretan el campo según objetivo y versión, preservando el contrato histórico.

La deduplicación activa usa `(id_proyecto, tipo_objetivo, sha256, version_pipeline, srid_trabajo)`. `PARCELA` y `Num_parcela` nunca se fusionan ni tienen precedencia global. `coincidencias` es un array de criterios observados, no un contenedor arbitrario de destinos: las relaciones administrativas permanecen normalizadas mediante FKs.

Los endpoints de features filtran atributos mediante una lista permitida, también al leer filas históricas. No se almacenan ni se utilizan nombres personales, CURP, domicilios, fechas de nacimiento o certificados. `Name`, `NOM_SEDATU` y atributos de semántica personal incierta se excluyen. No se calculan superficies administrativas a partir de geometría.

Referencias GIS renumeradas excepcionalmente desde 020–024 a 021–025; los originales
y la correspondencia se conservan en [MIGRACIONES.md](MIGRACIONES.md). No cambió el
modelo funcional GIS ni administrativo.
