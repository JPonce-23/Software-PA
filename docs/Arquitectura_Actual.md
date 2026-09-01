# Arquitectura actual de SOFTWARE-PA

> Rama verificada: `feature/backend-logica`
> Esquema vigente: migraciones `001` a `039`
> Última validación: 2026-09-01
> Fuente de verdad: SQL aplicado, modelos SQLAlchemy, contratos Pydantic, API, frontend y pruebas del repositorio.

## 1. Estado implementado

SOFTWARE-PA administra el seguimiento de liberación de derecho de vía ferroviario sobre propiedad social. El contexto funcional es `ProyectoNucleo`, relación entre un proyecto y un núcleo agrario. Las referencias históricas se conservan como datos, no como expedientes.

El dominio vigente eliminó del código activo y del esquema objetivo la navegación y autorización por tramo, los ciclos artificiales de afectación y los gates administrativos espaciales. PostGIS se conserva para mapa, importación y validación técnica.

```text
Proyecto
├── UsuarioProyecto (alcance RBAC)
├── TrazoProyecto (MULTILINESTRING 4326)
└── ProyectoNucleo
    ├── Referencias
    ├── Responsables
    ├── ActividadesCampo
    ├── Afectaciones
    │   └── AfectacionUnidadAgraria N:M
    ├── Asambleas
    │   └── TramiteRan 1:N (→ TramiteRanEvento 1:N)
    ├── Convenios
    │   └── TramiteRan 1:N (→ TramiteRanEvento 1:N)
    ├── TramitesFIFONAFE
    │   └── TramiteFifonafeEvento 1:N
    └── Indemnizaciones
        └── Pagos

NucleoAgrario
├── PadronHistorial
├── ORV
│   ├── Integrantes
│   └── TramiteRan 1:N (→ TramiteRanEvento 1:N)
├── Parcelas
│   └── Titulares
└── UnidadesAgrarias
    └── Titulares
```

`Tramo`, `TramoNucleo`, `AfectacionCiclo`, `usuario_tramo`, candidatos espaciales y secciones de derecho de vía sólo pueden aparecer en las migraciones históricas o en comprobaciones explícitas de ausencia.

## 2. Stack y despliegue

| Capa | Implementación |
|---|---|
| Base | PostgreSQL 15, PostGIS 3.3, SQL versionado en `schema_migrations` |
| Backend | FastAPI, SQLAlchemy 2, Pydantic, Uvicorn |
| Frontend | React, Vite, React Router, Leaflet |
| Seguridad | Sesión en cookie HTTP-only, CSRF, bloqueo de acceso y RBAC por proyecto |
| Archivos | Almacenamiento controlado, metadatos y SHA-256 |
| Pruebas | Contrato SQL, pytest, ESLint/build y Playwright |
| Ejecución local | Docker Compose: `db`, `backend`, `frontend` y `pgadmin` |

La salud se expone en `/health` y devuelve la versión efectiva del esquema. FastAPI construye su engine exclusivamente con `DB_RUNTIME_USER` y `DB_RUNTIME_PASSWORD`; las credenciales owner no se inyectan al servicio backend. Ningún seed SQL incorpora contraseñas.

## 3. Base de datos

### 3.1 Catálogo y contexto

- `entidad_federativa` y `municipio`: catálogo territorial reproducible de 32 entidades y 2,478 municipios/alcaldías activos, con claves naturales INEGI.
- `proyecto`: proyecto administrativo.
- `catalogo_operativo` y `catalogo_operativo_alias`: opciones administrables, códigos estables, etiquetas editables, aliases, vigencia y baja lógica. Incluyen tenencia, residencia, gestión, COP operativo, destino, estructura/estado ORV, asamblea, RAN, FIFONAFE y checklist documental.
- `nucleo_agrario`: núcleo con municipio, tipo de tenencia catalogado, comunidad indígena trivalente (`NULL`, sí, no) y geometría `MULTIPOLYGON(4326)` opcional.
- `proyecto_nucleo`: contexto canónico; existe como máximo uno activo por proyecto y núcleo.
- `proyecto_nucleo_referencia`: consecutivo, clave/numero de tramo u otra referencia. Admite varias por tipo y una principal activa por tipo.
- `proyecto_nucleo_responsable`: historial 1:N de nombre, cargo y contacto, sin obligar a que el responsable sea usuario.

