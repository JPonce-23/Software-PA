# Arquitectura del Sistema — SOFTWARE-PA

> **Autoridad:** Documento canónico de arquitectura técnica de SOFTWARE-PA.  
> **Propósito:** Describe la estructura, tecnologías, patrones de diseño y subsistemas que componen la implementación real y ejecutable del proyecto hoy.

---

## 1. Visión General y Stack Tecnológico

SOFTWARE-PA está implementado como una aplicación web modular desacoplada, orientada a servicios y respaldada por una base de datos relacional con capacidades espaciales:

```text
┌────────────────────────────────────────────────────────┐
│                   Cliente Web (Frontend)                │
│       React 19 + Vite + React Router 7 + Leaflet       │
└───────────────────────────┬────────────────────────────┘
                            │ HTTPS / HTTP (REST API JSON)
                            │ Cookies HttpOnly + X-CSRF-Token
┌───────────────────────────▼────────────────────────────┐
│                  Servidor de API (Backend)             │
│            FastAPI + SQLAlchemy 2.0 + Pydantic v2      │
│  - Autenticación por Sesión y RBAC                     │
│  - Autorización por Proyecto (UsuarioProyecto)         │
│  - Servicios Transaccionales de Dominio                │
│  - Pipeline Geoespacial y Vistas de Reporting          │
└───────────────────────────┬────────────────────────────┘
                            │ PostgreSQL Wire Protocol
┌───────────────────────────▼────────────────────────────┐
│                 Base de Datos Persistente              │
│               PostgreSQL 15 + PostGIS 3.3              │
│  - Schema Canónico (Migraciones 001–028)               │
│  - Constraints de Dominio y Triggers de Integridad     │
│  - Bitácora Append-Only (SECURITY DEFINER)             │
│  - Read-Models mediante Vistas SQL                    │
└────────────────────────────────────────────────────────┘
```

### 1.1 Tecnologías principales

- **Backend:**
  - **Framework:** FastAPI con Python 3.11+.
  - **ORM:** SQLAlchemy 2.0 con soporte relacional y geoespacial (`GeoAlchemy2`).
  - **Validación y Contratos:** Pydantic v2.
  - **Seguridad Criptográfica:** Bcrypt para hashes de contraseña y `secrets` para tokens de sesión opacos.
- **Base de datos:**
  - **Motor:** PostgreSQL 15.
  - **Extensión Espacial:** PostGIS 3.3.
  - **Versionado de Esquema:** Motor de migraciones SQL secuenciales y verificadas por SHA-256 (`backend/scripts/run_migrations.sh`). Linaje canónico vigente: **001–028**.
- **Frontend:**
  - **Librería de Interfaz:** React 19.
  - **Herramienta de Construcción:** Vite.
  - **Enrutamiento:** React Router DOM v7.
  - **Cliente HTTP:** Axios configurado con `withCredentials: true`.
  - **Componentes Cartográficos:** Leaflet y React-Leaflet con utilerías WKT (`wellknown`).
  - **Iconografía:** Lucide React.
- **Entorno e Infraestructura:**
  - Orquestación local mediante Docker Compose con cuatro servicios base: `db`, `backend`, `frontend` y `pgadmin`. No hay un servicio `alertas_scheduler` en la configuración vigente.

---

## 2. Separación Estricta Backend / Frontend

1. **Desacoplamiento total:**  
   El frontend interactúa con el sistema **exclusivamente a través de la API REST HTTP JSON** expuesta por FastAPI bajo el prefijo `/api`.
2. **Prohibición de acceso directo a la base de datos:**  
   El cliente web no se conecta de forma directa a PostgreSQL ni asume la estructura interna de tablas físicas, índices o funciones almacenadas. Su contrato de integración formal es la especificación OpenAPI (`docs/openapi.json`).
3. **No filtrado en cliente de datos no autorizados:**  
   El backend es la única autoridad responsable de filtrar, restringir y aislar la información por proyecto y por rol antes de devolver las respuestas al navegador.

---

## 3. Modelo de Dominio y Organización del Backend

El backend se organiza en capas arquitectónicas bien definidas:

```text
backend/app/
├── main.py             # Configuración FastAPI, middlewares (CORS, CSRF), manejadores de error y montaje de routers
├── config.py           # Configuración de autenticación (AUTH_SETTINGS)
├── database.py         # DATABASE_URL, conexión SQLAlchemy y sesión por petición (SessionLocal)
├── models.py           # Modelos ORM relacionales y geoespaciales con AuditableMixin
├── schemas.py          # Schemas Pydantic de entrada, salida y validación de tipos
├── auth.py             # Dependencias de seguridad (get_current_user, RoleChecker)
├── routers/            # Controladores HTTP por módulo funcional
│   ├── authentication.py
│   ├── users.py
│   ├── audit.py
│   ├── domain.py
│   ├── documents.py
│   ├── geospatial_imports.py
│   └── reporting.py
└── services/           # Lógica transaccional de negocio
    ├── authentication.py
    ├── access.py
    └── domain.py
```

### 3.1 Relaciones Fundamentales de Dominio

El centro del dominio articula el seguimiento administrativo en torno a `ProyectoNucleo`:

1. `Proyecto` (1:N) → `ProyectoNucleo` (N:1) ← `NucleoAgrario`.
2. `ProyectoNucleo` contiene:
   - `ProyectoNucleoResponsable` (responsables institucionales con vigencia).
   - `ProyectoNucleoReferencia` (consecutivos y claves históricas de tramo).
   - Acceso a `PadronHistorial` y `Orv` por el núcleo; estos registros pertenecen a `NucleoAgrario`, no directamente a `ProyectoNucleo`.
   - `ActividadCampo` (sensibilizaciones y caminamientos con tipo de COP operativo).
3. **Ruta Colectiva:**
   - `Asamblea` (1:N) → `AsambleaConvocatoria` (primera, segunda, ulterior).
   - `Asamblea` (1:N) → `TramiteRan` (trámites del acta de asamblea).
   - `Afectacion` (ámbito colectivo) vinculada a `ProyectoNucleo`.
   - `Convenio` colectivo (autorizado opcionalmente por `Asamblea`, con trámites `TramiteRan`).
   - `ConvenioAfectacion` (relación N:M que asocia convenios y afectaciones sin duplicar montos).
4. **Ruta Individual:**
   - `Parcela` (único `no_parcela`) asociada al `NucleoAgrario`.
   - `ParcelaTitular` (titulares verificables con certificados y vigencias).
   - `Afectacion` individual vinculada a `ProyectoNucleo`; la parcela se obtiene mediante `AfectacionUnidadAgraria → UnidadAgraria → Parcela`, sin FK directa en Afectacion.
   - `Convenio` individual (con trámites `TramiteRan`).
5. **Cadena Financiera:**
   - `Afectacion` (1:1 activa) → `Indemnizacion` (1:N) → `Pago`.
6. **Desglose Físico por Destino:**
   - `UnidadAgraria` (asociada a parcela o núcleo con `id_destino_superficie`).
   - `AfectacionUnidadAgraria` (relación que fija la `superficie_afectada_ha` exacta por destino).

---

## 4. Seguridad, Autenticación y Control de Acceso

### 4.1 Autenticación Basada en Cookies Seguras

El sistema rechaza el uso de tokens Bearer/JWT en almacenamiento local de navegador (`localStorage`) por vulnerabilidad a ataques XSS. Emplea un esquema robusto de sesiones opacas en base de datos:

- **Inicio de sesión (`POST /api/auth/sesiones`):**  
  Valida credenciales contra `usuario` y `estado_autenticacion_usuario`. Ante éxito, genera un token criptográfico aleatorio, persiste el registro en `sesion_usuario` y emite dos cookies HTTP:
  - Cookie de sesión: `pa_session_dev` (desarrollo) o `__Host-pa_session` (producción), con atributos `HttpOnly`, `SameSite=Lax` y `Secure` en producción.
  - Cookie CSRF: `pa_csrf_dev` o `__Host-pa_csrf`, accesible por JavaScript para ser enviada en la cabecera `X-CSRF-Token`.
- **Protección CSRF:**  
  Middleware que controla peticiones mutables bajo `/api/`: el login exige `Origin` permitido; las demás peticiones con cookie de sesión validan origen, cookie y encabezado `X-CSRF-Token` contra la sesión. Sin cookie, la dependencia de autenticación conserva el rechazo por falta de sesión.
