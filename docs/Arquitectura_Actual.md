# Arquitectura actual de SOFTWARE-PA

> Rama verificada: `feature/backend-logica`
> Esquema vigente: migraciones `001` a `035`
> Última validación: 2026-08-25
> Fuente de verdad: SQL aplicado, modelos SQLAlchemy, contratos Pydantic, API, frontend y pruebas del repositorio.

## 1. Estado implementado

SOFTWARE-PA administra el seguimiento de liberación de derecho de vía ferroviario sobre propiedad social. El contexto funcional es `ProyectoNucleo`, relación entre un proyecto y un núcleo agrario. Las referencias históricas se conservan como datos, no como expedientes.

El dominio vigente eliminó del código activo y del esquema objetivo la navegación y autorización por tramo, los ciclos artificiales de afectación y los gates administrativos espaciales. PostGIS se conserva para mapa, importación y validación técnica.

```text
Proyecto
├── UsuarioProyecto (alcance RBAC)
├── TrazoProyecto (MULTILINESTRING 4326)
└── ProyectoNucleo
    ├── Referencias históricas
    ├── Actividades de campo
    ├── Asambleas colectivas
    ├── Afectaciones colectivas
    ├── Parcelas del núcleo -> Afectaciones individuales
    ├── Convenios <-> Afectaciones
    └── FIFONAFE <-> Afectaciones
                         └── Indemnización -> Pagos
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
- `nucleo_agrario`: núcleo con municipio, tipo ejido/comunidad y geometría `MULTIPOLYGON(4326)` opcional.
- `proyecto_nucleo`: contexto canónico; existe como máximo uno activo por proyecto y núcleo.
- `proyecto_nucleo_referencia`: consecutivo, clave/numero de tramo u otra referencia. Admite varias por tipo y una principal activa por tipo.

### 3.2 Representación, padrón y parcelas

- `persona`, `orv`, `orv_integrante`: personas y órganos de representación del núcleo.
- `padron_historial`: cortes históricos de ejidatarios/comuneros.
- `parcela`, `parcela_titular`: unidad individual, titulares y geometría opcional `MULTIPOLYGON(4326)`.

La falta de geometría de parcela no bloquea una afectación, convenio, trámite o pago.

### 3.3 Hechos administrativos

- `actividad_campo`: sensibilización o caminamiento de `ProyectoNucleo`, con contexto, programación y realización.
- `afectacion`: colectiva sin parcela o individual con parcela del mismo núcleo.
- `asamblea`: hecho colectivo de `ProyectoNucleo`; separa el tipo jurídico de su `contexto_proceso`, puede autorizar varios convenios y no depende de una afectación.
- `convenio`: instrumento repetible; se asocia a afectaciones exclusivamente por `convenio_afectacion`.
- `tramite_fifonafe`: trámite colectivo o individual de `ProyectoNucleo`, con fecha de acuse y sus cuatro pares oficio/fecha; su cobertura se expresa en `tramite_fifonafe_afectacion`.
- `indemnizacion`: máximo una activa por afectación; registra la entrega del expediente SICT–PA.
- `pago`: uno o varios pagos por indemnización.

Los triggers diferidos validan que las asociaciones N:M mantengan `ProyectoNucleo` y ámbito, que exista como máximo un vínculo principal activo por convenio y que un convenio confirmado no quede sin afectación. Las operaciones normales crean convenio más vínculo principal y FIFONAFE más coberturas en una transacción.

### 3.4 Documentos, trazabilidad y auditoría

- `documento`: identidad lógica del documento con fecha propia y número de oficio/folio.
- `documento_version`: versión inmutable con SHA-256, tamaño, MIME, ruta y usuario de carga.
- `documento_vinculo`: vínculo controlado a un tipo de entidad permitido; un trigger comprueba la existencia del objetivo.
- `trazabilidad_fuente`: archivo, hoja, celda, valor original y tratamiento de la fuente.
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

031 y 032 adquieren advisory lock y abortan antes del DDL si faltan entorno autorizado, confirmación destructiva o respaldo verificado. Las migraciones 001-030 permanecen intactas.

El fixture territorial está separado del seed demo, ordenado de forma determinista y validado por conteo, unicidad y checksum. El seed objetivo es pequeño, idempotente, marca los casos sintéticos como QA y conserva trazabilidad de los casos derivados de Excel. Las geometrías demo son sintéticas y no se presentan como cartografía RAN.

## 8. Contratos de alineación

La implementación se valida mediante:

- construcción limpia real `001 -> 004...030 -> 031 -> 032 -> 033 -> 034 -> 035`;
- migración desde un respaldo equivalente a 030;
- pruebas de rollback inducido de los gates 031/032;
- contrato SQL de tablas, constraints, triggers, ausencia legacy, catálogo y KPI del seed;
- configuración completa de mappers SQLAlchemy y OpenAPI;
- pytest de dominio, auth, RBAC, documentos, GIS, dashboard y exportación;
- lint/build de frontend y Playwright de los flujos objetivo.

La documentación histórica bajo `docs/historico/` no describe la arquitectura vigente.