### 3.2 Representación, padrón y parcelas

- `persona`, `orv`, `orv_integrante`: personas y órganos históricos del núcleo; órgano, cargo y calidad propietario/suplente se normalizan con catálogo.
- `padron_historial`: cortes históricos de ejidatarios/comuneros con fuente y documento.
- `parcela`, `parcela_titular`: estructura existente utilizada por procesos individuales/parcelarios; geometría opcional `MULTIPOLYGON(4326)`.
- `unidad_agraria`, `unidad_agraria_titular`: identidad estable y generalizada del bien/unidad perteneciente al núcleo agrario (incorporada en 037). Reutiliza `Persona` / `ParcelaTitular` para la titularidad sin duplicar identidades y no debe confundirse con una `Afectacion` (que es el seguimiento administrativo). Se relaciona 1:N opcionalmente con `parcela` si hay geometría explícita o historia parcela.

La falta de geometría de parcela no bloquea una afectación, convenio, trámite o pago.

### 3.3 Hechos administrativos

- `proyecto_nucleo`: contexto administrativo/operativo del seguimiento entre Proyecto y NucleoAgrario. No debe confundirse con la cartografía (`TrazoProyecto`) que no ejerce autoridad administrativa. Registra los campos TUC (`afecta_tuc`, `id_motivo_no_afecta_tuc`, `tuc_revision_pendiente`, etc.) y documenta cuando `afecta_tuc = false` sin crear afectaciones ficticias.
- `afectacion_unidad_agraria`: entidad asociativa N:M entre `Afectacion` y `UnidadAgraria`. Una misma UnidadAgraria puede participar en múltiples afectaciones sin duplicarse.
- `convenio_compareciente`: instantánea auditable de quien compareció o firmó cada convenio individual, incluida su acreditación; no sustituye la titularidad histórica de `parcela_titular`.