- **Políticas de credenciales:**  
  Mínimo 8 caracteres, al menos una letra y un número, longitud máxima estricta de 72 bytes UTF-8 (compatibilidad bcrypt). Bloqueo temporal automático tras intentos fallidos consecutivos.

### 4.2 Control de Acceso Basado en Roles (RBAC)

Existen cuatro roles de sistema predefinidos:

| Rol | Permisos y Alcance Operativo |
|---|---|
| `admin` | Acceso global irrestricto; administración de usuarios, asignación de proyectos, auditoría y catálogos. |
| `operador` | Captura y edición documental, operativa y financiera en proyectos asignados. |
| `visualizador` | Consulta y lectura de expedientes, reportes y dashboards en proyectos asignados. |
| `geografo` | Gestión de capas espaciales, cargas GeoJSON y edición cartográfica en proyectos asignados. |

### 4.3 Autorización por Proyecto (`UsuarioProyecto`)

La autorización de los usuarios no administradores se rige exclusivamente a nivel **Proyecto**:
- La tabla `usuario_proyecto` vincula al usuario con los proyectos autorizados.
- La función de seguridad `enforce_project_access` en `backend/app/services/access.py` verifica en cada petición que el recurso solicitado pertenezca a un proyecto activo asignado al usuario.
- **Confirmación técnica:** El mecanismo histórico `usuario_tramo` fue retirado por completo del código y de la base de datos. No existe restricción por tramos.

---

## 5. Auditoría e Integridad de Datos

### 5.1 Trazabilidad Estándar (`AuditableMixin`)

Todas las entidades de dominio heredan las columnas estándar de auditoría:
- `activo`: Bandera booleana para bajas lógicas. La eliminación física (`DELETE`) está deshabilitada en tablas de dominio.
- `creado_en`, `creado_por`: Marca temporal y usuario creador.
- `actualizado_en`, `actualizado_por`: Registro de la última mutación.
- `fecha_baja`, `id_usuario_baja`, `motivo_baja`: Metadatos obligatorios para efectuar una baja lógica.
- `observaciones`: Campo de texto libre para notas aclaratorias.

### 5.2 Bitácora Append-Only y Eventos de Acceso

- **Bitácora de mutaciones (`bitacora`):**  
  Almacena el historial cronológico de cambios mediante el trigger `fn_audit_log` con `SECURITY DEFINER`. Desde 009, `software_pa_app` sólo tiene SELECT sobre `bitacora`: la inserción corresponde al trigger; INSERT, UPDATE, DELETE y TRUNCATE directos están revocados.
- **Eventos de acceso (`evento_acceso`):**  
  Registro inmutable de eventos de autenticación (inicios de sesión exitosos, fallidos, bloqueos y cierres de sesión).

---

## 6. Subsistema Documental y Expedientes

El subsistema gestiona la evidencia jurídica que respalda cada actuación:
- **`Documento`:** Identidad lógica del documento (tipo, estado, fecha propia del instrumento y número de folio u oficio).
- **`DocumentoVersion`:** Archivos físicos almacenados en disco/volumen con su respectivo hash criptográfico SHA-256 inmutable.
- **`DocumentoVinculo`:** Relaciona un documento con una o más entidades del dominio. La API comprueba acceso al documento y al objetivo por separado; no impone una prohibición general de compartir documentos entre proyectos autorizados. El listado consolidado sólo publica procedencias dentro del alcance consultado.
- **`ExpedienteRequisito`:** Seguimiento del checklist documental por objetivo, admitiendo estados `disponible`, `parcial`, `pendiente_validacion`, `faltante` y `no_aplica`.

---

## 7. Seguimiento Funcional y Máquina de Hechos

