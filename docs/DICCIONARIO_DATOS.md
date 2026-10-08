# Diccionario de Datos — SOFTWARE-PA

> **Autoridad:** Especificación canónica del modelo físico y lógico de datos de SOFTWARE-PA.  
> **Validación:** Verificado contra `backend/app/models.py`, migraciones canónicas `001–028` y read-models de base de datos en PostgreSQL 15 / PostGIS.

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
| `clave_proyecto` | `VARCHAR(30)` | No | UNIQUE | Código institucional del proyecto. | PROYECTO | Identificador de negocio |
| `nombre_proyecto` | `VARCHAR(200)` | No | — | Nombre descriptivo oficial. | PROYECTO | Encabezados y reportes |
| `descripcion` | `TEXT` | Sí | — | Alcance y notas descriptivas. | Notas | Interfaz |
| `fecha_inicio` | `DATE` | Sí | — | Fecha de arranque institucional del proyecto. | Calendario | Trazabilidad |
| `fecha_fin` | `DATE` | Sí | — | Fecha final registrada; no implementa un estado de proyecto completado. | Cronograma | Trazabilidad |

### 2.3.1 `derecho_via_proyecto`

DDV cartográfico canónico ligado directamente a `proyecto`. Admite historial de versiones y como máximo una versión vigente por proyecto. `es_vigente` expresa vigencia cartográfica; `activo` expresa baja lógica. Una versión anterior conserva `activo = true` al ser sustituida. `trazo_proyecto` (`MULTILINESTRING`) permanece como estructura legacy para consumidores actuales.

| Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen | Uso |
|---|---|---|---|---|---|---|
| `id_derecho_via` | `INTEGER` | No | PK | Identificador de la versión. | Sistema | Auditoría |
| `id_proyecto` | `INTEGER` | No | `proyecto.id_proyecto` | Proyecto propietario del DDV. | Proyecto | Alcance |
| `version` | `INTEGER` | No | `UNIQUE(id_proyecto, version)`, `> 0` | Versión secuencial por proyecto. | Captura cartográfica | Historial |
| `es_vigente` | `BOOLEAN` | No | Índice único parcial por proyecto; default `false` | Marca la versión cartográfica vigente; requiere `activo = true`. | Promoción explícita | Selección de la versión publicada en `/mapa` |
| `geometria_poligono` | `geometry(MULTIPOLYGON,4326)` | No | GiST; no vacía y válida | Polígono del Derecho de Vía. | Cartografía | Capa poligonal DDV en `/mapa` |
| `fuente` | `VARCHAR(250)` | No | No vacía | Procedencia de la geometría. | Cartografía | Trazabilidad |
| `fecha_fuente` | `DATE` | Sí | — | Fecha declarada de la fuente. | Cartografía | Trazabilidad |

Incluye las columnas estándar de auditoría y baja lógica descritas en §1. No sustituye superficies administrativas. Desde B-07, el endpoint `/mapa` publica el DDV activo y vigente como capa independiente de `trazo_proyecto`; los endpoints de trazo no cambian.

### 2.3.2 Staging de importación DDV

`importacion_archivo.tipo_objetivo = 'derecho_via_proyecto'` identifica el flujo estricto de GeoPackage. En este objetivo, `formato_detectado = 'gpkg'`, `mapeo` y `opciones_mapeo` son objetos vacíos, `id_perfil` es nulo y `crs_destino = 'EPSG:4326'`. `importacion_archivo` conserva nombre del archivo, tamaño, SHA-256, fuente, fecha, CRS original, capa en el reporte, contadores, usuario y fechas. `importacion_feature` conserva índice, capa, atributos originales, geometría normalizada, estado, errores, advertencias, transformaciones y, tras confirmar, `registro_destino_id` hacia el DDV del mismo proyecto. Una reparación válida registra `GEOMETRIA_REPARADA` y requiere aceptación explícita; una geometría irrecuperable queda en error. El staging no modifica `derecho_via_proyecto` ni entidades administrativas.

### 2.4 `nucleo_agrario`
Catálogo maestro nacional de núcleos agrarios (ejidos y comunidades). Su identidad interna permanece en `id_nucleo`; para el catálogo RAN/PHINA, la `cve_unica` oficial se almacena físicamente en `id_nucleo_fuente` y se identifica junto con `fuente_datos = 'RAN_PHINA_CATALOGO_NUCLEOS'`. No existe una columna física `clave_ran`. `ProyectoNucleo` continúa siendo el vínculo operativo con cada proyecto, conforme al principio Excel-First.

