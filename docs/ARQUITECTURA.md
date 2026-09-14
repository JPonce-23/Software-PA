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
│  - Schema Canónico (Migraciones 001–015)               │
│  - Constraints de Dominio y Triggers de Integridad     │
│  - Bitácora Append-Only (SECURITY DEFINER)             │
│  - Read-Models Materializados en Vistas SQL            │
└────────────────────────────────────────────────────────┘
```

### 1.1 Tecnologías principales

- **Backend:**
  - **Framework:** FastAPI con Python 3.11+.
  - **ORM:** SQLAlchemy 2.0 con soporte relacional y geoespacial (`GeoAlchemy2`).
  - **Validación y Contratos:** Pydantic v2.
  - **Seguridad Criptográfica:** Passlib / Bcrypt para almacenamiento de hashes de contraseña y generación segura de tokens de sesión opacos.
- **Base de datos:**
  - **Motor:** PostgreSQL 15.
  - **Extensión Espacial:** PostGIS 3.3.
  - **Versionado de Esquema:** Motor de migraciones SQL secuenciales y verificadas por SHA-256 (`backend/scripts/run_migrations.sh`). Esquema vigente: **015**.
- **Frontend:**
  - **Librería de Interfaz:** React 19.
  - **Herramienta de Construcción:** Vite.
  - **Enrutamiento:** React Router DOM v7.
  - **Cliente HTTP:** Axios configurado con `withCredentials: true`.
  - **Componentes Cartográficos:** Leaflet y React-Leaflet con utilerías WKT (`wellknown`).
  - **Iconografía:** Lucide React.
- **Entorno e Infraestructura:**
  - Orquestación local mediante Docker Compose con cinco servicios: `db`, `backend`, `frontend`, `alertas_scheduler` y `pgadmin`.

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
├── config.py           # Variables de configuración del entorno (AUTH_SETTINGS, DATABASE_URL)
├── database.py         # Conexión SQLAlchemy, pool de conexiones y sesión por petición (SessionLocal)
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
   - `PadronHistorial` y `Orv` (evidencia de órganos ejidales).
   - `ActividadCampo` (sensibilizaciones y caminamientos con tipo de COP operativo).
3. **Ruta Colectiva:**
   - `Asamblea` (1:N) → `AsambleaConvocatoria` (primera, segunda, ulterior).
   - `Asamblea` (1:1 opcional) → `TramiteRan` (acta de asamblea).
   - `Afectacion` (ámbito colectivo) vinculada a `ProyectoNucleo`.
   - `Convenio` colectivo (autorizado opcionalmente por `Asamblea`, con trámites `TramiteRan`).
   - `ConvenioAfectacion` (relación N:M que asocia convenios y afectaciones sin duplicar montos).
4. **Ruta Individual:**
   - `Parcela` (único `no_parcela`) asociada al `NucleoAgrario`.
   - `ParcelaTitular` (titulares verificables con certificados y vigencias).
   - `Afectacion` (ámbito individual) vinculada a la `Parcela` y `ProyectoNucleo`.
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
  Middleware en FastAPI que intercepta todas las peticiones mutables (`POST`, `PUT`, `PATCH`, `DELETE`). Valida que el encabezado `X-CSRF-Token` coincida exactamente con el token de la sesión activa.
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
  Almacena el historial cronológico de cambios sobre tablas críticas mediante un trigger PL/pgSQL configurado con `SECURITY DEFINER`. Los usuarios y la aplicación solo tienen permisos de inserción; las filas son estrictamente inmutables.
- **Eventos de acceso (`evento_acceso`):**  
  Registro inmutable de eventos de autenticación (inicios de sesión exitosos, fallidos, bloqueos y cierres de sesión).

---

## 6. Subsistema Documental y Expedientes

El subsistema gestiona la evidencia jurídica que respalda cada actuación:
- **`Documento`:** Identidad lógica del documento (tipo, estado, fecha propia del instrumento y número de folio u oficio).
- **`DocumentoVersion`:** Archivos físicos almacenados en disco/volumen con su respectivo hash criptográfico SHA-256 inmutable.
- **`DocumentoVinculo`:** Relaciona un documento con una o más entidades del dominio (asambleas, convenios, parcelas, trámites). Incluye validación de aislamiento para impedir vincular documentos entre proyectos distintos.
- **`ExpedienteRequisito`:** Seguimiento del checklist documental por objetivo, admitiendo estados `disponible`, `parcial`, `pendiente_validacion`, `faltante` y `no_aplica`.

---

## 7. Seguimiento Funcional y Máquina de Hechos

Para gestionar la no linealidad del proceso agrario sin mutar destructivamente los expedientes:
- **`SeguimientoEvento`:** Tabla append-only asociada a `ProyectoNucleo` y opcionalmente a un objetivo tipado.
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

- **Almacenamiento geográfico:** PostGIS almacena geometrías en proyección geográfica estándar WGS84 (`SRID=4326`):
  - `trazo_proyecto.geometria_linea`: Líneas del proyecto ferroviario (`MULTILINESTRING`).
  - `nucleo_agrario.geometria_poligono`: Perímetro del núcleo agrario (`MULTIPOLYGON`).
  - `parcela.geometria_poligono`: Polígono parcelario opcional (`MULTIPOLYGON`).
- **Pipeline de Importación Geoespacial:**  
  Permite cargar archivos GeoJSON/Shapefile mediante un flujo controlado en tres fases:
  1. Carga del archivo y análisis de metadatos (`importacion_archivo`).
  2. Extracción y validación topológica de cada feature (`importacion_feature`).
  3. Previsualización y confirmación explícita del usuario (`confirmacion_explicita = true`) antes de impactar las capas de producción.
- **Directriz arquitectónica rectora:** La geometría es estrictamente de apoyo visual y consulta. **Ninguna validación espacial condiciona la captura administrativa de una afectación ni sustituye la superficie administrativa capturada (`superficie_ha` / `superficie_afectada_ha`) de un convenio o afectación**.