Para gestionar la no linealidad del proceso agrario sin mutar destructivamente los expedientes:
- **`SeguimientoEvento`:** Historia funcional asociada a `ProyectoNucleo` y opcionalmente a un objetivo tipado. La API permite alta, edición y baja lógica; la bitácora de esas mutaciones sí es append-only.
- **Catálogos asociados:**
  - `tipo_evento_seguimiento`: `inicio`, `suspension`, `reapertura`, `cierre`, `cambio_alcance`, `reunion`, `negociacion`, `consulta_indigena`, `continuacion_asamblea`, `medicion_bdt`, `otro`.
  - `motivo_seguimiento`: `expropiacion_directa`, `no_afectacion`, `comunidad_indigena`, `dominio_pleno`, `juicio_agrario`, `conflicto_titularidad`, `rechazo`, `cambio_trazo`, `nueva_informacion`, `calificacion_negativa`, `falta_pago`, `otro`.
- **Vista `vw_seguimiento_estado_actual`:** Read-model que computa el estado vigente (`activo`, `suspendido`, `cerrado`) basándose en el evento fechado más reciente.

---

## 8. Arquitectura de Reporting y Read-Models

El reporting implementa un desacoplamiento estricto entre escritura transaccional y lectura gerencial para evitar duplicidades por relaciones N:M:

```text
Tablas Transaccionales
(Afectacion, Asamblea, Convenio, TramiteRan, TramiteFifonafe, Indemnizacion, Pago)
         │
         ▼
[Capa 1] vw_hito_seguimiento
(Consolida cada hito operativo único por clave_hito, con fechas canónicas y montos)
         │
         ├───────────────────────────────────────────┐
         ▼                                           ▼
[Capa 2A] vw_reporte_avance_periodo        [Capa 2B] vw_dashboard_kpi
(15 columnas por periodo: mes/trimestre)   (Agregado anual deduplicado por proyecto)
```

### 8.1 Vistas Principales de Reporting

1. **`vw_hito_seguimiento`:**  
   Normaliza cada evento relevante bajo una clave única `clave_hito` (p. ej. `asamblea:12`, `convenio:45`, `pago:89`). Asigna ámbito, tipo COP, tipo de convenio, destino, cantidad, superficie y montos. Previene que múltiples comparecientes o afectaciones multipliquen un convenio.
2. **`vw_reporte_avance_periodo`:**  
   Proyecta los hitos hacia dimensiones temporales calculadas (año, mes, trimestre), diferenciando avance programado y realizado. Expone las 15 columnas requeridas para conciliación con Excel.
3. **`vw_dashboard_kpi`:**  
   Calcula totales anuales directos sobre hitos deduplicados.
4. **`vw_reporte_snapshot_actual`:**  
   Representa el corte fotográfico del estado presente acumulado (núcleos, parcelas intervenidas, hectáreas, no afecta TUC, comunidad indígena). No admite filtros de año/mes.
5. **`vw_convenio_colectivo_destino`:**  
   Detalle con granularidad `id_convenio + destino_superficie`. Distingue la superficie física real (`superficie_ha`) de la superficie declarada en el instrumento (`superficie_declarada_ha`) y expone el monto acordado (`monto_declarado`) como **atributo NO ADITIVO**.
6. **Integración de pagos reales:**  
   La cadena `Pago → Indemnizacion → Afectacion → ProyectoNucleo → Proyecto` asegura que cada pago efectivo genere un hito propio (`indicador = 'pagos'`) sin distorsionar convenios ni retiros.
7. **Exclusión de proyectos inactivos:**  
   Todos los read-models filtran automáticamente proyectos con `activo IS NOT TRUE`.

---

## 9. Componente Geoespacial y Cartografía

La verdad administrativa sigue en Software-PA. GIS busca geometrías para registros existentes; ninguna feature crea proyectos, vínculos administrativos, núcleos, parcelas, afectaciones o expedientes. `ST_Intersects` no determina pertenencia administrativa. `ST_Area` y las áreas GIS son métricas auxiliares/cartográficas, nunca superficie oficial ni sustitutos de superficies administrativas capturadas.

### Destinos y legado

DDV representa superficie y permanece en `derecho_via_proyecto`, con `MultiPolygon`, versiones históricas y una sola vigente; `activo` y `es_vigente` conservan significados distintos. Un núcleo del proyecto recibe geometría en `proyecto_nucleo_geometria`, ligada al `ProyectoNucleo` existente. Una parcela recibe geometría en `proyecto_parcela_geometria`, ligada a `ProyectoNucleo + Parcela`, sólo si ya existe el vínculo activo por afectación. Estas tablas son complementos cartográficos, no nuevos registros administrativos.