La conciliación vigente usa `conciliacion-v3-historia` (base 025 ampliada por 026) en `POST /api/proyectos/{id_proyecto}/geoespacial/nucleos/importaciones`. `cve_unica` es opcional: si está presente se verifica contra la identidad oficial; si falta se proponen candidatos por nombre y territorio dentro de los `ProyectoNucleo` existentes. Ninguna coincidencia guarda automáticamente geometría. La confirmación escribe únicamente `proyecto_nucleo_geometria`, conserva el campo global legacy y registra una decisión auditada. Véanse la base 025 y la historia técnica 026 al final de este diccionario.

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
| `geometria_poligono` | `geometry(MULTIPOLYGON,4326)` | Sí | SRID 4326 | Perímetro global legacy; no recibe nuevas escrituras de importación GIS. | Cartografía | Visor cartográfico de apoyo |

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
| `orv` | `numero_orv` | `VARCHAR(50)` | Sí | — | Número de acta o registro del ORV. | ORV | `/api/proyecto-nucleo/{id_proyecto_nucleo}/orv` |
| `orv` | `inicio_vigencia` / `fin_vigencia` | `DATE` | Sí | — | Periodo de ejercicio legal del Comisariado. | VIGENCIA ORV | Validación jurídica |
| `orv` | `id_estado_registral` | `BIGINT` | Sí | `catalogo_operativo` | Estado registral de la mesa directiva. | ESTATUS ORV | Evidencia institucional |
| `orv_integrante` | `id_persona` | `INTEGER` | No | `persona.id_persona` | Persona que ostenta el cargo ejidal. | INTEGRANTES | Acreditación en convenios |
| `orv_integrante` | `id_organo` / `id_cargo` / `id_calidad` | `BIGINT` | No | `catalogo_operativo` | Órgano, cargo y calidad según sus catálogos; no existe columna `cargo` de texto libre. | CARGO | `/api/orv/{id_orv}/integrantes` |
| `orv_integrante` | `fecha_inicio` / `fecha_fin` | `DATE` | Sí | — | Periodo funcional con límites inclusivos. | Vigencia del cargo | Histórico funcional |
| `orv_integrante` | `id_tipo_fin` / `detalle_fin` | `BIGINT` / `TEXT` | Sí | `catalogo_operativo` para tipo | Causa y detalle del cierre; fecha de fin y tipo deben coexistir. | Cierre funcional | `/api/orv-integrantes/{id_orv_integrante}/finalizar` |
| `orv_integrante` | `activo` | `BOOLEAN` | No | — | Estado administrativo; un periodo finalizado puede conservar `true`. | Sistema | Baja lógica y restauración |
| `orv_integrante` | `fecha_baja` / `motivo_baja` / `id_usuario_baja` | `TIMESTAMPTZ` / `TEXT` / `INTEGER` | Sí | `usuario` para actor | Obligatorios en baja administrativa y nulos cuando activo. | Auditoría | DELETE / reactivar |
| `padron_historial` | `fecha_padron` | `DATE` | Sí | — | Fecha de expedición del padrón ejidal. | FECHA PADRÓN | Quórum de asamblea |
| `padron_historial` | `numero_ejidatarios_comuneros` | `INTEGER` | Sí | — | Total de sujetos de derecho reconocidos. | NO. SUJETOS | Verificación de mayorías |

`vigente` es una propiedad calculada, no una columna: activo, inicio alcanzado
y fin no vencido, incluyendo ambos límites. No incorpora el periodo del ORV
padre. `finalizar` conserva el estado activo; la baja administrativa conserva el
periodo y la causa del cierre. `reactivar` limpia únicamente los campos de baja,
sin eliminar `fecha_fin`, `id_tipo_fin` ni `detalle_fin`.

El listado conserva `OrvIntegranteDetailResponse`, incluidos los campos de baja
ya existentes, y el orden por órgano, cargo y nombre. `incluir_historico=false`
y `incluir_bajas=false` son los valores predeterminados:

| Histórico | Bajas | Universo |
|---|---|---|
| false | false | Activos vigentes |
| true | false | Todos los activos |
| false | true | Activos vigentes más todas las bajas, independientemente de sus fechas |
| true | true | Todos los activos y todas las bajas |

La Persona permanece obligatoriamente activa. El ORV y núcleo deben estar
activos y se conserva el acceso de lectura para admin, operador, visualizador
y geógrafo; la opción de bajas no amplía el alcance por proyecto. No resuelve
el actor a datos de perfil. La baja y reactivación siguen siendo exclusivas de
admin. No se modifica la exclusión temporal por ORV/órgano/cargo/calidad para
filas activas, ni se introduce reapertura o cambio de esquema.

### 3.2 `actividad_campo`
Sensibilización comunitaria y caminamientos técnicos.

Desde 027 también es objetivo documental directo: `documento_vinculo.entidad_tipo = 'actividad_campo'` y `entidad_id = actividad_campo.id_actividad`. El acceso se deriva de `id_proyecto_nucleo` hacia el proyecto, con actividad y vínculo ProyectoNucleo activos; `id_afectacion` es opcional y no determina la autorización documental.

| Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|
| `id_actividad` | `INTEGER` | No | PK | Identificador primario de la actividad. | Sistema | `/api/proyecto-nucleo/{id_proyecto_nucleo}/actividades` |
| `id_proyecto_nucleo` | `INTEGER` | No | `proyecto_nucleo` | Proyecto-núcleo donde se efectuó. | Fila Excel | Agrupador operativo |
| `tipo_actividad` | `VARCHAR(30)` | No | — | Solo `sensibilizacion` o `caminamiento`. | Bloques W:AH | Hito de avance |
| `id_tipo_cop_operativo` | `BIGINT` | Sí | `catalogo_operativo` | Dimensión COP asociada (`ORIGEN`, etc.). | TIPO COP | Reporting dimensional |
| `contexto_actividad` | `VARCHAR(40)` | No | — | Contexto específico (`general`, etc.). | Notas | Trazabilidad |
| `fecha_programada` | `DATE` | Sí | — | Fecha agendada para el evento. | PROGRAMADA | Indicador de programación |
| `fecha_realizada` | `DATE` | Sí | — | Fecha efectiva de ejecución en campo. | REALIZADA | Indicador de avance real |
| `responsable` | `VARCHAR(300)` | Sí | — | Brigadista que condujo la actividad. | RESPONSABLE | Auditoría operativa |
| `resultado` | `TEXT` | Sí | — | Minuta o acuerdos alcanzados. | RESULTADO | Despliegue en expediente |

---

## 4. Derechos Individuales: Parcelas y Titulares

### 4.1 `parcela` y `parcela_titular`
La unidad operativa central de la ruta individual.

`Parcela.no_parcela` es el único identificador funcional canónico; no existe un segundo campo de dominio `no_parcela_ppt`. Sus orígenes Excel son `NO. DE PARCELA` / `NO. DE PARCELA PPT`. Los valores fuente individuales se preservan mediante `TrazabilidadFuente` / `ImportacionCelda` (modelo implementado: `ImportacionTabularCelda`), **no en dos columnas de `Parcela`**. Deben conservarse por columna, cuando corresponda, `archivo`, `hoja`, `fila`, `columna`, `valor_original`, `valor_normalizado`, `tratamiento` y `mensajes`; en las celdas de importación, archivo y hoja se obtienen de `ImportacionTabular`.