- `actividad_campo`: sensibilización o caminamiento de `ProyectoNucleo`, con contexto, programación y realización; puede relacionarse opcionalmente con una `Afectacion` del mismo ProyectoNucleo para seguimiento individual.
- `afectacion`: participación de una o más unidades agrarias dentro del seguimiento de un `ProyectoNucleo`. El ámbito (colectivo/individual) se define por `tipo_afectacion`, el cual es distinto a `tipo_gestion`. Conserva los atributos operativos `id_tipo_cop_operativo`, `tipo_cop_revision_pendiente` y `tipo_cop_revision_detalle` como propios, no de la unidad agraria.
- `bien_afectado`: unidades 1:N (COMPATIBILIDAD LEGACY / TRANSICIÓN). No es la nueva fuente canónica. La migración 037 incorpora vínculos y proyección automática hacia `unidad_agraria` y `afectacion_unidad_agraria` para lograr una migración gradual, pero la fuente canónica futura es `UnidadAgraria` y sus relaciones.
- `asamblea`: hecho colectivo de `ProyectoNucleo`; separa tipo jurídico y contexto mediante catálogos, puede autorizar varios convenios y referenciar un padrón del mismo núcleo.
- `asamblea_convocatoria`: intentos 1:N, ordinales y resultados explícitos; permite celebrada, no verificativo, cancelada y reprogramada, con documento. Los campos legacy de convocatoria en `asamblea` (`fecha_expedicion_primera`, `fecha_programada_primera`, `fecha_expedicion_segunda`, `fecha_programada_segunda`, `fecha_realizada`) y los campos legacy RAN (`fecha_programada_ingreso_ran`, `fecha_ingreso_ran`, `numero_solicitud_ran`, `calificacion_registral_ran`, `fecha_inscripcion_ran`) son READ-ONLY desde 038; los triggers de la migración 038 bloquean escritura directa. La fuente canónica de convocatorias es `asamblea_convocatoria` y la fuente canónica RAN es `tramite_ran` + `tramite_ran_evento`.
- `convenio`: instrumento repetible; se asocia a afectaciones exclusivamente por `convenio_afectacion`. Los campos RAN legacy (`fecha_programada_ingreso_ran`, `ingreso_ran_fecha`, `numero_solicitud_ingreso`, `calificacion_registral`, `fecha_inscripcion_ran`) son READ-ONLY desde 038. Crear un convenio NO genera automáticamente un `TramiteRan`. La fuente canónica RAN es `tramite_ran` + `tramite_ran_evento`.
- `tramite_ran` y `tramite_ran_evento`: expediente registral tipado con FK fuerte a una asamblea, convenio u ORV y secuencia 1:N de ingresos, reingresos, prevenciones, correcciones, desistimientos, calificaciones e inscripciones. Desde 038, la cardinalidad es **1:N por objetivo** (ya no existe restricción 1:1). El contexto se bifurca: para Asamblea y Convenio, `id_proyecto_nucleo` NOT NULL e `id_nucleo` NULL; para ORV, `id_nucleo` NOT NULL e `id_proyecto_nucleo` NULL. El constraint `chk_tramite_ran_contexto_038` garantiza la integridad.
- `tramite_fifonafe` y `tramite_fifonafe_evento`: trámite y correspondencia repetible; su cobertura N:M permanece en `tramite_fifonafe_afectacion`. Los ocho campos legacy de oficios son READ-ONLY desde 038; la fuente canónica es `tramite_fifonafe_evento`. El estatus `completo` requiere los cuatro eventos canónicos con `numero_oficio` y `fecha_oficio` no vacíos, validados por constraint trigger diferido `ctr_038_fifonafe_completo_*`.
- `indemnizacion`: máximo una activa por afectación; registra la entrega del expediente SICT–PA.
- `pago`: uno o varios pagos por indemnización.

Los triggers diferidos validan que las asociaciones N:M mantengan `ProyectoNucleo` y ámbito, que exista como máximo un vínculo principal activo por convenio y que un convenio confirmado no quede sin afectación. Las operaciones normales crean convenio más vínculo principal y FIFONAFE más coberturas en una transacción.

### 3.4 Documentos, trazabilidad y auditoría

- `documento`: identidad lógica del documento con fecha propia y número de oficio/folio.
- `documento_version`: versión inmutable con SHA-256, tamaño, MIME, ruta y usuario de carga.
- `documento_vinculo`: vínculo controlado a un tipo de entidad permitido; un trigger comprueba la existencia del objetivo.
- `requisito_documental` y `expediente_requisito`: checklist administrable e histórico; el documento disponible se vincula sin sustituir el estado del requisito.
- `importacion_tabular` e `importacion_tabular_celda`: archivo Excel, SHA-256, hoja/fila/columna, valor original/normalizado, tratamiento y mensajes. Se mantienen separados de `importacion_feature`, que continúa siendo exclusivamente GIS.
- `trazabilidad_fuente`: vínculo del dato importado con su registro tabular, valor normalizado y mensajes.
- `bitacora`: cambios con actor y contexto de proyecto/núcleo.

Las tablas funcionales usan baja lógica (`activo`, fecha, usuario y motivo de baja), auditoría de creación/actualización y triggers que impiden `DELETE` físico.

### 3.5 GIS e importación

- `trazo_proyecto`: versiones de `MULTILINESTRING(4326)` por proyecto, fuente y vigencia.
- `importacion_archivo`: cabecera idempotente por proyecto/objetivo/SHA-256, CRS, mapeo, estado, métricas, confirmación y reporte.
- `importacion_feature`: staging por feature, geometría normalizada, errores, advertencias y registro destino.
- `perfil_mapeo_importacion` y `catalogo_alias_territorial`: configuración reutilizable y resolución territorial aprobada.