Los campos globales `NucleoAgrario.geometria_poligono` y `Parcela.geometria_poligono` permanecen para compatibilidad; las nuevas importaciones no escriben en ellos. Se mantienen los endpoints directos legacy y el flujo lineal `trazo_proyecto`. Desde la corrección B-07, `/api/proyectos/{id_proyecto}/mapa` publica las geometrías activas y vigentes de núcleo/parcela por `ProyectoNucleo`, con precedencia sobre los campos globales. Estos últimos se usan sólo cuando no existe geometría vigente del proyecto. Las parcelas, incluido el fallback, deben pertenecer a `vw_gis_parcela_proyecto`; compartir núcleo no basta. El DDV activo y vigente se publica como capa poligonal `derecho_via_proyecto`, independiente del trazo lineal legacy activo. Las importaciones poligonales legacy pendientes deben reprocesarse para usar la conciliación por proyecto.

### Staging y conciliación

El código vigente usa `conciliacion-v3-historia` (`gis_history.ALGORITHM`).
`conciliacion-v2` identifica el contrato histórico introducido por 025; 026
incorpora la historia técnica sin cambiar la autoridad administrativa.

`gis_ingestion.py` identifica sólo capas espaciales y mantiene `COORDINATE_PRECISION=15` en GeoJSONSeq. Un GPKG debe tener exactamente una capa espacial de datos; tablas como `layer_styles` son auxiliares. Se conserva WKB original, FID, capa, CRS/WKT, dimensión y atributos autorizados. El archivo cargado se elimina tras staging para evitar retener datos personales innecesarios; su nombre y SHA permanecen como trazabilidad. Los originales locales de los geógrafos no se alteran.

`gis_reconciliation.py` consulta destinos activos del proyecto y propone 0..N filas normalizadas en `importacion_feature_candidato`. Una clave RAN oficial se verifica y nunca crea vínculos. Sin clave se comparan nombre y atributos territoriales disponibles, normalizando Unicode, acentos, caja y espacios; una coincidencia textual requiere revisión. En parcelas se evalúan `PARCELA` y `Num_parcela` por separado y se conserva cada valor. Dos destinos distintos son ambiguos. La normalización parcelaria preserva letras, sufijos, ceros y puntuación, salvo la equivalencia aprobada `P.-<dígitos> → P-<dígitos>`.

Seleccionar un candidato no escribe geometría. Confirmarlo exige `confirmacion_explicita`, aceptación de advertencias y rol `admin` o `geografo` con acceso al proyecto. La transacción bloquea proyecto, importación, feature y relaciones administrativas; revalida identidad, pertenencia y hash de geometría previa. Restricciones únicas impiden seleccionar/confirmar dos features al mismo destino dentro de una importación. La geometría y la decisión append-only se guardan conjuntamente; un fallo revierte toda la decisión. Cada nueva importación puede crear una versión histórica posterior del mismo destino.

La finalización permite features confirmadas, ignoradas, rechazadas y sin coincidencia. Los candidatos/ambiguos pendientes requieren decisión o ignorado explícito; una feature en error requiere ignorado explícito. No se obliga a vincular todo el archivo. El resumen distingue universo administrativo, features, confirmados, ambiguos, registros sin geometría y features no utilizadas.

### CRS y dimensión

`proyecto_configuracion_gis.srid_trabajo` define un CRS registrado y transformable en PostGIS. Sin configuración explícita se usa 4326, conservando compatibilidad; no hay un UTM nacional. Importación y feature conservan el CRS fuente; la importación fija el CRS de trabajo usado. Toda geometría de dominio tiene representación 2D de trabajo y representación 4326 para salida web. Si el origen válido ya utiliza el CRS de trabajo, se conserva directamente su geometría XY nativa, evitando el viaje de ida y vuelta por 4326. Los demás cambios de CRS se transforman explícitamente y se registran.

XYZ/XYM/XYZM se detectan, se conserva la geometría original y se registra la reducción explícita a XY; no se asume Z=0 ni se usa altura para matching. Una geometría inválida en origen puede repararse con `ST_MakeValid`, con motivo y advertencia que exige aceptación. Una geometría válida que se invalida por serialización o transformación produce error, sin reparación que oculte el problema.