La resolución del identificador sigue [MODELO_FUNCIONAL.md §6.1](MODELO_FUNCIONAL.md#61-identificador-funcional-canónico-único) y [FUENTES_Y_COBERTURA_EXCEL.md §3.1](FUENTES_Y_COBERTURA_EXCEL.md#31-unicidad-del-identificador-parcelario-no_parcela): equivalencia o diferencia de formato produce un único valor conservando ambos originales; un solo valor presente se utiliza con su procedencia exacta; divergencia sustantiva requiere **REVISAR** y aclaración humana sin crear automáticamente dos parcelas ni asumir prioridad PPT. Sin ambos valores, `no_parcela` puede quedar `NULL` y la ausencia se conserva en trazabilidad/revisión al importar, incluidas las 17 filas auditadas.

La conciliación vigente usa `conciliacion-v3-historia` (base 025 ampliada por 026) en `POST /api/proyectos/{id_proyecto}/geoespacial/parcelas/importaciones`. `cve_unica_nucleo` es opcional y no se inventa. Sólo son destinos las parcelas previamente vinculadas al proyecto por la cadena administrativa de afectación. `PARCELA` y `Num_parcela` se conservan y comparan separadamente; letras, sufijos y otros signos permanecen distintos. La confirmación escribe `proyecto_parcela_geometria`, sin actualizar la geometría global ni superficies administrativas. Véanse la base 025 y la historia técnica 026 al final de este diccionario.

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `parcela` | `id_parcela` | `INTEGER` | No | PK | Identificador interno de la parcela. | Sistema | `/api/parcelas/{id_parcela}` |
| `parcela` | `id_nucleo` | `INTEGER` | No | `nucleo_agrario` | Núcleo agrario al que pertenece. | NÚCLEO | Pertenencia agraria |
| `parcela` | `no_parcela` | `VARCHAR(80)` | Sí | — | **Único identificador funcional canónico.** | NO. DE PARCELA / NO. DE PARCELA PPT | Identificación unívoca |
| `parcela` | `tipo_parcela` | `VARCHAR(30)` | No | — | Ejidal, comunal, infraestructura, etc. | TIPO PARCELA | Clasificación |
| `parcela` | `geometria_poligono` | `geometry(MULTIPOLYGON,4326)` | Sí | SRID 4326 | Polígono global legacy; no recibe nuevas escrituras de importación GIS. | Legacy | Visor cartográfico (opcional) |
| `parcela_titular` | `id_parcela` | `INTEGER` | No | `parcela.id_parcela` | Parcela correspondiente. | Fila titular | Vínculo de titularidad |
| `parcela_titular` | `id_persona` | `INTEGER` | No | `persona.id_persona` | Sujeto de derecho acreditado. | TITULAR | Suscripción de convenios |
| `parcela_titular` | `tipo_derecho` | `VARCHAR(50)` | No | — | Titular, posesionario, sucesor. | CALIDAD | Cláusulas contractuales |
| `parcela` | `certificado_parcelario` | `VARCHAR(120)` | Sí | — | Folio del certificado parcelario oficial. | CERTIFICADO | Acreditación jurídica |
| `parcela` | `folio_derechos` | `VARCHAR(120)` | Sí | — | Folio registral de derechos agrarios. | FOLIO | Acreditación jurídica |
| `parcela` | `constancia_vigencia_fecha` | `DATE` | Sí | — | Fecha validada de la constancia emitida por RAN; textos mixtos permanecen en trazabilidad. | CONSTANCIA | Soporte de vigencia |

---

### 4.2 `persona` — búsqueda y reutilización

Persona es una identidad compartida; su alcance por proyecto se deriva de
relaciones de negocio activas (ORV, titulares parcelarios y de unidad agraria
directos/indirectos, comparecientes, intervinientes FIFONAFE y beneficiarios de
pago), respetando los padres activos de cada camino. No existe un vínculo
Persona–Proyecto creado automáticamente por el POST de Persona o la búsqueda.

`GET /api/personas` devuelve la proyección `PersonaBusquedaResponse`:

| Campo | Tipo del dato fuente | Nullable | Uso |
|---|---|---|---|
| `id_persona` | `INTEGER` | No | Seleccionar una Persona existente |
| `nombre` | `VARCHAR(300)` | No | Identificación |
| `apellido_paterno` | `VARCHAR(200)` | Sí | Identificación |
| `apellido_materno` | `VARCHAR(200)` | Sí | Identificación |
| `curp` | `VARCHAR(18)` | Sí | Búsqueda exacta e identificación |
| `rfc` | `VARCHAR(13)` | Sí | Búsqueda exacta; no es único |

No expone contacto, observaciones, origen, auditoría ni relaciones. Exige
exactamente un criterio: `q` (2–300 caracteres, todas las palabras en nombres o
apellidos, sin distinguir caja ni eliminar acentos), `curp` (no vacío, máximo
18) o `rfc` (no vacío, máximo 13). Se retiran espacios ordinarios exteriores;
CURP/RFC se comparan mediante `upper(btrim(...))`, sin modificar datos.
En `q`, `%`, `_` y `\` son literales. `limit` vale 20 por defecto (1–100) y
`skip` vale 0 por defecto (mínimo 0). Orden estable por apellidos, nombre e id,
sin distinguir caja y con apellidos nulos al final; visibilidad antes del límite.

Admin ve todas las Personas activas; operador, visualizador y geógrafo ven las
relacionadas con algún proyecto activo autorizado. Sólo el operador creador,
con algún proyecto activo autorizado, obtiene además sus verdaderas huérfanas:
sin proyectos derivados y sin referencias activas según
`fn_persona_tiene_relaciones_activas()`. Padres inactivos no bastan para esa
excepción. Personas inactivas y coincidencias fuera de alcance no se devuelven
(lista vacía, HTTP 200). El criterio ausente, vacío, combinado o inválido y la
paginación inválida producen 422; siguen aplicándose autenticación y roles.

`uq_persona_curp` conserva su definición: único sobre `upper(curp)` para
Personas activas con CURP no nulo, sin `btrim`. Por ello la búsqueda normalizada
puede devolver varias coincidencias visibles. No se introduce unicidad de RFC,
normalización de escrituras ni cambios de esquema; el esquema vigente es 028.
La selección no crea relaciones y no amplía permisos de captura o edición.

## 5. Afectaciones y Unidades Agrarias

### 5.1 `afectacion`, `unidad_agraria` y `afectacion_unidad_agraria`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `afectacion` | `id_afectacion` | `INTEGER` | No | PK | Identificador del subexpediente de afectación. | Sistema | `/api/afectaciones/{id_afectacion}` |
| `afectacion` | `id_proyecto_nucleo` | `INTEGER` | No | `proyecto_nucleo` | Proyecto-núcleo propietario. | Fila Excel | Agrupador maestro |
| `unidad_agraria` | `id_parcela` | `INTEGER` | Sí | `parcela.id_parcela` | Parcela del destino, cuando corresponde. | NO PARCELA | Afectacion se relaciona mediante AfectacionUnidadAgraria, sin FK directa a Parcela |
| `afectacion` | `tipo_afectacion` | `VARCHAR(20)` | No | — | `colectivo` o `individual`. | Ámbito | Bifurcación funcional |
| `afectacion` | `id_tipo_cop_operativo` | `BIGINT` | Sí | `catalogo_operativo` | Clasificación COP (`ORIGEN`, etc.). | TIPO COP | Reporting dimensional |
| `afectacion` | `superficie_preliminar_ha` | `NUMERIC(15,7)` | Sí | — | Superficie estimada inicialmente en campo. | SUP. PRELIMINAR | Referencia técnica |
| `afectacion` | `superficie_afectada_ha` | `NUMERIC(15,7)` | Sí | — | **Superficie administrativa capturada.** | SUP. AFECTADA | Cómputo y reporting administrativo |
| `afectacion` | `avaluo_monto` | `NUMERIC(18,2)` | Sí | — | Monto determinado por INDAABIN. | AVALÚO MAESTRO | Referencia indemnizatoria |
| `unidad_agraria` | `id_destino_superficie` | `BIGINT` | Sí | `catalogo_operativo` | Destino de suelo (TUC, canal, camino, etc.). | DESTINO | Catálogo operativo |
| `afectacion_unidad_agraria` | `superficie_afectada_ha` | `NUMERIC(15,7)` | Sí | — | Superficie física exacta por destino de suelo. | SUP. DESTINO | Desglose multidestino |

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
| `asamblea_convocatoria` | `ordinal` | `INTEGER` | No | — | Número de convocatoria (1 = 1ª, 2 = 2ª, etc.). | 1A / 2A | Quórum legal Ley Agraria |
| `asamblea_convocatoria` | `fecha_expedicion` | `DATE` | Sí | — | Fecha en que se fijó la convocatoria. | EXPEDICIÓN | Validez temporal |
| `asamblea_convocatoria` | `fecha_programada` | `DATE` | Sí | — | Fecha agendada para la asamblea. | PROGRAMADA | Hito programado |
| `asamblea_convocatoria` | `fecha_realizacion` | `DATE` | Sí | — | Fecha en que efectivamente se desahogó. | REALIZADA | Hito de asamblea |
| `asamblea_convocatoria` | `id_resultado` | `BIGINT` | Sí | `catalogo_operativo` | `celebrada`, `no_verificativo`, `cancelada`. | RESULTADO | Solo celebrada acredita hito |

---

## 7. Convenios de Ocupación Previa (COP)

### 7.1 `convenio`, `convenio_afectacion` y `convenio_compareciente`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `convenio` | `id_convenio` | `INTEGER` | No | PK | Identificador del convenio celebrado. | Sistema | `/api/convenios/{id_convenio}` |
| `convenio` | `ambito` | `VARCHAR(20)` | No | — | `colectivo` o `individual`. | Ámbito | Bifurcación funcional |
| `convenio` | `tipo_convenio` | `VARCHAR(40)` | Sí | — | `cop_original`, `modificatorio`, `ampliacion`... | TIPO CONVENIO | Catálogo contractual |
| `convenio` | `modalidad_especial` | `VARCHAR(30)` | Sí | — | `permuta` u otras modalidades excepcionales. | MODALIDAD | Tratamiento de permuta |
| `convenio` | `id_asamblea_autorizacion` | `INTEGER` | Sí | `asamblea.id_asamblea` | Asamblea que autorizó la firma (colectivo). | ASAMBLEA | Null en individuales |
| `convenio` | `fecha_programada_firma` | `DATE` | Sí | — | Fecha meta de formalización. | PROG. FIRMA | Programación de convenio |
| `convenio` | `fecha_firma` | `DATE` | Sí | — | **Fecha real de firma del convenio.** | FIRMA REAL | Hito de formalización |
| `convenio` | `superficie_ha` | `NUMERIC(15,7)` | Sí | — | Superficie total amparada en el instrumento. | SUPERFICIE | Declarado en instrumento |
| `convenio` | `monto_100` | `NUMERIC(18,2)` | Sí | — | **Importe pactado total del convenio.** | MONTO 100% | **NO ADITIVO** en multidestino |
| `convenio_afectacion` | `id_convenio` / `id_afectacion` | `INTEGER` | No | FKs; pareja única cuando activa | Relación N:M entre convenios y afectaciones. | Cruce operativo | Cobertura sin duplicar montos |
| `convenio_compareciente` | `id_persona` | `INTEGER` | No | `persona.id_persona` | Comparecientes (titulares o comisariados). | FIRMANTES | Acreditación de partes |

---

## 8. Tramitaciones Registrales ante el RAN

### 8.1 `tramite_ran` y `tramite_ran_evento`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `tramite_ran` | `id_tramite_ran` | `BIGINT` | No | PK | Identificador del expediente registral. | Sistema | `/api/tramites-ran` |
| `tramite_ran` | `id_asamblea` | `INTEGER` | Sí | `asamblea.id_asamblea` | Vinculado a acta de asamblea (exclusivo). | RAN ACTA | Inscripción de asamblea |
| `tramite_ran` | `id_convenio` | `INTEGER` | Sí | `convenio.id_convenio` | Vinculado a convenio COP (exclusivo). | RAN CONVENIO | Inscripción de convenio |
| `tramite_ran` | `id_orv` | `INTEGER` | Sí | `orv.id_orv` | Vinculado a acta de elección ORV. | RAN ORV | Inscripción de directiva |
| `tramite_ran` | `fecha_programada_ingreso` | `DATE` | Sí | — | Fecha agendada de presentación ante el RAN. | PROG. INGRESO | Planificación registral |
| `tramite_ran_evento` | `id_tipo_evento` | `BIGINT` | No | `catalogo_operativo` | `ingreso`, `prevencion`, `inscripcion`, etc. | Hitos RAN | Línea de tiempo registral |
| `tramite_ran_evento` | `fecha_evento` | `DATE` | Sí | — | Fecha formal del sello o actuación del RAN. | FECHA INGRESO / INSCRIPCIÓN | Fechas de hito oficiales |
| `tramite_ran_evento` | `numero_solicitud` | `VARCHAR(150)` | Sí | — | Número oficial de trámite / código de barras. | NO. SOLICITUD | Seguimiento en portal RAN |
| `tramite_ran_evento` | `calificacion` | `TEXT` | Sí | — | Calificación intermedia (favorable / observaciones). | CALIFICACIÓN | No equivale a inscripción |

---

## 9. Procedimiento FIFONAFE

### 9.1 `tramite_fifonafe`, `tramite_fifonafe_evento` y `tramite_fifonafe_afectacion`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `tramite_fifonafe` | `id_tramite_fifonafe` | `INTEGER` | No | PK | Identificador de la solicitud fiduciaria. | Sistema | `/api/fifonafe/{id_tramite_fifonafe}` |
| `tramite_fifonafe` | `id_proyecto_nucleo` | `INTEGER` | No | `proyecto_nucleo` | Proyecto-núcleo propietario. | Fila Excel | Alcance institucional |
| `tramite_fifonafe` | `ambito` | `VARCHAR(20)` | No | — | `colectivo` o `individual`. | Ámbito | Cadena histórica v1; v2 aplica evidencia integral de 008 |
| `tramite_fifonafe` | `hay_conflictos` | `BOOLEAN` | Sí | Triestado | Resultado del análisis de conflictos sociales. | NO CONFLICTOS | Semántica independiente |
| `tramite_fifonafe` | `acuse_fifonafe_fecha` | `DATE` | Sí | — | Fecha del sello de recepción de FIFONAFE. | ACUSE | Evidencia fiduciaria |
| `tramite_fifonafe_evento` | `id_tipo_evento` | `BIGINT` | No | `catalogo_operativo` | Tipo catalogado: oficios históricos y eventos v2 de 008. | CC:CF | Cadena de correspondencia |
| `tramite_fifonafe_evento` | `numero_oficio` | `VARCHAR(150)` | Sí | — | Número oficial de correspondencia. | NO. OFICIO | Trazabilidad documental |
| `tramite_fifonafe_evento` | `fecha_oficio` | `DATE` | Sí | — | Fecha asentada en el oficio. | FECHA OFICIO | Fecha documental; MAX en indicador legado, hitos separados en v2 |
| `tramite_fifonafe_afectacion` | `id_tramite_fifonafe` / `id_afectacion` | `INTEGER` | No | FKs; pareja única cuando activa | Afectaciones y parcelas cubiertas. | Cruce fiduciario | Cobertura N:M sin duplicar |

---

## 10. Cadena Financiera: Indemnización y Pagos

### 10.1 `indemnizacion` y `pago`

Indemnizacion aplica a afectaciones colectivas e individuales. Su estatus admite
`pendiente`, `programado`, `en_proceso`, `completo`, `pagado`, `cancelado` y `otro`
(con descripción). No tiene columna `monto_total`: el avalúo está en Afectacion,
el monto pactado en Convenio y los desembolsos en Pago, sin equivalencia automática.
El bloque/estatus de ambos Excel se revalidó en
[FUENTES_Y_COBERTURA_EXCEL.md §3.4](FUENTES_Y_COBERTURA_EXCEL.md#34-indemnización-colectiva-e-individual-evidencia-revalidada).

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `indemnizacion` | `id_indemnizacion` | `INTEGER` | No | PK | Identificador del expediente indemnizatorio. | Sistema | `/api/afectaciones/{id_afectacion}/indemnizacion` |
| `indemnizacion` | `id_afectacion` | `INTEGER` | No | `afectacion.id_afectacion` | Afectación compensada (máximo 1 activa). | Fila Excel | Vínculo físico |
| `indemnizacion` | `estatus` | `VARCHAR(30)` | No | — | `pendiente`, `en_proceso`, `pagado`, etc. | ESTATUS PAGO | Estado administrativo |
| `indemnizacion` | `fecha_resolucion` | `DATE` | Sí | — | **Fecha legal en que se resolvió la indemnización.** | FECHA RESOLUCIÓN | **Hito de indemnización resuelta** |
| `indemnizacion` | `fecha_entrega_expediente_pa` | `DATE` | Sí | — | Fecha de entrega del expediente SICT a PA. | ENTREGA SICT/PA | Trazabilidad interinstitucional |
| `pago` | `id_pago` | `INTEGER` | No | PK | Identificador del desembolso real. | Sistema | `/api/indemnizaciones/{id_indemnizacion}/pagos` |
| `pago` | `id_indemnizacion` | `INTEGER` | No | `indemnizacion` | Indemnización amparada. | Vínculo pago | Cadena canónica financiera |
| `pago` | `fecha_pago` | `DATE` | No | — | **Fecha real de entrega/dispersión del recurso.** | FECHA PAGO | **Hito de pago efectivo** |
| `pago` | `monto` | `NUMERIC(18,2)` | No | — | Cantidad líquida pagada en el evento. | MONTO PAGADO | Agregación económica |
| `pago` | `beneficiario_nombre` | `VARCHAR(300)` | No | — | Persona o núcleo que recibió el recurso. | BENEFICIARIO | Comprobación de entrega |

---

## 11. Subsistema Documental, Trazabilidad y Eventos

### 11.1 `documento`, `documento_version` y `documento_vinculo`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `documento` | `id_documento` | `INTEGER` | No | PK | Identidad lógica del documento. | Sistema | Rutas genéricas de documentos por objetivo |
| `documento` | `tipo_documento` | `VARCHAR(80)` | No | — | Texto legado/compatibilidad. No vacío según `btrim`; API rechaza NULL explícito y sólo espacios. | Tipo soporte | Nuevas capturas por ID guardan el nombre del catálogo; los históricos conservan su texto. |
| `documento` | `id_tipo_documento` | `BIGINT` | Sí | `catalogo_tipo_documento` | Clasificación autoritativa cuando existe; no se infiere a partir del texto legado. | Taxonomía V1 revisada | FK sin cascada; 028 no realiza backfill. |
| `documento` | `descripcion` | `TEXT` | Sí | — | Detalle libre del documento; obligatorio y no vacío para OTRO. | Detalle/observación | Validación Python y trigger SQL. |
| `documento` | `fecha_documento` | `DATE` | Sí | — | Fecha propia del documento físico. | FECHA OFICIO | Metadato jurídico |
| `documento` | `numero_folio` | `VARCHAR(150)` | Sí | — | Número de oficio, acta o folio impreso. | FOLIO / NO. OFICIO | Identificación documental |
| `documento_version` | `id_documento_version` | `BIGINT` | No | PK | Versión inmutable del archivo digital. | Sistema | Descarga de archivos |
| `documento_version` | `hash_sha256` | `CHAR(64)` | No | — | Hash criptográfico para integridad. | Archivo | Detección de alteración |
| `documento_vinculo` | `entidad_tipo` / `entidad_id` | `VARCHAR(50)` / `INTEGER` | No | Polimórfico | Entidad asociada (convenio, asamblea, actividad_campo...). | Asociación | Vinculación y aislamiento |

`chk_documento_vinculo_tipo` admite desde 027 los 22 tipos de 026 más `actividad_campo`. El trigger de objetivo reutiliza `fn_objetivo_controlado_existe`; `fn_objetivo_requisito_en_pn` y el CHECK de `expediente_requisito` ya admitían actividades y permanecen intactos. El vínculo conserva auditoría y baja lógica.

### 11.1.1 `catalogo_tipo_documento` (028)

Tabla con `id_tipo_documento BIGINT` identity, `codigo VARCHAR(80)` único e inmutable,
`nombre VARCHAR(250)` no vacío, `descripcion TEXT` nullable, `orden INTEGER >= 0`,
`activo BOOLEAN` y los campos comunes de auditoría/baja lógica. El código admite
ASCII mayúscula inicial y luego mayúsculas, números o underscore. No permite DELETE
físico; la baja requiere fecha, actor y motivo. Utiliza la auditoría existente.

Taxonomía V1: los 27 valores siguientes nacen activos. No incluye actividades,
estados, resultados registrales ni subtipos de convenio/COP.

| Código | Nombre | Descripción funcional | Orden |
|---|---|---|---|
| `MINUTA` | Minuta | Registro escrito de reunión o actividad. | 10 |
| `FOTOGRAFIA` | Fotografía | Evidencia fotográfica; la actividad respaldada se identifica en el contexto. | 20 |
| `ACTA_ASAMBLEA` | Acta de asamblea | Acta de acuerdos de asamblea, salvo los tipos específicos del catálogo. | 30 |
| `PADRON` | Padrón de ejidatarios/comuneros | Documento que identifica integrantes del núcleo; no equivale a cualquier lista de personas. | 40 |
| `ACTA_ELECCION_ORV` | Acta de elección de ORV | Acta que documenta la elección de órganos de representación y vigilancia. | 50 |
| `ACTA_REMOCION_ORV` | Acta de remoción de ORV | Acta de remoción, distinta del acto de elección. | 60 |
| `ACTA_NO_VERIFICATIVO` | Acta de no verificativo | Acta que acredita que una asamblea no se verificó. | 70 |
| `ACTA_COMPLEMENTARIA` | Acta complementaria | Documento complementario de un acto previo, identificado en la descripción. | 80 |
| `ACTA_DELIMITACION_DESTINO_ASIGNACION` | Acta de delimitación, destino y asignación de tierras | Acta específica sobre delimitación, destino y asignación de tierras. | 90 |
| `CONVOCATORIA_PRIMERA` | Primera convocatoria | Documento de primera convocatoria de asamblea. | 100 |
| `CONVOCATORIA_SEGUNDA` | Segunda convocatoria | Documento de segunda convocatoria de asamblea. | 110 |
| `CONVENIO` | Convenio | Instrumento de convenio/COP; el subtipo jurídico pertenece a la entidad Convenio. | 120 |
| `ACUSE_RAN` | Acuse de ingreso al RAN | Evidencia de recepción de un ingreso al RAN, distinta de la solicitud. | 130 |
| `SOLICITUD_RAN` | Solicitud de ingreso al RAN | Documento de solicitud de ingreso o reingreso al Registro Agrario Nacional. | 140 |
| `AVISO_INSCRIPCION_RAN` | Aviso de inscripción RAN | Aviso que comunica la inscripción de un instrumento. | 150 |
| `CONSTANCIA_INSCRIPCION_RAN` | Constancia de inscripción RAN | Constancia acreditativa de inscripción, distinta del aviso cuando sea identificable. | 160 |
| `FOLIO_EJIDOS_COMUNIDADES` | Documento de folio de ejidos/comunidades | Impresión o extracto del folio; un número aislado es metadato. | 170 |
| `CREDENCIAL_INE` | Credencial INE | Identificación oficial INE. | 180 |
| `CREDENCIAL_RAN` | Credencial RAN | Credencial expedida en contexto RAN, distinta de la identificación INE. | 190 |
| `CERTIFICADO_PARCELARIO` | Certificado parcelario | Documento de acreditación parcelaria. | 200 |
| `CERTIFICADO_DERECHOS_AGRARIOS` | Certificado de derechos agrarios | Medio de acreditación agraria distinto del certificado parcelario. | 210 |
| `CONSTANCIA_VIGENCIA_DERECHOS` | Constancia de vigencia de derechos | Constancia que acredita la vigencia del derecho. | 220 |
| `OFICIO` | Oficio | Comunicación formal identificada como oficio; emisor, destinatario y asunto son contexto. | 230 |
| `RESPUESTA` | Respuesta documental | Respuesta cuyo soporte no se identifica como oficio u otro tipo más concreto. | 240 |
| `VALIDACION` | Documento de validación | Documento que acredita una validación; no representa un estado de cumplimiento. | 250 |
| `AVALUO` | Avalúo | Documento de valoración; monto y contexto permanecen separados. | 260 |
| `OTRO` | Otro documento | Documento identificado no cubierto por los tipos anteriores; requiere descripción. | 999 |

`GET /api/catalogos/tipos-documento` sólo expone ID, código, nombre, descripción,
orden y activo. Una opción inactiva sigue siendo legible en documentos ya
clasificados y admite edición de sus otros metadatos, pero no nuevas selecciones.
La API serializa `clasificacion` con ID, código, nombre y activo, sin auditoría.
`OTRO` utiliza `Documento.descripcion`; no se crea otra columna de detalle.
`documento.estado`, `RequisitoDocumental`, `ExpedienteRequisito`, actividades y
vínculos conservan sus dominios separados. La transición futura de históricos
necesitará un mapeo aprobado; ni OTRO ni CONVENIO se asignan automáticamente.

### 11.2 `seguimiento_evento` y `trazabilidad_fuente`

| Entidad | Campo / Relación | Tipo SQL | Nullable | FK / Ref | Significado Funcional | Origen Excel | Uso / API / Reporting |
|---|---|---|---|---|---|---|---|
| `seguimiento_evento` | `id_seguimiento_evento` | `BIGINT` | No | PK | Identificador del evento histórico. | Sistema | `/api/seguimiento/{id_seguimiento_evento}` |
| `seguimiento_evento` | `id_proyecto_nucleo` | `INTEGER` | No | `proyecto_nucleo` | Proyecto-núcleo sobre el que incide. | Fila Excel | Pertenencia |
| `seguimiento_evento` | `id_tipo_evento` | `BIGINT` | No | `catalogo_operativo` | `suspension`, `reapertura`, `cierre`, etc. | Hechos de campo | Transiciones |
| `seguimiento_evento` | `id_motivo` | `BIGINT` | Sí | `catalogo_operativo` | `expropiacion_directa`, `juicio`, etc. | Motivos Excel | Justificación |
| `seguimiento_evento` | `fecha_evento` | `DATE` | Sí | — | Fecha en que ocurrió el suceso. | FECHA EVENTO | Cronología determinista |
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


## Conciliación GIS por proyecto — base 025 e historia 026

Las tablas y reglas de 025 se conservan y amplían por 026. La versión actualmente
utilizada por el código es `conciliacion-v3-historia`; `conciliacion-v2` permanece
como identificador histórico. Las métricas `ST_Area`/áreas GIS son auxiliares,
nunca superficie oficial ni sustitutos de `superficie_afectada_ha` o `superficie_ha`.

### Entidades cartográficas introducidas por 025

| Tabla | Clave y referencias | Campos funcionales | Restricciones y uso |
|---|---|---|---|
| `proyecto_configuracion_gis` | PK/FK `id_proyecto`; FK `srid_trabajo → spatial_ref_sys` | `srid_trabajo`, auditoría estándar | Una configuración explícita por proyecto; sin fila se usa 4326. Cambio bloqueado cuando hay geometrías confirmadas. |
| `importacion_feature_candidato` | PK bigint `id_candidato`; FKs importación, feature/importación, `id_proyecto_nucleo`, `id_parcela` opcional | `criterio`, `clasificacion`, `coincidencias`, `estado`, `geometria_previa_hash`, `id_usuario_revision`, `fecha_revision`, auditoría estándar | 0..N destinos tipados. `clasificacion`: exacta/fuerte/revision; `estado`: propuesto/seleccionado/rechazado/confirmado. Una selección por feature y por destino/importación. Se valida ámbito y vínculo administrativo. |
| `importacion_feature_decision` | PK bigint `id_decision`; FK feature; FK compuesta candidato/feature opcional; FK usuario | `accion`, `motivo`, `creado_por`, `creado_en` | Append-only. Acciones seleccionar/confirmar/rechazar/ignorar. Ignorar no lleva candidato. |
| `proyecto_nucleo_geometria` | PK bigint `id_geometria`; FK `id_proyecto_nucleo`; FK única `id_importacion_feature` | `version`, `es_vigente`, `geometria_poligono`, `geometria_trabajo`, `srid_trabajo`, `fuente`, `fecha_fuente`, auditoría estándar | Versionado por vínculo administrativo, una vigente; geometrías no vacías/válidas. Procedencia se obtiene de feature/importación, incluyendo SHA y transformaciones. |
| `proyecto_parcela_geometria` | Igual a núcleo, más FK `id_parcela` | Mismos campos geométricos y de auditoría | Versionado por `id_proyecto_nucleo + id_parcela`; requiere vínculo administrativo por afectación, no sólo pertenencia al núcleo. |

Las geometrías web son `geometry(MULTIPOLYGON,4326)`. Las geometrías de trabajo son `geometry(MULTIPOLYGON)` con SRID explícito validado contra `srid_trabajo`, dimensión XY, validez y no vacío. Ambas representaciones cuentan con GiST. Estas entidades no duplican el modelo administrativo.

`vw_gis_parcela_proyecto` contiene `id_proyecto`, `id_proyecto_nucleo`, `id_parcela`, `id_nucleo`. Deriva exclusivamente de `ProyectoNucleo → Afectacion → AfectacionUnidadAgraria → UnidadAgraria → Parcela`, con todos los registros activos y núcleos concordantes. No usa intersección espacial.

Desde B-07, `/mapa` lee la geometría activa y vigente por proyecto de núcleo/parcela; sólo si falta utiliza el campo global legacy del registro administrativo. Las parcelas se filtran siempre mediante `vw_gis_parcela_proyecto`, también para el fallback. Las versiones no vigentes no se publican y la lectura no modifica datos administrativos.

### Ampliaciones de tablas existentes

| Tabla | Campo nuevo | Tipo / significado |
|---|---|---|
| `importacion_archivo` | `version_pipeline` | varchar(40), no nulo; históricos `legacy-v1` y `conciliacion-v2`; vigente desde 026 `conciliacion-v3-historia`. |
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

`importacion_feature` conserva índice, FID externo, capa, geometría 4326 normalizada, atributos originales/normalizados permitidos, errores, advertencias, transformaciones, aceptación y auditoría existentes. Desde el contrato histórico `conciliacion-v2`, conservado en el vigente `conciliacion-v3-historia`, `registro_destino_id` sólo se establece al confirmar: para núcleos es `id_proyecto_nucleo`; para parcelas es `id_parcela` (el candidato conserva además el vínculo del proyecto); para DDV es `id_derecho_via`. Los triggers interpretan el campo según objetivo y versión, preservando el contrato histórico.

La deduplicación activa usa `(id_proyecto, tipo_objetivo, sha256, version_pipeline, srid_trabajo)`. `PARCELA` y `Num_parcela` nunca se fusionan ni tienen precedencia global. `coincidencias` es un array de criterios observados, no un contenedor arbitrario de destinos: las relaciones administrativas permanecen normalizadas mediante FKs.

Los endpoints de features filtran atributos mediante una lista permitida, también al leer filas históricas. No se almacenan ni se utilizan nombres personales, CURP, domicilios, fechas de nacimiento o certificados. `Name`, `NOM_SEDATU` y atributos de semántica personal incierta se excluyen. No se calculan superficies administrativas a partir de geometría.

Referencias GIS renumeradas excepcionalmente desde 020–024 a 021–025; los originales
y la correspondencia se conservan en [MIGRACIONES.md](MIGRACIONES.md). No cambió el
modelo funcional GIS ni administrativo.

### Historia técnica GIS (026)

| Entidad / campo | Significado y reglas |
|---|---|
| importacion_archivo.alcance_entrega | completa o parcial, explícito en las rutas estrictas de núcleos/parcelas; histórico desconocido = parcial. Inmutable. |
| importacion_archivo.id_importacion_anterior | FK a la última entrega finalizada del mismo proyecto/objetivo lógico al hacer staging. Inmutable. |
| importacion_conciliacion_ciclo | Intento numerado por importación; tipo histórico/inicial/reconciliación, motivo, algoritmo, usuario, fechas, UUID de idempotencia, snapshot de universo y resumen. Identidad inmutable y cierre único. |
| importacion_conciliacion_resultado | PK ciclo + feature, FK al staging y resultado de matching inmutable. Las decisiones explican el resultado posterior sin borrar el inicial. |
| candidato.id_ciclo / decision.id_ciclo | FKs compuestas garantizan ciclo, importación y feature coherentes. Los ciclos antiguos no se sobrescriben. |
| revision_cambio_gis | Observación inmutable: proyecto, objetivo ddv/nucleo/parcela, destino opcional, feature, importaciones y versiones con FKs tipadas. Tipos: geometria_modificada, aparece_en_nueva_version, desaparece_en_nueva_version, cambio_relacion_ddv. |
| revisión.id_nucleo_geometria_*, id_parcela_geometria_*, id_ddv_* | FKs a versiones históricas existentes. Una desaparición no elimina ni desactiva ninguna de ellas. |
| revisión.area_*_m2, porcentaje_diferencia, srid_medicion | Métricas GIS; NULL si no se acredita CRS proyectado con unidades en metros. Porcentaje de diferencia simétrica respecto del área anterior; no es superficie administrativa. |
| revisión.metricas | Información descriptiva auxiliar (política, componentes, tipo de medida); las relaciones estructurales usan FKs. |
| revision_cambio_gis_decision | Append-only: acción revisado/no_aplica/aplicado, motivo obligatorio, usuario, fecha, UUID único por revisión y FK opcional al evento existente. |
| decisión.id_seguimiento_evento | Sólo con aplicado. Evento activo del mismo proyecto y núcleo cuando corresponda, entidad compatible. No se crea ni actualiza desde GIS. |
| vw_revision_cambio_gis_estado | Estado pendiente o última acción por id_decision; no se guarda un estado administrativo ni otro estado físico. |

Las tablas de versiones de núcleo/parcela/DDV de 025 se reutilizan, con payloads
inmutables y una sola vigente. Las revisiones técnicas no cambian pertenencia,
afectaciones, convenios, trámites, superficies, avalúos ni eventos. Se preserva
TRANSVERSALES como tipo COP, sin implementar obras transversales GIS.


### Campos de API derivados, sin almacenamiento adicional

Las proyecciones de lectura descritas en [API.md §11](API.md#11-proyecciones-de-lectura-para-el-frontend-esquema-028)
añaden nombres mínimos de actores GIS y `destino` legible de revisiones, un
listado documental por procedencia y totales de paginación por header.
No son columnas, tablas ni relaciones nuevas. Usuario permanece intacto;
los nombres se consultan en bloque y las etiquetas de candidatos se obtienen
del snapshot existente `importacion_conciliacion_ciclo.universo_destinos`.
La versión documental vigente de la proyección es el máximo `numero_version`
de DocumentoVersion. Los vínculos y referencias de ExpedienteRequisito mantienen
su identidad, procedencia y autorizaciones actuales. No se añade migración 029.