Los únicos objetivos de confirmación son `trazo_proyecto`, `nucleo_agrario` y `parcela`. El importador normaliza a SRID 4326 y exige confirmación explícita. Los cálculos espaciales son diagnósticos; `ST_Intersects` no autoriza hechos y `ST_Area` no produce superficies ni KPI oficiales.

### 3.6 Vistas objetivo

- `vw_orv_estado`: vigencia derivada del ORV.
- `vw_proyecto_nucleo_resumen`: jerarquía territorial y conteos del expediente.
- `vw_dashboard_kpi`: hechos agregados por proyecto, año e indicador.
- `vw_convenio_tipo_cop_operativo`: proyección de convenio jurídico + consecutivo a ORIGEN, ADICIONAL, 2A ADICIONAL y futuras secuencias, sin inventar tipos jurídicos.

El dashboard agrega cada familia antes de combinarla. Convenios, coberturas FIFONAFE y pagos N:M no se unen en un producto cartesiano. Las superficies provienen de campos administrativos capturados.

## 4. Backend

La aplicación monta seis routers activos:

| Módulo | Responsabilidad |
|---|---|
| `routers/authentication.py` | login, logout, recuperación y sesiones |
| `routers/users.py` | usuarios, roles, baja/reactivación y asignaciones de proyecto |
| `routers/domain.py` | proyectos, núcleos, actividades, parcelas, afectaciones, asambleas, convenios, FIFONAFE, indemnizaciones y pagos |
| `routers/documents.py` | documentos, versiones, vínculos y descarga autorizada |
| `routers/geospatial_imports.py` | carga, staging, previsualización y confirmación GIS |
| `routers/reporting.py` | KPI, CSV y capas de mapa por proyecto |

`models.py` representa todas las tablas/vistas objetivo y no define clases del dominio retirado. `schemas.py` no acepta IDs de tramo/ciclo ni IDs de proyecto redundantes cuando el contexto se deriva de la ruta o del recurso. Los servicios críticos resuelven el proyecto desde relaciones canónicas, aplican autorización antes de paginar/exportar/agregar y usan transacciones atómicas.

## 5. Seguridad y RBAC

`usuario_proyecto` reemplaza el alcance por tramo:

| Rol | Alcance efectivo |
|---|---|
| `admin` | acceso global y administración |
| `operador` | lectura y captura en proyectos asignados |
| `visualizador` | sólo lectura en proyectos asignados |
| `geografo` | lectura e importación/mapa en proyectos asignados; sin captura financiera |

`require_project_access` y sus variantes de lectura/escritura/GIS derivan el proyecto desde el recurso. Listados, exportaciones, documentos y dashboard se filtran antes de consultar o agregar datos.

PostgreSQL separa identidades técnicas: el owner `pa_app` ejecuta bootstrap y migraciones; `software_pa_app` es `NOLOGIN` y contiene sólo el contrato DML; `pa_runtime` es el LOGIN de FastAPI y hereda únicamente ese rol. Runtime no posee `public` ni tablas, no tiene atributos administrativos, no puede crear en `public` y carece de `DELETE`, `TRUNCATE` y DDL. La migración 034 instala ACL actuales y default privileges para el owner real de migraciones; la contraseña runtime se provisiona fuera del SQL versionado.

Las rutas de API relevantes al seguimiento agrario exigen que las entidades consultadas operen bajo un `ProyectoNucleo` autorizado para el usuario. Para 037, se expusieron los endpoints (usando prefijo `/api`):
- `POST /api/nucleos/{nucleo_id}/unidades-agrarias` y `GET /api/nucleos/{nucleo_id}/unidades-agrarias` (identidad de los bienes por núcleo).
- `PATCH /api/unidades-agrarias/{unidad_id}`.
- `POST /api/afectaciones/{afectacion_id}/unidades-agrarias` y `GET /api/afectaciones/{afectacion_id}/unidades-agrarias` (relación N:M).