No se permite confirmar staging con un CRS de proyecto cambiado. Una vez existen geometrías confirmadas, cambiar ese CRS exige una futura reproyección explícita; el endpoint rechaza el cambio para evitar mezcla accidental. La deduplicación incluye proyecto, objetivo, SHA-256, versión de pipeline y CRS de trabajo, permitiendo reprocesar la misma fuente con una versión/CRS diferente.

### Alcance y API

Se reutilizan creación de importaciones DDV/núcleos/parcelas, preview y finalización. Se agregan configuración GIS, resumen, candidatos, decisiones y GeoJSON 4326 de staging; `features?estado_conciliacion=ambiguo` reutiliza el listado existente. Lectura mantiene `admin/operador/visualizador/geografo`; escritura GIS mantiene `admin/geografo`, sin ampliar permisos. B-07 adapta únicamente la lectura del endpoint `/mapa` existente, sin migración ni escrituras administrativas. El pipeline poligonal no incorpora obras transversales ni un nuevo flujo DDV lineal; el trazo lineal legacy permanece disponible.

El inventario y las pruebas de la etapa previa están en [INFORME_CONCILIACION_GIS_2026-10-05.md](INFORME_CONCILIACION_GIS_2026-10-05.md); su alcance histórico no sustituye el contrato actual de [API.md](API.md).

Referencias GIS renumeradas excepcionalmente desde 020–024 a 021–025; los originales
y la correspondencia se conservan en [MIGRACIONES.md](MIGRACIONES.md). No cambió el
modelo funcional GIS ni administrativo.

### Historia de conciliación y cambios GIS — 026

`gis_reconciliation.py` conserva el matching y la confirmación de 025;
`gis_history.py` añade ciclos, reanálisis del staging y observaciones técnicas. No
hay un segundo importador ni arquitectura de pertenencia por geometría. La
migración 026 depende por SHA de 025, agrega contexto a candidatos/decisiones y
hace backfill determinista sin cambiar su contenido histórico.

Las entregas estrictas tienen alcance explícito y una referencia previa fija. La
aparición puede existir sin destino administrativo; desaparición exige dos
entregas completas comparables, identidad confirmada y conciliación finalizada.
Las versiones confirmadas se conservan; ST_Equals evita falsos cambios por
serialización. No existe tolerancia numérica nueva. Las áreas son diagnósticos
métricos del CRS de trabajo acreditado, nunca escrituras de superficies de dominio.

Cada confirmación y sus observaciones se escriben atómicamente bajo el bloqueo de
proyecto, importación y destino existente. Ciclos y solicitudes usan unicidades
para concurrencia/idempotencia. Revisiones y decisiones son append-only; el estado
se deriva de la última decisión. La API sólo vincula SeguimientoEvento existente
tras validar proyecto/núcleo/entidad, manteniendo el flujo administrativo separado.
El servicio GIS no contiene creación de esos eventos ni de afectaciones.

Lectura: roles existentes con acceso al proyecto. Escritura GIS: admin/geografo.
La autorización se revalida tras adquirir el bloqueo del proyecto. El contrato
OpenAPI incorpora ciclos, revisiones y alcance multipart explícito. B-07 conserva
el contrato GeoJSON de /mapa y conecta su lectura con las geometrías del proyecto.
Se conservan frontend, RAN y lógica de seguimiento; geometry_columns y obras transversales
GIS permanecen fuera del alcance.

### Proyecciones de lectura posteriores a 028

[API.md §11](API.md#11-proyecciones-de-lectura-para-el-frontend-esquema-028)
describe nombres opcionales de actores GIS, `destino` legible en revisiones,
documentos consolidados por ProyectoNucleo y `X-Total-Count` en los cuatro
listados GIS paginados indicados allí, expuesto por CORS. Son consultas sobre
entidades existentes, sin persistencia ni reglas nuevas. Los candidatos reutilizan
las etiquetas del snapshot `universo_destinos`; no se duplican por fila.
Usuario y Responsable operativo permanecen separados. `Proyecto.activo`
representa baja lógica; no existe un ciclo de proyecto activo/completado/reabierto.