Para 038, se expusieron los endpoints de TramiteRan canónico:
- `POST /api/tramites-ran`: creación de trámite RAN con objetivo tipado en el payload (`id_asamblea`, `id_convenio` o `id_orv`). El contexto (`id_proyecto_nucleo` o `id_nucleo`) se deriva del objetivo; el cliente no elige un ProyectoNucleo arbitrario para ORV.
- `GET /api/tramites-ran/{id_tramite_ran}`: detalle de un trámite RAN.
- `GET /api/asambleas/{id_asamblea}/tramites-ran`: trámites RAN 1:N de una asamblea.
- `GET /api/convenios/{id_convenio}/tramites-ran`: trámites RAN 1:N de un convenio.
- `GET /api/orv/{id_orv}/tramites-ran`: trámites RAN 1:N de un ORV.
- `GET /api/proyecto-nucleo/{id}/tramites-ran`: trámites RAN del ProyectoNucleo (mantiene compatibilidad).
- `GET /api/tramites-ran/{id_tramite_ran}/eventos`: eventos de un trámite RAN.
- `POST /api/tramites-ran/{id_tramite_ran}/eventos`: agregar evento a un trámite RAN.
- `PATCH /api/eventos-ran/{id_evento_ran}`: actualizar evento RAN.

Para 039, se incorporaron los endpoints del modelo operativo individual y expediente por objetivo:
- `POST /api/convenios/{id_convenio}/comparecientes` y `GET /api/convenios/{id_convenio}/comparecientes`: gestión de comparecientes y firmantes por convenio.
- `PATCH /api/convenio-comparecientes/{id_compareciente}` y `DELETE /api/convenio-comparecientes/{id_compareciente}`: actualización y baja lógica de comparecientes.
- `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/unidades-agrarias`: creación directa de unidad agraria dentro del contexto ProyectoNucleo.
- `POST /api/unidades-agrarias/{id_unidad_agraria}/titulares` y `GET /api/unidades-agrarias/{id_unidad_agraria}/titulares`: vinculación de titularidades a la unidad agraria.
- `PATCH /api/unidad-agraria-titulares/{id_unidad_titular}` y `DELETE /api/unidad-agraria-titulares/{id_unidad_titular}`: actualización y baja lógica de titularidades de unidad.
- `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/requisitos-documentales` con `entidad_tipo` y `entidad_id`: checklist documental por objetivo concreto dentro del ProyectoNucleo.
- `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/actividades` con `id_afectacion` opcional: actividades de campo general o contextualizadas a una afectación.

La autorización RAN se resuelve mediante `require_ran_procedure_access`, que bifurca según el objetivo del trámite: para Asamblea y Convenio, verifica acceso al `ProyectoNucleo` correspondiente; para ORV, verifica acceso al `NucleoAgrario` del ORV mediante `require_nucleus_access` (que verifica que el usuario tenga al menos un proyecto activo sobre ese núcleo, o sea admin).

Estos endpoints utilizan dependencias `Depends(auth.RoleChecker(READ_ROLES))` para lectura y `CAPTURE_ROLES` para escritura, aplicando `require_nucleus_access` o `require_affectation_access` y preservando obligatoriamente el contexto de auditoría `app.current_user_id`.

## 6. Frontend

La navegación administrativa implementada es `Proyecto -> Entidad -> Municipio -> Núcleo`. El detalle de `ProyectoNucleo` contiene resumen, datos generales, ORV, padrón, sensibilización, caminamiento, derechos colectivos y parcelas/derechos individuales.

Los flujos principales son:

- colectivo: afectación, asamblea independiente, RAN del acta, convenios, RAN del convenio, FIFONAFE, indemnización, pagos y documentos;
- individual: parcela y titulares, afectación, convenios, FIFONAFE, indemnización, pagos y soporte, incluso sin geometría;
- convenio: creación sencilla desde una afectación y acción secundaria para asociar otra del mismo contexto y ámbito;
- mapa: trazo de proyecto, núcleos y parcelas con geometría;
- administración: usuarios, roles y proyectos asignados;
- dashboard: KPI derivados con filtros por proyecto/año según alcance.

## 7. Migraciones, fixture y seed

- `031_reset_dominio_proyecto_nucleo.sql`: reset protegido y creación del dominio administrativo objetivo.
- `032_cleanup_legacy_gis_importacion.sql`: trazo por proyecto, importador consolidado y retiro de GIS legacy.
- `033_dashboard_modelo_objetivo.sql`: vistas objetivo y KPI.
- `034_separacion_usuario_runtime_postgresql.sql`: separación owner/runtime, cierre de PUBLIC y default privileges no destructivos.
- `035_completitud_seguimiento_operativo.sql`: tipo/contexto de Asamblea y metadatos operativos/documentales confirmados por Excel.
- `036_modelo_operativo_excel_colectivo.sql`: catálogos administrables, datos generales normalizados, bienes, convocatorias, RAN/FIFONAFE repetibles, checklist y trazabilidad tabular.
- `037_normalizacion_unidad_agraria.sql`: normalización de unidad agraria, relación N:M `AfectacionUnidadAgraria`, alcance TUC y proyección de `BienAfectado`.
- `038_cierre_legacy_asamblea_ran_fifonafe.sql`: cierre de escrituras legacy de Asamblea/RAN/FIFONAFE, TramiteRan 1:N con contextualización por objetivo (Asamblea/Convenio vía `id_proyecto_nucleo`, ORV vía `id_nucleo`), triggers read-only para campos legacy y validación diferida de completitud FIFONAFE.
- `039_modelo_operativo_individual_expediente.sql`: modelo operativo individual completo: actividades contextualizadas por afectación, reconciliación y retiro de `no_parcela_ppt` en favor del canónico `no_parcela`, linaje y comparecientes de convenio individual (validación diferida de `UnidadAgraria` compartida), y expediente documental por objetivo (`entidad_tipo`/`entidad_id`).

031 y 032 adquieren advisory lock y abortan antes del DDL si faltan entorno autorizado, confirmación destructiva o respaldo verificado. Las migraciones 001-030 permanecen intactas.

El fixture territorial está separado del seed demo, ordenado de forma determinista y validado por conteo, unicidad y checksum. El seed objetivo es pequeño, idempotente, marca los casos sintéticos como QA y conserva trazabilidad de los casos derivados de Excel. Las geometrías demo son sintéticas y no se presentan como cartografía RAN.

## 8. Contratos de alineación

La implementación se valida mediante:

- construcción limpia contractual `001` (línea base consolidada que ya incorpora 002/003) `-> fixture territorial -> 004...035 -> 036 -> 037 -> 038 -> 039`, y actualización incremental `038 -> 039`;
- migración desde un respaldo equivalente a 030;
- pruebas de rollback inducido de los gates 031/032;
- contrato SQL de tablas, constraints, triggers, ausencia legacy, catálogo y KPI del seed;
- contrato SQL 038 de cierre legacy y completitud FIFONAFE;
- contrato SQL 039 de modelo individual, comparecientes y expediente documental por objetivo;
- configuración completa de mappers SQLAlchemy y OpenAPI;
- pytest de dominio, auth, RBAC, documentos, GIS, dashboard y exportación;
- lint/build de frontend y Playwright de los flujos objetivo.

La documentación histórica bajo `docs/historico/` no describe la arquitectura vigente.

## 9. Deuda técnica y compatibilidad

No se declaran resueltos todavía:
- Importador Excel individual completo (automatización masiva / importador tabular individual).
- Mejoras posteriores que pertenezcan a 040.
(Estas transiciones pertenecen a fases posteriores a la 039).
